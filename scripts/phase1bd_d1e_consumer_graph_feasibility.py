#!/usr/bin/env python3
"""Generate and validate the planning-only D1E AST-graph feasibility record.

This module describes a future static-evidence task. It does not invoke an AST
extractor, create a compilation database, build a graph, or execute generator
or physics software.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

SCHEMA = "partonsbi.phase1bd.d1e.consumer-graph-feasibility.v2"
ARTIFACT = "docs/phase1bd_d1e_consumer_graph_feasibility.json"
SEARCH_MANIFEST = "docs/phase1bd_d1d_pythia_semantics_search_manifest.json"
RELEASE_ROOT = ".external/src/releases-pythia8312"

ALLOWED_DECISIONS = {
    "FEASIBLE_FOR_SEPARATE_STATIC_EVIDENCE_TASK",
    "INCONCLUSIVE",
    "DO_NOT_PROCEED",
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
TOOLCHAIN_IDS = (
    "LLVM_CLANG_LIBTOOLING_18_1_8",
    "CLANG_AST_JSON_QUERY_NORMALIZER_18_1_8",
    "CODEQL_CPP_2_25_5",
)
ROOT_CLASSES = (
    "PYTHIA8_PDF_PROVIDER_TYPE_AND_ACTUAL_DERIVED_TYPES",
    "PDF_POINTER_DECLARATIONS_AND_FIELDS",
    "SIXTEEN_PDF_POINTER_ROLES",
    "POINTER_CONSTRUCTION_ASSIGNMENT_AND_INSTALLATION",
    "BEAM_PARTICLE_FORWARDING_INTERFACES",
    "PUBLIC_XF_XFVAL_XFSEA_READERS",
    "PROTECTED_OR_VIRTUAL_PROVIDER_UPDATE_INTERFACES",
    "PDF_DERIVED_CACHES",
    "ALPHA_S_PROVIDERS_AND_ROUTING",
    "HARD_PROCESS_NEUTRAL_CURRENT_CONSUMERS",
    "ISR_BACKWARD_EVOLUTION_CONSUMERS",
    "BEAM_REMNANT_CONSUMERS",
    "EXPLICIT_LHA_COMPLETE_EVENT_WEIGHT_BOUNDARIES",
)
POINTER_ROLES = (
    "pdfAPtr",
    "pdfBPtr",
    "pdfHardAPtr",
    "pdfHardBPtr",
    "pdfPomAPtr",
    "pdfPomBPtr",
    "pdfGamAPtr",
    "pdfGamBPtr",
    "pdfHardGamAPtr",
    "pdfHardGamBPtr",
    "pdfUnresAPtr",
    "pdfUnresBPtr",
    "pdfUnresGamAPtr",
    "pdfUnresGamBPtr",
    "pdfVMDAPtr",
    "pdfVMDBPtr",
)
EDGE_KINDS = (
    "DECLARES",
    "HAS_STATIC_TYPE",
    "POINTS_TO",
    "ASSIGNED_FROM",
    "MAY_ALIAS",
    "PASSED_AS_ARGUMENT",
    "RECEIVED_AS_PARAMETER",
    "RETURNS",
    "RETURN_VALUE_CONSUMED_BY",
    "CALLS",
    "VIRTUAL_DISPATCH_CANDIDATE",
    "READS_FIELD",
    "WRITES_FIELD",
    "CACHE_WRITE",
    "CACHE_READ",
    "ARITHMETIC_DEPENDENCY",
    "CONDITION_DEPENDENCY",
    "CATEGORICAL_SELECTION_DEPENDENCY",
    "DENOMINATOR_DEPENDENCY",
    "MAXIMUM_OR_ENVELOPE_DEPENDENCY",
    "EVENT_WEIGHT_DEPENDENCY",
)
UNRESOLVED_STATES = (
    "UNRESOLVED_ALIAS",
    "UNRESOLVED_VIRTUAL_TARGET",
    "FUNCTION_POINTER_UNRESOLVED",
    "TEMPLATE_INSTANTIATION_NOT_MATERIALIZED",
    "MACRO_GENERATED_USE_UNRESOLVED",
    "EXTERNAL_LIBRARY_BOUNDARY",
    "RUNTIME_SELECTED_PROVIDER",
    "POST_INIT_POINTER_REPLACEMENT",
    "CONFIGURATION_DEPENDENT_REACHABILITY",
    "MISSING_TRANSLATION_UNIT",
    "PARSE_FAILURE",
)
NEGATIVE_CONTROL_IDENTIFIERS = ("state", "size", "id", "push_back", "p", "Vec4")
FALSE_NEGATIVE_CLASSES = (
    "NEUTRAL_NAME_ALIASES",
    "MEMBER_WRITES_READ_IN_ANOTHER_FUNCTION",
    "PARAMETER_PROPAGATION",
    "RETURN_TO_CALLER_PROPAGATION",
    "REFERENCES_AND_POINTERS",
    "TEMPLATES",
    "MACROS",
    "VIRTUAL_DISPATCH",
    "HELPER_WRAPPERS",
    "NEUTRAL_NAME_CACHE_VARIABLES",
)
GATE_IDS = (
    "G01_AUTHORITATIVE_CORPUS_IDENTITY_COMPLETE",
    "G02_EVERY_REQUIRED_TRANSLATION_UNIT_PARSED",
    "G03_COMPILE_COMMAND_REPLAY_DETERMINISTIC",
    "G04_TYPED_ROOTS_COMPLETE",
    "G05_NO_NAME_OR_HISTORICAL_FALLBACK",
    "G06_EVERY_EDGE_SOURCE_SUPPORTED",
    "G07_INTERPROCEDURAL_ARGUMENT_PARAMETER_RETURN_FLOW",
    "G08_MEMBER_CACHE_WRITE_READ_FLOW",
    "G09_ALIAS_AND_VIRTUAL_TARGETS_RESOLVED_OR_BLOCKING",
    "G10_SIXTEEN_POINTER_ROLES_LOCALLY_ACCOUNTED",
    "G11_ALPHA_S_ROUTING_ACCOUNTED",
    "G12_HARD_ISR_REMNANT_PATHS_REPRESENTED",
    "G13_HOLDOUT_RECOVERY_ZERO_UNRESOLVED_OR_NOT_RECOVERED",
    "G14_NEGATIVE_CONTROLS_PASS",
    "G15_FALSE_NEGATIVE_CHALLENGE_NO_MATERIAL_MISS",
    "G16_GRAPH_GENERATION_SERIALIZATION_DETERMINISTIC",
    "G17_INDEPENDENT_REVIEW_REPRODUCES",
    "G18_RUNTIME_LIMITATIONS_NOT_STATIC_CLOSURE",
)
FEASIBILITY_CONDITION_IDS = (
    "toolchain_identity_supported",
    "corpus_identity_supported",
    "compile_contract_supported",
    "relation_representation_supported",
    "typed_root_contract_complete",
    "alias_dispatch_policy_complete",
    "interprocedural_plan_complete",
    "member_cache_plan_complete",
    "calibration_contract_complete",
    "false_negative_contract_complete",
    "static_runtime_boundary_complete",
    "implementation_cost_bounded",
    "independent_review_cost_bounded",
    "stop_conditions_machine_checkable",
    "scientific_contract_unchanged",
    "acceptance_contract_complete",
    "source_lineage_portable_or_explicitly_qualified",
)
FEASIBILITY_STATUSES = {
    "SUPPORTED",
    "SUPPORTED_WITH_QUALIFICATION",
    "NOT_SUPPORTED",
    "NOT_EVALUATED",
}


class FeasibilityError(RuntimeError):
    """Raised when the planning evidence contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FeasibilityError(message)


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_release_inventory(repo: Path) -> tuple[list[dict[str, Any]], list[str], str]:
    manifest = json.loads((repo / SEARCH_MANIFEST).read_text(encoding="utf-8"))
    prefix = f"{RELEASE_ROOT}/"
    selected = sorted(
        (
            row
            for row in manifest["searched_files"]
            if row["path"].startswith(prefix)
            and (row["path"].endswith(".h") or row["path"].endswith(".cc"))
        ),
        key=lambda row: row["path"],
    )
    inventory = [
        {
            "bytes": row["bytes"],
            "evidence_file_id": row["file_id"],
            "path": row["path"],
            "semantic_file_id": f"PY8312-{index:04d}",
            "sha256": row["sha256"],
        }
        for index, row in enumerate(selected, 1)
    ]
    translation_units = [
        row["semantic_file_id"] for row in inventory if row["path"].endswith(".cc")
    ]
    identity_rows = [
        {key: row[key] for key in ("bytes", "path", "sha256")} for row in inventory
    ]
    return inventory, translation_units, canonical_hash(identity_rows)


@lru_cache(maxsize=1)
def verified_source_hashes(repo_text: str) -> tuple[tuple[str, int, str], ...]:
    repo = Path(repo_text)
    inventory, _, _ = load_release_inventory(repo)
    rows = []
    for row in inventory:
        path = repo / row["path"]
        require(path.is_file(), f"authoritative source file is missing: {row['path']}")
        rows.append((row["path"], path.stat().st_size, file_sha256(path)))
    return tuple(rows)


def verify_source_bytes_when_available(
    repo: Path, expected_inventory: list[dict[str, Any]]
) -> bool:
    """Check ignored source bytes when present; clean CI remains manifest-only."""
    if not (repo / RELEASE_ROOT).is_dir():
        return False
    actual = verified_source_hashes(str(repo.resolve()))
    expected = tuple(
        (row["path"], row["bytes"], row["sha256"]) for row in expected_inventory
    )
    require(actual == expected, "authoritative source bytes differ from inventory")
    return True


def capability(
    responsibility_class: str,
    support: str,
    evidence: str,
    limitation: str,
    future_requirement: str,
) -> dict[str, str]:
    return {
        "responsibility_class": responsibility_class,
        "support": support,
        "primary_evidence": evidence,
        "limitation": limitation,
        "future_requirement": future_requirement,
    }


def build_toolchains() -> list[dict[str, Any]]:
    llvm_identity = {
        "tool": "LLVM/Clang LibTooling and Clang Tooling API",
        "version": "18.1.8",
        "release_tag": "llvmorg-18.1.8",
        "release_commit_sha": "3b5b5c1ec4a3095ab096dd780e84d7ab81f3d7ff",
        "official_repository": "https://github.com/llvm/llvm-project",
        "official_documentation": "https://releases.llvm.org/18.1.8/tools/clang/docs/LibTooling.html",
        "license": "Apache-2.0 WITH LLVM-exception",
        "identity_verification_status": "SUPPORTED",
    }
    clang_capabilities = {
        "cxx_language_and_templates": capability(
            "CLANG_AST_DIRECTLY_PROVIDES",
            "SUPPORTED_WITH_QUALIFICATION",
            "Clang exposes typed declarations and materialized template instances for parsed C++11 translation units.",
            "Cross-TU specialization identity and unmaterialized instances are not supplied as a complete graph.",
            "Repository analysis must identify specializations across TUs and fail closed on an unmaterialized required instance.",
        ),
        "macro_handling": capability(
            "CLANG_AST_DIRECTLY_PROVIDES",
            "SUPPORTED_WITH_QUALIFICATION",
            "Clang source locations expose spelling and expansion coordinates.",
            "A stable macro identity and expansion policy is not automatic.",
            "Repository analysis must serialize both coordinates or emit MACRO_GENERATED_USE_UNRESOLVED.",
        ),
        "dynamic_dispatch": capability(
            "REPOSITORY_ANALYSIS_MUST_IMPLEMENT",
            "SUPPORTED_WITH_QUALIFICATION",
            "Clang anchors typed virtual calls and class declarations.",
            "Runtime-selected concrete targets cannot be statically proven by this record.",
            "Construct source-backed candidate sets under explicit closed-world conditions and block every open set.",
        ),
        "interprocedural_call_and_return": capability(
            "REPOSITORY_ANALYSIS_MUST_IMPLEMENT",
            "SUPPORTED_WITH_QUALIFICATION",
            "Clang anchors call expressions, declarations, parameters, returns, and parsed overload resolution.",
            "AST traversal does not supply complete cross-TU argument/parameter or return/caller flow.",
            "Implement stable cross-TU call, parameter, and return matching with unresolved external boundaries.",
        ),
        "field_member_dataflow": capability(
            "REPOSITORY_ANALYSIS_MUST_IMPLEMENT",
            "SUPPORTED_WITH_QUALIFICATION",
            "Clang anchors field declarations and member expressions with static types.",
            "Cross-function member and cache write/read flow is not automatic.",
            "Index field identity and source-supported writes and reads across the corpus.",
        ),
        "alias_pointer_analysis": capability(
            "REPOSITORY_ANALYSIS_MUST_IMPLEMENT",
            "SUPPORTED_WITH_QUALIFICATION",
            "Clang anchors typed pointer/reference assignments.",
            "General alias closure and post-init pointer replacement cannot be proven statically.",
            "Propagate only source-supported points-to facts and serialize every remaining alias as blocking.",
        ),
        "source_coordinate_stability": capability(
            "CLANG_AST_DIRECTLY_PROVIDES",
            "SUPPORTED_WITH_QUALIFICATION",
            "Clang provides spelling and expansion source coordinates.",
            "Coordinates depend on exact source bytes and compile arguments.",
            "Bind coordinates to source, toolchain, and canonical command hashes.",
        ),
        "deterministic_serialization": capability(
            "REPOSITORY_ANALYSIS_MUST_IMPLEMENT",
            "SUPPORTED_WITH_QUALIFICATION",
            "Typed declarations and coordinates provide possible stable anchors.",
            "Traversal order and compiler-internal identifiers are not stable artifact identities.",
            "Define canonical cross-TU symbol IDs, ordering, normalization, and byte equality.",
        ),
    }
    common = {
        "acquisition_and_pinning_strategy": {
            "installation_performed_in_this_task": False,
            "pin_is_immutable": True,
        },
        "wsl_availability": "NOT_CURRENTLY_INSTALLED",
        "expected_unresolved_classes": list(UNRESOLVED_STATES),
    }
    codeql_sources = [
        {
            "source_id": "CODEQL_CLI_BINARY_TAG_V2_25_5",
            "canonical_url": "https://github.com/github/codeql-cli-binaries/releases/tag/v2.25.5",
            "immutable_identity": "697ca25a6968ae01bab1b11ae56c3be5960f588c",
            "claim_scope": ["official_cli_version_tag_identity"],
        },
        {
            "source_id": "CODEQL_QUERY_TAG_V2_25_5",
            "canonical_url": "https://github.com/github/codeql/tree/codeql-cli/v2.25.5",
            "immutable_identity": "b551e89ea8e011c0e3301fd0ce05589c9f2d3681",
            "claim_scope": ["official_query_repository_tag_identity", "query_repository_mit_license"],
        },
        {
            "source_id": "CODEQL_CLI_TERMS_V2_25_5",
            "canonical_url": "https://github.com/github/codeql-cli-binaries/blob/v2.25.5/LICENSE.md",
            "immutable_identity": "versioned_file_at_tag:v2.25.5:LICENSE.md",
            "claim_scope": [
                "automated_ci_permitted_for_osi_licensed_codebase_hosted_and_maintained_on_github",
                "other_automated_ci_contexts_restricted_without_applicable_paid_license",
            ],
        },
    ]
    return [
        {
            "candidate_id": "LLVM_CLANG_LIBTOOLING_18_1_8",
            "exact_tool_identity": llvm_identity,
            **copy.deepcopy(common),
            "acquisition_and_pinning_strategy": {
                **common["acquisition_and_pinning_strategy"],
                "method": "A future separately authorized task would obtain llvmorg-18.1.8 and verify the peeled commit before installation.",
            },
            "license_assessment": "PINNED_APACHE_2_0_WITH_LLVM_EXCEPTION",
            "ci_availability": "NOT_IN_CURRENT_WORKFLOW_FUTURE_PINNED_JOB_REQUIRES_REVIEW",
            "capabilities": copy.deepcopy(clang_capabilities),
            "compilation_database_requirements": "Exact source-only argv arrays for all 120 TUs, including deterministic per-TU overrides.",
            "implementation_burden_person_weeks": 4.25,
            "independent_review_burden_person_weeks": 1.5,
            "candidate_feasibility": "PLAUSIBLE_FOUNDATION_REQUIRES_FURTHER_BOUNDING",
        },
        {
            "candidate_id": "CLANG_AST_JSON_QUERY_NORMALIZER_18_1_8",
            "exact_tool_identity": {
                **llvm_identity,
                "tool": "Clang AST JSON / clang-query plus repository-owned normalizer",
                "official_documentation": "https://releases.llvm.org/18.1.8/tools/clang/docs/IntroductionToTheClangAST.html",
            },
            **copy.deepcopy(common),
            "acquisition_and_pinning_strategy": {
                **common["acquisition_and_pinning_strategy"],
                "method": "A future task would use the same pinned Clang release and own all cross-TU normalization.",
            },
            "license_assessment": "PINNED_APACHE_2_0_WITH_LLVM_EXCEPTION",
            "ci_availability": "NOT_IN_CURRENT_WORKFLOW_FUTURE_PINNED_JOB_REQUIRES_REVIEW",
            "capabilities": copy.deepcopy(clang_capabilities),
            "compilation_database_requirements": "The same exact 120-TU command set; JSON output does not remove flag dependence.",
            "implementation_burden_person_weeks": 6.5,
            "independent_review_burden_person_weeks": 2.0,
            "candidate_feasibility": "PLAUSIBLE_BUT_NORMALIZER_SCOPE_NOT_BOUNDED",
        },
        {
            "candidate_id": "CODEQL_CPP_2_25_5",
            "exact_tool_identity": {
                "tool": "GitHub CodeQL CLI C/C++ database and query layer",
                "version": "2.25.5",
                "binary_release_tag": "v2.25.5",
                "binary_release_commit_sha": "697ca25a6968ae01bab1b11ae56c3be5960f588c",
                "query_repository_tag": "codeql-cli/v2.25.5",
                "query_repository_commit_sha": "b551e89ea8e011c0e3301fd0ce05589c9f2d3681",
                "official_binary_repository": "https://github.com/github/codeql-cli-binaries",
                "official_query_repository": "https://github.com/github/codeql",
                "identity_verification_status": "SUPPORTED",
            },
            **copy.deepcopy(common),
            "acquisition_and_pinning_strategy": {
                **common["acquisition_and_pinning_strategy"],
                "method": "A future review would pin the official CLI tag and query commit; no acquisition occurred here.",
            },
            "official_sources": codeql_sources,
            "license_assessment": {
                "status": "REPOSITORY_SPECIFIC_APPLICABILITY_NOT_ESTABLISHED",
                "versioned_terms_permit_some_automated_ci": True,
                "permitted_scope": "OSI-licensed codebases hosted and maintained on GitHub.com, subject to the versioned terms.",
                "repository_root_osi_license_identity_reviewed": False,
                "universal_ci_prohibition_claimed": False,
                "selection_effect": "BLOCKED_BY_REPOSITORY_SPECIFIC_LICENSE_DEPLOYMENT_AND_MODEL_STABILITY_UNCERTAINTY",
            },
            "ci_availability": "REPOSITORY_SPECIFIC_LICENSE_DEPLOYMENT_AND_MODEL_STABILITY_UNRESOLVED",
            "capabilities": {
                **copy.deepcopy(clang_capabilities),
                "interprocedural_call_and_return": capability(
                    "REPOSITORY_ANALYSIS_MUST_IMPLEMENT",
                    "SUPPORTED_WITH_QUALIFICATION",
                    "Official CodeQL C/C++ libraries expose local/global dataflow and call-graph APIs.",
                    "Model coverage and dynamic target completeness remain query- and version-dependent.",
                    "Pin queries, enumerate models, and fail closed on every unmodeled call.",
                ),
            },
            "compilation_database_requirements": "Exact source-only database creation adds capture, licensing, and deployment constraints.",
            "implementation_burden_person_weeks": 5.0,
            "independent_review_burden_person_weeks": 2.0,
            "candidate_feasibility": "NOT_SELECTED_LICENSE_DEPLOYMENT_AND_MODEL_STABILITY_UNRESOLVED",
        },
    ]


def build_acceptance_contract() -> dict[str, Any]:
    rows = (
        ("AC01_GRAPH_NODE_SCHEMA", "Define every node kind, required fields, stable node ID, and prohibited synthetic fields.", "schema_validate_all_nodes"),
        ("AC02_NODE_SOURCE_EVIDENCE", "Every node kind requires exact source coordinate, source hash, TU identity, and owning declaration or function.", "node_source_evidence_count_equals_node_count"),
        ("AC03_CROSS_TU_SYMBOL_IDENTITY", "Canonical symbol identity combines qualified declaration identity, signature, source identity, and linkage scope.", "zero_ambiguous_cross_tu_symbol_ids"),
        ("AC04_OVERLOAD_IDENTITY", "Overloads are distinct by canonical parameter and cv/ref/template signature.", "zero_unresolved_overload_bindings"),
        ("AC05_TEMPLATE_IDENTITY", "Primary templates, specializations, and materialized instantiations have distinct stable identities.", "zero_required_unmaterialized_template_paths"),
        ("AC06_ODR_RECONCILIATION", "Duplicate declarations are reconciled only with equivalent canonical declarations; conflicting definitions block closure.", "zero_odr_conflicts_or_unreconciled_duplicates"),
        ("AC07_GRAPH_PATH_VALIDITY", "A provenance path is an ordered root-to-consumer edge sequence with matching endpoints and source-backed transitions.", "all_admitted_units_have_valid_root_paths"),
        ("AC08_EDGE_COMPOSITION", "Only declared edge-kind compositions may propagate provenance; direct synthetic root-to-unit attachment is forbidden.", "zero_invalid_or_synthetic_edge_compositions"),
        ("AC09_STATIC_REACHABILITY", "Static reachability means a source-backed call/configuration path under the declared closed-world configuration, never filename inference.", "zero_final_reachability_without_static_path"),
        ("AC10_PROSPECTIVE_CONFIGURATION", "The future configuration manifest must fix enabled processes, showers, remnants, pointer roles, and disabled modules before graph interpretation.", "configuration_manifest_identity_present_and_complete"),
        ("AC11_EXCLUSION_RELEVANCE", "Every excluded module requires a source-backed proof that no required configuration path depends on it.", "zero_unproved_relevant_exclusions"),
        ("AC12_EXTERNAL_CALL_BOUNDARY", "External calls require a typed signature, modeled argument/return effect, or blocking EXTERNAL_LIBRARY_BOUNDARY.", "zero_unmodeled_binding_external_calls"),
        ("AC13_CALLBACK_FUNCTION_POINTER", "Callbacks and function pointers require a closed target set or blocking FUNCTION_POINTER_UNRESOLVED.", "zero_open_binding_callback_target_sets"),
        ("AC14_MATERIAL_MISS", "A material miss is any omitted source-backed PDF-derived path affecting hard, ISR, remnant, selection, ratio, envelope, or weight semantics.", "material_miss_count_equals_zero"),
        ("AC15_EXEMPTION_REVIEW", "Boundary/policy exemptions require an independent reviewer, exact source evidence, rationale, and non-dataflow justification.", "zero_unreviewed_or_invalid_exemptions"),
        ("AC16_MACRO_IDENTITY", "Macro-generated evidence records spelling and expansion identities and blocks when either coordinate cannot be stabilized.", "zero_unresolved_binding_macro_identities"),
        ("AC17_CLOSED_WORLD_VIRTUAL_TARGETS", "A virtual target set is closed only when corpus, class hierarchy, construction sites, and configuration exclusions are proven complete.", "zero_open_binding_virtual_target_sets"),
        ("AC18_NEUTRAL_WRAPPER_REGISTRATION", "Neutral wrappers and registration tables are discovered from typed call/assignment/registration relations, not names.", "zero_unresolved_binding_wrappers_or_registrations"),
        ("AC19_GRAPH_RESOURCE_CAPS", "Predeclared node, edge, memory, and serialized-byte caps stop with an explicit incomplete result when exceeded.", "resource_caps_declared_and_not_exceeded"),
        ("AC20_TIMEOUT_TRUNCATION", "Any timeout, depth limit, dropped TU, or truncation is serialized and blocks completeness.", "zero_timeout_or_truncation_events"),
        ("AC21_OVERALL_UNRESOLVED_CAP", "The total unresolved-record cap is predeclared; exceeding it blocks the evidence task rather than dropping records.", "unresolved_total_within_predeclared_cap"),
        ("AC22_REQUIRED_PATH_ZERO_UNRESOLVED", "Required hard-process, ISR, and remnant paths each require zero unresolved binding records.", "hard_isr_remnant_unresolved_binding_count_equals_zero"),
        ("AC23_INDEPENDENT_REVIEWER", "The reviewer must not author graph-construction rules or curate the construction input and must reproduce from pinned inputs.", "reviewer_independence_attested"),
        ("AC24_BLINDED_HOLDOUT", "The 672-member holdout stays inaccessible to construction and is evaluated only after graph serialization is frozen.", "holdout_access_audit_proves_post_freeze_only"),
        ("AC25_GATE_MACHINE_PREDICATES", "Every binding gate names deterministic input fields, a machine predicate, expected value, and failure output.", "all_gate_predicates_defined_and_executable"),
    )
    return {
        "contract_status": "SUPPORTED_WITH_QUALIFICATION",
        "qualification": "Definitions are binding and machine-oriented, but their future implementations and predicates have not been built or evaluated.",
        "sections": [
            {
                "section_id": section_id,
                "binding": True,
                "definition": definition,
                "machine_predicate": predicate,
                "planning_status": "NOT_EVALUATED_FUTURE_STATIC_EVIDENCE_CONTRACT",
            }
            for section_id, definition, predicate in rows
        ],
    }


def build_gates() -> list[dict[str, Any]]:
    specifications = (
        ("Authoritative source identity, inventory, mirrors, and exclusions reproduce exactly.", ("AC02_NODE_SOURCE_EVIDENCE", "AC11_EXCLUSION_RELEVANCE")),
        ("All 120 required translation units parse; one miss is a blocking failure.", ("AC19_GRAPH_RESOURCE_CAPS", "AC20_TIMEOUT_TRUNCATION")),
        ("Canonical compile argv and environment replay with exact set and byte equality.", ("AC03_CROSS_TU_SYMBOL_IDENTITY", "AC20_TIMEOUT_TRUNCATION")),
        ("All required roots arise from typed declarations, definitions, or assignments.", ("AC01_GRAPH_NODE_SCHEMA", "AC02_NODE_SOURCE_EVIDENCE", "AC09_STATIC_REACHABILITY")),
        ("Identifier, filename, historical, global, and synthetic fallback counts are zero.", ("AC07_GRAPH_PATH_VALIDITY", "AC08_EDGE_COMPOSITION", "AC18_NEUTRAL_WRAPPER_REGISTRATION")),
        ("Every graph edge has exact source support and valid composition.", ("AC02_NODE_SOURCE_EVIDENCE", "AC07_GRAPH_PATH_VALIDITY", "AC08_EDGE_COMPOSITION")),
        ("Argument-to-parameter and return-to-caller flows are implemented and tested.", ("AC03_CROSS_TU_SYMBOL_IDENTITY", "AC04_OVERLOAD_IDENTITY", "AC12_EXTERNAL_CALL_BOUNDARY", "AC13_CALLBACK_FUNCTION_POINTER")),
        ("Member and cache writes connect to reads across functions without spelling inference.", ("AC03_CROSS_TU_SYMBOL_IDENTITY", "AC06_ODR_RECONCILIATION", "AC07_GRAPH_PATH_VALIDITY")),
        ("Aliases, callbacks, and virtual targets resolve or block completeness.", ("AC13_CALLBACK_FUNCTION_POINTER", "AC17_CLOSED_WORLD_VIRTUAL_TARGETS", "AC21_OVERALL_UNRESOLVED_CAP", "AC22_REQUIRED_PATH_ZERO_UNRESOLVED")),
        ("All sixteen BeamSetup PDF pointer roles have local typed installation/accounting paths.", ("AC07_GRAPH_PATH_VALIDITY", "AC09_STATIC_REACHABILITY", "AC10_PROSPECTIVE_CONFIGURATION")),
        ("PDF-object alpha_s providers and routing paths are represented or block closure.", ("AC07_GRAPH_PATH_VALIDITY", "AC10_PROSPECTIVE_CONFIGURATION", "AC22_REQUIRED_PATH_ZERO_UNRESOLVED")),
        ("Hard-process NC, ISR/backward-evolution, and remnant paths are represented.", ("AC09_STATIC_REACHABILITY", "AC10_PROSPECTIVE_CONFIGURATION", "AC22_REQUIRED_PATH_ZERO_UNRESOLVED")),
        ("The 672-member holdout has zero binding unresolved and not-recovered entries.", ("AC14_MATERIAL_MISS", "AC15_EXEMPTION_REVIEW", "AC23_INDEPENDENT_REVIEWER", "AC24_BLINDED_HOLDOUT")),
        ("All generic-name and co-located-occurrence controls pass.", ("AC07_GRAPH_PATH_VALIDITY", "AC14_MATERIAL_MISS", "AC18_NEUTRAL_WRAPPER_REGISTRATION")),
        ("Independent neutral-name/interprocedural recall finds no material miss.", ("AC14_MATERIAL_MISS", "AC23_INDEPENDENT_REVIEWER")),
        ("Two independent graph generations serialize byte-identically.", ("AC03_CROSS_TU_SYMBOL_IDENTITY", "AC05_TEMPLATE_IDENTITY", "AC06_ODR_RECONCILIATION", "AC16_MACRO_IDENTITY")),
        ("An independent reviewer reproduces source, commands, graph, and calibration.", ("AC23_INDEPENDENT_REVIEWER", "AC24_BLINDED_HOLDOUT")),
        ("Runtime-only limitations remain unresolved and never satisfy a static gate.", ("AC09_STATIC_REACHABILITY", "AC10_PROSPECTIVE_CONFIGURATION", "AC22_REQUIRED_PATH_ZERO_UNRESOLVED")),
    )
    return [
        {
            "gate_id": gate_id,
            "binding": True,
            "planning_status": "NOT_EVALUATED_FUTURE_STATIC_EVIDENCE_GATE",
            "requirement": requirement,
            "contract_section_ids": list(section_ids),
            "machine_predicate_id": f"PREDICATE_{gate_id}",
        }
        for gate_id, (requirement, section_ids) in zip(
            GATE_IDS, specifications, strict=True
        )
    ]


def build_cost_challenge() -> dict[str, Any]:
    rows = (
        ("LLVM_ACQUISITION_BUILD_CI", 2, 4, 7, "Toolchain build and CI reproducibility."),
        ("DETERMINISTIC_120_TU_COMMAND_INVENTORY", 2, 4, 7, "Per-TU flags and environment reconstruction."),
        ("AST_EXTRACTION", 3, 6, 10, "Corpus-specific AST size and traversal."),
        ("STABLE_DECLARATION_TYPE_IDENTITY", 4, 8, 14, "Cross-TU and ODR identity."),
        ("CROSS_TU_CALL_MATCHING", 5, 10, 20, "Overloads, callbacks, and indirect calls."),
        ("ARGUMENT_TO_PARAMETER_FLOW", 3, 6, 10, "Wrappers and default arguments."),
        ("RETURN_TO_CALLER_FLOW", 3, 6, 10, "Chained and indirect returns."),
        ("FIELD_MEMBER_FLOW", 5, 10, 20, "Cross-function state mutation."),
        ("CACHE_FLOW", 2, 5, 10, "Neutral cache names and lifetimes."),
        ("POINTER_REFERENCE_ALIASES", 6, 12, 25, "Alias-set growth."),
        ("VIRTUAL_CANDIDATE_SETS", 4, 8, 16, "Closed-world assumptions."),
        ("MACRO_TEMPLATE_POLICY", 5, 10, 20, "Expansion and specialization identity."),
        ("UNRESOLVED_STATE_SERIALIZATION", 2, 4, 7, "Binding-path semantics."),
        ("SIXTEEN_POINTER_ROLES", 2, 4, 8, "Installation and replacement chains."),
        ("ALPHA_S_ROUTING", 2, 4, 8, "Multiple provider paths."),
        ("HARD_ISR_REMNANT_CLASSIFICATION", 5, 10, 18, "Scientific source review."),
        ("GRAPH_SERIALIZATION", 2, 4, 7, "Stable identities and ordering."),
        ("TESTS", 6, 12, 20, "Adversarial and corpus fixtures."),
        ("HISTORICAL_672_MEMBER_HOLDOUT", 3, 6, 12, "Exemptions and independence."),
        ("NEGATIVE_CONTROLS", 2, 4, 8, "Occurrence-level exclusion proof."),
        ("INDEPENDENT_RECALL_CHALLENGE", 5, 10, 20, "False-negative discovery."),
        ("EVIDENCE_DOCUMENTATION", 3, 6, 10, "Traceability and review."),
    )
    breakdown = [
        {
            "work_item": name,
            "optimistic_person_days": optimistic,
            "nominal_person_days": nominal,
            "pessimistic_person_days": pessimistic,
            "principal_uncertainty": uncertainty,
        }
        for name, optimistic, nominal, pessimistic, uncertainty in rows
    ]
    totals = {
        "optimistic": {"person_days": 76, "person_weeks": 15.2},
        "nominal": {"person_days": 153, "person_weeks": 30.6},
        "pessimistic": {"person_days": 287, "person_weeks": 57.4},
    }
    review = {
        "optimistic": {"person_days": 5, "person_weeks": 1.0},
        "nominal": {"person_days": 10, "person_weeks": 2.0},
        "pessimistic": {"person_days": 15, "person_weeks": 3.0},
    }
    return {
        "original_planning_estimate_person_weeks": 7.0,
        "independent_audit_assessment": "NOT_CREDIBLE",
        "work_breakdown_challenge": breakdown,
        "implementation_range": totals,
        "independent_reproduction_range": review,
        "implementation_cap_8_person_weeks": "NOT_SUPPORTED",
        "independent_review_cap_2_person_weeks": "SUPPORTED_WITH_QUALIFICATION",
        "scheduling_commitment": False,
        "interpretation": "These ranges challenge feasibility; they are not precise project scheduling commitments.",
    }


def build_condition(
    status: str, qualified_allowed: bool, rationale: str
) -> dict[str, Any]:
    require(status in FEASIBILITY_STATUSES, f"unsupported feasibility status: {status}")
    return {
        "status": status,
        "qualified_state_permitted_for_feasible": qualified_allowed,
        "rationale": rationale,
    }


def derive_feasibility_conditions(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidates = {row["candidate_id"]: row for row in record.get("toolchain_candidates", [])}
    preferred = record.get("preferred_feasibility_candidate", {})
    preferred_row = candidates.get(preferred.get("candidate_id"), {})
    source = record.get("authoritative_source_contract", {})
    compile_contract = record.get("compilation_database_contract", {})
    roots = record.get("graph_root_contract", {})
    calibration = record.get("calibration_contract", {})
    challenge = record.get("false_negative_challenge", {})
    runtime = record.get("static_runtime_boundary", {})
    cost = record.get("cost_bound", {})
    acceptance = record.get("acceptance_contract", {})
    lineage = record.get("source_lineage", {})
    stops = record.get("scientific_decisiveness", {}).get("stop_conditions", [])

    tool_status = (
        "SUPPORTED"
        if preferred_row.get("exact_tool_identity", {}).get("identity_verification_status")
        == "SUPPORTED"
        and preferred.get("status") == "PLAUSIBLE_FOUNDATION_REQUIRES_FURTHER_BOUNDING"
        else "NOT_SUPPORTED"
    )
    corpus_status = (
        "SUPPORTED"
        if source.get("identity_assessment") == "SUPPORTED"
        and source.get("inventory_count") == 247
        and source.get("translation_unit_count") == 120
        else "NOT_SUPPORTED"
    )
    compile_status = (
        "SUPPORTED"
        if compile_contract.get("assessment") == "PARSE_VALIDATED_EXACT_COMMAND_SET"
        and compile_contract.get("exact_per_tu_command_inventory_complete") is True
        else "SUPPORTED_WITH_QUALIFICATION"
        if compile_contract.get("assessment")
        == "SOURCE_INSPECTION_CORRECTED_BUT_PARSE_NOT_VALIDATED"
        else "NOT_SUPPORTED"
    )
    acceptance_status = acceptance.get("contract_status", "NOT_SUPPORTED")
    conditions = {
        "toolchain_identity_supported": build_condition(tool_status, False, "LLVM 18.1.8 identity is pinned; preference is not selection."),
        "corpus_identity_supported": build_condition(corpus_status, False, "Official PYTHIA identity and the 247-file manifest inventory reproduced."),
        "compile_contract_supported": build_condition(compile_status, False, "Source inspection corrected two per-TU definitions, but exact commands have not been generated or parsed."),
        "relation_representation_supported": build_condition(preferred.get("relation_representation_status", "NOT_SUPPORTED"), False, "Clang supplies typed anchors; repository cross-TU and dataflow relations remain unimplemented."),
        "typed_root_contract_complete": build_condition(roots.get("contract_status", "NOT_SUPPORTED"), False, "Typed root classes and prohibitions are specified with source-evidence requirements."),
        "alias_dispatch_policy_complete": build_condition(acceptance_status, False, "Alias, callback, function-pointer, and virtual closed-world policies are defined but unevaluated."),
        "interprocedural_plan_complete": build_condition(acceptance_status, False, "Cross-TU identity, overload, call, parameter, and return rules are defined but unimplemented."),
        "member_cache_plan_complete": build_condition(acceptance_status, False, "Member/cache source-path requirements are defined but unimplemented."),
        "calibration_contract_complete": build_condition(calibration.get("contract_status", "NOT_SUPPORTED"), False, "The holdout remains post-construction and blinded with zero binding misses."),
        "false_negative_contract_complete": build_condition(challenge.get("contract_status", "NOT_SUPPORTED"), False, "Material-miss and independent challenge classes are explicit."),
        "static_runtime_boundary_complete": build_condition(runtime.get("contract_status", "NOT_SUPPORTED"), False, "Runtime-only properties cannot satisfy static closure."),
        "implementation_cost_bounded": build_condition(cost.get("implementation_cap_8_person_weeks", "NOT_SUPPORTED"), False, "The independent 15.2/30.6/57.4-week challenge does not support the eight-week cap."),
        "independent_review_cost_bounded": build_condition(cost.get("independent_review_cap_2_person_weeks", "NOT_SUPPORTED"), True, "Two weeks is nominally plausible but the pessimistic range is three weeks."),
        "stop_conditions_machine_checkable": build_condition("SUPPORTED" if stops and all(row.get("machine_predicate_id") for row in stops) else "NOT_SUPPORTED", False, "Each stop condition names a future machine predicate."),
        "scientific_contract_unchanged": build_condition("SUPPORTED" if record.get("scientific_decisiveness", {}).get("scientific_contract_changed") is False else "NOT_SUPPORTED", False, "The accepted PDF family, support, sign, and inference contracts remain unchanged."),
        "acceptance_contract_complete": build_condition(acceptance_status, False, "Twenty-five binding definitions exist, but their schemas and predicates are not implemented or evaluated."),
        "source_lineage_portable_or_explicitly_qualified": build_condition("SUPPORTED_WITH_QUALIFICATION" if lineage.get("clean_ci_source_identity_validation") == "PORTABLE_MANIFEST_VALIDATION_ONLY" else "NOT_SUPPORTED", True, "Clean CI is explicitly limited to committed-manifest and artifact reproducibility."),
    }
    require(tuple(conditions) == FEASIBILITY_CONDITION_IDS, "condition ordering changed")
    return conditions


def derive_decision(record: dict[str, Any]) -> str:
    conditions = derive_feasibility_conditions(record)
    feasible = all(
        row["status"] == "SUPPORTED"
        or (
            row["status"] == "SUPPORTED_WITH_QUALIFICATION"
            and row["qualified_state_permitted_for_feasible"] is True
        )
        for row in conditions.values()
    ) and record.get("selected_toolchain") is not None
    if feasible:
        return "FEASIBLE_FOR_SEPARATE_STATIC_EVIDENCE_TASK"
    relevant = (
        record.get("scientific_decisiveness", {}).get("approach_status")
        == "AST_GRAPH_APPROACH_REMAINS_SCIENTIFICALLY_RELEVANT"
        and conditions["toolchain_identity_supported"]["status"] != "NOT_SUPPORTED"
        and conditions["corpus_identity_supported"]["status"] != "NOT_SUPPORTED"
    )
    return "INCONCLUSIVE" if relevant else "DO_NOT_PROCEED"


def build_record(repo: Path) -> dict[str, Any]:
    inventory, translation_units, inventory_hash = load_release_inventory(repo)
    manifest_path = repo / SEARCH_MANIFEST
    acceptance = build_acceptance_contract()
    record: dict[str, Any] = {
        "schema_version": SCHEMA,
        "decision": None,
        "precedence": {
            "D1C_FINAL_DECISION": "FAIL",
            "MINIMAL_PUBLIC_READER_PATCH": "INSUFFICIENT",
            "PROVENANCE_SLICE_V1_DECISION": "FAIL",
            "PROVENANCE_SLICE_V1_STATUS": "REJECTED_DIAGNOSTIC",
            "D1D_A_FINAL_DECISION": "FAIL",
            "D1D_A_FAILED_GATE": "provenance_evidence_integrity",
            "D1D_B_FINAL_DECISION": "INCONCLUSIVE",
            "CURRENT_OPERATIONAL_POLICY": "PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION",
            "ARCHITECTURE_COMPARISON_READY": False,
            "D2_AUTHORIZED": False,
        },
        "objective": {
            "task": "Assess whether a separately reviewed AST-grounded PYTHIA PDF-consumer graph task is technically bounded and scientifically useful.",
            "planning_only": True,
            "production_graph_constructed": False,
            "scientific_objective_unchanged": "p(theta_PDF | D), where D is a set of events",
        },
        "authoritative_source_contract": {
            "pythia_version": "8.312",
            "upstream_repository": "https://gitlab.com/Pythia8/releases",
            "upstream_tag": "pythia8312",
            "upstream_commit_sha": "cf0823ace0e2ebc2435f3f614e0926e9b381e21f",
            "archive_url": "https://gitlab.com/Pythia8/releases/-/archive/pythia8312/releases-pythia8312.tar.gz",
            "archive_sha256": "c1a33aa5fa15e6b70d7946ce6d237246842887ec84ea0b35dfc2535c868a2770",
            "identity_assessment": "SUPPORTED",
            "authoritative_source_root": RELEASE_ROOT,
            "inventory_identity": "PYTHIA_8_312_RELEASE_CORE_H_CC_247_V1",
            "inventory_sha256": inventory_hash,
            "inventory_count": len(inventory),
            "header_count": sum(row["path"].endswith(".h") for row in inventory),
            "translation_unit_count": len(translation_units),
            "file_inventory": inventory,
            "translation_unit_semantic_file_ids": translation_units,
            "installed_mirror": {
                "root": ".external/pythia-8.3.12/include/Pythia8",
                "release_headers_compared": 127,
                "byte_identical_headers": 127,
                "semantic_node_policy": "IDENTITY_EVIDENCE_ONLY_EXCLUDED_FROM_GRAPH_NODES",
            },
            "prior_search_manifest": {
                "path": SEARCH_MANIFEST,
                "schema_version": "partonsbi.phase1bd.d1d.pythia-semantics-search-manifest.v3",
                "sha256": file_sha256(manifest_path),
                "prior_inventory_count": 374,
            },
            "cxx_standard": "c++11",
            "project_include_paths": ["${PYTHIA_SOURCE_ROOT}/include"],
            "common_preprocessor_definitions": [],
            "required_generated_headers": [],
            "system_headers_required": True,
            "optional_feature_configuration": {
                "core_source": "ENABLED",
                "external_plugins": "DISABLED",
                "lhapdf_linkage": "DISABLED",
                "hepmc_and_fastjet_plugins": "DISABLED",
                "policy": "Expand and re-review the corpus before claiming a path that depends on a disabled module.",
            },
            "intentional_exclusions": [
                {"scope": ".external/pythia-8.3.12/include/Pythia8", "reason": "BYTE_IDENTICAL_INSTALLED_HEADER_MIRROR"},
                {"scope": "examples/", "reason": "NOT_CORE_LIBRARY_TRANSLATION_UNITS"},
                {"scope": "plugins/", "reason": "OPTIONAL_EXTERNAL_DEPENDENCIES_DISABLED_FOR_FIXED_CORE_CONTRACT"},
                {"scope": "share/ and documentation", "reason": "NON_CXX_SOURCE_INPUT"},
                {"scope": "non-.h/.cc files", "reason": "NOT_AUTHORITATIVE_CORE_CXX_SOURCE"},
            ],
        },
        "source_lineage": {
            "clean_ci_source_identity_validation": "PORTABLE_MANIFEST_VALIDATION_ONLY",
            "official_archive_reproduced_independently_during_audit": True,
            "committed_manifest_stores_paths_sizes_and_sha256": True,
            "d1e_inventory_is_deterministic_manifest_filter": True,
            "local_ignored_bytes_checked_only_when_checkout_exists": True,
            "clean_ci_skips_absent_local_byte_comparison": True,
            "clean_ci_retrieves_official_archive": False,
            "clean_ci_independently_resolves_upstream_tag_or_commit": False,
            "clean_ci_proves": "COMMITTED_MANIFEST_AND_ARTIFACT_REPRODUCIBILITY",
            "clean_ci_does_not_prove": "INDEPENDENT_UPSTREAM_BYTE_IDENTITY",
        },
        "toolchain_candidates": build_toolchains(),
        "preferred_feasibility_candidate": {
            "candidate_id": "LLVM_CLANG_LIBTOOLING_18_1_8",
            "status": "PLAUSIBLE_FOUNDATION_REQUIRES_FURTHER_BOUNDING",
            "relation_representation_status": "SUPPORTED_WITH_QUALIFICATION",
            "selection_or_authorization": False,
            "reason": "Typed AST anchors remain scientifically relevant, but cross-TU/dataflow implementation, compile replay, and cost are not bounded.",
        },
        "selected_toolchain": None,
        "llvm_capability_boundary": {
            "CLANG_AST_DIRECTLY_PROVIDES": [
                "typed_declarations_and_expressions",
                "source_spelling_and_expansion_coordinates",
                "materialized_template_instances",
                "call_parameter_return_ast_anchors",
                "field_member_ast_anchors",
            ],
            "REPOSITORY_ANALYSIS_MUST_IMPLEMENT": [
                "cross_translation_unit_identity",
                "odr_reconciliation",
                "overload_and_specialization_identity",
                "call_site_to_parameter_propagation",
                "return_to_caller_propagation",
                "field_cache_write_read_flow",
                "points_to_propagation",
                "closed_virtual_target_construction",
                "deterministic_graph_serialization",
            ],
            "STATIC_ANALYSIS_CANNOT_PROVE": [
                "runtime_selected_concrete_targets",
                "post_init_pointer_replacement",
                "actual_query_envelopes",
                "general_alias_closure",
                "thread_process_behavior",
            ],
        },
        "compilation_database_contract": {
            "upstream_build_system": "configure plus GNU Makefile",
            "strategy": "REPOSITORY_OWNED_SOURCE_ONLY_JSON_COMPILATION_DATABASE",
            "command_model": "COMMON_ARGUMENTS_PLUS_DETERMINISTIC_PER_TU_OVERRIDES",
            "assessment": "SOURCE_INSPECTION_CORRECTED_BUT_PARSE_NOT_VALIDATED",
            "source_only_configuration_sufficient": "NOT_EVALUATED_WITH_PARSER",
            "exact_per_tu_command_inventory_complete": False,
            "database_generated_in_this_task": False,
            "compile_commands_present_at_review": False,
            "link_or_generator_execution_required": False,
            "compiler": {
                "executable": "${PINNED_LLVM_18_1_8_ROOT}/bin/clang++",
                "version": "18.1.8",
                "llvm_commit_sha": "3b5b5c1ec4a3095ab096dd780e84d7ab81f3d7ff",
            },
            "common_argv_template": [
                "${PINNED_LLVM_18_1_8_ROOT}/bin/clang++",
                "-std=c++11",
                "-pedantic",
                "-W",
                "-Wall",
                "-Wshadow",
                "-fPIC",
                "-pthread",
                "-I${PYTHIA_SOURCE_ROOT}/include",
                "-fsyntax-only",
            ],
            "per_translation_unit_overrides": [
                {
                    "source_file": "${PYTHIA_SOURCE_ROOT}/src/Pythia.cc",
                    "arguments": ["-DXMLDIR=\"<PINNED_SHARE_ROOT>/xmldoc\""],
                    "source_evidence": "XMLDIR is used unconditionally by Pythia.cc and supplied by the upstream Makefile.",
                },
                {
                    "source_file": "${PYTHIA_SOURCE_ROOT}/src/FJcore.cc",
                    "arguments": ["-DFJCORE_HAVE_LIMITED_THREAD_SAFETY"],
                    "source_evidence": "The upstream FJcore build definition changes limited-thread-safety semantics.",
                },
            ],
            "textual_include_closure_audit": {
                "translation_units_inspected": 120,
                "generated_core_header_dependencies": 0,
                "includes_escaping_authoritative_root": 0,
                "apparent_missing_quoted_includes": [
                    "fastjet/internal/Dnn4piCylinder.hh",
                    "fastjet/internal/Dnn3piCylinder.hh",
                    "fastjet/internal/Dnn2piCylinder.hh",
                ],
                "apparent_missing_include_disposition": "DISABLED_BY___FJCORE_DROP_CGAL_DEFINED_IN_PYTHIA8_FJCORE_H",
                "actual_parse_success_claimed": False,
            },
            "superseded_v1_claims": [
                "PREPROCESSOR_DEFINITIONS_EMPTY",
                "ONE_CANONICAL_ARGV_TEMPLATE_SUFFICIENT",
            ],
            "environment_allowlist": {"LC_ALL": "C", "TZ": "UTC"},
            "required_future_identities": [
                "canonical_compile_command_set_sha256",
                "canonical_environment_sha256",
                "compiler_binary_sha256",
                "toolchain_release_commit_sha",
            ],
            "missing_or_unparsable_policy": "FAIL_CLOSED",
        },
        "graph_root_contract": {
            "contract_status": "SUPPORTED",
            "root_basis": "TYPED_SOURCE_DECLARATION_DEFINITION_OR_ASSIGNMENT_COORDINATE_ONLY",
            "required_root_classes": list(ROOT_CLASSES),
            "sixteen_pointer_roles": list(POINTER_ROLES),
            "prohibitions": {
                "identifier_name_roots": False,
                "filename_substring_roots": False,
                "historical_member_seeded_roots": False,
                "global_xf_pdf_pdfptr_fallback": False,
                "synthetic_root_without_source_coordinate": False,
            },
        },
        "graph_edge_contract": {
            "edge_kinds": list(EDGE_KINDS),
            "required_fields": [
                "exact_source_coordinate",
                "enclosing_function_or_declaration",
                "source_static_type",
                "target_static_type",
                "derivation_rule",
                "confidence_or_evidence_state",
                "translation_unit_identity",
            ],
            "direct_root_to_unit_synthetic_edge_allowed": False,
            "source_support_required": True,
        },
        "unresolved_evidence_contract": {
            "states": list(UNRESOLVED_STATES),
            "critical_path_policy": "UNRESOLVED_HARD_PROCESS_ISR_OR_REMNANT_PATH_BLOCKS_COMPLETENESS",
            "unresolved_may_satisfy_supported_edge": False,
            "closure_requires_zero_unresolved_binding_paths": True,
        },
        "static_runtime_boundary": {
            "contract_status": "SUPPORTED",
            "static_graph_can_authorize_issue_10_or_d2": False,
            "runtime_only_properties": [
                {"property": "actual_runtime_pointer_installation", "statically_proven": False, "later_evidence": "Separately authorized configuration-specific runtime pointer identity trace."},
                {"property": "post_init_pointer_substitution", "statically_proven": False, "later_evidence": "Separately authorized post-init mutation trace."},
                {"property": "configuration_selected_dynamic_targets", "statically_proven": False, "later_evidence": "Reviewed configuration plus separately authorized runtime target observation."},
                {"property": "runtime_query_envelopes", "statically_proven": False, "later_evidence": "Separately authorized bounded query-envelope measurement."},
                {"property": "thread_and_process_behavior", "statically_proven": False, "later_evidence": "Separately authorized concurrency and lifecycle validation."},
            ],
            "runtime_evidence_may_satisfy_static_gate": False,
        },
        "calibration_contract": {
            "contract_status": "SUPPORTED",
            "historical_member_count": 672,
            "use": "POST_CONSTRUCTION_BLINDED_HOLDOUT_ONLY",
            "may_seed_identifiers": False,
            "may_seed_roots": False,
            "may_define_edges": False,
            "may_define_reachability": False,
            "may_influence_fallback": False,
            "report_states": ["LOCALLY_RECOVERED", "EXPLICIT_BOUNDARY_OR_POLICY_EXEMPTION", "UNRESOLVED", "NOT_RECOVERED"],
            "acceptance_zero_counts": ["GLOBAL_NAME_FALLBACK", "SYNTHETIC_ROOT_ATTACHMENT", "DANGLING_CALIBRATION_REFERENCE", "UNRESOLVED_BINDING_MEMBER", "NOT_RECOVERED_BINDING_MEMBER"],
        },
        "negative_controls": {
            "identifiers": list(NEGATIVE_CONTROL_IDENTIFIERS),
            "lexical_name_admission_allowed": False,
            "co_located_line_admission_allowed": False,
            "required_proof": "The exact occurrence must lie on a typed, source-backed provenance path.",
        },
        "false_negative_challenge": {
            "contract_status": "SUPPORTED",
            "independent_from_graph_construction": True,
            "required_classes": list(FALSE_NEGATIVE_CLASSES),
            "material_miss_definition": "Any omitted source-backed PDF-derived path affecting hard, ISR, remnant, selection, ratio, envelope, or weight semantics.",
            "acceptance": "ZERO_MATERIAL_MISSES_AND_ZERO_UNRESOLVED_BINDING_CHALLENGES",
        },
        "acceptance_contract": acceptance,
        "acceptance_gates": build_gates(),
        "scientific_decisiveness": {
            "approach_status": "AST_GRAPH_APPROACH_REMAINS_SCIENTIFICALLY_RELEVANT",
            "scope_status": "CURRENT_IMPLEMENTATION_SCOPE_NOT_CREDIBLY_BOUNDED",
            "compile_status": "COMPILE_CONTRACT_NOT_YET_SUPPORTED",
            "implementation_status": "IMPLEMENTATION_NOT_AUTHORIZED",
            "could_materially_repair_failed_gate": "provenance_evidence_integrity",
            "repair_is_conditional_on_all_binding_gates": True,
            "cannot_establish": [
                "SIGNED_PROBABILITY_OR_RATE_VALIDITY",
                "SIGNED_SUDAKOV_MATHEMATICS",
                "RUNTIME_POINTER_IDENTITY",
                "POST_INIT_POINTER_SUBSTITUTION",
                "ACTUAL_GENERATOR_QUERY_ENVELOPES",
                "THREAD_PROCESS_SAFETY",
                "GENERATOR_COMPATIBILITY",
                "D2_AUTHORIZATION",
            ],
            "stop_conditions": [
                {"condition": "Any required translation unit cannot be parsed reproducibly.", "machine_predicate_id": "STOP_ANY_REQUIRED_TU_PARSE_FAILURE"},
                {"condition": "Source-backed interprocedural or member flow remains incomplete after a separately approved bound.", "machine_predicate_id": "STOP_BINDING_FLOW_INCOMPLETE_AT_APPROVED_BOUND"},
                {"condition": "Holdout or independent challenge exposes a material miss that cannot be bounded.", "machine_predicate_id": "STOP_UNBOUNDED_MATERIAL_MISS"},
                {"condition": "Construction uses identifier, filename, global, historical, or synthetic fallback.", "machine_predicate_id": "STOP_PROHIBITED_FALLBACK_NONZERO"},
                {"condition": "Any timeout, truncation, ODR conflict, or required unresolved path remains.", "machine_predicate_id": "STOP_INCOMPLETE_OR_UNRESOLVED_BINDING_EVIDENCE"},
            ],
            "scientific_contract_changed": False,
        },
        "cost_bound": build_cost_challenge(),
        "feasibility_conditions": None,
        "failure_scope": "INCONCLUSIVE rejects the current boundedness and compile-contract claims; it does not prove all future typed source-analysis methods impossible.",
        "non_failure_scope": "AST evidence may still repair provenance integrity, but does not establish graph completeness, signed-rate mathematics, runtime reachability, generator compatibility, or implementation permission.",
        "authorization": {flag: False for flag in AUTHORIZATION_FLAGS},
        "dependencies": {
            "planning_issue": {"number": 45, "state": "OPEN", "authorization": "PLANNING_ONLY"},
            "completed_d1d_issue": {"number": 42, "state": "CLOSED"},
            "blocked_downstream_issue": {"number": 10, "state": "OPEN_BLOCKED", "gate_decision": "NOT_EVALUATED", "authorization": "NOT_AUTHORIZED"},
        },
        "next_step": {
            "action": "SEPARATE_REVIEW_TO_BOUND_COMPILE_COMMANDS_ACCEPTANCE_PREDICATES_AND_TASK_SCOPE",
            "implementation_authorized": False,
            "condition": "Only a later explicit decision may authorize a separately scoped static-evidence implementation task.",
        },
        "validation": {
            "artifact_generation_deterministic": True,
            "semantic_contract_validation_independent_of_byte_replay": True,
            "parser_or_graph_execution_performed": False,
            "compile_database_generated": False,
            "generator_or_physics_execution_performed": False,
            "production_graph_nodes_or_edges_generated": False,
        },
    }
    record["feasibility_conditions"] = derive_feasibility_conditions(record)
    record["decision"] = derive_decision(record)
    return record


def validate_record(record: dict[str, Any], repo: Path) -> None:
    expected = build_record(repo)
    require(set(record) == set(expected), "artifact top-level field set differs from v2")
    require(record.get("schema_version") == SCHEMA, "wrong schema")
    require(record.get("decision") in ALLOWED_DECISIONS, "decision is not allowed")

    # Bind each scientific contract independently. The CLI performs a separate
    # whole-artifact byte replay after these semantic checks pass.
    contract_sections = (
        "precedence",
        "objective",
        "authoritative_source_contract",
        "source_lineage",
        "toolchain_candidates",
        "preferred_feasibility_candidate",
        "selected_toolchain",
        "llvm_capability_boundary",
        "compilation_database_contract",
        "graph_root_contract",
        "graph_edge_contract",
        "unresolved_evidence_contract",
        "static_runtime_boundary",
        "calibration_contract",
        "negative_controls",
        "false_negative_challenge",
        "acceptance_contract",
        "acceptance_gates",
        "scientific_decisiveness",
        "cost_bound",
        "failure_scope",
        "non_failure_scope",
        "authorization",
        "dependencies",
        "next_step",
        "validation",
    )
    for section in contract_sections:
        require(
            record.get(section) == expected[section],
            f"semantic contract changed: {section}",
        )

    source = record["authoritative_source_contract"]
    inventory, tus, inventory_hash = load_release_inventory(repo)
    require(source["file_inventory"] == inventory, "manifest-backed inventory changed")
    require(source["translation_unit_semantic_file_ids"] == tus, "TU set changed")
    require(source["inventory_sha256"] == inventory_hash, "inventory hash changed")
    verify_source_bytes_when_available(repo, inventory)

    acceptance = record["acceptance_contract"]
    section_ids = [row["section_id"] for row in acceptance["sections"]]
    require(len(section_ids) == 25 and len(set(section_ids)) == 25, "exactly 25 unique acceptance sections are required")
    require(all(row["binding"] is True and row["machine_predicate"] for row in acceptance["sections"]), "every acceptance section must be binding and machine-checkable")
    known_sections = set(section_ids)
    gates = record["acceptance_gates"]
    require([gate["gate_id"] for gate in gates] == list(GATE_IDS), "gate set changed")
    require(all(gate["binding"] is True for gate in gates), "all gates must bind")
    require(all(gate["machine_predicate_id"] for gate in gates), "gate predicate missing")
    require(all(set(gate["contract_section_ids"]).issubset(known_sections) and gate["contract_section_ids"] for gate in gates), "gate references unknown or empty contract sections")

    cost = record["cost_bound"]
    breakdown = cost["work_breakdown_challenge"]
    for key, expected_days in (("optimistic", 76), ("nominal", 153), ("pessimistic", 287)):
        actual_days = sum(row[f"{key}_person_days"] for row in breakdown)
        require(actual_days == expected_days, f"{key} implementation total changed")
        require(cost["implementation_range"][key]["person_days"] == actual_days, f"{key} serialized total mismatch")
        require(cost["implementation_range"][key]["person_weeks"] == actual_days / 5, f"{key} week conversion mismatch")
    require(cost["implementation_cap_8_person_weeks"] == "NOT_SUPPORTED", "unsupported implementation cap promoted")
    require(cost["independent_review_cap_2_person_weeks"] == "SUPPORTED_WITH_QUALIFICATION", "review qualification changed")

    recomputed_conditions = derive_feasibility_conditions(record)
    require(record["feasibility_conditions"] == recomputed_conditions, "feasibility conditions differ from recomputation")
    require(tuple(recomputed_conditions) == FEASIBILITY_CONDITION_IDS, "condition set changed")
    require(all(row["status"] in FEASIBILITY_STATUSES for row in recomputed_conditions.values()), "invalid feasibility status")
    require(record["decision"] == derive_decision(record), "decision differs from recomputed evidence")
    if record["decision"] == "INCONCLUSIVE":
        require(record["selected_toolchain"] is None, "INCONCLUSIVE cannot select a toolchain")
        require(record["preferred_feasibility_candidate"]["selection_or_authorization"] is False, "preferred candidate became selected or authorized")
        require("IMPLEMENT" not in record["next_step"]["action"], "INCONCLUSIVE cannot name an implementation next step")

    require(set(record["authorization"]) == set(AUTHORIZATION_FLAGS), "authorization fields changed")
    require(all(value is False for value in record["authorization"].values()), "all authorization flags must remain false")
    require(record["precedence"]["D2_AUTHORIZED"] is False, "D2 precedence changed")
    require(record["dependencies"]["blocked_downstream_issue"] == {"number": 10, "state": "OPEN_BLOCKED", "gate_decision": "NOT_EVALUATED", "authorization": "NOT_AUTHORIZED"}, "issue #10 must remain blocked")
    require(record["next_step"]["implementation_authorized"] is False, "next step cannot authorize implementation")


def write_record(record: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true", help="write the planning artifact")
    parser.add_argument("--validate", action="store_true", help="validate the committed planning artifact")
    parser.add_argument("--artifact", default=ARTIFACT)
    args = parser.parse_args()
    if not args.generate and not args.validate:
        parser.error("choose --generate or --validate")

    repo = Path(__file__).resolve().parents[1]
    artifact_path = repo / args.artifact
    try:
        if args.generate:
            record = build_record(repo)
            validate_record(record, repo)
            write_record(record, artifact_path)
            print(f"generated {args.artifact}: {record['decision']}")
        if args.validate:
            record = json.loads(artifact_path.read_text(encoding="utf-8"))
            validate_record(record, repo)
            expected_bytes = json.dumps(build_record(repo), indent=2, sort_keys=True) + "\n"
            require(artifact_path.read_text(encoding="utf-8") == expected_bytes, "artifact does not reproduce byte-identically")
            print(f"validated {args.artifact}: {record['decision']}")
    except (FeasibilityError, KeyError, TypeError, ValueError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
