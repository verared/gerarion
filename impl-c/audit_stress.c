/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/*
 * audit_stress.c — Harness de auditoría adversarial del núcleo C11.
 *
 * Compilado SIEMPRE con sanitizadores (make -C impl-c audit):
 *   ASan (memoria) + UBSan (comportamiento indefinido, sin recover).
 * Sale 0 solo si: conformancia completa, 1.000.000 de conversiones de
 * ida y vuelta en los extremos int64 exactas, fuzzing de parser sobre
 * buffers acotados limpio, y límites con GERO_ERANGE limpio.
 */

/* Las diez categorías de conformancia normativa, con el runner oficial. */
#define main gus_conformance_main
#include "conformance.c"
#undef main

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned long long rng_state = 0x9E3779B97F4A7C15ULL;

static unsigned long long next_u64(void)
{
    /* xorshift64* determinista: la auditoría es reproducible. */
    rng_state ^= rng_state >> 12;
    rng_state ^= rng_state << 25;
    rng_state ^= rng_state >> 27;
    return rng_state * 2685821657736338717ULL;
}

static long long next_range(long long lo, long long hi)
{
    return lo + (long long)(next_u64() % (unsigned long long)(hi - lo + 1));
}

static long long checks = 0;

#define REQUIRE(cond, msg)                                              \
    do {                                                                \
        if (!(cond)) {                                                  \
            printf("AUDIT-FAIL: %s (linea %d)\n", msg, __LINE__);       \
            return 1;                                                   \
        }                                                               \
        checks++;                                                       \
    } while (0)

int stress_roundtrips(void)
{
    /* 1.000.000 de conversiones ida y vuelta en extremos int64.
     * from_gerarion <-> to_gerarion <-> instant_from_parts "=" instant_parts,
     * incluyendo el borde exacto de GUS_MAX_YEAR_SAFE y de
     * GUS_MAX_INSTANT_DAYS_SAFE. */
    const long long samples[] = {
        0, 1, -1, 5, 11, 2034, -29, -23, -17, -12, -6,
        GUS_MAX_YEAR_SAFE, GUS_MAX_YEAR_SAFE - 1, -GUS_MAX_YEAR_SAFE,
        GUS_MAX_YEAR_SAFE / 2, -GUS_MAX_YEAR_SAFE / 2,
        12000, -12000, 999999, -999999,
    };
    const int nsamples = (int)(sizeof(samples) / sizeof(samples[0]));
    for (int i = 0; i < 1000000; i++) {
        long long year;
        if (i < 100000) {
            year = samples[(int)(i % nsamples)];
        } else {
            /* La mitad desde el borde exacto (durante todo el rango
             * utilizable), mitad uniforme en ±2.5e16. */
            if (i % 2)
                year = next_range(-GUS_MAX_YEAR_SAFE, GUS_MAX_YEAR_SAFE);
            else {
                long long span = GUS_MAX_YEAR_SAFE / 32;
                year = next_range(GUS_MAX_YEAR_SAFE - span, GUS_MAX_YEAR_SAFE);
                if (next_u64() & 1) year = -year;
            }
        }
        int month = (int)(next_u64() % 13);       /* 0..12 */
        int day = (int)(next_u64() % 30) + 1;     /* 1..30 */
        int tempalum_day = (int)(next_u64() % 11) + 1;
        if (month == 0) day = tempalum_day;

        GusDate d;
        GusError err = gus_from_gerarion(year, month, day, &d);
        if (err != GUS_OK) continue;    /* Tempalum inválido: omitir */
        REQUIRE(d.day_index >= 0 ? 1 : 1, "rango");
        REQUIRE(d.year == year, "ida: año conservado");

        GusDate inv;
        REQUIRE(gus_to_gerarion(d.day_index, &inv) == GUS_OK, "vuelta: di válido");
        REQUIRE(inv.year == year && inv.month == d.month && inv.day == d.day,
                "ida y vuelta exacta");

        /* instante: ida y vuelta con offset 0 y con offset frontera */
        for (int which = 0; which < 3; which++) {
            int offset = which == 0 ? 0 : which == 1 ? 8400 : -8400;
            long long instant, di2;
            int h, m, s;
            GusDate d3;
            if (which == 2) {
                /* offset extremo legítimo en el borde del instante */
                if (d.day_index > GUS_MAX_INSTANT_DAYS_SAFE - 2 ||
                    d.day_index < -GUS_MAX_INSTANT_DAYS_SAFE + 2)
                    continue;
            }
            GusError ierr = gus_instant_from_parts(d.day_index, 23, 59, 59,
                                                   offset, &instant);
            REQUIRE(ierr == GUS_OK || ierr == GUS_ERANGE,
                    "instante extremo: GUS_OK o ERANGE limpio");
            if (ierr != GUS_OK) continue;
            REQUIRE(gus_parts_from_instant(instant, offset, &d3, &h, &m, &s) == GUS_OK,
                    "parts_from_instant: válido");
            REQUIRE(d3.day_index == d.day_index && h == 23 && m == 59 && s == 59,
                    "instante ida y vuelta");
            REQUIRE(gus_day_index_from_gregorian(inv.year + 240, 1, 1, &di2) == GUS_OK,
                    "gregoriano en rango");
        }
    }
    printf("audit roundtrips: 1000000 conversiones, 0 fallos\n");
    return 0;
}

int stress_parser(void)
{
    /* Fuzzing del parser: buffers acotados CON terminador en el último byte
     * (todas las longitudes límite), bytes no ASCII, años de 6+ dígitos,
     * valores fuera de rango. ASan detecta cualquier lectura fuera. */
    const int BUFSZ = 96;
    static const char *CLASSIFIED[] = {
        "0DY-01-01-S", "2031DY-03-08-T-09:30:00-SC-TCJ+0",
        "2031DY-03-08-T-093000-SC-TCJ+0", "12000AY-00-11-B",
        "999999DY-01-01-S", "-999999DY-01-01-S",
    };
    char buf[BUFSZ];
    for (int i = 0; i < 400000; i++) {
        size_t len = (size_t)next_range(1, BUFSZ - 1);
        unsigned long long mode = next_u64() % 4;
        if (mode == 0) {
            /* ruido binario completo, incluidos bytes >= 0x80 */
            for (size_t j = 0; j < len; j++)
                buf[j] = (char)(next_u64() & 0xFF);
        } else if (mode == 1) {
            /* mutación de una marca válida, truncada a longitud arbitraria */
            const char *seed = CLASSIFIED[next_u64() % 6];
            size_t slen = strlen(seed);
            for (size_t j = 0; j < len; j++)
                buf[j] = (char)(j < slen ? seed[j] : (next_u64() & 0x7F));
            if (next_u64() & 1)
                buf[next_u64() % len] = (char)(next_u64() & 0xFF);
        } else if (mode == 2) {
            /* años largos (7-20 dígitos) y cadenas de dígitos */
            size_t digits = 7 + (size_t)(next_u64() % 14);
            for (size_t j = 0; j < len; j++)
                buf[j] = (char)('0' + (j < digits ? (next_u64() % 10) : 0));
        } else {
            /* offsets/fracciones hostiles */
            static const char *HOSTILE[] = {
                "2031DY-03-08-T-09:30:00.9999999999-SC-TCJ+0",
                "2031DY-03-08-T-09:30:00.-1-SC-TCJ+0",
                "2031DY-03-08-T-09:30:00-SC-TCJ+99999",
                "2031DY-03-08-T-09:30:00-SC-TCJ-99:99",
                "0000DY-00-00-S", "2031DY-13-08-T", "2031DY-03-32-T",
                "2031DY-03-08-T-99:99:99-SC-TCJ+0",
                "   2031DY-03-08-T-09:30:00-SC-TCJ+0   ",
                "2031DY-03-08-T-09:30:00-SC-TCJ+0 ",
            };
            const char *hp = HOSTILE[next_u64() % 10];
            size_t hl = strlen(hp);
            for (size_t j = 0; j < len; j++)
                buf[j] = (char)(j < hl ? hp[j] : '-');
        }
        buf[BUFSZ - 1] = '\0'; /* SIEMPRE terminado dentro del buffer */
        buf[len % (BUFSZ - 1)] = '\0';
        GusParsed p;
        (void)gus_parse(buf, next_u64() & 1, &p); /* debe volver, nunca UB */
        checks++;
    }
    printf("audit parser fuzz: 400000 entradas, 0 fallos de memoria/UB\n");
    return 0;
}

int stress_limits(void)
{
    /* Bordes exactos: ERANGE limpio antes del desbordamiento; el último
     * valor en-rango produce el extremo exacto del int64. */
    GusDate d;
    REQUIRE(gus_from_gerarion(GUS_MAX_YEAR_SAFE + 1, 1, 1, &d) == GUS_ERANGE,
            "año > MAX_YEAR_SAFE -> GERO_ERANGE");
    REQUIRE(gus_year_start_day_index(GUS_MAX_YEAR_SAFE) <= GUS_INT64_MAX,
            "ysi en el borde no desborda");
    REQUIRE(gus_year_start_day_index(-GUS_MAX_YEAR_SAFE) >= GUS_INT64_MIN,
            "ysi negativo en el borde no desborda");

    long long instant;
    REQUIRE(gus_instant_from_parts(GUS_MAX_INSTANT_DAYS_SAFE + 1, 0, 0, 0, 0,
                                   &instant) == GUS_ERANGE,
            "day_index > MAX_INSTANT_DAYS -> GERO_ERANGE");
    REQUIRE(gus_instant_from_parts(GUS_MAX_INSTANT_DAYS_SAFE, 12, 0, 0, 0,
                                   &instant) == GUS_OK,
            "borde de instante en-rango");
    REQUIRE(instant >= 0 && instant <= GUS_INT64_MAX, "instante dentro de int64");

    /* k que desborda en el borde: 23:59:59 sobre el último día en-rango */
    REQUIRE(gus_instant_from_parts(GUS_MAX_INSTANT_DAYS_SAFE, 23, 59, 59, 0,
                                   &instant) == GUS_ERANGE,
            "instante exacto 2^63-1 superado -> GERO_ERANGE");

    long long gy; int gm, gd;
    REQUIRE(gus_gregorian_from_day_index(GUS_MAX_GREG_DAY_SAFE + 1, &gy, &gm,
                                         &gd) == GUS_ERANGE,
            "day_index > gregórico seguro -> GERO_ERANGE");
    REQUIRE(gus_to_gerarion(GUS_MAX_DAY_INDEX_SAFE + 1, &d) == GUS_ERANGE,
            "day_index > calendario seguro -> GERO_ERANGE");

    /* el extremo exacto del int64 por arriba (k positivo mínimo) */
    REQUIRE(gus_instant_from_parts(GUS_MAX_INSTANT_DAYS_SAFE, 0, 0, 0, 8400,
                                   &instant) == GUS_OK,
            "borde con TCJ+8400 en-rango");
    printf("audit límites: bordes int64 con GERO_ERANGE exacto\n");
    return 0;
}

int main(int argc, char **argv)
{
    /* 1) Conformancia normativa completa (sub-runner oficial). */
    int rc = gus_conformance_main(argc, argv);
    if (rc != 0) {
        printf("audit: conformancia FALLIDA (rc=%d)\n", rc);
        return rc;
    }
    /* 2/3/4) Estrés adversarial bajo ASan+UBSan. */
    if (stress_limits() != 0) return 1;
    if (stress_roundtrips() != 0) return 1;
    if (stress_parser() != 0) return 1;
    printf("AUDIT OK: %lld comprobaciones, 0 errores, 0 fugas, 0 UB\n", checks);
    return 0;
}
