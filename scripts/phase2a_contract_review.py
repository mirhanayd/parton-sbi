import json
import os
import sys
import re
import hashlib
from pathlib import Path

def check(condition, message):
    if not condition:
        print(f"Validation Error: {message}")
        sys.exit(1)

def file_sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def check_adr013_consistency(review, phase2b):
    adr_path = Path("docs/adr/ADR-013-reduced-nc-dis-observation-law-contract.md")
    try:
        adr = adr_path.read_text()
    except FileNotFoundError:
        check(False, "Missing ADR-013")

    check(re.search(r'## Status\s+Proposed', adr, re.IGNORECASE), "ADR-013 is not Proposed")

    decision = review['scientific_decision']
    check(f"scientific decision is `{decision}`" in adr, "ADR-013 decision does not match review")

    unavailable_gate_ids = [
        gate['gate_id']
        for gate in review['gate_reviews']
        if gate['status'] == "PRIMARY_EVIDENCE_UNAVAILABLE"
    ]
    for gate_id in unavailable_gate_ids:
        check(gate_id in adr, f"ADR-013 missing unavailable gate {gate_id}")

    check(f"plan_completeness = {phase2b.get('plan_completeness')}" in adr, "ADR-013 Phase 2B completeness mismatch")
    check(f"authorization = {phase2b.get('authorization')}" in adr, "ADR-013 Phase 2B authorization mismatch")
    check(f"execution_status = {phase2b.get('execution_status')}" in adr, "ADR-013 Phase 2B execution mismatch")

    if decision != "PASS":
        stale_pass_claims = [
            "All 11 binding gates evaluate to SUPPORTED",
            "provisional decision is PASS",
            "decision is PASS",
            "Recommends the Phase 2B validation proposal",
        ]
        for claim in stale_pass_claims:
            check(claim not in adr, f"ADR-013 contains stale PASS claim: {claim}")

def main():
    try:
        with open('docs/reduced_nc_dis/sources/phase2a_source_registry.json') as f:
            registry = json.load(f)
        with open('docs/reduced_nc_dis/contracts/phase2a_claim_source_ledger.json') as f:
            ledger = json.load(f)
        with open('docs/reduced_nc_dis/contracts/phase2a_contract_review.json') as f:
            review = json.load(f)
        with open('docs/reduced_nc_dis/contracts/phase2b_validation_plan_proposal.json') as f:
            phase2b = json.load(f)
    except FileNotFoundError:
        check(False, "Missing JSON files")

    # exact schemas (v3)
    check(registry.get("schema_version") == "partonsbi.phase2a.source-registry.v3", "Wrong registry schema")
    check(ledger.get("schema_version") == "partonsbi.phase2a.claim-source-ledger.v3", "Wrong ledger schema")
    check(review.get("schema_version") == "partonsbi.phase2a.reduced-nc-dis-contract-review.v3", "Wrong review schema")
    check(phase2b.get("schema_version") == "partonsbi.phase2b.reduced-nc-dis-validation-plan-proposal.v3", "Wrong phase2b schema")

    # exact cross-artifact hash verification
    reg_hash = file_sha256("docs/reduced_nc_dis/sources/phase2a_source_registry.json")
    led_hash = file_sha256("docs/reduced_nc_dis/contracts/phase2a_claim_source_ledger.json")
    p2b_hash = file_sha256("docs/reduced_nc_dis/contracts/phase2b_validation_plan_proposal.json")
    check(review.get('source_registry_identity') == reg_hash, "Mismatched source_registry_identity")
    check(review.get('claim_ledger_identity') == led_hash, "Mismatched claim_ledger_identity")
    check(review.get('phase2b_validation_plan_identity') == p2b_hash, "Mismatched phase2b_validation_plan_identity")

    # source-id uniqueness
    src_ids = [s['source_id'] for s in registry['sources']]
    check(len(src_ids) == len(set(src_ids)), "Duplicate source IDs")

    # claim-id uniqueness
    claim_ids = [c['claim_id'] for c in ledger['claim_records']]
    check(len(claim_ids) == len(set(claim_ids)), "Duplicate claim IDs")

    # source rules
    for src in registry['sources']:
        doi = src['persistent_identifiers'].get('DOI')
        if doi:
            check(doi.startswith('10.'), "Invalid DOI format")
        
        pub_date = src.get('publication_date')
        ver_date = src.get('version_date')
        check(pub_date and ver_date, "Missing publication or version date")
        
        # retrieval status semantics
        ret_status = src['retrieval'].get('retrieval_status')
        if ret_status == 'RETRIEVED':
            sha = src['retrieval'].get('byte_sha256')
            check(sha and re.match(r'^[a-fA-F0-9]{64}$', sha), "Missing or invalid byte hash for RETRIEVED source")
        
        if src.get('identity_status') == 'VERIFIED':
            check(ret_status == 'RETRIEVED' or src['source_class'] == 'AUTHORITATIVE_REVIEW', "VERIFIED source must be retrieved or authoritative review")

    # contradicted-source exclusion
    contradicted_sources = {s['source_id'] for s in registry['sources'] if s.get('identity_status') == 'CONTRADICTED'}
    
    # direct-support source requirements
    for claim in ledger['claim_records']:
        if claim['source_bindings']:
            if claim.get('evidence_kind') != 'REPOSITORY_FACT':
                check(claim.get('exact_locators'), "Missing precise locators for source bindings")
        
        check(not any(s in contradicted_sources for s in claim['source_bindings']), "Claim binds to contradicted source")

        if claim['support_status'] == 'DIRECTLY_SUPPORTED':
            if claim['evidence_kind'] == 'SOURCE_FACT':
                check(len(claim['source_bindings']) > 0, "DIRECTLY_SUPPORTED SOURCE_FACT requires valid active source binding")

        # qualifications checking
        if claim['support_status'] == 'SUPPORTED_WITH_QUALIFICATION':
            check('phase2a_pass_blocking' in claim, "SUPPORTED_WITH_QUALIFICATION must have phase2a_pass_blocking")
            check(claim.get('blocking_reason'), "SUPPORTED_WITH_QUALIFICATION must have blocking_reason")

    # all 24 obligation identities
    ob_ids = [
        "EXACT_E_MINUS_NC_FORMULA", "EXACT_E_PLUS_NC_FORMULA", "F2_FL_XF3_CONVENTIONS",
        "GAMMA_Z_INTERFERENCE_AND_SIGNS", "ELECTROWEAK_INPUT_SCHEME", "FACTORIZATION_AND_RENORMALIZATION_SCALES",
        "FLAVOR_AND_HEAVY_QUARK_SCHEME", "PDF_FAMILY_AND_TRANSPORT_IDENTITY", "KINEMATIC_COORDINATES_AND_JACOBIAN",
        "ACCEPTANCE_REGION_DEFINITION", "STRICT_PDF_SUPPORT_INTERSECTION", "FINITE_NONZERO_NORMALIZATION_FOR_EVERY_THETA",
        "NONNEGATIVE_COMPLETE_DIFFERENTIAL_RATE", "FIXED_N_SHAPE_ONLY_OBSERVATION_LAW", "RATE_INCLUSIVE_EXTENSION_SEPARATED",
        "NORMALIZED_DETECTOR_MARKOV_KERNEL", "PERFECT_DETECTOR_IDENTITY_KERNEL", "OBSERVED_FEATURE_AND_LEAKAGE_CONTRACT",
        "EXPLICIT_OMITTED_PHYSICS_DECLARATION", "INDEPENDENT_NUMERICAL_CLOSURE_PLAN", "POSTERIOR_TARGET_AND_PROPER_TRAINING_OBJECTIVE",
        "CALIBRATION_COVERAGE_AND_FAILURE_CRITERIA", "OBSERVATION_SELECTION_AND_FIXED_N_CONDITIONING", "PARAMETER_IDENTIFIABILITY_AND_INFORMATION_CONTENT"
    ]
    check(len(review['obligation_reviews']) == 24, "Must have exactly 24 obligations")
    rev_ob_ids = [ob['obligation_id'] for ob in review['obligation_reviews']]
    check(set(rev_ob_ids) == set(ob_ids), "Missing or incorrect obligation IDs")

    claim_map = {c['claim_id']: c for c in ledger['claim_records']}

    for ob in review['obligation_reviews']:
        ob_id = ob['obligation_id']
        derived_status = "SUPPORTED"
        for cid in ob['source_claim_ids']:
            if cid not in claim_map:
                continue
            cstat = claim_map[cid]['support_status']
            is_blocking = claim_map[cid].get('phase2a_pass_blocking', False)
            
            # evaluate for this claim
            eff_stat = cstat
            if is_blocking and cstat == "SUPPORTED_WITH_QUALIFICATION":
                eff_stat = "PRIMARY_EVIDENCE_UNAVAILABLE"

            if eff_stat == "CONTRADICTED":
                derived_status = "CONTRADICTED"
                break
            elif eff_stat == "NOT_SUPPORTED" and derived_status != "CONTRADICTED":
                derived_status = "NOT_SUPPORTED"
            elif eff_stat == "PRIMARY_EVIDENCE_UNAVAILABLE" and derived_status not in ["CONTRADICTED", "NOT_SUPPORTED"]:
                derived_status = "PRIMARY_EVIDENCE_UNAVAILABLE"
            elif eff_stat == "SUPPORTED_WITH_QUALIFICATION" and derived_status == "SUPPORTED":
                derived_status = "SUPPORTED_WITH_QUALIFICATION"

        check(ob['contract_review_status'] == derived_status, f"Obligation {ob_id} status {ob['contract_review_status']} does not match derived {derived_status}")

    # Reciprocal obligation dependencies
    for claim in ledger['claim_records']:
        c_obs = claim.get('obligation_ids', [])
        for o_id in c_obs:
            ob = next((o for o in review['obligation_reviews'] if o['obligation_id'] == o_id), None)
            check(ob is not None, f"Claim {claim['claim_id']} lists unknown obligation ID {o_id}")
            check(claim['claim_id'] in ob['source_claim_ids'], f"Claim {claim['claim_id']} lists obligation {o_id} but obligation does not list claim")

    for ob in review['obligation_reviews']:
        for cid in ob['source_claim_ids']:
            check(cid in claim_map, f"Obligation {ob['obligation_id']} lists unknown claim {cid}")
            c_obs = claim_map[cid].get('obligation_ids', [])
            check(ob['obligation_id'] in c_obs, f"Obligation {ob['obligation_id']} lists claim {cid} but claim does not list obligation")

    # gate required_claim_ids non-empty, obligation_dependencies non-empty
    check(len(review['gate_reviews']) == 11, "Must have exactly 11 gates")
    gate_ids = [
        "exact_formula_contract", "finite_positive_normalization_reviewability", "posterior_target_coherence",
        "strict_support_contract", "normalized_detector_kernel_contract", "no_hidden_clipping",
        "fixed_n_shape_only_semantics", "bounded_phase2b_validation_plan", "paper_claim_boundary_consistency",
        "selected_event_conditioning_coherence", "bounded_identifiability_and_information_plan"
    ]
    rev_gate_ids = [g['gate_id'] for g in review['gate_reviews']]
    check(set(rev_gate_ids) == set(gate_ids), "Missing or incorrect gate IDs")

    # gate required_claim_ids non-empty, obligation_dependencies non-empty
    for claim in ledger['claim_records']:
        c_gates = claim.get('gate_dependencies', [])
        for g_id in c_gates:
            gate = next((g for g in review['gate_reviews'] if g['gate_id'] == g_id), None)
            check(gate is not None and claim['claim_id'] in gate['required_claim_ids'], f"Claim {claim['claim_id']} lists gate {g_id} but gate does not list claim")

    for gate in review['gate_reviews']:
        check(len(gate['required_claim_ids']) > 0, f"Gate {gate['gate_id']} has empty required_claim_ids")
        check(len(gate['obligation_dependencies']) > 0, f"Gate {gate['gate_id']} has empty obligation_dependencies")

        for rcid in gate['required_claim_ids']:
            check(rcid in claim_map, f"Gate {gate['gate_id']} requires unknown claim {rcid}")

        for ob_dep in gate['obligation_dependencies']:
            check(ob_dep in ob_ids, f"Gate {gate['gate_id']} has unknown obligation dependency {ob_dep}")

        # deterministic gate status derivation
        derived_status = "SUPPORTED"
        for cid in gate['required_claim_ids']:
            cstat = claim_map[cid]['support_status']
            is_blocking = claim_map[cid].get('phase2a_pass_blocking', False)
            if is_blocking:
                cstat = "PRIMARY_EVIDENCE_UNAVAILABLE"

            if cstat == "CONTRADICTED":
                derived_status = "CONTRADICTED"
                break
            elif cstat == "NOT_SUPPORTED" and derived_status != "CONTRADICTED":
                derived_status = "NOT_SUPPORTED"
                break
            elif cstat == "PRIMARY_EVIDENCE_UNAVAILABLE" and derived_status not in ["CONTRADICTED", "NOT_SUPPORTED"]:
                derived_status = "PRIMARY_EVIDENCE_UNAVAILABLE"
                break
            elif cstat == "SUPPORTED_WITH_QUALIFICATION" and derived_status == "SUPPORTED":
                derived_status = "SUPPORTED_WITH_QUALIFICATION"
        
        check(gate['status'] == derived_status, f"Gate {gate['gate_id']} status {gate['status']} does not match derived {derived_status}")

    # deterministic decision derivation
    derived_decision = "PASS"
    for gate in review['gate_reviews']:
        if gate['status'] in ["NOT_SUPPORTED", "CONTRADICTED"]:
            derived_decision = "FAIL"
            break
        elif gate['status'] == "PRIMARY_EVIDENCE_UNAVAILABLE" and derived_decision != "FAIL":
            derived_decision = "INCONCLUSIVE"
            
    check(review['scientific_decision'] == derived_decision, f"Decision {review['scientific_decision']} does not match derived {derived_decision}")

    # all later executions NOT_EXECUTED
    for ob in review['obligation_reviews']:
        check(ob['later_execution_status'] == "NOT_EXECUTED", f"Obligation {ob['obligation_id']} has executed status")
    
    check(phase2b.get("execution_status") == "NOT_EXECUTED", "Phase 2B plan execution status not NOT_EXECUTED")
    check(phase2b.get("authorization") == "NOT_AUTHORIZED", "Phase 2B plan authorized")

    # check Phase 2B plan concrete bounds if COMPLETE
    if phase2b.get("plan_completeness") != "INCOMPLETE":
        check(len(phase2b.get('anchors', [])) > 0, "Phase 2B plan has empty anchors")
        check(len(phase2b.get('grids', [])) > 0, "Phase 2B plan has empty grids")
        check(len(phase2b.get('convergence_rules', [])) > 0, "Phase 2B plan has empty convergence_rules")

        for t in phase2b.get('tolerances', []):
            check("quantity" in t, "Tolerance missing quantity")
            check("threshold" in t, "Tolerance missing threshold")
            check("absolute_or_relative" in t, "Tolerance missing absolute_or_relative")
            check("justification_type" in t, "Tolerance missing justification_type")
            check("justification_source_or_repository_identity" in t, "Tolerance missing justification_source_or_repository_identity")
            check("blocking_if_unresolved" in t, "Tolerance missing blocking_if_unresolved")

    # Phase 2B unauthorized, all implementation flags false, legacy D2 false
    auth = review['authorization']
    check(not auth.get("PHASE2B_AUTHORIZED"), "Phase 2B authorized")
    check(not auth.get("IMPLEMENTATION_AUTHORIZED"), "Implementation authorized")
    check(not auth.get("NUMERICAL_PHYSICS_AUTHORIZED"), "Numerical physics authorized")
    check(not auth.get("D2_AUTHORIZED"), "Legacy D2 authorized")

    # Predecessor checks
    pred = review.get('predecessor_identities', {})
    check(pred.get('phase1b_closeout') == "ea509c228aa74021af15c5e1473b257dd0c1b6863118ac9f4be484358c7c8fd5", "Wrong phase1b closeout hash")
    check(pred.get('phase1bd_revision') == file_sha256("docs/phase1bd_d0_revision_decision.json"), "Wrong phase1bd hash")

    # paper nonclaims
    forbidden = review.get("paper_claim_boundary", {}).get("forbidden", [])
    check("full-generator equivalence" in forbidden, "Missing full-generator equivalence nonclaim")

    # no committed source bytes
    check(not os.path.exists("docs/reduced_nc_dis/sources/papers"), "Paper bytes committed")

    check_adr013_consistency(review, phase2b)

    print("VALID phase2a.contract_review")

if __name__ == "__main__":
    main()
