# Phase 1B-D1D-A semantics-evidence correction report

## Completion status and fixed boundary

This phase-scoped correction addresses the independent integrity review of the
draft D1D-A static PYTHIA source audit. It does not modify or execute PYTHIA,
load APFEL or LHAPDF, invoke a repository physics binary, initialize a
generator, create an event or dataset, perform numerical work, select an
architecture, or authorize a prototype.

The immutable D1C result remains:

```text
D1C_FINAL_DECISION = FAIL
failed_gate = generator_facing_signed_pdf_contract
D2_AUTHORIZED = false
```

The robust D1D-A conclusion also remains:

```text
MINIMAL_PUBLIC_READER_PATCH = INSUFFICIENT
```

The stronger v2 readiness claim did not survive integrity review. The
corrected prospective result is derived by the validator and is:

```text
D1D_A_RESULT = EVIDENCE_CORRECTION_REQUIRED
```

Issue #10 remains blocked. D2 remains unauthorized.

## Original v2 finding and integrity-review failure

Audit v2 reported `READY_FOR_ARCHITECTURE_COMPARISON` from closure over nine
declared patterns. The independent review established that this overstated the
evidence:

- eight of nine stored command strings were not executable because ERE
  metacharacters were unquoted;
- no canonical raw-match identity was defined;
- 41 boundary-member references were dangling;
- 21 raw matches implicitly mapped to multiple pointer-role targets;
- `PR01`–`PR04` and `PU01`, `PU02`, and `PU04` lacked honest origin handling;
- `CSG118.M001` named the wrong owning symbol;
- 90 legitimate declaration-derived locations and 15 `getXPDF` locations were
  absent from the declared recall set;
- 66 concrete members had the wrong denominator semantic class;
- 18 exclusions were overbroad and eight had the wrong exclusion class; and
- the artifact called 375 members denominators without separately reporting
  the 60-group scale of that claim.

No source text was copied, so this was not a copyright blocker. The artifacts
did require normalization and compaction.

## Corrected generator and schemas

The repository-owned generator/validator is:

```text
scripts/phase1bd_d1d_pythia_semantics_audit.py
```

It supports:

```text
--generate
--validate
--output-audit PATH
--output-search-manifest PATH
```

It reads only installed/extracted PYTHIA headers and source plus the curated
documentation evidence. It performs no physics execution.

Schema changes are:

| Artifact | Old schema | Corrected schema |
|---|---|---|
| Audit | `partonsbi.phase1bd.d1d.pythia-semantics-audit.v2` | `partonsbi.phase1bd.d1d.pythia-semantics-audit.v3` |
| Search manifest | `partonsbi.phase1bd.d1d.pythia-semantics-search-manifest.v1` | `partonsbi.phase1bd.d1d.pythia-semantics-search-manifest.v2` |

## Artifact identity and compaction

| Artifact | Version | SHA-256 | Bytes | Lines |
|---|---|---|---:|---:|
| Audit | v2 | `0515ef7146bfca17545f4cb145511804efc9695ae991bf98ac353f6adc2e1eb4` | 625,466 | 14,537 |
| Audit | v3 | `3668143ab16ad4463e79012ac8422c99f21d796c150b6089eaa9400e820ff2c6` | 566,320 | 1 |
| Search manifest | v1 | `a7aec222fdb75165733739624ae1b6db9782ded715bf5d03a7a8944b192656b5` | 1,511,865 | 41,527 |
| Search manifest | v2 | `f7a5da0ba209dca175b7ba0dcfce5980aa355c85b30bb2f2d2aafcc29081e221` | 555,402 | 1 |

The search artifact normalizes file, identifier, classification, reason,
symbol, and target-type values through stable dictionaries. Raw matches are
compact rows of IDs and coordinates. The audit and manifest use deterministic
canonical JSON. No PYTHIA source line or excerpt is stored.

## Structured search contract

Ten specifications cover the same declared 374-file inventory. Each stores:

```text
executable
argv[]
pattern_id
pattern_syntax
source_inventory_id
```

The nine v1 pattern families remain, and
`P10_DECLARATION_DERIVED_RECALL` covers the declaration-derived integrity
review identifiers. The validator emulates the structured specifications
directly from their argument data; it never passes an interpolated command to
a shell. Display commands are non-authoritative and rendered with shell
quoting.

The canonical raw-match key is the ordered tuple:

```text
pattern_id
inventory_file_id
line_number
match_ordinal_on_line
utf8_byte_offset
matched_identifier_sha256_16
```

`match_ordinal_on_line` and `utf8_byte_offset` prevent distinct occurrences on
one line from being collapsed. The regenerated key set must equal the
serialized set, and its canonical order must also match.

Corrected search totals are:

```text
searched_file_count             = 374
structured_search_spec_count    = 10
canonical_raw_match_count       = 4033
included_match_count            = 1109
excluded_match_count            = 2924
unclassified_raw_match_count    = 0
duplicate_canonical_key_count   = 0
```

Exact set equality and deterministic ordering both pass.

## Declaration-derived recall resolution

The candidate vocabulary is derived from `PDF` and `BeamParticle`
declarations, PDF provider fields, wrappers, and concept-bearing declarations.
The corrected inventory derivation yields 779 identifiers and records the
deterministic vocabulary SHA-256
`4f136e3fcdbebaf7a83060595e367dc7450da60eb71a9269be9bd448fe2134ce`.
It includes the omitted `xfModified0`, `xfModPrep`, `xfRaw`, `xMax`, PDF
envelope helpers, ordinary/hard pointer roles, valence helpers, photon-PDF
approximants, and `getXPDF`.

All 105 integrity-review findings have explicit coordinates and exactly one
outcome:

| Previous finding set | Outcome | Count |
|---|---|---:|
| 90 legitimate locations | `INCLUDED_AS_MATERIAL_CONSUMER` | 31 |
| 90 legitimate locations | `INCLUDED_AS_BOUNDARY` | 32 |
| 90 legitimate locations | `INCLUDED_AS_POINTER_OR_POLICY_EVIDENCE` | 27 |
| 90 legitimate locations | `SOURCE_CONFIRMED_NONMATERIAL` | 0 |
| 90 legitimate locations | `DUPLICATE_ALIAS_WITH_CANONICAL_TARGET` | 0 |
| 90 legitimate locations | `UNRESOLVED` | 0 |
| 15 `getXPDF` locations | `UNRESOLVED` | 15 |

The 15 `getXPDF` entries are not suppressed or guessed into a class. They are
linked to `PU05` and prevent architecture-comparison readiness.

## Mapping and provenance correction

Every addressable boundary member now has a stable member ID. Raw matches have
one primary target plus zero or more explicitly typed related targets. Evidence
origins use the v3 enum:

```text
SEARCH_DERIVED
HEADER_INVENTORY_DERIVED
CONFIGURATION_DERIVED
POLICY_QUESTION
MANUAL_SCIENTIFIC_INFERENCE
```

`PR01`–`PR04` are explicitly header-inventory-derived. `PU01` and `PU02` are
manual scientific inference, while `PU03`–`PU05` are policy questions.
`CSG118.M001` now names `BranchElementalISR::saveTrial`.

Corrected integrity totals are:

```text
dangling_target_ids                    = 0
orphan_search_derived_records          = 0
incompatible_multi_target_mappings     = 0
nonexistent_source_coordinates         = 0
invalid_enclosing_symbols              = 0
```

## Classification correction

The review's 74 classification defects consist of 66 wrong denominator member
classes and eight wrong exclusion classes.

The 66 member corrections were made from their owning expressions:

| Corrected primary role | Members |
|---|---:|
| `REQUIRES_NONNEGATIVE_DENSITY` | 50 |
| `REQUIRES_MONOTONE_CUMULATIVE_WEIGHT` | 4 |
| `SUPPORT_DOMAIN_CHECK_NOT_SIGN_SEMANTICS` | 12 |

All 18 overbroad exclusions are now included as `BeamParticle` boundary
evidence. Of the eight wrong exclusion classes, three `xfUpdate` records are
boundary evidence and five `TINYPDF` constant records are `DEFINITION_ONLY`.
The one wrong owning symbol is corrected as described above.

Corrected group and concrete-member totals are reported separately. A group
count means the number of groups containing at least one member of the class;
a heterogeneous group can contribute to more than one class.

| Primary semantic class | Groups containing class | Concrete members |
|---|---:|---:|
| `REQUIRES_NONNEGATIVE_DENSITY` | 25 | 80 |
| `REQUIRES_STRICTLY_POSITIVE_DENOMINATOR` | 59 | 309 |
| `REQUIRES_NONNEGATIVE_RATE` | 17 | 66 |
| `REQUIRES_PROBABILITY_IN_ZERO_ONE` | 12 | 40 |
| `REQUIRES_NONNEGATIVE_MAXIMUM_OR_ENVELOPE` | 22 | 116 |
| `REQUIRES_MONOTONE_CUMULATIVE_WEIGHT` | 31 | 80 |
| `SUPPORT_DOMAIN_CHECK_NOT_SIGN_SEMANTICS` | 4 | 12 |

Overall evidence-model totals are 146 call-site groups, 703 concrete members,
two boundary nodes, 16 pointer-role records, five unresolved-policy records,
and one signed-LHA policy-evidence record.

## Claim scope

The corrected evidence distinguishes six different statements:

1. Closure over the ten declared structured specifications is supported.
2. Declaration-derived recall expansion records all 105 prior findings, but
   15 `getXPDF` semantics remain unresolved.
3. Reachability is static source reachability, not runtime execution coverage.
4. Post-initialization identity/substitution of every PDF pointer remains a
   runtime-only unresolved policy question.
5. One PDF/hard/ISR/MPI alpha_s routing policy remains unresolved.
6. No runtime consumer coverage was performed or claimed.

Therefore this is not called a mathematically complete semantic audit.

The minimal-reader conclusion remains supported because confirmed reachable
hard-process, ISR, remnant, probability, maximum, and envelope paths already
require nonnegative sampling semantics.

The final-weight conclusion is deliberately qualified:

> For confirmed audited reachable paths, an external final event weight cannot
> repair a sign that already changed an internal selection probability, veto,
> channel or remnant choice, maximum, or envelope.

It is not generalized to unaudited or unresolved paths.

Support status is:

| Claim | Status |
|---|---|
| Declared structured-search closure | `SUPPORTED` |
| Mathematically complete semantic audit | `NOT_SUPPORTED` |
| Minimal public-reader patch is insufficient | `SUPPORTED` |
| Qualified final-weight claim | `SUPPORTED_WITH_QUALIFICATION` |
| Architecture-comparison readiness | `NOT_SUPPORTED` |

## Remaining unresolved evidence

- 15 `getXPDF` downstream paths still require static semantic classification;
- no accepted signed Markov/Sudakov replacement is specified;
- no accepted unbiased signed categorical-selection contract is specified;
- alpha_s routing remains a future policy question;
- runtime pointer identity/substitution remains unverified; and
- no runtime consumer coverage exists.

These limitations are visible and force `EVIDENCE_CORRECTION_REQUIRED`.

## Authorization boundary

Every authorization flag remains false:

```text
IMPLEMENTATION_AUTHORIZED=false
PROTOTYPE_AUTHORIZED=false
PYTHIA_INIT_AUTHORIZED=false
PYTHIA_NEXT_AUTHORIZED=false
EVENT_GENERATION_AUTHORIZED=false
DATASET_AUTHORIZED=false
SIGNED_WEIGHT_PROTOTYPE_AUTHORIZED=false
PYTHIA_FORK_AUTHORIZED=false
ALTERNATIVE_GENERATOR_AUTHORIZED=false
D2_AUTHORIZED=false
```

No architecture is selected.

## Static-only validation record

The phase completion validation is restricted to:

```text
python3 scripts/phase1bd_d1d_pythia_semantics_audit.py \
  --validate \
  --output-audit docs/phase1bd_d1d_pythia_semantics_audit.json \
  --output-search-manifest \
    docs/phase1bd_d1d_pythia_semantics_search_manifest.json

python3 -m json.tool \
  docs/phase1bd_d1d_pythia_semantics_audit.json >/dev/null

python3 -m json.tool \
  docs/phase1bd_d1d_pythia_semantics_search_manifest.json >/dev/null

python3 analysis/tests/test_d1d_semantics_audit.py
cargo fmt --all -- --check
git diff --check
```

All commands pass. No cargo test, cargo clippy, CTest, PYTHIA, APFEL, LHAPDF,
repository physics binary, event generation, dataset construction, observable
scan, or numerical physics evaluation is part of this validation.

## One next step

The next phase-scoped action is a separately reviewed static classification of
the 15 `getXPDF` paths. Do not begin architecture comparison, prototype work,
or D2 until the current D1D-A acceptance conditions pass.
