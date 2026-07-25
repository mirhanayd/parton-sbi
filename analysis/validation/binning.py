def apply_cuts(df, q2_min=3.5, q2_max=100000.0, x_min=0.0, x_max=1.0, y_min=0.0, y_max=1.0):
    """
    Applies standard kinematic cuts to the HERA dataset.
    """
    filtered_df = df[
        (df["Q2"] >= q2_min) & (df["Q2"] <= q2_max) &
        (df["x"] >= x_min) & (df["x"] <= x_max) &
        (df["y"] >= y_min) & (df["y"] <= y_max)
    ].copy()
    
    return filtered_df
