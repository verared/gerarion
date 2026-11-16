# Pendientes abiertos (lista TODO normativa)

Esta lista es la cola formal de problemas abiertos que la especificación
declara **no especificados en 2.0**. Cada ítem apunta a la sección de la
spec que lo marca. Un ítem se cierra solo con: (1) decisión registrada en
la spec (ES+EN), (2) vectores normativos actualizados si toca al kernel y
(3) entrada en el CHANGELOG.

## TODO-001 — Frontera exacta del día GUS con UTC/TAI (spec §9)

Estado: **BORRADOR DE DECISIÓN** — la propuesta D-001 vive en
`docs/decisions/D-001-frontera-utc-tai.md` (ES espejo) /
`docs/en/decisions/D-001-utc-tai-boundary.md` (EN normativo):
instante sobre TAI, día a medianoche TAI, adaptador UTC con tabla
explícita, TAI pre-1958 como convención declarada. Pasa a RESUELTO solo
tras la ventana de revisión de 90 días (GOVERNANCE §3.1), con nueva
versión del vector set.

Demanda de decisión normativa entre al menos tres opciones:

1. **Medianoche UTC** (comportamiento de facto del reloj de referencia web
   y, por extensión, de cualquier consumidor que re-etiquete una hora UTC).
   Ventaja: mapeo trivial con la hora civil actual. Defecto: el segundo
   intercalar hace que algunos "días UTC" fueran 1 s más largos; el instante
   GUS congelaría esa diferencia como una deriva acumulada de 37 s (y
   creciendo), no documentada como tal frente a TAI.
2. **Medianoche TAI** (día GUS = TAI transcurrido real desde el origen).
   Ventaja: escala física pura, coherente con "análogo a TAI". Defecto: la
   lectura civil exige tabla TAI−UTC, que es otra dependencia mutable.
3. **Época TAI declarada sin tabla** (status quo documentado en la spec
   2.0): instante = re-etiquetado directo del reloj UTC de pared; la
   divergencia con TAI fino se declara explícitamente.

Impacto normativo: cualquier decisión de las opciones 1↔2 cambia el valor
numérico de los instantes (offset constante de 37 s en 2026) → toca el
vector set (`instant`) y exige Looking Period de 90 días según
GOVERNANCE.md §3.1. Por eso la 2.0 lo declara **no especificado** y la
implementación de referencia documenta lo que hace (medianoche UTC,
sin tabla), sin convertirlo en regla normativa todavía.

Además, pendiente de decisión en el mismo paquete: mapeo de la escala para
fechas anteriores a la introducción de TAI (1958) y al inicio de la tabla
TAI−UTC (1972).

## TODO-002 — Wire-format UDP del protocolo Roughtime (perfil roughtime-001)

Estado: **ABIERTO**.

El perfil GUS-Roughtime (`docs/en/profiles/gus-roughtime-profile.md` /
`docs/profiles/gus-roughtime-perfil.md`) define y verifica el RECEIPT:
la unidad firmada por un testigo (midpoint, radius, nonce, Ed25519),
offline y sin dependencias. Queda sin especificar el TRANSPORTE: el
wire-format UDP del draft Roughtime (negociación de shards, árbol de
noances, encadenamiento multi-testigo íntegro) y el cliente de red que
produce receipts reales contra testigos públicos vivos.

No se definen como parte de este perfil porque exige acceso a la red y
decidir sobre un protocolo en borrador; un cliente UDP mal hecho podría
firmar receipts que esta capa verificaría sin poder jurar proveniencia
real. Cierra con: cliente de referencia, vectores de receipts capturados
de testigos reales, y regla de composición multi-testigo.


## TODO-003 — Nombres N0 dentro del formato canónico (spec §6.1)

Estado: **CERRADO** (2026-11-16).

Decisión del autor: **los nombres del formato (meses, días Nuvid, días del
Tempalum, letras S L M A T V B, eras DY/AY) son los canónicos; los niveles
de nombre N0–N4 son solo presentación; no existen nombres N0 numéricos
canónicos en la spec 2.0.** El N0 "numérico" es simplemente la numeración
válida del formato canónico (mes `01`–`12`/`00`, día 1–30). No se define
ninguna representación serializable adicional.
