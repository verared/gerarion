# GUS in English — Normative version

The documents in `docs/en/` are the **normative English version** of the
Gerarion Universal Standard (GUS).

The Spanish originals (`docs/spec/gus-2.1.0.md`,
`docs/spec/threat-model.md`, `docs/errata-v1.2.md`,
`docs/informe-adopcion-gus.md`) are **informative mirrors** of this
English version: they exist for reference and reading convenience, but
they carry no independent normative weight of their own.

## Rule of precedence

**In case of divergence between this English version and the Spanish
original (docs/spec/, docs/errata-v1.2.md,
docs/informe-adopcion-gus.md), the English version (docs/en/) prevails
for normative purposes.**

This rule applies both to the content of the normative sections of the
documents listed below and to anything else in those documents where the
two versions could be read differently.

## Correspondence of documents

| English (normative, this folder) | Spanish original (informative mirror) |
|---|---|
| `docs/en/gus-2.1.0.md` | `docs/spec/gus-2.1.0.md` |
| `docs/en/threat-model.md` | `docs/spec/threat-model.md` |
| `docs/en/errata-v1.2.md` | `docs/errata-v1.2.md` |
| `docs/en/adoption-report.md` | `docs/informe-adopcion-gus.md` |

Terms that are proper names of the standard or of its calendar are
translated nowhere and carried identically in both versions: GUS, GST,
the `GERO_*` error constants (GERO_EINVAL, GERO_ETEMPALUM, GERO_EWEEK),
the week day names (Soludyia, Loondyia, Mardyia, Aisterdyia, Trustdyia,
Viendyia, Sabatyeh), Tempalum — first mention "Great Tempalum (GT)" —,
Keuphero, Yeshuvid, Nuvid, the eras DY / AY, the cycles SC / LC, TCJ,
JDN, `day_index`, the context string `"GUS2-TS"`, and the canonical
format `AAAAYY-MM-DD-X[-HH:MM:SS-CC-TCJ±O]` exactly as written.

## Complementary historical documentation

The historical corpus of 32 documents (Spanish) is not published as a
separate repository. Its historical, documentary and spiritual content is
preserved in `docs/papers/` as an explicitly non-normative, informative
layer: it is part of the record of GUS but does not take part in the
normative precedence defined above. The calendar, the Nuvid language and
the original research were created by Gerardo Loyola (github.com/geroiloyola);
the standard is maintained by the verared project (future foundation) (github.com/verared).

## Change control

Divergences between the English normative version and the Spanish mirrors
are defects and are handled like any other erratum: an entry in
`docs/en/errata-v1.2.md` — mirrored in the Spanish errata — plus the
corresponding test, following the versioning rules of section 11 of
`docs/en/gus-2.1.0.md`.
