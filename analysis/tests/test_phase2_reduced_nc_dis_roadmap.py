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


def test_committed_artifacts_validate() -> None:
    roadmap, spec = artifacts()
    roadmap_validator.validate_roadmap(roadmap, spec, ROOT, verify_files=True)


def test_nine_issues_are_eight_stages_plus_umbrella() -> None:
    roadmap, _ = artifacts()
    assert [phase["phase_id"] for phase in roadmap["phases"]] == roadmap_validator.PHASE_IDS
    assert len(roadmap["phases"]) == 9


def test_twenty_two_obligations_are_not_evaluated() -> None:
    _, spec = artifacts()
    assert len(spec["proof_obligations"]) == 22
    assert {item["status"] for item in spec["proof_obligations"]} == {"NOT_EVALUATED"}


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
