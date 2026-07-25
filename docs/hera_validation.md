# HERA DIS Data Validation

This document describes the validation of the project's inclusive Deep Inelastic Scattering (DIS) theory predictions against combined HERA measurements.

## Objective

The goal is to provide a quantitative, reproducible validation framework comparing theoretical inclusive cross sections against experimental data from the combined H1 and ZEUS collaborations.

## Selected Dataset & Kinematics

- **Observable:** Reduced neutral-current cross section $\sigma_{r, \text{NC}}^{+}$ for $e^{+}p$ scattering.
- **Dataset ID:** `HERA1+2_NCep_920` (Data from Table 1 of HERAPDF2.0 combined paper).
- **Beam Energies:** 
  - Electron beam: $27.5$ GeV
  - Proton beam: $920$ GeV
  - Centre-of-mass energy $\sqrt{s} = 318$ GeV.
- **Kinematic Cut:** $Q^2 \ge 3.5 \text{ GeV}^2$ (standard cut to restrict analysis to the perturbative QCD regime).

## Theory Configuration

- **Backend:** APFEL++
- **Perturbative Order:** NLO (Next-to-Leading Order QCD)
- **PDF Set:** CT18LO (or other LHAPDF-installed sets)
- **Factorization/Renormalization Scales:** $\mu_F = \mu_R = Q$
- **Heavy Flavor Scheme:** Zero-Mass Variable Flavor Number Scheme (ZM-VFNS)
- **Electroweak Mode:** Single-photon exchange (no $Z$ exchange or EW running)

## $\chi^2$ Analysis Results

The validation pipeline calculates the $\chi^2$ and $\chi^2/\text{NDF}$ using two distinct approximations:
1. **Uncorrelated Approximation:** Assumes all statistical and systematic uncertainties are uncorrelated.
2. **Full Covariance Method:** Incorporates the 162 correlated systematic uncertainty sources published in the HERA data tables.

## Limitations

- **Electroweak Corrections:** The APFEL++ configuration is pinned to pure electromagnetic photon-exchange. Parity-violating contributions ($xF_3$) and $Z$-boson exchange are omitted.
- **Bin Integration:** The comparison directly evaluates the theory at the published effective bin centers ($x, Q^2$), which is the standard approach for inclusive DIS fits.
