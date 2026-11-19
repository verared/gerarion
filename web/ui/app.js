// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
// Gerarion · Atlas del tiempo. Native ES modules; no framework, account or remote API.
import { ORIGIN_JDN, MONTHS, toGerarion, canonicalOf } from "../engine/core.mjs";
import { passed, failed, report } from "../test/tests.mjs";
import {
  ES_MONTHS,
  pad,
  fmt,
  civilYear,
  civil,
  facts,
  todayJdn,
  modes,
  metadata,
  modeHint,
  equivalent,
  equivalents,
  endpoints,
  interpret,
  parseSource,
  monthGrid,
  shiftMonth,
  yearStartJdn,
  clockSample,
  interval,
  milestones,
} from "./atlas.mjs";

import {
  REFERENCE,
  zoneInfo,
  zoneCount,
  territories,
  zoneDelta,
  deltaLabel,
  observe,
  supportedZone,
  zoneGroups,
} from "../engine/zonas-tcj.mjs";

const $ = (id) => document.getElementById(id),
  root = $("view"),
  modal = $("dialog");
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const ico = (name, cl = "") =>
  `<svg class="icon ${cl}" aria-hidden="true" focusable="false"><use href="assets/atlas.svg#${name}"/></svg>`;
const button = (label, action, icon, cls = "button") =>
  `<button type="button" class="${cls}" data-action="${action}">${icon ? ico(icon) : ""}${label}</button>`;
const iconButton = (icon, label, attr) =>
  `<button type="button" class="icon-button" ${attr} title="${esc(label)}" aria-label="${esc(label)}">${ico(icon)}</button>`;
const copyButton = (v, label = "Copiar valor") =>
  iconButton("copy", label, `data-copy="${esc(v)}"`);
const options = (selected, keys = modes) =>
  keys
    .map(
      (k) =>
        `<option value="${k}"${k === selected ? " selected" : ""}>${esc(k === "auto" ? "Detectar formato" : k === "jdn" ? "Día juliano (JDN)" : metadata(k).title)}</option>`,
    )
    .join("");
const pageNames = {
  calendario: "Calendario",
  traductor: "Traductor de fechas",
  reloj: "Reloj en vivo",
  distancia: "Distancia entre fechas",
  hitos: "Hitos históricos",
  referencia: "Referencia técnica",
  verificacion: "Verificación",
};
const aliases = {
  mes: "calendario",
  ahora: "reloj",
  conversiones: "traductor",
  ...Object.fromEntries(Object.keys(pageNames).map((k) => [k, k])),
};
let initialZone = REFERENCE;
try {
  const stored = localStorage.getItem("gerarion-zone");
  if (supportedZone(stored)) initialZone = stored;
} catch {}
const initialDay = todayJdn(new Date(), initialZone);
const state = {
  j: initialDay,
  view: "calendario",
  system: "gero",
  mode: "greg",
  source: "greg",
  sourceText: civil(initialDay).iso,
  stamp: null,
  followToday: true,
  filter: "",
  zone: initialZone,
  target: "chinese",
  draft: null,
  allOpen: false,
  exchangeOpen: false,
  paused: null,
};
const selectedToday = () => todayJdn(new Date(), state.zone);
let dist = {
  a: canonicalOf(toGerarion(yearStartJdn(state.j) - ORIGIN_JDN)),
  b: civil(state.j).iso,
  am: "auto",
  bm: "auto",
  result: null,
};
let toastTimer,
  dialogOpener = null,
  lastToday = state.j,
  mobileOpen = false,
  railHidden = false;
const mobile = matchMedia("(max-width: 800px)");
const portable = document.documentElement.hasAttribute("data-portable");
// In the portable viewer, buttons calculate locally, without submitting HTML forms.
function localForms(container) {
  if (!portable) return;
  container.querySelectorAll("button[type=submit]").forEach((b) => {
    b.type = "button";
    b.dataset.runForm = "";
  });
}
function announce(text) {
  $("announcement").textContent = text;
}
function toast(text) {
  const t = $("toast");
  t.textContent = text;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2700);
}
function pageHead(kicker, title, subtitle, action = "") {
  return `<div class="page-heading"><div><div class="eyebrow accent"><span class="short-line"></span>${kicker}</div><h1 tabindex="-1">${title}</h1><p>${subtitle}</p></div>${action ? `<div class="page-actions">${action}</div>` : ""}</div>`;
}
function routeHash(view = state.view) {
  const p = new URLSearchParams({
    cal: state.source,
    d: state.sourceText,
    vista: view,
    de: state.mode,
    a: state.target,
    zona: state.zone,
  });
  if (state.stamp && state.source !== "gero") p.set("sello", state.stamp);
  return "#" + p;
}
function urlFor() {
  if (document.documentElement.hasAttribute("data-portable"))
    return `https://verared.github.io/gerarion/#cal=gero&d=${encodeURIComponent(state.stamp || facts(state.j).canonical)}`;
  return `${location.origin}${location.pathname}${routeHash()}`;
}
function saveURL(push = false) {
  const h = routeHash();
  if (h !== location.hash) {
    try {
      history[push ? "pushState" : "replaceState"](null, "", h);
    } catch {
      /* An opaque, sandboxed file preview can still navigate entirely in memory. */
    }
  }
}
function setDay(j, res = null) {
  parseSource("jdn", String(j));
  state.j = j;
  state.followToday = false;
  state.source = res?.source || "gero";
  state.sourceText = res?.text || facts(j).canonical;
  state.stamp = res?.stamp || null;
  state.draft = null;
}
function go(view, push = true) {
  if (!Object.hasOwn(pageNames, view)) return;
  const changed = view !== state.view;
  state.view = view;
  closeMenu();
  if (modal.open) modal.close();
  saveURL(push && changed);
  render();
  window.scrollTo({ top: 0, behavior: "instant" });
  root.querySelector("h1")?.focus({ preventScroll: true });
}
function readRoute() {
  const h = location.hash.slice(1),
    p = new URLSearchParams(h);
  let view =
    aliases[h] || p.get("vista") || (p.has("cal") ? "traductor" : "calendario");
  if (!Object.hasOwn(pageNames, view)) view = "calendario";
  if (p.has("zona")) {
    if (supportedZone(p.get("zona"))) state.zone = p.get("zona");
    else {
      state.zone = REFERENCE;
      toast("Ubicación no disponible. Se usa TCJ+0 · Jerusalén.");
    }
  }
  if (p.has("cal") || p.has("d")) {
    try {
      const r = parseSource(p.get("cal"), p.get("d"));
      setDay(r.jdn, r);
      state.mode = endpoints.includes(p.get("de"))
        ? p.get("de")
        : endpoints.includes(r.source)
          ? r.source
          : "greg";
      state.target =
        endpoints.includes(p.get("a")) && p.get("a") !== state.mode
          ? p.get("a")
          : state.mode === "chinese"
            ? "greg"
            : "chinese";
      if (p.has("sello")) {
        const t = parseSource("gero", p.get("sello"));
        if (t.jdn === r.jdn && t.stamp) state.stamp = t.stamp;
      }
    } catch (err) {
      toast(
        "El enlace no contiene una fecha válida. Se muestra hoy en la ubicación seleccionada.",
      );
      resetToday();
    }
  } else if (!h) {
    resetToday();
  }
  state.view = view;
  closeMenu();
  if (modal.open) modal.close();
  render();
}
function resetToday() {
  const j = selectedToday();
  setDay(j, parseSource("greg", civil(j).iso));
  state.followToday = true;
}
function refreshDay(j, res = null, refocus = false) {
  const sy = window.scrollY;
  setDay(j, res);
  saveURL();
  render();
  window.scrollTo({ top: sy, behavior: "instant" });
  if (refocus)
    root.querySelector(".day-cell.selected")?.focus({ preventScroll: true });
  const g = facts(j);
  announce(
    `Seleccionado: ${g.day} de ${g.monthName}, ${g.yearLabel}. ${g.civil.label}.`,
  );
}
function hero(g) {
  return `<section class="day-hero" aria-label="Fecha Gerarion seleccionada"><div class="hero-content"><div class="hero-kicker">${ico("sun")}<span>${state.j === selectedToday() ? "Hoy en Gerarion" : "Fecha Gerarion"}</span></div><h2>${g.day} de ${esc(g.monthName)}, ${Math.abs(g.year)} <span class="era-tag">${g.era}</span></h2><p class="hero-meta">${esc(g.weekday)}<span class="hero-separator" aria-hidden="true">·</span>${esc(g.monthGloss)}</p><span class="canonical-tag"><span class="stamp-symbol" aria-hidden="true">#</span><code>${esc(g.canonical)}</code>${copyButton(g.canonical, "Copiar fecha canónica GUS")}</span></div><div class="plate" aria-hidden="true"><svg class="construction" viewBox="0 0 720 220" preserveAspectRatio="xMidYMid slice"><g fill="none" stroke="currentColor" stroke-width=".65"><ellipse cx="475" cy="105" rx="295" ry="70" transform="rotate(-14 475 105)"/><ellipse cx="475" cy="105" rx="216" ry="91" transform="rotate(13 475 105)" stroke-dasharray="2 6"/><path d="M140 160h490M260 46h430M270 11v180M600 13v176" stroke-dasharray="1.5 5"/><path d="m205 80 0 10m-5-5h10m401 50v10m-5-5h10"/></g></svg><img src="assets/esfera-armilar.webp" alt="" width="1073" height="720" fetchpriority="high"><span class="plate-caption">Fig. 01 <i></i> Esfera armilar</span></div></section>`;
}
function calendarCard() {
  const m = monthGrid(state.j, state.system),
    today = selectedToday();
  return `<section class="panel month-panel" aria-labelledby="month-title"><div class="month-head"><div class="card-overline"><span class="eyebrow">Vista mensual</span><label class="month-system">${ico("layers")}<select id="month-system" aria-label="Sistema de la cuadrícula mensual"><option value="gero"${state.system === "gero" ? " selected" : ""}>Gerarion</option><option value="greg"${state.system === "greg" ? " selected" : ""}>Gregoriano</option></select>${ico("down")}</label></div><div class="month-title-row"><h2 id="month-title">${esc(m.title)} <span>${esc(m.yearLabel)}</span></h2><div class="month-controls"><button class="today-button" data-action="today" title="Hoy en ${esc(zoneInfo(state.zone).city)} · referencia TCJ">Hoy</button><div class="month-arrows">${iconButton("left", "Mes anterior", 'data-step="-1"')}${iconButton("right", "Mes siguiente", 'data-step="1"')}</div></div></div></div><div class="week-head" aria-hidden="true">${m.week.map((v, i) => `<abbr title="${m.fullWeek[i]}">${v}</abbr>`).join("")}</div><div class="month-days" role="group" aria-label="Días de ${esc(m.title)}. Usa las flechas para moverte entre días.">${m.cells.map((d) => `<button type="button" class="day-cell${d.outside ? " outside" : ""}${d.selected ? " selected" : ""}${d.jdn === today ? " is-today" : ""}" data-day="${d.jdn}" title="${esc(d.special || d.label)}" aria-label="${esc(d.label)}${d.special ? ", " + esc(d.special) : ""}${d.jdn === today ? ", hoy en " + esc(zoneInfo(state.zone).city) : ""}" aria-pressed="${d.selected}"${d.jdn === today ? ' aria-current="date"' : ""} tabindex="${d.selected ? "0" : "-1"}">${d.special ? '<span class="day-special" aria-hidden="true">✧</span>' : ""}<span class="day-number">${d.day}</span><span class="day-civil">${esc(d.sub)}</span></button>`).join("")}</div><div class="calendar-legend"><span><i class="legend-square"></i>Seleccionado</span><span><i class="legend-today"></i>Hoy</span><small>${state.system === "gero" ? "GUS / Gregoriano" : "Gregoriano / GUS"}</small></div></section>`;
}
function inspector(g) {
  return `<section class="panel inspector" aria-labelledby="inspector-title"><div class="inspector-heading"><span class="small-icon clay">${ico("file")}</span><h2 id="inspector-title">Ficha del día</h2>${iconButton("link", "Copiar enlace a esta fecha", 'data-action="share"')}</div><div class="civil-date"><div class="eyebrow">Fecha gregoriana</div><h3>${g.civil.day} de ${ES_MONTHS[g.civil.month - 1]} de ${civilYear(g.civil.year)}</h3><span>${g.civil.weekday}</span></div><dl class="fact-list"><div><dt>Día juliano <abbr title="Julian Day Number">JDN</abbr></dt><dd>${fmt(g.jdn)}</dd></div><div><dt>Índice de día</dt><dd>${fmt(g.dayIndex)}</dd></div><div><dt>Mes del ciclo</dt><dd>${pad(g.month)} <span>/ 12</span></dd></div></dl><div class="year-progress"><div><span>Progreso del año</span><strong>${g.pct}%</strong></div><div class="meter" role="progressbar" aria-label="Progreso del año Gerarion" aria-valuemin="0" aria-valuemax="${g.length}" aria-valuenow="${g.ordinal}"><i style="width:${g.pct}%"></i></div><small>Día ${g.ordinal} de ${g.length}${g.special ? " · " + esc(g.special) : ""}</small></div><button class="translate-day" data-action="translate-day">${ico("convert")}Traducir esta fecha${ico("arrow")}</button></section>`;
}
function miniCard(id) {
  const v = equivalent(id, state.j, state.stamp);
  return `<button class="panel mini-card" data-detail="${id}"><div class="mini-top"><span class="calendar-seal ${v.tone}">${ico(v.icon)}</span><span class="mini-name"><strong>${esc(v.title)}</strong><small>${esc(v.family)}</small></span>${ico("external", "mini-arrow")}</div><span class="mini-value">${esc(v.value)}</span></button>`;
}
function calendarPage() {
  const g = facts(state.j);
  return (
    pageHead(
      "Atlas temporal",
      "Calendario universal",
      "Un mismo día, distintas formas de medir el tiempo.",
      button("Ir a una fecha", "jump", "calendar-add"),
    ) +
    hero(g) +
    `<div class="calendar-layout">${calendarCard()}${inspector(g)}</div><section class="correspondences"><div class="section-heading"><div class="heading-with-count"><h2>Equivalencias del día</h2><span class="count-badge">10 sistemas</span></div><button class="text-button" data-action="all-dates">Ver todas ${ico("arrow")}</button></div><div class="mini-grid">${["julian", "hebrew", "maya"].map(miniCard).join("")}</div></section>`
  );
}
function sourceValue(id) {
  if (id === state.source && state.sourceText) return state.sourceText;
  if (id === "jdn") return String(state.j);
  return equivalent(id, state.j, state.stamp).raw;
}
function resultCard(v) {
  return `<article class="panel result-card" data-result="${v.id}" data-name="${esc(v.title + " " + v.family)}"><div class="result-label"><span class="calendar-seal ${v.tone}">${ico(v.icon)}</span><div><h3>${esc(v.title)}</h3><small>${esc(v.family)}</small></div></div><p class="result-value">${esc(v.value)}</p><p class="result-note">${esc(v.note)}</p><div class="result-actions">${v.ok ? `<button class="text-button" data-origin="${v.id}">${v.id === "gero" ? "Introducir sello GUS" : "Usar como origen"} ${ico("arrow")}</button>${copyButton(v.raw, "Copiar fecha en " + v.title)}` : `<span class="muted">${ico("info")} No representable</span>`}</div></article>`;
}
function bridgeSelect(id, selected, title) {
  const m = metadata(selected);
  return `<label class="bridge-choice"><span class="sr-only">${title}</span><span class="calendar-seal ${m.tone}">${ico(m.icon)}</span><select id="${id}">${options(selected, endpoints)}</select>${ico("down")}</label>`;
}
function translatorPage() {
  const g = facts(state.j),
    out = equivalent(state.target, state.j),
    pending = state.draft !== null;
  const gus = state.stamp || g.canonical;
  return (
    pageHead(
      "Piedra Rosetta",
      "Traductor de fechas",
      "Dos calendarios, un intérprete: cada fecha pasa por Gerarion.",
      button("Copiar enlace", "share", "link"),
    ) +
    `
  <section class="panel bridge-panel" aria-labelledby="bridge-title">
    <div class="bridge-top"><div><span class="eyebrow accent">Conversión bidireccional</span><h2 id="bridge-title">Ruta de interpretación</h2></div><button class="button" data-action="swap-route">${ico("convert")}Invertir ruta</button></div>
    <div class="bridge-grid">
      <div class="bridge-end"><span class="eyebrow">01 · Calendario de origen</span>${bridgeSelect("source-mode", state.mode, "Calendario de origen")}
        <form id="translator-form" novalidate><label class="field">Fecha de entrada<input id="source-date" maxlength="150" autocomplete="off" spellcheck="false" required value="${esc(state.draft ?? sourceValue(state.mode))}" aria-describedby="source-hint trans-error"></label><button type="submit" class="button primary">Interpretar ${ico("arrow")}</button></form>
      </div>
      <div class="bridge-core"><span class="bridge-connector before" aria-hidden="true">${ico("convert")}</span><span class="bridge-connector after" aria-hidden="true">${ico("convert")}</span>
        <span class="eyebrow">02 · Calendario intérprete</span><h3>${ico("brand")}Gerarion</h3><p class="gus-reading">${g.day} de ${esc(g.monthName)} · ${g.yearLabel}</p>
        <span class="bridge-canonical"><code id="bridge-stamp">${esc(g.canonical)}</code>${copyButton(gus, "Copiar sello Gerarion")}</span>
        <button class="text-button" data-action="edit-pivot">Introducir sello GUS ${ico("right")}</button>
      </div>
      <div class="bridge-end"><span class="eyebrow">03 · Calendario de destino</span>${bridgeSelect("target-mode", state.target, "Calendario de destino")}
        <div class="bridge-caption">Fecha interpretada</div><p class="bridge-value" id="bridge-output">${esc(out.value)}</p>
        ${out.ok ? `<button class="bridge-copy text-button" data-copy="${esc(out.raw)}">${ico("copy")}Copiar fecha de destino</button>` : '<p class="field-hint">Prueba otro calendario de destino.</p>'}
      </div>
    </div>
    <div class="bridge-metadata">${ico("orbit")}<span>Un mismo día</span><code>day_index ${g.dayIndex}</code><i>/</i><code>JDN ${g.jdn}</code><button class="text-button" data-action="today">Hoy en ${esc(zoneInfo(state.zone).city)} ${ico("clock")}</button></div>
    <p class="form-error" role="alert" id="trans-error" hidden></p><p id="trans-pending" class="bridge-pending" ${pending ? "" : "hidden"}>Entrada sin aplicar. Pulsa «Interpretar» para actualizar la ruta.</p>
    ${state.stamp ? `<p class="time-preserved">${ico("clock")} Sello con hora conservado: <code>${esc(state.stamp)}</code>. La ruta traduce su día declarado.</p>` : ""}
  </section>
  <div class="bridge-notes"><div><span class="eyebrow">Cómo introducir ${esc(metadata(state.mode).title)}</span><p id="source-hint">${esc(modeHint(state.mode))}</p></div><div><span class="eyebrow">Lectura del destino</span><p>${esc(out.note)}</p></div></div>
  <details class="panel equivalents-fold" id="all-calendars" ${state.allOpen ? "open" : ""}><summary><span>${ico("layers")}Todas las equivalencias</span><span class="summary-meta">10 sistemas · 11 variantes ${ico("down")}</span></summary>
    <div class="all-calendars-content"><div class="result-toolbar"><p>Reutiliza cualquier resultado como entrada del intérprete.</p><label class="search-field">${ico("search")}<input type="search" id="calendar-filter" value="${esc(state.filter)}" placeholder="Filtrar calendarios" aria-label="Filtrar calendarios por nombre"></label></div><div class="result-grid" id="results">${equivalents(state.j, state.stamp).map(resultCard).join("")}</div><p class="empty-state" id="no-results" hidden>No hay coincidencias con ese nombre.</p></div>
  </details>`
  );
}
function editPivot() {
  openDialog(
    dialogHead("Intérprete Gerarion", "Introducir sello GUS") +
      `<p class="dialog-desc">Los dos extremos de la ruta se calcularán desde este sello. Si incluye hora, se conservará como dato adjunto.</p><form id="pivot-form" novalidate><label class="field">Fecha o sello canónico<input id="pivot-value" value="${esc(state.stamp || facts(state.j).canonical)}" spellcheck="false" maxlength="150" aria-describedby="pivot-error" required></label><p class="form-error" id="pivot-error" role="alert" hidden></p><div class="dialog-actions">${button("Cancelar", "close-dialog", null)}<button type="submit" class="button primary">Interpretar ${ico("arrow")}</button></div></form>`,
  );
  $("pivot-value").select();
}
function swapRoute() {
  // Do not swap an uncommitted invalid date, or invent an inverse outside ICU coverage.
  try {
    const prior = state.mode,
      left = state.target;
    const r = interpret(prior, $("source-date").value, left),
      dst = r.output;
    if (!dst.ok) throw Error(dst.note);
    const back = parseSource(left, dst.raw);
    if (back.jdn !== r.jdn)
      throw Error("Este destino no admite una conversión inversa comprobable.");
    const stamp = r.jdn === state.j ? state.stamp : null;
    setDay(back.jdn, back);
    state.stamp = stamp;
    state.mode = left;
    state.target = prior;
    saveURL();
    render();
    announce(
      `Ruta invertida: ${metadata(left).title}, Gerarion, ${metadata(prior).title}.`,
    );
    root
      .querySelector('[data-action="swap-route"]')
      .focus({ preventScroll: true });
  } catch (err) {
    errorAt("trans-error", err, $("source-date"));
  }
}
function filterResults() {
  const norm = (s) =>
    s
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  let n = 0;
  root.querySelectorAll("[data-result]").forEach((el) => {
    el.hidden = !norm(el.dataset.name).includes(norm(state.filter.trim()));
    if (!el.hidden) n++;
  });
  if ($("no-results")) $("no-results").hidden = n !== 0;
}
function dateFace() {
  let ticks = "";
  for (let i = 0; i < 60; i++)
    ticks += `<path d="M100 11v${i % 5 === 0 ? 7 : 3}" transform="rotate(${i * 6} 100 100)" stroke-width="${i % 5 === 0 ? 1.5 : 0.65}"/>`;
  return `<svg viewBox="0 0 200 200" class="clock-face" aria-hidden="true"><circle cx="100" cy="100" r="94" fill="none" stroke="currentColor" stroke-width=".7"/><g stroke="currentColor">${ticks}</g><g class="dial-numbers"><text x="100" y="36">XII</text><text x="169" y="104">III</text><text x="100" y="174">VI</text><text x="32" y="104">IX</text></g><g stroke="currentColor" stroke-linecap="round"><path id="hand-h" d="M100 104V61" stroke-width="3"/><path id="hand-m" d="M100 109V35" stroke-width="2"/><path id="hand-s" d="M100 116V24" stroke="var(--accent)" stroke-width="1.2"/></g><circle cx="100" cy="100" r="3.6" fill="var(--accent)"/></svg>`;
}
const spots = [REFERENCE, "America/Santiago", "America/Argentina/Buenos_Aires"];
const clockRow = ([key, name, desc]) =>
  `<div class="code-row"><div><strong>${name}</strong><small>${desc}</small></div><code id="live-${key}">—</code>${iconButton("copy", "Copiar " + name, `data-copy-id="live-${key}"`)}</div>`;
function clockPage() {
  const place = zoneInfo(state.zone);
  return (
    pageHead(
      "Coordenadas Gerarion",
      "Reloj en vivo",
      "Un mismo instante, leído desde el meridiano de Jerusalén y las regiones del mundo.",
      button(
        state.paused === null ? "Pausar lectura" : "Reanudar lectura",
        "pause",
        state.paused === null ? "pause" : "play",
      ),
    ) +
    `
<section class="clock-hero panel"><div><div class="hero-kicker"><i class="status-dot"></i>${state.paused === null ? "Lectura en vivo" : "Lectura en pausa"} · ${esc(place.city)}</div><div class="clock-digits mono" id="main-clock">--:--:--</div><p id="clock-caption"></p><button class="button choose-place" data-action="zones">${ico("globe")}Cambiar ubicación ${ico("down")}</button></div>${dateFace()}</section>
<div class="scale-grid regional-clocks">${spots
      .map((id, i) => {
        const z = zoneInfo(id);
        return `<button class="panel scale ${state.zone === id ? "selected-spot" : ""}" data-zone="${esc(id)}" aria-pressed="${state.zone === id}"><span class="eyebrow">${esc(z.reference ? "Meridiano de referencia" : z.country)}</span><span class="spot-city">${esc(z.city)}</span><strong id="spot-time-${i}" class="mono">—</strong><span class="count-badge" id="spot-delta-${i}">—</span></button>`;
      })
      .join("")}</div>
<section class="panel codes-panel"><div class="panel-title"><span class="small-icon clay">${ico("code")}</span><h2>Coordenada canónica</h2></div>${[
      [
        "stamp",
        "Sello GUS",
        "Fecha y hora del meridiano TCJ+0, independiente de la ciudad elegida",
      ],
      ["instant", "Instante GUS", "Segundos continuos desde el origen"],
      ["dayindex", "Índice de día TCJ", "Día del sello canónico en TCJ+0"],
      ["jdn", "JDN del día TCJ", "Número juliano de esa fecha"],
    ]
      .map(clockRow)
      .join("")}
<details class="exchange-formats" id="clock-exchange" ${state.exchangeOpen ? "open" : ""}><summary>Formatos de intercambio ${ico("down")}</summary>${[
      [
        "rfc",
        "RFC 3339",
        "Perfil de interoperabilidad con sufijo Z; no es un sello TCJ",
      ],
      ["unix", "Unix", "Segundos POSIX desde la época Unix"],
      ["ntp", "Marca NTP", "Segundos y fracción en hexadecimal, con era"],
    ]
      .map(clockRow)
      .join("")}</details></section>
<div class="info-note">${ico("info")}<p>TCJ+0 es la coordenada Gerarion de Jerusalén, no su hora civil. Para las regiones, el desfase se calcula al instante de la lectura y conserva los segundos en el reloj; la etiqueta se muestra redondeada a horas. No se inserta como sufijo de un sello GUS. El reloj usa el dispositivo, sin sincronización de red.</p></div>`
  );
}
function updateClock() {
  const ms = Date.now(),
    head = observe(ms, state.zone);
  $("header-time").textContent = head.time;
  $("header-zone").textContent = head.label;
  $("header-city").textContent = head.zone.city;
  $("zone-trigger").setAttribute(
    "aria-label",
    `Elegir ubicación: ${head.label} · ${head.zone.city}`,
  );
  if (head.jdn !== lastToday) {
    lastToday = head.jdn;
    if (state.followToday) {
      const draft = state.draft;
      resetToday();
      state.draft = draft;
      if (location.hash.includes("d=")) saveURL();
    }
    if (
      state.view === "calendario" ||
      (state.view === "traductor" && state.followToday)
    )
      render();
  }
  if (state.view !== "reloj") return;
  const s = clockSample(state.paused ?? ms, state.zone),
    o = s.seen,
    part = o.p;
  $("main-clock").textContent = o.time;
  $("clock-caption").textContent =
    `${o.label} · ${part.day} de ${MONTHS[part.month][0]}, ${Math.abs(part.year)} ${part.year < 0 ? "AY" : "DY"} · ${part.weekday} · ${part.cycle}`;
  spots.forEach((id, i) => {
    try {
      const r = id === REFERENCE ? s.ref : observe(s.ms, id, s.instant);
      $("spot-time-" + i).textContent = r.time;
      $("spot-delta-" + i).textContent = r.label;
    } catch {
      $("spot-time-" + i).textContent = "—";
      $("spot-delta-" + i).textContent = "Sin cobertura";
    }
  });
  Object.entries({
    stamp: s.stamp,
    instant: String(s.instant),
    dayindex: s.p.dayIndex,
    jdn: s.ref.jdn,
    rfc: s.rfc,
    unix: s.unix,
    ntp: `${s.ntp.hex} · era ${s.ntp.era}`,
  }).forEach(([k, v]) => ($("live-" + k).textContent = v));
  const h = part.hour,
    m = part.minute,
    sec = part.second;
  [
    ["h", (h % 12) * 30 + m / 2],
    ["m", m * 6 + sec / 10],
    ["s", sec * 6],
  ].forEach(([k, a]) =>
    $("hand-" + k).setAttribute("transform", `rotate(${a} 100 100)`),
  );
}
function distanceResult(r) {
  const n = interval(r.a.jdn, r.b.jdn);
  return `<div class="distance-output"><div class="eyebrow accent">Intervalo calculado</div><h2>${fmt(n.days)} <span>${Math.abs(n.days) === 1 ? "día" : "días"}</span></h2><p>${n.days < 0 ? "En sentido inverso" : "En sentido cronológico"} · ${fmt(n.weeks)} semanas y ${n.remainder} días de distancia absoluta.</p></div><div class="distance-stats"><div><small>JDN inicial</small><code>${fmt(r.a.jdn)}</code></div><div><small>JDN final</small><code>${fmt(r.b.jdn)}</code></div><div><small>Segundos convencionales</small><code>${fmt(n.seconds)}</code></div></div>`;
}
function distancePage() {
  if (!dist.result)
    dist.result = {
      a: parseSource("auto", dist.a),
      b: parseSource("auto", dist.b),
    };
  const dfield = (k, title) =>
    `<div class="interval-field"><label class="field">${title}<select id="dist-${k}-mode">${options(dist[k + "m"], ["auto", ...modes, "jdn"])}</select></label><label class="sr-only" for="dist-${k}">${title}, valor</label><input id="dist-${k}" maxlength="150" value="${esc(dist[k])}" spellcheck="false" required></div>`;
  return (
    pageHead(
      "Aritmética del tiempo",
      "Distancia entre fechas",
      "Mide el intervalo entre dos días, incluso al cruzar calendarios o eras.",
    ) +
    `<section class="panel tool-panel"><div class="panel-title"><span class="small-icon clay">${ico("distance")}</span><h2>Comparar dos fechas</h2></div><form id="distance-form" novalidate><div class="interval-inputs">${dfield("a", "Fecha inicial")}${iconButton("convert", "Intercambiar fechas", 'data-action="swap-dates"')}${dfield("b", "Fecha final")}</div><p class="field-hint">Detección automática: GUS, gregoriano AAAA-MM-DD, cuenta larga maya o «año mes día» juliano. Para los demás, elige el calendario.</p><button class="button primary" type="submit">Calcular distancia ${ico("arrow")}</button><p role="alert" id="distance-error" class="form-error" hidden></p></form></section><section class="panel interval-result" id="interval-result" ${dist.dirty ? "hidden" : ""} aria-live="polite">${distanceResult(dist.result)}</section><div class="info-note">${ico("info")}<p>El intervalo es JDN final menos JDN inicial. Dos fechas iguales distan cero días. Los segundos se calculan a razón de 86.400 por día; no son una medición de segundos intercalares entre instantes físicos.</p></div>`
  );
}
function milestonesPage() {
  return (
    pageHead(
      "Cuaderno del atlas",
      "Hitos históricos",
      "Seis puntos de entrada para recorrer las eras y los ciclos de Gerarion.",
    ) +
    `<div class="milestone-grid">${milestones
      .map((p, i) => {
        const r = parseSource("gero", p.mark);
        return `<article class="panel milestone"><div class="milestone-top"><span class="calendar-seal ${["clay", "sage", "gold", "violet", "olive", "gold"][i]}">${ico(p.icon)}</span><span class="plate-no">LÁM. ${pad(i + 1)}</span></div><span class="eyebrow">${esc(p.tag)}</span><h2>${esc(p.title)}</h2><p>${esc(p.desc)}</p><code>${esc(r.text)}</code><button class="text-button" data-milestone="${i}">Explorar fecha ${ico("arrow")}</button></article>`;
      })
      .join("")}</div>`
  );
}
const spec =
  "https://github.com/verared/gerarion/blob/main/docs/spec/gus-3.0.0.md";
function referencePage() {
  return (
    pageHead(
      "Biblioteca del sistema",
      "Referencia técnica",
      "Las reglas de lectura, los formatos y los límites de precisión del atlas.",
      `<a class="button" href="${spec}" target="_blank" rel="noopener noreferrer">Especificación GUS ${ico("external")}</a>`,
    ) +
    `<section class="panel reference-intro"><div class="eyebrow accent">La base de toda conversión</div><h2>Un contador entero, muchos calendarios.</h2><p>Cada fecha se proyecta sobre un número de día juliano (JDN). En Gerarion, el índice cero corresponde al primer día de Keuphero del año 0 DY.</p><code class="formula">JDN = 1.719.313 + day_index</code></section><section class="panel guide"><h2>Guía de lectura</h2>${[
      [
        "El calendario mensual",
        "Los meses 01 a 12 duran 30 días. Después llega Tempalum (mes 00), con cuatro días o once en los años Gran Tempalum. El año suma 364 o 371 días. En la cuadrícula, el número grande es el día del sistema elegido; debajo figura su equivalencia. Las flechas del teclado mueven la selección por días o semanas.",
      ],
      [
        "Semanas, eras y sellos GUS",
        "La semana GUS tiene siete días: Soludyia, Loondyia, Mardyia, Aisterdyia, Trustdyia, Viendyia y Sabatyeh. Sus letras S, L, M, A, T, V, B no equivalen a los días civiles. DY identifica el origen y los años posteriores; AY, los anteriores. Un sello puede añadir hora, ciclo SC/LC y desplazamiento TCJ.",
      ],
      [
        "TCJ+0, Jerusalén y las regiones civiles",
        "En GUS 3.0.0, TCJ = TAI + 8400 segundos. TCJ+0 designa el meridiano Gerarion de Jerusalén, no su huso civil. En el selector internacional, reloj civil = TCJ+0 + diferencia de la región. Las reglas IANA del navegador determinan esa diferencia para el instante consultado, con sus cambios estacionales. Las regiones que comparten la misma hora civil exacta se agrupan en una sola fila y la etiqueta se redondea a horas enteras (TCJ±H). Por eso el sello canónico siempre se emite en TCJ+0. «Hoy» sigue la región elegida; una fecha seleccionada manualmente no se desplaza.",
      ],
      [
        "RFC 3339 y NTP no son calendarios",
        "RFC 3339 define una representación textual de instantes. El perfil de intercambio conserva el sufijo Z, precisión de segundos y sin :60. NTP es un protocolo de sincronización: su marca de 64 bits contiene 32 bits de segundos desde 1900 (módulo 2³²) y 32 de fracción. Se muestra la era para distinguir los reinicios del contador. El atlas no es un cliente NTP.",
      ],
      [
        "Cobertura y precisión",
        "Gerarion, gregoriano, juliano, egipcio, etíope y cuenta larga maya usan aritmética entera. La correspondencia maya usa la constante GMT 584283. Bahá’í usa la tabla UHJ para 172–221 BE y una convención aproximada fuera de ella. Los calendarios hebreo, chino e islámicos dependen de Intl/ICU: el chino es orientativo fuera de 1900–2100 y Umm al-Qura fuera de 1900–2074. Si falta cobertura, esa ficha lo indica sin invalidar las otras.",
      ],
      [
        "Privacidad y funcionamiento local",
        "Las conversiones, las pruebas y el reloj se ejecutan en este navegador. El atlas no envía fechas ni realiza consultas a servicios horarios. Las fuentes y la ilustración se sirven con la web. El enlace compartido guarda la fecha en el fragmento de la URL, no en una consulta al servidor. Las preferencias de ubicación y contraste se conservan solo en el dispositivo.",
      ],
    ]
      .map(
        ([title, text], n) =>
          `<details${n === 0 ? " open" : ""}><summary>${title}${ico("down")}</summary><p>${text}</p></details>`,
      )
      .join(
        "",
      )}</section><div class="source-links"><a class="panel" href="https://www.rfc-editor.org/rfc/rfc3339" target="_blank" rel="noopener noreferrer">${ico("file")}RFC 3339${ico("external")}</a><a class="panel" href="https://www.rfc-editor.org/rfc/rfc5905" target="_blank" rel="noopener noreferrer">${ico("clock")}NTPv4 · RFC 5905${ico("external")}</a><button class="panel" data-view="verificacion">${ico("shield")}Verificación local${ico("arrow")}</button></div>`
  );
}
function verifyPage() {
  return (
    pageHead(
      "Control de conformidad",
      "Verificación del núcleo",
      "Resultados reales de las pruebas del proyecto, ejecutadas en este navegador.",
    ) +
    `<section class="panel verify-banner"><span class="verify-mark">${ico("shield")}</span><div><div class="eyebrow">Suite integrada · GUS</div><h2>${failed ? "Se detectaron discrepancias" : "Núcleo verificado"}</h2><p>${passed} comprobaciones correctas de ${passed + failed}. ${failed ? "Revisa el informe antes de usar las conversiones." : "No se detectaron discrepancias en esta suite."}</p></div></section><section class="panel tool-panel"><div class="panel-title"><span class="small-icon sage">${ico("code")}</span><h2>Informe de ejecución</h2></div><pre class="test-report">${esc(report())}</pre><p class="prose">El archivo <code>tests.mjs</code> es el original del portal: comprueba fechas conocidas, reglas de Gran Tempalum, normalización de sellos y conversiones de instantes. Este informe verifica el núcleo local; no certifica el reloj ni supone una homologación por IETF o BIPM.</p><a class="text-button" href="https://github.com/verared/gerarion/blob/main/web/tests.mjs" target="_blank" rel="noopener noreferrer">Consultar las pruebas originales ${ico("external")}</a></section>`
  );
}
function render() {
  const v = state.view;
  $("crumb").textContent = pageNames[v];
  document.title = `${v === "calendario" ? "Calendario universal" : pageNames[v]} · Gerarion`;
  document.querySelectorAll(".sidebar [data-view]").forEach((el) => {
    const on = el.dataset.view === v;
    el.classList.toggle("active", on);
    if (on) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
  // Static dispatch: the view arrives from the URL hash, so rendering must
  // go through fixed branches, never a dynamic lookup.
  switch (v) {
    case "calendario":
      root.innerHTML = calendarPage();
      break;
    case "traductor":
      root.innerHTML = translatorPage();
      break;
    case "reloj":
      root.innerHTML = clockPage();
      break;
    case "distancia":
      root.innerHTML = distancePage();
      break;
    case "hitos":
      root.innerHTML = milestonesPage();
      break;
    case "referencia":
      root.innerHTML = referencePage();
      break;
    case "verificacion":
      root.innerHTML = verifyPage();
      break;
  }
  localForms(root);
  if (v === "traductor") filterResults();
  if (v === "reloj") updateClock();
}
function openDialog(html) {
  dialogOpener = document.activeElement;
  modal.innerHTML = html;
  localForms(modal);
  modal.showModal();
}
function dialogHead(kicker, title) {
  return `<div class="dialog-head"><div><div class="eyebrow accent">${kicker}</div><h2 id="dialog-title">${title}</h2></div>${iconButton("x", "Cerrar ventana", 'data-action="close-dialog"')}</div>`;
}
let zoneRows = [],
  searchAsOf = 0;
const fold = (s) =>
  String(s)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replaceAll("−", "-")
    .toLowerCase();
function openZones() {
  searchAsOf =
    state.view === "reloj" && state.paused !== null ? state.paused : Date.now();
  const ref = observe(searchAsOf),
    g = facts(ref.jdn);
  zoneRows = zoneGroups(searchAsOf).map((grp) => {
    if (!grp.ids.length)
      return {
        country: grp.countries[0],
        city: grp.label === "Sin asignación" ? "Sin zona propia en el catálogo IANA" : "No disponible",
        key: fold(grp.countries.join(" ")),
        id: null,
        label: grp.label,
      };
    const z = zoneInfo(grp.primary);
    return {
      city: z.city,
      country:
        grp.countries.slice(0, 3).join(" · ") +
        (grp.countries.length > 3 ? ` +${grp.countries.length - 3}` : ""),
      key: fold(
        [
          ...grp.ids,
          ...grp.countries,
          ...grp.ids.map((id) => zoneInfo(id)?.city || ""),
          z.city,
          grp.label,
        ].join(" "),
      ),
      id: grp.primary,
      label: grp.label,
    };
  });
  openDialog(
    dialogHead("Coordenadas del mundo", "Elegir ubicación") +
      `<p class="dialog-desc">Selecciona la región del observador. Todos los desfases se expresan respecto de <strong>TCJ+0 · Jerusalén</strong>.</p>
  <button class="zone-reference" data-zone="${REFERENCE}" aria-pressed="${state.zone === REFERENCE}"><span class="calendar-seal clay">${ico("brand")}</span><span><small>Meridiano de referencia</small><strong>TCJ+0 · Jerusalén</strong></span>${ico(state.zone === REFERENCE ? "check" : "arrow")}</button>
  <label class="search-field zone-search">${ico("search")}<input id="zone-query" type="search" placeholder="Buscar país, ciudad o desfase TCJ" aria-label="Buscar país, ciudad o desfase TCJ" autocomplete="off" aria-controls="zone-list"></label>
  <div class="zone-totals"><span>${territories.length} países y territorios</span><span>${zoneCount} regiones IANA</span></div><div class="zone-list" id="zone-list" role="group" aria-label="Regiones civiles"></div><p id="zone-matches" class="sr-only" role="status"></p>
  <p class="zone-footnote">Las regiones con la misma hora civil exacta comparten una fila; la etiqueta se redondea a horas enteras. Desfases a ${esc(g.canonical)} · ${ref.time} TCJ+0. Incluyen los cambios estacionales de la base horaria del navegador. Las regiones sin datos no se sustituyen por otro huso.</p>`,
  );
  drawZones("");
  $("zone-query").focus();
}
function drawZones(query) {
  const words = fold(query).trim().split(/\s+/),
    rows = zoneRows.filter((r) => words.every((w) => r.key.includes(w)));
  let first = true;
  const markup = rows
    .map((r) => {
      const tab = r.id && first ? "0" : "-1";
      if (r.id) first = false;
      return r.id
        ? `<button type="button" class="zone-option${r.id === state.zone ? " is-current" : ""}" data-zone="${esc(r.id)}" tabindex="${tab}" aria-pressed="${r.id === state.zone}"><span><strong>${esc(r.city)}</strong><small>${esc(r.country)}</small></span><code>${esc(r.label)}</code>${ico(r.id === state.zone ? "check" : "right")}</button>`
        : `<div class="zone-option zone-unavailable"><span><strong>${esc(r.city)}</strong><small>${esc(r.country)}</small></span><small>${esc(r.label)}</small></div>`;
    })
    .join("");
  $("zone-list").innerHTML =
    markup ||
    '<p class="empty-state">No hay coincidencias. Prueba un país, su código o una ciudad.</p>';
  $("zone-list").scrollTop = 0;
  $("zone-matches").textContent = `${rows.length} coincidencias.`;
}
function chooseZone(id) {
  if (!supportedZone(id)) {
    toast("Región no disponible en esta versión del navegador.");
    return;
  }
  state.zone = id;
  try {
    localStorage.setItem("gerarion-zone", id);
  } catch {}
  if (state.followToday) {
    const draft = state.draft;
    resetToday();
    state.draft = draft;
  }
  lastToday = selectedToday();
  if (modal.open) modal.close();
  saveURL();
  render();
  updateClock();
  toast(`Ubicación: ${zoneInfo(id).city} · ${observe(Date.now(), id).label}`);
}
function openJump() {
  const c = civil(state.j),
    type = c.year > 0 && c.year <= 9999 ? "greg" : "gero";
  openDialog(
    dialogHead("Navegación temporal", "Ir a una fecha") +
      `<p class="dialog-desc">Elige un sistema e introduce la fecha que quieres explorar.</p><form id="jump-form" novalidate><label class="field">Sistema de entrada<select id="jump-mode">${options(type, ["greg", "gero", "jdn", ...modes.filter((k) => !["greg", "gero"].includes(k))])}</select></label><label class="field">Fecha<input id="jump-value" maxlength="150" aria-describedby="jump-hint jump-error" required></label><p class="field-hint" id="jump-hint"></p><p class="form-error" role="alert" id="jump-error" hidden></p><div class="dialog-actions">${button("Cancelar", "close-dialog", null)}<button type="submit" class="button primary">Ver fecha ${ico("arrow")}</button></div></form>`,
  );
  fillJump();
  $("jump-value").focus();
}
function fillJump() {
  const k = $("jump-mode").value,
    el = $("jump-value"),
    c = civil(state.j);
  el.type = k === "greg" && c.year > 0 && c.year <= 9999 ? "date" : "text";
  el.value = sourceValue(k);
  el.placeholder =
    k === "gero" ? "2031DY-01-01-S" : k === "jdn" ? "2461363" : "año mes día";
  $("jump-hint").textContent =
    el.type === "date"
      ? "Fecha civil del calendario gregoriano. Para años anteriores al 1, usa el traductor."
      : modeHint(k);
  $("jump-error").hidden = true;
}
function openDetail(id) {
  const v = equivalent(id, state.j, state.stamp);
  openDialog(
    dialogHead("Correspondencia del día", esc(v.title)) +
      `<div class="detail-plate"><span class="calendar-seal ${v.tone}">${ico(v.icon)}</span><div><span class="eyebrow">${esc(v.family)}</span><h3>${esc(v.value)}</h3></div></div><p class="prose">${esc(v.note)}</p><dl class="fact-list"><div><dt>Día juliano</dt><dd>${fmt(state.j)}</dd></div><div><dt>Fecha Gerarion</dt><dd>${esc(facts(state.j).canonical)}</dd></div></dl><div class="dialog-actions">${v.ok ? `<button class="button" data-copy="${esc(v.raw)}">${ico("copy")}Copiar</button><button class="button primary" data-origin="${id}">Usar como origen ${ico("arrow")}</button>` : button("Cerrar", "close-dialog", null)}</div>`,
  );
}
async function copyText(value, el) {
  let ok = false;
  try {
    if (!navigator.clipboard?.writeText) throw Error();
    await navigator.clipboard.writeText(value);
    ok = true;
  } catch {
    const a = document.createElement("textarea");
    a.value = value;
    a.className = "clipboard-helper";
    (modal.open ? modal : document.body).append(a);
    a.select();
    try {
      ok = document.execCommand("copy");
    } catch {}
    a.remove();
  }
  if (ok) {
    toast("Copiado al portapapeles");
    if (el?.isConnected) {
      el.classList.add("copy-done");
      setTimeout(() => el.classList.remove("copy-done"), 1200);
    }
    return;
  }
  if (modal.open) modal.close();
  openDialog(
    dialogHead("Portapapeles", "Copiar contenido") +
      `<p class="dialog-desc">Tu navegador requiere una copia manual. Selecciona y copia este valor.</p><textarea id="manual-copy" readonly>${esc(value)}</textarea><div class="dialog-actions">${button("Listo", "close-dialog", null, "button primary")}</div>`,
  );
  $("manual-copy").select();
}
function errorAt(id, err, input) {
  const el = $(id);
  el.textContent = err.message || String(err);
  el.hidden = false;
  if (input) {
    input.setAttribute("aria-invalid", "true");
    input.focus();
  }
}
function syncMenu() {
  document.body.classList.toggle("rail-hidden", !mobile.matches && railHidden);
  document.body.classList.toggle("menu-open", mobile.matches && mobileOpen);
  const visible = mobile.matches ? mobileOpen : !railHidden;
  $("sidebar").inert = !visible;
  $("workspace").inert = mobile.matches && mobileOpen;
  $("scrim").hidden = !(mobile.matches && mobileOpen);
  $("menu-toggle").setAttribute("aria-expanded", String(visible));
  if (mobile.matches && mobileOpen) {
    $("sidebar").setAttribute("role", "dialog");
    $("sidebar").setAttribute("aria-modal", "true");
  } else {
    $("sidebar").removeAttribute("role");
    $("sidebar").removeAttribute("aria-modal");
  }
}
function closeMenu() {
  mobileOpen = false;
  syncMenu();
}
function chooseOrigin(id) {
  if (id === "gero") {
    if (state.view !== "traductor") go("traductor");
    editPivot();
    return;
  }
  const v = equivalent(id, state.j, state.stamp);
  if (!v.ok) {
    toast(v.note);
    return;
  }
  try {
    const r = parseSource(id, v.raw);
    if (r.jdn !== state.j) throw Error("El resultado inverso no coincide.");
    const adjunta = state.stamp,
      previous = state.mode;
    if (state.target === id)
      state.target =
        previous !== id ? previous : id === "chinese" ? "greg" : "chinese";
    state.mode = id;
    setDay(r.jdn, r);
    state.stamp = r.stamp || adjunta;
    state.filter = "";
    go("traductor");
    $("source-date")?.focus();
  } catch {
    toast("Esta fecha no admite conversión inversa en este navegador.");
  }
}
function doAction(action, el) {
  switch (action) {
    case "menu":
      if (mobile.matches) {
        mobileOpen = !mobileOpen;
        syncMenu();
        (mobileOpen
          ? document.querySelector(".mobile-close")
          : $("menu-toggle")
        ).focus();
      } else {
        railHidden = !railHidden;
        syncMenu();
      }
      break;
    case "contrast": {
      const on = document.documentElement.classList.toggle("contrast");
      $("contrast-control").setAttribute("aria-pressed", String(on));
      try {
        localStorage.setItem("gerarion-contrast", on ? "1" : "0");
      } catch {}
      toast(on ? "Alto contraste activado" : "Contraste estándar");
      break;
    }
    case "zones":
      openZones();
      break;
    case "swap-route":
      swapRoute();
      break;
    case "edit-pivot":
      editPivot();
      break;
    case "all-dates":
      state.allOpen = true;
      state.filter = "";
      go("traductor");
      break;
    case "jump":
      openJump();
      break;
    case "close-dialog":
      modal.close();
      break;
    case "today": {
      resetToday();
      saveURL();
      render();
      toast(
        `Hoy en ${zoneInfo(state.zone).city} · ${observe(Date.now(), state.zone).label}`,
      );
      break;
    }
    case "share":
      copyText(urlFor(), el);
      break;
    case "translate-day":
      state.filter = "";
      state.allOpen = false;
      go("traductor");
      break;
    case "pause":
      state.paused = state.paused === null ? Date.now() : null;
      render();
      break;
    case "swap-dates": {
      const a = $("dist-b").value,
        b = $("dist-a").value;
      dist.a = a;
      dist.b = b;
      dist.am = $("dist-b-mode").value;
      dist.bm = $("dist-a-mode").value;
      dist.dirty = false;
      $("dist-a").value = a;
      $("dist-b").value = b;
      $("dist-a-mode").value = dist.am;
      $("dist-b-mode").value = dist.bm;
      runForm($("distance-form"));
      break;
    }
  }
}
document.addEventListener("click", (ev) => {
  const el = ev.target.closest("button,a[data-view]");
  if (!el) return;
  if (el.matches("a") && (ev.ctrlKey || ev.metaKey || ev.shiftKey || ev.altKey))
    return;
  try {
    if (el.hasAttribute("data-run-form")) {
      runForm(el.form);
      return;
    }
    if (el.dataset.view) {
      ev.preventDefault();
      go(el.dataset.view);
      return;
    }
    if (el.hasAttribute("data-copy")) {
      copyText(el.dataset.copy, el);
      return;
    }
    if (el.dataset.copyId) {
      copyText($(el.dataset.copyId).textContent, el);
      return;
    }
    if (el.dataset.zone) {
      chooseZone(el.dataset.zone);
      return;
    }
    if (el.dataset.action) {
      doAction(el.dataset.action, el);
      return;
    }
    if (el.dataset.day) {
      refreshDay(Number(el.dataset.day), null, true);
      return;
    }
    if (el.dataset.step) {
      const step = el.dataset.step;
      refreshDay(shiftMonth(state.j, Number(step), state.system));
      root
        .querySelector(`[data-step="${step}"]`)
        ?.focus({ preventScroll: true });
      return;
    }
    if (el.dataset.detail) {
      openDetail(el.dataset.detail);
      return;
    }
    if (el.dataset.origin) {
      chooseOrigin(el.dataset.origin);
      return;
    }
    if (el.hasAttribute("data-milestone")) {
      const r = parseSource(
        "gero",
        milestones[Number(el.dataset.milestone)].mark,
      );
      setDay(r.jdn, r);
      go("calendario");
    }
  } catch (err) {
    toast(err.message);
  }
});
document.addEventListener("change", (ev) => {
  const el = ev.target;
  if (el.id === "jump-mode") fillJump();
  if (el.id === "month-system") {
    state.system = el.value;
    render();
    $("month-system").focus({ preventScroll: true });
  }
  if (el.id === "source-mode") {
    const old = state.mode;
    state.mode = el.value;
    if (state.target === state.mode) state.target = old;
    state.draft = null;
    saveURL();
    render();
    $("source-mode").focus({ preventScroll: true });
  }
  if (el.id === "target-mode") {
    if (el.value === state.mode) {
      el.value = state.target;
      swapRoute();
    } else {
      state.target = el.value;
      saveURL();
      render();
      $("target-mode").focus({ preventScroll: true });
    }
  }
  if (el.id === "dist-a-mode" || el.id === "dist-b-mode") {
    dist[el.id === "dist-a-mode" ? "am" : "bm"] = el.value;
    dist.dirty = true;
    $("interval-result").hidden = true;
  }
});
document.addEventListener("input", (ev) => {
  const el = ev.target;
  el.removeAttribute("aria-invalid");
  if (el.id === "zone-query") drawZones(el.value);
  if (el.id === "source-date") {
    state.draft = el.value;
    $("trans-pending").hidden = false;
    $("trans-error").hidden = true;
  }
  if (el.id === "calendar-filter") {
    state.filter = el.value;
    filterResults();
  }
  if (el.id === "dist-a" || el.id === "dist-b") {
    dist[el.id === "dist-a" ? "a" : "b"] = el.value;
    dist.dirty = true;
    $("interval-result").hidden = true;
  }
});
function runForm(form) {
  const id = form?.id;
  if (
    !["jump-form", "translator-form", "distance-form", "pivot-form"].includes(
      id,
    )
  )
    return;
  if (id === "pivot-form") {
    try {
      const r = interpret("gero", $("pivot-value").value, state.target);
      setDay(r.jdn, r.input);
      modal.close();
      saveURL();
      render();
      announce(`Sello interpretado: ${r.canonical}.`);
      toast(r.input.warning || "Sello interpretado");
    } catch (err) {
      errorAt("pivot-error", err, $("pivot-value"));
    }
    return;
  }
  if (id === "jump-form") {
    try {
      const r = parseSource($("jump-mode").value, $("jump-value").value);
      setDay(r.jdn, r);
      go("calendario");
      toast(r.warning || "Fecha seleccionada");
    } catch (err) {
      errorAt("jump-error", err, $("jump-value"));
    }
  }
  if (id === "translator-form") {
    try {
      const route = interpret(
          $("source-mode").value,
          $("source-date").value,
          state.target,
        ),
        r = route.input;
      const attached = r.jdn === state.j ? state.stamp : null;
      setDay(route.jdn, r);
      state.stamp = r.stamp || attached;
      state.filter = "";
      saveURL();
      render();
      announce(`Traducción completada. JDN ${r.jdn}.`);
      toast(r.warning || "Equivalencias actualizadas");
    } catch (err) {
      errorAt("trans-error", err, $("source-date"));
    }
  }
  if (id === "distance-form") {
    let input = $("dist-a");
    try {
      dist.a = input.value;
      dist.b = $("dist-b").value;
      dist.am = $("dist-a-mode").value;
      dist.bm = $("dist-b-mode").value;
      const a = parseSource(dist.am, dist.a);
      input = $("dist-b");
      const b = parseSource(dist.bm, dist.b);
      dist.result = { a, b };
      dist.dirty = false;
      $("distance-error").hidden = true;
      $("interval-result").innerHTML = distanceResult(dist.result);
      $("interval-result").hidden = false;
    } catch (err) {
      errorAt("distance-error", err, input);
      $("interval-result").hidden = true;
    }
  }
}
document.addEventListener("submit", (ev) => {
  ev.preventDefault();
  runForm(ev.target);
});
document.addEventListener(
  "toggle",
  (ev) => {
    if (ev.target.id === "clock-exchange" && ev.target.isConnected)
      state.exchangeOpen = ev.target.open;
    if (ev.target.id === "all-calendars" && ev.target.isConnected)
      state.allOpen = ev.target.open;
  },
  true,
);
document.addEventListener("keydown", (ev) => {
  if (
    modal.open &&
    $("zone-query") &&
    ["ArrowDown", "ArrowUp", "Home", "End", "Enter"].includes(ev.key)
  ) {
    const rows = [...$("zone-list").querySelectorAll("button[data-zone]")],
      isQuery = ev.target.id === "zone-query",
      i = rows.indexOf(ev.target);
    if (
      (isQuery && ["ArrowDown", "Enter"].includes(ev.key)) ||
      (i >= 0 && ev.key !== "Enter")
    ) {
      ev.preventDefault();
      if (!rows.length) return;
      if (isQuery && ev.key === "Enter") {
        chooseZone(rows[0].dataset.zone);
        return;
      }
      const n =
        isQuery || ev.key === "Home"
          ? 0
          : ev.key === "End"
            ? rows.length - 1
            : Math.max(
                0,
                Math.min(
                  rows.length - 1,
                  i + (ev.key === "ArrowDown" ? 1 : -1),
                ),
              );
      rows.forEach((r, j) => (r.tabIndex = j === n ? 0 : -1));
      rows[n].focus();
      return;
    }
  }
  if (ev.key === "Escape" && mobileOpen && !modal.open) {
    closeMenu();
    $("menu-toggle").focus();
    return;
  }
  const el = ev.target;
  if (
    portable &&
    ev.key === "Enter" &&
    !ev.isComposing &&
    el.tagName === "INPUT" &&
    el.form
  ) {
    ev.preventDefault();
    runForm(el.form);
    return;
  }
  if (el.closest?.(".day-cell")) {
    const delta = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[
      ev.key
    ];
    if (delta) {
      ev.preventDefault();
      try {
        refreshDay(state.j + delta, null, true);
      } catch (err) {
        toast(err.message);
      }
      return;
    }
  }
  if (
    ev.key === "/" &&
    !modal.open &&
    !mobileOpen &&
    !["INPUT", "SELECT", "TEXTAREA"].includes(el.tagName) &&
    !ev.ctrlKey &&
    !ev.metaKey
  ) {
    ev.preventDefault();
    openJump();
  }
  if (ev.key === "Tab" && mobileOpen) {
    const list = [...$("sidebar").querySelectorAll("a[href],button")].filter(
      (x) => x.offsetParent !== null,
    );
    if (ev.shiftKey && document.activeElement === list[0]) {
      ev.preventDefault();
      list.at(-1).focus();
    } else if (!ev.shiftKey && document.activeElement === list.at(-1)) {
      ev.preventDefault();
      list[0].focus();
    }
  }
});
modal.addEventListener("close", () => {
  if (dialogOpener?.isConnected && dialogOpener.offsetParent !== null)
    dialogOpener.focus({ preventScroll: true });
});
modal.addEventListener("click", (ev) => {
  if (ev.target === modal) {
    const b = modal.getBoundingClientRect();
    if (
      ev.clientX < b.left ||
      ev.clientX > b.right ||
      ev.clientY < b.top ||
      ev.clientY > b.bottom
    )
      modal.close();
  }
});
$("scrim").addEventListener("click", () => {
  closeMenu();
  $("menu-toggle").focus();
});
mobile.addEventListener("change", closeMenu);
window.addEventListener("hashchange", readRoute);
try {
  const high = localStorage.getItem("gerarion-contrast") === "1";
  document.documentElement.classList.toggle("contrast", high);
  $("contrast-control").setAttribute("aria-pressed", String(high));
} catch {}
$("engine-status").textContent = failed
  ? "Pruebas con errores"
  : "Cálculo verificado";
if (failed) document.body.classList.add("test-failed");
readRoute();
updateClock();
setInterval(updateClock, 1000);

// PWA (fase GUTI-1): registrar el Service Worker sin dependencias.
// El activo precacheado permite abrir la vista completa en modo avión;
// el cálculo de los diez calendarios ya era JavaScript local.
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js").then(
    () => {
      const line = document.getElementById("offline-line");
      if (line) line.hidden = false;
    },
    () => {},
  );
}
