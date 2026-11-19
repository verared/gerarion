# Portal y Traductor Cronológico Universal — GUS 2.1.0

Portal web del estándar Gerarion: reloj en vivo (marca canónica completa con
ciclo luminoso y `day_index`/JDN/instant), traductor cronológico universal
(Piedra Rosetta de 10 calendarios: Gerarion, gregoriano proléptico, juliano,
egipcio, etíope, bahá'í, maya/hebreo/islámico/chino vía `Intl`), presets
históricos, calculadora de distancias entre fechas y autoverificación de los
vectores normativos ejecutada en el propio navegador.

Módulos (reorganización modular v3.2.0): `engine/core.mjs` (núcleo GUS),
`engine/tcj-tai.mjs` (TCJ + tabla TAI−UTC + perfil 3339),
`engine/calendars.mjs` (modos de entrada, presentación y rutas Intl
legadas), `engine/guti.mjs` + `engine/china-table.mjs` (motor GUTI
determinista), `engine/zonas-tcj.mjs`; `gerarion.mjs` es el
re-exportador de compatibilidad. Pruebas en `test/` e interfaz en
`ui/`: `tests.mjs`, `conformance.mjs`,
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

- `engine/core.mjs` — port exacto de `src/gerarion/core/calendar.py` +
  `format.py`. Aritmética entera; BigInt solo en instantes. Exporta
  `toGerarion`, `fromGerarion`, `parse`, `canonicalOf`, `cycleOf`,
  `dayIndexFromGregorian`, `gregorianFromDayIndex`, `tempalumName`, etc.
- `test/tests.mjs` — misma matriz de vectores normativos que `tests/test_calendar.py`.
  Ejecutable con Node (`node test/tests.mjs`, salida: N pasan / M fallan, exit 1 en
  fallo) y desde el navegador (sección self-test de la página).
- `index.html` / `style.css` / `ui/app.js` — interfaz. Regla de seguridad:
  todo dato dinámico se inserta vía `textContent`; la página no envía
  ni recibe nada por red.

## Convención horaria

Las fechas de todos los calendarios son días civiles completos en **UTC**:
el pivote es el JDN del mediodía UTC del día civil (JDN = 1719313 +
day_index para Gerarion). Medianoche UTC es el cambio de día; al proyectar
un instante hacia otro calendario la hora se conserva como dato adjunto.
El instante continuo es lineal `día×86400 + h×3600 + m×60 + s` (sin
segundos intercalares). El ciclo SC (06:00–17:59) / LC (18:00–05:59) es una
etiqueta luminosa de la hora de referencia (UTC en modo TCJ+0), no una
frontera de fecha. El reloj admite además la zona local del visitante.

## Convenciones calendáricas y límites documentados

- **Gerarion (GUS 2.1.0)** — exacto: aritmética entera, Gran Tempalum
  simétrico en DY y AY (371 días), era AY con años de 5–6 dígitos.
- **Gregoriano y juliano prolépticos** — exactos con años negativos
  (numeración astronómica; 1 a.C. = año 0).
- **Egipcio (Vago)** — 12 × 30 + 5 epagómenos, época Nabonassar
  (JDN 1448638). No tiene año cero propio: la extensión proleptica puede
  mostrar años ≤ 0.
- **Etíope** — Amete Mihret, época JDN 1724221; bisiesto cuando
  `año % 4 == 3` (Pagume de 5/6 días). Exacto con JDN.
- **Bahá'í (Badí')** — tabla oficial UHJ de Naw-Rúz para los años BE
  172–221; en ese rango el Naw-Rúz y la longitud de Ayyám-i-Há (4 o 5 días)
  son exactos. Fuera de la tabla se usa la convención 21 de marzo
  (aproximación, sesgo ≤ 1 día respecto a la astronomía desde 2015); la
  tarjeta lo indica.
- **Maya (cuenta larga)** — correlación GMT (584283). Exacta con JDN en
  toda la extensión.
- **Hebreo, islámico y chino** — vía `Intl.DateTimeFormat` del navegador.
  Cobertura: todo el rango de `Date` (±8,64·10¹⁵ ms ≈ ±273.790 años), con
  extrapolación matemática de ICU fuera de las tablas históricas
  (chino fiable ≈ 1900–2100; Umm al-Qura ≈ 1900–2074; el islámico civil es
  tabular y exacto en todo el rango). El hebreo distingue Adar I/II en años
  bisiestos; el chino permite introducir meses intercalares con la marca
  `bis`. Si una fecha está fuera de rango, su tarjeta lo dice con claridad
  sin afectar a las demás conversiones.
- **Conversión inversa Intl** — los tres calendarios nativos también
  hacen de origen: se busca el JDN cuyo `Intl` produce los componentes
  pedidos y se verifica con el mismo motor (ida y vuelta) antes de aceptarlo.

## Accesibilidad

Tipografía Atkinson Hyperlegible (OFL, archivos locales en `fonts/`),
texto ≥ 16 px, controles ≥ 2,4 rem de alto, foco visible, navegación
completa por teclado, `aria-live` en resultados y modo de contraste
reforzado (botón «contraste alto» en la cabecera). Diseño verificado a
320, 390, 768 y 1440 px, y funcionando sin conexión una vez cargada.

## Qué no puede hacer esta página

Verificar firmas GST (eso requiere la capa criptográfica de `src/`,
ver `src/gerarion/gts.py` y `adapters.py`). El calculador solo expone
la capa matemática — deliberadamente, para mantener superficie de
ataque cero: nada de claves, nada de red, nada de estado persistente.
