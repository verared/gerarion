// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
/**
 * Verificador offline de recibos GST v2 (híbrido Ed25519 + ML-DSA).
 *
 * 100% Web-API puro: Ed25519 vía WebCrypto (`crypto.subtle`); ML-DSA vía
 * carga perezosa de `@noble/post-quantum`. Fail-closed: si el backend
 * ML-DSA no está disponible, el veredicto es `unsupported`, jamás `sealed`.
 *
 * Los bytes firmables son EXACTAMENTE `GUS3-GST-V2\x00 + JCS(payload)`,
 * igual que `gst/v2.py` (`gst_v2_message`).
 */
import { jcsSerialize } from "./jcs.js";

export const GST_V2_DOMAIN: Uint8Array = new Uint8Array(
  /* "GUS3-GST-V2\x00" */
  [0x47, 0x55, 0x53, 0x33, 0x2d, 0x47, 0x53, 0x54, 0x2d, 0x56, 0x32, 0x00],
);

/** Límite explícito de tamaño del sobre (bytes); configurable por llamada. */
export const GST_V2_MAX_BYTES_DEFAULT = 64 * 1024;

/** Forma exigida del digest del artefacto: sha256:<hex64> o sha512:<hex128>. */
const EVENT_HASH_RE = /^(?:sha256:[0-9a-f]{64}|sha512:[0-9a-f]{128})$/;

export type GstV2Verdict = "sealed" | "invalid" | "unsupported";

export interface GstV2Result {
  verdict: GstV2Verdict;
  /** true SOLO con ambas firmas híbridas válidas y esquema conforme. */
  sealed: boolean;
  reason: string;
}

function str(v: unknown): string {
  return typeof v === "string" ? v : "";
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  if (v === null || typeof v !== "object") return false;
  const proto = Object.getPrototypeOf(v);
  return (
    typeof v === "object" &&
    v !== null &&
    !Array.isArray(v) &&
    (proto === Object.prototype || proto === null)
  );
}

function hexToBytes(hex: string): Uint8Array {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

function mlLevelOf(algPqc: string): "ml_dsa44" | "ml_dsa65" | "ml_dsa87" | null {
  if (algPqc === "ML-DSA-44") return "ml_dsa44";
  if (algPqc === "ML-DSA-65") return "ml_dsa65";
  if (algPqc === "ML-DSA-87") return "ml_dsa87";
  return null;
}

/** Contexto de dominio canónico de los testigos ML-DSA (gst/adapters.py). */
const ML_DSA_CTX = new TextEncoder().encode("GUS2-TS");

interface MlDsaModule {
  ml_dsa44: { verify: (sig: Uint8Array, msg: Uint8Array, pub: Uint8Array, opts?: { context?: Uint8Array }) => boolean };
  ml_dsa65: { verify: (sig: Uint8Array, msg: Uint8Array, pub: Uint8Array, opts?: { context?: Uint8Array }) => boolean };
  ml_dsa87: { verify: (sig: Uint8Array, msg: Uint8Array, pub: Uint8Array, opts?: { context?: Uint8Array }) => boolean };
}

let mlDsaCache: Promise<MlDsaModule | null> | undefined;

async function defaultLoadMlDsa(): Promise<MlDsaModule | null> {
  if (mlDsaCache === undefined) {
    mlDsaCache = import("@noble/post-quantum/ml-dsa.js").then(
      (m) => m as unknown as MlDsaModule,
      () => null,
    );
  }
  return mlDsaCache;
}

/**
 * Punto de inyección para pruebas: permite simular la ausencia del backend
 * PQC (loader nulo) o sustituirlo por un doble de verificación. `null`
 * restaura el loader real (@noble/post-quantum con caché).
 */
let mlDsaLoader: () => Promise<MlDsaModule | null> = defaultLoadMlDsa;

export function setMlDsaLoaderForTests(
  loader: (() => Promise<MlDsaModule | null>) | null,
): void {
  if (loader === null) {
    mlDsaLoader = defaultLoadMlDsa;
    mlDsaCache = undefined; // resetea la caché también
  } else {
    mlDsaLoader = loader;
  }
}

async function loadMlDsa(): Promise<MlDsaModule | null> {
  return mlDsaLoader();
}

/**
 * Verificación offline de un sobre GST v2.
 *
 * Exige igualdad EXACTA del `event_hash` del sobre contra
 * `expectedEventHash` (digest del artefacto esperado, no solo formato),
 * descriptor híbrido completo sin downgrades y doble firma válida sobre
 * los MISMOS bytes canónicos: `GUS3-GST-V2\x00 + JCS(payload)`.
 *
 * La rama ML-DSA (44/65/87) se selecciona por el campo `alg_pqc` del
 * descriptor; el backend `@noble/post-quantum` se carga perezosamente y su
 * ausencia produce `unsupported` (fail-closed, nunca acepta sin PQC).
 */
export async function verifyGstV2Offline(
  envelope: unknown,
  expectedEventHash: string,
  maxBytes: number = GST_V2_MAX_BYTES_DEFAULT,
): Promise<GstV2Result> {
  if (!isPlainObject(envelope)) {
    return { verdict: "invalid", sealed: false, reason: "INVALID_ENVELOPE: no es un objeto JSON" };
  }
  const raw = JSON.stringify(envelope);
  if (raw.length > maxBytes) {
    return { verdict: "invalid", sealed: false, reason: `ENVELOPE_TOO_LARGE: supera ${maxBytes} bytes` };
  }

  const alg = str(envelope["alg"]);
  if (!alg.startsWith("HYBRID-ED25519-ML-DSA-")) {
    return { verdict: "invalid", sealed: false, reason: "INVALID_ALG: alg debe ser un híbrido HYBRID-ED25519-ML-DSA-*" };
  }

  for (const field of ["gst_version", "ts", "scale", "kid", "issuer", "policy_version"]) {
    if (typeof envelope[field] !== "string" || !(envelope[field] as string).length) {
      return { verdict: "invalid", sealed: false, reason: `SCHEMA_INVALID: campo obligatorio ausente: ${field}` };
    }
  }
  // El instante entero (segundos TCJ) puede viajar como number o como
  // cadena decimal; nunca como bool (trampa typeof de JSON).
  const ins = envelope["ins"];
  const insOk =
    (typeof ins === "number" && Number.isInteger(ins)) ||
    (typeof ins === "string" && /^-?\d+$/.test(ins)) ||
    typeof ins === "bigint";
  if (!insOk) {
    return { verdict: "invalid", sealed: false, reason: "SCHEMA_INVALID: ins debe ser un entero" };
  }
  if (envelope["gst_version"] !== "2.0") {
    return { verdict: "invalid", sealed: false, reason: "VERSION_DOWNGRADE: gst_version distinto de 2.0" };
  }
  if (envelope["scale"] !== "TCJ") {
    return { verdict: "invalid", sealed: false, reason: "INVALID_SCALE: GST v2 solo admite la escala TCJ" };
  }
  const level = mlLevelOf(str(envelope["alg_pqc"]));
  if (level === null) {
    return { verdict: "invalid", sealed: false, reason: "INVALID_ALG: alg_pqc debe ser ML-DSA-44/65/87" };
  }

  // Igualdad EXACTA del event_hash contra el digest esperado (no solo
  // formato): un digest válido de OTRO artefacto se rechaza.
  const eventHash = str(envelope["event_hash"]);
  if (!EVENT_HASH_RE.test(eventHash) || eventHash !== expectedEventHash) {
    return {
      verdict: "invalid",
      sealed: false,
      reason: "EVENT_HASH_MISMATCH: event_hash divergente del artefacto esperado",
    };
  }

  const sigs = envelope["sigs"];
  if (!isPlainObject(sigs)) {
    return { verdict: "invalid", sealed: false, reason: "MISSING_SIGS: falta el bloque de firmas 'sigs'" };
  }
  // El blob de firmas viaja como {alg, sigs: {ed25519, mldsa}}.
  const sigPair = isPlainObject(sigs) && isPlainObject(sigs["sigs"]) ? sigs["sigs"] : undefined;
  const sigEd = str(sigPair?.["ed25519"]);
  const sigMl = str(sigPair?.["mldsa"]);
  if (!sigEd || !sigMl) {
    return { verdict: "invalid", sealed: false, reason: "MISSING_SIGS: el modo híbrido exige el par ed25519+mldsa" };
  }

  const pubClassical = hexToBytes(str(envelope["pub_classical"]));
  const pubPqc = hexToBytes(str(envelope["pub_pqc"]));
  const sigEdBytes = hexToBytes(sigEd);
  const sigMlBytes = hexToBytes(sigMl);

  // Bytes firmables exactos: dominio || JCS(payload sin sigs).
  const { sigs: _sigs, ...payload } = envelope;
  const body = new TextEncoder().encode(jcsSerialize(payload));
  const message = new Uint8Array(GST_V2_DOMAIN.length + body.length);
  message.set(GST_V2_DOMAIN, 0);
  message.set(body, GST_V2_DOMAIN.length);

  // 1. Rama clásica: Ed25519 (WebCrypto) sobre los bytes canónicos.
  const edOk = await (async () => {
    try {
      const key = await crypto.subtle.importKey(
        "raw",
        pubClassical as BufferSource,
        { name: "Ed25519" } as AlgorithmIdentifier,
        false,
        ["verify"],
      );
      return await crypto.subtle.verify(
        { name: "Ed25519" } as AlgorithmIdentifier,
        key,
        sigEdBytes as BufferSource,
        message as BufferSource,
      );
    } catch {
      return false;
    }
  })();
  if (!edOk) {
    return { verdict: "invalid", sealed: false, reason: "SIGNATURE_INVALID: rama Ed25519 inválida" };
  }

  // 2. Rama PQC: ML-DSA-44/65/87 (carga perezosa, fail-closed).
  const pqc = await loadMlDsa();
  if (!pqc) {
    return { verdict: "unsupported", sealed: false, reason: "ml_dsa_unavailable" };
  }
  const mlOk = pqc[level].verify(sigMlBytes, message, pubPqc, {
    context: ML_DSA_CTX,
  });
  if (!mlOk) {
    return { verdict: "invalid", sealed: false, reason: "SIGNATURE_INVALID: rama ML-DSA inválida" };
  }

  return { verdict: "sealed", sealed: true, reason: "CRYPTO_OK: firma híbrida Ed25519 + ML-DSA verificada" };
}
