#!/usr/bin/env python3
"""Validate the Phase 2B preauthorization blocker-resolution record statically."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_blocker_resolution_v1.json"
COMPANION = ROOT / "docs/reduced_nc_dis/PHASE2B_BLOCKER_RESOLUTION_V1.md"
SCHEMA = "partonsbi.phase2b.blocker-resolution.v1"

OUTCOMES = {
    "BR1_ALL_PREAUTH_BLOCKERS_RESOLVED",
    "BR2_ALPHA_BLOCKER_REMAINS",
    "BR3_REFERENCE_BLOCKER_REMAINS",
    "BR4_NUMERICAL_CONVERGENCE_BLOCKER_REMAINS",
    "BR5_MULTIPLE_BLOCKERS_REMAIN",
}
EXPECTED_OUTCOME = "BR5_MULTIPLE_BLOCKERS_REMAIN"
NON_BR1_OUTCOMES = OUTCOMES - {"BR1_ALL_PREAUTH_BLOCKERS_RESOLVED"}

STARTING_MAIN_SHA = "e29f8f63aa4d98f102e087c7be3901705eed5365"

EXPECTED_PREDECESSORS = {
    "fonll_a_amendment": (
        "docs/reduced_nc_dis/contracts/phase2_fonll_a_contract_amendment.json",
        "10cf19fedcdfe1b94e18ff89d1ae09514a31b8e0f6b055beeb729d61b6c32da8",
    ),
    "preauthorization_v1": (
        "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan.json",
        "7eb8834eb8435532a85bd7d49b173b03e57a268f69f9676e0effbd877903672b",
    ),
    "execution_authorization_review_v1": (
        "docs/reduced_nc_dis/contracts/phase2b_execution_authorization_review.json",
        "03d8119efb819b7a8b51161d5f2ce58fe59dd385b63f2dbfd6203692dac1f9e2",
    ),
    "preauthorization_v2": (
        "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v2.json",
        "a79e87538fae4d3f20793756b321af4d7521c1277ee08580e1b773a7452a9cd2",
    ),
    "execution_authorization_review_v2": (
        "docs/reduced_nc_dis/contracts/phase2b_execution_authorization_review_v2.json",
        "d7826158718ea0c4e5d3fc7c0f60829913e9634c98c45d2316c63bffdce47821",
    ),
    "preauthorization_v3": (
        "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v3.json",
        "78a029686489e9712e65ef6f9df3263b4821f96de0ee9873a910dee31f307e06",
    ),
}

EXPECTED_GRAPH_NODES = {
    "TEST_ALPHA",
    "TEST_BRIDGE",
    "TEST_FONLL_COMPONENT",
    "TEST_MASSLESS",
    "TEST_EW_JACOBIAN",
    "TEST_RAW_RATE_SIGN",
    "TEST_GRID_CONVERGENCE",
    "TEST_QUADRATURE_A",
    "TEST_QUADRATURE_B",
    "TEST_CROSS_QUADRATURE",
    "TEST_NORMALIZATION",
    "TEST_NORMALIZED_LAW",
}
DEFICIENCY_CODES = {
    "MISSING_SOURCE_EVIDENCE",
    "MISSING_SOFTWARE_IDENTITY",
    "MISSING_MATHEMATICAL_BOUND",
    "MISSING_ACCEPTANCE_RULE",
    "MISSING_RESOURCE_BOUND",
    "UPSTREAM_BLOCKED",
}
UNRESOLVED_NODE_STATUSES = {
    "BLOCKED_PREAUTH_SPECIFICATION",
    "BLOCKED_ACCEPTANCE_RULE",
    "BLOCKED_BY_UPSTREAM_RULES",
    "PARTIALLY_RESOLVED_BLOCKER_NARROWED",
    "REDESIGN_REQUIRED_IN_A_SUCCESSOR",
}
RESOLVED_NODE_STATUSES = {"FULLY_SPECIFIED_NOT_EXECUTED"}

REJECTED_BACKEND_TOKENS = ("mpmath", "mpmath.iv")
ACCEPTED_BACKEND_TOKEN = "python-flint"

EXPECTED_RESOURCE_CATEGORIES = {
    "physics_evaluator_calls",
    "alpha_interval_cells",
    "alpha_rhs_evaluations",
    "external_reference_calls",
    "bridge_evaluator_calls",
    "quadrature_integrand_calls",
    "analytic_unit_test_calls",
    "storage_bound",
}

REPRODUCIBILITY_CLASSES = {
    "BITWISE_SAME_FROZEN_ENVIRONMENT",
    "NUMERICALLY_REPRODUCIBLE_WITH_FROZEN_SOFTWARE_IDENTITY",
    "ENVIRONMENT_REPRODUCIBILITY_UNRESOLVED",
}

FONLL_REF_CLASSES = {
    "FONLL_REF_EXECUTABLE_FULLY_SPECIFIED",
    "FONLL_REF_PUBLISHED_ONLY",
    "FONLL_REF_UNRESOLVED",
}
MASSLESS_REF_CLASSES = {
    "MASSLESS_REF_FULLY_SPECIFIED",
    "MASSLESS_REF_PARTIAL",
    "MASSLESS_REF_UNRESOLVED",
}
ALPHA_CLAIMS = {
    "ALPHA_CLAIM_EXACT_FUNCTION_IDENTITY",
    "ALPHA_CLAIM_BOUNDED_NUMERICAL_CONSISTENCY",
}
BACKEND_DECISIONS = {"ALPHA_BACKEND_BOUND", "ALPHA_BACKEND_UNRESOLVED"}
C1_ANSWERS = {
    "C1A_RIGOROUS_QUADRATURE_REMAINDER_CERTIFICATE",
    "C1B_PREDECLARED_EMPIRICAL_CONVERGENCE_AND_INDEPENDENT_CROSSCHECK",
    "NEITHER_IS_CURRENTLY_AVAILABLE",
}

FORBIDDEN_TOLERANCE_TOKENS = ("0.000125", "0.0013")


class ValidationError(Exception):
    """Raised when the blocker-resolution record is internally inconsistent."""


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_predecessors(record: dict, root: Path, check_files: bool) -> None:
    predecessors = record.get("predecessors", {})
    require(
        set(predecessors) == set(EXPECTED_PREDECESSORS),
        "Predecessor set changed",
    )
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


def _validate_history(record: dict) -> None:
    history = record.get("historical_state", {})
    require(history.get("phase2a_status") == "COMPLETE", "Phase 2A status changed")
    require(
        history.get("phase2a_scientific_decision") == "INCONCLUSIVE",
        "Phase 2A decision strengthened",
    )
    require(history.get("adr_013_status") == "Proposed", "ADR-013 status changed")
    require(
        history.get("accepted_pdf_family") == "ct18nlo_two_parameter_boundary_v2",
        "Accepted PDF family changed",
    )
    require(history.get("issue_54_unchanged") is True, "Issue #54 touched")
    require(history.get("issue_10_unchanged") is True, "Issue #10 touched")
    require(
        history.get("all_predecessor_bytes_unchanged") is True,
        "Historical artifact mutation claimed",
    )
    require(
        record.get("task_kind") == "BLOCKER_RESOLUTION_ONLY",
        "Record is not declared a blocker resolution",
    )
    require(
        record.get("not_an_execution_authorization_review") is True,
        "Record poses as an execution authorization review",
    )
    require(
        record.get("starting_main_sha") == STARTING_MAIN_SHA,
        "Starting main SHA changed",
    )
    require(
        len(record.get("accepted_v3_results_not_relitigated", [])) == 8,
        "Accepted V3 results were dropped",
    )


def _validate_graph(record: dict) -> tuple[set[str], set[str]]:
    graph = record.get("blocker_dependency_graph", {})
    require(
        set(graph.get("deficiency_codes", [])) == DEFICIENCY_CODES,
        "Deficiency vocabulary changed",
    )
    nodes = graph.get("nodes", [])
    identifiers = {node.get("test_id") for node in nodes}
    require(identifiers == EXPECTED_GRAPH_NODES, "Blocker graph node set changed")
    require(len(nodes) == len(identifiers), "Duplicate blocker graph node")

    unresolved: set[str] = set()
    resolved: set[str] = set()
    for node in nodes:
        identifier = node["test_id"]
        status = node.get("post_task_status")
        require(
            status in UNRESOLVED_NODE_STATUSES | RESOLVED_NODE_STATUSES,
            f"Unknown post-task status for {identifier}",
        )
        for code in node.get("deficiencies_after", []):
            require(code in DEFICIENCY_CODES, f"Unknown deficiency code on {identifier}")
        for code in node.get("deficiencies_before", []):
            require(code in DEFICIENCY_CODES, f"Unknown deficiency code on {identifier}")
        if status in RESOLVED_NODE_STATUSES:
            require(
                not node.get("deficiencies_after"),
                f"{identifier} is marked resolved but still lists deficiencies",
            )
            require(
                not node.get("still_missing"),
                f"{identifier} is marked resolved but still lists missing items",
            )
            resolved.add(identifier)
        else:
            require(
                node.get("still_missing"),
                f"{identifier} is marked unresolved without naming what is missing",
            )
            unresolved.add(identifier)

    shared = graph.get("shared_prerequisite_nodes", [])
    require(shared, "Shared prerequisite nodes removed")
    shared_ids = {item.get("node") for item in shared}
    for item in shared:
        require(
            item.get("status") in {"RESOLVED", "UNRESOLVED"},
            "Unknown shared prerequisite status",
        )
        require(item.get("blocks"), "Shared prerequisite blocks nothing")
        require(item.get("reason"), "Shared prerequisite has no reason")
        if item.get("status") == "UNRESOLVED":
            for blocked in item["blocks"]:
                require(
                    blocked in unresolved,
                    f"{blocked} depends on an unresolved prerequisite but is marked resolved",
                )

    for node in nodes:
        for upstream in node.get("depends_on", []):
            require(
                upstream in EXPECTED_GRAPH_NODES | shared_ids,
                f"{node['test_id']} depends on an unknown node {upstream}",
            )
            if upstream in unresolved and node["test_id"] in resolved:
                raise ValidationError(
                    f"{node['test_id']} is resolved above the unresolved {upstream}"
                )
    require(graph.get("traversal_rule"), "Traversal rule removed")
    return unresolved, resolved


def _validate_alpha(record: dict) -> None:
    alpha = record.get("workstream_a_alpha", {})

    ct18 = alpha.get("a1_ct18_exact_representation", {})
    require(ct18.get("status") == "RESOLVED", "CT18 representation not resolved")
    require(ct18.get("alphas_type") == "ipol", "CT18 alpha type changed")
    require(ct18.get("stored_q_points") == 37, "CT18 knot count changed")
    require(ct18.get("stored_alphas_values") == 37, "CT18 value count changed")
    require(
        "log" in ct18.get("interpolation_variable", "").lower(),
        "CT18 interpolation variable lost",
    )
    clamp = ct18.get("discontinuous_clamp", {})
    require(clamp.get("source_line"), "Discontinuous clamp locator missing")
    require(
        "max" in clamp.get("expression", "").lower(),
        "Discontinuous clamp expression missing",
    )
    require(clamp.get("consequence"), "Discontinuous clamp consequence missing")
    partition = ct18.get("domain_partition_verified", {})
    require(partition.get("in_domain_knots") == 21, "In-domain knot count changed")
    require(partition.get("unique_breakpoints") == 24, "Breakpoint count changed")
    require(partition.get("root_intervals") == 23, "Root interval count changed")
    require(
        partition.get("intervals_at_or_below_mb", 0)
        + partition.get("intervals_above_mb", 0)
        == partition.get("root_intervals"),
        "Root interval arithmetic inconsistent",
    )

    apfel = alpha.get("a2_apfel_exact_mathematics", {})
    require(apfel.get("status") == "RESOLVED", "APFEL mathematics not resolved")
    require(
        apfel.get("source_file_hashes_reverified", {}).get("all_match_v3") is True,
        "APFEL source hashes no longer match V3",
    )
    four_pi = apfel.get("four_pi_conclusion", {})
    require(four_pi.get("resolved") is True, "The 4*pi convention is not resolved")
    require(four_pi.get("v3_open_item_closed") is True, "V3 4*pi open item not closed")
    require(
        four_pi.get("pi_binary64_hex") == "400921fb54442d18",
        "APFEL pi constant identity changed",
    )
    require(
        four_pi.get("pi_is_nearest_binary64_to_pi") is True,
        "APFEL pi constant claim changed",
    )
    require(
        "4d0 * pi" in four_pi.get("body", ""),
        "The 4*pi conversion body is missing",
    )
    rk4 = apfel.get("rk4", {})
    require(rk4.get("nstep") == 10, "APFEL RK4 step count changed")
    require(rk4.get("adaptivity") == "none", "APFEL RK4 adaptivity claim changed")
    sixth = rk4.get("sixth_literal", {})
    require(
        sixth.get("binary64_hex") == "3fc555555555553d",
        "Truncated one-sixth literal identity changed",
    )
    require(
        sixth.get("exact_one_sixth_hex") == "3fc5555555555555",
        "Exact one-sixth reference changed",
    )
    require(
        sixth.get("binary64_hex") != sixth.get("exact_one_sixth_hex"),
        "Truncated literal collapsed onto exact one sixth",
    )
    thresholds = apfel.get("threshold_semantics", {})
    require(
        thresholds.get("asymmetry_is_real") is True,
        "Threshold equality asymmetry erased",
    )
    require(
        "greater than or equal" in thresholds.get("final_flavour_selection", ""),
        "Final flavour threshold comparison lost",
    )
    require(
        "strictly greater" in thresholds.get("initial_flavour_selection", ""),
        "Initial flavour threshold comparison lost",
    )

    backend = alpha.get("a3_interval_backend", {})
    require(backend.get("decision") in BACKEND_DECISIONS, "Unknown backend decision")
    serialized = json.dumps(backend)
    if backend.get("decision") == "ALPHA_BACKEND_BOUND":
        selected = backend.get("selected", {})
        transcendental = selected.get("transcendental_backend", {})
        rational = selected.get("rational_core", {})
        require(
            ACCEPTED_BACKEND_TOKEN in transcendental.get("identity", ""),
            "Bound backend is not the declared rigorous one",
        )
        require(
            len(transcendental.get("cp310_wheel_sha256", "")) == 64,
            "Bound backend has no wheel identity",
        )
        require(
            transcendental.get("probe_qualification"),
            "Backend probe qualification removed",
        )
        require(len(rational.get("sha256", "")) == 64, "Rational core has no hash identity")
        require(rational.get("guarantee"), "Rational core guarantee missing")
    rejected = {item.get("candidate", "") for item in backend.get("evaluated_and_rejected", [])}
    require(
        any(token in " ".join(rejected) for token in REJECTED_BACKEND_TOKENS),
        "mpmath is no longer explicitly rejected",
    )
    require(
        "not enclose the logarithm the frozen providers actually call" in serialized
        or backend.get("critical_qualification"),
        "Backend qualification removed",
    )

    a5 = alpha.get("a5_apfel_continuous_enclosure", {})
    require(
        a5.get("method_finding", {}).get("headline") == "VALIDATED_IVP_INTEGRATION_IS_NOT_REQUIRED",
        "Validated-IVP finding changed",
    )
    require(
        a5.get("method_finding", {}).get("what_it_does_not_claim"),
        "The recursion-versus-differential-equation distinction was dropped",
    )
    require(
        a5.get("evidence", {}).get("physics_executed") is False,
        "Alpha evidence claims physics execution",
    )

    a6 = alpha.get("a6_consistency_claim", {})
    require(a6.get("decision") in ALPHA_CLAIMS, "Unknown alpha consistency claim")
    require(a6.get("no_tolerance_manufactured") is True, "A tolerance was manufactured")
    if a6.get("criterion_status") != "RESOLVED":
        require(a6.get("why_unresolved"), "Unresolved criterion has no reason")

    libm = alpha.get("libm_finding", {})
    require(
        libm.get("status") in {"RESOLVED", "UNRESOLVED_AND_LOAD_BEARING"},
        "Unknown libm finding status",
    )
    if libm.get("status") != "RESOLVED":
        require(len(libm.get("evidence", [])) >= 2, "libm finding lacks source evidence")
        require(libm.get("guard_implemented"), "libm guard not recorded")

    require(
        alpha.get("outcome")
        in {"ALPHA_RESOLVED", "ALPHA_BLOCKER_REMAINS_NARROWED", "ALPHA_BLOCKER_REMAINS"},
        "Unknown Workstream A outcome",
    )


def _validate_references(record: dict) -> None:
    references = record.get("workstream_b_references", {})

    massivedis = references.get("b1_massivedis_executable_provenance", {})
    require(massivedis.get("decision") in FONLL_REF_CLASSES, "Unknown FONLL reference class")
    require(len(massivedis.get("archive_sha256", "")) == 64, "MassiveDIS archive hash missing")
    coverage = massivedis.get("observable_coverage", {})
    for key in ("f2c", "flc", "f3"):
        require(key in coverage, f"MassiveDIS coverage entry {key} missing")
    fonll_config = massivedis.get("fonll_a_configuration", {})
    require(
        fonll_config.get("binding_status") in {"BOUND", "NOT_BOUND"},
        "Unknown FONLL scheme binding status",
    )
    if fonll_config.get("binding_status") == "NOT_BOUND":
        require(fonll_config.get("why"), "Unbound scheme correspondence has no reason")
    if massivedis.get("decision") == "FONLL_REF_EXECUTABLE_FULLY_SPECIFIED":
        require(
            massivedis.get("published_configuration_reconstructable") is True,
            "A fully specified reference must have a reconstructable configuration",
        )
        require(
            fonll_config.get("binding_status") == "BOUND",
            "A fully specified reference must bind the scheme correspondence",
        )
        require(
            massivedis.get("numerical_error_certificate", {}).get("available") is True,
            "A fully specified reference must supply a numerical error certificate",
        )
        require(
            massivedis.get("internal_work_bound", {}).get("derivable") is True,
            "A fully specified reference must have a derivable work bound",
        )
    else:
        require(
            massivedis.get("published_configuration_reconstructable") is False,
            "Reference is blocked yet the configuration is claimed reconstructable",
        )
        require(massivedis.get("why_not"), "Blocked reference gives no reason")
    certificate = massivedis.get("numerical_error_certificate", {})
    require("available" in certificate, "MassiveDIS error certificate status missing")
    if certificate.get("available") is False:
        require(certificate.get("evidence"), "Missing error certificate has no evidence")

    search = references.get("b2_alternative_independent_comparator", {})
    require(search.get("search_performed") is True, "Bounded comparator search not recorded")
    candidates = search.get("candidates", [])
    require(candidates, "Comparator search recorded no candidates")
    assessments = {item.get("name"): item.get("assessment") for item in candidates}
    require(
        assessments.get("APFEL++") == "REJECTED_AS_INDEPENDENT",
        "APFEL++ is no longer rejected as an independent comparator",
    )

    massless = references.get("b3_massless_benchmark_execution_contract", {})
    require(massless.get("decision") in MASSLESS_REF_CLASSES, "Unknown massless reference class")
    require(
        "displayed-digit" in massless.get("decision_rule", ""),
        "Massless decision rule is not publication-precision containment",
    )
    discrepancy = massless.get("prose_versus_code_discrepancy", {})
    require(
        discrepancy.get("matches_stated_epsilon") is False,
        "Prose-versus-code discrepancy erased",
    )
    if massless.get("decision") != "MASSLESS_REF_FULLY_SPECIFIED":
        require(massless.get("still_blocking"), "Blocked massless gate names nothing")

    rules = references.get("b4_reference_decision_rules", {})
    require(rules.get("global_budget_created") is False, "A global error budget was created")
    for rule in rules.get("rules", []):
        require(
            rule.get("mode")
            in {"REPLICATE_PUBLISHED_CONFIGURATION", "GENERAL_SIMULATOR_CLOSURE"},
            "Unknown reference comparison mode",
        )
        require(rule.get("transferable") is False, "A reference tolerance was made transferable")
    require(rules.get("explicit_nontransfer"), "Non-transfer statement removed")

    graph = references.get("b5_reference_graph", [])
    require(graph, "Reference graph removed")
    unvalidated = [
        node
        for node in graph
        if node.get("load_bearing") and node.get("validation_kind") == "unvalidated"
    ]
    require(
        references.get("load_bearing_unvalidated_nodes_present") == bool(unvalidated),
        "Unvalidated load-bearing node inventory is inconsistent",
    )
    require(
        references.get("outcome")
        in {"REFERENCE_RESOLVED", "REFERENCE_BLOCKER_REMAINS"},
        "Unknown Workstream B outcome",
    )


def _validate_convergence(record: dict) -> None:
    convergence = record.get("workstream_c_convergence", {})

    decision = convergence.get("c1_requirement_decision", {})
    require(decision.get("answer") in C1_ANSWERS, "Unknown C1 answer")
    require(decision.get("c1a_assessment", {}).get("derivation"), "C1A has no derivation")
    require(decision.get("c1b_assessment", {}).get("reason"), "C1B has no reason")
    require(
        decision.get("no_requirement_was_weakened_for_convenience") is True,
        "A requirement was weakened for convenience",
    )
    require(
        decision.get("no_stronger_requirement_was_imposed_than_the_claim_needs") is True,
        "A stronger requirement than the claim needs was imposed",
    )

    rigorous = convergence.get("c2_rigorous_route", {})
    require(rigorous.get("investigated"), "Rigorous quadrature routes not investigated")
    require(
        rigorous.get("precondition_satisfied") in {True, False},
        "Rigorous route precondition undecided",
    )

    empirical = convergence.get("c3_empirical_route", {})
    require(
        empirical.get("precision_target_derivable") in {True, False},
        "Precision target derivability undecided",
    )
    require(empirical.get("no_target_manufactured") is True, "A precision target was manufactured")
    if empirical.get("precision_target_derivable") is False:
        require(empirical.get("why_it_fails"), "Missing target has no explanation")
        require(
            empirical.get("outcome") == "WORKSTREAM_C_REMAINS_BLOCKED",
            "Missing target did not block Workstream C",
        )

    tests = convergence.get("c4_analytic_software_tests", {})
    require(tests.get("exact_integral_cases"), "Analytic quadrature cases removed")
    require(
        len(tests.get("exact_integral_cases", [])) >= 4,
        "Analytic quadrature coverage reduced below four regularity classes",
    )
    require(
        "do not prove" in tests.get("scope", ""),
        "Analytic tests are no longer scoped to software mechanics",
    )
    counterexample = tests.get("counterexample", {})
    require(counterexample.get("finding"), "Convergence counterexample removed")
    require(
        counterexample.get("first_difference") == 0.0
        and counterexample.get("second_difference") == 0.0,
        "Counterexample differences changed",
    )
    require(
        counterexample.get("true_error_of_both_paths", 0) > 0,
        "Counterexample no longer demonstrates an unbounded error",
    )
    require(counterexample.get("scope_limit"), "Counterexample scope limit removed")

    grid = convergence.get("c5_grid_gate", {})
    separation = grid.get("separation", {})
    for key in (
        "pointwise_validation_coverage",
        "numerical_interpolation_or_discretisation_error",
        "continuum_physics_claim",
    ):
        require(key in separation, f"Grid gate separation entry {key} missing")
    require(grid.get("conclusion"), "Grid gate conclusion removed")
    require(
        grid.get("recommended_successor_redesign", {}).get("not_applied_to_v3"),
        "Grid redesign was not kept out of V3",
    )

    require(
        convergence.get("outcome")
        in {"NUMERICAL_CONVERGENCE_RESOLVED", "NUMERICAL_CONVERGENCE_BLOCKER_REMAINS"},
        "Unknown Workstream C outcome",
    )


def _validate_environment(record: dict) -> None:
    environment = record.get("workstream_d_environment", {})
    require(
        environment.get("reproducibility_classification") in REPRODUCIBILITY_CLASSES,
        "Unknown reproducibility classification",
    )
    if environment.get("reproducibility_classification") != "BITWISE_SAME_FROZEN_ENVIRONMENT":
        require(environment.get("bitwise_claim") is False, "Bitwise claim overreaches")
        require(environment.get("bitwise_claim_reason"), "Bitwise refusal has no reason")
    if (
        environment.get("reproducibility_classification")
        == "NUMERICALLY_REPRODUCIBLE_WITH_FROZEN_SOFTWARE_IDENTITY"
    ):
        require(
            environment.get("native_code_identity", {}).get("libm_identity_bound") is True,
            "Numerical reproducibility claimed while the libm identity is unbound",
        )
    else:
        require(
            environment.get("why_not_numerically_reproducible_with_frozen_software_identity"),
            "The weaker reproducibility class was declined without a reason",
        )
    native = environment.get("native_code_identity", {})
    require(native.get("load_bearing_native_components"), "Native component inventory removed")
    if native.get("libm_identity_bound") is False:
        require(native.get("reason"), "Unbound libm identity has no reason")
        require(
            environment.get("reproducibility_classification")
            != "BITWISE_SAME_FROZEN_ENVIRONMENT",
            "Bitwise reproducibility claimed with an unbound libm",
        )
    cpython = environment.get("cpython", {})
    require(cpython.get("target") == "3.10.20", "Frozen CPython target changed")
    if cpython.get("executable_bound") is False:
        require(cpython.get("note"), "Unbound interpreter has no note")


def _validate_resources(record: dict) -> None:
    resources = record.get("resource_model", {})
    categories = resources.get("categories", [])
    names = {item.get("category") for item in categories}
    require(names == EXPECTED_RESOURCE_CATEGORIES, "Resource category set changed")
    require(len(categories) == len(names), "Duplicate resource category")

    has_null = False
    for item in categories:
        require(item.get("unit"), f"Resource category {item.get('category')} has no unit")
        value = item.get("value")
        if value is None:
            has_null = True
            require(item.get("reason"), f"Null resource {item.get('category')} has no reason")
        else:
            require(
                isinstance(value, int) and value > 0,
                f"Resource category {item.get('category')} is not a positive integer",
            )
            require(item.get("source"), f"Resource {item.get('category')} has no source")

    require(
        resources.get("every_category_finite") is (not has_null),
        "Resource finiteness claim contradicts the category values",
    )
    if has_null:
        require(
            resources.get("aggregate_status") == "BLOCKED_NOT_DERIVABLE",
            "An aggregate was formed over null categories",
        )
        require(resources.get("aggregate_blocker"), "Aggregate blocker has no reason")
        require(resources.get("why_not"), "Missing finiteness has no explanation")
    require("never summed" in resources.get("policy", "") or "No heterogeneous aggregate" in resources.get("policy", ""), "Aggregation policy removed")

    lookup = {item["category"]: item.get("value") for item in categories}
    require(lookup["physics_evaluator_calls"] == 63882, "Rate evaluation count changed")
    require(lookup["bridge_evaluator_calls"] == 1045, "Bridge callback count changed")
    require(lookup["analytic_unit_test_calls"] == 216, "Analytic case count changed")
    require(
        lookup["quadrature_integrand_calls"] == 9 * (16**2 + 32**2 + 64**2) + 9 * (17**2 + 33**2 + 65**2),
        "Quadrature integrand arithmetic inconsistent",
    )


def _validate_outcome(record: dict, unresolved: set[str], expected_outcome: str | None) -> None:
    outcome = record.get("outcome", {})
    code = outcome.get("code")
    require(code in OUTCOMES, "Unknown blocker-resolution outcome")
    require(outcome.get("derivation"), "Outcome has no derivation")

    blockers = outcome.get("blockers_remaining", [])
    identifiers = {item.get("id") for item in blockers}
    require(len(identifiers) == len(blockers), "Duplicate remaining blocker id")
    for blocker in blockers:
        require(blocker.get("family"), "Remaining blocker has no family")
        require(blocker.get("missing"), "Remaining blocker names nothing missing")
        require(blocker.get("would_be_resolved_by"), "Remaining blocker has no resolution path")

    if code == "BR1_ALL_PREAUTH_BLOCKERS_RESOLVED":
        require(not blockers, "BR1 declared with remaining blockers")
        require(not unresolved, "BR1 declared with unresolved graph nodes")
        require(
            record.get("workstream_a_alpha", {}).get("outcome") == "ALPHA_RESOLVED",
            "BR1 declared with an unresolved Workstream A",
        )
        require(
            record.get("workstream_b_references", {}).get("outcome") == "REFERENCE_RESOLVED",
            "BR1 declared with an unresolved Workstream B",
        )
        require(
            record.get("workstream_c_convergence", {}).get("outcome")
            == "NUMERICAL_CONVERGENCE_RESOLVED",
            "BR1 declared with an unresolved Workstream C",
        )
        require(
            record.get("resource_model", {}).get("every_category_finite") is True,
            "BR1 declared with a null resource category",
        )
        require(
            not record.get("workstream_b_references", {}).get(
                "load_bearing_unvalidated_nodes_present"
            ),
            "BR1 declared with a load-bearing unvalidated node",
        )
        require(outcome.get("v4_created") is True, "BR1 did not produce V4")
    else:
        require(blockers, f"{code} declared with no remaining blockers")
        require(unresolved, f"{code} declared while every graph node is resolved")
        require(outcome.get("v4_created") is False, "V4 created for a non-BR1 outcome")
        require(outcome.get("why_no_v4"), "Non-BR1 outcome does not explain the absent V4")
        require(
            outcome.get("new_authorization_review_warranted") is False,
            "A non-BR1 outcome warrants an authorization review",
        )
        require(
            outcome.get("why_no_authorization_review"),
            "Non-BR1 outcome does not explain the absent authorization review",
        )
        families = {item.get("family") for item in blockers}
        if code == "BR2_ALPHA_BLOCKER_REMAINS":
            require(families == {"A_ALPHA"}, "BR2 blocker families inconsistent")
        elif code == "BR3_REFERENCE_BLOCKER_REMAINS":
            require(families == {"B_REFERENCE"}, "BR3 blocker families inconsistent")
        elif code == "BR4_NUMERICAL_CONVERGENCE_BLOCKER_REMAINS":
            require(families == {"C_CONVERGENCE"}, "BR4 blocker families inconsistent")
        else:
            require(len(families) > 1, "BR5 declared with a single blocker family")

    if expected_outcome is not None:
        require(code == expected_outcome, "Wrong blocker-resolution outcome")


def _validate_state(record: dict) -> None:
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
    require(
        record.get("non_dis_validation_evidence", {}).get("physics_executed") is False,
        "Non-DIS evidence claims physics execution",
    )
    require(record.get("remaining_scientific_limitations"), "Scientific limitations removed")
    require(record.get("next_step"), "Next step removed")

    serialized = json.dumps(record)
    for token in FORBIDDEN_TOLERANCE_TOKENS:
        require(token not in serialized, f"Rejected tolerance {token} reintroduced")


def validate(
    record: dict,
    *,
    root: Path = ROOT,
    check_docs: bool = True,
    check_files: bool = True,
    expected_outcome: str | None = EXPECTED_OUTCOME,
) -> None:
    require(record.get("schema_version") == SCHEMA, "Wrong schema version")
    require(
        record.get("record_type") == "PHASE2B_PREAUTHORIZATION_BLOCKER_RESOLUTION_V1",
        "Wrong record type",
    )
    _validate_history(record)
    _validate_predecessors(record, root, check_files)
    unresolved, _ = _validate_graph(record)
    _validate_alpha(record)
    _validate_references(record)
    _validate_convergence(record)
    _validate_environment(record)
    _validate_resources(record)
    _validate_outcome(record, unresolved, expected_outcome)
    _validate_state(record)

    if check_docs:
        markers = {
            "docs/reduced_nc_dis/PHASE2B_BLOCKER_RESOLUTION_V1.md": [
                EXPECTED_OUTCOME,
                "ALPHA_BACKEND_BOUND",
                "FONLL_REF_PUBLISHED_ONLY",
                "MASSLESS_REF_PARTIAL",
                "ENVIRONMENT_REPRODUCIBILITY_UNRESOLVED",
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
        raise SystemExit(f"INVALID phase2b.blocker_resolution_v1: {error}") from error
    print("VALID phase2b.blocker_resolution_v1")


if __name__ == "__main__":
    main()
