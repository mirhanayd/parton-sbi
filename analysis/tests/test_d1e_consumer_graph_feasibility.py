"""Adversarial tests for the planning-only D1E v2 feasibility contract."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Callable

import pytest

REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts/phase1bd_d1e_consumer_graph_feasibility.py"
SPEC = importlib.util.spec_from_file_location("d1e_feasibility", MODULE_PATH)
assert SPEC and SPEC.loader
d1e = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(d1e)


@pytest.fixture()
def record() -> dict:
    return d1e.build_record(REPO)


def rejected(record: dict) -> None:
    with pytest.raises(d1e.FeasibilityError):
        d1e.validate_record(record, REPO)


def candidate(record: dict, candidate_id: str) -> dict:
    return next(
        row for row in record["toolchain_candidates"] if row["candidate_id"] == candidate_id
    )


def test_committed_artifact_is_valid_and_deterministic(record: dict) -> None:
    path = REPO / d1e.ARTIFACT
    committed = json.loads(path.read_text(encoding="utf-8"))
    d1e.validate_record(committed, REPO)
    assert committed == record
    assert path.read_text(encoding="utf-8") == json.dumps(
        record, indent=2, sort_keys=True
    ) + "\n"


def test_ignored_source_checkout_is_optional_in_clean_ci(tmp_path: Path) -> None:
    assert d1e.verify_source_bytes_when_available(tmp_path, []) is False


def test_corrected_artifact_derives_inconclusive(record: dict) -> None:
    assert record["decision"] == "INCONCLUSIVE"
    assert d1e.derive_decision(record) == "INCONCLUSIVE"


def test_preferred_candidate_is_not_selected(record: dict) -> None:
    assert record["preferred_feasibility_candidate"]["candidate_id"] == (
        "LLVM_CLANG_LIBTOOLING_18_1_8"
    )
    assert record["preferred_feasibility_candidate"]["selection_or_authorization"] is False
    assert record["selected_toolchain"] is None


def test_issue_10_remains_blocked(record: dict) -> None:
    assert record["dependencies"]["blocked_downstream_issue"] == {
        "number": 10,
        "state": "OPEN_BLOCKED",
        "gate_decision": "NOT_EVALUATED",
        "authorization": "NOT_AUTHORIZED",
    }


def test_all_authorization_flags_remain_false(record: dict) -> None:
    assert set(record["authorization"]) == set(d1e.AUTHORIZATION_FLAGS)
    assert all(value is False for value in record["authorization"].values())


def m01(record: dict) -> None:
    candidate(record, "LLVM_CLANG_LIBTOOLING_18_1_8")["capabilities"]["dynamic_dispatch"]["support"] = "NOT_SUPPORTED"


def m02(record: dict) -> None:
    candidate(record, "LLVM_CLANG_LIBTOOLING_18_1_8")["capabilities"]["interprocedural_call_and_return"]["support"] = "NOT_SUPPORTED"


def m03(record: dict) -> None:
    candidate(record, "LLVM_CLANG_LIBTOOLING_18_1_8")["implementation_burden_person_weeks"] = 9.0


def m04(record: dict) -> None:
    candidate(record, "LLVM_CLANG_LIBTOOLING_18_1_8")["license_assessment"] = "CHANGED"


def m05(record: dict) -> None:
    candidate(record, "CODEQL_CPP_2_25_5")["exact_tool_identity"]["binary_release_commit_sha"] = "0" * 40


def m06(record: dict) -> None:
    candidate(record, "CODEQL_CPP_2_25_5")["license_assessment"]["universal_ci_prohibition_claimed"] = True


def m07(record: dict) -> None:
    record["authoritative_source_contract"]["upstream_tag"] = "pythia8311"


def m08(record: dict) -> None:
    record["authoritative_source_contract"]["upstream_commit_sha"] = "0" * 40


def m09(record: dict) -> None:
    record["authoritative_source_contract"]["archive_sha256"] = "0" * 64


def m10(record: dict) -> None:
    record["authoritative_source_contract"]["cxx_standard"] = "c++17"


def m11(record: dict) -> None:
    record["authoritative_source_contract"]["project_include_paths"] = []


def m12(record: dict) -> None:
    record["compilation_database_contract"]["per_translation_unit_overrides"].pop(0)


def m13(record: dict) -> None:
    record["compilation_database_contract"]["per_translation_unit_overrides"].pop(1)


def m14(record: dict) -> None:
    record["compilation_database_contract"]["common_argv_template"] = [
        "unrelated",
        "six",
        "item",
        "argv",
        "with",
        "padding",
    ]


def m15(record: dict) -> None:
    record["acceptance_gates"][0]["requirement"] = "Changed prose under same gate ID."


def m16(record: dict) -> None:
    record["acceptance_gates"][0]["planning_status"] = "PASS"


def m17(record: dict) -> None:
    record["scientific_decisiveness"]["stop_conditions"] = [
        {"condition": "Irrelevant.", "machine_predicate_id": "NONEMPTY"}
    ]


def m18(record: dict) -> None:
    record["false_negative_challenge"]["required_classes"].pop()


def m19(record: dict) -> None:
    record["false_negative_challenge"]["independent_from_graph_construction"] = False


def m20(record: dict) -> None:
    record["calibration_contract"]["acceptance_zero_counts"].remove(
        "UNRESOLVED_BINDING_MEMBER"
    )


def m21(record: dict) -> None:
    record["calibration_contract"]["acceptance_zero_counts"].remove(
        "NOT_RECOVERED_BINDING_MEMBER"
    )


def m22(record: dict) -> None:
    record["static_runtime_boundary"]["runtime_only_properties"].pop()


def m23(record: dict) -> None:
    record["scientific_decisiveness"]["cannot_establish"].pop()


def m24(record: dict) -> None:
    record["source_lineage"]["clean_ci_source_identity_validation"] = (
        "FULLY_PORTABLE_IDENTITY_VALIDATION"
    )


def m25(record: dict) -> None:
    record["scientific_decisiveness"]["scientific_contract_changed"] = True


def m26(record: dict) -> None:
    record["cost_bound"]["implementation_cap_8_person_weeks"] = "SUPPORTED"


def m27(record: dict) -> None:
    record["selected_toolchain"] = {
        "candidate_id": "LLVM_CLANG_LIBTOOLING_18_1_8",
        "selection_scope": "SELECTED",
    }


def m28(record: dict) -> None:
    record["next_step"]["action"] = "IMPLEMENT_GRAPH"


def m29(record: dict) -> None:
    record["authorization"]["IMPLEMENTATION_AUTHORIZED"] = True


def m30(record: dict) -> None:
    record["precedence"]["D2_AUTHORIZED"] = True


ADVERSARIAL_MUTATIONS: tuple[tuple[str, Callable[[dict], None]], ...] = (
    ("dynamic_dispatch_not_supported", m01),
    ("interprocedural_not_supported", m02),
    ("candidate_burden_changed", m03),
    ("llvm_license_changed", m04),
    ("codeql_identity_changed", m05),
    ("codeql_license_claim_changed", m06),
    ("pythia_tag_changed", m07),
    ("pythia_commit_changed", m08),
    ("pythia_archive_hash_changed", m09),
    ("cxx_standard_changed", m10),
    ("include_path_removed", m11),
    ("pythia_xmldir_override_removed", m12),
    ("fjcore_override_removed", m13),
    ("unrelated_argv", m14),
    ("gate_requirement_changed", m15),
    ("gate_promoted_to_pass", m16),
    ("irrelevant_stop_condition", m17),
    ("false_negative_class_removed", m18),
    ("false_negative_independence_disabled", m19),
    ("unresolved_binding_zero_removed", m20),
    ("not_recovered_zero_removed", m21),
    ("runtime_property_removed", m22),
    ("scientific_limitation_removed", m23),
    ("source_lineage_overpromoted", m24),
    ("scientific_contract_changed", m25),
    ("implementation_cost_promoted", m26),
    ("toolchain_selected_while_inconclusive", m27),
    ("implementation_next_step", m28),
    ("authorization_true", m29),
    ("d2_authorized", m30),
)


@pytest.mark.parametrize(("name", "mutate"), ADVERSARIAL_MUTATIONS)
def test_material_semantic_mutation_fails_direct_validation(
    record: dict, name: str, mutate: Callable[[dict], None]
) -> None:
    del name
    mutate(record)
    rejected(record)
