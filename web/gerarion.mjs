// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
/**
 * Núcleo Gerarion GUS 2.0 — port exacto de src/gerarion/calendar.py + format.py
 *
 * Aritmética entera exacta (acumulador solar en microdías). BigInt solo donde
 * el rango lo exige (instantes): el resto cabe en Number con garantía de
 * exactitud entera (días e índices < 2^53).
 *
 * Misma matriz de vectores normativos que la suite de Python.
 */

export const ORIGIN_JDN = 1719313;
export const SOLAR_DELTA_UD = 1242190;
export const SOLAR_THRESHOLD_UD = 7000000;
export const MONTH_BLOCK_DAYS = 360;
export const SECS_PER_DAY = 86400;

// tercer elemento: posicion en el ciclo de 7 dias (NO dia civil)
export const WEEKDAYS = [
  ["Soludyia", "S", "día 1 del ciclo"],
  ["Loondyia", "L", "día 2 del ciclo"],
  ["Mardyia", "M", "día 3 del ciclo"],
  ["Aisterdyia", "A", "día 4 del ciclo"],
  ["Trustdyia", "T", "día 5 del ciclo"],
  ["Viendyia", "V", "día 6 del ciclo"],
  ["Sabatyeh", "B", "día 7 del ciclo"],
];

export const MONTHS = {
  0: ["Tempalum", "Cierre del año"],
  1: ["Keuphero", "Aries · Equinoccio Norte"],
  2: ["Duphilus", "Tauro · Ascenso 2"],
  3: ["Tritom", "Géminis · Ascenso 3"],
  4: ["Andra", "Cáncer · Solsticio Norte"],
  5: ["Quintob", "Leo · Afelio"],
  6: ["Hexohan", "Virgo · Ecuatorial"],
  7: ["Barseti", "Libra · Equinoccio Sur"],
  8: ["Omary", "Escorpio · Meridión"],
  9: ["Novat", "Sagitario · Nuevo ciclo"],
  10: ["Deshimo", "Capricornio · Solsticio Sur"],
  11: ["Duitades", "Acuario · Perihelio"],
  12: ["Ichtys", "Piscis · Retorno Ecuatorial"],
};

const GT_CACHE = new Map();

/**
 * Acumulador solar simétrico (spec GUS 2.1 §3), O(1), todo entero year.
 *
 *   r_y = ((year % U) + U) % U   // módulo euclidiano (JS trunca hacia 0)
 *   r   = (r_y * S) % U
 *   es Gran Tempalum <=> r + S >= U
 *
 * Igual bit a bit a la recurrencia iterativa para year >= 0 y extendida
 * hacia el pasado: los años AY con GT empiezan en -1, -6, -12, -17, ...
 */
export function isGranTempalum(year) {
  if (GT_CACHE.has(year)) return GT_CACHE.get(year);
  const rY = ((year % SOLAR_THRESHOLD_UD) + SOLAR_THRESHOLD_UD) % SOLAR_THRESHOLD_UD;
  const r = (rY * SOLAR_DELTA_UD) % SOLAR_THRESHOLD_UD;
  const isGt = r + SOLAR_DELTA_UD >= SOLAR_THRESHOLD_UD;
  GT_CACHE.set(year, isGt);
  return isGt;
}

export function yearLength(year) {
  return isGranTempalum(year) ? 371 : 364;
}

export function tempalumDays(year) {
  return yearLength(year) === 371 ? 11 : 4;
}

export function jdn(year, month, day) {
  const a = Math.floor((14 - month) / 12);
  const y = year + 4800 - a;
  const m = month + 12 * a - 3;
  return day + Math.floor((153 * m + 2) / 5) + 365 * y + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400) - 32045;
}

export function jdnToGregorian(j) {
  const a = j + 68569;
  const b = Math.floor((4 * a) / 146097);
  const c = a - Math.floor((146097 * b + 3) / 4);
  const d = Math.floor((4000 * (c + 1)) / 1461001);
  const e = c - Math.floor((1461 * d) / 4) + 31;
  const f = Math.floor((80 * e) / 2447);
  const day = e - Math.floor((2447 * f) / 80);
  const g = Math.floor(f / 11);
  const month = f + 2 - 12 * g;
  const year = 100 * (b - 49) + d + g;
  return [year, month, day];
}

export function dayIndexFromGregorian(year, month, day) {
  return jdn(year, month, day) - ORIGIN_JDN;
}

export function gregorianFromDayIndex(dayIndex) {
  return jdnToGregorian(ORIGIN_JDN + dayIndex);
}

/**
 * Inicio del año Gerarion, O(1) y simétrico (spec GUS 2.1 §3):
 * con q = floor(year / U), r = year mod U (euclidiano):
 *   gt_count = q*S + floor(r*S / U)
 *   year_start_day_index = year*364 + 7*gt_count
 * ysi(0) = 0; ysi(-1) = -371 (0001AY es Gran Tempalum).
 */
export function yearStartDayIndex(year) {
  const q = Math.floor(year / SOLAR_THRESHOLD_UD);
  const r = year - q * SOLAR_THRESHOLD_UD;
  const gtCount = q * SOLAR_DELTA_UD + Math.floor((r * SOLAR_DELTA_UD) / SOLAR_THRESHOLD_UD);
  return year * 364 + 7 * gtCount;
}

export function toGerarion(dayIndex) {
  // Inversa simétrica (spec GUS 2.1 §3): estimación con la longitud media
  // exacta de año (364 + 7*S/U días) y corrección monotónica con
  // yearStartDayIndex O(1); usa la duración real de cada año (364 o 371)
  // en ambas eras.
  let year, rest;
  if (dayIndex === 0) {
    year = 0; rest = 0;
  } else {
    year = Math.floor((dayIndex * SOLAR_THRESHOLD_UD) / (364 * SOLAR_THRESHOLD_UD + 7 * SOLAR_DELTA_UD));
    while (yearStartDayIndex(year) > dayIndex) year--;
    while (yearStartDayIndex(year + 1) <= dayIndex) year++;
    rest = dayIndex - yearStartDayIndex(year);
  }
  let month, day;
  if (rest < MONTH_BLOCK_DAYS) {
    month = Math.floor(rest / 30) + 1;
    day = (rest % 30) + 1;
  } else {
    month = 0;
    day = rest - MONTH_BLOCK_DAYS + 1;
  }
  const weekdayIndex = ((dayIndex % 7) + 7) % 7;
  const wd = WEEKDAYS[weekdayIndex];
  return { year, month, day, dayIndex, weekdayIndex, weekday: wd[0], abbr: wd[1] };
}

export function fromGerarion(year, month, day) {
  if (month === 0) {
    const max = tempalumDays(year);
    if (day < 1 || day > max) {
      const kind = max === 11 ? "es" : "no es";
      throw new GeroError(`GERO_ETEMPALUM: Tempalum día ${day} inválido: el año ${year} ${kind} Gran Tempalum`);
    }
  } else if (month >= 1 && month <= 12) {
    if (day < 1 || day > 30) throw new GeroError(`GERO_EINVAL: día ${day} fuera de rango 1..30`);
  } else {
    throw new GeroError(`GERO_EINVAL: mes ${month} fuera de rango 0..12`);
  }
  const offset = (month === 0 ? MONTH_BLOCK_DAYS : (month - 1) * 30) + (day - 1);
  return toGerarion(yearStartDayIndex(year) + offset);
}

export class GeroError extends Error {}

/*(mm) Formato canónico: AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O] */
const TS_RE =
  /^(\d{1,6})(DY|AY)?[-.](\d{1,2})[-.](\d{1,2})[-.]([SLMATVB])(?:[-](\d{1,2}):(\d{1,2}):(\d{1,2})[-](SC|LC)[-]TCJ([+-]\d{1,2}))?$/;

/** Normaliza: mayúsculas, separadores homogéneos (reglas 1, 6). */
export function normalize(raw) {
  return raw.trim().toUpperCase().replace(/\s+/g, "-").replace(/\./g, "-");
}

export function parse(raw, { strictWeekday = false } = {}) {
  const clean = normalize(raw);
  const m = TS_RE.exec(clean);
  if (!m) throw new GeroError(`GERO_EINVAL: sintaxis inválida: ${raw}`);
  const flags = [];
  let year = parseInt(m[1], 10);
  let era = m[2];
  if (!era) {
    flags.push("era_assumed_DY");
    era = "DY";
  }
  if (era === "AY") year = -year;
  const month = parseInt(m[3], 10);
  const day = parseInt(m[4], 10);
  const declared = m[5];
  const gdate = fromGerarion(year, month, day);
  if (WEEKDAYS[gdate.weekdayIndex][1] !== declared) {
    if (strictWeekday) throw new GeroError(`GERO_EWEEK: letra declarada ${declared} != calculada ${WEEKDAYS[gdate.weekdayIndex][1]}`);
    flags.push("weekday_corrected");
  }
  let hour = 0, minute = 0, second = 0, cycle = null, offset = 0;
  if (m[6] !== undefined) {
    hour = parseInt(m[6], 10);
    minute = parseInt(m[7], 10);
    second = parseInt(m[8], 10);
    if (hour > 23 || minute > 59 || second > 59) throw new GeroError("GERO_EINVAL: hora fuera de rango");
    offset = m[10] ? parseInt(m[10], 10) : 0;
    const expected = cycleOf(hour);
    if (m[9]) {
      cycle = expected;
      if (m[9] !== expected) flags.push("cycle_corrected");
    } else {
      cycle = expected;
    }
  }
  return { ...gdate, hour, minute, second, cycle, offset, flags };
}

export function cycleOf(hour) {
  if (hour < 0 || hour > 23) throw new GeroError("GERO_EINVAL: hora fuera de rango 0..23");
  return hour >= 6 && hour < 18 ? "SC" : "LC";
}

export function canonicalOf(d) {
  const era = d.year >= 0 ? "DY" : "AY";
  const yy = Math.abs(d.year);
  let base = `${String(yy).padStart(4, "0")}${era}-${String(d.month).padStart(2, "0")}-${String(d.day).padStart(2, "0")}-${d.abbr}`;
  if (d.cycle) {
    base += `-${String(d.hour).padStart(2, "0")}:${String(d.minute).padStart(2, "0")}:${String(d.second).padStart(2, "0")}-${d.cycle}-TCJ${d.offset >= 0 ? "+" : ""}${d.offset}`;
  } else if (d.hour !== undefined && (d.hour || d.minute || d.second)) {
    const cyc = cycleOf(d.hour);
    base += `-${String(d.hour).padStart(2, "0")}:${String(d.minute).padStart(2, "0")}:${String(d.second).padStart(2, "0")}-${cyc}-TCJ+0`;
  }
  return base;
}

/** Instante continuo (BigInt): sin segundos intercalares. Valida rangos. */
export function instantFromParts(dayIndex, hour = 0, minute = 0, second = 0) {
  if (!Number.isInteger(hour) || !Number.isInteger(minute) || !Number.isInteger(second) ||
      hour < 0 || hour > 23 || minute < 0 || minute > 59 || second < 0 || second > 59) {
    throw new GeroError("GERO_EINVAL: hora/minuto/segundo fuera de rango");
  }
  return BigInt(dayIndex) * BigInt(SECS_PER_DAY) + BigInt(hour * 3600 + minute * 60 + second);
}

export function tempalumName(date) {
  if (date.month !== 0) return null;
  const names = tempalumDays(date.year) === 11
    ? ["Unictis", "Kindom", "Iki", "Ikiyeh", "Nuvivid I", "Nuvivid II", "Nuvivid III", "Nuvivid IV", "Nuvivid V", "Nuvivid VI", "Nuvivid VII"]
    : ["Unictis", "Kindom", "Iki", "Ikiyeh"];
  return names[date.day - 1];
}

// ---------------------------------------------------------------------------
// Perfil GUS-3339: instante GUS <-> RFC 3339 UTC (perfil estricto)
// Documento normativo: docs/profiles/gus-3339-perfil.md / docs/en/profiles/.
// Vectores: vectors/gus-3339-001.json. Espejo exacto de profiles.py.
// ---------------------------------------------------------------------------

/** JDN (gregoriano proleptico) del 1970-01-01. */
export const UNIX_EPOCH_JDN = 2440588;

/** Instante GUS de 1970-01-01T00:00:00Z = (2440588 - 1719313) * 86400. */
export const GUS_UNIX_OFFSET = BigInt((UNIX_EPOCH_JDN - ORIGIN_JDN) * SECS_PER_DAY);

const R3339_RE = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z$/;

/** Lanza GeroError("GERO_E3339: ...") si el stamp está fuera de perfil. */
function assertProfile(ok, msg) {
  if (!ok) throw new GeroError(`GERO_E3339: ${msg}`);
}

/** Instante GUS → "AAAA-MM-DDTHH:MM:SSZ" (o GERO_E3339 fuera del dominio 0000..9999). */
export function instantToRFC3339(instant) {
  const unix = BigInt(instant) - GUS_UNIX_OFFSET;
  let days = unix / BigInt(SECS_PER_DAY);           // truncado; floor manual:
  let rem = unix % BigInt(SECS_PER_DAY);
  if (rem < 0n) { days -= 1n; rem += BigInt(SECS_PER_DAY); }
  const [year, month, day] = jdnToGregorian(UNIX_EPOCH_JDN + Number(days));
  if (year < 0 || year > 9999) {
    throw new GeroError(`GERO_E3339: instante fuera del dominio RFC 3339 (año ${year})`);
  }
  const hour = Number(rem / 3600n);
  const minute = Number((rem % 3600n) / 60n);
  const second = Number(rem % 60n);
  const pad = (n, w = 2) => String(n).padStart(w, "0");
  return `${pad(year, 4)}-${pad(month)}-${pad(day)}T${pad(hour)}:${pad(minute)}:${pad(second)}Z`;
}

/** "AAAA-MM-DDTHH:MM:SSZ" (perfil estricto: solo Z, sin offsets, sin :60) → instante BigInt. */
export function instantFromRFC3339(stamp) {
  const m = R3339_RE.exec(stamp);
  assertProfile(m !== null, `sintaxis fuera de perfil: ${JSON.stringify(stamp)}`);
  const [year, month, day, hour, minute, second] = m.slice(1).map(Number);
  // F1: la hora no se normaliza nunca; campos fuera de rango se rechazan.
  if (hour > 23 || minute > 59 || second > 59) {
    throw new GeroError(
      `GERO_E3339: campo horario fuera de rango (00-23:59:59): ${stamp}`
    );
  }
  if (second === 60) {
    throw new GeroError(
      "GERO_E3339: :60 (segundo intercalar UTC) no pertenece a la escala GUS; conviértelo a etiqueta UTC/Unix antes (MUST del perfil)"
    );
  }
  const j = jdn(year, month, day);
  const back = jdnToGregorian(j);
  assertProfile(back[0] === year && back[1] === month && back[2] === day,
    `fecha inválida: ${JSON.stringify(stamp)}`);
  return (
    BigInt(j - UNIX_EPOCH_JDN) * BigInt(SECS_PER_DAY) +
    BigInt(hour * 3600 + minute * 60 + second) +
    GUS_UNIX_OFFSET
  );
}
