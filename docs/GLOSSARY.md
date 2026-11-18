# Glosario Gerarion (GUS) / Gerarion Glossary

> Una sola definición por término. Este archivo es la referencia
> terminológica del repositorio; está enlazado desde el README y la spec.
> Cuando un término tiene versión en inglés y español, la inglesa es la
> canónica para los documentos normativos (EN > ES).

## ES

| Término | Definición única |
|---|---|
| **GUS** (Gerarion Universal Standard) | La especificación del proyecto: reglas del calendario, escala de instantes, formato canónico y perfiles de interoperabilidad. Versión normativa vigente: **3.0.0**. Es una especificación abierta; no implica aprobación por ningún organismo de estandarización. |
| **GST** (Gerarion Signed Timestamp) | Marca temporal firmada: documento que liga una marca canónica y su entero de instante con una firma. El módulo Python de referencia se llama `gerarion/gts.py` por razones históricas (GTS fue el nombre provisional del formato antes de distinguir formato y marca firmada); **no** implica un protocolo distinto llamado «GTS». |
| **GTS** (formato canónico) | Nombre histórico que la gobernanza (`GOVERNANCE.md`) usa para el **formato canónico y sus reglas de normalización** — la marca sin firma. Un documento GST *contiene* una GTS (marca) más su firma y anclaje. No existe un protocolo independiente con ese nombre. |
| **GUS-3339** | Perfil de interoperabilidad: instante GUS ↔ RFC 3339 UTC estricto (`Z`, segundos enteros, años 0000–9999, sin `:60`, sin fracciones, sin offsets). Una entrada inválida se rechaza (`GERO_*`); nunca se normaliza. |
| **GUS-3161** | Perfil de sellado temporal: vinculación de un artefacto con una Autoridad de Sellado de Tiempo (TSA conforma RFC 3161). La validez depende del dato exacto sellado, del certificado y de la confianza en la TSA; no es producción de fe por sí mismo. |
| **GUS-Roughtime** | Perfil de recibos inspirado en Roughtime (RFC 10049, experimental): nonce, radio y punto medio firmados por un testigo. **No** es una implementación completa del protocolo de red Roughtime y usa Ed25519 (criptografía clásica): no es poscuántico. |
| **GUS-for-notation** | Superficie mínima de intercambio: solo notación del calendario y el formato canónico, sin exigir las capas de atestación. Pensada para adopción gradual. |
| **Tempalum** | Mes de cierre del año GUS: 4 días en año común (364 días) y 11 días en año de Gran Tempalum (371 días). Sus fechas usan mes `00`. |
| **Gran Tempalum (GT)** | Año de 371 días (Tempalum de 11: la semana extra). Regla simétrica e infinita en ambas eras (DY y AY), definida en spec §3/§6 con módulo euclidiano y división piso. |
| **TCJ** | Tiempo de Coordinación de Jerusalén (GUS 3.0.0, CIERRA D-001): coordenada global de referencia, definida operacionalmente como **`TCJ = TAI + 8,400 s`** sobre el meridiano de Jerusalén (31.7683°N, 35.2137°E, 754 m). Es un offset matemático, no un servidor. El instante canónico se describe en `TCJ+0`; el campo `TCJ±O` describe la hora civil del observador (con minutos, TODO-004 cerrado) y resta el offset al descomponer en `day_index`/hora. |
| **day_index** | Entero continuo de días desde el origen GUS (`0000DY-01-01-S` = 0). Los años AY (era anterior) usan índices negativos. |
| **JDN** | Julian Day Number: día astronómico continuo; pivote de las conversiones multicalendario (`ORIGIN_JDN = 1719313` es el JDN del origen GUS). |
| **instant** | Entero de segundos continuos (sin segundos intercalares internos, base Capa 0 TAI) desde el origen GUS: `day_index·86400 + h·3600 + m·60 + s − offset_seconds`. El puente con Unix/UTC aplica la tabla histórica IERS TAI−UTC (Capa 0) más los 8,400 s de TCJ (Capa 1); ver «Escala de tiempo» del README. |
| **SC / LC** | Ciclo luminoso del día GUS: `SC` (06:00–17:59) y `LC` (18:00–05:59), **siempre sobre la hora civil `HH` declarada del observador** en la marca temporal (nunca forzada a `TCJ+0`). |

## EN

| Term | Single definition |
|---|---|
| **GUS** (Gerarion Universal Standard) | The project's specification: calendar rules, instant scale, canonical format and interoperability profiles. Current normative version: **3.0.0**. It is an open specification; publication here implies no approval by any standards body. |
| **GST** (Gerarion Signed Timestamp) | Signed timestamp: a document binding a canonical mark and its instant integer with a signature. The reference Python module is named `gerarion/gts.py` for historical reasons (GTS was the provisional name of the format before format and signed mark were distinguished); it does **not** imply a separate protocol called "GTS". |
| **GTS** (canonical format) | Historical name used by governance (`GOVERNANCE.md`) for the **canonical format and its normalization rules** — the unsigned mark. A GST document *contains* a GTS (mark) plus its signature and anchoring. No independent protocol carries this name. |
| **GUS-3339** | Interoperability profile: GUS instant ↔ strict RFC 3339 UTC (`Z`, whole seconds, years 0000–9999, no `:60`, no fractions, no offsets). Invalid input is rejected (`GERO_*`); it is never normalized. |
| **GUS-3161** | Timestamping profile: binding an artifact to a Time-Stamping Authority (TSA per RFC 3161). Validity depends on the exact data sealed, the certificate and trust in the TSA; it is not, by itself, legal evidence. |
| **GUS-Roughtime** | Receipt profile inspired by Roughtime (RFC 10049, experimental): nonce, radius and signed midpoint from a witness. It is **not** a complete implementation of the Roughtime wire protocol and uses Ed25519 (classical cryptography): it is not post-quantum. |
| **GUS-for-notation** | Minimal exchange surface: calendar notation and canonical format only, without requiring the attestation layers. Intended for gradual adoption. |
| **Tempalum** | The GUS closing month: 4 days in a common year (364 days) and 11 days in a Gran Tempalum year (371 days). Its dates use month `00`. |
| **Gran Tempalum (GT)** | A 371-day year (11-day Tempalum: the extra week). Symmetric, infinite rule in both eras (DY and AY), defined in spec §3/§6 with Euclidean division and floor division. |
| **TCJ** | Jerusalem Coordinated Time (GUS 3.0.0, CLOSES D-001): the global reference coordinate, operationally defined as **`TCJ = TAI + 8,400 s`** on the Jerusalem meridian (31.7683°N, 35.2137°E, 754 m). It is a mathematical offset, not a server. The canonical instant is described in `TCJ+0`; the `TCJ±O` field describes the observer's civil time (minutes allowed, TODO-004 closed) and the offset is subtracted when decomposing into `day_index`/time. |
| **day_index** | Continuous integer day count since the GUS origin (`0000DY-01-01-S` = 0). AY years (the earlier era) use negative indices. |
| **JDN** | Julian Day Number: continuous astronomical day; the pivot of the multi-calendar conversions (`ORIGIN_JDN = 1719313` is the JDN of the GUS origin). |
| **instant** | Integer seconds since the GUS origin: `day_index·86400 + h·3600 + m·60 + s`. Linear in labels; applies no TAI−UTC table (see the README "Time scale" section). |
| **SC / LC** | GUS luminous cycle: `SC` (06:00–17:59) and `LC` (18:00–05:59), always on the UTC reference hour. |
