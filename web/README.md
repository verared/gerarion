# Portal y Traductor Cronológico Universal — GUS 2.1.0

Portal web del estándar Gerarion: reloj en vivo (marca canónica completa con
ciclo luminoso y `day_index`/JDN/instant), traductor cronológico universal
(Piedra Rosetta de 10 calendarios: Gerarion, gregoriano proléptico, juliano,
egipcio, etíope, bahá'í, maya/hebreo/islámico/chino vía `Intl`), presets
históricos, calculadora de distancias entre fechas y autoverificación de los
vectores normativos ejecutada en el propio navegador.

Módulos: `gerarion.mjs` (kernel), `calendars.mjs` (puentes multi-calendario
con `day_index`/JDN como pivote), `tests.mjs`, `conformance.mjs`,
`profiles-conformance.mjs`, `calendars.test.mjs` (pruebas unitarias de los
puentes).

Convertidor bidireccional gerarion ↔ gregoriano con reloj vivo y
verificación de vectores en el propio navegador. 100% estático: HTML + CSS +
JavaScript puro (módulos ES). Sin backend, sin cookies, sin telemetría.

## Ejecutar

Cualquier servidor de archivos estáticos sirve; por los módulos ES hace
falta HTTP (no funciona con `file://`):

```
python3 -m http.server 8000 --directory . 
# → http://localhost:8000
```

(El puerto y el directorio exactos no importan; sirve la carpeta `web/`.)

Importante: los módulos ES no cargan si abres `index.html` por `file://`
(doble clic en el archivo). La página detecta ese caso y muestra un aviso
en lugar de quedarse muda. Verificación E2E automatizada (Playwright +
Chromium headless): `python3 e2e_web_test.py` desde la raíz del repo,
con un servidor estático corriendo en el puerto 8123.
```
python3 -m pip install --user playwright
python3 -m playwright install chromium
```

## Archivos

Distribución: sin npm ni registries externos. `gerarion.mjs` (fichero
suelto) y el tarball `gerarion-kernel-<versión>.tgz` se descargan
directamente de [GitHub Releases](https://github.com/verared/gerarion/releases),
con `SHA256SUMS.txt` para verificar integridad. `npm pack` genera el
tarball (lo automatiza el workflow `release.yml` en cada tag `v*`).

- `gerarion.mjs` — port exacto de `src/gerarion/calendar.py` +
  `format.py`. Aritmética entera; BigInt solo en instantes. Exporta
  `toGerarion`, `fromGerarion`, `parse`, `canonicalOf`, `cycleOf`,
  `dayIndexFromGregorian`, `gregorianFromDayIndex`, `tempalumName`, etc.
- `tests.mjs` — misma matriz de vectores normativos que `tests/test_calendar.py`.
  Ejecutable con Node (`node tests.mjs`, salida: N pasan / M fallan, exit 1 en
  fallo) y desde el navegador (sección self-test de la página).
- `index.html` / `style.css` / `app.js` — interfaz. Regla de seguridad:
  todo dato dinámico se inserta vía `textContent`; la página no envía
  ni recibe nada por red.

## Convención horaria

El día rueda a medianoche: el instante continuo es lineal
`día×86400 + h×3600 + m×60 + s` (sin segundos intercalares). El ciclo
SC (06:00-17:59) / LC (18:00-05:59) es una etiqueta luminosa de la hora
actual, no una frontera de fecha. La página muestra la hora TCJ+0 (UTC).

## Qué no puede hacer esta página

Verificar firmas GST (eso requiere la capa criptográfica de `src/`,
ver `src/gerarion/gts.py` y `adapters.py`). El calculador solo expone
la capa matemática — deliberadamente, para mantener superficie de
ataque cero: nada de claves, nada de red, nada de estado persistente.
