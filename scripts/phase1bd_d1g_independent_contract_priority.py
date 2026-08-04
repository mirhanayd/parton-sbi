#!/usr/bin/env python3
"""Generate and validate the planning-only Phase 1B-D1G decision.

The module binds a bounded registry of independent primary sources to four
prospective scientific contracts and derives review priority from ten
mandatory gates.  It executes no parser, generator, PDF library, event code,
numerical physics, detector simulation, dataset pipeline, or neural code.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "partonsbi.phase1bd.d1g.independent-contract-priority.v1"
ARTIFACT = "docs/phase1bd_d1g_independent_contract_priority.json"

CANDIDATES = (
    "NEW_NONNEGATIVE_GENERATOR_COMPATIBLE_PDF_FAMILY",
    "LOWER_LEVEL_DIS_HARD_EVENT_MODEL",
    "WEIGHTED_EMPIRICAL_EVENT_SET",
    "SIGNED_WEIGHT_INFERENCE_RESEARCH",
)
B, C, D, E = CANDIDATES

CRITERIA = (
    "normalized_observation_measure",
    "posterior_target_coherence",
    "scientific_motivation",
    "qcd_factorization_compatibility",
    "pdf_interpretability",
    "event_set_representation",
    "weight_semantics",
    "rate_shape_semantics",
    "detector_response_coherence",
    "calibration_and_coverage",
    "no_clipping_preservation",
    "strict_support_preservation",
    "bounded_planning_review_question",
    "independent_falsifiability",
    "credible_end_to_end_mvp_path",
    "objective_change_risk",
    "reproducibility",
    "expected_evidence_value_if_review_fails",
)

STATUSES = {
    "SUPPORTED",
    "SUPPORTED_WITH_QUALIFICATION",
    "NOT_SUPPORTED",
    "PRIMARY_EVIDENCE_UNAVAILABLE",
    "NOT_APPLICABLE",
}
POSITIVE = {"SUPPORTED", "SUPPORTED_WITH_QUALIFICATION"}
EVIDENCE_CLASSES = {
    "DIRECT_PRIMARY_EVIDENCE",
    "EXPLICIT_INFERENCE_FROM_PRIMARY_EVIDENCE",
    "PROSPECTIVE_HYPOTHESIS",
    "PRIMARY_EVIDENCE_UNAVAILABLE",
    "NOT_APPLICABLE",
}
OUTCOMES = {
    B: "PRIORITIZE_NEW_NONNEGATIVE_FAMILY_CONTRACT_REVIEW",
    C: "PRIORITIZE_LOWER_LEVEL_DIS_CONTRACT_REVIEW",
    D: "PRIORITIZE_WEIGHTED_EMPIRICAL_SET_CONTRACT_REVIEW",
    E: "PRIORITIZE_SIGNED_WEIGHT_RESEARCH_REVIEW",
}
PAUSE_OUTCOME = "NO_UNIQUE_PRIORITY_MAINTAIN_PAUSE"

MANDATORY_GATES = (
    "normalized_measure_reviewability",
    "posterior_reviewability",
    "scientific_motivation",
    "bounded_planning_review",
    "independent_falsifiability",
    "credible_MVP_path",
    "no_hidden_repair",
    "prospective_supersession_explicit",
    "objective_change_understood",
    "independent_evidence_available",
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

OPTION_C_OBLIGATIONS = (
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


class D1GDecisionError(RuntimeError):
    """Raised when the D1G evidence or derivation contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise D1GDecisionError(message)


def claim(
    option_scope: list[str],
    criterion_scope: list[str],
    maximum_supported_status: str,
    statement: str,
) -> dict[str, Any]:
    return {
        "option_scope": option_scope,
        "criterion_scope": criterion_scope,
        "maximum_supported_status": maximum_supported_status,
        "statement": statement,
    }


def source(
    source_id: str,
    source_type: str,
    title: str,
    authors: str,
    publication: str,
    publication_date: str,
    identifier: str,
    version: str,
    url: str,
    digest: str | None,
    option_scope: list[str],
    criterion_scope: list[str],
    claims: dict[str, dict[str, Any]],
    maximum: str,
    limitations: str,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "source_type": source_type,
        "exact_title": title,
        "authors_or_institution": authors,
        "publication_or_standard": publication,
        "publication_date": publication_date,
        "DOI_or_arXiv_or_official_identifier": identifier,
        "exact_version": version,
        "official_URL": url,
        "retrieval_date": "2026-08-04",
        "retrieved_byte_SHA256_when_downloaded": digest,
        "primary_source_status": "PRIMARY_SOURCE_CONFIRMED",
        "option_scope": option_scope,
        "criterion_scope": criterion_scope,
        "claim_scope": claims,
        "maximum_supported_status": maximum,
        "limitations": limitations,
        "load_bearing": True,
    }


def build_sources() -> dict[str, dict[str, Any]]:
    return {
        "B_MSbar_POSITIVITY_2023": source(
            "B_MSbar_POSITIVITY_2023", "ORIGINAL_RESEARCH_PAPER",
            "On the positivity of MSbar parton distributions",
            "Alessandro Candido; Stefano Forte; Tommaso Giani; Felix Hekhorn",
            "arXiv", "2026-04-22", "arXiv:2308.00025v4", "v4",
            "https://arxiv.org/pdf/2308.00025v4",
            "b46edb54469cd2d7f1da85245f2b44cf1fa8dda377e2e28dac305ab33c006281",
            [B], ["scientific_motivation", "qcd_factorization_compatibility", "pdf_interpretability", "objective_change_risk"],
            {
                "PERTURBATIVE_MSBAR_NONNEGATIVITY_DOMAIN": claim([B], ["scientific_motivation", "qcd_factorization_compatibility"], "SUPPORTED_WITH_QUALIFICATION", "MSbar PDFs are argued to be nonnegative only in a stated perturbative domain."),
                "LOW_SCALE_NEGATIVITY_REMAINS_POSSIBLE": claim([B], ["pdf_interpretability", "objective_change_risk"], "SUPPORTED", "The analysis explicitly distinguishes perturbative-domain positivity from possible low-scale negativity."),
            }, "SUPPORTED_WITH_QUALIFICATION",
            "Does not define the proposed PartonSBI family, theta law, generator interface, observation law, or end-to-end inference contract.",
        ),
        "B_NNPDF40": source(
            "B_NNPDF40", "OFFICIAL_COLLABORATION_PUBLICATION",
            "The Path to Proton Structure at One-Percent Accuracy",
            "NNPDF Collaboration", "European Physical Journal C 82 (2022) 428",
            "2022-05-31", "doi:10.1140/epjc/s10052-022-10328-7; arXiv:2109.02653v4", "v4",
            "https://arxiv.org/pdf/2109.02653v4",
            "c0825bb47708b2b691862256f2a315dd8788f6521859e0d7eaeee58a88e3c7a6",
            [B], ["scientific_motivation", "pdf_interpretability", "no_clipping_preservation", "bounded_planning_review_question", "independent_falsifiability", "reproducibility", "expected_evidence_value_if_review_fails"],
            {
                "POSITIVITY_AND_SUM_RULE_CONSTRAINTS": claim([B], ["scientific_motivation", "pdf_interpretability", "no_clipping_preservation"], "SUPPORTED_WITH_QUALIFICATION", "NNPDF4.0 reports systematic positivity constraints and integrability of sum rules in a global PDF determination."),
                "CLOSURE_AND_FUTURE_TESTS": claim([B], ["bounded_planning_review_question", "independent_falsifiability", "expected_evidence_value_if_review_fails"], "SUPPORTED_WITH_QUALIFICATION", "The PDF methodology is validated with closure and future tests."),
                "OPEN_METHOD_IMPLEMENTATION": claim([B], ["reproducibility"], "SUPPORTED_WITH_QUALIFICATION", "The collaboration reports an open-source framework for its PDF methodology."),
            }, "SUPPORTED_WITH_QUALIFICATION",
            "Observable-positivity constraints in a global fit do not establish generator-compatible positivity for a new PartonSBI family or its deployment.",
        ),
        "B_MSBAR_POSITIVITY_2020": source(
            "B_MSBAR_POSITIVITY_2020", "PEER_REVIEWED_ORIGINAL_RESEARCH",
            "Can MSbar parton distributions be negative?",
            "Alessandro Candido; Stefano Forte; Felix Hekhorn", "JHEP 11 (2020) 129",
            "2020-10-20", "doi:10.1007/JHEP11(2020)129; arXiv:2006.07377v2", "v2",
            "https://arxiv.org/pdf/2006.07377v2",
            "5c1c0e00d3e86aa8dc7269afbcc6e0824507bd6457d2315236d1fda99b0d4b2a",
            [B], ["qcd_factorization_compatibility", "pdf_interpretability", "strict_support_preservation"],
            {"NLO_MSBAR_POSITIVITY_IS_PERTURBATIVE": claim([B], ["qcd_factorization_compatibility", "pdf_interpretability", "strict_support_preservation"], "SUPPORTED_WITH_QUALIFICATION", "The NLO positivity argument depends on a perturbative regime and a controlled scheme transformation.")},
            "SUPPORTED_WITH_QUALIFICATION",
            "Does not prove positivity over the accepted D0R box, at every scale, flavor, interpolation point, or generator query.",
        ),
        "C_HERA_COMBINED_DIS": source(
            "C_HERA_COMBINED_DIS", "OFFICIAL_COLLABORATION_PUBLICATION",
            "Combination of Measurements of Inclusive Deep Inelastic e+-p Scattering Cross Sections and QCD Analysis of HERA Data",
            "H1 and ZEUS Collaborations", "European Physical Journal C 75 (2015) 580",
            "2015-11-20", "doi:10.1140/epjc/s10052-015-3710-4; arXiv:1506.06042v3", "v3",
            "https://arxiv.org/pdf/1506.06042v3",
            "04971dfad54401348e66d6bf39ea6ef43ac8e5b854ad313381d68df045ab40bc",
            [C], ["normalized_observation_measure", "posterior_target_coherence", "scientific_motivation", "qcd_factorization_compatibility", "pdf_interpretability", "weight_semantics", "rate_shape_semantics", "no_clipping_preservation", "strict_support_preservation", "bounded_planning_review_question", "independent_falsifiability", "credible_end_to_end_mvp_path", "objective_change_risk", "reproducibility", "expected_evidence_value_if_review_fails"],
            {
                "NC_EPLUS_EMINUS_STRUCTURE": claim([C], ["normalized_observation_measure", "posterior_target_coherence", "scientific_motivation", "qcd_factorization_compatibility", "pdf_interpretability", "weight_semantics", "rate_shape_semantics"], "SUPPORTED_WITH_QUALIFICATION", "The collaboration publishes inclusive neutral-current e- and e+ DIS cross sections, structure-function dependence, and QCD PDF analyses."),
                "GAMMA_Z_XF3_EVIDENCE": claim([C], ["bounded_planning_review_question", "independent_falsifiability", "credible_end_to_end_mvp_path", "expected_evidence_value_if_review_fails"], "SUPPORTED_WITH_QUALIFICATION", "The publication reports xF3 gamma-Z extraction and electroweak structure, bounding a formula-level review question."),
                "REDUCED_INCLUSIVE_SCOPE": claim([C], ["no_clipping_preservation", "objective_change_risk", "strict_support_preservation", "reproducibility"], "SUPPORTED_WITH_QUALIFICATION", "The measured inclusive DIS scope is explicit and narrower than a complete generator event record."),
            }, "SUPPORTED_WITH_QUALIFICATION",
            "Does not by itself prove positivity and finite normalization for every theta, detector-kernel normalization, or full-generator equivalence.",
        ),
        "C_DAGOSTINI_UNFOLDING": source(
            "C_DAGOSTINI_UNFOLDING", "PEER_REVIEWED_ORIGINAL_METHOD_PAPER",
            "A multidimensional unfolding method based on Bayes theorem",
            "Giulio D'Agostini", "Nuclear Instruments and Methods A 362 (1995) 487-498",
            "1995-09-28", "doi:10.1016/0168-9002(95)00274-X; arXiv:hep-ph/9509307v1", "v1",
            "https://arxiv.org/pdf/hep-ph/9509307",
            "d3ad8e695c6a89c157e51d313e0f8254f9c7688920294cf0cf4f8467f679350a",
            [C], ["detector_response_coherence", "bounded_planning_review_question", "credible_end_to_end_mvp_path", "objective_change_risk"],
            {"DETECTOR_RESPONSE_CONDITIONAL_PROBABILITIES": claim([C], ["detector_response_coherence", "bounded_planning_review_question", "credible_end_to_end_mvp_path", "objective_change_risk"], "SUPPORTED_WITH_QUALIFICATION", "The method represents detector smearing and inefficiency through conditional response probabilities in a Bayesian unfolding construction.")},
            "SUPPORTED_WITH_QUALIFICATION",
            "An unfolding response matrix is evidence for conditional detector semantics, not a validated PartonSBI detector kernel.",
        ),
        "C_SIMULATION_BASED_CALIBRATION": source(
            "C_SIMULATION_BASED_CALIBRATION", "ORIGINAL_METHOD_PAPER",
            "Validating Bayesian Inference Algorithms with Simulation-Based Calibration",
            "Sean Talts; Michael Betancourt; Daniel Simpson; Aki Vehtari; Andrew Gelman",
            "arXiv", "2020-10-21", "arXiv:1804.06788v2", "v2",
            "https://arxiv.org/pdf/1804.06788v2",
            "64ed9a85a4467380afb446588d4cb34788cc3a90ab4c95986f230f0372b9fed6",
            [C], ["posterior_target_coherence", "calibration_and_coverage", "independent_falsifiability", "credible_end_to_end_mvp_path", "expected_evidence_value_if_review_fails"],
            {"SBC_REQUIRES_GENERATIVE_MODEL_AND_POSTERIOR": claim([C], ["posterior_target_coherence", "calibration_and_coverage", "independent_falsifiability", "credible_end_to_end_mvp_path", "expected_evidence_value_if_review_fails"], "SUPPORTED_WITH_QUALIFICATION", "SBC validates Bayesian computation through repeated draws from a specified generative model and posterior algorithm.")},
            "SUPPORTED_WITH_QUALIFICATION",
            "SBC supplies a validation framework but does not establish the proposed DIS likelihood or discharge its physics obligations.",
        ),
        "C_DEEP_SETS": source(
            "C_DEEP_SETS", "PEER_REVIEWED_ORIGINAL_METHOD_PAPER", "Deep Sets",
            "Manzil Zaheer; Satwik Kottur; Siamak Ravanbakhsh; Barnabas Poczos; Ruslan Salakhutdinov; Alexander Smola",
            "NeurIPS 2017", "2018-04-14", "arXiv:1703.06114v3", "v3",
            "https://arxiv.org/pdf/1703.06114v3",
            "b72a01cc43b222ea9e5808e10135c55c63444546b4c9f29cbe8e9abed9f7ea70",
            [C], ["event_set_representation", "credible_end_to_end_mvp_path", "reproducibility"],
            {"PERMUTATION_INVARIANT_SET_FUNCTIONS": claim([C], ["event_set_representation", "credible_end_to_end_mvp_path", "reproducibility"], "SUPPORTED_WITH_QUALIFICATION", "The paper characterizes permutation-invariant functions and architectures for set-valued inputs.")},
            "SUPPORTED_WITH_QUALIFICATION",
            "Set-network representation does not establish that the proposed events are iid, normalized, sufficient, or physically complete.",
        ),
        "D_WEIGHTED_EMPIRICAL_MEASURES": source(
            "D_WEIGHTED_EMPIRICAL_MEASURES", "PEER_REVIEWED_ORIGINAL_RESEARCH",
            "Large deviations for weighted empirical measures arising in importance sampling",
            "Henrik Hult; Pierre Nyquist", "Stochastic Processes and their Applications 126 (2016) 138-170",
            "2014-08-29", "doi:10.1016/j.spa.2015.08.002; arXiv:1210.2251v2", "v2",
            "https://arxiv.org/pdf/1210.2251v2",
            "1f1715034b2d9adc8c61e4a5dd1028ca440e5dc38cdfddcaea95af1ae0c02956",
            [D], ["normalized_observation_measure", "scientific_motivation", "event_set_representation", "weight_semantics", "no_clipping_preservation", "strict_support_preservation", "bounded_planning_review_question", "independent_falsifiability", "objective_change_risk", "expected_evidence_value_if_review_fails"],
            {"IMPORTANCE_WEIGHTED_EMPIRICAL_MEASURE": claim([D], ["normalized_observation_measure", "scientific_motivation", "event_set_representation", "weight_semantics", "no_clipping_preservation", "strict_support_preservation", "bounded_planning_review_question", "independent_falsifiability", "objective_change_risk", "expected_evidence_value_if_review_fails"], "SUPPORTED_WITH_QUALIFICATION", "Positive likelihood-ratio weights define an importance-sampling weighted empirical measure with an explicit proposal and target.")},
            "SUPPORTED_WITH_QUALIFICATION",
            "Does not define posterior conditioning on a random weighted observed event set or justify replacing the accepted iid event-set objective.",
        ),
        "D_IMPORTANCE_ESS": source(
            "D_IMPORTANCE_ESS", "PEER_REVIEWED_ORIGINAL_METHOD_PAPER",
            "Effective Sample Size for Importance Sampling based on discrepancy measures",
            "Luca Martino; Victor Elvira; Francisco Louzada", "Signal Processing 131 (2017) 386-401",
            "2016-09-25", "doi:10.1016/j.sigpro.2016.08.025; arXiv:1602.03572v5", "v5",
            "https://arxiv.org/pdf/1602.03572v5",
            "d6afe982335f645f0744d3fb8e1814458634efd571f89484f2a9d8bdf1f784de",
            [D], ["weight_semantics", "independent_falsifiability", "reproducibility", "expected_evidence_value_if_review_fails"],
            {"NORMALIZED_WEIGHT_ESS_DIAGNOSTICS": claim([D], ["weight_semantics", "independent_falsifiability", "reproducibility", "expected_evidence_value_if_review_fails"], "SUPPORTED_WITH_QUALIFICATION", "The paper derives effective-sample-size diagnostics from normalized importance weights and weight discrepancy." )},
            "SUPPORTED_WITH_QUALIFICATION",
            "ESS diagnoses importance-weight concentration; it does not supply a posterior or calibration law for weighted observed sets.",
        ),
        "D_WEIGHTED_ERM": source(
            "D_WEIGHTED_ERM", "ORIGINAL_METHOD_PAPER",
            "Weighted Empirical Risk Minimization: Sample Selection Bias Correction based on Importance Sampling",
            "Robin Vogel; Mastane Achab; Stephan Clemencon; Charles Tillier", "arXiv",
            "2020-02-19", "arXiv:2002.05145v2", "v2",
            "https://arxiv.org/pdf/2002.05145v2",
            "ecf956590af46c6fd89f3396c19af3cdd2c4127b6c0390aba3a3f331a975e68b",
            [D], ["scientific_motivation", "strict_support_preservation", "bounded_planning_review_question", "reproducibility"],
            {"TARGET_PROPOSAL_DOMINATION_AND_WEIGHTED_RISK": claim([D], ["scientific_motivation", "strict_support_preservation", "bounded_planning_review_question", "reproducibility"], "SUPPORTED_WITH_QUALIFICATION", "Weighted risk correction requires a target distribution dominated by the sampling distribution and explicit likelihood-ratio semantics.")},
            "SUPPORTED_WITH_QUALIFICATION",
            "Weighted ERM addresses sample-selection correction, not a new generative observation object for amortized Bayesian set inference.",
        ),
        "E_MCATNLO": source(
            "E_MCATNLO", "PEER_REVIEWED_ORIGINAL_METHOD_PAPER",
            "Matching NLO QCD computations and parton shower simulations",
            "Stefano Frixione; Bryan R. Webber", "JHEP 06 (2002) 029",
            "2002-07-31", "doi:10.1088/1126-6708/2002/06/029; arXiv:hep-ph/0204244v2", "v2",
            "https://arxiv.org/pdf/hep-ph/0204244",
            "a0b4c198461c324f28c5adb20f663982f4b89684f653beb07d746841c6975c81",
            [E], ["normalized_observation_measure", "posterior_target_coherence", "scientific_motivation", "qcd_factorization_compatibility", "event_set_representation", "weight_semantics", "calibration_and_coverage", "no_clipping_preservation", "bounded_planning_review_question", "independent_falsifiability", "credible_end_to_end_mvp_path", "objective_change_risk", "reproducibility", "expected_evidence_value_if_review_fails"],
            {"NEGATIVE_COMPLETE_EVENT_WEIGHTS_ARE_ESTIMATOR_CONTRIBUTIONS": claim([E], ["normalized_observation_measure", "posterior_target_coherence", "scientific_motivation", "qcd_factorization_compatibility", "event_set_representation", "weight_semantics", "calibration_and_coverage", "no_clipping_preservation", "bounded_planning_review_question", "independent_falsifiability", "credible_end_to_end_mvp_path", "objective_change_risk", "reproducibility", "expected_evidence_value_if_review_fails"], "SUPPORTED_WITH_QUALIFICATION", "MC@NLO permits negative complete-event weights as contributions to matched NLO predictions, not as probabilities for individual events.")},
            "SUPPORTED_WITH_QUALIFICATION",
            "Negative NLO event weights do not define a signed probability law, posterior target, proper loss, or calibration procedure.",
        ),
        "E_SHERPA_NEGATIVE_WEIGHTS": source(
            "E_SHERPA_NEGATIVE_WEIGHTS", "ORIGINAL_SOFTWARE_METHOD_PAPER",
            "Reducing negative weights in Monte Carlo event generation with Sherpa",
            "Katharina Danziger; Stefan Hoeche; Frank Siegert", "arXiv",
            "2021-10-28", "arXiv:2110.15211v1", "v1",
            "https://arxiv.org/pdf/2110.15211v1",
            "ec752ecf2dd30027dd1270a3ebba550c5590ac755e291df9cc088e4ea5bf23a6",
            [E], ["scientific_motivation", "event_set_representation", "weight_semantics", "independent_falsifiability", "credible_end_to_end_mvp_path", "reproducibility", "expected_evidence_value_if_review_fails"],
            {"NEGATIVE_WEIGHTS_CAUSE_CANCELLATION_AND_COST": claim([E], ["scientific_motivation", "event_set_representation", "weight_semantics", "independent_falsifiability", "credible_end_to_end_mvp_path", "reproducibility", "expected_evidence_value_if_review_fails"], "SUPPORTED_WITH_QUALIFICATION", "The paper documents negative weights in higher-order event generation as an efficiency and cancellation problem." )},
            "SUPPORTED_WITH_QUALIFICATION",
            "Operational treatment of negative generator weights is not evidence for signed posterior conditioning or a normalized signed data law.",
        ),
        "E_PROPER_SCORING_RULES": source(
            "E_PROPER_SCORING_RULES", "PEER_REVIEWED_ORIGINAL_RESEARCH",
            "Strictly Proper Scoring Rules, Prediction, and Estimation",
            "Tilmann Gneiting; Adrian E. Raftery", "Journal of the American Statistical Association 102 (2007) 359-378",
            "2007-03-01", "doi:10.1198/016214506000001437", "published article",
            "https://doi.org/10.1198/016214506000001437", None,
            [E], ["normalized_observation_measure", "posterior_target_coherence", "calibration_and_coverage", "credible_end_to_end_mvp_path"],
            {"PROPER_SCORES_ELICIT_PROBABILITY_DISTRIBUTIONS": claim([E], ["normalized_observation_measure", "posterior_target_coherence", "calibration_and_coverage", "credible_end_to_end_mvp_path"], "SUPPORTED", "Strictly proper scoring rules are defined for probabilistic forecasts and observations drawn from probability distributions." )},
            "SUPPORTED",
            "The paper does not analyze signed event measures; the incompatibility conclusion is an explicit inference when no positive law is supplied.",
        ),
    }


def build_repository_constraints() -> dict[str, dict[str, Any]]:
    return {
        "D1F_V3": {
            "path": "docs/phase1bd_d1f_active_contract_decision.json",
            "sha256": "62afa19354cb4546f4bc6019d58168d1803b6b2c9e8c57f29ecab14e29d198e5",
            "role": "IMMUTABLE_PARTONSBI_STATE_NOT_INDEPENDENT_PREFERENCE_EVIDENCE",
        },
        "ADR001": {
            "path": "docs/adr/ADR-001-continuous-pdf-family.md",
            "sha256": "bb31dcdf2f0e38e6807c06c887fa1b2ff1895755f03f90c81e4bca4e5bfc01d8",
            "role": "ACTIVE_FAMILY_AND_NO_CLIPPING_CONSTRAINT",
        },
        "ADR003": {
            "path": "docs/adr/ADR-003-event-sampling-semantics.md",
            "sha256": "89c0cf8c09c4349f79855b614b2fea5c9d6eb632882bff5c18abe7f1a8d28fd5",
            "role": "ACTIVE_FIXED_N_SET_SEMANTICS_CONSTRAINT",
        },
        "ADR010": {
            "path": "docs/adr/ADR-010-active-scientific-contract-after-generator-pause.md",
            "sha256": "e30b2dd4045af61a45953d2f176132dcb84d3b6d7424d4ecdf8ae1525115e428",
            "role": "D1F_DECISION_RECORD_NOT_INDEPENDENT_PREFERENCE_EVIDENCE",
        },
    }


STATUS_CODES = {
    B: "UUQQQUUUUUQQQQUQQQ",
    C: "QQQQQQQQQQQQQQQQQQ",
    D: "QUQUUQQUUUQQQQUQQQ",
    E: "NNQQUQQUUNQUQQNQQQ",
}
CODE_TO_STATUS = {
    "S": "SUPPORTED",
    "Q": "SUPPORTED_WITH_QUALIFICATION",
    "N": "NOT_SUPPORTED",
    "U": "PRIMARY_EVIDENCE_UNAVAILABLE",
    "A": "NOT_APPLICABLE",
}

BINDINGS: dict[str, dict[str, list[tuple[str, str]]]] = {
    B: {
        "scientific_motivation": [("B_MSbar_POSITIVITY_2023", "PERTURBATIVE_MSBAR_NONNEGATIVITY_DOMAIN"), ("B_NNPDF40", "POSITIVITY_AND_SUM_RULE_CONSTRAINTS")],
        "qcd_factorization_compatibility": [("B_MSbar_POSITIVITY_2023", "PERTURBATIVE_MSBAR_NONNEGATIVITY_DOMAIN"), ("B_MSBAR_POSITIVITY_2020", "NLO_MSBAR_POSITIVITY_IS_PERTURBATIVE")],
        "pdf_interpretability": [("B_MSbar_POSITIVITY_2023", "LOW_SCALE_NEGATIVITY_REMAINS_POSSIBLE"), ("B_NNPDF40", "POSITIVITY_AND_SUM_RULE_CONSTRAINTS")],
        "no_clipping_preservation": [("B_NNPDF40", "POSITIVITY_AND_SUM_RULE_CONSTRAINTS")],
        "strict_support_preservation": [("B_MSBAR_POSITIVITY_2020", "NLO_MSBAR_POSITIVITY_IS_PERTURBATIVE")],
        "bounded_planning_review_question": [("B_NNPDF40", "CLOSURE_AND_FUTURE_TESTS")],
        "independent_falsifiability": [("B_NNPDF40", "CLOSURE_AND_FUTURE_TESTS")],
        "objective_change_risk": [("B_MSbar_POSITIVITY_2023", "LOW_SCALE_NEGATIVITY_REMAINS_POSSIBLE")],
        "reproducibility": [("B_NNPDF40", "OPEN_METHOD_IMPLEMENTATION")],
        "expected_evidence_value_if_review_fails": [("B_NNPDF40", "CLOSURE_AND_FUTURE_TESTS")],
    },
    C: {
        "normalized_observation_measure": [("C_HERA_COMBINED_DIS", "NC_EPLUS_EMINUS_STRUCTURE")],
        "posterior_target_coherence": [("C_HERA_COMBINED_DIS", "NC_EPLUS_EMINUS_STRUCTURE"), ("C_SIMULATION_BASED_CALIBRATION", "SBC_REQUIRES_GENERATIVE_MODEL_AND_POSTERIOR")],
        "scientific_motivation": [("C_HERA_COMBINED_DIS", "NC_EPLUS_EMINUS_STRUCTURE")],
        "qcd_factorization_compatibility": [("C_HERA_COMBINED_DIS", "NC_EPLUS_EMINUS_STRUCTURE")],
        "pdf_interpretability": [("C_HERA_COMBINED_DIS", "NC_EPLUS_EMINUS_STRUCTURE")],
        "event_set_representation": [("C_DEEP_SETS", "PERMUTATION_INVARIANT_SET_FUNCTIONS")],
        "weight_semantics": [("C_HERA_COMBINED_DIS", "NC_EPLUS_EMINUS_STRUCTURE")],
        "rate_shape_semantics": [("C_HERA_COMBINED_DIS", "NC_EPLUS_EMINUS_STRUCTURE")],
        "detector_response_coherence": [("C_DAGOSTINI_UNFOLDING", "DETECTOR_RESPONSE_CONDITIONAL_PROBABILITIES")],
        "calibration_and_coverage": [("C_SIMULATION_BASED_CALIBRATION", "SBC_REQUIRES_GENERATIVE_MODEL_AND_POSTERIOR")],
        "no_clipping_preservation": [("C_HERA_COMBINED_DIS", "REDUCED_INCLUSIVE_SCOPE")],
        "strict_support_preservation": [("C_HERA_COMBINED_DIS", "REDUCED_INCLUSIVE_SCOPE")],
        "bounded_planning_review_question": [("C_HERA_COMBINED_DIS", "GAMMA_Z_XF3_EVIDENCE"), ("C_DAGOSTINI_UNFOLDING", "DETECTOR_RESPONSE_CONDITIONAL_PROBABILITIES")],
        "independent_falsifiability": [("C_HERA_COMBINED_DIS", "GAMMA_Z_XF3_EVIDENCE"), ("C_SIMULATION_BASED_CALIBRATION", "SBC_REQUIRES_GENERATIVE_MODEL_AND_POSTERIOR")],
        "credible_end_to_end_mvp_path": [("C_HERA_COMBINED_DIS", "GAMMA_Z_XF3_EVIDENCE"), ("C_DAGOSTINI_UNFOLDING", "DETECTOR_RESPONSE_CONDITIONAL_PROBABILITIES"), ("C_SIMULATION_BASED_CALIBRATION", "SBC_REQUIRES_GENERATIVE_MODEL_AND_POSTERIOR"), ("C_DEEP_SETS", "PERMUTATION_INVARIANT_SET_FUNCTIONS")],
        "objective_change_risk": [("C_HERA_COMBINED_DIS", "REDUCED_INCLUSIVE_SCOPE"), ("C_DAGOSTINI_UNFOLDING", "DETECTOR_RESPONSE_CONDITIONAL_PROBABILITIES")],
        "reproducibility": [("C_HERA_COMBINED_DIS", "REDUCED_INCLUSIVE_SCOPE"), ("C_DEEP_SETS", "PERMUTATION_INVARIANT_SET_FUNCTIONS")],
        "expected_evidence_value_if_review_fails": [("C_HERA_COMBINED_DIS", "GAMMA_Z_XF3_EVIDENCE"), ("C_SIMULATION_BASED_CALIBRATION", "SBC_REQUIRES_GENERATIVE_MODEL_AND_POSTERIOR")],
    },
    D: {
        "normalized_observation_measure": [("D_WEIGHTED_EMPIRICAL_MEASURES", "IMPORTANCE_WEIGHTED_EMPIRICAL_MEASURE")],
        "scientific_motivation": [("D_WEIGHTED_EMPIRICAL_MEASURES", "IMPORTANCE_WEIGHTED_EMPIRICAL_MEASURE"), ("D_WEIGHTED_ERM", "TARGET_PROPOSAL_DOMINATION_AND_WEIGHTED_RISK")],
        "event_set_representation": [("D_WEIGHTED_EMPIRICAL_MEASURES", "IMPORTANCE_WEIGHTED_EMPIRICAL_MEASURE")],
        "weight_semantics": [("D_WEIGHTED_EMPIRICAL_MEASURES", "IMPORTANCE_WEIGHTED_EMPIRICAL_MEASURE"), ("D_IMPORTANCE_ESS", "NORMALIZED_WEIGHT_ESS_DIAGNOSTICS")],
        "no_clipping_preservation": [("D_WEIGHTED_EMPIRICAL_MEASURES", "IMPORTANCE_WEIGHTED_EMPIRICAL_MEASURE")],
        "strict_support_preservation": [("D_WEIGHTED_ERM", "TARGET_PROPOSAL_DOMINATION_AND_WEIGHTED_RISK")],
        "bounded_planning_review_question": [("D_WEIGHTED_EMPIRICAL_MEASURES", "IMPORTANCE_WEIGHTED_EMPIRICAL_MEASURE"), ("D_WEIGHTED_ERM", "TARGET_PROPOSAL_DOMINATION_AND_WEIGHTED_RISK")],
        "independent_falsifiability": [("D_WEIGHTED_EMPIRICAL_MEASURES", "IMPORTANCE_WEIGHTED_EMPIRICAL_MEASURE"), ("D_IMPORTANCE_ESS", "NORMALIZED_WEIGHT_ESS_DIAGNOSTICS")],
        "objective_change_risk": [("D_WEIGHTED_EMPIRICAL_MEASURES", "IMPORTANCE_WEIGHTED_EMPIRICAL_MEASURE")],
        "reproducibility": [("D_IMPORTANCE_ESS", "NORMALIZED_WEIGHT_ESS_DIAGNOSTICS"), ("D_WEIGHTED_ERM", "TARGET_PROPOSAL_DOMINATION_AND_WEIGHTED_RISK")],
        "expected_evidence_value_if_review_fails": [("D_WEIGHTED_EMPIRICAL_MEASURES", "IMPORTANCE_WEIGHTED_EMPIRICAL_MEASURE"), ("D_IMPORTANCE_ESS", "NORMALIZED_WEIGHT_ESS_DIAGNOSTICS")],
    },
    E: {
        "normalized_observation_measure": [("E_MCATNLO", "NEGATIVE_COMPLETE_EVENT_WEIGHTS_ARE_ESTIMATOR_CONTRIBUTIONS"), ("E_PROPER_SCORING_RULES", "PROPER_SCORES_ELICIT_PROBABILITY_DISTRIBUTIONS")],
        "posterior_target_coherence": [("E_MCATNLO", "NEGATIVE_COMPLETE_EVENT_WEIGHTS_ARE_ESTIMATOR_CONTRIBUTIONS"), ("E_PROPER_SCORING_RULES", "PROPER_SCORES_ELICIT_PROBABILITY_DISTRIBUTIONS")],
        "scientific_motivation": [("E_MCATNLO", "NEGATIVE_COMPLETE_EVENT_WEIGHTS_ARE_ESTIMATOR_CONTRIBUTIONS"), ("E_SHERPA_NEGATIVE_WEIGHTS", "NEGATIVE_WEIGHTS_CAUSE_CANCELLATION_AND_COST")],
        "qcd_factorization_compatibility": [("E_MCATNLO", "NEGATIVE_COMPLETE_EVENT_WEIGHTS_ARE_ESTIMATOR_CONTRIBUTIONS")],
        "event_set_representation": [("E_MCATNLO", "NEGATIVE_COMPLETE_EVENT_WEIGHTS_ARE_ESTIMATOR_CONTRIBUTIONS"), ("E_SHERPA_NEGATIVE_WEIGHTS", "NEGATIVE_WEIGHTS_CAUSE_CANCELLATION_AND_COST")],
        "weight_semantics": [("E_MCATNLO", "NEGATIVE_COMPLETE_EVENT_WEIGHTS_ARE_ESTIMATOR_CONTRIBUTIONS"), ("E_SHERPA_NEGATIVE_WEIGHTS", "NEGATIVE_WEIGHTS_CAUSE_CANCELLATION_AND_COST")],
        "calibration_and_coverage": [("E_PROPER_SCORING_RULES", "PROPER_SCORES_ELICIT_PROBABILITY_DISTRIBUTIONS")],
        "no_clipping_preservation": [("E_MCATNLO", "NEGATIVE_COMPLETE_EVENT_WEIGHTS_ARE_ESTIMATOR_CONTRIBUTIONS")],
        "bounded_planning_review_question": [("E_MCATNLO", "NEGATIVE_COMPLETE_EVENT_WEIGHTS_ARE_ESTIMATOR_CONTRIBUTIONS")],
        "independent_falsifiability": [("E_MCATNLO", "NEGATIVE_COMPLETE_EVENT_WEIGHTS_ARE_ESTIMATOR_CONTRIBUTIONS"), ("E_SHERPA_NEGATIVE_WEIGHTS", "NEGATIVE_WEIGHTS_CAUSE_CANCELLATION_AND_COST")],
        "credible_end_to_end_mvp_path": [("E_SHERPA_NEGATIVE_WEIGHTS", "NEGATIVE_WEIGHTS_CAUSE_CANCELLATION_AND_COST"), ("E_PROPER_SCORING_RULES", "PROPER_SCORES_ELICIT_PROBABILITY_DISTRIBUTIONS")],
        "objective_change_risk": [("E_MCATNLO", "NEGATIVE_COMPLETE_EVENT_WEIGHTS_ARE_ESTIMATOR_CONTRIBUTIONS")],
        "reproducibility": [("E_MCATNLO", "NEGATIVE_COMPLETE_EVENT_WEIGHTS_ARE_ESTIMATOR_CONTRIBUTIONS"), ("E_SHERPA_NEGATIVE_WEIGHTS", "NEGATIVE_WEIGHTS_CAUSE_CANCELLATION_AND_COST")],
        "expected_evidence_value_if_review_fails": [("E_MCATNLO", "NEGATIVE_COMPLETE_EVENT_WEIGHTS_ARE_ESTIMATOR_CONTRIBUTIONS"), ("E_SHERPA_NEGATIVE_WEIGHTS", "NEGATIVE_WEIGHTS_CAUSE_CANCELLATION_AND_COST")],
    },
}

RATIONALE_PREFIX = {
    B: "A prospective nonnegative family",
    C: "A reduced neutral-current DIS hard-event contract",
    D: "A positive weighted empirical event-set contract",
    E: "A signed-weight research contract",
}

RATIONALE_DETAIL = {
    "normalized_observation_measure": "is assessed on whether its evidence defines a positive finite observation law rather than only scalar or estimator semantics.",
    "posterior_target_coherence": "is assessed on whether conditioning is defined against that same observation law.",
    "scientific_motivation": "is assessed on independent scientific motivation rather than implementation convenience.",
    "qcd_factorization_compatibility": "is assessed on the exact factorization scope established by primary QCD evidence.",
    "pdf_interpretability": "is assessed on preserving or explicitly replacing the meaning of the accepted PDF parameters.",
    "event_set_representation": "is assessed on the random object represented by one observed set.",
    "weight_semantics": "is assessed on whether weights are probabilities, positive importance ratios, or signed estimator contributions.",
    "rate_shape_semantics": "is assessed on whether conditioning on fixed sample size and discarded rate information is explicit.",
    "detector_response_coherence": "is assessed on whether a normalized conditional response law is specified.",
    "calibration_and_coverage": "is assessed on whether repeated sampling from a generative law can validate the posterior procedure.",
    "no_clipping_preservation": "is assessed on preserving values and failures without numerical clipping or absolute-value repair.",
    "strict_support_preservation": "is assessed on explicit target/proposal or physical support rather than extrapolation.",
    "bounded_planning_review_question": "is assessed on whether a later contract review has finite, checkable questions.",
    "independent_falsifiability": "is assessed on whether independent evidence identifies decisive failure observations.",
    "credible_end_to_end_mvp_path": "is assessed only at contract-review level, never as implementation authorization.",
    "objective_change_risk": "is assessed on whether departure from the accepted D0R fixed-N objective is explicit.",
    "reproducibility": "is assessed on pinned identities and a repeatable prospective contract, not on unexecuted software.",
    "expected_evidence_value_if_review_fails": "is assessed on whether a negative review would resolve a real scientific ambiguity.",
}

LIMITATIONS = {
    B: "No source defines the new theta/prior, complete generator observation law, or a PartonSBI end-to-end MVP; this is a new family, not a D0R correction.",
    C: "Primary sources support the component review question only; all fourteen physics and normalization obligations remain NOT_EVALUATED and no full-generator equivalence is claimed.",
    D: "The sources concern positive importance weights with explicit proposal/target laws; none establishes posterior conditioning on a random weighted observed event set.",
    E: "Negative event weights are estimator contributions, not a normalized probability law; no coherent signed posterior target or calibration law is supplied.",
}


def build_scorecards(sources: dict[str, dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    cards: dict[str, dict[str, dict[str, Any]]] = {}
    for candidate in CANDIDATES:
        require(len(STATUS_CODES[candidate]) == len(CRITERIA), f"score code length: {candidate}")
        cards[candidate] = {}
        for criterion, code in zip(CRITERIA, STATUS_CODES[candidate], strict=True):
            status = CODE_TO_STATUS[code]
            pairs = BINDINGS.get(candidate, {}).get(criterion, [])
            bindings = []
            for source_id, claim_key in pairs:
                scope = sources[source_id]["claim_scope"][claim_key]
                bindings.append({
                    "source_id": source_id,
                    "claim_key": claim_key,
                    "option_scope": copy.deepcopy(scope["option_scope"]),
                    "criterion_scope": copy.deepcopy(scope["criterion_scope"]),
                    "maximum_supported_status": scope["maximum_supported_status"],
                })
            if status == "PRIMARY_EVIDENCE_UNAVAILABLE":
                evidence_class = "PRIMARY_EVIDENCE_UNAVAILABLE"
            elif status == "NOT_APPLICABLE":
                evidence_class = "NOT_APPLICABLE"
            elif status == "SUPPORTED" and len(bindings) == 1:
                evidence_class = "DIRECT_PRIMARY_EVIDENCE"
            else:
                evidence_class = "EXPLICIT_INFERENCE_FROM_PRIMARY_EVIDENCE"
            explicit = None
            if evidence_class == "EXPLICIT_INFERENCE_FROM_PRIMARY_EVIDENCE":
                explicit = {
                    "premises": [f"{row['source_id']}:{row['claim_key']}" for row in bindings],
                    "conclusion": f"The bounded primary evidence supports only {status} for {candidate}/{criterion}.",
                }
            load_bearing = status in POSITIVE | {"NOT_SUPPORTED"}
            cards[candidate][criterion] = {
                "candidate_id": candidate,
                "criterion_id": criterion,
                "status": status,
                "evidence_class": evidence_class,
                "evidence_bindings": bindings,
                "explicit_inference": explicit,
                "candidate_specific_rationale": f"{RATIONALE_PREFIX[candidate]} {RATIONALE_DETAIL[criterion]} The recorded status is {status}.",
                "limitations": LIMITATIONS[candidate],
                "load_bearing": load_bearing,
            }
    return cards


def build_candidates() -> dict[str, dict[str, Any]]:
    common = {
        "implementation_ready": False,
        "implementation_authorized": False,
        "prospective_supersession_explicit": True,
    }
    return {
        B: {
            **common,
            "contract_scope": "A separately identified nonnegative evolved PDF family with new theta, prior, and family identity.",
            "not_a_D0R_correction": True,
            "no_hidden_repair": True,
            "scientific_boundary": "Observable positivity and scheme-dependent PDF positivity must remain distinct; no clipping is allowed.",
        },
        C: {
            **common,
            "contract_scope": "z~p_theta(z), y~K(y|z), fixed-N D={y_i}, with p_theta proportional to the accepted-domain neutral-current DIS differential rate.",
            "no_hidden_repair": True,
            "full_generator_equivalence_claimed": False,
            "issue_10_completed": False,
            "omitted_physics": ["ISR", "parton_showering", "hadronization", "underlying_event", "beam_remnants"],
            "proof_obligations": [{"obligation_id": item, "status": "NOT_EVALUATED"} for item in OPTION_C_OBLIGATIONS],
        },
        D: {
            **common,
            "contract_scope": "A random positive weighted empirical measure with explicit proposal, target, normalization, and ESS semantics.",
            "no_hidden_repair": True,
            "weights_positive_only": True,
            "treated_as_iid_unweighted_events": False,
            "signed_weights_included": False,
        },
        E: {
            **common,
            "contract_scope": "Research on signed estimator samples only if a positive normalized observation law and coherent posterior can be constructed.",
            "no_hidden_repair": True,
            "signed_weights_are_probabilities": False,
            "negative_event_weights_alone_establish_posterior": False,
        },
    }


GATE_CRITERIA = {
    "normalized_measure_reviewability": "normalized_observation_measure",
    "posterior_reviewability": "posterior_target_coherence",
    "scientific_motivation": "scientific_motivation",
    "bounded_planning_review": "bounded_planning_review_question",
    "independent_falsifiability": "independent_falsifiability",
    "credible_MVP_path": "credible_end_to_end_mvp_path",
    "objective_change_understood": "objective_change_risk",
}


def derive_gates(record: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for candidate in CANDIDATES:
        cells = record["criterion_scorecards"][candidate]
        gates = {gate: cells[criterion]["status"] for gate, criterion in GATE_CRITERIA.items()}
        gates["no_hidden_repair"] = cells["no_clipping_preservation"]["status"] if record["candidates"][candidate]["no_hidden_repair"] else "NOT_SUPPORTED"
        gates["prospective_supersession_explicit"] = "SUPPORTED" if record["candidates"][candidate]["prospective_supersession_explicit"] else "NOT_SUPPORTED"
        primary_load_bearing = any(
            cell["load_bearing"] and cell["evidence_class"] in {"DIRECT_PRIMARY_EVIDENCE", "EXPLICIT_INFERENCE_FROM_PRIMARY_EVIDENCE"} and cell["evidence_bindings"]
            for cell in cells.values()
        )
        gates["independent_evidence_available"] = "SUPPORTED" if primary_load_bearing else "PRIMARY_EVIDENCE_UNAVAILABLE"
        result[candidate] = gates
    return result


def derive_eligibility(gates: dict[str, dict[str, str]]) -> dict[str, dict[str, Any]]:
    return {
        candidate: {
            "eligible": all(value in POSITIVE for value in gates[candidate].values()),
            "failed_or_unavailable_gates": [gate for gate, value in gates[candidate].items() if value not in POSITIVE],
        }
        for candidate in CANDIDATES
    }


def derive_decision(eligibility: dict[str, dict[str, Any]]) -> str:
    eligible = [candidate for candidate in CANDIDATES if eligibility[candidate]["eligible"]]
    return OUTCOMES[eligible[0]] if len(eligible) == 1 else PAUSE_OUTCOME


def flattened_bindings(scorecards: dict[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    result = []
    for candidate in CANDIDATES:
        for criterion in CRITERIA:
            for binding in scorecards[candidate][criterion]["evidence_bindings"]:
                result.append({"candidate_id": candidate, "criterion_id": criterion, **copy.deepcopy(binding)})
    return result


def score_totals(scorecards: dict[str, dict[str, dict[str, Any]]]) -> dict[str, dict[str, int]]:
    return {candidate: dict(sorted(Counter(cell["status"] for cell in scorecards[candidate].values()).items())) for candidate in CANDIDATES}


def build_precedence() -> dict[str, Any]:
    return {
        "D1F_FINAL_DECISION": "MAINTAIN_CURRENT_CONTRACT_AND_PAUSE",
        "D1F_CURRENT_LINE_DISPOSITION": "MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE",
        "D1F_PREFERRED_SEPARATE_CONTRACT_REVIEW": "NONE",
        "D1F_LOWER_LEVEL_CANDIDATE_STATUS": "PLAUSIBLE_SEPARATE_REVIEW_CANDIDATE_REQUIRES_INDEPENDENT_EVIDENCE",
        "ACTIVE_OPERATIONAL_POLICY": "PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION",
        "CURRENT_FULL_GENERATOR_LINE": "PAUSED_NO_BOUNDED_CONTINUATION_ESTABLISHED",
        "D2_AUTHORIZED": False,
    }


def build_record() -> dict[str, Any]:
    sources = build_sources()
    candidates = build_candidates()
    scorecards = build_scorecards(sources)
    seed = {"candidates": candidates, "criterion_scorecards": scorecards}
    gates = derive_gates(seed)
    eligibility = derive_eligibility(gates)
    decision = derive_decision(eligibility)
    return {
        "schema_version": SCHEMA,
        "decision": decision,
        "precedence": build_precedence(),
        "active_pause_state": {
            "current_full_generator_line": "PAUSED_NO_BOUNDED_CONTINUATION_ESTABLISHED",
            "preferred_separate_contract_review_before_D1G": "NONE",
            "active_contract_changed": False,
        },
        "candidates": candidates,
        "external_source_registry": sources,
        "repository_constraint_registry": build_repository_constraints(),
        "claim_bindings": flattened_bindings(scorecards),
        "criterion_scorecards": scorecards,
        "mandatory_priority_gates": gates,
        "candidate_eligibility": eligibility,
        "unique_priority_rule": {
            "rule": "Exactly one candidate must pass all mandatory gates; zero or multiple eligible candidates derive NO_UNIQUE_PRIORITY_MAINTAIN_PAUSE.",
            "manual_totals_or_labels_break_ties": False,
        },
        "derived_decision_inputs": {
            "eligible_candidates": [candidate for candidate in CANDIDATES if eligibility[candidate]["eligible"]],
            "eligible_candidate_count": sum(row["eligible"] for row in eligibility.values()),
            "decision_from_unique_priority_rule": decision,
        },
        "limitations": [
            "The external source bytes are not vendored; twelve versioned PDFs were retrieved and hashed under /tmp/partonsbi_d1g_sources on 2026-08-04.",
            "The proper-scoring-rule source is pinned by peer-reviewed DOI without a committed or downloaded byte hash.",
            "Priority is planning-only and does not discharge scientific proof obligations or establish an executable simulator.",
            "Candidate C is a reduced observation contract and is not equivalent to the paused full-generator line.",
        ],
        "authorization": {flag: False for flag in AUTHORIZATION_FLAGS},
        "dependencies": {
            "planning_issue": {"number": 49, "state": "OPEN", "authorization": "PLANNING_ONLY"},
            "issue_10": {"number": 10, "state": "OPEN_BLOCKED", "authorization": "NOT_AUTHORIZED", "completed_by_candidate_C": False},
            "D2": "BLOCKED_AND_UNAUTHORIZED",
            "roadmap": {"D2": "BLOCKED", "D3": "BACKLOG", "D4": "BACKLOG", "D5": "BACKLOG", "active_supersession": False},
        },
        "next_step": {
            "action": "CREATE_SEPARATE_LOWER_LEVEL_DIS_CONTRACT_REVIEW_PROPOSAL",
            "scope": "Planning proposal only; independently review all fourteen still-NOT_EVALUATED obligations before any implementation decision.",
            "implementation": False,
            "authorization_granted": False,
        },
        "validation": {
            "external_source_count": len(sources),
            "source_count_per_candidate": {candidate: sum(candidate in row["option_scope"] for row in sources.values()) for candidate in CANDIDATES},
            "criterion_totals": score_totals(scorecards),
            "option_C_obligation_count": len(OPTION_C_OBLIGATIONS),
            "deterministic_generation": True,
        },
    }


def validate_source_registry(record: dict[str, Any]) -> None:
    sources = record["external_source_registry"]
    require(sources == build_sources(), "external source identity registry changed")
    require(len(sources) <= 18, "external source bound exceeded")
    for source_id, row in sources.items():
        require(row["source_id"] == source_id, f"source id mismatch: {source_id}")
        require(row["primary_source_status"] == "PRIMARY_SOURCE_CONFIRMED", f"secondary source used: {source_id}")
        require(row["limitations"], f"source limitation missing: {source_id}")
        require("ADR-010" not in row["official_URL"] and "ADR-011" not in row["official_URL"], f"self/circular source used: {source_id}")
        require(row["maximum_supported_status"] in POSITIVE, f"invalid source maximum: {source_id}")
    counts = {candidate: sum(candidate in row["option_scope"] for row in sources.values()) for candidate in CANDIDATES}
    require(all(count <= 5 for count in counts.values()), "per-candidate source bound exceeded")


def validate_cells(record: dict[str, Any]) -> None:
    cards = record["criterion_scorecards"]
    sources = record["external_source_registry"]
    require(set(cards) == set(CANDIDATES), "candidate scorecards incomplete")
    expected_keys = {"candidate_id", "criterion_id", "status", "evidence_class", "evidence_bindings", "explicit_inference", "candidate_specific_rationale", "limitations", "load_bearing"}
    for candidate in CANDIDATES:
        require(set(cards[candidate]) == set(CRITERIA), f"criterion scorecard incomplete: {candidate}")
        rationales = []
        for criterion in CRITERIA:
            cell = cards[candidate][criterion]
            require(set(cell) == expected_keys, f"cell schema changed: {candidate}/{criterion}")
            require(cell["candidate_id"] == candidate and cell["criterion_id"] == criterion, f"cell identity changed: {candidate}/{criterion}")
            require(cell["status"] in STATUSES and cell["evidence_class"] in EVIDENCE_CLASSES, f"invalid score semantics: {candidate}/{criterion}")
            require(cell["limitations"], f"cell limitation missing: {candidate}/{criterion}")
            require(len(cell["candidate_specific_rationale"]) >= 100, f"cell rationale too shallow: {candidate}/{criterion}")
            rationales.append(cell["candidate_specific_rationale"])
            if cell["evidence_class"] in {"PROSPECTIVE_HYPOTHESIS", "PRIMARY_EVIDENCE_UNAVAILABLE", "NOT_APPLICABLE"}:
                require(not cell["load_bearing"], f"non-evidence cell made load-bearing: {candidate}/{criterion}")
            if cell["load_bearing"]:
                require(cell["evidence_bindings"], f"load-bearing cell lacks source: {candidate}/{criterion}")
                require(cell["evidence_class"] in {"DIRECT_PRIMARY_EVIDENCE", "EXPLICIT_INFERENCE_FROM_PRIMARY_EVIDENCE"}, f"load-bearing evidence class invalid: {candidate}/{criterion}")
            for binding in cell["evidence_bindings"]:
                source_id = binding["source_id"]
                require(source_id in sources, f"repository/self reference used as independent evidence: {candidate}/{criterion}")
                source_row = sources[source_id]
                require(source_row["primary_source_status"] == "PRIMARY_SOURCE_CONFIRMED", f"nonprimary load-bearing source: {source_id}")
                claim_key = binding["claim_key"]
                require(claim_key in source_row["claim_scope"], f"unknown source claim: {source_id}/{claim_key}")
                scope = source_row["claim_scope"][claim_key]
                require(binding["option_scope"] == scope["option_scope"] and candidate in binding["option_scope"], f"wrong option scope: {candidate}/{criterion}/{source_id}")
                require(binding["criterion_scope"] == scope["criterion_scope"] and criterion in binding["criterion_scope"], f"wrong criterion scope: {candidate}/{criterion}/{source_id}")
                require(binding["maximum_supported_status"] == scope["maximum_supported_status"], f"source maximum changed: {candidate}/{criterion}/{source_id}")
                if cell["status"] == "SUPPORTED":
                    require(binding["maximum_supported_status"] == "SUPPORTED", f"maximum-supported status exceeded: {candidate}/{criterion}/{source_id}")
            if cell["evidence_class"] == "EXPLICIT_INFERENCE_FROM_PRIMARY_EVIDENCE":
                require(cell["explicit_inference"] is not None and cell["explicit_inference"]["premises"], f"inference lacks premises: {candidate}/{criterion}")
                expected = [f"{row['source_id']}:{row['claim_key']}" for row in cell["evidence_bindings"]]
                require(cell["explicit_inference"]["premises"] == expected, f"inference premises circular or changed: {candidate}/{criterion}")
                require(all("ADR010" not in item and "ADR011" not in item for item in expected), f"ADR self-reference: {candidate}/{criterion}")
        require(len(set(rationales)) == len(CRITERIA), f"generic rationale reused: {candidate}")
    require(record["claim_bindings"] == flattened_bindings(cards), "top-level claim bindings differ from scorecards")


def validate_candidate_boundaries(record: dict[str, Any]) -> None:
    candidates = record["candidates"]
    require(set(candidates) == set(CANDIDATES), "candidate set changed")
    require(candidates[B]["not_a_D0R_correction"] is True, "new family represented as D0R correction")
    require(candidates[C]["full_generator_equivalence_claimed"] is False, "lower-level model claims full-generator equivalence")
    require(candidates[C]["issue_10_completed"] is False, "lower-level model completes issue #10")
    require(set(candidates[C]["omitted_physics"]) == {"ISR", "parton_showering", "hadronization", "underlying_event", "beam_remnants"}, "lower-level omissions changed")
    obligations = candidates[C]["proof_obligations"]
    require([row["obligation_id"] for row in obligations] == list(OPTION_C_OBLIGATIONS), "Option C obligations missing or reordered")
    require(all(row["status"] == "NOT_EVALUATED" for row in obligations), "Option C obligation promoted")
    require(candidates[D]["weights_positive_only"] is True and candidates[D]["signed_weights_included"] is False, "Candidate D includes signed weights")
    require(candidates[D]["treated_as_iid_unweighted_events"] is False, "weighted events treated as iid unweighted")
    require(candidates[E]["signed_weights_are_probabilities"] is False, "signed weights treated as probabilities")
    require(candidates[E]["negative_event_weights_alone_establish_posterior"] is False, "negative weights claimed to establish posterior")
    require(all(not row["implementation_ready"] and not row["implementation_authorized"] for row in candidates.values()), "candidate became implementation-ready")


def validate_record(record: dict[str, Any]) -> None:
    require(record.get("schema_version") == SCHEMA, "schema mismatch")
    require(record.get("precedence") == build_precedence(), "immutable D1F state changed")
    require(record.get("active_pause_state") == {"current_full_generator_line": "PAUSED_NO_BOUNDED_CONTINUATION_ESTABLISHED", "preferred_separate_contract_review_before_D1G": "NONE", "active_contract_changed": False}, "active pause changed")
    require(record.get("repository_constraint_registry") == build_repository_constraints(), "repository constraint identities changed")
    validate_source_registry(record)
    validate_candidate_boundaries(record)
    validate_cells(record)
    gates = derive_gates(record)
    require(record["mandatory_priority_gates"] == gates, "mandatory gates differ from evidence recomputation")
    eligibility = derive_eligibility(gates)
    require(record["candidate_eligibility"] == eligibility, "eligibility differs from mandatory gates")
    decision = derive_decision(eligibility)
    require(record["decision"] == decision and decision in set(OUTCOMES.values()) | {PAUSE_OUTCOME}, "decision differs from unique-priority derivation")
    eligible = [candidate for candidate in CANDIDATES if eligibility[candidate]["eligible"]]
    require(record["derived_decision_inputs"] == {"eligible_candidates": eligible, "eligible_candidate_count": len(eligible), "decision_from_unique_priority_rule": decision}, "derived decision inputs changed")
    require(record["unique_priority_rule"] == {"rule": "Exactly one candidate must pass all mandatory gates; zero or multiple eligible candidates derive NO_UNIQUE_PRIORITY_MAINTAIN_PAUSE.", "manual_totals_or_labels_break_ties": False}, "unique-priority rule changed")
    require(record["authorization"] == {flag: False for flag in AUTHORIZATION_FLAGS}, "authorization flag became true")
    require(record["dependencies"] == {"planning_issue": {"number": 49, "state": "OPEN", "authorization": "PLANNING_ONLY"}, "issue_10": {"number": 10, "state": "OPEN_BLOCKED", "authorization": "NOT_AUTHORIZED", "completed_by_candidate_C": False}, "D2": "BLOCKED_AND_UNAUTHORIZED", "roadmap": {"D2": "BLOCKED", "D3": "BACKLOG", "D4": "BACKLOG", "D5": "BACKLOG", "active_supersession": False}}, "issue #10, D2, or roadmap changed")
    require(record["next_step"] == {"action": "CREATE_SEPARATE_LOWER_LEVEL_DIS_CONTRACT_REVIEW_PROPOSAL", "scope": "Planning proposal only; independently review all fourteen still-NOT_EVALUATED obligations before any implementation decision.", "implementation": False, "authorization_granted": False}, "next step became implementation")
    require(record["validation"] == {"external_source_count": len(record["external_source_registry"]), "source_count_per_candidate": {candidate: sum(candidate in row["option_scope"] for row in record["external_source_registry"].values()) for candidate in CANDIDATES}, "criterion_totals": score_totals(record["criterion_scorecards"]), "option_C_obligation_count": len(OPTION_C_OBLIGATIONS), "deterministic_generation": True}, "validation aggregates differ from recomputation")


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
        print(f"VALID {SCHEMA} decision={actual['decision']} sources={actual['validation']['external_source_count']}")
    if not args.write and not args.validate:
        parser.error("one of --write or --validate is required")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (D1GDecisionError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
