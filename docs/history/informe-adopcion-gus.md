# Informe técnico: por qué adoptar el tiempo GUS en cómputo

| Campo | Valor |
|---|---|
| Documento | Informe de adopción — GUS 2.0 (Gerarion Universal Standard) |
| Audiencia | CTO, arquitectura y seguridad de plataformas, equipos de infraestructura |
| Estado | Propuesta técnica (v1.0) |
| Base verificable | Este repositorio: spec, 83 tests Python, 18 vectores JS, 12 checks E2E (Playwright), errores de corpus documentados E-01..E-07 |
| Alcance del juicio | Ingeniería de sistemas y seguridad. El calendario se presenta como infraestructura, no como cosmología |

---

## 1. Resumen ejecutivo

Los ordenadores no corren "el tiempo": corren una pila de compromisos
históricos (calendario gregoriano + UTC + zonas horarias + NTP/GNSS)
cada uno de los cuales ha provocado incidentes documentados y costosos.
El paso común entre esos incidentes no es la mala suerte: son cuatro
defectos estructurales que el estándar actual lleva incorporados.

GUS 2.0 es una propuesta de infraestructura de tiempo diseñada para
eliminar esos cuatro defectos por construcción, no por parche:

1. **Escala continua y regular**: 12 meses x 30 días + Tempalum (4/11
   días); todo año es múltiplo exacto de la semana (364/371 días).
   Sin segundos intercalares, sin meses de 28-31 días, sin excepciones.
2. **Conteo propio e independiente**: el instante continuo es un entero
   (`día x 86400 + h x 3600 + m x 60 + s`) desde un origen fijo
   (1 Keuphero del año 0 DY = JDN 1.719.313). Ninguna decisión civil
   (DST, reformas, leap seconds) puede moverlo.
3. **Tiempo verificable, no consultado**: el instante puede llevar firma
   (hash-only de referencia o SLH-DSA FIPS 205) y anclarse en un notario
   Merkle diario multi-réplica (quórum k-de-n). Falsificar el pasado
   exige reescribir todas las réplicas o romper SHA-256.
4. **Post-cuántico por diseño**: la firma hash-only permanece segura en
   el modelo Grover (~2^128 de margen); el adaptador SLH-DSA está
   integrado con despacho por campo `alg`.

**Recomendación:** coexistencia por capas — mantener gregoriano
como presentación de cara al usuario y registrar el tiempo canónico GUS
como capa de verdad en logs, firmas, contratos y sincronización crítica.
No requiere big-bang: el formato es un sobre sobre el entero continuo.

---

## 2. Método y honestidad de este informe

- Cada incidente citado en la sección 3 es público y verificable
  (fecha, afectados, mecanismo). El catálogo completo con fuentes está
  en el README del repositorio.
- Cada propiedad de GUS afirmada aquí tiene test o vector que la ejecuta:
  la tabla de la sección 6 enlaza qué prueba la sostiene.
- Uno de los defectos del corpus original fue detectado por nosotros y
  queda documentado como errata con su test (E-01..E-07). Ese proceso —
  "la spec se puede equivocar, y se ha demostrado que sabemos detectarlo" —
  es parte del argumento de madurez.

---

## 3. Diagnóstico: el tiempo civil como pasivo de ingeniería

### 3.1 El defecto de fondo: hoy el tiempo se consulta, no se verifica

El reloj de un servidor es una creencia alimentada por la red: NTP
sin autenticar, GNSS satelital o cadena de administradores. Bajo ese
modelo, "la hora" no tiene garantía criptográfica y, sin embargo,
los protocolos críticos (Kerberos, TLS, certificados, contratos on-chain)
construyen la seguridad sobre un valor que el adversario puede
influir con coste cero.

### 3.2 Catálogo condensado de incidentes

| Defecto | Incidente real | Afectados |
|---|---|---|
| Segundo intercalar | 30 jun 2012: kernel Linux en livelock (Reddit, Mozilla, LinkedIn, Cloudera caídas). 1 ene 2017: Cloudflare → 502 masivos | Millones de servidores, cada leap second futuro |
| NTP sin auth / crypto rota | CVE-2013-5211 (monlist → DDoS ~400 Gbps); CVE-2014-9295 (claves débiles en ntpd) | Hosts y routers globales |
| GNSS spoofing | Jun 2011, Mar Negro: 20+ barcos con GPS desplazado; jamming afecta a redes sincronizadas por satélite | Naval, aviación, 5G |
| Ventanas de skew | Kerberos: ±5 min por diseño; cookies y tiquets re-juzgados dentro de la ventana | Infraestructura corporativa |
| Irregularidad de calendario | Meses 28-31, bisiestos observables, reformas: bugs de borde cada año | Finanzas, planificación |
| Zonas horarias y DST | Bugs de tzdata y librerías (Java 8 pre-1900); decretos políticos cambian semántica sin aviso | Logs, facturación, jobs |
| Segundos desde epoch como contrato | `block.timestamp` (SWC-116): el minero mueve el reloj segundos para alterar suerte/vencimientos | DeFi, contratos on-chain |
| Techo de 32 bits | Y2038: desborde de `time_t` el 19 de enero de 2038 | Miles de millones de dispositivos legacy |

### 3.3 Las cuatro causas raíz

1. **Irregularidad estructural** — el calendario civil no es una escala
   métrica; obliga a la lógica de casos borde perpetua.
2. **Gobernabilidad arbitraria** — la semántica del tiempo puede cambiar
   por decreto (DST, leap seconds) sin que el software tenga voto.
3. **Confianza en infraestructura mudable** — la hora percibida depende
   de tercero consultado (NTP, GNSS), cada uno con su propia superficie de
   ataque.
4. **No-verificabilidad** — después del hecho, nadie puede demostrar
   criptográficamente qué hora era. El tiempo no deja evidencia.

GUS 2.0 responde punto por punto: regularidad total; regla única
determinista con offset civil opcional y visible; tiempo firmable por el
mismo actor que lo declara; y evidencia Merkle encadenada que convierte
"la era ayer" en una propiedad demostrable.

---

## 4. Diseño GUS 2.0: propiedades relevantes para cómputo

### 4.1 Aritmética exacta, clase de bugs eliminada

- Entrada gregoriana → índice de día → fecha GUS: enteros puros; nunca
  `float`. El acumulador del Gran Tempalum opera en microdías enteros
  (Δ = 1.242.190 µd, umbral 7.000.000 µd): determinista en cualquier
  orden de ejecución, replicable bit a bit entre implementaciones.
- El porte JavaScript del núcleo (`web/gerarion.mjs`) ejecuta la misma
  matriz de 18 vectores normativos que la suite Python: la web y el CLI
  no pueden divergir sin que el vector lo delate.

### 4.2 Instante continuo, sin segundos intercalares

`instante = día * 86400 + h * 3600 + m * 60 + s`. No existe el instante
que la infraestructura no sabe representar. La comparación de tiempos es
una resta de enteros; la ordenación es total; los rangos son exactos.

### 4.3 Semana invariante

El día de la semana es `day_index mod 7` — calculado prevalece sobre el
declarado — donde todo año empieza en Soludyia y cada año común cierra
52 semanas exactas. Consecuencia operativa: los planificadores y jobs
semanales no requieren tablas de bisiesto ni ajustes manuales de fechas.

### 4.4 Tiempo como valor firmable

- **GST (instante firmado):** firma hash-only de referencia (SHA-256 +
  Winternitz + árbol Merkle) o SLH-DSA (FIPS 205) vía adaptador con
  despacho por `alg`. La firma cubre el instante canónico.
- **Notario Merkle diario:** raíz del día por réplica, encadenada al
  día anterior; publicación verificable standalone (`verify_bundle`).
  Falsificar una declaración histórica de tiempo exige:
  - romper SHA-256 (preimagen: 2^256 de trabajo serial, 2^128 cuántico
    Grover), o
  - reescribir el log de todas las réplicas que superan el quórum k-de-n
    y toda la cadena posterior — visiblemente.
- Las réplicas con derivación incorrecta quedan automáticamente fuera
  del quórum (`bad_derivation`/`divergent`): un GNSS spoofed o un
  administrador con prisa no produce tiempo válido, produce réplica
  excluida y visible.

### 4.5 Presentación y orden separadas

`TCJ±O` (offset) y el ciclo SC/LC son campos de presentación. La zona
horaria no puede alterar el instante canónico — es lo contrario de la
semántica actual, donde la zona puede cambiar qué día "es".

---

## 5. Comparativa de régimen de tiempo

| Criterio | Gregoriano/UTC + NTP/GNSS (status quo) | GUS 2.0 |
|---|---|---|
| Continuidad | Se rompe con leap seconds (por decreto futuro indeterminado) | Continuo por definición |
| Longitud de año | 365/366, meses 28-31 | 364/371, meses 30 siempre |
| Múltiplo de semana | No (fracciones de 52.16 semanas) | Siempre exacto (52/53) |
| Semana invariante | No | Sí (day_index mod 7 calculado) |
| Techo de representación | Y2038 (32-bit) en legacy | Entero sin techo (BigInt) |
| Fuente de verdad | Red consultada (NTP, GNSS) | Aritmética propia + firma opcional |
| Verificabilidad post-hoc | Ninguna | Merkle + firma; costo de falsificación 2^256 |
| Post-cuántico | Depende de migraciones externas (TLS) | Hash-only nativo + SLH-DSA integrado |
| Reacción a la gobernanza civil | Cambia semántica | Inmune (offset opcional y visible) |
| Contratos/logs | Timestamp consultado, mutable por operadores | Anclable a day_root publicado |
| Curva de adopción | Ya instalado | Coexistencia por capas (sección 7) |

---

## 6. Evidencia: de cada propiedad a su prueba

| Propiedad afirmada en este informe | Test / vector |
|---|---|
| Origen exacto (JDN 1.719.313 = 21-03-(-5)) | `test_origin_jdn`, `test_normative_jdn_vector` |
| Regularidad (todo año múltiplo de 7; inicio en Soludyia) | `test_all_year_lengths_multiple_of_7`, `test_every_year_starts_on_soludyia` |
| Cota de drift del acumulador entero (500 años) | `test_drift_bound_sawtooth` |
| Formato canónico, normalización, errores GERO_* | `test_format.py` (14 tests, reglas 1-7) |
| Firma hash-only: alterar 1 bit falla | `test_crypto.py` (12 tests) |
| SLH-DSA FIPS 205 integrado | `test_adapters.py` (6 tests) |
| Notario k-de-n: réplicas divergentes excluidas | `test_notary_cluster.py` (7 tests) |
| Independencia del gregoriano (E-07) | `test_errata_e07_origin_independence` |
| Port web idéntico al núcleo | `web/tests.mjs` (18 vectores) + E2E Playwright (12 checks) |

Reproducir: `PYTHONPATH=src python3 -m pytest tests/ -q` ·
`node web/tests.mjs` · `python3 e2e_web_test.py` (con servidor estático).

---

## 7. Estrategia de adopción: por capas, sin big-bang

| Fase | Aplicación | Riesgo | Requisito |
|---|---|---|---|
| 0 | **Doble sello**: logs y documentos llevan GUS junto al UTC actual | Casi nulo | Formato de una línea (`2031DY-03-08-T-09:30:00-SC-TCJ+0`) |
| 1 | **Archivos/listas de eventos fijos**: planificación semanal, jobs, SLA | Bajo | Semana invariante elimina lógica de borde |
| 2 | **Firma de tiempo operación**: GST hash-only sobre eventos críticos | Bajo-medió | Claves del operador; notario opcional |
| 3 | **Notario multi-réplica** (k-de-n ≥ 3 réplicas, ≥ 2 operadores) | Medio | Descriptor de despliegue; rotación de claves |
| 4 | **SLH-DSA FIPS 205** para máxima garantía post-cuántica | Medio | Coste de firma (~4.5 s en hardware "común" en 128s; 0.22 s en 128f) — apto para firmas de cierre diario, no por-tick |
| 5 | Anclaje on-chain / contratos (`day_root` previamente publicado) | Alto (acuerdo externo) | Requiere contraparte |

La migración no exige "reemplazar el tiempo": exige añadir una capa de
verdad firme que el régimen actual no puede dar. El gregoriano sigue
existiendo como vista derivada — ya se genera exactamente con F-01/F-02.

---

## 8. Riesgos y contras (declarados)

1. **Ecosistema**: es un calendario y formato nuevo; el aprendizaje es
   real. Mitigación: coexistencia de fase 0 y port web con self-test
   (cero riesgo de divergencia silenciosa).
2. **Drift con respecto al día civil**: el año GUS es 364/371 días y el
   solar ~365.2422; el inicio de año oscila dentro de la cota |Δ| < 7
   días (demostrado, no observacional). Si un dominio exige anclaje al
   equinoccio exacto, existe el mecanismo de forks de época.
3. **La firma 128s es lenta por tick**: es deliberado (horizonte
   post-cuántico); el diseño esperado es por-lote o por-día. Para
   firmas en caliente, 128f (0.22s).
4. **Adopción orgánica**: un estándar de tiempo vale tanto como sus
   réplicas; sin réplicas del notario, la garantía retroactiva es solo
   la firma del emisor. El riesgo es institucional, no matemático.
5. **Sin promesas místicas**: este informe no afirma que GUS haga el
   tiempo "absoluto" (eso no existe en cómputo); lo hace **regular,
   continuo y demostrable después del hecho**, que son las tres
   propiedades que hoy no tiene ningún régimen operativo.

---

## 9. Conclusión y recomendación

El tiempo actual en cómputo es un contrato implícito con la red y con el
decreto político; cada vencimiento de esa promesa ha sido un incidente
público. GUS 2.0 propone lo mínimo que un estándar serio debería
garantizar: un reloj que nadie pueda mover, una escala sin excepciones
y una prueba de lo que fue "el ayer".

**Recomendación formal:**
1. Adoptar la fase 0 inmediatamente (doble sello GUS en logs y documentos
   nuevos).
2. Integrar GST hash-only en el pipeline de firma operado.
3. Desplegar notario de 3 réplicas antes de confiar en cualquier
   verificación retroactiva.
4. Evaluar SLH-DSA para firmas de cierre diario en entornos con horizonte
   post-cuántico.

La implementación de referencia (este repositorio) está lista y verificada;
los vectores y los tests son la definición operativa de cada afirmación
hecha en este informe.

---

## Anexo A — Parámetros exactos (copy-safe)

```
JDN de origen        = 1.719.313      (1 Keuphero, año 0 DY; conversión: 21-03-(-5) gregoriano proleptico)
Año                  = 12 x 30 días + Tempalum (mes 00): 4 días (común) / 11 (Gran Tempalum)
Año común / GT       = 364 / 371 días (52 / 53 semanas exactas)
Semana               = S L M A T V B  (Soludyia ... Sabatyeh); weekday = day_index mod 7
Acumulador solar     = r(n) = r(n-1) + 1.242.190 µd, umbral 7.000.000 µd (enteros exactos)
GT                   = 5, 11, 16, 22, 28, 33, 39, 45 ... (recurrencia, no tabla)
Instante             = día * 86400 + h*3600 + m*60 + s   (sin segundos intercalares)
Formato              = AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O]
Firma                = SHA-256 + Winternitz + Merkle (hash-only) / SLH-DSA-SHA2-128s|128f (FIPS 205)
Notario              = árbol Merkle diario, encadenado, quórum k-de-n, réplicas divergentes excluidas
Alfabeto del día     = día de semana calculado prevalece sobre el declarado
Eras                 = DY (después del origen) / AY (antes, años no negativos en la escala)
```

## Anexo B — Inventario del repositorio

```
src/gerarion/calendar.py       núcleo (enteros exactos, F-01..F-07)
src/gerarion/format.py         formato canónico + normalización
src/gerarion/gts.py            GST: create/verify con despacho de firmador
src/gerarion/hashots.py        firma hash-only de referencia
src/gerarion/adapters.py       SLH-DSA (FIPS 205) integrado
src/gerarion/notary.py         árbol Merkle diario
src/gerarion/notary_cluster.py notario multi-réplica (k-de-n) + verify_bundle
src/gerarion/cli.py            CLI gero
web/                            port del núcleo + calculador con self-test
docs/spec/                      especificación normativa y modelo de amenazas
docs/errata-v1.2.md             E-01..E-07 con tests
docs/papers/                  papers históricos complementarios (no normativos)
tests/  (83) web/tests.mjs (18) e2e_web_test.py (12 checks)
```
