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
# Modo de estrés: corpus a escala + límites int64 (batch por ficheros)
# ---------------------------------------------------------------------------

INT64_MAX = 9223372036854775807
INT64_MIN = -9223372036854775808
# Debe espejar impl-c/gus.h (GUS_MAX_*): límites blindados con GERO_ERANGE.
C_MAX_INSTANT_DAYS = INT64_MAX // 86400                # 106751991167300
C_MAX_GREG_DAYS = INT64_MAX // 4 - 68569 - 1719313     # gus_max_grég jdn-safe
JS_MAX_SAFE = 9007199254740991                          # 2^53-1

GT_TRANSITION_YEARS = [-29, -23, -17, -12, -6, -1, 0, 5, 11, 2034]
OFFSET_STAMPS = ["+0", "-2:20", "+5:45", "-12:00", "+14:00"]
NANOS_STAMPS = ["0", "1", "999999999"]
MUTATE_ALPHABET = ("0123456789-S.LMATVBslmatvb:TCJ+ "
                   "\u00e9\u00ff\u00f1\u2022")
TRASH_POOL = ["", "  ", "basura@@@", "99999999DY-01-01-S pendiente", "TCJ+9",
              "0000DY-00-00-S", "\u00e9\u00e9-\u00e9", "2031DY-13-08-T",
              "2031DY-03-32-T", "x" * 120, "2031DY-03-08-T-99:99:99-SC-TCJ+0",
              "2031DY-03-08-T-093000-XX-TCJ+3", "-5AY-.5-.5-S"]


def gen_stress_cases(n: int, seed: int) -> list:
    """Corpus de estrés: bloque determinista obligatorio + distribución.

    Ops y política de comparación (véase run_stress):
      tg/fg/gr/pt/in   -> igualdad bit a bit Python <-> JS <-> C
      tgs/fgs/grs      -> igualdad Python <-> C (JS se salta: |valor| > 2^53)
      tgq/fgq/grq/inq  -> C debe responder GERO_ERANGE exactamente;
                          Python responde ok:true exacto (int arbitrario);
                          JS calcula con imprecisión Number y NO se compara.
      inb              -> igualdad de las tres con di parseado BigInt en JS.
    """
    rng = random.Random(seed)
    cases: list = []

    def add(op, payload):
        cases.append((op, str(payload)) if op != "pt" else (op, str(payload)))

    # ---- bloque determinista obligatorio -------------------------------
    for y in GT_TRANSITION_YEARS + [-45, -8, 12000, 999999, -999999]:
        era_y = y if y < 0 else y  # AY se expresa como año negativo en fg
        add("pt", f"{abs(y)}{'AY' if y < 0 else 'DY'}-01-01-S")
        add("pt", f"{abs(y)}{'AY' if y < 0 else 'DY'}-12-30-B")
        add("fg", f"{era_y} {rng.choice([0, 1, 12])} {rng.choice([1, 4])}")
        add("tg", ysi_py(era_y))
        add("tg", ysi_py(era_y) + rng.randint(-371, 371))
    # Tempalum completo en GT y no-GT (días 1..11 y 1..4)
    add("fg", "0 0 1"); add("fg", "0 0 11"); add("fg", "0 0 12")
    add("fg", "1 0 1"); add("fg", "-1 0 4"); add("fg", "-1 0 11")
    add("fg", "2034 0 11"); add("fg", "2034 0 12")
    # Offsets con horas y minutos + fracciones nanos + compacto
    for off in OFFSET_STAMPS:
        add("pt", f"2031DY-03-08-T-09:30:00-SC-TCJ{off}")
        add("pt", f"2031DY-03-08-T-093000-SL-TCJ{off.replace(':', '')}")
        add("in", f"2459045 {rng.randrange(24)} 59 59")
    for frac in NANOS_STAMPS:
        add("pt", f"2031DY-03-08-T-09:30:00.{frac}-SC-TCJ+0")
    add("pt", "999999DY-06-15-A")
    add("pt", "12000AY-00-11-B")
    add("pt", "0000AY-01-01-S")
    # Límites int64: extremos de instante con k acotado (12:00:00, k=43.200
    # < 55.807) para que el instante quede dentro del int64 en las tres
    # implementaciones.
    for di in (C_MAX_INSTANT_DAYS, -C_MAX_INSTANT_DAYS,
               C_MAX_INSTANT_DAYS - 1, -C_MAX_INSTANT_DAYS + 1):
        add("in", f"{di} 12 0 0")
    # 2^53 (Number.MAX_SAFE_INTEGER): frontera de CALENDARIO exacto en JS
    for di in (JS_MAX_SAFE, JS_MAX_SAFE - 1):
        add("tg", di)
    add("tgs", JS_MAX_SAFE + 1)
    add("tgs", JS_MAX_SAFE + 12345)
    add("tgs", 9_000_000_000_000_000_000)          # profundo: py<->c
    add("fgs", "9000000000000 12 30")              # 9e12 años: js impreciso
    add("fgs", "-9000000000000 1 1")
    add("grs", 9_000_000_000_000_000)
    add("grs", 2_000_000_000_000_000_000)          # bajos del límite C greg
    # FUERA de los límites C: GERO_ERANGE limpio (sin UB) — espejo gus.h
    add("tgq", 9_200_000_000_000_000_000)
    add("tgq", -9_200_000_000_000_000_000)
    add("tgq", INT64_MAX)
    add("tgq", INT64_MIN)
    add("fgq", "25_300_000_000_000_000".replace("_", "") + " 1 1")
    add("fgq", "-25_300_000_000_000_000".replace("_", "") + " 1 1")
    add("fgq", "99999999999999999999 1 1")
    add("grq", 2_400_000_000_000_000_000)
    add("grq", -2_400_000_000_000_000_000)
    add("inq", f"{C_MAX_INSTANT_DAYS + 1} 0 0 0")
    add("inq", f"-{C_MAX_INSTANT_DAYS + 1} 0 0 0")
    # Basura malformada (idéntico rechazo en los tres)
    for t in TRASH_POOL:
        add("pt", t[:120])

    # ---- distribución aleatoria ----------------------------------------
    while len(cases) < n:
        kind = rng.randrange(8)
        if kind == 0:
            add("tg", rng.randint(-3_000_000, 8_000_000))
        elif kind == 1:
            y = rng.choice([rng.randint(-200, 2100), rng.randint(-45, 45),
                            rng.randint(-10**6, 10**6)])
            add("fg", f"{y} {rng.choice(list(range(-1, 14)))} "
                      f"{rng.choice(list(range(-3, 41)))}")
        elif kind == 2:
            add("gr", rng.randint(-3_000_000, 8_000_000))
        elif kind == 3:
            add("pt", gen_stamp(rng))
        elif kind == 4:
            add("in", f"{rng.randint(-3_000_000, 8_000_000)} "
                      f"{rng.randrange(-1, 25)} {rng.randrange(-1, 61)} "
                      f"{rng.randrange(-1, 61)}")
        elif kind == 5:
            # in en la franja del límite de instante de C (margen para k)
            add("in", f"{rng.randint(-C_MAX_INSTANT_DAYS + 3, C_MAX_INSTANT_DAYS - 3)} "
                      f"{rng.randrange(0, 24)} {rng.randrange(0, 60)} "
                      f"{rng.randrange(0, 60)}")
        elif kind == 6:
            # mutación de un byte de una marca válida
            s = list(gen_stamp(rng))
            if len(s) > 1 and len(" ".join(s)) < 500:
                i = rng.randrange(len(s))
                s[i] = rng.choice(MUTATE_ALPHABET)
                add("pt", "".join(s)[:120])
        else:
            add("pt", rng.choice(TRASH_POOL))
    rng.shuffle(cases)
    return cases[:n]


# ---------------------------------------------------------------------------
# Ejecutores
# ---------------------------------------------------------------------------


def ysi_py(year: int) -> int:
    """Day index del 1-1 del año (espejo de gus_year_start_day_index)."""
    U, S, C = 7_000_000, 1_242_190, 364
    q = year // U  # piso
    r = year - q * U
    return year * C + 7 * (q * S + r * S // U)

def handle_case(op: str, payload: str) -> dict:
    """Ejecuta un caso en la referencia Python; devuelve el dict respuesta.

    Los ops del modo de estrés (tgs/fgs/grs/tgq/fgq/grq/inq) comparten la
    semántica de su op base; la política de COMPARACIÓN entre lenguajes la
    decide el comparador (run_stress), no el núcleo.
    """
    base = {"tgs": "tg", "fgs": "fg", "grs": "gr", "tgq": "tg",
            "fgq": "fg", "grq": "gr", "inq": "in"}.get(op, op)
    if base == "tg":
        di = int(payload)
        g = cal.to_gerarion(di)
        return {"ok": True, "di": di,
                "year": abs(g.year), "era": "DY" if g.year >= 0 else "AY",
                "month": g.month, "day": g.day, "abbr": g.weekday[1],
                "canon": g.canonical()}
    if base == "fg":
        y, m, d = (int(t) for t in payload.split(" "))
        g = cal.from_gerarion(y, m, d)
        return {"ok": True, "day_index": g.day_index, "canon": g.canonical()}
    if base == "gr":
        di = int(payload)
        gy, gm, gd = cal.gregorian_from_day_index(di)
        return {"ok": True, "di": di, "greg": f"{gy}-{gm}-{gd}",
                "greg_year": gy, "greg_month": gm, "greg_day": gd}
    if base == "pt":
        p = fmt.parse(payload)
        return {"ok": True, "canon": fmt.to_canonical(p),
                "flags": sorted(p.flags)}
    # in / inb / inq
    di, h, m, s = (int(t) for t in payload.split(" "))
    inst = cal.instant_from_parts(di, h, m, s)
    return {"ok": True, "instant": str(inst)}


def run_python(cases: list) -> list:
    out = []
    for op, payload in cases:
        try:
            r = handle_case(op, payload)
            r = dict(r)
            r.pop("ex", None)
            out.append(r)
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


Q_OPS = {"tgq", "fgq", "grq", "inq"}
PY_C_OPS = {"tgs", "fgs", "grs"}
ALL_OPS = {"tg", "fg", "gr", "pt", "in", "inb"}


def run_stress(cases: list, c_path: str, js_path: str, allow_missing: bool) -> int:
    """Corpus masivo por ficheros: comparación en flujo, memoria O(1).

    Políticas por op (documentadas en gen_stress_cases):
      ALL_OPS  -> igualdad exacta entre python, js y c.
      PY_C_OPS -> igualdad exacta python <-> c (JS se salta por Number).
      Q_OPS    -> c == GERO_ERANGE exacto y python ok:true; js libre.
    """
    import hashlib
    import tempfile

    tmp = tempfile.mkdtemp(prefix="gus-fuzz-")
    cases_path = os.path.join(tmp, "cases.txt")
    py_path = os.path.join(tmp, "python.res")
    js_path_f = os.path.join(tmp, "js.res")
    c_path_f = os.path.join(tmp, "c.res")

    with open(cases_path, "w", encoding="utf-8") as fh:
        for op, payload in cases:
            fh.write(f"{op} {payload}\n" if payload else f"{op}\n")

    # Referencia Python, en flujo (sin materializar la lista completa).
    with open(cases_path, encoding="utf-8") as fin, \
            open(py_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.rstrip("\n")
            if not line:
                continue
            op, _, payload = line.partition(" ")
            try:
                r = handle_case(op, payload)
                r.pop("ex", None)
                fout.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
            except Exception as exc:  # noqa: BLE001
                fout.write(json.dumps({"ok": False, "error": py_err(exc),
                                       "ex": type(exc).__name__}) + "\n")

    js_cmd = [js_path, os.path.join(REPO, "web", "test", "conformance.mjs"), "--cli"]
    runs = [("JS (node)", js_cmd, js_path_f), ("C (impl-c)", [c_path], c_path_f)]
    for name, cmd, outp in runs:
        try:
            with open(cases_path, "rb") as fin, open(outp, "wb") as fout:
                subprocess.run(cmd, stdin=fin, stdout=fout,
                               stderr=subprocess.DEVNULL, timeout=900)
        except FileNotFoundError:
            if allow_missing:
                print(f"  SKIP {name}")
                open(outp, "w").close()
                continue
            raise
        except subprocess.TimeoutExpired:
            print(f"TIEMPO AGOTADO en {name}")
            return 2

    digest = {name: hashlib.sha256() for name in ("python", "js", "c")}
    fails = 0
    shown = 0
    with open(py_path, encoding="utf-8") as fpy, \
            open(js_path_f, encoding="utf-8") as fjs, \
            open(c_path_f, encoding="utf-8") as fc:
        for idx, ((op, payload), lpy, ljs, lc) in enumerate(
                zip(cases, fpy, fjs, fc)):
            rp = json.loads(lpy) if lpy.strip() else {}
            rj = json.loads(ljs) if ljs.strip() else {}
            rc = json.loads(lc) if lc.strip() else {}
            for name, r in (("python", rp), ("js", rj), ("c", rc)):
                r.pop("ex", None)
                digest[name].update(json.dumps(r, sort_keys=True,
                                               ensure_ascii=False).encode())
            ok = True
            if op in Q_OPS:
                ok = rp.get("ok") is True and rc == {"ok": False, "error": "GERO_ERANGE"}
            elif op in PY_C_OPS:
                ok = rp == rc
            else:
                ok = rp == rj == rc
            if not ok:
                fails += 1
                if shown < 10:
                    shown += 1
                    print(f"DIV #{idx} [{op} {payload}]\n  py: {lpy.strip()[:160]}"
                          f"\n  js: {ljs.strip()[:160]}\n  c : {lc.strip()[:160]}")
    n = len(cases)
    print(f"digest python={digest['python'].hexdigest()[:16]} "
          f"js={digest['js'].hexdigest()[:16]} c={digest['c'].hexdigest()[:16]}")
    if fails:
        print(f"DIVERGENCIAS EN ESTRES: {fails} de {n} casos")
        return 1
    print(f"OK estres: {n} casos, 0 divergencias bajo las politicas por op")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1500)
    ap.add_argument("--cases", type=int, default=0,
                    help="modo de estrés: N casos por lotes con límites int64")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--python-only", action="store_true")
    ap.add_argument("--allow-missing", action="store_true")
    ap.add_argument("--c-path", default=os.path.join(REPO, "impl-c", "gus-cli"))
    ap.add_argument("--js-path", default="node")
    args = ap.parse_args()

    if args.cases > 0:
        if args.python_only:
            print("--cases no admite --python-only (compara los tres canales)")
            return 2
        return run_stress(gen_stress_cases(args.cases, args.seed),
                          args.c_path, args.js_path, args.allow_missing)

    cases = gen_cases(args.n, args.seed)
    py_res = normalize(run_python(cases))
    results = {"python": py_res}

    js_cmd = [args.js_path, os.path.join(REPO, "web", "test", "conformance.mjs"), "--cli"]
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
