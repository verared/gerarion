// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
// Helper compartido: política de emisores autorizados desde el fixture.
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const HERE = path.dirname(fileURLToPath(import.meta.url));

export function loadFixture() {
  const stdout = execFileSync(
    process.env.GERARION_PYTHON || "python3",
    [path.join(HERE, "gen-parity-fixtures.py")],
    { encoding: "utf8", stdio: ["ignore", "pipe", "inherit"] },
  );
  const start = stdout.indexOf("{");
  if (start < 0) throw new Error("el generador no produjo JSON");
  return JSON.parse(stdout.slice(start));
}

/**
 * Construye trustedIssuers para el emisor del fixture con las claves
 * firmantes reales (Ed25519 + ML-DSA) de la variante indicada.
 */
export function trustedIssuersFor(fixture, param = "ML-DSA-65") {
  const v = fixture.variants[param];
  return {
    [v.issuer]: {
      ed25519: v.ed_pub_hex,
      mldsa: v.pqc_pub_hex,
    },
  };
}
