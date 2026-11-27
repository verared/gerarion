// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
/**
 * Contrato `AnchorProvider` para v0.2 (honestidad temporal).
 *
 * Estados explícitamente separados — un recibo offline NUNCA es `anchored`:
 * - `sealed`:    política EXPLÍCITA de emisores autorizados (`trustedIssuers`)
 *                con llaves Ed25519 + ML-DSA que coinciden exactamente con
 *                las del sobre, coherencia temporal interna ts/ins/nanos,
 *                `event_hash` exacto y doble firma híbrida válida sobre los
 *                bytes canónicos JCS. El tiempo NO está corroborado
 *                externamente. (Ver `verifyGstV2Offline` en `gst-v2.ts`: mismo
 *                contrato, fail-closed si falta la política de emisores.)
 * - `anchored`:  `sealed` + cota superior de existencia verificada bajo
 *                raíz de testigo y tabla TCJ fijadas (requiere ancla
 *                externa verificada; fuera del alcance de 0.1.0-alpha.1).
 * - `invalid`:   firma, digest, JCS, llave, escala o versión inválidos.
 * - `unsupported`: algoritmo/versión/perfil no soportado por este backend.
 * - `unavailable`: fallo operativo/transporte al emitir o consultar una
 *                fuente externa (no confundir con `invalid`).
 */

export type AnchorVerdict =
  | "sealed"
  | "anchored"
  | "invalid"
  | "unsupported"
  | "unavailable";

export interface Receipt {
  /** Recibo GST v2 (sobre firmado, sin el ancla). */
  gst: Uint8Array;
  /** Ancla temporal externa opcional (testigo firmado, p. ej. GTS). */
  anchor?: Uint8Array;
}

export interface AnchorIssueArgs {
  /** Digest del artefacto a anclar (forma `sha256:<hex>`). */
  eventHash: string;
  /** Cooperación con cancelación cooperativa del emisor externo. */
  signal?: AbortSignal;
}

export interface AnchorVerifyArgs {
  eventHash: string;
  /** Instante de evaluación (segundos Unix) para vigencia del ancla. */
  evaluationTimeUnixSeconds: number;
  /** Política de anclaje bajo la que se juzga el testigo. */
  trustPolicyId: string;
}

/**
 * Proveedor de anclas temporales (v0.2). La admisión anti-replay es una
 * operación ATÓMICA responsabilidad del host: este contrato es puro y sin
 * estado mutable oculto, de modo que la verificación es repetible.
 */
export interface AnchorProvider {
  issue(args: AnchorIssueArgs): Promise<Uint8Array>;
  verify(receipt: Receipt, args: AnchorVerifyArgs): Promise<AnchorVerdict>;
}
