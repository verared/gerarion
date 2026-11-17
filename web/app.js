// app.js — Portal y Traductor Cronológico Universal Gerarion (GUS v2.1.0).
//
// Regla de seguridad: todo dato dinámico pasa por textContent — nunca
// innerHTML con datos derivados del usuario. Matemática 100 % local
// (gerarion.mjs + calendars.mjs); la página no envía ni recibe nada por red.
// Sin cookies, sin estado persistente.

import {
  ORIGIN_JDN,
  dayIndexFromGregorian,
  gregorianFromDayIndex,
  fromGerarion,
  toGerarion,
  parse,
  canonicalOf,
  cycleOf,
  tempalumDays,
  tempalumName,
  WEEKDAYS,
  MONTHS,
  GeroError,
} from './gerarion.mjs';

import {
  INPUT_MODES,
  jdnToGregorianStr,
  jdnToJulian,
  jdnToEgyptian,
  EGYPT_EPOCH_JDN,
  EGYPT_MONTHS,
  jdnToEthiopic,
  ETHIOPIC_EPOCH_JDN,
  ETHIOPIC_MONTHS,
  isEthiopicLeap,
  jdnToBahai,
  bahaiYearIsExact,
  BAHAI_EPOCH_JDN,
  BAHAI_MONTHS,
  jdnToMaya,
  MAYA_CORRELATION_JDN,
  intlCalendar,
  civilWeekday,
  gusView,
  autodetectToJdn,
} from './calendars.mjs';

import { report, failed } from './tests.mjs';

const $ = (id) => document.getElementById(id);

function pad2(n) {
  return String(n).padStart(2, '0');
}

// ---------------------------------------------------------------------------
// Enlace compartible: #cal=<modo>&d=<texto> (solo hash; ASCII en el modo;
// el texto va URL-encodeado; sin datos personales, es la consulta tuya)
// ---------------------------------------------------------------------------

let lastHashWritten = null;

function writeHash(modeId, text) {
  lastHashWritten = `#cal=${modeId}&d=${encodeURIComponent(text)}`;
  if (lastHashWritten !== location.hash) {
    history.replaceState(null, '', lastHashWritten);
  }
}

function applyHash() {
  const m = /^#cal=([a-zA-Z0-9]+)&d=(.+)$/.exec(location.hash);
  if (!m) return false;
  const mode = MODES.find((mm) => mm.id === m[1]);
  if (!mode) return false;
  let res;
  try {
    res = mode.toJdn(decodeURIComponent(m[2]));
  } catch {
    return false;
  }
  lastHashWritten = location.hash;
  setMode(mode, decodeURIComponent(m[2]));
  applyPivot(res, `enlace compartido: ${res.label}`, null);
  return true;
}

window.addEventListener('hashchange', () => {
  if (location.hash === lastHashWritten) return;
  applyHash();
});

function bindShare() {
  const btn = $('share-link');
  if (!btn) return;
  btn.addEventListener('click', () => {
    if (lastRes) writeHash(lastRes.modeId, lastRes.text);
    const url = `${location.origin}${location.pathname}${location.hash}`;
    navigator.clipboard.writeText(url).then(
      () => toast('Enlace copiado al portapapeles'),
      () => toast('No se pudo copiar el enlace'),
    );
  });
}

function todayJdnUtc() {
  const now = new Date();
  return ORIGIN_JDN + dayIndexFromGregorian(
    now.getUTCFullYear(), now.getUTCMonth() + 1, now.getUTCDate(),
  );
}

// ---------------------------------------------------------------------------
// Toast + copia
// ---------------------------------------------------------------------------

let toastTimer = null;
function toast(text) {
  let el = document.querySelector('.toast');
  if (!el) {
    el = document.createElement('div');
    el.className = 'toast';
    el.setAttribute('role', 'status');
    document.body.appendChild(el);
  }
  el.textContent = text;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 1600);
}

function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(
      () => toast('Copiado al portapapeles'),
      () => {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        ta.remove();
        toast('Copiado al portapapeles');
      },
    );
  }
}

// ---------------------------------------------------------------------------
// Contraste reforzado (accesibilidad). Sin persistencia: ni cookies ni storage.
// data-theme ausente = claro estándar; data-theme="light" = contraste alto.
// ---------------------------------------------------------------------------

function bindTheme() {
  const btn = $('theme-toggle');
  if (!btn) return;
  btn.addEventListener('click', () => {
    const forced = document.documentElement.getAttribute('data-theme') === 'light';
    if (forced) {
      document.documentElement.removeAttribute('data-theme');
      btn.setAttribute('aria-pressed', 'false');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
      btn.setAttribute('aria-pressed', 'true');
    }
  });
}

// ---------------------------------------------------------------------------
// Reloj en vivo
// Convención de la spec: el día rueda a medianoche UTC (el instante continuo
// es lineal día*86400 + h*3600 + m*60 + s); el ciclo SC/LC es solo la etiqueta
// luminosa de la hora de referencia (SC 06:00-17:59, LC 18:00-05:59, en UTC
// para el modo TCJ+0).
// ---------------------------------------------------------------------------

let clockMode = 'utc';

function clockStamp() {
  const now = new Date();
  const utcMode = clockMode === 'utc';
  const y = utcMode ? now.getUTCFullYear() : now.getFullYear();
  const mo = (utcMode ? now.getUTCMonth() : now.getMonth()) + 1;
  const d = utcMode ? now.getUTCDate() : now.getDate();
  const h = utcMode ? now.getUTCHours() : now.getHours();
  const mi = utcMode ? now.getUTCMinutes() : now.getMinutes();
  const s = utcMode ? now.getUTCSeconds() : now.getSeconds();
  const dayIndex = dayIndexFromGregorian(y, mo, d);
  const g = toGerarion(dayIndex);
  const cyc = cycleOf(h);
  const stamp = canonicalOf({ ...g, hour: h, minute: mi, second: s, cycle: cyc, offset: 0 });
  const offsetHours = utcMode ? 0 : -now.getTimezoneOffset() / 60;
  const jdnNow = ORIGIN_JDN + dayIndex;
  const instant = dayIndex * 86400 + h * 3600 + mi * 60 + s;
  return { stamp, dayIndex, jdnNow, instant, g, cyc, offsetHours, utcMode };
}

function tickClock() {
  const t = clockStamp();
  setText('now-gero', t.stamp);
  const monthName = t.g.month === 0 ? 'Tempalum' : MONTHS[t.g.month][0];
  setText(
    'now-details',
    `día ${t.dayIndex} · ${t.g.weekday} · ${monthName} (mes ${pad2(t.g.month)}) · ` +
      `ciclo ${t.cyc} · hora ${t.utcMode ? 'TCJ+0 (UTC)' : `TCJ${t.offsetHours >= 0 ? '+' : ''}${t.offsetHours} (local)`}`,
  );
  const cycEl = $('now-cycle');
  if (cycEl) {
    cycEl.textContent = t.cyc;
    cycEl.classList.toggle('is-sc', t.cyc === 'SC');
    cycEl.classList.toggle('is-lc', t.cyc === 'LC');
  }
  setText('now-dayindex', String(t.dayIndex));
  setText('now-jdn', String(t.jdnNow));
  setText('now-instant', String(t.instant));
}

function bindClock() {
  const sel = $('clock-tz');
  if (sel) {
    sel.addEventListener('change', () => {
      clockMode = sel.value;
      tickClock();
    });
    // si el offset local ya es UTC, la opción TCJ+0 es la misma hora
    const off = -(new Date().getTimezoneOffset() / 60);
    sel.options[1].textContent = `TCJ local (${off >= 0 ? '+' : ''}${off})`;
  }
  const copy = $('now-copy');
  if (copy) {
    copy.addEventListener('click', () => {
      const t = clockStamp();
      copyText(`${t.stamp} · day_index ${t.dayIndex} · JDN ${t.jdnNow} · instant ${t.instant}`);
    });
  }
  tickClock();
  setInterval(tickClock, 1000);
}

// ---------------------------------------------------------------------------
// Estado central: currentJdn alimenta la cuadrícula y el calendario mensual
// ---------------------------------------------------------------------------

let currentJdn = todayJdnUtc();
let lastRes = null; // última traducción: { modeId, text, jdn } → alimenta el enlace compartible

// ---------------------------------------------------------------------------
// Cuadrícula de calendarios (Piedra Rosetta): 10 tarjetas desde un JDN
// ---------------------------------------------------------------------------

function tileActions(el, copyVal, origin) {
  const wrap = document.createElement('div');
  wrap.className = 'cal-actions';
  if (copyVal) {
    const cp = document.createElement('button');
    cp.type = 'button';
    cp.className = 'cal-copy';
    cp.textContent = 'copiar';
    cp.setAttribute('aria-label', `Copiar ${copyVal}`);
    cp.addEventListener('click', () => copyText(copyVal));
    wrap.appendChild(cp);
  }
  if (origin) {
    const og = document.createElement('button');
    og.type = 'button';
    og.className = 'cal-origin';
    og.textContent = 'origen';
    og.title = 'Usar esta fecha como origen del traductor';
    og.setAttribute('aria-label', `Usar ${copyVal || 'esta fecha'} como origen`);
    og.addEventListener('click', () => setOrigin(origin.mode, origin.text));
    wrap.appendChild(og);
  }
  el.appendChild(wrap);
}

function tile({ title, main, sub, note, check, copyText: cval, origin, accent }) {
  const el = document.createElement('div');
  el.className = `cal-tile${accent ? ' tile-gero' : ''}`;

  const h3 = document.createElement('h3');
  h3.textContent = title;
  el.appendChild(h3);

  const mainEl = document.createElement('div');
  mainEl.className = 'cal-main';
  mainEl.textContent = main;
  el.appendChild(mainEl);

  if (sub) {
    const subEl = document.createElement('div');
    subEl.className = 'cal-sub';
    subEl.textContent = sub;
    el.appendChild(subEl);
  }
  if (note) {
    const noteEl = document.createElement('div');
    noteEl.className = 'cal-note';
    noteEl.textContent = note;
    el.appendChild(noteEl);
  }
  if (check) {
    const chk = document.createElement('div');
    chk.className = 'cal-check';
    chk.textContent = check;
    el.appendChild(chk);
  }
  tileActions(el, cval, origin);
  return el;
}

function signedYearIso(y, m, d) {
  return `${String(y).padStart(4, '0')}-${pad2(m)}-${pad2(d)}`;
}

// Texto de origen para volver a introducir la misma fecha en cada sistema.
function originFor(kind, comps) {
  return { mode: kind, text: comps };
}

function hebrewDisplay(r) {
  // r.month ya viene normalizado (12 = Adar I en bisiesto, 13 = Adar II)
  const hist = { 1: 'Tishrei', 2: 'Jeshvan', 3: 'Kislev', 4: 'Tevet', 5: 'Shevat', 6: 'Adar', 7: 'Nisán', 8: 'Iyar', 9: 'Siván', 10: 'Tamuz', 11: 'Av', 12: 'Elul' };
  let name;
  if (r.month === 13) name = 'Adar II';
  else if (r.month === 6) name = 'Adar I';
  else name = hist[r.month] || `mes ${r.month}`;
  return `${r.day} de ${name} de ${r.year} AM`;
}

function islamicDisplay(r) {
  return `${r.day}/${r.month}/${r.year} AH`;
}

function chineseDisplay(r) {
  const leap = r.leapMonth ? 'bis' : '';
  const rel = r.year !== null ? r.year : r.relatedYear;
  return `mes ${r.month}${leap} · día ${r.day} · año chino ${rel}`;
}

function renderGrid(container, jdnVal, pivotLabel) {
  container.textContent = '';
  const dayIndex = jdnVal - ORIGIN_JDN;

  // 1. GUS — marca canónica
  const gv = gusView(dayIndex);
  const gusSub = `${gv.weekday} (${gv.weekdayAbbr}) · ${gv.monthName}` +
    (gv.monthGloss ? ` — ${gv.monthGloss}` : '');
  container.appendChild(tile({
    title: 'Gerarion · GUS 2.1.0',
    main: gv.canonical,
    sub: gusSub + (gv.special ? ` · ${gv.special}` : '') +
      (gv.granTempalum ? ' · año Gran Tempalum (371 días)' : ''),
    check: `day_index ${dayIndex}${pivotLabel ? ` · ${pivotLabel}` : ''}`,
    copyText: gv.canonical,
    origin: originFor('gero', gv.canonical),
    accent: true,
  }));

  // 2. Gregoriano proléptico
  const gr = jdnToGregorianStr(jdnVal);
  container.appendChild(tile({
    title: 'Gregoriano proléptico',
    main: gr.iso,
    sub: `era ${gr.year < 0 ? `${-gr.year} a.C.` : 'e.c.'} · ${civilWeekday(jdnVal)}`,
    check: `JDN ${jdnVal}`,
    copyText: gr.iso,
    origin: originFor('greg', gr.iso),
  }));

  // 3. Juliano
  const jl = jdnToJulian(jdnVal);
  const jlText = `${jl.year} ${jl.month} ${jl.day}`;
  container.appendChild(tile({
    title: 'Juliano',
    main: signedYearIso(jl.year, jl.month, jl.day),
    sub: `${civilWeekday(jdnVal)} · año juliano`,
    check: 'exacto con JDN',
    copyText: jlText,
    origin: originFor('julian', jlText),
  }));

  // 4. Egipcio (Vago)
  const eg = jdnToEgyptian(jdnVal);
  const egMonth = eg.month === 13 ? EGYPT_MONTHS[12] : EGYPT_MONTHS[eg.month - 1];
  const egText = `${eg.year} ${eg.month} ${eg.day}`;
  container.appendChild(tile({
    title: 'Egipcio antiguo (Vago)',
    main: `${egMonth} ${eg.day} · año ${eg.year} Nab.`,
    sub: eg.epagomenos ? `${eg.day}.º epagómeno` : '12 × 30 + 5 epagómenos',
    note: eg.year <= 0 ? 'extensión proleptica (año ≤ 0 Nabonassar)' : null,
    check: `época: JDN ${EGYPT_EPOCH_JDN} (Nabonassar 1)`,
    copyText: egText,
    origin: originFor('egyptian', egText),
  }));

  // 5. Etíope
  const et = jdnToEthiopic(jdnVal);
  const etMonth = ETHIOPIC_MONTHS[et.month - 1] || '?';
  const etText = `${et.year} ${et.month} ${et.day}`;
  container.appendChild(tile({
    title: 'Etíope (Amete Mihret)',
    main: `${etMonth} ${et.day} · ${et.year} EC`,
    sub: et.pagume ? 'Pagume (mes intercalar)' : '12 × 30 + Pagume (5/6)',
    note: et.year <= 0 ? 'extensión proleptica' : null,
    check: `bisiesto EC: ${isEthiopicLeap(et.year) ? 'sí' : 'no'}`,
    copyText: etText,
    origin: originFor('ethiopic', etText),
  }));

  // 6. Bahá'í (Badí') — tabla oficial UHJ 172–221; fuera, convención 21-mar
  const bh = jdnToBahai(jdnVal);
  const bhMonth = BAHAI_MONTHS[bh.month] || '?';
  const bhText = `${bh.year} ${bh.month} ${bh.day}`;
  container.appendChild(tile({
    title: "Bahá'í (Badí')",
    main: `${bhMonth} ${bh.day} · ${bh.year} BE`,
    sub: bh.month === 0 ? 'Ayyám-i-Há (días intercalares)' : '19 × 19 + Ayyám-i-Há',
    note: bahaiYearIsExact(bh.year)
      ? 'tabla oficial UHJ: Naw-Rúz exacto'
      : 'convención Naw-Rúz = 21 de marzo (aproximada, sesgo ≤ 1 día)',
    check: `época: JDN ${BAHAI_EPOCH_JDN} (21 mar 1844)`,
    copyText: bhText,
    origin: originFor('bahai', bhText),
  }));

  // 7. Cuenta Larga Maya
  const my = jdnToMaya(jdnVal);
  const lcStr = `${my.baktun}.${my.katun}.${my.tun}.${my.uinal}.${my.kin}`;
  container.appendChild(tile({
    title: 'Cuenta Larga Maya',
    main: lcStr,
    sub: `${my.days.toLocaleString('es')} días desde 0.0.0.0.0`,
    note: my.days < 0 ? 'antes de la correlación GMT (proleptico)' : 'correlación GMT (584283)',
    check: '13.0.0.0.0 = 21 dic 2012',
    copyText: lcStr,
    origin: originFor('maya', lcStr),
  }));

  // 8. Hebreo / 9. Islámico / 10. Chino — Intl nativo con inverso verificado
  const intlTiles = [
    ['hebrew', 'Hebreo', 'cuenta Anno Mundi (ICU; Adar II = mes 13 en bisiesto)', hebrewDisplay, 'hebrew'],
    ['islamicCivil', 'Islámico (civil)', 'Hijri tabular con JDN (exacto en todo el rango Date)', islamicDisplay, 'islamicCivil'],
    ['chinese', 'Chino', 'lunar; aprox. astronómica de ICU; fiable ≈ 1900–2100', chineseDisplay, 'chinese'],
  ];
  for (const [which, title, enumNote, display, modeId] of intlTiles) {
    const r = intlCalendar(jdnVal, which);
    if (r.ok) {
      let text;
      try {
        text = display(r);
      } catch {
        text = r.text;
      }
      const origText = which === 'chinese'
        ? `${r.year} ${r.month} ${r.day}${r.leapMonth ? ' bis' : ''}`
        : `${r.year} ${r.month} ${r.day}`;
      container.appendChild(tile({
        title,
        main: text,
        sub: [
          r.era ? `era ${r.era}` : null,
          r.leapMonth ? 'mes bisiesto' : null,
        ].filter(Boolean).join(' · ') || null,
        note: r.note ? `nota: ${r.note}` : null,
        check: `${enumNote} · conversión inversa verificada con Intl`,
        copyText: origText,
        origin: originFor(modeId === 'islamicCivil' ? 'islamicCivil' : modeId, origText),
      }));
    } else {
      container.appendChild(tile({
        title,
        main: '—',
        sub: 'fecha no representable en este calendario',
        note: r.note || null,
        check: enumNote,
        copyText: null,
        origin: null,
      }));
    }
  }
}

// ---------------------------------------------------------------------------
// Traductor universal: modos (datasource única: INPUT_MODES de calendars.mjs)
// ---------------------------------------------------------------------------

const MODES = Object.values(INPUT_MODES);

let currentMode = MODES[0];

function setMode(mode, value = '') {
  currentMode = mode;
  const modeRow = $('uni-modes');
  for (const btn of modeRow.children) {
    const active = btn.dataset.mode === mode.id;
    btn.classList.toggle('active', active);
    btn.setAttribute('aria-checked', active ? 'true' : 'false');
  }
  $('uni-label').textContent = `${mode.hint} — ${mode.label}`;
  const input = $('uni-in');
  input.placeholder = mode.placeholder;
  input.value = value;
}

function setOrigin(modeId, text) {
  const mode = MODES.find((mm) => mm.id === modeId) || MODES[0];
  setMode(mode, text);
  try {
    const res = mode.toJdn(text);
    applyPivot(res, `recibido desde tarjeta ${mode.label.toLowerCase()}`, { id: mode.id, text });
  } catch {
    // si el texto no re-parsea (p. ej. fuera de rango Intl), deja la entrada lista
    $('uni-in').focus();
  }
}

function bindTranslator() {
  const modeRow = $('uni-modes');
  const form = $('form-uni');
  const input = $('uni-in');

  for (const mode of MODES) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'mode-btn';
    btn.textContent = mode.label;
    btn.dataset.mode = mode.id;
    btn.setAttribute('role', 'radio');
    btn.setAttribute('aria-checked', 'false');
    btn.addEventListener('click', () => setMode(mode));
    modeRow.appendChild(btn);
  }

  form.addEventListener('submit', (ev) => {
    ev.preventDefault();
    const status = $('rosetta-status');
    status.textContent = '';
    status.classList.remove('error');
    let res;
    try {
      res = currentMode.toJdn(input.value);
    } catch (err) {
      status.textContent = `Formato esperado (${currentMode.hint}) — ej.: ${currentMode.placeholder}` +
        (err && err.message ? `. Detalle: ${err.message}` : '') +
        '. Revisa el calendario de origen seleccionado arriba.';
      status.classList.add('error');
      return;
    }
    applyPivot(res, `traducido desde ${currentMode.label.toLowerCase()}`, { id: currentMode.id, text: input.value });
  });
}

function applyPivot(res, pivotLabel, hashInfo) {
  currentJdn = res.jdn;
  if (hashInfo) {
    lastRes = { modeId: hashInfo.id, text: hashInfo.text, jdn: res.jdn };
    writeHash(hashInfo.id, hashInfo.text);
  }
  const status = $('rosetta-status');
  const di = res.jdn - ORIGIN_JDN;
  status.textContent = `Pivote: ${res.label} → day_index ${di} → JDN ${res.jdn}`;
  renderGrid($('rosetta-grid'), res.jdn, pivotLabel);
  renderMonth();
}

// ---------------------------------------------------------------------------
// Calendario mensual Gerarion navegable (incluye Tempalum y días sagrados)
// ---------------------------------------------------------------------------

const SACRED_DAYS = { '1-12': 'Cruxyphi', '1-15': 'Resinove', '1-30': 'Yeshuvid' };

function gusMarkFor(di) {
  const g = toGerarion(di);
  let special = tempalumName(g) || SACRED_DAYS[`${g.month}-${g.day}`] || '';
  return { g, special };
}

function renderMonth() {
  const grid = $('month-grid');
  const status = $('month-status');
  if (!grid) return;
  const di = currentJdn - ORIGIN_JDN;
  const g = toGerarion(di);
  const monthName = g.month === 0 ? 'Tempalum' : `${MONTHS[g.month][0]} — ${MONTHS[g.month][1]}`;
  const era = g.year >= 0 ? 'DY' : 'AY';
  const yearStr = `${String(Math.abs(g.year)).padStart(4, '0')}${era}`;
  const title = `Calendario del mes: ${monthName} · año ${yearStr}`;
  const h2 = $('month-title');
  if (h2) h2.textContent = title;

  const start = fromGerarion(g.year, g.month, 1);
  const len = g.month === 0 ? tempalumDays(g.year) : 30;
  const startWd = start.weekdayIndex;

  grid.textContent = '';
  for (const wd of WEEKDAYS) {
    const c = document.createElement('span');
    c.className = 'wd';
    c.textContent = wd[1];
    grid.appendChild(c);
  }
  for (let i = 0; i < startWd; i++) {
    const c = document.createElement('span');
    c.className = 'month-empty';
    c.setAttribute('aria-hidden', 'true');
    grid.appendChild(c);
  }
  for (let d = 1; d <= len; d++) {
    const dayDi = start.dayIndex + (d - 1);
    const { g: gd, special } = gusMarkFor(dayDi);
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'month-cell';
    btn.textContent = String(d);
    btn.setAttribute('aria-label', `${gd.canonical}${special ? ` — ${special}` : ''}`);
    if (special) btn.title = special;
    if (dayDi === di) {
      btn.classList.add('selected');
      btn.setAttribute('aria-current', 'date');
    }
    btn.addEventListener('click', () => {
      currentJdn = ORIGIN_JDN + dayDi;
      setOrigin('gero', canonicalOf(gv));
    });
    grid.appendChild(btn);
  }
  if (status) {
    status.textContent = `seleccionado: ${canonicalOf(g)} (día ${di})`;
  }
}

function bindMonthNav() {
  const prev = $('month-prev');
  const next = $('month-next');
  const hoy = $('month-hoy');
  const shift = (delta) => {
    const g = toGerarion(currentJdn - ORIGIN_JDN);
    let y = g.year;
    let m = g.month + delta;
    if (m > 12) { m = 0; }          // tras Ichtys (12) viene Tempalum (00) del mismo año
    if (m < 0) { y -= 1; m = 12; }  // antes de Tempalum (00) está 12 del año anterior
    try {
      const start = fromGerarion(y, m, 1);
      currentJdn = ORIGIN_JDN + start.dayIndex;
      renderGrid($('rosetta-grid'), currentJdn, 'navegación de mes');
      renderMonth();
    } catch (err) {
      toast(`no se puede navegar: ${err.message}`);
    }
  };
  if (prev) prev.addEventListener('click', () => shift(-1));
  if (next) next.addEventListener('click', () => shift(1));
  if (hoy) {
    hoy.addEventListener('click', () => {
      currentJdn = todayJdnUtc();
      renderGrid($('rosetta-grid'), currentJdn, 'hoy UTC');
      renderMonth();
    });
  }
}

function bindHoyUtc() {
  const hoy = $('hoy-utc');
  if (!hoy) return;
  hoy.addEventListener('click', () => {
    const j = todayJdnUtc();
    const gd = toGerarion(j - ORIGIN_JDN);
    setOrigin('gero', canonicalOf(gd));
    toast('Hoy UTC');
  });
}

// ---------------------------------------------------------------------------
// Presets históricos y astronómicos
// ---------------------------------------------------------------------------

const PRESETS = [
  {
    label: 'Hoy',
    run: () => {
      const j = todayJdnUtc();
      setOrigin('gero', canonicalOf(toGerarion(j - ORIGIN_JDN)));
    },
  },
  { label: 'Inicio año 2031 DY', ts: '2031DY-01-01-S' },
  { label: 'Cruxyphi · 2031DY-01-12-T', ts: '2031DY-01-12-T' },
  { label: 'Origen · 0000DY-01-01-S', ts: '0000DY-01-01-S' },
  { label: 'Nuvivid VII · 0001AY-00-11-B', ts: '0001AY-00-11-B' },
  { label: 'Cleopatra · 0064AY-11-12-T', ts: '0064AY-11-12-T' },
  { label: 'Younger Dryas · 12000AY-01-01-S', ts: '12000AY-01-01-S' },
];

function bindPresets() {
  const row = $('presets');
  if (!row) return;
  const lb = document.createElement('span');
  lb.className = 'presets-label dim';
  lb.textContent = 'hitos:';
  row.appendChild(lb);
  for (const p of PRESETS) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'preset-btn';
    btn.textContent = p.label;
    btn.addEventListener('click', () => {
      if (p.run) {
        p.run();
        return;
      }
      try {
        const ts = parse(p.ts);
        setOrigin('gero', canonicalOf(ts));
        toast(p.label);
      } catch (err) {
        toast(`preset inválido: ${err.message}`);
      }
    });
    row.appendChild(btn);
  }
}

// ---------------------------------------------------------------------------
// Quick forms (compatibilidad e2e: #form-greg, #form-gero)
// ---------------------------------------------------------------------------

function showOutput(id, lines, isError = false) {
  const el = $(id);
  if (!el) return;
  el.textContent = lines.join('\n');
  el.classList.toggle('error', isError);
}

function bindGregForm() {
  $('form-greg').addEventListener('submit', (ev) => {
    ev.preventDefault();
    const m = /^(\d{4,6})-(\d{2})-(\d{2})$/.exec($('greg-date').value);
    if (!m) {
      showOutput('output-greg', ['Fecha inválida: se espera AAAA-MM-DD.'], true);
      return;
    }
    try {
      const dayIndex = dayIndexFromGregorian(Number(m[1]), Number(m[2]), Number(m[3]));
      const g = toGerarion(dayIndex);
      const lines = [
        `instante continuo: día ${dayIndex}`,
        `gerarion:          ${canonicalOf(g)}`,
        `nombre del día:    ${WEEKDAYS[g.weekdayIndex][0]}`,
      ];
      if (g.month === 0) {
        const tname = tempalumName(g);
        lines.push(`mes:               Tempalum${tname ? ` · ${tname}` : ''}`);
      } else {
        lines.push(`mes:               ${MONTHS[g.month][0]} — ${MONTHS[g.month][1]}`);
      }
      showOutput('output-greg', lines);
    } catch (err) {
      showOutput('output-greg', [`Error: ${err.message}`], true);
    }
  });
}

function bindGeroForm() {
  $('form-gero').addEventListener('submit', (ev) => {
    ev.preventDefault();
    const input = $('gero-ts').value;
    if (!input.trim()) {
      showOutput('output-gero', ['Introduce una marca GUS (sello GUS).'], true);
      return;
    }
    try {
      const ts = parse(input);
      const [gy, gm, gd] = gregorianFromDayIndex(ts.dayIndex);
      const grid = $('rosetta-grid');
      if (grid) {
        currentJdn = ORIGIN_JDN + ts.dayIndex;
        renderGrid(grid, ORIGIN_JDN + ts.dayIndex, `traducido desde «${input}»`);
        renderMonth();
      }
      const lines = [
        `canónico:          ${canonicalOf(ts)}`,
        `instante continuo: día ${ts.dayIndex}`,
        `gregoriano:        ${gy}-${pad2(gm)}-${pad2(gd)}`,
        `nombre del día:    ${WEEKDAYS[ts.weekdayIndex][0]}`,
      ];
      if (ts.flags.length > 0) {
        lines.push(`nota:              campos corregidos (weekday_corrected): ${ts.flags.join(', ')}`);
      }
      showOutput('output-gero', lines);
    } catch (err) {
      showOutput('output-gero', [
        err instanceof GeroError ? `Sello inválido: ${err.message}` : `Error: ${err.message}`,
      ], true);
      const grid = $('rosetta-grid');
      if (grid) grid.textContent = '';
    }
  });
}

// ---------------------------------------------------------------------------
// Distancia entre fechas (AY ↦ DY, libre; autodetección de formato)
// ---------------------------------------------------------------------------

function bindIntervals() {
  $('form-int').addEventListener('submit', (ev) => {
    ev.preventDefault();
    let a, b;
    try {
      a = autodetectToJdn($('int-a').value);
      b = autodetectToJdn($('int-b').value);
    } catch (err) {
      showOutput('output-int', [err.message], true);
      return;
    }
    const days = b.jdn - a.jdn;
    const sign = days < 0 ? '←' : '→';
    const weeksGus = days / 7;
    const secondsSi = days * 86400;
    const yA = toGerarion(a.jdn - ORIGIN_JDN);
    const yB = toGerarion(b.jdn - ORIGIN_JDN);
    const yearSpan = yB.year - yA.year;
    const weeksStr = Number.isInteger(weeksGus)
      ? `${weeksGus} semanas Gerarion exactas`
      : `${weeksGus.toFixed(4).replace(/0+$/, '').replace(/\.$/, '')} semanas Gerarion`;
    const eraOf = (g) => (g.year < 0 ? `${-g.year} AY` : `${g.year} DY`);
    showOutput('output-int', [
      `${a.label} ${sign} ${b.label}`,
      `distancia: ${days.toLocaleString('es')} días (${sign})`,
      `         = ${weeksStr}`,
      `         = ${secondsSi.toLocaleString('es')} segundos SI (${days} × 86.400, sin segundos intercalares)`,
      `años Gerarion: ${eraOf(yA)} ${sign} ${eraOf(yB)} (Δ año: ${yearSpan > 0 ? '+' : ''}${yearSpan})`,
      `  · JDN: ${a.jdn.toLocaleString('es')} ${sign} ${b.jdn.toLocaleString('es')}`,
    ]);
  });
}

// ---------------------------------------------------------------------------
// Autoverificación normativa en vivo (#selftest)
// ---------------------------------------------------------------------------

function runSelfTest() {
  const el = $('selftest');
  if (!el) return;
  try {
    // tests.mjs ya corrió sus 22 checks al importarse (el mismo set normativo
    // en el navegador, gus-normative-002 + reglas del núcleo)
    el.textContent = report();
    el.classList.add(failed === 0 ? 'pass' : 'fail');
  } catch (err) {
    el.textContent = `Error ejecutando vectores: ${err.message}`;
    el.classList.add('fail');
  }
}

// ---------------------------------------------------------------------------
// utilidades + arranque
// ---------------------------------------------------------------------------

function setText(id, text) {
  const el = $(id);
  if (el) el.textContent = text;
}

function main() {
  if (location.protocol === 'file:') {
    // Los módulos ES no cargan bajo file:// (CORS del navegador).
    setText('now-gero', 'Abre esta página vía HTTP — no por file://');
    setText(
      'now-details',
      'Sirve la carpeta con: python3 -m http.server 8000 --directory web  (y abre http://localhost:8000)',
    );
    const el = $('selftest');
    if (el) {
      el.textContent = 'bloqueado por file:// — sirve la página por HTTP para ejecutar los vectores';
      el.classList.add('fail');
    }
    return;
  }
  bindTheme();
  bindClock();
  bindGregForm();
  bindGeroForm();
  bindTranslator();
  bindPresets();
  bindIntervals();
  bindMonthNav();
  bindHoyUtc();
  bindShare();
  runSelfTest();
  if (!applyHash()) {
    setMode(MODES[0]);
    renderGrid($('rosetta-grid'), currentJdn, 'hoy UTC (estado inicial)');
    renderMonth();
  }
}

main();
