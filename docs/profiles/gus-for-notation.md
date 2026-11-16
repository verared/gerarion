# GUS-for-notation — superficie mínima: notación e interoperabilidad

> **Capa**: documento de adopción (perfil mínimo) · **Versión**: 1 · **Estado**: espejo ES (normativo: EN)
> **Documento normativo**: [`docs/en/profiles/gus-for-notation.md`](../en/profiles/gus-for-notation.md) — EN prevalece.
> Sin criptografía, sin notario, sin protocolo: es lo más pequeño que un tercero puede adoptar.

## Resumen

Este documento define la superficie MÍNIMA del Estándar Universal
Gerarion (GUS) que un sistema necesita para intercambiar y comparar
valores de tiempo sin ambigüedad: el formato canónico de marca, el
instante continuo, el mapeo con RFC 3339 (GUS-3339) y el vector set
normativo legible por máquina.

## 1. El instante

- Entero exacto: segundos transcurridos desde el origen GUS (día 0,
  00:00:00), con signo (negativo = era AY).
- El día 0 se define por su JDN: 1.719.313. Por conversión equivale al
  21 de marzo de -5 gregoriano proleptico (año astronómico -5 = 6 a.C.);
  la equivalencia es derivada, no definitoria. El JDN es el punto de
  interop con cualquier sistema gregoriano/proleptico.
- Escala sin segundos intercalares (conteo lineal análogo a TAI). La
  frontera UTC/TAI con la conversión exacta es la decisión D-001
  (borrador, en revisión de 90 días); mientras no se RESUELVA, el
  mapeo UTC↔instante por GUS-3339 se define por los vectores normativos,
  no por prosa.

## 2. Marca canónica

    AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O]

- Año 1-4 dígitos + era DY/AY; mes 01..12 (00 = Tempalum, mes de cierre);
  día 01..30 (o 01..04 / 01..11 en Tempalum); letra de día S L M A T V B.
- La letra de día es DERIVADA (día mod 7), la calculada siempre prevalece
  (REGLA 4); el conflicto se reporta (GERO_EWEEK).
- Hora opcional 00:00:00..23:59:59; el segundo intercalar :60 está
  PROHIBIDO. Ciclo SC/LC debe coincidir con la hora. Offset TCJ±O en horas.
- Día Tempalum > 4 en año común → GERO_ETEMPALUM.
- Bytes canónicos para firma/anclaje (contexto GUS2-TS): ver vectores.

## 3. GUS-3339 (interoperabilidad RFC 3339 UTC)

- Offset exacto (vector set `gus-3339-001.json`):
  instante(UTC 1970-01-01T00:00:00Z) = 62.318.160.000 s, es decir
  (JDN 2.440.588 − ORIGIN_JDN 1.719.313) × 86.400.
- Dominio años 0000..9999; 'Z' y '+00:00' equivalentes; :60 y offsets
  ≠ 0 rechazados con GERO_E3339.

## 4. Errores

GERO_EINVAL, GERO_ETEMPALUM, GERO_EWEEK, GERO_E3339 (mismos códigos en
todas las implementaciones).

## 5. Conformancia (única regla)

Una implementación es conforme a GUS-for-notation si y solo si consume
`vectors/gus-normative-001.json` y `vectors/gus-3339-001.json` y produce
exactamente la salida declarada por los vectores, incluidos los códigos
de error exactos. Dos implementaciones conformes con los mismos vectores
NO pueden divergir silenciosamente: los vectores SON el estándar.

## 6. Consideraciones de seguridad

El formato es notación: hace comparables y ordenables los valores de
tiempo, pero no certifica NADA sobre la veracidad del instante
declarado. El tiempo autenticado exige la capa de atestación (GST,
perfiles GUS-3161 y GUS-Roughtime) y una fuente de tiempo confiable al
firmar; la notación NO debe confundirse con un reloj.

## 7. Consideraciones IANA

Ningún registro requerido por este documento.
