# Guía de Integración CMS y API (`gt-core` + `gt-gst` @ `v3.3.0`)

- **Línea base normativa:** `GUS v3.0.0` / suite `v3.3.0`
- **Audiencia:** Desarrolladores que integren *Gerarion Time* en plataformas CMS externas (p. ej. Portaless, WordPress, APIs headless) o pipelines de auditoría de eventos sin clonar el monorepo `verared/gerarion`.
- **Versión normativa en inglés:** [`CMS-INTEGRATION.en.md`](CMS-INTEGRATION.en.md) (EN > ES)

---

## 1. Instalación Autónoma (Consumiendo Solo Satélites)

Un CMS o servicio API externo nunca necesita clonar `verared/gerarion`. Combina
los árboles `src/` de **`verared/gt-core`** y **`verared/gt-gst`** (ambos
fijados al tag `v3.3.0` y verificados contra su `EXPORT-MANIFEST.json`), más
`cryptography>=47` para ML-DSA (FIPS 204) + Ed25519 (RFC 8032):

```bash
mkdir -p vendor/gerarion-satellites
git clone --branch v3.3.0 --depth 1 https://github.com/verared/gt-core.git /tmp/gt-core
git clone --branch v3.3.0 --depth 1 https://github.com/verared/gt-gst.git /tmp/gt-gst
cp -R /tmp/gt-core/src/* /tmp/gt-gst/src/* vendor/gerarion-satellites/
python3 -m pip install "cryptography>=47"
export PYTHONPATH="$PWD/vendor/gerarion-satellites"
```

Como `gt-core` y `gt-gst` conservan las rutas relativas bajo `src/gerarion/`,
Python 3.9+ carga `gerarion.core` y `gerarion.gst` como un paquete de espacio
de nombres PEP 420 limpio, sin configuración adicional.

---

## 2. Esquema Canónico de Evento (`gerarion-cms-event/1`)

Antes de crear un sobre `GST v2`, canonicaliza el evento de negocio del CMS con
`gerarion.gst.jcs.dumps_bytes(event)` para que `event_hash` vincule el
contenido exacto, la cadena causal, el actor y el contexto temporal:

```json
{
  "schema": "gerarion-cms-event/1",
  "tenant": "portaless-main",
  "actor": "user:editor-17",
  "action": "post.publish",
  "object_id": "post:2026-11-launch",
  "object_version": 3,
  "content_hash": "sha256:4f8b42c22dd3729b519ba6f68d2da7cc5b2d606d05daed5ad5128cc03e6c6358",
  "previous_event_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
  "event_time": "2031DY-03-08-T-09:30:00-SC-TCJ+0",
  "recorded_at": "2031DY-03-08-T-09:30:00-SC-TCJ+0",
  "signed_at": "2031DY-03-08-T-09:30:00-SC-TCJ+0",
  "clock_state": "UNKNOWN"
}
```

### Separación Obligatoria de Campos Temporales
- **`event_time`:** Instante en que ocurrió el evento de dominio según la aplicación o el productor original.
- **`recorded_at`:** Instante en que la base de datos o capa de persistencia del CMS registró la entrada.
- **`signed_at` (`ts` en `GST v2`):** Instante en que el `HybridSigner` selló el sobre `GST v2`.
- **`clock_state`:** Estado explícito de confianza de `gt-gts` (`VERIFIED`, `HOLDOVER`, `UNVERIFIED`, `REJECTED`), o `"UNKNOWN"` cuando se opera sobre el reloj del SO sin una fuente `gt-gts` autenticada. **Jamás declares `"VERIFIED"` si no se evaluó una lectura real autenticada por `gt-gts`.**

---

## 3. Integración de Extremo a Extremo: `KeyRegistry`, `SQLiteReplayStore`, Rotación y Revocación

```python
import hashlib
from gerarion.core import format as fmt
from gerarion.gst import HybridSigner, jcs, v2

# 1. Registro de confianza: vincula (issuer, kid) con claves públicas autorizadas y vigencia
signer_2026 = HybridSigner(seed_classical=bytes(range(32)), seed_pqc=bytes(range(32, 64)))
registry = v2.KeyRegistry()
registry.register_signer(
    issuer="cms.portaless.org",
    kid="cms-2026-q4",
    signer=signer_2026,
    valid_from="2031DY-01-01-S-00:00:00-LC-TCJ+0",
    valid_until="2031DY-12-30-L-23:59:59-LC-TCJ+0",
    scopes=("cms.events",),
)

# 2. Almacén transaccional multi-worker anti-replay y monotónico (SQLite WAL + BEGIN IMMEDIATE)
replay_store = v2.SQLiteReplayStore("/tmp/cms_gst_replay.sqlite3")

# 3. Canonicalizar el evento del CMS con RFC 8785 (JCS) y calcular event_hash
cms_event = {
    "schema": "gerarion-cms-event/1",
    "tenant": "portaless-main",
    "actor": "user:editor-17",
    "action": "post.publish",
    "object_id": "post:42",
    "object_version": 1,
    "content_hash": "sha256:" + hashlib.sha256(b"<h1>Hola</h1>").hexdigest(),
    "previous_event_hash": "sha256:" + "00" * 32,
    "event_time": "2031DY-03-08-T-09:30:00-SC-TCJ+0",
    "recorded_at": "2031DY-03-08-T-09:30:00-SC-TCJ+0",
    "signed_at": "2031DY-03-08-T-09:30:00-SC-TCJ+0",
    "clock_state": "UNKNOWN",
}
event_hash = "sha256:" + hashlib.sha256(jcs.dumps_bytes(cms_event)).hexdigest()

# 4. Emitir sobre GST v2
envelope = v2.create(
    fmt.parse(cms_event["signed_at"]),
    signer_2026,
    event_hash=event_hash,
    issuer="cms.portaless.org",
    kid="cms-2026-q4",
    seq=1,
)

# 5. Verificación en 3 niveles (fail-closed)
result = v2.verify(
    envelope,
    trust_store=registry,
    replay_store=replay_store,
    required_scope="cms.events",
)
assert result.crypto.valid is True
assert result.identity.valid is True and result.identity.key_status == "ACTIVE"
assert result.identity.replay_status == "OK"
assert result.temporal.clock_state == "UNKNOWN"
assert result.overall_trusted is True
```

### Rotación de Claves, Revocación y Copias de Seguridad
- **Rotación de claves:** Al rotar hacia `cms-2027-q1`, conserva `cms-2026-q4` en `KeyRegistry` con su ventana cerrada `valid_until`. Los eventos históricos firmados durante `2031DY` siguen verificando con `result.identity.key_status == "HISTORICAL"` (`HISTORICAL_VALID`) y `result.overall_trusted == True`, mientras que cualquier evento nuevo firmado con `cms-2026-q4` tras `valid_until` se rechaza con `KEY_EXPIRED`.
- **Revocación de emergencia:** Define `revoked_at` (instante TCJ o sello GUS) en el `TrustedKeyRecord` comprometido. Los eventos anteriores a `revoked_at` siguen siendo auditables como `HISTORICAL`, y cualquier evento en o después de `revoked_at` se rechaza con `KEY_REVOKED`.
- **Copias de seguridad sin rollback silencioso:** `SQLiteReplayStore` opera en modo `WAL` con `synchronous=FULL` y `BEGIN IMMEDIATE`. Nunca restaures una instantánea antigua de la base SQLite de replay para un `kid` activo (restaurar un `last_seq` anterior reabriría una ventana de replay). Si una recuperación ante desastres exige restaurar desde backup, rota inmediatamente a un `kid` nuevo al recuperar el servicio.

---

## 4. Checklist de Prueba de Aceptación Externa (`GEIACT-1`)

Al crear el repositorio externo del CMS, ejecuta los siguientes **8 experimentos + 3 inyecciones deliberadas de fallo** para certificar la integración:

### Los 8 Experimentos Funcionales y de Seguridad
1. **E1 — Ensamblado exclusivo desde satélites:** Instalar únicamente desde `verared/gt-core` + `verared/gt-gst` (`v3.3.0`), verificando `EXPORT-MANIFEST.json` con `--verify-existing` antes de arrancar el CMS.
2. **E2 — Hash determinista de evento:** Canonicalizar un payload `gerarion-cms-event/1` con `jcs.dumps_bytes` y confirmar `event_hash` idéntico tras reinicios de workers.
3. **E3 — Verificación en 3 niveles:** Emitir un sobre `GST v2` y comprobar `result.crypto.valid == True`, `result.identity.valid == True`, `result.identity.key_status == "ACTIVE"`, `result.temporal.clock_state == "UNKNOWN"` y `result.overall_trusted == True`.
4. **E4 — Cadena causal de hashes:** Encadenar 100 eventos consecutivos del CMS (`previous_event_hash -> event_hash`) con `seq = 1..100` estrictamente creciente y verificar toda la cadena offline.
5. **E5 — Concurrencia multi-worker:** Lanzar 16 hilos/workers simultáneos intentando verificar/ingerir el mismo sobre firmado contra un `SQLiteReplayStore` compartido; confirmar **1 aceptado (`OK`)** y **15 rechazados (`REPLAY`)**.
6. **E6 — Preservación tras rotación de claves:** Registrar `k2` tras el `valid_until` de `k1`; confirmar que los eventos antiguos de `k1` validan como `HISTORICAL` y los nuevos de `k2` como `ACTIVE`.
7. **E7 — Corte por revocación de clave:** Fijar `revoked_at` sobre `k1`; confirmar que los eventos previos a `revoked_at` validan como `HISTORICAL` y los posteriores fallan con `KEY_REVOKED`.
8. **E8 — Propagación de reloj autenticado (`gt-gts` opcional):** Pasar un `ClockReading(state=ClockState.VERIFIED, ...)` a `v2.verify(..., clock_reading=reading)` y confirmar `result.temporal.clock_state == "VERIFIED"`.

### Las 3 Inyecciones Deliberadas de Fallo (Deben Fallar en Modo *Fail-Closed*)
1. **F1 — Suplantación con clave autofirmada (`KEY_MISMATCH`):** Un atacante firma un sobre `GST v2` matemáticamente válido con su propio `HybridSigner` declarando `issuer="cms.portaless.org"` y `kid="cms-2026-q4"`. El Nivel 1 (`crypto.valid`) es `True`, pero el Nivel 2 (`identity.valid`) **DEBE** ser `False` con `key_status == "MISMATCH"` (`KEY_MISMATCH`) y `overall_trusted == False`.
2. **F2 — Omisión de almacén anti-replay (`REPLAY_UNCHECKED`):** Llamar a `v2.verify(envelope, trust_store=registry, replay_store=None)` sin `allow_unchecked_replay=True` **DEBE** fijar `identity.replay_checked == False`, `identity.replay_status == "SKIPPED"`, `identity.valid == False` y `overall_trusted == False`.
3. **F3 — Corrupción del archivo SQLite de replay (`CORRUPT_STATE`):** Sobrescribir la cabecera del archivo SQLite con bytes arbitrarios **DEBE** poner a `SQLiteReplayStore` en modo *fail-closed*, rechazando todo sobre posterior en lugar de reiniciar `seq` a cero.
