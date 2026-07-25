# Reproducibility and Physical Validation

This document describes the seed configuration, reproducibility validation, and physical validation checks implemented in the PYTHIA 8 DIS event generator.

## Reproducibility and Seed Configuration

PYTHIA 8 uses a pseudo-random number generator (PRNG) to simulate the stochastic processes of hard scattering, parton showers, and hadronization. To ensure reproducibility of a generation run:

- **Explicit Seed Requirement**: The seed is configured using the JSON field `"random_seed"`.
- **Initialization**: If `random_seed` is positive, the generator sets:
  - `Random:setSeed = on`
  - `Random:seed = <seed_value>`
- **Dynamic Seeding**: If the seed is negative or omitted, a unique seed is dynamically generated using the current system time in nanoseconds. The actual seed used is recorded in `metadata.json`.
- **Reproducibility Guarantee**: Running the backend twice with the same:
  - Generator/software versions
  - Input configuration parameters
  - PDF set and member
  - Random seed
  generates identical events in the HepMC3 record and identical numerical variables in `inclusive_observables.csv`.

---

## Physical Validation Checks

Every generated event is subjected to rigorous physical validation checks before being written to the output record:

### 1. Four-Momentum Conservation
Total energy and momentum must be conserved from the initial beam state to the final stable particle state.
- **Initial State**: $p_{\text{initial}} = k_{\text{beam}} + P_{\text{beam}}$
- **Final State**: $p_{\text{final}} = \sum_{i \in \text{final}} p_i$ (where $i$ runs over all particles with `isFinal() == true`).
- **Tolerance**: We enforce component-wise mismatches to be less than $10^{-3}$ GeV ($1.0$ MeV):
  $$\max(|p_{x, \text{final}} - p_{x, \text{initial}}|, |p_{y, \text{final}} - p_{y, \text{initial}}|, |p_{z, \text{final}} - p_{z, \text{initial}}|) \le 1.0 \times 10^{-3} \text{ GeV}$$
  $$|E_{\text{final}} - E_{\text{initial}}| \le 1.0 \times 10^{-3} \text{ GeV}$$
- Events violating this tolerance are vetoed and increment the `vetoed_conservation_events` count in `summary.json`.

### 2. Finite Four-Vectors
The energy and momentum components of the scattered electron and all final-state particles must be finite (i.e. not `NaN` or `Infinity`). Events with non-finite values are failed and recorded.

### 3. Kinematic Cut Validation
Event kinematics ($Q^2$, $x$, and $y$) reconstructed from the scattered electron four-vector are verified against the user-requested cuts. Events falling outside the cuts are vetoed (`vetoed_cuts_events`).

---

## Failed vs. Vetoed Events

- **Failed Events** (`failed_events`): Events where the PYTHIA generator itself failed (e.g. `pythia.next()` returned false due to shower or hadronization errors) or where NaN/inf was detected. These are recorded with details.
- **Vetoed Events**:
  - `vetoed_cuts_events`: Events that were physically generated but fell outside the requested $x$, $Q^2$, or $y$ cuts.
  - `vetoed_conservation_events`: Events that failed four-momentum conservation checks.
- **Accepted Events** (`accepted_events`): Events that passed all checks and are written to output files. The loop continues until the requested count is met.
