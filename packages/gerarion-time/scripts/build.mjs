// SPDX-License-Identifier: Apache-2.0
/** Build de @verared/gerarion-time: tsc + embebido verbatim del núcleo. */
import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync, rmSync, existsSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const pkgRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(pkgRoot, "..", "..");
const coreSrc = path.join(repoRoot, "web", "engine", "core.mjs");
const coreStage = path.join(pkgRoot, "src", "core.mjs");
const dist = path.join(pkgRoot, "dist");

if (!existsSync(coreSrc)) {
  console.error(`[build] núcleo no encontrado: ${coreSrc}`);
  process.exit(1);
}

// 1. Embebe el núcleo verbatim en src/ (fuente única: web/engine/core.mjs).
copyFileSync(coreSrc, coreStage);

// 2. Compila TS (NodeNext, estricto).
execFileSync(path.join(pkgRoot, "node_modules", ".bin", "tsc"), {
  cwd: pkgRoot,
  stdio: "inherit",
});

// 3. Copia el núcleo embebido al dist (index.js hace `export * from "./core.mjs"`).
copyFileSync(coreStage, path.join(dist, "core.mjs"));
copyFileSync(path.join(pkgRoot, "src", "core.d.mts"), path.join(dist, "core.d.mts"));

// 4. Chequeo estático: 0 imports node:* en src/ y dist/.
try {
  execFileSync("node", [path.join(pkgRoot, "scripts", "check-no-node-imports.mjs")], {
    cwd: pkgRoot,
    stdio: "inherit",
  });
} catch {
  process.exit(1);
}

console.log("[build] @verared/gerarion-time OK (dist/ + núcleo embebido verbatim)");
