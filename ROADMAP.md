# Gerarion Time — Technical Roadmap & Verifiable Vision

> **Living, Non-Binding Technical Vision — Zero Promises, Zero Fixed Dates.**
>
> *Gerarion Time* is an open, modular, offline-first, and verifiable temporal
> infrastructure that **complements — without replacing — UTC, NTP, PTP, and
> operating system clocks**. This document is a living technical compass, **not
> a contract, delivery guarantee, or schedule with fixed dates**. Every `[x]`
> box requires reproducible evidence in this repository; every `[ ]` box
> represents an open direction that *may* be pursued over months or years if
> the project and community advance in that direction.
>
> - **Audited baseline:** `v3.2.2` (`322a650`)
> - **Normative specification:** `GUS v3.0.0` (frozen arithmetic and vectors)
> - **Spanish mirror:** [`ROADMAP.es.md`](ROADMAP.es.md) (in case of divergence, EN > ES)
> - **Related references:** [`COMPATIBILITY.md`](COMPATIBILITY.md) · [`docs/architecture/SATELLITE-REPOS.en.md`](docs/architecture/SATELLITE-REPOS.en.md) · [`SECURITY.md`](SECURITY.md) · [`docs/en/audit/AUDIT-REPORT-v3.0.0.md`](docs/en/audit/AUDIT-REPORT-v3.0.0.md)

---

## Evolution Horizons (No Committed Dates)

- **Short term (consolidation & real-world adoption):** Practical integration of
  `gt-core`, `gt-gst`, and `gt-gts` into real applications (web services, APIs,
  auditable event logs), smoother ergonomics for consuming standalone
  satellites, explicit 32-bit CI coverage, and embedded deployment guides.
- **Medium term (experimental profiles & platform infrastructure):** Working
  prototypes with reproducible test vectors for `gt-tslr` and `gt-gcerts`,
  Linux user-space adapters (`CLOCK_TAI` + verified `chrony`/PTP inputs), and
  hardware key custody (`TPM`/`HSM`) developed in separate satellite
  repositories.
- **Long term (external validation & open ecosystem):** Independent third-party
  cryptographic audits, interoperable third-party implementations built from
  [`docs/specs/`](docs/specs/GUS.en.md), formal standards-body review (IETF),
  and desktop/OS-level integration only after proven user-space maturity.

---

## Four-Level Maturity Model & Ecosystem Matrix

No module advances in maturity merely by having code or by being declared
stable in a README; promotion requires verifiable artifacts, tests, and — for
production security claims — independent external review.

| Level | Definition |
|---|---|
| `EXPERIMENTAL` | Specification and/or early prototype; subject to change; not for production. |
| `IMPLEMENTED` | Working reference code exists, but full cross-platform parity or hardening is incomplete. |
| `VERIFIED` | Cross-verified against shared normative vectors and automated CI suites (`reuse`, unit, conformance, fuzz/sanitizers). |
| `STABLE` | Frozen normative contract (`>=3.2.0,<4.0.0`), verified across platforms, and reproducible via `EXPORT-MANIFEST.json`. *(Cryptographic production readiness additionally requires external audit + hardware key custody.)* |

### Ecosystem Matrix (`v3.2.2`, aligned with [`COMPATIBILITY.md`](COMPATIBILITY.md))

| Satellite | Specification | Maturity (`v3.2.2`) | Honest Scope & Limits |
|---|---|---|---|
| `verared/gt-core` | [`TCJ.en.md`](docs/specs/TCJ.en.md), [`GUS.en.md`](docs/specs/GUS.en.md) | **STABLE / VERIFIED** | Frozen `GUS v3.0.0` kernel; zero-malloc C11, Python, and JS; 100 % standalone. |
| `verared/gt-gus` | [`GUS.en.md`](docs/specs/GUS.en.md) | **STABLE / VERIFIED** | Canonical 29/32-char syntax, normalization rules 1–7, `quick_verify`, `int64` + `nanos`. |
| `verared/gt-tcj` | [`TCJ.en.md`](docs/specs/TCJ.en.md) | **STABLE / VERIFIED** | `TCJ = TAI + 8,400 s`, versioned `IERS-C-2026.1` `TAI−UTC` bridge with horizon check. |
| `verared/gt-calendar` | [`CALENDAR.en.md`](docs/specs/CALENDAR.en.md) | **STABLE / VERIFIED** | Regular `AY`/`DY` + deterministic GUTI-1 translation across 10 calendar systems. |
| `verared/gt-gts` | [`GTS.en.md`](docs/specs/GTS.en.md) | **STABLE (core) / EXPERIMENTAL (Roughtime)** | Clock trust state machine (`VERIFIED`/`HOLDOVER`/`UNVERIFIED`/`REJECTED`) + sub-second anti-rollback; Roughtime profile is experimental. |
| `verared/gt-gst` | [`GST.en.md`](docs/specs/GST.en.md) | **STABLE reference (`GST v2`); external audit pending** | Hybrid **Ed25519 + ML-DSA** over RFC 8785 JCS, `GUS3-GST-V2`, anti-downgrade, fail-closed `ReplayGuard`, optional daily Merkle notary. **Requires independent third-party cryptographic audit and TPM/HSM custody before critical production use.** Legacy `WOTS+` is deprecated (`src/gerarion/deprecated/hashots.py`). |
| `verared/gt-interop` | [`INTEROP.en.md`](docs/specs/INTEROP.en.md) | **STABLE (`RFC 3339` / `ISO 8601` / `Unix`) / EXPERIMENTAL (`RFC 3161`)** | Strict GUS-3339 parser with shared negative vectors; `RFC 3161` TSA profile is experimental. |
| `verared/gt-tslr` | [`TSLR.en.md`](docs/specs/TSLR.en.md) | **EXPERIMENTAL** | Specification and empty scaffold only; no reference implementation yet. |
| `verared/gt-gcerts` | [`GCERTS.en.md`](docs/specs/GCERTS.en.md) | **EXPERIMENTAL** | Specification and empty scaffold only; no reference implementation yet. |

---

## Master Roadmap (10 Phases + Cross-Cutting Tracks)

### Phase 1 — Temporal Foundation (`gt-core`, `gt-tcj`, `gt-gus`)
**Objective:** Freeze a deterministic, leap-second-free atomic coordinate (`TCJ = TAI + 8,400 s`), unambiguous 29/32-character syntax, and bit-identical integer arithmetic across C11, Python, and JavaScript.

- [x] Frozen normative specification `GUS v3.0.0` and domain specs (`docs/en/gus-3.0.0.md`, `docs/specs/TCJ.en.md`, `docs/specs/GUS.en.md`).
- [x] Continuous atomic scale `TCJ = TAI + 8,400 s` with exact integer bounds and separated `nanos` (`impl-c/core/gus_core.c`, `src/gerarion/core/calendar.py`, `web/engine/core.mjs`).
- [x] Canonical 32-char and compact 29-char syntax, normalization rules 1–7, and `quick_verify` (`impl-c/core/gus_core.c`, `src/gerarion/core/format.py`, `web/engine/core.mjs`).
- [x] Shared CC0 normative, quick-verify, and `AY` regression vectors verified across all three runtimes (`vectors/gus-normative-003.json`, `vectors/gus-quickverify-001.json`, `vectors/gus-regression-001.json`, `tests/test_conformance.py`, `tools/fuzz_diff.py`).

**Acceptance criterion:** Zero divergence across C11, Python, and JS on all normative vectors and differential fuzzing.

---

### Phase 2 — Universal Calendar Translation Engine (`gt-calendar`)
**Objective:** Provide pure-integer, deterministic bidirectional translation across 10 calendar systems pivoting on `day_index` / `JDN` with zero network or `Intl` dependencies.

- [x] Deterministic 10-system GUTI-1 engine (`gus`, `greg`, `julian`, `egyptian`, `ethiopic`, `bahai`, `maya`, `islamic`, `hebrew`, `chinese`) in C11, Python, and JS (`impl-c/calendars/gerarion_calendars.c`, `src/gerarion/calendars/engine.py`, `web/engine/guti.mjs`).
- [x] Versioned offline Chinese lunisolar table (1645–2650) with strict range enforcement (`impl-c/calendars/china_table.c`, `src/gerarion/calendars/china_table.py`, `web/engine/china-table.mjs`).
- [x] Cross-verified against 63,850+ GUTI vectors and documented historical tolerances (`vectors/guti-calendars-001.json`, `tests/test_guti_calendars.py`, `docs/en/CALENDAR-ENGINE.md`).
- [ ] Optional GUTI-2 extension profiles (additional regional/historical calendars or extended astronomical ranges beyond 1645–2650, only if backed by verifiable tables and vectors).

**Acceptance criterion:** Bit-for-bit parity across C11, Python, and JS on `vectors/guti-calendars-001.json` with zero silent extrapolation outside validated ranges.

---

### Phase 3 — Portable Runtime & Bindings
**Objective:** Ensure the core runs cleanly from bare-metal microcontrollers to servers and browsers without dynamic allocation or hidden platform dependencies.

- [x] Zero-malloc, OS-clock-free C11 standalone library `libgerarion-core` compiled cleanly with `-Wall -Wextra -Werror` under GCC/Clang (`impl-c/core/gus_core.c`, `impl-c/Makefile`, `tests/test_export_module.py`).
- [x] Pure-stdlib Python core and zero-dependency ESM JavaScript engine using `BigInt` (`src/gerarion/core/`, `web/engine/core.mjs`).
- [x] Shared conformance vectors and cross-satellite assembly tests in C11, Python, and JS (`tests/test_satellite_integration.py`, `.github/workflows/ci.yml`).
- [ ] Explicit 32-bit architecture CI matrix (e.g., `i686` / `armv7` / `arm-none-eabi` cross-compilation and vector execution).
- [ ] Formal long-term C ABI stability policy and automated ABI-check gate across minor releases.
- [ ] Detailed embedded/bare-metal deployment guides (MCU linker budgets, tick-to-TCJ bridging, static memory profiles).

**Acceptance criterion:** Green builds and vector conformance across 64-bit, 32-bit, and bare-metal targets with a documented ABI contract.

---

### Phase 4 — Offline-First Infrastructure
**Objective:** Guarantee that conversion, serialization, and verification work 100 % offline without external APIs, trackers, or silent network fallbacks.

- [x] 100 % client-side offline web calculator with fail-closed Service Worker and strict CSP (`web/sw.js`, `e2e_web_test.py`).
- [x] Zero-network sandbox verification for core and calendar conversion (`tests/test_guti_m0_sandbox.py`, `tools/verify_gus.py`).
- [x] Standalone offline verification of exported satellites via `EXPORT-MANIFEST.json` (`tools/export_module.py`, `tests/test_satellite_integration.py`).
- [ ] Automated, auditable workflow for updating versioned IERS `TAI−UTC` tables prior to horizon expiration (`IERS-C-2026.1` / post-2027 CGPM continuous UTC transition).

**Acceptance criterion:** Zero outbound network calls during conversion, serialization, or verification, verified by automated sandbox and Playwright airplane-mode E2E tests.

---

### Phase 5 — Time Trust & Synchronization (`gt-gts`)
**Objective:** Separate monotonic interval measurement from authenticated absolute time and make clock uncertainty explicit rather than silent.

- [x] Clock trust state machine (`VERIFIED`, `HOLDOVER`, `UNVERIFIED`, `REJECTED`) in Python and C11 (`src/gerarion/gts/clock.py`, `impl-c/clock/gus_clock.c`, `docs/specs/GTS.en.md`).
- [x] Persistent sub-second `(instant, nanos)` anti-rollback anchors and explicit `require_authenticated` policy (`tests/test_clock_state.py`, `impl-c/conformance.c`).
- [x] Experimental Roughtime receipt verification profile (`src/gerarion/gts/roughtime.py`, `tests/test_profiles_roughtime.py`).
- [ ] Distributed network-partition and split-brain fault-injection test suite for multi-source clock fleets.
- [ ] Hardware-in-the-loop validation against real GNSS receivers, PTP grandmasters, and physical oscillator holdover curves.

**Acceptance criterion:** Deterministic state transitions under rollback, unauthenticated sources, and holdover exhaustion, validated both in simulation and on physical timing hardware.

---

### Phase 6 — Cryptographic Temporal Evidence (`gt-gst`)
**Objective:** Provide post-quantum-ready, tamper-evident timestamp envelopes (`GST v2`) with strict canonicalization, anti-downgrade binding, and fail-closed replay protection.

- [x] Normative `GST v2` envelope with hybrid **Ed25519 + ML-DSA**, RFC 8785 JCS (`±(2^53 - 1)` integer enforcement), domain `GUS3-GST-V2`, and anti-downgrade descriptor binding (`src/gerarion/gst/envelope.py`, `src/gerarion/gst/jcs.py`, `src/gerarion/gst/adapters.py`, `docs/specs/GST.en.md`).
- [x] Fail-closed `ReplayGuard` (`seq` + `nonce`) and optional daily Merkle notary with distinct-signer quorum (`src/gerarion/gst/notary.py`, `src/gerarion/gst/notary_cluster.py`, `tests/test_jcs_gstv2.py`, `tests/test_notary_cluster.py`).
- [x] Legacy `WOTS+` isolated in `src/gerarion/deprecated/hashots.py` with `DeprecationWarning`, outside normative `GST v2`.
- [ ] Operational key-rotation and revocation policies backed by hardware key custody (`TPM`/`HSM`).
- [ ] Language-independent external cryptographic cross-verification test vectors for `GST v2` envelopes.
- [ ] **Independent third-party cryptographic security audit** of `gt-gst` and the Merkle notary prior to critical production use.

**Acceptance criterion:** Closed external cryptographic audit report with zero unmitigated high/critical findings, hardware custody reference profile, and independent third-party verifier passing shared vectors.

---

### Phase 7 — Interoperability (`gt-interop`)
**Objective:** Bridge legacy civil formats cleanly at system boundaries without compromising internal TCJ monotonicity.

- [x] Versioned `TAI−UTC` table (`IERS-C-2026.1`) with explicit extrapolation flag past horizon (`src/gerarion/tcj/tai.py`, `impl-c/tai/gus_tai.c`, `web/engine/tcj-tai.mjs`).
- [x] Strict `RFC 3339` (`GUS-3339`), `ISO 8601`, and `Unix` bidirectional bridges with shared positive and negative vectors (`src/gerarion/interop/profiles.py`, `vectors/gus-3339-002.json`, `vectors/gus-3339-negative-001.json`, `tests/test_profiles.py`, `tests/test_profiles_negative.py`).
- [x] Experimental `RFC 3161` TSA sidecar adapter (`src/gerarion/interop/tsa.py`, `tests/test_profiles_tsa.py`, `docs/specs/INTEROP.en.md`).
- [ ] Support for **RFC 9557** internet date/time extensions (explicit time-zone and calendar suffix annotations).
- [ ] Production hardening of `RFC 3161` TSA verification and real-platform `NTP`/`NTS`/`PTP` observation bridges.

**Acceptance criterion:** Strict round-trip compliance on positive and negative vector suites across RFC 3339, RFC 9557, and authenticated external time-stamping/synchronization bridges.

---

### Phase 8 — Astronomical & Physical Context (`gt-tslr`)
**Objective:** Explore optional Level-3 forensic astronomical cross-verification (*Tiempo Solar Local Real*) cleanly isolated from the normative core.

- [x] Experimental domain specification and standalone satellite scaffold published (`docs/specs/TSLR.en.md`, `docs/specs/TSLR.es.md`, `verared/gt-tslr`).
- [ ] Deterministic solar-position calculation engine (algorithmic specification + reference implementation in `gt-tslr`).
- [ ] `UT1` / JPL `DE440` ephemeris cross-verification profile with versioned offline tables.
- [ ] Explicit geographic/altitude uncertainty propagation model and reproducible CC0 test vectors.

**Acceptance criterion:** Reproducible solar-context vectors verified against published astronomical ephemerides within declared uncertainty bounds, without altering `gt-core`.

---

### Phase 9 — Temporal Certificate Validity Profiles (`gt-gcerts`)
**Objective:** Define unambiguous TCJ-based temporal validity windows for PKI certificates, cleanly isolated from the normative core.

- [x] Experimental domain specification and standalone satellite scaffold published (`docs/specs/GCERTS.en.md`, `docs/specs/GCERTS.es.md`, `verared/gt-gcerts`).
- [ ] Normative `notBefore` / `notAfter` evaluation semantics over TCJ coordinates.
- [ ] Explicit verification policies under `HOLDOVER` and `UNVERIFIED` clock states.
- [ ] X.509 extension/interoperability profile, reproducible test vectors, and independent security review.

**Acceptance criterion:** Unambiguous certificate validity evaluation across clock trust states with test vectors and external PKI security review.

---

### Phase 10 — Operating System & Infrastructure Integration (Future External Satellites)
**Objective:** Enable incremental adoption in Linux, embedded, and observability stacks via user-space libraries and adapters — never rushing kernel modifications.

- [x] Standalone `libgerarion` and `libgerarion-core` release artifacts with `SHA256SUMS.txt` (`.github/workflows/release.yml`, `v3.2.2`).
- [ ] Linux user-space daemon reading `CLOCK_TAI` + `chrony`/PTP status into `gt-gts` trust states.
- [ ] Reference embedded and industrial examples (bare-metal C11 + RTOS integration).
- [ ] Observability integration (e.g., OpenTelemetry trace/log timestamp attributes and `GST v2` exporters).
- [ ] Exploratory `systemd`/desktop tooling and long-term evaluation of OS/kernel interfaces only after proven user-space maturity.

**Acceptance criterion:** Production-proven user-space adapters operating cleanly alongside standard OS time services without requiring custom kernels.

---

### Cross-Cutting Track A — Ecosystem Integrity & Reproducible Releases
**Objective:** Guarantee that every satellite repository is a byte-for-byte verifiable projection of a tagged commit in `verared/gerarion`.

- [x] Deterministic export from versioned commit with `EXPORT-MANIFEST.json` (`gerarion-export-manifest/1`) and `--verify-existing` (`tools/export_module.py`, `COMPATIBILITY.md`, `compatibility.json`).
- [x] Cross-language integration tests on cleanly assembled satellites in C11, Python, and JS, gated in CI (`tests/test_satellite_integration.py`, `.github/workflows/ci.yml`).
- [x] 100 % REUSE 3.3 licensing compliance and CycloneDX 1.5 SBOM (`REUSE.toml`, `sbom.cdx.json`, `.github/workflows/ci.yml`).
- [ ] External cryptographic signing of release tags and `EXPORT-MANIFEST.json` artifacts in CI (e.g., Sigstore/Cosign or GPG attestations).
- [ ] Formal multi-satellite rollback and emergency synchronization runbook.

**Acceptance criterion:** Every release tag and satellite export is deterministically reproducible, hash-verified, license-compliant, and cryptographically attested.

---

### Cross-Cutting Track B — Security, Reliability & Conformance
**Objective:** Maintain continuous adversarial testing, memory safety, and honest threat modeling across all implementations.

- [x] Differential fuzzing across Python, JS, and C11 (`tools/fuzz_diff.py`, `impl-c/audit_stress.c` — 1M+ round-trips) and ASan + UBSan stress audit (6.5M+ checks, 0 errors, `impl-c/Makefile`).
- [x] Adversarial test suites for JCS, anti-downgrade, `ReplayGuard`, sub-second rollback, and static analysis (`tests/test_jcs_gstv2.py`, `tests/test_adversarial_security.py`, `tests/test_clock_state.py`, `.github/workflows/codeql.yml`).
- [x] Published threat model, security policy, and internal audit report (`docs/en/threat-model.md`, `SECURITY.md`, `docs/en/audit/AUDIT-REPORT-v3.0.0.md`).
- [ ] Independent third-party security review of the full cryptographic and notarial stack.
- [ ] Formal vulnerability disclosure / bug-bounty program (if and when external production deployments warrant it).

**Acceptance criterion:** Zero unmitigated memory-safety or conformance failures in CI, plus published third-party audit closure before production cryptographic claims.

---

## Ten Architectural Principles

1. **Open:** Public specifications, dual-licensed reference code (`MIT OR Apache-2.0`), `CC-BY-4.0` documentation, and `CC0-1.0` test vectors.
2. **Decentralized:** `TCJ` is a mathematical offset (`TAI + 8,400 s`), not a central server; verification never depends on a single authority.
3. **Offline-First:** Core arithmetic, 10-calendar translation, and cryptographic verification operate with zero network requests.
4. **Deterministic:** Pure integer arithmetic across C11, Python, and JavaScript produces bit-identical outputs for every valid input.
5. **Portable:** Zero-malloc C11 core, pure-stdlib Python core, and zero-dependency ESM JavaScript run from MCUs to browsers.
6. **Interoperable:** Clean, auditable boundary bridges to `UTC`, `TAI`, `Unix`, `RFC 3339`, `ISO 8601`, and `RFC 3161` without mutating internal coordinates.
7. **Verifiable:** Every claim is backed by shared CC0 vectors, reproducible `EXPORT-MANIFEST.json` hashes, and fail-closed verification.
8. **Modular:** Independent domain satellites (`verared/gt-*`) let adopters take only what they need without pulling the entire stack.
9. **Open & Non-Proprietary (Transparent Normative Reference):** An open standard with no central authority or commercial ownership, a transparently documented normative epoch and reference meridian (`TCJ`), and impartial bidirectional translation across 10 calendar systems.
10. **Transparent:** Honest maturity boundaries, explicit non-guarantees, and clear separation between verified code and aspirational work.

---

## Long-Term Vision

Digital infrastructure deserves time that is **interpretable** across cultures
and calendars without ambiguity, **contextualizable** against physical and
atomic reference scales, **verifiable** offline by any party without trusting a
single server, and **provable** through post-quantum cryptographic evidence
audited in the open.

*Gerarion Time* moves toward that vision one verified artifact at a time: **no
checkbox in this document is ever marked `[x]` without reproducible evidence in
the repository.**
