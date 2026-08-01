#!/usr/bin/env python3
"""Generate and validate the terminal D1D signed-generator planning decision.

This module records a desk-review decision only.  It does not import, compile,
link, or execute generator software.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "partonsbi.phase1bd.d1d.terminal-decision.v1"
ARTIFACT = "docs/phase1bd_d1d_terminal_decision.json"

ALLOWED_DECISIONS = {
    "INCONCLUSIVE",
    "DO_NOT_AUTHORIZE_FURTHER_GENERATOR_PROTOTYPE",
}
ALLOWED_SCORES = {
    "SUPPORTED",
    "SUPPORTED_WITH_QUALIFICATION",
    "NOT_SUPPORTED",
    "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE",
    "NOT_APPLICABLE",
}
AUTHORIZATION_FLAGS = (
    "IMPLEMENTATION_AUTHORIZED",
    "PROTOTYPE_AUTHORIZED",
    "PYTHIA_FORK_AUTHORIZED",
    "SIGNED_WEIGHT_PROTOTYPE_AUTHORIZED",
    "ALTERNATIVE_GENERATOR_AUTHORIZED",
    "PYTHIA_INIT_AUTHORIZED",
    "PYTHIA_NEXT_AUTHORIZED",
    "EVENT_GENERATION_AUTHORIZED",
    "DATASET_AUTHORIZED",
    "D2_AUTHORIZED",
)
ARCHITECTURES = (
    "A_REPOSITORY_OWNED_PYTHIA_FORK_OR_PATCH",
    "B_SIGNED_WEIGHT_GENERATOR_ARCHITECTURE",
    "C_ALTERNATIVE_GENERATOR_OR_TRANSPORT_INTERFACE",
    "D_STOP_FURTHER_GENERATOR_COUPLING_WORK",
)
CRITERIA = (
    "signed_scalar_preservation",
    "nonnegative_probability_rate_validity",
    "hard_process_coverage",
    "isr_sudakov_coverage",
    "beam_remnant_coverage",
    "flavor_categorical_selection",
    "denominator_ratio_validity",
    "maximum_envelope_rejection_semantics",
    "event_weight_semantics",
    "strict_support_no_extrapolation",
    "alpha_s_consistency",
    "full_neutral_current_gamma_z_compatibility",
    "deterministic_identity_and_provenance",
    "thread_process_safety",
    "build_deployment_reproducibility",
    "license_redistribution",
    "upstream_maintenance_burden",
    "bounded_prototype_falsifiability",
    "amortized_set_inference_compatibility",
    "authorization_hierarchy_compatibility",
)


class DecisionError(RuntimeError):
    """Raised when the planning-decision contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DecisionError(message)


def score(status: str, rationale: str, *source_ids: str) -> dict[str, Any]:
    return {"primary_source_ids": list(source_ids), "rationale": rationale, "status": status}


def derive_decision(rule: dict[str, Any]) -> str:
    """Derive the only non-authorizing outcome justified by the rule inputs."""
    if (
        rule["no_current_architecture_has_coherent_bounded_path"]
        and rule["disproportionate_cost_supported_for_all_routes"]
        and not rule["potentially_coherent_route_remains"]
    ):
        return "DO_NOT_AUTHORIZE_FURTHER_GENERATOR_PROTOTYPE"
    if (
        rule["potentially_coherent_route_remains"]
        and rule["primary_or_mathematical_evidence_insufficient"]
    ):
        return "INCONCLUSIVE"
    raise DecisionError("decision-rule inputs do not derive an allowed outcome")


def build_decision() -> dict[str, Any]:
    sources = {
        "D1C": {
            "kind": "repository_evidence",
            "path": "docs/phase1bd_d1c_decision.json",
            "sha256": "1ce8a824175d078887bef6fc7c72bbccb2b7c8277cd9669c2a355ced42a6e41b",
        },
        "D1D_AUDIT_V6": {
            "kind": "repository_evidence",
            "path": "docs/phase1bd_d1d_pythia_semantics_audit.json",
            "sha256": "bd63eb4b779c8f6fa622b4a4111fa07a963303d7c80ba3761c339bb764a5b430",
        },
        "D1D_DECISION": {
            "kind": "repository_evidence",
            "path": "docs/phase1bd_d1d_pythia_provenance_slice_decision.json",
            "sha256": "f92958fe745d64c24cd6d12222537154af7d916f24a0c7362c460123d46e04d7",
        },
        "HERWIG_7_0": {"kind": "primary_software_paper", "url": "https://arxiv.org/abs/1512.01178"},
        "HERWIG_7_3": {"kind": "primary_software_paper", "url": "https://arxiv.org/abs/2312.05175"},
        "HERWIGPP_MANUAL": {"kind": "primary_manual_paper", "url": "https://arxiv.org/abs/0803.0883"},
        "LHEF_STANDARD": {"kind": "primary_standard_paper", "url": "https://arxiv.org/abs/hep-ph/0609017"},
        "MCATNLO": {"kind": "primary_research_paper", "url": "https://arxiv.org/abs/hep-ph/0204244"},
        "SHERPA_3": {"kind": "primary_software_paper", "url": "https://arxiv.org/abs/2410.22148"},
        "SHERPA_DIS": {"kind": "official_documentation", "url": "https://sherpa-team.gitlab.io/sherpa/master/examples.html"},
        "SHERPA_EXTERNAL_PDF": {"kind": "official_documentation", "url": "https://sherpa-team.gitlab.io/sherpa/v3.0.0alpha1/manual/customization/external-pdf.html"},
        "SHERPA_ISR": {"kind": "official_documentation", "url": "https://sherpa-team.gitlab.io/sherpa/v3.0.1/manual/parameters/isr.html"},
        "SHERPA_MANUAL": {"kind": "official_documentation", "url": "https://sherpa-team.gitlab.io/sherpa/master/index_single.html"},
        "SHERPA_SOURCE": {"kind": "official_source_repository", "url": "https://gitlab.com/sherpa-team/sherpa/-/tree/master"},
    }

    candidates = [
        {
            "candidate_id": "SHERPA_EXTERNAL_PDF_FULL_DIS_STACK",
            "evidence_requirements": {
                "alpha_s_routing": score("SUPPORTED_WITH_QUALIFICATION", "The official ISR documentation exposes PDF and alpha_s routing, but not signed-PDF consistency across every consumer.", "SHERPA_ISR", "SHERPA_DIS"),
                "beam_remnant_semantics": score("SUPPORTED_WITH_QUALIFICATION", "Beam-remnant machinery is documented; validity for signed internal PDF rates is not established.", "SHERPA_MANUAL", "SHERPA_3"),
                "hard_process_semantics": score("SUPPORTED", "The official examples include neutral-current lepton-proton DIS with gamma/Z exchange.", "SHERPA_DIS"),
                "license_redistribution": score("SUPPORTED_WITH_QUALIFICATION", "Source and license files are public; any redistributed modification would still require a dedicated license review.", "SHERPA_SOURCE"),
                "maintained_source_build_availability": score("SUPPORTED", "An official maintained source repository and build documentation are available.", "SHERPA_SOURCE", "SHERPA_3"),
                "negative_rate_or_signed_weight_treatment": score("SUPPORTED_WITH_QUALIFICATION", "Primary literature supports negative final event weights in NLO matching, not negative PDFs inside all sampling kernels.", "SHERPA_3", "MCATNLO"),
                "pointer_provider_coverage": score("SUPPORTED_WITH_QUALIFICATION", "The external PDF API exposes scalar accessors and copies; complete internal consumer coverage is not proven.", "SHERPA_EXTERNAL_PDF"),
                "reproducibility": score("SUPPORTED_WITH_QUALIFICATION", "Versioned source and configuration are available, while the proposed signed contract has no validated identity record.", "SHERPA_SOURCE", "SHERPA_3"),
                "signed_pdf_scalar_preservation": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "No reviewed primary source proves signed scalar preservation through hard, ISR, and remnant consumers."),
                "isr_backward_evolution_semantics": score("SUPPORTED_WITH_QUALIFICATION", "ISR and PDF variation support are documented, but signed-kernel probability validity is not.", "SHERPA_ISR"),
            },
            "result": "POTENTIALLY_COHERENT_INTERFACE_WITH_UNRESOLVED_SIGNED_SEMANTICS",
        },
        {
            "candidate_id": "HERWIG_PDF_AND_SHOWER_STACK",
            "evidence_requirements": {
                "alpha_s_routing": score("SUPPORTED_WITH_QUALIFICATION", "Herwig 7.3 documents separate ISR and FSR alpha_s controls; complete PDF-provider coupling is unproven.", "HERWIG_7_3"),
                "beam_remnant_semantics": score("SUPPORTED_WITH_QUALIFICATION", "The primary manual describes remnant construction, not signed-PDF validity.", "HERWIGPP_MANUAL"),
                "hard_process_semantics": score("SUPPORTED_WITH_QUALIFICATION", "Herwig is documented for lepton-hadron hard scattering, but this exact fixed contract is not validated.", "HERWIGPP_MANUAL", "HERWIG_7_0", "HERWIG_7_3"),
                "license_redistribution": score("SUPPORTED_WITH_QUALIFICATION", "The current software paper identifies GPLv3 availability; redistribution details require a dedicated review.", "HERWIG_7_3"),
                "maintained_source_build_availability": score("SUPPORTED", "The current software paper identifies maintained public source and build availability.", "HERWIG_7_3"),
                "negative_rate_or_signed_weight_treatment": score("SUPPORTED_WITH_QUALIFICATION", "MC@NLO supports negative event weights, not negative probabilities in PDF-dependent shower/remnant steps.", "HERWIG_7_0", "MCATNLO"),
                "pointer_provider_coverage": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "No bounded primary-source audit establishes provider coverage for the present signed PDF contract."),
                "reproducibility": score("SUPPORTED_WITH_QUALIFICATION", "Versioned releases are documented, but no validated deterministic identity exists for this proposed coupling.", "HERWIG_7_3"),
                "signed_pdf_scalar_preservation": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "No reviewed primary source proves signed scalar preservation through hard, ISR, and remnant consumers."),
                "isr_backward_evolution_semantics": score("SUPPORTED_WITH_QUALIFICATION", "Backward-evolution shower semantics are documented; signed-kernel probability validity is not.", "HERWIGPP_MANUAL", "HERWIG_7_3"),
            },
            "result": "POTENTIALLY_COHERENT_INTERFACE_WITH_UNRESOLVED_SIGNED_SEMANTICS",
        },
        {
            "candidate_id": "LES_HOUCHES_SIGNED_HARD_EVENT_TRANSPORT",
            "evidence_requirements": {
                "alpha_s_routing": score("NOT_APPLICABLE", "The transport record does not own downstream alpha_s routing."),
                "beam_remnant_semantics": score("NOT_SUPPORTED", "Beam-remnant construction is delegated to the receiving generator.", "LHEF_STANDARD"),
                "hard_process_semantics": score("SUPPORTED_WITH_QUALIFICATION", "The standard transports hard parton-level configurations but does not validate this signed PDF contract.", "LHEF_STANDARD"),
                "license_redistribution": score("NOT_APPLICABLE", "This entry evaluates an interchange standard rather than redistributing a generator."),
                "maintained_source_build_availability": score("NOT_APPLICABLE", "The interchange standard is not a generator implementation."),
                "negative_rate_or_signed_weight_treatment": score("SUPPORTED", "The standard carries event weights and MC@NLO establishes signed hard-event samples.", "LHEF_STANDARD", "MCATNLO"),
                "pointer_provider_coverage": score("NOT_APPLICABLE", "A hard-event record is not a PDF provider interface."),
                "reproducibility": score("SUPPORTED_WITH_QUALIFICATION", "The standardized record supports provenance fields, but downstream generator identity remains separate.", "LHEF_STANDARD"),
                "signed_pdf_scalar_preservation": score("NOT_APPLICABLE", "The interface transports events, not the signed PDF scalar through generator internals."),
                "isr_backward_evolution_semantics": score("NOT_SUPPORTED", "Backward evolution is delegated and therefore cannot be repaired by the transported final weight.", "LHEF_STANDARD"),
            },
            "result": "BOUNDARY_ONLY_NOT_A_COMPLETE_GENERATOR_COUPLING",
        },
    ]

    matrix_statuses = {
        ARCHITECTURES[0]: (
            "NOT_SUPPORTED", "NOT_SUPPORTED", "NOT_SUPPORTED", "NOT_SUPPORTED", "NOT_SUPPORTED",
            "NOT_SUPPORTED", "NOT_SUPPORTED", "NOT_SUPPORTED", "NOT_SUPPORTED", "SUPPORTED_WITH_QUALIFICATION",
            "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "NOT_SUPPORTED", "SUPPORTED_WITH_QUALIFICATION",
            "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "SUPPORTED_WITH_QUALIFICATION", "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE",
            "NOT_SUPPORTED", "NOT_SUPPORTED", "SUPPORTED_WITH_QUALIFICATION", "NOT_SUPPORTED",
        ),
        ARCHITECTURES[1]: (
            "NOT_SUPPORTED", "NOT_SUPPORTED", "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "NOT_SUPPORTED", "NOT_SUPPORTED",
            "NOT_SUPPORTED", "NOT_SUPPORTED", "NOT_SUPPORTED", "SUPPORTED_WITH_QUALIFICATION",
            "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE",
            "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "NOT_SUPPORTED", "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE",
            "NOT_SUPPORTED", "NOT_APPLICABLE", "NOT_SUPPORTED", "NOT_SUPPORTED", "SUPPORTED_WITH_QUALIFICATION",
            "NOT_SUPPORTED",
        ),
        ARCHITECTURES[2]: (
            "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "NOT_SUPPORTED", "SUPPORTED_WITH_QUALIFICATION",
            "SUPPORTED_WITH_QUALIFICATION", "SUPPORTED_WITH_QUALIFICATION", "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE",
            "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE",
            "SUPPORTED_WITH_QUALIFICATION", "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "SUPPORTED_WITH_QUALIFICATION",
            "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "SUPPORTED_WITH_QUALIFICATION",
            "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "SUPPORTED_WITH_QUALIFICATION", "SUPPORTED_WITH_QUALIFICATION",
            "SUPPORTED_WITH_QUALIFICATION", "NOT_SUPPORTED", "SUPPORTED_WITH_QUALIFICATION", "NOT_SUPPORTED",
        ),
        ARCHITECTURES[3]: (
            "NOT_APPLICABLE", "NOT_APPLICABLE", "NOT_APPLICABLE", "NOT_APPLICABLE", "NOT_APPLICABLE",
            "NOT_APPLICABLE", "NOT_APPLICABLE", "NOT_APPLICABLE", "NOT_APPLICABLE", "NOT_APPLICABLE",
            "NOT_APPLICABLE", "NOT_APPLICABLE", "SUPPORTED", "NOT_APPLICABLE", "NOT_APPLICABLE",
            "NOT_APPLICABLE", "SUPPORTED", "NOT_APPLICABLE", "SUPPORTED_WITH_QUALIFICATION", "SUPPORTED",
        ),
    }
    matrix_sources = {
        ARCHITECTURES[0]: {
            "strict_support_no_extrapolation": ("D1C", "D1D_DECISION"),
            "deterministic_identity_and_provenance": ("D1D_DECISION",),
            "build_deployment_reproducibility": ("D1D_DECISION",),
            "amortized_set_inference_compatibility": ("D1C",),
        },
        ARCHITECTURES[1]: {
            "event_weight_semantics": ("MCATNLO", "LHEF_STANDARD"),
            "amortized_set_inference_compatibility": ("D1C",),
        },
        ARCHITECTURES[2]: {
            "hard_process_coverage": ("SHERPA_DIS", "HERWIGPP_MANUAL", "HERWIG_7_3"),
            "isr_sudakov_coverage": ("SHERPA_ISR", "HERWIGPP_MANUAL", "HERWIG_7_3"),
            "beam_remnant_coverage": ("SHERPA_MANUAL", "HERWIGPP_MANUAL"),
            "event_weight_semantics": ("LHEF_STANDARD", "MCATNLO", "SHERPA_3", "HERWIG_7_0"),
            "alpha_s_consistency": ("SHERPA_ISR", "HERWIG_7_3"),
            "deterministic_identity_and_provenance": ("LHEF_STANDARD", "SHERPA_SOURCE", "HERWIG_7_3"),
            "build_deployment_reproducibility": ("SHERPA_SOURCE", "HERWIG_7_3"),
            "license_redistribution": ("SHERPA_SOURCE", "HERWIG_7_3"),
            "upstream_maintenance_burden": ("SHERPA_SOURCE", "SHERPA_3", "HERWIG_7_3"),
            "amortized_set_inference_compatibility": ("LHEF_STANDARD", "MCATNLO"),
        },
        ARCHITECTURES[3]: {
            "deterministic_identity_and_provenance": ("D1D_DECISION",),
            "upstream_maintenance_burden": ("D1D_DECISION",),
            "amortized_set_inference_compatibility": ("D1C", "D1D_DECISION"),
            "authorization_hierarchy_compatibility": ("D1D_DECISION",),
        },
    }
    matrix = {
        architecture: {
            criterion: score(
                status,
                "See the corresponding architecture assessment and primary-source limitations.",
                *matrix_sources[architecture].get(criterion, ()),
            )
            for criterion, status in zip(CRITERIA, statuses, strict=True)
        }
        for architecture, statuses in matrix_statuses.items()
    }

    rule = {
        "architecture_comparison_ready": False,
        "disproportionate_cost_supported_for_all_routes": False,
        "mandatory_d1d_a_gate_passed": False,
        "no_current_architecture_has_coherent_bounded_path": False,
        "potentially_coherent_route_remains": True,
        "primary_or_mathematical_evidence_insufficient": True,
    }
    decision = derive_decision(rule)
    return {
        "architecture_assessments": {
            ARCHITECTURES[0]: {
                "assessment": "NOT_SUPPORTED_FOR_A_BOUNDED_PROTOTYPE",
                "distinctions": {
                    "bypass_reader_interface": "Does not resolve downstream sign-sensitive consumers or provide a validated dataflow contract.",
                    "downstream_algorithm_redesign": "Would require reviewed semantics for hard-process, ISR, remnant, flavor selection, ratios, maxima, envelopes, and cumulative selection.",
                    "public_reader_change": "Already established insufficient by D1C and D1D-A.",
                    "versioned_fork_maintenance": "Creates a continuing upstream-integration and scientific-validation burden.",
                },
                "rationale": "The negative D1D-A record does not supply the complete consumer evidence required to bound a fork or redesign.",
            },
            ARCHITECTURES[1]: {
                "assessment": "NOT_SUPPORTED_FOR_THE_FIXED_CONTRACT",
                "distinctions": {
                    "ordinary_positive_probability_generation": "Requires valid nonnegative sampling probabilities and rates.",
                    "signed_event_samples": "Can represent cancellations between complete weighted events but do not repair invalid internal sampling steps.",
                    "signed_final_event_weight": "Cannot retroactively repair negative probabilities, denominators, maxima, categorical choices, or rejection sampling.",
                    "signed_kernels_or_sudakovs": "Would require a reviewed mathematical formulation and a generator designed to sample it.",
                    "signed_matrix_element_contributions": "Are not equivalent to signed PDFs entering every internal generator consumer.",
                    "weighted_empirical_event_sets": "Are compatible with set inference only after a coherent event-generation measure exists.",
                },
                "rationale": "No reviewed mathematical construction establishes valid signed internal sampling for the present PDF family and full generator path.",
            },
            ARCHITECTURES[2]: {
                "assessment": "INCONCLUSIVE_PRIMARY_EVIDENCE_GAPS",
                "bounded_candidate_count": 3,
                "candidates": candidates,
                "rationale": "Sherpa and Herwig expose potentially relevant full-generator interfaces, while LHEF transports signed complete-event weights only; none proves the fixed signed-PDF contract end to end.",
            },
            ARCHITECTURES[3]: {
                "assessment": "SUPPORTED_WITH_QUALIFICATION_FOR_CURRENT_CONTRACT",
                "rationale": "Stopping current generator-coupling work protects the fixed D0R signed binary64 contract, theta box, shape-only fixed-N MVP, and hard/ISR/remnant consistency requirement. This is not a universal impossibility theorem and can be reopened only on new reviewed evidence.",
            },
        },
        "authorization": {flag: False for flag in AUTHORIZATION_FLAGS},
        "decision": decision,
        "decision_criteria": {"criterion_order": list(CRITERIA), "matrix": matrix},
        "decision_rule": {**rule, "derived_decision": decision},
        "dependencies": {
            "blocked_issue": 10,
            "planning_issue": 42,
            "project_fields_must_remain_unchanged": True,
        },
        "evaluated_evidence": {
            "primary_sources": sources,
            "source_policy": "OFFICIAL_DOCUMENTATION_SOURCE_REPOSITORY_STANDARD_OR_PRIMARY_PAPER_ONLY",
        },
        "failure_scope": [
            "No current architecture is authorized for the fixed signed D0R generator-coupling contract.",
            "The minimal public-reader patch remains insufficient.",
            "The rejected provenance slice remains diagnostic rather than architecture evidence.",
        ],
        "fixed_scientific_contract": {
            "amortized_objective": "p(theta_PDF | D) for a set of events D",
            "event_sampling": "shape-only fixed-N conditional event distribution",
            "generator_consistency": ["hard_process", "ISR_backward_evolution", "beam_remnant"],
            "pdf_family": "ct18nlo_two_parameter_boundary_v2",
            "scalar_contract": "signed binary64 x*f with strict support and no extrapolation",
            "theta_box": {"delta_v": [-0.2, 0.2], "lambda_sea": [-0.25, 0.25]},
        },
        "next_step": "SCIENTIFIC_REVIEW_OF_TERMINAL_D1D_B_DECISION",
        "non_failure_scope": [
            "This decision is not a universal impossibility theorem for signed event generators.",
            "It does not reject weighted empirical sets after a coherent event measure exists.",
            "It does not alter the fixed PDF-family or inference contracts.",
        ],
        "precedence": {
            "ARCHITECTURE_COMPARISON_READY": False,
            "D1C_FINAL_DECISION": "FAIL",
            "D1D_A_FAILED_GATE": "provenance_evidence_integrity",
            "D1D_A_FINAL_DECISION": "FAIL",
            "MINIMAL_PUBLIC_READER_PATCH": "INSUFFICIENT",
            "PROVENANCE_SLICE_V1_DECISION": "FAIL",
            "PROVENANCE_SLICE_V1_STATUS": "REJECTED_DIAGNOSTIC",
        },
        "reopen_conditions": [
            {"authorization_granted": False, "condition": "A reviewed mathematical signed-kernel and signed-Sudakov formulation covering all internal sampling decisions."},
            {"authorization_granted": False, "condition": "A primary-source generator interface with proven signed scalar, rate, ISR, remnant, and event-weight semantics."},
            {"authorization_granted": False, "condition": "An independently validated complete consumer and dataflow graph for the proposed coupling."},
            {"authorization_granted": False, "condition": "A separately reviewed and approved change to the PDF-family or inference contract."},
        ],
        "schema_version": SCHEMA,
        "unresolved_evidence": [
            "No complete independently validated PDF-consumer graph is available.",
            "No reviewed signed-kernel or signed-Sudakov probability construction is available.",
            "Sherpa and Herwig primary sources do not prove signed scalar preservation through hard process, ISR, and remnants.",
            "Full neutral-current gamma/Z, strict-support, provider, alpha_s, and concurrency behavior remain unvalidated for candidate alternatives.",
            "Maintenance and redistribution costs are not sufficiently bounded across every potentially coherent route.",
        ],
        "validation": {
            "artifact_is_deterministically_generated": True,
            "command": "python3 scripts/phase1bd_d1d_terminal_decision.py --validate",
            "physics_execution_performed": False,
        },
    }


def walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_strings(child)


def validate_decision(value: dict[str, Any]) -> None:
    require(value.get("schema_version") == SCHEMA, "wrong schema_version")
    require(value.get("decision") in ALLOWED_DECISIONS, "decision is not an allowed non-authorizing outcome")
    expected = build_decision()
    require(value == expected, "artifact differs from deterministic generator output")
    require(value["decision"] == derive_decision(value["decision_rule"]), "stored decision is not derived from rule inputs")

    precedence = value["precedence"]
    require(precedence["D1C_FINAL_DECISION"] == "FAIL", "D1C failure changed")
    require(precedence["MINIMAL_PUBLIC_READER_PATCH"] == "INSUFFICIENT", "minimal-reader conclusion changed")
    require(precedence["PROVENANCE_SLICE_V1_DECISION"] == "FAIL", "provenance decision changed")
    require(precedence["PROVENANCE_SLICE_V1_STATUS"] == "REJECTED_DIAGNOSTIC", "provenance status changed")
    require(precedence["D1D_A_FINAL_DECISION"] == "FAIL", "D1D-A failure changed")
    require(precedence["D1D_A_FAILED_GATE"] == "provenance_evidence_integrity", "D1D-A failed gate changed")
    require(precedence["ARCHITECTURE_COMPARISON_READY"] is False, "architecture readiness became true")

    authorization = value["authorization"]
    require(set(authorization) == set(AUTHORIZATION_FLAGS), "authorization flag set differs from contract")
    require(all(authorization[flag] is False for flag in AUTHORIZATION_FLAGS), "an authorization flag became true")
    require(all(item.get("authorization_granted") is False for item in value["reopen_conditions"]), "a reopen condition grants authorization")

    assessments = value["architecture_assessments"]
    require(set(assessments) == set(ARCHITECTURES), "all four architecture classes must be assessed")
    criteria = value["decision_criteria"]
    require(tuple(criteria["criterion_order"]) == CRITERIA, "the exact twenty criteria are required")
    require(set(criteria["matrix"]) == set(ARCHITECTURES), "criterion matrix architecture set is incomplete")
    for architecture in ARCHITECTURES:
        row = criteria["matrix"][architecture]
        require(set(row) == set(CRITERIA), f"criterion row is incomplete for {architecture}")
        for criterion in CRITERIA:
            require(row[criterion]["status"] in ALLOWED_SCORES, f"invalid score for {architecture}/{criterion}")
            if row[criterion]["status"] in {"SUPPORTED", "SUPPORTED_WITH_QUALIFICATION"}:
                require(row[criterion]["primary_source_ids"], f"support lacks cited evidence for {architecture}/{criterion}")
            if row[criterion]["status"] == "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE":
                require(not row[criterion]["primary_source_ids"], f"unavailable evidence cites support for {architecture}/{criterion}")
            require(
                all(source_id in value["evaluated_evidence"]["primary_sources"] for source_id in row[criterion]["primary_source_ids"]),
                f"unknown evidence source for {architecture}/{criterion}",
            )

    candidates = assessments[ARCHITECTURES[2]]["candidates"]
    require(len(candidates) <= 3, "bounded desk review contains more than three candidates")
    require(len(candidates) == 3, "the three declared candidates are required")
    for candidate in candidates:
        for requirement, finding in candidate["evidence_requirements"].items():
            require(finding["status"] in ALLOWED_SCORES, f"invalid candidate evidence status: {requirement}")
            if finding["status"] == "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE":
                require(not finding["primary_source_ids"], "missing primary evidence cannot cite support")
            if finding["status"] in {"SUPPORTED", "SUPPORTED_WITH_QUALIFICATION"}:
                require(bool(finding["primary_source_ids"]), "support must cite primary evidence")

    forbidden = ("AUTHORIZE_SEPARATE_BOUNDED_",)
    require(not any(text.startswith(forbidden) for text in walk_strings(value)), "an authorizing outcome appears")
    require(value["authorization"]["D2_AUTHORIZED"] is False, "D2 became authorized")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--artifact", default=ARTIFACT)
    args = parser.parse_args()
    if args.generate == args.validate:
        parser.error("choose exactly one of --generate or --validate")
    path = Path(args.artifact)
    try:
        if args.generate:
            value = build_decision()
            validate_decision(value)
            write_json(path, value)
            print(f"generated {path}")
        else:
            value = json.loads(path.read_text(encoding="utf-8"))
            validate_decision(value)
            print("terminal D1D planning decision validation: PASS")
    except (DecisionError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"terminal D1D planning decision validation: FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
