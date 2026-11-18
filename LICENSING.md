# LICENSING.md — Arquitectura de licencias del repositorio

> Este documento es la tabla de referencia única del licenciamiento por
> capa. Compleméntalo con `REUSE.toml` (asignación archivo por archivo,
> conforme a [REUSE](https://reuse.software/spec/) / [SPDX](https://spdx.org/))
> y los textos íntegros en `LICENSES/`.

## Tabla por capa

| Capa | Rutas | SPDX-License-Identifier | Aviso |
|---|---|---|---|
| **Código propio** (SDK Python, kernel JS, C11, portal web, CLI, tests, scripts, `deploy/**`, `.github/**`) | `src/**`, `web/*.{mjs,js,html,css}`, `web/tests*.mjs`, `web/conformance.mjs`, `web/profiles-conformance.mjs`, `web/regression-conformance.mjs`, `web/calendars*.mjs`, `impl-c/**`, `tools/**`, `tests/**`, `e2e_web_test.py`, `deploy/**`, `.github/**` | `MIT OR Apache-2.0` | (c) 2026 verared contributors; atribución original a Gerardo Loyola (github.com/geroiloyola) |
| **Metadatos de proyecto** (`pyproject.toml`, `web/package.json`, `sbom.cdx.json`, `CITATION.cff`, `NOTICE`, `LICENSING.md`, `REUSE.toml`, `.gitignore`, este esquema) | raíz | `MIT OR Apache-2.0` (`.gitignore` y `REUSE.toml`: `CC0-1.0`) | (c) 2026 verared contributors |
| **Especificación y documentación** | `docs/**`, `README.md`, `README.es.md`, `CHANGELOG.md`, `GOVERNANCE.md`, `SECURITY.md`, `CONTRIBUTING.md`, `LICENSE`/`web/LICENSE` (texto explicativo) | `CC-BY-4.0` | (c) 2026 verared contributors |
| **Vectores de prueba (datos)** | `vectors/**/*.json` | `CC0-1.0` (dominio público: máxima reusabilidad normativa) | declinado; atribución apreciada |
| **Terceros vendorizados: fuentes tipográficas** | `web/fonts/*.woff2`, `web/fonts/OFL.txt`, `LICENSES/OFL-1.1.txt` | `OFL-1.1` | (c) Braille Institute of America, Inc. — Atkinson Hyperlegible |
| **Terceros NO vendorizados (opcional)** | paquete `slh-dsa` 0.2.5 (PyPI) | `LGPL-3.0-or-later` | se instala el usuario; este repo NO redistribuye su código (ver `NOTICE`) |

## Doble licencia del código sin regresión de derechos

Las capas de código se redistribuyen como **`MIT OR Apache-2.0`** (expresión
SPDX válida; el usuario elige una). Los derechos **MIT ya otorgados** en
todas las releases previas (hasta 2.5.0b1 inclusive) **quedan íntegramente
preservados**: la opción MIT permanece disponible con los mismos términos de
siempre (`LICENSES/MIT.txt` es el texto del antiguo `LICENSE` raíz, con su
copyright y atribución intactos). Apache-2.0 es una opción **adicional**
con patent-grant explícito, útil para integradores corporativos.

## Gobernanza de siglas

- **GUS** — Gerarion Universal Standard: la especificación (v2.1.0). Único
  nombre vigente del especificación abierta.
- **GST** — Gerarion Signed Timestamp: la marca temporal firmada
  (`src/gerarion/gts.py`, clase `GtsDocument`).
- **GTS** — nombre histórico (gobernanza v2.0) del **formato canónico sin
  firma**; definición única en `docs/GLOSSARY.md`. Persiste en
  `GOVERNANCE.md` y explica el nombre del módulo `gts.py`; renombrarlo es
  decisión de autoría con alias retrocompatible.
- **`Gerotime`** — no existe en este repositorio ni se permite su
  introducción como nombre de activo (grep `gerotime`: 0 apariciones).

## Nota sobre clasificadores PyPI (PEP 639)

Con la expresión de licencia SPDX (`license = "MIT OR Apache-2.0"`,
setuptools ≥ 77), PyPI prohíbe los classifiers `License :: OSI Approved …`
(supercedidos por la expresión, PEP 639). La doble licencia queda declarada
por la expresión y por el campo `license-files`, no por classifiers.

## Verificación

```bash
# pendiente de añadir al CI (REUSE tool):
pipx run reuse lint
```
