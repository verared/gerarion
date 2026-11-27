// SPDX-License-Identifier: Apache-2.0
/** Chequeo estático: 0 imports `node:*` en src/ y dist/ (Web-API puro). */
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const pkgRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function walk(dir, acc = []) {
  for (const entry of readdirSync(dir)) {
    const p = path.join(dir, entry);
    if (statSync(p).isDirectory()) walk(p, acc);
    else if (/\.(m?js|ts|d\.mts)$/.test(entry)) acc.push(p);
  }
  return acc;
}

let failures = 0;
for (const sub of ["src", "dist"]) {
  const dir = path.join(pkgRoot, sub);
  if (!statSync(dir, { throwIfNoEntry: false })) continue;
  for (const file of walk(dir)) {
    const text = readFileSync(file, "utf8");
    if (/(?:from\s+|require\(\s*|import\s*\(\s*)["']node:[^"']+["']/.test(text)) {
      console.error(`[check:pure] FALLO: import node:* en ${file}`);
      failures++;
    }
  }
}

if (failures > 0) {
  console.error(`[check:pure] ${failures} fichero(s) con imports node:*`);
  process.exit(1);
}
console.log("[check:pure] OK: 0 imports node:* en src/ y dist/");
