/*
 * gus.h — Núcleo GUS 2.x en C (segunda implementación independiente).
 *
 * Implementa el núcleo normativo: calendario regular (12x30 + Tempalum),
 * semana invariante, conversión JDN exacta con enteros, formato canónico
 * AAAAYY-MM-DD-X[-HH:MM:SS-SC/LC-TCJ±O] e instante continuo.
 *
 * CONFORMANCIA: según vectors/README.md, esta implementación es conforme si
 * pasa las categorías del núcleo de vectors/gus-normative-001.json
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

/* Constantes fundamentales (especificación GUS v2.0, sección 3) */
#define GUS_ORIGIN_JDN 1719313LL
#define GUS_SOLAR_DELTA_UD 1242190LL
#define GUS_SOLAR_THRESHOLD_UD 7000000LL
#define GUS_YEAR_COMMON_DAYS 364LL
#define GUS_YEAR_GRAN_DAYS 371LL
#define GUS_MONTH_BLOCK_DAYS 360LL
#define GUS_SECS_PER_DAY 86400LL

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
    bool has_time;
    char cycle[3];            /* "SC" o "LC"; "" si no hay hora */
    int offset;               /* TCJ en horas */
    bool era_assumed;
    bool weekday_corrected;
    bool cycle_corrected;
} GusParsed;

/* ---------------- calendario ---------------- */

bool gus_is_gran_tempalum(long long year);      /* false para la era AY */
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

/* Analiza una marca Geroriana (aplica normalización REGLAS 1-6).
 * Con strict=true, la letra de día inconsistente devuelve GUS_EWEEK. */
GusError gus_parse(const char *raw, bool strict, GusParsed *out);

/* ---------------- instante continuo ---------------- */

GusError gus_instant_from_parts(long long day_index, int hour, int minute,
                                int second, long long *instant);
GusError gus_instant_parts(long long instant, GusDate *date,
                           int *hour, int *minute, int *second);

/* Ciclo luminoso: "SC" (06:00-17:59) o "LC" (18:00-05:59) */
GusError gus_cycle_of(int hour, char out[3]);

#ifdef __cplusplus
}
#endif

#endif /* GUS_H */
