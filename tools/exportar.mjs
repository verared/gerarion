#!/usr/bin/env node
// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
// Exportador del HTML autónomo: incrusta los módulos JavaScript, el CSS, las
// fuentes, los vectores y las licencias en un único archivo navegable sin
// conexión ni servidor. Es un producto generado: no se edita a mano.
//
// Uso:
//   npm exec --yes --package=esbuild@0.28.2 -- node tools/exportar.mjs [salida.html]
//   (si esbuild está instalado, basta `node tools/exportar.mjs [salida.html]`;
//    la ruta del binario se indica con la variable ESBUILD)
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";

const WEB = resolve(dirname(fileURLToPath(import.meta.url)), "..", "web");
const OUT = resolve(process.argv[2] || "Gerarion.html");

function bundle() {
  const bin = process.env.ESBUILD || "esbuild";
  const args = [
    resolve(WEB, "app.js"),
    "--bundle",
    "--format=esm",
    "--target=es2022",
    "--platform=browser",
    "--alias:assets=./dataurl-stub",
  ];
  try {
    return execFileSync(bin, args, {
      cwd: WEB,
      inputEncoding: "utf8",
      maxBuffer: 1 << 26,
    });
  } catch (err) {
    throw new Error(
      `No se pudo ejecutar esbuild (${bin}). Si no está instalado, usa:\n` +
        `  npm exec --yes --package=esbuild@0.28.2 -- node tools/exportar.mjs\n\n${err.message}`,
    );
  }
}

const inline64 = (rel, mime) =>
  `data:${mime};base64,${readFileSync(resolve(WEB, rel)).toString("base64")}`;

const js = bundle();

// CSS local → fuentes embebidas.
let css = readFileSync(resolve(WEB, "style.css"), "utf8").replace(
  /url\("fonts\/([a-z-]+)\.woff2"\)/g,
  (_, f) => `url("${inline64(`fonts/${f}.woff2`, "font/woff2")}")`,
);

// Sprite de iconos en línea: los <use href="assets/atlas.svg#id"> locales no
// se resuelven desde data: URI en todos los navegadores.
const dot =
  /<svg[^>]*>([\s\S]*?)<\/svg>/.exec(
    readFileSync(resolve(WEB, "assets/atlas.svg"), "utf8"),
  )[1] || "";
const sprite = `<svg style="display:none" aria-hidden="true" focusable="false">${dot}</svg>`;

let html = readFileSync(resolve(WEB, "index.html"), "utf8")
  .replace(/<link\s+rel="preload"[\s\S]*?\/>\n?/g, "")
  .replace(
    /<link rel="icon"[^>]*>/,
    '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 24 24\'%3E%3Ccircle cx=\'12\' cy=\'12\' r=\'4.5\' fill=\'%23a55439\'/%3E%3C/svg%3E" />',
  )
  .replace(/<link rel="stylesheet" href="style\.css" \/>/, () => `<style>\n${css}\n</style>`)
  .replace(/<script type="module" src="app\.js"><\/script>/, () => `<script type="module">\n${js}\n</script>`)
  .replace(/<body>/, `<body data-portable="true">\n${sprite}`)
  .replaceAll('href="assets/atlas.svg#', 'href="#');

// La lámina decorativa se embebe para que la edición portátil no dependa de
// archivos vecinos (los datos nunca dependen de la imagen).
const plate64 = inline64("assets/esfera-armilar.webp", "image/webp");
html = html.replace(
  /src="assets\/esfera-armilar\.webp"/,
  `src="${plate64}"`,
);

// CSP calculada sobre el html final: el hash del style y script inline must
// match exactly; gererate both hashes over the two blocks.
const styleBlock = /<style>\n([\s\S]*?)\n<\/style>/.exec(html)[1];
const scriptBlock = /<script type="module">\n([\s\S]*?)\n<\/script>/.exec(html)[1];
const h = (s) => `'sha256-${createHash("sha256").update(s, "utf8").digest("base64")}'`;
const csp = `default-src 'none'; style-src 'self' ${h(styleBlock)}; script-src 'self' ${h(scriptBlock)}; img-src data:; font-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'`;
html = html.replace(
  /<\/head>/,
  `<meta http-equiv="Content-Security-Policy" content="${csp}" />\n  </head>`,
);
html = html.replace(
  /<\/title>/,
  `</title>\n    <meta name="generator" content="tools/exportar.mjs · edición portátil" />`,
);

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, html);
console.log(
  `OK ${OUT} (${(readFileSync(OUT).length / 1024).toFixed(0)} KiB, fuentes + sprite + lámina embebidas).`,
);
