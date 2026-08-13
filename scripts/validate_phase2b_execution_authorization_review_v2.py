#!/usr/bin/env python3
"""Validate the Phase 2B v2 authorization review without numerical physics."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_execution_authorization_review_v2.json"
V2_PLAN = ROOT / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v2.json"
QUADRATURE = ROOT / "analysis/validation/phase2b_quadrature_oracles.py"
REQUIREMENTS = ROOT / "analysis/requirements.txt"

SCHEMA = "partonsbi.phase2b.execution-authorization-review.v2"
AR1 = "AR1_AUTHORIZE_PHASE2B_BOUNDED_NUMERICAL_VALIDATION"
AR2 = "AR2_PREAUTH_V2_REVISION_REQUIRED"
AR3 = "AR3_PHASE2B_AUTHORIZATION_BLOCKED"

EXPECTED_PREDECESSORS = {
    "fonll_a_amendment": (
        "docs/reduced_nc_dis/contracts/phase2_fonll_a_contract_amendment.json",
        "10cf19fedcdfe1b94e18ff89d1ae09514a31b8e0f6b055beeb729d61b6c32da8",
    ),
    "preauthorization_v1": (
        "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan.json",
        "7eb8834eb8435532a85bd7d49b173b03e57a268f69f9676e0effbd877903672b",
    ),
    "authorization_review_v1": (
        "docs/reduced_nc_dis/contracts/phase2b_execution_authorization_review.json",
        "03d8119efb819b7a8b51161d5f2ce58fe59dd385b63f2dbfd6203692dac1f9e2",
    ),
    "preauthorization_v2": (
        "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v2.json",
        "a79e87538fae4d3f20793756b321af4d7521c1277ee08580e1b773a7452a9cd2",
    ),
}

EXPECTED_CRITERIA = {
    "rv1_derivable": "PASS",
    "budget_parent": "BLOCKED_REVISION",
    "equal_split": "BLOCKED_REVISION",
    "alpha_s_as2": "BLOCKED_REVISION",
    "pdf_apfel_bridge": "BLOCKED_REVISION",
    "quadrature_independence": "PASS_WITH_QUALIFICATION",
    "reference_graph": "BLOCKED_REVISION",
    "nr2": "BLOCKED_REVISION",
    "normalized_law": "BLOCKED_REVISION",
    "jacobian": "PASS",
    "resource_bound": "BLOCKED_REVISION",
    "dependency_reproducibility": "BLOCKED_REVISION",
    "failure_policy": "PASS",
}

EXPECTED_GRAPH = {
    "complete_nc_rate": "PARTIAL",
    "electroweak_assembly": "FULLY_INDEPENDENT",
    "massless_coefficients": "PUBLISHED_INDEPENDENT_BENCHMARK",
    "massive_contribution": "INDEPENDENT_POSTAUTH_TEST_DEFINED",
    "fonll_matching_difference_term": "INDEPENDENT_POSTAUTH_TEST_DEFINED",
    "pdf_provider": "INDEPENDENT_POSTAUTH_TEST_DEFINED",
    "pdf_to_apfel_bridge": "INDEPENDENT_POSTAUTH_TEST_DEFINED",
    "alpha_s": "INDEPENDENT_POSTAUTH_TEST_DEFINED",
    "coordinate_jacobian": "FULLY_INDEPENDENT",
    "quadrature_a": "FULLY_INDEPENDENT",
    "quadrature_b": "FULLY_INDEPENDENT",
    "normalization_assembly": "INDEPENDENT_POSTAUTH_TEST_DEFINED",
}

AUTHORIZATION_KEYS = {
    "PHASE2B_BOUNDED_NUMERICAL_VALIDATION_AUTHORIZED",
    "PHASE2B_EXECUTION_AUTHORIZED",
    "PHASE2C_AUTHORIZED",
    "EVENT_GENERATION_AUTHORIZED",
    "DATASET_AUTHORIZED",
    "DETECTOR_IMPLEMENTATION_AUTHORIZED",
    "TRAINING_AUTHORIZED",
    "NEURAL_TRAINING_AUTHORIZED",
    "D2_AUTHORIZED",
    "FULL_GENERATOR_EXECUTION_AUTHORIZED",
}


class ValidationError(ValueError):
    """Raised when the successor authorization review is inconsistent."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def derive_decision(criteria: dict[str, str]) -> str:
    values = set(criteria.values())
    if "BLOCKED_SUBSTANTIVE" in values:
        return AR3
    if "BLOCKED_REVISION" in values:
        return AR2
    return AR1 if values <= {"PASS", "PASS_WITH_QUALIFICATION"} else AR2


def _validate_predecessors(record: dict[str, Any], root: Path) -> dict[str, Any]:
    predecessors = record.get("predecessors", {})
    require(set(predecessors) == set(EXPECTED_PREDECESSORS), "Wrong predecessor set")
    for name, (relative, expected_hash) in EXPECTED_PREDECESSORS.items():
        item = predecessors[name]
        require(item.get("path") == relative, f"Wrong predecessor path: {name}")
        require(item.get("sha256") == expected_hash, f"Wrong predecessor SHA: {name}")
        require(sha256(root / relative) == expected_hash, f"Historical predecessor bytes changed: {name}")

    v2 = json.loads((root / EXPECTED_PREDECESSORS["preauthorization_v2"][0]).read_text(encoding="utf-8"))
    require(v2.get("schema_version") == "partonsbi.phase2b.preauthorization-validation-plan.v2", "V2 schema changed")
    require(v2.get("outcome") == "RV1_PREAUTH_V2_COMPLETE_READY_FOR_NEW_AUTHORIZATION_REVIEW", "RV1 outcome changed")
    require(v2.get("plan_completeness") == "COMPLETE", "V2 plan completeness changed")
    require(v2.get("alpha_s_architecture", {}).get("choice") == "AS2_DUAL_PROVIDER_PREDECLARED_EQUIVALENCE_TEST", "V2 AS2 architecture changed")
    require(v2.get("execution_state", {}).get("phase2b") == "NOT_EXECUTED", "V2 execution state changed")
    require(not any(v2.get("authorization", {}).values()), "V2 authorization became true")
    return v2


def _validate_quadrature_source(root: Path) -> None:
    module = ast.parse((root / "analysis/validation/phase2b_quadrature_oracles.py").read_text(encoding="utf-8"))
    functions = {node.name: node for node in module.body if isinstance(node, ast.FunctionDef)}
    required = {
        "scipy_gauss_legendre_rule",
        "scipy_gauss_legendre_integrate",
        "clenshaw_curtis_rule",
        "clenshaw_curtis_integrate",
    }
    require(required <= set(functions), "Quadrature implementation entrypoint missing")
    cc_identifiers = {
        value
        for name in ("clenshaw_curtis_rule", "clenshaw_curtis_integrate")
        for child in ast.walk(functions[name])
        for value in (
            child.id.lower() if isinstance(child, ast.Name) else None,
            child.attr.lower() if isinstance(child, ast.Attribute) else None,
        )
        if value is not None
    }
    require(not cc_identifiers.intersection({"scipy", "numpy", "roots_legendre", "dot"}), "Quadrature paths share implementation core")


def validate(record: dict[str, Any], *, root: Path = ROOT, check_docs: bool = True) -> None:
    require(record.get("schema_version") == SCHEMA, "Wrong successor-review schema")
    require(record.get("record_type") == "PHASE2B_EXECUTION_AUTHORIZATION_REVIEW_V2", "Wrong record type")
    require(record.get("starting_main_sha") == "d2d2d4d95a6a405200ac9aba78d50ab19e67ead6", "Starting main changed")
    v2 = _validate_predecessors(record, root)

    preflight = record.get("integrity_preflight", {})
    require(preflight.get("classification") == "TEMP_A_NOT_TRACKED", "Wrong temp-file classification")
    require(preflight.get("inspected_path") == "C:/tmp/partonsbi-phase2b-preauth-v2-pr-body.md", "Wrong temp-file path")
    require(preflight.get("tracked_path_result") == [], "Named temp file recorded as tracked")
    require(preflight.get("cleanup_performed") is False, "Unexpected cleanup recorded")
    require(preflight.get("cleanup_main_sha") == record["starting_main_sha"], "Cleanup/main lineage mismatch")

    historical = record.get("historical_state", {})
    require(historical.get("phase2a_status") == "COMPLETE", "Historical Phase 2A status changed")
    require(historical.get("phase2a_scientific_decision") == "INCONCLUSIVE", "Historical Phase 2A changed to PASS")
    require(historical.get("adr_013_status") == "Proposed", "ADR-013 status changed")
    require(historical.get("accepted_pdf_family") == "ct18nlo_two_parameter_boundary_v2", "Accepted PDF family changed")
    for key in ("phase2a_changed", "fonll_a_amendment_changed", "preauthorization_v1_changed", "authorization_review_v1_changed", "preauthorization_v2_changed"):
        require(historical.get(key) is False, f"Historical record changed: {key}")

    rv1 = record.get("rv1_derivation_audit", {})
    require(rv1.get("classification") == "RV1_INDEPENDENTLY_DERIVED_AS_PLAN_COMPLETENESS_ONLY", "RV1 not independently bounded")
    require(rv1.get("result") == "PASS_WITH_AUTHORIZATION_BLOCKERS", "RV1 derivation result changed")

    budget = record.get("budget_parent_audit", {})
    require(budget.get("classification") == "BUDGET_PARENT_NOT_JUSTIFIED", "Unjustified T_external accepted")
    require(budget.get("value") == 0.001, "T_external value changed")
    require(budget.get("error_kind") == "OBSERVED_RELATIVE_COMPONENT_BENCHMARK_DISCREPANCY", "0.001 source meaning changed")
    require("observed" in budget.get("source_meaning", "").lower(), "0.001 not identified as observed discrepancy")
    require(budget.get("formal_guarantee") is False, "0.001 upgraded to formal guarantee")
    require(budget.get("project_parent_allowance_derived") is False, "T_external treated as derived parent")
    require(budget.get("commensurable_additive_parent_established") is False, "Mixed errors treated as commensurable")
    require(budget.get("near_zero_relative_decomposition_valid") is False, "Near-zero relative decomposition accepted")
    require(budget.get("authorization_consequence") == "AR1_FORBIDDEN", "Budget blocker does not forbid AR1")

    split = record.get("equal_split_audit", {})
    require(split.get("classification") == "ERROR_BUDGET_STRUCTURE_INVALID", "Invalid equal split accepted")
    require(split.get("serialized_share_count") * split.get("serialized_share") == split.get("arithmetic_sum") == 0.001, "Equal-share arithmetic changed")
    require(split.get("absolute_relative_units_compatible") is False, "Mixed budget units accepted")
    require(split.get("double_counting_excluded") is False, "Unproved no-double-counting claim")
    require(split.get("normalization_amplification_in_allocation") is False, "Normalization amplification falsely allocated")

    alpha = record.get("alpha_s_audit", {})
    require(alpha.get("classification") == "AS2_REVISION_REQUIRED", "AS2 unresolved audit accepted")
    require(alpha.get("required_identity") == "NUMERICAL_EQUIVALENCE_WITHIN_BOUNDED_TOLERANCE", "Wrong alpha_s identity requirement")
    require(alpha.get("identical_alpha_s_object_required") is False, "Impossible identical alpha_s object required")
    require(alpha.get("threshold_side_probes_present") is True, "Missing alpha threshold probe")
    require(alpha.get("actual_result") == "NOT_EXECUTED", "Alpha equivalence marked executed")
    require("282-point" in alpha.get("finding", ""), "AS2 sampled-domain limitation missing")

    bridge = record.get("bridge_audit", {})
    require(bridge.get("classification") == "BRIDGE_PLAN_REVISION_REQUIRED", "Underived bridge plan accepted")
    require(bridge.get("sentinel_count") == 14, "Bridge sentinel count changed")
    require(bridge.get("theta_anchor_count") == 9 and bridge.get("grid_levels") == [17, 33, 65], "Bridge grid changed")
    require(bridge.get("tolerance") == "16*2^-53 relative with exact +0.0 zeros", "Bridge tolerance not derived")
    require(bridge.get("actual_result") == "NOT_EXECUTED", "Bridge marked executed")

    quadrature = record.get("quadrature_audit", {})
    require(quadrature.get("classification") == "QUADRATURE_INDEPENDENCE_QUALIFIED", "Wrong quadrature independence classification")
    for key in ("shared_node_generation", "shared_weight_generation", "shared_polynomial_recurrence", "shared_accumulation_core"):
        require(quadrature.get(key) is False, f"Quadrature paths share implementation core: {key}")
    require(set(quadrature.get("generic_tests", [])) == {"symmetry", "positive weights", "weight sum two", "monomials degree zero through twelve", "exp"}, "Generic quadrature tests changed")
    _validate_quadrature_source(root)

    massive = record.get("massivedis_audit", {})
    require(massive.get("classification") == "MASSIVE_FONLL_COMPONENT_ORACLE_QUALIFIED", "MassiveDIS classification changed")
    require(massive.get("runnable_later") is True and massive.get("source_restorable") is True, "MassiveDIS future oracle unavailable")
    require(massive.get("full_rate_oracle") is False, "MassiveDIS upgraded to full-rate oracle without evidence")

    graph = record.get("reference_graph", [])
    graph_map = {item.get("node"): item for item in graph}
    require(len(graph) == len(graph_map) == len(EXPECTED_GRAPH), "Reference graph node set changed")
    require({name: item.get("classification") for name, item in graph_map.items()} == EXPECTED_GRAPH, "Reference graph classification changed")
    require(all(item.get("load_bearing") is True and nonempty(item.get("authorization_finding")) for item in graph), "Reference graph finding missing")
    require(not any(item.get("classification") == "UNVALIDATED" for item in graph), "UNVALIDATED reference node")
    circularity = record.get("postauth_circularity_audit", {})
    require(circularity.get("classification") == "POSTAUTH_SPECIFICATION_UNDERDEFINED", "Post-auth specification gap hidden")
    require(circularity.get("failure_can_fail_phase2b") is True, "Post-auth failure cannot fail Phase 2B")
    require(circularity.get("posthoc_repair_forbidden") is True, "Post-hoc plan repair allowed")
    require(circularity.get("all_test_specs_fully_fixed") is False, "Underdefined post-auth tests marked fully fixed")

    nr2 = record.get("nr2_audit", {})
    require(nr2.get("classification") == "NR2_REVISION_REQUIRED", "Incomplete NR2 accepted")
    require(nr2.get("formula") == "E_total=E_upstream+gamma_32*S_assembly", "Missing upstream error term")
    require(nr2.get("negative_beyond_envelope") == "FAIL_NEGATIVE_RATE", "Negative rate does not fail")
    require(nr2.get("inside_envelope") == "INCONCLUSIVE_SIGN", "INCONCLUSIVE_SIGN treated as PASS")
    require(nr2.get("inconclusive_any_required_point_blocks_global_pass") is True, "Inconclusive sign can pass globally")
    for key in ("averaging_allowed", "point_removal_allowed", "clipping_allowed"):
        require(nr2.get(key) is False, f"Forbidden NR2 repair enabled: {key}")

    normalized = record.get("normalized_law_audit", {})
    require(normalized.get("classification") == "NORMALIZED_BOUND_FORMALLY_VALID_INPUT_BUDGET_REVISION_REQUIRED", "Normalized-law audit changed")
    require(normalized.get("bound") == "E_r/(Z_hat-E_Z)+abs(r_hat)*E_Z/(Z_hat*(Z_hat-E_Z))", "Normalized-law bound changed")
    require(normalized.get("requires_z_hat_greater_than_e_z") is True, "Z_hat>E_Z precondition missing")
    require(normalized.get("z_hat_le_e_z_result") == "INCONCLUSIVE_OR_FAIL_NEVER_PASS", "Z_hat<=E_Z accepted")
    require(normalized.get("compatible_absolute_units_established") is False, "Relative/absolute unit mismatch hidden")

    jacobian = record.get("jacobian_audit", {})
    require(jacobian.get("classification") == "JACOBIAN_BOUND_AUTHORIZED", "Jacobian classification changed")
    require(jacobian.get("bound") == "8*2^-53 relative", "Bad Jacobian operation-count bound")
    require("one multiplication" in jacobian.get("operation_path", "") and "one reciprocal or division" in jacobian.get("operation_path", ""), "Jacobian operation path missing")

    resources = record.get("resource_audit", {})
    serialized = 63882 + 98811 + 310 + 2 * 282 + 9 * (17 + 33 + 65) + 282 + 282 * (20 + 40 + 80 + 160) * 4
    corrected = 63882 + 98811 + 310 + 2 * 282 + 9 * (17 + 33 + 65) + 282 + 282 * 2 * (20 + 40 + 80 + 160) * 4 + 1
    require(serialized == 503284, "Internal serialized resource arithmetic changed")
    require(corrected == 841685, "Internal corrected resource arithmetic changed")
    require(resources.get("classification") == "RESOURCE_BOUND_REVISION_REQUIRED", "Resource mismatch accepted")
    require(resources.get("serialized_arithmetic_total") == serialized, "Serialized resource mismatch")
    require(resources.get("corrected_conservative_upper_bound") == corrected, "Corrected resource mismatch")
    require(resources.get("finite") is True and resources.get("deterministic") is True, "Resource bound is not finite and deterministic")
    require(resources.get("unbounded_adaptive_extension") is False and resources.get("retry_until_pass") is False, "Unbounded or retry-until-pass execution allowed")
    require(v2.get("resource_bounds", {}).get("maximum_total_declared_evaluations") == serialized, "V2 serialized resource total changed")

    dependencies = record.get("dependency_audit", {})
    requirements = (root / "analysis/requirements.txt").read_text(encoding="utf-8").splitlines()
    require(dependencies.get("classification") == "UNPINNED_LOAD_BEARING_DEPENDENCY", "Unpinned load-bearing dependency accepted")
    require(dependencies.get("python_version_pinned") is False, "Python pin audit changed")
    require(dependencies.get("scipy") == "==1.15.3" and "scipy==1.15.3" in requirements, "SciPy pin changed")
    require(dependencies.get("mpmath") == "==1.3.0" and "mpmath==1.3.0" in requirements, "mpmath pin changed")
    require(dependencies.get("numpy") == ">=1.26.0" and "numpy>=1.26.0" in requirements, "NumPy dependency audit changed")
    require(dependencies.get("numpy_load_bearing") is True, "NumPy load-bearing role hidden")

    failure = record.get("failure_policy_audit", {})
    for key in ("no_clipping", "no_abs_repair", "no_max_zero", "no_support_deletion"):
        require(failure.get(key) is True, f"No-repair policy weakened: {key}")
    require(failure.get("inconclusive_is_pass") is False, "INCONCLUSIVE treated as PASS")
    require(failure.get("one_bad_point_can_be_averaged_away") is False, "Bad point can be averaged away")

    criteria = record.get("authorization_criteria", {})
    require(criteria == EXPECTED_CRITERIA, "Authorization criteria not derived from audits")
    decision = derive_decision(criteria)
    require(record.get("decision") == decision == AR2, "Authorization decision is not derived")
    require(bool(record.get("blocking_revisions")) and all(nonempty(item) for item in record["blocking_revisions"]), "AR2 blocking revisions missing")
    require(nonempty(record.get("decision_derivation")), "Decision rationale missing")

    authorization = record.get("authorization", {})
    require(set(authorization) == AUTHORIZATION_KEYS, "Authorization flag set changed")
    require(not any(authorization.values()), "AR2 cannot authorize execution or downstream work")
    execution = record.get("execution_state", {})
    require(execution.get("phase2b") == "NOT_EXECUTED", "Numerical execution marked complete")
    for key, value in execution.items():
        if key != "phase2b":
            require(value is False, f"Forbidden execution recorded: {key}")

    github = record.get("github_target_state", {})
    require(github == {"issue": 55, "state": "OPEN", "status": "Backlog", "gate_decision": "Not Evaluated", "authorization": "Not Authorized", "phase": "Phase2B", "work_type": "Physics", "priority": "P0", "research_line": "Reduced NC DIS"}, "Issue #55 target state changed")
    require(nonempty(record.get("next_action")), "Next action missing")

    if check_docs:
        markers = {
            "docs/reduced_nc_dis/PHASE2B_EXECUTION_AUTHORIZATION_REVIEW_V2.md": [AR2, "BUDGET_PARENT_NOT_JUSTIFIED", "ERROR_BUDGET_STRUCTURE_INVALID", "841,685", "NOT_EXECUTED"],
            "docs/CURRENT_PHASE.md": [AR2, "Phase 2B remains Not Authorized"],
            "docs/reduced_nc_dis/README.md": ["v2 execution authorization review", AR2],
            "docs/reduced_nc_dis/ROADMAP.md": [AR2, "Not Authorized"],
            "docs/adr/ADR-013-reduced-nc-dis-observation-law-contract.md": [AR2, "Historical Phase 2A remains `INCONCLUSIVE`"],
        }
        for relative, required in markers.items():
            text = (root / relative).read_text(encoding="utf-8")
            for marker in required:
                require(marker in text, f"Documentation marker missing from {relative}: {marker}")


def main() -> None:
    try:
        record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        validate(record)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise SystemExit(f"INVALID phase2b.execution_authorization_review_v2: {error}") from error
    print("VALID phase2b.execution_authorization_review_v2")


if __name__ == "__main__":
    main()
