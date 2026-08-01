#!/usr/bin/env python3
"""Generate and validate the planning-only D1E AST-graph feasibility record.

This module only describes a future static-evidence task.  It does not invoke
an AST extractor, create a compilation database, build a graph, or execute
generator or physics software.
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

SCHEMA = "partonsbi.phase1bd.d1e.consumer-graph-feasibility.v1"
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


@lru_cache(maxsize=1)
def verified_source_hashes(repo_text: str) -> tuple[tuple[str, int, str], ...]:
    """Read the fixed corpus once per process; this is source inspection only."""
    repo = Path(repo_text)
    inventory, _, _ = load_release_inventory(repo)
    result = []
    for row in inventory:
        path = repo / row["path"]
        require(path.is_file(), f"authoritative source file is missing: {row['path']}")
        result.append((row["path"], path.stat().st_size, file_sha256(path)))
    return tuple(result)


def verify_source_bytes_when_available(
    repo: Path, expected_inventory: list[dict[str, Any]]
) -> bool:
    """Verify ignored source bytes locally without requiring them in clean CI.

    The committed broad manifest, pinned upstream tag/commit, and archive hash
    are the portable contract.  The ignored release checkout is extra local
    evidence and is checked whenever its authoritative root is present.
    """
    if not (repo / RELEASE_ROOT).is_dir():
        return False
    actual_source_rows = verified_source_hashes(str(repo.resolve()))
    require(
        actual_source_rows
        == tuple(
            (row["path"], row["bytes"], row["sha256"])
            for row in expected_inventory
        ),
        "authoritative source bytes differ from the serialized inventory",
    )
    return True


def load_release_inventory(repo: Path) -> tuple[list[dict[str, Any]], list[str], str]:
    manifest_path = repo / SEARCH_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prefix = f"{RELEASE_ROOT}/"
    selected = [
        row
        for row in manifest["searched_files"]
        if row["path"].startswith(prefix)
        and (row["path"].endswith(".h") or row["path"].endswith(".cc"))
    ]
    selected.sort(key=lambda row: row["path"])
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


def capability(
    support: str, evidence: str, limitation: str, future_requirement: str
) -> dict[str, str]:
    return {
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
    }
    common_clang_capabilities = {
        "cxx_language_and_templates": capability(
            "SUPPORTED_WITH_QUALIFICATION",
            "Clang 18.1.8 parses C++11 templates and exposes typed AST declarations and instantiations.",
            "Only materialized instantiations in the fixed translation-unit set are visible.",
            "Fail closed on a required template use without a materialized specialization.",
        ),
        "macro_handling": capability(
            "SUPPORTED_WITH_QUALIFICATION",
            "Clang source locations distinguish spelling and expansion coordinates.",
            "Macro-generated semantics need an explicit expansion policy.",
            "Serialize both spelling and expansion ranges or emit MACRO_GENERATED_USE_UNRESOLVED.",
        ),
        "dynamic_dispatch": capability(
            "SUPPORTED_WITH_QUALIFICATION",
            "Typed virtual call sites and class hierarchies are representable.",
            "Runtime-selected concrete targets cannot be proven statically.",
            "Emit candidate targets and block closure when the target set is not closed.",
        ),
        "interprocedural_call_and_return": capability(
            "REPRESENTABLE_WITH_REPOSITORY_ANALYSIS",
            "AST call expressions, function declarations, parameters, and returns expose the required anchors.",
            "Clang AST traversal alone does not construct whole-program value flow.",
            "Implement deterministic call-site/parameter/return matching and fail on unresolved callees.",
        ),
        "field_member_dataflow": capability(
            "REPRESENTABLE_WITH_REPOSITORY_ANALYSIS",
            "Member expressions and field declarations carry static type and coordinates.",
            "Cross-function write/read flow requires repository-owned indexing.",
            "Index field identity and all writes/reads across the authoritative corpus.",
        ),
        "alias_pointer_analysis": capability(
            "PARTIAL_FAIL_CLOSED",
            "Typed pointer/reference assignments can be extracted from the AST.",
            "General C++ alias closure and runtime pointer replacement are not guaranteed.",
            "Resolve only source-supported points-to/assignment facts; serialize every remainder as blocking.",
        ),
        "source_coordinate_stability": capability(
            "SUPPORTED",
            "Pinned bytes plus Clang spelling/expansion offsets provide deterministic coordinates.",
            "Coordinates change if source bytes or flags change.",
            "Bind every coordinate to source SHA-256 and canonical compile-command identity.",
        ),
        "deterministic_serialization": capability(
            "SUPPORTED_WITH_REPOSITORY_NORMALIZER",
            "USR/type/coordinate anchors can be normalized independently of traversal order.",
            "Raw traversal order and compiler-internal IDs are not a stable artifact contract.",
            "Sort canonical source-backed keys and hash normalized records.",
        ),
    }
    return [
        {
            "candidate_id": "LLVM_CLANG_LIBTOOLING_18_1_8",
            "exact_tool_identity": llvm_identity,
            "acquisition_and_pinning_strategy": {
                "method": "Future task obtains official llvm-project tag llvmorg-18.1.8 and verifies peeled commit before a separate reviewed installation/build step.",
                "installation_performed_in_this_task": False,
                "pin_is_immutable": True,
            },
            "license": "Apache-2.0 WITH LLVM-exception",
            "wsl_availability": "NOT_CURRENTLY_INSTALLED; PINNED_ACQUISITION_FEASIBLE",
            "ci_availability": "NOT_IN_CURRENT_WORKFLOW; FUTURE_PINNED_TOOLCHAIN_JOB_FEASIBLE",
            "capabilities": copy.deepcopy(common_clang_capabilities),
            "compilation_database_requirements": "A deterministic repository-owned JSON Compilation Database containing all 120 release translation units and exact Clang argv arrays.",
            "expected_unresolved_classes": list(UNRESOLVED_STATES),
            "implementation_burden_person_weeks": 4.25,
            "independent_review_burden_person_weeks": 1.5,
            "candidate_feasibility": "PINNABLE_AND_RELATIONS_TECHNICALLY_REPRESENTABLE",
        },
        {
            "candidate_id": "CLANG_AST_JSON_QUERY_NORMALIZER_18_1_8",
            "exact_tool_identity": {
                **llvm_identity,
                "tool": "Clang AST JSON / clang-query plus repository-owned normalizer",
                "official_documentation": "https://releases.llvm.org/18.1.8/tools/clang/docs/IntroductionToTheClangAST.html",
            },
            "acquisition_and_pinning_strategy": {
                "method": "Same pinned Clang 18.1.8 release; consume source-only AST output and own all cross-translation-unit normalization.",
                "installation_performed_in_this_task": False,
                "pin_is_immutable": True,
            },
            "license": "Apache-2.0 WITH LLVM-exception",
            "wsl_availability": "NOT_CURRENTLY_INSTALLED; PINNED_ACQUISITION_FEASIBLE",
            "ci_availability": "NOT_IN_CURRENT_WORKFLOW; FUTURE_PINNED_TOOLCHAIN_JOB_FEASIBLE",
            "capabilities": copy.deepcopy(common_clang_capabilities),
            "compilation_database_requirements": "The same exact 120-translation-unit database; JSON emission does not remove compile-flag dependence.",
            "expected_unresolved_classes": list(UNRESOLVED_STATES),
            "implementation_burden_person_weeks": 6.5,
            "independent_review_burden_person_weeks": 2.0,
            "candidate_feasibility": "TECHNICALLY_POSSIBLE_BUT_NORMALIZER_BURDEN_NEAR_CAP",
        },
        {
            "candidate_id": "CODEQL_CPP_2_25_5",
            "exact_tool_identity": {
                "tool": "GitHub CodeQL CLI C/C++ database and query layer",
                "version": "2.25.5",
                "binary_release_tag": "v2.25.5",
                "binary_release_commit_sha": "697ca25e7c992daa3ecdb020fb62c38d0f5f8907",
                "query_repository_tag": "codeql-cli/v2.25.5",
                "query_repository_commit_sha": "b551e89ea8e011c0e3301fd0ce05589c9f2d3681",
                "official_repository": "https://github.com/github/codeql",
                "official_documentation": "https://docs.github.com/en/code-security/codeql-cli",
            },
            "acquisition_and_pinning_strategy": {
                "method": "Future review would pin official CLI bundle v2.25.5 and matching query-repository commit; no acquisition occurred here.",
                "installation_performed_in_this_task": False,
                "pin_is_immutable": True,
            },
            "license": "CodeQL CLI standard terms; query repository MIT",
            "wsl_availability": "NOT_CURRENTLY_INSTALLED; LICENSE_REVIEW_REQUIRED",
            "ci_availability": "DATABASE_GENERATION_IN_AUTOMATED_CI_NOT_SUPPORTED_BY_STANDARD_DOWNLOADED_CLI_TERMS",
            "capabilities": {
                **copy.deepcopy(common_clang_capabilities),
                "interprocedural_call_and_return": capability(
                    "SUPPORTED_WITH_QUALIFICATION",
                    "Official CodeQL C/C++ libraries provide local/global data-flow and call-graph APIs.",
                    "Custom models and dynamic target completeness remain query- and version-dependent.",
                    "Pin the query pack, enumerate modeled boundaries, and fail closed on unmodeled calls.",
                ),
                "alias_pointer_analysis": capability(
                    "SUPPORTED_WITH_QUALIFICATION",
                    "Official C/C++ data-flow libraries model pointer indirections and fields.",
                    "Runtime-selected providers and model gaps remain unresolved.",
                    "Audit every modeled/unmodeled boundary and retain blocking unresolved states.",
                ),
            },
            "compilation_database_requirements": "Manual-build database creation with the exact source-only build commands; this adds capture and licensing constraints.",
            "expected_unresolved_classes": list(UNRESOLVED_STATES),
            "implementation_burden_person_weeks": 5.0,
            "independent_review_burden_person_weeks": 2.0,
            "candidate_feasibility": "TECHNICALLY_CAPABLE_BUT_CI_DATABASE_LICENSE_AND_MODEL_STABILITY_BLOCK_SELECTION",
        },
    ]


def build_gates() -> list[dict[str, Any]]:
    requirements = (
        "Authoritative source identity, inventory, mirrors, and exclusions reproduce exactly.",
        "All 120 required translation units parse; one miss is a blocking failure.",
        "Canonical compile argv and environment replay with exact set and byte equality.",
        "All required roots arise from typed declarations, definitions, or assignments.",
        "Identifier, filename, historical, global, and synthetic fallback counts are zero.",
        "Every graph edge has exact source support and the required evidence fields.",
        "Argument-to-parameter and return-to-caller flows are implemented and tested on corpus code.",
        "Member and cache writes connect to reads across functions without spelling inference.",
        "Unresolved aliases and virtual targets either resolve or block completeness.",
        "All sixteen BeamSetup PDF pointer roles have local typed installation/accounting paths.",
        "PDF-object alpha_s providers and routing paths are represented or block closure.",
        "Hard-process NC, ISR/backward-evolution, and remnant paths are represented.",
        "The 672-member holdout has zero binding UNRESOLVED and NOT_RECOVERED entries.",
        "All generic-name and co-located-occurrence controls pass.",
        "Independent neutral-name/interprocedural recall challenge finds no material miss.",
        "Two independent graph generations serialize byte-identically.",
        "An independent reviewer reproduces source, commands, graph, and calibration.",
        "Runtime-only properties remain explicitly unresolved and never satisfy a static gate.",
    )
    return [
        {
            "gate_id": gate_id,
            "binding": True,
            "planning_status": "NOT_EVALUATED_FUTURE_STATIC_EVIDENCE_GATE",
            "requirement": requirement,
        }
        for gate_id, requirement in zip(GATE_IDS, requirements, strict=True)
    ]


def derive_decision(record: dict[str, Any]) -> str:
    selected = record.get("selected_toolchain")
    candidates = {row["candidate_id"]: row for row in record.get("toolchain_candidates", [])}
    source = record.get("authoritative_source_contract", {})
    compile_contract = record.get("compilation_database_contract", {})
    cost = record.get("cost_bound", {})
    technically_representable = bool(
        selected
        and selected.get("candidate_id") in candidates
        and candidates[selected["candidate_id"]].get("candidate_feasibility")
        == "PINNABLE_AND_RELATIONS_TECHNICALLY_REPRESENTABLE"
    )
    corpus_defined = (
        source.get("inventory_count") == 247
        and source.get("translation_unit_count") == 120
        and source.get("authoritative_source_root") == RELEASE_ROOT
    )
    commands_defined = (
        compile_contract.get("strategy")
        == "REPOSITORY_OWNED_SOURCE_ONLY_JSON_COMPILATION_DATABASE"
        and compile_contract.get("missing_or_unparsable_policy") == "FAIL_CLOSED"
    )
    bounded = (
        cost.get("implementation_total_person_weeks", 99)
        <= cost.get("implementation_cap_person_weeks", -1)
        <= 8
        and cost.get("independent_review_person_weeks", 99)
        <= cost.get("independent_review_cap_person_weeks", -1)
        <= 2
    )
    relations_defined = set(record.get("graph_edge_contract", {}).get("edge_kinds", ())) == set(
        EDGE_KINDS
    )
    stop_conditions = bool(record.get("scientific_decisiveness", {}).get("stop_conditions"))
    if all(
        (
            technically_representable,
            corpus_defined,
            commands_defined,
            bounded,
            relations_defined,
            stop_conditions,
        )
    ):
        return "FEASIBLE_FOR_SEPARATE_STATIC_EVIDENCE_TASK"
    if source and compile_contract and candidates:
        return "INCONCLUSIVE"
    return "DO_NOT_PROCEED"


def build_record(repo: Path) -> dict[str, Any]:
    inventory, translation_units, inventory_hash = load_release_inventory(repo)
    manifest_path = repo / SEARCH_MANIFEST
    cost = {
        "toolchain_preparation_person_weeks": 0.75,
        "graph_implementation_person_weeks": 4.25,
        "corpus_execution_person_weeks": 0.25,
        "evidence_normalization_person_weeks": 0.75,
        "tests_person_weeks": 1.0,
        "implementation_total_person_weeks": 7.0,
        "implementation_cap_person_weeks": 8.0,
        "independent_review_person_weeks": 2.0,
        "independent_review_cap_person_weeks": 2.0,
        "estimate_scope": "One pinned toolchain, the 247-file/120-TU core corpus, fail-closed graph relations, calibration, controls, and static evidence only.",
    }
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
            "task": "Decide whether a separately reviewed AST-grounded PYTHIA PDF-consumer graph task is technically bounded and scientifically useful.",
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
            "include_paths": [f"${{PYTHIA_SOURCE_ROOT}}/include"],
            "preprocessor_definitions": [],
            "required_generated_headers": [],
            "generated_configuration_note": "Upstream configure materializes Makefile.inc, not a required core parse header; a future task must fail if an include is missing.",
            "optional_feature_configuration": {
                "core_source": "ENABLED",
                "external_plugins": "DISABLED",
                "lhapdf_linkage": "DISABLED",
                "hepmc_and_fastjet_plugins": "DISABLED",
                "policy": "Expand and re-review the corpus before claiming a path that depends on a disabled module.",
            },
            "upstream_core_compiler_flags": [
                "-O2",
                "-std=c++11",
                "-pedantic",
                "-W",
                "-Wall",
                "-Wshadow",
                "-fPIC",
                "-pthread",
            ],
            "intentional_exclusions": [
                {"scope": ".external/pythia-8.3.12/include/Pythia8", "reason": "BYTE_IDENTICAL_INSTALLED_HEADER_MIRROR"},
                {"scope": "examples/", "reason": "NOT_CORE_LIBRARY_TRANSLATION_UNITS"},
                {"scope": "plugins/", "reason": "OPTIONAL_EXTERNAL_DEPENDENCIES_DISABLED_FOR_FIXED_CORE_CONTRACT"},
                {"scope": "share/ and documentation", "reason": "NON_CXX_SOURCE_INPUT"},
                {"scope": "non-.h/.cc files", "reason": "NOT_AUTHORITATIVE_CORE_CXX_SOURCE"},
            ],
        },
        "toolchain_candidates": build_toolchains(),
        "selected_toolchain": {
            "candidate_id": "LLVM_CLANG_LIBTOOLING_18_1_8",
            "selection_scope": "FEASIBILITY_REFERENCE_ONLY_NOT_AUTHORIZATION_FOR_ACQUISITION_OR_IMPLEMENTATION",
            "reason": "The pinned API exposes typed AST and source locations while permitting repository-owned fail-closed interprocedural normalization within the cost cap.",
        },
        "compilation_database_contract": {
            "upstream_cmake_can_emit_for_this_corpus": False,
            "upstream_build_system": "configure plus GNU Makefile",
            "strategy": "REPOSITORY_OWNED_SOURCE_ONLY_JSON_COMPILATION_DATABASE",
            "source_only_configuration_sufficient": True,
            "database_generated_in_this_task": False,
            "compile_commands_present_at_review": False,
            "link_or_generator_execution_required": False,
            "inspected_existing_build_tools": {
                "cmake": "/usr/bin/cmake 3.28.3",
                "gcc": "/usr/bin/gcc 13.3.0",
                "gxx": "/usr/bin/g++ 13.3.0",
                "clang": "NOT_INSTALLED",
                "clang_query": "NOT_INSTALLED",
                "codeql": "NOT_INSTALLED",
            },
            "compiler": {
                "executable": "${PINNED_LLVM_18_1_8_ROOT}/bin/clang++",
                "version": "18.1.8",
                "llvm_commit_sha": "3b5b5c1ec4a3095ab096dd780e84d7ab81f3d7ff",
            },
            "canonical_argv_template": [
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
                "${SOURCE_FILE}",
            ],
            "environment_allowlist": {"LC_ALL": "C", "TZ": "UTC"},
            "optional_modules": "All external plugins disabled; core 120 translation units required.",
            "canonicalization": [
                "Store argv arrays, never shell command strings.",
                "Normalize paths to repository-relative POSIX paths and stable root placeholders.",
                "Sort entries by semantic_file_id and reject duplicate or omitted translation units.",
                "Exclude output paths, wall-clock values, host paths, and non-allowlisted environment.",
                "Hash canonical compact JSON for the command set and environment separately.",
            ],
            "required_future_identities": [
                "canonical_compile_command_set_sha256",
                "canonical_environment_sha256",
                "compiler_binary_sha256",
                "toolchain_release_commit_sha",
            ],
            "missing_or_unparsable_policy": "FAIL_CLOSED",
        },
        "graph_root_contract": {
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
            "static_graph_can_authorize_issue_10_or_d2": False,
            "runtime_only_properties": [
                {"property": "actual_runtime_pointer_installation", "statically_proven": False, "later_evidence": "Separately authorized configuration-specific runtime pointer identity trace."},
                {"property": "post_init_pointer_substitution", "statically_proven": False, "later_evidence": "Separately authorized post-init mutation trace over the selected configuration."},
                {"property": "configuration_selected_dynamic_targets", "statically_proven": False, "later_evidence": "Reviewed configuration plus runtime target observation for every dynamic dispatch site."},
                {"property": "runtime_query_envelopes", "statically_proven": False, "later_evidence": "Separately authorized bounded query-envelope measurement with support checks."},
                {"property": "thread_and_process_behavior", "statically_proven": False, "later_evidence": "Separately authorized concurrency and lifecycle validation."},
            ],
            "runtime_evidence_may_satisfy_static_gate": False,
        },
        "calibration_contract": {
            "historical_member_count": 672,
            "use": "POST_CONSTRUCTION_HOLDOUT_ONLY",
            "may_seed_identifiers": False,
            "may_seed_roots": False,
            "may_define_edges": False,
            "may_define_reachability": False,
            "may_influence_fallback": False,
            "report_states": [
                "LOCALLY_RECOVERED",
                "EXPLICIT_BOUNDARY_OR_POLICY_EXEMPTION",
                "UNRESOLVED",
                "NOT_RECOVERED",
            ],
            "acceptance_zero_counts": [
                "GLOBAL_NAME_FALLBACK",
                "SYNTHETIC_ROOT_ATTACHMENT",
                "DANGLING_CALIBRATION_REFERENCE",
                "UNRESOLVED_BINDING_MEMBER",
                "NOT_RECOVERED_BINDING_MEMBER",
            ],
        },
        "negative_controls": {
            "identifiers": list(NEGATIVE_CONTROL_IDENTIFIERS),
            "lexical_name_admission_allowed": False,
            "co_located_line_admission_allowed": False,
            "required_proof": "The exact lexical occurrence must lie on a typed, source-backed provenance path.",
        },
        "false_negative_challenge": {
            "independent_from_graph_construction": True,
            "required_classes": list(FALSE_NEGATIVE_CLASSES),
            "acceptance": "ZERO_MATERIAL_MISSES_AND_ZERO_UNRESOLVED_BINDING_CHALLENGES",
        },
        "acceptance_gates": build_gates(),
        "scientific_decisiveness": {
            "could_materially_repair_failed_gate": "provenance_evidence_integrity",
            "repair_is_conditional_on_all_binding_gates": True,
            "cannot_establish": [
                "SIGNED_PROBABILITY_OR_RATE_VALIDITY",
                "SIGNED_SUDAKOV_MATHEMATICS",
                "RUNTIME_POINTER_IDENTITY",
                "ACTUAL_GENERATOR_QUERY_ENVELOPES",
            ],
            "not_merely_lexical_reason": "LibTooling can anchor typed declarations, calls, assignments, parameters, returns, and fields; repository logic must connect only source-supported relations and fail closed.",
            "stop_conditions": [
                "Any required translation unit cannot be parsed reproducibly.",
                "Interprocedural or member flow cannot be source-backed within the implementation cap.",
                "The holdout or independent challenge exposes a material missed path that cannot be bounded.",
                "The result degenerates into identifier, filename, global, historical, or synthetic fallback.",
            ],
            "scientific_contract_changed": False,
        },
        "cost_bound": cost,
        "failure_scope": "Failure would reject this bounded Clang-18.1.8 static consumer-graph plan; it would not prove all future source-analysis methods impossible.",
        "non_failure_scope": "Feasibility does not establish graph completeness, signed-rate mathematics, runtime reachability, generator compatibility, or permission to implement.",
        "authorization": {flag: False for flag in AUTHORIZATION_FLAGS},
        "dependencies": {
            "planning_issue": {"number": 45, "state": "OPEN", "authorization": "PLANNING_ONLY"},
            "completed_d1d_issue": {"number": 42, "state": "CLOSED"},
            "blocked_downstream_issue": {"number": 10, "state": "OPEN_BLOCKED", "gate_decision": "NOT_EVALUATED", "authorization": "NOT_AUTHORIZED"},
        },
        "next_step": {
            "action": "SEPARATE_REVIEW_OF_D1E_FEASIBILITY_AND_ACCEPTANCE_CONTRACT",
            "implementation_authorized": False,
            "condition": "Only a later explicit decision may open a separately scoped static-evidence implementation task.",
        },
        "validation": {
            "artifact_generation_deterministic": True,
            "parser_or_graph_execution_performed": False,
            "compile_database_generated": False,
            "generator_or_physics_execution_performed": False,
            "production_graph_nodes_or_edges_generated": False,
        },
    }
    record["decision"] = derive_decision(record)
    return record


def validate_record(record: dict[str, Any], repo: Path) -> None:
    required_fields = {
        "schema_version", "decision", "precedence", "objective",
        "authoritative_source_contract", "toolchain_candidates", "selected_toolchain",
        "compilation_database_contract", "graph_root_contract", "graph_edge_contract",
        "unresolved_evidence_contract", "static_runtime_boundary", "calibration_contract",
        "negative_controls", "false_negative_challenge", "acceptance_gates",
        "scientific_decisiveness", "cost_bound", "failure_scope", "non_failure_scope",
        "authorization", "dependencies", "next_step", "validation",
    }
    require(set(record) == required_fields, "artifact top-level field set differs from the v1 contract")
    require(record["schema_version"] == SCHEMA, "wrong schema")
    require(record["decision"] in ALLOWED_DECISIONS, "decision is not allowed")
    expected_precedence = build_record(repo)["precedence"]
    require(record["precedence"] == expected_precedence, "immutable D1C/D1D precedence changed")

    candidates = record["toolchain_candidates"]
    require([row.get("candidate_id") for row in candidates] == list(TOOLCHAIN_IDS), "all three exact toolchain candidates are required in deterministic order")
    required_candidate_fields = {
        "candidate_id", "exact_tool_identity", "acquisition_and_pinning_strategy", "license",
        "wsl_availability", "ci_availability", "capabilities",
        "compilation_database_requirements", "expected_unresolved_classes",
        "implementation_burden_person_weeks", "independent_review_burden_person_weeks",
        "candidate_feasibility",
    }
    for candidate in candidates:
        require(set(candidate) == required_candidate_fields, f"incomplete assessment for {candidate.get('candidate_id')}")
        require(candidate["acquisition_and_pinning_strategy"]["installation_performed_in_this_task"] is False, "tool installation is outside scope")
        require(candidate["acquisition_and_pinning_strategy"]["pin_is_immutable"] is True, "tool identity must be immutable")
        require(set(candidate["capabilities"]) == {
            "cxx_language_and_templates", "macro_handling", "dynamic_dispatch",
            "interprocedural_call_and_return", "field_member_dataflow", "alias_pointer_analysis",
            "source_coordinate_stability", "deterministic_serialization",
        }, "candidate capability matrix is incomplete")
    expected_toolchains = {row["candidate_id"]: row for row in build_toolchains()}
    selected_id = record.get("selected_toolchain", {}).get("candidate_id") if record.get("selected_toolchain") else None
    if selected_id:
        require(
            next(row for row in candidates if row["candidate_id"] == selected_id)["exact_tool_identity"]
            == expected_toolchains[selected_id]["exact_tool_identity"],
            "selected toolchain identity is not the pinned repository contract",
        )

    source = record["authoritative_source_contract"]
    expected_inventory, expected_tus, expected_hash = load_release_inventory(repo)
    require(source["authoritative_source_root"] == RELEASE_ROOT, "wrong authoritative source root")
    require(source["file_inventory"] == expected_inventory, "source inventory differs from the manifest-backed release corpus")
    require(source["inventory_sha256"] == expected_hash, "source inventory hash mismatch")
    require(source["inventory_count"] == 247 and source["header_count"] == 127, "release corpus must contain 247 files and 127 headers")
    require(source["translation_unit_count"] == 120, "exactly 120 translation units are required")
    require(source["translation_unit_semantic_file_ids"] == expected_tus, "translation-unit inventory mismatch")
    require(source["installed_mirror"]["byte_identical_headers"] == 127, "all installed mirror headers must be identity-checked")
    require(source["installed_mirror"]["semantic_node_policy"] == "IDENTITY_EVIDENCE_ONLY_EXCLUDED_FROM_GRAPH_NODES", "installed mirror may not create duplicate graph nodes")
    require(source["prior_search_manifest"]["sha256"] == file_sha256(repo / SEARCH_MANIFEST), "broad manifest identity mismatch")
    verify_source_bytes_when_available(repo, expected_inventory)

    compile_contract = record["compilation_database_contract"]
    require(compile_contract["strategy"] == "REPOSITORY_OWNED_SOURCE_ONLY_JSON_COMPILATION_DATABASE", "compile-command strategy is missing")
    require(compile_contract["database_generated_in_this_task"] is False, "compilation database generation is prohibited")
    require(compile_contract["compile_commands_present_at_review"] is False, "compile_commands.json was absent and may not be claimed present")
    require(compile_contract["link_or_generator_execution_required"] is False, "source parse must not link or execute generator code")
    require(compile_contract["missing_or_unparsable_policy"] == "FAIL_CLOSED", "missing translation units must fail closed")
    require(len(compile_contract["canonical_argv_template"]) > 5, "canonical compile argv is not defined")
    require(set(compile_contract["required_future_identities"]) == {
        "canonical_compile_command_set_sha256", "canonical_environment_sha256",
        "compiler_binary_sha256", "toolchain_release_commit_sha",
    }, "future command identity contract is incomplete")

    roots = record["graph_root_contract"]
    require(set(roots["required_root_classes"]) == set(ROOT_CLASSES), "required typed root classes are incomplete")
    require(roots["sixteen_pointer_roles"] == list(POINTER_ROLES), "all sixteen pointer roles are required")
    require(all(value is False for value in roots["prohibitions"].values()), "name/global/historical/synthetic root fallback is prohibited")
    edges = record["graph_edge_contract"]
    require(set(edges["edge_kinds"]) == set(EDGE_KINDS), "required edge kinds are incomplete")
    require(edges["direct_root_to_unit_synthetic_edge_allowed"] is False, "synthetic root-to-unit edges are prohibited")
    require(edges["source_support_required"] is True, "every edge must be source-supported")

    unresolved = record["unresolved_evidence_contract"]
    require(set(unresolved["states"]) == set(UNRESOLVED_STATES), "unresolved states are incomplete")
    require(unresolved["unresolved_may_satisfy_supported_edge"] is False, "unresolved evidence cannot satisfy closure")
    require(unresolved["closure_requires_zero_unresolved_binding_paths"] is True, "critical unresolved paths must block closure")
    runtime = record["static_runtime_boundary"]
    require(runtime["static_graph_can_authorize_issue_10_or_d2"] is False, "static evidence cannot authorize issue #10 or D2")
    require(runtime["runtime_evidence_may_satisfy_static_gate"] is False, "runtime-only claims cannot satisfy static gates")
    require(all(row["statically_proven"] is False for row in runtime["runtime_only_properties"]), "runtime-only properties may not be represented as statically proven")

    calibration = record["calibration_contract"]
    require(calibration["historical_member_count"] == 672, "the historical holdout must contain 672 members")
    require(calibration["use"] == "POST_CONSTRUCTION_HOLDOUT_ONLY", "historical evidence must be holdout-only")
    require(all(calibration[key] is False for key in (
        "may_seed_identifiers", "may_seed_roots", "may_define_edges",
        "may_define_reachability", "may_influence_fallback",
    )), "historical evidence may not seed construction or fallback")
    require({"GLOBAL_NAME_FALLBACK", "SYNTHETIC_ROOT_ATTACHMENT", "DANGLING_CALIBRATION_REFERENCE"}.issubset(calibration["acceptance_zero_counts"]), "calibration zero-count requirements are incomplete")
    require(record["negative_controls"]["identifiers"] == list(NEGATIVE_CONTROL_IDENTIFIERS), "negative controls are incomplete")
    require(record["negative_controls"]["lexical_name_admission_allowed"] is False, "lexical names cannot admit controls")
    require(record["negative_controls"]["co_located_line_admission_allowed"] is False, "same-line colocation cannot admit controls")

    gates = record["acceptance_gates"]
    require(len(gates) == 18, "exactly eighteen gates are required")
    require([gate.get("gate_id") for gate in gates] == list(GATE_IDS), "acceptance gate set or ordering changed")
    require(all(gate.get("binding") is True for gate in gates), "every acceptance gate must be binding")
    require("G07_INTERPROCEDURAL_ARGUMENT_PARAMETER_RETURN_FLOW" in {gate["gate_id"] for gate in gates}, "interprocedural flow gate is missing")
    require("G13_HOLDOUT_RECOVERY_ZERO_UNRESOLVED_OR_NOT_RECOVERED" in {gate["gate_id"] for gate in gates}, "holdout recovery gate is missing")

    cost = record["cost_bound"]
    require(cost["implementation_cap_person_weeks"] <= 8, "implementation cap exceeds eight person-weeks")
    require(cost["independent_review_cap_person_weeks"] <= 2, "review cap exceeds two person-weeks")
    require(cost["implementation_total_person_weeks"] <= cost["implementation_cap_person_weeks"], "implementation estimate exceeds cap")
    require(cost["independent_review_person_weeks"] <= cost["independent_review_cap_person_weeks"], "review estimate exceeds cap")
    require(abs(cost["implementation_total_person_weeks"] - sum(cost[key] for key in (
        "toolchain_preparation_person_weeks", "graph_implementation_person_weeks",
        "corpus_execution_person_weeks", "evidence_normalization_person_weeks",
        "tests_person_weeks",
    ))) < 1e-9, "implementation cost total does not equal its components")

    selected = record["selected_toolchain"]
    if record["decision"] == "FEASIBLE_FOR_SEPARATE_STATIC_EVIDENCE_TASK":
        require(selected is not None, "FEASIBLE requires a pinned toolchain")
        require(selected["candidate_id"] in TOOLCHAIN_IDS, "selected toolchain was not assessed")
        require("NOT_AUTHORIZATION" in selected["selection_scope"], "toolchain selection must be feasibility-only")
    elif record["decision"] == "INCONCLUSIVE":
        require(record["next_step"]["implementation_authorized"] is False, "INCONCLUSIVE cannot authorize implementation")
        require("IMPLEMENT" not in record["next_step"]["action"], "INCONCLUSIVE cannot name an implementation next step")
    else:
        require(selected is None, "DO_NOT_PROCEED cannot select an implementation toolchain")
    require(record["decision"] == derive_decision(record), "serialized decision differs from evidence-derived decision")

    require(set(record["authorization"]) == set(AUTHORIZATION_FLAGS), "authorization field set changed")
    require(all(value is False for value in record["authorization"].values()), "every authorization flag must remain false")
    dependencies = record["dependencies"]
    require(dependencies["completed_d1d_issue"] == {"number": 42, "state": "CLOSED"}, "issue #42 must remain closed")
    require(dependencies["blocked_downstream_issue"]["number"] == 10 and dependencies["blocked_downstream_issue"]["state"] == "OPEN_BLOCKED", "issue #10 must remain open and blocked")
    require(dependencies["blocked_downstream_issue"]["authorization"] == "NOT_AUTHORIZED", "issue #10 authorization changed")
    require(record["next_step"]["implementation_authorized"] is False, "next step cannot authorize implementation")
    validation = record["validation"]
    require(validation["parser_or_graph_execution_performed"] is False, "no parser or graph execution is allowed")
    require(validation["compile_database_generated"] is False, "no compilation database may be generated")
    require(validation["production_graph_nodes_or_edges_generated"] is False, "no production graph may be generated")


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
