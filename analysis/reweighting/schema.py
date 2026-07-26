"""Versioned loader for compact Rust Phase 1A event diagnostics."""

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np


OBSERVABLES = (
    "log10_x",
    "log10_q2",
    "y",
    "log10_w2",
    "scattered_electron_energy",
    "scattered_electron_cos_theta",
    "final_state_multiplicity",
    "charged_final_state_multiplicity",
    "visible_final_state_energy",
    "scalar_final_state_pt_sum",
    "leading_stable_hadron_pt",
    "electron_muon_fraction",
    "photon_fraction",
    "neutrino_fraction",
    "hadron_fraction",
    "other_fraction",
)


@dataclass(frozen=True)
class DiagnosticSample:
    event_numbers: np.ndarray
    weights: np.ndarray
    observables: dict[str, np.ndarray]

    @property
    def size(self) -> int:
        return int(self.weights.size)


def load_diagnostic_sample(path: str | Path) -> DiagnosticSample:
    """Load valid diagnostics without exposing hidden PDF truth as observables."""
    events: list[int] = []
    weights: list[float] = []
    values = {name: [] for name in OBSERVABLES}
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not record.get("valid", False):
                continue
            observable = record.get("observables")
            if observable is None:
                raise ValueError(f"missing observables at {path}:{line_number}")
            weight = float(record["target_event_weight"])
            if not np.isfinite(weight):
                raise ValueError(f"non-finite target weight at {path}:{line_number}")
            events.append(int(record["event_number"]))
            weights.append(weight)
            for name in OBSERVABLES:
                value = float(observable[name])
                if not np.isfinite(value):
                    raise ValueError(f"non-finite {name} at {path}:{line_number}")
                values[name].append(value)
    if not events:
        raise ValueError(f"no valid events in {path}")
    return DiagnosticSample(
        event_numbers=np.asarray(events, dtype=np.int64),
        weights=np.asarray(weights, dtype=np.float64),
        observables={name: np.asarray(data, dtype=np.float64) for name, data in values.items()},
    )
