# Changelog — GUS

## 3.2.1 — Exportador modular a repositorios satélite gt-* (2026-11-19)

Herramienta de empaquetado (sin cambios en aritmética, motores, vectores
ni web publicada; PR #22):

- `tools/export_module.py` (stdlib pura): exporta los 9 dominios
  normativos (`gt-core`, `gt-tcj`, `gt-gus`, `gt-calendar`, `gt-gts`,
  `gt-gst`, `gt-interop`, `gt-tslr` y `gt-gcerts`) como paquetes
  autónomos con la jerarquía relativa intacta; genera `LICENSE`,
  `LICENSES/` (solo textos usados), `NOTICE`, `REUSE.toml` con
  cobertura 100 % y README bilingüe con contrato de sincronización.
- `--verify`: `reuse lint` al 100 % en cada export y compilación
  standalone de `libgerarion-core` (`-std=gnu11 -Wall -Wextra -Werror`
  + humo; la excepción pedantic — el guardia congelado usa `__int128`,
  extensión GNU — está documentada).
- `tests/test_export_module.py`: 19 pruebas (lint del export,
  compilación autónoma, dependencias declaradas, determinismo,
  solo lectura del origen, `--no-large-vectors`).
- `docs/architecture/SATELLITE-REPOS.{es,en}.md`: modelo de satélites
  y flujos exportar/publicar/consumir/actualizar.

## 3.2.0 — Reorganización modular en 8 dominios (2026-11-19)

Desacoplamiento estructural de la suite de referencia. **Ningún cambio
de la aritmética congelada de GUS v3.0.0, de los vectores
`gus-normative-003.json` ni de las reglas de los 10 calendarios.**

- **Documentación**: cada dominio tiene ahora una especificación
  autocontenida bilingüe en `docs/specs/` (TCJ, GUS, CALENDAR, GTS, GST,
  TSLR\*, GCERTS\*, INTEROP; \* experimentales). `docs/spec/gus-3.0.0.md`
  permanece como edición consolidada. Historial en `docs/history/`
  (REDISENO, erratas v1.2, informe de adopción, TODO-pendientes).
- **C11**: `impl-c/` dividido por dominio — `core/` (TCJ+GUS, apto para
  MCU sin reloj ni TAI), `tai/`, `clock/` (GTS §6.3), `calendars/`;
  `gus.h`/`gerarion.h` quedan como paraguas retrocompatibles. Makefile
  con 4 bibliotecas (`libgerarion-core`, `-clock`, `-calendars` y la
  unificada) con pkg-config por dominio; `core-smoke` demuestra que el
  núcleo standalone compila y corre solo.
- **Pruebas C**: parser JSON unificado en `test_jsonmin.[ch]` (antes
  duplicado en los dos runners).
- **Python**: `src/gerarion/` en subpaquetes (`core`, `tcj`,
  `calendars`, `gts`, `gst`, `interop`, `service`, `deprecated`) con
  shims planos de compatibilidad (importaciones de 3.1.1 intactas) y
  extras por dominio (`[gst]`, `[gts]`, `[service]`, `[all]`).
  `hashots.py` a `deprecated/` con `DeprecationWarning`; el stack
  activo carga el legado de forma condicional.
- **Web**: `engine/` (núcleo dividido en `core.mjs` + `tcj-tai.mjs`,
  GUTI, tabla china, zonas), `ui/` (app, atlas) y `test/` (seis
  runners); `web/gerarion.mjs` reexporta el API unido; Service Worker
  fail-closed con las rutas nuevas (`gerarion-v3-2-0`); `package.json`
  exporta cada submódulo.
- **Distribución**: `release.yml` publica `libgerarion-core` standalone
  además de la suite completa; `vectors/README.md` mapea cada conjunto
  de vectores con su dominio.

Verificación completa: pytest 310+1, seis runners JS (36/36, 42/42,
127.204/127.204, conformance/3339/regresión 0 fallos), C conformance 11
categorías + 63.850/63.850 GUTI, audit ASan+UBSan 6.524.458
comprobaciones 0 errores, e2e Playwright 62/62, `reuse lint` 100 %.

## 3.1.1 — Endurecimiento quirúrgico: JCS binary64, reloj autenticado, SW fail-closed, verificación china (2026-11-19) — Endurecimiento quirúrgico: JCS binary64, reloj autenticado, SW fail-closed, verificación china (2026-11-19)

Parche de seguridad de la cuarta revisión adversarial estática (adenda
v3.1.1 en `docs/audit/AUDIT-REPORT-v3.0.0.md`, hallazgos `B-1..B-4`).
Ningún cambio de aritmética congelada ni de vectores normativos.

- **B-1 (JCS/RFC 8785)**: `jcs.dumps` rechaza enteros fuera de
  ±(2^53−1) — la serialización interoperable exige Number de ECMAScript;
  los valores de 64 bits viajan como cadena decimal.
- **B-2 (reloj de confianza)**: anti-rollback por tupla
  `(instant, nanos)` (un retroceso solo de nanosegundos también se
  rechaza, incluso contra el ancla persistida en disco); autenticidad
  EXPLÍCITA de la fuente: `ClockReading.authenticated` +
  `ClockPolicy.require_authenticated` (por defecto true) y lista blanca
  opcional `trusted_sources`; sin autenticidad nunca hay `VERIFIED`
  aunque la cota sea 0. Equivalente C11 (`GusClockReading.authenticated`,
  `GusClockPolicy.require_authenticated` + categoría `check_clock_state`
  en conformance).
- **B-3 (Service Worker fail-closed)**: se elimina el fallback abierto
  `fetch(req)` — solo se sirve la lista blanca precacheada, con 403
  explícito para el resto del mismo origen; CSP restrictiva
  (`connect-src 'none'`, `object-src 'none'`, `base-uri 'self'`).
- **B-4 (chino verificado)**: `tests/test_guti_calendars.py` — 40
  pruebas contra fechas publicadas (Años Nuevos, ocho runyue, bordes de
  lunación, noches límite con tolerancia documentada en
  `CALENDAR-ENGINE.md` ES/EN).
- Regresiones exactas de los cuatro hallazgos en `test_jcs_gstv2.py`,
  `test_clock_state.py` y `e2e_web_test.py` (62/62). `reuse lint` 100 %.

## 3.1.0 — Fase GUTI-1: motor multi-calendario determinista y portal 100 % offline (2026-11-18)

La aritmética congelada de GUS v3.0.0 no cambia: `TCJ = TAI + 8.400 s`,
recurrencia simétrica `AY`/`DY`, `ORIGIN_JDN = 1719313`, formatos de
32/29 caracteres y los vectores `gus-normative-003.json` permanecen
intactos; los blindajes `A-1..A-6` se conservan.

- **Motor multi-calendario** (`DayIndex` como pivote): diez sistemas
  completos — `gus`, `greg`, `julian`, `egyptian`, `ethiopic`, `bahai`,
  `maya`, `islamic`, `hebrew`, `chinese` — con metadatos estructurados,
  con paridad bit a bit en C11 (`impl-c/gerarion_calendars.c`,
  `libgerarion`), Python (`src/gerarion/calendars.py`) y JavaScript
  (`web/guti.mjs`, sin `Intl`, `BigInt` intermedio).
- **Set de vectores compartido CC0** `vectors/guti-calendars-001.json`
  (63.545 vectores + 450 cruces palíndromos + inválidos/no
  soportados/erange), regenerable determinísticamente con
  `tools/generate_guti_vectors.py`. Corredores: pytest
  (`tests/test_guti_m0_sandbox.py`, con red bloqueada),
  `make -C impl-c guti-conformance` (63.850/63.850 CONFORME) y
  `node web/guti_vectors.mjs` (127.204/127.204).
- **Correciones de rigor descubiertas por la batería M0**: límite de mes
  rabínico hebreo (12/13), estimador de año de molad O(1) (el escaneo
  lineal previo degeneraba a O(años)), baktun maya negativo proléptico,
  guardias de producto int64.
- **Portal 100 % offline**: `web/sw.js` + `manifest.webmanifest`
  precachean el activo local; el panel de equivalencias muestra hebreo,
  islámico tabular y chino del motor determinista (Umm al-Qura conserva
  su nota de cobertura); marcador «Modo Offline Listo»; prueba e2e en
  modo avión incluida (59/59).
- **Documentación**: `docs/spec/CALENDAR-ENGINE.md` +
  `docs/en/CALENDAR-ENGINE.md` y `docs/spec/GUS-LIBRARY-API.md` +
  `docs/en/GUS-LIBRARY-API.md`; `reuse lint` 100 %.

## 3.0.1 — Parche de seguridad de la auditoría adversarial (2026-11-18)

Publica los hallazgos `A-1..A-6` resueltos en el informe
`docs/audit/AUDIT-REPORT-v3.0.0.md`. Sin cambios de formato ni de
aritmética normativa (los vectores `gus-normative-003.json` no cambian).

### Corregido

- **A-1 (Alto)** — JS: `toGerarion` entraba en bucle no terminante con
  `day_index >= 2^53` (imprecisión de `Number`). Ahora `toGerarion`,
  `fromGerarion` y `gregorianFromDayIndex` rechazan con `GERO_EINVAL` lo
  que exceda el dominio exacto de `Number` y documentan el umbral
  (`Number.MAX_SAFE_INTEGER`) frente a `BigInt`.
- **A-2 (Alto)** — `ReplayGuard`: un archivo de estado corrupto, truncado
  o de estructura ajena activa fail-closed (`_poisoned`); antes se
  reanudaba como historial vacío y habilitaba replay/rollback.
- **A-3 (Medio)** — Quórum del notario: `known_replicas` opcional excluye
  y reporta identidades ajenas al trust root
  (`unknown_replicas`); antes computaban para el quórum.
- **A-4 (Medio)** — Paridad de rechazo: precedencia normada
  sintaxis → calendario → semana → rangos, idéntica en C/Python/JS para
  marcas doblemente inválidas.
- **A-5 (Medio)** — `normalize` de JS ya no colapsa espacios múltiples;
  C recorta extremos como `raw.strip()` de la referencia.
- **A-6 (Bajo)** — C11: `GUS_ERANGE` + macros `GUS_MAX_*` blindan
  `instant` (±2,92e11 años), el calendario (±2,51e16) y la vía
  gregoriana (±6,31e15); sin trayectorias de signed overflow (UB).
- Auditado además bajo `make -C impl-c audit` (ASan+UBSan, -Werror:
  0 errores/UB/warnings), fuzzing diferencial de 1.000.000 de casos
  (0 divergencias) y suite adversarial de 18 ataques (todos rechazados).

## 3.0.0 — Versión estable del endurecimiento (2026-11-18)

Equivalencia de versiones: `3.0.0` (PEP 440 y semver) unifica
`3.0.0a1` / `3.0.0-alpha.1`. Promoción a estable del paquete de
endurecimiento derivado de la revisión técnica: la aritmética entera
O(1) del calendario (AY/DY), la coordenada `TCJ = TAI + 8,400 s` y los
vectores normativos `gus-normative-003.json` quedan intactos.

### Kernel

- **Precisión sub-segundo separada**: campo `nanos` (0..999_999_999,
  validado estrictamente, sin normalización silenciosa) junto al
  `instant` en segundos int64, en Python (`calendar`, `gts`, `format`),
  C11 (`impl-c/gus.h`/`gus.c`) y JS (`web/gerarion.mjs`). La marca
  canónica no emite la fracción; viaja como dato de precisión.
- **Puente TAI − UTC versionado** en los tres lenguajes:
  `table_version: IERS-C-2026.1`, `valid_until_unix: 2027-11-18`
  (transición al UTC continuo aprobada por la CGPM), `smear_policy:
  reject` y advertencia de extrapolación pasada la vigencia.
- **Máquina de estados de reloj (Cap 6.3)**: `src/gerarion/clock.py` y
  equivalentes C. Estados VERIFIED/HOLDOVER/UNVERIFIED/REJECTED;
  duraciones SIEMPRE con reloj monotónico, tiempo absoluto solo de
  fuente autenticada; ancla persistida con detección de rollback.

### Seguridad (GST)

- **GST v2**: canonicalización determinista RFC 8785 (JCS, stdlib puro,
  `src/gerarion/jcs.py`); firma híbrida simultánea Ed25519 + ML-DSA con
  el descriptor de algoritmos dentro del payload firmado (anti-downgrade
  estructural); `event_hash` obligatorio (`sha256:`/`sha512:`);
  `ReplayGuard` anti-replay/anti-rollback persistente. Lectura de
  sellos v1 compatible; los sellos nuevos se emiten en v2. CLI de
  verificación (`tools/verify_gus.py`) actualizada.

### Documentación

- spec 3.0.0 (ES/EN) y threat-model (ES/EN): nodo metrológico del BIPM
  en Sèvres; garantías verificables en lugar de afirmaciones absolutas;
  TSLR/GCERTS marcados como perfiles experimentales separados del
  núcleo; GUS no sustituye controles de SO, aislamiento de hardware ni
  mitigaciones de red.
- Defecto corregido: `verify_v2` rechazaba todo sobre GST v2 con
  `nanos != 0` al contraste contra la marca canónica.

### CI y distribución

- Matriz de Python instala `[dev,slh,pqc]` y ejecuta las suites
  `test_jcs_gstv2.py` (41) y `test_clock_state.py` (15) explícitamente.
- Job de `reuse lint` (REUSE 3.3) en cada push/PR.

## 3.0.0-alpha.1 — GUS 3.0.0 (base TAI + TCJ = TAI + 8,400 s; CIERRA D-001 y TODO-004)

Equivalencia de versiones: `3.0.0a1` (PEP 440; pyproject, CITATION, sbom) =
`3.0.0-alpha.1` (semver; `web/package.json`). La spec sube de **2.1.0** a
**3.0.0** (`docs/spec/gus-3.0.0.md` + espejo EN). Cambio MAYOR de kernel:
todos los instantes de los vectores cambian.

### Base temporal (kernel, Cap 7 / Cap 13 del documento canónico)

- **TAI como Capa 0** (CIERRA **D-001**): `instant` son segundos continuos
  y monotónicos sin segundos intercalares internos; nuevo módulo
  `src/gerarion/tai.py` con la tabla histórica IERS TAI−UTC completa
  (29 entradas, 1958 = 10 s … 2017 = 37 s; pre-1958 convención proléptica
  0 s), `tai_minus_utc`, `instant_from_unix` y `unix_from_instant`
  (inversa exacta por segmentos). Espejo en `web/gerarion.mjs` e
  `impl-c/gus.c` (`gus_tai_table`/`gus_tai_minus_utc`).
- **TCJ = TAI + 8,400 s** (Tiempo de Coordinación de Jerusalén, meridiano
  35.2137°E; 31.7683°N, 754 m): sustituye a la medianoche UTC de la 2.1
  como coordenada global. Offset matemático sin SPOF; convención
  documentada con sistemas legacy (TCJ−UTC ≈ 2 h 20 min 37 s en 2026).
- **El campo `TCJ±O` entra en el cálculo** (CIERRA **TODO-004**):
  `instant_from_parts(..., offset_seconds)` y
  `parts_from_instant(instant, offset_seconds)` en los tres lenguajes;
  offsets con minutos (`TCJ-2:20`/`TCJ-220`, rango ±24 h en múltiplos de
  60 s). `2031DY-03-08-T-09:30:00-SC-TCJ+0` ≡
  `2031DY-03-08-T-07:10:00-SC-TCJ-2:20` (mismo instante).
- **Formato COMPACTO de 29 caracteres** (Cap 13.1):
  `2031DY-03-08-T-093000-SC-TCJ0`; entrada en los tres lenguajes y
  `to_compact`/`compactOf` de salida auxiliar. La forma canónica de
  salida sigue siendo SIEMPRE la extendida.
- **SC/LC siempre sobre la hora civil declarada del observador** (Cap
  13.3), nunca forzado a `TCJ+0`.
- **Cruzar un intercalar histórico ahora conserva la duración física**
  (diferencia de enteros = 2 s en 2016-12-31; antes 1 s): propiedad
  estructural nueva garantizada por la tabla.
- Espejo EN del compilado despecs: `docs/en/gus-3.0.0.md`.

### Vectores y conformancia

- `gus-normative-002.json` y `gus-3339-001.json` **archivados** en
  `vectors/archive/`; nuevos `vectors/gus-normative-003.json` y
  `vectors/gus-3339-002.json` (TCJ = TAI + 8,400 s, offsets con minutos,
  compacto, `equivalent_views`, intercalar Δ = 2 s). Consumidores
  actualizados: `tools/conformance.py`, `tests/test_conformance.py`,
  `tests/test_profiles.py`, `impl-c/conformance.c` + Makefile,
  `web/conformance.mjs` y `web/profiles-conformance.mjs`.

### Portal web

- Reloj en vivo con la hora TCJ real (TCJ = UTC + 8,437 s), equivalencia
  TAI/UTC y etiqueta civil `TCJ±H:MM` del observador; opción
  «TCJ+0 (Jerusalén · TAI + 8,400 s)»; leyenda del ciclo actualizada.

### Documentación y decisiones

- D-001 marcada **CERRADA/ADOPTADA** (ES/EN); TODO-004 **CERRADO**.
- Glosario ES/EN: TCJ = "Tiempo de Coordinación de Jerusalén"
  (antes, errata: "Tiempo Civil de Jaén"); escalas e instant actualizados.
- README/README.es: sección «Escala de tiempo» reescrita para 3.0.0.
- GOVERNANCE (ES/EN), docs/CONFORMANCE.md, vectors/README.md,
  CITATION.cff, sbom.cdx.json, pyproject.toml y web/package.json
  versionados a 3.0.0(-alpha.1 / a1). Advertencia de mantenimiento: el
  software sigue en fase alfa/beta — **no apto para producción**
  (ver SECURITY.md).

## Sin publicar (rama beta/cap13-improvements)

Mejoras derivadas del contraste «Cap 13 — Identificadores y Seguridad v1.2»
(documento canónico externo de GeroTime Foundation) contra el stack real.
Sin cambios en vectores normativos ni en la matemática del calendario.

### Seguridad y criptografía

- **Adaptador ML-DSA (FIPS 204) opcional** (`src/gerarion/adapters.py`,
  `MlDsaSigner`): firma pura con contexto de dominio `GUS2-TS`, vía el
  paquete `cryptography>=47` (extra `gerarion[pqc]`); semilla determinista
  para tests. `gts.verify` ahora despacha por `alg` a SLH-DSA o ML-DSA.
  NOTICE, sbom.cdx.json y pyproject actualizados (sin dependencias nuevas
  obligatorias; sin secretos).
- **Plan de migración post-cuántica documentado** (threat-model.md,
  ES y EN, §G6): estado real y tres fases; la firma híbrida
  Ed25519+ML-DSA queda como OBJETIVO, no como "vigente" — ni el kernel ni
  el calendario cambian (cambio de capa de firma, versión menor).
- `__init__.py`: `__version__` alineado con pyproject (2.5.0b1; antes
  quedaba 2.4.0 tras el salto de beta).

### Formato y verificación rápida

- **`quick_verify` O(1) sin red** (Cap 13.8 v1.2): `format.py` (Python,
  exportado en el paquete), `quickVerify` (JS) y `gus_quick_verify` (C).
  Valida sintaxis, rangos, letra Nuvid estricta y ciclo exacto, y rechaza
  correcciones silenciosas (era asumida, ciclo declarado equivocado): una
  entrada dudosa se rechaza, NUNCA se normaliza a válido. Filtro barato
  para logs e IoT; no sustituye a `parse` + verificación de firma.
- **Vector compartido NUEVO** `vectors/gus-quickverify-001.json` (6 casos
  válidos, 8 tampering) consumido por `tests/test_quick_verify.py`,
  `web/tests.mjs` y la nueva categoría **10ª** del runner de conformancia
  de impl-c.

### Roadmap

- Nota exploratoria sobre la verificación astronómica TSLR con quorum
  3-de-4 (propuesta externa Cap 13.4.1): NO condición de RC/1.0, no altera
  el kernel ni el formato; puntos de extensión en docs/papers/.

## 2.5.0b1 — BETA inicial (formats + release; 2026-11-17)

Equivalencia de versiones: `2.5.0b1` (PEP 440; pyproject, CITATION, sbom) =
`2.5.0-beta.1` (semver; `web/package.json`). La spec mantiene **2.1.0**.
Etiqueta de ciclo: `alfa-final` pasa a **BETA**.

### Formatos y perfiles

- **F1 (GUS-3339):** los parsers de Python y JS rechazan —sin normalizar—
  campos horarios fuera de rango (hora > 23, minuto > 59, segundo > 59),
  fechas inexistentes, años fuera de 0000–9999, offsets ≠ Z y fracciones.
  Vector negativo NUEVO compartido `vectors/gus-3339-negative-001.json`
  (17 casos) consumido por pytest, `web/profiles-conformance.mjs` y
  `impl-c/conformance.c`; C ya validaba por partes. El vector normativo
  `gus-3339-001.json` no se ha tocado.
- **F2 (era AY):** vector de regresión NUEVO compartido
  `vectors/gus-regression-001.json` (8 casos AY, incluidos
  `0001AY-00-11-B` y vecinos) consumido por el núcleo (Python/JS/C), el
  nuevo runner `web/regression-conformance.mjs` y `tools/verify_gus.py`
  (que ya no rechaza AY con GERO_ETEMPALUM: corregido en 2.4.0/PR #6).

### Documentación

- **D1:** sección única «Escala de tiempo» / "Time scale" (README EN+ES):
  día GUS a medianoche UTC, entero tipo Unix/POSIX sin tabla TAI−UTC,
  ejemplo medido con el código (2016-12-31T23:59:59Z →
  2017-01-01T00:00:00Z: entero +1 s, transcurrieron 2 s SI). Contexto
  verificado con fuente primaria: NIST (TAI−UTC = 37 s) y Resolución 5 de
  la 28.ª CGPM (2026): UTC continuo desde 2027-05-20, |UT1−UTC| ≤ 3.600 s.
  **D-001 (medianoche UTC vs TAI) queda como DECISIÓN DEL AUTOR.**
- **D2:** `docs/GLOSSARY.md` (ES+EN), definición única por término
  (GUS, GST, GTS, GUS-3339, GUS-3161, GUS-Roughtime, GUS-for-notation,
  Tempalum, Gran Tempalum, TCJ, day_index, JDN, instant, SC/LC);
  enlazado desde ambos README. El módulo `gts.py` conserva su nombre
  (razón histórica documentada en el glosario); renombrar sería
  DECISIÓN DEL AUTOR.
- **F3:** `docs/history/TODO-pendientes.md` TODO-004 (offsets con minutos en
  `TCJ±O`, p. ej. +05:45): el formato NO cambia en esta beta (cambiarlo
  exige decidir la forma canónica); DECISIÓN DEL AUTOR con dos opciones.
- **Lenguaje:** «estándar» → «especificación abierta» / «proyecto de
  estándar» en README EN+ES (no hay adopción por un organismo).
- Comparativo actualizado con fuentes verificadas: calendario egipcio
  civil (12×30+5; WebExhibits) y Symmetry454 (años 364/371, semana
  intercalar; Threeten-Extra), con el coste declarado: 3 meses = 90 días
  ≠ 13 semanas.

### Seguridad (sin detalles de explotación)

- Endurecimiento beta de 2.4.x/PR #6 incluido: verificación de anclas
  contra notario de política, clave de confianza externa exigida, quórum
  por identidades únicas, persistencia de pendientes, firma de referencia
  deshabilitada por defecto. **Además:** tabla «Qué está listo y qué no»
  en ambos README y ajuste de metadatos de release
  ("calendario computacional y proyecto de interoperabilidad temporal y
  evidencias verificables; funciones de seguridad en revisión"), sin
  afirmaciones de garantía absoluta.

### CI y cadena de suministro

- CodeQL (Python + JavaScript) anclado por SHA real;
  `dependabot.yml` (github-actions, npm, pip); `pip-audit` en CI.
- Estado: `permissions: contents: read` como base en todos los workflows,
  con los mínimos extra por job (pages, release).
- `docs/CONFORMANCE.md` (cómo una tercera parte reimplementa el núcleo),
  invitación a implementaciones independientes en `CONTRIBUTING.md`,
  `docs/ROADMAP.md` (beta/RC/1.0, sin fechas).
- Build en seco verificado (sdist/wheel `twine check` PASSED; `npm pack`
  5 archivos, 11,2 kB). Sin tag ni release en esta rama: los decide el
  autor.

## Sin publicar (web-ux) — UX del portal

- **Portal reordenado:** el traductor de fechas pasa a ser la primera
  sección (título «Traductor de fechas entre calendarios», con
  «Piedra Rosetta» de subtítulo); conversiones rápidas plegadas,
  reloj «Ahora en Gerarion» compacto, mini-navegación por anclas,
  jerga técnica (day_index/JDN/instant, límites Intl/Umm al-Qura/chino/
  bahá'í) dentro de `<details>`.
- **Enlace compartible:** cada traducción escribe `#cal=<modo>&d=<fecha>`
  (solo hash); botón «Copiar enlace»; al cargar y en `hashchange` el
  resultado se reproduce en el navegador, sin red.
- **Errores con formato esperado:** los mensajes de entrada inválida
  indican formato y ejemplo por calendario en lugar de «Error» a secas.
- **Accesibilidad:** etiquetas métricas por `aria-labelledby` (deja de
  abusar de `<label>` sin `for`), `role=status` en toasts, `aria-live` en
  resultados, foco visible, contraste reforzado por `data-theme`.
- **CSP y metadatos:** `<meta http-equiv="Content-Security-Policy">`
  (`default-src 'self'`, sin inline scripts), `theme-color`, favicon SVG
  inline (data URI), Open Graph.
- **E2E (Playwright) actualizado a la nueva estructura (32 checks) + job
  CI `web-e2e`** que levanta un servidor estático y ejecuta Chromium
  headless, fallando si hay peticiones externas.

## 2.4.0 — Gran Tempalum simétrico + spec GUS 2.1.0 (2026-11-17)

**Cambio normativo (kernel §3/§5, spec 2.0 → 2.1.0): el Gran Tempalum es
simétrico e infinito hacia ambos lados del origen.** Nueva versión del
vector set: `gus-normative-002.json` (la `gus-normative-001` queda
archivada en `vectors/archive/` al exigirlo GOVERNANCE §3.1.4). Ningún
vector de la era DY cambia: los valores DY de la 002 son bit a bit los de
la 001 (verificado por comparación de categorías y por la suite completa).

- **Regla matemática (idéntica en Python, C y JS), con S = 1_242_190 y
  U = 7_000_000, para todo entero `year`:**
  - `r_y = ((year % U) + U) % U` (residuo euclidiano);
  - `r = (r_y * S) % U` (sin desbordamiento: `r_y < U` antes de
    multiplicar; `U*S < 2^63`);
  - `is_gran_tempalum(year) <=> r + S >= U`.
  GT DY: `5, 11, 16, 22, 28...`; GT AY: `-1, -6, -12, -17, -23, -29...`
  (`0001AY` es GT de 371 días; `r(-1) = 5_757_810`).
- **`year_start_day_index` O(1) cerrado:** `q, r = divmod(year, U)` por
  división piso (euclidiana también en AY);
  `gt_count = q*S + floor(r*S/U)`;
  `year_start = year*364 + 7*gt_count`. `ysi(0)=0`, `ysi(-1)=-371`;
  para todo `year >= 0` coincide bit a bit con la suma iterativa anterior.
- **Búsqueda inversa simétrica:** `_locate`/`gus_to_gerarion`/`toGerarion`
  estiman el año con la longitud media exacta (`364 + 7*S/U`) y corrigen
  de forma monotónica con `year_start_day_index`, usando la duración real
  (364 o 371) de cada año AY (antes se asumían 364 fijos).
- **Formato canónico:** años de más de 4 dígitos ahora parseables
  (regex `\d{1,6}` en Python/JS; `is_digits(..., 1, 6)` en C) — los años
  GT infinitos en ambas eras lo exigen (p. ej. `12000AY-01-01-S`).
- **Vectores normativos 002:** añade patrón GT AY (`pattern_years_m45_m1`
  = `[-46..-1]`), muestras `-1/-6/-12000`, `year_starts` AY
  (`-1/-6/-12/-17/-29/-12000` con `gran_tempalum` real), roundtrip AY
  (`-1,-5,-7,-10,-364,-365,-371,-372,-728,-1000,-4382910,-1000000`),
  calendario AY (`0001AY-00-11-B` Nuvivid VII, `0001AY-01-04-A`,
  `0006AY-01-01-S`, `0029AY-01-01-S`, `12000AY-01-01-S`) e instantes
  (`0001AY-00-11-B-12:00:00-SC-TCJ+0` = -43200). SHA-256 del set:
  `580d8843137c0e8f1a77c670773ce8090a49ea21cb0d70a9b6a5aec2c1de08b0`
  (regeneración byte a byte idéntica).
- **Runner de conformancia:** `year_starts` ya no invierte el signo del
  año AY y valida `gran_tempalum`/`tempalum_days` en ambas eras (Python,
  JS y C); `check_gran_tempalum` valida también `pattern_years_m45_m1`.
- **Spec:** `docs/spec/gus-2.1.0.md` y `docs/en/gus-2.1.0.md`
  (renombradas desde gus-2.0.md): §3 con la regla cerrada simétrica,
  §5 eras con simetría y cota |Δ| < 7 días en ambos sentidos, §9 ya
  normativa (medianoche UTC, pre-1958 proléptico).
- **Distribución:** GitHub Releases (workflow `release.yml`) con nuevos
  artefactos `gerarion-2.4.0-*` y `gerarion-kernel-2.4.0.tgz`.

## 2.3.5 — alpha-final (GUS v2.0 congelado, 2026-11-17)

Cierre documental: **sin cambios normativos de kernel ni nuevos vectores** —
la salida numérica es idéntica a `2.3.4-alpha.2` (verificado: 110 tests +
`gus-normative-001.json` sin tocar).

- **README principal en inglés** (`README.md`): badges (CI, Pages), demo
  en vivo, "Why Gerarion", 30-Second Quickstart (Python/JS/C reales),
  tabla de componentes y verificación por `SHA256SUMS.txt`. El README
  completo en español pasa a `README.es.md` (espejo; EN > ES en
  divergencia).
- **Spec §9 normativizada (TODO-001 cerrado 2026-11-17, ES+EN):**
  - Meridiano del día GUS: **medianoche UTC** (la regla de facto de las
    tres implementaciones pasa a regla normativa explícita).
  - Pre-1958: **convención proléptica declarada** (aritmética entera
    extendida hacia atrás, sin pretensión de coincidir con UT1/TAI
    históricas).
  - Divergencia TAI/GUS declarada (37 s en 2026, valor congelado en los
    vectores). Sin cambio numérico: vectores intactos.
- **D-001 (medianoche TAI con tabla) queda viva como PROPUESTA 2.x**
  (Looking Period, GOVERNANCE §3.1; exigiría `gus-normative-002` y
  regeneración de sellos).
- Distribución: GitHub Releases como único canal (workflow `release.yml`:
  wheel + sdist + tarball npm + `SHA256SUMS.txt`); sin PyPI ni npm.
- Estado del estándar: **ALFA-FINAL — GUS v2.0 congelado**; camino a 1.0
  queda: adaptadores criptográficos opcionales y pase a beta.
- `docs/history/TODO-pendientes.md`: TODO-001 CERRADO; TODO-002 (Roughtime UDP)
  sigue ABIERTO.

## 2.3.4-alpha.2 — arreglo de CI (2026-11)

Equivalencia de versiones: `2.3.4a2` en PEP 440 (pyproject, CITATION, SBOM)
= `2.3.4-alpha.2` en semver (web/package.json, README, tag `v2.3.4-alpha.2`).

Sin cambios normativos: GUS, GTS, GST y los códigos `GERO_*` no cambian; los
vectores no se regeneran.

- **CI (GitHub Actions):** la matriz de Python fallaba porque
  `setup-python` no suministra CPython 3.9 en Ubuntu 26.04 (`ubuntu-latest`
  actual); se fija `runs-on: ubuntu-24.04` y `fail-fast: false`.
- **CI:** el paso de fuzzing diferencial requiere `impl-c/gus-cli`, que no
  se compilaba; ahora el propio paso ejecuta `make -C impl-c gus-cli`.
- **Pages:** el sitio web (calculador GUS) se publica vía GitHub Actions
  en https://verared.github.io/gerarion/.

## 2.3.4-alpha.1 — prepush (rebrand: Gerarion, 2026-11)

Equivalencia de versiones: `2.3.4a1` en PEP 440 (pyproject, CITATION, SBOM)
= `2.3.4-alpha.1` en semver (web/package.json, README, tag `v2.3.4-alpha.1`).

Sin cambios normativos: GUS, GTS, GST y los códigos `GERO_*` no cambian; los
vectores no se regeneran. Antes del primer push público:

- **Rebrand completo a Gerarion:** El estándar GUS
  (Gerarion Universal Standard) lo mantiene la organización `verared`
  (github.com/verared/gerarion).
- Paquete PyPI `gerarion`, npm `gerarion-kernel`, módulo Python
  `gerarion` (src/gerarion/), web `gerarion.mjs`, draft IETF
  `draft-gerarion-gus-00`, repo `github.com/verared/gerarion`, impl-c
  recompilada.
- Marca: búsqueda pública sin hallazgos de "Gerarion" en PyPI/GitHub ni
  marcas homónimas en clases relevantes; verificar USPTO/EUIPO y whois
  oficial antes del anuncio público.
- Los nombres Nuvid (Keuphero…Ichtys, Tempalum, Soludyia…) no cambian: son
  contenido del calendario, no marca.

## 2.3.3-alpha — prepush (identidad del repositorio: verared, 2026-11)

Sin cambios normativos: la spec sigue siendo 2.0, los vectores y el kernel no
cambian. Antes del primer push público:

- **Marca anterior eliminada de todo el repositorio.** La organización
  responsable es `verared` (github.com/verared); el repo se publica como
  `github.com/verared/gerarion` y todas las URLs/metadatos apuntan ahí.
- **Créditos:** Gerardo Loyola (github.com/geroiloyola) es el creador único del
  Calendario Gerarion, de la lengua Nuvid y de la investigación original; el
  estándar GUS lo mantiene el proyecto verared (futura fundación).
- `AGENTS.md` añadido para trabajo asistido por IA en el repo.
- El fundamento histórico/cultural/religioso no se esconde: se conserva como
  documentación complementaria no normativa en `docs/papers/` (con README propio).
- Comentarios en código/tests que citaban "corpus v1 cap. N" ahora citan la
  spec GUS 2.0 (§3-§6); las erratas E-01..E-07 se referencian como
  `docs/history/errata-v1.2.md`.

## 2.3.2-alpha — prepush (rama `audit-fixes`, 2026-11)

Sin cambios normativos: la spec sigue siendo 2.0, los vectores y el kernel
no cambian. Preparación para el primer push.

### Decisión registrada
- **Semana independiente (decisión del autor: se mantiene).** La spec (ES y
  EN) declara ahora en normas que el ciclo de 7 días de GUS es independiente
  de la semana civil y que la letra S L M A T V B es etiqueta del formato,
  no día civil (ejemplo medido: 2026-03-17 = letra S).
- **Origen definido por JDN.** Día 0 = JDN 1.719.313; la conversión
  gregoriana proléptica queda como servicio de interoperabilidad, ejemplo
  derivado, no definición. NO se afirma equivalencia juliana (el mismo JDN
  en juliano da 23-mar-−5, verificado por cálculo).
- **TODO-003 CERRADO:** los nombres del formato son los canónicos; no hay
  nombres N0 canónicos en 2.0 (spec §6.1 ES/EN ajustada). TODO-001 y
  TODO-002 siguen abiertos.

### Cambios de repo
- Errata de textos culturales (fuera de este repositorio) eliminada del
  repo técnico; su resumen vive en la errata histórica (`docs/history/errata-v1.2.md`).
- Todas las URLs externas a otros repositorios eliminadas: el material
  histórico complementario vive en `docs/papers/` (no normativo).
- Tercer elemento de WEEKDAYS (nombre civil, no usado) neutralizado a
  posición del ciclo en `src/gerarion/calendar.py` y `web/gerarion.mjs`
  (sin cambio de comportamiento; conversancias en verde).
- Etiquetas civiles neutralizadas en errata-v1.2 (E-04/E-06) y
  lib-c-referencia.

## 2.3.1 — cierre alfa (rama `audit-fixes`, 2026-11)

Sin cambios normativos: la spec sigue siendo 2.0 y el draft D-001 (frontera
UTC/TAI) sigue en revisión de 90 días. Esta entrada cierra la versión alfa
del proyecto, lista para el primer push.

### Añadido
- **GUS-3339** (perfil): mapeo instante↔RFC 3339 UTC exacto, con vector set
  propio (`vectors/gus-3339-001.json`), implementación Python y JS y runner
  de conformancia (`web/profiles-conformance.mjs`, añadido a CI).
- **D-001 (borrador de decisión)**: frontera UTC/TAI — instante sobre TAI,
  día a medianoche TAI, adaptador UTC con tabla explícita, TAI pre-1958 como
  convención declarada. Resolución de TODO-001 en propuesta; pasa a RESUELTO
  solo tras la ventana de 90 días (GOVERNANCE §3.1).
- **GUS-3161** (perfil): marca GUS anclada en TSA RFC 3161 existente; sello
  en sidecar `gus3161-001`, TSA efímera local en e2e (subprocess openssl,
  stdlib; sin red), la TSA es testigo de existencia, nunca autoridad.
- **GUS-Roughtime** (perfil): receipts Ed25519 de testigos externos
  independientes del clúster, ligados al campo `anchor` de la GST; nonce
  anti-replay firmado; verificador Ed25519 RFC 8032 en Python puro (solo
  stdlib, referencia); el transporte UDP real queda abierto como TODO-002.
- **Verificador monolítico** `tools/verify_gus.py`: un solo archivo, solo
  stdlib, sin importar el paquete — núcleo + formato canónico + firma
  hash-only + anclaje; validado diferencialmente contra la librería.
- **GUS-for-notation**: documento corto de adopción mínima (EN normativo,
  ES espejo): solo formato canónico, instante, GUS-3339 y conformancia por
  vectores; sin criptografía ni notario.

### Notas
- Ningún vector del núcleo cambió; `gus-normative-001.json` intacto.
- Numeración de paquetes propuesta para la primera publicación: 2.3.0
  (ver tabla "Versiones" del README).

## 2.3.1 (rama `audit-fixes`, 2026-11 — correcciones de auditoría, no normativa)

Sin cambios normativos: la spec sigue siendo 2.0. Numeración de paquete
propuesta para la primera publicacion de estas correcciones.

### Corregido (auditoría)
- **Cifras**: firma SLH-DSA del set de referencia `SHA2-128f` = 17 088 B
  (medido), pk 32 B; nota añadida de que `128s` produciría firmas de
  ~7,9 KB pero no es el set usado. Firma hash-only (referencia, solo
  pruebas): 2 400 B en serialización binaria vs 9 354 B serializada en
  JSON — ambos valores distinguidos donde aparecían como "~9,4 KB".
- **Ventana solar 13–29 de marzo**: eliminada como garantía; la garantía
  normativa es la cota |Δ| < 7 días (propiedad del modelo: 1 Keuphero
  siempre Soludyia, corrección en pasos de 7 días); la ventana
  observada (10–21 de marzo en 11 000 años simulados) queda marcada
  como "observada, no estructural". Test ampliado a 11 000 años.
- **Frontera UTC/TAI**: nueva sección §9 de la spec (ES y EN)
  documentando exactamente lo que el código hace; lo no definido quedó
  registrado en `docs/history/TODO-pendientes.md` (TODO-001), no inventado.
- **Hoja WOTS**: docstrings marcan el esquema hash-only como referencia
  de pruebas (producción = SLH-DSA); `LeafLedger` persistente con
  bloqueo fcntl cierra el hueco de reutilización de hojas.
- **Catálogo de fallos**: Cloudflare 2017 (duración negativa en Go,
  sin smear ni overflow), IFC/Liga de Naciones 1937 (objeción a los
  días en blanco fuera del ciclo de 7), GNSS Mar Negro junio 2017,
  etíope septiembre 2007 — cada fila enlaza fuente primaria; el
  encabezado ya no promete "cada fila cita un hecho verificable".
- **Primera implementación hash-only** renombrada en docs como
  "esquema de referencia".

### Añadido
- `pyproject.toml`: extra opcional `[slh]` (= `slh-dsa==0.2.5` PyPI,
  verificado con `pip install -e '.[slh]'`).
- `NOTICE` (terceros: slh-dsa, LGPL-3.0-or-later, no vendorizado) y
  sección de licencia del README actualizada (ES y EN).
- `CITATION.cff` (v2.3.0, MIT + CC-BY-4.0; DOI/URL real pendientes).
- Tabla "Versiones" en README (ES y EN): spec 2.0 / draft IETF 2.1 /
  paquetes 2.3.0.
- `.gitignore`: `.env*`, `*.pem`, `*.key`, `notary-*.json`, `*.DS_Store`.

### Renombrado
- El borrador histórico antiguo con prefijo `draft-ietf-` quedó fuera del
  repositorio (obsoleto; ese prefijo está reservado a grupos de trabajo).

## 2.3.0 (2026-06 — estándar publicable)

### Añadido
- **Vectores normativos de máquina** (`vectors/gus-normative-001.json`):
  una sola fuente de verdad (constantes, Gran Tempalum, calendario, años,
  roundtrip gregoriano, formato, instantes, hashots, SLH-DSA, notario)
  que consumen Python, JavaScript y C. Cláusula de conformancia en
  `vectors/README.md`: una implementación es conforme si y solo si pasa
  el vector set.
- **Segunda implementación independiente en C** (`impl-c/`): cero
  dependencias, cero red, mismo vector set — conformancia por
  differential testing, no por autoridad.
- **Fuzzing y conformancia**: tests de parse hostil, propiedades de
  roundtrip e invariantes (`tests/test_fuzz.py`), y runner diferencial
  Python↔JS↔C (`tools/fuzz_diff.py`, 800/800 casos idénticos).
- **Draft IETF 2.1** (`docs/ietf/draft-gerarion-gus-00.xml`): xml2rfc v3,
  RFC 2119, ABNF, IANA (media type, códigos GERO_*, offsets TCJ).
- **Ciclo de vida notarial**: servicio de réplicas HTTP
  (`src/gerarion/notary_service.py`), despliegue reproducible
  (`deploy/`), runbook operativo (`docs/notary-runbook.md`), trust root
  firmada SLH-DSA (`tools/trust_root.py`), puente OpenTimestamps
  (`tools/ots_bridge.py`).
- **Publicación**: paquete PyPI `gerarion` (v2.3.0, wheel verificado),
  paquete npm `gerarion-kernel` (`web/package.json`), GitHub Pages del
  calculador (`.github/workflows/pages.yml`), SBOM CycloneDX
  (`sbom.cdx.json`).
- **Inglés normativo** (`docs/en/`): spec, threat model, erratas, informe
  de adopción y README con regla de precedencia EN > ES.

## 2.2.1 (2026-06 — informe de adopción)

- `docs/history/informe-adopcion-gus.md`: informe técnico senior argumentando la
  adopción del tiempo GUS sobre el régimen civil actual en cómputo —
  diagnóstico (4 causas raíz con incidentes públicos), propiedades
  verificables, comparativa de regímenes, evidencia test a test,
  estrategia de adopción por fases sin big-bang, riesgos y contras
  declarados. Enlazado desde el README.

## 2.2.0 (2026-06 — corpus universal por capas)

### Añadido
- `docs/universal/`: los 32 documentos del corpus reorganizados con el
  modelo de capas — Capa 0 núcleo normativo sin terminología confesional
  (11 docs), Capa 1 nombres y eventos como etiquetas estándar opacas con
  notas de origen (18 docs), Capa 2 documentos filosóficos/históricos no
  normativos (3 docs: Fundamentos, Eventos Clave, Anexo Hitos). El
  glosario queda en Capa 1 (la etimología es su contenido).
- `tools/build_universal_docs.py`: transformador idempotente y auditable
  (tabla de sustituciones exacta, sin reemplazos ciegos). Reglas
  principales: descriptores confesionales de reglas → equivalente
  funcional neutro; DY/AY y Yeshuvid conservan el nombre como etiquetas,
  su expansión histórica baja a nota de origen; la capa oficial del
  sistema pasa a ser la astronómica ("tradiciones" = forks opcionales);
  identificadores de código neutralizados (EVENTOS_FIJOS ante
  DIAS_SAGRADOS, FIXED_EVENT ante SACRED_DAY, etc.).
- `tests/test_docs_neutral.py`: 7 tests — espejo completo de archive,
  cabecera de capa en los 32 documentos, Capa 2 exacto, Capa 0 sin
  terminología confesional (regex), sin identificadores confesionales de
  código fuera de Capa 2, nombres estándar preservados en Capa 1.
- `docs/universal/README.md`: política de capas y principio central
  (tiempo por aritmética entera y anclas astronómicas; ninguna regla
  requiere creencia).

### Mantenido intacto
- `docs/archive/` (corpus original) y el contenido normativo de la v2.0.
- Nombres propios, vectores, JDN de origen y acumulador solar.

### Corregido
- E-07 (docs/history/errata-v1.2.md): aclaración estructural — el tiempo Gerarion
  no está anclado al gregoriano. Origen: 1 Keuphero del año 0 DY
  (JDN 1.719.313 = 21 de marzo de -5 = 6 a.C.); 6 a.C. es el año 0, no el
  año 01. Toda fecha gregoriana es equivalencia derivada (interop), nunca
  entrada normativa. Especificación reforzada con el párrafo
  "Independencia del calendario civil" (§3) y test
  `test_errata_e07_origin_independence`.

## 2.1.0 (2026-06 — no-falsificación de producción)

### Añadido
- Catálogo de fallos en el README: vulnerabilidades documentadas de los
  calendarios civiles existentes (gregoriano, judío, islámico, chino, etíope,
  persa) y de la infraestructura global de tiempo (leap seconds — Linux 2012,
  Cloudflare 2017; NTP monlist y crypto-Pi CVEs; spoofing GNSS Mar Negro 2011;
  Kerberos skew; block.timestamp en Ethereum; Y2038; folds/gaps DST), con el
  patrón de causas comunes que GUS 2.0 elimina por construcción.
- `src/gerarion/notary_cluster.py`: notario multi-réplica de producción.
  Quórum k-de-n, publicación de raíces diarias, exclusión de réplicas con
  derivación incorrecta y verificación standalone del bundle para
  consumidores externos.
- `src/gerarion/adapters.py`: adaptador SLH-DSA (FIPS 205) con
  SLH-DSA-SHA2-128S y 128F, integrado en `gts.create()`/`gts.verify()`
  por campo `alg`. Modo puro con contexto GUS2-TS.
- `web/`: calculador completo — puerto exacto del núcleo a JavaScript
  puro (`gerarion.mjs`, 18 vectores normativos idénticos a la suite
  Python), interfaz static (sin backend, sin cookies, sin telemetría)
  con reloj vivo, conversión bidireccional, normalización con flags
  visibles y self-test de vectores en el propio navegador.
  El test vector SLH-DSA en tests/test_adapters.py usa una clave
  generada para tests (digest de 96 bytes embebido) — NO es clave de
  producción.

### Notas
- La firma SLH-DSA de referencia hash-only sigue disponible y es la
  dependencia cero del núcleo; el adaptador es opcional.
- E2E del calculador con Playwright + Chromium headless (`e2e_web_test.py`):
  12 checks (carga sin errores JS, self-test en vivo, reloj en formato
  canónico, conversión bidireccional, flags weekday_corrected, errores
  GERO_* y aviso de file://) — 12/12 en verde.
- Suite: 75 tests Python + 18 vectores JavaScript en verde.

## 2.0.0 (2026-06 — versión inicial "100% nueva")

### Cambios rupturistas respecto al corpus v1.2
- Acumulador solar en microdías enteros exactos (antes: float).
- Erratas E-01..E-06 aplicadas (docs/history/errata-v1.2.md): ancla de año 2031,
  patrón Gran Tempalum, posición del Tempalum, corrección del vector
  Yeshuvid, código ejecutable, alfabeto canónico.
- Aritmética de instantes: escala continua sin segundos intercalares.
- Capa criptográfica nueva: GST firmada (hash-only reference) + notario
  diario Merkle encadenado. v1 no tenía capa de no-falsificación.
- La capa filosófica se reproduce como apéndice no normativo.

### Conservado de v1.2
- Estructura 12×30 + Tempalum; semana Nuvid invariante; origen JDN 1719313;
  reglas de normalización 1–7; formato canónico; día de semana calculado
  prevalece sobre el declarado.
