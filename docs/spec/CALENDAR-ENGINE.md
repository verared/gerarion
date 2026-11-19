<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- SPDX-FileCopyrightText: 2026 verared contributors -->

# Motor multi-calendario (GUTI-1)

Estado: parte de GUS v3.1.0. Este documento afecta a la capa de
`CalendarDate` (fechas proyectadas); no modifica la aritmética congelada
del núcleo (`gus-normative-003.json`, `ORIGIN_JDN = 1719313`,
`TCJ = TAI + 8.400 s`).

## Separación de las tres primitivas

| Primitiva | Contenido | Convivencia |
|---|---|---|
| `Instant` | seg. ENTEROS int64 + nanos `0..999.999.999` | fuente de verdad física |
| `CalendarDate` | campos del sistema (1..5) + `leap` | proyección de un `day_index` |
| `LocalTime` | presentación civil con desfase `TCJ±O` | presentación; sin efecto |

El pivote único de todas las conversiones es el `day_index` GUS
(`JDN − 1719313`): ninguna conversión A→B es directa; siempre
`A → day_index → B` con redondeo truncado en ambos pasos. Un
`from_day_index(to_day_index(x))` es la identidad exacta para todos los
sistemas y todo el rango compartido.

## Los diez sistemas

| id | Sistema | Tipo | Época (JDN) | Dependencia astronómica |
|---|---|---|---|---|
| `gus` | Gerarion `DY`/`AY` | aritmético | 1719313 | ninguna |
| `greg` | Gregoriano proléptico | aritmético | `day_index(0001-01-01)` | ninguna |
| `julian` | Juliano proléptico | aritmético | 1721424 | ninguna |
| `egyptian` | Egipcio vago (Nabonassar) | solar fijo | 1448638 | ninguna |
| `ethiopic` | Etíope (Amete Mihrêt) | aritmético | 1724221 | ninguna |
| `bahai` | Badí' tabular (Naw-Rúz 21-03) | solar tabular | 2394647 | ninguna |
| `maya` | Cuenta Larga (GMT 584283) | aritmético | 584283 | ninguna |
| `islamic` | Islámico civil tabular | lunar tabular | 1948440 | ninguna en ejecución |
| `hebrew` | Hebreo aritmético (molad + dehiyot) | lunisolar | 347998 | ninguna en ejecución |
| `chinese` | Chino lunisolar (Shixian) | lunisolar astronómico | 2319912 (Año Nuevo 1645) | tabla precalculada SHUO/ZHONGQI |

Todos los sistemas exponen metadatos estructurados en las tres
implementaciones (`id`, `name`, `version`, `type`, `epoch_jdn`,
`supported_range`, `astronomical_dependency`, `reference_meridian`,
`known_limitations`, `field_names`).

### Decisiones por sistema

- **Hebreo**: molad BaHaRaD (2d 5h 204p) con los cuatro dehiyot en
  **cascada elif estricta** (zaken → Lo ADU → BeTUTaKaPaT → GaTaRaD),
  meses en **numeración rabínica** (1 = Nisán, 7 = Tishri, 12/13 =
  Adar I/II). La numeración civil (Tishri primero) es un detalle interno.
- **Chino**: sin punto flotante en ejecución. La tabla generada
  (`tools/generate_china_table.py`, efemérides Meeus truncadas, meridiano
  de Pekín UTC+8/120°E) da lunas nuevas (*shuo*) y término solar
  (*zhongqi*). El ancla del año lunar es el último Dongzhi; el mes
  intercalar (*runyue*) es la primera lunación sin zhongqi entre dos
  meses 11 con 13 lunaciones. Rango validado **estricto 1645–2650 d.C.**:
  fuera de rango se devuelve `GERO_EUNSUPPORTED`, nunca extrapolación.
- **Islámico**: ciclo tabular de 30 años con bisiestos
  `{2,5,7,10,13,16,18,21,24,26,29}`; el día 30 de Dhu al-Hiyya existe
  solo en años bisiestos tabulares (p. ej. 1445 AE sí lo es, 1446 no).
  La observación lunar local puede diferir un día; la ficha lo declara.

## Cotas y dominios (paridad demostrada)

La paridad bit a bit Python ↔ C11 ↔ JavaScript se demuestra contra el set
CC0 `vectors/guti-calendars-001.json` (63.545 vectores, 450 cruces
palíndromos A→GUS→B→GUS→A, 30 inválidos, 5 no soportados, 2 `erange`),
autovalidado por el generador determinista (`tools/generate_guti_vectors.py`,
semilla 584283, sin reloj).

### Envolvente operativa por plataforma

| Plataforma | Aritmética interna | Dominio exacto del `day_index` | Efecto visible |
|---|---|---|---|
| C11 (`libgerarion`) | `int64_t` con guardias de producto | \|di\| ≤ 2²⁵·10¹⁵ aprox. (`GUS_MAX_DAY_INDEX_SAFE`) | `GUS_ERANGE` |
| Python (`gerarion.calendars`) | entero arbitrario | sin límite práctico; horizonte hebreo AM 9·10¹¹ | `GERO_ERANGE` solo por horizonte de sistema |
| JavaScript (`web/guti.mjs`) | BigInt intermedio, cierre en `Number` | \|di\| ≤ 2⁵³−1 (`Number.isSafeInteger`); el set compartido usa \|di\| ≤ 2⁴⁸−1, dominio común de las tres | `GERO_ERANGE` |

El límite común del set compartido (±2⁴⁸−1 días ≈ ±7,7·10¹¹ años) evita
la pérdida de precisión en el interior del núcleo web
(`jdnToGregorian` multiplica internamente por 4; por encima de ~2⁵¹
los dígitos bajos no son representables con `Number`). Los extremos de
plataforma se prueban por suite nativa: límites `int64_t` en C
(`make -C impl-c audit`) y rechazos `isSafeInteger` en JS.

## Verificación hebrea por definición

El estimador de año del molad reemplaza al escaneo lineal (que acumulaba
un error de ~(años/48) días y era O(años)). La corrección es un lazo
acotado (≤ 8 iteraciones); además, cada fecha hebreo devuelta satisface
la definición misma de pertenencia de año:

```
RH(y) ≤ jdn < RH(y+1)      (RH = JDN de Tishri 1, con dehiyot)
to_day_index(year, month, day) == di        (ida y vuelta exacta)
```

comprobada sobre 6.805 muestras hasta ±3,3·10¹⁴ días sin un solo fallo.

## Cómo ejecutar

| Suite | Comando | Resultado |
|---|---|---|
| Python (con red bloqueada) | `python3 -m pytest tests/test_guti_m0_sandbox.py` | 13 pruebas |
| C11 conformance | `make -C impl-c guti-conformance` | 63.850/63.850 |
| JS runner | `node web/guti_vectors.mjs` | 127.204/127.204 |
| Regenerar vectores | `PYTHONPATH=src python3 tools/generate_guti_vectors.py` | determinista |

## Verificación astronómica independiente y tolerancia documentada (adenda v3.1.1)

La suite `tests/test_guti_calendars.py` contrasta el calendario chino del
motor contra fechas de referencia publicadas (Observatorio de la Montaña
Púrpura / listas lunisolares estándar de la reforma Shixian) en cuatro
categorías:

1. **Años Nuevos chinos (1900–2100 + época 1645)** — coincidencia EXACTA.
2. **Primeros días de meses intercalares (runyue)**: 闰五 1952, 闰六 1979,
   闰二 2004, 闰五 2009, 闰六 2017, 闰四 2020, 闰二 2023, 闰六 2025 — exactos.
3. **Bordes de lunación** (vísperas de Año Nuevo, días 29/30 de
   diciembre lunar) — exactos.
4. **Noches límite** (luna nueva a pocos minutos de la medianoche UTC+8:
   1700, 1751, 1851, 2050): el motor puede diferir en **1 día** de las
   listas publicadas de la época; el test FIJA la lectura exacta del
   motor como regresión (el motor es determinista y nunca desplaza una
   fecha en silencio) y la divergencia queda registrada aquí.

Margen de tolerancia del motor: **±2 minutos** de las efemérides completas
(truncamiento polinómico de `tools/generate_china_table.py`), más la
diferencia con el cálculo histórico Shixian en las noches límite de la
categoría 4 (≤ 1 día, sólo en lunaciones cuyo instante de luna nueva cae
a menos de ~30 minutos de las 0:00 UTC+8). Fuera de esos casos, la
conversión es exacta y reproducible bit a bit en C11, Python y JS.
