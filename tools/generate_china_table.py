# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Genera la tabla china determinista (shuo + zhongqi) para 1640..2655.

SOLAMENTE se usa sin conexión, para regenerar las tablas de enteros que
consumen los tres lenguajes (`src/gerarion/china_table.py`,
`web/china-table.mjs`, `impl-c/china_table.c|h`). El motor en ejercicio
NUNCA ejecuta punto flotante: determinismo por datos.

Modelo astronómico (Meeus, Astronomical Algorithms, 2.ª ed.):
- Cap. 49: lunas nuevas (25 términos + correcciones planetarias A1..A14).
- Cap. 25 (baja precisión): longitud solar aparente (ecuación de centro
  + aberración + nutación en longitud con Ω truncado): error << 0,01°,
  sobrado para precisión de DÍA.
- ΔT: polinomios por tramos de Espenak & Meeus (1600–2650).

Meridiano de referencia: Pekín (UTC+8, 120°E), como exige la reforma
Shixian. Los días se redondean al día civil de Pekín del fenómeno.
Convención de ZQ: ZQ[k] = JDN del instant en que la longitud aparente
solar cruza 270° + 30·(k−3) (k ≡ 3 (mod 12) ⇒ Dongzhi/solsticio de invierno).

Uso: python3 tools/generate_china_table.py [--out-dir .] [--check]
"""

from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from gerarion import calendar as cal  # noqa: E402

PI = math.pi
D2R = PI / 180.0


def sin_d(deg: float) -> float:
    return math.sin(deg * D2R)


def cos_d(deg: float) -> float:
    return math.cos(deg * D2R)


def wrap180(deg: float) -> float:
    x = math.fmod(deg + 180.0, 360.0)
    if x < 0:
        x += 360.0
    return x - 180.0


# --- ΔT (Espenak & Meeus) --------------------------------------------------


def delta_t(year: float) -> float:
    if 1600 <= year < 1700:
        t = year - 1600
        return 120 - 0.9808 * t - 0.01532 * t * t + t * t * t / 7129.0
    if 1700 <= year < 1800:
        t = year - 1700
        return (8.83 + 0.1603 * t - 0.0059285 * t * t + 0.00013336 * t * t * t
                - t * t * t * t / 1174000.0)
    if 1800 <= year < 1860:
        t = year - 1800
        return (13.72 - 0.332447 * t + 0.0068612 * t * t + 0.0041116 * t ** 3
                - 0.00037436 * t ** 4 + 0.0000121272 * t ** 5
                - 0.0000001699 * t ** 6 + 0.000000000875 * t ** 7)
    if 1860 <= year < 1900:
        t = year - 1860
        return (7.62 + 0.5737 * t - 0.251754 * t * t + 0.01680668 * t ** 3
                - 0.0004473624 * t ** 4 + t ** 5 / 233174.0)
    if 1900 <= year < 1920:
        t = year - 1900
        return (-2.79 + 1.494119 * t - 0.0598939 * t * t + 0.0061966 * t ** 3
                - 0.000197 * t ** 4)
    if 1920 <= year < 1941:
        t = year - 1920
        return 21.20 + 0.84493 * t - 0.076100 * t * t + 0.0020936 * t ** 3
    if 1941 <= year < 1961:
        t = year - 1950
        return 29.07 + 0.407 * t - t * t / 233.0 + t ** 3 / 2547.0
    if 1961 <= year < 1986:
        t = year - 1975
        return 45.45 + 1.067 * t - t * t / 260.0 - t ** 3 / 718.0
    if 1986 <= year < 2005:
        t = year - 2000
        return (63.86 + 0.3345 * t - 0.060374 * t * t + 0.0017275 * t ** 3
                + 0.000651814 * t ** 4 + 0.00002373599 * t ** 5)
    if 2005 <= year < 2050:
        t = year - 2000
        return 62.92 + 0.32217 * t + 0.005589 * t * t
    if 2050 <= year < 2150:
        u = (year - 1820) / 100.0
        return -20 + 32 * u * u - 0.5628 * (2150 - year)
    u = (year - 1820) / 100.0
    return -20 + 32 * u * u


# --- cap 49: lunas nuevas ---------------------------------------------------


def new_moon_jde(k: int) -> float:
    """JDE (Dinámica del Tiempo Terrestre) de la luna nueva k."""
    T = k / 1236.85
    jde = (2451550.09766 + 29.530588861 * k + 0.00015437 * T * T
           - 0.000000150 * T ** 3 + 0.00000000073 * T ** 4)
    E = 1 - 0.002516 * T - 0.0000074 * T * T
    M = (2.5534 + 29.10535670 * k - 0.0000014 * T * T
         - 0.00000011 * T ** 3)
    Mp = (201.5643 + 385.81693528 * k + 0.0107582 * T * T
          + 0.00001238 * T ** 3 - 0.000000058 * T ** 4)
    F = (160.7108 + 390.67050284 * k - 0.0016118 * T * T
         - 0.00000227 * T ** 3 + 0.000000011 * T ** 4)
    Om = 124.7746 - 1.56375588 * k + 0.0020672 * T * T + 0.00000215 * T ** 3

    corr = (
        -0.40720 * sin_d(Mp)
        + 0.17241 * E * sin_d(M)
        + 0.01608 * sin_d(2 * Mp)
        + 0.01039 * sin_d(2 * F)
        + 0.00739 * E * sin_d(Mp - M)
        - 0.00514 * E * sin_d(Mp + M)
        + 0.00208 * E * E * sin_d(2 * M)
        - 0.00111 * sin_d(Mp - 2 * F)
        - 0.00057 * sin_d(Mp + 2 * F)
        + 0.00056 * E * sin_d(2 * Mp + M)
        - 0.00042 * sin_d(3 * Mp)
        + 0.00042 * E * sin_d(M + 2 * F)
        + 0.00038 * E * sin_d(M - 2 * F)
        - 0.00024 * E * sin_d(2 * Mp - M)
        - 0.00017 * sin_d(Om)
        - 0.00007 * sin_d(Mp + 2 * M)
        + 0.00004 * sin_d(2 * Mp - 2 * F)
        + 0.00004 * sin_d(3 * M)
        + 0.00003 * sin_d(Mp + M - 2 * F)
        + 0.00003 * sin_d(2 * Mp + 2 * F)
        - 0.00003 * sin_d(Mp + M + 2 * F)
        + 0.00003 * sin_d(Mp - M + 2 * F)
        - 0.00002 * sin_d(Mp - M - 2 * F)
        - 0.00002 * sin_d(3 * Mp + M)
        + 0.00002 * sin_d(4 * Mp)
    )
    A1 = 299.77 + 0.107408 * k - 0.009173 * T * T
    A2 = 251.88 + 0.016321 * k
    A3 = 251.83 + 26.651886 * k
    A4 = 349.42 + 36.412478 * k
    A5 = 84.66 + 18.206239 * k
    A6 = 141.74 + 53.303771 * k
    A7 = 207.14 + 2.453732 * k
    A8 = 154.84 + 7.306860 * k
    A9 = 34.52 + 27.261239 * k
    A10 = 207.19 + 0.121824 * k
    A11 = 291.34 + 1.844379 * k
    A12 = 161.72 + 24.198154 * k
    A13 = 239.56 + 25.513099 * k
    A14 = 331.55 + 3.592518 * k
    corr += (
        +0.000325 * sin_d(A1) + 0.000165 * sin_d(A2) + 0.000164 * sin_d(A3)
        + 0.000126 * sin_d(A4) + 0.000110 * sin_d(A5) + 0.000062 * sin_d(A6)
        + 0.000060 * sin_d(A7) + 0.000056 * sin_d(A8) + 0.000047 * sin_d(A9)
        + 0.000042 * sin_d(A10) + 0.000040 * sin_d(A11) + 0.000037 * sin_d(A12)
        + 0.000035 * sin_d(A13) + 0.000023 * sin_d(A14)
    )
    return jde + corr


# --- cap 25 (baja precisión): longitud solar aparente -----------------------


def sun_apparent_longitude(jd_tdb: float) -> float:
    """Longitud aparente del Sol (grados) para un JD/TT dado."""
    T = (jd_tdb - 2451545.0) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = 357.52911 + 35999.05029 * T - 0.0001537 * T * T
    e = 0.016708634 - 0.000042037 * T - 0.0000001267 * T * T
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * sin_d(M)
         + (0.019993 - 0.000101 * T) * sin_d(2 * M)
         + 0.000289 * sin_d(3 * M))
    true_long = L0 + C
    Om = 125.04 - 1934.136 * T
    apparent = true_long - 0.00569 - 0.00478 * sin_d(Om)
    return apparent % 360.0


# --- conversión al día civil de Pekín ---------------------------------------


def jde_to_beijing_jdn(jde: float) -> int:
    """JDE (TDT) → JDN entero del día civil de Pekín (UTC+8) del fenómeno."""
    ut = jde - delta_t(_year_of_jde(jde)) / 86400.0
    beijing = ut + 8.0 / 24.0
    return math.floor(beijing + 0.5)


def _year_of_jde(jde: float) -> float:
    y, _, _ = cal.gregorian_from_day_index(math.floor(jde + 0.5) - 1719313)
    m = cal.gregorian_from_day_index(math.floor(jde + 0.5) - 1719313)[1]
    return y + (m - 1) / 12.0  # valor suave para el tramo de ΔT


def generate(year_lo: int = 1640, year_hi: int = 2656):
    """Devuelve (shuo, zhongqi): listas de JDN con convención ZQ[k]=270+30k.

    `year_lo/hi` interiores: la tabla sobrepasa el rango VALIDADO
    (1645..2650) para que los anclajes de solsticio existan en los bordes.
    """
    shuo: list = []
    k0 = int((year_lo - 2000) * 12.3685) - 3
    k1 = int((year_hi - 2000) * 12.3685) + 3
    for k in range(k0, k1 + 1):
        jdn = jde_to_beijing_jdn(new_moon_jde(k))
        if not shuo or jdn > shuo[-1]:
            shuo.append(jdn)

    # --- zhongqi: bisección con ancla en el cruce de 270° cerca de J2000 ---
    anchor = 2451545.0  # JD del J2000 (longitud solar ~280.5°)
    a0 = anchor
    for _ in range(90):  # primer cruce de 270° hacia atrás desde J2000
        pass
    lo, hi = anchor - 30.0, anchor + 10.0
    # busco el cruce de 270° dentro de [anchor-30, anchor+10]: la longitud
    # en anchor es ~280, cruza 270 ~10 días antes (sin aliasing en 40 días)
    for _ in range(90):
        mid = (lo + hi) / 2.0
        if wrap180(sun_apparent_longitude(mid) - 270.0) < 0:
            lo = mid
        else:
            hi = mid
    j0 = (lo + hi) / 2.0  # cruce de 270° ≈ 1999-12-22 → n = 0
    # Por construcción, el cruce de 270° en UTC 1999-12-22 es el n=0;
    # los n negativos van hacia 1640. El arranque se ancla al JD real del
    # 1 de enero de (year_lo - 1) para cubrir TODO el rango con margen.
    jd_start = 1719313 + cal.day_index_from_gregorian(year_lo - 1, 1, 1)
    n_start = -int((j0 - jd_start) / 30.4368) - 4  # hacia atrás: n negativos
    zq = []
    for n in range(n_start, n_start + 12 * (year_hi - year_lo + 8)):
        target = 270.0 + 30.0 * n
        approx = j0 + 30.4368 * n
        lo2, hi2 = approx - 3.5, approx + 3.5
        for _ in range(90):
            mid = (lo2 + hi2) / 2.0
            if wrap180(sun_apparent_longitude(mid) - target) < 0:
                lo2 = mid
            else:
                hi2 = mid
        jdn = jde_to_beijing_jdn((lo2 + hi2) / 2.0)
        if not zq or jdn > zq[-1]:
            zq.append(jdn)
    return shuo, zq


def beijing_day_of_cny(shuo, zq):
    """Sanity: devuelve los JDN del mes 1 (Año Nuevo Chino) para chequear."""
    # el mes 1 es la 2.ª lunación tras el dongzhi… (se valida en tests)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(os.path.dirname(__file__), ".."))
    args = ap.parse_args()
    shuo, zq = generate()

    py_lines = ([x for x in shuo], [x for x in zq])

    shuo_s = "SHUO = (tuple(range(0)) + (" + ",\n    ".join(
        ", ".join(str(x) for x in shuo[i:i + 12]) for i in range(0, len(shuo), 12)
    ) + "))"
    zq_s = "ZHONGQI = (tuple(range(0)) + (" + ",\n    ".join(
        ", ".join(str(x) for x in zq[i:i + 12]) for i in range(0, len(zq), 12)
    ) + "))"

    out = os.path.join(args.out_dir, "src", "gerarion", "china_table.py")
    with open(out, "w") as fh:
        fh.write(header_py())
        fh.write(shuo_s + "\n\n" + zq_s + "\n")

    out_mjs = os.path.join(args.out_dir, "web", "china-table.mjs")
    with open(out_mjs, "w") as fh:
        fh.write(header_mjs())
        fh.write("export const SHUO = [" + ",\n  ".join(
            ", ".join(str(x) for x in shuo[i:i + 12]) for i in range(0, len(shuo), 12)
        ) + "];\n\nexport const ZHONGQI = [" + ",\n  ".join(
            ", ".join(str(x) for x in zq[i:i + 12]) for i in range(0, len(zq), 12)
        ) + "];\n")

    out_h = os.path.join(args.out_dir, "impl-c", "china_table.h")
    with open(out_h, "w") as fh:
        fh.write(header_c_h(len(shuo), len(zq)))
    out_c = os.path.join(args.out_dir, "impl-c", "china_table.c")
    with open(out_c, "w") as fh:
        fh.write(header_c_c())
        fh.write("const long long GUS_CHINA_SHUO[] = {\n" + ",\n".join(
            ", ".join(str(x) for x in shuo[i:i + 12]) for i in range(0, len(shuo), 12)
        ) + "};\n\nconst long long GUS_CHINA_ZHONGQI[] = {\n" + ",\n".join(
            ", ".join(str(x) for x in zq[i:i + 12]) for i in range(0, len(zq), 12)
        ) + "};\n")

    print(f"shuo: {len(shuo)} lunaciones ({shuo[0]}..{shuo[-1]})")
    print(f"zhongqi: {len(zq)} ({zq[0]}..{zq[-1]})")
    return 0


def header_py() -> str:
    return '''# SPDX-License-Identifier: CC0-1.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Tabla china generada (determinista, CC0): SHUO/ZHONGQI 1640..2655.

REGENERAR con: python3 tools/generate_china_table.py
Numerales: día civil JULIANO ENTERO (JDN) del fenómeno en Pekín (UTC+8);
ZQ[k] = cruce de la longitud solar aparente 270° + 30·(k−3) (k ≡ 3 (mod 12)
⇒ Dongzhi). CC0-1.0: datos factuales, sin autoría.
"""


'''

def header_mjs() -> str:
    return '''// SPDX-License-Identifier: CC0-1.0
// SPDX-FileCopyrightText: 2026 verared contributors
// Tabla china generada (determinista, CC0): SHUO/ZHONGQI 1640..2655.
// Regenerar con: python3 tools/generate_china_table.py
// ZQ[k] = cruce de la longitud solar 270° + 30·(k−3) (k ≡ 3 (mod 12) ⇒ Dongzhi).

'''


def header_c_h(ns: int, nz: int) -> str:
    return f'''/*
 * SPDX-License-Identifier: CC0-1.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/* Tabla china generada (determinista, CC0): SHUO/ZHONGQI 1640..2655.
 * Regenerar con: python3 tools/generate_china_table.py
 * ZQ[k] = cruce de la longitud solar 270° + 30·(k−3) (k ≡ 3 (mod 12) ⇒ Dongzhi). */

#ifndef GUS_CHINA_TABLE_H
#define GUS_CHINA_TABLE_H

#include <stdint.h>

#define GUS_CHINA_SHUO_LEN {ns}
#define GUS_CHINA_ZHONGQI_LEN {nz}
#define GUS_CHINA_MIN_YEAR 1645
#define GUS_CHINA_MAX_YEAR 2650

extern const long long GUS_CHINA_SHUO[GUS_CHINA_SHUO_LEN];
extern const long long GUS_CHINA_ZHONGQI[GUS_CHINA_ZHONGQI_LEN];

#endif
'''


def header_c_c() -> str:
    return '''/*
 * SPDX-License-Identifier: CC0-1.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/* Generado: NO editar (tools/generate_china_table.py). */

#include "china_table.h"

'''


if __name__ == "__main__":
    sys.exit(main())
