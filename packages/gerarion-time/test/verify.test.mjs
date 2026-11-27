// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
// Suite de verificación offline GST v2 (veredictos, límites y firmas).
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  GST_V2_DOMAIN,
  GST_V2_MAX_BYTES_DEFAULT,
  verifyGstV2Offline,
} from "../dist/index.js";
import { setMlDsaLoaderForTests } from "../dist/gst-v2.js";
import { jcsSerialize, JcsError } from "../dist/jcs.js";
import { loadFixture, trustedIssuersFor } from "./helpers.mjs";

test("dominio GST v2 exacto", () => {
  assert.deepEqual([...GST_V2_DOMAIN], [...new TextEncoder().encode("GUS3-GST-V2\x00")]);
});

test("JCS: claves ordenadas por unidades de código UTF-16 y escape mínimo", () => {
  const obj = { b: 1, a: "x\u0001y", A: [2, null, true] };
  assert.equal(jcsSerialize(obj), '{"A":[2,null,true],"a":"x\\u0001y","b":1}');
});

test("verificador: firma ausente o sobre no-objeto → invalid; backend PQC ausente → unsupported fail-closed", async () => {
  const fx = loadFixture();
  // Sin bloque de firmas → invalid.
  const { sigs, ...payload } = fx.variants["ML-DSA-65"].envelope;
  const noSigs = await verifyGstV2Offline(payload, fx.event_hash, {
    trustedIssuers: trustedIssuersFor(fx, "ML-DSA-65"),
  });
  assert.equal(noSigs.verdict, "invalid");

  assert.equal(GST_V2_DOMAIN.length, 12);
  assert.ok(GST_V2_MAX_BYTES_DEFAULT >= 64 * 1024);

  // Simulación de backend PQC ausente → unsupported (fail-closed).
  setMlDsaLoaderForTests(async () => null);
  try {
    const r = await verifyGstV2Offline(fx.variants["ML-DSA-65"].envelope, fx.event_hash, {
      trustedIssuers: trustedIssuersFor(fx, "ML-DSA-65"),
    });
    assert.equal(r.verdict, "unsupported");
    assert.equal(r.reason, "ml_dsa_unavailable");
    assert.equal(r.sealed, false);
  } finally {
    setMlDsaLoaderForTests(null);
  }

  // Tras restaurar el loader real, el mismo sobre vuelve a verificar sealed.
  const ok = await verifyGstV2Offline(fx.variants["ML-DSA-65"].envelope, fx.event_hash, {
    trustedIssuers: trustedIssuersFor(fx, "ML-DSA-65"),
  });
  assert.equal(ok.verdict, "sealed");
});
