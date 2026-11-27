// SPDX-License-Identifier: Apache-2.0
// Paridad Python ↔ JS de la canonicalización JCS (RFC 8785 / Appendix B).
// El generador Python (jcs-edge-cases.py) canonicaliza cada caso con
// gerarion.gst.jcs; aquí se recomputa con src/jcs.ts y se compara byte a byte.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { jcsSerialize, JcsError } from "../dist/jcs.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PYTHON = process.env.GERARION_PYTHON || "python3";
const SCRIPT = path.join(HERE, "jcs-edge-cases.py");

function loadCases() {
  const stdout = execFileSync(PYTHON, [SCRIPT], {
    encoding: "utf8",
    stdio: ["ignore", "pipe", "inherit"],
  });
  assert.ok(stdout.trim().startsWith("["), "el generador no produjo un array JSON");
  return JSON.parse(stdout); // el generador emite un array de casos completo
}

test("JCS: paridad byte-a-byte Python ↔ JS en casos borde RFC 8785", () => {
  const cases = loadCases();
  assert.ok(cases.length >= 6, "el generador debe aportar los casos acordados");
  for (const c of cases) {
    const value = JSON.parse(c.input); // misma semántica de parseo en ambos lados
    const expected = Buffer.from(c.canonical_hex, "hex");
    const actual = Buffer.from(jcsSerialize(value), "utf8");
    assert.ok(
      expected.equals(actual),
      `divergencia JCS en '${c.name}': python=${expected.toString("utf8")} js=${actual.toString("utf8")}`,
    );
  }
});

test("JCS: enteros fuera de ±(2^53-1) se rechazan como en jcs.py (BigInt)", () => {
  assert.throws(() => jcsSerialize({ v: 9007199254740993n }), JcsError);
  assert.throws(() => jcsSerialize({ v: -9007199254740993n }), JcsError);
  // El límite interoperable exacto ±(2^53-1) SÍ canonicaliza.
  assert.equal(jcsSerialize({ v: 9007199254740991n }), '{"v":9007199254740991}');
  assert.equal(jcsSerialize({ v: -9007199254740991n }), '{"v":-9007199254740991}');
});

test("JCS: sustituto huérfano y NaN/Infinity se rechazan (fail-closed)", () => {
  assert.throws(() => jcsSerialize({ s: "\ud800" }), JcsError);
  assert.throws(() => jcsSerialize(NaN), JcsError);
  assert.throws(() => jcsSerialize(Infinity), JcsError);
});
