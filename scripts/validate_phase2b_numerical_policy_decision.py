#!/usr/bin/env python3
"""Validate the Phase 2B numerical-contract policy decision statically."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_numerical_policy_decision_v1.json"
SCHEMA = "partonsbi.phase2b.numerical-policy-decision.v1"

ALPHA_OPTIONS = {
    "AP1_APFEL_ALPHA_IS_AUTHORITATIVE_SIMULATOR_COUPLING",
    "AP2_CERTIFY_FROZEN_PLATFORM_LIBM_PROVIDER",
    "AP3_REIMPLEMENT_PROVIDER_WITH_RIGOROUS_INTERVAL_LOG",
    "AP4_ALPHA_POLICY_REMAINS_UNRESOLVED",
}
NORMALIZATION_OPTIONS = {
    "NP1_REQUIRE_RIGOROUS_CERTIFIED_NORMALIZATION_ACCURACY",
    "NP2_REQUIRE_EMPIRICAL_NUMERICAL_STABILITY_NOT_CERTIFIED_ACCURACY",
    "NP3_REMOVE_NORMALIZATION_VALIDATION_FROM_PHASE2B",
    "NP4_NORMALIZATION_POLICY_REMAINS_UNRESOLVED",
}
COMBINED_OPTIONS = {
    "PD1_ADOPT_AP1_AND_NP2",
    "PD2_ADOPT_ALPHA_POLICY_ONLY_NORMALIZATION_UNRESOLVED",
    "PD3_ADOPT_NORMALIZATION_POLICY_ONLY_ALPHA_UNRESOLVED",
    "PD4_RETAIN_STRICT_CERTIFICATION_REQUIREMENTS",
    "PD5_POLICY_DECISION_REMAINS_BLOCKED",
}
EXPECTED_ALPHA = "AP1_APFEL_ALPHA_IS_AUTHORITATIVE_SIMULATOR_COUPLING"
EXPECTED_NORMALIZATION = "NP2_REQUIRE_EMPIRICAL_NUMERICAL_STABILITY_NOT_CERTIFIED_ACCURACY"
EXPECTED_COMBINED = "PD1_ADOPT_AP1_AND_NP2"

CONTRACT_IMPACT_CODES = {
    "DISAMBIGUATES_EXISTING_CONTRACT",
    "NARROWS_CLAIM_BOUNDARY",
    "REPLACES_EXISTING_CONTRACT",
    "CHANGES_RESEARCH_QUESTION",
    "UNCHANGED",
}

STARTING_MAIN_SHA = "bf36b7c193a8061c70f4209051f979ed4c7441ba"

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
}

REQUIRED_COMPATIBILITY_ITEMS = {
    "alpha_s at the Z mass",
    "perturbative order of the observable",
    "heavy-quark pole masses",
    "flavour scheme and maximum active flavours",
    "matching-scale ratios and renormalisation-to-factorisation ratio",
    "perturbative order of the coupling running itself",
}

EXPECTED_BLOCKER_IDS = {
    "BLOCKER_ALPHA_IMPLEMENTED_LOG_ENCLOSURE",
    "BLOCKER_ALPHA_CONSISTENCY_CRITERION",
    "BLOCKER_PROJECT_PRECISION_TARGET",
    "BLOCKER_GRID_GATE_SEMANTICS",
    "BLOCKER_MASSLESS_CANDIDATE_SIDE",
    "BLOCKER_NUMERICAL_RUNTIME_IDENTITY",
    "BLOCKER_FONLL_REFERENCE_EXECUTION_SPEC",
}
BLOCKER_STATUSES = {
    "DISSOLVED_BY_POLICY",
    "CONVERTED_TO_PLAN_AUTHORING_ITEM",
    "DOWNGRADED_TO_DISCLOSURE_REQUIREMENT",
    "REMAINS_A_SCIENTIFIC_BLOCKER",
}
#: Only blockers that lie inside the scope of the two decided policies may be
#: dissolved by this record.  The alpha policy can retire the two alpha-gate
#: blockers; nothing here bears on the independent-reference gap, the massless
#: candidate side, the grid-gate redesign or the runtime identity.
DISSOLVABLE_BY_THIS_DECISION = {
    "BLOCKER_ALPHA_IMPLEMENTED_LOG_ENCLOSURE",
    "BLOCKER_ALPHA_CONSISTENCY_CRITERION",
}

#: Substrings that would smuggle a certified-accuracy or equivalence claim back in.
FORBIDDEN_MAY_CLAIM_TOKENS = (
    "rigorously certified",
    "certified to",
    "certified accuracy",
    "equivalent",
    "bitwise identical",
    "proves convergence",
    "bounds the",
)
#: Numerical tolerances that earlier reviews rejected and that may not return.
FORBIDDEN_TOLERANCE_TOKENS = ("0.000125", "0.0013")

RESEARCH_QUESTION_KEYS = (
    "inference_unit_unchanged",
    "posterior_target_unchanged",
    "theta_domain_and_prior_unchanged",
    "observation_space_unchanged",
    "selected_event_conditioning_unchanged",
    "detector_kernel_unchanged",
    "normalized_law_form_unchanged",
)


class ValidationError(Exception):
    """Raised when the policy-decision record is internally inconsistent."""


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_header(record: dict) -> None:
    require(record.get("schema_version") == SCHEMA, "Wrong schema version")
    require(
        record.get("record_type") == "PHASE2B_NUMERICAL_CONTRACT_POLICY_DECISION_V1",
        "Wrong record type",
    )
    require(
        record.get("task_kind") == "SCIENTIFIC_CONTRACT_POLICY_DECISION",
        "Record is not declared a policy decision",
    )
    require(
        record.get("not_an_execution_authorization_review") is True,
        "Record poses as an execution authorization review",
    )
    require(
        record.get("not_a_successor_preauthorization_plan") is True,
        "Record poses as a successor preauthorization plan",
    )
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
        predecessors["preauthorization_v3"].get("historical_outcome")
        == "V3R6_MULTIPLE_BLOCKERS_REMAIN",
        "V3 historical outcome rewritten",
    )
    require(
        predecessors["blocker_resolution_v1"].get("historical_outcome")
        == "BR5_MULTIPLE_BLOCKERS_REMAIN",
        "Blocker-resolution historical outcome rewritten",
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
    require(history.get("issue_54_unchanged") is True, "Issue #54 touched")
    require(history.get("issue_10_unchanged") is True, "Issue #10 touched")
    require(
        history.get("all_predecessor_bytes_unchanged") is True,
        "Historical artifact mutation claimed",
    )


def _validate_contract_impact(impact: dict, label: str) -> str:
    require(impact.get("primary") in CONTRACT_IMPACT_CODES, f"{label} primary impact unknown")
    by_scope = impact.get("by_scope", {})
    require(by_scope, f"{label} impact has no scope breakdown")
    for scope, code in by_scope.items():
        require(code in CONTRACT_IMPACT_CODES, f"{label} scope {scope} has an unknown impact code")
    research = by_scope.get("research_question")
    require(research is not None, f"{label} does not classify research-question impact")
    if "REPLACES_EXISTING_CONTRACT" in by_scope.values():
        require(
            impact.get("replacement_is_explicit_not_silent") is True,
            f"{label} replaces a contract silently",
        )
        require(impact.get("replacement_detail"), f"{label} replacement has no detail")
    return research


def _validate_alpha(record: dict) -> None:
    alpha = record.get("question_a_alpha_authority", {})
    decision = alpha.get("decision")
    require(decision in ALPHA_OPTIONS, "Unknown alpha policy option")

    fact = alpha.get("decisive_source_fact", {})
    review = alpha.get("scientific_review", {})
    forbids = alpha.get("what_ap1_forbids", [])

    if decision == EXPECTED_ALPHA:
        require(fact.get("statement"), "AP1 has no decisive source fact")
        require(fact.get("locator"), "AP1 decisive fact has no source locator")
        require(fact.get("verified_this_task") is True, "AP1 decisive fact was not verified")
        require(
            alpha.get("why_this_is_not_a_convenience_choice"),
            "AP1 adopted without arguing it is more than convenience",
        )

        q1 = review.get("q1_runtime_evaluator_must_match_grid_producing_evaluator", {})
        require(q1.get("answer") == "NO", "AP1 while still requiring evaluator identity")
        require(q1.get("derivation"), "AP1 evaluator answer has no derivation")

        q2 = review.get("q2_declared_convention_is_the_relevant_contract", {})
        require(q2.get("answer") == "YES", "AP1 without adopting declared-convention consistency")
        items = q2.get("required_compatibility_items", [])
        names = {entry.get("item") for entry in items}
        require(
            REQUIRED_COMPATIBILITY_ITEMS <= names,
            "AP1 silently drops a declared-convention compatibility item",
        )
        for entry in items:
            require(entry.get("status"), f"Compatibility item {entry.get('item')} has no status")
            if entry.get("status") == "UNRESOLVED_COMPATIBILITY_ITEM":
                require(entry.get("note"), "Unresolved compatibility item carries no note")

        q3 = review.get("q3_new_hidden_theory_inconsistency", {})
        require(q3.get("answer"), "AP1 does not answer the hidden-inconsistency question")
        require(q3.get("explicitly_not_claimed"), "AP1 does not list what it refrains from claiming")

        q4 = review.get("q4_changes_the_research_question", {})
        require(q4.get("answer") == "NO", "AP1 recorded as changing the research question")

        q5 = review.get("q5_later_diagnostic_that_remains_appropriate", {})
        require(q5.get("required") is True, "AP1 without a required later diagnostic")
        require(q5.get("gating") is False, "AP1 diagnostic incorrectly made a gate")
        require(q5.get("content"), "AP1 diagnostic has no content")
        require(q5.get("review_trigger"), "AP1 diagnostic has no review trigger")
        require(
            q5.get("review_trigger_is_not_a_numerical_threshold") is True,
            "AP1 diagnostic smuggles in a numerical threshold",
        )
        require(q5.get("no_tolerance_defined_here") is True, "AP1 defines a tolerance")

        joined = " ".join(forbids).lower()
        require(
            "bitwise" in joined or "continuous" in joined,
            "AP1 does not forbid a continuous or bitwise identity gate",
        )
        require(
            "equivalen" in joined,
            "AP1 does not forbid calling the diagnostic an equivalence result",
        )

    rejected = {entry.get("option") for entry in alpha.get("rejected_alternatives", [])}
    require(
        rejected == ALPHA_OPTIONS - {decision},
        "Alpha rejected-alternative inventory does not cover every other option",
    )
    for entry in alpha.get("rejected_alternatives", []):
        require(entry.get("rejected_because"), f"{entry.get('option')} rejected with no reason")

    research = _validate_contract_impact(alpha.get("contract_impact", {}), "Alpha policy")
    require(research == "UNCHANGED", "Alpha policy changes the research question")


def _validate_normalization(record: dict) -> None:
    normalization = record.get("question_b_normalization_claim", {})
    decision = normalization.get("decision")
    require(decision in NORMALIZATION_OPTIONS, "Unknown normalization policy option")

    review = normalization.get("scientific_review", {})
    distinctions = review.get("distinctions", {})
    for key in (
        "mathematical_proof_of_quadrature_error",
        "empirical_convergence_evidence",
        "reproducibility",
        "physical_or_theory_uncertainty",
        "downstream_sbi_calibration",
    ):
        require(distinctions.get(key), f"Normalization review omits the {key} distinction")

    require(
        normalization.get("normalization_remains_in_the_probability_law_contract") is True,
        "Normalization removed from the probability-law contract",
    )
    mandatory = normalization.get("normalization_mandatory_properties", [])
    joined_mandatory = " ".join(mandatory).lower()
    require("finite" in joined_mandatory, "Finite normalization no longer mandatory")
    require("positive" in joined_mandatory, "Positive normalization no longer mandatory")
    for banned in ("clipping", "absolute value", "deletion", "retry"):
        require(banned in joined_mandatory, f"Normalization policy stops forbidding {banned}")

    if decision == EXPECTED_NORMALIZATION:
        q1 = review.get("q1_paper_requires_a_certified_integration_theorem", {})
        require(q1.get("answer") == "NO", "NP2 while still requiring a certified theorem")
        require(q1.get("derivation"), "NP2 theorem answer has no derivation")

        q2 = review.get("q2_empirical_independent_quadrature_stability_is_sufficient_if_disclosed", {})
        require(q2.get("answer") == "YES_CONDITIONALLY", "NP2 sufficiency answer changed")
        require(q2.get("conditions"), "NP2 states no sufficiency conditions")
        require(q2.get("residual_risk_disclosed"), "NP2 hides its residual risk")

        forbidden = review.get("q3_claims_forbidden_under_np2", [])
        joined = " ".join(forbidden).lower()
        require("certified" in joined, "NP2 does not forbid a certified-accuracy claim")
        require(
            "successive difference" in joined,
            "NP2 does not forbid treating a successive difference as a bound",
        )
        require(
            "0.001" in joined or "massivedis" in joined,
            "NP2 does not forbid transferring the external benchmark level",
        )
        require(
            "after seeing" in joined or "post-hoc" in joined or "adjusted after" in joined,
            "NP2 does not forbid post-hoc tolerance tuning",
        )

        criteria = review.get("q4_minimum_predeclared_empirical_criteria", [])
        require(len(criteria) >= 8, "NP2 minimum criteria list is too thin to be a protocol")
        joined_criteria = " ".join(criteria).lower()
        for needle, message in (
            ("independently generated", "NP2 does not require independent rule generation"),
            ("before", "NP2 does not require predeclaration before execution"),
            ("every theta anchor", "NP2 does not require agreement at every anchor"),
            ("inconclusive", "NP2 does not define an inconclusive outcome"),
            ("retry-until-pass", "NP2 does not forbid retry-until-pass"),
        ):
            require(needle in joined_criteria, message)

        require(
            review.get("numerical_tolerance_defined_here") is False,
            "The policy decision invented a numerical tolerance",
        )
        require(review.get("why_no_tolerance_here"), "No reason given for deferring the tolerance")

    if decision == "NP3_REMOVE_NORMALIZATION_VALIDATION_FROM_PHASE2B":
        require(
            normalization.get("compatibility_with_normalized_law_proven") is True,
            "NP3 selected without proving compatibility with the normalized law",
        )

    rejected = {entry.get("option") for entry in normalization.get("rejected_alternatives", [])}
    require(
        rejected == NORMALIZATION_OPTIONS - {decision},
        "Normalization rejected-alternative inventory does not cover every other option",
    )
    for entry in normalization.get("rejected_alternatives", []):
        require(entry.get("rejected_because"), f"{entry.get('option')} rejected with no reason")
        if entry.get("option") == "NP3_REMOVE_NORMALIZATION_VALIDATION_FROM_PHASE2B":
            require(
                entry.get("compatibility_with_normalized_law_proven") is False,
                "NP3 rejection claims an unproven compatibility proof",
            )

    research = _validate_contract_impact(normalization.get("contract_impact", {}), "Normalization policy")
    require(research == "UNCHANGED", "Normalization policy changes the research question")


def _validate_combined(record: dict, expected: str | None) -> None:
    combined = record.get("combined_decision", {})
    code = combined.get("code")
    require(code in COMBINED_OPTIONS, "Unknown combined policy outcome")
    require(combined.get("derivation"), "Combined outcome has no derivation")

    alpha = record["question_a_alpha_authority"]["decision"]
    normalization = record["question_b_normalization_claim"]["decision"]

    if code == "PD1_ADOPT_AP1_AND_NP2":
        require(alpha == EXPECTED_ALPHA, "PD1 declared without AP1")
        require(normalization == EXPECTED_NORMALIZATION, "PD1 declared without NP2")
    elif code == "PD2_ADOPT_ALPHA_POLICY_ONLY_NORMALIZATION_UNRESOLVED":
        require(alpha != "AP4_ALPHA_POLICY_REMAINS_UNRESOLVED", "PD2 without an alpha decision")
        require(
            normalization == "NP4_NORMALIZATION_POLICY_REMAINS_UNRESOLVED",
            "PD2 with a resolved normalization policy",
        )
    elif code == "PD3_ADOPT_NORMALIZATION_POLICY_ONLY_ALPHA_UNRESOLVED":
        require(
            alpha == "AP4_ALPHA_POLICY_REMAINS_UNRESOLVED",
            "PD3 with a resolved alpha policy",
        )
        require(
            normalization != "NP4_NORMALIZATION_POLICY_REMAINS_UNRESOLVED",
            "PD3 without a normalization decision",
        )
    elif code == "PD4_RETAIN_STRICT_CERTIFICATION_REQUIREMENTS":
        require(
            alpha in {"AP2_CERTIFY_FROZEN_PLATFORM_LIBM_PROVIDER", "AP3_REIMPLEMENT_PROVIDER_WITH_RIGOROUS_INTERVAL_LOG"},
            "PD4 without a strict alpha certification requirement",
        )
        require(
            normalization == "NP1_REQUIRE_RIGOROUS_CERTIFIED_NORMALIZATION_ACCURACY",
            "PD4 without a strict normalization certification requirement",
        )
    else:
        require(
            alpha == "AP4_ALPHA_POLICY_REMAINS_UNRESOLVED"
            and normalization == "NP4_NORMALIZATION_POLICY_REMAINS_UNRESOLVED",
            "PD5 declared while a policy was in fact decided",
        )

    require(
        combined.get("research_question_impact") == "UNCHANGED",
        "Combined decision changes the research question",
    )
    check = combined.get("research_question_check", {})
    for key in RESEARCH_QUESTION_KEYS:
        require(check.get(key) is True, f"Research-question invariant {key} not preserved")

    if expected is not None:
        require(code == expected, "Wrong combined policy outcome")


def _validate_paper_impact(record: dict) -> None:
    paper = record.get("paper_impact", {})
    may = paper.get("may_claim", [])
    must_not = paper.get("must_not_claim", [])
    require(may, "Paper impact lists nothing the paper may say")
    require(must_not, "Paper impact lists nothing the paper must not say")

    for statement in may:
        lowered = statement.lower()
        for token in FORBIDDEN_MAY_CLAIM_TOKENS:
            require(
                token not in lowered,
                f"Permitted paper claim smuggles in a forbidden assertion: {statement}",
            )

    joined_must_not = " ".join(must_not).lower()
    for needle, message in (
        ("equivalent", "Paper impact does not forbid the coupling-equivalence claim"),
        ("certified", "Paper impact does not forbid a certified-accuracy claim"),
        ("successive difference", "Paper impact does not forbid the successive-difference bound"),
        ("continuum", "Paper impact does not forbid the continuum claims"),
    ):
        require(needle in joined_must_not, message)

    require(paper.get("example_permitted_sentence"), "No permitted example sentence recorded")
    require(paper.get("example_forbidden_sentence"), "No forbidden example sentence recorded")
    require(paper.get("conditional_release"), "No conditions recorded for revisiting a must-not item")


def _validate_blockers(record: dict) -> None:
    entries = record.get("blocker_status_after_decision", [])
    identifiers = {entry.get("id") for entry in entries}
    require(identifiers == EXPECTED_BLOCKER_IDS, "Blocker inventory changed")
    require(len(entries) == len(identifiers), "Duplicate blocker entry")
    remaining = []
    for entry in entries:
        identifier = entry.get("id")
        status = entry.get("status")
        require(status in BLOCKER_STATUSES, f"Unknown status for {identifier}")
        require(entry.get("reason"), f"Blocker {identifier} has no reason")
        if status == "DISSOLVED_BY_POLICY":
            require(
                identifier in DISSOLVABLE_BY_THIS_DECISION,
                f"{identifier} is outside the scope of this decision and cannot be dissolved by it",
            )
        if status == "REMAINS_A_SCIENTIFIC_BLOCKER":
            remaining.append(identifier)
    require(
        "BLOCKER_FONLL_REFERENCE_EXECUTION_SPEC" in remaining,
        "The independent-reference blocker was retired by a decision that does not address it",
    )

    successor = record.get("successor_plan_assessment", {})
    require(successor.get("v4_not_created_in_this_task") is True, "V4 created in a policy task")
    require(successor.get("why"), "Successor assessment has no derivation")
    if remaining:
        require(
            successor.get("v4_completeness_achievable_now") is False,
            "Successor completeness claimed while a scientific blocker remains",
        )
    third = successor.get("third_policy_question_identified", {})
    if successor.get("v4_completeness_achievable_now") is False:
        require(third.get("question"), "Incomplete successor without naming the open question")
        require(third.get("status") == "NOT_DECIDED_HERE", "Third question status inconsistent")
        require(third.get("why_not_decided_here"), "Third question deferred with no reason")


def _validate_state(record: dict, root: Path) -> None:
    authorization = record.get("authorization", {})
    require(authorization, "Authorization block removed")
    require(all(value is False for value in authorization.values()), "Authorization flag is true")
    require(
        authorization.get("PHASE2B_EXECUTION_AUTHORIZED") is False,
        "Phase 2B execution authorized",
    )
    require(authorization.get("PHASE2C_AUTHORIZED") is False, "Phase 2C authorized")

    execution = record.get("execution_state", {})
    require(execution.get("phase2b") == "NOT_EXECUTED", "Phase 2B execution occurred")
    require(
        all(value is False for key, value in execution.items() if key != "phase2b"),
        "Forbidden physics or downstream execution recorded",
    )

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
        record.get("successor_plan_assessment", {}).get("v4_not_created_in_this_task") is True,
        "A V4 plan artifact was created by the policy task",
    )
    v4_path = root / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v4.json"
    if v4_path.exists():
        v4 = json.loads(v4_path.read_text(encoding="utf-8"))
        binding = v4.get("predecessors", {}).get("numerical_policy_decision_v1", {})
        require(
            binding.get("sha256") == sha256_of(
                root / "docs/reduced_nc_dis/contracts/phase2b_numerical_policy_decision_v1.json"
            ),
            "A V4 plan exists that does not bind this policy record as a predecessor",
        )


def validate(
    record: dict,
    *,
    root: Path = ROOT,
    check_docs: bool = True,
    check_files: bool = True,
    expected_outcome: str | None = EXPECTED_COMBINED,
) -> None:
    _validate_header(record)
    _validate_history(record)
    _validate_predecessors(record, root, check_files)
    _validate_alpha(record)
    _validate_normalization(record)
    _validate_combined(record, expected_outcome)
    _validate_paper_impact(record)
    _validate_blockers(record)
    _validate_state(record, root)

    if check_docs:
        markers = {
            "docs/reduced_nc_dis/PHASE2B_NUMERICAL_POLICY_DECISION_V1.md": [
                EXPECTED_COMBINED,
                EXPECTED_ALPHA,
                EXPECTED_NORMALIZATION,
                "NOT_EXECUTED",
            ],
            "docs/CURRENT_PHASE.md": [EXPECTED_COMBINED, "Phase 2B remains Not Authorized"],
            "docs/reduced_nc_dis/README.md": [EXPECTED_COMBINED, "Not Authorized"],
            "docs/adr/ADR-013-reduced-nc-dis-observation-law-contract.md": [
                EXPECTED_COMBINED,
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
        raise SystemExit(f"INVALID phase2b.numerical_policy_decision_v1: {error}") from error
    print("VALID phase2b.numerical_policy_decision_v1")


if __name__ == "__main__":
    main()
