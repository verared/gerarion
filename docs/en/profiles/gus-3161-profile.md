# GUS-3161 Profile — GUS marks anchored into RFC 3161 (existing TSAs)

> **Layer**: attestation profile · **Version**: 3161-001 · **Status**: normative
> **Spanish mirror**: [`docs/profiles/gus-3161-perfil.md`](../../profiles/gus-3161-perfil.md) — EN prevails.
> **Reference code**: `src/gerarion/profiles_tsa.py` (subprocess `openssl`, stdlib only)
> **Tests**: `tests/test_profiles_tsa.py` (local ephemeral TSA; no network)

## 1. Purpose

RFC 3161 Time Stamping Authorities (TSAs) are the already-deployed
attestation infrastructure: every enterprise PKI has one. Their limit is
cryptography: TSA responses are RSA or ECDSA (classical signatures), and
their time units are UTC wall-clock labels.

GUS-3161 makes GUS and RFC 3161 complementary:

- **The TSA certifies EXISTENCE**: the sealed bytes were presented to
  the TSA no later than its `genTime` (the TSA says nothing about the
  veracity of any declared instant).
- **GUS certifies ORDER and AUTHORSHIP**: the GST binds the canonical
  instant to a post-quantum signature and to a notary chain.

Anchoring a GUS artifact into an existing TSA gives GUS a bridge into
deployed infrastructure without asking it to trust any GUS notary. It
also adds a second, independent witness from outside the GUS cluster:
compromising the notaries alone no longer suffices to move existence
boundaries.

## 2. Rules (MUST)

1. **Sealed data**: the TSA hashes exactly the bundle bytes
   `canonical_bytes(canon, instant)` of the GST (or the artifact bytes
   being anchored). The digest algorithm MUST be SHA-256 or stronger.
2. **The TSA is a witness, not an authority**: the profile never derives
   the GUS instant from `genTime`. The genTime is recorded as an
   existence bound, converted to a GUS instant with the **GUS-3339**
   profile for comparability, and labeled as a bound, not as truth.
3. **Sidecar JSON** (`type: "gus3161-001"`): `gst_sha256`,
   `tsa_gen_time` (RFC 3339 Z), `tsa_gen_time_gus_instant`,
   `token_b64` (the full TS_RESP in base64; self-contained).
4. **Offline verification**: the verifier MUST check (a) the TS_RESP
   cryptographically against a declared trust root (TSA certificate;
   `openssl ts -verify` in the reference), and (b) that the sealed
   digest equals the digest of the artifact being verified. Without
   (a) and (b), the sidecar PROVES NOTHING.
5. **genTime precision**: fractional seconds are truncated. Sub-second
   races are not GUS semantics; the sidecar is an upper bound from an
   external witness, not a primary reading.
6. **TSA certificates are data, not trust**: the verifier declares
   which trust roots it accepts. A TSA unknown to the verifier yields
   "not verifiable here", never "silently true".

## 3. What the profile guarantees and what it does not

| Property | Guarantee |
|---|---|
| The sealed bytes existed at genTime | Yes, after validating the TSA trust root |
| The declared GST instant is true | NO — the TSA only bounds it: `gst.instant <= sidecar.tsa_gen_time_gus_instant` |
| The TSA's clock was honest | NO — a witness is always as honest as its clock; that is why the notary chain exists |
| Reuse of an old TSA token over modified bytes | Detectable — the digest check (rule 4b) fails |

## 4. Conformance

The profile carries no new constants beyond GUS-3339 and the bundle
definition. Conformance clause: an implementation declares GUS-3161 if
it (a) extracts the genTime from a real TS_RESP (the dynamic content is
built locally in the e2e test with an ephemeral TSA, so no machine
vector carries a wall-clock value), (b) verifies tokens offline, and
(c) reproduces the sidecar JSON key-for-key from the same
(bundle, token) pair.
