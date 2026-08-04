"""Adversarial tests for the immutable Phase 1B closeout manifest."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "validate_phase1b_closeout.py"
SPEC = importlib.util.spec_from_file_location("phase1b_closeout", MODULE_PATH)
assert SPEC and SPEC.loader
closeout = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(closeout)


def manifest() -> dict:
    return json.loads((ROOT / closeout.MANIFEST_PATH).read_text(encoding="utf-8"))


def rejects(value: dict, match: str | None = None) -> None:
    with pytest.raises(closeout.CloseoutValidationError, match=match):
        closeout.validate_manifest(value, ROOT, verify_git=False)


def test_committed_manifest_validates_with_full_lineage() -> None:
    if closeout.is_shallow_repository(ROOT):
        pytest.skip("full merge-lineage validation requires non-shallow Git history")
    closeout.validate_manifest(manifest(), ROOT, verify_git=True)


def test_generator_is_deterministic_and_matches_committed_bytes() -> None:
    value = closeout.build_manifest()
    assert value == closeout.build_manifest() == manifest()
    assert closeout.serialized(value) == (ROOT / closeout.MANIFEST_PATH).read_text(encoding="utf-8")


def test_inventory_aggregates_are_complete() -> None:
    value = manifest()
    assert len(value["accepted_artifacts"]) == 20
    assert len(value["accepted_adrs"]) == 11
    assert len(value["merge_lineage"]) == 7
    assert value["accepted_artifacts"] == list(closeout.ARTIFACT_SPECS)
    assert value["accepted_adrs"] == closeout.build_manifest()["accepted_adrs"]
    assert value["merge_lineage"] == list(closeout.MERGE_LINEAGE)


def restore_timeless_closeout_issue(value: dict) -> None:
    value["issue_state"]["closeout_issue"] = {
        "number": 51,
        "state": "OPEN",
        "status": "In Progress",
        "gate_decision": "Not Evaluated",
        "authorization": "Planning Only",
    }
    value["issue_state"].pop("closeout_workflow")


@pytest.mark.parametrize(
    "mutation",
    [
        restore_timeless_closeout_issue,
        lambda value: value["issue_state"]["closeout_workflow"]["inventory_snapshot"].pop("observed_at"),
        lambda value: value["issue_state"]["closeout_workflow"]["expected_post_merge_finalization"].pop("state"),
        lambda value: value["issue_state"]["closeout_workflow"]["expected_post_merge_finalization"].update({"authorization": "Authorized"}),
        lambda value: value["issue_state"]["closeout_workflow"]["lifecycle_semantics"].update({"offline_validator_can_verify_live_github_state": True}),
        lambda value: value["validation"].update({"internet_contacted": False}),
        lambda value: value["validation"].update({"github_metadata_was_used_to_construct_inventory": False}),
        lambda value: value["merge_lineage"][0].pop("reviewed_branch_head_source"),
        lambda value: value["merge_lineage"][0].update({"reviewed_branch_head_offline_ancestry_verifiable": True}),
        lambda value: value["issue_state"]["issue_10"].update({"expected_state": "CLOSED"}),
        lambda value: value["authorization"].update({"IMPLEMENTATION_AUTHORIZED": True}),
        lambda value: value["accepted_artifacts"][0].update({"sha256": "f" * 64}),
        lambda value: value["merge_lineage"][2].update({"merge_commit": "f" * 40}),
    ],
)
def test_v2_lifecycle_and_provenance_mutations_are_rejected(mutation) -> None:
    value = manifest()
    mutation(value)
    rejects(value)


def test_closeout_snapshot_and_expected_lifecycle_coexist() -> None:
    workflow = manifest()["issue_state"]["closeout_workflow"]
    assert workflow["inventory_snapshot"] == closeout.ISSUE_STATE["closeout_workflow"]["inventory_snapshot"]
    assert workflow["expected_post_merge_finalization"] == closeout.ISSUE_STATE["closeout_workflow"]["expected_post_merge_finalization"]
    assert workflow["lifecycle_semantics"]["inventory_snapshot_is_historical"] is True
    assert workflow["lifecycle_semantics"]["offline_validator_can_verify_live_github_state"] is False


def test_issue_10_is_active_expected_boundary() -> None:
    boundary = manifest()["issue_state"]["issue_10"]
    assert boundary == closeout.ISSUE_STATE["issue_10"]
    assert boundary["expected_state"] == "OPEN"
    assert boundary["expected_status"] == "Blocked"
    assert boundary["expected_gate_decision"] == "Not Evaluated"
    assert boundary["expected_authorization"] == "Not Authorized"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value["accepted_artifacts"][0].update({"sha256": "0" * 64}), "metadata changed"),
        (lambda value: value["accepted_artifacts"].pop(1), "required accepted artifact"),
        (lambda value: value["accepted_artifacts"].__setitem__(1, {**value["accepted_artifacts"][1], "superseded": True}), "metadata changed"),
        (lambda value: value["accepted_artifacts"].__setitem__(4, {**value["accepted_artifacts"][4], "superseded_by": "D1R"}), "metadata changed"),
        (lambda value: value["accepted_decisions"].update({"D1F_FINAL_DECISION": "CONTINUE"}), "accepted decision ledger"),
        (lambda value: value["accepted_decisions"].update({"D1G_ELIGIBLE_CANDIDATES": ["CANDIDATE_C"]}), "accepted decision ledger"),
        (lambda value: value["active_policy"].update({"preferred_scientific_candidate": "CANDIDATE_C"}), "active pause"),
        (lambda value: value["authorization"].update({"D2_AUTHORIZED": True}), "authorization flag"),
        (lambda value: value["authorization"].update({"PROTOTYPE_AUTHORIZED": True}), "authorization flag"),
        (lambda value: value["issue_state"]["issue_10"].update({"expected_state": "CLOSED", "expected_status": "Done"}), "issue #10"),
        (lambda value: value["roadmap_state"].update({"active_supersession": True}), "roadmap state"),
        (lambda value: value["reopen_conditions"][0].update({"authorization_granted": True}), "reopen conditions"),
        (lambda value: value["active_policy"].update({"implementation_next_step": "BUILD_CANDIDATE_C"}), "active pause"),
        (lambda value: value["merge_lineage"][0].update({"merge_commit": "0" * 40}), "merge lineage"),
        (lambda value: value["merge_lineage"].pop(), "merge lineage"),
        (lambda value: value["accepted_artifacts"].append(copy.deepcopy(value["accepted_artifacts"][0])), "duplicate artifact path"),
        (lambda value: value["accepted_adrs"].pop(), "accepted ADR ledger"),
    ],
)
def test_adversarial_mutations_are_rejected(mutation, message: str) -> None:
    value = manifest()
    mutation(value)
    rejects(value, message)


def test_all_authorization_flags_are_false() -> None:
    value = manifest()
    assert set(value["authorization"]) == set(closeout.AUTHORIZATION_FLAGS)
    assert all(flag is False for flag in value["authorization"].values())


def test_reopen_conditions_are_non_authorizing() -> None:
    value = manifest()
    assert len(value["reopen_conditions"]) == 4
    assert all(row["authorization_granted"] is False for row in value["reopen_conditions"])


def test_original_failures_coexist_with_revisions() -> None:
    value = manifest()
    artifacts = {row["path"]: row for row in value["accepted_artifacts"]}
    assert artifacts["docs/phase1bd_d0_decision.json"]["decision"] == "FAIL"
    assert artifacts["docs/phase1bd_d0r_decision.json"]["decision"] == "PASS"
    assert artifacts["docs/phase1bd_d1_decision.json"]["decision"] == "FAIL"
    assert artifacts["docs/phase1bd_d1r_decision.json"]["decision"] == "FAIL"
    assert all(row["superseded"] is False for row in artifacts.values())
