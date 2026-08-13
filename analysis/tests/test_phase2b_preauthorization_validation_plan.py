import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_phase2b_preauthorization_validation_plan.py"
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan.json"

SPEC = importlib.util.spec_from_file_location("phase2b_preauth_validator", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


@pytest.fixture
def record():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def rejected(record, expected_message):
    with pytest.raises(VALIDATOR.ValidationError, match=expected_message):
        VALIDATOR.validate(record, root=ROOT, check_docs=False)


def test_cli_validates_current_artifact():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "VALID phase2b.preauthorization_validation_plan" in result.stdout


def test_authorization_true_is_rejected(record):
    record["authorization"]["PHASE2B_AUTHORIZED"] = True
    rejected(record, "Authorization flag is true")


def test_executed_state_is_rejected(record):
    record["phase2b_state"]["execution_status"] = "EXECUTED"
    rejected(record, "Phase 2B execution occurred")


def test_required_anchor_removal_is_rejected(record):
    record["theta_anchors"].pop()
    rejected(record, "Required theta anchor missing or changed")


def test_anchor_outside_accepted_domain_is_rejected(record):
    record["theta_anchors"][0]["delta_v"] = 0.21
    rejected(record, "Required theta anchor missing or changed")


def test_empty_required_grid_is_rejected(record):
    record["validation_grids"] = []
    rejected(record, "Required grid is empty")


def test_tolerance_without_justification_is_rejected(record):
    record["tolerances"][0]["justification_text"] = ""
    rejected(record, "Tolerance has empty field")


def test_standard_tolerance_rationale_is_rejected(record):
    record["tolerances"][0]["justification_text"] = "This is a standard tolerance."
    rejected(record, "Forbidden tolerance rationale")


def test_reasonable_tolerance_rationale_is_rejected(record):
    record["tolerances"][0]["justification_text"] = "This is a reasonable tolerance."
    rejected(record, "Forbidden tolerance rationale")


def test_convergence_rule_removal_is_rejected(record):
    record["convergence_rules"].pop()
    rejected(record, "Required convergence rule missing")


def test_apfel_wrapper_cannot_be_independent(record):
    wrapper = next(
        item
        for item in record["independent_reference_hierarchy"]["references"]
        if item["reference_id"] == "REF_APFEL_WRAPPER_REPETITION"
    )
    wrapper["independent"] = True
    rejected(record, "Internal repetition marked independent")


def test_clipping_is_rejected(record):
    record["positivity_no_hidden_clipping_contract"]["clipping_allowed"] = True
    rejected(record, "Forbidden positivity repair enabled: clipping_allowed")


def test_abs_repair_is_rejected(record):
    record["positivity_no_hidden_clipping_contract"]["abs_allowed"] = True
    rejected(record, "Forbidden positivity repair enabled: abs_allowed")


def test_max_rate_zero_repair_is_rejected(record):
    record["positivity_no_hidden_clipping_contract"]["max_rate_zero_allowed"] = True
    rejected(record, "Forbidden positivity repair enabled: max_rate_zero_allowed")


def test_post_hoc_support_deletion_is_rejected(record):
    record["positivity_no_hidden_clipping_contract"]["post_hoc_support_deletion_allowed"] = True
    rejected(record, "Forbidden positivity repair enabled: post_hoc_support_deletion_allowed")


def test_resource_bound_removal_is_rejected(record):
    del record["resource_bounds"]["maximum_total_declared_evaluations"]
    rejected(record, "Resource bound missing or changed")


def test_fonll_predecessor_misbinding_is_rejected(record):
    record["predecessor_identities"]["phase2_fonll_a_contract_amendment"] = "0" * 64
    rejected(record, "Wrong predecessor identity: phase2_fonll_a_contract_amendment")


def test_accepted_pdf_family_change_is_rejected(record):
    record["accepted_contract"]["pdf_family"] = "another_family"
    rejected(record, "Accepted PDF family changed")


def test_apfel_control_drift_is_rejected(record):
    record["heavy_quark_contract"]["software_controls"][-1] = "SetDampingPowerFONLL(2)"
    rejected(record, "APFEL heavy-flavor controls changed")


def test_numerical_positivity_pass_field_is_rejected(record):
    record["positivity_result"] = "PASS"
    rejected(record, "Numerical result field masquerades as planning")


def test_historical_phase2a_cannot_be_converted_to_pass(record):
    record["historical_phase2a"]["scientific_decision"] = "PASS"
    rejected(record, "Historical Phase 2A decision changed")


def test_issue_55_gate_cannot_be_promoted(record):
    record["phase2b_state"]["gate_decision"] = "PASS"
    rejected(record, "Issue #55 gate decision changed")


def test_full_end_to_end_reference_cannot_be_invented(record):
    record["independent_reference_hierarchy"]["full_end_to_end_fonll_a_observable_reference_available"] = True
    rejected(record, "Invented full FONLL-A independent reference")


def test_pre_auth_post_auth_boundary_is_exact(record):
    mutated = copy.deepcopy(record)
    mutated["pre_auth_post_auth_separation"]["post_auth_not_executed"].remove("POSITIVITY_SCAN")
    rejected(mutated, "POST_AUTH classification changed")
