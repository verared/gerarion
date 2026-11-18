<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- SPDX-FileCopyrightText: 2026 verared contributors -->

# Multi-calendar engine (GUTI-1)

Status: part of GUS v3.1.0. This document covers the `CalendarDate` layer
(projected dates); it does not modify the frozen kernel arithmetic
(`gus-normative-003.json`, `ORIGIN_JDN = 1719313`, `TCJ = TAI + 8,400 s`).

## Separation of the three primitives

| Primitive | Content | Role |
|---|---|---|
| `Instant` | integer seconds (int64) + nanos `0..999,999,999` | physical source of truth |
| `CalendarDate` | system fields (1..5) + `leap` | projection of a `day_index` |
| `LocalTime` | civil presentation with offset `TCJ±O` | presentation only |

The single pivot of every conversion is the GUS `day_index`
(`JDN − 1719313`): no A→B conversion is direct; it always goes
`A → day_index → B`. For every system and the whole shared range,
`from_day_index(to_day_index(x))` is the exact identity.

## The ten systems

| id | System | Type | Epoch (JDN) | Astronomical dependency |
|---|---|---|---|---|
| `gus` | Gerarion `DY`/`AY` | arithmetical | 1719313 | none |
| `greg` | Proleptic Gregorian | arithmetical | `day_index(0001-01-01)` | none |
| `julian` | Proleptic Julian | arithmetical | 1721424 | none |
| `egyptian` | Egyptian vague (Nabonassar) | fixed solar | 1448638 | none |
| `ethiopic` | Ethiopic (Amete Mihrêt) | arithmetical | 1724221 | none |
| `bahai` | Badí' tabular (Naw-Rúz Mar 21) | tabular solar | 2394647 | none |
| `maya` | Long Count (GMT 584283) | arithmetical | 584283 | none |
| `islamic` | Islamic civil tabular | tabular lunar | 1948440 | none at run time |
| `hebrew` | Hebrew arithmetical (molad + dehiyot) | lunisolar | 347998 | none at run time |
| `chinese` | Chinese lunisolar (Shixian) | astronomical lunisolar | 2319912 (New Year 1645) | precomputed SHUO/ZHONGQI table |

All systems expose structured metadata in the three implementations
(`id`, `name`, `version`, `type`, `epoch_jdn`, `supported_range`,
`astronomical_dependency`, `reference_meridian`, `known_limitations`,
`field_names`).

### System-level decisions

- **Hebrew**: BaHaRaD molad (2d 5h 204p) with the four dehiyot applied as a
  **strict ELIF cascade** (zaken → Lo ADU → BeTUTaKaPaT → GaTaRaD), months
  numbered **rabinically** (1 = Nisan, 7 = Tishri, 12/13 = Adar I/II). The
  civil order (Tishri first) is an internal detail only.
- **Chinese**: no floating point at run time. The generated table
  (`tools/generate_china_table.py`, truncated Meeus ephemerides, Beijing
  meridian UTC+8/120°E) provides new moons (*shuo*) and solar terms
  (*zhongqi*). The lunar-year anchor is the latest Dongzhi; the intercalary
  month (*runyue*) is the first zhongqi-less lunation between two month-11s
  of a 13-lunation year. Validated range is **strictly 1645–2650 CE**:
  outside it the engine returns `GERO_EUNSUPPORTED`, never extrapolation.
- **Islamic**: 30-year tabular cycle with leap years
  `{2,5,7,10,13,16,18,21,24,26,29}`; Dhu al-Hijjah 30 exists only in tabular
  leap years (e.g. 1445 AH is one, 1446 is not). Local lunar observation may
  differ by one day; the record says so.

## Bounds and domains (parity proven)

Python ↔ C11 ↔ JavaScript bit-for-bit parity is demonstrated against the
CC0 shared set `vectors/guti-calendars-001.json` (63,545 vectors, 450
A→GUS→B→GUS→A palindrome crosses, 30 invalid, 5 unsupported, 2 `erange`),
self-validated by the deterministic generator
(`tools/generate_guti_vectors.py`, seed 584283, no clock).

### Per-platform operational envelope

| Platform | Internal arithmetic | Exact `day_index` domain | Visible effect |
|---|---|---|---|
| C11 (`libgerarion`) | `int64_t` with product guards | \|di\| ≤ ~2.5×10¹⁶ (`GUS_MAX_DAY_INDEX_SAFE`) | `GUS_ERANGE` |
| Python (`gerarion.calendars`) | arbitrary integer | effectively unbounded; Hebrew horizon AM 9×10¹¹ | `GERO_ERANGE` only at system horizons |
| JavaScript (`web/guti.mjs`) | BigInt intermediates, closed into `Number` | \|di\| ≤ 2⁵³−1 (`Number.isSafeInteger`); the shared set uses \|di\| ≤ 2⁴⁸−1, the common domain of all three | `GERO_ERANGE` |

The shared-set common limit (±2⁴⁸−1 days ≈ ±7.7×10¹¹ years) avoids
precision loss inside the web kernel (`jdnToGregorian` multiplies
internally by 4; above ~2⁵¹ the low digits are not representable with
`Number`). Platform edges are tested by the native suites: `int64_t`
bounds in C (`make -C impl-c audit`), `isSafeInteger` rejections in JS.

## Hebrew verification by definition

The molad-based year estimator replaces the linear scan (which accumulated
a ~(years/48)-day drift and was O(years)). The correction is a bounded
loop (≤ 8 iterations); additionally, every returned Hebrew date satisfies
the very definition of year membership:

```
RH(y) ≤ jdn < RH(y+1)      (RH = JDN of Tishri 1, dehiyot applied)
to_day_index(year, month, day) == di        (exact round trip)
```

checked over 6,805 samples up to ±3.3×10¹⁴ days with zero failures.

## How to run

| Suite | Command | Result |
|---|---|---|
| Python (network blocked) | `python3 -m pytest tests/test_guti_m0_sandbox.py` | 13 tests |
| C11 conformance | `make -C impl-c guti-conformance` | 63,850/63,850 |
| JS runner | `node web/guti_vectors.mjs` | 127,204/127,204 |
| Regenerate vectors | `PYTHONPATH=src python3 tools/generate_guti_vectors.py` | deterministic |
