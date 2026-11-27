# CMS & API Integration Guide (`gt-core` + `gt-gst` @ `v3.4.0`)

- **Normative baseline:** `GUS v3.0.0` / suite `v3.4.0` (release target; satellite tags require Phase B synchronization)
- **Target audience:** Developers integrating *Gerarion Time* into external CMS platforms (e.g., Portaless, WordPress, headless content APIs) or audit-log pipelines without cloning the `verared/gerarion` monorepo.
- **Spanish mirror:** [`CMS-INTEGRATION.es.md`](CMS-INTEGRATION.es.md) (EN > ES)

---

## 1. Standalone Installation (Consuming Satellites Only)

An external CMS or API service never needs to clone `verared/gerarion`. Combine
the `src/` trees of **`verared/gt-core`** and **`verared/gt-gst`** (both pinned
to tag `v3.4.0` and verified against their `EXPORT-MANIFEST.json`), plus
`cryptography>=47` for ML-DSA (FIPS 204) + Ed25519 (RFC 8032):

```bash
mkdir -p vendor/gerarion-satellites
git clone --branch v3.4.0 --depth 1 https://github.com/verared/gt-core.git /tmp/gt-core
git clone --branch v3.4.0 --depth 1 https://github.com/verared/gt-gst.git /tmp/gt-gst
cp -R /tmp/gt-core/src/* /tmp/gt-gst/src/* vendor/gerarion-satellites/
python3 -m pip install "cryptography>=47"
export PYTHONPATH="$PWD/vendor/gerarion-satellites"
```

Because `gt-core` and `gt-gst` preserve relative paths under `src/gerarion/`,
Python 3.9+ loads `gerarion.core` and `gerarion.gst` as a clean PEP 420
namespace package with zero extra configuration.

---

## 2. Canonical Event Schema (`gerarion-cms-event/1`)

Before creating a `GST v2` envelope, canonicalize the CMS business event with
`gerarion.gst.jcs.dumps_bytes(event)` so that `event_hash` binds the exact
content, causal chain, actor, and temporal context:

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

### Mandatory Separation of Temporal Fields
- **`event_time`:** When the domain event occurred according to the application or upstream producer.
- **`recorded_at`:** When the CMS database or persistence layer committed the record.
- **`signed_at` (`ts` in `GST v2`):** When the `HybridSigner` sealed the `GST v2` envelope.
- **`clock_state`:** Explicit trust state from `gt-gts` (`VERIFIED`, `HOLDOVER`, `UNVERIFIED`, `REJECTED`), or `"UNKNOWN"` when running on a standard OS wall clock without an authenticated `gt-gts` source. **Never report `"VERIFIED"` unless a real `gt-gts` authenticated reading was evaluated.**

---

## 3. End-to-End Integration: `KeyRegistry`, `SQLiteReplayStore`, Rotation & Revocation

```python
import hashlib
from gerarion.core import format as fmt
from gerarion.gst import HybridSigner, jcs, v2

# 1. Key Trust Registry: bind (issuer, kid) to authorized public keys and validity windows
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

# 2. Multi-worker transactional replay & monotonic sequence store (SQLite WAL + BEGIN IMMEDIATE)
replay_store = v2.SQLiteReplayStore("/tmp/cms_gst_replay.sqlite3")

# 3. Canonicalize CMS event with RFC 8785 (JCS) and compute event_hash
cms_event = {
    "schema": "gerarion-cms-event/1",
    "tenant": "portaless-main",
    "actor": "user:editor-17",
    "action": "post.publish",
    "object_id": "post:42",
    "object_version": 1,
    "content_hash": "sha256:" + hashlib.sha256(b"<h1>Hello</h1>").hexdigest(),
    "previous_event_hash": "sha256:" + "00" * 32,
    "event_time": "2031DY-03-08-T-09:30:00-SC-TCJ+0",
    "recorded_at": "2031DY-03-08-T-09:30:00-SC-TCJ+0",
    "signed_at": "2031DY-03-08-T-09:30:00-SC-TCJ+0",
    "clock_state": "UNKNOWN",
}
event_hash = "sha256:" + hashlib.sha256(jcs.dumps_bytes(cms_event)).hexdigest()

# 4. Issue GST v2 envelope
envelope = v2.create(
    fmt.parse(cms_event["signed_at"]),
    signer_2026,
    event_hash=event_hash,
    issuer="cms.portaless.org",
    kid="cms-2026-q4",
    seq=1,
)

# 5. Three-level verification (fail-closed)
result = v2.verify(
    envelope,
    expected_event_hash=event_hash,
    trust_store=registry,
    replay_store=replay_store,
    required_scope="cms.events",
)
assert result.crypto.valid is True
assert result.identity.valid is True and result.identity.key_status == "ACTIVE"
assert result.identity.replay_status == "OK"
assert result.temporal.clock_state == "UNKNOWN"
assert result.sealed and not result.overall_trusted
```

### Key Rotation, Revocation, and Backup Safety
- **Key rotation:** Keep the former key in `KeyRegistry` with its closed `valid_until` window. Historical events within that window can still be `sealed` with key status `HISTORICAL`; events signed after it fail with `KEY_EXPIRED`.
- **Emergency revocation:** Set `revoked_at` (TCJ instant or GUS stamp) on the compromised `TrustedKeyRecord`. Events prior to `revoked_at` remain auditable as `HISTORICAL`, while any event at or after `revoked_at` is rejected with `KEY_REVOKED`.
- **Backups without silent rollback:** `SQLiteReplayStore` runs in `WAL` mode with `synchronous=FULL` and `BEGIN IMMEDIATE`. Never restore an older snapshot of the replay SQLite database for an active `kid` (restoring an older `last_seq` would reopen a replay window). If disaster recovery requires restoring from backup, rotate to a fresh `kid` upon recovery.

---

## 4. External Acceptance Test Checklist (`GEIACT-1`)

When creating the external CMS repository, execute the following **8 experiments + 3 deliberate failure injections** to certify the integration:

### The 8 Functional & Security Experiments
1. **E1 — Satellite-only assembly:** Install solely from `verared/gt-core` + `verared/gt-gst` (`v3.4.0`), verifying `EXPORT-MANIFEST.json` with `--verify-existing` before starting the CMS.
2. **E2 — Deterministic event hashing:** Canonicalize a `gerarion-cms-event/1` payload with `jcs.dumps_bytes` and confirm identical `event_hash` across worker restarts.
3. **E3 — Three-level verification:** With the independently computed event digest, verify that the active key produces `sealed=True`; with `clock_state="UNKNOWN"`, `overall_trusted` remains `False`.
4. **E4 — Causal hash chain:** Chain 100 consecutive CMS events (`previous_event_hash -> event_hash`) with monotonically increasing `seq = 1..100` and verify the full chain offline.
5. **E5 — Multi-worker concurrency:** Submit 16 concurrent threads/workers attempting to verify/ingest the same signed envelope against a shared `SQLiteReplayStore`; confirm **1 accepted (`OK`)** and **15 rejected (`REPLAY`)**.
6. **E6 — Key rotation preservation:** Register `k2` after `k1`'s `valid_until`; confirm old events signed by `k1` validate as `HISTORICAL` while new events signed by `k2` validate as `ACTIVE`.
7. **E7 — Key revocation cutoff:** Set `revoked_at` on `k1`; confirm events before `revoked_at` validate as `HISTORICAL` and events at/after `revoked_at` fail with `KEY_REVOKED`.
8. **E8 — Authenticated clock propagation (optional `gt-gts`):** Pass a `ClockReading(state=ClockState.VERIFIED, ...)` to `v2.verify(..., clock_reading=reading)` and confirm `result.temporal.clock_state == "VERIFIED"`.

### The 3 Deliberate Failure Injections (Must Fail Closed)
1. **F1 — Self-signed key spoofing (`KEY_MISMATCH`):** An attacker signs a valid `GST v2` envelope with their own `HybridSigner` claiming `issuer="cms.portaless.org"` and `kid="cms-2026-q4"`. Level 1 (`crypto.valid`) is `True`, but Level 2 (`identity.valid`) **MUST** be `False` with `key_status == "MISMATCH"` (`KEY_MISMATCH`) and `overall_trusted == False`.
2. **F2 — Omitted replay store (`REPLAY_UNCHECKED`):** Without a replay store or `allow_unchecked_replay=True`, verification reports replay `SKIPPED`, identity invalid, and `sealed=False`.
3. **F3 — Corrupted SQLite replay file (`CORRUPT_STATE`):** Overwriting the SQLite file header with random bytes **MUST** put `SQLiteReplayStore` into fail-closed mode, rejecting all subsequent envelopes rather than resetting `seq` to zero.
