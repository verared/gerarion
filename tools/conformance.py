#!/usr/bin/env python3
"""Runner de conformancia GUS contra vectors/gus-normative-001.json.

Verifica que la implementación de referencia en src/gerarion sigue pasando
los vectores normativos, categoría por categoría. Es la implementación de la
cláusula de conformancia de vectors/README.md:

    una implementación es conforme si y solo si pasa el 100 % de las
    categorías que declara soportar.

Las categorías core se validan siempre. Las categorías `slh_dsa` requieren
el paquete PyPI `slh-dsa` (se saltan con aviso si no está instalado).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Callable, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gerarion import adapters as adp  # noqa: E402
from gerarion import calendar as cal  # noqa: E402
from gerarion import format as fmt  # noqa: E402
from gerarion import hashots  # noqa: E402
from gerarion import notary as nty  # noqa: E402
from gerarion import notary_cluster as ncl  # noqa: E402

DEFAULT_VECTORS = os.path.join(
    os.path.dirname(__file__), "..", "vectors", "gus-normative-001.json"
)

CORE = ("constants", "gran_tempalum", "calendar", "year_starts",
        "gregorian_roundtrip", "format", "instant")
FULL = CORE + ("hashots", "slh_dsa", "notary")


def load_vectors(path: Optional[str] = None) -> dict:
    with open(path or DEFAULT_VECTORS, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Categorías core
# ---------------------------------------------------------------------------

def check_constants(v: dict) -> None:
    c = v["constants"]
    assert cal.ORIGIN_JDN == c["ORIGIN_JDN"]
    assert cal.SOLAR_DELTA_UD == c["SOLAR_DELTA_UD"]
    assert cal.SOLAR_THRESHOLD_UD == c["SOLAR_THRESHOLD_UD"]
    assert cal.SECS_PER_DAY == c["SECS_PER_DAY"]
    assert cal.YEAR_COMMON_DAYS == c["YEAR_COMMON_DAYS"]
    assert cal.YEAR_GRAN_DAYS == c["YEAR_GRAN_DAYS"]
    assert cal.MONTH_BLOCK_DAYS == c["MONTH_BLOCK_DAYS"]
    assert [w[1] for w in cal.WEEKDAYS] == c["WEEKDAY_LETTERS"]
    assert fmt.CANONICAL_CTX == c["context"]


def check_gran_tempalum(v: dict) -> None:
    g = v["gran_tempalum"]
    pattern = [y for y in range(46) if cal.is_gran_tempalum(y)]
    assert pattern == g["pattern_years_0_45"]
    for ys, is_gt in g["years_sample"].items():
        assert cal.is_gran_tempalum(int(ys)) == is_gt


def check_calendar(v: dict) -> None:
    for row in v["calendar"]:
        di = cal.day_index_from_gregorian(row["greg_year"], row["greg_month"], row["greg_day"])
        assert di == row["day_index"], row
        g = cal.to_gerarion(di)
        assert g.year == (row["year"] if row["era"] == "DY" else -row["year"])
        assert g.month == row["month"] and g.day == row["day"]
        assert g.weekday[1] == row["abbr"] and g.weekday[0] == row["weekday"]
        assert g.weekday_index == row["weekday_index"]
        assert g.tempalum_name == row["tempalum_name"]
        assert g.sacred_day == row["sacred_day"]


def check_year_starts(v: dict) -> None:
    for row in v["year_starts"]:
        y = row["year"] if row["era"] == "DY" else -row["year"]
        di = cal.year_start_day_index(y)
        assert di == row["day_index"], row
        assert cal.to_gerarion(di).weekday[1] == "S"
        assert cal.is_gran_tempalum(y) == row["gran_tempalum"] or y < 0
        assert cal.tempalum_days(y) == row["tempalum_days"]


def check_gregorian_roundtrip(v: dict) -> None:
    for row in v["gregorian_roundtrip"]:
        gy, gm, gd = row["greg_year"], row["greg_month"], row["greg_day"]
        assert cal.gregorian_from_day_index(row["day_index"]) == (gy, gm, gd)
        assert cal.day_index_from_gregorian(gy, gm, gd) == row["day_index"]


def check_format(v: dict) -> None:
    for case in v["format"]["canonical"]:
        parsed = fmt.parse(case["input"])
        assert fmt.to_canonical(parsed) == case["canonical"], case
        assert sorted(parsed.flags) == sorted(case["flags"]), case
        f = case["fields"]
        assert abs(parsed.year) == f["year"]
        assert ("DY" if parsed.year >= 0 else "AY") == f["era"]
        for key in ("month", "day", "hour", "minute", "second", "cycle", "offset"):
            assert getattr(parsed, key) == f[key], (case, key)
    for case in v["format"]["errors"]:
        raised = None
        try:
            fmt.parse(case["input"])
        except cal.GeroError as exc:
            raised = type(exc).__name__
        assert raised is not None, case
        assert case["error"] == {
            "GeroEinval": "GERO_EINVAL",
            "GeroItemporal": "GERO_ETEMPALUM",
            "GeroError": "GERO_EWEEK",
        }[raised], case
    for case in v["format"]["strict_weekday"]:
        try:
            fmt.parse(case["input"], strict_weekday=True)
        except cal.GeroError:
            pass
        else:
            raise AssertionError(case)


def check_instant(v: dict) -> None:
    for row in v["instant"]:
        parsed = fmt.parse(row["ts"])
        gdate = cal.from_gerarion(parsed.year, parsed.month, parsed.day)
        instant = cal.instant_from_parts(gdate.day_index, parsed.hour, parsed.minute, parsed.second)
        assert instant == row["instant"], row
        assert gdate.day_index == row["day"], row


# ---------------------------------------------------------------------------
# Categorías full
# ---------------------------------------------------------------------------

def check_hashots(v: dict) -> None:
    for row in v["hashots"]["vectors"]:
        message = bytes.fromhex(row["message_hex"])
        assert hashlib.sha256(message).hexdigest() == row["message_sha256"]
        sig = {"leaf": row["leaf"], "sig": row["sig_hex"], "path": row["path_hex"]}
        ok = hashots.WotsMerkleSigner.verify(
            bytes.fromhex(row["pub_hex"]), hashots.digest_message(message), sig
        )
        expected = not row.get("tampered", False)
        assert ok == expected, row


def check_slh_dsa(v: dict) -> str:
    try:
        import slhdsa  # noqa: F401
    except ImportError:
        return "skip"
    for row in v["slh_dsa"]["vectors"]:
        message = bytes.fromhex(row["message_hex"])
        ok = adp.SlhDsaSigner.verify(row["pub_hex"], message, row["sig_hex"], row["alg"])
        expected = not row.get("tampered", False)
        assert ok == expected, row
    return "ok"


def check_notary(v: dict) -> None:
    notary = nty.DayNotary()
    for entry in v["notary"]["day_seals"]:
        payloads = [bytes.fromhex(p) for p in entry["payloads_hex"]]
        for payload in payloads:
            notary.append(payload)
        rec = notary.seal_day(entry["day"])
        assert rec["tree_root"] == entry["tree_root"], entry["day"]
        assert rec["prev_root"] == entry["prev_root"]
        assert rec["day_root"] == entry["day_root"]
        assert rec["leaves"] == entry["leaves_hex"]
        if "proof_leaf0" in entry:
            proof = notary.inclusion_proof(entry["day"], 0)
            expected = entry["proof_leaf0"]
            assert proof["proof"] == expected["proof_hex"]
            assert proof["root"] == expected["root"]
            assert nty.verify_inclusion(
                hashlib.sha256(b"\x00" + (payloads[0] if payloads else b"")).digest(),
                expected["proof_hex"], 0, bytes.fromhex(expected["root"]),
            )
    bundle = v["notary"]["bundle"]
    result = ncl.verify_bundle(bundle["publications"], bundle["threshold"])
    expected = bundle["expected"]
    assert result == expected, result


# ---------------------------------------------------------------------------
# Orquestación
# ---------------------------------------------------------------------------

CHECKS: dict = {
    "constants": check_constants,
    "gran_tempalum": check_gran_tempalum,
    "calendar": check_calendar,
    "year_starts": check_year_starts,
    "gregorian_roundtrip": check_gregorian_roundtrip,
    "format": check_format,
    "instant": check_instant,
    "hashots": check_hashots,
    "slh_dsa": check_slh_dsa,
    "notary": check_notary,
}


def run_all(path: Optional[str] = None, verbose: bool = True) -> dict:
    data = load_vectors(path)
    results = {"ok": 0, "fail": 0, "skip": 0, "failures": [], "skips": []}
    for name in FULL:
        fn: Callable = CHECKS[name]
        try:
            outcome = fn(data)
            status = "skip" if outcome == "skip" else "ok"
        except AssertionError as exc:
            results["fail"] += 1
            results["failures"].append((name, str(exc)[:200]))
            status = "fail"
        if status == "ok":
            results["ok"] += 1
            if verbose:
                print(f"  OK   {name}")
        elif status == "skip":
            results["skip"] += 1
            results["skips"].append(name)
            if verbose:
                print(f"  SKIP {name} (dependencia no instalada)")
        else:
            if verbose:
                print(f"  FALLA {name}: {results['failures'][-1][1]}")
    return results


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    print(f"gus-normative conformance: {path or DEFAULT_VECTORS}")
    results = run_all(path)
    total = results["ok"] + results["fail"]
    print(f"conformancia: {results['ok']}/{total} categorias OK"
          + (f", {results['skip']} saltadas" if results["skip"] else ""))
    return 0 if results["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
