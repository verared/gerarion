// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
/**
 * web/gerarion.mjs — re-exportador de compatibilidad (v3.2.0).
 *
 * El núcleo vive ahora dividido por dominio:
 *   engine/core.mjs    — GUS puro (calendario, formato, instantes)
 *   engine/tcj-tai.mjs — TCJ + tabla TAI−UTC versionada + perfil 3339
 * Este módulo conserva el API unido para Node, tests y consumidores
 * históricos: `import * as g from "web/gerarion.mjs"` sigue funcionando.
 */

export * from "./engine/core.mjs";
export * from "./engine/tcj-tai.mjs";
