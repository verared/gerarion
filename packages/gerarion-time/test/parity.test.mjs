// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
// Paridad Python ↔ JS: bytes firmables GST v2 + verificación híbrida.
import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";

import { GST_V2_DOMAIN, verifyGstV2Offline } from "../dist/index.js";
import { jcsSerialize } from "../dist/jcs.js";
import { loadFixture, trustedIssuersFor, HERE } from "./helpers.mjs";

test("paridad Python ↔ JS: bytes firmables idénticos y verificación sealed (3 variantes)", async () => {
  const fx = loadFixture();
  assert.equal(fx.stamp, "2031DY-03-08-T-09:30:00-SC-TCJ+0");
  assert.deepEqual(Object.keys(fx.variants).sort(), ["ML-DSA-44", "ML-DSA-65", "ML-DSA-87"]);

  for (const [param, fixture] of Object.entries(fx.variants)) {
    // 1. Paridad byte-a-byte: JCS de JS === JCS de Python (message_hex
    //    incluye el prefijo de dominio GST_V2_DOMAIN de 12 bytes).
    const { message } = domainAndJcs(fixture.envelope);
    const pythonMessage = Buffer.from(fixture.message_hex, "hex");
    assert.equal(
      Buffer.compare(message, pythonMessage),
      0,
      `JCS(payload) desigual en ${param}`,
    );

    // 2. Verificación positiva con política de emisores → sealed.
    const trustedIssuers = {
      [fixture.issuer]: { ed25519: fixture.ed_pub_hex, mldsa: fixture.pqc_pub_hex },
    };
    const result = await verifyGstV2Offline(fixture.envelope, fx.event_hash, {
      trustedIssuers,
    });
    assert.equal(result.verdict, "sealed", `${param}: ${result.reason}`);
    assert.equal(result.sealed, true, `${param} no debe exponer anchored offline`);
  }
});

function domainAndJcs(envelope) {
  const { sigs, ...payload } = envelope;
  const jcs = jcsSerialize(payload);
  const body = new TextEncoder().encode(jcs);
  const message = new Uint8Array(GST_V2_DOMAIN.length + body.length);
  message.set(GST_V2_DOMAIN, 0);
  message.set(body, GST_V2_DOMAIN.length);
  return { payload, message };
}

test("event_hash divergente → invalid", async () => {
  const fx = loadFixture();
  for (const fixture of Object.values(fx.variants)) {
    const result = await verifyGstV2Offline(
      fixture.envelope,
      "sha256:" + "cd".repeat(32),
      { trustedIssuers: trustedIssuersFor(fx, Object.keys(fx.variants).find(k => fx.variants[k] === fixture)) },
    );
    assert.equal(result.verdict, "invalid");
  }
});

test("payload manipulado (ts) → invalid", async () => {
  const fx = loadFixture();
  for (const [param, fixture] of Object.entries(fx.variants)) {
    const tampered = { ...fixture.envelope, ts: "2031DY-03-08-T-23:59:59-SC-TCJ+0" };
    const result = await verifyGstV2Offline(tampered, fx.event_hash, {
      trustedIssuers: trustedIssuersFor(fx, param),
    });
    assert.equal(result.verdict, "invalid");
  }
});

test("downgrade de algoritmo → invalid", async () => {
  const fx = loadFixture();
  for (const [param, fixture] of Object.entries(fx.variants)) {
    // Altera el descriptor de algoritmos a un valor DISTINTO del firmado:
    // la firma cubre JCS(payload), así que cualquier cambio en `alg` /
    // `alg_pqc` debe romper la verificación (anti-downgrade estructural).
    const alteredAlg =
      fixture.envelope.alg === "HYBRID-ED25519-ML-DSA-44"
        ? "HYBRID-ED25519-ML-DSA-87"
        : "HYBRID-ED25519-ML-DSA-44";
    const downgraded = { ...fixture.envelope, alg: alteredAlg };
    const result = await verifyGstV2Offline(downgraded, fx.event_hash, {
      trustedIssuers: trustedIssuersFor(fx, param),
    });
    assert.equal(result.verdict, "invalid");
  }
});
