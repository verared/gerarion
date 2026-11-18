# Adversarial and Numeric-Bounds Audit Report — GUS 3.0.0

**Audit v3.0.0 · November 18, 2026 · verared**
Scope: calendar core (Python/C11/JavaScript), active cryptographic stack
(GST v2 with JCS RFC 8785 and hybrid Ed25519+ML-DSA), persistent
anti-replay guard and notary quorum. Deprecated modules (`hashots.py`)
and experimental profiles (TSLR/GCERTS) are outside the audited active
surface.

## 1. Executive summary

The system withstands the full adversarial battery: **1,000,000
bit-exact differential fuzzing cases Python↔JS↔C** with zero
divergences, **1,000,000 integer round-trips at the int64 extremes with
no undefined behavior** (ASan+UBSan), and 18 simulated cryptographic
attacks (downgrade, key substitution, replay, rollback, quorum) rejected
in 100% of cases.

Two REAL weaknesses were discovered by this audit and were **fixed
within the same series** (table §3): the `ReplayGuard` fail-open on
corrupted state, and counting foreign replicas in the quorum. None
reached Critical: there is no known path to a false valid seal.

**Message for hardware and critical-systems integrators:** the calendar
arithmetic is O(1), deterministic and float-free; exact per-platform
limits are contracted in spec Appendix A.5 and hardened with clean
`GERO_ERANGE` in C11. The active cryptography requires all-or-nothing
hybrid verification with mandatory `event_hash` and fail-closed
persistent anti-replay state.

## 2. Findings matrix

| # | Severity | Finding | Status |
|---|---|---|---|
| A-1 | High | `toGerarion` (JS) enters a non-terminating loop with `day_index` ≥ 2⁵³: `Number` imprecision breaks the annual correction convergence (tab DoS with hostile input) | **Fixed**: `Number.isSafeInteger` guard + `GERO_EINVAL`; domain model in spec Appendix A.5 |
| A-2 | High | `ReplayGuard` with a corrupted/truncated state file resumed as empty history (fail-open): silent `seq` restart, replay and rollback enabled | **Fixed**: `_poisoned` fail-closed mechanism; corrupted state rejects everything until operator action |
| A-3 | Medium | The notary quorum counted UNAUTHORIZED identities arriving with well-formed publications (the name→key binding existed only as external policy without verifier support) | **Fixed**: optional `known_replicas` in `quorum`/`verify_day`/`verify_bundle`; foreign identities excluded and reported in `unknown_replicas` |
| A-4 | Medium | Divergent validation order C vs Python on DOUBLY invalid stamps (malformed time syntax + impossible Tempalum): C answered `GERO_ETEMPALUM` where Python/JS answered `GERO_EINVAL` (and the reverse with out-of-range hours) | **Fixed**: normed precedence syntax → calendar → weekday → ranges, identical in the three implementations; enforced by the mutation corpus |
| A-5 | Medium | JS `normalize` collapsed multiple spaces (`\s+` → `-`) while the Python reference replaces per character: double-space stamps diverged (JS accepted, Python/C rejected) | **Fixed**: per-character replacement in JS; C adds end-trimming mirroring `raw.strip()` |
| A-6 | Low | No exhaustive int64 boundary hardening in C: theoretical *signed integer overflow* (UB) paths for extreme years/days | **Fixed**: `GUS_MAX_*` macros in `gus.h`, `GUS_ERANGE` guards in `from/to_gerarion`, `instant_from_parts`, `gregorian_from_day_index` and `day_index_from_gregorian`; verified with 10⁶ round-trips under UBSan |
| A-7 | Informational | ASan `detect_leaks` is unsupported on macOS; the 0-leak check must run on Linux CI (`ASAN_OPTIONS=detect_leaks=1`) | Documented in `impl-c/Makefile` and §3 of this report |
| A-8 | Informational | The `kid`↔public-key correspondence is a deployment trust-root binding: an envelope re-signed with another key is cryptographically valid and only the trust root detects it | Documented (test `test_c_kid_cruzado...`); no code change: binding is by-design a deployment concern |

No Critical findings. The hybrid signature, JCS canonicalization, domain
separation (GST-V2 prefix), mandatory `event_hash` and the frozen
calendar arithmetic withstood every attack without needing correction.

## 3. Reproducible evidence

### 3.1 Massive differential fuzzing (1,000,000 cases)

```bash
make -C impl-c gus-cli                       # C correductor
python3 tools/fuzz_diff.py --cases 1000000   # fixed seed: 20310101
```

Actual result (49 s, 41.5 s CPU):

```
digest python=070913bc0ed2e168 js=ef00051b4b126a1b c=2bd86c2da8e3ed10
OK estres: 1000000 casos, 0 divergencias bajo las politicas por op
```

Corpus: mandatory deterministic blocks (Gran Tempalum transitions
−29/−23/−17/−12/−6/−1/0/5/11/2034; deep 12000AY, 999999DY/AY; offsets
`TCJ+0/-2:20/+5:45/-12:00/+14:00`; `nanos` fractions 0/1/999,999,999;
extended and compact formats) plus a random distribution with one-byte
mutations and malformed-garbage pools. Per-op policy: triple equality
(common), exact Python↔C with JS outside its domain (`tgs`/`fgs`/`grs`),
and exact `GERO_ERANGE` in C for limits (`tgq`/`fgq`/`grq`/`inq`).
Intermediate scales used during the audit: 3,000 (bisection of the 45
divergences A-4/A-5), 20,000, 100,000 (39), 200,000 (72), 300,000 (0)
and 1,000,000 (0).

### 3.2 C11 memory and UB audit (ASan + UBSan)

```bash
make -C impl-c audit      # -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic
                          # -fsanitize=address,undefined -fno-sanitize-recover=all
```

Actual result:

```
CONFORME (núcleo GUS en C): 10 categorías, 0 fallos
audit límites: bordes int64 con GERO_ERANGE exacto
audit roundtrips: 1000000 conversiones, 0 fallos
audit parser fuzz: 400000 entradas, 0 fallos de memoria/UB
AUDIT OK: 6524458 comprobaciones, 0 errores, 0 fugas, 0 UB
```

The harness (`impl-c/audit_stress.c`) runs under sanitizers: (1) the 10
normative conformance categories with the official vectors; (2) one
million round-trip conversions sampled up to the exact edge of
`GUS_MAX_YEAR_SAFE` and instants at ±`GUS_MAX_INSTANT_DAYS_SAFE`; (3)
400,000 parser inputs in bounded buffers with the terminator at the edge
(binary noise with non-ASCII bytes, truncated mutations, 7-20 digit
years, hostile offsets and fractions). Compilation with `-Werror`: 0
warnings. The additional MSan (`-fsanitize=memory`) pass is not
available: Apple Clang does not implement it; pending Linux CI with
instrumented clang.

### 3.3 Adversarial tests (`tests/test_adversarial_security.py`)

```bash
python -m pytest tests/test_adversarial_security.py -v
```

18 attacks, all rejected: duplicate keys/UTF-16 ordering/subnormals in
JCS; deletion and degradation of the ML-DSA branch; altered byte in
`event_hash`/`nanos`; signature reused out-of-domain; replay burst;
rollback after restart; corrupted state fail-closed; duplicate and
intruder nodes in the 2-of-3 and 3-of-4 quorum. The two fixed findings
(A-2, A-3) were born as failures of this suite.

### 3.4 Full battery of the audited version

| Group | Result |
|---|---:|
| `pytest tests/` (`[dev,slh,pqc]`) | 244 passed, 1 skipped |
| `web/tests.mjs` | 36/36 |
| `web/calendars.test.mjs` | 42/42 |
| `tests/atlas.test.mjs` | 40/40 |
| `make -C impl-c conformance` | 10/10 |
| `make -C impl-c audit` (ASan+UBSan) | 0 errors, 0 UB, 0 warnings |
| `tools/fuzz_diff.py --cases 1000000` | 1,000,000, 0 divergences |
| `e2e_web_test.py` | 53/53 |
| `reuse lint` | REUSE 3.3, 0 errors |

## 4. Audit limits

This audit is static + dynamic over the reference implementations of
this repository, on a macOS (arm64) host. It is not a certification: it
does not cover the supply chain of third-party libraries
(`cryptography`), hardware, timing (side channels), or an exhaustive
sample of the full 64-bit input space. The formal proofs of the calendar
(closed derivations) are in spec Appendix A; the operational limits, in
its table A.5.
