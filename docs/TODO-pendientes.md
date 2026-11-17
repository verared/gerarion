# Pendientes abiertos (lista TODO normativa)

Esta lista es la cola formal de problemas abiertos que la especificación
declara **no especificados en 2.0**. Cada ítem apunta a la sección de la
spec que lo marca. Un ítem se cierra solo con: (1) decisión registrada en
la spec (ES+EN), (2) vectores normativos actualizados si toca al kernel y
(3) entrada en el CHANGELOG.

## TODO-001 — Frontera exacta del día GUS con UTC/TAI (spec §9)

Estado: **CERRADO** (2026-11-17) — decisión normativizada en la spec §9
(ES+EN), **sin cambio de valores** (los vectores `gus-normative-002.json`
quedan intactos y siguen siendo el criterio de conformancia):

- **Meridiano del día GUS: medianoche UTC.** El día `[n, n+1)` es el
  intervalo de segundos GUS `[n×86.400, (n+1)×86.400)`; no es medianoche
  TAI ni medianoche local. Se fija la regla de facto ya implementada y
  verificada en las tres implementaciones (Python/JS/C).
- **Pre-1958: convención proléptica declarada.** La misma aritmética
  entera se extiende hacia atrás sin pretensión de coincidir con las
  efemérides históricas UT1/TAI; la correspondencia con esas escalas es
  adaptador, no núcleo.
- **Divergencia TAI declarada:** el instante GUS difiere del TAI real en
  los segundos intercalares acumulados (37 s en 2026, congelado en los
  vectores). La propuesta D-001 (medianoche TAI con tabla) queda **viva
  como PROPUESTA** para una futura versión 2.x por el Looking Period
  (GOVERNANCE §3.1): exigiría nuevo vector set (`gus-normative-002`) y
  regeneración de sellos; no es aplicación retroactiva de la 2.0.

Registro de la revisión: el cierre no altera el kernel (los 6 ítems de
GOVERNANCE §2): salida numérica idéntica antes y después, verificada por
la suite y por el vector set vigente.

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
