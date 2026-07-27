"""Direct-self-closure-calibrated Phase 1A shape acceptance."""

import math

import numpy as np

from .metrics import FIXED_BINS, compare_samples
from .schema import DiagnosticSample, OBSERVABLES


BOOTSTRAP_REPLICATES = 8191
BOOTSTRAP_SEED = 713_2026
FAMILYWISE_ALPHA = 0.05
ACCEPTANCE_METRICS = (
    "chi_square_per_effective_dof",
    "maximum_absolute_populated_bin_pull",
    "jensen_shannon_divergence",
    "wasserstein_distance",
)
OBSERVABLE_METRIC_COMPARISONS = len(OBSERVABLES) * len(ACCEPTANCE_METRICS)
PER_COMPARISON_ALPHA = FAMILYWISE_ALPHA / OBSERVABLE_METRIC_COMPARISONS
# With B null replicates and one future target statistic, this rank makes the
# exchangeable upper-tail false-rejection probability no larger than alpha.
CRITICAL_ORDER_STATISTIC_RANK = math.ceil(
    (BOOTSTRAP_REPLICATES + 1) * (1.0 - PER_COMPARISON_ALPHA)
)
EMPIRICAL_TAIL_PROBABILITY_BOUND = (
    BOOTSTRAP_REPLICATES + 1 - CRITICAL_ORDER_STATISTIC_RANK
) / (BOOTSTRAP_REPLICATES + 1)


def _bootstrap_indices(
    rng: np.random.Generator, population_size: int, sample_size: int
) -> np.ndarray:
    return rng.integers(0, population_size, size=sample_size)


def _pooled_bootstrap_indices(
    rng: np.random.Generator,
    pooled_size: int,
    direct_a_size: int,
    direct_b_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Draw two independent null samples from the pooled direct A+B sample."""
    return (
        _bootstrap_indices(rng, pooled_size, direct_a_size),
        _bootstrap_indices(rng, pooled_size, direct_b_size),
    )


def _conservative_empirical_threshold(values: list[float]) -> float | None:
    """Return the predeclared non-interpolated finite-sample critical value."""
    if len(values) != BOOTSTRAP_REPLICATES:
        return None
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    return float(ordered[CRITICAL_ORDER_STATISTIC_RANK - 1])


def evaluate_shape_closure(
    reweighted: DiagnosticSample,
    direct_a: DiagnosticSample,
    direct_b: DiagnosticSample,
) -> dict[str, object]:
    """Apply fixed bins and a conservative empirical direct-self reference.

    Alpha 0.05 is preallocated equally across the 64 observable-metric tests.
    Each threshold is the fixed finite-sample order statistic from 8,191 pooled
    direct-null bootstrap replicates, without interpolation. A target passes
    only if every defined metric is at or below its threshold. Undefined or
    underresolved metrics make the decision INCONCLUSIVE.
    """
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    observable_results: dict[str, object] = {}
    failed: list[str] = []
    undefined: list[str] = []
    pooled_weights = np.concatenate((direct_a.weights, direct_b.weights))
    pooled_size = pooled_weights.size
    for name in OBSERVABLES:
        edges = FIXED_BINS[name]
        pooled_values = np.concatenate(
            (direct_a.observables[name], direct_b.observables[name])
        )
        self_metrics = compare_samples(
            direct_a.observables[name], direct_a.weights,
            direct_b.observables[name], direct_b.weights, edges,
        )
        target_metrics = compare_samples(
            reweighted.observables[name], reweighted.weights,
            direct_b.observables[name], direct_b.weights, edges,
        )
        references = {metric: [] for metric in ACCEPTANCE_METRICS}
        for _ in range(BOOTSTRAP_REPLICATES):
            index_a, index_b = _pooled_bootstrap_indices(
                rng, pooled_size, direct_a.size, direct_b.size
            )
            metrics = compare_samples(
                pooled_values[index_a], pooled_weights[index_a],
                pooled_values[index_b], pooled_weights[index_b], edges,
            )
            for metric in ACCEPTANCE_METRICS:
                if metrics[metric] is not None and np.isfinite(metrics[metric]):
                    references[metric].append(float(metrics[metric]))
        thresholds: dict[str, float | None] = {}
        metric_pass: dict[str, bool | None] = {}
        for metric in ACCEPTANCE_METRICS:
            threshold = (
                _conservative_empirical_threshold(references[metric])
                if target_metrics[metric] is not None
                else None
            )
            thresholds[metric] = threshold
            if threshold is None or not np.isfinite(target_metrics[metric]):
                metric_pass[metric] = None
                undefined.append(f"{name}:{metric}")
            else:
                metric_pass[metric] = bool(target_metrics[metric] <= threshold)
                if not metric_pass[metric]:
                    failed.append(f"{name}:{metric}")
        observable_results[name] = {
            "direct_vs_direct": self_metrics,
            "reweighted_vs_direct": target_metrics,
            "bootstrap_thresholds": thresholds,
            "valid_bootstrap_replicates": {
                metric: len(references[metric]) for metric in ACCEPTANCE_METRICS
            },
            "metric_pass": metric_pass,
        }
    decision = "INCONCLUSIVE" if undefined else ("FAIL" if failed else "PASS")
    return {
        "schema_version": 1,
        "binning_policy": "fixed physics-motivated bins declared in metrics.py",
        "low_statistics_rule": "both weighted effective bin counts >= 5",
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "multiple_observable_policy": (
            "predeclared conservative empirical familywise policy: alpha 0.05 "
            "allocated equally across 64 observable-metric comparisons"
        ),
        "familywise_alpha": FAMILYWISE_ALPHA,
        "observable_metric_comparisons": OBSERVABLE_METRIC_COMPARISONS,
        "per_comparison_alpha": PER_COMPARISON_ALPHA,
        "critical_order_statistic_rank": CRITICAL_ORDER_STATISTIC_RANK,
        "threshold_order_statistic_policy": (
            "ascending non-interpolated rank ceil((B + 1) * (1 - alpha / 64))"
        ),
        "empirical_tail_probability_bound": EMPIRICAL_TAIL_PROBABILITY_BOUND,
        "decision": decision,
        "failed_observable_metrics": failed,
        "undefined_observable_metrics": undefined,
        "observables": observable_results,
    }
