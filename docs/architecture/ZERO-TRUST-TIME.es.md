# Infraestructura Temporal Verificable para Arquitecturas Zero Trust

Versión: 1.0.0 · Línea base: `v3.4.0` (`GUS v3.0.0`) · Licencia: CC-BY-4.0 ·
Mantenido por: verared contributors

[English](ZERO-TRUST-TIME.en.md) · **Español** — en caso de divergencia, prevalece el texto en inglés (EN > ES).

> **Alcance y frontera de honestidad.**
> *Gerarion Time* **complementa** a las arquitecturas Zero Trust; **no sustituye**
> el control de acceso, la autorización por operación, la autenticación de red,
> la custodia de claves en hardware (`TPM` / `HSM`) ni la seguridad del
> controlador o actuador.
> Los perfiles `Gerarion Lite`, `Gerarion Trusted` y `Gerarion Full` definidos a
> continuación son **perfiles conceptuales de despliegue y composición modular**
> sobre los nueve repositorios satélite existentes — **no** son productos nuevos
> ni repositorios adicionales. `gt-tslr` y `gt-gcerts` siguen en estado
> **`EXPERIMENTAL`** (solo especificación y andamiaje, sin implementación de
> referencia ni garantía operativa). Ver [`SECURITY.md`](../../SECURITY.md) y
> [`docs/spec/threat-model.md`](../spec/threat-model.md).

---

## 1. Principio Rector

> **Ningún evento se considera temporalmente confiable solo porque contiene una fecha; su procedencia, integridad, frescura, incertidumbre y autorización deben poder verificarse mediante política explícita.**

En los sistemas distribuidos convencionales, una marca temporal se trata como un
metadato pasivo: una cadena o un entero adjunto a una petición, registro o
comando que se acepta por su valor aparente. En un modelo Zero Trust —donde ni
la red ni el reloj del emisor se consideran implícitamente confiables— esa
suposición constituye una brecha estructural.

*Gerarion Time* replantea el tiempo como una **dimensión operativa verificable**
junto a la identidad, la integridad del mensaje y la frescura. En lugar de
colapsar todo en un único booleano de «timestamp válido», el verificador de
referencia (`gerarion.gst.v2.verify`, línea base `v3.4.0`) separa la
verificación en **tres niveles independientes** (`VerificationResult`):

| Nivel | Campo (`v3.4.0`) | Qué verifica | Qué **no** demuestra por sí solo |
|---|---|---|---|
| **Nivel 1 — Criptografía** | `result.crypto` | Canonicalización determinista RFC 8785 (JCS), separación de dominio `GUS3-GST-V2`, descriptor anti-downgrade y validez matemática de la firma híbrida **Ed25519 + ML-DSA**. | Si la clave firmante está autorizada o si el sobre fue reenviado (*replay*). |
| **Nivel 2 — Identidad y frescura** | `result.identity` | Autorización de la clave, ventana de vigencia y revocación en `KeyRegistry`, más verificación atómica anti-replay y secuencia monotónica en un `ReplayStore` transaccional (`SQLiteReplayStore`), ambos *fail-closed*. | Si el reloj físico del host firmante estaba sincronizado o era veraz. |
| **Nivel 3 — Procedencia temporal** | `result.temporal` | Estado de confianza del reloj (`VERIFIED`, `HOLDOVER`, `UNVERIFIED`, `REJECTED`) y cotas explícitas de incertidumbre aportadas por una lectura autenticada de `gt-gts` (`UNKNOWN` por defecto cuando se omite). | Resistencia física frente a interferencias GNSS/PTP/NTP o a un atacante con `root` en el host. |

`result.sealed` cubre los niveles 1 y 2. `result.anchored` y `result.overall_trusted`
exigen además `VERIFIED` y evidencia temporal independiente vinculada al sobre
exacto por el verificador del host. Las cotas dependen de esa política.

---

## 2. Matriz de Amenazas y Límites Reales (7 Vectores)

La siguiente tabla detalla qué aporta *Gerarion Time* frente a siete vectores
habituales de ataque temporal y probatorio, y dónde terminan explícitamente sus
garantías.

| # | Ataque | Qué aporta Gerarion | Límite explícito |
|---|---|---|---|
| 1 | **Replay de mensajes** | `gt-gst` (`GST v2`) + `ReplayStore` transaccional (`SQLiteReplayStore` en modo `WAL` + `BEGIN IMMEDIATE`) rechazan sobres duplicados y retrocesos de secuencia en modo *fail-closed*. | Depende de una persistencia, durabilidad y despliegue atómico correctos del `ReplayStore` entre réplicas. |
| 2 | **Manipulación de timestamps** | La firma híbrida **Ed25519 + ML-DSA** sobre RFC 8785 (JCS) liga la coordenada GUS canónica, `event_hash`, emisor, `kid` y `seq` en un único sobre con detección de alteraciones. | No prueba por sí sola que el reloj original del host emisor fuera verdadero en el momento de firmar. |
| 3 | **Retroceso del reloj** | La máquina de estados de `gt-gts` y las anclas persistentes anti-rollback sub-segundo `(instant, nanos)` detectan saltos hacia atrás y sacan el reloj de `VERIFIED`. | Depende de proteger el almacenamiento de las anclas y las fuentes temporales; un atacante con `root` sin protección en hardware puede borrar o alterar anclas locales. |
| 4 | **Suplantación de dispositivos / emisores** | `KeyRegistry` (`TrustedKeyRecord`) exige vínculo explícito emisor-clave, verificación en tiempo constante, ventanas de rotación histórica, expiración y revocación. | Una clave privada robada sigue siendo crítica hasta su revocación; las claves en software no sustituyen la custodia en hardware (`TPM` / `HSM`). |
| 5 | **Alteración de logs** | Los hashes SHA-256 por evento, las firmas `GST v2` y las raíces opcionales de notaría Merkle diaria hacen detectable sin conexión cualquier edición o borrado posterior al anclaje. | No impide que un productor comprometido borre o suprima eventos **antes** de firmarlos o anclarlos. |
| 6 | **Desincronización temporal** | `gt-gts` expone estados explícitos `HOLDOVER` y `UNVERIFIED` junto con incertidumbre declarada en lugar de degradarse silenciosamente a un reloj de sistema no verificado. | No impide interferencias físicas de radio o de red sobre fuentes GNSS, PTP o NTP. |
| 7 | **Falsificación de evidencia** | Los sobres `GST v2` y la verificación independiente sin conexión (`tools/verify_gus.py`, `gerarion.gst.v2.verify`) permiten a terceros validar integridad y procedencia sin confiar en un servidor único. | Depende de emisores y testigos/notarios confiables, y de una auditoría criptográfica externa independiente (pendiente antes de uso crítico en producción). |

---

## 3. Lenguaje Común en los 9 Satélites

Los nueve repositorios bajo `verared/gt-*` comparten un mismo modelo de
coordenadas congelado (`GUS v3.0.0`, `TCJ = TAI + 8.400 s`) y cubren
responsabilidades diferenciadas dentro de una pila temporal Zero Trust. Ver
[`SATELLITE-REPOS.es.md`](SATELLITE-REPOS.es.md) y
[`COMPATIBILITY.md`](../../COMPATIBILITY.md) para el contrato de dependencias.

| Satélite | Rol en una arquitectura temporal Zero Trust | Madurez (`v3.4.0`) |
|---|---|---|
| [`verared/gt-core`](https://github.com/verared/gt-core) | Núcleo entero determinista TCJ + GUS sin `malloc` (C11, Python, JS) para coordenadas homogéneas desde MCUs hasta servidores. | Estable / Verificado |
| [`verared/gt-gus`](https://github.com/verared/gt-gus) | Sintaxis canónica de 29/32 caracteres, reglas de normalización 1–7 y `quick_verify` para rechazar marcas malformadas en el borde. | Estable / Verificado |
| [`verared/gt-tcj`](https://github.com/verared/gt-tcj) | Escala atómica monotónica (`TCJ = TAI + 8.400 s`) y puente `TAI−UTC` versionado (`IERS-C-2026.1`) con aviso explícito de horizonte. | Estable / Verificado |
| [`verared/gt-calendar`](https://github.com/verared/gt-calendar) | Traducción determinista entre 10 calendarios (`AY`/`DY` + GUTI-1) para presentación humana y auditoría interregional sin ambigüedad. | Estable / Verificado |
| [`verared/gt-gts`](https://github.com/verared/gt-gts) | Máquina de estados de confianza de reloj (`VERIFIED`/`HOLDOVER`/`UNVERIFIED`/`REJECTED`) y anclas anti-rollback sub-segundo para decisiones de Nivel 3. | Núcleo estable · Roughtime **experimental** |
| [`verared/gt-gst`](https://github.com/verared/gt-gst) | Sobres híbridos `GST v2`, `KeyRegistry`, `ReplayStore` transaccional y notario Merkle diario opcional para Niveles 1–2 y auditoría offline. | Referencia estable · **auditoría externa y TPM/HSM pendientes** |
| [`verared/gt-interop`](https://github.com/verared/gt-interop) | Puentes estrictos en frontera (`RFC 3339`, `ISO 8601`, `Unix`) con vectores negativos compartidos, aislando formatos heredados en el perímetro. | Estable (`RFC 3339`/`ISO`/`Unix`) · `RFC 3161` **experimental** |
| [`verared/gt-tslr`](https://github.com/verared/gt-tslr) | Futuro contexto opcional de contraste físico/solar (*Tiempo Solar Local Real*). | **`EXPERIMENTAL`** — solo especificación y andamiaje; **no operativo** |
| [`verared/gt-gcerts`](https://github.com/verared/gt-gcerts) | Futura semántica de ventanas de validez de certificados sobre TCJ bajo estados de confianza de reloj. | **`EXPERIMENTAL`** — solo especificación y andamiaje; **no operativo** |

---

## 4. Perfiles Conceptuales de Adopción Gradual (No Nuevos Repositorios)

Los despliegues Zero Trust abarcan desde microcontroladores con recursos mínimos
hasta pasarelas de borde e infraestructuras críticas multi-entidad. En lugar de
exigir que todos los nodos ejecuten criptografía post-cuántica, *Gerarion Time*
define **tres perfiles conceptuales de despliegue** compuestos estrictamente a
partir de los satélites existentes. Son **guías de composición, no productos
nuevos ni repositorios adicionales**.

| Perfil | Composición (satélites y controles existentes) | Entorno objetivo | Garantías declaradas |
|---|---|---|---|
| **Gerarion Lite** | `gt-core` + `gt-gus` + `gt-tcj` | Dispositivos embebidos, MCUs y sensores *bare-metal* con recursos mínimos. | Representación canónica TCJ/GUS sin segundos intercalares y aritmética entera determinista sin `malloc` ni sobrecarga criptográfica (delega firma y anti-replay en la pasarela superior). |
| **Gerarion Trusted** | **Lite** + `gt-gts` + `gt-gst` (`KeyRegistry` + `ReplayStore` transaccional) | Pasarelas, servicios, APIs, backends CMS/auditoría y nodos de borde. | Evalúa validez criptográfica (`crypto`), autorización de clave y anti-replay atómico (`identity`) y estado explícito del reloj (`temporal`) antes de ejecutar o aceptar operaciones. |
| **Gerarion Full** | **Trusted** + notaría Merkle diaria + políticas de confianza multi-entidad + auditoría offline independiente + controles de frontera `gt-interop` + custodia en hardware (`TPM` / `HSM`) | Infraestructuras críticas, trazabilidad distribuida, OT/IoT industrial y flujos multi-agente. | Añade verificabilidad entre entidades, anclaje Merkle de registros, puentes perimetrales estrictos y protección de claves en hardware (requiere auditoría criptográfica externa e integración de custodia en hardware antes de uso crítico en producción). |

> **Regla de composición:** *La seguridad no exige que todos los dispositivos soporten todo; exige que cada dispositivo declare explícitamente qué perfil y garantías ofrece.*

Un sensor `Gerarion Lite` NO debe tratarse como criptográficamente autenticado
solo por emitir una cadena GUS válida; es la pasarela `Gerarion Trusted`
receptora la que aplica la frontera de confianza y registra explícitamente el
perfil de origen.

---

## 5. Escenario de Referencia y Protocolo de Validación Cuantitativa (Experimento A/B)

### 5.1 Escenario de referencia: pasarela industrial / IoT

Considérese una pasarela industrial de borde que media órdenes de actuación (por
ejemplo, *«abrir válvula V-14»*) entre un controlador remoto y un bus de campo:

1. **Compuerta sintáctica en el borde (`gt-gus`):** La coordenada GUS canónica
   de la orden se valida con `quick_verify`; cualquier cadena malformada o no
   canónica se descarta de inmediato.
2. **Verificación criptográfica y de identidad (`gt-gst` + `KeyRegistry` + `ReplayStore`):**
   Cinco minutos después llega un reenvío capturado de la misma orden «abrir
   válvula V-14». Aunque la firma sigue siendo matemáticamente válida
   (`crypto.valid == True`), el `SQLiteReplayStore` transaccional detecta el
   duplicado `(issuer, seq)` / digest del sobre y falla cerrado
   (`identity.replay_status == "REPLAY"`, `overall_trusted == False`). La
   apertura de la válvula queda bloqueada.
3. **Control de confianza y retroceso de reloj (`gt-gts`):** Si el reloj local de
   la pasarela sufrió un retroceso o perdió sincronización autenticada, `gt-gts`
   reporta `REJECTED`, `HOLDOVER` o `UNVERIFIED`, permitiendo que la política
   deniegue actuaciones de alto riesgo en lugar de confiar silenciosamente en el
   reloj del sistema.
4. **Preservación de evidencia:** El sobre reenviado rechazado, el resultado de
   verificación y el estado `gt-gts` de la pasarela se registran como evidencia
   del intento con detección de alteraciones en lugar de descartarse en silencio.

**Controles externos de Zero Trust que siguen siendo obligatorios:** *Gerarion
Time* **no** sustituye la autenticación mutua de red (mTLS/IPsec), la
autorización granular por operación (RBAC/ABAC que decide *si* un emisor puede
abrir V-14), la custodia de claves en hardware (`TPM`/`HSM`), la segmentación
física de red ni los enclavamientos de seguridad del propio PLC o actuador.

### 5.2 Benchmark adversarial comparativo (Protocolo A/B)

Para evaluar estas propiedades de forma cuantitativa —y no por mera afirmación—,
la hoja de ruta ([`ROADMAP.es.md`](../../ROADMAP.es.md)) recoge un **benchmark
adversarial comparativo A/B independiente** a desarrollar en un **futuro
repositorio externo**:

- **Sistemas bajo prueba:** Dos pasarelas de borde funcionalmente idénticas bajo
  la misma carga y esquema de órdenes:
  - **Línea base (A):** Validación temporal convencional sobre reloj de sistema
    (RFC 3339 / época Unix + ventana de tolerancia, sin `GST v2`, `KeyRegistry`,
    `ReplayStore` transaccional ni anclas anti-rollback de `gt-gts`).
  - **Tratamiento (B):** Perfil **Gerarion Trusted** (`gt-core` + `gt-gus` +
    `gt-gts` + `gt-gst` con `KeyRegistry` y `SQLiteReplayStore` en modo
    *fail-closed*).
- **Escenarios controlados de ataque y fallo:**
  1. Captura y **replay** de órdenes válidas (inmediato, diferido y en ráfagas
     concurrentes multihilo).
  2. **Manipulación de reloj** (salto hacia atrás, retroceso sub-segundo, deriva
     hacia adelante más allá de *holdover*).
  3. **Falsificación de eventos y abuso de claves** (alteración de payload o
     timestamp, clave desconocida, clave expirada/revocada, intento de
     *downgrade* algorítmico).
  4. **Reinicio malicioso / recuperación ante caída** (reinicio forzado del
     proceso para probar la persistencia de `ReplayStore` y de las anclas
     anti-rollback de `gt-gts`).
- **Métricas principales a publicar de forma reproducible:**
  - **Tasa de rechazo de operaciones fraudulentas** (por clase de ataque).
  - **Tasa de falsos positivos** sobre tráfico legítimo en operación nominal y
    degradada (`HOLDOVER`).
  - **Latencia de verificación extremo a extremo** (sobrecarga p50 / p95 / p99
    de verificación híbrida + chequeo transaccional de replay).
  - **Disponibilidad del servicio** durante degradación del reloj, *holdover* y
    recuperación.

---

## 6. Referencias Relacionadas

- [`SECURITY.md`](../../SECURITY.md) — Política de seguridad vigente, perfil normativo `GST v2` y divulgación responsable.
- [`docs/spec/threat-model.md`](../spec/threat-model.md) — Modelo de amenazas detallado (`v3.4.0`).
- [`docs/architecture/SATELLITE-REPOS.es.md`](SATELLITE-REPOS.es.md) — Modelo de exportación de satélites y grafo de dependencias.
- [`docs/guides/CMS-INTEGRATION.es.md`](../guides/CMS-INTEGRATION.es.md) — Patrón concreto de integración (`KeyRegistry` + `SQLiteReplayStore` + checklist `GEIACT-1`).
- [`ROADMAP.es.md`](../../ROADMAP.es.md) — Visión verificable y ejes abiertos de ingeniería.
