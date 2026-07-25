# Systematic Theory Uncertainties in HERA DIS Validation

This document describes the systematic theory uncertainty calculations implemented in the `neuronswq/quark_sim` HERA validation framework.

---

## 1. Parton Distribution Function (PDF) Uncertainties

PDF sets present errors differently depending on their design. Our framework queries the LHAPDF `ErrorType` metadata key and applies the matching prescription:

### A. Asymmetric Hessian (`hessian`)
Standard for CTEQ/CT18 sets. The $N$ members (excluding member 0) represent $N/2$ orthogonal eigenvectors. Odd members $2i-1$ and even members $2i$ represent positive and negative displacements along eigenvector $i$:
$$\Delta \sigma^+ = \sqrt{ \sum_{i=1}^{N/2} \left[ \max(\sigma_{2i-1} - \sigma_0, \sigma_{2i} - \sigma_0, 0) \right]^2 }$$
$$\Delta \sigma^- = \sqrt{ \sum_{i=1}^{N/2} \left[ \max(\sigma_0 - \sigma_{2i-1}, \sigma_0 - \sigma_{2i}, 0) \right]^2 }$$

### B. Symmetric Hessian (`symmhessian`)
Common for older or simplified Hessian sets. Error variations are symmetric:
$$\Delta \sigma^+ = \Delta \sigma^- = \sqrt{ \sum_{k=1}^N (\sigma_k - \sigma_0)^2 }$$

### C. Monte Carlo Replicas (`replicas`)
Standard for NNPDF sets. Predictions are calculated statistically from the replica ensemble:
$$\Delta \sigma^+ = \Delta \sigma^- = \sqrt{ \frac{1}{N-1} \sum_{k=1}^N (\sigma_k - \langle\sigma\rangle)^2 }$$
where $\langle\sigma\rangle$ is the mean of the replicas.

---

## 2. Scale Uncertainties (7-Point Variation)

To estimate uncertainties from uncalculated higher-order QCD corrections, we vary the renormalization scale ($\mu_R$) and factorization scale ($\mu_F$) by factors of $0.5$ and $2.0$ around the central scale $\mu_0 = Q$:
$$(\mu_R, \mu_F) \in \left\{ (1,1), (0.5,0.5), (0.5,1), (1,0.5), (1,2), (2,1), (2,2) \right\}$$
Antipodal scale variations $(0.5, 2.0)$ and $(2.0, 0.5)$ are excluded to avoid large unphysical logarithms $\ln(\mu_R/\mu_F)$.

The scale uncertainty band is computed as the envelope (maximum and minimum variations):
$$\Delta \sigma^+_{\text{scale}} = \max\left(0, \max_{(R, F)} (\sigma_{(R, F)}) - \sigma_{(1,1)}\right)$$
$$\Delta \sigma^-_{\text{scale}} = \max\left(0, \sigma_{(1,1)} - \min_{(R, F)} (\sigma_{(R, F)})\right)$$

---

## 3. Monte Carlo Statistical Uncertainty

For weighted event samples, statistical uncertainties are calculated from event weights $w_i$:
$$\sigma_{\text{stat}} = \sqrt{\sum_i w_i^2}$$
This avoids the naive $\sqrt{N}$ poisson errors which are mathematically incorrect for weighted events.

---

## 4. Deterministic Cache Design

Since evaluating structure functions for 58 PDF members and 7 scale combinations is computationally intensive, we implement a thread-safe deterministic caching system (`data/cache/apfel_predictions_cache.json`).

The cache key is computed as a SHA-256 hash of the following parameters:
- Physics backend and version (e.g. `"apfel"`, `"4.8.0"`)
- PDF set and central member index
- Perturbative order (`LO` or `NLO`)
- Bjorken $x$ and virtuality $Q^2$
- Scale definitions
- Target process (`nc_dis`)
- Active PDF members and scale variations lists

This ensures that cached values are never incorrectly shared across incompatible runs, while providing instant evaluation for identical configurations.
