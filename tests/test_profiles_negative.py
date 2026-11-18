# -*- coding: utf-8 -*-
"""Regresión F1: entradas inválidas del perfil GUS-3339 nunca se normalizan.

Consume vectors/gus-3339-negative-001.json (casos negativos compartidos por
Python, JS y C). Cualquier aceptación de estos casos es un fallo.
"""
import json
from pathlib import Path

import pytest

from gerarion import instant_from_parts, instant_from_rfc3339

VECTORS = Path(__file__).resolve().parent.parent / "vectors"
NEG = json.loads((VECTORS / "gus-3339-negative-001.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "case", NEG["reject_rfc3339"], ids=[c["rfc3339"] for c in NEG["reject_rfc3339"]]
)
def test_rfc3339_rechazado(case):
    with pytest.raises(Exception, match="GERO_"):
        instant_from_rfc3339(case["rfc3339"])


@pytest.mark.parametrize(
    "case", NEG["instant_parts"], ids=[c["why"] for c in NEG["instant_parts"]]
)
def test_instant_parts_rechazado(case):
    with pytest.raises(Exception, match="GERO_"):
        instant_from_parts(case["day_index"], case["hour"], case["minute"], case["second"])
