# ADR-013: Source-backed Reduced NC DIS observation-law contract

## Status

Proposed

## Context

Phase 2A defined the mathematical and scientific contract for the Reduced NC
DIS observation model using primary or authoritative source evidence. The
review binds the selected-event law, posterior target, paper claim boundary,
and the gates that must pass before any later numerical closure phase can be
authorized.

PR #63 merged the Phase 2A source-backed contract review. The accepted
machine-readable decision is conservative: Phase 2A is complete, but its final
scientific decision is `INCONCLUSIVE`.

## Primary-Source Methodology

Every load-bearing claim relies on authoritative references or repository facts
recorded in the source registry and claim ledger. Missing primary evidence is
not converted into support.

## Exact Contract

- Formula: Standard NC DIS differential cross section.
- Electroweak scheme: `G_F` scheme.
- Perturbative scheme: NLO VFNS remains incompletely bound for the full
  heavy-flavor contract.
- PDF family: accepted CT18NLO Phase 1a strict-support family boundary.

## Selected-Event Law

The accepted baseline is a selected-event, fixed-`N`, shape-only observation
law. Count/rate information is not part of the Phase 2A baseline.

## Posterior Law

The posterior target is `p(theta | D, N, selected)` for an event set `D`, not an
instantaneous single-proton PDF inferred from one event.

## Gate Summary

The accepted Phase 2A gate grouping is:

- `SUPPORTED`: `posterior_target_coherence`,
  `fixed_n_shape_only_semantics`, `paper_claim_boundary_consistency`,
  `selected_event_conditioning_coherence`.
- `SUPPORTED_WITH_QUALIFICATION`:
  `finite_positive_normalization_reviewability`, `strict_support_contract`,
  `normalized_detector_kernel_contract`,
  `bounded_identifiability_and_information_plan`.
- `PRIMARY_EVIDENCE_UNAVAILABLE`: `exact_formula_contract`,
  `no_hidden_clipping`, `bounded_phase2b_validation_plan`.

The unresolved `exact_formula_contract` includes the `CLAIM_HEAVY_FLAVOR`
limitation: the review does not bind a single complete, internally consistent
heavy-flavor scheme from primary evidence. The full differential-rate
positivity premise is therefore not established by Phase 2A.

## Decision Derivation

Because required primary evidence remains unavailable, the final Phase 2A
scientific decision is `INCONCLUSIVE`.

This is neither a PASS nor a FAIL. It is a completed conservative review result
that blocks Phase 2B authorization until the missing evidence and validation
plan details are addressed by a later reviewed decision.

## Phase 2B Boundary

The Phase 2B proposal remains:

- `plan_completeness = INCOMPLETE`
- `authorization = NOT_AUTHORIZED`
- `execution_status = NOT_EXECUTED`

Anchors, grids, tolerances, convergence rules, and independent-reference
details remain unresolved. No Phase 2B numerical work is authorized by this
ADR or by the Phase 2A closeout.

## Nonclaims

The bounded paper nonclaims remain in force. The review does not claim
full-generator equivalence, showering, ISR, hadronization, beam-remnant
modelling, underlying event, full collider realism, production-grade detector
simulation, unrestricted full-flavor determination, global-fit replacement,
universal identifiability, guaranteed contraction for every theta direction,
legacy D2 completion, or full-generator closure.

## Authorization

- `PHASE2A_CONTRACT_REVIEW_AUTHORIZED = true`
- `PHASE2B_AUTHORIZED = false`
- `NUMERICAL_PHYSICS_AUTHORIZED = false`
- `IMPLEMENTATION_AUTHORIZED = false`
- `D2_AUTHORIZED = false`

## Consequences

Phase 2A is closed as a completed source-backed contract review with an
`INCONCLUSIVE` scientific decision. Phase 2B issue #55 remains Backlog,
Not Evaluated, and Not Authorized.
