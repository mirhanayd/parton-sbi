"""Predeclared weighted one-dimensional closure metrics."""

from dataclasses import dataclass

import numpy as np
from scipy.spatial.distance import jensenshannon
from scipy.stats import wasserstein_distance


LOW_STAT_EFFECTIVE_COUNT = 5.0


FIXED_BINS = {
    "log10_x": np.linspace(-4.0, np.log10(0.8), 17),
    "log10_q2": np.linspace(np.log10(3.5), 4.0, 17),
    "y": np.linspace(0.01, 0.95, 17),
    "log10_w2": np.linspace(0.0, 5.1, 17),
    "scattered_electron_energy": np.linspace(0.0, 28.0, 17),
    "scattered_electron_cos_theta": np.linspace(-1.0, 1.0, 17),
    "final_state_multiplicity": np.linspace(-0.5, 120.5, 18),
    "charged_final_state_multiplicity": np.linspace(-0.5, 70.5, 18),
    "visible_final_state_energy": np.linspace(0.0, 1000.0, 17),
    "scalar_final_state_pt_sum": np.linspace(0.0, 250.0, 17),
    "leading_stable_hadron_pt": np.linspace(0.0, 100.0, 17),
    "electron_muon_fraction": np.linspace(0.0, 1.0, 12),
    "photon_fraction": np.linspace(0.0, 1.0, 12),
    "neutrino_fraction": np.linspace(0.0, 1.0, 12),
    "hadron_fraction": np.linspace(0.0, 1.0, 12),
    "other_fraction": np.linspace(0.0, 1.0, 12),
}


@dataclass(frozen=True)
class WeightedHistogram:
    edges: np.ndarray
    sum_w: np.ndarray
    sum_w2: np.ndarray

    @property
    def total_weight(self) -> float:
        return float(self.sum_w.sum())

    @property
    def normalized(self) -> np.ndarray:
        return self.sum_w / self.total_weight

    @property
    def normalized_variance(self) -> np.ndarray:
        return self.sum_w2 / self.total_weight**2


def weighted_histogram(values: np.ndarray, weights: np.ndarray, edges: np.ndarray) -> WeightedHistogram:
    values = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if values.shape != weights.shape:
        raise ValueError("values and weights must have identical shape")
    if not np.all(np.isfinite(values)) or not np.all(np.isfinite(weights)):
        raise ValueError("histogram inputs must be finite")
    sum_w, _ = np.histogram(values, bins=edges, weights=weights)
    sum_w2, _ = np.histogram(values, bins=edges, weights=weights * weights)
    return WeightedHistogram(np.asarray(edges), sum_w.astype(float), sum_w2.astype(float))


def _effective_count(histogram: WeightedHistogram) -> np.ndarray:
    result = np.zeros_like(histogram.sum_w)
    positive = histogram.sum_w2 > 0.0
    result[positive] = histogram.sum_w[positive] ** 2 / histogram.sum_w2[positive]
    return result


def compare_histograms(left: WeightedHistogram, right: WeightedHistogram) -> dict[str, object]:
    if left.total_weight == 0.0 or right.total_weight == 0.0:
        raise ValueError("shape metrics require non-zero total weight")
    left_probability = left.normalized
    right_probability = right.normalized
    variance = left.normalized_variance + right.normalized_variance
    populated = (
        (_effective_count(left) >= LOW_STAT_EFFECTIVE_COUNT)
        & (_effective_count(right) >= LOW_STAT_EFFECTIVE_COUNT)
        & (variance > 0.0)
    )
    differences = left_probability - right_probability
    pulls = np.zeros_like(differences)
    pulls[populated] = differences[populated] / np.sqrt(variance[populated])
    chi_square = float(np.sum(pulls[populated] ** 2)) if np.any(populated) else None
    degrees = max(int(np.count_nonzero(populated)) - 1, 0)
    chi_square_per_dof = chi_square / degrees if chi_square is not None and degrees > 0 else None
    maximum_pull = float(np.max(np.abs(pulls[populated]))) if np.any(populated) else None
    js = None
    if np.all(left_probability >= 0.0) and np.all(right_probability >= 0.0):
        js = float(jensenshannon(left_probability, right_probability, base=2.0) ** 2)
    return {
        "sum_w_left": left.sum_w.tolist(),
        "sum_w2_left": left.sum_w2.tolist(),
        "sum_w_right": right.sum_w.tolist(),
        "sum_w2_right": right.sum_w2.tolist(),
        "populated_bin_mask": populated.tolist(),
        "populated_bins": int(np.count_nonzero(populated)),
        "chi_square": chi_square,
        "chi_square_per_effective_dof": chi_square_per_dof,
        "maximum_absolute_populated_bin_pull": maximum_pull,
        "jensen_shannon_divergence": js,
    }


def compare_samples(
    left_values: np.ndarray,
    left_weights: np.ndarray,
    right_values: np.ndarray,
    right_weights: np.ndarray,
    edges: np.ndarray,
) -> dict[str, object]:
    left = weighted_histogram(left_values, left_weights, edges)
    right = weighted_histogram(right_values, right_weights, edges)
    result = compare_histograms(left, right)
    result["bin_edges"] = np.asarray(edges).tolist()
    result["wasserstein_distance"] = None
    if np.all(left_weights >= 0.0) and np.all(right_weights >= 0.0):
        result["wasserstein_distance"] = float(
            wasserstein_distance(left_values, right_values, left_weights, right_weights)
        )
    return result
