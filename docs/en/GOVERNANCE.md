# Governance — GUS (Gerarion Universal Standard)

Version: 2.0 — status: RATIFIED (v2.0). Maintainer: the verared project (future foundation)
(github.com/verared). Original creator: Gerardo Loyola (github.com/geroiloyola).

> **Language.** This document is the normative governance reference. The
> Spanish version (`GOVERNANCE.md`) is an informative mirror. In case of
> divergence, the English text prevails (EN > ES). The normative
> terminology (GTS, GST, notary, vector set) is identical in both.

---

## 1. Guiding principle

GUS is a technically verifiable standard. Legitimacy does not come from an
organization, an author, or an affinity community: it comes from the
**verifiable properties of the artifact**. A change to the GUS kernel does
not "win" because a committee approves it: it wins because, against the
published normative vectors (`vectors/gus-normative-001.json`), every
implementation keeps producing the same output, bitwise, from three
independently written code bases (Python, JavaScript, C).

Any proposal that compromises this verifiable property is invalid by
definition, no matter how many votes it receives.

## 2. What is "kernel" (and is immutable without a Looking Period)

The **GUS kernel** is the exact set of constants and rules that define the
output of the calendar and of the instants:

- `ORIGIN_JDN` (JDN 1719313)
- `SOLAR_DELTA_UD` (1 242 190 µd/day) and `SOLAR_THRESHOLD_UD` (7 000 000 µd)
- The Gran Tempalum rule (GT years: 5, 11, 16, 22, 28, 33, 39, 45;
  position and length of the Tempalum)
- The month order (12×30 + Tempalum) and the Nuvid pattern (7 invariant
  days, computed from the day index, not from what any document declares)
- The canonical GTS format and its normalization rules 1–7
- The semantics of instants (continuous leap-second-free scale over TAI)
  and the solar oscillation bound of the anchor (|Δ| < 7 days; the
  concrete window of start dates is an observed measurement that shifts
  over millennia, not a kernel property)
- The `GERO_*` error codes and the ABNF of the format

What is **not** kernel (changeable by maintainer majority): informative
context documents (the historical and cultural documentation lives in
`docs/papers/`, non-normative), auxiliary tools (`tools/`), the web frontend
(`web/index.html`, `web/app.js`, `web/style.css`), CI infrastructure,
packaging, and informative texts.

## 3. The four decision mechanisms

### 3.1. Kernel: 90-day Looking Period

Every kernel change (the 7 items of §2) follows the same cycle
formalized in this governance:

1. **Public proposal** (PR + issue labelled `kernel-change`): must cite the
   affected vector(s) and give a technical justification. Without technical
   justification the PR does not enter review.
2. **Looking Period — 90 running days**: the proposal stays visible, open,
   unmerged, for at least 90 running days. During this period, any
   implementation (the three reference ones and third-party ones) must be
   able to re-run the test suites and its own tests against the proposal.
   The "break glass" route — see §3.4 — is the only shorter path.
3. **Decision**: the proposal is approved if, at the close of the period:
   (a) no conformant implementation reproducibly diverges from the
   proposal, and (b) at least **two of three maintainers** are favorably
   informed (§3.5). If there is no agreement, the proposal is postponed to
   the next 90-day cycle (it is not discarded).
4. **Vectors**: an approved kernel change implies a new versioned vector
   set (`gus-normative-002.json`, etc.) generated with
   `tools/generate_vectors.py` and a CHANGELOG commit. The previous vector
   set is archived (outside the main branch) for traceability.

**Practical implication**: if after reading this someone concludes "GUS
already works, why opine?" — the answer is: 90 days and reproducible
proofs, or nothing. The short route (§3.4) exists for security incidents,
not for design disagreements.

### 3.2. Errata

A factual error (date, constant, value) in a normative document is
corrected via `docs/errata-vN.M.md` (ES) / `docs/en/errata-vN.M.md` (EN)
even when it does not affect kernel output. If it affects the output, it
is a breaking kernel change (§3.1) and forces a new vector set version.
Errata are enumerated with the prefix E-01, E-02, etc., with its minimal
reproduction and its correction.

The historical file `docs/errata-v1.2.md` remains as the record of the six
errata E-01..E-06 applied to the historical v1.2 document.

### 3.3. Fork Certification

**Any fork** of the standard (kernel divergence, different constants,
regional variant) is **welcome, public and certifiable** — but for a fork
to call itself "GUS" (reserved siglum — see §5), it must:

1. Publish a **fork certificate** (`forks/<slug>/FORK.yaml`) with:
   - `gus_base_version`: the GUS version the fork branches from
   - `kernel_diff`: enumeration of the constants/rules that differ
   - `vector_set_fingerprint`: SHA-256 fingerprint of the fork's vector
     set (the fork's Python and third-party implementations must pass
     their own vector set generated with `tools/generate_vectors.py`)
   - `maintainers`: who maintains the fork (verifiable identities, §5)
   - `epoch`: the instant (GUS timestamp) of the fork, signed with the
     fork's or GUS's notary/cluster (so the divergence is
     timestamp-anchored, not "work in silence")
2. Publish the fork URL in this repository's fork registry
   (`forks/README.md`), linking FORK.yaml and the fork repository.
3. Expose a **health-check** endpoint equivalent to the notary replicas':
   the fork signs publications with its own key, so a GUS client can
   immediately distinguish a fork signature from a GUS signature
   (different `pub`, different replica tables).

Certification is **not** an endorsement of content: it is a public
declaration of difference, so that nobody mistakes a fork for the
standard. A fork passing itself off as GUS without a certificate is the
offender's problem, not the standard's — but governance documents it.

### 3.4. Security process (break glass)

**If a real vulnerability exists that threatens the unforgeability
property of time (GST, notary, trust root):**

- **Announce in the security channel**, not in public issues. The channel
  is this repo's `SECURITY.md`. Publishing in issues before a mitigation
  is achieved is the reporter's own responsibility.
- Maintainers have authority to **apply the fix WITHOUT a Looking Period**
  and immediately publish a security release (patch version, i.e. x.y.Z)
  with an attached security note, provided that:
  - the fix passes the existing vectors: no conformant implementation
    changes output except in the cases declared vulnerable,
  - an erratum `docs/errata-vN.M.md` (ES) / `docs/en/` (EN) is written
    explaining the incident,
  - the CHANGELOG records the unaffected vector set (same hashes).
- Exposure of the trust root ceremony key (§5) is the most severe case: it
  forces a re-ceremony and re-publishing the trust root
  (`tools/trust_root.py`), with revocation of the previous key inside the
  new trust root itself (field `previous_trust_root`), never deletion.

### 3.5. Maintainers

| Role | Responsibility | Count |
|---|---|---|
| Kernel maintainer | Approves kernel changes (§3.1) after the Looking Period | 2 of 3 |
| Implementation maintainer | Keeps Python, JavaScript or C conformant with the vector set | 1 per language |
| Notary maintainer | Cluster operation, key ceremony, rotation (docs/notary-runbook.md) | 1-3 replicas |
| Publication maintainer | PyPI/npm/Pages/SBOM and packaging | 1 |

(Adjusted to project maturity; one person may hold two roles, but must
**never** hold "kernel maintainer" + "implementation maintainer" over the
same code base that votes on the vector set that same implementation must
conform to — the fox-in-the-henhouse pattern.)

A third and final group — not listed above — is the **general public**:
anyone may propose, review, submit vectors, report errata, run the
differential fuzzing against the repo, and open issues. Technical
sovereignty is not voting; it is **the power to reproduce**.

## 4. End-to-end flow of a technical change

```
issue labelled kernel-change
   -> PR with technical justification and affected vectors
   -> Looking Period 90 days (or security track §3.4)
   -> test re-run in Python + JS + C against the vectors
   -> 2/3 maintainers approve
   -> merge + new versioned vector set + CHANGELOG
   -> release (PyPI + npm + tag + Pages re-deploy)
```

Conformance of a third-party implementation:

```
publish the vector set (JSON) -> consume the JSON -> PASS == conformant
```

If an implementation answers "I am conformant" without naming the version
of the vector set it passed, it declares nothing.

## 5. Key policy and cryptographic authority

- **Ceremony key** of the trust root: SLH-DSA-SHA2-128F (FIPS 205),
  generated in ceremony with OS RNG, **the private key is wiped from
  every networked computer** after signing (recorded on two separate
  physical channels — see runbook §4).
- **Key rotation**: yearly or upon any suspicion of compromise. Rotation =
  new ceremony + new trust root that names the `previous_trust_root`
  (chain revocation, never deletion).
- **Replica keys**: one per notary-cluster replica, quarterly rotation
  (configurable in `deploy/`).
- **Cryptographic veto**: anyone can verify the trust root
  (`tools/trust_root.py verify`) against a ceremony key they personally
  recorded outside the digital channel. If two trust roots with the same
  ceremony but different replicas appear: it is a **split brain** —
  declared a governance emergency (§3.4 mitigation) and resolved by
  notary weight (the longest verified daily chained log wins; runbook §5).
- **The siglum "GUS" is reserved**: only the kernel may carry it (see
  forks in §3.3). Any fork that wants to differentiate publicly uses its
  own name, without sharing the brand or the cluster keys.

## 6. Conflict of interest

- A member may not simultaneously hold two roles whose decision on the
  same proof is decided by the same person (§3.5).
- Any contribution from a commercial entity must declare whether the
  proposal affects its product. Declaring does not disqualify; **not
  disclosing an effect while having one** does disqualify.
- Normative vectors, tests and the IETF draft are decided by
  reproducibility, not commercial affinity: a PR from a rival company
  with correct vectors beats an internal PR with incorrect vectors.

## 7. Governance errata

This document itself can be erratized — but with the same 90-day Looking
Period as the kernel. Governing/technical conflicts are resolved in favor
of reproducibility (§1).

---

## 8. Trademark "Gerarion"

**Registration status**: NOT VERIFIED — as of the current state of this
repository, "Gerarion" does not appear as a registered trademark in any
trademark office, and this governance declares no registration.

**Use policy** (while no registration exists):

- The name "Gerarion", the siglum "GUS" and the standard's name are used
  freely by conformant implementations (passing the normative vector set)
  and for honest communication about the standard.
- Claiming conformance ("conformant with gus-normative-001") is allowed;
  any use that declares false conformance or nonexistent sponsorship will
  be forbidden if a registration is formalized in the future.
- Conformant forks may keep the name with their identifier added
  (e.g. "Gerarion — fork <name>"); non-conformant forks may not claim
  conformance with GUS.

If the trademark is ever registered, this section is updated first
(governance erratum, §7) and the registration is declared here, nowhere
else.

## 9. Glossary not here: pointers

- Format properties and regex: `docs/en/gus-2.0.md` (EN normative) /
  `docs/spec/gus-2.0.md` (ES mirror, informative).
- Threat model: `docs/en/threat-model.md` (EN) / `docs/spec/threat-model.md`.
- Notary runbook: `docs/notary-runbook.md` (planes: EN pending; see repo).
- Vectors and conformance clause: `vectors/README.md`.
- Historical errata: `docs/en/errata-v1.2.md` (EN) / `docs/errata-v1.2.md`.
