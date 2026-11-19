# Gerarion Time — Compatibility & Version Matrix (`v3.3.0`)

This document defines the official version contract between the monorepo
source of truth (`verared/gerarion`) and the nine standalone satellite
repositories (`verared/gt-*`). Machine-readable equivalent:
[`compatibility.json`](compatibility.json).

- **Suite release:** `3.3.0` (tag `v3.3.0`)
- **Frozen normative specification:** `GUS v3.0.0` (arithmetic and `vectors/*.json` frozen)
- **Semantic compatibility range:** `>=3.2.0,<4.0.0`

## Satellite Compatibility Matrix

| Satellite | Repository | Release | Compatible range | Maturity | Dependencies |
|---|---|---|---|---|---|
| `gt-core` | `verared/gt-core` | `3.3.0` | `>=3.2.0,<4.0.0` | `stable` | *(none — 100 % standalone)* |
| `gt-gus` | `verared/gt-gus` | `3.3.0` | `>=3.2.0,<4.0.0` | `stable` | *(none — 100 % standalone)* |
| `gt-tcj` | `verared/gt-tcj` | `3.3.0` | `>=3.2.0,<4.0.0` | `stable` | `gt-core` (`>=3.2.0,<4.0.0`) |
| `gt-calendar` | `verared/gt-calendar` | `3.3.0` | `>=3.2.0,<4.0.0` | `stable` | `gt-core` (`>=3.2.0,<4.0.0`) |
| `gt-gts` | `verared/gt-gts` | `3.3.0` | `>=3.2.0,<4.0.0` | `stable-core/experimental-roughtime` | `gt-core` (`>=3.2.0,<4.0.0`) |
| `gt-gst` | `verared/gt-gst` | `3.3.0` | `>=3.2.0,<4.0.0` | `stable` *(external crypto audit + TPM/HSM required for production)* | `gt-core` (`>=3.2.0,<4.0.0`) |
| `gt-interop` | `verared/gt-interop` | `3.3.0` | `>=3.2.0,<4.0.0` | `stable` *(RFC 3339 stable; RFC 3161 experimental)* | `gt-core` (`>=3.2.0,<4.0.0`), `gt-tcj` (`>=3.2.0,<4.0.0`) |
| `gt-tslr` | `verared/gt-tslr` | `3.3.0` | `>=3.2.0,<4.0.0` | `experimental` *(spec + scaffold only)* | `gt-core` (`>=3.2.0,<4.0.0`) |
| `gt-gcerts` | `verared/gt-gcerts` | `3.3.0` | `>=3.2.0,<4.0.0` | `experimental` *(spec + scaffold only)* | `gt-core` (`>=3.2.0,<4.0.0`), `gt-gst` (`>=3.2.0,<4.0.0`) |

## Three-Axis Maturity Contract

1. **Specification & arithmetic (`GUS v3.0.0` + 10 calendars):** Frozen and
   verified bit-for-bit across Python, JavaScript, and C11.
2. **Reference implementations (`v3.3.0`):** Stable and continuously verified
   in CI (`gt-core`, `gt-gus`, `gt-tcj`, `gt-calendar`, `gt-gts`, `gt-gst`,
   `gt-interop`). `gt-tslr` and `gt-gcerts` remain **EXPERIMENTAL**
   (specification + scaffold, no reference implementation).
3. **Production cryptographic assurance:** `gt-gst` (`GST v2`: hybrid
   Ed25519 + ML-DSA over RFC 8785 JCS, domain `GUS3-GST-V2`, anti-downgrade,
   `KeyRegistry`, fail-closed `SQLiteReplayStore` / `ReplayGuard`) and the
   daily Merkle notary require an independent third-party cryptographic audit
   and hardware key custody (TPM/HSM) before production security decisions.
   Legacy `WOTS+` (`src/gerarion/deprecated/hashots.py`) is deprecated and
   outside `GST v2`.

## The 5 Official Distribution Guarantees

| # | Guarantee | What it proves | How it is verified |
|---|---|---|---|
| 1 | **SHA-256 Integrity** | Every exported file matches the exact SHA-256 recorded in `EXPORT-MANIFEST.json`, with zero missing or extraneous files. | `python3 tools/export_module.py --verify-existing <dir>` |
| 2 | **Declared Provenance** | The satellite declares its exact `source_repo` (`verared/gerarion`), `source_tag` (`v3.3.0`), and 40-char `source_commit`. | Inspecting `EXPORT-MANIFEST.json` against `git rev-parse v3.3.0^{commit}` |
| 3 | **Publication Authenticity** | Detached Ed25519 signature `EXPORT-MANIFEST.json.sig` (or release attestation) proves the manifest was signed by the release key without self-reference. | `python3 tools/export_module.py --verify-existing <dir> --trusted-pub-key <pub.pem>` |
| 4 | **Reproducibility** | Re-running `export_module.py` from the same `--source-commit` produces a bit-for-bit identical tree and manifest. | `pytest tests/test_satellite_integration.py` |
| 5 | **Functional Conformance** | Assembled satellites compile and pass normative and cross-domain integration tests in C11, Python, and JavaScript. | `pytest tests/test_satellite_integration.py` & CI `satellites` job |

## Verification Contract (`EXPORT-MANIFEST.json` & `EXPORT-MANIFEST.json.sig`)

Every exported satellite includes an `EXPORT-MANIFEST.json` at its root
(`schema: "gerarion-export-manifest/1"`). When signed with `--sign-key <pem>`
(or `GERARION_MANIFEST_SIGNING_KEY`), a detached `EXPORT-MANIFEST.json.sig`
(`schema: "gerarion-manifest-sig/1"`, `algorithm: "Ed25519"`) is written
alongside it without ever being included inside `EXPORT-MANIFEST.json["files"]`.

To verify any exported satellite directory offline:

```bash
# Integrity + REUSE 3.3 + C11 core smoke (authenticity reported as SKIPPED):
python3 tools/export_module.py --verify-existing /path/to/gt-<module>

# Full verification including detached Ed25519 signature authenticity:
python3 tools/export_module.py --verify-existing /path/to/gt-<module> --trusted-pub-key /path/to/release-pub.pem
```
