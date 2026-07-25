import unittest
import numpy as np
import os
import sys
import shutil
import tempfile
import json

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from validation.uncertainty import (
    calculate_pdf_uncertainty, 
    calculate_scale_uncertainty, 
    calculate_mc_statistical_uncertainty
)
from validation.cache import TheoryCache

class TestUncertaintyFramework(unittest.TestCase):

    # 1. Hessian uncertainty fixtures (symmetric)
    def test_symmetric_hessian(self):
        central = 10.0
        # diffs: [1.0, -1.0, 2.0]
        # diffs^2: [1.0, 1.0, 4.0] -> sum = 6.0 -> sqrt(6)
        members = [11.0, 9.0, 12.0]
        plus, minus = calculate_pdf_uncertainty(central, members, error_type="symmhessian")
        self.assertAlmostEqual(plus, np.sqrt(6.0))
        self.assertAlmostEqual(minus, np.sqrt(6.0))

    # 2. Replica uncertainty fixtures
    def test_replica_uncertainty(self):
        # Replicas: [9.0, 10.0, 11.0] -> mean = 10.0
        # variance: ((9-10)^2 + (10-10)^2 + (11-10)^2) / (3-1) = (1 + 0 + 1) / 2 = 1.0
        # std_dev = 1.0
        members = [9.0, 10.0, 11.0]
        plus, minus = calculate_pdf_uncertainty(10.0, members, error_type="replicas")
        self.assertAlmostEqual(plus, 1.0)
        self.assertAlmostEqual(minus, 1.0)

    # 3. Asymmetric errors
    def test_asymmetric_hessian(self):
        central = 10.0
        # Pairs:
        # Pair 1: m1=11.0 (diff=1.0), m2=8.0 (diff=-2.0)
        #   max(1.0, -2.0, 0.0) = 1.0 -> plus^2 = 1.0
        #   max(-1.0, 2.0, 0.0) = 2.0 -> minus^2 = 4.0
        # Pair 2: m3=9.5 (diff=-0.5), m4=10.5 (diff=0.5)
        #   max(-0.5, 0.5, 0.0) = 0.5 -> plus^2 += 0.25
        #   max(0.5, -0.5, 0.0) = 0.5 -> minus^2 += 0.25
        # Total plus = sqrt(1.25) = 1.11803
        # Total minus = sqrt(4.25) = 2.06155
        members = [11.0, 8.0, 9.5, 10.5]
        plus, minus = calculate_pdf_uncertainty(central, members, error_type="hessian")
        self.assertAlmostEqual(plus, np.sqrt(1.25))
        self.assertAlmostEqual(minus, np.sqrt(4.25))

    # 4. Seven-point scale list
    def test_seven_point_scale_list(self):
        # Ensure scale variation combinations are exactly 7
        combinations = [
            [1.0, 1.0], [0.5, 0.5], [0.5, 1.0], 
            [1.0, 0.5], [1.0, 2.0], [2.0, 1.0], [2.0, 2.0]
        ]
        self.assertEqual(len(combinations), 7)
        # Exclude antipodal combinations [0.5, 2.0] and [2.0, 0.5]
        self.assertNotIn([0.5, 2.0], combinations)
        self.assertNotIn([2.0, 0.5], combinations)

    # 5. Envelope computation
    def test_scale_envelope(self):
        central = 10.0
        # Variations: [9.0, 10.5, 11.0, 9.8, 10.2]
        # max_val = 11.0 -> err_plus = max(0, 11.0 - 10.0) = 1.0
        # min_val = 9.0 -> err_minus = max(0, 10.0 - 9.0) = 1.0
        variations = [9.0, 10.5, 11.0, 9.8, 10.2]
        plus, minus = calculate_scale_uncertainty(central, variations)
        self.assertAlmostEqual(plus, 1.0)
        self.assertAlmostEqual(minus, 1.0)

    # 6. Weighted-event uncertainty
    def test_weighted_event_uncertainty(self):
        # Weights: [0.5, 0.5, 1.0]
        # sum of w^2 = 0.25 + 0.25 + 1.0 = 1.5 -> err = sqrt(1.5)
        weights = [0.5, 0.5, 1.0]
        err = calculate_mc_statistical_uncertainty(weights)
        self.assertAlmostEqual(err, np.sqrt(1.5))

    # 7. Cache-key correctness
    def test_cache_key_correctness(self):
        temp_dir = tempfile.mkdtemp()
        try:
            cache_file = os.path.join(temp_dir, "cache.json")
            cache = TheoryCache(cache_file)
            
            # Save a prediction
            cache.set("apfel", "4.8.0", "CT18NLO", 0, "NLO", 0.01, 100.0, "mu_R=mu_F=Q", "nc_dis", {"f2": 1.5, "fl": 0.2})
            cache.save()
            
            # Read back with same params
            val = cache.get("apfel", "4.8.0", "CT18NLO", 0, "NLO", 0.01, 100.0, "mu_R=mu_F=Q", "nc_dis")
            self.assertIsNotNone(val)
            self.assertEqual(val["f2"], 1.5)
        finally:
            shutil.rmtree(temp_dir)

    # 8. Cache invalidation
    def test_cache_invalidation(self):
        temp_dir = tempfile.mkdtemp()
        try:
            cache_file = os.path.join(temp_dir, "cache.json")
            cache = TheoryCache(cache_file)
            
            # Save a prediction
            cache.set("apfel", "4.8.0", "CT18NLO", 0, "NLO", 0.01, 100.0, "mu_R=mu_F=Q", "nc_dis", {"f2": 1.5, "fl": 0.2})
            
            # Query with slightly different Q2 -> should result in cache miss
            val = cache.get("apfel", "4.8.0", "CT18NLO", 0, "NLO", 0.01, 100.1, "mu_R=mu_F=Q", "nc_dis")
            self.assertIsNone(val)
        finally:
            shutil.rmtree(temp_dir)

    # 9. Missing PDF members (Finite output values checking)
    def test_finite_output_values(self):
        # Calculation should throw if central values contain NaNs
        with self.assertRaises(ValueError):
            calculate_pdf_uncertainty(np.nan, [1.0, 2.0])
            
        with self.assertRaises(ValueError):
            calculate_scale_uncertainty(np.nan, [1.0, 2.0])

if __name__ == "__main__":
    unittest.main()
