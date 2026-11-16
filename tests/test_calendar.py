"""Vectores normativos de GUS 2.0 (spec §3-§4) + erratas documentadas.

Origen y verificadores:
  - JDN origen 1719313 = 21 marzo año astronómico -5 (spec §3).
  - jdn(2026, 5, 23) = 2461184 (vector normativo).
  - Estructura interna del año 2031 DY: fin del mes 12, Tempalum, año nuevo
    2032 (vectores normativos de la spec — todos reproducidos aquí).
  - Errata E-01 (docs/errata-v1.2.md): el vector "2026-03-21 → 2031DY-01-01-S"
    del borrador histórico v1.2 era matemáticamente inconsistente (360 días
    de separación con el vector del año nuevo 2032, que exige longitud
    364/371). El algoritmo canónico ubica 2031DY-01-01 en 2026-03-17, y esa
    es la definición normativa de GUS 2.0. El inicio de año oscila dentro de
    la cota de drift; "21 de marzo" es una descripción aproximada, no una
    regla.
"""

from __future__ import annotations

import pytest

from gerarion import calendar as cal
from gerarion.calendar import GeroEinval, GeroItemporal

# ---------------------------------------------------------------------------
# Constantes y origen
# ---------------------------------------------------------------------------


def test_origin_jdn():
    assert cal.jdn(-5, 3, 21) == 1_719_313


def test_normative_jdn_vector():
    assert cal.jdn(2026, 5, 23) == 2_461_184


def test_origin_is_soludyia():
    assert cal.to_gerarion(0).weekday == ("Soludyia", "S")


def test_errata_e07_origin_independence():
    # E-07: el ancla es 1 Keuphero del año 0 (no del año 1); 6 a.C. es el año 0.
    d0 = cal.to_gerarion(0)
    assert (d0.year, d0.month, d0.day) == (0, 1, 1)
    d1 = cal.to_gerarion(cal.year_start_day_index(1))
    assert (d1.year, d1.month, d1.day) == (1, 1, 1)
    # El año 1 comienza 364 días después del origen, en 5 a.C. (-4 astronómico).
    assert cal.gregorian_from_day_index(cal.year_start_day_index(1)) == (-4, 3, 19)
    # Independencia: la equivalencia gregoriana de 2031DY-01-01 (derivada del
    # acumulador sobre el origen) coincide con la ruta por contador puro.
    assert cal.jdn(2026, 3, 17) - cal.ORIGIN_JDN == cal.year_start_day_index(2031)


# ---------------------------------------------------------------------------
# Vectores normativos de la spec §3 (estructura del año 2031 DY)
# ---------------------------------------------------------------------------


def _conv_greg(y, m, d):
    return cal.to_gerarion(cal.day_index_from_gregorian(y, m, d))


@pytest.mark.parametrize(
    "greg,expected",
    [
        # (gregoriano, (año, mes, día, letra))
        ((2027, 3, 11), (2031, 12, 30, "M")),
        ((2027, 3, 12), (2031, 0, 1, "A")),
        ((2027, 3, 15), (2031, 0, 4, "B")),
        ((2027, 3, 16), (2032, 1, 1, "S")),
        # Errata E-02: el borrador histórico daba Yeshuvid 2031 el 19 abril
        # (asumiendo inicio 21 marzo). Con el inicio algorítmico (17 marzo),
        # 30 Keuphero es 15 abril; el día Nuvid sigue siendo Loondyia.
        ((2026, 4, 15), (2031, 1, 30, "L")),
        ((2026, 5, 23), (2031, 3, 8, "T")),    # hoy
    ],
)
def test_normative_vectors(greg, expected):
    got = _conv_greg(*greg)
    assert (got.year, got.month, got.day, got.weekday[1]) == expected


def test_errata_new_year_2031():
    """Errata: el algoritmo canónico da 17 marzo 2026 (no 21)."""
    d = _conv_greg(2026, 3, 17)
    assert (d.year, d.month, d.day, d.weekday[1]) == (2031, 1, 1, "S")
    # y el 21 de marzo queda dentro del mes 1, no en el inicio:
    d2 = _conv_greg(2026, 3, 21)
    assert (d2.year, d2.month, d2.weekday[1]) == (2031, 1, "T")


# ---------------------------------------------------------------------------
# Invariantes estructurales (spec §3-§5)
# ---------------------------------------------------------------------------


def test_all_year_lengths_multiple_of_7():
    for year in range(0, 200):
        assert cal.year_length(year) % 7 == 0


def test_every_year_starts_on_soludyia():
    for year in range(1, 200):
        start = cal.year_start_day_index(year)
        assert cal.to_gerarion(start).weekday[1] == "S", year


def test_gran_tempalum_pattern_matches_spec():
    """Patrón normativo (spec §3): 5, 11, 16, 22, 28, 33, 39, 45..."""
    got = [y for y in range(0, 46) if cal.is_gran_tempalum(y)]
    assert got == [5, 11, 16, 22, 28, 33, 39, 45]


def test_drift_bound_sawtooth():
    """Cota del drift (spec §4): |Δn| < 7 días para todo n."""
    total = 0
    for year in range(1, 500):
        total += cal.year_length(year - 1)
        tropical = year * 365.24219
        drift = total - tropical
        assert -7.0 < drift <= 0.0001, (year, drift)


def test_tempalum_days_names():
    normal = cal.to_gerarion(cal.from_gerarion(2031, 0, 4).day_index)
    assert normal.tempalum_name == "Ikiyeh"
    gran = cal.to_gerarion(cal.from_gerarion(2034, 0, 11).day_index)
    assert gran.tempalum_name == "Nuvivid VII"


def test_two_saturdays_in_gran_tempalum():
    day4 = cal.from_gerarion(2034, 0, 4)
    day11 = cal.from_gerarion(2034, 0, 11)
    assert day4.weekday[0] == "Sabatyeh"
    assert day11.weekday[0] == "Sabatyeh"


# ---------------------------------------------------------------------------
# Rango y errores canónicos
# ---------------------------------------------------------------------------


def test_month_31_invalid():
    with pytest.raises(GeroEinval):
        cal.from_gerarion(2031, 3, 31)


def test_month_13_invalid():
    with pytest.raises(GeroEinval):
        cal.from_gerarion(2031, 13, 1)


def test_tempalum_day5_in_normal_year_invalid():
    with pytest.raises(GeroItemporal):
        cal.from_gerarion(2031, 0, 5)


def test_tempalum_day5_in_gran_year_valid():
    d = cal.from_gerarion(2034, 0, 5)
    assert d.tempalum_name == "Nuvivid I"


# ---------------------------------------------------------------------------
# Instantes y ciclos
# ---------------------------------------------------------------------------


def test_instant_roundtrip():
    date = cal.from_gerarion(2031, 3, 8)
    instant = cal.instant_from_parts(date.day_index, 9, 30, 0)
    back, hour, minute, second = cal.instant_parts(instant)
    assert back == date and (hour, minute, second) == (9, 30, 0)


def test_no_leap_seconds_linear_count():
    """El invariante de continuidad: día n siempre tiene 86400 segundos."""
    for day in (0, 1000, 10000, 100000):
        a = cal.instant_from_parts(day, 0, 0, 0)
        b = cal.instant_from_parts(day + 1, 0, 0, 0)
        assert b - a == 86_400


def test_instants_are_comparable_across_eras():
    """Un instante AY es negativo; el orden temporal es total."""
    before = cal.instant_from_parts(-10)
    origin = cal.instant_from_parts(0)
    assert before < origin


@pytest.mark.parametrize(
    "hour,cycle", [(0, "LC"), (5, "LC"), (6, "SC"), (12, "SC"), (17, "SC"), (18, "LC"), (23, "LC")]
)
def test_cycle_rule(hour, cycle):
    assert cal.cycle_of(hour) == cycle


# ---------------------------------------------------------------------------
# Idempotencia de conversión bidireccional (property test acotado)
# ---------------------------------------------------------------------------


def test_roundtrip_gregorian_gerarion():
    for di in range(0, 3001, 37):
        gy, gm, gd = cal.gregorian_from_day_index(di)
        assert cal.day_index_from_gregorian(gy, gm, gd) == di
