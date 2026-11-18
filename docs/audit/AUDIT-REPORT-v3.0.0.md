# Informe de auditoría adversarial y de límites numéricos — GUS 3.0.0

**Auditoría v3.0.0 · 18 de noviembre de 2026 · verared**
Cobertura: núcleo calendárico (Python/C11/JavaScript), stack criptográfico
activo (GST v2 con JCS RFC 8785 e híbrida Ed25519+ML-DSA), guardia
anti-replay persistente y quórum del notario. Los módulos deprecados
(`hashots.py`) y los perfiles experimentales (TSLR/GCERTS) quedan fuera
del activo auditado.

## 1. Resumen ejecutivo

El sistema resiste la batería adversarial completa: **1.000.000 de casos
de fuzzing diferencial bit a bit Python↔JS↔C** sin una sola divergencia,
**1.000.000 de conversiones enteras de ida y vuelta en los extremos de
int64 sin comportamiento indefinido** (ASan+UBSan), y 18 ataques
criptográficos simulados (downgrade, sustitución de clave, replay,
rollback, quórum) con rechazo en el 100 % de los casos.

Dos debilidades REALES fueron descubiertas por esta auditoría y quedaron
**corregidas dentro de la misma serie** (tabla §3): el fail-open del
`ReplayGuard` ante estado corrupto y el cómputo de réplicas ajenas en el
quórum. Ninguna alcanzó la categoría Crítica: no existe trayectoria
conocida hacia un sello válido falso.

**Mensaje para integradores de hardware y sistemas críticos:** la
aritmética del calendario es O(1), determinista y sin punto flotante; los
límites precisos por plataforma están contractuados en el Apéndice A.5
de la spec y blindados con `GERO_ERANGE` limpio en C11. La criptografía
activa exige verificación híbrida todo-o-nada con `event_hash` obligatorio
y estado anti-replay persistente fail-closed.

## 2. Matriz de hallazgos

| # | Severidad | Hallazgo | Estado |
|---|---|---|---|
| A-1 | Alto | `toGerarion` (JS) entra en bucle no terminante con `day_index` ≥ 2⁵³: la imprecisión de `Number` rompe la convergencia de la corrección anual (DoS de pestaña con entrada hostil) | **Corregido**: guard `Number.isSafeInteger` + `GERO_EINVAL`; modelo por dominios en Apéndice A.5 |
| A-2 | Alto | `ReplayGuard` con archivo de estado corrupto/truncado reanudaba como historial vacío (fail-open): reinicio silencioso de `seq`, replay y rollback habilitados | **Corregido**: mecanismo `_poisoned` fail-closed; estado corrupto rechaza todo hasta intervención del operador |
| A-3 | Medio | El quórum del notario computaba identidades NO autorizadas que llegaran con publicaciones bien formadas (el binding nombre→clave solo existía como política externa sin soporte en el verificador) | **Corregido**: `known_replicas` opcional en `quorum`/`verify_day`/`verify_bundle`; identidades ajenas excluidas y reportadas en `unknown_replicas` |
| A-4 | Medio | Orden de validación divergente C vs Python en marcas DOBLEMENTE inválidas (sintaxis de hora malformada + Tempalum imposible): C respondía `GERO_ETEMPALUM` y Python/JS `GERO_EINVAL` (o viceversa con hora fuera de rango) | **Corregido**: precedencia normada sintaxis → calendario → semana → rangos, idéntica en las tres implementaciones; forzada por el corpus de mutaciones |
| A-5 | Medio | `normalize` de JS colapsaba espacios múltiples (`\s+` → `-`) mientras la referencia Python los procesa por carácter: marcas con dobles espacio divergían (JS aceptaba, Python/C rechazaban) | **Corregido**: reemplazo por carácter en JS; C añade recorte de extremos espejo de `raw.strip()` |
| A-6 | Bajo | Sin blindaje exhaustivo de bordes int64 en C: trayectorias teóricas de *signed integer overflow* (UB) para años/días extremos | **Corregido**: macros `GUS_MAX_*` en `gus.h`, guards `GUS_ERANGE` en `from/to_gerarion`, `instant_from_parts`, `gregorian_from_day_index` y `day_index_from_gregorian`; verificado con 10⁶ roundtrips bajo UBSan |
| A-7 | Informativo | `detect_leaks` de ASan no está soportado en macOS; la verificación de 0 fugas debe ejecutarse en Linux CI (`ASAN_OPTIONS=detect_leaks=1`) | Documentado en `impl-c/Makefile` y §3 de este informe |
| A-8 | Informativo | La correspondencia `kid`↔clave pública es binding del trust root del despliegue: un sobre re-firmado por otra clave es criptográficamente válido y solo el trust root lo delata | Documentado (test `test_c_kid_cruzado...`); sin cambio de código: el binding es del despliegue por diseño |

No se detectaron hallazgos Críticos. La firma híbrida, la
canonicalización JCS, la protección de dominio (GST-V2 prefix), el
`event_hash` obligatorio y la aritmética calendárica congelada pasaron
todos los ataques sin necesidad de corrección.

## 3. Evidencia reproducible

### 3.1 Fuzzing diferencial masivo (1.000.000 de casos)

```bash
make -C impl-c gus-cli                       # correductor C
python3 tools/fuzz_diff.py --cases 1000000   # semilla fija: 20310101
```

Resultado real (49 s, 41,5 s de CPU):

```
digest python=070913bc0ed2e168 js=ef00051b4b126a1b c=2bd86c2da8e3ed10
OK estres: 1000000 casos, 0 divergencias bajo las politicas por op
```

Corpus: bloques deterministas obligatorios (transiciones de Gran Tempalum
−29/−23/−17/−12/−6/−1/0/5/11/2034; 12000AY, 999999DY/AY profundos;
offsets `TCJ+0/-2:20/+5:45/-12:00/+14:00`; fracciones `nanos`
0/1/999.999.999; formato extendido y compacto) más distribución aleatoria
con mutaciones de un byte y grupos de basura malformada. Política por op:
igualdad triple (común), Python↔C exacto con JS fuera de su dominio
(`tgs`/`fgs`/`grs`), y `GERO_ERANGE` exacto en C para los límites
(`tgq`/`fgq`/`grq`/`inq`). Escalas intermedias usadas durante la
auditoría: 3.000 (bisección de las 45 divergencias A-4/A-5), 20.000,
100.000 (39), 200.000 (72), 300.000 (0) y 1.000.000 (0).

### 3.2 Auditoría de memoria y UB en C11 (ASan + UBSan)

```bash
make -C impl-c audit      # -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic
                          # -fsanitize=address,undefined -fno-sanitize-recover=all
```

Resultado real:

```
CONFORME (núcleo GUS en C): 10 categorías, 0 fallos
audit límites: bordes int64 con GERO_ERANGE exacto
audit roundtrips: 1000000 conversiones, 0 fallos
audit parser fuzz: 400000 entradas, 0 fallos de memoria/UB
AUDIT OK: 6524458 comprobaciones, 0 errores, 0 fugas, 0 UB
```

El harness (`impl-c/audit_stress.c`) ejecuta bajo sanitizadores: (1) las
10 categorías de conformancia normativa con los vectores oficiales; (2) un
millón de conversiones ida y vuelta muestreadas hasta el borde exacto de
`GUS_MAX_YEAR_SAFE` e instantes en ±`GUS_MAX_INSTANT_DAYS_SAFE`; (3)
400.000 entradas de parser en buffers acotados con terminador en el borde
(ruido binario con bytes no ASCII, mutaciones truncadas, años de 7-20
dígitos, offsets y fracciones hostiles). Compilación con `-Werror`: 0
advertencias. Corrida adicional de MSan (`-fsanitize=memory`) no
disponible: Apple Clang no la implementa; pendiente de Linux CI si se
añade clang instrumentado.

### 3.3 Pruebas adversariales (`tests/test_adversarial_security.py`)

```bash
python -m pytest tests/test_adversarial_security.py -v
```

18 ataques, todos rechazados: claves duplicadas/orden UTF-16/subnormales
en JCS; eliminación y degradación de la rama ML-DSA; byte alterado en
`event_hash`/`nanos`; firma reutilizada fuera de dominio; ráfaga de
replay; rollback tras reinicio; estado corrupto fail-closed; nodo
duplicado y nodo intruso en quórum 2-de-3 y 3-de-4. Los dos hallazgos
corregidos (A-2, A-3) nacieron como fallos de esta suite.

### 3.4 Batería completa de la versión auditada

| Grupo | Resultado |
|---|---:|
| `pytest tests/` (`[dev,slh,pqc]`) | 244 passed, 1 skipped |
| `web/tests.mjs` | 36/36 |
| `web/calendars.test.mjs` | 42/42 |
| `tests/atlas.test.mjs` | 40/40 |
| `make -C impl-c conformance` | 10/10 |
| `make -C impl-c audit` (ASan+UBSan) | 0 errores, 0 UB, 0 warnings |
| `tools/fuzz_diff.py --cases 1000000` | 1.000.000, 0 divergencias |
| `e2e_web_test.py` | 53/53 |
| `reuse lint` | REUSE 3.3, 0 errores |

## 4. Límites de la auditoría

Esta auditoría es estática + dinámica sobre las implementaciones de
referencia de este repositorio, en un host macOS (arm64). No es una
certificación: no cubre la cadena de suministro de las bibliotecas de
terceros (`cryptography`), ni hardware, ni temporización (side channels),
ni un muestreo exhaustivo de todo el espacio de entradas de 64 bits. Las
garantías formales del calendario (derivación cerrada) están en el
Apéndice A de la spec; los límites operativos, en su tabla A.5.
