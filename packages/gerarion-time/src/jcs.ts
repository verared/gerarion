// SPDX-License-Identifier: Apache-2.0
/**
 * Canonicalización JSON RFC 8785 (JCS) — 100% Web-API puro.
 *
 * Paridad byte-a-byte con `gerarion/gst/jcs.py` (Python):
 * - Claves de objeto ordenadas por unidades de código UTF-16 (orden
 *   lexicográfico ECMAScript por defecto sobre arrays de claves).
 * - Cadenas con escape mínimo ECMAScript (`JSON.stringify`): solo `"`,
 *   `\` y controles < 0x20; el resto de Unicode viaja literal UTF-8.
 * - Números: representación ECMAScript `Number::toString`; se rechazan
 *   NaN/±Infinity (JCS no los representa) y enteros fuera del rango
 *   interoperable ±(2^53 − 1), igual que `jcs.py`.
 */

export class JcsError extends Error {}

export function jcsSerialize(value: unknown): string {
  const out = jcsValue(value, "raíz JCS");
  if (out === null) {
    throw new JcsError("JCS_INVALID: la raíz no puede ser null");
  }
  return out;
}

/**
 * Rechaza cadenas con sustitutos huérfanos (U+D800..U+DFFF sin pareja),
 * igual que jcs.py: JCS exige cadenas Unicode bien formadas; nunca se
 * "arreglan" en silencio (fail-closed).
 */
function assertWellFormed(s: string, where: string): void {
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c >= 0xd800 && c <= 0xdfff) {
      // Par alternado emparejado (alto seguido de bajo) = astral válido.
      const isHigh = c <= 0xdbff;
      const paired =
        isHigh &&
        i + 1 < s.length &&
        s.charCodeAt(i + 1) >= 0xdc00 &&
        s.charCodeAt(i + 1) <= 0xdfff;
      if (!paired) {
        throw new JcsError(
          `JCS_INVALID: ${where}: sustituto huérfano no es Unicode bien formado`,
        );
      }
      i++; // consume la mitad baja del par emparejado
    }
  }
}

/** Devuelve null cuando el valor no es canonizable (señal interna). */
function jcsValue(value: unknown, where: string): string | null {
  if (value === null) return "null";
  switch (typeof value) {
    case "boolean":
      return value ? "true" : "false";
    case "number":
      return jcsNumber(value, where);
    case "string":
      assertWellFormed(value, where);
      return JSON.stringify(value);
    case "bigint": {
      if (value > BigInt(Number.MAX_SAFE_INTEGER) || value < -BigInt(Number.MAX_SAFE_INTEGER)) {
        throw new JcsError(
          `JCS_INVALID: ${where}: entero fuera del rango interoperable ±(2^53−1)`,
        );
      }
      return value.toString();
    }
    case "object": {
      if (Array.isArray(value)) {
        const parts = value.map((v) => {
          const s = jcsValue(v, where);
          if (s === null) throw new JcsError(`JCS_INVALID: ${where}: valor no canonizable en array`);
          return s;
        });
        return `[${parts.join(",")}]`;
      }
      const obj = value as Record<string, unknown>;
      const proto = Object.getPrototypeOf(obj);
      if (proto !== Object.prototype && proto !== null) {
        throw new JcsError(`JCS_INVALID: ${where}: tipo ajeno a JSON`);
      }
      const entries = Object.keys(obj).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
      const parts: string[] = [];
      for (const k of entries) {
        const v = obj[k];
        if (v === undefined) continue;
        const s = jcsValue(v, where);
        if (s === null) throw new JcsError(`JCS_INVALID: ${where}: valor no canonizable`);
        parts.push(`${JSON.stringify(k)}:${s}`);
      }
      return `{${parts.join(",")}}`;
    }
    default:
      throw new JcsError(`JCS_INVALID: ${where}: tipo no canonizable`);
  }
}

function jcsNumber(n: number, where: string): string {
  if (!Number.isFinite(n)) {
    throw new JcsError(`JCS_INVALID: ${where}: NaN/Infinity no representable en JCS`);
  }
  return JSON.stringify(n);
}
