# -*- coding: utf-8 -*-
"""Perfil GUS-3161: la marca GUS anclada dentro de un sello RFC 3161.

E2E local con TSA efímera (openssl ts): cero red, cero servicio externo.
Las identidades TSA viven y mueren en el proceso de test (CN marca
"NOT SECRET"; nunca se versionan). Si openssl no está disponible, todo el
módulo se omite con un mensaje explícito (NO VERIFICADO), nunca en silencio.
"""
import base64
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from gerarion import format as fmt, profiles
from gerarion.profiles_tsa import (
    SIDECAR_TYPE,
    attach_sidecar,
    gen_time_from_token,
    openssl_available,
    timestamp_reply,
    timestamp_request,
    verify_token,
)

pytestmark = pytest.mark.skipif(
    not openssl_available(), reason="openssl ts no disponible: perfil GUS-3161 no verificado"
)

TS_CANON = "2031DY-03-08-T-09:30:00-SC-TCJ+0"
TS_INSTANT = 64097688600


@pytest.fixture(scope="module")
def tsa_identity():
    """Identidad TSA efímera con EKU timeStamping (jamás una clave de producción)."""
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(
        ["openssl", "req", "-new", "-x509", "-newkey", "rsa:2048", "-nodes",
         "-keyout", str(tmp / "k.pem"), "-out", str(tmp / "c.pem"),
         "-days", "3650", "-subj", "/CN=GUS test TSA (NOT SECRET)",
         "-addext", "basicConstraints=critical,CA:false",
         "-addext", "keyUsage=critical,digitalSignature,nonRepudiation",
         "-addext", "extendedKeyUsage=critical,timeStamping"],
        check=True, capture_output=True,
    )
    return tmp / "k.pem", tmp / "c.pem"


@pytest.fixture(scope="module")
def sealed(tsa_identity):
    key_p, cert_p = tsa_identity
    data = fmt.canonical_bytes(TS_CANON, TS_INSTANT)
    req = timestamp_request(data)
    token = timestamp_reply(req, key_p.read_bytes(), cert_p.read_bytes())
    return data, token, cert_p.read_bytes()


def test_verify_token_accepts_exact_bundle(sealed):
    data, token, cert = sealed
    assert verify_token(token, data, cert) is True


def test_verify_token_rejects_tampered_bundle(sealed):
    data, token, cert = sealed
    assert verify_token(token, data + b" ", cert) is False
    assert verify_token(token, b"otro bundle", cert) is False


def test_gen_time_is_rfc3339_and_after_the_mark(sealed):
    _, token, _ = sealed
    gt = gen_time_from_token(token)
    ins = profiles.instant_from_rfc3339(gt)
    # El genTime de la TSA (ahora real) es posterior al instante sellado:
    # la TSA solo da cota de existencia superior, NUNCA la veracidad del
    # instante declarado (documentado en threat-model y .md del perfil).
    assert ins > TS_INSTANT


def test_sidecar_converts_tsa_time_to_gus_instant(sealed, tsa_identity):
    data, token, _ = sealed
    gst_json = f'{{"ts": "{TS_CANON}", "ins": {TS_INSTANT}}}'
    doc = json.loads(attach_sidecar(gst_json, token))
    assert doc["type"] == SIDECAR_TYPE
    # Coherencia del sidecar: genTime GUS == conversión GUS-3339 del genTime
    assert doc["tsa_gen_time_gus_instant"] == profiles.instant_from_rfc3339(
        doc["tsa_gen_time"]
    )
    assert doc["tsa_gen_time_gus_instant"] > TS_INSTANT
    # El token embebido en base64 es el mismo TSR (verificable con el
    # trust root TSA que el verificador declare, aquí el cert del fixture).
    token2 = base64.b64decode(doc["token_b64"])
    key_p, cert_p = tsa_identity
    assert verify_token(token2, data, cert_p.read_bytes()) is True
