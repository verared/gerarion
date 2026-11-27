# Gerarion Time

**Infraestructura temporal abierta, modular, *offline-first* y verificable: un calendario regular, una escala atómica continua y evidencia criptográfica temporal híbrida post-cuántica.**

[![CI](https://github.com/verared/gerarion/actions/workflows/ci.yml/badge.svg)](https://github.com/verared/gerarion/actions/workflows/ci.yml)
[![CodeQL](https://github.com/verared/gerarion/actions/workflows/codeql.yml/badge.svg)](https://github.com/verared/gerarion/actions/workflows/codeql.yml)
![Licencia: MIT OR Apache-2.0](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue)
![Versión v3.3.0](https://img.shields.io/badge/version-v3.3.0-green)
![REUSE 3.3](https://img.shields.io/badge/REUSE-3.3%20compliant-brightgreen)

[English](README.md) · **Español** — en caso de divergencia, prevalece el texto en inglés (EN > ES).

---

## 2. Estado del proyecto

Release **`v3.3.0`** sobre la especificación congelada **`GUS v3.0.0`**.

| Eje | Estado | Alcance |
|---|---|---|
| **1. Especificación y aritmética** (`GUS v3.0.0` + 10 calendarios) | **Congelada y verificada** | Aritmética entera (`TCJ = TAI + 8.400 s`), verificada bit a bit entre Python, JavaScript y C11 contra `vectors/*.json`. |
| **2. Implementaciones de referencia** (`v3.3.0`) | **Estables y probadas en CI** | `gt-core`, `gt-gus`, `gt-tcj`, `gt-calendar`, `gt-gts` (núcleo), `gt-gst` (referencia), `gt-interop` (RFC 3339 / ISO 8601 / Unix). |
| **3. Aseguramiento criptográfico de producción** | **Pendiente** | `gt-gst` aún no cuenta con auditoría criptográfica externa independiente ni custodia de claves en `TPM` / `HSM`. |

> **Qué NO usar todavía en decisiones críticas de producción:**
> `gt-gst` y el notario Merkle (sin auditoría externa ni custodia en hardware),
> y los perfiles **experimentales** `gt-tslr`, `gt-gcerts`, Roughtime (`gt-gts`)
> y RFC 3161 (`gt-interop`). `gt-tslr` y `gt-gcerts` son solo especificación y
> andamiaje (sin implementación de referencia). Ver [SECURITY.md](SECURITY.md) y
> [ROADMAP.es.md](ROADMAP.es.md).

## 3. Qué es y qué no es

**Es:**

- Una infraestructura temporal modular, determinista y *offline-first*: calendario regular 12×30, escala continua `TCJ = TAI + 8.400 s`, traducción entre 10 calendarios y sobres temporales híbridos (Ed25519 + ML-DSA).
- Una forma de convertir el tiempo en una dimensión verificable (procedencia, integridad, frescura, incertidumbre) para arquitecturas Zero Trust ([arquitectura temporal Zero Trust](docs/architecture/ZERO-TRUST-TIME.es.md)).
- Tres implementaciones independientes (C11, Python, JavaScript) ligadas a un único conjunto de vectores normativos CC0.
- Dividida en nueve repositorios satélite adoptables de forma independiente.

**No es:**

- Un sustituto de UTC, TAI, NTP, PTP ni del reloj del sistema operativo; los complementa.
- Un sustituto del control de acceso Zero Trust, la autorización por operación, la custodia de claves en hardware (`TPM` / `HSM`) ni la seguridad del controlador; los complementa.
- Una blockchain ni un certificado de reloj físico: sin una lectura autenticada de `gt-gts`, la hora dentro de un sobre es solo una afirmación del firmante.

## 4. Probar en línea

**<https://verared.github.io/gerarion/>** — el traductor de fechas corre íntegramente en el navegador (diez calendarios, enlaces compartibles, reloj GUS en vivo, calendario mensual y calculadora de distancias). Sin peticiones a servidor, cookies ni cuentas, y sigue funcionando sin conexión tras cargar.

## 5. Ejemplo mínimo de uso (1 minuto)

### Integra `gt-core` + `gt-gst` en 1 minuto (Guía rápida CMS / API)

Requiere `cryptography>=47` (extra `gst`). Guía completa: [docs/guides/CMS-INTEGRATION.es.md](docs/guides/CMS-INTEGRATION.es.md).

```python
import hashlib
from gerarion.core import format as fmt
from gerarion.gst import HybridSigner, v2

# 1. Firmante híbrido (Ed25519 + ML-DSA-65), registro de confianza y ReplayStore SQLite
signer = HybridSigner(seed_classical=bytes(range(32)), seed_pqc=bytes(range(32, 64)))
registry = v2.KeyRegistry()
registry.register_signer(issuer="cms.example.org", kid="cms-2026-k1", signer=signer)
replay_store = v2.SQLiteReplayStore(":memory:")  # en producción: "/var/lib/cms/gst_replay.sqlite3"

# 2. Sellar un evento de negocio sobre una coordenada GUS canónica
event_bytes = b'{"action":"post.publish","object_id":"art-42","version":1}'
event_hash = "sha256:" + hashlib.sha256(event_bytes).hexdigest()
envelope = v2.create(
    fmt.parse("2031DY-03-08-T-09:30:00-SC-TCJ+0"),
    signer,
    event_hash=event_hash,
    issuer="cms.example.org",
    kid="cms-2026-k1",
    seq=1,
)

# 3. Verificar en 3 niveles independientes (criptografía, identidad/replay, aseguramiento temporal)
res = v2.verify(envelope, expected_event_hash=event_hash, trust_store=registry, replay_store=replay_store)
assert res.crypto.valid is True
assert res.identity.valid is True and res.identity.key_status == "ACTIVE"
assert res.identity.replay_status == "OK"
assert res.temporal.clock_state == "UNKNOWN"  # "VERIFIED" solo con una lectura autenticada de gt-gts
assert res.sealed and not res.overall_trusted  # sin ancla temporal verificada
print("crypto   :", res.crypto.valid, res.crypto.algorithm)
print("identity :", res.identity.valid, res.identity.key_status, res.identity.replay_status)
print("temporal :", res.temporal.clock_state)
print("overall_trusted:", res.overall_trusted)

# 4. El mismo sobre reenviado es rechazado (anti-replay atómico)
again = v2.verify(envelope, expected_event_hash=event_hash, trust_store=registry, replay_store=replay_store)
print("replay   :", again.identity.replay_status, again.overall_trusted)
```

Salida esperada:

```text
crypto   : True HYBRID-ED25519-ML-DSA-65
identity : True ACTIVE OK
temporal : UNKNOWN
overall_trusted: False
replay   : REPLAY False
```

## 6. Instalación

**Ecosistema completo** (sin PyPI, sin npm, sin registros externos):

```bash
# Python >= 3.9 (núcleo solo stdlib; el extra `gst` añade cryptography>=47)
pip install "gerarion[gst] @ git+https://github.com/verared/gerarion.git@v3.3.0"

# C11 (sin dependencias, núcleo sin malloc) — construye las bibliotecas, CLI y suite de conformancia
make -C impl-c            # archivos pkg-config: gerarion.pc, gerarion-core.pc, gerarion-clock.pc, gerarion-calendars.pc

# JavaScript / ESM (cero dependencias): importa web/gerarion.mjs o el tarball npm de la GitHub Release
```

**Solo los satélites que necesites** — cada repositorio satélite conserva las rutas relativas del monorepo, por lo que se combinan copiando sus árboles:

```bash
git clone --branch v3.3.0 --depth 1 https://github.com/verared/gt-core.git
git clone --branch v3.3.0 --depth 1 https://github.com/verared/gt-gst.git
```

**Verificar un satélite** (desde un checkout de este repositorio):

```bash
python3 tools/export_module.py --verify-existing /ruta/a/gt-core
# con autenticidad de firma separada, cuando el satélite incluya EXPORT-MANIFEST.json.sig:
python3 tools/export_module.py --verify-existing /ruta/a/gt-core --trusted-pub-key /ruta/a/release-pub.pem
```

Sin `--trusted-pub-key`, la autenticidad se reporta como `SKIPPED`: solo se comprobó integridad. Los satélites publicados en `v3.3.0` aún no incluyen `.sig` (la firma automatizada en CI se sigue en [ROADMAP.es.md](ROADMAP.es.md)).

| # | Garantía de distribución | Mecanismo |
|---|---|---|
| 1 | Integridad SHA-256 | Mapa `files` de `EXPORT-MANIFEST.json` |
| 2 | Procedencia declarada | `source_repo`, `source_tag`, `source_commit` |
| 3 | Autenticidad de publicación | Firma Ed25519 separada `EXPORT-MANIFEST.json.sig` (`--trusted-pub-key`) |
| 4 | Reproducibilidad | Re-exportación bit a bit desde el mismo commit |
| 5 | Conformidad funcional | Vectores normativos + pruebas cruzadas de satélites en C11, Python y JS |

Cada GitHub Release adjunta wheel, sdist, tarball JS, bibliotecas C y `SHA256SUMS.txt` (`sha256sum -c SHA256SUMS.txt`). Detalles: [COMPATIBILITY.md](COMPATIBILITY.md).

## 7. Capas del ecosistema y repositorios satélite

Matriz de versiones y contrato de dependencias: [COMPATIBILITY.md](COMPATIBILITY.md). Brújula técnica (sin fechas ni promesas): [ROADMAP.es.md](ROADMAP.es.md) · [ROADMAP.md](ROADMAP.md).

| Satélite | Responsabilidad | Madurez (`v3.3.0`) |
|---|---|---|
| [`gt-core`](https://github.com/verared/gt-core) | Núcleo TCJ + GUS: C11 sin `malloc`, Python, JS | Estable |
| [`gt-gus`](https://github.com/verared/gt-gus) | Sintaxis canónica de 29/32 caracteres, `quick_verify` | Estable |
| [`gt-tcj`](https://github.com/verared/gt-tcj) | `TCJ = TAI + 8.400 s`, puente TAI−UTC versionado (`IERS-C-2026.1`) | Estable |
| [`gt-calendar`](https://github.com/verared/gt-calendar) | Calendario `AY`/`DY` + traducción entre 10 sistemas | Estable |
| [`gt-gts`](https://github.com/verared/gt-gts) | Máquina de estados de confianza de reloj, anclas anti-rollback | Núcleo estable · Roughtime **experimental** |
| [`gt-gst`](https://github.com/verared/gt-gst) | Sobres `GST v2`, `KeyRegistry`, `ReplayStore`, notario Merkle | Referencia estable · **auditoría externa pendiente** |
| [`gt-interop`](https://github.com/verared/gt-interop) | Puentes RFC 3339 / ISO 8601 / Unix | Estable · RFC 3161 **experimental** |
| [`gt-tslr`](https://github.com/verared/gt-tslr) | Perfil Tiempo Solar Local Real | **Experimental** (spec + andamiaje) |
| [`gt-gcerts`](https://github.com/verared/gt-gcerts) | Perfiles de validez temporal de certificados | **Experimental** (spec + andamiaje) |

## 8. Conformidad y pruebas

Los vectores normativos en [`vectors/`](vectors/README.md) (CC0) son la única fuente de verdad de conformidad: `gus-normative-003.json`, `gus-quickverify-001.json`, `gus-regression-001.json`, `gus-3339-*.json` (positivos y negativos) y `guti-calendars-001.json` (63.850 casos calendáricos).

```bash
# C11: conformancia contra todos los vectores + auditoría de estrés ASan/UBSan (6,5M+ comprobaciones)
make -C impl-c conformance
make -C impl-c audit

# Python (añade `pip install -e .[dev,pqc]` para las pruebas GST v2)
PYTHONPATH=src python3 -m pytest tests/

# JavaScript: los seis corredores
node web/test/tests.mjs
node web/test/conformance.mjs
node web/test/profiles-conformance.mjs
node web/test/regression-conformance.mjs
node web/test/calendars.test.mjs
node tests/atlas.test.mjs

# Satélites: exportar, verificar y ejecutar integración de satélites ensamblados (C11 + Python + JS)
python3 tools/export_module.py --all --out /tmp/satellites --verify
PYTHONPATH=src python3 -m pytest tests/test_export_module.py tests/test_satellite_integration.py

# Licencias
python3 -m reuse lint
```

**Validar una implementación independiente:** lee la cláusula ejecutable en [docs/CONFORMANCE.md](docs/CONFORMANCE.md), carga los vectores JSON desde tu lenguaje y compara cada campo. Cualquier divergencia sobre un vector normativo es un defecto de tu implementación; los vectores negativos deben ser rechazados.

## 9. Seguridad

- Perfil normativo `GST v2`: firma híbrida **Ed25519 + ML-DSA** sobre **RFC 8785 (JCS)**, dominio `GUS3-GST-V2` y descriptor anti-downgrade dentro de los bytes firmados. `WOTS+` y la API `GST v1` son legado (`src/gerarion/deprecated/hashots.py`).
- `gerarion.gst.v2.verify` exige el `expected_event_hash` calculado externamente. `sealed` indica firmas, vínculo con el evento y política del emisor válidos; `anchored` y `overall_trusted` exigen además un reloj `VERIFIED` y un callback de política del host que valide evidencia temporal independiente vinculada al sobre exacto. Una lectura de reloj no es por sí sola un ancla.
- Los integradores deben suministrar un `KeyRegistry` y un `ReplayStore` transaccional (ambos *fail-closed*).
- Límites conocidos: siguen pendientes la auditoría criptográfica externa independiente y la custodia de claves en `TPM` / `HSM`; un atacante con `root` en el host firmante no está mitigado.

Lee [SECURITY.md](SECURITY.md) (incluyendo divulgación responsable) y el [modelo de amenazas](docs/spec/threat-model.md).

## 10. Documentación y especificaciones

| Tema | Ubicación |
|---|---|
| Especificaciones por dominio | [`docs/specs/`](docs/specs/GUS.es.md): [TCJ](docs/specs/TCJ.es.md) · [GUS](docs/specs/GUS.es.md) · [CALENDAR](docs/specs/CALENDAR.es.md) · [GTS](docs/specs/GTS.es.md) · [GST](docs/specs/GST.es.md) · [INTEROP](docs/specs/INTEROP.es.md) · [TSLR](docs/specs/TSLR.es.md) · [GCERTS](docs/specs/GCERTS.es.md) |
| Edición normativa consolidada | [docs/spec/gus-3.0.0.md](docs/spec/gus-3.0.0.md) |
| Guía de integración (CMS / API externo, checklist `GEIACT-1`) | [docs/guides/CMS-INTEGRATION.es.md](docs/guides/CMS-INTEGRATION.es.md) |
| Arquitectura de satélites | [docs/architecture/SATELLITE-REPOS.es.md](docs/architecture/SATELLITE-REPOS.es.md) |
| Arquitectura temporal Zero Trust | [docs/architecture/ZERO-TRUST-TIME.es.md](docs/architecture/ZERO-TRUST-TIME.es.md) |
| Contrato de versiones | [COMPATIBILITY.md](COMPATIBILITY.md) |
| Hoja de ruta | [ROADMAP.es.md](ROADMAP.es.md) · [ROADMAP.md](ROADMAP.md) |
| Modelo de amenazas / política de seguridad | [docs/spec/threat-model.md](docs/spec/threat-model.md) · [SECURITY.md](SECURITY.md) |

**Precedencia normativa:** cada especificación existe en español e inglés; en caso de divergencia prevalece la **versión inglesa (EN > ES)**.

## 11. Trabajos relacionados

Gerarion complementa —y no compite con— los estándares temporales existentes:

- **UTC / TAI:** `TCJ = TAI + 8.400 s` es un desplazamiento matemático sobre la escala atómica; el puente TAI−UTC está versionado y señala extrapolación tras su horizonte de vigencia.
- **ISO 8601 / RFC 3339:** tratados como formatos de entrada/salida mediante `gt-interop`; nunca sustituyen a la coordenada GUS.
- **NTP / NTS / PTP / Roughtime:** la sincronización física sigue en ellos; `gt-gts` clasifica lecturas (`VERIFIED`, `HOLDOVER`, `UNVERIFIED`, `REJECTED`) y detecta retrocesos. El perfil Roughtime es experimental.
- **RFC 3161 (TSA):** una autoridad externa de sellado de tiempo puede contrafirmar un sobre canónico (perfil experimental).
- **ICU / calendarios civiles:** el motor de 10 calendarios es aritmética entera determinista, independiente de ICU, con rangos y tolerancias documentados.
- **Precedentes de diseño calendárico:** los calendarios egipcio y republicano francés (12×30), Symmetry454, Hanke-Henry y Pax. Como 364 y 371 son múltiplos de 7, el Tempalum añade semanas completas y nunca días fuera del ciclo semanal.

## 12. Contribuir, gobernanza y licencia

- **Fuente de verdad única:** `verared/gerarion` es el único lugar donde se edita código; los nueve satélites `verared/gt-*` se generan desde un commit etiquetado y nunca deben editarse a mano ([arquitectura](docs/architecture/SATELLITE-REPOS.es.md)).
- [CONTRIBUTING.md](CONTRIBUTING.md) · [GOVERNANCE.md](GOVERNANCE.md) · [SECURITY.md](SECURITY.md).
- **Licencias:** código `MIT OR Apache-2.0`; documentación `CC-BY-4.0`; vectores de prueba `CC0-1.0`; fuentes `OFL-1.1`. El repositorio cumple **REUSE 3.3** (`python3 -m reuse lint`). Ver [LICENSING.md](LICENSING.md), [NOTICE](NOTICE) y [sbom.cdx.json](sbom.cdx.json).

## 13. Cómo citar

```bibtex
@software{gerarion_time_2026,
  author  = {{verared} and Loyola, Gerardo},
  title   = {Gerarion Time: Gerarion Universal Standard (GUS 3.0.0) reference suite},
  year    = {2026},
  version = {3.3.0},
  url     = {https://github.com/verared/gerarion},
  license = {MIT OR Apache-2.0}
}
```

Metadatos legibles por máquina: [CITATION.cff](CITATION.cff).
