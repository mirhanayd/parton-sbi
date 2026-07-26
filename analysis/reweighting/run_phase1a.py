"""Analyze one predeclared Phase 1A target/physics-level closure case."""

import argparse
import json
from pathlib import Path

from .closure import evaluate_shape_closure
from .plotting import write_closure_plots
from .schema import load_diagnostic_sample


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reweighted", required=True)
    parser.add_argument("--direct-a", required=True)
    parser.add_argument("--direct-b", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ess-fraction", required=True, type=float)
    arguments = parser.parse_args()
    output = Path(arguments.output)
    output.mkdir(parents=True, exist_ok=True)
    reweighted = load_diagnostic_sample(arguments.reweighted)
    direct_a = load_diagnostic_sample(arguments.direct_a)
    direct_b = load_diagnostic_sample(arguments.direct_b)
    result = evaluate_shape_closure(reweighted, direct_a, direct_b)
    result["ess_fraction"] = arguments.ess_fraction
    result["ess_threshold"] = 0.20
    result["ess_pass"] = arguments.ess_fraction >= 0.20
    if not result["ess_pass"]:
        result["decision"] = "FAIL"
        result["decision_reason"] = "DIRECT REGENERATION REQUIRED: ESS/N < 0.20"
    with (output / "closure_metrics.json").open("w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    decision = {
        "schema_version": 1,
        "decision": result["decision"],
        "ess_threshold": 0.20,
        "achieved_ess_fraction": arguments.ess_fraction,
        "failed_observables": result["failed_observable_metrics"],
        "phase1b_permission": result["decision"] == "PASS",
    }
    with (output / "decision.json").open("w", encoding="utf-8") as stream:
        json.dump(decision, stream, indent=2, sort_keys=True)
        stream.write("\n")
    write_closure_plots(output / "plots", reweighted, direct_a, direct_b)


if __name__ == "__main__":
    main()
