# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
# -*- coding: utf-8 -*-
"""Regresión F2: el Gran Tempalum opera simétricamente en la era AY.

Consume vectors/gus-regression-001.json (compartido por Python, JS, C y
tools/verify_gus.py). El verificador monolítico antes rechazaba casos AY
(GERO_ETEMPALUM); ahora debe aceptarlos en la capa calendario.
"""
import json
import sys
from pathlib import Path

import pytest

from gerarion import from_gerarion, parse, to_canonical, to_gerarion

REPO = Path(__file__).resolve().parent.parent
VEC = json.loads((REPO / "vectors" / "gus-regression-001.json").read_text(encoding="utf-8"))
sys.path.insert(0, str(REPO / "tools"))
from verify_gus import verify_document  # noqa: E402


@pytest.mark.parametrize(
    "case", VEC["calendar_ay"], ids=[c["canonical"] for c in VEC["calendar_ay"]]
)
def test_nucleo_ay_symmetric(case):
    d = to_gerarion(case["day_index"])
    assert d.canonical() == case["canonical"]
    assert d.weekday[0] == case["weekday"], (d.weekday, case["weekday"])
    back = from_gerarion(d.year, d.month, d.day)
    assert back.day_index == case["day_index"]
    p = parse(case["canonical"])
    assert from_gerarion(p.year, p.month, p.day).day_index == case["day_index"]
    assert to_canonical(p) == case["canonical"]


@pytest.mark.parametrize(
    "case", VEC["calendar_ay"], ids=[c["canonical"] for c in VEC["calendar_ay"]]
)
def test_verify_gus_acepta_ay(case):
    """F2: verify_gus no rechaza AY en la capa calendario; el único error
    restante admitido es la firma ausente (no forma parte de F2)."""
    doc = {"ts": case["canonical"], "ins": case["day_index"] * 86400, "day": case["day_index"]}
    res = verify_document(doc)
    calendar_errors = [e for e in res["errors"] if e.startswith("GERO_ETEMPALUM") or e.startswith("GERO_EWEEK")]
    assert calendar_errors == [], res
    assert res["errors"], "sin firma el documento no puede validar (`ok` debe seguir false)"
