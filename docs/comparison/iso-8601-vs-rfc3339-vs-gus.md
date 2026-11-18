# ISO 8601 vs RFC 3339 vs Gerarion GUS v3.0.0 — Cap. 13.5 Comparativa de identificadores

> Documento explicativo (no normativo). Contrastado contra el código real
> del repositorio (`src/gerarion/`, `web/gerarion.mjs`, `impl-c/gus.c`) y
> contra los vectores normativos `gus-normative-003.json` /
> `gus-3339-002.json`. Cada afirmación está marcada como **[CONFIRMADO]**
> (verificado contra código o vectores) o **[MATIZ]** (la afirmación del
> borrador original sobre-alcanza; aquí está la precisión).

## 1. Los tres formatos, lado a lado

| Criterio | ISO 8601 | RFC 3339 | Gerarion GUS v3.0.0 |
|---|---|---|---|
| Ejemplo | `20240115T123045` | `2024-01-15T12:30:45Z` | `2031DY-03-08-T-09:30:00-SC-TCJ+0` |
| Longitud mínima | 15 caracteres (**CONFIRMADO**: `len=15`) | 20 caracteres (**CONFIRMADO**: `len=20`) | 32 extendido (**CONFIRMADO**: `len=32`); 29 compacto (**CONFIRMADO**: `len=29`) |
| Forma compacta | sí (`20240115T123045`) pero suele omitir la zona | prohibido (exige guiones y dos puntos) | sí, con designador de referencia intacto: `2031DY-03-08-T-093000-SC-TCJ0` |
| Zona obligatoria | no (opcional, en la práctica casi siempre omitida) | sí (`Z` o `±HH:MM`) | sí, con hora: `TCJ±O` **obligatorio** en toda marca con hora (**CONFIRMADO** en la gramática del parser, `src/gerarion/format.py`) |
| Ambigüedad de zona | alta | baja | **cero** (el offset es dato estructural de la marca, no metadata opcional) |
| DST / hora duplicada | la zona puede tener DST → hora ambigua en el cambio | idem (`Z` no tiene DST, pero el reloj civil del emisor sí) | la marca no tiene DST: el offset `TCJ±O` es fijo respecto de TCJ y cada instante tiene una única representación canónica (**CONFIRMADO**) |
| Escala física | gregoriano civil (intercalares y DST reales) | UTC real (con segundos intercalares) | **TAI + 8,400 s (TCJ)**: entero `int64` continuo y monotónico, sin intercalares internos (**CONFIRMADO** contra `src/gerarion/tai.py`: `TAI_MINUS_UTC = 37 s` en 2026) |
| Calendario | gregoriano civil irregular | gregoriano civil irregular | regular: 12 × 30 días + Tempalum; dígito verificador de semana integrado (**CONFIRMADO**: invariante `weekday = day_index mod 7`) |
| Detección de corrupción O(1) | ninguna | ninguna | parcial (ver §2.2 **[MATIZ]**) |
| Punto único de falla (definición) | Greenwich/ITU (Unix/UTC) | idem | TCJ es un offset matemático: cualquier reloj lo calcula sin consultar a nadie (**CONFIRMADO**, cap. 13.0) |
| Horizonte (Y2K38) | expuesto (epoch `int32` en muchas plataformas) | idem | resuelto: `instant` es `int64` de segundos continuos (horizonte ~292 mil millones de años) |

## 2. Lo que v3.0.0 resuelve estructuralmente y los otros dos no pueden tocar

(Verificado contra el código; la base TAI entra en vigor con la tabla
IERS embebida — `src/gerarion/tai.py`, `web/gerarion.mjs`,
`impl-c/gus.c` — y los vectores `gus-normative-003` / `gus-3339-002`.)

### 2.1 Ambigüedad de zona y DST

En ISO 8601 la zona es opcional y en la práctica se omite; en RFC 3339 es
obligatoria pero la hora civil de un `±HH:MM` con DST es ambigua dos veces
al año (la «hora duplicada» del cambio de horario). En GUS v3.0.0 el
desplazamiento `TCJ±O` es **obligatorio** en toda marca con hora, admite
minutos (`TCJ-2:20`) y entra en el cálculo del instante; el offset es fijo
respecto de TCJ, así que un instante dado produce exactamente una cadena
canónica y viceversa. **[MATIZ]** GUS no elimina el DST del mundo: si el
observador está en una zona con DST, las reglas de su zona civil siguen
siendo necesarias para producir el `TCJ±O` correcto al emitir la marca; lo
que GUS elimina es la ambigüedad *dentro de la marca* (lo que RFC 3339
logra exigiendo `Z`, pero con el designador siempre presente y semántica
de Tiempo Atómico, no civil).

### 2.2 Detección de corrupción estructural O(1)

La letra del día (`X`) es un dígito verificador natural
(`day_index mod 7`) y el ciclo (SC/LC) es consistente con la hora civil
declarada; la combinación (día + letra + hora + ciclo + offset) es
validable sin red en tiempo constante (**CONFIRMADO**:
`format.quick_verify` en Python; `quickVerify` en JS; `gus_quick_verify`
en C; vector `gus-quickverify-001.json` con casos de manipulación que se
RECHAZAN sin normalizar). Ni ISO 8601 ni RFC 3339 ofrecen nada
equivalente: una cadena `2024-01-15T12:30:99Z` puede ser sintácticamente
válida y temporalmente imposible, y ninguno de los dos formatos la
detecta por estructura. **[MATIZ]** La verificación O(1) detecta
inconsistencias de *día de semana* y de *ciclo* (cambiar el día rompe la
letra `X`; sacar la hora del rango 06–17 rompe SC→LC), pero NO detecta un
cambio fino dentro de una hora civil válida (`09:30:00` → `09:30:01`):
eso es un dato distinto, no una marca corrupta, y contra eso la
integridad fuerte la dan la firma (GST, cap. 13.4) y el hash encadenado
(cap. 13.6), no el formato textual. El borrador original sobre-alcanza
aquí; la precisión importa.

### 2.3 Cadena ↔ entero exacto y reversible

ISO 8601 y RFC 3339 son *presentaciones*: para calcular hay que pasar por
`datetime`, con zonas y DST. En GUS v3.0.0 la cadena canónica y el entero
`instant` (`int64`) son la misma cosa vista de dos maneras:
`instant = day_index·86400 + h·3600 + m·60 + s − offset_seconds` —
proyección entera exacta, reversible sin tablas de zonas **[MATIZ]** en
el dominio GUS (**CONFIRMADO** contra `src/gerarion/calendar.py:
instant_from_parts` / `web/gerarion.mjs` / `impl-c/gus.c`: los tres
lenguajes comparten la fórmula y los vectores `gus-normative-003`). El
puente hacia afuera (Unix/UTC ↔ GUS) sí usa la tabla histórica IERS
TAI−UTC completa (37 s en 2026; 29 entradas desde 1958), embebida en los
tres lenguajes: la conversión UTC↔GUS es exacta por segmentos, no «sin
tablas». El borrador original lo dice bien en el capítulo 13.4 («tabla de
28 saltos + convención proléptica»); la afirmación «sin tablas» de esta
sección solo es cierta dentro del dominio GUS.

## 3. Ejemplo verificado de extremo a extremo

Un mismo instante físico (2026-05-23, 09:30:00 UTC) en los tres mundos:

| Mundo | Marca | Nota |
|---|---|---|
| ISO 8601 | `20260523T093000Z` | zona `Z`; hora civil de Greenwich |
| RFC 3339 | `2026-05-23T09:30:00Z` | idem; escala UTC con intercalares |
| GUS TCJ+0 | `2031DY-03-08-T-09:30:00-SC-TCJ+0` → `instant = 64097688600` | **CONFIRMADO** contra el vector: `day_index 741871`, `weekday T`, hora 09:30:00 |
| GUS London | `2031DY-03-08-T-07:10:00-SC-TCJ-2:20` → **el mismo** `instant` | **CONFIRMADO**: mismo entero, distinta vista civil del observador |

El «día Gerarion» (`day_index = 741871`) rueda a medianoche `TCJ+0` — la
medianoche del meridiano de Jerusalén (35.2137°E), NO la medianoche UTC:
7.200 s de meridiano + 37 s de TAI−UTC más tarde que UTC
(**CONFIRMADO**: `tai_minus_utc(2026) = 37`).

## 4. Qué NO resuelve todavía GUS v3.0.0 (lagunas honestas)

Lo que la cadena canónica de GUS v3.0.0 mantiene fuera, por decisión de
simplicidad, y qué perfil o versión futura lo cubriría:

1. **Segundos fraccionarios en el texto**: la marca canónica opera a
   resolución de 1 segundo entero (`SS`); la precisión sub-segundo
   (p. ej. `tai_nanos`) vive en la capa estructurada del documento
   firmado (GST/JSON) o en perfiles futuros, no en la cadena. RFC 3339
   sí admite `.123` opcional.
2. **Zonas horarias nombradas**: GUS emite un offset `TCJ±O`, no un
   nombre de zona (`Asia/Tokyo`); la conversión desde un reloj civil con
   DST sigue necesitando tzdata en el dispositivo emisor. Misma
   limitación estructural que RFC 3339 (`±HH:MM`).
3. **Integridad criptográfica**: la cadena estandariza qué significa un
   instante, no prueba quién lo firmó; la integridad la dan GST
   (Ed25519 + ancla TAI + ancla de red Roughtime/TSA + TSLR con
   `ephemeris_hash` y quorum de Nodos Maestros; caps. 13.4/13.5), el
   hash encadenado de logs (cap. 13.6) y el notario diario (spec §8 del
   repo). Ninguna de las tres capas reemplaza a las otras.
4. **Instrumentos legales pre-Gerarion**: sin tratamiento normativo en
   este momento; el notario diario y la TSA (perfil GUS-3161) cubren
   «existió antes de ahora», no «resultado de un contrato humano firmado
   antes de adoptar GUS» — tema registrado en `docs/decisions/`.
5. **Perfiles adicionales**: IoT ligero, GUS-for-notation, TSLR y la
   fase 2 PQC son opcionales hoy; una implementación mínima conforme no
   los necesita, pero una cadena forense completa sí exige varias piezas
   coordinadas.

La conclusión honesta no es «GUS reemplaza a ISO 8601 y RFC 3339», sino:
**GUS añade la capa que a los dos les falta** — una escala física
continua (TAI) con proyección cadena↔entero exacta, designador de
coordinación obligatorio y sin ambigüedad DST dentro de la marca —
manteniendo puentes normativos hacia los dos formatos que el mundo ya
usa (README «Escala de tiempo», spec §9 de la 2.1 / §9.3 de la 3.0,
perfil GUS-3339).

---

## Anexo: verificación de las afirmaciones del borrador (contra el repo)

| Afirmación del borrador | Veredicto contra el repo |
|---|---|
| Marca extendida = 32 caracteres | **CONFIRMADO** (`len=32`) |
| Marca compacta = 29 caracteres | **CONFIRMADO** (`len=29`; `to_compact` en format.py) |
| RFC 3339 = 20 · ISO básico = 15 | **CONFIRMADO** |
| «Sin dos puntos ⇒ seguro en filesystem/URL» | **CONFIRMADO** (el compacto elimina `:`; conserva guiones, seguros) |
| TCJ±O obligatorio en marcas con hora | **CONFIRMADO** (gramática del parser) |
| «Cero ambigüedad de zona» | **CONFIRMADO** (el offset entra en el cálculo; una vista por instante) |
| Escala TAI + 8,400 s monotónica | **CONFIRMADO** (`tai.py`, vectores) |
| «Detección O(1) de corrupción» | **MATIZ** — detecta letra de semana y ciclo; NO detecta cambios finos de HH:MM:SS (para eso están la firma GST y el hash encadenado) |
| «Reversible sin tablas de zona» | **MATIZ** — exacto y reversible *en el dominio GUS*; el puente Unix/UTC sí lleva la tabla IERS de 29 entradas embebida |
| «Segundos fraccionarios fuera de la cadena» | **CONFIRMADO** (resolución 1 s en el texto; precisión extra en GST/JSON o perfiles) |
| «TCJ no es servidor» | **CONFIRMADO** (offset matemático; cap. 13.0) |
