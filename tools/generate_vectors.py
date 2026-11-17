#!/usr/bin/env python3
"""Genera vectors/gus-normative-002.json — la única fuente normativa de vectores.

Cambios respecto de `gus-normative-001` (archivada en vectors/archive/):
kernel de calendario GUS 2.1 con Gran Tempalum simétrico (spec GUS v2.1.0,
spec §3/§6): la regla es idéntica en ambas eras (DY y AY), por lo que los
valores de vectores con día_index < 0 se recalculan y se añaden casos AY
nuevos (0001AY-00-11-B, 12000AY-01-01-S, etc.). Los vectores de la era DY
son bit a bit los de la 001: ningún dato de DY cambia.

Reglas de generación:

  1. Todo valor se calcula con la implementación de referencia (src/gerarion).
  2. La generación es determinista: sin aleatoriedad, sin reloj, orden de
     recorrido fijo. Regenerar produce byte a byte el mismo archivo (los
     firmantes usan semillas y digests fijos).
  3. El JSON incluye, junto a cada categoría, la definición de los algoritmos
     de los que dependen sus valores (hash de hoja, concatenación con prefijo
     de longitud, etc.) para que una tercera implementación pueda verificar
     sin leer el código Python.

Uso:  PYTHONPATH=src python3 tools/generate_vectors.py
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gerarion import adapters as adp  # noqa: E402
from gerarion import calendar as cal  # noqa: E402
from gerarion import format as fmt  # noqa: E402
from gerarion import hashots  # noqa: E402
from gerarion import notary as nty  # noqa: E402
from gerarion import notary_cluster as ncl  # noqa: E402
from gerarion import gts  # noqa: E402

VECTOR_ID = "gus-normative-002"
GUS_VERSION = "2.1.0"

ERR_CODE = {
    cal.GeroEinval: "GERO_EINVAL",
    cal.GeroItemporal: "GERO_ETEMPALUM",
    cal.GeroError: "GERO_EWEEK",  # solo se lanza en strict_weekday
}

ALG_DOC = {
    "leaf": "leaf = SHA-256(0x00 || payload); node = SHA-256(0x01 || left || right); pares impares: duplicar la última hoja",
    "day_root": 'day_root(n) = L("\x01GUS2-DAY" || u64be(n) || tree_root(n) || prev_root(n)) donde L concatena cada parte con prefijo u32be(len)',
    "empty_root": 'EMPTY_ROOT = SHA-256("GUS2-EMPTY")',
}

# ---------------------------------------------------------------------------
# Obras maestras de contenido vectorial
# ---------------------------------------------------------------------------

#: Fechas de borde calendario: gregoriano proleptico -> GUS
CALENDAR_DATES = [
    (-5, 3, 21),     # origen: 0DY-01-01 Soludyia (por definición)
    (-5, 3, 20),     # día -1: 1AY-00-11 Tempalum día 11 (Nuvivid VII; GT AY simétrico, spec 2.1)
    (-6, 3, 18),     # 1AY-01-04 Aisterdyia (primer regular del año GT 1AY)
    (-11, 3, 14),    # 6AY-01-01 (inicio del año GT 6AY)
    (-34, 3, 15),    # 29AY-01-01 (inicio del año GT 29AY, borde del patrón)
    (-12005, 3, 21), # 12000AY-01-01
    (2026, 3, 16),   # víspera del cambio de año 2030->2031 (errata v1.2 E-01)
    (2026, 3, 17),   # 2031DY-01-01 (errata v1.2 E-01)
    (2026, 4, 15),   # Yeshuvid 2031DY-01-30 (errata v1.2 E-02)
    (2026, 5, 23),
    (2027, 3, 10),
    (2027, 3, 11),   # 2031DY-12-30
    (2027, 3, 12),   # 2031DY-00-01 Tempalum
    (2027, 3, 15),   # 2031DY-00-04 Tempalum día 4
    (2027, 3, 16),   # 2032DY-01-01
]

#: Índices de día de borde para round-trip gregoriano
GREG_ROUNDTRIP_INDICES = [
    0, 1, -1, 363, 364, 371, 727, 728, 735, 2030, 2031,
    73913, 100000, 1000000, 2000000,
    -1, -5, -7, -10, -364, -365, -371, -372, -728, -1000, -4382910, -1000000,  # AY simétrico (spec 2.1)
]

YEAR_STARTS = [-12000, -29, -17, -12, -6, -1,
               0, 1, 2, 3, 4, 5, 6, 7, 11, 12, 45, 46,
               2029, 2030, 2031, 2032, 2033, 2034, 2035, 2039, 2040, 2045]

FORMAT_CANONICAL = [
    {"input": "2031DY-03-08-T", "expected": "2031DY-03-08-T", "flags": []},
    {"input": "2031dy-3-8-t", "expected": "2031DY-03-08-T", "flags": []},
    {"input": "2031DY.03.08.T", "expected": "2031DY-03-08-T", "flags": []},
    {"input": "2031-03-08-T", "expected": "2031DY-03-08-T", "flags": ["era_assumed_DY"]},
    {"input": "2031DY-03-08-S", "expected": "2031DY-03-08-T", "flags": ["weekday_corrected"]},
    {"input": "2031DY-03-08-T-09:30:00-SC-TCJ+0", "expected": "2031DY-03-08-T-09:30:00-SC-TCJ+0", "flags": []},
    {"input": "2031DY-03-08 T 09:30:00 SC TCJ+0", "expected": "2031DY-03-08-T-09:30:00-SC-TCJ+0", "flags": []},
    {"input": "2031DY-03-08-T-21:45:10-SC-TCJ+3", "expected": "2031DY-03-08-T-21:45:10-LC-TCJ+3", "flags": ["cycle_corrected"]},
    {"input": "2034DY-00-07-M", "expected": "2034DY-00-07-M", "flags": []},
    {"input": "2034DY-00-07-V", "expected": "2034DY-00-07-M", "flags": ["weekday_corrected"]},
    {"input": "1AY-00-11-B", "expected": "0001AY-00-11-B", "flags": []},
    {"input": "6AY-01-01-S", "expected": "0006AY-01-01-S", "flags": []},
    {"input": "12000AY-01-01-S", "expected": "12000AY-01-01-S", "flags": []},
    {"input": "31DY-03-08-t", "expected": "0031DY-03-08-T", "flags": []},
]

FORMAT_ERRORS = [
    {"input": "2031DY-00-05-T", "error": "GERO_ETEMPALUM"},
    {"input": "2034DY-00-12-T", "error": "GERO_ETEMPALUM"},
    {"input": "2031DY-01-31-T", "error": "GERO_EINVAL"},
    {"input": "2031DY-00-31-T", "error": "GERO_ETEMPALUM"},
    {"input": "2031DY-13-01-T", "error": "GERO_EINVAL"},
    {"input": "2031DY-03-08-Z", "error": "GERO_EINVAL"},
    {"input": "hola", "error": "GERO_EINVAL"},
    {"input": "2031DY-03-08-T-24:00:00-SC-TCJ+0", "error": "GERO_EINVAL"},
    {"input": "2031DY-03-08-T-09:60:00-SC-TCJ+0", "error": "GERO_EINVAL"},
    {"input": "2031DY-03-08-T-09:30:00-XX-TCJ+0", "error": "GERO_EINVAL"},
]

FORMAT_STRICT = [
    {"input": "2031DY-03-08-S", "error": "GERO_EWEEK"},
]

#: Marcas completas -> instante continuo
INSTANT_CASES = [
    ("2031DY-03-08-T-09:30:00-SC-TCJ+0", 64097688600),
    ("2031DY-01-01-S-00:00:00-LC-TCJ+0", 64091865600),
    ("0000DY-01-01-S-00:00:00-LC-TCJ+0", 0),
    ("0000DY-01-01-S-00:00:01-LC-TCJ+0", 1),
    ("0000DY-01-01-S-23:59:59-SC-TCJ+0", 86399),
    ("0000DY-01-01-S-05:59:59-LC-TCJ+0", 21599),
    ("0000DY-01-01-S-06:00:00-SC-TCJ+0", 21600),
    ("0000DY-01-01-S-17:59:59-SC-TCJ+0", 64799),
    ("0000DY-01-01-S-18:00:00-LC-TCJ+0", 64800),
    ("0001AY-00-11-B-12:00:00-SC-TCJ+0", -43200),  # día -1: último día de 0001AY (GT AY simétrico)
]

#: Caso de sello diario del notario determinista
NOTARY_PAYLOAD_TS = [
    "2031DY-03-08-T-09:30:00-SC-TCJ+0",
    "2031DY-01-01-S",
]


def build_constants() -> dict:
    return {
        "ORIGIN_JDN": cal.ORIGIN_JDN,
        "SOLAR_DELTA_UD": cal.SOLAR_DELTA_UD,
        "SOLAR_THRESHOLD_UD": cal.SOLAR_THRESHOLD_UD,
        "YEAR_COMMON_DAYS": cal.YEAR_COMMON_DAYS,
        "YEAR_GRAN_DAYS": cal.YEAR_GRAN_DAYS,
        "MONTH_BLOCK_DAYS": cal.MONTH_BLOCK_DAYS,
        "SECS_PER_DAY": cal.SECS_PER_DAY,
        "TROPICAL_YEAR_UD": cal.TROPICAL_YEAR_UD,
        "WEEKDAY_LETTERS": [w[1] for w in cal.WEEKDAYS],
        "canonical_format": "AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O]",
        "context": fmt.CANONICAL_CTX,
        "signed_bytes": '"GUS2-TS\\n" + canon + "\\n" + str(instant) + "\\n" en UTF-8',
    }


def build_calendar_vectors() -> list:
    rows = []
    for gy, gm, gd in CALENDAR_DATES:
        di = cal.day_index_from_gregorian(gy, gm, gd)
        g = cal.to_gerarion(di)
        nuvid, abbr = g.weekday
        rows.append({
            "greg": f"{gy:04d}-{gm:02d}-{gd:02d}",
            "greg_year": gy, "greg_month": gm, "greg_day": gd,
            "day_index": di,
            "era": "DY" if g.year >= 0 else "AY",
            "year": abs(g.year),
            "month": g.month,
            "day": g.day,
            "weekday_index": g.weekday_index,
            "weekday": nuvid,
            "abbr": abbr,
            "tempalum_name": g.tempalum_name,
            "sacred_day": g.sacred_day,
        })
    return rows


def build_year_starts() -> list:
    rows = []
    for y in YEAR_STARTS:
        di = cal.year_start_day_index(y)
        gy, gm, gd = cal.gregorian_from_day_index(di)
        rows.append({
            "year": y,
            "era": "DY" if y >= 0 else "AY",
            "day_index": di,
            "greg": f"{gy:04d}-{gm:02d}-{gd:02d}",
            "greg_year": gy, "greg_month": gm, "greg_day": gd,
            "gran_tempalum": cal.is_gran_tempalum(y),  # simétrico: también en AY (spec 2.1)
            "tempalum_days": cal.tempalum_days(y),
            "abbr": "S",
        })
    return rows


def build_greg_roundtrip() -> list:
    rows = []
    for di in GREG_ROUNDTRIP_INDICES:
        gy, gm, gd = cal.gregorian_from_day_index(di)
        rows.append({
            "day_index": di,
            "greg": f"{gy:04d}-{gm:02d}-{gd:02d}",
            "greg_year": gy, "greg_month": gm, "greg_day": gd,
        })
    return rows


def build_format_vectors() -> dict:
    canonical = []
    for case in FORMAT_CANONICAL:
        parsed = fmt.parse(case["input"])
        canonical.append({
            "input": case["input"],
            "canonical": fmt.to_canonical(parsed),
            "flags": sorted(parsed.flags),
            "fields": {
                "year": abs(parsed.year), "era": "DY" if parsed.year >= 0 else "AY",
                "month": parsed.month, "day": parsed.day,
                "hour": parsed.hour, "minute": parsed.minute, "second": parsed.second,
                "cycle": parsed.cycle, "offset": parsed.offset,
            },
        })
        assert fmt.to_canonical(parsed) == case["expected"], case
        assert sorted(parsed.flags) == sorted(case["flags"]), case
    errors = []
    for case in FORMAT_ERRORS:
        try:
            fmt.parse(case["input"])
        except cal.GeroError as exc:
            code = type(exc).__name__
            errors.append({"input": case["input"], "error": case["error"], "python_class": code})
        else:
            raise AssertionError(f"se esperaba {case['error']} para {case['input']!r}")
    strict = []
    for case in FORMAT_STRICT:
        try:
            fmt.parse(case["input"], strict_weekday=True)
        except cal.GeroError:
            strict.append({"input": case["input"], "error": "GERO_EWEEK"})
        else:
            raise AssertionError("se esperaba GERO_EWEEK")
    return {"canonical": canonical, "errors": errors, "strict_weekday": strict}


def build_instant_vectors() -> list:
    rows = []
    for ts, expected in INSTANT_CASES:
        parsed = fmt.parse(ts)
        gdate = cal.from_gerarion(parsed.year, parsed.month, parsed.day)
        instant = cal.instant_from_parts(gdate.day_index, parsed.hour, parsed.minute, parsed.second)
        assert instant == expected, (ts, instant, expected)
        rows.append({"ts": ts, "instant": instant, "day": gdate.day_index})
    return rows


def build_hashots_vectors() -> dict:
    seed = bytes.fromhex("5e" * 32)
    signer = hashots.WotsMerkleSigner(seed, height=4)
    rows = []
    for ts in NOTARY_PAYLOAD_TS[:2] + ["2034DY-00-07-V"]:
        parsed = fmt.parse(ts)
        gdate = cal.from_gerarion(parsed.year, parsed.month, parsed.day)
        instant = cal.instant_from_parts(gdate.day_index, parsed.hour, parsed.minute, parsed.second)
        message = fmt.canonical_bytes(fmt.to_canonical(parsed), instant)
        doc = gts.create(parsed, signer)
        rows.append({
            "message_hex": message.hex(),
            "message_sha256": hashlib.sha256(message).hexdigest(),
            "pub_hex": signer.public_key.hex(),
            "leaf": doc.sig["leaf"],
            "sig_hex": doc.sig["sig"],
            "path_hex": doc.sig["path"],
            "gts_day": doc.day,
            "gts_instant": doc.instant,
        })
    # vector de manipulación: la misma firma no vale para otro mensaje
    other = fmt.canonical_bytes("2031DY-03-08-T", 0)
    rows.append({
        "message_hex": other.hex(),
        "message_sha256": hashlib.sha256(other).hexdigest(),
        "pub_hex": signer.public_key.hex(),
        "leaf": rows[0]["leaf"],
        "sig_hex": rows[0]["sig_hex"],
        "path_hex": rows[0]["path_hex"],
        "gts_day": None,
        "gts_instant": None,
        "tampered": True,
    })
    return {"alg": "WOTS16-MERKLE-REF-SHA256", "height": 4, "vectors": rows, "algorithms": ALG_DOC}


#: Pares SLH-DSA fijos (generados una única vez con slhdsa.KeyPair.gen() y
#: embebidos para determinismo; SOLO vector de test — jamás usar en producción).
SLHDSA_FIXED_DIGESTS = {
    "SLH-DSA-SHA2-128F": (
        "f2fa226fd9532e51b5c71a86a8d364a90d7a4debf04026e73f6e7e4ec984c1e4"
        "fd0617195aca3d9897d386e871956f49a5a4c15243fa86f08fe36172de220789"
        "f2fa226fd9532e51b5c71a86a8d364a90d7a4debf04026e73f6e7e4ec984c1e4"
    ),
    "SLH-DSA-SHA2-128S": (
        "e3d6aea241f29c436528ddbcbfeb45fce13d7bc2a095986ae7110d91b5d52211"
        "3026450b7cdd0f2f8e41dde30e070fd57686b418bbf730d1aa9b1ddba6c62fa"
        "8e3d6aea241f29c436528ddbcbfeb45fce13d7bc2a095986ae7110d91b5d52211"
    ),
}


def build_slhdsa_vectors() -> dict | None:
    rows = []
    for alg, digest_hex in SLHDSA_FIXED_DIGESTS.items():
        signer = adp.SlhDsaSigner(alg, digest=bytes.fromhex(digest_hex))
        parsed = fmt.parse(NOTARY_PAYLOAD_TS[0])
        gdate = cal.from_gerarion(parsed.year, parsed.month, parsed.day)
        instant = cal.instant_from_parts(gdate.day_index, parsed.hour, parsed.minute, parsed.second)
        message = fmt.canonical_bytes(fmt.to_canonical(parsed), instant)
        sig_hex = signer.sign_payload(message)
        assert adp.SlhDsaSigner.verify(signer.public_key_hex, message, sig_hex, alg)
        rows.append({
            "alg": alg,
            "message_hex": message.hex(),
            "pub_hex": signer.public_key_hex,
            "sig_hex": sig_hex,
        })
    # manipulación: otra marca con la misma firma debe fallar
    rows.append({
        "alg": "SLH-DSA-SHA2-128F",
        "message_hex": b"GUS2-tamper\\n".hex(),
        "pub_hex": rows[0]["pub_hex"],
        "sig_hex": rows[0]["sig_hex"],
        "tampered": True,
    })
    return {
        "algorithms": ["SLH-DSA-SHA2-128F", "SLH-DSA-SHA2-128S"],
        "note": "FIPS 205 puro (modo pur, contexto GUS2-TS). Semillas deterministas vía digest fijo de 6n bytes.",
        "vectors": rows,
    }


def build_notary_vectors() -> dict:
    # (1) sellado determinista con días de borde (vacío incluido)
    notary = nty.DayNotary()
    day_vectors = []
    plan = [
        (0, 2),   # dos marcas
        (1, 0),   # día vacío: raíz vacía definida
        (2, 1),   # una marca
    ]
    payload0 = fmt.canonical_bytes(*_ts_to_parts(NOTARY_PAYLOAD_TS[0]))
    payload1 = fmt.canonical_bytes(*_ts_to_parts(NOTARY_PAYLOAD_TS[1]))
    payloads_by_day = {0: [payload1, payload0], 1: [], 2: [payload1]}
    for day, count in plan:
        for which in range(count):
            notary.append(payloads_by_day[day][which])
        rec = notary.seal_day(day)
        entry = {
            "day": day,
            "payloads_hex": [p.hex() for p in payloads_by_day[day]],
            "leaves_hex": rec["leaves"],
            "tree_root": rec["tree_root"],
            "prev_root": rec["prev_root"],
            "day_root": rec["day_root"],
        }
        if count:
            proof = notary.inclusion_proof(day, 0)
            entry["proof_leaf0"] = {"leaf_index": 0, "proof_hex": proof["proof"], "root": proof["root"]}
        day_vectors.append(entry)

    # (2) bundle multi-réplica con réplica divergente
    cluster = ncl.NotaryCluster(["alpha", "beta", "gamma"], threshold=2)
    payload = payload0
    cluster.fanout(payload)
    pubs = cluster.seal_day(73913)
    publications = [pub.to_dict() for pub in pubs.values()]
    # gamma publica una raíz derivada de otro árbol (divergencia quizá bien formada)
    bad_tree = hashlib.sha256(b"GUS2-CORRUPT-TREE").digest()
    publications.append({
        "replica": "delta-censura",
        "day": 73913,
        "tree_root": bad_tree.hex(),
        "prev_root": pubs["gamma"].prev_root,
        "day_root": ncl.derive_day_root(73913, bad_tree.hex(), pubs["gamma"].prev_root),
    })
    result = ncl.verify_bundle(publications, 2)
    bundle = {
        "day": 73913,
        "threshold": 2,
        "payload_payload_hex": payload.hex(),
        "payload_leaf_hex": hashlib.sha256(b"\x00" + payload).hexdigest(),
        "publications": publications,
        "expected": result,
    }
    return {"algorithms": ALG_DOC, "day_seals": day_vectors, "bundle": bundle}


def _ts_to_parts(ts: str):
    parsed = fmt.parse(ts)
    gdate = cal.from_gerarion(parsed.year, parsed.month, parsed.day)
    canon = fmt.to_canonical(parsed)
    instant = cal.instant_from_parts(gdate.day_index, parsed.hour, parsed.minute, parsed.second)
    return canon, instant


def main() -> None:
    data = {
        "schema": VECTOR_ID,
        "gus_version": GUS_VERSION,
        "source": "src/gerarion (implementación de referencia Python)",
        "deterministic": True,
        "categories_core": ["constants", "gran_tempalum", "calendar", "year_starts",
                            "gregorian_roundtrip", "format", "instant"],
        "categories_full": ["constants", "gran_tempalum", "calendar", "year_starts",
                            "gregorian_roundtrip", "format", "instant", "hashots",
                            "slh_dsa", "notary"],
        "constants": build_constants(),
        "gran_tempalum": {
            "pattern_years_0_45": [y for y in range(46) if cal.is_gran_tempalum(y)],
            "pattern_years_m45_m1": [y for y in range(-46, 0) if cal.is_gran_tempalum(y)],
            "years_sample": {str(y): cal.is_gran_tempalum(y)
                             for y in [-12000, -6, -1, 1, 2031, 2034, 2039, 2040]},
        },
        "calendar": build_calendar_vectors(),
        "year_starts": build_year_starts(),
        "gregorian_roundtrip": build_greg_roundtrip(),
        "format": build_format_vectors(),
        "instant": build_instant_vectors(),
        "hashots": build_hashots_vectors(),
        "slh_dsa": build_slhdsa_vectors(),
        "notary": build_notary_vectors(),
    }
    out_path = os.path.join(os.path.dirname(__file__), "..", "vectors", "gus-normative-002.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    print(f"# escribiendo {os.path.abspath(out_path)}")


if __name__ == "__main__":
    main()
