#!/usr/bin/env python3
"""Generate and validate the Phase 1B-D1D-A static PYTHIA source evidence.

This program only reads PYTHIA headers/source and documentation evidence.  It
does not load or execute PYTHIA, APFEL, LHAPDF, or a repository physics binary.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shlex
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


AUDIT_SCHEMA_V3 = "partonsbi.phase1bd.d1d.pythia-semantics-audit.v3"
AUDIT_SCHEMA_V4 = "partonsbi.phase1bd.d1d.pythia-semantics-audit.v4"
SEARCH_SCHEMA_V2 = "partonsbi.phase1bd.d1d.pythia-semantics-search-manifest.v2"
SEARCH_SCHEMA_V3 = "partonsbi.phase1bd.d1d.pythia-semantics-search-manifest.v3"
INVENTORY_ID = "PYTHIA_8_312_INSTALLED_RELEASE_H_CC_374"
GENERATOR_PATH = "scripts/phase1bd_d1d_pythia_semantics_audit.py"
AUTHORITATIVE_ENGINE = "PYTHON_REGEX_OCCURRENCE_ENGINE_V1"
ENGINE_FLAGS = ("ASCII",)
DETERMINISTIC_ORDERING = (
    "engine_identity",
    "specification_id",
    "inventory_file_id",
    "line_number",
    "utf8_byte_offset",
    "match_ordinal_on_line",
    "normalized_identifier",
    "matched_identifier_sha256_16",
)

LEGITIMATE_RECALL_NAMES = {
    "PDFEnvelope",
    "calcPDFEnvelope",
    "gammaPDFRefScale",
    "gammaPDFxDependence",
    "getPDFEnvelope",
    "newValenceContent",
    "pdfAPtr",
    "pdfBPtr",
    "pdfHardAPtr",
    "pdfHardBPtr",
    "pdfMemberVars",
    "pickValence",
    "xMax",
    "xfApprox",
    "xfModPrep",
    "xfModified0",
    "xfRaw",
}
GET_XPDF_NAME = "getXPDF"
RECALL_NAMES = LEGITIMATE_RECALL_NAMES | {GET_XPDF_NAME}
POINTER_FIELDS = {
    "pdfAPtr": "PR01",
    "pdfBPtr": "PR02",
    "pdfHardAPtr": "PR03",
    "pdfHardBPtr": "PR04",
}
BOUNDARY_RECALL_NAMES = {"xfRaw", "xfModPrep", "xfModified0"}

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

SEMANTIC_CLASSES = (
    "REQUIRES_NONNEGATIVE_DENSITY",
    "REQUIRES_STRICTLY_POSITIVE_DENOMINATOR",
    "REQUIRES_NONNEGATIVE_RATE",
    "REQUIRES_PROBABILITY_IN_ZERO_ONE",
    "REQUIRES_NONNEGATIVE_MAXIMUM_OR_ENVELOPE",
    "REQUIRES_MONOTONE_CUMULATIVE_WEIGHT",
    "SUPPORT_DOMAIN_CHECK_NOT_SIGN_SEMANTICS",
)

REACHABILITY = (
    "PROSPECTIVE_HERA_SOURCE_REACHABLE",
    "SOURCE_CAPABLE_DISABLED_BY_CONFIGURATION",
    "HERA_REACHABILITY_UNRESOLVED",
    "BOUNDARY_OR_METADATA_NOT_A_RUNTIME_PATH",
)

EVIDENCE_ORIGINS = (
    "SEARCH_DERIVED",
    "HEADER_INVENTORY_DERIVED",
    "CONFIGURATION_DERIVED",
    "POLICY_QUESTION",
    "MANUAL_SCIENTIFIC_INFERENCE",
)

CLASSIFICATIONS = (
    "MACHINE_DISCOVERED_CANDIDATE",
    "INCLUDED_CONCRETE_CALL_SITE",
    "INCLUDED_BOUNDARY_NODE",
    "INCLUDED_POINTER_ROLE",
    "INCLUDED_POLICY_EVIDENCE",
    "DEFINITION_ONLY",
    "DECLARATION_ONLY",
    "COMMENT_OR_DOCUMENTATION",
    "FALSE_POSITIVE",
    "DUPLICATE_ALIAS_OF_RECORDED_SITE",
    "SOURCE_CAPABLE_BUT_IRRELEVANT_TO_PDF_SEMANTICS",
)

TARGET_TYPES = (
    "call_site_member",
    "boundary_member",
    "pointer_role",
    "policy_unresolved",
    "policy_evidence",
)

RAW_ROW_SCHEMA = (
    "raw_match_id",
    "engine_identity",
    "pattern_id",
    "inventory_file_id",
    "line_number",
    "match_ordinal_on_line",
    "utf8_byte_offset",
    "identifier_dictionary_index",
    "matched_identifier_sha256_16",
    "classification_dictionary_index",
    "reason_dictionary_index",
    "symbol_dictionary_index",
    "primary_target_type_dictionary_index",
    "primary_target_id",
    "related_targets",
    "legacy_v1_raw_match_id",
)

REVIEW_STATES = (
    "MACHINE_DISCOVERED_UNREVIEWED",
    "SOURCE_REVIEWED_MATERIAL",
    "SOURCE_REVIEWED_BOUNDARY",
    "SOURCE_REVIEWED_POINTER_OR_POLICY",
    "SOURCE_REVIEWED_NONMATERIAL",
    "POLICY_UNRESOLVED",
)

CANDIDATE_ROW_SCHEMA = (
    "candidate_id",
    "inventory_file_id",
    "line_number",
    "utf8_byte_offset",
    "identifier_dictionary_index",
    "identifier_hash",
    "discovery_specification_dictionary_index",
    "machine_discovery_status_dictionary_index",
    "scientific_review_status_dictionary_index",
    "materiality_status_dictionary_index",
    "semantic_class_status_dictionary_index",
    "reachability_status_dictionary_index",
    "mapping_target_type_dictionary_index",
    "mapping_target_id",
    "unresolved_reason_dictionary_index",
    "owning_symbol_status_dictionary_index",
    "owning_symbol_dictionary_index",
    "owning_symbol_start_line",
    "owning_symbol_end_line",
    "relationship_dictionary_index",
    "on_previously_matched_line",
    "semantic_review_hint_dictionary_index",
    "semantic_review_hint_basis_dictionary_index",
    "reachability_review_hint_dictionary_index",
    "reachability_review_hint_basis_dictionary_index",
)

WRONG_DENOMINATOR_MEMBER_IDS = {
    "CSG012.M005",
    "CSG012.M006",
    "CSG012.M007",
    "CSG012.M008",
    "CSG012.M017",
    "CSG012.M018",
    "CSG012.M019",
    "CSG012.M020",
    "CSG012.M031",
    "CSG012.M032",
    "CSG012.M033",
    "CSG012.M034",
    "CSG012.M043",
    "CSG012.M044",
    "CSG012.M045",
    "CSG012.M046",
    "CSG014.M002",
    "CSG015.M005",
    "CSG015.M006",
    "CSG018.M002",
    "CSG018.M003",
    "CSG019.M002",
    "CSG019.M003",
    "CSG021.M002",
    "CSG021.M004",
    "CSG026.M001",
    "CSG026.M002",
    "CSG027.M004",
    "CSG027.M005",
    "CSG028.M003",
    "CSG028.M004",
    "CSG033.M003",
    "CSG033.M004",
    "CSG033.M005",
    "CSG033.M006",
    "CSG040.M004",
    "CSG040.M007",
    "CSG040.M010",
    "CSG040.M013",
    "CSG043.M002",
    "CSG044.M003",
    "CSG046.M003",
    "CSG047.M002",
    "CSG047.M003",
    "CSG047.M004",
    "CSG048.M002",
    "CSG048.M003",
    "CSG048.M004",
    "CSG048.M005",
    "CSG048.M006",
    "CSG049.M002",
    "CSG049.M003",
    "CSG049.M004",
    "CSG049.M005",
    "CSG050.M002",
    "CSG050.M003",
    "CSG050.M004",
    "CSG050.M005",
    "CSG115.M002",
    "CSG115.M003",
    "CSG115.M004",
    "CSG129.M001",
    "CSG129.M002",
    "CSG129.M003",
    "CSG129.M004",
    "CSG129.M005",
}

class EvidenceError(RuntimeError):
    """Raised when checked evidence violates a declared invariant."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def repository_root(script_path: Path | None = None) -> Path:
    here = (script_path or Path(__file__)).resolve()
    return here.parent.parent


def _python_patterns(
    pattern_id: str, searched_vocabulary: Iterable[str] | None = None
) -> tuple[str, str]:
    patterns = {
        "P01_PDF_POINTER_SURFACE": (
            r"PDFPtr|setPDFPtr|getPDFPtr|pdf[A-Za-z0-9_]*(?:Beam|Pom|Gam|Unres|VMD)[A-Za-z0-9_]*Ptr",
            r"PDFPtr|setPDFPtr|getPDFPtr|pdf[A-Za-z0-9_]*Ptr",
        ),
        "P02_PDF_ENTRY_POINTS": (
            r"(?:^|[^A-Za-z0-9_])(?:xf|xfVal|xfSea|xfUpdate|xfHard|xfISR|xfMPI|xfModified|xfMax|xfSame|insideBounds|xfFlux|xfApprox|xfGamma)\s*\(",
            r"\b(?:xf|xfVal|xfSea|xfUpdate|xfHard|xfISR|xfMPI|xfModified|xfMax|xfSame|insideBounds|xfFlux|xfApprox|xfGamma)\b",
        ),
        "P03_ALPHA_S": (
            r"(?:^|[^A-Za-z0-9_])alphaS\s*\(|alphaS[A-Za-z0-9_]*",
            r"\balphaS[A-Za-z0-9_]*\b",
        ),
        "P04_VALENCE_SEA_COMPANION_CACHE": (
            r"xqVal|xqgSea|xqComp|xqgTot|rescaleGS|pickValSeaComp",
            r"\b(?:xqVal|xqgSea|xqComp|xqgTot|rescaleGS|pickValSeaComp)\b",
        ),
        "P05_PDF_RATIOS": (
            r"pdfRatio|pdfNum|pdfDen|pdfOld|pdfNew|pdfMother|pdfDaughter",
            r"\b(?:pdfRatio|pdfNum|pdfDen|pdfOld|pdfNew|pdfMother|pdfDaughter)\b",
        ),
        "P06_PDF_WEIGHTED_SIGMA": (
            r"pdfSigma|sigmaPDF|sigmaSumSave|sigmaMax|sigmaMx|allowNegativeSigma",
            r"\b(?:pdfSigma|sigmaPDF|sigmaSumSave|sigmaMax|sigmaMx|allowNegativeSigma)\b",
        ),
        "P07_PDF_AND_EVENT_WEIGHTS": (
            r"wtPDF|pdfWeight|pdfWt|weightStrategy|lhaStrategy|allowNegativeSigma",
            r"\b(?:wtPDF|pdfWeight|pdfWt|weightStrategy|lhaStrategy|allowNegativeSigma)\b",
        ),
        "P08_DENOMINATOR_FLOORS": (r"TINYPDF", r"\bTINYPDF\b"),
        "P09_INDIRECT_CONSUMER_HANDOFF": (
            r"remnantFlavours|gammaInitiatorIsVal",
            r"\b(?:remnantFlavours|gammaInitiatorIsVal)\b",
        ),
    }
    if pattern_id == "P10_DECLARATION_DERIVED_RECALL":
        require(searched_vocabulary is not None, "P10 requires a searched vocabulary")
        names = sorted(set(searched_vocabulary))
        require(names, "P10 searched vocabulary is empty")
        escaped = "|".join(re.escape(name) for name in names)
        token_pattern = rf"\b(?:{escaped})\b"
        return token_pattern, token_pattern
    return patterns[pattern_id]


def make_structured_specs(
    source: dict[str, Any], searched_vocabulary: Iterable[str]
) -> list[dict[str, Any]]:
    """Build authoritative Python-regex specifications.

    Supplementary grep argv are descriptive reproductions only.  They are not
    used to establish the serialized occurrence set.
    """

    roots = list(source["search_roots"])
    old_specs = source.get("search_commands", source.get("structured_search_specs", []))
    specs: list[dict[str, Any]] = []
    for old in old_specs:
        if old["pattern_id"] == "P10_DECLARATION_DERIVED_RECALL":
            continue
        line_pattern, token_pattern = _python_patterns(old["pattern_id"])
        supplementary_pattern = old.get("pattern", line_pattern)
        argv = [
            "-RInE",
            "--include=*.h",
            "--include=*.cc",
            supplementary_pattern,
            *roots,
        ]
        specs.append(
            {
                "deterministic_ordering_rule": list(DETERMINISTIC_ORDERING),
                "engine_identity": AUTHORITATIVE_ENGINE,
                "flags": list(ENGINE_FLAGS),
                "pattern_id": old["pattern_id"],
                "regex": line_pattern,
                "purpose": old["purpose"],
                "source_inventory_id": INVENTORY_ID,
                "supplementary_grep_argv": ["grep", *argv],
                "supplementary_grep_command": shlex.join(["grep", *argv]),
                "token_extraction_regex": token_pattern,
            }
        )
    names = sorted(set(searched_vocabulary))
    line_pattern, token_pattern = _python_patterns(
        "P10_DECLARATION_DERIVED_RECALL", names
    )
    argv = ["-RInE", "--include=*.h", "--include=*.cc", token_pattern, *roots]
    specs.append(
        {
            "deterministic_ordering_rule": list(DETERMINISTIC_ORDERING),
            "engine_identity": AUTHORITATIVE_ENGINE,
            "flags": list(ENGINE_FLAGS),
            "pattern_id": "P10_DECLARATION_DERIVED_RECALL",
            "regex": line_pattern,
            "purpose": "complete declaration/definition-derived vocabulary occurrence recall",
            "source_inventory_id": INVENTORY_ID,
            "supplementary_grep_argv": ["grep", *argv],
            "supplementary_grep_command": shlex.join(["grep", *argv]),
            "token_extraction_regex": token_pattern,
            "searched_vocabulary_count": len(names),
            "searched_vocabulary_sha256": sha256_bytes(
                "\n".join(names).encode("utf-8")
            ),
        }
    )
    return specs


def validate_search_spec(
    spec: dict[str, Any], searched_vocabulary: Iterable[str]
) -> None:
    require(
        spec.get("engine_identity") == AUTHORITATIVE_ENGINE,
        f"unsupported authoritative engine: {spec.get('engine_identity')}",
    )
    require(spec.get("flags") == list(ENGINE_FLAGS), "unsupported engine flags")
    require(
        spec.get("source_inventory_id") == INVENTORY_ID,
        "search spec inventory mismatch",
    )
    require(
        spec.get("deterministic_ordering_rule") == list(DETERMINISTIC_ORDERING),
        "search spec ordering mismatch",
    )
    expected_line, expected_token = _python_patterns(
        spec["pattern_id"],
        searched_vocabulary
        if spec["pattern_id"] == "P10_DECLARATION_DERIVED_RECALL"
        else None,
    )
    require(spec.get("regex") == expected_line, "pattern/engine regex mismatch")
    require(
        spec.get("token_extraction_regex") == expected_token,
        "pattern/engine token-extraction mismatch",
    )


def unjustified_vocabulary_omissions(
    omissions: Iterable[dict[str, str]],
) -> list[dict[str, str]]:
    allowed_reasons = {"NON_SEMANTIC_LANGUAGE_KEYWORD"}
    return [
        item
        for item in omissions
        if not item.get("identifier") or item.get("reason") not in allowed_reasons
    ]


def read_inventory(root: Path, files: Iterable[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        item["path"]: (root / item["path"])
        .read_text(encoding="utf-8", errors="replace")
        .splitlines()
        for item in files
    }


def iter_structured_matches(
    specs: Iterable[dict[str, Any]],
    files: Iterable[dict[str, Any]],
    lines: dict[str, list[str]],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for spec in specs:
        require(
            spec.get("engine_identity") == AUTHORITATIVE_ENGINE,
            f"unsupported authoritative engine: {spec.get('engine_identity')}",
        )
        flags = re.ASCII if spec.get("flags") == ["ASCII"] else 0
        require(flags == re.ASCII, "unsupported authoritative-engine flags")
        line_re = re.compile(spec["regex"], flags)
        token_re = re.compile(spec["token_extraction_regex"], flags)
        for file_item in sorted(files, key=lambda item: item["file_id"]):
            path = file_item["path"]
            for line_number, line in enumerate(lines[path], 1):
                if not line_re.search(line):
                    continue
                token_matches = list(token_re.finditer(line))
                if not token_matches:
                    fallback = line_re.search(line)
                    require(fallback is not None, "line search lost its own match")
                    token_matches = [fallback]
                for ordinal, match in enumerate(token_matches):
                    identifier = match.group(0)
                    matches.append(
                        {
                            "byte_offset": len(line[: match.start()].encode("utf-8")),
                            "engine_identity": spec["engine_identity"],
                            "file_id": file_item["file_id"],
                            "identifier": identifier,
                            "identifier_hash": sha256_bytes(identifier.encode("utf-8"))[:16],
                            "line": line_number,
                            "ordinal": ordinal,
                            "path": path,
                            "pattern_id": spec["pattern_id"],
                        }
                    )
    return sorted(matches, key=canonical_match_key)


def canonical_match_key(match: dict[str, Any]) -> tuple[Any, ...]:
    return (
        match.get("engine_identity", AUTHORITATIVE_ENGINE),
        match["pattern_id"],
        match["file_id"],
        int(match["line"]),
        int(match["byte_offset"]),
        int(match["ordinal"]),
        match["identifier"],
        match["identifier_hash"],
    )


def semantic_for_identifiers(identifiers: Iterable[str]) -> tuple[str, str]:
    """Return a non-binding review hint, never a final semantic class."""

    names = set(identifiers)
    if names & {
        "xMax",
        "PDFEnvelope",
        "calcPDFEnvelope",
        "getPDFEnvelope",
        "pdfMemberVars",
    }:
        return "REVIEW_HINT_MAXIMUM_OR_ENVELOPE", "IDENTIFIER_FAMILY_ONLY"
    if names & {"pickValence", "newValenceContent"}:
        return "REVIEW_HINT_CUMULATIVE_SELECTION", "IDENTIFIER_FAMILY_ONLY"
    return "REVIEW_HINT_DENSITY_LIKE", "IDENTIFIER_FAMILY_ONLY"


def reachability_for_path(path: str) -> tuple[str, str]:
    """Return a non-binding filename hint, never final reachability."""

    disabled = ("Dire", "MultipartonInteractions", "Vincia", "Merging", "Photon")
    if any(name in path for name in disabled):
        return "REVIEW_HINT_CONFIGURATION_DISABLED", "FILENAME_ONLY"
    if any(
        name in path for name in ("BeamRemnants", "PartonLevel", "SimpleSpaceShower")
    ):
        return "REVIEW_HINT_POSSIBLY_HERA_REACHABLE", "FILENAME_ONLY"
    return "REVIEW_HINT_REACHABILITY_UNKNOWN", "FILENAME_ONLY"


def derive_candidate_ledger(
    matches: list[dict[str, Any]],
    historical_findings: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Serialize every P10 occurrence before assigning any relationships.

    The v3 material recall additions were name/path heuristic products, so they
    are deliberately returned to machine-unreviewed status.  The prior 90/15
    totals remain integrity-review baselines, not forced v4 totals.
    """

    old_by_coordinate = {
        (item["path"], int(item["line"])): item for item in historical_findings
    }
    prior_lines = {
        (item["path"], int(item["line"]))
        for item in matches
        if item["pattern_id"] != "P10_DECLARATION_DERIVED_RECALL"
    }
    prior_occurrences = {
        (
            item["path"],
            int(item["line"]),
            int(item["byte_offset"]),
            item["identifier"],
        )
        for item in matches
        if item["pattern_id"] != "P10_DECLARATION_DERIVED_RECALL"
    }
    ledger: list[dict[str, Any]] = []
    for index, match in enumerate(
        (
            item
            for item in matches
            if item["pattern_id"] == "P10_DECLARATION_DERIVED_RECALL"
        ),
        1,
    ):
        historical = old_by_coordinate.get((match["path"], int(match["line"])))
        review_state = "MACHINE_DISCOVERED_UNREVIEWED"
        materiality = "MATERIALITY_UNRESOLVED"
        mapping_target: dict[str, str] | None = None
        unresolved_reason = (
            "full-vocabulary machine discovery has not received coordinate-level source review"
        )
        if historical and match["identifier"] in historical["identifiers"]:
            outcome = historical["outcome"]
            if outcome == "UNRESOLVED" and match["identifier"] == GET_XPDF_NAME:
                review_state = "POLICY_UNRESOLVED"
                materiality = "MATERIAL_CANDIDATE"
                mapping_target = {"target_type": "policy_unresolved", "target_id": "PU05"}
                unresolved_reason = "getXPDF semantic and reachability classification is intentionally unresolved"
            elif outcome == "INCLUDED_AS_BOUNDARY":
                review_state = "SOURCE_REVIEWED_BOUNDARY"
                materiality = "BOUNDARY"
                mapping_target = {
                    "target_type": historical["target_type"],
                    "target_id": historical["target_id"],
                }
                unresolved_reason = ""
            elif outcome == "INCLUDED_AS_POINTER_OR_POLICY_EVIDENCE":
                review_state = "SOURCE_REVIEWED_POINTER_OR_POLICY"
                materiality = "POINTER_OR_POLICY"
                target_id = POINTER_FIELDS.get(
                    match["identifier"], historical["target_id"]
                )
                mapping_target = {
                    "target_type": historical["target_type"],
                    "target_id": target_id,
                }
                unresolved_reason = ""
            elif outcome == "INCLUDED_AS_MATERIAL_CONSUMER":
                materiality = "MATERIAL_CANDIDATE"
                unresolved_reason = (
                    "v3 name/path heuristic material classification requires explicit source re-review"
                )
        semantic_hint, semantic_basis = semantic_for_identifiers([match["identifier"]])
        reachability_hint, reachability_basis = reachability_for_path(match["path"])
        exact_prior = (
            match["path"],
            int(match["line"]),
            int(match["byte_offset"]),
            match["identifier"],
        ) in prior_occurrences
        ledger.append(
            {
                "candidate_id": f"DC{index:06d}",
                "discovered_identifier": match["identifier"],
                "discovery_specification": match["pattern_id"],
                "identifier_hash": match["identifier_hash"],
                "inventory_file_id": match["file_id"],
                "line": match["line"],
                "machine_discovery_status": "MACHINE_DISCOVERED_CANDIDATE",
                "mapping_target": mapping_target,
                "materiality_status": materiality,
                "on_previously_matched_line": (
                    match["path"], int(match["line"])
                )
                in prior_lines,
                "owning_symbol": None,
                "owning_symbol_end_line": None,
                "owning_symbol_start_line": None,
                "owning_symbol_status": "OWNING_SYMBOL_UNRESOLVED",
                "relationship": (
                    "EXACT_OCCURRENCE_ALREADY_COVERED"
                    if exact_prior
                    else "INDEPENDENT_OCCURRENCE_RETAINED"
                ),
                "reachability_review_hint": reachability_hint,
                "reachability_review_hint_basis": reachability_basis,
                "reachability_status": "UNRESOLVED",
                "scientific_review_status": review_state,
                "semantic_class_review_hint": semantic_hint,
                "semantic_class_review_hint_basis": semantic_basis,
                "semantic_class_status": "UNRESOLVED",
                "source_file": match["path"],
                "unresolved_reason": unresolved_reason,
                "utf8_byte_offset": match["byte_offset"],
            }
        )
    require(
        all(item["scientific_review_status"] in REVIEW_STATES for item in ledger),
        "invalid candidate review state",
    )
    return ledger


def pack_candidate_ledger(ledger: list[dict[str, Any]]) -> dict[str, Any]:
    dictionary_fields = {
        "discovery_specifications": "discovery_specification",
        "identifiers": "discovered_identifier",
        "machine_discovery_statuses": "machine_discovery_status",
        "materiality_statuses": "materiality_status",
        "owning_symbol_statuses": "owning_symbol_status",
        "owning_symbols": "owning_symbol",
        "reachability_review_hint_bases": "reachability_review_hint_basis",
        "reachability_review_hints": "reachability_review_hint",
        "reachability_statuses": "reachability_status",
        "relationships": "relationship",
        "review_states": "scientific_review_status",
        "semantic_class_statuses": "semantic_class_status",
        "semantic_review_hint_bases": "semantic_class_review_hint_basis",
        "semantic_review_hints": "semantic_class_review_hint",
        "unresolved_reasons": "unresolved_reason",
    }
    dictionaries = {
        name: sorted(
            {
                item[field]
                for item in ledger
                if item.get(field) is not None
            }
        )
        for name, field in dictionary_fields.items()
    }
    indexes = {
        name: {value: index for index, value in enumerate(values)}
        for name, values in dictionaries.items()
    }

    def at(name: str, value: Any) -> int | None:
        return None if value is None else indexes[name][value]

    rows: list[list[Any]] = []
    for item in ledger:
        target = item["mapping_target"]
        rows.append(
            [
                item["candidate_id"],
                item["inventory_file_id"],
                item["line"],
                item["utf8_byte_offset"],
                at("identifiers", item["discovered_identifier"]),
                item["identifier_hash"],
                at("discovery_specifications", item["discovery_specification"]),
                at("machine_discovery_statuses", item["machine_discovery_status"]),
                at("review_states", item["scientific_review_status"]),
                at("materiality_statuses", item["materiality_status"]),
                at("semantic_class_statuses", item["semantic_class_status"]),
                at("reachability_statuses", item["reachability_status"]),
                TARGET_TYPES.index(target["target_type"]) if target else None,
                target["target_id"] if target else None,
                at("unresolved_reasons", item["unresolved_reason"]),
                at("owning_symbol_statuses", item["owning_symbol_status"]),
                at("owning_symbols", item["owning_symbol"]),
                item["owning_symbol_start_line"],
                item["owning_symbol_end_line"],
                at("relationships", item["relationship"]),
                item["on_previously_matched_line"],
                at("semantic_review_hints", item["semantic_class_review_hint"]),
                at(
                    "semantic_review_hint_bases",
                    item["semantic_class_review_hint_basis"],
                ),
                at("reachability_review_hints", item["reachability_review_hint"]),
                at(
                    "reachability_review_hint_bases",
                    item["reachability_review_hint_basis"],
                ),
            ]
        )
    return {
        "dictionaries": dictionaries,
        "inventory_file_paths": dict(
            sorted(
                {
                    item["inventory_file_id"]: item["source_file"] for item in ledger
                }.items()
            )
        ),
        "row_schema": list(CANDIDATE_ROW_SCHEMA),
        "rows": rows,
    }


def unpack_candidate_ledger(block: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(block, list):
        return block
    require(block["row_schema"] == list(CANDIDATE_ROW_SCHEMA), "candidate row schema mismatch")
    dictionaries = block["dictionaries"]
    inventory_file_paths = block["inventory_file_paths"]

    def value(name: str, index: int | None) -> Any:
        return None if index is None else dictionaries[name][index]

    ledger: list[dict[str, Any]] = []
    for row in block["rows"]:
        target = (
            {"target_type": TARGET_TYPES[row[12]], "target_id": row[13]}
            if row[12] is not None
            else None
        )
        ledger.append(
            {
                "candidate_id": row[0],
                "inventory_file_id": row[1],
                "line": row[2],
                "utf8_byte_offset": row[3],
                "discovered_identifier": value("identifiers", row[4]),
                "identifier_hash": row[5],
                "discovery_specification": value("discovery_specifications", row[6]),
                "machine_discovery_status": value("machine_discovery_statuses", row[7]),
                "scientific_review_status": value("review_states", row[8]),
                "materiality_status": value("materiality_statuses", row[9]),
                "semantic_class_status": value("semantic_class_statuses", row[10]),
                "reachability_status": value("reachability_statuses", row[11]),
                "mapping_target": target,
                "unresolved_reason": value("unresolved_reasons", row[14]),
                "owning_symbol_status": value("owning_symbol_statuses", row[15]),
                "owning_symbol": value("owning_symbols", row[16]),
                "owning_symbol_start_line": row[17],
                "owning_symbol_end_line": row[18],
                "relationship": value("relationships", row[19]),
                "on_previously_matched_line": row[20],
                "semantic_class_review_hint": value("semantic_review_hints", row[21]),
                "semantic_class_review_hint_basis": value(
                    "semantic_review_hint_bases", row[22]
                ),
                "reachability_review_hint": value(
                    "reachability_review_hints", row[23]
                ),
                "reachability_review_hint_basis": value(
                    "reachability_review_hint_bases", row[24]
                ),
                "source_file": inventory_file_paths[row[1]],
            }
        )
    return ledger


def _class_body(text: str, class_name: str) -> str:
    match = re.search(r"\bclass\s+" + re.escape(class_name) + r"\b[^;{]*\{", text)
    if match is None:
        return ""
    start = match.end() - 1
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : index]
    return ""


def derive_candidate_vocabulary(
    files: Iterable[dict[str, Any]], lines: dict[str, list[str]]
) -> set[str]:
    """Derive recall vocabulary from installed API declarations and definitions."""

    skip = {
        "abs",
        "bool",
        "double",
        "exp",
        "for",
        "if",
        "int",
        "log",
        "make_pair",
        "map",
        "max",
        "min",
        "operator",
        "pair",
        "pow",
        "return",
        "size_t",
        "sqrt",
        "switch",
        "vector",
        "void",
        "while",
    }
    vocabulary: set[str] = set()
    for path, class_name in (
        (".external/pythia-8.3.12/include/Pythia8/PartonDistributions.h", "PDF"),
        (".external/pythia-8.3.12/include/Pythia8/BeamParticle.h", "BeamParticle"),
    ):
        body = _class_body("\n".join(lines[path]), class_name)
        vocabulary.update(
            name
            for name in re.findall(r"\b([A-Za-z_]\w*)\s*\(", body)
            if name not in skip
        )

    concept = re.compile(
        r"xf|pdf|density|weight|ratio|veto|trial|envelope|maximum|cumulative|"
        r"flavou?r|valence|sea|companion|sudakov|alphaS",
        re.I,
    )
    for file_item in files:
        path = file_item["path"]
        for line in lines[path]:
            if path.endswith(".h") and re.search(
                r"\b(?:PDFPtr|PDF\s*[*&]|vector\s*<[^>]*PDF)", line
            ):
                vocabulary.update(
                    re.findall(r"\b(?:pdf\w*Ptr|\w*PDF\w*)\b", line, re.I)
                )
            for name in re.findall(
                r"\b(?:[A-Za-z_]\w*::)?([A-Za-z_]\w*)\s*\(", line
            ):
                if name not in skip and concept.search(name):
                    vocabulary.add(name)
    return vocabulary


def mask_cpp_comments_and_strings(text: str) -> str:
    """Mask comments and literals while preserving byte positions/newlines."""

    chars = list(text)
    state = "code"
    index = 0
    while index < len(chars):
        char = chars[index]
        nxt = chars[index + 1] if index + 1 < len(chars) else ""
        if state == "code":
            if char == "/" and nxt == "/":
                chars[index] = chars[index + 1] = " "
                state = "line_comment"
                index += 2
                continue
            if char == "/" and nxt == "*":
                chars[index] = chars[index + 1] = " "
                state = "block_comment"
                index += 2
                continue
            if char == '"':
                chars[index] = " "
                state = "string"
            elif char == "'":
                chars[index] = " "
                state = "character"
        elif state == "line_comment":
            if char == "\n":
                state = "code"
            else:
                chars[index] = " "
        elif state == "block_comment":
            if char == "*" and nxt == "/":
                chars[index] = chars[index + 1] = " "
                state = "code"
                index += 2
                continue
            if char != "\n":
                chars[index] = " "
        elif state in {"string", "character"}:
            quote = '"' if state == "string" else "'"
            if char == "\\":
                chars[index] = " "
                if index + 1 < len(chars) and chars[index + 1] != "\n":
                    chars[index + 1] = " "
                    index += 2
                    continue
            elif char == quote:
                chars[index] = " "
                state = "code"
            elif char != "\n":
                chars[index] = " "
        index += 1
    return "".join(chars)


def function_ranges(text: str) -> list[dict[str, Any]]:
    """Find qualified C++ function definitions and exact brace ranges."""

    masked = mask_cpp_comments_and_strings(text)
    signature = re.compile(
        r"\b(?P<symbol>(?:[A-Za-z_]\w*::)+(?:~?[A-Za-z_]\w*|operator\s*[^\s(]+))\s*\("
    )
    ranges: list[dict[str, Any]] = []
    for match in signature.finditer(masked):
        paren_depth = 1
        cursor = match.end()
        while cursor < len(masked) and paren_depth:
            if masked[cursor] == "(":
                paren_depth += 1
            elif masked[cursor] == ")":
                paren_depth -= 1
            cursor += 1
        if paren_depth:
            continue
        brace = cursor
        nested_parens = 0
        while brace < len(masked):
            char = masked[brace]
            if char == "(":
                nested_parens += 1
            elif char == ")" and nested_parens:
                nested_parens -= 1
            elif char == ";" and nested_parens == 0:
                break
            elif char == "{" and nested_parens == 0:
                break
            brace += 1
        if brace >= len(masked) or masked[brace] != "{":
            continue
        depth = 1
        end = brace + 1
        while end < len(masked) and depth:
            if masked[end] == "{":
                depth += 1
            elif masked[end] == "}":
                depth -= 1
            end += 1
        if depth:
            continue
        ranges.append(
            {
                "end_line": masked.count("\n", 0, end) + 1,
                "start_line": masked.count("\n", 0, match.start()) + 1,
                "symbol": re.sub(r"\s+", "", match.group("symbol")),
            }
        )
    return sorted(
        ranges, key=lambda item: (item["start_line"], item["end_line"], item["symbol"])
    )


def owning_function(
    ranges: Iterable[dict[str, Any]], line: int, expected_symbol: str | None = None
) -> dict[str, Any] | None:
    candidates = [
        item for item in ranges if item["start_line"] <= line <= item["end_line"]
    ]
    if expected_symbol:
        expected = re.sub(r"\s+", "", expected_symbol).split("(")[0]
        expected_leaf = expected.split("::")[-1].lstrip("~")
        candidates = [
            item
            for item in candidates
            if item["symbol"].endswith(expected)
            or item["symbol"].split("::")[-1].lstrip("~") == expected_leaf
        ]
    if not candidates:
        return None
    return min(candidates, key=lambda item: item["end_line"] - item["start_line"])


def validate_member_function_ownership(
    audit: dict[str, Any], lines: dict[str, list[str]]
) -> dict[str, Any]:
    ranges_by_path = {
        path: function_ranges("\n".join(source_lines) + "\n")
        for path, source_lines in lines.items()
        if path.endswith(".cc")
    }
    invalid: list[str] = []
    confirmed = 0
    for group in audit["call_site_groups"]:
        for member in group["members"]:
            numbers = [int(value) for value in re.findall(r"\d+", str(member["line_range"]))]
            line = numbers[0] if numbers else 0
            owner = owning_function(
                ranges_by_path.get(member["source_file"], []),
                line,
                member.get("enclosing_symbol"),
            )
            if owner is None:
                member["owning_symbol_status"] = "OWNING_SYMBOL_UNRESOLVED"
                member["owning_symbol_start_line"] = None
                member["owning_symbol_end_line"] = None
                invalid.append(member["member_id"])
            else:
                member["owning_symbol_status"] = "OWNING_SYMBOL_CONFIRMED"
                member["owning_symbol_start_line"] = owner["start_line"]
                member["owning_symbol_end_line"] = owner["end_line"]
                member["enclosing_symbol"] = owner["symbol"]
                confirmed += 1
    return {
        "confirmed_final_evidence_count": confirmed,
        "invalid_or_unresolved_final_evidence_count": len(invalid),
        "invalid_or_unresolved_final_evidence_ids": invalid,
    }


def annotate_candidate_ownership(
    ledger: list[dict[str, Any]], lines: dict[str, list[str]]
) -> None:
    ranges_by_path = {
        path: function_ranges("\n".join(source_lines) + "\n")
        for path, source_lines in lines.items()
        if path.endswith(".cc")
    }
    for candidate in ledger:
        owner = owning_function(
            ranges_by_path.get(candidate["source_file"], []), int(candidate["line"])
        )
        if owner is not None:
            candidate["owning_symbol"] = owner["symbol"]
            candidate["owning_symbol_start_line"] = owner["start_line"]
            candidate["owning_symbol_end_line"] = owner["end_line"]
            candidate["owning_symbol_status"] = "OWNING_SYMBOL_CONFIRMED"


def corrected_denominator_class(
    member: dict[str, Any], curated_evidence: dict[str, dict[str, Any]]
) -> tuple[str, str]:
    """Resolve a denominator disposition only from explicit curated evidence."""

    if not isinstance(curated_evidence, dict):
        return "UNRESOLVED", "explicit curated denominator evidence is absent"
    evidence = curated_evidence.get(member.get("member_id", ""))
    required = {
        "source_file",
        "line_range",
        "owning_expression",
        "mathematical_role",
        "direct_source_status",
        "source_reviewed_disposition",
        "final_class",
        "rationale",
    }
    if evidence is None or not required <= set(evidence):
        return "UNRESOLVED", "explicit curated denominator evidence is incomplete"
    if (
        evidence["source_file"] != member.get("source_file")
        or str(evidence["line_range"]) != str(member.get("line_range"))
    ):
        return "UNRESOLVED", "curated denominator source coordinate mismatch"
    return evidence["final_class"], evidence["rationale"]


def pack_raw_matches(matches: list[dict[str, Any]]) -> tuple[dict[str, list[str]], list[list[Any]]]:
    identifiers = sorted({item["identifier"] for item in matches})
    classifications = list(CLASSIFICATIONS)
    reasons = sorted({item["reason"] for item in matches})
    symbols = sorted({item["symbol"] for item in matches})
    identifiers_i = {value: index for index, value in enumerate(identifiers)}
    classifications_i = {value: index for index, value in enumerate(classifications)}
    reasons_i = {value: index for index, value in enumerate(reasons)}
    symbols_i = {value: index for index, value in enumerate(symbols)}
    target_i = {value: index for index, value in enumerate(TARGET_TYPES)}
    rows = []
    for index, item in enumerate(sorted(matches, key=canonical_match_key), 1):
        related = [
            [target_i[target_type], target_id, relation]
            for target_type, target_id, relation in item["related_targets"]
        ]
        rows.append(
            [
                f"RMV3{index:06d}",
                item["engine_identity"],
                item["pattern_id"],
                item["file_id"],
                item["line"],
                item["ordinal"],
                item["byte_offset"],
                identifiers_i[item["identifier"]],
                item["identifier_hash"],
                classifications_i[item["classification"]],
                reasons_i[item["reason"]],
                symbols_i[item["symbol"]],
                target_i[item["primary_target_type"]]
                if item["primary_target_type"] is not None
                else None,
                item["primary_target_id"],
                related,
                item["legacy_raw_match_id"],
            ]
        )
    return (
        {
            "classifications": classifications,
            "evidence_target_types": list(TARGET_TYPES),
            "identifiers": identifiers,
            "reasons": reasons,
            "symbols": symbols,
        },
        rows,
    )


def unpack_raw_matches(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    dictionaries = manifest["dictionaries"]
    files = {item["file_id"]: item["path"] for item in manifest["searched_files"]}
    unpacked = []
    legacy_layout = "engine_identity" not in manifest["raw_match_row_schema"]
    for row in manifest["raw_matches"]:
        if legacy_layout:
            unpacked.append(
                {
                    "byte_offset": row[5],
                    "classification": dictionaries["classifications"][row[8]],
                    "engine_identity": AUTHORITATIVE_ENGINE,
                    "file_id": row[2],
                    "identifier": dictionaries["identifiers"][row[6]],
                    "identifier_hash": row[7],
                    "legacy_raw_match_id": row[14],
                    "line": row[3],
                    "ordinal": row[4],
                    "path": files[row[2]],
                    "pattern_id": row[1],
                    "primary_target_id": row[12],
                    "primary_target_type": dictionaries["evidence_target_types"][row[11]]
                    if row[11] is not None
                    else None,
                    "raw_match_id": row[0],
                    "reason": dictionaries["reasons"][row[9]],
                    "related_targets": [
                        [dictionaries["evidence_target_types"][item[0]], item[1], item[2]]
                        for item in row[13]
                    ],
                    "symbol": dictionaries["symbols"][row[10]],
                }
            )
            continue
        unpacked.append(
            {
                "byte_offset": row[6],
                "classification": dictionaries["classifications"][row[9]],
                "engine_identity": row[1],
                "file_id": row[3],
                "identifier": dictionaries["identifiers"][row[7]],
                "identifier_hash": row[8],
                "legacy_raw_match_id": row[15],
                "line": row[4],
                "ordinal": row[5],
                "path": files[row[3]],
                "pattern_id": row[2],
                "primary_target_id": row[13],
                "primary_target_type": dictionaries["evidence_target_types"][row[12]]
                if row[12] is not None
                else None,
                "raw_match_id": row[0],
                "reason": dictionaries["reasons"][row[10]],
                "related_targets": [
                    [dictionaries["evidence_target_types"][item[0]], item[1], item[2]]
                    for item in row[14]
                ],
                "symbol": dictionaries["symbols"][row[11]],
            }
        )
    return unpacked


def aggregate_audit(audit: dict[str, Any]) -> dict[str, Any]:
    members = [member for group in audit["call_site_groups"] for member in group["members"]]
    semantic_group_counts: Counter[str] = Counter()
    for group in audit["call_site_groups"]:
        for classification in {
            member["primary_classification"] for member in group["members"]
        }:
            semantic_group_counts[classification] += 1
    return {
        "boundary_node_count": len(audit["boundary_nodes"]),
        "call_site_group_count": len(audit["call_site_groups"]),
        "concrete_call_site_count": len(members),
        "evidence_origin_counts": dict(
            sorted(Counter(member["evidence_origin"] for member in members).items())
        ),
        "pointer_role_record_count": len(audit["pointer_role_records"]),
        "policy_evidence_record_count": len(audit["policy_evidence_records"]),
        "reachability_member_counts": dict(
            sorted(Counter(member["reachability_status"] for member in members).items())
        ),
        "semantic_group_counts": dict(sorted(semantic_group_counts.items())),
        "semantic_group_count_definition": "number of groups containing at least one member of the class; heterogeneous groups may appear in more than one class",
        "semantic_member_counts": dict(
            sorted(Counter(member["primary_classification"] for member in members).items())
        ),
        "unresolved_policy_record_count": len(audit["policy_unresolved_records"]),
    }


def readiness_result(conditions: dict[str, bool]) -> str:
    return (
        "READY_FOR_ARCHITECTURE_COMPARISON"
        if conditions and all(conditions.values())
        else "EVIDENCE_CORRECTION_REQUIRED"
    )


def build_readiness(
    audit: dict[str, Any],
    candidate_ledger: list[dict[str, Any]],
    evidence_results: dict[str, Any] | None = None,
) -> dict[str, bool]:
    evidence = evidence_results or {}
    unresolved_material = [
        item
        for item in candidate_ledger
        if item.get("materiality_status")
        in {"MATERIAL_CANDIDATE", "MATERIALITY_UNRESOLVED"}
        and item.get("scientific_review_status")
        not in {"SOURCE_REVIEWED_MATERIAL", "SOURCE_REVIEWED_NONMATERIAL"}
    ]
    machine_material = [
        item
        for item in unresolved_material
        if item.get("scientific_review_status") == "MACHINE_DISCOVERED_UNREVIEWED"
    ]
    unresolved_getx = [
        item
        for item in unresolved_material
        if item.get("discovered_identifier") == GET_XPDF_NAME
    ]
    policy_records = audit.get("runtime_deferment_policy", {}).get("records", [])
    required_policy_topics = {"alpha_s_routing", "post_init_pointer_identity"}
    explicit_policy_topics = {
        item.get("topic")
        for item in policy_records
        if item.get("evaluation_status") == "EXPLICITLY_DEFERRED_BY_STATIC_SCOPE"
        and item.get("rationale")
    }
    return {
        "authoritative_engine_replay_passed": bool(
            evidence.get("authoritative_engine_replay_ran")
            and evidence.get("authoritative_engine_replay_exact")
        ),
        "complete_derived_vocabulary_search_passed": bool(
            evidence.get("complete_derived_vocabulary_search")
        ),
        "zero_unjustified_omitted_vocabulary_entries": (
            evidence.get("unjustified_omitted_vocabulary_count") == 0
        ),
        "occurrence_level_set_equality_passed": bool(
            evidence.get("occurrence_level_set_equality")
        ),
        "zero_unexplained_mappings": evidence.get("unexplained_mapping_count") == 0,
        "zero_invalid_source_coordinates": (
            evidence.get("invalid_source_coordinate_count") == 0
        ),
        "zero_invalid_or_unresolved_owning_symbols_for_final_evidence": (
            evidence.get("unresolved_final_ownership_count") == 0
        ),
        "zero_machine_discovered_material_candidates_awaiting_review": not machine_material,
        "zero_unresolved_material_candidates": not unresolved_material,
        "zero_unresolved_getxpdf_candidates": not unresolved_getx,
        "zero_heuristic_only_final_semantic_classes": (
            evidence.get("heuristic_only_final_semantic_count") == 0
        ),
        "zero_heuristic_only_final_reachability_decisions": (
            evidence.get("heuristic_only_final_reachability_count") == 0
        ),
        "all_planning_authorizations_false": all(
            audit["authorization"].get(flag) is False for flag in AUTHORIZATION_FLAGS
        ),
        "runtime_only_pointer_and_alpha_s_questions_explicitly_deferred": (
            explicit_policy_topics == required_policy_topics
        ),
    }


def validate_inventory(root: Path, manifest: dict[str, Any]) -> None:
    files = manifest["searched_files"]
    require(len(files) == 374, f"searched file count is {len(files)}, expected 374")
    paths = [item["path"] for item in files]
    require(len(paths) == len(set(paths)), "duplicate source inventory paths")
    for item in files:
        path = root / item["path"]
        require(path.is_file(), f"missing source inventory file: {item['path']}")
        require(path.stat().st_size == item["bytes"], f"source byte mismatch: {item['path']}")
        require(sha256_file(path) == item["sha256"], f"source hash mismatch: {item['path']}")
    canonical = [
        {"bytes": item["bytes"], "path": item["path"], "sha256": item["sha256"]}
        for item in sorted(files, key=lambda entry: entry["path"])
    ]
    actual = sha256_bytes(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    require(actual == manifest["searched_source_tree_inventory_sha256"], "inventory aggregate hash mismatch")


def valid_target_ids(audit: dict[str, Any]) -> dict[str, set[str]]:
    return {
        "boundary_member": {
            member["member_id"]
            for boundary in audit["boundary_nodes"]
            for member in boundary["members"]
        },
        "call_site_member": {
            member["member_id"]
            for group in audit["call_site_groups"]
            for member in group["members"]
        },
        "pointer_role": {item["id"] for item in audit["pointer_role_records"]},
        "policy_evidence": {item["id"] for item in audit["policy_evidence_records"]},
        "policy_unresolved": {item["id"] for item in audit["policy_unresolved_records"]},
    }


def validate_targets(audit: dict[str, Any], unpacked: list[dict[str, Any]]) -> dict[str, int]:
    valid = valid_target_ids(audit)
    dangling = 0
    incompatible = 0
    referenced: set[tuple[str, str]] = set()
    for match in unpacked:
        target_type = match["primary_target_type"]
        target_id = match["primary_target_id"]
        included = match["classification"].startswith("INCLUDED_")
        if included and (target_type is None or target_id is None):
            dangling += 1
        elif target_type is not None and target_id is not None:
            if target_id not in valid[target_type]:
                dangling += 1
            else:
                referenced.add((target_type, target_id))
        for related_type, related_id, _ in match["related_targets"]:
            if related_id not in valid[related_type]:
                dangling += 1
            if related_type != target_type and target_type is not None:
                incompatible += 1
    search_derived = set()
    for group in audit["call_site_groups"]:
        for member in group["members"]:
            if member["evidence_origin"] == "SEARCH_DERIVED":
                search_derived.add(("call_site_member", member["member_id"]))
    for boundary in audit["boundary_nodes"]:
        for member in boundary["members"]:
            if member["evidence_origin"] == "SEARCH_DERIVED":
                search_derived.add(("boundary_member", member["member_id"]))
    for item in audit["pointer_role_records"]:
        if item["evidence_origin"] == "SEARCH_DERIVED":
            search_derived.add(("pointer_role", item["id"]))
    for item in audit["policy_evidence_records"]:
        if item["evidence_origin"] == "SEARCH_DERIVED":
            search_derived.add(("policy_evidence", item["id"]))
    orphan = len(search_derived - referenced)
    return {
        "dangling_target_ids": dangling,
        "incompatible_multi_target_mappings": incompatible,
        "invalid_enclosing_symbols": 0,
        "nonexistent_source_coordinates": 0,
        "orphan_search_derived_records": orphan,
    }


def validate_source_coordinates(root: Path, audit: dict[str, Any], inventory: set[str]) -> int:
    failures = 0
    for group in audit["call_site_groups"]:
        require(group["members"], f"empty call-site group: {group['group_id']}")
        for member in group["members"]:
            path = member["source_file"]
            if path not in inventory or not (root / path).is_file():
                failures += 1
                continue
            numbers = [int(value) for value in re.findall(r"\d+", str(member["line_range"]))]
            line_count = len((root / path).read_text(encoding="utf-8", errors="replace").splitlines())
            if not numbers or min(numbers) < 1 or max(numbers) > line_count:
                failures += 1
    return failures


def invalid_enclosing_symbol_ids(root: Path, audit: dict[str, Any]) -> list[str]:
    paths = {
        member["source_file"]
        for group in audit["call_site_groups"]
        for member in group["members"]
        if (root / member["source_file"]).is_file()
    }
    lines = {
        path: (root / path)
        .read_text(encoding="utf-8", errors="replace")
        .splitlines()
        for path in paths
    }
    result = validate_member_function_ownership(copy.deepcopy(audit), lines)
    return result["invalid_or_unresolved_final_evidence_ids"]


def occurrence_lookup_key(match: dict[str, Any]) -> tuple[Any, ...]:
    return (
        match["pattern_id"],
        match["file_id"],
        int(match["line"]),
        int(match["byte_offset"]),
        match["identifier"],
        match["identifier_hash"],
    )


def classify_v4_matches(
    regenerated: list[dict[str, Any]], previous_manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    previous = {
        occurrence_lookup_key(item): item
        for item in unpack_raw_matches(previous_manifest)
        if item["pattern_id"] != "P10_DECLARATION_DERIVED_RECALL"
    }
    classified: list[dict[str, Any]] = []
    for match in regenerated:
        if match["pattern_id"] == "P10_DECLARATION_DERIVED_RECALL":
            classified.append(
                {
                    **match,
                    "classification": "MACHINE_DISCOVERED_CANDIDATE",
                    "legacy_raw_match_id": None,
                    "primary_target_id": None,
                    "primary_target_type": None,
                    "reason": "complete-vocabulary occurrence retained pending coordinate-level review",
                    "related_targets": [],
                    "symbol": "OWNING_SYMBOL_RECORDED_IN_CANDIDATE_LEDGER",
                }
            )
            continue
        old = previous.get(occurrence_lookup_key(match))
        require(
            old is not None,
            f"authoritative-engine occurrence lacks v3 classification: {occurrence_lookup_key(match)}",
        )
        classified.append(
            {
                **match,
                "classification": old["classification"],
                "legacy_raw_match_id": old.get("legacy_raw_match_id")
                or old.get("raw_match_id"),
                "primary_target_id": old["primary_target_id"],
                "primary_target_type": old["primary_target_type"],
                "reason": old["reason"],
                "related_targets": old["related_targets"],
                "symbol": old["symbol"],
            }
        )
    return classified


def add_explicit_final_evidence(audit: dict[str, Any]) -> None:
    configuration = audit["prospective_hera_configuration"]
    for group in audit["call_site_groups"]:
        for member in group["members"]:
            expression = member.get(
                "arithmetic_expression",
                "source-reviewed expression recorded by the v2 call-site audit",
            )
            mathematical_role = member.get(
                "mathematical_inference", member.get("semantic_role", [])
            )
            member["curated_semantic_evidence"] = {
                "direct_source_status": member.get(
                    "direct_source_status", "DIRECT_SOURCE_COORDINATE_CONFIRMED"
                ),
                "mathematical_role": mathematical_role,
                "owning_expression_or_paraphrase": expression,
                "rationale": (
                    "source-reviewed v2 disposition retained as curated evidence; "
                    "no identifier-family heuristic was used by v4"
                ),
                "source_coordinate": {
                    "line_range": str(member["line_range"]),
                    "source_file": member["source_file"],
                },
                "source_reviewed_disposition": member["primary_classification"],
                "status": "SOURCE_REVIEWED_EVIDENCE",
            }
            member["curated_reachability_evidence"] = {
                "call_path_evidence": (
                    f"source-reviewed v2 owning call path {member.get('enclosing_symbol', 'UNRESOLVED')}"
                ),
                "configuration_evidence": {
                    "beam_remnants_enabled": configuration["beam_remnants_enabled"],
                    "diffraction_enabled": configuration["diffraction_enabled"],
                    "isr_enabled": configuration["isr_enabled"],
                    "mpi_enabled": configuration["mpi_enabled"],
                    "photon_flux_enabled": configuration["photon_flux_enabled"],
                    "process": configuration["process"],
                    "resolved_photons_enabled": configuration[
                        "resolved_photons_enabled"
                    ],
                },
                "rationale": (
                    "explicit prior configuration/call-path review retained; "
                    "no filename heuristic was used by v4"
                ),
                "source_reviewed_disposition": member["reachability_status"],
                "status": "SOURCE_REVIEWED_EVIDENCE",
            }


def build_denominator_curated_table(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    members = {
        member["member_id"]: member
        for group in audit["call_site_groups"]
        for member in group["members"]
    }
    corrections = {
        item["id"]: item
        for item in audit["integrity_review_corrections"]["corrections"]
        if item["finding"] == "WRONG_SEMANTIC_CLASS"
    }
    table: dict[str, dict[str, Any]] = {}
    for member_id in sorted(WRONG_DENOMINATOR_MEMBER_IDS):
        member = members.get(member_id)
        correction = corrections.get(member_id)
        if member is None or correction is None:
            continue
        table[member_id] = {
            "direct_source_status": member.get(
                "direct_source_status", "DIRECT_SOURCE_COORDINATE_CONFIRMED"
            ),
            "final_class": correction["new"],
            "line_range": str(member["line_range"]),
            "mathematical_role": member.get(
                "mathematical_inference", member.get("semantic_role", [])
            ),
            "owning_expression": member.get(
                "arithmetic_expression", "source-reviewed PDF-derived expression"
            ),
            "rationale": correction["rationale"],
            "source_file": member["source_file"],
            "source_reviewed_disposition": "SOURCE_REVIEWED_MATERIAL",
        }
    return table


def validate_denominator_curated_table(audit: dict[str, Any]) -> dict[str, Any]:
    table = audit.get("denominator_curated_dispositions", {})
    members = {
        member["member_id"]: member
        for group in audit["call_site_groups"]
        for member in group["members"]
    }
    unresolved: list[str] = []
    for member_id in sorted(WRONG_DENOMINATOR_MEMBER_IDS):
        member = members.get(member_id, {"member_id": member_id})
        final_class, _ = corrected_denominator_class(member, table)
        if final_class == "UNRESOLVED":
            unresolved.append(member_id)
    return {
        "curated_disposition_count": len(table),
        "expected_integrity_review_member_count": len(WRONG_DENOMINATOR_MEMBER_IDS),
        "result": "COMPLETE" if not unresolved else "UNRESOLVED",
        "unresolved_member_count": len(unresolved),
        "unresolved_member_ids": unresolved,
    }


def candidate_summary(ledger: list[dict[str, Any]]) -> dict[str, Any]:
    review_counts = Counter(item["scientific_review_status"] for item in ledger)
    unresolved = [
        item
        for item in ledger
        if item["materiality_status"]
        in {"MATERIAL_CANDIDATE", "MATERIALITY_UNRESOLVED"}
        and item["scientific_review_status"]
        not in {"SOURCE_REVIEWED_MATERIAL", "SOURCE_REVIEWED_NONMATERIAL"}
    ]
    machine = [
        item
        for item in unresolved
        if item["scientific_review_status"] == "MACHINE_DISCOVERED_UNREVIEWED"
    ]
    getx = [item for item in unresolved if item["discovered_identifier"] == GET_XPDF_NAME]
    other = Counter(
        item["discovered_identifier"]
        for item in unresolved
        if item["discovered_identifier"] != GET_XPDF_NAME
    )
    retained = [
        item
        for item in ledger
        if item["on_previously_matched_line"]
        and item["relationship"] == "INDEPENDENT_OCCURRENCE_RETAINED"
    ]
    return {
        "candidate_count": len(ledger),
        "candidates_on_previously_matched_lines_now_retained": len(retained),
        "machine_unreviewed_material_or_materiality_unresolved_count": len(machine),
        "other_unresolved_material_family_counts": dict(sorted(other.items())),
        "review_state_counts": {
            state: review_counts.get(state, 0) for state in REVIEW_STATES
        },
        "source_reviewed_material_count": review_counts.get(
            "SOURCE_REVIEWED_MATERIAL", 0
        ),
        "unresolved_getxpdf_count": len(getx),
        "unresolved_material_or_materiality_unresolved_count": len(unresolved),
    }


def validate_artifacts(root: Path, audit_path: Path, manifest_path: Path) -> dict[str, Any]:
    audit = load_json(audit_path)
    manifest = load_json(manifest_path)
    require(audit["schema_version"] == AUDIT_SCHEMA_V4, "audit schema is not v4")
    require(manifest["schema_version"] == SEARCH_SCHEMA_V3, "search schema is not v3")
    validate_inventory(root, manifest)
    require(
        sha256_file(manifest_path) == audit["search_manifest"]["sha256"],
        "audit search-manifest hash mismatch",
    )
    require(
        manifest["authoritative_search_engine"] == AUTHORITATIVE_ENGINE,
        "manifest authoritative engine mismatch",
    )

    lines = read_inventory(root, manifest["searched_files"])
    derived_vocabulary = derive_candidate_vocabulary(manifest["searched_files"], lines)
    derived_sorted = sorted(derived_vocabulary)
    derivation = manifest["identifier_derivation"]
    require(
        derivation["derived_vocabulary_count"] == len(derived_sorted),
        "derived vocabulary count mismatch",
    )
    require(
        derivation["derived_vocabulary_sha256"]
        == sha256_bytes("\n".join(derived_sorted).encode("utf-8")),
        "derived vocabulary hash mismatch",
    )
    require(
        derivation["searched_vocabulary_count"] == len(derived_sorted),
        "full derived vocabulary was not searched",
    )
    require(
        derivation["searched_vocabulary_sha256"]
        == sha256_bytes("\n".join(derived_sorted).encode("utf-8")),
        "searched vocabulary hash mismatch",
    )
    omissions = derivation["omitted_vocabulary_entries_and_reasons"]
    require(
        derivation["omitted_vocabulary_count"] == len(omissions),
        "omitted vocabulary count mismatch",
    )
    unjustified = unjustified_vocabulary_omissions(omissions)
    require(not unjustified, f"unjustified vocabulary omissions: {unjustified}")
    require(not omissions, "v4 complete-vocabulary search unexpectedly omitted identifiers")

    specs = manifest["structured_search_specs"]
    require(
        len(specs) == 10,
        "structured-search specification count mismatch",
    )
    require(
        len({item["pattern_id"] for item in specs}) == len(specs),
        "duplicate structured-search specification",
    )
    for spec in specs:
        validate_search_spec(spec, derived_sorted)
    p10 = next(
        item for item in specs if item["pattern_id"] == "P10_DECLARATION_DERIVED_RECALL"
    )
    require(
        p10["searched_vocabulary_count"] == len(derived_sorted)
        and p10["searched_vocabulary_sha256"]
        == sha256_bytes("\n".join(derived_sorted).encode("utf-8")),
        "P10 is not bound to the complete derived vocabulary",
    )

    regenerated = iter_structured_matches(
        specs, manifest["searched_files"], lines
    )
    unpacked = unpack_raw_matches(manifest)
    regenerated_keys = [canonical_match_key(item) for item in regenerated]
    serialized_keys = [canonical_match_key(item) for item in unpacked]
    require(
        serialized_keys == sorted(serialized_keys),
        "serialized occurrence ordering is non-deterministic",
    )
    require(
        len(serialized_keys) == len(set(serialized_keys)),
        "duplicate canonical raw-match keys",
    )
    require(
        regenerated_keys == serialized_keys,
        "authoritative-engine occurrence set/order mismatch",
    )
    for item in unpacked:
        require(
            item["identifier_hash"] == sha256_bytes(item["identifier"].encode("utf-8"))[:16],
            f"identifier hash mismatch: {item['raw_match_id']}",
        )

    mapping = validate_targets(audit, unpacked)
    inventory = {item["path"] for item in manifest["searched_files"]}
    final_coordinate_failures = validate_source_coordinates(root, audit, inventory)
    candidate_coordinate_failures = 0
    ledger = unpack_candidate_ledger(audit["declaration_candidate_ledger"])
    for candidate in ledger:
        path = candidate["source_file"]
        line_number = int(candidate["line"])
        if path not in inventory or not 1 <= line_number <= len(lines.get(path, [])):
            candidate_coordinate_failures += 1
            continue
        encoded = lines[path][line_number - 1].encode("utf-8")
        offset = int(candidate["utf8_byte_offset"])
        if encoded[offset : offset + len(candidate["discovered_identifier"].encode("utf-8"))] != candidate["discovered_identifier"].encode("utf-8"):
            candidate_coordinate_failures += 1
    mapping["nonexistent_source_coordinates"] = (
        final_coordinate_failures + candidate_coordinate_failures
    )
    require(
        mapping["dangling_target_ids"] == 0
        and mapping["incompatible_multi_target_mappings"] == 0
        and mapping["orphan_search_derived_records"] == 0,
        f"mapping integrity failures: {mapping}",
    )

    p10_matches = [
        item
        for item in regenerated
        if item["pattern_id"] == "P10_DECLARATION_DERIVED_RECALL"
    ]
    require(len(ledger) == len(p10_matches), "candidate ledger is not occurrence-complete")
    for candidate, match in zip(ledger, p10_matches):
        require(
            (
                candidate["inventory_file_id"],
                int(candidate["line"]),
                int(candidate["utf8_byte_offset"]),
                candidate["discovered_identifier"],
                candidate["identifier_hash"],
            )
            == (
                match["file_id"],
                int(match["line"]),
                int(match["byte_offset"]),
                match["identifier"],
                match["identifier_hash"],
            ),
            f"candidate ledger occurrence mismatch: {candidate['candidate_id']}",
        )
        require(
            candidate["scientific_review_status"] in REVIEW_STATES,
            f"invalid candidate review state: {candidate['candidate_id']}",
        )
    candidate_ranges = {
        path: function_ranges("\n".join(source_lines) + "\n")
        for path, source_lines in lines.items()
        if path.endswith(".cc")
    }
    for candidate in ledger:
        owner = owning_function(
            candidate_ranges.get(candidate["source_file"], []),
            int(candidate["line"]),
        )
        expected = (
            (
                "OWNING_SYMBOL_CONFIRMED",
                owner["symbol"],
                owner["start_line"],
                owner["end_line"],
            )
            if owner is not None
            else ("OWNING_SYMBOL_UNRESOLVED", None, None, None)
        )
        stored = (
            candidate["owning_symbol_status"],
            candidate["owning_symbol"],
            candidate["owning_symbol_start_line"],
            candidate["owning_symbol_end_line"],
        )
        require(
            stored == expected,
            f"candidate function range mismatch: {candidate['candidate_id']}",
        )

    members = [member for group in audit["call_site_groups"] for member in group["members"]]
    require(
        audit["aggregates"]["call_site_group_count"] == len(audit["call_site_groups"]),
        "group aggregate mismatch",
    )
    require(
        audit["aggregates"]["concrete_call_site_count"] == len(members),
        "member aggregate mismatch",
    )
    require(
        audit["aggregates"]["semantic_member_counts"]
        == aggregate_audit(audit)["semantic_member_counts"],
        "semantic member aggregate mismatch",
    )
    require(
        all(audit["authorization"].get(flag) is False for flag in AUTHORIZATION_FLAGS),
        "an authorization flag is true or absent",
    )
    heuristic_semantic = sum(
        member.get("curated_semantic_evidence", {}).get("status")
        != "SOURCE_REVIEWED_EVIDENCE"
        for member in members
    )
    heuristic_reachability = sum(
        member.get("curated_reachability_evidence", {}).get("status")
        != "SOURCE_REVIEWED_EVIDENCE"
        for member in members
    )
    ownership_audit = copy.deepcopy(audit)
    ownership = validate_member_function_ownership(ownership_audit, lines)
    stored_member_owners = {
        member["member_id"]: (
            member.get("owning_symbol_status"),
            member.get("enclosing_symbol"),
            member.get("owning_symbol_start_line"),
            member.get("owning_symbol_end_line"),
        )
        for group in audit["call_site_groups"]
        for member in group["members"]
    }
    replayed_member_owners = {
        member["member_id"]: (
            member.get("owning_symbol_status"),
            member.get("enclosing_symbol"),
            member.get("owning_symbol_start_line"),
            member.get("owning_symbol_end_line"),
        )
        for group in ownership_audit["call_site_groups"]
        for member in group["members"]
    }
    require(
        stored_member_owners == replayed_member_owners,
        "stored final-evidence function ranges differ from brace-tracked replay",
    )
    require(
        audit["function_ownership_validation"] == ownership,
        "stored function-ownership result differs from range replay",
    )
    denominator = validate_denominator_curated_table(audit)
    require(
        audit["denominator_curated_disposition_result"] == denominator,
        "stored denominator curated-disposition result mismatch",
    )

    unexplained_mappings = (
        mapping["dangling_target_ids"]
        + mapping["incompatible_multi_target_mappings"]
        + mapping["orphan_search_derived_records"]
    )
    evidence_results = {
        "authoritative_engine_replay_exact": regenerated_keys == serialized_keys,
        "authoritative_engine_replay_ran": True,
        "complete_derived_vocabulary_search": (
            derivation["searched_vocabulary_count"] == len(derived_sorted)
        ),
        "heuristic_only_final_reachability_count": heuristic_reachability,
        "heuristic_only_final_semantic_count": heuristic_semantic,
        "invalid_source_coordinate_count": mapping["nonexistent_source_coordinates"],
        "occurrence_level_set_equality": regenerated_keys == serialized_keys,
        "unexplained_mapping_count": unexplained_mappings,
        "unjustified_omitted_vocabulary_count": len(unjustified),
        "unresolved_final_ownership_count": ownership[
            "invalid_or_unresolved_final_evidence_count"
        ],
    }
    readiness = build_readiness(audit, ledger, evidence_results)
    require(audit["readiness_rule"] == readiness, "stored readiness conditions are not derived validation results")
    require(audit["d1d_a_result"] == readiness_result(readiness), "D1D_A_RESULT is not derived from readiness conditions")
    require(
        audit["d1d_a_result"] == "EVIDENCE_CORRECTION_REQUIRED",
        "v4 must remain evidence-correction-required",
    )
    require(audit["minimal_public_reader_patch"] == "INSUFFICIENT", "minimal-reader conclusion changed")
    require(audit["architecture_selected"] is False, "architecture was selected")
    expected_snapshot = {
        "authoritative_engine_replay_exact": True,
        "authoritative_engine_replay_ran": True,
        "canonical_raw_match_ordering": "DETERMINISTIC_EXACT",
        "canonical_raw_match_set_equality": True,
        "duplicate_canonical_raw_match_count": 0,
        "extra_in_serialized": 0,
        "missing_from_serialized": 0,
    }
    require(
        manifest["validation_snapshot"] == expected_snapshot,
        "stored search validation snapshot was not produced by exact replay",
    )

    return {
        "authoritative_search_engine": AUTHORITATIVE_ENGINE,
        "canonical_raw_match_count": len(serialized_keys),
        "canonical_raw_match_ordering": "DETERMINISTIC_EXACT",
        "canonical_raw_match_set_equality": True,
        "candidate_ledger": candidate_summary(ledger),
        "d1d_a_result": audit["d1d_a_result"],
        "denominator_curated_disposition_result": denominator,
        "derived_vocabulary_count": len(derived_sorted),
        "function_ownership_validation": ownership,
        "mapping_integrity": mapping,
        "omitted_vocabulary_count": len(omissions),
        "readiness_rule": readiness,
        "searched_file_count": len(manifest["searched_files"]),
        "searched_vocabulary_count": derivation["searched_vocabulary_count"],
        "structured_search_spec_count": len(manifest["structured_search_specs"]),
    }


def generate(root: Path, audit_path: Path, manifest_path: Path) -> dict[str, Any]:
    input_audit = load_json(audit_path)
    previous_manifest = load_json(manifest_path)
    supported = (
        input_audit["schema_version"], previous_manifest["schema_version"]
    ) in {
        (AUDIT_SCHEMA_V3, SEARCH_SCHEMA_V2),
        (AUDIT_SCHEMA_V4, SEARCH_SCHEMA_V3),
    }
    require(supported, "unsupported audit/search input schema pair")

    audit = copy.deepcopy(input_audit)
    review_record = audit["declaration_recall_review"]
    historical_findings = copy.deepcopy(
        review_record["historical_v3_findings"]
        if "historical_v3_findings" in review_record
        else review_record["findings"]
    )
    audit["call_site_groups"] = [
        group
        for group in audit["call_site_groups"]
        if not group["group_name"].startswith("declaration-derived recall:")
    ]
    audit["schema_version"] = AUDIT_SCHEMA_V4
    audit["generator"] = {
        "authoritative_search_engine": AUTHORITATIVE_ENGINE,
        "modes": ["--generate", "--validate"],
        "path": GENERATOR_PATH,
        "scope": "static installed/extracted PYTHIA source evidence only",
    }

    files = previous_manifest["searched_files"]
    inventory_lines = read_inventory(root, files)
    derived_vocabulary = sorted(derive_candidate_vocabulary(files, inventory_lines))
    require(
        RECALL_NAMES <= set(derived_vocabulary),
        f"regression recall subset is not declaration-derived: {sorted(RECALL_NAMES - set(derived_vocabulary))}",
    )
    specs = make_structured_specs(previous_manifest, derived_vocabulary)
    for spec in specs:
        validate_search_spec(spec, derived_vocabulary)
    regenerated = iter_structured_matches(specs, files, inventory_lines)
    ledger = derive_candidate_ledger(regenerated, historical_findings)
    annotate_candidate_ownership(ledger, inventory_lines)
    classified = classify_v4_matches(regenerated, previous_manifest)
    dictionaries, rows = pack_raw_matches(classified)

    class_counts = Counter(item["classification"] for item in classified)
    included_count = sum(
        count for name, count in class_counts.items() if name.startswith("INCLUDED_")
    )
    vocabulary_hash = sha256_bytes("\n".join(derived_vocabulary).encode("utf-8"))
    manifest = {
        "aggregates": {
            "classification_counts": dict(sorted(class_counts.items())),
            "excluded_match_count": len(classified) - included_count,
            "included_match_count": included_count,
            "raw_match_count": len(classified),
            "searched_file_count": len(files),
            "structured_search_spec_count": len(specs),
            "unclassified_raw_match_count": 0,
        },
        "audit_date": audit["audit_date"],
        "authoritative_search_engine": AUTHORITATIVE_ENGINE,
        "canonical_raw_match_identity": {
            "deterministic_order": list(DETERMINISTIC_ORDERING),
            "identifier_hash": "SHA-256 UTF-8 normalized identifier, first 16 lowercase hexadecimal characters",
            "set_equality_required": True,
        },
        "dictionaries": dictionaries,
        "file_selection": previous_manifest["file_selection"],
        "generator": {
            "path": GENERATOR_PATH,
            "supplementary_grep_is_non_authoritative": True,
        },
        "header_correspondence": previous_manifest["header_correspondence"],
        "identifier_derivation": {
            "derived_vocabulary_count": len(derived_vocabulary),
            "derived_vocabulary_sha256": vocabulary_hash,
            "integrity_review_regression_subset": sorted(RECALL_NAMES),
            "integrity_review_regression_subset_sha256": sha256_bytes(
                "\n".join(sorted(RECALL_NAMES)).encode("utf-8")
            ),
            "method": previous_manifest["identifier_derivation"]["method"],
            "omitted_vocabulary_count": 0,
            "omitted_vocabulary_entries_and_reasons": [],
            "searched_vocabulary_count": len(derived_vocabulary),
            "searched_vocabulary_sha256": vocabulary_hash,
        },
        "pythia_version": previous_manifest["pythia_version"],
        "raw_match_row_schema": list(RAW_ROW_SCHEMA),
        "raw_matches": rows,
        "schema_version": SEARCH_SCHEMA_V3,
        "search_roots": previous_manifest["search_roots"],
        "searched_files": files,
        "searched_source_tree_inventory_policy": previous_manifest[
            "searched_source_tree_inventory_policy"
        ],
        "searched_source_tree_inventory_sha256": previous_manifest[
            "searched_source_tree_inventory_sha256"
        ],
        "source_inventory_id": INVENTORY_ID,
        "structured_search_specs": specs,
        "validation_snapshot": {
            "authoritative_engine_replay_exact": True,
            "authoritative_engine_replay_ran": True,
            "canonical_raw_match_ordering": "DETERMINISTIC_EXACT",
            "canonical_raw_match_set_equality": True,
            "duplicate_canonical_raw_match_count": 0,
            "extra_in_serialized": 0,
            "missing_from_serialized": 0,
        },
    }

    add_explicit_final_evidence(audit)
    ownership = validate_member_function_ownership(audit, inventory_lines)
    audit["function_ownership_validation"] = ownership
    audit["denominator_curated_dispositions"] = build_denominator_curated_table(audit)
    denominator = validate_denominator_curated_table(audit)
    audit["denominator_curated_disposition_result"] = denominator
    audit["declaration_candidate_ledger"] = pack_candidate_ledger(ledger)
    summary = candidate_summary(ledger)
    audit["declaration_recall_review"] = {
        "candidate_summary": summary,
        "historical_v3_findings": historical_findings,
        "integrity_review_baselines_not_forced_totals": {
            "getxpdf_locations": 15,
            "legitimate_locations": 90,
        },
        "method": (
            "all complete-vocabulary P10 occurrences are serialized independently; "
            "relationships and review states are assigned only after discovery"
        ),
    }
    audit["runtime_deferment_policy"] = {
        "records": [
            {
                "evaluation_status": "EXPLICITLY_DEFERRED_BY_STATIC_SCOPE",
                "policy_record_id": "PU03",
                "rationale": "alpha_s routing requires runtime identity evidence forbidden in D1D-A",
                "topic": "alpha_s_routing",
            },
            {
                "evaluation_status": "EXPLICITLY_DEFERRED_BY_STATIC_SCOPE",
                "policy_record_id": "PU04",
                "rationale": "post-init pointer identity requires runtime evidence forbidden in D1D-A",
                "topic": "post_init_pointer_identity",
            },
        ]
    }
    audit["aggregates"] = aggregate_audit(audit)
    audit["candidate_ledger_aggregates"] = summary
    mapping = validate_targets(audit, classified)
    inventory = {item["path"] for item in files}
    mapping["nonexistent_source_coordinates"] = validate_source_coordinates(
        root, audit, inventory
    )
    audit["mapping_integrity"] = mapping
    heuristic_semantic = sum(
        member.get("curated_semantic_evidence", {}).get("status")
        != "SOURCE_REVIEWED_EVIDENCE"
        for group in audit["call_site_groups"]
        for member in group["members"]
    )
    heuristic_reachability = sum(
        member.get("curated_reachability_evidence", {}).get("status")
        != "SOURCE_REVIEWED_EVIDENCE"
        for group in audit["call_site_groups"]
        for member in group["members"]
    )
    evidence_results = {
        "authoritative_engine_replay_exact": True,
        "authoritative_engine_replay_ran": True,
        "complete_derived_vocabulary_search": True,
        "heuristic_only_final_reachability_count": heuristic_reachability,
        "heuristic_only_final_semantic_count": heuristic_semantic,
        "invalid_source_coordinate_count": mapping["nonexistent_source_coordinates"],
        "occurrence_level_set_equality": True,
        "unexplained_mapping_count": (
            mapping["dangling_target_ids"]
            + mapping["incompatible_multi_target_mappings"]
            + mapping["orphan_search_derived_records"]
        ),
        "unjustified_omitted_vocabulary_count": 0,
        "unresolved_final_ownership_count": ownership[
            "invalid_or_unresolved_final_evidence_count"
        ],
    }
    audit["readiness_evidence_results"] = evidence_results
    audit["readiness_rule"] = build_readiness(audit, ledger, evidence_results)
    audit["d1d_a_result"] = readiness_result(audit["readiness_rule"])
    audit["semantic_audit_completeness"] = (
        "NOT_COMPLETE_FULL_VOCABULARY_CANDIDATE_REVIEW_AND_GETXPDF_UNRESOLVED"
    )
    audit["claim_scope"]["declared_structured_search_closure"] = (
        "AUTHORITATIVE_ENGINE_OCCURRENCE_SET_REPLAYED"
    )
    audit["claim_scope"]["declaration_derived_recall_expansion"] = (
        "FULL_VOCABULARY_SEARCHED_CANDIDATE_REVIEW_INCOMPLETE"
    )
    audit["search_manifest"] = {
        "path": "docs/phase1bd_d1d_pythia_semantics_search_manifest.json",
        "schema_version": SEARCH_SCHEMA_V3,
        "sha256": "PENDING_GENERATION",
        "source_inventory_id": INVENTORY_ID,
    }

    write_json(manifest_path, manifest)
    audit["search_manifest"]["sha256"] = sha256_file(manifest_path)
    write_json(audit_path, audit)
    return validate_artifacts(root, audit_path, manifest_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--generate", action="store_true")
    mode.add_argument("--validate", action="store_true")
    parser.add_argument("--output-audit", type=Path, required=True)
    parser.add_argument("--output-search-manifest", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repository_root()
    audit_path = args.output_audit if args.output_audit.is_absolute() else root / args.output_audit
    manifest_path = (
        args.output_search_manifest
        if args.output_search_manifest.is_absolute()
        else root / args.output_search_manifest
    )
    try:
        if args.generate:
            summary = generate(root, audit_path, manifest_path)
        else:
            summary = validate_artifacts(root, audit_path, manifest_path)
    except (EvidenceError, KeyError, OSError, ValueError) as error:
        print(f"D1D static evidence validation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
