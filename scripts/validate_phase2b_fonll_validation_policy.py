#!/usr/bin/env python3
"""Validate the Phase 2B FONLL validation policy statically."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_fonll_validation_policy_v1.json"
SCHEMA = "partonsbi.phase2b.fonll-validation-policy.v1"

OUTCOMES = {
    "FPD1_REQUIRE_EXECUTABLE_FONLL_REFERENCE",
    "FPD2_ACCEPT_EXECUTABLE_FONLL_GAP_AS_DISCLOSED_LIMITATION",
    "FPD3_ADOPT_HYBRID_COMPONENT_VALIDATION_POLICY",
    "FPD4_FONLL_REFERENCE_POLICY_REMAINS_UNRESOLVED",
}
EXPECTED_OUTCOME = "FPD3_ADOPT_HYBRID_COMPONENT_VALIDATION_POLICY"
DISCLOSURE_OUTCOMES = {
    "DISCLOSURE_SCIENTIFICALLY_SUFFICIENT",
    "DISCLOSURE_INSUFFICIENT_EXECUTABLE_ORACLE_REQUIRED",
    "DISCLOSURE_POLICY_UNRESOLVED",
}
PROPORTIONALITY_OUTCOMES = {
    "PROPORTIONATE_REQUIRED_GATE",
    "SCIENTIFICALLY_DESIRABLE_BUT_NOT_REQUIRED_GATE",
    "INSUFFICIENT_INFORMATION",
}
TERMINOLOGY_OUTCOMES = {
    "TERMINOLOGY_REPLACEMENT_JUSTIFIED",
    "TERMINOLOGY_REPLACEMENT_NOT_JUSTIFIED",
    "TERMINOLOGY_REPLACEMENT_UNRESOLVED",
}
V4_OUTCOMES = {
    "V4_SUCCESSOR_PLANNING_NOW_WARRANTED",
    "V4_STILL_BLOCKED_BY_FONLL_POLICY",
    "V4_BLOCKED_FOR_OTHER_REASON",
}
CONTRACT_IMPACT_CODES = {
    "DISAMBIGUATES_EXISTING_CONTRACT",
    "NARROWS_CLAIM_BOUNDARY",
    "REPLACES_VALIDATION_GATE_SEMANTICS",
    "CHANGES_RESEARCH_QUESTION",
    "UNCHANGED",
}

STARTING_MAIN_SHA = "41e1600c369b9b655b84eae9c9a0b6a1e2384fbe"

EXPECTED_PREDECESSORS = {
    "fonll_a_amendment": (
        "docs/reduced_nc_dis/contracts/phase2_fonll_a_contract_amendment.json",
        "10cf19fedcdfe1b94e18ff89d1ae09514a31b8e0f6b055beeb729d61b6c32da8",
    ),
    "preauthorization_v3": (
        "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v3.json",
        "78a029686489e9712e65ef6f9df3263b4821f96de0ee9873a910dee31f307e06",
    ),
    "blocker_resolution_v1": (
        "docs/reduced_nc_dis/contracts/phase2b_blocker_resolution_v1.json",
        "d66a1bbcb67b7105f489233bfd292c7064bcda35ef8c6f8dbc0dec41aa6da8de",
    ),
    "numerical_policy_decision_v1": (
        "docs/reduced_nc_dis/contracts/phase2b_numerical_policy_decision_v1.json",
        "a855dfeb49a4f6f8e26804c5fac8708691fa9c345be57acfc5efa55e1864830c",
    ),
}

EVIDENCE_CLASSES = {
    "E1_EXECUTABLE_INDEPENDENT_ORACLE",
    "E2_PUBLISHED_INDEPENDENT_NUMERICAL_BENCHMARK",
    "E3_INDEPENDENT_ANALYTIC_CHECK",
    "E4_SEMANTIC_IMPLEMENTATION_CROSSCHECK",
    "E5_SOURCE_PROVENANCE_ONLY",
    "E6_INTERNAL_SELF_CONVERGENCE",
}
NODE_CLASS_TOKENS = {"E1", "E2", "E3", "E4", "E5", "E6"}

EXPECTED_GRAPH_NODES = {
    "complete_nc_observable",
    "electroweak_assembly",
    "massless_coefficient_contribution",
    "massive_contribution",
    "fonll_matching_difference_contribution",
    "pdfs",
    "pdf_to_apfel_bridge",
    "alpha_s",
    "coordinate_and_jacobian",
    "numerical_integration",
    "normalization",
    "normalized_law_assembly",
}

FAILURE_CLASSIFICATIONS = {
    "DETECTABLE_BY_CURRENT_PLAN",
    "PARTIALLY_DETECTABLE",
    "NOT_INDEPENDENTLY_DETECTABLE",
}

REQUIRED_NON_EQUIVALENCES = [
    "PUBLISHED != EXECUTABLE",
    "BENCHMARKED != FULLY_VALIDATED",
    "COMPONENT_VALIDATION != END_TO_END_VALIDATION",
    "DISCLOSED_LIMITATION != PASS",
    "ABSENCE_OF_EVIDENCE != EVIDENCE_OF_CORRECTNESS",
    "CALIBRATED_POSTERIOR != VALIDATED_PHYSICS_IMPLEMENTATION",
]

RESEARCH_QUESTION_KEYS = (
    "inference_unit_unchanged",
    "posterior_target_unchanged",
    "theta_domain_and_prior_unchanged",
    "observation_space_unchanged",
    "selected_event_conditioning_unchanged",
    "detector_kernel_unchanged",
    "normalized_law_form_unchanged",
)

#: Affirmative assertions that would smuggle an end-to-end or executable claim
#: into the permitted paper language.  Statements framed as an admission of a
#: limitation are exempt, because naming the missing comparator is exactly what
#: this policy requires the paper to do.
FORBIDDEN_MAY_CLAIM_TOKENS = (
    "independently validated",
    "independently reimplemented",
    "end-to-end independent",
    "certified",
    "proves",
    "production-precision",
)
#: Markers that identify a permitted claim as an admission rather than an
#: assertion of validation strength.
MAY_CLAIM_ADMISSION_MARKERS = ("absence of", "is a stated limitation", "is not claimed")
FORBIDDEN_TOLERANCE_TOKENS = ("0.000125", "0.0013")


class ValidationError(Exception):
    """Raised when the FONLL validation policy record is internally inconsistent."""


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_header(record: dict) -> None:
    require(record.get("schema_version") == SCHEMA, "Wrong schema version")
    require(record.get("record_type") == "PHASE2B_FONLL_VALIDATION_POLICY_V1", "Wrong record type")
    require(
        record.get("task_kind") == "SCIENTIFIC_VALIDATION_POLICY_DECISION",
        "Record is not declared a validation-policy decision",
    )
    require(
        record.get("not_an_execution_authorization_review") is True,
        "Record poses as an execution authorization review",
    )
    require(
        record.get("not_a_successor_preauthorization_plan") is True,
        "Record poses as a successor plan",
    )
    require(record.get("v4_not_created_in_this_task") is True, "V4 created in a policy task")
    require(record.get("starting_main_sha") == STARTING_MAIN_SHA, "Starting main SHA changed")


def _validate_predecessors(record: dict, root: Path, check_files: bool) -> None:
    predecessors = record.get("predecessors", {})
    require(set(predecessors) == set(EXPECTED_PREDECESSORS), "Predecessor set changed")
    for key, (path, digest) in EXPECTED_PREDECESSORS.items():
        entry = predecessors[key]
        require(entry.get("path") == path, f"Predecessor path changed for {key}")
        require(entry.get("sha256") == digest, f"Predecessor hash changed for {key}")
        require(entry.get("bytes_immutable") is True, f"Predecessor {key} not marked immutable")
        if check_files:
            require(
                sha256_of(root / path) == digest,
                f"Historical artifact mutated on disk: {path}",
            )
    require(
        predecessors["numerical_policy_decision_v1"].get("historical_outcome")
        == "PD1_ADOPT_AP1_AND_NP2",
        "Numerical policy outcome rewritten",
    )
    require(
        predecessors["blocker_resolution_v1"].get("historical_outcome")
        == "BR5_MULTIPLE_BLOCKERS_REMAIN",
        "Blocker-resolution outcome rewritten",
    )


def _validate_history(record: dict) -> None:
    history = record.get("historical_state", {})
    require(history.get("phase2a_status") == "COMPLETE", "Phase 2A status changed")
    require(
        history.get("phase2a_scientific_decision") == "INCONCLUSIVE",
        "Phase 2A decision changed",
    )
    require(history.get("adr_013_status") == "Proposed", "ADR-013 status changed")
    require(
        history.get("accepted_pdf_family") == "ct18nlo_two_parameter_boundary_v2",
        "Accepted PDF family changed",
    )
    require(
        history.get("heavy_flavor_contract") == "APFEL FONLL-A NLO",
        "Heavy-flavor contract changed",
    )
    require(
        history.get("alpha_policy_unchanged") == "AP1_APFEL_ALPHA_IS_AUTHORITATIVE_SIMULATOR_COUPLING",
        "Alpha policy silently changed",
    )
    require(
        history.get("normalization_policy_unchanged")
        == "NP2_REQUIRE_EMPIRICAL_NUMERICAL_STABILITY_NOT_CERTIFIED_ACCURACY",
        "Normalization policy silently changed",
    )
    require(history.get("issue_54_unchanged") is True, "Issue #54 touched")
    require(history.get("issue_10_unchanged") is True, "Issue #10 touched")
    require(
        history.get("all_predecessor_bytes_unchanged") is True,
        "Historical artifact mutation claimed",
    )


def _validate_historical_reconstruction(record: dict) -> bool:
    reconstruction = record.get("historical_requirement_reconstruction", {})
    require(
        reconstruction.get("obligation_id") == "INDEPENDENT_NUMERICAL_CLOSURE_PLAN",
        "Historical obligation identifier changed",
    )
    sources = reconstruction.get("accepted_sources", [])
    require(len(sources) >= 3, "Historical reconstruction rests on too little accepted evidence")
    for entry in sources:
        require(entry.get("locator"), "Historical source has no locator")

    q1 = reconstruction.get("q1_required_executable_implementation_for_every_load_bearing_component", {})
    q2 = reconstruction.get("q2_required_credible_independent_closure_strategy", {})
    q3 = reconstruction.get("q3_any_accepted_record_promised_end_to_end_independent_fonll_a", {})
    q4 = reconstruction.get("q4_status_of_the_present_executable_fonll_requirement", {})
    for label, block in (("q1", q1), ("q2", q2), ("q3", q3), ("q4", q4)):
        require(block.get("answer"), f"Historical reconstruction {label} has no answer")
        require(block.get("evidence"), f"Historical reconstruction {label} has no evidence")
    require(
        reconstruction.get("retroactive_strengthening_performed") is False,
        "Historical wording was retroactively strengthened",
    )

    e1_was_mandatory = q1.get("answer") == "YES"
    if not e1_was_mandatory:
        require(
            reconstruction.get("v1_review_specific_defects_now_addressed"),
            "Reconstruction claims E1 was not mandatory without accounting for the v1 review objections",
        )
        for entry in reconstruction["v1_review_specific_defects_now_addressed"]:
            require(entry.get("defect"), "v1 defect entry has no defect")
            require(entry.get("status"), "v1 defect entry has no status")
            require(entry.get("how"), "v1 defect entry has no resolution")
    return e1_was_mandatory


def _validate_evidence_classes(record: dict) -> None:
    classes = record.get("evidence_classes", [])
    names = {entry.get("class") for entry in classes}
    require(names == EVIDENCE_CLASSES, "Evidence-class inventory changed")
    for entry in classes:
        require(entry.get("definition"), f"{entry.get('class')} has no definition")
        require(entry.get("can_establish"), f"{entry.get('class')} states nothing it can establish")
        require(
            entry.get("cannot_establish"),
            f"{entry.get('class')} states nothing it cannot establish",
        )

    lookup = {entry["class"]: entry for entry in classes}
    published = " ".join(lookup["E2_PUBLISHED_INDEPENDENT_NUMERICAL_BENCHMARK"]["cannot_establish"]).lower()
    require(
        "this frozen build" in published or "this build" in published,
        "E2 no longer denies coverage of the frozen build",
    )
    require(
        "replication" in published,
        "E2 no longer denies executable replication",
    )
    self_conv = " ".join(lookup["E6_INTERNAL_SELF_CONVERGENCE"]["cannot_establish"]).lower()
    require("correctness" in self_conv, "E6 no longer denies correctness")
    require("independence" in self_conv, "E6 no longer denies independence")


def _validate_graph(record: dict) -> list[dict]:
    graph = record.get("fonll_validation_graph", [])
    names = {entry.get("node") for entry in graph}
    require(names == EXPECTED_GRAPH_NODES, "Validation graph node set changed")
    require(len(graph) == len(names), "Duplicate validation graph node")

    for entry in graph:
        node = entry["node"]
        cls = entry.get("evidence_class")
        require(cls in NODE_CLASS_TOKENS, f"Node {node} has an unknown evidence class")
        require("independent" in entry, f"Node {node} does not state independence")
        require(entry.get("evidence_mode"), f"Node {node} has no evidence mode")
        require("future_phase2b_test" in entry, f"Node {node} does not state a future test")
        require(entry.get("residual_risk"), f"Node {node} has no residual-risk statement")
        require("disclosure_required" in entry, f"Node {node} does not state a disclosure duty")
        if cls in {"E2", "E5", "E6"} and entry.get("disclosure_required") is not True:
            raise ValidationError(
                f"Node {node} lacks executable independent evidence but requires no disclosure"
            )
        # PUBLISHED != EXECUTABLE, enforced structurally rather than by wording.
        # Published evidence is E2 by definition, so a published node may be
        # neither promoted to an executable oracle nor demoted to an analytic or
        # semantic check that would quietly retire its disclosure duty.
        if entry.get("evidence_mode") == "published" and cls != "E2":
            raise ValidationError(
                f"Node {node} carries published evidence but is not classed E2"
            )
        if cls == "E1" and entry.get("future_phase2b_test") in (None, ""):
            raise ValidationError(
                f"Node {node} is classed E1 with no executable comparison test"
            )

    require(
        record.get("end_to_end_independent_closure_claimed") is False,
        "End-to-end independent closure is claimed",
    )
    complete = next(entry for entry in graph if entry["node"] == "complete_nc_observable")
    require(
        complete.get("independent") is False,
        "The complete observable is presented as independently validated",
    )
    require(
        complete.get("evidence_class") != "E1",
        "The complete observable is presented as having an executable independent oracle",
    )
    return graph


def _validate_proportionality(record: dict) -> str:
    block = record.get("paper_scope_proportionality", {})
    classification = block.get("classification")
    require(classification in PROPORTIONALITY_OUTCOMES, "Unknown proportionality classification")
    require(block.get("derivation"), "Proportionality has no derivation")
    require(
        block.get("not_an_excuse_for_weak_physics"),
        "Proportionality does not address the weak-physics objection",
    )
    return classification


def _validate_failure_modes(record: dict) -> None:
    modes = record.get("failure_mode_analysis", [])
    require(len(modes) >= 8, "Failure-mode analysis does not cover the enumerated failures")
    for entry in modes:
        require(entry.get("failure"), "Failure-mode entry has no failure")
        require(
            entry.get("classification") in FAILURE_CLASSIFICATIONS,
            f"Unknown classification for {entry.get('failure')}",
        )
        require(entry.get("why"), f"Failure mode {entry.get('failure')} has no reasoning")
        if entry["classification"] == "DETECTABLE_BY_CURRENT_PLAN":
            require(
                entry.get("covered_by"),
                f"Failure mode {entry['failure']} is called detectable with no coverage",
            )
        if entry["classification"] == "NOT_INDEPENDENTLY_DETECTABLE":
            require(
                not entry.get("covered_by"),
                f"Failure mode {entry['failure']} is undetectable yet lists coverage",
            )
    require(
        any(entry["classification"] == "NOT_INDEPENDENTLY_DETECTABLE" for entry in modes),
        "No residual undetectable failure is acknowledged",
    )

    calibration = record.get("posterior_calibration_is_not_physics_validation", {})
    require(calibration.get("asserted") is True, "Posterior calibration is treated as physics validation")
    require(calibration.get("reason"), "The calibration non-equivalence has no reasoning")


def _validate_disclosure(record: dict) -> str:
    block = record.get("disclosure_sufficiency", {})
    classification = block.get("classification")
    require(classification in DISCLOSURE_OUTCOMES, "Unknown disclosure classification")
    if classification == "DISCLOSURE_SCIENTIFICALLY_SUFFICIENT":
        conditions = block.get("conditions_all_required", [])
        require(len(conditions) >= 8, "Disclosure sufficiency rests on too few conditions")
        joined = " ".join(conditions).lower()
        for needle, message in (
            ("disclosed", "Disclosure conditions omit explicit disclosure"),
            ("independently validated", "Disclosure conditions omit the mislabelling prohibition"),
            ("frozen", "Disclosure conditions omit configuration freezing"),
            ("uncertainty", "Disclosure conditions omit the no-uncertainty-from-missing-validation rule"),
            ("conditional", "Disclosure conditions omit conditionality on the frozen simulator"),
        ):
            require(needle in joined, message)
        require(block.get("scope_limit"), "Disclosure sufficiency has no scope limit")
    return classification


def _validate_candidate_policies(record: dict, outcome: str) -> None:
    policies = record.get("candidate_policies", {})
    for key in (
        "FR1_REQUIRE_EXECUTABLE_FONLL_REFERENCE",
        "FR2_ACCEPT_PUBLISHED_FONLL_EVIDENCE_AS_DISCLOSED_LIMITATION",
        "FR3_HYBRID_REQUIRED_COMPONENT_COVERAGE",
    ):
        require(key in policies, f"Candidate policy {key} not evaluated")
        require(policies[key].get("evaluation"), f"Candidate policy {key} has no evaluation")

    fr1 = policies["FR1_REQUIRE_EXECUTABLE_FONLL_REFERENCE"]
    require(fr1.get("assessment"), "FR1 has no assessment")
    require(
        fr1.get("rejected_because_more_validation_is_always_better") is False,
        "FR1 rejected or justified on a more-validation-is-better basis",
    )

    if outcome == "FPD3_ADOPT_HYBRID_COMPONENT_VALIDATION_POLICY":
        fr3 = policies["FR3_HYBRID_REQUIRED_COMPONENT_COVERAGE"]
        require(fr3.get("evaluation") == "ADOPTED", "FPD3 declared without adopting FR3")
        require(fr3.get("why_not_a_compromise"), "FR3 adopted without arguing it is not a compromise")
        require(fr3.get("stronger_than_fr2_because"), "FR3 adopted without showing it strengthens FR2")
        requirements = fr3.get("requirements", [])
        require(len(requirements) >= 4, "FR3 requirement set is too thin")
        joined = " ".join(requirements).lower()
        for needle, message in (
            ("mandatory and gating", "FR3 does not make the available checks gating"),
            ("frozen before authorization", "FR3 does not freeze the coverage matrix before authorization"),
            ("disclosed", "FR3 does not require disclosure of uncovered nodes"),
            ("fails", "FR3 does not fail a skipped available check"),
        ):
            require(needle in joined, message)


def _validate_terminology(record: dict) -> str:
    block = record.get("terminology_replacement", {})
    classification = block.get("classification")
    require(classification in TERMINOLOGY_OUTCOMES, "Unknown terminology classification")
    if classification == "TERMINOLOGY_REPLACEMENT_JUSTIFIED":
        require(
            block.get("new_rule") == "NO_UNDISCLOSED_LOAD_BEARING_VALIDATION_GAP",
            "Terminology replacement target changed",
        )
        require(block.get("derivation"), "Terminology replacement has no derivation")
        fields = block.get("required_fields_per_load_bearing_node", [])
        for needle in ("evidence_class", "validation_method", "residual_risk"):
            require(needle in fields, f"Terminology replacement omits required field {needle}")
        require(
            any("disclosure" in field for field in fields),
            "Terminology replacement omits the paper-disclosure field",
        )
        forbidden = " ".join(block.get("does_not_permit", [])).lower()
        for needle, message in (
            ("unnamed", "Terminology replacement permits an unspecified gap"),
            ("pass", "Terminology replacement permits a gap to count as a PASS"),
            ("reclassif", "Terminology replacement permits reclassifying to avoid a check"),
        ):
            require(needle in forbidden, message)
    return classification


def _validate_non_equivalences(record: dict) -> None:
    preserved = record.get("preserved_non_equivalences", [])
    for required in REQUIRED_NON_EQUIVALENCES:
        require(required in preserved, f"Non-equivalence dropped: {required}")


def _validate_outcome(
    record: dict,
    *,
    e1_was_mandatory: bool,
    proportionality: str,
    disclosure: str,
    terminology: str,
    expected: str | None,
) -> str:
    outcome = record.get("outcome", {})
    code = outcome.get("code")
    require(code in OUTCOMES, "Unknown FONLL policy outcome")
    require(outcome.get("scientific_rationale"), "Outcome has no scientific rationale")

    if code in {
        "FPD2_ACCEPT_EXECUTABLE_FONLL_GAP_AS_DISCLOSED_LIMITATION",
        "FPD3_ADOPT_HYBRID_COMPONENT_VALIDATION_POLICY",
    }:
        require(
            not e1_was_mandatory,
            "A disclosed-limitation outcome was chosen although the original contract required E1",
        )
        require(
            disclosure == "DISCLOSURE_SCIENTIFICALLY_SUFFICIENT",
            "A disclosed-limitation outcome was chosen without sufficient disclosure",
        )
        require(
            proportionality == "SCIENTIFICALLY_DESIRABLE_BUT_NOT_REQUIRED_GATE",
            "A disclosed-limitation outcome was chosen while the gate was ruled proportionate",
        )
        require(
            terminology == "TERMINOLOGY_REPLACEMENT_JUSTIFIED",
            "A disclosed-limitation outcome was chosen without a justified terminology replacement",
        )
        require(outcome.get("fpd1_rejected_reason"), "FPD1 rejected with no reason")

    if code == "FPD1_REQUIRE_EXECUTABLE_FONLL_REFERENCE":
        require(
            e1_was_mandatory
            or disclosure == "DISCLOSURE_INSUFFICIENT_EXECUTABLE_ORACLE_REQUIRED"
            or proportionality == "PROPORTIONATE_REQUIRED_GATE",
            "FPD1 declared without any of its three triggering conditions",
        )

    if code == "FPD4_FONLL_REFERENCE_POLICY_REMAINS_UNRESOLVED":
        require(
            disclosure == "DISCLOSURE_POLICY_UNRESOLVED"
            or proportionality == "INSUFFICIENT_INFORMATION"
            or terminology == "TERMINOLOGY_REPLACEMENT_UNRESOLVED",
            "FPD4 declared while every supporting analysis was in fact conclusive",
        )

    if expected is not None:
        require(code == expected, "Wrong FONLL policy outcome")
    return code


def _validate_contract_impact(record: dict) -> None:
    impact = record.get("contract_impact", {})
    by_scope = impact.get("by_scope", {})
    require(by_scope, "Contract impact has no scope breakdown")
    for scope, code in by_scope.items():
        require(code in CONTRACT_IMPACT_CODES, f"Scope {scope} has an unknown impact code")
    require(
        by_scope.get("research_question") == "UNCHANGED",
        "The FONLL policy changes the research question",
    )
    if "REPLACES_VALIDATION_GATE_SEMANTICS" in by_scope.values():
        require(
            impact.get("replacement_is_explicit_not_silent") is True,
            "A validation gate is replaced silently",
        )
        require(impact.get("replacement_detail"), "Gate replacement has no detail")
    check = impact.get("research_question_check", {})
    for key in RESEARCH_QUESTION_KEYS:
        require(check.get(key) is True, f"Research-question invariant {key} not preserved")


def _validate_paper_impact(record: dict, outcome: str) -> None:
    paper = record.get("paper_impact", {})
    may = paper.get("may_claim", [])
    must_not = paper.get("must_not_claim", [])
    require(may, "Paper impact lists nothing the paper may say")
    require(must_not, "Paper impact lists nothing the paper must not say")

    for statement in may:
        lowered = statement.lower()
        if any(marker in lowered for marker in MAY_CLAIM_ADMISSION_MARKERS):
            continue
        for token in FORBIDDEN_MAY_CLAIM_TOKENS:
            require(
                token not in lowered,
                f"Permitted paper claim smuggles in a forbidden assertion: {statement}",
            )

    joined = " ".join(must_not).lower()
    for needle, message in (
        ("independently executable", "Paper impact does not forbid the executable-closure claim"),
        ("published benchmark proves", "Paper impact does not forbid the published-proves-current claim"),
        ("production-precision", "Paper impact does not forbid the production-precision claim"),
        ("end-to-end independent", "Paper impact does not forbid end-to-end independent closure"),
        ("posterior calibration validates", "Paper impact does not forbid calibration-as-physics"),
        ("passed gate", "Paper impact does not forbid treating a disclosed limitation as a pass"),
    ):
        require(needle in joined, message)

    if outcome in {
        "FPD2_ACCEPT_EXECUTABLE_FONLL_GAP_AS_DISCLOSED_LIMITATION",
        "FPD3_ADOPT_HYBRID_COMPONENT_VALIDATION_POLICY",
    }:
        limitation = paper.get("mandatory_paper_limitation", "")
        require(limitation, "A disclosed-limitation outcome carries no mandatory paper limitation")
        lowered = limitation.lower()
        require(
            "no independently executable" in lowered,
            "The mandatory limitation does not state the missing executable comparator",
        )
        require(
            "published" in lowered,
            "The mandatory limitation does not identify the published-evidence basis",
        )


def _validate_v4(record: dict, outcome: str) -> None:
    block = record.get("v4_assessment", {})
    conclusion = block.get("conclusion")
    require(conclusion in V4_OUTCOMES, "Unknown V4 conclusion")
    require(block.get("why"), "V4 conclusion has no derivation")
    require(block.get("v4_not_created_here") is True, "V4 created by a policy task")

    if conclusion == "V4_SUCCESSOR_PLANNING_NOW_WARRANTED":
        require(
            outcome != "FPD4_FONLL_REFERENCE_POLICY_REMAINS_UNRESOLVED",
            "V4 warranted while the FONLL policy remains unresolved",
        )
        require(
            block.get("remaining_policy_blockers") == [],
            "V4 warranted while policy blockers remain",
        )
        require(
            block.get("remaining_plan_authoring_tasks"),
            "V4 warranted without naming the remaining plan-authoring tasks",
        )


def _validate_state(record: dict, root: Path) -> None:
    authorization = record.get("authorization", {})
    require(authorization, "Authorization block removed")
    require(all(value is False for value in authorization.values()), "Authorization flag is true")
    require(authorization.get("PHASE2C_AUTHORIZED") is False, "Phase 2C authorized")

    execution = record.get("execution_state", {})
    require(execution.get("phase2b") == "NOT_EXECUTED", "Phase 2B execution occurred")
    require(
        all(value is False for key, value in execution.items() if key != "phase2b"),
        "Forbidden physics or downstream execution recorded",
    )
    for key in ("apfel_executed", "apfelxx_executed", "massivedis_executed"):
        require(key in execution, f"Execution state omits {key}")

    require(
        record.get("github_target_state")
        == {
            "issue": 55,
            "state": "OPEN",
            "status": "Backlog",
            "gate_decision": "Not Evaluated",
            "authorization": "Not Authorized",
        },
        "Issue #55 target state changed",
    )
    require(record.get("remaining_scientific_limitations"), "Scientific limitations removed")
    require(record.get("next_step"), "Next step removed")

    serialized = json.dumps(record)
    for token in FORBIDDEN_TOLERANCE_TOKENS:
        require(token not in serialized, f"Rejected tolerance {token} reintroduced")
    # The policy task itself must not have created V4.  A later, separately
    # reviewed successor may legitimately create one, so the guard asserts the
    # record's own flag and, when a V4 exists, that it binds this record as a
    # predecessor rather than having been produced by this task.
    require(
        record.get("v4_not_created_in_this_task") is True,
        "A V4 plan artifact was created by the policy task",
    )
    v4_path = root / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v4.json"
    if v4_path.exists():
        v4 = json.loads(v4_path.read_text(encoding="utf-8"))
        binding = v4.get("predecessors", {}).get("fonll_validation_policy_v1", {})
        require(
            binding.get("sha256") == sha256_of(
                root / "docs/reduced_nc_dis/contracts/phase2b_fonll_validation_policy_v1.json"
            ),
            "A V4 plan exists that does not bind this policy record as a predecessor",
        )


def validate(
    record: dict,
    *,
    root: Path = ROOT,
    check_docs: bool = True,
    check_files: bool = True,
    expected_outcome: str | None = EXPECTED_OUTCOME,
) -> None:
    _validate_header(record)
    _validate_history(record)
    _validate_predecessors(record, root, check_files)
    e1_was_mandatory = _validate_historical_reconstruction(record)
    _validate_evidence_classes(record)
    _validate_graph(record)
    proportionality = _validate_proportionality(record)
    _validate_failure_modes(record)
    disclosure = _validate_disclosure(record)
    terminology = _validate_terminology(record)
    _validate_non_equivalences(record)
    outcome = _validate_outcome(
        record,
        e1_was_mandatory=e1_was_mandatory,
        proportionality=proportionality,
        disclosure=disclosure,
        terminology=terminology,
        expected=expected_outcome,
    )
    _validate_candidate_policies(record, outcome)
    _validate_contract_impact(record)
    _validate_paper_impact(record, outcome)
    _validate_v4(record, outcome)
    _validate_state(record, root)

    if check_docs:
        markers = {
            "docs/reduced_nc_dis/PHASE2B_FONLL_VALIDATION_POLICY_V1.md": [
                EXPECTED_OUTCOME,
                "NO_UNDISCLOSED_LOAD_BEARING_VALIDATION_GAP",
                "V4_SUCCESSOR_PLANNING_NOW_WARRANTED",
                "NOT_EXECUTED",
            ],
            "docs/CURRENT_PHASE.md": [EXPECTED_OUTCOME, "Phase 2B remains Not Authorized"],
            "docs/reduced_nc_dis/README.md": [EXPECTED_OUTCOME, "Not Authorized"],
            "docs/adr/ADR-013-reduced-nc-dis-observation-law-contract.md": [
                EXPECTED_OUTCOME,
                "Historical Phase 2A remains `INCONCLUSIVE`",
            ],
        }
        for relative, required in markers.items():
            text = (root / relative).read_text(encoding="utf-8")
            for marker in required:
                require(marker in text, f"Documentation marker missing from {relative}: {marker}")


def main() -> None:
    try:
        record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        validate(record)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise SystemExit(f"INVALID phase2b.fonll_validation_policy_v1: {error}") from error
    print("VALID phase2b.fonll_validation_policy_v1")


if __name__ == "__main__":
    main()
