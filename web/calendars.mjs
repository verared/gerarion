// calendars.mjs — Traductor cronológico universal del portal Gerarion.
//
// Pivote matemático central: el JDN (Julian Day Number, número entero) y el
// day_index GUS (day_index = jdn − ORIGIN_JDN, ORIGIN_JDN = 1719313). Todos
// los calendarios se implementan como puentes enteros exactos hacia/desde
// JDN; los calendarios presentes en Intl (hebreo, islámico civil, chino)
// usan Intl.DateTimeFormat nativo con aviso limpio fuera de rango.
//
// 100 % local, cero dependencias externas, sin punto flotante para las
// conversiones exactas (solo enteros; el Date de JS se usa únicamente como
// mensajero de milisegundos para Intl).
//
// Seguridad: sin red, sin estado persistente.

import {
  ORIGIN_JDN,
  jdn,
  jdnToGregorian,
  toGerarion,
  canonicalOf,
  tempalumName,
  MONTHS,
} from './gerarion.mjs';

// ---------------------------------------------------------------------------
// Semana civil (etiqueta persuasiva solo para humanos: el día GUS no usa
// semana civil). JDN 0 (lunes) → (jdn + 1) % 7: 0=Domingo..6=Sábado.
// ---------------------------------------------------------------------------

const CIVIL_WEEK = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];

export function civilWeekday(j) {
  return CIVIL_WEEK[(((j + 1) % 7) + 7) % 7];
}

// ---------------------------------------------------------------------------
// Gregoriano proleptico (puente directo a gerarion.mjs)
// ---------------------------------------------------------------------------

export function gregorianToJdn(y, m, d) {
  return jdn(y, m, d);
}

export function jdnToGregorianStr(j) {
  const [y, m, d] = jdnToGregorian(j);
  return { year: y, month: m, day: d, iso: `${String(y).padStart(4, '0')}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}` };
}

// ---------------------------------------------------------------------------
// Juliano (aritmético, entero exacto)
// ---------------------------------------------------------------------------

export function julianToJdn(y, m, d) {
  const a = Math.floor((14 - m) / 12);
  const y2 = y + 4800 - a;
  const m2 = m + 12 * a - 3;
  return d + Math.floor((153 * m2 + 2) / 5) + 365 * y2 + Math.floor(y2 / 4) - 32083;
}

export function jdnToJulian(j) {
  const c = j + 32082;
  const d4 = Math.floor((4 * c + 3) / 1461);
  const e = c - Math.floor((1461 * d4) / 4);
  const m = Math.floor((5 * e + 2) / 153);
  const day = e - Math.floor((153 * m + 2) / 5) + 1;
  const month = m + 3 - 12 * Math.floor(m / 10);
  const year = d4 - 4800 + Math.floor(m / 10);
  return { year, month, day };
}

// ---------------------------------------------------------------------------
// Egipcio antiguo (Vago/Alejandrino sin bisiesto): 12 × 30 + 5 epagómenos.
// Época de Nabonassar: 1 Thoth 1 = JDN 1448638 (26 feb 747 a.C. juliano).
// Meses: Thoth..Mesore; mes 13 = epagómenos. Extensión proleptica: años <= 0
// Nabonassar son convención declarada.
// ---------------------------------------------------------------------------

export const EGYPT_EPOCH_JDN = 1448638;

export const EGYPT_MONTHS = [
  'Thoth', 'Phaophi', 'Athyr', 'Choiak', 'Tybi', 'Mecheir',
  'Phamenoth', 'Pharmuthi', 'Pachon', 'Payni', 'Epiphi', 'Mesore',
  'Epagómenos',
];

export function egyptianToJdn(y, m, d) {
  return EGYPT_EPOCH_JDN + (y - 1) * 365 + (m - 1) * 30 + (d - 1);
}

export function jdnToEgyptian(j) {
  const n = j - EGYPT_EPOCH_JDN; // 0 = 1 Thoth 1 Nabonassar
  const year = Math.floor(n / 365) + 1;
  const doy = n - (year - 1) * 365; // 0..364
  if (doy >= 360) {
    return { year, month: 13, day: doy - 359, epagomenos: true };
  }
  return { year, month: Math.floor(doy / 30) + 1, day: (doy % 30) + 1, epagomenos: false };
}

// ---------------------------------------------------------------------------
// Etíope (Amete Mihret): 12 × 30 + Pagume (5 o 6 días). Años bisiestos:
// year % 4 == 3. Época: 1 Meskerem 1 = JDN 1724221 (29 ago 8 e.c. juliano).
// Meses: Meskerem..Pagume. Fuera de ~543 e.c. es extensión proleptica.
// ---------------------------------------------------------------------------

export const ETHIOPIC_EPOCH_JDN = 1724221;

export const ETHIOPIC_MONTHS = [
  'Meskerem', 'Tikimt', 'Hidar', 'Tahsas', 'Tir', 'Yekatit',
  'Megabit', 'Miyazya', 'Ginbot', 'Sene', 'Hamle', 'Nehase', 'Pagume',
];

export function isEthiopicLeap(year) {
  return ((year % 4) + 4) % 4 === 3;
}

export function ethiopicToJdn(y, m, d) {
  const ny = ETHIOPIC_EPOCH_JDN + (y - 1) * 365 + Math.floor(y / 4);
  const add = m === 13 ? 360 + (d - 1) : (m - 1) * 30 + (d - 1);
  return ny + add;
}

export function jdnToEthiopic(j) {
  const n = j - ETHIOPIC_EPOCH_JDN; // 0 en 1 Meskerem 1
  const cycle = Math.floor(n / 1461);
  const w = n - cycle * 1461; // 0..1460
  // El año bisiesto (year % 4 == 3) ocupa la 3.ª posición del ciclo:
  // posiciones de año en el ciclo: 0 [0..364], 1 [365..729],
  // 2 (bisiesto) [730..1095], 3 [1096..1460].
  let pos, doy;
  if (w <= 729) {
    pos = Math.floor(w / 365);
    doy = w - pos * 365;
  } else if (w <= 1095) {
    pos = 2;
    doy = w - 730;
  } else {
    pos = 3;
    doy = w - 1096;
  }
  const year = cycle * 4 + pos + 1;
  if (pos === 2 && doy >= 360) {
    return { year, month: 13, day: doy - 359, pagume: true };
  }
  return { year, month: Math.floor(doy / 30) + 1, day: (doy % 30) + 1 };
}

// ---------------------------------------------------------------------------
// Bahá'í (Badí'): 19 meses × 19 días + Ayyám-i-Há (4/5 días) antes de 'Alá'.
// Época: 1 Bahá 1 = JDN 2394647 (Naw-Rúz, 21 mar 1844 e.c. gregoriano).
// Convención Naw-Rúz: 21 de marzo del año gregoriano (Y + 1843); el año
// Badí' Y dura 366 días exactamente si (Y + 1843) es bisiesto gregoriano.
// Nota: la regla astronómica del Naw-Rúz vigente desde 2015 oscila 20/21
// de marzo; este portal usa la convención del 21 de marzo (sesgo ≤ 1 día).
// ---------------------------------------------------------------------------

export const BAHAI_EPOCH_JDN = 2394647;

export const BAHAI_YEAR_OFFSET = 1843; // año badí' Y inicia el 21 mar GY = Y + 1843

export const BAHAI_MONTHS = [
  'Ayyám-i-Há (intercalar)',
  'Bahá', 'Jalál', 'Jamál', 'ʿAzamat', 'Núr', 'Rahmat',
  'Kalimát', 'Kamál', 'Asmáʼ', 'ʿIzzat', 'Mashíyyat', 'ʿIlm',
  'Qudrat', 'Qawl', 'Masáʼil', 'Sharaf', 'Sultán', 'Mulk', 'ʿAláʼ',
];

function gregorianIsLeap(y) {
  return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
}

export function bahaiYearStartJdn(y) {
  // 21 de marzo gregoriano de (Y + 1843): el 1 Bahá 1 BE ancla en 1844.
  return jdn(y + BAHAI_YEAR_OFFSET, 3, 21);
}

export function bahaiToJdn(y, m, d) {
  const start = bahaiYearStartJdn(y);
  // El 29 feb dentro del año Badí' Y pertenece al GY = Y + 1844:
  let add;
  if (m === 0) {
    // Ayyám-i-Há: tras los 18 primeros meses (342 días)
    add = 342 + (d - 1);
  } else if (m === 19) {
    const leap = gregorianIsLeap(y + BAHAI_YEAR_OFFSET + 1);
    add = 342 + (leap ? 5 : 4) + (d - 1);
  } else {
    add = (m - 1) * 19 + (d - 1);
  }
  return start + add;
}

export function jdnToBahai(j) {
  // año candidato por longitud media, luego corrección monotónica
  let y = Math.floor((j - BAHAI_EPOCH_JDN) / 365.25) + 1;
  while (bahaiYearStartJdn(y) > j) y--;
  while (bahaiYearStartJdn(y + 1) <= j) y++;
  const start = bahaiYearStartJdn(y);
  const leap = gregorianIsLeap(y + BAHAI_YEAR_OFFSET + 1);
  const doy = j - start; // 0..364/365
  if (doy < 342) {
    return { year: y, month: Math.floor(doy / 19) + 1, day: (doy % 19) + 1 };
  }
  const ayhamDays = leap ? 5 : 4;
  if (doy < 342 + ayhamDays) {
    return { year: y, month: 0, day: doy - 341, ayyamiha: true };
  }
  return { year: y, month: 19, day: doy - 342 - ayhamDays + 1 };
}

// ---------------------------------------------------------------------------
// Cuenta Larga Maya — correlación GMT (584283): 0.0.0.0.0 = JDN 584283
// (11 ago 3114 a.C. gregoriano proleptico). División piso + módulo
// euclidiano: exacta también hacia el pasado.
// ---------------------------------------------------------------------------

export const MAYA_CORRELATION_JDN = 584283;

export function mayaToJdn(baktun, katun, tun, uinal, kin) {
  return MAYA_CORRELATION_JDN + baktun * 144000 + katun * 7200 + tun * 360 + uinal * 20 + kin;
}

export function jdnToMaya(j) {
  const days = j - MAYA_CORRELATION_JDN;
  const m = (x, n) => (((x % n) + n) % n);
  const kin = m(days, 20);
  const uinal = m(Math.floor(days / 20), 18);
  const tun = m(Math.floor(days / 360), 20);
  const katun = m(Math.floor(days / 7200), 20);
  const baktun = Math.floor(days / 144000); // sin módulo 20: cuenta libre
  return { baktun, katun, tun, uinal, kin, days };
}

// ---------------------------------------------------------------------------
// Calendarios Intl (hebreo, islámico civil, chino): Intl.DateTimeFormat
// nativo. Devuelve note con avisos limpios cuando la fecha está fuera del
// rango histórico que Intl soporta o del rango de Date (±~273 mil años).
// ---------------------------------------------------------------------------

const JS_DATE_MIN_JDN = Math.round(-8.64e15 / 86400000) + 2440588; // ≈ −98 000 000
const JS_DATE_MAX_JDN = Math.round(8.64e15 / 86400000) + 2440588;

export function jdnToJsDate(j) {
  // mediodía UTC del día JDN
  return new Date((j - 2440588) * 86400000 + 43200000);
}

const INTL_CALS = {
  hebrew: { locale: 'en-u-ca-hebrew', era: false },
  islamic: { locale: 'en-u-ca-islamic-civil', era: true },
  chinese: { locale: 'en-u-ca-chinese', era: false },
};

export function intlCalendar(j, which) {
  const conf = INTL_CALS[which];
  if (j < JS_DATE_MIN_JDN || j > JS_DATE_MAX_JDN) {
    return { ok: false, note: 'fuera del rango de Date (Intl no puede representarla)' };
  }
  const d = jdnToJsDate(j);
  try {
    const fmt = new Intl.DateTimeFormat(conf.locale, {
      day: 'numeric', month: 'numeric', year: 'numeric',
      ...(conf.era ? { era: 'short' } : {}),
    });
    const parts = Object.fromEntries(fmt.formatToParts(d).map((p) => [p.type, p.value]));
    // yearNum: 'year' puede venir con era SEPARADA en 'era'
    let yearNum = parseInt((parts.year || '').replace(/[^0-9]/g, ''), 10);
    if (Number.isNaN(yearNum)) yearNum = null;
    // mes bisiesto (calendario chino): month puede traer "bis"/"leap"
    const isLeapMonth = /bis|leap/i.test(parts.month || '');
    const monthNum = parseInt((parts.month || '0').replace(/[^0-9]/g, ''), 10);
    const dayNum = parseInt((parts.day || '').replace(/[^0-9]/g, ''), 10);
    const eraStr = parts.era || '';
    // Hebreo/islámico: Intl da años ≤ 0 raros o erróneos antes de sus épocas
    if (which !== 'chinese' && yearNum !== null && yearNum <= 0) {
      return { ok: false, note: 'antes de la época del calendario (Intl no lo cubre)' };
    }
    return {
      ok: true,
      year: yearNum,
      month: monthNum,
      day: dayNum,
      leapMonth: isLeapMonth,
      era: eraStr,
      text: fmt.format(d),
    };
  } catch (e) {
    return { ok: false, note: 'no soportada por Intl para esta fecha' };
  }
}

// ---------------------------------------------------------------------------
// Gerarion: vista completa de un día (usa gerarion.mjs como fuente canónica)
// ---------------------------------------------------------------------------

const SACRED_DAYS = { '1-12': 'Cruxyphi', '1-15': 'Resinove', '1-30': 'Yeshuvid' };

export function gusView(dayIndex) {
  const d = toGerarion(dayIndex);
  const canon = canonicalOf(d);
  const monthName = d.month === 0 ? 'Tempalum' : MONTHS[d.month][0];
  const monthGloss = d.month === 0 ? 'cierre del año' : MONTHS[d.month][1];
  let special = tempalumName(d);
  if (!special) {
    special = SACRED_DAYS[`${d.month}-${d.day}`] || null;
  }
  return {
    canonical: canon,
    dateCanonical: canon,
    weekday: d.weekday,
    weekdayAbbr: d.abbr,
    monthName,
    monthGloss,
    special,
    year: d.year,
    month: d.month,
    day: d.day,
    dayIndex,
  };
}
