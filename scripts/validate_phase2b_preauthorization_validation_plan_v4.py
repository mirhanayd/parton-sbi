#!/usr/bin/env python3
"""Validate the Phase 2B preauthorization validation plan V4 statically.

Fail-closed.  Where a serialized value is derivable it is recomputed here rather
than compared against a copied literal.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v4.json"
SCHEMA = "partonsbi.phase2b.preauthorization-validation-plan.v4"

OUTCOMES = {
    "V4_PREAUTH_PLAN_COMPLETE_READY_FOR_SEPARATE_EXECUTION_AUTHORIZATION_REVIEW",
    "V4_PREAUTH_PLAN_INCOMPLETE_BLOCKED",
    "V4_NEW_POLICY_CONTRADICTION_DISCOVERED",
}
EXPECTED_OUTCOME = "V4_PREAUTH_PLAN_COMPLETE_READY_FOR_SEPARATE_EXECUTION_AUTHORIZATION_REVIEW"
STARTING_MAIN_SHA = "4d2018a0873b9374559194221b6e6cf8b5bf7ac8"

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
    "preauthorization_v2": (
        "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v2.json",
        "a79e87538fae4d3f20793756b321af4d7521c1277ee08580e1b773a7452a9cd2",
    ),
    "execution_authorization_review_v2": (
        "docs/reduced_nc_dis/contracts/phase2b_execution_authorization_review_v2.json",
        "d7826158718ea0c4e5d3fc7c0f60829913e9634c98c45d2316c63bffdce47821",
    ),
    "preauthorization_v3": (
        "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v3.json",
        "78a029686489e9712e65ef6f9df3263b4821f96de0ee9873a910dee31f307e06",
    ),
    "blocker_resolution_v1": (
        "docs/reduced_nc_dis/contracts/phase2b_blocker_resolution_v1.json",
        "d66a1bbcb67b7105f489233bfd292c7064bcda35ef8c6f8dbc0dec41aa6da8de",
    ),
    "numerical_policy_decision_v1": (
        "docs/reduced_nc_dis/contracts/phase2b_numerical_policy_decision_v1.json",
        "a855dfeb49a4f6f8e26804c5fac8708691fa9c345be57acfc5efa55e1864830c",
    ),
    "fonll_validation_policy_v1": (
        "docs/reduced_nc_dis/contracts/phase2b_fonll_validation_policy_v1.json",
        "8210b926f1461938638f9ddcbb94c1003e52b4a5ec0bcd944d53e6b6bec8ce91",
    ),
}

INHERITED_POLICIES = {
    "alpha_policy": "AP1_APFEL_ALPHA_IS_AUTHORITATIVE_SIMULATOR_COUPLING",
    "normalization_policy": "NP2_REQUIRE_EMPIRICAL_NUMERICAL_STABILITY_NOT_CERTIFIED_ACCURACY",
    "fonll_validation_policy": "FPD3_ADOPT_HYBRID_COMPONENT_VALIDATION_POLICY",
    "completion_rule": "NO_UNDISCLOSED_LOAD_BEARING_VALIDATION_GAP",
    "sign_policy": "SIGN1_STRICT_IMPLEMENTED_RATE_NONNEGATIVITY",
}

REQUIRED_NON_EQUIVALENCES = [
    "PUBLISHED != EXECUTABLE",
    "BENCHMARKED != FULLY_VALIDATED",
    "COMPONENT_VALIDATION != END_TO_END_VALIDATION",
    "SELF_CONVERGENCE != INDEPENDENT_CORRECTNESS",
    "DISCLOSED_LIMITATION != PASS",
    "NO_DETECTED_DISCREPANCY != PROOF_OF_CORRECTNESS",
    "POSTERIOR_CALIBRATION != PHYSICS_IMPLEMENTATION_VALIDATION",
    "NUMERICAL_STABILITY != CERTIFIED_NUMERICAL_ACCURACY",
    "V4_COMPLETE != PHASE2B_AUTHORIZED",
    "PHASE2B_AUTHORIZED != PHASE2B_EXECUTED",
]

EVIDENCE_CLASSES = {
    "E1_EXECUTABLE_INDEPENDENT_ORACLE",
    "E2_PUBLISHED_INDEPENDENT_NUMERICAL_BENCHMARK",
    "E3_INDEPENDENT_ANALYTIC_CHECK",
    "E4_SEMANTIC_IMPLEMENTATION_CROSSCHECK",
    "E5_SOURCE_PROVENANCE_ONLY",
    "E6_INTERNAL_SELF_CONVERGENCE",
}
CLASS_TOKENS = {"E1", "E2", "E3", "E4", "E5", "E6"}

EXPECTED_COMPONENTS = {
    "COMPLETE_NC_OBSERVABLE",
    "ELECTROWEAK_ASSEMBLY",
    "MASSLESS_COEFFICIENT_CONTRIBUTION",
    "MASSIVE_CONTRIBUTION",
    "FONLL_MATCHING_DIFFERENCE_CONTRIBUTION",
    "PDF_PROVIDER",
    "PDF_TO_APFEL_BRIDGE",
    "ALPHA_S",
    "COORDINATE_AND_JACOBIAN",
    "POINT_GRID_COVERAGE",
    "QUADRATURE_A",
    "QUADRATURE_B",
    "NORMALIZATION_ASSEMBLY",
    "NORMALIZED_LAW_ASSEMBLY",
    "SUPPORT_AND_DOMAIN_HANDLING",
    "RAW_RATE_SIGN_CLASSIFICATION",
}
REQUIRED_ROW_FIELDS = (
    "component_id",
    "implementation_identity",
    "evidence_class",
    "reference_identity",
    "independent",
    "executable",
    "reference_available",
    "mandatory",
    "gating",
    "future_execution_status",
    "test_definition",
    "comparison_target",
    "pass_semantics",
    "fail_semantics",
    "inconclusive_semantics",
    "residual_risk",
    "allowed_claim",
    "prohibited_claim",
    "work_count_formula",
    "resource_category",
    "disclosure_required",
)

FORBIDDEN_TOLERANCE_TOKENS = ("0.000125", "0.0013")
#: Wording that would turn an empirical stability plan into a certification claim.
FORBIDDEN_CERTIFICATION_PHRASES = (
    "certified accuracy",
    "rigorously certified",
    "certified remainder",
    "remainder certificate is provided",
)
FORBIDDEN_MAY_CLAIM_TOKENS = (
    "independently validated",
    "independently reimplemented",
    "end-to-end independent",
    "certified",
    "proves",
    "production-precision",
)
MAY_CLAIM_ADMISSION_MARKERS = ("absence of", "is an explicit limitation", "is not claimed")

RESEARCH_QUESTION_KEYS = (
    "inference_unit_unchanged",
    "posterior_target_unchanged",
    "theta_domain_and_prior_unchanged",
    "observation_space_unchanged",
    "selected_event_conditioning_unchanged",
    "detector_kernel_unchanged",
    "normalized_law_form_unchanged",
)

ANCHORS = 9
POINT_LEVELS = (17, 33, 65)
GL_ORDERS = (16, 32, 64)
CC_COUNTS = (17, 33, 65)
BRIDGE_SLOTS = 14


class ValidationError(Exception):
    """Raised when the V4 plan is internally inconsistent."""


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_header(record: dict) -> None:
    require(record.get("schema_version") == SCHEMA, "Wrong schema version")
    require(
        record.get("record_type") == "PHASE2B_PREAUTHORIZATION_VALIDATION_PLAN_V4",
        "Wrong record type",
    )
    require(
        record.get("task_kind") == "PREAUTHORIZATION_PLANNING_ONLY",
        "Record is not declared planning-only",
    )
    require(
        record.get("not_an_execution_authorization_review") is True,
        "Record poses as an execution authorization review",
    )
    require(
        record.get("no_numerical_physics_executed") is True,
        "Record does not assert that no numerical physics was executed",
    )
    require(record.get("starting_main_sha") == STARTING_MAIN_SHA, "Starting main SHA changed")


def _validate_predecessors(record: dict, root: Path, check_files: bool) -> None:
    predecessors = record.get("predecessors", {})
    require(set(predecessors) == set(EXPECTED_PREDECESSORS), "Predecessor set changed")
    for key, (path, digest) in EXPECTED_PREDECESSORS.items():
        entry = predecessors[key]
        require(entry.get("path") == path, f"Predecessor path changed for {key}")
        require(entry.get("sha256") == digest, f"Predecessor hash changed for {key}")
        require(entry.get("bytes_immutable") is True, f"Predecessor {key} not marked immutable")
        if check_files:
            require(
                sha256_of(root / path) == digest,
                f"Historical artifact mutated on disk: {path}",
            )
    require(
        predecessors["fonll_validation_policy_v1"].get("historical_outcome")
        == "FPD3_ADOPT_HYBRID_COMPONENT_VALIDATION_POLICY",
        "FPD3 outcome rewritten",
    )
    require(
        predecessors["numerical_policy_decision_v1"].get("historical_outcome")
        == "PD1_ADOPT_AP1_AND_NP2",
        "Numerical policy outcome rewritten",
    )


def _validate_history_and_policies(record: dict) -> None:
    history = record.get("historical_state", {})
    require(history.get("phase2a_status") == "COMPLETE", "Phase 2A status changed")
    require(
        history.get("phase2a_scientific_decision") == "INCONCLUSIVE",
        "Phase 2A decision changed",
    )
    require(history.get("adr_013_status") == "Proposed", "ADR-013 status changed")
    require(
        history.get("accepted_pdf_family") == "ct18nlo_two_parameter_boundary_v2",
        "Accepted PDF family drifted",
    )
    require(
        history.get("heavy_flavor_contract") == "APFEL FONLL-A NLO",
        "FONLL-A contract drifted",
    )
    require(history.get("issue_54_unchanged") is True, "Issue #54 reinterpreted")
    require(history.get("issue_10_unchanged") is True, "Issue #10 touched")

    inherited = record.get("inherited_policies", {})
    for key, value in INHERITED_POLICIES.items():
        require(inherited.get(key) == value, f"Inherited policy {key} silently changed")
    require(
        inherited.get("policies_changed_by_v4") == [],
        "V4 silently created or changed a scientific policy",
    )

    preserved = record.get("preserved_non_equivalences", [])
    for statement in REQUIRED_NON_EQUIVALENCES:
        require(statement in preserved, f"Non-equivalence dropped: {statement}")

    contract = record.get("accepted_contract", {})
    require(contract.get("scheme") == "FONLL-A", "Scheme drifted")
    require(contract.get("perturbative_order") == "NLO", "Perturbative order drifted")
    require(contract.get("theta_anchor_count") == ANCHORS, "Anchor count drifted")


def _validate_evidence_taxonomy(record: dict) -> None:
    taxonomy = record.get("evidence_taxonomy", [])
    names = {entry.get("class") for entry in taxonomy}
    require(names == EVIDENCE_CLASSES, "Evidence taxonomy changed")
    for entry in taxonomy:
        require(entry.get("may_support"), f"{entry.get('class')} has no support statement")
        require(entry.get("cannot_establish"), f"{entry.get('class')} has no exclusion statement")

    lookup = {entry["class"]: entry for entry in taxonomy}
    e2 = " ".join(lookup["E2_PUBLISHED_INDEPENDENT_NUMERICAL_BENCHMARK"]["cannot_establish"]).lower()
    for needle, message in (
        ("frozen current build", "E2 no longer denies current-build correctness"),
        ("executable replication", "E2 no longer denies executable replication"),
        ("transferable tolerance", "E2 no longer denies a transferable tolerance"),
        ("end-to-end", "E2 no longer denies end-to-end validation"),
    ):
        require(needle in e2, message)
    e6 = " ".join(lookup["E6_INTERNAL_SELF_CONVERGENCE"]["cannot_establish"]).lower()
    for needle, message in (
        ("independent correctness", "E6 no longer denies independent correctness"),
        ("rigorous accuracy", "E6 no longer denies rigorous accuracy"),
        ("error bound", "E6 no longer denies a theorem-level bound"),
    ):
        require(needle in e6, message)
    e5 = " ".join(lookup["E5_SOURCE_PROVENANCE_ONLY"]["cannot_establish"]).lower()
    require("numerical correctness" in e5, "E5 no longer denies numerical correctness")

    forbidden = " ".join(record.get("evidence_promotion_forbidden", [])).lower()
    for needle, message in (
        ("e2 may not be recorded as e1", "E2 to E1 promotion is no longer forbidden"),
        ("e6 may not be recorded as independent correctness", "E6 promotion is no longer forbidden"),
        ("e5 may not be recorded as executable verification", "E5 promotion is no longer forbidden"),
        ("after results are observed", "post-result reclassification is no longer forbidden"),
    ):
        require(needle in forbidden, message)


def _validate_fpd3(record: dict) -> None:
    block = record.get("fpd3_binding", {})
    require(
        block.get("policy") == "FPD3_ADOPT_HYBRID_COMPONENT_VALIDATION_POLICY",
        "FPD3 binding changed",
    )
    require(
        block.get("post_result_reclassification_allowed") is False,
        "Post-result reclassification permitted",
    )
    require(
        block.get("executable_fonll_comparator_available") is False,
        "An executable FONLL comparator is claimed available",
    )
    require(
        block.get("executable_fonll_comparator_limitation"),
        "The executable FONLL limitation is not disclosed",
    )
    joined = " ".join(block.get("requirements_frozen_here", [])).lower()
    for needle, message in (
        ("mandatory and gating", "FPD3 no longer makes available checks gating"),
        ("frozen in this artifact before any execution", "FPD3 coverage matrix is not frozen here"),
        ("may not be reclassified", "FPD3 no longer forbids reclassification"),
    ):
        require(needle in joined, message)


def _validate_item1_stability(record: dict) -> None:
    item = record.get("authoring_item_1_np2_stability_protocol", {})
    require(item.get("status") == "FROZEN", "NP2 stability protocol not frozen")
    require(
        item.get("claim_type") == "EMPIRICAL_NUMERICAL_STABILITY_NOT_CERTIFIED_ACCURACY",
        "NP2 claim type changed",
    )
    require(
        item.get("invented_scalar_tolerance") is False,
        "A scalar tolerance was invented",
    )
    require(item.get("why_no_scalar_target"), "No provenance given for the absent scalar target")

    concepts = item.get("distinguished_concepts", {})
    for key in (
        "floating_point_reproducibility",
        "refinement_stability",
        "cross_family_numerical_stability",
        "implementation_comparison",
        "physics_correctness",
        "physical_or_theory_uncertainty",
        "normalized_law_stability",
    ):
        require(concepts.get(key), f"NP2 protocol does not distinguish {key}")

    frozen = item.get("frozen_before_execution", {})
    for key in (
        "statistic",
        "comparison_direction",
        "refinement_ladder",
        "arithmetic_noise_formulas",
        "within_family_criterion",
        "cross_family_criterion",
        "near_zero_behavior",
        "absolute_versus_relative_switching_rule",
        "anchor_aggregation",
        "acceptance_semantics",
        "failure_precedence",
        "work_limit",
        "no_retry_rule",
    ):
        require(frozen.get(key), f"NP2 protocol does not freeze {key}")

    ladder = frozen["refinement_ladder"]
    require(tuple(ladder.get("family_a_gauss_legendre_orders", ())) == GL_ORDERS, "Family A ladder changed")
    require(tuple(ladder.get("family_b_clenshaw_curtis_node_counts", ())) == CC_COUNTS, "Family B ladder changed")
    require(ladder.get("ladder_is_fixed") is True, "Refinement ladder is not fixed")
    require(ladder.get("adaptive_refinement_allowed") is False, "Adaptive refinement permitted")

    semantics = frozen["acceptance_semantics"]
    for key in ("PASS", "FAIL", "INCONCLUSIVE"):
        require(semantics.get(key), f"NP2 acceptance semantics missing {key}")
    require("never PASS" in semantics["INCONCLUSIVE"], "INCONCLUSIVE may become PASS")

    principles = item.get("required_principles_asserted", {})
    for key in (
        "families_independently_implemented",
        "every_theta_anchor_evaluated",
        "no_anchor_dropped",
        "no_averaging_over_a_failed_anchor",
        "no_post_hoc_tolerance_choice",
        "no_retry_until_pass",
        "no_point_deletion",
        "no_adaptive_refinement_beyond_frozen_ladder",
        "finite_normalization_required",
        "strictly_positive_normalization_required",
        "cross_family_disagreement_is_fail",
        "agreement_necessary_but_not_sufficient",
        "unstable_refinement_cannot_become_pass",
        "empirical_stability_is_not_a_remainder_certificate",
    ):
        require(principles.get(key) is True, f"NP2 principle {key} not asserted")

    forbidden = " ".join(item.get("forbidden_imports", []))
    require("0.001" in forbidden, "The MassiveDIS level is no longer a forbidden import")
    require("1e-5" in forbidden, "The massless level is no longer a forbidden import")


def _validate_item2_grid(record: dict) -> None:
    item = record.get("authoring_item_2_grid_gate", {})
    require(item.get("status") == "FROZEN", "Grid gate not frozen")
    require(item.get("gate_id") == "EXACT_COVERAGE_AND_NESTING_AUDIT", "Grid gate id changed")

    grid = item.get("point_grid", {})
    require(tuple(grid.get("levels", ())) == POINT_LEVELS, "Point-grid levels changed")
    require(grid.get("nesting_status") == "NESTED_BITWISE", "Point-grid nesting claim changed")
    require(grid.get("per_level_work_formula") == "N^2 + 13*N", "Point-grid work formula changed")
    require(grid.get("support_mask_rule"), "Point-grid support mask missing")
    require(grid.get("threshold_probes"), "Point-grid threshold probes missing")
    require(grid.get("deterministic_ordering"), "Point-grid ordering not deterministic")

    cc = item.get("clenshaw_curtis", {})
    require(tuple(cc.get("node_counts", ())) == CC_COUNTS, "Clenshaw-Curtis counts changed")
    require(cc.get("nesting_status") == "NESTED_BITWISE", "Clenshaw-Curtis nesting claim changed")

    gl = item.get("gauss_legendre", {})
    require(tuple(gl.get("orders", ())) == GL_ORDERS, "Gauss-Legendre orders changed")
    require(
        gl.get("nesting_status") == "NOT_NESTED",
        "Gauss-Legendre levels mislabelled as nested",
    )
    require(gl.get("mislabelling_forbidden") is True, "Gauss-Legendre mislabelling permitted")

    prohibitions = item.get("prohibitions", {})
    require(prohibitions.get("adaptive_insertion_allowed") is False, "Adaptive insertion permitted")
    require(prohibitions.get("post_hoc_deletion_allowed") is False, "Post-hoc deletion permitted")
    require(prohibitions.get("reordering_allowed") is False, "Reordering permitted")

    counterexample = item.get("structural_counterexample_required", {})
    require(counterexample.get("requirement"), "The false-convergence counterexample is not required")
    require(
        counterexample.get("is_dis_physics") is False,
        "The counterexample is described as DIS physics",
    )


def _validate_item3_massless(record: dict) -> None:
    item = record.get("authoring_item_3_massless_reference", {})
    require(
        item.get("status") == "FROZEN_WITH_DECLARED_UNBOUND_ITEMS",
        "Massless reference status changed",
    )
    bound = item.get("reference_side_bound", {})
    for key in (
        "perturbative_order",
        "initial_scale_gev",
        "alpha_s_at_q0",
        "active_flavours_at_q0",
        "thresholds_gev_in_released_code",
        "scales",
        "weak_mixing",
        "observables",
        "coordinates",
    ):
        require(bound.get(key) is not None, f"Massless reference does not bind {key}")
    require(bound.get("active_flavours_at_q0") == 3, "Massless initial active-flavour count changed")
    require(bound.get("published_scalar_tokens") == 27 * 3, "Published token count inconsistent")

    discrepancy = item.get("prose_versus_code_discrepancy_carried_forward", {})
    require(
        discrepancy.get("released_code_literal") == 1.414213563,
        "The released-code charm literal changed",
    )
    require(
        "executable literal is binding" in discrepancy.get("binding_rule", ""),
        "The executable literal is no longer binding",
    )

    candidate = item.get("candidate_side", {})
    require(candidate.get("grid_settings_locator"), "Candidate grid settings have no source locator")
    require(candidate.get("grid_settings_values"), "Candidate grid settings values missing")
    require(
        "not call" in candidate.get("grid_settings_binding_rule", ""),
        "The default-grid binding rule no longer forbids overriding the defaults",
    )

    require(item.get("declared_unbound_items"), "No unbound items are declared")
    rule = item.get("comparison_rule", {})
    require(rule.get("tolerance_invented") is False, "A massless tolerance was invented")
    require("displayed digits" in rule.get("rule", ""), "Massless rule is not displayed-digit containment")
    require(rule.get("provenance"), "Massless rule has no provenance")
    require(item.get("evidence_class") == "E2", "Massless evidence class changed")
    require(item.get("gating") is True, "The available massless check is not gating")
    require(item.get("residual_risk"), "Massless residual risk missing")


def _validate_item4_bridge(record: dict) -> None:
    item = record.get("authoring_item_4_bridge", {})
    require(item.get("status") == "FROZEN", "Bridge not frozen")
    profiles = {p.get("profile_id") for p in item.get("profiles", [])}
    require(
        profiles
        == {"BRIDGE_PROFILE_A_CT18_BOUNDARY", "BRIDGE_PROFILE_B_MASSLESS_REFERENCE_BOUNDARY"},
        "Bridge profile set changed",
    )
    semantics = item.get("shared_semantics", {})
    require(
        semantics.get("exactly_one_multiplication_policy") is True,
        "The exactly-one-multiplication policy was dropped",
    )
    for key in (
        "extrapolation_allowed",
        "support_repair_allowed",
        "double_multiplication_allowed",
        "implicit_flavor_remap_allowed",
        "silent_zero_replacement_allowed",
    ):
        require(semantics.get(key) is False, f"Bridge permits {key}")
    for key in (
        "f_versus_xf",
        "q_versus_q2_convention",
        "q0_behaviour",
        "threshold_behaviour",
        "signed_zero_behaviour",
        "exact_zero_slots",
        "subnormal_semantics",
    ):
        require(semantics.get(key), f"Bridge does not freeze {key}")
    require(len(item.get("invariants", [])) == 8, "Bridge invariant set changed")

    cap = item.get("work_cap", {})
    a = item.get("profile_a_inventory", {})
    b = item.get("profile_b_inventory", {})
    expected_attempts = a.get("callback_attempts", 0) + b.get("callback_attempts", 0)
    expected_invocations = a.get("evaluator_invocations", 0) + b.get("evaluator_invocations", 0)
    require(
        cap.get("callback_attempts_total") == expected_attempts,
        "Bridge callback-attempt cap does not equal the profile sum",
    )
    require(
        cap.get("evaluator_invocations_total") == expected_invocations,
        "Bridge evaluator-invocation cap does not equal the profile sum",
    )
    require(
        cap.get("slot_comparisons_total") == expected_invocations * BRIDGE_SLOTS,
        "Bridge slot-comparison cap is not invocations times slots",
    )
    require(
        a.get("real_callbacks") == ANCHORS * sum(POINT_LEVELS),
        "Profile A real-callback count does not match 9*(17+33+65)",
    )
    require(item.get("executed_in_this_task") is False, "Bridge validation claimed executed")


def _validate_item5_alpha(record: dict) -> None:
    item = record.get("authoring_item_5_alpha_diagnostic", {})
    require(item.get("status") == "FROZEN", "Alpha diagnostic not frozen")
    require(
        item.get("policy") == "AP1_APFEL_ALPHA_IS_AUTHORITATIVE_SIMULATOR_COUPLING",
        "Alpha policy changed",
    )
    require(item.get("gating") == "NON_GATING", "Alpha diagnostic is not marked non-gating")
    require(item.get("gating_is_false") is True, "Alpha diagnostic gating flag inconsistent")
    require(
        "provenance" in item.get("ct18_alpha_role", "").lower(),
        "CT18 alpha is no longer provenance evidence",
    )
    items = {entry.get("item"): entry.get("status") for entry in item.get("declared_convention_compatibility_items", [])}
    require(len(items) == 6, "Compatibility item inventory changed")
    require(
        items.get("perturbative order of the coupling running itself")
        == "UNRESOLVED_COMPATIBILITY_ITEM",
        "The unresolved running-order item was silently resolved",
    )
    require(item.get("material_mismatch_triggers_review") is True, "Review trigger removed")

    nodes = item.get("node_generation", {})
    require(nodes.get("distinct_nodes") == 25, "Alpha diagnostic node count changed")
    require(nodes.get("rule"), "Alpha diagnostic node rule missing")
    require(
        item.get("provider_evaluations") == 2 * nodes.get("distinct_nodes", 0),
        "Alpha provider evaluations are not two per node",
    )
    forbidden = " ".join(item.get("must_not_establish", [])).lower()
    for needle, message in (
        ("continuous-domain equivalence", "Alpha diagnostic may claim continuum equivalence"),
        ("bitwise identity", "Alpha diagnostic may claim bitwise identity"),
        ("phase 2b authorization", "Alpha diagnostic may imply authorization"),
    ):
        require(needle in forbidden, message)
    require(item.get("executed_in_this_task") is False, "Alpha diagnostic claimed executed")


def _validate_item6_runtime(record: dict) -> None:
    item = record.get("authoring_item_6_runtime_identity", {})
    require(
        item.get("status") == "FROZEN_WITH_EXPLICIT_CLASSIFICATIONS",
        "Runtime identity status changed",
    )
    require(item.get("bitwise_cross_host_claim") is False, "A cross-host bitwise claim was made")
    require(
        item.get("libm_certification_resurrected_as_gate") is False,
        "libm certification was resurrected as a gate",
    )
    require(
        item.get("source_hash_is_not_executable_verification") is True,
        "A source hash is treated as executable verification",
    )

    deps = item.get("dependencies", [])
    require(len(deps) >= 12, "Runtime dependency inventory is incomplete")
    names = {d.get("name") for d in deps}
    for required_name in ("CPython", "NumPy", "SciPy", "APFEL", "LHAPDF", "glibc", "libm"):
        require(required_name in names, f"Runtime inventory omits {required_name}")
    for dep in deps:
        for key in (
            "source_identified",
            "hash_pinned",
            "installed",
            "executable_in_current_environment",
            "required_for_phase2b_execution",
        ):
            require(key in dep, f"Dependency {dep.get('name')} lacks classification {key}")
        if dep.get("executable_in_current_environment") is True:
            require(
                dep.get("installed") is True,
                f"Dependency {dep.get('name')} is executable but not installed",
            )
    lookup = {d["name"]: d for d in deps}
    for pinned in ("CPython", "NumPy", "SciPy"):
        require(lookup[pinned].get("hash_pinned") is True, f"{pinned} is not hash pinned")

    must_install = set(item.get("must_be_installed_before_execution", []))
    derived = {
        d["name"]
        for d in deps
        if d.get("required_for_phase2b_execution") and not d.get("installed")
    }
    require(
        {name.split()[0] for name in must_install} == derived,
        "The must-install list does not match the required-but-not-installed dependencies",
    )

    cpu = item.get("cpu_feature_dependency", {})
    require(
        cpu.get("is_a_scientific_dependency") is False,
        "CPU microarchitecture was made a scientific dependency",
    )
    require(cpu.get("reason"), "CPU dependency classification has no reason")


def _validate_item7_resources(record: dict) -> None:
    item = record.get("authoring_item_7_resource_model", {})
    require(item.get("status") == "FROZEN", "Resource model not frozen")
    require(item.get("recount_from_first_principles") is True, "Resources were not recounted")
    require(item.get("copied_from_previous_totals") is False, "Resources were copied")
    require(item.get("retry_budget") == 0, "A retry budget exists")
    require(item.get("retry_until_pass_allowed") is False, "Retry-until-pass permitted")
    require(item.get("resource_exhaustion_result") == "INCONCLUSIVE", "Exhaustion may pass")

    units = item.get("unit_definitions", {})
    require(units.get("complete_rate_evaluation"), "The complete-rate evaluation unit is undefined")

    categories = item.get("categories", [])
    names = [c.get("category") for c in categories]
    require(len(names) == len(set(names)), "Duplicate resource category")
    for entry in categories:
        for key in ("unit", "formula", "minimum", "nominal", "worst_case", "cap"):
            require(entry.get(key) is not None, f"Resource {entry.get('category')} lacks {key}")
        require(
            entry["unit"] in units,
            f"Resource {entry['category']} uses an undefined unit {entry['unit']}",
        )
        require(
            entry["minimum"] <= entry["nominal"] <= entry["worst_case"] <= entry["cap"],
            f"Resource {entry['category']} bounds are not ordered",
        )

    lookup = {c["category"]: c for c in categories}

    # Recompute rather than trust the serialized values.
    point_grid = ANCHORS * sum(n * n + 13 * n for n in POINT_LEVELS)
    require(
        lookup["point_grid_complete_rate_evaluations"]["cap"] == point_grid,
        f"Point-grid cap should be {point_grid}",
    )
    qa = ANCHORS * sum(n * n for n in GL_ORDERS)
    require(lookup["quadrature_a_integrand_evaluations"]["cap"] == qa, f"Quadrature A cap should be {qa}")
    qb = ANCHORS * sum(n * n for n in CC_COUNTS)
    require(lookup["quadrature_b_integrand_evaluations"]["cap"] == qb, f"Quadrature B cap should be {qb}")
    require(lookup["massless_reference_candidate_evaluations"]["cap"] == 27 * 3, "Massless cap should be 81")
    require(lookup["published_record_comparisons"]["cap"] == 27 * 3, "Published comparison cap should be 81")
    require(lookup["analytic_ew_jacobian_cases"]["cap"] == ANCHORS * 24, "Analytic case cap should be 216")

    bridge = record["authoring_item_4_bridge"]["work_cap"]
    require(
        lookup["bridge_callback_attempts"]["cap"] == bridge["callback_attempts_total"],
        "Bridge attempt cap disagrees with the bridge work cap",
    )
    require(
        lookup["bridge_evaluator_invocations"]["cap"] == bridge["evaluator_invocations_total"],
        "Bridge invocation cap disagrees with the bridge work cap",
    )
    require(
        lookup["bridge_slot_comparisons"]["cap"] == bridge["slot_comparisons_total"],
        "Bridge slot cap disagrees with the bridge work cap",
    )
    require(
        lookup["alpha_diagnostic_provider_evaluations"]["cap"]
        == record["authoring_item_5_alpha_diagnostic"]["provider_evaluations"],
        "Alpha resource cap disagrees with the diagnostic inventory",
    )

    aggregates = item.get("additive_aggregates", [])
    require(len(aggregates) == 1, "There must be exactly one additive aggregate")
    aggregate = aggregates[0]
    require(aggregate.get("unit_is_common") is True, "The aggregate does not declare a common unit")
    require(aggregate.get("definition_of_one_evaluation"), "The aggregate does not define one evaluation")
    member_units = {lookup[m]["unit"] for m in aggregate["members"]}
    require(len(member_units) == 1, "The aggregate mixes units")
    require(
        aggregate["unit"] in member_units,
        "The aggregate unit does not match its members",
    )
    recomputed = sum(lookup[m]["cap"] for m in aggregate["members"])
    require(
        aggregate["value"] == recomputed,
        f"Aggregate value should be {recomputed}",
    )
    require(item.get("forbidden_aggregate"), "The no-cross-unit-sum rule was removed")


def _validate_coverage_matrix(record: dict) -> None:
    matrix = record.get("component_coverage_matrix", [])
    ids = [row.get("component_id") for row in matrix]
    require(set(ids) == EXPECTED_COMPONENTS, "Coverage matrix component set changed")
    require(len(ids) == len(set(ids)), "Duplicate coverage-matrix row")

    rules = record.get("coverage_matrix_rules", {})
    exceptions = set(rules.get("policy_designated_non_gating", []))
    require(
        rules.get("post_result_reclassification_forbidden") is True,
        "Coverage matrix permits post-result reclassification",
    )
    if exceptions:
        require(
            rules.get("policy_designated_non_gating_authority"),
            "A non-gating exception exists with no policy authority",
        )

    for row in matrix:
        component = row["component_id"]
        for field in REQUIRED_ROW_FIELDS:
            require(field in row, f"Row {component} lacks required field {field}")
        require(row["evidence_class"] in CLASS_TOKENS, f"Row {component} has an unknown evidence class")
        require(row["residual_risk"], f"Row {component} has no residual-risk statement")
        require(row["allowed_claim"], f"Row {component} has no allowed claim")
        require(row["prohibited_claim"], f"Row {component} has no prohibited claim")
        require(
            row["future_execution_status"] == "NOT_EXECUTED",
            f"Row {component} is not marked NOT_EXECUTED",
        )
        if row["gating"]:
            require(
                row["reference_available"] is True,
                f"Row {component} is gating without an available reference",
            )
            for key in ("pass_semantics", "fail_semantics", "inconclusive_semantics"):
                require(row.get(key), f"Gating row {component} lacks {key}")
        if row["reference_available"] is False:
            require(row["gating"] is False, f"Row {component} gates on an unavailable reference")
        if row["mandatory"] and row["reference_available"] and component not in exceptions:
            require(row["gating"] is True, f"Row {component} has an available mandatory check but is not gating")
        if row["evidence_class"] in {"E2", "E5", "E6"}:
            require(
                row["disclosure_required"] is True,
                f"Row {component} lacks executable independent evidence but requires no disclosure",
            )

    complete = next(row for row in matrix if row["component_id"] == "COMPLETE_NC_OBSERVABLE")
    require(complete["evidence_class"] != "E1", "The complete observable is marked E1")
    require(complete["independent"] is False, "The complete observable is marked independent")
    require(complete["disclosure_required"] is True, "The complete observable requires no disclosure")
    require(
        "independently validated" in complete["prohibited_claim"].lower()
        or "end to end" in complete["prohibited_claim"].lower(),
        "The complete observable does not forbid an end-to-end claim",
    )

    for component in ("MASSIVE_CONTRIBUTION", "FONLL_MATCHING_DIFFERENCE_CONTRIBUTION"):
        row = next(r for r in matrix if r["component_id"] == component)
        require(row["evidence_class"] == "E2", f"{component} is no longer published evidence")
        require(row["executable"] is False, f"{component} is marked executable")
        require(row["disclosure_required"] is True, f"{component} requires no disclosure")

    alpha = next(row for row in matrix if row["component_id"] == "ALPHA_S")
    require(alpha["gating"] is False, "The alpha diagnostic became gating")
    require("ALPHA_S" in exceptions, "The alpha non-gating row is not a declared policy exception")


def _validate_sign_and_normalization(record: dict) -> None:
    sign = record.get("raw_rate_sign_policy", {})
    require(
        sign.get("policy") == "SIGN1_STRICT_IMPLEMENTED_RATE_NONNEGATIVITY",
        "Sign policy changed",
    )
    require(sign.get("finite_negative") == "FAIL", "A negative raw rate no longer fails")
    require(sign.get("nonfinite") == "FAIL", "A nonfinite raw rate no longer fails")
    forbidden = " ".join(sign.get("forbidden_operations", [])).lower()
    for needle, message in (
        ("clipping", "Clipping is no longer forbidden"),
        ("abs(rate)", "abs(rate) is no longer forbidden"),
        ("max(rate,0)", "max(rate,0) is no longer forbidden"),
        ("epsilon replacement", "Epsilon replacement is no longer forbidden"),
        ("point removal", "Point removal is no longer forbidden"),
        ("support shrinkage", "Support shrinkage is no longer forbidden"),
    ):
        require(needle in forbidden, message)
    require(sign.get("continuum_positivity_claimed") is False, "Continuum positivity claimed")
    require(sign.get("all_orders_positivity_claimed") is False, "All-orders positivity claimed")
    require(sign.get("executed_in_this_task") is False, "A positivity scan was executed")

    norm = record.get("normalization_policy", {})
    require(
        norm.get("policy") == "NP2_REQUIRE_EMPIRICAL_NUMERICAL_STABILITY_NOT_CERTIFIED_ACCURACY",
        "Normalization policy changed",
    )
    for key in (
        "finite_required",
        "strictly_positive_required",
        "two_independent_families",
        "refinement_levels_frozen",
        "anchor_set_frozen",
        "residual_risk_disclosed",
    ):
        require(norm.get(key) is True, f"Normalization policy dropped {key}")
    require(norm.get("post_hoc_target_change_allowed") is False, "Post-hoc target change permitted")
    require(norm.get("adaptive_retry_allowed") is False, "Adaptive retry permitted")
    require(norm.get("certified_remainder_provided") is False, "A certified remainder is claimed")


def _validate_paper_boundary(record: dict) -> None:
    paper = record.get("paper_claim_boundary", {})
    may = paper.get("may_claim", [])
    must_not = paper.get("must_not_claim", [])
    require(may, "Paper boundary lists nothing the paper may claim")
    require(must_not, "Paper boundary lists nothing the paper must not claim")

    for statement in may:
        lowered = statement.lower()
        if any(marker in lowered for marker in MAY_CLAIM_ADMISSION_MARKERS):
            continue
        for token in FORBIDDEN_MAY_CLAIM_TOKENS:
            require(
                token not in lowered,
                f"Permitted paper claim smuggles in a forbidden assertion: {statement}",
            )

    joined = " ".join(must_not).lower()
    for needle, message in (
        ("independent executable full fonll-a closure", "Executable closure is no longer forbidden"),
        ("published benchmark", "The published-benchmark inference is no longer forbidden"),
        ("production-precision", "Production-precision validation is no longer forbidden"),
        ("end-to-end independent", "End-to-end independent closure is no longer forbidden"),
        ("rigorous normalization accuracy", "Rigorous normalization accuracy is no longer forbidden"),
        ("continuum alpha-provider equivalence", "Continuum coupling equivalence is no longer forbidden"),
        ("continuum rate positivity", "Continuum positivity is no longer forbidden"),
        ("posterior calibration proves physics", "Calibration-as-physics is no longer forbidden"),
    ):
        require(needle in joined, message)
    require(paper.get("mandatory_limitation"), "The mandatory paper limitation was removed")


def _validate_outcome_and_state(record: dict, root: Path, expected_outcome: str | None) -> None:
    invariants = record.get("research_question_invariants", {})
    for key in RESEARCH_QUESTION_KEYS:
        require(invariants.get(key) is True, f"Research-question invariant {key} not preserved")

    outcome = record.get("outcome", {})
    code = outcome.get("code")
    require(code in OUTCOMES, "Unknown V4 outcome")
    require(outcome.get("derivation"), "Outcome has no derivation")
    require(outcome.get("new_policy_created") is False, "V4 created new scientific policy")

    dispositions = outcome.get("seven_authoring_items_disposition", {})
    require(len(dispositions) == 7, "There must be exactly seven authoring-item dispositions")
    if code == EXPECTED_OUTCOME:
        require(
            all(value.startswith("FROZEN") for value in dispositions.values()),
            "A complete V4 has an unfrozen authoring item",
        )
        require(
            outcome.get("new_policy_contradiction_discovered") is False,
            "A complete V4 also reports a policy contradiction",
        )
        for statement in outcome.get("does_not_mean", []):
            require(statement, "An empty does-not-mean entry")
        joined = " ".join(outcome.get("does_not_mean", [])).lower()
        require("phase 2b authorized" in joined, "V4 does not deny that it authorizes Phase 2B")
        require("phase 2b executed" in joined, "V4 does not deny that it executes Phase 2B")

    authorization = record.get("authorization", {})
    require(authorization, "Authorization block removed")
    require(all(value is False for value in authorization.values()), "An authorization flag is true")
    for key in (
        "PHASE2B_AUTHORIZED",
        "PHASE2B_EXECUTED",
        "PHASE2C_AUTHORIZED",
        "APFEL_EXECUTION_AUTHORIZED",
        "APFELXX_EXECUTION_AUTHORIZED",
        "MASSIVEDIS_EXECUTION_AUTHORIZED",
        "POSITIVITY_SCAN_AUTHORIZED",
        "NORMALIZATION_EXECUTION_AUTHORIZED",
        "D2_AUTHORIZED",
    ):
        require(key in authorization, f"Authorization matrix omits {key}")

    execution = record.get("execution_state", {})
    require(execution.get("phase2b") == "NOT_EXECUTED", "Phase 2B execution occurred")
    require(
        all(value is False for key, value in execution.items() if key != "phase2b"),
        "Forbidden physics or downstream execution recorded",
    )
    for key in ("apfel_executed", "apfelxx_executed", "massivedis_executed", "fonll_benchmark_executed"):
        require(key in execution, f"Execution matrix omits {key}")

    require(
        record.get("github_target_state")
        == {
            "issue": 55,
            "state": "OPEN",
            "status": "Backlog",
            "gate_decision": "Not Evaluated",
            "authorization": "Not Authorized",
        },
        "Issue #55 target state changed",
    )
    require(
        record.get("next_action") == "SEPARATE_INDEPENDENT_PHASE2B_EXECUTION_AUTHORIZATION_REVIEW",
        "The next action is not a separate authorization review",
    )
    require(record.get("remaining_scientific_limitations"), "Scientific limitations removed")

    serialized = json.dumps(record).lower()
    for token in FORBIDDEN_TOLERANCE_TOKENS:
        require(token not in serialized, f"Rejected tolerance {token} reintroduced")

    # Certification wording is scanned only on surfaces that make a positive
    # claim.  Prohibitions and policy names legitimately contain the same words.
    positive_surfaces = list(record.get("paper_claim_boundary", {}).get("may_claim", []))
    positive_surfaces += list(record.get("outcome", {}).get("means", []))
    positive_surfaces += [
        row.get("allowed_claim", "") for row in record.get("component_coverage_matrix", [])
    ]
    for statement in positive_surfaces:
        lowered = statement.lower()
        for phrase in FORBIDDEN_CERTIFICATION_PHRASES:
            require(
                phrase not in lowered,
                f"Certification wording reintroduced in a positive claim: {statement}",
            )
    require(
        len(record.get("failure_precedence", [])) >= 8,
        "Failure precedence is incomplete",
    )

    if expected_outcome is not None:
        require(code == expected_outcome, "Wrong V4 outcome")


def validate(
    record: dict,
    *,
    root: Path = ROOT,
    check_docs: bool = True,
    check_files: bool = True,
    expected_outcome: str | None = EXPECTED_OUTCOME,
) -> None:
    _validate_header(record)
    _validate_history_and_policies(record)
    _validate_predecessors(record, root, check_files)
    _validate_evidence_taxonomy(record)
    _validate_fpd3(record)
    _validate_item1_stability(record)
    _validate_item2_grid(record)
    _validate_item3_massless(record)
    _validate_item4_bridge(record)
    _validate_item5_alpha(record)
    _validate_item6_runtime(record)
    _validate_item7_resources(record)
    _validate_coverage_matrix(record)
    _validate_sign_and_normalization(record)
    _validate_paper_boundary(record)
    _validate_outcome_and_state(record, root, expected_outcome)

    if check_docs:
        markers = {
            "docs/reduced_nc_dis/PHASE2B_PREAUTHORIZATION_VALIDATION_PLAN_V4.md": [
                EXPECTED_OUTCOME,
                "NOT_EXECUTED",
                "SEPARATE_INDEPENDENT_PHASE2B_EXECUTION_AUTHORIZATION_REVIEW",
                "NOT_NESTED",
            ],
            "docs/CURRENT_PHASE.md": [EXPECTED_OUTCOME, "Phase 2B remains Not Authorized"],
            "docs/reduced_nc_dis/README.md": [EXPECTED_OUTCOME, "Not Authorized"],
            "docs/adr/ADR-013-reduced-nc-dis-observation-law-contract.md": [
                EXPECTED_OUTCOME,
                "Historical Phase 2A remains `INCONCLUSIVE`",
            ],
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
        raise SystemExit(f"INVALID phase2b.preauthorization_validation_plan_v4: {error}") from error
    print("VALID phase2b.preauthorization_validation_plan_v4")


if __name__ == "__main__":
    main()
