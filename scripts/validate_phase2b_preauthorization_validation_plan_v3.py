#!/usr/bin/env python3
"""Validate the blocked Phase 2B preauthorization V3 record statically."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v3.json"
SCHEMA = "partonsbi.phase2b.preauthorization-validation-plan.v3"
OUTCOMES = {
    "V3R1_PREAUTH_V3_COMPLETE_READY_FOR_AUTHORIZATION_REVIEW",
    "V3R2_ALPHA_S_CERTIFICATION_BLOCKED",
    "V3R3_NUMERICAL_ACCEPTANCE_RULES_BLOCKED",
    "V3R4_REFERENCE_OR_BRIDGE_BLOCKED",
    "V3R5_SIGN_CONTRACT_BLOCKED",
    "V3R6_MULTIPLE_BLOCKERS_REMAIN",
}
EXPECTED_OUTCOME = "V3R6_MULTIPLE_BLOCKERS_REMAIN"
EXPECTED_PREDECESSORS = {
    "fonll_a_amendment": (
        "docs/reduced_nc_dis/contracts/phase2_fonll_a_contract_amendment.json",
        "10cf19fedcdfe1b94e18ff89d1ae09514a31b8e0f6b055beeb729d61b6c32da8",
    ),
    "preauthorization_v1": (
        "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan.json",
        "7eb8834eb8435532a85bd7d49b173b03e57a268f69f9676e0effbd877903672b",
    ),
    "execution_authorization_review_v1": (
        "docs/reduced_nc_dis/contracts/phase2b_execution_authorization_review.json",
        "03d8119efb819b7a8b51161d5f2ce58fe59dd385b63f2dbfd6203692dac1f9e2",
    ),
    "preauthorization_v2": (
        "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v2.json",
        "a79e87538fae4d3f20793756b321af4d7521c1277ee08580e1b773a7452a9cd2",
    ),
    "execution_authorization_review_v2": (
        "docs/reduced_nc_dis/contracts/phase2b_execution_authorization_review_v2.json",
        "d7826158718ea0c4e5d3fc7c0f60829913e9634c98c45d2316c63bffdce47821",
    ),
}
EXPECTED_TESTS = {
    "TEST_ALPHA",
    "TEST_BRIDGE",
    "TEST_FONLL_COMPONENT",
    "TEST_MASSLESS",
    "TEST_EW_JACOBIAN",
    "TEST_RAW_RATE_SIGN",
    "TEST_GRID_CONVERGENCE",
    "TEST_QUADRATURE_A",
    "TEST_QUADRATURE_B",
    "TEST_CROSS_QUADRATURE",
    "TEST_NORMALIZATION",
    "TEST_NORMALIZED_LAW",
}
EXPECTED_GATES = {f"G{number}_{name}" for number, name in enumerate(
    (
        "FONLL_COMPONENT_REFERENCE",
        "MASSLESS_REFERENCE",
        "ALPHA_S_CONSISTENCY",
        "PDF_BRIDGE_IDENTITY",
        "ANALYTIC_EW_JACOBIAN",
        "POINTWISE_RAW_RATE_NONNEGATIVITY",
        "GRID_REFINEMENT",
        "QUADRATURE_A_CONVERGENCE",
        "QUADRATURE_B_CONVERGENCE",
        "CROSS_QUADRATURE_NORMALIZATION",
        "NORMALIZED_LAW_CLOSURE",
    ), start=1)
}
EXPECTED_GATE_STATUSES = {
    "G1_FONLL_COMPONENT_REFERENCE": "BLOCKED_PREAUTH_SPECIFICATION",
    "G2_MASSLESS_REFERENCE": "BLOCKED_PREAUTH_SPECIFICATION",
    "G3_ALPHA_S_CONSISTENCY": "BLOCKED_PREAUTH_SPECIFICATION",
    "G4_PDF_BRIDGE_IDENTITY": "FULLY_SPECIFIED_NOT_EXECUTED",
    "G5_ANALYTIC_EW_JACOBIAN": "FULLY_SPECIFIED_NOT_EXECUTED",
    "G6_POINTWISE_RAW_RATE_NONNEGATIVITY": "FULLY_SPECIFIED_NOT_EXECUTED",
    "G7_GRID_REFINEMENT": "BLOCKED_ACCEPTANCE_RULE",
    "G8_QUADRATURE_A_CONVERGENCE": "BLOCKED_ACCEPTANCE_RULE",
    "G9_QUADRATURE_B_CONVERGENCE": "BLOCKED_ACCEPTANCE_RULE",
    "G10_CROSS_QUADRATURE_NORMALIZATION": "BLOCKED_BY_UPSTREAM_RULES",
    "G11_NORMALIZED_LAW_CLOSURE": "BLOCKED_BY_UPSTREAM_RULES",
}
EXPECTED_COVERAGE = {
    "complete_implemented_nc_rate",
    "electroweak_assembly",
    "massless_coefficients",
    "massive_contribution",
    "fonll_difference_matching",
    "pdf_evaluator",
    "pdf_to_apfel_bridge",
    "alpha_s",
    "coordinate_jacobian",
    "quadrature_a",
    "quadrature_b",
    "normalization_assembly",
    "normalized_law_assembly",
}
EXPECTED_REFERENCE_STATUSES = {
    "complete_implemented_nc_rate": "PARTIAL",
    "electroweak_assembly": "DEFINED_SIMULATOR_COMPONENT_WITH_LOCAL_VALIDATION",
    "massless_coefficients": "PUBLISHED_INDEPENDENT_BENCHMARK",
    "massive_contribution": "UNVALIDATED",
    "fonll_difference_matching": "UNVALIDATED",
    "pdf_evaluator": "INDEPENDENT_POSTAUTH_TEST_FULLY_SPECIFIED",
    "pdf_to_apfel_bridge": "INDEPENDENT_POSTAUTH_TEST_FULLY_SPECIFIED",
    "alpha_s": "PARTIAL",
    "coordinate_jacobian": "FULLY_INDEPENDENT",
    "quadrature_a": "PARTIAL",
    "quadrature_b": "PARTIAL",
    "normalization_assembly": "PARTIAL",
    "normalized_law_assembly": "PARTIAL",
}
EXPECTED_PRECEDENCE = [
    "CONTRACT_IDENTITY_FAILURE",
    "SUPPORT_FAILURE",
    "BRIDGE_FAILURE",
    "ALPHA_S_FAILURE",
    "REFERENCE_FAILURE",
    "NONFINITE_IMPLEMENTED_RATE",
    "RAW_NEGATIVE_RATE",
    "NORMALIZATION_NONPOSITIVE",
    "CONVERGENCE_FAILURE",
    "RESOURCE_EXHAUSTION",
    "INCONCLUSIVE",
]
REQUIRED_TEST_FIELDS = {
    "test_id",
    "purpose",
    "status",
    "implementation_identity",
    "inputs",
    "exact_finite_domain_grid",
    "metric",
    "threshold_or_rule",
    "near_zero_behavior",
    "pass",
    "fail",
    "inconclusive",
    "resource_count",
    "artifacts_emitted",
    "failure_precedence",
    "blocker",
}

EXPECTED_DEFECT_RESOLUTIONS = {
    "D1_GLOBAL_ERROR_BUDGET_INVALID": "REMOVED",
    "D2_EQUAL_EIGHT_WAY_SPLIT_INVALID": "REMOVED",
    "D3_AS2_CONTINUOUS_DOMAIN_UNDERDEFINED": "PARTIAL_BLOCKER_REMAINS",
    "D4_BRIDGE_UNDERDEFINED": "RESOLVED_AT_PLAN_LEVEL",
    "D5_POSTAUTH_REFERENCE_SPEC_UNDERDEFINED": "PARTIAL_BLOCKER_REMAINS",
    "D6_NR2_UPSTREAM_ERROR_UNDERDEFINED": "REPLACED_BY_SIGN1",
    "D7_RESOURCE_COUNT_WRONG": "HONESTLY_BLOCKED_NOT_REPLACED_BY_FALSE_TOTAL",
    "D8_REPRODUCIBILITY_INCOMPLETE": "PARTIAL_BLOCKER_REMAINS",
}

EXPECTED_SOURCE_KEYS = {
    "source_id",
    "title",
    "authors_or_project",
    "official_url",
    "version_or_publication_date",
    "retrieved_utc",
    "sha256",
    "exact_locator",
    "claim",
    "qualification",
    "noncoverage",
    "load_bearing",
}
EXPECTED_SOURCE_HASHES = {
    "PYTHON_3_10_20_SOURCE": "4ff5fd4c5bab803b935019f3e31d7219cebd6f870d00389cea53b88bbe935d1a",
    "NUMPY_2_2_6": [
        "e29554e2bef54a90aa5cc07da6ce955accb83f21ab5de01a62c8478897b264fd",
        "fc7b73d02efb0e18c000e9ad8b83480dfcd5dfd11065997ed4c6747470ae8915",
    ],
    "SCIPY_1_15_3_CP310_MANYLINUX2014_X86_64_WHEEL": "9e2abc762b0811e09a0d3258abee2d98e0c703eee49464ce0069590846f31d40",
    "MPMATH_1_3_0_PY3_WHEEL": "a0b2b9fe80bbcd81a6647ff13108738cfb482d481d826cc0e02f5b35e5c88d2c",
    "LHAPDF_6_5_6_SOURCE_REINSPECTION": "6b8b7e38dc26a977a24f5a321215b7054c14a4469d04134d70cb93a860eeeea7",
    "CT18NLO_MEMBER0_COMPONENT_BYTES": {
        "archive": "c9127231e77e97cbec79cb5839203ab00f8db77237a061b61f9420f2b7b9c213",
        "info": "be60232d8e6c49982c82f5fa990fd5b0fd1050719944f31602bf27cdb16548b0",
        "member0": "375db856d2f8c7087a626c92ebf228d3f080e5de83175519778ffaf6e72e5410",
    },
    "MASSLESS_DIS_BENCHMARK_2024_TEX": {
        "source_tar": "ccd5134044bc95027e696ddf764d759950dd2486eeeece9f98deaa2a4591c0db",
        "main_tex": "86a6cd320eea21846b50e0cd67276ac7a50393c04038834ff5e361722f5c19f6",
        "nlo_table_tex": "0c8017612bc0da934ee53221f16c9b9118d6c0640e715e8fbbaaedcb7dad2edb",
    },
    "FONLL_BENCHMARK_2011_V3_TEX_RETRIEVAL": "1218743006463298bef050737f00fa84da848bbd36f67ff3e2e671463c876765",
    "LES_HOUCHES_2010_SOURCE_RETRIEVAL": "83b25c39419b6d5617f2a5e1571412ea4c48952d81cb39c864ac9a1f4e4f20d7",
}
EXPECTED_SOURCE_URLS = {
    "PYTHON_3_10_20_SOURCE": "https://www.python.org/ftp/python/3.10.20/Python-3.10.20.tgz",
    "NUMPY_2_2_6": "https://pypi.org/project/numpy/2.2.6/",
    "SCIPY_1_15_3_CP310_MANYLINUX2014_X86_64_WHEEL": "https://files.pythonhosted.org/packages/8e/6d/41991e503e51fc1134502694c5fa7a1671501a17ffa12716a4a9151af3df/scipy-1.15.3-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
    "MPMATH_1_3_0_PY3_WHEEL": "https://files.pythonhosted.org/packages/43/e3/7d92a15f894aa0c9c4b49b8ee9ac9850d6e63b03c9c32c0367a13ae62209/mpmath-1.3.0-py3-none-any.whl",
    "LHAPDF_6_5_6_SOURCE_REINSPECTION": "https://lhapdf.hepforge.org/downloads/?f=LHAPDF-6.5.6.tar.gz",
    "CT18NLO_MEMBER0_COMPONENT_BYTES": "https://lhapdfsets.web.cern.ch/current/CT18NLO.tar.gz",
    "MASSLESS_DIS_BENCHMARK_2024_TEX": "https://arxiv.org/e-print/2404.15711v1",
    "FONLL_BENCHMARK_2011_V3_TEX_RETRIEVAL": "https://arxiv.org/e-print/1101.1300v3",
    "LES_HOUCHES_2010_SOURCE_RETRIEVAL": "https://arxiv.org/e-print/1003.1241",
}

EXPECTED_ACCEPTED_SOFTWARE = {
    "name": "APFEL",
    "version": "3.1.1",
    "commit": "72bf6ec7c72c923dd2115f2a98c6f593f9c91d2a",
    "archive_sha256": "e5c4b3d955f8d33e8e8ff2d9d1687da57f2ee99245abc579f9d32caa616f0f53",
}
EXPECTED_APFEL_CONTROLS = [
    "SetAlphaQCDRef(0.118,91.187)",
    "SetAlphaEvolution(exact)",
    "SetPerturbativeOrder(1)",
    "SetPoleMasses(1.3,4.75,172.0)",
    "SetMaxFlavourAlpha(5)",
    "SetVFNS",
    "SetRenFacRatio(1)",
    "SetMassMatchingScales(1,1,1)",
    "SetRenQRatio(1)",
]
EXPECTED_APFEL_SOURCE_HASHES = {
    "apfel_evol_header": "de70eaa26195ed5258fd8bf59485733b3c9fea0a40ff2de46e5a11fe6fa536b0",
    "compute_dis_operators": "4f4b17bac6cf360fe1406b00fe7d20078053f99e624c6b403b93bf3a8aa65990",
    "a_qcd": "3725900eb705779e3595eb1e85fccc11b864b1fde8a91971775abe3bad56ca94",
    "set_pdf_set": "b5505d4298487eb04c4fbf30a26fb90750973ce0897f38d7155d25057cd9d165",
    "init_pdfs": "e96aa76b41bff4217613f45dfacca7f53591955cca65e286abaa9fd2dcbda1a2",
}

EXPECTED_RAW_PDF = {
    "set": "CT18NLO",
    "data_version": 1,
    "set_index": 14400,
    "member": 0,
    "archive_sha256": "c9127231e77e97cbec79cb5839203ab00f8db77237a061b61f9420f2b7b9c213",
    "info_sha256": "be60232d8e6c49982c82f5fa990fd5b0fd1050719944f31602bf27cdb16548b0",
    "member_file": "CT18NLO_0000.dat",
    "member_sha256": "375db856d2f8c7087a626c92ebf228d3f080e5de83175519778ffaf6e72e5410",
    "flavor_order": [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 21],
    "x_support": [1e-9, 1],
    "q_support_gev": [1.295, 100000],
    "q0_gev": 1.295,
    "interpolation": "logcubic",
    "installed_extrapolator": "continuation",
    "caller_policy": "strict_no_extrapolation",
    "lhapdf_version": "6.5.6",
    "lhapdf_commit": "92239ac82134be698805c1002b4615e5167c6fa3",
}
EXPECTED_ANCHORS = [
    ("CENTER", 0, 0, "sha256:61d340fd4754bcdc03dfd1ff79b9871e8eb10170b064518846f8f17d2f3a99ed"),
    ("DELTA_V_MIN", -0.2, 0, "sha256:c848736053067f041a2ae951553130508da7998a92140f07aa9007b57982eef8"),
    ("DELTA_V_MAX", 0.2, 0, "sha256:32bac2f397c1863d4272c11395b45a1949fa42957d39c7b322342116b48dceff"),
    ("LAMBDA_SEA_MIN", 0, -0.25, "sha256:1722969c7bd0162946a6c1dc1dd4da5468d4bc84877edbac9aced2cf643e475e"),
    ("LAMBDA_SEA_MAX", 0, 0.25, "sha256:3347da52d25c9cfe5c57f15b1a3b451c0ba462bc6dda9b4385726c01f49f0b91"),
    ("CORNER_MIN_MIN", -0.2, -0.25, "sha256:5ea6b258d24c65ffe596b7fb3cc9b9778172c617477c37399809f40579281632"),
    ("CORNER_MIN_MAX", -0.2, 0.25, "sha256:e5d64d18fbd1a3db6a820b2a22af93c9154eafbe3f24fb46082790bb5a7bf95b"),
    ("CORNER_MAX_MIN", 0.2, -0.25, "sha256:2aa2b5f2625f06240e3256eea0e7bf1b66f789776553d057cb95d6ac31b8851c"),
    ("CORNER_MAX_MAX", 0.2, 0.25, "sha256:54ce59c91ca6646a26c082de6e753964229a17a941b9aec05a28f9ee8cdba142"),
]
EXPECTED_PROJECTED_PDF = {
    "family": "ct18nlo_two_parameter_boundary_v2",
    "baseline": "ct18nlo_member0_sumrule_projected_boundary_v2",
    "implementation_commit": "94e46aca6dd870c6de21f9426f165ac1880429dd",
    "d0r_merge_commit": "12755acbbf0791f97be95fe72177bab4a126c58b",
    "d0r_decision_sha256": "40e75fda281578f45d193858667eeed2c1747a07d64f53672adec10145c9e775",
    "continuous_pdf_sha256_at_implementation": "34fd0da98d6ea7c3eab79cc7d797c4bdc321dc4d9bf58aad313bc82afa2226a6",
    "projected_baseline_canonical_identity": "sha256:3c1320251b098c9362a619b646575ce109ad5c1222815f9705dc03134e85a2b6",
}

EXPECTED_BRIDGE_INVARIANTS = [
    "B1_MEMBER_SET_IDENTITY",
    "B2_FLAVOR_MAPPING",
    "B3_X_TIMES_F_EXACTLY_ONCE",
    "B4_SIGN_PRESERVATION",
    "B5_ZERO_PRESERVATION",
    "B6_STRICT_SUPPORT",
    "B7_Q_IN_GEV_EXACT_Q0",
    "B8_CALLBACK_INTERFACE_IDENTITY",
]
EXPECTED_BRIDGE_SLOTS = {
    "0": "x*f(21)",
    "1": "x*f(1)",
    "2": "x*f(2)",
    "3": "x*f(3)",
    "4": "x*f(4)",
    "5": "x*f(5)",
    "6": "top=+0",
    "7": "photon=+0",
    "-6": "topbar=+0",
    "-5": "x*f(-5)",
    "-4": "x*f(-4)",
    "-3": "x*f(-3)",
    "-2": "x*f(-2)",
    "-1": "x*f(-1)",
}
EXPECTED_SENTINEL_F = {
    "1": -64,
    "2": 128,
    "3": -256,
    "4": 512,
    "5": -1024,
    "21": 32,
    "-5": -1,
    "-4": 2,
    "-3": -4,
    "-2": 8,
    "-1": -16,
}
EXPECTED_BRIDGE_RESOURCES = {
    "identity_cases": 16,
    "interface_checks": 2,
    "callback_attempts": 1045,
    "evaluator_invocations": 1040,
    "slot_comparisons": 14532,
    "total_logical_cases": 1063,
}
EXPECTED_BRIDGE_ORACLE = {
    "path": "analysis/validation/phase2b_bridge_oracles.py",
    "sha256": "b1c70070dc0fbb66a5b7de7125a16b478893d624b5909b44426ae61a8a27f92c",
    "test_path": "analysis/tests/test_phase2b_bridge_oracles.py",
    "test_sha256": "01029a7969b00b878d3de3096e6b1c4074edd5f0147d58204bfe25378aa77fe1",
}
EXPECTED_BRIDGE_CASE_HASHES = {
    "identity_cases": "4e651393009b8df31d634437c90fd5cacb4f5853c54fdab52709c3bc6e7a8246",
    "support_cases": "6dbfb7d97e5b38990e49c93b219c8ddbd1e66700d92bffa2e8f5135b8c98c439",
    "q_cases": "aa16cb4a7bdae69b7f210b88fc0a1d1417568d1e2a3cfaf05899aff49c935dae",
    "interface_cases": "d662f5b9652a4df78263593ad6f59c120f26ac219abab103359bb37e3a8aca69",
}
MASSLESS_GRID_SHA256 = "909047190af89e8ac44c2ec41a7b1686e333dfdab8b4b6e7b5ceacaee43bfcff"
EXPECTED_TEST_STATUSES = {
    "TEST_ALPHA": "BLOCKED_PREAUTH_SPECIFICATION",
    "TEST_BRIDGE": "FULLY_SPECIFIED_NOT_EXECUTED",
    "TEST_FONLL_COMPONENT": "BLOCKED_PREAUTH_SPECIFICATION",
    "TEST_MASSLESS": "BLOCKED_PREAUTH_SPECIFICATION",
    "TEST_EW_JACOBIAN": "FULLY_SPECIFIED_NOT_EXECUTED",
    "TEST_RAW_RATE_SIGN": "FULLY_SPECIFIED_NOT_EXECUTED",
    "TEST_GRID_CONVERGENCE": "BLOCKED_ACCEPTANCE_RULE",
    "TEST_QUADRATURE_A": "BLOCKED_ACCEPTANCE_RULE",
    "TEST_QUADRATURE_B": "BLOCKED_ACCEPTANCE_RULE",
    "TEST_CROSS_QUADRATURE": "BLOCKED_BY_UPSTREAM_RULES",
    "TEST_NORMALIZATION": "BLOCKED_BY_UPSTREAM_RULES",
    "TEST_NORMALIZED_LAW": "BLOCKED_BY_UPSTREAM_RULES",
}
EXPECTED_OUTCOME_CATEGORIES = {
    "ALPHA_EXECUTION_SPECIFICATION",
    "REFERENCE_EXECUTION_SPECIFICATION",
    "NUMERICAL_ACCEPTANCE_RULES",
    "NUMERICAL_RUNTIME_IDENTITY",
    "RESOURCE_AGGREGATE",
}


class ValidationError(ValueError):
    """Raised when V3 violates its static scientific contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def anchor_tuples(anchors: Any) -> list[tuple[Any, Any, Any, Any]]:
    require(isinstance(anchors, list), "Anchor collection is not a list")
    return [
        (
            anchor.get("anchor_id"),
            anchor.get("delta_v"),
            anchor.get("lambda_sea"),
            anchor.get("canonical_identity"),
        )
        for anchor in anchors
    ]


def validate(
    record: dict[str, Any],
    *,
    root: Path = ROOT,
    check_docs: bool = True,
    expected_outcome: str | None = EXPECTED_OUTCOME,
) -> None:
    require(record.get("schema_version") == SCHEMA, "Wrong v3 schema")
    require(record.get("starting_main_sha") == "63069023cc6e7bbd57f80ecf10c8e7d57acae367", "Starting main changed")

    predecessors = record.get("predecessors", {})
    require(set(predecessors) == set(EXPECTED_PREDECESSORS), "Wrong predecessor set")
    for key, (relative, digest) in EXPECTED_PREDECESSORS.items():
        item = predecessors[key]
        require(item.get("path") == relative, f"Wrong predecessor path: {key}")
        require(item.get("sha256") == digest, f"Wrong predecessor SHA: {key}")
        require(item.get("bytes_immutable") is True, f"Predecessor not immutable: {key}")
        require(sha256(root / relative) == digest, f"Historical predecessor bytes changed: {key}")

    history = record.get("historical_state", {})
    require(history.get("phase2a_status") == "COMPLETE", "Historical Phase 2A status changed")
    require(history.get("phase2a_scientific_decision") == "INCONCLUSIVE", "Historical Phase 2A changed to PASS")
    require(history.get("adr_013_status") == "Proposed", "ADR-013 status changed")
    require(history.get("accepted_pdf_family") == "ct18nlo_two_parameter_boundary_v2", "Accepted PDF family changed")
    require(history.get("issue_54_unchanged") is True and history.get("issue_10_unchanged") is True, "Unrelated issue changed")

    scientific = record.get("scientific_object", {})
    require(scientific.get("target") == "p(theta_PDF | D)", "Wrong inference target")
    require("No full flavor separation" in scientific.get("flavor_claim", ""), "Flavor nonclaim missing")
    require("not default observed ML features" in scientific.get("truth_policy", ""), "Truth-feature policy missing")

    defects = record.get("established_defects", {})
    require(set(defects) == set(EXPECTED_DEFECT_RESOLUTIONS), "D1-D8 coverage incomplete")
    for defect_id, resolution in EXPECTED_DEFECT_RESOLUTIONS.items():
        item = defects[defect_id]
        require(set(item) == {"resolution", "evidence"}, f"Malformed defect record: {defect_id}")
        require(item.get("resolution") == resolution, f"Wrong defect resolution: {defect_id}")
        require(isinstance(item.get("evidence"), str) and item["evidence"], f"Missing defect evidence: {defect_id}")

    accepted = record.get("accepted_contract", {})
    require(accepted.get("scheme") == "FONLL-A", "Accepted scheme changed")
    require(accepted.get("perturbative_order") == "NLO", "Accepted perturbative order changed")
    require(accepted.get("software") == EXPECTED_ACCEPTED_SOFTWARE, "Accepted APFEL identity changed")
    require(accepted.get("pdf_family") == EXPECTED_PROJECTED_PDF["family"], "Accepted PDF family changed")
    require(accepted.get("pdf_baseline") == EXPECTED_PROJECTED_PDF["baseline"], "Accepted PDF baseline changed")
    require(accepted.get("theta_domain") == {"delta_v": [-0.2, 0.2], "lambda_sea": [-0.25, 0.25]}, "Accepted theta domain changed")
    require(anchor_tuples(accepted.get("theta_anchors")) == EXPECTED_ANCHORS, "Accepted theta anchors changed")

    sources = record.get("source_registry_additions", [])
    require(isinstance(sources, list), "Source registry is not a list")
    source_map = {item.get("source_id"): item for item in sources}
    require(len(source_map) == len(sources), "Duplicate source registry identity")
    require(set(source_map) == set(EXPECTED_SOURCE_HASHES), "Source registry identity set changed")
    for source_id, expected_hash in EXPECTED_SOURCE_HASHES.items():
        source = source_map[source_id]
        require(set(source) == EXPECTED_SOURCE_KEYS, f"Malformed source registry entry: {source_id}")
        require(source.get("official_url") == EXPECTED_SOURCE_URLS[source_id], f"Wrong source URL: {source_id}")
        require(source.get("sha256") == expected_hash, f"Wrong source SHA: {source_id}")
        require(isinstance(source.get("load_bearing"), bool), f"Source load-bearing flag is not boolean: {source_id}")
        for field in (
            "title",
            "authors_or_project",
            "version_or_publication_date",
            "retrieved_utc",
            "exact_locator",
            "claim",
            "qualification",
            "noncoverage",
        ):
            require(source.get(field) not in (None, "", [], {}), f"Source field missing: {source_id}.{field}")

    architecture = record.get("error_budget_architecture", {})
    require(architecture.get("global_parent_budget") is None, "Global parent budget reintroduced")
    require(architecture.get("equal_share_allocation") is None, "Equal 1/8 split reintroduced")
    require(architecture.get("gate_local_only") is True and architecture.get("cross_gate_compensation") is False, "Gate-local isolation weakened")
    serialized = json.dumps(record, sort_keys=True).lower()
    require("t_external" not in serialized, "T_external global budget reintroduced")
    bridge_derivation = record.get("bridge_contract", {}).get("floating_derivation", "").lower()
    require("16u" not in bridge_derivation, "Unexplained 16u bridge tolerance reintroduced")
    require("282-point" not in serialized and "282 sampled" not in serialized, "Sample-only continuous alpha claim reintroduced")

    gates = record.get("gate_local_architecture", [])
    gate_map = {gate.get("gate_id"): gate for gate in gates}
    require(len(gate_map) == len(gates) and set(gate_map) == EXPECTED_GATES, "G1-G11 architecture incomplete")
    for gate_id, expected_status in EXPECTED_GATE_STATUSES.items():
        require(gate_map[gate_id].get("status") == expected_status, f"Wrong gate status: {gate_id}")
        require(isinstance(gate_map[gate_id].get("semantics"), str) and gate_map[gate_id]["semantics"], f"Missing gate semantics: {gate_id}")

    massive = record.get("external_comparator_semantics", {}).get("massivedis", {})
    require(massive.get("classification") == "PUBLISHED_OBSERVED_BENCHMARK_LEVEL", "MassiveDIS level misclassified")
    require(massive.get("observed_level") == 0.001 and massive.get("local_only") is True, "MassiveDIS local scope changed")
    require(massive.get("formal_uncertainty") is False and massive.get("complete_rate_claim") is False, "MassiveDIS overclaim")
    require(massive.get("allowed_future_ceiling_phrase") == "replication no worse than the published benchmark level", "MassiveDIS ceiling phrase changed")

    alpha = record.get("alpha_s_architecture", {})
    require(alpha.get("choice") == "AS2_CONTINUOUS_EQUIVALENCE_CERTIFICATION", "Wrong alpha architecture")
    require(alpha.get("status") == "PARTIAL_BLOCKER_REMAINS", "Alpha blocker hidden")
    require(alpha.get("as1_assessment", {}).get("technically_bindable") is False, "Invented AS1 API path")
    require(alpha.get("provider_a", {}).get("identity") == "CT18NLO DataVersion 1 member 0 LHAPDF 6.5.6 alphasQ", "Wrong CT18 alpha provider")
    provider_b = alpha.get("provider_b", {})
    require(provider_b.get("identity") == "APFEL 3.1.1 a_QCD exact NLO finite algorithm", "Wrong APFEL alpha provider")
    require(provider_b.get("controls") == EXPECTED_APFEL_CONTROLS, "APFEL alpha controls changed")
    require("10-step classical RK4" in provider_b.get("source_semantics", ""), "APFEL finite algorithm missing")
    require("4*pi" in provider_b.get("unresolved_output_conversion", ""), "Unresolved APFEL alpha conversion hidden")
    require(alpha.get("source_file_hashes") == EXPECTED_APFEL_SOURCE_HASHES, "APFEL source-file hashes changed")
    require(alpha.get("interval_backend_identity") is None, "Unverified interval backend asserted")
    certificate = alpha.get("continuous_certificate", {})
    require(certificate.get("status") == "NONAUTHORITATIVE_CANDIDATE_DESIGN", "Provisional alpha design promoted")
    require(certificate.get("algorithm_id") == "AS2_DYADIC_INTERVAL_REPLAY_V1_PROVISIONAL", "Alpha candidate identity missing")
    require(certificate.get("q2_domain_gev2") == [3.5, 50000], "Alpha domain changed")
    require("24 unique breakpoints, 23 roots" in certificate.get("breakpoints", ""), "Alpha interval coverage incomplete")
    require("depth <=12" in certificate.get("traversal", ""), "Alpha subdivision cap missing")
    require(certificate.get("pass") == "Every required upper(R)<=0.", "Alpha PASS rule changed")
    require(certificate.get("fail") == "Any lower(R)>0.", "Alpha FAIL rule changed")
    alpha_inconclusive = certificate.get("inconclusive", "")
    require(
        "undecided cell" in alpha_inconclusive and "pass" not in alpha_inconclusive.lower(),
        "Alpha INCONCLUSIVE rule missing",
    )
    require(len(certificate.get("specification_gaps", [])) == 4, "Alpha specification gaps hidden")
    require(alpha.get("blocker", {}).get("id") == "BLOCKER_ALPHA_EXECUTION_SPEC", "Alpha blocker identity missing")
    require(alpha.get("actual_result") == "NOT_EXECUTED", "Alpha study executed")

    pdf = record.get("pdf_artifact_contract", {})
    raw = pdf.get("raw", {})
    require(raw == EXPECTED_RAW_PDF, "Raw PDF contract changed")
    projected = pdf.get("projected", {})
    require(set(projected) == set(EXPECTED_PROJECTED_PDF) | {"anchors"}, "Projected PDF fields changed")
    for field, expected in EXPECTED_PROJECTED_PDF.items():
        require(projected.get(field) == expected, f"Projected PDF identity changed: {field}")
    require(anchor_tuples(projected.get("anchors")) == EXPECTED_ANCHORS, "Projected PDF anchors changed")
    require(projected.get("anchors") == accepted.get("theta_anchors"), "Accepted/projected anchor copies diverged")
    require("Failed D1/D1R evolved artifacts are not accepted" in pdf.get("failure_rule", ""), "Rejected evolved artifacts were accepted")

    bridge = record.get("bridge_contract", {})
    require(bridge.get("apfel_interface") == "SetPDFSet(external) -> exactly one strong ExternalSetAPFEL(x,Q,xf[-6:7]); Q is GeV and must equal Q0.", "Bridge callback interface changed")
    oracle = bridge.get("oracle", {})
    for field, expected in EXPECTED_BRIDGE_ORACLE.items():
        require(oracle.get(field) == expected, f"Bridge oracle identity changed: {field}")
    require(set(oracle) == set(EXPECTED_BRIDGE_ORACLE) | {"algorithm"}, "Bridge oracle fields changed")
    for field in ("path", "test_path"):
        require(sha256(root / oracle[field]) == oracle[field.replace("path", "sha256")], f"Bridge oracle bytes changed: {field}")
    algorithm = oracle.get("algorithm", "")
    for marker in ("exact signed dyadic integers", "round-to-nearest ties-to-even", "signed zero", "subnormal", "overflow", "NaN/infinite inputs are rejected"):
        require(marker in algorithm, f"Bridge oracle behavior missing: {marker}")
    require(bridge.get("flavor_slots") == EXPECTED_BRIDGE_SLOTS, "Bridge flavor-slot mapping changed")
    require(bridge.get("invariants") == EXPECTED_BRIDGE_INVARIANTS, "Bridge B1-B8 incomplete")
    sentinels = bridge.get("sentinels", {})
    require(sentinels.get("f_by_pdg") == EXPECTED_SENTINEL_F, "Bridge sentinel values changed")
    require(sentinels.get("x") == [0.5, 0.25], "Bridge sentinel x values changed")
    require(sentinels.get("expected_slot_order") == [-6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7], "Bridge sentinel slot order changed")
    require(sentinels.get("signed_zero_callback", {}).get("x") == 0.5, "Bridge signed-zero callback missing")
    require(len(bridge.get("identity_cases", [])) == 16, "Bridge identity cases incomplete")
    require(bridge.get("identity_cases", [None])[0] == "B1_VALID_EXACT_TUPLE", "Bridge valid identity case missing")
    require("every serialized raw and projected identity field" in bridge.get("identity_comparison", ""), "Bridge full identity comparison missing")
    require(len(bridge.get("support_cases", [])) == 4, "Bridge support cases incomplete")
    require(len(bridge.get("q_cases", [])) == 4, "Bridge Q cases incomplete")
    require(len(bridge.get("interface_cases", [])) == 2, "Bridge interface cases incomplete")
    for field, expected_hash in EXPECTED_BRIDGE_CASE_HASHES.items():
        require(canonical_sha256(bridge.get(field)) == expected_hash, f"Bridge exact case inventory changed: {field}")
    signed_zero = sentinels.get("signed_zero_callback", {})
    require(signed_zero.get("x") == 0.5 and "alternate bitwise +0,-0" in signed_zero.get("density_rule", ""), "Bridge signed-zero sentinel changed")
    require("structural slots -6,6,7 are bitwise +0" in signed_zero.get("expected_rule", ""), "Bridge structural-zero rule changed")
    require("exactly one RN-even binary64 x*f" in bridge.get("value_source", ""), "Bridge x/xf rule missing")
    require("bitwise equality" in bridge.get("floating_derivation", ""), "Bridge bitwise comparison missing")
    require("u=2^-53" in bridge.get("floating_derivation", ""), "Bridge unit-roundoff derivation missing")
    require(bridge.get("actual_result") == "NOT_EXECUTED", "Bridge test executed")

    sign = record.get("sign_contract", {})
    require(sign.get("choice") == "SIGN1_STRICT_IMPLEMENTED_RATE_NONNEGATIVITY", "Wrong sign contract")
    semantics = " ".join(sign.get("exact_semantics", [])).lower()
    for forbidden in ("no clipping", "abs", "max(rate,0)", "no replacement", "no deletion", "no epsilon", "no averaging", "no retry"):
        require(forbidden in semantics, f"Sign repair prohibition missing: {forbidden}")
    require("raw rate < 0 => fail" in semantics and "raw rate >= 0 => local sign pass" in semantics, "Strict raw sign rule changed")
    require(sign.get("actual_result") == "NOT_EXECUTED", "Sign scan executed")

    tests = record.get("post_authorization_tests", [])
    test_map = {item.get("test_id"): item for item in tests}
    require(len(tests) == len(test_map) and set(test_map) == EXPECTED_TESTS, "Post-auth TEST_* set incomplete")
    for test_id, item in test_map.items():
        extra_fields = {"non_authoritative_candidate_ceiling_ref"} if test_id == "TEST_ALPHA" else set()
        require(set(item) == REQUIRED_TEST_FIELDS | extra_fields, f"Incomplete post-auth test fields: {test_id}")
        require(item.get("status") in {"FULLY_SPECIFIED_NOT_EXECUTED", "BLOCKED_PREAUTH_SPECIFICATION", "BLOCKED_ACCEPTANCE_RULE", "BLOCKED_BY_UPSTREAM_RULES"}, f"Bad test status: {test_id}")
        require(item.get("status") == EXPECTED_TEST_STATUSES[test_id], f"Wrong post-auth test status: {test_id}")
        if item["status"] == "FULLY_SPECIFIED_NOT_EXECUTED":
            for field in ("implementation_identity", "inputs", "exact_finite_domain_grid", "metric", "threshold_or_rule", "near_zero_behavior", "pass", "fail", "inconclusive", "resource_count"):
                require(item.get(field) not in (None, "", [], {}), f"Fully specified test missing {field}: {test_id}")
            require(item.get("blocker") is None, f"Fully specified test has blocker: {test_id}")
        else:
            require(isinstance(item.get("blocker"), dict) and item["blocker"].get("id"), f"Blocked test lacks blocker: {test_id}")
    normalized_rule = test_map["TEST_NORMALIZED_LAW"].get("threshold_or_rule", "").lower()
    require("no standalone residual tolerance" in normalized_rule, "Standalone normalized-law tolerance introduced")

    massless = test_map["TEST_MASSLESS"]
    massless_grid = massless.get("exact_finite_domain_grid")
    require(isinstance(massless_grid, list) and len(massless_grid) == 27, "Massless grid must contain 27 rows")
    require(sum(len(row.get("published_tokens", {})) for row in massless_grid) == 81, "Massless grid must contain 81 tokens")
    require(canonical_sha256(massless_grid) == MASSLESS_GRID_SHA256, "Massless published table changed")
    require(massless.get("implementation_identity") is None, "Blocked massless implementation asserted")
    require(massless.get("metric") is None and massless.get("threshold_or_rule") is None and massless.get("pass") is None, "Blocked massless acceptance rule asserted")
    require(massless.get("blocker", {}).get("id") == "BLOCKER_MASSLESS_EXECUTION_SPEC", "Massless blocker identity missing")

    alpha_candidate_numeric = {
        "root_intervals": 23,
        "max_depth": 12,
        "total_cells": 188393,
        "ct18_interval_evaluations": 188393,
        "apfel_interval_evaluations": 188393,
        "apfel_beta_rhs_interval_evaluations": 9829200,
        "provider_api_probes": 58,
        "rigorous_log_series_terms": 3840,
        "total_declared_primitive_actions": 10209884,
    }
    require(test_map["TEST_ALPHA"]["resource_count"] is None, "Blocked alpha resource count fabricated")
    alpha_candidate = alpha.get("non_authoritative_candidate_ceiling", {})
    require(alpha_candidate.get("classification") == "NONAUTHORITATIVE_CANDIDATE_CEILING", "Alpha candidate ceiling promoted")
    require({key: alpha_candidate.get(key) for key in alpha_candidate_numeric} == alpha_candidate_numeric, "Alpha candidate arithmetic changed")
    require(alpha_candidate["total_cells"] == 23 * (2 ** 13 - 1), "Alpha candidate cell arithmetic is inconsistent")
    require(
        alpha_candidate["total_declared_primitive_actions"]
        == alpha_candidate["ct18_interval_evaluations"]
        + alpha_candidate["apfel_interval_evaluations"]
        + alpha_candidate["apfel_beta_rhs_interval_evaluations"]
        + alpha_candidate["provider_api_probes"]
        + alpha_candidate["rigorous_log_series_terms"],
        "Alpha candidate primitive-action sum is inconsistent",
    )
    bridge_count = test_map["TEST_BRIDGE"]["resource_count"]
    require(bridge_count == EXPECTED_BRIDGE_RESOURCES, "Bridge resource arithmetic changed")
    require(bridge_count["total_logical_cases"] == bridge_count["identity_cases"] + bridge_count["interface_checks"] + bridge_count["callback_attempts"], "Bridge logical-case sum is inconsistent")
    real_callbacks = len(EXPECTED_ANCHORS) * sum((17, 33, 65))
    require(real_callbacks == 1035, "Bridge real-callback derivation changed")
    require(bridge_count["slot_comparisons"] == (real_callbacks + 3) * len(EXPECTED_BRIDGE_SLOTS), "Bridge slot-comparison sum is inconsistent")
    require(bridge_count["evaluator_invocations"] == real_callbacks + 3 + 2, "Bridge evaluator-invocation sum is inconsistent")
    require(test_map["TEST_RAW_RATE_SIGN"]["resource_count"]["raw_rate_evaluations"] == 63882, "Rate-grid count changed")
    require(test_map["TEST_QUADRATURE_A"]["resource_count"]["integrand_evaluations"] == 48384, "Quadrature A count changed")
    require(test_map["TEST_QUADRATURE_B"]["resource_count"]["integrand_evaluations"] == 50427, "Quadrature B count changed")
    require(test_map["TEST_FONLL_COMPONENT"]["resource_count"] is None, "Blocked FONLL resource count fabricated")
    require(test_map["TEST_MASSLESS"]["resource_count"] is None, "Blocked massless resource count fabricated")

    coverage = record.get("reference_coverage_graph", [])
    coverage_map = {item.get("node"): item for item in coverage}
    require(len(coverage_map) == len(coverage) and set(coverage_map) == EXPECTED_COVERAGE, "Reference graph incomplete")
    require(all(item.get("load_bearing") is True for item in coverage), "Load-bearing reference node hidden")
    for node, expected_status in EXPECTED_REFERENCE_STATUSES.items():
        require(coverage_map[node].get("status") == expected_status, f"Wrong reference status: {node}")
        require(isinstance(coverage_map[node].get("evidence"), str) and coverage_map[node]["evidence"], f"Missing reference evidence: {node}")

    requirements = root / "analysis/requirements-phase2b-v3.txt"
    freeze = record.get("dependency_freeze", {})
    require(freeze.get("python") == {
        "implementation": "CPython",
        "version": "3.10.20",
        "source_sha256": "4ff5fd4c5bab803b935019f3e31d7219cebd6f870d00389cea53b88bbe935d1a",
        "executable_sha256": None,
    }, "Python runtime source identity changed")
    expected_packages = {
        "numpy": {
            "version": "2.2.6",
            "wheel": "numpy-2.2.6-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
            "sha256": "fc7b73d02efb0e18c000e9ad8b83480dfcd5dfd11065997ed4c6747470ae8915",
            "apis": ["numpy.asarray(dtype=numpy.float64)", "numpy.dot"],
        },
        "scipy": {
            "version": "1.15.3",
            "wheel": "scipy-1.15.3-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
            "sha256": "9e2abc762b0811e09a0d3258abee2d98e0c703eee49464ce0069590846f31d40",
            "apis": ["scipy.special.roots_legendre"],
        },
        "mpmath": {
            "version": "1.3.0",
            "wheel": "mpmath-1.3.0-py3-none-any.whl",
            "sha256": "a0b2b9fe80bbcd81a6647ff13108738cfb482d481d826cc0e02f5b35e5c88d2c",
            "apis": ["mp.dps", "mp.mpf"],
            "role": "diagnostic only, not rigorous interval backend",
        },
        "python_stdlib": {"apis": ["math.cos", "math.fsum", "math.nextafter"]},
    }
    require(freeze.get("packages") == expected_packages, "Pinned package wheel/API identity changed")
    require(freeze.get("requirements_file") == {
        "path": "analysis/requirements-phase2b-v3.txt",
        "sha256": "7fc226d93b4cb3ff7ac319f29162ce80867abfaa2ece50bb65f4e425ae1423ba",
    }, "Requirements-file identity changed")
    require(sha256(requirements) == "7fc226d93b4cb3ff7ac319f29162ce80867abfaa2ece50bb65f4e425ae1423ba", "V3 requirements bytes changed")
    requirement_text = requirements.read_text(encoding="utf-8")
    for marker in (
        "--only-binary=:all:",
        "--require-hashes",
        "numpy==2.2.6",
        "--hash=sha256:fc7b73d02efb0e18c000e9ad8b83480dfcd5dfd11065997ed4c6747470ae8915",
        "scipy==1.15.3",
        "--hash=sha256:9e2abc762b0811e09a0d3258abee2d98e0c703eee49464ce0069590846f31d40",
        "mpmath==1.3.0",
        "--hash=sha256:a0b2b9fe80bbcd81a6647ff13108738cfb482d481d826cc0e02f5b35e5c88d2c",
    ):
        require(marker in requirement_text, f"Requirements marker missing: {marker}")
    require(freeze.get("environment") == {"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}, "Numerical thread environment changed")
    require(freeze.get("non_load_bearing_packages") == ["pandas", "matplotlib", "pytest"], "Load-bearing dependency classification changed")
    require(freeze.get("status") == "PARTIAL_BLOCKER_REMAINS", "Runtime identity blocker hidden")
    require(len(freeze.get("unbound_runtime_identity", [])) == 5, "Unbound runtime identity inventory changed")
    require(freeze.get("runtime_blocker", {}).get("id") == "BLOCKER_NUMERICAL_RUNTIME_IDENTITY", "Runtime blocker identity missing")

    resources = record.get("resource_model", {})
    require(resources.get("discarded_totals") == [503284, 841685], "Predecessor resource totals reused")
    require(resources.get("predecessor_totals_authoritative") is False, "Predecessor total marked authoritative")
    per_test = resources.get("per_test", {})
    require(set(per_test) == EXPECTED_TESTS, "Resource per-test set changed")
    for test_id, test in test_map.items():
        require(per_test[test_id] == test.get("resource_count"), f"Resource cross-copy differs: {test_id}")
    resource_alpha_candidate = resources.get("non_authoritative_candidate_ceilings", {}).get("TEST_ALPHA", {})
    require(resource_alpha_candidate.get("classification") == "NONAUTHORITATIVE_CANDIDATE_CEILING", "Alpha candidate resource promoted")
    require({key: resource_alpha_candidate.get(key) for key in alpha_candidate_numeric} == alpha_candidate_numeric, "Alpha candidate resource cross-copy differs")
    require(resources.get("published_reference_inventory_not_execution_cost", {}).get("TEST_MASSLESS") == {"coordinate_records": 27, "displayed_scalar_tokens": 81}, "Massless publication inventory changed")
    require(resources.get("aggregate_maximum") is None, "Fabricated aggregate resource maximum")
    require(resources.get("aggregate_status") == "BLOCKED_NOT_DERIVABLE", "Aggregate blocker hidden")
    require(resources.get("all_required_tests_have_authoritative_finite_bounds") is False, "Missing resource counts hidden")
    require(resources.get("blocked_tests_without_authoritative_resource_counts") == ["TEST_ALPHA", "TEST_FONLL_COMPONENT", "TEST_MASSLESS"], "Blocked resource inventory changed")
    require(resources.get("unbounded_loop_allowed") is False, "Unbounded loop allowed")
    require(resources.get("retry_until_pass_allowed") is False, "Retry-until-pass allowed")
    require(resources.get("exhaustion_result") == "INCONCLUSIVE", "Resource exhaustion can pass")
    partial = resources.get("bounded_partial_vectors", {})
    require(partial.get("bridge_logical_cases") == EXPECTED_BRIDGE_RESOURCES["total_logical_cases"], "Bridge partial resource vector inconsistent")
    require(partial.get("unique_raw_rate_grid_evaluations") == 63882, "Rate partial resource vector inconsistent")
    require(partial.get("quadrature_a_integrand_evaluations") == 9 * (16**2 + 32**2 + 64**2), "Quadrature A resource arithmetic inconsistent")
    require(partial.get("quadrature_b_integrand_evaluations") == 9 * (17**2 + 33**2 + 65**2), "Quadrature B resource arithmetic inconsistent")
    require(partial.get("total_physics_rate_or_integrand_evaluations") == 63882 + 48384 + 50427 == 162693, "Partial physics resource vector inconsistent")
    require(partial.get("normalization_cached_operations") == 54 + 9 + 9 == 72, "Normalization cached arithmetic inconsistent")

    require(record.get("failure_precedence") == EXPECTED_PRECEDENCE, "Failure precedence changed")
    outcome = record.get("outcome", {})
    outcome_code = outcome.get("code")
    require(outcome_code in OUTCOMES, "Unknown V3 outcome")
    categories = {item.get("category") for item in outcome.get("blockers", [])}
    require(len(categories) == len(outcome.get("blockers", [])), "Duplicate outcome blocker category")
    if outcome_code == "V3R1_PREAUTH_V3_COMPLETE_READY_FOR_AUTHORIZATION_REVIEW":
        require(not any(item.get("status") == "UNVALIDATED" for item in coverage), "V3R1 with UNVALIDATED load-bearing node")
        require(all(item.get("status") == "FULLY_SPECIFIED_NOT_EXECUTED" for item in tests), "V3R1 with incomplete post-auth test")
        require(resources.get("aggregate_maximum") is not None, "V3R1 without aggregate resource maximum")
        require(not categories, "V3R1 with blocker categories")
        require(outcome.get("plan_completeness") == "COMPLETE", "V3R1 plan not complete")
        require(outcome.get("new_authorization_review_warranted") is True, "V3R1 does not warrant authorization review")
    else:
        require(outcome.get("plan_completeness") == "BLOCKED", "Blocked V3 marked complete")
        require(outcome.get("new_authorization_review_warranted") is False, "Authorization review incorrectly warranted")
        if outcome_code == "V3R2_ALPHA_S_CERTIFICATION_BLOCKED":
            require(categories == {"ALPHA_EXECUTION_SPECIFICATION"}, "V3R2 blocker derivation inconsistent")
        elif outcome_code == "V3R3_NUMERICAL_ACCEPTANCE_RULES_BLOCKED":
            require(categories == {"NUMERICAL_ACCEPTANCE_RULES"}, "V3R3 blocker derivation inconsistent")
        elif outcome_code == "V3R4_REFERENCE_OR_BRIDGE_BLOCKED":
            require(categories == {"REFERENCE_EXECUTION_SPECIFICATION"}, "V3R4 blocker derivation inconsistent")
        elif outcome_code == "V3R5_SIGN_CONTRACT_BLOCKED":
            require(categories == {"SIGN_CONTRACT"}, "V3R5 blocker derivation inconsistent")
        else:
            require(categories == EXPECTED_OUTCOME_CATEGORIES, "Multiple blocker derivation incomplete")
    if expected_outcome is not None:
        require(outcome_code == expected_outcome, "Wrong V3 outcome")

    authorization = record.get("authorization", {})
    require(authorization and all(value is False for value in authorization.values()), "Authorization flag is true")
    execution = record.get("execution_state", {})
    require(execution.get("phase2b") == "NOT_EXECUTED", "Phase 2B execution occurred")
    require(all(value is False for key, value in execution.items() if key != "phase2b"), "Forbidden physics execution recorded")
    require(record.get("github_target_state") == {"issue": 55, "state": "OPEN", "status": "Backlog", "gate_decision": "Not Evaluated", "authorization": "Not Authorized"}, "Issue #55 target state changed")
    require(record.get("source_policy", {}).get("publication_bytes_committed") is False, "Publication bytes claimed committed")

    if check_docs:
        markers = {
            "docs/reduced_nc_dis/PHASE2B_PREAUTHORIZATION_VALIDATION_PLAN_V3.md": [EXPECTED_OUTCOME, "AS2_CONTINUOUS_EQUIVALENCE_CERTIFICATION", "SIGN1_STRICT_IMPLEMENTED_RATE_NONNEGATIVITY", "NOT_EXECUTED"],
            "docs/CURRENT_PHASE.md": [EXPECTED_OUTCOME, "Phase 2B remains Not Authorized"],
            "docs/reduced_nc_dis/README.md": [EXPECTED_OUTCOME, "Not Authorized"],
            "docs/reduced_nc_dis/ROADMAP.md": [EXPECTED_OUTCOME, "Not Authorized"],
            "docs/adr/ADR-013-reduced-nc-dis-observation-law-contract.md": [EXPECTED_OUTCOME, "Historical Phase 2A remains `INCONCLUSIVE`"],
        }
        for relative, required in markers.items():
            text = (root / relative).read_text(encoding="utf-8")
            for marker in required:
                require(marker in text, f"Documentation marker missing from {relative}: {marker}")


def main() -> None:
    try:
        record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        validate(record)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise SystemExit(f"INVALID phase2b.preauthorization_validation_plan_v3: {error}") from error
    print("VALID phase2b.preauthorization_validation_plan_v3")


if __name__ == "__main__":
    main()
