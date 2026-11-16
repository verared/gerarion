# Technical report: why to adopt GUS time in computing

| Field | Value |
|---|---|
| Document | Adoption report — GUS 2.0 (Gerarion Universal Standard) |
| Audience | CTO, platform architecture and security, infrastructure teams |
| Status | Technical proposal (v1.0) |
| Verifiable basis | This repository: spec, 83 Python tests, 18 JS vectors, 12 E2E checks (Playwright), documented corpus errors E-01..E-07 |
| Scope of the judgment | Systems engineering and security. The calendar is presented as infrastructure, not as cosmology |

---

## 1. Executive summary

Computers do not run "time": they run a stack of historical compromises
(gregorian calendar + UTC + time zones + NTP/GNSS), each of which has
caused documented and costly incidents. The common thread across those
incidents is not bad luck: it is four structural defects that the current
standard carries built in.

GUS 2.0 is a time-infrastructure proposal designed to eliminate those
four defects by construction, not by patch:

1. **Continuous and regular scale**: 12 months x 30 days + Tempalum (4/11
   days); every year is an exact multiple of the week (364/371 days).
   No leap seconds, no 28-31 day months, no exceptions.
2. **Independent count of its own**: the continuous instant is an integer
   (`day × 86400 + h × 3600 + m × 60 + s`) from a fixed origin
   (1 Keuphero of year 0 DY = JDN 1.719.313). No civil decision
   (DST, reforms, leap seconds) can move it.
3. **Verifiable time, not consulted**: the instant can carry a signature
   (reference hash-only or SLH-DSA FIPS 205) and be anchored in a daily
   Merkle notary with multiple replicas (k-of-n quorum). Forging the past
   requires rewriting all replicas or breaking SHA-256.
4. **Post-quantum by design**: the hash-only signature remains secure in
   the Grover model (~2^128 margin); the SLH-DSA adapter is
   integrated with dispatch by the `alg` field.

**Recommendation:** layered coexistence — keep the gregorian calendar as
the user-facing presentation and record the canonical GUS time as the
layer of truth in logs, signatures, contracts and critical
synchronization. No big-bang required: the format is an envelope over the
continuous integer.

---

## 2. Method and honesty of this report

- Every incident cited in section 3 is public and verifiable
  (date, affected parties, mechanism). The complete catalog with sources
  is in the repository README.
- Every property of GUS asserted here has a test or vector that exercises
  it: the table in section 6 links which test upholds it.
- One of the defects of the original corpus was detected by us and
  is documented as an erratum with its test (E-01..E-07). That process —
  "the spec can be wrong, and we have proven we know how to detect it" —
  is part of the maturity argument.

---

## 3. Diagnosis: civil time as an engineering liability

### 3.1 The underlying defect: today time is consulted, not verified

A server's clock is a belief fed by the network: unauthenticated NTP,
satellite GNSS or a chain of administrators. Under that model, "the time"
has no cryptographic guarantee, and yet the critical protocols (Kerberos,
TLS, certificates, on-chain contracts) build security on a value that the
adversary can influence at zero cost.

### 3.2 Condensed incident catalog

| Defect | Real incident | Affected |
|---|---|---|
| Leap second | Jun 30, 2012: Linux kernel livelock (Reddit, Mozilla, LinkedIn, Cloudera down). Jan 1, 2017: Cloudflare → mass 502s | Millions of servers, every future leap second |
| Unauthenticated NTP / broken crypto | CVE-2013-5211 (monlist → DDoS ~400 Gbps); CVE-2014-9295 (weak keys in ntpd) | Global hosts and routers |
| GNSS spoofing | Jun 2011, Black Sea: 20+ ships with displaced GPS; jamming affects satellite-synchronized networks | Naval, aviation, 5G |
| Skew windows | Kerberos: ±5 min by design; cookies and tickets re-judged inside the window | Corporate infrastructure |
| Calendar irregularity | 28-31 day months, observable leap days, reforms: edge-case bugs every year | Finance, planning |
| Time zones and DST | tzdata and library bugs (Java 8 pre-1900); political decrees change semantics without notice | Logs, billing, jobs |
| Seconds since epoch as a contract | `block.timestamp` (SWC-116): the miner moves the clock seconds to alter luck/deadlines | DeFi, on-chain contracts |
| 32-bit ceiling | Y2038: `time_t` overflow on January 19, 2038 | Billions of legacy devices |

### 3.3 The four root causes

1. **Structural irregularity** — the civil calendar is not a metric
   scale; it forces perpetual edge-case logic.
2. **Arbitrary governability** — the semantics of time can be changed by
   decree (DST, leap seconds) without the software having a vote.
3. **Trust in mutable infrastructure** — the perceived time depends on
   the third party consulted (NTP, GNSS), each with its own attack
   surface.
4. **Non-verifiability** — after the fact, nobody can prove
   cryptographically what time it was. Time leaves no evidence.

GUS 2.0 answers point by point: total regularity; a single deterministic
rule with an optional and visible civil offset; time signable by the same
actor that declares it; and chained Merkle evidence that turns "it was
yesterday" into a provable property.

---

## 4. GUS 2.0 design: properties relevant to computing

### 4.1 Exact arithmetic, an eliminated class of bugs

- Gregorian input → day index → GUS date: pure integers; never
  `float`. The Gran Tempalum accumulator operates in integer microdays
  (Δ = 1.242.190 µd, threshold 7.000.000 µd): deterministic under any
  execution order, reproducible bit for bit across implementations.
- The JavaScript port of the core (`web/gerarion.mjs`) runs the same
  matrix of 18 normative vectors as the Python suite: the web and the CLI
  cannot diverge without the vector exposing it.

### 4.2 Continuous instant, no leap seconds

`instant = day × 86400 + h × 3600 + m × 60 + s`. There is no instant the
infrastructure cannot represent. Time comparison is an integer
subtraction; ordering is total; ranges are exact.

### 4.3 Invariant week

The day of the week is `day_index mod 7` — computed, prevailing over the
declared — where every year starts on Soludyia and every common year
closes exactly 52 weeks. Operational consequence: weekly schedulers and
jobs require neither leap-year tables nor manual date adjustments.

### 4.4 Time as a signable value

- **GST (signed instant):** reference hash-only signature (SHA-256 +
  Winternitz + Merkle tree) or SLH-DSA (FIPS 205) via adapter with
  dispatch by `alg`. The signature covers the canonical instant.
- **Daily Merkle notary:** day root per replica, chained to the previous
  day; standalone verifiable publication (`verify_bundle`). Forging a
  historical statement of time requires:
  - breaking SHA-256 (preimage: 2^256 of serial work, 2^128 quantum
    Grover), or
  - rewriting the log of all replicas that exceed the k-of-n quorum
    and the entire subsequent chain — visibly.
- Replicas with incorrect derivation are automatically excluded from
  the quorum (`bad_derivation`/`divergent`): a spoofed GNSS or a
  hurried administrator does not produce valid time; it produces an
  excluded, visible replica.

### 4.5 Presentation and order kept separate

`TCJ±O` (offset) and the SC/LC cycle are presentation fields. The time
zone cannot alter the canonical instant — the opposite of the current
semantics, where the zone can change which day it "is".

---

## 5. Comparison of time regimes

| Criterion | Gregorian/UTC + NTP/GNSS (status quo) | GUS 2.0 |
|---|---|---|
| Continuity | Broken by leap seconds (by future, indeterminate decree) | Continuous by definition |
| Year length | 365/366, months 28-31 | 364/371, always 30-day months |
| Week multiple | No (fractions of 52.16 weeks) | Always exact (52/53) |
| Invariant week | No | Yes (day_index mod 7, computed) |
| Representation ceiling | Y2038 (32-bit) in legacy | Integer without ceiling (BigInt) |
| Source of truth | Consulted network (NTP, GNSS) | Own arithmetic + optional signature |
| Post-hoc verifiability | None | Merkle + signature; forgery cost 2^256 |
| Post-quantum | Depends on external migrations (TLS) | Native hash-only + integrated SLH-DSA |
| Reaction to civil governance | Semantics change | Immune (optional, visible offset) |
| Contracts/logs | Consulted timestamp, mutable by operators | Anchorable to a published day_root |
| Adoption curve | Already installed | Layered coexistence (section 7) |

---

## 6. Evidence: from each property to its proof

| Property asserted in this report | Test / vector |
|---|---|
| Exact origin (JDN 1.719.313 = 21-03-(-5)) | `test_origin_jdn`, `test_normative_jdn_vector` |
| Regularity (every year a multiple of 7; start on Soludyia) | `test_all_year_lengths_multiple_of_7`, `test_every_year_starts_on_soludyia` |
| Drift bound of the integer accumulator (500 years) | `test_drift_bound_sawtooth` |
| Canonical format, normalization, GERO_* errors | `test_format.py` (14 tests, rules 1-7) |
| Hash-only signature: altering 1 bit fails | `test_crypto.py` (12 tests) |
| SLH-DSA FIPS 205 integrated | `test_adapters.py` (6 tests) |
| k-of-n notary: divergent replicas excluded | `test_notary_cluster.py` (7 tests) |
| Independence from the gregorian (E-07) | `test_errata_e07_origin_independence` |
| Web port identical to the core | `web/tests.mjs` (18 vectors) + E2E Playwright (12 checks) |

Reproduce: `PYTHONPATH=src python3 -m pytest tests/ -q` ·
`node web/tests.mjs` · `python3 e2e_web_test.py` (with static server).

---

## 7. Adoption strategy: layer by layer, no big-bang

| Phase | Application | Risk | Requirement |
|---|---|---|---|
| 0 | **Double seal**: logs and documents carry GUS alongside current UTC | Near zero | One-line format (`2031DY-03-08-T-09:30:00-SC-TCJ+0`) |
| 1 | **Files/fixed-event lists**: weekly planning, jobs, SLA | Low | Invariant week removes edge-case logic |
| 2 | **Time-signing operation**: hash-only GST on critical events | Low-medium | Operator keys; optional notary |
| 3 | **Multi-replica notary** (k-of-n ≥ 3 replicas, ≥ 2 operators) | Medium | Deployment descriptor; key rotation |
| 4 | **SLH-DSA FIPS 205** for maximum post-quantum assurance | Medium | Signature cost (~4.5 s on "common" hardware in 128s; 0.22 s in 128f) — fit for daily closing signatures, not per-tick |
| 5 | On-chain anchoring / contracts (`day_root` published beforehand) | High (external agreement) | Requires counterparty |

Migration does not require "replacing time": it requires adding a layer of
firm truth that the current regime cannot provide. The gregorian continues
to exist as a derived view — it is already generated exactly with
F-01/F-02.

---

## 8. Risks and cons (declared)

1. **Ecosystem**: it is a new calendar and format; the learning curve is
   real. Mitigation: phase-0 coexistence and web port with self-test
   (zero risk of silent divergence).
2. **Drift with respect to the civil day**: the GUS year is 364/371 days
   and the solar one ~365.2422; the year start oscillates within the
   bound |Δ| < 7 days (proven, not observational). If a domain requires
   anchoring to the exact equinox, the epoch-fork mechanism exists.
3. **The 128s signature is slow per tick**: this is deliberate
   (post-quantum horizon); the expected design is per-batch or per-day.
   For hot signing, 128f (0.22 s).
4. **Organic adoption**: a time standard is worth as much as its
   replicas; without notary replicas, the retroactive guarantee is only
   the issuer's signature. The risk is institutional, not mathematical.
5. **No mystical promises**: this report does not claim that GUS makes
   time "absolute" (that does not exist in computing); it makes it
   **regular, continuous and provable after the fact**, which are the
   three properties that no operational regime has today.

---

## 9. Conclusion and recommendation

Current time in computing is an implicit contract with the network and
with political decree; every default of that promise has been a public
incident. GUS 2.0 proposes the minimum a serious standard should
guarantee: a clock nobody can move, a scale without exceptions and a
proof of what "yesterday" was.

**Formal recommendation:**
1. Adopt phase 0 immediately (GUS double seal in new logs and
   documents).
2. Integrate hash-only GST into the operated signing pipeline.
3. Deploy a 3-replica notary before trusting any retroactive
   verification.
4. Evaluate SLH-DSA for daily closing signatures in environments with a
   post-quantum horizon.

The reference implementation (this repository) is ready and verified;
the vectors and the tests are the operational definition of every claim
made in this report.

---

## Annex A — Exact parameters (copy-safe)

```
JDN de origen        = 1.719.313      (1 Keuphero, year 0 DY; conversion: 03-21-(-5) proleptic gregorian)
Año                  = 12 x 30 días + Tempalum (mes 00): 4 días (común) / 11 (Gran Tempalum)
Año común / GT       = 364 / 371 días (52 / 53 semanas exactas)
Semana               = S L M A T V B  (Soludyia ... Sabatyeh); weekday = day_index mod 7
Acumulador solar     = r(n) = r(n-1) + 1.242.190 µd, umbral 7.000.000 µd (enteros exactos)
GT                   = 5, 11, 16, 22, 28, 33, 39, 45 ... (recurrencia, no tabla)
Instante             = día * 86400 + h*3600 + m*60 + s   (sin segundos intercalares)
Formato              = AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O]
Firma                = SHA-256 + Winternitz + Merkle (hash-only) / SLH-DSA-SHA2-128s|128f (FIPS 205)
Notario              = árbol Merkle diario, encadenado, quórum k-de-n, réplicas divergentes excluidas
Alfabeto del día     = día de semana calculado prevalece sobre el declarado
Eras                 = DY (después del origen) / AY (antes, años no negativos en la escala)
```

## Annex B — Repository inventory

```
src/gerarion/calendar.py       núcleo (enteros exactos, F-01..F-07)
src/gerarion/format.py         formato canónico + normalización
src/gerarion/gts.py            GST: create/verify con despacho de firmador
src/gerarion/hashots.py        firma hash-only de referencia
src/gerarion/adapters.py       SLH-DSA (FIPS 205) integrado
src/gerarion/notary.py         árbol Merkle diario
src/gerarion/notary_cluster.py notario multi-réplica (k-de-n) + verify_bundle
src/gerarion/cli.py            CLI gero
web/                            port del núcleo + calculador con self-test
docs/spec/                      especificación normativa y modelo de amenazas
docs/errata-v1.2.md             E-01..E-07 con tests
docs/papers/                  complementary historical papers (non-normative)
tests/  (83) web/tests.mjs (18) e2e_web_test.py (12 checks)
```
