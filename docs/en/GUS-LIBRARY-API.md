<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- SPDX-FileCopyrightText: 2026 verared contributors -->

# `libgerarion` · C11 library API (GUTI-1)

Single public entry point: `impl-c/gerarion.h`, which includes `gus.h`
(frozen kernel) and `gerarion_calendars.h` (multi-calendar engine). No
`malloc` in data structures, no external dependencies, no `Intl`.

## Version macros

```c
#define GERARION_VERSION_MAJOR 3
#define GERARION_VERSION_MINOR 1
#define GERARION_VERSION_PATCH 0
#define GERARION_VERSION_STRING "3.1.0"
```

## Return codes

| Code | Value | Meaning |
|---|---|---|
| `GUS_OK` | 0 | success |
| `GUS_EINVAL` | 1 | impossible argument or date (never normalized) |
| `GUS_ERANGE` | 2 | result outside the safe int64 domain |
| `GUS_ETEMPALUM` | 3 | Tempalum day requested in a non-GT year (kernel) |
| `GUS_EFORMAT` | 4 | invalid seal format (kernel) |
| `GERARION_EUNSUPPORTED` | 5 | valid date but outside the system's validated range (e.g. Chinese outside 1645–2650 CE) |

## Multi-calendar engine — `gerarion_calendars.h`

```c
typedef struct {
    long long f[5];   /* up to 5 fields (maya uses all five) */
    int count;        /* active fields: 3 (y/m/d) or 5 (maya) */
    int leap;         /* Chinese intercalary month */
} GerarionCalDate;

/* GUS day_index (JDN − 1719313) → date in `system` */
int gerarion_cal_from_day_index(long long day_index, int system,
                                GerarionCalDate *out);

/* date → GUS day_index; the exact identity is guaranteed */
int gerarion_cal_to_day_index(int system, const GerarionCalDate *date,
                              long long *out);

/* one-call A → GUS → B conversion (exact palindrome) */
int gerarion_cal_convert(int src, const GerarionCalDate *from, int dst,
                         GerarionCalDate *to);

/* metadata */
int gerarion_cal_system_from_id(const char *id);   /* -1 if unknown */
const char *gerarion_cal_id(int system);
int gerarion_cal_field_count(int system);
long long gerarion_cal_epoch_jdn(int system);
int gerarion_cal_selfcheck(void);                  /* 0 = all good */
```

Per-system error rules (selection):

| System | Errors |
|---|---|
| `greg` / `julian` | impossible civil dates (Feb 30, month 13) → `GUS_EINVAL` |
| `egyptian` | month 1..13 (13 = epagomenal, day ≤ 5) |
| `ethiopic` | Pagume ≤ 5/6 per year % 4 == 3 |
| `bahai` | month 0 = Ayyám-i-Há (4/5 days per Gregorian leap year) |
| `maya` | `uinal ≤ 17`, `kin/katun/tun ≤ 19`; baktun product guard for int64 |
| `islamic` | day 30 only in odd months and Dhu al-Hijjah of leap years |
| `hebrew` | horizon AM ±9×10¹¹ → `GUS_ERANGE`; rabbinic month 1..12/13 |
| `chinese` | strict range 1645–2650 → `GERARION_EUNSUPPORTED`; `leap` requires a real intercalary month |

## Build and install

```bash
make -C impl-c                  # conformance + library
make -C impl-c conformance      # kernel + 10 calendars (63,850 vectors)
make -C impl-c audit            # ASan + UBSan (0 errors, 0 leaks)
make -C impl-c install PREFIX=$HOME/.local   # lib + headers + pkg-config
pkg-config --cflags --libs gerarion
```

`gerarion.pc` declares no `Requires`: zero dependencies. Link
consumers against `libgerarion.a` (static) or `libgerarion.so.3` /
`libgerarion.3.dylib` (shared).

## Minimal example

```c
#include <stdio.h>
#include "gerarion.h"

int main(void) {
    GerarionCalDate d, b;
    int rc = gerarion_cal_from_day_index(207094, GER_CAL_MAYA, &d);
    if (rc != GUS_OK) return 1;                  /* 13.0.0.0.0 */
    printf("%lld.%lld.%lld.%lld.%lld\n", d.f[0], d.f[1], d.f[2], d.f[3], d.f[4]);
    rc = gerarion_cal_convert(GER_CAL_MAYA, &d, GER_CAL_GREG, &b);
    if (rc == GUS_OK)
        printf("greg: %lld-%02lld-%02lld\n", b.f[0], b.f[1], b.f[2]);
    return 0;
}
```

## Robustness assessment (current audit)

- `make -C impl-c audit` builds the engine and the kernel with
  `-fsanitize=address,undefined -fno-sanitize-recover=all -Werror` and runs
  10⁶ sampled conversions, `int64_t` bounds, impossible dates and exact
  error codes (0 failures).
- The frozen kernel arithmetic (`gus.c/gus.h`) was not modified in GUTI-1:
  the new objects live beside it, not inside it.
