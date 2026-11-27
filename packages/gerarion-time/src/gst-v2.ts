// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
/**
 * Verificador offline de recibos GST v2 (híbrido Ed25519 + ML-DSA).
 *
 * 100% Web-API puro: Ed25519 vía WebCrypto (`crypto.subtle`); ML-DSA vía
 * carga perezosa de `@noble/post-quantum`. Fail-closed: si el backend
 * ML-DSA no está disponible, el veredicto es `unsupported`, jamás `sealed`.
 *
 * Contrato `sealed` (alineado con `gst/v2.py`, nivel crypto + identidad):
 * - política EXPLÍCITA de emisores autorizados (`trustedIssuers`); sin ella
 *   o sin coincidencia exacta de llaves → `invalid` (fail-closed);
 * - coherencia temporal interna ts/ins/nanos/scale verificada con el núcleo
 *   determinista (`core.mjs`, misma regla que Python);
 * - doble firma híbrida válida sobre los MISMOS bytes canónicos
 *   `GUS3-GST-V2\x00 + JCS(payload)`;
 * - `event_hash` exactamente igual al digest esperado;
 * - tamaño del sobre medido en BYTES UTF-8 reales (límite 64 KiB por defecto).
 */
import { jcsSerialize } from "./jcs.js";
import {
  parse as gusParse,
  canonicalOf,
  fromGerarion,
  instantFromParts,
  NANOS_MAX,
} from "./core.mjs";

export const GST_V2_DOMAIN: Uint8Array = new Uint8Array(
  /* "GUS3-GST-V2\x00" */
  [0x47, 0x55, 0x53, 0x33, 0x2d, 0x47, 0x53, 0x54, 0x2d, 0x56, 0x32, 0x00],
);

/** Límite explícito de tamaño del sobre (bytes UTF-8); configurable. */
export const GST_V2_MAX_BYTES_DEFAULT = 64 * 1024;

/** Forma exigida del digest del artefacto: sha256:<hex64> o sha512:<hex128>. */
const EVENT_HASH_RE = /^(?:sha256:[0-9a-f]{64}|sha512:[0-9a-f]{128})$/;

export type GstV2Verdict = "sealed" | "invalid" | "unsupported";

export interface GstV2Result {
  verdict: GstV2Verdict;
  /** true SOLO con política de emisor autorizada + firmas híbridas válidas. */
  sealed: boolean;
  /** Código de error estructurado (p. ej. UNAUTHORIZED_ISSUER). */
  code: string;
  reason: string;
}

/** Claves autorizadas de un emisor (hex crudo, como viajan en el sobre). */
export interface TrustedIssuerKeys {
  /** Clave pública Ed25519 autorizada (hex, 32 bytes). */
  ed25519: string;
  /** Clave pública ML-DSA autorizada (hex). */
  mldsa: string;
  /** Niveles ML-DSA permitidos para este emisor (si se fijan). */
  allowedMlDsaLevels?: Array<"ML-DSA-44" | "ML-DSA-65" | "ML-DSA-87">;
}

export interface GstV2VerifyOptions {
  /**
   * Registro EXPLÍCITO de emisores autorizados: issuer_id → claves públicas.
   * Obligatorio (fail-closed): el verificador NUNCA confía en las llaves
   * embebidas en el sobre por sí solas.
   */
  trustedIssuers?: Record<string, TrustedIssuerKeys>;
  /** Límite de tamaño del sobre en bytes UTF-8 (por defecto 64 KiB). */
  maxBytes?: number;
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

function invalid(code: string, reason: string): GstV2Result {
  return { verdict: "invalid", sealed: false, code, reason };
}

/**
 * Coherencia temporal interna del sello GUS (misma regla que `gst/v2.py`):
 * `ts` canónico ⇔ `ins` (segundos) y `nanos` en [0, 999_999_999].
 */
function checkTemporalCoherence(envelope: Record<string, unknown>): string | null {
  const ts = str(envelope["ts"]);
  let parsed;
  try {
    parsed = gusParse(ts);
  } catch {
    return "TEMPORAL_FIELD_MISMATCH: ts no parsea como marca GUS canónica";
  }
  if (canonicalOf(parsed) !== ts) {
    return "TEMPORAL_FIELD_MISMATCH: ts no está en forma canónica";
  }
  const nanos = envelope["nanos"];
  if (
    typeof nanos !== "number" ||
    !Number.isInteger(nanos) ||
    nanos < 0 ||
    nanos > NANOS_MAX
  ) {
    return `TEMPORAL_FIELD_MISMATCH: nanos fuera de rango 0..${NANOS_MAX}`;
  }
  const date = fromGerarion(parsed.year, parsed.month, parsed.day);
  const instant = instantFromParts(
    date.dayIndex,
    parsed.hour,
    parsed.minute,
    parsed.second,
    parsed.offsetSeconds ?? 0,
  );
  const ins = envelope["ins"];
  if (instant !== BigInt(ins as number | string | bigint)) {
    return "TEMPORAL_FIELD_MISMATCH: ins no corresponde a ts (segundos TCJ)";
  }
  return null;
}

/**
 * Verificación offline de un sobre GST v2 (fail-closed).
 *
 * Parámetros:
 * - `envelope`: sobre GST v2 (objeto JSON con `sigs`).
 * - `expectedEventHash`: digest EXACTO del artefacto esperado.
 * - `options`: `{ trustedIssuers, maxBytes? }`. Por compatibilidad, un
 *   `number` como tercer argumento se interpreta como `maxBytes` (pero la
 *   política de emisores sigue siendo OBLIGATORIA: sin ella → invalid).
 *
 * Veredicto `sealed` exige: política de emisor presente y coincidente,
 * coherencia temporal interna, event_hash exacto, esquema conforme,
 * tamaño dentro del límite (bytes UTF-8) y doble firma híbrida válida.
 */
export async function verifyGstV2Offline(
  envelope: unknown,
  expectedEventHash: string,
  options: GstV2VerifyOptions | number = {},
): Promise<GstV2Result> {
  const opts: GstV2VerifyOptions =
    typeof options === "number" ? { maxBytes: options } : options;
  const maxBytes = opts.maxBytes ?? GST_V2_MAX_BYTES_DEFAULT;

  if (!isPlainObject(envelope)) {
    return invalid("INVALID_ENVELOPE", "no es un objeto JSON");
  }
  // Tamaño real en BYTES UTF-8 (no en caracteres JS).
  const rawBytes = new TextEncoder().encode(JSON.stringify(envelope)).byteLength;
  if (rawBytes > maxBytes) {
    return invalid(
      "ENVELOPE_TOO_LARGE",
      `supera ${maxBytes} bytes UTF-8 (medido: ${rawBytes})`,
    );
  }

  const alg = str(envelope["alg"]);
  if (!alg.startsWith("HYBRID-ED25519-ML-DSA-")) {
    return invalid("INVALID_ALG", "alg debe ser un híbrido HYBRID-ED25519-ML-DSA-*");
  }

  for (const field of ["gst_version", "ts", "scale", "kid", "issuer", "policy_version"]) {
    if (typeof envelope[field] !== "string" || !(envelope[field] as string).length) {
      return invalid("SCHEMA_INVALID", `campo obligatorio ausente: ${field}`);
    }
  }
  const ins = envelope["ins"];
  const insOk =
    (typeof ins === "number" && Number.isInteger(ins)) ||
    (typeof ins === "string" && /^-?\d+$/.test(ins)) ||
    typeof ins === "bigint";
  if (!insOk) {
    return invalid("SCHEMA_INVALID", "ins debe ser un entero");
  }
  if (envelope["gst_version"] !== "2.0") {
    return invalid("VERSION_DOWNGRADE", "gst_version distinto de 2.0");
  }
  if (envelope["scale"] !== "TCJ") {
    return invalid("INVALID_SCALE", "GST v2 solo admite la escala TCJ");
  }
  const algPqc = str(envelope["alg_pqc"]);
  const level = mlLevelOf(algPqc);
  if (level === null) {
    return invalid("INVALID_ALG", "alg_pqc debe ser ML-DSA-44/65/87");
  }

  // Coherencia temporal interna (ts ⇔ ins ⇔ nanos), con el núcleo GUS/TCJ.
  const temporalError = checkTemporalCoherence(envelope);
  if (temporalError !== null) {
    return invalid("TEMPORAL_FIELD_MISMATCH", temporalError);
  }

  // Política EXPLÍCITA de emisores autorizados (fail-closed).
  const trusted = opts.trustedIssuers;
  if (!trusted || typeof trusted !== "object") {
    return invalid(
      "MISSING_ISSUER_POLICY",
      "se exige trustedIssuers explícito; las llaves del sobre no bastan",
    );
  }
  const issuer = str(envelope["issuer"]);
  const policy = trusted[issuer];
  if (!policy) {
    return invalid("UNAUTHORIZED_ISSUER", `emisor no autorizado: ${issuer}`);
  }
  const pubClassicalHex = str(envelope["pub_classical"]).toLowerCase();
  const pubPqcHex = str(envelope["pub_pqc"]).toLowerCase();
  if (
    pubClassicalHex !== str(policy.ed25519).toLowerCase() ||
    pubPqcHex !== str(policy.mldsa).toLowerCase()
  ) {
    return invalid(
      "KEY_NOT_AUTHORIZED",
      "las claves del sobre no coinciden exactamente con las autorizadas del emisor",
    );
  }
  if (
    policy.allowedMlDsaLevels &&
    !policy.allowedMlDsaLevels.includes(algPqc as "ML-DSA-44" | "ML-DSA-65" | "ML-DSA-87")
  ) {
    return invalid("KEY_NOT_AUTHORIZED", `nivel ML-DSA no permitido para ${issuer}: ${algPqc}`);
  }

  // Igualdad EXACTA del event_hash contra el digest esperado (no solo formato).
  const eventHash = str(envelope["event_hash"]);
  if (!EVENT_HASH_RE.test(eventHash) || eventHash !== expectedEventHash) {
    return invalid(
      "EVENT_HASH_MISMATCH",
      "event_hash divergente del artefacto esperado",
    );
  }

  const sigs = envelope["sigs"];
  if (!isPlainObject(sigs)) {
    return invalid("MISSING_SIGS", "falta el bloque de firmas 'sigs'");
  }
  // El blob de firmas viaja como {alg, sigs: {ed25519, mldsa}}.
  const sigPair = isPlainObject(sigs["sigs"]) ? sigs["sigs"] : undefined;
  const sigEd = str(sigPair?.["ed25519"]);
  const sigMl = str(sigPair?.["mldsa"]);
  if (!sigEd || !sigMl) {
    return invalid("MISSING_SIGS", "el modo híbrido exige el par ed25519+mldsa");
  }

  const pubClassical = hexToBytes(pubClassicalHex);
  const pubPqc = hexToBytes(pubPqcHex);
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
    return invalid("SIGNATURE_INVALID", "rama Ed25519 inválida");
  }

  // 2. Rama PQC: ML-DSA-44/65/87 (carga perezosa, fail-closed).
  const pqc = await loadMlDsa();
  if (!pqc) {
    return { verdict: "unsupported", sealed: false, code: "ML_DSA_UNAVAILABLE", reason: "ml_dsa_unavailable" };
  }
  const mlOk = pqc[level].verify(sigMlBytes, message, pubPqc, {
    context: ML_DSA_CTX,
  });
  if (!mlOk) {
    return invalid("SIGNATURE_INVALID", "rama ML-DSA inválida");
  }

  return {
    verdict: "sealed",
    sealed: true,
    code: "CRYPTO_OK",
    reason: "firma híbrida Ed25519 + ML-DSA verificada, emisor autorizado, coherencia temporal OK",
  };
}
