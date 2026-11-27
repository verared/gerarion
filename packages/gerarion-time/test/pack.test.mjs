// SPDX-License-Identifier: Apache-2.0
// Smoke del tarball: npm pack + instalación limpia + consumo real.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PKG = path.resolve(HERE, "..");

test("tarball npm pack: instalación limpia y superficie completa", () => {
  const packDir = mkdtempSync(path.join(tmpdir(), "gtime-pack-"));
  const consumer = mkdtempSync(path.join(tmpdir(), "gtime-consumer-"));
  try {
    const tarball = execFileSync("npm", ["pack", "--pack-destination", packDir], {
      encoding: "utf8",
      cwd: PKG,
    })
      .trim()
      .split("\n")
      .pop();
    assert.match(tarball, /\.tgz$/);

    writeFileSync(
      path.join(consumer, "package.json"),
      JSON.stringify({ name: "gtime-consumer", type: "module" }, null, 2),
    );
    execFileSync("npm", ["install", "--no-audit", "--no-fund", path.join(packDir, tarball)], {
      cwd: consumer,
      encoding: "utf8",
    });

    // El tarball debe incluir el núcleo embebido + declaraciones TS.
    const installed = path.join(consumer, "node_modules", "@verared", "gerarion-time");
    for (const f of ["dist/index.js", "dist/index.d.ts", "dist/core.mjs", "dist/core.d.mts"]) {
      assert.ok(existsSync(path.join(installed, f)), `falta ${f} en el tarball`);
    }

    // El consumidor ejecuta la superficie desde el tarball instalado.
    writeFileSync(
      path.join(consumer, "consumer.mjs"),
      [
        'import { quickVerify, verifyGstV2Offline, GST_V2_DOMAIN } from "@verared/gerarion-time";',
        "if (GST_V2_DOMAIN.length !== 12) throw new Error('dominio inválido');",
        'if (typeof quickVerify !== "function") throw new Error("quickVerify ausente");',
        'if (typeof verifyGstV2Offline !== "function") throw new Error("verifyGstV2Offline ausente");',
        'if (!quickVerify("2031DY-03-08-T-09:30:00-SC-TCJ+0")) throw new Error("quickVerify falló");',
        'console.log("consumidor externo OK");',
      ].join("\n"),
    );
    const out = execFileSync("node", [path.join(consumer, "consumer.mjs")], {
      cwd: consumer,
      encoding: "utf8",
    });
    assert.match(out, /consumidor externo OK/);
  } finally {
    rmSync(packDir, { recursive: true, force: true });
    rmSync(consumer, { recursive: true, force: true });
  }
});
