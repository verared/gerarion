# `verared/gt-*` Satellite Repository Architecture

Version: 1.0.0 · Baseline: `v3.2.0` · License: CC-BY-4.0 ·
Maintained by: verared contributors

## 1. General model

`verared/gerarion` is the **complete reference suite**: the 8 normative
specifications, the CC0 vectors, the reference cores on the three
platforms, and the verification battery. The `verared/gt-*`
(Gerarion Time) satellite repositories are **single-domain derived
products**: each adopts exactly one problem, without dragging the rest
of the suite along.

```
verared/gerarion          (source of truth: specs + vectors + cores + battery)
   │  python3 tools/export_module.py --module <gt-*> --out <dir>
   ▼
verared/gt-core      gt-tcj      gt-gus      gt-calendar
        gt-gts       gt-gst      gt-interop
        gt-tslr*     gt-gcerts*  (* experimental, initial scaffolds)
```

## 2. Modules and dependencies

| Module | Domain | Depends on | Status |
|---|---|---|---|
| `gt-core` | TCJ + GUS (MCU/bare-metal core) | — | Stable |
| `gt-tcj` | TCJ atomic scale, TAI − UTC bridge | gt-core | Stable |
| `gt-gus` | Canonical 32/29 syntax, quick_verify | — | Stable |
| `gt-calendar` | AY/DY + 10 calendars (GUTI-1) | gt-core | Stable |
| `gt-gts` | State machine §6.3 + Roughtime | gt-core (Roughtime: +gt-interop, compat re-exports: gt-gst) | Stable (core) |
| `gt-gst` | GST v2, JCS RFC 8785, hybrid, ReplayGuard, notary | gt-core | Stable |
| `gt-interop` | RFC 3339, ISO 8601, Unix, RFC 3161 | gt-core + gt-tcj | Stable (3339) |
| `gt-tslr` | True Local Solar Time | gt-core | EXPERIMENTAL |
| `gt-gcerts` | Temporal validity of certificates | gt-core + gt-gst | EXPERIMENTAL |

The exact dependency truth lives in the code
(`tools/export_module.py`, `deps` + `external_roots` attributes) and is
repeated in every export's README.

## 3. System rules

1. **Relative paths intact.** Every export keeps the base
   repository's directory layout (`docs/specs/`, `impl-c/`,
   `src/gerarion/`, `web/engine/`, `vectors/`). Two or more satellites
   merge into one tree without path conflicts.
2. **Read-only origin.** Exporting does not modify `verared/gerarion`
   (verified invariant: `tests/test_export_module.py`). Satellites
   **never hand-edit** exported files: they regenerate from a tag.
3. **Single source of truth.** Specifications, CC0 vectors, and the
   full battery live ONLY in `verared/gerarion`. A satellite declares
   its baseline (`v3.2.0` or later) and reproduces it with its own
   runners where applicable.
4. **Legal compatibility.** Every export is a complete REUSE 3.3
   project: `LICENSE`, `LICENSES/`, `NOTICE`, and a generated
   `REUSE.toml` cover 100 % of its files (`reuse lint` 100 %).
   `LICENSES/` texts are only copied when the module actually uses
   them.
5. **Vectors per module.** Each export carries its CC0 vectors
   (`gus-normative-003.json` for cores, `guti-calendars-001.json` for
   the calendar engine, `gus-3339-*` for INTEROP), with
   `--no-large-vectors` for lightweight distributions.

## 4. Operating flow

### 4.1 Export

```bash
python3 tools/export_module.py --all --out /tmp/gt --verify
# or a single module:
python3 tools/export_module.py --module gt-core --out /tmp/gt --verify
```

`--verify` runs `reuse lint` inside every export and, for `gt-core`,
compiles the standalone core with
`-std=gnu11 -Wall -Wextra -Werror` and runs its smoke test (the frozen
internal guard uses `__int128`, a GNU extension: strict ISO pedantic
compliance is covered by the base repository's audit battery; GCC/Clang
compile warning-free in this mode). It
exits 2 on any error.

### 4.2 Publish a satellite

```bash
python3 tools/export_module.py --module gt-core --out /tmp/gt --verify
cd /tmp/gt/gt-core
git init && git add -A && git commit -m "gt-core v3.2.0 (generated from verared/gerarion)"
git remote add origin git@github.com:verared/gt-core.git
git push -u origin main
gh repo create verared/gt-core --public --source . --push  # alternative
```

Operational recommendation: create the remote from the current release
and protect the satellite's `main`; any change goes to the base
repository first and is regenerated downstream.

### 4.3 Consume (integrators)

An integrator needs only the domain their product uses:

```bash
git clone https://github.com/verared/gt-core   # MCU C11 core
make -C gt-core/impl-c smoke                   # verifiable standalone core
```

Or, for applications combining domains: clone the needed modules into a
common tree (relative paths match), or add the Python packages
per-extras (`pip install gerarion[gst,gts]`).

### 4.4 Update a satellite

```bash
# in verared/gerarion, with a new tag (>= v3.2.0):
python3 tools/export_module.py --module gt-core --out /tmp/gt --verify
# in the satellite clone:
git pull --rebase          # never manual edits past the last export
# overlay with the fresh export:
rsync -a --delete /tmp/gt/gt-core/ ~/src/gt-core/
git diff --stat            # the only expected diff: new code from the tag
```

## 5. Contents of every export

Besides the domain's code and docs, each package includes:

| Piece | Origin |
|---|---|
| `LICENSE`, `NOTICE`, `LICENSES/` | copied from the `verared/gerarion` root |
| `REUSE.toml` | generated by the tool, override annotations, 100 % coverage |
| `README.md` / `README.es.md` | generated: unique problem, status, dependencies, offline usage, sync contract |
| `impl-c/Makefile` (gt-core only) | generated: `libgerarion-core.a`/`.so` + `gerarion-core.pc` + standalone smoke, malloc-free |
| `src/`, `tests/`, `vectors/` scaffolds (experimental modules only) | generated |

## 6. Closure certification

- `reuse lint` on the base repository: **100 %** (required on every PR).
- `reuse lint` on every export: **100 %** (guaranteed by the tool and
  tested in `tests/test_export_module.py`).
- Satellites inherit the domain's normative status: a Stable module
  exposes frozen arithmetic; an EXPERIMENTAL module always starts
  marked as such (`EXPERIMENTAL` in README and spec).
