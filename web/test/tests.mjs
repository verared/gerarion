// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
/**
 * Suite de vectores normativos — misma matriz que tests/test_calendar.py (Python).
 * Ejecutar: node web/tests.mjs  (y también corre auto en el navegador, index.html)
 */
import {
  dayIndexFromGregorian,
  fromGerarion,
  gregorianFromDayIndex,
  isGranTempalum,
  parse,
  quickVerify,
  canonicalOf,
  cycleOf,
  toGerarion,
  instantFromParts,
  GUS_UNIX_OFFSET,
  instantFromRFC3339,
  instantToRFC3339,
} from "../gerarion.mjs";

let passed = 0;
let failed = 0;
const failures = [];

function check(name, fn) {
  try {
    fn();
    passed++;
  } catch (e) {
    failed++;
    failures.push(`${name}: ${e.message}`);
  }
}

function assertEq(a, b, msg = "") {
  if (JSON.stringify(a) !== JSON.stringify(b)) {
    throw new Error(`esperado ${JSON.stringify(b)}, obtenido ${JSON.stringify(a)} ${msg}`);
  }
}

// --- vectores normativos (spec GUS 2.0 §3-§4 + errata v1.2) ---------------
const VECTORS = [
  [[2027, 3, 11], [2031, 12, 30, "M"]],
  [[2027, 3, 12], [2031, 0, 1, "A"]],
  [[2027, 3, 15], [2031, 0, 4, "B"]],
  [[2027, 3, 16], [2032, 1, 1, "S"]],
  [[2026, 4, 15], [2031, 1, 30, "L"]],  // Yeshuvid (errata v1.2 E-02)
  [[2026, 5, 23], [2031, 3, 8, "T"]],
];

for (const [greg, expected] of VECTORS) {
  check(`vector ${greg.join("-")}`, () => {
    const d = toGerarion(dayIndexFromGregorian(...greg));
    assertEq([d.year, d.month, d.day, d.abbr], expected);
  });
}

check("errata E-01: 2031DY-01-01 = 2026-03-17", () => {
  const d = toGerarion(dayIndexFromGregorian(2026, 3, 17));
  assertEq([d.year, d.month, d.day, d.abbr], [2031, 1, 1, "S"]);
});

check("gran tempalum: patrón 5,11,16,22,28,33,39,45", () => {
  const got = [];
  for (let y = 0; y < 46; y++) if (isGranTempalum(y)) got.push(y);
  assertEq(got, [5, 11, 16, 22, 28, 33, 39, 45]);
});

check("todo año empieza en Soludyia (0..200)", () => {
  // año start = yearStartDayIndex — recalc via toGerarion del primer día
  let start = 0;
  for (let year = 0; year < 200; year++) {
    if (toGerarion(start).abbr !== "S") throw new Error(`año ${year} no empieza en Soludyia`);
    start += yearLength(year);
  }
});

function yearLength(year) {
  return isGranTempalum(year) ? 371 : 364;
}

check("roundtrip greg -> gero -> greg (múltiplos de 37)", () => {
  for (let di = 0; di < 3001; di += 37) {
    const [y, m, d] = gregorianFromDayIndex(di);
    if (dayIndexFromGregorian(y, m, d) !== di) throw new Error(`fallo roundtrip en ${di}`);
  }
});

check("normalización regla 1-2: minúsculas y sin ceros", () => {
  const p = parse("2031dy-3-8-t");
  assertEq(canonicalOf(p).slice(0, 14), "2031DY-03-08-T");
});

check("regla 3: era asumida DY", () => {
  const p = parse("2031-03-08-T");
  assertEq(p.flags.includes("era_assumed_DY"), true);
});

check("regla 4: weekday corregido", () => {
  const p = parse("2031DY-03-08-S");
  assertEq(p.flags.includes("weekday_corrected"), true);
  assertEq(canonicalOf(p).endsWith("-T"), true);
});

check("regla 5: Tempalum día 7 en año normal → error", () => {
  let threw = false;
  try {
    parse("2031DY-00-07-T");
  } catch (e) {
    threw = true;
  }
  if (!threw) throw new Error("pegó aceptar Tempalum inválido");
});

check("regla 5: Tempalum día 7 en año GT (2034) válido", () => {
  const p = parse("2034DY-00-07-V");
  assertEq([p.month, p.day], [0, 7]);
});

check("ciclo SC/LC", () => {
  assertEq([cycleOf(0), cycleOf(5), cycleOf(6), cycleOf(12), cycleOf(17), cycleOf(18), cycleOf(23)],
    ["LC", "LC", "SC", "SC", "SC", "LC", "LC"]);
});

check("formato completo idempotente", () => {
  const raw = "2031DY-03-08-T-09:30:00-SC-TCJ+0";
  assertEq(canonicalOf(parse(raw)), raw);
});

check("instante continuo: día siempre 86400", () => {
  for (const di of [0, 1000, 10000, 100000]) {
    const a = instantFromParts(di);
    const b = instantFromParts(di + 1);
    if (b - a !== 86400n) throw new Error("día irregular");
  }
});

// --- perfil GUS-3339 (vectores completos en web/profiles-conformance.mjs) --
check("GUS-3339: época Unix (GUS 3.0.0: TAI + tabla IERS + TCJ)", () => {
  // 1970-01-01T00:00:00Z = instante GUS 62_318_160_000 + 8 410 (TAI − UTC = 10 s).
  const epochInstant = GUS_UNIX_OFFSET + 8410n;
  assertEq(instantFromRFC3339("1970-01-01T00:00:00Z").toString(), epochInstant.toString());
  assertEq(instantToRFC3339(epochInstant), "1970-01-01T00:00:00Z");
  // El segundo anterior mantiene la unidad de 1 s (sin saltos fraccionarios).
  const prev = instantFromRFC3339("1969-12-31T23:59:59Z");
  assertEq(prev.toString(), (epochInstant - 1n).toString());
  assertEq(instantToRFC3339(prev), "1969-12-31T23:59:59Z");
});

check("GUS-3339: puente GUS 3.0.0 (TCJ = TAI + 8,400 s)", () => {
  // 2026-05-23T09:30:00Z → +37 s (TAI−UTC) + 8 400 s (TCJ) → 64097697037.
  assertEq(instantFromRFC3339("2026-05-23T09:30:00Z").toString(), "64097697037");
  assertEq(instantToRFC3339(64097697037n), "2026-05-23T09:30:00Z");
  // TCJ+0 09:30:00 (= 64097688600) es 2 h 20 min 37 s antes del Z de arriba.
  assertEq(instantToRFC3339(64097688600n), "2026-05-23T07:09:23Z");
  assertEq(instantFromRFC3339("2026-05-23T07:09:23Z").toString(), "64097688600");
});

check("GUS-3339: rechaza :60, offset y minúsculas", () => {
  const bad = [
    "2026-03-17T00:00:60Z",
    "2026-03-17T00:00:00+01:00",
    "2026-03-17t00:00:00Z",
    "2026-02-30T00:00:00Z",
  ];
  for (const s of bad) {
    let threw = false;
    try {
      instantFromRFC3339(s);
    } catch (e) {
      threw = e.message.startsWith("GERO_E3339");
    }
    if (!threw) throw new Error(`pegó aceptar ${s}`);
  }
});

check("GUS-3339: origen fuera de dominio RFC 3339", () => {
  let threw = false;
  try {
    instantToRFC3339(0n);
  } catch (e) {
    threw = e.message.startsWith("GERO_E3339");
  }
  if (!threw) throw new Error("el origen GUS (año -5) no puede salir como RFC 3339");
});

// --- quickVerify (Cap 13.8 v1.2: verificación rápida O(1), vector gus-quickverify-001)
check("quickVerify: canónico pleno", () => {
  if (quickVerify("2031DY-03-08-T-09:30:00-SC-TCJ+0") !== true) throw new Error("canónico válido");
});
check("quickVerify: fecha sin hora", () => {
  if (quickVerify("2031DY-03-08-T") !== true) throw new Error("fecha de día");
});
check("quickVerify: Tempalum normal con letra V", () => {
  if (quickVerify("0031DY-00-03-V") !== true) throw new Error("Tempalum 00-03 = V");
});
check("quickVerify: AY con Tempalum GT", () => {
  if (quickVerify("0001AY-00-11-B") !== true) throw new Error("0001AY-00-11-B");
});
check("quickVerify: ciclo LC correcto con offset", () => {
  if (quickVerify("2031DY-03-08-T-21:45:10-LC-TCJ+3") !== true) throw new Error("21:45 LC");
});
check("quickVerify: tolerancia de espacios", () => {
  if (quickVerify("2031DY-03-08 T 09:30:00 SC TCJ+0") !== true) throw new Error("REGLA 1");
});
check("quickVerify detecta letra manipulada", () => {
  if (quickVerify("2031DY-03-08-S-09:30:00-SC-TCJ+0") !== false) throw new Error("letra S != T");
});
check("quickVerify detecta ciclo manipulado", () => {
  if (quickVerify("2031DY-03-08-T-21:45:10-SC-TCJ+0") !== false) throw new Error("21:45 declarado SC");
});
check("quickVerify detecta hora 25", () => {
  if (quickVerify("2031DY-03-08-T-25:00:00-SC-TCJ+0") !== false) throw new Error("hora 25");
});
check("quickVerify detecta :60", () => {
  if (quickVerify("2031DY-03-08-T-09:30:60-SC-TCJ+0") !== false) throw new Error("segundo intercalar");
});
check("quickVerify detecta día 31", () => {
  if (quickVerify("2031DY-02-31-A") !== false) throw new Error("todos los meses tienen 30 días");
});
check("quickVerify detecta Tempalum fantasma", () => {
  if (quickVerify("2031DY-00-05-S") !== false) throw new Error("año normal: Tempalum 1-4");
});
check("quickVerify rechaza era asumida", () => {
  if (quickVerify("31-03-08-T") !== false) throw new Error("era DY asumida");
});
check("quickVerify detecta mes 13", () => {
  if (quickVerify("2031DY-13-01-S") !== false) throw new Error("mes fuera de rango");
});

// --- reporte --------------------------------------------------------------
function report() {
  const lines = [
    `GUS vectores normativos: ${passed} pasan, ${failed} fallan`,
    ...failures.map((f) => `  FALLA ${f}`),
  ];
  return lines.join("\n");
}

export { report, passed, failed };

if (typeof process !== "undefined" && process.argv[1] && process.argv[1].endsWith("tests.mjs")) {
  console.log(report());
  process.exit(failed > 0 ? 1 : 0);
}
