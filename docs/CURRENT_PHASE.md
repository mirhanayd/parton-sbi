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
- A Phase 1B-D design and staged acceptance contract have been drafted for
  scientific review.
- No Phase 1B-D code, generated PDF artifact, direct event corpus, continuous
  parameterization, or amortized posterior model exists.

# Proposed next phase

```text
Phase 1B-D0:
Validate the continuous, sum-rule-preserving input family and candidate pilot
box without generating a training corpus.
```

The design selects APFEL++ evolution and an immutable generated LHAPDF artifact
for direct regeneration. It proposes fixed-envelope accept-reject unweighting
as an experiment, not as an already validated sampling method.

# Gate

- Review and accept the Phase 1B-D design and ADRs before D0 implementation.
- Do not reuse or reweight a nominal event pool.
- Do not begin D1 until D0 acceptance criteria pass.
- Do not begin neural inference until D0-D5 pass and a separate neural phase is
  authorized.

# Model recommendation

- Maintenance: GPT-5.6 Sol — Medium
- Scientific implementation: GPT-5.6 Sol — High
- Cross-phase architecture review: GPT-5.6 Sol — High
