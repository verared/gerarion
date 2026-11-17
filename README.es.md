# Gerarion Universal Standard (GUS)

🌐 English: **[README.md](README.md)** — este documento es el espejo en
español; en caso de divergencia prevalece la versión inglesa (EN > ES).

[![CI](https://github.com/verared/gerarion/actions/workflows/ci.yml/badge.svg)](https://github.com/verared/gerarion/actions/workflows/ci.yml)

> **ESTADO: BETA (alpha-final).** GUS v2.0 está congelado: las cuestiones
> normativas abiertas de la fase alfa quedaron resueltas (ver
> [registro TODO](docs/TODO-pendientes.md)); pueden cambiar antes de la
> v1.0 los adaptadores criptográficos opcionales y el packaging.

**Tiempo regular, universal y verificable.**

Un estándar de tiempo que integra tres capas bajo una misma especificación
máquina-verificable:

1. **Calendario regular:** 12 meses de 30 días exactos + Tempalum de cierre
   (4/11 días). Toda fecha fija cae siempre en el mismo día de la semana.
2. **Escala continua:** instantes lineales sobre TAI, sin segundos
   intercalares. Comparaciones, rangos y totales triviales en cualquier
   lenguaje.
3. **Marca temporal verificable (GST):** firma post-cuántica + notario
   Merkle diario encadenado. El nivel de seguridad efectivo es ~2^128
   frente a un atacante cuántico (Grover); el coste crudo de preimagen de
   SHA-256 es 2^256, y el nivel de WOTS+Merkle depende además de los
   parámetros (altura del árbol, Winternitz — ver
   [números](#por-qué-las-marcas-son-caras-de-alterar)). Reescribir el
   pasado **anclado** exige recomputar toda la cadena del notario sin
   dejar divergencia detectable entre réplicas.

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
de día y las eras DY/AY son *etiquetas opacas* del estándar: ninguna regla
normativa depende de su significado. Su etimología, filosofía y notas de
origen tienen un origen cultural documentado fuera de este repositorio
(no publicado).

> ⓘ **Resumen.** GUS es un estándar de tiempo: un calendario regular 12×30
> con un «Tempalum» de cierre (años de 53 semanas incluidos, a propósito),
> una escala continua de tiempo sin segundos intercalares sobre TAI, y
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

## Idioma normativo

La versión inglesa de `docs/spec/gus-2.0.md`, `docs/spec/threat-model.md`,
`docs/errata-v1.2.md` y el informe de adopción vive en
[`docs/en/`](docs/en/), junto con [`README.md`](README.md) (principal, en
inglés), del que este documento es espejo completo en español. **En caso de
divergencia entre la versión inglesa
y la española, prevalece la inglesa (EN > ES).** La documentación histórica
complementaria del Calendario Gerarion vive en [`docs/papers/`](docs/papers/)
como capa informativa, no normativa (ver [Créditos y contexto cultural](#créditos-y-contexto-cultural)).

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
  [`vectors/gus-normative-001.json`](vectors/gus-normative-001.json) — la
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
5. **La escala TAI no es "100 % matemática".** Lo puramente matemático es
   el calendario: una función total del índice de día. TAI depende de
   relojes atómicos físicos que mantiene el BIPM, y la divergencia con el
   día solar (UT1) sigue creciendo — es exactamente el precio de eliminar
   los segundos intercalares. La garantía de GUS sobre el tiempo es
   *consistencia verificable*, no verdad astronómica.
6. **No exige adopción universal para ser útil.** El notario funciona con
   cualquier calendario (un `day_root` es solo una cadena firmada);
   GUS lo ofrece *integrado* con un calendario regular y vectores, pero
   puede usarse como notario sobre fechas gregorianas si eso facilita la
   migración.

## Por qué las marcas son caras de alterar

| Capa | Mecanismo | Coste de romper (declarado honestamente) |
|---|---|---|
| Marca (GST) | Firma hash-only de referencia (SHA-256 + WOTS + Merkle) | Preimagen SHA-256: 2^256. **Nivel efectivo: ~2^128** (dominado por Grover en el caso cuántico, y dependiente de los parámetros: altura del árbol y cota Winternitz — ver nota stateful) |
| Marca (SLH-DSA) | FIPS 205, SHA2-128f: firma **sin estado** | Nivel QP Categoría I de FIPS 205 (~2^128 colisión/preimagen con Grover); firma de 17.088 bytes, clave pública de 32 bytes. Nota: `SLH-DSA-SHA2-128s` produciría firmas de ~7,9 KB (7.856 B medidos con la librería de referencia), más lenta al firmar; **no es el set usado por la referencia** |
| Notario | Raíz diaria encadenada `root(n) = H(n, tree(n), root(n-1))` | Recomputar toda la cadena posterior **conservando consistencia entre réplicas publicadas** |
| Objetividad | Réplicas independientes publicadas (supuesto operativo declarado — ver §3 de "Qué NO garantiza") | Reescribir todas **sin dejar divergencia detectable** |

**Nota sobre firmas con estado.** El esquema hash-only de referencia usa
WOTS+Winternitz+Merkle: cada hoja firma exactamente un mensaje; reutilizar
un índice rompe la seguridad (misma familia de riesgo que XMSS/LMS — ver
NIST SP 800-208). La disciplina de estado es responsabilidad del portador y
el anclaje diario registra el índice usado (hoja repetida = alarma pública).
El esquema recomendado para producción es **SLH-DSA (FIPS 205)**, sin
estado: `gerarion.adapters.SlhDsaSigner`.

**Números concretos:** referencia hash-only altura 8 → firma JSON de
9.354 bytes (serialización binaria cruda: 67×32 + 8×32 = 2.400 bytes: 67
elementos Winternitz + 8 nodos de path, todos de 32 bytes),
clave pública 32 bytes (hex 64), árbol de 256 hojas (256 marcas/día por
clave); SLH-DSA-128f → firma 17.088 bytes (128s: 7.856, no es el set de
referencia), pk 32 bytes. La raíz diaria del
notario es de 32 bytes — verificar offline es re-calcular el árbol con las
hojas del bundle (cero red, cero latencia de terceros).

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
   adopción ([ES](docs/informe-adopcion-gus.md) /
   [EN](docs/en/adoption-report.md)) propone un camino por fases sin
   big-bang.
4. **El notario necesita operación.** Claves, réplicas, rotación, ceremonia:
   es infraestructura con coste ops (runbook completo en
   [`docs/notary-runbook.md`](docs/notary-runbook.md)).

## Trabajos relacionados

**Nada de aquí es nuevo pieza por pieza — cada componente tiene precedente,
y conviene decirlo.**

- **12×30 + días de cierre:** el calendario civil egipcio antiguo
  (12×30+5), el republicano francés (12×30 + 5/6 días complementarios),
  el copto, el etíope y el bahá'í (19×19 + intercalares). Es el
  antecedente estructural más cercano al bloque GUS.
- **Semana invariante con semana intercalar:** Symmetry454, Hanke-Henry
  y Pax. El Tempalum de GUS es, conceptualmente, una *semana intercalar*
  (leap week) y debe leerse como tal.
- **Calendarios puramente aritméticos:** el hebreo (computable por
  aritmética desde el siglo IV), el hijri tabular, el persa de 33 años.
- **Conteo continuo de días:** Julian Day Number, la cuenta larga maya,
  Unix time, TAI.
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
certifica). GUS usa una escala TAI continua y añade la capa de
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
del estándar lo garantiza), por eso la cota vale como propiedad del modelo
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
├── spec/gus-2.0.md          Especificación normativa (v2.0; EN normativo en docs/en/)
├── spec/threat-model.md     Modelo de amenazas y garantías
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

La gobernanza formal del estándar (quién aprueba cambios de kernel,
Looking Period de 90 días, certificación de forks, política de claves,
conflictos de interés) está en [GOVERNANCE.md](GOVERNANCE.md).

## Créditos y contexto cultural

El Calendario Gerarion, la lengua Nuvid y la investigación original fueron
creados por **Gerardo Loyola** ([github.com/geroiloyola](https://github.com/geroiloyola)),
cuyo trabajo es la base de todo este proyecto. El estándar GUS lo mantiene el
proyecto **verared** (futura fundación) ([github.com/verared](https://github.com/verared)),
responsable del estándar a largo plazo (github.com/verared/gerarion).

Ese origen histórico, cultural y religioso **no es normativa de GUS**: el
estándar solo usa el formato canónico de la spec y los vectores. La
documentación complementaria se conserva, como investigación no normativa, en
[`docs/papers/`](docs/papers/); las discrepancias conocidas entre ese material
y este kernel están registradas en [`docs/errata-v1.2.md`](docs/errata-v1.2.md).

## Estado

- [x] Núcleo de calendario exacto (enteros, sin floats) — 91 tests Python
      (incl. 6 fuzzing + 2 conformancia) + 22 vectores JS en verde
- [x] Conformancia contra `vectors/gus-normative-001.json`: Python, JS y
      C, 7/7 categorías núcleo cada uno; fuzzing diferencial entre las
      tres implementaciones (1500×3 casos idénticos)
- [x] Formato canónico + normalización (reglas 1–7, errores GERO_*)
- [x] GST hash-only de referencia (WOTS+Merkle, disciplinado por estado)
      + SLH-DSA (FIPS 205) vía adaptador + notario Merkle encadenado
- [x] CLI (`gero`)
- [x] Notario de producción (multi-réplica, k-de-n, trust root firmada
      SLH-DSA, puentes OTS/RFC 3161, deploy compose/systemd)
- [x] Calculador web (estático, sin backend, self-test de vectores en
      vivo, E2E Playwright 12/12)
- [x] Inglés normativo (`docs/en/`, 5 documentos, precedencia EN>ES)
- [x] Perfiles de interop (GUS-3339, GUS-3161, GUS-Roughtime) con pruebas
      e2e locales y verificador monolítico stdlib puro
      (`tools/verify_gus.py`); decisión D-001 (frontera UTC/TAI) en
      borrador público, en revisión de 90 días
- [x] Documento de adopción mínima GUS-for-notation (solo notación)
- [x] Primer push a GitHub + publicación vía GitHub Releases (distribución independiente, sin registries externos)
- [ ] Primer ancla OpenTimestamps operacional
- [ ] Verificador de testigos contra la red Roughtime real (TODO-002)

**Versión actual: alfa** — el estándar es reproducible desde el repo
(vectores, tres implementaciones, conformancia), pero no hay todavía
despliegue externo ni tercero independiente que lo implemente.

## Licencia

Código: MIT. Documentos: CC-BY-4.0. Dependencia opcional
[`slh-dsa`](https://pypi.org/project/slh-dsa/) (LGPL-3.0-or-later) **no** se
incluye ni se vendoriza: se instala aparte y este repositorio no redistribuye
ninguno de sus fragmentos. Ver [NOTICE](NOTICE) y [sbom.cdx.json](sbom.cdx.json).

## Versiones

| Artefacto | Versión | Qué numera |
|---|---|---|
| Especificación normativa (`docs/spec/gus-2.0.md`) | **2.0** | El estándar en sí; solo cambia con cambios normativos aprobados (ventana de revisión de 90 días) |
| Draft IETF (`docs/ietf/draft-gerarion-gus-00.xml`) | **2.1** | El documento de envío (individual submission) que describe la spec; puede avanzar sin que la spec cambie |
| Paquetes (`pyproject.toml`, `web/package.json`) | **2.3.5** | Los artefactos de software: kernel Python/JS/C, tests, docs y erratas aplicadas. Puede cambiar entre releases de la spec |
