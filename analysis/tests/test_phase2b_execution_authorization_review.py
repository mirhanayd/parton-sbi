import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_phase2b_execution_authorization_review.py"
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_execution_authorization_review.json"

SPEC = importlib.util.spec_from_file_location("phase2b_authorization_validator", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


@pytest.fixture
def record():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def rejected(record, expected_message):
    with pytest.raises(VALIDATOR.ValidationError, match=expected_message):
        VALIDATOR.validate(record, root=ROOT, check_docs=False)


def hypothetical_ar1(record):
    candidate = copy.deepcopy(record)
    candidate["decision"] = VALIDATOR.AR1
    candidate["authorization_criteria"] = {
        key: "PASS" for key in candidate["authorization_criteria"]
    }
    candidate["blocking_revisions"] = []
    candidate["heavy_flavor_and_coupling_audit"]["overall_result"] = "COHERENT"
    candidate["grid_audit"]["result"] = "PASS"
    for tolerance in candidate["tolerance_audit"]:
        if tolerance["classification"] == "UNJUSTIFIED_TOLERANCE":
            tolerance["classification"] = "QUALIFIED_TOLERANCE"
    candidate["roundoff_and_negative_rate_audit"]["result"] = "PASS"
    candidate["roundoff_and_negative_rate_audit"][
        "operational_binary128_complete_rate_recomputation_bound"
    ] = True
    for component in candidate["independent_reference_coverage"]:
        if component["classification"] in {"NOT_INDEPENDENT", "UNVALIDATED"}:
            component["classification"] = "PARTIALLY_INDEPENDENT"
    candidate["independent_reference_conclusion"]["current_hierarchy_sufficient"] = True
    candidate["independent_reference_conclusion"]["result"] = "PASS"
    candidate["authorization"]["PHASE2B_BOUNDED_NUMERICAL_VALIDATION_AUTHORIZED"] = True
    candidate["authorization"]["PHASE2B_EXECUTION_AUTHORIZED"] = True
    candidate["execution_boundary"]["later_execution_task_permitted"] = True
    candidate["github_target_state"]["status"] = "In Progress"
    candidate["github_target_state"]["authorization"] = "Authorized"
    return candidate


def test_cli_validates_current_ar2_artifact():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "VALID phase2b.execution_authorization_review" in result.stdout


def test_ar1_with_unjustified_tolerance_is_rejected(record):
    candidate = hypothetical_ar1(record)
    candidate["tolerance_audit"][0]["classification"] = "UNJUSTIFIED_TOLERANCE"
    rejected(candidate, "AR1 with an unjustified tolerance")


def test_ar1_with_unvalidated_load_bearing_component_is_rejected(record):
    candidate = hypothetical_ar1(record)
    bridge = next(
        item
        for item in candidate["independent_reference_coverage"]
        if item["component"] == "accepted_deformed_pdfs_and_external_apfel_bridge"
    )
    bridge["classification"] = "UNVALIDATED"
    rejected(candidate, "AR1 with an unvalidated load-bearing component")


def test_ar1_with_resource_count_mismatch_is_rejected(record):
    candidate = hypothetical_ar1(record)
    candidate["resource_audit"]["total_evaluations"] += 1
    rejected(candidate, "Resource-count mismatch: total evaluations")


def test_ar1_with_clipping_allowed_is_rejected(record):
    candidate = hypothetical_ar1(record)
    candidate["roundoff_and_negative_rate_audit"]["clipping_allowed"] = True
    rejected(candidate, "Forbidden negative-rate repair enabled: clipping_allowed")


def test_ar1_cannot_convert_high_precision_negative_to_zero(record):
    candidate = hypothetical_ar1(record)
    candidate["roundoff_and_negative_rate_audit"]["high_precision_negative_result"] = (
        "REPLACE_WITH_ZERO"
    )
    rejected(candidate, "High-precision negative does not fail")


def test_ar1_with_post_auth_result_executed_is_rejected(record):
    candidate = hypothetical_ar1(record)
    candidate["rederived_plan"]["post_auth_execution_status"] = "EXECUTED"
    rejected(candidate, "POST_AUTH result marked executed")


def test_ar1_with_phase2c_authorized_is_rejected(record):
    candidate = hypothetical_ar1(record)
    candidate["authorization"]["PHASE2C_AUTHORIZED"] = True
    rejected(candidate, "Downstream authorization is true")


def test_ar1_cannot_change_historical_phase2a_to_pass(record):
    candidate = hypothetical_ar1(record)
    candidate["historical_state"]["phase2a_scientific_decision"] = "PASS"
    rejected(candidate, "Historical Phase 2A changed to PASS")


def test_ar1_cannot_change_pdf_identity(record):
    candidate = hypothetical_ar1(record)
    candidate["accepted_contract"]["pdf_family"] = "another_family"
    rejected(candidate, "Accepted PDF identity changed")


def test_ar1_with_plan_predecessor_hash_mismatch_is_rejected(record):
    candidate = hypothetical_ar1(record)
    candidate["predecessors"]["phase2b_preauthorization_plan"]["sha256"] = "0" * 64
    rejected(candidate, "Wrong predecessor SHA: phase2b_preauthorization_plan")


def test_ar1_with_anchor_removed_is_rejected(record):
    candidate = hypothetical_ar1(record)
    candidate["anchor_audit"]["anchor_count"] = 8
    rejected(candidate, "Required anchor removed")


def test_ar1_with_domain_changed_is_rejected(record):
    candidate = hypothetical_ar1(record)
    candidate["domain_audit"]["coordinates"] = ["x_Bj", "y"]
    rejected(candidate, "Domain coordinates changed")


@pytest.mark.parametrize("decision", [VALIDATOR.AR2, VALIDATOR.AR3])
def test_ar2_or_ar3_cannot_authorize_execution(record, decision):
    candidate = copy.deepcopy(record)
    candidate["decision"] = decision
    if decision == VALIDATOR.AR3:
        candidate["heavy_flavor_and_coupling_audit"]["overall_result"] = "INCONSISTENT"
        candidate["authorization_criteria"]["heavy_mass_threshold_alpha_s_identity"] = (
            "BLOCKED_SUBSTANTIVE"
        )
    candidate["authorization"]["PHASE2B_EXECUTION_AUTHORIZED"] = True
    rejected(candidate, "Phase 2B execution authorization contradicts decision")


def test_unavailable_high_precision_cannot_pass(record):
    candidate = copy.deepcopy(record)
    candidate["roundoff_and_negative_rate_audit"]["high_precision_unavailable_result"] = "PASS"
    rejected(candidate, "Unavailable high precision can pass")


def test_issue_gate_cannot_be_promoted(record):
    candidate = copy.deepcopy(record)
    candidate["github_target_state"]["gate_decision"] = "PASS"
    rejected(candidate, "Issue #55 gate decision changed")


def test_ar2_decision_is_derived_from_revision_blockers(record):
    candidate = copy.deepcopy(record)
    candidate["decision"] = VALIDATOR.AR3
    rejected(candidate, "Authorization decision is not derived")
