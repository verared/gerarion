// SPDX-License-Identifier: Apache-2.0
// Matriz de tests negativos del verificador offline GST v2.
// Cada caso confirma el veredicto esperado sobre un recibo real firmado
// por Python (gerarion.gst.v2.create) con mutaciones dirigidas.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { verifyGstV2Offline } from "../dist/index.js";
import { setMlDsaLoaderForTests } from "../dist/gst-v2.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));

function loadFixture() {
  const stdout = execFileSync(
    process.env.GERARION_PYTHON || "python3",
    [path.join(HERE, "gen-parity-fixtures.py")],
    { encoding: "utf8", stdio: ["ignore", "pipe", "inherit"] },
  );
  return JSON.parse(stdout.slice(stdout.indexOf("{")));
}

// Prepara una copia limpia del sobre válido por variante.
function freshEnv(fx, param) {
  return { ...fx.variants[param].envelope };
}

test("firma Ed25519 alterada (ML-DSA válida) → invalid", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  // Cambia UN hex del par ed25519: los bytes firmados ya no corresponden.
  const tamperedSig = (env.sigs.sigs.ed25519[0] === "f" ? "0" : "f") + env.sigs.sigs.ed25519.slice(1);
  const tampered = structuredClone(env);
  tampered.sigs = { ...env.sigs, sigs: { ...env.sigs.sigs, ed25519: tamperedSig } };
  const r = await verifyGstV2Offline(tampered, fx.event_hash);
  assert.equal(r.verdict, "invalid");
  assert.equal(r.sealed, false);
});

test("firma ML-DSA alterada (Ed25519 válida) → invalid", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  const tamperedSig = (env.sigs.sigs.mldsa[0] === "a" ? "0" : "a") + env.sigs.sigs.mldsa.slice(1);
  const tampered = structuredClone(env);
  tampered.sigs = { ...env.sigs, sigs: { ...env.sigs.sigs, mldsa: tamperedSig } };
  const r = await verifyGstV2Offline(tampered, fx.event_hash);
  assert.equal(r.verdict, "invalid");
});

test("llave equivocada (pub de otro firmante) → invalid", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  // Pub Ed25519 de 32 bytes distinta de la firmante.
  env.pub_classical = "aa".repeat(32);
  const r = await verifyGstV2Offline(env, fx.event_hash);
  assert.equal(r.verdict, "invalid");
});

test("recibo que supera el límite por defecto (64 KiB) → invalid", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  env.kid = "x".repeat(70 * 1024); // JSON.stringify(envelope) > 65536 bytes
  const r = await verifyGstV2Offline(env, fx.event_hash); // SIN maxBytes explícito
  assert.equal(r.verdict, "invalid");
});

test("escala fuera de perfil → invalid", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  env.scale = "GUS"; // GST v2 solo admite TCJ
  const r = await verifyGstV2Offline(env, fx.event_hash);
  assert.equal(r.verdict, "invalid");
});

test("emisor no autorizado (identidad ajena al sello) → invalid", async () => {
  const fx = loadFixture();
  const env = freshEnv(fx, "ML-DSA-65");
  env.issuer = "otro-emisor";
  const r = await verifyGstV2Offline(env, fx.event_hash);
  assert.equal(r.verdict, "invalid");
});

test("backend ML-DSA ausente → unsupported (ml_dsa_unavailable)", async () => {
  const fx = loadFixture();
  // Simula un runtime sin backend PQC inyectando loader nulo.
  setMlDsaLoaderForTests(async () => null);
  try {
    const r = await verifyGstV2Offline(freshEnv(fx, "ML-DSA-65"), fx.event_hash);
    assert.equal(r.verdict, "unsupported");
    assert.equal(r.reason, "ml_dsa_unavailable");
    assert.equal(r.sealed, false);
  } finally {
    setMlDsaLoaderForTests(null); // restaura el loader real
  }
});
