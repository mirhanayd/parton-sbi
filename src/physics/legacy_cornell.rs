//! Legacy Cornell-potential functionality used by the original visualization.

/// Effective strong-coupling parameter used by the legacy demo.
pub const ALPHA_S: f32 = 0.5;

/// String tension used by the legacy demo, labelled in GeV/fm.
pub const STRING_TENSION: f32 = 0.9;

/// Reduced Planck conversion constant in GeV·fm.
///
/// It is retained for backward compatibility but is not applied by the legacy
/// Cornell expression.
pub const HBARC: f32 = 0.1973;

/// Evaluate the legacy Cornell potential `V(r) = -4 αs / (3 r) + k r`.
///
/// This function belongs to the educational Cornell visualization. It is not
/// used by the DIS kinematics implementation.
#[must_use]
pub fn cornell_potential(r: f32) -> f32 {
    let coulomb = -(4.0 * ALPHA_S) / (3.0 * r);
    let linear = STRING_TENSION * r;
    coulomb + linear
}
