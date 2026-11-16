# Política de seguridad

## Alcance
- `src/gerarion/` — implementación de referencia del estándar GUS 2.0.
- `docs/spec/` — garantías declaradas (ver threat-model.md).

## Denunciar una vulnerabilidad
Reportes: abrir una *security advisory* en GitHub (Security > Advisories) o
contactar a los mantenedores de verared (github.com/verared). Respuesta objetivo: 7 días para
triage, 30 días para fix o mitigación documentada.

## Reglas del proyecto
1. Toda nueva propiedad de seguridad llega con su test (vectores).
2. La suite completa debe pasar antes de cualquier release: la spec y el
   código no pueden divergir.
3. Las claves firmantes jamás se versionan en este repositorio.
4. Toda afirmación de "post-cuántico" debe expresar sus premisas exactas
   (ver threat-model.md sección 3).
