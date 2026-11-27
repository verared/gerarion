# @verared/gerarion-time

Núcleo temporal determinista de Gerarion (GUS/TCJ) y verificador offline de
recibos GST v2, empaquetado para npm. **100% Web-API puro**: cero imports
`node:*` en `src/` y `dist/` — ejecuta en Node >= 20.19 (verificado en CI con
Node 24; `@noble/post-quantum@0.7.1` requiere Node >= 20.19), Deno y
Cloudflare Workers (workerd sin `nodejs_compat`).

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

### Verificador offline de recibos GST v2 (fail-closed)

```js
import { verifyGstV2Offline } from "@verared/gerarion-time";

const result = await verifyGstV2Offline(envelope, "sha256:<digest-del-artefacto>", {
  trustedIssuers: {
    "emisor-autorizado": {
      ed25519: "<hex pub Ed25519 autorizada>",
      mldsa: "<hex pub ML-DSA autorizada>",
    },
  },
});
// { verdict: "sealed" | "invalid" | "unsupported", sealed, code, reason }
```

- `sealed`: **política explícita de emisores autorizados** con llaves que
  coinciden exactamente con las del sobre (las llaves embebidas solas NO
  bastan; sin `trustedIssuers` → `invalid`/`MISSING_ISSUER_POLICY`),
  coherencia temporal interna ts/ins/nanos verificada con el núcleo GUS,
  `event_hash` exacto, tamaño dentro del límite (bytes UTF-8 reales,
  64 KiB por defecto) y doble firma híbrida Ed25519 + ML-DSA válida sobre
  `GUS3-GST-V2\x00 + JCS(payload)`.
- `invalid`: firma, digest, JCS, llave, escala, versión, emisor no
  autorizado (`UNAUTHORIZED_ISSUER` / `KEY_NOT_AUTHORIZED`), incoherencia
  temporal (`TEMPORAL_FIELD_MISMATCH`) o tamaño excedido
  (`ENVELOPE_TOO_LARGE`) inválidos.
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
