# ADR-010: Active scientific contract after generator-coupling pause

- Status: Proposed
- Scope: Phase 1B-D1F planning only
- Schema: `partonsbi.phase1bd.d1f.active-contract-decision.v3`
- Current-line disposition: `MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE`
- Preferred separate contract review: `NONE`
- Lower-level candidate: `PLAUSIBLE_SEPARATE_REVIEW_CANDIDATE_REQUIRES_INDEPENDENT_EVIDENCE`

## Immutable precedence

```text
D1C_FINAL_DECISION = FAIL
MINIMAL_PUBLIC_READER_PATCH = INSUFFICIENT
PROVENANCE_SLICE_V1_DECISION = FAIL
PROVENANCE_SLICE_V1_STATUS = REJECTED_DIAGNOSTIC
D1D_A_FINAL_DECISION = FAIL
D1D_A_FAILED_GATE = provenance_evidence_integrity
D1D_B_FINAL_DECISION = INCONCLUSIVE
D1E_FINAL_DECISION = INCONCLUSIVE
D1E_SELECTED_TOOLCHAIN = null
ARCHITECTURE_COMPARISON_READY = false
D2_AUTHORIZED = false
```

The D0R family, strict support, signed binary64 `x*f`, no clipping, fixed-N
shape-only initial objective, and set-level target `p(theta_PDF | D)` remain
scientific evidence. No result above is reopened or weakened.

## Correction of the unmerged v2 proposal

The unmerged v2 draft proposed termination of the current line and uniquely
preferred a lower-level DIS review. The independent integrity audit rejected
both derivations. V2 was never merged and is not an immutable scientific
result.

The corrected v3 record separates direct evidence, explicit inference,
unevaluated propositions, and prospective hypotheses. It does not convert
missing evidence into affirmative incompatibility and does not use this ADR
as independent evidence for its own recommendation.

## Current-line evidence

| Proposition | Status | Evidence class |
|---|---|---|
| Full-generator architecture ready | `NOT_SUPPORTED` | `DIRECT_IMMUTABLE_EVIDENCE` |
| Bounded static-evidence path exists | `NOT_SUPPORTED` | `DIRECT_IMMUTABLE_EVIDENCE` |
| Bounded signed-kernel path exists | `NOT_SUPPORTED` | `DIRECT_IMMUTABLE_EVIDENCE` |
| Bounded alternative-generator path exists | `NOT_EVALUATED` | `NOT_EVALUATED` |
| Accepted generator measure exists | `NOT_SUPPORTED` | `EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE` |
| Accepted runtime consumer closure exists | `NOT_SUPPORTED` | `DIRECT_IMMUTABLE_EVIDENCE` |
| Implementation task credibly bounded | `NOT_SUPPORTED` | `DIRECT_IMMUTABLE_EVIDENCE` |
| Current contract preserved by continuation | `NOT_EVALUATED` | `NOT_EVALUATED` |
| Redesigns are separate contracts | `SUPPORTED` | `EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE` |

D1D leaves Architecture C, Sherpa, and Herwig possible with evidence gaps. It
does not establish a bounded alternative path, but it also does not establish
that no such path can exist. No immutable source establishes that every
continuation fails to preserve the current contract. Both propositions
therefore remain `NOT_EVALUATED`.

The accepted-measure proposition is an explicit inference from the absence of
an accepted generator architecture, reviewed signed internal-rate
construction, and completed normalized generator measure. It is not
represented as a verbatim D1D result.

## Two independent axes

Continuation requires supported mandatory foundations and at least one
supported bounded path. Termination requires every mandatory continuation
proposition to be affirmatively `NOT_SUPPORTED` by direct immutable evidence
or a reviewed explicit inference. Any mandatory `NOT_EVALUATED` proposition
retains the pause.

Therefore:

```text
D1F_CURRENT_LINE_DISPOSITION =
  MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE

D1F_PREFERRED_SEPARATE_CONTRACT_REVIEW =
  NONE

D1F_TOP_LEVEL_DECISION =
  MAINTAIN_CURRENT_CONTRACT_AND_PAUSE
```

The current-line axis does not depend on a separate-review preference, and a
prospective candidate cannot reopen or authorize the current line.

## Scorecard evidence model

Every one of the 120 cells records its option and criterion identity,
epistemic status, rationale, evidence class, source bindings, explicit
inference, decision implications, load-bearing status, and historical audit
classification.

Each binding is limited to an exact option and criterion and records the
maximum supported status. Criterion-wide source membership no longer implies
support for every option. ADR-010 is limited to decision-record definition,
explicit-inference recording, and contract description; it cannot be the sole
evidence for motivation, detector feasibility, MVP feasibility, or unique
preference.

Historical audit correction totals are:

| Direct | Qualified | Misbound | Unsupported | Overstated | Not applicable |
|---:|---:|---:|---:|---:|---:|
| 17 | 30 | 53 | 8 | 1 | 11 |

After correction the evidence classes are 17 direct immutable cells, 30
explicit-inference cells, 62 prospective hypotheses, and 11 not-applicable
cells. Prospective hypotheses are not load-bearing for disposition or unique
preference.

## Normalized-measure gates

| Option | Gate |
|---|---|
| Preserve current contract and pause | `PASS_WITH_QUALIFICATION` |
| New nonnegative family | `PASS_WITH_QUALIFICATION` |
| Lower-level NC DIS hard-event model | `PASS_WITH_QUALIFICATION` |
| Weighted empirical event set | `PASS_WITH_QUALIFICATION` |
| Signed-weight inference research | `FAIL` |
| Termination option | `NOT_APPLICABLE` |

## Lower-level candidate

The lower-level option retains the conceptual form

```text
z ~ p_theta(z)
y ~ K(y | z)
D = {y_i}_{i=1}^N

p_theta(z) =
  1_A(z) d_sigma_theta/dz
  / integral_A d_sigma_theta/dz dz
```

Its reviewability is `INCOMPLETE_BUT_REVIEWABLE`, but independent evidence
does not establish its scientific motivation, end-to-end MVP, or unique
priority. Its status is:

```text
D1F_LOWER_LEVEL_CANDIDATE_STATUS =
  PLAUSIBLE_SEPARATE_REVIEW_CANDIDATE_REQUIRES_INDEPENDENT_EVIDENCE
```

The following fourteen obligations remain `NOT_EVALUATED`:

1. exact e− and e+ neutral-current differential formula;
2. F2, FL, and xF3 conventions and signs;
3. gamma, Z, and interference terms;
4. electroweak parameter scheme;
5. factorization and renormalization scales;
6. flavor and heavy-quark treatment;
7. phase-space coordinates and Jacobian;
8. finite nonzero normalization for every accepted theta;
9. complete-rate nonnegativity;
10. strict PDF-support intersection;
11. detector/acceptance-kernel normalization;
12. perfect-detector identity-kernel special case;
13. independent numerical closure; and
14. explicit omitted-physics declaration.

No obligation is discharged or authorized. The candidate omits ISR,
parton showering, hadronization, underlying event, and beam remnants and does
not claim full-generator equivalence.

## Active policy and roadmap

```text
ACTIVE_OPERATIONAL_POLICY =
  PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION

CURRENT_FULL_GENERATOR_LINE =
  PAUSED_NO_BOUNDED_CONTINUATION_ESTABLISHED

LOWER_LEVEL_CONTRACT_REVIEW =
  PLAUSIBLE_BUT_NOT_PREFERRED_OR_AUTHORIZED
```

Issue #10 remains open, blocked, not evaluated, and not authorized. D2 remains
blocked; D3-D5 retain their existing backlog states. No roadmap supersession
is active.

If Option C were separately accepted in the future, it would require
prospective treatment of ADR-002 and ADR-006, explicit confirmation of
ADR-003, a new roadmap decision, and a new Neural decision. These are
hypothetical consequences, not active supersession. ADR-001, ADR-004, D0R,
and every historical negative result remain preserved. A lower-level model
cannot complete issue #10.

## Authorization boundary

```text
LOWER_LEVEL_SIMULATOR_AUTHORIZED = false
EVENT_GENERATION_AUTHORIZED = false
DATASET_AUTHORIZED = false
NEURAL_TRAINING_AUTHORIZED = false
D2_AUTHORIZED = false
```

All other implementation, prototype, family-redesign, weighted-objective,
signed-weight, and PYTHIA authorization flags are also false.

## Next step

The only next action is a planning-only independent-evidence review of whether
any separate contract deserves priority. It is not implementation and does
not discharge Option C's mathematical obligations. No parser, generator,
event, dataset, numerical closure, neural, prototype, issue #10, or D2 work is
authorized.
