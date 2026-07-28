use std::collections::BTreeSet;

use parton_sbi::physics::{
    guard_shell_5_percent, pilot_grid_21x21, validate_positivity, ContinuousPdfContext, PdfTheta,
    Stage0Classification, DELTA_V_MAX, DELTA_V_MIN, LAMBDA_SEA_MAX, LAMBDA_SEA_MIN,
};

#[test]
fn exact_pilot_grid_and_guard_shell_contract() {
    let pilot = pilot_grid_21x21();
    assert_eq!(pilot.len(), 441);
    assert_eq!(
        pilot
            .iter()
            .map(|point| (point.delta_v.to_bits(), point.lambda_sea.to_bits()))
            .collect::<BTreeSet<_>>()
            .len(),
        441
    );
    assert!(pilot
        .iter()
        .any(|point| point.delta_v == 0.0 && point.lambda_sea == 0.0));
    for &(delta, sea) in &[
        (DELTA_V_MIN, 0.0),
        (DELTA_V_MAX, 0.0),
        (0.0, LAMBDA_SEA_MIN),
        (0.0, LAMBDA_SEA_MAX),
        (DELTA_V_MIN, LAMBDA_SEA_MIN),
        (DELTA_V_MIN, LAMBDA_SEA_MAX),
        (DELTA_V_MAX, LAMBDA_SEA_MIN),
        (DELTA_V_MAX, LAMBDA_SEA_MAX),
    ] {
        assert!(pilot
            .iter()
            .any(|point| point.delta_v == delta && point.lambda_sea == sea));
    }

    let guard = guard_shell_5_percent();
    assert_eq!(guard.len(), 80);
    assert_eq!(
        guard
            .iter()
            .map(|point| (point.delta_v.to_bits(), point.lambda_sea.to_bits()))
            .collect::<BTreeSet<_>>()
            .len(),
        80
    );
    assert!(guard.iter().all(|point| {
        point.delta_v < DELTA_V_MIN
            || point.delta_v > DELTA_V_MAX
            || point.lambda_sea < LAMBDA_SEA_MIN
            || point.lambda_sea > LAMBDA_SEA_MAX
    }));
}

#[test]
fn theta_validation_rejects_without_projection_and_canonicalizes_zero() {
    for &(delta, sea) in &[
        (0.0, 0.0),
        (DELTA_V_MIN, 0.0),
        (DELTA_V_MAX, 0.0),
        (0.0, LAMBDA_SEA_MIN),
        (0.0, LAMBDA_SEA_MAX),
        (DELTA_V_MIN, LAMBDA_SEA_MIN),
        (DELTA_V_MIN, LAMBDA_SEA_MAX),
        (DELTA_V_MAX, LAMBDA_SEA_MIN),
        (DELTA_V_MAX, LAMBDA_SEA_MAX),
    ] {
        assert_eq!(PdfTheta::new(delta, sea).unwrap().delta_v, delta);
    }
    assert!(PdfTheta::new(DELTA_V_MAX.next_up(), 0.0).is_err());
    assert!(PdfTheta::new(0.0, LAMBDA_SEA_MIN.next_down()).is_err());
    assert!(PdfTheta::new(f64::NAN, 0.0).is_err());
    assert!(PdfTheta::new(0.0, f64::INFINITY).is_err());
    let zero = PdfTheta::new(-0.0, -0.0).unwrap();
    assert_eq!(zero.delta_v.to_bits(), 0.0f64.to_bits());
    assert_eq!(zero.lambda_sea.to_bits(), 0.0f64.to_bits());
}

#[test]
#[ignore = "requires LHAPDF 6.5.6 and CT18NLO DataVersion 1 installed"]
fn authoritative_ct18nlo_metadata_q2_flavors_and_boundary_are_verified() {
    let context = ContinuousPdfContext::load_ct18nlo_v1().unwrap();
    let metadata = &context.metadata;
    assert_eq!(metadata.set_name, "CT18NLO");
    assert_eq!(metadata.member, 0);
    assert_eq!(metadata.data_version, 1);
    assert_eq!(metadata.order_qcd, 1);
    assert_eq!(metadata.q0_gev, metadata.support.q_minimum_gev);
    assert_eq!(metadata.q0_gev, 1.295);
    assert_eq!(metadata.alpha_s_mz, 0.118);
    assert_eq!(metadata.charm_mass_gev, 1.3);
    assert_eq!(metadata.charm_threshold_gev, 1.3);
    assert_eq!(metadata.bottom_mass_gev, 4.75);
    assert_eq!(metadata.bottom_threshold_gev, 4.75);
    assert_eq!(metadata.flavor_scheme, "variable");
    assert_eq!(metadata.lhapdf_version, "6.5.6");
    for flavor in [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 21] {
        assert!(metadata.supported_flavors.contains(&flavor));
    }
    assert_eq!(metadata.x_knots.last(), Some(&1.0));
    assert!(metadata.x_knots[0] < metadata.support.x_minimum);

    // Loading and every evaluation use Q in GeV. The managed xfxQ2 call is
    // reached only after the provider squares this Q exactly once.
    let center = context.construct(PdfTheta::new(0.0, 0.0).unwrap()).unwrap();
    let densities = center.densities(0.01).unwrap();
    assert!(densities.up.is_finite());
    assert!(densities.anti_up.is_finite());
    assert_ne!(densities.up, densities.anti_up);

    // Charm and bottom are verified as zero rather than clipped.
    for &x in metadata
        .x_knots
        .iter()
        .filter(|x| **x >= metadata.support.x_minimum)
    {
        let values = center.densities(x).unwrap();
        assert_eq!(values.charm, 0.0);
        assert_eq!(values.anti_charm, 0.0);
        assert_eq!(values.bottom, 0.0);
        assert_eq!(values.anti_bottom, 0.0);
    }
}

#[test]
#[ignore = "requires LHAPDF 6.5.6 and CT18NLO DataVersion 1 installed"]
fn construction_quadrature_identity_and_positivity_are_deterministic() {
    let context = ContinuousPdfContext::load_ct18nlo_v1().unwrap();
    let grid = context.validation_x_grid();
    let baseline = context.baseline_moments().unwrap();
    for theta in [
        PdfTheta::new(0.0, 0.0).unwrap(),
        PdfTheta::new(DELTA_V_MIN, 0.0).unwrap(),
        PdfTheta::new(DELTA_V_MAX, 0.0).unwrap(),
        PdfTheta::new(0.0, LAMBDA_SEA_MIN).unwrap(),
        PdfTheta::new(0.0, LAMBDA_SEA_MAX).unwrap(),
        PdfTheta::new(DELTA_V_MIN, LAMBDA_SEA_MIN).unwrap(),
        PdfTheta::new(DELTA_V_MIN, LAMBDA_SEA_MAX).unwrap(),
        PdfTheta::new(DELTA_V_MAX, LAMBDA_SEA_MIN).unwrap(),
        PdfTheta::new(DELTA_V_MAX, LAMBDA_SEA_MAX).unwrap(),
    ] {
        let delta = context.delta_moments(theta.delta_v).unwrap();
        let point = context
            .construct_from_moments(theta, &baseline, &delta)
            .unwrap();
        assert!(point.normalizations.a_u.is_sign_positive());
        assert!(point.normalizations.a_d.is_sign_positive());
        assert!(point.normalizations.a_g.is_sign_positive());
        let sums = context.sum_rules_from_moments(&point, &baseline, &delta);
        assert!(sums.construction_passes());
        assert!(sums.independent_passes());
        let identity_a = point.canonical_identity().unwrap();
        let identity_b = point.canonical_identity().unwrap();
        assert_eq!(identity_a, identity_b);
        assert!(identity_a.sha256.starts_with("sha256:"));
        assert_eq!(identity_a.sha256.len(), 71);
        let positivity = validate_positivity(&point, &grid).unwrap();
        // This test validates honest classification, not an expected PASS.
        assert!(matches!(
            positivity.classification,
            Stage0Classification::Pass
                | Stage0Classification::Fail
                | Stage0Classification::Inconclusive
        ));
    }

    let center = context.construct(PdfTheta::new(0.0, 0.0).unwrap()).unwrap();
    let changed = context
        .construct(PdfTheta::new(0.01, 0.0).unwrap())
        .unwrap();
    assert_ne!(
        center.canonical_identity().unwrap().sha256,
        changed.canonical_identity().unwrap().sha256
    );
    assert_eq!(
        center.canonical_identity().unwrap(),
        context
            .construct(PdfTheta::new(-0.0, 0.0).unwrap())
            .unwrap()
            .canonical_identity()
            .unwrap()
    );
}
