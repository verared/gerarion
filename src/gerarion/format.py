# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Shim retrocompatible (v3.2.0): la implementación vive en ``gerarion.core.format``.

Las importaciones planas históricas siguen operando sin cambios::

    from gerarion.format import ...

Todo nombre público del módulo real se reexporta aquí (import relativo:
no crea una segunda identidad de clases); se prefiere la ruta nueva en
código nuevo.
"""

from .core import format as _impl

globals().update(
    {
        _k: _v
        for _k, _v in vars(_impl).items()
        if not _k.startswith("__")
    }
)

__all__ = [_k for _k in vars(_impl) if not _k.startswith("__")]
