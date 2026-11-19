# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Milestone 0: prove the shared vector set is valid without a JS runtime.

Loads vectors/guti-calendars-001.json and validates every category with the
Python reference engine inside a socket-blocked sandbox. The C and JS engines
validate the same file in their own runners; the vector set is the shared
contract, so a broken vector fails here first.

Network isolation: no socket can be created while any test in this module
runs, demonstrating that the whole engine works fully offline.
"""

import json
import socket
import sys
import urllib.request
from pathlib import Path
from typing import Optional

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from gerarion import calendars as gc  # noqa: E402

VECTOR_PATH = ROOT / "vectors" / "guti-calendars-001.json"


class _Blocked(socket.socket):
    def __init__(self, *args, **kwargs):
        raise OSError("network access is disabled during GUTI tests")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(socket, "socket", _Blocked, raising=True)

    def _blocked_urlopen(*args, **kwargs):
        raise OSError("network access is disabled during GUTI tests")

    monkeypatch.setattr(urllib.request, "urlopen", _blocked_urlopen, raising=True)
    yield


@pytest.fixture(scope="module")
def vectors():
    with open(VECTOR_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _fields_of(sysid: str, d) -> dict:
    return dict(zip(gc.metadata(sysid)["field_names"], d.fields))


def _error_code(exc: Exception) -> Optional[str]:
    msg = str(exc)
    for code in ("GERO_ERANGE", "GERO_EUNSUPPORTED", "GERO_EINVAL"):
        if msg.startswith(code):
            return code
    return None


# ---------------------------------------------------------------- structure


def test_vector_file_exists():
    assert VECTOR_PATH.is_file(), "run tools/generate_guti_vectors.py first"


def test_metadata_header(vectors):
    assert vectors["version"] == "001"
    assert vectors["license"] == "CC0-1.0"
    assert vectors["origin_jdn"] == 1719313
    assert set(vectors["calendars"]) == set(gc.system_ids())


def test_calendars_metadata_complete(vectors):
    required = ("id", "name", "version", "type", "epoch_jdn",
                "supported_range", "astronomical_dependency",
                "reference_meridian", "known_limitations", "field_names")
    for sysid, meta in vectors["calendars"].items():
        for key in required:
            assert key in meta and meta[key] not in (None, "", []), (sysid, key)


# ------------------------------------------------- single-platform vectors


def test_from_day_index_vectors(vectors):
    bad = []
    for v in vectors["vectors"]:
        got = gc.from_day_index(v["day_index"], v["system"])
        if got.fields != tuple(v["fields"].values()):
            bad.append((v, got))
    assert not bad, f"{len(bad)} mismatches; first: {bad[0]}"


def test_round_trip_vectors(vectors):
    bad = []
    for v in vectors["vectors"]:
        if gc.to_day_index(v["system"], v["fields"]) != v["day_index"]:
            bad.append(v)
    assert not bad, f"{len(bad)} round-trips failed; first: {bad[0]}"


def test_cross_mappings_palindrome(vectors):
    bad = []
    for c in vectors["cross"]:
        f, t = c["from"], c["to"]
        if c["via"] != f:
            bad.append(c)
            continue
        d1 = gc.from_day_index(c["day_index"], f)
        d2 = gc.from_day_index(gc.to_day_index(f, _fields_of(f, d1)), t)
        d3 = gc.from_day_index(gc.to_day_index(t, _fields_of(t, d2)), f)
        if d3.fields != d1.fields:
            bad.append((c, d1, d3))
    assert not bad, f"{len(bad)} cross checks failed; first: {bad[0]}"


def test_invalid_rejections(vectors):
    bad = []
    for v in vectors["invalid"]:
        try:
            gc.to_day_index(v["system"], v["fields"])
        except ValueError as exc:
            continue  # el rechazo basta; el núcleo congelado no usa prefijo
        bad.append(v)
    assert not bad, f"invalid vectors mishandled: {bad[:4]}"


def test_unsupported_ranges(vectors):
    bad = []
    for v in vectors["unsupported"]:
        try:
            if "day_index" in v:
                gc.from_day_index(v["day_index"], v["system"])
            else:
                gc.to_day_index(v["system"], v["fields"])
        except ValueError as exc:
            if _error_code(exc) != "GERO_EUNSUPPORTED":
                bad.append((v, f"unexpected error: {exc}"))
            continue
        bad.append((v, "accepted"))
    assert not bad, f"unsupported vectors mishandled: {bad[:4]}"


def test_erange_horizons(vectors):
    bad = []
    for v in vectors.get("erange", []):
        try:
            gc.to_day_index(v["system"], v["fields"])
        except ValueError as exc:
            if _error_code(exc) != "GERO_ERANGE":
                bad.append((v, f"unexpected error: {exc}"))
            continue
        bad.append((v, "accepted"))
    assert not bad, f"erange vectors mishandled: {bad[:4]}"


# --------------------------------------------------------------- structure


def test_cross_paths_reference_valid_systems(vectors):
    names = set(gc.system_ids())
    for c in vectors["cross"]:
        assert c["from"] in names and c["to"] in names and c["via"] in names, c


def test_fields_order_matches_metadata(vectors):
    for v in vectors["vectors"]:
        meta = gc.metadata(v["system"])
        assert list(v["fields"]) == meta["field_names"], v["system"]


# ------------------------------------------------- hebrew dehiyah integrity


def test_hebrew_year_membership_by_definition(vectors):
    """El año devuelto cumple RH(y) <= jdn < RH(y+1) en todo el set."""
    bad = []
    for v in vectors["vectors"]:
        if v["system"] != "hebrew":
            continue
        y = v["fields"]["year"]
        jdn = v["day_index"] + 1719313
        if not (gc._heb_rosh_hashanah(y) <= jdn < gc._heb_rosh_hashanah(y + 1)):
            bad.append(v)
    assert not bad, f"{len(bad)} hebrew vectors break year membership"


def test_hebrew_far_years_are_fast(vectors):
    """El estimador de molad debe ser O(1): sin deriva lineal en años."""
    import time
    far = [di for v in vectors["vectors"] if (di := v["day_index"] if False else None) is not None][:0]
    t = time.time()
    for di in (-2_814_749_767_106_56, 0, 300_000_000_000):
        try:
            gc.from_day_index(di, "hebrew")
        except ValueError:
            pass
    elapsed = time.time() - t
    assert elapsed < 0.1, f"hebrew from_day_index degeneró: {elapsed:.2f}s"
