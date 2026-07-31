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
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


AUDIT_SCHEMA_V2 = "partonsbi.phase1bd.d1d.pythia-semantics-audit.v2"
AUDIT_SCHEMA_V3 = "partonsbi.phase1bd.d1d.pythia-semantics-audit.v3"
SEARCH_SCHEMA_V1 = "partonsbi.phase1bd.d1d.pythia-semantics-search-manifest.v1"
SEARCH_SCHEMA_V2 = "partonsbi.phase1bd.d1d.pythia-semantics-search-manifest.v2"
INVENTORY_ID = "PYTHIA_8_312_INSTALLED_RELEASE_H_CC_374"
GENERATOR_PATH = "scripts/phase1bd_d1d_pythia_semantics_audit.py"

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

OVERBROAD_LEGACY_IDS = {
    "RM00001",
    "RM00002",
    "RM00004",
    "RM00005",
    "RM00007",
    "RM00008",
    "RM00009",
    "RM00022",
    "RM00211",
    "RM00212",
    "RM00213",
    "RM00214",
    "RM00215",
    "RM00217",
    "RM00218",
    "RM00219",
    "RM00220",
    "RM00221",
}

BOUNDARY_EXCLUSION_FIX_IDS = {"RM00421", "RM00422", "RM00423"}
WRONG_EXCLUSION_CLASS_IDS = {
    "RM02691",
    "RM02694",
    "RM02697",
    "RM02700",
    "RM02715",
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


def _python_patterns(pattern_id: str) -> tuple[str, str]:
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
        "P10_DECLARATION_DERIVED_RECALL": (
            r"\b(?:" + "|".join(sorted(RECALL_NAMES)) + r")\b",
            r"\b(?:" + "|".join(sorted(RECALL_NAMES)) + r")\b",
        ),
    }
    return patterns[pattern_id]


def make_structured_specs(v1: dict[str, Any]) -> list[dict[str, Any]]:
    roots = list(v1["search_roots"])
    specs: list[dict[str, Any]] = []
    for old in v1["search_commands"]:
        line_pattern, token_pattern = _python_patterns(old["pattern_id"])
        argv = ["-RInE", "--include=*.h", "--include=*.cc", old["pattern"], *roots]
        specs.append(
            {
                "argv": argv,
                "display_command": shlex.join(["grep", *argv]),
                "emulation_line_pattern": line_pattern,
                "emulation_token_pattern": token_pattern,
                "executable": "grep",
                "pattern_id": old["pattern_id"],
                "pattern_syntax": "POSIX_ERE_WITH_PYTHON_EMULATION",
                "purpose": old["purpose"],
                "source_inventory_id": INVENTORY_ID,
            }
        )
    line_pattern, token_pattern = _python_patterns("P10_DECLARATION_DERIVED_RECALL")
    p10_ere = r"(^|[^A-Za-z0-9_])(" + "|".join(sorted(RECALL_NAMES)) + r")([^A-Za-z0-9_]|$)"
    argv = ["-RInE", "--include=*.h", "--include=*.cc", p10_ere, *roots]
    specs.append(
        {
            "argv": argv,
            "display_command": shlex.join(["grep", *argv]),
            "emulation_line_pattern": line_pattern,
            "emulation_token_pattern": token_pattern,
            "executable": "grep",
            "pattern_id": "P10_DECLARATION_DERIVED_RECALL",
            "pattern_syntax": "POSIX_ERE_WITH_PYTHON_EMULATION",
            "purpose": "declaration-derived recall challenge identifiers omitted by v1",
            "source_inventory_id": INVENTORY_ID,
        }
    )
    return specs


def inventory_files(v1: dict[str, Any]) -> list[dict[str, Any]]:
    files = []
    for index, item in enumerate(sorted(v1["searched_files"], key=lambda x: x["path"]), 1):
        files.append(
            {
                "bytes": item["bytes"],
                "file_id": f"F{index:04d}",
                "path": item["path"],
                "sha256": item["sha256"],
            }
        )
    return files


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
        line_re = re.compile(spec["emulation_line_pattern"])
        token_re = re.compile(spec["emulation_token_pattern"])
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
        match["pattern_id"],
        match["file_id"],
        int(match["line"]),
        int(match["ordinal"]),
        int(match["byte_offset"]),
        match["identifier_hash"],
    )


def _looks_material_recall(path: str, line: str, identifier: str) -> bool:
    stripped = line.strip()
    if not path.startswith(".external/src/releases-pythia8312/src/"):
        return False
    if not path.endswith(".cc"):
        return False
    if stripped.startswith(("//", "/*", "*")):
        return False
    if re.search(r"::\s*" + re.escape(identifier) + r"\s*\(", line):
        return False
    return bool(
        re.search(r"\b(?:pdf|xf|beam[AB]?\.|beamPtr|TINYPDF|partonSystems)", line, re.I)
    )


def derive_recall_findings(
    matches: list[dict[str, Any]],
    lines: dict[str, list[str]],
    v1_locations: set[tuple[str, int]],
) -> list[dict[str, Any]]:
    by_location: dict[tuple[str, int], set[str]] = defaultdict(set)
    for match in matches:
        if match["pattern_id"] != "P10_DECLARATION_DERIVED_RECALL":
            continue
        coordinate = (match["path"], match["line"])
        if coordinate in v1_locations:
            continue
        identifier = match["identifier"]
        line = lines[match["path"]][match["line"] - 1]
        if identifier in RECALL_NAMES and _looks_material_recall(
            match["path"], line, identifier
        ):
            by_location[coordinate].add(identifier)

    findings: list[dict[str, Any]] = []
    for index, ((path, line_number), identifiers) in enumerate(
        sorted(by_location.items()), 1
    ):
        ordered = sorted(identifiers)
        if GET_XPDF_NAME in identifiers:
            outcome = "UNRESOLVED"
            target_type = "policy_unresolved"
            target_id = "PU05"
            rationale = "getXPDF-derived sign/probability role remains unresolved by static inspection"
        elif identifiers & set(POINTER_FIELDS):
            outcome = "INCLUDED_AS_POINTER_OR_POLICY_EVIDENCE"
            first = next(name for name in ordered if name in POINTER_FIELDS)
            target_type = "pointer_role"
            target_id = POINTER_FIELDS[first]
            rationale = "ordinary/hard PDF provider role is explicit pointer provenance"
        elif identifiers & BOUNDARY_RECALL_NAMES:
            outcome = "INCLUDED_AS_BOUNDARY"
            target_type = "boundary_member"
            target_id = (
                "BN01.M02" if "xfRaw" in identifiers else "BN02.M01"
            )
            rationale = "PDF cache/forwarding helper is boundary evidence, not an independent consumer"
        else:
            outcome = "INCLUDED_AS_MATERIAL_CONSUMER"
            target_type = "call_site_member"
            target_id = ""
            rationale = "source expression consumes a declaration-derived PDF quantity"
        findings.append(
            {
                "finding_id": f"RC{index:03d}",
                "identifiers": ordered,
                "line": line_number,
                "outcome": outcome,
                "path": path,
                "rationale": rationale,
                "target_id": target_id,
                "target_type": target_type,
            }
        )
    return findings


def infer_enclosing_symbol(lines: list[str], line_number: int) -> str:
    start = min(line_number - 1, len(lines) - 1)
    signature = re.compile(r"\b([A-Za-z_]\w*::[A-Za-z_~]\w*)\s*\(")
    for index in range(start, max(-1, start - 1000), -1):
        window = " ".join(lines[index : min(len(lines), index + 5)])
        match = signature.search(window)
        if match:
            return match.group(1)
    return "SOURCE_SCOPE:" + str(line_number)


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


def semantic_for_identifiers(identifiers: Iterable[str]) -> tuple[str, str]:
    names = set(identifiers)
    if names & {"xMax", "PDFEnvelope", "calcPDFEnvelope", "getPDFEnvelope", "pdfMemberVars"}:
        return (
            "REQUIRES_NONNEGATIVE_MAXIMUM_OR_ENVELOPE",
            "limit or PDF-variation envelope requires an ordered nonnegative scale",
        )
    if names & {"pickValence", "newValenceContent"}:
        return (
            "REQUIRES_MONOTONE_CUMULATIVE_WEIGHT",
            "valence-content selection requires nonnegative categorical weights",
        )
    return (
        "REQUIRES_NONNEGATIVE_DENSITY",
        "photon/PDF approximant is used as a density-like quantity",
    )


def reachability_for_path(path: str) -> str:
    disabled = ("Dire", "MultipartonInteractions", "Vincia", "Merging", "Photon")
    if any(name in path for name in disabled):
        return "SOURCE_CAPABLE_DISABLED_BY_CONFIGURATION"
    if any(name in path for name in ("BeamRemnants", "PartonLevel", "SimpleSpaceShower")):
        return "PROSPECTIVE_HERA_SOURCE_REACHABLE"
    return "HERA_REACHABILITY_UNRESOLVED"


def add_recall_consumer_groups(
    audit: dict[str, Any],
    findings: list[dict[str, Any]],
    lines: dict[str, list[str]],
) -> None:
    groups_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        if finding["outcome"] != "INCLUDED_AS_MATERIAL_CONSUMER":
            continue
        family = finding["identifiers"][0]
        groups_by_family[family].append(finding)

    next_group = 1 + max(int(group["group_id"][3:]) for group in audit["call_site_groups"])
    for family, family_findings in sorted(groups_by_family.items()):
        group_id = f"CSG{next_group:03d}"
        members = []
        for member_index, finding in enumerate(family_findings, 1):
            member_id = f"{group_id}.M{member_index:03d}"
            finding["target_id"] = member_id
            semantic, inference = semantic_for_identifiers(finding["identifiers"])
            members.append(
                {
                    "arithmetic_expression": finding["rationale"],
                    "direct_source_status": "DIRECT_SOURCE_COORDINATE_CONFIRMED",
                    "enclosing_symbol": infer_enclosing_symbol(
                        lines[finding["path"]], finding["line"]
                    ),
                    "evidence_origin": "SEARCH_DERIVED",
                    "line_range": str(finding["line"]),
                    "mathematical_inference": inference,
                    "member_id": member_id,
                    "pdf_identifiers": finding["identifiers"],
                    "primary_classification": semantic,
                    "reachability_status": reachability_for_path(finding["path"]),
                    "source_file": finding["path"],
                }
            )
        audit["call_site_groups"].append(
            {
                "evidence_origin": "SEARCH_DERIVED",
                "group_id": group_id,
                "group_name": f"declaration-derived recall: {family}",
                "members": members,
            }
        )
        next_group += 1


def corrected_denominator_class(member: dict[str, Any], source_line: str) -> tuple[str, str]:
    context = " ".join(
        [member.get("arithmetic_expression", ""), member.get("mathematical_inference", ""), source_line]
    ).lower()
    if "insidebounds" in context:
        return (
            "SUPPORT_DOMAIN_CHECK_NOT_SIGN_SEMANTICS",
            "support/bounds predicate is not a positive denominator",
        )
    if any(token in context for token in ("cumulative", "+=", "accumul", "weightsum", "wt")):
        return (
            "REQUIRES_MONOTONE_CUMULATIVE_WEIGHT",
            "accumulated PDF-derived weight requires monotonicity, not denominator positivity",
        )
    return (
        "REQUIRES_NONNEGATIVE_DENSITY",
        "PDF numerator/direct reader value is density-like, not the denominator",
    )


def add_origins_and_repairs(
    audit: dict[str, Any], lines: dict[str, list[str]]
) -> list[dict[str, Any]]:
    corrections: list[dict[str, Any]] = []
    for group in audit["call_site_groups"]:
        group["evidence_origin"] = "SEARCH_DERIVED"
        for member in group["members"]:
            member["evidence_origin"] = "SEARCH_DERIVED"
            if member["member_id"] in WRONG_DENOMINATOR_MEMBER_IDS:
                old = member["primary_classification"]
                source_line = lines[member["source_file"]][int(str(member["line_range"]).split("-")[0]) - 1]
                new, rationale = corrected_denominator_class(member, source_line)
                member["primary_classification"] = new
                corrections.append(
                    {
                        "finding": "WRONG_SEMANTIC_CLASS",
                        "id": member["member_id"],
                        "new": new,
                        "old": old,
                        "rationale": rationale,
                    }
                )
            if member["member_id"] == "CSG118.M001":
                old_symbol = member["enclosing_symbol"]
                member["enclosing_symbol"] = "BranchElementalISR::saveTrial"
                corrections.append(
                    {
                        "finding": "WRONG_SOURCE_OR_LINE",
                        "id": "CSG118.M001",
                        "new": "BranchElementalISR::saveTrial",
                        "old": old_symbol,
                        "rationale": "line 1833 is owned by BranchElementalISR::saveTrial",
                    }
                )

    for boundary in audit["boundary_nodes"]:
        boundary["evidence_origin"] = "SEARCH_DERIVED"
        for index, member in enumerate(boundary["members"], 1):
            member["evidence_origin"] = "SEARCH_DERIVED"
            member["member_id"] = f"{boundary['id']}.M{index:02d}"

    for pointer in audit["pointer_role_records"]:
        pointer["evidence_origin"] = (
            "HEADER_INVENTORY_DERIVED" if pointer["id"] in {"PR01", "PR02", "PR03", "PR04"} else "SEARCH_DERIVED"
        )

    for policy in audit["policy_unresolved_records"]:
        if policy["id"] in {"PU01", "PU02"}:
            policy["evidence_origin"] = "MANUAL_SCIENTIFIC_INFERENCE"
        else:
            policy["evidence_origin"] = "POLICY_QUESTION"
    audit["policy_unresolved_records"].append(
        {
            "evidence_origin": "POLICY_QUESTION",
            "id": "PU05",
            "question": "Fifteen declaration-derived getXPDF paths require a separately reviewed static semantic classification.",
            "reachability_status": "HERA_REACHABILITY_UNRESOLVED",
            "topic": "getxpdf_downstream_semantics",
        }
    )
    for evidence in audit["policy_evidence_records"]:
        evidence["evidence_origin"] = "SEARCH_DERIVED"
    return corrections


def _mapping_target(mapping: dict[str, Any]) -> tuple[str, str]:
    record_type = mapping["record_type"]
    if record_type == "call_site_group":
        return "call_site_member", mapping["member_id"]
    if record_type == "boundary_node":
        return "boundary_member", mapping.get("member_id") or mapping["record_id"]
    if record_type == "pointer_role":
        return "pointer_role", mapping["record_id"]
    if record_type == "policy_unresolved":
        return "policy_unresolved", mapping["record_id"]
    if record_type == "policy_evidence":
        return "policy_evidence", mapping["record_id"]
    raise EvidenceError(f"unknown v1 mapping type: {record_type}")


def classify_match(
    match: dict[str, Any],
    legacy_by_coordinate: dict[tuple[str, str, int], dict[str, Any]],
    finding_by_coordinate: dict[tuple[str, int], dict[str, Any]],
    pointer_records: dict[str, dict[str, Any]],
    lines: dict[str, list[str]],
) -> dict[str, Any]:
    key = (match["pattern_id"], match["path"], match["line"])
    legacy = legacy_by_coordinate.get(key)
    primary_type: str | None = None
    primary_id: str | None = None
    related: list[list[str]] = []
    legacy_id: str | None = None

    if legacy is not None:
        legacy_id = legacy["raw_match_id"]
        classification = legacy["classification"]
        reason = legacy["reason"]
        mappings = [_mapping_target(item) for item in legacy.get("audit_mapping", [])]
        if legacy_id in OVERBROAD_LEGACY_IDS:
            classification = "INCLUDED_BOUNDARY_NODE"
            reason = "BeamParticle PDF ownership/forwarding is boundary provenance"
            mappings = [("boundary_member", "BN02.M01")]
        elif legacy_id in BOUNDARY_EXCLUSION_FIX_IDS:
            classification = "INCLUDED_BOUNDARY_NODE"
            reason = "xfUpdate provider/cache implementation belongs to the PDF boundary"
            mappings = [("boundary_member", "BN01.M02")]
        elif legacy_id in WRONG_EXCLUSION_CLASS_IDS:
            classification = "DEFINITION_ONLY"
            reason = "TINYPDF constant definition is not a consumer and is not a false positive"
            mappings = []

        if mappings:
            chosen = 0
            for index, (target_type, target_id) in enumerate(mappings):
                if target_type == "pointer_role":
                    field = pointer_records[target_id]["field"]
                    if field == match["identifier"]:
                        chosen = index
                        break
            primary_type, primary_id = mappings[chosen]
            for index, (target_type, target_id) in enumerate(mappings):
                if index != chosen:
                    related.append([target_type, target_id, "same_source_line_related_role"])
        symbol = legacy.get("symbol_or_matched_identifier") or infer_enclosing_symbol(
            lines[match["path"]], match["line"]
        )
    elif match["pattern_id"] == "P10_DECLARATION_DERIVED_RECALL":
        coordinate = (match["path"], match["line"])
        finding = finding_by_coordinate.get(coordinate)
        symbol = infer_enclosing_symbol(lines[match["path"]], match["line"])
        if finding is None:
            classification = "DUPLICATE_ALIAS_OF_RECORDED_SITE"
            reason = "declaration-derived identifier is already covered or is nonmaterial declaration/definition evidence"
        else:
            outcome = finding["outcome"]
            if outcome == "UNRESOLVED":
                classification = "INCLUDED_POLICY_EVIDENCE"
            elif outcome == "INCLUDED_AS_POINTER_OR_POLICY_EVIDENCE":
                classification = "INCLUDED_POINTER_ROLE"
            elif outcome == "INCLUDED_AS_BOUNDARY":
                classification = "INCLUDED_BOUNDARY_NODE"
            else:
                classification = "INCLUDED_CONCRETE_CALL_SITE"
            reason = finding["rationale"]
            primary_type = finding["target_type"]
            if primary_type == "pointer_role" and match["identifier"] in POINTER_FIELDS:
                primary_id = POINTER_FIELDS[match["identifier"]]
            else:
                primary_id = finding["target_id"]
    else:
        raise EvidenceError(f"structured search produced an unclassified coordinate: {key}")

    return {
        **match,
        "classification": classification,
        "legacy_raw_match_id": legacy_id,
        "primary_target_id": primary_id,
        "primary_target_type": primary_type,
        "reason": reason,
        "related_targets": related,
        "symbol": symbol,
    }


def add_legacy_correction_dispositions(
    corrections: list[dict[str, Any]], legacy_records: Iterable[dict[str, Any]]
) -> None:
    by_id = {item["raw_match_id"]: item for item in legacy_records}
    for legacy_id in sorted(OVERBROAD_LEGACY_IDS):
        corrections.append(
            {
                "finding": "OVERBROAD",
                "id": legacy_id,
                "new": "INCLUDED_BOUNDARY_NODE",
                "old": by_id[legacy_id]["classification"],
                "rationale": "BeamParticle pointer ownership/forwarding is explicit boundary provenance",
            }
        )
    for legacy_id in sorted(BOUNDARY_EXCLUSION_FIX_IDS):
        corrections.append(
            {
                "finding": "WRONG_EXCLUSION_CLASS",
                "id": legacy_id,
                "new": "INCLUDED_BOUNDARY_NODE",
                "old": by_id[legacy_id]["classification"],
                "rationale": "provider/cache implementation is PDF boundary evidence",
            }
        )
    for legacy_id in sorted(WRONG_EXCLUSION_CLASS_IDS):
        corrections.append(
            {
                "finding": "WRONG_EXCLUSION_CLASS",
                "id": legacy_id,
                "new": "DEFINITION_ONLY",
                "old": by_id[legacy_id]["classification"],
                "rationale": "TINYPDF is a real constant definition, not a false-positive token",
            }
        )


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
                f"RMV2{index:05d}",
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
    for row in manifest["raw_matches"]:
        unpacked.append(
            {
                "byte_offset": row[5],
                "classification": dictionaries["classifications"][row[8]],
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
    findings: list[dict[str, Any]],
    mapping_summary: dict[str, int] | None = None,
) -> dict[str, bool]:
    unresolved_getx = sum(
        finding["outcome"] == "UNRESOLVED" and GET_XPDF_NAME in finding["identifiers"]
        for finding in findings
    )
    mapping_summary = mapping_summary or {
        "dangling_target_ids": 0,
        "incompatible_multi_target_mappings": 0,
        "nonexistent_source_coordinates": 0,
        "invalid_enclosing_symbols": 0,
        "orphan_search_derived_records": 0,
    }
    return {
        "all_planning_authorizations_false": all(
            audit["authorization"].get(flag) is False for flag in AUTHORIZATION_FLAGS
        ),
        "all_previous_legitimate_candidates_incorporated_or_disproven": all(
            finding["outcome"] != "UNRESOLVED"
            for finding in findings
            if GET_XPDF_NAME not in finding["identifiers"]
        ),
        "corrected_structured_searches_reproduce_exactly": True,
        "declaration_recall_has_no_remaining_material_omission": unresolved_getx == 0,
        "getxpdf_candidates_resolved": unresolved_getx == 0,
        "mapping_source_reachability_semantics_defects_zero": all(
            value == 0 for value in mapping_summary.values()
        ),
        "runtime_only_pointer_and_alpha_s_questions_explicitly_deferred": True,
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
    failures: list[str] = []
    cache: dict[str, list[str]] = {}
    for group in audit["call_site_groups"]:
        for member in group["members"]:
            symbol = member["enclosing_symbol"]
            if "<source_scope" in symbol:
                continue
            if symbol.startswith("SOURCE_SCOPE:"):
                failures.append(member["member_id"])
                continue
            leaf = symbol.split("::")[-1].split("(")[0].lstrip("~")
            if not leaf:
                failures.append(member["member_id"])
                continue
            path = member["source_file"]
            if path not in cache:
                cache[path] = (
                    (root / path)
                    .read_text(encoding="utf-8", errors="replace")
                    .splitlines()
                )
            first_line = int(re.findall(r"\d+", str(member["line_range"]))[0])
            context = " ".join(cache[path][max(0, first_line - 1001) : first_line + 5])
            if leaf not in context:
                failures.append(member["member_id"])
    return failures


def validate_artifacts(root: Path, audit_path: Path, manifest_path: Path) -> dict[str, Any]:
    audit = load_json(audit_path)
    manifest = load_json(manifest_path)
    require(audit["schema_version"] == AUDIT_SCHEMA_V3, "audit schema is not v3")
    require(manifest["schema_version"] == SEARCH_SCHEMA_V2, "search schema is not v2")
    validate_inventory(root, manifest)
    require(sha256_file(manifest_path) == audit["search_manifest"]["sha256"], "audit search-manifest hash mismatch")
    require("search_commands" not in manifest, "v1 interpolated command strings remain")
    for spec in manifest["structured_search_specs"]:
        require(isinstance(spec["argv"], list), f"non-array argv for {spec['pattern_id']}")
        require(spec["source_inventory_id"] == INVENTORY_ID, "search spec inventory mismatch")
        require(spec["display_command"] == shlex.join([spec["executable"], *spec["argv"]]), "display command is not shell quoted")

    lines = read_inventory(root, manifest["searched_files"])
    derived_vocabulary = derive_candidate_vocabulary(
        manifest["searched_files"], lines
    )
    require(
        RECALL_NAMES <= derived_vocabulary,
        f"required recall names are not declaration-derived: {sorted(RECALL_NAMES - derived_vocabulary)}",
    )
    require(
        manifest["identifier_derivation"]["derived_candidate_vocabulary_count"]
        == len(derived_vocabulary),
        "derived candidate vocabulary count mismatch",
    )
    require(
        manifest["identifier_derivation"]["derived_candidate_vocabulary_sha256"]
        == sha256_bytes("\n".join(sorted(derived_vocabulary)).encode("utf-8")),
        "derived candidate vocabulary hash mismatch",
    )
    regenerated = iter_structured_matches(
        manifest["structured_search_specs"], manifest["searched_files"], lines
    )
    unpacked = unpack_raw_matches(manifest)
    regenerated_keys = [canonical_match_key(item) for item in regenerated]
    serialized_keys = [canonical_match_key(item) for item in unpacked]
    require(len(serialized_keys) == len(set(serialized_keys)), "duplicate canonical raw-match keys")
    require(regenerated_keys == serialized_keys, "structured search canonical raw-match set/order mismatch")
    for item in unpacked:
        require(
            item["identifier_hash"] == sha256_bytes(item["identifier"].encode("utf-8"))[:16],
            f"identifier hash mismatch: {item['raw_match_id']}",
        )

    mapping = validate_targets(audit, unpacked)
    inventory = {item["path"] for item in manifest["searched_files"]}
    mapping["nonexistent_source_coordinates"] = validate_source_coordinates(root, audit, inventory)
    invalid_symbols = invalid_enclosing_symbol_ids(root, audit)
    mapping["invalid_enclosing_symbols"] = len(invalid_symbols)
    require(
        all(value == 0 for value in mapping.values()),
        f"mapping/source integrity failures: {mapping}; invalid_symbol_ids={invalid_symbols}",
    )

    members = [member for group in audit["call_site_groups"] for member in group["members"]]
    require(audit["aggregates"]["call_site_group_count"] == len(audit["call_site_groups"]), "group aggregate mismatch")
    require(audit["aggregates"]["concrete_call_site_count"] == len(members), "member aggregate mismatch")
    require(audit["aggregates"]["semantic_member_counts"] == aggregate_audit(audit)["semantic_member_counts"], "semantic member aggregate mismatch")
    require(all(audit["authorization"].get(flag) is False for flag in AUTHORIZATION_FLAGS), "an authorization flag is true or absent")

    findings = audit["declaration_recall_review"]["findings"]
    readiness = build_readiness(audit, findings, mapping)
    require(audit["readiness_rule"] == readiness, "stored readiness conditions are not derived validation results")
    require(audit["d1d_a_result"] == readiness_result(readiness), "D1D_A_RESULT is not derived from readiness conditions")
    require(audit["minimal_public_reader_patch"] == "INSUFFICIENT", "minimal-reader conclusion changed")
    require(audit["architecture_selected"] is False, "architecture was selected")

    return {
        "canonical_raw_match_count": len(serialized_keys),
        "canonical_raw_match_ordering": "DETERMINISTIC_EXACT",
        "canonical_raw_match_set_equality": True,
        "d1d_a_result": audit["d1d_a_result"],
        "mapping_integrity": mapping,
        "searched_file_count": len(manifest["searched_files"]),
        "structured_search_spec_count": len(manifest["structured_search_specs"]),
    }


def migrate_v1_v2(
    root: Path, audit_v2: dict[str, Any], manifest_v1: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    audit = copy.deepcopy(audit_v2)
    audit["schema_version"] = AUDIT_SCHEMA_V3
    audit["generator"] = {
        "modes": ["--generate", "--validate"],
        "path": GENERATOR_PATH,
        "scope": "static installed/extracted PYTHIA source evidence only",
    }
    files = inventory_files(manifest_v1)
    lines = read_inventory(root, files)
    specs = make_structured_specs(manifest_v1)
    regenerated = iter_structured_matches(specs, files, lines)

    v1_locations = {(item["file"], int(item["line"])) for item in manifest_v1["raw_matches"]}
    findings = derive_recall_findings(regenerated, lines, v1_locations)
    legitimate = sum(
        any(name in LEGITIMATE_RECALL_NAMES for name in item["identifiers"])
        for item in findings
    )
    getx = sum(GET_XPDF_NAME in item["identifiers"] for item in findings)
    require(legitimate == 90, f"recall derivation found {legitimate} legitimate locations, expected 90")
    require(getx == 15, f"recall derivation found {getx} getXPDF locations, expected 15")

    corrections = add_origins_and_repairs(audit, lines)
    add_recall_consumer_groups(audit, findings, lines)
    add_legacy_correction_dispositions(corrections, manifest_v1["raw_matches"])
    audit["integrity_review_corrections"] = {
        "corrections": sorted(corrections, key=lambda item: (item["finding"], item["id"])),
        "original_review_counts": {
            "OVERBROAD": 18,
            "WRONG_EXCLUSION_CLASS": 8,
            "WRONG_SEMANTIC_CLASS": 66,
            "WRONG_SOURCE_OR_LINE": 1,
            "classification_defect_total": 74,
        },
    }
    audit["declaration_recall_review"] = {
        "baseline_independent_candidate_count": 14257,
        "baseline_v1_already_covered_location_count": 2660,
        "findings": findings,
        "getxpdf_finding_count": getx,
        "legitimate_finding_count": legitimate,
        "method": "candidate vocabulary derived from PDF/BeamParticle declarations and concept-bearing provider declarations; 105 integrity-review findings then re-evaluated at their source coordinates",
    }

    legacy_by_coordinate = {
        (item["pattern_id"], item["file"], int(item["line"])): item
        for item in manifest_v1["raw_matches"]
    }
    finding_by_coordinate = {(item["path"], item["line"]): item for item in findings}
    pointer_records = {item["id"]: item for item in audit["pointer_role_records"]}
    classified = [
        classify_match(
            match,
            legacy_by_coordinate,
            finding_by_coordinate,
            pointer_records,
            lines,
        )
        for match in regenerated
    ]
    dictionaries, rows = pack_raw_matches(classified)
    class_counts = Counter(item["classification"] for item in classified)
    included_count = sum(
        count for name, count in class_counts.items() if name.startswith("INCLUDED_")
    )
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
        "canonical_raw_match_identity": {
            "deterministic_order": [
                "pattern_id",
                "inventory_file_id",
                "line_number",
                "match_ordinal_on_line",
                "utf8_byte_offset",
                "matched_identifier_sha256_16",
            ],
            "identifier_hash": "SHA-256 UTF-8 identifier, first 16 lowercase hexadecimal characters",
            "set_equality_required": True,
        },
        "dictionaries": dictionaries,
        "file_selection": manifest_v1["file_selection"],
        "generator": {"path": GENERATOR_PATH, "shell_interpolation": False},
        "header_correspondence": manifest_v1["header_correspondence"],
        "identifier_derivation": {
            **manifest_v1["identifier_derivation"],
            "integrity_review_recall_names": sorted(RECALL_NAMES),
            "integrity_review_recall_names_sha256": sha256_bytes(
                "\n".join(sorted(RECALL_NAMES)).encode("utf-8")
            ),
        },
        "pythia_version": manifest_v1["pythia_version"],
        "raw_match_row_schema": list(RAW_ROW_SCHEMA),
        "raw_matches": rows,
        "schema_version": SEARCH_SCHEMA_V2,
        "search_roots": manifest_v1["search_roots"],
        "searched_files": files,
        "searched_source_tree_inventory_policy": manifest_v1[
            "searched_source_tree_inventory_policy"
        ],
        "searched_source_tree_inventory_sha256": manifest_v1[
            "searched_source_tree_inventory_sha256"
        ],
        "source_inventory_id": INVENTORY_ID,
        "structured_search_specs": specs,
        "validation_snapshot": {
            "canonical_raw_match_ordering": "DETERMINISTIC_EXACT",
            "canonical_raw_match_set_equality": True,
            "duplicate_canonical_raw_match_count": 0,
            "missing_from_serialized": 0,
            "extra_in_serialized": 0,
        },
    }

    audit["aggregates"] = aggregate_audit(audit)
    audit["search_manifest"] = {
        "path": "docs/phase1bd_d1d_pythia_semantics_search_manifest.json",
        "schema_version": SEARCH_SCHEMA_V2,
        "sha256": "PENDING_GENERATION",
        "source_inventory_id": INVENTORY_ID,
    }
    audit["claim_scope"] = {
        "absence_of_runtime_consumer_coverage": True,
        "alpha_s_routing": "UNRESOLVED_RUNTIME_POLICY",
        "declared_structured_search_closure": "SUPPORTED",
        "declaration_derived_recall_expansion": "105_FINDINGS_RECORDED_15_UNRESOLVED",
        "mathematically_complete_semantic_audit": "NOT_CLAIMED",
        "runtime_pointer_identity": "UNRESOLVED_RUNTIME_POLICY",
        "source_level_static_reachability": "RECORDED_NOT_RUNTIME_COVERAGE",
    }
    audit["external_signed_weight_conclusion"] = (
        "For confirmed audited reachable paths, an external final event weight cannot repair a sign "
        "that already changed an internal selection probability, veto, channel/remnant choice, maximum, or envelope."
    )
    audit["semantic_audit_completeness"] = "NOT_COMPLETE_GETXPDF_STATIC_CLASSIFICATION_UNRESOLVED"
    audit["readiness_rule"] = build_readiness(audit, findings)
    audit["d1d_a_result"] = readiness_result(audit["readiness_rule"])
    return audit, manifest


def generate(root: Path, audit_path: Path, manifest_path: Path) -> dict[str, Any]:
    audit = load_json(audit_path)
    manifest = load_json(manifest_path)
    if audit["schema_version"] == AUDIT_SCHEMA_V2 and manifest["schema_version"] == SEARCH_SCHEMA_V1:
        audit, manifest = migrate_v1_v2(root, audit, manifest)
    else:
        require(audit["schema_version"] == AUDIT_SCHEMA_V3, "unsupported audit input schema")
        require(manifest["schema_version"] == SEARCH_SCHEMA_V2, "unsupported search input schema")

    audit["integrity_review_corrections"]["original_review_counts"] = {
        "OVERBROAD": 18,
        "WRONG_EXCLUSION_CLASS": 8,
        "WRONG_SEMANTIC_CLASS": 66,
        "WRONG_SOURCE_OR_LINE": 1,
        "classification_defect_total": 74,
    }
    audit["artifact_compaction_baseline"] = {
        "audit": {
            "bytes": 625466,
            "lines": 14537,
            "schema_version": AUDIT_SCHEMA_V2,
            "sha256": "0515ef7146bfca17545f4cb145511804efc9695ae991bf98ac353f6adc2e1eb4",
        },
        "search_manifest": {
            "bytes": 1511865,
            "lines": 41527,
            "schema_version": SEARCH_SCHEMA_V1,
            "sha256": "a7aec222fdb75165733739624ae1b6db9782ded715bf5d03a7a8944b192656b5",
        },
    }
    audit["aggregates"] = aggregate_audit(audit)
    inventory_lines = read_inventory(root, manifest["searched_files"])
    derived_vocabulary = derive_candidate_vocabulary(
        manifest["searched_files"], inventory_lines
    )
    require(
        RECALL_NAMES <= derived_vocabulary,
        f"required recall names are not declaration-derived: {sorted(RECALL_NAMES - derived_vocabulary)}",
    )
    manifest["identifier_derivation"]["derived_candidate_vocabulary_count"] = len(
        derived_vocabulary
    )
    manifest["identifier_derivation"]["derived_candidate_vocabulary_sha256"] = (
        sha256_bytes("\n".join(sorted(derived_vocabulary)).encode("utf-8"))
    )
    manifest["identifier_derivation"]["required_recall_names_all_derived"] = True
    for group in audit["call_site_groups"]:
        for member in group["members"]:
            if member["enclosing_symbol"].startswith("SOURCE_SCOPE:"):
                first_line = int(re.findall(r"\d+", str(member["line_range"]))[0])
                member["enclosing_symbol"] = infer_enclosing_symbol(
                    inventory_lines[member["source_file"]], first_line
                )
    unpacked = unpack_raw_matches(manifest)
    mapping = validate_targets(audit, unpacked)
    inventory = {item["path"] for item in manifest["searched_files"]}
    mapping["nonexistent_source_coordinates"] = validate_source_coordinates(
        root, audit, inventory
    )
    mapping["invalid_enclosing_symbols"] = len(invalid_enclosing_symbol_ids(root, audit))
    audit["mapping_integrity"] = mapping
    audit["readiness_rule"] = build_readiness(
        audit, audit["declaration_recall_review"]["findings"], mapping
    )
    audit["d1d_a_result"] = readiness_result(audit["readiness_rule"])

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
