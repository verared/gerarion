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
  toGerarion,
  parse,
  canonicalOf,
  cycleOf,
  tempalumDays,
  tempalumName,
  WEEKDAYS,
  MONTHS,
  GUS_UNIX_OFFSET,
  GeroError,
} from './gerarion.mjs';

import {
  gregorianToJdn,
  jdnToGregorianStr,
  julianToJdn,
  jdnToJulian,
  egyptianToJdn,
  jdnToEgyptian,
  EGYPT_EPOCH_JDN,
  EGYPT_MONTHS,
  ethiopicToJdn,
  jdnToEthiopic,
  ETHIOPIC_EPOCH_JDN,
  ETHIOPIC_MONTHS,
  isEthiopicLeap,
  bahaiToJdn,
  jdnToBahai,
  BAHAI_EPOCH_JDN,
  BAHAI_MONTHS,
  mayaToJdn,
  jdnToMaya,
  MAYA_CORRELATION_JDN,
  intlCalendar,
  civilWeekday,
  gusView,
} from './calendars.mjs';

import { report, failed } from './tests.mjs';

const $ = (id) => document.getElementById(id);

function pad2(n) {
  return String(n).padStart(2, '0');
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
// Tema claro/oscuro (sin persistencia: no cookies ni storage)
// ---------------------------------------------------------------------------

function bindTheme() {
  const btn = $('theme-toggle');
  if (!btn) return;
  btn.addEventListener('click', () => {
    const light = document.documentElement.getAttribute('data-theme') === 'light';
    if (light) {
      document.documentElement.removeAttribute('data-theme');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
    }
    btn.textContent = light ? 'tema' : 'tema ☾';
  });
}

// ---------------------------------------------------------------------------
// Reloj en vivo
// Convención de la spec: el día rueda a medianoche (el instante continuo es
// lineal día*86400 + h*3600 + m*60 + s); el ciclo SC/LC es solo la etiqueta
// luminosa de la hora actual (SC 06:00-17:59, LC 18:00-05:59).
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
    sel.options[1].textContent = `TCJ local (${-(new Date().getTimezoneOffset() / 60) >= 0 ? '+' : ''}${-new Date().getTimezoneOffset() / 60})`;
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
// Traductor universal: parseo por modo y autodetección
// ---------------------------------------------------------------------------

const MODES = [
  {
    id: 'gero',
    label: 'Gerarion',
    placeholder: '2031DY-03-08-T-09:30:00-SC-TCJ+0  ·  12000AY-01-01-S',
    hint: 'marca canónica GUS completa o fecha AAAAYY-MM-DD-X',
    toJdn(text) {
      const ts = parse(text);
      return { jdn: ORIGIN_JDN + ts.dayIndex, label: canonicalOf(ts) };
    },
  },
  {
    id: 'greg',
    label: 'Gregoriano',
    placeholder: '2026-03-17',
    hint: 'gregoriano proléptico ISO (años negativos = a.C.)',
    toJdn(text) {
      const m = /^(-?\d{1,6})-(\d{1,2})-(\d{1,2})$/.exec(text.trim());
      if (!m) throw new Error('formato esperado: AAAA-MM-DD');
      const y = Number(m[1]);
      const j = gregorianToJdn(y, Number(m[2]), Number(m[3]));
      return { jdn: j, label: `gregoriano ${y}-${pad2(Number(m[2]))}-${pad2(Number(m[3]))}` };
    },
  },
  {
    id: 'julian',
    label: 'Juliano',
    placeholder: '2026 11 4',
    hint: 'año mes día julianos (enteros; años a.C. = negativos)',
    toJdn(text) {
      const p = triplet(text);
      return { jdn: julianToJdn(p[0], p[1], p[2]), label: `juliano ${p.join(' ')}` };
    },
  },
  {
    id: 'egyptian',
    label: 'Egipcio',
    placeholder: '3641 8 5',
    hint: 'año Nabonassar · mes 1–12 (Thoth..Mesore) o 13 (epagómenos) · día',
    toJdn(text) {
      const p = triplet(text);
      return { jdn: egyptianToJdn(p[0], p[1], p[2]), label: `año ${p[0]} Nabonassar` };
    },
  },
  {
    id: 'ethiopic',
    label: 'Etíope',
    placeholder: '2019 3 8',
    hint: 'año EC · mes 1–13 (Meskerem..Pagume) · día',
    toJdn(text) {
      const p = triplet(text);
      return { jdn: ethiopicToJdn(p[0], p[1], p[2]), label: `año ${p[0]} EC` };
    },
  },
  {
    id: 'bahai',
    label: "Bahá'í",
    placeholder: '183 13 14',
    hint: 'año BE · mes 1–19 (0 = Ayyám-i-Há) · día',
    toJdn(text) {
      const p = triplet(text);
      return { jdn: bahaiToJdn(p[0], p[1], p[2]), label: `año ${p[0]} BE` };
    },
  },
  {
    id: 'maya',
    label: 'Maya',
    placeholder: '13.0.14.1.19',
    hint: 'cuenta larga B.K.T.U.K (correlación GMT)',
    toJdn(text) {
      const p = text.trim().split(/[.\s]+/).map(Number);
      if (p.length !== 5 || p.some((n) => !Number.isInteger(n))) {
        throw new Error('formato esperado: B.K.T.U.K (ej. 13.0.14.1.19)');
      }
      return { jdn: mayaToJdn(p[0], p[1], p[2], p[3], p[4]), label: `${p.join('.')} (cuenta larga)` };
    },
  },
];

function triplet(text) {
  const parts = text.trim().split(/[\s,/.]+/).map(Number);
  if (parts.length !== 3 || parts.some((n) => !Number.isInteger(n))) {
    throw new Error('formato esperado: año mes día (ej. -6 3 21)');
  }
  return parts;
}

function autodetectJdn(text) {
  const t = text.trim();
  if (/^(DY|AY)/i.test(t) || /\d{4,6}(DY|AY)/i.test(t)) return MODES[0].toJdn(t);
  if (/^-?\d{1,6}-\d{1,2}-\d{1,2}$/.test(t)) return MODES[1].toJdn(t);
  if (/^-?\d+\.\d+\.\d+\.\d+\.\d+$/.test(t)) return MODES[6].toJdn(t);
  if (/^[\s(),\.\-\/]*-?\d+[\s,\/]+-?\d+[\s,\/]+-?\d+/.test(t)) return MODES[2].toJdn(t);
  throw new Error('formato no reconocido: usa una marca GUS (…DY/…AY), AAAA-MM-DD, «año mes día», o una cuenta larga maya');
}

// ---------------------------------------------------------------------------
// Cuadrícula de calendarios (Piedra Rosetta): 10 tarjetas desde un JDN
// ---------------------------------------------------------------------------

function tile({ title, main, sub, note, check, copyText, accent }) {
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
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'cal-copy';
  btn.textContent = '⧉';
  btn.title = 'Copiar';
  btn.setAttribute('aria-label', `Copiar ${title}`);
  btn.addEventListener('click', () => copyText(copyText ?? main));
  el.appendChild(btn);

  return el;
}

function signedYearIso(y, m, d) {
  return `${String(y).padStart(4, '0')}-${pad2(m)}-${pad2(d)}`;
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
    sub: gusSub + (gv.special ? ` · ${gv.special}` : ''),
    check: `day_index ${dayIndex}${pivotLabel ? ` · ${pivotLabel}` : ''}`,
    copyText: gv.canonical,
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
  }));

  // 3. Juliano
  const jl = jdnToJulian(jdnVal);
  container.appendChild(tile({
    title: 'Juliano',
    main: signedYearIso(jl.year, jl.month, jl.day),
    sub: `${civilWeekday(jdnVal)} · año juliano`,
    check: 'exacto con JDN',
    copyText: signedYearIso(jl.year, jl.month, jl.day),
  }));

  // 4. Egipcio (Vago)
  const eg = jdnToEgyptian(jdnVal);
  const egMonth = eg.month === 13 ? EGYPT_MONTHS[12] : EGYPT_MONTHS[eg.month - 1];
  container.appendChild(tile({
    title: 'Egipcio antiguo (Vago)',
    main: `${egMonth} ${eg.day} · año ${eg.year} Nab.`,
    sub: eg.epagomenos ? `${eg.day}.º epagómeno` : '12 × 30 + 5 epagómenos',
    note: eg.year <= 0 ? 'extensión proleptica (año ≤ 0 Nabonassar)' : null,
    check: `época: JDN ${EGYPT_EPOCH_JDN} (Nabonassar 1)`,
    copyText: `${eg.year} ${eg.month} ${eg.day}`,
  }));

  // 5. Etíope
  const et = jdnToEthiopic(jdnVal);
  const etMonth = ETHIOPIC_MONTHS[et.month - 1] || '?';
  container.appendChild(tile({
    title: 'Etíope (Amete Mihret)',
    main: `${etMonth} ${et.day} · ${et.year} EC`,
    sub: et.pagume ? 'Pagume (mes intercalar de 6 días)' : '12 × 30 + Pagume (5/6)',
    note: et.year <= 0 ? 'extensión proleptica' : null,
    check: `bisiesto EC: ${isEthiopicLeap(et.year) ? 'sí' : 'no'}`,
    copyText: `${et.year} ${et.month} ${et.day}`,
  }));

  // 6. Bahá'í (Badí')
  const bh = jdnToBahai(jdnVal);
  const bhMonth = BAHAI_MONTHS[bh.month] || '?';
  container.appendChild(tile({
    title: "Bahá'í (Badí')",
    main: `${bhMonth} ${bh.day} · ${bh.year} BE`,
    sub: bh.month === 0 ? 'días intercalares antes de ʿAláʼ' : '19 × 19 + Ayyám-i-Há',
    note: 'convención Naw-Rúz = 21 de marzo (sesgo ≤ 1 día vs. astronomía desde 2015)',
    check: 'época: JDN 2394647 (21 mar 1844)',
    copyText: `${bh.year} ${bh.month} ${bh.day}`,
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
  }));

  // 8-10. Intl: hebreo, islámico-civil, chino
  for (const [which, title, enumNote] of [
    ['hebrew', 'Hebreo', 'cuenta Anno Mundi (ICU)'],
    ['islamic', 'Islámico (civil)', 'Hijri aritmético (tabular)'],
    ['chinese', 'Chino', 'lunar; aprox. astronómica de ICU'],
  ]) {
    const r = intlCalendar(jdnVal, which);
    if (r.ok) {
      container.appendChild(tile({
        title,
        main: r.text,
        sub: [
          r.year !== null ? `año ${r.year}` : null,
          r.leapMonth ? 'mes bisiesto' : null,
          r.era ? r.era : null,
        ].filter(Boolean).join(' · ') || enumNote,
        note: which === 'chinese' ? 'los meses bisiestos se marcan «bis»' : null,
        check: enumNote,
        copyText: r.text,
      }));
    } else {
      container.appendChild(tile({
        title,
        main: '—',
        note: `fecha no representable: ${r.note}`,
        sub: null,
      }));
    }
  }
}

// ---------------------------------------------------------------------------
// Traductor universal: modos + envío
// ---------------------------------------------------------------------------

let currentMode = MODES[0];

function bindTranslator() {
  const modeRow = $('uni-modes');
  const input = $('uni-in');
  const label = $('uni-label');
  const status = $('rosetta-status');
  const grid = $('rosetta-grid');
  const form = $('form-uni');

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

  function setMode(mode, value = '') {
    currentMode = mode;
    for (const btn of modeRow.children) {
      const active = btn.dataset.mode === mode.id;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-checked', active ? 'true' : 'false');
    }
    label.textContent = `${mode.hint} — ${mode.label}`;
    input.placeholder = mode.placeholder;
    input.value = value;
  }

  form.addEventListener('submit', (ev) => {
    ev.preventDefault();
    status.textContent = '';
    status.classList.remove('error');
    grid.textContent = '';
    let res;
    try {
      res = currentMode.toJdn(input.value);
    } catch (err) {
      status.textContent = `Entrada inválida: ${err.message}`;
      status.classList.add('error');
      return;
    }
    const di = res.jdn - ORIGIN_JDN;
    status.textContent = `Pivote: ${res.label} → day_index ${di} → JDN ${res.jdn}`;
    renderGrid(grid, res.jdn, `traducido desde ${currentMode.label.toLowerCase()}`);
  });

  window.__setUni = (modeId, value) => {
    const mode = MODES.find((mm) => mm.id === modeId) || MODES[0];
    setMode(mode, value);
    form.requestSubmit();
  };

  setMode(MODES[0]);
}

// ---------------------------------------------------------------------------
// Presets históricos y astronómicos
// ---------------------------------------------------------------------------

const PRESETS = [
  { label: 'Hoy', run: () => showDay(ORIGIN_JDN + dayIndexFromGregorian(new Date().getUTCFullYear(), new Date().getUTCMonth() + 1, new Date().getUTCDate())) },
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
        showDay(ORIGIN_JDN + ts.dayIndex);
        toast(p.label);
      } catch (err) {
        toast(`preset inválido: ${err.message}`);
      }
    });
    row.appendChild(btn);
  }
}

function showDay(jdnVal) {
  const di = jdnVal - ORIGIN_JDN;
  // carga la fecha en el traductor universal (modo Gerarion, marca canónica)
  const g = toGerarion(di);
  if (typeof window.__setUni === 'function') {
    window.__setUni('gero', canonicalOf(g));
  } else {
    renderPresetStatus(jdnVal);
  }
}

function renderPresetStatus(jdnVal) {
  const status = $('rosetta-status');
  const di = jdnVal - ORIGIN_JDN;
  status.textContent = `Pivote: day_index ${di} → JDN ${jdnVal}`;
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
        `gerearion:         ${canonicalOf(g)}`,
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
      showOutput('output-gero', ['Introduce un sello GTS.'], true);
      return;
    }
    try {
      const ts = parse(input);
      const [gy, gm, gd] = gregorianFromDayIndex(ts.dayIndex);
      const grid = $('rosetta-grid');
      if (grid) {
        renderGrid(grid, ORIGIN_JDN + ts.dayIndex, `traducido desde «${input}»`);
      }
      const lines = [
        `canónico:          ${canonicalOf(ts)}`,
        `instante continuo: día ${ts.dayIndex}`,
        `gregoriano:        ${gy}-${pad2(gm)}-${pad2(gd)}`,
        `nombre del día:     ${WEEKDAYS[ts.weekdayIndex][0]}`,
      ];
      if (ts.flags.length > 0) {
        lines.push(`nota:              campos corregidos: ${ts.flags.join(', ')}`);
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
// Distancia entre fechas (AY ↦ DY, libre)
// ---------------------------------------------------------------------------

function bindIntervals() {
  $('form-int').addEventListener('submit', (ev) => {
    ev.preventDefault();
    let a, b;
    try {
      a = autodetectJdn($('int-a').value);
      b = autodetectJdn($('int-b').value);
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
    showOutput('output-int', [
      `${a.label} ${sign} ${b.label}`,
      `distancia: ${days.toLocaleString('es')} días (${sign})`,
      `         = ${weeksStr}`,
      `         = ${secondsSi.toLocaleString('es')} segundos SI (${days} × 86.400, sin intercalares)`,
      `años Gerarion: ${yA.year < 0 ? `${-yA.year} AY` : `${yA.year} DY`} ${sign} ${yB.year < 0 ? `${-yB.year} AY` : `${yB.year} DY`} (Δ año: ${yearSpan > 0 ? '+' : ''}${yearSpan})`,
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
  runSelfTest();
}

main();
