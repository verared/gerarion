# Gerarion Universal Standard (GUS) — Specification v2.1.0

> **v2.1.0 (alpha-final):** Gran Tempalum is symmetric and infinite in both
> eras (DY/AY, spec §3/§6) and the UTC/TAI boundary is now normative (§9:
> midnight UTC, proleptic pre-1958 convention). No output changes in the DY
> era: the DY vectors of `gus-normative-001` are bit-for-bit those of
> `gus-normative-002`. New rules: new AY vectors in the `gus-normative-002`
> set. (v2.0: kept below as the base.)

>This specification supersedes the historical v1.2 draft (documented as
>non-normative complementary material in `docs/papers/`).
>Every v1 property that is preserved is reproduced here in executable form
>and verified by the test suite. Every divergence is documented in
>`docs/history/errata-v1.2.md`.

## 1. What it is

GUS defines:

1. **A regular calendar** — 12 months of exactly 30 days plus a closing
   period (Tempalum) of 4 or 11 days. All date arithmetic is free of edge
   cases.
2. **An invariant week** — every year is exactly 52 or 53 weeks, so that a
   fixed date always falls on the same day of the week.
3. **A continuous instant** — seconds since the origin, without leap
   seconds (analogous to TAI; see §9 for the exact UTC/TAI boundary).
   The count is linear and total.
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

Normative vector of the pattern (`gus-normative-002`): the DY GT years are
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
instante = day_index × 86.400 + segundos_del_día
day_index ≥ 0  → era DY;  day_index < 0 → era AY
```

- No leap seconds: each day lasts exactly 86,400 seconds and the instant
  is comparable and orderable across the whole domain.
- Luminous cycle (semantic, not computational): `SC` = 06:00–17:59,
  `LC` = 18:00–05:59. It is a label, not an arithmetic transformation.

## 6. Canonical timestamp format

```
AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O]

Ejemplo mínimo: 2031DY-03-08-T
Ejemplo completo: 2031DY-03-08-T-09:30:00-SC-TCJ+0
```

Nuvid day letters: S, L, M, A, T, V, B (Soludyia... Sabatyeh). Normalization
rules: see module `gerarion.format` (RULES 1-7 of the v1 corpus, preserved
in full, incl. `weekday_corrected`, `GERO_ETEMPALUM`,
`GERO_EINVAL`).

Eras: `DY` (after the origin) and `AY` (before). The Gran Tempalum rule is
**symmetric** (§3): it operates identically in DY and AY via the euclidean
modulus, keeping the solar drift bound |Δ| < 7 days on both sides of the
origin. The backward count (`year_start_day_index` by floor division +
accumulated GT years) is total and unambiguous: `year_start(-1) = -371`.

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

## 9. UTC/TAI boundary

What the reference implementation does **exactly** (verified in
`calendar.py`, `web/app.js`), and not one rule more:

- The instant scale is **analogous** to TAI: no leap seconds, linear
  count (`instant = day_index × 86,400 + time_of_day`). **It is not TAI
  with a table**: there is no TAI−UTC table anywhere in the code or in
  the vectors; leap seconds accumulated since 1972 (37 s at the time of
  this version) are **never applied** to any instant.
- Day start (**NORMATIVE, D-001 resolved**): the GUS day rolls at
  **midnight UTC** — the day `[n, n+1)` is the GUS-second interval
  `[n×86,400, (n+1)×86,400)` in the scale above. The day meridian is the
  reference civil clock's midnight UTC; it is **not** midnight TAI nor
  midnight in any local time zone.
- Before 1958 (**NORMATIVE, declared convention**): the same integer
  arithmetic extends **proleptically** to dates before the introduction
  of TAI (1958) and of the TAI−UTC table (1972): a pre-1958 GUS instant
  is a linear count of wall-clock civil UTC seconds on the proleptic
  gregorian, with no claim of matching historical UT1/TAI ephemerides.
  Correspondence with those scales stays outside GUS (adapters, not the
  core).
- Declared consequence: the GUS instant derived from a UTC time differs
  from actual elapsed TAI by the accumulated leap seconds (37 s in 2026,
  value frozen in the normative vectors). Any future change of this rule
  (e.g. proposal D-001 of midnight TAI) requires a new spec version and
  a new vector set via the Looking Period (GOVERNANCE §3.1) — it is not
  a retroactive application of this version.

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
