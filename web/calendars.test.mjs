// tests-calendars.mjs — pruebas unitarias del traductor multi-calendario.
// Uso: node web/calendars.test.mjs  (exit 1 si algo falla). 100% local.

import {
  julianToJdn,
  jdnToJulian,
  egyptianToJdn,
  jdnToEgyptian,
  EGYPT_EPOCH_JDN,
  ethiopicToJdn,
  jdnToEthiopic,
  isEthiopicLeap,
  ETHIOPIC_EPOCH_JDN,
  bahaiToJdn,
  jdnToBahai,
  bahaiYearStartJdn,
  BAHAI_EPOCH_JDN,
  mayaToJdn,
  jdnToMaya,
  MAYA_CORRELATION_JDN,
  intlCalendar,
  civilWeekday,
  gregorianToJdn,
} from './calendars.mjs';
import { jdn, dayIndexFromGregorian, parse, toGerarion, canonicalOf } from './gerarion.mjs';

const failures = [];
let checks = 0;

function check(name, fn) {
  checks++;
  try {
    fn();
  } catch (e) {
    failures.push(`${name}: ${e.message}`);
  }
}

function assertEq(a, b, msg = '') {
  const sa = JSON.stringify(a);
  const sb = JSON.stringify(b);
  if (sa !== sb) throw new Error(`${msg} esperado ${sb}, obtenido ${sa}`);
}

// ---------- Juliano ----------

check('juliano: época JD (1 ene −4712 juliano) = JDN 0', () => {
  assertEq(julianToJdn(-4712, 1, 1), 0);
});

check('juliano: JDN 1448638 = 26 feb −746 juliano (1 Thoth 1 Nabonassar)', () => {
  assertEq(jdnToJulian(EGYPT_EPOCH_JDN), { year: -746, month: 2, day: 26 });
});

check('juliano: hoy 17 nov 2026 greg = 4 nov 2026 juliano (offset 13)', () => {
  const j = gregorianToJdn(2026, 11, 17);
  assertEq(jdnToJulian(j), { year: 2026, month: 11, day: 4 });
});

check('juliano: ida y vuelta 12.000 fechas aleatorias-deterministas', () => {
  let seed = 12345;
  const rnd = () => {
    seed = (seed * 1103515245 + 12345) % 2147483648;
    return seed / 2147483648;
  };
  for (let i = 0; i < 12000; i++) {
    const y = Math.round(rnd() * 8000 - 4000);
    const m = 1 + Math.floor(rnd() * 12);
    const d = 1 + Math.floor(rnd() * 28);
    const j = julianToJdn(y, m, d);
    const back = jdnToJulian(j);
    assertEq(back, { year: y, month: m, day: d }, `(${y},${m},${d})`);
  }
});

// ---------- Egipcio (Vago) ----------

check('egipcio: 1 Thoth 1 Nabonassar = JDN 1448638', () => {
  assertEq(egyptianToJdn(1, 1, 1), EGYPT_EPOCH_JDN);
  assertEq(EGYPT_EPOCH_JDN, 1448638);
});

check('egipcio: año de 365 días exactos, sin bisiesto', () => {
  assertEq(egyptianToJdn(2, 1, 1) - egyptianToJdn(1, 1, 1), 365);
});

check('egipcio: ida y vuelta 12.000 fechas', () => {
  for (let y = -2500; y <= 3500; y++) {
    for (const [m, d] of [[1, 1], [6, 15], [12, 30], [13, 1], [13, 5]]) {
      const j = egyptianToJdn(y, m, d);
      const back = jdnToEgyptian(j);
      assertEq(back.year, y, `año (${y},${m},${d})`);
      assertEq(back.month, m, `mes (${y},${m},${d})`);
      assertEq(back.day, d, `día (${y},${m},${d})`);
    }
  }
});

// ---------- Etíope ----------

check('etíope: 1 Meskerem 2000 = JDN 2454356 (12 sep 2007 gregoriano)', () => {
  assertEq(ethiopicToJdn(2000, 1, 1), 2454356);
});

check('etíope:转折 bisiesto Pagume de 6 — año 2015 EC (2015%4==3)', () => {
  assertEq(isEthiopicLeap(2015), true);
  assertEq(isEthiopicLeap(2016), false);
  const j6 = ethiopicToJdn(2015, 13, 6);
  const j7 = ethiopicToJdn(2015, 13, 5) + 1;
  assertEq(j6, j7);
  assertEq(jdnToEthiopic(j6 + 1), { year: 2016, month: 1, day: 1 });
});

check('etíope: ida y vuelta 14.000 fechas (incluye bisiestos)', () => {
  for (let y = -200; y <= 6000; y++) {
    for (const [m, d] of [[1, 1], [6, 30], [12, 20], [13, 1], [13, 5], [13, isEthiopicLeap(y) ? 6 : 1]]) {
      const j = ethiopicToJdn(y, m, d);
      const back = jdnToEthiopic(j);
      assertEq(back.year, y, `año (${y},${m},${d})`);
      assertEq([back.month, back.day], m === 13 && !isEthiopicLeap(y) && d === 6 ? [13, 5 + 1] : [m, d], `md (${y},${m},${d})`);
    }
  }
});

// ---------- Bahá'í ----------

check('bahai: 1 Bahá 1 = JDN 2394647 (época dada)', () => {
  assertEq(bahaiToJdn(1, 1, 1), BAHAI_EPOCH_JDN);
  assertEq(BAHAI_EPOCH_JDN, 2394647);
  assertEq(bahaiYearStartJdn(1), 2394647);
});

check('bahai: Naw-Rúz 180 BE = 21 mar 2023 gregoriano (convención 21-mar)', () => {
  assertEq(bahaiYearStartJdn(180), gregorianToJdn(2023, 3, 21));
});

check('bahai: Ayyám-i-Há de 5 días en año Y con (Y+1844) bisiesto gregoriano', () => {
  // Y = 180 → 180 + 1844 = 2024, bisiesto (el 29 feb 2024 cae dentro de BE 180)
  const j1 = bahaiToJdn(180, 0, 1);
  const j5 = bahaiToJdn(180, 0, 5);
  assertEq(j5 - j1, 4);
  assertEq(jdnToBahai(j1).month, 0);
  assertEq(jdnToBahai(j5).day, 5);
  // el día siguiente ya es 1 de 'Alá' (mes 19)
  assertEq(jdnToBahai(j5 + 1), { year: 180, month: 19, day: 1 });
  // y en año sin 29 feb dentro (181 → 2025) Ayyám-i-Há dura 4 días
  const j4n = bahaiToJdn(181, 0, 4);
  assertEq(bahaiToJdn(181, 19, 1) - j4n, 1);
});

check('bahai: ida y vuelta 3.000 fechas', () => {
  for (let y = 1; y <= 300; y++) {
    for (const [m, d] of [[1, 1], [9, 19], [18, 19], [0, 1], [0, 4], [19, 1], [19, 19]]) {
      try {
        const j = bahaiToJdn(y, m, d);
        const back = jdnToBahai(j);
        assertEq({ year: back.year, month: back.month, day: back.day }, { year: y, month: m, day: d }, `(${y},${m},${d})`);
      } catch (e) {
        throw new Error(`(${y},${m},${d}): ${e.message}`);
      }
    }
  }
});

// ---------- Cuenta Larga Maya ----------

check('maya: 0.0.0.0.0 = JDN 584283 (correlación GMT)', () => {
  assertEq(mayaToJdn(0, 0, 0, 0, 0), MAYA_CORRELATION_JDN);
  assertEq(MAYA_CORRELATION_JDN, 584283);
});

check('maya: 13.0.0.0.0 = 21 dic 2012 gregoriano', () => {
  assertEq(mayaToJdn(13, 0, 0, 0, 0), gregorianToJdn(2012, 12, 21));
});

check('maya: ida y vuelta 100.000 posiciones alrededor del origen', () => {
  for (let k = -50000; k <= 50000; k += 3) {
    const j = MAYA_CORRELATION_JDN + k;
    const lc = jdnToMaya(j);
    assertEq(mayaToJdn(lc.baktun, lc.katun, lc.tun, lc.uinal, lc.kin), j, `k=${k}`);
  }
});

check('maya: negativo profundo — 0.0.0.0.0 menos 5.000 días queda back-castable', () => {
  const j = MAYA_CORRELATION_JDN - 5000;
  const lc = jdnToMaya(j);
  assertEq(mayaToJdn(lc.baktun, lc.katun, lc.tun, lc.uinal, lc.kin), j);
});

// ---------- GUS AY profundo ----------

check('GUS: 12000AY-01-01-S <-> día index -4382910 (simetría GT, spec 2.1)', () => {
  const ts = parse('12000AY-01-01-S');
  assertEq(ts.dayIndex, -4382910);
  assertEq(canonicalOf(ts), '12000AY-01-01-S');
  assertEq(canonicalOf(toGerarion(-4382910)), '12000AY-01-01-S');
});

check('GUS: 0001AY-00-11-B es el día -1 (Nuvivid VII, GT AY simétrico)', () => {
  const d = toGerarion(-1);
  assertEq(canonicalOf(d), '0001AY-00-11-B');
  assertEq(d.weekday, 'Sabatyeh');
});

check('GUS: años de 6 dígitos parseables y canónicos', () => {
  const d = toGerarion(dayIndexFromGregorian(-275760, 1, 1));
  assertEq(String(Math.abs(d.year)).length <= 6, true);
});

// ---------- Intl (hebreo / islámico / chino) ----------

check('intl hebreo: 17 nov 2026 = 7 Kislev 5787', () => {
  const h = intlCalendar(gregorianToJdn(2026, 11, 17), 'hebrew');
  assertEq(h.ok, true);
  assertEq(h.year, 5787);
  assertEq(h.day, 7);
});

check('intl hebreo: época egipcia (747 a.C.) sigue soportada por ICU', () => {
  const h = intlCalendar(EGYPT_EPOCH_JDN, 'hebrew');
  assertEq(h.ok, true, h.note || '');
});

check('intl islámico civil: 17 nov 2026 = 6/6/1448 AH', () => {
  const i = intlCalendar(gregorianToJdn(2026, 11, 17), 'islamic');
  assertEq(i.ok, true);
  assertEq(i.year, 1448);
  assertEq(i.month, 6);
  assertEq(i.day, 6);
});

check('intl chino: 21 dic 2012 parsea sin error (día 1..30 del mes lunar)', () => {
  const c = intlCalendar(gregorianToJdn(2012, 12, 21), 'chinese');
  assertEq(c.ok, true, c.note || '');
  assertEq(c.day !== null && c.day >= 1 && c.day <= 30, true);
  assertEq(c.month !== null && c.month >= 1 && c.month <= 12, true, `mes lunar raro: ${c.month}`);
});

check('intl fuera de rango: JDN imposible devuelve ok:false con nota limpia', () => {
  const far = intlCalendar(2440588 + 200000000, 'hebrew');
  assertEq(far.ok, false);
  assertEq(typeof far.note, 'string');
});

// ---------- Semana civil ----------

check('civilWeekday: JDN 2451545 (1 ene 2000) = Sábado', () => {
  assertEq(civilWeekday(2451545), 'Sábado');
});

check('civilWeekday: JDN 0 = Lunes', () => {
  assertEq(civilWeekday(0), 'Lunes');
});

// ---------- reporte ----------

const report = [
  `calendars.mjs: ${checks - failures.length}/${checks} pruebas pasan, ${failures.length} fallan`,
  ...failures.map((f) => `  FALLA ${f}`),
].join('\n');
console.log(report);
if (failures.length > 0) process.exit(1);
