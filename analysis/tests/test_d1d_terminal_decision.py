"""Focused regressions for the terminal D1D planning-decision contract."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "phase1bd_d1d_terminal_decision.py"
SPEC = importlib.util.spec_from_file_location("d1d_terminal_decision", MODULE_PATH)
assert SPEC and SPEC.loader
decision_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decision_module)


def artifact() -> dict:
    return json.loads((ROOT / decision_module.ARTIFACT).read_text(encoding="utf-8"))


def test_committed_artifact_matches_generator_and_validates() -> None:
    value = artifact()
    assert value == decision_module.build_decision()
    decision_module.validate_decision(value)


def test_decision_is_derived_as_inconclusive() -> None:
    value = artifact()
    assert decision_module.derive_decision(value["decision_rule"]) == "INCONCLUSIVE"
    assert value["decision"] == "INCONCLUSIVE"


def test_authorizing_decision_is_rejected() -> None:
    value = artifact()
    value["decision"] = "AUTHORIZE_PROTOTYPE"
    with pytest.raises(decision_module.DecisionError):
        decision_module.validate_decision(value)


@pytest.mark.parametrize("flag", decision_module.AUTHORIZATION_FLAGS)
def test_every_authorization_flag_must_remain_false(flag: str) -> None:
    value = artifact()
    value["authorization"][flag] = True
    with pytest.raises(decision_module.DecisionError):
        decision_module.validate_decision(value)


def test_all_four_architecture_classes_are_required() -> None:
    value = artifact()
    del value["architecture_assessments"][decision_module.ARCHITECTURES[0]]
    with pytest.raises(decision_module.DecisionError):
        decision_module.validate_decision(value)


def test_all_twenty_criteria_are_required() -> None:
    value = artifact()
    del value["decision_criteria"]["matrix"][decision_module.ARCHITECTURES[1]][decision_module.CRITERIA[0]]
    with pytest.raises(decision_module.DecisionError):
        decision_module.validate_decision(value)


def test_missing_primary_evidence_cannot_be_scored_as_support() -> None:
    value = artifact()
    candidate = value["architecture_assessments"][decision_module.ARCHITECTURES[2]]["candidates"][0]
    candidate["evidence_requirements"]["signed_pdf_scalar_preservation"]["status"] = "SUPPORTED"
    with pytest.raises(decision_module.DecisionError):
        decision_module.validate_decision(value)


def test_supported_matrix_score_requires_cited_evidence() -> None:
    value = artifact()
    entry = value["decision_criteria"]["matrix"][decision_module.ARCHITECTURES[2]]["hard_process_coverage"]
    entry["primary_source_ids"] = []
    with pytest.raises(decision_module.DecisionError):
        decision_module.validate_decision(value)


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("D1C_FINAL_DECISION", "PASS"),
        ("MINIMAL_PUBLIC_READER_PATCH", "SUFFICIENT"),
        ("PROVENANCE_SLICE_V1_DECISION", "PASS"),
        ("PROVENANCE_SLICE_V1_STATUS", "ACCEPTED"),
        ("D1D_A_FINAL_DECISION", "PASS"),
        ("D1D_A_FAILED_GATE", "none"),
        ("ARCHITECTURE_COMPARISON_READY", True),
    ],
)
def test_precedence_record_is_immutable(field: str, changed: object) -> None:
    value = artifact()
    value["precedence"][field] = changed
    with pytest.raises(decision_module.DecisionError):
        decision_module.validate_decision(value)


def test_reopen_conditions_do_not_authorize_work() -> None:
    value = artifact()
    value["reopen_conditions"][0]["authorization_granted"] = True
    with pytest.raises(decision_module.DecisionError):
        decision_module.validate_decision(value)


def test_terminal_stop_requires_both_evidentiary_conditions() -> None:
    value = artifact()
    rule = copy.deepcopy(value["decision_rule"])
    rule["potentially_coherent_route_remains"] = False
    rule["primary_or_mathematical_evidence_insufficient"] = False
    rule["no_current_architecture_has_coherent_bounded_path"] = True
    rule["disproportionate_cost_supported_for_all_routes"] = True
    assert decision_module.derive_decision(rule) == "DO_NOT_AUTHORIZE_FURTHER_GENERATOR_PROTOTYPE"


def test_ambiguous_rule_inputs_are_rejected() -> None:
    value = artifact()
    rule = copy.deepcopy(value["decision_rule"])
    rule["potentially_coherent_route_remains"] = False
    with pytest.raises(decision_module.DecisionError):
        decision_module.derive_decision(rule)
