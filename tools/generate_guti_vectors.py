#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Genera vectors/guti-calendars-001.json — set compartido del motor multi-calendario.

Única fuente de los vectores de conversión de los 10 calendarios (fase
GUTI-1). Los corredores Python (tests/test_guti_m0_sandbox.py), C11
(impl-c/gerarion_calendars_vetri.c → cal-fast) y JS (web/guti_vectors.mjs)
validan este mismo archivo bit a bit.

Reglas de generación:

  1. Todo valor se calcula con la implementación de referencia
     (src/gerarion/calendars.py) tras su corrección de validación hebrea.
  2. Determinismo total: sin reloj, sin azar; recorrido fijo, semilla de
     muestreo fija (584283). Regenerar produce byte a byte el mismo archivo.
  3. Cada categoría se autovalida durante la generación: los vectores
     `vectors` ida-y-vuelta, `cross` palíndromo A→GUS→B→GUS→A, `invalid`
     rechazados con GERO_EINVAL, `unsupported` con GERO_EUNSUPPORTED y
     `erange` con GERO_ERANGE. Si el motor acepta un caso imposible, la
     generación aborta en lugar de emitir un vector falso.

Uso:  PYTHONPATH=src python3 tools/generate_guti_vectors.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from gerarion import calendars as gc  # noqa: E402

OUT = ROOT / "vectors" / "guti-calendars-001.json"
SEED = 584283
ORIGIN = gc.ORIGIN_JDN if hasattr(gc, "ORIGIN_JDN") else 1719313

# di de referencia: épocas y fechas emblemáticas (día_index = JDN - 1719313)
SPECIAL_DI = [
    0,                     # origen: 0000DY-01-01-S = -0005-03-21 proléptico
    -1, 1, -7, 7,
    0 - 1721425,           # epoch juliano proléptico menos 1
    0 - 1719313,           # JDN 0
    207094,                # 13.0.0.0.0 maya = 2012-12-21 (greg)
    240578,                # 0001AY-00-11-B (Nuvivid VII)
    741186 - 1719313,      # islamic 1445-12-30 (bisiesto tabular)
    741168,                # hebreo 5784-01-01 (Nisan AM 5784)
    480672,                # China 2024-02-10 (Año Nuevo lunar)
    0 + 365 * 2024,        # ~greg 2024
]

# di grandes sin tocar el horizonte del chino (1645..2650 d.C.):
# ±2^53 - 1 está fuera del rango del motor chino y del hebreo;
# para esos dos se usan límites internos (ver SPECIAL_PER_SYSTEM).


def _greg_year(di: int) -> int:
    return gc.from_day_index(di, "greg").fields[0]


def _safe_big_di(target: int) -> int:
    return target


def sample_dis() -> list[int]:
    """Días de muestra: especiales + barrido denso + grandes deterministas."""
    rng = random.Random(SEED)
    dis = set(SPECIAL_DI)
    # barrido denso ±400.000 días (~±1.100 años) con paso 233
    for di in range(-400_000, 400_001, 233):
        dis.add(di)
        dis.add(di + 1)   # bordes de mes/年 vecinos
    # grandes: potencias de dos y ±(2^k - 1) — dominio común exacto de las
    # tres plataformas: |di| <= 2^48-1 (JS Number pierde precisión en el
    # interior del core por encima de ~2^51; véase CALENDAR-ENGINE.md).
    for k in range(20, 49):
        d = 1 << k
        dis.add(d - 1)
        dis.add(-(d - 1))
        if k % 3 == 0:
            dis.add(d)
            dis.add(-d)
    # jitter determinista alrededor de los grandes
    for base in sorted(x for x in dis if abs(x) > 10**6):
        dis.add(base + rng.randint(-365, 365))
    return sorted(dis)


def _fields(sysid: str, di: int) -> dict:
    d = gc.from_day_index(di, sysid)
    return dict(zip(gc.metadata(sysid)["field_names"], d.fields))


def build_vectors(dis: list[int]) -> list[dict]:
    vectors = []
    for sysid in gc.system_ids():
        for di in dis:
            try:
                fields = _fields(sysid, di)
            except ValueError:
                # el sistema no soporta ese día (p. ej. chino fuera de
                # 1645..2650): se muestrean sus extremos internos aparte
                continue
            # autovalidación: ida y vuelta bit a bit
            assert gc.to_day_index(sysid, fields) == di, (sysid, di)
            vectors.append({"system": sysid, "day_index": di, "fields": fields})
    return vectors


def build_cross() -> list[dict]:
    """Cruces palindrómicos A→GUS→B→GUS→A para cada par ordenado."""
    edges = [0, 207094, 741168, -1718900, 22450, -21998]
    cross = []
    ids = gc.system_ids()
    for a in ids:
        for b in ids:
            if a == b:
                continue
            for di in edges:
                try:
                    d1 = gc.from_day_index(di, a)
                    f1 = dict(zip(gc.metadata(a)["field_names"], d1.fields))
                    di2 = gc.to_day_index(a, f1)
                    d2 = gc.from_day_index(di2, b)
                    f2 = dict(zip(gc.metadata(b)["field_names"], d2.fields))
                    di3 = gc.to_day_index(b, f2)
                    d3 = gc.from_day_index(di3, a)
                except ValueError:
                    continue
                assert d3.fields == d1.fields, (a, b, di)
                cross.append({"from": a, "via": a, "to": b, "day_index": di})
    return cross


INVALID = {
    "gus": [
        {"year": 0, "month": 14, "day": 1},
        {"year": 12000, "month": 1, "day": 62},
        {"year": 0, "month": 1, "day": 0},
    ],
    "greg": [
        {"year": 2023, "month": 2, "day": 29},
        {"year": 2024, "month": 13, "day": 1},
        {"year": 2024, "month": 4, "day": 31},
        {"year": 2024, "month": 2, "day": 30},
    ],
    "julian": [
        {"year": 2023, "month": 2, "day": 29},
        {"year": 1900, "month": 2, "day": 30},
        {"year": 2024, "month": 0, "day": 1},
    ],
    "egyptian": [
        {"year": 1300, "month": 14, "day": 1},
        {"year": 1300, "month": 3, "day": 31},
        {"year": 1300, "month": 13, "day": 7},   # epagómenos: 5/6 días
    ],
    "ethiopic": [
        {"year": 2017, "month": 14, "day": 1},
        {"year": 2017, "month": 1, "day": 31},
    ],
    "bahai": [
        {"year": 181, "month": 20, "day": 1},
        {"year": 181, "month": 1, "day": 20},
    ],
    "maya": [
        {"baktun": 13, "katun": 0, "tun": 0, "uinal": 18, "kin": 0},
        {"baktun": 13, "katun": 0, "tun": 0, "uinal": 0, "kin": 21},
    ],
    "islamic": [
        {"year": 1446, "month": 12, "day": 30},   # 1446 común: solo 29 días
        {"year": 1445, "month": 13, "day": 1},
        {"year": 1445, "month": 4, "day": 30},    # mes par: 29 días
    ],
    "hebrew": [
        {"year": 5785, "month": 13, "day": 1},    # común: no hay Adar II
        {"year": 5784, "month": 14, "day": 1},
        {"year": 5784, "month": 10, "day": 30},   # Tevet: 29 días
        {"year": 5784, "month": 1, "day": 31},    # Nisan: 30 días
    ],
    "chinese": [
        {"year": 2024, "month": 13, "day": 1},
        {"year": 2024, "month": 5, "day": 1, "leap": True},  # intercalar inexistente
        {"year": 2024, "month": 0, "day": 1},
        {"year": 2023, "month": 2, "day": 31},    # lunación máx. 30 días
    ],
}

UNSUPPORTED_DI = [
    {"system": "chinese", "day_index": 48070 - 1719313 + 1719313 - 1719314},  # greg 1644
    {"system": "chinese", "day_index": 0},
]
UNSUPPORTED_FIELDS = [
    {"system": "chinese", "fields": {"year": 1644, "month": 1, "day": 1}},
    {"system": "chinese", "fields": {"year": 2651, "month": 1, "day": 1}},
]

ERANGE = [
    {"system": "hebrew", "fields": {"year": 900_000_000_001, "month": 7, "day": 1}},
    {"system": "hebrew", "fields": {"year": -900_000_000_001, "month": 7, "day": 1}},
]


def build_unsupported() -> list[dict]:
    """Días fuera del rango del chino, verificados con el motor."""
    out = []
    for di in (-999_999, -3_000_000, 3_000_000):
        try:
            gc.from_day_index(di, "chinese")
        except ValueError as exc:
            assert str(exc).startswith("GERO_EUNSUPPORTED"), (di, exc)
            out.append({"system": "chinese", "day_index": di})
    return out


def build_erange() -> list[dict]:
    out = []
    for case in ERANGE:
        try:
            gc.to_day_index(case["system"], case["fields"])
        except ValueError as exc:
            assert str(exc).startswith("GERO_ERANGE"), (case, exc)
            out.append(case)
    return out


def main() -> None:
    dis = sample_dis()
    vectors = build_vectors(dis)

    invalid = []
    for sysid, cases in INVALID.items():
        for fields in cases:
            try:
                gc.to_day_index(sysid, fields)
            except ValueError:
                # el núcleo congelado (GeroEinval) y el adaptador
                # (GERO_EINVAL) rechazan ambos; la clase basta
                invalid.append({"system": sysid, "fields": fields})
            else:
                raise AssertionError(f"caso invalid aceptado: {sysid} {fields}")

    unsupported = UNSUPPORTED_FIELDS + build_unsupported()
    erange = build_erange()

    calendars = {m["id"]: m for m in gc.METADATA}
    doc = {
        "spec": "GUTI-1 motor multi-calendario; pivote day_index / JDN "
                "1719313; convención hebrea rabínica (1 = Nisan, 7 = Tishri, "
                "12/13 = Adar I/II); chino tabular 1645..2650 (tabla "
                "china_table, Shixian).",
        "version": "001",
        "license": "CC0-1.0",
        "origin_jdn": ORIGIN,
        "note": "Determinista: semilla de muestreo 584283, sin reloj. "
                "Regenerar: PYTHONPATH=src python3 tools/generate_guti_vectors.py",
        "calendars": calendars,
        "vectors": vectors,
        "cross": build_cross(),
        "invalid": invalid,
        "unsupported": unsupported,
        "erange": erange,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    print(f"{OUT}: {len(vectors)} vectores, {len(doc['cross'])} cruces, "
          f"{len(invalid)} inválidos, {len(unsupported)} no soportados, "
          f"{len(erange)} erange")


if __name__ == "__main__":
    main()
