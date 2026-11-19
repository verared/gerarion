# GUS-Roughtime Profile — external witnesses bound to the anchor field

> **Layer**: attestation profile · **Version**: roughtime-001 · **Status**: normative
> **Spanish mirror**: [`docs/profiles/gus-roughtime-perfil.md`](../../profiles/gus-roughtime-perfil.md) — EN prevails.
> **Reference code**: `src/gerarion/profiles_roughtime.py` (pure Python, stdlib only)
> **Tests**: `tests/test_profiles_roughtime.py` (no network, no external service)
> **TODO-002**: full UDP wire-format parsing and shard chaining of the Roughtime protocol is out of scope of this profile and is listed in `docs/history/TODO-pendientes.md`.

## 1. Purpose

The GUS notary (k-de-n) bounds existence from INSIDE the cluster. An
attacker who compromises all notaries can still rewrite existence
bounds alone. Roughtime adds witnesses that are INDEPENDENT of the
GUS cluster: servers that sign, with Ed25519, their response to a
nonce chosen by the sealer. Compromising the notaries is no longer
enough: the forged chain must also carry the signatures of every
external witness.

This profile defines the RECEIPT: the signed unit a witness (or a
full client in the name of one) produces, verifiable offline with zero
dependencies. Where the data comes from on the wire (UDP Roughtime
protocol) is a transport concern and stays open as TODO-002.

## 2. Rules (MUST)

1. **Signed bytes** (exact byte sequence signed by the witness):

   ```
   "GUS-ROUGH-TIME" \n nonce \n midpoint (RFC 3339 Z) \n radius (decimal) \n
   ```

2. **Receipt JSON** (`type: "gusroughtime-001"`): `midpoint_rfc3339`,
   `radius_s`, `pubkey_b64`, `signed_b64` (the bytes of rule 1),
   `sig_b64` (Ed25519). All base64 fields are standard encoding.
3. **The witness is a witness, not an authority**: the receipt yields
   the assertion window `[midpoint - radius, midpoint + radius]`, never
   the truth of a declared instant. The GUS instant MUST NOT be derived
   from the midpoint.
4. **Anti-replay by nonce**: the nonce is `SHA-256(bundle_bytes)` of the
   sealed artifact. It is a SIGNED field, so an old receipt cannot be
   replayed over new bytes: recomputing the nonce on modified bytes
   breaks the binding. A verifier MUST reject a receipt whose nonce
   cannot be matched to the artifact it claims to cover.
5. **Trust root of witnesses**: the verifier declares which witness
   public keys it accepts. A receipt from a key not in that list is
   "not verifiable here", never "silently true".
6. **Coherence check**: with the GST instant `t`, the verifier MUST
   reject the anchor if `t > midpoint + radius` (a witness cannot have
   answered before the artifact existed).
7. **Ed25519**: signatures follow RFC 8032. The reference verifier is
   pure Python (stdlib only, `profiles_roughtime.py`); it is a REFERENCE
   implementation for conformance and offline checking, not for
   production signing. The public-key path is validated against the
   RFC 8032 TEST 2 vector.

## 3. What the profile guarantees and what it does not

| Property | Guarantee |
|---|---|
| The sealed bytes existed no later than `midpoint + radius` | Yes, after validating the witness trust root |
| Resistance to replay of old receipts | Yes — the nonce is signed and bound to the bundle digest |
| A witness independent of the GUS notary cluster | Yes, if the verifier accepts multiple keys |
| The declared GST instant is true | NO — the witness only bounds it from outside |
| The witness's clock was honest | NO — same limits as GUS-3161; independence is what Roughtime adds, honesty comes from having several witnesses |
| Protection if the device's clock is wrong | NO — see threat model; GUS attests order and existence, not the current wall clock |

## 4. Placement in the GST

The GST field `anchor` carries exactly the result of `bind_anchor`:

```json
{"type": "roughtime", "midpoint_rfc3339": "...", "radius_s": 3,
 "pubkey_b64": "...", "signed_b64": "...", "sig_b64": "..."}
```

Anchors compose: one GST can carry a GUS-3161 sidecar, a `roughtime`
anchor, and the k-de-n notary chain at the same time. The verifier is
free to require 1+ of each; the profile defines the unit, not the
quorum policy.
