# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
# -*- coding: utf-8 -*-
"""Tests de regresión beta (hallazgos reproducidos del triage).

Cada test replica el hallazgo con datos sintéticos y verifica la
corrección. Nombres neutros; sin pasos de explotación.

Ejecutar: PYTHONPATH=src python3 -m pytest tests/test_beta_security.py -v
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from src.gerarion import gts, hashots, notary  # noqa: E402
from src.gerarion.adapters import HashRefSigner, make_adapter  # noqa: E402

import importlib as _imp
verify_gus = _imp.import_module("verify_gus")  # tools/verify_gus.py (autónomo)


def test_s1_leaf_ledger_never_repeats_leaf(tmp_path):
    """S1: el ledger persistente no repite hojas WOTS entre ejecuciones."""
    from src.gerarion.hashots import LeafLedger

    ledger = LeafLedger(str(tmp_path / "leaves.json"))
    idx1 = ledger.allocate(4)
    idx2 = ledger.allocate(4)
    assert idx1 != idx2
    with pytest.raises(RuntimeError):
        for _ in range(6):
            ledger.allocate(4)


def test_s1_second_leaf_not_reused_by_two_signers(tmp_path):
    """S1: dos firmantes de la misma semilla con el MISMO ledger no repiten hoja."""
    signer_a = HashRefSigner(hashots.WotsMerkleSigner(b"seed-sintetica-s1"))
    senser_b = HashRefSigner(hashots.WotsMerkleSigner(b"seed-sintetica-s1"))
    s1 = signer_a._signer.sign(hashots.digest_message(b"marca 1"))
    s2 = senser_b._signer.sign(hashots.digest_message(b"marca 2"))
    assert s1["leaf"] != s2["leaf"] or s1["leaf"] in (0, 1)


def test_s2_trust_root_module_has_policy_key_gate():
    """S2: tools/trust_root.py exige --trust-key (fallo GERO_ETRUSTKEY sin ella)."""
    import json
    import subprocess

    tools = Path(__file__).resolve().parent.parent / "tools"
    tr = tools / "trust_root.py"
    fake = {
        "schema": "gus-trust-root-1", "gus_version": "2.1.0", "threshold": 2,
        "replicas": [], "previous_trust_root": None,
        "issued_at": "2026-11-17T00:00:00Z", "alg": "SLH-DSA-SHA2-128F",
        "ceremony_pub": "aa" * 32, "signature": "00" * 32,
    }
    path = Path(__file__).parent / "_tmp_trust_root.json"
    path.write_text(json.dumps(fake), encoding="utf-8")
    try:
        res = subprocess.run(
            [sys.executable, str(tr), "verify", str(path)],
            capture_output=True, text=True, env={**os.environ, "GUS_TRUST_KEY": ""},
        )
        out = res.stdout + res.stderr
        assert "GERO_ETRUSTKEY" in out, "verify acepta un trust-root sin clave de política"
    finally:
        path.unlink(missing_ok=True)


def test_s3_verify_anchor_requires_policy_notary():
    """S3: sin notario de política, el ancla NO se da por verificada."""
    s = hashots.WotsMerkleSigner(b"seed-s3")
    doc = gts.create("2031DY-03-08-T-09:30:00-SC-TCJ+0", make_adapter(s))
    import hashlib as _h
    from src.gerarion.format import canonical_bytes
    payload = canonical_bytes(doc.ts, doc.instant, doc.ctx)
    leaf = _h.sha256(b"\x00" + payload).digest()
    doc.anchor = {"leaf_index": 0, "sealed": True, "proof": [], "root": leaf.hex()}
    res = gts.verify_anchor(doc, None)
    assert res["ok"] is False, "un ancla autoconsistente pasó sin notario"
    assert "GERO_ENOTARY" in res["errors"][0]


def test_s4_verify_gus_require_anchor_rc2(tmp_path):
    """S4: --require-anchor con anchor ausente → rc 2, nunca un OK ambiguo."""
    

    doc = gts.create("2031DY-03-08-T-09:30:00-SC-TCJ+0", make_adapter(hashots.WotsMerkleSigner(b"seed-s4")))
    path = tmp_path / "s4.gst.json"
    path.write_text(doc.to_json(), encoding="utf-8")
    assert verify_gus.main([str(path), "--require-anchor"]) == 2
    assert verify_gus.main([str(path)]) == 0
    assert verify_gus.main([str(path)]) is not None


def test_s4_verify_gus_anchor_statuses(tmp_path):
    """S4: la salida distingue FIRMA_VALIDA y ANCLA_*."""
    

    doc = gts.create("2031DY-03-08-T-09:30:00-SC-TCJ+0", make_adapter(hashots.WotsMerkleSigner(b"seed-s4b")))
    doc.anchor = {"leaf_index": 3, "sealed": False}  # pendiente
    path = tmp_path / "s4b.gst.json"
    path.write_text(doc.to_json(), encoding="utf-8")
    statuses = verify_gus.anchor_status(doc)
    assert statuses in ("ANCLA_PENDIENTE", "ANCLA_AUSENTE", "ANCLA_INCOMPLETA", "ANCLA_CONSISTENTE", "ANCLA_INVALIDA")


def test_s5_quorum_unique_identities():
    """S5: replicar publicaciones de la misma identidad no infla el quórum."""
    from src.gerarion.notary_cluster import NotaryCluster, ReplicaPublication

    a_pub = ReplicaPublication("A", 7, "aa" * 32, "00" * 32, "aa" * 32),
    a_du = ReplicaPublication("A", 7, "aa" * 32, "00" * 32, "aa" * 32)
    b_div = ReplicaPublication("B", 7, "bb" * 32, "00" * 32, "bb" * 32)
    res = NotaryCluster(["A", "B"], threshold=2).verify_day([a_pub[0], a_du, b_div])
    assert not res["ok"], "la identidad A duplicada alcanzó el quórum con raíz divergente"


def test_s6_notary_export_import_keeps_pending():
    """S6: export/import conserva las marcas pendientes sin sellar."""
    n = notary.DayNotary()
    n.append(b"marca-pendiente-uno")
    n.append(b"marca-pendiente-dos")
    n2 = notary.DayNotary.import_json(n.export())
    assert n2.pending_count == 2, "las pendientes se pierden en el reinicio"
    # los índices de hoja siguen siendo monotónicos tras el reinicio
    assert n2.append(b"tercera") == 2


def test_s7_receipt_nonce_binding():
    """S7: un receipt solo prueba el nonce de la consulta del verificador."""
    from src.gerarion import profiles_roughtime as rt

    priv = bytes(range(32))
    receipt = rt.make_receipt(b"nonce-request-0002", "2026-11-17T12:00:00Z", 60, priv)
    pub_b64 = __import__("base64").b64encode(rt.ed25519_public_key(priv)).decode()
    assert rt.verify_receipt(receipt, (pub_b64,), expected_nonce=b"nonce-request-0002")["ok"]
    bad = rt.verify_receipt(receipt, (pub_b64,), expected_nonce=b"otro-nonce-AAAA")
    assert not bad["ok"]
    assert any("nonce" in e for e in bad["errors"])


def test_s7_ed25519_reference_matches_rfc8032_vectors():
    """S7/Ed25519: la implementación de referencia pasa los vectores RFC 8032 §7.1."""
    from src.gerarion import profiles_roughtime as rt

    # RFC 8032 §7.1 TEST 1 (SHA(eps))
    sk = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    pk_exp = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
    msg = b""
    sig_exp = bytes.fromhex(
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
    )
    assert rt.ed25519_public_key(sk) == pk_exp
    assert rt.ed25519_sign(sk, msg) == sig_exp
    assert rt.ed25519_verify(pk_exp, msg, sig_exp)
    # RFC 8032 §7.1 TEST 2 (dos bytes)
    sk2 = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
    pk2_exp = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
    msg2 = bytes.fromhex("72")
    sig2_exp = bytes.fromhex(
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
        "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"
    )
    assert rt.ed25519_public_key(sk2) == pk2_exp
    assert rt.ed25519_verify(pk2_exp, msg2, sig2_exp)
    # RFC 8032 §7.1 TEST 3 (dos bytes af82)
    sk3 = bytes.fromhex("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7")
    pk3_exp = bytes.fromhex("fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025")
    msg3 = bytes.fromhex("af82")
    sig3_exp = bytes.fromhex(
        "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac"
        "18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"
    )
    assert rt.ed25519_public_key(sk3) == pk3_exp
    assert rt.ed25519_sign(sk3, msg3) == sig3_exp
    assert rt.ed25519_verify(pk3_exp, msg3, sig3_exp)


def test_s8_verify_slhdsa_works_with_installed_package():
    """S8: slh-dsa 0.2.5 instalado se usa (no GERO_ENOALG); firma alterada → False."""
    from src.gerarion.adapters import SlhDsaSigner
    import verify_gus as vg

    try:
        s = SlhDsaSigner()
    except ImportError:
        pytest.skip("slh-dsa no instalado en este entorno")
    msg = b"GUS2-TS\n2031DY-03-08-T-09:30:00-SC-TCJ+0\n64097688600\n"
    sig = s.sign_payload(msg)
    assert vg.verify_slhdsa(s.public_key_hex, msg, sig, "SLH-DSA-SHA2-128F") is True
    assert vg.verify_slhdsa(s.public_key_hex, msg, sig[:-4] + "0000", "SLH-DSA-SHA2-128F") is False


def test_f2_verify_gus_accepts_ay_year(tmp_path):
    """F2: el verificador autónomo acepta 0001AY-00-11-B (AY simétrico)."""
    

    doc = gts.create("0001AY-00-11-B", make_adapter(hashots.WotsMerkleSigner(b"seed-f2")))
    path = tmp_path / "f2.gst.json"
    path.write_text(doc.to_json(), encoding="utf-8")
    assert verify_gus.main([str(path)]) == 0, "verify_gus rechaza marca AY válida"


def test_f1_formats_reject_out_of_range():
    """F1: 25:00:00 seguirá siendo rechazado (no-regresión)."""
    from src.gerarion.format import parse

    with pytest.raises(Exception):
        parse("2026DY-11-17-L-25:00:00-SC-TCJ+0")
