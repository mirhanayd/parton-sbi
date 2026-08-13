"""Grid nesting and convergence-rule tests, plus analytic quadrature mechanics.

These tests exercise generic mathematical software on functions whose exact
integrals are known.  They execute no Phase 2B physics, and they establish
nothing about the future DIS integrand.
"""

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analysis.validation import phase2b_grid_oracles as GRID
from analysis.validation import phase2b_quadrature_oracles as QUAD

X_DOMAIN = (6e-7, 0.65)
Q2_DOMAIN = (3.5, 50000.0)


# --------------------------------------------------------------------------
# node generation and nesting
# --------------------------------------------------------------------------


def test_geometric_nodes_hit_both_endpoints():
    nodes = GRID.geometric_nodes(17, *X_DOMAIN)
    assert nodes[0] == X_DOMAIN[0]
    assert nodes[-1] == pytest.approx(X_DOMAIN[1], rel=1e-15)


def test_geometric_nodes_are_increasing():
    nodes = GRID.geometric_nodes(33, *Q2_DOMAIN)
    assert list(nodes) == sorted(nodes)


def test_geometric_nodes_reject_degenerate_input():
    with pytest.raises(ValueError):
        GRID.geometric_nodes(1, *X_DOMAIN)
    with pytest.raises(ValueError):
        GRID.geometric_nodes(17, 0.0, 1.0)
    with pytest.raises(ValueError):
        GRID.geometric_nodes(17, 1.0, 0.5)


def test_17_33_65_levels_are_bitwise_nested_on_the_x_axis():
    nested, failures = GRID.levels_are_bitwise_nested([17, 33, 65], *X_DOMAIN)
    assert nested, failures


def test_17_33_65_levels_are_bitwise_nested_on_the_q2_axis():
    nested, failures = GRID.levels_are_bitwise_nested([17, 33, 65], *Q2_DOMAIN)
    assert nested, failures


def test_nesting_is_a_property_that_must_be_tested_not_assumed():
    nested, failures = GRID.levels_are_bitwise_nested([16, 32, 64], *X_DOMAIN)
    assert not nested
    assert failures


# --------------------------------------------------------------------------
# refinement records carry no bound
# --------------------------------------------------------------------------


def test_refinement_record_labels_itself_as_stability_only():
    record = GRID.refinement_record("Zmin", [1.0, 1.001, 1.0011])
    assert record.interpretation == GRID.DIFFERENCE_INTERPRETATION
    assert "NOT_A_REMAINDER_BOUND" in record.interpretation


def test_refinement_record_uses_absolute_differences():
    record = GRID.refinement_record("signed", [1.0, -1.0, 0.0])
    assert record.first_difference == 2.0
    assert record.second_difference == 1.0


def test_refinement_record_needs_exactly_three_levels():
    with pytest.raises(ValueError):
        GRID.refinement_record("Zmin", [1.0, 2.0])


def test_convergence_verdict_refuses_a_missing_target():
    record = GRID.refinement_record("Zmin", [1.0, 1.001, 1.0011])
    with pytest.raises(GRID.MissingPrecisionTargetError, match="no declared absolute precision"):
        GRID.convergence_verdict(record, None, "some reason")


def test_convergence_verdict_refuses_an_unjustified_target():
    record = GRID.refinement_record("Zmin", [1.0, 1.001, 1.0011])
    with pytest.raises(GRID.MissingPrecisionTargetError, match="stated reason"):
        GRID.convergence_verdict(record, 1e-3, "   ")


@pytest.mark.parametrize("target", [0.0, -1.0, float("inf"), float("nan")])
def test_convergence_verdict_refuses_a_degenerate_target(target):
    record = GRID.refinement_record("Zmin", [1.0, 1.001, 1.0011])
    with pytest.raises(GRID.MissingPrecisionTargetError):
        GRID.convergence_verdict(record, target, "a declared reason")


def test_convergence_verdict_fails_on_nonfinite_data():
    record = GRID.refinement_record("Zmin", [1.0, float("nan"), 1.0])
    assert GRID.convergence_verdict(record, 1e-3, "a declared reason") == "FAIL"


def test_convergence_verdict_is_decided_only_with_a_declared_target():
    record = GRID.refinement_record("Zmin", [1.0, 1.001, 1.0011])
    assert GRID.convergence_verdict(record, 1e-3, "a declared reason") == "PASS"
    assert GRID.convergence_verdict(record, 1e-5, "a declared reason") == "FAIL"


def test_growing_differences_are_inconclusive_not_passing():
    record = GRID.refinement_record("Zmin", [1.0, 1.0001, 1.001])
    assert GRID.convergence_verdict(record, 1e-2, "a declared reason") == "INCONCLUSIVE"


# --------------------------------------------------------------------------
# cross-path comparison
# --------------------------------------------------------------------------


def test_cross_path_overlap_requires_certified_radii():
    with pytest.raises(ValueError):
        GRID.cross_path_overlap(1.0, -1e-6, 1.0, 1e-6)
    with pytest.raises(ValueError):
        GRID.cross_path_overlap(1.0, float("nan"), 1.0, 1e-6)


def test_cross_path_overlap_decides_on_certified_intervals():
    assert GRID.cross_path_overlap(1.0, 1e-6, 1.0 + 5e-7, 1e-6) == "PASS"
    assert GRID.cross_path_overlap(1.0, 1e-9, 1.0 + 5e-7, 1e-9) == "FAIL"


# --------------------------------------------------------------------------
# analytic quadrature mechanics
# --------------------------------------------------------------------------


ANALYTIC_CASES = [
    ("polynomial", lambda x: x**7 - 3 * x**3 + 1, -1.0, 1.0, 2.0, 1e-13),
    ("exponential", math.exp, -1.0, 1.0, math.e - 1 / math.e, 1e-13),
    (
        "smooth_rational",
        lambda x: 1 / (1 + 25 * x * x),
        -1.0,
        1.0,
        2 * math.atan(5) / 5,
        1e-9,
    ),
]


@pytest.mark.parametrize("name,fn,lo,hi,exact,tolerance", ANALYTIC_CASES)
def test_gauss_legendre_reproduces_known_integrals(name, fn, lo, hi, exact, tolerance):
    assert abs(QUAD.scipy_gauss_legendre_integrate(fn, 64, lo, hi) - exact) < tolerance


@pytest.mark.parametrize("name,fn,lo,hi,exact,tolerance", ANALYTIC_CASES)
def test_clenshaw_curtis_reproduces_known_integrals(name, fn, lo, hi, exact, tolerance):
    assert abs(QUAD.clenshaw_curtis_integrate(fn, 65, lo, hi) - exact) < tolerance


def test_endpoint_sensitive_analytic_case_is_not_resolved_at_these_levels():
    """A pole just outside the interval defeats both rules at the planned levels."""

    def fn(x):
        return 1 / (x + 1.0001)

    exact = math.log(2.0001 / 0.0001)
    assert abs(QUAD.scipy_gauss_legendre_integrate(fn, 64, -1.0, 1.0) - exact) > 0.1
    assert abs(QUAD.clenshaw_curtis_integrate(fn, 65, -1.0, 1.0) - exact) > 0.1


def test_successive_difference_agreement_does_not_bound_the_remainder():
    """Both rules agree perfectly with themselves and each other, and are wrong.

    The integrand is entire.  Its mass sits between the nodes of every planned
    level, so all six rules return exactly zero while the true integral does
    not.  This is a statement about the rule, not about the DIS integrand.
    """

    centre, width = 0.1824, 1e-4

    def bump(x):
        return math.exp(-(((x - centre) / width) ** 2))

    exact = (
        width
        * math.sqrt(math.pi)
        / 2
        * (math.erf((1 - centre) / width) - math.erf((-1 - centre) / width))
    )
    assert exact > 1e-4

    gauss = [QUAD.scipy_gauss_legendre_integrate(bump, order, -1.0, 1.0) for order in (16, 32, 64)]
    clenshaw = [QUAD.clenshaw_curtis_integrate(bump, count, -1.0, 1.0) for count in (17, 33, 65)]

    assert gauss == [0.0, 0.0, 0.0]
    assert clenshaw == [0.0, 0.0, 0.0]

    gauss_record = GRID.refinement_record("Z_A", gauss)
    clenshaw_record = GRID.refinement_record("Z_B", clenshaw)
    assert gauss_record.first_difference == 0.0
    assert gauss_record.second_difference == 0.0
    assert clenshaw_record.first_difference == 0.0
    assert clenshaw_record.second_difference == 0.0

    # Independent cross-rule agreement is likewise perfect and likewise wrong.
    assert abs(gauss[-1] - clenshaw[-1]) == 0.0
    assert abs(gauss[-1] - exact) == pytest.approx(exact)
