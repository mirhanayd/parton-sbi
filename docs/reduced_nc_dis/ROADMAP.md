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
