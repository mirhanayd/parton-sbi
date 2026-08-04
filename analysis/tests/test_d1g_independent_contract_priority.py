"""Adversarial tests for the Phase 1B-D1G primary-evidence decision."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Callable

import pytest

REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts/phase1bd_d1g_independent_contract_priority.py"
SPEC = importlib.util.spec_from_file_location("d1g_decision", MODULE_PATH)
assert SPEC and SPEC.loader
d1g = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(d1g)

B, C, D, E = d1g.CANDIDATES


@pytest.fixture()
def record() -> dict:
    return d1g.build_record()


def rejected(record: dict) -> None:
    with pytest.raises(d1g.D1GDecisionError):
        d1g.validate_record(record)


def test_committed_artifact_is_valid_and_deterministic(record: dict) -> None:
    path = REPO / d1g.ARTIFACT
    actual_text = path.read_text(encoding="utf-8")
    actual = json.loads(actual_text)
    d1g.validate_record(actual)
    assert actual == record
    assert actual_text == d1g.serialized(record)


def test_source_bounds_and_primary_identities(record: dict) -> None:
    sources = record["external_source_registry"]
    assert len(sources) == 13
    assert record["validation"]["source_count_per_candidate"] == {B: 3, C: 4, D: 3, E: 3}
    assert all(row["primary_source_status"] == "PRIMARY_SOURCE_CONFIRMED" for row in sources.values())


def test_candidate_c_is_uniquely_eligible(record: dict) -> None:
    assert record["derived_decision_inputs"]["eligible_candidates"] == [C]
    assert record["decision"] == "PRIORITIZE_LOWER_LEVEL_DIS_CONTRACT_REVIEW"
    assert d1g.derive_decision(record["candidate_eligibility"]) == record["decision"]


def test_option_c_obligations_remain_unevaluated(record: dict) -> None:
    obligations = record["candidates"][C]["proof_obligations"]
    assert [row["obligation_id"] for row in obligations] == list(d1g.OPTION_C_OBLIGATIONS)
    assert all(row["status"] == "NOT_EVALUATED" for row in obligations)


def test_authorization_and_roadmap_remain_frozen(record: dict) -> None:
    assert set(record["authorization"]) == set(d1g.AUTHORIZATION_FLAGS)
    assert all(value is False for value in record["authorization"].values())
    assert record["dependencies"]["issue_10"]["state"] == "OPEN_BLOCKED"
    assert record["dependencies"]["D2"] == "BLOCKED_AND_UNAUTHORIZED"
    assert record["dependencies"]["roadmap"] == {"D2": "BLOCKED", "D3": "BACKLOG", "D4": "BACKLOG", "D5": "BACKLOG", "active_supersession": False}


def m_secondary_source(record: dict) -> None:
    record["external_source_registry"]["C_HERA_COMBINED_DIS"]["primary_source_status"] = "SECONDARY_SOURCE"


def m_source_identity(record: dict) -> None:
    record["external_source_registry"]["C_HERA_COMBINED_DIS"]["exact_version"] = "v2"


def m_source_limitation(record: dict) -> None:
    record["external_source_registry"]["D_IMPORTANCE_ESS"]["limitations"] = ""


def m_wrong_candidate(record: dict) -> None:
    record["criterion_scorecards"][C]["scientific_motivation"]["evidence_bindings"][0]["option_scope"] = [B]


def m_wrong_criterion(record: dict) -> None:
    record["criterion_scorecards"][C]["calibration_and_coverage"]["evidence_bindings"][0]["criterion_scope"] = ["reproducibility"]


def m_exceed_maximum(record: dict) -> None:
    record["criterion_scorecards"][B]["scientific_motivation"]["status"] = "SUPPORTED"


def m_adr010_independent(record: dict) -> None:
    record["criterion_scorecards"][C]["scientific_motivation"]["evidence_bindings"][0]["source_id"] = "ADR010"


def m_adr011_self_reference(record: dict) -> None:
    record["criterion_scorecards"][C]["scientific_motivation"]["evidence_bindings"][0]["source_id"] = "ADR011"


def m_hypothesis_load_bearing(record: dict) -> None:
    cell = record["criterion_scorecards"][B]["normalized_observation_measure"]
    cell["evidence_class"] = "PROSPECTIVE_HYPOTHESIS"
    cell["load_bearing"] = True


def m_select_without_normalized_measure(record: dict) -> None:
    record["candidate_eligibility"][B] = {"eligible": True, "failed_or_unavailable_gates": []}
    record["decision"] = d1g.OUTCOMES[B]


def m_select_without_posterior(record: dict) -> None:
    record["candidate_eligibility"][D] = {"eligible": True, "failed_or_unavailable_gates": []}
    record["decision"] = d1g.OUTCOMES[D]


def m_select_without_independent_motivation(record: dict) -> None:
    cell = record["criterion_scorecards"][C]["scientific_motivation"]
    cell.update(status="PRIMARY_EVIDENCE_UNAVAILABLE", evidence_class="PRIMARY_EVIDENCE_UNAVAILABLE", evidence_bindings=[], explicit_inference=None, load_bearing=False)


def m_candidate_c_mvp_without_evidence(record: dict) -> None:
    cell = record["criterion_scorecards"][C]["credible_end_to_end_mvp_path"]
    cell.update(status="PRIMARY_EVIDENCE_UNAVAILABLE", evidence_class="PRIMARY_EVIDENCE_UNAVAILABLE", evidence_bindings=[], explicit_inference=None, load_bearing=False)


def m_option_c_obligation_pass(record: dict) -> None:
    record["candidates"][C]["proof_obligations"][0]["status"] = "PASS"


def m_option_c_obligation_removed(record: dict) -> None:
    record["candidates"][C]["proof_obligations"].pop()


def m_weighted_as_iid(record: dict) -> None:
    record["candidates"][D]["treated_as_iid_unweighted_events"] = True


def m_signed_as_probability(record: dict) -> None:
    record["candidates"][E]["signed_weights_are_probabilities"] = True


def m_new_family_as_correction(record: dict) -> None:
    record["candidates"][B]["not_a_D0R_correction"] = False


def m_c_completes_issue10(record: dict) -> None:
    record["candidates"][C]["issue_10_completed"] = True


def m_force_preference_with_two(record: dict) -> None:
    record["candidate_eligibility"][B] = {"eligible": True, "failed_or_unavailable_gates": []}


def m_force_preference_with_none(record: dict) -> None:
    record["candidate_eligibility"][C] = {"eligible": False, "failed_or_unavailable_gates": ["credible_MVP_path"]}


def m_issue10_state(record: dict) -> None:
    record["dependencies"]["issue_10"]["state"] = "CLOSED"


def m_d2_state(record: dict) -> None:
    record["dependencies"]["D2"] = "AUTHORIZED"


def m_roadmap_supersession(record: dict) -> None:
    record["dependencies"]["roadmap"]["active_supersession"] = True


def m_authorization(record: dict) -> None:
    record["authorization"]["LOWER_LEVEL_SIMULATOR_AUTHORIZED"] = True


def m_next_step_implementation(record: dict) -> None:
    record["next_step"].update(action="IMPLEMENT_LOWER_LEVEL_DIS_SIMULATOR", implementation=True, authorization_granted=True)


ADVERSARIAL_MUTATIONS: tuple[tuple[str, Callable[[dict], None]], ...] = (
    ("secondary_source_load_bearing", m_secondary_source),
    ("source_identity_changed", m_source_identity),
    ("source_limitation_removed", m_source_limitation),
    ("source_bound_to_wrong_candidate", m_wrong_candidate),
    ("source_bound_to_wrong_criterion", m_wrong_criterion),
    ("maximum_supported_status_exceeded", m_exceed_maximum),
    ("adr010_used_as_independent_evidence", m_adr010_independent),
    ("adr011_self_reference", m_adr011_self_reference),
    ("hypothesis_made_load_bearing", m_hypothesis_load_bearing),
    ("candidate_selected_without_normalized_measure", m_select_without_normalized_measure),
    ("candidate_selected_without_posterior", m_select_without_posterior),
    ("candidate_selected_without_independent_motivation", m_select_without_independent_motivation),
    ("candidate_c_selected_without_mvp_evidence", m_candidate_c_mvp_without_evidence),
    ("option_c_obligation_promoted", m_option_c_obligation_pass),
    ("option_c_obligation_removed", m_option_c_obligation_removed),
    ("weighted_events_treated_as_iid", m_weighted_as_iid),
    ("signed_weights_treated_as_probability", m_signed_as_probability),
    ("new_family_treated_as_d0r_correction", m_new_family_as_correction),
    ("candidate_c_completes_issue10", m_c_completes_issue10),
    ("preference_forced_with_two_eligible", m_force_preference_with_two),
    ("preference_forced_with_no_eligible", m_force_preference_with_none),
    ("issue10_state_changed", m_issue10_state),
    ("d2_state_changed", m_d2_state),
    ("roadmap_supersession_activated", m_roadmap_supersession),
    ("authorization_flag_true", m_authorization),
    ("next_step_becomes_implementation", m_next_step_implementation),
)


@pytest.mark.parametrize(("name", "mutate"), ADVERSARIAL_MUTATIONS)
def test_adversarial_mutation_is_rejected(record: dict, name: str, mutate: Callable[[dict], None]) -> None:
    del name
    mutate(record)
    rejected(record)


def test_unique_priority_rule_pauses_for_tie(record: dict) -> None:
    eligibility = {candidate: {"eligible": candidate in {B, C}, "failed_or_unavailable_gates": []} for candidate in d1g.CANDIDATES}
    assert d1g.derive_decision(eligibility) == d1g.PAUSE_OUTCOME


def test_unique_priority_rule_pauses_for_zero_eligible(record: dict) -> None:
    del record
    eligibility = {candidate: {"eligible": False, "failed_or_unavailable_gates": ["normalized_measure_reviewability"]} for candidate in d1g.CANDIDATES}
    assert d1g.derive_decision(eligibility) == d1g.PAUSE_OUTCOME
