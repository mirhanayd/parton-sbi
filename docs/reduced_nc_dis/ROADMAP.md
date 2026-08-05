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
| Phase2A | #54 | Define the observation-law contract | In Progress | Planning Only |
| Phase2B | #55 | Formula and normalization closure | Backlog | Not Authorized |
| Phase2C | #56 | Normalized latent-event sampler | Backlog | Not Authorized |
| Phase2D | #57 | Detector response kernel | Backlog | Not Authorized |
| Phase2E | #58 | Fixed-N set-level SBI proof of principle | Backlog | Not Authorized |
| Phase2F | #59 | Calibration, coverage, and robustness | Backlog | Not Authorized |
| Phase2G | #60 | Reproducible methodology paper package | Backlog | Not Authorized |
| Phase2H | #61 | Optional rate-inclusive extension | Backlog | Not Authorized |

Every implementation phase requires a later, explicit authorization after its
predecessor's binding acceptance criteria pass. A future Phase 2A PASS would
authorize only a separate Phase 2B proposal, not implementation.

GitHub sub-issue and blocked-by relationships were created and verified for the
graph above. The repository JSON remains the machine-validated scientific
contract; its timestamped GitHub data are an external snapshot.
