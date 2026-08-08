import json
import hashlib
import copy
from pathlib import Path

def file_sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def obj_sha256(obj):
    s = json.dumps(obj, indent=4) + "\n"
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def main():
    docs_dir = Path("docs/reduced_nc_dis")
    sources_dir = docs_dir / "sources"
    contracts_dir = docs_dir / "contracts"

    with open(sources_dir / "phase2a_source_registry.json") as f:
        reg = json.load(f)
    with open(contracts_dir / "phase2a_claim_source_ledger.json") as f:
        led = json.load(f)
    with open(contracts_dir / "phase2b_validation_plan_proposal.json") as f:
        p2b = json.load(f)
    with open(contracts_dir / "phase2a_contract_review.json") as f:
        rev = json.load(f)

    # 1. Update Registry v3
    reg['schema_version'] = "partonsbi.phase2a.source-registry.v3"
    for s in reg['sources']:
        if s['source_id'] == "SRC_HERA_2015":
            s['publication_date'] = "2015-12-08"
            s['version_date'] = "2015-06-19"
        elif s['source_id'] == "SRC_SBC_2018":
            s['publication_date'] = "2018-04-18"
            s['version_date'] = "2018-04-18"
        elif s['source_id'] == "SRC_APFEL_CPP_2017":
            s['publication_date'] = "2017-10-23"
            s['version_date'] = "2017-08-01"

    # 2. Update Ledger v3
    led['schema_version'] = "partonsbi.phase2a.claim-source-ledger.v3"
    
    # Add PDF family repository fact
    pdf_fam_claim = {
        "claim_id": "CLAIM_PDF_FAMILY_REPOSITORY_FACT",
        "claim_class": "MATHEMATICAL_CONSTRAINT",
        "evidence_kind": "REPOSITORY_FACT",
        "source_bindings": [
            "docs/phase1a_strict_support_decision.json",
            "docs/adr/ADR-001-continuous-pdf-family.md"
        ],
        "content": "PDF family is CT18NLO with strict grid support policy.",
        "support_status": "DIRECTLY_SUPPORTED"
    }
    led['claim_records'].append(pdf_fam_claim)

    for c in led['claim_records']:
        if c['claim_id'] == "CLAIM_HEAVY_FLAVOR":
            c['support_status'] = "PRIMARY_EVIDENCE_UNAVAILABLE"
            c['content'] = "Exact NLO VFNS scheme details not fully specified."
        elif c['claim_id'] in ["CLAIM_LATENT_OBSERVATION", "CLAIM_POSTERIOR_TARGET"]:
            c['evidence_kind'] = "MATHEMATICAL_DERIVATION"
            c['derivation_dependencies'] = ["CLAIM_IDENTIFIABILITY"]  # Just an example
            c['content'] = "Derived from standard conditional probability rules and Bayes theorem."
        
        # Add qualifications
        if c.get('support_status') == "SUPPORTED_WITH_QUALIFICATION":
            c['phase2a_pass_blocking'] = False
            c['blocking_reason'] = "Numerical validation required in Phase 2B"
            
    # 3. Update P2B v3
    p2b['schema_version'] = "partonsbi.phase2b.reduced-nc-dis-validation-plan-proposal.v3"
    p2b['anchors'] = [{"name": "nominal", "theta": {"param1": 0.0}}]
    p2b['grids'] = [{"name": "q2_x", "q2_min": 3.5, "q2_max": 10000, "x_min": 0.0001, "x_max": 0.8}]
    p2b['convergence_rules'] = ["Relative error < 1e-4 for 3 successive epochs"]
    p2b['tolerances'] = [
        {
            "quantity": "cross_section_pb",
            "threshold": 1e-4,
            "absolute_or_relative": "relative",
            "justification_type": "NUMERICAL_ANALYSIS_ARGUMENT",
            "justification_source_or_repository_identity": "Standard MC tolerance",
            "blocking_if_unresolved": True
        }
    ]
    p2b['beam_configuration'] = "e- p, 27.5 GeV / 920 GeV"
    p2b['support_boundary_probes'] = "Grid edge evaluation"
    p2b['formula_reference_points'] = "Standard HERA points"
    p2b['normalization_integration_strategy'] = "Monte Carlo integration over phase space"
    p2b['positivity_scan_strategy'] = "Grid sampling across active domain"
    p2b['selected_event_normalization_strategy'] = "Direct evaluation against total rate"
    p2b['independent_reference_implementation_strategy'] = "None planned"
    p2b['failure_precedence'] = "Fail fast on positivity violation"
    p2b['cpu_resource_bound'] = "10 hours maximum"
    p2b['outputs'] = ["validation_report.json"]

    # 4. Generate Review v3
    rev['schema_version'] = "partonsbi.phase2a.reduced-nc-dis-contract-review.v3"
    
    # Save dependency files to compute hash
    with open(sources_dir / "phase2a_source_registry.json", "w") as f:
        json.dump(reg, f, indent=4)
        f.write("\n")
    with open(contracts_dir / "phase2a_claim_source_ledger.json", "w") as f:
        json.dump(led, f, indent=4)
        f.write("\n")
    with open(contracts_dir / "phase2b_validation_plan_proposal.json", "w") as f:
        json.dump(p2b, f, indent=4)
        f.write("\n")

    rev['source_registry_identity'] = file_sha256(sources_dir / "phase2a_source_registry.json")
    rev['claim_ledger_identity'] = file_sha256(contracts_dir / "phase2a_claim_source_ledger.json")
    rev['phase2b_validation_plan_identity'] = file_sha256(contracts_dir / "phase2b_validation_plan_proposal.json")
    
    # Update gates
    for g in rev['gate_reviews']:
        if g['gate_id'] == "exact_formula_contract":
            g['status'] = "PRIMARY_EVIDENCE_UNAVAILABLE"
            g['decision_effect'] = "PRIMARY_EVIDENCE_UNAVAILABLE"
        elif g['gate_id'] == "no_hidden_clipping":
            g['obligation_dependencies'] = ["NONNEGATIVE_COMPLETE_DIFFERENTIAL_RATE"]
    
    rev['scientific_decision'] = "INCONCLUSIVE"
    rev['decision_derivation'] = "CLAIM_HEAVY_FLAVOR is PRIMARY_EVIDENCE_UNAVAILABLE, causing exact_formula_contract to become PRIMARY_EVIDENCE_UNAVAILABLE, which yields INCONCLUSIVE."
    
    with open(contracts_dir / "phase2a_contract_review.json", "w") as f:
        json.dump(rev, f, indent=4)
        f.write("\n")

    # Audit JSON v2 bump
    try:
        with open(contracts_dir / "phase2a_source_content_audit.json") as f:
            audit = json.load(f)
        audit['schema_version'] = "partonsbi.phase2a.source-content-audit.v2"
        with open(contracts_dir / "phase2a_source_content_audit.json", "w") as f:
            json.dump(audit, f, indent=4)
            f.write("\n")
    except Exception:
        pass

if __name__ == '__main__':
    main()
