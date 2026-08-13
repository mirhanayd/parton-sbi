"""Generic binary64 and bridge-routing oracles for a later Phase 2B task.

This module is repository-owned mathematical support code.  It does not load a
PDF set, import APFEL, construct a DIS observable, or execute physics.  The
multiplication oracle starts from captured IEEE-754 binary64 bit patterns and
uses only exact Python integer arithmetic for decode, multiplication, and
round-to-nearest, ties-to-even.

Non-finite *inputs* are rejected because the planned bridge requires finite
``x`` and ``f`` values.  A finite exact product that overflows is encoded as a
signed infinity, allowing a caller to report the planned bridge failure rather
than inheriting the host language's floating-point multiplication result.
"""

from __future__ import annotations

import struct
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


BINARY64_SIGN_MASK = 0x8000_0000_0000_0000
BINARY64_EXPONENT_MASK = 0x7FF0_0000_0000_0000
BINARY64_FRACTION_MASK = 0x000F_FFFF_FFFF_FFFF
BINARY64_POSITIVE_INFINITY_BITS = 0x7FF0_0000_0000_0000
BINARY64_NEGATIVE_INFINITY_BITS = 0xFFF0_0000_0000_0000
BINARY64_POSITIVE_ZERO_BITS = 0x0000_0000_0000_0000
BINARY64_NEGATIVE_ZERO_BITS = 0x8000_0000_0000_0000

_BINARY64_EXPONENT_SHIFT = 52
_BINARY64_EXPONENT_ALL_ONES = 0x7FF
_BINARY64_EXPONENT_BIAS = 1023
_BINARY64_SIGNIFICAND_BITS = 53
_BINARY64_HIDDEN_BIT = 1 << 52
_BINARY64_MIN_NORMAL_EXPONENT = -1022
_BINARY64_SUBNORMAL_EXPONENT = -1074
_BINARY64_MAX_NORMAL_EXPONENT = 1023
_UINT64_LIMIT = 1 << 64


class NonFiniteBinary64Operand(ValueError):
    """Raised when the exact finite-input oracle receives NaN or infinity."""


@dataclass(frozen=True)
class FiniteBinary64:
    """Exact dyadic decode of a finite binary64 value.

    The represented value is ``(-1)**sign * significand * 2**exponent``.
    Both signs of zero retain their sign bit and use a zero significand.
    """

    sign: int
    significand: int
    exponent: int

    @property
    def is_zero(self) -> bool:
        return self.significand == 0


@dataclass(frozen=True)
class BridgeIdentityMutation:
    """One field whose mutation must make B1 identity validation fail."""

    case_id: str
    field_path: str


@dataclass(frozen=True)
class BridgeInterfaceCheck:
    """One static/dynamic linkage assertion reserved for bridge check B8."""

    case_id: str
    requirement: str


@dataclass(frozen=True)
class BridgeSentinelProbe:
    """Captured input and expected slot bits for one sentinel callback."""

    case_id: str
    x_bits: int
    expected_slot_bits: tuple[int, ...]


def _require_binary64_bits(bits: int) -> None:
    if isinstance(bits, bool) or not isinstance(bits, int):
        raise TypeError("binary64 bits must be an integer")
    if not 0 <= bits < _UINT64_LIMIT:
        raise ValueError("binary64 bits must be in [0, 2**64)")


def float_to_binary64_bits(value: float) -> int:
    """Return the exact IEEE-754 binary64 interchange bits of ``value``."""

    return struct.unpack(">Q", struct.pack(">d", value))[0]


def binary64_bits_to_float(bits: int) -> float:
    """Construct a Python binary64 float from exact interchange bits."""

    _require_binary64_bits(bits)
    return struct.unpack(">d", struct.pack(">Q", bits))[0]


def decode_finite_binary64_bits(bits: int) -> FiniteBinary64:
    """Decode finite binary64 bits to an exact signed dyadic integer."""

    _require_binary64_bits(bits)
    sign = 1 if bits & BINARY64_SIGN_MASK else 0
    exponent_field = (bits & BINARY64_EXPONENT_MASK) >> _BINARY64_EXPONENT_SHIFT
    fraction = bits & BINARY64_FRACTION_MASK
    if exponent_field == _BINARY64_EXPONENT_ALL_ONES:
        kind = "infinity" if fraction == 0 else "NaN"
        raise NonFiniteBinary64Operand(f"finite binary64 operand required, got {kind}")
    if exponent_field == 0:
        return FiniteBinary64(sign, fraction, _BINARY64_SUBNORMAL_EXPONENT)
    return FiniteBinary64(
        sign,
        _BINARY64_HIDDEN_BIT | fraction,
        exponent_field - _BINARY64_EXPONENT_BIAS - 52,
    )


def _round_integer_right_ties_even(integer: int, shift: int) -> int:
    """Return RN-ties-even(integer / 2**shift), exactly."""

    if shift <= 0:
        return integer << -shift
    quotient, remainder = divmod(integer, 1 << shift)
    halfway = 1 << (shift - 1)
    if remainder > halfway or (remainder == halfway and quotient & 1):
        quotient += 1
    return quotient


def round_dyadic_to_binary64_bits(sign: int, coefficient: int, exponent: int) -> int:
    """Correctly round ``(-1)**sign * coefficient * 2**exponent``.

    ``coefficient`` is non-negative.  The returned encoding covers both signs
    of zero, subnormals, normals, and signed overflow to infinity.  All
    decisions, including the normal/subnormal and finite/overflow boundaries,
    are made with exact integer comparisons and round-to-nearest, ties-to-even.
    """

    if isinstance(sign, bool) or not isinstance(sign, int) or sign not in (0, 1):
        raise ValueError("sign must be the integer 0 or 1")
    if isinstance(coefficient, bool) or not isinstance(coefficient, int) or coefficient < 0:
        raise ValueError("coefficient must be a non-negative integer")
    if isinstance(exponent, bool) or not isinstance(exponent, int):
        raise TypeError("exponent must be an integer")

    sign_bits = BINARY64_SIGN_MASK if sign else 0
    if coefficient == 0:
        return sign_bits

    exact_top_exponent = coefficient.bit_length() - 1 + exponent

    # Values below half the least subnormal cannot round away from signed zero.
    if exact_top_exponent < _BINARY64_SUBNORMAL_EXPONENT - 1:
        return sign_bits

    # Any value at least 2**1024 overflows without needing a large intermediate.
    if exact_top_exponent > _BINARY64_MAX_NORMAL_EXPONENT:
        return sign_bits | BINARY64_POSITIVE_INFINITY_BITS

    if exact_top_exponent < _BINARY64_MIN_NORMAL_EXPONENT:
        subnormal = _round_integer_right_ties_even(
            coefficient,
            _BINARY64_SUBNORMAL_EXPONENT - exponent,
        )
        if subnormal == 0:
            return sign_bits
        if subnormal < _BINARY64_HIDDEN_BIT:
            return sign_bits | subnormal
        # Rounding the upper subnormal boundary can produce minimum normal.
        if subnormal == _BINARY64_HIDDEN_BIT:
            return sign_bits | (1 << _BINARY64_EXPONENT_SHIFT)
        raise AssertionError("subnormal rounding exceeded the minimum normal encoding")

    target_exponent = exact_top_exponent - (_BINARY64_SIGNIFICAND_BITS - 1)
    significand = _round_integer_right_ties_even(
        coefficient,
        target_exponent - exponent,
    )
    if significand == 1 << _BINARY64_SIGNIFICAND_BITS:
        significand = _BINARY64_HIDDEN_BIT
        exact_top_exponent += 1
    if exact_top_exponent > _BINARY64_MAX_NORMAL_EXPONENT:
        return sign_bits | BINARY64_POSITIVE_INFINITY_BITS

    exponent_field = exact_top_exponent + _BINARY64_EXPONENT_BIAS
    fraction = significand - _BINARY64_HIDDEN_BIT
    return sign_bits | (exponent_field << _BINARY64_EXPONENT_SHIFT) | fraction


def multiply_binary64_bits(left_bits: int, right_bits: int) -> int:
    """Correctly multiply two finite binary64 encodings using exact integers."""

    left = decode_finite_binary64_bits(left_bits)
    right = decode_finite_binary64_bits(right_bits)
    sign = left.sign ^ right.sign
    return round_dyadic_to_binary64_bits(
        sign,
        left.significand * right.significand,
        left.exponent + right.exponent,
    )


def multiply_binary64(left: float, right: float) -> float:
    """Float wrapper around :func:`multiply_binary64_bits`."""

    result_bits = multiply_binary64_bits(
        float_to_binary64_bits(left),
        float_to_binary64_bits(right),
    )
    return binary64_bits_to_float(result_bits)


# These 15 category mutations complement one valid exact-tuple case.  The
# bridge compares the complete serialized raw/projected identity before any
# callback; the mutations make each load-bearing identity category observable.
BRIDGE_B1_IDENTITY_MUTATIONS = (
    BridgeIdentityMutation("B1_01_SET", "raw.set"),
    BridgeIdentityMutation("B1_02_DATA_VERSION", "raw.data_version"),
    BridgeIdentityMutation("B1_03_MEMBER", "raw.member"),
    BridgeIdentityMutation("B1_04_ARCHIVE_SHA256", "raw.archive_sha256"),
    BridgeIdentityMutation("B1_05_INFO_SHA256", "raw.info_sha256"),
    BridgeIdentityMutation("B1_06_MEMBER_SHA256", "raw.member_sha256"),
    BridgeIdentityMutation("B1_07_LHAPDF_IDENTITY", "raw.lhapdf_version+raw.lhapdf_commit"),
    BridgeIdentityMutation("B1_08_FAMILY", "projected.family"),
    BridgeIdentityMutation("B1_09_BASELINE", "projected.baseline"),
    BridgeIdentityMutation("B1_10_ANCHOR_IDENTITY", "projected.anchors[*].canonical_identity"),
    BridgeIdentityMutation("B1_11_FLAVOR_ORDER", "raw.flavor_order"),
    BridgeIdentityMutation("B1_12_X_SUPPORT", "raw.x_support"),
    BridgeIdentityMutation("B1_13_Q_SUPPORT_Q0", "raw.q_support_gev+raw.q0_gev"),
    BridgeIdentityMutation("B1_14_INTERPOLATION", "raw.interpolation"),
    BridgeIdentityMutation("B1_15_CALLER_POLICY", "raw.caller_policy"),
)


BRIDGE_INTERFACE_CHECKS = (
    BridgeInterfaceCheck(
        "B8_01_STRONG_SYMBOL_LINK",
        "SetPDFSet(external) resolves to the intended strong ExternalSetAPFEL symbol",
    ),
    BridgeInterfaceCheck(
        "B8_02_ONE_CALLBACK_ONE_ARRAY",
        "one APFEL request makes exactly one callback that writes exactly slots -6 through 7",
    ),
)


BRIDGE_EXPECTED_SLOT_ORDER = tuple(range(-6, 8))
BRIDGE_STRUCTURAL_ZERO_SLOTS = (-6, 6, 7)
BRIDGE_FLAVOR_SLOT_TO_PDG = MappingProxyType(
    {
        -6: None,
        -5: -5,
        -4: -4,
        -3: -3,
        -2: -2,
        -1: -1,
        0: 21,
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        5: 5,
        6: None,
        7: None,
    }
)
BRIDGE_SENTINEL_F_BY_PDG = MappingProxyType(
    {
        -5: -1.0,
        -4: 2.0,
        -3: -4.0,
        -2: 8.0,
        -1: -16.0,
        1: -64.0,
        2: 128.0,
        3: -256.0,
        4: 512.0,
        5: -1024.0,
        21: 32.0,
    }
)
BRIDGE_SENTINEL_X_VALUES = (0.5, 0.25)
BRIDGE_SENTINEL_DENSITY_BITS_BY_PDG = MappingProxyType(
    {pdg: float_to_binary64_bits(value) for pdg, value in BRIDGE_SENTINEL_F_BY_PDG.items()}
)


def expected_bridge_slot_bits(
    x_bits: int,
    density_bits_by_pdg: Mapping[int, int],
) -> tuple[int, ...]:
    """Return the exact planned ``xf[-6:7]`` slot encodings.

    The eleven mapped flavor inputs must be present exactly.  Positive finite
    ``x`` is required.  Mapped signed zero is preserved by multiplication;
    top, antitop, and photon are structural bitwise ``+0``.
    """

    x = decode_finite_binary64_bits(x_bits)
    if x.sign or x.is_zero:
        raise ValueError("bridge x must be positive and finite")
    required_pdgs = {pdg for pdg in BRIDGE_FLAVOR_SLOT_TO_PDG.values() if pdg is not None}
    if set(density_bits_by_pdg) != required_pdgs:
        raise ValueError("bridge densities must contain exactly the eleven mapped PDG flavors")

    slot_bits = []
    for slot in BRIDGE_EXPECTED_SLOT_ORDER:
        pdg = BRIDGE_FLAVOR_SLOT_TO_PDG[slot]
        if pdg is None:
            slot_bits.append(BINARY64_POSITIVE_ZERO_BITS)
        else:
            slot_bits.append(multiply_binary64_bits(x_bits, density_bits_by_pdg[pdg]))
    return tuple(slot_bits)


BRIDGE_SENTINEL_PROBES = tuple(
    BridgeSentinelProbe(
        case_id=f"B2_B5_SENTINEL_{index}",
        x_bits=float_to_binary64_bits(x),
        expected_slot_bits=expected_bridge_slot_bits(
            float_to_binary64_bits(x),
            BRIDGE_SENTINEL_DENSITY_BITS_BY_PDG,
        ),
    )
    for index, x in enumerate(BRIDGE_SENTINEL_X_VALUES, start=1)
)

# A third callback isolates B5 from the nonzero mapping/permutation sentinels.
# Alternating signs make loss of either +0 or -0 observable in mapped slots.
BRIDGE_ZERO_SENTINEL_DENSITY_BITS_BY_PDG = MappingProxyType(
    {
        pdg: (BINARY64_NEGATIVE_ZERO_BITS if index % 2 else BINARY64_POSITIVE_ZERO_BITS)
        for index, pdg in enumerate(sorted(BRIDGE_SENTINEL_F_BY_PDG))
    }
)
BRIDGE_ZERO_SENTINEL_PROBE = BridgeSentinelProbe(
    case_id="B5_SIGNED_ZERO_SENTINEL",
    x_bits=float_to_binary64_bits(0.5),
    expected_slot_bits=expected_bridge_slot_bits(
        float_to_binary64_bits(0.5),
        BRIDGE_ZERO_SENTINEL_DENSITY_BITS_BY_PDG,
    ),
)


__all__ = [
    "BINARY64_EXPONENT_MASK",
    "BINARY64_FRACTION_MASK",
    "BINARY64_NEGATIVE_INFINITY_BITS",
    "BINARY64_NEGATIVE_ZERO_BITS",
    "BINARY64_POSITIVE_INFINITY_BITS",
    "BINARY64_POSITIVE_ZERO_BITS",
    "BINARY64_SIGN_MASK",
    "BRIDGE_B1_IDENTITY_MUTATIONS",
    "BRIDGE_EXPECTED_SLOT_ORDER",
    "BRIDGE_FLAVOR_SLOT_TO_PDG",
    "BRIDGE_INTERFACE_CHECKS",
    "BRIDGE_SENTINEL_DENSITY_BITS_BY_PDG",
    "BRIDGE_SENTINEL_F_BY_PDG",
    "BRIDGE_SENTINEL_PROBES",
    "BRIDGE_SENTINEL_X_VALUES",
    "BRIDGE_STRUCTURAL_ZERO_SLOTS",
    "BRIDGE_ZERO_SENTINEL_DENSITY_BITS_BY_PDG",
    "BRIDGE_ZERO_SENTINEL_PROBE",
    "BridgeIdentityMutation",
    "BridgeInterfaceCheck",
    "BridgeSentinelProbe",
    "FiniteBinary64",
    "NonFiniteBinary64Operand",
    "binary64_bits_to_float",
    "decode_finite_binary64_bits",
    "expected_bridge_slot_bits",
    "float_to_binary64_bits",
    "multiply_binary64",
    "multiply_binary64_bits",
    "round_dyadic_to_binary64_bits",
]
