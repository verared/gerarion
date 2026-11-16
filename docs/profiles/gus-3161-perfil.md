# Perfil GUS-3161 — marcas GUS ancladas en RFC 3161 (TSA existentes)

> **Capa**: perfil de atestación · **Versión**: 3161-001 · **Estado**: normativo
> **EN normativo**: [`docs/en/profiles/gus-3161-profile.md`](../en/profiles/gus-3161-profile.md) — prevalece EN.
> **Código de referencia**: `src/gerarion/profiles_tsa.py` (subprocess `openssl`, stdlib puro)
> **Tests**: `tests/test_profiles_tsa.py` (TSA local efímera; sin red)

## 1. Propósito

Las TSA de RFC 3161 son la infraestructura de atestación ya desplegada:
toda PKI corporativa tiene una. Su límite es criptográfico: las
respuestas TSA usan RSA o ECDSA (firmas clásicas), y su unidad de tiempo
es el reloj UTC de pared.

GUS-3161 hace que GUS y RFC 3161 sean complementarios:

- **La TSA certifica EXISTENCIA**: los bytes sellados fueron presentados
  a la TSA no más tarde de su `genTime` (la TSA no dice nada sobre la
  veracidad de ningún instante declarado).
- **GUS certifica ORDEN y AUTORÍA**: la GST liga el instante canónico a
  una firma post-cuántica y a una cadena de notario.

Anclar un artefacto GUS en una TSA existente da a GUS un puente hacia la
infraestructura desplegada sin pedirle que confíe en ningún notario GUS,
y añade un segundo testigo independiente fuera del clúster: comprometer
solo a los notarios ya no basta para mover las cotas de existencia.

## 2. Reglas (MUST)

1. **Datos sellados**: la TSA aplica hash exactamente a los bytes del
   bundle `canonical_bytes(canon, instant)` de la GST (o a los bytes del
   artefacto anclado). El algoritmo MUST ser SHA-256 o superior.
2. **La TSA es testigo, no autoridad**: el perfil nunca deriva el
   instante GUS desde `genTime`. El genTime se registra como cota de
   existencia, convertido a instante GUS con el perfil **GUS-3339** para
   comparabilidad, y etiquetado como cota, no como verdad.
3. **Sidecar JSON** (`type: "gus3161-001"`): `gst_sha256`,
   `tsa_gen_time` (RFC 3339 Z), `tsa_gen_time_gus_instant`,
   `token_b64` (el TS_RESP completo en base64; autocontenido).
4. **Verificación offline**: el verificador MUST comprobar (a) la
   validez criptográfica del TS_RESP contra un trust root declarado
   (certificado TSA; `openssl ts -verify` en la referencia) y (b) que el
   digest sellado coincide con el digest del artefacto verificado. Sin
   (a) y (b), el sidecar NO PRUEBA NADA.
5. **Precisión del genTime**: las fracciones de segundo se truncan. Las
   carreras sub-segundo no son semántica GUS; el sidecar es una cota
   superior desde un testigo externo, no una lectura primaria.
6. **Los certificados TSA son datos, no confianza**: el verificador
   declara qué trust roots acepta. Una TSA desconocida produce "no
   verificable aquí", nunca "silenciosamente verdadero".

## 3. Qué garantiza el perfil y qué no

| Propiedad | Garantía |
|---|---|
| Los bytes sellados existían en el genTime | Sí, tras validar el trust root de la TSA |
| El instante declarado de la GST es verdadero | NO — la TSA solo lo acota: `gst.instant <= sidecar.tsa_gen_time_gus_instant` |
| El reloj de la TSA era honesto | NO — un testigo es tan honesto como su reloj; por eso existe la cadena de notarios |
| Reutilizar un token TSA viejo sobre bytes modificados | Detectable — la comprobación del digest (regla 4b) falla |

## 4. Conformancia

El perfil no añade constantes más allá de GUS-3339 y la definición del
bundle. Cláusula de conformancia: una implementación declara GUS-3161 si
(a) extrae el genTime de un TS_RESP real (el contenido dinámico se
construye localmente en el test e2e con una TSA efímera: ningún vector
porta valores de reloj), (b) verifica tokens offline y (c) reproduce el
sidecar JSON clave a clave a partir del mismo par (bundle, token).
