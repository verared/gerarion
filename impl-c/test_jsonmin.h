/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/*
 * test_jsonmin.h — parser JSON mínimo compartido por los runners de
 * pruebas de impl-c (conformance.c, guti_conformance.c y los harness
 * de auditoría). NO forma parte del código publicado de libgerarion:
 * es código de instrumento, stdlib puro, árbol en memoria con arena
 * sin liberar (los runners terminan al acabar la batería).
 */

#ifndef TEST_JSONMIN_H
#define TEST_JSONMIN_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

JNode *jload(const char *path);
JNode *jo(JNode *obj, const char *key);
JNode *jobj_get(const JNode *o, const char *key); /* alias tolerante de jo */
long long jn(JNode *obj, const char *key);
const char *js(JNode *obj, const char *key);
int jarr_len(const JNode *a);
JNode *jarr_at(const JNode *a, int i);

#endif /* TEST_JSONMIN_H */
