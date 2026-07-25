//! Leading-order electromagnetic DIS structure functions.
//!
//! [`PartonDensities`] stores LHAPDF-style `x f(x, Q²)` values. Consequently,
//! the `x` in `F₂ = x Σ e_q²(q + q̄)` is already present in each
//! flavor field and must not be multiplied a second time.

use std::error::Error;
use std::fmt;

use super::pdf::{PartonDensities, PdfError, PdfProvider};

/// Squared electric charge of an up-type quark, `(2/3)²`.
pub const UP_TYPE_CHARGE_SQUARED: f64 = 4.0 / 9.0;

/// Squared electric charge of a down-type quark, `(-1/3)²`.
pub const DOWN_TYPE_CHARGE_SQUARED: f64 = 1.0 / 9.0;

/// The longitudinal structure function in the phase-one parton-model limit.
pub const LO_LONGITUDINAL_STRUCTURE_FUNCTION: f64 = 0.0;

/// The parity-violating structure function in the electromagnetic approximation.
pub const LO_PARITY_VIOLATING_STRUCTURE_FUNCTION: f64 = 0.0;

/// Leading-order electromagnetic structure functions and the PDF values used.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct LoStructureFunctions {
    /// LHAPDF-style `x f(x, Q²)` parton densities.
    pub densities: PartonDensities,
    /// Electromagnetic `F₂`.
    pub f2: f64,
    /// `F_L`, fixed to zero in this leading-order approximation.
    pub fl: f64,
    /// `xF₃`, fixed to zero for pure photon exchange.
    pub xf3: f64,
}

/// Failures while validating PDF values or calculating structure functions.
#[derive(Debug)]
pub enum StructureFunctionError {
    InvalidBjorkenX {
        x: f64,
    },
    NonPositiveQ2 {
        q2: f64,
    },
    NonFiniteDensity {
        flavor: &'static str,
        value: f64,
    },
    MismatchedPdfKinematics {
        quantity: &'static str,
        requested: f64,
        returned: f64,
    },
    NonFiniteResult {
        quantity: &'static str,
        value: f64,
    },
    Pdf(PdfError),
}

impl fmt::Display for StructureFunctionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidBjorkenX { x } => {
                write!(formatter, "Bjorken x must satisfy 0 < x < 1, got {x}")
            }
            Self::NonPositiveQ2 { q2 } => {
                write!(formatter, "Q² must be finite and positive, got {q2} GeV²")
            }
            Self::NonFiniteDensity { flavor, value } => {
                write!(
                    formatter,
                    "PDF density x·{flavor}(x,Q²) is not finite: {value}"
                )
            }
            Self::MismatchedPdfKinematics {
                quantity,
                requested,
                returned,
            } => write!(
                formatter,
                "PDF provider returned {quantity} = {returned}, but {requested} was requested"
            ),
            Self::NonFiniteResult { quantity, value } => {
                write!(formatter, "calculated {quantity} is not finite: {value}")
            }
            Self::Pdf(source) => write!(formatter, "PDF evaluation failed: {source}"),
        }
    }
}

impl Error for StructureFunctionError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Pdf(source) => Some(source),
            _ => None,
        }
    }
}

impl From<PdfError> for StructureFunctionError {
    fn from(source: PdfError) -> Self {
        Self::Pdf(source)
    }
}

/// Calculate electromagnetic `F₂` from LHAPDF-style `x f(x, Q²)` values.
///
/// Up and charm receive the charge-squared weight `4/9`; down, strange, and
/// bottom receive `1/9`. Gluons do not enter the leading-order photon-exchange
/// expression. No additional factor of `x` is applied.
pub fn electromagnetic_f2_from_xf(
    densities: &PartonDensities,
) -> Result<f64, StructureFunctionError> {
    validate_pdf_point(densities.x, densities.q2)?;
    validate_densities(densities)?;

    let up_type = densities.up + densities.anti_up + densities.charm + densities.anti_charm;
    let down_type = densities.down
        + densities.anti_down
        + densities.strange
        + densities.anti_strange
        + densities.bottom
        + densities.anti_bottom;

    validate_finite_result("up-type flavor sum", up_type)?;
    validate_finite_result("down-type flavor sum", down_type)?;

    let f2 = UP_TYPE_CHARGE_SQUARED * up_type + DOWN_TYPE_CHARGE_SQUARED * down_type;
    validate_finite_result("F₂", f2)?;
    Ok(f2)
}

/// Query a PDF provider and calculate the phase-one LO structure functions.
pub fn evaluate_lo_structure_functions<P: PdfProvider + ?Sized>(
    provider: &P,
    x: f64,
    q2: f64,
) -> Result<LoStructureFunctions, StructureFunctionError> {
    validate_pdf_point(x, q2)?;

    let densities = provider.parton_densities(x, q2)?;
    validate_returned_kinematics("x", x, densities.x)?;
    validate_returned_kinematics("Q²", q2, densities.q2)?;
    let f2 = electromagnetic_f2_from_xf(&densities)?;

    Ok(LoStructureFunctions {
        densities,
        f2,
        fl: LO_LONGITUDINAL_STRUCTURE_FUNCTION,
        xf3: LO_PARITY_VIOLATING_STRUCTURE_FUNCTION,
    })
}

fn validate_pdf_point(x: f64, q2: f64) -> Result<(), StructureFunctionError> {
    if !x.is_finite() || x <= 0.0 || x >= 1.0 {
        return Err(StructureFunctionError::InvalidBjorkenX { x });
    }
    if !q2.is_finite() || q2 <= 0.0 {
        return Err(StructureFunctionError::NonPositiveQ2 { q2 });
    }
    Ok(())
}

fn validate_densities(densities: &PartonDensities) -> Result<(), StructureFunctionError> {
    let values = [
        ("g", densities.gluon),
        ("u", densities.up),
        ("ū", densities.anti_up),
        ("d", densities.down),
        ("d̄", densities.anti_down),
        ("s", densities.strange),
        ("s̄", densities.anti_strange),
        ("c", densities.charm),
        ("c̄", densities.anti_charm),
        ("b", densities.bottom),
        ("b̄", densities.anti_bottom),
    ];

    for (flavor, value) in values {
        if !value.is_finite() {
            return Err(StructureFunctionError::NonFiniteDensity { flavor, value });
        }
    }
    Ok(())
}

fn validate_returned_kinematics(
    quantity: &'static str,
    requested: f64,
    returned: f64,
) -> Result<(), StructureFunctionError> {
    let scale = requested.abs().max(returned.abs()).max(1.0);
    let tolerance = 8.0 * f64::EPSILON * scale;
    if !returned.is_finite() || (returned - requested).abs() > tolerance {
        return Err(StructureFunctionError::MismatchedPdfKinematics {
            quantity,
            requested,
            returned,
        });
    }
    Ok(())
}

fn validate_finite_result(
    quantity: &'static str,
    value: f64,
) -> Result<(), StructureFunctionError> {
    if !value.is_finite() {
        return Err(StructureFunctionError::NonFiniteResult { quantity, value });
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    struct MockPdf {
        densities: PartonDensities,
    }

    impl PdfProvider for MockPdf {
        fn parton_densities(&self, _x: f64, _q2: f64) -> Result<PartonDensities, PdfError> {
            Ok(self.densities)
        }
    }

    fn fixture() -> PartonDensities {
        PartonDensities {
            x: 0.1,
            q2: 100.0,
            gluon: 1.25,
            up: 0.36,
            anti_up: 0.04,
            down: 0.18,
            anti_down: 0.02,
            strange: 0.015,
            anti_strange: 0.015,
            charm: 0.01,
            anti_charm: 0.01,
            bottom: 0.002,
            anti_bottom: 0.002,
        }
    }

    fn assert_close(actual: f64, expected: f64, tolerance: f64) {
        assert!(
            (actual - expected).abs() <= tolerance,
            "actual {actual:.16e}, expected {expected:.16e}, tolerance {tolerance:.3e}"
        );
    }

    #[test]
    fn applies_quark_charge_weights_and_includes_antiquarks() {
        let densities = fixture();
        let expected = (4.0 / 9.0) * (0.36 + 0.04 + 0.01 + 0.01)
            + (1.0 / 9.0) * (0.18 + 0.02 + 0.015 + 0.015 + 0.002 + 0.002);

        let actual = electromagnetic_f2_from_xf(&densities).unwrap();

        assert_close(actual, expected, 1.0e-15);
    }

    #[test]
    fn does_not_multiply_xf_values_by_x_again_or_include_gluons() {
        let mut densities = fixture();
        densities.up = 0.45;
        densities.anti_up = 0.0;
        densities.charm = 0.0;
        densities.anti_charm = 0.0;
        densities.down = 0.0;
        densities.anti_down = 0.0;
        densities.strange = 0.0;
        densities.anti_strange = 0.0;
        densities.bottom = 0.0;
        densities.anti_bottom = 0.0;
        densities.gluon = 1.0e12;

        let f2 = electromagnetic_f2_from_xf(&densities).unwrap();

        assert_close(f2, 0.2, 1.0e-15);
    }

    #[test]
    fn evaluates_f2_through_a_mock_pdf_provider() {
        let provider = MockPdf {
            densities: fixture(),
        };

        let result = evaluate_lo_structure_functions(&provider, 0.1, 100.0).unwrap();

        assert_eq!(result.densities, fixture());
        assert_close(result.f2, 0.212_666_666_666_666_64, 1.0e-15);
        assert_eq!(result.fl, 0.0);
        assert_eq!(result.xf3, 0.0);
    }

    #[test]
    fn rejects_invalid_pdf_points_before_evaluation() {
        let provider = MockPdf {
            densities: fixture(),
        };

        assert!(matches!(
            evaluate_lo_structure_functions(&provider, 0.0, 100.0),
            Err(StructureFunctionError::InvalidBjorkenX { .. })
        ));
        assert!(matches!(
            evaluate_lo_structure_functions(&provider, 1.0, 100.0),
            Err(StructureFunctionError::InvalidBjorkenX { .. })
        ));
        assert!(matches!(
            evaluate_lo_structure_functions(&provider, 0.1, 0.0),
            Err(StructureFunctionError::NonPositiveQ2 { .. })
        ));
        assert!(matches!(
            evaluate_lo_structure_functions(&provider, 0.1, f64::NAN),
            Err(StructureFunctionError::NonPositiveQ2 { .. })
        ));
    }

    #[test]
    fn rejects_non_finite_density_values() {
        let mut densities = fixture();
        densities.anti_strange = f64::INFINITY;

        let error = electromagnetic_f2_from_xf(&densities).unwrap_err();

        assert!(matches!(
            error,
            StructureFunctionError::NonFiniteDensity { flavor: "s̄", .. }
        ));
    }

    #[test]
    fn rejects_provider_results_for_a_different_point() {
        let provider = MockPdf {
            densities: fixture(),
        };

        let error = evaluate_lo_structure_functions(&provider, 0.2, 100.0).unwrap_err();

        assert!(matches!(
            error,
            StructureFunctionError::MismatchedPdfKinematics { quantity: "x", .. }
        ));
    }
}
