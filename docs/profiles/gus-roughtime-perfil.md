# Perfil GUS-Roughtime — testigos externos ligados al campo anchor

> **Capa**: perfil de atestación · **Versión**: roughtime-001 · **Estado**: espejo ES (normativo: EN)
> **Documento normativo**: [`docs/en/profiles/gus-roughtime-profile.md`](../en/profiles/gus-roughtime-profile.md) — EN prevalece; en divergencia mandar EN.
> **Código de referencia**: `src/gerarion/profiles_roughtime.py` (Python puro, solo stdlib)
> **Tests**: `tests/test_profiles_roughtime.py` (sin red, sin servicio externo)
> **TODO-002**: parsear el wire-format UDP completo y el encadenamiento de shards del protocolo Roughtime queda fuera de este perfil; registrado en `docs/history/TODO-pendientes.md`.

## 1. Propósito

El notario GUS (k-de-n) acota la existencia desde DENTRO del clúster.
Un atacante que compromete todos los notarios podría reescribir solo
las cotas de existencia. Roughtime añade testigos INDEPENDIENTES del
clúster GUS: servidores que firman, con Ed25519, su respuesta a un
nonce elegido por quien sella. Comprometer los notarios ya no basta:
la cadena falsificada debe llevar también las firmas de cada testigo
externo.

Este perfil define el RECEIPT: la unidad firmada que un testigo (o un
cliente completo en su nombre) produce, verificable offline sin
dependencias. Cómo llegan esos datos por la red (protocolo Roughtime
UDP) es transporte y queda abierto como TODO-002.

## 2. Reglas (MUST)

1. **Bytes firmados** (secuencia exacta que firma el testigo):

   ```
   "GUS-ROUGH-TIME" \n nonce \n midpoint (RFC 3339 Z) \n radius (decimal) \n
   ```

2. **Receipt JSON** (`type: "gusroughtime-001"`): `midpoint_rfc3339`,
   `radius_s`, `pubkey_b64`, `signed_b64` (los bytes de la regla 1),
   `sig_b64` (Ed25519). Base64 estándar.
3. **El testigo es testigo, no autoridad**: el receipt da la ventana
   `[midpoint − radius, midpoint + radius]`, nunca la verdad de un
   instante declarado. El instante GUS NO se deriva del midpoint.
4. **Anti-replay por nonce**: el nonce es `SHA-256(bundle_bytes)` del
   artefacto sellado. Es un campo FIRMADO, así que un receipt antiguo
   no se puede reutilizar sobre bytes nuevos: recomputar el nonce sobre
   bytes modificados rompe la ligadura. El verificador DEBE rechazar un
   receipt cuyo nonce no se pueda casar con el artefacto que dice cubrir.
5. **Trust root de testigos**: el verificador declara qué claves
   públicas de testigo acepta. Un receipt de una clave fuera de esa
   lista es "no verificable aquí", nunca "silenciosamente verdadero".
6. **Coherencia**: con el instante GST `t`, el verificador DEBE
   rechazar el anchor si `t > midpoint + radius` (un testigo no pudo
   responder antes de que el artefacto existiera).
7. **Ed25519**: firmas según RFC 8032. El verificador de referencia es
   Python puro (solo stdlib, `profiles_roughtime.py`); es una
   implementación de REFERENCIA para conformancia y chequeo offline, no
   para firmar en producción. La ruta de clave pública está validada
   contra el vector TEST 2 del RFC 8032.

## 3. Qué garantiza el perfil y qué no

| Propiedad | Garantía |
|---|---|
| Los bytes sellados existieron hasta `midpoint + radius` | Sí, tras validar el trust root del testigo |
| Resistencia a replay de receipts antiguos | Sí — el nonce está firmado y ligado al digest del bundle |
| Un testigo independiente del clúster notarial GUS | Sí, si el verificador acepta varias claves |
| El instante GST declarado es verdadero | NO — el testigo solo lo acota desde fuera |
| El reloj del testigo era honesto | NO — mismos límites que GUS-3161; la independencia es lo que aporta Roughtime, la honestidad viene de tener varios testigos |
| Protección si el reloj del dispositivo está mal | NO — ver threat-model; GUS atestigua orden y existencia, no el reloj de pared actual |

## 4. Ubicación en la GST

El campo `anchor` de la GST lleva exactamente el resultado de
`bind_anchor`:

```json
{"type": "roughtime", "midpoint_rfc3339": "...", "radius_s": 3,
 "pubkey_b64": "...", "signed_b64": "...", "sig_b64": "..."}
```

Los anchors componen: una GST puede llevar un sidecar GUS-3161, un
anchor `roughtime` y la cadena notarial k-de-n a la vez. El verificador
libremente puede exigir 1+ de cada; el perfil define la unidad, no la
política de quórum.
