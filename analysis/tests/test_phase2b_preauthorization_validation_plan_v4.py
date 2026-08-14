"""Adversarial tests for the Phase 2B preauthorization validation plan V4."""

import copy
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SCRIPT = ROOT / "scripts/validate_phase2b_preauthorization_validation_plan_v4.py"
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v4.json"

SPEC = importlib.util.spec_from_file_location("phase2b_preauth_v4_validator", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


@pytest.fixture
def record():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def rejected(candidate, expected_message, expected_outcome=VALIDATOR.EXPECTED_OUTCOME):
    with pytest.raises(VALIDATOR.ValidationError, match=expected_message):
        VALIDATOR.validate(
            candidate,
            root=ROOT,
            check_docs=False,
            check_files=False,
            expected_outcome=expected_outcome,
        )


def row(candidate, component_id):
    for entry in candidate["component_coverage_matrix"]:
        if entry["component_id"] == component_id:
            return entry
    raise AssertionError(f"missing component {component_id}")


def category(candidate, name):
    for entry in candidate["authoring_item_7_resource_model"]["categories"]:
        if entry["category"] == name:
            return entry
    raise AssertionError(f"missing resource category {name}")


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
    assert "VALID phase2b.preauthorization_validation_plan_v4" in result.stdout


def test_recorded_outcome(record):
    assert record["outcome"]["code"] == VALIDATOR.EXPECTED_OUTCOME
    assert record["authorization"]["PHASE2B_AUTHORIZED"] is False
    assert record["authorization"]["PHASE2B_EXECUTED"] is False
    assert record["execution_state"]["phase2b"] == "NOT_EXECUTED"
    assert record["next_action"] == "SEPARATE_INDEPENDENT_PHASE2B_EXECUTION_AUTHORIZATION_REVIEW"


def test_predecessor_bytes_are_checked_on_disk(record):
    VALIDATOR.validate(record, root=ROOT, check_docs=False, check_files=True)


def test_v4_creates_no_new_policy(record):
    assert record["inherited_policies"]["policies_changed_by_v4"] == []
    assert record["outcome"]["new_policy_created"] is False


# --------------------------------------------------------------------------
# 1-5 evidence-class integrity
# --------------------------------------------------------------------------


def test_fake_e1_assignment_rejected(record):
    candidate = copy.deepcopy(record)
    entry = row(candidate, "MASSIVE_CONTRIBUTION")
    entry["evidence_class"] = "E1"
    entry["disclosure_required"] = False
    rejected(candidate, "MASSIVE_CONTRIBUTION is no longer published evidence")


def test_e2_promoted_to_implementation_correctness_rejected(record):
    candidate = copy.deepcopy(record)
    for entry in candidate["evidence_taxonomy"]:
        if entry["class"] == "E2_PUBLISHED_INDEPENDENT_NUMERICAL_BENCHMARK":
            entry["cannot_establish"] = ["a transferable tolerance", "end-to-end validation"]
    rejected(candidate, "E2 no longer denies current-build correctness")


def test_e6_promoted_to_independent_correctness_rejected(record):
    candidate = copy.deepcopy(record)
    for entry in candidate["evidence_taxonomy"]:
        if entry["class"] == "E6_INTERNAL_SELF_CONVERGENCE":
            entry["cannot_establish"] = ["rigorous accuracy", "a theorem-level error bound"]
    rejected(candidate, "E6 no longer denies independent correctness")


def test_complete_observable_marked_independently_closed_rejected(record):
    candidate = copy.deepcopy(record)
    row(candidate, "COMPLETE_NC_OBSERVABLE")["independent"] = True
    rejected(candidate, "The complete observable is marked independent")


def test_complete_observable_marked_e1_rejected(record):
    candidate = copy.deepcopy(record)
    row(candidate, "COMPLETE_NC_OBSERVABLE")["evidence_class"] = "E1"
    rejected(candidate, "The complete observable is marked E1")


def test_published_fonll_evidence_called_executable_rejected(record):
    candidate = copy.deepcopy(record)
    row(candidate, "FONLL_MATCHING_DIFFERENCE_CONTRIBUTION")["executable"] = True
    rejected(candidate, "FONLL_MATCHING_DIFFERENCE_CONTRIBUTION is marked executable")


def test_e5_promotion_prohibition_cannot_be_removed(record):
    candidate = copy.deepcopy(record)
    candidate["evidence_promotion_forbidden"] = [
        entry
        for entry in candidate["evidence_promotion_forbidden"]
        if "executable verification" not in entry
    ]
    rejected(candidate, "E5 promotion is no longer forbidden")


# --------------------------------------------------------------------------
# 6-8 disclosure, skipped checks, reclassification
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "component",
    ["MASSIVE_CONTRIBUTION", "MASSLESS_COEFFICIENT_CONTRIBUTION", "QUADRATURE_A", "ALPHA_S"],
)
def test_disclosed_limitation_converted_to_pass_rejected(record, component):
    candidate = copy.deepcopy(record)
    row(candidate, component)["disclosure_required"] = False
    rejected(candidate, "lacks executable independent evidence but requires no disclosure")


def test_skipped_available_check_reclassified_optional_rejected(record):
    candidate = copy.deepcopy(record)
    entry = row(candidate, "MASSLESS_COEFFICIENT_CONTRIBUTION")
    entry["gating"] = False
    rejected(candidate, "has an available mandatory check but is not gating")


def test_post_result_reclassification_forbidden(record):
    candidate = copy.deepcopy(record)
    candidate["coverage_matrix_rules"]["post_result_reclassification_forbidden"] = False
    rejected(candidate, "permits post-result reclassification")


def test_fpd3_reclassification_prohibition_cannot_be_removed(record):
    candidate = copy.deepcopy(record)
    candidate["fpd3_binding"]["post_result_reclassification_allowed"] = True
    rejected(candidate, "Post-result reclassification permitted")


def test_gating_on_unavailable_reference_rejected(record):
    candidate = copy.deepcopy(record)
    row(candidate, "MASSIVE_CONTRIBUTION")["gating"] = True
    rejected(candidate, "gating without an available reference|gates on an unavailable reference")


# --------------------------------------------------------------------------
# 9-12 posterior calibration and alpha diagnostic
# --------------------------------------------------------------------------


def test_posterior_calibration_used_as_physics_validation_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["paper_claim_boundary"]["must_not_claim"] = [
        entry
        for entry in candidate["paper_claim_boundary"]["must_not_claim"]
        if "posterior calibration proves physics" not in entry.lower()
    ]
    rejected(candidate, "Calibration-as-physics is no longer forbidden")


def test_alpha_diagnostic_made_gating_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_5_alpha_diagnostic"]["gating"] = "GATING"
    rejected(candidate, "Alpha diagnostic is not marked non-gating")


def test_alpha_diagnostic_row_made_gating_rejected(record):
    candidate = copy.deepcopy(record)
    row(candidate, "ALPHA_S")["gating"] = True
    rejected(candidate, "The alpha diagnostic became gating")


def test_alpha_diagnostic_called_continuum_proof_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_5_alpha_diagnostic"]["must_not_establish"] = [
        "bitwise identity",
        "Phase 2B authorization",
    ]
    rejected(candidate, "Alpha diagnostic may claim continuum equivalence")


def test_ct18_apfel_called_bitwise_identical_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_5_alpha_diagnostic"]["must_not_establish"] = [
        "continuous-domain equivalence",
        "Phase 2B authorization",
    ]
    rejected(candidate, "Alpha diagnostic may claim bitwise identity")


def test_unresolved_running_order_item_cannot_be_silently_resolved(record):
    candidate = copy.deepcopy(record)
    for entry in candidate["authoring_item_5_alpha_diagnostic"]["declared_convention_compatibility_items"]:
        if entry["item"] == "perturbative order of the coupling running itself":
            entry["status"] = "COMPATIBLE"
    rejected(candidate, "unresolved running-order item was silently resolved")


# --------------------------------------------------------------------------
# 13-16 tolerance transfer and post-hoc mutation
# --------------------------------------------------------------------------


def test_external_benchmark_tolerance_transferred_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_1_np2_stability_protocol"]["forbidden_imports"] = [
        "nothing in particular"
    ]
    rejected(candidate, "MassiveDIS level is no longer a forbidden import")


def test_massless_level_transferred_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_1_np2_stability_protocol"]["forbidden_imports"] = [
        "the published MassiveDIS 0.001 observation"
    ]
    rejected(candidate, "massless level is no longer a forbidden import")


def test_rejected_v2_tolerances_cannot_return(record):
    candidate = copy.deepcopy(record)
    candidate["remaining_scientific_limitations"].append("residual budget 0.000125")
    rejected(candidate, "Rejected tolerance 0.000125 reintroduced")


def test_invented_scalar_tolerance_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_1_np2_stability_protocol"]["invented_scalar_tolerance"] = True
    rejected(candidate, "A scalar tolerance was invented")


def test_post_hoc_tolerance_mutation_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_1_np2_stability_protocol"]["required_principles_asserted"][
        "no_post_hoc_tolerance_choice"
    ] = False
    rejected(candidate, "no_post_hoc_tolerance_choice not asserted")


def test_certification_wording_in_a_positive_claim_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["paper_claim_boundary"]["may_claim"].append(
        "normalization was rigorously certified to the stated accuracy"
    )
    rejected(candidate, "smuggles in a forbidden assertion|Certification wording reintroduced")


# --------------------------------------------------------------------------
# 17-23 anchors, adaptivity, nesting, degenerate convergence
# --------------------------------------------------------------------------


def test_dropped_theta_anchor_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_1_np2_stability_protocol"]["required_principles_asserted"][
        "no_anchor_dropped"
    ] = False
    rejected(candidate, "no_anchor_dropped not asserted")


def test_averaging_away_a_failed_anchor_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_1_np2_stability_protocol"]["required_principles_asserted"][
        "no_averaging_over_a_failed_anchor"
    ] = False
    rejected(candidate, "no_averaging_over_a_failed_anchor not asserted")


def test_adaptive_refinement_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_1_np2_stability_protocol"]["frozen_before_execution"][
        "refinement_ladder"
    ]["adaptive_refinement_allowed"] = True
    rejected(candidate, "Adaptive refinement permitted")


def test_hidden_point_insertion_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_2_grid_gate"]["prohibitions"]["adaptive_insertion_allowed"] = True
    rejected(candidate, "Adaptive insertion permitted")


def test_hidden_point_deletion_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_2_grid_gate"]["prohibitions"]["post_hoc_deletion_allowed"] = True
    rejected(candidate, "Post-hoc deletion permitted")


def test_gauss_legendre_mislabeled_nested_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_2_grid_gate"]["gauss_legendre"]["nesting_status"] = "NESTED_BITWISE"
    rejected(candidate, "Gauss-Legendre levels mislabelled as nested")


def test_gauss_legendre_mislabelling_guard_cannot_be_removed(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_2_grid_gate"]["gauss_legendre"]["mislabelling_forbidden"] = False
    rejected(candidate, "Gauss-Legendre mislabelling permitted")


def test_degenerate_convergence_counterexample_cannot_be_dropped(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_2_grid_gate"]["structural_counterexample_required"]["requirement"] = ""
    rejected(candidate, "false-convergence counterexample is not required")


def test_inconclusive_may_not_become_pass(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_1_np2_stability_protocol"]["frozen_before_execution"][
        "acceptance_semantics"
    ]["INCONCLUSIVE"] = "treated as a pass when convenient"
    rejected(candidate, "INCONCLUSIVE may become PASS")


def test_gauss_legendre_really_is_not_nested():
    """The non-nesting claim is verified, not asserted."""
    from scipy.special import roots_legendre

    gl16 = {float(v) for v in roots_legendre(16)[0]}
    gl32 = {float(v) for v in roots_legendre(32)[0]}
    assert len(gl16 & gl32) == 0


def test_clenshaw_curtis_really_is_nested():
    from analysis.validation.phase2b_quadrature_oracles import clenshaw_curtis_rule

    cc17 = clenshaw_curtis_rule(17)[0]
    cc33 = clenshaw_curtis_rule(33)[0]
    cc65 = clenshaw_curtis_rule(65)[0]
    assert all(cc17[i] == cc33[2 * i] for i in range(17))
    assert all(cc33[i] == cc65[2 * i] for i in range(33))


def test_point_grid_really_is_nested():
    from analysis.validation.phase2b_grid_oracles import levels_are_bitwise_nested

    for lo, hi in ((6e-7, 0.65), (3.5, 50000.0)):
        nested, failures = levels_are_bitwise_nested([17, 33, 65], lo, hi)
        assert nested, failures


# --------------------------------------------------------------------------
# 24-27 bridge integrity
# --------------------------------------------------------------------------


def test_double_x_times_f_multiplication_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_4_bridge"]["shared_semantics"]["double_multiplication_allowed"] = True
    rejected(candidate, "Bridge permits double_multiplication_allowed")


def test_exactly_one_multiplication_policy_cannot_be_dropped(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_4_bridge"]["shared_semantics"][
        "exactly_one_multiplication_policy"
    ] = False
    rejected(candidate, "exactly-one-multiplication policy was dropped")


def test_bridge_support_extrapolation_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_4_bridge"]["shared_semantics"]["extrapolation_allowed"] = True
    rejected(candidate, "Bridge permits extrapolation_allowed")


def test_support_repair_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_4_bridge"]["shared_semantics"]["support_repair_allowed"] = True
    rejected(candidate, "Bridge permits support_repair_allowed")


def test_incorrect_q_versus_q2_mapping_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_4_bridge"]["shared_semantics"]["q_versus_q2_convention"] = ""
    rejected(candidate, "Bridge does not freeze q_versus_q2_convention")


def test_flavor_remapping_drift_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_4_bridge"]["shared_semantics"][
        "implicit_flavor_remap_allowed"
    ] = True
    rejected(candidate, "Bridge permits implicit_flavor_remap_allowed")


def test_silent_zero_replacement_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_4_bridge"]["shared_semantics"][
        "silent_zero_replacement_allowed"
    ] = True
    rejected(candidate, "Bridge permits silent_zero_replacement_allowed")


def test_bridge_slot_cap_must_equal_invocations_times_slots(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_4_bridge"]["work_cap"]["slot_comparisons_total"] = 14532
    rejected(candidate, "not invocations times slots")


def test_bridge_attempt_cap_must_equal_profile_sum(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_4_bridge"]["work_cap"]["callback_attempts_total"] = 2000
    rejected(candidate, "does not equal the profile sum")


# --------------------------------------------------------------------------
# 28-33 runtime identity and resources
# --------------------------------------------------------------------------


def test_source_hash_mislabeled_executable_verification_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_6_runtime_identity"][
        "source_hash_is_not_executable_verification"
    ] = False
    rejected(candidate, "source hash is treated as executable verification")


def test_executable_without_installed_rejected(record):
    candidate = copy.deepcopy(record)
    for dep in candidate["authoring_item_6_runtime_identity"]["dependencies"]:
        if dep["name"] == "CPython":
            dep["executable_in_current_environment"] = True
    rejected(candidate, "is executable but not installed")


@pytest.mark.parametrize("dependency", ["CPython", "NumPy", "SciPy"])
def test_unpinned_load_bearing_dependency_rejected(record, dependency):
    candidate = copy.deepcopy(record)
    for dep in candidate["authoring_item_6_runtime_identity"]["dependencies"]:
        if dep["name"] == dependency:
            dep["hash_pinned"] = False
    rejected(candidate, f"{dependency} is not hash pinned")


def test_must_install_list_must_match_derived_set(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_6_runtime_identity"]["must_be_installed_before_execution"] = [
        "CPython 3.10.20"
    ]
    rejected(candidate, "must-install list does not match")


def test_cpu_made_a_scientific_dependency_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_6_runtime_identity"]["cpu_feature_dependency"][
        "is_a_scientific_dependency"
    ] = True
    rejected(candidate, "CPU microarchitecture was made a scientific dependency")


def test_libm_certification_resurrected_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_6_runtime_identity"][
        "libm_certification_resurrected_as_gate"
    ] = True
    rejected(candidate, "libm certification was resurrected as a gate")


@pytest.mark.parametrize(
    "name,wrong",
    [
        ("point_grid_complete_rate_evaluations", 63881),
        ("quadrature_a_integrand_evaluations", 48000),
        ("quadrature_b_integrand_evaluations", 50000),
        ("analytic_ew_jacobian_cases", 215),
    ],
)
def test_resource_undercount_rejected(record, name, wrong):
    candidate = copy.deepcopy(record)
    entry = category(candidate, name)
    entry["cap"] = wrong
    entry["worst_case"] = wrong
    entry["nominal"] = min(entry["nominal"], wrong)
    entry["minimum"] = min(entry["minimum"], wrong)
    rejected(candidate, "cap should be")


def test_resource_heterogeneous_unit_sum_rejected(record):
    candidate = copy.deepcopy(record)
    aggregate = candidate["authoring_item_7_resource_model"]["additive_aggregates"][0]
    aggregate["members"] = aggregate["members"] + ["bridge_callback_attempts"]
    rejected(candidate, "aggregate mixes units")


def test_aggregate_value_is_recomputed(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_7_resource_model"]["additive_aggregates"][0]["value"] = 999999
    rejected(candidate, "Aggregate value should be")


def test_more_than_one_aggregate_rejected(record):
    candidate = copy.deepcopy(record)
    aggregates = candidate["authoring_item_7_resource_model"]["additive_aggregates"]
    candidate["authoring_item_7_resource_model"]["additive_aggregates"] = aggregates * 2
    rejected(candidate, "exactly one additive aggregate")


def test_hidden_retry_budget_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_7_resource_model"]["retry_budget"] = 1
    rejected(candidate, "A retry budget exists")


def test_retry_until_pass_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_7_resource_model"]["retry_until_pass_allowed"] = True
    rejected(candidate, "Retry-until-pass permitted")


def test_resource_copied_from_previous_totals_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authoring_item_7_resource_model"]["copied_from_previous_totals"] = True
    rejected(candidate, "Resources were copied")


def test_resource_bounds_must_be_ordered(record):
    candidate = copy.deepcopy(record)
    entry = category(candidate, "alpha_diagnostic_provider_evaluations")
    entry["minimum"] = entry["cap"] + 1
    rejected(candidate, "bounds are not ordered")


def test_resource_arithmetic_is_independently_derivable():
    """The serialized caps are reproduced from first principles here."""
    assert 9 * sum(n * n + 13 * n for n in (17, 33, 65)) == 63882
    assert 9 * sum(n * n for n in (16, 32, 64)) == 48384
    assert 9 * sum(n * n for n in (17, 33, 65)) == 50427
    assert 9 * 24 == 216
    assert 27 * 3 == 81
    assert 1042 * 14 == 14588
    assert 63882 + 48384 + 50427 == 162693


# --------------------------------------------------------------------------
# 34-37 sign and clipping
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "banned,message",
    [
        ("abs(rate)", "abs\\(rate\\) is no longer forbidden"),
        ("max(rate,0)", "max\\(rate,0\\) is no longer forbidden"),
        ("clipping", "Clipping is no longer forbidden"),
        ("post-hoc support shrinkage", "Support shrinkage is no longer forbidden"),
        ("point removal", "Point removal is no longer forbidden"),
    ],
)
def test_sign_repair_prohibitions_must_survive(record, banned, message):
    candidate = copy.deepcopy(record)
    candidate["raw_rate_sign_policy"]["forbidden_operations"] = [
        entry
        for entry in candidate["raw_rate_sign_policy"]["forbidden_operations"]
        if entry != banned
    ]
    rejected(candidate, message)


def test_negative_raw_rate_must_fail(record):
    candidate = copy.deepcopy(record)
    candidate["raw_rate_sign_policy"]["finite_negative"] = "PASS"
    rejected(candidate, "A negative raw rate no longer fails")


def test_continuum_positivity_claim_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["raw_rate_sign_policy"]["continuum_positivity_claimed"] = True
    rejected(candidate, "Continuum positivity claimed")


# --------------------------------------------------------------------------
# 38-47 authorization, history and paper claims
# --------------------------------------------------------------------------


def test_phase2b_authorization_promotion_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authorization"]["PHASE2B_AUTHORIZED"] = True
    rejected(candidate, "An authorization flag is true")


def test_execution_promotion_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["execution_state"]["phase2b"] = "EXECUTED"
    rejected(candidate, "Phase 2B execution occurred")


@pytest.mark.parametrize(
    "key", ["apfel_executed", "apfelxx_executed", "massivedis_executed", "fonll_benchmark_executed"]
)
def test_physics_execution_promotion_rejected(record, key):
    candidate = copy.deepcopy(record)
    candidate["execution_state"][key] = True
    rejected(candidate, "Forbidden physics or downstream execution recorded")


def test_phase2c_authorization_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authorization"]["PHASE2C_AUTHORIZED"] = True
    rejected(candidate, "An authorization flag is true")


def test_d2_authorization_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authorization"]["D2_AUTHORIZED"] = True
    rejected(candidate, "An authorization flag is true")


def test_historical_phase2a_changed_to_pass_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_state"]["phase2a_scientific_decision"] = "PASS"
    rejected(candidate, "Phase 2A decision changed")


def test_adr_013_changed_to_accepted_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_state"]["adr_013_status"] = "Accepted"
    rejected(candidate, "ADR-013 status changed")


def test_accepted_pdf_family_drift_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_state"]["accepted_pdf_family"] = "ct18nlo_other_family"
    rejected(candidate, "Accepted PDF family drifted")


def test_fonll_a_contract_drift_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_state"]["heavy_flavor_contract"] = "FONLL-C NNLO"
    rejected(candidate, "FONLL-A contract drifted")


def test_scheme_drift_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["accepted_contract"]["scheme"] = "RTOPT"
    rejected(candidate, "Scheme drifted")


def test_predecessor_hash_mutation_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["predecessors"]["fonll_validation_policy_v1"]["sha256"] = "0" * 64
    rejected(candidate, "Predecessor hash changed for fonll_validation_policy_v1")


def test_issue_54_reinterpretation_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_state"]["issue_54_unchanged"] = False
    rejected(candidate, "Issue #54 reinterpreted")


def test_paper_claim_expansion_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["paper_claim_boundary"]["may_claim"].append(
        "the FONLL implementation was independently validated"
    )
    rejected(candidate, "smuggles in a forbidden assertion")


def test_end_to_end_independent_closure_claim_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["paper_claim_boundary"]["must_not_claim"] = [
        entry
        for entry in candidate["paper_claim_boundary"]["must_not_claim"]
        if "end-to-end independent" not in entry.lower()
    ]
    rejected(candidate, "End-to-end independent closure is no longer forbidden")


def test_mandatory_paper_limitation_cannot_be_removed(record):
    candidate = copy.deepcopy(record)
    candidate["paper_claim_boundary"]["mandatory_limitation"] = ""
    rejected(candidate, "mandatory paper limitation was removed")


def test_silent_policy_change_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["inherited_policies"]["alpha_policy"] = "AP2_SOMETHING_ELSE"
    rejected(candidate, "Inherited policy alpha_policy silently changed")


def test_policy_change_list_must_stay_empty(record):
    candidate = copy.deepcopy(record)
    candidate["inherited_policies"]["policies_changed_by_v4"] = ["AP1"]
    rejected(candidate, "silently created or changed a scientific policy")


@pytest.mark.parametrize("statement", VALIDATOR.REQUIRED_NON_EQUIVALENCES)
def test_non_equivalences_cannot_be_dropped(record, statement):
    candidate = copy.deepcopy(record)
    candidate["preserved_non_equivalences"] = [
        entry for entry in candidate["preserved_non_equivalences"] if entry != statement
    ]
    rejected(candidate, "Non-equivalence dropped")


@pytest.mark.parametrize("key", VALIDATOR.RESEARCH_QUESTION_KEYS)
def test_research_question_invariants_must_hold(record, key):
    candidate = copy.deepcopy(record)
    candidate["research_question_invariants"][key] = False
    rejected(candidate, f"Research-question invariant {key} not preserved")


def test_complete_outcome_requires_all_items_frozen(record):
    candidate = copy.deepcopy(record)
    candidate["outcome"]["seven_authoring_items_disposition"]["item_2_grid_gate"] = "BLOCKED"
    rejected(candidate, "complete V4 has an unfrozen authoring item")


def test_v4_must_deny_that_it_authorizes_phase2b(record):
    candidate = copy.deepcopy(record)
    candidate["outcome"]["does_not_mean"] = ["numerical physics validated"]
    rejected(candidate, "does not deny that it authorizes Phase 2B")
