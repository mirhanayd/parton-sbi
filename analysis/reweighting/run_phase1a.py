"""Analyze one predeclared Phase 1A target/physics-level closure case."""

import argparse
import json
import platform
from pathlib import Path

from .closure import evaluate_shape_closure
from .plotting import write_closure_plots
from .schema import load_diagnostic_sample


ESS_THRESHOLD = 0.20


def finalize_phase1a_ess_decision(
    *,
    nominal_ess_fraction: float,
    mild_ess_fraction: float,
    stress_ess_fraction: float,
    direct_closure_passed: bool | None = None,
) -> dict[str, object]:
    """Apply the aggregate predeclared ESS gate before any direct closure."""
    fractions = {
        "nominal": nominal_ess_fraction,
        "mild": mild_ess_fraction,
        "stress": stress_ess_fraction,
    }
    if any(not 0.0 <= value <= 1.0 for value in fractions.values()):
        raise ValueError("all ESS fractions must be between zero and one")
    failed = [name for name, value in fractions.items() if value < ESS_THRESHOLD]
    if failed:
        return {
            "schema_version": 1,
            "decision": "FAIL — NOMINAL-POOL REUSE REJECTED",
            "reason": "DIRECT REGENERATION REQUIRED: predeclared ESS/N gate failed",
            "ess_threshold": ESS_THRESHOLD,
            "ess_fractions": fractions,
            "failed_ess_roles": failed,
            "direct_closure_executed": False,
            "pool_reuse_allowed": False,
            "reweighting_path_allowed": False,
            "direct_regeneration_required": True,
            "phase1a_complete": True,
            "phase1bd_planning_permission": True,
        }
    if direct_closure_passed is not True:
        return {
            "schema_version": 1,
            "decision": "PENDING — DIRECT CLOSURE REQUIRED",
            "reason": "ESS passed, but ESS alone cannot validate pool reuse",
            "ess_threshold": ESS_THRESHOLD,
            "ess_fractions": fractions,
            "failed_ess_roles": [],
            "direct_closure_executed": direct_closure_passed is not None,
            "pool_reuse_allowed": False,
            "reweighting_path_allowed": False,
            "direct_regeneration_required": False,
            "phase1a_complete": False,
            "phase1bd_planning_permission": False,
        }
    return {
        "schema_version": 1,
        "decision": "PASS",
        "reason": "ESS and independently seeded direct closure passed",
        "ess_threshold": ESS_THRESHOLD,
        "ess_fractions": fractions,
        "failed_ess_roles": [],
        "direct_closure_executed": True,
        "pool_reuse_allowed": True,
        "reweighting_path_allowed": True,
        "direct_regeneration_required": False,
        "phase1a_complete": True,
        "phase1bd_planning_permission": False,
    }


def apply_ess_gate(shape_result: dict[str, object], ess_fraction: float) -> dict[str, object]:
    """Apply the mandatory single-case ESS stop without mutating shape output."""
    if not 0.0 <= ess_fraction <= 1.0:
        raise ValueError("ESS fraction must be between zero and one")
    result = dict(shape_result)
    result["ess_fraction"] = ess_fraction
    result["ess_threshold"] = ESS_THRESHOLD
    result["ess_pass"] = ess_fraction >= ESS_THRESHOLD
    if not result["ess_pass"]:
        result["decision"] = "FAIL"
        result["decision_reason"] = "DIRECT REGENERATION REQUIRED: ESS/N < 0.20"
    return result


def single_case_decision(
    result: dict[str, object],
    *,
    physics_level: str,
    target_role: str,
    target_pdf_set: str,
    target_pdf_member: int,
) -> dict[str, object]:
    """Record one case without granting aggregate Phase 1A permissions."""
    return {
        "schema_version": 1,
        "case_identity": {
            "physics_level": physics_level,
            "target_role": target_role,
            "target_pdf_set": target_pdf_set,
            "target_pdf_member": target_pdf_member,
        },
        "decision": result["decision"],
        "ess_threshold": ESS_THRESHOLD,
        "achieved_ess_fraction": result["ess_fraction"],
        "failed_observables": result["failed_observable_metrics"],
        "aggregate_gate": "NOT_EVALUATED",
        "aggregate_gate_reason": (
            "a single physics-level/target case cannot evaluate the aggregate "
            "Phase 1A gate"
        ),
        "pool_reuse_permission": False,
        "phase1b_permission": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reweighted", required=True)
    parser.add_argument("--direct-a", required=True)
    parser.add_argument("--direct-b", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ess-fraction", required=True, type=float)
    parser.add_argument(
        "--physics-level", required=True, choices=("hard-process", "full-event")
    )
    parser.add_argument("--target-role", required=True, choices=("mild", "stress"))
    parser.add_argument("--target-pdf-set", required=True)
    parser.add_argument("--target-pdf-member", required=True, type=int)
    arguments = parser.parse_args()
    output = Path(arguments.output)
    output.mkdir(parents=True, exist_ok=True)
    reweighted = load_diagnostic_sample(arguments.reweighted)
    direct_a = load_diagnostic_sample(arguments.direct_a)
    direct_b = load_diagnostic_sample(arguments.direct_b)
    result = apply_ess_gate(
        evaluate_shape_closure(reweighted, direct_a, direct_b), arguments.ess_fraction
    )
    result["python_version"] = platform.python_version()
    with (output / "closure_metrics.json").open("w", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    decision = single_case_decision(
        result,
        physics_level=arguments.physics_level,
        target_role=arguments.target_role,
        target_pdf_set=arguments.target_pdf_set,
        target_pdf_member=arguments.target_pdf_member,
    )
    with (output / "decision.json").open("w", encoding="utf-8") as stream:
        json.dump(decision, stream, indent=2, sort_keys=True)
        stream.write("\n")
    write_closure_plots(output / "plots", reweighted, direct_a, direct_b)


if __name__ == "__main__":
    main()
