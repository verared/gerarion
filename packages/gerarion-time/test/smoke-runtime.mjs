// SPDX-License-Identifier: Apache-2.0
// Smoke multi-runtime del paquete: verifica un recibo GST v2 real con el
// núcleo embebido + verificador híbrido. 100% Web-API puro (sin node:*),
// así que corre igual en Node, Deno y Cloudflare Workers (workerd).
import { verifyGstV2Offline, quickVerify } from "../dist/index.js";
import { envelope, eventHash } from "./fixtures/gst-v2-receipt.mjs";

export async function runSmoke() {
  if (!quickVerify("2031DY-03-08-T-09:30:00-SC-TCJ+0")) {
    throw new Error("núcleo embebido: quickVerify falló");
  }
  const result = await verifyGstV2Offline(envelope, eventHash);
  if (result.verdict !== "sealed" || !result.sealed) {
    throw new Error(`verificación GST v2 inesperada: ${result.reason}`);
  }
  return result;
}
