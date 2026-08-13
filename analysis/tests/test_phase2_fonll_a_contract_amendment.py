import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_phase2_fonll_a_contract_amendment.py"
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2_fonll_a_contract_amendment.json"

SPEC = importlib.util.spec_from_file_location("fonll_a_validator", SCRIPT)
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
    assert "VALID phase2.fonll_a_contract_amendment" in result.stdout


def test_historical_phase2a_must_remain_inconclusive(record):
    record["historical_phase2a"]["scientific_decision"] = "PASS"
    rejected(record, "Historical Phase 2A decision changed")


def test_source_hash_is_exact(record):
    record["source_evidence"][0]["sha256"] = "0" * 64
    rejected(record, "Wrong sha256 for HERA_2015_V3")


def test_apfel_commit_is_exact(record):
    source = next(item for item in record["source_evidence"] if item["source_id"] == "APFEL_SOURCE_3_1_1")
    source["commit"] = "0" * 40
    rejected(record, "Wrong commit for APFEL_SOURCE_3_1_1")


def test_all_twenty_candidate_criteria_are_required(record):
    del record["candidate_assessments"]["APFEL_FONLL_A_NLO"]["matching_conditions"]
    rejected(record, "Wrong criteria for APFEL_FONLL_A_NLO")


def test_eligibility_is_derived_from_elimination_checks(record):
    record["candidate_assessments"]["APFEL_FONLL_A_NLO"]["elimination_checks"]["requires_hidden_repair"] = True
    rejected(record, "Eligibility is not derived for APFEL_FONLL_A_NLO")


def test_decision_is_derived_from_unique_eligible_candidate(record):
    candidate = record["candidate_assessments"]["APFEL_FONLL_A_NLO"]
    candidate["elimination_checks"]["requires_hidden_repair"] = True
    candidate["eligible"] = False
    record["eligibility"]["eligible_candidates"] = []
    rejected(record, "Decision is not derived from elimination checks")


def test_ffn_cannot_silently_replace_pdf_contract(record):
    record["special_classifications"]["ffn"] = "FFN_COMPATIBLE_WITH_ACCEPTED_PDF_FAMILY"
    rejected(record, "Wrong FFN classification")


def test_zmvfn_requires_predeclared_domain(record):
    record["special_classifications"]["zm_vfn"] = "ZMVFN_NO_DOMAIN_NARROWING_REQUIRED"
    rejected(record, "Wrong ZM-VFN classification")


def test_rtopt_implementation_path_remains_unbound(record):
    record["special_classifications"]["rtopt"] = "RTOPT_IMPLEMENTATION_PATH_BOUND"
    rejected(record, "Wrong RTOPT classification")


def test_hidden_repairs_are_rejected(record):
    record["contract_amendment"]["clipping_allowed"] = True
    rejected(record, "Clipping allowed")


def test_unresolved_pre_auth_evidence_cannot_be_promoted(record):
    record["pre_auth_contract_evidence"]["currently_unresolved"].remove("planned_theta_anchors")
    rejected(record, "Unresolved pre-auth item promoted: planned_theta_anchors")


def test_post_auth_numerical_work_remains_unexecuted(record):
    record["post_auth_numerical_validation"]["not_executed"].remove("positivity_scan")
    rejected(record, "Post-auth execution status changed")


def test_every_authorization_flag_remains_false(record):
    record["authorization"]["PHASE2B_AUTHORIZED"] = True
    rejected(record, "An authorization flag is true")


def test_phase2b_remains_incomplete_and_unexecuted(record):
    record["phase2b_state"]["plan_completeness"] = "COMPLETE"
    rejected(record, "Phase 2B plan promoted")


def test_decision_matrix_has_all_ten_scored_criteria(record):
    del record["decision_matrix"]["APFEL_ZM_VFN"]["reversibility"]
    rejected(record, "Wrong decision-matrix criteria for APFEL_ZM_VFN")


def test_source_bytes_are_not_committed(record):
    mutated = copy.deepcopy(record)
    mutated["validation"]["source_bytes_committed"] = True
    rejected(mutated, "Source bytes claimed committed")
