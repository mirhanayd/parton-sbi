//! External integration checks for the system LHAPDF installation.
//!
//! These tests are ignored during the normal test suite. Prepare the WSL
//! environment first, then run:
//!
//! `cargo test --test lhapdf_integration -- --ignored`

use quark_sim::physics::pdf::{LhapdfProvider, PartonDensities, PdfError, PdfProvider};
use quark_sim::physics::structure_functions::electromagnetic_f2_from_xf;

const PINNED_SET: &str = "CT18LO";
const PINNED_MEMBER: i32 = 0;

fn flavor_values(densities: PartonDensities) -> [f64; 11] {
    [
        densities.gluon,
        densities.up,
        densities.anti_up,
        densities.down,
        densities.anti_down,
        densities.strange,
        densities.anti_strange,
        densities.charm,
        densities.anti_charm,
        densities.bottom,
        densities.anti_bottom,
    ]
}

fn assert_close(actual: f64, expected: f64) {
    let scale = expected.abs().max(1.0);
    let tolerance = 5.0e-13 * scale;
    assert!(
        (actual - expected).abs() <= tolerance,
        "actual {actual:.17e}, expected {expected:.17e}, tolerance {tolerance:.3e}"
    );
}

#[test]
#[ignore = "requires LHAPDF 6 and the CT18LO set installed in WSL"]
fn pinned_set_member_and_grid_metadata_are_available() {
    let provider = LhapdfProvider::new(PINNED_SET, PINNED_MEMBER).unwrap();

    assert_eq!(provider.set_name(), PINNED_SET);
    assert_eq!(provider.member(), PINNED_MEMBER);
    assert_eq!(provider.data_version(), 1);
    assert_eq!(provider.order_qcd(), 0);
    for expected_flavor in [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 21] {
        assert!(provider.available_flavors().contains(&expected_flavor));
    }

    let (x_minimum, x_maximum) = provider.x_range();
    let (q2_minimum, q2_maximum) = provider.q2_range();
    assert!(x_minimum > 0.0 && x_minimum < x_maximum && x_maximum <= 1.0);
    assert!(q2_minimum > 0.0 && q2_minimum < q2_maximum);
}

#[test]
#[ignore = "requires a working LHAPDF 6 installation in WSL"]
fn unavailable_set_returns_a_typed_error() {
    let error = LhapdfProvider::new("__quark_sim_set_that_does_not_exist__", 0).unwrap_err();

    assert!(matches!(error, PdfError::SetUnavailable { .. }));
}

#[test]
#[ignore = "requires LHAPDF 6 and the CT18LO set installed in WSL"]
fn unavailable_member_returns_a_typed_error() {
    let error = LhapdfProvider::new(PINNED_SET, 10_000).unwrap_err();

    assert!(matches!(
        error,
        PdfError::MemberOutOfRange {
            set_name,
            member: 10_000,
            ..
        } if set_name == PINNED_SET
    ));
}

#[test]
#[ignore = "requires LHAPDF 6 and the CT18LO set installed in WSL"]
fn representative_points_return_finite_physical_densities() {
    let provider = LhapdfProvider::new(PINNED_SET, PINNED_MEMBER).unwrap();

    for (x, q2) in [(1.0e-4, 10.0), (1.0e-2, 100.0), (0.3, 10_000.0)] {
        let densities = provider.parton_densities(x, q2).unwrap();
        assert_eq!(densities.x, x);
        assert_eq!(densities.q2, q2);

        let values = flavor_values(densities);
        assert!(values.into_iter().all(|value| value.is_finite()));
        // CT18LO is a positive-definite LO set. A heavy flavor may be exactly
        // zero below threshold, while the light quarks and gluon are positive.
        assert!(values.into_iter().all(|value| value >= 0.0));
        assert!(densities.gluon > 0.0);
        assert!(densities.up > 0.0);
        assert!(densities.down > 0.0);
    }
}

#[test]
#[ignore = "requires LHAPDF 6 and CT18LO data version 1 installed in WSL"]
fn ct18lo_v1_member_zero_matches_pinned_numeric_fixture() {
    let provider = LhapdfProvider::new(PINNED_SET, PINNED_MEMBER).unwrap();
    let densities = provider.parton_densities(0.01, 100.0).unwrap();

    assert_eq!(provider.data_version(), 1);
    // Generated once with LHAPDF 6.5.6 and CT18LO data version 1. These are
    // native x*f values; no extra factor of x has been applied.
    let expected = [
        7.048_573_373_780_798,
        0.697_243_077_062_449_2,
        0.498_310_426_275_845_9,
        0.637_404_734_948_826_4,
        0.539_440_556_348_112_3,
        0.085_437_232_530_629_42,
        0.085_437_232_530_629_42,
        0.193_239_217_403_326_2,
        0.193_239_217_403_326_2,
        0.069_987_112_152_875_91,
        0.069_987_112_152_875_91,
    ];

    for (actual, expected) in flavor_values(densities).into_iter().zip(expected) {
        assert_close(actual, expected);
    }
    let f2 = electromagnetic_f2_from_xf(&densities).unwrap();
    assert_close(f2, 0.868_424_637_027_082_1);
}
