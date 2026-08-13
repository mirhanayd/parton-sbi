#!/usr/bin/env python3
"""Validate the Phase 2B preauthorization v2 plan without DIS execution."""

from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v2.json"
SCHEMA = "partonsbi.phase2b.preauthorization-validation-plan.v2"
RV1 = "RV1_PREAUTH_V2_COMPLETE_READY_FOR_NEW_AUTHORIZATION_REVIEW"
RV2 = "RV2_ALPHA_S_CONTRACT_STILL_BLOCKED"
RV3 = "RV3_REFERENCE_COVERAGE_STILL_BLOCKED"
RV4 = "RV4_ERROR_BUDGET_STILL_BLOCKED"
RV5 = "RV5_MULTIPLE_PREAUTH_BLOCKERS_REMAIN"

EXPECTED_PREDECESSORS = {
    "fonll_a_amendment": (
        "docs/reduced_nc_dis/contracts/phase2_fonll_a_contract_amendment.json",
        "10cf19fedcdfe1b94e18ff89d1ae09514a31b8e0f6b055beeb729d61b6c32da8",
    ),
    "preauthorization_v1": (
        "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan.json",
        "7eb8834eb8435532a85bd7d49b173b03e57a268f69f9676e0effbd877903672b",
    ),
    "execution_authorization_review_v1": (
        "docs/reduced_nc_dis/contracts/phase2b_execution_authorization_review.json",
        "03d8119efb819b7a8b51161d5f2ce58fe59dd385b63f2dbfd6203692dac1f9e2",
    ),
}

BLOCKERS = {
    "B1_SHARED_ALPHA_S_IDENTITY",
    "B2_NEGATIVE_RATE_ADJUDICATION",
    "B3_REFERENCE_AND_BRIDGE_INDEPENDENCE",
    "B4_TOLERANCE_AND_NEAR_ZERO_ERROR_BUDGETS",
}

SOURCE_HASHES = {
    "NNPDF_CHARM_2016_V3": {
        "e77630247ee7e60a115918b3a7cce27bf5c138bf727a9f41d291fb13b44328bd",
        "14719f6141494003411e1e071acc5642ab7f3bb0bca83c502eeb33dd0eda7413",
    },
    "MASSIVEDISFUNCTION_1_2": {
        "2361fb39f047f42ad1f964f49b43ecd619a599c3afecc8137435c32e79fda420",
        "ccdcbc5147da8532cf80c41d890cc117adee10d3a9141164de752780cfd8f9f2",
    },
    "SCIPY_1_18_0_SDIST": {
        "67b2ad2ad54c72ca6d04975a9b2df8c3638c34ddd5b28738e94fc2b57929d378"
    },
    "WALDVOGEL_CC_2006": {
        "183264aa174aa7cd542e69715d41dfb4f28e057a3a898c47ad90f85bd7632128"
    },
    "MPMATH_1_3_0_SDIST": {
        "7a28eb2a9774d00c7bc92411c19a89209d5da7c4c9a9e227be8330a23a25b91f"
    },
}

COVERAGE_NODES = {
    "complete_nc_rate",
    "electroweak_assembly",
    "massless_coefficients",
    "massive_contribution",
    "fonll_matching_difference_term",
    "pdf_provider",
    "pdf_to_apfel_bridge",
    "alpha_s",
    "coordinate_jacobian",
    "quadrature_a",
    "quadrature_b",
    "normalization_assembly",
}

ALLOWED_COVERAGE = {
    "FULLY_INDEPENDENT",
    "PUBLISHED_INDEPENDENT_BENCHMARK",
    "INDEPENDENT_POSTAUTH_TEST_DEFINED",
    "PARTIAL",
    "UNVALIDATED",
}

BUDGET_COMPONENTS = {
    "PDF_BRIDGE",
    "ALPHA_S_EQUIVALENCE",
    "STRUCTURE_FUNCTION_EVALUATION",
    "COORDINATE_JACOBIAN",
    "GRID_DISCRETIZATION",
    "QUADRATURE_A",
    "QUADRATURE_B",
    "NORMALIZATION_PROPAGATION",
}

TOLERANCE_IDS = {
    "TOL_MASSIVEDIS_FONLL_COMPONENT",
    "TOL_MASSLESS_NC_REFERENCE",
    "TOL_ALPHA_S_PROVIDER_EQUIVALENCE",
    "TOL_PDF_APFEL_BRIDGE",
    "TOL_JACOBIAN",
}

POST_AUTH = {
    "ALPHA_S_PROVIDER_EQUIVALENCE",
    "PDF_APFEL_BRIDGE_COMPARISON",
    "MASSIVEDIS_FONLL_COMPONENT_COMPARISON",
    "MASSLESS_REFERENCE_COMPARISON",
    "APFEL_FONLL_A_EVALUATIONS",
    "POSITIVITY_SCAN",
    "NORMALIZATION_INTEGRATIONS",
    "CONVERGENCE_STUDY",
    "INDEPENDENT_REFERENCE_CLOSURE",
    "SELECTED_EVENT_NORMALIZATION_EVALUATION",
}


class ValidationError(ValueError):
    """Raised when the successor plan violates its static contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def derive_outcome(record: dict[str, Any]) -> str:
    alpha = record.get("alpha_s_architecture", {})
    alpha_ok = (
        alpha.get("choice") in {"AS1_SINGLE_SHARED_PROVIDER", "AS2_DUAL_PROVIDER_PREDECLARED_EQUIVALENCE_TEST"}
        and alpha.get("plan_resolution") == "RESOLVED_AT_PLAN_LEVEL"
        and alpha.get("future_equivalence_test", {}).get("status") == "DEFINED_NOT_EXECUTED"
    )
    coverage = record.get("independent_reference_coverage", [])
    coverage_ok = (
        {item.get("node") for item in coverage} == COVERAGE_NODES
        and not any(item.get("load_bearing") and item.get("classification") == "UNVALIDATED" for item in coverage)
        and record.get("pdf_apfel_bridge_contract", {}).get("classification")
        == "BRIDGE_STATICALLY_BOUND_AND_POSTAUTH_TESTABLE"
        and record.get("quadrature_contract", {}).get("shared_node_weight_or_accumulation_core_allowed") is False
    )
    budget = record.get("numerical_error_budget", {})
    components = budget.get("components", [])
    budget_ok = (
        {item.get("id") for item in components} == BUDGET_COMPONENTS
        and math.isclose(sum(item.get("relative_share", math.inf) for item in components), 0.001, abs_tol=1e-15)
        and budget.get("parent", {}).get("value") == 0.001
        and budget.get("relative_sum") == 0.001
        and "0.0013" not in json.dumps(record)
        and "factor ten" not in json.dumps(record).lower()
    )
    negative = record.get("negative_rate_policy", {})
    negative_ok = (
        negative.get("choice") in {"NR1_FULL_HIGH_PRECISION_REFERENCE", "NR2_ERROR_ENVELOPE_WITH_INCONCLUSIVE_BAND"}
        and negative.get("plan_resolution") == "RESOLVED_AT_PLAN_LEVEL"
        and negative.get("classification", {}).get("inconclusive_band")
        == "|r_hat| <= E_total => INCONCLUSIVE_SIGN"
    )
    failures = [not alpha_ok, not coverage_ok, not budget_ok or not negative_ok]
    if not any(failures):
        return RV1
    if failures == [True, False, False]:
        return RV2
    if failures == [False, True, False]:
        return RV3
    if failures == [False, False, True]:
        return RV4
    return RV5


def validate(record: dict[str, Any], *, root: Path = ROOT, check_docs: bool = True) -> None:
    require(record.get("schema_version") == SCHEMA, "Wrong v2 schema")
    require(
        record.get("record_type") == "PHASE2B_PREAUTHORIZATION_VALIDATION_PLAN_SUCCESSOR_REVISION",
        "Wrong v2 record type",
    )
    require(record.get("starting_main_sha") == "4597b5f0896c133861222b6b0c123fb0cd6b7362", "Starting main changed")

    predecessors = record.get("predecessors", {})
    require(set(predecessors) == set(EXPECTED_PREDECESSORS), "Wrong predecessor set")
    for identity, (relative_path, expected_hash) in EXPECTED_PREDECESSORS.items():
        item = predecessors[identity]
        require(item.get("path") == relative_path, f"Wrong predecessor path: {identity}")
        require(item.get("sha256") == expected_hash, f"Wrong predecessor SHA: {identity}")
        require(file_sha256(root / relative_path) == expected_hash, f"Historical predecessor bytes changed: {identity}")
    require(predecessors["preauthorization_v1"].get("bytes_immutable") is True, "v1 immutability not bound")
    require(predecessors["execution_authorization_review_v1"].get("bytes_immutable") is True, "AR2 immutability not bound")

    requirements = {
        line.strip()
        for line in (root / "analysis/requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    require("scipy==1.18.0" in requirements, "SciPy quadrature version not pinned")
    require("mpmath==1.3.0" in requirements, "alpha_s precision reference version not pinned")

    historical = record.get("historical_state", {})
    require(historical.get("phase2a_status") == "COMPLETE", "Historical Phase 2A status changed")
    require(historical.get("phase2a_scientific_decision") == "INCONCLUSIVE", "Historical Phase 2A changed to PASS")
    require(historical.get("phase2a_changed") is False, "Historical Phase 2A rewritten")
    require(historical.get("adr_013_status") == "Proposed", "ADR-013 state changed")
    for field in ("fonll_a_contract_changed", "preauthorization_v1_changed", "authorization_review_v1_changed"):
        require(historical.get(field) is False, f"Historical record changed: {field}")

    accepted = record.get("accepted_contract", {})
    require((accepted.get("scheme"), accepted.get("perturbative_order")) == ("FONLL-A", "NLO"), "FONLL-A contract changed")
    require(
        accepted.get("software")
        == {"name": "APFEL", "version": "3.1.1", "commit": "72bf6ec7c72c923dd2115f2a98c6f593f9c91d2a"},
        "APFEL identity changed",
    )
    require(accepted.get("pdf_family") == "ct18nlo_two_parameter_boundary_v2", "Accepted PDF family changed")
    require(accepted.get("pdf_baseline") == "ct18nlo_member0_sumrule_projected_boundary_v2", "Accepted PDF baseline changed")
    require(accepted.get("strict_support") is True, "Strict support weakened")
    require(accepted.get("theta_domain") == {"delta_v": [-0.2, 0.2], "lambda_sea": [-0.25, 0.25]}, "Theta domain changed")
    require(accepted.get("theta_anchor_count") == 9, "Theta anchor count changed")

    blocker_resolution = record.get("ar2_blocker_resolution", {})
    require(set(blocker_resolution) == BLOCKERS, "AR2 blocker set changed")
    require(all("RESOLVED_AT_PLAN_LEVEL" in value for value in blocker_resolution.values()), "AR2 blocker unresolved")

    source_policy = record.get("source_policy", {})
    require(source_policy.get("cache_path") == "/tmp/partonsbi-phase2b-preauth-v2-review/", "Wrong source cache")
    require(source_policy.get("source_bytes_committed") is False, "Source bytes claimed committed")
    sources = record.get("source_registry_additions", [])
    source_map = {source.get("source_id"): source for source in sources}
    require(len(sources) == len(source_map), "Duplicate source ID")
    require(set(source_map) == set(SOURCE_HASHES), "Wrong added source set")
    for source_id, expected_hashes in SOURCE_HASHES.items():
        source = source_map[source_id]
        require(
            all(nonempty(source.get(field)) for field in ("title", "authors_or_project", "official_url", "publication_or_version", "retrieved_utc", "claim_supported", "qualification", "explicit_noncoverage")),
            f"Incomplete source record: {source_id}",
        )
        require(bool(source.get("exact_locators")), f"Missing source locator: {source_id}")
        hashes = {stream.get("sha256") for stream in source.get("byte_streams", [])}
        require(hashes == expected_hashes, f"Wrong source hash: {source_id}")

    massive = record.get("massivedisfunction_assessment", {})
    require(massive.get("classification") == "MASSIVE_FONLL_COMPONENT_ORACLE", "Wrong MassiveDISsFunction classification")
    require(massive.get("implementation_independent_from_apfel") is True, "MassiveDISsFunction independence denied")
    require(
        any("old FONLL-A S-ACOT" in item for item in massive.get("covered_components", [])),
        "No-intrinsic-charm special case missing",
    )
    require(bool(massive.get("not_covered")), "MassiveDISsFunction noncoverage hidden")
    require(
        "SetPrec(6.25e-5)" in massive.get("future_configuration", "")
        and "GSL qags" in massive.get("future_configuration", "")
        and "half T_SF=0.000125" in massive.get("future_configuration", ""),
        "MassiveDISsFunction precision budget unbound",
    )
    require(massive.get("future_status") == "DEFINED_NOT_EXECUTED", "MassiveDISsFunction comparison executed")

    alpha = record.get("alpha_s_architecture", {})
    require(alpha.get("choice") == "AS2_DUAL_PROVIDER_PREDECLARED_EQUIVALENCE_TEST", "Wrong alpha_s architecture")
    require("CT18NLO DataVersion 1" in alpha.get("provider_a", {}).get("identity", ""), "Wrong CT18 alpha_s provider")
    require("APFEL 3.1.1" in alpha.get("provider_b", {}).get("identity", ""), "Wrong APFEL alpha_s provider")
    require("cubic Hermite interpolation" in alpha.get("provider_a", {}).get("representation", ""), "CT18 interpolation algorithm unbound")
    require("10-step classical RK4" in alpha.get("provider_b", {}).get("identity", ""), "APFEL provider precision unbound")
    alpha_test = alpha.get("future_equivalence_test", {})
    require(alpha_test.get("status") == "DEFINED_NOT_EXECUTED", "alpha_s test was executed")
    require("257 fixed log-Q nodes" in alpha_test.get("comparison_points", ""), "alpha_s grid missing")
    require(
        "E_CT18_ipol(Q)+E_APFEL_RK4(Q)" in alpha_test.get("criterion", "")
        and "32*2^-53" in alpha_test.get("criterion", ""),
        "Wrong alpha_s mixed criterion",
    )
    require("+/-5e-7" in alpha_test.get("ct18_interpolation_envelope", ""), "CT18 interpolation envelope missing")
    require(
        all(token in alpha_test.get("apfel_precision_envelope", "") for token in ("mp.dps=80", "20,40,80,160", "d_160/7", "INCONCLUSIVE_PROVIDER_PRECISION")),
        "APFEL provider precision envelope missing",
    )
    require("half-last-decimal" in alpha_test.get("atol_derivation", ""), "alpha_s atol lacks serialization derivation")
    require("0.000125" in alpha_test.get("budget_gate", ""), "alpha_s budget gate missing")
    require(alpha.get("actual_equivalence_result") == "NOT_EXECUTED", "alpha_s result present")

    bridge = record.get("pdf_apfel_bridge_contract", {})
    require(bridge.get("classification") == "BRIDGE_STATICALLY_BOUND_AND_POSTAUTH_TESTABLE", "Bridge architecture unresolved")
    require("number densities" in bridge.get("value_convention", "") and "x*f_i exactly once" in bridge.get("value_convention", ""), "Bridge x*f convention missing")
    expected_slots = {str(slot) for slot in range(-6, 8)}
    require(set(bridge.get("flavor_map", {})) == expected_slots, "Bridge flavor map incomplete")
    require(bridge.get("flavor_map", {}).get("0") == "x*gluon from PDG 21", "Bridge gluon map changed")
    bridge_test = bridge.get("future_validation_test", {})
    require(bridge_test.get("status") == "DEFINED_NOT_EXECUTED", "Bridge test was executed")
    require("14 distinct" in bridge_test.get("synthetic_test", ""), "Bridge synthetic sentinel test missing")
    require("nine theta anchors" in bridge_test.get("accepted_value_test", ""), "Bridge accepted-value grid missing")
    require(bridge.get("actual_bridge_result") == "NOT_EXECUTED", "Bridge result present")

    quadrature = record.get("quadrature_contract", {})
    require(quadrature.get("shared_node_weight_or_accumulation_core_allowed") is False, "Shared quadrature core allowed")
    path_a = quadrature.get("path_a", {})
    path_b = quadrature.get("path_b", {})
    require(path_a.get("implementation") == "scipy.special.roots_legendre", "Wrong quadrature A implementation")
    require(
        path_a.get("integration_entrypoint")
        == "analysis/validation/phase2b_quadrature_oracles.py::scipy_gauss_legendre_integrate",
        "Wrong quadrature A integration entrypoint",
    )
    require(path_a.get("version") == "SciPy 1.18.0", "Quadrature A version not pinned")
    require(path_a.get("orders") == [16, 32, 64], "Quadrature A levels changed")
    require(path_b.get("implementation") == "analysis/validation/phase2b_quadrature_oracles.py::clenshaw_curtis_rule", "Wrong quadrature B implementation")
    require(
        path_b.get("integration_entrypoint")
        == "analysis/validation/phase2b_quadrature_oracles.py::clenshaw_curtis_integrate",
        "Wrong quadrature B integration entrypoint",
    )
    require(path_b.get("node_counts") == [17, 33, 65], "Quadrature B levels changed")
    module_path = root / "analysis/validation/phase2b_quadrature_oracles.py"
    require(file_sha256(module_path) == path_b.get("implementation_sha256"), "Quadrature B implementation bytes changed")
    module = ast.parse(module_path.read_text(encoding="utf-8"))
    functions = [
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"clenshaw_curtis_rule", "clenshaw_curtis_integrate"}
    ]
    identifiers = {
        value
        for function in functions
        for child in ast.walk(function)
        for value in (
            child.id.lower() if isinstance(child, ast.Name) else None,
            child.attr.lower() if isinstance(child, ast.Attribute) else None,
        )
        if value is not None
    }
    require(
        not identifiers.intersection({"scipy", "numpy", "roots_legendre", "leggauss"}),
        "Fake quadrature independence",
    )
    require(quadrature.get("analytic_software_tests", {}).get("physics_integrals_executed") is False, "Physics integral executed as software test")

    coverage = record.get("independent_reference_coverage", [])
    coverage_map = {item.get("node"): item for item in coverage}
    require(len(coverage) == len(coverage_map), "Duplicate coverage node")
    require(set(coverage_map) == COVERAGE_NODES, "Reference coverage graph incomplete")
    for node, item in coverage_map.items():
        require(item.get("classification") in ALLOWED_COVERAGE, f"Invalid coverage class: {node}")
        require(item.get("load_bearing") is True, f"Coverage node not load-bearing: {node}")
        require(nonempty(item.get("oracle")) and nonempty(item.get("future_test")), f"Coverage node undefined: {node}")
    if record.get("outcome") == RV1:
        require(not any(item.get("classification") == "UNVALIDATED" for item in coverage), "RV1 with UNVALIDATED load-bearing node")
    sufficiency = record.get("reference_sufficiency", {})
    require(sufficiency.get("unvalidated_load_bearing_nodes") == [], "Unvalidated nodes hidden")
    require(sufficiency.get("full_end_to_end_independent_comparator_claimed") is False, "Invented end-to-end comparator")

    comparison = record.get("comparison_policy", {})
    require(comparison.get("generic_mixed_form") == "|a-b| <= atol_pair + rtol_source*max(|a|,|b|)", "Mixed comparison form missing")
    require("INCONCLUSIVE_NEAR_ZERO" in comparison.get("near_zero_semantics", ""), "Near-zero semantics missing")
    require(comparison.get("post_hoc_tuning_allowed") is False, "Post-hoc tolerance tuning allowed")
    tolerances = record.get("comparator_tolerances", [])
    tolerance_map = {item.get("tolerance_id"): item for item in tolerances}
    require(len(tolerances) == len(tolerance_map), "Duplicate tolerance")
    require(set(tolerance_map) == TOLERANCE_IDS, "Tolerance table incomplete")
    for tolerance_id, item in tolerance_map.items():
        for field in ("quantity", "rtol", "atol", "derivation", "scope", "near_zero", "failure"):
            value = item.get(field)
            require(nonempty(value) or isinstance(value, (int, float)), f"Tolerance field missing: {tolerance_id}/{field}")
        require("factor ten" not in item.get("derivation", "").lower(), f"Factor-ten-only tolerance: {tolerance_id}")
    require(tolerance_map["TOL_ALPHA_S_PROVIDER_EQUIVALENCE"].get("rtol") == "32*2^-53", "Wrong-object alpha_s epsilon tolerance")
    require(
        tolerance_map["TOL_ALPHA_S_PROVIDER_EQUIVALENCE"].get("atol")
        == "E_CT18_ipol(Q)+E_APFEL_RK4(Q)",
        "alpha_s absolute tolerance changed",
    )

    budget = record.get("numerical_error_budget", {})
    require(budget.get("parent", {}).get("value") == 0.001, "Wrong external error allowance")
    components = budget.get("components", [])
    component_map = {item.get("id"): item for item in components}
    require(len(components) == len(component_map), "Duplicate error-budget component")
    require(set(component_map) == BUDGET_COMPONENTS, "Missing error-budget component")
    shares = [item.get("relative_share") for item in components]
    require(all(isinstance(value, float) and value > 0 for value in shares), "Invalid error-budget share")
    require(math.isclose(sum(shares), 0.001, abs_tol=1e-15), "Error-budget sum exceeds parent allowance")
    require(budget.get("relative_sum") == 0.001, "Serialized error-budget sum changed")
    require("assigned once" in budget.get("double_counting_policy", ""), "Error budget can double count")
    serialized = json.dumps(record).lower()
    require("0.0013" not in serialized, "Arbitrary v1 0.0013 retained")
    require("one tenth" not in serialized and "factor ten" not in serialized, "Factor-ten-only rationale retained")

    negative = record.get("negative_rate_policy", {})
    require(negative.get("choice") == "NR2_ERROR_ENVELOPE_WITH_INCONCLUSIVE_BAND", "Wrong negative-rate architecture")
    require("E_total=E_upstream+E_outer" in negative.get("total_formula", ""), "Incomplete propagated sign envelope")
    require(
        negative.get("classification", {}).get("rate_below_negative_envelope")
        == "r_hat < -E_total => FAIL_NEGATIVE_RATE",
        "Negative envelope no longer fails",
    )
    require(negative.get("classification", {}).get("inconclusive_band") == "|r_hat| <= E_total => INCONCLUSIVE_SIGN", "INCONCLUSIVE_SIGN policy changed")
    require("prevents a global positivity PASS" in negative.get("global_semantics", ""), "INCONCLUSIVE_SIGN counted as PASS")
    for field in ("clipping_allowed", "abs_allowed", "max_rate_zero_allowed", "support_deletion_allowed", "retry_until_positive_allowed"):
        require(negative.get(field) is False, f"Forbidden negative-rate repair enabled: {field}")
    require(negative.get("raw_signed_rate_retained") is True, "Raw signed rate not retained")
    require(negative.get("actual_sign_result") == "NOT_EXECUTED", "Sign result present")

    normalized = record.get("normalized_law_error_propagation", {})
    require("E_r/(Z_hat-E_Z)" in normalized.get("pointwise_bound", ""), "Normalized-law propagation missing")
    require("no division by r_hat" in normalized.get("near_zero_rate", ""), "Normalized-law near-zero rule missing")
    require("I_A[r]/Z_B" in normalized.get("cross_normalization", ""), "Independent cross-normalization missing")
    require("no standalone residual threshold" in normalized.get("closure_bound", ""), "Arbitrary normalized-law tolerance retained")
    require(normalized.get("actual_normalization_result") == "NOT_EXECUTED", "Normalization result present")

    jacobian = record.get("jacobian_audit", {})
    require((jacobian.get("result"), jacobian.get("tolerance")) == ("RETAIN_8U", "8*2^-53 relative"), "Jacobian tolerance changed")
    require(jacobian.get("actual_check") == "NOT_EXECUTED", "Jacobian physics check executed")

    resources = record.get("resource_bounds", {})
    references = 310 + 2 * 282 + 9 * (17 + 33 + 65) + 282
    beta_rhs = 282 * (20 + 40 + 80 + 160) * 4
    total = 63882 + 98811 + references + beta_rhs
    require(references == 2191 and beta_rhs == 338400 and total == 503284, "Internal v2 resource derivation changed")
    require(resources.get("maximum_point_grid_evaluations") == 63882, "Point resource count changed")
    require(resources.get("maximum_normalization_integrand_evaluations") == 98811, "Normalization resource count changed")
    require(resources.get("maximum_reference_and_contract_evaluations") == references, "Reference resource count mismatch")
    require(resources.get("alpha_s_high_precision_beta_rhs_evaluations") == beta_rhs, "alpha_s precision resource count mismatch")
    require(resources.get("maximum_total_declared_evaluations") == total, "Total resource count mismatch")
    require(resources.get("maximum_output_bytes") == 64 * 1024 * 1024, "Output bound changed")
    require(resources.get("unbounded_adaptive_loop") is False, "Unbounded adaptive loop allowed")
    require(resources.get("continue_until_pass_allowed") is False, "Continue-until-pass allowed")
    require(resources.get("exhaustion_result") == "INCONCLUSIVE", "Resource exhaustion can pass")

    precedence = record.get("failure_precedence", [])
    require(precedence[:4] == ["CONTRACT_IDENTITY_FAILURE", "NONFINITE_RATE", "FAIL_NEGATIVE_RATE", "OUTSIDE_SUPPORT"], "Failure precedence weakened")
    require("INCONCLUSIVE_SIGN" in precedence, "Sign inconclusive state missing")
    require(len(precedence) == len(set(precedence)), "Duplicate failure precedence")

    separation = record.get("pre_auth_post_auth", {})
    require(set(separation.get("post_auth_defined_not_executed", [])) == POST_AUTH, "POST_AUTH set changed")
    require(separation.get("post_auth_status") == "DEFINED_NOT_EXECUTED", "POST_AUTH work executed")
    require(len(separation.get("pre_auth_resolved", [])) == 8, "PRE_AUTH blocker coverage incomplete")

    criteria = record.get("decision_criteria", {})
    require(bool(criteria) and all(value == "PASS" for value in criteria.values()), "RV1 criterion did not pass")
    require(record.get("outcome") == derive_outcome(record), "RV outcome is not derived")
    require(record.get("outcome") == RV1, "Wrong RV outcome")
    require(record.get("plan_completeness") == "COMPLETE", "v2 plan not complete")

    authorization = record.get("authorization", {})
    require(bool(authorization) and all(value is False for value in authorization.values()), "Authorization flag is true")
    require(authorization.get("PHASE2C_AUTHORIZED") is False, "Phase2C authorized")
    execution = record.get("execution_state", {})
    require(execution.get("phase2b") == "NOT_EXECUTED", "Phase 2B execution occurred")
    for field in ("dis_numerical_physics_executed", "positivity_or_normalization_executed", "reference_closure_executed", "events_data_detector_or_neural_work"):
        require(execution.get(field) is False, f"Forbidden execution recorded: {field}")
    require(execution.get("generic_analytic_quadrature_tests_only") is True, "Generic-only test boundary changed")

    github = record.get("github_target_state", {})
    require(github == {"issue": 55, "state": "OPEN", "status": "Backlog", "gate_decision": "Not Evaluated", "authorization": "Not Authorized"}, "Issue #55 target state changed")
    require(bool(record.get("remaining_limitations")), "Scientific limitations hidden")
    require("new execution-authorization review" in record.get("next_action", ""), "Next action is not a new authorization review")
    require(not (root / "docs/reduced_nc_dis/sources/papers").exists(), "Publication bytes were committed")

    if check_docs:
        markers = {
            "docs/reduced_nc_dis/PHASE2B_PREAUTHORIZATION_VALIDATION_PLAN_V2.md": [RV1, "AS2_DUAL_PROVIDER_PREDECLARED_EQUIVALENCE_TEST", "NR2_ERROR_ENVELOPE_WITH_INCONCLUSIVE_BAND", "NOT_EXECUTED"],
            "docs/CURRENT_PHASE.md": [RV1, "Phase 2B remains Not Authorized"],
            "docs/reduced_nc_dis/README.md": ["preauthorization v2 successor", RV1],
            "docs/reduced_nc_dis/ROADMAP.md": [RV1, "Not Authorized"],
            "docs/adr/ADR-013-reduced-nc-dis-observation-law-contract.md": [RV1, "Historical Phase 2A remains `INCONCLUSIVE`"],
        }
        for relative_path, required in markers.items():
            text = (root / relative_path).read_text(encoding="utf-8")
            for marker in required:
                require(marker in text, f"Documentation marker missing from {relative_path}: {marker}")


def main() -> None:
    try:
        record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        validate(record)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise SystemExit(f"INVALID phase2b.preauthorization_validation_plan_v2: {error}") from error
    print("VALID phase2b.preauthorization_validation_plan_v2")


if __name__ == "__main__":
    main()
