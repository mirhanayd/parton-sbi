import ast
import copy
import importlib.util
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/validate_phase2b_preauthorization_validation_plan_v2.py"
ARTIFACT = ROOT / "docs/reduced_nc_dis/contracts/phase2b_preauthorization_validation_plan_v2.json"
QUADRATURE = ROOT / "analysis/validation/phase2b_quadrature_oracles.py"

SPEC = importlib.util.spec_from_file_location("phase2b_preauth_v2_validator", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

QUAD_SPEC = importlib.util.spec_from_file_location("phase2b_quadrature_oracles", QUADRATURE)
assert QUAD_SPEC and QUAD_SPEC.loader
QUAD = importlib.util.module_from_spec(QUAD_SPEC)
QUAD_SPEC.loader.exec_module(QUAD)


@pytest.fixture
def record():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def rejected(candidate, expected_message):
    with pytest.raises(VALIDATOR.ValidationError, match=expected_message):
        VALIDATOR.validate(candidate, root=ROOT, check_docs=False)


def test_cli_validates_current_v2_artifact():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "VALID phase2b.preauthorization_validation_plan_v2" in result.stdout


@pytest.mark.parametrize(
    ("factory", "integrator", "levels"),
    [
        (QUAD.scipy_gauss_legendre_rule, QUAD.scipy_gauss_legendre_integrate, [16, 32, 64]),
        (QUAD.clenshaw_curtis_rule, QUAD.clenshaw_curtis_integrate, [17, 33, 65]),
    ],
)
def test_generic_quadrature_rules_integrate_analytic_monomials(factory, integrator, levels):
    for level in levels:
        nodes, weights = factory(level)
        assert len(nodes) == len(weights) == level
        assert all(math.isfinite(value) for value in (*nodes, *weights))
        assert all(weight > 0 for weight in weights)
        direction = math.copysign(1.0, nodes[1] - nodes[0])
        assert all(
            math.copysign(1.0, right - left) == direction
            for left, right in zip(nodes, nodes[1:])
        )
        assert all(
            math.isclose(left, -right, rel_tol=0.0, abs_tol=2e-15)
            for left, right in zip(nodes, reversed(nodes), strict=True)
        )
        assert all(
            math.isclose(left, right, rel_tol=0.0, abs_tol=2e-15)
            for left, right in zip(weights, reversed(weights), strict=True)
        )
        assert math.isclose(math.fsum(weights), 2.0, rel_tol=0.0, abs_tol=2e-14)
        for power in range(13):
            observed = integrator(lambda x, p=power: x**p, level)
            expected = 0.0 if power % 2 else 2.0 / (power + 1)
            assert math.isclose(observed, expected, rel_tol=0.0, abs_tol=5e-13)
        assert math.isclose(integrator(math.exp, level), 2.0 * math.sinh(1.0), rel_tol=0.0, abs_tol=5e-13)


def test_clenshaw_curtis_path_has_no_scipy_or_numpy_quadrature_core():
    module = ast.parse(QUADRATURE.read_text(encoding="utf-8"))
    functions = [
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"clenshaw_curtis_rule", "clenshaw_curtis_integrate"}
    ]
    identifiers = {
        value
        for function in functions
        for child in ast.walk(function)
        for value in (
            child.id.lower() if isinstance(child, ast.Name) else None,
            child.attr.lower() if isinstance(child, ast.Attribute) else None,
        )
        if value is not None
    }
    assert not identifiers.intersection({"scipy", "numpy", "roots_legendre", "leggauss"})


def test_historical_v1_byte_change_is_rejected(record, tmp_path):
    for _, (relative, _) in VALIDATOR.EXPECTED_PREDECESSORS.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    module_target = tmp_path / "analysis/validation/phase2b_quadrature_oracles.py"
    module_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(QUADRATURE, module_target)
    v1 = tmp_path / VALIDATOR.EXPECTED_PREDECESSORS["preauthorization_v1"][0]
    v1.write_bytes(v1.read_bytes() + b"\n")
    with pytest.raises(VALIDATOR.ValidationError, match="Historical predecessor bytes changed: preauthorization_v1"):
        VALIDATOR.validate(record, root=tmp_path, check_docs=False)


def test_rv1_with_as3_is_rejected(record):
    record["alpha_s_architecture"]["choice"] = "AS3_ALPHA_S_ARCHITECTURE_UNRESOLVED"
    rejected(record, "Wrong alpha_s architecture")


def test_rv1_with_unresolved_bridge_is_rejected(record):
    record["pdf_apfel_bridge_contract"]["classification"] = "BRIDGE_ARCHITECTURE_UNRESOLVED"
    rejected(record, "Bridge architecture unresolved")


def test_rv1_with_unvalidated_reference_node_is_rejected(record):
    record["independent_reference_coverage"][0]["classification"] = "UNVALIDATED"
    rejected(record, "RV1 with UNVALIDATED load-bearing node")


def test_fake_wrapper_independence_is_rejected(record):
    record["quadrature_contract"]["shared_node_weight_or_accumulation_core_allowed"] = True
    rejected(record, "Shared quadrature core allowed")


def test_same_quadrature_implementation_under_two_names_is_rejected(record):
    record["quadrature_contract"]["path_b"]["implementation"] = record["quadrature_contract"]["path_a"]["implementation"]
    rejected(record, "Wrong quadrature B implementation")


def test_shared_quadrature_accumulation_entrypoint_is_rejected(record):
    record["quadrature_contract"]["path_b"]["integration_entrypoint"] = record["quadrature_contract"]["path_a"]["integration_entrypoint"]
    rejected(record, "Wrong quadrature B integration entrypoint")


def test_massivedis_precision_without_structure_function_budget_is_rejected(record):
    record["massivedisfunction_assessment"]["future_configuration"] = "Use the default precision."
    rejected(record, "MassiveDISsFunction precision budget unbound")


def test_factor_ten_only_tolerance_is_rejected(record):
    record["comparator_tolerances"][0]["derivation"] = "Chosen as a factor ten below another number."
    rejected(record, "Factor-ten-only tolerance")


def test_tolerance_without_near_zero_behavior_is_rejected(record):
    record["comparator_tolerances"][0]["near_zero"] = ""
    rejected(record, "Tolerance field missing")


def test_wrong_object_alpha_machine_epsilon_tolerance_is_rejected(record):
    alpha = next(
        item
        for item in record["comparator_tolerances"]
        if item["tolerance_id"] == "TOL_ALPHA_S_PROVIDER_EQUIVALENCE"
    )
    alpha["rtol"] = "72*2^-53"
    rejected(record, "Wrong-object alpha_s epsilon tolerance")


def test_alpha_provider_precision_envelope_is_required(record):
    record["alpha_s_architecture"]["future_equivalence_test"]["apfel_precision_envelope"] = "32 binary64 roundoffs"
    rejected(record, "APFEL provider precision envelope missing")


def test_gamma32_only_full_rate_policy_is_rejected(record):
    record["negative_rate_policy"]["total_formula"] = "E_total=E_outer=gamma_32*S_assembly"
    rejected(record, "Incomplete propagated sign envelope")


def test_negative_to_zero_conversion_is_rejected(record):
    record["negative_rate_policy"]["classification"]["rate_below_negative_envelope"] = "REPLACE_WITH_ZERO"
    rejected(record, "Negative envelope no longer fails")


def test_inconclusive_sign_counted_as_pass_is_rejected(record):
    record["negative_rate_policy"]["global_semantics"] = "INCONCLUSIVE_SIGN counts as PASS"
    rejected(record, "INCONCLUSIVE_SIGN counted as PASS")


def test_arbitrary_normalized_law_0013_is_rejected(record):
    record["normalized_law_error_propagation"]["closure_bound"] = "absolute 0.0013"
    rejected(record, "Arbitrary v1 0.0013 retained")


def test_missing_error_budget_component_is_rejected(record):
    record["numerical_error_budget"]["components"].pop()
    rejected(record, "Missing error-budget component")


def test_budget_sum_exceeding_parent_is_rejected(record):
    record["numerical_error_budget"]["components"][0]["relative_share"] = 0.000126
    rejected(record, "Error-budget sum exceeds parent allowance")


def test_authorization_true_is_rejected(record):
    record["authorization"]["PHASE2B_AUTHORIZED"] = True
    rejected(record, "Authorization flag is true")


def test_execution_true_is_rejected(record):
    record["execution_state"]["phase2b"] = "EXECUTED"
    rejected(record, "Phase 2B execution occurred")


def test_phase2c_authorization_is_rejected(record):
    record["authorization"]["PHASE2C_AUTHORIZED"] = True
    rejected(record, "Authorization flag is true")


def test_pdf_family_drift_is_rejected(record):
    record["accepted_contract"]["pdf_family"] = "another_family"
    rejected(record, "Accepted PDF family changed")


def test_historical_phase2a_pass_is_rejected(record):
    record["historical_state"]["phase2a_scientific_decision"] = "PASS"
    rejected(record, "Historical Phase 2A changed to PASS")


def test_source_hash_drift_is_rejected(record):
    record["source_registry_additions"][0]["byte_streams"][0]["sha256"] = "0" * 64
    rejected(record, "Wrong source hash")


def test_issue_55_authorization_change_is_rejected(record):
    record["github_target_state"]["authorization"] = "Authorized"
    rejected(record, "Issue #55 target state changed")
