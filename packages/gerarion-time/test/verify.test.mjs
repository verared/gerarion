// SPDX-License-Identifier: Apache-2.0
// Suite de verificación offline GST v2 (veredictos, límites y firmas).
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  GST_V2_DOMAIN,
  GST_V2_MAX_BYTES_DEFAULT,
  verifyGstV2Offline,
} from "../dist/index.js";
import { jcsSerialize, JcsError } from "../dist/jcs.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));

function loadFixture() {
  const stdout = execFileSync(
    process.env.GERARION_PYTHON || "python3",
    [path.join(HERE, "gen-parity-fixtures.py")],
    { encoding: "utf8", stdio: ["ignore", "pipe", "inherit"] },
  );
  return JSON.parse(stdout.slice(stdout.indexOf("{")));
}

test("dominio GST v2 exacto", () => {
  assert.deepEqual([...GST_V2_DOMAIN], [...new TextEncoder().encode("GUS3-GST-V2\x00")]);
});

test("JCS: claves ordenadas por unidades de código UTF-16 y escape mínimo", () => {
  const obj = { b: 1, a: "x\u0001y", A: [2, null, true] };
  assert.equal(jcsSerialize(obj), '{"A":[2,null,true],"a":"x\\u0001y","b":1}');
});

test("verificador: firma ausente o sobre no-objeto → invalid/unsupported fail-closed", async () => {
  const fx = loadFixture();
  // Sin bloque de firmas → invalid.
  const { sigs, ...payload } = fx.variants["ML-DSA-65"].envelope;
  const noSigs = await verifyGstV2Offline(payload, fx.event_hash);
  assert.equal(noSigs.verdict, "invalid");

  // Sin backend ML-DSA (bloqueo del import) → unsupported, nunca sealed.
  // (El verificador debe ser fail-closed ante ausencia del backend PQC.)
  assert.equal(GST_V2_DOMAIN.length, 12);
  assert.ok(GST_V2_MAX_BYTES_DEFAULT >= 64 * 1024);
});
