#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
# -*- coding: utf-8 -*-
"""verify_gus.py — verificador monolítico de marcas GUS, autocontenido.

UNICO ARCHIVO. Solo stdlib. NO importar el paquete `gerarion`: este script
re-implementa (1) la aritmética del núcleo del calendario, (2) el formato
canónico AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O], (3) la verificación de firma
hash-only (WOTS16 + Merkle, SHA-256) y (4) el anclaje del notario. Es el
artefacto descargable para que un tercero SIN el repositorio verifique una
GST con:

    python3 verify_gus.py marca.gst.json
    python3 verify_gus.py marca.gst.json --no-anchor   (solo formato+firma)

Salida: "OK ..." y exit 0 si TODO verifica; errores GERO_* y exit != 0 si
cualquier cosa falla. Conformancia: una implementación es conforme si y
solo si pasa el vector set (vectors/gus-normative-003.json); este
verificador comparte esa semántica, no la produce.

ADVERTENCIA: la firma hash-only WOTS16-MERKLE-REF es la de referencia del
estándar, SOLO pruebas/referencia; producción = SLH-DSA (FIPS 205). Si la
GST declara un parameter set SLH-DSA, este verificador lo valida vía el
paquete opcional `slh-dsa` si está instalado; sin él, reporta GERO_ENOALG
(NO VERIFICADO, nunca falso OK).
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import re
import sys

# ---------------------------------------------------------------------------
# Núcleo del calendario (spec GUS 2.0 §2-§4) — enteros exactos
# ---------------------------------------------------------------------------

ORIGIN_JDN = 1_719_313            # 1 Keuphero año 0 DY = 21 de marzo de -5
SOLAR_DELTA_UD = 1_242_190        # microdías/año común
SOLAR_THRESHOLD_UD = 7_000_000
YEAR_COMMON_DAYS = 364            # 12x30 + Tempalum 4
YEAR_GRAN_DAYS = 371              # 12x30 + Tempalum 11 (Gran Tempalum)
MONTH_BLOCK_DAYS = 360
SECS_PER_DAY = 86_400
TS_CONTEXT = "GUS2-TS"

WEEKDAY_ABBREVS = ["S", "L", "M", "A", "T", "V", "B"]

TIMESTAMP_RE = re.compile(
    r"^(?P<year>\d{1,4})(?P<era>DY|AY)"
    r"[-.](?P<month>\d{1,2})[-.](?P<day>\d{1,2})[-.]"
    r"(?P<weekday>[SLMATVB])"
    r"(?:[-](?P<hour>\d{1,2}):(?P<minute>\d{1,2}):(?P<second>\d{1,2})"
    r"[-](?P<cycle>SC|LC)"
    r"[-]TCJ(?P<offset>[+-]\d{1,2}))?$"
)


def jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32_045


def is_gran_tempalum(year: int) -> bool:
    """Regla simétrica e infinita (spec GUS 2.1 §3), bit a bit idéntica al
    núcleo (r = residuo euclidiano al inicio del año; GT <=> r + S >= U)."""
    r_y = ((year % SOLAR_THRESHOLD_UD) + SOLAR_THRESHOLD_UD) % SOLAR_THRESHOLD_UD
    r = (r_y * SOLAR_DELTA_UD) % SOLAR_THRESHOLD_UD
    return r + SOLAR_DELTA_UD >= SOLAR_THRESHOLD_UD


def year_length(year: int) -> int:
    return YEAR_GRAN_DAYS if is_gran_tempalum(year) else YEAR_COMMON_DAYS


def year_start_day_index(year: int) -> int:
    """O(1), simétrico: q, r = divmod piso(year, U); gt = q*S + (r*S)//U."""
    q = year // SOLAR_THRESHOLD_UD          # división piso (trunca hacia -inf)
    r = year - q * SOLAR_THRESHOLD_UD
    gt_count = q * SOLAR_DELTA_UD + (r * SOLAR_DELTA_UD) // SOLAR_THRESHOLD_UD
    return year * YEAR_COMMON_DAYS + 7 * gt_count


def locate(day_index: int):
    if day_index >= 0:
        year, rest = 0, day_index
        while True:
            length = year_length(year)
            if rest < length:
                return year, rest
            rest -= length
            year += 1
    years_back = (-day_index + YEAR_COMMON_DAYS - 1) // YEAR_COMMON_DAYS
    year = -years_back
    return year, day_index - year_start_day_index(year)


def from_gerarion(year: int, month: int, day: int) -> int:
    """Índice de día; los errores GERO_* viajan como ValueError."""
    if month == 0:
        max_day = 11 if year_length(year) == YEAR_GRAN_DAYS else 4
        if day < 1 or day > max_day:
            code = "GERO_ETEMPALUM"
            raise ValueError(code)
    elif 1 <= month <= 12:
        if day < 1 or day > 30:
            raise ValueError("GERO_EINVAL")
    else:
        raise ValueError("GERO_EINVAL")
    offset = (MONTH_BLOCK_DAYS if month == 0 else (month - 1) * 30) + (day - 1)
    return year_start_day_index(year) + offset


def cycle_of(hour: int) -> str:
    if not 0 <= hour <= 23:
        raise ValueError("GERO_EINVAL")
    return "SC" if 6 <= hour < 18 else "LC"


# ---------------------------------------------------------------------------
# Formato canónico
# ---------------------------------------------------------------------------


class BadTimestamp(ValueError):
    """Error de formato con código GERO_*."""


def parse_canonical(raw: str):
    """Parsea una marca canónica. Devuelve (year, month, day, weekday_idx,
    hour, minute, second, offset). REGLA 4: la letra declarada se
    corrige contra la calculada; aquí se DEVUELVE la declarada y la
    verificada para que el llamador decida (la spec: la calculada prevalece)."""
    cleaned = raw.strip().upper().replace(" ", "-").replace(".", "-")
    m = TIMESTAMP_RE.match(cleaned)
    if not m:
        raise BadTimestamp("GERO_EINVAL")
    year = int(m.group("year"))
    if m.group("era") == "AY":
        year = -year
    month = int(m.group("month"))
    day = int(m.group("day"))
    declared = m.group("weekday")
    hour = minute = second = 0
    offset = 0
    if m.group("hour") is not None:
        hour = int(m.group("hour"))
        minute = int(m.group("minute"))
        second = int(m.group("second"))
        offset = int(m.group("offset") or 0)
        if hour > 23 or minute > 59 or second > 59:
            raise BadTimestamp("GERO_EINVAL")
        if m.group("cycle") != cycle_of(hour):
            # REGLA 4 sobre el ciclo: la calculada prevalece; la marca es
            # aceptada con corrección, no rechazada.
            pass
    return year, month, day, declared, hour, minute, second, offset


def canonical_bytes_from(canon: str, instant: int, ctx: str = TS_CONTEXT) -> bytes:
    return f"{ctx}\n{canon}\n{instant}\n".encode("utf-8")


# ---------------------------------------------------------------------------
# Firma hash-only de referencia (WOTS16 + Merkle 1 nivel, SHA-256)
# ---------------------------------------------------------------------------

N = 32
W = 16
U = (8 * N) // 4
V = 3
P = U + V


def _h(*parts: bytes) -> bytes:
    d = hashlib.sha256()
    for p in parts:
        d.update(len(p).to_bytes(4, "big") + p)
    return d.digest()


def _chain(seed: bytes, start: int, steps: int, index: int) -> bytes:
    tmp = seed
    for i in range(start, start + steps):
        tmp = _h(b"F", tmp, i.to_bytes(4, "big"), index.to_bytes(4, "big"))
    return tmp


def _encode_message(digest: bytes):
    value = int.from_bytes(digest, "big")
    out = []
    for _ in range(U):
        out.append(value % W)
        value //= W
    csum = sum(W - 1 - c for c in out)
    for _ in range(V):
        out.append(csum % W)
        csum //= W
    return out


def leaf_from_sig_elements(public_key: bytes, digest: bytes, signature: dict) -> bytes:
    """Reconstruye la hoja Merkle desde la firma (verificación WOTS)."""
    leaf_index = int(signature["leaf"])
    sig_elements = [bytes.fromhex(x) for x in signature["sig"]]
    if len(sig_elements) != P:
        raise ValueError("GERO_ESIG")
    coeffs = _encode_message(digest)
    recomputed = bytearray()
    for i, (elem, c) in enumerate(zip(sig_elements, coeffs)):
        recomputed += _chain(elem, c, W - 1 - c, i)
    node = bytes(recomputed)
    for h, sib_hex in enumerate(signature["path"]):
        sib = bytes.fromhex(sib_hex)
        if (leaf_index >> h) & 1:
            node = _h(b"T", sib, node)
        else:
            node = _h(b"T", node, sib)
    return node


def verify_hashonly(public_key_bytes: bytes, message: bytes, signature: dict) -> bool:
    digest = hashlib.sha256(message).digest()
    try:
        node = leaf_from_sig_elements(public_key_bytes, digest, signature)
    except (KeyError, TypeError, ValueError):
        return False
    return hmac.compare_digest(node, public_key_bytes)


# ---------------------------------------------------------------------------
# Firma SLH-DSA (FIPS 205) vía paquete opcional
# ---------------------------------------------------------------------------


def verify_slhdsa(public_key_hex: str, message: bytes, sig_b64: str, alg: str):
    """Verificación SLH-DSA (FIPS 205) con la API real del paquete `slh-dsa`
    (0.2.x: KeyPair/PublicKey/SecretKey + verify_pure con contexto).

    La firma viaja en hex (formato del adaptador de referencia); se acepta
    también base64 por compatibilidad con documentos antiguos. Sin el
    paquete instalado: GERO_ENOALG — nunca un resultado ambiguo.
    """
    try:
        import slhdsa
    except ImportError:
        raise RuntimeError("GERO_ENOALG: algoritmo %s requiere el paquete 'slh-dsa'" % alg)
    params = alg.removeprefix("SLH-DSA-") if hasattr(str, "removeprefix") else alg[8:]
    alias = {"SHA2-128F": "128f", "SHA2-128S": "128s", "SHA2-192F": "192f", "SHA2-256S": "256s"}
    key = alias.get(params.upper())
    if key is None or not hasattr(slhdsa, f"sha2_{key}"):
        raise RuntimeError("GERO_ENOALG: parameter set desconocido para 'slh-dsa': %s" % alg)
    param = getattr(slhdsa, f"sha2_{key}")
    try:
        pub = slhdsa.PublicKey.from_digest(bytes.fromhex(public_key_hex), param)
    except Exception:  # noqa: BLE001 - llave malformada = firma inválida
        return False
    raw = bytes.fromhex(sig_b64) if _is_hex(sig_b64) else base64.b64decode(sig_b64)
    try:
        return pub.verify_pure(message, raw, ctx=b"GUS2-TS")
    except Exception:  # noqa: BLE001 - firma malformada = inválida
        return False


def verify_mldsa(public_key_hex: str, message: bytes, sig_b64: str, alg: str):
    """Verificación ML-DSA (FIPS 204) con el paquete `cryptography` (>= 47)
    (extra `gerarion[pqc]`), firma pura con contexto GUS2-TS.

    La firma viaja en hex (formato del adaptador de referencia); se acepta
    también base64. Sin el paquete instalado: GERO_ENOALG — nunca un
    resultado ambiguo.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric import mldsa
    except ImportError:
        raise RuntimeError("GERO_ENOALG: algoritmo %s requiere el paquete 'cryptography' (>= 47)" % alg)
    alias = {
        "ML-DSA-44": "MLDSA44PublicKey",
        "ML-DSA-65": "MLDSA65PublicKey",
        "ML-DSA-87": "MLDSA87PublicKey",
    }
    cls = alias.get(alg)
    if cls is None:
        raise RuntimeError("GERO_ENOALG: parameter set desconocido para 'cryptography': %s" % alg)
    try:
        pub = getattr(mldsa, cls).from_public_bytes(bytes.fromhex(public_key_hex))
    except Exception:  # noqa: BLE001 - llave malformada = firma inválida
        return False
    raw = bytes.fromhex(sig_b64) if _is_hex(sig_b64) else base64.b64decode(sig_b64)
    try:
        pub.verify(raw, message, b"GUS2-TS")
        return True
    except Exception:  # noqa: BLE001 - firma malformada = inválida
        return False


def _is_hex(s: str) -> bool:
    try:
        bytes.fromhex(s)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Anclaje del notario (dia GUS: Merkle de hojas + cadena day_root)
# ---------------------------------------------------------------------------

EMPTY_ROOT = hashlib.sha256(b"GUS2-EMPTY").digest()


def _node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def verify_inclusion(leaf: bytes, path, index: int, root: bytes) -> bool:
    node = leaf
    depth = 0
    for sib_hex in path:
        sib = bytes.fromhex(sib_hex)
        if (index >> depth) & 1:
            node = _node_hash(sib, node)
        else:
            node = _node_hash(node, sib)
        depth += 1
    return hmac.compare_digest(node, root)


# ---------------------------------------------------------------------------
# Verificación de documento GST completo
# ---------------------------------------------------------------------------


def verify_document(doc: dict) -> dict:
    # GST v2 (sobre JCS/híbrido): dominio y esquema distintos de los
    # documentos v1; se despacha a su verificador dedicado.
    if doc.get("gst_version") == "2.0":
        return verify_document_v2(doc)
    errors = []
    flags = []
    ts = doc.get("ts")
    if not isinstance(ts, str):
        return {"ok": False, "errors": ["GERO_EINVAL: falta ts"], "flags": []}
    try:
        year, month, day, declared, hour, minute, second, offset = parse_canonical(ts)
    except BadTimestamp as exc:
        return {"ok": False, "errors": [str(exc)], "flags": []}

    # --- calendario: recalcular la fecha desde la fecha declarada ---
    try:
        day_index = from_gerarion(year, month, day)
    except ValueError as exc:
        return {"ok": False, "errors": [str(exc)], "flags": []}
    weekday_idx = day_index % 7
    expected = WEEKDAY_ABBREVS[weekday_idx]
    if declared != expected:
        errors.append("GERO_EWEEK: letra declarada %s != calculada %s" % (declared, expected))

    instant = day_index * SECS_PER_DAY + hour * 3600 + minute * 60 + second
    if int(doc.get("ins", -1)) != instant:
        errors.append("instante divergente del formato canónico")
    if int(doc.get("day", -1)) != day_index:
        errors.append("índice de día divergente del formato canónico")

    ctx = doc.get("ctx", TS_CONTEXT)
    message = canonical_bytes_from(ts, instant, ctx)

    alg = doc.get("alg", "")
    pub = doc.get("pub")
    sig = doc.get("sig")
    if not isinstance(pub, str) or sig is None:
        errors.append("firma ausente o malformada")
    elif alg == "WOTS16-MERKLE-REF-SHA256":
        if not verify_hashonly(bytes.fromhex(pub), message, sig):
            errors.append("GERO_ESIG: firma inválida")
    elif isinstance(alg, str) and alg.startswith("SLH-DSA"):
        try:
            if not verify_slhdsa(pub, message, sig, alg):
                errors.append("firma SLH-DSA inválida")
        except RuntimeError as exc:
            errors.append(str(exc))
        except Exception as exc:  # noqa: BLE001
            errors.append("firma inválida: %s" % exc)
    elif isinstance(alg, str) and alg.startswith("ML-DSA"):
        try:
            if not verify_mldsa(pub, message, sig, alg):
                errors.append("firma ML-DSA inválida")
        except RuntimeError as exc:
            errors.append(str(exc))
        except Exception as exc:  # noqa: BLE001
            errors.append("firma inválida: %s" % exc)
    else:
        errors.append("algoritmo desconocido: %r" % (alg,))

    # --- anclaje del notario ---
    anchor = doc.get("anchor")
    if anchor:
        if anchor.get("day") is None:
            errors.append("anclaje incompleto: falta day")
        else:
            leaf = hashlib.sha256(b"\x00" + message).digest()
            if "root" in anchor:
                if not verify_inclusion(
                    leaf, anchor.get("proof", []), int(anchor.get("index", 0)),
                    bytes.fromhex(anchor["root"]),
                ):
                    errors.append("la marca no está incluida en la raíz")

    return {"ok": not errors, "errors": errors, "flags": flags}


# ---------------------------------------------------------------------------
# GST v2: canonicalización JCS (RFC 8785) compacta + verificación híbrida
# ---------------------------------------------------------------------------

_JCS_ESCAPES = {0x08: "\\b", 0x09: "\\t", 0x0A: "\\n", 0x0C: "\\f", 0x0D: "\\r"}


def _jcs_string(s: str) -> str:
    out = ['"']
    for ch in s:
        code = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif 0x20 <= code < 0x7F:
            out.append(ch)
        elif code in _JCS_ESCAPES:
            out.append(_JCS_ESCAPES[code])
        elif code < 0x20:
            out.append("\\u%04x" % code)
        elif 0xD800 <= code <= 0xDFFF:
            raise ValueError("GERO_EINVAL: sustituto huérfano no canonizable")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _jcs_number(x: float) -> str:
    """Formato numérico ECMAScript determinista (RFC 8785, Appendix B)."""
    if x != x or x in (float("inf"), float("-inf")):
        raise ValueError("GERO_EINVAL: NaN/Infinity no es JCS")
    if x == 0:
        return "0"
    sign = "-" if x < 0 else ""
    rep = repr(abs(x))
    if "e" in rep or "E" in rep:
        mant, exp_s = rep.replace("E", "e").split("e")
        exp = int(exp_s)
    else:
        mant, exp = rep, 0
    int_part, _, frac = mant.partition(".")
    digits_raw = int_part + frac
    stripped = digits_raw.lstrip("0")
    first = len(digits_raw) - len(stripped)
    s = stripped.rstrip("0") or "0"
    k = len(s)
    n = len(int_part) - first + exp
    if k <= n <= 21:
        return sign + s + "0" * (n - k)
    if 0 < n <= 21:
        return sign + s[:n] + "." + s[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * (-n) + s
    e = n - 1
    mant_part = s[0] if k == 1 else s[0] + "." + s[1:]
    return "%s%se%s%d" % (sign, mant_part, "+" if e >= 0 else "-", abs(e))


def _jcs_dump(value, out: list) -> None:
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, int):
        out.append(str(value))
    elif isinstance(value, float):
        out.append(_jcs_number(value))
    elif isinstance(value, str):
        out.append(_jcs_string(value))
    elif isinstance(value, (list, tuple)):
        out.append("[")
        for i, item in enumerate(value):
            if i:
                out.append(",")
            _jcs_dump(item, out)
        out.append("]")
    elif isinstance(value, dict):
        keys = sorted(value.keys(), key=lambda k: k.encode("utf-16-be"))
        out.append("{")
        for i, k in enumerate(keys):
            if i:
                out.append(",")
            if not isinstance(k, str):
                raise ValueError("GERO_EINVAL: clave no textual")
            out.append(_jcs_string(k))
            out.append(":")
            _jcs_dump(value[k], out)
        out.append("}")
    else:
        raise ValueError("GERO_EINVAL: tipo no serializable en JCS")


def jcs_bytes(value) -> bytes:
    """Serialización canónica RFC 8785 en UTF-8 sin BOM."""
    out: list = []
    _jcs_dump(value, out)
    return "".join(out).encode("utf-8")


def verify_ed25519(pub_hex: str, message: bytes, sig_hex: str) -> bool:
    """Ed25519 (RFC 8032) vía `cryptography`; False si falta o falla."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey,
        )
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex))
        pub.verify(bytes.fromhex(sig_hex), message)
        return True
    except Exception:  # noqa: BLE001 - ausencia o invalidez = no verificado
        return False


_GST_V2_DOMAIN = b"GUS3-GST-V2\x00"
_EVENT_HASH_RE = re.compile(r"^sha(256|512):[0-9a-f]{64,128}$")
_NONCE_RE = re.compile(r"^[0-9a-f]{32}$")


def verify_document_v2(doc: dict) -> dict:
    """Verificador GST v2: esquema estricto + firma híbrida todo-o-nada.

    Exige `event_hash` válido, metadatos de custodia completos y que AMBAS
    firmas (Ed25519 y ML-DSA) verifiquen sobre b"GUS3-GST-V2\\0" + JCS(payload).
    Sin el paquete `cryptography` el resultado es GERO_ENOALG (NUNCA un
    falso OK). La guardia anti-replay es estado del verificador: este CLI
    es apátrida y LO SEÑALA, no la simula.
    """
    errors = []
    payload = {k: v for k, v in doc.items() if k != "sigs"}
    if doc.get("gst_version") != "2.0":
        errors.append("gst_version debe ser '2.0'")
    if doc.get("scale") not in ("TCJ", "TAI"):
        errors.append("scale debe ser 'TCJ' o 'TAI' explícito")
    if not isinstance(doc.get("event_hash"), str) or not _EVENT_HASH_RE.match(
        doc.get("event_hash", "")
    ):
        errors.append("event_hash obligatorio (sha256:/sha512:<hex>)")
    for field in ("kid", "issuer", "policy_version", "kid_classical", "kid_pqc"):
        if not isinstance(doc.get(field), str) or not doc.get(field):
            errors.append(f"{field} obligatorio")
    if not isinstance(doc.get("nonce"), str) or not _NONCE_RE.match(doc.get("nonce", "")):
        errors.append("nonce debe ser hex de 16 bytes")
    seq, ins = doc.get("seq"), doc.get("ins")
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
        errors.append("seq debe ser entero >= 0")
    if isinstance(ins, bool) or not isinstance(ins, int):
        errors.append("ins debe ser entero (segundos)")
    nanos = doc.get("nanos")
    if isinstance(nanos, bool) or not isinstance(nanos, int) or not 0 <= nanos <= 999_999_999:
        errors.append("nanos fuera de rango 0..999_999_999")
    alg = doc.get("alg", "")
    if not isinstance(alg, str) or not alg.startswith("HYBRID-ED25519-ML-DSA-"):
        errors.append("alg debe ser HYBRID-ED25519-ML-DSA-*")
    sigs = doc.get("sigs")
    if not isinstance(sigs, dict) or sigs.get("alg") != alg or not isinstance(sigs.get("sigs"), dict):
        errors.append("bloque de firmas ausente o inconsistente con el alg del payload")
    if errors:
        return {"ok": False, "errors": errors, "flags": []}

    # Coherencia de la marca: la marca canónica manda.
    try:
        year, month, day, declared, hour, minute, second, offset = parse_canonical(
            doc["ts"]
        )
        day_index = from_gerarion(year, month, day)
    except (BadTimestamp, ValueError) as exc:
        return {"ok": False, "errors": [str(exc)], "flags": []}
    expected_wd = WEEKDAY_ABBREVS[day_index % 7]
    if declared != expected_wd:
        errors.append("GERO_EWEEK: letra de día inconsistente")
    instant = day_index * SECS_PER_DAY + hour * 3600 + minute * 60 + second
    if ins != instant:
        errors.append("instante divergente del formato canónico")

    message = _GST_V2_DOMAIN + jcs_bytes(payload)
    pair = sigs["sigs"]
    ed, ml = pair.get("ed25519"), pair.get("mldsa")
    if not isinstance(ed, str) or not isinstance(ml, str):
        errors.append("REJECTED: faltan firmas del par híbrido (todo-o-nada)")
        return {"ok": False, "errors": errors, "flags": []}
    alg_pqc = alg.removeprefix("HYBRID-ED25519-")
    if not verify_ed25519(payload["pub_classical"], message, ed):
        errors.append("firma Ed25519 inválida")
    try:
        if not verify_mldsa(payload["pub_pqc"], message, ml, alg_pqc):
            errors.append("firma ML-DSA inválida")
    except RuntimeError as exc:
        errors.append(str(exc))
    except Exception as exc:  # noqa: BLE001
        errors.append("firma inválida: %s" % exc)
    return {
        "ok": not errors,
        "errors": errors,
        "flags": [],
        "state": "VALID" if not errors else "REJECTED",
        "note": "anti-replay: requiere estado del verificador (guardia persistente); este CLI es apátrida",
    }


def anchor_status(doc) -> str:
    """Estado del anclaje declarado: ANCLA_AUSENTE / ANCLA_PENDIENTE /
    ANCLA_INCOMPLETA / ANCLA_CONSISTENTE (la consistencia interna de la raíz
    autoincluida NO prueba origen: contrastarla es papel del trust root)."""
    if hasattr(doc, "anchor"):
        doc = {"anchor": doc.anchor, "ts": doc.ts, "ins": doc.instant, "ctx": doc.ctx}
    anchor = doc.get("anchor")
    if not anchor:
        return "ANCLA_AUSENTE"
    if not anchor.get("sealed"):
        return "ANCLA_PENDIENTE"
    if "root" not in anchor or "proof" not in anchor:
        return "ANCLA_INCOMPLETA"
    leaf = hashlib.sha256(b"\x00" + canonical_bytes_from(
        doc["ts"], int(doc.get("ins", -1)), doc.get("ctx", TS_CONTEXT))).digest()
    if verify_inclusion(leaf, anchor.get("proof", []), int(anchor.get("index", 0)),
                        bytes.fromhex(anchor["root"])):
        return "ANCLA_CONSISTENTE"
    return "ANCLA_INVALIDA"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verificador monolítico GST (GUS 2.0)")
    ap.add_argument("gst", help="archivo JSON del documento GST")
    ap.add_argument("--require-anchor", action="store_true",
                    help="exigir un anchor internamente consistente (rc 2 si falta/inválido)")
    args = ap.parse_args(argv)
    with open(args.gst, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    res = verify_document(doc)
    if res["ok"] and doc.get("gst_version") == "2.0":
        # GST v2: sin anclaje de notario (esquema distinto); la nota de
        # anti-replay viaja en el resultado.
        print("FIRMA_VALIDA %s | GST v2 híbrida (%s)" % (doc.get("ts"), doc.get("alg")))
        for note in res.get("note", "").splitlines():
            if note:
                print("nota: %s" % note, file=sys.stderr)
        return 0
    status = anchor_status(doc)
    if res["ok"]:
        sig_line = "FIRMA_VALIDA"
        if status == "ANCLA_CONSISTENTE":
            print("%s %s | %s (consistencia interna; la raíz debe contrastarse "
                  "con un notario de política)" % (sig_line, doc.get("ts"), status))
            return 0
        print("%s %s | %s" % (sig_line, doc.get("ts"), status))
        if args.require_anchor:
            print("FAIL GERO_ENOANCHOR: --require-anchor exige un anchor "
                  "internamente consistente (rc 2)", file=sys.stderr)
            return 2
        print("nota: el anclaje no está verificado; usa --require-anchor para exigirlo",
              file=sys.stderr)
        return 0
    for err in res["errors"]:
        print("FAIL %s" % err, file=sys.stderr)
    print("estado del anclaje: %s" % status, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
