# Phase 1B-D1 revision audit

## Outcome

```text
D1_REVISION_DECISION = SELECTED
D1_REVISION_IMPLEMENTATION_AUTHORIZED = true
D2_AUTHORIZED = false
```

This audit does not implement the selected revision. It preserves the original
Stage 1 `FAIL` and authorizes only a separately reviewed revised-D1
implementation and revalidation.

## Provenance

- D1 merge commit:
  `c9c8de68c8192309e98bcaf538a8b06e8749f10d`
- original implementation:
  `1a7181ad1582029aa93cf743807c24e18a147704`
- original study:
  `phase1bd_d1_apfel_lhapdf_artifact_v1_20260728`
- transport diagnostic:
  `phase1bd_d1r_transport_diagnostic_v1_20260728`
- official LHAPDF source:
  tag `lhapdf-6.5.6`, commit
  `92239ac82134be698805c1002b4615e5167c6fa3`

Temporary diagnostic source, generated artifacts, and full numerical scans
remained ignored and are not part of this report commit.

## Commands

The audit used the normal WSL environment and baseline commands:

```bash
source scripts/pythia_env.sh
cargo fmt --all -- --check
cargo check --workspace
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
analysis/venv/bin/python -m pytest analysis/tests
ctest --test-dir physics-engine/build --output-on-failure
git diff --check
```

Temporary ignored diagnostics compiled against the installed APFEL++ 4.8.0
and LHAPDF 6.5.6 libraries. They compared all nine anchors, independently
implemented LHAPDF's documented log-bicubic equations, varied APFEL
computational grids, and decomposed raw/public/projected evolution.

## Findings

### Serialization

The writer is correct. It follows official x-outer/Q-inner ordering, increasing
PDG flavor order, unsquared file Q, and 17-digit scientific formatting. Every
anchor had zero exact-knot failures. The center maximum absolute difference
was `3.1763735522036263e-22`.

Independent log-bicubic reconstruction matched LHAPDF with zero D1-tolerance
failures. The maximum absolute implementation difference over all anchors was
`1.0913936421275139e-11`.

### Subgrids and interpolation

Distributed CT18NLO member 0 has one 161 x 37 Q subgrid and no duplicate Q
knots. The D1 artifact has one 161 x 39 Q block after adding charm and top
knots.

The center has 56,793 off-knot failures. Only 4,969 lie in the declared
threshold neighborhood; 51,824 occur elsewhere. The gluon worst case is
`13.676177930319682` at `x=1.0635741629054353e-9`,
`Q=71852.27901743959 GeV`.

Threshold segmentation alone is not a numerical cure. Combined one-level x/Q
refinement reduces the maximum to `4.013933338614152` and the failure fraction
from 20.89% to 13.35%, still a decisive failure.

### Evolution and sum rules

At fixed computational/exported `xmin=1e-9`, APFEL node, degree, and subgrid
transition changes do not remove the high-Q residual. Center APFEL-native and
independent maximum residuals are both about `5.46e-5`.

With zero boundary input below `1e-9` and computational `xmin=1e-11`, the
doubled-node independent maximum is `8.3769066461236719e-7` at center and
`6.4815101532555985e-6` at delta-min. At `Q=100000 GeV`, evolved momentum
below exported support is `5.4194349993874624e-5` and
`6.2578836954374495e-5`, respectively.

The original sum-rule failure therefore conflates full evolution conservation
with finite exported-support retention. Both quantities must be reported, but
only full computational-domain conservation is a sum-rule gate.

### Raw CT18 fidelity

Raw CT input evolved by APFEL has 8,529 values outside the old pointwise rule
relative to public CT18. Projecting the boundary changes that to 8,532. The
projected and raw-boundary APFEL evolutions have zero values outside the same
rule. D0 projection is not the cause.

Only 161 of the 8,529 failures use the near-zero absolute branch. Failures span
threshold, low-, mid-, and high-Q regions. Universal pointwise identity to a
PDF fitted and evolved by another implementation is not a defensible gate.

### Physical observable

The existing compact check is the LO photon charge-weighted F2 expression
evaluated with evolved PDFs. It has no coefficient functions or FL and is not
full neutral-current gamma/Z validation.

The revised binding contract uses the repository's APFEL++ NLO zero-mass
photon-exchange F2 and FL construction, comparing direct distributions with
the same distributions loaded through the artifact.

## Selected revision

ADR-005 selects:

- APFEL computational support to `1e-11`, with exact zero boundary input below
  the exported `1e-9` support;
- base and doubled-node convergence;
- independent full-domain moments as binding;
- explicit retained-support and below-support moment accounting;
- charm/bottom-separated LHAPDF Q subgrids;
- bounded deterministic error-driven x/Q refinement;
- unchanged direct-APFEL/artifact pointwise tolerances;
- raw CT18 pointwise fidelity as mandatory diagnostic; and
- binding direct/artifact APFEL++ NLO photon-exchange F2/FL closure.

## Alternatives

One global dense subgrid is inefficient and crosses thresholds. A custom
direct-APFEL Pythia PDF or separate validation/generator representations would
abandon the accepted same-artifact contract. Reducing support changes the
scientific domain. Changing the engine or baseline is not justified by the
diagnosed failures.

## Limitations

- The selected observable remains photon exchange, not gamma/Z.
- The audit did not implement or validate the proposed refined artifacts.
- APFEL `Distribution::Integrate` shows resolution sensitivity near the fixed
  gate; independent quadrature is therefore binding in the proposal.
- The selected refinement may hit its complexity cap. That would be an honest
  revised-D1 FAIL, not permission to alter the rule.

## Next step

Scientifically review ADR-005. If accepted, implement and revalidate only the
revised D1 contract tracked by issue #30. D2 remains unauthorized.
