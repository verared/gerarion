# -*- coding: utf-8 -*-
"""Verificador monolítico tools/verify_gus.py: stdlib puro, sin paquete.

La propiedad clave: el monolítico NO importa `gerarion`. Se valida contra
la librería de referencia por CONFORMANCIA (differential): GST construida
con la librería debe dar exit 0 en el monolítico; cualquier byte alterado,
exit != 0 con error GERO_*.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from gerarion import format as fmt, hashots, gts as gtsmod

TOOL = Path(__file__).resolve().parent.parent / "tools" / "verify_gus.py"


@pytest.fixture(scope="module")
def good_doc():
    """GST firmada por la librería + anchor sintético (mismas primitivas)."""
    doc = gtsmod.create(
        fmt.parse("0001DY-02-06-S-09:30:12-SC-TCJ+0"),
        hashots.WotsMerkleSigner(seed=b"unit-test-seed-not-secret", height=3),
    )
    leaf0 = hashlib.sha256(
        b"\x00" + fmt.canonical_bytes(doc.ts, doc.instant, doc.ctx)
    ).digest()
    leaf1 = hashlib.sha256(b"\x00" + b"otra-marca-cualquiera").digest()
    root = hashlib.sha256(b"\x01" + leaf0 + leaf1).digest()
    doc.anchor = {
        "day": doc.day, "index": 0, "root": root.hex(),
        "proof": [leaf1.hex()], "sealed": True,
    }
    return doc


def _run(doc_json: str):
    p = Path("/tmp/gusverify-monolithic.gst.json")
    p.write_text(doc_json)
    proc = subprocess.run(
        [sys.executable, str(TOOL), str(p)],
        capture_output=True, text=True, timeout=120,
    )
    return proc


def test_good_gst_verifies(good_doc):
    proc = _run(good_doc.to_json())
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("OK " + good_doc.ts)


def test_tampered_time_rejected(good_doc):
    bad = json.loads(good_doc.to_json())
    bad["ts"] = bad["ts"].replace("09:30:12", "09:30:13")
    proc = _run(json.dumps(bad))
    assert proc.returncode != 0


def test_tampered_signature_rejected(good_doc):
    bad = json.loads(good_doc.to_json())
    bad["sig"]["sig"][0] = "00" * 64
    proc = _run(json.dumps(bad))
    assert proc.returncode != 0
    assert "GERO_" in proc.stderr


def test_broken_anchor_rejected(good_doc):
    bad = json.loads(good_doc.to_json())
    bad["anchor"]["root"] = "00" * 32
    proc = _run(json.dumps(bad))
    assert proc.returncode != 0
    assert "incluida" in proc.stderr


def test_slhdsa_without_package_is_enoalg_not_false_ok(good_doc):
    """Con slh-dsa ausente, la GST de esa familia NO puede verificar:
    el verificador debe reportar GERO_ENOALG (nunca falso OK)."""
    bad = json.loads(good_doc.to_json())
    bad["alg"] = "SLH-DSA-SHA2-128f"
    proc = _run(json.dumps(bad))
    try:
        import slhdsa  # noqa: F401
        has_pkg = True
    except ImportError:
        has_pkg = False
    if has_pkg:
        pytest.skip("slh-dsa instalado: la firma de referencia no es SLH-DSA, "
                    "el rechazo de dominio ya lo cubren los tests de adaptadores")
    assert proc.returncode != 0
    assert "GERO_ENOALG" in proc.stderr


def test_bad_weekday_letter_flagged(good_doc):
    bad = json.loads(good_doc.to_json())
    bad["ts"] = bad["ts"].replace("-S-09:30", "-L-09:30")
    proc = _run(json.dumps(bad))
    assert proc.returncode != 0
    assert "GERO_EWEEK" in proc.stderr
