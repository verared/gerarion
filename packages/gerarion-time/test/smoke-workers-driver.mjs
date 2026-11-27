// SPDX-License-Identifier: Apache-2.0
// Driver de smoke para Cloudflare Workers vía miniflare, SIN nodejs_compat.
// 1) empaqueta el worker con esbuild (resuelve node_modules en build time,
//    igual que wrangler); 2) lo ejecuta en workerd vía miniflare sin
//    compatibilityFlags y verifica el recibo GST v2 real.
import { build } from "esbuild";
import { Miniflare } from "miniflare";
import { mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SMOKE = path.join(HERE, "..", ".smoke");

mkdirSync(SMOKE, { recursive: true });
const bundle = path.join(SMOKE, "worker.bundle.mjs");
await build({
  entryPoints: [path.join(HERE, "smoke-workers.mjs")],
  bundle: true,
  format: "esm",
  platform: "neutral",
  outfile: bundle,
  logLevel: "silent",
});

const mf = new Miniflare({
  modules: true,
  modulesRoot: SMOKE,
  scriptPath: bundle,
  // Intencionadamente SIN compatibilityFlags: sin nodejs_compat.
});

try {
  const res = await mf.dispatchFetch("http://localhost/verify");
  const body = await res.json();
  if (res.status !== 200 || !body.ok || body.verdict !== "sealed") {
    console.error("smoke Workers FALLÓ:", body);
    process.exitCode = 1;
  } else {
    console.log(
      `smoke Workers OK (workerd sin nodejs_compat): ${body.verdict} — ${body.reason}`,
    );
  }
} finally {
  await mf.dispose();
  rmSync(SMOKE, { recursive: true, force: true });
}
