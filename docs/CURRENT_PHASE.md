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
- No continuous PDF parameterization.
- No amortized posterior model.

# Next phase

Phase 1B-D planning: a continuous, sum-rule-preserving PDF family coupled to
direct event regeneration at each PDF parameter point.

# Gate

Phase 1B-D is authorized for planning only. Do not implement it until its
scientific design and acceptance criteria are reviewed. The failed nominal-pool
reuse path is not authorized, and neural inference is not implemented.

# Model recommendation

- Maintenance: GPT-5.6 Sol — Medium
- Scientific implementation: GPT-5.6 Sol — High
- Cross-phase architecture review: GPT-5.6 Sol — High
