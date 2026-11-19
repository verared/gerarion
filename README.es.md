# Gerarion Universal Standard (GUS)

🌐 English: **[README.md](README.md)** — este documento es el espejo en
español; en caso de divergencia prevalece la versión inglesa (EN > ES).

[![CI](https://github.com/verared/gerarion/actions/workflows/ci.yml/badge.svg)](https://github.com/verared/gerarion/actions/workflows/ci.yml)

## Estado de madurez en tres ejes (`v3.2.2`)

| Eje | Estado | Alcance y límites |
|---|---|---|
| **1. Especificación y aritmética (`GUS v3.0.0` + 10 calendarios)** | **Congelada y verificada** | Aritmética entera determinista (`TCJ = TAI + 8.400 s`, `AY`/`DY` simétrico, GUTI-1 en 10 sistemas calendáricos), verificada bit a bit entre Python, JavaScript y C11 contra `vectors/*.json`. |
| **2. Implementaciones de referencia (`v3.2.2`)** | **Estables y probadas en CI** | `gt-core`, `gt-gus`, `gt-tcj`, `gt-calendar`, `gt-gts`, `gt-gst` y `gt-interop` son estables y se verifican continuamente en CI (unitarias, conformancia, ASan/UBSan, fuzzing diferencial, E2E e integración de satélites ensamblados). `gt-tslr` y `gt-gcerts` están en estado **EXPERIMENTAL** (especificación + andamiaje, sin implementación de referencia aún). Ver [COMPATIBILITY.md](COMPATIBILITY.md). |
| **3. Aseguramiento criptográfico de producción** | **Requiere auditoría externa** | `gt-gst` (`GST v2`) y el notario Merkle diario requieren una **auditoría criptográfica independiente de terceros** y **custodia de claves en hardware (TPM/HSM)** antes de decisiones críticas de producción. Ver [SECURITY.md](SECURITY.md) y [docs/spec/threat-model.md](docs/spec/threat-model.md). |

### Gerarion Time — Estado del Proyecto y Visión

En **`v3.2.2`**, el núcleo congelado `GUS v3.0.0` (`TCJ = TAI + 8.400 s`), el motor GUTI-1 de 10 calendarios, la referencia `GST v2` (Ed25519 + ML-DSA sobre RFC 8785 JCS) y los **9 repositorios satélite** (`verared/gt-*`) están publicados y verificados en CI. *Gerarion Time* complementa —sin reemplazar— a UTC, NTP, PTP y los relojes del SO.

- **Foco próximo:** adopción real de `gt-core`, `gt-gst` y `gt-gts`, matriz CI en 32 bits y guías de despliegue embebido.
- **Mediano plazo:** prototipos funcionales + vectores para los perfiles experimentales `gt-tslr` y `gt-gcerts`, adaptadores Linux en espacio de usuario (`CLOCK_TAI`) y custodia en hardware (`TPM`/`HSM`).
- **Largo plazo:** auditorías criptográficas independientes de terceros, implementaciones de terceros y revisión formal de estándares (sin fechas fijas ni promesas de entrega).
- **Explorar:** [ROADMAP.es.md](ROADMAP.es.md) · [ROADMAP.md](ROADMAP.md) · [COMPATIBILITY.md](COMPATIBILITY.md) · [`docs/specs/`](docs/specs/GUS.es.md)

**Tiempo regular, universal y verificable.**

## Probar en línea (sin instalar nada, sin cuentas)

El **traductor de fechas** corre íntegramente en el navegador en
<https://verared.github.io/gerarion/>: introduce una fecha en cualquiera de
los diez calendarios soportados (Gerarion GUS 3.0.0 —incluidos años AY de
5–6 dígitos—, gregoriano/juliano prolépticos, egipcio, etíope, bahá'í,
cuenta larga maya, hebreo, islámico y chino) y obtén todas las equivalencias
de golpe, con enlaces compartibles por fecha (`#cal=…&d=…`), reloj GUS en
vivo, calendario del mes y calculadora de distancias. Sin peticiones de red,
sin cookies, sin cuentas; funciona sin conexión una vez cargada.
Para opciones de instalación (Python, JS, C11) por GitHub Releases, mira la
sección de distribución del README en inglés `README.md`.

Una especificación abierta y proyecto de estándar de tiempo que integra tres capas bajo una misma especificación verificable por máquina:

1. **Calendario regular:** 12 meses de 30 días exactos + Tempalum de cierre
   (4/11 días). Toda fecha fija cae siempre en el mismo día de la semana.
2. **Escala continua:** instantes lineales sobre base TAI con la tabla
   histórica IERS TAI−UTC, coordinados mediante TCJ = TAI + 8.400 s
   (Jerusalén; ver [Escala de tiempo](#escala-de-tiempo)). Comparaciones,
   rangos y totales triviales en cualquier lenguaje.
3. **Marca temporal verificable (`GST v2`):** firma híbrida **Ed25519 +
   ML-DSA** sobre payload canonicalizado con **RFC 8785 (JCS)**, protección
   anti-downgrade, `ReplayGuard` *fail-closed* y notario Merkle diario
   opcional.

### Perfil criptográfico normativo (`GST v2`)

| Aspecto | Declaración normativa |
|---|---|
| **Algoritmo normativo (`GST v2`)** | Firma híbrida **Ed25519 + ML-DSA** sobre payload canonicalizado con **RFC 8785 (JCS)** (enteros estrictamente dentro de IEEE-754 `binary64` `±(2^53 - 1)`), separación de dominio `GUS3-GST-V2`, descriptor de algoritmos y claves incluido dentro de los bytes firmados (protección **anti-downgrade**), contador monotónico `seq` + `nonce` con `ReplayGuard` *fail-closed* y notario Merkle diario opcional. |
| **Algoritmo deprecado / educativo** | `WOTS+` / `WotsMerkleSigner`, aislado en `src/gerarion/deprecated/hashots.py` con `DeprecationWarning` explícito; **fuera** del perfil normativo `GST v2` y no apto para producción. |
| **Cobertura de pruebas y límite de auditoría** | **Cubierto por vectores normativos y pruebas automatizadas:** núcleo aritmético, RFC 8785 JCS (incluyendo entradas hostiles y rechazo de enteros `> 2^53 - 1`), verificación dual híbrida, rechazo anti-downgrade, `ReplayGuard` *fail-closed*, anclas anti-rollback sub-segundo e integración de satélites ensamblados. **Pendiente:** auditoría criptográfica externa independiente de `gt-gst` / notario y custodia de claves en hardware (TPM/HSM) para despliegues de producción. |

Las garantías exactas —y lo que GUS **no** garantiza— están declaradas en
["Qué NO garantiza GUS"](#qué-no-garantiza-gus) y en el
[modelo de amenazas](docs/spec/threat-model.md). Este README evita
sobrepromesas a propósito: la credibilidad es el producto: un lector escéptico que encuentra
un error factual duda de todo lo demás.

---

## La idea en 30 segundos

```
2026-05-23 (gregoriano)  →  2031DY-03-08-T  (GUS canónico)
```

Anatomía del formato `AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O]`:

| Campo | Ejemplo | Qué es |
|---|---|---|
| `AAAA` + era | `2031DY` | Año 2031 de la era **DY** (después del origen). `AY` cuenta hacia atrás. El día 0 es 1 Keuphero del año 0 |
| `MM-DD` | `03-08` | Mes 3, día 8 → 68 días tras el inicio del año. Meses de 30, sin excepciones |
| `X` | `T` | Letra del día de la semana Nuvid (`S L M A T V B` = Soludyia…Sabatyeh). Se **calcula** del índice de día: si lo que declaras no coincide, lo corrige el parser (`weekday_corrected`) |
| `HH:MM:SS` | `09:30:00` | Hora del día. El instante canónico es un entero único: `day_index × 86.400 + s` sin segundos intercalares |
| `CC` | `SC` | Ciclo luminoso (etiqueta semántica, no aritmética): `SC` 06:00–17:59, `LC` 18:00–05:59 |
| `TCJ±O` | `TCJ+0` | Offset civil (presentación). El instante canonico no lo cambia |

Estructura del año:

| Año | Días | Semanas | Tempalum | Determinado por |
|---|---|---|---|---|
| Común | 364 | 52 exactas | 4 días | recurrencia entera |
| **Gran Tempalum** | 371 | **53 exactas** | 11 días | la misma recurrencia |

Los años GT se conocen por recurrencia aritmética para todo n (los
primeros del ciclo corto: 5, 11, 16, 22, 28, 33, 39, 45 — el año 2031DY
empieza el 17 de marzo de 2026 gregoriano). **1 Keuphero siempre es
Soludyia**: GUS sí tiene años de 53 semanas, pero la semana 53 es
estructural, determinista de antemano y con nombre propio (los 11 días del
Gran Tempalum) — no una anomalía que las librerías resuelven cada una a su
manera como en ISO 8601. Conceptualmente el Tempalum es una **semana
intercalar** (leap week), como en Symmetry454 o Pax — con la propiedad
crítica de que 364 y 371 son múltiplos de 7: nunca hay días fuera del
ciclo semanal (ver [Trabajos relacionados](#trabajos-relacionados)).

Nombres como **Keuphero** (mes 1), **Tempalum** (mes de cierre), las letras
de día y las eras DY/AY son *etiquetas opacas* de la especificación: ninguna regla
normativa depende de su significado. Su etimología, filosofía y notas de
origen tienen un origen cultural documentado fuera de este repositorio
(no publicado).

> ⓘ **Resumen.** GUS es una especificación abierta y proyecto de estándar de tiempo: un calendario regular 12×30
> con un «Tempalum» de cierre (años de 53 semanas incluidos, a propósito),
> una escala continua de tiempo sin segundos intercalares (ver
> [Escala de tiempo](#escala-de-tiempo)), y
> marcas temporales verificables post-cuánticas (GST) con un notario
> diario Merkle encadenado. El README completo en inglés es
> [`README.md`](README.md); la spec normativa en inglés vive en
> [`docs/en/`](docs/en/). Los textos originales en español quedan como
> espejos informativos.

## Instalación

Distribución independiente desde GitHub: sin PyPI, sin npm, sin registros
externos. Tres capas, cero dependencias obligatorias:

```bash
# Python (kernel, stdlib >= 3.9) — instalable directo del repo con pip:
pip install "git+https://github.com/verared/gerarion.git"
pip install "gerarion[slh] @ git+https://github.com/verared/gerarion.git"
#   la segunda añade SLH-DSA (slh-dsa 0.2.5) para firmas de producción.
#   Alternativa: descarga el .whl o .tar.gz de la última GitHub Release e
#   instala con: pip install <fichero.descargado>
```

```bash
# JavaScript / ESM (kernel, cero dependencias): descarga directa desde
# GitHub Releases (https://github.com/verared/gerarion/releases):
#   - gerarion.mjs (fichero suelto, importarlo tal cual), o
#   - gerarion-kernel-<versión>.tgz (tarball npm estándar, descomprimir y
#     hacer require desde package.json local)
import { toGerarion, fromGerarion } from "./gerarion.mjs";
```

```c
/* C11 (kernel y conformancia): compila directo, sin dependencias */
make -C impl-c            # construye gus-cli y la suite de conformancia
# o, mínimo, solo el núcleo:
cc -std=c11 -O2 -c impl-c/gus.c -o gus.o    # gus.h es la cabecera pública
```

Cada GitHub Release adjunta los artefactos (`.whl`, `.tar.gz`, `.tgz`,
binarios C) más `SHA256SUMS.txt` para verificación de integridad
(`sha256sum -c SHA256SUMS.txt`); los genera el workflow
`.github/workflows/release.yml` en cada tag `v*` (ver
[Publicación](#publicación)). El extra `[slh]` es opcional: es la única
dependencia de todo el proyecto.

## Distribución modular (v3.2.2)

La suite de referencia está organizada en **8 dominios normativos
autocontenidos** (`TCJ`, `GUS`, `CALENDAR`, `GTS`, `GST`, `TSLR`\*,
`GCERTS`\*, `INTEROP`; \* experimentales), cada uno documentado en
`docs/specs/<DOMINIO>.es.md` (y `.en.md`) y exportado como repositorio
satélite `verared/gt-*` independiente (ver [COMPATIBILITY.md](COMPATIBILITY.md)
y `compatibility.json`). Un producto derivado puede adoptar un solo
dominio sin el resto:

- `impl-c/core/` — `libgerarion-core`: núcleo C11 para
  microcontroladores (TCJ+GUS: sin reloj de SO ni tabla TAI);
  `tai/`, `clock/` y `calendars/` son bibliotecas separadas y
  `gus.h`/`gerarion.h` siguen siendo paraguas retrocompatibles.
- `src/gerarion/` — SDK Python en subpaquetes por dominio (`core`,
  `tcj`, `calendars`, `gts`, `gst`, `interop`, `service`,
  `deprecated`) con shims planos de compatibilidad y extras de
  instalación por dominio (`pip install gerarion[gst]`).
- `web/engine/` — motores puros del navegador (`core.mjs`,
  `tcj-tai.mjs`, `guti.mjs`); `web/ui/` (interfaz) y `web/test/`
  (corredores); el scope de la PWA sigue siendo `web/`.
- `vectors/` — vectores de prueba CC0, mapeados por dominio en
  `vectors/README.md`.

`docs/spec/gus-3.0.0.md` permanece como edición consolidada de
referencia.

## Idioma normativo

La versión inglesa de `docs/spec/gus-3.0.0.md`, `docs/spec/threat-model.md`,
`docs/history/errata-v1.2.md` y el informe de adopción vive en
[`docs/en/`](docs/en/), junto con [`README.md`](README.md) (principal, en
inglés), del que este documento es espejo completo en español. **En caso de
divergencia entre la versión inglesa
y la española, prevalece la inglesa (EN > ES).** La documentación histórica
complementaria del Calendario Gerarion vive en [`docs/papers/`](docs/papers/)
como capa informativa, no normativa (ver [Créditos y contexto cultural](#créditos-y-contexto-cultural)).

## Escala de tiempo

Declaración única y autoritativa de lo que hace el código (la spec §9 es
el hogar normativo de este texto; **D-001 CERRADA/ADOPTADA y TODO-004
CERRADO en GUS 3.0.0**).

- **El instante se define sobre TAI (Capa 0).** `instant` son segundos
  continuos y monotónicos sin segundos intercalares internos:
  `instant = day_index·86400 + h·3600 + m·60 + s − offset_seconds`, con
  origen `0000DY-01-01-S-00:00:00-LC-TCJ+0 = 0`.
- **La coordenada global es TCJ = TAI + 8,400 s (Capa 1),** el Tiempo de
  Coordinación de Jerusalén (meridiano 35.2137°E; 31.7683°N, 754 m). Es
  un offset matemático, no un servidor: sin punto único de falla.
- **El puente Unix/UTC aplica la tabla histórica IERS TAI−UTC completa**
  (29 entradas, 1958-01-01 = 10 s … 2017-01-01 = 37 s embebida como
  constante en Python, JS y C): `unix → TAI (+37 s en 2026) → TCJ
  (+8,400 s) → instant`. La inversa es exacta por segmentos y el
  round-trip se verifica en la suite.
- **Cruzar un segundo intercalar histórico ahora conserva la duración
  física.** Medido con la implementación de referencia:
  `2016-12-31T23:59:59Z → 2017-01-01T00:00:00Z` hace subir el entero GUS
  **2 s**, exactamente los 2 segundos SI transcurridos (la etiqueta UTC
  2016-12-31T23:59:60Z existió).
- **La hora HH:MM:SS de una marca es la hora civil del observador** y el
  campo `TCJ±O` (horas o horas:minutos, p. ej. `TCJ-2:20`) entra en el
  cálculo del instante; el ciclo SC/LC se evalúa sobre esa hora
  declarada, nunca sobre `TCJ+0`.
- **La extensión pre-1958** es una convención proléptica declarada
  (offset 0 s); no pretende reproducir ninguna materialización histórica
  de TAI (spec §9.3).
- **Contexto (fuentes verificadas):** NIST documenta TAI − UTC = 37 s
  (nist.gov, leap seconds). La Resolución 5 de la CGPM (2026) decidió que
  el UTC continuo entra en vigor el 20 de mayo de 2027 con un máximo
  |UT1−UTC| de 3.600 s (bipm.org, DOI 10.59161/CGPM2026RES5E). La base
  TAI de GUS alinea el kernel con esa resolución.

## ISO 8601 vs RFC 3339 vs GUS (comparativa breve)

| Criterio | ISO 8601 | RFC 3339 | GUS v3.0.0 |
|---|---|---|---|
| Designador de zona | opcional (casi siempre omitido) | obligatorio (`Z` / `±HH:MM`) | obligatorio con hora (`TCJ±O`), entra en el cálculo del instante |
| Ambigüedad DST | sí, en valores con zona | sí, en valores `±HH:MM` | ninguna: offset fijo respecto de TCJ, una representación por instante |
| Forma compacta | laxa (suele omitir la zona) | prohibida | `2031DY-03-08-T-093000-SC-TCJ0` (29 caracteres, designador intacto) |
| Escala física | gregoriano civil (intercalares + DST) | UTC real (intercalares) | TAI + 8,400 s, `int64` continuo y monotónico, sin intercalares internos |
| Verificación estructural O(1) | ninguna | ninguna | letra de semana (X) + ciclo SC/LC verificables sin red |
| Cadena ↔ entero | vía `datetime` (zonas, DST) | vía `datetime` (zonas, DST) | proyección entera exacta y reversible en dominio (`instant = día·86400 + hms − offset`) |

Comparativa detallada, afirmación por afirmación contra el código real
(incluyendo lo que GUS v3.0 **aún no** resuelve — fracciones de segundo
en el texto, zonas horarias nombradas, integridad criptográfica que vive
en la GST): **ES**
[`docs/comparison/iso-8601-vs-rfc3339-vs-gus.md`](docs/comparison/iso-8601-vs-rfc3339-vs-gus.md)
· **EN**
[`docs/en/comparison/iso-8601-vs-rfc3339-vs-gus.md`](docs/en/comparison/iso-8601-vs-rfc3339-vs-gus.md).

## ISO 8601 vs RFC 3339 vs GUS v3.0.0 — comparativa breve

| Criterio | ISO 8601 | RFC 3339 | GUS v3.0.0 |
|---|---|---|---|
| Designador de zona | opcional, casi siempre omitido | obligatorio (`Z`/`±HH:MM`) | **obligatorio con hora** (`TCJ±O`), entra en el cálculo del instante |
| Ambigüedad DST | sí, en valores con zona | sí, en valores `±HH:MM` | **ninguna** — una vista canónica por instante |
| Forma compacta | laxa (suele omitir la zona) | prohibida | `2031DY-03-08-T-093000-SC-TCJ0` (29 caracteres, designador intacto) |
| Escala física | gregoriano civil (intercalares + DST) | UTC real (intercalares) | **TAI + 8,400 s (TCJ)**, `int64` continuo y monotónico |
| Verificación estructural O(1) | ninguna | ninguna | letra de semana + ciclo SC/LC, sin red e instantánea |
| Cadena ↔ entero | vía `datetime` (zonas, DST) | vía `datetime` (zonas, DST) | **proyección entera exacta**, reversible en dominio |

Comparativa completa, afirmación por afirmación y verificada contra el
repo (con la lista honesta de lo que GUS v3.0 **aún no** resuelve —
fracciones de segundo en el texto, zonas horarias nombradas, integridad
criptográfica que vive en la GST):
[`docs/comparison/iso-8601-vs-rfc3339-vs-gus.md`](docs/comparison/iso-8601-vs-rfc3339-vs-gus.md) (ES) ·
[`docs/en/comparison/iso-8601-vs-rfc3339-vs-gus.md`](docs/en/comparison/iso-8601-vs-rfc3339-vs-gus.md) (EN).

## Publicación

- **GitHub Releases**: <https://github.com/verared/gerarion/releases> —
  artefactos de cada versión: wheel y sdist de Python (`pip install`),
  tarball del kernel JS (`gerarion-kernel-<versión>.tgz`), binarios de la
  implementación C y `SHA256SUMS.txt`. Los genera `release.yml` en cada tag
  `v*`.
- **Calculador web**: GitHub Pages desde `web/` (workflow `pages.yml`:
  suite Python + JS + conformancia JS y C antes de publicar).
- **SBOM**: [`sbom.cdx.json`](sbom.cdx.json) (CycloneDX 1.5).
- **Vectores normativos**:
  [`vectors/gus-normative-003.json`](vectors/gus-normative-003.json) — la
  conformancia de toda implementación (Python, JS, C y terceros) se
  declara contra este archivo. Cláusula completa en
  [`vectors/README.md`](vectors/README.md).
- **Verificador monolítico**: [`tools/verify_gus.py`](tools/verify_gus.py)
  — un único archivo, solo stdlib, sin instalar nada: implementa núcleo,
  formato canónico, firma hash-only de referencia y anclaje del notario.
  Pensado como artefacto descargable para verificar una GST fuera del
  repo (`python3 verify_gus.py marca.gst.json`).
- **Perfiles de interoperabilidad** (ES espejo + EN normativo):
  [GUS-3339](docs/profiles/gus-3339-perfil.md) (mapeo RFC 3339 con
  vectores propios),
  [GUS-3161](docs/profiles/gus-3161-perfil.md) (sello RFC 3161 con
  sidecar), [GUS-Roughtime](docs/profiles/gus-roughtime-perfil.md)
  (receipts Ed25519 de testigos externos ligados al anchor), y
  [GUS-for-notation](docs/profiles/gus-for-notation.md) (la superficie
  mínima consumible: solo notación, sin criptografía).

## Uso rápido

```python
from gerarion import calendar as cal

cal.to_gerarion(cal.day_index_from_gregorian(2026, 5, 23)).canonical()
# '2031DY-03-08-T'
```

```bash
gero convert 2026-05-23          # gregoriano -> gerarion
gero convert 2031DY-03-08-T      # gerarion -> gregoriano
gero keygen --height 8           # par de claves hash-only (post-cuántico)
gero sign "2031DY-03-08-T-09:30:00-SC-TCJ+0"      # crea una GST
gero verify gst.json             # verificación completa
```

## Limitaciones de cada sistema para uso computacional

Este catálogo analiza cada sistema de tiempo vigente desde un único ángulo:
**su uso como valor computacional** (aritmética de fechas, logs, contratos,
sincronización). Los calendarios lunales o lunisolares (hebreo, hijri,
chino) hacen eso *a propósito*: su observación de la luna es una función
religiosa y cultural, no un defecto — la limitación aparece cuando un
sistema de cómputo los usa como base de registro. Las filas de incidentes
enlazan fuente; las filas de limitación estructural justifican el hecho en
el propio texto (estructural = verificable con aritmética, no requiere
prensa). Cada fila declara qué propiedad de GUS la cierra.

### Calendarios civiles

| Sistema | Limitación estructural o incidente documentado | Qué falla en cómputo | Respuesta GUS |
|---|---|---|---|
| **Gregoriano** | Meses de 28–31 días; Feb 29 solo cada 4 (salvo años centenarios); la práctica moderna bien hecha (UTC + RFC 3339, epoch 64-bit) evita *parte* del problema, pero la conversión fecha↔fecha sigue atravesando tablas/librerías | Aritmética con casos borde en *toda* conversión: bugs bancarios y de facturación en fin de mes, comparación de formatos mixtos | 12×30 exactos + Tempalum único: la resta de fechas es un múltiplo de 30 más residuo; cero tablas |
| **Gregoriano (semana)** | Fecha fija cae en día de semana distinto cada año; "todos los lunes" fiscal no existe | Sesiones, recordatorios y contratos requieren recálculo perpetuo | Año de 52 o 53 semanas exactas; 1 Keuphero siempre Soludyia; cada fecha fija tiene día de semana permanente |
| **Gregoriano (ISO 8601)** | La semana 53 (364→371 días) existe, pero cae en años que empiezan jueves (año común) o miércoles (bisiesto): la regla del "primer jueves" la hace irregular y poco memorizable (2009, 2015 y 2020 son 53 semanas y nadie lo sabe de antemano sin calcular) | Sistemas que agrupan por semana fiscal difieren entre sí | La semana 53 existe también en GUS, pero es **estructural**: son los 11 días del Gran Tempalum, determinados por recurrencia entera conocida de antemano, siempre entre el fin y el inicio de año |
| **Gregoriano (Excel/1900)** | Excel hereda de Lotus el bisiesto inexistente del 29 feb 1900 (bug documentado hasta hoy) | Diferencias de 1 día en hojas de cálculo del mundo entero | Origen JDN único y conversión verificada por vectores normativos; sin "fechas históricas decorativas" |
| **Judío (hebreo)** | Lunisolar *a propósito*: meses de 29/30 días, año de 353–355 o 383–385 días, Adar II intercalar, el día arranca al atardecer. Su propósito religioso es legítimo — la limitación computacional es otra: una fecha civil atraviesa dos fechas hebreas y los años varían ±30 días | Duraciones anuales imprevisibles para software; un vencimiento hebreo requiere tablas de conversión actualizadas | Día fijo de 86.400 s con inicio a medianoche; meses regulares; conteo continuo. El propósito religioso del hebreo no se toca |
| **Islámico (hijri)** | Puro lunar *a propósito*: 11 días de deriva anual contra el solar, inicio de mes por observación de luna (no computable de antemano), variantes Umm al-Qura u otras divergen (dos países pueden tener distinto "1 de mes" el mismo día) | Contratos y logs cruzando hijri/solar requieren tablas de conversión vigentes por país | Base solar con anclaje matemático; deriva acotada (\|Δ\| < 7 días) a cambio de una oscilación anual mayor — un intercambio, no una superioridad; implementación determinista |
| **Chino (lunisolar)** | Meses bisiestos por reglas de términos solares y lunas nuevas: la asignación tiene ambigüedades históricas documentadas ("problema 2033": distintas autoridades difieren en qué mes intercalar toca) | Mismos datos astronómicos, dos calendarios chinos distintos; software que no coincide | Regla intercalar única, entera y cacheada (recurrencia del acumulador); lo mismo en cualquier plataforma |
| **Etíope** | 13 meses (12×30 + Pagume de 5/6); 7–8 años por detrás del gregoriano; nuevo año 11/12 sept. El "bug del milenio" etíope fue en septiembre de **2007** gregoriano (año 2000 etíope; [New Scientist](https://www.newscientist.com/article/dn12650-mystery-of-the-ethiopian-millennium-bug-solved/)) | Fronteras de año desfasadas contra sistemas gregorianos | Un solo origen JDN; conversión ida-y-vuelta exacta, sin desfases de era |
| **Persa (solar hijri)** | Meses de 29–31 días; el bisiesto depende del equinoccio observado antes/después del mediodía de Teherán; históricamente requería astronomía y a veces decretos | No existe fórmula simple universal: implementaciones de Nowruz divergen por años concretos | Recurrencia cerrada y exacta (aritmética entera pura): mismo resultado en 2026 y en el año 10.000 |
| **Todos** | El año medio no coincide con el tropical: gregoriano +0.00031 d/a (~1 día cada 3.220 años); juliano +0.0078 d/a (13 días de desfase ya) | Drift no acotado a largo plazo, aunque el gregoriano está bien calibrado | **Intercambio, no superioridad:** GUS acota la deriva (\|Δ\| < 7 días demostrado, [paper](docs/papers/)) a cambio de una oscilación mayor momentánea (±7 días respecto del equinoccio) — el mismo compromiso de los calendarios de semana intercalar |

### Fallos de hora, zona y sincronización (afectan al planeta hoy)

| Vulnerabilidad | Hecho documentado (fuente citable) | Alcance típico | Respuesta GUS |
|---|---|---|---|
| **Segundo intercalar** | 30 jun 2012: kernel Linux en *livelock* (Reddit, Mozilla, LinkedIn, Cloudera caídos; [Wired](https://www.wired.com/2012/07/leap-second-glitch-explained/)). 1 ene 2017: [Cloudflare 502s en el borde](https://blog.cloudflare.com/how-and-why-the-leap-second-affected-cloudflare-dns/) — una duración **negativa** (combinación del segundo intercalar y del smoothing aplicado), unida a la no monotonía de `time.Now()` en Go, hizo entrar en pánico al
proceso DNS ([blog oficial de Cloudflare](https://blog.cloudflare.com/how-and-why-the-leap-second-affected-cloudflare-dns/)). Contexto: la CGPM ([Resolución 2](https://www.bipm.org/en/cgpm-2022/resolution-2), 2022) votó abolir los leap seconds hacia 2035, y mientras tanto Google y AWS *smear* el segundo a su manera (smears diferentes entre sí) — la "mejor práctica" hoy es un parche por operador | Millones de servidores | Conteo continuo: no existe el segundo que la infraestructura no sepa manejar. Ni decretos de operador ni smears distintos por proveedor |
| **tzdata: el "pasado" cambia por decreto** | La base tzdata es una actualización constante: países redefinen sus offsets históricos (Rusia 2011 extends DST turquía 2016/2022, Marruecos cada Ramadan) — paquetes tzdata viejos muestran horas erróneas durante meses | Cientos de millones de móviles con tzdata desactualizado | `TCJ±O` es un campo de presentación, no una transformación: el instante canónico es único y la zona no puede alterar el conteo |
| **DST cambiado por decreto** | México abolió el DST (oct 2022); Egipto lo re-instauró (2023); transiciones anuales cambian por ley | Horas desalineadas durante meses tras cada ley | GUS no cambia relojes civiles por política. Nota honesta: el mapeo lugar→offset seguirá necesitando una base tipo tzdata — lo que GUS resuelve es el **instante canónico**, no el problema civil |
| **Hora local ambigua (fold/gap)** | En transición DST la misma hora civil ocurre dos veces (otoño) o nunca (primavera): facturas, alarmas y logs no-convertibles | Cualquier zona con DST (~40% del mundo) | Único mapeo instante → ciclo SC/LC, nunca ambiguo (la práctica RFC 3339 con offset resuelve esto *si* se almacena el offset de siempre — GUS lo hace estructura) |
| **NTP spoofing / MITM** | ntpd sin autenticación es modificable en tránsito; la autenticación NTS (RFC 8915, 2020) existe pero requiere despliegue; CVE-2013-5211: amplificación `monlist` usada en DDoS de ~400 Gbps (2014; [NVD](https://nvd.nist.gov/vuln/detail/CVE-2013-5211)) | Cualquier host que consulte NTP abierto | El tiempo como valor firmado + notario: la hora no se *consulta*, se *verifica* |
| **Claves débiles por defecto NTP** | CVE-2014-9293/9294: ntpd generaba claves MD5 débiles por defecto sin `requestkey` configurado; los desbordamientos de búfer asociados son [CVE-2014-9295](https://nvd.nist.gov/vuln/detail/CVE-2014-9295) (NVD, dic 2014) | Routers domésticos y appliances | Firmas hash-only, sin secretos por defecto compartidos; el anclaje diario hace el ataque visible |
| **GNSS spoofing** | Jun **2017**, Mar Negro: 22 de junio, el US Maritime Administration registró el caso de Novorossiysk — 20+ barcos reportan saltar su GPS 32 km tierra adentro, a [Gelendzhik Airport](https://www.newscientist.com/article/2143499-ships-fooled-at-sea-in-the-first-gps-cyberattack-in-russia/) (New Scientist). Jamming GNSS afecta redes 5G que sincronizan por satélite | Barcos, aviones, redes móviles | Un salto de GNSS produce raíces divergentes: el notario diario no admite raíz retroactiva y las réplicas lo delatan |
| **Replay en protocolos con reloj** | Kerberos admite skew de 5 min por diseño: dentro de esa ventana hay reutilización (replay) de tiquets; web que aceptan cookies expiradas por el reloj del cliente | Infraestructura corporativa global | El instante es un entero total y firmado; la ventana de skew deja de ser perimeter criptográfico y queda como tolerancia operativa |
| **Timestamp en contratos inteligentes** | Dependencia de [`block.timestamp`](http://swcregistry.io/docs/SWC-116/) (SWC-116, clase de vulnerabilidad reconocida en Solidity): mineros pueden moverlo hacia adelante | DeFi/on-chain | El tiempo on-chain se ancla a un `day_root` GUS previamente publicado: alterar el ancla exige romper SHA-256, no "esperar a que minen" |
| **Y2038 (32-bit)** | La práctica moderna ya usa epoch de 64 bits (Linux/glibc, iOS/Android); quedan miles de millones de dispositivos 32-bit (IoT, RTOS, routers legacy) donde `time_t` se desborda el 19 enero 2038 | Devices legacy | GUS opera en enteros arbitrarios de Python/BigInt: sin techo de representación |
| **Y10K y límites silenciosos** | Librerías que asumen 4 dígitos de año o meses 1–12 como invariant | Parches perpetuos | Formato de longitud variable, era explícita, días de Tempalum con nombre |
| **Confianza en "la hora del servidor"** | Un servidor comprometido muestra cualquier hora: logs inservibles en forense | Toda empresa con un solo reloj de autoridad | Una marca sin GST es una *afirmación*; con anclaje notarial es un *hecho* verificable frente a terceros (cota: la marca existía **no más tarde** del ancla — ver ["Qué NO garantiza"](#qué-no-garantiza-gus)) |
| **Roughtime (precedente)** | Google (2016) demostró que el tiempo distribuido puede verificarse con pruebas de cadena/hash — exactamente el mecanismo que GUS especializa a un calendario regular | — | GUS añade: calendario sin casos borde, semana invariante y firma post-cuántica; el notario usa el mismo tipo de prueba Merkle |

### El patrón detrás de cada fila

Cada incidente cumple una de estas cuatro causas; GUS las cierra como
diseño, no como parche:

1. **Irregularidad estructural** (meses 28–31, lunas, bisiestos
   observables) → regularidad total (12×30 + Tempalum, recurrencia entera
   exacta).
2. **Gobernabilidad arbitraria** (decretos de DST, reformas, variantes
   regionales) → regla única determinista; el offset civil es opcional y
   visible.
3. **Confianza en infraestructura mudable** (NTP, GNSS, relojes de
   servidor) → firma criptográfica + notario encadenado con réplicas.
4. **Límites de representación** (32 bits, años de 4 dígitos, zonas
   históricas) → enteros arbitrarios + era explícita + escapes
   documentados.

## Qué NO garantiza GUS

Declarado con la misma fuerza que las garantías:

## Qué está listo y qué no

| Capa / Satélite | Estado | Resumen |
|---|---|---|
| `gt-core`, `gt-gus`, `gt-tcj` | **estable** | Aritmética congelada `GUS v3.0.0`, `TCJ = TAI + 8.400 s`, verificada bit a bit entre Python, JS y C11 (`libgerarion-core` sin malloc). |
| `gt-calendar` | **estable** | Motor determinista `AY`/`DY` + 10 calendarios GUTI-1, verificado contra `vectors/guti-calendars-001.json` y portal web 100 % offline. |
| `gt-gts` | **estable (núcleo) / experimental (Roughtime)** | Máquina de estados de confianza de reloj (`VERIFIED`/`HOLDOVER`/`UNVERIFIED`/`REJECTED`) con anclas anti-rollback sub-segundo; el perfil Roughtime es experimental. |
| `gt-gst` (`GST v2`) | **estable (pendiente de auditoría externa)** | Firma híbrida normativa **Ed25519 + ML-DSA** sobre **RFC 8785 (JCS)**, dominio `GUS3-GST-V2`, protección anti-downgrade, `ReplayGuard` *fail-closed* y notario Merkle diario opcional. Requiere auditoría independiente de terceros y custodia TPM/HSM antes de producción. |
| `gt-interop` | **estable (RFC 3339) / experimental (RFC 3161)** | Parser estricto GUS-3339 con vectores negativos compartidos; el puente RFC 3161 TSA es experimental. |
| `gt-tslr`, `gt-gcerts` | **EXPERIMENTAL** | Solo especificaciones y andamiaje vacío; sin implementación de referencia aún. |
| `WOTS+` (`src/gerarion/deprecated/hashots.py`) | **deprecado / educativo** | Aislado con `DeprecationWarning`; fuera del perfil normativo `GST v2`; nunca usar en producción. |

1. **No garantiza que la hora firmada sea *verdadera*.** Una GST prueba
   que una marca existía y se comprometió **no más tarde** del ancla
   notarial que la referencia (cota superior). Quien posee la clave puede
   firmar cualquier hora; el notario la delata solo si se publica *después*
   del ancla que la hora declarada exige. Roughtime y RFC 3161 tienen la
   misma limitación — es el límite matemático de toda marca temporal sin
   un oráculo externo que certifique la verdad de cada hora.
2. **No garantiza la integridad de las claves.** Si la clave de firma se
   ve comprometida sin revocación visible en el log, las marcas firmadas
   en la ventana de compromiso son dudosas.
3. **No garantiza distribución honesta de réplicas.** La "objetividad"
   del notario descansa en un supuesto **operativo** (no matemático): que
   las k réplicas no coluyen. Dos trust roots divergentes (split brain)
   se detectan entre sí, pero el consumidor decide a cuál confía. El
   runbook declara el procedimiento de emergencia.
4. **No reemplaza la infraestructura civil.** El mapeo lugar→offset civil
   sigue necesitando tzdata. Los relojes físicos siguen necesitando una
   fuente (GNSS/NTP). GUS hace que el *valor* sea verificable; no sustituye
   la sincronización física.
5. **Las escalas de referencia no son "100 % matemáticas".** Lo
   puramente matemático es el calendario: una función total del índice
   de día. Las escalas de referencia reales que mantiene el BIPM
   dependen de relojes atómicos físicos, y la divergencia con el día
   solar (UT1) sigue creciendo. La garantía de GUS sobre el tiempo es
   *consistencia verificable*, no verdad astronómica — ver
   [Escala de tiempo](#escala-de-tiempo) para lo que cuenta exactamente
   el entero.
6. **No exige adopción universal para ser útil.** El notario funciona con
   cualquier calendario (un `day_root` es solo una cadena firmada);
   GUS lo ofrece *integrado* con un calendario regular y vectores, pero
   puede usarse como notario sobre fechas gregorianas si eso facilita la
   migración.

## Por qué las marcas son caras de alterar

| Capa | Mecanismo | Propiedades y límites de seguridad (declarados honestamente) |
|---|---|---|
| Marca (`GST v2`, normativo) | Firma híbrida **Ed25519 + ML-DSA** sobre **RFC 8785 (JCS)** (`GUS3-GST-V2`) | Firma dual con descriptores de algoritmo y claves dentro de los bytes firmados (**anti-downgrade**); `seq` monotónico + `nonce` con `ReplayGuard` *fail-closed*. Requiere auditoría independiente de terceros y custodia TPM/HSM para producción. |
| Marca (adaptador opcional) | SLH-DSA (FIPS 205, sin estado) | Adaptador opcional (`gerarion.gst.adapters.SlhDsaSigner`); el paquete externo `slh-dsa` no está validado FIPS aquí. |
| `WOTS+` legado (deprecado) | `WotsMerkleSigner` (`src/gerarion/deprecated/hashots.py`) | **Deprecado / solo educativo** (hojas de un solo uso con estado; emite `DeprecationWarning`); fuera de `GST v2`. |
| Notario (opcional) | Raíz diaria encadenada `root(n) = H(n, tree(n), root(n-1))` | Recomputar toda la cadena posterior **conservando consistencia entre réplicas publicadas** (quórum de firmantes distintos). |
| Objetividad | Réplicas independientes publicadas (supuesto operativo declarado — ver §3 de "Qué NO garantiza") | Reescribir todas **sin dejar divergencia detectable** |

Nada de esto depende de confianza política *para su verificación*: la
matemática es ejecutable por cualquiera. La *independencia* de réplicas y la
gobernanza de claves sí son cuestiones de confianza humana (gobernanza
formal en [GOVERNANCE.md](GOVERNANCE.md)). Detalle completo en el
[modelo de amenazas](docs/spec/threat-model.md).

## Limitaciones y costes honestos

1. **Trimestres fiscales.** Un trimestre fiscal de 13 semanas (91 días) no
   coincide con 3 meses de 30 (90 días). La semana invariante ayuda a los
   calendarios semanales, no a los trimestres.
2. **Bloque Tempalum.** Un año común deja 4 días fuera de los meses y un
   año GT 11. Cualquier sistema que asuma 12 meses uniformes de longitud
   fiscal debe tratar el Tempalum como bloque aparte (está escrito en el
   formato: `MM=00`).
3. **Los meses no encajan en semanas.** 30 no es múltiplo de 7: una fecha
   fija conserva su día de semana entre años, pero el día 1 de cada mes
   cae en un día de semana distinto según el mes. Symmetry454 y el
   International Fixed Calendar alinean mes y semana; GUS no (elige
   meses uniformes en vez de meses semanales).
3. **Coste de migración.** Todo sistema debe hablarse con lo ya existente:
   GUS viaja con conversión exacta bidireccional (`to_gerarion` /
   `from_gerarion`, roundtrip gregoriano emitido en el vector set) y el
   offset civil opcional mantiene la lectura habitual. La migración real
   (bancos, JEE, contratos) es un proyecto institucional: el informe de
   adopción ([ES](docs/history/informe-adopcion-gus.md) /
   [EN](docs/history/adoption-report.en.md)) propone un camino por fases sin
   big-bang.
4. **El notario necesita operación.** Claves, réplicas, rotación, ceremonia:
   es infraestructura con coste ops (runbook completo en
   [`docs/notary-runbook.md`](docs/notary-runbook.md)).

## Trabajos relacionados

**Nada de aquí es nuevo pieza por pieza — cada componente tiene precedente,
y conviene decirlo.**

- **12×30 + días de cierre:** el calendario civil egipcio antiguo
  (12×30+5 — WebExhibits, *Ancient calendars*:
  webexhibits.org/calendars/calendar-ancient.html: «a solar year of
  365 days (12 months × 30 + 5 extra)»), el republicano francés
  (12×30 + 5/6 días complementarios), el copto, el etíope y el bahá'í
  (19×19 + intercalares). Es el antecedente estructural más cercano al
  bloque GUS.
- **Semana invariante con semana intercalar:** Symmetry454 (meses de
  28/35 días, trimestres de 13 semanas, años comunes de 364 días y una
  semana intercalar que alarga los años largos a 371 — javadoc de
  Threeten-Extra, threeten.org), Hanke-Henry y Pax. El Tempalum de GUS
  es, conceptualmente, una *semana intercalar* (leap week) y debe
  leerse como tal.
- **Coste conocido, compartido con esos diseños:** tres meses regulares
  suman **90 días, no 13 semanas**, y no todos los meses empiezan en el
  mismo día del ciclo.
- **Calendarios puramente aritméticos:** el hebreo (computable por
  aritmética desde el siglo IV), el hijri tabular, el persa de 33 años.
- **Conteo continuo de días:** Julian Day Number, la cuenta larga maya,
  Unix time.
- **Marca temporal encadenada:** Haber y Stornetta (1991) — de ahí Surety,
  publicando hashes semanales en el New York Times desde 1995 — más RFC
  3161, OpenTimestamps, Certificate Transparency y Roughtime.
- **"Antiguo para la era computacional":** la Era Holocena, el reloj de
  la Long Now (años de 5 dígitos) y el calendario positivista de Comte.

**La lección histórica clave.** La reforma del calendario (el IFC de
Cotsworth/Eastman y el World Calendar) fue objeto de estudio de la Liga de
Naciones — el 18 de enero de **1937** la Liga tomó acción formal sobre el
tema ([Ministry Magazine, julio 1937](https://www.ministrymagazine.org/archive/1937/07/status-of-reform-calendar-issue)) —
y no prosperó; la objeción principal fue **religiosa**: los días en blanco
rompían la continuidad del ciclo de 7 días (la delegación judía lo expuso
ante el comité preparatorio de la Liga — [JTA](https://www.jta.org/archive/calendar-reform-threat-to-sabbath-jewish-delegation-puts-case-against-blank-day-to-league-of-nati)).
GUS no peca de
eso porque **364 y 371 son múltiplos de 7**: el Tempalum añade semanas
*enteras*, nunca días huérfanos. Este es el argumento de diseño más
fuerte del calendario y por eso se explicita.

**Y la novedad real de GUS es el paquete:** un calendario regular con
vectores normativos, tres implementaciones independientes conformantes y
una capa criptográfica opcional, todo bajo una cláusula de conformancia
ejecutable. Ninguno de los precedentes ofrece ese contrato: su
reforma fracasó por adopción política; GUS sustituye la adopción política
por reproducibilidad (ver [GOVERNANCE.md](GOVERNANCE.md)).

**Timestamping criptográfico:** GUS no compite con OTS/CT/Rekor/3161/
Roughtime — los incorpora como puentes réplicas/auditores
(`tools/ots_bridge.py` ancla el day_root diario a OTS; RFC 3161 se mapea
en el runbook) y usa el mismo mecanismo Merkle.

## FAQ

**¿Por qué no UTC + RFC 3339?**
UTC + offset resuelve *representación* de instantes — y es el formato de
intercambio correcto. No resuelve aritmética de calendario (meses
irregulares), ni la estabilidad de la escala ( leap seconds que
la CGPM aún no ha abolido de facto, smears por operador), ni la
verificabilidad (un `2026-05-23T09:30:00Z` es solo un número; nada lo
certifica). GUS usa una escala lineal continua sobre etiquetas de
medianoche UTC (ver [Escala de tiempo](#escala-de-tiempo)) y añade la capa de
verificación; el offset TCJ±O mantiene compatibilidad de presentación
con la lectura civil.

**¿Por qué no simplemente usar el notario con calendario gregoriano?**
Puedes — es exactamente el punto 5 de ["Qué NO garantiza
GUS"](#qué-no-garantiza-gus). El notario no sabe qué calendario lleva
arriba (es una cadena de raíces firmadas). GUS los ofrece integrados porque el
calendario es lo que la gente **diseña contratos con**: si la capa
contractual tiene meses de 28–31 y la capa de anclaje otra cosa, el error
de presentación es lo único que nunca falta en el log forense. Por eso
la especificación es única para el par calendario+instante+anclaje y
tiene un vector set para los tres.

**¿Por qué "2031DY"? ¿Qué es DY?**
El origen del conteo es 1 Keuphero del año 0, **definido por su JDN:
día 0 = JDN 1719313**, Soludyia por definición. La equivalencia con 21 de
marzo de -5 (6 a.C.) en gregoriano proléptico es un ejemplo de conversión
con errata E-07 como frontera: el calendario GUS es independiente del
gregoriano, y la conversión gregoriana proléptica se usa como servicio de
interoperabilidad en todo el dominio. El año 2031DY del ejemplo — anclado al
17 de marzo de 2026 gregoriano — es una entrada del vector set: el año se determina
por la recurrencia solar; la garantía normativa es la cota de oscilación
(|Δ| < 7 días), que sale de que 1 Keuphero debe seguir cayendo en Soludyia:
cualquier corrección se aplica en pasos de 7 días (la constante de año medio
de la especificación lo garantiza), por eso la cota vale como propiedad del modelo
pero NO cubre la deriva física real del año tropical a escala de milenios;
y la ventana de fechas es **observada, no estructural** (el
inicio de año cae entre el 10 y el 21 de marzo en 11.000 años simulados, y
esa ventana se desplaza lentamente con los milenios). La era DY cubre
`day_index ≥ 0`; AY, antes del origen.

**¿Y si mi caso de uso no necesita firma?**
Ignórala. El kernel de calendario + formato canónico funciona solo
(`gerarion.calendar`, `web/gerarion.mjs`, `impl-c/`), cero dependencias
criptográficas. La capa GST/notario es opt-in.

## Documentos

```
docs/
├── spec/gus-3.0.0.md          Especificación normativa (v3.0.0; EN normativo en docs/en/)
├── spec/threat-model.md     Modelo de amenazas y garantías
├── GLOSSARY.md              Glosario de definición única, ES y EN
├── informe-adopcion-gus.md  Informe técnico: por qué adoptar GUS en cómputo
├── errata-v1.2.md           Los 6 defectos del borrador histórico v1.2, verificables en tests
├── en/                      5 documentos normativos en inglés (precedencia EN>ES)
├── ietf/                    Draft xml2rfc (GUS 2.1) para IETF
├── notary-runbook.md        Operación, ceremonia y rotación del clúster notarial
└── papers/                  Drift acotado (demostración), draft IETF v1, lib C
```

*(La documentación histórica complementaria está en `docs/papers/`, no normativa.)*

**Estado IETF:** el draft
([`docs/ietf/draft-gerarion-gus-00.xml`](docs/ietf/draft-gerarion-gus-00.xml))
es una *individual submission* (sin grupo de trabajo asignado); está
preparado en xml2rfc v3 con registros IANA propuestos, a la espera de
presentación formal. El draft markdown histórico v1 está OBSOLETO
(archivado fuera de este repositorio, no publicado).

La gobernanza formal del proyecto (quién aprueba cambios de kernel,
Looking Period de 90 días, certificación de forks, política de claves,
conflictos de interés) está en [GOVERNANCE.md](GOVERNANCE.md).

## Créditos y contexto cultural

El Calendario Gerarion, la lengua Nuvid y la investigación original fueron
creados por **Gerardo Loyola** ([github.com/geroiloyola](https://github.com/geroiloyola)),
cuyo trabajo es la base de todo este proyecto. La especificación GUS la mantiene el
proyecto **verared** (futura fundación) ([github.com/verared](https://github.com/verared)),
responsable de la especificación a largo plazo (github.com/verared/gerarion).

Ese origen histórico, cultural y religioso **no es normativa de GUS**: el
este perfil usa solo el formato canónico de la spec y los vectores. La
documentación complementaria se conserva, como investigación no normativa, en
[`docs/papers/`](docs/papers/); las discrepancias conocidas entre ese material
y este kernel están registradas en [`docs/history/errata-v1.2.md`](docs/history/errata-v1.2.md).

## Estado

- [x] Núcleo de calendario exacto (enteros, sin floats) — 91 tests Python
      (incl. 6 fuzzing + 2 conformancia) + 22 vectores JS en verde
- [x] Conformancia contra `vectors/gus-normative-003.json`: Python, JS y
      C, 7/7 categorías núcleo cada uno; fuzzing diferencial entre las
      tres implementaciones (1500×3 casos idénticos)
- [x] Formato canónico + normalización (reglas 1–7, errores GERO_*)
- [x] `GST v2` normativo (firma híbrida Ed25519 + ML-DSA sobre RFC 8785 JCS,
      protección anti-downgrade, `ReplayGuard` *fail-closed*, notario Merkle
      diario opcional); `WOTS+` legado aislado en `deprecated/hashots.py`
- [x] CLI (`gero`)
- [x] Notario Merkle multi-réplica (quórum k-de-n, trust root, puentes
      OTS/RFC 3161, deploy compose/systemd)
- [x] Calculador web (estático, sin backend, self-test de vectores en
      vivo, E2E Playwright)
- [x] Inglés normativo (`docs/en/`, `docs/specs/*.en.md`, precedencia EN>ES)
- [x] Perfiles de interop (GUS-3339, GUS-3161, GUS-Roughtime) con pruebas
      e2e locales y verificador monolítico stdlib puro (`tools/verify_gus.py`)
- [x] Documento de adopción mínima GUS-for-notation (solo notación)
- [x] Exportación modular y 9 repositorios satélite `verared/gt-*` con
      `EXPORT-MANIFEST.json` verificable y `COMPATIBILITY.md`
- [ ] Auditoría criptográfica externa independiente de `gt-gst` y notario
- [ ] Verificador de testigos contra la red Roughtime real (TODO-002)

Consulta el [Estado de madurez en tres ejes](#estado-de-madurez-en-tres-ejes-v322)
y [COMPATIBILITY.md](COMPATIBILITY.md) para la matriz exacta de versiones
y madurez.

## Licencia

Código: `MIT OR Apache-2.0`. Documentos: `CC-BY-4.0`. Vectores: `CC0-1.0`.
La dependencia opcional [`slh-dsa`](https://pypi.org/project/slh-dsa/)
(LGPL-3.0-or-later) **no** se incluye ni se vendoriza: se instala aparte y
este repositorio no redistribuye ninguno de sus fragmentos. Ver
[NOTICE](NOTICE), [REUSE.toml](REUSE.toml) y [sbom.cdx.json](sbom.cdx.json).

## Versiones

| Artefacto | Versión | Qué numera |
|---|---|---|
| Especificación normativa (`docs/spec/gus-3.0.0.md`) | **3.0.0** | La especificación en sí; aritmética y vectores congelados (`vectors/gus-normative-003.json`) |
| Draft IETF (`docs/ietf/draft-gerarion-gus-00.xml`) | **2.1** | El documento de envío (individual submission) que describe la spec |
| Suite de referencia y satélites (`pyproject.toml`, `web/package.json`, `impl-c/gerarion.h`, `verared/gt-*`) | **3.2.2** | Artefactos de software sincronizados y exportaciones satélite (ver [COMPATIBILITY.md](COMPATIBILITY.md)) |
