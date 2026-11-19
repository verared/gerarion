/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/*
 * gerarion.h — Punto de entrada público unificado de libgerarion.
 *
 * Incluye el núcleo normativo GUS (gus.h) y el motor multi-calendario
 * determinista (gerarion_calendars.h). Las tablas china integera están en
 * china_table.h (CC0-1.0, generadas offline).
 */

#ifndef GERARION_H
#define GERARION_H

#define GERARION_VERSION_MAJOR 3
#define GERARION_VERSION_MINOR 2
#define GERARION_VERSION_PATCH 0
#define GERARION_VERSION_STRING "3.2.0"

/* Código extendido para fechas fuera del rango validado (misma familia
 * que los GUS_* de gus.h; no altera el núcleo congelado). */
#ifndef GERARION_EUNSUPPORTED
#define GERARION_EUNSUPPORTED 5
#endif

#include "gus.h"
#include "calendars/gerarion_calendars.h"
#include "calendars/china_table.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Versión como entero comparable: (mayor << 16) | (menor << 8) | parche. */
#define GERARION_VERSION_ID                                          \
    ((GERARION_VERSION_MAJOR << 16) | (GERARION_VERSION_MINOR << 8) | \
     GERARION_VERSION_PATCH)

#ifdef __cplusplus
}
#endif

#endif /* GERARION_H */
