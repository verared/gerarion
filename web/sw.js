// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
// Service Worker sin dependencias externas (fase GUTI-1, PASO 4; endurecido
// con aislamiento estricto fail-closed en la adenda v3.1.1):
// - precachea en la instalación todo el activo local del portal;
// - sirve ÚNICAMENTE los activos autorizados de la lista blanca;
// - rechaza con 403 cualquier otra petición del mismo origen (p. ej.
//   /telemetry?…), así el SW no puede convertirse en canal de red.
// Toda la interfaz es cálculo JavaScript local; el motor no consulta la
// red en ningún caso (traductor de diez calendarios, reloj TCJ y
// autodiagnóstico funcionan en modo avión).
const CACHE = "gerarion-v1";

const PRECACHE = [
  "/",
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

/* Lista blanca estricta: la ruta normalizada de la petición debe estar
 * aquí; cualquier otra del mismo origen recibe 403 (fail-closed). */
const ALLOWED = new Set(
  PRECACHE.map((p) => new URL(p, self.registration.scope).pathname),
);

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
        Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // fuera de alcance local
  // Adenda v3.1.1: sin fetch de red como fallback — solo caché y solo
  // activos de la lista blanca; el resto, rechazo explícito.
  if (!ALLOWED.has(url.pathname)) {
    event.respondWith(
      new Response("Offline-only strict isolation", { status: 403 }),
    );
    return;
  }
  /* "/" sirve index.html (navegación); el resto, su activo precacheado. */
  const target =
    url.pathname === "/"
      ? new URL("./index.html", self.registration.scope).href
      : req.url;
  event.respondWith(
    caches.match(target, { ignoreSearch: true }).then(
      (hit) =>
        hit ||
        new Response("Activo no almacenado en la caché local", { status: 404 }),
    ),
  );
});
