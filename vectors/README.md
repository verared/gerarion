# Vectores normativos GUS — `gus-normative-001`

Este directorio contiene la **única fuente normativa de vectores de prueba** de
GUS: `gus-normative-001.json`. Define qué significa "implementación conforme"
y sirve a la vez a Python, JavaScript y a cualquier tercera implementación.

## Cláusula de conformancia (normativa)

> Una implementación de GUS es **conforme** si y solo si pasa el 100 % de los
> vectores de todas las categorías que declare soportar. Las categorías del
> bloque `categories_core` son el núcleo obligatorio para toda implementación;
> las de `categories_full` adicionales (`hashots`, `slh_dsa`, `notary`) son
> obligatorias solo para implementaciones que emitán o verifiquen GST.
>
> Los vectores son de **verificación** (y de creación, cuando definen semillas
> deterministas): una implementación que los "pase" con salidas distintas a las
> esperadas en cualquier campo (`canonical`, `flags`, `instant`, `day`, raíces
> del notario) **no es conforme**. Divergir silenciosamente es exactamente el
> fallo que este archivo existe para impedir.

## Contenido del archivo

| Clave | Qué valida |
|---|---|
| `constants` | Constantes fundamentales (ORIGIN_JDN, acumulador solar, formato canónico) |
| `gran_tempalum` | Patrón GT (años 0–45) y decisiones puntuales por año |
| `calendar` | Conversión gregoriano proleptico → GUS, con día de semana, nombre de Tempalum y días marcados (DAY_SACRED) |
| `year_starts` | Inicio de cada año (oscilación solar, cota \|Δ\| < 7 días, spec §4) |
| `gregorian_roundtrip` | Round-trip exacto día-índice ↔ gregoriano, incluidos bordes de era AY |
| `format` | Formato canónico: normalización, flags (`era_assumed_DY`, `weekday_corrected`, `cycle_corrected`), errores `GERO_EINVAL` / `GERO_ETEMPALUM` y modo estricto `GERO_EWEEK` |
| `instant` | Marca completa → instante continuo (bordes SC/LC, 00:00:00, era AY) |
| `hashots` | Firma hash-only de referencia: verificación de firmas WOTS16-Merkle-SHA256 + vector de manipulación que debe fallar |
| `slh_dsa` | Verificador FIPS 205 (SLH-DSA-SHA2-128F/128S, modo `pure`, contexto `GUS2-TS`) + vector de manipulación |
| `notary` | Sellado diario determinista (incluye día vacío), pruebas de inclusión Merkle y bundle multi-réplica con réplica divergente detectada por quórum |

Cada categoría criptográfica documenta sus algoritmos dentro del propio JSON
(`algorithms`) para que una tercera implementación no necesite leer código.

## Determinismo

La generación es determinista (semillas y pares de claves SLH-DSA fijos,
embebidos como constantes de vector — **jamás usar en producción**):

```
PYTHONPATH=src python3 tools/generate_vectors.py
```

Regenerar produce un archivo byte a byte idéntico. El checksum SHA-256 del
archivo vigente se publica en el CHANGELOG de cada versión de GUS.

## Runners de conformancia incluidos

- Python: `tools/conformance.py` (llamado por `tests/test_conformance.py`)
- JavaScript: `node web/conformance.mjs` (núcleo)
- C: `make -C impl-c conformance` (núcleo, segunda implementación independiente)
- Fuzzing diferencial entre las tres: `python3 tools/fuzz_diff.py`

Una implementación nueva en cualquier lenguaje debe consumir directamente
`gus-normative-001.json` (no copiar vectores a mano a su suite) y ejecutar al
menos la cláusula del núcleo antes de declararse compatible con GUS.

## Archivos de perfil

Los perfiles de interoperabilidad llevan sus propios vectores, separados del
núcleo para que la conformancia del núcleo no dependa de perfiles opcionales:

| Archivo | Perfil | Cláusula |
|---|---|---|
| `gus-normative-001.json` | Núcleo calendario/formato/instantes/GST/notario (arriba) | obligatorio toda implementación |
| `gus-3339-001.json` | **GUS-3339**: instante GUS ↔ RFC 3339 UTC (perfil estricto Z) | obligatoria solo para implementaciones que declaren el perfil |

Regla: el núcleo nunca cambia por añadir un perfil. Runners del perfil
GUS-3339: `python3 -m pytest tests/test_profiles.py` (Python) y
`node web/profiles-conformance.mjs` (JavaScript). La C de referencia no
implementa perfiles.
