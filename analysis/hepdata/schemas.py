import os
import json

def validate_metadata(metadata):
    """
    Validates the dataset metadata format and completeness.
    """
    required_keys = {
        "dataset_id", 
        "name", 
        "description", 
        "source_url", 
        "download_date", 
        "checksum_sha256", 
        "citation"
    }
    
    missing = required_keys - set(metadata.keys())
    if missing:
        raise ValueError(f"Missing required metadata keys: {missing}")
        
    # Ensure fields are non-empty strings
    for k in required_keys:
        if not str(metadata[k]).strip():
            raise ValueError(f"Metadata key '{k}' must not be empty.")

def validate_data_columns(df):
    """
    Validates that the parsed pandas DataFrame has the required columns for analysis.
    """
    required_columns = ["Q2", "x", "y", "Sigma", "stat", "uncor"]
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing required column in HERA data: {col}")
            
    # Also verify that systematic columns exist
    sys_cols = [c for c in df.columns if c.startswith("sys")]
    if not sys_cols:
        raise ValueError("No systematic uncertainty columns (sys*) found in parsed data.")
