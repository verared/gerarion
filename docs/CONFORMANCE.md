# Conformancia GUS — guía para implementaciones independientes

Este documento explica cómo una implementación de tercera parte demuestra
que es conforme a GUS 2.1.0 **sin leer una sola línea de las
implementaciones de referencia** (Python, JavaScript, C): todo se verifica
contra los archivos de `vectors/`.

## 1. Archivos de vectores

| Archivo | Contenido | Obligatoriedad |
|---|---|---|
| `vectors/gus-normative-003.json` | Núcleo: constantes, regla del Gran Tempalum (simétrica DY/AY), calendario, inicios de año, ida y vuelta gregoriano, formato canónico, instantes | **Obligatorio** para cualquier implementación que declare GUS |
| `vectors/gus-3339-002.json` | Perfil GUS-3339: instantes ↔ RFC 3339 `Z` estricto + 3 casos canónicos | Obligatorio si se declara GUS-3339 |
| `vectors/gus-3339-negative-001.json` | Casos negativos del perfil (hora/minuto/segundo fuera de rango, fechas inexistentes, offsets, fracciones): **rechazar, nunca normalizar** | Obligatorio si se declara GUS-3339 |
| `vectors/gus-regression-001.json` | Era AY simétrica (Gran Tempalum en años < 0), incluidos vecinos de `0001AY-00-11-B` | Obligatorio para cualquier implementación (el núcleo lo incluye) |
| `vectors/archive/` | Vectores históricos de versiones anteriores | Informativo |

Ningún valor de los vectores normativos cambia sin ventana de revisión de
90 días (GOVERNANCE) y entrada en el CHANGELOG.

## 2. Cómo ejecutar las baterías de referencia

```bash
# Python (referencia)
python -m venv .venv && . .venv/bin/activate
pip install -e '.[slh]'           # [slh] es opcional (FIPS 205)
python -m pytest tests/ -q
python tools/conformance.py vectors/gus-normative-003.json

# JavaScript
node web/tests.mjs
node web/conformance.mjs
node web/profiles-conformance.mjs
node web/regression-conformance.mjs
node web/calendars.test.mjs       # traductor multicalendario (web)

# C (tercera implementación en el repo)
make -C impl-c conformance

# Fuzz diferencial Python <-> C <-> JS
make -C impl-c gus-cli
python tools/fuzz_diff.py --n 1500
```

## 3. Formato de `vectors/`

Un archivo de vectores es JSON con:

- `schema`: identificador del set (p. ej. `gus-normative-003`).
- `deterministic`: `true` (ningún vector depende de reloj, red ni azar).
- Categorías con casos autodescriptivos: entrada (`ts`, `day_index`, …) y
  salida esperada exacta (`canonical`, `instant`, `weekday`, `day`, flags).
- Un caso negativo expresa rechazo: la implementación debe devolver un
  error con código `GERO_*` equivalente y **nunca** una salida normalizada.

## 4. Categorías obligatorias (núcleo)

`constants`, `gran_tempalum`, `calendar`, `year_starts`,
`gregorian_roundtrip`, `format`, `instant` — además de los casos negativos
(`gus-3339-negative-001`) si se declara el perfil GUS-3339. El núcleo C
(`impl-c/conformance.c`) consume los tres archivos en una sola invocación:

```bash
./impl-c/gus-conformance vectors/gus-normative-003.json \
  vectors/gus-3339-negative-001.json vectors/gus-regression-001.json
```

## 5. Criterio de conformancia

> Tu implementación es conforme si y solo si pasa el 100 % de los vectores
> de las categorías que declare. Una salida distinta en cualquier campo —
> incluida una fecha "amablemente" normalizada o un error silencioso —
> es NO CONFORME.

Invitamos implementaciones independientes (inclusive en otros lenguajes) a
consumir los vectores y abrir issue/PR con resultados; ver
[CONTRIBUTING.md](../CONTRIBUTING.md).
