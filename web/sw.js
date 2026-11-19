// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
// Service Worker sin dependencias externas (fase GUTI-1, PASO 4):
// precachea en la instalación todo el activo local del portal y sirve
// cache-primero. Toda la interfaz es cálculo JavaScript local; el motor
// no consulta la red en ningún caso (traductor de diez calendarios,
// reloj TCJ y autodiagnóstico funcionan en modo avión).
const CACHE = "gerarion-v1";
const RUNTIME = "gerarion-runtime-v1";

const PRECACHE = [
  "./",
  "./index.html",
  "./style.css",
  "./app.js",
  "./manifest.webmanifest",
  "./gerarion.mjs",
  "./calendars.mjs",
  "./guti.mjs",
  "./china-table.mjs",
  "./atlas.mjs",
  "./zonas-tcj.mjs",
  "./tests.mjs",
  "./calendars.test.mjs",
  "./fonts/newsreader-latin.woff2",
  "./fonts/dm-sans-latin.woff2",
  "./fonts/AtkinsonHyperlegible-Regular.woff2",
  "./fonts/AtkinsonHyperlegible-Bold.woff2",
  "./fonts/AtkinsonHyperlegible-Italic.woff2",
  "./fonts/AtkinsonHyperlegible-BoldItalic.woff2",
  "./assets/atlas.svg",
  "./assets/esfera-armilar.webp",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => k !== CACHE && k !== RUNTIME)
            .map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // nada externo se sirve
  event.respondWith(
    caches.match(req, { ignoreSearch: false }).then((hit) => {
      if (hit) return hit;
      return fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(RUNTIME).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => hit);
    }),
  );
});
