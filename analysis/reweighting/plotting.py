"""Diagnostic-only closure plots; plots never determine acceptance."""

from pathlib import Path

import matplotlib.pyplot as plt

from .metrics import FIXED_BINS
from .schema import DiagnosticSample, OBSERVABLES


def write_closure_plots(
    output: str | Path,
    reweighted: DiagnosticSample,
    direct_a: DiagnosticSample,
    direct_b: DiagnosticSample,
) -> None:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name in OBSERVABLES:
        figure, axis = plt.subplots(figsize=(6.4, 4.2))
        for sample, label in (
            (reweighted, "reweighted nominal"),
            (direct_a, "direct target A"),
            (direct_b, "direct target B"),
        ):
            axis.hist(
                sample.observables[name], bins=FIXED_BINS[name], weights=sample.weights,
                density=True, histtype="step", linewidth=1.4, label=label,
            )
        axis.set_xlabel(name)
        axis.set_ylabel("normalized weighted density")
        axis.set_title("DIAGNOSTIC ONLY — NOT USED FOR ACCEPTANCE")
        axis.legend()
        figure.tight_layout()
        figure.savefig(output / f"{name}.png", dpi=140)
        plt.close(figure)
