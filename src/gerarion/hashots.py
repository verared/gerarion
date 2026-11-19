# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Shim retrocompatible para el módulo deprecado ``hashots``.

La implementación vive en ``gerarion.deprecated.hashots`` y está
DEPRECADA: construcción educativa hash-only sin auditoría, no apta
para producción. Importarlo por la ruta plana emite un
``DeprecationWarning``; el stack activo (gst/, cli) lo carga de forma
condicional y funciona sin él.
"""

import warnings

warnings.warn(
    "gerarion.hashots está DEPRECATADO: usa gerarion.deprecated.hashots "
    "o, en producción, SLH-DSA/ML-DSA (FIPS 205/204) vía gerarion.gst.adapters.",
    DeprecationWarning,
    stacklevel=2,
)

from .deprecated.hashots import *  # noqa: E402,F401,F403
from .deprecated import hashots as _impl  # noqa: E402

globals().update(
    {
        _k: _v
        for _k, _v in vars(_impl).items()
        if not _k.startswith("__")
    }
)
