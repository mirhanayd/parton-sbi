# Phase 1B-D1D-A2 typed PDF-provenance slicing report

## Completion status and boundary

This phase adds a conservative static PDF-provenance slice over the complete
PYTHIA 8.312 occurrence corpus. It does not execute PYTHIA, APFEL, LHAPDF, a
repository physics binary, `Pythia::init()`, or `Pythia::next()`. It creates no
events or datasets, performs no observable scan or numerical physics work,
selects no architecture, authorizes no prototype, and does no D2 work.

The preserved decisions are:

```text
D1C_FINAL_DECISION = FAIL
MINIMAL_PUBLIC_READER_PATCH = INSUFFICIENT
D1D_A_RESULT = EVIDENCE_CORRECTION_REQUIRED
```

All ten authorization flags remain false. Issue #10 and D2 remain blocked, and
PR #43 remains open and draft.

## Three evidence layers

The evidence now keeps three meanings separate:

1. `BROAD_SYNTACTIC_OCCURRENCE_CORPUS` is the immutable authoritative search:
   779/779 derived identifiers, 67,375 raw occurrences, and 63,763 independent
   P10 candidates.
2. `PDF_PROVENANCE_SLICE` contains source statements connected to a typed PDF
   provider, accessor, cache, pointer installation, or propagated PDF-derived
   value by a source-supported edge.
3. `SOURCE_REVIEWED_SCIENTIFIC_EVIDENCE` contains only curated semantic and
   reachability conclusions. Machine slicing never promotes a unit to this
   layer.

The prior 63,674 machine-unreviewed count arose because the broad vocabulary
deliberately contains generic C++ identifiers such as `state`, `size`, `id`,
`push_back`, `p`, and `Vec4`. It is a syntactic recall corpus, not a PDF
dependency graph, and it is not a coordinate-level manual-review queue.

## Artifact identity

| Artifact | Schema | SHA-256 |
|---|---|---|
| Broad search manifest | `partonsbi.phase1bd.d1d.pythia-semantics-search-manifest.v3` | `e381a6774a17306336ebb016f152b611e9b66c4628e5c3835cc93efb5a9dc701` |
| Audit (v4 to v5) | `partonsbi.phase1bd.d1d.pythia-semantics-audit.v5` | `bfbe2020cffcfa3084f8109267c4e2ac2be2f165546fbdd9df35ecdde33b76ce` |
| PDF-provenance slice | `partonsbi.phase1bd.d1d.pythia-pdf-provenance-slice.v1` | `6641d6e2fb615780819bd957be2f942eab5f78f34828073eb66078088ef708c7` |

The v3 manifest retains its byte-identical schema, hash, source inventory, and
`PYTHON_REGEX_OCCURRENCE_ENGINE_V1` meaning. The v5 audit binds both other
artifacts by path, schema, and SHA-256.

## Static analyzer and typed roots

WSL contained no Clang, ctags, or tree-sitter executable. The selected allowed
approach is the repository-owned conservative tokenizer
`PARTON_SBI_CPP_PROVENANCE_TOKENIZER_V1` version `1.0.0`, used by slice
algorithm `PARTON_SBI_TYPED_PDF_PROVENANCE_SLICE_V1`. It masks comments and
strings, uses brace-tracked function ranges, derives declarations and
definitions from the installed source, and records exact coordinates. It does
not infer types, aliases, overloads, templates, macros, or dynamic targets from
spelling alone; unsupported cases remain unresolved.

The 939 source-derived typed roots are:

| Root category | Count |
|---|---:|
| `PDF_PROVIDER_TYPE` | 46 |
| `PDF_PROVIDER_POINTER` | 37 |
| `PDF_PROVIDER_FIELD` | 168 |
| `PDF_ACCESSOR_METHOD` | 155 |
| `BEAM_PDF_FORWARDER` | 62 |
| `PDF_DERIVED_CACHE` | 274 |
| `PDF_COUPLING_ACCESSOR` | 2 |
| `CONFIGURATION_POINTER_INSTALLATION` | 114 |
| `EXPLICIT_EVENT_OR_LHA_WEIGHT_BOUNDARY` | 81 |

Each root records its declared type, owning class/namespace, coordinate,
direct-source rationale, prospective-HERA status, disabled-source capability,
and unresolved reachability status. The graph serializes every required node
and edge kind; kinds absent from directly established corpus edges have count
zero rather than invented evidence. It contains 1,841 nodes and 1,221 edges,
with zero unexplained edges and 35 explicitly unresolved dynamic/alias edges.

## Broad-corpus dispositions and review units

Every P10 occurrence has exactly one occurrence-level structural disposition:

| Disposition | Count |
|---|---:|
| `CONTRIBUTES_TO_PROVENANCE_UNIT` | 699 |
| `ROOT_DECLARATION_OR_DEFINITION` | 619 |
| `OUTSIDE_PDF_PROVENANCE_SLICE` | 62,050 |
| `DUPLICATE_OCCURRENCE_OF_SAME_UNIT` | 352 |
| `DYNAMIC_OR_ALIAS_PROVENANCE_UNRESOLVED` | 43 |

The graph normalizes admitted expressions and paths into 867 scientific review
units rather than one unit per lexical identifier:

| Materiality | Count |
|---|---:|
| `PDF_PROVENANCE_CONFIRMED` | 832 |
| `PDF_PROVENANCE_POSSIBLE` | 0 |
| `PROVENANCE_UNRESOLVED` | 35 |
| `OUTSIDE_PDF_PROVENANCE_SLICE` | 0 |

| Review state | Count |
|---|---:|
| `SOURCE_REVIEWED_MATERIAL` | 669 |
| `MACHINE_SLICED_UNREVIEWED` | 163 |
| `POLICY_UNRESOLVED` | 35 |
| all other allowed reviewed states | 0 |

Thus 62,050 broad occurrences are structurally removed from scientific review.
The 163 machine-sliced confirmed units and 35 unresolved units remain blocked;
machine slicing assigns neither a final scientific semantic class nor final
HERA reachability.

## Calibration and controls

All 672 retained final-evidence members are
`RECOVERED_BY_PROVENANCE_SLICE`; `NOT_RECOVERED=0` and
`RECOVERY_UNRESOLVED=0`. The prior 90-finding baseline reconciles as 31
recovered dataflow findings and 59 boundary/policy findings not expected in
dataflow. Its separate 15 `getXPDF` baseline remains `RECOVERY_UNRESOLVED`.
All 16 provider-pointer records are root-accounted; both boundary records are
explicit exemptions; policy records contain two boundary exemptions and three
explicit unresolved policies.

The 35 lexical `getXPDF` occurrences normalize to 35 unresolved units. They
record declarations, definitions, calls/downstream uses, provider/caller
context, and unresolved dynamic targets, but receive no final scientific
classification.

Generic-name negative controls reconcile exactly:

| Identifier | Broad | Admitted with root path | Structurally excluded | Unresolved |
|---|---:|---:|---:|---:|
| `state` | 6,003 | 4 | 5,999 | 0 |
| `size` | 4,563 | 0 | 4,563 | 0 |
| `id` | 3,932 | 46 | 3,882 | 4 |
| `push_back` | 3,198 | 6 | 3,192 | 0 |
| `p` | 3,130 | 0 | 3,130 | 0 |
| `Vec4` | 2,824 | 0 | 2,824 | 0 |

Every admitted generic occurrence carries an explicit root path. No generic
identifier is admitted merely because it is common or appears on a root line.

## Derived readiness

| Readiness condition | Actual result |
|---|---|
| broad authoritative occurrence replay passes | `true` |
| provenance-slice generation is deterministic | `true` |
| all broad occurrences have one structural disposition | `true` |
| all PDF roots are accounted for | `true` |
| historical final evidence has zero `NOT_RECOVERED` | `true` |
| zero unexplained graph edges | `true` |
| zero unresolved material provenance units | `false` |
| zero machine-sliced material units awaiting review | `false` |
| zero unresolved `getXPDF` units | `false` |
| final reviewed evidence has valid coordinates and ownership | `true` |
| zero heuristic-only final semantic/reachability results | `true` |
| all authorization flags false | `true` |

The broad 63,674 machine-occurrence count is no longer a readiness input once
each occurrence has a structural disposition. The three false normalized-unit
conditions derive:

```text
D1D_A_RESULT = EVIDENCE_CORRECTION_REQUIRED
```

The minimal public reader patch remains `INSUFFICIENT` based only on retained
source-reviewed internal sampling consumers; the conclusion is not generalized
to machine-sliced units.

## Static-only validation record

The exact allowed checks are:

```text
python3 scripts/phase1bd_d1d_pythia_semantics_audit.py \
  --validate \
  --output-audit docs/phase1bd_d1d_pythia_semantics_audit.json \
  --output-search-manifest \
    docs/phase1bd_d1d_pythia_semantics_search_manifest.json

python3 scripts/phase1bd_d1d_pythia_pdf_provenance_slice.py \
  --validate \
  --input-audit docs/phase1bd_d1d_pythia_semantics_audit.json \
  --input-search-manifest \
    docs/phase1bd_d1d_pythia_semantics_search_manifest.json \
  --output docs/phase1bd_d1d_pythia_pdf_provenance_slice.json

python3 -m json.tool docs/phase1bd_d1d_pythia_semantics_audit.json >/dev/null
python3 -m json.tool \
  docs/phase1bd_d1d_pythia_semantics_search_manifest.json >/dev/null
python3 -m json.tool \
  docs/phase1bd_d1d_pythia_pdf_provenance_slice.json >/dev/null
python3 -m pytest -q analysis/tests/test_d1d_semantics_audit.py
cargo fmt --all -- --check
git diff --check
```

These checks are static only. No native physics validation is relevant or
permitted for this evidence-framework task.

## Unresolved limitations and one next step

The tokenizer deliberately leaves 35 dynamic/alias graph edges and the 35
`getXPDF` units unresolved. Source review is still required for 163 normalized
machine-sliced confirmed units plus the unresolved units. Runtime PDF-pointer
identity and alpha_s routing remain policy-deferred. There is no runtime
consumer coverage.

The one next phase-scoped action is source review of the normalized provenance
units, including the unresolved `getXPDF`, alias, pointer, and policy paths.
Do not begin architecture comparison, prototype work, issue #10, or D2 until
the D1D-A acceptance conditions pass.
