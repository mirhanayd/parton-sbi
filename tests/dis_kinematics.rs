//! Public-API regression fixture for the DIS kinematics core.

use quark_sim::physics::{
    collider_beams, compute_dis_kinematics, scattered_electron, ELECTRON_MASS_GEV, PROTON_MASS_GEV,
};

fn assert_near(actual: f64, expected: f64, absolute: f64, relative: f64) {
    let tolerance = absolute + relative * expected.abs();
    assert!(
        (actual - expected).abs() <= tolerance,
        "expected {expected:.16e}, got {actual:.16e}, tolerance {tolerance:.3e}"
    );
}

#[test]
fn independently_calculated_hera_like_fixture_matches() {
    // Independent derivation (not generated from production-code output):
    //
    //   p  = sqrt(E² - m²)
    //   k  = (Ee, 0, 0, +pe)
    //   P  = (Ep, 0, 0, -pp)
    //   k' = (Ee', pe' sin(theta), 0, pe' cos(theta))
    //
    // Using Ee=27.5 GeV, Ep=920 GeV, Ee'=15 GeV, theta=20 degrees,
    // m_e=0.00051099895000 GeV, and m_p=0.93827208816 GeV gives
    // the hard-coded expected values below. They were evaluated separately
    // with 80-digit decimal arithmetic; see docs/dis_kinematics.md.
    let beams = collider_beams(27.5, 920.0).expect("reference beams must be valid");
    let outgoing = scattered_electron(15.0, 20.0).expect("scattered electron must be valid");
    let event = compute_dis_kinematics(beams.proton, beams.electron, outgoing)
        .expect("reference event must be physical");

    assert_near(event.q.e, 12.5, 1e-13, 1e-13);
    assert_near(event.q.px, -5.130_302_146_908_089, 1e-12, 1e-12);
    assert_near(event.q.py, 0.0, 1e-15, 0.0);
    assert_near(event.q.pz, 13.404_610_691_642_821, 1e-12, 1e-12);

    assert_near(event.s, 101_200.854_031_085_42, 1e-9, 1e-12);
    assert_near(event.q2, 49.753_587_913_074_78, 1e-11, 1e-12);
    assert_near(event.x, 0.001_043_829_649_849_406, 1e-15, 1e-12);
    assert_near(event.y, 0.470_992_917_430_067_27, 1e-14, 1e-12);
    assert_near(event.w2, 47_615.597_612_250_96, 2e-9, 1e-12);

    assert_near(
        beams.electron.mass_squared(),
        ELECTRON_MASS_GEV * ELECTRON_MASS_GEV,
        1e-12,
        1e-12,
    );
    assert_near(
        outgoing.mass_squared(),
        ELECTRON_MASS_GEV * ELECTRON_MASS_GEV,
        1e-12,
        1e-12,
    );
    assert_near(
        beams.proton.mass_squared(),
        PROTON_MASS_GEV * PROTON_MASS_GEV,
        1e-9,
        1e-12,
    );

    let hadronic_identity = PROTON_MASS_GEV * PROTON_MASS_GEV + event.q2 * (1.0 / event.x - 1.0);
    assert_near(event.w2, hadronic_identity, 2e-9, 1e-12);

    let lepton_identity = event.x
        * event.y
        * (event.s - PROTON_MASS_GEV * PROTON_MASS_GEV - ELECTRON_MASS_GEV * ELECTRON_MASS_GEV);
    assert_near(event.q2, lepton_identity, 1e-9, 1e-12);
}
