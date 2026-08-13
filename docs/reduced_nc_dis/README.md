# Reduced neutral-current DIS research line

This directory defines the planning-only Phase 2 research line for a reduced,
normalized neutral-current DIS observation model. It preserves the repository's
set-level PDF inference objective while leaving the legacy full-generator line
paused.

Phase 2 currently has a completed Phase 2A mathematical and primary-source
contract review with final scientific decision `INCONCLUSIVE`. It does not
authorize formula evaluation, simulation, event generation, datasets, detector
implementation, or neural training.

Schema v2 binds the `SELECTED_EVENT_CONDITIONED_V1` fixed-N law and separates
latent acceptance `A_z`, the complete detector space `Y_full`, and selected
observations `Y_obs`. It also requires a bounded later identifiability and
information-content plan: calibration is necessary but does not by itself
establish that the selected data are informative about theta. Phase 2A reviewed
all 24 proof obligations and ended `INCONCLUSIVE` because required primary
evidence remains unavailable.

## Authoritative planning records

- [Research question and claim boundary](RESEARCH_QUESTION.md)
- [Phase dependency roadmap](ROADMAP.md)
- [Repository strategy and planned layout](REPOSITORY_LAYOUT.md)
- [Machine-readable roadmap](phase2_roadmap.json)
- [Phase 2A contract-review specification](contracts/phase2a_contract_review_spec.json)
- [Roadmap completion report](PHASE2_ROADMAP_COMPLETION.md)
- [ADR-012](../adr/ADR-012-reduced-nc-dis-research-direction.md)

The machine-readable artifacts and their validator record the authorization
boundary. The GitHub snapshot is external provenance; the offline validator
does not contact or verify live GitHub state.

Phase 2A review is complete: PR #63 merged at
`e798a64265afd806bb7030218e2fac60e1656a78`, and issue #54 is
closed/completed. Later numerical closure remains unexecuted. Phase 2B issue
#55 remains Backlog with Gate Decision Not Evaluated, Authorization Not
Authorized, and execution `NOT_EXECUTED`. ADR-013 remains Proposed.

A versioned follow-on contract amendment now selects source-bound APFEL
FONLL-A at NLO as the heavy-flavor convention. The selection disambiguates the
historical generic NLO-VFNS wording while preserving the historical Phase 2A
`INCONCLUSIVE` result, accepted PDF family, observation law, research question,
and paper nonclaims. Required mass, `alpha_s`, validation-plan, and independent
closure details remain unresolved; the amendment does not authorize Phase 2B
or numerical execution.

- [FONLL-A contract-selection review](PHASE2_FONLL_A_CONTRACT_AMENDMENT.md)
- [Machine-readable FONLL-A amendment](contracts/phase2_fonll_a_contract_amendment.json)

A later planning-only review now records a complete Phase 2B pre-authorization
validation plan. It resolves the amendment's eight planning questions without
executing them and derives
`P1_PREAUTH_PLAN_COMPLETE_READY_FOR_SEPARATE_AUTHORIZATION_REVIEW`. Phase 2B
remains Not Authorized and `NOT_EXECUTED`.

- [Phase 2B pre-authorization validation plan](PHASE2B_PREAUTHORIZATION_VALIDATION_PLAN.md)
- [Machine-readable Phase 2B pre-authorization plan](contracts/phase2b_preauthorization_validation_plan.json)

A successor execution authorization review independently audits that complete
plan and derives `AR2_PREAUTH_PLAN_REVISION_REQUIRED`. The research direction
remains viable, but bounded plan amendments are required before numerical
execution can be authorized. Phase 2B remains Not Authorized and
`NOT_EXECUTED`.

- [Phase 2B execution authorization review](PHASE2B_EXECUTION_AUTHORIZATION_REVIEW.md)
- [Machine-readable authorization review](contracts/phase2b_execution_authorization_review.json)
