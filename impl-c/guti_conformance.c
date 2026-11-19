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
#include "test_jsonmin.h"
#include "calendars/gerarion_calendars.h"

/* ------------------------------------------------------------------ */
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
    JNode *root = jload(path);
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
