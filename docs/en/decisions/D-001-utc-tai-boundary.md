# Decision D-001 (PROPOSED for 2.x) — GUS instant boundary with UTC/TAI

> **Status**: PROPOSAL STILL OPEN — spec 2.0 got **frozen with midnight
> UTC** (TODO-001 closed 2026-11-17; the lowest-numerical-registry decision).
> This decision stays open as a kernel-change candidate for a future 2.x:
> it requires the 90-day review window (GOVERNANCE §3.1), a new vector set
> (`gus-normative-002`) and witness regeneration, because it changes the
> numeric value of instants.
> **Spanish mirror**: [`docs/decisions/D-001-frontera-utc-tai.md`](../../decisions/D-001-frontera-utc-tai.md).

## 1. Context

Spec 2.0 (§9) declares the instant scale "analogous to TAI" and leaves three
points unspecified (TODO-001 in `docs/TODO-pendientes.md`):

- (a) the GUS day meridian: midnight UTC vs midnight TAI;
- (b) the UTC↔GUS conversion and the TAI−UTC table (37 s in 2026);
- (c) the treatment of TAI before 1958.

The current de facto state (documented, not normative): the reference web
clock re-labels the UTC second directly; the GUS day rolls at midnight UTC;
no table.

## 2. Proposed decision

**The GUS instant is defined on TAI**: `instant = atomic seconds elapsed
since (1 Keuphero, year 0, 00:00:00 proleptic TAI)`.

Sub-decisions:

- **D-001.1 (point c)** — *TAI before 1958 is a declared convention, not a
  measurement*: the proleptic extension of TAI into the past is an
  arithmetic act (the same nominal second), with no claim of matching
  historical ephemerides (UT1/ET). Every GUS date before 1958-01-01 TAI
  carries that condition in its semantics.
- **D-001.2 (point a)** — *the GUS day rolls at midnight TAI*: the day
  `[n, n+1)` belongs to the scale; civil reading (wall calendar, time
  zones) is an adapter, never part of the instant. Operational
  consequence: today TAI midnight occurs ~37 s after UTC midnight.
- **D-001.3 (point b)** — *the UTC↔GUS conversion is an adapter with an
  explicit table*: `adapters/tai-utc.json` is published (validity date →
  TAI−UTC offset in seconds), regenerated with every release that changes
  it, with checksum in the CHANGELOG. The Python/JS reference will move
  from "direct re-labeling" to applying the table's current offset; the
  web clock will show the corrected civil time (currently a 37 s
  difference, made visible in the README).

## 3. Rejected alternatives

- **(1) Midnight UTC (status quo)**: accumulates an undeclared drift
  versus TAI that grows with no correction mechanism; it turns "no leap
  seconds" into a hollow promise exactly at the boundary where it is
  needed.
- **(3) Declared epoch without table** (the current "not specified"):
  it cripples forensic attestation — a GUS log would never say how many
  atomic seconds lie between two marks — for no gain in return.

## 4. Declared cost

- The TAI day separates ~37 s from the UTC civil day (in 2026): civil
  users will perceive the adapter's adjustment, not the core's.
- It changes the instants of the existing `instant` vectors (constant
  offset `− Δ(t)`), which requires a new vector set version
  (`gus-normative-002`) and regeneration of all test seals. Migration
  cost: one constant per replica, no historical log rewrite (old logs
  declare the vector set version they were created with).

## 5. CGPM 2025 (context, not a requirement)

The CGPM resolved to abolish leap seconds from UTC by 2035; leap smear
(Google/AWS) and NTS (RFC 8915) mitigate symptoms, not the cause. TAI as
the base aligns GUS with that resolution: UTC remains, as a scale, a civil
adapter with a table — not the scale.

## 6. Update plan (when the window closes)

1. Spec 2.1: definition in §3/§9, pre-1958 proleptic semantics (§9).
2. `vectors/gus-normative-002.json` with recomputed instants and the
   current TAI−UTC table embedded as a vector-set constant.
3. `tai-utc` adapter Python/JS + web clock regeneration.
4. Differential validation Python/JS/C against the new vectors.
