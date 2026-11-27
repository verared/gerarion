# Security Policy / Política de seguridad — verared/gerarion

🇬🇧 English first · 🇪🇸 Español más abajo ([ir a la versión en español](#política-de-seguridad-es)).
In case of divergence, the English text prevails (EN > ES).

---

## Security Policy (EN)

### Supported versions

| Version | Status |
|---|---|
| Suite `v3.4.0` on frozen specification `GUS v3.0.0` (release target) | **Supported** (security fixes) |
| `v3.2.x` / `v3.3.x` | Critical fixes only; upgrade to `v3.4.0` when released |
| `<= v3.1.x` | Unsupported |

The nine satellite repositories (`verared/gt-*`) are generated from a tagged
commit of this repository (see [COMPATIBILITY.md](COMPATIBILITY.md)); report
vulnerabilities here, never in the generated copies.

### Normative cryptographic profile (`GST v2`)

- **Signature:** hybrid **Ed25519 + ML-DSA** over **RFC 8785 (JCS)** canonical
  bytes, with domain separation `GUS3-GST-V2` and the algorithm/key
  descriptor *inside* the signed bytes (structural **anti-downgrade**:
  removing or downgrading either branch invalidates the envelope).
- **Legacy only:** `WOTS+` (`src/gerarion/deprecated/hashots.py`) and the
  `GST v1` API (`gerarion.gst.create` / `verify`, `GtsDocument`) are
  deprecated, emit `DeprecationWarning`, and are outside the normative
  profile.

### Mandatory trust requirements for integrators

A mathematically valid envelope is **not** a trusted envelope. Integrators
**MUST** pass both of the following to `gerarion.gst.v2.verify`:

1. a **`KeyRegistry`** binding `(issuer, kid)` to the authorized public keys
   (constant-time comparison via `hmac.compare_digest`; validity window,
   rotation and revocation), and
2. an atomic, transactional **`ReplayStore`** (`SQLiteReplayStore`, or an
   equivalent atomic store; `ReplayGuard` is a single-process reference).

Both operate **fail-closed**: with `trust_store=None` the issuer is reported
untrusted (`key_status="UNCHECKED"`); with `replay_store=None` the identity
level is invalid unless the integrator explicitly opts in with
`allow_unchecked_replay=True` (and `replay_checked` stays `False` in the
report). A corrupted replay store rejects everything instead of resetting
`seq`.

### The three verification levels (`gerarion.gst.v2.VerificationResult`)

| Level | Field | What it establishes |
|---|---|---|
| 1 | `crypto` | Mathematical validity: JCS canonicalization, `event_hash`, anti-downgrade descriptor, dual Ed25519 + ML-DSA signatures. |
| 2 | `identity` | Key authorization for `(issuer, kid)` at the signed instant (active / historical / expired / revoked / mismatch) and transactional anti-replay / anti-rollback. |
| 3 | `temporal` | Provenance and quality of the clock (`gt-gts`): `VERIFIED`, `HOLDOVER`, `UNVERIFIED`, `REJECTED`, or `UNKNOWN` when no authenticated reading is supplied. |

> **`sealed` covers levels 1 and 2.** `anchored` and `overall_trusted` additionally
> require a `VERIFIED` reading and independent temporal evidence bound to the
> exact envelope and accepted by the host's verification policy.

### Known limits (honest status)

- **No independent third-party cryptographic audit** of `gt-gst` or the
  Merkle notary has been performed yet.
- **No hardware key custody (`TPM` / `HSM`)** is integrated yet; an attacker
  with `root` on the signing host can sign arbitrary events with its keys.
- `gt-tslr`, `gt-gcerts`, the Roughtime profile and the RFC 3161 profile are
  **EXPERIMENTAL**.

Until both items above are closed, `gt-gst` **must not** be used for
critical production security decisions. Distribution integrity is provided by
`SHA256SUMS.txt` and `EXPORT-MANIFEST.json` (+ optional detached
`EXPORT-MANIFEST.json.sig`, see [COMPATIBILITY.md](COMPATIBILITY.md)).
Threat analysis: [docs/en/threat-model.md](docs/en/threat-model.md).

### Reporting a vulnerability (responsible disclosure)

- Channel: GitHub **Private vulnerability reporting** (Security → Advisories →
  *Report a vulnerability*). Do **not** open a public issue.
- Target timeline from report: **7 days** acknowledgement, **30 days**
  assessment and decision, **90 days** fix + CVE (if applicable) or a
  justification for declining.
- Disclosure is coordinated with the reporter; credit under the name the
  reporter indicates.

---

## Política de seguridad (ES)

### Versiones con soporte

| Versión | Estado |
|---|---|
| Suite `v3.4.0` sobre la especificación congelada `GUS v3.0.0` (release objetivo) | **Con soporte** (correcciones de seguridad) |
| `v3.2.x` / `v3.3.x` | Solo correcciones críticas; actualizar a `v3.4.0` cuando se publique |
| `<= v3.1.x` | Sin soporte |

Los nueve repositorios satélite (`verared/gt-*`) se generan desde un commit
etiquetado de este repositorio (ver [COMPATIBILITY.md](COMPATIBILITY.md));
reporta las vulnerabilidades aquí, nunca en las copias generadas.

### Perfil criptográfico normativo (`GST v2`)

- **Firma:** híbrida **Ed25519 + ML-DSA** sobre los bytes canónicos
  **RFC 8785 (JCS)**, con separación de dominio `GUS3-GST-V2` y el
  descriptor de algoritmos/claves *dentro* de los bytes firmados
  (**anti-downgrade** estructural: quitar o degradar cualquiera de las dos
  ramas invalida el sobre).
- **Solo legado:** `WOTS+` (`src/gerarion/deprecated/hashots.py`) y la API
  `GST v1` (`gerarion.gst.create` / `verify`, `GtsDocument`) están
  deprecados, emiten `DeprecationWarning` y quedan fuera del perfil
  normativo.

### Requisitos obligatorios de confianza para integradores

Un sobre matemáticamente válido **no** es un sobre confiable. Los
integradores **DEBEN** pasar ambos elementos a `gerarion.gst.v2.verify`:

1. un **`KeyRegistry`** que vincule `(issuer, kid)` con las claves públicas
   autorizadas (comparación en tiempo constante con `hmac.compare_digest`;
   ventana de vigencia, rotación y revocación), y
2. un **`ReplayStore`** atómico y transaccional (`SQLiteReplayStore` o un
   equivalente atómico; `ReplayGuard` es una referencia de un solo proceso).

Ambos operan en modo ***fail-closed***: con `trust_store=None` el emisor se
reporta no confiable (`key_status="UNCHECKED"`); con `replay_store=None` el
nivel de identidad es inválido salvo opt-in explícito
`allow_unchecked_replay=True` (y `replay_checked` queda en `False` en el
reporte). Un almacén de replay corrupto rechaza todo en lugar de reiniciar
`seq`.

### Los tres niveles de verificación (`gerarion.gst.v2.VerificationResult`)

| Nivel | Campo | Qué establece |
|---|---|---|
| 1 | `crypto` | Validez matemática: canonicalización JCS, `event_hash`, descriptor anti-downgrade y firmas duales Ed25519 + ML-DSA. |
| 2 | `identity` | Autorización de la clave para `(issuer, kid)` en el instante firmado (activa / histórica / expirada / revocada / discordante) y anti-replay / anti-rollback transaccional. |
| 3 | `temporal` | Procedencia y calidad del reloj (`gt-gts`): `VERIFIED`, `HOLDOVER`, `UNVERIFIED`, `REJECTED` o `UNKNOWN` cuando no se aporta una lectura autenticada. |

> **`sealed` cubre los niveles 1 y 2.** `anchored` y `overall_trusted` exigen
> además una lectura `VERIFIED` y evidencia temporal independiente vinculada
> al sobre exacto y aceptada por la política de verificación del host.

### Límites conocidos (estado honesto)

- **Aún no existe auditoría criptográfica externa independiente** de
  `gt-gst` ni del notario Merkle.
- **Aún no hay custodia de claves en hardware (`TPM` / `HSM`)**; un atacante
  con `root` en el host firmante puede firmar eventos arbitrarios con sus
  claves.
- `gt-tslr`, `gt-gcerts`, el perfil Roughtime y el perfil RFC 3161 son
  **EXPERIMENTALES**.

Mientras no se cierren ambos puntos, `gt-gst` **no debe** usarse en decisiones
críticas de seguridad en producción. La integridad de distribución la
aportan `SHA256SUMS.txt` y `EXPORT-MANIFEST.json` (+ firma separada opcional
`EXPORT-MANIFEST.json.sig`, ver [COMPATIBILITY.md](COMPATIBILITY.md)).
Análisis de amenazas: [docs/spec/threat-model.md](docs/spec/threat-model.md).

### Reportar una vulnerabilidad (divulgación responsable)

- Canal: **Private vulnerability reporting** de GitHub (Security → Advisories
  → *Report a vulnerability*). **No** abras un issue público.
- Plazos objetivo desde el reporte: **7 días** acuse de recibo, **30 días**
  evaluación y decisión, **90 días** fix + CVE (si procede) o justificación
  de descarte.
- Coordinamos la divulgación con el reportante; crédito bajo el nombre que
  indique en el reporte.
