import math
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from analysis.validation.phase2b_bridge_oracles import (
    BINARY64_NEGATIVE_INFINITY_BITS,
    BINARY64_NEGATIVE_ZERO_BITS,
    BINARY64_POSITIVE_INFINITY_BITS,
    BINARY64_POSITIVE_ZERO_BITS,
    BRIDGE_B1_IDENTITY_MUTATIONS,
    BRIDGE_EXPECTED_SLOT_ORDER,
    BRIDGE_FLAVOR_SLOT_TO_PDG,
    BRIDGE_INTERFACE_CHECKS,
    BRIDGE_SENTINEL_DENSITY_BITS_BY_PDG,
    BRIDGE_SENTINEL_F_BY_PDG,
    BRIDGE_SENTINEL_PROBES,
    BRIDGE_SENTINEL_X_VALUES,
    BRIDGE_STRUCTURAL_ZERO_SLOTS,
    BRIDGE_ZERO_SENTINEL_DENSITY_BITS_BY_PDG,
    BRIDGE_ZERO_SENTINEL_PROBE,
    NonFiniteBinary64Operand,
    binary64_bits_to_float,
    decode_finite_binary64_bits,
    expected_bridge_slot_bits,
    float_to_binary64_bits,
    multiply_binary64,
    multiply_binary64_bits,
    round_dyadic_to_binary64_bits,
)


MIN_SUBNORMAL_BITS = 0x0000_0000_0000_0001
MAX_SUBNORMAL_BITS = 0x000F_FFFF_FFFF_FFFF
MIN_NORMAL_BITS = 0x0010_0000_0000_0000
MAX_FINITE_BITS = 0x7FEF_FFFF_FFFF_FFFF


@pytest.mark.parametrize(
    ("bits", "sign", "significand", "exponent"),
    [
        (BINARY64_POSITIVE_ZERO_BITS, 0, 0, -1074),
        (BINARY64_NEGATIVE_ZERO_BITS, 1, 0, -1074),
        (MIN_SUBNORMAL_BITS, 0, 1, -1074),
        (MAX_SUBNORMAL_BITS, 0, (1 << 52) - 1, -1074),
        (MIN_NORMAL_BITS, 0, 1 << 52, -1074),
        (0x3FF0_0000_0000_0000, 0, 1 << 52, -52),
        (MAX_FINITE_BITS, 0, (1 << 53) - 1, 971),
    ],
)
def test_finite_decode_is_an_exact_signed_dyadic(bits, sign, significand, exponent):
    decoded = decode_finite_binary64_bits(bits)
    assert (decoded.sign, decoded.significand, decoded.exponent) == (
        sign,
        significand,
        exponent,
    )


@pytest.mark.parametrize(
    "bits",
    [
        BINARY64_POSITIVE_ZERO_BITS,
        BINARY64_NEGATIVE_ZERO_BITS,
        MIN_SUBNORMAL_BITS,
        MAX_SUBNORMAL_BITS,
        MIN_NORMAL_BITS,
        0x3FF8_0000_0000_0000,
        MAX_FINITE_BITS,
        BINARY64_POSITIVE_INFINITY_BITS,
        0x7FF8_0000_0000_0001,
    ],
)
def test_binary64_bit_conversion_round_trips(bits):
    assert float_to_binary64_bits(binary64_bits_to_float(bits)) == bits


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (1.5, 2.0, 3.0),
        (-1.5, 2.0, -3.0),
        (1.5, -2.0, -3.0),
        (-1.5, -2.0, 3.0),
        (0.5, 8.0, 4.0),
    ],
)
def test_exact_normal_products(left, right, expected):
    assert float_to_binary64_bits(multiply_binary64(left, right)) == float_to_binary64_bits(expected)


@pytest.mark.parametrize(
    ("left_bits", "right_bits", "expected_bits"),
    [
        (BINARY64_POSITIVE_ZERO_BITS, float_to_binary64_bits(-3.0), BINARY64_NEGATIVE_ZERO_BITS),
        (BINARY64_NEGATIVE_ZERO_BITS, float_to_binary64_bits(-3.0), BINARY64_POSITIVE_ZERO_BITS),
        (BINARY64_NEGATIVE_ZERO_BITS, float_to_binary64_bits(3.0), BINARY64_NEGATIVE_ZERO_BITS),
        (BINARY64_POSITIVE_ZERO_BITS, float_to_binary64_bits(3.0), BINARY64_POSITIVE_ZERO_BITS),
    ],
)
def test_zero_product_uses_xor_sign(left_bits, right_bits, expected_bits):
    assert multiply_binary64_bits(left_bits, right_bits) == expected_bits


@pytest.mark.parametrize(
    ("coefficient", "exponent", "expected_bits"),
    [
        ((1 << 53) + 1, -53, 0x3FF0_0000_0000_0000),
        ((1 << 53) + 3, -53, 0x3FF0_0000_0000_0002),
        (1, -1075, BINARY64_POSITIVE_ZERO_BITS),
        (3, -1075, 0x0000_0000_0000_0002),
        (5, -1075, 0x0000_0000_0000_0002),
    ],
)
def test_exact_dyadic_halfway_cases_round_to_even(coefficient, exponent, expected_bits):
    assert round_dyadic_to_binary64_bits(0, coefficient, exponent) == expected_bits


@pytest.mark.parametrize(
    ("left_bits", "right_bits", "expected_bits"),
    [
        (MIN_NORMAL_BITS, float_to_binary64_bits(0.5), 0x0008_0000_0000_0000),
        (MIN_SUBNORMAL_BITS, float_to_binary64_bits(0.5), BINARY64_POSITIVE_ZERO_BITS),
        (MIN_SUBNORMAL_BITS, float_to_binary64_bits(0.75), MIN_SUBNORMAL_BITS),
        (0x0000_0000_0000_0003, float_to_binary64_bits(0.5), 0x0000_0000_0000_0002),
        (0x0000_0000_0000_0005, float_to_binary64_bits(0.5), 0x0000_0000_0000_0002),
        (MAX_SUBNORMAL_BITS, float_to_binary64_bits(1.0), MAX_SUBNORMAL_BITS),
        (MIN_NORMAL_BITS, float_to_binary64_bits(1.0), MIN_NORMAL_BITS),
    ],
)
def test_gradual_underflow_and_subnormal_boundaries(left_bits, right_bits, expected_bits):
    assert multiply_binary64_bits(left_bits, right_bits) == expected_bits


def test_subnormal_rounding_can_cross_to_minimum_normal():
    exact_midpoint = (1 << 53) - 1
    assert round_dyadic_to_binary64_bits(0, exact_midpoint, -1075) == MIN_NORMAL_BITS


@pytest.mark.parametrize(
    ("left_bits", "right_bits", "expected_bits"),
    [
        (MAX_FINITE_BITS, float_to_binary64_bits(1.0), MAX_FINITE_BITS),
        (MAX_FINITE_BITS, float_to_binary64_bits(2.0), BINARY64_POSITIVE_INFINITY_BITS),
        (MAX_FINITE_BITS | (1 << 63), float_to_binary64_bits(2.0), BINARY64_NEGATIVE_INFINITY_BITS),
    ],
)
def test_finite_products_encode_normal_or_signed_overflow(left_bits, right_bits, expected_bits):
    assert multiply_binary64_bits(left_bits, right_bits) == expected_bits


def test_overflow_midpoint_tie_selects_infinity():
    assert round_dyadic_to_binary64_bits(0, (1 << 54) - 1, 970) == BINARY64_POSITIVE_INFINITY_BITS
    assert round_dyadic_to_binary64_bits(0, (1 << 54) - 2, 970) == MAX_FINITE_BITS


@pytest.mark.parametrize(
    "nonfinite_bits",
    [
        BINARY64_POSITIVE_INFINITY_BITS,
        BINARY64_NEGATIVE_INFINITY_BITS,
        0x7FF8_0000_0000_0001,
        0xFFF0_0000_0000_0001,
    ],
)
def test_nonfinite_operands_are_rejected(nonfinite_bits):
    with pytest.raises(NonFiniteBinary64Operand):
        multiply_binary64_bits(nonfinite_bits, float_to_binary64_bits(1.0))


@pytest.mark.parametrize("bad_bits", [-1, 1 << 64, 1.25, True])
def test_invalid_bit_containers_are_rejected(bad_bits):
    with pytest.raises((TypeError, ValueError)):
        decode_finite_binary64_bits(bad_bits)


@pytest.mark.parametrize(
    "args",
    [
        (2, 1, 0),
        (False, 1, 0),
        (0, -1, 0),
        (0, True, 0),
        (0, 1, 1.5),
    ],
)
def test_invalid_exact_dyadics_are_rejected(args):
    with pytest.raises((TypeError, ValueError)):
        round_dyadic_to_binary64_bits(*args)


def test_deterministic_finite_random_products_match_host_binary64():
    generator = random.Random(0xB21D_6E)
    checked = 0
    while checked < 10_000:
        left_bits = generator.getrandbits(64)
        right_bits = generator.getrandbits(64)
        if ((left_bits >> 52) & 0x7FF) == 0x7FF or ((right_bits >> 52) & 0x7FF) == 0x7FF:
            continue
        left = binary64_bits_to_float(left_bits)
        right = binary64_bits_to_float(right_bits)
        host_bits = float_to_binary64_bits(left * right)
        assert multiply_binary64_bits(left_bits, right_bits) == host_bits
        checked += 1


def test_b1_inventory_has_fifteen_unique_mutation_cases_plus_valid_case():
    assert len(BRIDGE_B1_IDENTITY_MUTATIONS) == 15
    assert len({case.case_id for case in BRIDGE_B1_IDENTITY_MUTATIONS}) == 15
    assert len({case.field_path for case in BRIDGE_B1_IDENTITY_MUTATIONS}) == 15
    assert all(case.case_id.startswith("B1_") for case in BRIDGE_B1_IDENTITY_MUTATIONS)


def test_b1_inventory_covers_raw_projected_and_runtime_identity_categories():
    assert tuple(case.field_path for case in BRIDGE_B1_IDENTITY_MUTATIONS) == (
        "raw.set",
        "raw.data_version",
        "raw.member",
        "raw.archive_sha256",
        "raw.info_sha256",
        "raw.member_sha256",
        "raw.lhapdf_version+raw.lhapdf_commit",
        "projected.family",
        "projected.baseline",
        "projected.anchors[*].canonical_identity",
        "raw.flavor_order",
        "raw.x_support",
        "raw.q_support_gev+raw.q0_gev",
        "raw.interpolation",
        "raw.caller_policy",
    )


def test_b8_inventory_has_two_unique_interface_checks():
    assert len(BRIDGE_INTERFACE_CHECKS) == 2
    assert {case.case_id for case in BRIDGE_INTERFACE_CHECKS} == {
        "B8_01_STRONG_SYMBOL_LINK",
        "B8_02_ONE_CALLBACK_ONE_ARRAY",
    }


def test_bridge_slot_mapping_is_exact_and_structural_zeros_are_explicit():
    assert BRIDGE_EXPECTED_SLOT_ORDER == tuple(range(-6, 8))
    assert BRIDGE_STRUCTURAL_ZERO_SLOTS == (-6, 6, 7)
    assert tuple(BRIDGE_FLAVOR_SLOT_TO_PDG[slot] for slot in BRIDGE_EXPECTED_SLOT_ORDER) == (
        None,
        -5,
        -4,
        -3,
        -2,
        -1,
        21,
        1,
        2,
        3,
        4,
        5,
        None,
        None,
    )


def test_signed_power_of_two_sentinel_mapping_is_frozen():
    assert dict(BRIDGE_SENTINEL_F_BY_PDG) == {
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
    assert BRIDGE_SENTINEL_X_VALUES == (0.5, 0.25)


@pytest.mark.parametrize(
    ("probe_index", "expected_values"),
    [
        (0, (0.0, -0.5, 1.0, -2.0, 4.0, -8.0, 16.0, -32.0, 64.0, -128.0, 256.0, -512.0, 0.0, 0.0)),
        (1, (0.0, -0.25, 0.5, -1.0, 2.0, -4.0, 8.0, -16.0, 32.0, -64.0, 128.0, -256.0, 0.0, 0.0)),
    ],
)
def test_sentinel_probe_expected_slots_are_exact(probe_index, expected_values):
    probe = BRIDGE_SENTINEL_PROBES[probe_index]
    assert probe.case_id == f"B2_B5_SENTINEL_{probe_index + 1}"
    assert probe.x_bits == float_to_binary64_bits(BRIDGE_SENTINEL_X_VALUES[probe_index])
    assert probe.expected_slot_bits == tuple(float_to_binary64_bits(value) for value in expected_values)


def test_bridge_helper_preserves_mapped_negative_zero_but_not_structural_zero_signs():
    density_bits = dict(BRIDGE_SENTINEL_DENSITY_BITS_BY_PDG)
    density_bits[-5] = BINARY64_NEGATIVE_ZERO_BITS
    slot_bits = expected_bridge_slot_bits(float_to_binary64_bits(0.5), density_bits)
    assert slot_bits[BRIDGE_EXPECTED_SLOT_ORDER.index(-5)] == BINARY64_NEGATIVE_ZERO_BITS
    for slot in BRIDGE_STRUCTURAL_ZERO_SLOTS:
        assert slot_bits[BRIDGE_EXPECTED_SLOT_ORDER.index(slot)] == BINARY64_POSITIVE_ZERO_BITS


def test_dedicated_signed_zero_probe_preserves_every_mapped_zero_bit():
    assert BRIDGE_ZERO_SENTINEL_PROBE.case_id == "B5_SIGNED_ZERO_SENTINEL"
    for slot in BRIDGE_EXPECTED_SLOT_ORDER:
        index = BRIDGE_EXPECTED_SLOT_ORDER.index(slot)
        pdg = BRIDGE_FLAVOR_SLOT_TO_PDG[slot]
        expected = (
            BINARY64_POSITIVE_ZERO_BITS
            if pdg is None
            else BRIDGE_ZERO_SENTINEL_DENSITY_BITS_BY_PDG[pdg]
        )
        assert BRIDGE_ZERO_SENTINEL_PROBE.expected_slot_bits[index] == expected


@pytest.mark.parametrize("x", [0.0, -0.0, -0.5])
def test_bridge_helper_rejects_nonpositive_x(x):
    with pytest.raises(ValueError, match="positive and finite"):
        expected_bridge_slot_bits(
            float_to_binary64_bits(x),
            BRIDGE_SENTINEL_DENSITY_BITS_BY_PDG,
        )


def test_bridge_helper_rejects_missing_or_extra_flavors():
    missing = dict(BRIDGE_SENTINEL_DENSITY_BITS_BY_PDG)
    missing.pop(21)
    with pytest.raises(ValueError, match="exactly the eleven"):
        expected_bridge_slot_bits(float_to_binary64_bits(0.5), missing)

    extra = dict(BRIDGE_SENTINEL_DENSITY_BITS_BY_PDG)
    extra[22] = float_to_binary64_bits(1.0)
    with pytest.raises(ValueError, match="exactly the eleven"):
        expected_bridge_slot_bits(float_to_binary64_bits(0.5), extra)


def test_oracle_is_commutative_for_all_frozen_sentinel_products():
    for x in BRIDGE_SENTINEL_X_VALUES:
        x_bits = float_to_binary64_bits(x)
        for density_bits in BRIDGE_SENTINEL_DENSITY_BITS_BY_PDG.values():
            assert multiply_binary64_bits(x_bits, density_bits) == multiply_binary64_bits(
                density_bits,
                x_bits,
            )


def test_test_module_itself_did_not_require_nonfinite_host_arithmetic():
    assert math.isinf(binary64_bits_to_float(BINARY64_POSITIVE_INFINITY_BITS))
