# Changelog — GUS

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
  `docs/errata-v1.2.md`.

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
  repo técnico; su resumen vive en la errata histórica (`docs/errata-v1.2.md`).
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
  registrado en `docs/TODO-pendientes.md` (TODO-001), no inventado.
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

- `docs/informe-adopcion-gus.md`: informe técnico senior argumentando la
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
- E-07 (docs/errata-v1.2.md): aclaración estructural — el tiempo Gerarion
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
- Erratas E-01..E-06 aplicadas (docs/errata-v1.2.md): ancla de año 2031,
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
