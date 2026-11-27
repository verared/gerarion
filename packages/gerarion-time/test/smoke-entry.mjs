// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: 2026 verared contributors
// Entrada de smoke para Node y Deno (sin imports node:*).
import { runSmoke } from "./smoke-runtime.mjs";

const result = await runSmoke();
console.log(`smoke OK: ${result.verdict} — ${result.reason}`);
