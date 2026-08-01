"""Adversarial tests for the planning-only D1E feasibility contract."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts/phase1bd_d1e_consumer_graph_feasibility.py"
SPEC = importlib.util.spec_from_file_location("d1e_feasibility", MODULE_PATH)
assert SPEC and SPEC.loader
d1e = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(d1e)


@pytest.fixture()
def record() -> dict:
    return d1e.build_record(REPO)


def rejected(record: dict) -> None:
    with pytest.raises(d1e.FeasibilityError):
        d1e.validate_record(record, REPO)


def test_committed_artifact_is_valid_and_deterministic(record: dict) -> None:
    path = REPO / d1e.ARTIFACT
    committed = json.loads(path.read_text(encoding="utf-8"))
    d1e.validate_record(committed, REPO)
    assert committed == record
    assert path.read_text(encoding="utf-8") == json.dumps(
        record, indent=2, sort_keys=True
    ) + "\n"


def test_ignored_source_checkout_is_optional_in_clean_ci(tmp_path: Path) -> None:
    assert d1e.verify_source_bytes_when_available(tmp_path, []) is False


def test_feasible_without_pinned_toolchain_fails(record: dict) -> None:
    record["selected_toolchain"] = None
    rejected(record)


def test_feasible_without_compile_command_strategy_fails(record: dict) -> None:
    record["compilation_database_contract"]["strategy"] = "UNDEFINED"
    rejected(record)


def test_feasible_above_implementation_cost_cap_fails(record: dict) -> None:
    record["cost_bound"]["implementation_total_person_weeks"] = 8.25
    record["cost_bound"]["tests_person_weeks"] = 2.25
    rejected(record)


def test_feasible_above_review_cost_cap_fails(record: dict) -> None:
    record["cost_bound"]["independent_review_person_weeks"] = 2.25
    rejected(record)


def test_global_name_fallback_fails(record: dict) -> None:
    record["graph_root_contract"]["prohibitions"][
        "global_xf_pdf_pdfptr_fallback"
    ] = True
    rejected(record)


def test_historical_evidence_used_as_root_seed_fails(record: dict) -> None:
    record["calibration_contract"]["may_seed_roots"] = True
    rejected(record)


def test_historical_evidence_used_as_identifier_seed_fails(record: dict) -> None:
    record["calibration_contract"]["may_seed_identifiers"] = True
    rejected(record)


def test_synthetic_root_to_unit_edge_fails(record: dict) -> None:
    record["graph_edge_contract"]["direct_root_to_unit_synthetic_edge_allowed"] = True
    rejected(record)


def test_unresolved_critical_alias_represented_as_closure_fails(record: dict) -> None:
    record["unresolved_evidence_contract"][
        "unresolved_may_satisfy_supported_edge"
    ] = True
    rejected(record)


def test_runtime_pointer_installation_represented_as_static_fails(record: dict) -> None:
    row = record["static_runtime_boundary"]["runtime_only_properties"][0]
    assert row["property"] == "actual_runtime_pointer_installation"
    row["statically_proven"] = True
    rejected(record)


def test_runtime_evidence_cannot_satisfy_static_gate(record: dict) -> None:
    record["static_runtime_boundary"]["runtime_evidence_may_satisfy_static_gate"] = True
    rejected(record)


def test_missing_interprocedural_flow_gate_fails(record: dict) -> None:
    record["acceptance_gates"] = [
        gate
        for gate in record["acceptance_gates"]
        if gate["gate_id"] != "G07_INTERPROCEDURAL_ARGUMENT_PARAMETER_RETURN_FLOW"
    ]
    rejected(record)


def test_missing_holdout_recovery_gate_fails(record: dict) -> None:
    record["acceptance_gates"] = [
        gate
        for gate in record["acceptance_gates"]
        if gate["gate_id"]
        != "G13_HOLDOUT_RECOVERY_ZERO_UNRESOLVED_OR_NOT_RECOVERED"
    ]
    rejected(record)


@pytest.mark.parametrize("flag", d1e.AUTHORIZATION_FLAGS)
def test_every_true_authorization_flag_fails(record: dict, flag: str) -> None:
    record["authorization"][flag] = True
    rejected(record)


def test_d2_authorization_in_precedence_fails(record: dict) -> None:
    record["precedence"]["D2_AUTHORIZED"] = True
    rejected(record)


def test_inconclusive_with_implementation_next_step_fails(record: dict) -> None:
    record["decision"] = "INCONCLUSIVE"
    record["selected_toolchain"] = None
    record["next_step"]["action"] = "IMPLEMENT_GRAPH"
    rejected(record)


def test_do_not_proceed_with_selected_toolchain_fails(record: dict) -> None:
    record["decision"] = "DO_NOT_PROCEED"
    rejected(record)


def test_installed_mirror_cannot_create_semantic_nodes(record: dict) -> None:
    record["authoritative_source_contract"]["installed_mirror"][
        "semantic_node_policy"
    ] = "INCLUDE_AS_DUPLICATE_NODES"
    rejected(record)


def test_missing_translation_unit_fails(record: dict) -> None:
    record["authoritative_source_contract"][
        "translation_unit_semantic_file_ids"
    ].pop()
    rejected(record)


def test_all_sixteen_pointer_roles_are_required(record: dict) -> None:
    record["graph_root_contract"]["sixteen_pointer_roles"].pop()
    rejected(record)


def test_same_line_control_admission_fails(record: dict) -> None:
    record["negative_controls"]["co_located_line_admission_allowed"] = True
    rejected(record)


def test_issue_10_must_remain_blocked(record: dict) -> None:
    record["dependencies"]["blocked_downstream_issue"]["state"] = "OPEN"
    rejected(record)


def test_feasibility_decision_is_derived(record: dict) -> None:
    assert d1e.derive_decision(record) == "FEASIBLE_FOR_SEPARATE_STATIC_EVIDENCE_TASK"
    record["decision"] = "INCONCLUSIVE"
    rejected(record)


def test_planning_validation_records_no_parser_or_graph_execution(record: dict) -> None:
    for key in (
        "parser_or_graph_execution_performed",
        "compile_database_generated",
        "production_graph_nodes_or_edges_generated",
    ):
        record["validation"][key] = True
        rejected(record)
        record = d1e.build_record(REPO)
