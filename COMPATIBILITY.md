# Gerarion Time — Compatibility & Version Matrix (`v3.2.2`)

This document defines the official version contract between the monorepo
source of truth (`verared/gerarion`) and the nine standalone satellite
repositories (`verared/gt-*`). Machine-readable equivalent:
[`compatibility.json`](compatibility.json).

- **Suite release:** `3.2.2` (tag `v3.2.2`)
- **Frozen normative specification:** `GUS v3.0.0` (arithmetic and `vectors/*.json` frozen)
- **Semantic compatibility range:** `>=3.2.0,<4.0.0`

## Satellite Compatibility Matrix

| Satellite | Repository | Release | Compatible range | Maturity | Dependencies |
|---|---|---|---|---|---|
| `gt-core` | `verared/gt-core` | `3.2.2` | `>=3.2.0,<4.0.0` | `stable` | *(none — 100 % standalone)* |
| `gt-gus` | `verared/gt-gus` | `3.2.2` | `>=3.2.0,<4.0.0` | `stable` | *(none — 100 % standalone)* |
| `gt-tcj` | `verared/gt-tcj` | `3.2.2` | `>=3.2.0,<4.0.0` | `stable` | `gt-core` (`>=3.2.0,<4.0.0`) |
| `gt-calendar` | `verared/gt-calendar` | `3.2.2` | `>=3.2.0,<4.0.0` | `stable` | `gt-core` (`>=3.2.0,<4.0.0`) |
| `gt-gts` | `verared/gt-gts` | `3.2.2` | `>=3.2.0,<4.0.0` | `stable-core/experimental-roughtime` | `gt-core` (`>=3.2.0,<4.0.0`) |
| `gt-gst` | `verared/gt-gst` | `3.2.2` | `>=3.2.0,<4.0.0` | `stable` *(external crypto audit + TPM/HSM required for production)* | `gt-core` (`>=3.2.0,<4.0.0`) |
| `gt-interop` | `verared/gt-interop` | `3.2.2` | `>=3.2.0,<4.0.0` | `stable` *(RFC 3339 stable; RFC 3161 experimental)* | `gt-core` (`>=3.2.0,<4.0.0`), `gt-tcj` (`>=3.2.0,<4.0.0`) |
| `gt-tslr` | `verared/gt-tslr` | `3.2.2` | `>=3.2.0,<4.0.0` | `experimental` *(spec + scaffold only)* | `gt-core` (`>=3.2.0,<4.0.0`) |
| `gt-gcerts` | `verared/gt-gcerts` | `3.2.2` | `>=3.2.0,<4.0.0` | `experimental` *(spec + scaffold only)* | `gt-core` (`>=3.2.0,<4.0.0`), `gt-gst` (`>=3.2.0,<4.0.0`) |

## Three-Axis Maturity Contract

1. **Specification & arithmetic (`GUS v3.0.0` + 10 calendars):** Frozen and
   verified bit-for-bit across Python, JavaScript, and C11.
2. **Reference implementations (`v3.2.2`):** Stable and continuously verified
   in CI (`gt-core`, `gt-gus`, `gt-tcj`, `gt-calendar`, `gt-gts`, `gt-gst`,
   `gt-interop`). `gt-tslr` and `gt-gcerts` remain **EXPERIMENTAL**
   (specification + scaffold, no reference implementation).
3. **Production cryptographic assurance:** `gt-gst` (`GST v2`: hybrid
   Ed25519 + ML-DSA over RFC 8785 JCS, domain `GUS3-GST-V2`, anti-downgrade,
   fail-closed `ReplayGuard`) and the daily Merkle notary require an
   independent third-party cryptographic audit and hardware key custody
   (TPM/HSM) before production security decisions. Legacy `WOTS+`
   (`src/gerarion/deprecated/hashots.py`) is deprecated and outside `GST v2`.

## Verification Contract (`EXPORT-MANIFEST.json`)

Every exported satellite includes an `EXPORT-MANIFEST.json` at its root
(`schema: "gerarion-export-manifest/1"`) containing the exact `source_commit`,
`source_tag`, `dependencies`, `maturity`, and the sorted SHA-256 map of every
exported file.

To verify any exported satellite directory offline:

```bash
python3 tools/export_module.py --verify-existing /path/to/gt-<module>
```

This checks:
1. SHA-256 integrity of every file in `EXPORT-MANIFEST.json` with zero missing
   or extraneous files.
2. 100 % REUSE 3.3 compliance (`reuse lint`).
3. Clean standalone compilation and smoke test (`-Werror`) for `gt-core`.
