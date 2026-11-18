# Perfil GUS-3339 — instante GUS ↔ RFC 3339 (UTC)

> **Capa**: 0 (núcleo normativo) · **Versión**: 3339-001 · **Estado**: normativo
> **EN normativo**: [`docs/en/profiles/gus-3339-profile.md`](../en/profiles/gus-3339-profile.md) — en caso de divergencia, prevalece la versión inglesa (EN > ES).
> **Vectores**: [`vectors/gus-3339-001.json`](../../vectors/gus-3339-002.json)

## 1. Propósito

GUS-3339 define la únicas regla de interoperabilidad que un sistema
existente necesita para *emitir y consumir* tiempo GUS sin adoptar el
calendario Gerarion: convertir un instante GUS entero a un string
RFC 3339 en UTC, y de vuelta. Es el equivalente funcional de
ISO 8601 / RFC 3339 para la escala de instantes GUS — no un parser
general de fechas.

Con este perfil, cualquier campo existente que ya transporte
`2026-05-23T09:30:00Z` (columnas SQL, headers HTTP, JSON, X.509
`notBefore`, logs) puede transportar tiempo GUS sin cambios de esquema.

## 2. Constante de anclaje

| Nombre | Valor | Definición |
|---|---|---|
| `GUS_UNIX_OFFSET` | `62_318_160_000` | Instante GUS de `1970-01-01T00:00:00Z` = `(2 440 588 − 1 719 313) × 86 400` |

Equivalencia: para instante GUS `I`, el segundo UTC etiquetado es
`unix = I − GUS_UNIX_OFFSET`. Ambas escalas son etiquetas sin segundos
intercalares (ver §9 de la spec para la frontera exacta UTC/TAI), de
modo que el mapping es **biyectivo** en el dominio declarado.

## 3. Reglas del perfil (MUST)

1. **Forma canónica única**: `AAAA-MM-DDTHH:MM:SSZ`. Separador `T` y
   sufijo `Z` en mayúsculas. Un emisor RFC 3339 conforme al perfil no
   produce minúsculas, fracciones decimales ni desplazamientos de zona.
2. **Solo UTC**: formas con offset (`+01:00`) son invalidas bajo perfil.
   Quien recibe hora local la convierte a UTC antes de entrar.
3. **Segundo `:60` prohibido** (MUST): la escala GUS no tiene segundos
   intercalares. Plegar `:60` en `00:00:00` rompería la inyectividad;
   una fuente UTC que emite `:60` DEBE convertir a etiqueta Unix antes.
4. **Dominio**: años gregorianos `0000..9999`. El origen GUS (año −5) y
   la era AY quedan fuera de este formato: para ese rango se usa el
   string canónico GUS (`AAAAAY-MM-DD-X…`) o el instante entero.
5. **Aritmética**: conversiones enteras puras vía JDN gregoriano
   proleptico (misma base que el núcleo GUS). Error canónico:
   `GERO_E3339`.

## 4. Conformancia

Una implementación declara el perfil GUS-3339 si y solo si pasa el 100 %
de los vectores de `vectors/gus-3339-001.json` (8 mappings, 8 rechazos,
3 casos de coherencia con el formato canónico GUS). La conformancia del
núcleo (`gus-normative-002.json`) es independiente y no implica este
perfil. Verificada en: Python (`tests/test_profiles.py`), JavaScript
(`web/tests.mjs`, `node web/profiles-conformance.mjs`). La C de referencia
no implementa perfiles (solo núcleo).

## 5. Errores canónicos

- `GERO_E3339` — entrada fuera de perfil (sintaxis no canónica, offset,
  `:60`, fecha inválida) o instante fuera del dominio 0000..9999.
