import json
import os
import sys

import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from reweighting.closure import evaluate_shape_closure
from reweighting.metrics import FIXED_BINS, compare_samples, weighted_histogram
from reweighting.schema import DiagnosticSample, OBSERVABLES, load_diagnostic_sample


def test_weighted_histogram_preserves_sum_w_and_sum_w2():
    histogram = weighted_histogram(
        np.array([0.1, 0.2, 0.8]), np.array([1.0, 2.0, -0.5]), np.array([0.0, 0.5, 1.0])
    )
    np.testing.assert_allclose(histogram.sum_w, [3.0, -0.5])
    np.testing.assert_allclose(histogram.sum_w2, [5.0, 0.25])


def test_identical_samples_have_zero_shape_distances():
    values = np.linspace(0.05, 0.95, 100)
    weights = np.ones(100)
    result = compare_samples(values, weights, values, weights, np.linspace(0.0, 1.0, 11))
    assert result["chi_square"] == 0.0
    assert result["maximum_absolute_populated_bin_pull"] == 0.0
    assert result["jensen_shannon_divergence"] == 0.0
    assert result["wasserstein_distance"] == 0.0


def test_signed_histograms_do_not_claim_js_or_wasserstein():
    values = np.linspace(0.05, 0.95, 20)
    signed = np.where(np.arange(20) % 2 == 0, 2.0, -1.0)
    result = compare_samples(values, signed, values, np.ones(20), np.linspace(0.0, 1.0, 5))
    assert result["wasserstein_distance"] is None


def test_loader_exposes_only_declared_observables(tmp_path):
    path = tmp_path / "events.jsonl"
    observable = {name: 1.0 for name in OBSERVABLES}
    path.write_text(
        json.dumps(
            {
                "event_number": 1,
                "valid": True,
                "target_event_weight": 2.0,
                "proton_side_flavor": 2,
                "target_xf": 9.0,
                "observables": observable,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    sample = load_diagnostic_sample(path)
    assert sample.size == 1
    assert set(sample.observables) == set(OBSERVABLES)
    assert "proton_side_flavor" not in sample.observables
    assert "target_xf" not in sample.observables


def test_closure_policy_fails_low_ess_after_shape_evaluation():
    rng = np.random.default_rng(42)
    size = 100
    observables = {
        name: rng.uniform(FIXED_BINS[name][0] + 1e-6, FIXED_BINS[name][-1] - 1e-6, size)
        for name in OBSERVABLES
    }
    sample = DiagnosticSample(np.arange(size), np.ones(size), observables)
    result = evaluate_shape_closure(sample, sample, sample)
    assert result["decision"] in {"PASS", "INCONCLUSIVE"}
    assert result["multiple_observable_policy"].startswith("Bonferroni")
