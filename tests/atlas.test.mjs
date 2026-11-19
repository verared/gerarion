// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
// Suite del adaptador del atlas: 40 pruebas, sin dependencias externas.
// Ejecutar: node --test tests/atlas.test.mjs (desde la raíz del repositorio).
import test from "node:test";
import assert from "node:assert/strict";

import {
  ES_MONTHS,
  pad,
  fmt,
  era,
  civilYear,
  civil,
  facts,
  todayJdn,
  modes,
  metadata,
  modeHint,
  equivalent,
  equivalents,
  parseSource,
  endpoints,
  interpret,
  monthGrid,
  shiftMonth,
  yearStartJdn,
  ntpStamp,
  clockSample,
  interval,
  milestones,
} from "../web/ui/atlas.mjs";
import {
  REFERENCE,
  territories,
  zoneCount,
  zoneInfo,
  zoneDelta,
  deltaLabel,
  zoneGroups,
  observe,
  supportedZone,
  civilOffset,
} from "../web/engine/zonas-tcj.mjs";
import { ORIGIN_JDN, parse as parseGus } from "../web/gerarion.mjs";

// Gregoriano proléptico → JDN, año astronómico.
const J = (y, m, d) => {
  const a = Math.floor((14 - m) / 12),
    y2 = y + 4800 - a;
  return (
    d +
    Math.floor((153 * (m + 12 * a - 3) + 2) / 5) +
    365 * y2 +
    Math.floor(y2 / 4) -
    Math.floor(y2 / 100) +
    Math.floor(y2 / 400) -
    32045
  );
};
const dj = (s) => ORIGIN_JDN + parseGus(s).dayIndex;
const NOV18 = J(2026, 11, 18); // 2031DY-09-07-L, el día de referencia del rediseño

test("1 · el origen GUS es 0000DY-01-01-S (Keuphero)", () => {
  const f = facts(ORIGIN_JDN);
  assert.equal(f.canonical, "0000DY-01-01-S");
  assert.equal(f.year, 0);
  assert.equal(f.month, 1);
  assert.equal(f.day, 1);
  assert.equal(f.monthName, "Keuphero");
});

test("2 · equivalencia gregoriana del origen, proléptica con año astronómico", () => {
  assert.equal(civil(ORIGIN_JDN).iso, "-0005-03-21");
  assert.match(civil(ORIGIN_JDN).label, /a\. C\./);
});

test("3 · round-trip civil → JDN → civil en fechas crucibles", () => {
  for (const [y, m, d] of [
    [2026, 3, 17],
    [2000, 2, 29],
    [1900, 3, 1],
    [2100, 2, 28],
  ]) {
    const j = J(y, m, d);
    const back = civil(j);
    const esperado = `${y < 0 ? "-" : ""}${pad(Math.abs(y), 4)}-${pad(m)}-${pad(d)}`;
    assert.equal(back.iso, esperado, `${y}-${m}-${d}`);
  }
});

test("4 · 2026-03-17 abre el año 2031 DY (1 de Keuphero, Soludyia)", () => {
  const g = facts(J(2026, 3, 17));
  assert.equal(g.canonical, "2031DY-01-01-S");
  assert.equal(g.monthName, "Keuphero");
  assert.equal(g.ordinal, 1);
  assert.equal(g.pct, 0);
});

test("5 · Nuvivid VII es 0001AY-00-11-B, víspera del origen", () => {
  const f = facts(dj("0001AY-00-11-B"));
  assert.equal(f.canonical, "0001AY-00-11-B");
  assert.equal(f.special, "Nuvivid VII");
  assert.equal(f.jdn, ORIGIN_JDN - 1);
});

test("6 · Nuvivid III: 2030-03-14 → 2034DY-00-07-M en un año Gran Tempalum", () => {
  const f = facts(J(2030, 3, 14));
  assert.equal(f.canonical, "2034DY-00-07-M");
  assert.equal(f.special, "Nuvivid III");
  assert.equal(f.granTempalum, true);
});

test("7 · los meses 01 a 12 duran exactamente 30 días", () => {
  for (const m of [1, 6, 12]) {
    const y = 2031,
      start = dj(`2031DY-${pad(m)}-01-S`);
    assert.equal(facts(start).month, m);
    assert.equal(facts(start + 29).day, 30);
  }
});

test("8 · el año normal dura 364 días y el Gran Tempalum 371", () => {
  const normal = parseGus("2031DY-01-01-S").dayIndex,
    nextNormal = parseGus("2032DY-01-01-S").dayIndex;
  assert.equal(nextNormal - normal, 364);
  const gt = parseGus("2034DY-01-01-S").dayIndex,
    afterGt = parseGus("2035DY-01-01-S").dayIndex;
  assert.equal(afterGt - gt, 371);
  assert.ok(facts(dj("2034DY-00-06-M")).granTempalum, "Tempalum de 2034 marcado como GT");
  assert.ok(!facts(dj("2031DY-00-03-M")).granTempalum, "Tempalum de 2031 no es GT");
});

test("9 · Tempalum tiene 11 días solo en años Gran Tempalum; día 7 no-GT lanza GERO_ETEMPALUM", () => {
  assert.equal(dj("2034DY-00-11-T"), dj("2035DY-01-01-S") - 1);
  assert.equal(dj("2031DY-00-04-M"), dj("2032DY-01-01-S") - 1);
  assert.throws(() => parseGus("2031DY-00-07-T"), /GERO_ETEMPALUM/);
});

test("10 · cruce de eras: la víspera de 0000DY-01-01-S es un día AY de Tempalum", () => {
  const prev = facts(ORIGIN_JDN - 1);
  assert.match(prev.canonical, /^0001AY-00-/);
  assert.equal(prev.era, "AY");
});

test("11 · la letra del día rota S L M A T V B desde el origen", () => {
  const letters = ["S", "L", "M", "A", "T", "V", "B"];
  for (let i = 0; i < 7; i++) {
    const f = facts(ORIGIN_JDN + i);
    assert.equal(f.canonical.at(-1), letters[i]);
  }
});

test("12 · un sello con hora se conserva como dato adjunto, con ciclo y TCJ+0", () => {
  const r = parseSource("gero", "2031DY-03-08-T-09:30:00-SC-TCJ+0");
  assert.equal(r.jdn, facts(J(2026, 5, 23)).jdn);
  assert.equal(r.stamp, "2031DY-03-08-T-09:30:00-SC-TCJ+0");
});

test("13 · entrada GUS imposible: mes 13 lanza GERO_EINVAL, nunca un silencio", () => {
  assert.throws(() => parseSource("gero", "2031DY-13-08-T"), /GERO_EINVAL/);
  assert.equal(parseSource("gero", "2031DY-12-30-V").jdn, dj("2031DY-12-30-V"));
});

test("14 · detección automática clasifica GUS, ISO, maya y juliano", () => {
  assert.equal(parseSource("auto", "2031DY-01-01-S").source, "gero");
  assert.equal(parseSource("auto", "2026-03-17").source, "greg");
  assert.equal(parseSource("auto", "13.0.0.0.0").source, "maya");
  assert.equal(parseSource("auto", "2026 11 18").source, "julian");
});

test("15 · entrada vacía o excesiva se rechaza con mensaje claro", () => {
  assert.throws(() => parseSource("greg", ""), /150/);
  assert.throws(() => parseSource("greg", "9".repeat(200)), /150/);
});

test("16 · una fecha civil inexistente (2026-02-30) lanza error en vez de normalizar", () => {
  assert.throws(() => parseSource("greg", "2026-02-30"), /no existe|Rango|mes|día/i);
});

test("17 · once variantes corresponden a diez familias externas + Gerarion", () => {
  assert.equal(endpoints.length, 10);
  const fams = new Set(endpoints.map((id) => metadata(id).family));
  assert.equal(fams.size, 8, `familias={${[...fams]}}`);
  for (const id of endpoints) {
    const m = metadata(id);
    assert.ok(m.title && m.icon && m.tone, id);
    assert.ok(typeof modeHint(id) === "string" && modeHint(id).length > 5, id);
  }
});

test("18 · equivalents() devuelve 11 fichas todas cubiertas en una fecha moderna", () => {
  const list = equivalents(NOV18);
  assert.equal(list.length, 11);
  assert.equal(list.filter((x) => x.ok).length, 11);
  assert.ok(list.some((x) => x.id === "gero"));
});

test("19 · maya GMT 584283: 21-12-2012 = 13.0.0.0.0", () => {
  const m = equivalent("maya", J(2012, 12, 21));
  assert.equal(m.raw, "13.0.0.0.0");
  assert.ok(m.ok);
});

test("20 · JDN: ceros de miles y no-numéricos se rechazan con ejemplo", () => {
  assert.throws(() => parseSource("jdn", "2.461.363"), /JDN/);
  assert.throws(() => parseSource("jdn", "2461363.5"), /JDN/);
  assert.equal(parseSource("jdn", "2461363").jdn, NOV18);
});

test("21 · interpret(): cualquier ruta A → Gerarion → B conserva el día", () => {
  for (const t of ["greg", "maya", "julian", "ethiopic"]) {
    const src = equivalent(t, NOV18);
    if (!src.ok) continue;
    const r = interpret(t, src.raw, "julian");
    assert.equal(r.jdn, NOV18, t);
    assert.ok(r.output.ok, t);
  }
});

test("22 · round-trip inverso en las diez variantes reproduce el JDN", () => {
  for (const id of endpoints) {
    const src = equivalent(id, NOV18);
    if (!src.ok) continue;
    const back = parseSource(id, src.raw);
    // ICU puede reformatear, pero el día proyectado no cambia.
    assert.equal(back.jdn, NOV18, id);
  }
});

test("23 · interpret() con destino imposible lanza un error del dominio", () => {
  assert.throws(() => interpret("greg", "2026-13-01", "maya"), /no existe|calendario|Fecha|fecha/i);
});

test("24 · facts() llena la ficha completa del día", () => {
  const f = facts(NOV18);
  for (const k of [
    "canonical",
    "weekday",
    "weekdayAbbr",
    "monthName",
    "monthGloss",
    "granTempalum",
    "year",
    "month",
    "day",
    "dayIndex",
    "jdn",
    "civil",
    "era",
    "yearLabel",
    "length",
    "ordinal",
    "pct",
  ])
    assert.ok(f[k] !== undefined && f[k] !== null && f[k] !== "", k);
  assert.equal(f.canonical, "2031DY-09-07-L");
  assert.equal(f.civil.iso, "2026-11-18");
});

test("25 · canon SIEMPRE: año de 4 dígitos, mes/día a 2, letra de semana", () => {
  for (const s of ["0000DY-01-01-S", "0001AY-00-11-B", "9999DY-12-30-B"]) {
    const f = facts(dj(s));
    assert.match(f.canonical, /^\d{4}(DY|AY)-\d{2}-\d{2}-[SLMATVB]$/, s);
  }
});

test("26 · monthGrid: múltiplo de 7, día seleccionado único fuera/incluido", () => {
  for (const sys of ["gero", "greg"]) {
    for (const j of [NOV18, ORIGIN_JDN + 380]) {
      const grid = monthGrid(j, sys);
      assert.equal(grid.cells.length % 7, 0, sys);
      assert.ok(grid.cells.length >= 28 && grid.cells.length <= 42, sys);
      assert.equal(grid.cells.filter((c) => c.jdn === j).length, 1, sys);
      const sel = grid.cells.find((c) => c.selected);
      assert.equal(sel.jdn, j, sys);
      for (const c of grid.cells)
        assert.ok(c.day >= 1 && c.day <= (sys === "gero" ? 30 : 31), sys);
    }
  }
});

test("27 · la cuadrícula anota la sub-lectura cruzada y la cabecera de semana", () => {
  const gero = monthGrid(NOV18, "gero"),
    greg = monthGrid(NOV18, "greg");
  assert.equal(gero.week.length, 7);
  assert.equal(greg.week.length, 7);
  assert.match(gero.title, /Novat/);
  assert.match(greg.title, /Noviembre/);
  // En la vista gregoriana, la línea inferior es la lectura GUS.
  const cell = greg.cells.find((c) => !c.outside && c.day === 18);
  assert.equal(cell.sub, "7 Nov");
  assert.match(cell.label, /Novat/);
});

test("28 · shiftMonth va y vuelve al mismo JDN en ambos sistemas", () => {
  for (const sys of ["gero", "greg"]) {
    for (const j of [NOV18, dj("2034DY-00-11-T")]) {
      const fwd = shiftMonth(j, 1, sys);
      assert.notEqual(fwd, j, sys);
      assert.equal(shiftMonth(fwd, -1, sys), j, sys);
    }
  }
});

test("29 · shiftMonth atraviesa 12 → 00 → 01 y el cambio de era", () => {
  const dec = shiftMonth(dj("2031DY-12-15-V"), 1, "gero");
  assert.equal(facts(dec).month, 0);
  const gtEnd = shiftMonth(dj("2034DY-00-11-T"), 1, "gero");
  assert.equal(facts(gtEnd).month, 1);
  const gregDec = shiftMonth(J(2026, 12, 15), 1, "greg");
  assert.equal(civil(gregDec).iso.slice(5, 7), "01");
});

test("30 · yearStartJdn cae en el 01-01 de GUS (17-03-2026 civil)", () => {
  const gs = yearStartJdn(NOV18),
    f = facts(gs);
  assert.equal(f.month, 1);
  assert.equal(f.day, 1);
  assert.equal(f.year, 2031);
  assert.equal(civil(gs).iso, "2026-03-17");
});

test("31 · perfil RFC 3339: sufijo Z, segundos exactos, sin :60", () => {
  const s = clockSample(Date.UTC(2026, 10, 18, 15, 0, 0), REFERENCE);
  assert.match(s.rfc, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/);
  assert.equal(s.rfc, "2026-11-18T15:00:00Z");
});

test("32 · Unix, sello GUS y lectura TCJ son coherentemente el mismo instante", () => {
  const ms = Date.UTC(2026, 10, 18, 15, 0, 0),
    s = clockSample(ms, REFERENCE);
  assert.equal(s.unix, 1795014000);
  assert.equal(s.stamp, "2031DY-09-07-L-17:20:37-SC-TCJ+0");
  assert.equal(s.seen.time, "17:20:37");
  assert.equal(s.ref.time, "17:20:37");
});

test("33 · marca NTP: era 0, hex 8+8 con la época de 1900", () => {
  const s = ntpStamp(Date.UTC(2026, 10, 18, 15, 0, 0));
  assert.equal(s.era, 0);
  assert.match(s.hex, /^[0-9A-F]{8}\.[0-9A-F]{8}$/);
  assert.equal(s.whole, 1795014000 + 2208988800);
});

test("34 · el rollo de 2036: la era sigue creciendo en vez de reiniciar", () => {
  const before = ntpStamp(Date.UTC(2036, 1, 6, 6, 28, 15));
  const after = ntpStamp(Date.UTC(2036, 4, 7));
  assert.equal(before.era, 0);
  assert.equal(after.era, 1);
  assert.ok(after.whole < before.whole + 2 ** 32);
});

test("35 · interval(): días positivos, negativos y cero", () => {
  const fwd = interval(NOV18, NOV18 + 1);
  assert.equal(fwd.days, 1);
  assert.equal(interval(NOV18 + 1, NOV18).days, -1);
  assert.equal(interval(NOV18, NOV18).days, 0);
  assert.equal(interval(NOV18, NOV18 + 3).days, 3);
});

test("36 · segundos convencionales = 86400 por día, sin segundos intercalares", () => {
  const n = interval(J(1950, 1, 1), J(2000, 1, 1));
  assert.equal(n.days, 18262);
  assert.equal(Number(n.seconds), 18262 * 86400);
  assert.equal(n.weeks, Math.floor(18262 / 7));
  assert.equal(n.remainder, 18262 % 7);
});

test("37 · hitos: seis láminas, todas parseables y con icono/tag/desc", () => {
  assert.equal(milestones.length, 6);
  const seen = new Set();
  for (const m of milestones) {
    assert.ok(m.title && m.desc && m.icon && m.tag && m.mark, m.title);
    const r = parseSource("gero", m.mark);
    assert.ok(Number.isFinite(r.jdn), m.mark);
    seen.add(r.jdn);
  }
  assert.ok(seen.size >= 5, "variedad de hitos");
  // El tiempo profundo (Younger Dryas) apunta a un JDN proléptico negativo.
  assert.ok(parseSource("gero", "12000AY-01-01-S").jdn < 0);
});

test("38 · todayJdn con zona: el día observado cambia al cruzar medianoche civil", () => {
  const ms = Date.UTC(2026, 10, 18, 2, 0, 0); // 23:00 civiles en Santiago, 17-nov
  const ref = todayJdn(new Date(ms), REFERENCE),
    santiago = todayJdn(new Date(ms), "America/Santiago");
  // 02:00 UTC = 04:20 TCJ: amanece dentro del mismo día GUS 2031DY-09-07.
  assert.equal(ref, facts(NOV18).jdn);
  assert.equal(observe(ms, "America/Santiago").time, "23:00:00");
  assert.equal(santiago, ref - 1);
});

test("39 · zonas: catálogo, etiqueta a horas enteras y grupos sin duplicados", () => {
  assert.ok(zoneCount >= 300, `zonas=${zoneCount}`);
  assert.ok(territories.length >= 240, `territorios=${territories.length}`);
  assert.equal(deltaLabel(0), "TCJ+0");
  assert.equal(deltaLabel(-5 * 3600), "TCJ−5");
  assert.equal(deltaLabel(-(5 * 3600 + 20 * 60 + 37)), "TCJ−5");
  assert.equal(deltaLabel(3 * 3600), "TCJ+3");
  // Σ grupada = Σ registros, sin duplicados de zona.
  const groups = zoneGroups(Date.UTC(2026, 10, 18, 15, 0, 0)),
    seen = new Set();
  let withZone = 0;
  for (const g of groups) {
    for (const id of g.ids) {
      assert.ok(!seen.has(id), `duplicado: ${id}`);
      seen.add(id);
    }
    if (g.primary) assert.ok(zoneInfo(g.primary), g.primary);
  }
  for (const t of territories)
    for (const id of t.ids)
      if (supportedZone(id, Date.UTC(2026, 10, 18, 15, 0, 0))) withZone++;
  assert.equal(seen.size, withZone, "cada zona utilizable aparece exactamente una vez");
});

test("40 · agrupación civil: Santiago y Buenos Aires se unen y separan según estación", () => {
  const nov = zoneGroups(Date.UTC(2026, 10, 18, 15, 0, 0)),
    jul = zoneGroups(Date.UTC(2026, 6, 15, 15, 0, 0));
  const novRow = nov.find((g) => g.ids.includes("America/Santiago"));
  assert.ok(novRow, "Santiago presente en noviembre");
  assert.ok(novRow.ids.includes("America/Argentina/Buenos_Aires"), "agrupada con Buenos Aires");
  assert.ok(novRow.ids.includes("America/Coyhaique"), "Coyhaique comparte fila");
  assert.notEqual(fila(nov, "Pacific/Easter"), novRow, "Isla de Pascua en otra fila");
  const julRowAr = jul.find((g) => g.ids.includes("America/Argentina/Buenos_Aires")),
    julRowCl = jul.find((g) => g.ids.includes("America/Santiago"));
  assert.ok(julRowAr && julRowCl, "ambas presentes en julio");
  assert.notEqual(julRowAr, julRowCl, "en julio las reglas estacionales las separan");
  assert.ok(jul.some((g) => g.ids.length === 0 && ["Sin asignación", "No disponible"].includes(g.label)), "BV/HM sin hora inventada");
  assert.equal(civilOffset(Date.UTC(2026, 6, 15), "America/Santiago"), -4 * 3600);
  assert.equal(civilOffset(Date.UTC(2026, 6, 15), "America/Argentina/Buenos_Aires"), -3 * 3600);
  assert.throws(() => zoneDelta(Date.UTC(2026, 6, 15), "no/existe"));
  assert.equal(supportedZone("no/existe"), false);
  assert.equal(supportedZone("America/Santiago"), true);
  assert.notEqual(zoneDelta(Date.UTC(2026, 6, 15), "America/Santiago"), 0);
});

function fila(groups, id) {
  return groups.find((g) => g.ids.includes(id));
}
