#!/usr/bin/env python3
# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Exportador modular de la suite de referencia Gerarion (v3.2.0).

Genera paquetes autónomos —uno por dominio normativo— listos para
publicarse como repositorios satélite ``verared/gt-*`` (Gerarion Time),
manteniendo intacta la matemática, los motores y los vectores congelados
de ``verared/gerarion``. La herramienta SOLO empaqueta: nunca altera el
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
import dataclasses
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
GERARION_VERSION = "3.2.0"
SOURCE_REPO = "verared/gerarion"

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
    status: str                    # "Estable" | "EXPERIMENTAL"
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
            status="Estable (GST v2)",
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

- **{status}** — línea base `v{version}` (aritmética y vectores
  congelados: GUS v3.0.0).
- Especificación(es) incluida(s): {spec_list}

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

- **{status}** — baseline `v{version}` (frozen arithmetic and vectors:
  GUS v3.0.0).
- Included specification(s): {spec_list}

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


def _deps_text(spec: ModuleSpec, lang: str) -> str:
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
            if d == "gt-core" else
            "módulo hermano de esta suite."
            if lang == "es" else
            "sibling module of this suite."))
    if lang == "es":
        lines.append("Base común: `verared/gerarion` `v{}`.".format(GERARION_VERSION))
    else:
        lines.append("Common base: `verared/gerarion` `{}`.".format(GERARION_VERSION))
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


def _copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def export_module(spec: ModuleSpec, out_dir: Path,
                  include_large_vectors: bool = True) -> List[str]:
    """Exporta `spec` a `<out_dir>/<spec.name>`; devuelve la lista de
    archivos escritos (rutas relativas al export)."""
    export = out_dir / spec.name
    if export.exists():
        shutil.rmtree(export)
    export.mkdir(parents=True)
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
        date = "2026-11-19"
        (export / "impl-c" / "Makefile").write_text(GT_CORE_MAKEFILE)
        (export / "impl-c" / "gerarion-core.pc.in").write_text(GT_CORE_PC_IN)
        (export / "impl-c" / "smoke.c").write_text(GT_CORE_SMOKE_C)
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
    files_desc = "\n".join(_tree_lines(written))
    readme_es = README_TMPL_ES.format(
        title=spec.title_es,
        source=SOURCE_REPO,
        version=GERARION_VERSION,
        name=spec.name,
        purpose=spec.purpose_es,
        status=spec.status,
        spec_list=specs,
        deps_es=_deps_text(spec, "es"),
        content_es=files_desc,
        usage_es=usage,
        verify_extra=verify_extra,
    )
    readme_en = README_TMPL_EN.format(
        title=spec.title_en,
        source=SOURCE_REPO,
        version=GERARION_VERSION,
        name=spec.name,
        purpose=spec.purpose_en,
        status=spec.status,
        spec_list=specs,
        deps_en=_deps_text(spec, "en"),
        content_en=files_desc,
        usage_en=usage,
        verify_extra=verify_extra,
    )
    (export / "README.md").write_text(readme_en)
    (export / "README.es.md").write_text(readme_es)
    written.extend(["README.md", "README.es.md"])

    # 8. (último) REUSE.toml del export: cubre el 100 % de los archivos;
    # después, solo los textos de licencia realmente referenciados.
    used = _write_export_reuse(export)
    rel_add(export / "REUSE.toml")
    texts = set()
    for lic in used:
        if lic == "MIT OR Apache-2.0":
            texts.update({"MIT", "Apache-2.0"})  # dual: exige ambos textos
        else:
            texts.add(lic)
    (export / "LICENSES").mkdir()
    for name in sorted(texts):
        _copy_file(REPO_ROOT / "LICENSES" / f"{name}.txt", export / "LICENSES" / f"{name}.txt")
        rel_add(export / "LICENSES" / f"{name}.txt")

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


def _write_export_reuse(export: Path) -> None:
    """Escribe un REUSE.toml con anotaciones override que cubren cada
    archivo del export agrupado por licencia."""
    by_license: Dict[str, List[str]] = {}
    for p in sorted(export.rglob("*")):
        if not p.is_file() or p.name == "REUSE.toml":
            continue
        if p.parent.name == "LICENSES" or p.name in ("LICENSE", "LICENSES"):
            # textos de licencia: autodetectados por reuse
            continue
        lic = classify_license(p.relative_to(export))
        if lic:
            by_license.setdefault(lic, []).append(p.relative_to(export).as_posix())

    blocks = [
        "version = 1",
        "",
        f"# Export generado por tools/export_module.py (fuente: verared/gerarion v{GERARION_VERSION}).",
        "# Cobertura completa del paquete (precedencia override).",
    ]
    used_licenses = set()
    header_by_lic = {
        LICENSE_CODE: "code",
        LICENSE_DOC: "docs",
        LICENSE_VECTOR: "vectors + andamiaje",
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
    (export / "REUSE.toml").write_text("\n".join(blocks) + "\n")
    return used_licenses


# ---------------------------------------------------------------------------
# Verificación integrada
# ---------------------------------------------------------------------------


def verify_module(export_dir: Path) -> Tuple[bool, str]:
    """reuse lint al 100 % dentro del export y, para gt-core, compilación
    limpia del núcleo standalone. Devuelve (ok, mensaje)."""
    messages = []
    ok = True

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
        messages.append("reuse lint falló:\n" + (lint.stdout + lint.stderr)[-2000:])
    else:
        messages.append("reuse lint: 100 % conforme")

    if export_dir.name == "gt-core":
        make = shutil.which("make")
        cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if not make or not cc:
            return False, "make/cc no disponibles para verificar gt-core"
        # -std=gnu11 (no c11+pedantic): el guardia interno de 128 bits del
        # núcleo congelado usa __int128, extensión GNU; GCC la marca como
        # aviso pedantic ISO incluso en gnu11 y la aritmética NO es
        # editable desde esta herramienta. El gate estricto compila con
        # -Werror sobre todos los avisos estándar (-Wall -Wextra); la
        # conformancia pedantic estricta del núcleo la cubre la batería
        # audit/conformance del repositorio base.
        build = subprocess.run(
            [make,
             "CFLAGS=-std=gnu11 -O2 -Wall -Wextra -Werror",
             "smoke"],
            cwd=export_dir / "impl-c", capture_output=True, text=True,
        )
        if build.returncode != 0:
            ok = False
            messages.append("compilación del núcleo falló:\n" + (build.stdout + build.stderr)[-2000:])
        else:
            messages.append("make smoke: compilación limpia (-Werror) y humo OK")
        clean = subprocess.run([make, "clean"], cwd=export_dir / "impl-c",
                               capture_output=True, text=True)
        if clean.returncode != 0:
            ok = False
            messages.append("make clean falló:\n" + (clean.stdout + clean.stderr)[-1000:])

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
    ap.add_argument("--out", required=True,
                    help="directorio base de los exports (uno por módulo)")
    ap.add_argument("--verify", action="store_true",
                    help="verificar cada export (reuse lint + compilación del núcleo)")
    ap.add_argument("--no-large-vectors", action="store_true",
                    help="omitir vectores grandes (p. ej. guti-calendars-001.json, ~8 MB)")
    args = ap.parse_args(argv)

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    names = sorted(MODULES) if args.all else [args.module]
    exit_code = 0
    for name in names:
        spec = MODULES[name]
        target = out_dir / name
        files = export_module(spec, out_dir,
                              include_large_vectors=not args.no_large_vectors)
        print(f"export {name} -> {target} ({len(files)} archivos)")
        if args.verify:
            ok, msg = verify_module(target)
            for line in msg.splitlines():
                print(f"  {line}")
            if not ok:
                exit_code = 2
    if exit_code:
        print("VERIFICACIÓN FALLIDA", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
