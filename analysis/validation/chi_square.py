import numpy as np
import scipy.linalg

def calculate_chi2_uncorrelated(data, theory, stat_rel, uncor_rel):
    """
    Calculates chi2 using the uncorrelated approximation.
    Uncertainties are in percent relative to the data.
    """
    if len(data) != len(theory) or len(data) != len(stat_rel) or len(data) != len(uncor_rel):
        raise ValueError("Inconsistent dimensions in uncorrelated chi2 input.")
        
    s_abs = data * (stat_rel / 100.0)
    u_abs = data * (uncor_rel / 100.0)
    sigma_total = np.sqrt(s_abs**2 + u_abs**2)
    
    if np.any(sigma_total <= 0.0):
        raise ValueError("Detected points with zero or negative total uncorrelated uncertainty.")
        
    residuals = data - theory
    pulls = residuals / sigma_total
    chi2 = np.sum(pulls**2)
    return chi2, pulls

def calculate_chi2_covariance(data, theory, cov):
    """
    Calculates chi2 using the full covariance matrix C:
    chi2 = (D - T)^T C^-1 (D - T)
    
    Uses stable Cholesky decomposition to avoid direct matrix inversion.
    """
    n = len(data)
    if len(theory) != n:
        raise ValueError("Inconsistent dimensions between data and theory.")
    if cov.shape != (n, n):
        raise ValueError(f"Inconsistent covariance dimensions. Expected ({n}, {n}), got {cov.shape}.")
        
    residuals = data - theory
    
    # Check for NaN or Inf in residuals or covariance
    if not np.all(np.isfinite(residuals)):
        raise ValueError("Detected non-finite values in residuals (data - theory).")
    if not np.all(np.isfinite(cov)):
        raise ValueError("Detected non-finite values in covariance matrix.")
        
    # Check positive definiteness and solve using Cholesky decomposition
    try:
        # C = L L^T. L is lower triangular, or U is upper triangular.
        # cho_factor returns (c, lower)
        c, lower = scipy.linalg.cho_factor(cov, lower=True)
        # Solve C * x = residuals
        x = scipy.linalg.cho_solve((c, lower), residuals)
        chi2 = np.dot(residuals, x)
        
        # Check if the result is a valid finite float
        if not np.isfinite(chi2):
            raise ValueError("Calculated chi2 is non-finite.")
            
        # Compute normalized pulls (often computed using the diagonal of the covariance matrix for display)
        diag_uncor = np.sqrt(np.diag(cov))
        pulls = residuals / diag_uncor
        
        return chi2, pulls
        
    except scipy.linalg.LinAlgError as e:
        # If Cholesky decomposition fails, the matrix is not positive-definite or is singular.
        # Check if the matrix is symmetric
        if not np.allclose(cov, cov.T):
            raise ValueError("Covariance matrix is not symmetric.")
        # Check eigenvalues to classify
        eigenvalues = np.linalg.eigvalsh(cov)
        min_ev = np.min(eigenvalues)
        if min_ev < 0:
            raise ValueError(f"Covariance matrix is non-positive-definite. Minimum eigenvalue: {min_ev}")
        elif min_ev == 0:
            raise ValueError("Covariance matrix is singular (has zero eigenvalue).")
        else:
            raise ValueError(f"Covariance matrix factorization failed: {e}")
