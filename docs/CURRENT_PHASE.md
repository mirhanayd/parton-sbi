# Completed

- Imported validated QuarkSim DIS baseline into PartonSBI.
- Repository and scientific audit.
- Amortized-inference roadmap.
- Phase 0A typed streaming HepMC3 extraction.
- Rust baseline restored to green.
- Research-only repository cleanup and renaming.

# Current state

- CLI and batch-oriented DIS research infrastructure.
- APFEL++, LHAPDF, PYTHIA 8, HepMC3, and Candle surrogate retained.
- No Cornell demo.
- No desktop GUI.
- Phase 1A reweighting infrastructure implemented, audited, and unit-tested.
- Phase 1A scientific validation blocked at Stage A by an out-of-grid CT18NLO
  scale in the nominal pool; no direct-target closure was started.
- No continuous PDF parameterization.
- No amortized posterior model.

# Next phase

Resolve the Phase 1A PDF-support contract, then restart discrete
LHAPDF-member hard-PDF reweighting closure under a new study ID. The current
nominal smoke sample also has `ESS/N = 0.01176`, below the mandatory 0.20 reuse
threshold.

# Gate

Do not begin Phase 1B or neural inference. Phase 1A is incomplete and blocked;
pool reuse is not authorized.

# Model recommendation

- Maintenance: GPT-5.6 Sol — Medium
- Scientific implementation: GPT-5.6 Sol — High
- Cross-phase architecture review: GPT-5.6 Sol — High
