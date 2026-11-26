# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Pruebas de endurecimiento: JCS (RFC 8785), GST v2 y firma híbrida.

Cubre:
- Vectores de canonicalización del RFC 8785 (strings, números, orden UTF-16).
- GST v2: emisión/verificación positiva, event_hash obligatorio, anti-replay,
  anti-rollback (seq y reloj), persistencia del ReplayGuard.
- Firma híbrida Ed25519 + ML-DSA: anti-downgrade estructural (quitar o
  degradar cualquiera de las ramas invalida el sobre).
- Precisión sub-segundo: límites del campo `nanos` separado (0..999_999_999).
"""

import json
import pytest

from gerarion import calendar as cal
from gerarion import gts
from gerarion import tai
from gerarion.adapters import Ed25519Signer, HybridSigner, HybridVerifier
from gerarion.format import parse as fmt_parse
from gerarion.jcs import JcsError, canonical_bytes, dumps

mldsa_skip = pytest.importorskip(
    "cryptography.hazmat.primitives.asymmetric.mldsa"
)

# ---------------------------------------------------------------- JCS


def test_jcs_vector_rfc8785_completo():
    """Vector de prueba del §genérico del RFC 8785 (input y salida textuales)."""
    raw_input = r"""{
  "numbers": [333333333.33333329, 1E30, 4.50, 2e-3, 0.000000000000000000000000001],
  "string": "\u20ac$\u000F\u000aA'\u0042\u0022\u005c\\\"\/",
  "literals": [null, true, false]
}"""
    expected = (
        '{"literals":[null,true,false],'
        '"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
        '"string":"€$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}'
    )
    assert dumps(json.loads(raw_input)) == expected


def test_jcs_vector_rfc8785_utf8_bytes():
    raw = {"string": "\u20ac$\u000f\nA'B\"\\\\\"/"}
    expected = '"string":"\u20ac$\\u000f\\nA\'B\\"\\\\\\\\\\"/"'
    assert canonical_bytes(raw).decode("utf-8") == "{" + expected + "}"


def test_jcs_numeros_frontera_es6():
    assert dumps([0, -0, 0.0, -0.0]) == "[0,0,0,0]"
    assert dumps([1e21, 1e21 + 1]) == "[1e+21,1e+21]"  # >= 1e21 usa exponente
    assert dumps([1e-7]) == "[1e-7]"
    assert dumps([-6.1e-7]) == "[-6.1e-7]"
    assert dumps([1.0]) == "[1]"
    # >= 1e21 pasa a notación exponencial; 1234500000000000000000.0 → 1.2345e+21
    assert dumps([1234500000000000000000.0]) == "[1.2345e+21]"


def test_jcs_orden_claves_utf16():
    # El orden es por unidades de código UTF-16, no por punto Unicode:
    # U+FF03 (-) vs pares de sustitutos... claves ASCII bastan aquí; el caso
    # crítico clásico: "\u0fb1" (una unidad) antes que "\U0001d7ee" (par).
    obj = {"\U0001d7ee": 1, "\u0fb1": 2, "a": 3}
    assert (
        dumps(obj)
        == '{"a":3,"\u0fb1":2,"\U0001d7ee":1}'
    )


def test_jcs_rechaza_nan_inf_sustituto():
    with pytest.raises(JcsError):
        dumps(float("nan"))
    with pytest.raises(JcsError):
        dumps(float("inf"))
    with pytest.raises(JcsError):
        dumps("\ud800")


def test_jcs_booleans_no_son_numeros():
    assert dumps({"a": True, "b": False}) == '{"a":true,"b":false}'


# ------------------------------------------------- nanos (precisión)


@pytest.mark.parametrize("mal", [-1, 1_000_000_000, 1.5, "x", None, True])
def test_nanos_fuera_de_rango_rechazado(mal):
    with pytest.raises(Exception):
        cal.validate_nanos(mal)


def test_nanos_limites_aceptados():
    assert cal.validate_nanos(0) == 0
    assert cal.validate_nanos(999_999_999) == 999_999_999


def test_nanos_max_constante():
    assert cal.NANOS_MAX == 999_999_999


def test_marca_con_fraccion_parsea_nanos_exactos():
    p = fmt_parse("2031DY-03-08-T-09:30:00.250-SC-TCJ+0")
    assert p.nanos == 250_000_000
    p2 = fmt_parse("2031DY-03-08-T-09:30:00.999999999-SC-TCJ+0")
    assert p2.nanos == 999_999_999
    p3 = fmt_parse("2031DY-03-08-T-09:30:00-SC-TCJ+0")
    assert p3.nanos == 0


def test_marca_con_fraccion_de_10_digitos_rechazada():
    with pytest.raises(Exception):
        fmt_parse("2031DY-03-08-T-09:30:00.1234567890-SC-TCJ+0")


def test_marca_con_nanos_negativos_rechazada():
    # '-1' tras el segundo es interpretado como sintaxis, no como fracción
    # negativa; el campo nunca puede ser negativo (defensa en profundidad).
    with pytest.raises(Exception):
        fmt_parse("2031DY-03-08-T-09:30:00.-1-SC-TCJ+0")
    with pytest.raises(Exception):
        cal.validate_nanos(-1)


# ------------------------------------------------------------ GST v2

TS = "2031DY-03-08-T-09:30:00-SC-TCJ+0"
EVENT_HASH = "sha256:" + "ab" * 32


def verify_v2(envelope, **kwargs):
    return gts.verify_v2(envelope, expected_event_hash=EVENT_HASH, **kwargs)


@pytest.fixture()
def signer():
    return HybridSigner(seed_classical=bytes(range(32)), seed_pqc=bytes(range(32, 64)))


def test_gst_v2_ciclo_completo_valido(signer):
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=1)
    assert env["gst_version"] == "2.0"
    assert env["scale"] == "TCJ"
    assert env["alg"] == "HYBRID-ED25519-ML-DSA-65"
    res = verify_v2(dict(env))
    assert res["ok"] is True and res["state"] == "VALID"


def test_gst_v2_dominio_y_mensaje_canonico(signer):
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=1)
    payload = {k: v for k, v in env.items() if k != "sigs"}
    msg = gts.gst_v2_message(payload)
    assert msg.startswith(gts.GST_V2_DOMAIN)
    assert msg[len(gts.GST_V2_DOMAIN):] == canonical_bytes(payload)


def test_gst_v2_descriptor_hybrid_dentro_del_payload(signer):
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=1)
    # El descriptor vive en el payload firmado: quitarlo rompe la firma dual.
    for field in ("alg", "alg_classical", "alg_pqc", "kid_classical", "kid_pqc"):
        assert field in env


@pytest.mark.parametrize("mal", ["", "sin-hash", "sha256:zz", "md5:" + "ab" * 16])
def test_gst_v2_rechaza_event_hash_invalido(signer, mal):
    with pytest.raises(Exception):
        gts.create_v2(TS, signer, event_hash=mal, kid="k1",
                      issuer="test", seq=1)


def test_gst_v2_sobre_sin_event_hash_rechazado(signer):
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=1)
    roto = dict(env)
    del roto["event_hash"]
    roto["sigs"] = signer.sign_payload(gts.gst_v2_message(
        {k: v for k, v in roto.items() if k != "sigs"}))
    assert verify_v2(roto)["state"] == "REJECTED"


def test_gst_v2_event_hash_alterado_rechazado(signer):
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=1)
    roto = dict(env)
    roto["event_hash"] = "sha256:" + "cd" * 32
    assert verify_v2(roto)["state"] == "REJECTED"


def test_gst_v2_replay_nonce_repetido_rechazado(signer):
    guard = gts.ReplayGuard()
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=1)
    assert verify_v2(dict(env), guard=guard)["state"] == "VALID"
    assert verify_v2(dict(env), guard=guard)["state"] == "REJECTED"
    assert "replay" in verify_v2(dict(env), guard=guard)["errors"][0]


def test_gst_v2_guardia_aisla_por_kid(signer):
    guard = gts.ReplayGuard()
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=1)
    rev1 = verify_v2(dict(env), guard=guard)
    env2 = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k2",
                         issuer="test", seq=1)
    rev2 = verify_v2(dict(env2), guard=guard)
    assert rev1["ok"] and rev2["ok"]


def test_gst_v2_rollback_seq_rechazado(signer):
    guard = gts.ReplayGuard()
    env1 = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                         issuer="test", seq=5)
    antiguo = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                            issuer="test", seq=4)
    assert verify_v2(dict(env1), guard=guard)["state"] == "VALID"
    rev = verify_v2(dict(antiguo), guard=guard)
    assert rev["state"] == "REJECTED" and "rollback" in rev["errors"][0]


def test_gst_v2_rollback_reloj_rechazado(signer):
    guard = gts.ReplayGuard()
    env1 = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                         issuer="test", seq=1)
    tarde = gts.create_v2("2031DY-03-09-T-09:30:00-SC-TCJ+0", signer,
                          event_hash=EVENT_HASH, kid="k1", issuer="test", seq=2)
    temprano = gts.create_v2("2031DY-03-07-T-09:30:00-SC-TCJ+0", signer,
                             event_hash=EVENT_HASH, kid="k1", issuer="test", seq=3)
    assert verify_v2(dict(env1), guard=guard)["ok"]
    assert verify_v2(dict(tarde), guard=guard)["ok"]
    rev = verify_v2(dict(temprano), guard=guard)
    assert rev["state"] == "REJECTED" and "rollback" in rev["errors"][0]


def test_gst_v2_guardia_persistente(tmp_path, signer):
    path = str(tmp_path / "guard.json")
    guard = gts.ReplayGuard(path)
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=1)
    assert verify_v2(dict(env), guard=guard)["ok"]
    # Un guardia nuevo que carga el mismo archivo detecta el replay.
    guard2 = gts.ReplayGuard(path)
    assert verify_v2(dict(env), guard=guard2)["state"] == "REJECTED"


def test_gst_v2_tamper_cualquier_campo_rechazado(signer):
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=1)
    for campo, valor in (("issuer", "otro"), ("seq", 99), ("nanos", 5),
                         ("policy_version", "gus-sec-vX")):
        roto = dict(env)
        roto[campo] = valor
        assert verify_v2(roto)["state"] == "REJECTED", campo


# ------------------------------------------------- híbrida (anti-downgrade)


def test_hibrida_eliminar_firma_pqc_rechazado(signer):
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=1)
    roto = dict(env)
    roto["sigs"] = {"alg": roto["sigs"]["alg"],
                    "sigs": {"ed25519": roto["sigs"]["sigs"]["ed25519"]}}
    assert verify_v2(roto)["state"] == "REJECTED"


def test_hibrida_eliminar_firma_clasica_rechazado(signer):
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=1)
    roto = dict(env)
    roto["sigs"] = {"alg": roto["sigs"]["alg"],
                    "sigs": {"mldsa": roto["sigs"]["sigs"]["mldsa"]}}
    assert verify_v2(roto)["state"] == "REJECTED"


def test_hibrida_alterar_firma_clasica_rechazado(signer):
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=1)
    roto = dict(env)
    roto["sigs"]["sigs"]["ed25519"] = roto["sigs"]["sigs"]["ed25519"][:-4] + "0000"
    assert verify_v2(roto)["state"] == "REJECTED"


def test_hibrida_degradar_alg_rechazado(signer):
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=1)
    roto = dict(env)
    roto["alg"] = "HYBRID-ED25519-ML-DSA-44"
    assert verify_v2(roto)["state"] == "REJECTED"


def test_hibrida_verifier_exige_ambas(signer):
    msg = b'{"a":1}'
    sig_blob = signer.sign_payload(msg)
    ok = HybridVerifier.verify(signer.public_key_hex,
                               signer.public_key_pqc_hex, msg, sig_blob,
                               signer.alg)
    assert ok is True
    par = sig_blob["sigs"]
    assert HybridVerifier.verify(signer.public_key_hex,
                                 signer.public_key_pqc_hex, msg,
                                 {"alg": signer.alg, "sigs": {}},
                                 signer.alg) is False
    for parcial in ({"ed25519": par["ed25519"]}, {"mldsa": par["mldsa"]}):
        assert HybridVerifier.verify(
            signer.public_key_hex, signer.public_key_pqc_hex, msg,
            {"alg": signer.alg, "sigs": parcial}, signer.alg) is False


def test_hibrida_parte_clasica_sola_no_sirve(signer):
    """Un atacante sin ML-DSA no puede fabricar un sobre v2 verificable."""
    solo_clasico = Ed25519Signer(bytes(range(32)))
    payload = {"ts": TS, "alg": "HYBRID-ED25519-ML-DSA-65"}
    msg = gts.GST_V2_DOMAIN + canonical_bytes(payload)
    suplantado = {
        "alg": "HYBRID-ED25519-ML-DSA-65",
        "pub_classical": solo_clasico.public_key_hex,
        "pub_pqc": signer.public_key_pqc_hex,
        "sigs": {"alg": "HYBRID-ED25519-ML-DSA-65",
                 "sigs": {"ed25519": solo_clasico.sign_payload(msg),
                          "mldsa": "00" * 16}},
    }
    payload["pub_classical"] = suplantado["pub_classical"]
    payload["pub_pqc"] = suplantado["pub_pqc"]
    msg = gts.GST_V2_DOMAIN + canonical_bytes(payload)
    suplantado["sigs"]["sigs"]["ed25519"] = solo_clasico.sign_payload(msg)
    assert HybridVerifier.verify(
        suplantado["pub_classical"], suplantado["pub_pqc"], msg,
        suplantado["sigs"], "HYBRID-ED25519-ML-DSA-65") is False


# ------------------------------------------- puente TAI-UTC versionado


def test_tai_utc_tabla_metadatos():
    info = tai.tai_utc_table_info()
    assert info["table_version"] == "IERS-C-2026.1"
    assert info["valid_until_unix"] == 1_809_129_600
    assert info["smear_policy"] == "reject"


def test_tai_utc_checked_vigencia():
    offset, extra = tai.tai_minus_utc_checked(1_700_000_000)
    assert offset == tai.tai_minus_utc(1_700_000_000)
    assert extra is False  # dentro de la ventana verificada


def test_tai_utc_checked_extrapolacion_marcada():
    _, extra = tai.tai_minus_utc_checked(tai.TAI_UTC_VALID_UNTIL_UNIX + 86_400)
    assert extra is True  # pasada la vigencia: advertencia de extrapolación


# ----------------------------------------- JCS binary64 (adenda v3.1.1)

def test_jcs_entero_limite_supero_binary64_aceptado():
    from gerarion.jcs import BINARY64_MAX_INT, BINARY64_MIN_INT
    assert BINARY64_MAX_INT == 9_007_199_254_740_991
    assert BINARY64_MIN_INT == -9_007_199_254_740_991
    # 2^53 - 1: el límite exacto interoperable de Number, VÁLIDO.
    assert dumps(BINARY64_MAX_INT) == "9007199254740991"
    assert dumps(BINARY64_MIN_INT) == "-9007199254740991"


@pytest.mark.parametrize("value", [9_007_199_254_740_992, 9_007_199_254_740_993,
                                   -(9_007_199_254_740_992),
                                   2**63 - 1, 2**63])
def test_jcs_entero_fuera_de_binary64_rechazado(value):
    # RFC 8785 serializa TODO número como Number de ECMAScript (binary64):
    # a partir de 2^53 los dígitos bajos no son interoperables. El serializador
    # rechaza (nunca redondea en silencio); el productor debe enviar str(value).
    with pytest.raises(JcsError):
        dumps(value)


def test_jcs_entero_64bit_viaja_como_cadena_decimal():
    # Patrón recomendado para valores de 64 bits en sobres GST v2.
    big = 2**63 - 1
    assert dumps({"ins": str(big)}) == ('{"ins":"9223372036854775807"}')


def test_gst_v2_campos_internos_dentro_del_rango_binary64(signer):
    # Los campos enteros del sobre GST v2 (ins, nanos, seq) se serializan
    # sin error: sus dominios quedan dentro de ±(2^53-1). Se chequea el
    # rango real de `ins` (horizonte calendario) y `seq` (contador).
    env = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                        issuer="test", seq=2**53 - 1)
    assert env["ins"] <= 9_007_199_254_740_991
    assert env["seq"] == 9_007_199_254_740_991
    assert 0 <= env.get("nanos", 0) <= cal.NANOS_MAX
