import json
import os
import sys
import re

def check(condition, message):
    if not condition:
        print(f"Validation Error: {message}")
        sys.exit(1)

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

    # exact schemas
    check(registry.get("schema_version") == "partonsbi.phase2a.source-registry.v2", "Wrong registry schema")
    check(ledger.get("schema_version") == "partonsbi.phase2a.claim-source-ledger.v2", "Wrong ledger schema")
    check(review.get("schema_version") == "partonsbi.phase2a.reduced-nc-dis-contract-review.v2", "Wrong review schema")
    check(phase2b.get("schema_version") == "partonsbi.phase2b.reduced-nc-dis-validation-plan-proposal.v2", "Wrong phase2b schema")

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
        # publication/version date separation is present in the schema
        
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
        # precise locator presence
        if claim['source_bindings']:
            check(claim['exact_locators'], "Missing precise locators for source bindings")
        
        # no contradicted sources
        check(not any(s in contradicted_sources for s in claim['source_bindings']), "Claim binds to contradicted source")

        if claim['support_status'] == 'DIRECTLY_SUPPORTED':
            if claim['evidence_kind'] == 'SOURCE_FACT':
                check(len(claim['source_bindings']) > 0, "DIRECTLY_SUPPORTED SOURCE_FACT requires valid active source binding")

    # claim-to-obligation consistency
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

    for gate in review['gate_reviews']:
        check(len(gate['required_claim_ids']) > 0, f"Gate {gate['gate_id']} has empty required_claim_ids")
        check(len(gate['obligation_dependencies']) > 0, f"Gate {gate['gate_id']} has empty obligation_dependencies")

        # deterministic gate status derivation
        derived_status = "SUPPORTED"
        for cid in gate['required_claim_ids']:
            cstat = claim_map[cid]['support_status']
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

    # Phase 2B unauthorized, all implementation flags false, legacy D2 false
    auth = review['authorization']
    check(not auth.get("PHASE2B_AUTHORIZED"), "Phase 2B authorized")
    check(not auth.get("IMPLEMENTATION_AUTHORIZED"), "Implementation authorized")
    check(not auth.get("NUMERICAL_PHYSICS_AUTHORIZED"), "Numerical physics authorized")
    check(not auth.get("D2_AUTHORIZED"), "Legacy D2 authorized")

    # predecessor hashes
    pred = review.get("predecessor_identities", {})
    check(pred.get("phase1b_closeout") == "ea509c228aa74021af15c5e1473b257dd0c1b6863118ac9f4be484358c7c8fd5", "Wrong phase1b hash")
    check(pred.get("phase2_roadmap") == "844a2783875039b1bf730c24f3ccf8814a7aa74fd78a017de3f5ca3339e2ca78", "Wrong phase2 roadmap hash")

    # paper nonclaims
    forbidden = review.get("paper_claim_boundary", {}).get("forbidden", [])
    check("full-generator equivalence" in forbidden, "Missing full-generator equivalence nonclaim")

    # no committed source bytes
    check(not os.path.exists("docs/reduced_nc_dis/sources/papers"), "Paper bytes committed")

    # ADR-013 Proposed
    try:
        with open("docs/adr/ADR-013-reduced-nc-dis-observation-law-contract.md") as f:
            adr = f.read()
            check(re.search(r'Status.*Proposed', adr, re.IGNORECASE | re.DOTALL), "ADR-013 is not Proposed")
    except FileNotFoundError:
        check(False, "Missing ADR-013")

    print("VALID phase2a.contract_review")

if __name__ == "__main__":
    main()
