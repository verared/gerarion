# Gobernanza — GUS (Gerarion Universal Standard)

Versión: 2.0 — estado: RATIFICADA (v2.0). Mantenedor: proyecto verared (futura fundación)
(github.com/verared). Creador original: Gerardo Loyola (github.com/geroiloyola).

> **Idioma.** La referencia normativa de gobernanza es la versión inglesa
> (`docs/en/GOVERNANCE.md`). Este documento es su espejo informativo; en
> caso de divergencia prevalece el inglés (EN > ES). La terminología
> normativa (GTS, GST, notario, vector set) es la misma en ambos. Un estándar sin gobernanza explícita es una asamblea de una persona: esto responde la pregunta "¿quién manda aquí?" antes de
> que alguien la pregunte desde fuera.

---

## 1. Principio rector

GUS es un estándar técnica-verificable. La legitimidad no proviene de una
organización, ni de un autor, ni de una comunidad de afinidad: proviene de
las **propiedades verificables del artefacto**. Un cambio al kernel GUS no
"gana" porque lo apruebe un comité: gana porque siguiendo los vectores
normativos publicados (`vectors/gus-normative-002.json`) todas las
implementaciones siguen produciendo el mismo output, bitwise, desde tres
bases de código (Python, JavaScript, C) escritas de forma independiente.

Cualquier propuesta que comprometa esta propiedad verificable es inválida
por definición, sin importar cuántos votos reciba.

## 2. Qué es "kernel" (y es inmutable sin Looking Period)

El **kernel GUS** es el conjunto exacto de constantes y reglas que definen
el output del calendario y de los instantes:

- `ORIGIN_JDN` (JDN 1719313)
- `SOLAR_DELTA_UD` (1 242 190 µd/día) y `SOLAR_THRESHOLD_UD` (7 000 000 µd)
- La regla Gran Tempalum (años GT: 5, 11, 16, 22, 28, 33, 39, 45;
  posición y longitud del Tempalum)
- El orden de meses (12×30 + Tempalum) y el patrón Nuvid (7 días
  invariantes, calculado sobre el índice de día, no sobre lo que declara
  el documento)
- El formato canónico GTS y sus reglas de normalización 1–7
- La semántica de instantes (escala continua sin segundos intercalares
  análoga a TAI[1], con el día GUS rodando a medianoche UTC — spec §9) y la cota de oscilación solar del ancla (|Δ| < 7 días; la
  ventana concreta de fechas de inicio es una medición observada y
  desplazable con los milenios, no una propiedad del kernel)
- Los códigos de error `GERO_*` y el ABNF del formato

Lo que **no** es kernel (y es cambiable por mayoría de mantenidores):
documentos de contexto informativos (la documentación histórica y cultural
complementaria vive en `docs/papers/`, no normativa), herramientas auxiliares
(`tools/`), la fachada web
(`web/index.html`, `web/app.js`, `web/style.css`), infraestructura CI,
empaquetado, y textos informativos.

## 3. Los cuatro mecanismos de decisión

### 3.1. Kernel: Looking Period de 90 días

Toda modificación al kernel (los 6 ítems de §2) sigue el mismo ciclo
formalizado en esta gobernanza:

1. **Propuesta pública** (PR + issue etiquetado `kernel-change`): debe
   citar el/los vectores afectados y la justificación técnica. Sin
   justificación técnica el PR no entra a revisión.
2. **Looking Period — 90 días corridos**: la propuesta queda visible,
   abierta, sin merge, durante al menos 90 días corridos. Durante ese
   periodo, cualquier implementación (las tres de referencia y
   terceras) debe poder re-ejecutar los test suites y sus propios tests
   contra la propuesta. El movimiento "break glass" — ver §3.4 — es el
   único camino más corto.
3. **Decisión**: la propuesta se aprueba si al cierre del periodo:
   (a) ninguna implementación conformante diverge reproduciblemente de
   la propuesta, y (b) hay al menos **dos de tres mantenidores**
   informados favorablemente (§3.5). Si no hay acuerdo, la propuesta
   queda postergada al siguiente ciclo de 90 días (no se descarta).
4. **Vectores**: un cambio de kernel aprobado implica un nuevo vector
   set versionado (`gus-normative-002.json`, etc.) generado con
   `tools/generate_vectors.py` y un commit del CHANGELOG. El vector set
   anterior queda archivado (fuera de la rama principal) para trazabilidad.

**Implicancia práctica**: si al leer esto, alguien llega a "GUS ya
funciona, ¿por qué opinar?" — la respuesta es: 90 días y pruebas
reproducibles, o nada. La ventana corta (§3.4) existe para incidentes de
seguridad, no para desacuerdos de diseño.

### 3.2. Eratas

Un error factual (fecha, constante, valor) en un documento normativo se
corrige vía `docs/errata-vN.M.md` también cuando no afecta el output del
kernel. Si afecta el output, es una breaking change de kernel (§3.1) y
obliga a nueva versión del vector set. Las erratas se enumeran con
prefijo E-01, E-02, etc., con reproducción mínima y corrección.

El archivo `docs/errata-v1.2.md` histórico queda como registro de las
seis erratas E-01..E-06 aplicadas al documento histórico v1.2.

### 3.3. Certificación de forks (Fork Certification)

**Cualquier fork** del estándar (divergencia de kernel, juego de
constantes distinto, variante regional) es **bienvenido, público y
certificable** — pero para que un fork pueda llamarse "GUS"
(sigla reservada — ver §5), debe:

1. Publicar un **certificado de fork** (`forks/<slug>/FORK.yaml`) con:
   - `gus_base_version`: la versión de GUS de la que se bifurca
   - `kernel_diff`: enumeración de las constantes/reglas que difieren
   - `vector_set_fingerprint`: el fingerprint SHA-256 del vector set del
     fork (Python y terceras implementaciones deben pasar su propio
     vector set generado con `tools/generate_vectors.py`)
   - `maintainers`: quién mantiene el fork (identidades verificables,
     ver §5)
   - `epoch`: el instante (timestamp GUS) de la bifurcación, firmado con
     el notario/clúster del fork o de GUS (para que la divergencia sea
     timestamp-anclada, no "trabajos en silencio")
2. Publicar la URL del fork en el registro de forks de este repo
   (`forks/README.md`), con enlace a FORK.yaml y al repositorio del fork.
3. Exponer un endpoint de **health-check** equivalente al de las réplicas
   del notario: el fork firma publicaciones con su propia clave, por lo
   que un cliente GUS puede distinguir de inmediato una firma de fork de
   una firma de GUS (diferentes `pub`, tablas de réplicas distintas).

La certificación **no** es una aprobación de contenido: es una declaración
pública de diferencia, para que nadie confunde un fork con el estándar.
Un fork que se hace pasar por GUS sin certificado es ellos el problema, no
el estándar — pero la gobernanza lo documenta.

### 3.4. Proceso de seguridad (break glass)

**Si existe una vulnerabilidad real que amenaza la propiedad
no-falsificable del tiempo (GST, notario, trust root):**

- **Anunciar en el canal de seguridad** no en issues públicos. El canal
  es `SECURITY.md` de este repo. Publicarlo en issues antes de lograrse
  una mitigación es responsabilidad del que reporta.
- Los mantenidores tienen autoridad para **aplicar el fix SIN Looking
  Period** y publicar una release de seguridad inmediatamente (versión
  patch, a.m. x.y.Z) con nota de seguridad adjunta, siempre que:
  - el fix pasa la prueba de los vectores existentes: ninguna
    implementación conformante cambia de output salvo en los casos
    declarados como vulnerables,
  - se escriba una errata `docs/errata-vN.M.md` explicando el incidente,
  - el CHANGELOG registre el vector set no afectado (mismos hashes).
- La exposición de la clave de ceremonia del trust root (§5) es el caso
  más severo: obliga a re-ceremonia y a re-publicar el trust root
  (`tools/trust_root.py`), con revocación de la clave anterior en
  el propio trust root (campo `previous_trust_root`), no borrado.

### 3.5. Mantenedores

| Rol | Responsabilidad | Cantidad |
|---|---|---|
| Mantenedor de kernel | Aprueba cambios de kernel (§3.1) tras Looking Period | 2 de 3 |
| Mantenedor de implementación | Mantiene Python, JavaScript o C conforme al vector set | 1 por lenguaje |
| Mantenedor de notario | Operación del clúster, ceremonia de claves, rotación (docs/notary-runbook.md) | 1-3 réplicas |
| Mantenedor de publicación | PyPI/npm/Pages/SBOM y empaquetado | 1 |

(Ajuste según madurez del proyecto; una persona puede tener dos roles,
pero **nunca** debe tener "mantenedor de kernel" + "mantenedor de
implementación" sobre la misma base de código que vota el vector set que
esa misma implementación debe conformar — el patrón fox en el gallinero.)

Un tercer y último grupo — no listado arriba — es el **público general**:
cualquiera puede proponer, revisar, presentar vectores, reportar errata,
ejecutar el fuzzing diferencial contra el repo y abrir issues. La
soberanía técnica no es votar; es **poder reproducir**.

## 4. Flujo del cambio técnico de punta a punta

```
issue etiquetado kernel-change
   -> PR con justificación técnica y vectores afectados
   -> Looking Period 90 días (o expediente de seguridad §3.4)
   -> re-ejecución de tests en Python + JS + C contra vectores
   -> 2/3 mantenidores dan visto bueno
   -> merge + nuevo vector set versionado + CHANGELOG
   -> release (PyPI + npm + tag + Pages re-deploy)
```

Conformancia de una implementación de tercero:

```
publicar el vector set (JSON) -> consumir el JSON -> PASS == conformante
```

Si una implementación responde "estoy conforme" sin mencionar la versión
del vector set que pasó, no está declarando nada.

## 5. Política de claves y autoridad criptográfica

- **Clave de ceremonia** del trust root: SLH-DSA-SHA2-128F (FIPS 205),
  generada en ceremonia con RNG del SO, **la clave privada se borra de
  toda computadora conectada** después de firmar (grabada en dos canales
  físicos separados, similar a L2 de state — ver runbook §4).
- **Rotación de claves**: anual o ante cualquier sospecha de
  compromiso. Rotación = nueva ceremonia + nuevo trust root que nombra al
  `previous_trust_root` (revocación en cadena, no borrado).
- **Claves de réplica**: una por réplica del clúster notarial, rotación
  trimestral (configurable en `deploy/`).
- **Veto criptográfico**: cualquier persona puede verificar el trust
  root (`tools/trust_root.py verify`) contra la clave de ceremonia que
  ella misma haya grabado fuera del canal digital. Si hay dos trust
  roots con la misma ceremonia pero réplicas distintas: es un **split
  brain** — se declara como emergencia de gobernanza (§3.4 mitigación) y se resuelve por peso del notario (el log encadenado más
  largo verificado diario gana; ver runbook §5).
- **La sigla "GUS" es reservada**: sólo puede llevarla el kernel
 (ver forks en §3.3).
  Cualquier fork que quiera diferenciarse públicamente usa su propio
  nombre, sin compartir marca ni claves del clúster.

## 6. Conflicto de interés

- Un integrante no puede estar simultáneamente en dos roles cuya decisión
  sobre la misma prueba sea la misma persona (§3.5).
- Cualquier contribución de una entidad comercial debe declarar si la
  propuesta afecta su producto. Declararlo no descalifica; **no afectar
  si lo declara** sí descalifica.
- Los vectores normativos, los tests y el draft IETF se deciden por
  reproducibilidad, no por afinidad comercial: un PR de una empresa
  rival con vectores correctos gana a un PR interno con vectores
  incorrectos.

## 7. Erratas de gobernanza

Este documento también puede ser erratado — pero con Looking Period de
90 días, idéntico al del kernel. La producción de conflictos entre
gobernanza y técnica se resuelve a favor de la reproducibilidad (§1).

---

## 8. Marca "Gerarion"

**Estado del registro**: NO VERIFICADO — según el estado actual de este
repositorio, "Gerarion" no consta como marca registrada en ninguna
oficina de marcas, y esta gobernanza no declara registro alguno.

**Política de uso** (mientras no exista un registro):

- El nombre "Gerarion", el acrónimo "GUS" y el nombre del estándar se
  usan libremente para implementaciones conformes (paso del vector set
  normativo) y para comunicación honesta sobre el estándar.
- Se permite señalar conformidad ("implementación conforme a
  gus-normative-002"); se prohibirá cualquier uso que declare conformidad
  falsa o patrocinio inexistente, si en el futuro se formaliza registro.
- Los forks conformes pueden mantener el nombre añadiendo su
  identificador (p. ej. "Gerarion — fork <nombre>"); los forks no
  conformes no pueden acreditar conformidad con GUS.

Si en el futuro se registra la marca, esta sección se actualiza primero
(errata de gobernanza, §7) y el registro se declara aquí, no en otra parte.

## 9. Glosario aquí no: apuntadores

- Propiedades y regex del formato: `docs/spec/gus-2.1.0.md` (ES) /
  `docs/en/gus-2.1.0.md` (EN normativo).
- Modelo de amenazas: `docs/spec/threat-model.md` (ES) / `docs/en/threat-model.md`.
- Runbook del notario: `docs/notary-runbook.md`.
- Vectores y cláusula de conformancia: `vectors/README.md`.
- Erratas históricas: `docs/errata-v1.2.md`.

---

[1] Semántica de "análoga a TAI": la escala de instantes es lineal en
etiquetas (sin tabla TAI−UTC) con el día GUS rodando a medianoche UTC — texto normativo
en spec §9 y sección «Escala de tiempo» del README. La propuesta de
frontera alternativa (instante sobre TAI con tabla explícita) queda como
DECISIÓN DEL AUTOR en docs/decisions/D-001-frontera-utc-tai.md.
