/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/*
 * gus.h — Núcleo GUS 2.x en C (segunda implementación independiente).
 *
 * Implementa el núcleo normativo: calendario regular (12x30 + Tempalum),
 * semana invariante, conversión JDN exacta con enteros, formato canónico
 * AAAAYY-MM-DD-X[-HH:MM:SS-SC/LC-TCJ±O] e instante continuo.
 *
 * CONFORMANCIA: según vectors/README.md, esta implementación es conforme si
 * pasa las categorías del núcleo de vectors/gus-normative-003.json
 * (make -C impl-c conformance). No implementa criptografía: las categorías
 * hashots/slh_dsa/notary exigen bibliotecas auditadas FIPS 205.
 *
 * Sin punto flotante en rutas normativas; sin dependencias externas (C11).
 */

#ifndef GUS_H
#define GUS_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Constantes fundamentales (especificación GUS v3.0.0, sección 3/§9) */
#define GUS_ORIGIN_JDN 1719313LL
#define GUS_SOLAR_DELTA_UD 1242190LL
#define GUS_SOLAR_THRESHOLD_UD 7000000LL
#define GUS_YEAR_COMMON_DAYS 364LL
#define GUS_YEAR_GRAN_DAYS 371LL
#define GUS_MONTH_BLOCK_DAYS 360LL
#define GUS_SECS_PER_DAY 86400LL

/* Capa 1 — TCJ (Cap 7/Cap 13 v1.2): TCJ = TAI + 8 400 s (Jerusalén) */
#define GUS_TCJ_OFFSET_SECONDS 8400LL

/* Tabla TAI − UTC (IERS): entradas {unix_utc_inicio, offset_s} vigente
 * desde esa fecha (28+1 entradas; pre-1958: 0 s proléptico, spec §9).
 * El puente GUS-3339 aplica la entrada vigente. */
typedef struct { long long epoch; int offset; } GusTaiEntry;
const GusTaiEntry *gus_tai_table(int *count);
int gus_tai_minus_utc(long long unix_seconds);

/* Códigos de error canónicos (GERO_*) */
typedef enum {
    GUS_OK = 0,
    GUS_EINVAL = 1,     /* campo fuera de rango o sintaxis inválida */
    GUS_ETEMPALUM = 2,  /* día de Tempalum inexistente para el tipo de año */
    GUS_EWEEK = 3       /* letra de día inconsistente en modo estricto */
} GusError;

#define GUS_ERR_NAME_MAX 16 /* "GERO_ETEMPALUM" + NUL */

/* Fecha Geroriana descompuesta */
typedef struct {
    long long year;      /* DY >= 0; < 0 es la era AY */
    int month;           /* 0 = Tempalum, 1..12 regulares */
    int day;             /* 1..30, o 1..4 / 1..11 en Tempalum */
    long long day_index; /* días desde el origen; negativo en la era AY */
    int weekday_index;   /* 0 = Soludyia .. 6 = Sabatyeh */
    char abbr;           /* 'S','L','M','A','T','V','B' */
} GusDate;

/* Resultado del análisis sintáctico del formato canónico */
#define GUS_FLAG_MAX 4
typedef struct {
    GusDate date;
    int hour, minute, second; /* 0 si la marca no trae hora */
    uint32_t nanos;           /* fracción sub-segundo 0..999999999 (campo
                               * SEPARADO del instante; 0 si no hay hora o
                               * no se declaró fracción). Nunca se fusiona
                               * con los segundos en un solo entero. */
    bool has_time;
    bool compact;             /* la entrada vino en formato compacto (29+) */
    char cycle[3];            /* "SC" o "LC"; "" si no hay hora */
    int offset;               /* TCJ±O en horas (compat 2.x; 0 si hay minutos) */
    int offset_seconds;       /* TCJ±O exacto en segundos (GUS 3.0.0) */
    bool era_assumed;
    bool weekday_corrected;
    bool cycle_corrected;
} GusParsed;

/* ---------------- calendario ---------------- */

bool gus_is_gran_tempalum(long long year);      /* simétrico: GT también en la era AY (spec 2.1) */
long long gus_year_length(long long year);
long long gus_tempalum_days(long long year);
long long gus_year_start_day_index(long long year);
long long gus_jdn(long long year, int month, int day); /* proleptico, años astronómicos */
void gus_jdn_to_gregorian(long long jdn, long long *year, int *month, int *day);

long long gus_day_index_from_gregorian(long long year, int month, int day);
void gus_gregorian_from_day_index(long long day_index, long long *year, int *month, int *day);

/* Conversión índice de día <-> fecha; GusError para fechas imposibles */
GusError gus_to_gerarion(long long day_index, GusDate *out);
GusError gus_from_gerarion(long long year, int month, int day, GusDate *out);

/* Tempalum de cierre ("Unictis".."Nuvivid VII"); NULL si no es Tempalum */
const char *gus_tempalum_name(const GusDate *d);

/* ---------------- formato canónico ---------------- */

/* Serializa fecha (o fecha+hora si has_time) a formato canónico.
 * buf debe tener al menos 48 bytes. Devuelve GUS_OK o GUS_EINVAL. */
GusError gus_canonical(const GusParsed *p, char *buf, size_t buflen);

/* Analiza una marca Geroriana (aplica normalización REGLAS 1-6; acepta
 * extendido y compacto; offsets TCJ±O con minutos, GUS 3.0.0).
 * Con strict=true, la letra de día inconsistente devuelve GUS_EWEEK. */
GusError gus_parse(const char *raw, bool strict, GusParsed *out);

/* Verificación rápida de consistencia interna, O(1) y sin red (Cap 13.8
 * v1.2): true solo si la marca es válida tal cual, sin correcciones
 * silenciosas (era asumida, letra Nuvid o ciclo declarados equivocados).
 * Filtro barato para logs e IoT; no sustituye la verificación de firma. */
bool gus_quick_verify(const char *raw);

/* ---------------- instante continuo ---------------- */

GusError gus_instant_from_parts(long long day_index, int hour, int minute,
                                int second, int offset_seconds, long long *instant);
GusError gus_parts_from_instant(long long instant, int offset_seconds,
                                GusDate *date, int *hour, int *minute, int *second);
GusError gus_instant_parts(long long instant, GusDate *date,
                           int *hour, int *minute, int *second);

/* Ciclo luminoso: "SC" (06:00-17:59) o "LC" (18:00-05:59) */
GusError gus_cycle_of(int hour, char out[3]);

/* ---------------- precisión sub-segundo (GUS 3.0.0) ---------------- */

#define GUS_NANOS_MAX 999999999u

/* Par canónico de precisión sub-segundo: segundos int64 + nanos uint32
 * SEPARADOS (nunca fusionados en un solo entero: preserva el horizonte
 * ±292e9 años). Sin asignación dinámica. */
typedef struct {
    long long seconds;   /* instante continuo TCJ en segundos (int64) */
    uint32_t nanos;      /* 0..999999999, validado estricto */
} GusInstant;

/* Valida la fracción: GUS_OK en 0..999999999; GUS_EINVAL si no
 * (rechaza, no normaliza en silencio). */
GusError gus_validate_nanos(uint32_t nanos);

/* Constructor con fracción: valida nanos y los segundos; los campos
 * viajan separados en *out. */
GusError gus_instant_from_parts_nanos(long long day_index, int hour,
                                      int minute, int second,
                                      uint32_t nanos, int offset_seconds,
                                      GusInstant *out);

/* ---------------- máquina de estados de reloj (§6.3) ---------------- */

typedef enum {
    GUS_CLOCK_VERIFIED = 0,   /* fuente autenticada dentro de la cota */
    GUS_CLOCK_HOLDOVER = 1,   /* extrapolación con ancla previa válida */
    GUS_CLOCK_UNVERIFIED = 2, /* sin fuente confiable / incertidumbre unknown */
    GUS_CLOCK_REJECTED = 3    /* retroceso respecto del ancla persistida */
} GusClockState;

typedef struct {
    long long seconds;        /* lectura absoluta propuesta (int64) */
    uint32_t nanos;           /* 0..999999999 */
    GusClockState state;
    const char *source_id;    /* identificador de la fuente (estático) */
    long long uncertainty_ns; /* cota de error declarada, ns */
    long long monotonic_ns;   /*_CLOCK_MONOTONIC del sistema en la lectura */
} GusClockReading;

/* Parámetros de la máquina de estados (todos en unidades explícitas). */
typedef struct {
    long long max_uncertainty_ns; /* cota para considerarlo VERIFIED */
    long long max_holdover_s;     /* ventana máxima de extrapolación */
    long long drift_ppm;          /* deriva máxima declarada (ppm) */
    int strict;                   /* 1: sin fuente → REJECTED (no UNVERIFIED) */
} GusClockPolicy;

/* Estabiliza una lectura contra el último ancla
 * (sec.monotonic + sec.nanos; -1 / UINT32_MAX si no hay). */
GusClockState gus_clock_classify(const GusClockReading *reading,
                                 const GusClockPolicy *policy,
                                 const GusClockReading *last_anchor);

/* ................ TAI − UTC versionado (puente vigilado) ................ */

typedef struct {
    const char *table_version;   /* "IERS-C-2026.1" */
    long long valid_until_unix;  /* fin de la vigencia verificada */
    const char *smear_policy;    /* "reject": el leap smear no es TAI */
} GusTaiTableInfo;

/* Metadatos de la tabla embebida (vigencia y política de smear). */
GusTaiTableInfo gus_tai_table_info(void);

/* Offset + aviso de extrapolación: *extrapolated = 1 si unix_seconds es
 * posterior a valid_until_unix (la tabla no cubre ese futuro: puede
 * cambiar con la transición a UTC continuo). */
int gus_tai_minus_utc_checked(long long unix_seconds, int *extrapolated);

#ifdef __cplusplus
}
#endif

#endif /* GUS_H */
