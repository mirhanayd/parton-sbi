# Completed

- Imported validated QuarkSim DIS baseline into PartonSBI.
- Repository and scientific audit.
- Amortized-inference roadmap.
- Phase 0A typed streaming HepMC3 extraction.
- Rust baseline restored to green.
- Research-only repository cleanup and renaming.
- Phase 1A discrete LHAPDF-member reweighting infrastructure.
- Strict in-grid LHAPDF support contract and provenance-complete confirmation
  study.
- Phase 1A negative decision: nominal-pool reuse rejected by the predeclared
  ESS gate.
- Phase 1B-D design and staged acceptance contract.
- Phase 1B-D0 mathematical boundary-family implementation and complete
  441-point pilot-box study.
- Phase 1B-D0 negative decision: the proposed pilot family failed positivity
  and central-reconstruction gates.
- D0-revision audit and proposed baseline/admissibility contract.
- ADR-004 accepted and revised D0 projected-baseline revalidation completed.
- Phase 1B-D1 APFEL++ evolution and deterministic one-member LHAPDF artifact
  implementation.
- Phase 1B-D1 negative decision: the fixed off-knot transport and evolved
  sum-rule gates failed across the complete nine-anchor study.
- Phase 1B-D1 revision audit and ADR-005 proposal.
- ADR-005 accepted and revised D1 threshold-separated artifact implementation
  completed.
- Phase 1B-D1R negative decision: deterministic refinement exceeded its fixed
  performance cap, moment/leakage convergence failed, and direct off-knot
  transport remained outside tolerance across all nine anchors.
- Phase 1B-D1A evolved-PDF transport architecture audit completed with an
  `INCONCLUSIVE` decision and a bounded prototype authorization.
- Phase 1B-D1A bounded transport-comparison prototype completed with an
  `INCONCLUSIVE` decision: the fixed custom interpolator failed, while direct
  APFEL transport remained unselected because required evidence was not
  measured.

# Current state

- CLI and batch-oriented DIS research infrastructure.
- APFEL++, LHAPDF, PYTHIA 8, HepMC3, and Candle surrogate retained.
- No Cornell demo.
- No desktop GUI.
- Phase 1A is complete with a negative scientific result.
- The active support policy is `strict_in_grid`; PDF extrapolation is disabled.
- The clean 2,000-event confirmation pool had nominal `ESS/N = 0.04156296`,
  below the fixed 0.20 reuse threshold.
- Reweighting-based pool reuse is rejected; direct event generation is required
  at every PDF parameter point.
- The D0 input-scale continuous boundary family and validation CLI are
  implemented. This is not an evolved or generator-ready PDF artifact.
- The clean v1 D0 study evaluated 441 hard-box points and 80 guard-shell
  diagnostics. All hard-box points failed because the gluon became negative
  near `x -> 1`; the center also exceeded the fixed reconstruction tolerance.
- The D0-revision audit found no negative raw gluon knots. The inherited
  LHAPDF `logcubic` interpolant first crosses below zero off-knot at
  `x=0.9935531299173892`; its negative gluon momentum fraction is
  `1.5822152070733786e-11`.
- ADR-004 defines a versioned sum-rule-projected CT18NLO boundary and a
  baseline-relative NLO input-admissibility contract. That v2 contract is now
  implemented and has passed a clean 441-point/80-guard-point revalidation.
- The historical D0 v1 `FAIL` and revised-D0 v2 `PASS` remain unchanged.
- D1 was explicitly authorized after D0R review and is now complete with
  `STAGE1_DECISION = FAIL`.
- The clean D1 study evaluated exactly nine anchors from implementation commit
  `1a7181ad1582029aa93cf743807c24e18a147704`.
- Boundary callbacks and alpha_s knots passed, but 511,900 off-knot
  flavor-point round trips exceeded tolerance. The maximum evolved sum-rule
  residual was `4.2761916359967955e-4` at `Q=100000 GeV`.
- Deterministic APFEL-evolved LHAPDF artifacts now exist only in the ignored
  content-addressed cache. No artifact is generator-ready under the failed
  Stage 1 contract.
- The D1-revision audit found the lhagrid1 serialization correct: all exact
  knots passed, and an independent log-bicubic implementation reproduced
  LHAPDF. Off-knot errors are global finite-grid representation errors.
- The apparent high-Q conservation failure combines finite exported support
  with evolution below `x=1e-9`. On an APFEL computational grid extending to
  `1e-11`, independently integrated full-domain moments meet the proposed
  `1e-5` gate while the lost exported-support momentum remains explicit.
- ADR-005 defines threshold-separated, deterministically refined artifacts,
  computational-domain moment gates, raw-CT18 fidelity as a mandatory
  diagnostic, and NLO photon-exchange structure-function closure.
- The clean D1R study ran from commit
  `de26c57066dc018b530963d25d9a547b4b650c67` with `dirty=false` and evaluated
  all nine mandatory anchors on one common 641-x by 149-Q grid.
- Exact-knot serialization and independent LHAPDF log-bicubic reconstruction
  passed with zero tolerance failures, and all nine NLO photon F2/FL
  observable closures passed.
- The refinement trace stopped at `669.137992893 s` for its worst anchor,
  above the fixed 600-second cap. It retained `3,492,044` direct off-knot
  failures with maximum absolute error `1374.7964848542324`.
- The worst base and doubled full-domain residuals were
  `1.0118550574755858e-5` and `8.177903536354947e-6`; the maximum
  base/doubled leakage disagreement was `4.501148846980385e-7`, above the
  fixed `1e-7` gate.
- Revised Stage 1 is complete with `FAIL`;
  `D2_AUTHORIZATION_CANDIDATE = false` and `D2_AUTHORIZED = false`.
- ADR-006 rejects further unconstrained global LHAPDF refinement as the next
  path. It does not yet select between a direct APFEL-backed evaluator and a
  repository-owned deterministic interpolator because all-consumer PYTHIA
  reachability, evaluator safety, performance, and cache behavior remain
  unproven.
- A layered future acceptance contract requires PDF closure on a predeclared
  conservative all-consumer reachable domain, full neutral-current gamma/Z
  observable closure, and later separately authorized event-distribution
  closure. Global-support pointwise discrepancies remain mandatory
  diagnostics.
- The clean D1A prototype ran from commit
  `6cdd617cae88dc7b4d79a2388f1822076a8008bd` with `dirty=false`, three fixed
  anchors, no events, and the versioned
  `serde_json_float_roundtrip_pretty_v1` evidence policy.
- The fixed 6x6 custom bilinear representation reproduced all 396 stored knots
  at every anchor, but failed 245 of 275 off-knot comparisons at every anchor
  and failed one-sided threshold closure. It is rejected without post-hoc
  refinement.
- Direct APFEL deterministic batch repetition and strict support passed, but
  persistent scalar throughput, thread safety, process isolation, and the
  complete all-consumer query envelope were not measured. Direct APFEL
  transport remains unselected.
- The unresolved PYTHIA consumers are `initial_state_shower` and
  `beam_remnants`; all-consumer envelope closure is false.
- D1A is complete with `PROTOTYPE_DECISION = INCONCLUSIVE`,
  `DIRECT_CANDIDATE_STATUS = INCONCLUSIVE`, `CUSTOM_CANDIDATE_STATUS = FAIL`,
  and `D2_AUTHORIZED = false`.
- No PYTHIA continuous-PDF coupling, direct event corpus, sampling method,
  dataset, or amortized posterior model exists.

# Next scientific action

```text
Scientifically review the D1A prototype result. A separate future decision
would be required to test a persistent direct APFEL-backed scalar adapter and
instrument all enabled PYTHIA PDF consumers.
```

The approved design's later APFEL and fixed-envelope proposals remain
unimplemented hypotheses.

# Gate

- Do not reuse or reweight a nominal event pool.
- Do not begin D2: revised Stage 1 failed and
  `D2_AUTHORIZATION_CANDIDATE = false`.
- Do not reinterpret exact-knot or photon-observable closure as qualification
  of the failed direct off-knot transport contract.
- Any additional D1 revision requires a new reviewed architecture decision.
- The D1A prototype authorization is planning/validation only and cannot
  authorize production PYTHIA coupling or D2.
- The D1A `INCONCLUSIVE` decision does not select direct APFEL transport; the
  custom 6x6 representation is rejected and D2 remains unauthorized.
- Do not shrink the pilot box, clip negative densities, or change tolerances
  without a reviewed scientific decision.
- Do not begin neural inference until D0-D5 pass and a separate neural phase is
  authorized.

# Model recommendation

- Maintenance: GPT-5.6 Sol — Medium
- Scientific implementation: GPT-5.6 Sol — High
- Cross-phase architecture review: GPT-5.6 Sol — High
