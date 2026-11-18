// SPDX-License-Identifier: MIT OR Apache-2.0
// Adapter for the atlas. The upstream calendar engines are deliberately unmodified.
import {
  ORIGIN_JDN,
  WEEKDAYS,
  MONTHS,
  SECS_PER_DAY,
  jdn,
  jdnToGregorian,
  toGerarion,
  fromGerarion,
  yearLength,
  yearStartDayIndex,
  tempalumDays,
  parse,
  canonicalOf,
  instantFromUnix,
  instantToRFC3339,
} from "./gerarion.mjs";
import {
  INPUT_MODES,
  gusView,
  civilWeekday,
  jdnToJulian,
  jdnToEgyptian,
  jdnToEthiopic,
  jdnToBahai,
  jdnToMaya,
  EGYPT_MONTHS,
  ETHIOPIC_MONTHS,
  BAHAI_MONTHS,
  BAHAI_EPOCH_JDN,
  intlCalendar,
  isHebrewLeap,
} from "./calendars.mjs";

import { REFERENCE, observe } from "./zonas-tcj.mjs";

export const ES_MONTHS = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];
const HEBREW = [
  "",
  "Nisán",
  "Iyar",
  "Siván",
  "Tamuz",
  "Av",
  "Elul",
  "Tishrei",
  "Jeshván",
  "Kislev",
  "Tévet",
  "Shevat",
  "Adar",
  "Adar II",
];
export const pad = (n, l = 2) => String(n).padStart(l, "0");
export const fmt = (n) => new Intl.NumberFormat("es-CL").format(n);
export const cap = (t) => t.charAt(0).toUpperCase() + t.slice(1);
export const era = (y) => (y < 0 ? "AY" : "DY");
export const civilYear = (y) => (y <= 0 ? `${1 - y} a. C.` : String(y));
const emod = (x, n) => ((x % n) + n) % n;
export const iso = (y, m, d) =>
  `${y < 0 ? "-" : ""}${pad(Math.abs(y), 4)}-${pad(m)}-${pad(d)}`;
export const todayJdn = (now = new Date(), zone = REFERENCE) =>
  observe(Number(now), zone).jdn;
export const civil = (j) => {
  const [year, month, day] = jdnToGregorian(j);
  return {
    year,
    month,
    day,
    iso: iso(year, month, day),
    weekday: civilWeekday(j),
    label: `${day} de ${ES_MONTHS[month - 1]} de ${civilYear(year)}`,
    short: `${day} ${ES_MONTHS[month - 1].slice(0, 3)} ${civilYear(year)}`,
  };
};
export function facts(j) {
  const di = j - ORIGIN_JDN,
    g = gusView(di),
    length = yearLength(g.year),
    ordinal = di - yearStartDayIndex(g.year) + 1;
  return {
    ...g,
    granTempalum: length === 371,
    jdn: j,
    civil: civil(j),
    era: era(g.year),
    yearLabel: `${Math.abs(g.year)} ${era(g.year)}`,
    length,
    ordinal,
    pct: Math.round((ordinal / length) * 100),
  };
}

// Ten calendar families, eleven concrete input/output variants (two Hijri variants).
const META = {
  gero: ["Gerarion", "Estándar GUS", "brand", "clay"],
  greg: ["Gregoriano", "Calendario solar", "globe", "sage"],
  julian: ["Juliano", "Calendario solar", "columns", "olive"],
  maya: ["Maya", "Cuenta larga", "pyramid", "clay"],
  hebrew: ["Hebreo", "Calendario lunisolar", "hexagram", "violet"],
  egyptian: ["Egipcio", "Calendario de Nabonassar", "obelisk", "gold"],
  ethiopic: ["Etíope", "Amete Mihret", "sun", "clay"],
  bahai: ["Bahá’í", "Calendario badí‘", "flower", "sage"],
  islamicCivil: [
    "Islámico civil",
    "Calendario lunar tabular",
    "moon",
    "violet",
  ],
  islamicUmalqura: [
    "Islámico Umm al-Qura",
    "Calendario lunar",
    "moon",
    "olive",
  ],
  chinese: ["Chino", "Calendario lunisolar", "lantern", "gold"],
};
export const modes = Object.keys(META);
export const metadata = (id) => {
  const [title, family, icon, tone] = META[id];
  return { id, title, family, icon, tone };
};
export const modeHint = (id) =>
  ({
    gero: "Sello GUS: año, era, mes, día y letra. La hora TCJ es opcional.",
    greg: "AAAA-MM-DD. Para fechas anteriores a la era común, usa años astronómicos con signo.",
    jdn: "Número de día juliano entero, por ejemplo 2461363.",
    maya: "Baktún.katún.tun.uinal.kin, por ejemplo 13.0.0.0.0.",
    auto: "Marca GUS, AAAA-MM-DD, cuenta larga maya o terna juliana.",
  })[id] ||
  INPUT_MODES[id]?.hint ||
  "";

export function equivalent(id, j, stamp = null) {
  const meta = metadata(id),
    row = (value, raw, note) => ({ ...meta, value, raw, note, ok: true });
  const unavailable = (note) => ({
    ...meta,
    value: "Fuera de cobertura",
    raw: "",
    note,
    ok: false,
  });
  if (id === "gero") {
    const g = facts(j);
    return row(
      g.canonical,
      stamp || g.canonical,
      `${g.weekday} · ${g.monthName}. Aritmética entera del núcleo GUS.`,
    );
  }
  if (id === "greg") {
    const d = civil(j);
    return row(
      d.short,
      d.iso,
      `${d.weekday}. Calendario gregoriano proléptico; la entrada admite el año astronómico cero.`,
    );
  }
  if (id === "julian") {
    const d = jdnToJulian(j);
    return row(
      `${d.day} ${ES_MONTHS[d.month - 1].slice(0, 3)} ${civilYear(d.year)}`,
      `${d.year} ${d.month} ${d.day}`,
      "Conversión aritmética entera con JDN. No se aplica el salto de la reforma gregoriana.",
    );
  }
  if (id === "maya") {
    const d = jdnToMaya(j),
      v = [d.baktun, d.katun, d.tun, d.uinal, d.kin].join(".");
    return row(
      v,
      v,
      `Correlación GMT: 584283. ${fmt(d.days)} días desde 0.0.0.0.0.`,
    );
  }
  if (id === "egyptian") {
    const d = jdnToEgyptian(j);
    return row(
      `${d.day} ${EGYPT_MONTHS[d.month - 1]} · ${d.year} Nab.`,
      `${d.year} ${d.month} ${d.day}`,
      `Doce meses de 30 días y cinco epagómenos. Época: JDN 1448638.${d.year <= 0 ? " Extensión proléptica." : ""}`,
    );
  }
  if (id === "ethiopic") {
    const d = jdnToEthiopic(j);
    return row(
      `${d.day} ${ETHIOPIC_MONTHS[d.month - 1]} · ${d.year} EC`,
      `${d.year} ${d.month} ${d.day}`,
      `Doce meses de 30 días y Pagume, de cinco o seis días.${d.year <= 0 ? " Extensión proléptica." : ""}`,
    );
  }
  if (id === "bahai") {
    if (j < BAHAI_EPOCH_JDN)
      return unavailable(
        "La fecha precede al inicio de la era bahá’í (21 de marzo de 1844).",
      );
    const d = jdnToBahai(j);
    return row(
      `${d.day} ${BAHAI_MONTHS[d.month]} · ${d.year} BE`,
      `${d.year} ${d.month} ${d.day}`,
      d.approx
        ? "Fuera de la tabla UHJ se usa el 21 de marzo para Naw-Rúz. Resultado aproximado."
        : "Naw-Rúz determinado por la tabla UHJ del núcleo Gerarion.",
    );
  }
  const calendarId = {
    hebrew: "hebrew",
    islamicCivil: "islamic-civil",
    islamicUmalqura: "islamic-umalqura",
    chinese: "chinese",
  }[id];
  try {
    if (
      new Intl.DateTimeFormat("en", { calendar: calendarId }).resolvedOptions()
        .calendar !== calendarId
    )
      return unavailable("Este navegador no ofrece este calendario.");
  } catch {
    return unavailable("Este calendario no está disponible en Intl.");
  }
  const d = intlCalendar(j, id);
  if (!d.ok) return unavailable(d.note);
  const raw = `${d.year} ${d.month} ${d.day}${d.leapMonth ? " bis" : ""}`;
  if (id === "hebrew")
    return row(
      `${d.day} ${d.month === 12 && isHebrewLeap(d.year) ? "Adar I" : HEBREW[d.month]} ${d.year}`,
      raw,
      "Año Anno Mundi. Cálculo de ICU; las fechas anteriores a su uso histórico son prolépticas.",
    );
  if (id === "chinese")
    return row(
      `${d.day}/${d.month}${d.leapMonth ? " bis" : ""} · ${d.year}`,
      raw,
      "Día / mes · año relacionado. Aproximación astronómica de ICU; cobertura histórica orientativa: 1900–2100.",
    );
  return row(
    `${d.day}/${d.month}/${d.year} AH`,
    raw,
    id === "islamicCivil"
      ? "Variante civil tabular calculada por Intl/ICU. No representa una observación local de la luna."
      : "Tablas Umm al-Qura de ICU, aproximadamente 1900–2074. Fuera del intervalo, el resultado es aproximado.",
  );
}
export const equivalents = (j, stamp = null) =>
  modes.map((id) => equivalent(id, j, stamp));

export function parseSource(id, input) {
  const t = String(input ?? "").trim();
  if (!t || t.length > 150)
    throw Error("Introduce una fecha de hasta 150 caracteres.");
  if (id === "auto")
    id = /(DY|AY)/i.test(t)
      ? "gero"
      : /^-?\d{1,6}-\d{1,2}-\d{1,2}$/.test(t)
        ? "greg"
        : /^-?\d+(\.\d+){4}$/.test(t)
          ? "maya"
          : "julian";
  let j,
    stamp = null,
    normalized = t,
    warning = "";
  if (id === "jdn") {
    if (!/^-?\d{1,9}$/.test(t))
      throw Error("Introduce un JDN entero, sin puntos de miles.");
    j = Number(t);
  } else if (id === "gero") {
    const p = parse(t);
    j = ORIGIN_JDN + p.dayIndex;
    normalized = canonicalOf(p);
    if (p.hasTime) stamp = normalized;
    if (p.flags.length)
      warning =
        "El motor normalizó la era, la letra del día o el ciclo del sello.";
  } else if (!Object.hasOwn(INPUT_MODES, id))
    throw Error("Calendario no reconocido.");
  else {
    let nums = [];
    if (id === "greg") {
      const m = /^(-?\d{1,6})-(\d{1,2})-(\d{1,2})$/.exec(t);
      if (!m) throw Error("Usa AAAA-MM-DD; por ejemplo, 2026-11-18.");
      nums = m.slice(1).map(Number);
    } else if (id === "maya") {
      if (!/^-?\d{1,6}(?:[.\s]+\d{1,2}){4}$/.test(t))
        throw Error("Usa cinco números separados por puntos: 13.0.0.0.0.");
      nums = t.split(/[.\s]+/).map(Number);
      if (nums.slice(1).some((n, i) => n > (i === 2 ? 17 : 19)))
        throw Error("Katún, tun y kin admiten 0–19; uinal admite 0–17.");
    } else {
      const m =
        /^(-?\d{1,6})[\s,./]+(\d{1,2})[\s,./]+(\d{1,2})(?:\s+(bis))?$/i.exec(t);
      if (!m || (m[4] && id !== "chinese"))
        throw Error("Usa «año mes día» con números enteros.");
      nums = m.slice(1, 4).map(Number);
      if (id === "bahai" && nums[0] < 1)
        throw Error("La era bahá’í comienza en el año 1 BE.");
    }
    const res = INPUT_MODES[id].toJdn(t);
    j = res.jdn;
    const inverse = {
      greg: (k) => {
        const [year, month, day] = jdnToGregorian(k);
        return { year, month, day };
      },
      julian: jdnToJulian,
      egyptian: jdnToEgyptian,
      ethiopic: jdnToEthiopic,
      bahai: jdnToBahai,
    }[id];
    if (inverse) {
      const d = inverse(j);
      if (d.year !== nums[0] || d.month !== nums[1] || d.day !== nums[2])
        throw Error(
          "Esta fecha no existe en el calendario seleccionado. Revisa el mes y el día.",
        );
    }
  }
  if (
    !Number.isSafeInteger(j) ||
    Math.abs(j) > 368000000 ||
    Math.abs(toGerarion(j - ORIGIN_JDN).year) > 999999
  )
    throw Error("Fecha fuera del rango de seis dígitos del atlas GUS.");
  return { jdn: j, source: id, text: normalized, stamp, warning };
}

// Every endpoint is interpreted through a validated canonical GUS date.
export const endpoints = modes.filter((id) => id !== "gero");
export function interpret(source, text, target) {
  if (!endpoints.includes(target))
    throw Error("Elige un calendario de destino.");
  const input = parseSource(source, text);
  const canonical = canonicalOf(toGerarion(input.jdn - ORIGIN_JDN));
  const pivot = parse(canonical, { strictWeekday: true });
  const pivotJdn = ORIGIN_JDN + pivot.dayIndex;
  if (pivotJdn !== input.jdn)
    throw Error("La fecha no supera la comprobación de ida y vuelta GUS.");
  return {
    input,
    canonical,
    dayIndex: pivot.dayIndex,
    jdn: pivotJdn,
    output: equivalent(target, pivotJdn),
  };
}

export function monthGeometry(j, system = "gero") {
  if (system === "greg") {
    const d = civil(j),
      start = j - d.day + 1,
      next = jdn(
        d.year + (d.month === 12 ? 1 : 0),
        d.month === 12 ? 1 : d.month + 1,
        1,
      );
    return {
      start,
      length: next - start,
      first: emod(start, 7),
      day: d.day,
      title: cap(ES_MONTHS[d.month - 1]),
      yearLabel: civilYear(d.year),
      week: ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
      fullWeek: [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
      ],
    };
  }
  const g = toGerarion(j - ORIGIN_JDN),
    start = j - g.day + 1;
  return {
    start,
    length: g.month === 0 ? tempalumDays(g.year) : 30,
    first: toGerarion(start - ORIGIN_JDN).weekdayIndex,
    day: g.day,
    title: MONTHS[g.month][0],
    yearLabel: `${Math.abs(g.year)} ${era(g.year)}`,
    week: WEEKDAYS.map((w) => w[0].slice(0, 3)),
    fullWeek: WEEKDAYS.map((w) => w[0]),
  };
}
export function monthGrid(j, system = "gero") {
  const m = monthGeometry(j, system),
    count = Math.ceil((m.first + m.length) / 7) * 7,
    cells = [];
  for (let i = 0; i < count; i++) {
    const k = m.start - m.first + i,
      g = toGerarion(k - ORIGIN_JDN),
      c = civil(k);
    const special = [0, 1].includes(g.month)
      ? gusView(k - ORIGIN_JDN).special
      : null;
    cells.push({
      jdn: k,
      special,
      day: system === "gero" ? g.day : c.day,
      sub:
        system === "gero"
          ? `${c.day} ${ES_MONTHS[c.month - 1].slice(0, 3)}`
          : `${g.day} ${MONTHS[g.month][0].slice(0, 3)}`,
      label: `${g.day} de ${MONTHS[g.month][0]}, ${Math.abs(g.year)} ${era(g.year)}; ${c.label}`,
      outside: k < m.start || k >= m.start + m.length,
      selected: k === j,
    });
  }
  return { ...m, cells };
}
// Step over the end of the actual month, including 12 → 00 → 01 and both eras.
export function shiftMonth(j, delta, system = "gero") {
  const m = monthGeometry(j, system),
    next = monthGeometry(delta < 0 ? m.start - 1 : m.start + m.length, system);
  return next.start + Math.min(m.day, next.length) - 1;
}
export const yearStartJdn = (j) => {
  const g = toGerarion(j - ORIGIN_JDN);
  return ORIGIN_JDN + fromGerarion(g.year, 1, 1).dayIndex;
};
export function ntpStamp(ms) {
  const unix = Math.floor(ms / 1000),
    seconds = unix + 2208988800,
    whole = emod(seconds, 2 ** 32),
    fraction = Math.floor((emod(ms, 1000) * 2 ** 32) / 1000);
  return {
    era: Math.floor(seconds / 2 ** 32),
    whole,
    fraction,
    hex: `${whole.toString(16).padStart(8, "0").toUpperCase()}.${fraction.toString(16).padStart(8, "0").toUpperCase()}`,
  };
}
export function clockSample(ms = Date.now(), zone = REFERENCE) {
  const unix = Math.floor(ms / 1000),
    instant = instantFromUnix(BigInt(unix));
  const ref = observe(ms, REFERENCE, instant),
    seen = zone === REFERENCE ? ref : observe(ms, zone, instant);
  return {
    ms,
    unix,
    instant,
    p: ref.p,
    tcj: ref.time,
    ref,
    seen,
    stamp: canonicalOf(ref.p),
    rfc: instantToRFC3339(instant),
    ntp: ntpStamp(ms),
  };
}
export function interval(a, b) {
  const days = b - a;
  return {
    days,
    weeks: Math.trunc(Math.abs(days) / 7),
    remainder: Math.abs(days) % 7,
    seconds: BigInt(days) * BigInt(SECS_PER_DAY),
  };
}
export const milestones = [
  {
    title: "El origen Gerarion",
    tag: "Punto de partida",
    mark: "0000DY-01-01-S",
    icon: "brand",
    desc: "El primer Soludyia: el día cero desde el que se cuentan todos los demás.",
  },
  {
    title: "Inicio de 2031 DY",
    tag: "Inicio de año",
    mark: "2031DY-01-01-S",
    icon: "sun",
    desc: "Keuphero abre el ciclo anual de 2031 DY, el 17 de marzo de 2026 gregoriano.",
  },
  {
    title: "Cruxyphi",
    tag: "Día especial",
    mark: "2031DY-01-12-T",
    icon: "orbit",
    desc: "El duodécimo día de Keuphero, una de las fechas con nombre propio del calendario.",
  },
  {
    title: "Nuvivid VII",
    tag: "Gran Tempalum",
    mark: "0001AY-00-11-B",
    icon: "moon",
    desc: "El undécimo día de Tempalum cierra el año 1 AY, justo antes del origen.",
  },
  {
    title: "Cleopatra",
    tag: "Hito del portal",
    mark: "0064AY-11-12-A",
    icon: "obelisk",
    desc: "Una referencia histórica del portal original para explorar las conversiones en la era AY.",
  },
  {
    title: "Younger Dryas",
    tag: "Tiempo profundo",
    mark: "12000AY-01-01-S",
    icon: "layers",
    desc: "Un punto de exploración del atlas en la prehistoria; no es una datación exacta del episodio climático.",
  },
];
