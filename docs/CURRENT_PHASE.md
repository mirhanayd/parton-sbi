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
- The clean D0 study evaluated 441 hard-box points and 80 guard-shell
  diagnostics. All hard-box points failed because the gluon became negative
  near `x -> 1`; the center also exceeded the fixed reconstruction tolerance.
- D1 is not authorized.
- The D0-revision audit found no negative raw gluon knots. The inherited
  LHAPDF `logcubic` interpolant first crosses below zero off-knot at
  `x=0.9935531299173892`; its negative gluon momentum fraction is
  `1.5822152070733786e-11`.
- ADR-004 proposes a versioned sum-rule-projected CT18NLO boundary and a
  baseline-relative NLO input-admissibility contract. It is under scientific
  review and has not been implemented or revalidated.
- No APFEL-evolved family artifact, generated LHAPDF grid, PYTHIA continuous
  PDF coupling, direct event corpus, sampling method, dataset, or amortized
  posterior model exists.

# Next scientific action

```text
Scientifically review ADR-004. If accepted, authorize only the separately
scoped revised D0 implementation and validation.
```

The approved design's later APFEL and fixed-envelope proposals remain
unimplemented hypotheses.

# Gate

- Do not reuse or reweight a nominal event pool.
- Do not begin D1: D0 failed its binding acceptance criteria.
- Do not implement the D0 revision until ADR-004 is accepted and the blocked
  validation issue is explicitly authorized.
- Do not shrink the pilot box, clip negative densities, or change tolerances
  without a reviewed scientific decision.
- Do not begin neural inference until D0-D5 pass and a separate neural phase is
  authorized.

# Model recommendation

- Maintenance: GPT-5.6 Sol — Medium
- Scientific implementation: GPT-5.6 Sol — High
- Cross-phase architecture review: GPT-5.6 Sol — High
