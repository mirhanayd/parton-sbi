#!/usr/bin/env python3
"""Validate the Phase 2B pre-authorization validation plan without physics execution."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan.json"
SCHEMA = "partonsbi.phase2b.preauthorization-validation-plan.v1"
OUTCOME = "P1_PREAUTH_PLAN_COMPLETE_READY_FOR_SEPARATE_AUTHORIZATION_REVIEW"

EXPECTED_PREDECESSORS = {
    "phase2_fonll_a_contract_amendment": (
        "docs/reduced_nc_dis/contracts/phase2_fonll_a_contract_amendment.json",
        "10cf19fedcdfe1b94e18ff89d1ae09514a31b8e0f6b055beeb729d61b6c32da8",
    ),
    "phase2a_contract_review": (
        "docs/reduced_nc_dis/contracts/phase2a_contract_review.json",
        "4ce2b5b8e910edda6f2183fe7a7e24ec1f0d5e99bd603b708f587c178d1d237b",
    ),
    "phase2a_claim_source_ledger": (
        "docs/reduced_nc_dis/contracts/phase2a_claim_source_ledger.json",
        "ca2eb35d38c59b2f5f79435acd0171b60cc80d9577d6f4db35f10d98f329f0fc",
    ),
    "phase2b_validation_plan_proposal": (
        "docs/reduced_nc_dis/contracts/phase2b_validation_plan_proposal.json",
        "e60846b5975cd12284b17ef2e28b873760b8ff17cc03f8cb3a85929af6a71786",
    ),
    "phase1bd_d0_revision": (
        "docs/phase1bd_d0_revision_decision.json",
        "ef44ec6b230d06edce4b30b435d30ee382e3e151a8dfe3a9f8098e4ac6747873",
    ),
    "phase1bd_d0r_decision": (
        "docs/phase1bd_d0r_decision.json",
        "40e75fda281578f45d193858667eeed2c1747a07d64f53672adec10145c9e775",
    ),
    "phase1bd_d1_decision": (
        "docs/phase1bd_d1_decision.json",
        "3cdb3e6e11fae63aa9b4bb9e0094c0610a8c01eb636eecc25571e3c2f11e9881",
    ),
}

PLANNING_CATEGORIES = {
    "heavy_quark_mass_convention_and_values",
    "shared_alpha_s_identity",
    "theta_anchors",
    "kinematic_domain_and_grids",
    "tolerances",
    "convergence_rules",
    "independent_reference_strategy",
    "resource_bound",
}

EXPECTED_ANCHORS = {
    ("CENTER", 0.0, 0.0),
    ("DELTA_V_MIN", -0.2, 0.0),
    ("DELTA_V_MAX", 0.2, 0.0),
    ("LAMBDA_SEA_MIN", 0.0, -0.25),
    ("LAMBDA_SEA_MAX", 0.0, 0.25),
    ("CORNER_MIN_MIN", -0.2, -0.25),
    ("CORNER_MIN_MAX", -0.2, 0.25),
    ("CORNER_MAX_MIN", 0.2, -0.25),
    ("CORNER_MAX_MAX", 0.2, 0.25),
}

GRID_IDS = {
    "DOMAIN_TENSOR_L0",
    "DOMAIN_TENSOR_L1",
    "DOMAIN_TENSOR_L2",
    "BOUNDARY_AND_THRESHOLD_AUGMENTATION",
    "NORMALIZATION_GL_CC_LEVELS",
}

TOLERANCE_FIELDS = {
    "tolerance_id",
    "quantity",
    "threshold",
    "absolute_relative_or_mixed",
    "comparison_reference",
    "numerical_precision_context",
    "justification_class",
    "justification_text",
    "failure_consequence",
}

ALLOWED_JUSTIFICATIONS = {
    "SOURCE_BOUND",
    "ANALYTIC_ERROR_BUDGET",
    "NUMERICAL_CONVERGENCE_REQUIREMENT",
    "CROSS_IMPLEMENTATION_PRECISION_REQUIREMENT",
    "REPOSITORY_PRECEDENT_WITH_ARGUMENT",
}

CONVERGENCE_IDS = {
    "INTEGRATION_CONVERGENCE",
    "GRID_REFINEMENT_STABILITY",
    "SUPPORT_BOUNDARY_STABILITY",
    "POSITIVITY_RESULT_STABILITY",
    "INDEPENDENT_REFERENCE_DISCREPANCY_STABILITY",
}

ALLOWED_EVIDENCE_CLASSES = {
    "FULL_SCHEME_INDEPENDENT_REFERENCE",
    "COMPONENT_LEVEL_INDEPENDENT_REFERENCE",
    "ANALYTIC_REFERENCE_POINT",
    "PUBLISHED_BENCHMARK",
    "INTERNAL_REPETITION",
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


class ValidationError(ValueError):
    """Raised when the serialized plan violates its pre-authorization contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def derive_outcome(record: dict[str, Any]) -> str:
    categories = record.get("planning_categories", {})
    complete = (
        set(categories) == PLANNING_CATEGORIES
        and all(value == "RESOLVED" for value in categories.values())
        and record.get("plan_completeness") == "COMPLETE"
        and len(record.get("theta_anchors", [])) == 9
        and bool(record.get("validation_grids"))
        and bool(record.get("tolerances"))
        and bool(record.get("convergence_rules"))
        and bool(record.get("independent_reference_hierarchy", {}).get("references"))
        and bool(record.get("resource_bounds"))
    )
    return OUTCOME if complete else "P2_PREAUTH_PLAN_INCOMPLETE_PRIMARY_EVIDENCE_REQUIRED"


def walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.append(str(key))
            keys.extend(walk_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.extend(walk_keys(nested))
    return keys


def validate(record: dict[str, Any], *, root: Path = ROOT, check_docs: bool = True) -> None:
    require(record.get("schema_version") == SCHEMA, "Wrong preauthorization schema")
    require(record.get("record_type") == "PRE_AUTHORIZATION_VALIDATION_PLAN", "Wrong record type")

    historical = record.get("historical_phase2a", {})
    require(historical.get("status") == "COMPLETE", "Historical Phase 2A status changed")
    require(historical.get("scientific_decision") == "INCONCLUSIVE", "Historical Phase 2A decision changed")
    require(historical.get("changed") is False, "Historical Phase 2A was rewritten")
    require(record.get("adr_013_status") == "Proposed", "ADR-013 status changed")

    predecessors = record.get("predecessor_identities", {})
    require(set(predecessors) == set(EXPECTED_PREDECESSORS), "Wrong predecessor identity set")
    for identity, (relative_path, expected_hash) in EXPECTED_PREDECESSORS.items():
        require(predecessors[identity] == expected_hash, f"Wrong predecessor identity: {identity}")
        require(file_sha256(root / relative_path) == expected_hash, f"Predecessor bytes changed: {identity}")

    accepted = record.get("accepted_contract", {})
    require(accepted.get("scheme") == "FONLL-A", "FONLL-A scheme changed")
    require(accepted.get("perturbative_order") == "NLO", "FONLL-A order changed")
    require(
        accepted.get("software")
        == {"name": "APFEL", "version": "3.1.1", "commit": "72bf6ec7c72c923dd2115f2a98c6f593f9c91d2a"},
        "APFEL identity changed",
    )
    require(accepted.get("pdf_family") == "ct18nlo_two_parameter_boundary_v2", "Accepted PDF family changed")
    require(
        accepted.get("pdf_baseline") == "ct18nlo_member0_sumrule_projected_boundary_v2",
        "Accepted PDF baseline changed",
    )
    support = accepted.get("pdf_support", {})
    require(support.get("policy") == "STRICT_INTERSECTION_NO_EXTRAPOLATION", "Strict support policy changed")

    sources = record.get("source_registry", [])
    require(len(sources) >= 8, "Insufficient source registry")
    source_ids = [source.get("source_id") for source in sources]
    require(len(source_ids) == len(set(source_ids)), "Duplicate source IDs")
    for source in sources:
        require(all(nonempty(source.get(field)) for field in ("source_id", "identity", "official_url", "retrieved_utc", "publication_or_version_date")), f"Incomplete source identity: {source.get('source_id')}")
        require(bool(re.fullmatch(r"[0-9a-f]{64}", str(source.get("sha256", "")))), f"Invalid source hash: {source.get('source_id')}")
        require(bool(source.get("locators")) and all(nonempty(item) for item in source["locators"]), f"Missing source locator: {source.get('source_id')}")

    categories = record.get("planning_categories", {})
    require(set(categories) == PLANNING_CATEGORIES, "Wrong planning category set")
    require(all(value == "RESOLVED" for value in categories.values()), "Complete plan has unresolved planning category")

    heavy = record.get("heavy_quark_contract", {})
    require(heavy.get("mass_renormalization_convention", {}).get("value") == "POLE", "Heavy-quark mass convention changed")
    require(heavy.get("charm_mass_gev", {}).get("value") == 1.3, "Charm mass changed")
    require(heavy.get("bottom_mass_gev", {}).get("value") == 4.75, "Bottom mass changed")
    require(
        heavy.get("software_controls")
        == [
            "SetPoleMasses(1.3,4.75,172.0)",
            "SetMaxFlavourPDFs(5)",
            "SetMaxFlavourAlpha(5)",
            'SetMassScheme("FONLL-A")',
            "EnableDampingFONLL(1)",
            "SetDampingPowerFONLL(2,2,2)",
        ],
        "APFEL heavy-flavor controls changed",
    )
    for field in ("mass_renormalization_convention", "charm_mass_gev", "bottom_mass_gev", "threshold_relationship"):
        require(nonempty(heavy.get(field, {}).get("classification")), f"Missing heavy-mass classification: {field}")
        require(nonempty(heavy.get(field, {}).get("rationale")), f"Missing heavy-mass rationale: {field}")
    require(heavy.get("unresolved") == [], "Heavy-quark contract remains unresolved")

    alpha = record.get("alpha_s_contract", {})
    require(alpha.get("alpha_s_reference_value") == 0.118, "alpha_s reference value changed")
    require(alpha.get("reference_scale_gev") == 91.187, "alpha_s reference scale changed")
    require(alpha.get("perturbative_evolution_order") == "NLO_TWO_LOOP", "alpha_s order changed")
    require(
        alpha.get("software_controls")
        == ["SetAlphaQCDRef(0.118,91.187)", "SetPerturbativeOrder(1)"],
        "APFEL alpha_s controls changed",
    )
    require("own implementation" in alpha.get("independent_reference_binding", ""), "Independent alpha_s identity is circular")
    require(alpha.get("unresolved") == [], "alpha_s contract remains unresolved")

    theta = record.get("theta_domain", {})
    require(theta.get("bounds") == {"delta_v": [-0.2, 0.2], "lambda_sea": [-0.25, 0.25]}, "Accepted theta domain changed")
    require(theta.get("prior_selected") is False, "Validation box was converted into a prior")
    anchors = record.get("theta_anchors", [])
    anchor_tuples = {(anchor.get("anchor_id"), anchor.get("delta_v"), anchor.get("lambda_sea")) for anchor in anchors}
    require(len(anchors) == len(anchor_tuples), "Duplicate anchor IDs or coordinates")
    require(anchor_tuples == EXPECTED_ANCHORS, "Required theta anchor missing or changed")
    for _, delta_v, lambda_sea in anchor_tuples:
        require(-0.2 <= delta_v <= 0.2 and -0.25 <= lambda_sea <= 0.25, "Theta anchor outside accepted domain")

    coordinates = record.get("coordinate_contract", {})
    require(coordinates.get("coordinates") == ["x_Bj", "Q2"], "Coordinate convention changed")
    require(coordinates.get("differential_quantity") == "d2sigma_dx_Bj_dQ2", "Differential measure changed")
    require(coordinates.get("s_massless_gev2") == 101200.0, "Beam invariant changed")
    require(coordinates.get("jacobian") == "dy/dQ2 at fixed x_Bj = 1/(s*x_Bj)", "Jacobian contract changed")

    domain = record.get("physics_validity_domain", {})
    require(domain.get("domain_id") == "HERA_PQCD_STRICT_SUPPORT_INTERSECTION_V1", "Physics domain identity changed")
    require(domain.get("x_bj_bounds") == [6e-07, 0.65], "Physics x bounds changed")
    require(domain.get("q2_bounds_gev2") == [3.5, 50000.0], "Physics Q2 bounds changed")
    require(domain.get("y_bounds") == [0.005, 0.95], "Physics y bounds changed")
    require(domain.get("distinct_from_numerical_grid") is True, "Grid was used to define physics validity")
    require(nonempty(domain.get("rationale")), "Physics-domain rationale missing")

    grids = record.get("validation_grids", [])
    require(bool(grids), "Required grid is empty")
    grid_ids = [grid.get("grid_id") for grid in grids]
    require(len(grid_ids) == len(set(grid_ids)), "Duplicate grid IDs")
    require(set(grid_ids) == GRID_IDS, "Required grid missing")
    for grid in grids:
        require(len(grid) > 2, f"Grid definition is empty: {grid.get('grid_id')}")

    tolerances = record.get("tolerances", [])
    require(bool(tolerances), "Tolerance table is empty")
    tolerance_ids = [tolerance.get("tolerance_id") for tolerance in tolerances]
    require(len(tolerance_ids) == len(set(tolerance_ids)), "Duplicate tolerance IDs")
    forbidden_rationales = ("standard tolerance", "reasonable tolerance", "typical tolerance")
    for tolerance in tolerances:
        require(TOLERANCE_FIELDS <= set(tolerance), f"Tolerance missing required field: {tolerance.get('tolerance_id')}")
        require(tolerance.get("justification_class") in ALLOWED_JUSTIFICATIONS, f"Invalid tolerance justification: {tolerance.get('tolerance_id')}")
        for field in TOLERANCE_FIELDS - {"threshold"}:
            require(nonempty(tolerance.get(field)), f"Tolerance has empty field: {tolerance.get('tolerance_id')}/{field}")
        threshold = tolerance.get("threshold")
        require((isinstance(threshold, (int, float)) and not isinstance(threshold, bool) and math.isfinite(threshold) and threshold > 0) or nonempty(threshold), f"Invalid tolerance threshold: {tolerance.get('tolerance_id')}")
        rationale = tolerance["justification_text"].lower()
        require(not any(phrase in rationale for phrase in forbidden_rationales), f"Forbidden tolerance rationale: {tolerance.get('tolerance_id')}")

    convergence = record.get("convergence_rules", [])
    convergence_ids = [rule.get("convergence_id") for rule in convergence]
    require(len(convergence_ids) == len(set(convergence_ids)), "Duplicate convergence IDs")
    require(set(convergence_ids) == CONVERGENCE_IDS, "Required convergence rule missing")
    for rule in convergence:
        require(all(nonempty(rule.get(status)) for status in ("pass", "fail", "inconclusive")), f"Incomplete convergence definition: {rule.get('convergence_id')}")

    hierarchy = record.get("independent_reference_hierarchy", {})
    require(hierarchy.get("full_end_to_end_fonll_a_observable_reference_available") is False, "Invented full FONLL-A independent reference")
    require(nonempty(hierarchy.get("gate_interpretation")), "Independent-reference gate interpretation missing")
    references = hierarchy.get("references", [])
    reference_ids = [reference.get("reference_id") for reference in references]
    require(len(reference_ids) == len(set(reference_ids)), "Duplicate independent-reference IDs")
    require(len(references) >= 5, "Incomplete independent-reference hierarchy")
    for reference in references:
        require(reference.get("evidence_class") in ALLOWED_EVIDENCE_CLASSES, f"Invalid evidence class: {reference.get('reference_id')}")
        require(bool(reference.get("covers")), f"Reference has empty coverage: {reference.get('reference_id')}")
        require(bool(reference.get("does_not_cover")), f"Reference omits noncoverage: {reference.get('reference_id')}")
        if reference.get("evidence_class") == "INTERNAL_REPETITION":
            require(reference.get("independent") is False, "Internal repetition marked independent")
        if "WRAPPER" in str(reference.get("reference_id", "")):
            require(reference.get("independent") is False, "APFEL wrapper marked independent")
    require(bool(hierarchy.get("fake_independence_forbidden")), "Fake-independence prohibitions missing")

    resources = record.get("resource_bounds", {})
    expected_resources = {
        "maximum_theta_anchors": 9,
        "maximum_refinement_levels": 3,
        "maximum_point_grid_evaluations": 63882,
        "maximum_normalization_integrand_evaluations": 98811,
        "maximum_independent_reference_evaluations": 310,
        "maximum_total_declared_evaluations": 163003,
        "maximum_output_bytes": 67108864,
    }
    for field, expected in expected_resources.items():
        require(resources.get(field) == expected, f"Resource bound missing or changed: {field}")
    require(nonempty(resources.get("derivation")), "Resource-bound derivation missing")
    require("INCONCLUSIVE" in resources.get("wall_clock_rule", ""), "Resource stopping rule missing")

    positivity = record.get("positivity_no_hidden_clipping_contract", {})
    require(positivity.get("required_nonnegative") is True, "Complete rate need not be nonnegative")
    for field in ("clipping_allowed", "abs_allowed", "max_rate_zero_allowed", "post_hoc_support_deletion_allowed", "hidden_rejected_point_removal_allowed"):
        require(positivity.get(field) is False, f"Forbidden positivity repair enabled: {field}")
    require(positivity.get("repair_mechanism") is None, "Positivity repair mechanism introduced")
    require("binary128" in positivity.get("roundoff_semantics", ""), "Roundoff sign adjudication missing")

    normalization = record.get("normalization_closure_contract", {})
    require(normalization.get("finite_required") is True, "Finite normalization not required")
    require(normalization.get("strictly_positive_required") is True, "Positive normalization not required")
    require(normalization.get("fixed_n_shape_only_preserved") is True, "Fixed-N shape-only semantics changed")
    require(normalization.get("count_or_rate_likelihood_included") is False, "Count/rate likelihood introduced")
    require(nonempty(normalization.get("independent_evaluation")), "Independent normalization evaluation missing")

    precedence = record.get("failure_precedence", [])
    require(precedence[:4] == ["CONTRACT_IDENTITY_FAILURE", "NONFINITE_RATE", "NEGATIVE_RATE", "OUTSIDE_SUPPORT"], "Failure precedence weakened")
    require(len(precedence) == len(set(precedence)), "Duplicate failure-precedence entries")

    separation = record.get("pre_auth_post_auth_separation", {})
    require(set(separation.get("pre_auth_complete", [])) == EXPECTED_PRE_AUTH, "PRE_AUTH classification incomplete")
    require(set(separation.get("post_auth_not_executed", [])) == EXPECTED_POST_AUTH, "POST_AUTH classification changed")

    authorization = record.get("authorization", {})
    require(bool(authorization) and all(value is False for value in authorization.values()), "Authorization flag is true")
    phase2b = record.get("phase2b_state", {})
    require(phase2b.get("issue") == 55 and phase2b.get("state") == "OPEN", "Issue #55 state changed")
    require(phase2b.get("project_status") == "Backlog", "Issue #55 project status changed")
    require(phase2b.get("gate_decision") == "Not Evaluated", "Issue #55 gate decision changed")
    require(phase2b.get("authorization") == "Not Authorized", "Issue #55 was authorized")
    require(phase2b.get("execution_status") == "NOT_EXECUTED", "Phase 2B execution occurred")
    require(phase2b.get("plan_completeness") == "COMPLETE", "P1 plan is not complete")

    state = record.get("validation_state", {})
    require(bool(state) and all(value is False for value in state.values()), "Numerical execution or result state is present")
    forbidden_result_keys = {
        "numerical_results",
        "observed_minimum_rate",
        "observed_normalization",
        "positivity_result",
        "normalization_result",
        "reference_result",
    }
    require(not (set(walk_keys(record)) & forbidden_result_keys), "Numerical result field masquerades as planning")

    require(record.get("plan_completeness") == "COMPLETE", "Plan completeness changed")
    require(record.get("outcome") == derive_outcome(record), "Outcome is not derived from plan completeness")
    require(record.get("outcome") == OUTCOME, "Wrong P1/P2/P3/P4 outcome")
    require(bool(record.get("remaining_limitations")), "Scientific limitations are hidden")
    require("separate authorization review" in record.get("next_step", ""), "Next decision is not separate authorization review")
    require(not (root / "docs/reduced_nc_dis/sources/papers").exists(), "Publication bytes were committed")

    if check_docs:
        doc_markers = {
            "docs/reduced_nc_dis/PHASE2B_PREAUTHORIZATION_VALIDATION_PLAN.md": [
                OUTCOME,
                "PHASE2B_AUTHORIZED = false",
                "PHASE2B_EXECUTION_STATUS = NOT_EXECUTED",
                "No complete independent implementation",
            ],
            "docs/CURRENT_PHASE.md": [OUTCOME, "Phase 2B remains Not Authorized"],
            "docs/reduced_nc_dis/README.md": ["pre-authorization validation plan", "NOT_EXECUTED"],
            "docs/reduced_nc_dis/ROADMAP.md": [OUTCOME, "Not Authorized"],
            "docs/adr/ADR-013-reduced-nc-dis-observation-law-contract.md": [
                "Historical Phase 2A remains `INCONCLUSIVE`",
                "Phase 2B remains `NOT_AUTHORIZED` and `NOT_EXECUTED`",
            ],
        }
        for relative_path, markers in doc_markers.items():
            text = (root / relative_path).read_text(encoding="utf-8")
            for marker in markers:
                require(marker in text, f"Documentation marker missing from {relative_path}: {marker}")


def main() -> None:
    try:
        record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        validate(record)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise SystemExit(f"INVALID phase2b.preauthorization_validation_plan: {error}") from error
    print("VALID phase2b.preauthorization_validation_plan")


if __name__ == "__main__":
    main()
