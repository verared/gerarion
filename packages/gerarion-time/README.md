# @verared/gerarion-time

Núcleo temporal determinista de Gerarion (GUS/TCJ) y verificador offline de
recibos GST v2, empaquetado para npm. **100% Web-API puro**: cero imports
`node:*` en `src/` y `dist/` — ejecuta en Node 18+, Deno, Bun y Cloudflare
Workers.

**Estado: `0.1.0-alpha.1` (experimental).** No auditar de forma independiente;
no usar en producción sin revisar los Honest Limits.

## Instalación

```bash
npm install @verared/gerarion-time
```

## Uso

### Núcleo determinista (calendario GUS/TCJ)

El paquete re-exporta de forma tipada el núcleo determinista de
`web/engine/core.mjs` (fuente única de verdad, embebido verbatim en el
build):

```js
import { parse, quickVerify, instantFromParts, canonicalOf } from "@verared/gerarion-time";

quickVerify("2031DY-03-08-T-09:30:00-SC-TCJ+0"); // true
const d = parse("2031DY-03-08-T-09:30:00-SC-TCJ+0");
canonicalOf(d); // forma canónica
```

### Verificador offline de recibos GST v2

```js
import { verifyGstV2Offline } from "@verared/gerarion-time";

const result = await verifyGstV2Offline(envelope, "sha256:<digest-del-artefacto>");
// { verdict: "sealed" | "invalid" | "unsupported", sealed: boolean, reason: string }
```

- `sealed`: firmas híbridas Ed25519 + ML-DSA válidas sobre los mismos bytes
  canónicos (RFC 8785 JCS), `event_hash` exacto y descriptor híbrido
  completo sin downgrades.
- `invalid`: firma, digest, JCS, llave, escala o versión inválidos.
- `unsupported`: backend ML-DSA ausente (`ml_dsa_unavailable`) o
  algoritmo/perfil no soportado.

## Honest Limits

- **Experimental**: versión `0.1.0-alpha.1`, sujeta a cambios sin aviso.
- **ML-DSA sin auditoría independiente**: la rama post-cuántica usa
  `@noble/post-quantum`, que no ha sido auditada por terceros.
- **Sin anclas externas**: `0.1.0-alpha.1` cubre verificación offline
  (`sealed`). Los testigos/anclaje GTS en red (raíz de testigo verificada,
  política de anclaje, tabla TCJ fijada) quedan para P1: un recibo sin
  ancla externa verificada JAMÁS devuelve `anchored`.
- **Admisión anti-replay atómica**: responsabilidad del host. Este contrato
  es puro y sin estado mutable oculto; la deduplicación de nonces/seq
  (p. ej. contra un `ReplayStore` transaccional) debe implementarla el
  llamador como operación atómica.
- **Límite de tamaño**: por defecto los sobres superiores a 64 KiB se
  rechazan (`ENVELOPE_TOO_LARGE`), configurable por llamada.

## Licencia

Apache-2.0. Ver `LICENSE` y `NOTICE`.
