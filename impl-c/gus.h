/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/*
 * gus.h — Paraguas de compatibilidad (umbrella) de libgerarion.
 *
 * Desde la reorganización modular, el núcleo vive dividido por dominio:
 *   core/gus_core.h    — calendario, formato canónico, instante (TCJ+GUS)
 *   tai/gus_tai.h      — tabla TAI − UTC versionada y offset TCJ (TCJ/INTEROP)
 *   clock/gus_clock.h  — máquina de estados de reloj §6.3 (GTS)
 * Este encabezado incluye los tres y conserva el API histórico de gus.h
 * intacto: el código existente sigue compilando sin cambios.
 */

#ifndef GUS_H
#define GUS_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "core/gus_core.h"
#include "tai/gus_tai.h"
#include "clock/gus_clock.h"

#endif /* GUS_H */
