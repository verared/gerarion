# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Pruebas de quick_verify (verificación rápida O(1), Cap 13.8 v1.2).

Casos compartidos en vectors/gus-quickverify-001.json y consumidos también
por web/gerarion.mjs (quickVerify) e impl-c (gus_quick_verify).
"""

import json
from pathlib import Path

import pytest

from gerarion.format import quick_verify

VECTORS = Path(__file__).resolve().parent.parent / "vectors" / "gus-quickverify-001.json"


def _load() -> dict:
    return json.loads(VECTORS.read_text(encoding="utf-8"))


def test_quick_verify_valid():
    for case in _load()["valid"]:
        assert quick_verify(case["ts"]) is True, case["ts"]

def test_quick_verify_rejects_invalid():
    """Un cambio no canónico —letra, ciclo, rango, era— devuelve False.

    Detalle: en el código anterior (pre-quick_verify) la única forma de
    detectar el ciclo declarado equivocado era parse() + inspección manual
    de flags; cualquier consumidor que solo llamara a `parse(raw)` y
    comprobara campos obtenía True para el caso «21:45:10-SC» (el flag
    cycle_corrected se ignoraba): el vector invalid[1] codifica ese caso.
    """
    for case in _load()["invalid"]:
        assert quick_verify(case["ts"]) is False, case["ts"]

def test_quick_verify_no_levanta_excepciones():
    """quick_verify nunca propaga: cualquier entrada rara es simplemente False."""
    for raro in ("", "   ", "2031DT-03-08-T", "2031MY-03-08-X", "2031DY-03-08-T-TCJ+0"):
        assert quick_verify(raro) is False

def test_quick_verify_ciclo_manipulado_detectado():
    """Ciclo declarado ≠ calculado → False (flag cycle_corrected silencioso)."""
    assert quick_verify("2031DY-03-08-T-21:45:10-SC-TCJ+0") is False
    assert quick_verify("2031DY-03-08-T-21:45:10-LC-TCJ+0") is True
    assert quick_verify("2031DY-03-08-T-21:45:10-LC-TCJ+3") is True

def test_quick_verify_letra_manipulada_detectada():
    """Modo estricto: la letra declarada equivocada se rechaza (GERO_EWEEK)."""
    assert quick_verify("2031DY-03-08-S-09:30:00-SC-TCJ+0") is False
