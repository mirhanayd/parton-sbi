"""Adversarial tests for the Phase 2B numerical-contract policy decision."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_phase2b_numerical_policy_decision.py"
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_numerical_policy_decision_v1.json"

SPEC = importlib.util.spec_from_file_location("phase2b_numerical_policy_validator", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


@pytest.fixture
def record():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def rejected(candidate, expected_message, expected_outcome=VALIDATOR.EXPECTED_COMBINED):
    with pytest.raises(VALIDATOR.ValidationError, match=expected_message):
        VALIDATOR.validate(
            candidate,
            root=ROOT,
            check_docs=False,
            check_files=False,
            expected_outcome=expected_outcome,
        )


def alpha(candidate):
    return candidate["question_a_alpha_authority"]


def norm(candidate):
    return candidate["question_b_normalization_claim"]


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
    assert "VALID phase2b.numerical_policy_decision_v1" in result.stdout


def test_recorded_decisions(record):
    assert alpha(record)["decision"] == "AP1_APFEL_ALPHA_IS_AUTHORITATIVE_SIMULATOR_COUPLING"
    assert (
        norm(record)["decision"]
        == "NP2_REQUIRE_EMPIRICAL_NUMERICAL_STABILITY_NOT_CERTIFIED_ACCURACY"
    )
    assert record["combined_decision"]["code"] == "PD1_ADOPT_AP1_AND_NP2"
    assert record["combined_decision"]["research_question_impact"] == "UNCHANGED"


def test_no_v4_artifact_created():
    assert not (
        ROOT / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v4.json"
    ).exists()
    assert record_successor_flag()


def record_successor_flag():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    return data["successor_plan_assessment"]["v4_not_created_in_this_task"] is True


def test_predecessor_bytes_are_checked_on_disk(record):
    VALIDATOR.validate(record, root=ROOT, check_docs=False, check_files=True)


# --------------------------------------------------------------------------
# adversarial: alpha policy
# --------------------------------------------------------------------------


def test_ap1_while_still_requiring_continuous_bitwise_identity_rejected(record):
    candidate = copy.deepcopy(record)
    alpha(candidate)["scientific_review"][
        "q1_runtime_evaluator_must_match_grid_producing_evaluator"
    ]["answer"] = "YES"
    rejected(candidate, "AP1 while still requiring evaluator identity")


def test_ap1_that_drops_the_identity_forbiddance_rejected(record):
    candidate = copy.deepcopy(record)
    alpha(candidate)["what_ap1_forbids"] = [
        "claiming the diagnostic comparison establishes equivalence"
    ]
    rejected(candidate, "AP1 does not forbid a continuous or bitwise identity gate")


def test_ap1_that_stops_forbidding_the_equivalence_claim_rejected(record):
    candidate = copy.deepcopy(record)
    alpha(candidate)["what_ap1_forbids"] = [
        "requiring continuous or bitwise coupling identity as a preauthorization gate"
    ]
    rejected(candidate, "AP1 does not forbid calling the diagnostic an equivalence result")


@pytest.mark.parametrize(
    "dropped",
    [
        "alpha_s at the Z mass",
        "perturbative order of the observable",
        "heavy-quark pole masses",
        "flavour scheme and maximum active flavours",
        "perturbative order of the coupling running itself",
    ],
)
def test_ap1_silently_ignoring_a_compatibility_item_rejected(record, dropped):
    candidate = copy.deepcopy(record)
    review = alpha(candidate)["scientific_review"][
        "q2_declared_convention_is_the_relevant_contract"
    ]
    review["required_compatibility_items"] = [
        item for item in review["required_compatibility_items"] if item["item"] != dropped
    ]
    rejected(candidate, "AP1 silently drops a declared-convention compatibility item")


def test_unresolved_compatibility_item_must_carry_a_note(record):
    candidate = copy.deepcopy(record)
    for item in alpha(candidate)["scientific_review"][
        "q2_declared_convention_is_the_relevant_contract"
    ]["required_compatibility_items"]:
        if item["status"] == "UNRESOLVED_COMPATIBILITY_ITEM":
            item.pop("note")
    rejected(candidate, "Unresolved compatibility item carries no note")


def test_ap1_calling_the_diagnostic_proven_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["paper_impact"]["may_claim"].append(
        "the CT18 and APFEL couplings were shown to be equivalent"
    )
    rejected(candidate, "Permitted paper claim smuggles in a forbidden assertion")


def test_ap1_diagnostic_may_not_become_a_gate(record):
    candidate = copy.deepcopy(record)
    alpha(candidate)["scientific_review"]["q5_later_diagnostic_that_remains_appropriate"][
        "gating"
    ] = True
    rejected(candidate, "AP1 diagnostic incorrectly made a gate")


def test_ap1_diagnostic_may_not_be_dropped(record):
    candidate = copy.deepcopy(record)
    alpha(candidate)["scientific_review"]["q5_later_diagnostic_that_remains_appropriate"][
        "required"
    ] = False
    rejected(candidate, "AP1 without a required later diagnostic")


def test_ap1_may_not_define_a_tolerance(record):
    candidate = copy.deepcopy(record)
    alpha(candidate)["scientific_review"]["q5_later_diagnostic_that_remains_appropriate"][
        "no_tolerance_defined_here"
    ] = False
    rejected(candidate, "AP1 defines a tolerance")


def test_ap1_review_trigger_may_not_be_a_numerical_threshold(record):
    candidate = copy.deepcopy(record)
    alpha(candidate)["scientific_review"]["q5_later_diagnostic_that_remains_appropriate"][
        "review_trigger_is_not_a_numerical_threshold"
    ] = False
    rejected(candidate, "AP1 diagnostic smuggles in a numerical threshold")


def test_ap1_without_a_decisive_source_fact_rejected(record):
    candidate = copy.deepcopy(record)
    alpha(candidate)["decisive_source_fact"]["verified_this_task"] = False
    rejected(candidate, "AP1 decisive fact was not verified")


def test_ap1_adopted_purely_for_convenience_rejected(record):
    candidate = copy.deepcopy(record)
    alpha(candidate).pop("why_this_is_not_a_convenience_choice")
    rejected(candidate, "AP1 adopted without arguing it is more than convenience")


def test_alpha_rejected_alternatives_must_cover_every_option(record):
    candidate = copy.deepcopy(record)
    alpha(candidate)["rejected_alternatives"] = alpha(candidate)["rejected_alternatives"][:1]
    rejected(candidate, "Alpha rejected-alternative inventory does not cover every other option")


def test_alpha_policy_changing_research_question_rejected(record):
    candidate = copy.deepcopy(record)
    alpha(candidate)["contract_impact"]["by_scope"][
        "research_question"
    ] = "CHANGES_RESEARCH_QUESTION"
    rejected(candidate, "Alpha policy changes the research question")


def test_silent_contract_replacement_rejected(record):
    candidate = copy.deepcopy(record)
    alpha(candidate)["contract_impact"]["replacement_is_explicit_not_silent"] = False
    rejected(candidate, "Alpha policy replaces a contract silently")


# --------------------------------------------------------------------------
# adversarial: normalization policy
# --------------------------------------------------------------------------


def test_np2_labelled_rigorous_or_certified_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["paper_impact"]["may_claim"].append(
        "normalization is rigorously certified to the stated accuracy"
    )
    rejected(candidate, "Permitted paper claim smuggles in a forbidden assertion")


def test_np2_dropping_the_certified_prohibition_rejected(record):
    candidate = copy.deepcopy(record)
    norm(candidate)["scientific_review"]["q3_claims_forbidden_under_np2"] = [
        "agreement between the two quadrature families proves convergence"
    ]
    rejected(candidate, "NP2 does not forbid a certified-accuracy claim")


def test_np2_allowing_post_hoc_tolerance_tuning_rejected(record):
    candidate = copy.deepcopy(record)
    forbidden = norm(candidate)["scientific_review"]["q3_claims_forbidden_under_np2"]
    norm(candidate)["scientific_review"]["q3_claims_forbidden_under_np2"] = [
        entry
        for entry in forbidden
        if "after seeing" not in entry.lower() and "post-hoc" not in entry.lower()
    ]
    rejected(candidate, "NP2 does not forbid post-hoc tolerance tuning")


def test_np2_transferring_the_external_benchmark_rejected(record):
    candidate = copy.deepcopy(record)
    forbidden = norm(candidate)["scientific_review"]["q3_claims_forbidden_under_np2"]
    norm(candidate)["scientific_review"]["q3_claims_forbidden_under_np2"] = [
        entry for entry in forbidden if "0.001" not in entry and "massivedis" not in entry.lower()
    ]
    rejected(candidate, "NP2 does not forbid transferring the external benchmark level")


def test_np2_dropping_the_successive_difference_prohibition_rejected(record):
    candidate = copy.deepcopy(record)
    forbidden = norm(candidate)["scientific_review"]["q3_claims_forbidden_under_np2"]
    norm(candidate)["scientific_review"]["q3_claims_forbidden_under_np2"] = [
        entry for entry in forbidden if "successive difference" not in entry.lower()
    ]
    rejected(candidate, "NP2 does not forbid treating a successive difference as a bound")


def test_np2_inventing_a_tolerance_rejected(record):
    candidate = copy.deepcopy(record)
    norm(candidate)["scientific_review"]["numerical_tolerance_defined_here"] = True
    rejected(candidate, "The policy decision invented a numerical tolerance")


def test_np2_hiding_residual_risk_rejected(record):
    candidate = copy.deepcopy(record)
    norm(candidate)["scientific_review"][
        "q2_empirical_independent_quadrature_stability_is_sufficient_if_disclosed"
    ].pop("residual_risk_disclosed")
    rejected(candidate, "NP2 hides its residual risk")


def test_np2_thin_protocol_rejected(record):
    candidate = copy.deepcopy(record)
    norm(candidate)["scientific_review"]["q4_minimum_predeclared_empirical_criteria"] = [
        "two quadrature families"
    ]
    rejected(candidate, "NP2 minimum criteria list is too thin to be a protocol")


@pytest.mark.parametrize(
    "needle,message",
    [
        ("independently generated", "NP2 does not require independent rule generation"),
        ("every theta anchor", "NP2 does not require agreement at every anchor"),
        ("retry-until-pass", "NP2 does not forbid retry-until-pass"),
    ],
)
def test_np2_criteria_must_retain_each_guard(record, needle, message):
    candidate = copy.deepcopy(record)
    criteria = norm(candidate)["scientific_review"]["q4_minimum_predeclared_empirical_criteria"]
    norm(candidate)["scientific_review"]["q4_minimum_predeclared_empirical_criteria"] = [
        entry for entry in criteria if needle not in entry.lower()
    ] + ["padding criterion"] * 3
    rejected(candidate, message)


def test_np2_still_requires_a_certified_theorem_rejected(record):
    candidate = copy.deepcopy(record)
    norm(candidate)["scientific_review"]["q1_paper_requires_a_certified_integration_theorem"][
        "answer"
    ] = "YES"
    rejected(candidate, "NP2 while still requiring a certified theorem")


def test_normalization_removed_from_probability_law_rejected(record):
    candidate = copy.deepcopy(record)
    norm(candidate)["normalization_remains_in_the_probability_law_contract"] = False
    rejected(candidate, "Normalization removed from the probability-law contract")


@pytest.mark.parametrize("banned", ["clipping", "absolute value", "deletion", "retry"])
def test_normalization_repair_prohibitions_must_survive(record, banned):
    candidate = copy.deepcopy(record)
    norm(candidate)["normalization_mandatory_properties"] = [
        entry
        for entry in norm(candidate)["normalization_mandatory_properties"]
        if banned not in entry.lower()
    ]
    rejected(candidate, f"Normalization policy stops forbidding {banned}")


def test_finite_positive_normalization_must_survive(record):
    candidate = copy.deepcopy(record)
    norm(candidate)["normalization_mandatory_properties"] = ["evaluated at every theta anchor"]
    rejected(candidate, "Finite normalization no longer mandatory")


def test_np3_without_compatibility_proof_rejected(record):
    candidate = copy.deepcopy(record)
    normalization = norm(candidate)
    normalization["decision"] = "NP3_REMOVE_NORMALIZATION_VALIDATION_FROM_PHASE2B"
    normalization["compatibility_with_normalized_law_proven"] = False
    normalization["rejected_alternatives"] = [
        {"option": option, "rejected_because": "n/a"}
        for option in VALIDATOR.NORMALIZATION_OPTIONS
        if option != "NP3_REMOVE_NORMALIZATION_VALIDATION_FROM_PHASE2B"
    ]
    rejected(
        candidate,
        "NP3 selected without proving compatibility with the normalized law",
        expected_outcome=None,
    )


def test_normalization_policy_changing_research_question_rejected(record):
    candidate = copy.deepcopy(record)
    norm(candidate)["contract_impact"]["by_scope"][
        "research_question"
    ] = "CHANGES_RESEARCH_QUESTION"
    rejected(candidate, "Normalization policy changes the research question")


# --------------------------------------------------------------------------
# adversarial: combined derivation and research question
# --------------------------------------------------------------------------


def test_pd1_without_ap1_rejected(record):
    candidate = copy.deepcopy(record)
    alpha(candidate)["decision"] = "AP4_ALPHA_POLICY_REMAINS_UNRESOLVED"
    with pytest.raises(VALIDATOR.ValidationError):
        VALIDATOR.validate(candidate, root=ROOT, check_docs=False, check_files=False)


def test_pd1_without_np2_rejected(record):
    candidate = copy.deepcopy(record)
    normalization = norm(candidate)
    normalization["decision"] = "NP4_NORMALIZATION_POLICY_REMAINS_UNRESOLVED"
    normalization["rejected_alternatives"] = [
        {
            "option": option,
            "rejected_because": "n/a",
            **(
                {"compatibility_with_normalized_law_proven": False}
                if option == "NP3_REMOVE_NORMALIZATION_VALIDATION_FROM_PHASE2B"
                else {}
            ),
        }
        for option in VALIDATOR.NORMALIZATION_OPTIONS
        if option != "NP4_NORMALIZATION_POLICY_REMAINS_UNRESOLVED"
    ]
    rejected(candidate, "PD1 declared without NP2")


def test_pd5_declared_while_policies_were_decided_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["combined_decision"]["code"] = "PD5_POLICY_DECISION_REMAINS_BLOCKED"
    rejected(
        candidate,
        "PD5 declared while a policy was in fact decided",
        expected_outcome=None,
    )


@pytest.mark.parametrize("key", VALIDATOR.RESEARCH_QUESTION_KEYS)
def test_policy_marked_preserving_while_changing_the_target_rejected(record, key):
    candidate = copy.deepcopy(record)
    candidate["combined_decision"]["research_question_check"][key] = False
    rejected(candidate, f"Research-question invariant {key} not preserved")


def test_combined_research_question_change_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["combined_decision"]["research_question_impact"] = "CHANGES_RESEARCH_QUESTION"
    rejected(candidate, "Combined decision changes the research question")


# --------------------------------------------------------------------------
# adversarial: paper impact and blockers
# --------------------------------------------------------------------------


def test_paper_must_not_list_cannot_lose_the_equivalence_prohibition(record):
    candidate = copy.deepcopy(record)
    candidate["paper_impact"]["must_not_claim"] = [
        entry
        for entry in candidate["paper_impact"]["must_not_claim"]
        if "equivalent" not in entry.lower()
    ]
    rejected(candidate, "Paper impact does not forbid the coupling-equivalence claim")


def test_paper_must_not_list_cannot_lose_the_continuum_prohibition(record):
    candidate = copy.deepcopy(record)
    candidate["paper_impact"]["must_not_claim"] = [
        entry
        for entry in candidate["paper_impact"]["must_not_claim"]
        if "continuum" not in entry.lower()
    ]
    rejected(candidate, "Paper impact does not forbid the continuum claims")


def test_successor_completeness_claimed_with_open_blocker_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["successor_plan_assessment"]["v4_completeness_achievable_now"] = True
    rejected(candidate, "Successor completeness claimed while a scientific blocker remains")


def test_v4_creation_flag_must_stay_false(record):
    candidate = copy.deepcopy(record)
    candidate["successor_plan_assessment"]["v4_not_created_in_this_task"] = False
    rejected(candidate, "V4 created in a policy task")


def test_blocker_inventory_cannot_shrink(record):
    candidate = copy.deepcopy(record)
    candidate["blocker_status_after_decision"] = candidate["blocker_status_after_decision"][:-1]
    rejected(candidate, "Blocker inventory changed")


def test_fonll_blocker_cannot_be_silently_dissolved(record):
    candidate = copy.deepcopy(record)
    for entry in candidate["blocker_status_after_decision"]:
        if entry["id"] == "BLOCKER_FONLL_REFERENCE_EXECUTION_SPEC":
            entry["status"] = "DISSOLVED_BY_POLICY"
    candidate["successor_plan_assessment"]["v4_completeness_achievable_now"] = True
    rejected(
        candidate,
        "outside the scope of this decision and cannot be dissolved by it",
        expected_outcome=None,
    )


@pytest.mark.parametrize(
    "identifier",
    [
        "BLOCKER_PROJECT_PRECISION_TARGET",
        "BLOCKER_GRID_GATE_SEMANTICS",
        "BLOCKER_MASSLESS_CANDIDATE_SIDE",
        "BLOCKER_NUMERICAL_RUNTIME_IDENTITY",
    ],
)
def test_out_of_scope_blockers_cannot_be_dissolved_by_this_decision(record, identifier):
    candidate = copy.deepcopy(record)
    for entry in candidate["blocker_status_after_decision"]:
        if entry["id"] == identifier:
            entry["status"] = "DISSOLVED_BY_POLICY"
    rejected(candidate, "outside the scope of this decision and cannot be dissolved by it")


def test_fonll_blocker_must_be_recorded_as_remaining(record):
    candidate = copy.deepcopy(record)
    for entry in candidate["blocker_status_after_decision"]:
        if entry["id"] == "BLOCKER_FONLL_REFERENCE_EXECUTION_SPEC":
            entry["status"] = "CONVERTED_TO_PLAN_AUTHORING_ITEM"
    rejected(
        candidate,
        "independent-reference blocker was retired by a decision that does not address it",
    )


# --------------------------------------------------------------------------
# adversarial: authorization and history
# --------------------------------------------------------------------------


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


def test_forbidden_physics_execution_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["execution_state"]["normalization_integrals_executed"] = True
    rejected(candidate, "Forbidden physics or downstream execution recorded")


def test_phase2a_changed_to_pass_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_state"]["phase2a_scientific_decision"] = "PASS"
    rejected(candidate, "Phase 2A decision changed")


def test_adr_status_change_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_state"]["adr_013_status"] = "Accepted"
    rejected(candidate, "ADR-013 status changed")


def test_heavy_flavor_contract_change_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["historical_state"]["heavy_flavor_contract"] = "FONLL-C NNLO"
    rejected(candidate, "Heavy-flavor contract changed")


def test_issue_55_state_change_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["github_target_state"]["gate_decision"] = "PASS"
    rejected(candidate, "Issue #55 target state changed")


def test_historical_artifact_mutation_detected(record):
    candidate = copy.deepcopy(record)
    candidate["predecessors"]["blocker_resolution_v1"]["sha256"] = "0" * 64
    rejected(candidate, "Predecessor hash changed for blocker_resolution_v1")


def test_blocker_resolution_outcome_rewrite_rejected(record):
    candidate = copy.deepcopy(record)
    candidate["predecessors"]["blocker_resolution_v1"]["historical_outcome"] = "BR1_ALL_RESOLVED"
    rejected(candidate, "Blocker-resolution historical outcome rewritten")


def test_rejected_tolerances_cannot_return(record):
    candidate = copy.deepcopy(record)
    candidate["remaining_scientific_limitations"].append("residual target 0.000125")
    rejected(candidate, "Rejected tolerance 0.000125 reintroduced")
