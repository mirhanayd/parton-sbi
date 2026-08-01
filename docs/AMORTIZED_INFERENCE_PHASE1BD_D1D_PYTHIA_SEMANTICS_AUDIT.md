# Phase 1B-D1D-A final negative static-evidence report

## Final decisions and boundary

```text
D1C_FINAL_DECISION = FAIL
MINIMAL_PUBLIC_READER_PATCH = INSUFFICIENT
PROVENANCE_SLICE_V1_DECISION = FAIL
PROVENANCE_SLICE_V1_STATUS = REJECTED_DIAGNOSTIC
D1D_A_FINAL_DECISION = FAIL
failed_gate = provenance_evidence_integrity
ARCHITECTURE_COMPARISON_READY = false
D2_AUTHORIZED = false
```

All ten authorization flags remain false. PR #43 remains open and draft;
issue #10 and D2 remain blocked. No architecture comparison, implementation,
prototype, generator patch, or later phase is authorized.

This finalization records a failed evidence prototype. It does not attempt a
new parser, AST, root-discovery pass, provenance algorithm, dataflow engine, or
manual review of the 867 serialized units.

## Artifact precedence and identity

The final decision artifact has
`EVIDENCE_INTEGRITY_FAIL_PRECEDENCE`. The broad manifest and rejected slice are
kept byte-identical as historical evidence:

| Artifact | Schema | SHA-256 | Role |
|---|---|---|---|
| Broad search manifest | `partonsbi.phase1bd.d1d.pythia-semantics-search-manifest.v3` | `e381a6774a17306336ebb016f152b611e9b66c4628e5c3835cc93efb5a9dc701` | Supported deterministic syntactic replay |
| Provenance slice | `partonsbi.phase1bd.d1d.pythia-pdf-provenance-slice.v1` | `6641d6e2fb615780819bd957be2f942eab5f78f34828073eb66078088ef708c7` | Deterministic rejected diagnostic prototype |
| Provenance decision | `partonsbi.phase1bd.d1d.pythia-provenance-slice-decision.v1` | `b872647ba1073e07262e95ceb70efe7c81c1165718b8d078867bf1e7918cf590` | Terminal integrity decision |
| Semantics audit | `partonsbi.phase1bd.d1d.pythia-semantics-audit.v6` | `6022f377da6f9993e0d5e4966a6e23f65e3facea23f2b37675725198c5197163` | Final D1D-A negative record |

Audit v5 is retained by identity in the decision artifact at SHA-256
`bfbe2020cffcfa3084f8109267c4e2ac2be2f165546fbdd9df35ecdde33b76ce`.
Audit v6 references the broad manifest, rejected slice, and final decision by
path, schema, and hash.

## Supported results that survive the provenance failure

The broad syntactic search remains valid within its declared meaning:

```text
source files              = 374
searched identifiers      = 779
broad raw occurrences     = 67,375
P10 occurrences           = 63,763
authoritative replay      = exact deterministic equality
```

Deterministic JSON regeneration also remains supported. Neither establishes a
typed dependency graph.

The immutable D1C result remains `FAIL`. The minimal public-reader patch remains
`INSUFFICIENT` independently of provenance slice v1. That conclusion rests on
the retained direct source-reviewed evidence that internal hard-process, ISR,
remnant, probability, denominator, maximum, envelope, veto, and cumulative
selection operations consume nonnegative PDF-derived quantities before an
external final event weight could act. Audit v6 preserves all 672 direct
source-reviewed members and all 66 curated denominator dispositions.

Modified/forked-generator and alternative-generator possibilities remain not
reviewed; the provenance failure neither rejects nor authorizes them.

## Why provenance slice v1 failed

The independent integrity review reproduced the serialized totals—939 roots,
867 units, 1,841 nodes, and 1,221 edges—but rejected their scientific
interpretation.

### Root integrity

| Finding | Count |
|---|---:|
| Syntactically confirmed roots | 720 |
| Ordinary uses promoted to roots | 162 |
| Call sites promoted to roots | 43 |
| Unresolved roots | 14 |
| Misclassified or unresolved | 219 |
| Owner fields containing function symbols | 401 |
| Generic rather than recovered declared types | 722 |
| Reachability flags assigned by symbol/path substrings | 939 |

Consequently, category non-emptiness is not proof of root completeness or
typing. Reachability flags are heuristic diagnostics, not final configuration
or call-path evidence.

### Construction-circular historical calibration

With global `xf`, `PDF`, and `PDFPtr` recovery disabled:

```text
LOCAL_TYPED_RECOVERED             = 0
FALLBACK_XF_PDF_PDFPTR_ONLY       = 669
NOT_RECOVERED                     = 3
```

The three dangling members are `CSG034.M006`, `CSG034.M007`, and
`CSG034.M014`. All other historical paths select the same global `class PDF`
root at `PartonDistributions.h:49`. Historical members are inserted before
recovery is measured, historical names seed discovery, the same global-root
selection assigns recovery status, and the v1 validator did not check the
calibration unit references. The prior 672/672 figure is therefore a rejected,
construction-circular diagnostic—not independent recovery.

### Graph and edge support

All 867 paths have length two. There are zero explicit multi-edge production
dataflow paths. The rejected graph contains 669 historical global-root
attachments, 103 synthetic root-to-unit paths, and 35 unresolved dynamic/alias
paths.

Production has zero `ASSIGNED_FROM`, `PASSED_AS_ARGUMENT`,
`RECEIVED_AS_PARAMETER`, `FORWARDED_TO`, `CALLS`, or `MAY_ALIAS` edges; zero
cache write/read chains; and zero caller-return propagation. Fixture behavior
does not establish corpus production support.

| Edge support finding | Count |
|---|---:|
| Source-supported | 314 |
| Source supports target only | 33 |
| Synthetic root attachment | 658 |
| Wrong edge kind | 181 |
| Unresolved support | 35 |

The v1 endpoint/enum/nonempty-file checks were insufficient to validate the
source meaning of an edge.

### Occurrence and recall integrity

Coordinate-level attribution admitted 209 same-line unrelated occurrences and
11 declaration/comment occurrences. Negative-control wrong dispositions
included four `state` and 28 `id` occurrences.

The outside-slice challenge found 46 legitimate missed provenance occurrences
at 32 coordinates and 189 provenance-unresolved occurrences at 139
coordinates. Therefore 62,050 is retained only as the rejected prototype's
outside disposition count; it is not a proven scientific exclusion total.

### getXPDF and validator soundness

The 35 `getXPDF` lexical occurrences comprise four mirrored inline wrapper
definitions and 31 direct calls, normalizing to 33 semantic source units after
mirror deduplication. They remain scientifically unresolved. Treating all 35
as separate unresolved dynamic targets is not supported.

Seven of eight adversarial fixtures were incorrectly accepted by v1. The
accepted defects covered global fallback recovery, ordinary-use roots,
unsupported root-to-unit edges, unresolved recovery, category-nonempty
completeness, same-line contamination, and fixture-only interprocedural
support. Only deterministic serialized drift was rejected.

## Failed gates and removed claims

The terminal failed gates are:

```text
typed_root_integrity
local_provenance_recovery
graph_path_support
edge_source_support
historical_calibration_independence
occurrence_disposition_integrity
outside_slice_recall
reachability_evidence
validator_soundness
getxpdf_normalization
```

Audit v6 removes v1 readiness conditions and does not claim that all roots are
typed, paths establish dataflow, historical evidence was independently
recovered, outside occurrences were scientifically excluded, negative controls
prove occurrence attribution, or the 163 machine units form a valid review
queue. The v1 totals remain only under
`REJECTED_DIAGNOSTIC_NOT_READINESS_EVIDENCE`.

## Static-only validation

```text
python3 scripts/phase1bd_d1d_pythia_semantics_audit.py \
  --validate \
  --output-audit docs/phase1bd_d1d_pythia_semantics_audit.json \
  --output-search-manifest \
    docs/phase1bd_d1d_pythia_semantics_search_manifest.json

python3 scripts/phase1bd_d1d_pythia_pdf_provenance_slice.py --validate

python3 scripts/phase1bd_d1d_pythia_provenance_decision.py --validate

python3 -m json.tool docs/phase1bd_d1d_pythia_semantics_audit.json >/dev/null
python3 -m json.tool \
  docs/phase1bd_d1d_pythia_semantics_search_manifest.json >/dev/null
python3 -m json.tool \
  docs/phase1bd_d1d_pythia_pdf_provenance_slice.json >/dev/null
python3 -m json.tool \
  docs/phase1bd_d1d_pythia_provenance_slice_decision.json >/dev/null
python3 -m pytest -q analysis/tests/test_d1d_semantics_audit.py
cargo fmt --all -- --check
git diff --check
```

These checks are static only. The frozen broad-manifest and provenance-slice
hashes are verified before and after validation.

| Check | Result |
|---|---|
| Semantics audit replay/validator | PASS; 374 files, 779 searched identifiers, 67,375 raw occurrences, exact set/order equality |
| Rejected historical slice identity validator | PASS; deterministic serialized identity only, not scientific acceptance |
| Final provenance decision validator | PASS; ten failed gates and all authorization flags false |
| Four `json.tool` parses | PASS |
| Focused Python tests | PASS; 42 passed |
| `cargo fmt --all -- --check` | PASS |
| `git diff --check` | PASS |

The WSL system Python did not provide pytest, so pytest 9.1.1 was installed to
an isolated `/tmp` target and exposed through `PYTHONPATH` only for the exact
`python3 -m pytest` invocation. No repository or system package was changed.

## Next step

```text
SCIENTIFIC_REVIEW_AND_MERGE_NEGATIVE_D1D_A_RECORD
```

This is a review/merge step for the negative record, not authorization for
architecture comparison or another prototype. Issue #10 remains blocked and
D2 remains unauthorized.
