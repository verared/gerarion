"""Tests de la capa criptográfica: firma hash pura y notario diario.

Objetivo de seguridad verificado aquí:
  - una GST firmada verifica
  - un solo bit alterado en cualquier campo rompe la verificación
  - reutilizar una hoja OTS no falsifica: produce firmas distintas
  - el encadenado diario detecta retro-ediciones en el log
"""

from __future__ import annotations

import json

import pytest

from gerarion import calendar as cal, format as fmt, gts, hashots
from gerarion.notary import DayNotary, verify_inclusion


@pytest.fixture(scope="module")
def signer():
    return hashots.WotsMerkleSigner(seed=bytes(range(32)), height=3)


def _gst(signer, ts="2031DY-03-08-T-09:30:00-SC-TCJ+0"):
    return gts.create(ts, signer)


def test_gst_create_and_verify(signer):
    doc = _gst(signer)
    result = gts.verify(doc)
    assert result["ok"], result["errors"]


def test_gst_tamper_timestamp(signer):
    doc = _gst(signer)
    doc.ts = "2031DY-03-08-T-09:31:00-SC-TCJ+0"  # 1 minuto posterior
    assert not gts.verify(doc)["ok"]


def test_gst_tamper_instant(signer):
    doc = _gst(signer)
    doc.instant += 1
    assert not gts.verify(doc)["ok"]


def test_gst_tamper_signature(signer):
    doc = _gst(signer)
    doc.sig["sig"][0] = "00" * 32
    assert not gts.verify(doc)["ok"]


def test_gst_wrong_key(signer):
    doc = _gst(signer)
    other = hashots.WotsMerkleSigner(seed=b"x" * 32, height=3)
    doc.pub = other.public_key.hex()
    assert not gts.verify(doc)["ok"]


def test_json_roundtrip_preserves_verifiability(signer):
    doc = _gst(signer)
    clone = gts.GtsDocument.from_json(doc.to_json())
    assert gts.verify(clone)["ok"]


def test_ots_leaves_are_single_use():
    signer = hashots.WotsMerkleSigner(seed=b"\x01" * 32, height=3)
    doc1 = gts.create("2031DY-03-08-T", signer)
    doc2 = gts.create("2031DY-03-08-T", signer)
    assert doc1.sig["leaf"] == 0 and doc2.sig["leaf"] == 1
    # ambos verifican (cada uno con su hoja) y firman cosas distintas
    assert gts.verify(doc1)["ok"] and gts.verify(doc2)["ok"]
    assert doc1.sig["sig"] != doc2.sig["sig"]


# ---------------------------------------------------------------------------
# Notario
# ---------------------------------------------------------------------------


def _fill_day(notary, day, n=3, ts_day=None):
    """Sella un día con n marcas deterministas."""
    docs = []
    ts = f"{ts_day or '2031DY-03-08-T'}"
    base_date = fmt.parse(ts)
    date = cal.from_gerarion(base_date.year, base_date.month, base_date.day)
    for i in range(n):
        instant = cal.instant_from_parts(date.day_index, 9, 30, i)
        payload = fmt.canonical_bytes(ts, instant)
        idx = notary.append(payload)
        docs.append((payload, idx, instant))
    notary.seal_day(day)
    return docs


def test_notary_chain_and_sealing():
    notary = DayNotary()
    _fill_day(notary, 0)
    _fill_day(notary, 1)
    assert len(notary._days) == 2
    assert notary.chain_head(1) != notary.chain_head(0)
    assert notary.verify_chain()


def test_notary_inclusion_proof():
    import hashlib

    notary = DayNotary()
    docs = _fill_day(notary, 7)
    payload, idx, _instant = docs[1]
    proof = notary.inclusion_proof(7, idx)
    leaf = hashlib.sha256(b"\x00" + payload).digest()
    assert verify_inclusion(leaf, proof["proof"], idx, bytes.fromhex(proof["root"]))
    # una hoja distinta no verifica esa prueba
    other = hashesha256(b"\x00" + payload + b"x")
    assert not verify_inclusion(
        bytes.fromhex(other), proof["proof"], idx, bytes.fromhex(proof["root"])
    )


def hashesha256(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def test_notary_tamper_detected():
    notary = DayNotary()
    _fill_day(notary, 0)
    _fill_day(notary, 1)
    # manipular una hoja del día 0 rompe la cadena completa
    rec = notary._days[0]
    leaves = json.loads(notary.export())["days"][0]["leaves"]
    rec2 = json.loads(notary.export())
    rec2["days"][0]["leaves"][0] = "00" * 32
    tampered = DayNotary.import_json(json.dumps(rec2))
    assert not tampered.verify_chain()


def test_notary_out_of_order_rejected():
    notary = DayNotary()
    _fill_day(notary, 0)
    with pytest.raises(ValueError):
        notary.seal_day(5)


def test_anchor_lifecycle():
    signer = hashots.WotsMerkleSigner(seed=b"a" * 32, height=2)
    notary = DayNotary()
    doc = gts.create("2031DY-03-08-T", signer)
    gts.notarize(doc, notary)
    # aún sin sellar: no verificable como anclada
    assert not gts.verify_anchor(doc, notary)["ok"]
    anchor_day = doc.anchor["day"]
    notary.seal_day(anchor_day)
    proof = notary.inclusion_proof(anchor_day, doc.anchor["leaf_index"])
    doc.anchor = {
        "day": anchor_day,
        "leaf_index": proof["index"],
        "sealed": True,
        "proof": proof["proof"],
        "root": proof["root"],
    }
    assert gts.verify_anchor(doc, notary)["ok"]


def test_leaf_ledger_persists_and_never_repeats():
    """LeafLedger: índices únicos bajo bloqueo de archivo y estado persistente.

    Cierre del hueco de dos instancias en memoria con la misma semilla.
    """
    import os
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    signer = hashots.WotsMerkleSigner(seed=b"b" * 32, height=2)
    tmp = tempfile.mkdtemp()
    ledger_path = os.path.join(tmp, "leaves.json")

    # En un proceso: asigna 3 índices y muere (simula caída tras firmar)
    code = (
        "from gerarion import hashots;"
        f"led = hashots.LeafLedger({ledger_path!r});"
        f"print([led.allocate({signer.leaves}) for _ in range(3)])"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, check=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )
    assert json.loads(out.stdout.strip()) == [0, 1, 2]
    assert json.loads(Path(ledger_path).read_text()) == {"next": 3}

    # En otro proceso distinto: continúa en 3, jamás repite
    led = hashots.LeafLedger(ledger_path)
    assert led.allocate(signer.leaves) == 3
    with pytest.raises(RuntimeError, match="agotado"):
        led.allocate(signer.leaves)
    # El archivo solo guarda el contador, sin material criptográfico
    assert json.loads(Path(ledger_path).read_text()) == {"next": 4}


def test_leaf_ledger_exact_contents():
    signer = hashots.WotsMerkleSigner(seed=b"c" * 32, height=1)
    import tempfile
    import os
    import json as _json
    path = os.path.join(tempfile.mkdtemp(), "leaves.json")
    led = hashots.LeafLedger(path)
    a, b = led.allocate(signer.leaves), led.allocate(signer.leaves)
    assert (a, b) == (0, 1)
    assert _json.loads(open(path).read()) == {"next": 2}
