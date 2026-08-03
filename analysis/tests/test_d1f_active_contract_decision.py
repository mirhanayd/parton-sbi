"""Adversarial tests for the two-axis Phase 1B-D1F v2 decision."""

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


def test_current_line_disposition_is_independently_derived(record: dict) -> None:
    assert d1f.derive_current_line_disposition(record) == (
        "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING"
    )
    assert record["current_line_disposition"] == (
        "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING"
    )


def test_preferred_separate_review_is_independently_derived(record: dict) -> None:
    assert d1f.derive_preferred_review(record) == C
    assert record["preferred_separate_contract_review"] == C
    assert record["separate_review_eligibility"][C]["preferred_review_eligible"]
    assert not any(
        record["separate_review_eligibility"][option]["preferred_review_eligible"]
        for option in (B, D, E)
    )


def test_lower_level_measure_gate_remains_qualified(record: dict) -> None:
    assert record["normalized_measure_gate"][C]["status"] == (
        "PASS_WITH_QUALIFICATION"
    )
    assert all(
        row["status"] == "NOT_EVALUATED"
        for row in record["options"][C]["proof_obligations"]
    )


def test_top_level_decision_follows_current_line_axis(record: dict) -> None:
    assert record["decision"] == "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING"
    assert d1f.derive_top_level_decision(
        record["current_line_disposition"],
        record["preferred_separate_contract_review"],
    ) == record["decision"]


def test_all_authorization_flags_are_false(record: dict) -> None:
    assert set(record["authorization"]) == set(d1f.AUTHORIZATION_FLAGS)
    assert all(value is False for value in record["authorization"].values())


def test_issue_10_and_d2_remain_blocked(record: dict) -> None:
    assert record["dependencies"]["issue_10"] == {
        "number": 10,
        "state": "OPEN_BLOCKED",
        "completed_by_lower_level_model": False,
        "authorization": "NOT_AUTHORIZED",
    }
    assert record["dependencies"]["D2"] == "BLOCKED_AND_UNAUTHORIZED"


def m01(record: dict) -> None:
    record["normalized_measure_gate"][A]["status"] = "PASS"


def m02(record: dict) -> None:
    record["normalized_measure_gate"][C]["status"] = "PASS"


def m03(record: dict) -> None:
    record["options"][C]["proof_obligations"].pop()


def m04(record: dict) -> None:
    record["options"][C]["complete_rate_positivity_proven"] = True


def m05(record: dict) -> None:
    record["options"][C]["detector_kernel_normalization_proven"] = True


def m06(record: dict) -> None:
    record["separate_review_eligibility"][C]["credible_mvp_path_status"] = (
        "SUPPORTED"
    )


def m07(record: dict) -> None:
    record["separate_review_eligibility"][D]["objective_change_status"] = (
        "SUPPORTED"
    )


def m08(record: dict) -> None:
    record["derived_decision_inputs"][
        "current_objective_remains_scientifically_worth_preserving"
    ] = True


def m09(record: dict) -> None:
    record["options"][C]["relationship_to_current_line"] = (
        "CURRENT_LINE_CONTINUATION"
    )


def m10(record: dict) -> None:
    record["termination_scope"]["historical_negative_evidence_preserved"] = False


def m11(record: dict) -> None:
    record["dependencies"]["issue_10"]["completed_by_lower_level_model"] = True


def m12(record: dict) -> None:
    record["option_scorecards"][C]["detector_model_feasibility"]["status"] = (
        "SUPPORTED"
    )


def m13(record: dict) -> None:
    generic = "One generic rationale is repeated and does not distinguish the criterion-specific evidence or its implications."
    for cell in record["option_scorecards"][C].values():
        cell["criterion_specific_rationale"] = generic


def m14(record: dict) -> None:
    record["supersession_matrix"]["redesign_option_effects"][C] = {}


def m15(record: dict) -> None:
    record["options"][C]["smallest_falsifiable_next_step"]["status"] = (
        "OPEN_ENDED_RESEARCH"
    )


def m16(record: dict) -> None:
    record["preferred_separate_contract_review"] = E


def m17(record: dict) -> None:
    record["current_line_evidence"]["bounded_static_evidence_path_exists"][
        "status"
    ] = "SUPPORTED"


def m18(record: dict) -> None:
    record["authorization"]["LOWER_LEVEL_SIMULATOR_AUTHORIZED"] = True


def m19(record: dict) -> None:
    record["authorization"]["EVENT_GENERATION_AUTHORIZED"] = True


def m20(record: dict) -> None:
    record["authorization"]["D2_AUTHORIZED"] = True


def m21(record: dict) -> None:
    record["next_step"]["action"] = "IMPLEMENT_LOWER_LEVEL_SIMULATOR"
    record["next_step"]["implementation"] = True


def m22(record: dict) -> None:
    record["decision"] = "RECOMMEND_LOWER_LEVEL_HARD_EVENT_CONTRACT_REVIEW"


ADVERSARIAL_MUTATIONS: tuple[tuple[str, Callable[[dict], None]], ...] = (
    ("option_a_unqualified_pass", m01),
    ("option_c_unqualified_pass", m02),
    ("lower_level_obligation_removed", m03),
    ("complete_rate_positivity_prematurely_proven", m04),
    ("detector_kernel_normalization_prematurely_proven", m05),
    ("mvp_status_manually_forced", m06),
    ("risk_status_manually_forced", m07),
    ("unconditional_preserve_boolean_added", m08),
    ("redesign_claimed_as_current_line_continuation", m09),
    ("termination_deletes_historical_negative", m10),
    ("lower_level_claims_issue_10_completion", m11),
    ("criterion_score_changed_without_claim", m12),
    ("generic_rationale_reused", m13),
    ("prospective_supersession_removed", m14),
    ("bounded_planning_review_removed", m15),
    ("signed_weight_research_selected", m16),
    ("current_line_bounded_without_evidence", m17),
    ("lower_level_simulator_authorized", m18),
    ("event_generation_authorized", m19),
    ("d2_authorized", m20),
    ("next_step_becomes_implementation", m21),
    ("top_level_decision_inconsistent", m22),
)


@pytest.mark.parametrize(("name", "mutate"), ADVERSARIAL_MUTATIONS)
def test_direct_semantic_mutation_is_rejected(
    record: dict, name: str, mutate: Callable[[dict], None]
) -> None:
    del name
    mutate(record)
    rejected(record)
