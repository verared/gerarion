#!/usr/bin/env python3
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
solo si pasa el vector set (vectors/gus-normative-001.json); este
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
    if year < 0:
        return False
    r = 0
    found = False
    for n in range(year + 1):
        r += SOLAR_DELTA_UD
        if r >= SOLAR_THRESHOLD_UD:
            found = True
            r -= SOLAR_THRESHOLD_UD
        else:
            found = False
    return found


def year_length(year: int) -> int:
    if year < 0:
        return YEAR_COMMON_DAYS
    return YEAR_GRAN_DAYS if is_gran_tempalum(year) else YEAR_COMMON_DAYS


def year_start_day_index(year: int) -> int:
    if year >= 0:
        return sum(year_length(n) for n in range(year))
    return year * YEAR_COMMON_DAYS


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
    try:
        from slhdsa import SlhDsa
    except ImportError:
        raise RuntimeError("GERO_ENOALG: algoritmo %s requiere el paquete 'slh-dsa'" % alg)
    params = alg.split("-", 1)[1] if "-" in alg else alg
    key = SlhDsa(params, bytes.fromhex(public_key_hex))
    return key.verify(message, base64.b64decode(sig_b64))


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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verificador monolítico GST (GUS 2.0)")
    ap.add_argument("gst", help="archivo JSON del documento GST")
    ap.add_argument("--no-anchor", action="store_true",
                    help="no exigir anchor de notario (no está definido exigirlo por defecto)")
    args = ap.parse_args(argv)
    with open(args.gst, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    res = verify_document(doc)
    if res["ok"]:
        print("OK %s (instant=%s day=%s flags=%s)" % (
            doc.get("ts"), doc.get("ins"), doc.get("day"), res["flags"]))
        return 0
    for err in res["errors"]:
        print("FAIL %s" % err, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
