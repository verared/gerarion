<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- SPDX-FileCopyrightText: 2026 verared contributors -->

# Preparación de Gerarion v3.4.0 y dry-run de satélites

Fecha: 2026-11-27. Ejecución local en pcitri: Python 3.12.3,
Node 24.22.3, npm 11.21.3. Rama: `release/v3.4.0`.

## Origen y alcance

- Main inicial limpio: `9056f9b` (PR #37, Trusted Publishing).
- Base comparada: `7d4bf95f29956888f6f19590ae2b024125828d12` (`v3.3.0`).
- Commit de preparación validado y exportado:
  `b81a5c6ea373f897a4c2dc1f27942689cb391aad`.
- Versiones de distribución actualizadas a 3.4.0: `pyproject.toml`,
  `src/gerarion/__init__.py`, `web/package.json`, macros de `impl-c/gerarion.h`,
  `impl-c/Makefile` (también corrige pkg-config, antes en 3.1.0),
  `CITATION.cff`, `sbom.cdx.json`, matriz JSON/Markdown y documentación vigente.
- `CHANGELOG.md` documenta los cambios desde la base: bordes temporales,
  expected_nonce/HOLDOVER, contrato GST sealed/anchored, event_hash exacto,
  paquete npm experimental y cambios de seguridad/CI.
- Se conservan las referencias históricas a 3.3.0: changelog, fixtures de
  pruebas, línea base auditada y publicación previa en roadmap/README.
- `GUS v3.0.0`, vectores y versión independiente del paquete
  `@verared/gerarion-time@0.1.0-alpha.1` permanecen iguales.
- Las instrucciones de consumo del tag objetivo señalan que la
  sincronización de los tags satélite requiere la Fase B posterior.

## Qué ejecuta release.yml al empujar v3.4.0

El workflow se dispara por `push.tags: ["v*"]` o manualmente. Usa Python
3.13 y Node 20 en GitHub Actions (distintos del entorno local de esta prueba).

1. Construye wheel y sdist Python.
2. Empaqueta `gerarion-kernel` desde `web/` con `npm pack`.
3. Compila y ejecuta conformancia C; genera bibliotecas estáticas/compartidas,
   cabeceras y pkg-config, con tarballs linux-x86_64 de la suite y del core.
4. Ejecuta `tools/export_module.py --all --out /tmp/release-satellites --verify`
   y genera `SHA256SUMS.txt` de los artefactos.
5. Con tag, crea la GitHub Release y sube wheel, sdist, tarball JS,
   tarballs C y SHA256SUMS. En ejecución manual, sube artefactos del workflow.

**No hace commits, pushes ni tags en gt-*.** Los exports temporales se
verifican, pero ni estos árboles ni sus manifiestos se adjuntan a la Release.
No publica en PyPI ni npm. El paquete npm experimental tiene su propio
workflow, disparado por `gerarion-time-v*`, no por `v3.4.0`.
La Fase B requiere exportar desde el tag definitivo con
`tools/export_module.py` desde pcitri y sincronizar los repositorios
satélite en una operación posterior autorizada.

## Exportador: interfaz y garantías

- Selección excluyente: `--module <gt-*>`, `--all`, `--verify-existing <dir>`.
- Opciones: `--out`, `--verify`, `--no-large-vectors`, `--source-commit`,
  `--sign-key`, `--trusted-pub-key`.
- Copia código, especificaciones y vectores de cada dominio. Genera
  README bilingüe, LICENSE/NOTICE, LICENSES usadas, REUSE.toml y
  EXPORT-MANIFEST.json (versión, procedencia, dependencias y SHA-256 de archivos).
  gt-core añade Makefile, plantilla pkg-config y smoke C; los módulos
  experimentales incluyen scaffold src/tests/vectors.
- Firma detached Ed25519 opcional: `--sign-key` o
  `GERARION_MANIFEST_SIGNING_KEY` genera EXPORT-MANIFEST.json.sig.
  `--trusted-pub-key` activa su comprobación; no es requisito para exportar.
- Este dry-run comprueba integridad y licencias; autenticidad detached
  aparece como **SKIPPED**, sin clave de firma ni clave pública suministradas.
- `--verify` también compila y limpia el smoke de gt-core con `-Werror`.

## Resultado de las suites

| Validación local | Resultado |
|---|---|
| `python -m pytest tests/ -q -rs -p no:cacheprovider` | 349 passed, 1 skipped; 41 avisos de deprecación |
| `node web/test/tests.mjs` | 36/36 |
| `node web/test/conformance.mjs` | 7 categorías, 0 fallos |
| `node web/test/profiles-conformance.mjs` | 13 vectores + 3 canónicos + 17 negativos, 0 fallos |
| `node web/test/regression-conformance.mjs` | 8 casos, 0 fallos |
| `node --test web/test/p0-time-boundaries.mjs` | 4/4 |
| `node web/test/guti_vectors.mjs` | 127.204/127.204 |
| `node web/test/calendars.test.mjs` | 42/42 |
| `node --test tests/atlas.test.mjs` | 40/40 |
| Paquete npm: `npm ci`, build, check:pure, test | Instalación limpia; build OK; 0 imports node:*; 24/24 tests, incluido tarball |
| `make -C impl-c conformance` | 11 categorías sin fallos; GUTI 63.850/63.850 |
| `reuse lint` del candidato | 266/266 archivos, 100% conforme |
| Coherencia de versiones y `git diff --check` | OK |

La única omisión Python es prevista: con slh-dsa instalado, la firma del
fixture de referencia no es SLH-DSA; los tests de adaptadores cubren su
rechazo de dominio. En el primer intento faltaba make/cc en PATH; se
habilitó el toolchain existente dentro de `.git/` (GNU Make 4.3, Zig
0.15.2/Clang 20.1.2, con assertions activas) y la suite completa pasó.
No se necesitaron instalaciones globales.

## Dry-run de los nueve satélites

Se extrajo la base con `git archive 7d4bf95` a un directorio temporal y se
exportó con su propio exportador. Después se ejecutó el exportador candidato
con `--all --verify`, sin omitir vectores grandes, y se repitió la exportación.
Se compararon SHA-256 y conjuntos de archivos, se comprobó versión 3.4.0,
source_tag v3.4.0 y source_commit exacto del candidato, y se verificó que
los manifiestos repetidos fueran idénticos byte a byte. Se volvieron a
comprobar los hashes tras limpiar el smoke C.

| Satélite | Archivos en manifest | Manifest / REUSE / determinismo | Diferencia funcional frente a v3.3.0 |
|---|---:|---|---|
| gt-calendar | 22 | OK / OK / OK | Ninguna; solo metadata/README |
| gt-core | 25 | OK / OK / OK; smoke C OK | `web/engine/core.mjs` |
| gt-gcerts | 12 | OK / OK / OK | Ninguna; solo metadata/README |
| gt-gst | 22 | OK / OK / OK | `src/gerarion/gst/envelope.py`, `src/gerarion/gst/v2.py` |
| gt-gts | 16 | OK / OK / OK | `impl-c/clock/gus_clock.c`, `src/gerarion/gts/clock.py`, `src/gerarion/gts/roughtime.py` |
| gt-gus | 19 | OK / OK / OK | `web/engine/core.mjs` |
| gt-interop | 16 | OK / OK / OK | Ninguna; solo metadata/README |
| gt-tcj | 17 | OK / OK / OK | `impl-c/tai/gus_tai.c`, `src/gerarion/tcj/tai.py`, `web/engine/tcj-tai.mjs` |
| gt-tslr | 12 | OK / OK / OK | Ninguna; solo metadata/README |

Todos actualizan EXPORT-MANIFEST.json, README.md, README.es.md y REUSE.toml.
gt-core también actualiza versión/comentarios del Makefile y del smoke C
generados; gt-gst actualiza especificaciones GST y modelos de amenazas EN/ES.
Los cuatro módulos sin cambios funcionales conservan código, vectores y
especificaciones idénticos; pueden consumir fixes de sus dependencias
cuando se ensamblan con los demás satélites.

El árbol `/tmp/gt-export-dryrun-ayknp1gm` (base, candidato y repetición)
fue eliminado al finalizar y se comprobó su ausencia. No se escribieron
checkouts locales de satélites ni otros proyectos; no se creó el tag
v3.4.0 ni se empujó main.

## Revisión

[Abrir PR release/v3.4.0 → main](https://github.com/verared/gerarion/compare/main...release/v3.4.0?expand=1).
