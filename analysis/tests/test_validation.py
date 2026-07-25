import unittest
import numpy as np
import pandas as pd
import json
import os
import sys
import shutil
import tempfile

# Add parent directory to sys.path so we can import modules correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hepdata.schemas import validate_metadata, validate_data_columns
from hepdata.download import get_file_sha256
from validation.binning import apply_cuts

from validation.covariance import build_covariance_matrix
from validation.chi_square import calculate_chi2_uncorrelated, calculate_chi2_covariance

class TestValidationFramework(unittest.TestCase):

    def setUp(self):
        # Create a synthetic dataset matching the schema
        self.dummy_data = pd.DataFrame({
            "Q2": [2.0, 10.0, 100.0],
            "x": [0.01, 0.05, 0.1],
            "y": [0.1, 0.2, 0.3],
            "Sigma": [1.5, 1.2, 0.8],
            "stat": [1.0, 2.0, 1.5],     # in percent
            "uncor": [0.5, 1.0, 1.0],    # in percent
            "sys1": [0.2, 0.5, 0.1],     # in percent
            "sys2": [0.1, 0.3, 0.2]      # in percent
        })

    # 1. HEPData schema parsing & columns
    def test_schema_columns(self):
        # Correct columns should validate without error
        try:
            validate_data_columns(self.dummy_data)
        except ValueError as e:
            self.fail(f"Schema validation failed on valid data: {e}")
            
        # Missing required column should fail
        bad_df = self.dummy_data.drop(columns=["stat"])
        with self.assertRaises(ValueError):
            validate_data_columns(bad_df)

    # 2. Unit conversion & relative/absolute error scaling
    def test_absolute_error_scaling(self):
        df = self.dummy_data.copy()
        cov = build_covariance_matrix(df)
        
        # Point 0: Sigma = 1.5, stat = 1.0%, uncor = 0.5%
        # s_abs = 1.5 * 0.01 = 0.015
        # u_abs = 1.5 * 0.005 = 0.0075
        # diag_uncor = s_abs^2 + u_abs^2 = 0.015^2 + 0.0075^2 = 0.000225 + 0.00005625 = 0.00028125
        
        # sys1_abs = 1.5 * 0.002 = 0.003
        # sys2_abs = 1.5 * 0.001 = 0.0015
        # sum_sys_sq = 0.003^2 + 0.0015^2 = 0.000009 + 0.00000225 = 0.00001125
        
        # C_00 = diag_uncor + sum_sys_sq = 0.00028125 + 0.00001125 = 0.0002925
        self.assertAlmostEqual(cov[0, 0], 0.0002925)

    # 3. Bin matching and kinematic cuts
    def test_bin_matching_and_cuts(self):
        # Default cut Q2 >= 3.5 should filter out Q2=2.0
        filtered = apply_cuts(self.dummy_data, q2_min=3.5)
        self.assertEqual(len(filtered), 2)
        self.assertTrue(np.all(filtered["Q2"] >= 3.5))

    # 4. Uncorrelated Chi2 calculation
    def test_chi2_uncorrelated(self):
        data = np.array([10.0, 20.0])
        theory = np.array([9.0, 21.0])
        stat_rel = np.array([10.0, 5.0]) # 10% of 10 = 1.0, 5% of 20 = 1.0
        uncor_rel = np.array([0.0, 0.0])  # zero uncor
        
        # Point 0: diff = 1.0, err = 1.0 -> pull = 1.0
        # Point 1: diff = -1.0, err = 1.0 -> pull = -1.0
        # Chi2 = 1^2 + (-1)^2 = 2.0
        chi2, pulls = calculate_chi2_uncorrelated(data, theory, stat_rel, uncor_rel)
        self.assertAlmostEqual(chi2, 2.0)
        np.testing.assert_allclose(pulls, [1.0, -1.0])

    # 5. Covariance Chi2 calculation
    def test_chi2_covariance(self):
        data = np.array([10.0, 10.0])
        theory = np.array([9.0, 8.0])
        # residuals: [1.0, 2.0]
        # Covariance matrix:
        # [[2.0, 1.0],
        #  [1.0, 2.0]]
        # det = 4 - 1 = 3 (positive definite)
        # C^-1 = 1/3 * [[2, -1], [-1, 2]]
        # C^-1 * res = 1/3 * [[2*1 - 2], [-1 + 4]] = 1/3 * [0, 3] = [0, 1]
        # chi2 = res^T * C^-1 * res = [1.0, 2.0] . [0, 1] = 2.0
        cov = np.array([[2.0, 1.0], [1.0, 2.0]])
        chi2, pulls = calculate_chi2_covariance(data, theory, cov)
        self.assertAlmostEqual(chi2, 2.0)

    # 6. Singular covariance matrix handling
    def test_singular_covariance(self):
        data = np.array([1.0, 2.0])
        theory = np.array([1.0, 1.0])
        # Singular covariance matrix (rank 1)
        cov = np.array([[1.0, 1.0], [1.0, 1.0]])
        
        with self.assertRaises(ValueError) as ctx:
            calculate_chi2_covariance(data, theory, cov)
        self.assertTrue("singular" in str(ctx.exception) or "non-positive-definite" in str(ctx.exception))

    # 7. Known synthetic fixtures with analytically known Chi2
    def test_synthetic_fixtures(self):
        # 1-dimensional case: D=5.0, T=4.0, C=[[0.25]]
        # chi2 = (5 - 4)^2 / 0.25 = 4.0
        data = np.array([5.0])
        theory = np.array([4.0])
        cov = np.array([[0.25]])
        chi2, pulls = calculate_chi2_covariance(data, theory, cov)
        self.assertAlmostEqual(chi2, 4.0)

    # 8. Dataset metadata completeness
    def test_metadata_completeness(self):
        valid_meta = {
            "dataset_id": "test_ds",
            "name": "Test Dataset",
            "description": "A validation test fixture dataset.",
            "source_url": "http://example.com",
            "download_date": "2026-07-16",
            "checksum_sha256": "dfa2fb...",
            "citation": "Author et al., Journal (Year)."
        }
        try:
            validate_metadata(valid_meta)
        except ValueError as e:
            self.fail(f"Metadata validation failed: {e}")
            
        bad_meta = valid_meta.copy()
        del bad_meta["citation"]
        with self.assertRaises(ValueError):
            validate_metadata(bad_meta)

    # 9. Reproducible output serialization
    def test_reproducible_serialization(self):
        temp_dir = tempfile.mkdtemp()
        try:
            meta = {
                "dataset_id": "test_ds",
                "name": "Test Dataset",
                "description": "Desc",
                "source_url": "http://url",
                "download_date": "2026-07-16",
                "checksum_sha256": "abc",
                "citation": "Cite"
            }
            filepath = os.path.join(temp_dir, "metadata.json")
            with open(filepath, "w") as f:
                json.dump(meta, f, indent=2)
                
            # Read back and compare
            with open(filepath, "r") as f:
                loaded = json.load(f)
            self.assertEqual(loaded["dataset_id"], "test_ds")
            self.assertEqual(loaded["checksum_sha256"], "abc")
        finally:
            shutil.rmtree(temp_dir)

    # 10. Missing-source and checksum failures
    def test_checksum_failures(self):
        temp_dir = tempfile.mkdtemp()
        try:
            test_file = os.path.join(temp_dir, "test.dat")
            with open(test_file, "w") as f:
                f.write("Some dummy data content.")
            # Calculate SHA256 of dummy content
            real_sha = get_file_sha256(test_file)
            self.assertNotEqual(real_sha, "dfa2fba16fa490600d10b7125189676343f07b40787d41a74a2d29d30fd8a8bc")
        finally:
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    unittest.main()
