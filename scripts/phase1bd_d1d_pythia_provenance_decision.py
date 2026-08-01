#!/usr/bin/env python3
"""Generate and validate the terminal D1D-A provenance-slice failure decision.

This module treats the broad-search manifest and provenance-slice v1 as frozen
historical evidence. It performs no source analysis and executes no physics code.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "partonsbi.phase1bd.d1d.pythia-provenance-slice-decision.v1"
AUDIT_SCHEMA = "partonsbi.phase1bd.d1d.pythia-semantics-audit.v6"
SEARCH_SCHEMA = "partonsbi.phase1bd.d1d.pythia-semantics-search-manifest.v3"
PROVENANCE_SCHEMA = "partonsbi.phase1bd.d1d.pythia-pdf-provenance-slice.v1"

SEARCH_PATH = "docs/phase1bd_d1d_pythia_semantics_search_manifest.json"
AUDIT_PATH = "docs/phase1bd_d1d_pythia_semantics_audit.json"
PROVENANCE_PATH = "docs/phase1bd_d1d_pythia_pdf_provenance_slice.json"
DECISION_PATH = "docs/phase1bd_d1d_pythia_provenance_slice_decision.json"

SEARCH_SHA256 = "e381a6774a17306336ebb016f152b611e9b66c4628e5c3835cc93efb5a9dc701"
AUDIT_V5_SOURCE_COMMIT_SHA = "e197509928d5ccbbf7765956688522f919ccecec"
AUDIT_V5_GIT_BLOB_SHA = "b152650e4e21e4ac77cc5cbab2ca8d2c0aee1987"
AUDIT_V5_SHA256 = "bfbe2020cffcfa3084f8109267c4e2ac2be2f165546fbdd9df35ecdde33b76ce"
PROVENANCE_SHA256 = "6641d6e2fb615780819bd957be2f942eab5f78f34828073eb66078088ef708c7"

AUTHORIZATION_FLAGS = (
    "IMPLEMENTATION_AUTHORIZED",
    "PROTOTYPE_AUTHORIZED",
    "PYTHIA_INIT_AUTHORIZED",
    "PYTHIA_NEXT_AUTHORIZED",
    "EVENT_GENERATION_AUTHORIZED",
    "DATASET_AUTHORIZED",
    "SIGNED_WEIGHT_PROTOTYPE_AUTHORIZED",
    "PYTHIA_FORK_AUTHORIZED",
    "ALTERNATIVE_GENERATOR_AUTHORIZED",
    "D2_AUTHORIZED",
)

REQUIRED_FAILED_GATES = (
    "typed_root_integrity",
    "local_provenance_recovery",
    "graph_path_support",
    "edge_source_support",
    "historical_calibration_independence",
    "occurrence_disposition_integrity",
    "outside_slice_recall",
    "reachability_evidence",
    "validator_soundness",
    "getxpdf_normalization",
)

INTEGRITY_REVIEW_COUNTS: dict[str, Any] = {
    "structural_totals": {
        "source_file_count": 374,
        "searched_identifier_count": 779,
        "broad_raw_row_count": 67375,
        "p10_row_count": 63763,
        "root_count": 939,
        "candidate_unit_count": 867,
        "graph_node_count": 1841,
        "graph_edge_count": 1221,
    },
    "root_integrity": {
        "confirmed_root_count": 720,
        "ordinary_use_root_count": 162,
        "call_site_root_count": 43,
        "unresolved_root_count": 14,
        "misclassified_or_unresolved_root_count": 219,
        "function_symbol_in_owner_field_count": 401,
        "generic_declared_type_count": 722,
        "heuristic_reachability_flag_count": 939,
    },
    "historical_recovery_without_global_fallback": {
        "LOCAL_TYPED_RECOVERED": 0,
        "FALLBACK_XF_PDF_PDFPTR_ONLY": 669,
        "NOT_RECOVERED": 3,
        "dangling_member_ids": ["CSG034.M006", "CSG034.M007", "CSG034.M014"],
        "shared_global_root": {
            "declared_type": "class PDF",
            "line": 49,
            "source_file": ".external/pythia-8.3.12/include/Pythia8/PartonDistributions.h",
        },
    },
    "graph_integrity": {
        "path_length_two_count": 867,
        "explicit_multi_edge_dataflow_count": 0,
        "historical_global_root_attachment_count": 669,
        "root_to_unit_synthetic_only_path_count": 103,
        "unresolved_dynamic_or_alias_path_count": 35,
    },
    "production_interprocedural_dataflow": {
        "ASSIGNED_FROM": 0,
        "PASSED_AS_ARGUMENT": 0,
        "RECEIVED_AS_PARAMETER": 0,
        "FORWARDED_TO": 0,
        "CALLS": 0,
        "MAY_ALIAS": 0,
        "cache_write_read_chain_count": 0,
        "caller_return_propagation_count": 0,
    },
    "edge_support": {
        "source_supported_count": 314,
        "source_supports_target_only_count": 33,
        "synthetic_root_attachment_count": 658,
        "wrong_edge_kind_count": 181,
        "unresolved_edge_support_count": 35,
    },
    "occurrence_contamination": {
        "directly_contributes_count": 754,
        "same_expression_alias_count": 77,
        "same_line_unrelated_count": 209,
        "declaration_or_comment_count": 11,
        "negative_control_wrong_dispositions": {"id": 28, "state": 4},
    },
    "outside_slice_recall_challenge": {
        "legitimate_missed_provenance_occurrence_count": 46,
        "legitimate_missed_provenance_coordinate_count": 32,
        "provenance_unresolved_occurrence_count": 189,
        "provenance_unresolved_coordinate_count": 139,
    },
    "getxpdf_normalization": {
        "lexical_occurrence_count": 35,
        "inline_wrapper_definition_count": 4,
        "direct_call_count": 31,
        "mirror_deduplicated_semantic_unit_count": 33,
        "serialized_unresolved_unit_count": 35,
    },
    "validator_adversarial_review": {
        "incorrectly_accepted_count": 7,
        "correctly_rejected_count": 1,
    },
}


class DecisionError(RuntimeError):
    """Raised when the final provenance decision contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DecisionError(message)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )


def build_decision() -> dict[str, Any]:
    return {
        "authorization": {flag: False for flag in AUTHORIZATION_FLAGS},
        "decision": "FAIL",
        "evaluated_artifact": {
            "audit_v5": {
                "git_blob_sha": AUDIT_V5_GIT_BLOB_SHA,
                "repository_path": AUDIT_PATH,
                "schema_version": "partonsbi.phase1bd.d1d.pythia-semantics-audit.v5",
                "sha256": AUDIT_V5_SHA256,
                "source_commit_sha": AUDIT_V5_SOURCE_COMMIT_SHA,
            },
            "broad_search_manifest": {
                "path": SEARCH_PATH,
                "schema_version": SEARCH_SCHEMA,
                "sha256": SEARCH_SHA256,
            },
            "provenance_slice_v1": {
                "path": PROVENANCE_PATH,
                "schema_version": PROVENANCE_SCHEMA,
                "sha256": PROVENANCE_SHA256,
                "status": "REJECTED_DIAGNOSTIC",
            },
        },
        "failed_gates": list(REQUIRED_FAILED_GATES),
        "failure_scope": (
            "repository-owned tokenizer provenance slice v1 and its scientific "
            "acceptance claims"
        ),
        "integrity_review_counts": copy.deepcopy(INTEGRITY_REVIEW_COUNTS),
        "next_step": "SCIENTIFIC_REVIEW_AND_MERGE_NEGATIVE_D1D_A_RECORD",
        "non_failure_scope": [
            "broad syntactic occurrence replay",
            "deterministic JSON generation",
            "direct source-reviewed downstream nonnegativity evidence",
            "MINIMAL_PUBLIC_READER_PATCH = INSUFFICIENT",
            "immutable D1C_FINAL_DECISION = FAIL",
            "modified or forked generator possibilities not yet reviewed",
            "alternative generator possibilities not yet reviewed",
        ],
        "precedence": "EVIDENCE_INTEGRITY_FAIL_PRECEDENCE",
        "preserved_supported_results": {
            "D1C_FINAL_DECISION": "FAIL",
            "MINIMAL_PUBLIC_READER_PATCH": "INSUFFICIENT",
            "broad_syntactic_occurrence_replay": "SUPPORTED",
            "deterministic_json_generation": "SUPPORTED",
            "direct_source_reviewed_downstream_nonnegativity_evidence": (
                "SUPPORTED_INDEPENDENTLY_OF_PROVENANCE_SLICE_V1"
            ),
        },
        "schema_version": SCHEMA,
        "unsupported_claims": [
            "all 939 roots are typed declarations or definitions",
            "serialized provenance paths represent source-backed PDF dataflow",
            "672 of 672 historical members are independently recovered",
            "62050 occurrences are proven outside PDF provenance",
            "negative controls prove occurrence-level disposition correctness",
            "163 machine-sliced units form a valid scientific review queue",
        ],
        "validation": {
            "all_authorization_flags_false": True,
            "architecture_comparison_ready": False,
            "decision_is_fail": True,
            "historical_artifact_hashes_required": True,
            "rejected_diagnostics_are_readiness_evidence": False,
        },
    }


def validate_payload(
    decision: dict[str, Any],
    audit: dict[str, Any] | None,
    actual_search_sha256: str,
    actual_provenance_sha256: str,
    decision_sha256: str | None = None,
) -> None:
    require(decision["schema_version"] == SCHEMA, "decision schema mismatch")
    require(decision["decision"] == "FAIL", "provenance decision must be FAIL")
    require(
        decision["precedence"] == "EVIDENCE_INTEGRITY_FAIL_PRECEDENCE",
        "decision precedence mismatch",
    )
    require(
        set(decision["failed_gates"]) == set(REQUIRED_FAILED_GATES)
        and len(decision["failed_gates"]) == len(REQUIRED_FAILED_GATES),
        "required failed-gate set mismatch",
    )
    require(
        decision["integrity_review_counts"] == INTEGRITY_REVIEW_COUNTS,
        "integrity-review counts mismatch",
    )
    evaluated = decision["evaluated_artifact"]
    require(
        evaluated["audit_v5"]
        == {
            "git_blob_sha": AUDIT_V5_GIT_BLOB_SHA,
            "repository_path": AUDIT_PATH,
            "schema_version": "partonsbi.phase1bd.d1d.pythia-semantics-audit.v5",
            "sha256": AUDIT_V5_SHA256,
            "source_commit_sha": AUDIT_V5_SOURCE_COMMIT_SHA,
        },
        "evaluated audit-v5 reference mismatch",
    )
    require(
        evaluated["broad_search_manifest"]
        == {
            "path": SEARCH_PATH,
            "schema_version": SEARCH_SCHEMA,
            "sha256": SEARCH_SHA256,
        },
        "broad-manifest decision reference mismatch",
    )
    require(
        actual_search_sha256 == SEARCH_SHA256,
        "frozen broad-manifest hash drift",
    )
    require(
        evaluated["provenance_slice_v1"]["path"] == PROVENANCE_PATH
        and evaluated["provenance_slice_v1"]["schema_version"] == PROVENANCE_SCHEMA
        and evaluated["provenance_slice_v1"]["sha256"] == PROVENANCE_SHA256
        and evaluated["provenance_slice_v1"]["status"] == "REJECTED_DIAGNOSTIC",
        "provenance-slice decision reference mismatch",
    )
    require(
        actual_provenance_sha256 == PROVENANCE_SHA256,
        "frozen provenance-slice hash drift",
    )
    require(
        all(decision["authorization"].get(flag) is False for flag in AUTHORIZATION_FLAGS),
        "decision authorization flag is true or absent",
    )
    require(
        decision["failure_scope"]
        == (
            "repository-owned tokenizer provenance slice v1 and its scientific "
            "acceptance claims"
        ),
        "failure scope mismatch",
    )
    require(
        decision["next_step"]
        == "SCIENTIFIC_REVIEW_AND_MERGE_NEGATIVE_D1D_A_RECORD",
        "next step mismatch",
    )
    require(
        decision["preserved_supported_results"]["MINIMAL_PUBLIC_READER_PATCH"]
        == "INSUFFICIENT",
        "minimal-reader conclusion changed",
    )
    require(
        decision["preserved_supported_results"]["D1C_FINAL_DECISION"] == "FAIL",
        "D1C immutable FAIL changed",
    )
    require(
        decision["validation"]["rejected_diagnostics_are_readiness_evidence"]
        is False,
        "rejected diagnostics were promoted to readiness evidence",
    )
    require(
        decision["validation"]["architecture_comparison_ready"] is False,
        "decision claims architecture-comparison readiness",
    )
    if audit is None:
        return
    require(audit["schema_version"] == AUDIT_SCHEMA, "audit schema is not v6")
    require(audit["d1d_a_result"] == "FAIL", "D1D-A result changed")
    require(audit["d1d_a_final_decision"] == "FAIL", "D1D-A final decision changed")
    require(audit["failed_gate"] == "provenance_evidence_integrity", "failed gate mismatch")
    require(
        audit["provenance_slice_v1_status"] == "REJECTED_DIAGNOSTIC",
        "provenance slice is not rejected diagnostic evidence",
    )
    require(
        audit["provenance_slice_v1_decision"] == "FAIL",
        "provenance-slice v1 decision changed",
    )
    require(
        audit["architecture_comparison_ready"] is False,
        "audit claims architecture-comparison readiness",
    )
    require("readiness_rule" not in audit, "rejected slice still supplies readiness")
    require(
        "historical_recall_calibration" not in audit,
        "audit still claims independent 672/672 provenance recovery",
    )
    require(
        audit["rejected_provenance_slice_v1_diagnostics"]["role"]
        == "REJECTED_DIAGNOSTIC_NOT_READINESS_EVIDENCE",
        "rejected diagnostic role mismatch",
    )
    require(
        audit["search_manifest"]
        == {
            "path": SEARCH_PATH,
            "schema_version": SEARCH_SCHEMA,
            "sha256": SEARCH_SHA256,
            "source_inventory_id": "PYTHIA_8_312_INSTALLED_RELEASE_H_CC_374",
        },
        "audit broad-manifest reference mismatch",
    )
    require(
        audit["provenance_slice"]
        == {
            "path": PROVENANCE_PATH,
            "role": "REJECTED_DIAGNOSTIC_NOT_READINESS_EVIDENCE",
            "schema_version": PROVENANCE_SCHEMA,
            "sha256": PROVENANCE_SHA256,
            "status": "REJECTED_DIAGNOSTIC",
        },
        "audit rejected provenance-slice reference mismatch",
    )
    require(
        all(audit["authorization"].get(flag) is False for flag in AUTHORIZATION_FLAGS),
        "audit authorization flag is true or absent",
    )
    require(audit["minimal_public_reader_patch"] == "INSUFFICIENT", "minimal reader changed")
    require(audit["d1c_stock_boundary_decision"] == "FAIL", "D1C audit decision changed")
    reference = audit["provenance_slice_decision"]
    require(
        reference["path"] == DECISION_PATH
        and reference["schema_version"] == SCHEMA,
        "audit decision-artifact reference mismatch",
    )
    if decision_sha256 is not None:
        require(reference["sha256"] == decision_sha256, "audit decision hash mismatch")


def validate(root: Path, decision_path: Path, audit_path: Path) -> dict[str, Any]:
    decision = load_json(decision_path)
    audit = load_json(audit_path)
    validate_payload(
        decision,
        audit,
        sha256_file(root / SEARCH_PATH),
        sha256_file(root / PROVENANCE_PATH),
        sha256_file(decision_path),
    )
    return {
        "all_authorization_flags_false": True,
        "audit_schema": audit["schema_version"],
        "decision": decision["decision"],
        "decision_schema": decision["schema_version"],
        "failed_gate_count": len(decision["failed_gates"]),
        "frozen_broad_manifest_sha256": sha256_file(root / SEARCH_PATH),
        "frozen_provenance_slice_sha256": sha256_file(root / PROVENANCE_PATH),
        "rejected_diagnostics_are_readiness_evidence": False,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--generate", action="store_true")
    mode.add_argument("--validate", action="store_true")
    parser.add_argument("--decision", type=Path, default=Path(DECISION_PATH))
    parser.add_argument("--audit", type=Path, default=Path(AUDIT_PATH))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    decision_path = args.decision if args.decision.is_absolute() else root / args.decision
    audit_path = args.audit if args.audit.is_absolute() else root / args.audit
    try:
        if args.generate:
            require(sha256_file(root / SEARCH_PATH) == SEARCH_SHA256, "frozen broad hash drift")
            require(
                sha256_file(root / PROVENANCE_PATH) == PROVENANCE_SHA256,
                "frozen provenance hash drift",
            )
            write_json(decision_path, build_decision())
            result = {
                "decision": "FAIL",
                "decision_schema": SCHEMA,
                "decision_sha256": sha256_file(decision_path),
            }
        else:
            result = validate(root, decision_path, audit_path)
    except (DecisionError, KeyError, OSError, ValueError) as error:
        print(f"D1D provenance decision validation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
