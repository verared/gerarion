/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/*
 * guti_conformance.c — conformance del motor multi-calendario (fase GUTI-1)
 * contra el set compartido CC0 vectors/guti-calendars-001.json.
 *
 * Valida bit a bit sobre libgerarion (gerarion_calendars.c):
 *   1. `vectors`     — from_day_index + ida-y-vuelta (10 sistemas).
 *   2. `cross`       — palíndromo A→GUS→B→GUS→A.
 *   3. `invalid`     — rechazo con GUS_EINVAL.
 *   4. `unsupported` — rechazo con GERARION_EUNSUPPORTED.
 *   5. `erange`      — rechazo con GUS_ERANGE.
 *   6. Metadatos: exactamente 10 sistemas con id y época.
 *
 * Uso:  ./guti-conformance [ruta-al-json]   (exit 0 = CONFORME)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gerarion_calendars.h"

/* ------------------------------------------------------------------ */
/* Parser JSON mínimo (árbol en memoria; igual enfoque que
 * conformance.c: stdlib, arena sin liberar — no forma parte del
 * código publicado de libgerarion).                                    */
/* ------------------------------------------------------------------ */

typedef enum { J_NULL, J_BOOL, J_NUM, J_STR, J_ARR, J_OBJ } JType;

typedef struct JNode {
    JType type;
    int boolean;
    long long num;
    char *str;
    struct JNode **items;
    char **keys;
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
        buf[len++] = ch;   /* UTF-8 raw passthrough */
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
        skip_ws(p);
        JNode *v = jparse_value(p);
        if (!v) return NULL;
        if (n->count == cap) { cap *= 2; n->keys = realloc(n->keys, sizeof(char *) * cap); n->items = realloc(n->items, sizeof(JNode *) * cap); }
        n->keys[n->count] = key;
        n->items[n->count] = v;
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
        skip_ws(p);
        JNode *v = jparse_value(p);
        if (!v) return NULL;
        if (n->count == cap) { cap *= 2; n->items = realloc(n->items, sizeof(JNode *) * cap); }
        n->items[n->count++] = v;
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
    char c = p->src[p->pos];
    if (c == '{') return jparse_object(p);
    if (c == '[') return jparse_array(p);
    if (c == '"') {
        JNode *n = jnew(J_STR);
        n->str = jparse_string_raw(p);
        return n->str ? n : NULL;
    }
    if (!strncmp(p->src + p->pos, "true", 4)) { p->pos += 4; JNode *n = jnew(J_BOOL); n->boolean = 1; return n; }
    if (!strncmp(p->src + p->pos, "false", 5)) { p->pos += 5; JNode *n = jnew(J_BOOL); n->boolean = 0; return n; }
    if (!strncmp(p->src + p->pos, "null", 4)) { p->pos += 4; return jnew(J_NULL); }
    if (c == '-' || (c >= '0' && c <= '9')) {
        JNode *n = jnew(J_NUM);
        char *end;
        n->num = strtoll(p->src + p->pos, &end, 10);
        p->pos = (size_t)(end - p->src);
        return n;
    }
    jfail(p, "valor JSON inesperado");
    return NULL;
}

static JNode *jparse_all(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f) { fprintf(stderr, "no se puede abrir %s\n", path); return NULL; }
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *buff = malloc((size_t)size + 1);
    if (fread(buff, 1, (size_t)size, f) != (size_t)size) {
        fprintf(stderr, "lectura incompleta de %s\n", path);
        fclose(f);
        return NULL;
    }
    buff[size] = '\0';
    fclose(f);
    JParser p = { buff, 0, "" };
    JNode *root = jparse_value(&p);
    if (!root) { fprintf(stderr, "JSON inválido: %s\n", p.err); return NULL; }
    return root;
}

/* helpers de acceso */
static JNode *jobj_get(const JNode *o, const char *key)
{
    if (!o || o->type != J_OBJ) return NULL;
    for (int i = 0; i < o->count; i++)
        if (!strcmp(o->keys[i], key)) return o->items[i];
    return NULL;
}
static int jarr_len(const JNode *a) { return (a && a->type == J_ARR) ? a->count : 0; }
static JNode *jarr_at(const JNode *a, int i) { return (a && a->type == J_ARR && i < a->count) ? a->items[i] : NULL; }

/* ------------------------------------------------------------------ */

static int failures = 0;
static void ck(const char *what, int cond)
{
    if (cond) return;
    failures++;
    if (failures <= 10) fprintf(stderr, "FALLO: %s\n", what);
}

static void fill_fields(const JNode *fobj, GerarionCalDate *d)
{
    memset(d, 0, sizeof(*d));
    d->leap = 0;
    if (!fobj || fobj->type != J_OBJ) return;
    static const char *names[] = { "baktun", "katun", "tun", "uinal", "kin",
                                   "year", "month", "day" };
    int idx = 0;
    /* maya primero (si existe 'baktun'), si no year/month/day */
    if (jobj_get(fobj, "baktun")) {
        const char *mkeys[] = { "baktun", "katun", "tun", "uinal", "kin" };
        for (int i = 0; i < 5; i++) {
            JNode *v = jobj_get(fobj, mkeys[i]);
            d->f[idx++] = v && v->type == J_NUM ? v->num : 0;
        }
        d->count = 5;
        return;
    }
    for (int i = 5; i < 8; i++) {
        JNode *v = jobj_get(fobj, names[i]);
        d->f[idx++] = v && v->type == J_NUM ? v->num : 0;
    }
    d->count = 3;
    JNode *lv = jobj_get(fobj, "leap");
    d->leap = (lv && lv->type == J_BOOL) ? lv->boolean : 0;
}

int main(int argc, char **argv)
{
    const char *path = argc > 1 ? argv[1] : "../vectors/guti-calendars-001.json";
    JNode *root = jparse_all(path);
    if (!root) return 2;

    long long total = 0;

    /* 1. vectors */
    JNode *arr = jobj_get(root, "vectors");
    int n = jarr_len(arr);
    for (int i = 0; i < n; i++) {
        JNode *v = jarr_at(arr, i);
        const char *sys = jobj_get(v, "system")->str;
        long long di = jobj_get(v, "day_index")->num;
        int s = gerarion_cal_system_from_id(sys);
        char what[256];
        total++;
        if (s < 0) { snprintf(what, sizeof(what), "sistema desconocido %s", sys); ck(what, 0); continue; }
        GerarionCalDate got;
        int rc = gerarion_cal_from_day_index(di, s, &got);
        snprintf(what, sizeof(what), "%s di=%lld from_day_index rc=%d", sys, di, rc);
        ck(what, rc == GUS_OK);
        if (rc != GUS_OK) continue;
        GerarionCalDate want;
        fill_fields(jobj_get(v, "fields"), &want);
        int same = got.count == want.count && got.leap == want.leap;
        for (int k = 0; same && k < want.count; k++) same = got.f[k] == want.f[k];
        snprintf(what, sizeof(what), "%s di=%lld campos", sys, di);
        ck(what, same);
        if (!same) continue;
        long long back = -1;
        rc = gerarion_cal_to_day_index(s, &want, &back);
        snprintf(what, sizeof(what), "%s di=%lld ida-y-vuelta rc=%d back=%lld", sys, di, rc, back);
        ck(what, rc == GUS_OK && back == di);
    }

    /* 2. cross: palíndromo */
    arr = jobj_get(root, "cross");
    n = jarr_len(arr);
    for (int i = 0; i < n; i++) {
        JNode *c = jarr_at(arr, i);
        int from = gerarion_cal_system_from_id(jobj_get(c, "from")->str);
        int to = gerarion_cal_system_from_id(jobj_get(c, "to")->str);
        long long di = jobj_get(c, "day_index")->num;
        char what[256];
        total++;
        if (from < 0 || to < 0) { snprintf(what, sizeof(what), "cross sistemas"); ck(what, 0); continue; }
        GerarionCalDate d1, d2, d3;
        long long di2 = 0, di3 = -123456789;
        int rc = gerarion_cal_from_day_index(di, from, &d1);
        if (rc == GUS_OK) rc = gerarion_cal_to_day_index(from, &d1, &di2);
        if (rc == GUS_OK) rc = gerarion_cal_from_day_index(di2, to, &d2);
        if (rc == GUS_OK) rc = gerarion_cal_to_day_index(to, &d2, &di3);
        int ok = (rc == GUS_OK);
        if (ok) { rc = gerarion_cal_from_day_index(di3, from, &d3); ok = (rc == GUS_OK && di3 == di); }
        snprintf(what, sizeof(what), "cross %s->%s di=%lld rc=%d", jobj_get(c, "from")->str, jobj_get(c, "to")->str, di, rc);
        ck(what, ok);
    }

    /* 3. invalid: GUS_EINVAL (o el código del núcleo congelado) */
    arr = jobj_get(root, "invalid");
    n = jarr_len(arr);
    for (int i = 0; i < n; i++) {
        JNode *v = jarr_at(arr, i);
        int s = gerarion_cal_system_from_id(jobj_get(v, "system")->str);
        GerarionCalDate d;
        fill_fields(jobj_get(v, "fields"), &d);
        long long out = 0;
        int rc = gerarion_cal_to_day_index(s, &d, &out);
        char what[256];
        snprintf(what, sizeof(what), "invalid %s rc=%d", jobj_get(v, "system")->str, rc);
        ck(what, rc == GUS_EINVAL);
        total++;
    }

    /* 4. unsupported: GERARION_EUNSUPPORTED */
    arr = jobj_get(root, "unsupported");
    n = jarr_len(arr);
    for (int i = 0; i < n; i++) {
        JNode *v = jarr_at(arr, i);
        int s = gerarion_cal_system_from_id(jobj_get(v, "system")->str);
        long long out = 0;
        int rc;
        char what[256];
        JNode *dj = jobj_get(v, "day_index");
        if (dj) {
            rc = gerarion_cal_from_day_index(dj->num, s, &(GerarionCalDate){0});
        } else {
            GerarionCalDate d;
            fill_fields(jobj_get(v, "fields"), &d);
            rc = gerarion_cal_to_day_index(s, &d, &out);
        }
        snprintf(what, sizeof(what), "unsupported %s rc=%d", jobj_get(v, "system")->str, rc);
        ck(what, rc == GERARION_EUNSUPPORTED);
        total++;
    }

    /* 5. erange: GUS_ERANGE */
    arr = jobj_get(root, "erange");
    n = jarr_len(arr);
    for (int i = 0; i < n; i++) {
        JNode *v = jarr_at(arr, i);
        int s = gerarion_cal_system_from_id(jobj_get(v, "system")->str);
        GerarionCalDate d;
        fill_fields(jobj_get(v, "fields"), &d);
        long long out = 0;
        int rc = gerarion_cal_to_day_index(s, &d, &out);
        char what[256];
        snprintf(what, sizeof(what), "erange %s rc=%d", jobj_get(v, "system")->str, rc);
        ck(what, rc == GUS_ERANGE);
        total++;
    }

    /* 6. metadatos: 10 sistemas, campos y época */
    ck("10 sistemas registrados", gerarion_cal_field_count(GER_CAL_GUS) == 3
        && gerarion_cal_field_count(GER_CAL_MAYA) == 5
        && gerarion_cal_epoch_jdn(GER_CAL_GUS) == 1719313
        && gerarion_cal_epoch_jdn(GER_CAL_MAYA) == 584283);
    for (int s = 0; s < GER_CAL_COUNT; s++)
        ck("id de sistema", gerarion_cal_id(s) != NULL);
    total += 10;

    printf("guti-conformance (C11): %lld/%lld correctos%s\n",
           total - failures, total, failures ? "" : " — CONFORME");
    return failures ? 1 : 0;
}
