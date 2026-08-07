# Reduced neutral-current DIS research line

This directory defines the planning-only Phase 2 research line for a reduced,
normalized neutral-current DIS observation model. It preserves the repository's
set-level PDF inference objective while leaving the legacy full-generator line
paused.

Phase 2 currently authorizes only the roadmap and Phase 2A mathematical and
primary-source contract review. It does not authorize formula evaluation,
simulation, event generation, datasets, detector implementation, or neural
training.

Schema v2 binds the `SELECTED_EVENT_CONDITIONED_V1` fixed-N law and separates
latent acceptance `A_z`, the complete detector space `Y_full`, and selected
observations `Y_obs`. It also requires a bounded later identifiability and
information-content plan: calibration is necessary but does not by itself
establish that the selected data are informative about theta. All 24 proof
obligations remain `NOT_EVALUATED`; no external source review or experiment was
performed by this correction.

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

Phase 2A review is a source-backed contract review; later numerical closure remains unexecuted. Phase 2B remains unauthorized. ADR-013 remains Proposed. The result is not accepted until independent review and merge.
