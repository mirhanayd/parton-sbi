"""Adversarial tests for the Phase 2B preauthorization blocker-resolution record."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_phase2b_blocker_resolution.py"
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_blocker_resolution_v1.json"

SPEC = importlib.util.spec_from_file_location("phase2b_blocker_resolution_validator", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


@pytest.fixture
def record():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def rejected(candidate, expected_message):
    with pytest.raises(VALIDATOR.ValidationError, match=expected_message):
        VALIDATOR.validate(candidate, root=ROOT, check_docs=False, check_files=False)


def node(candidate, test_id):
    for item in candidate["blocker_dependency_graph"]["nodes"]:
        if item["test_id"] == test_id:
            return item
    raise AssertionError(f"missing node {test_id}")


# --------------------------------------------------------------------------
# baseline
# --------------------------------------------------------------------------


def test_cli_validates_current_artifact():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "VALID phase2b.blocker_resolution_v1" in result.stdout


def test_current_record_is_br5(record):
    assert record["outcome"]["code"] == "BR5_MULTIPLE_BLOCKERS_REMAIN"
    assert record["outcome"]["v4_created"] is False
    assert record["outcome"]["new_authorization_review_warranted"] is False


def test_this_record_did_not_create_v4(record):
    """This task must not have created V4.

    A later, separately reviewed successor may legitimately create one, so the
    assertion is on this record's own outcome rather than on the permanent
    absence of the file.  When a V4 exists it must bind this record.
    """

    assert record["outcome"]["v4_created"] is False
    v4_path = ROOT / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v4.json"
    if v4_path.exists():
        v4 = json.loads(v4_path.read_text(encoding="utf-8"))
        assert (
            v4["predecessors"]["blocker_resolution_v1"]["sha256"]
            == VALIDATOR.sha256_of(ARTIFACT)
        )


def test_record_declares_itself_a_blocker_resolution(record):
    assert record["task_kind"] == "BLOCKER_RESOLUTION_ONLY"
    assert record["not_an_execution_authorization_review"] is True


# --------------------------------------------------------------------------
# adversarial: fabricated rigor
# --------------------------------------------------------------------------


def test_fake_interval_backend_rejected(record):
    candidate = copy.deepcopy(record)
    backend = candidate["workstream_a_alpha"]["a3_interval_backend"]["selected"]
    backend["transcendental_backend"]["identity"] = "homemade-interval-shim 1.0"
    rejected(candidate, "Bound backend is not the declared rigorous one")


def test_backend_without_wheel_identity_rejected(record):
    candidate = copy.deepcopy(record)
    backend = candidate["workstream_a_alpha"]["a3_interval_backend"]["selected"]
    backend["transcendental_backend"]["cp310_wheel_sha256"] = ""
    rejected(candidate, "Bound backend has no wheel identity")


def test_high_precision_mislabelled_as_rigorous_rejected(record):
    candidate = copy.deepcopy(record)
    backend = candidate["workstream_a_alpha"]["a3_interval_backend"]
    backend["selected"]["transcendental_backend"]["identity"] = "mpmath 1.3.0 high precision"
    backend["evaluated_and_rejected"] = []
    rejected(candidate, "Bound backend is not the declared rigorous one")


def test_dropping_the_mpmath_rejection_is_caught(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_a_alpha"]["a3_interval_backend"]["evaluated_and_rejected"] = [
        {"candidate": "something else", "reason": "n/a"}
    ]
    rejected(candidate, "mpmath is no longer explicitly rejected")


def test_sampled_points_mislabelled_as_continuous_proof_rejected(record):
    candidate = copy.deepcopy(record)
    finding = candidate["workstream_a_alpha"]["a5_apfel_continuous_enclosure"]["method_finding"]
    del finding["what_it_does_not_claim"]
    rejected(
        candidate,
        "The recursion-versus-differential-equation distinction was dropped",
    )


def test_alpha_evidence_claiming_physics_execution_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_a_alpha"]["a5_apfel_continuous_enclosure"]["evidence"][
        "physics_executed"
    ] = True
    rejected(candidate, "Alpha evidence claims physics execution")


# --------------------------------------------------------------------------
# adversarial: exact provider semantics
# --------------------------------------------------------------------------


def test_missing_four_pi_conversion_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_a_alpha"]["a2_apfel_exact_mathematics"]["four_pi_conclusion"][
        "resolved"
    ] = False
    rejected(candidate, "The 4\\*pi convention is not resolved")


def test_wrong_pi_constant_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_a_alpha"]["a2_apfel_exact_mathematics"]["four_pi_conclusion"][
        "pi_binary64_hex"
    ] = "400921fb54442d19"
    rejected(candidate, "APFEL pi constant identity changed")


def test_truncated_sixth_literal_collapsed_onto_exact_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_a_alpha"]["a2_apfel_exact_mathematics"]["rk4"]["sixth_literal"][
        "binary64_hex"
    ] = "3fc5555555555555"
    rejected(candidate, "Truncated one-sixth literal identity changed")


def test_unfrozen_threshold_semantics_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_a_alpha"]["a2_apfel_exact_mathematics"]["threshold_semantics"][
        "asymmetry_is_real"
    ] = False
    rejected(candidate, "Threshold equality asymmetry erased")


def test_erasing_the_threshold_comparison_direction_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_a_alpha"]["a2_apfel_exact_mathematics"]["threshold_semantics"][
        "initial_flavour_selection"
    ] = "nfi advances at the threshold"
    rejected(candidate, "Initial flavour threshold comparison lost")


def test_dropping_the_discontinuous_clamp_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_a_alpha"]["a1_ct18_exact_representation"]["discontinuous_clamp"][
        "expression"
    ] = "p0 + m0 + p1 + m1"
    rejected(candidate, "Discontinuous clamp expression missing")


def test_ct18_partition_arithmetic_must_be_consistent(record):
    candidate = copy.deepcopy(record)
    partition = candidate["workstream_a_alpha"]["a1_ct18_exact_representation"][
        "domain_partition_verified"
    ]
    partition["intervals_above_mb"] = 15
    rejected(candidate, "Root interval arithmetic inconsistent")


# --------------------------------------------------------------------------
# adversarial: references
# --------------------------------------------------------------------------


def test_invented_fonll_benchmark_coordinates_rejected(record):
    candidate = copy.deepcopy(record)
    massivedis = candidate["workstream_b_references"]["b1_massivedis_executable_provenance"]
    massivedis["published_configuration_reconstructable"] = True
    rejected(
        candidate,
        "Reference is blocked yet the configuration is claimed reconstructable",
    )


def test_apfel_wrapper_mislabelled_independent_rejected(record):
    candidate = copy.deepcopy(record)
    for item in candidate["workstream_b_references"]["b2_alternative_independent_comparator"][
        "candidates"
    ]:
        if item["name"] == "APFEL++":
            item["assessment"] = "BOUND"
    rejected(candidate, "APFEL\\+\\+ is no longer rejected as an independent comparator")


def test_published_figure_mislabelled_executable_oracle_rejected(record):
    candidate = copy.deepcopy(record)
    massivedis = candidate["workstream_b_references"]["b1_massivedis_executable_provenance"]
    massivedis["decision"] = "FONLL_REF_EXECUTABLE_FULLY_SPECIFIED"
    candidate["workstream_b_references"]["outcome"] = "REFERENCE_RESOLVED"
    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(candidate, root=ROOT, check_docs=False, check_files=False)


def test_external_tolerance_transferred_to_normalization_rejected(record):
    candidate = copy.deepcopy(record)
    for rule in candidate["workstream_b_references"]["b4_reference_decision_rules"]["rules"]:
        rule["transferable"] = True
    rejected(candidate, "A reference tolerance was made transferable")


def test_global_error_budget_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_b_references"]["b4_reference_decision_rules"][
        "global_budget_created"
    ] = True
    rejected(candidate, "A global error budget was created")


def test_rejected_v2_tolerances_cannot_return(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_c_convergence"]["c3_empirical_route"]["rule_shape_that_a_successor_would_need"].append(
        "absolute target 0.000125"
    )
    rejected(candidate, "Rejected tolerance 0.000125 reintroduced")


def test_prose_versus_code_discrepancy_cannot_be_erased(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_b_references"]["b3_massless_benchmark_execution_contract"][
        "prose_versus_code_discrepancy"
    ]["matches_stated_epsilon"] = True
    rejected(candidate, "Prose-versus-code discrepancy erased")


def test_unvalidated_node_inventory_must_be_consistent(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_b_references"]["load_bearing_unvalidated_nodes_present"] = False
    rejected(candidate, "Unvalidated load-bearing node inventory is inconsistent")


# --------------------------------------------------------------------------
# adversarial: convergence
# --------------------------------------------------------------------------


def test_empirical_convergence_mislabelled_rigorous_remainder_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_c_convergence"]["c1_requirement_decision"]["c1a_assessment"][
        "derivation"
    ] = ""
    rejected(candidate, "C1A has no derivation")


def test_arbitrary_project_precision_target_rejected(record):
    candidate = copy.deepcopy(record)
    empirical = candidate["workstream_c_convergence"]["c3_empirical_route"]
    empirical["precision_target_derivable"] = True
    empirical["no_target_manufactured"] = False
    rejected(candidate, "A precision target was manufactured")


def test_declaring_a_target_without_unblocking_is_caught(record):
    candidate = copy.deepcopy(record)
    empirical = candidate["workstream_c_convergence"]["c3_empirical_route"]
    empirical["why_it_fails"] = []
    rejected(candidate, "Missing target has no explanation")


def test_counterexample_cannot_be_softened(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_c_convergence"]["c4_analytic_software_tests"]["counterexample"][
        "true_error_of_both_paths"
    ] = 0.0
    rejected(candidate, "Counterexample no longer demonstrates an unbounded error")


def test_analytic_tests_cannot_claim_dis_coverage(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_c_convergence"]["c4_analytic_software_tests"][
        "scope"
    ] = "validates the future DIS integrand"
    rejected(candidate, "Analytic tests are no longer scoped to software mechanics")


def test_continuum_positivity_from_finite_sign_grid_rejected(record):
    candidate = copy.deepcopy(record)
    del candidate["workstream_c_convergence"]["c5_grid_gate"]["separation"][
        "continuum_physics_claim"
    ]
    rejected(candidate, "Grid gate separation entry continuum_physics_claim missing")


def test_grid_redesign_must_not_touch_v3(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_c_convergence"]["c5_grid_gate"]["recommended_successor_redesign"][
        "not_applied_to_v3"
    ] = False
    rejected(candidate, "Grid redesign was not kept out of V3")


# --------------------------------------------------------------------------
# adversarial: environment and resources
# --------------------------------------------------------------------------


def test_missing_environment_identity_cannot_claim_bitwise(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_d_environment"][
        "reproducibility_classification"
    ] = "BITWISE_SAME_FROZEN_ENVIRONMENT"
    rejected(candidate, "Bitwise reproducibility claimed with an unbound libm")


def test_bitwise_claim_without_reason_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_d_environment"]["bitwise_claim"] = True
    rejected(candidate, "Bitwise claim overreaches")


def test_numerical_reproducibility_requires_a_bound_libm(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_d_environment"][
        "reproducibility_classification"
    ] = "NUMERICALLY_REPRODUCIBLE_WITH_FROZEN_SOFTWARE_IDENTITY"
    rejected(candidate, "Numerical reproducibility claimed while the libm identity is unbound")


def test_declining_the_weaker_class_needs_a_reason(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_d_environment"].pop(
        "why_not_numerically_reproducible_with_frozen_software_identity"
    )
    rejected(candidate, "The weaker reproducibility class was declined without a reason")


def test_unbound_interpreter_needs_a_note(record):
    candidate = copy.deepcopy(record)
    candidate["workstream_d_environment"]["cpython"]["note"] = ""
    rejected(candidate, "Unbound interpreter has no note")


def test_fabricated_aggregate_resource_count_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["resource_model"]["aggregate_status"] = "DERIVED"
    rejected(candidate, "An aggregate was formed over null categories")


def test_null_resource_needs_a_reason(record):
    candidate = copy.deepcopy(record)
    for item in candidate["resource_model"]["categories"]:
        if item["value"] is None:
            item.pop("reason")
            break
    rejected(candidate, "has no reason")


def test_resource_finiteness_claim_must_match_categories(record):
    candidate = copy.deepcopy(record)
    candidate["resource_model"]["every_category_finite"] = True
    rejected(candidate, "Resource finiteness claim contradicts the category values")


def test_quadrature_resource_arithmetic_is_checked(record):
    candidate = copy.deepcopy(record)
    for item in candidate["resource_model"]["categories"]:
        if item["category"] == "quadrature_integrand_calls":
            item["value"] = 98812
    rejected(candidate, "Quadrature integrand arithmetic inconsistent")


# --------------------------------------------------------------------------
# adversarial: outcome and state
# --------------------------------------------------------------------------


def test_br1_with_unresolved_blocker_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["outcome"]["code"] = "BR1_ALL_PREAUTH_BLOCKERS_RESOLVED"
    candidate["outcome"]["v4_created"] = True
    with pytest.raises(VALIDATOR.ValidationError, match="BR1 declared with remaining blockers"):
        VALIDATOR.validate(
            candidate,
            root=ROOT,
            check_docs=False,
            check_files=False,
            expected_outcome=None,
        )


def test_br1_with_empty_blockers_but_unresolved_nodes_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["outcome"]["code"] = "BR1_ALL_PREAUTH_BLOCKERS_RESOLVED"
    candidate["outcome"]["v4_created"] = True
    candidate["outcome"]["blockers_remaining"] = []
    with pytest.raises(VALIDATOR.ValidationError, match="BR1 declared with unresolved graph nodes"):
        VALIDATOR.validate(
            candidate,
            root=ROOT,
            check_docs=False,
            check_files=False,
            expected_outcome=None,
        )


def test_non_br1_outcome_may_not_create_v4(record):
    candidate = copy.deepcopy(record)
    candidate["outcome"]["v4_created"] = True
    rejected(candidate, "V4 created for a non-BR1 outcome")


def test_br5_needs_more_than_one_family(record):
    candidate = copy.deepcopy(record)
    candidate["outcome"]["blockers_remaining"] = [
        item for item in candidate["outcome"]["blockers_remaining"] if item["family"] == "A_ALPHA"
    ]
    rejected(candidate, "BR5 declared with a single blocker family")


def test_blocker_without_resolution_path_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["outcome"]["blockers_remaining"][0].pop("would_be_resolved_by")
    rejected(candidate, "Remaining blocker has no resolution path")


def test_authorization_true_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authorization"]["PHASE2B_EXECUTION_AUTHORIZED"] = True
    rejected(candidate, "Authorization flag is true")


def test_execution_true_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["execution_state"]["phase2b"] = "EXECUTED"
    rejected(candidate, "Phase 2B execution occurred")


def test_forbidden_physics_execution_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["execution_state"]["dis_structure_functions_executed"] = True
    rejected(candidate, "Forbidden physics or downstream execution recorded")


def test_phase2c_true_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authorization"]["PHASE2C_AUTHORIZED"] = True
    rejected(candidate, "Authorization flag is true")


def test_issue_55_state_change_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["github_target_state"]["status"] = "In Progress"
    rejected(candidate, "Issue #55 target state changed")


def test_gate_decision_change_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["github_target_state"]["gate_decision"] = "PASS"
    rejected(candidate, "Issue #55 target state changed")


def test_non_dis_evidence_cannot_claim_physics(record):
    candidate = copy.deepcopy(record)
    candidate["non_dis_validation_evidence"]["physics_executed"] = True
    rejected(candidate, "Non-DIS evidence claims physics execution")


# --------------------------------------------------------------------------
# adversarial: historical immutability and graph ordering
# --------------------------------------------------------------------------


def test_historical_artifact_mutation_detected(record):
    candidate = copy.deepcopy(record)
    candidate["predecessors"]["preauthorization_v3"]["sha256"] = "0" * 64
    rejected(candidate, "Predecessor hash changed for preauthorization_v3")


def test_v3_outcome_rewrite_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["predecessors"]["preauthorization_v3"]["historical_outcome"] = "V3R1_COMPLETE"
    rejected(candidate, "V3 historical outcome rewritten")


def test_phase2a_decision_strengthening_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_state"]["phase2a_scientific_decision"] = "PASS"
    rejected(candidate, "Phase 2A decision strengthened")


def test_adr_status_change_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_state"]["adr_013_status"] = "Accepted"
    rejected(candidate, "ADR-013 status changed")


def test_pdf_family_change_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_state"]["accepted_pdf_family"] = "ct18nlo_other"
    rejected(candidate, "Accepted PDF family changed")


def test_predecessor_bytes_are_checked_on_disk(record):
    VALIDATOR.validate(record, root=ROOT, check_docs=False, check_files=True)


def test_resolving_a_node_above_an_unresolved_prerequisite_rejected(record):
    candidate = copy.deepcopy(record)
    target = node(candidate, "TEST_QUADRATURE_A")
    target["post_task_status"] = "FULLY_SPECIFIED_NOT_EXECUTED"
    target["deficiencies_after"] = []
    target["still_missing"] = []
    rejected(candidate, "depends on an unresolved prerequisite but is marked resolved")


def test_unresolved_node_must_name_what_is_missing(record):
    candidate = copy.deepcopy(record)
    node(candidate, "TEST_ALPHA")["still_missing"] = []
    rejected(candidate, "marked unresolved without naming what is missing")


def test_resolved_node_may_not_carry_deficiencies(record):
    candidate = copy.deepcopy(record)
    node(candidate, "TEST_BRIDGE")["deficiencies_after"] = ["MISSING_ACCEPTANCE_RULE"]
    rejected(candidate, "marked resolved but still lists deficiencies")


def test_graph_node_set_is_fixed(record):
    candidate = copy.deepcopy(record)
    candidate["blocker_dependency_graph"]["nodes"] = candidate["blocker_dependency_graph"]["nodes"][
        :-1
    ]
    rejected(candidate, "Blocker graph node set changed")


def test_unknown_deficiency_code_rejected(record):
    candidate = copy.deepcopy(record)
    node(candidate, "TEST_ALPHA")["deficiencies_after"].append("MISSING_VIBES")
    rejected(candidate, "Unknown deficiency code on TEST_ALPHA")
