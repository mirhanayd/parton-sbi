#!/usr/bin/env python3
"""Generate and validate the planning-only Phase 1B-D1F contract decision.

This module performs no physics calculation and invokes no generator, parser,
PDF library, event pipeline, dataset code, or neural code.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "partonsbi.phase1bd.d1f.active-contract-decision.v1"
ARTIFACT = "docs/phase1bd_d1f_active_contract_decision.json"

OPTION_IDS = (
    "PRESERVE_CURRENT_CONTRACT_AND_PAUSE",
    "NEW_NONNEGATIVE_GENERATOR_COMPATIBLE_PDF_FAMILY",
    "LOWER_LEVEL_DIS_HARD_EVENT_MODEL",
    "WEIGHTED_EMPIRICAL_EVENT_SET",
    "SIGNED_WEIGHT_INFERENCE_RESEARCH",
    "TERMINATE_PHASE1B_GENERATOR_COUPLING",
)

DECISIONS = {
    "RECOMMEND_NEW_NONNEGATIVE_FAMILY_CONTRACT_REVIEW",
    "RECOMMEND_LOWER_LEVEL_HARD_EVENT_CONTRACT_REVIEW",
    "RECOMMEND_WEIGHTED_EMPIRICAL_SET_CONTRACT_REVIEW",
    "RECOMMEND_SIGNED_WEIGHT_INFERENCE_RESEARCH",
    "MAINTAIN_CURRENT_CONTRACT_AND_PAUSE",
    "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING",
}

DECISION_FOR_OPTION = {
    OPTION_IDS[0]: "MAINTAIN_CURRENT_CONTRACT_AND_PAUSE",
    OPTION_IDS[1]: "RECOMMEND_NEW_NONNEGATIVE_FAMILY_CONTRACT_REVIEW",
    OPTION_IDS[2]: "RECOMMEND_LOWER_LEVEL_HARD_EVENT_CONTRACT_REVIEW",
    OPTION_IDS[3]: "RECOMMEND_WEIGHTED_EMPIRICAL_SET_CONTRACT_REVIEW",
    OPTION_IDS[4]: "RECOMMEND_SIGNED_WEIGHT_INFERENCE_RESEARCH",
    OPTION_IDS[5]: "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING",
}

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

SCORE_STATUSES = {
    "SUPPORTED",
    "SUPPORTED_WITH_QUALIFICATION",
    "NOT_SUPPORTED",
    "PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE",
    "NOT_APPLICABLE",
}

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

SUPERSESSION_TARGETS = (
    "ADR-001_CONTINUOUS_PDF_FAMILY",
    "ADR-002_DIRECT_GENERATION_ARTIFACT",
    "ADR-003_EVENT_SAMPLING_SEMANTICS",
    "ADR-004_PROJECTED_BASELINE_AND_SIGN_TOPOLOGY",
    "ADR-005_D1_EVOLUTION_AND_ARTIFACT_TRANSPORT",
    "ADR-006_TRANSPORT_ARCHITECTURE",
    "ADR-008_SIGNED_GENERATOR_TERMINAL_DECISION",
    "ADR-009_AST_GRAPH_FEASIBILITY",
    "D0R_EVIDENCE",
    "ORIGINAL_D1_RESULT",
    "D1R_RESULT",
    "D1C_RESULT",
    "D1D_RESULT",
    "D1E_RESULT",
    "ISSUE_10_FULL_GENERATOR_D2",
    "D2_D5_ROADMAP",
    "NEURAL_PHASE",
)

SUPERSESSION_STATUSES = {
    "PRESERVED",
    "PRESERVED_AS_HISTORICAL_EVIDENCE",
    "PROSPECTIVELY_SUPERSEDED",
    "REQUIRES_NEW_DECISION",
    "NOT_APPLICABLE",
}


class ContractDecisionError(RuntimeError):
    """Raised when the D1F planning evidence contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractDecisionError(message)


def c(status: str, statement: str) -> dict[str, str]:
    return {"status": status, "statement": statement}


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


def common_preserved() -> list[str]:
    return [
        "All D0R, D1, D1R, D1C, D1D, and D1E results remain immutable evidence.",
        "Strict support, explicit provenance, and the prohibition on hidden clipping remain binding.",
    ]


def build_options() -> dict[str, dict[str, Any]]:
    return {
        OPTION_IDS[0]: {
            "latent_parameter_theta": c("DEFINED", "theta=(delta_v, lambda_sea) on the accepted D0R box."),
            "active_pdf_family_identity": c("DEFINED", "The accepted versioned sum-rule-projected D0R family remains active."),
            "simulator_or_data_generating_law": c("BLOCKED", "The intended full neutral-current generator law remains unavailable because signed values cannot enter every required internal consumer coherently."),
            "normalized_probability_measure": c("DEFINED_BUT_NOT_OPERATIONAL", "The original target remains a normalized selected-event law p(event|theta,selection), but no accepted full-generator realization exists."),
            "observed_event_set_representation": c("DEFINED", "An unordered fixed-N set of observed event features; generator-only truth is provenance, not a default feature."),
            "event_and_set_weights": c("DEFINED", "Primary sets are unweighted; source weights remain provenance and clipping, absolute values, or weights=1 repair are forbidden."),
            "sample_size_semantics": c("DEFINED", "Fixed N conditions away rate information."),
            "rate_shape_semantics": c("DEFINED", "Shape-only MVP; cross sections and veto rates remain diagnostics."),
            "detector_response_contract": c("DEFERRED", "A separately validated detector response is required before detector-level inference."),
            "support_extrapolation_rules": c("DEFINED", "Strict declared support; no extrapolation, clamping, or observed-query-defined shrinkage."),
            "positivity_signed_value_rules": c("DEFINED", "Signed binary64 x*f is preserved; no positivity repair is allowed."),
            "posterior_target": c("DEFINED_BUT_NOT_OPERATIONAL", "p(theta_PDF|D) for fixed-N sets from the unavailable accepted generator law."),
            "training_objective": c("DEFERRED", "A proper amortized posterior loss is defined only after a valid simulator law exists."),
            "calibration_coverage_target": c("DEFINED_BUT_NOT_OPERATIONAL", "Simulation-based calibration and coverage under the same selected-event law; no simulator currently instantiates it."),
            "original_objective_compatibility": c("PRESERVED", "Preserves p(theta_PDF|D) exactly."),
            "preserved_evidence": common_preserved(),
            "prospectively_superseded_evidence": [],
            "issue_roadmap_implications": c("PAUSED", "Issue #10 and D2 remain blocked; D3-D5 and Neural cannot begin."),
            "smallest_falsifiable_next_step": c("NOT_BOUNDED", "D1E found the complete AST consumer graph unbounded and selected no toolchain; the other reopen paths still require separate decisions."),
            "burden_estimate": c("UNBOUNDED", "Full-generator evidence and signed internal-rate mathematics remain unbounded."),
        },
        OPTION_IDS[1]: {
            "latent_parameter_theta": c("REQUIRES_NEW_DECISION", "A new theta and domain must be scientifically defined; the D0R box cannot be silently reused."),
            "active_pdf_family_identity": c("PROSPECTIVE_NEW_FAMILY", "A new immutable generator-compatible family, not a correction to D0R."),
            "simulator_or_data_generating_law": c("PLANNING_DEFINED", "A future full neutral-current generator law using nonnegative evolved densities across every consumer domain."),
            "normalized_probability_measure": c("DEFINED_CONDITIONALLY", "A normalized selected-event probability law exists only if nonnegative rates, ratios, channels, envelopes, ISR, and remnants validate end to end."),
            "observed_event_set_representation": c("DEFINED", "Unordered fixed-N observed event sets, excluding generator-only truth by default."),
            "event_and_set_weights": c("DEFINED", "Unweighted selected events after a separately validated sampling law; no clipping or absolute-value repair."),
            "sample_size_semantics": c("DEFINED", "Fixed-N primary sets; variable-N rate inference requires another decision."),
            "rate_shape_semantics": c("DEFINED", "Shape-only primary target with rate diagnostics."),
            "detector_response_contract": c("REQUIRES_NEW_DECISION", "A validated detector kernel would compose with the parton/event law."),
            "support_extrapolation_rules": c("DEFINED", "Explicit family support covers the full consumer domain; no extrapolation."),
            "positivity_signed_value_rules": c("PROSPECTIVE_NEW_RULE", "Nonnegative evolved densities and positivity-preserving interpolation are defining family properties, never post-hoc clipping."),
            "posterior_target": c("DEFINED_CONDITIONALLY", "p(theta_new_family|D) under the validated new-family generator law."),
            "training_objective": c("DEFINED_CONDITIONALLY", "A proper amortized posterior objective for unweighted fixed-N sets."),
            "calibration_coverage_target": c("DEFINED_CONDITIONALLY", "SBC and frequentist coverage across the new theta domain under the same law."),
            "original_objective_compatibility": c("CHANGED_PARAMETER_FAMILY", "Preserves the form p(theta_PDF|D) but changes which PDF family and theta are scientifically active."),
            "preserved_evidence": common_preserved() + ["D0R remains historical evidence and is never relabelled as the new family."],
            "prospectively_superseded_evidence": ["ADR-001 active family selection", "ADR-004 active D0R family identity", "D0R as the active family"],
            "issue_roadmap_implications": c("REQUIRES_NEW_ROADMAP", "Issue #10 cannot resume under its current D0R contract; a new D0-family and evolution validation sequence is required."),
            "smallest_falsifiable_next_step": c("BOUNDED_PLANNING_REVIEW", "Specify scientific motivation, analytic family, theta, sum rules, positivity theorem/gates, and full consumer support without implementation."),
            "burden_estimate": c("HIGH_AND_UNBOUNDED_BEYOND_REVIEW", "The contract review is bounded; APFEL and full-generator implementation/validation are not yet bounded."),
        },
        OPTION_IDS[2]: {
            "latent_parameter_theta": c("DEFINED", "Retain theta=(delta_v, lambda_sea) and the accepted D0R domain unless a later review explicitly changes them."),
            "active_pdf_family_identity": c("DEFINED", "Retain the accepted D0R boundary/evolution family as scientific input; transport requirements are replaced only prospectively."),
            "simulator_or_data_generating_law": c("PLANNING_DEFINED", "A repository-owned or independently validated normalized neutral-current e±p hard-event density including gamma, Z, and interference over declared phase space, followed by an explicit detector kernel."),
            "normalized_probability_measure": c("DEFINED", "For fixed N, each event is drawn from the nonnegative differential hard-event cross section restricted to declared acceptance and divided by its finite integral; the set law is the exchangeable product conditioned on N."),
            "observed_event_set_representation": c("DEFINED", "An unordered fixed-N set of detector-level lepton/hadronic-summary observables with stable event identities; hard flavor and PDF values remain provenance."),
            "event_and_set_weights": c("DEFINED", "Primary draws are unweighted under the normalized hard-event law; integration weights are validation provenance and never observed features."),
            "sample_size_semantics": c("DEFINED", "Fixed N and exchangeable sampling conditioned on selection; a Poisson rate extension is outside this contract."),
            "rate_shape_semantics": c("DEFINED", "Shape-only likelihood uses the normalized cross section; total rates are retained as diagnostics, not conditioned features."),
            "detector_response_contract": c("DEFINED_FOR_REVIEW", "A normalized, theta-independent response/acceptance kernel must be specified and separately validated; perfect-detector identity is an explicit initial special case."),
            "support_extrapolation_rules": c("DEFINED", "Phase-space and PDF support are intersected analytically; queries outside support fail and no clipping/extrapolation is allowed."),
            "positivity_signed_value_rules": c("DEFINED", "Only the complete physical differential rate must be nonnegative; signed NLO component terms may cancel before normalization and are never sampled as probabilities."),
            "posterior_target": c("DEFINED", "p(theta_D0R|D_hard) proportional to the prior times the fixed-N product of normalized detector-level hard-event densities."),
            "training_objective": c("DEFINED_FOR_REVIEW", "A proper amortized posterior or likelihood-ratio objective trained only on samples from the declared normalized law."),
            "calibration_coverage_target": c("DEFINED_FOR_REVIEW", "SBC, conditional coverage, support-failure accounting, and closure against independent quadrature over predeclared theta points."),
            "original_objective_compatibility": c("PRESERVED_WITH_SCOPED_SIMULATOR", "Preserves set-level p(theta_PDF|D), while D is explicitly a lower-level hard-event observation rather than a full hadronized generator event."),
            "preserved_evidence": common_preserved() + ["D0R family identity and all negative full-generator results remain binding evidence."],
            "prospectively_superseded_evidence": ["ADR-002 full-generator artifact requirement", "ADR-006 full-generator transport architecture", "issue #10 full-generator D2 scope", "the current D2-D5 full-generator roadmap"],
            "issue_roadmap_implications": c("PROSPECTIVE_SCOPE_REPLACEMENT", "A later accepted contract would supersede, not complete, issue #10 and would require a new lower-level validation roadmap before Neural."),
            "smallest_falsifiable_next_step": c("BOUNDED_PLANNING_REVIEW", "Write a mathematical hard-event contract covering beams, full NC gamma/Z/interference, phase-space/Jacobian, flavor sum, normalization, detector kernel, omissions, and independent validation gates."),
            "burden_estimate": c("MEDIUM_FOR_CONTRACT_HIGH_FOR_LATER_IMPLEMENTATION", "The mathematical contract review is bounded; implementation and numerical validation remain separately unestimated and unauthorized."),
        },
        OPTION_IDS[3]: {
            "latent_parameter_theta": c("REQUIRES_NEW_DECISION", "May retain D0R theta only if the weighted empirical measure is defined independently of the failed generator coupling."),
            "active_pdf_family_identity": c("UNRESOLVED", "The producer family and its weight semantics must be fixed before this can be an active contract."),
            "simulator_or_data_generating_law": c("PARTIALLY_DEFINED", "A random weighted empirical measure requires a specified proposal law and weight functional; no accepted producer currently supplies them."),
            "normalized_probability_measure": c("DEFINED_WITH_QUALIFICATION", "Positive normalized weights define a random empirical probability measure conditional on the generated support; signed weights do not."),
            "observed_event_set_representation": c("DEFINED_WITH_QUALIFICATION", "A set of (observed event, source weight, provenance) tuples, not an iid unweighted set."),
            "event_and_set_weights": c("DEFINED_WITH_QUALIFICATION", "Weights remain explicit; positive weights normalize by their sum, while signed weights require the separate research contract."),
            "sample_size_semantics": c("DEFINED_WITH_QUALIFICATION", "Both candidate count and effective sample size are recorded; neither is silently equated with iid N."),
            "rate_shape_semantics": c("REQUIRES_NEW_DECISION", "Normalization may erase rate information; rate-aware use needs luminosity and producer-normalization semantics."),
            "detector_response_contract": c("REQUIRES_NEW_DECISION", "Response must act on events before empirical-measure normalization and preserve weight provenance."),
            "support_extrapolation_rules": c("DEFINED", "Strict proposal and target support; no cross-point pool reuse or extrapolation."),
            "positivity_signed_value_rules": c("DEFINED", "No clipping, absolute values, or reset-to-one; signed cases fail this option and move to signed-weight research."),
            "posterior_target": c("DEFINED_WITH_QUALIFICATION", "p(theta|random positive empirical measure) requires a hierarchical law for proposal draws and weights, not merely normalized histograms."),
            "training_objective": c("UNRESOLVED", "A proper permutation-invariant objective respecting weights and proposal randomness has not been selected."),
            "calibration_coverage_target": c("UNRESOLVED", "Coverage must repeat both proposal sampling and weighted-measure construction and report ESS/support failures."),
            "original_objective_compatibility": c("OBJECTIVE_CHANGED", "Replaces ordinary fixed-N event sets with random empirical measures."),
            "preserved_evidence": common_preserved(),
            "prospectively_superseded_evidence": ["ADR-003 fixed-N unweighted shape-only primary objective"],
            "issue_roadmap_implications": c("REQUIRES_NEW_ROADMAP", "Issue #10 does not become complete; a producer-law and weighted-inference decision must precede any dataset or Neural work."),
            "smallest_falsifiable_next_step": c("BOUNDED_MATHEMATICAL_REVIEW", "Specify a positive-weight proposal/target empirical-measure law, posterior, ESS, loss, and coverage definitions."),
            "burden_estimate": c("HIGH_AND_UNRESOLVED", "Mathematical review is bounded, but a scientifically valid producer and end-to-end MVP are not established."),
        },
        OPTION_IDS[4]: {
            "latent_parameter_theta": c("UNRESOLVED", "Could reference D0R only after a signed data object and conditioning rule are defined."),
            "active_pdf_family_identity": c("UNRESOLVED", "No signed-weight inference family is selected."),
            "simulator_or_data_generating_law": c("NOT_DEFINED", "A finite signed sample is currently only an estimator, not a data-generating probability law."),
            "normalized_probability_measure": c("NOT_SUPPORTED", "No reviewed positive normalized measure has been constructed from signed event weights."),
            "observed_event_set_representation": c("UNRESOLVED", "A cancellation-aware signed measure representation would be required."),
            "event_and_set_weights": c("DEFINED_AS_PROBLEM", "Signed complete-event weights are retained exactly, but cannot be interpreted as probabilities."),
            "sample_size_semantics": c("UNRESOLVED", "N and signed effective sample size do not define an iid sample size without new mathematics."),
            "rate_shape_semantics": c("UNRESOLVED", "Signed normalization and cancellation obstruct ordinary shape/rate decomposition."),
            "detector_response_contract": c("UNRESOLVED", "The response action on a signed estimator has not been connected to a positive observation law."),
            "support_extrapolation_rules": c("DEFINED", "No extrapolation, clipping, absolute values, or discarded signs."),
            "positivity_signed_value_rules": c("DEFINED_AS_RESEARCH_BOUNDARY", "Signed weights remain signed estimators; negative MC@NLO weights are not probability evidence."),
            "posterior_target": c("NOT_SUPPORTED", "No coherent p(theta|signed finite sample) is established without an underlying positive law."),
            "training_objective": c("NOT_SUPPORTED", "No proper loss is established for the undefined posterior target."),
            "calibration_coverage_target": c("NOT_SUPPORTED", "Coverage is undefined until repeated data draws from a positive law are defined."),
            "original_objective_compatibility": c("UNRESOLVED", "May change p(theta_PDF|D) into inference from a signed estimator."),
            "preserved_evidence": common_preserved(),
            "prospectively_superseded_evidence": ["ADR-003 ordinary unweighted fixed-N primary objective if a future signed contract were accepted"],
            "issue_roadmap_implications": c("RESEARCH_ONLY", "Issue #10 and D2 remain blocked; no dataset or neural work follows."),
            "smallest_falsifiable_next_step": c("OPEN_MATHEMATICAL_RESEARCH", "Construct or rule out a positive normalized law, proper loss, and calibration semantics; this is not currently bounded as project implementation planning."),
            "burden_estimate": c("OPEN_ENDED", "Signed-kernel, variance, cancellation, posterior, and calibration theory are unbounded."),
        },
        OPTION_IDS[5]: {
            "latent_parameter_theta": c("PRESERVED_HISTORICALLY", "D0R theta remains valid evidence but is not coupled to a full generator."),
            "active_pdf_family_identity": c("PRESERVED_HISTORICALLY", "D0R remains accepted at its validated scope."),
            "simulator_or_data_generating_law": c("TERMINATED_SCOPE", "No further full-generator law is pursued for the fixed D0R signed contract."),
            "normalized_probability_measure": c("NOT_APPLICABLE", "Termination proposes no new data law."),
            "observed_event_set_representation": c("NOT_APPLICABLE", "Termination proposes no dataset."),
            "event_and_set_weights": c("NOT_APPLICABLE", "Termination proposes no event weights."),
            "sample_size_semantics": c("NOT_APPLICABLE", "Termination proposes no sampling."),
            "rate_shape_semantics": c("NOT_APPLICABLE", "Termination proposes no likelihood."),
            "detector_response_contract": c("NOT_APPLICABLE", "Termination proposes no detector model."),
            "support_extrapolation_rules": c("PRESERVED_HISTORICALLY", "Strict support and no extrapolation remain historical requirements."),
            "positivity_signed_value_rules": c("PRESERVED_HISTORICALLY", "No clipping or sign repair is introduced."),
            "posterior_target": c("NOT_APPLICABLE", "Termination proposes no posterior implementation."),
            "training_objective": c("NOT_APPLICABLE", "Termination proposes no training."),
            "calibration_coverage_target": c("NOT_APPLICABLE", "Termination proposes no calibration study."),
            "original_objective_compatibility": c("SCOPED_TERMINATION", "Does not refute p(theta_PDF|D); it ends only the current full-generator route."),
            "preserved_evidence": common_preserved(),
            "prospectively_superseded_evidence": ["issue #10 full-generator continuation", "the current full-generator D2-D5 roadmap"],
            "issue_roadmap_implications": c("CLOSE_CURRENT_LINE", "Issue #10 would require explicit closure; alternative lower-level or changed-contract work would be separate."),
            "smallest_falsifiable_next_step": c("NOT_APPLICABLE", "The option records a resource decision, not a scientific experiment."),
            "burden_estimate": c("LOW", "Documentation and roadmap closure only."),
        },
    }


def score(status: str, rationale: str, evidence: list[str]) -> dict[str, Any]:
    return {"status": status, "rationale": rationale, "evidence": evidence}


def build_scorecards() -> dict[str, dict[str, dict[str, str]]]:
    vectors = {
        OPTION_IDS[0]: ("S","S","S","S","Q","S","S","Q","S","S","Q","Q","N","N","Q","N","Q","N","S","Q"),
        OPTION_IDS[1]: ("Q","Q","S","Q","Q","S","S","Q","S","S","Q","Q","U","U","Q","N","Q","Q","N","Q"),
        OPTION_IDS[2]: ("S","S","S","Q","S","S","S","Q","S","S","Q","S","Q","Q","Q","Q","Q","Q","Q","S"),
        OPTION_IDS[3]: ("Q","Q","Q","Q","Q","S","S","Q","Q","Q","U","Q","U","U","Q","Q","Q","U","N","Q"),
        OPTION_IDS[4]: ("N","N","U","U","U","S","S","U","Q","U","N","Q","N","N","Q","N","Q","N","N","Q"),
        OPTION_IDS[5]: ("A","A","A","A","A","S","S","A","A","A","A","S","S","S","S","S","A","A","S","Q"),
    }
    names = {"S":"SUPPORTED","Q":"SUPPORTED_WITH_QUALIFICATION","N":"NOT_SUPPORTED","U":"PRIMARY_OR_MATHEMATICAL_EVIDENCE_UNAVAILABLE","A":"NOT_APPLICABLE"}
    rationale = {
        OPTION_IDS[0]: "The accepted fixed contract supplies this property only at its recorded scope; the failed full-generator realization limits operational closure.",
        OPTION_IDS[1]: "A prospectively new nonnegative family could supply this property, but scientific motivation, evolution-wide positivity, and end-to-end bounds are not yet established.",
        OPTION_IDS[2]: "The explicit normalized hard-event law supplies this property at lower-level NC DIS scope; omitted ISR, hadronization, and remnants prevent full-generator equivalence.",
        OPTION_IDS[3]: "A positive weighted empirical-measure contract can partly supply this property, but producer randomness, ESS, proper loss, and coverage remain unresolved.",
        OPTION_IDS[4]: "The current signed object lacks a reviewed positive data law and coherent posterior; preserving signs alone does not supply probability semantics.",
        OPTION_IDS[5]: "Termination is evaluated only as a scoped resource and provenance decision; it proposes no new simulator or posterior.",
    }
    evidence = {
        OPTION_IDS[0]: ["ADR-003", "ADR-008", "ADR-009", "phase1bd_d1d_terminal_decision.json", "phase1bd_d1e_consumer_graph_feasibility.json"],
        OPTION_IDS[1]: ["ADR-001", "ADR-004", "ADR-008", "phase1bd_d1d_terminal_decision.json"],
        OPTION_IDS[2]: ["ADR-001", "ADR-003", "ADR-004", "ADR-008", "ADR-009"],
        OPTION_IDS[3]: ["ADR-003", "ADR-008", "phase1bd_d1d_terminal_decision.json"],
        OPTION_IDS[4]: ["ADR-003", "ADR-008", "phase1bd_d1d_terminal_decision.json"],
        OPTION_IDS[5]: ["ADR-008", "ADR-009", "phase1bd_d1d_terminal_decision.json", "phase1bd_d1e_consumer_graph_feasibility.json"],
    }
    return {
        option: {
            criterion: score(names[code], f"{criterion}: {rationale[option]}", evidence[option])
            for criterion, code in zip(CRITERIA, vector, strict=True)
        }
        for option, vector in vectors.items()
    }


def build_supersession_matrix() -> dict[str, dict[str, str]]:
    historical = {
        "ADR-005_D1_EVOLUTION_AND_ARTIFACT_TRANSPORT",
        "ADR-008_SIGNED_GENERATOR_TERMINAL_DECISION",
        "ADR-009_AST_GRAPH_FEASIBILITY",
        "ORIGINAL_D1_RESULT",
        "D1R_RESULT",
        "D1C_RESULT",
        "D1D_RESULT",
        "D1E_RESULT",
    }
    rows: dict[str, dict[str, str]] = {}
    for target in SUPERSESSION_TARGETS:
        rows[target] = {option: "PRESERVED" for option in OPTION_IDS}
        if target in historical:
            rows[target] = {option: "PRESERVED_AS_HISTORICAL_EVIDENCE" for option in OPTION_IDS}

    for target in ("ADR-001_CONTINUOUS_PDF_FAMILY", "ADR-004_PROJECTED_BASELINE_AND_SIGN_TOPOLOGY", "D0R_EVIDENCE"):
        rows[target][OPTION_IDS[1]] = "PROSPECTIVELY_SUPERSEDED" if target != "D0R_EVIDENCE" else "PRESERVED_AS_HISTORICAL_EVIDENCE"
    rows["ADR-002_DIRECT_GENERATION_ARTIFACT"][OPTION_IDS[1]] = "REQUIRES_NEW_DECISION"
    rows["ADR-006_TRANSPORT_ARCHITECTURE"][OPTION_IDS[1]] = "REQUIRES_NEW_DECISION"
    rows["ISSUE_10_FULL_GENERATOR_D2"][OPTION_IDS[1]] = "REQUIRES_NEW_DECISION"
    rows["D2_D5_ROADMAP"][OPTION_IDS[1]] = "REQUIRES_NEW_DECISION"
    rows["NEURAL_PHASE"][OPTION_IDS[1]] = "REQUIRES_NEW_DECISION"

    for target in ("ADR-002_DIRECT_GENERATION_ARTIFACT", "ADR-006_TRANSPORT_ARCHITECTURE", "ISSUE_10_FULL_GENERATOR_D2", "D2_D5_ROADMAP"):
        rows[target][OPTION_IDS[2]] = "PROSPECTIVELY_SUPERSEDED"
    rows["ADR-003_EVENT_SAMPLING_SEMANTICS"][OPTION_IDS[2]] = "REQUIRES_NEW_DECISION"
    rows["NEURAL_PHASE"][OPTION_IDS[2]] = "REQUIRES_NEW_DECISION"

    rows["ADR-003_EVENT_SAMPLING_SEMANTICS"][OPTION_IDS[3]] = "PROSPECTIVELY_SUPERSEDED"
    rows["ISSUE_10_FULL_GENERATOR_D2"][OPTION_IDS[3]] = "PRESERVED"
    rows["D2_D5_ROADMAP"][OPTION_IDS[3]] = "REQUIRES_NEW_DECISION"
    rows["NEURAL_PHASE"][OPTION_IDS[3]] = "REQUIRES_NEW_DECISION"

    rows["ADR-003_EVENT_SAMPLING_SEMANTICS"][OPTION_IDS[4]] = "PROSPECTIVELY_SUPERSEDED"
    rows["ISSUE_10_FULL_GENERATOR_D2"][OPTION_IDS[4]] = "PRESERVED"
    rows["D2_D5_ROADMAP"][OPTION_IDS[4]] = "REQUIRES_NEW_DECISION"
    rows["NEURAL_PHASE"][OPTION_IDS[4]] = "REQUIRES_NEW_DECISION"

    rows["ISSUE_10_FULL_GENERATOR_D2"][OPTION_IDS[5]] = "PROSPECTIVELY_SUPERSEDED"
    rows["D2_D5_ROADMAP"][OPTION_IDS[5]] = "PROSPECTIVELY_SUPERSEDED"
    rows["NEURAL_PHASE"][OPTION_IDS[5]] = "REQUIRES_NEW_DECISION"
    return rows


def derive_normalized_measure_gate(options: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    results = {}
    for option_id, option in options.items():
        if option_id == OPTION_IDS[5]:
            status = "NOT_APPLICABLE"
        else:
            measure = option["normalized_probability_measure"]["status"]
            posterior = option["posterior_target"]["status"]
            representation = option["observed_event_set_representation"]["status"]
            calibration = option["calibration_coverage_target"]["status"]
            signed_as_probability = option.get("signed_weights_are_probabilities", False)
            hidden_repair = option.get("hidden_clipping_or_semantic_repair", False)
            if measure == "NOT_SUPPORTED" or posterior == "NOT_SUPPORTED":
                status = "FAIL"
            elif any(value in {"UNRESOLVED", "NOT_DEFINED"} for value in (measure, posterior, representation, calibration)):
                status = "FAIL"
            elif signed_as_probability or hidden_repair:
                status = "FAIL"
            elif any("QUALIFICATION" in value or "CONDITIONALLY" in value for value in (measure, posterior, representation, calibration)):
                status = "PASS_WITH_QUALIFICATION"
            else:
                status = "PASS"
        results[option_id] = {
            "status": status,
            "normalized_measure_status": option["normalized_probability_measure"]["status"],
            "posterior_status": option["posterior_target"]["status"],
            "event_representation_status": option["observed_event_set_representation"]["status"],
            "weight_rule_status": option["event_and_set_weights"]["status"],
            "calibration_status": option["calibration_coverage_target"]["status"],
            "hidden_clipping_or_semantic_repair": option.get("hidden_clipping_or_semantic_repair", False),
            "signed_weights_are_probabilities": option.get("signed_weights_are_probabilities", False),
        }
    return results


def score_totals(scorecards: dict[str, dict[str, dict[str, str]]]) -> dict[str, dict[str, int]]:
    return {
        option: {status: sum(cell["status"] == status for cell in cells.values()) for status in sorted(SCORE_STATUSES)}
        for option, cells in scorecards.items()
    }


def derive_inputs(
    options: dict[str, dict[str, Any]],
    gates: dict[str, dict[str, Any]],
    scorecards: dict[str, dict[str, dict[str, str]]],
    matrix: dict[str, dict[str, str]],
) -> dict[str, Any]:
    risk = {
        OPTION_IDS[0]: "LOW_BUT_NO_BOUNDED_ACTION",
        OPTION_IDS[1]: "HIGH_NOT_SCIENTIFICALLY_JUSTIFIED",
        OPTION_IDS[2]: "MEDIUM_EXPLICITLY_JUSTIFIED_BY_SCOPED_SIMULATOR",
        OPTION_IDS[3]: "HIGH_STATISTICAL_OBJECTIVE_UNRESOLVED",
        OPTION_IDS[4]: "HIGH_POSTERIOR_UNDEFINED",
        OPTION_IDS[5]: "LOW_SCOPED_RESOURCE_DECISION",
    }
    mvp = {
        OPTION_IDS[0]: False,
        OPTION_IDS[1]: False,
        OPTION_IDS[2]: True,
        OPTION_IDS[3]: False,
        OPTION_IDS[4]: False,
        OPTION_IDS[5]: False,
    }
    bounded = {
        option: options[option]["smallest_falsifiable_next_step"]["status"] in {"BOUNDED_PLANNING_REVIEW", "BOUNDED_MATHEMATICAL_REVIEW"}
        for option in OPTION_IDS
    }
    prospective = {
        option: any(matrix[target][option] == "PROSPECTIVELY_SUPERSEDED" for target in SUPERSESSION_TARGETS)
        for option in OPTION_IDS
    }
    eligible = {}
    for option in OPTION_IDS:
        eligible[option] = bool(
            option in OPTION_IDS[1:5]
            and gates[option]["status"] in {"PASS", "PASS_WITH_QUALIFICATION"}
            and bounded[option]
            and mvp[option]
            and prospective[option]
            and risk[option] == "MEDIUM_EXPLICITLY_JUSTIFIED_BY_SCOPED_SIMULATOR"
            and scorecards[option]["no_clipping_preservation"]["status"] in {"SUPPORTED", "SUPPORTED_WITH_QUALIFICATION"}
        )
    return {
        "per_option": {
            option: {
                "normalized_measure_gate": gates[option]["status"],
                "posterior_target_status": options[option]["posterior_target"]["status"],
                "prospective_supersession_explicit": prospective[option],
                "bounded_next_decision": bounded[option],
                "credible_end_to_end_mvp_path": mvp[option],
                "scientific_objective_change_risk": risk[option],
                "redesign_recommendation_eligible": eligible[option],
            }
            for option in OPTION_IDS
        },
        "eligible_redesign_options": [option for option in OPTION_IDS if eligible[option]],
        "current_full_generator_continuation_bounded": False,
        "current_objective_remains_scientifically_worth_preserving": True,
        "all_redesigns_are_separate_contracts_not_continuations": True,
    }


def derive_decision(record: dict[str, Any]) -> str:
    eligible = record["derived_decision_inputs"]["eligible_redesign_options"]
    if eligible:
        require(len(eligible) == 1, "decision rule requires one non-dominated eligible redesign")
        return DECISION_FOR_OPTION[eligible[0]]
    inputs = record["derived_decision_inputs"]
    if inputs["current_objective_remains_scientifically_worth_preserving"]:
        return "MAINTAIN_CURRENT_CONTRACT_AND_PAUSE"
    if not inputs["current_full_generator_continuation_bounded"] and inputs["all_redesigns_are_separate_contracts_not_continuations"]:
        return "TERMINATE_CURRENT_PHASE1B_GENERATOR_COUPLING"
    raise ContractDecisionError("evidence does not derive an allowed decision")


def build_record() -> dict[str, Any]:
    options = build_options()
    for option in options.values():
        option["hidden_clipping_or_semantic_repair"] = False
        option["signed_weights_are_probabilities"] = False
    scorecards = build_scorecards()
    matrix = build_supersession_matrix()
    gates = derive_normalized_measure_gate(options)
    record: dict[str, Any] = {
        "schema_version": SCHEMA,
        "decision": None,
        "precedence": build_precedence(),
        "current_contract": {
            "theta": "theta=(delta_v, lambda_sea) on the accepted D0R domain",
            "pdf_family": "versioned sum-rule-projected D0R family",
            "pdf_value_semantics": "signed binary64 x*f with strict support and no clipping",
            "data_objective": "fixed-N shape-only unordered event sets",
            "posterior_objective": "p(theta_PDF | D)",
            "generator_consistency": "hard process, ISR, and beam remnants must share scientifically valid PDF semantics",
        },
        "fixed_contract_failure_summary": {
            "scope": "current D0R signed family through a complete full-generator coupling",
            "failure": "No bounded source-backed complete-consumer path or signed internal probability construction was established.",
            "not_a_failure_of": ["all SBI for PDFs", "all event simulators", "all lower-level hard-event models", "all future PDF-family contracts"],
        },
        "options": options,
        "normalized_measure_gate": gates,
        "option_scorecards": scorecards,
        "supersession_matrix": matrix,
        "decision_rule": {
            "redesign_requirements": ["normalized measure passes", "posterior target is coherent", "no hidden clipping", "prospective supersession is explicit", "next decision is bounded", "credible end-to-end MVP path exists", "objective-change risk is lower or scientifically justified"],
            "maintain_pause_when": "the current objective remains worth preserving but no redesign has a bounded eligible next decision",
            "terminate_when": "the current full-generator line is unbounded, the objective is not preserved, and redesigns are separate contracts",
            "selection_method": "independently recompute gates and per-option inputs; select the sole non-dominated eligible redesign",
        },
        "derived_decision_inputs": derive_inputs(options, gates, scorecards, matrix),
        "scientific_scope": "Planning comparison of six active-contract choices after the generator-coupling pause.",
        "failure_scope": "The fixed D0R signed full-generator coupling has no bounded next task under accepted evidence.",
        "non_failure_scope": ["D0R input-scale scientific evidence", "set-level posterior inference in general", "a separately reviewed normalized lower-level hard-event law", "future contract decisions"],
        "authorization": {flag: False for flag in AUTHORIZATION_FLAGS},
        "dependencies": {
            "planning_issue": {"number": 47, "state": "OPEN", "authorization": "PLANNING_ONLY"},
            "issue_42": {"number": 42, "state": "CLOSED", "gate_decision": "INCONCLUSIVE"},
            "issue_45": {"number": 45, "state": "CLOSED", "gate_decision": "INCONCLUSIVE"},
            "issue_10": {"number": 10, "state": "OPEN_BLOCKED", "gate_decision": "NOT_EVALUATED", "authorization": "NOT_AUTHORIZED"},
            "D2": "BLOCKED_AND_UNAUTHORIZED",
        },
        "next_step": {
            "action": "SCIENTIFIC_REVIEW_OF_LOWER_LEVEL_NC_DIS_HARD_EVENT_CONTRACT",
            "scope": "Planning-only definition of the normalized hard-event measure, full gamma/Z/interference terms, phase space, detector kernel, omissions, posterior, and validation gates.",
            "implementation": False,
            "authorization_granted": False,
        },
        "validation": {
            "generator": "scripts/phase1bd_d1f_active_contract_decision.py",
            "exactly_six_options": True,
            "complete_twenty_field_contracts": True,
            "complete_twenty_criterion_scorecards": True,
            "decision_recomputed_from_serialized_evidence": True,
            "all_authorization_flags_false": True,
            "score_totals": score_totals(scorecards),
        },
    }
    record["decision"] = derive_decision(record)
    return record


def validate_record(record: dict[str, Any]) -> None:
    require(record.get("schema_version") == SCHEMA, "schema mismatch")
    require(record.get("decision") in DECISIONS, "invalid decision")
    require(record.get("precedence") == build_precedence(), "immutable precedence changed")
    options = record.get("options", {})
    require(set(options) == set(OPTION_IDS) and len(options) == 6, "exactly six options are required")
    expected_options = build_options()
    for option in expected_options.values():
        option["hidden_clipping_or_semantic_repair"] = False
        option["signed_weights_are_probabilities"] = False
    require(options == expected_options, "option probability/posterior contracts changed")
    for option_id, option in options.items():
        require(set(CONTRACT_FIELDS).issubset(option), f"{option_id} contract incomplete")
        require(not option["hidden_clipping_or_semantic_repair"], f"{option_id} permits hidden repair")
        require(not option["signed_weights_are_probabilities"], f"{option_id} treats signed weights as probabilities")

    scorecards = record.get("option_scorecards", {})
    require(scorecards == build_scorecards(), "option scorecards changed")
    for option_id, cells in scorecards.items():
        require(set(cells) == set(CRITERIA) and len(cells) == 20, f"{option_id} lacks all twenty criteria")
        require(all(cell["status"] in SCORE_STATUSES for cell in cells.values()), f"{option_id} has invalid score")

    matrix = record.get("supersession_matrix", {})
    require(matrix == build_supersession_matrix(), "supersession matrix changed")
    require(set(matrix) == set(SUPERSESSION_TARGETS) and len(matrix) == len(SUPERSESSION_TARGETS), "supersession targets incomplete")
    require(all(set(row) == set(OPTION_IDS) and set(row.values()) <= SUPERSESSION_STATUSES for row in matrix.values()), "invalid supersession row")
    require(matrix["ADR-003_EVENT_SAMPLING_SEMANTICS"][OPTION_IDS[3]] == "PROSPECTIVELY_SUPERSEDED", "weighted sets must supersede ADR-003")
    require(matrix["ISSUE_10_FULL_GENERATOR_D2"][OPTION_IDS[2]] == "PROSPECTIVELY_SUPERSEDED", "lower-level model must supersede issue #10 rather than complete it")

    gates = derive_normalized_measure_gate(options)
    require(record.get("normalized_measure_gate") == gates, "normalized-measure gates differ from recomputation")
    inputs = derive_inputs(options, gates, scorecards, matrix)
    require(record.get("derived_decision_inputs") == inputs, "derived decision inputs differ from recomputation")
    selected_option = next(option for option, decision in DECISION_FOR_OPTION.items() if decision == record["decision"])
    if record["decision"].startswith("RECOMMEND_"):
        require(gates[selected_option]["status"] in {"PASS", "PASS_WITH_QUALIFICATION"}, "recommended option failed normalized-measure gate")
        require(options[selected_option]["posterior_target"]["status"] not in {"NOT_SUPPORTED", "UNRESOLVED", "NOT_DEFINED"}, "recommended option lacks posterior")
    require(record["decision"] == derive_decision(record), "decision is inconsistent with serialized evidence")
    require(record.get("authorization") == {flag: False for flag in AUTHORIZATION_FLAGS}, "all authorization flags must be false")
    require(record["dependencies"]["issue_10"]["state"] == "OPEN_BLOCKED", "issue #10 must remain blocked")
    require(record["dependencies"]["D2"] == "BLOCKED_AND_UNAUTHORIZED", "D2 must remain blocked")
    require(record["next_step"]["implementation"] is False and record["next_step"]["authorization_granted"] is False, "next step must remain planning-only")
    require(record["validation"]["score_totals"] == score_totals(scorecards), "score totals differ from recomputation")


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
        print(f"VALID {SCHEMA} decision={actual['decision']}")
    if not args.write and not args.validate:
        parser.error("one of --write or --validate is required")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractDecisionError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
