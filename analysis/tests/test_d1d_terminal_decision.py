"""Adversarial regressions for the evidence-derived D1D-B decision."""

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


def affirmative_not_supported(*, cost: bool = False) -> dict:
    return decision_module.score(
        "NOT_SUPPORTED",
        "The test route is affirmatively incompatible with the scoped criterion.",
        "A pinned merged decision is used only as a deterministic adversarial fixture.",
        "The pinned evidence affirmatively blocks the route and it cannot satisfy the criterion.",
        ("D1D_DECISION",),
        ("authorization_hierarchy_blocks_prototype",),
        disproportionate_cost_evidence=cost,
    )


def refresh_derived(value: dict) -> None:
    candidates = value["architecture_assessments"][decision_module.ARCH_C]["candidate_matrices"]
    value["decision_criteria"]["matrix"][decision_module.ARCH_C] = decision_module.aggregate_candidate_matrices(candidates)
    states = decision_module.recompute_route_states(value)
    value["route_states"] = states["architecture_route_states"]
    assessment = value["architecture_assessments"][decision_module.ARCH_C]
    assessment["candidate_route_states"] = states["candidate_route_states"]
    assessment["candidate_critical_status_counts"] = {
        candidate_id: decision_module.critical_status_counts(candidates[candidate_id])
        for candidate_id in decision_module.CANDIDATE_IDS
    }
    value["decision_rule"] = decision_module.recompute_decision_rule(value)


def test_committed_v2_artifact_validates() -> None:
    value = artifact()
    assert value["schema_version"] == decision_module.SCHEMA
    decision_module.validate_decision(value)


def test_generator_is_deterministic() -> None:
    assert decision_module.build_decision() == decision_module.build_decision()
    assert artifact() == decision_module.build_decision()


def test_critical_candidate_score_recomputes_route_state() -> None:
    value = artifact()
    sherpa = value["architecture_assessments"][decision_module.ARCH_C]["candidate_matrices"][decision_module.CANDIDATE_IDS[0]]
    assert decision_module.route_state_from_row(sherpa) == "COHERENT_BOUNDED_PATH_POSSIBLE_WITH_EVIDENCE_GAPS"
    sherpa["signed_scalar_preservation"] = affirmative_not_supported()
    assert decision_module.route_state_from_row(sherpa) == "COHERENT_BOUNDED_PATH_NOT_SUPPORTED"
    with pytest.raises(decision_module.DecisionError):
        decision_module.validate_decision(value)


def test_all_architecture_c_critical_criteria_not_supported_rejects_inconclusive() -> None:
    value = artifact()
    candidates = value["architecture_assessments"][decision_module.ARCH_C]["candidate_matrices"]
    for row in candidates.values():
        for criterion in decision_module.CRITICAL_CRITERIA:
            row[criterion] = affirmative_not_supported(cost=criterion == "bounded_prototype_falsifiability")
    refresh_derived(value)
    assert value["decision_rule"]["potentially_coherent_route_remains"] is False
    value["decision"] = "INCONCLUSIVE"
    value["current_operational_policy"] = "PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION"
    with pytest.raises(decision_module.DecisionError):
        decision_module.validate_decision(value)


def test_missing_evidence_rationale_cannot_be_relabelled_not_supported() -> None:
    value = artifact()
    cell = value["architecture_assessments"][decision_module.ARCH_C]["candidate_matrices"][decision_module.CANDIDATE_IDS[0]]["signed_scalar_preservation"]
    cell["status"] = "NOT_SUPPORTED"
    cell["epistemic_basis"] = "AFFIRMATIVE_INCOMPATIBILITY_EVIDENCE"
    cell["claim_keys"] = ["external_pdf_calculate_getxpdf_accessor_availability"]
    with pytest.raises(decision_module.DecisionError, match="only reports missing evidence"):
        decision_module.validate_decision(value)


def test_affirmative_incompatibility_cannot_be_labelled_evidence_unavailable() -> None:
    value = artifact()
    cell = value["architecture_assessments"][decision_module.ARCH_C]["candidate_matrices"][decision_module.CANDIDATE_IDS[2]]["isr_sudakov_coverage"]
    cell["status"] = "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE"
    cell["epistemic_basis"] = "BOUNDED_REVIEW_EVIDENCE_GAP"
    with pytest.raises(decision_module.DecisionError, match="claims affirmative incompatibility"):
        decision_module.validate_decision(value)


def test_supported_score_rejects_unpinned_master_source() -> None:
    value = artifact()
    source = copy.deepcopy(value["evaluated_evidence"]["primary_sources"]["SHERPA_301_SOURCE_COMMIT"])
    source["source_id"] = "MUTABLE_SHERPA_MASTER"
    source["canonical_url"] = "https://gitlab.com/sherpa-team/sherpa/-/tree/master"
    source["source_identity_status"] = "SOURCE_IDENTITY_UNRESOLVED"
    value["evaluated_evidence"]["primary_sources"]["MUTABLE_SHERPA_MASTER"] = source
    cell = value["architecture_assessments"][decision_module.ARCH_C]["candidate_matrices"][decision_module.CANDIDATE_IDS[0]]["build_deployment_reproducibility"]
    cell["source_ids"] = ["MUTABLE_SHERPA_MASTER"]
    cell["claim_keys"] = ["source_commit_availability"]
    with pytest.raises(decision_module.DecisionError, match="mutable master"):
        decision_module.validate_decision(value)


def test_architecture_c_aggregate_cannot_be_altered_independently() -> None:
    value = artifact()
    value["decision_criteria"]["matrix"][decision_module.ARCH_C]["hard_process_coverage"]["claim"] = "manually promoted"
    with pytest.raises(decision_module.DecisionError, match="aggregate differs"):
        decision_module.validate_decision(value)


def test_manual_potentially_coherent_rule_override_is_rejected() -> None:
    value = artifact()
    value["decision_rule"]["potentially_coherent_route_remains"] = False
    with pytest.raises(decision_module.DecisionError, match="decision-rule booleans"):
        decision_module.validate_decision(value)


def test_sherpa_hera_example_alone_cannot_claim_complete_gamma_z() -> None:
    value = artifact()
    sherpa = value["architecture_assessments"][decision_module.ARCH_C]["candidate_matrices"][decision_module.CANDIDATE_IDS[0]]
    sherpa["full_neutral_current_gamma_z_compatibility"] = decision_module.score(
        "SUPPORTED",
        "The HERA example proves the complete gamma/Z/interference contract.",
        "The claim relies only on the HERA YAML.",
        "The pinned example directly establishes the claimed complete contract.",
        ("SHERPA_301_HERA_YAML",),
        ("hera_ew_order_two_hard_process",),
    )
    refresh_derived(value)
    with pytest.raises(decision_module.DecisionError, match="gamma/Z support"):
        decision_module.validate_decision(value)


def test_all_routes_failed_with_all_route_cost_support_derives_stop() -> None:
    value = artifact()
    matrix = value["decision_criteria"]["matrix"]
    candidates = value["architecture_assessments"][decision_module.ARCH_C]["candidate_matrices"]
    for architecture in (decision_module.ARCH_A, decision_module.ARCH_B):
        for criterion in decision_module.CRITICAL_CRITERIA:
            matrix[architecture][criterion] = affirmative_not_supported(cost=criterion == "bounded_prototype_falsifiability")
        for criterion in decision_module.COST_CRITERIA:
            matrix[architecture][criterion] = affirmative_not_supported(cost=True)
    for row in candidates.values():
        for criterion in decision_module.CRITICAL_CRITERIA:
            row[criterion] = affirmative_not_supported(cost=criterion == "bounded_prototype_falsifiability")
        for criterion in decision_module.COST_CRITERIA:
            row[criterion] = affirmative_not_supported(cost=True)
    value["decision_criteria"]["matrix"][decision_module.ARCH_C] = decision_module.aggregate_candidate_matrices(candidates)
    rule = decision_module.recompute_decision_rule(value)
    assert rule["no_current_architecture_has_coherent_bounded_path"] is True
    assert rule["disproportionate_cost_supported_for_all_routes"] is True
    assert decision_module.derive_decision(rule) == "DO_NOT_AUTHORIZE_FURTHER_GENERATOR_PROTOTYPE"


def test_one_evidence_gap_route_derives_inconclusive() -> None:
    value = artifact()
    rule = decision_module.recompute_decision_rule(value)
    assert rule["potentially_coherent_route_remains"] is True
    assert rule["primary_or_mathematical_evidence_insufficient"] is True
    assert decision_module.derive_decision(rule) == "INCONCLUSIVE"


def test_inconclusive_uses_interim_pause_policy() -> None:
    value = artifact()
    assert value["decision"] == "INCONCLUSIVE"
    assert value["current_operational_policy"] == "PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION"
    assert value["architecture_assessments"][decision_module.ARCH_D]["assessment"] == "INTERIM_PAUSE_SUPPORTED_BY_FAILED_READINESS_GATE"


def test_inconclusive_terminal_stop_policy_is_rejected() -> None:
    value = artifact()
    value["current_operational_policy"] = "TERMINAL_STOP_FOR_FIXED_CONTRACT"
    with pytest.raises(decision_module.DecisionError, match="operational policy"):
        decision_module.validate_decision(value)


def test_reopen_conditions_grant_no_authorization() -> None:
    value = artifact()
    assert all(item["authorization_granted"] is False for item in value["reopen_conditions"])
    value["reopen_conditions"][0]["authorization_granted"] = True
    with pytest.raises(decision_module.DecisionError):
        decision_module.validate_decision(value)


@pytest.mark.parametrize("flag", decision_module.AUTHORIZATION_FLAGS)
def test_all_ten_authorization_flags_remain_false(flag: str) -> None:
    value = artifact()
    assert value["authorization"][flag] is False
    value["authorization"][flag] = True
    with pytest.raises(decision_module.DecisionError, match="authorization flag"):
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
    with pytest.raises(decision_module.DecisionError, match="immutable precedence"):
        decision_module.validate_decision(value)


def test_every_candidate_has_exact_twenty_criteria() -> None:
    value = artifact()
    candidates = value["architecture_assessments"][decision_module.ARCH_C]["candidate_matrices"]
    assert set(candidates) == set(decision_module.CANDIDATE_IDS)
    assert all(set(row) == set(decision_module.CRITERIA) for row in candidates.values())


def test_sherpa_dis_and_gamma_z_dispositions_are_conservative() -> None:
    value = artifact()
    sherpa = value["architecture_assessments"][decision_module.ARCH_C]["candidate_matrices"][decision_module.CANDIDATE_IDS[0]]
    assert sherpa["hard_process_coverage"]["status"] == "SUPPORTED_WITH_QUALIFICATION"
    assert sherpa["full_neutral_current_gamma_z_compatibility"]["status"] == "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE"
