#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Exportador modular de la suite de referencia Gerarion.

Genera paquetes autónomos —uno por dominio normativo— listos para
publicarse como repositorios satélite ``verared/gt-*`` (Gerarion Time),
manteniendo intacta la matemática, los motores y los vectores congelados
de ``verared/gerarion``. La versión se lee dinámicamente desde
``pyproject.toml``. La herramienta SOLO empaqueta: nunca altera el
código fuente del repositorio base.

Para cada exportación se genera en el directorio destino:
- el árbol de archivos del módulo (misma ruta relativa que en el
  repositorio base, de modo que los satélites se combinan limpiamente);
- ``LICENSE``, ``LICENSES/`` y ``NOTICE`` copiados de la raíz;
- un ``REUSE.toml`` que cubre el 100 % de los archivos exportados;
- ``README.md`` y ``README.es.md`` con alcance, estado normativo,
  dependencias y contrato de sincronización;
- para ``gt-core``, un ``Makefile`` standalone (sin malloc, sin
  dependencias) que construye ``libgerarion-core`` y su ``.pc``.

Uso::

    python3 tools/export_module.py --module gt-core --out /tmp/satelites
    python3 tools/export_module.py --all --out /tmp/satelites --verify

Salida de exportación: ``<out>/<modulo>/...``. ``--verify`` ejecuta
``reuse lint`` dentro de cada exportación y, para ``gt-core``, la
compilación limpia del núcleo standalone; falla con código distinto de
cero ante cualquier error.
"""

from __future__ import annotations

import argparse
import ast
import base64
import dataclasses
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_REPO = "verared/gerarion"
COMPAT_RANGE = ">=3.2.0,<4.0.0"
MANIFEST_FILENAME = "EXPORT-MANIFEST.json"
MANIFEST_SCHEMA = "gerarion-export-manifest/1"
MANIFEST_SIG_FILENAME = "EXPORT-MANIFEST.json.sig"
MANIFEST_SIG_SCHEMA = "gerarion-manifest-sig/1"


def _read_project_version() -> str:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', pyproject)
    if not m:
        raise RuntimeError("No se pudo leer version de pyproject.toml")
    return m.group(1)


def _resolve_source_commit(override: Optional[str] = None) -> str:
    if override:
        return override.strip()
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(
            "No se pudo determinar source_commit vía git rev-parse HEAD: "
            + (proc.stderr or proc.stdout).strip()
        )
    return proc.stdout.strip()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


GERARION_VERSION = _read_project_version()

# ---------------------------------------------------------------------------
# Especificación de módulos
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ModuleSpec:
    name: str                      # gt-core, gt-tcj, ...
    title_es: str
    title_en: str
    purpose_es: str
    purpose_en: str
    status: str                    # "Estable" | "EXPERIMENTAL" | ...
    maturity: str                  # "stable" | "stable-core/experimental-roughtime" | "experimental"
    deps: Tuple[str, ...]          # módulos gt-* de los que depende
    files: Tuple[str, ...] = ()    # archivos individuales (ruta exacta)
    dirs: Tuple[str, ...] = ()     # directorios copiados enteros
    vectors: Tuple[str, ...] = ()
    large_vectors: Tuple[str, ...] = ()  # omitibles con --no-large-vectors
    docs: Tuple[str, ...] = ()     # especificaciones (docs/)
    scaffold: bool = False         # crear src/, tests/, vectors/ con .gitkeep
    external_roots: Tuple[str, ...] = ()  # importaciones externas esperadas
    # (primer componente de módulo relativo no resuelto en el export)
    core_checked: bool = False     # --verify compila el núcleo C


MODULES: Dict[str, ModuleSpec] = {
    m.name: m
    for m in [
        ModuleSpec(
            name="gt-core",
            title_es="Núcleo autónomo TCJ + GUS",
            title_en="Standalone TCJ + GUS core",
            purpose_es=(
                "El núcleo normativo mínimo: calendario AY/DY con Gran "
                "Tempalum, formato canónico de 32/29 caracteres, "
                "quick_verify e instantes int64 + nanos. Apto para "
                "microcontroladores y despliegues bare-metal: sin malloc, "
                "sin reloj de SO, sin tabla TAI−UTC y sin dependencias."
            ),
            purpose_en=(
                "The minimum normative core: AY/DY calendar with Great "
                "Tempalum, canonical 32/29-character format, quick_verify, "
                "and int64 + nanos instants. Fit for microcontrollers and "
                "bare metal: no malloc, no OS clock, no TAI−UTC table, no "
                "dependencies."
            ),
            status="Estable",
            maturity="stable",
            deps=(),
            dirs=(
                "impl-c/core",
                "src/gerarion/core",
            ),
            files=("web/engine/core.mjs",),
            vectors=(
                "vectors/gus-normative-003.json",
                "vectors/gus-quickverify-001.json",
                "vectors/gus-regression-001.json",
            ),
            docs=(
                "docs/specs/TCJ.es.md",
                "docs/specs/TCJ.en.md",
                "docs/specs/GUS.es.md",
                "docs/specs/GUS.en.md",
            ),
            external_roots=(),
            core_checked=True,
        ),
        ModuleSpec(
            name="gt-tcj",
            title_es="Escala atómica TCJ y puente TAI − UTC",
            title_en="TCJ atomic scale and TAI − UTC bridge",
            purpose_es=(
                "La coordenada global TCJ = TAI + 8.400 s, la tabla "
                "histórica TAI − UTC versionada (IERS-C-2026.1) con aviso "
                "de extrapolación tras su vigencia, y el índice geográfico "
                "de desfases civiles frente a TCJ."
            ),
            purpose_en=(
                "The global TCJ = TAI + 8,400 s coordinate, the versioned "
                "historical TAI − UTC table (IERS-C-2026.1) with an "
                "extrapolation warning past its validity horizon, and the "
                "geographic index of civil offsets against TCJ."
            ),
            status="Estable",
            maturity="stable",
            deps=("gt-core",),
            dirs=(
                "impl-c/tai",
                "src/gerarion/tcj",
            ),
            files=(
                "web/engine/tcj-tai.mjs",
                "web/engine/zonas-tcj.mjs",
            ),
            docs=(
                "docs/specs/TCJ.es.md",
                "docs/specs/TCJ.en.md",
            ),
            external_roots=("core",),
        ),
        ModuleSpec(
            name="gt-gus",
            title_es="Sintaxis canónica de marca Gerarion",
            title_en="Gerarion canonical stamp syntax",
            purpose_es=(
                "El formato canónico de 32 y 29 caracteres, sus reglas de "
                "normalización (REGLAS 1-7), la verificación rápida "
                "(quick_verify) y la representación del instante "
                "(int64 segundos + nanos separado)."
            ),
            purpose_en=(
                "The 32- and 29-character canonical format, its "
                "normalisation rules (RULES 1-7), the fast check "
                "(quick_verify), and the instant representation "
                "(int64 seconds + separate nanos)."
            ),
            status="Estable",
            maturity="stable",
            deps=(),
            dirs=("src/gerarion/core",),
            files=("impl-c/core/gus_core.h", "impl-c/core/gus_core.c",
                   "web/engine/core.mjs"),
            vectors=(
                "vectors/gus-normative-003.json",
                "vectors/gus-quickverify-001.json",
            ),
            docs=(
                "docs/specs/GUS.es.md",
                "docs/specs/GUS.en.md",
            ),
            external_roots=(),
        ),
        ModuleSpec(
            name="gt-calendar",
            title_es="Calendario Gerarion y motor multi-calendario",
            title_en="Gerarion calendar and multi-calendar engine",
            purpose_es=(
                "El año regular AY/DY con Gran Tempalum simétrico y el "
                "motor determinista de conversión con 10 sistemas "
                "calendáricos externos (GUTI-1), todo pivotando sobre "
                "day_index/JDN con aritmética entera pura."
            ),
            purpose_en=(
                "The regular AY/DY year with symmetric Great Tempalum and "
                "the deterministic conversion engine for 10 external "
                "calendar systems (GUTI-1), all pivoting on day_index/JDN "
                "with pure integer arithmetic."
            ),
            status="Estable",
            maturity="stable",
            deps=("gt-core",),
            dirs=(
                "impl-c/calendars",
                "src/gerarion/calendars",
            ),
            files=(
                "web/engine/guti.mjs",
                "web/engine/china-table.mjs",
                "web/engine/calendars.mjs",
            ),
            vectors=(),
            large_vectors=("vectors/guti-calendars-001.json",),
            docs=(
                "docs/specs/CALENDAR.es.md",
                "docs/specs/CALENDAR.en.md",
            ),
            external_roots=("core",),
        ),
        ModuleSpec(
            name="gt-gts",
            title_es="Sincronización y calidad de reloj",
            title_en="Time synchronisation and clock quality",
            purpose_es=(
                "La máquina de estados de confianza de reloj (VERIFIED → "
                "HOLDOVER → UNVERIFIED → REJECTED), las anclas "
                "anti-rollback persistentes y el perfil experimental de "
                "sincronización Roughtime."
            ),
            purpose_en=(
                "The clock trust state machine (VERIFIED → HOLDOVER → "
                "UNVERIFIED → REJECTED), persistent anti-rollback anchors, "
                "and the experimental Roughtime profile."
            ),
            status="Estable (núcleo) / Experimental (Roughtime)",
            maturity="stable-core/experimental-roughtime",
            deps=("gt-core",),
            dirs=(
                "impl-c/clock",
                "src/gerarion/gts",
            ),
            # "gst": el __init__ de gerarion.gts reexporta compatibilidad
            # desde gerarion.gst.envelope (el sobre GST v2 histórico).
            # La máquina de reloj pura (gerarion.gts.clock) solo necesita
            # gt-core; los reexports exigen gt-gst.
            docs=(
                "docs/specs/GTS.es.md",
                "docs/specs/GTS.en.md",
            ),
            external_roots=("core", "interop", "gst"),
        ),
        ModuleSpec(
            name="gt-gst",
            title_es="Sellado criptográfico de eventos",
            title_en="Cryptographic event sealing",
            purpose_es=(
                "El sobre firmado GST v2: canonicalización RFC 8785 (JCS), "
                "firma híbrida Ed25519 + ML-DSA con protección "
                "anti-downgrade, ReplayGuard persistente y notario Merkle "
                "diario con quórum."
            ),
            purpose_en=(
                "The signed GST v2 envelope: RFC 8785 canonicalisation "
                "(JCS), hybrid Ed25519 + ML-DSA signing with "
                "anti-downgrade protection, persistent ReplayGuard, and "
                "the daily Merkle notary with quorum."
            ),
            status="Estable (GST v2; auditoría criptográfica externa requerida para producción)",
            maturity="stable",
            deps=("gt-core",),
            dirs=("src/gerarion/gst",),
            docs=(
                "docs/specs/GST.es.md",
                "docs/specs/GST.en.md",
                "docs/spec/threat-model.md",
                "docs/en/threat-model.md",
            ),
            external_roots=("core", "deprecated"),
        ),
        ModuleSpec(
            name="gt-interop",
            title_es="Puentes con estándares heredados",
            title_en="Bridges with legacy standards",
            purpose_es=(
                "Conversión exacta y auditable entre GUS y RFC 3339 / "
                "ISO 8601 / Unix, y el perfil RFC 3161 (TSA). Los formatos "
                "heredados son de entrada/salida: nunca sustituyen a la "
                "coordenada GUS."
            ),
            purpose_en=(
                "Exact, auditable conversion between GUS and RFC 3339 / "
                "ISO 8601 / Unix, plus the RFC 3161 (TSA) profile. Legacy "
                "formats are for input/output: they never replace the GUS "
                "coordinate."
            ),
            status="Estable (RFC 3339) / Experimental (RFC 3161)",
            maturity="stable",
            deps=("gt-core", "gt-tcj"),
            dirs=("src/gerarion/interop",),
            vectors=(
                "vectors/gus-3339-002.json",
                "vectors/gus-3339-negative-001.json",
            ),
            docs=(
                "docs/specs/INTEROP.es.md",
                "docs/specs/INTEROP.en.md",
            ),
            external_roots=("core", "tcj"),
        ),
        ModuleSpec(
            name="gt-tslr",
            title_es="Tiempo Solar Local Real (EXPERIMENTAL)",
            title_en="True Local Solar Time (EXPERIMENTAL)",
            purpose_es=(
                "Verificación astronómica opcional para evidencia forense "
                "de Nivel 3. PERFIL EXPERIMENTAL: separado del núcleo "
                "normativo; sin implementación de referencia todavía. La "
                "estructura inicial está lista para desarrollo "
                "independiente."
            ),
            purpose_en=(
                "Optional astronomical verification for Level-3 forensic "
                "evidence. EXPERIMENTAL PROFILE: separate from the "
                "normative core; no reference implementation yet. The "
                "initial structure is ready for independent development."
            ),
            status="EXPERIMENTAL",
            maturity="experimental",
            deps=("gt-core",),
            docs=(
                "docs/specs/TSLR.es.md",
                "docs/specs/TSLR.en.md",
            ),
            scaffold=True,
            external_roots=(),
        ),
        ModuleSpec(
            name="gt-gcerts",
            title_es="Validez temporal de certificados (EXPERIMENTAL)",
            title_en="Temporal validity of certificates (EXPERIMENTAL)",
            purpose_es=(
                "Perfiles de vigencia temporal de certificados sobre "
                "coordenadas GUS. PERFIL EXPERIMENTAL: separado del "
                "núcleo normativo; sin implementación de referencia "
                "todavía. La estructura inicial está lista para "
                "desarrollo independiente."
            ),
            purpose_en=(
                "Certificate temporal-validity profiles over GUS "
                "coordinates. EXPERIMENTAL PROFILE: separate from the "
                "normative core; no reference implementation yet. The "
                "initial structure is ready for independent development."
            ),
            status="EXPERIMENTAL",
            maturity="experimental",
            deps=("gt-core", "gt-gst"),
            docs=(
                "docs/specs/GCERTS.es.md",
                "docs/specs/GCERTS.en.md",
            ),
            scaffold=True,
            external_roots=(),
        ),
    ]
}

# ---------------------------------------------------------------------------
# Clasificación de licencias para el REUSE.toml del export
# ---------------------------------------------------------------------------

CODE_SUFFIXES = {".c", ".h", ".mjs", ".py", ".in"}
DOC_SUFFIXES = {".md"}
VECTOR_SUFFIXES = {".json"}

LICENSE_CODE = "MIT OR Apache-2.0"
LICENSE_DOC = "CC-BY-4.0"
LICENSE_VECTOR = "CC0-1.0"


def classify_license(rel: Path) -> Optional[str]:
    """Licencia SPDX de un archivo relativo del export."""
    # .gitkeep: reuse ignora los dotfiles; anotarlos solo produciría
    # licencias "unused". El andamiaje queda cubierto por los dotfiles
    # ignorados y por los README del export.
    if rel.name == "Makefile" or rel.suffix in CODE_SUFFIXES:
        return LICENSE_CODE
    if rel.suffix in VECTOR_SUFFIXES:
        return LICENSE_VECTOR
    if rel.suffix in DOC_SUFFIXES:
        return LICENSE_DOC
    if rel.name in ("LICENSE", "NOTICE"):
        return LICENSE_DOC
    return None


# ---------------------------------------------------------------------------
# Plantillas (Makefile standalone de gt-core, README, REUSE.toml)
# ---------------------------------------------------------------------------

GT_CORE_MAKEFILE = """\
# Makefile standalone de libgerarion-core (export gt-core).
# Generado por tools/export_module.py de {source} v{version} ({date}).
# Núcleo TCJ+GUS: sin malloc, sin reloj de SO, sin tabla TAI-UTC, sin
# dependencias externas. Compilable con GCC y Clang (C11, -Werror).

NAME = gerarion-core
MAJOR = 3
MINOR = 2
PATCH = 0

PREFIX ?= /usr/local
INCLUDEDIR ?= $(PREFIX)/include
LIBDIR ?= $(PREFIX)/lib
PKGCONFDIR ?= $(LIBDIR)/pkgconfig

CC ?= cc
CFLAGS ?= -std=gnu11 -O2 -Wall -Wextra -pedantic
PICFLAGS ?= -fPIC

SRC = core/gus_core.c
HDRS = core/gus_core.h

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
SO_LDFLAGS = -shared
else
SO_LDFLAGS = -shared -Wl,-soname,lib$(NAME).so.$(MAJOR)
endif

.PHONY: all smoke clean install pkgconfig

all: libgerarion-core.a libgerarion-core.so.$(MAJOR) gerarion-core.pc

libgerarion-core.a: $(SRC) $(HDRS)
	$(CC) $(CFLAGS) -c $(SRC) -o gus_core.a.o
	ar rcs $@ gus_core.a.o
	rm -f gus_core.a.o

libgerarion-core.so.$(MAJOR): $(SRC) $(HDRS)
	$(CC) $(CFLAGS) $(PICFLAGS) $(SO_LDFLAGS) -o $@ $(SRC)

gerarion-core.pc: gerarion-core.pc.in
	sed -e 's|@PREFIX@|$(PREFIX)|g' \\
		-e 's|@VERSION@|$(MAJOR).$(MINOR).$(PATCH)|g' \\
		gerarion-core.pc.in > $@

pkgconfig: gerarion-core.pc

# Humo: núcleo compilado y ejecutado en total aislamiento.
smoke: libgerarion-core.a
	$(CC) $(CFLAGS) -I. -o smoke.c.bin smoke.c ./libgerarion-core.a
	./smoke.c.bin

install: all
	install -d $(DESTDIR)$(INCLUDEDIR)/gerarion/core $(DESTDIR)$(LIBDIR) $(DESTDIR)$(PKGCONFDIR)
	install -m 644 core/gus_core.h $(DESTDIR)$(INCLUDEDIR)/gerarion/core/
	install -m 644 libgerarion-core.a libgerarion-core.so.$(MAJOR) $(DESTDIR)$(LIBDIR)/
	ln -sf libgerarion-core.so.$(MAJOR) $(DESTDIR)$(LIBDIR)/libgerarion-core.so
	install -m 644 gerarion-core.pc $(DESTDIR)$(PKGCONFDIR)/

clean:
	rm -f libgerarion-core.a libgerarion-core.so.$(MAJOR) gerarion-core.pc smoke.c.bin gus_core.a.o *.o
"""

GT_CORE_PC_IN = """prefix=@PREFIX@
libdir=${{prefix}}/lib
includedir=${{prefix}}/include

Name: gerarion-core
Description: libgerarion-core - nucleo GUS standalone (calendario AY/DY, formato canonico 32/29, quick_verify, instantes int64+nanos); sin reloj de SO ni tabla TAI
Version: @VERSION@
Libs: -L${{libdir}} -lgerarion-core
Cflags: -I${{includedir}}/gerarion
"""

GT_CORE_SMOKE_C = """\
/*
 * smoke.c — humo del núcleo standalone (export gt-core).
 * Compila y corre SOLO con core/gus_core.h + libgerarion-core.a.
 * Generado por tools/export_module.py de {source} v{version}.
 */

#include "core/gus_core.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    long long di = 0;
    assert(gus_day_index_from_gregorian(2026, 3, 17, &di) == GUS_OK);
    GusDate d;
    assert(gus_to_gerarion(di, &d) == GUS_OK);
    char buf[48];
    GusParsed p;
    p.date = d;
    p.has_time = 0;
    assert(gus_canonical(&p, buf, sizeof(buf)) == GUS_OK);
    printf("gt-core smoke: %s (%lld)\\n", buf, di);
    return gus_quick_verify(buf) ? 0 : 1;
}
"""

README_TMPL_ES = """\
# {title}

Parte de la suite de referencia **Gerarion** ({source} `v{version}`,
Gerarion Universal Standard). Este directorio es un **paquete de
exportación** listo para publicarse (o consumirse) como repositorio
satélite `verared/{name}`; conserva las rutas relativas del repositorio
base para componer módulos.

## El problema único que resuelve

{purpose}

## Estado normativo

- **{status}** (`maturity: {maturity}`) — línea base `v{version}` (aritmética y vectores
  congelados: GUS v3.0.0).
- Especificación(es) incluida(s): {spec_list}
- Manifiesto de integridad verificable: [`EXPORT-MANIFEST.json`](EXPORT-MANIFEST.json)
- Matriz oficial de compatibilidad: [`COMPATIBILITY.md`](https://github.com/{source}/blob/v{version}/COMPATIBILITY.md)
{crypto_section_es}{quickstart_section_es}
## Las 5 Garantías de Distribución

| # | Garantía | Mecanismo verificable |
|---|---|---|
| 1 | **Integridad SHA-256** | Mapa `files` en [`EXPORT-MANIFEST.json`](EXPORT-MANIFEST.json) verificado con `--verify-existing`. |
| 2 | **Procedencia declarada** | Campos `source_repo`, `source_tag` (`v{version}`) y `source_commit` (SHA-1 de 40 caracteres). |
| 3 | **Autenticidad de publicación** | Firma Ed25519 separada `EXPORT-MANIFEST.json.sig` verificable con `--trusted-pub-key` (sin autorreferencia). |
| 4 | **Reproducibilidad** | Re-exportación determinista bit a bit desde el mismo `--source-commit`. |
| 5 | **Conformidad funcional** | Suite de vectores normativos CC0 e integración cruzada en C11, Python y JavaScript. |

## Dependencias

{deps_es}

## Contenido

{content_es}

## Uso offline

No requiere red, cuentas, registro de paquetes ni frameworks:

{usage_es}

## Verificación

Con Python ≥ 3.9 y `reuse` instalado:

```bash
reuse lint                                    # licencias al 100 %
{verify_extra}
```

Desde `{source}`, la integridad y (opcionalmente) la autenticidad de firma separada se verifican con:

```bash
python3 tools/export_module.py --verify-existing /ruta/a/{name}
# Con verificación criptográfica de EXPORT-MANIFEST.json.sig:
python3 tools/export_module.py --verify-existing /ruta/a/{name} --trusted-pub-key /ruta/a/release-pub.pem
```

## Contrato de sincronización con `{source}`

Este paquete es **generado, no editado a mano**: se regenera byte a
byte desde `{source} v{version}` con
`python3 tools/export_module.py --module {name} --out <dir>`. La fuente
de verdad normativa (especificaciones, vectores CC0, núcleos de
referencia de las tres plataformas y la batería completa) permanece en
`{source}`; los satélites `verared/{name}` la consumen y no forkean la
aritmética. Las actualizaciones fluyen regenerando la exportación desde
un tag del repositorio base; nunca editando los archivos exportados.
"""

README_TMPL_EN = """\
# {title}

Part of the **Gerarion** reference suite ({source} `v{version}`,
Gerarion Universal Standard). This directory is an **export package**
ready to be published (or consumed) as the `verared/{name}` satellite
repository; it keeps the base repository's relative layout so modules
compose cleanly.

## The unique problem it solves

{purpose}

## Normative status

- **{status}** (`maturity: {maturity}`) — baseline `v{version}` (frozen arithmetic and vectors:
  GUS v3.0.0).
- Included specification(s): {spec_list}
- Verifiable integrity manifest: [`EXPORT-MANIFEST.json`](EXPORT-MANIFEST.json)
- Official compatibility matrix: [`COMPATIBILITY.md`](https://github.com/{source}/blob/v{version}/COMPATIBILITY.md)
{crypto_section_en}{quickstart_section_en}
## The 5 Distribution Guarantees

| # | Guarantee | Verifiable mechanism |
|---|---|---|
| 1 | **SHA-256 Integrity** | `files` map in [`EXPORT-MANIFEST.json`](EXPORT-MANIFEST.json) checked via `--verify-existing`. |
| 2 | **Declared Provenance** | `source_repo`, `source_tag` (`v{version}`), and 40-char `source_commit` fields. |
| 3 | **Publication Authenticity** | Detached Ed25519 signature `EXPORT-MANIFEST.json.sig` verified via `--trusted-pub-key` (zero self-reference). |
| 4 | **Reproducibility** | Bit-for-bit deterministic re-export from the same `--source-commit`. |
| 5 | **Functional Conformance** | Shared CC0 normative vectors and cross-satellite integration tests in C11, Python, and JavaScript. |

## Dependencies

{deps_en}

## Contents

{content_en}

## Offline usage

No network, accounts, package registries, or frameworks required:

{usage_en}

## Verification

With Python ≥ 3.9 and `reuse` installed:

```bash
reuse lint                                    # licensing 100 %
{verify_extra}
```

From `{source}`, full integrity and (optionally) detached-signature authenticity are verified with:

```bash
python3 tools/export_module.py --verify-existing /path/to/{name}
# With cryptographic verification of EXPORT-MANIFEST.json.sig:
python3 tools/export_module.py --verify-existing /path/to/{name} --trusted-pub-key /path/to/release-pub.pem
```

## Synchronisation contract with `{source}`

This package is **generated, never hand-edited**: it is regenerated
byte for byte from `{source} v{version}` with
`python3 tools/export_module.py --module {name} --out <dir>`. The
normative source of truth (specifications, CC0 vectors, reference
cores for the three platforms, and the full test suite) stays in
`{source}`; `verared/{name}` satellites consume it and never fork the
arithmetic. Updates flow by regenerating the export from a tag of the
base repository — never by editing exported files.
"""

GST_CRYPTO_SECTION_ES = """
### Perfil criptográfico normativo (`GST v2`)

| Aspecto | Declaración normativa |
|---|---|
| **Algoritmo normativo (`GST v2`)** | Firma híbrida **Ed25519 + ML-DSA** sobre payload canonicalizado con **RFC 8785 (JCS)** (enteros estrictamente dentro de IEEE-754 `binary64` `±(2^53 - 1)`), separación de dominio `GUS3-GST-V2`, descriptor de algoritmos y claves incluido en los bytes firmados (protección **anti-downgrade**), `KeyRegistry` con vigencia/rotación/revocación, contador monotónico `seq` + `nonce` con `SQLiteReplayStore` / `ReplayGuard` *fail-closed* y notario Merkle diario opcional. |
| **Algoritmo deprecado / educativo** | `WOTS+` / `WotsMerkleSigner`, aislado en `src/gerarion/deprecated/hashots.py` de `verared/gerarion` con `DeprecationWarning` explícito; **fuera** del perfil normativo `GST v2`. |
| **Cobertura y límite de auditoría** | Cubierto por vectores y pruebas (JCS, verificación dual, anti-downgrade, `KeyRegistry`, `SQLiteReplayStore` concurrente, integración de satélites). Pendiente de **auditoría criptográfica externa independiente** y **custodia TPM/HSM** antes de producción. |
"""

GST_CRYPTO_SECTION_EN = """
### Normative Cryptographic Profile (`GST v2`)

| Aspect | Normative declaration |
|---|---|
| **Normative algorithm (`GST v2`)** | Hybrid **Ed25519 + ML-DSA** over **RFC 8785 (JCS)** canonicalised payload (integers strictly within IEEE-754 `binary64` `±(2^53 - 1)`), domain separation `GUS3-GST-V2`, algorithm and key descriptors included in signed bytes (**anti-downgrade**), `KeyRegistry` with validity/rotation/revocation, monotonic counter `seq` + `nonce` with fail-closed `SQLiteReplayStore` / `ReplayGuard`, and optional daily Merkle notary. |
| **Deprecated / educational algorithm** | `WOTS+` / `WotsMerkleSigner`, isolated in `src/gerarion/deprecated/hashots.py` of `verared/gerarion` with explicit `DeprecationWarning`; **outside** the normative `GST v2` profile. |
| **Test coverage & audit boundary** | Covered by vectors and tests (JCS, dual verification, anti-downgrade, `KeyRegistry`, concurrent `SQLiteReplayStore`, satellite integration). **Independent third-party cryptographic audit** and **TPM/HSM key custody** are required before production security decisions. |
"""

CMS_QUICKSTART_ES = """
## Integra `gt-core` + `gt-gst` en 1 minuto (Guía rápida CMS / API)

```python
import hashlib
from gerarion.core import format as fmt
from gerarion.gst import HybridSigner, v2

# 1. Inicializar firmante híbrido (Ed25519 + ML-DSA-65), registro de claves y ReplayStore SQLite
signer = HybridSigner(seed_classical=bytes(range(32)), seed_pqc=bytes(range(32, 64)))
registry = v2.KeyRegistry()
registry.register_signer(issuer="cms.example.org", kid="cms-2026-k1", signer=signer)
replay_store = v2.SQLiteReplayStore(":memory:")  # En producción: "/var/lib/cms/gst_replay.sqlite3"

# 2. Sellar un evento de negocio sobre coordenada canónica GUS
event_bytes = b\'{"action":"post.publish","object_id":"art-42","version":1}\'
event_hash = "sha256:" + hashlib.sha256(event_bytes).hexdigest()
envelope = v2.create(
    fmt.parse("2031DY-03-08-T-09:30:00-SC-TCJ+0"),
    signer,
    event_hash=event_hash,
    issuer="cms.example.org",
    kid="cms-2026-k1",
    seq=1,
)

# 3. Verificar en 3 niveles independientes (Criptografía, Identidad/Replay, Aseguramiento Temporal)
res = v2.verify(envelope, trust_store=registry, replay_store=replay_store)
assert res.crypto.valid is True
assert res.identity.valid is True and res.identity.key_status == "ACTIVE"
assert res.identity.replay_status == "OK"
assert res.temporal.clock_state == "UNKNOWN"  # O "VERIFIED" al pasar una lectura de gt-gts
assert res.overall_trusted is True
```
"""

CMS_QUICKSTART_EN = """
## Integrate `gt-core` + `gt-gst` in 1 Minute (CMS / API Quickstart)

```python
import hashlib
from gerarion.core import format as fmt
from gerarion.gst import HybridSigner, v2

# 1. Initialize hybrid signer (Ed25519 + ML-DSA-65), key trust registry, and SQLite ReplayStore
signer = HybridSigner(seed_classical=bytes(range(32)), seed_pqc=bytes(range(32, 64)))
registry = v2.KeyRegistry()
registry.register_signer(issuer="cms.example.org", kid="cms-2026-k1", signer=signer)
replay_store = v2.SQLiteReplayStore(":memory:")  # In production: "/var/lib/cms/gst_replay.sqlite3"

# 2. Seal a business event on a canonical GUS coordinate
event_bytes = b\'{"action":"post.publish","object_id":"art-42","version":1}\'
event_hash = "sha256:" + hashlib.sha256(event_bytes).hexdigest()
envelope = v2.create(
    fmt.parse("2031DY-03-08-T-09:30:00-SC-TCJ+0"),
    signer,
    event_hash=event_hash,
    issuer="cms.example.org",
    kid="cms-2026-k1",
    seq=1,
)

# 3. Verify across 3 independent levels (Cryptography, Identity/Replay, Temporal Assurance)
res = v2.verify(envelope, trust_store=registry, replay_store=replay_store)
assert res.crypto.valid is True
assert res.identity.valid is True and res.identity.key_status == "ACTIVE"
assert res.identity.replay_status == "OK"
assert res.temporal.clock_state == "UNKNOWN"  # Or "VERIFIED" when passing a gt-gts ClockReading
assert res.overall_trusted is True
```
"""


def _deps_text(spec: ModuleSpec, lang: str, version: Optional[str] = None) -> str:
    ver = version or _read_project_version()
    if not spec.deps:
        return ("- **Ninguna externa: 100 % standalone.** Puede adoptarse "
                "aisladamente, sin el resto de la suite."
                if lang == "es"
                else "- **None: 100 % standalone.** May be adopted "
                "independently from the rest of the suite.")
    lines = []
    for d in spec.deps:
        lines.append(f"- `{d}` (*verared/{d}*): " + (
            "tipos base y servicios del núcleo."
            if d == "gt-core" and lang == "es" else
            "base types and core services."
            if d == "gt-core" else
            "módulo hermano de esta suite."
            if lang == "es" else
            "sibling module of this suite."))
    if lang == "es":
        lines.append("Base común: `verared/gerarion` `v{}`.".format(ver))
    else:
        lines.append("Common base: `verared/gerarion` `v{}`.".format(ver))
    if spec.name == "gt-gts":
        lines.append(
            "- *Nota:* el perfil Roughtime (experimental) importa "
            "`gerarion.interop` (gt-interop) para el perfil GUS-3339."
            if lang == "es" else
            "- *Note:* the experimental Roughtime profile imports "
            "`gerarion.interop` (gt-interop) for the GUS-3339 profile.")
    return "\n".join(lines)


def _content_text(spec: ModuleSpec, text_es: str, text_en: str) -> str:
    return text_es if text_es else text_en


def _listing(rel: Path, is_dir: bool) -> str:
    kind = " (directorio)" if is_dir else ""
    en_kind = " (directory)" if is_dir else ""
    if rel.suffix == ".json":
        why = " — vectores de prueba CC0" if rel.name != ".gitkeep" else ""
        why_en = " — CC0 test vectors" if rel.name != ".gitkeep" else ""
    elif rel.suffix in (".md",):
        why = " — especificación/documentación (CC-BY-4.0)"
        why_en = " — specification/documentation (CC-BY-4.0)"
    elif rel.suffix in CODE_SUFFIXES or rel.name in ("Makefile", "LICENSE", "NOTICE"):
        why = " — código/licencia (MIT OR Apache-2.0)" if rel.name not in ("LICENSE", "NOTICE") else ""
        why_en = " — code/license (MIT OR Apache-2.0)" if rel.name not in ("LICENSE", "NOTICE") else ""
    else:
        why = ""
        why_en = ""
    return f"- `{rel.as_posix()}`{kind}{why}" if is_dir or why else f"- `{rel.as_posix()}`"


# ---------------------------------------------------------------------------
# Referencias internas / huérfanas
# ---------------------------------------------------------------------------

JS_IMPORT_RE = re.compile(
    r"""(?:from\s+|import\s*\(\s*|import\s+)['"](\.[^'"]+)['"]""",
)


def _external_import_roots(export_dir: Path) -> List[str]:
    """Primer componente de los imports relativos que no resuelven
    dentro del propio export (referencias a módulos de otros dominios
    o a código no exportado)."""
    missing = []
    for path in sorted(export_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(export_dir)
        if rel.parts[0] not in ("src", "web"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix == ".py":
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or node.level == 0:
                    continue
                # nivel 1 = mismo directorio; subir (level-1) desde rel.parent
                base = rel.parent
                for _ in range(node.level - 1):
                    base = base.parent
                if node.module:
                    candidate = base.joinpath(*node.module.split("."))
                else:
                    candidate = base
                if not (
                    (export_dir / candidate.parent / (candidate.name + ".py")).exists()
                    or (export_dir / candidate / "__init__.py").exists()
                    or (export_dir / (candidate.parent.name + ".py")).exists()
                ):
                    root = node.module.split(".")[0] if node.module else "."
                    missing.append(root)
        elif path.suffix == ".mjs":
            for m in JS_IMPORT_RE.finditer(text):
                target = (rel.parent / m.group(1)).resolve()
                if not target.exists():
                    missing.append(Path(m.group(1)).parts[0].lstrip("./"))
        else:
            # C: #include "..." relativos
            for m in re.finditer(r'#include\s+"([^"]+)"', text):
                target = (rel.parent / m.group(1)).resolve()
                if not target.exists() and not m.group(1).startswith("../core"):
                    missing.append(m.group(1))
                elif not target.exists():
                    missing.append(m.group(1).split("/")[1] if "/" in m.group(1) else m.group(1))
    return sorted(set(missing))


# ---------------------------------------------------------------------------
# Exportación
# ---------------------------------------------------------------------------


def _is_git_internal(rel: Path) -> bool:
    return ".git" in rel.parts


def _clear_export_dir_preserving_git(export: Path) -> None:
    if not export.exists():
        export.mkdir(parents=True)
        return
    for child in list(export.iterdir()):
        if child.name == ".git":
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def _copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def _format_gt_core_makefile(version: str) -> str:
    parts = version.split(".")
    major = parts[0] if len(parts) > 0 else "3"
    minor = parts[1] if len(parts) > 1 else "2"
    patch = parts[2] if len(parts) > 2 else "0"
    text = GT_CORE_MAKEFILE
    text = text.replace("{source}", SOURCE_REPO)
    text = text.replace("{version}", version)
    text = text.replace("{date}", "2026-11-19")
    text = re.sub(r"(?m)^MAJOR = \d+$", f"MAJOR = {major}", text)
    text = re.sub(r"(?m)^MINOR = \d+$", f"MINOR = {minor}", text)
    text = re.sub(r"(?m)^PATCH = \d+$", f"PATCH = {patch}", text)
    return text


def _format_gt_core_smoke_c(version: str) -> str:
    return (
        GT_CORE_SMOKE_C
        .replace("{source}", SOURCE_REPO)
        .replace("{version}", version)
    )


def _collect_export_hashes(export: Path) -> Dict[str, str]:
    """Mapa ordenado alfabéticamente ruta_relativa -> sha256 de todos los
    archivos exportados (excluyendo EXPORT-MANIFEST.json, EXPORT-MANIFEST.json.sig y .git/**)."""
    hashes: Dict[str, str] = {}
    for p in sorted(export.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(export)
        if _is_git_internal(rel):
            continue
        posix = rel.as_posix()
        if posix in (MANIFEST_FILENAME, MANIFEST_SIG_FILENAME):
            continue
        hashes[posix] = _sha256_file(p)
    return dict(sorted(hashes.items()))


def sign_manifest(export_dir: Path, sign_key_source: str) -> Path:
    """Firma los bytes exactos de EXPORT-MANIFEST.json con Ed25519 y escribe
    el archivo separado EXPORT-MANIFEST.json.sig (sin autorreferencia)."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    manifest_path = export_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise FileNotFoundError(f"No existe {manifest_path} para firmar")
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()

    key_path = Path(sign_key_source)
    if not sign_key_source.lstrip().startswith("-----BEGIN") and key_path.is_file():
        pem_bytes = key_path.read_bytes()
    else:
        pem_bytes = sign_key_source.encode("utf-8")

    priv = serialization.load_pem_private_key(pem_bytes, password=None)
    if not isinstance(priv, Ed25519PrivateKey):
        raise TypeError("La clave de firma de manifiesto debe ser Ed25519 (PEM)")

    sig_bytes = priv.sign(manifest_bytes)
    pub_raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    key_id = hashlib.sha256(pub_raw).hexdigest()[:16]

    sig_doc = {
        "schema": MANIFEST_SIG_SCHEMA,
        "algorithm": "Ed25519",
        "manifest_sha256": manifest_sha256,
        "key_id": key_id,
        "signature_b64": base64.b64encode(sig_bytes).decode("ascii"),
    }
    sig_path = export_dir / MANIFEST_SIG_FILENAME
    sig_path.write_text(json.dumps(sig_doc, indent=2) + "\n", encoding="utf-8")
    return sig_path


def verify_manifest_signature(
    export_dir: Path,
    trusted_pub_key_source: Union[str, Path],
) -> Tuple[bool, str]:
    """Verifica criptográficamente EXPORT-MANIFEST.json.sig contra EXPORT-MANIFEST.json."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    manifest_path = export_dir / MANIFEST_FILENAME
    sig_path = export_dir / MANIFEST_SIG_FILENAME
    if not manifest_path.is_file():
        return False, f"falta {MANIFEST_FILENAME}"
    if not sig_path.is_file():
        return False, f"falta {MANIFEST_SIG_FILENAME}"

    try:
        sig_doc = json.loads(sig_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return False, f"{MANIFEST_SIG_FILENAME} JSON inválido: {exc}"

    if not isinstance(sig_doc, dict) or sig_doc.get("schema") != MANIFEST_SIG_SCHEMA:
        return False, f"schema inesperado en {MANIFEST_SIG_FILENAME}: {sig_doc.get('schema') if isinstance(sig_doc, dict) else None!r}"
    if sig_doc.get("algorithm") != "Ed25519":
        return False, f"algoritmo no soportado en {MANIFEST_SIG_FILENAME}: {sig_doc.get('algorithm')!r}"

    manifest_bytes = manifest_path.read_bytes()
    actual_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if sig_doc.get("manifest_sha256") != actual_sha256:
        return False, "manifest_sha256 en .sig no coincide con EXPORT-MANIFEST.json"

    try:
        if isinstance(trusted_pub_key_source, Path):
            pub_pem = trusted_pub_key_source.read_bytes()
        elif not str(trusted_pub_key_source).lstrip().startswith("-----BEGIN") and Path(str(trusted_pub_key_source)).is_file():
            pub_pem = Path(str(trusted_pub_key_source)).read_bytes()
        else:
            pub_pem = str(trusted_pub_key_source).encode("utf-8")
        pub = serialization.load_pem_public_key(pub_pem)
        if not isinstance(pub, Ed25519PublicKey):
            return False, "la clave pública confiable no es Ed25519"
        sig_bytes = base64.b64decode(sig_doc["signature_b64"], validate=True)
        pub.verify(sig_bytes, manifest_bytes)
    except Exception as exc:  # noqa: BLE001
        return False, f"firma Ed25519 inválida: {exc}"

    return True, f"EXPORT-MANIFEST.json.sig verificada (key_id={sig_doc.get('key_id')})"


def export_module(spec: ModuleSpec, out_dir: Path,
                  include_large_vectors: bool = True,
                  source_commit: Optional[str] = None,
                  sign_key: Optional[str] = None) -> List[str]:
    """Exporta `spec` a `<out_dir>/<spec.name>`; devuelve la lista de
    archivos escritos (rutas relativas al export)."""
    global GERARION_VERSION
    version = _read_project_version()
    GERARION_VERSION = version
    commit = _resolve_source_commit(source_commit)
    export = out_dir / spec.name
    _clear_export_dir_preserving_git(export)
    written: List[str] = []

    def rel_add(p: Path) -> None:
        written.append(p.relative_to(export).as_posix())

    # 1. código: archivos individuales y directorios enteros
    for f in spec.files:
        _copy_file(REPO_ROOT / f, export / f)
        rel_add(export / f)
    for d in spec.dirs:
        shutil.copytree(REPO_ROOT / d, export / d)
        for chain in sorted((export / d).rglob("*")):
            if chain.is_file():
                rel_add(chain)

    # 2. vectores
    vectors = list(spec.vectors)
    if include_large_vectors:
        vectors += list(spec.large_vectors)
    for v in vectors:
        _copy_file(REPO_ROOT / v, export / v)
        rel_add(export / v)

    # 3. documentación
    for doc in spec.docs:
        _copy_file(REPO_ROOT / doc, export / doc)
        rel_add(export / doc)

    # 4. andamiaje de módulos experimentales
    if spec.scaffold:
        for sub in ("src", "tests", "vectors"):
            (export / sub).mkdir(exist_ok=True)
            keep = export / sub / ".gitkeep"
            keep.touch()
            rel_add(keep)

    # 5. extras específicos de gt-core (Makefile standalone)
    if spec.name == "gt-core":
        (export / "impl-c" / "Makefile").write_text(
            _format_gt_core_makefile(version), encoding="utf-8"
        )
        (export / "impl-c" / "gerarion-core.pc.in").write_text(
            GT_CORE_PC_IN.replace("${{", "${").replace("}}", "}"),
            encoding="utf-8",
        )
        (export / "impl-c" / "smoke.c").write_text(
            _format_gt_core_smoke_c(version), encoding="utf-8"
        )
        for extra in ("impl-c/Makefile", "impl-c/gerarion-core.pc.in", "impl-c/smoke.c"):
            rel_add(export / extra)

    # 6. higiene legal (los textos de LICENSES/ se copian al final, según uso)
    _copy_file(REPO_ROOT / "LICENSE", export / "LICENSE")
    rel_add(export / "LICENSE")
    _copy_file(REPO_ROOT / "NOTICE", export / "NOTICE")
    rel_add(export / "NOTICE")

    # 7. README bilingüe de entrada (antes del REUSE.toml: debe quedar cubierto)
    specs = ", ".join(f"`{d}`" for d in spec.docs) or "—"
    verify_extra = (
        "make -C impl-c smoke                          # núcleo standalone"
        if spec.core_checked
        else "# (sin código compilable en este módulo)"
        if spec.scaffold
        else "# (las pruebas viven en la suite de verared/gerarion)"
    )
    usage = "```bash\n"
    if spec.core_checked:
        usage += "make -C impl-c          # y `make -C impl-c smoke`\n"
    if any(w.startswith("src/") for w in written):
        usage += 'python3 -c \'import sys; sys.path.insert(0, "src"); import gerarion\'\n'
    usage += "```"
    files_desc = "\n".join(_tree_lines(written + [MANIFEST_FILENAME]))
    crypto_es = GST_CRYPTO_SECTION_ES if spec.name == "gt-gst" else ""
    crypto_en = GST_CRYPTO_SECTION_EN if spec.name == "gt-gst" else ""
    quickstart_es = CMS_QUICKSTART_ES if spec.name in ("gt-core", "gt-gst") else ""
    quickstart_en = CMS_QUICKSTART_EN if spec.name in ("gt-core", "gt-gst") else ""
    readme_es = README_TMPL_ES.format(
        title=spec.title_es,
        source=SOURCE_REPO,
        version=version,
        name=spec.name,
        purpose=spec.purpose_es,
        status=spec.status,
        maturity=spec.maturity,
        spec_list=specs,
        crypto_section_es=crypto_es,
        quickstart_section_es=quickstart_es,
        deps_es=_deps_text(spec, "es", version=version),
        content_es=files_desc,
        usage_es=usage,
        verify_extra=verify_extra,
    )
    readme_en = README_TMPL_EN.format(
        title=spec.title_en,
        source=SOURCE_REPO,
        version=version,
        name=spec.name,
        purpose=spec.purpose_en,
        status=spec.status,
        maturity=spec.maturity,
        spec_list=specs,
        crypto_section_en=crypto_en,
        quickstart_section_en=quickstart_en,
        deps_en=_deps_text(spec, "en", version=version),
        content_en=files_desc,
        usage_en=usage,
        verify_extra=verify_extra,
    )
    (export / "README.md").write_text(readme_en, encoding="utf-8")
    (export / "README.es.md").write_text(readme_es, encoding="utf-8")
    written.extend(["README.md", "README.es.md"])

    # 8. REUSE.toml del export (incluyendo EXPORT-MANIFEST.json* bajo CC0-1.0);
    # después, solo los textos de licencia realmente referenciados.
    used = _write_export_reuse(export, version=version)
    rel_add(export / "REUSE.toml")
    texts = set()
    for lic in used:
        if lic == "MIT OR Apache-2.0":
            texts.update({"MIT", "Apache-2.0"})  # dual: exige ambos textos
        else:
            texts.add(lic)
    (export / "LICENSES").mkdir(exist_ok=True)
    for name in sorted(texts):
        _copy_file(REPO_ROOT / "LICENSES" / f"{name}.txt", export / "LICENSES" / f"{name}.txt")
        rel_add(export / "LICENSES" / f"{name}.txt")

    # 9. (último) EXPORT-MANIFEST.json con SHA-256 de todos los demás archivos
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "module": spec.name,
        "version": version,
        "maturity": spec.maturity,
        "source_repo": SOURCE_REPO,
        "source_tag": f"v{version}",
        "source_commit": commit,
        "dependencies": {d: COMPAT_RANGE for d in sorted(spec.deps)},
        "files": _collect_export_hashes(export),
    }
    (export / MANIFEST_FILENAME).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    rel_add(export / MANIFEST_FILENAME)

    # 10. Firma separada opcional (EXPORT-MANIFEST.json.sig, nunca incluida en files)
    active_sign_key = sign_key or os.environ.get("GERARION_MANIFEST_SIGNING_KEY")
    if active_sign_key:
        sig_path = sign_manifest(export, active_sign_key)
        rel_add(sig_path)

    return written


def _tree_lines(rel_files: List[str]) -> List[str]:
    """Agrupa los archivos escritos en líneas de README legibles (es)."""
    groups: Dict[str, List[str]] = {}
    for f in rel_files:
        groups.setdefault(str(Path(f).parent if Path(f).parent != Path(".") else "."), []).append(f)
    lines = []
    for g in sorted(groups):
        items = sorted(groups[g])
        if g == "LICENSES" or len(items) > 4:
            lines.append(f"- `{g}/` ({len(items)} archivos)")
        else:
            for i in items:
                lines.append(f"- `{i}`")
    return lines


def _write_export_reuse(export: Path, version: Optional[str] = None) -> Set[str]:
    """Escribe un REUSE.toml con anotaciones override que cubren cada
    archivo del export agrupado por licencia (incluyendo EXPORT-MANIFEST.json)."""
    ver = version or _read_project_version()
    by_license: Dict[str, List[str]] = {}
    for p in sorted(export.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(export)
        if _is_git_internal(rel):
            continue
        if p.name == "REUSE.toml":
            continue
        if p.parent.name == "LICENSES" or p.name in ("LICENSE", "LICENSES"):
            # textos de licencia: autodetectados por reuse
            continue
        lic = classify_license(rel)
        if lic:
            by_license.setdefault(lic, []).append(rel.as_posix())

    # EXPORT-MANIFEST.json (y opcionalmente .sig) quedan bajo CC0-1.0
    vec_paths = by_license.setdefault(LICENSE_VECTOR, [])
    manifest_glob = f"{MANIFEST_FILENAME}*"
    if manifest_glob not in vec_paths:
        vec_paths.append(manifest_glob)
        vec_paths.sort()

    blocks = [
        "version = 1",
        "",
        f"# Export generado por tools/export_module.py (fuente: verared/gerarion v{ver}).",
        "# Cobertura completa del paquete (precedencia override).",
    ]
    used_licenses: Set[str] = set()
    header_by_lic = {
        LICENSE_CODE: "code",
        LICENSE_DOC: "docs",
        LICENSE_VECTOR: "vectors + manifest + andamiaje",
    }
    for lic in (LICENSE_CODE, LICENSE_DOC, LICENSE_VECTOR):
        paths = by_license.get(lic)
        if not paths:
            continue
        blocks.append(f"\n# {header_by_lic[lic]} — {lic}\n")
        blocks.append("[[annotations]]")
        blocks.append('precedence = "override"')
        blocks.append("path = [" + ", ".join(f'"{p}"' for p in paths) + "]")
        blocks.append(f'SPDX-License-Identifier = "{lic}"')
        blocks.append('SPDX-FileCopyrightText = "2026 verared contributors"')
        used_licenses.add(lic)
    (export / "REUSE.toml").write_text("\n".join(blocks) + "\n", encoding="utf-8")
    return used_licenses


# ---------------------------------------------------------------------------
# Verificación integrada
# ---------------------------------------------------------------------------


def verify_manifest(export_dir: Path) -> Tuple[bool, str, Optional[dict]]:
    """Valida EXPORT-MANIFEST.json: existencia, esquema, ausencia de archivos
    faltantes o sobrantes y coincidencia exacta SHA-256."""
    manifest_path = export_dir / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return False, f"falta {MANIFEST_FILENAME} en {export_dir}", None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"{MANIFEST_FILENAME} inválido: {exc}", None

    if manifest.get("schema") != MANIFEST_SCHEMA:
        return False, f"schema inesperado en {MANIFEST_FILENAME}: {manifest.get('schema')!r}", manifest
    expected_files = manifest.get("files")
    if not isinstance(expected_files, dict) or not expected_files:
        return False, f"{MANIFEST_FILENAME} sin mapa 'files' válido", manifest

    actual_files = _collect_export_hashes(export_dir)
    expected_keys = set(expected_files.keys())
    actual_keys = set(actual_files.keys())

    missing = sorted(expected_keys - actual_keys)
    extra = sorted(actual_keys - expected_keys)
    mismatched = sorted(
        k for k in (expected_keys & actual_keys)
        if actual_files[k] != expected_files[k]
    )

    errors = []
    if missing:
        errors.append(f"archivos faltantes ({len(missing)}): {missing}")
    if extra:
        errors.append(f"archivos sobrantes ({len(extra)}): {extra}")
    if mismatched:
        errors.append(f"SHA-256 distinto ({len(mismatched)}): {mismatched}")

    if errors:
        return False, "EXPORT-MANIFEST.json falló: " + "; ".join(errors), manifest
    return True, f"EXPORT-MANIFEST.json: OK ({len(actual_files)} archivos verificados)", manifest


def verify_module(
    export_dir: Path,
    trusted_pub_key: Optional[Union[str, Path]] = None,
) -> Tuple[bool, str]:
    """Verifica EXPORT-MANIFEST.json (SHA-256 + sin faltantes/sobrantes),
    reuse lint al 100 % dentro del export, compilación limpia del núcleo
    standalone en gt-core y (si se provee --trusted-pub-key) autenticidad de
    la firma separada EXPORT-MANIFEST.json.sig. Devuelve (ok, mensaje)."""
    messages = []
    ok = True

    m_ok, m_msg, manifest = verify_manifest(export_dir)
    if m_ok:
        messages.append(f"[OK] SHA-256 Integrity — {m_msg}")
    else:
        ok = False
        messages.append(f"[FAIL] SHA-256 Integrity — {m_msg}")

    lint = subprocess.run(
        [sys.executable, "-m", "reuse", "lint", "--quiet"],
        cwd=export_dir, capture_output=True, text=True,
    )
    # --quiet no existe en todas las versiones: si falla por eso, reintentar
    if lint.returncode != 0 and "unrecognized arguments" in (lint.stderr or ""):
        lint = subprocess.run(
            [sys.executable, "-m", "reuse", "lint"],
            cwd=export_dir, capture_output=True, text=True,
        )
    if lint.returncode != 0:
        ok = False
        messages.append(
            "[FAIL] REUSE 3.3 License Compliance — reuse lint falló:\n"
            + (lint.stdout + lint.stderr)[-2000:]
        )
    else:
        messages.append("[OK] REUSE 3.3 License Compliance — reuse lint: 100 % conforme")

    mod_name = (manifest or {}).get("module") or export_dir.name
    if mod_name == "gt-core":
        make = shutil.which("make")
        cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if not make or not cc:
            return False, "make/cc no disponibles para verificar gt-core"
        build = subprocess.run(
            [make,
             "CFLAGS=-std=gnu11 -O2 -Wall -Wextra -Werror",
             "smoke"],
            cwd=export_dir / "impl-c", capture_output=True, text=True,
        )
        if build.returncode != 0:
            ok = False
            messages.append(
                "[FAIL] C11 Core Standalone Smoke — compilación del núcleo falló:\n"
                + (build.stdout + build.stderr)[-2000:]
            )
        else:
            messages.append(
                "[OK] C11 Core Standalone Smoke — make smoke: compilación limpia (-Werror) y humo OK"
            )
        clean = subprocess.run([make, "clean"], cwd=export_dir / "impl-c",
                               capture_output=True, text=True)
        if clean.returncode != 0:
            ok = False
            messages.append("make clean falló:\n" + (clean.stdout + clean.stderr)[-1000:])

    if trusted_pub_key:
        sig_ok, sig_msg = verify_manifest_signature(export_dir, trusted_pub_key)
        if sig_ok:
            messages.append(f"[OK] Detached Signature Authenticity — {sig_msg}")
        else:
            ok = False
            messages.append(f"[FAIL] Detached Signature Authenticity — {sig_msg}")
    else:
        messages.append(
            "[SKIPPED — no --trusted-pub-key provided] Detached Signature Authenticity"
        )

    return ok, "\n".join(messages)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="export_module.py",
        description="Exporta módulos normativos de verared/gerarion como paquetes autónomos verared/gt-*.",
    )
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--module", choices=sorted(MODULES),
                       help="módulo a exportar")
    group.add_argument("--all", action="store_true",
                       help="exportar los 9 módulos")
    group.add_argument("--verify-existing", metavar="DIR",
                       help="verificar un directorio satélite ya exportado (manifest + reuse + core + .sig opcional)")
    ap.add_argument("--out",
                    help="directorio base de los exports (requerido con --module o --all)")
    ap.add_argument("--verify", action="store_true",
                    help="verificar cada export (EXPORT-MANIFEST.json + reuse lint + compilación del núcleo)")
    ap.add_argument("--no-large-vectors", action="store_true",
                    help="omitir vectores grandes (p. ej. guti-calendars-001.json, ~8 MB)")
    ap.add_argument("--source-commit",
                    help="hash SHA-1 de origen para EXPORT-MANIFEST.json (por defecto git rev-parse HEAD)")
    ap.add_argument("--sign-key", metavar="PEM",
                    help="ruta a clave privada Ed25519 PEM (o GERARION_MANIFEST_SIGNING_KEY) para generar EXPORT-MANIFEST.json.sig")
    ap.add_argument("--trusted-pub-key", metavar="PEM",
                    help="ruta a clave pública Ed25519 PEM confiable para verificar EXPORT-MANIFEST.json.sig")
    args = ap.parse_args(argv)

    if args.verify_existing:
        target = Path(args.verify_existing).resolve()
        if not target.is_dir():
            print(f"ERROR: no existe el directorio {target}", file=sys.stderr)
            return 2
        ok, msg = verify_module(target, trusted_pub_key=args.trusted_pub_key)
        print(f"verify {target.name}:")
        for line in msg.splitlines():
            print(f"  {line}")
        if not ok:
            print("VERIFICACIÓN FALLIDA", file=sys.stderr)
            return 2
        return 0

    if not args.out:
        ap.error("--out es obligatorio con --module o --all")

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    names = sorted(MODULES) if args.all else [args.module]
    exit_code = 0
    for name in names:
        spec = MODULES[name]
        target = out_dir / name
        files = export_module(
            spec,
            out_dir,
            include_large_vectors=not args.no_large_vectors,
            source_commit=args.source_commit,
            sign_key=args.sign_key,
        )
        print(f"export {name} -> {target} ({len(files)} archivos)")
        if args.verify:
            ok, msg = verify_module(target, trusted_pub_key=args.trusted_pub_key)
            for line in msg.splitlines():
                print(f"  {line}")
            if not ok:
                exit_code = 2
    if exit_code:
        print("VERIFICACIÓN FALLIDA", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
