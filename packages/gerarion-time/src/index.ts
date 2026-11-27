// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
/**
 * @verared/gerarion-time — núcleo temporal determinista de Gerarion
 * y verificador offline de recibos GST v2.
 *
 * Superficie:
 * - Núcleo GUS/TCJ re-exportado de forma tipada (fuente única de verdad:
 *   `web/engine/core.mjs`, embebido verbatim en el build).
 * - Verificador offline GST v2 (`verifyGstV2Offline`): híbrido
 *   Ed25519 + ML-DSA sobre bytes canónicos RFC 8785 (JCS).
 * - Contrato `AnchorProvider` para v0.2 (honestidad temporal): la
 *   verificación offline de un recibo sin ancla externa verificada
 *   devuelve `sealed`, JAMÁS `anchored`.
 */

export * from "./core.mjs";
export * from "./gst-v2.js";
export * from "./anchor.js";
