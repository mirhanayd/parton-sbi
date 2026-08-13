import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_phase2b_preauthorization_validation_plan_v3.py"
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v3.json"

SPEC = importlib.util.spec_from_file_location("phase2b_preauth_v3_validator", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


@pytest.fixture
def record():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def rejected(candidate, expected_message):
    with pytest.raises(VALIDATOR.ValidationError, match=expected_message):
        VALIDATOR.validate(candidate, root=ROOT, check_docs=False)


def test_cli_validates_current_v3_artifact():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "VALID phase2b.preauthorization_validation_plan_v3" in result.stdout


def test_global_massivedis_parent_budget_is_rejected(record):
    record["error_budget_architecture"]["global_parent_budget"] = {
        "name": "T_external",
        "value": 0.001,
    }
    rejected(record, "Global parent budget reintroduced")


def test_equal_eighth_split_is_rejected(record):
    record["error_budget_architecture"]["equal_share_allocation"] = [0.000125] * 8
    rejected(record, "Equal 1/8 split reintroduced")


def test_282_point_only_alpha_claim_is_rejected(record):
    record["alpha_s_architecture"]["scientific_requirement"] = "282 sampled Q points prove continuous equivalence"
    rejected(record, "Sample-only continuous alpha claim reintroduced")


def test_alpha_interval_coverage_is_required(record):
    record["alpha_s_architecture"]["continuous_certificate"]["breakpoints"] = "only endpoints"
    rejected(record, "Alpha interval coverage incomplete")


def test_alpha_subdivision_cap_is_required(record):
    record["alpha_s_architecture"]["continuous_certificate"]["traversal"] = "bisect until pass"
    rejected(record, "Alpha subdivision cap missing")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("set", "CT18NNLO"),
        ("member", 1),
        ("archive_sha256", "0" * 64),
        ("info_sha256", "0" * 64),
        ("member_sha256", "0" * 64),
    ],
)
def test_wrong_pdf_identity_is_rejected(record, field, value):
    record["pdf_artifact_contract"]["raw"][field] = value
    rejected(record, "Raw PDF contract changed")


def test_flavor_permutation_is_rejected(record):
    record["pdf_artifact_contract"]["raw"]["flavor_order"][0:2] = [-4, -5]
    rejected(record, "Raw PDF contract changed")


def test_x_vs_xf_bridge_defect_is_rejected(record):
    record["bridge_contract"]["value_source"] = "ContinuousPdfPoint densities are copied without x"
    rejected(record, "Bridge x/xf rule missing")


def test_double_x_bridge_defect_is_rejected(record):
    record["bridge_contract"]["value_source"] = "multiply x*f twice"
    rejected(record, "Bridge x/xf rule missing")


def test_sign_loss_bridge_defect_is_rejected(record):
    record["bridge_contract"]["invariants"].remove("B4_SIGN_PRESERVATION")
    rejected(record, "Bridge B1-B8 incomplete")


def test_unexplained_16u_bridge_tolerance_is_rejected(record):
    record["bridge_contract"]["floating_derivation"] = "Use a 16u tolerance"
    rejected(record, "Unexplained 16u bridge tolerance reintroduced")


def test_negative_to_zero_conversion_is_rejected(record):
    record["sign_contract"]["exact_semantics"][2] = "raw rate < 0 => replace with zero"
    rejected(record, "Strict raw sign rule changed")


def test_epsilon_clipped_sign_pass_is_rejected(record):
    record["sign_contract"]["exact_semantics"][4] = "Use epsilon and clip small negatives"
    rejected(record, "Sign repair prohibition missing: no clipping")


def test_inconclusive_counted_as_pass_is_rejected(record):
    record["alpha_s_architecture"]["continuous_certificate"]["inconclusive"] = "At depth 12 count undecided cells as PASS"
    rejected(record, "Alpha INCONCLUSIVE rule missing")


def test_standalone_normalized_law_tolerance_is_rejected(record):
    test = next(item for item in record["post_authorization_tests"] if item["test_id"] == "TEST_NORMALIZED_LAW")
    test["threshold_or_rule"] = "PASS at absolute residual <=0.0013"
    rejected(record, "Standalone normalized-law tolerance introduced")


def test_missing_cross_quadrature_rule_is_rejected(record):
    test = next(item for item in record["post_authorization_tests"] if item["test_id"] == "TEST_CROSS_QUADRATURE")
    test.pop("threshold_or_rule")
    rejected(record, "Incomplete post-auth test fields")


def test_incomplete_fully_specified_postauth_test_is_rejected(record):
    test = next(item for item in record["post_authorization_tests"] if item["test_id"] == "TEST_BRIDGE")
    test["metric"] = None
    rejected(record, "Fully specified test missing metric")


def test_v3r1_with_unvalidated_load_bearing_node_is_rejected(record):
    record["outcome"]["code"] = "V3R1_PREAUTH_V3_COMPLETE_READY_FOR_AUTHORIZATION_REVIEW"
    rejected(record, "V3R1 with UNVALIDATED load-bearing node")


def test_unpinned_python_is_rejected(record):
    record["dependency_freeze"]["python"]["version"] = "3.10"
    rejected(record, "Python runtime source identity changed")


def test_unpinned_numpy_is_rejected(record):
    record["dependency_freeze"]["packages"]["numpy"]["version"] = ">=1.26"
    rejected(record, "Pinned package wheel/API identity changed")


def test_inconsistent_resource_count_is_rejected(record):
    test = next(item for item in record["post_authorization_tests"] if item["test_id"] == "TEST_BRIDGE")
    test["resource_count"]["slot_comparisons"] += 1
    rejected(record, "Bridge resource arithmetic changed")


def test_fabricated_aggregate_resource_total_is_rejected(record):
    record["resource_model"]["aggregate_maximum"] = 841685
    rejected(record, "Fabricated aggregate resource maximum")


def test_retry_until_pass_is_rejected(record):
    record["resource_model"]["retry_until_pass_allowed"] = True
    rejected(record, "Retry-until-pass allowed")


@pytest.mark.parametrize(
    "field",
    ["PHASE2B_AUTHORIZED", "PHASE2B_EXECUTION_AUTHORIZED", "PHASE2C_AUTHORIZED"],
)
def test_authorization_true_is_rejected(record, field):
    record["authorization"][field] = True
    rejected(record, "Authorization flag is true")


def test_execution_true_is_rejected(record):
    record["execution_state"]["phase2b"] = "EXECUTED"
    rejected(record, "Phase 2B execution occurred")


def test_pdf_family_drift_is_rejected(record):
    record["pdf_artifact_contract"]["projected"]["family"] = "another_family"
    rejected(record, "Projected PDF identity changed: family")


def test_historical_phase2a_pass_is_rejected(record):
    record["historical_state"]["phase2a_scientific_decision"] = "PASS"
    rejected(record, "Historical Phase 2A changed to PASS")


def test_defect_d3_cannot_be_promoted_to_resolved(record):
    record["established_defects"]["D3_AS2_CONTINUOUS_DOMAIN_UNDERDEFINED"]["resolution"] = "RESOLVED_AT_PLAN_LEVEL"
    rejected(record, "Wrong defect resolution: D3_AS2_CONTINUOUS_DOMAIN_UNDERDEFINED")


def test_defect_d8_runtime_gap_cannot_be_hidden(record):
    record["established_defects"]["D8_REPRODUCIBILITY_INCOMPLETE"]["resolution"] = "RESOLVED"
    rejected(record, "Wrong defect resolution: D8_REPRODUCIBILITY_INCOMPLETE")


def test_source_hash_mutation_is_rejected(record):
    source = next(item for item in record["source_registry_additions"] if item["source_id"] == "SCIPY_1_15_3_CP310_MANYLINUX2014_X86_64_WHEEL")
    source["sha256"] = "0" * 64
    rejected(record, "Wrong source SHA: SCIPY_1_15_3_CP310_MANYLINUX2014_X86_64_WHEEL")


def test_source_registry_omission_is_rejected(record):
    record["source_registry_additions"].pop()
    rejected(record, "Source registry identity set changed")


def test_apfel_control_mutation_is_rejected(record):
    record["alpha_s_architecture"]["provider_b"]["controls"][0] = "SetAlphaQCDRef(0.117,91.187)"
    rejected(record, "APFEL alpha controls changed")


def test_apfel_source_hash_mutation_is_rejected(record):
    record["alpha_s_architecture"]["source_file_hashes"]["a_qcd"] = "0" * 64
    rejected(record, "APFEL source-file hashes changed")


def test_alpha_backend_gap_cannot_be_hidden(record):
    record["alpha_s_architecture"]["interval_backend_identity"] = "unreviewed/backend.py"
    rejected(record, "Unverified interval backend asserted")


def test_alpha_gate_cannot_be_promoted_while_specification_is_blocked(record):
    gate = next(
        item
        for item in record["gate_local_architecture"]
        if item["gate_id"] == "G3_ALPHA_S_CONSISTENCY"
    )
    gate["status"] = "FULLY_SPECIFIED_NOT_EXECUTED"
    rejected(record, "Wrong gate status: G3_ALPHA_S_CONSISTENCY")


def test_alpha_resource_candidate_cannot_be_promoted(record):
    test = next(item for item in record["post_authorization_tests"] if item["test_id"] == "TEST_ALPHA")
    test["resource_count"] = record["alpha_s_architecture"]["non_authoritative_candidate_ceiling"].copy()
    rejected(record, "Blocked alpha resource count fabricated")


def test_raw_pdf_support_mutation_is_rejected(record):
    record["pdf_artifact_contract"]["raw"]["x_support"] = [1e-8, 1]
    rejected(record, "Raw PDF contract changed")


def test_anchor_hash_mutation_is_rejected(record):
    record["pdf_artifact_contract"]["projected"]["anchors"][0]["canonical_identity"] = "sha256:" + "0" * 64
    rejected(record, "Projected PDF anchors changed")


def test_bridge_oracle_hash_mutation_is_rejected(record):
    record["bridge_contract"]["oracle"]["sha256"] = "0" * 64
    rejected(record, "Bridge oracle identity changed: sha256")


def test_bridge_signed_zero_callback_omission_is_rejected(record):
    record["bridge_contract"]["sentinels"].pop("signed_zero_callback")
    rejected(record, "Bridge signed-zero callback missing")


def test_bridge_identity_case_omission_is_rejected(record):
    record["bridge_contract"]["identity_cases"].pop()
    rejected(record, "Bridge identity cases incomplete")


def test_bridge_identity_case_same_length_mutation_is_rejected(record):
    record["bridge_contract"]["identity_cases"][1] = "B1_01_SET: accept any set"
    rejected(record, "Bridge exact case inventory changed: identity_cases")


def test_bridge_q_case_omission_is_rejected(record):
    record["bridge_contract"]["q_cases"].pop()
    rejected(record, "Bridge Q cases incomplete")


def test_massless_table_token_mutation_is_rejected(record):
    test = next(item for item in record["post_authorization_tests"] if item["test_id"] == "TEST_MASSLESS")
    test["exact_finite_domain_grid"][0]["published_tokens"]["F1_NC"] = "4.9967e+4"
    rejected(record, "Massless published table changed")


def test_blocked_massless_rule_cannot_be_asserted(record):
    test = next(item for item in record["post_authorization_tests"] if item["test_id"] == "TEST_MASSLESS")
    test["threshold_or_rule"] = "PASS when values agree"
    rejected(record, "Blocked massless acceptance rule asserted")


def test_dependency_wheel_hash_mutation_is_rejected(record):
    record["dependency_freeze"]["packages"]["numpy"]["sha256"] = "0" * 64
    rejected(record, "Pinned package wheel/API identity changed")


def test_runtime_identity_blocker_cannot_be_hidden(record):
    record["dependency_freeze"]["status"] = "RESOLVED"
    rejected(record, "Runtime identity blocker hidden")


def test_resource_cross_copy_mutation_is_rejected(record):
    record["resource_model"]["per_test"]["TEST_BRIDGE"]["total_logical_cases"] += 1
    rejected(record, "Resource cross-copy differs: TEST_BRIDGE")


def test_massless_inventory_cannot_be_counted_as_execution_cost(record):
    record["resource_model"]["per_test"]["TEST_MASSLESS"] = {"coordinate_invocations": 27}
    rejected(record, "Resource cross-copy differs: TEST_MASSLESS")


def test_reference_alpha_status_cannot_be_promoted(record):
    node = next(item for item in record["reference_coverage_graph"] if item["node"] == "alpha_s")
    node["status"] = "INDEPENDENT_POSTAUTH_TEST_FULLY_SPECIFIED"
    rejected(record, "Wrong reference status: alpha_s")


def test_missing_outcome_category_is_rejected(record):
    record["outcome"]["blockers"] = record["outcome"]["blockers"][:-1]
    rejected(record, "Multiple blocker derivation incomplete")


def test_v3r1_outcome_implications_are_reachable(record):
    record["outcome"]["code"] = "V3R1_PREAUTH_V3_COMPLETE_READY_FOR_AUTHORIZATION_REVIEW"
    rejected(record, "V3R1 with UNVALIDATED load-bearing node")


def test_wrong_specific_outcome_is_rejected_after_implication_validation(record):
    record["outcome"]["code"] = "V3R2_ALPHA_S_CERTIFICATION_BLOCKED"
    rejected(record, "V3R2 blocker derivation inconsistent")
