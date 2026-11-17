# GUS-3339 Profile — GUS instant ↔ RFC 3339 (UTC)

> **Layer**: 0 (normative core) · **Version**: 3339-001 · **Status**: normative
> **Spanish mirror**: [`docs/profiles/gus-3339-perfil.md`](../../profiles/gus-3339-perfil.md) — this English version prevails (EN > ES).
> **Vectors**: [`vectors/gus-3339-001.json`](../../../vectors/gus-3339-001.json)

## 1. Purpose

GUS-3339 defines the single interoperability rule an existing system
needs in order to *emit and consume* GUS time without adopting the
Gerarion calendar: convert a GUS integer instant to an RFC 3339 string
in UTC, and back. It is the functional equivalent of ISO 8601 / RFC 3339
for the GUS instant scale — not a general-purpose date parser.

With this profile, any existing field that already carries
`2026-05-23T09:30:00Z` (SQL columns, HTTP headers, JSON, X.509
`notBefore`, logs) can carry GUS time with no schema changes.

## 2. Anchor constant

| Name | Value | Definition |
|---|---|---|
| `GUS_UNIX_OFFSET` | `62_318_160_000` | GUS instant of `1970-01-01T00:00:00Z` = `(2,440,588 − 1,719,313) × 86,400` |

Equivalence: for a GUS instant `I`, the labeled UTC second is
`unix = I − GUS_UNIX_OFFSET`. Both scales are leap-second-free labels
(see §9 of the spec for the exact UTC/TAI boundary), so the mapping is
**bijective** over the declared domain.

## 3. Profile rules (MUST)

1. **Single canonical form**: `YYYY-MM-DDTHH:MM:SSZ`. `T` and `Z` MUST be
   uppercase. A profile-conformant RFC 3339 sender does not produce
   lowercase, decimal fractions or zone offsets.
2. **UTC only**: forms carrying an offset (`+01:00`) are invalid under
   the profile. Anyone receiving local time MUST convert to UTC first.
3. **Second `:60` forbidden** (MUST): the GUS scale has no leap seconds.
   Folding `:60` into the next `00:00:00` would break injectivity; a UTC
   source that emits `:60` MUST convert to the Unix label first.
4. **Domain**: Gregorian years `0000..9999`. The GUS origin (year −5)
   and the whole AY era are outside this format: use the GUS canonical
   string (`AAAAAY-MM-DD-X…`) or the integer instant for that range.
5. **Arithmetic**: pure integer conversions via the proleptic Gregorian
   JDN (same base as the GUS core). Canonical error: `GERO_E3339`.

## 4. Conformance

An implementation declares the GUS-3339 profile if and only if it passes
100 % of the vectors in `vectors/gus-3339-001.json` (8 mappings,
8 rejections, 3 canonical-format coherence cases). Core conformance
(`gus-normative-002.json`) is independent and does not imply this
profile. Verified in: Python (`tests/test_profiles.py`), JavaScript
(`web/tests.mjs`, `node web/profiles-conformance.mjs`). The reference C
implementation does not implement profiles (core only).

## 5. Canonical errors

- `GERO_E3339` — out-of-profile input (non-canonical syntax, offset,
  `:60`, invalid date) or instant outside the 0000..9999 domain.
