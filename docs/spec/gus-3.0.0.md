# Gerarion Universal Standard (GUS) — Especificación v3.0.0

> **v3.0.0 (alfa):** cambio MAYOR de la base temporal (CIERRA D-001 y
> TODO-004). La escala de instantes se define sobre **TAI** con la tabla
> histórica IERS TAI−UTC embebida (§9) y la coordenada global pasa a ser
> **TCJ = TAI + 8,400 s** (Tiempo de Coordinación de Jerusalén,
> 31.7683°N, 35.2137°E, 754 m) en lugar de medianoche UTC. El campo
> `TCJ±O` entra en el cálculo del instante y admite offsets con minutos
> (`TCJ-2:20`); se añade el formato COMPACTO de 29 caracteres (§6). Los
> instantes de todos los vectores cambian (nuevo set `gus-normative-003`
> + `gus-3339-002`; los anteriores quedan archivados en `vectors/archive/`).
> (v2.1.0: base anterior, conservada como referencia en `docs/spec/`.)

> Esta especificación sustituye al borrador histórico v1.2 (documentado como
> material complementario no normativo en `docs/papers/`).

> **Edición consolidada.** Desde la reorganización modular, cada dominio
> normativo tiene una especificación autocontenida en [`docs/specs/`](../specs/):
> [TCJ](../specs/TCJ.es.md) · [GUS](../specs/GUS.es.md) ·
> [CALENDAR](../specs/CALENDAR.es.md) · [GTS](../specs/GTS.es.md) ·
> [GST](../specs/GST.es.md) · [TSLR](../specs/TSLR.es.md) (experimental) ·
> [GCERTS](../specs/GCERTS.es.md) (experimental) · [INTEROP](../specs/INTEROP.es.md).
> Este documento permanece como la edición consolidada de referencia; en
> caso de divergencia, manda la especificación del dominio.
> Toda propiedad de v1 que se conserva se reproduce aquí de forma ejecutable
> y verificada por la suite de tests. Toda divergencia está documentada en
> `docs/history/errata-v1.2.md`.

## 1. Qué es

GUS define:

1. **Un calendario regular** — 12 meses de 30 días exactos más un período de
   cierre (Tempalum) de 4 u 11 días. Toda la aritmética de fechas es sin
   casos borde.
2. **Una semana invariante** — todo año dura 52 o 53 semanas exactas, de modo
   que una fecha fija cae siempre en el mismo día de la semana.
3. **Un instante continuo** — segundos atómicos (TAI, Capa 0) desde el
   origen, sin segundos intercalares internos; la coordenada global es
   TCJ = TAI + 8,400 s (Capa 1; ver §9 para la frontera exacta con
   UTC/TAI). El conteo es lineal, total y monotónico.
4. **Una marca temporal firmada (GST)** — el valor de tiempo firmado con
   esquemas post-cuánticos (hash-only en la referencia: SHA-256 + Winternitz
   + Merkle).
5. **Un notario diario Merkle encadenado** — la objetividad: cada día se
   sella y se encadena con el anterior; las raíces se publican en réplicas
   independientes.

## 2. Propósito de seguridad

**Un tiempo cuyo costo de falsificación supera cualquier beneficio.**

Falsificar una GST vigente exige, por construcción:

- quemar la resistencia de preimágenes de SHA-256 (≥ 2^128 contra Grover, el
  único atacante cuántico aplicable; el resto de la estructura no usa
  asunciones de logaritmos discretos), **o**
- reescribir el log de *todos* los notarios independientes que anclaron el
  día, sin que ninguna réplica externa detecte la divergencia, **o**
- comprometer la clave del firmante y firmar retroactivamente sin alterar la
  cadena de apertura del notario, lo que la disciplina de un solo uso y las
  raíces publicadas hacen observable.

Ninguna dependencia política, legal o social protege el valor: solo matemática
y replicación. Es la diferencia estructural frente a cualquier decreto
calendárico histórico.

## 3. Estructura del calendario

```
12 meses × 30 días = 360 días regulares (bloque De Kalendis)
Tempalum (mes 00, cierre del año): 4 días (año común) o 11 (Gran Tempalum)
Año común: 364 días = 52 semanas exactas
Gran Tempalum: 371 días = 53 semanas exactas
```

Origen: 1 Keuphero, año 0 DY. **El origen se define por su Número de Día
Juliano: día 0 = JDN 1.719.313, Soludyia por definición.** La conversión
gregoriana proléptica es un servicio de interoperabilidad de entrada/salida
y no forma parte de la definición del calendario GUS. A título de ejemplo de
conversión: JDN 1.719.313 equivale a 21 de marzo de -5 gregoriano proléptico
(6 a.C., año astronómico -5).

**Independencia del calendario civil.** El tiempo Gerarion propio es un
conteo continuo desde este origen; JDN se usa solo como contador absoluto
de días. Toda fecha gregoriana citada en esta especificación (incluida la
equivalencia del año 2031 = 17-03-2026) es un resultado derivado por
aritmética (F-01/F-02), nunca una entrada normativa. El sistema es
funcionalmente completo sin acceder a ningún calendario civil.

**Independencia de la semana civil.** El ciclo de 7 días de GUS es
independiente de la semana civil. La letra del día (S L M A T V B) es una
etiqueta del formato y no corresponde a ningún día civil. Ejemplo medido:
el 17 de marzo de 2026 gregoriano, inicio del año 2031 DY, es letra `S`
(del formato; no es una afirmación sobre el día civil de esa fecha).

Regla del Gran Tempalum (**simétrica en ambas eras**, forma cerrada; spec 2.1):
con `S = 1_242_190` µd y `U = 7_000_000` µd, para **todo** entero `year`
(positivo, cero o negativo; era DY y era AY):

```
r_y  = ((year mod U) + U) mod U        // residuo euclidiano: 0 <= r_y < U
r    = (r_y × S) mod U                 // acumulador solar del año
GT(year)  <=>  r + S >= U
```

Equivalente bit a bit a la recurrencia iterativa `r(n) = (r(n-1) + S) mod U`
para `year >= 0` (la de v2.0, conservada como justificación); los módulos son
**euclidianos** (resultado en `[0, U)`), no truncados hacia cero — la única
regla que cambia respecto de la 2.0 es la extensión: la secuencia es **infinita
en ambas direcciones**. En C11, implementarla con `euclid_mod` y `floor_div`
explícitos (`/` trunca hacia cero en negativos).

Vector normativo del patrón (`gus-normative-003`): los años GT DY son
`5, 11, 16, 22, 28, 33, 39, 45...`; los GT AY son `-1, -6, -12, -17, -23, -29...`
(`0001AY` es Gran Tempalum de 371 días: `r(-1) = 5_757_810`, `r + S = U`).
El corpus v1 listaba además "2039 DY" — errata: corresponde a 2040 DY.

Inicio de año en forma cerrada O(1) (equivalente a la suma de longitudes):

```
q, r = división piso de (year / U)      // 0 <= r < U, euclidiana
GT años acumulados = q×S + floor(r×S / U)
year_start_day_index(year) = year×364 + 7×(años GT acumulados)
```

Verificado: `year_start(0) = 0`, `year_start(-1) = -371`, y para todo
`year >= 0` coincide bit a bit con la suma iterativa de la 2.0.

El acarreo es en **microdías enteros**: sin error de punto flotante en
ningún horizonte temporal. Esta es una divergencia deliberada de v1, que
usaba `float` (defecto documentado en la errata).

## 4. Inicios de año — oscilación solar

El año no comienza *siempre* exactamente el 21 de marzo: el año común (364
días) es más corto que el tropical, y el Gran Tempalum (371) lo sobrepasa.
El inicio de año oscila alrededor del equinoccio dentro de la cota de drift
(|Δ| < 7 días; ecuación del sawtooth, demostrada en el paper del drift,
`docs/papers/`).

Vector normativo GUS: el año 2031 DY comienza el **17 de marzo de 2026**
gregoriano, Soludyia. Las fechas "21 de marzo" del corpus v1 son
aproximaciones descriptivas del equinoccio, ya no reglas.

## 5. Instante continuo y ciclos

```
instant = day_index × 86.400 + h·3600 + m·60 + s − offset_seconds
day_index ≥ 0  → era DY;  day_index < 0 → era AY
```

`HH:MM:SS` es la hora civil **del observador** que emite la marca y
`offset_seconds` es su offset declarado `TCJ±O` (§6, §9.4): así,
`2031DY-03-08-T-09:30:00-SC-TCJ+0` y `2031DY-03-08-T-07:10:00-SC-TCJ-2:20`
describen EXACTAMENTE el mismo instante, cada observador con su hora civil
y su propio ciclo. `offset_seconds` es múltiplo de 60 con |offset| ≤ 86.400.

- Sin segundos intercalares internos (Capa 0, TAI): cada día dura
  exactamente 86.400 segundos y el instante es comparable, ordenable y
  monotónico en todo el dominio. Los segundos intercalares de UTC viven
  SOLO en la tabla histórica del adaptador de entrada (§9.3).
- Ciclo luminoso (semántico, no computacional): `SC` = 06:00–17:59,
  `LC` = 18:00–05:59, evaluado SIEMPRE sobre la hora civil `HH`
  declarada del observador (§9.4). Es etiqueta, no transformación
  aritmética.

## 6. Formato canónico de marca temporal

Dos formatos canónicos oficiales (Cap. 13.1; precedente: ISO 8601
extended/basic):

```
EXTENDIDO (32 caracteres; forma canónica de SALIDA):
  AAAAYY-MM-DD-X-HH:MM:SS-CC-TCJ±O
  2031DY-03-08-T-09:30:00-SC-TCJ+0
  Uso: legibilidad humana, documentos, logs de auditoría.

COMPACTO (29 caracteres; entrada y almacenamiento):
  AAAAYY-MM-DD-X-HHMMSS-CC-TCJ±O
  2031DY-03-08-T-093000-SC-TCJ0
  Uso: machine-to-machine, JSON, protocolos de red.
```

Offsets `TCJ±O`: horas enteras (`TCJ+0`, `TCJ+2`) o con minutos
(`TCJ-2:20`, `TCJ+3:10`; en compacto `TCJ-220`, `TCJ+310`). Regla de
emisión: si `offset_seconds % 3600 == 0`, `TCJ±H`; si tiene minutos,
`TCJ±H:MM` (extendido) o `TCJ±HMM` (compacto). El offset cero se emite
siempre `TCJ+0` (extendido) / `TCJ0` (compacto). `TCJ±O` entra en el
cálculo del instante (§5) y describe la hora civil del observador.

Letras de día Nuvid: S, L, M, A, T, V, B (Soludyia... Sabatyeh). Reglas de
normalización: ver módulo `gerarion.format` (REGLAS 1-7 del corpus v1,
conservadas íntegras, incl. `weekday_corrected`, `GERO_ETEMPALUM`,
`GERO_EINVAL`).

Eras: `DY` (después del origen) y `AY` (antes). La regla del Gran Tempalum es
**simétrica** (§3): opera idénticamente en DY y AY vía módulo euclidiano, con
la cota de drift solar |Δ| < 7 días en ambos sentidos del origen. El conteo
hacia atrás (`year_start_day_index` por división piso + GT acumulados) es
total y no ambiguo: `year_start(-1) = -371`.

## 6.1 Niveles de nombre (solo presentación)

Decisión registrada (TODO-003 cerrado): los nombres del formato (meses,
días Nuvid, días del Tempalum, letras S L M A T V B, eras DY/AY) **son los
canónicos**; no existen nombres N0 numéricos canónicos en 2.0 — el N0
"numérico" coincide con la numeración del formato. Los niveles de nombre
(N0–N4) son exclusivamente presentación, con tablas mantenidas fuera de
este repositorio, y nunca afectan al instante, al índice de día ni a la
conformancia declarada contra los vectores. La spec 2.0 define el formato
canónico y el instante; no define nombres de presentación de terceros más
allá de las letras y la numeración del formato.

## 7. Marca temporal firmada (GST)

Documento JSON, campos: `v, ctx, alg, ts, ins, day, pub, sig, anchor`.

- `ctx = "GUS2-TS"` — separación estricta de dominio.
- Bytes firmados: `ctx || "\n" || ts || "\n" || ins || "\n"`.
- `alg` intercambiable: la referencia usa `WOTS16-MERKLE-REF-SHA256`
  (implementación educativa, hash-only). Los algoritmos de producción
  recomendados son **FIPS 205 (SLH-DSA)** y **FIPS 204 (ML-DSA)** con
  bibliotecas auditadas; la semántica de verificación es la misma interfaz.
  Nota sobre el adaptador: el paquete PyPI `slh-dsa` que usa la referencia
  es biblioteca de **código abierto sin auditoría ni validación FIPS
  verificadas** — sirve para interoperabilidad y vectores; un despliegue
  real exige una implementación auditada (o validada CMVP).
- `anchor` — inclusión Merkle en el log del notario del día.

### 7.1 Requisitos operacionales del firmante

1. Cada hoja OTS firma exactamente un documento. Reuso = catástrofe de clave
   LMS/XMSS: el estado se audita y se publica.
2. Re-key por época: el árbol es finito (por defecto 2^8 firmas); rodar a un
   árbol nuevo antes de agotarlo. La llave vieja se archiva para verificación
   histórica (no para firmar).
3. Rotación de claves firmada por la clave saliente (cadena de confianza),
   anclado en un día del notario.

## 8. Notario diario

```
day_root(n) = SHA-256("GUS2-DAY" || n || tree_root(n) || day_root(n-1))
```

- Los días se sellan en orden estricto (0, 1, 2, ...).
- Días sin marcas también se sellan (raíz vacía definida): no hay huecos
  explotables.
- La raíz del día se publica en réplicas independientes. La objetividad es
  la divergencia imposible entre réplicas honestas: reescribir el pasado
  exige convencer a todas simultáneamente.

## 9. Escala de tiempo — TAI, TCJ y frontera con UTC (GUS 3.0.0)

Arquitectura de cuatro capas temporales (Cap. 13.0 del documento canónico):

```
CAPA 3: TSLR (Tiempo Solar Local Real) — perfil forense OPCIONAL;
        verificación astronómica con efemérides y quorum (§9.6).
CAPA 2: Fecha civil Geroriana — presentación humana y
        planificación (§5/§6): meses, semana Nuvid, ciclo SC/LC.
CAPA 1: TCJ = TAI + 8,400 s — coordenada global de referencia (§9.2).
CAPA 0: TAI — base atómica continua y monotónica; el soporte del
        entero `instant` y de todas las firmas (§9.1, §9.3).
```

### 9.1 Definición del instante (CIERRA D-001)

**DECISIÓN ADOPTADA en GUS 3.0.0** (sustituye la frontera "medianoche UTC"
de la 2.1): el instante GUS se define sobre **TAI** con la tabla histórica
TAI−UTC explícita, y la coordenada de referencia global es **TCJ =
TAI + 8,400 s**. El entero `instant` es segundos continuos desde el origen
(`0000DY-01-01-S-00:00:00-LC-TCJ+0` = 0), sin segundos intercalares
internos:

```
instant = day_index × 86.400 + h·3600 + m·60 + s − offset_seconds
```

Dos vistas del mismo instante son válidas y interconvertibles
(`parts_from_instant(instant, offset_seconds)`); la forma canónica de
salida es SIEMPRE la vista `TCJ+0` (§6).

### 9.2 TCJ — Capa 1 (sin SPOF)

```
TCJ = TAI + 8,400 s      (meridiano de Jerusalén, 35.2137°E)
```

TCJ NO es un servidor ni una autoridad central: es un offset matemático
fijo que cualquier reloj puede calcular sin consultar a nadie (sin punto
único de falla). Referencia geográfica: Jerusalén, 31.7683°N, 35.2137°E,
754 m. Convención con sistemas legacy: TCJ−UTC ≈ +2 h 20 min 37 s en 2026
(8,400 s + 37 s de TAI−UTC).

### 9.3 Tabla histórica TAI − UTC (adaptador de entrada, Capa 0)

El puente Unix/UTC → GUS aplica la tabla histórica IERS completa
(constante embebida en `src/gerarion/tai.py`, `web/gerarion.mjs` e
`impl-c/gus.c`; 29 entradas: 1958-01-01 = 10 s … 2017-01-01 = 37 s):

```
tai_unix = unix_seconds + tai_minus_utc(unix_seconds)
tcj_unix = tai_unix + 8,400
instant  = tcj_unix + 62_318_160_000     (constante GUS_UNIX_OFFSET)
```

- Pre-1958 (D-001.1, convención declarada): extensión proléptica con
  offset 0 s, sin pretensión de coincidir con UT1/efemérides históricas.
- Inversa (`instant → unix`): exacta por segmentos de la tabla; el
  round-trip es exacto en ambos sentidos (verificado por la suite).
- Un segundo intercalar histórico (p. ej. 2016-12-31T23:59:60Z) produce
  una diferencia de enteros de 2 s: las diferencias de `instant` son
  duraciones físicas exactas (esta es la propiedad que la 2.1 no
  garantizaba).

### 9.4 SC/LC del observador y offsets con minutos (CIERRA TODO-004)

El ciclo `SC`/`LC` se evalúa SIEMPRE sobre la hora civil `HH` declarada
del observador en la marca temporal, nunca sobre la hora `TCJ+0`: un
observador en Tokio a las 02:00 locales tiene `LC`, igual que uno en
Jerusalén a las 02:00 locales. Los offsets admiten minutos (§6); el rango
válido es |TCJ±O| ≤ 24 h en múltiplos de 60 s.

### 9.5 Niveles de firma y Perfil IoT Ligero (Cap. 13.4)

- **Nivel 0** — sin firma (informativo). **Nivel 1** — firma simple con
  ancla TAI. **Nivel 2** — + ancla de red (Roughtime/TSA). **Nivel 3** —
  + verificación astronómica TSLR con quorum (§9.6).
- **Perfil IoT Ligero**: reloj interno + clave embebida, hash encadenado
  local y sincronización oportunista; SIN GPS/TPM/Roughtime. Declarado
  explícitamente NO apto para evidencia forense (concesión de seguridad
  por viabilidad económica).

### 9.6 Perfil forense TSLR (opcional, Capa 3)

> **CARÁCTER EXPERIMENTAL.** TSLR (Capa 3) y GCERTS (Cap 13.4) son perfiles
> EXPERIMENTALES, separados del núcleo normativo: no forman parte de la
> garantía de conformidad del calendario ni de la marca canónica. GUS no
> sustituye los controles de seguridad del sistema operativo, el aislamiento
> de hardware ni las mitigaciones de red: los cubre por fuera, nunca en su
> lugar.

Verificación astronómica opcional para evidencia de Nivel 3:

- Posición solar (altitud/azimut) calculada con efemérides (DE440) y
  fijada por `ephemeris_hash` obligatorio: una actualización futura de la
  efeméride nunca invalida retroactivamente una firma anterior.
- **Quorum 3-de-4 Nodos Maestros** (Jerusalén 31.7683°N/35.2137°E,
  Sèvres (BIPM) 48.8292°N/2.2203°E, Santiago 33.4489°S/70.6693°O, Sídney
  33.8688°S/151.2093°E): sin punto único de falla de verificación.
- **Protocolo polar** (latitud |φ| > 66.5°): el cálculo TSLR por
  altura/azimut es degenerado en noches o días polares; en ese caso el
  verificador degrada la marca a Nivel 2 y registra la condición.
- Invariantes de integridad (Cap. 13.6): monotonía de `tai_seconds`,
  consistencia ciclo/hora del observador, consistencia día de semana
  (invariante I-1), consistencia año↔TAI y verificabilidad de la
  efeméride declarada; logs con hash encadenado y doble sello
  (`gero_canonical` + `tai_seconds`) en eventos críticos.

## 10. Interoperabilidad

- Convertibilidad exacta con el gregoriano proleptico vía JDN (ida y vuelta
  verificada por la suite de tests, sin ventana de exclusión).
- Mapeo directo con `datetime` gregoriano; sin librerías externas.
- Forks del formato (`1404IY-...`, `5786AH-...`) permanecen válidos: el fork
  es una elección de valores de época, nunca de algoritmo.

## 11. Versionado

- `GUS x.y.z` — semver sobre la *especificación*, no el software.
- Cambios en el algoritmo de conversión o en el formato canónico: `x.y.0+`
  (mayor).
- Cambios solo criptográficos o de anclaje: `x.0.z` (menor).
- Cualquier cambio requiere: (1) vectores nuevos en `tests/`, (2) entrada de
  errata/changelog, (3) periodo de comentario público de un release.

## Apéndice A — Formalización matemática y época normativa (GUS 3.0.0)

Este apéndice fija, con demostraciones cerradas, las propiedades numéricas
del calendario y el estatus de la época. Nada de lo aquí escrito modifica el
algoritmo: congelar la aritmética y dejar constancia de por qué es segura
son objetivos complementarios.

### A.1 Duración media exacta del año

Con el acumulador solar en microdías `U = 7.000.000` y el paso de
Tempalum `S = 1.242.190`, cada bloque de `U` años añade `7·S = 8.695.330`
días solares, repartidos como 7 días extra en `S` años Gran Tempalum:

    L  = 364 + 7·(1.242.190 / 7.000.000)
       = 364 + 8.695.330 / 7.000.000
       = 364 + 1,24219
       = 365,24219 días  (racional exacto, sin aproximación)

La expansión decimal se agota en 5 decimales exactos: 365,24219 no es una
aproximación flotante sino el cociente racional exacto, coincidente con la
duración del año trópico medio de la referencia J2000.

### A.2 Cota estricta de la deriva solar: |Δ| < 7 días para todo n ∈ ℤ

Defínase `ysi(n)` = `day_index` del 1-1 del año `n` y, con la división piso
euclidiana ( resto `Rₙ = n·S mod U ∈ [0, U)` también en la era `AY`):

    g(n)    = floor(n·S / U)
    ysi(n)  = n·364 + 7·g(n)

Restándole la traza ideal `n·L`:

    ysi(n) − n·L = 7·( floor(n·S/U) − n·S/U ) = −7·( Rₙ / U )

con `Rₙ/U ∈ [0, 1)` por la definición misma del residuo euclidiano
(invariante: `n = q·U + Rₙ`, `0 ≤ Rₙ < U`, válido para `n < 0`). Por tanto:

    −7 < ysi(n) − n·L ≤ 0      y      |Δ(n)| < 7 días, ∀ n ∈ ℤ (AY y DY)

La deriva del inicio de año respecto del calendario solar ideal está
acotada ESTRICTAMENTE por 7 días: el año nunca empieza más de 7 días
"después" del punto ideal y siempre dentro del mismo año, y el valor se
recupera en cada Gran Tempalum (el residuo nunca se hereda acumulado).
Comprobación numérica del invariante: para n = 1 … 200.000, max(Rₙ/U)
= 0,99999857… < 1.

### A.3 Invariancia semanal perpetua

Todo año común dura `364 ≡ 0 (mod 7)` días y todo año Gran Tempalum
`371 = 364 + 7 ≡ 0 (mod 7)`. Sea cual sea el año, la semana termina
alineada: el 1-1 de TODO año cae en el mismo día de la semana (Soludyia)
y para dos días cualesquiera `d₁, d₂`:

    semana(d₁) = semana(d₂)  ⟺  d₁ ≡ d₂ (mod 7),   ∀ d ∈ ℤ

La semana de Gerarion no puede desalinearse jamás, en ninguna era ni
desplazamiento; la letra del día es función pura `weekday(d) = ((d mod 7)+7) mod 7`.

### A.4 Convención normativa de época ≠ historiografía

La época del estándar es:

    0000DY-01-01-S  ≡  JDN 1.719.313  ≡  21 de marzo de −5 proléptico
                       (año astronómico −5; 6 a.C.)

Se declara como **época matemática fija, determinista y reproducible**:
un origen elegido por coherencia astronómica y cultural del proyecto. Su
función normativa es la UNICIDAD y la REPRODUCIBILIDAD de las coordenadas,
no la datación historiográfica de eventos antiguos: GUS no afirma nada
sobre la fecha exacta de ningún hecho histórico, y los debates
historiográficos quedan explícitamente DESACOPLADOS del estándar (§10:
un fork puede fijar otra época cambiando el JDN base, sin alterar un
solo paso del algoritmo).

### A.5 Envolvente operativa segura por plataforma

Límites verificados (sin desbordamiento con signo; C11 devuelve
`GERO_ERANGE` antes de calcular cualquier valor fuera de rango):

| Magnitud | C11 (`impl-c`) | Python (referencia) | JavaScript (`web/`) |
|---|---|---|---|
| `instant` (s) | `int64` exacto en ±9.223.372.036.854.775.807 s ≈ ±2,92·10¹¹ años; más allá: `GERO_ERANGE` | `int` arbitrario: exacto en todo ℤ (en wire/formato: int64) | `BigInt`: exacto (cobertura total del contrato int64) |
| `nanos` | `uint32` 0..999.999.999, campo separado | `int` 0..999.999.999, campo separado (validación estricta) | 0..999.999.999, campo separado |
| Calendario: `day_index` | ±9.172.971.096.762.673.200 d ≈ ±2,51·10¹⁶ años | exacto | `Number` exacto hasta 2⁵³−1 d ≈ ±2,466·10¹³ años; más allá: `GERO_EINVAL` |
| Vía gregoriana (JDN) | ±2.305.843.009.211.906.069 d ≈ ±6,31·10¹⁵ años | exacta | 2⁵³−1 (el factor 4 de la conversión acota antes) |
| Año de entrada (`fromGerarion`) | ±25.200.470.046.051.300 ≈ ±2,52·10¹⁶ años | exacto | ±23.703.155.933.528 ≈ ±2,37·10¹³ años |

Los `day_index` por encima de 2⁵³−1 son válidos y exactos en C11 y Python;
JavaScript los rechaza. Esta asimetría es el contrato (Apéndice de
`gus.h`, comentario de cabecera de `web/gerarion.mjs`) y la red de pruebas
la ejerce: `tools/fuzz_diff.py --cases 1000000` (ops `tg`/`fg` comunes,
`tgs`/`fgs` Python↔C y `tgq`/`fgq`/`grq`/`inq` con `GERO_ERANGE` esperado)
y `make -C impl-c audit` (un millón de idas y vueltas en los extremos
int64 más 400.000 entradas de parser bajo ASan+UBSan).
