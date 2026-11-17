/**
 * Runner de conformancia de regresión F2 — consume vectors/gus-regression-001.json.
 * El Gran Tempalum (GT) opera simétricamente en DY y AY; ninguna era se asume
 * sin años largos. Igual que tools/ y impl-c/ consumen el mismo archivo.
 *
 *   node web/regression-conformance.mjs   (exit 0 = CONFORME)
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  parse, canonicalOf, toGerarion, gregorianFromDayIndex, isGranTempalum,
} from "./gerarion.mjs";

const path = fileURLToPath(new URL("../vectors/gus-regression-001.json", import.meta.url));
const v = JSON.parse(readFileSync(path, "utf8"));

let total = 0;
let errors = 0;

for (const c of v.calendar_ay) {
  total++;
  const d = toGerarion(c.day_index);
  if (canonicalOf(d) !== c.canonical) {
    errors++;
    console.log(`FALLA to ${c.day_index}: ${canonicalOf(d)} != ${c.canonical}`);
    continue;
  }
  // weekday llega como string "Sabatyeh" (JS) o como par [nombre, abbr] (Python);
  // el vector usa el nombre completo — se empareja por nombre o abreviatura.
  const wdName = Array.isArray(d.weekday) ? d.weekday[0] : d.weekday;
  const wdAbbr = Array.isArray(d.weekday) ? d.weekday[1] : wdName[0];
  if (wdName !== c.weekday && wdAbbr !== c.weekday) {
    errors++;
    console.log(`FALLA weekday ${c.canonical}: ${wdName} != ${c.weekday}`);
  }
  const g = gregorianFromDayIndex(c.day_index);
  if (g[0] !== c.gregorian[0] || g[1] !== c.gregorian[1] || g[2] !== c.gregorian[2]) {
    errors++;
    console.log(`FALLA greg ${c.canonical}: ${g} != ${c.gregorian}`);
  }
  const p = parse(c.canonical);
  if (canonicalOf(p) !== c.canonical) {
    errors++;
    console.log(`FALLA parse ${c.canonical}: ida y vuelta divergente`);
  }
  if (isGranTempalum(p.year) !== c.gran_tempalum) {
    errors++;
    console.log(`FALLA GT ${c.canonical}`);
  }
}

console.log(`conformance regresión AY (JS): ${total} casos, ${errors} fallos`);
process.exit(errors > 0 ? 1 : 0);
