"""Rigorous rational interval arithmetic reserved for a later Phase 2B task.

This module is generic mathematical software.  It does not import an APFEL or
LHAPDF binding, does not construct a DIS integrand, does not read a PDF member,
and does not execute any Phase 2B physics.  Every routine here operates on toy
inputs supplied by the caller.

Scope of the guarantee
----------------------
``Interval`` endpoints are exact :class:`fractions.Fraction` values, so the four
rational operations are exact and the resulting enclosures are rigorous without
any directed-rounding library.  :func:`binary64_round_enclosure` widens an exact
rational enclosure into one that provably contains the IEEE-754 binary64
round-to-nearest image of every real number in the input, which is what a
faithful model of a frozen binary64 program requires.

What this module deliberately does *not* provide is a transcendental function.
The two frozen Phase 2B coupling providers each evaluate exactly one
transcendental, a natural logarithm, and everything downstream of it is built
from ``+``, ``-``, ``*`` and ``/`` only.  A rigorous logarithm enclosure must
therefore come from a declared external backend, and
:func:`assert_rigorous_transcendental_backend` refuses the high-precision
substitutes that are frequently mistaken for one.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

# IEEE-754 binary64 constants used by the rounding model.
BINARY64_UNIT_ROUNDOFF = Fraction(1, 2**53)
BINARY64_MIN_SUBNORMAL_HALF = Fraction(1, 2**1075)

#: Significant bits retained when endpoints are normalised outward.  Exact
#: rational endpoints are rigorous but their denominators grow without bound
#: through a long recursion, so every derived interval is widened onto a dyadic
#: grid.  Widening only ever loses tightness, never containment.
WORKING_PRECISION_BITS = 192

#: Backends whose published contract is a rigorous enclosure.  The value is the
#: reason the backend qualifies.
RIGOROUS_TRANSCENDENTAL_BACKENDS = {
    "python-flint.arb": (
        "Arb ball arithmetic carries an explicit radius and every documented "
        "operation returns a ball provably containing the exact result."
    ),
    "mpfi": (
        "MPFI implements directed-rounding interval arithmetic on top of MPFR "
        "and documents containment for its elementary functions."
    ),
}

#: Backends that are routinely mislabelled as rigorous.  The value is the reason
#: the label is wrong.
REJECTED_TRANSCENDENTAL_BACKENDS = {
    "mpmath": (
        "Arbitrary-precision floating point is not interval arithmetic; a "
        "precise point value carries no containment certificate."
    ),
    "mpmath.iv": (
        "mpmath interval transcendental rounding is not a documented rigorous "
        "enclosure and is excluded by the accepted Phase 2B records."
    ),
    "math": "The standard library delegates to the platform libm and returns a point.",
    "numpy": "NumPy delegates to the platform libm and returns a point.",
    "decimal": "Decimal is exact-decimal point arithmetic, not an enclosure.",
}


class NonRigorousBackendError(RuntimeError):
    """Raised when a non-enclosing backend is offered as a rigorous one."""


class UnjustifiedBoundError(ValueError):
    """Raised when an enclosure is requested without a declared justification."""


def assert_rigorous_transcendental_backend(name: str) -> str:
    """Return the acceptance reason for ``name`` or refuse it.

    Higher precision is not containment.  A backend qualifies only when its own
    published contract is that the returned object encloses the exact result.
    """

    if name in RIGOROUS_TRANSCENDENTAL_BACKENDS:
        return RIGOROUS_TRANSCENDENTAL_BACKENDS[name]
    if name in REJECTED_TRANSCENDENTAL_BACKENDS:
        raise NonRigorousBackendError(
            f"{name} is not a rigorous interval backend: "
            f"{REJECTED_TRANSCENDENTAL_BACKENDS[name]}"
        )
    raise NonRigorousBackendError(
        f"{name} is not a declared interval backend; no containment contract is known"
    )


@dataclass(frozen=True)
class Interval:
    """A closed real interval with exact rational endpoints."""

    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        if not isinstance(self.lower, Fraction) or not isinstance(self.upper, Fraction):
            raise TypeError("interval endpoints must be exact Fraction values")
        if self.lower > self.upper:
            raise ValueError("interval lower endpoint exceeds its upper endpoint")

    @staticmethod
    def exact(value: int | float | Fraction) -> "Interval":
        """Return the degenerate interval holding ``value`` exactly."""

        exact_value = Fraction(value)
        return Interval(exact_value, exact_value)

    @staticmethod
    def hull(values: Sequence[Fraction]) -> "Interval":
        if not values:
            raise ValueError("hull of an empty sequence is undefined")
        return Interval(min(values), max(values))

    @property
    def width(self) -> Fraction:
        return self.upper - self.lower

    def contains(self, value: int | float | Fraction) -> bool:
        return self.lower <= Fraction(value) <= self.upper

    def contains_interval(self, other: "Interval") -> bool:
        return self.lower <= other.lower and other.upper <= self.upper

    def __add__(self, other: "Interval") -> "Interval":
        return Interval(self.lower + other.lower, self.upper + other.upper)

    def __sub__(self, other: "Interval") -> "Interval":
        return Interval(self.lower - other.upper, self.upper - other.lower)

    def __mul__(self, other: "Interval") -> "Interval":
        products = (
            self.lower * other.lower,
            self.lower * other.upper,
            self.upper * other.lower,
            self.upper * other.upper,
        )
        return Interval(min(products), max(products))

    def __truediv__(self, other: "Interval") -> "Interval":
        if other.contains(0):
            raise ZeroDivisionError("interval division by an interval containing zero")
        quotients = (
            self.lower / other.lower,
            self.lower / other.upper,
            self.upper / other.lower,
            self.upper / other.upper,
        )
        return Interval(min(quotients), max(quotients))

    def __neg__(self) -> "Interval":
        return Interval(-self.upper, -self.lower)


def _dyadic_floor(value: Fraction, exponent: int) -> Fraction:
    """Largest multiple of ``2**exponent`` not exceeding ``value``."""

    numerator, denominator = value.numerator, value.denominator
    if exponent >= 0:
        quotient = numerator // (denominator << exponent)
    else:
        quotient = (numerator << -exponent) // denominator
    return Fraction(quotient << exponent) if exponent >= 0 else Fraction(quotient, 1 << -exponent)


def dyadic_outward(value: Interval, bits: int = WORKING_PRECISION_BITS) -> Interval:
    """Widen ``value`` onto a dyadic grid holding roughly ``bits`` significant bits.

    The lower endpoint moves down and the upper endpoint moves up, so the result
    always contains the input.  Only tightness is traded away, which keeps every
    downstream containment claim valid while bounding endpoint size.
    """

    if bits < 8:
        raise ValueError("outward normalisation needs at least eight significant bits")
    magnitude = max(abs(value.lower), abs(value.upper))
    if magnitude == 0:
        return value
    exponent = (
        magnitude.numerator.bit_length() - magnitude.denominator.bit_length() - bits
    )
    lower = _dyadic_floor(value.lower, exponent)
    upper = -_dyadic_floor(-value.upper, exponent)
    return Interval(lower, upper)


def binary64_round_enclosure(value: Interval) -> Interval:
    """Enclose the binary64 round-to-nearest image of every real in ``value``.

    For every real ``z`` the IEEE-754 binary64 round-to-nearest result satisfies
    ``|RN(z) - z| <= u*|z| + eta`` with ``u = 2**-53`` and ``eta = 2**-1075``.
    The ``eta`` term covers the subnormal range, where the relative bound alone
    does not hold.  Overflow is not modelled: a caller whose operands can reach
    the binary64 overflow boundary must handle that branch explicitly.
    """

    magnitude = max(abs(value.lower), abs(value.upper))
    slack = BINARY64_UNIT_ROUNDOFF * magnitude + BINARY64_MIN_SUBNORMAL_HALF
    return dyadic_outward(Interval(value.lower - slack, value.upper + slack))


def binary64_operation(kind: str, left: Interval, right: Interval) -> Interval:
    """Enclose one rounded binary64 arithmetic operation."""

    if kind == "add":
        exact = left + right
    elif kind == "sub":
        exact = left - right
    elif kind == "mul":
        exact = left * right
    elif kind == "div":
        exact = left / right
    else:
        raise ValueError(f"unsupported binary64 operation {kind!r}")
    return binary64_round_enclosure(exact)


def declared_ulp_log_enclosure(
    exact_log: Interval,
    ulp_bound: Fraction | None,
    justification: str,
) -> Interval:
    """Widen an exact logarithm enclosure by a declared implementation error.

    A frozen program does not evaluate the mathematical logarithm; it calls a
    platform routine whose result differs from it.  Modelling that requires a
    bound on the platform routine.  This helper refuses to invent one: both
    ``ulp_bound`` and a non-empty ``justification`` naming the authority for the
    bound are mandatory.
    """

    if ulp_bound is None:
        raise UnjustifiedBoundError(
            "no platform logarithm error bound was declared; a rigorous "
            "enclosure of an implemented logarithm cannot be formed"
        )
    if not justification.strip():
        raise UnjustifiedBoundError("a declared logarithm error bound needs a stated authority")
    if ulp_bound < 0:
        raise UnjustifiedBoundError("a logarithm error bound must be nonnegative")
    magnitude = max(abs(exact_log.lower), abs(exact_log.upper))
    slack = ulp_bound * (BINARY64_UNIT_ROUNDOFF * 2 * magnitude + BINARY64_MIN_SUBNORMAL_HALF)
    return Interval(exact_log.lower - slack, exact_log.upper + slack)


def hermite_cubic_enclosure(
    t: Interval,
    value_low: Interval,
    slope_low: Interval,
    value_high: Interval,
    slope_high: Interval,
    *,
    rounded: bool = True,
) -> Interval:
    """Enclose the cubic Hermite form ``(2t^3-3t^2+1)VL + ... + (t^3-t^2)VDH``.

    The operation order follows the usual textbook grouping.  With
    ``rounded=True`` each elementary operation is wrapped in the binary64
    rounding model, so the result encloses the value a binary64 program computes
    for every ``t`` in the input interval, not merely the exact real cubic.
    """

    def mul(a: Interval, b: Interval) -> Interval:
        return binary64_operation("mul", a, b) if rounded else a * b

    def add(a: Interval, b: Interval) -> Interval:
        return binary64_operation("add", a, b) if rounded else a + b

    def sub(a: Interval, b: Interval) -> Interval:
        return binary64_operation("sub", a, b) if rounded else a - b

    one = Interval.exact(1)
    two = Interval.exact(2)
    three = Interval.exact(3)

    t2 = mul(t, t)
    t3 = mul(t2, t)

    p0 = mul(add(sub(mul(two, t3), mul(three, t2)), one), value_low)
    m0 = mul(add(sub(t3, mul(two, t2)), t), slope_low)
    p1 = mul(add(-mul(two, t3), mul(three, t2)), value_high)
    m1 = mul(sub(t3, t2), slope_high)

    return add(add(add(p0, m0), p1), m1)


def magnitude_clamp_branch(value: Interval, threshold: Fraction) -> str:
    """Classify a ``abs(v) < threshold`` guard over a whole interval.

    A frozen interpolator that substitutes a sentinel when its cubic leaves a
    magnitude band is not continuous.  An enclosure is only meaningful once the
    branch is decided for the entire cell, so this returns ``"BELOW"``,
    ``"AT_OR_ABOVE"`` or ``"UNDECIDED"`` and the caller must subdivide on
    ``"UNDECIDED"`` rather than assume the smooth branch.
    """

    if threshold <= 0:
        raise ValueError("clamp threshold must be positive")
    magnitude_low = Fraction(0) if value.contains(0) else min(abs(value.lower), abs(value.upper))
    magnitude_high = max(abs(value.lower), abs(value.upper))
    if magnitude_high < threshold:
        return "BELOW"
    if magnitude_low >= threshold:
        return "AT_OR_ABOVE"
    return "UNDECIDED"


def cubic_beta_rhs_enclosure(
    coupling: Interval,
    beta0: Interval,
    beta1: Interval,
    *,
    rounded: bool = True,
) -> Interval:
    """Enclose the toy right-hand side ``-a^2 * (b0 + a*b1)``.

    Only ``+``, ``-`` and ``*`` appear, so no transcendental backend is needed.
    The coefficients are supplied by the caller; this routine holds no physics
    constant and reads no accepted contract.
    """

    def mul(a: Interval, b: Interval) -> Interval:
        return binary64_operation("mul", a, b) if rounded else a * b

    def add(a: Interval, b: Interval) -> Interval:
        return binary64_operation("add", a, b) if rounded else a + b

    square = mul(coupling, coupling)
    inner = add(beta0, mul(coupling, beta1))
    return -mul(square, inner)


def fixed_step_rk4_enclosure(
    initial: Interval,
    step: Interval,
    beta0: Interval,
    beta1: Interval,
    *,
    steps: int,
    sixth: Interval,
    rounded: bool = True,
) -> Interval:
    """Enclose a fixed-step classical RK4 recursion with a cubic right-hand side.

    This is deliberately *not* validated initial-value-problem integration.  A
    fixed step count with no adaptivity and no error control is a finite
    composition of arithmetic operations, so ordinary interval evaluation
    already encloses everything the recursion can produce.  The result therefore
    bounds the recursion's own output and says nothing about the exact solution
    of the underlying differential equation.

    ``sixth`` is supplied by the caller because a frozen program may hold a
    truncated decimal literal rather than the exact rational one sixth.
    """

    if steps < 1:
        raise ValueError("a fixed-step recursion needs at least one step")

    def mul(a: Interval, b: Interval) -> Interval:
        return binary64_operation("mul", a, b) if rounded else a * b

    def add(a: Interval, b: Interval) -> Interval:
        return binary64_operation("add", a, b) if rounded else a + b

    half = Interval.exact(Fraction(1, 2))
    two = Interval.exact(2)
    current = initial
    for _ in range(steps):
        k0 = mul(step, cubic_beta_rhs_enclosure(current, beta0, beta1, rounded=rounded))
        k1 = mul(
            step,
            cubic_beta_rhs_enclosure(
                add(current, mul(half, k0)), beta0, beta1, rounded=rounded
            ),
        )
        k2 = mul(
            step,
            cubic_beta_rhs_enclosure(
                add(current, mul(half, k1)), beta0, beta1, rounded=rounded
            ),
        )
        k3 = mul(
            step,
            cubic_beta_rhs_enclosure(add(current, k2), beta0, beta1, rounded=rounded),
        )
        increment = add(add(add(k0, mul(two, k1)), mul(two, k2)), k3)
        current = add(current, mul(sixth, increment))
    return current


def subdivision_enclosure(
    lower: Fraction,
    upper: Fraction,
    cells: int,
    evaluate,
) -> Interval:
    """Union the per-cell enclosures produced by ``evaluate`` over a partition.

    ``cells`` is fixed by the caller, so the work is finite and predeclared.
    There is no retry loop and no adaptive refinement.
    """

    if cells < 1:
        raise ValueError("a partition needs at least one cell")
    if lower > upper:
        raise ValueError("partition bounds are reversed")
    width = Fraction(upper - lower, cells)
    result: Interval | None = None
    for index in range(cells):
        cell = Interval(lower + width * index, lower + width * (index + 1))
        enclosure = evaluate(cell)
        result = (
            enclosure
            if result is None
            else Interval(
                min(result.lower, enclosure.lower), max(result.upper, enclosure.upper)
            )
        )
    assert result is not None
    return result
