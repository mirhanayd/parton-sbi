# ADR-012: Reduced NC DIS research direction after the full-generator pause

- Status: Proposed
- Scope: Phase 2 roadmap and Phase 2A planning only
- Decision: `KEEP_IN_PARTON_SBI`
- Scientific gate: `NOT_EVALUATED`
- Implementation authorization: false

## Context

The high-level objective remains set-level inference of continuous PDF
deformations from unbinned DIS event sets, with target
`p(theta_PDF | D)`. The legacy full-generator line remains
`PAUSED_NO_BOUNDED_CONTINUATION_ESTABLISHED`, issue #10 remains open and
blocked, and legacy D2 remains unauthorized.

After the immutable Phase 1B closeout, the user explicitly authorized a new
planning-only line based on an explicit, normalized, detector-aware reduced NC
DIS observation model. Phase 2 is independent of legacy D2 and does not alter
any accepted Phase 1 decision or closeout identity.

## Decision

Keep the new line in `parton-sbi` as a monorepo with an independent research
namespace. The operational observation law is

```text
z_i ~ p_theta(z)
y_i ~ K(y | z_i)
D = {y_i}_{i=1}^N

p_theta(z) =
  1_A(z) [d sigma_theta / dz]
  / integral_A [d sigma_theta / dz] dz
```

The baseline is fixed-N, shape-only, unbinned, set-level, detector-aware
amortized posterior inference. The paper scope is proof-of-principle
methodology under the declared reduced model.

## Claims and nonclaims

Later validated work may claim a normalized NC DIS observation law,
continuous-deformation set-level amortized inference, a normalized detector
kernel, and calibration and repeated-sampling coverage under the reduced model.

It may not claim full PYTHIA equivalence; showering; ISR; hadronization;
beam-remnant or underlying-event modelling; complete collider realism;
production-grade detector simulation; unrestricted full-flavor PDF
determination; replacement of a global PDF fit; legacy D2 completion; or
full-generator closure.

## Dependencies

```text
Phase2A -> Phase2B -> Phase2C -> Phase2D -> Phase2E -> Phase2F -> Phase2G
                                                        |
                                                        +-> Phase2H
```

Phase 2H is optional and does not block Phase 2G.

## Repository boundary

The planned namespaces are `src/reduced_nc_dis/`,
`analysis/reduced_nc_dis/`, and `tests/reduced_nc_dis/`. They are not created by
this decision. Files appear only after the corresponding phase receives
separate authorization, and no preferred implementation architecture is
selected here.

A separate `reduced-dis-sim` repository may be proposed only if the simulator
becomes useful outside PartonSBI, needs an independent public API and semantic
versioning, gains multiple downstream consumers, needs its own release and
governance cycle, or becomes scientifically independent of PDF posterior
inference. No split is authorized.

## Consequences and authorization

This ADR authorizes the roadmap, documentation, validators, mathematical
specification, and Phase 2A primary-source contract review only. A later
accepted Phase 2A contract is required before any code proposal. Even a Phase
2A PASS would authorize only a separate Phase 2B proposal.

This ADR does not validate the observation law, discharge any proof
obligation, evaluate physics formulae, or authorize implementation, numerical
closure, events, datasets, detector simulation, neural training, or legacy D2.
