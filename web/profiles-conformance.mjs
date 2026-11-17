/**
 * Runner de conformancia del perfil GUS-3339 — consume vectors/gus-3339-001.json.
 *
 * Cláusula de conformancia (vectors/README.md): una implementación que declara
 * el perfil GUS-3339 es conforme si y solo si pasa el 100 % de los vectores de
 * este archivo. El núcleo de calendario (gus-normative-002.json) no cambia.
 *
 *   node web/profiles-conformance.mjs
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import * as g from "./gerarion.mjs";

const path = fileURLToPath(new URL("../vectors/gus-3339-001.json", import.meta.url));
const v = JSON.parse(readFileSync(path, "utf8"));

let total = 0;
let errors = 0;

for (const c of v.gus3339) {
  total++;
  if (c.op === "map") {
    try {
      const ins = g.instantFromRFC3339(c.rfc3339);
      if (ins.toString() !== String(c.ins)) {
        errors++;
        console.log(`FALLA from ${c.rfc3339}: ${ins} != ${c.ins}`);
        continue;
      }
      const back = g.instantToRFC3339(BigInt(c.ins));
      if (back !== c.rfc3339) {
        errors++;
        console.log(`FALLA to ${c.ins}: ${back} != ${c.rfc3339}`);
      }
    } catch (e) {
      errors++;
      console.log(`FALLA map ${c.rfc3339}: excepción ${e.message}`);
    }
  } else if (c.op === "from") {
    let threwOk = false;
    try {
      g.instantFromRFC3339(c.rfc3339);
    } catch (e) {
      threwOk = e.message.startsWith(c.error);
    }
    if (!threwOk) {
      errors++;
      console.log(`FALLA reject-from ${c.rfc3339}: debía rechazar con ${c.error}`);
    }
  } else if (c.op === "to") {
    let threwOk = false;
    try {
      g.instantToRFC3339(BigInt(c.ins));
    } catch (e) {
      threwOk = e.message.startsWith(c.error);
    }
    if (!threwOk) {
      errors++;
      console.log(`FALLA reject-to ${c.ins}: debía rechazar con ${c.error}`);
    }
  }
}

for (const c of v.gus3339_canonical) {
  total++;
  try {
    const p = g.parse(c.gus_canonical);
    if (g.canonicalOf(p) !== c.gus_canonical) {
      errors++;
      console.log(`FALLA canon ${c.gus_canonical}: idempotencia`);
      continue;
    }
    const ins = g.instantFromParts(p.dayIndex, p.hour, p.minute, p.second);
    if (ins.toString() !== String(c.ins)) {
      errors++;
      console.log(`FALLA canon ${c.gus_canonical}: instant ${ins} != ${c.ins}`);
      continue;
    }
    if (g.instantToRFC3339(ins) !== c.rfc3339) {
      errors++;
      console.log(`FALLA canon ${c.gus_canonical}: rfc3339 ${g.instantToRFC3339(ins)} != ${c.rfc3339}`);
    }
  } catch (e) {
    errors++;
    console.log(`FALLA canon ${c.gus_canonical}: excepción ${e.message}`);
  }
}

console.log(`conformance GUS-3339 (JS): ${v.gus3339.length} vectores + ${v.gus3339_canonical.length} canon, ${errors} fallos`);
process.exit(errors > 0 ? 1 : 0);
