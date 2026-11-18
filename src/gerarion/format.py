# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Formato canónico de marca temporal Geroriana y normalización de entradas.

Implementa la especificación de formatos (spec GUS 2.1, §6):

    AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O]

    Obligatorios:   AAAAYY-MM-DD-X      (fecha + letra de día Nuvid)
    Opcionales:     -HH:MM:SS-CC-TCJ±O  (hora, ciclo, offset temporal)

Errores canónicos:
    GERO_EINVAL     campo fuera de rango o sintaxis inválida
    GERO_ETEMPALUM  día Tempalum inexistente para ese tipo de año
    GERO_EWEEK      letra de día Nuvid inconsistente con la calculada
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from . import calendar as cal
from .calendar import GeroEinval, GeroError, GeroItemporal

TIMESTAMP_RE = re.compile(
    r"^(?P<year>\d{1,6})(?:(?P<era>DY|AY))?"
    r"[-.](?P<month>\d{1,2})[-.](?P<day>\d{1,2})[-.]"
    r"(?P<weekday>[SLMATVBslmatvb])"
    r"(?:[-](?P<hour>\d{1,2}):(?P<minute>\d{1,2}):(?P<second>\d{1,2})"
    r"[-](?P<cycle>SC|LC|sc|lc)"
    r"[-]TCJ(?P<offset>[+-]\d{1,2}))?$"
)

WEEKDAY_LETTERS = {abbrev: idx for idx, (_, abbrev, _latin) in enumerate(cal.WEEKDAYS)}

CANONICAL_CTX = "GUS2-TS"


@dataclass
class ParsedTimestamp:
    """Marca temporal parseada y normalizada."""

    year: int            # años desde el origen (>= 0: DY; < 0: AY)
    month: int
    day: int
    weekday_index: int
    hour: int = 0
    minute: int = 0
    second: int = 0
    autocycle: bool = True   # ciclo inferido de la hora
    cycle: str | None = None  # si el emisor declaró SC/LC explícito
    offset: int = 0           # TCJ en horas
    flags: List[str] = field(default_factory=list)


def normalize(raw: str) -> str:
    """Normaliza una entrada a formato canónico sin validar el calendario."""
    s = raw.strip().upper().replace(" ", "-")
    s = s.replace(".", "-")
    return s


def parse(raw: str, *, strict_weekday: bool = False) -> ParsedTimestamp:
    """Parsea una marca temporal Geroriana aplicando las reglas 1-7.

    Las violaciones recuperables se reportan en `flags`; la letra de día
    calculada siempre prevalece sobre la declarada (REGLA 4). Con
    `strict_weekday=True` el conflicto eleva GERO_EWEEK en lugar de corregir.
    """
    cleaned = normalize(raw)
    m = TIMESTAMP_RE.match(cleaned)
    if not m:
        raise GeroEinval(f"Sintaxis inválida: {raw!r}")
    flags: List[str] = []

    year = int(m.group("year"))
    era = m.group("era")
    if era is None:
        flags.append("era_assumed_DY")          # REGLA 3
        era = "DY"
    if era == "AY":
        year = -year
    elif year == 0 and "era_assumed_DY" in flags:
        pass

    month = int(m.group("month"))
    day = int(m.group("day"))
    declared = m.group("weekday").upper()

    # REGLA 5: Tempalum solo en años Gran Tempalum — la valida to_gerarion.
    try:
        gdate = cal.from_gerarion(year, month, day)
    except GeroItemporal:
        raise
    except GeroEinval:
        raise

    actual_idx = gdate.weekday_index
    if WEEKDAY_LETTERS[declared] != actual_idx:
        if strict_weekday:
            raise GeroError(
                f"GERO_EWEEK: letra declarada {declared} != calculada "
                f"{cal.WEEKDAYS[actual_idx][1]}"
            )
        flags.append("weekday_corrected")       # REGLA 4

    hour = minute = second = 0
    cycle: str | None = None
    offset = 0
    if m.group("hour") is not None:
        hour, minute, second = (
            int(m.group("hour")),
            int(m.group("minute")),
            int(m.group("second")),
        )
        if hour > 23 or minute > 59 or second > 59:
            raise GeroEinval("Hora fuera de rango")
        cycle = m.group("cycle").upper() if m.group("cycle") else None
        offset = int(m.group("offset") or 0)
        if cycle is not None:
            expected = cal.cycle_of(hour)
            if cycle != expected:
                flags.append("cycle_corrected")  # REGLA 4 aplicada al ciclo
                cycle = expected
        else:
            cycle = cal.cycle_of(hour)

    return ParsedTimestamp(
        year=year,
        month=month,
        day=day,
        weekday_index=actual_idx,
        hour=hour,
        minute=minute,
        second=second,
        cycle=cycle,
        offset=offset,
        flags=flags,
    )


def to_canonical(parsed: ParsedTimestamp) -> str:
    """Serializa a formato canónico completo."""
    era = "DY" if parsed.year >= 0 else "AY"
    yy = abs(parsed.year)
    date = cal.from_gerarion(parsed.year, parsed.month, parsed.day)
    _, abbrev = date.weekday
    base = f"{yy:04d}{era}-{parsed.month:02d}-{parsed.day:02d}-{abbrev}"
    if parsed.cycle is None:
        return base
    cycle = parsed.cycle or cal.cycle_of(parsed.hour)
    return (
        f"{base}-{parsed.hour:02d}:{parsed.minute:02d}:{parsed.second:02d}"
        f"-{cycle}-TCJ{parsed.offset:+d}"
    )


def canonical_bytes(canon: str, instant: int, context: str = CANONICAL_CTX) -> bytes:
    """Bytes canónicos firmables: contexto || marca || instante.

    El contexto evita colisiones de dominio con otros usos del mismo hash.
    """
    return f"{context}\n{canon}\n{instant}\n".encode("utf-8")
