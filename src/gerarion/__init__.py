# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Gerarion Universal Standard (GUS) v2.0 — implementación de referencia.

Un sistema de tiempo universal, regular y con marcas verificables:

    - Calendario regular: 12 meses x 30 días + Tempalum (4/11 días de cierre).
    - Semana invariante: toda fecha fija cae siempre en el mismo día Nuvid.
    - Instante continuo: sin segundos intercalares, conteo lineal sobre TAI.
    - Marca temporal firmada (GST) con esquemas hash-only (post-cuánticos).
    - Notario diario Merkle encadenado: alterar el pasado exige romper SHA-256
      y todas las réplicas publicadas a la vez.

Ejemplo:

    from gerarion import calendar as cal
    cal.to_gerarion(cal.day_index_from_gregorian(2026, 5, 23)).canonical()
    # -> '2031DY-03-08-T'
"""

from .core.calendar import (
    GeroEinval,
    GeroError,
    GeroItemporal,
    GerarionDate,
    from_gerarion,
    instant_from_parts,
    instant_parts,
    parts_from_instant,
    to_gerarion,
)
from .core.format import ParsedTimestamp, parse, quick_verify, to_canonical, to_compact
from .tcj.tai import (
    TCJ_OFFSET_SECONDS,
    TAI_MINUS_UTC_TABLE,
    instant_from_unix,
    tai_minus_utc,
    unix_from_instant,
)
from .gst.envelope import GtsDocument, create as create_gst, verify as verify_gst
from .interop.profiles import (
    GUS_UNIX_OFFSET,
    instant_from_rfc3339,
    instant_to_rfc3339,
)

# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Gerarion Universal Standard (GUS) v2.0 — implementación de referencia.

Un sistema de tiempo universal, regular y con marcas verificables:

    - Calendario regular: 12 meses x 30 días + Tempalum (4/11 días de cierre).
    - Semana invariante: toda fecha fija cae siempre en el mismo día Nuvid.
    - Instante continuo: sin segundos intercalares, conteo lineal sobre TAI.
    - Marca temporal firmada (GST) con esquemas hash-only (post-cuánticos).
    - Notario diario Merkle encadenado: alterar el pasado exige romper SHA-256
      y todas las réplicas publicadas a la vez.

Ejemplo:

    from gerarion import calendar as cal
    cal.to_gerarion(cal.day_index_from_gregorian(2026, 5, 23)).canonical()
    # -> '2031DY-03-08-T'
"""

from .core.calendar import (
    GeroEinval,
    GeroError,
    GeroItemporal,
    GerarionDate,
    from_gerarion,
    instant_from_parts,
    instant_parts,
    parts_from_instant,
    to_gerarion,
)
from .core.format import ParsedTimestamp, parse, quick_verify, to_canonical, to_compact
from .tcj.tai import (
    TCJ_OFFSET_SECONDS,
    TAI_MINUS_UTC_TABLE,
    instant_from_unix,
    tai_minus_utc,
    unix_from_instant,
)
from .gst.envelope import GtsDocument, create as create_gst, verify as verify_gst
from .interop.profiles import (
    GUS_UNIX_OFFSET,
    instant_from_rfc3339,
    instant_to_rfc3339,
)

__version__ = "3.2.0a1"


__all__ = [
    "GeroEinval",
    "GeroError",
    "GeroItemporal",
    "GerarionDate",
    "ParsedTimestamp",
    "GtsDocument",
    "GUS_UNIX_OFFSET",
    "unix_from_instant",
    "create_gst",
    "from_gerarion",
    "instant_from_parts",
    "instant_from_rfc3339",
    "instant_from_unix",
    "instant_parts",
    "instant_to_rfc3339",
    "parse",
    "parts_from_instant",
    "quick_verify",
    "TCJ_OFFSET_SECONDS",
    "TAI_MINUS_UTC_TABLE",
    "tai_minus_utc",
    "to_canonical",
    "to_compact",
    "to_gerarion",
    "verify_gst",
    "__version__",
]

