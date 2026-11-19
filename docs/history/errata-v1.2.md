# Errata GUS — diferencias entre corpus v1.2 y la especificación v2.0

Verificadas ejecutando el algoritmo canónico del corpus (cap. 10.10) contra
los vectores normativos del cap. 11. Cada corrección se acompaña del cambio
de definición en GUS 2.0 y de su test correspondiente.

## E-01 — El vector "año nuevo 2031 el 21 de marzo de 2026" es matemáticamente inconsistente

El corpus declara simultáneamente:

- `2026-03-21 → 2031DY-01-01-S` (inicio del año 2031)
- `2027-03-16 → 2032DY-01-01-S` (inicio del año 2032)

Entre ambos hay exactamente 360 días gregorianos, pero todo año Gerarion
tiene 364 o 371 días. Ambas afirmaciones no pueden ser ciertas a la vez.

**Resolución GUS 2.0:** el algoritmo canónico (acumulador solar + JDN de
origen) es la única fuente normativa. El año 2031 DY comienza el
**17 de marzo de 2026** (Soludyia) — y esta fecha gregoriana es una
**equivalencia derivada**, no un ancla: el sistema no está anclado al
calendario gregoriano (ver E-07). El "21 de marzo" queda como descripción
aproximada del equinoccio: el inicio de año oscila dentro de la cota de
drift (|Δ| < 7 días), que es exactamente lo que el trigésimo primer archivo
del corpus (paper del drift acotado) ya demostraba sin pronunciar esta
consecuencia interna.

Tests: `test_errata_new_year_2031`, `test_every_year_starts_on_soludyia`.

## E-02 — El vector "Yeshuvid 2031 = 19 abril 2026" hereda E-01

Con inicio de año 2026-03-17, 30 Keuphero de 2031 cae el **15 de abril de
2026** (no el 19). La propiedad estructural se conserva: sigue siendo
Loondyia, como exigía el cap. 11.

Test: `test_normative_vectors[greg4]`.

## E-03 — "Próximos Gran Tempalum: 2034, 2039, 2045" contradice el propio patrón

El patrón normativo del mismo capítulo (`5, 11, 16, 22, 28, 33, 39, 45...`)
empieza la lista de años Gran Tempalum en DY: ... 2034, **2040**, 2045... El "2039" es un
error de transcripción.

**Resolución GUS 2.0:** el patrón de la recurrencia es la única fuente
normativa (test `test_gran_tempalum_pattern_matches_spec`).

## E-04 — "Tempalum es el mes 00, el inicio de todo" vs. "el mes 00 actúa como cierre del año"

Normativa y axiomáticamente no pueden coexistir: los vectores del cap. 11
muestran el Tempalum **después** del mes 12 (12-30 → 00-01 → año nuevo), y toda
la aritmética de días sagrados (dos días Sabatyeh en Gran Tempalum, semanas
exactas) solo cierra con Tempalum al final.

**Resolución GUS 2.0:** el Tempalum es el **cierre** del año Gerarion
(mes 00, últimos 4/11 días). La redacción "inicio de todo" del cap. 1 es
retórica no normativa y no se reproduce.

Tests: vectores `2027-03-12 → 2031DY-00-01-A`, `test_two_saturdays_in_gran_tempalum`.

## E-05 — El código Python del cap. 10.10 no es ejecutable

53 líneas con comillas tipográficas (`"` → `"`, `'` → `'`), flechas y
divisiones corrompidas por copy-paste; acumulador en punto flotante (riesgo
de error acumulativo en horizontes largos y dependencia del orden de sumas).

**Resolución GUS 2.0:** implementación de referencia en aritmética entera
exacta (microdías), ejecutable y cubierta por la suite completa.
Test: `test_drift_bound_sawtooth` (cota de drift en 500 años).

## E-06 — Día de Tempalum en formato canónico y la letra `B` de Sabatyeh

El corpus usa la letra `B` para Sabatyeh en el código del cap. 10.10 y el
formato canónico del cap. 12 valida ese alfabeto, pero el cap. 4 no la
documenta de forma consistente. GUS 2.0 fija el alfabeto normativo:
`S L M A T V B`.

## E-07 — El tiempo Gerarion no está anclado al calendario gregoriano

Aclaración estructural (formulada como errata porque la redacción de E-01
podía sugerir lo contrario): el Gerarion **ocupa su propio tiempo**. Su
origen es **1 Keuphero del año 0 DY, definido por su JDN: día 0 =
JDN 1.719.313, Soludyia por definición.** (Por conversión, ese JDN
equivale a 21 de marzo del año astronómico -5 = 6 a.C. gregoriano
proléptico; la equivalencia es derivada, no definitoria.) Desde ahí el
sistema es un conteo continuo propio: JDN se usa únicamente como contador
absoluto de días (entero, sin mes ni Jahr civiles), nunca como calendario
gregoriano.

Consecuencias:

- **Año 0 ≠ año 1.** El empieza del conteo es el año 0 (donde está el ancla
  Yeshuvid del corpus); el año 1 comienza 364 días después,
  19 de marzo de -4 (5 a.C.). Cualquier texto que diga "año 01 = 6 a.C."
  está desviado: 6 a.C. es el año 0.
- **Toda fecha gregoriana citada es derivada.** "El año 2031 DY comienza el
  17 de marzo de 2026" es el resultado de aplicar el acumulador solar sobre
  el origen — no una entrada de la norma. Sin gregoriano el sistema sigue
  funcionando íntegro (instantes, semanas, ciclos, firmas).
- **Cero dependencia práctica.** Las conversiones grego ↔ gero (F-01/F-02)
  son alias aritméticos interop. Si mañana el calendario civil cambiara,
  el tiempo Gerarion no se movería un día.

Test: `test_errata_e07_origin_independence`.

## Procedencia

El corpus original completo (corpus canónico v1.2 + working papers, con la
capa filosófica y espiritual como apéndice explícitamente no normativo) no
se publica como repositorio aparte; su documentación complementaria se
conserva en `docs/papers/`.
