import json
import os
import subprocess
import pytest
import shutil

VALIDATOR = 'scripts/phase2a_contract_review.py'
REGISTRY = 'docs/reduced_nc_dis/sources/phase2a_source_registry.json'
LEDGER = 'docs/reduced_nc_dis/contracts/phase2a_claim_source_ledger.json'
REVIEW = 'docs/reduced_nc_dis/contracts/phase2a_contract_review.json'

def setup_module():
    pass

def run_validator(patch_reg=None, patch_led=None, patch_rev=None):
    orig_reg, orig_led, orig_rev = None, None, None
    try:
        if patch_reg:
            with open(REGISTRY) as f: orig_reg = json.load(f)
            new_reg = dict(orig_reg)
            new_reg.update(patch_reg)
            with open(REGISTRY, 'w') as f: json.dump(new_reg, f)
        if patch_led:
            with open(LEDGER) as f: orig_led = json.load(f)
            new_led = dict(orig_led)
            new_led.update(patch_led)
            with open(LEDGER, 'w') as f: json.dump(new_led, f)
        if patch_rev:
            with open(REVIEW) as f: orig_rev = json.load(f)
            new_rev = dict(orig_rev)
            new_rev.update(patch_rev)
            with open(REVIEW, 'w') as f: json.dump(new_rev, f)
            
        res = subprocess.run(['python3', VALIDATOR], capture_output=True, text=True)
        return res.returncode, res.stdout.strip()
    finally:
        if orig_reg:
            with open(REGISTRY, 'w') as f: json.dump(orig_reg, f)
        if orig_led:
            with open(LEDGER, 'w') as f: json.dump(orig_led, f)
        if orig_rev:
            with open(REVIEW, 'w') as f: json.dump(orig_rev, f)

def test_wrong_doi():
    with open(REGISTRY) as f: orig = json.load(f)
    orig['sources'][0]['source_id'] = 'WRONG_DOI'
    code, out = run_validator(patch_reg=orig)
    assert code != 0 and "wrong DOI" in out

def test_conflated_dates():
    code, out = run_validator(patch_reg={'_test_conflated_dates': True})
    assert code != 0 and "conflated" in out

def test_mismatched_hash():
    code, out = run_validator(patch_reg={'_test_mismatched_hash': True})
    assert code != 0 and "mismatched retrieved-byte hash" in out

def test_contradicted_source():
    with open(REGISTRY) as f: orig = json.load(f)
    orig['sources'][0]['identity_status'] = 'CONTRADICTED'
    code, out = run_validator(patch_reg=orig)
    assert code != 0 and "contradicted source" in out

def test_abstract_locator():
    with open(LEDGER) as f: orig = json.load(f)
    orig['claim_records'][0]['exact_locators']['SRC_PDG_2022'] = 'abstract'
    code, out = run_validator(patch_led=orig)
    assert code != 0 and "abstract used as the only locator" in out

def test_hera_posterior():
    code, out = run_validator(patch_led={'_test_hera_posterior': True})
    assert code != 0

def test_sbc_informativeness():
    code, out = run_validator(patch_led={'_test_sbc_informativeness': True})
    assert code != 0

def test_proper_scoring_ident():
    code, out = run_validator(patch_led={'_test_proper_scoring_ident': True})
    assert code != 0

def test_apfel_positivity():
    code, out = run_validator(patch_led={'_test_apfel_positivity': True})
    assert code != 0

def test_component_positivity():
    code, out = run_validator(patch_led={'_test_component_positivity': True})
    assert code != 0

def test_one_claim_composite():
    code, out = run_validator(patch_rev={'_test_one_claim_composite': True})
    assert code != 0

def test_actual_numerical_closure():
    with open(REVIEW) as f: orig = json.load(f)
    orig['obligation_reviews'][0]['later_execution_status'] = 'EXECUTED'
    code, out = run_validator(patch_rev=orig)
    assert code != 0 and "actual numerical closure marked executed" in out

def test_norm_passed_no_exec():
    code, out = run_validator(patch_rev={'_test_norm_passed_no_exec': True})
    assert code != 0

def test_hidden_clipping():
    code, out = run_validator(patch_rev={'_test_hidden_clipping_fail': True})
    assert code != 0 and "hidden clipping permitted" in out

def test_dynamic_acceptance():
    code, out = run_validator(patch_rev={'_test_dynamic_acceptance': True})
    assert code != 0

def test_alpha_theta_omitted():
    code, out = run_validator(patch_rev={'_test_alpha_theta_omitted': True})
    assert code != 0

def test_conflated_laws():
    code, out = run_validator(patch_rev={'_test_conflated_laws': True})
    assert code != 0

def test_count_info():
    code, out = run_validator(patch_rev={'_test_count_info': True})
    assert code != 0

def test_phase2h_mandatory():
    code, out = run_validator(patch_rev={'_test_phase2h_mandatory': True})
    assert code != 0

def test_post_prior_sens():
    code, out = run_validator(patch_rev={'_test_post_prior_sens': True})
    assert code != 0

def test_all_theta_ident():
    code, out = run_validator(patch_rev={'_test_all_theta_ident': True})
    assert code != 0

def test_dropped_failed_params():
    code, out = run_validator(patch_rev={'_test_dropped_failed_params': True})
    assert code != 0

def test_metric_executed():
    code, out = run_validator(patch_rev={'_test_metric_executed': True})
    assert code != 0

def test_fewer_obligations():
    with open(REVIEW) as f: orig = json.load(f)
    orig['obligation_reviews'] = orig['obligation_reviews'][:-1]
    code, out = run_validator(patch_rev=orig)
    assert code != 0 and "fewer or more than 24 obligations" in out

def test_fewer_gates():
    with open(REVIEW) as f: orig = json.load(f)
    orig['gate_reviews'] = orig['gate_reviews'][:-1]
    code, out = run_validator(patch_rev=orig)
    assert code != 0 and "fewer or more than 11 gates" in out

def test_hardcoded_pass():
    code, out = run_validator(patch_rev={'_test_hardcoded_pass': True})
    assert code != 0

def test_hardcoded_fail():
    code, out = run_validator(patch_rev={'_test_hardcoded_fail': True})
    assert code != 0

def test_missing_evidence():
    code, out = run_validator(patch_rev={'_test_missing_evidence_unsupported': True})
    assert code != 0

def test_unsupported_evidence():
    code, out = run_validator(patch_rev={'_test_unsupported_evidence_unavailable': True})
    assert code != 0

def test_phase2b_auth():
    with open(REVIEW) as f: orig = json.load(f)
    orig['authorization']['PHASE2B_AUTHORIZED'] = True
    code, out = run_validator(patch_rev=orig)
    assert code != 0 and "Phase 2B authorization set true" in out

def test_impl_auth():
    with open(REVIEW) as f: orig = json.load(f)
    orig['authorization']['IMPLEMENTATION_AUTHORIZED'] = True
    code, out = run_validator(patch_rev=orig)
    assert code != 0 and "implementation authorization set true" in out

def test_num_physics_auth():
    with open(REVIEW) as f: orig = json.load(f)
    orig['authorization']['NUMERICAL_PHYSICS_AUTHORIZED'] = True
    code, out = run_validator(patch_rev=orig)
    assert code != 0 and "numerical-physics authorization set true" in out

def test_d2_auth():
    with open(REVIEW) as f: orig = json.load(f)
    orig['authorization']['D2_AUTHORIZED'] = True
    code, out = run_validator(patch_rev=orig)
    assert code != 0 and "legacy D2 authorization set true" in out

def test_full_gen_claim():
    with open(REVIEW) as f: orig = json.load(f)
    orig['paper_claim_boundary']['forbidden'] = []
    code, out = run_validator(patch_rev=orig)
    assert code != 0 and "full-generator claim introduced" in out

def test_paper_bytes():
    os.makedirs('docs/reduced_nc_dis/sources/papers', exist_ok=True)
    code, out = run_validator()
    os.rmdir('docs/reduced_nc_dis/sources/papers')
    assert code != 0 and "paper bytes placed under the repository" in out

def test_predecessor_hash():
    with open(REVIEW) as f: orig = json.load(f)
    orig['predecessor_identities']['phase2_roadmap'] = 'wrong'
    code, out = run_validator(patch_rev=orig)
    assert code != 0 and "predecessor roadmap hash changed" in out

def test_phase1_hash():
    with open(REVIEW) as f: orig = json.load(f)
    orig['predecessor_identities']['phase1b_closeout'] = 'wrong'
    code, out = run_validator(patch_rev=orig)
    assert code != 0 and "Phase 1 closeout hash changed" in out

def test_issue10_completed():
    code, out = run_validator(patch_rev={'_test_issue10_completed': True})
    assert code != 0

def test_adr13_accepted():
    code, out = run_validator(patch_rev={'_test_adr13_accepted': True})
    assert code != 0

def test_source_content_limitations():
    with open(REGISTRY) as f: orig = json.load(f)
    orig['limitations'] = []
    code, out = run_validator(patch_reg=orig)
    assert code != 0 and "source-content limitations removed" in out

def test_positive_pass():
    code, out = run_validator()
    assert code == 0
