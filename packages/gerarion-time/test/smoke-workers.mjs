// SPDX-License-Identifier: Apache-2.0
// Entrada de smoke para Cloudflare Workers (workerd) SIN nodejs_compat:
// el handler verifica el recibo GST v2 real con el paquete empaquetado.
import { runSmoke } from "./smoke-runtime.mjs";

export default {
  async fetch() {
    try {
      const result = await runSmoke();
      return new Response(JSON.stringify({ ok: true, ...result }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    } catch (err) {
      return new Response(
        JSON.stringify({ ok: false, error: String(err && err.message ? err.message : err) }),
        { status: 500, headers: { "content-type": "application/json" } },
      );
    }
  },
};
