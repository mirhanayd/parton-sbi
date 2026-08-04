"""Adversarial tests for the corrected Phase 1B-D1G evidence ledger."""

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


def binding(source_id: str, claim_key: str) -> dict:
    return {
        "source_id": source_id,
        "claim_key": claim_key,
        "identity_classification": "VERIFIED_WITH_QUALIFICATION",
        "content_classification": "OVERSTATED_IN_V1",
        "maximum_supported_status": "SUPPORTED_WITH_QUALIFICATION",
    }


def promote(record: dict, candidate: str, criterion: str, source_id: str, claim_key: str) -> None:
    cell = record["criterion_scorecards"][candidate][criterion]
    cell.update(
        status="SUPPORTED_WITH_QUALIFICATION",
        evidence_class="EXPLICIT_INFERENCE_FROM_PRIMARY_EVIDENCE",
        source_content_bindings=[binding(source_id, claim_key)],
        explicit_inference={"premises": [f"{source_id}:{claim_key}"], "conclusion": "tampered"},
        load_bearing=True,
    )


def test_committed_artifact_is_valid_and_deterministic(record: dict) -> None:
    path = REPO / d1g.ARTIFACT
    actual_text = path.read_text(encoding="utf-8")
    actual = json.loads(actual_text)
    d1g.validate_record(actual)
    assert actual == record
    assert actual_text == d1g.serialized(record)


def test_corrected_identity_and_content_audit_totals(record: dict) -> None:
    assert len(record["external_source_registry"]) == 13
    assert record["validation"]["v1_source_identity_audit_totals"] == {
        "CONTRADICTED": 1,
        "VERIFIED": 5,
        "VERIFIED_WITH_QUALIFICATION": 7,
    }
    assert record["validation"]["corrected_source_identity_totals"] == {
        "VERIFIED": 5,
        "VERIFIED_WITH_QUALIFICATION": 8,
    }
    assert record["validation"]["source_content_ledger_totals"] == {
        "DIRECTLY_SUPPORTED": 2,
        "MISBOUND_IN_V1": 1,
        "OVERSTATED_IN_V1": 14,
        "SUPPORTED_WITH_QUALIFICATION": 1,
    }
    assert record["validation"]["v1_cell_audit_totals"] == {
        "MISBOUND_IN_V1": 6,
        "OVERSTATED_IN_V1": 16,
        "PRIMARY_EVIDENCE_UNAVAILABLE": 19,
        "SUPPORTED_WITH_QUALIFICATION": 31,
    }


def test_dagostini_identity_is_publisher_bound(record: dict) -> None:
    row = record["external_source_registry"]["C_DAGOSTINI_UNFOLDING"]
    assert row["DOI_or_arXiv_or_official_identifier"] == "doi:10.1016/0168-9002(95)00274-X"
    assert row["publication_date"] == "1995-08-15"
    assert row["publication_date_kind"] == "PUBLISHER_ARTICLE_DATE"
    assert row["official_URL"].startswith("https://www.sciencedirect.com/")
    assert row["retrieved_byte_SHA256_when_downloaded"] is None


def test_corrected_scores_gates_and_pause(record: dict) -> None:
    assert record["validation"]["criterion_totals"] == {
        B: {"PRIMARY_EVIDENCE_UNAVAILABLE": 11, "SUPPORTED_WITH_QUALIFICATION": 7},
        C: {"PRIMARY_EVIDENCE_UNAVAILABLE": 11, "SUPPORTED_WITH_QUALIFICATION": 7},
        D: {"PRIMARY_EVIDENCE_UNAVAILABLE": 10, "SUPPORTED_WITH_QUALIFICATION": 8},
        E: {"PRIMARY_EVIDENCE_UNAVAILABLE": 9, "SUPPORTED_WITH_QUALIFICATION": 9},
    }
    assert record["derived_decision_inputs"]["eligible_candidates"] == []
    assert all(not row["eligible"] for row in record["candidate_eligibility"].values())
    assert record["decision"] == d1g.PAUSE_OUTCOME
    common = {
        "normalized_measure_reviewability": "PRIMARY_EVIDENCE_UNAVAILABLE",
        "posterior_reviewability": "PRIMARY_EVIDENCE_UNAVAILABLE",
        "scientific_motivation": "SUPPORTED_WITH_QUALIFICATION",
        "bounded_planning_review": "SUPPORTED_WITH_QUALIFICATION",
        "independent_falsifiability": "SUPPORTED_WITH_QUALIFICATION",
        "credible_MVP_path": "PRIMARY_EVIDENCE_UNAVAILABLE",
        "prospective_supersession_explicit": "SUPPORTED",
        "objective_change_understood": "SUPPORTED_WITH_QUALIFICATION",
        "independent_evidence_available": "PRIMARY_EVIDENCE_UNAVAILABLE",
    }
    for candidate, gates in record["mandatory_priority_gates"].items():
        assert {key: gates[key] for key in common} == common
        assert gates["no_hidden_repair"] == ("SUPPORTED_WITH_QUALIFICATION" if candidate == E else "PRIMARY_EVIDENCE_UNAVAILABLE")
    assert all(row["status"] == "PRIMARY_EVIDENCE_UNAVAILABLE" for row in record["composite_mvp_contract"].values())


def test_candidate_c_status_and_obligations(record: dict) -> None:
    candidate = record["candidates"][C]
    assert candidate["candidate_status"] == "SCIENTIFICALLY_MOTIVATED_COMPONENTS_PRESENT_BUT_PRIORITY_GATES_UNMET"
    assert candidate["full_generator_equivalence_claimed"] is False
    assert candidate["issue_10_completed"] is False
    assert [row["obligation_id"] for row in candidate["proof_obligations"]] == list(d1g.OPTION_C_OBLIGATIONS)
    assert all(row["status"] == "NOT_EVALUATED" for row in candidate["proof_obligations"])


def test_authorization_and_roadmap_remain_frozen(record: dict) -> None:
    assert set(record["authorization"]) == set(d1g.AUTHORIZATION_FLAGS)
    assert all(value is False for value in record["authorization"].values())
    assert record["dependencies"]["issue_10"]["state"] == "OPEN_BLOCKED"
    assert record["dependencies"]["D2"] == "BLOCKED_AND_UNAUTHORIZED"
    assert record["dependencies"]["roadmap"] == {"D2": "BLOCKED", "D3": "BACKLOG", "D4": "BACKLOG", "D5": "BACKLOG", "active_supersession": False}


def m_old_dagostini_bytes(record: dict) -> None:
    row = record["external_source_registry"]["C_DAGOSTINI_UNFOLDING"]
    row["official_URL"] = "https://arxiv.org/pdf/hep-ph/9509307"
    row["retrieved_byte_SHA256_when_downloaded"] = "d3ad8e695c6a89c157e51d313e0f8254f9c7688920294cf0cf4f8467f679350a"


def m_date_conflation(record: dict) -> None:
    row = record["external_source_registry"]["B_MSbar_POSITIVITY_2023"]
    row["publication_date"] = row["version_date"]
    row.pop("publication_date_kind")


def m_promote_hard(record: dict, criterion: str, source: str, claim: str) -> None:
    promote(record, C, criterion, source, claim)


def m_c_normalized(record: dict) -> None:
    m_promote_hard(record, "normalized_observation_measure", "C_HERA_COMBINED_DIS", "NC_EPLUS_EMINUS_STRUCTURE")


def m_c_posterior(record: dict) -> None:
    m_promote_hard(record, "posterior_target_coherence", "C_HERA_COMBINED_DIS", "NC_EPLUS_EMINUS_STRUCTURE")


def m_hera_weight(record: dict) -> None:
    m_promote_hard(record, "weight_semantics", "C_HERA_COMBINED_DIS", "NC_EPLUS_EMINUS_STRUCTURE")


def m_hera_rate_shape(record: dict) -> None:
    m_promote_hard(record, "rate_shape_semantics", "C_HERA_COMBINED_DIS", "NC_EPLUS_EMINUS_STRUCTURE")


def m_hera_no_clip(record: dict) -> None:
    m_promote_hard(record, "no_clipping_preservation", "C_HERA_COMBINED_DIS", "REDUCED_INCLUSIVE_SCOPE")


def m_hera_strict_support(record: dict) -> None:
    m_promote_hard(record, "strict_support_preservation", "C_HERA_COMBINED_DIS", "REDUCED_INCLUSIVE_SCOPE")


def m_deep_sets_mvp(record: dict) -> None:
    m_promote_hard(record, "credible_end_to_end_mvp_path", "C_DEEP_SETS", "PERMUTATION_INVARIANT_SET_FUNCTIONS")


def m_deep_sets_normalized(record: dict) -> None:
    m_promote_hard(record, "normalized_observation_measure", "C_DEEP_SETS", "PERMUTATION_INVARIANT_SET_FUNCTIONS")


def m_sbc_posterior(record: dict) -> None:
    m_promote_hard(record, "posterior_target_coherence", "C_SIMULATION_BASED_CALIBRATION", "SBC_REQUIRES_GENERATIVE_MODEL_AND_POSTERIOR")


def m_sbc_positive_rate(record: dict) -> None:
    m_promote_hard(record, "normalized_observation_measure", "C_SIMULATION_BASED_CALIBRATION", "SBC_REQUIRES_GENERATIVE_MODEL_AND_POSTERIOR")


def m_dagostini_qcd(record: dict) -> None:
    m_promote_hard(record, "qcd_factorization_compatibility", "C_DAGOSTINI_UNFOLDING", "DETECTOR_RESPONSE_CONDITIONAL_PROBABILITIES")


def m_dagostini_mvp(record: dict) -> None:
    m_promote_hard(record, "credible_end_to_end_mvp_path", "C_DAGOSTINI_UNFOLDING", "DETECTOR_RESPONSE_CONDITIONAL_PROBABILITIES")


def m_unrelated_independent_gate(record: dict) -> None:
    record["mandatory_priority_gates"][C]["independent_evidence_available"] = "SUPPORTED"


def m_candidate_eligible(record: dict) -> None:
    record["candidate_eligibility"][C] = {"eligible": True, "failed_or_unavailable_gates": []}


def m_e_measure_not_supported(record: dict) -> None:
    record["criterion_scorecards"][E]["normalized_observation_measure"]["status"] = "NOT_SUPPORTED"


def m_e_posterior_not_supported(record: dict) -> None:
    record["criterion_scorecards"][E]["posterior_target_coherence"]["status"] = "NOT_SUPPORTED"


def m_option_c_obligation_removed(record: dict) -> None:
    record["candidates"][C]["proof_obligations"].pop()


def m_option_c_obligation_promoted(record: dict) -> None:
    record["candidates"][C]["proof_obligations"][0]["status"] = "PASS"


def m_c_completes_issue10(record: dict) -> None:
    record["candidates"][C]["issue_10_completed"] = True


def m_roadmap_supersession(record: dict) -> None:
    record["dependencies"]["roadmap"]["active_supersession"] = True


def m_authorization(record: dict) -> None:
    record["authorization"]["LOWER_LEVEL_SIMULATOR_AUTHORIZED"] = True


def m_next_step_contract(record: dict) -> None:
    record["next_step"].update(action="CREATE_LOWER_LEVEL_CONTRACT", implementation=True, authorization_granted=True)


def m_manual_decision(record: dict) -> None:
    record["decision"] = d1g.OUTCOMES[C]


ADVERSARIAL_MUTATIONS: tuple[tuple[str, Callable[[dict], None]], ...] = (
    ("old_hocker_kartvelishvili_bytes_attached_to_dagostini", m_old_dagostini_bytes),
    ("journal_date_replaced_by_revision_date", m_date_conflation),
    ("hera_bound_to_normalized_measure", m_c_normalized),
    ("hera_bound_to_posterior", m_c_posterior),
    ("hera_bound_to_event_weight", m_hera_weight),
    ("hera_bound_to_rate_shape", m_hera_rate_shape),
    ("hera_bound_to_no_clipping", m_hera_no_clip),
    ("hera_bound_to_strict_support", m_hera_strict_support),
    ("deep_sets_bound_to_mvp", m_deep_sets_mvp),
    ("deep_sets_bound_to_normalized_measure", m_deep_sets_normalized),
    ("sbc_bound_to_posterior_existence", m_sbc_posterior),
    ("sbc_bound_to_complete_rate_positivity", m_sbc_positive_rate),
    ("dagostini_bound_to_qcd", m_dagostini_qcd),
    ("dagostini_bound_to_mvp", m_dagostini_mvp),
    ("candidate_c_normalized_promoted", m_c_normalized),
    ("candidate_c_posterior_promoted", m_c_posterior),
    ("candidate_c_mvp_promoted", m_deep_sets_mvp),
    ("one_unrelated_source_satisfies_independent_gate", m_unrelated_independent_gate),
    ("candidate_eligible_with_unavailable_gate", m_candidate_eligible),
    ("candidate_e_measure_asserted_incompatible_without_source", m_e_measure_not_supported),
    ("candidate_e_posterior_asserted_incompatible_without_source", m_e_posterior_not_supported),
    ("candidate_c_obligation_removed", m_option_c_obligation_removed),
    ("candidate_c_obligation_promoted", m_option_c_obligation_promoted),
    ("candidate_c_completes_issue10", m_c_completes_issue10),
    ("roadmap_supersession_activated", m_roadmap_supersession),
    ("authorization_flag_true", m_authorization),
    ("next_step_creates_contract_or_implementation", m_next_step_contract),
    ("decision_manually_changed", m_manual_decision),
)


@pytest.mark.parametrize(("name", "mutate"), ADVERSARIAL_MUTATIONS)
def test_semantic_adversarial_mutation_is_rejected(record: dict, name: str, mutate: Callable[[dict], None]) -> None:
    del name
    mutate(record)
    rejected(record)


def test_one_unrelated_source_cannot_satisfy_complete_critical_coverage(record: dict) -> None:
    assert any(cell["load_bearing"] for cell in record["criterion_scorecards"][C].values())
    assert d1g.derive_gates(record)[C]["independent_evidence_available"] == "PRIMARY_EVIDENCE_UNAVAILABLE"


def test_unique_priority_rule_pauses_for_tie() -> None:
    eligibility = {candidate: {"eligible": candidate in {B, C}, "failed_or_unavailable_gates": []} for candidate in d1g.CANDIDATES}
    assert d1g.derive_decision(eligibility) == d1g.PAUSE_OUTCOME


def test_unique_priority_rule_pauses_for_zero_eligible() -> None:
    eligibility = {candidate: {"eligible": False, "failed_or_unavailable_gates": ["normalized_measure_reviewability"]} for candidate in d1g.CANDIDATES}
    assert d1g.derive_decision(eligibility) == d1g.PAUSE_OUTCOME
