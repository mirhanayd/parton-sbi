#!/usr/bin/env python3
"""Generate and validate the evidence-derived D1D-B planning decision.

This module performs static evidence bookkeeping only.  It does not import,
compile, link, or execute generator or physics software.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "partonsbi.phase1bd.d1d.terminal-decision.v2"
ARTIFACT = "docs/phase1bd_d1d_terminal_decision.json"
RETRIEVAL_UTC_DATE = "2026-08-01"

ALLOWED_DECISIONS = {
    "INCONCLUSIVE",
    "DO_NOT_AUTHORIZE_FURTHER_GENERATOR_PROTOTYPE",
}
ALLOWED_OPERATIONAL_POLICIES = {
    "PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION",
    "TERMINAL_STOP_FOR_FIXED_CONTRACT",
}
ALLOWED_SCORES = {
    "SUPPORTED",
    "SUPPORTED_WITH_QUALIFICATION",
    "NOT_SUPPORTED",
    "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE",
    "NOT_APPLICABLE",
}
SCORE_SEMANTICS = {
    "SUPPORTED": "Direct primary or immutable repository evidence establishes the criterion for the stated scope.",
    "SUPPORTED_WITH_QUALIFICATION": "Evidence establishes only a clearly stated subset of the criterion.",
    "NOT_SUPPORTED": "Evidence affirmatively establishes incompatibility or failure for the stated scope.",
    "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE": "The bounded review did not find sufficient primary evidence to decide.",
    "NOT_APPLICABLE": "The criterion does not apply to the architecture.",
}
EPISTEMIC_BASIS = {
    "SUPPORTED": "DIRECT_SCOPE_EVIDENCE",
    "SUPPORTED_WITH_QUALIFICATION": "SCOPED_SUBSET_EVIDENCE",
    "NOT_SUPPORTED": "AFFIRMATIVE_INCOMPATIBILITY_EVIDENCE",
    "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE": "BOUNDED_REVIEW_EVIDENCE_GAP",
    "NOT_APPLICABLE": "CRITERION_OUTSIDE_ARCHITECTURE_SCOPE",
}
ROUTE_STATES = {
    "COHERENT_BOUNDED_PATH_SUPPORTED",
    "COHERENT_BOUNDED_PATH_POSSIBLE_WITH_EVIDENCE_GAPS",
    "COHERENT_BOUNDED_PATH_NOT_SUPPORTED",
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
ARCH_A = "A_REPOSITORY_OWNED_PYTHIA_FORK_OR_PATCH"
ARCH_B = "B_SIGNED_WEIGHT_GENERATOR_ARCHITECTURE"
ARCH_C = "C_ALTERNATIVE_GENERATOR_OR_TRANSPORT_INTERFACE"
ARCH_D = "D_STOP_FURTHER_GENERATOR_COUPLING_WORK"
ARCHITECTURES = (ARCH_A, ARCH_B, ARCH_C, ARCH_D)
CANDIDATE_IDS = (
    "SHERPA_EXTERNAL_PDF_FULL_DIS_STACK",
    "HERWIG_PDF_AND_SHOWER_STACK",
    "LES_HOUCHES_SIGNED_HARD_EVENT_TRANSPORT",
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
CRITICAL_CRITERIA = (
    "signed_scalar_preservation",
    "nonnegative_probability_rate_validity",
    "hard_process_coverage",
    "isr_sudakov_coverage",
    "beam_remnant_coverage",
    "flavor_categorical_selection",
    "denominator_ratio_validity",
    "maximum_envelope_rejection_semantics",
    "event_weight_semantics",
    "bounded_prototype_falsifiability",
)
COST_CRITERIA = (
    "upstream_maintenance_burden",
    "build_deployment_reproducibility",
    "bounded_prototype_falsifiability",
)

MISSING_EVIDENCE_RE = re.compile(
    r"\b(missing|unreviewed|unknown|unavailable|unresolved|evidence gap|insufficient evidence|"
    r"not (?:established|proven|validated|reviewed|quantified)|"
    r"did not (?:find|establish)|found no|does not establish|"
    r"no (?:reviewed|primary|complete)(?: evidence)?)\b",
    re.IGNORECASE,
)
AFFIRMATIVE_INCOMPATIBILITY_RE = re.compile(
    r"\b(cannot|incompatible|incompatibilit(?:y|ies)|fails?|failure|violates?|precludes?|delegates?|blocks?|lacks?|"
    r"outside the complete-route scope|does not carry|does not preserve)\b",
    re.IGNORECASE,
)


class DecisionError(RuntimeError):
    """Raised when the D1D-B evidence contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DecisionError(message)


def score(
    status: str,
    claim: str,
    evidence_scope: str,
    rationale: str,
    source_ids: tuple[str, ...] = (),
    claim_keys: tuple[str, ...] = (),
    *,
    disproportionate_cost_evidence: bool = False,
) -> dict[str, Any]:
    return {
        "claim": claim,
        "claim_keys": list(claim_keys),
        "disproportionate_cost_evidence": disproportionate_cost_evidence,
        "epistemic_basis": EPISTEMIC_BASIS[status],
        "evidence_scope": evidence_scope,
        "rationale": rationale,
        "source_ids": list(source_ids),
        "status": status,
    }


def arxiv_source(
    source_id: str,
    arxiv_id: str,
    version: str,
    sha256: str,
    claim_scope: tuple[str, ...],
) -> dict[str, Any]:
    versioned_id = f"{arxiv_id}{version}"
    return {
        "arxiv_identifier": arxiv_id,
        "canonical_abstract_url": f"https://arxiv.org/abs/{versioned_id}",
        "canonical_url": f"https://arxiv.org/pdf/{versioned_id}",
        "claim_scope": list(claim_scope),
        "content_sha256": sha256,
        "document_or_software_version": version,
        "immutable_identifier": f"arxiv:{versioned_id}",
        "retrieval_utc_date": RETRIEVAL_UTC_DATE,
        "source_id": source_id,
        "source_identity_status": "PINNED",
        "source_kind": "ARXIV_PRIMARY_PAPER",
    }


def repository_source(
    source_id: str,
    path: str,
    sha256: str,
    claim_scope: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "canonical_url": f"repository://{path}",
        "claim_scope": list(claim_scope),
        "content_sha256": sha256,
        "document_or_software_version": "MERGED_MAIN_AT_D1D_B_START",
        "immutable_identifier": f"sha256:{sha256}",
        "repository_path": path,
        "retrieval_utc_date": RETRIEVAL_UTC_DATE,
        "source_id": source_id,
        "source_identity_status": "PINNED",
        "source_kind": "IMMUTABLE_REPOSITORY_EVIDENCE",
    }


def build_sources() -> dict[str, dict[str, Any]]:
    sources = {
        "D1C": repository_source(
            "D1C",
            "docs/phase1bd_d1c_decision.json",
            "1ce8a824175d078887bef6fc7c72bbccb2b7c8277cd9669c2a355ced42a6e41b",
            (
                "stock_pythia_public_reader_signed_scalar_failure",
                "fixed_signed_binary64_contract",
            ),
        ),
        "D1D_AUDIT_V6": repository_source(
            "D1D_AUDIT_V6",
            "docs/phase1bd_d1d_pythia_semantics_audit.json",
            "bd63eb4b779c8f6fa622b4a4111fa07a963303d7c80ba3761c339bb764a5b430",
            (
                "complete_consumer_graph_not_validated",
                "provenance_evidence_integrity_failure",
                "current_bounded_fork_not_falsifiable",
            ),
        ),
        "D1D_DECISION": repository_source(
            "D1D_DECISION",
            "docs/phase1bd_d1d_pythia_provenance_slice_decision.json",
            "f92958fe745d64c24cd6d12222537154af7d916f24a0c7362c460123d46e04d7",
            (
                "minimal_public_reader_patch_insufficient",
                "external_final_weight_cannot_repair_internal_selection",
                "architecture_comparison_not_ready",
                "provenance_evidence_integrity_failure",
                "prototype_authorization_blocked",
                "authorization_hierarchy_blocks_prototype",
            ),
        ),
        "SHERPA_301_EXTERNAL_PDF_DOC": {
            "canonical_url": "https://sherpa-team.gitlab.io/sherpa/v3.0.1/manual/customization/external-pdf.html",
            "claim_scope": [
                "external_pdf_calculate_getxpdf_accessor_availability",
                "custom_pdf_runtime_library_loading",
            ],
            "content_sha256": "7b8936eac5ee66fa569fc64a0b027e692ad86de9f5979638373267ebf703fbaa",
            "document_or_software_version": "Sherpa Manual 3.0.1",
            "immutable_identifier": "sha256:7b8936eac5ee66fa569fc64a0b027e692ad86de9f5979638373267ebf703fbaa",
            "retrieval_utc_date": RETRIEVAL_UTC_DATE,
            "source_id": "SHERPA_301_EXTERNAL_PDF_DOC",
            "source_identity_status": "PINNED",
            "source_kind": "VERSIONED_OFFICIAL_DOCUMENTATION",
        },
        "SHERPA_301_ISR_DOC": {
            "canonical_url": "https://sherpa-team.gitlab.io/sherpa/v3.0.1/manual/parameters/isr.html",
            "claim_scope": [
                "initial_state_pdf_configuration",
                "pdf_alpha_s_routing_option",
                "shower_pdf_variation_support",
            ],
            "content_sha256": "e5b1f8d7c38ec2371333672c90bd80710a352d0806b032488bfecbbe4a744110",
            "document_or_software_version": "Sherpa Manual 3.0.1",
            "immutable_identifier": "sha256:e5b1f8d7c38ec2371333672c90bd80710a352d0806b032488bfecbbe4a744110",
            "retrieval_utc_date": RETRIEVAL_UTC_DATE,
            "source_id": "SHERPA_301_ISR_DOC",
            "source_identity_status": "PINNED",
            "source_kind": "VERSIONED_OFFICIAL_DOCUMENTATION",
        },
        "SHERPA_301_MANUAL": {
            "canonical_url": "https://sherpa-team.gitlab.io/sherpa/v3.0.1/index_single.html",
            "claim_scope": [
                "lepton_hadron_dis_capability",
                "beam_remnant_module_exists",
                "weighted_event_generation_modes",
                "versioned_build_instructions",
            ],
            "content_sha256": "7f78e097a43d8c27f9b082a5e1919701aac955c7bf7db944e1e1b03709addcf5",
            "document_or_software_version": "Sherpa Manual 3.0.1",
            "immutable_identifier": "sha256:7f78e097a43d8c27f9b082a5e1919701aac955c7bf7db944e1e1b03709addcf5",
            "retrieval_utc_date": RETRIEVAL_UTC_DATE,
            "source_id": "SHERPA_301_MANUAL",
            "source_identity_status": "PINNED",
            "source_kind": "VERSIONED_OFFICIAL_DOCUMENTATION",
        },
        "SHERPA_301_SOURCE_COMMIT": {
            "canonical_url": "https://gitlab.com/sherpa-team/sherpa/-/commit/82ede7a88616eec1ca2ebf6ba3b7dde53fcb3f2c",
            "claim_scope": [
                "source_commit_availability",
                "pdf_base_interface_source",
                "hera_example_source",
                "cmake_build_definition",
                "license_files_present",
            ],
            "content_sha256": None,
            "document_or_software_version": "Sherpa 3.0.1",
            "immutable_identifier": "git:82ede7a88616eec1ca2ebf6ba3b7dde53fcb3f2c",
            "pinned_files": [
                {"path": "PDF/Main/PDF_Base.H", "sha256": "a2e16eb17f1e19b9390140d0bc688fc1da175a3a7b460a68e801f39d7f30db9a"},
                {"path": "PDF/Main/ISR_Handler.C", "sha256": "1933b82a128a79e43ecfbcc1661ff008d279804b29cb4a51603ccfb5ddfcd38a"},
                {"path": "Examples/Jets_in_DIS/HERA/Sherpa.yaml", "sha256": "2ee1d02489b061009c901bb5c30663d0d39bdb5c045c5041a6f67bd622bb98b1"},
                {"path": "CMakeLists.txt", "sha256": "b82d719019060ba990583253bf422141365a716dcc562523e57d6912c65f3292"},
                {"path": "LICENCE", "sha256": "55a4562db3fe9920e7a2ad7405f00bb2207f53c5d51faf696361f9b33029749a"},
                {"path": "COPYING", "sha256": "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986"},
            ],
            "repository_commit_sha": "82ede7a88616eec1ca2ebf6ba3b7dde53fcb3f2c",
            "repository_url": "https://gitlab.com/sherpa-team/sherpa",
            "retrieval_utc_date": RETRIEVAL_UTC_DATE,
            "source_id": "SHERPA_301_SOURCE_COMMIT",
            "source_identity_status": "PINNED",
            "source_kind": "OFFICIAL_SOURCE_REPOSITORY_COMMIT",
        },
        "SHERPA_301_HERA_YAML": {
            "canonical_url": "https://gitlab.com/sherpa-team/sherpa/-/raw/82ede7a88616eec1ca2ebf6ba3b7dde53fcb3f2c/Examples/Jets_in_DIS/HERA/Sherpa.yaml",
            "claim_scope": [
                "hera_lepton_proton_dis_configuration",
                "hera_ew_order_two_hard_process",
                "hera_shower_configuration",
                "hera_pdf_configuration",
                "mcatnlo_mode_configuration",
            ],
            "content_sha256": "2ee1d02489b061009c901bb5c30663d0d39bdb5c045c5041a6f67bd622bb98b1",
            "document_or_software_version": "Sherpa 3.0.1",
            "immutable_identifier": "git-blob:dfa23751d6bd6e28f202fe915ed666edf13e2aad",
            "repository_commit_sha": "82ede7a88616eec1ca2ebf6ba3b7dde53fcb3f2c",
            "repository_path": "Examples/Jets_in_DIS/HERA/Sherpa.yaml",
            "retrieval_utc_date": RETRIEVAL_UTC_DATE,
            "source_id": "SHERPA_301_HERA_YAML",
            "source_identity_status": "PINNED",
            "source_kind": "OFFICIAL_SOURCE_FILE_AT_COMMIT",
        },
    }
    sources.update(
        {
            "SHERPA_3_PAPER": arxiv_source(
                "SHERPA_3_PAPER",
                "2410.22148",
                "v1",
                "5adefda595551caec2bb33f48eaaf6b4c67d343e398c7a5dec822242a7ac0447",
                ("maintained_sherpa3_software", "complete_event_negative_weights"),
            ),
            "HERWIGPP_MANUAL": arxiv_source(
                "HERWIGPP_MANUAL",
                "0803.0883",
                "v3",
                "ea5fa4e0cd538b9eeb38ffb3ac2d825a5cae3780c33f1d8d6b22bafc4e921d93",
                (
                    "lepton_hadron_hard_process_capability",
                    "backward_evolution_shower",
                    "beam_remnant_model",
                    "pdf_handler_interface",
                ),
            ),
            "HERWIG_7_0": arxiv_source(
                "HERWIG_7_0",
                "1512.01178",
                "v1",
                "fe7512b2939da056fea4fb34ad7fa8a6a425d4a38b5d04fe6fcc360d4704deb3",
                ("nlo_matching_negative_complete_event_weights", "hard_process_and_shower_stack"),
            ),
            "HERWIG_7_3": arxiv_source(
                "HERWIG_7_3",
                "2312.05175",
                "v2",
                "028b0658f35ebac3dd24d96a6247653bb45725bfd9de53baa07151787fec7f9b",
                (
                    "maintained_source_and_build_availability",
                    "gplv3_license_declaration",
                    "isr_fsr_alpha_s_controls",
                    "lepton_hadron_support",
                ),
            ),
            "LHEF_STANDARD": arxiv_source(
                "LHEF_STANDARD",
                "hep-ph/0609017",
                "v1",
                "9509b8727dad8cecc1c467d91b25af540e663b2a744c4377f65618b523659330",
                (
                    "signed_complete_event_weight_field",
                    "parton_level_event_transport",
                    "downstream_shower_delegation",
                    "boundary_not_generator",
                ),
            ),
            "MCATNLO": arxiv_source(
                "MCATNLO",
                "hep-ph/0204244",
                "v2",
                "a0b4c198461c324f28c5adb20f663982f4b89684f653beb07d746841c6975c81",
                ("negative_complete_event_weights", "nlo_matching_event_sample_semantics"),
            ),
        }
    )
    return sources


def build_architecture_a_matrix() -> dict[str, dict[str, Any]]:
    gap_sources = ("D1D_AUDIT_V6", "D1D_DECISION")
    return {
        "signed_scalar_preservation": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "A full fork could change the public boundary, but end-to-end signed scalar preservation is undecided.", "The merged evidence proves the stock reader failure and minimal-patch insufficiency; it does not evaluate a complete fork.", "The bounded review did not find a source-backed complete fork dataflow.", gap_sources),
        "nonnegative_probability_rate_validity": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Probability and rate validity for a redesigned fork is undecided.", "No complete redesigned sampling measure or consumer graph was reviewed.", "The bounded review found no primary or immutable evidence deciding a full replacement construction.", gap_sources),
        "hard_process_coverage": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Hard-process coverage for a complete fork is undecided.", "D1D-A audited selected existing consumers, not a proposed redesigned hard-process implementation.", "The reviewed repository evidence does not establish the prospective fork behavior.", gap_sources),
        "isr_sudakov_coverage": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "ISR and Sudakov coverage for a complete fork is undecided.", "The current consumer graph is not independently valid and no replacement kernel is specified.", "The bounded review found no complete proposed ISR construction.", gap_sources),
        "beam_remnant_coverage": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Beam-remnant coverage for a complete fork is undecided.", "The existing remnant evidence supports minimal-patch insufficiency only.", "The bounded review found no complete redesigned remnant path.", gap_sources),
        "flavor_categorical_selection": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Flavor and categorical selection validity for a fork is undecided.", "No replacement categorical measure was proposed or reviewed.", "The bounded review found no primary or immutable complete selection construction.", gap_sources),
        "denominator_ratio_validity": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Denominator and ratio validity for a fork is undecided.", "Existing sign-sensitive denominators establish risk, not a redesigned solution.", "The bounded review found no complete replacement arithmetic contract.", gap_sources),
        "maximum_envelope_rejection_semantics": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Maximum, envelope, and rejection semantics for a fork are undecided.", "The current evidence identifies sign-sensitive uses but no replacement sampler.", "The bounded review found no complete bounded construction.", gap_sources),
        "event_weight_semantics": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Final event-weight semantics for a redesigned fork are undecided.", "D1D-A rejects final weights as repair of existing internal decisions, not every redesigned measure.", "No reviewed complete fork event measure is available.", gap_sources),
        "strict_support_no_extrapolation": score("SUPPORTED_WITH_QUALIFICATION", "The upstream PDF transport contract can enforce strict support before generator consumption.", "This establishes the evaluator-side subset only; complete fork propagation is not established.", "The fixed repository contract directly supports strict evaluator rejection, while generator integration remains outside scope.", ("D1C",), ("fixed_signed_binary64_contract",)),
        "alpha_s_consistency": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "alpha_s consistency for a proposed fork is undecided.", "No complete fork routing record exists.", "The bounded review found no source-backed alpha_s consumer map for the redesign.", gap_sources),
        "full_neutral_current_gamma_z_compatibility": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Complete neutral-current gamma/Z/interference compatibility for a fork is undecided.", "No full observable contract was evaluated for a proposed fork.", "The bounded review found no source-backed complete compatibility result.", gap_sources),
        "deterministic_identity_and_provenance": score("SUPPORTED_WITH_QUALIFICATION", "Repository commits can identify a future patch deterministically.", "Commit identity covers source provenance, not the absent patch and build artifact.", "Immutable repository evidence establishes the identity mechanism only.", ("D1D_DECISION",), ("provenance_evidence_integrity_failure",)),
        "thread_process_safety": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Thread and process safety for a future fork is undecided.", "No proposed fork exists to test or inspect.", "The bounded review found no primary or immutable safety evidence.", gap_sources),
        "build_deployment_reproducibility": score("SUPPORTED_WITH_QUALIFICATION", "A versioned repository fork can be built from an immutable source identity.", "This establishes an identity mechanism, not a validated patched build or deployment.", "The repository lineage supports the subset while the proposed fork remains absent.", ("D1D_DECISION",), ("provenance_evidence_integrity_failure",)),
        "license_redistribution": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "License and redistribution terms for a proposed PYTHIA fork are undecided.", "No pinned upstream license review is included in this bounded record.", "The bounded review did not establish the redistribution contract.", ("D1D_DECISION",)),
        "upstream_maintenance_burden": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "The long-term maintenance burden of a complete fork is not quantified.", "A versioned fork implies work, but no primary evidence bounds or proves disproportionate cost.", "The bounded review did not establish a cost conclusion.", ("D1D_DECISION",)),
        "bounded_prototype_falsifiability": score("NOT_SUPPORTED", "The present evidence cannot define a bounded complete-fork prototype.", "The merged D1D-A integrity failure invalidates the consumer graph required to scope that prototype.", "The failed provenance-evidence gate affirmatively precludes a bounded complete-consumer prototype under the current record.", ("D1D_AUDIT_V6", "D1D_DECISION"), ("current_bounded_fork_not_falsifiable", "provenance_evidence_integrity_failure")),
        "amortized_set_inference_compatibility": score("SUPPORTED_WITH_QUALIFICATION", "A coherent generator could supply event sets to the fixed set-inference objective.", "This establishes the downstream data shape only, not a coherent generator measure.", "The fixed repository contract supports only that subset.", ("D1C",), ("fixed_signed_binary64_contract",)),
        "authorization_hierarchy_compatibility": score("NOT_SUPPORTED", "A fork prototype is incompatible with the current authorization hierarchy.", "The statement is scoped to the current failed readiness gate, not every future review.", "The merged decision affirmatively blocks prototype authorization at this gate.", ("D1D_DECISION",), ("authorization_hierarchy_blocks_prototype",)),
    }


def build_architecture_b_matrix() -> dict[str, dict[str, Any]]:
    d1d = ("D1D_DECISION",)
    return {
        "signed_scalar_preservation": score("NOT_SUPPORTED", "An external signed final weight does not preserve signed PDF scalars inside generator consumers.", "This applies to the final-weight architecture, not an unformulated replacement signed-kernel generator.", "The weight is applied after internal consumers and therefore does not carry or preserve their signed scalar inputs.", d1d, ("external_final_weight_cannot_repair_internal_selection",)),
        "nonnegative_probability_rate_validity": score("NOT_SUPPORTED", "A signed final weight cannot make an invalid internal probability or rate valid.", "The claim covers decisions made before a complete event history exists.", "The merged evidence affirmatively shows that post-hoc weighting cannot repair those internal measures.", d1d, ("external_final_weight_cannot_repair_internal_selection",)),
        "hard_process_coverage": score("SUPPORTED_WITH_QUALIFICATION", "Signed complete-event weights can encode NLO hard-process cancellations.", "MC@NLO establishes complete hard-event weights, not signed PDFs through all generator consumers.", "The primary papers support the hard-event subset only.", ("MCATNLO", "HERWIG_7_0"), ("negative_complete_event_weights", "nlo_matching_negative_complete_event_weights")),
        "isr_sudakov_coverage": score("NOT_SUPPORTED", "A final event weight does not replace ISR or Sudakov sampling kernels.", "This covers standard backward evolution executed before the final weight exists.", "Post-hoc weighting affirmatively cannot repair an already sampled ISR history.", d1d, ("external_final_weight_cannot_repair_internal_selection",)),
        "beam_remnant_coverage": score("NOT_SUPPORTED", "A final event weight does not replace beam-remnant selection semantics.", "This covers remnant choices made while constructing the event.", "Post-hoc weighting affirmatively cannot repair an already selected remnant history.", d1d, ("external_final_weight_cannot_repair_internal_selection",)),
        "flavor_categorical_selection": score("NOT_SUPPORTED", "A final event weight does not make an invalid flavor probability valid.", "This covers categorical choices made before event completion.", "Post-hoc weighting affirmatively cannot repair an already selected category.", d1d, ("external_final_weight_cannot_repair_internal_selection",)),
        "denominator_ratio_validity": score("NOT_SUPPORTED", "A final event weight does not repair invalid PDF denominators or ratios.", "This covers ratios used internally in sampling and evolution.", "The merged evidence places these computations before final weighting, so a final weight cannot change the invalid arithmetic.", d1d, ("external_final_weight_cannot_repair_internal_selection",)),
        "maximum_envelope_rejection_semantics": score("NOT_SUPPORTED", "A final event weight does not repair maxima, envelopes, vetoes, or rejection probabilities.", "This covers internal accept/reject construction.", "The event history is changed before a final weight exists, so the weight cannot repair the sampler.", d1d, ("external_final_weight_cannot_repair_internal_selection",)),
        "event_weight_semantics": score("SUPPORTED_WITH_QUALIFICATION", "Negative complete-event weights are established for NLO matching.", "They represent cancellations between complete histories, not signed internal PDF probabilities.", "The primary papers directly support only complete-event weight semantics.", ("MCATNLO", "LHEF_STANDARD"), ("negative_complete_event_weights", "signed_complete_event_weight_field")),
        "strict_support_no_extrapolation": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Strict support behavior for a new signed-kernel generator is undecided.", "Complete-event weight papers do not specify this PDF transport contract.", "The bounded review did not find primary evidence for the proposed internal architecture.", ("MCATNLO", "LHEF_STANDARD")),
        "alpha_s_consistency": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "alpha_s consistency for a new signed-kernel generator is undecided.", "Complete-event weight sources do not establish a signed PDF/alpha_s routing contract.", "The bounded review did not find sufficient primary evidence.", ("MCATNLO",)),
        "full_neutral_current_gamma_z_compatibility": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Complete gamma/Z/interference compatibility for a signed-kernel generator is undecided.", "The reviewed matching papers do not validate this fixed DIS contract.", "The bounded review did not find sufficient primary evidence.", ("MCATNLO",)),
        "deterministic_identity_and_provenance": score("SUPPORTED_WITH_QUALIFICATION", "Standardized event records can preserve complete-event weight provenance.", "They do not identify an absent signed internal generator implementation.", "The LHEF standard supports only the boundary-record subset.", ("LHEF_STANDARD",), ("signed_complete_event_weight_field",)),
        "thread_process_safety": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Thread and process safety for a signed-kernel generator is undecided.", "No implementation is identified.", "The bounded review did not find a primary implementation record.", ("MCATNLO",)),
        "build_deployment_reproducibility": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Build and deployment reproducibility for a signed-kernel generator is undecided.", "No implementation or source identity exists for this architecture.", "The bounded review did not find a reproducible implementation.", ("MCATNLO",)),
        "license_redistribution": score("NOT_APPLICABLE", "No software license criterion applies to the abstract mathematical architecture.", "A future implementation would require its own license review.", "This criterion is outside the current architecture scope."),
        "upstream_maintenance_burden": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Maintenance burden for an unimplemented signed-kernel generator is undecided.", "No implementation scope exists to cost.", "The bounded review did not establish a maintenance conclusion.", ("MCATNLO",)),
        "bounded_prototype_falsifiability": score("NOT_SUPPORTED", "The final-weight architecture is not a bounded test of internal signed sampling validity.", "A test of final event weights leaves the failing internal construction unchanged.", "The architecture therefore affirmatively fails to falsify the critical internal semantics it claims to repair.", ("D1D_DECISION",), ("external_final_weight_cannot_repair_internal_selection",)),
        "amortized_set_inference_compatibility": score("SUPPORTED_WITH_QUALIFICATION", "Set inference can consume weighted complete histories if their measure is coherent.", "No coherent signed internal generator measure is established here.", "Primary event-weight evidence supports only the downstream weighted-set subset.", ("MCATNLO", "LHEF_STANDARD"), ("negative_complete_event_weights", "signed_complete_event_weight_field")),
        "authorization_hierarchy_compatibility": score("NOT_SUPPORTED", "A signed-weight prototype is incompatible with the current authorization hierarchy.", "This applies at the current failed readiness gate.", "The merged decision affirmatively blocks prototype authorization.", ("D1D_DECISION",), ("authorization_hierarchy_blocks_prototype",)),
    }


def build_sherpa_matrix() -> dict[str, dict[str, Any]]:
    sherpa_docs = ("SHERPA_301_EXTERNAL_PDF_DOC", "SHERPA_301_SOURCE_COMMIT")
    return {
        "signed_scalar_preservation": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Signed PDF scalar preservation through Sherpa internals is undecided.", "The interface exposes Calculate/GetXPDF and runtime loading, but no sign-preservation dataflow.", "The bounded review did not find primary evidence covering hard, ISR, and remnant consumers.", sherpa_docs),
        "nonnegative_probability_rate_validity": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Validity of internal Sherpa probabilities and rates for signed PDFs is undecided.", "The manual documents ordinary generator modules, not a signed internal measure.", "The bounded review did not find a signed-rate or signed-kernel formulation.", ("SHERPA_301_MANUAL", "SHERPA_3_PAPER")),
        "hard_process_coverage": score("SUPPORTED_WITH_QUALIFICATION", "Sherpa 3.0.1 provides a lepton-proton EW DIS hard-process configuration.", "The HERA YAML fixes lepton/proton beams and an EW-order-two DIS process; it does not establish complete gamma/Z/interference closure.", "The pinned HERA source directly supports the configuration subset only.", ("SHERPA_301_HERA_YAML", "SHERPA_301_MANUAL"), ("hera_lepton_proton_dis_configuration", "hera_ew_order_two_hard_process", "lepton_hadron_dis_capability")),
        "isr_sudakov_coverage": score("SUPPORTED_WITH_QUALIFICATION", "Sherpa documents initial-state PDF configuration and shower integration.", "The sources establish ordinary ISR/shower plumbing but not valid signed Sudakov kernels.", "The pinned documentation and HERA YAML support only the ordinary-shower subset.", ("SHERPA_301_ISR_DOC", "SHERPA_301_HERA_YAML"), ("initial_state_pdf_configuration", "shower_pdf_variation_support", "hera_shower_configuration")),
        "beam_remnant_coverage": score("SUPPORTED_WITH_QUALIFICATION", "Sherpa includes a beam-remnant module in its event-generation stack.", "The manual establishes module existence, not signed-PDF remnant semantics.", "The versioned manual supports only the ordinary-remnant subset.", ("SHERPA_301_MANUAL",), ("beam_remnant_module_exists",)),
        "flavor_categorical_selection": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Flavor and categorical selection validity under signed PDFs is undecided.", "The reviewed interface and manuals do not trace signed values into categorical choices.", "The bounded review did not find sufficient primary evidence.", ("SHERPA_301_EXTERNAL_PDF_DOC", "SHERPA_301_MANUAL")),
        "denominator_ratio_validity": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "PDF denominator and ratio validity under signed inputs is undecided.", "The reviewed sources do not specify every internal ratio consumer.", "The bounded review did not find sufficient primary evidence.", ("SHERPA_301_EXTERNAL_PDF_DOC", "SHERPA_301_ISR_DOC")),
        "maximum_envelope_rejection_semantics": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Maximum, envelope, and rejection semantics under signed PDFs are undecided.", "Ordinary event-generation documentation does not define a signed replacement.", "The bounded review did not find sufficient primary evidence.", ("SHERPA_301_MANUAL", "SHERPA_3_PAPER")),
        "event_weight_semantics": score("SUPPORTED_WITH_QUALIFICATION", "Sherpa supports weighted complete events and MC@NLO configurations.", "This supports complete-event weights, not signed PDF probabilities inside the generator.", "The pinned manual, HERA YAML, and primary paper establish only the complete-event subset.", ("SHERPA_301_MANUAL", "SHERPA_301_HERA_YAML", "SHERPA_3_PAPER", "MCATNLO"), ("weighted_event_generation_modes", "mcatnlo_mode_configuration", "complete_event_negative_weights", "negative_complete_event_weights")),
        "strict_support_no_extrapolation": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Strict no-extrapolation enforcement for a custom Sherpa PDF is undecided.", "The external-PDF API documents accessors and loading but no fixed strict-support contract.", "The bounded review did not find sufficient primary evidence.", ("SHERPA_301_EXTERNAL_PDF_DOC",)),
        "alpha_s_consistency": score("SUPPORTED_WITH_QUALIFICATION", "Sherpa exposes PDF-related alpha_s routing configuration.", "The documented option does not establish consistency for the proposed signed custom provider across every consumer.", "The versioned ISR documentation supports only the routing-option subset.", ("SHERPA_301_ISR_DOC",), ("pdf_alpha_s_routing_option",)),
        "full_neutral_current_gamma_z_compatibility": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Complete neutral-current gamma/Z/interference compatibility is undecided.", "The HERA example establishes an EW DIS configuration but does not separately validate gamma, Z, interference, and charge-sign conventions.", "The bounded review did not find a primary source proving the complete required contract.", ("SHERPA_301_HERA_YAML", "SHERPA_301_MANUAL")),
        "deterministic_identity_and_provenance": score("SUPPORTED_WITH_QUALIFICATION", "Sherpa release source and the reviewed HERA configuration have immutable identities.", "Those identities do not define an absent signed custom provider and full configuration artifact.", "The pinned commit and file hashes support only source/configuration provenance.", ("SHERPA_301_SOURCE_COMMIT", "SHERPA_301_HERA_YAML"), ("source_commit_availability", "hera_example_source")),
        "thread_process_safety": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Thread and process safety of a custom signed PDF provider is undecided.", "The reviewed API does not make a concurrency guarantee for the proposed provider.", "The bounded review did not find sufficient primary evidence.", ("SHERPA_301_EXTERNAL_PDF_DOC", "SHERPA_301_SOURCE_COMMIT")),
        "build_deployment_reproducibility": score("SUPPORTED", "Sherpa 3.0.1 source and build instructions are pinned reproducibly.", "The claim is limited to obtaining and building the official release, not the absent signed provider.", "The exact source commit, CMake file hash, and versioned build manual directly establish this scope.", ("SHERPA_301_SOURCE_COMMIT", "SHERPA_301_MANUAL", "SHERPA_3_PAPER"), ("source_commit_availability", "cmake_build_definition", "versioned_build_instructions", "maintained_sherpa3_software")),
        "license_redistribution": score("SUPPORTED_WITH_QUALIFICATION", "Sherpa 3.0.1 includes pinned license and copying files.", "File identity is established; legal obligations for a redistributed modified integration are not interpreted here.", "The exact commit and file hashes support only license-text availability.", ("SHERPA_301_SOURCE_COMMIT",), ("license_files_present",)),
        "upstream_maintenance_burden": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Maintenance burden for a custom signed provider is undecided.", "Pinned maintained source establishes availability, not integration cost across releases.", "The bounded review did not find a quantified maintenance record.", ("SHERPA_301_SOURCE_COMMIT", "SHERPA_3_PAPER")),
        "bounded_prototype_falsifiability": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "A complete bounded signed-PDF Sherpa prototype is not yet defined.", "The loadable interface is source-backed, but the internal signed consumer and probability checks are not bounded.", "The bounded review did not find evidence sufficient to specify all falsification gates.", ("SHERPA_301_EXTERNAL_PDF_DOC", "SHERPA_301_SOURCE_COMMIT", "D1D_AUDIT_V6")),
        "amortized_set_inference_compatibility": score("SUPPORTED_WITH_QUALIFICATION", "Sherpa can produce weighted complete events that could form event sets.", "Compatibility requires a coherent signed generation measure, which is not established.", "The sources support only the event-record subset.", ("SHERPA_301_MANUAL", "MCATNLO"), ("weighted_event_generation_modes", "negative_complete_event_weights")),
        "authorization_hierarchy_compatibility": score("NOT_SUPPORTED", "A Sherpa prototype is incompatible with the current authorization hierarchy.", "This applies at the current failed D1D-A readiness gate.", "The merged decision affirmatively blocks any alternative-generator prototype now.", ("D1D_DECISION",), ("authorization_hierarchy_blocks_prototype",)),
    }


def build_herwig_matrix() -> dict[str, dict[str, Any]]:
    herwig = ("HERWIGPP_MANUAL", "HERWIG_7_0", "HERWIG_7_3")
    return {
        "signed_scalar_preservation": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Signed PDF scalar preservation through Herwig internals is undecided.", "The primary manual documents PDF handlers but no end-to-end signed dataflow.", "The bounded review did not find sufficient primary evidence.", herwig),
        "nonnegative_probability_rate_validity": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Internal probability and rate validity for signed PDFs is undecided.", "The reviewed papers describe ordinary shower and matching semantics, not signed PDF kernels.", "The bounded review did not find a mathematical replacement measure.", herwig),
        "hard_process_coverage": score("SUPPORTED_WITH_QUALIFICATION", "Herwig supports lepton-hadron hard scattering and an integrated hard-process stack.", "The papers do not validate the fixed signed-PDF neutral-current contract.", "The primary sources support only general lepton-hadron and hard-process coverage.", herwig, ("lepton_hadron_hard_process_capability", "hard_process_and_shower_stack", "lepton_hadron_support")),
        "isr_sudakov_coverage": score("SUPPORTED_WITH_QUALIFICATION", "Herwig implements backward-evolution showers and current ISR controls.", "The sources do not establish signed PDF ratios or signed Sudakov validity.", "The primary manual and release paper support only ordinary ISR coverage.", ("HERWIGPP_MANUAL", "HERWIG_7_3"), ("backward_evolution_shower", "isr_fsr_alpha_s_controls")),
        "beam_remnant_coverage": score("SUPPORTED_WITH_QUALIFICATION", "Herwig includes a beam-remnant model.", "The primary manual does not establish signed-PDF remnant semantics.", "The source supports only the ordinary-remnant subset.", ("HERWIGPP_MANUAL",), ("beam_remnant_model",)),
        "flavor_categorical_selection": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Flavor and categorical selection validity under signed PDFs is undecided.", "The bounded sources do not trace signed provider values through all choices.", "The bounded review did not find sufficient primary evidence.", herwig),
        "denominator_ratio_validity": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "PDF denominator and ratio validity under signed inputs is undecided.", "Backward-evolution documentation does not provide a signed replacement construction.", "The bounded review did not find sufficient primary evidence.", ("HERWIGPP_MANUAL",)),
        "maximum_envelope_rejection_semantics": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Maximum, envelope, and rejection semantics under signed PDFs are undecided.", "The reviewed papers do not specify a signed internal sampler.", "The bounded review did not find sufficient primary evidence.", herwig),
        "event_weight_semantics": score("SUPPORTED_WITH_QUALIFICATION", "Herwig/MC@NLO supports negative complete-event weights.", "This does not establish negative PDF probabilities or signed Sudakov kernels.", "The primary papers directly support only complete-event matching weights.", ("HERWIG_7_0", "MCATNLO"), ("nlo_matching_negative_complete_event_weights", "negative_complete_event_weights")),
        "strict_support_no_extrapolation": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Strict no-extrapolation behavior for a custom Herwig provider is undecided.", "The primary papers do not specify the fixed support contract.", "The bounded review did not find sufficient primary evidence.", herwig),
        "alpha_s_consistency": score("SUPPORTED_WITH_QUALIFICATION", "Herwig 7.3 documents separate ISR and FSR alpha_s controls.", "It does not prove consistency with the proposed signed custom provider across all consumers.", "The release paper supports only the exposed-control subset.", ("HERWIG_7_3",), ("isr_fsr_alpha_s_controls",)),
        "full_neutral_current_gamma_z_compatibility": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Complete neutral-current gamma/Z/interference compatibility is undecided.", "General lepton-hadron support does not prove the fixed component and convention checks.", "The bounded review did not find a primary validation of the complete contract.", ("HERWIGPP_MANUAL", "HERWIG_7_3")),
        "deterministic_identity_and_provenance": score("SUPPORTED_WITH_QUALIFICATION", "Versioned Herwig papers identify maintained release software.", "No exact signed-provider source/configuration identity is defined.", "The primary release record supports only software-version provenance.", ("HERWIG_7_3",), ("maintained_source_and_build_availability",)),
        "thread_process_safety": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Thread and process safety of a custom signed provider is undecided.", "The reviewed primary papers do not establish the proposed provider behavior.", "The bounded review did not find sufficient primary evidence.", herwig),
        "build_deployment_reproducibility": score("SUPPORTED", "Herwig 7.3 documents maintained public source and build availability.", "The claim is limited to the official software, not a signed-provider modification.", "The versioned primary software paper directly establishes this scope.", ("HERWIG_7_3",), ("maintained_source_and_build_availability",)),
        "license_redistribution": score("SUPPORTED_WITH_QUALIFICATION", "Herwig 7.3 declares GPLv3 software availability.", "The declaration is established; modified redistribution obligations are not interpreted here.", "The primary release paper supports only the license declaration subset.", ("HERWIG_7_3",), ("gplv3_license_declaration",)),
        "upstream_maintenance_burden": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "Maintenance burden for a signed Herwig provider is undecided.", "Maintained software availability does not quantify integration cost.", "The bounded review did not find a primary maintenance-cost record.", ("HERWIG_7_3",)),
        "bounded_prototype_falsifiability": score("PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "A complete bounded signed-PDF Herwig prototype is not yet defined.", "General PDF/shower interfaces exist, but complete signed-consumer gates are not bounded.", "The bounded review did not find sufficient primary evidence to specify the prototype.", herwig),
        "amortized_set_inference_compatibility": score("SUPPORTED_WITH_QUALIFICATION", "Herwig can produce weighted complete histories suitable for event-set representation.", "A coherent signed PDF generation measure is not established.", "The matching sources support only the weighted-event subset.", ("HERWIG_7_0", "MCATNLO"), ("nlo_matching_negative_complete_event_weights", "negative_complete_event_weights")),
        "authorization_hierarchy_compatibility": score("NOT_SUPPORTED", "A Herwig prototype is incompatible with the current authorization hierarchy.", "This applies at the current failed D1D-A readiness gate.", "The merged decision affirmatively blocks any alternative-generator prototype now.", ("D1D_DECISION",), ("authorization_hierarchy_blocks_prototype",)),
    }


def build_lhef_matrix() -> dict[str, dict[str, Any]]:
    lhef = ("LHEF_STANDARD",)
    return {
        "signed_scalar_preservation": score("NOT_SUPPORTED", "LHEF cannot preserve a signed PDF scalar through generator internals.", "The standard transports completed parton-level event records, not provider calls.", "The boundary format affirmatively does not carry the internal PDF scalar path.", lhef, ("boundary_not_generator",)),
        "nonnegative_probability_rate_validity": score("NOT_SUPPORTED", "LHEF cannot establish validity of upstream generator probabilities or rates.", "The file is written after those internal decisions.", "A downstream boundary affirmatively cannot repair an already constructed measure.", lhef, ("boundary_not_generator", "downstream_shower_delegation")),
        "hard_process_coverage": score("SUPPORTED_WITH_QUALIFICATION", "LHEF transports hard parton-level configurations and event weights.", "It does not generate or validate the fixed signed hard process.", "The standard directly supports the transport subset only.", lhef, ("parton_level_event_transport", "signed_complete_event_weight_field")),
        "isr_sudakov_coverage": score("NOT_SUPPORTED", "LHEF is not a complete ISR or Sudakov implementation.", "Backward evolution is delegated to the receiving generator.", "The standard affirmatively delegates this critical route component.", lhef, ("downstream_shower_delegation",)),
        "beam_remnant_coverage": score("NOT_SUPPORTED", "LHEF is not a complete beam-remnant implementation.", "Remnant construction is delegated downstream.", "The standard affirmatively delegates this critical route component.", lhef, ("downstream_shower_delegation",)),
        "flavor_categorical_selection": score("NOT_SUPPORTED", "LHEF cannot validate upstream flavor and categorical selection probabilities.", "It records the selected hard event after those choices.", "The boundary position affirmatively precludes repair of upstream categories.", lhef, ("boundary_not_generator",)),
        "denominator_ratio_validity": score("NOT_SUPPORTED", "LHEF cannot validate upstream PDF denominators or ratios.", "The standard has no provider or backward-evolution arithmetic interface.", "The boundary format affirmatively lacks this complete-route component.", lhef, ("boundary_not_generator",)),
        "maximum_envelope_rejection_semantics": score("NOT_SUPPORTED", "LHEF cannot validate upstream maxima, envelopes, vetoes, or rejection sampling.", "Those decisions precede the serialized event.", "The boundary position affirmatively precludes repair of upstream sampling.", lhef, ("boundary_not_generator",)),
        "event_weight_semantics": score("SUPPORTED", "LHEF directly carries signed complete-event weights.", "The claim is limited to complete parton-level event records.", "The standard and MC@NLO primary paper directly establish this scope.", ("LHEF_STANDARD", "MCATNLO"), ("signed_complete_event_weight_field", "negative_complete_event_weights")),
        "strict_support_no_extrapolation": score("NOT_APPLICABLE", "PDF support enforcement does not belong to the event-file boundary.", "It remains the responsibility of the event producer and receiving generator.", "This criterion is outside the transport-format scope."),
        "alpha_s_consistency": score("NOT_APPLICABLE", "alpha_s routing does not belong to the event-file boundary.", "Producer and receiver retain their own coupling configuration.", "This criterion is outside the transport-format scope."),
        "full_neutral_current_gamma_z_compatibility": score("NOT_SUPPORTED", "LHEF cannot establish complete neutral-current gamma/Z/interference generation compatibility.", "It transports whatever hard event the producer supplied.", "The boundary format affirmatively lacks the generator-level validation component.", lhef, ("boundary_not_generator",)),
        "deterministic_identity_and_provenance": score("SUPPORTED", "The versioned LHEF standard defines a deterministic interchange record structure.", "Generator and PDF identities still require explicit fields supplied by the producer.", "The standard directly establishes the interchange scope.", lhef, ("parton_level_event_transport",)),
        "thread_process_safety": score("NOT_APPLICABLE", "Generator concurrency does not belong to the serialized event format.", "It is an implementation concern of producer and receiver.", "This criterion is outside the transport-format scope."),
        "build_deployment_reproducibility": score("NOT_APPLICABLE", "A file standard has no generator build or deployment.", "Producer and receiver builds are separate.", "This criterion is outside the transport-format scope."),
        "license_redistribution": score("NOT_APPLICABLE", "Generator software redistribution does not belong to the interchange-format candidate.", "Any implementation has its own license.", "This criterion is outside the transport-format scope."),
        "upstream_maintenance_burden": score("NOT_APPLICABLE", "Generator maintenance burden does not belong to the interchange format alone.", "Producer and receiver maintenance remain separate.", "This criterion is outside the transport-format scope."),
        "bounded_prototype_falsifiability": score("NOT_SUPPORTED", "An LHEF-only prototype cannot falsify complete signed generator coupling.", "It tests a boundary after hard-event construction and delegates ISR/remnants.", "The standard affirmatively lacks the internal route being tested.", lhef, ("boundary_not_generator", "downstream_shower_delegation")),
        "amortized_set_inference_compatibility": score("SUPPORTED_WITH_QUALIFICATION", "Signed LHEF event weights can represent a weighted empirical event set.", "Compatibility still requires a coherent producer and an inference method that consumes signed weights explicitly.", "The standard supports only the record-level subset.", ("LHEF_STANDARD", "MCATNLO"), ("signed_complete_event_weight_field", "negative_complete_event_weights")),
        "authorization_hierarchy_compatibility": score("NOT_SUPPORTED", "An LHEF transport prototype is incompatible with the current authorization hierarchy.", "This applies at the current failed D1D-A readiness gate.", "The merged decision affirmatively blocks a transport prototype now.", ("D1D_DECISION",), ("authorization_hierarchy_blocks_prototype",)),
    }


def build_architecture_d_matrix() -> dict[str, dict[str, Any]]:
    row = {
        criterion: score("NOT_APPLICABLE", f"{criterion} is not decided by an interim operational pause.", "The pause makes no generator-architecture claim.", "This criterion is outside the interim-policy scope.")
        for criterion in CRITERIA
    }
    row["deterministic_identity_and_provenance"] = score("SUPPORTED", "The interim pause preserves the immutable negative evidence lineage.", "It records no new architecture identity.", "The merged decision directly establishes the precedence record.", ("D1D_DECISION",), ("provenance_evidence_integrity_failure",))
    row["upstream_maintenance_burden"] = score("SUPPORTED_WITH_QUALIFICATION", "The interim pause avoids immediate generator-integration maintenance work.", "It does not prove that every future route has disproportionate cost.", "The current failed readiness gate supports only pausing present work.", ("D1D_DECISION",), ("prototype_authorization_blocked",))
    row["amortized_set_inference_compatibility"] = score("SUPPORTED_WITH_QUALIFICATION", "The pause protects the fixed inference contract from an invalid generator measure.", "It leaves the generator-coupling dependency unresolved.", "The repository evidence supports preservation of the current boundary only.", ("D1C", "D1D_DECISION"), ("fixed_signed_binary64_contract", "prototype_authorization_blocked"))
    row["authorization_hierarchy_compatibility"] = score("SUPPORTED", "The interim pause exactly follows the current non-authorization hierarchy.", "It grants no implementation or reopen authority.", "The merged decision directly requires prototype blocking.", ("D1D_DECISION",), ("authorization_hierarchy_blocks_prototype",))
    return row


def route_state_from_row(row: dict[str, dict[str, Any]]) -> str:
    statuses = [row[criterion]["status"] for criterion in CRITICAL_CRITERIA]
    if any(status in {"NOT_SUPPORTED", "NOT_APPLICABLE"} for status in statuses):
        return "COHERENT_BOUNDED_PATH_NOT_SUPPORTED"
    if all(status == "SUPPORTED" for status in statuses):
        return "COHERENT_BOUNDED_PATH_SUPPORTED"
    if any(status in {"PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "SUPPORTED_WITH_QUALIFICATION"} for status in statuses):
        return "COHERENT_BOUNDED_PATH_POSSIBLE_WITH_EVIDENCE_GAPS"
    raise DecisionError("critical criterion statuses do not determine a route state")


def critical_status_counts(row: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in ALLOWED_SCORES}
    for criterion in CRITICAL_CRITERIA:
        counts[row[criterion]["status"]] += 1
    return dict(sorted(counts.items()))


def aggregate_status(statuses: list[str]) -> str:
    applicable = [status for status in statuses if status != "NOT_APPLICABLE"]
    if not applicable:
        return "NOT_APPLICABLE"
    if all(status == "SUPPORTED" for status in applicable):
        return "SUPPORTED"
    if all(status == "NOT_SUPPORTED" for status in applicable):
        return "NOT_SUPPORTED"
    if "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE" in applicable:
        return "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE"
    return "SUPPORTED_WITH_QUALIFICATION"


def aggregate_candidate_matrices(candidate_matrices: dict[str, dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    aggregate: dict[str, dict[str, Any]] = {}
    for criterion in CRITERIA:
        cells = [candidate_matrices[candidate_id][criterion] for candidate_id in CANDIDATE_IDS]
        statuses = [cell["status"] for cell in cells]
        status = aggregate_status(statuses)
        sources = tuple(sorted({source for cell in cells for source in cell["source_ids"]}))
        claim_keys = tuple(sorted({key for cell in cells for key in cell["claim_keys"]}))
        rendered = ", ".join(f"{candidate_id}={candidate_matrices[candidate_id][criterion]['status']}" for candidate_id in CANDIDATE_IDS)
        if status == "SUPPORTED":
            claim = f"All applicable bounded candidates directly support {criterion}."
            rationale = f"Conservative aggregation returns SUPPORTED because every applicable candidate is SUPPORTED: {rendered}."
        elif status == "SUPPORTED_WITH_QUALIFICATION":
            claim = f"At least one bounded candidate supports a subset of {criterion}, but support is not complete across candidates."
            rationale = f"Conservative aggregation returns SUPPORTED_WITH_QUALIFICATION for mixed supported, qualified, or incompatible evidence: {rendered}."
        elif status == "NOT_SUPPORTED":
            claim = f"Every applicable bounded candidate affirmatively fails {criterion}."
            rationale = f"Affirmative incompatibility is established because every applicable candidate is NOT_SUPPORTED: {rendered}."
        elif status == "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE":
            claim = f"The bounded candidate review cannot decide {criterion} for Architecture C."
            rationale = f"Conservative aggregation preserves an evidence gap because at least one candidate is PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE: {rendered}."
        else:
            claim = f"No bounded candidate applies {criterion}."
            rationale = f"Conservative aggregation returns NOT_APPLICABLE because every candidate is outside scope: {rendered}."
        aggregate[criterion] = score(
            status,
            claim,
            f"Candidate-level inputs: {rendered}.",
            rationale,
            sources,
            claim_keys,
            disproportionate_cost_evidence=all(cell["disproportionate_cost_evidence"] for cell in cells),
        )
        aggregate[criterion]["candidate_status_inputs"] = {
            candidate_id: candidate_matrices[candidate_id][criterion]["status"] for candidate_id in CANDIDATE_IDS
        }
    return aggregate


def architecture_c_route_state(candidate_states: dict[str, str]) -> str:
    if any(state == "COHERENT_BOUNDED_PATH_SUPPORTED" for state in candidate_states.values()):
        return "COHERENT_BOUNDED_PATH_SUPPORTED"
    if any(state == "COHERENT_BOUNDED_PATH_POSSIBLE_WITH_EVIDENCE_GAPS" for state in candidate_states.values()):
        return "COHERENT_BOUNDED_PATH_POSSIBLE_WITH_EVIDENCE_GAPS"
    return "COHERENT_BOUNDED_PATH_NOT_SUPPORTED"


def recompute_route_states(value: dict[str, Any]) -> dict[str, Any]:
    matrix = value["decision_criteria"]["matrix"]
    candidate_matrices = value["architecture_assessments"][ARCH_C]["candidate_matrices"]
    candidate_states = {candidate_id: route_state_from_row(candidate_matrices[candidate_id]) for candidate_id in CANDIDATE_IDS}
    architecture_states = {
        ARCH_A: route_state_from_row(matrix[ARCH_A]),
        ARCH_B: route_state_from_row(matrix[ARCH_B]),
        ARCH_C: architecture_c_route_state(candidate_states),
    }
    return {"architecture_route_states": architecture_states, "candidate_route_states": candidate_states}


def route_has_disproportionate_cost_support(row: dict[str, dict[str, Any]]) -> bool:
    return all(
        row[criterion]["status"] == "NOT_SUPPORTED"
        and row[criterion]["disproportionate_cost_evidence"] is True
        for criterion in COST_CRITERIA
    )


def recompute_decision_rule(value: dict[str, Any]) -> dict[str, bool]:
    states = recompute_route_states(value)
    architecture_states = states["architecture_route_states"]
    possible_states = {
        "COHERENT_BOUNDED_PATH_SUPPORTED",
        "COHERENT_BOUNDED_PATH_POSSIBLE_WITH_EVIDENCE_GAPS",
    }
    possible = any(state in possible_states for state in architecture_states.values())
    candidate_matrices = value["architecture_assessments"][ARCH_C]["candidate_matrices"]
    matrix = value["decision_criteria"]["matrix"]
    unresolved_critical = False
    for architecture in (ARCH_A, ARCH_B):
        if architecture_states[architecture] == "COHERENT_BOUNDED_PATH_POSSIBLE_WITH_EVIDENCE_GAPS":
            unresolved_critical |= any(matrix[architecture][criterion]["status"] in {"PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "SUPPORTED_WITH_QUALIFICATION"} for criterion in CRITICAL_CRITERIA)
    for candidate_id, state in states["candidate_route_states"].items():
        if state == "COHERENT_BOUNDED_PATH_POSSIBLE_WITH_EVIDENCE_GAPS":
            unresolved_critical |= any(candidate_matrices[candidate_id][criterion]["status"] in {"PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "SUPPORTED_WITH_QUALIFICATION"} for criterion in CRITICAL_CRITERIA)
    return {
        "architecture_comparison_ready": value["precedence"]["ARCHITECTURE_COMPARISON_READY"],
        "disproportionate_cost_supported_for_all_routes": all(route_has_disproportionate_cost_support(matrix[architecture]) for architecture in (ARCH_A, ARCH_B, ARCH_C)),
        "mandatory_d1d_a_gate_passed": value["precedence"]["D1D_A_FINAL_DECISION"] == "PASS",
        "no_current_architecture_has_coherent_bounded_path": not possible,
        "potentially_coherent_route_remains": possible,
        "primary_or_mathematical_evidence_insufficient": unresolved_critical,
    }


def derive_decision(rule: dict[str, bool]) -> str:
    if rule["potentially_coherent_route_remains"]:
        if rule["no_current_architecture_has_coherent_bounded_path"]:
            raise DecisionError("decision rule is logically inconsistent")
        if not (rule["primary_or_mathematical_evidence_insufficient"] or not rule["mandatory_d1d_a_gate_passed"] or not rule["architecture_comparison_ready"]):
            raise DecisionError("a coherent route exists without an allowed non-authorizing rationale")
        return "INCONCLUSIVE"
    if not rule["no_current_architecture_has_coherent_bounded_path"]:
        raise DecisionError("decision rule is logically inconsistent")
    if rule["disproportionate_cost_supported_for_all_routes"]:
        return "DO_NOT_AUTHORIZE_FURTHER_GENERATOR_PROTOTYPE"
    raise DecisionError("no coherent route remains but all-route terminal-cost evidence is insufficient")


def policy_for_decision(decision: str) -> str:
    if decision == "INCONCLUSIVE":
        return "PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION"
    return "TERMINAL_STOP_FOR_FIXED_CONTRACT"


def build_decision() -> dict[str, Any]:
    candidate_matrices = {
        CANDIDATE_IDS[0]: build_sherpa_matrix(),
        CANDIDATE_IDS[1]: build_herwig_matrix(),
        CANDIDATE_IDS[2]: build_lhef_matrix(),
    }
    matrix = {
        ARCH_A: build_architecture_a_matrix(),
        ARCH_B: build_architecture_b_matrix(),
        ARCH_C: aggregate_candidate_matrices(candidate_matrices),
        ARCH_D: build_architecture_d_matrix(),
    }
    value: dict[str, Any] = {
        "architecture_assessments": {
            ARCH_A: {
                "assessment": "CURRENT_BOUNDED_FORK_PATH_NOT_SUPPORTED",
                "distinctions": {
                    "bypass_reader_interface": "Does not resolve downstream sign-sensitive consumers or provide a validated dataflow contract.",
                    "downstream_algorithm_redesign": "Would require reviewed semantics for hard-process, ISR, remnant, flavor selection, ratios, maxima, envelopes, and cumulative selection.",
                    "public_reader_change": "Already established insufficient by D1C and D1D-A.",
                    "versioned_fork_maintenance": "Requires a separately evidenced maintenance and redistribution assessment.",
                },
            },
            ARCH_B: {
                "assessment": "FINAL_EVENT_WEIGHT_PATH_NOT_SUPPORTED",
                "distinctions": {
                    "ordinary_positive_probability_generation": "Requires valid nonnegative sampling probabilities and rates.",
                    "signed_event_samples": "Represent cancellations between complete weighted histories.",
                    "signed_final_event_weight": "Cannot retroactively repair internal sampling decisions.",
                    "signed_kernels_or_sudakovs": "Require a reviewed mathematical formulation not present in this record.",
                    "signed_matrix_element_contributions": "Do not establish signed PDFs through all generator consumers.",
                    "weighted_empirical_event_sets": "Require a coherent event measure before set inference.",
                },
            },
            ARCH_C: {
                "aggregate_rule": {
                    "NOT_APPLICABLE": "Return only when every candidate is NOT_APPLICABLE.",
                    "NOT_SUPPORTED": "Return only when every applicable candidate is NOT_SUPPORTED.",
                    "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE": "Preserve an evidence gap whenever any candidate is unavailable and the all-supported/all-failed rules do not apply.",
                    "SUPPORTED": "Return only when every applicable candidate is SUPPORTED.",
                    "SUPPORTED_WITH_QUALIFICATION": "Return for remaining mixed supported, qualified, or incompatible evidence.",
                },
                "candidate_matrices": candidate_matrices,
                "candidate_route_states": {},
            },
            ARCH_D: {
                "assessment": "INTERIM_PAUSE_SUPPORTED_BY_FAILED_READINESS_GATE",
                "interpretation": "This is an operational pause, not a selected terminal-stop decision.",
            },
        },
        "authorization": {flag: False for flag in AUTHORIZATION_FLAGS},
        "current_operational_policy": "",
        "decision": "",
        "decision_criteria": {
            "criterion_order": list(CRITERIA),
            "critical_criteria": list(CRITICAL_CRITERIA),
            "matrix": matrix,
            "score_semantics": SCORE_SEMANTICS,
        },
        "decision_rule": {},
        "dependencies": {"blocked_issue": 10, "planning_issue": 42, "project_fields_must_remain_unchanged": True},
        "evaluated_evidence": {
            "primary_sources": build_sources(),
            "source_pinning_policy": "SUPPORTED, qualified support, and affirmative incompatibility require source identities pinned by immutable repository hash, versioned content SHA-256, arXiv version plus PDF hash, or exact Git commit plus file hashes.",
        },
        "failure_scope": [
            "No generator architecture or prototype is authorized for the fixed current contract.",
            "The minimal public-reader patch remains insufficient.",
            "The rejected provenance slice remains diagnostic rather than readiness evidence.",
        ],
        "fixed_scientific_contract": {
            "amortized_objective": "p(theta_PDF | D) for a set of events D",
            "event_sampling": "shape-only fixed-N conditional event distribution",
            "generator_consistency": ["hard_process", "ISR_backward_evolution", "beam_remnant"],
            "pdf_family": "ct18nlo_two_parameter_boundary_v2",
            "scalar_contract": "signed binary64 x*f with strict support and no extrapolation",
            "theta_box": {"delta_v": [-0.2, 0.2], "lambda_sea": [-0.25, 0.25]},
        },
        "next_step": "SCIENTIFIC_REVIEW_OF_EVIDENCE_DERIVED_D1D_B_DECISION",
        "non_failure_scope": [
            "The interim pause is not a universal impossibility theorem.",
            "Possible routes with evidence gaps are not treated as supported architectures.",
            "Negative complete-event weights are not treated as signed internal PDF kernels.",
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
            {"authorization_granted": False, "condition": "A pinned primary-source generator interface with proven signed scalar, rate, ISR, remnant, and event-weight semantics."},
            {"authorization_granted": False, "condition": "An independently validated complete consumer and dataflow graph for the proposed coupling."},
            {"authorization_granted": False, "condition": "A separately reviewed and approved change to the PDF-family or inference contract."},
        ],
        "route_states": {},
        "schema_version": SCHEMA,
        "unresolved_evidence": [
            "No complete independently validated PDF-consumer graph is available.",
            "No reviewed signed-kernel or signed-Sudakov probability construction is available.",
            "Sherpa and Herwig sources do not establish signed scalar preservation through hard process, ISR, and remnants.",
            "Complete neutral-current gamma/Z/interference compatibility is not established for either full-generator candidate.",
            "Maintenance, concurrency, strict-support, and bounded-prototype evidence remains incomplete for possible routes.",
        ],
        "validation": {
            "artifact_is_deterministically_generated": True,
            "command": "python3 scripts/phase1bd_d1d_terminal_decision.py --validate",
            "derivation_recomputed_from_serialized_evidence": True,
            "physics_execution_performed": False,
        },
    }
    states = recompute_route_states(value)
    value["route_states"] = states["architecture_route_states"]
    value["architecture_assessments"][ARCH_C]["candidate_route_states"] = states["candidate_route_states"]
    value["architecture_assessments"][ARCH_C]["candidate_critical_status_counts"] = {
        candidate_id: critical_status_counts(candidate_matrices[candidate_id]) for candidate_id in CANDIDATE_IDS
    }
    rule = recompute_decision_rule(value)
    decision = derive_decision(rule)
    value["decision_rule"] = rule
    value["decision"] = decision
    value["current_operational_policy"] = policy_for_decision(decision)
    return value


def is_hex(value: Any, length: int) -> bool:
    return isinstance(value, str) and len(value) == length and all(char in "0123456789abcdef" for char in value)


def validate_source(source_id: str, source: dict[str, Any]) -> None:
    required = {
        "canonical_url",
        "claim_scope",
        "content_sha256",
        "document_or_software_version",
        "immutable_identifier",
        "retrieval_utc_date",
        "source_id",
        "source_identity_status",
        "source_kind",
    }
    require(required <= set(source), f"source metadata incomplete: {source_id}")
    require(source["source_id"] == source_id, f"source ID mismatch: {source_id}")
    require(source["retrieval_utc_date"] == RETRIEVAL_UTC_DATE, f"source retrieval date mismatch: {source_id}")
    require(source["source_identity_status"] in {"PINNED", "SOURCE_IDENTITY_UNRESOLVED"}, f"invalid source identity status: {source_id}")
    require("/master" not in source["canonical_url"] and "/tree/master" not in source["canonical_url"], f"mutable master source URL: {source_id}")
    if source["source_identity_status"] == "PINNED":
        if source["source_kind"] == "OFFICIAL_SOURCE_REPOSITORY_COMMIT":
            require(is_hex(source.get("repository_commit_sha"), 40), f"source commit is not pinned: {source_id}")
            require(source.get("pinned_files"), f"source commit lacks pinned files: {source_id}")
            require(all(is_hex(item.get("sha256"), 64) and item.get("path") for item in source["pinned_files"]), f"source file hash invalid: {source_id}")
        else:
            require(is_hex(source["content_sha256"], 64), f"source content hash is not pinned: {source_id}")
    if source["source_kind"] == "ARXIV_PRIMARY_PAPER":
        require(re.fullmatch(r"v[1-9][0-9]*", source["document_or_software_version"]), f"arXiv version invalid: {source_id}")
        require(source["document_or_software_version"] in source["canonical_url"], f"arXiv URL is not versioned: {source_id}")
        require(source.get("arxiv_identifier"), f"arXiv identifier missing: {source_id}")
        require(source.get("canonical_abstract_url"), f"arXiv abstract URL missing: {source_id}")


def validate_score_cell(
    location: str,
    cell: dict[str, Any],
    sources: dict[str, dict[str, Any]],
    *,
    aggregate: bool = False,
) -> None:
    required = {
        "claim",
        "claim_keys",
        "disproportionate_cost_evidence",
        "epistemic_basis",
        "evidence_scope",
        "rationale",
        "source_ids",
        "status",
    }
    require(required <= set(cell), f"score cell incomplete: {location}")
    status = cell["status"]
    require(status in ALLOWED_SCORES, f"invalid score: {location}")
    require(cell["epistemic_basis"] == EPISTEMIC_BASIS[status], f"score epistemic basis mismatch: {location}")
    require(all(isinstance(cell[field], str) and cell[field].strip() for field in ("claim", "evidence_scope", "rationale")), f"score prose missing: {location}")
    require(all(source_id in sources for source_id in cell["source_ids"]), f"unknown source ID: {location}")
    if status in {"SUPPORTED", "SUPPORTED_WITH_QUALIFICATION", "NOT_SUPPORTED"}:
        require(cell["source_ids"], f"evidence-bearing score lacks sources: {location}")
        require(cell["claim_keys"], f"evidence-bearing score lacks claim keys: {location}")
        for source_id in cell["source_ids"]:
            require(sources[source_id]["source_identity_status"] == "PINNED", f"supported score uses unpinned source: {location}/{source_id}")
        supported_claims = {claim for source_id in cell["source_ids"] for claim in sources[source_id]["claim_scope"]}
        require(set(cell["claim_keys"]) <= supported_claims, f"score claim exceeds cited source scope: {location}")
    if status == "NOT_SUPPORTED":
        require(not MISSING_EVIDENCE_RE.search(cell["rationale"]), f"NOT_SUPPORTED rationale only reports missing evidence: {location}")
        require(AFFIRMATIVE_INCOMPATIBILITY_RE.search(cell["rationale"]), f"NOT_SUPPORTED rationale lacks affirmative incompatibility: {location}")
    if status == "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE":
        require(not AFFIRMATIVE_INCOMPATIBILITY_RE.search(cell["rationale"]), f"evidence-gap rationale claims affirmative incompatibility: {location}")
        require(MISSING_EVIDENCE_RE.search(cell["rationale"]), f"evidence-gap rationale does not state the gap: {location}")
    if status == "NOT_APPLICABLE":
        require(not cell["source_ids"] and not cell["claim_keys"], f"NOT_APPLICABLE cell cites evidence: {location}")
    if cell["disproportionate_cost_evidence"]:
        require(status == "NOT_SUPPORTED", f"cost evidence requires affirmative NOT_SUPPORTED: {location}")
    if aggregate:
        require(set(cell.get("candidate_status_inputs", {})) == set(CANDIDATE_IDS), f"aggregate cell lacks candidate inputs: {location}")


def validate_decision(value: dict[str, Any]) -> None:
    require(value.get("schema_version") == SCHEMA, "wrong schema_version")
    require(value.get("decision") in ALLOWED_DECISIONS, "decision is not an allowed outcome")
    require(value["decision_criteria"].get("score_semantics") == SCORE_SEMANTICS, "score-semantics contract changed")
    require(tuple(value["decision_criteria"].get("criterion_order", ())) == CRITERIA, "the exact twenty criteria are required")
    require(tuple(value["decision_criteria"].get("critical_criteria", ())) == CRITICAL_CRITERIA, "critical criteria changed")

    precedence = value["precedence"]
    require(precedence == {
        "ARCHITECTURE_COMPARISON_READY": False,
        "D1C_FINAL_DECISION": "FAIL",
        "D1D_A_FAILED_GATE": "provenance_evidence_integrity",
        "D1D_A_FINAL_DECISION": "FAIL",
        "MINIMAL_PUBLIC_READER_PATCH": "INSUFFICIENT",
        "PROVENANCE_SLICE_V1_DECISION": "FAIL",
        "PROVENANCE_SLICE_V1_STATUS": "REJECTED_DIAGNOSTIC",
    }, "immutable precedence changed")

    sources = value["evaluated_evidence"]["primary_sources"]
    for source_id, source in sources.items():
        validate_source(source_id, source)

    matrix = value["decision_criteria"]["matrix"]
    require(set(matrix) == set(ARCHITECTURES), "all four architecture rows are required")
    for architecture in ARCHITECTURES:
        require(set(matrix[architecture]) == set(CRITERIA), f"architecture criterion row incomplete: {architecture}")
        for criterion in CRITERIA:
            validate_score_cell(f"{architecture}/{criterion}", matrix[architecture][criterion], sources, aggregate=architecture == ARCH_C)

    c_assessment = value["architecture_assessments"][ARCH_C]
    candidate_matrices = c_assessment["candidate_matrices"]
    require(set(candidate_matrices) == set(CANDIDATE_IDS), "candidate matrix set changed")
    for candidate_id in CANDIDATE_IDS:
        require(set(candidate_matrices[candidate_id]) == set(CRITERIA), f"candidate criterion row incomplete: {candidate_id}")
        for criterion in CRITERIA:
            validate_score_cell(f"{candidate_id}/{criterion}", candidate_matrices[candidate_id][criterion], sources)

    expected_aggregate = aggregate_candidate_matrices(candidate_matrices)
    require(matrix[ARCH_C] == expected_aggregate, "Architecture C aggregate differs from candidate aggregation")

    recomputed_states = recompute_route_states(value)
    require(value["route_states"] == recomputed_states["architecture_route_states"], "serialized architecture route state differs from recomputation")
    require(c_assessment["candidate_route_states"] == recomputed_states["candidate_route_states"], "serialized candidate route state differs from recomputation")
    require(c_assessment["candidate_critical_status_counts"] == {candidate_id: critical_status_counts(candidate_matrices[candidate_id]) for candidate_id in CANDIDATE_IDS}, "candidate critical counts differ from recomputation")
    for route, state in value["route_states"].items():
        require(state in ROUTE_STATES, f"invalid route state: {route}")

    sherpa = candidate_matrices[CANDIDATE_IDS[0]]
    require(sherpa["hard_process_coverage"]["status"] in {"SUPPORTED_WITH_QUALIFICATION", "PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE", "NOT_SUPPORTED"}, "Sherpa hard-process evidence is overstated")
    gamma = sherpa["full_neutral_current_gamma_z_compatibility"]
    explicit_gamma_claim = any("complete_nc_gamma_z_interference_contract" in sources[source_id]["claim_scope"] for source_id in gamma["source_ids"])
    if gamma["status"] in {"SUPPORTED", "SUPPORTED_WITH_QUALIFICATION"}:
        require(explicit_gamma_claim, "Sherpa gamma/Z support lacks an explicit complete-contract source")
    require(not (gamma["status"] == "SUPPORTED" and gamma["source_ids"] == ["SHERPA_301_HERA_YAML"]), "Sherpa HERA example alone cannot prove complete gamma/Z compatibility")

    recomputed_rule = recompute_decision_rule(value)
    require(value["decision_rule"] == recomputed_rule, "serialized decision-rule booleans differ from recomputation")
    expected_decision = derive_decision(recomputed_rule)
    require(value["decision"] == expected_decision, "serialized decision differs from evidence-derived decision")
    expected_policy = policy_for_decision(expected_decision)
    require(value["current_operational_policy"] == expected_policy, "operational policy differs from derived decision")
    if expected_decision == "INCONCLUSIVE":
        require(recomputed_rule["potentially_coherent_route_remains"], "INCONCLUSIVE requires a supported or evidence-gap route")
        require(value["architecture_assessments"][ARCH_D]["assessment"] == "INTERIM_PAUSE_SUPPORTED_BY_FAILED_READINESS_GATE", "INCONCLUSIVE is represented as terminal stop")
    else:
        require(recomputed_rule["no_current_architecture_has_coherent_bounded_path"], "terminal stop requires no possible route")
        require(recomputed_rule["disproportionate_cost_supported_for_all_routes"], "terminal stop lacks all-route cost evidence")

    authorization = value["authorization"]
    require(set(authorization) == set(AUTHORIZATION_FLAGS), "authorization flag set differs from contract")
    require(all(authorization[flag] is False for flag in AUTHORIZATION_FLAGS), "an authorization flag became true")
    require(all(item.get("authorization_granted") is False for item in value["reopen_conditions"]), "a reopen condition grants authorization")
    require(not any(text.startswith("AUTHORIZE_SEPARATE_BOUNDED_") for text in walk_strings(value)), "an authorizing outcome appears")


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
