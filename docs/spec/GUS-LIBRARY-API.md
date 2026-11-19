<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- SPDX-FileCopyrightText: 2026 verared contributors -->

# `libgerarion` · API de la biblioteca C11 (GUTI-1)

Punto de entrada público único: `impl-c/gerarion.h`, que incluye `gus.h`
(núcleo congelado) y `gerarion_calendars.h` (motor multi-calendario).
Sin `malloc` en las estructuras de datos; sin LLVM deps; sin `Intl`.

## Versiones

```c
#define GERARION_VERSION_MAJOR 3
#define GERARION_VERSION_MINOR 1
#define GERARION_VERSION_PATCH 0
#define GERARION_VERSION_STRING "3.1.0"
```

## Códigos de retorno

| Código | Valor | Significado |
|---|---|---|
| `GUS_OK` | 0 | operaciones correcta |
| `GUS_EINVAL` | 1 | argumento o fecha imposible (nunca se normaliza) |
| `GUS_ERANGE` | 2 | resultado fuera del dominio int64 seguro |
| `GUS_ETEMPALUM` | 3 | día Tempalum pedido en año no GT (núcleo) |
| `GUS_EFORMAT` | 4 | sello con formato inválido (núcleo) |
| `GERARION_EUNSUPPORTED` | 5 | fecha válida pero fuera del rango validado del sistema (p. ej. chino fuera de 1645–2650 d.C.) |

## Motor multi-calendario — `gerarion_calendars.h`

```c
typedef struct {
    long long f[5];   /* hasta 5 campos (maya usa los cinco) */
    int count;        /* campos activos: 3 (y/m/d) o 5 (maya) */
    int leap;         /* mes intercalar chino */
} GerarionCalDate;

/* day_index GUS (JDN − 1719313) → fecha en `system` */
int gerarion_cal_from_day_index(long long day_index, int system,
                                GerarionCalDate *out);

/* fecha → day_index GUS; la identidad exacta está garantizada */
int gerarion_cal_to_day_index(int system, const GerarionCalDate *date,
                              long long *out);

/* conversión A → GUS → B en una llamada (palíndromo exacto) */
int gerarion_cal_convert(int src, const GerarionCalDate *from, int dst,
                         GerarionCalDate *to);

/* metadatos */
int gerarion_cal_system_from_id(const char *id);   /* -1 si desconocido */
const char *gerarion_cal_id(int system);
int gerarion_cal_field_count(int system);
long long gerarion_cal_epoch_jdn(int system);
int gerarion_cal_selfcheck(void);                  /* 0 = todo correcto */
```

Errores de cada sistema (selección):

| Sistema | Errores |
|---|---|
| `greg` / `julian` | fechas civiles imposibles (30/02, mes 13) → `GUS_EINVAL` |
| `egyptian` | mes 1..13 (13 = epagómenos, día ≤ 5) |
| `ethiopic` | Pagume ≤ 5/6 según `año % 4 == 3` |
| `bahai` | mes 0 = Ayyám-i-Há (4/5 días según bisiesto gregoriano del año) |
| `maya` | `uinal ≤ 17`, `kin/katun/tun ≤ 19`; baktun con guardia de producto int64 |
| `islamic` | día 30 solo en meses impares y Dhu al-Hiyya de años `año % 30 ∈ {2,5,…}` |
| `hebrew` | horizonte AM ±9·10¹¹ → `GUS_ERANGE`; mes rabínico 1..12/13 |
| `chinese` | rango estricto 1645–2650 → `GERARION_EUNSUPPORTED`; `leap` exige mes intercalar real |

## Compilación e instalación

```bash
make -C impl-c                  # conformance + librería
make -C impl-c conformance      # núcleo + 10 calendarios (63.850 vectores)
make -C impl-c audit            # ASan + UBSan (0 errores, 0 fugas)
make -C impl-c install PREFIX=$HOME/.local   # lib + cabeceras + pkg-config
pkg-config --cflags --libs gerarion
```

`gerarion.pc` declara `Requires` — nada: cero dependencias. El orden de
enlace para binarios consumidores: `libgerarion.a` (estática) o
`libgerarion.so.3` / `libgerarion.3.dylib` (compartida).

##umping Ejemplo mínimo

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

## Evaluación de robustez (auditoría vigente)

- `make -C impl-c audit` compila el motor y el núcleo con
  `-fsanitize=address,undefined -fno-sanitize-recover=all -Werror` y lo
  ejecuta sobre 10⁶ conversiones de muestreo, bordes `int64_t`,
  fechas imposibles y cadena de errores exactos (0 fallos).
- La aritmética congelada del núcleo (`gus.c/gus.h`) no se modificó en
  GUTI-1: los objetos nuevos viven al lado, no dentro.
