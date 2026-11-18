#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Fuzzing diferencial GUS: Python (referencia) <-> JavaScript <-> C.

Genera entradas aleatorias con semilla fija, las alimenta por el protocolo de
líneas a los tres núcleos y exige igualdad exacta de los resultados de
cualquier par. Cualquier divergencia es un fallo (véase vectors/README.md).

Uso:
    python3 tools/fuzz_diff.py [--n N] [--js] [--c] [--python-only]
                                [--js-path bin] [--c-path bin]

Por defecto compara las tres (node y impl-c/gus-cli compilados).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import string
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gerarion import calendar as cal  # noqa: E402
from gerarion import format as fmt  # noqa: E402

REPO = os.path.join(os.path.dirname(__file__), "..")
SEED = 20310101


def py_err(exc: Exception) -> str:
    name = type(exc).__name__
    return {"GeroError": "GERO_EWEEK", "GeroEinval": "GERO_EINVAL",
            "GeroItemporal": "GERO_ETEMPALUM"}.get(name, name)


# ---------------------------------------------------------------------------
# Generación de casos
# ---------------------------------------------------------------------------

def gen_cases(n: int, seed: int) -> list:
    rng = random.Random(seed)
    cases = []

    def add(op, payload):
        cases.append((op, payload))

    for _ in range(n):
        kind = rng.randrange(5)
        if kind == 0:
            add("tg", str(rng.randint(-3_000_000, 8_000_000)))
        elif kind == 1:
            y = rng.randint(-200, 2100)
            m = rng.choice(list(range(-1, 14)))
            d = rng.choice(list(range(-3, 41)))
            add("fg", f"{y} {m} {d}")
        elif kind == 2:
            add("gr", str(rng.randint(-3_000_000, 8_000_000)))
        elif kind == 3:
            add("pt", gen_stamp(rng))
        else:
            di = rng.randint(-3_000_000, 8_000_000)
            h, m, s = rng.randrange(-1, 25), rng.randrange(-1, 61), rng.randrange(-1, 61)
            add("in", f"{di} {h} {m} {s}")
    return cases


def gen_stamp(rng: random.Random) -> str:
    y = rng.choice([str(rng.randint(0, 9999)), str(rng.randint(0, 9999)), str(rng.randint(0, 45))])
    era = rng.choice(["DY", "DY", "AY", ""])
    sep = rng.choice(["-", "-", "-", "."])
    sp = rng.choice(["-", "-", " "])  # espacio simple max (los dobles divergen por diseño de hosts)
    w = rng.choice(list("SLMATVB") + list("slmatvb") + list("SLMATVB"))
    m = rng.choice([1, 3, 0, 12, 13, 5, 7, 9])
    d = rng.choice([1, 8, 30, 31, 7, 11, 4, 25])
    base = f"{y}{era}{sep}{m}{sep}{d}{sp}{w}"
    if rng.random() < 0.5:
        h, mi, s = rng.randrange(0, 25), rng.randrange(0, 60), rng.randrange(0, 60)
        cyc = rng.choice(["SC", "LC"])
        off = rng.choice(["+0", "+3", "-7", "+23", "-23"])
        tail = rng.random() < 0.8
        base += f"{sp}{h:02d}:{mi:02d}:{s:02d}{sp}{cyc}{sp}TCJ{off}" if tail else ""
    return base


# ---------------------------------------------------------------------------
# Ejecutores
# ---------------------------------------------------------------------------

def run_python(cases: list) -> list:
    out = []
    for op, payload in cases:
        try:
            if op == "tg":
                di = int(payload)
                g = cal.to_gerarion(di)
                out.append({"ok": True, "di": di,
                            "year": abs(g.year), "era": "DY" if g.year >= 0 else "AY",
                            "month": g.month, "day": g.day, "abbr": g.weekday[1],
                            "canon": g.canonical()})
            elif op == "fg":
                y, m, d = (int(t) for t in payload.split(" "))
                g = cal.from_gerarion(y, m, d)
                out.append({"ok": True, "day_index": g.day_index, "canon": g.canonical()})
            elif op == "gr":
                di = int(payload)
                gy, gm, gd = cal.gregorian_from_day_index(di)
                out.append({"ok": True, "di": di, "greg": f"{gy}-{gm}-{gd}",
                            "greg_year": gy, "greg_month": gm, "greg_day": gd})
            elif op == "pt":
                p = fmt.parse(payload)
                out.append({"ok": True, "canon": fmt.to_canonical(p),
                            "flags": sorted(p.flags)})
            elif op == "in":
                di, h, m, s = (int(t) for t in payload.split(" "))
                inst = cal.instant_from_parts(di, h, m, s)
                out.append({"ok": True, "instant": str(inst)})
        except Exception as exc:  # noqa: BLE001
            out.append({"ok": False, "error": py_err(exc), "ex": type(exc).__name__})
    return out


def run_child(cmd: list, cases: list, name: str, allow_missing: bool) -> list:
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True)
    except FileNotFoundError:
        if allow_missing:
            print(f"  SKIP {name}: ejecutable no encontrado ({cmd[0]})")
            return []
        print(f"FALTA {name}: se requiere {cmd[0]} (compila impl-c o instala node)")
        sys.exit(2)
    lines = [f"{op} {payload}" if payload else op for op, payload in cases]
    try:
        stdout, _ = proc.communicate("\n".join(lines) + "\n", timeout=180)
    except subprocess.TimeoutExpired:
        proc.kill()
        print(f"TIEMPO AGOTADO en {name}")
        sys.exit(2)
    out = []
    for line in stdout.splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    if len(out) != len(cases):
        print(f"{name}: respuestas {len(out)} != casos {len(cases)}")
        sys.exit(2)
    return out


def normalize(res: list) -> list:
    """Elimina campos solo-side (ex) para comparar pares de ejecutores."""
    fixed = []
    for r in res:
        r = dict(r)
        r.pop("ex", None)
        fixed.append(r)
    return fixed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--python-only", action="store_true")
    ap.add_argument("--allow-missing", action="store_true")
    ap.add_argument("--c-path", default=os.path.join(REPO, "impl-c", "gus-cli"))
    ap.add_argument("--js-path", default="node")
    args = ap.parse_args()

    cases = gen_cases(args.n, args.seed)
    py_res = normalize(run_python(cases))
    results = {"python": py_res}

    js_cmd = [args.js_path, os.path.join(REPO, "web", "conformance.mjs"), "--cli"]
    c_res: list = []
    if not args.python_only:
        js_res = normalize(run_child(js_cmd, cases, "JS (node)", args.allow_missing))
        if js_res:
            results["js"] = js_res
        c_res = normalize(run_child([args.c_path], cases, "C (impl-c)", args.allow_missing))
        if c_res:
            results["c"] = c_res

    total_fail = 0
    pairs = [(a, b, name_a, name_b)
             for i, (name_a, a) in enumerate(results.items())
             for (name_b, b) in list(results.items())[i + 1:]]
    for name_a, name_b in [(x[2], x[3]) for x in pairs]:
        a = results[name_a]
        b = results[name_b]
        mismatches = []
        for idx, (ra, rb) in enumerate(zip(a, b)):
            if ra != rb:
                mismatches.append((idx, cases[idx], ra, rb))
        label = f"{name_a} <-> {name_b}"
        if mismatches:
            total_fail += len(mismatches)
            print(f"DIVERGENCIA {label}: {len(mismatches)} casos")
            for idx, (op, payload), ra, rb in mismatches[:10]:
                print(f"  caso #{idx} [{op} {payload}]\n    {name_a}: {ra}\n    {name_b}: {rb}")
        else:
            print(f"OK {label}: {len(a)} casos idénticos")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
