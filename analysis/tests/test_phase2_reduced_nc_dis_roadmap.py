"""Focused and adversarial tests for the planning-only Phase 2 roadmap."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "validate_phase2_reduced_nc_dis_roadmap.py"
SPEC = importlib.util.spec_from_file_location("phase2_roadmap", MODULE_PATH)
assert SPEC and SPEC.loader
roadmap_validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(roadmap_validator)


def artifacts() -> tuple[dict, dict]:
    roadmap = json.loads((ROOT / roadmap_validator.ROADMAP_PATH).read_text(encoding="utf-8"))
    spec = json.loads((ROOT / roadmap_validator.SPEC_PATH).read_text(encoding="utf-8"))
    return roadmap, spec


def rejects(mutation) -> None:
    roadmap, spec = artifacts()
    mutation(roadmap, spec)
    with pytest.raises(roadmap_validator.RoadmapValidationError):
        roadmap_validator.validate_roadmap(roadmap, spec, ROOT, verify_files=False)


def obligation(spec: dict, obligation_id: str) -> dict:
    return next(item for item in spec["proof_obligations"] if item["obligation_id"] == obligation_id)


def mutate_cycle(roadmap: dict, _spec: dict) -> None:
    roadmap["dependency_graph"]["edges"].append({"from": "Phase2G", "to": "Phase2A"})


def omit_phase(roadmap: dict, _spec: dict) -> None:
    roadmap["phases"].pop()


def duplicate_issue_number(roadmap: dict, _spec: dict) -> None:
    roadmap["phases"][-1]["issue_number"] = roadmap["phases"][-2]["issue_number"]


def remove_obligation(spec: dict, obligation_id: str) -> None:
    spec["proof_obligations"].remove(obligation(spec, obligation_id))


def remove_phase2d_selection_scope(roadmap: dict, _spec: dict) -> None:
    phase = next(row for row in roadmap["phases"] if row["phase_id"] == "Phase2D")
    phase["deliverables"] = ["Normalized kernel", "Forward closure"]


def remove_phase2e_prior_diagnostic(roadmap: dict, _spec: dict) -> None:
    phase = next(row for row in roadmap["phases"] if row["phase_id"] == "Phase2E")
    phase["deliverables"] = [item for item in phase["deliverables"] if item != "Prior-dominated posterior diagnostics"]


def remove_phase2f_information_scope(roadmap: dict, _spec: dict) -> None:
    phase = next(row for row in roadmap["phases"] if row["phase_id"] == "Phase2F")
    phase["deliverables"] = ["Simulation-based calibration", "Coverage", "Failure criteria"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r, s: r["research_objective"].update({"target": "p(theta_PDF | y_1)"}),
        lambda r, s: r["research_objective"].update({"single_event_instantaneous_pdf_objective": True}),
        lambda r, s: r["legacy_line"].update({"CURRENT_FULL_GENERATOR_LINE": "ACTIVE"}),
        lambda r, s: r["legacy_line"].update({"PHASE_2A_IS_NOT_LEGACY_D2": False}),
        lambda r, s: r["legacy_line"]["issue_10"].update({"state": "CLOSED"}),
        lambda r, s: r["legacy_line"].update({"LEGACY_D2_AUTHORIZED": True}),
        lambda r, s: r["paper_scope"]["claims_allowed_only_if_later_validated"].append("full PYTHIA equivalence"),
        lambda r, s: r["paper_scope"]["claims_allowed_only_if_later_validated"].append("showering and hadronization"),
        lambda r, s: s["proof_obligations"].remove(obligation(s, "FINITE_NONZERO_NORMALIZATION_FOR_EVERY_THETA")),
        lambda r, s: obligation(s, "EXACT_E_MINUS_NC_FORMULA").update({"status": "PASS"}),
        lambda r, s: obligation(s, "EXACT_E_PLUS_NC_FORMULA").update({"status": "FAIL"}),
        lambda r, s: r["authorization"].update({"PHASE2B_AUTHORIZED": True}),
        lambda r, s: r["authorization"].update({"SAMPLER_IMPLEMENTATION_AUTHORIZED": True}),
        lambda r, s: r["authorization"].update({"DETECTOR_IMPLEMENTATION_AUTHORIZED": True}),
        lambda r, s: r["authorization"].update({"TRAINING_AUTHORIZED": True}),
        lambda r, s: r["repository_strategy"].update({"preferred_implementation_architecture": "Rust-first"}),
        lambda r, s: r["repository_strategy"].update({"repository_split_active": True}),
        lambda r, s: r["split_triggers"].pop(),
        lambda r, s: s["fixed_n_shape_only_baseline"].update({"weighted_events": True}),
        lambda r, s: s["fixed_n_shape_only_baseline"].update({"count_or_rate_likelihood_included": True}),
        lambda r, s: r["phases"][7]["blockers"].append("Phase2H"),
        mutate_cycle,
        omit_phase,
        duplicate_issue_number,
        lambda r, s: r["project_fields"].pop("field_value_source"),
        lambda r, s: r["github_roadmap_snapshot"].update({"offline_validator_can_verify_live_github_state": True}),
        lambda r, s: r["predecessor_closeout"].update({"main_commit": "0" * 40}),
        lambda r, s: r["legacy_line"].update({"D1F_FINAL_DECISION": "SUPERSEDED"}),
        lambda r, s: r["authorization"].update({"PYTHIA_INIT_AUTHORIZED": True}),
        lambda r, s: r.update({"next_step": "IMPLEMENT_PHASE2B"}),
    ],
    ids=[f"adversarial-{index:02d}" for index in range(1, 31)],
)
def test_adversarial_mutations_are_rejected(mutation) -> None:
    rejects(mutation)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r, s: s["proof_obligations"].__setitem__(slice(None), s["proof_obligations"][:22]),
        lambda r, s: remove_obligation(s, "OBSERVATION_SELECTION_AND_FIXED_N_CONDITIONING"),
        lambda r, s: remove_obligation(s, "PARAMETER_IDENTIFIABILITY_AND_INFORMATION_CONTENT"),
        lambda r, s: s["observation_selection_contract"]["detector_output_spaces"].update({"selected_space_symbol": "A_z"}),
        lambda r, s: s["observation_selection_contract"]["full_detector_kernel"].update({"null_or_rejected_outcome_required_when_needed_for_normalization": False}),
        lambda r, s: s["observation_selection_contract"]["selected_observed_event_density"].update({"definition": "q_theta(dy | selected) = integral p_theta(z) K_full(dy | z) dz"}),
        lambda r, s: s["observation_selection_contract"]["theta_dependent_selected_fraction"].update({"required_finite_for_every_allowed_theta": False}),
        lambda r, s: s["observation_selection_contract"]["selected_observed_event_density"].update({"required_normalized_for_every_allowed_theta": False}),
        lambda r, s: s["observation_selection_contract"].update({"probability_mass_may_not_be_silently_discarded": False}),
        lambda r, s: s["fixed_n_shape_only_baseline"].update({"count_or_rate_likelihood_included": True}),
        lambda r, s: s["observation_selection_contract"].update({"phase2h_is_only_optional_count_or_rate_extension": False}),
        lambda r, s: s["identifiability_and_information_content_contract"].update({"calibration_and_coverage_alone_establish_informativeness": True}),
        lambda r, s: obligation(s, "PARAMETER_IDENTIFIABILITY_AND_INFORMATION_CONTENT").update({"fail_condition": ["uninformative posterior accepted"]}),
        lambda r, s: r["nonclaims"].remove("universal identifiability of all PDF-deformation parameters"),
        lambda r, s: s["go_no_go_rules"]["pass_requires_all_independently_supported"].remove("bounded_identifiability_and_information_plan"),
        lambda r, s: s["go_no_go_rules"]["pass_requires_all_independently_supported"].remove("selected_event_conditioning_coherence"),
        remove_phase2d_selection_scope,
        remove_phase2e_prior_diagnostic,
        remove_phase2f_information_scope,
        lambda r, s: r["authorization"].update({"PHASE2D_AUTHORIZED": True}),
    ],
    ids=[f"scientific-contract-{index:02d}" for index in range(1, 21)],
)
def test_scientific_contract_mutations_are_rejected(mutation) -> None:
    rejects(mutation)


def test_committed_artifacts_validate() -> None:
    roadmap, spec = artifacts()
    roadmap_validator.validate_roadmap(roadmap, spec, ROOT, verify_files=True)


def test_nine_issues_are_eight_stages_plus_umbrella() -> None:
    roadmap, _ = artifacts()
    assert [phase["phase_id"] for phase in roadmap["phases"]] == roadmap_validator.PHASE_IDS
    assert len(roadmap["phases"]) == 9


def test_twenty_four_obligations_are_not_evaluated() -> None:
    _, spec = artifacts()
    assert len(spec["proof_obligations"]) == 24
    assert [item["obligation_id"] for item in spec["proof_obligations"]] == roadmap_validator.OBLIGATION_IDS
    assert {item["status"] for item in spec["proof_obligations"]} == {"NOT_EVALUATED"}


def test_eleven_phase2a_pass_requirements_are_bound() -> None:
    _, spec = artifacts()
    assert spec["go_no_go_rules"]["pass_requires_all_independently_supported"] == roadmap_validator.PASS_REQUIREMENTS
    assert len(roadmap_validator.PASS_REQUIREMENTS) == 11


def test_selected_event_conditioning_law_is_complete() -> None:
    _, spec = artifacts()
    selection = spec["observation_selection_contract"]
    assert selection["BASELINE_SELECTION_MODE"] == "SELECTED_EVENT_CONDITIONED_V1"
    assert selection["latent_acceptance_region"]["symbol"] == "A_z"
    assert selection["detector_output_spaces"]["full_space_symbol"] == "Y_full"
    assert selection["detector_output_spaces"]["selected_space_symbol"] == "Y_obs"
    assert selection["full_detector_kernel"]["normalization"] == "integral_{Y_full} K_full(dy_star | z) = 1"
    assert selection["selection_efficiency"]["definition"] == "epsilon(z) = K_full(Y_obs | z)"
    assert selection["theta_dependent_selected_fraction"]["definition"] == "alpha_theta = integral_{A_z} p_theta(z) epsilon(z) dz"
    assert selection["theta_dependent_selected_fraction"]["required_finite_for_every_allowed_theta"] is True
    assert selection["theta_dependent_selected_fraction"]["required_strictly_positive_for_every_allowed_theta"] is True
    assert selection["selected_observed_event_density"]["required_normalized_for_every_allowed_theta"] is True
    assert selection["fixed_n_selected_set_law"]["likelihood"] == "p(D | theta, N, selected) = product_i q_theta(y_i | selected)"
    assert selection["fixed_n_selected_set_law"]["count_or_rate_likelihood_included"] is False
    assert selection["phase2h_is_only_optional_count_or_rate_extension"] is True


def test_identifiability_and_information_contract_is_bounded() -> None:
    roadmap, spec = artifacts()
    contract = spec["identifiability_and_information_content_contract"]
    assert contract["observational_equivalence"]["notation"] == "theta ~ theta_prime"
    assert "q_theta(D | N, selected)" in contract["observational_equivalence"]["definition"]
    assert contract["bounded_and_falsifiable_phase2e_phase2f_plan_required"] is True
    assert contract["calibration_and_coverage_alone_establish_informativeness"] is False
    assert contract["actual_information_content_experiment_authorized"] is False
    assert roadmap["paper_scope"]["claims_allowed_only_if_later_validated"][-1] == "proof-of-principle sensitivity only for predeclared parameter combinations that pass the later identifiability and information-content gates"


def test_phase2a_authorization_is_planning_only() -> None:
    roadmap, _ = artifacts()
    enabled = {key for key, value in roadmap["authorization"].items() if value}
    assert enabled == roadmap_validator.TRUE_AUTHORIZATION_FLAGS


def test_fixed_n_baseline_and_rate_extension_are_separate() -> None:
    _, spec = artifacts()
    assert spec["fixed_n_shape_only_baseline"]["fixed_n"] is True
    assert spec["fixed_n_shape_only_baseline"]["shape_only"] is True
    assert spec["fixed_n_shape_only_baseline"]["weighted_events"] is False
    assert spec["optional_rate_extension_boundary"]["separate_from_baseline"] is True


def test_same_repository_and_no_full_generator_claims() -> None:
    roadmap, _ = artifacts()
    assert roadmap["repository_strategy"]["CURRENT_REPOSITORY"] == "parton-sbi"
    assert set(roadmap["nonclaims"]) == roadmap_validator.NONCLAIMS


def test_planned_code_directories_do_not_exist() -> None:
    for relative in roadmap_validator.PLANNED_DIRS:
        assert not (ROOT / relative).exists()


def test_dependency_graph_is_acyclic_and_phase2g_ignores_phase2h() -> None:
    roadmap, _ = artifacts()
    edges = {(edge["from"], edge["to"]) for edge in roadmap["dependency_graph"]["edges"]}
    assert roadmap_validator.graph_is_acyclic(set(roadmap_validator.PHASE_IDS[1:]), edges)
    assert ("Phase2H", "Phase2G") not in edges
    assert "Phase2H" not in roadmap["phases"][7]["blockers"]
