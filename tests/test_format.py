"""Tests del formato canónico y normalización (spec GUS 2.0 §6)."""

from __future__ import annotations

import pytest

from gerarion import format as fmt
from gerarion.calendar import GeroItemporal, GeroError


# ---------------------------------------------------------------------------
# Reglas de normalización (spec §6)
# ---------------------------------------------------------------------------


def test_rule1_uppercase():
    parsed = fmt.parse("2031dy-03-08-t")
    assert parsed.month == 3 and parsed.day == 8


def test_rule2_zero_padding():
    parsed = fmt.parse("2031DY-3-8-T")
    assert fmt.to_canonical(parsed).startswith("2031DY-03-08-T")


def test_rule3_era_assumed():
    parsed = fmt.parse("2031-03-08-T")
    assert parsed.year == 2031
    assert "era_assumed_DY" in parsed.flags


def test_rule4_weekday_corrected():
    # 8 Tritom 2031 es Trustdyia (T); declarar S se corrige y se marca
    parsed = fmt.parse("2031DY-03-08-S")
    assert "weekday_corrected" in parsed.flags
    assert fmt.to_canonical(parsed).endswith("-T")


def test_rule4_strict_weekday():
    with pytest.raises(GeroError):
        fmt.parse("2031DY-03-08-S", strict_weekday=True)


def test_rule5_tempalum_normal_year_invalid():
    with pytest.raises(GeroItemporal):
        fmt.parse("2031DY-00-07-T")


def test_rule5_tempalum_gran_year_valid():
    parsed = fmt.parse("2034DY-00-07-V")
    assert parsed.month == 0 and parsed.day == 7


def test_rule7_full_timestamp():
    parsed = fmt.parse("2031DY-03-08-T-09:30:00-SC-TCJ+0")
    assert parsed.hour == 9 and parsed.cycle == "SC" and parsed.offset == 0


def test_full_canonical_roundtrip():
    raw = "2031DY-03-08-T-09:30:00-SC-TCJ+0"
    parsed = fmt.parse(raw)
    assert fmt.to_canonical(parsed) == raw


def test_cycle_corrected_flag():
    parsed = fmt.parse("2031DY-03-08-T-13:00:00-SC-TCJ+0")
    assert parsed.cycle == "SC"
    parsed2 = fmt.parse("2031DY-03-08-T-13:00:00-LC-TCJ+0")
    assert parsed2.cycle == "SC" and "cycle_corrected" in parsed2.flags


# ---------------------------------------------------------------------------
# Tabla de entradas inválidas (spec §6)
# ---------------------------------------------------------------------------


def test_month_out_of_range():
    with pytest.raises(Exception):
        fmt.parse("2031DY-13-01-T")


def test_day_out_of_range():
    with pytest.raises(Exception):
        fmt.parse("2031DY-03-31-T")


def test_arrow_chars_rejected():
    with pytest.raises(Exception):
        fmt.parse("2031DY-03-08-T→")


# ---------------------------------------------------------------------------
# Bytes canónicos firmables
# ---------------------------------------------------------------------------


def test_canonical_bytes_deterministic():
    a = fmt.canonical_bytes("2031DY-03-08-T", 12345)
    b = fmt.canonical_bytes("2031DY-03-08-T", 12345)
    assert a == b
    c = fmt.canonical_bytes("2031DY-03-08-T", 12346)
    assert a != c
    assert b"GUS2-TS" in a
