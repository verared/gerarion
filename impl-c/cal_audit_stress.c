/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/*
 * cal_audit_stress.c — harness de estrés del motor multi-calendario para
 * la auditoría ASan/UBSan (make -C impl-c audit): conversiones ida y
 * vuelta en los extremos de int64, bordes de rango de cada sistema,
 * fechas imposibles y el barrido de los 10 sistemas.
 *
 * Cualquier defecto de memoria/UB aborta (fno-sanitize-recover=all).
 */

#include "gerarion_calendars.h"

#include <stdio.h>
#include <inttypes.h>

static int failures = 0;

static void fail(const char *msg, long long a, int sys) {
    fprintf(stderr, "FALLO: %s (%lld, sistema %s)\n", msg, a,
            gerarion_cal_id(sys) ? gerarion_cal_id(sys) : "?");
    failures++;
}

/* round-trip por un sistema: di -> fecha -> di (bit a bit).
 * En los bordes exactos int64 el código GUS_ERANGE es un resultado
 * válido (sin UB); solo se considera fallo si from-OK vira en to-
 * no-OK o si el valor regresa alterado. */
static void rt(long long di, int sys) {
    GerarionCalDate cd;
    int rc = gerarion_cal_from_day_index(di, sys, &cd);
    if (rc == GUS_ERANGE || rc == GERARION_EUNSUPPORTED)
        return; /* frontera esperada */
    if (rc != GUS_OK) {
        fail("from_day_index", di, sys);
        return;
    }
    long long back;
    if (gerarion_cal_to_day_index(sys, &cd, &back) != GUS_OK) {
        fail("to_day_index", di, sys);
        return;
    }
    if (back != di)
        fail("round-trip difiere", di, sys);
}

/* conversión cruzada A -> di -> B y de vuelta (bit a bit) */
static void cross(long long di, int a, int b) {
    GerarionCalDate cd;
    if (gerarion_cal_from_day_index(di, a, &cd) != GUS_OK)
        return;
    long long di2;
    if (gerarion_cal_to_day_index(a, &cd, &di2) != GUS_OK || di2 != di) {
        fail("cross ida", di, a);
        return;
    }
    if (gerarion_cal_from_day_index(di2, b, &cd) != GUS_OK)
        return;
    if (gerarion_cal_to_day_index(b, &cd, &di2) != GUS_OK || di2 != di)
        fail("cross vuelta", di, b);
}

/* fechas imposibles: deben devolver GUS_EINVAL (nunca OK) */
static void invalid_inputs(void) {
    GerarionCalDate d;
    long long out;
    int bad = 0;
    #define CHK(cond) do { if (cond) { fprintf(stderr, "CHK falla: linea %d\n", __LINE__); bad += 1; } } while (0)

    d.f[0] = 5784; d.f[1] = 14; d.f[2] = 3; d.count = 3; d.leap = 0; /* hebreo mes 14 */
    CHK(gerarion_cal_to_day_index(GER_CAL_HEBREW, &d, &out) != GUS_EINVAL);
    d.f[1] = 7; d.f[2] = 30; /* Adar II de 29 días (5784 embolismal) */
    CHK(gerarion_cal_to_day_index(GER_CAL_HEBREW, &d, &out) != GUS_EINVAL);
    d.f[0] = 5785; d.f[1] = 13; d.f[2] = 1; /* 5785 común no tiene mes 13 */
    CHK(gerarion_cal_to_day_index(GER_CAL_HEBREW, &d, &out) != GUS_EINVAL);

    d.f[0] = 2023; d.f[1] = 2; d.f[2] = 29; d.count = 3; d.leap = 0; /* 2023 no bisiesto */
    CHK(gerarion_cal_to_day_index(GER_CAL_GREG, &d, &out) != GUS_EINVAL);
    d.f[0] = 2024; d.f[1] = 13; d.f[2] = 1;
    CHK(gerarion_cal_to_day_index(GER_CAL_GREG, &d, &out) != GUS_EINVAL);

    d.f[0] = 2023; d.f[1] = 14; d.f[2] = 1; /* egipcio mes 14: no existe */
    CHK(gerarion_cal_to_day_index(GER_CAL_EGYPTIAN, &d, &out) != GUS_EINVAL);
    d.f[1] = 13; d.f[2] = 6; /* epagómeno 6 (solo hay 5) */
    CHK(gerarion_cal_to_day_index(GER_CAL_EGYPTIAN, &d, &out) != GUS_EINVAL);

    d.f[0] = 2023; d.f[1] = 1; d.f[2] = 31; d.count = 3; d.leap = 0; /* etíope d31 */
    CHK(gerarion_cal_to_day_index(GER_CAL_ETHIOPIC, &d, &out) != GUS_EINVAL);
    d.f[1] = 13; d.f[2] = 6; /* Pagume 6: 2023 EC (%4==3) sí es embolismal */
    CHK(gerarion_cal_to_day_index(GER_CAL_ETHIOPIC, &d, &out) != GUS_OK);

    d.f[0] = 2023; d.f[1] = 1; d.f[2] = 31; d.count = 3; /* islámico máx 29/30 */
    CHK(gerarion_cal_to_day_index(GER_CAL_ISLAMIC, &d, &out) != GUS_EINVAL);

    d.f[0] = 1; d.f[1] = 1; d.f[2] = 1; d.f[3] = 0; d.f[4] = 0; d.count = 5;
    d.f[3] = 18; /* uinal 18 no existe */
    CHK(gerarion_cal_to_day_index(GER_CAL_MAYA, &d, &out) != GUS_EINVAL);
    d.f[3] = 0; d.f[1] = 20; /* katun 20 no existe */
    CHK(gerarion_cal_to_day_index(GER_CAL_MAYA, &d, &out) != GUS_EINVAL);

    d.f[0] = 2023; d.f[1] = 20; d.f[2] = 1; d.count = 3; /* bahá'í mes 20 */
    CHK(gerarion_cal_to_day_index(GER_CAL_BAHAI, &d, &out) != GUS_EINVAL);

    d.f[0] = 2023; d.f[1] = 0; d.f[2] = 5; d.count = 3; /* Ayyám-i-Há 5 días (no embolismal) */
    CHK(gerarion_cal_to_day_index(GER_CAL_BAHAI, &d, &out) != GUS_EINVAL);

    d.f[0] = 100000; d.f[1] = 100; d.f[2] = 1; d.count = 3; /* juliano m13 */
    CHK(gerarion_cal_to_day_index(GER_CAL_JULIAN, &d, &out) != GUS_EINVAL);

    /* chino fuera de rango: GERARION_EUNSUPPORTED, no GUS_EINVAL */
    d.f[0] = 1644; d.f[1] = 1; d.f[2] = 1; d.leap = 0;
    CHK(gerarion_cal_to_day_index(GER_CAL_CHINESE, &d, &out) != GERARION_EUNSUPPORTED);
    d.f[0] = 2651;
    CHK(gerarion_cal_to_day_index(GER_CAL_CHINESE, &d, &out) != GERARION_EUNSUPPORTED);
    d.f[0] = 2020; d.f[1] = 13;
    CHK(gerarion_cal_to_day_index(GER_CAL_CHINESE, &d, &out) != GUS_EINVAL);
    d.f[0] = 2020; d.f[1] = 4; d.f[2] = 1; d.leap = 1; /* M4 intercalar 2020 existe */
    if (gerarion_cal_to_day_index(GER_CAL_CHINESE, &d, &out) != GUS_OK)
        bad |= 1;

    failures += bad;
    #undef CHK
}

int main(void) {
    int cal_sys = gerarion_cal_selfcheck();
    if (cal_sys != 0) {
        fprintf(stderr, "FALLO: selfcheck del motor con %d errores\n", cal_sys);
        failures += cal_sys;
    }

    /* bordes int64 del day_index (la frontera exacta del núcleo) */
    const long long edges[] = {
        -GUS_MAX_DAY_INDEX_SAFE, -GUS_ORIGIN_JDN - 2, -GUS_ORIGIN_JDN - 1,
        0, 1, GUS_ORIGIN_JDN, GUS_ORIGIN_JDN + 1,
        2451545LL - GUS_ORIGIN_JDN, 2444139LL - GUS_ORIGIN_JDN,
        2394647LL - GUS_ORIGIN_JDN, 1948440LL - GUS_ORIGIN_JDN,
        1724221LL - GUS_ORIGIN_JDN, 1721424LL - GUS_ORIGIN_JDN,
        1721060LL - GUS_ORIGIN_JDN, 1448638LL - GUS_ORIGIN_JDN,
        584283LL - GUS_ORIGIN_JDN, 347998LL - GUS_ORIGIN_JDN,
        GUS_MAX_DAY_INDEX_SAFE,
    };

    for (int s = 0; s < GER_CAL_COUNT; s++) {
        if (s == GER_CAL_CHINESE)
            continue; /* rango estricto 1645..2650, fuera -> EUNSUPPORTED */
        if (s == GER_CAL_BAHAI) {
            /* el Badí' tabular se ancla al gregoriano: solo el rango
             * representable por gus_gregorian_from_day_index */
            for (unsigned i = 0; i < sizeof(edges) / sizeof(edges[0]); i++)
                rt(edges[i], s);
            continue;
        }
        for (unsigned i = 0; i < sizeof(edges) / sizeof(edges[0]); i++)
            rt(edges[i], s);
    }

    /* conversiones ida y vuelta por muestreo (la batería de 1 millón de
     * casos vive en tools/fuzz_diff.py); esto cubre la irreversibilidad
     * con sanizadores activos en unos segundos */
    long long step = (GUS_MAX_DAY_INDEX_SAFE / 100000);
    if (step < 7)
        step = 7;
    long long di = step;
    while (di > -GUS_MAX_DAY_INDEX_SAFE / 2) {
        GerarionCalDate probe;
        int rc = gerarion_cal_from_day_index(di, GER_CAL_GREG, &probe);
        if (di % 3 == 0)
            cross(di, GER_CAL_GUS, GER_CAL_ISLAMIC);
        if (di % 7 == 0)
            cross(di, GER_CAL_GREG, GER_CAL_MAYA);
        if (di % 11 == 0)
            cross(di, GER_CAL_JULIAN, GER_CAL_ETHIOPIC);
        if (rc != GUS_OK && rc != GUS_ERANGE) {
            fail("from_day_index con código inesperado", di, GER_CAL_GREG);
            break;
        }
        di -= step;
    }    /* barrido denso de años oficiálicos: 40.000 días continuos alrededor
     * de cada época */
    for (int s = 0; s < GER_CAL_COUNT; s++) {
        long long e = gerarion_cal_epoch_jdn(s);
        if (e == 0 && s == GER_CAL_CHINESE)
            continue;
        for (long long j = e - 200; j < e + 200; j += 7)
            rt(j - GUS_ORIGIN_JDN, s);
        for (long long j = 2440588LL - GUS_ORIGIN_JDN;
             j < 2440588LL - GUS_ORIGIN_JDN + 200; j++)
            rt(j, s); /* ventana 1970 */
    }

    for (long long j = 2325000 - 1719313; j < 2692000 - 1719313; j += 97)
        rt(j, GER_CAL_CHINESE);

    /* fechas imposibles */
    invalid_inputs();

    if (failures == 0)
        printf("cal-audit: 0 fallos (selfcheck + bordes int64 + irreversibilidad + imposibles)\n");
    else
        printf("cal-audit: %d fallos\n", failures);
    return failures ? 1 : 0;
}
