//! Leading-order inclusive electromagnetic electron-proton DIS cross section.
//!
//! The implemented approximation is
//! `d²σ/(dx dQ²) = 2πα² [Y₊ F₂ - y² F_L] / (x Q⁴)`, with
//! `Y₊ = 1 + (1-y)²`, `F_L = 0`, and `xF₃ = 0`. The differential
//! result has natural units GeV⁻⁴ because differentiation is with respect
//! to `Q²`; multiplying by [`GEV_MINUS_2_TO_PB`] expresses it in pb/GeV².

use std::error::Error;
use std::f64::consts::PI;
use std::fmt;

use super::constants::{ELECTRON_MASS_GEV, PROTON_MASS_GEV};
use super::structure_functions::{
    LO_LONGITUDINAL_STRUCTURE_FUNCTION, LO_PARITY_VIOLATING_STRUCTURE_FUNCTION,
};

/// Fixed electromagnetic coupling used by default, `α(0) = 1/137.035999084`.
///
/// This phase does not implement running electromagnetic coupling.
pub const DEFAULT_FIXED_ALPHA: f64 = 1.0 / 137.035_999_084;

/// Natural-unit conversion: `1 GeV⁻² = 3.893793721×10⁸ pb`.
///
/// A differential value in GeV⁻⁴ therefore acquires units pb/GeV² after
/// multiplication by this constant.
pub const GEV_MINUS_2_TO_PB: f64 = 3.893_793_721e8;

/// A pluggable electromagnetic-coupling strategy.
///
/// A future running-α implementation can depend on `q2`; the default strategy
/// deliberately returns a documented fixed value.
pub trait ElectromagneticCoupling {
    fn alpha(&self, q2: f64) -> Result<f64, CouplingError>;
}

/// A scale-independent electromagnetic coupling.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct FixedAlpha {
    value: f64,
}

impl FixedAlpha {
    /// Construct a fixed coupling in the physical interval `0 < α < 1`.
    pub fn new(value: f64) -> Result<Self, CouplingError> {
        validate_alpha(value)?;
        Ok(Self { value })
    }

    pub fn value(self) -> f64 {
        self.value
    }
}

impl Default for FixedAlpha {
    fn default() -> Self {
        Self {
            value: DEFAULT_FIXED_ALPHA,
        }
    }
}

impl ElectromagneticCoupling for FixedAlpha {
    fn alpha(&self, q2: f64) -> Result<f64, CouplingError> {
        if !q2.is_finite() || q2 <= 0.0 {
            return Err(CouplingError::InvalidScale { q2 });
        }
        validate_alpha(self.value)?;
        Ok(self.value)
    }
}

/// Failures produced by an electromagnetic-coupling strategy.
#[derive(Debug, Clone, PartialEq)]
pub enum CouplingError {
    InvalidScale { q2: f64 },
    InvalidCoupling { alpha: f64 },
}

impl fmt::Display for CouplingError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidScale { q2 } => {
                write!(
                    formatter,
                    "electromagnetic scale Q² must be positive, got {q2} GeV²"
                )
            }
            Self::InvalidCoupling { alpha } => write!(
                formatter,
                "electromagnetic coupling must satisfy 0 < α < 1, got {alpha}"
            ),
        }
    }
}

impl Error for CouplingError {}

/// Validated leading-order differential cross-section result.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct LoDisCrossSection {
    pub x: f64,
    /// Momentum-transfer scale in GeV².
    pub q2: f64,
    /// Squared electron-proton centre-of-mass energy in GeV².
    pub s: f64,
    pub y: f64,
    pub y_plus: f64,
    pub alpha: f64,
    pub f2: f64,
    /// Fixed to zero in this LO parton-model approximation.
    pub fl: f64,
    /// Fixed to zero for pure photon exchange.
    pub xf3: f64,
    /// `d²σ/(dx dQ²)` in GeV⁻⁴.
    pub d2sigma_dx_dq2_gev_minus4: f64,
    /// `d²σ/(dx dQ²)` in pb/GeV².
    pub d2sigma_dx_dq2_pb_per_gev2: f64,
}

/// Typed failures from kinematic validation or cross-section evaluation.
#[derive(Debug)]
pub enum CrossSectionError {
    InvalidBjorkenX { x: f64 },
    NonPositiveQ2 { q2: f64 },
    UnphysicalS { s: f64, threshold: f64 },
    InvalidInelasticity { y: f64 },
    InvalidDenominator { quantity: &'static str, value: f64 },
    InvalidStructureFunction { quantity: &'static str, value: f64 },
    NegativeCrossSectionFactor { value: f64 },
    NonFiniteResult { quantity: &'static str, value: f64 },
    Coupling(CouplingError),
}

impl fmt::Display for CrossSectionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidBjorkenX { x } => {
                write!(formatter, "Bjorken x must satisfy 0 < x < 1, got {x}")
            }
            Self::NonPositiveQ2 { q2 } => {
                write!(formatter, "Q² must be finite and positive, got {q2} GeV²")
            }
            Self::UnphysicalS { s, threshold } => write!(
                formatter,
                "beam invariant s must exceed the e⁻p threshold {threshold} GeV², got {s} GeV²"
            ),
            Self::InvalidInelasticity { y } => {
                write!(formatter, "inelasticity y must satisfy 0 < y < 1, got {y}")
            }
            Self::InvalidDenominator { quantity, value } => write!(
                formatter,
                "cross-section denominator {quantity} must be finite and positive, got {value}"
            ),
            Self::InvalidStructureFunction { quantity, value } => {
                write!(
                    formatter,
                    "structure function {quantity} is invalid: {value}"
                )
            }
            Self::NegativeCrossSectionFactor { value } => write!(
                formatter,
                "the LO cross-section structure-function factor is negative: {value}"
            ),
            Self::NonFiniteResult { quantity, value } => {
                write!(formatter, "calculated {quantity} is not finite: {value}")
            }
            Self::Coupling(source) => write!(formatter, "coupling evaluation failed: {source}"),
        }
    }
}

impl Error for CrossSectionError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Coupling(source) => Some(source),
            _ => None,
        }
    }
}

impl From<CouplingError> for CrossSectionError {
    fn from(source: CouplingError) -> Self {
        Self::Coupling(source)
    }
}

/// Calculate exact collider inelasticity from `x`, `Q²`, and beam invariant `s`.
///
/// With finite electron and proton masses,
/// `2 P·k = s - m_p² - m_e²`, hence
/// `y = Q² / [x (s - m_p² - m_e²)]`.
pub fn exact_inelasticity(x: f64, q2: f64, s: f64) -> Result<f64, CrossSectionError> {
    validate_x_q2(x, q2)?;

    let threshold = (PROTON_MASS_GEV + ELECTRON_MASS_GEV).powi(2);
    if !s.is_finite() || s <= threshold {
        return Err(CrossSectionError::UnphysicalS { s, threshold });
    }

    let twice_p_dot_k = s - PROTON_MASS_GEV.powi(2) - ELECTRON_MASS_GEV.powi(2);
    if !twice_p_dot_k.is_finite() || twice_p_dot_k <= 0.0 {
        return Err(CrossSectionError::UnphysicalS { s, threshold });
    }

    let y_denominator = x * twice_p_dot_k;
    validate_denominator("x(s - m_p² - m_e²)", y_denominator)?;
    let y = q2 / y_denominator;
    validate_y(y)?;
    Ok(y)
}

/// Calculate `Y₊ = 1 + (1-y)²` for a physical DIS inelasticity.
pub fn leptonic_y_plus(y: f64) -> Result<f64, CrossSectionError> {
    validate_y(y)?;
    let result = 1.0 + (1.0 - y).powi(2);
    validate_finite_result("Y₊", result)?;
    Ok(result)
}

/// Convert a differential cross section from GeV⁻⁴ to pb/GeV².
pub fn gev_minus_four_to_pb_per_gev2(value: f64) -> Result<f64, CrossSectionError> {
    if !value.is_finite() {
        return Err(CrossSectionError::NonFiniteResult {
            quantity: "d²σ/(dx dQ²) in GeV⁻⁴",
            value,
        });
    }
    let converted = value * GEV_MINUS_2_TO_PB;
    validate_finite_result("d²σ/(dx dQ²) in pb/GeV²", converted)?;
    Ok(converted)
}

/// Calculate the LO photon-exchange inclusive DIS differential cross section.
///
/// `f2` must be calculated at the supplied `(x, Q²)` point. This phase fixes
/// `F_L = 0` and `xF₃ = 0`; it does not claim NLO/NNLO or electroweak accuracy.
pub fn lo_differential_cross_section<C: ElectromagneticCoupling + ?Sized>(
    x: f64,
    q2: f64,
    s: f64,
    f2: f64,
    coupling: &C,
) -> Result<LoDisCrossSection, CrossSectionError> {
    validate_x_q2(x, q2)?;
    validate_structure_function("F₂", f2, true)?;

    let y = exact_inelasticity(x, q2, s)?;
    let y_plus = leptonic_y_plus(y)?;
    let alpha = coupling.alpha(q2)?;
    validate_alpha(alpha)?;

    let fl = LO_LONGITUDINAL_STRUCTURE_FUNCTION;
    let xf3 = LO_PARITY_VIOLATING_STRUCTURE_FUNCTION;
    let structure_factor = y_plus * f2 - y.powi(2) * fl;
    validate_finite_result("Y₊F₂ - y²F_L", structure_factor)?;
    if structure_factor < 0.0 {
        return Err(CrossSectionError::NegativeCrossSectionFactor {
            value: structure_factor,
        });
    }

    // q2 is Q², so q2² is Q⁴ in the conventional formula.
    let q4 = q2.powi(2);
    let cross_section_denominator = x * q4;
    validate_denominator("x Q⁴", cross_section_denominator)?;
    let prefactor = 2.0 * PI * alpha.powi(2) / cross_section_denominator;
    validate_finite_result("LO cross-section prefactor", prefactor)?;
    let d2sigma_dx_dq2_gev_minus4 = prefactor * structure_factor;
    validate_finite_result("d²σ/(dx dQ²) in GeV⁻⁴", d2sigma_dx_dq2_gev_minus4)?;
    let d2sigma_dx_dq2_pb_per_gev2 = gev_minus_four_to_pb_per_gev2(d2sigma_dx_dq2_gev_minus4)?;

    Ok(LoDisCrossSection {
        x,
        q2,
        s,
        y,
        y_plus,
        alpha,
        f2,
        fl,
        xf3,
        d2sigma_dx_dq2_gev_minus4,
        d2sigma_dx_dq2_pb_per_gev2,
    })
}

fn validate_x_q2(x: f64, q2: f64) -> Result<(), CrossSectionError> {
    if !x.is_finite() || x <= 0.0 || x >= 1.0 {
        return Err(CrossSectionError::InvalidBjorkenX { x });
    }
    if !q2.is_finite() || q2 <= 0.0 {
        return Err(CrossSectionError::NonPositiveQ2 { q2 });
    }
    Ok(())
}

fn validate_y(y: f64) -> Result<(), CrossSectionError> {
    if !y.is_finite() || y <= 0.0 || y >= 1.0 {
        return Err(CrossSectionError::InvalidInelasticity { y });
    }
    Ok(())
}

fn validate_alpha(alpha: f64) -> Result<(), CouplingError> {
    if !alpha.is_finite() || alpha <= 0.0 || alpha >= 1.0 {
        return Err(CouplingError::InvalidCoupling { alpha });
    }
    Ok(())
}

fn validate_structure_function(
    quantity: &'static str,
    value: f64,
    non_negative: bool,
) -> Result<(), CrossSectionError> {
    if !value.is_finite() || (non_negative && value < 0.0) {
        return Err(CrossSectionError::InvalidStructureFunction { quantity, value });
    }
    Ok(())
}

fn validate_denominator(quantity: &'static str, value: f64) -> Result<(), CrossSectionError> {
    if !value.is_finite() || value <= 0.0 {
        return Err(CrossSectionError::InvalidDenominator { quantity, value });
    }
    Ok(())
}

fn validate_finite_result(quantity: &'static str, value: f64) -> Result<(), CrossSectionError> {
    if !value.is_finite() {
        return Err(CrossSectionError::NonFiniteResult { quantity, value });
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn assert_close(actual: f64, expected: f64, relative_tolerance: f64) {
        let scale = actual.abs().max(expected.abs()).max(1.0);
        assert!(
            (actual - expected).abs() <= relative_tolerance * scale,
            "actual {actual:.16e}, expected {expected:.16e}, relative tolerance {relative_tolerance:.3e}"
        );
    }

    fn invariant_for_y(x: f64, q2: f64, y: f64) -> f64 {
        PROTON_MASS_GEV.powi(2) + ELECTRON_MASS_GEV.powi(2) + q2 / (x * y)
    }

    #[test]
    fn exact_y_retains_electron_and_proton_mass_terms() {
        let x = 0.01;
        let q2 = 100.0;
        let s = 101_200.854_031_085_39;

        let y = exact_inelasticity(x, q2, s).unwrap();

        assert_close(y, 0.098_814_254_952_129_78, 1.0e-14);
        assert!((y - q2 / (x * s)).abs() > 1.0e-8);
    }

    #[test]
    fn calculates_y_plus() {
        assert_close(leptonic_y_plus(0.4).unwrap(), 1.36, 1.0e-15);
    }

    #[test]
    fn cross_section_has_expected_prefactor_and_lo_assumptions() {
        let x = 0.2;
        let q2 = 10.0;
        let y = 0.25;
        let f2 = 0.3;
        let s = invariant_for_y(x, q2, y);
        let coupling = FixedAlpha::new(1.0 / 128.0).unwrap();

        let result = lo_differential_cross_section(x, q2, s, f2, &coupling).unwrap();
        let expected_y_plus = 1.0 + (1.0 - y).powi(2);
        let expected =
            2.0 * PI * (1.0_f64 / 128.0).powi(2) / (x * q2.powi(2)) * expected_y_plus * f2;

        assert_close(result.y, y, 1.0e-14);
        assert_close(result.y_plus, expected_y_plus, 1.0e-15);
        assert_close(result.d2sigma_dx_dq2_gev_minus4, expected, 1.0e-14);
        assert_close(
            result.d2sigma_dx_dq2_pb_per_gev2,
            expected * GEV_MINUS_2_TO_PB,
            1.0e-14,
        );
        assert_eq!(result.fl, 0.0);
        assert_eq!(result.xf3, 0.0);
    }

    #[test]
    fn converts_gev_minus_four_to_pb_per_gev2() {
        assert_close(
            gev_minus_four_to_pb_per_gev2(2.5e-9).unwrap(),
            0.973_448_430_25,
            1.0e-15,
        );
        assert!(matches!(
            gev_minus_four_to_pb_per_gev2(f64::NAN),
            Err(CrossSectionError::NonFiniteResult { .. })
        ));
    }

    #[test]
    fn fixed_alpha_default_is_documented_value() {
        let coupling = FixedAlpha::default();
        assert_eq!(coupling.value(), DEFAULT_FIXED_ALPHA);
        assert_eq!(coupling.alpha(100.0).unwrap(), DEFAULT_FIXED_ALPHA);
    }

    #[test]
    fn coupling_interface_can_support_scale_dependence() {
        struct LinearRunningAlpha;

        impl ElectromagneticCoupling for LinearRunningAlpha {
            fn alpha(&self, q2: f64) -> Result<f64, CouplingError> {
                Ok(1.0 / 137.0 + q2 * 1.0e-8)
            }
        }

        let low = LinearRunningAlpha.alpha(10.0).unwrap();
        let high = LinearRunningAlpha.alpha(1_000.0).unwrap();
        assert!(high > low);
    }

    #[test]
    fn rejects_invalid_x_q2_and_s() {
        let alpha = FixedAlpha::default();
        let threshold = (PROTON_MASS_GEV + ELECTRON_MASS_GEV).powi(2);

        assert!(matches!(
            lo_differential_cross_section(0.0, 10.0, 100.0, 0.2, &alpha),
            Err(CrossSectionError::InvalidBjorkenX { .. })
        ));
        assert!(matches!(
            lo_differential_cross_section(0.1, -10.0, 100.0, 0.2, &alpha),
            Err(CrossSectionError::NonPositiveQ2 { .. })
        ));
        assert!(matches!(
            lo_differential_cross_section(0.1, 10.0, threshold, 0.2, &alpha),
            Err(CrossSectionError::UnphysicalS { .. })
        ));
    }

    #[test]
    fn rejects_unphysical_y() {
        let alpha = FixedAlpha::default();
        let s_for_y_above_one = invariant_for_y(0.1, 10.0, 1.01);

        assert!(matches!(
            lo_differential_cross_section(0.1, 10.0, s_for_y_above_one, 0.2, &alpha),
            Err(CrossSectionError::InvalidInelasticity { .. })
        ));
        assert!(matches!(
            leptonic_y_plus(0.0),
            Err(CrossSectionError::InvalidInelasticity { .. })
        ));
        assert!(matches!(
            leptonic_y_plus(1.0),
            Err(CrossSectionError::InvalidInelasticity { .. })
        ));
    }

    #[test]
    fn rejects_invalid_structure_function_and_coupling() {
        let alpha = FixedAlpha::default();
        let s = invariant_for_y(0.1, 10.0, 0.5);

        assert!(matches!(
            lo_differential_cross_section(0.1, 10.0, s, f64::NAN, &alpha),
            Err(CrossSectionError::InvalidStructureFunction { .. })
        ));
        assert!(matches!(
            lo_differential_cross_section(0.1, 10.0, s, -0.2, &alpha),
            Err(CrossSectionError::InvalidStructureFunction { .. })
        ));
        assert!(matches!(
            FixedAlpha::new(0.0),
            Err(CouplingError::InvalidCoupling { .. })
        ));
        assert!(matches!(
            FixedAlpha::new(f64::INFINITY),
            Err(CouplingError::InvalidCoupling { .. })
        ));
    }

    #[test]
    fn rejects_an_overflowed_q4_denominator() {
        let error =
            lo_differential_cross_section(0.5, 1.0e200, 1.0e250, 0.2, &FixedAlpha::default())
                .unwrap_err();

        assert!(matches!(
            error,
            CrossSectionError::InvalidDenominator {
                quantity: "x Q⁴",
                ..
            }
        ));
    }
}
