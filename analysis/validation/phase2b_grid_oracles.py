"""Grid and refinement bookkeeping reserved for a later Phase 2B task.

This module is generic mathematical software.  It builds no DIS integrand,
imports no APFEL or LHAPDF binding, and executes no Phase 2B physics.  Its
purpose is to separate three things the ``17/33/65`` hierarchy has been asked to
carry at once:

* whether a coarse level's nodes really are a subset of a finer level's nodes,
  which is an exact and checkable property of the node formula;
* what successive-level differences of a reported statistic actually measure,
  which is sampling stability and not a remainder bound; and
* what a convergence decision would need before it could be made, which is a
  declared precision target that the accepted records do not currently supply.

Nothing here converts the second into the third.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

#: What a successive-difference record is permitted to be called.
DIFFERENCE_INTERPRETATION = "SAMPLING_STABILITY_ONLY_NOT_A_REMAINDER_BOUND"


class MissingPrecisionTargetError(ValueError):
    """Raised when a convergence verdict is requested with no declared target."""


def geometric_nodes(count: int, lower: float, upper: float) -> tuple[float, ...]:
    """Return ``count`` geometrically spaced binary64 nodes on ``[lower, upper]``.

    The formula is ``x_i = lower * (upper/lower)**(i/(count-1))``, evaluated in
    binary64 exactly as a later runtime would evaluate it.
    """

    if count < 2:
        raise ValueError("a geometric node set needs at least two nodes")
    if not (lower > 0.0 and upper > lower):
        raise ValueError("geometric nodes need 0 < lower < upper")
    ratio = upper / lower
    return tuple(lower * ratio ** (index / (count - 1)) for index in range(count))


def levels_are_bitwise_nested(
    levels: Sequence[int], lower: float, upper: float
) -> tuple[bool, tuple[str, ...]]:
    """Check that each coarse level's nodes appear bitwise in every finer level.

    Nesting is exact in real arithmetic whenever the level sizes follow
    ``N_k = 2**k * (N_0 - 1) + 1``, but the runtime evaluates ``pow`` in
    binary64, so the property has to be tested rather than assumed.  Returns the
    verdict and one diagnostic string per failing pair.
    """

    ordered = sorted(levels)
    grids = {count: geometric_nodes(count, lower, upper) for count in ordered}
    failures: list[str] = []
    for position, coarse in enumerate(ordered):
        for fine in ordered[position + 1 :]:
            if (fine - 1) % (coarse - 1) != 0:
                failures.append(f"level {coarse} does not divide level {fine}")
                continue
            stride = (fine - 1) // (coarse - 1)
            for index in range(coarse):
                if grids[coarse][index] != grids[fine][index * stride]:
                    failures.append(
                        f"level {coarse} node {index} is not bitwise equal to "
                        f"level {fine} node {index * stride}"
                    )
    return (not failures), tuple(failures)


@dataclass(frozen=True)
class RefinementRecord:
    """Successive-level differences of one reported statistic."""

    statistic: str
    values: tuple[float, ...]
    first_difference: float
    second_difference: float
    interpretation: str = DIFFERENCE_INTERPRETATION

    @property
    def all_finite(self) -> bool:
        return all(math.isfinite(value) for value in self.values)


def refinement_record(statistic: str, values: Sequence[float]) -> RefinementRecord:
    """Build a refinement record from exactly three successive-level values.

    Differences are reported as absolute magnitudes with no relative division,
    so a statistic that is zero or changes sign is still recorded faithfully.
    """

    if len(values) != 3:
        raise ValueError("a refinement record needs exactly three successive levels")
    return RefinementRecord(
        statistic=statistic,
        values=tuple(float(value) for value in values),
        first_difference=abs(float(values[1]) - float(values[0])),
        second_difference=abs(float(values[2]) - float(values[1])),
    )


def convergence_verdict(
    record: RefinementRecord,
    absolute_target: float | None,
    target_justification: str,
) -> str:
    """Return ``PASS``/``FAIL``/``INCONCLUSIVE`` for a refinement record.

    The verdict is only defined once a precision target and the reason that
    target is sufficient are both declared.  Refusing to supply them yields an
    error rather than a fabricated threshold, and a supplied target must be a
    finite positive number backed by a stated justification.
    """

    if not record.all_finite:
        return "FAIL"
    if absolute_target is None:
        raise MissingPrecisionTargetError(
            "no declared absolute precision target: successive differences alone "
            "do not bound the unsampled remainder"
        )
    if not target_justification.strip():
        raise MissingPrecisionTargetError(
            "a precision target needs a stated reason it is sufficient for the "
            "normalized simulator law"
        )
    if not (math.isfinite(absolute_target) and absolute_target > 0.0):
        raise MissingPrecisionTargetError("a precision target must be finite and positive")
    if record.second_difference > absolute_target:
        return "FAIL"
    if record.second_difference > record.first_difference:
        return "INCONCLUSIVE"
    return "PASS"


def cross_path_overlap(
    centre_a: float, radius_a: float, centre_b: float, radius_b: float
) -> str:
    """Compare two certified intervals without transferring either budget.

    Both radii must be certified upstream.  A negative radius, or a radius that
    is not finite, is refused rather than treated as zero.
    """

    for radius in (radius_a, radius_b):
        if not math.isfinite(radius) or radius < 0.0:
            raise ValueError("cross-path comparison needs finite nonnegative certified radii")
    if not (math.isfinite(centre_a) and math.isfinite(centre_b)):
        return "FAIL"
    return "PASS" if abs(centre_a - centre_b) <= radius_a + radius_b else "FAIL"
