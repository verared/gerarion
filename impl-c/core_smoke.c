/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/* core_smoke.c — humo de compilación independiente de libgerarion-core:
 * SOLO core/gus_core.h (sin reloj de SO, sin tabla TAI−UTC, sin
 * calendarios). Demuestra que el núcleo TCJ+GUS es autocontenido para
 * microcontroladores. NO forma parte de libgerarion. */

#include "core/gus_core.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    long long di = 0;
    assert(gus_day_index_from_gregorian(2026, 3, 17, &di) == GUS_OK);
    GusDate d;
    assert(gus_to_gerarion(di, &d) == GUS_OK);
    char buf[48];
    GusParsed p;
    p.date = d;
    p.has_time = 0;
    assert(gus_canonical(&p, buf, sizeof(buf)) == GUS_OK);
    printf("core-smoke: %s (%lld)\n", buf, di);
    return gus_quick_verify(buf) ? 0 : 1;
}
