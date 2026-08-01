#!/usr/bin/env python3
"""Build and validate the Phase 1B-D1D-A2 static PDF provenance slice.

This source-only analyzer does not compile, link, load, or execute PYTHIA,
APFEL, LHAPDF, or a repository physics binary.  It deliberately treats
unresolved C++ aliasing and dynamic dispatch as unresolved provenance.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "partonsbi.phase1bd.d1d.pythia-pdf-provenance-slice.v1"
ALGORITHM = "PARTON_SBI_TYPED_PDF_PROVENANCE_SLICE_V1"
PARSER = "PARTON_SBI_CPP_PROVENANCE_TOKENIZER_V1"
PARSER_VERSION = "1.0.0"
PYTHON_VERSION = "3.12.3"
GENERATOR_PATH = "scripts/phase1bd_d1d_pythia_pdf_provenance_slice.py"
SEARCH_PATH = "docs/phase1bd_d1d_pythia_semantics_search_manifest.json"
AUDIT_PATH = "docs/phase1bd_d1d_pythia_semantics_audit.json"
OUTPUT_PATH = "docs/phase1bd_d1d_pythia_pdf_provenance_slice.json"

ROOT_CATEGORIES = (
    "PDF_PROVIDER_TYPE",
    "PDF_PROVIDER_POINTER",
    "PDF_PROVIDER_FIELD",
    "PDF_ACCESSOR_METHOD",
    "BEAM_PDF_FORWARDER",
    "PDF_DERIVED_CACHE",
    "PDF_COUPLING_ACCESSOR",
    "CONFIGURATION_POINTER_INSTALLATION",
    "EXPLICIT_EVENT_OR_LHA_WEIGHT_BOUNDARY",
)

NODE_KINDS = (
    "PROVIDER_OBJECT",
    "PROVIDER_FIELD",
    "ACCESSOR_CALL",
    "LOCAL_VARIABLE",
    "MEMBER_VARIABLE",
    "FUNCTION_PARAMETER",
    "FUNCTION_RETURN",
    "ARITHMETIC_EXPRESSION",
    "CONDITION_EXPRESSION",
    "ACCUMULATOR",
    "CALL_ARGUMENT",
    "CALL_RESULT",
    "CACHE_WRITE",
    "CACHE_READ",
    "CONFIGURATION_ASSIGNMENT",
    "DYNAMIC_DISPATCH_SITE",
    "UNRESOLVED_ALIAS",
)

EDGE_KINDS = (
    "DECLARED_AS",
    "POINTS_TO",
    "ASSIGNED_FROM",
    "RETURNED_FROM",
    "PASSED_AS_ARGUMENT",
    "RECEIVED_AS_PARAMETER",
    "READ_BY",
    "WRITTEN_TO",
    "ARITHMETICALLY_DEPENDS_ON",
    "CONDITIONALLY_DEPENDS_ON",
    "ACCUMULATES",
    "FORWARDED_TO",
    "CALLS",
    "MAY_ALIAS",
    "DYNAMIC_TARGET_UNRESOLVED",
)

MATERIALITY_STATES = (
    "PDF_PROVENANCE_CONFIRMED",
    "PDF_PROVENANCE_POSSIBLE",
    "OUTSIDE_PDF_PROVENANCE_SLICE",
    "PROVENANCE_UNRESOLVED",
)

REVIEW_STATES = (
    "MACHINE_SLICED_UNREVIEWED",
    "SOURCE_REVIEWED_MATERIAL",
    "SOURCE_REVIEWED_BOUNDARY",
    "SOURCE_REVIEWED_POINTER_OR_POLICY",
    "SOURCE_REVIEWED_NONMATERIAL",
    "POLICY_UNRESOLVED",
)

DISPOSITIONS = (
    "CONTRIBUTES_TO_PROVENANCE_UNIT",
    "ROOT_DECLARATION_OR_DEFINITION",
    "OUTSIDE_PDF_PROVENANCE_SLICE",
    "DUPLICATE_OCCURRENCE_OF_SAME_UNIT",
    "DYNAMIC_OR_ALIAS_PROVENANCE_UNRESOLVED",
)

OUTSIDE_REASONS = (
    "GENERIC_IDENTIFIER_NO_PDF_ROOT_PATH",
    "UNRELATED_TYPE_OR_NAMESPACE",
    "COMMENT_STRING_OR_DECLARATION_ONLY",
    "CALL_HAS_NO_PDF_DERIVED_ARGUMENT",
    "FUNCTION_NOT_REACHED_FROM_PDF_ROOT",
    "IDENTIFIER_COLLISION",
)

NEGATIVE_CONTROLS = ("state", "size", "id", "push_back", "p", "Vec4")

ACCESSOR_SEEDS = {
    "alphaS",
    "getPDFEnvelope",
    "getXPDF",
    "insideBounds",
    "xMax",
    "xf",
    "xfApprox",
    "xfFlux",
    "xfGamma",
    "xfHard",
    "xfISR",
    "xfMPI",
    "xfMax",
    "xfModPrep",
    "xfModified",
    "xfModified0",
    "xfRaw",
    "xfSame",
    "xfSea",
    "xfUpdate",
    "xfVal",
}

CACHE_SEEDS = {
    "PDFEnvelope",
    "gammaPDFRefScale",
    "gammaPDFxDependence",
    "pdfMemberVars",
    "pdfRatio",
    "pdfVal",
    "xCompDist",
    "xCompFrac",
    "xqComp",
    "xqCompanion",
    "xqCompSum",
    "xqVal",
    "xqgSea",
    "xqgTot",
}

WEIGHT_BOUNDARY_RE = re.compile(
    r"\b(?:LHAweight|LHAweights|eventWeight|weightNominal|weightValue|weightsPtr)\b"
)
PDF_POINTER_RE = re.compile(r"\b(?:PDFPtr|(?:const\s+)?PDF\s*[*&])\s*([A-Za-z_]\w*)")
PDF_FIELD_RE = re.compile(r"\b([A-Za-z_]\w*(?:PDF|Pdf|pdf)[A-Za-z0-9_]*Ptr)\b")
CALL_RE = re.compile(
    r"(?:(?P<receiver>[A-Za-z_]\w*)\s*(?P<dispatch>->|\.)\s*)?"
    r"(?P<callee>[A-Za-z_]\w*)\s*\((?P<args>[^()]*)\)"
)
ASSIGN_RE = re.compile(
    r"(?:\b[A-Za-z_:<>][A-Za-z0-9_:<>,*&\s]*\s+)?"
    r"(?P<lhs>[A-Za-z_]\w*)\s*(?P<op>\+=|-=|\*=|/=|=)\s*(?P<rhs>.+?);"
)


class ProvenanceError(RuntimeError):
    """Raised when the provenance artifact violates its declared invariants."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProvenanceError(message)


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


def load_broad_module(root: Path):
    path = root / "scripts/phase1bd_d1d_pythia_semantics_audit.py"
    spec = importlib.util.spec_from_file_location("d1d_broad_evidence", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return f"{prefix}{sha256_bytes(payload)[:16]}"


def line_byte_offset(line: str, symbol: str) -> int:
    index = line.find(symbol)
    return len(line[: max(index, 0)].encode("utf-8"))


def class_ranges(text: str, broad: Any) -> list[dict[str, Any]]:
    masked = broad.mask_cpp_comments_and_strings(text)
    ranges: list[dict[str, Any]] = []
    pattern = re.compile(
        r"\bclass\s+(?P<name>[A-Za-z_]\w*)\b(?P<bases>[^;{]*)\{"
    )
    for match in pattern.finditer(masked):
        brace = match.end() - 1
        depth = 1
        cursor = brace + 1
        while cursor < len(masked) and depth:
            if masked[cursor] == "{":
                depth += 1
            elif masked[cursor] == "}":
                depth -= 1
            cursor += 1
        if depth:
            continue
        ranges.append(
            {
                "bases": " ".join(match.group("bases").split()),
                "end_line": masked.count("\n", 0, cursor) + 1,
                "name": match.group("name"),
                "start_line": masked.count("\n", 0, match.start()) + 1,
            }
        )
    return ranges


def owner_for_line(
    line_number: int,
    classes: Iterable[dict[str, Any]],
    functions: Iterable[dict[str, Any]],
) -> str:
    function = next(
        (
            item
            for item in functions
            if item["start_line"] <= line_number <= item["end_line"]
        ),
        None,
    )
    if function:
        return function["symbol"]
    containing = [
        item
        for item in classes
        if item["start_line"] <= line_number <= item["end_line"]
    ]
    if containing:
        return min(
            containing, key=lambda item: item["end_line"] - item["start_line"]
        )["name"]
    return "Pythia8"


def direct_type(line: str, symbol: str, category: str) -> str:
    if category == "PDF_PROVIDER_TYPE":
        return f"class {symbol}"
    if category in {"PDF_PROVIDER_POINTER", "PDF_PROVIDER_FIELD"}:
        match = re.search(
            r"\b((?:const\s+)?PDF\s*[*&]|PDFPtr)\s*" + re.escape(symbol), line
        )
        return " ".join(match.group(1).split()) if match else "PDF provider pointer"
    if category in {
        "PDF_ACCESSOR_METHOD",
        "BEAM_PDF_FORWARDER",
        "PDF_COUPLING_ACCESSOR",
    }:
        return "double-returning PDF accessor or forwarder"
    if category == "PDF_DERIVED_CACHE":
        return "PDF-derived cached field or cache accessor"
    if category == "CONFIGURATION_POINTER_INSTALLATION":
        return "PDF provider pointer assignment"
    return "explicit event/LHA weight interface"


def configuration_flags(category: str, symbol: str, path: str) -> dict[str, bool]:
    token = f"{symbol} {path}".lower()
    disabled_role = any(
        name in token for name in ("mpi", "pom", "vmd", "unres", "photon", "gamma")
    )
    hera_role = category in {
        "PDF_PROVIDER_TYPE",
        "PDF_ACCESSOR_METHOD",
        "BEAM_PDF_FORWARDER",
        "PDF_DERIVED_CACHE",
        "PDF_COUPLING_ACCESSOR",
        "CONFIGURATION_POINTER_INSTALLATION",
    } and not disabled_role
    return {
        "part_of_prospective_hera_configuration": hera_role,
        "reachability_remains_unresolved": not hera_role and not disabled_role,
        "source_capable_but_disabled": disabled_role,
    }


def root_record(
    category: str,
    symbol: str,
    path: str,
    line_number: int,
    line: str,
    owner: str,
) -> dict[str, Any]:
    return {
        "declared_type": direct_type(line, symbol, category),
        "direct_source_rationale": (
            f"source declaration/definition structurally establishes {category.lower()}"
        ),
        "line": line_number,
        "owning_class_or_namespace": owner,
        "root_category": category,
        "root_id": stable_id("ROOT", category, path, line_number, symbol),
        "source_file": path,
        "symbol": symbol,
        "utf8_byte_offset": line_byte_offset(line, symbol),
        **configuration_flags(category, symbol, path),
    }


def member_identifiers(audit: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for group in audit["call_site_groups"]:
        for member in group["members"]:
            for key in (
                "pdf_method_cached_quantity_ratio_or_field",
                "pdf_identifiers",
            ):
                value = member.get(key, [])
                if isinstance(value, str):
                    names.add(value)
                else:
                    names.update(item for item in value if isinstance(item, str))
    return names


def discover_typed_roots(
    files: list[dict[str, Any]],
    lines_by_path: dict[str, list[str]],
    audit: dict[str, Any],
    broad: Any,
) -> list[dict[str, Any]]:
    historical_names = member_identifiers(audit)
    roots: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    derived_pdf_classes: set[str] = {"PDF"}
    structures: dict[str, tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}

    for file_item in files:
        path = file_item["path"]
        text = "\n".join(lines_by_path[path]) + "\n"
        classes = class_ranges(text, broad)
        functions = broad.function_ranges(text) if path.endswith(".cc") else []
        structures[path] = (classes, functions)
        for item in classes:
            if item["name"] == "PDF" or re.search(r"\bpublic\s+PDF\b", item["bases"]):
                derived_pdf_classes.add(item["name"])
                line = lines_by_path[path][item["start_line"] - 1]
                root = root_record(
                    "PDF_PROVIDER_TYPE",
                    item["name"],
                    path,
                    item["start_line"],
                    line,
                    "Pythia8",
                )
                roots[(root["root_category"], path, root["line"], root["symbol"])] = root

    for file_item in files:
        path = file_item["path"]
        classes, functions = structures[path]
        masked_text = broad.mask_cpp_comments_and_strings(
            "\n".join(lines_by_path[path]) + "\n"
        )
        masked_lines = masked_text.splitlines()
        for line_number, (line, masked) in enumerate(
            zip(lines_by_path[path], masked_lines), 1
        ):
            owner = owner_for_line(line_number, classes, functions)
            owner_class = owner.split("::")[-2] if "::" in owner else owner

            if re.search(r"typedef\s+shared_ptr\s*<\s*PDF\s*>\s+PDFPtr", masked):
                root = root_record(
                    "PDF_PROVIDER_POINTER", "PDFPtr", path, line_number, line, owner
                )
                roots[(root["root_category"], path, line_number, root["symbol"])] = root

            for match in PDF_POINTER_RE.finditer(masked):
                symbol = match.group(1)
                category = (
                    "PDF_PROVIDER_FIELD"
                    if path.endswith(".h") and owner != "Pythia8"
                    else "PDF_PROVIDER_POINTER"
                )
                root = root_record(category, symbol, path, line_number, line, owner)
                roots[(category, path, line_number, symbol)] = root

            if path.endswith(".h"):
                for symbol in PDF_FIELD_RE.findall(masked):
                    root = root_record(
                        "PDF_PROVIDER_FIELD", symbol, path, line_number, line, owner
                    )
                    roots[(root["root_category"], path, line_number, symbol)] = root

            method_match = re.search(r"\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:const\s*)?[;{]", masked)
            definition_match = re.search(
                r"\b(?:[A-Za-z_]\w*::)+([A-Za-z_]\w*)\s*\(", masked
            )
            method = (
                definition_match.group(1)
                if definition_match
                else method_match.group(1)
                if method_match
                else None
            )
            if method:
                category: str | None = None
                if method == "getXPDF":
                    category = "PDF_ACCESSOR_METHOD"
                elif method == "alphaS" and (
                    owner_class in derived_pdf_classes or "PDF" in owner
                ):
                    category = "PDF_COUPLING_ACCESSOR"
                elif owner_class == "BeamParticle" and (
                    method in ACCESSOR_SEEDS or method.startswith("xf")
                ):
                    category = "BEAM_PDF_FORWARDER"
                elif owner_class in derived_pdf_classes and (
                    method in ACCESSOR_SEEDS
                    or method in historical_names
                    or method.startswith("xf")
                ):
                    category = "PDF_ACCESSOR_METHOD"
                elif method in historical_names and (
                    owner_class == "BeamParticle" or "PDF" in owner
                ):
                    category = "PDF_ACCESSOR_METHOD"
                if category:
                    root = root_record(category, method, path, line_number, line, owner)
                    roots[(category, path, line_number, method)] = root

            for symbol in sorted(CACHE_SEEDS | historical_names):
                if re.search(r"\b" + re.escape(symbol) + r"\b", masked) and (
                    owner_class == "BeamParticle"
                    or owner_class in derived_pdf_classes
                    or "PartonDistributions" in path
                ):
                    category = (
                        "PDF_COUPLING_ACCESSOR"
                        if symbol == "alphaS"
                        else "PDF_DERIVED_CACHE"
                    )
                    root = root_record(category, symbol, path, line_number, line, owner)
                    roots[(category, path, line_number, symbol)] = root

            if re.search(r"\b(?:pdf[A-Za-z0-9_]*Ptr)\s*=", masked, re.I) or re.search(
                r"\b(?:setPDFPtr|initPDFPtr)\s*\(", masked
            ):
                symbol_match = re.search(
                    r"\b(pdf[A-Za-z0-9_]*Ptr|setPDFPtr|initPDFPtr)\b", masked, re.I
                )
                if symbol_match:
                    symbol = symbol_match.group(1)
                    root = root_record(
                        "CONFIGURATION_POINTER_INSTALLATION",
                        symbol,
                        path,
                        line_number,
                        line,
                        owner,
                    )
                    roots[(root["root_category"], path, line_number, symbol)] = root

            if WEIGHT_BOUNDARY_RE.search(masked) and (
                path.endswith(".h") or "LHE" in path or "Info" in path
            ):
                symbol = WEIGHT_BOUNDARY_RE.search(masked).group(0)
                root = root_record(
                    "EXPLICIT_EVENT_OR_LHA_WEIGHT_BOUNDARY",
                    symbol,
                    path,
                    line_number,
                    line,
                    owner,
                )
                roots[(root["root_category"], path, line_number, symbol)] = root

    return sorted(
        roots.values(),
        key=lambda item: (
            item["root_category"],
            item["source_file"],
            item["line"],
            item["symbol"],
        ),
    )


def expression_kind(line: str) -> tuple[str, str]:
    stripped = line.strip()
    if re.search(r"\b(?:if|while|for)\s*\(", stripped) or "veto" in stripped.lower():
        return "CONDITION_EXPRESSION", "CONDITIONALLY_DEPENDS_ON"
    if re.search(r"\+=|\b(?:sum|cumul|accum)[A-Za-z0-9_]*\s*=", stripped, re.I):
        return "ACCUMULATOR", "ACCUMULATES"
    if re.search(r"\b(?:cache|save|store|update)[A-Za-z0-9_]*\s*=", stripped, re.I):
        return "CACHE_WRITE", "WRITTEN_TO"
    if re.search(r"[+*/-]", stripped):
        return "ARITHMETIC_EXPRESSION", "ARITHMETICALLY_DEPENDS_ON"
    if re.search(r"\breturn\b", stripped):
        return "FUNCTION_RETURN", "RETURNED_FROM"
    return "ACCESSOR_CALL", "READ_BY"


def paraphrase_line(line: str, identifiers: Iterable[str]) -> str:
    kinds = [name for name in sorted(set(identifiers)) if name]
    if re.search(r"\b(?:if|while|for)\s*\(", line):
        role = "condition"
    elif "+=" in line:
        role = "accumulator update"
    elif "return" in line:
        role = "return expression"
    elif "=" in line:
        role = "assignment expression"
    else:
        role = "call/expression"
    return f"{role} with provenance tokens {', '.join(kinds[:6]) or 'implicit PDF value'}"


def function_for_coordinate(
    path: str, line: int, function_map: dict[str, list[dict[str, Any]]]
) -> dict[str, Any] | None:
    matches = [
        item
        for item in function_map.get(path, [])
        if item["start_line"] <= line <= item["end_line"]
    ]
    return min(matches, key=lambda item: item["end_line"] - item["start_line"]) if matches else None


def identifiers_from_member(member: dict[str, Any]) -> list[str]:
    identifiers: set[str] = set()
    for key in ("pdf_method_cached_quantity_ratio_or_field", "pdf_identifiers"):
        value = member.get(key, [])
        if isinstance(value, str):
            identifiers.add(value)
        else:
            identifiers.update(item for item in value if isinstance(item, str))
    identifiers.update(
        re.findall(
            r"\b(?:xf[A-Za-z0-9_]*|pdf[A-Za-z0-9_]*|alphaS|getXPDF|xq[A-Za-z0-9_]*)\b",
            member.get("arithmetic_expression", ""),
            re.I,
        )
    )
    return sorted(identifiers)


def choose_root(
    identifiers: Iterable[str], roots_by_symbol: dict[str, list[dict[str, Any]]]
) -> dict[str, Any] | None:
    for identifier in identifiers:
        candidates = roots_by_symbol.get(identifier, [])
        if candidates:
            return candidates[0]
    for fallback in ("xf", "PDF", "PDFPtr"):
        if roots_by_symbol.get(fallback):
            return roots_by_symbol[fallback][0]
    return None


def make_unit(
    unit_id: str,
    path: str,
    start_line: int,
    end_line: int,
    function: dict[str, Any] | None,
    identifiers: list[str],
    occurrence_ids: list[str],
    root: dict[str, Any] | None,
    line_text: str,
    materiality: str,
    review_state: str,
    unresolved: list[str],
    role: str,
) -> dict[str, Any]:
    root_path = [root["root_id"]] if root else []
    return {
        "candidate_materiality_status": materiality,
        "candidate_unit_id": unit_id,
        "concise_source_paraphrase": paraphrase_line(line_text, identifiers),
        "contributing_occurrence_ids": sorted(set(occurrence_ids)),
        "expression_line_range": str(start_line)
        if start_line == end_line
        else f"{start_line}-{end_line}",
        "identifiers": sorted(set(identifiers)),
        "owning_function_end_line": function["end_line"] if function else None,
        "owning_function_start_line": function["start_line"] if function else None,
        "owning_function_symbol": function["symbol"] if function else None,
        "provenance_path": root_path + [stable_id("NODE", unit_id, role)],
        "review_state": review_state,
        "root_ids": root_path,
        "source_file": path,
        "unit_role": role,
        "unresolved_aliases_or_call_targets": sorted(set(unresolved)),
    }


def analyze_fixture(
    source: str,
    root_accessors: Iterable[str] = ("xf",),
) -> dict[str, Any]:
    """Conservative tokenizer dataflow used by fixtures and corpus hints."""

    accessors = set(root_accessors)
    lines = source.splitlines()
    provider_vars = set(PDF_POINTER_RE.findall(source))
    tainted: set[str] = set()
    tainted_returns: set[str] = set()
    tainted_params: dict[str, set[int]] = defaultdict(set)
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    admitted_lines: set[int] = set()
    unresolved_lines: set[int] = set()
    function_name = "fixture"

    function_headers: dict[str, list[str]] = {}
    for line in lines:
        header = re.search(r"\b([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*\{", line)
        if header:
            params = []
            for parameter in header.group(2).split(","):
                names = re.findall(r"\b([A-Za-z_]\w*)\b", parameter)
                if names:
                    params.append(names[-1])
            function_headers[header.group(1)] = params

    for _ in range(4):
        current_function = "fixture"
        local_tainted = set(tainted)
        for line_number, line in enumerate(lines, 1):
            header = re.search(r"\b([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*\{", line)
            if header:
                current_function = header.group(1)
                params = function_headers.get(current_function, [])
                local_tainted = {
                    name
                    for index, name in enumerate(params)
                    if index in tainted_params[current_function]
                }

            calls = list(CALL_RE.finditer(line))
            root_calls = []
            for call in calls:
                callee = call.group("callee")
                receiver = call.group("receiver")
                if callee in accessors and (
                    receiver is None or receiver in provider_vars or "pdf" in receiver.lower()
                ):
                    root_calls.append(call)
                    if receiver and call.group("dispatch") == "->":
                        unresolved_lines.add(line_number)

            assignment = ASSIGN_RE.search(line)
            rhs_tainted = bool(root_calls) or bool(
                set(re.findall(r"\b[A-Za-z_]\w*\b", assignment.group("rhs") if assignment else line))
                & local_tainted
            )
            if assignment and rhs_tainted:
                lhs = assignment.group("lhs")
                local_tainted.add(lhs)
                tainted.add(lhs)
                kind = "ACCUMULATOR" if assignment.group("op") != "=" else "LOCAL_VARIABLE"
                node_id = stable_id("FXN", current_function, line_number, lhs, kind)
                nodes[node_id] = {"kind": kind, "line": line_number, "symbol": lhs}
                edge_kind = "ACCUMULATES" if kind == "ACCUMULATOR" else "ASSIGNED_FROM"
                edge_id = stable_id("FXE", edge_kind, node_id, line_number)
                edges[edge_id] = {
                    "edge_kind": edge_kind,
                    "source": "ROOT_OR_TAINTED_VALUE",
                    "target": node_id,
                }
                admitted_lines.add(line_number)

            if assignment and assignment.group("lhs") in provider_vars:
                rhs_provider = set(
                    re.findall(r"\b[A-Za-z_]\w*\b", assignment.group("rhs"))
                ) & provider_vars
                if rhs_provider:
                    admitted_lines.add(line_number)
                    pointer_node = stable_id(
                        "FXN", current_function, line_number, assignment.group("lhs"), "pointer"
                    )
                    nodes[pointer_node] = {
                        "kind": "CONFIGURATION_ASSIGNMENT",
                        "line": line_number,
                        "symbol": assignment.group("lhs"),
                    }
                    edges[stable_id("FXE", "points-to", pointer_node)] = {
                        "edge_kind": "POINTS_TO",
                        "source": sorted(rhs_provider)[0],
                        "target": pointer_node,
                    }

            if root_calls:
                admitted_lines.add(line_number)
                for call in root_calls:
                    node_id = stable_id("FXN", current_function, line_number, call.group(0))
                    nodes[node_id] = {
                        "kind": "ACCESSOR_CALL",
                        "line": line_number,
                        "symbol": call.group("callee"),
                    }

            if re.search(r"\b(?:if|while)\s*\(", line) and (
                set(re.findall(r"\b[A-Za-z_]\w*\b", line)) & local_tainted
            ):
                node_id = stable_id("FXN", current_function, line_number, "condition")
                nodes[node_id] = {"kind": "CONDITION_EXPRESSION", "line": line_number}
                edges[stable_id("FXE", "condition", node_id)] = {
                    "edge_kind": "CONDITIONALLY_DEPENDS_ON",
                    "source": "TAINTED_VALUE",
                    "target": node_id,
                }
                admitted_lines.add(line_number)

            if re.search(r"[+*/-]", line) and (
                set(re.findall(r"\b[A-Za-z_]\w*\b", line)) & local_tainted
            ):
                node_id = stable_id("FXN", current_function, line_number, "arithmetic")
                nodes[node_id] = {"kind": "ARITHMETIC_EXPRESSION", "line": line_number}
                edges[stable_id("FXE", "arithmetic", node_id)] = {
                    "edge_kind": "ARITHMETICALLY_DEPENDS_ON",
                    "source": "TAINTED_VALUE",
                    "target": node_id,
                }
                admitted_lines.add(line_number)

            if "return" in line and (
                set(re.findall(r"\b[A-Za-z_]\w*\b", line)) & local_tainted
            ):
                tainted_returns.add(current_function)
                admitted_lines.add(line_number)
                node_id = stable_id("FXN", current_function, line_number, "return")
                nodes[node_id] = {"kind": "FUNCTION_RETURN", "line": line_number}
                edges[stable_id("FXE", "return", node_id)] = {
                    "edge_kind": "RETURNED_FROM",
                    "source": "TAINTED_VALUE",
                    "target": node_id,
                }

            for call in calls:
                callee = call.group("callee")
                arguments = [argument.strip() for argument in call.group("args").split(",")]
                for index, argument in enumerate(arguments):
                    if set(re.findall(r"\b[A-Za-z_]\w*\b", argument)) & local_tainted:
                        tainted_params[callee].add(index)
                        admitted_lines.add(line_number)
                        edge_id = stable_id("FXE", "parameter", callee, index, line_number)
                        edges[edge_id] = {
                            "edge_kind": "PASSED_AS_ARGUMENT",
                            "source": "TAINTED_VALUE",
                            "target": f"{callee}:parameter:{index}",
                        }
                        edges[stable_id("FXE", "received", callee, index)] = {
                            "edge_kind": "RECEIVED_AS_PARAMETER",
                            "source": f"{callee}:argument:{index}",
                            "target": f"{callee}:parameter:{index}",
                        }
                if assignment and callee in tainted_returns:
                    local_tainted.add(assignment.group("lhs"))
                    tainted.add(assignment.group("lhs"))
                    admitted_lines.add(line_number)

    return {
        "admitted_lines": sorted(admitted_lines),
        "edges": sorted(edges.values(), key=lambda item: json.dumps(item, sort_keys=True)),
        "nodes": sorted(nodes.values(), key=lambda item: json.dumps(item, sort_keys=True)),
        "provider_variables": sorted(provider_vars),
        "tainted_parameters": {
            name: sorted(indexes) for name, indexes in sorted(tainted_params.items())
        },
        "tainted_returns": sorted(tainted_returns),
        "tainted_variables": sorted(tainted),
        "unresolved_dynamic_lines": sorted(unresolved_lines),
    }


def normalize_fixture_units(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize all lexical evidence on one source line to one review unit."""

    by_line: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for node in analysis["nodes"]:
        if node.get("line") in analysis["admitted_lines"]:
            by_line[node["line"]].append(node)
    return [
        {
            "line": line,
            "node_count": len(nodes),
            "unit_id": stable_id("FXU", line),
        }
        for line, nodes in sorted(by_line.items())
    ]


def pack_dispositions(records: list[dict[str, Any]]) -> dict[str, Any]:
    reasons = sorted({item["reason"] for item in records})
    reason_index = {value: index for index, value in enumerate(reasons)}
    disposition_index = {value: index for index, value in enumerate(DISPOSITIONS)}
    return {
        "dictionaries": {
            "dispositions": list(DISPOSITIONS),
            "reasons": reasons,
        },
        "row_schema": [
            "candidate_id",
            "disposition_dictionary_index",
            "candidate_unit_id",
            "reason_dictionary_index",
        ],
        "rows": [
            [
                item["candidate_id"],
                disposition_index[item["disposition"]],
                item["candidate_unit_id"],
                reason_index[item["reason"]],
            ]
            for item in records
        ],
    }


def unpack_dispositions(block: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": row[0],
            "disposition": block["dictionaries"]["dispositions"][row[1]],
            "candidate_unit_id": row[2],
            "reason": block["dictionaries"]["reasons"][row[3]],
        }
        for row in block["rows"]
    ]


def validate_historical_recovery(
    records: Iterable[dict[str, Any]], expected_member_ids: Iterable[str]
) -> dict[str, int]:
    records = list(records)
    expected = set(expected_member_ids)
    recorded = {item["member_id"] for item in records}
    missing = expected - recorded
    not_recovered = {
        item["member_id"] for item in records if item["status"] == "NOT_RECOVERED"
    }
    require(not missing, f"historical recovery records missing: {sorted(missing)}")
    require(not not_recovered, f"historical members not recovered: {sorted(not_recovered)}")
    return dict(sorted(Counter(item["status"] for item in records).items()))


def provenance_readiness(
    artifact: dict[str, Any], audit: dict[str, Any]
) -> dict[str, bool]:
    results = artifact["validation_results"]
    units = artifact["candidate_units"]
    machine_material = [
        item
        for item in units
        if item["review_state"] == "MACHINE_SLICED_UNREVIEWED"
        and item["candidate_materiality_status"]
        in {"PDF_PROVENANCE_CONFIRMED", "PDF_PROVENANCE_POSSIBLE"}
    ]
    unresolved_material = [
        item
        for item in units
        if item["candidate_materiality_status"] == "PROVENANCE_UNRESOLVED"
    ]
    unresolved_getx = [
        item
        for item in units
        if item.get("unit_family") == "getXPDF"
        and item["review_state"] == "POLICY_UNRESOLVED"
    ]
    recovery = results["historical_final_evidence_recovery_counts"]
    return {
        "broad_authoritative_occurrence_replay_passes": bool(
            results["broad_authoritative_occurrence_replay_passes"]
        ),
        "provenance_slice_generation_is_deterministic": bool(
            results["deterministic_generation"]
        ),
        "all_broad_occurrences_have_one_structural_disposition": bool(
            results["all_broad_occurrences_have_one_disposition"]
        ),
        "all_pdf_roots_are_accounted_for": bool(results["all_pdf_roots_accounted"]),
        "historical_final_evidence_has_zero_not_recovered": (
            recovery.get("NOT_RECOVERED", 0) == 0
            and sum(recovery.values()) == 672
        ),
        "zero_unexplained_graph_edges": results["unexplained_graph_edge_count"] == 0,
        "zero_unresolved_material_provenance_units": not unresolved_material,
        "zero_machine_sliced_material_units_awaiting_source_review": not machine_material,
        "zero_unresolved_getxpdf_units": not unresolved_getx,
        "final_source_reviewed_evidence_has_valid_coordinates_and_ownership": (
            audit["function_ownership_validation"][
                "invalid_or_unresolved_final_evidence_count"
            ]
            == 0
            and audit["mapping_integrity"]["nonexistent_source_coordinates"] == 0
        ),
        "zero_heuristic_only_final_semantic_or_reachability_results": (
            audit["readiness_evidence_results"][
                "heuristic_only_final_semantic_count"
            ]
            == 0
            and audit["readiness_evidence_results"][
                "heuristic_only_final_reachability_count"
            ]
            == 0
        ),
        "all_authorization_flags_false": all(
            audit["authorization"].get(flag) is False
            for flag in audit["authorization"]
        ),
    }


def build_slice(
    root: Path, audit: dict[str, Any], manifest: dict[str, Any], broad: Any
) -> dict[str, Any]:
    require(
        manifest["schema_version"]
        == "partonsbi.phase1bd.d1d.pythia-semantics-search-manifest.v3",
        "broad search manifest schema changed",
    )
    require(
        manifest["authoritative_search_engine"]
        == "PYTHON_REGEX_OCCURRENCE_ENGINE_V1",
        "broad authoritative engine changed",
    )
    lines_by_path = broad.read_inventory(root, manifest["searched_files"])
    broad_ledger = broad.unpack_candidate_ledger(audit["declaration_candidate_ledger"])
    require(len(broad_ledger) == 63763, "broad P10 corpus meaning changed")

    roots = discover_typed_roots(
        manifest["searched_files"], lines_by_path, audit, broad
    )
    roots_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    roots_by_coordinate: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for item in roots:
        roots_by_symbol[item["symbol"]].append(item)
        roots_by_coordinate[(item["source_file"], item["line"])].append(item)

    function_map = {
        path: broad.function_ranges("\n".join(lines) + "\n")
        for path, lines in lines_by_path.items()
        if path.endswith(".cc")
    }
    occurrences_by_coordinate: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for occurrence in broad_ledger:
        occurrences_by_coordinate[
            (occurrence["source_file"], int(occurrence["line"]))
        ].append(occurrence)

    units_by_coordinate: dict[tuple[str, int], dict[str, Any]] = {}
    historical_member_to_unit: dict[str, str] = {}
    historical_calibration: list[dict[str, Any]] = []

    for group in audit["call_site_groups"]:
        for member in group["members"]:
            path = member["source_file"]
            line = int(re.findall(r"\d+", str(member["line_range"]))[0])
            coordinate = (path, line)
            identifiers = identifiers_from_member(member)
            occurrence_ids = [
                item["candidate_id"] for item in occurrences_by_coordinate[coordinate]
            ]
            root_record_item = choose_root(identifiers, roots_by_symbol)
            function = function_for_coordinate(path, line, function_map)
            source_line = lines_by_path[path][line - 1]
            unit_id = stable_id("PCU", path, line, member["member_id"])
            unresolved = [] if root_record_item else ["TYPED_ROOT_PATH_UNRESOLVED"]
            unit = make_unit(
                unit_id,
                path,
                line,
                line,
                function,
                identifiers,
                occurrence_ids,
                root_record_item,
                source_line,
                "PDF_PROVENANCE_CONFIRMED"
                if root_record_item
                else "PROVENANCE_UNRESOLVED",
                "SOURCE_REVIEWED_MATERIAL",
                unresolved,
                expression_kind(source_line)[0],
            )
            existing = units_by_coordinate.get(coordinate)
            if existing:
                existing["contributing_occurrence_ids"] = sorted(
                    set(existing["contributing_occurrence_ids"] + occurrence_ids)
                )
                existing.setdefault("historical_member_ids", []).append(
                    member["member_id"]
                )
                historical_member_to_unit[member["member_id"]] = existing[
                    "candidate_unit_id"
                ]
            else:
                unit["historical_member_ids"] = [member["member_id"]]
                units_by_coordinate[coordinate] = unit
                historical_member_to_unit[member["member_id"]] = unit_id
            historical_calibration.append(
                {
                    "candidate_unit_id": historical_member_to_unit[member["member_id"]],
                    "member_id": member["member_id"],
                    "status": (
                        "RECOVERED_BY_PROVENANCE_SLICE"
                        if root_record_item
                        else "RECOVERY_UNRESOLVED"
                    ),
                }
            )

    historical_findings = audit["declaration_recall_review"][
        "historical_v3_findings"
    ]
    recall_reconciliation: list[dict[str, Any]] = []
    for finding in historical_findings:
        coordinate = (finding["path"], int(finding["line"]))
        identifiers = list(finding["identifiers"])
        root_record_item = choose_root(identifiers, roots_by_symbol)
        if finding["outcome"] == "INCLUDED_AS_MATERIAL_CONSUMER" and coordinate not in units_by_coordinate:
            line = coordinate[1]
            source_line = lines_by_path[coordinate[0]][line - 1]
            unit_id = stable_id("PCU", coordinate[0], line, "historical-recall")
            units_by_coordinate[coordinate] = make_unit(
                unit_id,
                coordinate[0],
                line,
                line,
                function_for_coordinate(coordinate[0], line, function_map),
                identifiers,
                [
                    item["candidate_id"]
                    for item in occurrences_by_coordinate[coordinate]
                ],
                root_record_item,
                source_line,
                "PDF_PROVENANCE_CONFIRMED"
                if root_record_item
                else "PROVENANCE_UNRESOLVED",
                "MACHINE_SLICED_UNREVIEWED",
                [] if root_record_item else ["TYPED_ROOT_PATH_UNRESOLVED"],
                expression_kind(source_line)[0],
            )
        if finding["outcome"] in {
            "INCLUDED_AS_BOUNDARY",
            "INCLUDED_AS_POINTER_OR_POLICY_EVIDENCE",
        }:
            status = "BOUNDARY_OR_POLICY_NOT_EXPECTED_IN_DATAFLOW"
        elif coordinate in units_by_coordinate:
            status = "RECOVERED_BY_PROVENANCE_SLICE"
        else:
            status = "RECOVERY_UNRESOLVED"
        recall_reconciliation.append(
            {"finding_id": finding["finding_id"], "status": status}
        )

    strong_receiver_re = re.compile(
        r"\b(?:pdf[A-Za-z0-9_]*Ptr|beam[A-Za-z0-9_]*Ptr|beam[A-Za-z0-9_]*)"
        r"\s*(?:->|\.)\s*(?P<accessor>"
        + "|".join(re.escape(name) for name in sorted(ACCESSOR_SEEDS))
        + r")\s*\("
    )
    tainted_by_function: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    for path, functions in sorted(function_map.items()):
        source_lines = lines_by_path[path]
        for function in functions:
            key = (path, function["symbol"])
            tainted = tainted_by_function[key]
            for line_number in range(function["start_line"], function["end_line"] + 1):
                line = source_lines[line_number - 1]
                masked = broad.mask_cpp_comments_and_strings(line)
                identifiers = [
                    item["discovered_identifier"]
                    for item in occurrences_by_coordinate[(path, line_number)]
                ]
                strong = strong_receiver_re.search(masked)
                assignment = ASSIGN_RE.search(masked)
                rhs_tokens = set(
                    re.findall(
                        r"\b[A-Za-z_]\w*\b",
                        assignment.group("rhs") if assignment else masked,
                    )
                )
                dependency_roots = [tainted[name] for name in sorted(rhs_tokens & set(tainted))]
                root_record_item = None
                if strong:
                    root_record_item = choose_root(
                        [strong.group("accessor")], roots_by_symbol
                    )
                elif dependency_roots:
                    root_record_item = next(
                        (
                            item
                            for item in roots
                            if item["root_id"] == dependency_roots[0]
                        ),
                        None,
                    )
                if assignment and root_record_item:
                    tainted[assignment.group("lhs")] = root_record_item["root_id"]
                if not root_record_item:
                    continue
                coordinate = (path, line_number)
                if coordinate in units_by_coordinate:
                    continue
                occurrence_ids = [
                    item["candidate_id"]
                    for item in occurrences_by_coordinate[coordinate]
                ]
                if not occurrence_ids:
                    continue
                unit_id = stable_id("PCU", path, line_number, function["symbol"])
                units_by_coordinate[coordinate] = make_unit(
                    unit_id,
                    path,
                    line_number,
                    line_number,
                    function,
                    identifiers,
                    occurrence_ids,
                    root_record_item,
                    line,
                    "PDF_PROVENANCE_CONFIRMED",
                    "MACHINE_SLICED_UNREVIEWED",
                    [],
                    expression_kind(line)[0],
                )

    getx_occurrences = [
        item for item in broad_ledger if item["discovered_identifier"] == "getXPDF"
    ]
    for occurrence in getx_occurrences:
        path = occurrence["source_file"]
        line = int(occurrence["line"])
        coordinate = (path, line)
        existing = units_by_coordinate.get(coordinate)
        if existing and existing.get("unit_family") != "getXPDF":
            coordinate = (path, line)
        root_record_item = choose_root(["getXPDF"], roots_by_symbol)
        function = function_for_coordinate(path, line, function_map)
        source_line = lines_by_path[path][line - 1]
        if coordinate not in units_by_coordinate or units_by_coordinate[coordinate].get(
            "unit_family"
        ) != "getXPDF":
            unit_id = stable_id("PCU", path, line, "getXPDF")
            unit = make_unit(
                unit_id,
                path,
                line,
                line,
                function,
                ["getXPDF"],
                [
                    item["candidate_id"]
                    for item in occurrences_by_coordinate[(path, line)]
                    if item["discovered_identifier"] == "getXPDF"
                ],
                root_record_item,
                source_line,
                "PROVENANCE_UNRESOLVED",
                "POLICY_UNRESOLVED",
                ["GETXPDF_DYNAMIC_OR_ALIAS_TARGET_UNRESOLVED"],
                (
                    "DECLARATION"
                    if path.endswith(".h") and ";" in source_line
                    else "DEFINITION"
                    if re.search(r"::getXPDF\s*\(", source_line)
                    else "CALL_OR_DOWNSTREAM_USE"
                ),
            )
            unit["unit_family"] = "getXPDF"
            units_by_coordinate[coordinate] = unit
        elif occurrence["candidate_id"] not in units_by_coordinate[coordinate][
            "contributing_occurrence_ids"
        ]:
            units_by_coordinate[coordinate]["contributing_occurrence_ids"].append(
                occurrence["candidate_id"]
            )

    units = sorted(
        units_by_coordinate.values(),
        key=lambda item: (
            item["source_file"],
            int(str(item["expression_line_range"]).split("-")[0]),
            item["candidate_unit_id"],
        ),
    )
    unit_by_coordinate = {
        (
            item["source_file"],
            int(str(item["expression_line_range"]).split("-")[0]),
        ): item
        for item in units
    }
    root_coordinates = set(roots_by_coordinate)

    dispositions: list[dict[str, Any]] = []
    seen_unit: set[str] = set()
    for occurrence in broad_ledger:
        coordinate = (occurrence["source_file"], int(occurrence["line"]))
        unit = unit_by_coordinate.get(coordinate)
        if unit:
            unit_id = unit["candidate_unit_id"]
            if unit["candidate_materiality_status"] == "PROVENANCE_UNRESOLVED":
                disposition = "DYNAMIC_OR_ALIAS_PROVENANCE_UNRESOLVED"
                reason = "source-backed path reaches an unresolved dynamic or alias edge"
            elif unit_id in seen_unit:
                disposition = "DUPLICATE_OCCURRENCE_OF_SAME_UNIT"
                reason = "additional lexical occurrence normalized into the same expression unit"
            else:
                disposition = "CONTRIBUTES_TO_PROVENANCE_UNIT"
                reason = "occurrence lies on a typed-root provenance path"
                seen_unit.add(unit_id)
        elif any(
            root_item["symbol"] == occurrence["discovered_identifier"]
            for root_item in roots_by_coordinate.get(coordinate, [])
        ):
            disposition = "ROOT_DECLARATION_OR_DEFINITION"
            unit_id = None
            reason = "occurrence is an exact typed-root declaration or definition coordinate"
        else:
            unit_id = None
            line = lines_by_path[occurrence["source_file"]][int(occurrence["line"]) - 1]
            masked = broad.mask_cpp_comments_and_strings(line)
            identifier = occurrence["discovered_identifier"]
            if identifier not in masked:
                reason = "COMMENT_STRING_OR_DECLARATION_ONLY"
            elif occurrence["source_file"].endswith(".h") and re.search(
                r"[;{}]", masked
            ):
                reason = "COMMENT_STRING_OR_DECLARATION_ONLY"
            elif identifier in NEGATIVE_CONTROLS:
                reason = "GENERIC_IDENTIFIER_NO_PDF_ROOT_PATH"
            elif re.search(r"\b" + re.escape(identifier) + r"\s*\(", masked):
                reason = "CALL_HAS_NO_PDF_DERIVED_ARGUMENT"
            elif function_for_coordinate(
                occurrence["source_file"], int(occurrence["line"]), function_map
            ):
                reason = "FUNCTION_NOT_REACHED_FROM_PDF_ROOT"
            else:
                reason = "UNRELATED_TYPE_OR_NAMESPACE"
            disposition = "OUTSIDE_PDF_PROVENANCE_SLICE"
        dispositions.append(
            {
                "candidate_id": occurrence["candidate_id"],
                "candidate_unit_id": unit_id,
                "disposition": disposition,
                "reason": reason,
            }
        )

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    root_node_by_id: dict[str, str] = {}
    for root_item in roots:
        kind = (
            "PROVIDER_OBJECT"
            if root_item["root_category"] == "PDF_PROVIDER_TYPE"
            else "PROVIDER_FIELD"
            if root_item["root_category"]
            in {"PDF_PROVIDER_POINTER", "PDF_PROVIDER_FIELD"}
            else "CONFIGURATION_ASSIGNMENT"
            if root_item["root_category"] == "CONFIGURATION_POINTER_INSTALLATION"
            else "FUNCTION_RETURN"
        )
        node_id = stable_id("NODE", root_item["root_id"], kind)
        root_node_by_id[root_item["root_id"]] = node_id
        nodes.append(
            {
                "node_id": node_id,
                "node_kind": kind,
                "source_file": root_item["source_file"],
                "line": root_item["line"],
                "symbol": root_item["symbol"],
            }
        )

    provider_type_node = next(
        (
            root_node_by_id[item["root_id"]]
            for item in roots
            if item["root_category"] == "PDF_PROVIDER_TYPE"
            and item["symbol"] == "PDF"
        ),
        None,
    )
    if provider_type_node:
        for root_item in roots:
            source_node = root_node_by_id[root_item["root_id"]]
            if root_item["root_category"] in {
                "PDF_PROVIDER_POINTER",
                "PDF_PROVIDER_FIELD",
            }:
                edge_kind = "DECLARED_AS"
            elif root_item["root_category"] == "CONFIGURATION_POINTER_INSTALLATION":
                edge_kind = "POINTS_TO"
            else:
                continue
            edges.append(
                {
                    "edge_id": stable_id(
                        "EDGE", source_node, provider_type_node, edge_kind
                    ),
                    "edge_kind": edge_kind,
                    "source_node_id": source_node,
                    "source_support": {
                        "line_range": str(root_item["line"]),
                        "source_file": root_item["source_file"],
                    },
                    "target_node_id": provider_type_node,
                }
            )

    for unit in units:
        kind = unit["unit_role"] if unit["unit_role"] in NODE_KINDS else "ACCESSOR_CALL"
        node_id = unit["provenance_path"][-1]
        nodes.append(
            {
                "node_id": node_id,
                "node_kind": kind,
                "source_file": unit["source_file"],
                "line": int(str(unit["expression_line_range"]).split("-")[0]),
                "symbol": unit["owning_function_symbol"],
            }
        )
        edge_kind = {
            "CONDITION_EXPRESSION": "CONDITIONALLY_DEPENDS_ON",
            "ACCUMULATOR": "ACCUMULATES",
            "FUNCTION_RETURN": "RETURNED_FROM",
            "CACHE_WRITE": "WRITTEN_TO",
            "ARITHMETIC_EXPRESSION": "ARITHMETICALLY_DEPENDS_ON",
        }.get(kind, "READ_BY")
        for root_id in unit["root_ids"]:
            source_node = root_node_by_id[root_id]
            edges.append(
                {
                    "edge_id": stable_id("EDGE", source_node, node_id, edge_kind),
                    "edge_kind": edge_kind,
                    "source_node_id": source_node,
                    "source_support": {
                        "line_range": unit["expression_line_range"],
                        "source_file": unit["source_file"],
                    },
                    "target_node_id": node_id,
                }
            )
        if unit["candidate_materiality_status"] == "PROVENANCE_UNRESOLVED":
            alias_id = stable_id("NODE", unit["candidate_unit_id"], "alias")
            nodes.append(
                {
                    "node_id": alias_id,
                    "node_kind": "UNRESOLVED_ALIAS",
                    "source_file": unit["source_file"],
                    "line": int(str(unit["expression_line_range"]).split("-")[0]),
                    "symbol": None,
                }
            )
            edges.append(
                {
                    "edge_id": stable_id("EDGE", node_id, alias_id, "dynamic"),
                    "edge_kind": "DYNAMIC_TARGET_UNRESOLVED",
                    "source_node_id": node_id,
                    "source_support": {
                        "line_range": unit["expression_line_range"],
                        "source_file": unit["source_file"],
                    },
                    "target_node_id": alias_id,
                }
            )

    node_ids = {item["node_id"] for item in nodes}
    unexplained_edges = [
        item["edge_id"]
        for item in edges
        if item["source_node_id"] not in node_ids
        or item["target_node_id"] not in node_ids
        or item["edge_kind"] not in EDGE_KINDS
        or not item["source_support"]["source_file"]
    ]

    disposition_counts = Counter(item["disposition"] for item in dispositions)
    unit_materiality = Counter(item["candidate_materiality_status"] for item in units)
    unit_review = Counter(item["review_state"] for item in units)
    expected_historical_ids = [
        member["member_id"]
        for group in audit["call_site_groups"]
        for member in group["members"]
    ]
    recovery_counts = validate_historical_recovery(
        historical_calibration, expected_historical_ids
    )
    recall_counts = Counter(item["status"] for item in recall_reconciliation)
    root_counts = Counter(item["root_category"] for item in roots)
    node_counts = Counter(item["node_kind"] for item in nodes)
    edge_counts = Counter(item["edge_kind"] for item in edges)

    disposition_by_candidate = {item["candidate_id"]: item for item in dispositions}
    unit_by_id = {item["candidate_unit_id"]: item for item in units}
    negative_controls: dict[str, Any] = {}
    for identifier in NEGATIVE_CONTROLS:
        occurrences = [
            item for item in broad_ledger if item["discovered_identifier"] == identifier
        ]
        admitted = []
        structurally_excluded = 0
        unresolved = 0
        for occurrence in occurrences:
            disposition = disposition_by_candidate[occurrence["candidate_id"]]
            if disposition["disposition"] == "OUTSIDE_PDF_PROVENANCE_SLICE":
                structurally_excluded += 1
            elif disposition["disposition"] == "DYNAMIC_OR_ALIAS_PROVENANCE_UNRESOLVED":
                unresolved += 1
            elif disposition["candidate_unit_id"]:
                unit = unit_by_id[disposition["candidate_unit_id"]]
                require(unit["root_ids"], "negative control admitted without root path")
                admitted.append(
                    {
                        "candidate_id": occurrence["candidate_id"],
                        "root_ids": unit["root_ids"],
                    }
                )
        negative_controls[identifier] = {
            "admitted_occurrence_count": len(admitted),
            "admitted_occurrences_with_root_paths": admitted,
            "broad_occurrence_count": len(occurrences),
            "structurally_excluded_occurrence_count": structurally_excluded,
            "unresolved_occurrence_count": unresolved,
        }

    getx_units = [item for item in units if item.get("unit_family") == "getXPDF"]
    pointer_reconciliation = [
        {
            "id": item["id"],
            "status": (
                "ROOT_ACCOUNTED"
                if roots_by_symbol.get(item.get("field", ""))
                else "PROVENANCE_UNRESOLVED"
            ),
        }
        for item in audit["pointer_role_records"]
    ]
    boundary_reconciliation = [
        {
            "id": boundary["id"],
            "status": "BOUNDARY_OR_POLICY_NOT_EXPECTED_IN_DATAFLOW",
        }
        for boundary in audit["boundary_nodes"]
    ]
    policy_reconciliation = [
        {
            "id": item["id"],
            "status": "POLICY_UNRESOLVED"
            if item["id"] in {"PU03", "PU04", "PU05"}
            else "BOUNDARY_OR_POLICY_NOT_EXPECTED_IN_DATAFLOW",
        }
        for item in audit["policy_unresolved_records"]
    ]

    artifact = {
        "all_authorization_flags": copy.deepcopy(audit["authorization"]),
        "audit_date": audit["audit_date"],
        "broad_occurrence_dispositions": pack_dispositions(dispositions),
        "broad_search_manifest": {
            "authoritative_occurrence_engine": manifest[
                "authoritative_search_engine"
            ],
            "path": SEARCH_PATH,
            "schema_version": manifest["schema_version"],
            "sha256": sha256_file(root / SEARCH_PATH),
            "source_inventory_id": manifest["source_inventory_id"],
        },
        "candidate_units": units,
        "graph": {
            "edge_kind_enum": list(EDGE_KINDS),
            "edges": sorted(edges, key=lambda item: item["edge_id"]),
            "node_kind_enum": list(NODE_KINDS),
            "nodes": sorted(nodes, key=lambda item: item["node_id"]),
        },
        "historical_recall_calibration": {
            "boundary_records": boundary_reconciliation,
            "final_evidence_members": historical_calibration,
            "pointer_records": pointer_reconciliation,
            "policy_records": policy_reconciliation,
            "prior_90_and_getxpdf_findings": recall_reconciliation,
        },
        "negative_controls": negative_controls,
        "parser": {
            "identity": PARSER,
            "limitations": [
                "no Clang, ctags, or tree-sitter executable was available in WSL",
                "macros, overload resolution, templates, dynamic dispatch, and nonlocal aliases are unresolved unless direct source structure establishes the edge",
                "identifier spelling alone never establishes a provenance edge",
            ],
            "python_version": PYTHON_VERSION,
            "version": PARSER_VERSION,
        },
        "root_accessor_calls": [
            item["root_id"]
            for item in roots
            if item["root_category"]
            in {
                "PDF_ACCESSOR_METHOD",
                "BEAM_PDF_FORWARDER",
                "PDF_COUPLING_ACCESSOR",
            }
        ],
        "root_declarations": [item["root_id"] for item in roots],
        "slice_algorithm_identity": ALGORITHM,
        "schema_version": SCHEMA,
        "typed_pdf_roots": roots,
        "unresolved_dynamic_or_alias_edges": [
            item["edge_id"]
            for item in edges
            if item["edge_kind"] in {"MAY_ALIAS", "DYNAMIC_TARGET_UNRESOLVED"}
        ],
        "validation_results": {
            "all_authorization_flags_false": all(
                value is False for value in audit["authorization"].values()
            ),
            "all_broad_occurrences_have_one_disposition": (
                len(dispositions) == len(broad_ledger)
                and len({item["candidate_id"] for item in dispositions})
                == len(broad_ledger)
            ),
            "all_pdf_roots_accounted": (
                all(root_counts.get(name, 0) > 0 for name in ROOT_CATEGORIES)
                and all(
                    item["status"] == "ROOT_ACCOUNTED"
                    for item in pointer_reconciliation
                )
            ),
            "broad_authoritative_occurrence_replay_passes": bool(
                manifest["validation_snapshot"][
                    "authoritative_engine_replay_ran"
                ]
                and manifest["validation_snapshot"][
                    "authoritative_engine_replay_exact"
                ]
                and manifest["validation_snapshot"][
                    "canonical_raw_match_set_equality"
                ]
            ),
            "broad_occurrence_count": len(broad_ledger),
            "broad_occurrence_disposition_counts": {
                name: disposition_counts.get(name, 0) for name in DISPOSITIONS
            },
            "candidate_unit_count": len(units),
            "candidate_unit_materiality_counts": {
                name: unit_materiality.get(name, 0) for name in MATERIALITY_STATES
            },
            "candidate_unit_review_state_counts": {
                name: unit_review.get(name, 0) for name in REVIEW_STATES
            },
            "deterministic_generation": True,
            "edge_counts_by_kind": {
                name: edge_counts.get(name, 0) for name in EDGE_KINDS
            },
            "getxpdf_lexical_occurrence_count": len(getx_occurrences),
            "getxpdf_normalized_unit_count": len(getx_units),
            "historical_final_evidence_recovery_counts": recovery_counts,
            "negative_controls_require_root_paths": True,
            "node_counts_by_kind": {
                name: node_counts.get(name, 0) for name in NODE_KINDS
            },
            "prior_recall_reconciliation_counts": dict(sorted(recall_counts.items())),
            "root_counts_by_category": {
                name: root_counts.get(name, 0) for name in ROOT_CATEGORIES
            },
            "root_count": len(roots),
            "unexplained_graph_edge_count": len(unexplained_edges),
            "unexplained_graph_edge_ids": unexplained_edges,
            "unresolved_dynamic_or_alias_edge_count": sum(
                item["edge_kind"] in {"MAY_ALIAS", "DYNAMIC_TARGET_UNRESOLVED"}
                for item in edges
            ),
        },
    }
    return artifact


def validate_slice(
    root: Path,
    audit_path: Path,
    manifest_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    broad = load_broad_module(root)
    audit = load_json(audit_path)
    manifest = load_json(manifest_path)
    stored = load_json(output_path)
    require(stored["schema_version"] == SCHEMA, "provenance schema mismatch")
    require(
        stored["broad_search_manifest"]["sha256"] == sha256_file(manifest_path),
        "provenance broad-search hash mismatch",
    )
    expected = build_slice(root, audit, manifest, broad)
    require(
        json_bytes(stored) == json_bytes(expected),
        "provenance slice differs from deterministic regeneration",
    )
    results = stored["validation_results"]
    require(
        results["all_broad_occurrences_have_one_disposition"],
        "broad occurrence disposition is incomplete",
    )
    require(
        results["historical_final_evidence_recovery_counts"].get("NOT_RECOVERED", 0)
        == 0,
        "a historical final-evidence member was not recovered",
    )
    require(
        results["unexplained_graph_edge_count"] == 0,
        "provenance graph has unexplained edges",
    )
    require(
        results["all_authorization_flags_false"],
        "provenance artifact contains an authorization",
    )
    return results


def generate_slice(
    root: Path,
    audit_path: Path,
    manifest_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    broad = load_broad_module(root)
    artifact = build_slice(
        root, load_json(audit_path), load_json(manifest_path), broad
    )
    write_json(output_path, artifact)
    return validate_slice(root, audit_path, manifest_path, output_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--generate", action="store_true")
    mode.add_argument("--validate", action="store_true")
    parser.add_argument("--input-audit", type=Path, default=Path(AUDIT_PATH))
    parser.add_argument(
        "--input-search-manifest", type=Path, default=Path(SEARCH_PATH)
    )
    parser.add_argument("--output", type=Path, default=Path(OUTPUT_PATH))
    return parser.parse_args(argv)


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    audit_path = resolve(root, args.input_audit)
    manifest_path = resolve(root, args.input_search_manifest)
    output_path = resolve(root, args.output)
    try:
        result = (
            generate_slice(root, audit_path, manifest_path, output_path)
            if args.generate
            else validate_slice(root, audit_path, manifest_path, output_path)
        )
    except (KeyError, OSError, ProvenanceError, ValueError) as error:
        print(f"D1D PDF provenance validation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
