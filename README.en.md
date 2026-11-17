# Gerarion Universal Standard (GUS)

[![CI](https://github.com/verared/gerarion/actions/workflows/ci.yml/badge.svg)](https://github.com/verared/gerarion/actions/workflows/ci.yml)

> **STATUS: ALPHA.** Functional, verified standard, pre-adoption; the API and paths may change before v1.0.

**Regular, universal, verifiable time.**

A time standard integrating three layers under one machine-verifiable
specification:

1. **Regular calendar:** 12 months of exactly 30 days + closing Tempalum
   (4/11 days). Every fixed date falls on the same weekday, every year.
2. **Continuous scale:** linear instants over TAI, no leap seconds.
   Comparisons, ranges and totals trivial in any language.
3. **Verifiable timestamp (GST):** post-quantum signature + chained daily
   Merkle notary. The effective security level is ~2^128 against a
   quantum attacker (Grover); the raw SHA-256 preimage cost is 2^256, and
   the WOTS+Merkle level further depends on parameters (tree height,
   Winternitz — see [numbers](#why-the-marks-are-expensive-to-alter)).
   Rewriting anchored past requires recomputing the whole notary chain
   without leaving detectable divergence between replicas.

The exact guarantees — and what GUS does **not** guarantee — are declared
in ["What GUS does NOT guarantee"](#what-gus-does-not-guarantee) and in the
[threat model](docs/spec/threat-model.md). **In case of divergence between
this English version and the Spanish original
([README.md](README.md)), this English version prevails (EN > ES).**

---

## The idea in 30 seconds

```
2026-05-23 (Gregorian)  →  2031DY-03-08-T  (canonical GUS)
```

Anatomy of the format `AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O]`:

| Field | Example | What it is |
|---|---|---|
| `AAAA` + era | `2031DY` | Year 2031 of the **DY** era (after the origin). `AY` counts backward. Day 0 is 1 Keuphero of year 0 |
| `MM-DD` | `03-08` | Month 3, day 8 → 68 days after the year start. Months of 30, no exceptions |
| `X` | `T` | Nuvid weekday letter (`S L M A T V B` = Soludyia…Sabatyeh). **Computed** from the day index: a declared letter that disagrees is corrected by the parser (`weekday_corrected`) |
| `HH:MM:SS` | `09:30:00` | Time of day. The canonical instant is a single integer: `day_index × 86.400 + s`, no leap seconds |
| `CC` | `SC` | Luminous cycle (semantic label, not arithmetic): `SC` 06:00–17:59, `LC` 18:00–05:59 |
| `TCJ±O` | `TCJ+0` | Civil offset (presentation only). The canonical instant is not changed by it |

Year structure:

| Year | Days | Weeks | Tempalum | Determined by |
|---|---|---|---|---|
| Common | 364 | 52 exact | 4 days | integer recurrence |
| **Great Tempalum (GT)** | 371 | **53 exact** | 11 days | the same recurrence |

GT years are known by exact integer recurrence for all n (first of the
short cycle: 5, 11, 16, 22, 28, 33, 39, 45 — year 2031DY starts on
17 March 2026 Gregorian). **1 Keuphero is always Soludyia**: GUS does have
53 week years, but the 53rd week is structural — the 11 named days of the
Great Tempalum, determined in advance, not an anomaly each library solves
differently as in ISO 8601. Conceptually the Tempalum is an **intercalary
 week** (leap week), as in Symmetry454 or Pax — with the critical property
that 364 and 371 are multiples of 7: no day ever falls outside the weekly
cycle (see [Related work](#related-work)).

Names such as **Keuphero** (month 1), **Tempalum** (closing month), the
weekday letters and the DY/AY eras are *opaque labels* of the standard: no
normative rule depends on their meaning. Their etymology, philosophy and
origin notes have a cultural origin documented outside this repository
(not published).

## Installation

Independent distribution from GitHub: no PyPI, no npm, no external
registries. Three layers, zero mandatory dependencies:

```bash
# Python (kernel, stdlib >= 3.9) — installable straight from the repo with pip:
pip install "git+https://github.com/verared/gerarion.git"
pip install "gerarion[slh] @ git+https://github.com/verared/gerarion.git"
#   the second adds SLH-DSA (slh-dsa 0.2.5) for production signatures.
#   Alternatively: download the .whl or .tar.gz from the latest GitHub
#   Release and install with: pip install <downloaded-file>
```

```bash
# JavaScript / ESM (kernel, zero dependencies): direct download from
# GitHub Releases (https://github.com/verared/gerarion/releases):
#   - gerarion.mjs (single file, import it as-is), or
#   - gerarion-kernel-<version>.tgz (standard npm tarball; unpack and
#     require it from your local package.json)
import { toGerarion, fromGerarion } from "./gerarion.mjs";
```

```c
/* C11 (kernel and conformance): compiles directly, no dependencies */
make -C impl-c            # builds gus-cli and the conformance suite
# or, minimal, the kernel only:
cc -std=c11 -O2 -c impl-c/gus.c -o gus.o    # gus.h is the public header
```

Each GitHub Release attaches the artifacts (`.whl`, `.tar.gz`, `.tgz`,
C binaries) plus `SHA256SUMS.txt` for integrity verification
(`sha256sum -c SHA256SUMS.txt`); generated by the workflow
`.github/workflows/release.yml` on every `v*` tag (see
[Publication](#publication)). The `[slh]` extra is optional: it is the
project's only dependency.

## Normative language

The English version of `docs/spec/gus-2.0.md`, `docs/spec/threat-model.md`,
`docs/errata-v1.2.md` and the adoption report lives in
[`docs/en/`](docs/en/), together with [`README.en.md`](README.en.md), a
complete mirror of this README. **In case of divergence between the English
and Spanish versions, the English one prevails (EN > ES).** The complementary
historical documentation of the Gerarion Calendar lives in
[`docs/papers/`](docs/papers/) as an informative, non-normative layer (see
[Credits and cultural context](#credits-and-cultural-context)).

## Publication

- **GitHub Releases**: <https://github.com/verared/gerarion/releases> —
  artifacts per version: Python wheel and sdist (`pip install`), JS kernel
  tarball (`gerarion-kernel-<version>.tgz`), C implementation binaries and
  `SHA256SUMS.txt`. Generated by `release.yml` on every `v*` tag.
- **Web calculator**: GitHub Pages from `web/` (workflow `pages.yml`:
  Python + JS suites + JS and C conformance before publishing).
- **SBOM**: [`sbom.cdx.json`](sbom.cdx.json) (CycloneDX 1.5).
- **Normative vectors**:
  [`vectors/gus-normative-001.json`](vectors/gus-normative-001.json) — the
  conformance of every implementation (Python, JS, C and third parties)
  is declared against this file. Full clause in
  [`vectors/README.md`](vectors/README.md).
- **Monolithic verifier**: [`tools/verify_gus.py`](tools/verify_gus.py)
  — a single file, stdlib only, nothing to install: it implements the
  core, the canonical format, the reference signature (hash-only) and
  the notary anchor. Meant as a downloadable artifact to verify a GST
  outside the repo (`python3 verify_gus.py gst.json`).
- **Interop profiles** (EN normative, ES mirror):
  [GUS-3339](docs/en/profiles/gus-3339-profile.md) (RFC 3339 mapping
  with its own vector set),
  [GUS-3161](docs/en/profiles/gus-3161-profile.md) (RFC 3161 seal with
  sidecar), [GUS-Roughtime](docs/en/profiles/gus-roughtime-profile.md)
  (Ed25519 receipts from external witnesses bound to the anchor), and
  [GUS-for-notation](docs/en/profiles/gus-for-notation.md) (the minimal
  consumable surface: notation only, no cryptography).

## Quick start

```python
from gerarion import calendar as cal

cal.to_gerarion(cal.day_index_from_gregorian(2026, 5, 23)).canonical()
# '2031DY-03-08-T'
```

```bash
gero convert 2026-05-23          # Gregorian -> GUS
gero convert 2031DY-03-08-T      # GUS -> Gregorian
gero keygen --height 8           # hash-only key pair (post-quantum)
gero sign "2031DY-03-08-T-09:30:00-SC-TCJ+0"      # creates a GST
gero verify gst.json             # full verification
```

## Limitations of each system for computational use

This catalog analyzes each time system in force from a single angle: **its
use as a computational value** (date arithmetic, logs, contracts,
synchronization). The lunar and lunisolar calendars (Hebrew, Hijri,
Chinese) do that *on purpose*: observing the moon is a religious and
cultural function, not a defect — the limitation appears when a computing
system uses them as a record base. Incident rows link a source;
structural-limitation rows justify the fact in the row itself
(structural = verifiable with arithmetic, no press needed). Each row
declares which GUS property closes it.

### Civil calendars

| System | Structural limitation or documented incident | What fails in computing | GUS response |
|---|---|---|---|
| **Gregorian** | Months of 28–31 days; Feb 29 every 4 (except century years); modern best practice (UTC + RFC 3339, 64-bit epoch) avoids *part* of it, but date↔date conversion still crosses tables/libraries | Edge-case arithmetic in *every* conversion: banking and invoicing bugs at month end, comparing mixed formats | 12×30 exact + single Tempalum: date subtraction is a multiple of 30 plus residue; zero tables |
| **Gregorian (week)** | A fixed date changes weekday every year; "every Monday" fiscal does not exist | Sessions, reminders and contracts require perpetual recalculation | Years of exactly 52 or 53 weeks; 1 Keuphero always Soludyia; every fixed date has a permanent weekday |
| **Gregorian (ISO 8601)** | Week 53 (364→371 days) exists, but falls on years starting Thursday (common) or Wednesday (leap): the "first Thursday" rule makes it irregular and unmemorable (2009, 2015, 2020 are 53-week years and nobody knows without computing) | Systems grouping by fiscal week disagree | GUS also has week 53, but it is **structural**: the 11 days of the Great Tempalum, determined by integer recurrence known in advance, always between the end and the start of the year |
| **Gregorian (Excel/1900)** | Excel inherited Lotus's nonexistent Feb 29, 1900 leap day (documented bug to this day) | 1-day differences in spreadsheets worldwide | Single JDN origin and vector-verified conversion; no "decorative historical dates" |
| **Jewish (Hebrew)** | Lunisolar *on purpose*: months of 29/30 days, year of 353–355 or 383–385 days, leap Adar II, the day starts at sunset. Its religious purpose is legitimate — the computational limitation is different: one civil date spans two Hebrew dates and years vary by ±30 days | Unpredictable annual durations for software; a Hebrew deadline requires up-to-date conversion tables | Fixed day of 86,400 s starting at civil midnight; regular months; continuous count. The Hebrew religious purpose is untouched |
| **Islamic (Hijri)** | Purely lunar *on purpose*: 11 days of annual drift against the solar year, month start by moon observation (not computable in advance), Umm al-Qura and other variants diverge (two countries can have a different "1st of month" on the same day) | Contracts and logs crossing Hijri/solar require current conversion tables per country | Solar base with mathematical anchor; bounded drift (bound \|Δ\| < 7 days) in exchange for a larger annual oscillation — a trade-off, not a superiority; deterministic implementation |
| **Chinese (lunisolar)** | Leap months by solar-term and new-moon rules: the assignment has documented historical ambiguities ("2033 problem": different authorities disagree on which leap month applies) | Same astronomical data, two different Chinese calendars; software that disagrees | Single, integer, cached intercalation rule (accumulator recurrence); the same everywhere on any platform |
| **Ethiopian** | 13 months (12×30 + Pagume 5/6); 7–8 years behind Gregorian; new year Sept 11/12. The Ethiopian "millennium bug" was September **2007** Gregorian (Ethiopian year 2000; [New Scientist](https://www.newscientist.com/article/dn12650-mystery-of-the-ethiopian-millennium-bug-solved/)) | Year boundaries offset against Gregorian systems | A single JDN origin; exact round-trip conversion, no era gaps |
| **Persian (Solar Hijri)** | Months of 29–31 days; leap years depend on the equinox observed before/after noon in Teheran; historically required astronomy and sometimes decrees | No universal simple formula exists: Nowruz implementations diverge in specific years | Closed exact recurrence (pure integer arithmetic): same result in 2026 and in year 10,000 |
| **All** | The mean year does not match the tropical year: Gregorian +0.00031 d/a (~1 day per 3,220 years); Julian +0.0078 d/a (already 13 days off) | Drift is unbounded long-term, though the Gregorian is well calibrated | **A trade, not superiority:** GUS bounds the drift (\|Δ\| < 7 days proven, [paper](docs/papers/)) in exchange for a larger momentary oscillation (±7 days around the equinox) — the same compromise leap-week calendars make |

### Time, zone and synchronization failures (affecting the whole planet today)

| Vulnerability | Documented fact (citable source) | Typical scope | GUS response |
|---|---|---|---|
| **Leap second** | 30 Jun 2012: Linux kernel *livelock* (Reddit, Mozilla, LinkedIn, Cloudera outages; [Wired](https://www.wired.com/2012/07/leap-second-glitch-explained/)). 1 Jan 2017: [Cloudflare 502s at the edge](https://blog.cloudflare.com/how-and-why-the-leap-second-affected-cloudflare-dns/) — a **negative** duration (combination of the leap second and the applied smoothing), together with the non-monotonicity of Go's `time.Now()`, drove the DNS process into a panic ([official Cloudflare blog](https://blog.cloudflare.com/how-and-why-the-leap-second-affected-cloudflare-dns/)). Context: the CGPM ([Resolution 2](https://www.bipm.org/en/cgpm-2022/resolution-2), 2022) voted to abolish leap seconds by 2035, and meanwhile Google and AWS *smear* the second their own way (different smears from each other) — best practice today is an operator-by-operator patch | Millions of servers | Continuous counting: the second the infrastructure cannot handle does not exist. No operator decrees, no vendor-specific smears |
| **tzdata: the "past" changes by decree** | tzdata is a continuously updated database: countries redefine historical offsets (Russia abolished summer DST in 2011, Turkey in 2016, Morocco changes every Ramadan) — old tzdata packages show wrong times for months | Hundreds of millions of phones with stale tzdata | `TCJ±O` is a presentation field, not a transformation: the canonical instant is unique and the zone cannot alter the count |
| **DST changed by decree** | Mexico abolished DST (Oct 2022); Egypt reinstated it (2023); annual transitions change by law | Misaligned clocks for months after every law | GUS does not change civil clocks by policy. Honest note: mapping location→offset will still need a tzdata-like base — what GUS solves is the **canonical instant**, not the civil problem |
| **Ambiguous local time (fold/gap)** | At a DST transition the same civil time occurs twice (fall) or never (spring): invoices, alarms and logs are non-convertible | Any DST zone (~40% of the world) | Single mapping instant → SC/LC cycle, never ambiguous (RFC 3339 with offset solves this *if* the offset is always stored — GUS makes it structure) |
| **NTP spoofing / MITM** | Unauthenticated ntpd is modifiable in transit; NTS authentication (RFC 8915, 2020) exists but requires deployment; CVE-2013-5211: `monlist` amplification used in ~400 Gbps DDoS (2014; [NVD](https://nvd.nist.gov/vuln/detail/CVE-2013-5211)) | Any host querying open NTP | Time as a signed value + notary: the hour is not *queried*, it is *verified* |
| **Weak default NTP keys** | CVE-2014-9293/9294 (ntpd generated weak default MD5 keys without `requestkey`); the associated buffer overflows are [CVE-2014-9295](https://nvd.nist.gov/vuln/detail/CVE-2014-9295) (NVD, Dec 2014) — vulnerable routers and appliances | Home routers, appliances | Hash-only signatures, no shared default secrets; daily anchoring makes the attack visible |
| **GNSS spoofing** | Jun **2017**, Black Sea: on 22 June the US Maritime Administration logged the Novorossiysk case — 20+ ships reported jumping 32 km inland, to [Gelendzhik Airport](https://www.newscientist.com/article/2143499-ships-fooled-at-sea-in-the-first-gps-cyberattack-in-russia/) (New Scientist). GNSS jamming affects 5G networks synced by satellite | Ships, aircraft, mobile networks | A GNSS jump produces divergent roots: the daily notary admits no retroactive root and replicas expose it |
| **Replay in clock-based protocols** | Kerberos allows 5 min skew by design: within that window tickets can be replayed; web apps accepting expired cookies due to client clocks | Corporate infrastructure worldwide | The instant is a signed total integer; the skew window stops being a cryptographic perimeter and becomes operational tolerance |
| **Smart-contract timestamps** | Reliance on [`block.timestamp`](http://swcregistry.io/docs/SWC-116/) (SWC-116, recognized Solidity vulnerability class): miners can move it forward | DeFi/on-chain | On-chain time can anchor to a previously published GUS `day_root`: altering the anchor requires breaking SHA-256, not "waiting for mining" |
| **Y2038 (32-bit)** | Modern practice already uses 64-bit epoch (Linux/glibc, iOS/Android); billions of 32-bit devices remain (IoT, RTOS, legacy routers) where `time_t` overflows on 19 Jan 2038 | Legacy devices | GUS operates on arbitrary-precision integers (Python/BigInt): no representation ceiling |
| **Y10K and silent limits** | Libraries assuming 4-digit years or months 1–12 as invariant | Perpetual patching | Variable-length format, explicit era, named Tempalum days |
| **Trusting "the server's clock"** | A compromised server shows any time: logs useless for forensics | Every company with a single authority clock | A mark without GST is a *claim*; with notarial anchoring it is a *fact* verifiable by third parties (bound: the mark existed **no later than** the anchor — see ["What GUS does NOT guarantee"](#what-gus-does-not-guarantee)) |
| **Roughtime (precedent)** | Google (2016) showed distributed time can be verified with chain/hash proofs — exactly the mechanism GUS specializes to a regular calendar | — | GUS adds: an edge-case-free calendar, invariant week and post-quantum signature; the notary uses the same Merkle proof type |

### The pattern behind each row

Each incident matches one of four root causes; GUS closes them by design,
not by patch:

1. **Structural irregularity** (months 28–31, moons, observational leap
   days) → total regularity (12×30 + Tempalum, exact integer recurrence).
2. **Arbitrary governance** (DST decrees, reforms, regional variants) →
   single deterministic rule; the civil offset is optional and visible.
3. **Trust in mutable infrastructure** (NTP, GNSS, server clocks) →
   cryptographic signature + chained notary with replicas.
4. **Representation limits** (32 bits, 4-digit years, historical zones) →
   arbitrary integers + explicit era + documented escapes.

## What GUS does NOT guarantee

Declared with the same force as the guarantees:

1. **It does not guarantee that the signed time is *true*.** A GST proves a
   mark existed and was committed **no later than** the notarial anchor it
   references (upper bound). Whoever holds the key can sign any time; the
   notary exposes it only if published *after* the anchor the declared time
   demands. Roughtime and RFC 3161 share this limitation — it is the
   mathematical limit of every timestamp without an external oracle
   certifying the truth of each hour.
2. **It does not guarantee key integrity.** If a signing key is compromised
   without visible revocation in the log, marks signed in the compromise
   window are doubtful.
3. **It does not guarantee honest replica distribution.** The notary's
   "objectivity" rests on an **operational** (not mathematical) assumption:
   that the k replicas do not collude. Two divergent trust roots (split
   brain) detect each other, but the consumer decides which to trust. The
   runbook declares the emergency procedure.
4. **It does not replace civil infrastructure.** The location→civil-offset
   map still needs tzdata. Physical clocks still need a source
   (GNSS/NTP). GUS makes the *value* verifiable; it does not replace
   physical synchronization.
5. **The TAI scale is not "100% mathematical".** What is purely
   mathematical is the calendar: a total function of the day index. TAI
   depends on physical atomic clocks maintained by the BIPM, and the
   divergence from the solar day (UT1) keeps growing — exactly the price
   of eliminating leap seconds. GUS's guarantee about time is *verifiable
   consistency*, not astronomical truth.
6. **It does not require universal adoption to be useful.** The notary
   works with any calendar (a `day_root` is just a chain of signed roots);
   GUS offers it *integrated* with a regular calendar and vectors, but it
   can be used as a notary over Gregorian dates if that eases migration.

## Why the marks are expensive to alter

| Layer | Mechanism | Cost to break (honestly stated) |
|---|---|---|
| Mark (GST) | Reference hash-only signature (SHA-256 + WOTS + Merkle) | SHA-256 preimage: 2^256. **Effective level: ~2^128** (dominated by Grover in the quantum case, and parameter-dependent: Merkle tree height and Winternitz bound — see stateful note) |
| Mark (SLH-DSA) | FIPS 205, SHA2-128f: **stateless** signature | FIPS 205 Security Level 1 (~2^128 with Grover); 17,088-byte signature, 32-byte public key. Note: `SLH-DSA-SHA2-128s` would yield ~7.9 KB signatures (7,856 bytes measured with the reference library), slower to sign; **it is not the parameter set used by the reference** |
| Notary | Chained daily root `root(n) = H(n, tree(n), root(n-1))` | Recompute the entire later chain **keeping consistency across published replicas** |
| Objectivity | Independently published replicas (declared operational assumption — see §3 of "What GUS does NOT guarantee") | Rewrite all of them **without leaving detectable divergence** |

**Note on stateful signatures.** The reference hash-only scheme uses
Winternitz + Merkle: each leaf signs exactly one message; reusing an index
breaks security (the XMSS/LMS risk family — see NIST SP 800-208). State
discipline is the holder's responsibility and the daily anchoring records
the used index (repeated leaf = public alarm). The recommended production
scheme is **SLH-DSA (FIPS 205)**, stateless:
`gerarion.adapters.SlhDsaSigner`.

**Concrete numbers:** reference hash-only height 8 → JSON signature of
9,354 bytes (raw binary serialization: 67×32 + 8×32 = 2,400 bytes: 67
Winternitz elements + 8 path nodes, all 32 bytes),
32-byte public key (64 hex chars), 256-leaf tree (256 marks/day per key);
SLH-DSA-128f → 17,088-byte signature (128s: 7,856, not the reference set),
32-byte pk. The notary's daily root is
32 bytes — offline verification recomputes the tree from the bundle leaves
(no network, no third-party latency).

None of this depends on political trust *for its verification*: the
mathematics is executable by anyone. Replica *independence* and key
governance are human-trust questions (formal governance in
[GOVERNANCE.md](GOVERNANCE.md)). Full detail in the
[threat model](docs/spec/threat-model.md).

## Honest limitations and costs

1. **Fiscal quarters.** A 13-week fiscal quarter (91 days) does not match
   3 months of 30 (90 days). The invariant week helps weekly calendars,
   not quarters.
2. **Tempalum block.** A common year leaves 4 days outside the months and a
   GT year 11. Any system assuming 12 uniform fiscal months must treat the
   Tempalum as a separate block (it is written in the format: `MM=00`).
3. **Months do not fit weeks.** 30 is not a multiple of 7: a fixed date
   keeps its weekday across years, but the 1st of each month falls on a
   different weekday depending on the month. Symmetry454 and the
   International Fixed Calendar align month and week; GUS does not (it
   chooses uniform months over weekly months).
3. **Migration cost.** Every system must interoperate with what exists:
   GUS ships with exact bidirectional conversion (`to_gerarion` /
   `from_gerarion`, the Gregorian round trip shipped in the vector set)
   and the optional civil offset keeps the familiar reading. Real
   migration (banks, ERP, contracts) is an institutional project: the
   adoption report ([ES](docs/informe-adopcion-gus.md) /
   [EN](docs/en/adoption-report.md)) proposes a phased path without
   big-bang.
4. **The notary needs operation.** Keys, replicas, rotation, ceremony: it
   is infrastructure with ops cost (full runbook in
   [`docs/notary-runbook.md`](docs/notary-runbook.md)).

## Related work

**Nothing here is new piece by piece — every component has precedent,
and it is worth saying so.**

- **12×30 + closing days:** the ancient Egyptian civil calendar
  (12×30+5), the French Republican calendar (12×30 + 5/6 complementary
  days), the Coptic, the Ethiopian and the Bahá'í (19×19 + intercalary).
  These are the closest structural ancestors of the GUS block.
- **Invariant week with intercalary week:** Symmetry454, Hanke-Henry
  and Pax. The GUS Tempalum is, conceptually, an *intercalary week*
  (leap week) and should be read as such.
- **Purely arithmetic calendars:** the Hebrew (computable arithmetically
  since the 4th century), the tabular Hijri, the 33-year Persian.
- **Continuous day counting:** Julian Day Number, the Maya long count,
  Unix time, TAI.
- **Chained timestamping:** Haber and Stornetta (1991) — whence Surety,
  publishing weekly hashes in the New York Times since 1995 — plus RFC
  3161, OpenTimestamps, Certificate Transparency and Roughtime.
- **"Ancient for the computational era":** the Holocene Era, the Long
  Now clock (5-digit years) and Comte's Positivist Calendar.

**The key historical lesson.** Calendar reform (Cotsworth/Eastman's
International Fixed Calendar and the World Calendar) was studied by the
League of Nations — on 18 January **1937** the League took formal action
on the topic ([Ministry Magazine, July 1937](https://www.ministrymagazine.org/archive/1937/07/status-of-reform-calendar-issue)) —
and did not prosper; the main objection was **religious**: blank days
broke the continuity of the 7-day cycle (the Jewish delegation presented
that case to the League's preparatory committee — [JTA](https://www.jta.org/archive/calendar-reform-threat-to-sabbath-jewish-delegation-puts-case-against-blank-day-to-league-of-nati)).
GUS avoids that sin
because **364 and 371 are multiples of 7**: the Tempalum adds whole
weeks, never orphan days. This is the calendar's strongest design
argument, which is why it is explicit.

**And GUS's real novelty is the package:** a regular calendar with
normative vectors, three independent conforming implementations and an
optional cryptographic layer, all under an executable conformance
clause. None of the precedents offers that contract: their reform failed
through political adoption; GUS replaces political adoption with
reproducibility (see [GOVERNANCE.md](GOVERNANCE.md)).

**Cryptographic timestamping:** GUS does not compete with OTS/CT/Rekor/
3161/Roughtime — it incorporates them as bridges (`tools/ots_bridge.py`
anchors the daily day_root to OTS; RFC 3161 maps in the runbook) and
uses the same Merkle mechanism.

## FAQ

**Why not UTC + RFC 3339?**
UTC plus offset solves instant *representation* — and is the right exchange
format. It does not solve calendar arithmetic (irregular months), scale
stability (leap seconds the CGPM has not yet abolished in practice,
vendor-specific smears), or verifiability (a `2026-05-23T09:30:00Z` is just
a number; nothing certifies it). GUS uses a continuous TAI scale and adds
the verification layer; the TCJ±O offset keeps presentation compatibility
with civil reading.

**Why not just use the notary over a Gregorian calendar?**
You can — that is exactly point 5 of ["What GUS does NOT
guarantee"](#what-gus-does-not-guarantee). The notary does not know which
calendar sits on top of it (it is a chain of signed roots). GUS ships them
integrated because the calendar is what people **design contracts with**:
if the contract layer has months of 28–31 and the anchoring layer another
thing, presentation error is the one thing never missing from forensic
logs. That is why the specification is a single one for the
calendar+instant+anchoring triple, with a vector set for all three.

**Why "2031DY"? What is DY?**
The origin of the count is 1 Keuphero of year 0, **defined by its JDN:
day 0 = JDN 1719313**, Soludyia by definition. The equivalence with 21 March
of -5 (6 BC) proleptic gregorian is a conversion example, with erratum E-07
as the boundary: the GUS calendar is independent of the gregorian, and
proleptic gregorian conversion is used as an interoperability service. The year 2031DY of the example — anchored at 17 March
2026 — is a vector-set example: the year is determined by the solar
recurrence; the normative guarantee is the oscillation bound (|Δ| < 7 days),
which follows from 1 Keuphero always falling on Soludyia: any correction is
applied in whole 7-day steps (the standard's mean-year constant guarantees
it), so the bound holds as a model property but does NOT cover the real
physical drift of the tropical year over millennia; and the date window is
**observed, not structural** (year starts fall
between 10 and 21 March over 11,000 simulated years, and that window drifts
slowly over the millennia). The DY era covers `day_index ≥ 0`; AY,
before the origin.

**What if my use case needs no signature?**
Ignore it. The calendar kernel + canonical format works standalone
(`gerarion.calendar`, `web/gerarion.mjs`, `impl-c/`), zero cryptographic
dependencies. The GST/notary layer is opt-in.

## Documents

```
docs/
├── spec/gus-2.0.md          Normative specification (v2.0; ES mirror at docs/spec)
├── spec/threat-model.md     Threat model and guarantees
├── informe-adopcion-gus.md  Technical report: why adopt GUS in computing (ES)
├── errata-v1.2.md           The 6 defects of the historical v1.2 draft, test-verifiable
├── en/                      5 normative documents in English (EN>ES precedence)
├── ietf/                    xml2rfc draft (GUS 2.1) for IETF
├── notary-runbook.md        Notary cluster operation, ceremony and rotation
└── papers/                  Bounded drift (proof), IETF draft v1, C lib
```

*(Complementary historical documentation (papers) is in `docs/papers/`, non-normative.)*

**IETF status:** the draft
([`docs/ietf/draft-gerarion-gus-00.xml`](docs/ietf/draft-gerarion-gus-00.xml))
is an *individual submission* (no working group assigned); prepared in
xml2rfc v3 with proposed IANA registries, pending formal submission. The
historical v1 Markdown draft is OBSOLETE (archived outside this
repository, not published).

The formal governance of the standard (who approves kernel changes, the
90-day Looking Period, fork certification, key policy, conflicts of
interest) is in [GOVERNANCE.md](GOVERNANCE.md).

## Credits and cultural context

The Gerarion Calendar, the Nuvid language and the original research were
created by **Gerardo Loyola** ([github.com/geroiloyola](https://github.com/geroiloyola)),
whose work is the basis of this entire project. The GUS standard is
maintained by the **verared** project (future foundation)
([github.com/verared](https://github.com/verared)), responsible for the
standard in the long term (github.com/verared/gerarion).

That historical, cultural and religious origin is **not normative for GUS**:
the standard uses only the canonical format of the spec and the vectors.
Complementary documentation is preserved, as non-normative research, in
[`docs/papers/`](docs/papers/); known discrepancies between that material
and this kernel are logged in [`docs/errata-v1.2.md`](docs/errata-v1.2.md).

## Status

- [x] Exact calendar core (integers, no floats) — 91 Python tests
      (incl. 6 fuzzing + 2 conformance) + 22 JS vectors green
- [x] Conformance against `vectors/gus-normative-001.json`: Python, JS and
      C, 7/7 core categories each; differential fuzzing across the three
      implementations (1500×3 identical cases)
- [x] Canonical format + normalization (rules 1–7, GERO_* errors)
- [x] Reference hash-only GST (WOTS+Merkle, state-disciplined)
      + SLH-DSA (FIPS 205) via adapter + chained Merkle notary
- [x] CLI (`gero`)
- [x] Production notary (multi-replica, k-of-n, SLH-DSA-signed trust root,
      OTS/RFC 3161 bridges, compose/systemd deploy)
- [x] Web calculator (static, no backend, live vector self-test,
      Playwright E2E 12/12)
- [x] Normative English (`docs/en/`, 5 documents, EN>ES precedence)
- [x] Interop profiles (GUS-3339, GUS-3161, GUS-Roughtime) with local e2e
      tests and a pure-stdlib monolithic verifier (`tools/verify_gus.py`);
      decision D-001 (UTC/TAI boundary) as a public draft, in 90-day review
- [x] Minimal adoption document GUS-for-notation (notation only)
- [x] First GitHub push + publication via GitHub Releases (independent distribution, no external registries)
- [ ] First operational OpenTimestamps anchor
- [ ] Witness verification against the live Roughtime network (TODO-002)

**Current version: alpha** — the standard is reproducible from the repo
(vectors, three implementations, conformance), but there is not yet any
external deployment or independent third-party implementation.

## License

Code: MIT. Documents: CC-BY-4.0. The optional
[`slh-dsa`](https://pypi.org/project/slh-dsa/) dependency
(LGPL-3.0-or-later) is **not** bundled or vendored: it is installed
separately and this repository does not redistribute any of its source.
See [NOTICE](NOTICE) and [sbom.cdx.json](sbom.cdx.json).

## Versions

| Artifact | Version | What it numbers |
|---|---|---|
| Normative specification (`docs/spec/gus-2.0.md`) | **2.0** | The standard itself; it only changes with approved normative changes (90-day review window) |
| IETF draft (`docs/ietf/draft-gerarion-gus-00.xml`) | **2.1** | The submission document (individual submission) that describes the spec; it can advance without the spec changing |
| Packages (`pyproject.toml`, `web/package.json`) | **2.3.4-alpha.2** | The software artifacts: Python/JS/C kernel, tests, docs and applied errata. Can change between spec releases |
