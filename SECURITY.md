# Política de seguridad — verared/gerarion

> **AVISO DE BETA (leer primero).** Implementación DE REFERENCIA del
> estándar GUS 2.1.0. NO está auditado criptográficamente. El esquema
> hash-only de referencia, la raíz de confianza y el notario NO deben
> usarse para decisiones de seguridad reales. Úsalo solo para pruebas,
> evaluación y desarrollo de la especificación.

## Reportar una vulnerabilidad

- Canal: **Private vulnerability reporting** de GitHub (botón "Report a
  vulnerability" en Security → Advisories). NO abras un issue público.
- Plazos objetivo desde el reporte: **7 días** acuse de recibo,
  **30 días** evaluación y decisión, **90 días**
  fix + CVE (si procede) o justificación de ignorar.
- Coordinamos la divulgación con el reportante; crédito bajo el nombre que
  indique en el reporte.

## Versiones con soporte de seguridad

| Versión | Soporte |
|---|---|
| 2.5.0b1 (rama `beta-hardening`) | sí (beta) |
| <= 2.4.0 | solo actualizaciones de disponibilidad crítica; beta sin garantías |

## Qué SÍ es seguridad de producción hoy

Nada. La distribución recomendada es por GitHub Releases con
`SHA256SUMS.txt` para integridad de descarga; la existencia de la firma
hash-only y del notario es de REFERENCIA EDUCATIVA (semántica de la spec).
Producción requiere SLH-DSA (FIPS 205) con biblioteca auditada y un
despliegue de notario diseñado para ello (nevera el threat-model).
