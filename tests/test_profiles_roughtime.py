# -*- coding: utf-8 -*-
"""Perfil GUS-Roughtime: receipts de testigos externos ligados al anchor.

Ed25519: implementación de REFERENCIA RFC 8032 en Python puro (stdlib puro).
La derivación de clave pública se valida contra el vector normativo del RFC
8032 (TEST 2). La firma de referencia se usa solo para construir receipts de
prueba; producción = verificación contra testigos con claves validadas.
"""
import base64

import pytest

from gerarion import profiles_roughtime as rt

RFC8032_TEST2_SK = bytes.fromhex(
    "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb"
)
RFC8032_TEST2_PK = "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c"
MIDP = "2026-05-23T09:30:12Z"


@pytest.fixture(scope="module")
def witness():
    """Testigo efímero: clave privada de PRUEBA jamás versionada como secreta."""
    return bytes(range(32))


def test_ed25519_public_key_rfc8032_vector():
    assert rt.ed25519_public_key(RFC8032_TEST2_SK).hex() == RFC8032_TEST2_PK
    assert rt._point_compress(rt._G).hex().startswith("586666")


def test_ed25519_sign_verify_roundtrip_and_tamper(witness):
    pk = rt.ed25519_public_key(witness)
    sig = rt.ed25519_sign(witness, b"hello")
    assert rt.ed25519_verify(pk, b"hello", sig)
    bad = bytearray(sig)
    bad[10] ^= 1
    assert not rt.ed25519_verify(pk, b"hello", bytes(bad))
    assert not rt.ed25519_verify(pk, b"hellp", sig)


def test_receipt_ok_and_window(witness):
    r = rt.make_receipt(b"A" * 32, MIDP, 3, witness)
    res = rt.verify_receipt(r, [r["pubkey_b64"]])
    assert res["ok"]
    ins = rt._g3339.instant_from_rfc3339(MIDP)
    assert res["window"] == (ins - 3, ins + 3)


def test_receipt_rejects_tampered_signature(witness):
    r = rt.make_receipt(b"A" * 32, MIDP, 3, witness)
    r2 = dict(r)
    r2["sig_b64"] = r["sig_b64"][:-4] + "AAAA"
    assert not rt.verify_receipt(r2, [r["pubkey_b64"]])["ok"]


def test_receipt_rejects_field_not_covered_by_signature(witness):
    r = rt.make_receipt(b"A" * 32, MIDP, 3, witness)
    r2 = dict(r)
    r2["midpoint_rfc3339"] = "2026-05-23T10:00:00Z"
    assert not rt.verify_receipt(r2, [r["pubkey_b64"]])["ok"]


def test_receipt_untrusted_testigo_fails(witness):
    r = rt.make_receipt(b"A" * 32, MIDP, 3, witness)
    res = rt.verify_receipt(r, [])
    assert not res["ok"]
    assert "trust root" in res["errors"][0]


def test_anchor_boundary_coherence(witness):
    r = rt.make_receipt(b"A" * 32, MIDP, 3, witness)
    res = rt.verify_receipt(r, [r["pubkey_b64"]])
    a = rt.bind_anchor(r)
    hi = res["window"][1]
    assert rt.verify_anchor(a, [r["pubkey_b64"]], hi)["ok"]
    assert not rt.verify_anchor(a, [r["pubkey_b64"]], hi + 1)["ok"]


def test_anchor_nonce_binds_to_bundle(witness):
    """Anti-replay: el nonce es función de los bytes del bundle sellado."""
    import hashlib
    import json
    from gerarion import format as fmt

    instant = rt._g3339.instant_from_rfc3339(MIDP)
    canon = "2031DY-03-08-T-09:30:00-SC-TCJ+0"
    bundle = fmt.canonical_bytes(canon, instant)
    nonce = hashlib.sha256(bundle).digest()
    r = rt.make_receipt(nonce, MIDP, 3, witness)
    rid = rt.verify_receipt(r, [r["pubkey_b64"]])
    assert rid["ok"]
    assert rid["nonce"] == nonce.hex()
