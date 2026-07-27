import json
import os
import sys

import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from reweighting.closure import (
    BOOTSTRAP_REPLICATES,
    CRITICAL_ORDER_STATISTIC_RANK,
    EMPIRICAL_TAIL_PROBABILITY_BOUND,
    PER_COMPARISON_ALPHA,
    _conservative_empirical_threshold,
    _pooled_bootstrap_indices,
)
from reweighting.metrics import compare_samples, weighted_histogram
from reweighting.run_phase1a import (
    apply_ess_gate,
    finalize_phase1a_ess_decision,
    single_case_decision,
)
from reweighting.schema import OBSERVABLES, load_diagnostic_sample


def test_weighted_histogram_preserves_sum_w_and_sum_w2():
    histogram = weighted_histogram(
        np.array([0.1, 0.2, 0.8]), np.array([1.0, 2.0, -0.5]), np.array([0.0, 0.5, 1.0])
    )
    np.testing.assert_allclose(histogram.sum_w, [3.0, -0.5])
    np.testing.assert_allclose(histogram.sum_w2, [5.0, 0.25])


def test_weighted_histogram_rejects_values_below_fixed_range():
    with np.testing.assert_raises_regex(ValueError, "fixed bin range"):
        weighted_histogram(
            np.array([-0.01, 0.5]), np.ones(2), np.array([0.0, 0.5, 1.0])
        )


def test_weighted_histogram_rejects_values_above_fixed_range():
    with np.testing.assert_raises_regex(ValueError, "fixed bin range"):
        weighted_histogram(
            np.array([0.5, 1.01]), np.ones(2), np.array([0.0, 0.5, 1.0])
        )


def test_weighted_histogram_accepts_both_range_endpoints():
    histogram = weighted_histogram(
        np.array([0.0, 1.0]), np.ones(2), np.array([0.0, 0.5, 1.0])
    )
    np.testing.assert_allclose(histogram.sum_w, [1.0, 1.0])


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


def test_direct_self_bootstrap_draws_both_samples_from_pooled_null():
    class RecordingGenerator:
        def __init__(self):
            self.calls = []

        def integers(self, low, high, size):
            self.calls.append((low, high, size))
            return np.arange(size) % high

    rng = RecordingGenerator()
    index_a, index_b = _pooled_bootstrap_indices(rng, 12, 5, 7)
    assert rng.calls == [(0, 12, 5), (0, 12, 7)]
    assert index_a.size == 5
    assert index_b.size == 7


def test_empirical_policy_has_predeclared_resolved_conservative_tail():
    assert BOOTSTRAP_REPLICATES == 8191
    assert PER_COMPARISON_ALPHA == 0.05 / 64
    assert CRITICAL_ORDER_STATISTIC_RANK == 8186
    assert EMPIRICAL_TAIL_PROBABILITY_BOUND == 6 / 8192
    assert EMPIRICAL_TAIL_PROBABILITY_BOUND <= PER_COMPARISON_ALPHA
    values = list(reversed(range(BOOTSTRAP_REPLICATES)))
    assert _conservative_empirical_threshold(values) == 8185.0
    assert _conservative_empirical_threshold(values[:-1]) is None


def test_low_ess_case_fails_without_granting_aggregate_permissions():
    shape_result = {
        "decision": "PASS",
        "failed_observable_metrics": [],
    }
    result = apply_ess_gate(shape_result, 0.199)
    assert result["decision"] == "FAIL"
    assert result["ess_pass"] is False
    assert "DIRECT REGENERATION REQUIRED" in result["decision_reason"]

    decision = single_case_decision(
        result,
        physics_level="full-event",
        target_role="mild",
        target_pdf_set="CT18NLO",
        target_pdf_member=24,
    )
    assert decision["case_identity"] == {
        "physics_level": "full-event",
        "target_role": "mild",
        "target_pdf_set": "CT18NLO",
        "target_pdf_member": 24,
    }
    assert decision["aggregate_gate"] == "NOT_EVALUATED"
    assert decision["pool_reuse_permission"] is False
    assert decision["phase1b_permission"] is False


def test_passing_single_case_still_cannot_grant_aggregate_permissions():
    result = apply_ess_gate(
        {"decision": "PASS", "failed_observable_metrics": []}, 0.75
    )
    decision = single_case_decision(
        result,
        physics_level="hard-process",
        target_role="stress",
        target_pdf_set="CT18NLO",
        target_pdf_member=51,
    )
    assert decision["decision"] == "PASS"
    assert decision["pool_reuse_permission"] is False
    assert decision["phase1b_permission"] is False


def test_aggregate_low_ess_finalizes_negative_phase1a_result():
    decision = finalize_phase1a_ess_decision(
        nominal_ess_fraction=0.011,
        mild_ess_fraction=0.012,
        stress_ess_fraction=0.013,
    )
    assert decision["decision"] == "FAIL — NOMINAL-POOL REUSE REJECTED"
    assert decision["direct_closure_executed"] is False
    assert decision["pool_reuse_allowed"] is False
    assert decision["reweighting_path_allowed"] is False
    assert decision["direct_regeneration_required"] is True
    assert decision["phase1a_complete"] is True
    assert decision["phase1bd_planning_permission"] is True


def test_aggregate_ess_pass_never_grants_reuse_without_direct_closure():
    decision = finalize_phase1a_ess_decision(
        nominal_ess_fraction=0.8,
        mild_ess_fraction=0.7,
        stress_ess_fraction=0.6,
    )
    assert decision["decision"] == "PENDING — DIRECT CLOSURE REQUIRED"
    assert decision["pool_reuse_allowed"] is False
    assert decision["reweighting_path_allowed"] is False
    assert decision["phase1a_complete"] is False
    assert decision["phase1bd_planning_permission"] is False
