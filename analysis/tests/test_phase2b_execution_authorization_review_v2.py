import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_phase2b_execution_authorization_review_v2.py"
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_execution_authorization_review_v2.json"

SPEC = importlib.util.spec_from_file_location("phase2b_authorization_v2_validator", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


@pytest.fixture
def record():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def rejected(candidate, expected_message):
    with pytest.raises(VALIDATOR.ValidationError, match=expected_message):
        VALIDATOR.validate(candidate, root=ROOT, check_docs=False)


def test_cli_validates_current_ar2_successor():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "VALID phase2b.execution_authorization_review_v2" in result.stdout


def test_ar1_decision_without_passing_criteria_is_rejected(record):
    record["decision"] = VALIDATOR.AR1
    rejected(record, "Authorization decision is not derived")


def test_source_benchmark_cannot_be_promoted_to_parent_allowance(record):
    record["budget_parent_audit"]["classification"] = "BUDGET_PARENT_SOURCE_JUSTIFIED"
    rejected(record, "Unjustified T_external accepted")


def test_observed_discrepancy_cannot_be_called_formal_guarantee(record):
    record["budget_parent_audit"]["formal_guarantee"] = True
    rejected(record, "0.001 upgraded to formal guarantee")


def test_invalid_equal_split_cannot_be_declared_defensible(record):
    record["equal_split_audit"]["classification"] = "EQUAL_SPLIT_DEFENSIBLE"
    rejected(record, "Invalid equal split accepted")


def test_mixed_relative_and_absolute_budget_units_are_rejected(record):
    record["equal_split_audit"]["absolute_relative_units_compatible"] = True
    rejected(record, "Mixed budget units accepted")


def test_as2_cannot_be_authorized_with_sampled_domain_gap(record):
    record["alpha_s_audit"]["classification"] = "AS2_AUTHORIZABLE"
    rejected(record, "AS2 unresolved audit accepted")


def test_as2_requires_bottom_threshold_side_probes(record):
    record["alpha_s_audit"]["threshold_side_probes_present"] = False
    rejected(record, "Missing alpha threshold probe")


def test_bridge_plan_cannot_be_authorized_without_derived_path(record):
    record["bridge_audit"]["classification"] = "BRIDGE_PLAN_AUTHORIZABLE"
    rejected(record, "Underived bridge plan accepted")


def test_bridge_tolerance_mutation_is_rejected(record):
    record["bridge_audit"]["tolerance"] = "8*2^-53 relative"
    rejected(record, "Bridge tolerance not derived")


def test_shared_quadrature_accumulation_core_is_rejected(record):
    record["quadrature_audit"]["shared_accumulation_core"] = True
    rejected(record, "Quadrature paths share implementation core")


def test_massivedis_cannot_be_upgraded_to_full_rate_oracle(record):
    record["massivedis_audit"]["full_rate_oracle"] = True
    rejected(record, "MassiveDIS upgraded to full-rate oracle without evidence")


def test_unvalidated_reference_node_is_rejected(record):
    record["reference_graph"][0]["classification"] = "UNVALIDATED"
    rejected(record, "Reference graph classification changed")


def test_inconclusive_sign_cannot_count_as_pass(record):
    record["nr2_audit"]["inside_envelope"] = "PASS"
    rejected(record, "INCONCLUSIVE_SIGN treated as PASS")


def test_missing_upstream_error_term_is_rejected(record):
    record["nr2_audit"]["formula"] = "E_total=gamma_32*S_assembly"
    rejected(record, "Missing upstream error term")


def test_z_hat_not_above_e_z_cannot_pass(record):
    record["normalized_law_audit"]["z_hat_le_e_z_result"] = "PASS"
    rejected(record, "Z_hat<=E_Z accepted")


def test_bad_jacobian_operation_bound_is_rejected(record):
    record["jacobian_audit"]["bound"] = "4*2^-53 relative"
    rejected(record, "Bad Jacobian operation-count bound")


def test_serialized_resource_mismatch_is_rejected(record):
    record["resource_audit"]["serialized_arithmetic_total"] += 1
    rejected(record, "Serialized resource mismatch")


def test_corrected_resource_mismatch_is_rejected(record):
    record["resource_audit"]["corrected_conservative_upper_bound"] -= 1
    rejected(record, "Corrected resource mismatch")


def test_unpinned_load_bearing_numpy_cannot_be_declared_reproducible(record):
    record["dependency_audit"]["classification"] = "REPRODUCIBLE"
    rejected(record, "Unpinned load-bearing dependency accepted")


def test_numerical_execution_cannot_be_marked_complete(record):
    record["execution_state"]["phase2b"] = "EXECUTED"
    rejected(record, "Numerical execution marked complete")


def test_ar2_cannot_authorize_phase2c(record):
    record["authorization"]["PHASE2C_AUTHORIZED"] = True
    rejected(record, "AR2 cannot authorize execution or downstream work")


def test_historical_phase2a_pass_is_rejected(record):
    record["historical_state"]["phase2a_scientific_decision"] = "PASS"
    rejected(record, "Historical Phase 2A changed to PASS")


def test_pdf_family_drift_is_rejected(record):
    record["historical_state"]["accepted_pdf_family"] = "another_family"
    rejected(record, "Accepted PDF family changed")


def test_v2_predecessor_hash_drift_is_rejected(record):
    record["predecessors"]["preauthorization_v2"]["sha256"] = "0" * 64
    rejected(record, "Wrong predecessor SHA: preauthorization_v2")


def test_clipping_policy_mutation_is_rejected(record):
    record["failure_policy_audit"]["no_clipping"] = False
    rejected(record, "No-repair policy weakened: no_clipping")


def test_issue_55_cannot_be_promoted_by_ar2(record):
    record["github_target_state"]["authorization"] = "Authorized"
    rejected(record, "Issue #55 target state changed")
