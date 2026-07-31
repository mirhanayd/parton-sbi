import copy
import importlib.util
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "phase1bd_d1d_pythia_semantics_audit.py"
)
SPEC = importlib.util.spec_from_file_location("d1d_semantics_audit", SCRIPT)
D1D = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(D1D)


def minimal_audit():
    return {
        "authorization": {flag: False for flag in D1D.AUTHORIZATION_FLAGS},
        "runtime_deferment_policy": {
            "records": [
                {
                    "evaluation_status": "EXPLICITLY_DEFERRED_BY_STATIC_SCOPE",
                    "rationale": "static scope",
                    "topic": "alpha_s_routing",
                },
                {
                    "evaluation_status": "EXPLICITLY_DEFERRED_BY_STATIC_SCOPE",
                    "rationale": "static scope",
                    "topic": "post_init_pointer_identity",
                },
            ]
        },
    }


def passing_evidence():
    return {
        "authoritative_engine_replay_exact": True,
        "authoritative_engine_replay_ran": True,
        "complete_derived_vocabulary_search": True,
        "heuristic_only_final_reachability_count": 0,
        "heuristic_only_final_semantic_count": 0,
        "invalid_source_coordinate_count": 0,
        "occurrence_level_set_equality": True,
        "unexplained_mapping_count": 0,
        "unjustified_omitted_vocabulary_count": 0,
        "unresolved_final_ownership_count": 0,
    }


def candidate(identifier, review="MACHINE_DISCOVERED_UNREVIEWED"):
    return {
        "discovered_identifier": identifier,
        "materiality_status": "MATERIAL_CANDIDATE",
        "scientific_review_status": review,
    }


def p10_spec(vocabulary):
    source = {"search_roots": ["fixture"], "structured_search_specs": []}
    return D1D.make_structured_specs(source, vocabulary)[0]


def test_full_derived_vocabulary_is_used_by_recall_specification():
    vocabulary = {"alphaS", "getXPDF", "newIdentifier"}
    spec = p10_spec(vocabulary)
    assert spec["searched_vocabulary_count"] == len(vocabulary)
    assert all(name in spec["token_extraction_regex"] for name in vocabulary)
    assert spec["searched_vocabulary_sha256"] == D1D.sha256_bytes(
        "\n".join(sorted(vocabulary)).encode("utf-8")
    )


def test_new_identifier_on_already_matched_line_is_not_suppressed():
    source = {
        "search_roots": ["fixture"],
        "structured_search_specs": [
            {"pattern_id": "P03_ALPHA_S", "purpose": "alpha_s"}
        ],
    }
    specs = D1D.make_structured_specs(source, {"alphaS", "newIdentifier"})
    files = [{"file_id": "F0001", "path": "fixture.cc"}]
    lines = {"fixture.cc": ["double x = alphaS() + newIdentifier();"]}
    matches = D1D.iter_structured_matches(specs, files, lines)
    ledger = D1D.derive_candidate_ledger(matches, [])
    assert [item["discovered_identifier"] for item in ledger] == [
        "alphaS",
        "newIdentifier",
    ]
    retained = next(
        item for item in ledger if item["discovered_identifier"] == "newIdentifier"
    )
    assert retained["on_previously_matched_line"] is True
    assert retained["relationship"] == "INDEPENDENT_OCCURRENCE_RETAINED"


def test_unresolved_non_getxpdf_material_candidate_blocks_readiness():
    conditions = D1D.build_readiness(
        minimal_audit(), [candidate("newIdentifier")], passing_evidence()
    )
    assert conditions["zero_unresolved_material_candidates"] is False
    assert conditions["zero_unresolved_getxpdf_candidates"] is True
    assert D1D.readiness_result(conditions) == "EVIDENCE_CORRECTION_REQUIRED"


def test_unresolved_getxpdf_candidate_blocks_readiness():
    conditions = D1D.build_readiness(
        minimal_audit(),
        [candidate("getXPDF", "POLICY_UNRESOLVED")],
        passing_evidence(),
    )
    assert conditions["zero_unresolved_getxpdf_candidates"] is False
    assert D1D.readiness_result(conditions) == "EVIDENCE_CORRECTION_REQUIRED"


def test_authoritative_engine_mismatch_fails_validation():
    spec = p10_spec({"alphaS"})
    spec["engine_identity"] = "UNSUPPORTED_ENGINE"
    with pytest.raises(D1D.EvidenceError, match="unsupported authoritative engine"):
        D1D.validate_search_spec(spec, {"alphaS"})


def test_exact_replay_cannot_be_claimed_when_replay_was_not_run():
    evidence = passing_evidence()
    evidence["authoritative_engine_replay_ran"] = False
    conditions = D1D.build_readiness(minimal_audit(), [], evidence)
    assert conditions["authoritative_engine_replay_passed"] is False


def test_identifier_family_heuristic_cannot_produce_final_semantic_class():
    hint, basis = D1D.semantic_for_identifiers(["PDFEnvelope"])
    assert hint not in D1D.SEMANTIC_CLASSES
    assert hint.startswith("REVIEW_HINT_")
    assert basis == "IDENTIFIER_FAMILY_ONLY"


def test_filename_heuristic_cannot_produce_final_reachability_class():
    hint, basis = D1D.reachability_for_path("src/BeamRemnants.cc")
    assert hint not in D1D.REACHABILITY
    assert hint.startswith("REVIEW_HINT_")
    assert basis == "FILENAME_ONLY"


def test_denominator_final_disposition_requires_curated_evidence():
    member = {
        "member_id": "CSG012.M005",
        "source_file": "fixture.cc",
        "line_range": "4",
    }
    result, reason = D1D.corrected_denominator_class(member, {})
    assert result == "UNRESOLVED"
    assert "curated" in reason


def test_coordinate_outside_function_range_fails_symbol_ownership():
    text = "// Foo::inside() is only a comment\nvoid Foo::inside() {\n  int x = 1;\n}\n\nint outside = 2;\n"
    ranges = D1D.function_ranges(text)
    assert D1D.owning_function(ranges, 3, "Foo::inside") is not None
    assert D1D.owning_function(ranges, 6, "Foo::inside") is None


def test_omitted_vocabulary_entries_require_explicit_allowed_reason():
    allowed = [
        {"identifier": "return", "reason": "NON_SEMANTIC_LANGUAGE_KEYWORD"}
    ]
    forbidden = [{"identifier": "alphaS", "reason": "too broad"}]
    assert D1D.unjustified_vocabulary_omissions(allowed) == []
    assert D1D.unjustified_vocabulary_omissions(forbidden) == forbidden


def test_all_authorization_flags_remain_false():
    audit = minimal_audit()
    conditions = D1D.build_readiness(audit, [], passing_evidence())
    assert conditions["all_planning_authorizations_false"] is True
    for flag in D1D.AUTHORIZATION_FLAGS:
        changed = copy.deepcopy(audit)
        changed["authorization"][flag] = True
        assert (
            D1D.build_readiness(changed, [], passing_evidence())[
                "all_planning_authorizations_false"
            ]
            is False
        )


def test_canonical_key_is_occurrence_level_and_utf8_stable():
    first = {
        "byte_offset": 3,
        "engine_identity": D1D.AUTHORITATIVE_ENGINE,
        "file_id": "F0001",
        "identifier": "alphaS",
        "identifier_hash": D1D.sha256_bytes(b"alphaS")[:16],
        "line": 7,
        "ordinal": 0,
        "pattern_id": "P10_DECLARATION_DERIVED_RECALL",
    }
    second = {**first, "byte_offset": 18, "ordinal": 1}
    assert D1D.canonical_match_key(first) != D1D.canonical_match_key(second)


def test_candidate_ledger_compaction_round_trip():
    source = {
        "search_roots": ["fixture"],
        "structured_search_specs": [],
    }
    specs = D1D.make_structured_specs(source, {"alphaS"})
    files = [{"file_id": "F0001", "path": "fixture.cc"}]
    lines = {"fixture.cc": ["alphaS();"]}
    ledger = D1D.derive_candidate_ledger(
        D1D.iter_structured_matches(specs, files, lines), []
    )
    assert D1D.unpack_candidate_ledger(D1D.pack_candidate_ledger(ledger)) == ledger
