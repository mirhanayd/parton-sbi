import numpy as np

def calculate_pdf_uncertainty(central, members, error_type="hessian"):
    """
    Calculates PDF uncertainty based on error type:
    - hessian: standard asymmetric Hessian uncertainty
    - symmhessian: symmetric Hessian uncertainty
    - replicas: replica standard deviation
    """
    members = np.array(members)
    if not np.isfinite(central):
        raise ValueError("Central value is not finite.")
    if not np.all(np.isfinite(members)):
        raise ValueError("One or more members contain non-finite values.")
        
    n_members = len(members)
    if n_members == 0:
        return 0.0, 0.0
        
    error_type_lower = error_type.lower()
    
    if "symmhessian" in error_type_lower:
        # Symmetric Hessian: sqrt(sum( (f_k - f_0)^2 ))
        diff = members - central
        err = np.sqrt(np.sum(diff**2))
        return err, err
        
    elif "hessian" in error_type_lower:
        # Asymmetric Hessian (standard for CT18, etc.)
        # members vector: [m1, m2, ..., m_N]. Normally N is even.
        # Pairs: (m_1, m_2), (m_3, m_4), ... represent positive/negative directions
        err_plus_sq = 0.0
        err_minus_sq = 0.0
        
        # loop in pairs
        for i in range(0, n_members - 1, 2):
            diff1 = members[i] - central
            diff2 = members[i+1] - central
            
            # plus variation
            val_plus = max(diff1, diff2, 0.0)
            err_plus_sq += val_plus**2
            
            # minus variation
            val_minus = max(-diff1, -diff2, 0.0)
            err_minus_sq += val_minus**2
            
        return np.sqrt(err_plus_sq), np.sqrt(err_minus_sq)
        
    elif "replicas" in error_type_lower or "replica" in error_type_lower:
        # Replica standard deviation relative to replica mean
        # Central value for replicas is often the mean of replicas,
        # but we compute dispersion around the mean
        mean = np.mean(members)
        if n_members > 1:
            err = np.sqrt(np.sum((members - mean)**2) / (n_members - 1))
        else:
            err = 0.0
        return err, err
        
    else:
        # Fallback to symmetric Hessian if unknown
        diff = members - central
        err = np.sqrt(np.sum(diff**2))
        return err, err

def calculate_scale_uncertainty(central, variations):
    """
    Computes scale uncertainty envelope using the 7-point variations.
    The variations list should contain the evaluated predictions.
    We exclude the antipodal scales unless they are in the list.
    """
    variations = np.array(variations)
    if not np.isfinite(central):
        raise ValueError("Central value is not finite.")
    if not np.all(np.isfinite(variations)):
        raise ValueError("One or more variations contain non-finite values.")
        
    if len(variations) == 0:
        return 0.0, 0.0
        
    max_val = np.max(variations)
    min_val = np.min(variations)
    
    err_plus = max(0.0, max_val - central)
    err_minus = max(0.0, central - min_val)
    
    return err_plus, err_minus

def calculate_mc_statistical_uncertainty(weights):
    """
    Computes statistical uncertainty for weighted Monte Carlo events:
    err = sqrt( sum( w_i^2 ) )
    """
    weights = np.array(weights)
    if len(weights) == 0:
        return 0.0
    return np.sqrt(np.sum(weights**2))
