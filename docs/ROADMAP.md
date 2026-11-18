# Hoja de ruta (sin fechas prometidas)

## BETA (esta versión, 2.5.0b1)

- Kernel calendárico estable con vectors normativos (22) × 3 implementaciones
  + fuzz diferencial y vector negativo compartido.
- Web: traductor multicalendario con ida y vuelta densa 1900–2100.
- Avisos visibles: firma hash-only, notario y perfiles NO aptos para
  producción (ver README y SECURITY.md).
- CI: matriz Python 3.9–3.13, e2e Playwright, CodeQL, dependbot, pip-audit.

## RC (cada ítem es condición, no deseo)

1. **Auditoría criptográfica externa** de notario, trust root y perfiles de
   anclaje (la suite propia en verde no sustituye una revisión).
2. **Implementación independiente de un tercero** que consuma `vectors/`
   y contraste resultados (ver docs/CONFORMANCE.md).
3. **TODO-001/D-001 resuelto**: medianoche UTC mantiene el kernel;
   la decisión sobre escala alternativa (propuesta TAI) queda como DECISIÓN
   DEL AUTOR (docs/decisions/D-001).
4. **TODO-004 resuelto**: forma canónica de offsets con minutos o cierre
   formal del rango.
5. **Un caso de uso real** documentado de extremo a extremo (creación,
   anclaje, verificación y rotación de claves en un despliegue que no sea
   de prueba).
6. **Plan de migración post-cuántica** cerrado (threat-model.md §G6):
   firma dual/híbrida Clásica+ML-DSA verificado por un tercero, con política
   de re-firma y preservación de cadena.

## Notas exploratorias (no condiciones)

- **Verificación astronómica TSLR con quorum 3-de-4** (propuesta externa,
  "Cap 13.4.1 v1.2" del documento canónico de GeroTime Foundation): capa de
  evidencia de alto nivel que combinaría posición solar (DE440/ephemeris_hash),
  GPS firmado y quorum geográfico de nodos. Exigiría infraestructura nueva
  (nodos, efemérides versionadas, política de tolerancia) y una auditoría
  propia; NO es condición de RC ni de 1.0 y no altera el kernel ni el formato.
  Los puntos de extensión están descritos en docs/papers/lib-c-referencia.md.

## 1.0 (condiciones)

- Todas las condiciones de RC cerradas.
- Sin hallazgos reproducidos abiertos de clase S*.
- Una revisión independiente firmada (informe o advisory cerrado).
- Vector set congelado (sin cambios pendientes) y política de versionado
  (semver para el kernel JS; PEP 440 para Python) publicado.
