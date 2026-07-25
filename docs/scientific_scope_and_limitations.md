# Scientific Scope and Limitations

This document records the scientific approximations and boundaries of the PartonSBI inclusive deep-inelastic scattering (DIS) framework.

## 1. Perturbative Order & Missing Higher Orders (MHO)
- **Supported Orders:** The engine evaluates matrix elements and PDF evolution up to Next-to-Leading Order (NLO) in $\alpha_s$.
- **Limitations:** The codebase does not currently expose NNLO coefficient functions. Theoretical scale uncertainties computed by the pipeline therefore represent the NLO truncation error. At low $Q^2$ or extreme $x$, missing higher-order terms could lead to non-negligible theory-data tension.

## 2. Electroweak Corrections
- **Approximations:** The default structure function calculations ($F_2$, $F_L$, $xF_3$) and subsequent reduced cross-sections rely exclusively on virtual photon ($\gamma^*$) exchange and pure QCD corrections.
- **Missing Terms:** Pure $Z$-boson exchange and $\gamma Z$ interference terms are omitted from the default configuration. At $Q^2 > 1000 \text{ GeV}^2$, these electroweak terms become highly significant. Users must configure external parameters to include them if predicting high-$Q^2$ cross sections accurately.

## 3. Heavy Flavor Treatment
- **ZMVFNS Assumption:** The APFEL++ backend is primarily instantiated using a Zero-Mass Variable Flavor Number Scheme (ZMVFNS). Charm and bottom quarks are treated as massless partons above their respective thresholds.
- **Consequences:** Near the charm mass threshold ($Q^2 \sim 4 \text{ GeV}^2$), ZMVFNS predictions systematically diverge from experimental $F_2^c$ measurements. For dedicated threshold analyses, a FONLL or generalized mass (GM-VFNS) configuration would be required.

## 4. Hadronization and Detector Simulation
- **PYTHIA 8 Usage:** PartonSBI delegates the partonic cascade and string fragmentation to PYTHIA 8. This is a phenomenological step governed by the configured PYTHIA model.
- **No Detector Simulation:** Events produced by the simulator are explicitly at the "particle level." The repository contains no GEANT4 detector mockups. No acceptance, efficiency, or smearing effects are applied.

## 5. Neural Network Surrogate Model Limitations
- **Constraint Boundaries:** The surrogate backend is strictly an interpolation tool trained on deterministic APFEL++ data. Its domain is hardcoded ($10^{-5} \le x \le 0.8$, $3.5 \le Q^2 \le 10000 \text{ GeV}^2$).
- **No Extrapolation:** The surrogate lacks any encoded physical boundary conditions (such as $F_2 \to 0$ as $x \to 1$). Therefore, queries falling marginally outside the defined training hypercube are forcibly rejected to prevent unphysical scaling artifacts.

## 6. Target Mass Corrections & Higher Twist
- **Target Mass:** Proton mass corrections (TMC) are disabled by default. At large $x$ ($> 0.6$) and low $Q^2$, predictions may not safely compare to fixed-target experiments.
- **Higher Twist:** No phenomenological $1/Q^2$ higher-twist terms are parameterized in the calculation.

## Summary
PartonSBI currently supports forward-simulation and validation studies within these declared approximations. Its outputs are not a complete precision treatment, detector-level prediction, unrestricted flavor extraction, or publication claim.
