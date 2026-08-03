# ADR-010: Active scientific contract after generator-coupling pause

- Status: Proposed
- Scope: Phase 1B-D1F planning only
- Proposed decision: `RECOMMEND_LOWER_LEVEL_HARD_EVENT_CONTRACT_REVIEW`
- Implementation authorization: `false`

## Context and immutable precedence

The accepted PartonSBI objective is set-level inference,
`p(theta_PDF | D)`. The D0R family remains an accepted, versioned,
sum-rule-projected two-parameter boundary family with signed binary64 `x*f`,
strict support, and no clipping. The initial data contract is a fixed-N,
shape-only set of observed events.

The fixed attempt to realize that contract through a complete generator has no
bounded next task. D1C is `FAIL`; the minimal public-reader patch is
`INSUFFICIENT`; provenance slice v1 is `FAIL` and
`REJECTED_DIAGNOSTIC`; D1D-A is `FAIL` at
`provenance_evidence_integrity`; D1D-B and D1E are `INCONCLUSIVE`.
LLVM/Clang 18.1.8 is only D1E's preferred feasibility candidate, no toolchain
is selected, architecture comparison is not ready, and D2 is unauthorized.

Those results are historical evidence. This decision neither deletes nor
upgrades them.

## Decision method

The v1 decision artifact defines six complete scientific contracts, scores
each against twenty criteria, records a target-by-option supersession matrix,
and derives each normalized-measure gate. A redesign may enter the final
selection only if it has:

- a normalized data-generating probability measure and coherent posterior;
- an explicit event/set and weight representation;
- calibration semantics and strict no-clipping behavior;
- prospective supersession rather than silent contract drift;
- a bounded next decision;
- a credible end-to-end scientific MVP path; and
- an objective change whose risk is lower than alternatives or explicitly
  scientifically justified.

The validator recomputes those conditions from the serialized contracts and
scorecards. The recommendation is not stored as an independent policy switch.

## Option A: preserve the current contract and pause

This option preserves D0R, signed values, strict support, fixed-N shape-only
sets, full hard-process/ISR/remnant consistency, and the original posterior.
Its normalized-measure gate is `PASS`: the target law and posterior are
coherent as a contract. They are not operational because no accepted complete
generator instantiates them.

The option has no bounded next action. D1E's AST route is not credibly bounded,
and signed internal-rate mathematics and alternate interfaces remain separate
evidence decisions. Continued pause is scientifically honest but dominated by
the bounded lower-level contract review below.

## Option B: new nonnegative generator-compatible family

This would be a prospectively new family and theta contract, never a
correction to D0R. D0R would remain immutable historical evidence. The new
family would require nonnegative evolved densities over the complete consumer
domain, positivity-preserving interpolation, exact sum rules, explicit
support, a new identity, and independent APFEL and generator validation.

Its gate is `PASS_WITH_QUALIFICATION`: a conventional normalized generator law
and posterior can be stated conditionally. The scientific motivation is not
established. Requiring an NLO family to be pointwise nonnegative merely to fit
generator internals risks replacing a physics family with a software-driven
prior. Evolution-wide positivity, theta design, and end-to-end validation are
also unbounded. It is not recommended.

## Option C: lower-level neutral-current DIS hard-event model

This option retains D0R and theta while prospectively replacing the full-
generator transport requirement with a normalized lower-level law. A future
contract must specify:

- incoming electron/positron and proton states;
- the complete neutral-current gamma, Z, and interference contribution;
- PDF dependence, flavor summation, scales, phase space, and Jacobian;
- a finite accepted cross section and its normalization;
- an explicit detector response/acceptance kernel;
- fixed-N exchangeable shape-only sampling;
- strict PDF and phase-space support;
- event identity, posterior, training, and calibration definitions; and
- every omitted effect, including parton showers, hadronization, underlying
  event, and beam remnants.

For declared acceptance `A`, the planning law is the nonnegative differential
hard-event measure divided by its finite integral over `A`. A fixed-N set is
drawn from the resulting normalized detector-level density and the posterior
is proportional to the prior times that set likelihood. Signed perturbative
components may cancel before forming the physical rate; they are never used as
sampling probabilities.

The gate is `PASS`. The contract is a lower-level scientific model, not full-
generator equivalence. If later accepted, it would prospectively supersede
ADR-002/ADR-006 full-generator transport, issue #10's current D2 scope, and
the dependent D2-D5 roadmap. It would not complete issue #10. Its first step
is a bounded mathematical contract review, not implementation.

## Option D: weighted empirical event set

Positive normalized weights can define a random empirical probability
measure, but that object is not an ordinary iid unweighted event set. A valid
contract would require the proposal law, weight functional, normalization,
candidate count, ESS, rate/shape split, posterior, proper loss, resampling,
calibration, coverage, and deployment representation. Signed weights do not
pass as probabilities.

The gate is `PASS_WITH_QUALIFICATION`. The producer law, proper training loss,
and repeated-sampling calibration remain unresolved, and the option would
prospectively supersede ADR-003's primary fixed-N unweighted objective. It has
higher scientific-objective change risk and no credible end-to-end producer
path, so it is not recommended.

## Option E: signed-weight inference research

A signed finite sample is currently an estimator, not a normalized positive
data law. No coherent posterior, proper loss, or calibration/coverage target
has been established. Negative MC@NLO weights do not establish that signed
event sets are inference distributions.

The gate is `FAIL`. This remains potentially valuable mathematical research,
but it is open-ended and cannot be selected as implementation planning.

## Option F: terminate the current Phase 1B generator-coupling line

Termination would be scoped to the fixed D0R signed full-generator route. It
would not claim that PDF SBI, all generators, lower-level models, or changed
contracts are impossible. Its measure gate is `NOT_APPLICABLE` because it
defines no new data law.

The current full-generator route is unbounded, but Option C supplies a bounded,
scientifically motivated separate contract review. Termination is therefore
not selected at this planning point.

## Scorecard result

Legend: S = `SUPPORTED`, Q = `SUPPORTED_WITH_QUALIFICATION`, N =
`NOT_SUPPORTED`, U = `PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE`, A =
`NOT_APPLICABLE`.

| Option | S | Q | N | U | A |
|---|---:|---:|---:|---:|---:|
| A preserve and pause | 9 | 7 | 4 | 0 | 0 |
| B new nonnegative family | 5 | 11 | 2 | 2 | 0 |
| C lower-level hard-event law | 10 | 10 | 0 | 0 | 0 |
| D weighted empirical set | 2 | 13 | 1 | 4 | 0 |
| E signed-weight research | 2 | 5 | 8 | 5 | 0 |
| F terminate current line | 8 | 1 | 0 | 0 | 11 |

The machine-readable artifact contains all 120 criterion cells and their
scope-specific rationales.

## Proposed decision

The sole redesign satisfying the normalized-measure, posterior, no-clipping,
prospective-supersession, bounded-next-decision, credible-MVP, and justified-
objective-change conditions is:

```text
RECOMMEND_LOWER_LEVEL_HARD_EVENT_CONTRACT_REVIEW
```

This is a planning recommendation. It does not authorize a simulator,
implementation, PDF change, event generation, dataset, neural training, or
D2.

## Static validation

The phase-scoped record is validated with:

```text
python3 scripts/phase1bd_d1f_active_contract_decision.py --validate
python3 -m json.tool docs/phase1bd_d1f_active_contract_decision.json >/dev/null
python3 -m pytest -q analysis/tests/test_d1f_active_contract_decision.py
cargo fmt --all -- --check
git diff --check
```

All commands pass. The focused suite contains 20 tests, including the 15
required adversarial mutations. The unresolved scientific limitations remain
the absence of an accepted complete generator law, the lower-level model's
not-yet-reviewed matrix element/phase-space/detector details, and the explicit
omission of ISR, hadronization, and remnants. No numerical physics validation
was run or implied.

## Consequences and next step

Issue #10 remains open, blocked, and unauthorized under its existing full-
generator scope. D2 remains unauthorized. A later acceptance of a lower-level
contract would require an explicit new roadmap decision and would supersede,
not complete, that scope.

The exact next step is scientific review of a planning-only lower-level NC DIS
hard-event contract: normalized gamma/Z/interference measure, phase space,
detector kernel, omissions, posterior, calibration, and independent validation
gates. No implementation belongs in that review.

All twelve authorization flags in the v1 artifact are `false`.
