GUS-for-notation

Abstract

This short document defines the MINIMAL surface of the Gerarion
Universal Standard (GUS) that a system needs in order to exchange and
compare time values unambiguously: the canonical timestamp format,
the continuous instant, the RFC 3339 interoperability mapping
(GUS-3339), and the machine-readable normative vector set. It contains
NO cryptography, NO notary, NO protocol. It is deliberately the
smallest thing a third party can adopt.

Status of This Memo

This document is an individual submission, written to be convertible
to an RFC-style informational document. Normative language in this
text follows BCP 14 (RFC 2119 / RFC 8174). The regulatory language is
the English text; the Spanish mirror is informative (EN prevails).

1. The instant

1.1. The instant is an integer: exact seconds elapsed since the GUS
     origin (day index 0, 00:00:00). It is signed (negative = era AY).
1.2. Day index 0 corresponds to Julian Day Number 1719313
     (proleptic Gregorian 21 March -5, astronomical year -5 = 6 BC).
     The JDN is the interop point with any Gregorian/proleptic system.
1.3. Scale: no leap seconds (TAI-like linear count). Decision D-001
     (draft, in review) sharpens the UTC/TAI boundary; until it is
     RESOLVED, UTC-to-instant conversion via GUS-3339 is defined by the
     reference behavior and the normative vectors, not by prose.2. The canonical timestamp

2.1. Format:

      AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ+O]

      AAAAYY  year, 1-4 digits, era DY (forward) or AY (ante)
      MM      month: 01..12 regular, 00 Tempalum (year-closing month)
      DD      day: 01..30 (regular), 01..04 or 01..11 (Tempalum)
      X       weekday letter, one of S L M A T V B (0 = Soludyia)
      HH:MM:SS  optional, 00:00:00..23:59:59, leap second :60 FORBIDDEN
      CC      cycle, SC (06:00-17:59) or LC (18:00-05:59), MUST agree
              with HH (parsers MAY correct and flag, REGLA 4)
      TCJ+O   optional offset in hours, integer, -99..+99

2.2. The weekday letter is DERIVED, not carried: for the day index d,
     letter = WEEKDAYS[d mod 7]. A mismatch is reportable; the
     computed letter always prevails (REGLA 4).
2.3. Tempalum exists only in Gran Tempalum years beyond day 4 (days
     5..11 are "Nuvivid", structural intercalary week). A Tempalum day
     >4 in a common year is GERO_ETEMPALUM.
2.4. Canonical bytes for hashing/signing/anchoring:

      b"YYYY-MM-DD-X[-HH:MM:SS-CC-TCJ+O]\n<instant>\n"
      ctx = "GUS2-TS" (prefix form: context-line, see vectors)

3. GUS-3339 (interop with RFC 3339 UTC)

3.1. Mapping (exact, defined in vectors/gus-3339-001.json):

      instant(UTC 1970-01-01T00:00:00Z) = 62,318,160,000 s

      i.e. offset = (JDN 2440588 minus ORIGIN_JDN 1719313) * 86400.
3.2. Domain: years 0000..9999 RFC 3339; '+00:00' and 'Z' accepted and
     equivalent; leap second ':60' REJECTED (GERO_E3339); any nonzero
     UTC offset REJECTED (Z or +00:00).

4. Errors

   GERO_EINVAL      out-of-range field or syntax
   GERO_ETEMPALUM   nonexistent Tempalum day for that year type
   GERO_EWEEK       declared weekday letter inconsistent with computed
   GERO_E3339       RFC 3339 mapping violation (GUS-3339 profile)

5. Conformance (the ONLY rule)

An implementation is conformant to "GUS-for-notation" if and only if
it consumes vectors/gus-normative-001.json (calendar and instant
categories) and vectors/gus-3339-001.json (mapping category) and
produces, for each input, exactly the output the vectors declare,
including exact error codes. Two conformant implementations with the
same vectors CANNOT silently diverge: the vectors are the standard.

6. Security Considerations

The canonical format is notation only: it makes comparison and
ordering unambiguous but certifies nothing about the TRUTH of the
declared instant. Authenticated time requires the attestation layer
(GST, profiles GUS-3161 / GUS-Roughtime) and a source of trustworthy
time at signing; notation MUST NOT be mistaken for a clock.

7. IANA Considerations

No registry actions are required by this document.

Author's Address / Normative References

The vector set is the normative artifact:
   vectors/gus-normative-001.json  (calendar core, instants, canonical)
   vectors/gus-3339-001.json       (RFC 3339 mapping)
Reference implementations exist in Python (primary), JavaScript (web/)
and C (impl-c/); the monolithic stdlib verifier tools/verify_gus.py
serves as the offline check.
