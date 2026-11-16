# Capítulo 17 — Paquete Mínimo de Referencia (libgero-c) 

> **Documento técnico oficial**
> **Versión:** 1.2 (alineada con Capítulo 13 v1.2 y Anexo de Compatibilidad y Ciberseguridad v1.2)
> **Estado:** Especificación de referencia — primera versión compatible con el kernel canónico
> **Ámbito:** Librería C mínima para parseo, serialización, conversión y Tempalum

> **Nota de procedencia:** existió un borrador previo de este documento que usaba una regla de año bisiesto por divisibilidad fija (`year % 4 == 0 && year % 128 != 0`) y un Tempalum de 5/6 días. **Esa versión es incompatible con el kernel del Gerarion y queda descartada en su totalidad.** El Gerarion no tiene años "bisiestos" en el sentido gregoriano — tiene el **Gran Tempalum**, determinado por un acumulador solar progresivo (Cap 5, Cap 11), y el Tempalum tiene **4 días (año normal) u 11 días (Gran Tempalum)** — nunca 5 ni 6. Este documento es la única versión válida de `libgero-c`.

---

## 1. Abstract

Este documento define el paquete mínimo de referencia **libgero-c**, una librería C orientada a sistemas embebidos, kernel-adjacent code, servicios de backend y validación de calendarios Gerarions. Su objetivo es proporcionar una implementación pequeña, verificable y portable de:

- parseo de timestamps Gerarions (formato extendido y compacto, Cap 13.1 v1.2),
- serialización canónica,
- conversión Gerarion ↔ TAI (`tai_seconds = unix_epoch_seconds + ΔTAI`, Cap 9.4.2),
- conversión Gerarion ↔ UTC,
- manejo del Tempalum y el Gran Tempalum (acumulador solar, Cap 5),
- comparación y diferencia temporal,
- verificación de identificador de fecha por invariante I-1 (Cap 13.2 v1.2),
- y una tabla de conversión de referencia para validación.

Este paquete es la primera implementación que satisface el requisito de "implementación de referencia funcional" declarado como línea abierta en el Estado del Sistema v1.1 (sección 5).

## 2. Design Goals

1. Código pequeño y auditable.
2. Sin dependencias pesadas.
3. Compatible con C99.
4. Portable en Linux, BSD, macOS y sistemas embebidos.
5. Determinista y apto para fuzzing.
6. Adecuado como base de implementación de referencia.
7. Conforme estrictamente con el kernel canónico v1.2 — ninguna regla de este documento puede contradecir el Capítulo 13 v1.2 ni el Anexo Matemático.

## 3. Non-Goals

Este paquete no pretende:

- Proveer interfaz gráfica.
- Implementar el quorum completo de verificación astronómica TSLR (Cap 13.4.1) — solo expone los puntos de extensión necesarios para que una capa superior lo implemente.
- Reemplazar la librería de fecha/hora del sistema.
- Incluir lógica de gobernanza o de certificación de forks (Cap 15.2.1).
- Implementar el Perfil IoT Ligero completo (Cap 13.4.2) — eso es responsabilidad de una capa de aplicación sobre esta librería.

## 4. Public API

### 4.1 Core Types

```c
#include <stdint.h>

/* Ciclo horario — Cap 3, Cap 13.3 v1.2 */
typedef enum {
    GERO_CYCLE_SC = 0,  /* Solcycle  — 06:00 a 17:59, hora civil del observador */
    GERO_CYCLE_LC = 1   /* Loonacycle — 18:00 a 05:59, hora civil del observador */
} gero_cycle_t;

/* Día de semana Nuvid — Cap 13.2 v1.2 */
typedef enum {
    GERO_SOLUDYIA   = 0,
    GERO_LOONDYIA   = 1,
    GERO_MARDYIA    = 2,
    GERO_AISTERDYIA = 3,
    GERO_TRUSTDYIA  = 4,
    GERO_VIENDYIA   = 5,
    GERO_SABATYEH   = 6
} gero_weekday_t;

/* Representación binaria de un timestamp Gerarion completo.
 * Diseñada para wire format determinista (40 bytes, Cap 14). */
typedef struct {
    int64_t  tai_seconds;          /* ancla TAI — base de toda conversión */
    int32_t  tai_nanoseconds;
    int32_t  tcj_offset_seconds;   /* offset de coordinación, TCJ±O */
    int32_t  year;                 /* con signo: negativo = AY */
    uint8_t  is_ay;                /* 1 si año < 0 (época AY), 0 si DY */
    uint8_t  month;                /* 0 = Tempalum, 1-12 = meses regulares */
    uint8_t  day;                  /* 1-30 en meses regulares; 1-4 o 1-11 en Tempalum */
    uint8_t  weekday;              /* gero_weekday_t */
    uint8_t  hour;                 /* 0-23, hora civil del observador */
    uint8_t  minute;               /* 0-59 */
    uint8_t  second;               /* 0-59 */
    uint8_t  cycle;                /* gero_cycle_t */
    uint8_t  flags;                /* ver 4.4 */
    uint8_t  reserved[3];          /* padding explícito, alineación de 4 bytes */
} gero_timestamp_t;

/* Vista civil/humana, sin ancla TAI — para construcción manual
 * antes de resolver a un timestamp completo. */
typedef struct {
    int32_t year;
    int8_t  month;
    int8_t  day;
    int8_t  weekday;     /* -1 si se debe calcular automáticamente */
    int8_t  hour;
    int8_t  minute;
    int8_t  second;
    int8_t  cycle;        /* -1 si se debe derivar de hour */
    int32_t tcj_offset_seconds;
} gero_civil_t;
```

### 4.2 Functions

```c
/* --- Parseo y formato --- */
int gero_parse(const char *input, gero_timestamp_t *out);
int gero_format_extended(const gero_timestamp_t *ts, char *buf, size_t buflen); /* 32 chars */
int gero_format_compact(const gero_timestamp_t *ts, char *buf, size_t buflen);  /* 29 chars */

/* --- Conversión TAI (Cap 9.4.2, fórmula corregida v1.1/v1.2) --- */
int gero_from_tai(int64_t tai_seconds, int32_t tai_nanoseconds, gero_timestamp_t *out);
int gero_to_tai(const gero_timestamp_t *ts, int64_t *tai_seconds, int32_t *tai_nanoseconds);

/* --- Conversión UTC --- */
int gero_from_utc(const char *utc_iso8601, gero_timestamp_t *out);
int gero_to_utc(const gero_timestamp_t *ts, char *buf, size_t buflen);

/* --- Comparación y aritmética --- */
int gero_compare(const gero_timestamp_t *a, const gero_timestamp_t *b);
int gero_diff_days(const gero_timestamp_t *a, const gero_timestamp_t *b, int64_t *days_out);

/* --- Reglas del kernel (Cap 5, Cap 11) --- */
int gero_is_gran_tempalum(int32_t year);          /* NO "leap year" — ver 7 */
int gero_is_tempalum(uint8_t month);
int gero_days_in_year(int32_t year);               /* 364 o 371 */
int gero_days_in_tempalum(int32_t year);            /* 4 u 11 */
int gero_is_valid_date(int32_t year, uint8_t month, uint8_t day);

/* --- Verificación (Cap 13.2 v1.2, invariante I-1) --- */
int gero_verify_weekday(int32_t year, uint8_t month, uint8_t day, uint8_t weekday);
int gero_verify_cycle(uint8_t hour, uint8_t cycle);  /* Cap 13.3 v1.2 */

/* --- JDN: puente universal (Cap 9.3, Anexo Matemático) --- */
int64_t gero_to_jdn(const gero_timestamp_t *ts);
int gero_from_jdn(int64_t jdn, int32_t fork_origin_jdn, gero_timestamp_t *out);
```

### 4.3 Return Codes

```c
enum {
    GERO_OK            =  0,
    GERO_EINVAL        = -1,  /* parámetro inválido genérico */
    GERO_ERANGE        = -2,  /* fuera de rango (mes, día, hora...) */
    GERO_EPARSE        = -3,  /* fallo de parseo sintáctico */
    GERO_EFORMAT       = -4,  /* buffer de salida insuficiente */
    GERO_ETEMPALUM     = -5,  /* día de Tempalum inválido para ese año */
    GERO_EOVERFLOW     = -6,
    GERO_EUNDERFLOW    = -7,
    GERO_EWEEKDAY      = -8,  /* weekday no coincide con el calculado (modo estricto) */
    GERO_ECYCLE        = -9,  /* SC/LC inconsistente con la hora declarada */
    GERO_EFORK         = -10  /* fork no reconocido o JDN_ORIGEN inválido */
};
```

### 4.4 Flags (byte de banderas, Cap 12.6)

```c
#define GERO_FLAG_IS_TEMPALUM        (1 << 0)
#define GERO_FLAG_IS_GRAN_TEMPALUM   (1 << 1)
#define GERO_FLAG_TSLR_VERIFIED      (1 << 2)
#define GERO_FLAG_UTC_COMPAT         (1 << 3)
#define GERO_FLAG_WEEKDAY_CORRECTED  (1 << 4)
#define GERO_FLAG_FORK_CUSTOM        (1 << 5)
#define GERO_FLAG_TAI_ANCHORED       (1 << 6)
#define GERO_FLAG_SACRED_DAY         (1 << 7)
```

## 5. Data Model Rules

### 5.1 Year System

- `year >= 0` usa sufijo `DY`.
- `year < 0` usa sufijo `AY`.
- El año 0 existe y forma parte de la época Geroriana (1 Keuphero, Año 0 DY = 21 marzo, 6 a.C.).
- El año NO se determina "bisiesto" por divisibilidad. Ver sección 7.

### 5.2 Month System

- `00` = Tempalum.
- `01`–`12` = meses regulares (Keuphero a Ichtys).

### 5.3 Day System

- `01`–`30` para meses regulares — **siempre 30, sin excepción** (Cap 4.1).
- `01`–`04` para Tempalum en año normal.
- `01`–`11` para Tempalum en año con Gran Tempalum.

> **Corrección crítica respecto al borrador previo:** el rango de Tempalum NUNCA es `01`–`05` ni `01`–`06`. Es `01`–`04` (normal) o `01`–`11` (Gran Tempalum). Esta es la corrección más importante de esta versión.

### 5.4 Weekday System

| Char | Nombre |
|------|--------|
| `S` | Soludyia |
| `L` | Loondyia |
| `M` | Mardyia |
| `A` | Aisterdyia |
| `T` | Trustdyia |
| `V` | Viendyia |
| `B` | Sabatyeh |

### 5.5 Cycle System

- `SC` = Solcycle — 06:00 a 17:59, hora civil del observador.
- `LC` = Loonacycle — 18:00 a 05:59, hora civil del observador.

> **Clarificación obligatoria (Cap 13.3 v1.2):** SC/LC se calcula siempre sobre la hora civil del observador que generó el timestamp — nunca sobre la hora del meridiano TCJ. El campo `tcj_offset_seconds` es exclusivamente de coordinación entre sistemas y es independiente del cálculo de `cycle`.

## 6. Canonical String Format (corregido v1.2)

El borrador previo de este documento usaba un formato (`YYYYDY-MM-DD-W-HHMMCC-TCJ±O`) que no corresponde a ninguno de los dos formatos oficiales. Esta versión implementa exactamente los formatos definidos en el Capítulo 13.1 v1.2:

### 6.1 Formato Extendido — 32 caracteres

```text
AAAADY-MM-DD-X-HH:MM:SS-CC-TCJ±O
```

```text
2032DY-01-30-L-09:00:00-SC-TCJ+0
2032DY-00-03-V-10:00:00-SC-TCJ+2
2032DY-12-15-B-21:30:00-LC-TCJ+0
```

### 6.2 Formato Compacto — 29 caracteres

```text
AAAADY-MM-DD-X-HHMMSS-CC-TCJO
```

```text
2032DY-01-30-L-090000-SC-TCJ+0
2032DY-00-03-V-100000-SC-TCJ+2
2032DY-12-15-B-213000-LC-TCJ0
```

> Nota: en el formato compacto, el offset `TCJ0` omite el signo únicamente cuando el offset es cero. Cualquier offset distinto de cero conserva el signo explícito (`TCJ+2`, `TCJ-5`), en ambos formatos.

## 7. Gran Tempalum Rule (corregido v1.2 — reemplaza por completo la regla de "leap year")

El Gerarion **no tiene años bisiestos**. Tiene el **Gran Tempalum**, determinado por un acumulador solar progresivo que se evalúa año por año desde el origen — no por una fórmula de divisibilidad fija. Esta es la corrección más importante respecto al borrador previo, que usaba incorrectamente `year % 4 == 0 && year % 128 != 0`.

```c
#define GERO_DIAS_SOLAR   365.24219
#define GERO_BASE_ANIO    364.0
#define GERO_UMBRAL_GT    7.0

/*
 * gero_is_gran_tempalum: determina si un año tiene Gran Tempalum
 * (Tempalum de 11 días) reproduciendo el acumulador desde el
 * origen del fork. Cap 5.3, Anexo Matemático F-07.
 *
 * NOTA DE RENDIMIENTO: esta implementación de referencia es O(n)
 * en el año consultado, por claridad y auditabilidad. Una
 * implementación de producción DEBE precalcular y cachear una
 * tabla de Gran Tempalum (ver 7.1) en lugar de recorrer el
 * acumulador en cada llamada.
 */
int gero_is_gran_tempalum(int32_t year) {
    if (year < 0) return GERO_EINVAL; /* AY requiere tratamiento de fork, fuera de alcance mínimo */

    double acc = 0.0;
    for (int32_t y = 0; y < year; y++) {
        acc += GERO_DIAS_SOLAR - GERO_BASE_ANIO;
        if (acc >= GERO_UMBRAL_GT) {
            acc -= GERO_UMBRAL_GT;
        }
    }
    acc += GERO_DIAS_SOLAR - GERO_BASE_ANIO;
    return acc >= GERO_UMBRAL_GT;
}

int gero_days_in_tempalum(int32_t year) {
    int gt = gero_is_gran_tempalum(year);
    if (gt < 0) return gt;
    return gt ? 11 : 4;
}

int gero_days_in_year(int32_t year) {
    int gt = gero_is_gran_tempalum(year);
    if (gt < 0) return gt;
    return gt ? 371 : 364;
}
```

### 7.1 Tabla precalculada de Gran Tempalum (recomendada para producción)

```c
/* Años DY con Gran Tempalum, precalculados 0-99 (Cap 5.3).
 * Una implementación de producción debe generar y mantener
 * esta tabla en lugar de recalcular el acumulador en runtime. */
static const int32_t GERO_GT_YEARS_0_99[] = {
    5, 11, 16, 22, 28, 33, 39, 45, 50, 56,
    61, 67, 73, 78, 84, 90, 95
    /* ... continuar generando con gero_is_gran_tempalum()
       y congelar la tabla por rango, no recalcular en caliente */
};
```

> Próximos Gran Tempalum desde el presente (Cap 5.3, ya verificados): **2028, 2034, 2039, 2045, 2051, 2056** DY.

## 8. Month Length Rules

### 8.1 Regular Months

Todos los meses 1 a 12 tienen exactamente 30 días. Sin excepción, sin variación por año.

### 8.2 Tempalum (corregido v1.2)

```c
int gero_days_in_month(int32_t year, uint8_t month) {
    if (month == 0) {
        return gero_days_in_tempalum(year); /* 4 u 11 — NUNCA 5 ni 6 */
    }
    if (month >= 1 && month <= 12) {
        return 30;
    }
    return GERO_EINVAL;
}
```

## 9. Parsing Rules

### 9.1 Accepted Inputs

La librería debe aceptar (Cap 12.3):

- fecha completa con hora, en formato extendido o compacto,
- fecha sin hora,
- fecha con o sin weekday (se calcula si está ausente),
- representación de Tempalum (mes `00`),
- formato canónico en mayúsculas,
- entrada con o sin signo explícito en offset cero (`TCJ0` y `TCJ+0` son equivalentes).

### 9.2 Rejection

Debe rechazar:

- meses fuera de rango `[0, 12]`,
- días inválidos para el mes y año dados (incluyendo Tempalum fuera de `[1,4]` o `[1,11]` según corresponda),
- nombres de ciclo distintos de `SC`/`LC`,
- weekday no coincidente si el modo estricto está activado (`GERO_EWEEKDAY`),
- ciclo inconsistente con la hora declarada si el modo estricto está activado (`GERO_ECYCLE`).

### 9.3 Strict Mode

En modo estricto:

- el weekday debe coincidir con `gero_verify_weekday()`,
- el ciclo debe coincidir con `gero_verify_cycle()`.

## 10. Conversion Rules

### 10.1 Gerarion to TAI

1. Validar año, mes y día (`gero_is_valid_date`).
2. Calcular el JDN del día mediante `gero_to_jdn`, que internamente reproduce el acumulador solar desde `JDN_ORIGEN` (Cap 9.3, Anexo Matemático F-01 a F-05).
3. Convertir JDN + hora civil a segundos TAI mediante el puente Unix: `tai_seconds = unix_epoch_seconds + ΔTAI` (Cap 9.4.2 v1.1, ΔTAI = 37 vigente).

### 10.2 TAI to Gerarion

1. Derivar `unix_epoch_seconds = tai_seconds - ΔTAI`.
2. Derivar el JDN correspondiente.
3. Reproducir el acumulador solar desde `JDN_ORIGEN` para identificar año, mes y día (`gero_from_jdn`).
4. Derivar weekday por la invariante I-1 (Cap 13.2 v1.2 — el módulo 7 dentro del año es válido sin excepción, ver sección 11 de este documento).
5. Derivar ciclo (`SC`/`LC`) a partir de la hora civil resultante.

### 10.3 Determinism

La misma entrada debe producir la misma salida en todas las plataformas. No se permite ninguna dependencia de locale, zona horaria del sistema, ni redondeo de punto flotante no especificado — el acumulador solar debe usar `double` IEEE 754 de forma consistente entre implementaciones (ver 16.4).

## 11. Weekday Verification — Invariante I-1 (Cap 13.2 v1.2)

```c
/*
 * gero_verify_weekday: verifica el día de semana sin necesidad
 * de recorrer años anteriores, apoyándose en la invariante I-1:
 *
 *   364 mod 7 == 0   (año normal)
 *   371 mod 7 == 0   (Gran Tempalum)
 *
 * Como ambas duraciones de año son múltiplos exactos de 7, el
 * 1 de Keuphero SIEMPRE cae en Soludyia, sin importar cuántos
 * Gran Tempalum ocurrieron antes. Por lo tanto, el cálculo
 * dentro de un año cualquiera es válido sin consultar el
 * historial de años anteriores. Esta propiedad fue verificada
 * exhaustivamente para 2,060 años consecutivos (Cap 13.2 v1.2).
 */
int gero_verify_weekday(int32_t year, uint8_t month, uint8_t day, uint8_t weekday) {
    int dias_en_anio;
    if (month == 0) {
        dias_en_anio = 360 + (day - 1);
    } else {
        dias_en_anio = (month - 1) * 30 + (day - 1);
    }
    static const uint8_t CHARS[7] = {
        GERO_SOLUDYIA, GERO_LOONDYIA, GERO_MARDYIA, GERO_AISTERDYIA,
        GERO_TRUSTDYIA, GERO_VIENDYIA, GERO_SABATYEH
    };
    return CHARS[dias_en_anio % 7] == weekday ? GERO_OK : GERO_EWEEKDAY;
}

/*
 * gero_verify_cycle: verifica que el ciclo SC/LC sea consistente
 * con la hora civil declarada DEL MISMO OBSERVADOR (Cap 13.3 v1.2).
 * Nunca se evalúa contra la hora de otro meridiano.
 */
int gero_verify_cycle(uint8_t hour, uint8_t cycle) {
    uint8_t esperado = (hour >= 6 && hour <= 17) ? GERO_CYCLE_SC : GERO_CYCLE_LC;
    return cycle == esperado ? GERO_OK : GERO_ECYCLE;
}
```

## 12. Tempalum Handling

### 12.1 Representation

Tempalum se representa como mes `00`.

### 12.2 Internal Ordering

Orden temporal dentro del año:

```text
01..12 -> 00 -> siguiente año 01
```

### 12.3 Comparison

Las funciones de comparación deben tratar Tempalum como cierre anual, no como inicio del siguiente año.

### 12.4 Tempalum Day Table (corregida v1.2)

**Tabla normal (4 días, todos los años):**

| Día | Nombre | Función | Weekday |
|-----|--------|---------|---------|
| 01 | Unictis | Gratitud por ser | Aisterdyia |
| 02 | Kindom | Familia y hogar | Trustdyia |
| 03 | Iki | Propósito personal | Viendyia |
| 04 | Ikiyeh | Umbral — Dios | Sabatyeh |

**Tabla de Gran Tempalum (11 días — días 1-4 idénticos a la tabla normal, más 7 días adicionales):**

| Día | Nombre | Función | Weekday |
|-----|--------|---------|---------|
| 05 | Nuvivid I | La gracia del presente | Soludyia |
| 06 | Nuvivid II | El nuevo ciclo que espera | Loondyia |
| 07 | Nuvivid III | La acción que viene | Mardyia |
| 08 | Nuvivid IV | La tierra preparada | Aisterdyia |
| 09 | Nuvivid V | La verdad que se asienta | Trustdyia |
| 10 | Nuvivid VI | La alegría del umbral | Viendyia |
| 11 | Nuvivid VII | Día de cierre final | Sabatyeh |

> **Corrección respecto al borrador previo:** no existe un día llamado "Yeshuaway" en ningún glosario oficial del proyecto. El día 4 es siempre **Ikiyeh**, tanto en año normal como en Gran Tempalum — no se desplaza.

## 13. Reference Conversion Table

### 13.1 Calendar Reference Table

| Gerarion | Nuvid | Universal | Tipo | Días | Observación |
|-----------|-------|-----------|------|------|-------------|
| 01 | Keuphero | Equino | mes | 30 | Inicio de año |
| 02 | Duphilus | Ascendus | mes | 30 | |
| 03 | Tritom | Ascentris | mes | 30 | |
| 04 | Andra | Soltino | mes | 30 | |
| 05 | Quintob | Afelios | mes | 30 | |
| 06 | Hexohan | Torial | mes | 30 | |
| 07 | Barseti | Equinosu | mes | 30 | |
| 08 | Omary | Meridion | mes | 30 | |
| 09 | Novat | Noveridion | mes | 30 | |
| 10 | Deshimo | Soltisu | mes | 30 | |
| 11 | Duitades | Perion | mes | 30 | |
| 12 | Ichtys | Torialtys | mes | 30 | Cierre del ciclo regular |
| 00 | Tempalum | Zeroth | epagómeno | 4/11 | Días sagrados fuera de mes — **nunca 5/6** |

## 14. Test Vectors (regenerados v1.2 — verificados por cálculo exacto)

### 14.1 Valid Cases

```text
2032DY-01-01-S-00:00:00-SC-TCJ+0  -> valid, primer día del año
2032DY-01-30-L-09:00:00-SC-TCJ+0  -> valid, fin de mes (Keuphero)
2032DY-00-01-A-00:00:00-SC-TCJ+0  -> valid, Tempalum día 1 (Unictis)
2032DY-00-04-B-00:00:00-SC-TCJ+0  -> valid, Tempalum día 4 (Ikiyeh) — 2032 NO es Gran Tempalum
2034DY-00-11-B-00:00:00-SC-TCJ+0  -> valid SOLO en Gran Tempalum (Nuvivid VII)
```

### 14.2 Invalid Cases

```text
2032DY-00-05-S-00:00:00-SC-TCJ+0  -> invalid: 2032 no es Gran Tempalum (máx. día 4)
2032DY-00-12-S-00:00:00-SC-TCJ+0  -> invalid: excede incluso el máximo de Gran Tempalum (11)
2032DY-13-01-S-00:00:00-SC-TCJ+0  -> invalid: mes fuera de rango
2032DY-01-31-S-00:00:00-SC-TCJ+0  -> invalid: día 31 no existe (meses siempre tienen 30)
2032DY-00-00-S-00:00:00-SC-TCJ+0  -> invalid: día cero
2032DY-01-01-X-00:00:00-SC-TCJ+0  -> invalid: weekday "X" no existe
2032DY-01-01-L-14:00:00-LC-TCJ+0  -> invalid (modo estricto): 14:00 debe ser SC, no LC
```

### 14.3 Conversion Cases (recalculados — el placeholder TAI antiguo queda descartado)

```text
TAI 1807693237 -> 2032DY-01-30-L-09:00:00-SC-TCJ+0
                   (unix_epoch=1807693200, ΔTAI=37; greg. 2027-04-14 09:00:00 UTC)

2032DY-00-01-A-00:00:00-SC-TCJ+0 -> greg. 2028-03-10
2032DY-00-04-B-00:00:00-SC-TCJ+0 -> greg. 2028-03-13

2034DY-00-01-A -> greg. 2030-03-08  (inicio Gran Tempalum)
2034DY-00-11-B -> greg. 2030-03-18  (Nuvivid VII, fin Gran Tempalum)
```

> Nota: estos valores fueron recalculados desde cero usando el algoritmo canónico (Anexo Matemático, Cap 11). Ninguno reutiliza el placeholder `2085570600`/`2085609630` del borrador anterior, que ya fue purgado de todo el proyecto.

## 15. Fuzzing Strategy

La librería debe soportar fuzzing con tres objetivos:

1. Detectar errores de parseo.
2. Detectar desbordamientos.
3. Detectar inconsistencias entre parseo y formateo.

### 15.1 Fuzz Inputs

- Strings vacías.
- Fechas incompletas.
- Offsets inválidos (`TCJ` sin signo ni número, `TCJ++3`).
- Meses fuera de rango.
- Tempalum mal formado (día 5-11 en año sin Gran Tempalum).
- UTF-8 no ASCII.
- Campos duplicados.
- Mezcla de formato extendido y compacto en una sola cadena.

## 16. Property Tests

La referencia debe cumplir estas propiedades:

1. `format_extended(parse(x)) == canonical_extended(x)` para entradas válidas.
2. `format_compact(parse(x)) == canonical_compact(x)` para entradas válidas.
3. `to_tai(from_tai(t)) == t` dentro del perfil de precisión (round-trip exacto, ver Anexo Matemático sección 4).
4. `compare(a,b)` es antisimétrico.
5. `diff(a,b) == -diff(b,a)`.
6. El orden temporal es total para timestamps válidos del mismo fork.
7. `gero_is_gran_tempalum(year)` coincide exactamente con la tabla de referencia del Cap 5.3 para los años 2028, 2034, 2039, 2045, 2051, 2056.
8. `gero_verify_weekday` nunca falla para ninguna fecha válida generada por `gero_from_tai` (round-trip de invariante I-1).

## 17. Memory and Portability

### 17.1 C99 Constraint

No se deben usar extensiones no portables en el núcleo mínimo.

### 17.2 No Dynamic Allocation in Hot Path

Las funciones de parseo y formato deben operar sin asignación dinámica.

### 17.3 Endianness

Las estructuras binarias deben serializarse con orden de bytes definido por el perfil de wire format (network byte order / big-endian, consistente con Cap 14).

### 17.4 Determinismo de punto flotante (añadido v1.2)

El acumulador solar (`GERO_DIAS_SOLAR - GERO_BASE_ANIO`) usa aritmética `double` IEEE 754. Todas las implementaciones de referencia deben:

- Evitar operaciones que dependan de extensiones de precisión extendida no estándar (`long double` x87, FMA implícito).
- Validar contra los vectores de la sección 14 en cada plataforma soportada antes de declarar conformidad.

## 18. Reference Implementation Sketch

```c
int gero_is_valid_date(int32_t year, uint8_t month, uint8_t day) {
    int dim = gero_days_in_month(year, month);
    if (dim < 0) return dim;
    return (day >= 1 && day <= dim) ? GERO_OK : GERO_EINVAL;
}

int gero_is_tempalum(uint8_t month) {
    return month == 0;
}
```

## 19. Error Handling

### 19.1 Parse Errors

El parser DEBE retornar códigos de error estructurados en lugar de fallar (`crash`).

### 19.2 Range Errors

Los valores fuera de rango DEBEN ser rechazados con `GERO_ERANGE` o `GERO_ETEMPALUM` según corresponda.

### 19.3 Strict Validation Errors

Cuando el modo estricto está activo, una discrepancia entre weekday declarado y calculado DEBE reportarse como `GERO_EWEEKDAY`; una discrepancia de ciclo DEBE reportarse como `GERO_ECYCLE`.

## 20. Compatibility Layer

`libgero-c` PUEDE proveer funciones auxiliares para interoperar con `time.h` estándar de C:

- Helpers de conversión a/desde `struct tm`.
- Helpers de cadena UTC.
- Helpers de epoch POSIX.

Estos helpers DEBEN ser opcionales para no arrastrar ambigüedad específica del sistema al núcleo de la librería.

## 21. Packaging

```text
libgero-c/
├── include/
│   └── gero.h
├── src/
│   ├── parse.c
│   ├── format.c
│   ├── convert.c
│   ├── tempalum.c
│   ├── gran_tempalum.c     /* acumulador solar — núcleo del kernel */
│   ├── verify.c            /* gero_verify_weekday, gero_verify_cycle */
│   └── compare.c
├── tests/
│   ├── test_parse.c
│   ├── test_format.c
│   ├── test_convert.c
│   ├── test_tempalum.c
│   ├── test_gran_tempalum.c
│   └── test_verify.c
├── vectors/
│   └── gerarion_vectors_v1_2.txt
└── README.md
```

## 22. Compliance

Un paquete PUEDE reclamar conformidad de referencia `libgero-c v1.2` solo si:

1. Parsea timestamps canónicos en ambos formatos (extendido y compacto).
2. Formatea timestamps canónicos en ambos formatos.
3. Convierte a y desde TAI usando `tai_seconds = unix_epoch_seconds + ΔTAI`.
4. Maneja el Tempalum con 4 días (normal) y 11 días (Gran Tempalum) — nunca 5/6.
5. Determina el Gran Tempalum mediante el acumulador solar (sección 7), nunca por divisibilidad fija.
6. Pasa los vectores de prueba de referencia (sección 14).
7. Provee códigos de error documentados, incluyendo `GERO_EWEEKDAY` y `GERO_ECYCLE`.
8. Implementa `gero_verify_weekday` conforme a la invariante I-1 (sección 11).

## 23. Minimal Test Suite

### 23.1 Required Tests

- Parsear timestamp canónico válido (ambos formatos).
- Rechazar mes inválido.
- Rechazar día inválido.
- Rechazar día de Tempalum inválido para el año dado (5+ en año normal).
- Round trip de formato.
- Convertir TAI a Gerarion.
- Convertir Gerarion a TAI.
- Comparar dos timestamps.
- Diferencia de días a través del límite del Tempalum.
- Verificar `gero_is_gran_tempalum` contra los 6 años conocidos (2028-2056).
- Verificar `gero_verify_cycle` rechaza SC/LC inconsistente.

### 23.2 Example Assertions

```c
gero_timestamp_t ts;

ASSERT_EQ(GERO_OK, gero_parse("2032DY-01-30-L-09:00:00-SC-TCJ+0", &ts));

char buf[40];
ASSERT_EQ(GERO_OK, gero_format_extended(&ts, buf, sizeof buf));
ASSERT_STR_EQ("2032DY-01-30-L-09:00:00-SC-TCJ+0", buf);

ASSERT_EQ(GERO_OK,     gero_is_valid_date(2032, 0, 4));   /* Ikiyeh, año normal */
ASSERT_EQ(GERO_EINVAL, gero_is_valid_date(2032, 0, 5));   /* 2032 no es GT */
ASSERT_EQ(GERO_OK,     gero_is_valid_date(2034, 0, 11));  /* Nuvivid VII, 2034 SÍ es GT */

ASSERT_EQ(1, gero_is_gran_tempalum(2034));
ASSERT_EQ(0, gero_is_gran_tempalum(2032));

int64_t tai;
int32_t nanos;
ASSERT_EQ(GERO_OK, gero_to_tai(&ts, &tai, &nanos));
ASSERT_EQ(1807693237, tai);
```

## 24. Open Issues

Lo siguiente queda intencionalmente delegado a documentos complementarios o perfiles de plataforma:

- Codificación exacta del wire binario (Cap 14, perfil de transporte).
- Política exacta de despliegue del offset TCJ entre nodos.
- Implementación completa del quorum de verificación TSLR (Cap 13.4.1) — esta librería expone únicamente el punto de extensión, no la red de nodos.
- Tablas históricas completas de leap-second para conversión UTC retroactiva anterior a 1972.
- Implementación del Perfil IoT Ligero completo (Cap 13.4.2).

## 25. Conclusion

`libgero-c` v1.2 es la implementación portable mínima del modelo Gerarion, alineada estrictamente con el Capítulo 13 v1.2 y el Anexo de Compatibilidad y Ciberseguridad v1.2 — las fuentes normativas vigentes del proyecto. Corrige las cuatro incompatibilidades estructurales del borrador anterior (regla de Gran Tempalum, longitud del Tempalum, nombres de días sagrados, y formato canónico), y queda como la primera implementación de referencia funcional que el Estado del Sistema v1.1 declaraba como línea abierta.

Está pensada para ser pequeña para auditoría, estricta para corrección, y flexible para servir como capa de referencia para bindings de lenguajes de alto nivel, integración de kernel, y perfiles de certificado (GCERTS, Cap 13.4 v1.2).

---

*Fin del paquete de referencia libgero-c v1.2*
*Alineado con: Capítulo 13 — Identificadores y Seguridad v1.2*
*Alineado con: Anexo de Compatibilidad y Ciberseguridad v1.2*
*Gerardo Loyola (github.com/geroiloyola) — investigación original*