/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/*
 * conformance.c — Runner de conformancia GUS (núcleo) para impl-c.
 *
 * Lee vectors/gus-normative-002.json con un parser JSON mínimo incluido
 * (objetos, arrays, strings, enteros, bools, null — sin floats) y ejecuta
 * las categorías del núcleo, igual que tools/conformance.py y
 * web/conformance.mjs.
 *
 * Uso:  ./gus-conformance [ruta-al-json]   (exit 0 = CONFORME)
 */

#include "gus.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ------------------------------------------------------------------ */
/* Parser JSON mínimo (árbol en memoria, arena sin liberar)            */
/* ------------------------------------------------------------------ */

typedef enum { J_NULL, J_BOOL, J_NUM, J_STR, J_ARR, J_OBJ } JType;

typedef struct JNode {
    JType type;
    int boolean;
    long long num;
    char *str;
    struct JNode **items;   /* J_ARR / J_OBJ valores */
    char **keys;            /* J_OBJ claves */
    int count;
} JNode;

typedef struct {
    const char *src;
    size_t pos;
    char err[128];
} JParser;

static void jfail(JParser *p, const char *msg)
{
    if (p->err[0] == '\0') snprintf(p->err, sizeof(p->err), "%s (en offset %zu)", msg, p->pos);
}

static void skip_ws(JParser *p)
{
    while (p->src[p->pos] == ' ' || p->src[p->pos] == '\t' ||
           p->src[p->pos] == '\n' || p->src[p->pos] == '\r') p->pos++;
}

static JNode *jnew(JType t)
{
    JNode *n = calloc(1, sizeof(JNode));
    n->type = t;
    return n;
}

static JNode *jparse_value(JParser *p);

static char *jparse_string_raw(JParser *p)
{
    if (p->src[p->pos] != '"') { jfail(p, "se esperaba '\"'"); return NULL; }
    p->pos++;
    size_t cap = 64, len = 0;
    char *buf = malloc(cap);
    while (p->src[p->pos] != '"') {
        char ch = p->src[p->pos];
        if (ch == '\0') { jfail(p, "string sin cerrar"); free(buf); return NULL; }
        if (ch == '\\') {
            p->pos++;
            char esc = p->src[p->pos];
            if (esc == 'n') ch = '\n';
            else if (esc == 't') ch = '\t';
            else if (esc == 'r') ch = '\r';
            else if (esc == '\\') ch = '\\';
            else if (esc == '/') ch = '/';
            else if (esc == '"') ch = '"';
            else if (esc == 'u') {
            /* \uXXXX: los vectores del núcleo son ASCII; convertir un byte */
                char hex[5] = { 0 };
                memcpy(hex, p->src + p->pos + 1, 4);
                ch = (char)strtol(hex, NULL, 16);
                p->pos += 4;
            } else { jfail(p, "escape desconocido"); free(buf); return NULL; }
            p->pos++;
        } else {
            p->pos++;
        }
        if (len + 4 >= cap) { cap *= 2; buf = realloc(buf, cap); }
        if ((unsigned char)ch < 0x80) {
            buf[len++] = ch;
        } else {
            /* UTF-8 de dos bytes (\u00d7- style escapesdecode) passthrough simplificado */
            buf[len++] = ch; /* los vectores núcleo son ASCII */
        }
    }
    p->pos++;
    buf[len] = '\0';
    return buf;
}

static JNode *jparse_object(JParser *p)
{
    p->pos++; /* '{' */
    JNode *n = jnew(J_OBJ);
    int cap = 16;
    n->keys = malloc(sizeof(char *) * cap);
    n->items = malloc(sizeof(JNode *) * cap);
    skip_ws(p);
    if (p->src[p->pos] == '}') { p->pos++; return n; }
    for (;;) {
        skip_ws(p);
        char *key = jparse_string_raw(p);
        if (!key) return NULL;
        skip_ws(p);
        if (p->src[p->pos] != ':') { jfail(p, "se esperaba ':'"); return NULL; }
        p->pos++;
        JNode *val = jparse_value(p);
        if (!val) return NULL;
        if (n->count == cap) {
            cap *= 2;
            n->keys = realloc(n->keys, sizeof(char *) * cap);
            n->items = realloc(n->items, sizeof(JNode *) * cap);
        }
        n->keys[n->count] = key;
        n->items[n->count] = val;
        n->count++;
        skip_ws(p);
        if (p->src[p->pos] == ',') { p->pos++; continue; }
        if (p->src[p->pos] == '}') { p->pos++; return n; }
        jfail(p, "se esperaba ',' o '}'");
        return NULL;
    }
}

static JNode *jparse_array(JParser *p)
{
    p->pos++; /* '[' */
    JNode *n = jnew(J_ARR);
    int cap = 16;
    n->items = malloc(sizeof(JNode *) * cap);
    skip_ws(p);
    if (p->src[p->pos] == ']') { p->pos++; return n; }
    for (;;) {
        JNode *val = jparse_value(p);
        if (!val) return NULL;
        if (n->count == cap) {
            cap *= 2;
            n->items = realloc(n->items, sizeof(JNode *) * cap);
        }
        n->items[n->count++] = val;
        skip_ws(p);
        if (p->src[p->pos] == ',') { p->pos++; continue; }
        if (p->src[p->pos] == ']') { p->pos++; return n; }
        jfail(p, "se esperaba ',' o ']'");
        return NULL;
    }
}

static JNode *jparse_value(JParser *p)
{
    skip_ws(p);
    char ch = p->src[p->pos];
    if (ch == '{') return jparse_object(p);
    if (ch == '[') return jparse_array(p);
    if (ch == '"') {
        JNode *n = jnew(J_STR);
        n->str = jparse_string_raw(p);
        return n && n->str ? n : NULL;
    }
    if (ch == '-' || (ch >= '0' && ch <= '9')) {
        char *end;
        JNode *n = jnew(J_NUM);
        n->num = strtoll(p->src + p->pos, &end, 10);
        if (end == p->src + p->pos) { jfail(p, "número inválido"); free(n); return NULL; }
        p->pos = end - p->src;
        return n;
    }
    if (strncmp(p->src + p->pos, "true", 4) == 0) {
        p->pos += 4; JNode *n = jnew(J_BOOL); n->boolean = 1; return n;
    }
    if (strncmp(p->src + p->pos, "false", 5) == 0) {
        p->pos += 5; JNode *n = jnew(J_BOOL); n->boolean = 0; return n;
    }
    if (strncmp(p->src + p->pos, "null", 4) == 0) {
        p->pos += 4; return jnew(J_NULL);
    }
    jfail(p, "valor JSON inesperado");
    return NULL;
}

static JNode *jload(const char *path)
{
    FILE *fh = fopen(path, "rb");
    if (!fh) { fprintf(stderr, "no se pudo abrir %s\n", path); return NULL; }
    fseek(fh, 0, SEEK_END);
    long size = ftell(fh);
    fseek(fh, 0, SEEK_SET);
    char *buf = malloc((size_t)size + 1);
    size_t got = fread(buf, 1, (size_t)size, fh);
    buf[got] = '\0';
    fclose(fh);
    JParser p = { buf, 0, "" };
    JNode *root = jparse_value(&p);
    if (!root) {
        fprintf(stderr, "JSON inválido: %s\n", p.err);
        free(buf);
        return NULL;
    }
    return root;
}

static JNode *jo(JNode *obj, const char *key)
{
    for (int i = 0; i < obj->count; i++)
        if (strcmp(obj->keys[i], key) == 0) return obj->items[i];
    return NULL;
}

static long long jn(JNode *obj, const char *key)
{
    JNode *v = jo(obj, key);
    return v ? v->num : 0;
}

static const char *js(JNode *obj, const char *key)
{
    JNode *v = jo(obj, key);
    return (v && v->type == J_STR) ? v->str : NULL;
}

/* ------------------------------------------------------------------ */
/* Verificación de categorías del núcleo                               */
/* ------------------------------------------------------------------ */

static int g_failures;
static int g_checks;

static void fail(const char *cat, const char *msg)
{
    g_failures++;
    printf("  FALLA %s: %s\n", cat, msg);
}

static void fail3(const char *cat, const char *what, long long got, long long want)
{
    char msg[160];
    snprintf(msg, sizeof(msg), "%s: obtenido %lld, esperado %lld", what, got, want);
    fail(cat, msg);
}

static const char *FLAGS_SORTED[3] = { "cycle_corrected", "era_assumed_DY", "weekday_corrected" };

static void check_flags(const char *cat, const GusParsed *p, JNode *want)
{
    char got[64] = "";
    /* recompose sorted */
    const char *names[4] = { 0, 0, 0, 0 };
    int idx = 0;
    if (p->cycle_corrected) names[idx++] = FLAGS_SORTED[0];
    if (p->era_assumed) names[idx++] = FLAGS_SORTED[1];
    if (p->weekday_corrected) names[idx++] = FLAGS_SORTED[2];
    for (int i = 0; i < idx; i++) {
        if (i) strncat(got, "|", sizeof(got) - strlen(got) - 1);
        strncat(got, names[i], sizeof(got) - strlen(got) - 1);
    }
    char wanted[64] = "";
    for (int i = 0; i < want->count; i++) {
        if (i) strncat(wanted, "|", sizeof(wanted) - strlen(wanted) - 1);
        strncat(wanted, want->items[i]->str, sizeof(wanted) - strlen(wanted) - 1);
    }
    if (strcmp(got, wanted) != 0) {
        char msg[160];
        snprintf(msg, sizeof(msg), "flags [%s] != [%s]", got, wanted);
        fail(cat, msg);
        g_checks++;
    }
}

static void check_constants(JNode *v)
{
    const char *cat = "constants";
    g_checks++;
    JNode *c = jo(v, "constants");
    if (GUS_ORIGIN_JDN != jn(c, "ORIGIN_JDN")) fail3(cat, "ORIGIN_JDN", GUS_ORIGIN_JDN, jn(c, "ORIGIN_JDN"));
    if (GUS_SOLAR_DELTA_UD != jn(c, "SOLAR_DELTA_UD")) fail3(cat, "SOLAR_DELTA_UD", GUS_SOLAR_DELTA_UD, jn(c, "SOLAR_DELTA_UD"));
    if (GUS_SOLAR_THRESHOLD_UD != jn(c, "SOLAR_THRESHOLD_UD")) fail3(cat, "SOLAR_THRESHOLD_UD", GUS_SOLAR_THRESHOLD_UD, jn(c, "SOLAR_THRESHOLD_UD"));
    if (GUS_SECS_PER_DAY != jn(c, "SECS_PER_DAY")) fail3(cat, "SECS_PER_DAY", GUS_SECS_PER_DAY, jn(c, "SECS_PER_DAY"));
    if (GUS_MONTH_BLOCK_DAYS != jn(c, "MONTH_BLOCK_DAYS")) fail3(cat, "MONTH_BLOCK_DAYS", GUS_MONTH_BLOCK_DAYS, jn(c, "MONTH_BLOCK_DAYS"));
}

static void check_gran_tempalum(JNode *v)
{
    const char *cat = "gran_tempalum";
    g_checks++;
    JNode *g = jo(v, "gran_tempalum");
    JNode *pattern = jo(g, "pattern_years_0_45");
    int idx = 0;
    for (long long y = 0; y < 46; y++) {
        if (gus_is_gran_tempalum(y)) {
            if (idx >= pattern->count || pattern->items[idx]->num != y) {
                fail3(cat, "patrón GT", y, idx < pattern->count ? pattern->items[idx]->num : -999999);
                return;
            }
            idx++;
        }
    }
    if (idx != pattern->count) {
        fail3(cat, "cantidad de años GT 0-45", idx, pattern->count);
    }
    /* Patrón simétrico en era AY (spec 2.1): rango [-46, -1]. */
    JNode *pattern_neg = jo(g, "pattern_years_m45_m1");
    idx = 0;
    for (long long y = -46; y < 0; y++) {
        if (gus_is_gran_tempalum(y)) {
            if (idx >= pattern_neg->count || pattern_neg->items[idx]->num != y) {
                fail3(cat, "patrón GT AY", y, idx < pattern_neg->count ? pattern_neg->items[idx]->num : -999999);
                return;
            }
            idx++;
        }
    }
    if (idx != pattern_neg->count) {
        fail3(cat, "cantidad de años GT AY", idx, pattern_neg->count);
    }
    JNode *sample = jo(g, "years_sample");
    for (int i = 0; i < sample->count; i++) {
        long long y = strtoll(sample->keys[i], NULL, 10);
        if (gus_is_gran_tempalum(y) != (sample->items[i]->boolean != 0)) {
            char msg[80];
            snprintf(msg, sizeof(msg), "año %lld: GT != %d", y, sample->items[i]->boolean);
            fail(cat, msg);
        }
    }
}

static void check_calendar(JNode *v)
{
    const char *cat = "calendar";
    g_checks++;
    JNode *rows = jo(v, "calendar");
    static const char *NUVID[7] = {
        "Soludyia", "Loondyia", "Mardyia", "Aisterdyia", "Trustdyia", "Viendyia", "Sabatyeh"
    };
    for (int i = 0; i < rows->count; i++) {
        JNode *row = rows->items[i];
        long long gy = jn(row, "greg_year");
        int gm = (int)jn(row, "greg_month");
        int gd = (int)jn(row, "greg_day");
        long long di = gus_day_index_from_gregorian(gy, gm, gd);
        if (di != jn(row, "day_index")) {
            char msg[64];
            snprintf(msg, sizeof(msg), "%s", js(row, "greg"));
            fail3(cat, msg, di, jn(row, "day_index"));
        }
        GusDate d;
        GusError err = gus_to_gerarion(di, &d);
        if (err != GUS_OK) { fail(cat, "to_gerarion falló"); continue; }
        long long want_year = strcmp(js(row, "era"), "DY") == 0 ? jn(row, "year") : -jn(row, "year");
        if (d.year != want_year) fail3(cat, "year", d.year, want_year);
        if (d.month != jn(row, "month")) fail3(cat, "month", d.month, jn(row, "month"));
        if (d.day != jn(row, "day")) fail3(cat, "day", d.day, jn(row, "day"));
        if (d.weekday_index != jn(row, "weekday_index")) fail3(cat, "weekday_index", d.weekday_index, jn(row, "weekday_index"));
        if (d.abbr != js(row, "abbr")[0]) { fail(cat, "abbr"); }
        if (strcmp(NUVID[d.weekday_index], js(row, "weekday")) != 0) fail(cat, "weekday");
    }
}

static void check_year_starts(JNode *v)
{
    const char *cat = "year_starts";
    g_checks++;
    JNode *rows = jo(v, "year_starts");
    for (int i = 0; i < rows->count; i++) {
        JNode *row = rows->items[i];
        long long y = jn(row, "year"); /* signo ya en el vector (simétrico, GUS 2.1) */
        long long di = gus_year_start_day_index(y);
        if (di != jn(row, "day_index")) fail3(cat, js(row, "greg"), di, jn(row, "day_index"));
        GusDate d;
        if (gus_to_gerarion(di, &d) != GUS_OK || d.abbr != 'S') fail(cat, "no empieza en Soludyia");
        if (gus_is_gran_tempalum(y) != (jo(row, "gran_tempalum")->boolean != 0)) {
            fail(cat, "gran_tempalum divergente");
        }
        if (gus_tempalum_days(y) != jn(row, "tempalum_days")) fail(cat, "tempalum_days");
    }
}

static void check_roundtrip(JNode *v)
{
    const char *cat = "gregorian_roundtrip";
    g_checks++;
    JNode *rows = jo(v, "gregorian_roundtrip");
    for (int i = 0; i < rows->count; i++) {
        JNode *row = rows->items[i];
        long long di = jn(row, "day_index");
        long long gy;
        int gm, gd;
        gus_gregorian_from_day_index(di, &gy, &gm, &gd);
        if (gy != jn(row, "greg_year") || gm != jn(row, "greg_month") || gd != jn(row, "greg_day")) {
            char msg[80];
            snprintf(msg, sizeof(msg), "day %lld: greg %lld-%d-%d != %s", di, gy, gm, gd, js(row, "greg"));
            fail(cat, msg);
        }
        if (gus_day_index_from_gregorian(gy, gm, gd) != di) fail(cat, "roundtrip inverso");
    }
}

static void check_format(JNode *v)
{
    const char *cat = "format";
    g_checks++;
    JNode *f = jo(v, "format");
    JNode *cases = jo(f, "canonical");
    for (int i = 0; i < cases->count; i++) {
        JNode *c = cases->items[i];
        GusParsed p;
        GusError err = gus_parse(js(c, "input"), false, &p);
        if (err != GUS_OK) { fail(cat, "parse inesperadamente inválido"); continue; }
        char canon[64];
        if (gus_canonical(&p, canon, sizeof(canon)) != GUS_OK) { fail(cat, "canon overflow"); continue; }
        if (strcmp(canon, js(c, "canonical")) != 0) {
            char msg[160];
            snprintf(msg, sizeof(msg), "%s: canon %s != %s", js(c, "input"), canon, js(c, "canonical"));
            fail(cat, msg);
        }
        check_flags(cat, &p, jo(c, "flags"));
        JNode *fields = jo(c, "fields");
        long long want_year = strcmp(js(fields, "era"), "DY") == 0 ? jn(fields, "year") : -jn(fields, "year");
        if (p.date.year != want_year) fail3(cat, "fields.year", p.date.year, want_year);
        if (p.date.month != jn(fields, "month")) fail3(cat, "fields.month", p.date.month, jn(fields, "month"));
        if (p.date.day != jn(fields, "day")) fail3(cat, "fields.day", p.date.day, jn(fields, "day"));
        if (p.hour != jn(fields, "hour")) fail3(cat, "fields.hour", p.hour, jn(fields, "hour"));
        if (p.minute != jn(fields, "minute")) fail3(cat, "fields.minute", p.minute, jn(fields, "minute"));
        if (p.second != jn(fields, "second")) fail3(cat, "fields.second", p.second, jn(fields, "second"));
        if (p.offset != jn(fields, "offset")) fail3(cat, "fields.offset", p.offset, jn(fields, "offset"));
    }
    JNode *errs = jo(f, "errors");
    for (int i = 0; i < errs->count; i++) {
        JNode *c = errs->items[i];
        GusParsed p;
        GusError err = gus_parse(js(c, "input"), false, &p);
        GusError want = strcmp(js(c, "error"), "GERO_ETEMPALUM") == 0 ? GUS_ETEMPALUM : GUS_EINVAL;
        if (err != want) {
            char msg[80];
            snprintf(msg, sizeof(msg), "%s: código %d != %d", js(c, "input"), err, want);
            fail(cat, msg);
        }
    }
    JNode *strict = jo(f, "strict_weekday");
    for (int i = 0; i < strict->count; i++) {
        JNode *c = strict->items[i];
        GusParsed p;
        GusError err = gus_parse(js(c, "input"), true, &p);
        if (err != GUS_EWEEK) {
            char msg[80];
            snprintf(msg, sizeof(msg), "%s: strict código %d != GERO_EWEEK", js(c, "input"), err);
            fail(cat, msg);
        }
    }
}

static void check_instant(JNode *v)
{
    const char *cat = "instant";
    g_checks++;
    JNode *rows = jo(v, "instant");
    for (int i = 0; i < rows->count; i++) {
        JNode *row = rows->items[i];
        GusParsed p;
        GusError err = gus_parse(js(row, "ts"), false, &p);
        if (err != GUS_OK) { fail(cat, "parse falló"); continue; }
        long long instant;
        err = gus_instant_from_parts(p.date.day_index, p.hour, p.minute, p.second, &instant);
        if (err != GUS_OK) { fail(cat, "instant_from_parts falló"); continue; }
        char got[32], want[32];
        snprintf(got, sizeof(got), "%lld", instant);
        snprintf(want, sizeof(want), "%lld", jn(row, "instant"));
        if (strcmp(got, want) != 0) {
            char msg[120];
            snprintf(msg, sizeof(msg), "%s: instant %s != %s", js(row, "ts"), got, want);
            fail(cat, msg);
        }
        if (p.date.day_index != jn(row, "day")) fail3(cat, "day", p.date.day_index, jn(row, "day"));
    }
}

/* F1: casos negativos compartidos (gus-3339-negative-001.json).
 * impl-c no implementa el parser de strings GUS-3339; su superficie
 * equivalente es gus_instant_from_parts, que debe RECHAZAR todo campo
 * horario fuera de rango (nunca normalizar). */
static void check_negatives(JNode *v)
{
    const char *cat = "gus3339_negativos";
    JNode *rows = jo(v, "instant_parts");
    for (int i = 0; i < rows->count; i++) {
        JNode *row = rows->items[i];
        long long instant;
        GusError err = gus_instant_from_parts(jn(row, "day_index"),
            (int)jn(row, "hour"), (int)jn(row, "minute"),
            (int)jn(row, "second"), &instant);
        if (err == GUS_OK) {
            fail(cat, js(row, "why"));  /* aceptó una entrada inválida */
        }
    }
}

/* F2: regresión AY (gus-regression-001.json) — el GT es simétrico en DY/AY. */
static void check_ay_regression(JNode *v)
{
    const char *cat = "ay_regression";
    JNode *rows = jo(v, "calendar_ay");
    for (int i = 0; i < rows->count; i++) {
        JNode *row = rows->items[i];
        GusParsed p;
        GusError err = gus_parse(js(row, "canonical"), false, &p);
        if (err != GUS_OK) { fail(cat, js(row, "canonical")); continue; }
        if (p.date.day_index != jn(row, "day_index")) {
            fail3(cat, js(row, "canonical"), p.date.day_index, jn(row, "day_index"));
            continue;
        }
        GusDate d;
        if (gus_to_gerarion(jn(row, "day_index"), &d) != GUS_OK) {
            fail(cat, "to_gerarion falló");
            continue;
        }
        char canon[48]; /* gus_canonical exige al menos 48 bytes */
        if (gus_canonical(&p, canon, sizeof(canon)) != GUS_OK) {
            fail(cat, "canon overflow");
            continue;
        }
        if (strcmp(canon, js(row, "canonical")) != 0) {
            fail3(cat, "canon", d.day_index, jn(row, "day_index"));
        }
        const bool gt_expected = jo(row, "gran_tempalum")->boolean != 0;
        if (gus_is_gran_tempalum(d.year) != gt_expected) {
            fail(cat, "gran_tempalum divergente");
        }
    }
}

/* Cap 13.8 v1.2: verificación rápida O(1) (gus-quickverify-001.json).
 * Consumido también por tests/test_quick_verify.py (Python) y
 * web/tests.mjs (JS quickVerify); mismos casos, mismas decisiones:
 * una entrada dudosa se rechaza (false), nunca se normaliza a válido. */
static void check_quick_verify(JNode *v)
{
    const char *cat = "quick_verify";
    JNode *vals = jo(v, "valid");
    for (int i = 0; i < vals->count; i++) {
        JNode *row = vals->items[i];
        if (row->type != J_OBJ) { fail(cat, "vector valid[i] no es objeto"); continue; }
        if (!gus_quick_verify(js(row, "ts"))) fail(cat, js(row, "ts"));
    }
    JNode *invs = jo(v, "invalid");
    for (int i = 0; i < invs->count; i++) {
        JNode *row = invs->items[i];
        if (row->type != J_OBJ) { fail(cat, "vector invalid[i] no es objeto"); continue; }
        if (gus_quick_verify(js(row, "ts"))) fail(cat, js(row, "ts"));
    }
}

int main(int argc, char **argv)
{
    const char *path = argc > 1 ? argv[1] : "../vectors/gus-normative-002.json";
    const char *negPath = argc > 2 ? argv[2] : NULL;
    const char *ayPath = argc > 3 ? argv[3] : NULL;
    const char *quickPath = argc > 4 ? argv[4] : NULL;
    JNode *v = jload(path);
    if (!v) return 2;
    printf("gus-normative conformance (C): %s\n", path);
    check_constants(v);
    check_gran_tempalum(v);
    check_calendar(v);
    check_year_starts(v);
    check_roundtrip(v);
    check_format(v);
    check_instant(v);
    int cats = 7;
    if (negPath) {
        JNode *neg = jload(negPath);
        if (!neg) return 2;
        printf("gus-3339-negative conformance (C): %s\n", negPath);
        g_checks++;
        check_negatives(neg);
        cats = 8;
    }
    if (ayPath) {
        JNode *ay = jload(ayPath);
        if (!ay) return 2;
        printf("gus-regression AY conformance (C): %s\n", ayPath);
        g_checks++;
        check_ay_regression(ay);
        cats = 9;
    }
    if (quickPath) {
        JNode *qv = jload(quickPath);
        if (!qv) return 2;
        printf("gus-quickverify conformance (C): %s\n", quickPath);
        g_checks++;
        check_quick_verify(qv);
        cats = 10;
    }
    if (g_failures == 0) {
        printf("CONFORME (núcleo GUS en C): %d categorías, 0 fallos\n", cats);
        return 0;
    }
    printf("NO CONFORME: %d fallos\n", g_failures);
    return 1;
}
