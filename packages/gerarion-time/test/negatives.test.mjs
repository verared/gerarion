// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
// Matriz de tests negativos del verificador offline GST v2.
// Cada caso confirma el veredicto esperado sobre un recibo real firmado
// por Python (gerarion.gst.v2.create) con mutaciones dirigidas.
import { test } from "node:test";
import assert from "node:assert/strict";

import { verifyGstV2Offline } from "../dist/index.js";
import { setMlDsaLoaderForTests } from "../dist/gst-v2.js";
import { loadFixture, trustedIssuersFor } from "./helpers.mjs";

// Prepara una copia limpia del sobre válido por variante.
function freshEnv(fx, param) {
  return { ...fx.variants[param].envelope };
}

test("firma Ed25519 alterada (ML-DSA válida) → invalid", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  const tamperedSig = (env.sigs.sigs.ed25519[0] === "f" ? "0" : "f") + env.sigs.sigs.ed25519.slice(1);
  const tampered = structuredClone(env);
  tampered.sigs = { ...env.sigs, sigs: { ...env.sigs.sigs, ed25519: tamperedSig } };
  const r = await verifyGstV2Offline(tampered, fx.event_hash, {
    trustedIssuers: trustedIssuersFor(fx, "ML-DSA-65"),
  });
  assert.equal(r.verdict, "invalid");
  assert.equal(r.code, "SIGNATURE_INVALID");
  assert.equal(r.sealed, false);
});

test("firma ML-DSA alterada (Ed25519 válida) → invalid", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  const tamperedSig = (env.sigs.sigs.mldsa[0] === "a" ? "0" : "a") + env.sigs.sigs.mldsa.slice(1);
  const tampered = structuredClone(env);
  tampered.sigs = { ...env.sigs, sigs: { ...env.sigs.sigs, mldsa: tamperedSig } };
  const r = await verifyGstV2Offline(tampered, fx.event_hash, {
    trustedIssuers: trustedIssuersFor(fx, "ML-DSA-65"),
  });
  assert.equal(r.verdict, "invalid");
  assert.equal(r.code, "SIGNATURE_INVALID");
});

test("llave equivocada en el sobre (no coincide con trustedIssuers) → invalid KEY_NOT_AUTHORIZED", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  env.pub_classical = "aa".repeat(32); // otra llave Ed25519
  const r = await verifyGstV2Offline(env, fx.event_hash, {
    trustedIssuers: trustedIssuersFor(fx, "ML-DSA-65"),
  });
  assert.equal(r.verdict, "invalid");
  assert.equal(r.code, "KEY_NOT_AUTHORIZED");
});

test("emisor no autorizado (ausente en trustedIssuers) → invalid UNAUTHORIZED_ISSUER", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  const r = await verifyGstV2Offline(env, fx.event_hash, {
    trustedIssuers: { "otro-emisor": { ed25519: fx.variants["ML-DSA-65"].ed_pub_hex, mldsa: fx.variants["ML-DSA-65"].pqc_pub_hex } },
  });
  assert.equal(r.verdict, "invalid");
  assert.equal(r.code, "UNAUTHORIZED_ISSUER");
});

test("sin política de emisores → invalid MISSING_ISSUER_POLICY (fail-closed)", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  // Sin trustedIssuers: las llaves embebidas en el sobre NO bastan.
  const r = await verifyGstV2Offline(env, fx.event_hash, {});
  assert.equal(r.verdict, "invalid");
  assert.equal(r.code, "MISSING_ISSUER_POLICY");
  // Y con el tercer argumento como number (compatibilidad maxBytes) sigue exigiendo política.
  const r2 = await verifyGstV2Offline(env, fx.event_hash, 64 * 1024);
  assert.equal(r2.verdict, "invalid");
  assert.equal(r2.code, "MISSING_ISSUER_POLICY");
});

test("recibo autofirmado con llaves válidas pero no autorizadas → invalid", async () => {
  const fx = loadFixture();
  // El sobre está firmado por las llaves del fixture, pero la política
  // autoriza claves distintas (otro par válido): crypto OK pero llave no autorizada.
  const env = freshEnv(fx, "ML-DSA-65");
  const r = await verifyGstV2Offline(env, fx.event_hash, {
    trustedIssuers: {
      [fx.variants["ML-DSA-65"].issuer]: { ed25519: "bb".repeat(32), mldsa: "cc".repeat(64) },
    },
  });
  assert.equal(r.verdict, "invalid");
  assert.equal(r.code, "KEY_NOT_AUTHORIZED");
});

test("ts e ins no coinciden (ins +1s) → invalid TEMPORAL_FIELD_MISMATCH", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  env.ins = env.ins + 1;
  const r = await verifyGstV2Offline(env, fx.event_hash, {
    trustedIssuers: trustedIssuersFor(fx, "ML-DSA-65"),
  });
  assert.equal(r.verdict, "invalid");
  assert.equal(r.code, "TEMPORAL_FIELD_MISMATCH");
});

test("nanos fuera de rango → invalid TEMPORAL_FIELD_MISMATCH", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  env.nanos = 1_000_000_000; // > NANOS_MAX (999_999_999)
  const r = await verifyGstV2Offline(env, fx.event_hash, {
    trustedIssuers: trustedIssuersFor(fx, "ML-DSA-65"),
  });
  assert.equal(r.verdict, "invalid");
  assert.equal(r.code, "TEMPORAL_FIELD_MISMATCH");
});

test("recibo con caracteres multibyte cuyo tamaño en BYTES UTF-8 > 64 KiB → invalid ENVELOPE_TOO_LARGE", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  // "€" = 3 bytes UTF-8 pero 1 char JS: 30_000 chars = 90_000 bytes > 65_536,
  // mientras que JSON.stringify(...).length (chars) ≈ 30_0xx < 65_536.
  env.kid = "€".repeat(30_000);
  assert.ok(JSON.stringify(env).length <= 64 * 1024, "precondición: en chars cabe");
  assert.ok(new TextEncoder().encode(JSON.stringify(env)).byteLength > 64 * 1024, "en bytes no cabe");
  const r = await verifyGstV2Offline(env, fx.event_hash, {
    trustedIssuers: trustedIssuersFor(fx, "ML-DSA-65"),
  });
  assert.equal(r.verdict, "invalid");
  assert.equal(r.code, "ENVELOPE_TOO_LARGE");
});

test("recibo que supera el límite por defecto (64 KiB) → invalid", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  env.kid = "x".repeat(70 * 1024);
  const r = await verifyGstV2Offline(env, fx.event_hash, {
    trustedIssuers: trustedIssuersFor(fx, "ML-DSA-65"),
  });
  assert.equal(r.verdict, "invalid");
  assert.equal(r.code, "ENVELOPE_TOO_LARGE");
});

test("escala fuera de perfil → invalid", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  env.scale = "GUS";
  const r = await verifyGstV2Offline(env, fx.event_hash, {
    trustedIssuers: trustedIssuersFor(fx, "ML-DSA-65"),
  });
  assert.equal(r.verdict, "invalid");
  assert.equal(r.code, "INVALID_SCALE");
});

test("emisor no autorizado (identidad ajena al sello) → invalid", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  env.issuer = "otro-emisor";
  const r = await verifyGstV2Offline(env, fx.event_hash, {
    trustedIssuers: trustedIssuersFor(fx, "ML-DSA-65"),
  });
  assert.equal(r.verdict, "invalid");
  assert.equal(r.code, "UNAUTHORIZED_ISSUER");
});

test("backend ML-DSA ausente → unsupported (ml_dsa_unavailable)", async () => {
  const fx = loadFixture();
  setMlDsaLoaderForTests(async () => null);
  try {
    const r = await verifyGstV2Offline(freshEnv(fx, "ML-DSA-65"), fx.event_hash, {
      trustedIssuers: trustedIssuersFor(fx, "ML-DSA-65"),
    });
    assert.equal(r.verdict, "unsupported");
    assert.equal(r.code, "ML_DSA_UNAVAILABLE");
    assert.equal(r.reason, "ml_dsa_unavailable");
    assert.equal(r.sealed, false);
  } finally {
    setMlDsaLoaderForTests(null);
  }
});
