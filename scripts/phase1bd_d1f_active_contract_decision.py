#!/usr/bin/env python3
"""Generate and validate the planning-only Phase 1B-D1F v3 decision.

The record independently derives (1) disposition of the failed current
full-generator line and (2) priority among separate prospective contracts.
This module invokes no parser, generator, PDF library, event code, numerical
physics, dataset pipeline, or neural code.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "partonsbi.phase1bd.d1f.active-contract-decision.v3"
ARTIFACT = "docs/phase1bd_d1f_active_contract_decision.json"

OPTION_IDS = (
    "PRESERVE_CURRENT_CONTRACT_AND_PAUSE",
    "NEW_NONNEGATIVE_GENERATOR_COMPATIBLE_PDF_FAMILY",
    "LOWER_LEVEL_DIS_HARD_EVENT_MODEL",
    "WEIGHTED_EMPIRICAL_EVENT_SET",
    "SIGNED_WEIGHT_INFERENCE_RESEARCH",
    "TERMINATE_PHASE1B_GENERATOR_COUPLING",
)
REDESIGN_OPTIONS = OPTION_IDS[1:5]

CURRENT_LINE_DISPOSITIONS = {
    "CONTINUE_CURRENT_FULL_GENERATOR_LINE",
    "MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE",
    "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING",
}
PREFERRED_REVIEWS = {"NONE", *REDESIGN_OPTIONS}
TOP_LEVEL_DECISIONS = {
    "RECOMMEND_NEW_NONNEGATIVE_FAMILY_CONTRACT_REVIEW",
    "RECOMMEND_LOWER_LEVEL_HARD_EVENT_CONTRACT_REVIEW",
    "RECOMMEND_WEIGHTED_EMPIRICAL_SET_CONTRACT_REVIEW",
    "RECOMMEND_SIGNED_WEIGHT_INFERENCE_RESEARCH",
    "MAINTAIN_CURRENT_CONTRACT_AND_PAUSE",
    "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING",
}

EVIDENCE_STATUSES = {
    "SUPPORTED",
    "SUPPORTED_WITH_QUALIFICATION",
    "NOT_SUPPORTED",
    "NOT_EVALUATED",
}
CURRENT_EVIDENCE_CLASSES = {
    "DIRECT_IMMUTABLE_EVIDENCE",
    "EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE",
    "NOT_EVALUATED",
}
SCORE_EVIDENCE_CLASSES = {
    "DIRECT_IMMUTABLE_EVIDENCE",
    "EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE",
    "PROSPECTIVE_HYPOTHESIS",
    "NOT_APPLICABLE",
}
SCORE_STATUSES = {
    "SUPPORTED",
    "SUPPORTED_WITH_QUALIFICATION",
    "NOT_SUPPORTED",
    "PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE",
    "NOT_APPLICABLE",
}
GATE_STATUSES = {"PASS", "PASS_WITH_QUALIFICATION", "FAIL", "NOT_APPLICABLE"}

CONTRACT_FIELDS = (
    "latent_parameter_theta",
    "active_pdf_family_identity",
    "simulator_or_data_generating_law",
    "normalized_probability_measure",
    "observed_event_set_representation",
    "event_and_set_weights",
    "sample_size_semantics",
    "rate_shape_semantics",
    "detector_response_contract",
    "support_extrapolation_rules",
    "positivity_signed_value_rules",
    "posterior_target",
    "training_objective",
    "calibration_coverage_target",
    "original_objective_compatibility",
    "preserved_evidence",
    "prospectively_superseded_evidence",
    "issue_roadmap_implications",
    "smallest_falsifiable_next_step",
    "burden_estimate",
)

CRITERIA = (
    "normalized_generative_measure",
    "posterior_target_coherence",
    "set_level_amortized_sbi_compatibility",
    "pdf_interpretability",
    "qcd_factorization_compatibility",
    "strict_support_preservation",
    "no_clipping_preservation",
    "detector_model_feasibility",
    "event_weight_clarity",
    "rate_shape_clarity",
    "calibration_feasibility",
    "independent_falsifiability",
    "implementation_boundedness",
    "validation_boundedness",
    "reproducibility",
    "maintenance_burden",
    "existing_rust_cpp_infrastructure_compatibility",
    "end_to_end_scientific_mvp_path",
    "scientific_objective_change_risk",
    "evidence_value_on_failure",
)

AUTHORIZATION_FLAGS = (
    "IMPLEMENTATION_AUTHORIZED",
    "PROTOTYPE_AUTHORIZED",
    "PDF_FAMILY_REDESIGN_AUTHORIZED",
    "LOWER_LEVEL_SIMULATOR_AUTHORIZED",
    "WEIGHTED_SET_OBJECTIVE_AUTHORIZED",
    "SIGNED_WEIGHT_RESEARCH_AUTHORIZED",
    "PYTHIA_INIT_AUTHORIZED",
    "PYTHIA_NEXT_AUTHORIZED",
    "EVENT_GENERATION_AUTHORIZED",
    "DATASET_AUTHORIZED",
    "NEURAL_TRAINING_AUTHORIZED",
    "D2_AUTHORIZED",
)

CURRENT_EVIDENCE_FIELDS = (
    "full_generator_architecture_ready",
    "bounded_static_evidence_path_exists",
    "bounded_signed_kernel_path_exists",
    "bounded_alternative_generator_path_exists",
    "accepted_generator_measure_exists",
    "accepted_runtime_consumer_closure_exists",
    "implementation_task_credibly_bounded",
    "current_contract_preserved_by_continuation",
    "redesigns_are_separate_contracts",
)

LOWER_LEVEL_PROOF_OBLIGATIONS = (
    "EXACT_E_MINUS_AND_E_PLUS_NC_DIFFERENTIAL_FORMULA",
    "F2_FL_XF3_CONVENTIONS_AND_SIGNS",
    "GAMMA_Z_AND_INTERFERENCE_TERMS",
    "ELECTROWEAK_PARAMETER_SCHEME",
    "FACTORIZATION_AND_RENORMALIZATION_SCALES",
    "FLAVOR_AND_HEAVY_QUARK_TREATMENT",
    "PHASE_SPACE_COORDINATES_AND_JACOBIAN",
    "FINITE_NONZERO_NORMALIZATION_FOR_EVERY_ACCEPTED_THETA",
    "NONNEGATIVE_COMPLETE_DIFFERENTIAL_RATE_ON_ACCEPTED_SUPPORT",
    "STRICT_PDF_SUPPORT_INTERSECTION",
    "DETECTOR_AND_ACCEPTANCE_KERNEL_NORMALIZATION",
    "PERFECT_DETECTOR_IDENTITY_KERNEL_SPECIAL_CASE",
    "INDEPENDENT_NUMERICAL_CLOSURE",
    "EXPLICIT_OMITTED_PHYSICS_DECLARATION",
)

SUPERSESSION_STATUSES = {
    "PRESERVED",
    "PRESERVED_AS_HISTORICAL_EVIDENCE",
    "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED",
    "WOULD_REQUIRE_EXPLICIT_CONFIRMATION_IF_SEPARATELY_ACCEPTED",
    "WOULD_REQUIRE_NEW_DECISION_IF_SEPARATELY_ACCEPTED",
    "NOT_COMPLETED_BY_LOWER_LEVEL_MODEL",
    "CURRENT_STATE_PRESERVED",
    "NOT_APPLICABLE",
}

HISTORICAL_RESULT_KEYS = {
    "D0R_NEGATIVE_AND_POSITIVE_EVIDENCE",
    "D1_RESULT",
    "D1R_RESULT",
    "D1C_RESULT",
    "D1D_RESULT",
    "D1E_RESULT",
}

PREFERENCE_CRITICAL_CRITERIA = {
    "independent_falsifiability",
    "end_to_end_scientific_mvp_path",
    "scientific_objective_change_risk",
    "no_clipping_preservation",
}


class ContractDecisionError(RuntimeError):
    """Raised when the D1F evidence or derivation contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractDecisionError(message)


def field(status: str, statement: str, **extra: Any) -> dict[str, Any]:
    return {"status": status, "statement": statement, **extra}


def build_precedence() -> dict[str, Any]:
    return {
        "D1C_FINAL_DECISION": "FAIL",
        "MINIMAL_PUBLIC_READER_PATCH": "INSUFFICIENT",
        "PROVENANCE_SLICE_V1_DECISION": "FAIL",
        "PROVENANCE_SLICE_V1_STATUS": "REJECTED_DIAGNOSTIC",
        "D1D_A_FINAL_DECISION": "FAIL",
        "D1D_A_FAILED_GATE": "provenance_evidence_integrity",
        "D1D_B_FINAL_DECISION": "INCONCLUSIVE",
        "D1E_FINAL_DECISION": "INCONCLUSIVE",
        "D1E_PREFERRED_FEASIBILITY_CANDIDATE": "LLVM_CLANG_LIBTOOLING_18_1_8",
        "D1E_SELECTED_TOOLCHAIN": None,
        "CURRENT_OPERATIONAL_POLICY": "PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION",
        "ARCHITECTURE_COMPARISON_READY": False,
        "D2_AUTHORIZED": False,
    }


def build_repository_evidence() -> dict[str, dict[str, Any]]:
    return {
        "ADR001_D0R_FAMILY": {
            "path": "docs/adr/ADR-001-continuous-pdf-family.md",
            "claims": {
                "D0R_THETA_AND_PDF_INTERPRETABILITY": {
                    "option_scope": list(OPTION_IDS),
                    "criterion_scope": ["pdf_interpretability", "scientific_objective_change_risk"],
                    "maximum_supported_status": "SUPPORTED",
                },
                "STRICT_SUPPORT_AND_NO_CLIPPING": {
                    "option_scope": list(OPTION_IDS),
                    "criterion_scope": ["strict_support_preservation", "no_clipping_preservation"],
                    "maximum_supported_status": "SUPPORTED",
                },
            },
        },
        "ADR003_EVENT_SEMANTICS": {
            "path": "docs/adr/ADR-003-event-sampling-semantics.md",
            "claims": {
                "FIXED_N_SHAPE_ONLY_SET_OBJECTIVE": {
                    "option_scope": list(OPTION_IDS),
                    "criterion_scope": ["posterior_target_coherence", "set_level_amortized_sbi_compatibility", "rate_shape_clarity"],
                    "maximum_supported_status": "SUPPORTED",
                },
                "WEIGHTED_SETS_ARE_NOT_IID_UNWEIGHTED": {
                    "option_scope": list(OPTION_IDS),
                    "criterion_scope": ["set_level_amortized_sbi_compatibility", "event_weight_clarity"],
                    "maximum_supported_status": "SUPPORTED",
                },
                "CALIBRATION_REQUIRED": {
                    "option_scope": list(OPTION_IDS),
                    "criterion_scope": ["calibration_feasibility"],
                    "maximum_supported_status": "SUPPORTED_WITH_QUALIFICATION",
                },
            },
        },
        "ADR004_D0R_SIGN_TOPOLOGY": {
            "path": "docs/adr/ADR-004-d0-baseline-and-admissibility.md",
            "claims": {
                "D0R_SIGNED_NLO_VALUES": {
                    "option_scope": [OPTION_IDS[0], OPTION_IDS[4]],
                    "criterion_scope": ["qcd_factorization_compatibility"],
                    "maximum_supported_status": "SUPPORTED_WITH_QUALIFICATION",
                },
                "D0R_HISTORICAL_IDENTITY": {
                    "option_scope": list(OPTION_IDS),
                    "criterion_scope": ["pdf_interpretability", "scientific_objective_change_risk"],
                    "maximum_supported_status": "SUPPORTED_WITH_QUALIFICATION",
                },
            },
        },
        "D1D_FINAL_RECORD": {
            "path": "docs/phase1bd_d1d_terminal_decision.json",
            "claims": {
                "FULL_GENERATOR_ARCHITECTURE_NOT_READY": {"current_fields": ["full_generator_architecture_ready"]},
                "SIGNED_KERNEL_PATH_NOT_BOUNDED": {"current_fields": ["bounded_signed_kernel_path_exists"]},
                "ALTERNATIVE_GENERATOR_ROUTES_POSSIBLE_WITH_EVIDENCE_GAPS": {
                    "current_fields": ["bounded_alternative_generator_path_exists", "current_contract_preserved_by_continuation"],
                    "option_scope": [OPTION_IDS[0], OPTION_IDS[5]],
                    "criterion_scope": ["maintenance_burden"],
                    "maximum_supported_status": "SUPPORTED_WITH_QUALIFICATION",
                },
                "ACCEPTED_GENERATOR_ARCHITECTURE_ABSENT": {
                    "current_fields": ["accepted_generator_measure_exists"],
                    "option_scope": [OPTION_IDS[0], OPTION_IDS[4]],
                    "criterion_scope": ["normalized_generative_measure"],
                    "maximum_supported_status": "SUPPORTED_WITH_QUALIFICATION",
                },
                "SIGNED_INTERNAL_RATE_CONSTRUCTION_ABSENT": {"current_fields": ["accepted_generator_measure_exists"]},
                "COMPLETED_GENERATOR_MEASURE_ABSENT": {"current_fields": ["accepted_generator_measure_exists"]},
                "RUNTIME_CONSUMER_CLOSURE_NOT_VALIDATED": {"current_fields": ["accepted_runtime_consumer_closure_exists"]},
                "TERMINATION_IS_NOT_GLOBAL_IMPOSSIBILITY": {"current_fields": []},
            },
        },
        "D1E_FINAL_RECORD": {
            "path": "docs/phase1bd_d1e_consumer_graph_feasibility.json",
            "claims": {
                "CURRENT_STATIC_SCOPE_NOT_CREDIBLY_BOUNDED": {
                    "current_fields": ["bounded_static_evidence_path_exists"],
                    "option_scope": [OPTION_IDS[0], OPTION_IDS[5]],
                    "criterion_scope": ["independent_falsifiability"],
                    "maximum_supported_status": "SUPPORTED_WITH_QUALIFICATION",
                },
                "IMPLEMENTATION_COST_BOUND_NOT_SUPPORTED": {
                    "current_fields": ["implementation_task_credibly_bounded"],
                    "option_scope": [OPTION_IDS[0]],
                    "criterion_scope": ["implementation_boundedness", "validation_boundedness"],
                    "maximum_supported_status": "NOT_SUPPORTED",
                },
                "NO_TOOLCHAIN_SELECTED": {
                    "option_scope": [],
                    "criterion_scope": [],
                    "maximum_supported_status": "PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE",
                },
            },
        },
        "D1F_CONCEPTUAL_REVIEW": {
            "path": "docs/adr/ADR-010-active-scientific-contract-after-generator-pause.md",
            "allowed_roles": ["DECISION_RECORD_DEFINITION", "EXPLICIT_INFERENCE_RECORD", "CONTRACT_DESCRIPTION"],
            "claims": {},
        },
    }


def base_preserved() -> list[str]:
    return [
        "D0R, D1, D1R, D1C, D1D, and D1E results remain immutable evidence.",
        "Strict support, provenance, and the prohibition on hidden clipping remain binding.",
    ]


def build_options() -> dict[str, dict[str, Any]]:
    options = {
        OPTION_IDS[0]: {
            "latent_parameter_theta": field("DEFINED", "theta=(delta_v, lambda_sea) on the accepted D0R box."),
            "active_pdf_family_identity": field("DEFINED", "The accepted versioned D0R family remains active."),
            "simulator_or_data_generating_law": field("NOT_OPERATIONALLY_INSTANTIATED", "The intended full-generator law has no accepted implementation."),
            "normalized_probability_measure": field("CONCEPTUALLY_DEFINED_NOT_OPERATIONALLY_INSTANTIATED", "A normalized selected-event law is conceptually specified but no accepted simulator instantiates it."),
            "observed_event_set_representation": field("DEFINED", "Unordered fixed-N observed event sets; generator truth remains provenance."),
            "event_and_set_weights": field("DEFINED_UNWEIGHTED_PRIMARY", "Primary sets are unweighted; source weights remain provenance."),
            "sample_size_semantics": field("DEFINED_FIXED_N", "Fixed N conditions away rate information."),
            "rate_shape_semantics": field("DEFINED_SHAPE_ONLY", "Shape-only inference with rate diagnostics."),
            "detector_response_contract": field("NOT_EVALUATED", "No accepted detector kernel is instantiated."),
            "support_extrapolation_rules": field("DEFINED_STRICT", "Strict support; no extrapolation or clamping."),
            "positivity_signed_value_rules": field("DEFINED_SIGNED_NO_REPAIR", "Signed binary64 x*f is preserved without clipping."),
            "posterior_target": field("CONCEPTUALLY_DEFINED_NOT_OPERATIONALLY_INSTANTIATED", "p(theta_D0R|D) is defined conceptually but lacks an accepted simulator likelihood."),
            "training_objective": field("NOT_EVALUATED", "A proper objective awaits an accepted data law."),
            "calibration_coverage_target": field("CONCEPTUALLY_DEFINED_NOT_OPERATIONALLY_INSTANTIATED", "SBC and coverage are defined only relative to the unavailable law."),
            "original_objective_compatibility": field("PRESERVED", "Preserves p(theta_PDF|D)."),
            "preserved_evidence": base_preserved(),
            "prospectively_superseded_evidence": [],
            "issue_roadmap_implications": field("CURRENT_LINE_UNBOUNDED", "Issue #10 and D2 remain blocked."),
            "smallest_falsifiable_next_step": field("NO_BOUNDED_CURRENT_LINE_REVIEW", "No bounded current-line reopen task exists."),
            "burden_estimate": field("UNBOUNDED", "Complete generator evidence and signed internal-rate mathematics remain unbounded."),
            "relationship_to_current_line": "CURRENT_LINE",
            "scientific_motivation": field("SUPPORTED", "Preserves the accepted scientific objective, not the failed implementation line."),
            "implementation_ready_claimed": False,
            "hidden_clipping_or_semantic_repair": False,
            "signed_weights_are_probabilities": False,
        },
        OPTION_IDS[1]: {
            "latent_parameter_theta": field("REQUIRES_NEW_DECISION", "A new theta and domain require independent scientific definition."),
            "active_pdf_family_identity": field("NEW_FAMILY_NOT_D0R_CORRECTION", "A prospectively new nonnegative family; D0R remains historical evidence."),
            "simulator_or_data_generating_law": field("CONCEPTUALLY_DEFINED_REQUIRES_PROOFS", "A future full-generator law using nonnegative evolved densities."),
            "normalized_probability_measure": field("CONCEPTUALLY_COHERENT_REQUIRES_NEW_FAMILY_PROOFS", "A normalized law is conditional on positivity and complete generator validation."),
            "observed_event_set_representation": field("DEFINED", "Unordered fixed-N observed event sets."),
            "event_and_set_weights": field("DEFINED_UNWEIGHTED_PRIMARY", "Unweighted selected events after a separately validated law."),
            "sample_size_semantics": field("DEFINED_FIXED_N", "Fixed-N primary sets."),
            "rate_shape_semantics": field("DEFINED_SHAPE_ONLY", "Shape-only primary target."),
            "detector_response_contract": field("NOT_EVALUATED", "A detector kernel requires a new decision."),
            "support_extrapolation_rules": field("DEFINED_STRICT", "Explicit full consumer support without extrapolation."),
            "positivity_signed_value_rules": field("NEW_FAMILY_POSITIVITY_REQUIREMENT", "Positivity is a defining family property, never clipping."),
            "posterior_target": field("DEFINED_CONDITIONALLY_REQUIRES_NEW_FAMILY_LAW", "p(theta_new|D) under a validated new-family generator law."),
            "training_objective": field("CONCEPTUALLY_DEFINED", "A proper amortized posterior objective for fixed-N sets."),
            "calibration_coverage_target": field("CONCEPTUALLY_DEFINED_REQUIRES_NEW_FAMILY_LAW", "SBC and coverage across the new domain."),
            "original_objective_compatibility": field("CHANGES_ACTIVE_PDF_FAMILY", "Preserves posterior form but changes the active scientific family."),
            "preserved_evidence": base_preserved() + ["D0R remains immutable historical evidence."],
            "prospectively_superseded_evidence": ["ADR-001 active family", "ADR-004 active D0R identity", "current D0R active-family contract"],
            "issue_roadmap_implications": field("REQUIRES_NEW_ROADMAP", "Issue #10 cannot resume under its current D0R contract."),
            "smallest_falsifiable_next_step": field("BOUNDED_PLANNING_REVIEW", "Review motivation, family, theta, positivity, sum rules, and support without implementation."),
            "burden_estimate": field("IMPLEMENTATION_AND_VALIDATION_NOT_BOUNDED", "The contract review is bounded; later implementation is not."),
            "relationship_to_current_line": "SEPARATE_PROSPECTIVE_CONTRACT",
            "scientific_motivation": field("PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE", "NLO nonnegativity may be software-driven rather than scientifically justified."),
            "implementation_ready_claimed": False,
            "hidden_clipping_or_semantic_repair": False,
            "signed_weights_are_probabilities": False,
        },
        OPTION_IDS[2]: {
            "latent_parameter_theta": field("DEFINED", "Retain D0R theta unless a later review explicitly changes it."),
            "active_pdf_family_identity": field("DEFINED", "Retain D0R as scientific input."),
            "simulator_or_data_generating_law": field("CONCEPTUAL_FORM_ONLY", "z~p_theta(z), y~K(y|z), D={y_i}; exact hard-event and detector laws remain proof obligations."),
            "normalized_probability_measure": field("CONCEPTUALLY_COHERENT_REQUIRES_FORMAL_HARD_EVENT_CONTRACT", "p_theta(z)=1_A(z)(d sigma_theta/dz)/integral_A(d sigma_theta/dz dz), subject to every listed proof obligation."),
            "observed_event_set_representation": field("DEFINED", "Unordered fixed-N detector-level hard-event observables; hard flavor and PDF values remain provenance."),
            "event_and_set_weights": field("DEFINED_UNWEIGHTED_PRIMARY", "Primary draws are unweighted under the future normalized law; integration weights remain provenance."),
            "sample_size_semantics": field("DEFINED_FIXED_N", "Exchangeable fixed-N sampling conditioned on acceptance."),
            "rate_shape_semantics": field("DEFINED_SHAPE_ONLY", "Normalized shape likelihood; total rate remains diagnostic."),
            "detector_response_contract": field("CONCEPTUALLY_DEFINED_REQUIRES_NORMALIZATION_PROOF", "K(y|z) must be normalized; identity K is an explicit perfect-detector special case."),
            "support_extrapolation_rules": field("DEFINED_STRICT", "Analytic phase-space/PDF support intersection; no extrapolation."),
            "positivity_signed_value_rules": field("COMPLETE_RATE_POSITIVITY_NOT_EVALUATED", "Only the complete differential rate may define probabilities; signed components may cancel before it."),
            "posterior_target": field("CONCEPTUALLY_COHERENT_REQUIRES_FORMAL_LIKELIHOOD", "p(theta_D0R|D_hard) proportional to the prior times the fixed-N normalized detector-level likelihood."),
            "training_objective": field("CONCEPTUALLY_DEFINED", "A proper posterior or likelihood-ratio objective using only draws from the future law."),
            "calibration_coverage_target": field("CONCEPTUALLY_DEFINED_REQUIRES_EXECUTABLE_CLOSURE", "SBC, conditional coverage, and independent quadrature closure require future executable definitions."),
            "original_objective_compatibility": field("PRESERVED_WITH_SCOPED_OBSERVATION", "Preserves p(theta_PDF|D), with D explicitly lower-level rather than full-generator events."),
            "preserved_evidence": base_preserved() + ["ADR-001/ADR-004/D0R and initial fixed-N shape-only semantics may be preserved."],
            "prospectively_superseded_evidence": ["Would require prospective supersession of ADR-002, ADR-006, issue #10, and the current D2-D5 roadmap only if separately accepted."],
            "issue_roadmap_implications": field("SEPARATE_SCOPE_NOT_ISSUE_10_COMPLETION", "A later accepted contract would supersede, not complete, issue #10."),
            "smallest_falsifiable_next_step": field("BOUNDED_PLANNING_REVIEW", "Formalize formulae, support, positivity, normalization, detector kernel, omissions, and closure gates without implementation."),
            "burden_estimate": field("PLANNING_BOUNDED_IMPLEMENTATION_NOT_AUTHORIZED", "The mathematical contract review is bounded; implementation remains unestimated and unauthorized."),
            "relationship_to_current_line": "SEPARATE_PROSPECTIVE_CONTRACT",
            "scientific_motivation": field("PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE", "The lower-level form is plausible, but independent evidence does not establish it as the unique next scientific priority."),
            "implementation_ready_claimed": False,
            "hidden_clipping_or_semantic_repair": False,
            "signed_weights_are_probabilities": False,
            "mathematical_form": {
                "latent_event": "z ~ p_theta(z)",
                "observed_event": "y ~ K(y | z)",
                "dataset": "D = {y_i}_{i=1}^N",
                "normalized_density": "p_theta(z) = 1_A(z) d_sigma_theta/dz / integral_A d_sigma_theta/dz dz",
            },
            "proof_obligations": [
                {"obligation_id": obligation, "status": "NOT_EVALUATED"}
                for obligation in LOWER_LEVEL_PROOF_OBLIGATIONS
            ],
            "omitted_physics": ["ISR", "parton_showering", "hadronization", "underlying_event", "beam_remnants"],
            "full_generator_equivalence_claimed": False,
            "complete_rate_positivity_proven": False,
            "detector_kernel_normalization_proven": False,
            "conceptual_reviewability": "INCOMPLETE_BUT_REVIEWABLE",
            "candidate_status": "PLAUSIBLE_SEPARATE_REVIEW_CANDIDATE_REQUIRES_INDEPENDENT_EVIDENCE",
        },
        OPTION_IDS[3]: {
            "latent_parameter_theta": field("REQUIRES_NEW_DECISION", "May retain D0R only after defining the empirical-measure law."),
            "active_pdf_family_identity": field("NOT_EVALUATED", "Producer family and weights are not fixed."),
            "simulator_or_data_generating_law": field("CONCEPTUALLY_DEFINED_REQUIRES_STATISTICAL_CONTRACT", "A random positive weighted empirical measure needs a proposal and weight functional."),
            "normalized_probability_measure": field("CONCEPTUALLY_COHERENT_FOR_POSITIVE_WEIGHTS_REQUIRES_STATISTICAL_CONTRACT", "Positive normalized weights may define an empirical measure; signed weights do not."),
            "observed_event_set_representation": field("DEFINED_WEIGHTED_NOT_IID_UNWEIGHTED", "A set of event, weight, and provenance tuples."),
            "event_and_set_weights": field("DEFINED_POSITIVE_ONLY_SIGNED_EXCLUDED", "Positive weights remain explicit; signed cases are outside this option."),
            "sample_size_semantics": field("DEFINED_WITH_ESS_QUALIFICATION", "Candidate count and ESS are distinct."),
            "rate_shape_semantics": field("NOT_EVALUATED", "Rate-aware meaning requires producer normalization."),
            "detector_response_contract": field("NOT_EVALUATED", "Response ordering and weight semantics remain undefined."),
            "support_extrapolation_rules": field("DEFINED_STRICT", "Strict proposal/target support; no pool reuse."),
            "positivity_signed_value_rules": field("DEFINED_NO_REPAIR", "No clipping, absolute values, or weights=1 reset."),
            "posterior_target": field("CONCEPTUALLY_COHERENT_REQUIRES_WEIGHTED_EMPIRICAL_LAW", "A hierarchical posterior must include proposal randomness and weights."),
            "training_objective": field("NOT_EVALUATED", "No proper weighted set objective is selected."),
            "calibration_coverage_target": field("NOT_EVALUATED", "Coverage must repeat proposal sampling and empirical-measure construction."),
            "original_objective_compatibility": field("CHANGES_PRIMARY_DATA_OBJECT", "Replaces ordinary fixed-N sets with empirical measures."),
            "preserved_evidence": base_preserved(),
            "prospectively_superseded_evidence": ["ADR-003 fixed-N unweighted primary objective"],
            "issue_roadmap_implications": field("REQUIRES_NEW_ROADMAP", "Issue #10 remains incomplete and blocked."),
            "smallest_falsifiable_next_step": field("BOUNDED_PLANNING_REVIEW", "Specify proposal, weights, normalization, ESS, posterior, loss, and coverage."),
            "burden_estimate": field("END_TO_END_PATH_NOT_BOUNDED", "The mathematical review is bounded; producer and MVP are unresolved."),
            "relationship_to_current_line": "SEPARATE_PROSPECTIVE_CONTRACT",
            "scientific_motivation": field("PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE", "No evidence yet favors changing the primary data object."),
            "implementation_ready_claimed": False,
            "hidden_clipping_or_semantic_repair": False,
            "signed_weights_are_probabilities": False,
        },
        OPTION_IDS[4]: {
            "latent_parameter_theta": field("NOT_EVALUATED", "Could reference D0R only after defining a valid signed-data law."),
            "active_pdf_family_identity": field("NOT_EVALUATED", "No signed-weight inference family is selected."),
            "simulator_or_data_generating_law": field("NOT_SUPPORTED", "A finite signed sample is an estimator, not a probability law."),
            "normalized_probability_measure": field("NO_NORMALIZED_POSITIVE_DATA_LAW", "No positive normalized law has been constructed."),
            "observed_event_set_representation": field("NOT_EVALUATED", "A cancellation-aware representation is unresolved."),
            "event_and_set_weights": field("SIGNED_ESTIMATOR_NOT_PROBABILITY", "Signed complete-event weights remain estimators, never probabilities."),
            "sample_size_semantics": field("NOT_EVALUATED", "N and signed ESS do not define iid sample size."),
            "rate_shape_semantics": field("NOT_EVALUATED", "Signed normalization obstructs ordinary rate/shape semantics."),
            "detector_response_contract": field("NOT_EVALUATED", "No positive observation law exists."),
            "support_extrapolation_rules": field("DEFINED_STRICT", "No extrapolation or sign repair."),
            "positivity_signed_value_rules": field("SIGNED_ESTIMATOR_ONLY", "Negative weights are preserved but not interpreted as probability."),
            "posterior_target": field("NOT_SUPPORTED_WITHOUT_POSITIVE_DATA_LAW", "No coherent posterior target exists."),
            "training_objective": field("NOT_SUPPORTED", "No proper loss exists for the undefined posterior."),
            "calibration_coverage_target": field("NOT_SUPPORTED", "Coverage is undefined without repeated draws from a positive law."),
            "original_objective_compatibility": field("NOT_SUPPORTED", "Would replace conditioning on sampled data with a signed estimator."),
            "preserved_evidence": base_preserved(),
            "prospectively_superseded_evidence": ["ADR-003 only if future mathematics establishes a new contract"],
            "issue_roadmap_implications": field("RESEARCH_ONLY", "Issue #10 and D2 remain blocked."),
            "smallest_falsifiable_next_step": field("OPEN_ENDED_RESEARCH", "Construct a positive law, proper loss, and coverage semantics."),
            "burden_estimate": field("OPEN_ENDED", "Posterior, cancellation, and calibration theory are unbounded."),
            "relationship_to_current_line": "SEPARATE_PROSPECTIVE_CONTRACT",
            "scientific_motivation": field("PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE", "Negative event weights alone do not motivate a signed inference law."),
            "implementation_ready_claimed": False,
            "hidden_clipping_or_semantic_repair": False,
            "signed_weights_are_probabilities": False,
        },
        OPTION_IDS[5]: {
            "latent_parameter_theta": field("PRESERVED_HISTORICALLY", "D0R theta remains evidence."),
            "active_pdf_family_identity": field("PRESERVED_HISTORICALLY", "D0R remains accepted at its validated scope."),
            "simulator_or_data_generating_law": field("PROSPECTIVE_SCOPED_TERMINATION_OPTION", "Termination remains one reviewed option, not the active state."),
            "normalized_probability_measure": field("NOT_APPLICABLE", "Termination defines no new law."),
            "observed_event_set_representation": field("NOT_APPLICABLE", "Termination defines no dataset."),
            "event_and_set_weights": field("NOT_APPLICABLE", "Termination defines no weights."),
            "sample_size_semantics": field("NOT_APPLICABLE", "Termination defines no sampling."),
            "rate_shape_semantics": field("NOT_APPLICABLE", "Termination defines no likelihood."),
            "detector_response_contract": field("NOT_APPLICABLE", "Termination defines no response."),
            "support_extrapolation_rules": field("PRESERVED_HISTORICALLY", "Strict support remains historical."),
            "positivity_signed_value_rules": field("PRESERVED_HISTORICALLY", "No sign repair is introduced."),
            "posterior_target": field("NOT_APPLICABLE", "Termination defines no posterior implementation."),
            "training_objective": field("NOT_APPLICABLE", "Termination defines no training."),
            "calibration_coverage_target": field("NOT_APPLICABLE", "Termination defines no calibration."),
            "original_objective_compatibility": field("SCOPED_LINE_TERMINATION", "Terminates only the current full-generator path, not PDF SBI."),
            "preserved_evidence": base_preserved(),
            "prospectively_superseded_evidence": ["No active supersession; termination would require a separately supported decision."],
            "issue_roadmap_implications": field("NO_ACTIVE_TERMINATION", "Issue #10 and the current roadmap retain their existing states."),
            "smallest_falsifiable_next_step": field("NOT_APPLICABLE", "A scoped resource disposition, not an experiment."),
            "burden_estimate": field("LOW", "Documentation and roadmap disposition only."),
            "relationship_to_current_line": "CURRENT_LINE_DISPOSITION",
            "scientific_motivation": field("SUPPORTED", "Stops an unbounded implementation line without rejecting its objective."),
            "implementation_ready_claimed": False,
            "hidden_clipping_or_semantic_repair": False,
            "signed_weights_are_probabilities": False,
            "global_sbi_impossibility_claimed": False,
        },
    }
    return options


V2_SCORE_CODES = {
    OPTION_IDS[0]: ("Q","Q","S","S","Q","S","S","U","S","S","Q","N","N","N","Q","N","Q","N","S","Q"),
    OPTION_IDS[1]: ("Q","Q","S","Q","Q","S","S","U","S","S","Q","Q","U","U","Q","N","Q","U","N","Q"),
    OPTION_IDS[2]: ("Q","Q","S","Q","S","S","S","Q","S","S","Q","S","Q","Q","Q","Q","Q","Q","Q","S"),
    OPTION_IDS[3]: ("Q","Q","Q","Q","Q","S","S","U","Q","Q","U","Q","U","U","Q","Q","Q","U","N","Q"),
    OPTION_IDS[4]: ("N","N","U","U","U","S","S","U","Q","U","N","Q","N","N","Q","N","Q","N","N","Q"),
    OPTION_IDS[5]: ("A","A","A","A","A","S","S","A","A","A","A","S","S","S","S","S","A","A","S","Q"),
}
CODE_STATUS = {
    "S": "SUPPORTED",
    "Q": "SUPPORTED_WITH_QUALIFICATION",
    "N": "NOT_SUPPORTED",
    "U": "PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE",
    "A": "NOT_APPLICABLE",
}

CRITERION_RATIONALE = {
    "normalized_generative_measure": "The status follows the option's explicit normalized-law state and unresolved proof obligations.",
    "posterior_target_coherence": "The status follows whether conditioning is defined against the same normalized observation law.",
    "set_level_amortized_sbi_compatibility": "The status follows whether the declared object is an exchangeable set or an explicitly different empirical measure.",
    "pdf_interpretability": "The status follows preservation or explicit prospective change of the active PDF-family identity.",
    "qcd_factorization_compatibility": "The status reflects whether PDF dependence is scoped to a factorized hard law rather than inferred from software interfaces.",
    "strict_support_preservation": "The status follows the declared support intersection and fail-closed extrapolation policy.",
    "no_clipping_preservation": "The status follows the explicit prohibition on clipping, absolute values, and weights=1 repair.",
    "detector_model_feasibility": "The status reflects whether a normalized detector/acceptance kernel is defined or remains a future obligation.",
    "event_weight_clarity": "The status distinguishes unweighted draws, positive empirical weights, and signed estimators.",
    "rate_shape_clarity": "The status follows the declared fixed-N shape-only or alternative rate contract.",
    "calibration_feasibility": "The status reflects whether repeated draws, SBC, coverage, and failure accounting are coherently defined.",
    "independent_falsifiability": "The status follows the existence of a bounded review with independently checkable failure conditions.",
    "implementation_boundedness": "The status concerns later implementation scope, not the boundedness of this planning review.",
    "validation_boundedness": "The status reflects whether future numerical and statistical gates are sufficiently specified to bound validation.",
    "reproducibility": "The status follows identity, provenance, support, and deterministic-contract requirements.",
    "maintenance_burden": "The status reflects ongoing generator, family, or mathematical maintenance rather than one-time review cost.",
    "existing_rust_cpp_infrastructure_compatibility": "The status reflects reuse of set interfaces and scientific boundaries without assuming unavailable generator plumbing.",
    "end_to_end_scientific_mvp_path": "The status follows whether measure, posterior, representation, and validation can plausibly compose after a bounded contract review.",
    "scientific_objective_change_risk": "The status reflects whether changes to family, observation law, or inference target are explicit and scientifically justified.",
    "evidence_value_on_failure": "The status reflects whether a negative review would resolve a concrete scientific contract question.",
}

OPTION_SCOPE = {
    OPTION_IDS[0]: "The current contract is coherent in concept but has no accepted simulator or bounded continuation.",
    OPTION_IDS[1]: "A new nonnegative family is explicit, but its scientific motivation and end-to-end bounds are unavailable.",
    OPTION_IDS[2]: "The lower-level form is plausible and scoped, while exact formulae, positivity, normalization, detector response, and closure remain future gates.",
    OPTION_IDS[3]: "A positive empirical measure is conceptually possible, but producer, loss, calibration, and MVP semantics remain unresolved.",
    OPTION_IDS[4]: "A signed finite sample remains an estimator without a positive data law or coherent posterior.",
    OPTION_IDS[5]: "Scoped termination proposes no new data law and preserves all historical evidence.",
}

AUDIT_CLASS_CODES = {
    OPTION_IDS[0]: ("Q","Q","D","D","M","D","D","M","D","D","Q","D","D","Q","M","M","M","M","D","U"),
    OPTION_IDS[1]: ("M","M","Q","M","M","Q","Q","M","Q","Q","Q","M","M","M","M","M","M","M","Q","U"),
    OPTION_IDS[2]: ("M","Q","D","Q","O","D","D","U","Q","D","Q","M","M","M","M","M","M","U","Q","U"),
    OPTION_IDS[3]: ("M","M","Q","M","M","Q","Q","M","D","M","Q","M","M","M","M","M","M","M","M","U"),
    OPTION_IDS[4]: ("D","M","Q","M","Q","Q","Q","M","Q","M","Q","M","M","M","M","M","M","M","Q","U"),
    OPTION_IDS[5]: ("A","A","A","A","A","D","D","A","A","A","A","Q","M","M","M","Q","A","A","Q","U"),
}
AUDIT_CLASS = {
    "D": "DIRECTLY_SUPPORTED",
    "Q": "SUPPORTED_WITH_QUALIFICATION",
    "O": "OVERSTATED",
    "M": "MISBOUND",
    "U": "UNSUPPORTED",
    "A": "NOT_APPLICABLE",
}

SCORE_SOURCE = {
    "normalized_generative_measure": ("D1D_FINAL_RECORD", "ACCEPTED_GENERATOR_ARCHITECTURE_ABSENT"),
    "posterior_target_coherence": ("ADR003_EVENT_SEMANTICS", "FIXED_N_SHAPE_ONLY_SET_OBJECTIVE"),
    "set_level_amortized_sbi_compatibility": ("ADR003_EVENT_SEMANTICS", "FIXED_N_SHAPE_ONLY_SET_OBJECTIVE"),
    "pdf_interpretability": ("ADR001_D0R_FAMILY", "D0R_THETA_AND_PDF_INTERPRETABILITY"),
    "qcd_factorization_compatibility": ("ADR004_D0R_SIGN_TOPOLOGY", "D0R_SIGNED_NLO_VALUES"),
    "strict_support_preservation": ("ADR001_D0R_FAMILY", "STRICT_SUPPORT_AND_NO_CLIPPING"),
    "no_clipping_preservation": ("ADR001_D0R_FAMILY", "STRICT_SUPPORT_AND_NO_CLIPPING"),
    "event_weight_clarity": ("ADR003_EVENT_SEMANTICS", "WEIGHTED_SETS_ARE_NOT_IID_UNWEIGHTED"),
    "rate_shape_clarity": ("ADR003_EVENT_SEMANTICS", "FIXED_N_SHAPE_ONLY_SET_OBJECTIVE"),
    "calibration_feasibility": ("ADR003_EVENT_SEMANTICS", "CALIBRATION_REQUIRED"),
    "independent_falsifiability": ("D1E_FINAL_RECORD", "CURRENT_STATIC_SCOPE_NOT_CREDIBLY_BOUNDED"),
    "implementation_boundedness": ("D1E_FINAL_RECORD", "IMPLEMENTATION_COST_BOUND_NOT_SUPPORTED"),
    "validation_boundedness": ("D1E_FINAL_RECORD", "IMPLEMENTATION_COST_BOUND_NOT_SUPPORTED"),
    "maintenance_burden": ("D1D_FINAL_RECORD", "ALTERNATIVE_GENERATOR_ROUTES_POSSIBLE_WITH_EVIDENCE_GAPS"),
    "scientific_objective_change_risk": ("ADR001_D0R_FAMILY", "D0R_THETA_AND_PDF_INTERPRETABILITY"),
}


def corrected_score_status(v2_code: str, audit_code: str) -> str:
    if audit_code == "A":
        return "NOT_APPLICABLE"
    if audit_code in {"M", "O", "U"}:
        return "PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE"
    status = CODE_STATUS[v2_code]
    if audit_code == "Q" and status == "SUPPORTED":
        return "SUPPORTED_WITH_QUALIFICATION"
    return status


def build_scorecards(repository_evidence: dict[str, dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    cards: dict[str, dict[str, dict[str, Any]]] = {}
    for option_id in OPTION_IDS:
        cards[option_id] = {}
        for criterion, v2_code, audit_code in zip(CRITERIA, V2_SCORE_CODES[option_id], AUDIT_CLASS_CODES[option_id], strict=True):
            status = corrected_score_status(v2_code, audit_code)
            audit_class = AUDIT_CLASS[audit_code]
            if audit_code == "D":
                evidence_class = "DIRECT_IMMUTABLE_EVIDENCE"
            elif audit_code == "Q":
                evidence_class = "EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE"
            elif audit_code == "A":
                evidence_class = "NOT_APPLICABLE"
            else:
                evidence_class = "PROSPECTIVE_HYPOTHESIS"
            bindings: list[dict[str, Any]] = []
            if evidence_class in {"DIRECT_IMMUTABLE_EVIDENCE", "EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE"}:
                evidence_id, claim_key = SCORE_SOURCE[criterion]
                claim = repository_evidence[evidence_id]["claims"][claim_key]
                bindings.append({
                    "evidence_id": evidence_id,
                    "claim_key": claim_key,
                    "option_scope": [option_id],
                    "criterion_scope": [criterion],
                    "maximum_supported_status": claim["maximum_supported_status"],
                })
            explicit_inference = None
            if evidence_class == "EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE":
                explicit_inference = {
                    "premises": [f"{row['evidence_id']}:{row['claim_key']}" for row in bindings],
                    "inference": f"The immutable premise supports only the stated qualified conclusion for {option_id}/{criterion}.",
                }
            cards[option_id][criterion] = {
                "option_id": option_id,
                "criterion_id": criterion,
                "status": status,
                "criterion_specific_rationale": f"{CRITERION_RATIONALE[criterion]} {OPTION_SCOPE[option_id]} Audit correction: {audit_class}.",
                "evidence_class": evidence_class,
                "evidence_bindings": bindings,
                "explicit_inference": explicit_inference,
                "implication_for_current_line": "This score cannot reopen or authorize the paused current full-generator line.",
                "implication_for_separate_review": "A hypothesis may motivate future evidence collection but cannot establish unique preference." if evidence_class == "PROSPECTIVE_HYPOTHESIS" else "The cell contributes only within its exact option and criterion scope.",
                "load_bearing": bool(option_id in REDESIGN_OPTIONS and criterion in PREFERENCE_CRITICAL_CRITERIA and evidence_class in {"DIRECT_IMMUTABLE_EVIDENCE", "EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE"}),
                "historical_correction_classification": audit_class,
            }
    return cards


def build_supersession() -> dict[str, Any]:
    historical = {
        key: "PRESERVED_AS_HISTORICAL_EVIDENCE"
        for key in ("D0R_NEGATIVE_AND_POSITIVE_EVIDENCE", "D1_RESULT", "D1R_RESULT", "D1C_RESULT", "D1D_RESULT", "D1E_RESULT")
    }
    redesign = {
        OPTION_IDS[1]: {
            "ADR-001": "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED",
            "ADR-004": "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED",
            "D0R": "PRESERVED_AS_HISTORICAL_EVIDENCE",
            "ISSUE_10": "WOULD_REQUIRE_NEW_DECISION_IF_SEPARATELY_ACCEPTED",
            "NEURAL_PHASE": "WOULD_REQUIRE_NEW_DECISION_IF_SEPARATELY_ACCEPTED",
        },
        OPTION_IDS[2]: {
            "ADR-001": "PRESERVED",
            "ADR-004": "PRESERVED",
            "D0R": "PRESERVED",
            "ADR-003_FIXED_N_SHAPE_ONLY": "WOULD_REQUIRE_EXPLICIT_CONFIRMATION_IF_SEPARATELY_ACCEPTED",
            "ADR-002": "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED",
            "ADR-006": "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED",
            "ISSUE_10": "NOT_COMPLETED_BY_LOWER_LEVEL_MODEL",
            "NEURAL_PHASE": "WOULD_REQUIRE_NEW_DECISION_IF_SEPARATELY_ACCEPTED",
        },
        OPTION_IDS[3]: {
            "ADR-003_FIXED_N_SHAPE_ONLY": "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED",
            "ISSUE_10": "WOULD_REQUIRE_NEW_DECISION_IF_SEPARATELY_ACCEPTED",
            "NEURAL_PHASE": "WOULD_REQUIRE_NEW_DECISION_IF_SEPARATELY_ACCEPTED",
        },
        OPTION_IDS[4]: {
            "ADR-003_FIXED_N_SHAPE_ONLY": "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED",
            "ISSUE_10": "WOULD_REQUIRE_NEW_DECISION_IF_SEPARATELY_ACCEPTED",
            "NEURAL_PHASE": "WOULD_REQUIRE_NEW_DECISION_IF_SEPARATELY_ACCEPTED",
        },
    }
    return {
        "historical_negative_results": historical,
        "current_line_active_effects": {
            "ISSUE_10_FULL_GENERATOR_D2": "CURRENT_STATE_PRESERVED",
            "CURRENT_FULL_GENERATOR_D2_D5_ROADMAP": "CURRENT_STATE_PRESERVED",
        },
        "redesign_option_effects": redesign,
        "lower_level_candidate_hypothetical_effects": copy.deepcopy(redesign[OPTION_IDS[2]]),
    }


def build_current_line_evidence(options: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {
        "full_generator_architecture_ready": {
            "proposition_status": "NOT_SUPPORTED",
            "evidence_class": "DIRECT_IMMUTABLE_EVIDENCE",
            "evidence_ids": ["D1D_FINAL_RECORD"],
            "claim_keys": ["FULL_GENERATOR_ARCHITECTURE_NOT_READY"],
            "premises": ["D1D-A failed its evidence-integrity gate and architecture-comparison readiness remains false."],
            "inference": None,
            "rationale": "The immutable D1D record directly rejects readiness of the current full-generator architecture.",
        },
        "bounded_static_evidence_path_exists": {
            "proposition_status": "NOT_SUPPORTED",
            "evidence_class": "DIRECT_IMMUTABLE_EVIDENCE",
            "evidence_ids": ["D1E_FINAL_RECORD"],
            "claim_keys": ["CURRENT_STATIC_SCOPE_NOT_CREDIBLY_BOUNDED"],
            "premises": ["D1E records the current AST/consumer-graph implementation scope as not credibly bounded."],
            "inference": None,
            "rationale": "The immutable D1E assessment directly rejects a bounded current static-evidence task.",
        },
        "bounded_signed_kernel_path_exists": {
            "proposition_status": "NOT_SUPPORTED",
            "evidence_class": "DIRECT_IMMUTABLE_EVIDENCE",
            "evidence_ids": ["D1D_FINAL_RECORD"],
            "claim_keys": ["SIGNED_KERNEL_PATH_NOT_BOUNDED"],
            "premises": ["D1D finds no reviewed signed-kernel or signed-Sudakov construction for the current contract."],
            "inference": None,
            "rationale": "The immutable D1D review directly finds no bounded signed-kernel route in the reviewed scope.",
        },
        "bounded_alternative_generator_path_exists": {
            "proposition_status": "NOT_EVALUATED",
            "evidence_class": "NOT_EVALUATED",
            "evidence_ids": ["D1D_FINAL_RECORD"],
            "claim_keys": ["ALTERNATIVE_GENERATOR_ROUTES_POSSIBLE_WITH_EVIDENCE_GAPS"],
            "premises": ["D1D leaves Architecture C, Sherpa, and Herwig possible with evidence gaps."],
            "inference": "The source neither establishes a bounded path nor establishes the affirmative negative that no bounded path exists.",
            "rationale": "The proposition remains unevaluated rather than being converted from missing evidence into incompatibility.",
        },
        "accepted_generator_measure_exists": {
            "proposition_status": "NOT_SUPPORTED",
            "evidence_class": "EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE",
            "evidence_ids": ["D1D_FINAL_RECORD"],
            "claim_keys": ["ACCEPTED_GENERATOR_ARCHITECTURE_ABSENT", "SIGNED_INTERNAL_RATE_CONSTRUCTION_ABSENT", "COMPLETED_GENERATOR_MEASURE_ABSENT"],
            "premises": ["No accepted generator architecture exists.", "No reviewed signed internal-rate construction exists.", "No completed normalized generator measure exists."],
            "inference": "Together these immutable premises imply that no accepted generator measure is currently available; the exact proposition is not claimed to appear verbatim in D1D.",
            "rationale": "This is an explicit bounded inference, not a direct quotation from D1D.",
        },
        "accepted_runtime_consumer_closure_exists": {
            "proposition_status": "NOT_SUPPORTED",
            "evidence_class": "DIRECT_IMMUTABLE_EVIDENCE",
            "evidence_ids": ["D1D_FINAL_RECORD"],
            "claim_keys": ["RUNTIME_CONSUMER_CLOSURE_NOT_VALIDATED"],
            "premises": ["D1D records that a complete consumer/dataflow graph was not validated."],
            "inference": None,
            "rationale": "No accepted runtime-consumer closure exists in the immutable evidence.",
        },
        "implementation_task_credibly_bounded": {
            "proposition_status": "NOT_SUPPORTED",
            "evidence_class": "DIRECT_IMMUTABLE_EVIDENCE",
            "evidence_ids": ["D1E_FINAL_RECORD"],
            "claim_keys": ["IMPLEMENTATION_COST_BOUND_NOT_SUPPORTED"],
            "premises": ["D1E rejects the implementation cost bound for the current consumer-graph task."],
            "inference": None,
            "rationale": "The immutable D1E assessment directly rejects a credibly bounded current implementation task.",
        },
        "current_contract_preserved_by_continuation": {
            "proposition_status": "NOT_EVALUATED",
            "evidence_class": "NOT_EVALUATED",
            "evidence_ids": ["D1D_FINAL_RECORD"],
            "claim_keys": ["ALTERNATIVE_GENERATOR_ROUTES_POSSIBLE_WITH_EVIDENCE_GAPS"],
            "premises": ["D1D retains potentially coherent routes with evidence gaps under the fixed reviewed contract."],
            "inference": "No immutable source establishes that every continuation necessarily fails to preserve the current contract.",
            "rationale": "Contract preservation by continuation remains unevaluated.",
        },
    }
    separate = all(options[option]["relationship_to_current_line"] == "SEPARATE_PROSPECTIVE_CONTRACT" for option in REDESIGN_OPTIONS)
    evidence["redesigns_are_separate_contracts"] = {
        "proposition_status": "SUPPORTED" if separate else "NOT_SUPPORTED",
        "evidence_class": "EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE",
        "evidence_ids": ["ADR001_D0R_FAMILY", "ADR003_EVENT_SEMANTICS", "ADR004_D0R_SIGN_TOPOLOGY"],
        "claim_keys": ["D0R_THETA_AND_PDF_INTERPRETABILITY", "FIXED_N_SHAPE_ONLY_SET_OBJECTIVE", "D0R_HISTORICAL_IDENTITY"],
        "premises": ["Every redesign relationship_to_current_line is SEPARATE_PROSPECTIVE_CONTRACT.", "Every redesign records hypothetical prospective supersession rather than current-line continuation.", "The immutable D0R and fixed-N contracts remain the comparison baseline."],
        "inference": "The serialized redesign definitions are separate prospective contracts; ADR-010 records but does not independently prove this inference.",
        "rationale": "The separation conclusion follows from non-ADR-010 premises and exact option definitions.",
    }
    return evidence


def derive_normalized_measure_gates(options: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    measure_rules = {
        "CONCEPTUALLY_DEFINED_NOT_OPERATIONALLY_INSTANTIATED": "PASS_WITH_QUALIFICATION",
        "CONCEPTUALLY_COHERENT_REQUIRES_NEW_FAMILY_PROOFS": "PASS_WITH_QUALIFICATION",
        "CONCEPTUALLY_COHERENT_REQUIRES_FORMAL_HARD_EVENT_CONTRACT": "PASS_WITH_QUALIFICATION",
        "CONCEPTUALLY_COHERENT_FOR_POSITIVE_WEIGHTS_REQUIRES_STATISTICAL_CONTRACT": "PASS_WITH_QUALIFICATION",
        "NO_NORMALIZED_POSITIVE_DATA_LAW": "FAIL",
        "NOT_APPLICABLE": "NOT_APPLICABLE",
    }
    posterior_accepted = {
        "CONCEPTUALLY_DEFINED_NOT_OPERATIONALLY_INSTANTIATED",
        "DEFINED_CONDITIONALLY_REQUIRES_NEW_FAMILY_LAW",
        "CONCEPTUALLY_COHERENT_REQUIRES_FORMAL_LIKELIHOOD",
        "CONCEPTUALLY_COHERENT_REQUIRES_WEIGHTED_EMPIRICAL_LAW",
        "NOT_APPLICABLE",
    }
    representation_accepted = {"DEFINED", "DEFINED_WEIGHTED_NOT_IID_UNWEIGHTED", "NOT_APPLICABLE"}
    weight_accepted = {"DEFINED_UNWEIGHTED_PRIMARY", "DEFINED_POSITIVE_ONLY_SIGNED_EXCLUDED", "NOT_APPLICABLE"}
    calibration_accepted = {
        "CONCEPTUALLY_DEFINED_NOT_OPERATIONALLY_INSTANTIATED",
        "CONCEPTUALLY_DEFINED_REQUIRES_NEW_FAMILY_LAW",
        "CONCEPTUALLY_DEFINED_REQUIRES_EXECUTABLE_CLOSURE",
        "NOT_EVALUATED",
        "NOT_APPLICABLE",
    }
    gates: dict[str, dict[str, Any]] = {}
    for option_id, option in options.items():
        measure = option["normalized_probability_measure"]["status"]
        require(measure in measure_rules, f"unsupported normalized-measure semantic status for {option_id}")
        status = measure_rules[measure]
        posterior = option["posterior_target"]["status"]
        representation = option["observed_event_set_representation"]["status"]
        weights = option["event_and_set_weights"]["status"]
        calibration = option["calibration_coverage_target"]["status"]
        if posterior not in posterior_accepted or representation not in representation_accepted or weights not in weight_accepted or calibration not in calibration_accepted:
            status = "FAIL"
        if option["hidden_clipping_or_semantic_repair"] or option["signed_weights_are_probabilities"]:
            status = "FAIL"
        if option_id == OPTION_IDS[2]:
            obligations = option.get("proof_obligations", [])
            require({row["obligation_id"] for row in obligations} == set(LOWER_LEVEL_PROOF_OBLIGATIONS), "lower-level proof obligations are incomplete")
            require(all(row["status"] == "NOT_EVALUATED" for row in obligations), "D1F cannot claim a lower-level proof obligation is discharged")
            require(option["complete_rate_positivity_proven"] is False, "complete-rate positivity is not proven in D1F")
            require(option["detector_kernel_normalization_proven"] is False, "detector-kernel normalization is not proven in D1F")
            require(status == "PASS_WITH_QUALIFICATION", "lower-level gate must remain qualified")
        gates[option_id] = {
            "status": status,
            "measure_semantic_status": measure,
            "posterior_semantic_status": posterior,
            "event_representation_semantic_status": representation,
            "weight_semantic_status": weights,
            "calibration_semantic_status": calibration,
        }
    return gates


def derive_score_status(cell: dict[str, Any], evidence: dict[str, dict[str, Any]]) -> str:
    require(cell["status"] in SCORE_STATUSES, "invalid score status")
    require(cell["evidence_class"] in SCORE_EVIDENCE_CLASSES, "invalid score evidence class")
    bindings = cell["evidence_bindings"]
    if cell["evidence_class"] in {"PROSPECTIVE_HYPOTHESIS", "NOT_APPLICABLE"}:
        require(not bindings, "hypothesis or not-applicable cell cannot cite load-bearing evidence")
        require(cell["load_bearing"] is False, "hypothesis or not-applicable cell cannot be load-bearing")
        required_status = "NOT_APPLICABLE" if cell["evidence_class"] == "NOT_APPLICABLE" else "PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE"
        require(cell["status"] == required_status, "non-evidence cell overstates its status")
        return cell["status"]
    require(bindings, "evidence-backed score cell has no binding")
    for binding in bindings:
        evidence_id = binding["evidence_id"]
        claim_key = binding["claim_key"]
        require(evidence_id != "D1F_CONCEPTUAL_REVIEW", "ADR-010 cannot be independent score evidence")
        require(evidence_id in evidence, f"unknown score evidence ID: {evidence_id}")
        claims = evidence[evidence_id].get("claims", {})
        require(claim_key in claims, f"unknown score claim: {evidence_id}/{claim_key}")
        claim = claims[claim_key]
        require(binding["option_scope"] == [cell["option_id"]], "score evidence bound to wrong option")
        require(binding["criterion_scope"] == [cell["criterion_id"]], "score evidence bound to wrong criterion")
        require(cell["option_id"] in claim.get("option_scope", []), "source claim excludes score option")
        require(cell["criterion_id"] in claim.get("criterion_scope", []), "source claim excludes score criterion")
        require(binding["maximum_supported_status"] == claim["maximum_supported_status"], "maximum-supported status changed")
        rank = {"PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE": 0, "NOT_SUPPORTED": 0, "SUPPORTED_WITH_QUALIFICATION": 1, "SUPPORTED": 2, "NOT_APPLICABLE": 0}
        require(rank[cell["status"]] <= rank[claim["maximum_supported_status"]] or cell["status"] == "NOT_SUPPORTED", "maximum-supported status exceeded")
    if cell["evidence_class"] == "EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE":
        require(cell["explicit_inference"] and cell["explicit_inference"]["premises"], "explicit inference lacks premises")
    else:
        require(cell["explicit_inference"] is None, "direct evidence cell cannot hide an inference")
    return cell["status"]


def map_contract_status(value: str, mapping: dict[str, str], label: str) -> str:
    require(value in mapping, f"unsupported {label} semantic status: {value}")
    return mapping[value]


def derive_separate_review_eligibility(
    options: dict[str, dict[str, Any]],
    gates: dict[str, dict[str, Any]],
    scorecards: dict[str, dict[str, dict[str, Any]]],
    supersession: dict[str, Any],
    repository_evidence: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    provisional: dict[str, bool] = {}
    for option_id in REDESIGN_OPTIONS:
        option = options[option_id]
        cells = scorecards[option_id]
        for cell in cells.values():
            derive_score_status(cell, repository_evidence)
        effects = supersession["redesign_option_effects"].get(option_id, {})
        explicit_supersession = bool(effects) and any("WOULD_REQUIRE_" in value or value == "NOT_COMPLETED_BY_LOWER_LEVEL_MODEL" for value in effects.values())
        bounded_question = "SUPPORTED_WITH_QUALIFICATION" if option["smallest_falsifiable_next_step"]["status"] == "BOUNDED_PLANNING_REVIEW" and cells["independent_falsifiability"]["status"] in {"SUPPORTED", "SUPPORTED_WITH_QUALIFICATION"} else "PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE"
        independent = all(cells[key]["evidence_class"] in {"DIRECT_IMMUTABLE_EVIDENCE", "EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE"} for key in PREFERENCE_CRITICAL_CRITERIA)
        posterior = "SUPPORTED_WITH_QUALIFICATION" if option["posterior_target"]["status"] in {"DEFINED_CONDITIONALLY_REQUIRES_NEW_FAMILY_LAW", "CONCEPTUALLY_COHERENT_REQUIRES_FORMAL_LIKELIHOOD", "CONCEPTUALLY_COHERENT_REQUIRES_WEIGHTED_EMPIRICAL_LAW"} else "NOT_SUPPORTED"
        statuses = {
            "normalized_measure_reviewability": gates[option_id]["status"],
            "posterior_reviewability": posterior,
            "option_specific_scientific_motivation": option["scientific_motivation"]["status"],
            "bounded_planning_question": bounded_question,
            "independent_evidence_available": independent,
            "prospective_supersession_explicit": explicit_supersession,
            "no_hidden_repair": not option["hidden_clipping_or_semantic_repair"],
            "unique_preference_supported": False,
        }
        provisional[option_id] = gates[option_id]["status"] == "PASS_WITH_QUALIFICATION" and posterior in {"SUPPORTED", "SUPPORTED_WITH_QUALIFICATION"} and option["scientific_motivation"]["status"] in {"SUPPORTED", "SUPPORTED_WITH_QUALIFICATION"} and bounded_question in {"SUPPORTED", "SUPPORTED_WITH_QUALIFICATION"} and independent and explicit_supersession and statuses["no_hidden_repair"] and not option["implementation_ready_claimed"]
        result[option_id] = statuses
    candidates = [option_id for option_id, eligible in provisional.items() if eligible]
    for option_id in REDESIGN_OPTIONS:
        unique = provisional[option_id] and len(candidates) == 1
        result[option_id]["unique_preference_supported"] = unique
        result[option_id]["preferred_review_eligible"] = unique
        if option_id == OPTION_IDS[2]:
            result[option_id]["conceptual_reviewability"] = options[option_id]["conceptual_reviewability"]
            result[option_id]["candidate_status"] = options[option_id]["candidate_status"]
    return result


def derive_current_line_disposition(record: dict[str, Any]) -> str:
    evidence = record["current_line_evidence"]
    require(set(evidence) == set(CURRENT_EVIDENCE_FIELDS), "current-line evidence fields are incomplete")
    continuation_fields = CURRENT_EVIDENCE_FIELDS[:8]
    statuses = {key: evidence[key]["proposition_status"] for key in continuation_fields}
    path_fields = (
        "bounded_static_evidence_path_exists",
        "bounded_signed_kernel_path_exists",
        "bounded_alternative_generator_path_exists",
    )
    foundation_fields = (
        "full_generator_architecture_ready",
        "accepted_generator_measure_exists",
        "accepted_runtime_consumer_closure_exists",
        "implementation_task_credibly_bounded",
        "current_contract_preserved_by_continuation",
    )
    positive = {"SUPPORTED", "SUPPORTED_WITH_QUALIFICATION"}
    if all(statuses[key] in positive for key in foundation_fields) and any(
        statuses[key] in positive for key in path_fields
    ):
        return "CONTINUE_CURRENT_FULL_GENERATOR_LINE"
    if any(status == "NOT_EVALUATED" for status in statuses.values()):
        return "MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE"
    scope = record["termination_scope"]
    if (
        all(status == "NOT_SUPPORTED" for status in statuses.values())
        and evidence["redesigns_are_separate_contracts"]["proposition_status"] == "SUPPORTED"
        and scope["historical_negative_evidence_preserved"]
        and not scope["global_sbi_impossibility_claimed"]
        and all(evidence[key]["evidence_class"] in {"DIRECT_IMMUTABLE_EVIDENCE", "EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE"} for key in continuation_fields)
    ):
        return "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING"
    return "MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE"


def derive_preferred_review(record: dict[str, Any]) -> str:
    eligible = [option for option in REDESIGN_OPTIONS if record["separate_review_eligibility"][option]["preferred_review_eligible"]]
    require(len(eligible) <= 1, "evidence does not establish a unique preferred separate review")
    return eligible[0] if eligible else "NONE"


def derive_top_level_decision(current_line: str, preferred: str) -> str:
    del preferred
    if current_line == "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING":
        return "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING"
    if current_line == "MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE":
        return "MAINTAIN_CURRENT_CONTRACT_AND_PAUSE"
    raise ContractDecisionError("continuation has no authorizing D1F top-level outcome")


def score_totals(scorecards: dict[str, dict[str, dict[str, Any]]]) -> dict[str, dict[str, int]]:
    return {option: {status: sum(cell["status"] == status for cell in cells.values()) for status in sorted(SCORE_STATUSES)} for option, cells in scorecards.items()}


def build_record() -> dict[str, Any]:
    options = build_options()
    repository_evidence = build_repository_evidence()
    scorecards = build_scorecards(repository_evidence)
    supersession = build_supersession()
    gates = derive_normalized_measure_gates(options)
    current_evidence = build_current_line_evidence(options)
    record: dict[str, Any] = {
        "schema_version": SCHEMA,
        "decision": None,
        "current_line_disposition": None,
        "preferred_separate_contract_review": None,
        "precedence": build_precedence(),
        "repository_evidence": repository_evidence,
        "current_contract": {
            "theta": "theta=(delta_v, lambda_sea) on the accepted D0R domain",
            "pdf_family": "versioned sum-rule-projected D0R family",
            "pdf_value_semantics": "signed binary64 x*f; strict support; no clipping",
            "data_objective": "fixed-N shape-only unordered event sets",
            "posterior_objective": "p(theta_PDF | D)",
        },
        "fixed_contract_failure_summary": {
            "scope": "current D0R signed full-generator coupling line",
            "failure": "No accepted measure or runtime closure exists, and no bounded continuation has been established.",
            "not_a_failure_of": ["PDF SBI", "D0R evidence", "lower-level models", "future separately reviewed contracts"],
        },
        "options": options,
        "normalized_measure_gate": gates,
        "option_scorecards": scorecards,
        "supersession_matrix": supersession,
        "current_line_evidence": current_evidence,
        "termination_scope": {
            "historical_negative_evidence_preserved": True,
            "global_sbi_impossibility_claimed": False,
            "scope_statement": "Defines the evidence threshold for a hypothetical scoped termination; termination is not active in v3.",
        },
        "separate_review_eligibility": None,
        "decision_rule": {
            "current_line_axis": "Continue only with supported foundations and a supported bounded path; terminate only when every mandatory proposition is affirmatively NOT_SUPPORTED by direct evidence or reviewed inference; otherwise pause.",
            "separate_review_axis": "Prefer only a uniquely supported redesign with independent option-specific motivation, reviewability, and load-bearing evidence; hypotheses cannot select a preference.",
            "top_level_axis": "The top-level decision represents current-line disposition; a separate preference never converts redesign into continuation.",
        },
        "derived_decision_inputs": None,
        "scientific_scope": "Planning-only disposition of the failed current line and prioritization of separate contracts.",
        "failure_scope": "The current full-generator coupling line remains paused because bounded continuation and contract preservation are not fully evaluated.",
        "non_failure_scope": ["D0R evidence", "p(theta_PDF|D) generally", "lower-level hard-event contracts", "future reviewed family or inference changes"],
        "active_operational_policy": "PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION",
        "current_full_generator_line": "PAUSED_NO_BOUNDED_CONTINUATION_ESTABLISHED",
        "lower_level_contract_review": "PLAUSIBLE_BUT_NOT_PREFERRED_OR_AUTHORIZED",
        "lower_level_candidate_status": "PLAUSIBLE_SEPARATE_REVIEW_CANDIDATE_REQUIRES_INDEPENDENT_EVIDENCE",
        "authorization": {flag: False for flag in AUTHORIZATION_FLAGS},
        "dependencies": {
            "planning_issue": {"number": 47, "state": "OPEN", "authorization": "PLANNING_ONLY"},
            "issue_42": {"number": 42, "state": "CLOSED", "gate_decision": "INCONCLUSIVE"},
            "issue_45": {"number": 45, "state": "CLOSED", "gate_decision": "INCONCLUSIVE"},
            "issue_10": {"number": 10, "state": "OPEN_BLOCKED", "completed_by_lower_level_model": False, "authorization": "NOT_AUTHORIZED"},
            "D2": "BLOCKED_AND_UNAUTHORIZED",
            "roadmap": {"D2": "BLOCKED", "D3": "BACKLOG", "D4": "BACKLOG", "D5": "BACKLOG", "active_supersession": False},
        },
        "next_step": {
            "action": "INDEPENDENT_EVIDENCE_REVIEW_FOR_SEPARATE_CONTRACT_PRIORITY",
            "scope": "Planning-only review of independent motivation and load-bearing evidence; Option C obligations remain unevaluated.",
            "implementation": False,
            "authorization_granted": False,
        },
        "validation": None,
    }
    eligibility = derive_separate_review_eligibility(options, gates, scorecards, supersession, repository_evidence)
    record["separate_review_eligibility"] = eligibility
    record["current_line_disposition"] = derive_current_line_disposition(record)
    record["preferred_separate_contract_review"] = derive_preferred_review(record)
    record["decision"] = derive_top_level_decision(record["current_line_disposition"], record["preferred_separate_contract_review"])
    record["derived_decision_inputs"] = {
        "current_line_evidence_statuses": {key: value["proposition_status"] for key, value in current_evidence.items()},
        "separate_review_eligibility": {key: value["preferred_review_eligible"] for key, value in eligibility.items()},
        "axes_are_independent": True,
    }
    record["validation"] = {
        "generator": "scripts/phase1bd_d1f_active_contract_decision.py",
        "current_line_recomputed": True,
        "preferred_review_recomputed": True,
        "gates_recomputed": True,
        "score_totals": score_totals(scorecards),
        "historical_correction_totals": {
            classification: sum(cell["historical_correction_classification"] == classification for cells in scorecards.values() for cell in cells.values())
            for classification in sorted(set(AUDIT_CLASS.values()))
        },
        "score_evidence_class_totals": {
            evidence_class: sum(cell["evidence_class"] == evidence_class for cells in scorecards.values() for cell in cells.values())
            for evidence_class in sorted(SCORE_EVIDENCE_CLASSES)
        },
        "all_authorization_flags_false": True,
    }
    return record


def validate_repository_evidence(record: dict[str, Any]) -> None:
    evidence = record["repository_evidence"]
    expected = build_repository_evidence()
    require(set(evidence) == set(expected), "repository evidence identities changed")
    for evidence_id, identity in expected.items():
        require(evidence[evidence_id] == identity, f"repository evidence contract changed: {evidence_id}")


def validate_options(options: dict[str, dict[str, Any]]) -> None:
    require(set(options) == set(OPTION_IDS) and len(options) == 6, "exactly six options are required")
    for option_id, option in options.items():
        require(set(CONTRACT_FIELDS) <= set(option), f"incomplete contract: {option_id}")
        require(option["hidden_clipping_or_semantic_repair"] is False, f"hidden repair in {option_id}")
        require(option["signed_weights_are_probabilities"] is False, f"signed weights treated as probabilities in {option_id}")
        require(option["implementation_ready_claimed"] is False, f"implementation readiness claimed in {option_id}")
    require(options[OPTION_IDS[1]]["active_pdf_family_identity"]["status"] == "NEW_FAMILY_NOT_D0R_CORRECTION", "new family cannot silently replace D0R")
    require(options[OPTION_IDS[3]]["observed_event_set_representation"]["status"] == "DEFINED_WEIGHTED_NOT_IID_UNWEIGHTED", "weighted sets cannot be iid unweighted")
    require(options[OPTION_IDS[4]]["event_and_set_weights"]["status"] == "SIGNED_ESTIMATOR_NOT_PROBABILITY", "signed estimator cannot be probability")
    lower = options[OPTION_IDS[2]]
    require(lower["issue_roadmap_implications"]["status"] == "SEPARATE_SCOPE_NOT_ISSUE_10_COMPLETION", "lower-level review cannot complete issue #10")
    require(lower["full_generator_equivalence_claimed"] is False, "lower-level option cannot claim full-generator equivalence")
    require(set(lower["omitted_physics"]) >= {"ISR", "parton_showering", "hadronization", "beam_remnants"}, "lower-level omitted physics incomplete")
    termination = options[OPTION_IDS[5]]
    require(termination["global_sbi_impossibility_claimed"] is False, "termination cannot reject all SBI")
    require(all(options[option]["relationship_to_current_line"] == "SEPARATE_PROSPECTIVE_CONTRACT" for option in REDESIGN_OPTIONS), "redesign cannot be current-line continuation")


def validate_scorecards(record: dict[str, Any]) -> None:
    scorecards = record["option_scorecards"]
    evidence = record["repository_evidence"]
    require(set(scorecards) == set(OPTION_IDS), "scorecards incomplete")
    for option_id, cells in scorecards.items():
        require(set(cells) == set(CRITERIA) and len(cells) == 20, f"twenty criteria required: {option_id}")
        rationales = []
        for criterion, cell in cells.items():
            require(set(cell) == {"option_id", "criterion_id", "status", "criterion_specific_rationale", "evidence_class", "evidence_bindings", "explicit_inference", "implication_for_current_line", "implication_for_separate_review", "load_bearing", "historical_correction_classification"}, f"score cell schema invalid: {option_id}/{criterion}")
            require(cell["option_id"] == option_id, f"score option identity changed: {option_id}/{criterion}")
            require(cell["criterion_id"] == criterion, f"score criterion identity changed: {option_id}/{criterion}")
            derive_score_status(cell, evidence)
            index = CRITERIA.index(criterion)
            audit_code = AUDIT_CLASS_CODES[option_id][index]
            require(cell["historical_correction_classification"] == AUDIT_CLASS[audit_code], f"historical correction classification changed: {option_id}/{criterion}")
            require(cell["status"] == corrected_score_status(V2_SCORE_CODES[option_id][index], audit_code), f"corrected score status changed: {option_id}/{criterion}")
            require(len(cell["criterion_specific_rationale"]) >= 80, f"criterion rationale too shallow: {option_id}/{criterion}")
            rationales.append(cell["criterion_specific_rationale"])
        require(len(set(rationales)) == 20, f"generic rationale reused across scorecard: {option_id}")


def validate_supersession(supersession: dict[str, Any], options: dict[str, dict[str, Any]]) -> None:
    for section in ("historical_negative_results", "current_line_active_effects", "lower_level_candidate_hypothetical_effects"):
        require(section in supersession, f"missing supersession section: {section}")
        require(set(supersession[section].values()) <= SUPERSESSION_STATUSES, f"invalid supersession status: {section}")
    require(set(supersession["historical_negative_results"]) == HISTORICAL_RESULT_KEYS, "historical negative-result keys changed")
    require(supersession["current_line_active_effects"] == {"ISSUE_10_FULL_GENERATOR_D2": "CURRENT_STATE_PRESERVED", "CURRENT_FULL_GENERATOR_D2_D5_ROADMAP": "CURRENT_STATE_PRESERVED"}, "active pause effects changed")
    lower = supersession["lower_level_candidate_hypothetical_effects"]
    require(lower == supersession["redesign_option_effects"][OPTION_IDS[2]], "preferred lower-level effects differ from the option-derived row")
    require(lower["ADR-001"] == "PRESERVED" and lower["ADR-004"] == "PRESERVED" and lower["D0R"] == "PRESERVED", "lower-level review must preserve D0R evidence")
    require(lower["ADR-002"] == "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED" and lower["ADR-006"] == "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED", "lower-level hypothetical supersession incomplete")
    require(lower["ISSUE_10"] == "NOT_COMPLETED_BY_LOWER_LEVEL_MODEL", "lower-level model cannot complete issue #10")
    require(lower["NEURAL_PHASE"] == "WOULD_REQUIRE_NEW_DECISION_IF_SEPARATELY_ACCEPTED", "Neural decision boundary changed")
    require(all(value == "PRESERVED_AS_HISTORICAL_EVIDENCE" for value in supersession["historical_negative_results"].values()), "historical negative evidence changed")
    family = supersession["redesign_option_effects"][OPTION_IDS[1]]
    require(options[OPTION_IDS[1]]["active_pdf_family_identity"]["status"] == "NEW_FAMILY_NOT_D0R_CORRECTION", "nonnegative family relationship changed")
    require(family["ADR-001"] == "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED" and family["ADR-004"] == "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED" and family["D0R"] == "PRESERVED_AS_HISTORICAL_EVIDENCE", "new-family supersession does not follow its contract")
    weighted = supersession["redesign_option_effects"][OPTION_IDS[3]]
    require(options[OPTION_IDS[3]]["original_objective_compatibility"]["status"] == "CHANGES_PRIMARY_DATA_OBJECT", "weighted-set objective-change status changed")
    require(weighted["ADR-003_FIXED_N_SHAPE_ONLY"] == "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED", "weighted sets must remain hypothetical")
    signed = supersession["redesign_option_effects"][OPTION_IDS[4]]
    require(options[OPTION_IDS[4]]["original_objective_compatibility"]["status"] == "NOT_SUPPORTED", "signed-weight objective status changed")
    require(signed["ADR-003_FIXED_N_SHAPE_ONLY"] == "WOULD_REQUIRE_PROSPECTIVE_SUPERSESSION_IF_SEPARATELY_ACCEPTED", "signed-weight research must remain hypothetical")


def validate_current_line_evidence(record: dict[str, Any]) -> None:
    evidence = record["current_line_evidence"]
    require(set(evidence) == set(CURRENT_EVIDENCE_FIELDS), "current-line evidence incomplete")
    expected = build_current_line_evidence(record["options"])
    repo_evidence = record["repository_evidence"]
    required_keys = {"proposition_status", "evidence_class", "evidence_ids", "claim_keys", "premises", "inference", "rationale"}
    for field_id in CURRENT_EVIDENCE_FIELDS:
        row = evidence[field_id]
        require(set(row) == required_keys, f"current-line evidence schema changed: {field_id}")
        require(row["proposition_status"] in EVIDENCE_STATUSES, f"invalid current-line status: {field_id}")
        require(row["evidence_class"] in CURRENT_EVIDENCE_CLASSES, f"invalid current-line evidence class: {field_id}")
        require(row == expected[field_id], f"current-line evidence contract changed: {field_id}")
        for evidence_id, claim_key in zip(row["evidence_ids"], row["claim_keys"], strict=False):
            require(evidence_id != "D1F_CONCEPTUAL_REVIEW", f"ADR-010 cannot independently prove current-line evidence: {field_id}")
            require(claim_key in repo_evidence[evidence_id].get("claims", {}), f"unknown current-line claim: {field_id}")
        if row["evidence_class"] == "NOT_EVALUATED":
            require(row["proposition_status"] == "NOT_EVALUATED", f"unevaluated proposition promoted: {field_id}")
        if row["evidence_class"] == "EXPLICIT_INFERENCE_FROM_IMMUTABLE_EVIDENCE":
            require(row["premises"] and row["inference"], f"current-line inference lacks premises: {field_id}")


def validate_record(record: dict[str, Any]) -> None:
    require(record.get("schema_version") == SCHEMA, "schema mismatch")
    require(record.get("precedence") == build_precedence(), "immutable precedence changed")
    validate_repository_evidence(record)
    validate_options(record["options"])
    validate_scorecards(record)
    validate_supersession(record["supersession_matrix"], record["options"])
    validate_current_line_evidence(record)

    gates = derive_normalized_measure_gates(record["options"])
    require(record["normalized_measure_gate"] == gates, "normalized-measure gates differ from recomputation")
    require(gates[OPTION_IDS[0]]["status"] == "PASS_WITH_QUALIFICATION", "Option A cannot claim unqualified PASS")
    require(gates[OPTION_IDS[2]]["status"] == "PASS_WITH_QUALIFICATION", "Option C cannot claim unqualified PASS")

    eligibility = derive_separate_review_eligibility(record["options"], gates, record["option_scorecards"], record["supersession_matrix"], record["repository_evidence"])
    require(record["separate_review_eligibility"] == eligibility, "separate-review eligibility differs from recomputation")
    current = derive_current_line_disposition(record)
    preferred = derive_preferred_review(record)
    decision = derive_top_level_decision(current, preferred)
    require(record["current_line_disposition"] == current, "current-line disposition differs from recomputation")
    require(record["preferred_separate_contract_review"] == preferred, "preferred review differs from recomputation")
    require(record["decision"] == decision and decision in TOP_LEVEL_DECISIONS, "top-level decision differs from two-axis derivation")
    require(record["current_line_disposition"] in CURRENT_LINE_DISPOSITIONS, "invalid current-line disposition")
    require(record["preferred_separate_contract_review"] in PREFERRED_REVIEWS, "invalid preferred review")
    require(current == "MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE", "corrected evidence must retain the current-line pause")
    require(preferred == "NONE", "independent evidence does not support a unique preferred review")
    require(decision == "MAINTAIN_CURRENT_CONTRACT_AND_PAUSE", "corrected top-level pause decision changed")
    require(all(not row["unique_preference_supported"] and not row["preferred_review_eligible"] for row in eligibility.values()), "unsupported unique preference selected")
    require(record["options"][OPTION_IDS[2]]["candidate_status"] == "PLAUSIBLE_SEPARATE_REVIEW_CANDIDATE_REQUIRES_INDEPENDENT_EVIDENCE", "lower-level candidate status changed")
    require(record["options"][OPTION_IDS[2]]["conceptual_reviewability"] == "INCOMPLETE_BUT_REVIEWABLE", "lower-level reviewability changed")

    derived = {
        "current_line_evidence_statuses": {key: value["proposition_status"] for key, value in record["current_line_evidence"].items()},
        "separate_review_eligibility": {key: value["preferred_review_eligible"] for key, value in eligibility.items()},
        "axes_are_independent": True,
    }
    require(record["derived_decision_inputs"] == derived, "serialized derived inputs changed")
    require(record["validation"]["score_totals"] == score_totals(record["option_scorecards"]), "score totals differ from recomputation")
    expected_corrections = {classification: sum(cell["historical_correction_classification"] == classification for cells in record["option_scorecards"].values() for cell in cells.values()) for classification in sorted(set(AUDIT_CLASS.values()))}
    expected_evidence_classes = {evidence_class: sum(cell["evidence_class"] == evidence_class for cells in record["option_scorecards"].values() for cell in cells.values()) for evidence_class in sorted(SCORE_EVIDENCE_CLASSES)}
    require(record["validation"]["historical_correction_totals"] == expected_corrections, "historical correction totals changed")
    require(record["validation"]["score_evidence_class_totals"] == expected_evidence_classes, "score evidence-class totals changed")
    require(record["authorization"] == {flag: False for flag in AUTHORIZATION_FLAGS}, "all authorization flags must be false")
    require(record["dependencies"]["issue_10"] == {"number": 10, "state": "OPEN_BLOCKED", "completed_by_lower_level_model": False, "authorization": "NOT_AUTHORIZED"}, "issue #10 boundary changed")
    require(record["dependencies"]["D2"] == "BLOCKED_AND_UNAUTHORIZED", "D2 boundary changed")
    require(record["dependencies"]["roadmap"] == {"D2": "BLOCKED", "D3": "BACKLOG", "D4": "BACKLOG", "D5": "BACKLOG", "active_supersession": False}, "roadmap state changed")
    require(record["active_operational_policy"] == "PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION", "active operational policy changed")
    require(record["current_full_generator_line"] == "PAUSED_NO_BOUNDED_CONTINUATION_ESTABLISHED", "current full-generator state changed")
    require(record["lower_level_contract_review"] == "PLAUSIBLE_BUT_NOT_PREFERRED_OR_AUTHORIZED", "lower-level policy changed")
    require(record["next_step"] == {"action": "INDEPENDENT_EVIDENCE_REVIEW_FOR_SEPARATE_CONTRACT_PRIORITY", "scope": "Planning-only review of independent motivation and load-bearing evidence; Option C obligations remain unevaluated.", "implementation": False, "authorization_granted": False}, "next step became implementation or changed scope")


def serialized(record: dict[str, Any]) -> str:
    return json.dumps(record, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    expected = build_record()
    validate_record(copy.deepcopy(expected))
    path = repo / ARTIFACT
    if args.write:
        path.write_text(serialized(expected), encoding="utf-8")
    if args.validate:
        require(path.is_file(), f"missing artifact: {ARTIFACT}")
        actual_text = path.read_text(encoding="utf-8")
        actual = json.loads(actual_text)
        validate_record(actual)
        require(actual_text == serialized(expected), "artifact bytes differ from deterministic generation")
        print(f"VALID {SCHEMA} current_line={actual['current_line_disposition']} preferred={actual['preferred_separate_contract_review']}")
    if not args.write and not args.validate:
        parser.error("one of --write or --validate is required")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractDecisionError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
