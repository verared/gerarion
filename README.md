# Gerarion Time

**Open, modular, offline-first and verifiable time infrastructure: a regular calendar, a continuous atomic scale and hybrid post-quantum timestamp evidence.**

[![CI](https://github.com/verared/gerarion/actions/workflows/ci.yml/badge.svg)](https://github.com/verared/gerarion/actions/workflows/ci.yml)
[![CodeQL](https://github.com/verared/gerarion/actions/workflows/codeql.yml/badge.svg)](https://github.com/verared/gerarion/actions/workflows/codeql.yml)
![License: MIT OR Apache-2.0](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue)
![Version v3.4.0](https://img.shields.io/badge/version-v3.4.0-green)
![REUSE 3.3](https://img.shields.io/badge/REUSE-3.3%20compliant-brightgreen)

**English** · [Español](README.es.md) — in case of divergence, the English text prevails (EN > ES).

---

## 2. Project status

Release target **`v3.4.0`** on the frozen specification **`GUS v3.0.0`**.

| Axis | Status | Scope |
|---|---|---|
| **1. Specification & arithmetic** (`GUS v3.0.0` + 10 calendars) | **Frozen & verified** | Integer arithmetic (`TCJ = TAI + 8,400 s`), checked bit for bit across Python, JavaScript and C11 against `vectors/*.json`. |
| **2. Reference implementations** (`v3.4.0`) | **Stable & CI-tested** | `gt-core`, `gt-gus`, `gt-tcj`, `gt-calendar`, `gt-gts` (core), `gt-gst` (reference), `gt-interop` (RFC 3339 / ISO 8601 / Unix). |
| **3. Production cryptographic assurance** | **Pending** | `gt-gst` has no independent external cryptographic audit and no `TPM` / `HSM` key custody yet. |

> **Do not use yet in critical production security decisions:**
> `gt-gst` and the Merkle notary (no external audit, no hardware key custody),
> and the **experimental** profiles `gt-tslr`, `gt-gcerts`, Roughtime (`gt-gts`)
> and RFC 3161 (`gt-interop`). `gt-tslr` and `gt-gcerts` are specification +
> scaffold only (no reference implementation). See [SECURITY.md](SECURITY.md)
> and [ROADMAP.md](ROADMAP.md).

## 3. What it is and what it is not

**It is:**

- A modular, deterministic, offline-first temporal infrastructure: a regular 12×30 calendar, the continuous scale `TCJ = TAI + 8,400 s`, 10-calendar translation and hybrid (Ed25519 + ML-DSA) timestamp envelopes.
- A way to turn time into a verifiable dimension (provenance, integrity, freshness, uncertainty) for Zero Trust architectures ([Zero Trust time architecture](docs/architecture/ZERO-TRUST-TIME.en.md)).
- Three independent implementations (C11, Python, JavaScript) bound by one normative CC0 vector set.
- Split into nine satellite repositories that can be adopted one by one.

**It is not:**

- A replacement for UTC, TAI, NTP, PTP or the operating-system clock; it complements them.
- A substitute for Zero Trust access control, per-operation authorization, hardware key custody (`TPM` / `HSM`) or controller security; it complements them.
- A blockchain, nor a physical-clock certificate: without an authenticated `gt-gts` reading, the time inside an envelope is only an assertion by its signer.

## 4. Try it online

**<https://verared.github.io/gerarion/>** — the date translator runs entirely in your browser (ten calendars, shareable links, live GUS clock, month calendar and interval calculator). No server calls, cookies or accounts, and it keeps working offline once loaded.

## 5. Minimal example (1 minute)

### Integrate `gt-core` + `gt-gst` in 1 Minute (CMS / API Quickstart)

Requires `cryptography>=47` (extra `gst`). Full guide: [docs/guides/CMS-INTEGRATION.en.md](docs/guides/CMS-INTEGRATION.en.md).

```python
import hashlib
from gerarion.core import format as fmt
from gerarion.gst import HybridSigner, v2

# 1. Hybrid signer (Ed25519 + ML-DSA-65), key trust registry and SQLite ReplayStore
signer = HybridSigner(seed_classical=bytes(range(32)), seed_pqc=bytes(range(32, 64)))
registry = v2.KeyRegistry()
registry.register_signer(issuer="cms.example.org", kid="cms-2026-k1", signer=signer)
replay_store = v2.SQLiteReplayStore(":memory:")  # in production: "/var/lib/cms/gst_replay.sqlite3"

# 2. Seal a business event on a canonical GUS coordinate
event_bytes = b'{"action":"post.publish","object_id":"art-42","version":1}'
event_hash = "sha256:" + hashlib.sha256(event_bytes).hexdigest()
envelope = v2.create(
    fmt.parse("2031DY-03-08-T-09:30:00-SC-TCJ+0"),
    signer,
    event_hash=event_hash,
    issuer="cms.example.org",
    kid="cms-2026-k1",
    seq=1,
)

# 3. Verify across 3 independent levels (cryptography, identity/replay, temporal assurance)
res = v2.verify(envelope, expected_event_hash=event_hash, trust_store=registry, replay_store=replay_store)
assert res.crypto.valid is True
assert res.identity.valid is True and res.identity.key_status == "ACTIVE"
assert res.identity.replay_status == "OK"
assert res.temporal.clock_state == "UNKNOWN"  # "VERIFIED" only with an authenticated gt-gts reading
assert res.sealed and not res.overall_trusted  # no verified temporal anchor
print("crypto   :", res.crypto.valid, res.crypto.algorithm)
print("identity :", res.identity.valid, res.identity.key_status, res.identity.replay_status)
print("temporal :", res.temporal.clock_state)
print("overall_trusted:", res.overall_trusted)

# 4. The same envelope again is rejected (atomic anti-replay)
again = v2.verify(envelope, expected_event_hash=event_hash, trust_store=registry, replay_store=replay_store)
print("replay   :", again.identity.replay_status, again.overall_trusted)
```

Expected output:

```text
crypto   : True HYBRID-ED25519-ML-DSA-65
identity : True ACTIVE OK
temporal : UNKNOWN
overall_trusted: False
replay   : REPLAY False
```

## 6. Installation

**Whole ecosystem** (no PyPI, no npm, no external registry):

```bash
# Python >= 3.9 (kernel is stdlib-only; the `gst` extra adds cryptography>=47)
pip install "gerarion[gst] @ git+https://github.com/verared/gerarion.git@v3.4.0"

# C11 (no dependencies, zero-malloc core) — builds the libraries, CLI and conformance suite
make -C impl-c            # pkg-config files: gerarion.pc, gerarion-core.pc, gerarion-clock.pc, gerarion-calendars.pc

# JavaScript / ESM (zero dependencies): import web/gerarion.mjs, or the npm tarball from the GitHub Release
```

**Only the satellites you need** — each satellite repository keeps the monorepo's relative paths, so they combine by copying their trees:

```bash
# Run after the v3.4.0 satellite synchronization (Phase B).
git clone --branch v3.4.0 --depth 1 https://github.com/verared/gt-core.git
git clone --branch v3.4.0 --depth 1 https://github.com/verared/gt-gst.git
```

**Verify a satellite** (from a checkout of this repository):

```bash
python3 tools/export_module.py --verify-existing /path/to/gt-core
# with detached-signature authenticity, when the satellite ships EXPORT-MANIFEST.json.sig:
python3 tools/export_module.py --verify-existing /path/to/gt-core --trusted-pub-key /path/to/release-pub.pem
```

Without `--trusted-pub-key`, authenticity is reported as `SKIPPED`: only integrity was checked. The published `v3.3.0` satellites do not ship a `.sig` yet (signing in CI is tracked in [ROADMAP.md](ROADMAP.md)).

| # | Distribution guarantee | Mechanism |
|---|---|---|
| 1 | SHA-256 integrity | `files` map of `EXPORT-MANIFEST.json` |
| 2 | Declared provenance | `source_repo`, `source_tag`, `source_commit` |
| 3 | Publication authenticity | Detached Ed25519 `EXPORT-MANIFEST.json.sig` (`--trusted-pub-key`) |
| 4 | Reproducibility | Bit-for-bit re-export from the same commit |
| 5 | Functional conformance | Normative vectors + cross-satellite tests in C11, Python and JS |

GitHub Releases attach the wheel, sdist, JS tarball, C libraries and `SHA256SUMS.txt` (`sha256sum -c SHA256SUMS.txt`). Details: [COMPATIBILITY.md](COMPATIBILITY.md).

## 7. Ecosystem layers and satellite repositories

Version matrix and dependency contract: [COMPATIBILITY.md](COMPATIBILITY.md). Direction of travel (no dates, no promises): [ROADMAP.md](ROADMAP.md) · [ROADMAP.es.md](ROADMAP.es.md).

| Satellite | Responsibility | Maturity (`v3.4.0`) |
|---|---|---|
| [`gt-core`](https://github.com/verared/gt-core) | TCJ + GUS core: zero-malloc C11, Python, JS | Stable |
| [`gt-gus`](https://github.com/verared/gt-gus) | Canonical 29/32-character syntax, `quick_verify` | Stable |
| [`gt-tcj`](https://github.com/verared/gt-tcj) | `TCJ = TAI + 8,400 s`, versioned TAI−UTC bridge (`IERS-C-2026.1`) | Stable |
| [`gt-calendar`](https://github.com/verared/gt-calendar) | `AY`/`DY` calendar + translation across 10 systems | Stable |
| [`gt-gts`](https://github.com/verared/gt-gts) | Clock trust state machine, anti-rollback anchors | Stable core · Roughtime **experimental** |
| [`gt-gst`](https://github.com/verared/gt-gst) | `GST v2` envelopes, `KeyRegistry`, `ReplayStore`, Merkle notary | Stable reference · **external audit pending** |
| [`gt-interop`](https://github.com/verared/gt-interop) | RFC 3339 / ISO 8601 / Unix bridges | Stable · RFC 3161 **experimental** |
| [`gt-tslr`](https://github.com/verared/gt-tslr) | True Local Solar Time profile | **Experimental** (spec + scaffold) |
| [`gt-gcerts`](https://github.com/verared/gt-gcerts) | Certificate validity profiles | **Experimental** (spec + scaffold) |

## 8. Conformance and tests

The normative vectors in [`vectors/`](vectors/README.md) (CC0) are the single source of conformance truth: `gus-normative-003.json`, `gus-quickverify-001.json`, `gus-regression-001.json`, `gus-3339-*.json` (positive and negative) and `guti-calendars-001.json` (63,850 calendar cases).

```bash
# C11: conformance against all vectors + ASan/UBSan stress audit (6.5M+ checks)
make -C impl-c conformance
make -C impl-c audit

# Python (add `pip install -e .[dev,pqc]` for the GST v2 tests)
PYTHONPATH=src python3 -m pytest tests/

# JavaScript: the six runners
node web/test/tests.mjs
node web/test/conformance.mjs
node web/test/profiles-conformance.mjs
node web/test/regression-conformance.mjs
node web/test/calendars.test.mjs
node tests/atlas.test.mjs

# Satellites: export, verify and run assembled-satellite integration (C11 + Python + JS)
python3 tools/export_module.py --all --out /tmp/satellites --verify
PYTHONPATH=src python3 -m pytest tests/test_export_module.py tests/test_satellite_integration.py

# Licensing
python3 -m reuse lint
```

**Validating an independent implementation:** read the executable clause in [docs/CONFORMANCE.md](docs/CONFORMANCE.md), load the JSON vectors from your own language, and compare every field. Any divergence on a normative vector is a bug in your implementation; negative vectors must be rejected.

## 9. Security

- Normative profile `GST v2`: hybrid **Ed25519 + ML-DSA** over **RFC 8785 (JCS)**, domain `GUS3-GST-V2`, anti-downgrade descriptor inside the signed bytes. `WOTS+` and the `GST v1` API are legacy (`src/gerarion/deprecated/hashots.py`).
- `gerarion.gst.v2.verify` requires the externally computed `expected_event_hash`. `sealed` means valid signatures, event binding and issuer policy; `anchored` and `overall_trusted` additionally require a `VERIFIED` clock and a host policy callback validating independent temporal evidence bound to the exact GST envelope. A clock reading alone is not an anchor.
- Integrators must supply a `KeyRegistry` and a transactional `ReplayStore` (both fail-closed).
- Known limits: independent external cryptographic audit and `TPM` / `HSM` key custody are still pending; an attacker with `root` on the signing host is not mitigated.

Read [SECURITY.md](SECURITY.md) (including responsible disclosure) and the [threat model](docs/en/threat-model.md).

## 10. Documentation and specifications

| Topic | Where |
|---|---|
| Domain specifications | [`docs/specs/`](docs/specs/GUS.en.md): [TCJ](docs/specs/TCJ.en.md) · [GUS](docs/specs/GUS.en.md) · [CALENDAR](docs/specs/CALENDAR.en.md) · [GTS](docs/specs/GTS.en.md) · [GST](docs/specs/GST.en.md) · [INTEROP](docs/specs/INTEROP.en.md) · [TSLR](docs/specs/TSLR.en.md) · [GCERTS](docs/specs/GCERTS.en.md) |
| Consolidated normative edition | [docs/en/gus-3.0.0.md](docs/en/gus-3.0.0.md) |
| Integration guide (external CMS / API, `GEIACT-1` checklist) | [docs/guides/CMS-INTEGRATION.en.md](docs/guides/CMS-INTEGRATION.en.md) |
| Satellite architecture | [docs/architecture/SATELLITE-REPOS.en.md](docs/architecture/SATELLITE-REPOS.en.md) |
| Zero Trust time architecture | [docs/architecture/ZERO-TRUST-TIME.en.md](docs/architecture/ZERO-TRUST-TIME.en.md) |
| Version contract | [COMPATIBILITY.md](COMPATIBILITY.md) |
| Roadmap | [ROADMAP.md](ROADMAP.md) · [ROADMAP.es.md](ROADMAP.es.md) |
| Threat model / security policy | [docs/en/threat-model.md](docs/en/threat-model.md) · [SECURITY.md](SECURITY.md) |

**Normative precedence:** every specification exists in English and Spanish; in case of divergence the **English version prevails (EN > ES)**.

## 11. Related work

Gerarion complements, and does not compete with, existing time standards:

- **UTC / TAI:** `TCJ = TAI + 8,400 s` is a mathematical offset on the atomic scale; the TAI−UTC bridge is versioned and flags extrapolation past its validity horizon.
- **ISO 8601 / RFC 3339:** treated as input/output formats through `gt-interop`; they never replace the GUS coordinate.
- **NTP / NTS / PTP / Roughtime:** physical synchronization stays with them; `gt-gts` classifies readings (`VERIFIED`, `HOLDOVER`, `UNVERIFIED`, `REJECTED`) and detects rollback. The Roughtime profile is experimental.
- **RFC 3161 (TSA):** an external timestamp authority can countersign a canonical envelope (experimental profile).
- **ICU / civil calendars:** the 10-calendar engine is deterministic integer arithmetic, independent of ICU, with documented range and tolerance limits.
- **Calendar design precedents:** the 12×30 Egyptian and French Republican calendars, Symmetry454, Hanke-Henry and Pax. Because 364 and 371 are multiples of 7, the Tempalum adds whole weeks and never orphan days.

## 12. Contributing, governance and license

- **Single source of truth:** `verared/gerarion` is the only place where code is edited; the nine `verared/gt-*` satellites are generated from a tagged commit and must never be hand-edited ([architecture](docs/architecture/SATELLITE-REPOS.en.md)).
- [CONTRIBUTING.md](CONTRIBUTING.md) · [GOVERNANCE.md](GOVERNANCE.md) · [SECURITY.md](SECURITY.md).
- **Licenses:** code `MIT OR Apache-2.0`; documentation `CC-BY-4.0`; test vectors `CC0-1.0`; fonts `OFL-1.1`. The repository is **REUSE 3.3** compliant (`python3 -m reuse lint`). See [LICENSING.md](LICENSING.md), [NOTICE](NOTICE) and [sbom.cdx.json](sbom.cdx.json).

## 13. How to cite

```bibtex
@software{gerarion_time_2026,
  author  = {{verared} and Loyola, Gerardo},
  title   = {Gerarion Time: Gerarion Universal Standard (GUS 3.0.0) reference suite},
  year    = {2026},
  version = {3.4.0},
  url     = {https://github.com/verared/gerarion},
  license = {MIT OR Apache-2.0}
}
```

Machine-readable metadata: [CITATION.cff](CITATION.cff).
