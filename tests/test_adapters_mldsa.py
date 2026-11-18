# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Pruebas del adaptador ML-DSA (FIPS 204) — opcional, extra `pqc`.

Se omiten con skip si el paquete `cryptography` (>= 47, módulo mldsa) no
está disponible: igual que el patrón de los tests SLH-DSA.
"""

import pytest

from gerarion.adapters import MlDsaSigner
from gerarion.format import CANONICAL_CTX

mldsa = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.mldsa")

SEED_A = bytes(range(32))          # determinista para reproducibilidad en tests
SEED_B = bytes(range(32, 64))

MSG = b'{"alg":"ML-DSA-65","ts":"2031DY-03-08-T-09:30:00-SC-TCJ+0"}'


def test_ml_dsa_roundtrip_determinista():
    s1 = MlDsaSigner("ML-DSA-65", seed=SEED_A)
    s2 = MlDsaSigner("ML-DSA-65", seed=SEED_A)
    assert s1.public_key_hex == s2.public_key_hex
    sig = s1.sign_payload(MSG)
    assert MlDsaSigner.verify(s1.public_key_hex, MSG, sig, "ML-DSA-65") is True


def test_ml_dsa_rechaza_payload_alterado():
    s = MlDsaSigner("ML-DSA-65", seed=SEED_A)
    sig = s.sign_payload(MSG)
    otro = MSG.replace(b"09:30:00", b"09:30:01")
    assert MlDsaSigner.verify(s.public_key_hex, otro, sig, "ML-DSA-65") is False


def test_ml_dsa_rechaza_clave_distinta_y_parametro_desconocido():
    s = MlDsaSigner("ML-DSA-65", seed=SEED_A)
    otro = MlDsaSigner("ML-DSA-65", seed=SEED_B)
    sig = s.sign_payload(MSG)
    assert MlDsaSigner.verify(otro.public_key_hex, MSG, sig, "ML-DSA-65") is False
    assert MlDsaSigner.verify(s.public_key_hex, MSG, sig, "ML-DSA-1024") is False


def test_ml_dsa_parametros_disponibles_y_semilla_invalida():
    for p in ("ML-DSA-44", "ML-DSA-65", "ML-DSA-87"):
        assert MlDsaSigner(p, seed=SEED_A).alg == p
    with pytest.raises(ValueError):
        MlDsaSigner("ML-DSA-65", seed=b"corta")


def test_ml_dsa_contexto_de_dominio_gus2_ts():
    """Sin el contexto GUS2-TS la verificación debe fallar (dominio separado)."""
    s = MlDsaSigner("ML-DSA-65", seed=SEED_A)
    sig_hex = s.sign_payload(MSG)
    ctx = CANONICAL_CTX.encode("utf-8")
    assert ctx == b"GUS2-TS"
    pub = mldsa.MLDSA65PublicKey.from_public_bytes(bytes.fromhex(s.public_key_hex))
    with pytest.raises(Exception):
        pub.verify(bytes.fromhex(sig_hex), MSG, b"otro-contexto")


def test_gst_completo_con_ml_dsa_roundtrip():
    """GST end-to-end: create + verify con ML-DSA, y detección de tampering."""
    from gerarion import gts

    s = MlDsaSigner("ML-DSA-65", seed=SEED_A)
    doc = gts.create("2031DY-03-08-T-09:30:00-SC-TCJ+0", s)
    assert doc.alg == "ML-DSA-65"
    assert doc.instant == 64097688600
    assert gts.verify(doc)["ok"] is True
    doc.instant += 1
    assert gts.verify(doc)["ok"] is False
