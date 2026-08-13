"""Containment and rigor-guard tests for the Phase 2B interval oracles.

These tests exercise generic mathematical software on toy inputs.  They execute
no Phase 2B physics and they are not a substitute for later DIS closure
evidence.
"""

import sys
from fractions import Fraction
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analysis.validation import phase2b_interval_oracles as IV


TOY_BETA0 = IV.Interval.exact(2)
TOY_BETA1 = IV.Interval.exact(3)
TOY_INITIAL = IV.Interval.exact(Fraction(1, 10))
TRUNCATED_SIXTH = IV.Interval.exact(float("0.166666666666666"))


def point_rk4(value, step, beta0, beta1, steps, sixth):
    """A plain binary64 replay of the same fixed-step recursion."""

    for _ in range(steps):
        def rhs(x):
            return -x * x * (beta0 + x * beta1)

        k0 = step * rhs(value)
        k1 = step * rhs(value + 0.5 * k0)
        k2 = step * rhs(value + 0.5 * k1)
        k3 = step * rhs(value + k2)
        value = value + sixth * (k0 + 2 * k1 + 2 * k2 + k3)
    return value


def point_hermite(t, value_low, slope_low, value_high, slope_high):
    t2 = t * t
    t3 = t2 * t
    return (
        (2 * t3 - 3 * t2 + 1) * value_low
        + (t3 - 2 * t2 + t) * slope_low
        + (-2 * t3 + 3 * t2) * value_high
        + (t3 - t2) * slope_high
    )


# --------------------------------------------------------------------------
# interval algebra
# --------------------------------------------------------------------------


def test_endpoints_must_be_exact_rationals():
    with pytest.raises(TypeError):
        IV.Interval(0.5, 1.5)


def test_reversed_endpoints_rejected():
    with pytest.raises(ValueError):
        IV.Interval(Fraction(2), Fraction(1))


def test_arithmetic_contains_every_pointwise_product():
    left = IV.Interval(Fraction(-3), Fraction(2))
    right = IV.Interval(Fraction(-1), Fraction(4))
    product = left * right
    for a in (Fraction(-3), Fraction(-1), Fraction(0), Fraction(2)):
        for b in (Fraction(-1), Fraction(0), Fraction(3), Fraction(4)):
            assert product.contains(a * b)


def test_division_by_an_interval_containing_zero_is_refused():
    with pytest.raises(ZeroDivisionError):
        IV.Interval.exact(1) / IV.Interval(Fraction(-1), Fraction(1))


def test_dyadic_outward_only_widens():
    original = IV.Interval(Fraction(1, 3), Fraction(2, 3))
    widened = IV.dyadic_outward(original)
    assert widened.contains_interval(original)
    assert widened.width >= original.width


def test_dyadic_outward_refuses_absurd_precision():
    with pytest.raises(ValueError):
        IV.dyadic_outward(IV.Interval.exact(1), bits=4)


def test_binary64_round_enclosure_contains_the_rounded_value():
    for raw in (0.1, -2.5, 1e-320, 3.141592653589793, 5e-324):
        exact = IV.Interval.exact(Fraction(raw))
        assert IV.binary64_round_enclosure(exact).contains(Fraction(raw))


def test_binary64_operation_contains_the_binary64_result():
    left, right = 0.1, 0.30000000000000004
    for kind, expected in (
        ("add", left + right),
        ("sub", left - right),
        ("mul", left * right),
        ("div", left / right),
    ):
        enclosure = IV.binary64_operation(
            kind, IV.Interval.exact(left), IV.Interval.exact(right)
        )
        assert enclosure.contains(Fraction(expected)), kind


def test_unsupported_binary64_operation_rejected():
    with pytest.raises(ValueError):
        IV.binary64_operation("pow", IV.Interval.exact(2), IV.Interval.exact(3))


# --------------------------------------------------------------------------
# rigor guards
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(IV.RIGOROUS_TRANSCENDENTAL_BACKENDS))
def test_rigorous_backends_are_accepted(name):
    assert IV.assert_rigorous_transcendental_backend(name)


@pytest.mark.parametrize("name", sorted(IV.REJECTED_TRANSCENDENTAL_BACKENDS))
def test_high_precision_backends_are_refused(name):
    with pytest.raises(IV.NonRigorousBackendError):
        IV.assert_rigorous_transcendental_backend(name)


def test_unknown_backend_is_refused():
    with pytest.raises(IV.NonRigorousBackendError, match="no containment contract"):
        IV.assert_rigorous_transcendental_backend("homemade-interval-shim")


def test_mpmath_is_never_a_rigorous_backend():
    assert "mpmath" in IV.REJECTED_TRANSCENDENTAL_BACKENDS
    assert "mpmath.iv" in IV.REJECTED_TRANSCENDENTAL_BACKENDS
    assert "mpmath" not in IV.RIGOROUS_TRANSCENDENTAL_BACKENDS


def test_declared_log_bound_is_mandatory():
    exact = IV.Interval.exact(Fraction(1, 2))
    with pytest.raises(IV.UnjustifiedBoundError, match="no platform logarithm error bound"):
        IV.declared_ulp_log_enclosure(exact, None, "anything")


def test_declared_log_bound_needs_an_authority():
    exact = IV.Interval.exact(Fraction(1, 2))
    with pytest.raises(IV.UnjustifiedBoundError, match="stated authority"):
        IV.declared_ulp_log_enclosure(exact, Fraction(52, 100), "   ")


def test_declared_log_bound_must_be_nonnegative():
    exact = IV.Interval.exact(Fraction(1, 2))
    with pytest.raises(IV.UnjustifiedBoundError, match="nonnegative"):
        IV.declared_ulp_log_enclosure(exact, Fraction(-1), "an authority")


def test_declared_log_bound_widens_outward():
    exact = IV.Interval.exact(Fraction(1, 2))
    widened = IV.declared_ulp_log_enclosure(
        exact, Fraction(52, 100), "glibc 2.39 e_log.c stated worst-case error"
    )
    assert widened.contains_interval(exact)
    assert widened.width > 0


# --------------------------------------------------------------------------
# branch classification
# --------------------------------------------------------------------------


def test_clamp_branch_below():
    assert IV.magnitude_clamp_branch(IV.Interval(Fraction(1, 10), Fraction(2, 10)), Fraction(2)) == "BELOW"


def test_clamp_branch_at_or_above():
    assert IV.magnitude_clamp_branch(IV.Interval(Fraction(5), Fraction(6)), Fraction(2)) == "AT_OR_ABOVE"


def test_clamp_branch_undecided_forces_subdivision():
    assert IV.magnitude_clamp_branch(IV.Interval(Fraction(1), Fraction(3)), Fraction(2)) == "UNDECIDED"


def test_clamp_branch_spanning_zero_is_not_silently_above():
    straddling = IV.Interval(Fraction(-5), Fraction(5))
    assert IV.magnitude_clamp_branch(straddling, Fraction(2)) == "UNDECIDED"


def test_clamp_threshold_must_be_positive():
    with pytest.raises(ValueError):
        IV.magnitude_clamp_branch(IV.Interval.exact(1), Fraction(0))


# --------------------------------------------------------------------------
# enclosures contain their binary64 replays
# --------------------------------------------------------------------------


def test_hermite_enclosure_contains_binary64_replay():
    coefficients = [IV.Interval.exact(v) for v in (0.2154, -0.0113, 0.2041, -0.0106)]
    enclosure = IV.subdivision_enclosure(
        Fraction(0),
        Fraction(1),
        16,
        lambda cell: IV.hermite_cubic_enclosure(cell, *coefficients),
    )
    for index in range(201):
        t = index / 200
        assert enclosure.contains(Fraction(point_hermite(t, 0.2154, -0.0113, 0.2041, -0.0106)))


def test_fixed_step_rk4_enclosure_contains_binary64_replay():
    enclosure = IV.subdivision_enclosure(
        Fraction(1, 100),
        Fraction(2, 100),
        16,
        lambda cell: IV.fixed_step_rk4_enclosure(
            TOY_INITIAL, cell, TOY_BETA0, TOY_BETA1, steps=10, sixth=TRUNCATED_SIXTH
        ),
    )
    for index in range(101):
        step = 0.01 + 0.01 * index / 100
        assert enclosure.contains(
            Fraction(point_rk4(0.1, step, 2.0, 3.0, 10, float("0.166666666666666")))
        )


def test_rk4_enclosure_tightens_under_subdivision():
    widths = []
    for cells in (1, 4, 16, 64):
        enclosure = IV.subdivision_enclosure(
            Fraction(1, 100),
            Fraction(2, 100),
            cells,
            lambda cell: IV.fixed_step_rk4_enclosure(
                TOY_INITIAL, cell, TOY_BETA0, TOY_BETA1, steps=10, sixth=TRUNCATED_SIXTH
            ),
        )
        widths.append(enclosure.width)
    assert widths == sorted(widths, reverse=True)


def test_rk4_requires_at_least_one_step():
    with pytest.raises(ValueError):
        IV.fixed_step_rk4_enclosure(
            TOY_INITIAL,
            IV.Interval.exact(Fraction(1, 100)),
            TOY_BETA0,
            TOY_BETA1,
            steps=0,
            sixth=TRUNCATED_SIXTH,
        )


def test_truncated_sixth_literal_changes_the_recursion():
    step = IV.Interval.exact(Fraction(3, 200))
    truncated = IV.fixed_step_rk4_enclosure(
        TOY_INITIAL, step, TOY_BETA0, TOY_BETA1, steps=10, sixth=TRUNCATED_SIXTH
    )
    exact = IV.fixed_step_rk4_enclosure(
        TOY_INITIAL,
        step,
        TOY_BETA0,
        TOY_BETA1,
        steps=10,
        sixth=IV.Interval.exact(Fraction(1, 6)),
    )
    assert truncated.lower != exact.lower
    assert float("0.166666666666666") != 1 / 6


def test_cubic_beta_rhs_uses_no_transcendental():
    result = IV.cubic_beta_rhs_enclosure(
        IV.Interval(Fraction(1, 10), Fraction(2, 10)), TOY_BETA0, TOY_BETA1
    )
    assert result.upper < 0


def test_subdivision_requires_a_positive_cell_count():
    with pytest.raises(ValueError):
        IV.subdivision_enclosure(Fraction(0), Fraction(1), 0, lambda cell: cell)


def test_subdivision_rejects_reversed_bounds():
    with pytest.raises(ValueError):
        IV.subdivision_enclosure(Fraction(1), Fraction(0), 4, lambda cell: cell)
