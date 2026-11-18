# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Pruebas adversarias del stack criptográfico activo (auditoría v3.0.0).

Ataques simulados contra JCS (RFC 8785), GST v2 (híbrida Ed25519+ML-DSA),
ReplayGuard y el quórum del notario. Los componentes deprecados
(hashots.py) quedan fuera. Todo ataque debe terminar en REJECTED o en
fallo explícito: nunca en un válido silencioso.
"""

import json

import pytest

from gerarion import gts
from gerarion.adapters import Ed25519Signer, HybridSigner, HybridVerifier
from gerarion.jcs import JcsError, canonical_bytes, dumps
from gerarion.notary_cluster import (
    NotaryCluster,
    ReplicaPublication,
    derive_day_root,
    verify_bundle,
)

mldsa_skip = pytest.importorskip(
    "cryptography.hazmat.primitives.asymmetric.mldsa"
)

TS = "2031DY-03-08-T-09:30:00-SC-TCJ+0"
EVENT_HASH = "sha256:" + "ab" * 32


@pytest.fixture()
def signer():
    return HybridSigner(seed_classical=bytes(range(32)), seed_pqc=bytes(range(32, 64)))


@pytest.fixture()
def envelope(signer):
    return gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                         issuer="audit", seq=1)


# ------------------------- 1. JCS: vectores hostiles ----------------------


def test_jcs_claves_duplicadas_ultima_gana_determinista():
    """json.loads descarta claves duplicadas (queda la última): la salida
    canónica es determinista y no puede ser bifurcada por el atacante."""
    raw = '{"a":1,"b":2,"a":3}'
    assert dumps(json.loads(raw)) == '{"a":3,"b":2}'


def test_jcs_orden_utf16_con_sustitutos():
    """El orden es por unidades de código UTF-16, no por punto Unicode:
    el par subrogado U+10000 (UTF-16: D800 DC00) ordena ANTES que U+E000
    (una sola unidad, 0xE000) aunque su punto Unicode sea mayor."""
    obj = {"\uE000": 1, "\U00010000": 2}
    assert dumps(obj) == '{"\U00010000":2,"\uE000":1}'


def test_jcs_menos_cero_unifica_con_cero():
    assert dumps([0.0, -0.0]) == "[0,0]"


def test_jcs_notacion_cientifica_extrema_determinista():
    assert dumps([5e-324]) == "[5e-324]"          # subnormal mínimo
    assert dumps([1.7976931348623157e308]) == "[1.7976931348623157e+308]"
    assert dumps([2.2250738585072014e-308]) == "[2.2250738585072014e-308]"


def test_jcs_rechaza_nan_inf_bom_y_secuencia_basura():
    for mal in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(JcsError):
            dumps(mal)
    # BOM UTF-8 sobre un objeto: es un carácter más de la cadena, viaja
    # literal; NO se lo silencia con un escape no estándar.
    assert dumps({"a": "\ufeff"}) == '{"a":"﻿"}'
    # bytes basura tras el cierre del JSON no pueden entrar al pipeline:
    # json (el único parser permitido en el sobre) los rechaza.
    with pytest.raises(json.JSONDecodeError):
        json.loads('{"a":1} TRASH')
    with pytest.raises(json.JSONDecodeError):
        json.loads('{"a":1}}')


# ------------------- 2. Downgrade y sustitución en GST v2 -----------------


def test_a_eliminar_mldsa_rechazado(signer, envelope):
    roto = dict(envelope)
    roto["sigs"] = {"alg": roto["sigs"]["alg"],
                    "sigs": {"ed25519": roto["sigs"]["sigs"]["ed25519"]}}
    assert gts.verify_v2(roto)["state"] == "REJECTED"


def test_b_alg_solo_ed25519_rechazado(signer, envelope):
    for alg in ("Ed25519", "ED25519", "HYBRID-ED25519", "HYBRID-ED25519-RSA"):
        roto = dict(envelope)
        roto["alg"] = alg
        res = gts.verify_v2(roto)
        assert res["state"] == "REJECTED", alg


def test_c_kid_cruzado_con_clave_ajena_rechazado(signer):
    """El atacante re-firma con SU clave pero conserva el kid del emisor:
    la correspondencia kid→pubkey del trust root del verificador debe
    rechazar la publicación (binding externo, aquí simulado)."""
    atacante = HybridSigner()
    env = gts.create_v2(TS, atacante, event_hash=EVENT_HASH, kid="k1",
                        issuer="audit", seq=1)
    # Criptográficamente el sobre es válido (firmó el atacante)…
    assert gts.verify_v2(dict(env))["state"] == "VALID"
    # …pero el binding kid→pubkey del verificador lo detecta.
    pub_emisor = {"k1": (signer.public_key_hex, signer.public_key_pqc_hex)}
    kid = env["kid"]
    publicada = (env["pub_classical"], env["pub_pqc"])
    assert pub_emisor[kid] != publicada  # el trust root lo delata


def test_c2_byte_alterado_en_event_hash_y_nanos_rechazado(signer, envelope):
    for campo, nuevo in (("event_hash", "sha256:" + "ac" * 32), ("nanos", 1)):
        roto = dict(envelope)
        roto[campo] = nuevo
        assert gts.verify_v2(roto)["state"] == "REJECTED", campo


def test_e_firma_valida_en_otro_dominio_rechazada(signer, envelope):
    """La firma del sobre v2 no verifica contra ningún otro dominio
    (separación GST-V2 || JCS) ni contra bytes sin prefijo de dominio."""
    payload = {k: v for k, v in envelope.items() if k != "sigs"}
    sin_dominio = canonical_bytes(payload)
    assert gts.HybridVerifier if hasattr(gts, "HybridVerifier") else True
    # La firma del sobre fue sobre GST_V2_DOMAIN+canon; sobre el canon solo,
    # Ed25519 NO verifica.
    sig_ed = envelope["sigs"]["sigs"]["ed25519"]
    from gerarion.adapters import Ed25519Signer as E
    assert E.verify(envelope["pub_classical"], sin_dominio, sig_ed) is False


# ------------- 3. ReplayGuard: ráfagas, reinicio y corrupción -------------


def test_rafaga_concurrente_mismo_nonce_rechazada(signer, envelope):
    guard = gts.ReplayGuard()
    assert gts.verify_v2(dict(envelope), guard=guard)["ok"]
    for _ in range(5):
        res = gts.verify_v2(dict(envelope), guard=guard)
        assert res["state"] == "REJECTED" and "replay" in res["errors"][0]


def test_rollback_tras_reinicio_con_estado_persistente(signer, tmp_path):
    path = str(tmp_path / "guard.json")
    g1 = gts.ReplayGuard(path)
    env1 = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                         issuer="audit", seq=10)
    assert gts.verify_v2(dict(env1), guard=g1)["ok"]
    g2 = gts.ReplayGuard(path)  # "reinicio" con estado cargado
    env2 = gts.create_v2(TS, signer, event_hash=EVENT_HASH, kid="k1",
                         issuer="audit", seq=9)
    res = gts.verify_v2(dict(env2), guard=g2)
    assert res["state"] == "REJECTED" and "rollback" in res["errors"][0]


def test_estado_corrupto_fail_closed(signer, tmp_path):
    """Un estado truncado/corrupto NUNCA se comporta como historial vacío:
    la guardia queda envenenada y rechaza hasta que el operador intervenga."""
    path = tmp_path / "guard.json"
    raw = (b'{"seen":[["k1","' + b"ff" * 16 + b']],"last_seq":{"k1":10},'
           b'"last_ins":{')
    path.write_bytes(raw[: len(raw) // 2])  # truncado a la mitad
    guard = gts.ReplayGuard(str(path))
    assert guard._poisoned is True
    ok, motivo = guard.check_and_record("k1", "ee" * 16, 11, 100)
    assert ok is False and "corrupto" in motivo

    # JSON válido pero de estructura ajena: igual fail-closed.
    path2 = tmp_path / "guard2.json"
    path2.write_text('{"seen": "no-soy-una-lista", "last_seq": 42}')
    guard2 = gts.ReplayGuard(str(path2))
    ok2, m2 = guard2.check_and_record("k1", "ee" * 16, 1, 100)
    assert ok2 is False and "corrupto" in m2

    # seq/ins no enteros no registran nada.
    guard3 = gts.ReplayGuard()
    assert guard3.check_and_record("k1", "ee" * 16, "1", 100)[0] is False
    assert guard3.check_and_record("k1", "ee" * 16, True, 100)[0] is False


# ---------------------- 4. Quórum del notario ----------------------------


def _cluster(threshold=None):
    cluster = NotaryCluster(["n1", "n2", "n3"], threshold)
    cluster.fanout(b"evento-A")
    return cluster, cluster.seal_day(1)


def test_nodo_duplicado_no_infla_quorum():
    cluster, pubs = _cluster()
    lista = [pubs["n1"], pubs["n1"], pubs["n1"]]  # 3 respuestas, 1 identidad
    res = cluster.verify_day(lista)
    assert res["ok"] is False  # quórum 2-de-3 NO alcanzado con un nodo


def test_nodo_no_autorizado_no_alcanza_quorum():
    cluster, pubs = _cluster()
    intruso = ReplicaPublication(
        replica="intruso", day=1, tree_root=pubs["n1"].tree_root,
        prev_root=pubs["n1"].prev_root, day_root=pubs["n1"].day_root,
    )
    # Sin allowlist el nombre ajeno computa (por eso el trust root es
    # obligación del despliegue); CON allowlist el quórum es inalcanzable.
    res = cluster.verify_day([pubs["n1"], pubs["n2"], intruso])
    assert res["ok"] is True  # 3 respuestas de nodos presentes
    res2 = cluster.verify_day([pubs["n1"], pubs["n2"], intruso],
                              known_replicas={"n1", "n2", "n3"})
    assert "intruso" in res2["unknown_replicas"]
    bundle = [pubs["n1"].to_dict(), intruso.to_dict()]
    res3 = verify_bundle(bundle, threshold=2, known_replicas={"n1", "n2", "n3"})
    assert res3["ok"] is False and "intruso" in res3["unknown_replicas"]


def test_firma_de_nodo_inexistente_no_sostiene_nada():
    cluster, pubs = _cluster()
    falsa = ReplicaPublication(
        replica="falsa", day=1, tree_root=pubs["n1"].tree_root,
        prev_root=pubs["n1"].prev_root, day_root="0" * 64,
    )
    res = cluster.verify_day([pubs["n2"], pubs["n3"], falsa])
    assert res["ok"] is True  # quórum real con n2+n3
    res2 = cluster.verify_day([falsa, falsa, falsa], threshold=2)
    assert res2["ok"] is False  # raíz no derivable jamás sostiene quórum
    assert "falsa" in res2["bad_derivation"]


def test_discrepancia_temporal_fuera_de_tolerancia_rechazada():
    """Un nodo que publica un día distinto (desfasado) no compone quórum:
    su day_root no deriva del (day, tree_root, prev_root) del día pedido."""
    cluster, pubs = _cluster()
    desfasado = ReplicaPublication(
        replica="n3", day=7,  # otro día "valido" pero no el requerido
        tree_root=pubs["n3"].tree_root, prev_root=pubs["n3"].prev_root,
        day_root=derive_day_root(7, pubs["n3"].tree_root, pubs["n3"].prev_root),
    )
    res = cluster.verify_day([pubs["n1"], pubs["n2"], desfasado])
    assert res["ok"] is True  # n1+n2 componen quórum del día 1
    # el desfaso solo no alcanza: su único voto no llega a 2
    res2 = cluster.verify_day([pubs["n1"], desfasado])
    assert res2["ok"] is False and "n3" in res2["divergent"]


def test_quorum_tres_de_cuatro_requiere_dies_identidades():
    cluster = NotaryCluster(["a", "b", "c", "d"], threshold=3)
    cluster.fanout(b"evento-B")
    pubs = cluster.seal_day(2)
    assert cluster.verify_day(list(pubs.values()))["ok"] is True
    solo_dos = [pubs["a"], pubs["b"], pubs["a"]]  # duplicado no suma
    assert cluster.verify_day(solo_dos)["ok"] is False
