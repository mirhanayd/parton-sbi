"""Adversarial tests for the planning-only Phase 1B-D1F decision."""

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


def test_exactly_six_complete_option_contracts(record: dict) -> None:
    assert set(record["options"]) == set(d1f.OPTION_IDS)
    for option in record["options"].values():
        assert set(d1f.CONTRACT_FIELDS).issubset(option)


def test_all_twenty_criterion_scorecards_are_complete(record: dict) -> None:
    for card in record["option_scorecards"].values():
        assert set(card) == set(d1f.CRITERIA)
    assert record["validation"]["score_totals"] == d1f.score_totals(
        record["option_scorecards"]
    )


def test_decision_is_derived_from_serialized_evidence(record: dict) -> None:
    assert d1f.derive_decision(record) == (
        "RECOMMEND_LOWER_LEVEL_HARD_EVENT_CONTRACT_REVIEW"
    )
    assert record["derived_decision_inputs"]["eligible_redesign_options"] == [
        "LOWER_LEVEL_DIS_HARD_EVENT_MODEL"
    ]


def test_all_authorization_flags_are_false(record: dict) -> None:
    assert set(record["authorization"]) == set(d1f.AUTHORIZATION_FLAGS)
    assert all(value is False for value in record["authorization"].values())


def m01(record: dict) -> None:
    record["options"][d1f.OPTION_IDS[2]]["normalized_probability_measure"][
        "status"
    ] = "NOT_SUPPORTED"


def m02(record: dict) -> None:
    record["options"][d1f.OPTION_IDS[2]]["posterior_target"]["status"] = (
        "NOT_SUPPORTED"
    )


def m03(record: dict) -> None:
    record["options"][d1f.OPTION_IDS[4]]["signed_weights_are_probabilities"] = True


def m04(record: dict) -> None:
    record["options"][d1f.OPTION_IDS[3]]["observed_event_set_representation"][
        "statement"
    ] = "Treat weighted events as ordinary iid unweighted events."


def m05(record: dict) -> None:
    record["options"][d1f.OPTION_IDS[1]]["active_pdf_family_identity"][
        "statement"
    ] = "Correct D0R in place to force nonnegativity."


def m06(record: dict) -> None:
    record["options"][d1f.OPTION_IDS[2]]["issue_roadmap_implications"][
        "statement"
    ] = "This completes issue #10 under its existing contract."


def m07(record: dict) -> None:
    record["supersession_matrix"]["ADR-003_EVENT_SAMPLING_SEMANTICS"][
        d1f.OPTION_IDS[3]
    ] = "PRESERVED"


def m08(record: dict) -> None:
    record["precedence"]["D1D_A_FINAL_DECISION"] = "PASS"


def m09(record: dict) -> None:
    record["options"][d1f.OPTION_IDS[2]][
        "hidden_clipping_or_semantic_repair"
    ] = True


def m10(record: dict) -> None:
    record["options"][d1f.OPTION_IDS[2]]["calibration_coverage_target"][
        "status"
    ] = "UNRESOLVED"


def m11(record: dict) -> None:
    record["authorization"]["LOWER_LEVEL_SIMULATOR_AUTHORIZED"] = True


def m12(record: dict) -> None:
    record["authorization"]["D2_AUTHORIZED"] = True


def m13(record: dict) -> None:
    record["decision"] = "MAINTAIN_CURRENT_CONTRACT_AND_PAUSE"


def m14(record: dict) -> None:
    record["supersession_matrix"]["ISSUE_10_FULL_GENERATOR_D2"][
        d1f.OPTION_IDS[2]
    ] = "PRESERVED"


def m15(record: dict) -> None:
    record["next_step"]["action"] = "IMPLEMENT_LOWER_LEVEL_SIMULATOR"
    record["next_step"]["implementation"] = True


ADVERSARIAL_MUTATIONS: tuple[tuple[str, Callable[[dict], None]], ...] = (
    ("recommend_without_normalized_measure", m01),
    ("recommend_without_posterior", m02),
    ("signed_weights_as_probabilities", m03),
    ("weighted_events_as_iid", m04),
    ("d0r_silently_replaced", m05),
    ("lower_level_claims_issue_10_complete", m06),
    ("weighted_set_omits_adr_003_supersession", m07),
    ("historical_negative_removed", m08),
    ("recommended_option_clips", m09),
    ("recommend_without_calibration", m10),
    ("implementation_authorization_true", m11),
    ("d2_authorization_true", m12),
    ("decision_hardcoded_against_scorecard", m13),
    ("supersession_matrix_changed", m14),
    ("planning_step_becomes_implementation", m15),
)


@pytest.mark.parametrize(("name", "mutate"), ADVERSARIAL_MUTATIONS)
def test_adversarial_mutation_is_rejected(
    record: dict, name: str, mutate: Callable[[dict], None]
) -> None:
    del name
    mutate(record)
    rejected(record)
