# Gerarion Time — Hoja de Ruta Técnica y Visión Verificable

> **Brújula Técnica Viva y No Vinculante — Cero Promesas, Cero Fechas Fijas.**
>
> *Gerarion Time* es una infraestructura temporal abierta, modular,
> *offline-first* y verificable que **complementa —sin reemplazar— a UTC, NTP,
> PTP y los relojes del sistema operativo**. Este documento es una brújula
> técnica viva, **no un contrato, ni una promesa de entrega ni un cronograma
> con fechas fijas**. Cada casilla `[x]` exige evidencia reproducible en este
> repositorio; cada casilla `[ ]` representa una dirección aspiracional que
> *podría* construirse a meses o años vista si el proyecto y la comunidad
> avanzan en esa dirección.
>
> - **Línea base auditada:** `v3.3.0`
> - **Especificación normativa:** `GUS v3.0.0` (aritmética y vectores congelados)
> - **Versión normativa en inglés:** [`ROADMAP.md`](ROADMAP.md) (en caso de divergencia prevalece EN > ES)
> - **Referencias relacionadas:** [`COMPATIBILITY.md`](COMPATIBILITY.md) · [`docs/architecture/SATELLITE-REPOS.es.md`](docs/architecture/SATELLITE-REPOS.es.md) · [`docs/guides/CMS-INTEGRATION.es.md`](docs/guides/CMS-INTEGRATION.es.md) · [`SECURITY.md`](SECURITY.md) · [`docs/audit/AUDIT-REPORT-v3.0.0.md`](docs/audit/AUDIT-REPORT-v3.0.0.md)

---

## Horizontes de Evolución (Sin Fechas Cerradas)

- **Corto plazo (consolidación y adopción real):** Integración práctica de
  `gt-core`, `gt-gst` y `gt-gts` en aplicaciones reales (servicios web, APIs,
  registros auditables), mejor ergonomía de consumo de satélites autónomos,
  cobertura explícita de CI en 32 bits y guías de despliegue embebido.
- **Mediano plazo (perfiles experimentales e infraestructura de plataforma):**
  Prototipos funcionales con vectores reproducibles para `gt-tslr` y
  `gt-gcerts`, adaptadores en espacio de usuario en Linux (`CLOCK_TAI` +
  entradas verificadas de `chrony`/PTP) y custodia de claves en hardware
  (`TPM`/`HSM`) desarrollados en repositorios satélite separados.
- **Largo plazo (validación externa y ecosistema abierto):** Auditorías
  criptográficas independientes de terceros, implementaciones interoperables
  creadas por terceros a partir de [`docs/specs/`](docs/specs/GUS.es.md),
  revisión formal ante organismos de estándares (IETF) e integración de
  escritorio/sistema operativo solo tras madurez demostrada en espacio de
  usuario.

---

## Modelo de Madurez en 4 Niveles y Matriz del Ecosistema

Ningún módulo sube de nivel solo por tener código o por declararse estable en
un README; avanzar exige artefactos verificables, pruebas automatizadas y —para
afirmaciones de seguridad en producción— revisión externa independiente.

| Nivel | Definición |
|---|---|
| `EXPERIMENTAL` | Especificación y/o prototipo inicial; sujeto a cambios; no apto para producción. |
| `IMPLEMENTED` | Existe código de referencia funcional, pero falta paridad completa entre plataformas o endurecimiento. |
| `VERIFIED` | Verificado de forma cruzada contra vectores normativos compartidos y suites automatizadas en CI (`reuse`, unitarias, conformancia, fuzz/sanitizers). |
| `STABLE` | Contrato normativo congelado (`>=3.2.0,<4.0.0`), verificado entre plataformas y reproducible mediante `EXPORT-MANIFEST.json`. *(El uso criptográfico crítico en producción exige además auditoría externa + custodia en hardware.)* |

### Matriz del Ecosistema (`v3.3.0`, alineada con [`COMPATIBILITY.md`](COMPATIBILITY.md))

| Satélite | Especificación | Madurez (`v3.3.0`) | Alcance y límites honestos |
|---|---|---|---|
| `verared/gt-core` | [`TCJ.es.md`](docs/specs/TCJ.es.md), [`GUS.es.md`](docs/specs/GUS.es.md) | **STABLE / VERIFIED** | Núcleo `GUS v3.0.0` congelado; C11 sin `malloc`, Python y JS; 100 % autónomo. |
| `verared/gt-gus` | [`GUS.es.md`](docs/specs/GUS.es.md) | **STABLE / VERIFIED** | Sintaxis canónica 29/32 caracteres, reglas de normalización 1–7, `quick_verify`, `int64` + `nanos`. |
| `verared/gt-tcj` | [`TCJ.es.md`](docs/specs/TCJ.es.md) | **STABLE / VERIFIED** | `TCJ = TAI + 8.400 s`, puente `TAI−UTC` versionado `IERS-C-2026.1` con aviso de horizonte. |
| `verared/gt-calendar` | [`CALENDAR.es.md`](docs/specs/CALENDAR.es.md) | **STABLE / VERIFIED** | Calendario regular `AY`/`DY` + motor determinista GUTI-1 en 10 sistemas calendáricos. |
| `verared/gt-gts` | [`GTS.es.md`](docs/specs/GTS.es.md) | **STABLE (núcleo) / EXPERIMENTAL (Roughtime)** | Máquina de estados de confianza (`VERIFIED`/`HOLDOVER`/`UNVERIFIED`/`REJECTED`) + anti-rollback sub-segundo; el perfil Roughtime es experimental. |
| `verared/gt-gst` | [`GST.es.md`](docs/specs/GST.es.md) | **Referencia STABLE (`GST v2`); auditoría externa pendiente** | Firma híbrida **Ed25519 + ML-DSA** sobre RFC 8785 JCS, `GUS3-GST-V2`, anti-downgrade, `ReplayGuard` *fail-closed*, notario Merkle diario opcional. **Requiere auditoría criptográfica independiente de terceros y custodia TPM/HSM antes de uso crítico en producción.** `WOTS+` legado está deprecado (`src/gerarion/deprecated/hashots.py`). |
| `verared/gt-interop` | [`INTEROP.es.md`](docs/specs/INTEROP.es.md) | **STABLE (`RFC 3339` / `ISO 8601` / `Unix`) / EXPERIMENTAL (`RFC 3161`)** | Parser estricto GUS-3339 con vectores negativos compartidos; el perfil `RFC 3161` TSA es experimental. |
| `verared/gt-tslr` | [`TSLR.es.md`](docs/specs/TSLR.es.md) | **EXPERIMENTAL** | Solo especificación y andamiaje vacío; sin implementación de referencia todavía. |
| `verared/gt-gcerts` | [`GCERTS.es.md`](docs/specs/GCERTS.es.md) | **EXPERIMENTAL** | Solo especificación y andamiaje vacío; sin implementación de referencia todavía. |

---

## Hoja de Ruta Maestra (10 Fases + Ejes Transversales)

### Fase 1 — Fundamento Temporal (`gt-core`, `gt-tcj`, `gt-gus`)
**Objetivo:** Congelar una coordenada atómica determinista sin segundos intercalares (`TCJ = TAI + 8.400 s`), sintaxis inequívoca de 29/32 caracteres y aritmética entera idéntica bit a bit en C11, Python y JavaScript.

- [x] Especificación normativa `GUS v3.0.0` congelada y fichas por dominio (`docs/spec/gus-3.0.0.md`, `docs/specs/TCJ.es.md`, `docs/specs/GUS.es.md`).
- [x] Escala atómica continua `TCJ = TAI + 8.400 s` con límites enteros exactos y `nanos` separado (`impl-c/core/gus_core.c`, `src/gerarion/core/calendar.py`, `web/engine/core.mjs`).
- [x] Sintaxis canónica de 32 caracteres y compacta de 29, reglas de normalización 1–7 y `quick_verify` (`impl-c/core/gus_core.c`, `src/gerarion/core/format.py`, `web/engine/core.mjs`).
- [x] Vectores CC0 compartidos (normativos, `quick_verify` y regresión `AY`) verificados en los tres runtimes (`vectors/gus-normative-003.json`, `vectors/gus-quickverify-001.json`, `vectors/gus-regression-001.json`, `tests/test_conformance.py`, `tools/fuzz_diff.py`).

**Criterio de aceptación:** Cero divergencias entre C11, Python y JS sobre todos los vectores normativos y fuzzing diferencial.

---

### Fase 2 — Motor Universal de Traducción Calendárica (`gt-calendar`)
**Objetivo:** Proveer traducción bidireccional determinista en aritmética entera pura entre 10 sistemas calendáricos pivotando sobre `day_index` / `JDN`, sin red ni dependencias de `Intl`.

- [x] Motor GUTI-1 determinista de 10 sistemas (`gus`, `greg`, `julian`, `egyptian`, `ethiopic`, `bahai`, `maya`, `islamic`, `hebrew`, `chinese`) en C11, Python y JS (`impl-c/calendars/gerarion_calendars.c`, `src/gerarion/calendars/engine.py`, `web/engine/guti.mjs`).
- [x] Tabla lunisolar china offline versionada (1645–2650) con rechazo estricto fuera de rango (`impl-c/calendars/china_table.c`, `src/gerarion/calendars/china_table.py`, `web/engine/china-table.mjs`).
- [x] Verificación cruzada con 63.850+ vectores GUTI y tolerancias históricas documentadas (`vectors/guti-calendars-001.json`, `tests/test_guti_calendars.py`, `docs/spec/CALENDAR-ENGINE.md`).
- [ ] Perfiles opcionales de extensión GUTI-2 (calendarios regionales/históricos adicionales o rangos astronómicos ampliados más allá de 1645–2650, solo con tablas y vectores verificables).

**Criterio de aceptación:** Paridad bit a bit entre C11, Python y JS sobre `vectors/guti-calendars-001.json`, sin extrapolación silenciosa fuera de rangos validados.

---

### Fase 3 — Runtime Portable y Bindings
**Objetivo:** Garantizar que el núcleo corra limpiamente desde microcontroladores *bare-metal* hasta servidores y navegadores, sin asignación dinámica ni dependencias ocultas de plataforma.

- [x] Biblioteca C11 autónoma `libgerarion-core` sin `malloc` ni reloj de SO, compilada con `-Wall -Wextra -Werror` en GCC/Clang (`impl-c/core/gus_core.c`, `impl-c/Makefile`, `tests/test_export_module.py`).
- [x] Núcleo Python en biblioteca estándar pura y motor JavaScript ESM sin dependencias con `BigInt` (`src/gerarion/core/`, `web/engine/core.mjs`).
- [x] Vectores de conformancia compartidos y pruebas de ensamblado cruzado de satélites en C11, Python y JS (`tests/test_satellite_integration.py`, `.github/workflows/ci.yml`).
- [ ] Matriz explícita de CI en arquitecturas de 32 bits (p. ej. `i686` / `armv7` / `arm-none-eabi` con compilación cruzada y ejecución de vectores).
- [ ] Política formal de estabilidad ABI en C a largo plazo y gate automatizado de ABI entre versiones menores.
- [ ] Guías detalladas de despliegue embebido/*bare-metal* (presupuestos de memoria, puente tick-a-TCJ, perfiles estáticos).

**Criterio de aceptación:** Compilación limpia y conformancia de vectores en 64 bits, 32 bits y *bare-metal* con contrato ABI documentado.

---

### Fase 4 — Infraestructura Offline-First
**Objetivo:** Garantizar que conversión, serialización y verificación funcionen 100 % sin conexión, sin APIs externas, rastreadores ni *fallbacks* silenciosos a red.

- [x] Portal web 100 % cliente con Service Worker *fail-closed* y CSP restrictiva (`web/sw.js`, `e2e_web_test.py`).
- [x] Verificación en sandbox sin red para núcleo y conversión calendárica (`tests/test_guti_m0_sandbox.py`, `tools/verify_gus.py`).
- [x] Verificación offline autónoma de satélites exportados mediante `EXPORT-MANIFEST.json` (`tools/export_module.py`, `tests/test_satellite_integration.py`).
- [ ] Flujo automatizado y auditable para actualizar tablas `TAI−UTC` del IERS antes de que expire su horizonte (`IERS-C-2026.1` / transición CGPM 2027 a UTC continuo).

**Criterio de aceptación:** Cero peticiones salientes de red durante conversión, serialización o verificación, demostrado por pruebas de sandbox y E2E Playwright en modo avión.

---

### Fase 5 — Confianza Temporal y Sincronización (`gt-gts`)
**Objetivo:** Separar estructuralmente la medición monotónica de intervalos del tiempo absoluto autenticado y hacer explícita la incertidumbre del reloj.

- [x] Máquina de estados de confianza de reloj (`VERIFIED`, `HOLDOVER`, `UNVERIFIED`, `REJECTED`) en Python y C11 (`src/gerarion/gts/clock.py`, `impl-c/clock/gus_clock.c`, `docs/specs/GTS.es.md`).
- [x] Anclas persistentes anti-rollback sub-segundo `(instant, nanos)` y política explícita `require_authenticated` (`tests/test_clock_state.py`, `impl-c/conformance.c`).
- [x] Perfil experimental de verificación de recibos Roughtime (`src/gerarion/gts/roughtime.py`, `tests/test_profiles_roughtime.py`).
- [ ] Suite distribuida de inyección de fallos para particiones de red y *split-brain* en flotas multi-fuente.
- [ ] Validación en hardware real con receptores GNSS, *grandmasters* PTP y curvas reales de deriva en *holdover*.

**Criterio de aceptación:** Transiciones deterministas ante retrocesos, fuentes no autenticadas y agotamiento de *holdover*, validadas tanto en simulación como en hardware de temporización real.

---

### Fase 6 — Evidencia Criptográfica Temporal (`gt-gst`)
**Objetivo:** Proveer sobres temporales verificables y resistentes a computación cuántica (`GST v2`) con canonicalización estricta, protección anti-downgrade y anti-replay *fail-closed*.

- [x] Sobre normativo `GST v2` (`gerarion.gst.v2`) con firma híbrida **Ed25519 + ML-DSA**, RFC 8785 JCS (límite entero `±(2^53 - 1)`), separación de dominio `GUS3-GST-V2`, protección anti-downgrade y `VerificationResult` en 3 niveles (`src/gerarion/gst/v2.py`, `src/gerarion/gst/envelope.py`, `src/gerarion/gst/jcs.py`, `src/gerarion/gst/adapters.py`, `docs/specs/GST.es.md`).
- [x] Registro de confianza de claves (`KeyRegistry` / `TrustedKeyRecord`) con comparación en tiempo constante, rotación histórica (`HISTORICAL`), expiración (`KEY_EXPIRED`) y revocación (`KEY_REVOKED`), más `SQLiteReplayStore` transaccional concurrente (`WAL`, `BEGIN IMMEDIATE`) y notario Merkle diario opcional (`src/gerarion/gst/trust.py`, `src/gerarion/gst/replay.py`, `src/gerarion/gst/notary.py`, `tests/test_gst_v2_security.py`, `docs/guides/CMS-INTEGRATION.es.md`).
- [x] `WOTS+` legado aislado en `src/gerarion/deprecated/hashots.py` con `DeprecationWarning`, fuera del perfil normativo `GST v2`.
- [ ] Integración física con custodia de claves en hardware (`TPM`/`HSM`) y validación productiva en repositorio externo de CMS (`GEIACT-1`).
- [ ] Vectores criptográficos independientes del lenguaje para verificación cruzada externa de sobres `GST v2`.
- [ ] **Auditoría criptográfica independiente de terceros** sobre `gt-gst` y el notario Merkle antes de uso crítico en producción.

**Criterio de aceptación:** Informe cerrado de auditoría criptográfica externa sin hallazgos críticos/altos sin mitigar, perfil de custodia en hardware y verificador independiente de terceros pasando vectores compartidos.

---

### Fase 7 — Interoperabilidad (`gt-interop`)
**Objetivo:** Tender puentes limpios con formatos civiles heredados en las fronteras del sistema sin comprometer la monotonicidad interna de TCJ.

- [x] Tabla `TAI−UTC` versionada (`IERS-C-2026.1`) con marca explícita de extrapolación tras su horizonte (`src/gerarion/tcj/tai.py`, `impl-c/tai/gus_tai.c`, `web/engine/tcj-tai.mjs`).
- [x] Puentes bidireccionales estrictos para `RFC 3339` (`GUS-3339`), `ISO 8601` y `Unix` con vectores positivos y negativos compartidos (`src/gerarion/interop/profiles.py`, `vectors/gus-3339-002.json`, `vectors/gus-3339-negative-001.json`, `tests/test_profiles.py`, `tests/test_profiles_negative.py`).
- [x] Adaptador experimental `RFC 3161` TSA sidecar (`src/gerarion/interop/tsa.py`, `tests/test_profiles_tsa.py`, `docs/specs/INTEROP.es.md`).
- [ ] Soporte para anotaciones extendidas **RFC 9557** (sufijos explícitos de zona horaria y calendario).
- [ ] Maduración productiva de verificación `RFC 3161` TSA y puentes de observación `NTP`/`NTS`/`PTP` en plataformas reales.

**Criterio de aceptación:** Conformancia estricta de ida y vuelta en vectores positivos y negativos para RFC 3339, RFC 9557 y puentes autenticados externos de sellado y sincronización.

---

### Fase 8 — Contexto Astronómico y Físico (`gt-tslr`)
**Objetivo:** Explorar verificación astronómica forense opcional de Nivel 3 (*Tiempo Solar Local Real*), completamente aislada del núcleo normativo.

- [x] Especificación experimental de dominio y andamiaje de satélite publicados (`docs/specs/TSLR.es.md`, `docs/specs/TSLR.en.md`, `verared/gt-tslr`).
- [ ] Motor determinista de cálculo de posición solar (especificación algorítmica + implementación de referencia en `gt-tslr`).
- [ ] Perfil de contraste con `UT1` / efemérides JPL `DE440` mediante tablas offline versionadas.
- [ ] Modelo explícito de propagación de incertidumbre geográfica/altitudinal y vectores CC0 reproducibles.

**Criterio de aceptación:** Vectores reproducibles de contexto solar contrastados contra efemérides astronómicas publicadas dentro de las cotas de incertidumbre declaradas, sin alterar `gt-core`.

---

### Fase 9 — Perfiles Temporales de Certificados (`gt-gcerts`)
**Objetivo:** Definir ventanas inequívocas de validez temporal sobre coordenadas TCJ para certificados PKI, aisladas del núcleo normativo.

- [x] Especificación experimental de dominio y andamiaje de satélite publicados (`docs/specs/GCERTS.es.md`, `docs/specs/GCERTS.en.md`, `verared/gt-gcerts`).
- [ ] Semántica implementada de evaluación `notBefore` / `notAfter` sobre coordenadas TCJ.
- [ ] Políticas explícitas de verificación bajo estados de reloj `HOLDOVER` y `UNVERIFIED`.
- [ ] Perfil de interoperabilidad/extensiones X.509, vectores reproducibles y revisión independiente de seguridad.

**Criterio de aceptación:** Evaluación inequívoca de vigencia de certificados frente a estados de confianza de reloj con vectores de prueba y revisión externa de seguridad PKI.

---

### Fase 10 — Integración con Sistemas Operativos e Infraestructura (Satélites Externos Futuros)
**Objetivo:** Habilitar adopción incremental en Linux, sistemas embebidos y observabilidad mediante bibliotecas y adaptadores en espacio de usuario, sin apresurar cambios en kernel.

- [x] Publicación de artefactos autónomos `libgerarion` y `libgerarion-core` con `SHA256SUMS.txt` (`.github/workflows/release.yml`, `v3.3.0`).
- [ ] Demonio en espacio de usuario Linux que lea `CLOCK_TAI` + estado de `chrony`/PTP hacia estados de confianza `gt-gts`.
- [ ] Ejemplos de referencia embebidos e industriales (integración C11 *bare-metal* + RTOS).
- [ ] Integración con observabilidad (p. ej. atributos de marca temporal en OpenTelemetry y exportadores `GST v2`).
- [ ] Exploración de herramientas `systemd`/escritorio y evaluación futura de interfaces de kernel solo tras madurez demostrada en espacio de usuario.

**Criterio de aceptación:** Adaptadores en espacio de usuario probados en operación real junto a los servicios estándar de hora del SO, sin exigir kernels a medida.

---

### Eje Transversal A — Integridad del Ecosistema y Releases Reproducibles
**Objetivo:** Garantizar que cada repositorio satélite sea una proyección verificable byte a byte de un commit etiquetado en `verared/gerarion`.

- [x] Exportación determinista desde commit versionado con `EXPORT-MANIFEST.json` (`gerarion-export-manifest/1`), soporte de firma Ed25519 separada (`EXPORT-MANIFEST.json.sig` vía `--sign-key` / `--trusted-pub-key`) y `--verify-existing` (`tools/export_module.py`, `tests/test_export_module.py`, `COMPATIBILITY.md`, `compatibility.json`).
- [x] Pruebas de integración cruzada sobre satélites ensamblados limpiamente en C11, Python y JS, como gate obligatorio en CI (`tests/test_satellite_integration.py`, `.github/workflows/ci.yml`).
- [x] Conformidad REUSE 3.3 al 100 % y SBOM CycloneDX 1.5 (`REUSE.toml`, `sbom.cdx.json`, `.github/workflows/ci.yml`).
- [ ] Firma automatizada OIDC/Sigstore o respaldada por hardware en CI de tags de release y `EXPORT-MANIFEST.json.sig` en los 9 repositorios satélite.
- [ ] Runbook formal de rollback y sincronización de emergencia multi-satélite.

**Criterio de aceptación:** Cada tag de release y exportación satélite es reproducible deterministamente, verificada por hash, conforme en licencias y atestada criptográficamente.

---

### Eje Transversal B — Seguridad, Fiabilidad y Conformancia
**Objetivo:** Mantener pruebas adversariales continuas, seguridad de memoria y un modelo de amenazas honesto en todas las implementaciones.

- [x] Fuzzing diferencial entre Python, JS y C11 (`tools/fuzz_diff.py`, `impl-c/audit_stress.c` — 1M+ idas y vueltas) y auditoría de estrés ASan + UBSan (6,5M+ comprobaciones, 0 errores, `impl-c/Makefile`).
- [x] Suites adversariales para JCS, anti-downgrade, `ReplayGuard`, rollback sub-segundo y análisis estático (`tests/test_jcs_gstv2.py`, `tests/test_adversarial_security.py`, `tests/test_clock_state.py`, `.github/workflows/codeql.yml`).
- [x] Modelo de amenazas, política de seguridad e informe de auditoría interna publicados (`docs/spec/threat-model.md`, `SECURITY.md`, `docs/audit/AUDIT-REPORT-v3.0.0.md`).
- [ ] Revisión independiente de seguridad de terceros sobre todo el stack criptográfico y notarial.
- [ ] Programa formal de divulgación/recompensas de vulnerabilidades (cuando despliegues externos de producción lo justifiquen).

**Criterio de aceptación:** Cero fallos sin mitigar de seguridad de memoria o conformancia en CI, más cierre de auditoría externa antes de afirmar seguridad criptográfica de producción.

---

## Diez Principios Arquitectónicos

1. **Abierto (*Open*):** Especificaciones públicas, código de referencia con licencia dual (`MIT OR Apache-2.0`), documentación `CC-BY-4.0` y vectores `CC0-1.0`.
2. **Descentralizado (*Decentralized*):** `TCJ` es un desplazamiento matemático (`TAI + 8.400 s`), no un servidor central; verificar jamás depende de una autoridad única.
3. **Offline-First:** Aritmética del núcleo, traducción entre 10 calendarios y verificación criptográfica operan con cero peticiones de red.
4. **Determinista (*Deterministic*):** Aritmética entera pura entre C11, Python y JavaScript con salidas idénticas bit a bit para toda entrada válida.
5. **Portable (*Portable*):** Núcleo C11 sin `malloc`, núcleo Python en stdlib pura y JavaScript ESM sin dependencias, desde microcontroladores hasta navegadores.
6. **Interoperable (*Interoperable*):** Puentes auditables en frontera hacia `UTC`, `TAI`, `Unix`, `RFC 3339`, `ISO 8601` y `RFC 3161` sin mutar la coordenada interna.
7. **Verificable (*Verifiable*):** Cada afirmación se respalda con vectores CC0 compartidos, hashes reproducibles en `EXPORT-MANIFEST.json` y verificación *fail-closed*.
8. **Modular (*Modular*):** Satélites independientes por dominio (`verared/gt-*`) para adoptar solo lo necesario sin arrastrar toda la suite.
9. **Abierto y No Propietario (*Referencia Normativa Transparente*):** Estándar abierto sin autoridad central ni propiedad comercial, con época y meridiano normativos (`TCJ`) documentados con total transparencia y traducción bidireccional imparcial entre 10 sistemas calendáricos.
10. **Transparente (*Transparent*):** Límites de madurez honestos, no-garantías explícitas y separación clara entre lo verificado con código y el trabajo aspiracional.

---

## Visión a Largo Plazo

La infraestructura digital merece un tiempo que sea **interpretable** entre
culturas y calendarios sin ambigüedad, **contextualizable** frente a escalas
físicas y atómicas de referencia, **verificable** sin conexión por cualquier
parte sin confiar en un servidor único y **demostrable** mediante evidencia
criptográfica post-cuántica auditada en abierto.

*Gerarion Time* avanza hacia esa visión un artefacto verificado a la vez:
**ninguna casilla de este documento se marca `[x]` sin evidencia reproducible
en el repositorio.**
