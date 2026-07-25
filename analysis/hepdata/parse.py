import os
import pandas as pd
from .schemas import validate_data_columns

def parse_dataset(filepath):
    """
    Parses the HERA ASCII data table and returns a validated pandas DataFrame.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"HERA data file not found: {filepath}")
        
    # Read the whitespace-separated values
    try:
        df = pd.read_csv(filepath, sep=r'\s+')
    except Exception as e:
        raise ValueError(f"Failed to parse ASCII table: {e}")
        
    # Validate columns
    validate_data_columns(df)
    
    return df
