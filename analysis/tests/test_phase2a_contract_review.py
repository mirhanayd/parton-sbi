import os
import json
import pytest
import subprocess
import copy
import sys

def run_validator(reg_data, led_data, rev_data, phase2b_data, tmp_path, synchronize_dependency_hashes=True):
    reg_path = tmp_path / "phase2a_source_registry.json"
    led_path = tmp_path / "phase2a_claim_source_ledger.json"
    p2b_path = tmp_path / "phase2b_validation_plan_proposal.json"
    
    with open(reg_path, "w") as f:
        json.dump(reg_data, f)
    with open(led_path, "w") as f:
        json.dump(led_data, f)
    with open(p2b_path, "w") as f:
        json.dump(phase2b_data, f)

    if synchronize_dependency_hashes:
        import hashlib
        def file_sha256(path):
            with open(path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        rev_data['source_registry_identity'] = file_sha256(reg_path)
        rev_data['claim_ledger_identity'] = file_sha256(led_path)
        rev_data['phase2b_validation_plan_identity'] = file_sha256(p2b_path)

    rev_path = tmp_path / "phase2a_contract_review.json"
    with open(rev_path, "w") as f:
        json.dump(rev_data, f)

    script_path = os.path.abspath("scripts/phase2a_contract_review.py")
    
    # We need to temporarily mock the open() calls in the script or run it from a monkeypatched dir
    # Since the script hardcodes 'docs/reduced_nc_dis/sources/...', we will symlink or just run a patched version.
    # A better way for the test is to copy the script, replace paths, and run it.
    script_content = open(script_path).read()
    script_content = script_content.replace("'docs/reduced_nc_dis/sources/phase2a_source_registry.json'", f"'{reg_path.as_posix()}'")
    script_content = script_content.replace("'docs/reduced_nc_dis/contracts/phase2a_claim_source_ledger.json'", f"'{led_path.as_posix()}'")
    script_content = script_content.replace("'docs/reduced_nc_dis/contracts/phase2b_validation_plan_proposal.json'", f"'{p2b_path.as_posix()}'")
    script_content = script_content.replace("'docs/reduced_nc_dis/contracts/phase2a_contract_review.json'", f"'{rev_path.as_posix()}'")
    script_content = script_content.replace('"docs/reduced_nc_dis/sources/phase2a_source_registry.json"', f"'{reg_path.as_posix()}'")
    script_content = script_content.replace('"docs/reduced_nc_dis/contracts/phase2a_claim_source_ledger.json"', f"'{led_path.as_posix()}'")
    script_content = script_content.replace('"docs/reduced_nc_dis/contracts/phase2b_validation_plan_proposal.json"', f"'{p2b_path.as_posix()}'")
    script_content = script_content.replace('"docs/reduced_nc_dis/contracts/phase2a_contract_review.json"', f"'{rev_path.as_posix()}'")
    # For ADR check
    script_content = script_content.replace("'docs/adr/ADR-013-reduced-nc-dis-observation-law-contract.md'", "'docs/adr/ADR-013-reduced-nc-dis-observation-law-contract.md'")
    
    test_script_path = tmp_path / "test_script.py"
    with open(test_script_path, "w") as f:
        f.write(script_content)
        
    res = subprocess.run([sys.executable, str(test_script_path)], capture_output=True, text=True)
    return res.returncode, res.stdout

@pytest.fixture
def base_data():
    with open('docs/reduced_nc_dis/sources/phase2a_source_registry.json') as f:
        reg = json.load(f)
    with open('docs/reduced_nc_dis/contracts/phase2a_claim_source_ledger.json') as f:
        led = json.load(f)
    with open('docs/reduced_nc_dis/contracts/phase2a_contract_review.json') as f:
        rev = json.load(f)
    with open('docs/reduced_nc_dis/contracts/phase2b_validation_plan_proposal.json') as f:
        p2b = json.load(f)
    return reg, led, rev, p2b

def test_valid():
    rc = subprocess.run([sys.executable, "scripts/phase2a_contract_review.py"], capture_output=True, text=True).returncode
    assert rc == 0

def test_wrong_doi(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    reg['sources'][0]['persistent_identifiers']['DOI'] = "99.invalid/doi"
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "Invalid DOI format" in out

def test_missing_date(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    del reg['sources'][0]['version_date']
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "Missing publication or version date" in out

def test_gate_derivation_fail(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    # Actually change a required claim status
    led['claim_records'][0]['support_status'] = "NOT_SUPPORTED"
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "does not match derived" in out

def test_decision_derivation_fail(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    # The decision is natively INCONCLUSIVE in v3. We change it to PASS to trigger failure.
    rev['scientific_decision'] = "PASS"
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "does not match derived INCONCLUSIVE" in out

def test_hash_mutation(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    reg['sources'][0]['retrieval']['byte_sha256'] = "badhash"
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "Missing or invalid byte hash" in out

def test_contradicted_source(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    reg['sources'][0]['identity_status'] = "CONTRADICTED"
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "Claim binds to contradicted source" in out

def test_missing_precise_locator(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    led['claim_records'][0]['exact_locators'] = {}
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "Missing precise locators" in out

def test_direct_support_without_binding(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    led['claim_records'][0]['evidence_kind'] = "SOURCE_FACT"
    led['claim_records'][0]['source_bindings'] = []
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "requires valid active source binding" in out

def test_empty_gate_deps(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    rev['gate_reviews'][0]['required_claim_ids'] = []
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "lists gate" in out and "but gate does not list claim" in out

def test_executed_status(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    rev['obligation_reviews'][0]['later_execution_status'] = "EXECUTED"
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "has executed status" in out

def test_phase2b_authorized(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    rev['authorization']['PHASE2B_AUTHORIZED'] = True
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "Phase 2B authorized" in out

def test_missing_nonclaim(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    rev['paper_claim_boundary']['forbidden'] = []
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "Missing full-generator equivalence nonclaim" in out

def test_wrong_predecessor(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    rev['predecessor_identities']['phase1bd_revision'] = "bad"
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "Wrong phase1bd hash" in out

def test_wrong_schema(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    reg['schema_version'] = "v1"
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "Wrong registry schema" in out

def test_missing_cross_artifact_hashes(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    rev['source_registry_identity'] = "badhash"
    rc, out = run_validator(reg, led, rev, p2b, tmp_path, synchronize_dependency_hashes=False)
    assert rc != 0
    assert "Mismatched source_registry_identity" in out

def test_missing_pass_blocking_flag(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    # Add a qualified claim without blocking flag
    led['claim_records'][0]['support_status'] = "SUPPORTED_WITH_QUALIFICATION"
    if 'phase2a_pass_blocking' in led['claim_records'][0]:
        del led['claim_records'][0]['phase2a_pass_blocking']
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "SUPPORTED_WITH_QUALIFICATION must have phase2a_pass_blocking" in out

def test_pass_blocking_derivation(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    # Give it pass blocking
    led['claim_records'][0]['support_status'] = "SUPPORTED_WITH_QUALIFICATION"
    led['claim_records'][0]['phase2a_pass_blocking'] = True
    led['claim_records'][0]['blocking_reason'] = "Test blocking"
    # The gate is exact_formula_contract which is natively PRIMARY_EVIDENCE_UNAVAILABLE
    # To trigger a failure, we change the gate status to something else (e.g. SUPPORTED)
    rev['gate_reviews'][0]['status'] = "SUPPORTED"
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "does not match derived PRIMARY_EVIDENCE_UNAVAILABLE" in out

def test_empty_p2b_bounds(base_data, tmp_path):
    reg, led, rev, p2b = copy.deepcopy(base_data)
    p2b['plan_completeness'] = "COMPLETE"
    p2b['anchors'] = []
    rc, out = run_validator(reg, led, rev, p2b, tmp_path)
    assert rc != 0
    assert "Phase 2B plan has empty anchors" in out
