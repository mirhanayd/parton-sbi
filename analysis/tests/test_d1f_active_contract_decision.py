"""Semantic adversarial tests for the two-axis Phase 1B-D1F v3 decision."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Callable

import pytest

REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts/phase1bd_d1f_active_contract_decision.py"
SPEC = importlib.util.spec_from_file_location("d1f_decision", MODULE_PATH)
assert SPEC and SPEC.loader
d1f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(d1f)

A, B, C, D, E, F = d1f.OPTION_IDS


@pytest.fixture()
def record() -> dict:
    return d1f.build_record()


def rejected(record: dict) -> None:
    with pytest.raises(d1f.ContractDecisionError):
        d1f.validate_record(record)


def test_committed_artifact_is_valid_and_deterministic(record: dict) -> None:
    path = REPO / d1f.ARTIFACT
    committed = json.loads(path.read_text(encoding="utf-8"))
    d1f.validate_record(committed)
    assert committed == record
    assert path.read_text(encoding="utf-8") == d1f.serialized(record)


def test_corrected_current_line_evidence_derives_pause(record: dict) -> None:
    assert record["current_line_evidence"]["bounded_alternative_generator_path_exists"]["proposition_status"] == "NOT_EVALUATED"
    assert record["current_line_evidence"]["current_contract_preserved_by_continuation"]["proposition_status"] == "NOT_EVALUATED"
    assert d1f.derive_current_line_disposition(record) == "MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE"
    assert record["current_line_disposition"] == "MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE"


def test_no_separate_review_is_preferred(record: dict) -> None:
    assert d1f.derive_preferred_review(record) == "NONE"
    assert record["preferred_separate_contract_review"] == "NONE"
    assert not any(row["preferred_review_eligible"] for row in record["separate_review_eligibility"].values())


def test_lower_level_candidate_is_plausible_but_unpreferred(record: dict) -> None:
    option = record["options"][C]
    eligibility = record["separate_review_eligibility"][C]
    assert option["conceptual_reviewability"] == "INCOMPLETE_BUT_REVIEWABLE"
    assert option["candidate_status"] == "PLAUSIBLE_SEPARATE_REVIEW_CANDIDATE_REQUIRES_INDEPENDENT_EVIDENCE"
    assert not eligibility["independent_evidence_available"]
    assert not eligibility["unique_preference_supported"]


def test_lower_level_gate_and_obligations_remain_qualified(record: dict) -> None:
    assert record["normalized_measure_gate"][C]["status"] == "PASS_WITH_QUALIFICATION"
    obligations = record["options"][C]["proof_obligations"]
    assert {row["obligation_id"] for row in obligations} == set(d1f.LOWER_LEVEL_PROOF_OBLIGATIONS)
    assert all(row["status"] == "NOT_EVALUATED" for row in obligations)


def test_top_level_pause_is_independent_of_preferred_axis(record: dict) -> None:
    record["separate_review_eligibility"][B]["preferred_review_eligible"] = True
    assert d1f.derive_preferred_review(record) == B
    assert d1f.derive_current_line_disposition(record) == "MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE"
    assert d1f.derive_top_level_decision("MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE", B) == "MAINTAIN_CURRENT_CONTRACT_AND_PAUSE"


def test_issue_10_roadmap_and_d2_remain_blocked(record: dict) -> None:
    assert record["dependencies"]["issue_10"] == {"number": 10, "state": "OPEN_BLOCKED", "completed_by_lower_level_model": False, "authorization": "NOT_AUTHORIZED"}
    assert record["dependencies"]["D2"] == "BLOCKED_AND_UNAUTHORIZED"
    assert record["dependencies"]["roadmap"] == {"D2": "BLOCKED", "D3": "BACKLOG", "D4": "BACKLOG", "D5": "BACKLOG", "active_supersession": False}


def test_active_policy_is_pause_without_active_supersession(record: dict) -> None:
    assert record["active_operational_policy"] == "PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION"
    assert record["current_full_generator_line"] == "PAUSED_NO_BOUNDED_CONTINUATION_ESTABLISHED"
    assert record["lower_level_contract_review"] == "PLAUSIBLE_BUT_NOT_PREFERRED_OR_AUTHORIZED"
    assert set(record["supersession_matrix"]["current_line_active_effects"].values()) == {"CURRENT_STATE_PRESERVED"}


def test_all_authorization_flags_are_false(record: dict) -> None:
    assert set(record["authorization"]) == set(d1f.AUTHORIZATION_FLAGS)
    assert all(value is False for value in record["authorization"].values())


def m01(record: dict) -> None:
    cell = record["option_scorecards"][B]["detector_model_feasibility"]
    cell.update(status="SUPPORTED_WITH_QUALIFICATION", evidence_class="DIRECT_IMMUTABLE_EVIDENCE", load_bearing=True, evidence_bindings=[{"evidence_id": "D1F_CONCEPTUAL_REVIEW", "claim_key": "LOWER_LEVEL_FORM_IS_CONCEPTUALLY_COHERENT", "option_scope": [B], "criterion_scope": ["detector_model_feasibility"], "maximum_supported_status": "SUPPORTED_WITH_QUALIFICATION"}])


def m02(record: dict) -> None:
    cell = record["option_scorecards"][F]["end_to_end_scientific_mvp_path"]
    cell.update(status="SUPPORTED_WITH_QUALIFICATION", evidence_class="DIRECT_IMMUTABLE_EVIDENCE", load_bearing=False, evidence_bindings=[{"evidence_id": "D1F_CONCEPTUAL_REVIEW", "claim_key": "LOWER_LEVEL_FORM_IS_CONCEPTUALLY_COHERENT", "option_scope": [F], "criterion_scope": ["end_to_end_scientific_mvp_path"], "maximum_supported_status": "SUPPORTED_WITH_QUALIFICATION"}])


def m03(record: dict) -> None:
    record["option_scorecards"][C]["no_clipping_preservation"]["evidence_bindings"][0]["option_scope"] = [B]


def m04(record: dict) -> None:
    record["option_scorecards"][C]["no_clipping_preservation"]["evidence_bindings"][0]["criterion_scope"] = ["strict_support_preservation"]


def m05(record: dict) -> None:
    record["option_scorecards"][C]["calibration_feasibility"]["status"] = "SUPPORTED"


def m06(record: dict) -> None:
    for criterion in d1f.PREFERENCE_CRITICAL_CRITERIA:
        cell = record["option_scorecards"][C][criterion]
        cell.update(status="SUPPORTED_WITH_QUALIFICATION", evidence_class="DIRECT_IMMUTABLE_EVIDENCE", load_bearing=True, evidence_bindings=[{"evidence_id": "D1F_CONCEPTUAL_REVIEW", "claim_key": "LOWER_LEVEL_FORM_IS_CONCEPTUALLY_COHERENT", "option_scope": [C], "criterion_scope": [criterion], "maximum_supported_status": "SUPPORTED_WITH_QUALIFICATION"}])


def m07(record: dict) -> None:
    record["current_line_evidence"]["bounded_alternative_generator_path_exists"]["proposition_status"] = "NOT_SUPPORTED"


def m08(record: dict) -> None:
    record["current_line_evidence"]["current_contract_preserved_by_continuation"]["proposition_status"] = "NOT_SUPPORTED"


def m09(record: dict) -> None:
    record["current_line_disposition"] = "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING"
    record["decision"] = "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING"


def m10(record: dict) -> None:
    record["separate_review_eligibility"][C]["unique_preference_supported"] = True
    record["separate_review_eligibility"][C]["preferred_review_eligible"] = True
    record["preferred_separate_contract_review"] = C


def m11(record: dict) -> None:
    record["supersession_matrix"]["historical_negative_results"].pop("D1D_RESULT")


def m12(record: dict) -> None:
    record["next_step"]["action"] = "IMPLEMENT_LOWER_LEVEL_SIMULATOR"


def m13(record: dict) -> None:
    record["active_operational_policy"] = "CURRENT_PHASE1B_FULL_GENERATOR_LINE_TERMINATED"


def m14(record: dict) -> None:
    record["dependencies"]["issue_10"].update(state="CLOSED_COMPLETED", completed_by_lower_level_model=True)


def m15(record: dict) -> None:
    record["supersession_matrix"]["current_line_active_effects"]["ISSUE_10_FULL_GENERATOR_D2"] = "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED"


def m16(record: dict) -> None:
    record["options"][C]["proof_obligations"].pop()


def m17(record: dict) -> None:
    record["options"][C]["proof_obligations"][0]["status"] = "PASS"


def m18(record: dict) -> None:
    record["normalized_measure_gate"][C]["status"] = "PASS"


def m19(record: dict) -> None:
    record["options"][C]["full_generator_equivalence_claimed"] = True


def m20(record: dict) -> None:
    record["authorization"]["PROTOTYPE_AUTHORIZED"] = True


def m21(record: dict) -> None:
    record["authorization"]["D2_AUTHORIZED"] = True


def m22(record: dict) -> None:
    record["decision"] = "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING"


ADVERSARIAL_MUTATIONS: tuple[tuple[str, Callable[[dict], None]], ...] = (
    ("option_b_detector_uses_lower_level_claim", m01),
    ("option_f_mvp_uses_lower_level_claim", m02),
    ("binding_option_scope_changed", m03),
    ("binding_criterion_scope_changed", m04),
    ("maximum_supported_status_exceeded", m05),
    ("adr010_is_sole_option_c_preference_source", m06),
    ("alternative_path_unevaluated_promoted", m07),
    ("contract_preservation_unevaluated_promoted", m08),
    ("termination_retained_with_unevaluated_field", m09),
    ("option_c_selected_without_unique_support", m10),
    ("historical_negative_result_deleted", m11),
    ("next_step_action_becomes_implementation", m12),
    ("termination_policy_activated_during_pause", m13),
    ("issue_10_completed_by_lower_level_option", m14),
    ("hypothetical_supersession_activated", m15),
    ("option_c_obligation_removed", m16),
    ("option_c_obligation_promoted", m17),
    ("option_c_gate_promoted", m18),
    ("full_generator_equivalence_claimed", m19),
    ("prototype_authorized", m20),
    ("d2_authorized", m21),
    ("top_level_result_hardcoded_inconsistently", m22),
)


@pytest.mark.parametrize(("name", "mutate"), ADVERSARIAL_MUTATIONS)
def test_direct_semantic_mutation_is_rejected(record: dict, name: str, mutate: Callable[[dict], None]) -> None:
    del name
    mutate(record)
    rejected(record)
