# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Perfil GUS-3339: mapping exacto instante GUS ↔ fecha-hora RFC 3339 (UTC).

Perfil de notación de la versión 3.0.0 (documento normativo:
docs/profiles/gus-3339-perfil.md / docs/en/profiles/gus-3339-profile.md,
ES espejo informativo, EN prevalece). Vectores normativos:
vectors/gus-3339-002.json (GUS 3.0.0; la 001 está ARCHIVADA en
vectors/archive/).

Reglas del perfil (GUS 3.0.0 — puente vía TAI/TCJ, Cap 7/Cap 13):

1. Solo instante UTC. La forma canónica es ``AAAA-MM-DDTHH:MM:SSZ``
   (separador ``T`` y sufijo ``Z`` en mayúsculas; el parser acepta solo
   mayúsculas — RFC 3339 permite minúsculas, este perfil no: es un
   perfil canónico estricto, no un parser general).
2. Offsets de zona (``+01:00``) rechazados: quien recibe hora local la
   convierte a UTC antes de entrar al perfil.
3. Segundo ``:60`` (etiqueta de segundo intercalar UTC) rechazado: la
   escala GUS no tiene segundos intercalares internos y plegar ``:60``
   en 00:00:00 del día siguiente rompería la inyectividad; una fuente
   UTC que emite ``:60`` DEBE convertir antes (regla MUST del perfil).
   La etiqueta ``:60`` SÍ existe en la conversión (el segundo atómico no
   se pierde: GUS 3.0.0 aplica la tabla TAI−UTC histórica — ver
   ``gerarion.tai`` — de modo que cruzar un intercalar histórico avanza
   el instante GUS 2 s por segundo Unix 1).
4. Dominio: años gregorianos 0000..9999. El origen GUS (año -5) queda
   fuera del dominio del formato RFC 3339 — para ese rango se usa el
   string canónico GUS o el instante entero, nunca RFC 3339.
5. Aritmética entera pura vía JDN gregoriano proleptico; sin ``datetime``
   ni punto flotante (el año 0000 y las fechas negativas de Unix son
   exactas).

Puente (GUS 3.0.0, Cap 13): unix → TAI (tabla IERS) → TCJ (= TAI + 8 400 s)
→ GUS. Espejo exacto en la dirección inversa (sin ambigüedad).
etiquetado ``unix = I − GUS_UNIX_OFFSET``. Ambas escalas son
"etiqueta sin intercalares", así que el mapping es biyectivo en el
dominio declarado (ver §9 de la spec para la frontera exacta UTC/TAI).
"""

from __future__ import annotations

import re

from .calendar import GeroEinval, jdn, jdn_to_gregorian
from .calendar import ORIGIN_JDN
from .tai import instant_from_unix, unix_from_instant

#: JDN (gregoriano proleptico) del 1970-01-01.
UNIX_EPOCH_JDN = 2_440_588

#: Instante GUS en el second 0 de Unix: días del origen a la época Unix
#: × 86 400. Equivalencia: ``unix = instant − GUS_UNIX_OFFSET``.
GUS_UNIX_OFFSET = (UNIX_EPOCH_JDN - ORIGIN_JDN) * 86_400  # = 62_318_160_000

_RFC3339_RE = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
    r"T(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})Z$"
)

MAX_YEAR = 9999


def instant_to_rfc3339(instant: int) -> str:
    """Instante GUS → ``AAAA-MM-DDTHH:MM:SSZ`` (perfil GUS-3339).

    Lanza GeroEinval si el instante queda fuera del dominio de años
    0000..9999 de RFC 3339.
    """
    unix = unix_from_instant(instant)  # GUS → TCJ → TAI → UTC (tabla IERS)
    days, rem = divmod(unix, 86_400)
    year, month, day = jdn_to_gregorian(UNIX_EPOCH_JDN + days)
    if not 0 <= year <= MAX_YEAR:
        raise GeroEinval(
            f"GERO_E3339: instante fuera del dominio RFC 3339 (año {year})"
        )
    hour, rem2 = divmod(rem, 3600)
    minute, second = divmod(rem2, 60)
    return (
        f"{year:04d}-{month:02d}-{day:02d}"
        f"T{hour:02d}:{minute:02d}:{second:02d}Z"
    )


def instant_from_rfc3339(stamp: str) -> int:
    """``AAAA-MM-DDTHH:MM:SSZ`` (perfil GUS-3339) → instante GUS.

    Rechaza: offsets de zona, ``:60``, fechas gregorianas inválidas,
    años fuera de 0000..9999 y cualquier forma no canónica (minúsculas
    ``t``/``z`` incluidas).
    """
    m = _RFC3339_RE.match(stamp)
    if not m:
        raise GeroEinval(f"GERO_E3339: sintaxis fuera de perfil: {stamp!r}")
    hour = int(m.group("hour"))
    minute = int(m.group("minute"))
    second = int(m.group("second"))
    # F1: la hora no se normaliza nunca; campos fuera de rango se rechazan.
    if hour > 23 or minute > 59 or second > 59:
        raise GeroEinval(
            f"GERO_E3339: campo horario fuera de rango (00–23:59:59): {stamp!r}"
        )
    if second == 60:
        raise GeroEinval(
            "GERO_E3339: :60 (segundo intercalar UTC) no pertenece a la "
            "escala GUS; conviértelo a etiqueta UTC/Unix antes (MUST del perfil)"
        )
    year = int(m.group("year"))
    month = int(m.group("month"))
    day = int(m.group("day"))
    # Valida la fecha (Feb 30, mes 13, etc.) con el roundtrip JDN exacto.
    j = jdn(year, month, day)
    if jdn_to_gregorian(j) != (year, month, day):
        raise GeroEinval(f"GERO_E3339: fecha inválida: {stamp!r}")
    unix = (j - UNIX_EPOCH_JDN) * 86400 + int(m.group("hour")) * 3600 + int(m.group("minute")) * 60 + second
    return instant_from_unix(unix)  # GUS 3.0.0: unix → TAI → TCJ → GUS
