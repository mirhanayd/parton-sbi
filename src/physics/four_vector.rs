//! Lorentz four-vectors in the `(+,-,-,-)` metric convention.

use std::error::Error;
use std::fmt;
use std::ops::{Add, Sub};

/// A contravariant Lorentz four-vector `(E, p_x, p_y, p_z)`.
///
/// All components use a common unit. In this project's DIS calculations the
/// unit is GeV. The Minkowski metric is `g = diag(+1, -1, -1, -1)`, so
/// `a · b = a.E b.E - a.p⃗ · b.p⃗` and `p² = E² - |p⃗|²`.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct FourVector {
    pub e: f64,
    pub px: f64,
    pub py: f64,
    pub pz: f64,
}

/// Validation failure for a four-vector component.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum FourVectorError {
    NonFiniteComponent { component: &'static str, value: f64 },
}

impl fmt::Display for FourVectorError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NonFiniteComponent { component, value } => {
                write!(
                    formatter,
                    "four-vector component {component} is not finite: {value}"
                )
            }
        }
    }
}

impl Error for FourVectorError {}

impl FourVector {
    /// Construct a four-vector without changing or clamping any component.
    #[must_use]
    pub const fn new(e: f64, px: f64, py: f64, pz: f64) -> Self {
        Self { e, px, py, pz }
    }

    /// Construct and immediately validate a four-vector.
    pub fn try_new(e: f64, px: f64, py: f64, pz: f64) -> Result<Self, FourVectorError> {
        let vector = Self::new(e, px, py, pz);
        vector.validate()?;
        Ok(vector)
    }

    /// Return `true` only when every component is finite.
    #[must_use]
    pub fn is_finite(&self) -> bool {
        self.e.is_finite() && self.px.is_finite() && self.py.is_finite() && self.pz.is_finite()
    }

    /// Reject the first NaN or infinite component.
    pub fn validate(&self) -> Result<(), FourVectorError> {
        for (component, value) in [
            ("e", self.e),
            ("px", self.px),
            ("py", self.py),
            ("pz", self.pz),
        ] {
            if !value.is_finite() {
                return Err(FourVectorError::NonFiniteComponent { component, value });
            }
        }
        Ok(())
    }

    /// Minkowski dot product using `g = diag(+1, -1, -1, -1)`.
    #[must_use]
    pub fn dot(self, other: Self) -> f64 {
        self.e * other.e - self.px * other.px - self.py * other.py - self.pz * other.pz
    }

    /// Invariant mass squared, `p² = E² - |p⃗|²`.
    #[must_use]
    pub fn mass_squared(self) -> f64 {
        self.dot(self)
    }

    /// Euclidean magnitude of the spatial momentum `|p⃗|`.
    #[must_use]
    pub fn spatial_momentum(self) -> f64 {
        self.px.hypot(self.py).hypot(self.pz)
    }

    /// Transverse momentum `p_T = sqrt(p_x² + p_y²)`.
    #[must_use]
    pub fn transverse_momentum(self) -> f64 {
        self.px.hypot(self.py)
    }
}

impl Add for FourVector {
    type Output = Self;

    fn add(self, other: Self) -> Self::Output {
        Self::new(
            self.e + other.e,
            self.px + other.px,
            self.py + other.py,
            self.pz + other.pz,
        )
    }
}

impl Sub for FourVector {
    type Output = Self;

    fn sub(self, other: Self) -> Self::Output {
        Self::new(
            self.e - other.e,
            self.px - other.px,
            self.py - other.py,
            self.pz - other.pz,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn assert_close(actual: f64, expected: f64, tolerance: f64) {
        assert!(
            (actual - expected).abs() <= tolerance,
            "expected {expected:.16e}, got {actual:.16e}"
        );
    }

    #[test]
    fn arithmetic_is_component_wise() {
        let first = FourVector::new(5.0, 1.0, -2.0, 3.0);
        let second = FourVector::new(2.0, -4.0, 1.0, 0.5);
        let sum = first + second;
        let difference = first - second;

        assert_close(sum.e, 7.0, f64::EPSILON);
        assert_close(sum.px, -3.0, f64::EPSILON);
        assert_close(sum.py, -1.0, f64::EPSILON);
        assert_close(sum.pz, 3.5, f64::EPSILON);
        assert_close(difference.e, 3.0, f64::EPSILON);
        assert_close(difference.px, 5.0, f64::EPSILON);
        assert_close(difference.py, -3.0, f64::EPSILON);
        assert_close(difference.pz, 2.5, f64::EPSILON);
    }

    #[test]
    fn minkowski_metric_has_positive_time_and_negative_space_signs() {
        let time_like = FourVector::new(2.0, 0.0, 0.0, 0.0);
        let space_like = FourVector::new(0.0, 1.0, 2.0, 2.0);

        assert_close(time_like.mass_squared(), 4.0, f64::EPSILON);
        assert_close(space_like.mass_squared(), -9.0, f64::EPSILON);
        assert_close(time_like.dot(space_like), 0.0, f64::EPSILON);
    }

    #[test]
    fn invariant_mass_and_momentum_magnitudes_are_consistent() {
        let vector = FourVector::new(5.0, 3.0, 4.0, 0.0);

        assert_close(vector.mass_squared(), 0.0, f64::EPSILON);
        assert_close(vector.spatial_momentum(), 5.0, f64::EPSILON);
        assert_close(vector.transverse_momentum(), 5.0, f64::EPSILON);
    }

    #[test]
    fn non_finite_components_are_rejected() {
        let cases = [
            (FourVector::new(f64::NAN, 0.0, 0.0, 0.0), "e"),
            (FourVector::new(1.0, f64::INFINITY, 0.0, 0.0), "px"),
            (FourVector::new(1.0, 0.0, f64::NEG_INFINITY, 0.0), "py"),
            (FourVector::new(1.0, 0.0, 0.0, f64::NAN), "pz"),
        ];

        for (vector, expected_component) in cases {
            let error = vector.validate().expect_err("non-finite input must fail");
            assert!(matches!(
                error,
                FourVectorError::NonFiniteComponent { component, .. }
                    if component == expected_component
            ));
        }
    }
}
