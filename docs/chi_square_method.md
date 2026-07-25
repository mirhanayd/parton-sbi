# $\chi^2$ Analysis Methodology

This document details the mathematical definitions, implementation, and numerical stability of the $\chi^2$ comparison methods.

## Uncorrelated $\chi^2$

The uncorrelated approximation assumes that all sources of uncertainty are completely independent:

$$\chi^2_{\text{uncor}} = \sum_{i=1}^{N} \left( \frac{D_i - T_i}{\sigma_{i}} \right)^2$$

where:
- $D_i$ is the experimental measurement (data),
- $T_i$ is the theoretical prediction,
- $\sigma_i = \sqrt{s_i^2 + u_i^2}$ is the absolute uncorrelated uncertainty (combining statistical error $s_i$ and uncorrelated systematic error $u_i$).

---

## Full Covariance $\chi^2$

The full covariance method accounts for correlation between systematic uncertainty sources (e.g. calibration scales, luminosity, detector efficiencies):

$$\chi^2_{\text{cov}} = (D - T)^T C^{-1} (D - T)$$

where $C$ is the $N \times N$ covariance matrix.

### Covariance Matrix Construction

The covariance matrix $C_{ij}$ is constructed from the statistical ($s_i$), uncorrelated systematic ($u_i$), and $M$ correlated systematic ($\Delta_{ik}$) uncertainties:

$$C_{ij} = \delta_{ij} (s_i^2 + u_i^2) + \sum_{k=1}^{M} \Delta_{ik} \Delta_{jk}$$

Since the uncertainties in the data tables are published as percentages relative to the cross section, we scale them by the data value $D_i$:
- $s_i = D_i \times (\text{stat}_i / 100)$
- $u_i = D_i \times (\text{uncor}_i / 100)$
- $\Delta_{ik} = D_i \times (\text{sys}_k / 100)$

---

## Numerical Stability & Solver

Direct inversion of $C$ to compute $C^{-1}$ is numerically unstable and computationally expensive. Instead, we solve the linear system:

$$C x = D - T$$

for $x$, and then compute:

$$\chi^2_{\text{cov}} = (D - T)^T x$$

Because $C$ is symmetric and positive-definite, we use the **Cholesky Decomposition** ($C = L L^T$) to solve the system stably.

### Validation Checks
1. **Dimension Mismatch:** Verify that $D$, $T$, and $C$ shapes are consistent.
2. **Singularity & Positive Definiteness:** If $C$ is not positive-definite, Cholesky decomposition fails. The code catches this, computes eigenvalues, and reports if the matrix is singular or has negative eigenvalues.
3. **Zero Uncertainties:** We check that the diagonal uncorrelated uncertainties are strictly positive.
