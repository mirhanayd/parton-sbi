# ADR-003: event sampling semantics

Status: Experiment required

Date: 2026-07-28

## Context

Phase 1A found a severe Pythia generator-weight tail. Direct regeneration
removes the failed PDF-member reuse path but does not by itself turn weighted
generator output into ordinary i.i.d. event sets.

The first inference target must distinguish normalized shape information from
event-rate information. Changing Pythia phase-space maxima after accepted
events, clipping weights, or overwriting them would alter or obscure the
sampling measure.

## Decision

The primary MVP experiment is a second-stage fixed-envelope accept-reject
procedure:

1. use an independent calibration seed family;
2. freeze a documented upper bound `M` before production;
3. generate direct weighted candidates with disjoint seeds;
4. accept each candidate with probability `w/M` using an independent RNG;
5. fail the complete shard on a negative/non-finite weight or any `w > M`;
6. retain the source weight, probability, random draw, and envelope identity
   as provenance.

The method is not accepted until Stage 4 proves the Pythia weight semantics,
zero bound violations, and agreement of unweighted observables with
independent weighted and direct-replica references. The bound is never raised
after inspecting a production stream.

The initial event-set contract is fixed-`N` and shape-only:

```text
p(event | theta, declared selection).
```

Cross sections and veto rates are diagnostics, not observed model features.
A future rate-aware extension may draw Poisson event counts at a predeclared
luminosity, but it is deferred.

## Consequences

- Candidate generation cost grows as approximately `1/efficiency`.
- A failed envelope or distribution test invalidates a shard and may reject
  the method.
- Weighted samples remain an independent validation reference.
- No large corpus or neural stage is authorized until the experiment and
  resource pilot pass.
- A negative sampling result is scientifically valid and requires a new ADR.

## Rejected and deferred alternatives

- Weight clipping, winsorization, magnitude-based removal, and overwriting are
  rejected.
- Pythia's dynamic `PhaseSpace:increaseMaximum` behavior is rejected for the
  MVP.
- Nominal-pool reuse and cross-point resampling are rejected.
- Weighted empirical sets as the primary neural representation are deferred.
- Poisson rate-aware sets are deferred.

## Validation

Stage 4 of `../AMORTIZED_INFERENCE_PHASE1BD_ACCEPTANCE.md` is binding. Until it
passes, this ADR records a hypothesis to test rather than an approved sampling
implementation.

## Revisit conditions

Revisit the sampling decision when the Stage 4 experiment finds a bound breach,
unproven source-weight semantics, unacceptable efficiency, or distribution
failure. The replacement requires a new ADR that preserves source weights and
separates shape and rate; it cannot restore nominal-pool reuse or introduce
post-hoc clipping.
