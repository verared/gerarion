# Gerarion Universal Standard (GUS) — Specification v3.0.0

> **v3.0.0 (alpha):** MAJOR change of the time base (CLOSES D-001 and
> TODO-004). The instant scale is now defined on **TAI** with the embedded
> historical IERS TAI−UTC table (§9), and the global reference coordinate
> becomes **TCJ = TAI + 8,400 s** (Jerusalem Coordinated Time,
> 31.7683°N, 35.2137°E, 754 m) instead of midnight UTC. The `TCJ±O` field
> enters the instant computation and accepts minute offsets (`TCJ-2:20`);
> a new 29-character COMPACT format is added (§6). Every vector instant
> changes (new set `gus-normative-003` + `gus-3339-002`; the previous sets
> are archived in `vectors/archive/`).
> (v2.1.0: previous base, kept as reference in `docs/`.)

>This specification supersedes the historical v1.2 draft (documented as
>non-normative complementary material in `docs/papers/`).
>Every v1 property that is preserved is reproduced here in executable form
>and verified by the test suite. Every divergence is documented in
>`docs/errata-v1.2.md`.

## 1. What it is

GUS defines:

1. **A regular calendar** — 12 months of exactly 30 days plus a closing
   period (Tempalum) of 4 or 11 days. All date arithmetic is free of edge
   cases.
2. **An invariant week** — every year is exactly 52 or 53 weeks, so that a
   fixed date always falls on the same day of the week.
3. **A continuous instant** — atomic seconds (TAI, Layer 0) since the
   origin, without internal leap seconds; the global coordinate is
   TCJ = TAI + 8,400 s (Layer 1; see §9 for the exact UTC/TAI boundary).
   The count is linear, total and monotonic.
4. **A signed timestamp (GST)** — the signed time value using
   post-quantum schemes (hash-only in the reference: SHA-256 + Winternitz
   + Merkle).
5. **A chained daily Merkle notary** — objectivity: each day is sealed and
   chained to the previous one; the roots are published on independent
   replicas.

## 2. Security purpose

**A time whose forgery cost exceeds any benefit.**

Forging a valid GST requires, by construction:

- burning the preimage resistance of SHA-256 (≥ 2^128 against Grover, the
  only applicable quantum attacker; the rest of the structure makes no use
  of discrete-logarithm assumptions), **or**
- rewriting the log of *all* the independent notaries that anchored the
  day, without any external replica detecting the divergence, **or**
- compromising the signer's key and signing retroactively without altering
  the notary's opening chain — which the single-use discipline and the
  published roots make observable.

No political, legal or social dependency protects the value: only
mathematics and replication. This is the structural difference against any
historical calendrical decree.

## 3. Calendar structure

```
12 meses × 30 días = 360 días regulares (bloque De Kalendis)
Tempalum (mes 00, cierre del año): 4 días (año común) o 11 (Gran Tempalum)
Año común: 364 días = 52 semanas exactas
Gran Tempalum: 371 días = 53 semanas exactas
```

Origin: 1 Keuphero, year 0 DY. **The origin is defined by its Julian Day
Number: day 0 = JDN 1.719.313, Soludyia by definition.** Proleptic gregorian
conversion is an input/output interoperability service and is not part of
the definition of the GUS calendar. As a conversion example: JDN 1.719.313
corresponds to 21 March of -5 proleptic gregorian (6 BC, astronomical year
-5).

**Independence from the civil calendar.** Proper Gerarion time is a
continuous count from this origin; JDN is used only as an absolute day
counter. Every gregorian date cited in this specification (including the
equivalence of year 2031 = 17-03-2026) is a derived result obtained by
arithmetic (F-01/F-02), never a normative input. The system is
functionally complete without accessing any civil calendar.

**Independence from the civil week.** The GUS 7-day cycle is independent
of the civil week. The day letter (S L M A T V B) is a format label and
corresponds to no civil weekday. Measured example: 17 March 2026
(gregorian), start of year 2031 DY, carries letter `S` (of the format; no
claim is made about the civil weekday of that date).

Gran Tempalum rule (**symmetric in both eras**, closed form; spec 2.1):
with `S = 1_242_190` µd and `U = 7_000_000` µd, for **every** integer `year`
(positive, zero or negative; DY and AY eras):

```
r_y  = ((year mod U) + U) mod U        // euclidean residue: 0 <= r_y < U
r    = (r_y × S) mod U                 // year's solar accumulator
GT(year)  <=>  r + S >= U
```

Bit-for-bit equivalent to the iterative recurrence `r(n) = (r(n-1) + S) mod U`
for `year >= 0` (the 2.0 rule, kept as justification); the mods are
**euclidean** (result in `[0, U)`), never truncated toward zero — the only
change versus 2.0 is the extension: the sequence is **infinite in both
directions**. In C11, implement it with explicit `euclid_mod` and
`floor_div` (`/` truncates toward zero in negatives).

Normative vector of the pattern (`gus-normative-003`): the DY GT years are
`5, 11, 16, 22, 28, 33, 39, 45...`; the AY GT years are `-1, -6, -12, -17, -23, -29...`
(`0001AY` is a 371-day Gran Tempalum: `r(-1) = 5_757_810`, `r + S = U`).
The v1 corpus also listed "2039 DY" — erratum: it corresponds to 2040 DY.

Year start in closed O(1) form (proven equal to the length sum):

```
q, r = floor division of (year / U)      // 0 <= r < U, euclidean
accumulated GT years = q×S + floor(r×S / U)
year_start_day_index(year) = year×364 + 7×(accumulated GT years)
```

Verified: `year_start(0) = 0`, `year_start(-1) = -371`, and for every
`year >= 0` it matches bit for bit the 2.0 iterative length sum.

The carry is in **integer microdays**: no floating-point error at any
time horizon. This is a deliberate divergence from v1, which used `float`
(defect documented in the errata).

## 4. Year starts — solar oscillation

The year does not *always* begin exactly on March 21st: the common year
(364 days) is shorter than the tropical year, and the Gran Tempalum (371)
overshoots it. The year start oscillates around the equinox within the
drift bound (|Δ| < 7 days; sawtooth equation, proven in the drift paper,
`docs/papers/`).

GUS normative vector: year 2031 DY begins on **March 17th, 2026**
gregorian, Soludyia. The "March 21st" dates of the v1 corpus are
descriptive approximations of the equinox, no longer rules.

## 5. Continuous instant and cycles

```
instant = day_index × 86,400 + h·3600 + m·60 + s − offset_seconds
day_index ≥ 0  → DY era;  day_index < 0 → AY era
```

`HH:MM:SS` is the **observer's** civil time and `offset_seconds` is its
declared offset `TCJ±O` (§6, §9.4): thus
`2031DY-03-08-T-09:30:00-SC-TCJ+0` and
`2031DY-03-08-T-07:10:00-SC-TCJ-2:20` describe EXACTLY the same instant,
each observer keeping their civil time and their own cycle.
`offset_seconds` is a multiple of 60 with |offset| ≤ 86,400.

- No internal leap seconds (Layer 0, TAI): each day lasts exactly 86,400
  seconds and the instant is comparable and orderable across the whole
  domain. UTC leap seconds live ONLY in the historical table of the
  input adapter (§9.3).
- Luminous cycle (semantic, not computational): `SC` = 06:00–17:59,
  `LC` = 18:00–05:59, ALWAYS evaluated on the civil hour `HH` declared
  by the observer (§9.4). It is a label, not an arithmetic
  transformation.

## 6. Canonical timestamp format

Two official canonical formats (Cap. 13.1; precedent: ISO 8601
extended/basic):

```
EXTENDED (32 characters; canonical OUTPUT form):
  AAAAYY-MM-DD-X-HH:MM:SS-CC-TCJ±O
  2031DY-03-08-T-09:30:00-SC-TCJ+0
  Use: human readability, documents, audit logs.

COMPACT (29 characters; input & storage):
  AAAAYY-MM-DD-X-HHMMSS-CC-TCJ±O
  2031DY-03-08-T-093000-SC-TCJ0
  Use: machine-to-machine, JSON, network protocols.
```

Offsets `TCJ±O`: whole hours (`TCJ+0`, `TCJ+2`) or with minutes
(`TCJ-2:20`, `TCJ+3:10`; compact `TCJ-220`, `TCJ+310`). Emission rule:
if `offset_seconds % 3600 == 0`, emit `TCJ±H`; with minutes, `TCJ±H:MM`
(extended) or `TCJ±HMM` (compact). Zero offset is always emitted as
`TCJ+0` (extended) / `TCJ0` (compact). `TCJ±O` enters the instant
computation (§5) and describes the observer's civil time.

Nuvid day letters: S, L, M, A, T, V, B (Soludyia... Sabatyeh).
Normalization rules: see module `gerarion.format` (RULES 1-7 of the v1
corpus, preserved in full, incl. `weekday_corrected`, `GERO_ETEMPALUM`,
`GERO_EINVAL`).

## 6.1 Name levels (presentation only)

Recorded decision (TODO-003 closed): the format names (months, Nuvid
days, Tempalum days, letters S L M A T V B, eras DY/AY) **are canonical**;
there are no canonical numeric N0 names in 2.0 — the "numeric" N0 is
simply the valid numbering of the canonical format. Name levels (N0–N4)
are presentation only, with tables maintained outside this repository, and
never affect the instant, the day index, nor the conformance declared
against the vectors. The 2.0 spec defines the canonical format and the
instant; it defines no third-party presentation names beyond the format's
letters and numbering.

## 7. Signed timestamp (GST)

JSON document, fields: `v, ctx, alg, ts, ins, day, pub, sig, anchor`.

- `ctx = "GUS2-TS"` — strict domain separation.
- Signed bytes: `ctx || "\n" || ts || "\n" || ins || "\n"`.
- `alg` is interchangeable: the reference uses `WOTS16-MERKLE-REF-SHA256`
  (educational implementation, hash-only). The recommended production
  algorithms are **FIPS 205 (SLH-DSA)** and **FIPS 204 (ML-DSA)** with
  audited libraries; the verification semantics is the same interface.
  Note on the adapter: the PyPI package `slh-dsa` used by the reference is
  an **open-source library with no verified FIPS validation or external
  audit** — fine for interoperability and vectors; a real deployment
  requires an audited (or CMVP-validated) implementation.
- `anchor` — Merkle inclusion in the day's notary log.

### 7.1 Operational requirements of the signer

1. Each OTS leaf signs exactly one document. Reuse = LMS/XMSS key
   catastrophe: the state is audited and published.
2. Re-key per epoch: the tree is finite (2^8 signatures by default); roll
   to a new tree before exhausting it. The old key is archived for
   historical verification (not for signing).
3. Key rotation signed by the outgoing key (chain of trust), anchored on a
   notary day.

## 8. Daily notary

```
day_root(n) = SHA-256("GUS2-DAY" || n || tree_root(n) || day_root(n-1))
```

- Days are sealed in strict order (0, 1, 2, ...).
- Days without timestamps are also sealed (empty root defined): there are
  no exploitable gaps.
- The day root is published on independent replicas. Objectivity is the
  impossible divergence between honest replicas: rewriting the past
  requires convincing all of them simultaneously.

## 9. Time scale — TAI, TCJ and the UTC boundary (GUS 3.0.0)

Four-layer temporal architecture (Cap. 13.0 of the canonical document):

```
LAYER 3: TSLR (Real Local Solar Time) — OPTIONAL forensic profile;
         astronomical verification with ephemerides and quorum (§9.6).
LAYER 2: Gerorian civil date — human-readable presentation
         (§5/§6): months, Nuvid week, SC/LC cycle.
LAYER 1: TCJ = TAI + 8,400 s — global reference coordinate (§9.2).
LAYER 0: TAI — atomic, continuous and monotonic base; the substrate of
         the `instant` integer and of all signatures (§9.1, §9.3).
```

### 9.1 Instant definition (CLOSES D-001)

**DECISION ADOPTED in GUS 3.0.0** (replaces the "midnight UTC" boundary
of 2.1): the GUS instant is defined on **TAI** with the historical
TAI−UTC table explicit, and the global reference coordinate is **TCJ =
TAI + 8,400 s**. The integer `instant` is continuous seconds since the
origin (`0000DY-01-01-S-00:00:00-LC-TCJ+0` = 0), without internal leap
seconds:

```
instant = day_index × 86,400 + h·3600 + m·60 + s − offset_seconds
```

Two views of the same instant are valid and interconvertible
(`parts_from_instant(instant, offset_seconds)`); the canonical OUTPUT
form is ALWAYS the `TCJ+0` view (§6).

### 9.2 TCJ — Layer 1 (no SPOF)

```
TCJ = TAI + 8,400 s      (Jerusalem meridian, 35.2137°E)
```

TCJ is NOT a server nor a central authority: it is a fixed mathematical
offset that any clock can compute without querying anyone (no single
point of failure). Geographic reference: Jerusalem, 31.7683°N,
35.2137°E, 754 m. Convention with legacy systems: TCJ−UTC is about
+2 h 20 min 37 s in 2026 (8,400 s + 37 s of TAI−UTC).

### 9.3 Historical TAI − UTC table (input adapter, Layer 0)

The Unix/UTC → GUS bridge applies the complete historical IERS table
(embedded constant in `src/gerarion/tai.py`, `web/gerarion.mjs` and
`impl-c/gus.c`; 29 entries: 1958-01-01 = 10 s to 2017-01-01 = 37 s):

```
tai_unix = unix_seconds + tai_minus_utc(unix_seconds)
tcj_unix = tai_unix + 8,400
instant  = tcj_unix + 62_318_160_000     (constant GUS_UNIX_OFFSET)
```

- Pre-1958 (D-001.1, declared convention): proleptic extension with
  offset 0 s, with no claim of matching historical UT1/ephemerides.
- Inverse (`instant → unix`): exact by table segments; the round-trip is
  exact in both directions (verified by the test suite).
- A historical leap second crossing (e.g. 2016-12-31T23:59:60Z) produces
  an integer difference of 2 s: integer differences are exact physical
  durations (the property 2.1 did NOT guarantee).

### 9.4 Observer's SC/LC and minute offsets (CLOSES TODO-004)

The `SC`/`LC` cycle is ALWAYS evaluated on the civil hour `HH` declared
by the observer in the timestamp, never on the `TCJ+0` hour: an observer
in Tokyo at 02:00 local sees `LC`, exactly like one in Jerusalem at
02:00 local. Offsets accept minutes (§6); the valid range is
|TCJ±O| <= 24 h in multiples of 60 s.

### 9.5 Signing levels and Light-IoT profile (Cap. 13.4)

- **Level 0** — no signature (informational). **Level 1** — simple
  signature with TAI anchor. **Level 2** — + network anchor (Roughtime/
  TSA). **Level 3** — + astronomical TSLR verification with quorum.
- **Light-IoT profile**: internal clock + embedded key, local hash
  chaining and opportunistic synchronization; WITHOUT GPS/TPM/
  Roughtime. Declared explicitly as NOT suitable for forensic evidence
  (security concession for economic viability).

### 9.6 TSLR forensic profile (optional, Layer 3)

> **EXPERIMENTAL STATUS.** TSLR (Layer 3) and GCERTS (Cap 13.4) are
> EXPERIMENTAL profiles, separate from the normative kernel: they are not
> part of the calendar or canonical-timestamp conformance guarantee. GUS
> does not replace operating-system security controls, hardware isolation,
> or network mitigations; it complements them, never replaces them.

Optional astronomical verification for Level 3 evidence:

- Solar position (altitude/azimuth) computed with ephemerides (DE440)
  and pinned by the mandatory `ephemeris_hash`: a future ephemeris
  update never retroactively invalidates a previous signature.
- **3-of-4 Master Nodes quorum** (Jerusalem 31.7683°N/35.2137°E, Sèvres
  (BIPM) 48.8292°N/2.2203°E, Santiago 33.4489°S/70.6693°W, Sydney
  33.8688°S/151.2093°E): no single verification point of failure.
- **Polar protocol** (latitude |phi| > 66.5°): TSLR altitude/azimuth
  computation is degenerate for polar nights or days; in that case the
  verifier downgrades the timestamp to Level 2 and records the
  condition.
- Integrity invariants (Cap. 13.6): monotonicity of `tai_seconds`,
  cycle/civil-hour consistency of the observer, weekday consistency
  (invariant I-1), year-to-TAI consistency and verifiability of the
  declared ephemeris; logs with chained hashes and double sealing
  (`gero_canonical` + `tai_seconds`) for critical events.

## 10. Interoperability

- Exact convertibility with the proleptic gregorian via JDN (round trip
  verified by the test suite, no exclusion window).
- Direct mapping with gregorian `datetime`; no external libraries.
- Format forks (`1404IY-...`, `5786AH-...`) remain valid: a fork is a
  choice of epoch values, never of algorithm.

## 11. Versioning

- `GUS x.y.z` — semver over the *specification*, not the software.
- Changes in the conversion algorithm or in the canonical format: `x.y.0+`
  (major).
- Cryptographic or anchoring-only changes: `x.0.z` (minor).
- Any change requires: (1) new vectors in `tests/`, (2) an
  errata/changelog entry, (3) a public comment period of one release.
