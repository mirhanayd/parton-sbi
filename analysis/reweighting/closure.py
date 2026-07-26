"""Direct-self-closure-calibrated Phase 1A shape acceptance."""

import numpy as np

from .metrics import FIXED_BINS, compare_samples
from .schema import DiagnosticSample, OBSERVABLES


BOOTSTRAP_REPLICATES = 200
BOOTSTRAP_SEED = 713_2026
FAMILYWISE_ALPHA = 0.05
ACCEPTANCE_METRICS = (
    "chi_square_per_effective_dof",
    "maximum_absolute_populated_bin_pull",
    "jensen_shannon_divergence",
    "wasserstein_distance",
)


def _bootstrap_indices(rng: np.random.Generator, size: int) -> np.ndarray:
    return rng.integers(0, size, size=size)


def evaluate_shape_closure(
    reweighted: DiagnosticSample,
    direct_a: DiagnosticSample,
    direct_b: DiagnosticSample,
) -> dict[str, object]:
    """Apply fixed bins and a Bonferroni-controlled direct-self reference.

    Before any target result is inspected, the per-metric acceptance quantile is
    fixed at `1 - 0.05 / (number of observables * number of metrics)`. A target
    passes only if every defined metric is below its direct-vs-direct bootstrap
    threshold. Undefined metrics make the decision INCONCLUSIVE.
    """
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    quantile = 1.0 - FAMILYWISE_ALPHA / (len(OBSERVABLES) * len(ACCEPTANCE_METRICS))
    observable_results: dict[str, object] = {}
    failed: list[str] = []
    undefined: list[str] = []
    for name in OBSERVABLES:
        edges = FIXED_BINS[name]
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
            index_a = _bootstrap_indices(rng, direct_a.size)
            index_b = _bootstrap_indices(rng, direct_b.size)
            metrics = compare_samples(
                direct_a.observables[name][index_a], direct_a.weights[index_a],
                direct_b.observables[name][index_b], direct_b.weights[index_b], edges,
            )
            for metric in ACCEPTANCE_METRICS:
                if metrics[metric] is not None and np.isfinite(metrics[metric]):
                    references[metric].append(float(metrics[metric]))
        thresholds: dict[str, float | None] = {}
        metric_pass: dict[str, bool | None] = {}
        for metric in ACCEPTANCE_METRICS:
            threshold = (
                float(np.quantile(references[metric], quantile))
                if references[metric] and target_metrics[metric] is not None
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
            "metric_pass": metric_pass,
        }
    decision = "INCONCLUSIVE" if undefined else ("FAIL" if failed else "PASS")
    return {
        "schema_version": 1,
        "binning_policy": "fixed physics-motivated bins declared in metrics.py",
        "low_statistics_rule": "both weighted effective bin counts >= 5",
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "multiple_observable_policy": "Bonferroni familywise alpha 0.05 across observables and metrics",
        "acceptance_quantile": quantile,
        "decision": decision,
        "failed_observable_metrics": failed,
        "undefined_observable_metrics": undefined,
        "observables": observable_results,
    }
