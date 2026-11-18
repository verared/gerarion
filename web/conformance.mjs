// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
/**
 * Runner de conformancia GUS — consume vectors/gus-normative-003.json (núcleo).
 *
 * Cláusula de conformancia (vectors/README.md): una implementación es conforme
 * si y solo si pasa el 100 % de las categorías del núcleo que declara.
 *
 * Dos modos:
 *   node web/conformance.mjs [ruta-al-json]     -> suite de conformancia, exit 0/1
 *   node web/conformance.mjs --cli              -> protocolo de líneas para
 *     fuzzing diferencial (véase tools/fuzz_diff.py)
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { createInterface } from "node:readline";
import * as g from "./gerarion.mjs";

const CORE = ["constants", "gran_tempalum", "calendar", "year_starts",
  "gregorian_roundtrip", "format", "instant"];

function resolveVectorsPath() {
  const arg = process.argv[2];
  if (arg && arg !== "--cli") return arg;
  if (arg === "--cli") {
    const idx = process.argv.indexOf("--cli");
    const next = process.argv[idx + 1];
    if (next) return next;
  }
  return fileURLToPath(new URL("../vectors/gus-normative-003.json", import.meta.url));
}

// --- verificaciones ------------------------------------------------------

function checkConstants(v, errors) {
  const c = v.constants;
  const mine = {
    ORIGIN_JDN: g.ORIGIN_JDN,
    SOLAR_DELTA_UD: g.SOLAR_DELTA_UD,
    SOLAR_THRESHOLD_UD: g.SOLAR_THRESHOLD_UD,
    SECS_PER_DAY: g.SECS_PER_DAY,
    MONTH_BLOCK_DAYS: g.MONTH_BLOCK_DAYS,
  };
  for (const [k, val] of Object.entries(mine)) {
    if (val !== c[k]) errors.push(`constants.${k}: esperado ${c[k]}, obtenido ${val}`);
  }
  if (g.WEEKDAYS.map((w) => w[1]).join("") !== c.WEEKDAY_LETTERS.join("")) {
    errors.push("constants.WEEKDAY_LETTERS divergente");
  }
}

function checkGranTempalum(v, errors) {
  const pattern = [];
  for (let y = 0; y < 46; y++) if (g.isGranTempalum(y)) pattern.push(y);
  if (JSON.stringify(pattern) !== JSON.stringify(v.gran_tempalum.pattern_years_0_45)) {
    errors.push(`gran_tempalum patrón 0-45: esperado ${JSON.stringify(v.gran_tempalum.pattern_years_0_45)}, obtenido ${JSON.stringify(pattern)}`);
  }
  const patternNeg = [];
  for (let y = -46; y < 0; y++) if (g.isGranTempalum(y)) patternNeg.push(y);
  if (JSON.stringify(patternNeg) !== JSON.stringify(v.gran_tempalum.pattern_years_m45_m1)) {
    errors.push(`gran_tempalum patrón AY: esperado ${JSON.stringify(v.gran_tempalum.pattern_years_m45_m1)}, obtenido ${JSON.stringify(patternNeg)}`);
  }
  for (const [ys, isGt] of Object.entries(v.gran_tempalum.years_sample)) {
    if (g.isGranTempalum(parseInt(ys, 10)) !== isGt) {
      errors.push(`gran_tempalum ${ys}: esperado ${isGt}`);
    }
  }
}

function gregParse(field) {
  return [field.greg_year, field.greg_month, field.greg_day];
}

function checkCalendar(v, errors) {
  for (const row of v.calendar) {
    const di = g.dayIndexFromGregorian(...gregParse(row));
    if (di !== row.day_index) { errors.push(`calendar ${row.greg}: day_index ${di} != ${row.day_index}`); continue; }
    const d = g.toGerarion(di);
    const wantYear = row.era === "DY" ? row.year : -row.year;
    if (d.year !== wantYear || d.month !== row.month || d.day !== row.day) {
      errors.push(`calendar ${row.greg}: fecha ${d.year}/${d.month}/${d.day} != ${wantYear}/${row.month}/${row.day}`);
    }
    if (d.abbr !== row.abbr || d.weekday !== row.weekday) {
      errors.push(`calendar ${row.greg}: día de semana ${d.abbr} != ${row.abbr}`);
    }
  }
}

function checkYearStarts(v, errors) {
  for (const row of v.year_starts) {
    const y = row.year; // signo ya presente en el vector (simétrico, GUS 2.1)
    const di = g.yearStartDayIndex(y);
    if (di !== row.day_index) { errors.push(`year_starts ${y}: ${di} != ${row.day_index}`); continue; }
    if (g.toGerarion(di).abbr !== "S") errors.push(`year_starts ${y}: no empieza en Soludyia`);
    if (g.isGranTempalum(y) !== row.gran_tempalum) {
      errors.push(`year_starts ${y}: gran_tempalum ${g.isGranTempalum(y)} != ${row.gran_tempalum}`);
    }
    if (g.tempalumDays(y) !== row.tempalum_days) {
      errors.push(`year_starts ${y}: tempalum_days ${g.tempalumDays(y)} != ${row.tempalum_days}`);
    }
  }
}

function checkRoundtrip(v, errors) {
  for (const row of v.gregorian_roundtrip) {
    const [y, m, d2] = gregParse(row);
    const got = g.gregorianFromDayIndex(row.day_index);
    if (JSON.stringify(got) !== JSON.stringify([y, m, d2])) {
      errors.push(`roundtrip ${row.day_index}: ${got} != ${[y, m, d2]}`);
    }
    if (g.dayIndexFromGregorian(y, m, d2) !== row.day_index) {
      errors.push(`roundtrip inverso ${row.greg}: divergente`);
    }
  }
}

function errorKind(exc) {
  const msg = String(exc && exc.message);
  for (const code of ["GERO_ETEMPALUM", "GERO_EINVAL", "GERO_EWEEK"]) {
    if (msg.startsWith(code)) return code;
  }
  return msg.slice(0, 60);
}

function checkFormat(v, errors) {
  for (const c of v.format.canonical) {
    try {
      const p = g.parse(c.input);
      const canon = g.canonicalOf(p);
      if (canon !== c.canonical) errors.push(`format ${c.input}: canon ${canon} != ${c.canonical}`);
      const gotFlags = (p.flags || []).slice().sort();
      if (JSON.stringify(gotFlags) !== JSON.stringify(c.flags.slice().sort())) {
        errors.push(`format ${c.input}: flags ${JSON.stringify(gotFlags)} != ${JSON.stringify(c.flags)}`);
      }
    } catch (e) {
      errors.push(`format ${c.input}: excepción inesperada ${errorKind(e)}`);
    }
  }
  for (const c of v.format.errors) {
    let threw = null;
    try { g.parse(c.input); } catch (e) { threw = errorKind(e); }
    if (threw !== c.error) errors.push(`format-error ${c.input}: ${threw} != ${c.error}`);
  }
  for (const c of v.format.strict_weekday) {
    let threw = null;
    try { g.parse(c.input, { strictWeekday: true }); } catch (e) { threw = errorKind(e); }
    if (threw !== c.error) errors.push(`strict ${c.input}: ${threw} != ${c.error}`);
  }
}

function checkInstant(v, errors) {
  for (const row of v.instant) {
    if (row.ts === undefined) continue; // fila de invariantes (equivalent_views)
    try {
      const p = g.parse(row.ts);
      const ins = g.instantFromParts(p.dayIndex, p.hour, p.minute, p.second, row.offset_seconds ?? 0);
      if (ins.toString() !== String(row.instant)) {
        errors.push(`instant ${row.ts}: ${ins} != ${row.instant}`);
      }
      if (p.dayIndex !== row.day) errors.push(`instant ${row.ts}: day ${p.dayIndex} != ${row.day}`);
    } catch (e) {
      errors.push(`instant ${row.ts}: excepción ${errorKind(e)}`);
    }
  }
}

// ----transitional: modo suite -----------------------------------------------

function runSuite() {
  const v = JSON.parse(readFileSync(resolveVectorsPath(), "utf8"));
  const errors = [];
  checkConstants(v, errors);
  checkGranTempalum(v, errors);
  checkCalendar(v, errors);
  checkYearStarts(v, errors);
  checkRoundtrip(v, errors);
  checkFormat(v, errors);
  checkInstant(v, errors);
  for (const e of errors) console.log(`  FALLA ${e}`);
  const n = CORE.length;
  console.log(`conformance GUS núcleo (JS): ${n} categorías, ${errors.length} fallos`);
  if (errors.length === 0) console.log(`CONFORME (núcleo: ${CORE.join(", ")})`);
  else console.log("NO CONFORME");
  process.exit(errors.length === 0 ? 0 : 1);
}

// --- modo CLI de líneas para fuzzing diferencial ----------------------------

function respond(line) {
  const input = line.trim();
  if (input === "") return null;
  const sp = input.indexOf(" ");
  const cmd = sp === -1 ? input : input.slice(0, sp);
  const rest = sp === -1 ? "" : input.slice(sp + 1);
  const tokens = rest.split(" ").filter((t) => t !== "");
  try {
    if (cmd === "tg") {
      const di = parseInt(tokens[0], 10);
      const d = g.toGerarion(di);
      return { ok: true, di, year: Math.abs(d.year), era: d.year >= 0 ? "DY" : "AY", month: d.month, day: d.day, abbr: d.abbr, canon: g.canonicalOf(d) };
    }
    if (cmd === "fg") {
      const y = parseInt(tokens[0], 10), m = parseInt(tokens[1], 10), dd = parseInt(tokens[2], 10);
      const d = g.fromGerarion(y, m, dd);
      return { ok: true, day_index: d.dayIndex, canon: g.canonicalOf(d) };
    }
    if (cmd === "gr") {
      const di = parseInt(tokens[0], 10);
      const [y, m, dd] = g.gregorianFromDayIndex(di);
      return { ok: true, di, greg: `${y}-${m}-${dd}`, greg_year: y, greg_month: m, greg_day: dd };
    }
    if (cmd === "pt") {
      const raw = rest;
      const p = g.parse(raw);
      return { ok: true, canon: g.canonicalOf(p), flags: (p.flags || []).slice().sort() };
    }
    if (cmd === "in") {
      const di = parseInt(tokens[0], 10), h = parseInt(tokens[1], 10), m = parseInt(tokens[2], 10), s = parseInt(tokens[3], 10);
      const ins = g.instantFromParts(di, h, m, s);
      return { ok: true, instant: ins.toString() };
    }
    return { ok: false, error: "comando_desconocido" };
  } catch (e) {
    return { ok: false, error: errorKind(e) };
  }
}

// --- dispatch ---------------------------------------------------------------

if (process.argv.includes("--cli")) {
  const rl = createInterface({ input: process.stdin });
  rl.on("line", (line) => {
    const out = respond(line);
    if (out !== null) process.stdout.write(JSON.stringify(out) + "\n");
  });
} else {
  runSuite();
}
