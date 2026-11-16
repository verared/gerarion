# GUS Errata — differences between the v1.2 corpus and specification v2.0

Verified by executing the corpus's canonical algorithm (ch. 10.10) against
the normative vectors of ch. 11. Each correction is accompanied by the
definitional change in GUS 2.0 and by its corresponding test.

## E-01 — The vector "new year 2031 falls on March 21st, 2026" is mathematically inconsistent

The corpus simultaneously declares:

- `2026-03-21 → 2031DY-01-01-S` (start of year 2031)
- `2027-03-16 → 2032DY-01-01-S` (start of year 2032)

Between the two there are exactly 360 gregorian days, but every Gerarion
year has 364 or 371 days. Both statements cannot be true at once.

**GUS 2.0 resolution:** the canonical algorithm (solar accumulator + JDN of
origin) is the only normative source. Year 2031 DY begins on
**March 17th, 2026** (Soludyia) — and this gregorian date is a
**derived equivalence**, not an anchor: the system is not anchored to the
gregorian calendar (see E-07). "March 21st" remains as an approximate
description of the equinox: the year start oscillates within the drift
bound (|Δ| < 7 days), which is exactly what the corpus's thirty-first file
(the bounded-drift paper) already proved without voicing this internal
consequence.

Tests: `test_errata_new_year_2031`, `test_every_year_starts_on_soludyia`.

## E-02 — The vector "Yeshuvid 2031 = 19 April 2026" inherits E-01

With the year start on 2026-03-17, 30 Keuphero of 2031 falls on **April
15th, 2026** (not the 19th). The structural property is preserved: it is
still Loondyia, as ch. 11 required.

Test: `test_normative_vectors[greg4]`.

## E-03 — "Next Gran Tempalum: 2034, 2039, 2045" contradicts the pattern itself

The normative pattern of the same chapter (`5, 11, 16, 22, 28, 33, 39, 45...`)
starts the list of Gran Tempalum years in DY as: ... 2034, **2040**, 2045... "2039" is a
transcription error.

**GUS 2.0 resolution:** the recurrence pattern is the only normative
source (test `test_gran_tempalum_pattern_matches_spec`).

## E-04 — "Tempalum is month 00, the start of everything" vs. "month 00 acts as the close of the year"

Normatively and axiomatically they cannot coexist: the vectors of ch. 11
show Tempalum **after** month 12 (12-30 → 00-01 → new year), and all the
arithmetic of sacred days (two Sabatyeh days in Gran Tempalum, exact weeks)
only closes with Tempalum at the end.

**GUS 2.0 resolution:** Tempalum is the **close** of the Gerarion year
(month 00, last 4/11 days). The "start of everything" wording of ch. 1 is
non-normative rhetoric and is not reproduced.

Tests: vectors `2027-03-12 → 2031DY-00-01-A`, `test_two_saturdays_in_gran_tempalum`.

## E-05 — The Python code of ch. 10.10 is not executable

53 lines with typographic quotes (`"` → `"`, `'` → `'`), arrows and
divisions corrupted by copy-paste; accumulator in floating point (risk of
accumulated error over long horizons and dependence on the order of
summation).

**GUS 2.0 resolution:** reference implementation in exact integer
arithmetic (microdays), executable and covered by the full suite.
Test: `test_drift_bound_sawtooth` (drift bound over 500 years).

## E-06 — Tempalum day in the canonical format and the letter `B` of Sabatyeh

The corpus uses the letter `B` for Sabatyeh in the code of ch. 10.10 and
the canonical format of ch. 12 validates that alphabet, but ch. 4 does not
document it consistently. GUS 2.0 fixes the normative alphabet:
`S L M A T V B`.

## E-07 — Gerarion time is not anchored to the gregorian calendar

Structural clarification (formulated as an erratum because the wording of
E-01 could suggest otherwise): the Gerarion **occupies its own time**.
Its origin is **1 Keuphero of year 0 DY, defined by its JDN: day 0 =
JDN 1.719.313, Soludyia by definition.** (By conversion, that JDN
corresponds to 21 March of astronomical year -5 = 6 BC proleptic
gregorian; the equivalence is derived, not definitional.) From there the system is a
continuous count of its own: JDN is used solely as an absolute day counter
(integer, with no civil month or year), never as a gregorian calendar.

Consequences:

- **Year 0 ≠ year 1.** The count starts at year 0 (where the corpus's
  Yeshuvid anchor lies); year 1 begins 364 days later,
  March 19th, -4 (5 BC). Any text saying "year 01 = 6 BC" is off: 6 BC is
  year 0.
- **Every cited gregorian date is derived.** "Year 2031 DY begins on
  March 17th, 2026" is the result of applying the solar accumulator from
  the origin — not an input of the norm. Without gregorian, the system
  keeps working intact (instants, weeks, cycles, signatures).
- **Zero practical dependency.** The grego ↔ gero conversions (F-01/F-02)
  are interop arithmetic aliases. If tomorrow the civil calendar changed,
  Gerarion time would not move by a single day.

Test: `test_errata_e07_origin_independence`.

## Provenance

The full original corpus (32 documents — canonical corpus v1.2 + working
papers — with the philosophical and spiritual layer as an explicitly
non-normative appendix) is not published as a separate repository; its
complementary historical documentation is preserved in `docs/papers/`.
