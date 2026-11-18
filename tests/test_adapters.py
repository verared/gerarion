# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Tests de los adaptadores de firma (hash-only de referencia + SLH-DSA FIPS 205)."""

from __future__ import annotations

import pytest

from gerarion import gts
from gerarion.adapters import HashRefSigner, SlhDsaSigner
from gerarion.hashots import WotsMerkleSigner

slhdsa = pytest.importorskip("slhdsa", reason="requiere pip install slh-dsa")


# Par fijo de prueba (SLH-DSA-SHA2-128F): digest de 96 bytes generado una vez
# con KeyPair.gen() y embebido para reproducibilidad. Las claves de producción
# JAMAS se embeben; esta es exclusivamente vector de test.
TEST_KEYPAIR_128F = (
    "f2fa226fd9532e51b5c71a86a8d364a90d7a4debf04026e73f6e7e4ec984c1e4"
    "fd0617195aca3d9897d386e871956f49a5a4c15243fa86f08fe36172de220789"
    "f2fa226fd9532e51b5c71a86a8d364a90d7a4debf04026e73f6e7e4ec984c1e4"
)


@pytest.fixture(scope="module")
def slh_signer():
    return SlhDsaSigner("SLH-DSA-SHA2-128F", digest=bytes.fromhex(TEST_KEYPAIR_128F))


def test_slhdsa_gst_create_and_verify(slh_signer):
    doc = gts.create("2031DY-03-08-T-09:30:00-SC-TCJ+0", slh_signer)
    assert doc.alg == "SLH-DSA-SHA2-128F"
    result = gts.verify(doc)
    assert result["ok"], result["errors"]


def test_slhdsa_tamper_detected(slh_signer):
    doc = gts.create("2031DY-03-08-T-09:30:00-SC-TCJ+0", slh_signer)
    doc.instant += 60
    assert not gts.verify(doc)["ok"]


def test_slhdsa_keypair_from_digest_is_stable():
    a = SlhDsaSigner("SLH-DSA-SHA2-128F", digest=bytes.fromhex(TEST_KEYPAIR_128F))
    b = SlhDsaSigner("SLH-DSA-SHA2-128F", digest=bytes.fromhex(TEST_KEYPAIR_128F))
    assert a.public_key_hex == b.public_key_hex


def test_slhdsa_wrong_digest_length():
    with pytest.raises(ValueError):
        SlhDsaSigner("SLH-DSA-SHA2-128F", digest=bytes(16))


def test_hash_adapter_wrapping():
    signer = WotsMerkleSigner(seed=b"\x07" * 32, height=2)
    adapter = HashRefSigner(signer)
    doc = gts.create("2031DY-03-08-T", adapter)
    assert gts.verify(doc)["ok"]


def test_unknown_param_rejected():
    with pytest.raises(ValueError):
        SlhDsaSigner("SLH-DSA-SHA2-999Z")
