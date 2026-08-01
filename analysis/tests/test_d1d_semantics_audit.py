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

PROVENANCE_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "phase1bd_d1d_pythia_pdf_provenance_slice.py"
)
PROVENANCE_SPEC = importlib.util.spec_from_file_location(
    "d1d_pdf_provenance", PROVENANCE_SCRIPT
)
PROVENANCE = importlib.util.module_from_spec(PROVENANCE_SPEC)
assert PROVENANCE_SPEC.loader is not None
PROVENANCE_SPEC.loader.exec_module(PROVENANCE)

DECISION_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "phase1bd_d1d_pythia_provenance_decision.py"
)
DECISION_SPEC = importlib.util.spec_from_file_location(
    "d1d_provenance_decision", DECISION_SCRIPT
)
DECISION = importlib.util.module_from_spec(DECISION_SPEC)
assert DECISION_SPEC.loader is not None
DECISION_SPEC.loader.exec_module(DECISION)


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


def fixture_edge_kinds(source):
    return {
        edge["edge_kind"]
        for edge in PROVENANCE.analyze_fixture(source, {"xf"})["edges"]
    }


def minimal_provenance_audit():
    audit = minimal_audit()
    audit.update(
        {
            "function_ownership_validation": {
                "invalid_or_unresolved_final_evidence_count": 0
            },
            "mapping_integrity": {"nonexistent_source_coordinates": 0},
            "readiness_evidence_results": {
                "heuristic_only_final_reachability_count": 0,
                "heuristic_only_final_semantic_count": 0,
            },
        }
    )
    return audit


def minimal_provenance_artifact(units=None):
    return {
        "candidate_units": units or [],
        "validation_results": {
            "all_broad_occurrences_have_one_disposition": True,
            "all_pdf_roots_accounted": True,
            "broad_authoritative_occurrence_replay_passes": True,
            "deterministic_generation": True,
            "historical_final_evidence_recovery_counts": {
                "RECOVERED_BY_PROVENANCE_SLICE": 672
            },
            "unexplained_graph_edge_count": 0,
        },
    }


def test_generic_identifier_without_root_path_is_outside_slice():
    analysis = PROVENANCE.analyze_fixture(
        "void f() {\n  int state = 0;\n  state++;\n}\n", {"xf"}
    )
    assert analysis["admitted_lines"] == []


def test_generic_identifier_receiving_xf_derived_argument_is_inside_slice():
    source = (
        "double helper(double state) { return state * 2.; }\n"
        "void f(PDFPtr pdf) {\n"
        "  double value = pdf->xf(1, 0.1, 10.);\n"
        "  helper(value);\n"
        "}\n"
    )
    analysis = PROVENANCE.analyze_fixture(source, {"xf"})
    assert analysis["tainted_parameters"]["helper"] == [0]
    assert 1 in analysis["admitted_lines"]


def test_assignment_propagates_from_accessor_call():
    kinds = fixture_edge_kinds(
        "void f(PDFPtr pdf) {\n  double value = pdf->xf(1, .1, 10.);\n}\n"
    )
    assert "ASSIGNED_FROM" in kinds


def test_return_value_propagation():
    source = (
        "double source(PDFPtr pdf) {\n"
        "  double value = pdf->xf(1, .1, 10.);\n"
        "  return value;\n"
        "}\n"
        "void sink(PDFPtr pdf) {\n"
        "  double received = source(pdf);\n"
        "}\n"
    )
    analysis = PROVENANCE.analyze_fixture(source, {"xf"})
    assert "source" in analysis["tainted_returns"]
    assert "received" in analysis["tainted_variables"]
    assert "RETURNED_FROM" in {edge["edge_kind"] for edge in analysis["edges"]}


def test_function_parameter_propagation():
    source = (
        "void sink(double input) { double used = input; }\n"
        "void f(PDFPtr pdf) {\n"
        "  double value = pdf->xf(1, .1, 10.);\n"
        "  sink(value);\n"
        "}\n"
    )
    kinds = fixture_edge_kinds(source)
    assert {"PASSED_AS_ARGUMENT", "RECEIVED_AS_PARAMETER"} <= kinds


def test_arithmetic_dependency_propagation():
    kinds = fixture_edge_kinds(
        "void f(PDFPtr pdf) {\n"
        "  double value = pdf->xf(1, .1, 10.);\n"
        "  double ratio = value / 2.;\n"
        "}\n"
    )
    assert "ARITHMETICALLY_DEPENDS_ON" in kinds


def test_condition_and_veto_dependency_propagation():
    kinds = fixture_edge_kinds(
        "void f(PDFPtr pdf) {\n"
        "  double value = pdf->xf(1, .1, 10.);\n"
        "  if (value < 0.) return;\n"
        "}\n"
    )
    assert "CONDITIONALLY_DEPENDS_ON" in kinds


def test_accumulator_dependency_propagation():
    kinds = fixture_edge_kinds(
        "void f(PDFPtr pdf) {\n"
        "  double value = pdf->xf(1, .1, 10.);\n"
        "  double total = 0.;\n"
        "  total += value;\n"
        "}\n"
    )
    assert "ACCUMULATES" in kinds


def test_provider_pointer_assignment_propagation():
    kinds = fixture_edge_kinds(
        "void install(PDFPtr incoming) {\n  PDFPtr active = incoming;\n}\n"
    )
    assert "POINTS_TO" in kinds


def test_unresolved_dynamic_dispatch_remains_unresolved():
    analysis = PROVENANCE.analyze_fixture(
        "void f(PDFPtr pdf) {\n  double value = pdf->xf(1, .1, 10.);\n}\n",
        {"xf"},
    )
    assert analysis["unresolved_dynamic_lines"] == [2]


def test_two_lexical_occurrences_in_one_expression_make_one_review_unit():
    analysis = PROVENANCE.analyze_fixture(
        "void f(PDFPtr pdf) {\n"
        "  double value = pdf->xf(1, .1, 10.) + pdf->xf(2, .1, 10.);\n"
        "}\n",
        {"xf"},
    )
    units = PROVENANCE.normalize_fixture_units(analysis)
    assert [unit["line"] for unit in units].count(2) == 1


def test_all_broad_occurrences_receive_one_structural_disposition():
    root = Path(__file__).resolve().parents[2]
    artifact = PROVENANCE.load_json(
        root / "docs" / "phase1bd_d1d_pythia_pdf_provenance_slice.json"
    )
    dispositions = PROVENANCE.unpack_dispositions(
        artifact["broad_occurrence_dispositions"]
    )
    assert len(dispositions) == 63763
    assert len({item["candidate_id"] for item in dispositions}) == 63763


def test_all_672_historical_members_are_recovered_or_explicitly_exempt():
    root = Path(__file__).resolve().parents[2]
    artifact = PROVENANCE.load_json(
        root / "docs" / "phase1bd_d1d_pythia_pdf_provenance_slice.json"
    )
    records = artifact["historical_recall_calibration"]["final_evidence_members"]
    counts = PROVENANCE.validate_historical_recovery(
        records, [item["member_id"] for item in records]
    )
    assert sum(counts.values()) == 672
    assert counts.get("NOT_RECOVERED", 0) == 0


def test_missing_historical_material_member_fails_validation():
    records = [
        {"member_id": "CSG001.M001", "status": "RECOVERED_BY_PROVENANCE_SLICE"}
    ]
    with pytest.raises(PROVENANCE.ProvenanceError, match="missing"):
        PROVENANCE.validate_historical_recovery(
            records, ["CSG001.M001", "CSG001.M002"]
        )


def test_unresolved_getxpdf_units_block_provenance_readiness():
    unit = {
        "candidate_materiality_status": "PROVENANCE_UNRESOLVED",
        "review_state": "POLICY_UNRESOLVED",
        "unit_family": "getXPDF",
    }
    readiness = PROVENANCE.provenance_readiness(
        minimal_provenance_artifact([unit]), minimal_provenance_audit()
    )
    assert readiness["zero_unresolved_getxpdf_units"] is False


def test_machine_sliced_material_units_block_provenance_readiness():
    unit = {
        "candidate_materiality_status": "PDF_PROVENANCE_CONFIRMED",
        "review_state": "MACHINE_SLICED_UNREVIEWED",
    }
    readiness = PROVENANCE.provenance_readiness(
        minimal_provenance_artifact([unit]), minimal_provenance_audit()
    )
    assert (
        readiness["zero_machine_sliced_material_units_awaiting_source_review"]
        is False
    )


def test_negative_controls_do_not_enter_queue_without_provenance():
    for identifier in PROVENANCE.NEGATIVE_CONTROLS:
        analysis = PROVENANCE.analyze_fixture(
            f"void f() {{\n  int {identifier} = 0;\n}}\n", {"xf"}
        )
        assert analysis["admitted_lines"] == []


def test_provenance_readiness_keeps_all_authorization_flags_false():
    audit = minimal_provenance_audit()
    readiness = PROVENANCE.provenance_readiness(
        minimal_provenance_artifact(), audit
    )
    assert readiness["all_authorization_flags_false"] is True
    changed = copy.deepcopy(audit)
    changed["authorization"][D1D.AUTHORIZATION_FLAGS[0]] = True
    assert (
        PROVENANCE.provenance_readiness(
            minimal_provenance_artifact(), changed
        )["all_authorization_flags_false"]
        is False
    )


def final_decision_fixture():
    root = Path(__file__).resolve().parents[2]
    return (
        DECISION.load_json(
            root / "docs" / "phase1bd_d1d_pythia_provenance_slice_decision.json"
        ),
        DECISION.load_json(
            root / "docs" / "phase1bd_d1d_pythia_semantics_audit.json"
        ),
    )


def validate_final_fixture(decision, audit):
    DECISION.validate_payload(
        decision,
        audit,
        DECISION.SEARCH_SHA256,
        DECISION.PROVENANCE_SHA256,
    )


def test_final_decision_cannot_pass_with_required_failed_gates():
    decision, audit = final_decision_fixture()
    decision["decision"] = "PASS"
    with pytest.raises(DECISION.DecisionError, match="must be FAIL"):
        validate_final_fixture(decision, audit)


def test_final_decision_cannot_omit_required_failed_gate():
    decision, audit = final_decision_fixture()
    decision["failed_gates"].remove("typed_root_integrity")
    with pytest.raises(DECISION.DecisionError, match="failed-gate"):
        validate_final_fixture(decision, audit)


def test_final_decision_rejects_broad_manifest_hash_drift():
    decision, _ = final_decision_fixture()
    with pytest.raises(DECISION.DecisionError, match="broad-manifest hash drift"):
        DECISION.validate_payload(
            decision, None, "0" * 64, DECISION.PROVENANCE_SHA256
        )


def test_final_decision_rejects_provenance_slice_hash_drift():
    decision, _ = final_decision_fixture()
    with pytest.raises(DECISION.DecisionError, match="provenance-slice hash drift"):
        DECISION.validate_payload(
            decision, None, DECISION.SEARCH_SHA256, "0" * 64
        )


def test_final_audit_cannot_claim_architecture_readiness():
    decision, audit = final_decision_fixture()
    audit["architecture_comparison_ready"] = True
    with pytest.raises(DECISION.DecisionError, match="architecture-comparison"):
        validate_final_fixture(decision, audit)


def test_final_audit_cannot_claim_independent_historical_recovery():
    decision, audit = final_decision_fixture()
    audit["historical_recall_calibration"] = {
        "RECOVERED_BY_PROVENANCE_SLICE": 672
    }
    with pytest.raises(DECISION.DecisionError, match="independent 672/672"):
        validate_final_fixture(decision, audit)


def test_rejected_slice_cannot_supply_readiness_conditions():
    decision, audit = final_decision_fixture()
    audit["readiness_rule"] = {"all_pdf_roots_are_accounted_for": True}
    with pytest.raises(DECISION.DecisionError, match="supplies readiness"):
        validate_final_fixture(decision, audit)


def test_final_decision_and_audit_keep_all_authorization_flags_false():
    decision, audit = final_decision_fixture()
    for flag in DECISION.AUTHORIZATION_FLAGS:
        changed_decision = copy.deepcopy(decision)
        changed_decision["authorization"][flag] = True
        with pytest.raises(DECISION.DecisionError, match="authorization"):
            validate_final_fixture(changed_decision, audit)
        changed_audit = copy.deepcopy(audit)
        changed_audit["authorization"][flag] = True
        with pytest.raises(DECISION.DecisionError, match="authorization"):
            validate_final_fixture(decision, changed_audit)


def test_minimal_reader_conclusion_remains_independently_supported():
    decision, audit = final_decision_fixture()
    assert audit["minimal_public_reader_patch_basis"]
    audit["minimal_public_reader_patch"] = "SUFFICIENT"
    with pytest.raises(DECISION.DecisionError, match="minimal reader"):
        validate_final_fixture(decision, audit)


def test_d1c_immutable_fail_remains_unchanged():
    decision, audit = final_decision_fixture()
    audit["d1c_stock_boundary_decision"] = "PASS"
    with pytest.raises(DECISION.DecisionError, match="D1C"):
        validate_final_fixture(decision, audit)


def test_audit_v5_historical_reference_requires_source_commit_sha():
    decision, audit = final_decision_fixture()
    decision["evaluated_artifact"]["audit_v5"].pop("source_commit_sha")
    with pytest.raises(DECISION.DecisionError, match="audit-v5 reference"):
        validate_final_fixture(decision, audit)


def test_audit_v5_historical_reference_requires_git_blob_sha():
    decision, audit = final_decision_fixture()
    decision["evaluated_artifact"]["audit_v5"].pop("git_blob_sha")
    with pytest.raises(DECISION.DecisionError, match="audit-v5 reference"):
        validate_final_fixture(decision, audit)


def test_current_v6_blob_cannot_satisfy_audit_v5_reference():
    decision, audit = final_decision_fixture()
    decision["evaluated_artifact"]["audit_v5"]["git_blob_sha"] = (
        "da5d43038b598a90b92945a411c5edc847158dd1"
    )
    with pytest.raises(DECISION.DecisionError, match="audit-v5 reference"):
        validate_final_fixture(decision, audit)


def test_current_final_commit_cannot_replace_audit_v5_source_commit():
    decision, audit = final_decision_fixture()
    decision["evaluated_artifact"]["audit_v5"]["source_commit_sha"] = (
        "6da31bf7c03b05885e8a353d2026bc08978ef096"
    )
    with pytest.raises(DECISION.DecisionError, match="audit-v5 reference"):
        validate_final_fixture(decision, audit)


def test_audit_v5_historical_reference_rejects_wrong_repository_path():
    decision, audit = final_decision_fixture()
    decision["evaluated_artifact"]["audit_v5"]["repository_path"] = (
        "docs/phase1bd_d1d_pythia_semantics_audit_v5.json"
    )
    with pytest.raises(DECISION.DecisionError, match="audit-v5 reference"):
        validate_final_fixture(decision, audit)


def test_audit_v5_historical_reference_rejects_wrong_content_sha256():
    decision, audit = final_decision_fixture()
    decision["evaluated_artifact"]["audit_v5"]["sha256"] = "0" * 64
    with pytest.raises(DECISION.DecisionError, match="audit-v5 reference"):
        validate_final_fixture(decision, audit)


def test_exact_audit_v5_historical_object_tuple_passes():
    decision, audit = final_decision_fixture()
    assert decision["evaluated_artifact"]["audit_v5"] == {
        "git_blob_sha": DECISION.AUDIT_V5_GIT_BLOB_SHA,
        "repository_path": DECISION.AUDIT_PATH,
        "schema_version": "partonsbi.phase1bd.d1d.pythia-semantics-audit.v5",
        "sha256": DECISION.AUDIT_V5_SHA256,
        "source_commit_sha": DECISION.AUDIT_V5_SOURCE_COMMIT_SHA,
    }
    validate_final_fixture(decision, audit)


def test_bare_live_path_is_not_a_valid_audit_v5_reference():
    decision, audit = final_decision_fixture()
    historical = decision["evaluated_artifact"]["audit_v5"]
    historical["path"] = historical.pop("repository_path")
    with pytest.raises(DECISION.DecisionError, match="audit-v5 reference"):
        validate_final_fixture(decision, audit)


def test_lineage_correction_preserves_all_final_fail_decisions():
    decision, audit = final_decision_fixture()
    assert decision["preserved_supported_results"]["D1C_FINAL_DECISION"] == "FAIL"
    assert decision["decision"] == "FAIL"
    assert audit["d1c_stock_boundary_decision"] == "FAIL"
    assert audit["minimal_public_reader_patch"] == "INSUFFICIENT"
    assert audit["provenance_slice_v1_decision"] == "FAIL"
    assert audit["provenance_slice_v1_status"] == "REJECTED_DIAGNOSTIC"
    assert audit["d1d_a_final_decision"] == "FAIL"
    assert audit["failed_gate"] == "provenance_evidence_integrity"
    assert audit["architecture_comparison_ready"] is False
    assert audit["authorization"]["D2_AUTHORIZED"] is False
    validate_final_fixture(decision, audit)
