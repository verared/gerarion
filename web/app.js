// UI del calculador Gerarion.
// Regla de seguridad: todo dato dinámico pasa por textContent — nunca innerHTML
// con datos del usuario. Matemática 100% local (gerarion.mjs); la página no
// envía ni recibe nada por red.

import {
  dayIndexFromGregorian,
  gregorianFromDayIndex,
  toGerarion,
  parse,
  canonicalOf,
  cycleOf,
  tempalumDays,
  WEEKDAYS,
  MONTHS,
  tempalumName,
  GeroError,
} from './gerarion.mjs';

const $ = (id) => document.getElementById(id);

function pad2(n) {
  return String(n).padStart(2, '0');
}

function showOutput(id, lines, isError = false) {
  const el = $(id);
  if (!el) return;
  el.textContent = lines.join('\n');
  el.classList.toggle('error', isError);
}

function monthLabel(month, year) {
  if (month === 0) return 'Tempalum (mes 00)';
  return `${MONTHS[month] ? MONTHS[month][0] : '?'} (mes ${pad2(month)})`;
}

// ---------- Rel vivo ----------
// Convención de la spec: el día rueda a medianoche (el instante continuo es
// lineal día*86400 + h*3600 + m*60 + s); el ciclo SC/LC es solo la etiqueta
// luminosa de la hora actual (SC 06:00-17:59, LC 18:00-05:59).

function tickClock() {
  const now = new Date();
  const dayIndex = dayIndexFromGregorian(
    now.getUTCFullYear(),
    now.getUTCMonth() + 1,
    now.getUTCDate(),
  );
  const g = toGerarion(dayIndex);
  const h = now.getUTCHours();
  const m = now.getUTCMinutes();
  const s = now.getUTCSeconds();
  const cyc = cycleOf(h);

  setText(
    'now-gero',
    canonicalOf({ ...g, hour: h, minute: m, second: s, cycle: cyc, offset: 0 }),
  );
  setText(
    'now-details',
    `día ${dayIndex} · ${WEEKDAYS[g.weekdayIndex][0]} · ${monthLabel(g.month, g.year)} · ciclo ${cyc} · hora TCJ+0`,
  );
}

function setText(id, text) {
  const el = $(id);
  if (el) el.textContent = text;
}

// ---------- Gregoriano → Gerarion ----------

function bindGregForm() {
  $('form-greg').addEventListener('submit', (ev) => {
    ev.preventDefault();
    const m = /^(\d{1,6})-(\d{2})-(\d{2})$/.exec($('greg-date').value);
    if (!m) {
      showOutput('output-greg', ['Fecha inválida: se espera AAAA-MM-DD.'], true);
      return;
    }
    try {
      const dayIndex = dayIndexFromGregorian(Number(m[1]), Number(m[2]), Number(m[3]));
      const g = toGerarion(dayIndex);
      const lines = [
        `instante continuo: día ${dayIndex}`,
        `gerarion:         ${canonicalOf(g)}`,
        `nombre del día:    ${WEEKDAYS[g.weekdayIndex][0]}`,
      ];
      if (g.month === 0) {
        const tname = tempalumName(g);
        lines.push(`mes:               Tempalum${tname ? ` - ${tname}` : ''}`);
        if (g.day > tempalumDays(g.year)) {
          lines.push('nota: día fuera de Tempalum - solo existe en años Gran Tempalum');
        }
      } else {
        lines.push(`mes:               ${MONTHS[g.month][0]}`);
      }
      showOutput('output-greg', lines);
    } catch (err) {
      showOutput('output-greg', [`Error: ${err.message}`], true);
    }
  });
}

// ---------- Gerarion → Gregoriano ----------

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
      const lines = [
        `canónico:          ${canonicalOf(ts)}`,
        `instante continuo: día ${ts.dayIndex}`,
        `gregoriano:        ${gy}-${pad2(gm)}-${pad2(gd)}`,
        `nombre del día:    ${WEEKDAYS[ts.weekdayIndex][0]}`,
      ];
      if (ts.flags.length > 0) {
        lines.push(`nota:              campos corregidos: ${ts.flags.join(', ')}`);
      }
      showOutput('output-gero', lines);
    } catch (err) {
      showOutput('output-gero', [
        err instanceof GeroError ? `Sello inválido: ${err.message}` : `Error: ${err.message}`,
      ], true);
    }
  });
}

// ---------- Vectores self-test ----------

async function runSelfTest() {
  const el = $('selftest');
  try {
    const { report, failed } = await import('./tests.mjs');
    el.textContent = report();
    el.classList.add(failed === 0 ? 'pass' : 'fail');
  } catch (err) {
    el.textContent = `Error ejecutando vectores: ${err.message}`;
    el.classList.add('fail');
  }
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
  bindGregForm();
  bindGeroForm();
  tickClock();
  setInterval(tickClock, 1000);
  runSelfTest();
}

main();
