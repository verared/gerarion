# Vectores normativos GUS — `gus-normative-002`

Este directorio contiene la **única fuente normativa de vectores de prueba** de
GUS activa: `gus-normative-002.json`. Define qué significa "implementación
conforme"
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
archivo vigente se publica en el CHANGELOG de cada versión de GUS:

```
SHA-256(vectors/gus-normative-002.json)
= 580d8843137c0e8f1a77c670773ce8090a49ea21cb0d70a9b6a5aec2c1de08b0
```

## Versiones del set

| Vector set | Espec | Estado |
|---|---|---|
| `gus-normative-001` | GUS 2.0 (alfa) | **ARCHIVADA** en `vectors/archive/` — desfasada por el Gran Tempalum simétrico (AY), spec 2.1: sus entradas de era AY usaban años comunes fijos de 364. Los valores de era DY de la 002 son bit a bit los de la 001. |
| `gus-normative-002` | **GUS 2.1.0** | **VIGENTE** — núcleo con GT simétrico en DY y AY; añade vectores AY (`0001AY-00-11-B`, `12000AY-01-01-S`, años -1/-6/-12/-17/-29/-12000, patrón GT m45..m1). |

## Runners de conformancia incluidos

- Python: `tools/conformance.py` (llamado por `tests/test_conformance.py`)
- JavaScript: `node web/conformance.mjs` (núcleo)
- C: `make -C impl-c conformance` (núcleo, segunda implementación independiente)
- Fuzzing diferencial entre las tres: `python3 tools/fuzz_diff.py`

Una implementación nueva en cualquier lenguaje debe consumir directamente
`gus-normative-002.json` (no copiar vectores a mano a su suite) y ejecutar al
menos la cláusula del núcleo antes de declararse compatible con GUS.

## Archivos de perfil

Los perfiles de interoperabilidad llevan sus propios vectores, separados del
núcleo para que la conformancia del núcleo no dependa de perfiles opcionales:

| Archivo | Perfil | Cláusula |
|---|---|---|
| `gus-normative-002.json` | Núcleo calendario/formato/instantes/GST/notario (arriba) | obligatorio toda implementación |
| `gus-3339-001.json` | **GUS-3339**: instante GUS ↔ RFC 3339 UTC (perfil estricto Z) | obligatoria solo para implementaciones que declaren el perfil |
| `gus-3339-negative-001.json` | **GUS-3339 negativo**: entradas inválidas que deben RECHAZARSE (F1) | obligatoria para implementaciones que declaren GUS-3339 |
| `gus-regression-001.json` | **Regresión AY** (F2): `0001AY-00-11-B` y vecinos tras el GT simétrico | obligatoria toda implementación |
| `gus-quickverify-001.json` | **Verificación rápida O(1)** (Cap 13.8 v1.2): consistencia sin red, tampering detectado sin normalizar | opcional para implementaciones que expongan `quick_verify`/`quickVerify`/`gus_quick_verify` |

Regla: el núcleo nunca cambia por añadir un perfil. Runners del perfil
GUS-3339: `python3 -m pytest tests/test_profiles.py` (Python) y
`node web/profiles-conformance.mjs` (JavaScript). La C de referencia no
implementa perfiles. Runners del vector quick-verify:
`python3 -m pytest tests/test_quick_verify.py`, `node web/tests.mjs`
y la 10ª categoría de `make -C impl-c conformance`.
