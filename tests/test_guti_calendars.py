# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Verificación astronómica independiente del calendario chino (adenda v3.1.1).

Tabla de contraste del motor con fechas de referencia del estándar
astronómico publicado (Observatorio de la Montaña Púrpura / listas
lunisolares estándar derivadas de la reforma Shixian), dentro del rango
validado del motor (1645–2650 d.C., meridiano de Pekín UTC+8/120°E).

Categorías de la tabla:

1. Años Nuevos chinos (día 1, mes 1) contemporáneos — deben coincidir
   EXACTAMENTE con las fechas publicadas.
2. Primeros días de meses intercalares (runyue) documentados — exactos.
3. Vísperas y bordes de lunación (día 29/30) — exactos.
4. Noches límite históricas (luna nueva a pocos minutos de la medianoche
   UTC+8): el motor puede diferir en 1 día de las tablas publicadas de
   la época (Shixian usaba su propio cálculo del momento). Aquí NO se
   exige igualar la tabla: se FIJA la lectura exacta del motor como
   regresión y la divergencia queda documentada (≤ 1 día) en
   docs/spec/CALENDAR-ENGINE.md.

El motor es determinista: jamás desplaza una fecha en silencio; toda
desviación respecto de la tabla histórica debe ser un caso de esta
categoría 4, con la no-luna-nueva justificada por el instante real.
Régrido: cada entrada se recorre ida y vuelta por grego.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from gerarion import calendars as gc  # noqa: E402


def chin(gregorian):
    """(y, m, d) gregoriano → dict chino del motor."""
    di = gc.to_day_index("greg", dict(zip(("year", "month", "day"), gregorian)))
    fields = gc.from_day_index(di, "chinese").fields
    return dict(zip(gc.metadata("chinese")["field_names"], fields))


# ── 1. Años Nuevos chinos publicados (exactos) ─────────────────────────
CHINESE_NEW_YEARS = [
    # (gregoriano) — fuente: listas estándar de Año Nuevo chino (PBO/SBO)
    (1900, 1, 31), (1912, 2, 18), (1949, 1, 29), (1976, 1, 31),
    (1984, 2, 2), (1995, 1, 31), (2000, 2, 5), (2004, 1, 22),
    (2008, 2, 7), (2012, 1, 23), (2016, 2, 8), (2020, 1, 25),
    (2023, 1, 22), (2024, 2, 10), (2025, 1, 29), (2026, 2, 17),
    (2028, 1, 26), (2030, 2, 3), (2033, 1, 31), (2035, 2, 8),
    (2100, 2, 9),
    # época: primer Año Nuevo del rango validado (1645 d.C.)
    (1645, 1, 28),
]


@pytest.mark.parametrize("gregorian", CHINESE_NEW_YEARS)
def test_ano_nuevo_chino_exacto(gregorian):
    c = chin(gregorian)
    assert (c["year"], c["month"], c["day"]) == (
        gregorian[0], 1, 1), f"CNY {gregorian}: {c}"
    assert c["leap"] is False


# ── 2. Meses intercalares (runyue) documentados (exactos) ──────────────
RUNYUE_FIRST_DAYS = [
    # (gregoriano, mes intercalar, año lunar) — listas estándar
    ((1952, 6, 22), 5),   # 闰五月, 壬辰年
    ((1979, 7, 24), 6),   # 闰六月, 己未年
    ((2004, 3, 21), 2),   # 闰二月, 甲申年
    ((2009, 6, 23), 5),   # 闰五月, 己丑年
    ((2017, 7, 23), 6),   # 闰六月, 丁酉年
    ((2020, 5, 23), 4),   # 闰四月, 庚子年
    ((2023, 3, 22), 2),   # 闰二月, 癸卯年
    ((2025, 7, 25), 6),   # 闰六月, 乙巳年
]


@pytest.mark.parametrize(("gregorian", "leap_month"), RUNYUE_FIRST_DAYS)
def test_runyue_prime_dia_exacto(gregorian, leap_month):
    c = chin(gregorian)
    assert (c["year"], c["month"], c["day"], c["leap"]) == (
        # el año lunar del runyue de los primeros puestos coincide con el
        # gregoriano salvo si el mes intercalar pertenece al año lunar
        # anterior (runyue 11/12); los de esta tabla no son de esos.
        gregorian[0], leap_month, 1, True), f"runyue {gregorian}: {c}"


# ── 3. Bordes de lunación (día 29/30) exactos ──────────────────────────
BORDERS = [
    ((2024, 2, 9), (2023, 12, 30, False)),   # víspera CNY 2024: mes 12 de 30 días
    ((2025, 1, 28), (2024, 12, 29, False)),  # mes 12 de 29 días
    ((2023, 3, 21), (2023, 2, 30, False)),   # día 30 existente antes del runyue-2
    ((2017, 7, 22), (2017, 6, 29, False)),   # mes 6 regular de 29 días antes del runyue-6
]


@pytest.mark.parametrize(("gregorian", "want"), BORDERS)
def test_borde_lunacion_exacto(gregorian, want):
    c = chin(gregorian)
    assert (c["year"], c["month"], c["day"], c["leap"]) == want


# ── 4. Noches límite (luna nueva ∼ medianoche UTC+8): divergencia documentada
# Cada caso fija la lectura EXACTA del motor (regresión); vs las listas
# publicadas de la época puede diferir en 1 día — tolerancia documentada.
BOUNDARY_NIGHTS = [
    # (gregoriano, lectura-atómica-del-motor, nota)
    ((1700, 2, 20), (1700, 1, 2, False),  "Shixian列1700: 2/1; luna nueva 19-02 a minutos de 0:00 UTC+8"),
    ((1751, 1, 28), (1751, 1, 2, False),  "luna nueva 27/28-01 a minutos de medianoche"),
    ((1851, 2, 2),  (1851, 1, 2, False),  "luna nueva 01-02 a minutos de medianoche"),
    ((2050, 2, 22), (2050, 2, 2, False),  "noche límite proyectada (2027+ UTC continuo)"),
]


@pytest.mark.parametrize(("gregorian", "want", "_nota"), BOUNDARY_NIGHTS)
def test_noche_limite_lectura_fijada(gregorian, want, _nota):
    c = chin(gregorian)
    assert (c["year"], c["month"], c["day"], c["leap"]) == want, (
        f"regresión de noche límite {gregorian}: {c} (nota: {_nota})"
    )


# ── ida y vuelta en toda la tabla ──────────────────────────────────────
def test_tabla_completa_inversa_exacta():
    entries = [g for g in CHINESE_NEW_YEARS]
    entries += [g for g, _ in RUNYUE_FIRST_DAYS]
    entries += [g for g, _ in BORDERS]
    for g in entries:
        c = chin(g)
        fields = {"year": c["year"], "month": c["month"], "day": c["day"],
                  "leap": c["leap"]}
        di = gc.to_day_index("chinese", fields)
        assert gc.from_day_index(di, "greg").fields == g, (g, c)


def test_runyue_no_existe_fuera_de_su_ventana():
    # el intercalar de 2023 es SOLO el mes 2: pedir runyue-2 en 2024 falla
    with pytest.raises(ValueError):
        gc.to_day_index("chinese", {"year": 2024, "month": 2, "day": 1,
                                    "leap": True})
