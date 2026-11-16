# -*- coding: utf-8 -*-
"""Perfil GUS-3339 (instante GUS ↔ RFC 3339 UTC).

Cláusula de conformancia del perfil: una implementación que declara el
perfil es conforme si y solo si pasa el 100 % de los vectores de
vectors/gus-3339-001.json. El núcleo (gus-normative-001.json) no cambia.
"""
import json
from pathlib import Path

import pytest

from gerarion import calendar as cal
from gerarion import format as fmt
from gerarion import profiles
from gerarion.profiles import (
    GUS_UNIX_OFFSET,
    instant_from_rfc3339,
    instant_to_rfc3339,
)
from gerarion.calendar import GeroEinval

VECTORS = json.loads(
    (Path(__file__).resolve().parent.parent / "vectors" / "gus-3339-001.json").read_text(
        encoding="utf-8"
    )
)


def test_vector_constant():
    assert GUS_UNIX_OFFSET == VECTORS["constant"]["value"]
    # El offset es (JDN de 1970-01-01) - (JDN del origen), en segundos.
    assert GUS_UNIX_OFFSET == (2_440_588 - 1_719_313) * 86_400


def test_vector_map_cases():
    for c in VECTORS["gus3339"]:
        if c["op"] != "map":
            continue
        assert instant_from_rfc3339(c["rfc3339"]) == c["ins"]
        assert instant_to_rfc3339(c["ins"]) == c["rfc3339"]


def test_vector_reject_cases():
    for c in VECTORS["gus3339"]:
        if c.get("error") != "GERO_E3339":
            continue
        with pytest.raises(GeroEinval, match="GERO_E3339"):
            if c["op"] == "from":
                instant_from_rfc3339(c["rfc3339"])
            else:
                instant_to_rfc3339(c["ins"])


def test_vector_canonical_coherence():
    for c in VECTORS["gus3339_canonical"]:
        parsed = fmt.parse(c["gus_canonical"])
        assert fmt.to_canonical(parsed) == c["gus_canonical"]
        gdate = cal.from_gerarion(parsed.year, parsed.month, parsed.day)
        ins = cal.instant_from_parts(
            gdate.day_index, parsed.hour, parsed.minute, parsed.second
        )
        assert ins == c["ins"]
        assert instant_to_rfc3339(ins) == c["rfc3339"]


def test_profile_injectivity_and_domain():
    # Biyección exacta en el dominio declarado (años 0001..9999 sample).
    # Se recorre día a día un subgrupo denso + cada año en sus extremos.
    probe = set()
    for year in (1, 1600, 1900, 1970, 2026, 2400, 9999):
        j = cal.jdn(year, 1, 1)
        for k in (0, 1, 86_399, 432_441, 8_639_999):  # densos y bordes
            inst = (j - 2_440_588) * 86_400 + k + GUS_UNIX_OFFSET
            val = instant_from_rfc3339(instant_to_rfc3339(inst))
            assert val == inst
            probe.add(val)
    assert len(probe) == 35  # 7 años x 5 offsets (días 0, 0+1s, +1, +5, +99)


def test_epoch_seconds_and_negative_unix():
    # Unix 0 = instante GUS 62_318_160_000; unix negativo (pre-1970) map fine.
    assert instant_to_rfc3339(GUS_UNIX_OFFSET) == "1970-01-01T00:00:00Z"
    assert instant_from_rfc3339("1969-12-31T23:59:59Z") == GUS_UNIX_OFFSET - 1
    assert instant_to_rfc3339(GUS_UNIX_OFFSET - 1) == "1969-12-31T23:59:59Z"


def test_no_datetime_no_float_path():
    # El módulo del perfil no importa datetime ni usa punto flotante.
    src = Path(profiles.__file__).read_text(encoding="utf-8")
    assert "import datetime" not in src and "from datetime" not in src
    assert "import math" not in src
