# impl-c — segunda implementación independiente del núcleo GUS (C11)

Implementación independiente del núcleo normativo de GUS 2.x: calendario
regular, semana invariante, conversión JDN exacta (enteros, sin punto
flotante), formato canónico `AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O]` e instante
continuo. Escrita a partir de `docs/spec/gus-2.1.0.md` y de
`vectors/gus-normative-002.json`, no por transcripción del código Python.

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
