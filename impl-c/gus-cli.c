/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/*
 * gus-cli.c — Servidor de líneas para fuzzing diferencial de impl-c.
 *
 * Protocolo (una operación por línea; respuestas JSON una por línea), idéntico
 * a web/conformance.mjs --cli y al correductor Python de tools/fuzz_diff.py:
 *
 *   tg <day_index>              -> {"ok":true,"di":..,"year":..,"era":..,"month":..,"day":..,"abbr":..,"canon":".."}
 *   fg <year> <month> <day>     -> {"ok":true,"day_index":..,"canon":".."} | {"ok":false,"error":"GERO_.."}
 *   gr <day_index>              -> {"ok":true,"di":..,"greg":"Y-M-D","greg_year":..,"greg_month":..,"greg_day":..}
 *   pt <raw...>                 -> {"ok":true,"canon":"..","flags":[..]} | {"ok":false,"error":"GERO_.."}
 *   in <day_index> <h> <m> <s>  -> {"ok":true,"instant":".."} | {"ok":false,"error":"GERO_EINVAL"}
 *
 * Uso: ./gus-cli   (lee stdin, escribe stdout; para harness, no humanos)
 */

#include "gus.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *err_name(GusError e)
{
    switch (e) {
    case GUS_OK: return "GUS_OK";
    case GUS_EINVAL: return "GERO_EINVAL";
    case GUS_ETEMPALUM: return "GERO_ETEMPALUM";
    case GUS_EWEEK: return "GERO_EWEEK";
    }
    return "GERO_EINVAL";
}

static void print_err(GusError e)
{
    printf("{\"ok\":false,\"error\":\"%s\"}\n", err_name(e));
}

static void handle(const char *line)
{
    char cmd[4] = { 0, 0, 0, 0 };
    const char *rest = line;
    while (*rest == ' ') rest++;
    const char *sp = strchr(rest, ' ');
    size_t cmd_len = sp ? (size_t)(sp - rest) : strlen(rest);
    if (cmd_len > 2) return; /* comando desconocido => sin salida */
    memcpy(cmd, rest, cmd_len);
    rest = sp ? sp + 1 : "";
    while (*rest == ' ') rest++;

    if (strcmp(cmd, "tg") == 0) {
        long long di = strtoll(rest, NULL, 10);
        GusDate d;
        if (gus_to_gerarion(di, &d) != GUS_OK) { print_err(GUS_EINVAL); return; }
        char canon[48];
        GusParsed p = { 0 };
        p.date = d;
        gus_canonical(&p, canon, sizeof(canon));
        printf("{\"ok\":true,\"di\":%lld,\"year\":%lld,\"era\":\"%s\",\"month\":%d,\"day\":%d,\"abbr\":\"%c\",\"canon\":\"%s\"}\n",
            di, d.year < 0 ? -d.year : d.year, d.year >= 0 ? "DY" : "AY",
            d.month, d.day, d.abbr, canon);
    } else if (strcmp(cmd, "fg") == 0) {
        long long y = strtoll(rest, NULL, 10);
        const char *q = strstr(rest, " ");
        if (!q) { print_err(GUS_EINVAL); return; }
        long long m = strtoll(q + 1, NULL, 10);
        const char *q2 = strstr(q + 1, " ");
        if (!q2) { print_err(GUS_EINVAL); return; }
        long long d2 = strtoll(q2 + 1, NULL, 10);
        GusDate d;
        GusError err = gus_from_gerarion(y, (int)m, (int)d2, &d);
        if (err != GUS_OK) { print_err(err); return; }
        char canon[48];
        GusParsed pp = { 0 };
        pp.date = d;
        gus_canonical(&pp, canon, sizeof(canon));
        printf("{\"ok\":true,\"day_index\":%lld,\"canon\":\"%s\"}\n", d.day_index, canon);
    } else if (strcmp(cmd, "gr") == 0) {
        long long di = strtoll(rest, NULL, 10);
        long long gy;
        int gm, gd;
        gus_gregorian_from_day_index(di, &gy, &gm, &gd);
        printf("{\"ok\":true,\"di\":%lld,\"greg\":\"%lld-%d-%d\",\"greg_year\":%lld,\"greg_month\":%d,\"greg_day\":%d}\n",
               di, gy, gm, gd, gy, gm, gd);
    } else if (strcmp(cmd, "pt") == 0) {
        GusParsed p;
        GusError err = gus_parse(rest, false, &p);
        if (err != GUS_OK) { print_err(err); return; }
        char canon[64];
        gus_canonical(&p, canon, sizeof(canon));
        printf("{\"ok\":true,\"canon\":\"%s\",\"flags\":[", canon);
        int printed = 0;
        if (p.cycle_corrected) { printf("\"cycle_corrected\""); printed++; }
        if (p.era_assumed) { printf("%s\"era_assumed_DY\"", printed ? "," : ""); printed++; }
        if (p.weekday_corrected) { printf("%s\"weekday_corrected\"", printed ? "," : ""); }
        printf("]}\n");
    } else if (strcmp(cmd, "in") == 0) {
        long long di = strtoll(rest, NULL, 10);
        const char *q = strstr(rest, " ");
        if (!q) { print_err(GUS_EINVAL); return; }
        long long h = strtoll(q + 1, NULL, 10);
        const char *q2 = strstr(q + 1, " ");
        if (!q2) { print_err(GUS_EINVAL); return; }
        long long m = strtoll(q2 + 1, NULL, 10);
        const char *q3 = strstr(q2 + 1, " ");
        if (!q3) { print_err(GUS_EINVAL); return; }
        long long s = strtoll(q3 + 1, NULL, 10);
        long long instant;
        GusError err = gus_instant_from_parts(di, (int)h, (int)m, (int)s, 0, &instant);
        if (err != GUS_OK) { print_err(err); return; }
        printf("{\"ok\":true,\"instant\":\"%lld\"}\n", instant);
    }
}

int main(void)
{
    char line[512];
    while (fgets(line, sizeof(line), stdin)) {
        size_t len = strlen(line);
        while (len > 0 && (line[len - 1] == '\n' || line[len - 1] == '\r')) line[--len] = '\0';
        if (len == 0) continue;
        handle(line);
    }
    return 0;
}
