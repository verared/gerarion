/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/*
 * gus.c — Núcleo GUS 2.1 en C (segunda implementación independiente).
 *
 * Aritmética entera exacta; sin punto flotante. El acumulador solar
 * (Gran Tempalum) es simétrico e infinito en ambas eras (DY y AY), con
 * módulo euclidiano y división piso explícitos, idéntico bit a bit a la
 * implementación de referencia (src/gerarion/calendar.py) — spec §3.
 */

#include "gus.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---------------- calendario ---------------- */

/* Módulo euclidiano: resultado en [0, m) también para a < 0. */
static long long euclid_mod(long long a, long long m)
{
    long long r = a % m; /* / y % en C truncan hacia cero */
    return r < 0 ? r + m : r;
}

/* División piso (⊔), semántica de la referencia Python //. */
static long long floor_div(long long a, long long b)
{
    long long q = a / b;
    if ((a % b != 0) && ((a < 0) != (b < 0))) q -= 1;
    return q;
}

bool gus_is_gran_tempalum(long long year)
{
    /* Forma cerrada simétrica (spec §3): con q,r enteros tales que
     * year = q*U + r (piso, 0 <= r < U), el acumulador del año es
     * r_han = (r * S) mod U y el año es Gran Tempalum <=> r_han + S >= U.
     * Valores intermedios <= U * S < 2^63 (sin desbordamiento) porque
     * r < U queda acotado antes de multiplicar. */
    long long r = euclid_mod(year, GUS_SOLAR_THRESHOLD_UD);
    long long rc = (r * GUS_SOLAR_DELTA_UD) % GUS_SOLAR_THRESHOLD_UD;
    return (rc + GUS_SOLAR_DELTA_UD) >= GUS_SOLAR_THRESHOLD_UD;
}

long long gus_year_length(long long year)
{
    return gus_is_gran_tempalum(year) ? GUS_YEAR_GRAN_DAYS : GUS_YEAR_COMMON_DAYS;
}

long long gus_tempalum_days(long long year)
{
    return gus_year_length(year) == GUS_YEAR_GRAN_DAYS ? 11 : 4;
}

long long gus_year_start_day_index(long long year)
{
    /* O(1) cerrado (spec §3): year = q*U + r por división piso
     * (0 <= r < U, euclidiano también en AY):
     *   gt_count = q*S + floor(r*S / U)
     *   inicio   = year*364 + 7*gt_count
     * ysi(0) = 0; ysi(-1) = -371 (0001AY es Gran Tempalum). */
    long long q = floor_div(year, GUS_SOLAR_THRESHOLD_UD);
    long long r = year - q * GUS_SOLAR_THRESHOLD_UD;
    long long gt_count = q * GUS_SOLAR_DELTA_UD
                       + (r * GUS_SOLAR_DELTA_UD) / GUS_SOLAR_THRESHOLD_UD;
    return year * GUS_YEAR_COMMON_DAYS + 7 * gt_count;
}

/* División piso (⊔), semántica de la referencia Python //:
 * en C, / y % truncan hacia cero en negativos; aquí se corrige. */

long long gus_jdn(long long year, int month, int day)
{
    long long a = (14 - month) / 12;      /* month 1..12: cociente exacto */
    long long y = year + 4800 - a;
    long long m = month + 12 * a - 3;
    long long jdn_val = day + (153 * m + 2) / 5 + 365 * y
                        + floor_div(y, 4) - floor_div(y, 100) + floor_div(y, 400) - 32045;
    return jdn_val;
}

void gus_jdn_to_gregorian(long long j, long long *year, int *month, int *day)
{
    long long a = j + 68569;
    long long b = floor_div(4 * a, 146097);
    long long c = a - floor_div(146097 * b + 3, 4);
    long long d = floor_div(4000 * (c + 1), 1461001);
    long long e = c - floor_div(1461 * d, 4) + 31;
    long long f = floor_div(80 * e, 2447);
    long long dd = e - floor_div(2447 * f, 80);
    long long g = floor_div(f, 11);
    long long mm = f + 2 - 12 * g;
    long long yy = 100 * (b - 49) + d + g;
    *year = yy; *month = (int)mm; *day = (int)dd;
}

long long gus_day_index_from_gregorian(long long year, int month, int day)
{
    return gus_jdn(year, month, day) - GUS_ORIGIN_JDN;
}

void gus_gregorian_from_day_index(long long day_index, long long *year, int *month, int *day)
{
    gus_jdn_to_gregorian(GUS_ORIGIN_JDN + day_index, year, month, day);
}

static int weekday_index_of(long long day_index)
{
    int w = (int)(day_index % 7);
    if (w < 0) w += 7;
    return w;
}

/* Estimación del año para un day_index: primeros floor(day / longitud
 * media exacta de año), con longitud media = 364 + 7*S/U días, es decir
 * floor(day * U / (364*U + 7*S)). En 128 bits evita desbordamiento para
 * años astronómicos; el fallback usa división directa y cuenta con la
 * corrección iterativa de gus_to_gerarion. */
/* Estimación del año para un day_index: floor(day / longitud media exacta
 * de año), con longitud media = 364 + 7*S/U días, es decir
 * floor(day * U / (364*U + 7*S)). En 128 bits evita desbordamiento para
 * años astronómicos; el fallback usa división directa y cuenta con la
 * corrección iterativa de gus_to_gerarion. */
static long long estimate_year(long long day_index)
{
#if defined(__SIZEOF_INT128__)
    __int128 num = (__int128)day_index * GUS_SOLAR_THRESHOLD_UD;
    __int128 den = (__int128)GUS_YEAR_COMMON_DAYS * GUS_SOLAR_THRESHOLD_UD
                 + 7 * ( __int128)GUS_SOLAR_DELTA_UD;
    __int128 q = num / den;
    if ((num % den != 0) && ((num < 0) != (den < 0))) q -= 1;
    return (long long)q;
#else
    return floor_div(day_index, GUS_YEAR_COMMON_DAYS + 1);
#endif
}

GusError gus_to_gerarion(long long day_index, GusDate *out)
{
    /* Inversa simétrica (spec §3): estimación con la longitud media exacta
     * de año y corrección monotónica con year_start_day_index O(1); usa la
     * duración real de cada año (364 o 371) en ambas eras. */
    long long year = estimate_year(day_index);
    while (gus_year_start_day_index(year) > day_index) year -= 1;
    while (gus_year_start_day_index(year + 1) <= day_index) year += 1;
    long long rest = day_index - gus_year_start_day_index(year);
    if (rest < 0 || rest >= gus_year_length(year)) return GUS_EINVAL;

    int month, day;
    if (rest < GUS_MONTH_BLOCK_DAYS) {
        month = (int)(rest / 30) + 1;
        day = (int)(rest % 30) + 1;
    } else {
        month = 0;
        day = (int)(rest - GUS_MONTH_BLOCK_DAYS + 1);
    }
    out->year = year;
    out->month = month;
    out->day = day;
    out->day_index = day_index;
    out->weekday_index = weekday_index_of(day_index);
    static const char letters[7] = { 'S', 'L', 'M', 'A', 'T', 'V', 'B' };
    out->abbr = letters[out->weekday_index];
    return GUS_OK;
}

GusError gus_from_gerarion(long long year, int month, int day, GusDate *out)
{
    long long max_day;
    if (month == 0) {
        max_day = gus_tempalum_days(year);
        if (day < 1 || day > max_day) return GUS_ETEMPALUM;
    } else if (month >= 1 && month <= 12) {
        if (day < 1 || day > 30) return GUS_EINVAL;
        max_day = 0;
    } else {
        return GUS_EINVAL;
    }
    long long offset = (month == 0 ? GUS_MONTH_BLOCK_DAYS : (long long)(month - 1) * 30)
                       + (long long)(day - 1);
    return gus_to_gerarion(gus_year_start_day_index(year) + offset, out);
}

static const char *TEMPALUM_NORMAL[4] = { "Unictis", "Kindom", "Iki", "Ikiyeh" };
static const char *TEMPALUM_GRAN_EXTRA[7] = {
    "Nuvivid I", "Nuvivid II", "Nuvivid III", "Nuvivid IV",
    "Nuvivid V", "Nuvivid VI", "Nuvivid VII"
};

const char *gus_tempalum_name(const GusDate *d)
{
    if (d->month != 0) return NULL;
    if (d->day <= 4) return TEMPALUM_NORMAL[d->day - 1];
    if (gus_year_length(d->year) == GUS_YEAR_GRAN_DAYS) {
        return TEMPALUM_GRAN_EXTRA[d->day - 5];
    }
    return NULL;
}

/* ---------------- formato canónico ---------------- */

static void canonical_date(const GusDate *d, char *buf, size_t buflen)
{
    long long yy = d->year >= 0 ? d->year : -d->year;
    const char *era = d->year >= 0 ? "DY" : "AY";
    snprintf(buf, buflen, "%04lld%s-%02d-%02d-%c", yy, era, d->month, d->day, d->abbr);
}

GusError gus_canonical(const GusParsed *p, char *buf, size_t buflen)
{
    if (!p->has_time) {
        canonical_date(&p->date, buf, buflen);
        return GUS_OK;
    }
    char base[40];
    canonical_date(&p->date, base, sizeof(base));
    char offbuf[16];
    int os2 = p->offset_seconds;
    if (os2 == 0) {
        snprintf(offbuf, sizeof(offbuf), "TCJ+0");
    } else {
        const char signch = os2 < 0 ? '-' : '+';
        long long a = os2 < 0 ? -(long long)os2 : (long long)os2;
        long long h = a / 3600, m = (a % 3600) / 60;
        if (m) {
            /* canónico = SIEMPRE extendido (forma compacta solo en entrada) */
            snprintf(offbuf, sizeof(offbuf), "TCJ%c%lld:%02lld", signch, h, m);
        } else {
            snprintf(offbuf, sizeof(offbuf), "TCJ%c%lld", signch, h);
        }
    }
    int n = snprintf(buf, buflen, "%s-%02d:%02d:%02d-%s-%s",
                     base, p->hour, p->minute, p->second, p->cycle, offbuf);
    return (n < 0 || (size_t)n >= buflen) ? GUS_EINVAL : GUS_OK;
}

/* Normalización REGLAS 1-6: recortar extremos, mayúsculas, separadores. */
static void normalize(const char *raw, char *out, size_t outlen)
{
    size_t start = 0, len = strlen(raw);
    while (start < len && (raw[start] == ' ' || raw[start] == '\t' ||
                           raw[start] == '\r' || raw[start] == '\n')) start++;
    size_t end = len;
    while (end > start && (raw[end - 1] == ' ' || raw[end - 1] == '\t' ||
                           raw[end - 1] == '\r' || raw[end - 1] == '\n')) end--;
    size_t j = 0;
    for (size_t i = start; i < end && j + 1 < outlen; i++) {
        char ch = (char)toupper((unsigned char)raw[i]);
        if (ch == ' ' || ch == '.' || ch == '\t') ch = '-';
        out[j++] = ch;
    }
    out[j] = '\0';
}

static bool is_digits(const char *s, size_t min, size_t max, size_t *count)
{
    size_t n = 0;
    while (s[n] && isdigit((unsigned char)s[n])) n++;
    if (n < min || n > max) return false;
    *count = n;
    return true;
}

static bool parse_int(const char *s, size_t n, long long *out)
{
    char tmp[8];
    if (n >= sizeof(tmp)) return false;
    memcpy(tmp, s, n);
    tmp[n] = '\0';
    *out = strtoll(tmp, NULL, 10);
    return true;
}

/* Estructura del formato canónico (normalizado):
 *   YAD}[DY|AY]-(M|MM)-(D|DD)-X [ -HH:MM:SS-SC|LC-TCJ±O ]
 * Analiza de forma posicional; devuelve GUS_EINVAL ante cualquier desvío. */
GusError gus_parse(const char *raw, bool strict, GusParsed *out)
{
    char s[128];
    normalize(raw, s, sizeof(s));
    memset(out, 0, sizeof(*out));

    const char *cur = s;
    size_t n;
    long long yy;
    if (!is_digits(cur, 1, 6, &n)) return GUS_EINVAL;
    if (!parse_int(cur, n, &yy)) return GUS_EINVAL;
    cur += n;

    bool era_assumed = false;
    long long year = yy;
    if (strncmp(cur, "DY", 2) == 0) cur += 2;
    else if (strncmp(cur, "AY", 2) == 0) { year = -yy; cur += 2; }
    else era_assumed = true;

    if (*cur != '-' && *cur != '.') return GUS_EINVAL;
    cur++;
    if (!is_digits(cur, 1, 2, &n)) return GUS_EINVAL;
    long long month;
    if (!parse_int(cur, n, &month)) return GUS_EINVAL;
    cur += n;

    if (*cur != '-' && *cur != '.') return GUS_EINVAL;
    cur++;
    if (!is_digits(cur, 1, 2, &n)) return GUS_EINVAL;
    long long day;
    if (!parse_int(cur, n, &day)) return GUS_EINVAL;
    cur += n;

    if (*cur != '-' && *cur != '.') return GUS_EINVAL;
    cur++;
    if (!isalpha((unsigned char)*cur)) return GUS_EINVAL;
    char declared = (char)toupper((unsigned char)*cur);
    if (!strchr("SLMATVB", declared)) return GUS_EINVAL;
    cur++;

    if (*cur != '\0' && *cur != '-') return GUS_EINVAL;

    /* Validación del calendario (mismo orden que la referencia Python) */
    GusDate date;
    GusError err = gus_from_gerarion(year, (int)month, (int)day, &date);
    if (err != GUS_OK) return err;

    int weekday_index = weekday_index_of(date.day_index);
    static const char letters[7] = { 'S', 'L', 'M', 'A', 'T', 'V', 'B' };
    bool weekday_corrected = (declared != letters[weekday_index]);
    if (weekday_corrected && strict) return GUS_EWEEK;

    int hour = 0, minute = 0, second = 0;
    bool has_time = false, cycle_corrected = false;
    char cycle[3] = { 0, 0, 0 };
    long long tmp_h = 0, tmp_m = 0, tmp_s = 0, tmp_off = 0;
    bool compact_time = false;

    if (*cur == '-') {
        cur++;
        /* Hora: extendida 'HH:MM:SS' o compacta 'HHMMSS' (Cap 13.1) */
        if (is_digits(cur, 1, 2, &n) && cur[n] == ':') {
            if (!parse_int(cur, n, &tmp_h)) return GUS_EINVAL;
            cur += n;
            if (*cur != ':') return GUS_EINVAL;
            cur++;
            if (!is_digits(cur, 1, 2, &n)) return GUS_EINVAL;
            if (!parse_int(cur, n, &tmp_m)) return GUS_EINVAL;
            cur += n;
            if (*cur != ':') return GUS_EINVAL;
            cur++;
            if (!is_digits(cur, 1, 2, &n)) return GUS_EINVAL;
            if (!parse_int(cur, n, &tmp_s)) return GUS_EINVAL;
            cur += n;
        } else if (is_digits(cur, 6, 6, &n)) {
            tmp_h = (cur[0] - '0') * 10 + (cur[1] - '0');
            tmp_m = (cur[2] - '0') * 10 + (cur[3] - '0');
            tmp_s = (cur[4] - '0') * 10 + (cur[5] - '0');
            cur += 6;
            compact_time = true;
        } else {
            return GUS_EINVAL;
        }
        if (*cur != '-') return GUS_EINVAL;
        cur++;
        if (strncmp(cur, "SC", 2) == 0 || strncmp(cur, "LC", 2) == 0) {
            cycle[0] = cur[0]; cycle[1] = cur[1];
            cur += 2;
        } else {
            return GUS_EINVAL;
        }
        if (strncmp(cur, "-TCJ", 4) != 0) return GUS_EINVAL;
        cur += 4;
        long long off_h = 0, off_m = 0;
        if (*cur == '0' && !(cur[1] >= '0' && cur[1] <= '9')) {
            cur += 1; /* TCJ0 literal: cero */
        } else {
            long long sign = 1;
            if (*cur == '+') cur++;
            else if (*cur == '-') { sign = -1; cur++; }
            else return GUS_EINVAL;
            if (!is_digits(cur, 1, 4, &n)) return GUS_EINVAL;
            if (cur[n] == ':') {
                /* extendido con minutos: H|HH ':' MM (TODO-004, GUS 3.0.0) */
                if (!parse_int(cur, n, &off_h)) return GUS_EINVAL;
                cur += n;
                cur++; /* ':' */
                if (!is_digits(cur, 2, 2, &n)) return GUS_EINVAL;
                if (!parse_int(cur, n, &off_m)) return GUS_EINVAL;
                cur += n;
            } else if (n <= 2) {
                if (!parse_int(cur, n, &off_h)) return GUS_EINVAL;
                cur += n;
            } else if (n == 3) {
                off_h = cur[0] - '0';
                off_m = (cur[1] - '0') * 10 + (cur[2] - '0');
                cur += 3;
            } else {
                off_h = (cur[0] - '0') * 10 + (cur[1] - '0');
                off_m = (cur[2] - '0') * 10 + (cur[3] - '0');
                cur += 4;
            }
            if (off_h > 23 || off_m > 59) return GUS_EINVAL;
            tmp_off = sign * (off_h * 3600 + off_m * 60);
        }

        if (tmp_h > 23 || tmp_m > 59 || tmp_s > 59) return GUS_EINVAL;
        char expected[3];
        GusError cerr = gus_cycle_of((int)tmp_h, expected);
        if (cerr != GUS_OK) return cerr;
        if (strcmp(cycle, expected) != 0) {
            cycle_corrected = true;
            cycle[0] = expected[0]; cycle[1] = expected[1];
        }
        has_time = true;
        hour = (int)tmp_h; minute = (int)tmp_m; second = (int)tmp_s;
    }
    if (*cur != '\0') return GUS_EINVAL;

    out->date = date;
    out->hour = hour; out->minute = minute; out->second = second;
    out->has_time = has_time;
    out->compact = compact_time;
    out->era_assumed = era_assumed;
    out->weekday_corrected = weekday_corrected;
    out->cycle_corrected = cycle_corrected;
    out->offset = (tmp_off != 0 && tmp_off % 3600 == 0) ? (int)(tmp_off / 3600) : 0;
    out->offset_seconds = (int)tmp_off;
    memcpy(out->cycle, cycle, sizeof(cycle));
    return GUS_OK;
}

/* ---------------- instante continuo ---------------- */

GusError gus_cycle_of(int hour, char out[3])
{
    if (hour < 0 || hour > 23) return GUS_EINVAL;
    const char *c = (hour >= 6 && hour < 18) ? "SC" : "LC";
    out[0] = c[0]; out[1] = c[1]; out[2] = '\0';
    return GUS_OK;
}

GusError gus_instant_from_parts(long long day_index, int hour, int minute,
                                int second, int offset_seconds, long long *instant)
{
    if (hour < 0 || hour > 23 || minute < 0 || minute > 59 || second < 0 || second > 59) {
        return GUS_EINVAL;
    }
    if (offset_seconds % 60 != 0 || offset_seconds < -86400 || offset_seconds > 86400) {
        return GUS_EINVAL;
    }
    *instant = day_index * GUS_SECS_PER_DAY + (long long)hour * 3600
               + (long long)minute * 60 + (long long)second - (long long)offset_seconds;
    return GUS_OK;
}

GusError gus_parts_from_instant(long long instant, int offset_seconds,
                                GusDate *date, int *hour, int *minute, int *second)
{
    if (offset_seconds % 60 != 0 || offset_seconds < -86400 || offset_seconds > 86400) {
        return GUS_EINVAL;
    }
    return gus_instant_parts(instant + (long long)offset_seconds, date,
                             hour, minute, second);
}

GusError gus_instant_parts(long long instant, GusDate *date,
                           int *hour, int *minute, int *second)
{
    long long day_index = instant / GUS_SECS_PER_DAY;
    long long rem = instant % GUS_SECS_PER_DAY;
    if (rem < 0) { rem += GUS_SECS_PER_DAY; day_index -= 1; }
    long long h = rem / 3600;
    long long r2 = rem % 3600;
    long long m = r2 / 60;
    long long s = r2 % 60;
    GusError err = gus_to_gerarion(day_index, date);
    if (err != GUS_OK) return err;
    *hour = (int)h; *minute = (int)m; *second = (int)s;
    return GUS_OK;
}

/* ---------------- verificación rápida (Cap 13.8 v1.2) ---------------- */

bool gus_quick_verify(const char *raw)
{
    GusParsed p;
    if (gus_parse(raw, true, &p) != GUS_OK) return false;
    return !p.era_assumed && !p.weekday_corrected && !p.cycle_corrected;
}

/* ---------------- Capa 0 — TAI (IERS) y Capa 1 — TCJ ---------------- */

static const GusTaiEntry GUS_TAI_TABLE[] = {
    {-378691200, 10},  /* 1958-01-01: convención declarada (no medida) */
    {63072000, 10},    /* 1972-01-01: base UTC IERS */
    {78796800, 11},    /* 1972-07-01 */
    {94694400, 12},    /* 1973-01-01 */
    {126230400, 13},   /* 1974-01-01 */
    {157766400, 14},   /* 1975-01-01 */
    {189302400, 15},   /* 1976-01-01 */
    {220924800, 16},   /* 1977-01-01 */
    {252460800, 17},   /* 1978-01-01 */
    {283996800, 18},   /* 1979-01-01 */
    {315532800, 19},   /* 1980-01-01 */
    {362793600, 20},   /* 1981-07-01 */
    {394329600, 21},   /* 1982-07-01 */
    {425865600, 22},   /* 1983-07-01 */
    {489024000, 23},   /* 1985-07-01 */
    {567993600, 24},   /* 1988-01-01 */
    {631152000, 25},   /* 1990-01-01 */
    {662688000, 26},   /* 1991-01-01 */
    {709948800, 27},   /* 1992-07-01 */
    {741484800, 28},   /* 1993-07-01 */
    {773020800, 29},   /* 1994-07-01 */
    {820454400, 30},   /* 1996-01-01 */
    {867715200, 31},   /* 1997-07-01 */
    {915148800, 32},   /* 1999-01-01 */
    {1136073600, 33},  /* 2006-01-01 */
    {1230768000, 34},  /* 2009-01-01 */
    {1341100800, 35},  /* 2012-07-01 */
    {1435708800, 36},  /* 2015-07-01 */
    {1483228800, 37},  /* 2017-01-01: vigente */
};

const GusTaiEntry *gus_tai_table(int *count)
{
    if (count) *count = (int)(sizeof(GUS_TAI_TABLE) / sizeof(GUS_TAI_TABLE[0]));
    return GUS_TAI_TABLE;
}

int gus_tai_minus_utc(long long unix_seconds)
{
    int count = 0;
    const GusTaiEntry *t = gus_tai_table(&count);
    int result = 0; /* pre-1958: 0 s proléptico (spec §9) */
    for (int i = 0; i < count; i++) {
        if (unix_seconds >= t[i].epoch) result = t[i].offset;
        else break;
    }
    return result;
}
