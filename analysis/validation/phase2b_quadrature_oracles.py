"""Independent fixed quadrature rules reserved for a later Phase 2B task.

This module is generic mathematical software.  It does not import an APFEL
binding, construct a DIS integrand, or execute any Phase 2B physics.  The two
node/weight paths deliberately have different implementation provenance.
"""

from __future__ import annotations

import math
from collections.abc import Callable


def scipy_gauss_legendre_rule(order: int) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return SciPy 1.15.3 Gauss--Legendre nodes and weights on [-1, 1]."""

    if order < 1:
        raise ValueError("Gauss--Legendre order must be positive")
    import scipy
    from scipy.special import roots_legendre

    if scipy.__version__ != "1.15.3":
        raise RuntimeError(f"Phase 2B quadrature path A requires scipy==1.15.3, found {scipy.__version__}")
    nodes, weights = roots_legendre(order)
    return tuple(float(value) for value in nodes), tuple(float(value) for value in weights)


def scipy_gauss_legendre_integrate(
    function: Callable[[float], float],
    order: int,
    lower: float = -1.0,
    upper: float = 1.0,
) -> float:
    """Apply path A using NumPy's binary64 vector dot product."""

    if not (math.isfinite(lower) and math.isfinite(upper) and lower < upper):
        raise ValueError("integration bounds must be finite and ordered")
    import numpy

    nodes, weights = scipy_gauss_legendre_rule(order)
    half_width = (upper - lower) / 2.0
    midpoint = (upper + lower) / 2.0
    values = numpy.asarray(
        [function(midpoint + half_width * node) for node in nodes],
        dtype=numpy.float64,
    )
    return float(half_width * numpy.dot(numpy.asarray(weights, dtype=numpy.float64), values))


def clenshaw_curtis_rule(node_count: int) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Return direct Clenshaw--Curtis nodes and weights on [-1, 1].

    This is the explicit cosine-sum construction described by Waldvogel and
    Trefethen.  It uses only Python's scalar ``math`` operations and shares no
    node-generation, weight-generation, FFT, linear-algebra, or quadrature
    routine with the SciPy Gauss--Legendre path.
    """

    if node_count < 2:
        raise ValueError("Clenshaw--Curtis requires at least two nodes")
    degree = node_count - 1
    theta = [math.pi * index / degree for index in range(node_count)]
    nodes = [math.cos(angle) for angle in theta]
    weights = [0.0] * node_count
    interior = list(range(1, degree))
    values = [1.0] * len(interior)

    if degree % 2 == 0:
        endpoint = 1.0 / (degree * degree - 1.0)
        weights[0] = endpoint
        weights[-1] = endpoint
        for harmonic in range(1, degree // 2):
            denominator = 4.0 * harmonic * harmonic - 1.0
            for offset, index in enumerate(interior):
                values[offset] -= 2.0 * math.cos(2.0 * harmonic * theta[index]) / denominator
        denominator = degree * degree - 1.0
        for offset, index in enumerate(interior):
            values[offset] -= math.cos(degree * theta[index]) / denominator
    else:
        endpoint = 1.0 / (degree * degree)
        weights[0] = endpoint
        weights[-1] = endpoint
        for harmonic in range(1, (degree + 1) // 2):
            denominator = 4.0 * harmonic * harmonic - 1.0
            for offset, index in enumerate(interior):
                values[offset] -= 2.0 * math.cos(2.0 * harmonic * theta[index]) / denominator

    for value, index in zip(values, interior, strict=True):
        weights[index] = 2.0 * value / degree
    return tuple(nodes), tuple(weights)


def clenshaw_curtis_integrate(
    function: Callable[[float], float],
    node_count: int,
    lower: float = -1.0,
    upper: float = 1.0,
) -> float:
    """Apply path B using only scalar evaluation and ``math.fsum``."""

    if not (math.isfinite(lower) and math.isfinite(upper) and lower < upper):
        raise ValueError("integration bounds must be finite and ordered")
    nodes, weights = clenshaw_curtis_rule(node_count)
    half_width = (upper - lower) / 2.0
    midpoint = (upper + lower) / 2.0
    return half_width * math.fsum(
        weight * function(midpoint + half_width * node)
        for node, weight in zip(nodes, weights, strict=True)
    )
