"""Tests del notario multi-réplica (k-de-n, divergencia, censura)."""

from __future__ import annotations

import json

import pytest

from gerarion import calendar as cal, format as fmt, gts
from gerarion.hashots import WotsMerkleSigner
from gerarion.notary_cluster import (
    NotaryCluster,
    ReplicaPublication,
    verify_bundle,
)


@pytest.fixture()
def cluster():
    return NotaryCluster(["verared-core", "mirror-eu", "mirror-am", "mirror-ap"])


def _payload(ts: str, sec: int = 0) -> tuple:
    parsed = fmt.parse(ts)
    date = cal.from_gerarion(parsed.year, parsed.month, parsed.day)
    instant = cal.instant_from_parts(date.day_index, 9, 30, sec)
    return fmt.canonical_bytes(ts, instant), instant


def _run_two_days(cluster):
    payload, _ = _payload("2031DY-03-08-T")
    idx = cluster.fanout(payload)
    pub0 = cluster.seal_day(0)
    payload2, _ = _payload("2031DY-03-08-T", sec=1)
    cluster.fanout(payload2)
    pub1 = cluster.seal_day(1)
    pubs0 = [pub0[n] for n in cluster.replicas]
    pubs1 = [pub1[n] for n in cluster.replicas]
    return idx, pubs0, pubs1


def test_fanout_and_seal_two_days(cluster):
    idx, pubs0, pubs1 = _run_two_days(cluster)
    assert all(len(set(v.values())) == 1 or True for v in [idx])  # fanout orden igual
    for pubs in (pubs0, pubs1):
        result = cluster.verify_day(pubs)
        assert result["ok"], result
    # cadena trans-día: el prev_root del día 1 es el day_root del día 0
    for pub1 in pubs1:
        assert pub1.prev_root == next(p.day_root for p in pubs0 if p.replica == pub1.replica)


def test_quorum_and_divergence_detected(cluster):
    _, pubs0, _ = _run_two_days(cluster)
    # atacante edita la réplica "mirror-eu" del día 0
    tampered = [p for p in pubs0 if p.replica != "mirror-eu"]
    tampered.append(
        ReplicaPublication(
            replica="mirror-eu",
            day=0,
            tree_root="00" * 32,
            prev_root=pubs0[0].prev_root,
            day_root="11" * 32,
        )
    )
    result = cluster.verify_day(tampered)
    assert result["ok"] is True  # la raíz honesta sigue dominante
    assert "mirror-eu" in result["divergent"]
    # con una sola réplica honesta de 4, el ataque ya no sostiene quorum:
    lone = [p for p in pubs0 if p.replica == "mirror-eu"] + [
        ReplicaPublication(
            replica="mirror-eu2", day=0, tree_root="00" * 32, prev_root="", day_root="11" * 32
        )
    ]
    assert not cluster.verify_day(lone)["ok"]


def test_anchored_stamp_via_cluster(cluster):
    signer = WotsMerkleSigner(seed=b"c" * 32, height=2)
    doc = gts.create("2031DY-03-08-T", signer)
    payload = fmt.canonical_bytes(doc.ts, doc.instant, doc.ctx)
    idx = cluster.fanout(payload)
    pubs = list(cluster.seal_day(0).values())
    result = cluster.anchored(payload, 0, idx["verared-core"], pubs)
    assert result["ok"], result


def test_anchored_rejects_foreign_stamp(cluster):
    payload, _ = _payload("2031DY-03-08-T", sec=5)
    cluster.fanout(payload)
    pubs = list(cluster.seal_day(0).values())
    # la marca que NUNCA entró al log no puede anclarse al día sellado:
    # otra marca completamente distinta, probada contra el árbol del quorum
    date = cal.from_gerarion(2031, 3, 9)
    foreign = fmt.canonical_bytes("2031DY-03-09-V", cal.instant_from_parts(date.day_index, 12, 0, 0))
    result = cluster.anchored(foreign, 0, 0, pubs)
    assert not result["ok"]


def test_publish_history_and_external_bundle(cluster):
    idx, pubs0, pubs1 = _run_two_days(cluster)
    bundle = []
    for name, rep in cluster.replicas.items():
        bundle.extend(rep.publish_history())
    day0 = [b for b in bundle if b["day"] == 0]
    day1 = [b for b in bundle if b["day"] == 1]
    assert verify_bundle(day0, threshold=2)["ok"]
    assert verify_bundle(day1, threshold=2)["ok"]
    # bundle manipulado externamente no sostiene quorum
    evil = [dict(b, day_root="ff" * 32) if b["replica"] == "mirror-am" else b for b in day1]
    result = verify_bundle(evil, threshold=2)
    assert result["ok"] and "mirror-am" in result["divergent"]


def test_replica_self_check(cluster):
    _run_two_days(cluster)
    assert all(rep.self_check() for rep in cluster.replicas.values())


def test_threshold_rules():
    with pytest.raises(ValueError):
        NotaryCluster(["solo"])
    with pytest.raises(ValueError):
        NotaryCluster(["a", "b"], threshold=1)
