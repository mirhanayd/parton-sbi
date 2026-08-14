"""Adversarial tests for the Phase 2B FONLL validation policy."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_phase2b_fonll_validation_policy.py"
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_fonll_validation_policy_v1.json"

SPEC = importlib.util.spec_from_file_location("phase2b_fonll_policy_validator", SCRIPT)
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


def node(candidate, name):
    for entry in candidate["fonll_validation_graph"]:
        if entry["node"] == name:
            return entry
    raise AssertionError(f"missing node {name}")


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
    assert "VALID phase2b.fonll_validation_policy_v1" in result.stdout


def test_recorded_outcome(record):
    assert record["outcome"]["code"] == "FPD3_ADOPT_HYBRID_COMPONENT_VALIDATION_POLICY"
    assert record["v4_assessment"]["conclusion"] == "V4_SUCCESSOR_PLANNING_NOW_WARRANTED"
    assert record["contract_impact"]["by_scope"]["research_question"] == "UNCHANGED"


def test_this_record_did_not_create_v4(record):
    """This policy task must not have created V4.

    A later, separately reviewed successor may legitimately create one, so the
    assertion is on this record's own flag rather than on the permanent absence
    of the file.  When a V4 exists it must bind this record.
    """

    assert record["v4_not_created_in_this_task"] is True
    v4_path = ROOT / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v4.json"
    if v4_path.exists():
        v4 = json.loads(v4_path.read_text(encoding="utf-8"))
        assert (
            v4["predecessors"]["fonll_validation_policy_v1"]["sha256"]
            == VALIDATOR.sha256_of(ARTIFACT)
        )


def test_predecessor_bytes_are_checked_on_disk(record):
    VALIDATOR.validate(record, root=ROOT, check_docs=False, check_files=True)


def test_accepted_policies_are_not_silently_changed(record):
    assert (
        record["historical_state"]["alpha_policy_unchanged"]
        == "AP1_APFEL_ALPHA_IS_AUTHORITATIVE_SIMULATOR_COUPLING"
    )
    assert (
        record["historical_state"]["normalization_policy_unchanged"]
        == "NP2_REQUIRE_EMPIRICAL_NUMERICAL_STABILITY_NOT_CERTIFIED_ACCURACY"
    )


@pytest.mark.parametrize(
    "field,message",
    [
        ("alpha_policy_unchanged", "Alpha policy silently changed"),
        ("normalization_policy_unchanged", "Normalization policy silently changed"),
    ],
)
def test_silently_changing_an_accepted_policy_rejected(record, field, message):
    candidate = copy.deepcopy(record)
    candidate["historical_state"][field] = "SOMETHING_ELSE"
    rejected(candidate, message)


# --------------------------------------------------------------------------
# adversarial: published versus executable
# --------------------------------------------------------------------------


def test_published_benchmark_mislabeled_executable_rejected(record):
    candidate = copy.deepcopy(record)
    node(candidate, "massive_contribution")["evidence_class"] = "E1"
    node(candidate, "massive_contribution")["disclosure_required"] = False
    rejected(candidate, "carries published evidence but is not classed E2")


@pytest.mark.parametrize("demoted", ["E3", "E4", "E5"])
def test_published_node_demoted_to_another_class_rejected(record, demoted):
    candidate = copy.deepcopy(record)
    entry = node(candidate, "fonll_matching_difference_contribution")
    entry["evidence_class"] = demoted
    entry["disclosure_required"] = False
    rejected(
        candidate,
        "not classed E2|lacks executable independent evidence but requires no disclosure",
    )


def test_e1_without_an_executable_test_rejected(record):
    candidate = copy.deepcopy(record)
    entry = node(candidate, "massive_contribution")
    entry["evidence_class"] = "E1"
    entry["evidence_mode"] = "executable"
    entry["disclosure_required"] = False
    rejected(candidate, "classed E1 with no executable comparison test")


def test_e2_may_not_stop_denying_coverage_of_this_build(record):
    candidate = copy.deepcopy(record)
    for entry in candidate["evidence_classes"]:
        if entry["class"] == "E2_PUBLISHED_INDEPENDENT_NUMERICAL_BENCHMARK":
            entry["cannot_establish"] = ["a transferable tolerance"]
    rejected(candidate, "E2 no longer denies coverage of the frozen build")


def test_e2_may_not_stop_denying_replication(record):
    candidate = copy.deepcopy(record)
    for entry in candidate["evidence_classes"]:
        if entry["class"] == "E2_PUBLISHED_INDEPENDENT_NUMERICAL_BENCHMARK":
            entry["cannot_establish"] = ["anything about this frozen build"]
    rejected(candidate, "E2 no longer denies executable replication")


def test_published_agreement_mislabeled_proof_of_current_correctness_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["paper_impact"]["must_not_claim"] = [
        entry
        for entry in candidate["paper_impact"]["must_not_claim"]
        if "published benchmark proves" not in entry.lower()
    ]
    rejected(candidate, "Paper impact does not forbid the published-proves-current claim")


def test_permitted_claim_may_not_assert_independent_validation(record):
    candidate = copy.deepcopy(record)
    candidate["paper_impact"]["may_claim"].append(
        "the heavy-flavour terms were independently validated"
    )
    rejected(candidate, "Permitted paper claim smuggles in a forbidden assertion")


def test_permitted_claim_may_not_assert_end_to_end_independence(record):
    candidate = copy.deepcopy(record)
    candidate["paper_impact"]["may_claim"].append(
        "an end-to-end independent closure was demonstrated"
    )
    rejected(candidate, "Permitted paper claim smuggles in a forbidden assertion")


def test_end_to_end_closure_claim_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["end_to_end_independent_closure_claimed"] = True
    rejected(candidate, "End-to-end independent closure is claimed")


def test_complete_observable_presented_as_independent_rejected(record):
    candidate = copy.deepcopy(record)
    node(candidate, "complete_nc_observable")["independent"] = True
    rejected(candidate, "The complete observable is presented as independently validated")


def test_complete_observable_given_e1_rejected(record):
    candidate = copy.deepcopy(record)
    entry = node(candidate, "complete_nc_observable")
    entry["evidence_class"] = "E1"
    entry["independent"] = False
    entry["evidence_mode"] = "executable"
    entry["future_phase2b_test"] = "TEST_SOMETHING"
    rejected(candidate, "presented as having an executable independent oracle")


# --------------------------------------------------------------------------
# adversarial: hidden gaps and missing disclosure
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    ["massive_contribution", "fonll_matching_difference_contribution", "normalization", "alpha_s"],
)
def test_hidden_validation_gap_rejected(record, name):
    candidate = copy.deepcopy(record)
    node(candidate, name)["disclosure_required"] = False
    rejected(candidate, "lacks executable independent evidence but requires no disclosure")


@pytest.mark.parametrize(
    "name", ["massive_contribution", "complete_nc_observable", "normalization"]
)
def test_node_without_residual_risk_rejected(record, name):
    candidate = copy.deepcopy(record)
    node(candidate, name)["residual_risk"] = ""
    rejected(candidate, "has no residual-risk statement")


def test_graph_node_set_is_fixed(record):
    candidate = copy.deepcopy(record)
    candidate["fonll_validation_graph"] = candidate["fonll_validation_graph"][:-1]
    rejected(candidate, "Validation graph node set changed")


def test_unvalidated_component_silently_marked_pass_rejected(record):
    candidate = copy.deepcopy(record)
    entry = node(candidate, "fonll_matching_difference_contribution")
    entry["evidence_class"] = "E3"
    entry["disclosure_required"] = False
    entry["residual_risk"] = "none"
    rejected(candidate, "carries published evidence but is not classed E2")


def test_mandatory_paper_limitation_required(record):
    candidate = copy.deepcopy(record)
    candidate["paper_impact"]["mandatory_paper_limitation"] = ""
    rejected(candidate, "carries no mandatory paper limitation")


def test_mandatory_limitation_must_name_the_missing_comparator(record):
    candidate = copy.deepcopy(record)
    candidate["paper_impact"]["mandatory_paper_limitation"] = (
        "Some published evidence was used in this work."
    )
    rejected(candidate, "does not state the missing executable comparator")


# --------------------------------------------------------------------------
# adversarial: historical requirement handling
# --------------------------------------------------------------------------


def test_disclosed_limitation_outcome_when_original_contract_required_e1_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_requirement_reconstruction"][
        "q1_required_executable_implementation_for_every_load_bearing_component"
    ]["answer"] = "YES"
    rejected(
        candidate,
        "chosen although the original contract required E1",
    )


def test_retroactive_strengthening_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_requirement_reconstruction"][
        "retroactive_strengthening_performed"
    ] = True
    rejected(candidate, "retroactively strengthened")


def test_reconstruction_must_account_for_the_v1_review_objections(record):
    candidate = copy.deepcopy(record)
    candidate["historical_requirement_reconstruction"][
        "v1_review_specific_defects_now_addressed"
    ] = []
    rejected(candidate, "without accounting for the v1 review objections")


def test_reconstruction_needs_accepted_sources(record):
    candidate = copy.deepcopy(record)
    candidate["historical_requirement_reconstruction"]["accepted_sources"] = [
        {"locator": "only one"}
    ]
    rejected(candidate, "rests on too little accepted evidence")


@pytest.mark.parametrize("key", ["q1", "q2", "q3", "q4"])
def test_reconstruction_answers_need_evidence(record, key):
    candidate = copy.deepcopy(record)
    mapping = {
        "q1": "q1_required_executable_implementation_for_every_load_bearing_component",
        "q2": "q2_required_credible_independent_closure_strategy",
        "q3": "q3_any_accepted_record_promised_end_to_end_independent_fonll_a",
        "q4": "q4_status_of_the_present_executable_fonll_requirement",
    }
    candidate["historical_requirement_reconstruction"][mapping[key]]["evidence"] = ""
    rejected(candidate, f"{key} has no evidence")


# --------------------------------------------------------------------------
# adversarial: FR1 / proportionality / disclosure
# --------------------------------------------------------------------------


def test_fr1_justified_only_by_more_validation_is_better_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["candidate_policies"]["FR1_REQUIRE_EXECUTABLE_FONLL_REFERENCE"][
        "rejected_because_more_validation_is_always_better"
    ] = True
    rejected(candidate, "more-validation-is-better basis")


def test_disclosed_outcome_with_proportionate_gate_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["paper_scope_proportionality"]["classification"] = "PROPORTIONATE_REQUIRED_GATE"
    rejected(candidate, "while the gate was ruled proportionate")


def test_disclosed_outcome_with_insufficient_disclosure_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["disclosure_sufficiency"][
        "classification"
    ] = "DISCLOSURE_INSUFFICIENT_EXECUTABLE_ORACLE_REQUIRED"
    rejected(candidate, "without sufficient disclosure")


def test_proportionality_must_address_weak_physics_objection(record):
    candidate = copy.deepcopy(record)
    candidate["paper_scope_proportionality"].pop("not_an_excuse_for_weak_physics")
    rejected(candidate, "does not address the weak-physics objection")


@pytest.mark.parametrize(
    "needle,message",
    [
        ("independently validated", "Disclosure conditions omit the mislabelling prohibition"),
        ("frozen", "Disclosure conditions omit configuration freezing"),
        ("uncertainty", "Disclosure conditions omit the no-uncertainty-from-missing-validation rule"),
    ],
)
def test_disclosure_conditions_must_retain_each_guard(record, needle, message):
    candidate = copy.deepcopy(record)
    conditions = candidate["disclosure_sufficiency"]["conditions_all_required"]
    candidate["disclosure_sufficiency"]["conditions_all_required"] = [
        entry for entry in conditions if needle not in entry.lower()
    ] + ["padding condition"] * 3
    rejected(candidate, message)


# --------------------------------------------------------------------------
# adversarial: FR3 semantics and terminology
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "needle,message",
    [
        ("mandatory and gating", "FR3 does not make the available checks gating"),
        ("frozen before authorization", "FR3 does not freeze the coverage matrix before authorization"),
        ("fails", "FR3 does not fail a skipped available check"),
    ],
)
def test_fr3_requirements_must_retain_each_guard(record, needle, message):
    candidate = copy.deepcopy(record)
    requirements = candidate["candidate_policies"]["FR3_HYBRID_REQUIRED_COMPONENT_COVERAGE"][
        "requirements"
    ]
    candidate["candidate_policies"]["FR3_HYBRID_REQUIRED_COMPONENT_COVERAGE"]["requirements"] = [
        entry for entry in requirements if needle not in entry.lower()
    ] + ["padding requirement"] * 3
    rejected(candidate, message)


def test_fr3_adopted_without_non_compromise_argument_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["candidate_policies"]["FR3_HYBRID_REQUIRED_COMPONENT_COVERAGE"].pop(
        "why_not_a_compromise"
    )
    rejected(candidate, "adopted without arguing it is not a compromise")


def test_terminology_replacement_allowing_unspecified_gaps_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["terminology_replacement"]["does_not_permit"] = [
        "treating a disclosed gap as a PASS",
        "reclassifying a node",
    ]
    rejected(candidate, "permits an unspecified gap")


def test_terminology_replacement_allowing_pass_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["terminology_replacement"]["does_not_permit"] = [
        "an unnamed or unspecified gap",
        "reclassifying a node",
    ]
    rejected(candidate, "permits a gap to count as a PASS")


@pytest.mark.parametrize("field", ["evidence_class", "validation_method", "residual_risk"])
def test_terminology_replacement_must_require_each_field(record, field):
    candidate = copy.deepcopy(record)
    candidate["terminology_replacement"]["required_fields_per_load_bearing_node"] = [
        entry
        for entry in candidate["terminology_replacement"]["required_fields_per_load_bearing_node"]
        if entry != field
    ]
    rejected(candidate, f"omits required field {field}")


def test_unjustified_terminology_replacement_blocks_disclosed_outcome(record):
    candidate = copy.deepcopy(record)
    candidate["terminology_replacement"]["classification"] = "TERMINOLOGY_REPLACEMENT_UNRESOLVED"
    rejected(candidate, "without a justified terminology replacement")


# --------------------------------------------------------------------------
# adversarial: non-equivalences and failure modes
# --------------------------------------------------------------------------


@pytest.mark.parametrize("statement", VALIDATOR.REQUIRED_NON_EQUIVALENCES)
def test_non_equivalences_cannot_be_dropped(record, statement):
    candidate = copy.deepcopy(record)
    candidate["preserved_non_equivalences"] = [
        entry for entry in candidate["preserved_non_equivalences"] if entry != statement
    ]
    rejected(candidate, "Non-equivalence dropped")


def test_posterior_calibration_used_as_physics_validation_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["posterior_calibration_is_not_physics_validation"]["asserted"] = False
    rejected(candidate, "Posterior calibration is treated as physics validation")


def test_calibration_as_physics_must_stay_forbidden_in_the_paper(record):
    candidate = copy.deepcopy(record)
    candidate["paper_impact"]["must_not_claim"] = [
        entry
        for entry in candidate["paper_impact"]["must_not_claim"]
        if "posterior calibration validates" not in entry.lower()
    ]
    rejected(candidate, "Paper impact does not forbid calibration-as-physics")


def test_residual_undetectable_failure_must_be_acknowledged(record):
    candidate = copy.deepcopy(record)
    candidate["failure_mode_analysis"] = [
        entry
        for entry in candidate["failure_mode_analysis"]
        if entry["classification"] != "NOT_INDEPENDENTLY_DETECTABLE"
    ]
    rejected(candidate, "No residual undetectable failure is acknowledged")


def test_undetectable_failure_claiming_coverage_rejected(record):
    candidate = copy.deepcopy(record)
    for entry in candidate["failure_mode_analysis"]:
        if entry["classification"] == "NOT_INDEPENDENTLY_DETECTABLE":
            entry["covered_by"] = ["posterior calibration"]
    rejected(candidate, "is undetectable yet lists coverage")


def test_detectable_failure_without_coverage_rejected(record):
    candidate = copy.deepcopy(record)
    for entry in candidate["failure_mode_analysis"]:
        if entry["classification"] == "DETECTABLE_BY_CURRENT_PLAN":
            entry["covered_by"] = []
            break
    rejected(candidate, "is called detectable with no coverage")


def test_rejected_tolerances_cannot_return(record):
    candidate = copy.deepcopy(record)
    candidate["remaining_scientific_limitations"].append("residual budget 0.000125")
    rejected(candidate, "Rejected tolerance 0.000125 reintroduced")


# --------------------------------------------------------------------------
# adversarial: V4 warrant, authorization and history
# --------------------------------------------------------------------------


def test_v4_warranted_while_policy_unresolved_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["outcome"]["code"] = "FPD4_FONLL_REFERENCE_POLICY_REMAINS_UNRESOLVED"
    candidate["disclosure_sufficiency"]["classification"] = "DISCLOSURE_POLICY_UNRESOLVED"
    rejected(
        candidate,
        "V4 warranted while the FONLL policy remains unresolved",
        expected_outcome=None,
    )


def test_v4_warranted_with_remaining_policy_blockers_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["v4_assessment"]["remaining_policy_blockers"] = ["SOMETHING_UNRESOLVED"]
    rejected(candidate, "V4 warranted while policy blockers remain")


def test_v4_creation_flag_must_stay_true(record):
    candidate = copy.deepcopy(record)
    candidate["v4_not_created_in_this_task"] = False
    rejected(candidate, "V4 created in a policy task")


def test_authorization_true_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authorization"]["PHASE2B_EXECUTION_AUTHORIZED"] = True
    rejected(candidate, "Authorization flag is true")


def test_phase2c_true_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["authorization"]["PHASE2C_AUTHORIZED"] = True
    rejected(candidate, "Authorization flag is true")


def test_execution_true_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["execution_state"]["phase2b"] = "EXECUTED"
    rejected(candidate, "Phase 2B execution occurred")


@pytest.mark.parametrize(
    "key", ["apfel_executed", "apfelxx_executed", "massivedis_executed", "fonll_benchmark_executed"]
)
def test_forbidden_physics_execution_rejected(record, key):
    candidate = copy.deepcopy(record)
    candidate["execution_state"][key] = True
    rejected(candidate, "Forbidden physics or downstream execution recorded")


def test_phase2a_changed_to_pass_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_state"]["phase2a_scientific_decision"] = "PASS"
    rejected(candidate, "Phase 2A decision changed")


def test_adr_status_change_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_state"]["adr_013_status"] = "Accepted"
    rejected(candidate, "ADR-013 status changed")


def test_issue_55_state_change_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["github_target_state"]["authorization"] = "Authorized"
    rejected(candidate, "Issue #55 target state changed")


def test_historical_artifact_mutation_detected(record):
    candidate = copy.deepcopy(record)
    candidate["predecessors"]["numerical_policy_decision_v1"]["sha256"] = "0" * 64
    rejected(candidate, "Predecessor hash changed for numerical_policy_decision_v1")


def test_research_question_change_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["contract_impact"]["by_scope"]["research_question"] = "CHANGES_RESEARCH_QUESTION"
    rejected(candidate, "changes the research question")


@pytest.mark.parametrize("key", VALIDATOR.RESEARCH_QUESTION_KEYS)
def test_research_question_invariants_must_hold(record, key):
    candidate = copy.deepcopy(record)
    candidate["contract_impact"]["research_question_check"][key] = False
    rejected(candidate, f"Research-question invariant {key} not preserved")


def test_silent_gate_replacement_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["contract_impact"]["replacement_is_explicit_not_silent"] = False
    rejected(candidate, "A validation gate is replaced silently")
