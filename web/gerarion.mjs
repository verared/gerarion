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
  /^(\d{1,6})(DY|AY)?[-.](\d{1,2})[-.](\d{1,2})[-.]([SLMATVB])(?:[-](\d{1,2}):(\d{1,2}):(\d{1,2})[-](SC|LC)[-]TCJ(?:0(?![0-9])|([+-])(\d{1,2})(?::(\d{2}))?))?$/;

/*(mm) Formato COMPACTO (Cap 13.1): AAAAYY-MM-DD-X-HHMMSS-CC-TCJ±O */
const TS_COMPACT_RE =
  /^(\d{1,6})(DY|AY)?[-.](\d{1,2})[-.](\d{1,2})[-.]([SLMATVB])(?:[-](\d{2})(\d{2})(\d{2})[-](SC|LC)[-]TCJ(?:0(?![0-9])|([+-])(\d{1,4})))?$/;

/** Normaliza: mayúsculas, separadores homogéneos (reglas 1, 6). */
export function normalize(raw) {
  return raw.trim().toUpperCase().replace(/\s+/g, "-").replace(/\./g, "-");
}

export function parse(raw, { strictWeekday = false } = {}) {
  const clean = normalize(raw);
  let m = TS_RE.exec(clean);
  let compact = false;
  if (!m) { m = TS_COMPACT_RE.exec(clean); compact = true; }
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
  let hour = 0, minute = 0, second = 0, cycle = null, offset = 0, offsetSeconds = 0;
  const gi = (i) => (m[i] !== undefined ? parseInt(m[i], 10) : null);
  if (m[6] !== undefined) {
    hour = parseInt(m[6], 10);
    minute = compact ? parseInt(m[7], 10) : gi(7);
    second = compact ? parseInt(m[8], 10) : gi(8);
    if (hour > 23 || minute > 59 || second > 59) throw new GeroError("GERO_EINVAL: hora fuera de rango");
    // offset TCJ±O con minutos (TODO-004, GUS 3.0.0): TCJ0 | ±H(H)[:MM] | ±HMM/±HHMM
    if (compact) {
      const sgn = m[10];
      if (sgn === undefined) offsetSeconds = 0;              // TCJ0
      else {
        const d = m[11];
        const [h, mi] = d.length <= 2 ? [parseInt(d, 10), 0]
          : d.length === 3 ? [parseInt(d[0], 10), parseInt(d.slice(1), 10)]
          : [parseInt(d.slice(0, 2), 10), parseInt(d.slice(2), 10)];
        if (h > 23 || mi > 59) throw new GeroError(`GERO_EINVAL: offset TCJ fuera de rango: TCJ${sgn}${d}`);
        offsetSeconds = (sgn === "-" ? -1 : 1) * (h * 3600 + mi * 60);
      }
    } else {
      if (m[10] === undefined || m[10] === "0") offsetSeconds = 0;   // sin offset / TCJ0 / TCJ+0
      else {
        const h = gi(11), mi = m[12] !== undefined ? parseInt(m[12], 10) : 0;
        if (h > 23 || mi > 59) throw new GeroError(`GERO_EINVAL: offset TCJ fuera de rango: TCJ${m[10]}${h}:${String(mi).padStart(2, "0")}`);
        offsetSeconds = (m[10] === "-" ? -1 : 1) * (h * 3600 + mi * 60);
      }
    }
    offset = offsetSeconds % 3600 === 0 && offsetSeconds !== 0 ? offsetSeconds / 3600 : 0;
    const expected = cycleOf(hour);
    const declaredCycle = compact ? m[9] : m[9];
    if (declaredCycle) {
      cycle = expected;
      if (declaredCycle !== expected) flags.push("cycle_corrected");
    } else {
      cycle = expected;
    }
  }
  return { ...gdate, hour, minute, second, cycle, offset, offsetSeconds, hasTime: m[6] !== undefined, compact, flags };
}

/** Verificación rápida de consistencia interna, O(1) y sin red (Cap 13.8 v1.2).
 *  true solo si la marca es válida tal cual, sin correcciones silenciosas
 *  (era asumida, letra Nuvid o ciclo declarados equivocados). Filtro barato
 *  para logs e IoT; no sustituye a parse + verificación de firma. */
export function quickVerify(raw) {
  try {
    const p = parse(raw, { strictWeekday: true });
    return p.flags.length === 0;
  } catch {
    return false;
  }
}

export function cycleOf(hour) {
  if (hour < 0 || hour > 23) throw new GeroError("GERO_EINVAL: hora fuera de rango 0..23");
  return hour >= 6 && hour < 18 ? "SC" : "LC";
}

/* TCJ±O textual — canónico SIEMPRE extendido (GUS 3.0.0): TCJ+0 / TCJ+2 / TCJ-2:20 */
export function formatOffset(offsetSeconds) {
  if (offsetSeconds === 0 || offsetSeconds === undefined) return "TCJ+0";
  const sign = offsetSeconds < 0 ? "-" : "+";
  const a = offsetSeconds < 0 ? -offsetSeconds : offsetSeconds;
  const h = Math.trunc(a / 3600), m = Math.trunc((a % 3600) / 60);
  return m ? `TCJ${sign}${h}:${String(m).padStart(2, "0")}` : `TCJ${sign}${h}`;
}

export function canonicalOf(d) {
  const era = d.year >= 0 ? "DY" : "AY";
  const yy = Math.abs(d.year);
  let base = `${String(yy).padStart(4, "0")}${era}-${String(d.month).padStart(2, "0")}-${String(d.day).padStart(2, "0")}-${d.abbr}`;
  const offSec = d.offsetSeconds !== undefined ? d.offsetSeconds
    : (d.offset !== undefined && d.offset !== 0 ? d.offset * 3600 : 0);
  if (d.cycle) {
    base += `-${String(d.hour).padStart(2, "0")}:${String(d.minute).padStart(2, "0")}:${String(d.second).padStart(2, "0")}-${d.cycle}-${formatOffset(offSec)}`;
  } else if (d.hasTime || (d.hour !== undefined && (d.hour || d.minute || d.second))) {
    const cyc = d.cycle || cycleOf(d.hour);
    base += `-${String(d.hour).padStart(2, "0")}:${String(d.minute).padStart(2, "0")}:${String(d.second).padStart(2, "0")}-${cyc}-${formatOffset(offSec)}`;
  }
  return base;
}

/** Formato COMPACTO (Cap 13.1): HHMMSS + TCJ0/TCJ±H/TCJ±HMM */
export function compactOf(d) {
  const era = d.year >= 0 ? "DY" : "AY";
  const yy = Math.abs(d.year);
  let base = `${String(yy).padStart(4, "0")}${era}-${String(d.month).padStart(2, "0")}-${String(d.day).padStart(2, "0")}-${d.abbr}`;
  const offSec = d.offsetSeconds !== undefined ? d.offsetSeconds
    : (d.offset !== undefined && d.offset !== 0 ? d.offset * 3600 : 0);
  const cyc = d.cycle || (d.hour !== undefined ? cycleOf(d.hour) : null);
  if (!cyc) return base;
  let tcj;
  if (offSec === 0) tcj = "TCJ0";
  else {
    const sign = offSec < 0 ? "-" : "+";
    const a = offSec < 0 ? -offSec : offSec;
    const h = Math.trunc(a / 3600), m = Math.trunc((a % 3600) / 60);
    tcj = m ? (h < 10 ? `TCJ${sign}${h}${String(m).padStart(2, "0")}` : `TCJ${sign}${h}${m}`) : `TCJ${sign}${h}`;
  }
  return `${base}-${String(d.hour).padStart(2, "0")}${String(d.minute).padStart(2, "0")}${String(d.second).padStart(2, "0")}-${cyc}-${tcj}`;
}

/**
 * Instante continuo TCJ (GUS 3.0.0, Cap 13.1, BigInt): sin segundos
 * intercalares internos.
 * instant = dayIndex*86400 + h*3600 + m*60 + s - offsetSeconds
 * (la hora HH:MM:SS es hora civil del OBSERVADOR; offsetSeconds = TCJ±O).
 */
export function instantFromParts(dayIndex, hour = 0, minute = 0, second = 0, offsetSeconds = 0) {
  if (!Number.isInteger(hour) || !Number.isInteger(minute) || !Number.isInteger(second) ||
      hour < 0 || hour > 23 || minute < 0 || minute > 59 || second < 0 || second > 59) {
    throw new GeroError("GERO_EINVAL: hora/minuto/segundo fuera de rango");
  }
  if (!Number.isInteger(offsetSeconds) || offsetSeconds % 60 !== 0 ||
      offsetSeconds < -86400 || offsetSeconds > 86400) {
    throw new GeroError("GERO_EINVAL: TCJ±O fuera de rango o con segundos (mul. de 60, ±24 h)");
  }
  return BigInt(dayIndex) * BigInt(SECS_PER_DAY) + BigInt(hour * 3600 + minute * 60 + second - offsetSeconds);
}

/** Vista TCJ+0 de un instante: fecha Gerarion + hora civil (espejo de calendar.instant_parts). */
export function instantParts(instant) {
  const t = BigInt(instant);
  const day = t < 0n ? -((-t) / BigInt(SECS_PER_DAY)) : t / BigInt(SECS_PER_DAY);
  let rem = t % BigInt(SECS_PER_DAY);
  if (rem < 0n) rem += BigInt(SECS_PER_DAY);
  const hour = Number(rem / 3600n);
  const minute = Number((rem % 3600n) / 60n);
  const second = Number(rem % 60n);
  const date = toGerarion(Number(day));
  return { ...date, hour, minute, second, cycle: cycleOf(hour), offset: 0, offsetSeconds: 0 };
}

/** Vista del observador TCJ±O de un instante (suma offset y descompone). */
export function partsFromInstant(instant, offsetSeconds = 0) {
  const p = instantParts(BigInt(instant) + BigInt(offsetSeconds));
  p.offsetSeconds = offsetSeconds;
  return p;
}

// ---------------------------------------------------------------------------
// Capa 0 — TAI (tabla IERS) y Capa 1 — TCJ = TAI + 8 400 s (Cap 7/Cap 13)
// ---------------------------------------------------------------------------

/** TCJ = TAI + 8 400 s (meridiano de Jerusalén, 31.7683°N 35.2137°E). */
export const TCJ_OFFSET_SECONDS = 8400;

/** Tabla histórica TAI − UTC (IERS): [unix_utc_inicio, offset_vigente]. */
export const TAI_MINUS_UTC_TABLE = [
  [-378691200, 10],  // 1958-01-01 (convención declarada, no medida)
  [63072000, 10],    // 1972-01-01 (base UTC)
  [78796800, 11], [94694400, 12], [126230400, 13], [157766400, 14],
  [189302400, 15], [220924800, 16], [252460800, 17], [283996800, 18],
  [315532800, 19], [362793600, 20], [394329600, 21], [425865600, 22],
  [489024000, 23], [567993600, 24], [631152000, 25], [662688000, 26],
  [709948800, 27], [741484800, 28], [773020800, 29], [820454400, 30],
  [867715200, 31], [915148800, 32], [1136073600, 33], [1230768000, 34],
  [1341100800, 35], [1435708800, 36], [1483228800, 37],
];

/** Offset TAI − UTC vigente para un segundo Unix UTC (pre-1958: 0 s). */
export function taiMinusUTC(unixSeconds) {
  let current = 0;
  for (const [epoch, off] of TAI_MINUS_UTC_TABLE) {
    if (unixSeconds >= epoch) current = off; else break;
  }
  return current;
}

/** Unix (UTC) → instante GUS: unix → TAI → TCJ (+8400) → GUS. */
export function instantFromUnix(unixSeconds) {
  const u = BigInt(unixSeconds);
  return u + BigInt(taiMinusUTC(u)) + BigInt(TCJ_OFFSET_SECONDS) + GUS_UNIX_OFFSET;
}

/** Instante GUS → Unix UTC (exacto, inversa por segmentos de la tabla). */
export function unixFromInstant(instant) {
  const tai = BigInt(instant) - GUS_UNIX_OFFSET - BigInt(TCJ_OFFSET_SECONDS);
  const epochs = TAI_MINUS_UTC_TABLE.map(([e]) => e);
  const offs = [0, ...TAI_MINUS_UTC_TABLE.map(([, o]) => o)];
  for (let i = 0; i < offs.length; i++) {
    const low = i > 0 ? BigInt(epochs[i - 1]) : -(2n ** 62n);
    const high = i < epochs.length ? BigInt(epochs[i]) : 2n ** 62n;
    const utc = tai - BigInt(offs[i]);
    if (utc >= low && utc < high) return utc;
  }
  return tai;
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
// Vectores: vectors/gus-3339-002.json. Espejo exacto de profiles.py.
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

/** Instante GUS → "AAAA-MM-DDTHH:MM:SSZ" (perfil 3339; GUS → TCJ → TAI → UTC, tabla IERS). */
export function instantToRFC3339(instant) {
  const unix = unixFromInstant(instant);
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
  const unix =
    BigInt(j - UNIX_EPOCH_JDN) * BigInt(SECS_PER_DAY) +
    BigInt(hour * 3600 + minute * 60 + second);
  return instantFromUnix(unix); // GUS 3.0.0: unix → TAI (tabla IERS) → TCJ → GUS
}
