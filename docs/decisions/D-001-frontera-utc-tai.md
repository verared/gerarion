# Decisión D-001 (CERRADA / ADOPTADA en GUS 3.0.0) — Frontera del instante GUS con UTC/TAI

> **Estado**: **CERRADA — ADOPTADA en GUS 3.0.0** (rama
> `beta/gus-3-tai`). La spec 3.0.0 adopta la propuesta íntegra: instante
> definido sobre TAI con la tabla histórica IERS TAI−UTC embebida
> (§9.3), coordenada global **TCJ = TAI + 8,400 s** (Jerusalén,
> 31.7683°N / 35.2137°E / 754 m) y nuevo vector set
> (`gus-normative-003` + `gus-3339-002`; los anteriores archivados en
> `vectors/archive/`). **EN normativo**:
> [`docs/en/decisions/D-001-utc-tai-boundary.md`](../en/decisions/D-001-utc-tai-boundary.md).
>
> Histórico: la spec 2.1 quedó congelada con medianoche UTC (TODO-001
> cerrado 2026-11-17) y esta decisión permaneció abierta como candidato
> a cambio de kernel hasta su adopción en 3.0.0.
>
> **Qué hace HOY el código** (sección única «Escala de tiempo» del README):
> el día GUS rueda a medianoche UTC y el entero NO aplica tabla TAI−UTC
> (mapeo tipo Unix/POSIX). Consecuencia medida: cruzar el intercalar
> histórico 2016-12-31T23:59:60Z hace subir el entero 1 s mientras
> transcurrieron 2 s SI — las diferencias de enteros son duraciones de
> etiqueta, no siempre duraciones físicas exactas. Adoptar esta propuesta
> (instante sobre TAI con tabla explícita) cambiaría esos valores: es una
> DECISIÓN DEL AUTOR, no una omisión.

## 1. Contexto

La spec 2.0 (§9) declara la escala de instantes "análoga a TAI" y deja no
especificados tres puntos (TODO-001 en `docs/TODO-pendientes.md`):

- (a) el meridiano del día GUS: medianoche UTC vs medianoche TAI;
- (b) la conversión UTC↔GUS y la tabla TAI−UTC (37 s en 2026);
- (c) el tratamiento de TAI antes de 1958.

El estado de facto actual (documentado, no normativo): el reloj de
referencia web re-etiqueta el segundo UTC directamente; el día GUS rueda a
medianoche UTC; sin tabla.

## 2. Decisión propuesta

**El instante GUS se define sobre TAI**: `instante = segundos atómicos
transcurridos desde (1 Keuphero, año 0, 00:00:00 TAI-proléptico)`.

Sub-decisiones:

- **D-001.1 (punto c)** — *TAI antes de 1958 es convención declarada, no
  medida*: la extensión proléptica de TAI hacia el pasado es un acto
  aritmético (la misma nominal de segundo), sin pretensión de coincidir
  con las efemérides históricas (UT1/ET). Toda fecha GUS anterior a
  1958-01-01 TAI lleva esa condición en su semántica.
- **D-001.2 (punto a)** — *el día GUS rueda a medianoche TAI*: el día
  `[n, n+1)` pertenece a la escala; la lectura civil (calendario de
  pared, zonas horarias) es un adaptador, nunca parte del instante.
  Consecuencia operacional: hoy la medianoche TAI ocurre ~37 s después
  de la medianoche UTC.
- **D-001.3 (punto b)** — *la conversión UTC↔GUS es un adaptador con
  tabla explícita*: se publica `adapters/tai-utc.json` (fecha de vigencia
  → offset TAI−UTC en segundos), regenerada con cada release que la
  cambie, con checksum en el CHANGELOG. La referencia Python/JS pasará
  de "re-etiquetado directo" a aplicar el offset vigente de la tabla; el
  reloj web mostrará la hora civil corregida (la diferencia actual son
  37 s y el README lo hará visible).

## 3. Alternativas rechazadas

- **(1) Medianoche UTC (status quo)**: acumula una deriva no declarada
  frente a TAI que crece sin mecanismo de corrección; convierte "sin
  segundos intercalares" en una promesa hueca exactamente en la frontera
  donde se la necesita.
- **(3) Época declarada sin tabla** (la actual "no especificado"):
  lastra la atestación forense — un log GUS nunca diría cuántos segundos
  atómicos hay entre dos marcas — sin ganar nada a cambio.

## 4. Coste declarado

- El día TAI se separa ~37 s del día civil UTC (en 2026): los usuarios
  de hora civil percibirán el ajuste del adaptador, no del núcleo.
- Cambia los instantes de los vectores `instant` existentes (offset
  constante `− Δ(t)`), lo que exige nueva versión del vector set
  (`gus-normative-002`) y regeneración de todos los sellos de prueba.
  Coste de migración: una constante por réplica, sin reescritura de logs
  históricos (los logs viejos declaran la versión del vector set con que
  fueron creados).

## 5. CGPM 2025 (contexto, no requisito)

La CGPM resolvió eliminar los segundos intercales de UTC hacia 2035; el
leap-smear (Google/AWS) y NTS (RFC 8915) mitigan síntomas, no la causa.
TAI como base alinea GUS con esa resolución: UTC queda, en cuanto a la
escala, como adaptador civil con tabla — no como escala.

## 6. Plan de actualización (cuando la ventana cierre)

1. Spec 2.1: definición en §3/§9, semántica proléptica pre-1958 (§9).
2. `vectors/gus-normative-002.json` con los instantes recalculados y la
   tabla TAI−UTC vigente embebida como constante del vector set.
3. Adaptador `tai-utc` Python/JS + regeneración del reloj web.
4. Validación diferencial Python/JS/C con los nuevos vectores.
