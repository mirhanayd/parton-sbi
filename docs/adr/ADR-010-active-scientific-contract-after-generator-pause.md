# ADR-010: Active scientific contract after generator-coupling pause

- Status: Proposed
- Scope: Phase 1B-D1F planning only
- Current-line disposition: `TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING`
- Preferred separate contract review: `LOWER_LEVEL_DIS_HARD_EVENT_MODEL`
- Lower-level normalized-measure status: `PASS_WITH_QUALIFICATION`

## Immutable precedence

The following merged results remain unchanged:

```text
D1C_FINAL_DECISION = FAIL
MINIMAL_PUBLIC_READER_PATCH = INSUFFICIENT
PROVENANCE_SLICE_V1_DECISION = FAIL
PROVENANCE_SLICE_V1_STATUS = REJECTED_DIAGNOSTIC
D1D_A_FINAL_DECISION = FAIL
D1D_A_FAILED_GATE = provenance_evidence_integrity
D1D_B_FINAL_DECISION = INCONCLUSIVE
D1E_FINAL_DECISION = INCONCLUSIVE
D1E_PREFERRED_FEASIBILITY_CANDIDATE = LLVM_CLANG_LIBTOOLING_18_1_8
D1E_SELECTED_TOOLCHAIN = null
CURRENT_OPERATIONAL_POLICY = PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION
ARCHITECTURE_COMPARISON_READY = false
D2_AUTHORIZED = false
```

The D0R family, strict support, signed binary64 `x*f`, no clipping, fixed-N
shape-only initial objective, and set-level target `p(theta_PDF | D)` remain
scientific evidence. Preserving that objective does not require preserving a
failed implementation line.

## Two independent decision axes

D1F v2 separates two questions that v1 overloaded:

1. Does the current D0R signed full-generator coupling line have a justified,
   accepted, and credibly bounded continuation?
2. Which separate prospective scientific contract deserves a bounded planning
   review?

A separate redesign can be scientifically promising without continuing or
completing the current generator line. Its preference grants no implementation
authorization.

## Current-line evidence and disposition

The validator derives the current-line evidence statuses from serialized,
source-bound D1D/D1E claims:

| Evidence field | Status |
|---|---|
| Full-generator architecture ready | `NOT_SUPPORTED` |
| Bounded static-evidence path exists | `NOT_SUPPORTED` |
| Bounded signed-kernel path exists | `NOT_SUPPORTED` |
| Bounded alternative-generator path exists | `NOT_SUPPORTED` |
| Accepted generator measure exists | `NOT_SUPPORTED` |
| Accepted runtime consumer closure exists | `NOT_SUPPORTED` |
| Implementation task credibly bounded | `NOT_SUPPORTED` |
| Current contract preserved by continuation | `NOT_SUPPORTED` |
| Redesigns are separate contracts | `SUPPORTED` |

Every accepted or bounded continuation field is `NOT_SUPPORTED`; every
redesign is explicitly separate; all historical evidence is preserved; and no
global impossibility is claimed. Therefore:

```text
D1F_CURRENT_LINE_DISPOSITION =
  TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING
```

This terminates only the current Phase 1B D0R signed full-generator coupling
line. It does not reject PDF SBI, D0R evidence, lower-level simulators,
alternative families, weighted statistical contracts, or future reviewed
decisions.

## Normalized-measure gates

| Option | Gate | Reason |
|---|---|---|
| A. Preserve current contract and pause | `PASS_WITH_QUALIFICATION` | The probability law and posterior are conceptually defined but no accepted simulator instantiates them. |
| B. New nonnegative family | `PASS_WITH_QUALIFICATION` | A conventional law is conceptually possible, but family motivation, evolution-wide positivity, support, and generator proofs are absent. |
| C. Lower-level hard-event model | `PASS_WITH_QUALIFICATION` | The mathematical form is plausible, but formulae, support, positivity, normalization, detector response, and closure remain future obligations. |
| D. Weighted empirical event set | `PASS_WITH_QUALIFICATION` | Positive weights can define an empirical measure only after a proposal, weight, posterior, loss, ESS, and calibration contract. |
| E. Signed-weight inference research | `FAIL` | No positive normalized data law or coherent posterior exists. |
| F. Terminate current line | `NOT_APPLICABLE` | Termination proposes no new probability law. |

Gate transitions use exact semantic enums. The validator does not infer
qualification from substrings.

## Lower-level mathematical claim scope

Option C proposes only the form

```text
z ~ p_theta(z)
y ~ K(y | z)
D = {y_i}_{i=1}^N

p_theta(z) =
  1_A(z) d_sigma_theta/dz
  / integral_A d_sigma_theta/dz dz
```

It is not yet a formal or executable simulator contract. The following remain
`NOT_EVALUATED` proof obligations:

1. exact electron and positron neutral-current differential formula;
2. F2, FL, and xF3 conventions and signs;
3. gamma, Z, and interference terms;
4. electroweak parameter scheme;
5. factorization and renormalization scales;
6. flavor and heavy-quark treatment;
7. phase-space coordinates and Jacobian;
8. finite, nonzero normalization for every accepted theta;
9. nonnegative complete differential rate on accepted support;
10. strict PDF-support intersection;
11. detector/acceptance-kernel normalization;
12. perfect-detector identity-kernel special case;
13. independent numerical closure; and
14. explicit omitted-physics declaration.

The prospective contract omits ISR, parton showering, hadronization,
underlying event, and beam remnants. It cannot claim full-generator
equivalence.

## Separate-review prioritization

For each redesign, the validator derives thirteen statuses from option fields,
criterion-level evidence, and supersession records: measure, posterior,
representation, weights, calibration, no clipping, supersession, bounded
review, MVP path, objective change, scientific motivation, implementation
boundedness, and validation boundedness.

| Separate review | Eligible | Binding reason |
|---|:---:|---|
| New nonnegative family | No | MVP, implementation, validation, and scientific motivation are unavailable; objective-change risk is not supported. |
| Lower-level hard-event model | Yes | All review-critical statuses are supported or qualified; omissions and supersession are explicit; implementation readiness is not claimed. |
| Weighted empirical event set | No | Calibration and MVP path are unavailable, and objective-change risk is not supported. |
| Signed-weight inference research | No | The normalized measure, posterior, weights, calibration, and MVP path are not supported. |

Thus:

```text
D1F_PREFERRED_SEPARATE_CONTRACT_REVIEW =
  LOWER_LEVEL_DIS_HARD_EVENT_MODEL
```

This preference is a planning priority, not continuation of the terminated
line and not authorization.

## Criterion-specific scorecards

Every one of the 120 option/criterion cells records a unique
criterion-specific rationale, evidence IDs, claim keys, current-line
implication, and separate-review implication.

| Option | Supported | Qualified | Not supported | Unavailable | N/A |
|---|---:|---:|---:|---:|---:|
| A. Preserve and pause | 7 | 7 | 5 | 1 | 0 |
| B. New nonnegative family | 5 | 9 | 2 | 4 | 0 |
| C. Lower-level hard-event model | 8 | 12 | 0 | 0 | 0 |
| D. Weighted empirical set | 2 | 12 | 1 | 5 | 0 |
| E. Signed-weight research | 2 | 5 | 8 | 5 | 0 |
| F. Terminate current line | 8 | 1 | 0 | 0 | 11 |

Changing a score without its curated evidence claim, reusing a generic
rationale, or exceeding a cited source's claim scope fails validation.

## Supersession

Current-line termination prospectively supersedes or closes issue #10's
current full-generator D2 scope and prospectively supersedes the current
full-generator D2-D5 roadmap.

The preferred lower-level review independently:

- preserves ADR-001, ADR-004, and D0R;
- requires explicit confirmation of ADR-003 fixed-N shape-only semantics;
- prospectively supersedes ADR-002 and ADR-006 full-generator requirements;
- does not complete issue #10; and
- requires a new Neural-phase decision.

All D0R, D1, D1R, D1C, D1D, and D1E negative or qualified results remain
historical evidence.

## Top-level decision

The top-level field represents the primary current-line disposition:

```text
decision = TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING
preferred_separate_contract_review = LOWER_LEVEL_DIS_HARD_EVENT_MODEL
```

The separate preference does not prevent or reverse termination.

## Authorization boundary

```text
LOWER_LEVEL_SIMULATOR_AUTHORIZED = false
EVENT_GENERATION_AUTHORIZED = false
DATASET_AUTHORIZED = false
NEURAL_TRAINING_AUTHORIZED = false
D2_AUTHORIZED = false
```

All other implementation and prototype authorization fields are also false.
Issue #10 and D2 remain blocked during this draft.

## Static validation and next step

The deterministic validator recomputes both decision axes, all gates, all
separate-review eligibility fields, score totals, supersession effects, the
top-level decision, and authorization state. The focused suite has 29 tests,
including 22 direct adversarial mutations.

The only next step is planning review of the fourteen formal lower-level
contract obligations. No implementation, numerical closure, generator, event,
dataset, neural, or D2 work is authorized by that review.
