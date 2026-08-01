# ADR-009: AST-grounded PYTHIA PDF-consumer graph feasibility

- Status: Proposed
- Date: 2026-08-02
- Decision: `FEASIBLE_FOR_SEPARATE_STATIC_EVIDENCE_TASK`
- Operational policy: `PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION`

## Context

D1D-A failed at `provenance_evidence_integrity`. Its tokenizer-based provenance
slice remains a rejected diagnostic: it promoted ordinary uses and calls to
roots, attached historical members to global roots, emitted synthetic
root-to-unit edges, and lacked production interprocedural dataflow. D1D-B was
therefore `INCONCLUSIVE` and retained the non-authorizing pause.

This ADR asks a narrower planning question: can one future, independently
reviewed static-evidence task build a typed, source-backed consumer graph with
explicit completeness gates? It does not build that graph. No parser was
installed or run, no compilation database was generated, and no production
graph node or edge was created.

The immutable precedence remains:

```text
D1C_FINAL_DECISION = FAIL
MINIMAL_PUBLIC_READER_PATCH = INSUFFICIENT
PROVENANCE_SLICE_V1_DECISION = FAIL
PROVENANCE_SLICE_V1_STATUS = REJECTED_DIAGNOSTIC
D1D_A_FINAL_DECISION = FAIL
D1D_A_FAILED_GATE = provenance_evidence_integrity
D1D_B_FINAL_DECISION = INCONCLUSIVE
CURRENT_OPERATIONAL_POLICY = PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION
ARCHITECTURE_COMPARISON_READY = false
D2_AUTHORIZED = false
```

## Primary tooling evidence

The review used official documentation and source repositories only:

- LLVM/Clang LibTooling 18.1.8 documentation:
  <https://releases.llvm.org/18.1.8/tools/clang/docs/LibTooling.html>
- LLVM/Clang AST introduction 18.1.8:
  <https://releases.llvm.org/18.1.8/tools/clang/docs/IntroductionToTheClangAST.html>
- LLVM project tag `llvmorg-18.1.8`, peeled commit
  `3b5b5c1ec4a3095ab096dd780e84d7ab81f3d7ff`:
  <https://github.com/llvm/llvm-project>
- CMake `CMAKE_EXPORT_COMPILE_COMMANDS` documentation:
  <https://cmake.org/cmake/help/latest/variable/CMAKE_EXPORT_COMPILE_COMMANDS.html>
- CodeQL CLI and C/C++ dataflow documentation:
  <https://docs.github.com/en/code-security/codeql-cli> and
  <https://codeql.github.com/docs/codeql-language-guides/analyzing-data-flow-in-cpp/>
- CodeQL CLI v2.25.5 and query repository tag `codeql-cli/v2.25.5`, query
  commit `b551e89ea8e011c0e3301fd0ce05589c9f2d3681`:
  <https://github.com/github/codeql>
- Official PYTHIA release tag `pythia8312`, commit
  `cf0823ace0e2ebc2435f3f614e0926e9b381e21f`:
  <https://gitlab.com/Pythia8/releases>

LibTooling exposes the complete typed AST and source locations and consumes a
JSON compilation database. Those facts make the required relations
representable; they do not supply whole-program dataflow automatically.
Repository-owned, deterministic interprocedural normalization and fail-closed
unresolved states are still required.

## Candidate assessment

| Candidate | Identity | Technical result | Burden | Disposition |
|---|---|---|---:|---|
| LLVM/Clang LibTooling | 18.1.8, `llvmorg-18.1.8`, commit `3b5b5c1…` | Typed declarations, expressions, macro coordinates, call/parameter/return and field anchors are available. Dynamic targets and general aliases remain fail-closed. | 4.25 implementation weeks plus shared preparation/tests | Selected as feasibility reference only |
| Clang AST JSON / clang-query with normalizer | Same pinned Clang 18.1.8 | Emits typed syntax, but repository code must own still more cross-TU identity and dataflow normalization. AST emission alone is insufficient. | 6.5 graph weeks; near total cap | Technically possible, not preferred |
| CodeQL C/C++ | CLI 2.25.5; queries commit `b551e89…` | Official libraries provide local/global C++ dataflow, fields and pointer indirections. Models and dynamic closure still require review. | 5.0 graph weeks | Not selected: automated database creation under the downloaded CLI's standard terms and query/model stability complicate reproducible CI |

None of these executables was present in the inspected WSL environment or the
existing CI workflow. This is recorded availability evidence, not permission
to install one.

## Authoritative source and compile-command contract

The only future semantic corpus is the official PYTHIA 8.312 release tree at
`.external/src/releases-pythia8312`, pinned by tag, commit, archive URL, and
archive SHA-256. The exact inventory has 247 files: 127 headers and 120 core
`.cc` translation units. Its records and hashes are serialized in the JSON.
All 127 installed mirror headers were byte-identical; the installed mirror is
identity evidence only and must not produce duplicate nodes.

External plugins, examples, documentation, and non-C++ files are excluded with
explicit reasons. The fixed configuration uses C++11, the release `include`
directory, no added preprocessor definitions, no required generated core
header, and disabled external plugins/LHAPDF/HepMC/FastJet linkage. A path that
depends on an excluded module forces corpus expansion and review before any
completeness claim.

Upstream PYTHIA uses configure plus GNU Make rather than an upstream CMake
target that could directly emit `compile_commands.json`. A future task must
therefore build a repository-owned, source-only JSON Compilation Database over
the exact 120 translation units. Commands are argv arrays using pinned
`clang++` 18.1.8, C++11, upstream semantic flags, the release include path, and
`-fsyntax-only`. Paths use stable placeholders, entries are sorted by semantic
file ID, environment is restricted to `LC_ALL=C` and `TZ=UTC`, and command,
environment, compiler-binary, and release identities are hashed. Missing or
unparsable translation units fail closed. No link or generator execution is
needed.

## Graph contract

Roots may originate only in a typed declaration, definition, construction,
assignment, or installation coordinate. Required classes cover
`Pythia8::PDF` and derived providers, PDF pointer declarations/fields, all 16
BeamSetup roles, BeamParticle forwarders, public `xf`/`xfVal`/`xfSea`, provider
updates, caches, alpha_s routing, hard NC, ISR/backward evolution, remnants,
and LHA/complete-event-weight boundaries.

Identifier and filename roots, historical-member seeds, global
`xf`/`PDF`/`PDFPtr` fallback, and source-free synthetic roots are prohibited.
The 16 required roles are `pdfAPtr`, `pdfBPtr`, `pdfHardAPtr`, `pdfHardBPtr`,
`pdfPomAPtr`, `pdfPomBPtr`, `pdfGamAPtr`, `pdfGamBPtr`, `pdfHardGamAPtr`,
`pdfHardGamBPtr`, `pdfUnresAPtr`, `pdfUnresBPtr`, `pdfUnresGamAPtr`,
`pdfUnresGamBPtr`, `pdfVMDAPtr`, and `pdfVMDBPtr`.

The edge vocabulary is `DECLARES`, `HAS_STATIC_TYPE`, `POINTS_TO`,
`ASSIGNED_FROM`, `MAY_ALIAS`, `PASSED_AS_ARGUMENT`,
`RECEIVED_AS_PARAMETER`, `RETURNS`, `RETURN_VALUE_CONSUMED_BY`, `CALLS`,
`VIRTUAL_DISPATCH_CANDIDATE`, `READS_FIELD`, `WRITES_FIELD`, `CACHE_WRITE`,
`CACHE_READ`, `ARITHMETIC_DEPENDENCY`, `CONDITION_DEPENDENCY`,
`CATEGORICAL_SELECTION_DEPENDENCY`, `DENOMINATOR_DEPENDENCY`,
`MAXIMUM_OR_ENVELOPE_DEPENDENCY`, and `EVENT_WEIGHT_DEPENDENCY`.
Each future edge must serialize its exact coordinate, enclosing function or
declaration, endpoint static types, derivation rule, evidence state, and
translation-unit identity. A direct root-to-unit edge cannot stand in for a
dataflow path.

Aliases, virtual targets, function pointers, unmaterialized templates,
macro-generated uses, external boundaries, runtime providers, post-init
replacement, configuration-dependent reachability, missing translation units,
and parse failures have explicit unresolved states. Any such binding hard,
ISR, or remnant path blocks completeness.

## Static/runtime boundary

A static graph cannot prove the actual installed pointer, post-init
substitution, configuration-selected dynamic target, runtime query envelope,
or thread/process behavior. Those require separately authorized,
configuration-specific runtime identity, mutation, query-envelope, and
concurrency evidence. Runtime assertions cannot be substituted for a static
gate, and the static graph cannot by itself authorize issue #10 or D2.

Even a complete graph would not establish signed probability/rate validity or
signed Sudakov mathematics. Its scientifically material contribution would be
repairing source-backed consumer provenance and making the remaining
mathematical/runtime limitations explicit.

## Independent calibration and controls

The 672 historical source-reviewed members are a post-construction holdout.
They cannot seed identifiers, roots, edges, paths, reachability, or fallback.
Future results are `LOCALLY_RECOVERED`,
`EXPLICIT_BOUNDARY_OR_POLICY_EXEMPTION`, `UNRESOLVED`, or `NOT_RECOVERED`.
Global fallback, synthetic attachment, dangling calibration references, and
binding unresolved/not-recovered members must all be zero.

The negative controls are `state`, `size`, `id`, `push_back`, `p`, and `Vec4`.
An exact occurrence needs a typed source path; a common spelling or same-line
PDF expression is insufficient. An independent recall challenge must cover
neutral aliases, cross-function member/cache flow, parameters, returns,
references/pointers, templates, macros, virtual dispatch, and neutral helper
wrappers, with zero material misses and zero unresolved binding challenges.

## Binding acceptance gates

A future static evidence task may claim completeness only if all 18 gates pass:

1. authoritative corpus identity complete;
2. every required translation unit parsed;
3. exact compile-command replay deterministic;
4. typed roots complete;
5. no name-based or historical fallback;
6. every edge source-supported;
7. interprocedural argument/parameter/return flow implemented;
8. member/cache write-read flow implemented;
9. aliases and virtual targets resolved or explicitly blocking;
10. all 16 pointer roles accounted for locally;
11. alpha_s routing accounted for;
12. hard-process, ISR, and remnant paths represented;
13. holdout recovery has zero binding unresolved/not-recovered members;
14. negative controls pass;
15. independent recall challenge finds no material miss;
16. graph generation and serialization are deterministic;
17. an independent reviewer reproduces the result; and
18. runtime-only limitations are not represented as static closure.

These gates are not evaluated or passed by this planning ADR.

## Cost and stop conditions

The future implementation estimate is 7.0 person-weeks: 0.75 toolchain
preparation, 4.25 graph implementation, 0.25 corpus execution, 0.75 evidence
normalization, and 1.0 tests. The predeclared implementation cap is 8.0
person-weeks. Independent review is estimated and capped at 2.0 person-weeks.

Stop if a required translation unit cannot parse reproducibly, source-backed
interprocedural/member flow cannot fit the cap, calibration or the independent
challenge exposes an unbounded material miss, or the method degenerates into
name, filename, global, historical, or synthetic fallback. A negative future
result remains valid.

## Decision

`FEASIBLE_FOR_SEPARATE_STATIC_EVIDENCE_TASK` is selected because one immutable
toolchain is identifiable, the source and compile-command strategies are
exact, the required relations are technically representable, runtime limits
and stop conditions are explicit, and implementation/review fit the caps.

`INCONCLUSIVE` is not selected because source, build, toolchain, relation, and
cost information are sufficient to bound the separate evidence task.
`DO_NOT_PROCEED` is not selected because the proposed method is not merely a
more elaborate lexical search: it can produce typed, coordinate-backed,
interprocedural evidence if every gate passes.

This decision is feasibility only. LLVM/Clang acquisition, parser or graph
implementation, generator work, a prototype, architecture comparison, issue
#10, and D2 are not authorized. All ten authorization flags remain false.
Issue #42 stays closed, issue #45 remains open planning work, and issue #10
stays open and blocked.

## Next step

Review ADR-009 and the v1 feasibility artifact. Only a later explicit decision
may create a separately scoped static-evidence implementation task. That
review is not implementation authorization.
