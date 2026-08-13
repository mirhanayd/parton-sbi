#!/usr/bin/env python3
"""Validate the source-backed Phase 2 FONLL-A contract amendment."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2_fonll_a_contract_amendment.json"

SCHEMA = "partonsbi.phase2.fonll-a-contract-amendment.v1"
CANDIDATES = {
    "APFEL_FONLL_A_NLO",
    "HERA_RTOPT_NLO_VFNS",
    "APFEL_FFN",
    "APFEL_ZM_VFN",
}
CANDIDATE_CRITERIA = {
    "exact_physics_identity",
    "perturbative_order",
    "active_flavor_treatment",
    "heavy_quark_masses_and_mass_convention",
    "flavor_thresholds",
    "matching_conditions",
    "coefficient_function_order",
    "threshold_treatment",
    "factorization_scale_convention",
    "renormalization_scale_convention",
    "alpha_s_identity",
    "electron_positron_nc_applicability",
    "accepted_pdf_family_compatibility",
    "software_exposure",
    "predeclared_validity_domain",
    "positivity_implications",
    "later_no_clipping_testability",
    "independent_closure_possibilities",
    "paper_research_question_impact",
    "contract_impact",
}
MATRIX_CRITERIA = {
    "preservation_of_research_objective",
    "exact_source_binding",
    "compatibility_with_accepted_pdf_family",
    "reproducible_software_configuration",
    "minimal_contract_change",
    "threshold_physics_fidelity",
    "later_no_clipping_testability",
    "independent_closure_strength",
    "paper_claim_preservation",
    "reversibility",
}
ELIMINATION_CHECKS = {
    "incompatible_with_accepted_pdf_family",
    "physics_identity_not_source_defined",
    "software_configuration_not_reproducibly_bindable",
    "requires_hidden_repair",
    "requires_research_question_change_when_viable_preserving_candidate_exists",
    "cannot_support_meaningful_later_validation",
}
ASSESSMENT_STATUSES = {
    "SUPPORTED",
    "SUPPORTED_WITH_QUALIFICATION",
    "NOT_SUPPORTED",
    "PRIMARY_EVIDENCE_UNAVAILABLE",
    "NOT_APPLICABLE",
}
MATRIX_SCORES = {"HIGH", "MEDIUM", "LOW"}

EXPECTED_PREDECESSORS = {
    "phase2a_contract_review": (
        "docs/reduced_nc_dis/contracts/phase2a_contract_review.json",
        "4ce2b5b8e910edda6f2183fe7a7e24ec1f0d5e99bd603b708f587c178d1d237b",
    ),
    "phase2a_claim_source_ledger": (
        "docs/reduced_nc_dis/contracts/phase2a_claim_source_ledger.json",
        "ca2eb35d38c59b2f5f79435acd0171b60cc80d9577d6f4db35f10d98f329f0fc",
    ),
    "phase2b_validation_plan_proposal": (
        "docs/reduced_nc_dis/contracts/phase2b_validation_plan_proposal.json",
        "e60846b5975cd12284b17ef2e28b873760b8ff17cc03f8cb3a85929af6a71786",
    ),
    "phase1bd_d0_revision": (
        "docs/phase1bd_d0_revision_decision.json",
        "ef44ec6b230d06edce4b30b435d30ee382e3e151a8dfe3a9f8098e4ac6747873",
    ),
    "phase1bd_d0r_decision": (
        "docs/phase1bd_d0r_decision.json",
        "40e75fda281578f45d193858667eeed2c1747a07d64f53672adec10145c9e775",
    ),
    "phase1bd_d1_decision": (
        "docs/phase1bd_d1_decision.json",
        "3cdb3e6e11fae63aa9b4bb9e0094c0610a8c01eb636eecc25571e3c2f11e9881",
    ),
}

EXPECTED_SOURCES = {
    "HERA_2015_V3": {
        "canonical_url": "https://arxiv.org/pdf/1506.06042v3",
        "sha256": "04971dfad54401348e66d6bf39ea6ef43ac8e5b854ad313381d68df045ab40bc",
    },
    "APFEL_2014_V3": {
        "canonical_url": "https://arxiv.org/pdf/1310.1394v3",
        "sha256": "3699f4efd19eee7a178c07bb64136c2fab83690d9e84024478f237a88453b5da",
    },
    "FONLL_2010_V2": {
        "canonical_url": "https://arxiv.org/pdf/1001.2312v2",
        "sha256": "f1c40c70edd6debd649d2cead24cdf297f5eb18c8ed8065100731c150d20989b",
    },
    "APFELXX_2017_V1": {
        "canonical_url": "https://arxiv.org/pdf/1708.00911v1",
        "sha256": "c572c07e16a7ca6db350a092abb3c33d469bb144598eb18b195333b8f702b8ec",
    },
    "APFEL_SOURCE_3_1_1": {
        "canonical_url": "https://github.com/scarrazza/apfel/tree/72bf6ec7c72c923dd2115f2a98c6f593f9c91d2a",
        "tag": "3.1.1",
        "commit": "72bf6ec7c72c923dd2115f2a98c6f593f9c91d2a",
        "archive_url": "https://github.com/scarrazza/apfel/archive/72bf6ec7c72c923dd2115f2a98c6f593f9c91d2a.tar.gz",
        "archive_sha256": "e5c4b3d955f8d33e8e8ff2d9d1687da57f2ee99245abc579f9d32caa616f0f53",
        "pinned_files": {
            "CMakeLists.txt": "ecf1f782f4e120a6795e4b95c7c2032dfa889b59e99925477eeb8b4677148ba7",
            "include/APFEL/APFELobs.h": "d2b55bda1901f206c873923d5e851c41503854fca4f880baf4c01fe51bdbb9d3",
            "include/APFEL/APFELevol.h": "de70eaa26195ed5258fd8bf59485733b3c9fea0a40ff2de46e5a11fe6fa536b0",
            "src/DIS/initParametersDIS.f": "63e56cefa0c2fff8033a0f2eca27f4cd1d6c12948fa1d459e329a74d89670396",
            "src/DIS/ComputeDISOperators.f": "4f4b17bac6cf360fe1406b00fe7d20078053f99e624c6b403b93bf3a8aa65990",
            "src/Evolution/initParameters.f": "1acd6161a8870cfb9f22b20fc0bc7ee11dcac7d5211237b42ab7d55f72d5bbc4",
            "examples/DISObservablesCxx.cc": "9f9baea4dda1fd49f4a742cb841cd572add61a8e3f2dd75bd44d12a550b3b887",
            "examples/TabulationExternal.f": "ae313bb89fdcda815c37b7487e63fd4a204114e3be93805259c0271b631c0a31",
        },
    },
}


class ValidationError(ValueError):
    """Raised when the amendment violates its serialized contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive_eligible_candidates(record: dict[str, Any]) -> list[str]:
    eligible: list[str] = []
    for candidate_id in sorted(CANDIDATES):
        checks = record["candidate_assessments"][candidate_id]["elimination_checks"]
        if not any(checks.values()):
            eligible.append(candidate_id)
    return eligible


def derive_decision(record: dict[str, Any]) -> str:
    eligible = derive_eligible_candidates(record)
    if "APFEL_FONLL_A_NLO" in eligible:
        return "D1_PREPARE_FONLL_A_NLO_CONTRACT_AMENDMENT"
    if eligible:
        return "D2_PREPARE_OTHER_EXPLICIT_CONTRACT_AMENDMENT"
    software_only = any(
        candidate["elimination_checks"]["software_configuration_not_reproducibly_bindable"]
        and not candidate["elimination_checks"]["incompatible_with_accepted_pdf_family"]
        and not candidate["elimination_checks"]["requires_hidden_repair"]
        for candidate in record["candidate_assessments"].values()
    )
    if software_only:
        return "D4_SOFTWARE_ARCHITECTURE_DECISION_REQUIRED_BEFORE_PHYSICS_SELECTION"
    return "D3_NO_ELIGIBLE_CONTRACT_MAINTAIN_PHASE2_PAUSE"


def validate(record: dict[str, Any], *, root: Path = ROOT, check_docs: bool = True) -> None:
    require(record.get("schema_version") == SCHEMA, "Wrong amendment schema")
    require(record.get("record_type") == "FOLLOW_ON_CONTRACT_AMENDMENT", "Wrong record type")

    historical = record.get("historical_phase2a", {})
    require(historical.get("status") == "COMPLETE", "Historical Phase 2A status changed")
    require(historical.get("scientific_decision") == "INCONCLUSIVE", "Historical Phase 2A decision changed")
    require(historical.get("historical_result_changed") is False, "Historical Phase 2A result rewritten")
    require(historical.get("adr_013_status") == "Proposed", "ADR-013 status changed")

    predecessors = record.get("predecessor_identities", {})
    require(set(predecessors) == set(EXPECTED_PREDECESSORS), "Wrong predecessor identity set")
    for key, (relative_path, expected_hash) in EXPECTED_PREDECESSORS.items():
        require(predecessors[key] == expected_hash, f"Wrong serialized predecessor hash: {key}")
        require(file_sha256(root / relative_path) == expected_hash, f"Current predecessor bytes changed: {key}")

    cache = record.get("evidence_cache", {})
    require(cache.get("initial_status") == "EVIDENCE_CACHE_INCOMPLETE", "Wrong initial evidence-cache status")
    require(cache.get("bounded_retrieval_performed") is True, "Bounded retrieval not recorded")
    require(cache.get("repository_source_bytes_committed") is False, "External source bytes claimed committed")

    sources = record.get("source_evidence", [])
    require(len(sources) == len(EXPECTED_SOURCES), "Wrong source-evidence count")
    source_map = {source.get("source_id"): source for source in sources}
    require(set(source_map) == set(EXPECTED_SOURCES), "Wrong source-evidence identities")
    for source_id, expected in EXPECTED_SOURCES.items():
        source = source_map[source_id]
        for key, expected_value in expected.items():
            require(source.get(key) == expected_value, f"Wrong {key} for {source_id}")
        require(source.get("retrieved_utc"), f"Missing retrieval time for {source_id}")
        require(source.get("locators"), f"Missing precise locators for {source_id}")

    candidates = record.get("candidate_assessments", {})
    require(set(candidates) == CANDIDATES, "Must assess exactly the four declared candidates")
    for candidate_id, candidate in candidates.items():
        criterion_keys = set(candidate) - {"elimination_checks", "eligible"}
        require(criterion_keys == CANDIDATE_CRITERIA, f"Wrong criteria for {candidate_id}")
        for criterion in CANDIDATE_CRITERIA:
            cell = candidate[criterion]
            require(cell.get("status") in ASSESSMENT_STATUSES, f"Wrong status for {candidate_id}/{criterion}")
            require(bool(cell.get("rationale")), f"Missing rationale for {candidate_id}/{criterion}")
            evidence_ids = cell.get("evidence_ids", [])
            require(bool(evidence_ids), f"Missing evidence for {candidate_id}/{criterion}")
            require(set(evidence_ids) <= set(source_map), f"Unknown evidence for {candidate_id}/{criterion}")
        checks = candidate.get("elimination_checks", {})
        require(set(checks) == ELIMINATION_CHECKS, f"Wrong elimination checks for {candidate_id}")
        require(all(isinstance(value, bool) for value in checks.values()), f"Non-boolean elimination check for {candidate_id}")
        require(candidate.get("eligible") is (not any(checks.values())), f"Eligibility is not derived for {candidate_id}")

    matrix = record.get("decision_matrix", {})
    require(set(matrix) == CANDIDATES, "Decision matrix candidate mismatch")
    for candidate_id, row in matrix.items():
        require(set(row) == MATRIX_CRITERIA, f"Wrong decision-matrix criteria for {candidate_id}")
        for criterion, cell in row.items():
            require(cell.get("score") in MATRIX_SCORES, f"Wrong matrix score for {candidate_id}/{criterion}")
            require(bool(cell.get("reason")), f"Missing matrix reason for {candidate_id}/{criterion}")

    special = record.get("special_classifications", {})
    require(special.get("ffn") == "FFN_REQUIRES_NEW_PDF_CONTRACT", "Wrong FFN classification")
    require(special.get("zm_vfn") == "ZMVFN_REQUIRES_PREDECLARED_VALIDITY_DOMAIN", "Wrong ZM-VFN classification")
    require(special.get("rtopt") == "RTOPT_IMPLEMENTATION_PATH_NOT_BOUND", "Wrong RTOPT classification")

    derived_eligible = derive_eligible_candidates(record)
    require(record.get("eligibility", {}).get("eligible_candidates") == derived_eligible, "Eligible-candidate list is not derived")
    derived_decision = derive_decision(record)
    require(record.get("decision") == derived_decision, "Decision is not derived from elimination checks")
    require(derived_eligible == ["APFEL_FONLL_A_NLO"], "Current evidence does not leave FONLL-A uniquely eligible")

    special_fonll = record.get("fonll_a_special_findings", {})
    require(special_fonll.get("contract_effect") == "DISAMBIGUATES_CURRENT_GENERIC_NLO_VFNS_WORDING", "FONLL-A contract effect changed")
    require(special_fonll.get("apfel_controls_sufficient_for_reproducible_configuration") is True, "APFEL controls not bound")
    require(special_fonll.get("apfelxx_full_heavy_flavor_required_by_accepted_record") is False, "APFEL++ requirement invented")
    require(special_fonll.get("apfel_complete_fonll_a_nc_compatible_with_reduced_research_direction") is True, "Reduced-model compatibility changed")

    amendment = record.get("contract_amendment", {})
    require(amendment.get("scheme") == "FONLL-A", "Wrong selected scheme")
    require(amendment.get("perturbative_order") == "NLO", "Wrong perturbative order")
    require(amendment.get("software") == {"name": "APFEL", "version": "3.1.1", "commit": "72bf6ec7c72c923dd2115f2a98c6f593f9c91d2a"}, "Wrong software identity")
    require(amendment.get("pdf_family") == "ct18nlo_two_parameter_boundary_v2", "Accepted PDF family changed")
    require(amendment.get("pdf_baseline") == "ct18nlo_member0_sumrule_projected_boundary_v2", "Accepted PDF baseline changed")
    require(amendment.get("latent_coordinates") == ["x_Bj", "Q2"], "Wrong latent coordinates")
    require(amendment.get("differential_measure") == "d2sigma_dx_dQ2", "Wrong differential measure")
    require(amendment.get("support_policy") == "STRICT_INTERSECTION_NO_EXTRAPOLATION", "Strict support weakened")
    require(amendment.get("clipping_allowed") is False, "Clipping allowed")
    require(amendment.get("absolute_value_repair_allowed") is False, "Absolute-value repair allowed")
    require(amendment.get("post_hoc_support_deletion_allowed") is False, "Post-hoc support deletion allowed")
    require(amendment.get("paper_nonclaims_preserved") is True, "Paper nonclaims changed")

    pre_auth = record.get("pre_auth_contract_evidence", {})
    required = set(pre_auth.get("required", []))
    resolved = set(pre_auth.get("currently_resolved", []))
    unresolved = set(pre_auth.get("currently_unresolved", []))
    require(not (resolved & unresolved), "Pre-auth evidence is both resolved and unresolved")
    require("exact_formula_identity" in resolved, "Formula identity not resolved by amendment")
    require("exact_heavy_flavor_convention" in resolved, "Heavy-flavor convention not resolved by amendment")
    for item in (
        "heavy_quark_mass_convention_and_values",
        "shared_alpha_s_identity",
        "planned_theta_anchors",
        "planned_kinematic_grids",
        "planned_tolerances_with_justification",
        "convergence_rules",
        "independent_reference_strategy",
        "resource_bound",
    ):
        require(item in unresolved, f"Unresolved pre-auth item promoted: {item}")
    require(resolved | unresolved == required, "Pre-auth evidence does not partition the required set")

    post_auth = record.get("post_auth_numerical_validation", {})
    require(post_auth.get("permitted_only_after_separate_authorization") is True, "Post-auth work not separated")
    require(set(post_auth.get("not_executed", [])) == {"positivity_scan", "normalization_integration", "independent_numerical_closure"}, "Post-auth execution status changed")

    authorization = record.get("authorization", {})
    require(bool(authorization), "Missing authorization block")
    require(all(value is False for value in authorization.values()), "An authorization flag is true")
    phase2b = record.get("phase2b_state", {})
    require(phase2b.get("issue") == 55 and phase2b.get("state") == "OPEN", "Issue #55 state changed")
    require(phase2b.get("project_status") == "Backlog", "Issue #55 project status changed")
    require(phase2b.get("gate_decision") == "Not Evaluated", "Issue #55 gate changed")
    require(phase2b.get("authorization") == "Not Authorized", "Issue #55 authorized")
    require(phase2b.get("plan_completeness") == "INCOMPLETE", "Phase 2B plan promoted")
    require(phase2b.get("execution_status") == "NOT_EXECUTED", "Phase 2B executed")

    validation = record.get("validation", {})
    require(validation.get("decision_is_derived") is True, "Decision derivation not asserted")
    require(validation.get("source_bytes_committed") is False, "Source bytes claimed committed")
    require(validation.get("numerical_physics_executed") is False, "Numerical physics claimed executed")
    require(validation.get("phase2b_execution_occurred") is False, "Phase 2B execution claimed")
    require(not (root / "docs/reduced_nc_dis/sources/papers").exists(), "External paper bytes committed")

    if check_docs:
        required_doc_markers = {
            "docs/adr/ADR-013-reduced-nc-dis-observation-law-contract.md": [
                "D1_PREPARE_FONLL_A_NLO_CONTRACT_AMENDMENT",
                "Phase 2A result remains `INCONCLUSIVE`",
                "remains `NOT_AUTHORIZED` and `NOT_EXECUTED`",
            ],
            "docs/CURRENT_PHASE.md": ["FONLL-A", "Phase 2B remains"],
            "docs/reduced_nc_dis/README.md": ["FONLL-A", "follow-on contract amendment"],
            "docs/reduced_nc_dis/ROADMAP.md": ["FONLL-A", "D1_PREPARE_FONLL_A_NLO_CONTRACT_AMENDMENT"],
        }
        for relative_path, markers in required_doc_markers.items():
            text = (root / relative_path).read_text(encoding="utf-8")
            for marker in markers:
                require(marker in text, f"Documentation marker missing from {relative_path}: {marker}")


def main() -> None:
    try:
        record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        validate(record)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise SystemExit(f"INVALID phase2.fonll_a_contract_amendment: {error}") from error
    print("VALID phase2.fonll_a_contract_amendment")


if __name__ == "__main__":
    main()
