# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Configuración global de la suite de pruebas Python.

GUS_ALLOW_INSECURE_REF=1: la suite de tests firma con el esquema hash-only
de referencia (WOTS16-MERKLE-REF-SHA256), que `adapters.make_adapter`
mantiene deshabilitado por defecto por no ser apto para producción.
Los tests de regresión de seguridad verifican que la puerta está cerrada
por defecto y que solo se abre con la bandera explícita.
"""

import os

os.environ.setdefault("GUS_ALLOW_INSECURE_REF", "1")
