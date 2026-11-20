# Verifiable Time Infrastructure for Zero Trust Architectures

Version: 1.0.0 · Baseline: `v3.3.0` (`GUS v3.0.0`) · License: CC-BY-4.0 ·
Maintained by: verared contributors

**English** · [Español](ZERO-TRUST-TIME.es.md) — in case of divergence, the English text prevails (EN > ES).

> **Scope and honesty boundary.**
> *Gerarion Time* **complements** Zero Trust architectures; it **does not replace**
> access control, per-operation authorization, network authentication, hardware
> key custody (`TPM` / `HSM`), or controller/actuator security.
> The profiles `Gerarion Lite`, `Gerarion Trusted`, and `Gerarion Full` defined
> below are **conceptual deployment and modular composition profiles** over the
> existing nine satellite repositories — **not** new products or additional
> repositories. `gt-tslr` and `gt-gcerts` remain **`EXPERIMENTAL`**
> (specification + scaffold only, with no reference implementation or operational
> guarantee). See [`SECURITY.md`](../../SECURITY.md) and
> [`docs/en/threat-model.md`](../en/threat-model.md).

---

## 1. Guiding Principle

> **No event is considered temporally trustworthy merely because it carries a date; its provenance, integrity, freshness, uncertainty, and authorization must be verifiable under explicit policy.**

In conventional distributed systems, a timestamp is treated as a passive metadata
field: a string or integer attached to a request, log entry, or command and
accepted at face value. Under Zero Trust, where neither the network nor the peer
clock is implicitly trusted, that assumption is a structural gap.

*Gerarion Time* reframes time as a **verifiable operational dimension** alongside
identity, message integrity, and freshness. Rather than collapsing everything
into a single boolean "valid timestamp", the reference verifier
(`gerarion.gst.v2.verify`, baseline `v3.3.0`) separates verification into
**three independent levels** (`VerificationResult`):

| Level | Field (`v3.3.0`) | What it verifies | What it does **not** prove on its own |
|---|---|---|---|
| **Level 1 — Cryptography** | `result.crypto` | Deterministic RFC 8785 (JCS) canonicalization, `GUS3-GST-V2` domain separation, anti-downgrade algorithm descriptor, and hybrid **Ed25519 + ML-DSA** signature validity. | Whether the signing key is authorized or whether the envelope was replayed. |
| **Level 2 — Identity & freshness** | `result.identity` | Key authorization, validity window, and revocation status in `KeyRegistry`, plus atomic anti-replay and monotonic sequence checking in a transactional `ReplayStore` (`SQLiteReplayStore`), both fail-closed. | Whether the physical clock of the signing host was synchronized or accurate. |
| **Level 3 — Temporal provenance** | `result.temporal` | Clock trust state (`VERIFIED`, `HOLDOVER`, `UNVERIFIED`, `REJECTED`) and explicit uncertainty bounds supplied by an authenticated `gt-gts` reading (`UNKNOWN` by default when omitted). | Physical resistance against GNSS/PTP/NTP jamming or a `root` attacker on the host. |

By design, `result.overall_trusted` covers **Level 1 + Level 2 only** and **never**
certifies physical clock accuracy; policies that require bounded physical time
must additionally inspect `result.temporal.clock_state` and uncertainty bounds.

---

## 2. Threat Matrix and Real Limits (7 Vectors)

The table below states what *Gerarion Time* contributes against seven common
temporal and evidentiary attack vectors and where its guarantees stop.

| # | Attack | What Gerarion provides | Explicit limit |
|---|---|---|---|
| 1 | **Message replay** | `gt-gst` (`GST v2`) + transactional `ReplayStore` (`SQLiteReplayStore` in `WAL` + `BEGIN IMMEDIATE` mode) reject duplicate envelopes and sequence rollbacks fail-closed. | Depends on correct persistence, durability, and atomic deployment of the `ReplayStore` across replicas. |
| 2 | **Timestamp tampering** | Hybrid **Ed25519 + ML-DSA** signature over RFC 8785 (JCS) binds the canonical GUS coordinate, `event_hash`, issuer, `kid`, and `seq` into one tamper-evident envelope. | Does not prove by itself that the originating host's clock was truthful at signing time. |
| 3 | **Clock rollback** | `gt-gts` trust state machine and persistent sub-second `(instant, nanos)` anti-rollback anchors detect backward jumps and transition out of `VERIFIED`. | Depends on protecting the anchor storage and external time sources; a `root` attacker without hardware protection can wipe or alter local anchors. |
| 4 | **Device / issuer spoofing** | `KeyRegistry` (`TrustedKeyRecord`) enforces explicit issuer-to-key binding, constant-time key verification, historical rotation windows, expiration, and revocation. | A stolen private key remains critical until revoked; software keys do not substitute for hardware custody (`TPM` / `HSM`). |
| 5 | **Log alteration** | Per-event SHA-256 hashes, `GST v2` signatures, and optional daily Merkle notary roots make post-anchoring edits or deletions detectable offline. | Does not prevent a compromised producer from dropping or suppressing events **before** they are signed or anchored. |
| 6 | **Temporal desynchronization** | `gt-gts` exposes explicit `HOLDOVER` and `UNVERIFIED` states together with declared uncertainty bounds instead of failing silently to an unverified wall clock. | Does not prevent physical radio or network interference against GNSS, PTP, or NTP feeds. |
| 7 | **Evidence forgery** | `GST v2` envelopes and independent offline verification (`tools/verify_gus.py`, `gerarion.gst.v2.verify`) allow third parties to validate integrity and provenance without trusting a single server. | Still depends on trustworthy issuers, independent witnesses/notaries, and an external cryptographic audit (pending before critical production use). |

---

## 3. Common Language Across the 9 Satellites

All nine repositories under `verared/gt-*` share one frozen coordinate model
(`GUS v3.0.0`, `TCJ = TAI + 8,400 s`) and map to distinct responsibilities inside
a Zero Trust temporal stack. See [`SATELLITE-REPOS.en.md`](SATELLITE-REPOS.en.md)
and [`COMPATIBILITY.md`](../../COMPATIBILITY.md) for dependency rules.

| Satellite | Role in a Zero Trust temporal architecture | Maturity (`v3.3.0`) |
|---|---|---|
| [`verared/gt-core`](https://github.com/verared/gt-core) | Deterministic, zero-malloc TCJ + GUS integer kernel (C11, Python, JS) for uniform event coordinates from MCUs to servers. | Stable / Verified |
| [`verared/gt-gus`](https://github.com/verared/gt-gus) | Canonical 29/32-character syntax, normalization rules 1–7, and `quick_verify` to reject malformed timestamps at ingress. | Stable / Verified |
| [`verared/gt-tcj`](https://github.com/verared/gt-tcj) | Monotonic atomic scale (`TCJ = TAI + 8,400 s`) and versioned `TAI−UTC` bridge (`IERS-C-2026.1`) with explicit horizon flagging. | Stable / Verified |
| [`verared/gt-calendar`](https://github.com/verared/gt-calendar) | Deterministic 10-calendar translation (`AY`/`DY` + GUTI-1) for unambiguous human and cross-regional audit presentation. | Stable / Verified |
| [`verared/gt-gts`](https://github.com/verared/gt-gts) | Clock trust state machine (`VERIFIED`/`HOLDOVER`/`UNVERIFIED`/`REJECTED`) and sub-second anti-rollback anchors feeding Level 3 policy decisions. | Stable core · Roughtime **experimental** |
| [`verared/gt-gst`](https://github.com/verared/gt-gst) | Hybrid `GST v2` envelopes, `KeyRegistry`, transactional `ReplayStore`, and optional daily Merkle notary feeding Levels 1–2 and offline auditability. | Stable reference · **external audit & TPM/HSM pending** |
| [`verared/gt-interop`](https://github.com/verared/gt-interop) | Strict boundary bridges (`RFC 3339`, `ISO 8601`, `Unix`) with shared negative vectors, keeping legacy formats at the perimeter. | Stable (`RFC 3339`/`ISO`/`Unix`) · `RFC 3161` **experimental** |
| [`verared/gt-tslr`](https://github.com/verared/gt-tslr) | Future optional physical/solar cross-check context (*True Local Solar Time*). | **`EXPERIMENTAL`** — specification + scaffold only; **not operational** |
| [`verared/gt-gcerts`](https://github.com/verared/gt-gcerts) | Future TCJ-based certificate validity window semantics under clock trust states. | **`EXPERIMENTAL`** — specification + scaffold only; **not operational** |

---

## 4. Conceptual Gradual Adoption Profiles (Not New Repositories)

Zero Trust deployments span constrained microcontrollers, edge gateways, and
multi-entity critical infrastructure. Rather than forcing every node to run
post-quantum cryptography, *Gerarion Time* defines **three conceptual deployment
profiles** assembled strictly from the existing satellites above. They are
**composition guides, not new products or repositories**.

| Profile | Composition (existing satellites & controls) | Target environment | Declared guarantees |
|---|---|---|---|
| **Gerarion Lite** | `gt-core` + `gt-gus` + `gt-tcj` | Constrained embedded devices, MCUs, bare-metal sensors. | Canonical, leap-second-free TCJ/GUS representation and deterministic zero-malloc integer arithmetic with **no cryptographic overhead** (relies on upstream gateway for signing and replay checks). |
| **Gerarion Trusted** | **Lite** + `gt-gts` + `gt-gst` (`KeyRegistry` + transactional `ReplayStore`) | Gateways, APIs, microservices, CMS/audit backends, edge nodes. | Evaluates signature validity (`crypto`), key authorization and atomic anti-replay (`identity`), and explicit clock trust state (`temporal`) before executing or accepting operations. |
| **Gerarion Full** | **Trusted** + daily Merkle notary + multi-entity trust policies + independent offline auditing + `gt-interop` boundary controls + external hardware custody (`TPM` / `HSM`) | Critical infrastructure, distributed traceability, industrial OT/IoT, multi-agent workflows. | Adds cross-entity verifiability, Merkle anchoring of logs, strict perimeter bridges, and hardware-backed key protection (requires external cryptographic audit and hardware custody integration before critical production use). |

> **Core composition rule:** *Security does not require every device to support everything; it requires every device to declare explicitly which profile and guarantees it provides.*

A `Gerarion Lite` sensor MUST NOT be treated as cryptographically authenticated
merely because it emits a valid GUS string; the receiving `Gerarion Trusted`
gateway enforces the trust boundary and records the origin profile explicitly.

---

## 5. Reference Scenario and Quantitative Validation Protocol (A/B Experiment)

### 5.1 Reference scenario: industrial / IoT gateway

Consider an industrial edge gateway mediating actuation commands (for example,
*"open valve V-14"*) between a remote controller and a field bus:

1. **Ingress syntax gate (`gt-gus`):** The command's canonical GUS coordinate is
   validated with `quick_verify`; malformed or non-canonical coordinates are
   dropped immediately.
2. **Cryptographic & identity verification (`gt-gst` + `KeyRegistry` + `ReplayStore`):**
   A captured and replayed `"open valve V-14"` envelope arrives five minutes
   later. Even though the signature mathematically validates (`crypto.valid == True`),
   the transactional `SQLiteReplayStore` detects the repeated `(issuer, seq)` /
   envelope digest and fails closed (`identity.replay_status == "REPLAY"`,
   `overall_trusted == False`). The valve actuation is blocked.
3. **Clock trust & rollback check (`gt-gts`):** If the gateway's local clock has
   been pushed backward or lost authenticated synchronization, `gt-gts` reports
   `REJECTED`, `HOLDOVER`, or `UNVERIFIED`, allowing policy to deny high-risk
   actuations instead of trusting a silent wall-clock fallback.
4. **Evidence preservation:** The rejected replay envelope, its verification
   result, and the gateway's own `gt-gts` state are logged as tamper-evident
   incident evidence rather than silently discarded.

**External Zero Trust controls still required:** *Gerarion Time* does **not**
replace mutual network authentication (mTLS/IPsec), fine-grained per-operation
authorization (RBAC/ABAC deciding *whether* an issuer is allowed to open V-14),
hardware key storage (`TPM`/`HSM`), physical network segmentation, or safety
interlocks on the PLC/actuator itself.

### 5.2 Comparative adversarial benchmark (A/B protocol)

To evaluate these claims quantitatively — rather than by assertion — the roadmap
([`ROADMAP.md`](../../ROADMAP.md)) tracks an **independent comparative A/B
adversarial benchmark** to be built in a **future external repository**:

- **Systems under test:** Two functionally identical edge gateways handling the
  same workload and command schema:
  - **Baseline (A):** Conventional wall-clock timestamp validation (RFC 3339 /
    Unix epoch + tolerance window, without `GST v2`, `KeyRegistry`,
    transactional `ReplayStore`, or `gt-gts` anti-rollback anchors).
  - **Treatment (B):** **Gerarion Trusted** profile (`gt-core` + `gt-gus` +
    `gt-gts` + `gt-gst` with `KeyRegistry` and `SQLiteReplayStore` in
    fail-closed mode).
- **Controlled fault and attack scenarios:**
  1. Valid command capture and **replay** (immediate, delayed, and concurrent
     multi-threaded bursts).
  2. **Clock manipulation** (backward step, sub-second rollback, forward drift
     beyond holdover).
  3. **Event forgery and key misuse** (tampered payload/timestamp, unknown key,
     expired/revoked key, algorithm downgrade attempt).
  4. **Malicious restart / crash-recovery** (forced process restart to test
     persistence of `ReplayStore` and `gt-gts` anti-rollback anchors).
- **Primary metrics to publish reproducibly:**
  - **Fraudulent-operation rejection rate** (per attack class).
  - **False-positive rate** on legitimate traffic under nominal and degraded
    (`HOLDOVER`) conditions.
  - **End-to-end verification latency** (p50 / p95 / p99 overhead of hybrid
    verification + transactional replay check).
  - **Service availability** during clock degradation, holdover, and recovery.

---

## 6. Related References

- [`SECURITY.md`](../../SECURITY.md) — Current security policy, normative `GST v2` profile, and responsible disclosure.
- [`docs/en/threat-model.md`](../en/threat-model.md) — Detailed threat model (`v3.3.0`).
- [`docs/architecture/SATELLITE-REPOS.en.md`](SATELLITE-REPOS.en.md) — Satellite export model and dependency graph.
- [`docs/guides/CMS-INTEGRATION.en.md`](../guides/CMS-INTEGRATION.en.md) — Concrete integration pattern (`KeyRegistry` + `SQLiteReplayStore` + `GEIACT-1` checklist).
- [`ROADMAP.md`](../../ROADMAP.md) — Verifiable vision and open engineering tracks.
