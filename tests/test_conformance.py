"""Cláusula de conformancia GUS: el paquete pasa los vectores normativos.

vectors/README.md (normativo): una implementación es conforme si y solo si
pasa el 100 % de las categorías que declara soportar. Este test exige el
núcleo completo y todas las categorías full disponibles en el entorno.
"""

from __future__ import annotations

import os


sys_tools = os.path.join(os.path.dirname(__file__), "..", "tools")
import sys  # noqa: E402

sys.path.insert(0, sys_tools)

from conformance import run_all  # noqa: E402


def test_normative_vectors_conformance():
    results = run_all(verbose=False)
    assert results["failures"] == [], results["failures"]
    # El núcleo (7 categorías) es obligatorio sin dependencias externas:
    core_names = {"constants", "gran_tempalum", "calendar", "year_starts",
                  "gregorian_roundtrip", "format", "instant"}
    assert core_names.isdisjoint(results["skips"]), results["skips"]
    assert results["ok"] >= len(core_names)


def test_vectors_file_is_deterministic_and_loadable():
    from conformance import load_vectors

    data = load_vectors()
    assert data["schema"] == "gus-normative-002"
    assert data["deterministic"] is True
    core = set(data["categories_core"])
    full = set(data["categories_full"])
    assert core <= full
    assert len(data["calendar"]) >= 10
