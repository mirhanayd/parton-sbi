import numpy as np

def build_covariance_matrix(df):
    """
    Constructs the covariance matrix C_ij using:
    - statistical uncertainty ('stat')
    - uncorrelated systematic uncertainty ('uncor')
    - 162 correlated systematic uncertainties ('sys1' to 'sys162')
    
    All uncertainties in the dataset are in % relative to the cross section ('Sigma').
    """
    n = len(df)
    sigma_data = df["Sigma"].values
    stat_rel = df["stat"].values
    uncor_rel = df["uncor"].values
    
    # Calculate absolute statistical and uncorrelated systematic uncertainties
    s_abs = sigma_data * (stat_rel / 100.0)
    u_abs = sigma_data * (uncor_rel / 100.0)
    
    # Uncorrelated variance for each point
    diag_uncor = s_abs**2 + u_abs**2
    
    # Check for zero uncertainties
    if np.any(diag_uncor <= 0.0):
        raise ValueError("Detected points with zero or negative uncorrelated uncertainty.")
        
    # Initialize covariance matrix as diagonal matrix of uncorrelated uncertainties
    cov = np.diag(diag_uncor)
    
    # Find all systematic columns (sys1 to sys162)
    sys_cols = [col for col in df.columns if col.startswith("sys")]
    
    # Calculate absolute correlated systematic uncertainties
    # sys_matrix shape: (n_points, n_sources)
    sys_rel = df[sys_cols].fillna(0.0).values
    sys_abs = np.zeros_like(sys_rel)
    for col_idx in range(sys_rel.shape[1]):
        sys_abs[:, col_idx] = sigma_data * (sys_rel[:, col_idx] / 100.0)
        
    # Add correlated systematic contribution: Sum_{k} Delta_{ik} * Delta_{jk}
    # Using matrix multiplication: sys_abs @ sys_abs.T
    cov += np.dot(sys_abs, sys_abs.T)
    
    return cov
