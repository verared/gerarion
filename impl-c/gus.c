/*
 * gus.c — Núcleo GUS 2.x en C (segunda implementación independiente).
 *
 * Aritmética entera exacta; sin punto flotante. Los días fuera del rango
 * Dynastic Y anteriores usan años comunes de 364 (era AY), igual que la
 * implementación de referencia (src/gerarion/calendar.py).
 */

#include "gus.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---------------- calendario ---------------- */

bool gus_is_gran_tempalum(long long year)
{
    if (year < 0) return false;
    long long r = 0;
    for (long long n = 0; n <= year; n++) {
        bool gt = (r + GUS_SOLAR_DELTA_UD) >= GUS_SOLAR_THRESHOLD_UD;
        r += GUS_SOLAR_DELTA_UD;
        if (r >= GUS_SOLAR_THRESHOLD_UD) r -= GUS_SOLAR_THRESHOLD_UD;
        if (n == year) return gt;
    }
    return false;
}

long long gus_year_length(long long year)
{
    if (year < 0) return GUS_YEAR_COMMON_DAYS;
    return gus_is_gran_tempalum(year) ? GUS_YEAR_GRAN_DAYS : GUS_YEAR_COMMON_DAYS;
}

long long gus_tempalum_days(long long year)
{
    return gus_year_length(year) == GUS_YEAR_GRAN_DAYS ? 11 : 4;
}

long long gus_year_start_day_index(long long year)
{
    if (year >= 0) {
        long long total = 0;
        for (long long y = 0; y < year; y++) total += gus_year_length(y);
        return total;
    }
    return year * GUS_YEAR_COMMON_DAYS;
}

/* División con redondeo al suelo (semántica de la referencia Python //). */
static long long fdiv(long long a, long long b)
{
    long long q = a / b;
    if ((a % b != 0) && ((a < 0) != (b < 0))) q -= 1;
    return q;
}

long long gus_jdn(long long year, int month, int day)
{
    long long a = (14 - month) / 12;      /* month 1..12: cociente exacto */
    long long y = year + 4800 - a;
    long long m = month + 12 * a - 3;
    long long jdn_val = day + (153 * m + 2) / 5 + 365 * y
                        + fdiv(y, 4) - fdiv(y, 100) + fdiv(y, 400) - 32045;
    return jdn_val;
}

void gus_jdn_to_gregorian(long long j, long long *year, int *month, int *day)
{
    long long a = j + 68569;
    long long b = fdiv(4 * a, 146097);
    long long c = a - fdiv(146097 * b + 3, 4);
    long long d = fdiv(4000 * (c + 1), 1461001);
    long long e = c - fdiv(1461 * d, 4) + 31;
    long long f = fdiv(80 * e, 2447);
    long long dd = e - fdiv(2447 * f, 80);
    long long g = fdiv(f, 11);
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

GusError gus_to_gerarion(long long day_index, GusDate *out)
{
    long long year, rest;
    if (day_index >= 0) {
        year = 0;
        rest = day_index;
        for (;;) {
            long long len = gus_year_length(year);
            if (rest < len) break;
            rest -= len;
            year += 1;
        }
    } else {
        long long years_back = (-day_index + GUS_YEAR_COMMON_DAYS - 1) / GUS_YEAR_COMMON_DAYS;
        year = -years_back;
        rest = day_index - year * GUS_YEAR_COMMON_DAYS;
        if (rest < 0 || rest >= GUS_YEAR_COMMON_DAYS) return GUS_EINVAL;
    }
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
    int n = snprintf(buf, buflen, "%s-%02d:%02d:%02d-%s-TCJ%+d",
                     base, p->hour, p->minute, p->second, p->cycle, p->offset);
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
    if (!is_digits(cur, 1, 4, &n)) return GUS_EINVAL;
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

    int hour = 0, minute = 0, second = 0, offset = 0;
    bool has_time = false, cycle_corrected = false;
    char cycle[3] = { 0, 0, 0 };
    long long tmp_h = 0, tmp_m = 0, tmp_s = 0, tmp_off = 0;

    if (*cur == '-') {
        cur++;
        if (!is_digits(cur, 1, 2, &n)) return GUS_EINVAL;
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
        long long sign = 1;
        if (*cur == '+') cur++;
        else if (*cur == '-') { sign = -1; cur++; }
        else return GUS_EINVAL;
        if (!is_digits(cur, 1, 2, &n)) return GUS_EINVAL;
        if (!parse_int(cur, n, &tmp_off)) return GUS_EINVAL;
        cur += n;
        tmp_off *= sign;

        if (tmp_h > 23 || tmp_m > 59 || tmp_s > 59) return GUS_EINVAL;
        char expected[3];
        GusError cerr = gus_cycle_of((int)tmp_h, expected);
        if (cerr != GUS_OK) return cerr;
        if (strcmp(cycle, expected) != 0) {
            cycle_corrected = true;
            cycle[0] = expected[0]; cycle[1] = expected[1];
        }
        has_time = true;
        hour = (int)tmp_h; minute = (int)tmp_m; second = (int)tmp_s; offset = (int)tmp_off;
    }
    if (*cur != '\0') return GUS_EINVAL;

    out->date = date;
    out->hour = hour; out->minute = minute; out->second = second;
    out->has_time = has_time;
    out->era_assumed = era_assumed;
    out->weekday_corrected = weekday_corrected;
    out->cycle_corrected = cycle_corrected;
    out->offset = offset;
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
                                int second, long long *instant)
{
    if (hour < 0 || hour > 23 || minute < 0 || minute > 59 || second < 0 || second > 59) {
        return GUS_EINVAL;
    }
    *instant = day_index * GUS_SECS_PER_DAY + (long long)hour * 3600
               + (long long)minute * 60 + (long long)second;
    return GUS_OK;
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
