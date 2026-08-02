# ADR-009: AST-grounded PYTHIA PDF-consumer graph feasibility

- Status: Proposed
- Proposed decision: `INCONCLUSIVE`
- Preferred feasibility candidate: `LLVM_CLANG_LIBTOOLING_18_1_8`
- Selected toolchain: `null`
- Compile-contract status: `SOURCE_INSPECTION_CORRECTED_BUT_PARSE_NOT_VALIDATED`
- Implementation-cost bound: `NOT_SUPPORTED`
- Operational policy: `PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION`

## Context and precedence

The rejected tokenizer provenance slice did not establish a complete,
source-backed PDF-consumer graph. A typed AST approach remains scientifically
relevant to the failed `provenance_evidence_integrity` gate, but the previous
v1 `FEASIBLE_FOR_SEPARATE_STATIC_EVIDENCE_TASK` result depended on incomplete
compile commands, shallow decision predicates, and an unsupported cost bound.
Because PR #46 remains draft, that v1 planning result is superseded rather than
preserved as an immutable scientific result.

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

All ten implementation, prototype, generator, event, dataset, and D2
authorization flags remain false.

## Corrected decision

The v2 artifact derives `INCONCLUSIVE` because:

```text
AST_GRAPH_APPROACH_REMAINS_SCIENTIFICALLY_RELEVANT
CURRENT_IMPLEMENTATION_SCOPE_NOT_CREDIBLY_BOUNDED
COMPILE_CONTRACT_NOT_YET_SUPPORTED
IMPLEMENTATION_NOT_AUTHORIZED
```

The corpus identity is supported and LLVM is a plausible typed-AST
foundation, so `DO_NOT_PROCEED` would overstate the negative evidence. LLVM is
only a preferred feasibility candidate. It is not selected, and this ADR does
not authorize acquisition, installation, execution, or implementation.

## Tool identities and evidence boundaries

LLVM/Clang remains pinned to release `llvmorg-18.1.8`, peeled commit
`3b5b5c1ec4a3095ab096dd780e84d7ab81f3d7ff`, under Apache-2.0 with the LLVM
exception.

The corrected CodeQL identities are:

- CLI tag `v2.25.5`, official tag identity
  `697ca25a6968ae01bab1b11ae56c3be5960f588c`;
- query tag `codeql-cli/v2.25.5`, peeled commit
  `b551e89ea8e011c0e3301fd0ce05589c9f2d3681`.

The versioned CodeQL terms permit some automated analysis for OSI-licensed
codebases hosted and maintained on GitHub.com. Applicability to this repository
has not been established because no reviewed root OSI-license identity exists.
CodeQL therefore remains unselected because repository-specific licensing,
deployment, and query/model stability remain unresolved. This is not a
universal prohibition on CodeQL database generation in CI.

For the LLVM feasibility reference, responsibilities are separated:

- `CLANG_AST_DIRECTLY_PROVIDES`: typed declarations/expressions, spelling and
  expansion coordinates, materialized template instances, call/parameter/
  return AST anchors, and field/member anchors.
- `REPOSITORY_ANALYSIS_MUST_IMPLEMENT`: cross-TU identity, ODR reconciliation,
  overload/specialization identity, argument/parameter and return/caller flow,
  member/cache flow, points-to propagation, closed virtual-target sets, and
  deterministic serialization.
- `STATIC_ANALYSIS_CANNOT_PROVE`: runtime-selected concrete targets, post-init
  pointer replacement, actual query envelopes, general alias closure, and
  thread/process behavior.

## Authoritative source and portable lineage

The authoritative corpus remains the official PYTHIA 8.312 release:

- tag `pythia8312`;
- commit `cf0823ace0e2ebc2435f3f614e0926e9b381e21f`;
- archive SHA-256
  `c1a33aa5fa15e6b70d7946ce6d237246842887ec84ea0b35dfc2535c868a2770`;
- 247 files: 127 headers and 120 core translation units.

The independent audit reproduced the archive and found zero path, byte-size,
or hash mismatches. Installed mirror headers remain identity evidence only and
cannot become duplicate semantic nodes.

Clean CI source validation is exactly:

```text
PORTABLE_MANIFEST_VALIDATION_ONLY
```

The committed D1D manifest stores file paths, sizes, and hashes. D1E filters it
into the 247-file inventory. Ignored local release bytes are checked only when
that checkout exists; clean CI skips the comparison, does not retrieve the
official archive, and does not independently resolve the tag or commit. Clean
CI therefore proves committed-manifest and artifact reproducibility, not
independent upstream byte identity.

## Corrected compile-command contract

The future command model is common arguments plus deterministic per-TU
overrides. The only project include root remains
`${PYTHIA_SOURCE_ROOT}/include`, but system headers are also required.

Mandatory source-inspected overrides include:

```text
Pythia.cc:
  -DXMLDIR="<PINNED_SHARE_ROOT>/xmldoc"

FJcore.cc:
  -DFJCORE_HAVE_LIMITED_THREAD_SAFETY
```

`XMLDIR` is used unconditionally in `Pythia.cc`; the FJcore definition changes
the upstream core build semantics. Thus the v1 claims of no preprocessor
definitions and one sufficient argv template were false.

The bounded textual inspection found zero generated core-header dependencies
and zero includes escaping the authoritative root. Its three apparent missing
`fastjet/internal/Dnn*Cylinder.hh` includes are in the branch disabled by
`__FJCORE_DROP_CGAL`, defined in `Pythia8/FJcore.h`.

No parser ran, no `compile_commands.json` was created, and actual parse success
is not claimed. Reconstructing and reviewing the exact 120-TU command inventory
remains future work.

## Expanded acceptance contract

The v2 JSON binds 25 machine-oriented contract sections:

1. exact graph-node schema;
2. source evidence for every node kind;
3. stable cross-TU symbol identity;
4. overload identity;
5. template specialization/instantiation identity;
6. duplicate declaration and ODR reconciliation;
7. formal graph-path validity;
8. allowed edge composition;
9. static reachability semantics;
10. prospective configuration policy;
11. exclusion relevance proof;
12. external-call boundary policy;
13. callback/function-pointer policy;
14. material-miss definition;
15. boundary/policy exemption review;
16. macro spelling/expansion identity;
17. closed-world virtual-target conditions;
18. neutral wrapper/registration discovery;
19. graph-size/resource caps;
20. timeout/truncation behavior;
21. overall unresolved-record cap;
22. zero unresolved hard/ISR/remnant paths;
23. independent-reviewer definition;
24. blinded holdout procedure; and
25. machine predicates for every gate.

Each of the existing 18 gates now references applicable contract sections and
names its own future predicate. These definitions are binding, but none of the
future schemas, algorithms, or predicates has been implemented or evaluated;
the acceptance-contract condition is consequently
`SUPPORTED_WITH_QUALIFICATION`, not `SUPPORTED`.

## Cost challenge

The original 7.0-person-week estimate is retained only as historical planning
metadata and classified `NOT_CREDIBLE`. The independent work-breakdown
challenge gives:

| Range | Implementation | Independent reproduction |
|---|---:|---:|
| Optimistic | 76 days / 15.2 weeks | 5 days / 1 week |
| Nominal | 153 days / 30.6 weeks | 10 days / 2 weeks |
| Pessimistic | 287 days / 57.4 weeks | 15 days / 3 weeks |

Therefore:

```text
implementation_cap_8_person_weeks = NOT_SUPPORTED
independent_review_cap_2_person_weeks = SUPPORTED_WITH_QUALIFICATION
```

These ranges are a feasibility challenge, not precise scheduling commitments.

## Decision derivation and boundary

The validator independently binds tool identities and claims, source identity,
compile arguments, candidate capability matrices, lineage, cost breakdown,
acceptance definitions, gates, calibration, controls, runtime limitations,
scientific limitations, dependencies, and authorization boundaries. It then
recomputes 17 feasibility conditions and derives the decision. Whole-artifact
byte equality remains a second generator-consistency layer.

`INCONCLUSIVE` follows because the compile contract is only source-corrected,
relation/acceptance implementation remains unevaluated, and the implementation
cost bound is not supported. A correct graph could still provide evidence for
`provenance_evidence_integrity`; it would not solve signed-rate or Sudakov
mathematics, runtime pointer identity, generator compatibility, issue #10, or
D2.

## Next step

Review the corrected v2 feasibility and acceptance contract. Only a later
explicit decision may authorize a separately scoped static-evidence task.
Issue #45 remains open planning work, issue #42 remains closed, and issue #10
and D2 remain blocked. This next step is not implementation authorization.
