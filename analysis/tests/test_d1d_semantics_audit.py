import copy
import importlib.util
import tempfile
from pathlib import Path


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
        "boundary_nodes": [
            {
                "id": "BN01",
                "members": [
                    {
                        "evidence_origin": "SEARCH_DERIVED",
                        "member_id": "BN01.M01",
                    }
                ],
            }
        ],
        "call_site_groups": [
            {
                "group_id": "CSG001",
                "members": [
                    {
                        "evidence_origin": "SEARCH_DERIVED",
                        "member_id": "CSG001.M001",
                        "primary_classification": "REQUIRES_NONNEGATIVE_DENSITY",
                        "reachability_status": "PROSPECTIVE_HERA_SOURCE_REACHABLE",
                    },
                    {
                        "evidence_origin": "SEARCH_DERIVED",
                        "member_id": "CSG001.M002",
                        "primary_classification": "REQUIRES_STRICTLY_POSITIVE_DENOMINATOR",
                        "reachability_status": "PROSPECTIVE_HERA_SOURCE_REACHABLE",
                    },
                ],
            }
        ],
        "pointer_role_records": [],
        "policy_evidence_records": [],
        "policy_unresolved_records": [],
    }


def test_structured_specs_use_argv_not_interpolated_commands():
    v1 = {
        "search_roots": ["root-a", "root-b", "root-c"],
        "search_commands": [
            {
                "pattern": "TINYPDF",
                "pattern_id": "P08_DENOMINATOR_FLOORS",
                "purpose": "floor",
            }
        ],
    }
    specs = D1D.make_structured_specs(v1)
    assert all(isinstance(spec["argv"], list) for spec in specs)
    assert all("command" not in spec for spec in specs)
    assert all(
        spec["display_command"]
        == D1D.shlex.join([spec["executable"], *spec["argv"]])
        for spec in specs
    )


def test_canonical_key_does_not_collapse_two_matches_on_one_line():
    base = {
        "byte_offset": 3,
        "file_id": "F0001",
        "identifier_hash": "a" * 16,
        "line": 7,
        "ordinal": 0,
        "pattern_id": "P01",
    }
    second = {**base, "byte_offset": 18, "ordinal": 1, "identifier_hash": "b" * 16}
    assert D1D.canonical_match_key(base) != D1D.canonical_match_key(second)


def test_json_generation_is_byte_deterministic():
    left = {"z": [3, 2, 1], "a": {"k": False}}
    right = {"a": {"k": False}, "z": [3, 2, 1]}
    assert D1D.json_bytes(left) == D1D.json_bytes(right)


def test_identifier_hash_verification_uses_utf8_bytes():
    identifier = "xfModified0"
    assert D1D.sha256_bytes(identifier.encode("utf-8"))[:16] == "63a407488207ec54"


def test_dangling_target_is_detected():
    audit = minimal_audit()
    match = {
        "classification": "INCLUDED_CONCRETE_CALL_SITE",
        "primary_target_id": "CSG999.M999",
        "primary_target_type": "call_site_member",
        "related_targets": [],
    }
    summary = D1D.validate_targets(audit, [match])
    assert summary["dangling_target_ids"] == 1


def test_source_coordinate_validation(tmp_path):
    source = tmp_path / "source.cc"
    source.write_text("line one\nline two\n", encoding="utf-8")
    audit = minimal_audit()
    for member in audit["call_site_groups"][0]["members"]:
        member["line_range"] = "2"
        member["source_file"] = "source.cc"
    assert D1D.validate_source_coordinates(tmp_path, audit, {"source.cc"}) == 0
    audit["call_site_groups"][0]["members"][0]["line_range"] = "3"
    assert D1D.validate_source_coordinates(tmp_path, audit, {"source.cc"}) == 1


def test_group_and_member_counts_are_separate():
    aggregates = D1D.aggregate_audit(minimal_audit())
    assert aggregates["call_site_group_count"] == 1
    assert aggregates["concrete_call_site_count"] == 2
    assert aggregates["semantic_group_counts"] == {
        "REQUIRES_NONNEGATIVE_DENSITY": 1,
        "REQUIRES_STRICTLY_POSITIVE_DENOMINATOR": 1,
    }


def test_readiness_cannot_pass_with_unresolved_material_candidate():
    audit = minimal_audit()
    findings = [
        {
            "identifiers": ["getXPDF"],
            "outcome": "UNRESOLVED",
        }
    ]
    conditions = D1D.build_readiness(audit, findings)
    assert conditions["getxpdf_candidates_resolved"] is False
    assert D1D.readiness_result(conditions) == "EVIDENCE_CORRECTION_REQUIRED"


def test_authorization_flags_cannot_become_true_and_still_pass_readiness():
    audit = minimal_audit()
    audit["authorization"]["PROTOTYPE_AUTHORIZED"] = True
    conditions = D1D.build_readiness(audit, [])
    assert conditions["all_planning_authorizations_false"] is False
    assert D1D.readiness_result(conditions) == "EVIDENCE_CORRECTION_REQUIRED"


def test_target_validator_does_not_mutate_audit():
    audit = minimal_audit()
    before = copy.deepcopy(audit)
    D1D.validate_targets(audit, [])
    assert audit == before


if __name__ == "__main__":
    test_structured_specs_use_argv_not_interpolated_commands()
    test_canonical_key_does_not_collapse_two_matches_on_one_line()
    test_json_generation_is_byte_deterministic()
    test_identifier_hash_verification_uses_utf8_bytes()
    test_dangling_target_is_detected()
    with tempfile.TemporaryDirectory() as directory:
        test_source_coordinate_validation(Path(directory))
    test_group_and_member_counts_are_separate()
    test_readiness_cannot_pass_with_unresolved_material_candidate()
    test_authorization_flags_cannot_become_true_and_still_pass_readiness()
    test_target_validator_does_not_mutate_audit()
    print("10 D1D static-evidence tests passed")
