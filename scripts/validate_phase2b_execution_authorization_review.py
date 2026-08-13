#!/usr/bin/env python3
"""Validate the Phase 2B execution-authorization review without physics execution."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_execution_authorization_review.json"
SCHEMA = "partonsbi.phase2b.execution-authorization-review.v1"
AR1 = "AR1_AUTHORIZE_PHASE2B_BOUNDED_NUMERICAL_VALIDATION"
AR2 = "AR2_PREAUTH_PLAN_REVISION_REQUIRED"
AR3 = "AR3_PHASE2B_AUTHORIZATION_BLOCKED"

EXPECTED_PREDECESSORS = {
    "phase2b_preauthorization_plan": (
        "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan.json",
        "7eb8834eb8435532a85bd7d49b173b03e57a268f69f9676e0effbd877903672b",
    ),
    "fonll_a_amendment": (
        "docs/reduced_nc_dis/contracts/phase2_fonll_a_contract_amendment.json",
        "10cf19fedcdfe1b94e18ff89d1ae09514a31b8e0f6b055beeb729d61b6c32da8",
    ),
    "phase2a_contract_review": (
        "docs/reduced_nc_dis/contracts/phase2a_contract_review.json",
        "4ce2b5b8e910edda6f2183fe7a7e24ec1f0d5e99bd603b708f587c178d1d237b",
    ),
}

EXPECTED_PRE_AUTH = {
    "heavy_quark_mass_convention_and_values",
    "shared_alpha_s_identity",
    "theta_anchors",
    "physics_validity_domain",
    "coordinate_and_jacobian_convention",
    "validation_grids",
    "tolerances_with_justification",
    "convergence_rules",
    "independent_reference_hierarchy",
    "resource_bounds",
    "positivity_no_clipping_policy",
    "normalization_closure_strategy",
    "failure_precedence",
}

EXPECTED_POST_AUTH = {
    "APFEL_FONLL_A_EVALUATIONS",
    "POSITIVITY_SCAN",
    "NORMALIZATION_INTEGRATION",
    "CONVERGENCE_STUDY",
    "CROSS_IMPLEMENTATION_COMPARISON",
    "SELECTED_EVENT_NORMALIZATION_EVALUATION",
}

EXPECTED_CRITERIA = {
    "heavy_mass_threshold_alpha_s_identity",
    "physics_domain",
    "theta_anchors",
    "grid_and_refinement",
    "tolerances",
    "roundoff_and_negative_rate_policy",
    "independent_reference_coverage",
    "resource_bounds",
    "failure_precedence",
    "paper_claim_boundary",
}

TOLERANCE_IDS = {
    "TOL_FONLL_PUBLISHED_COMPONENT",
    "TOL_MASSLESS_NC_REFERENCE",
    "TOL_INTEGRATION_AND_GRID_BUDGET",
    "TOL_NORMALIZED_LAW",
    "TOL_ALPHA_S_IDENTITY",
    "TOL_JACOBIAN",
    "TOL_NEGATIVE_ROUNDOFF_ENVELOPE",
}

COVERAGE_COMPONENTS = {
    "complete_theta_dependent_nc_rate",
    "electroweak_assembly",
    "massless_coefficient_contribution",
    "massive_contribution",
    "fonll_matching_difference_term",
    "accepted_deformed_pdfs_and_external_apfel_bridge",
    "shared_alpha_s",
    "coordinate_and_jacobian",
    "numerical_integration_and_normalization",
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

BLOCKING_COVERAGE = {"NOT_INDEPENDENT", "UNVALIDATED"}
ALLOWED_COVERAGE = {
    "FULLY_INDEPENDENT",
    "PUBLISHED_BENCHMARK",
    "PARTIALLY_INDEPENDENT",
    "NOT_INDEPENDENT",
    "UNVALIDATED",
}
ALLOWED_TOLERANCE_CLASSES = {
    "AUTHORIZED_TOLERANCE",
    "QUALIFIED_TOLERANCE",
    "UNJUSTIFIED_TOLERANCE",
}
ALLOWED_CRITERION_RESULTS = {"PASS", "BLOCKED_REVISION", "BLOCKED_SUBSTANTIVE"}


class ValidationError(ValueError):
    """Raised when the authorization review violates its serialized contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def derive_decision(record: dict[str, Any]) -> str:
    criteria = record.get("authorization_criteria", {})
    values = set(criteria.values()) if set(criteria) == EXPECTED_CRITERIA else set()
    if "BLOCKED_SUBSTANTIVE" in values:
        return AR3
    if "BLOCKED_REVISION" in values:
        return AR2
    return AR1 if values == {"PASS"} else AR2


def validate(record: dict[str, Any], *, root: Path = ROOT, check_docs: bool = True) -> None:
    require(record.get("schema_version") == SCHEMA, "Wrong authorization-review schema")
    require(record.get("record_type") == "PHASE2B_EXECUTION_AUTHORIZATION_REVIEW", "Wrong record type")
    require(record.get("starting_main_sha") == "ae8cc6837a1692353c08aa08de2d0cf3a9ca8f58", "Starting main changed")

    predecessors = record.get("predecessors", {})
    require(set(predecessors) == set(EXPECTED_PREDECESSORS), "Wrong predecessor set")
    for identity, (relative_path, expected_hash) in EXPECTED_PREDECESSORS.items():
        item = predecessors[identity]
        require(item.get("path") == relative_path, f"Wrong predecessor path: {identity}")
        require(item.get("sha256") == expected_hash, f"Wrong predecessor SHA: {identity}")
        require(file_sha256(root / relative_path) == expected_hash, f"Predecessor bytes changed: {identity}")
    require(
        predecessors["phase2b_preauthorization_plan"].get("schema")
        == "partonsbi.phase2b.preauthorization-validation-plan.v1",
        "Wrong preauthorization-plan schema binding",
    )
    require(
        predecessors["phase2b_preauthorization_plan"].get("accepted_outcome")
        == "P1_PREAUTH_PLAN_COMPLETE_READY_FOR_SEPARATE_AUTHORIZATION_REVIEW",
        "Historical P1 outcome changed",
    )

    historical = record.get("historical_state", {})
    require(historical.get("phase2a_status") == "COMPLETE", "Historical Phase 2A status changed")
    require(historical.get("phase2a_scientific_decision") == "INCONCLUSIVE", "Historical Phase 2A changed to PASS")
    require(historical.get("phase2a_changed") is False, "Historical Phase 2A rewritten")
    require(historical.get("adr_013_status") == "Proposed", "ADR-013 state changed")
    require(historical.get("fonll_a_selection_changed") is False, "FONLL-A history rewritten")
    require(historical.get("preauthorization_p1_changed") is False, "P1 history rewritten")

    provenance = record.get("provenance_audit", {})
    require(provenance.get("new_source_selection_performed") is False, "Authorization review selected new physics sources")
    require(provenance.get("accepted_source_bytes_reinspected") is True, "Accepted source bytes were not reinspected")
    require(provenance.get("source_bytes_committed") is False, "External source bytes claimed committed")
    source_map = {
        item.get("source_id"): item for item in provenance.get("source_observations", [])
    }
    require(
        set(source_map) == {"CT18NLO_DATAVERSION_1", "APFEL_SOURCE_3_1_1"},
        "Wrong provenance-observation set",
    )
    require(
        source_map["CT18NLO_DATAVERSION_1"].get("sha256")
        == "c9127231e77e97cbec79cb5839203ab00f8db77237a061b61f9420f2b7b9c213",
        "CT18 source identity changed",
    )
    require(
        source_map["APFEL_SOURCE_3_1_1"].get("sha256")
        == "e5c4b3d955f8d33e8e8ff2d9d1687da57f2ee99245abc579f9d32caa616f0f53",
        "APFEL source identity changed",
    )
    for source in source_map.values():
        require(nonempty(source.get("locator")), f"Missing source locator: {source.get('source_id')}")
        require(nonempty(source.get("observation")), f"Missing source observation: {source.get('source_id')}")

    rederived = record.get("rederived_plan", {})
    require(set(rederived.get("pre_auth_items", [])) == EXPECTED_PRE_AUTH, "PRE_AUTH item set changed")
    require(rederived.get("pre_auth_plan_completeness") == "COMPLETE_AS_A_REVIEWABLE_PLAN", "P1 completeness not rederived")
    require(set(rederived.get("post_auth_items", [])) == EXPECTED_POST_AUTH, "POST_AUTH item set changed")
    require(rederived.get("post_auth_execution_status") == "NOT_EXECUTED", "POST_AUTH result marked executed")
    require(rederived.get("starting_execution_authorization") is False, "Starting authorization changed")

    accepted = record.get("accepted_contract", {})
    require(accepted.get("scheme") == "FONLL-A", "FONLL-A scheme changed")
    require(accepted.get("perturbative_order") == "NLO", "Perturbative order changed")
    require(
        accepted.get("software")
        == {"name": "APFEL", "version": "3.1.1", "commit": "72bf6ec7c72c923dd2115f2a98c6f593f9c91d2a"},
        "APFEL identity changed",
    )
    require(accepted.get("pdf_family") == "ct18nlo_two_parameter_boundary_v2", "Accepted PDF identity changed")
    require(accepted.get("pdf_baseline") == "ct18nlo_member0_sumrule_projected_boundary_v2", "Accepted PDF baseline changed")
    require(accepted.get("strict_support") is True, "Strict PDF support weakened")

    heavy = record.get("heavy_flavor_and_coupling_audit", {})
    mass = heavy.get("mass_findings", {})
    require(heavy.get("mass_result") == "COHERENT", "Heavy-mass audit changed")
    require(
        (mass.get("convention"), mass.get("charm_mass_gev"), mass.get("bottom_mass_gev"), mass.get("nf_max"))
        == ("POLE", 1.3, 4.75, 5),
        "Heavy mass/threshold identity changed",
    )
    require(mass.get("charm_threshold") == "mu_c=m_c_pole", "Charm threshold changed")
    require(mass.get("bottom_threshold") == "mu_b=m_b_pole", "Bottom threshold changed")
    alpha = heavy.get("alpha_s_findings", {})
    require(alpha.get("repository_identity") == "ct18nlo_as_mz_0p118_nlo_vfns_mc1p3_mb4p75_nfmax5_v1", "alpha_s identity changed")
    require((alpha.get("reference_value"), alpha.get("reference_scale_gev"), alpha.get("order")) == (0.118, 91.187, "NLO_TWO_LOOP"), "alpha_s tuple changed")
    require(alpha.get("ct18_authoritative_type") == "IPOL_TABLE_FROM_HOPPET_RUNNING_SOLUTION", "CT18 alpha_s provenance hidden")
    if record.get("decision") == AR1:
        require(heavy.get("overall_result") in {"COHERENT", "QUALIFIED_BUT_AUTHORIZABLE"}, "AR1 with unresolved heavy/coupling identity")
    else:
        require(nonempty(heavy.get("authorization_consequence")), "Missing heavy/coupling consequence")

    domain = record.get("domain_audit", {})
    require(domain.get("result") == "PASS", "Physics-domain audit did not pass")
    require(domain.get("coordinates") == ["x_Bj", "Q2"], "Domain coordinates changed")
    require(domain.get("differential_quantity") == "d2sigma_dx_Bj_dQ2", "Differential quantity changed")
    require(domain.get("beam", {}).get("s_massless_gev2") == 101200.0, "Beam invariant changed")
    require(domain.get("mask") == "PREDECLARED_RESULT_INDEPENDENT_INTERSECTION_MASK", "Domain mask is not predeclared")
    require(domain.get("normalization_domain_matches") is True, "Normalization domain changed")
    require(domain.get("strict_pdf_support") is True, "Domain no longer respects strict support")
    require(domain.get("post_hoc_removal_allowed") is False, "Post-hoc domain removal allowed")

    anchor = record.get("anchor_audit", {})
    require(anchor.get("anchor_count") == 9, "Required anchor removed")
    require(anchor.get("theta_bounds") == {"delta_v": [-0.2, 0.2], "lambda_sea": [-0.25, 0.25]}, "Theta domain changed")
    require(anchor.get("required_roles") == ["center", "four_axis_endpoints", "four_corners"], "Anchor roles changed")
    require(anchor.get("adaptive_anchors_allowed") is False, "Adaptive anchors allowed")
    require("does not prove" in anchor.get("claim_limit", ""), "Nine-anchor claim overstated")

    grid = record.get("grid_audit", {})
    require(grid.get("point_levels") == [17, 33, 65], "Point-grid levels changed")
    require(grid.get("normalization_primary_orders") == [16, 32, 64], "Primary quadrature orders changed")
    require(grid.get("normalization_independent_orders") == [17, 33, 65], "Independent quadrature orders changed")
    require(grid.get("adaptive_extension_allowed") is False, "Adaptive grid extension allowed")
    if record.get("decision") == AR1:
        require(grid.get("result") == "PASS", "AR1 without bound quadrature independence")

    resources = record.get("resource_audit", {})
    point = 9 * sum(n * n + 13 * n for n in (17, 33, 65))
    normalization = 9 * (sum(n * n for n in (16, 32, 64)) + sum(n * n for n in (17, 33, 65)))
    references = 64 + 30 + 9 * 24
    require(point == 63882, "Internal point-count derivation changed")
    require(normalization == 98811, "Internal normalization-count derivation changed")
    require(references == 310, "Internal reference-count derivation changed")
    require(point + normalization + references == 163003, "Internal total-count derivation changed")
    require(resources.get("point_evaluations") == point, "Resource-count mismatch: point evaluations")
    require(resources.get("normalization_evaluations") == normalization, "Resource-count mismatch: normalization evaluations")
    require(resources.get("reference_evaluations") == references, "Resource-count mismatch: reference evaluations")
    require(resources.get("total_evaluations") == point + normalization + references, "Resource-count mismatch: total evaluations")
    require(resources.get("maximum_output_bytes") == 64 * 1024 * 1024, "Output bound changed")
    require(resources.get("unbounded_adaptive_loop") is False, "Unbounded adaptive loop allowed")
    require(resources.get("continue_until_pass_allowed") is False, "Continue-until-pass allowed")
    require(resources.get("exhaustion_result") == "INCONCLUSIVE", "Resource exhaustion can pass")

    tolerances = record.get("tolerance_audit", [])
    tolerance_map = {item.get("tolerance_id"): item for item in tolerances}
    require(len(tolerances) == len(tolerance_map), "Duplicate tolerance audit")
    require(set(tolerance_map) == TOLERANCE_IDS, "Tolerance audit set changed")
    for tolerance in tolerances:
        require(tolerance.get("classification") in ALLOWED_TOLERANCE_CLASSES, f"Wrong tolerance class: {tolerance.get('tolerance_id')}")
        require(nonempty(tolerance.get("basis")), f"Missing tolerance basis: {tolerance.get('tolerance_id')}")
        require(nonempty(tolerance.get("authorization_finding")), f"Missing tolerance finding: {tolerance.get('tolerance_id')}")
        threshold = tolerance.get("threshold")
        require((isinstance(threshold, (int, float)) and not isinstance(threshold, bool) and math.isfinite(threshold) and threshold > 0) or nonempty(threshold), f"Invalid tolerance threshold: {tolerance.get('tolerance_id')}")
    if record.get("decision") == AR1:
        require(all(item["classification"] != "UNJUSTIFIED_TOLERANCE" for item in tolerances), "AR1 with an unjustified tolerance")

    roundoff = record.get("roundoff_and_negative_rate_audit", {})
    for key in ("clipping_allowed", "absolute_value_repair_allowed", "replace_negative_with_zero_allowed"):
        require(roundoff.get(key) is False, f"Forbidden negative-rate repair enabled: {key}")
    require(roundoff.get("original_signed_rate_retained") is True, "Original signed rate not retained")
    require(roundoff.get("high_precision_negative_result") == "FAIL", "High-precision negative does not fail")
    require(roundoff.get("high_precision_unavailable_result") == "INCONCLUSIVE", "Unavailable high precision can pass")
    if record.get("decision") == AR1:
        require(roundoff.get("operational_binary128_complete_rate_recomputation_bound") is True, "AR1 without operational binary128 complete-rate adjudication")

    coverage = record.get("independent_reference_coverage", [])
    coverage_map = {item.get("component"): item for item in coverage}
    require(len(coverage) == len(coverage_map), "Duplicate independent-reference component")
    require(set(coverage_map) == COVERAGE_COMPONENTS, "Independent-reference coverage graph incomplete")
    for component in coverage:
        require(component.get("classification") in ALLOWED_COVERAGE, f"Wrong coverage class: {component.get('component')}")
        require(nonempty(component.get("oracle")), f"Missing oracle: {component.get('component')}")
        require(nonempty(component.get("gap")), f"Missing coverage gap: {component.get('component')}")
    independent = record.get("independent_reference_conclusion", {})
    require("component decomposition" in independent.get("repository_gate_semantics", ""), "Repository independence semantics not derived")
    if record.get("decision") == AR1:
        require(not any(item["classification"] in BLOCKING_COVERAGE for item in coverage), "AR1 with an unvalidated load-bearing component")
        require(independent.get("current_hierarchy_sufficient") is True, "AR1 with insufficient reference hierarchy")

    failure = record.get("failure_precedence_audit", {})
    require(failure.get("result") == "PASS", "Failure precedence did not pass")
    for key in (
        "one_bad_anchor_can_be_averaged_away",
        "clipping_can_convert_fail_to_pass",
        "resource_exhaustion_can_convert_fail_to_pass",
        "reference_disagreement_can_be_waived",
        "inconclusive_counts_as_pass",
    ):
        require(failure.get(key) is False, f"Failure semantics weakened: {key}")
    require(record.get("paper_claim_audit", {}).get("result") == "PASS", "Paper-claim audit did not pass")

    criteria = record.get("authorization_criteria", {})
    require(set(criteria) == EXPECTED_CRITERIA, "Authorization criteria set changed")
    require(set(criteria.values()) <= ALLOWED_CRITERION_RESULTS, "Invalid authorization criterion result")
    heavy_result = heavy.get("overall_result")
    expected_heavy_criterion = {
        "COHERENT": "PASS",
        "QUALIFIED_BUT_AUTHORIZABLE": "PASS",
        "UNRESOLVED": "BLOCKED_REVISION",
        "INCONSISTENT": "BLOCKED_SUBSTANTIVE",
    }.get(heavy_result)
    expected_criteria = {
        "heavy_mass_threshold_alpha_s_identity": expected_heavy_criterion,
        "physics_domain": "PASS" if domain.get("result") == "PASS" else "BLOCKED_SUBSTANTIVE",
        "theta_anchors": "PASS" if anchor.get("result") == "PASS_FOR_NINE_ANCHOR_CLAIM_ONLY" else "BLOCKED_REVISION",
        "grid_and_refinement": "PASS" if grid.get("result") == "PASS" else "BLOCKED_REVISION",
        "tolerances": (
            "BLOCKED_REVISION"
            if any(item["classification"] == "UNJUSTIFIED_TOLERANCE" for item in tolerances)
            else "PASS"
        ),
        "roundoff_and_negative_rate_policy": (
            "PASS"
            if roundoff.get("result") == "PASS"
            and roundoff.get("operational_binary128_complete_rate_recomputation_bound") is True
            else "BLOCKED_REVISION"
        ),
        "independent_reference_coverage": (
            "PASS"
            if independent.get("current_hierarchy_sufficient") is True
            and not any(item["classification"] in BLOCKING_COVERAGE for item in coverage)
            else "BLOCKED_REVISION"
        ),
        "resource_bounds": "PASS" if resources.get("result") == "PASS" else "BLOCKED_REVISION",
        "failure_precedence": "PASS" if failure.get("result") == "PASS" else "BLOCKED_SUBSTANTIVE",
        "paper_claim_boundary": (
            "PASS" if record.get("paper_claim_audit", {}).get("result") == "PASS" else "BLOCKED_SUBSTANTIVE"
        ),
    }
    require(criteria == expected_criteria, "Authorization criteria are not derived from audit results")
    decision = derive_decision(record)
    require(record.get("decision") == decision, "Authorization decision is not derived")
    blockers = record.get("blocking_revisions", [])
    if decision == AR1:
        require(not blockers, "AR1 retains blocking revisions")
    else:
        require(bool(blockers) and all(nonempty(item) for item in blockers), "Non-AR1 decision lacks exact blockers")
    require(nonempty(record.get("decision_derivation")), "Decision derivation missing")

    authorization = record.get("authorization", {})
    require(set(authorization) == AUTHORIZATION_KEYS, "Authorization flag set changed")
    downstream = AUTHORIZATION_KEYS - {
        "PHASE2B_BOUNDED_NUMERICAL_VALIDATION_AUTHORIZED",
        "PHASE2B_EXECUTION_AUTHORIZED",
    }
    require(all(authorization[key] is False for key in downstream), "Downstream authorization is true")
    expected_phase2b = decision == AR1
    require(authorization["PHASE2B_BOUNDED_NUMERICAL_VALIDATION_AUTHORIZED"] is expected_phase2b, "Bounded Phase 2B authorization contradicts decision")
    require(authorization["PHASE2B_EXECUTION_AUTHORIZED"] is expected_phase2b, "Phase 2B execution authorization contradicts decision")

    execution = record.get("execution_boundary", {})
    require(execution.get("phase2b_execution_status") == "NOT_EXECUTED", "Phase 2B execution occurred")
    for key in (
        "apfel_or_apfelxx_numerical_physics_executed",
        "positivity_or_normalization_calculation_executed",
        "convergence_or_independent_closure_executed",
        "events_data_detector_or_neural_work",
    ):
        require(execution.get(key) is False, f"Forbidden execution recorded: {key}")
    require(execution.get("later_execution_task_permitted") is expected_phase2b, "Later execution permission contradicts decision")

    github = record.get("github_target_state", {})
    require(github.get("issue") == 55 and github.get("state") == "OPEN", "Issue #55 state changed")
    expected_status = "In Progress" if decision == AR1 else "Backlog"
    expected_auth = "Authorized" if decision == AR1 else "Not Authorized"
    require(github.get("status") == expected_status, "Issue #55 target status contradicts decision")
    require(github.get("gate_decision") == "Not Evaluated", "Issue #55 gate decision changed")
    require(github.get("authorization") == expected_auth, "Issue #55 authorization contradicts decision")
    require(github.get("phase") == "Phase2B", "Issue #55 phase changed")
    require(github.get("work_type") == "Physics", "Issue #55 work type changed")
    require(github.get("priority") == "P0", "Issue #55 priority changed")
    require(github.get("research_line") == "Reduced NC DIS", "Issue #55 research line changed")
    require(nonempty(record.get("next_action")), "Next action missing")

    if check_docs:
        markers = {
            "docs/reduced_nc_dis/PHASE2B_EXECUTION_AUTHORIZATION_REVIEW.md": [
                decision,
                "PHASE2B_EXECUTION_AUTHORIZED = false" if decision != AR1 else "PHASE2B_EXECUTION_AUTHORIZED = true",
                "PHASE2B_EXECUTION_STATUS = NOT_EXECUTED",
            ],
            "docs/CURRENT_PHASE.md": [decision, "Phase 2B remains Not Authorized" if decision != AR1 else "Phase 2B bounded numerical validation is Authorized"],
            "docs/reduced_nc_dis/README.md": ["execution authorization review", decision],
            "docs/reduced_nc_dis/ROADMAP.md": [decision, "Not Authorized" if decision != AR1 else "Authorized"],
            "docs/adr/ADR-013-reduced-nc-dis-observation-law-contract.md": [decision, "Historical Phase 2A remains `INCONCLUSIVE`"],
        }
        for relative_path, required_markers in markers.items():
            text = (root / relative_path).read_text(encoding="utf-8")
            for marker in required_markers:
                require(marker in text, f"Documentation marker missing from {relative_path}: {marker}")


def main() -> None:
    try:
        record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        validate(record)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise SystemExit(f"INVALID phase2b.execution_authorization_review: {error}") from error
    print("VALID phase2b.execution_authorization_review")


if __name__ == "__main__":
    main()
