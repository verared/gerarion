# Contribuir a GUS

## Principio único
Lo normativo es lo verificable. Cualquier cambio a la especificación se
manifiesta como: (1) texto en docs/spec/, (2) vectores en tests/, (3) entrada
en docs/history/errata-v1.2.md o CHANGELOG.md. Si un cambio no se puede expresar así,
no entra.

## Flujo
1. Discusión via GitHub Issues (etiqueta: `spec`, `impl`, `crypto`, `docs`).
2. PR con tests verdes. Los vectores normativos existentes no se editan: se
   deprecan con errata delante.
3. Cambios que alteran el algoritmo de conversión o el formato canónico =
   versión mayor (semver de la spec).

## Áreas abiertas
- Notario multi-réplica de producción (publicación de raíces).
- Adaptador SLH-DSA / ML-DSA (bibliotecas auditadas, nunca código propio).
- Calculador web (web/).
- Traducciones de la spec + i18n del formato Universal.

## Implementaciones independientes

Público explícito: **te invitamos a reimplementar el núcleo en otro
lenguaje** y demostrar conformancia ejecutando `vectors/` (ver
[docs/CONFORMANCE.md](docs/CONFORMANCE.md): formato, runners y categorías
obligatorias). Un archivo `vectors/` inmutable es todo lo que necesitas;
no leas el código de referencia (hazlo «gratis» solo después de tu propia
implementación verde). Abre tu PR con la salida de tus runners pegada en
la descripción y estilo de commit limpio (sin correos personales).

## Estilo
- Python >= 3.9, stdlib only en src/.
- Docstrings explicando *por qué*, comentarios explicando *qué*.
