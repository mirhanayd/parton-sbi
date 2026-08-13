# Phase 2 reduced NC DIS roadmap

Phase 2 is an independent research line in `parton-sbi`. It does not supersede
the legacy roadmap, complete issue #10, or authorize legacy D2.

## Dependency graph

```text
Phase2A
  -> Phase2B
  -> Phase2C
  -> Phase2D
  -> Phase2E
  -> Phase2F
  -> Phase2G

Phase2F
  -> Phase2H
```

Phase 2H is optional and does not block Phase 2G.

| Phase | Issue | Planned purpose | Status | Authorization |
|---|---:|---|---|---|
| Phase2 | #53 | Umbrella and claim boundary | In Progress | Planning Only |
| Phase2A | #54 | Define the observation-law contract | Done | Completed / INCONCLUSIVE |
| Phase2B | #55 | Formula and normalization closure | Backlog | Not Authorized |
| Phase2C | #56 | Normalized latent-event sampler | Backlog | Not Authorized |
| Phase2D | #57 | Detector response kernel | Backlog | Not Authorized |
| Phase2E | #58 | Fixed-N set-level SBI proof of principle | Backlog | Not Authorized |
| Phase2F | #59 | Calibration, coverage, and robustness | Backlog | Not Authorized |
| Phase2G | #60 | Reproducible methodology paper package | Backlog | Not Authorized |
| Phase2H | #61 | Optional rate-inclusive extension | Backlog | Not Authorized |

Every implementation phase requires a later, explicit authorization after its
predecessor's binding acceptance criteria pass. Phase 2A did not PASS; it is a
completed source-backed review with final scientific decision `INCONCLUSIVE`.
Phase 2B remains Backlog, Not Evaluated, and Not Authorized.

## Phase 2A closeout

PR #63 merged at `e798a64265afd806bb7030218e2fac60e1656a78`, and issue #54 is
closed/completed. Phase 2A's accepted gate grouping is:

- `SUPPORTED`: `posterior_target_coherence`,
  `fixed_n_shape_only_semantics`, `paper_claim_boundary_consistency`,
  `selected_event_conditioning_coherence`.
- `SUPPORTED_WITH_QUALIFICATION`:
  `finite_positive_normalization_reviewability`, `strict_support_contract`,
  `normalized_detector_kernel_contract`,
  `bounded_identifiability_and_information_plan`.
- `PRIMARY_EVIDENCE_UNAVAILABLE`: `exact_formula_contract`,
  `no_hidden_clipping`, `bounded_phase2b_validation_plan`.

The Phase 2B proposal remains `INCOMPLETE`, `NOT_AUTHORIZED`, and
`NOT_EXECUTED`. Legacy issue #10 remains Blocked, Not Evaluated, and Not
Authorized.

## Phase 2A binding additions

Phase 2A contains 24 reviewed proof obligations and eleven binding gate
requirements. The two added requirements bind selected-event conditioning and
a bounded identifiability/information-content plan. The fixed-N baseline is
`SELECTED_EVENT_CONDITIONED_V1`: `A_z`, `Y_full`, and `Y_obs` are distinct;
`K_full` is normalized on `Y_full`; efficiency and `alpha_theta` normalize the
selected law; and `N` and selection are conditioned upon. Count information
remains confined to optional Phase 2H.

The identifiability contract distinguishes a calibrated posterior from an
informative posterior. Later proposals must bind the prior, reported parameter
combinations, observational equivalence, degeneracies, and a predeclared
informativeness diagnostic without assuming every theta direction is
identifiable.

## Updated downstream planning scopes

- Phase2D plans `Y_full`, `Y_obs`, null/rejected outcomes, `epsilon(z)`,
  `alpha_theta`, selected-event forward-law closure, and perfect-detector
  selected-law closure.
- Phase2E plans the explicit theta prior, reported combinations, selected-event
  fixed-N training law, prior-dominated posterior diagnostics, and no forced
  reporting of non-identifiable directions.
- Phase2F plans identifiability, information content, a predeclared contraction
  or alternative informativeness diagnostic, calibration/informativeness
  separation, and structural-degeneracy reporting.

GitHub sub-issue and blocked-by relationships were created and verified for the
graph above. The repository JSON remains the machine-validated scientific
contract. Only issue body text for #53, #54, #57, #58, and #59 changed; issue
numbers, Project values, milestone, labels, and dependency relationships are
unchanged. The timestamped GitHub data remain an external snapshot.

Phase 2A review is complete; later numerical closure remains unexecuted. Phase
2B remains unauthorized. ADR-013 remains Proposed.

## Follow-on heavy-flavor selection

The bounded four-candidate review derives
`D1_PREPARE_FONLL_A_NLO_CONTRACT_AMENDMENT`. APFEL FONLL-A NLO is selected as
the only eligible contract amendment because it preserves the accepted
`ct18nlo_two_parameter_boundary_v2` family and current research question while
providing a pinned observable and boundary-interface contract. RTOPT is not
implementation-bound, FFN requires a new PDF-family contract, and ZM-VFN
requires a high-`Q2` domain narrowing.

This decision does not advance the dependency graph. Phase 2A remains
completed with `INCONCLUSIVE`; Phase 2B remains Backlog, Not Evaluated, Not
Authorized, `INCOMPLETE`, and `NOT_EXECUTED`. A later review must first bind
the remaining mass, `alpha_s`, anchors, grids, tolerances, convergence,
independent-reference, and resource-bound evidence.

## Phase 2B pre-authorization plan follow-on

The later review has now bound those planning inputs and derives
`P1_PREAUTH_PLAN_COMPLETE_READY_FOR_SEPARATE_AUTHORIZATION_REVIEW`. The new
plan is `COMPLETE` as a reviewable plan only. It does not change the dependency
graph or the historical incomplete proposal: Phase 2B remains Backlog, Gate
Decision Not Evaluated, Not Authorized, and `NOT_EXECUTED`. A separate future
authorization decision is required before any plan execution.

## Phase 2B execution authorization review

The successor review derives `AR2_PREAUTH_PLAN_REVISION_REQUIRED`. The P1 plan
remains complete as a planning artifact, but execution authorization is
withheld pending bounded amendments to coupling identity, high-precision sign
adjudication, exact PDF-bridge/reference coverage, quadrature independence and
tolerance error budgets. Phase 2B remains Open/Backlog, Gate Decision Not
Evaluated, Not Authorized and `NOT_EXECUTED`; Phase 2C remains Not Authorized.

## Phase 2B preauthorization v2 successor

The successor plan derives
`RV1_PREAUTH_V2_COMPLETE_READY_FOR_NEW_AUTHORIZATION_REVIEW`. It resolves the
four AR2 blockers at the plan level through AS2 coupling equivalence, NR2
sign uncertainty, a fixed PDF/APFEL bridge test, separately sourced
Gauss-Legendre and Clenshaw-Curtis paths, mixed near-zero comparisons and a
triangle-inequality numerical budget. All actual physics checks remain
post-authorization and `NOT_EXECUTED`.

This planning result does not alter the dependency graph or issue metadata.
Phase 2B remains Open/Backlog, Gate Decision Not Evaluated, Not Authorized;
Phase 2C remains Not Authorized.

## Phase 2B v2 execution authorization review

The successor authorization review derives
`AR2_PREAUTH_V2_REVISION_REQUIRED`. The v2 plan remains a complete planning
record, but its observed component benchmark does not justify a complete-rate
parent error allowance or equal split. Its post-authorization test identities,
per-flavor-segment resource cap, and load-bearing NumPy resolution also require
revision. Phase 2B remains Open/Backlog, Gate Decision Not Evaluated, Not
Authorized and `NOT_EXECUTED`; Phase 2C remains Not Authorized.

## Phase 2B preauthorization V3 successor

The V3 successor derives `V3R6_MULTIPLE_BLOCKERS_REMAIN`. Gate-local bridge and
strict implemented-rate sign specifications replace part of the invalid
global-budget architecture. Alpha and massless execution specifications, the
numerical runtime identity, grid/quadrature remainder rules, and an exact finite
FONLL comparator remain blocked. No aggregate execution maximum or
execution-ready plan is claimed.

This result does not alter the dependency graph or issue metadata. Phase 2B
remains Open/Backlog, Gate Decision Not Evaluated, Not Authorized and
`NOT_EXECUTED`; Phase 2C remains Not Authorized.
