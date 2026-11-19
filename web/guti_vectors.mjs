// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
// Corredor de los vectores compartidos del motor multi-calendario
// (vectors/guti-calendars-001.json, CC0-1.0) sobre web/guti.mjs.
//
// Uso Node (sin dependencias):  node web/guti_vectors.mjs
//   exit 0 = todos los vectores bit a bit; 1 = desacuerdo con el set.
// Con vectores opcionales:      node web/guti_vectors.mjs [ruta.json]

import { readFileSync } from 'node:fs';
import { gutiFromDayIndex, gutiToDayIndex, gutiMetadata, GUTI_SYSTEM_IDS } from './guti.mjs';

const path = process.argv[2] || new URL('../vectors/guti-calendars-001.json', import.meta.url).pathname;
const doc = JSON.parse(readFileSync(path, 'utf8'));

let pass = 0;
const fails = [];

function check(name, cond, extra) {
  if (cond) { pass++; } else { fails.push(`${name}${extra ? ' | ' + extra : ''}`); }
}

// 1. vectors: ida y vuelta bit a bit
for (const v of doc.vectors) {
  let from = null, fromErr = null;
  try { from = gutiFromDayIndex(v.day_index, v.system); }
  catch (e) { fromErr = e; }
  if (fromErr) {
    check(`from ${v.system} di=${v.day_index}`, false, `${v.system} lanzó ${fromErr.message}`);
    continue;
  }
  const got = JSON.stringify(from.fields);
  const want = JSON.stringify(v.fields);
  check(`from ${v.system} di=${v.day_index}`, got === want, `esperado ${want}, obtenido ${got}`);
  try {
    const back = gutiToDayIndex(v.system, v.fields);
    check(`to ${v.system} di=${v.day_index}`, back === v.day_index,
          `ida y vuelta: ${back} ≠ ${v.day_index}`);
  } catch (e) {
    check(`to ${v.system} di=${v.day_index}`, false, `lanzó ${e.message}`);
  }
}

// 2. cross: palíndromo A→GUS→B→GUS→A
for (const c of doc.cross) {
  try {
    const d1 = gutiFromDayIndex(c.day_index, c.from);
    const di2 = gutiToDayIndex(c.from, d1.fields);
    const d2 = gutiFromDayIndex(di2, c.to);
    const di3 = gutiToDayIndex(c.to, d2.fields);
    const d3 = gutiFromDayIndex(di3, c.from);
    check(`cross ${c.from}->${c.to} di=${c.day_index}`,
          di3 === c.day_index && d3.fields.year === d1.fields.year,
          `d3=${JSON.stringify(d3.fields)} d1=${JSON.stringify(d1.fields)}`);
  } catch (e) {
    check(`cross ${c.from}->${c.to} di=${c.day_index}`, false, e.message);
  }
}

// 3. invalid: rechazo con código GERO_EINVAL (o EINVAL del núcleo congelado)
for (const v of doc.invalid) {
  let err = null;
  try { gutiToDayIndex(v.system, v.fields); } catch (e) { err = e; }
  check(`invalid ${v.system} ${JSON.stringify(v.fields)}`,
        err !== null && (String(err.message).startsWith('GERO_EINVAL')
                         || err.name === 'GeroError'),
        err ? err.message : 'aceptado (¡no debe!)');
}

// 4. unsupported: GERO_EUNSUPPORTED (day_index o fields)
for (const v of doc.unsupported) {
  let err = null;
  try {
    if (v.day_index !== undefined) gutiFromDayIndex(v.day_index, v.system);
    else gutiToDayIndex(v.system, v.fields);
  } catch (e) { err = e; }
  const ok = err !== null && String(err.message).startsWith('GERO_EUNSUPPORTED');
  check(`unsupported ${v.system}`, ok,
        err ? err.message : 'aceptado (¡no debe!)');
}

// 5. erange: GERO_ERANGE
for (const v of doc.erange) {
  let err = null;
  try { gutiToDayIndex(v.system, v.fields); } catch (e) { err = e; }
  const ok = err !== null && String(err.message).startsWith('GERO_ERANGE');
  check(`erange ${v.system} ${JSON.stringify(v.fields)}`, ok,
        err ? err.message : 'aceptado (¡no debe!)');
}

// 6. metadatos de los 10 sistemas
check('10 sistemas registrados', GUTI_SYSTEM_IDS.length === 10,
      `obtenidos ${GUTI_SYSTEM_IDS.length}`);
for (const sys of GUTI_SYSTEM_IDS) {
  const meta = gutiMetadata(sys);
  check(`metadatos ${sys}`, meta !== null && meta.field_names.length >= 3,
        meta ? 'incompletos' : 'ausentes');
}
const total = pass + fails.length;
console.log(`guti-vectors (JS): ${pass}/${total} correctos` +
            (fails.length ? ` — ${fails.length} fallos` : ''));
if (fails.length) {
  for (const f of fails.slice(0, 10)) console.log('FALLO:', f);
  process.exit(1);
}
