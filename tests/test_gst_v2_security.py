# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Pruebas de endurecimiento GST v2 (v3.3.0):

- KeyRegistry y TrustedKeyRecord: rechazo de sobres autofirmados/suplantados
  (KEY_MISMATCH / UNKNOWN_KEY), rotación histórica (HISTORICAL), expiración
  (KEY_EXPIRED), revocación (KEY_REVOKED) y serialización JSON determinista.
- SQLiteReplayStore: concurrencia real con 16 hilos simultáneos (exactamente
  1 aceptado y 15 rechazados por REPLAY), rechazo de SEQ_ROLLBACK y modo
  fail-closed ante corrupción de base de datos.
- VerificationResult en 3 niveles (crypto, identity, temporal): política
  fail-closed para trust_store=None y replay_store=None, propagación honesta
  de clock_state ("UNKNOWN" por defecto vs lectura real de gt-gts).
- DeprecationWarning explícito en API legada GST v1 (create/verify) y cero
  warnings en gerarion.gst.v2.
- Ejecución directa del snippet «CMS / API in 1 Minute» documentado en README.md.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import re
import threading
import warnings
from pathlib import Path

import pytest

from gerarion.core import format as fmt
from gerarion.gst import HybridSigner, envelope as gst_env, v2
from gerarion.gts import clock as gts_clock

REPO = Path(__file__).resolve().parent.parent
EVENT_HASH = "sha256:" + hashlib.sha256(b"cms-event-payload-v3.3.0").hexdigest()


@pytest.fixture()
def signer_a() -> HybridSigner:
    return HybridSigner(
        seed_classical=bytes(range(32)),
        seed_pqc=bytes(range(32, 64)),
    )


@pytest.fixture()
def signer_b() -> HybridSigner:
    return HybridSigner(
        seed_classical=bytes(range(64, 96)),
        seed_pqc=bytes(range(96, 128)),
    )


# ---------------------------------------------------------------------------
# 1. KeyRegistry: suplantación autofirmada, rotación, expiración y revocación
# ---------------------------------------------------------------------------


def test_self_signed_spoofed_issuer_rejected_at_level_2(
    signer_a: HybridSigner,
    signer_b: HybridSigner,
) -> None:
    """Un sobre matemáticamente válido firmado por un atacante que suplanta
    (issuer, kid) pasa Nivel 1 (crypto) pero falla Nivel 2 (identity)."""
    registry = v2.KeyRegistry()
    registry.register_signer(
        issuer="cms.portaless.org",
        kid="cms-k1",
        signer=signer_a,
    )
    replay = v2.SQLiteReplayStore(":memory:")

    # signer_b suplanta issuer="cms.portaless.org" y kid="cms-k1"
    spoofed_env = v2.create(
        "2031DY-03-08-T-09:30:00-SC-TCJ+0",
        signer_b,
        event_hash=EVENT_HASH,
        issuer="cms.portaless.org",
        kid="cms-k1",
        seq=1,
    )
    res = v2.verify(spoofed_env, trust_store=registry, replay_store=replay)
    assert res.crypto.valid is True
    assert res.identity.valid is False
    assert res.identity.trusted_issuer is False
    assert res.identity.key_status == "MISMATCH"
    assert "KEY_MISMATCH" in res.identity.reason
    assert res.overall_trusted is False

    # Además, el intento con clave falsa NO debe haber consumido seq=1 del emisor real
    legit_env = v2.create(
        "2031DY-03-08-T-09:30:00-SC-TCJ+0",
        signer_a,
        event_hash=EVENT_HASH,
        issuer="cms.portaless.org",
        kid="cms-k1",
        seq=1,
    )
    res_legit = v2.verify(legit_env, trust_store=registry, replay_store=replay)
    assert res_legit.overall_trusted is True
    assert res_legit.identity.key_status == "ACTIVE"
    assert res_legit.identity.replay_status == "OK"


def test_unknown_key_rejected_at_level_2(signer_a: HybridSigner) -> None:
    registry = v2.KeyRegistry()
    replay = v2.SQLiteReplayStore(":memory:")
    env = v2.create(
        "2031DY-03-08-T-09:30:00-SC-TCJ+0",
        signer_a,
        event_hash=EVENT_HASH,
        issuer="unknown.example.org",
        kid="missing-kid",
        seq=1,
    )
    res = v2.verify(env, trust_store=registry, replay_store=replay)
    assert res.crypto.valid is True
    assert res.identity.valid is False
    assert res.identity.key_status == "UNKNOWN"
    assert "UNKNOWN_KEY" in res.identity.reason
    assert res.overall_trusted is False


def test_key_rotation_historical_valid_and_expired_or_revoked_rejected(
    signer_a: HybridSigner,
    signer_b: HybridSigner,
) -> None:
    """Rotación de claves:
    - Evento antiguo dentro de la ventana de k1 sigue validando como HISTORICAL.
    - Evento nuevo firmado con k1 fuera de valid_until falla con KEY_EXPIRED.
    - Evento firmado con clave revocada en/tras revoked_at falla con KEY_REVOKED,
      mientras un evento previo a revoked_at sigue siendo auditable como HISTORICAL.
    """
    registry = v2.KeyRegistry()
    # k1 válida durante los primeros 6 meses de 2031DY
    registry.register_signer(
        issuer="cms.portaless.org",
        kid="k1-2026",
        signer=signer_a,
        valid_from="2031DY-01-01-S-00:00:00-LC-TCJ+0",
        valid_until="2031DY-06-30-L-23:59:59-LC-TCJ+0",
    )
    # k2 rotada y activa desde el mes 7
    registry.register_signer(
        issuer="cms.portaless.org",
        kid="k2-2026",
        signer=signer_b,
        valid_from="2031DY-07-01-M-00:00:00-LC-TCJ+0",
    )
    replay = v2.SQLiteReplayStore(":memory:")

    # 1. Evento histórico firmado por k1 dentro de su ventana (mes 3) -> HISTORICAL
    old_env = v2.create(
        "2031DY-03-08-T-09:30:00-SC-TCJ+0",
        signer_a,
        event_hash=EVENT_HASH,
        issuer="cms.portaless.org",
        kid="k1-2026",
        seq=1,
    )
    res_old = v2.verify(old_env, trust_store=registry, replay_store=replay)
    assert res_old.crypto.valid is True
    assert res_old.identity.valid is True
    assert res_old.identity.key_status == "HISTORICAL"
    assert "HISTORICAL_VALID" in res_old.identity.reason
    assert res_old.overall_trusted is True

    # 2. Evento nuevo firmado por k1 fuera de su ventana (mes 8) -> KEY_EXPIRED
    expired_env = v2.create(
        "2031DY-08-10-A-12:00:00-SC-TCJ+0",
        signer_a,
        event_hash=EVENT_HASH,
        issuer="cms.portaless.org",
        kid="k1-2026",
        seq=2,
    )
    res_exp = v2.verify(expired_env, trust_store=registry, replay_store=replay)
    assert res_exp.crypto.valid is True
    assert res_exp.identity.valid is False
    assert res_exp.identity.key_status == "EXPIRED"
    assert "KEY_EXPIRED" in res_exp.identity.reason
    assert res_exp.overall_trusted is False

    # 3. Evento nuevo firmado por k2 (mes 8) -> ACTIVE
    active_env = v2.create(
        "2031DY-08-10-A-12:00:00-SC-TCJ+0",
        signer_b,
        event_hash=EVENT_HASH,
        issuer="cms.portaless.org",
        kid="k2-2026",
        seq=1,
    )
    res_act = v2.verify(active_env, trust_store=registry, replay_store=replay)
    assert res_act.overall_trusted is True
    assert res_act.identity.key_status == "ACTIVE"

    # 4. Revocación de clave en un instante exacto
    registry.register_signer(
        issuer="cms.portaless.org",
        kid="k-revoked",
        signer=signer_a,
        valid_from="2031DY-01-01-S-00:00:00-LC-TCJ+0",
        revoked_at="2031DY-05-01-T-00:00:00-LC-TCJ+0",
        revocation_reason="compromiso de host",
    )
    pre_rev = v2.create(
        "2031DY-04-15-B-10:00:00-SC-TCJ+0",
        signer_a,
        event_hash=EVENT_HASH,
        issuer="cms.portaless.org",
        kid="k-revoked",
        seq=1,
    )
    res_pre = v2.verify(pre_rev, trust_store=registry, replay_store=replay)
    assert res_pre.overall_trusted is True
    assert res_pre.identity.key_status == "HISTORICAL"

    post_rev = v2.create(
        "2031DY-05-01-T-00:00:00-LC-TCJ+0",
        signer_a,
        event_hash=EVENT_HASH,
        issuer="cms.portaless.org",
        kid="k-revoked",
        seq=2,
    )
    res_post = v2.verify(post_rev, trust_store=registry, replay_store=replay)
    assert res_post.crypto.valid is True
    assert res_post.identity.valid is False
    assert res_post.identity.key_status == "REVOKED"
    assert "KEY_REVOKED" in res_post.identity.reason
    assert res_post.overall_trusted is False

    # 5. Round-trip JSON determinista del KeyRegistry
    dumped = registry.to_json()
    restored = v2.KeyRegistry.from_json(dumped)
    assert restored.to_json() == dumped


# ---------------------------------------------------------------------------
# 2. SQLiteReplayStore: concurrencia real (16 hilos) y corrupción fail-closed
# ---------------------------------------------------------------------------


def test_sqlite_replay_store_16_threads_concurrency(
    tmp_path: Path,
    signer_a: HybridSigner,
) -> None:
    """16 hilos simultáneos enviando el mismo sobre firmado contra un
    SQLiteReplayStore en archivo: exactamente 1 aceptado y 15 rechazados por REPLAY."""
    db_path = tmp_path / "concurrent_replay.sqlite3"
    store = v2.SQLiteReplayStore(db_path)
    registry = v2.KeyRegistry()
    registry.register_signer(issuer="cms.example.org", kid="k-conc", signer=signer_a)

    env = v2.create(
        "2031DY-03-08-T-09:30:00-SC-TCJ+0",
        signer_a,
        event_hash=EVENT_HASH,
        issuer="cms.example.org",
        kid="k-conc",
        seq=1,
    )

    barrier = threading.Barrier(16)

    def _worker() -> v2.VerificationResult:
        barrier.wait(timeout=5.0)
        return v2.verify(dict(env), trust_store=registry, replay_store=store)

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: _worker(), range(16)))

    store.close()

    accepted = [r for r in results if r.overall_trusted and r.identity.replay_status == "OK"]
    rejected = [
        r for r in results
        if not r.overall_trusted
        and r.crypto.valid
        and r.identity.replay_status == "REPLAY"
    ]
    assert len(accepted) == 1, f"se esperaba exactamente 1 aceptado, hubo {len(accepted)}"
    assert len(rejected) == 15, f"se esperaban 15 rechazados por REPLAY, hubo {len(rejected)}"


def test_sqlite_replay_store_seq_rollback_and_fail_closed_corruption(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "state.sqlite3"
    store = v2.SQLiteReplayStore(db_path)
    d1 = store.check_and_record("iss", "k1", 10, "a" * 32, 1000)
    assert d1.ok is True and d1.status == "OK"

    # Rollback de seq (9 <= 10)
    d2 = store.check_and_record("iss", "k1", 9, "b" * 32, 1001)
    assert d2.ok is False and d2.status == "SEQ_ROLLBACK"
    store.close()

    # Corromper archivo SQLite en disco -> debe abrir en modo fail-closed
    corrupt_path = tmp_path / "corrupt.sqlite3"
    corrupt_path.write_bytes(b"NOT_A_VALID_SQLITE_HEADER_1234567890")
    corrupt_store = v2.SQLiteReplayStore(corrupt_path)
    d3 = corrupt_store.check_and_record("iss", "k1", 1, "c" * 32, 1000)
    assert d3.ok is False
    assert "fail-closed" in d3.reason


# ---------------------------------------------------------------------------
# 3. Política fail-closed (replay_store=None / trust_store=None) y Nivel 3
# ---------------------------------------------------------------------------


def test_fail_closed_when_replay_store_or_trust_store_is_none(
    signer_a: HybridSigner,
) -> None:
    registry = v2.KeyRegistry()
    registry.register_signer(issuer="cms.example.org", kid="k1", signer=signer_a)
    env = v2.create(
        "2031DY-03-08-T-09:30:00-SC-TCJ+0",
        signer_a,
        event_hash=EVENT_HASH,
        issuer="cms.example.org",
        kid="k1",
        seq=1,
    )

    # replay_store=None -> replay_checked=False, replay_status="SKIPPED", identity.valid=False
    res_no_replay = v2.verify(env, trust_store=registry, replay_store=None)
    assert res_no_replay.crypto.valid is True
    assert res_no_replay.identity.trusted_issuer is True
    assert res_no_replay.identity.replay_checked is False
    assert res_no_replay.identity.replay_status == "SKIPPED"
    assert res_no_replay.identity.valid is False
    assert res_no_replay.overall_trusted is False

    # Opt-in explícito allow_unchecked_replay=True -> overall_trusted=True pero deja rastro replay_checked=False
    res_opt_in = v2.verify(
        env,
        trust_store=registry,
        replay_store=None,
        allow_unchecked_replay=True,
    )
    assert res_opt_in.identity.replay_checked is False
    assert res_opt_in.identity.replay_status == "SKIPPED"
    assert res_opt_in.identity.valid is True
    assert res_opt_in.overall_trusted is True

    # trust_store=None -> key_status="UNCHECKED", overall_trusted=False
    replay = v2.SQLiteReplayStore(":memory:")
    res_no_trust = v2.verify(env, trust_store=None, replay_store=replay)
    assert res_no_trust.crypto.valid is True
    assert res_no_trust.identity.trusted_issuer is False
    assert res_no_trust.identity.key_status == "UNCHECKED"
    assert res_no_trust.identity.valid is False
    assert res_no_trust.overall_trusted is False


def test_level_3_temporal_unknown_by_default_and_propagates_gts_reading(
    signer_a: HybridSigner,
) -> None:
    registry = v2.KeyRegistry()
    registry.register_signer(issuer="cms.example.org", kid="k1", signer=signer_a)
    replay = v2.SQLiteReplayStore(":memory:")

    env = v2.create(
        "2031DY-03-08-T-09:30:00-SC-TCJ+0",
        signer_a,
        event_hash=EVENT_HASH,
        issuer="cms.example.org",
        kid="k1",
        seq=1,
    )
    res_default = v2.verify(env, trust_store=registry, replay_store=replay)
    assert res_default.temporal.clock_state == "UNKNOWN"
    assert res_default.temporal.clock_source is None
    assert res_default.temporal.signed_at == "2031DY-03-08-T-09:30:00-SC-TCJ+0"

    # Pasar una lectura real clasificada por gt-gts
    pol = gts_clock.ClockPolicy(max_uncertainty_ns=5_000_000, strict=True, require_authenticated=True)
    tc = gts_clock.TrustedClock(policy=pol)
    reading = tc.classify(
        gts_clock.ClockReading(
            instant=env["ins"],
            nanos=0,
            source_id="gnss-ptp-01",
            uncertainty_ns=250_000,
            monotonic_ns=1_000_000_000,
            authenticated=True,
        )
    )
    env2 = v2.create(
        "2031DY-03-08-T-09:30:01-SC-TCJ+0",
        signer_a,
        event_hash=EVENT_HASH,
        issuer="cms.example.org",
        kid="k1",
        seq=2,
    )
    res_verified = v2.verify(
        env2,
        trust_store=registry,
        replay_store=replay,
        clock_reading=reading,
    )
    assert res_verified.temporal.clock_state == "VERIFIED"
    assert res_verified.temporal.clock_source == "gnss-ptp-01"
    assert res_verified.temporal.clock_uncertainty_ns == 250_000


# ---------------------------------------------------------------------------
# 4. DeprecationWarning en v1 vs limpio en v2, y snippet README 1-Minute
# ---------------------------------------------------------------------------


def test_legacy_v1_emits_deprecation_warning_while_v2_is_clean(
    signer_a: HybridSigner,
) -> None:
    from gerarion.deprecated.hashots import WotsMerkleSigner

    legacy_signer = WotsMerkleSigner(seed=b"\x11" * 16, height=4)
    with pytest.deprecated_call():
        doc = gst_env.create("2031DY-03-08-T-09:30:00-SC-TCJ+0", legacy_signer)
    with pytest.deprecated_call():
        v1_res = gst_env.verify(doc)
    assert v1_res["ok"] is True

    # v2 no debe emitir ningún DeprecationWarning
    registry = v2.KeyRegistry()
    registry.register_signer(issuer="cms.example.org", kid="k1", signer=signer_a)
    replay = v2.SQLiteReplayStore(":memory:")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        env = v2.create(
            fmt.parse("2031DY-03-08-T-09:30:00-SC-TCJ+0"),
            signer_a,
            event_hash=EVENT_HASH,
            issuer="cms.example.org",
            kid="k1",
            seq=1,
        )
        res = v2.verify(env, trust_store=registry, replay_store=replay)
        assert res.overall_trusted is True
    dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert dep_warnings == []


def test_readme_cms_1_minute_quickstart_executes_verbatim() -> None:
    """Extrae y ejecuta el bloque Python de «Integrate gt-core + gt-gst in 1 Minute»
    directamente desde README.md para garantizar que el ejemplo nunca se desincronice."""
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    m = re.search(
        r"## Integrate `gt-core` \+ `gt-gst` in 1 Minute.*?```python\n(.*?)```",
        readme,
        re.DOTALL,
    )
    assert m is not None, "No se encontró el bloque Quickstart de 1 minuto en README.md"
    code = m.group(1)
    ns: dict = {}
    exec(compile(code, "<README-1-minute-quickstart>", "exec"), ns, ns)
    assert ns["res"].overall_trusted is True
