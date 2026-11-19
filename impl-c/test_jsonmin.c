/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/*
 * test_jsonmin.c — implementación compartida del parser JSON mínimo de
 * los runners de pruebas. Extraída de conformance.c y guti_conformance.c
 * sin cambios de comportamiento (v3.1.1).
 */
#include "test_jsonmin.h"

/* Parser JSON mínimo (árbol en memoria, arena sin liberar)            */
/* ------------------------------------------------------------------ */


void jfail(JParser *p, const char *msg)
{
    if (p->err[0] == '\0') snprintf(p->err, sizeof(p->err), "%s (en offset %zu)", msg, p->pos);
}

void skip_ws(JParser *p)
{
    while (p->src[p->pos] == ' ' || p->src[p->pos] == '\t' ||
           p->src[p->pos] == '\n' || p->src[p->pos] == '\r') p->pos++;
}

JNode *jnew(JType t)
{
    JNode *n = calloc(1, sizeof(JNode));
    n->type = t;
    return n;
}

JNode *jparse_value(JParser *p);

char *jparse_string_raw(JParser *p)
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

JNode *jparse_object(JParser *p)
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

JNode *jparse_array(JParser *p)
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

JNode *jparse_value(JParser *p)
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

JNode *jload(const char *path)
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

JNode *jo(JNode *obj, const char *key)
{
    for (int i = 0; i < obj->count; i++)
        if (strcmp(obj->keys[i], key) == 0) return obj->items[i];
    return NULL;
}

long long jn(JNode *obj, const char *key)
{
    JNode *v = jo(obj, key);
    return v ? v->num : 0;
}

const char *js(JNode *obj, const char *key)
{
    JNode *v = jo(obj, key);
    return (v && v->type == J_STR) ? v->str : NULL;
}


/* --- helpers tolerantes (venían de guti_conformance.c) --- */

JNode *jobj_get(const JNode *o, const char *key)
{
    return jo((JNode *)o, key);
}

int jarr_len(const JNode *a)
{
    return (a && a->type == J_ARR) ? a->count : 0;
}

JNode *jarr_at(const JNode *a, int i)
{
    return (a && a->type == J_ARR && i < a->count) ? a->items[i] : NULL;
}
