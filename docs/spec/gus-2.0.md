# Gerarion Universal Standard (GUS) — Especificación v2.0

> Esta especificación sustituye al borrador histórico v1.2 (documentado como
> material complementario no normativo en `docs/papers/`).
> Toda propiedad de v1 que se conserva se reproduce aquí de forma ejecutable
> y verificada por la suite de tests. Toda divergencia está documentada en
> `docs/errata-v1.2.md`.

## 1. Qué es

GUS define:

1. **Un calendario regular** — 12 meses de 30 días exactos más un período de
   cierre (Tempalum) de 4 u 11 días. Toda la aritmética de fechas es sin
   casos borde.
2. **Una semana invariante** — todo año dura 52 o 53 semanas exactas, de modo
   que una fecha fija cae siempre en el mismo día de la semana.
3. **Un instante continuo** — segundos desde el origen, sin segundos
   intercalares (análogo a TAI; ver §9 para la frontera exacta con
   UTC/TAI). El conteo es lineal y total.
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

Regla del Gran Tempalum (recurrencia exacta, entera):

```
r(0)        = 0
r(n)        = r(n-1) + 1_242_190_µd        si r(n-1) + 1_242_190_µd < 7_000_000_µd
r(n)        = r(n-1) + 1_242_190_µd - 7_000_000_µd   en caso contrario
GT(n)       = (r(n) + 1_242_190_µd >= 7_000_000_µd)
```

Vector normativo del patrón: los años GT son `5, 11, 16, 22, 28, 33, 39, 45...`
(el corpus v1 listaba además "2039 DY" — errata: corresponde a 2040 DY).

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
instante = day_index × 86.400 + segundos_del_día
day_index ≥ 0  → era DY;  day_index < 0 → era AY
```

- Sin segundos intercalares: cada día dura exactamente 86.400 segundos y el
  instante es comparable y ordenable en todo el dominio.
- Ciclo luminoso (semántico, no computacional): `SC` = 06:00–17:59,
  `LC` = 18:00–05:59. Es etiqueta, no transformación aritmética.

## 6. Formato canónico de marca temporal

```
AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O]

Ejemplo mínimo: 2031DY-03-08-T
Ejemplo completo: 2031DY-03-08-T-09:30:00-SC-TCJ+0
```

Letras de día Nuvid: S, L, M, A, T, V, B (Soludyia... Sabatyeh). Reglas de
normalización: ver módulo `gerarion.format` (REGLAS 1-7 del corpus v1,
conservadas íntegras, incl. `weekday_corrected`, `GERO_ETEMPALUM`,
`GERO_EINVAL`).

Eras: `DY` (después del origen) y `AY` (antes). Los años AY negativos se
extienden con años comunes de 364 días: la secuencia de Gran Tempalum se
define hacia adelante del origen, y la era AY no participa de ella. El conteo
hacia atrás exige exactamente esa definición para ser total y no ambigua.

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

## 9. Frontera con UTC/TAI

Qué hace **exactamente** la implementación de referencia (verificado en
`calendar.py`, `web/app.js`), ni una regla más:

- La escala de instantes es **análoga** a TAI: sin segundos intercalares,
  conteo lineal (`instante = day_index × 86.400 + hora_civil`). **No es
  TAI con tabla**: no existe ninguna tabla TAI−UTC en el código ni en los
  vectores; los segundos intercalares acumulados desde 1972 (37 s en la
  fecha de esta versión) **no se aplican** a ningún instante.
- Inicio del día (**NORMATIVO, D-001 resuelta**): el día GUS rueda a
  **medianoche UTC** — el día `[n, n+1)` es el intervalo de segundos GUS
  `[n×86.400, (n+1)×86.400)` en la escala anterior. El meridiano del día
  queda fijado a la medianoche UTC del reloj civil de referencia; **no**
  es medianoche TAI ni medianoche en zona horaria local.
- Pre-1958 (**NORMATIVO, convención declarada**): la misma aritmética
  entera se extiende **prolépticamente** para fechas anteriores a la
  introducción de TAI (1958) y de la tabla TAI−UTC (1972): un instante
  GUS pre-1958 es un recuento lineal de segundos civiles UTC de pared
  sobre el gregoriano proléptico, sin pretensión de coincidir con las
  efemérides históricas UT1/TAI. La correspondencia con esas escalas
  queda fuera de GUS (adaptadores, no núcleo).
- Consecuencia declarada: el instante GUS derivado de una hora UTC
  difiere del tiempo TAI transcurrido real en los segundos intercalares
  acumulados (37 s en 2026, valor congelado en los vectores
  normativos). Cualquier cambio futuro de esta regla (p. ej. la
  propuesta D-001 de medianoche TAI) exige nueva versión de spec y del
  vector set vía el Looking Period (GOVERNANCE §3.1) — no es aplicación
  retroactiva de esta versión.

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
