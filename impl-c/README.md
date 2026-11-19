# impl-c — segunda implementación independiente del núcleo GUS (C11)

Implementación independiente del núcleo normativo de GUS: calendario
regular, semana invariante, conversión JDN exacta (enteros, sin punto
flotante), formato canónico `AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O]` e instante
continuo. Escrita a partir de `docs/spec/gus-2.1.0.md` y de
`vectors/gus-normative-003.json`, no por transcripción del código Python.

Desde la reorganización modular, `impl-c/` se divide por dominio:

| Directorio | Dominio | Contenido |
|---|---|---|
| `core/` | TCJ+GUS | Calendario AY/DY, formato 32/29, `quick_verify`, instantes `int64`+`nanos` (apto para MCU, sin reloj de SO ni tabla TAI) |
| `tai/` | TCJ/INTEROP | Tabla histórica TAI−UTC versionada (`IERS-C-2026.1`) y offset TCJ |
| `clock/` | GTS | Máquina de estados de reloj §6.3 (`GusClockState/Policy/Reading`) |
| `calendars/` | CALENDAR | Motor de 10 calendarios + tabla china determinista |

`gus.h` y `gerarion.h` permanecen en la raíz como paraguas (*umbrella*) de
compatibilidad: el código existente contra `gus.h` sigue compilando igual.
El Makefile construye cuatro bibliotecas independientes (`libgerarion-core`,
`libgerarion-clock`, `libgerarion-calendars`, `libgerarion`) con sus
archivos pkg-config (`gerarion*.pc`).

Alcance deliberado: **solo categorías del núcleo** (ver `vectors/README.md`).
No implementa criptografía: GST, firma SLH-DSA y notario exigen bibliotecas
auditadas (FIPS 205, FIPS 204) y su verificación no se reimplementa aquí.

## Compilar y verificar

```
make              # binarios: gus-conformance, gus-cli
make conformance  # ejecuta el runner de conformancia contra vectors/
```

Salida esperada: `CONFORME (núcleo GUS en C): 7 categorías, 0 fallos`.

## Prueba diferencial continua

```
python3 tools/fuzz_diff.py            # Python <-> JS <-> C
make fuzz                             # idem vía make
```

Genera miles de entradas aleatorias (semilla fija) y exige igualdad exacta de
las tres implementaciones en conversión y formato. Cualquier divergencia es un
fallo de conformancia, no una diferencia "aceptable".

## Restricciones documentadas

- El bloque opcional de hora se analiza como unidad atómica
  (`-HH:MM:SS-CC-TCJ±O`), igual que la referencia Python y el núcleo JS: no se
  aceptan colas parciales.
- La normalización trata espacio y punto como separadores, y mayúsculas;
  espacios múltiples y tabulaciones pueden divergir entre hosts — las marcas
  normativas no las usan.
