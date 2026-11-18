# ISO 8601 vs RFC 3339 vs Gerarion GUS v3.0.0 — Cap. 13.5 Identifier comparison

> Explanatory document (non-normative). Verified against the real
> repository code (`src/gerarion/`, `web/gerarion.mjs`, `impl-c/gus.c`)
> and the normative vectors `gus-normative-003.json` /
> `gus-3339-002.json`. Every claim is tagged **[CONFIRMED]** (verified
> against code or vectors) or **[NUANCE]** (the original draft
> over-reaches; here is the precise statement).

## 1. The three formats, side by side

| Criterion | ISO 8601 | RFC 3339 | Gerarion GUS v3.0.0 |
|---|---|---|---|
| Example | `20240115T123045` | `2024-01-15T12:30:45Z` | `2031DY-03-08-T-09:30:00-SC-TCJ+0` |
| Minimum length | 15 characters (**CONFIRMED**: `len=15`) | 20 characters (**CONFIRMED**: `len=20`) | 32 extended (**CONFIRMED**: `len=32`); 29 compact (**CONFIRMED**: `len=29`) |
| Compact form | yes (`20240115T123045`) but usually drops the zone | forbidden (requires dashes and colons) | yes, with the reference designator intact: `2031DY-03-08-T-093000-SC-TCJ0` |
| Mandatory zone | no (optional, in practice almost always omitted) | yes (`Z` or `±HH:MM`) | yes, with time: `TCJ±O` **mandatory** in every stamp with a time (**CONFIRMED** in the parser grammar, `src/gerarion/format.py`) |
| Zone ambiguity | high | low | **zero** (the offset is structural data of the stamp, not optional metadata) |
| DST / duplicated hour | the zone may have DST → ambiguous hour at the transition | same (`Z` has no DST, but the emitter's civil clock may) | the stamp has no DST: the `TCJ±O` offset is fixed relative to TCJ and every instant has one single canonical representation (**CONFIRMED**) |
| Physical scale | civil Gregorian (real leap seconds and DST) | real UTC (with leap seconds) | **TAI + 8,400 s (TCJ)**: a continuous monotonic `int64` with no internal leap seconds (**CONFIRMED** against `src/gerarion/tai.py`: `TAI_MINUS_UTC = 37 s` in 2026) |
| Calendar | irregular civil Gregorian | irregular civil Gregorian | regular: 12 × 30-day months + Tempalum; built-in weekday check digit (**CONFIRMED**: invariant `weekday = day_index mod 7`) |
| O(1) corruption detection | none | none | partial (see §2.2 **[NUANCE]**) |
| Single point of failure (definition) | Greenwich/ITU (Unix/UTC) | same | TCJ is a mathematical offset: any clock computes it without consulting anyone (**CONFIRMED**, cap. 13.0) |
| Horizon (Y2K38) | exposed (int32 epoch on many platforms) | same | solved: `instant` is an int64 count of continuous seconds (~292-billion-year horizon) |

## 2. What v3.0.0 solves structurally and the other two cannot touch

(Verified against the code; the TAI base takes effect with the embedded
IERS table — `src/gerarion/tai.py`, `web/gerarion.mjs`,
`impl-c/gus.c` — and the `gus-normative-003` / `gus-3339-002` vectors.)

### 2.1 Zone ambiguity and DST

In ISO 8601 the zone is optional and in practice omitted; in RFC 3339 it
is mandatory but the civil time of a `±HH:MM` with DST is ambiguous twice
a year (the "duplicated hour" of the transition). In GUS v3.0.0 the
offset `TCJ±O` is **mandatory** in every stamp with a time, admits
minutes (`TCJ-2:20`) and enters the instant computation; the offset is
fixed relative to TCJ, so a given instant produces exactly one canonical
string and vice versa. **[NUANCE]** GUS does not abolish DST in the
world: if the observer is in a DST zone, their civil-zone rules are still
needed to produce the correct `TCJ±O` at emission; what GUS removes is
ambiguity *inside the stamp* (which RFC 3339 achieves by requiring `Z`,
but with the designator always present and Atomic-Time semantics rather
than civil).

### 2.2 O(1) structural corruption detection

The weekday letter (`X`) is a natural check digit (`day_index mod 7`) and
the cycle (SC/LC) is consistent with the declared civil hour; the
combination (day + letter + hour + cycle + offset) is verifiable offline
in constant time (**CONFIRMED**: `format.quick_verify` in Python;
`quickVerify` in JS; `gus_quick_verify` in C; vector
`gus-quickverify-001.json` with tampering cases that are REJECTED
without normalizing). Neither ISO 8601 nor RFC 3339 offers anything
equivalent: the string `2024-01-15T12:30:99Z` can be syntactically valid
and temporally impossible, and neither format detects it structurally.
**[NUANCE]** The O(1) check detects *weekday* and *cycle*
inconsistencies (changing the day breaks the letter `X`; moving the hour
out of 06–17 breaks SC→LC), but it does NOT detect a small change within
a valid civil hour (`09:30:00` → `09:30:01`): that is different data,
not a corrupt stamp, and strong integrity against that comes from the
signature (GST, cap. 13.4) and the chained hash (cap. 13.6), not from
the textual format. The original draft over-reaches here; precision
matters.

### 2.3 Exact, reversible string ↔ integer duality

ISO 8601 and RFC 3339 are *presentations*: to compute you must go through
`datetime`, with zones and DST. In GUS v3.0.0 the canonical string and
the `instant` integer (`int64`) are the same thing seen two ways:
`instant = day_index·86400 + h·3600 + m·60 + s − offset_seconds` — an
exact integer projection, reversible without zone tables **[NUANCE]**
within the GUS domain (**CONFIRMED** against
`src/gerarion/calendar.py:instant_from_parts` / `web/gerarion.mjs` /
`impl-c/gus.c`: all three languages share the formula and the
`gus-normative-003` vectors). The outward bridge (Unix/UTC ↔ GUS) does
use the complete historical IERS TAI−UTC table (37 s in 2026; 29 entries
since 1958), embedded in all three languages: the UTC↔GUS conversion is
exact by segments, not "tableless". The draft itself says it correctly
in chapter 13.4 ("28-jump table + proleptic convention"); the "without
tables" claim in this section only holds inside the GUS domain.

## 3. Verified end-to-end example

The same physical instant (2026-05-23, 09:30:00 UTC) in the three worlds:

| World | Stamp | Note |
|---|---|---|
| ISO 8601 | `20260523T093000Z` | explicit `Z`; Greenwich civil time |
| RFC 3339 | `2026-05-23T09:30:00Z` | same; UTC scale with leap seconds |
| GUS TCJ+0 | `2031DY-03-08-T-09:30:00-SC-TCJ+0` → `instant = 64097688600` | **CONFIRMED** against the vector: `day_index 741871`, `weekday T`, hour 09:30:00 |
| GUS London | `2031DY-03-08-T-07:10:00-SC-TCJ-2:20` → **the same** `instant` | **CONFIRMED**: same integer, different observer civil view |

The Gerarion day (`day_index = 741871`) rolls at `TCJ+0` midnight — the
midnight of the Jerusalem meridian (35.2137°E), NOT UTC midnight:
7,200 s of meridian + 37 s of TAI−UTC later than UTC (**CONFIRMED**:
`tai_minus_utc(2026) = 37`).

## 4. What GUS v3.0.0 does NOT solve yet (honest gaps)

What the GUS v3.0.0 canonical string keeps out, by simplicity decision,
and which profile or future version would cover it:

1. **Fractional seconds in the text**: the canonical stamp runs at 1
   whole-second resolution (`SS`); sub-second precision (e.g.
   `tai_nanos`) lives in the structured layer of the signed document
   (GST/JSON) or in future profiles, not in the string. RFC 3339 does
   admit optional `.123`.
2. **Named time zones**: GUS emits an offset `TCJ±O`, not a zone name
   (`Asia/Tokyo`); conversion from a DST civil clock still needs tzdata
   on the emitting device. Same structural limitation as RFC 3339
   (`±HH:MM`).
3. **Cryptographic integrity**: the string standardizes what an instant
   means; it does not prove who signed it. Integrity comes from GST
   (Ed25519 + TAI anchor + Roughtime/TSA network anchor + TSLR with
   `ephemeris_hash` and Master-Nodes quorum; caps. 13.4/13.5), the
   chained log hash (cap. 13.6) and the daily notary (repo spec §8).
   None of the three layers replaces the others.
4. **Pre-Gerarion legal instruments**: no normative treatment at this
   time; the daily notary and the TSA (GUS-3161 profile) cover "existed
   before now", not "outcome of a human contract signed before GUS
   adoption" — recorded in `docs/decisions/`.
5. **Additional profiles**: Light IoT, GUS-for-notation, TSLR and PQC
   phase 2 are optional today; a minimal conforming implementation needs
   none of them, but a full forensic chain requires several coordinated
   pieces.

The honest conclusion is not "GUS replaces ISO 8601 and RFC 3339", but:
**GUS adds the layer they both lack** — a continuous physical scale (TAI)
with an exact string↔integer projection, a mandatory coordination
designator and no DST ambiguity inside the stamp — while keeping
normative bridges to the two formats the world already uses (README
"Time scale", spec §9 of 2.1 / §9.3 of 3.0, GUS-3339 profile).

---

## Annex: verification of the draft's claims (against the repo)

| Draft claim | Verdict against the repo |
|---|---|
| Extended stamp = 32 characters | **CONFIRMED** (`len=32`) |
| Compact stamp = 29 characters | **CONFIRMED** (`len=29`; `to_compact` in format.py) |
| RFC 3339 = 20 · ISO basic = 15 | **CONFIRMED** |
| "No colons ⇒ filesystem/URL safe" | **CONFIRMED** (compact drops `:`; keeps dashes, which are safe) |
| TCJ±O mandatory in stamps with time | **CONFIRMED** (parser grammar) |
| "Zero zone ambiguity" | **CONFIRMED** (the offset enters the computation; one view per instant) |
| Monotonic TAI + 8,400 s scale | **CONFIRMED** (`tai.py`, vectors) |
| "O(1) corruption detection" | **NUANCE** — detects weekday letter and cycle; does NOT detect fine HH:MM:SS changes (that is the GST signature and chained-hash layer) |
| "Reversible with no zone tables" | **NUANCE** — exact and reversible *within the GUS domain*; the Unix/UTC bridge does embed the 29-entry IERS table |
| "Fractional seconds outside the string" | **CONFIRMED** (1 s resolution in the text; extra precision in GST/JSON or profiles) |
| "TCJ is not a server" | **CONFIRMED** (mathematical offset; cap. 13.0) |
