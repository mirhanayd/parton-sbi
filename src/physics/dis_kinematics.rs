//! Neutral-current inclusive electron-proton DIS kinematics.
//!
//! The implemented process is `e⁻(k) + p(P) -> e⁻(k') + X`, with exchanged
//! four-momentum `q = k - k'`. This module computes invariants only; it does
//! not model cross sections, parton distributions, or the hadronic final state.

use std::error::Error;
use std::fmt;

use super::constants::{ELECTRON_MASS_GEV, PROTON_MASS_GEV};
use super::four_vector::{FourVector, FourVectorError};

// The shell residual is formed by subtracting quantities of order E². Scale the
// tolerance with that cancellation, while keeping it tight for particles at rest.
const MASS_SHELL_TOLERANCE_ULPS: f64 = 64.0;

/// Incoming collider-frame beam momenta.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ColliderBeams {
    /// Incoming electron travelling along `+z`.
    pub electron: FourVector,
    /// Incoming proton travelling along `-z`.
    pub proton: FourVector,
}

/// Inclusive DIS invariants in GeV-based natural units.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct DisKinematics {
    /// Exchanged-boson four-momentum, `q = k - k'`, in GeV.
    pub q: FourVector,
    /// Positive momentum-transfer scale, `Q² = -q²`, in GeV².
    pub q2: f64,
    /// Squared electron-proton centre-of-mass energy, `(P + k)²`, in GeV².
    pub s: f64,
    /// Bjorken scaling variable, `x = Q² / (2 P·q)`.
    pub x: f64,
    /// Inelasticity, `y = (P·q) / (P·k)`.
    pub y: f64,
    /// Hadronic invariant mass squared, `(P + q)²`, in GeV².
    pub w2: f64,
}

/// Configurable inclusive-DIS analysis cuts.
///
/// Minimum and maximum bounds are inclusive. The physical-event validation
/// (`0 < x < 1`, `0 < y < 1`, and positive `Q²`) is always applied before
/// these analysis-specific cuts.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct DisCuts {
    pub q2_min: f64,
    pub q2_max: Option<f64>,
    pub x_min: f64,
    pub x_max: f64,
    pub y_min: f64,
    pub y_max: f64,
    pub w2_min: f64,
}

/// Typed validation failures for beam construction, DIS invariants, and cuts.
#[derive(Debug, Clone, PartialEq)]
pub enum DisError {
    NonFiniteInput {
        quantity: &'static str,
        value: f64,
    },
    InvalidFourVector {
        vector: &'static str,
        source: FourVectorError,
    },
    NonPositiveEnergy {
        particle: &'static str,
        energy: f64,
    },
    EnergyBelowRestMass {
        particle: &'static str,
        energy: f64,
        mass: f64,
    },
    OffMassShell {
        particle: &'static str,
        invariant_mass_squared: f64,
        expected_mass_squared: f64,
        tolerance: f64,
    },
    InvalidScatteringAngle {
        theta_deg: f64,
    },
    NonFiniteResult {
        quantity: &'static str,
        value: f64,
    },
    InvalidDenominator {
        quantity: &'static str,
        value: f64,
    },
    NonPositiveQ2 {
        q2: f64,
    },
    UnphysicalS {
        s: f64,
    },
    InvalidBjorkenX {
        x: f64,
    },
    InvalidInelasticity {
        y: f64,
    },
    UnphysicalW2 {
        w2: f64,
        minimum: f64,
    },
    InvalidCutValue {
        quantity: &'static str,
        value: f64,
    },
    InvalidCutRange {
        quantity: &'static str,
        minimum: f64,
        maximum: f64,
    },
}

impl fmt::Display for DisError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NonFiniteInput { quantity, value } => {
                write!(formatter, "{quantity} is not finite: {value}")
            }
            Self::InvalidFourVector { vector, source } => {
                write!(formatter, "invalid {vector} four-vector: {source}")
            }
            Self::NonPositiveEnergy { particle, energy } => {
                write!(
                    formatter,
                    "{particle} energy must be positive, got {energy} GeV"
                )
            }
            Self::EnergyBelowRestMass {
                particle,
                energy,
                mass,
            } => write!(
                formatter,
                "{particle} energy {energy} GeV is below its rest mass {mass} GeV"
            ),
            Self::OffMassShell {
                particle,
                invariant_mass_squared,
                expected_mass_squared,
                tolerance,
            } => write!(
                formatter,
                "{particle} is off mass shell: p² = {invariant_mass_squared} GeV², expected {expected_mass_squared} GeV² within {tolerance} GeV²"
            ),
            Self::InvalidScatteringAngle { theta_deg } => write!(
                formatter,
                "scattering angle must be in [0, 180] degrees, got {theta_deg}"
            ),
            Self::NonFiniteResult { quantity, value } => {
                write!(formatter, "derived {quantity} is not finite: {value}")
            }
            Self::InvalidDenominator { quantity, value } => write!(
                formatter,
                "DIS denominator {quantity} must be finite and positive, got {value}"
            ),
            Self::NonPositiveQ2 { q2 } => {
                write!(formatter, "DIS requires Q² > 0, got {q2} GeV²")
            }
            Self::UnphysicalS { s } => {
                write!(formatter, "DIS requires s > 0, got {s} GeV²")
            }
            Self::InvalidBjorkenX { x } => {
                write!(formatter, "Bjorken x must satisfy 0 < x < 1, got {x}")
            }
            Self::InvalidInelasticity { y } => {
                write!(formatter, "inelasticity y must satisfy 0 < y < 1, got {y}")
            }
            Self::UnphysicalW2 { w2, minimum } => write!(
                formatter,
                "inelastic DIS requires W² > m_p² = {minimum} GeV², got {w2} GeV²"
            ),
            Self::InvalidCutValue { quantity, value } => {
                write!(formatter, "cut {quantity} has an invalid value: {value}")
            }
            Self::InvalidCutRange {
                quantity,
                minimum,
                maximum,
            } => write!(
                formatter,
                "cut range {quantity} is invalid: minimum {minimum}, maximum {maximum}"
            ),
        }
    }
}

impl Error for DisError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::InvalidFourVector { source, .. } => Some(source),
            _ => None,
        }
    }
}

/// Build an incoming electron travelling along `+z`.
pub fn incoming_electron(energy: f64) -> Result<FourVector, DisError> {
    let momentum = momentum_from_energy(energy, ELECTRON_MASS_GEV, "incoming electron")?;
    FourVector::try_new(energy, 0.0, 0.0, momentum).map_err(|source| DisError::InvalidFourVector {
        vector: "incoming electron",
        source,
    })
}

/// Build an incoming proton travelling along `-z`.
pub fn incoming_proton(energy: f64) -> Result<FourVector, DisError> {
    let momentum = momentum_from_energy(energy, PROTON_MASS_GEV, "incoming proton")?;
    FourVector::try_new(energy, 0.0, 0.0, -momentum).map_err(|source| DisError::InvalidFourVector {
        vector: "incoming proton",
        source,
    })
}

/// Build the counter-propagating collider beams used by the CLI.
pub fn collider_beams(electron_energy: f64, proton_energy: f64) -> Result<ColliderBeams, DisError> {
    Ok(ColliderBeams {
        electron: incoming_electron(electron_energy)?,
        proton: incoming_proton(proton_energy)?,
    })
}

/// Build an outgoing on-shell electron in the `x-z` plane.
///
/// `theta_deg` is measured from the incoming electron's `+z` direction. The
/// azimuth is fixed to zero because inclusive invariants are azimuth-independent.
pub fn scattered_electron(energy: f64, theta_deg: f64) -> Result<FourVector, DisError> {
    if !theta_deg.is_finite() {
        return Err(DisError::NonFiniteInput {
            quantity: "scattering angle",
            value: theta_deg,
        });
    }
    if !(0.0..=180.0).contains(&theta_deg) {
        return Err(DisError::InvalidScatteringAngle { theta_deg });
    }

    let momentum = momentum_from_energy(energy, ELECTRON_MASS_GEV, "scattered electron")?;
    let (sin_theta, cos_theta) = theta_deg.to_radians().sin_cos();
    FourVector::try_new(energy, momentum * sin_theta, 0.0, momentum * cos_theta).map_err(|source| {
        DisError::InvalidFourVector {
            vector: "scattered electron",
            source,
        }
    })
}

/// Compute validated neutral-current inclusive DIS invariants.
///
/// No unphysical value is clamped. Inputs and derived quantities that do not
/// satisfy the DIS physical domain return a typed [`DisError`].
pub fn compute_dis_kinematics(
    proton: FourVector,
    incoming: FourVector,
    outgoing: FourVector,
) -> Result<DisKinematics, DisError> {
    validate_particle(proton, "incoming proton", PROTON_MASS_GEV)?;
    validate_particle(incoming, "incoming electron", ELECTRON_MASS_GEV)?;
    validate_particle(outgoing, "scattered electron", ELECTRON_MASS_GEV)?;

    let q = incoming - outgoing;
    q.validate().map_err(|source| DisError::InvalidFourVector {
        vector: "exchanged boson q",
        source,
    })?;

    let q2 = -q.mass_squared();
    validate_q2(q2)?;

    let p_dot_q = proton.dot(q);
    validate_result("P·q", p_dot_q)?;
    let x_denominator = 2.0 * p_dot_q;
    validate_denominator("2 P·q", x_denominator)?;

    let p_dot_k = proton.dot(incoming);
    validate_result("P·k", p_dot_k)?;
    validate_denominator("P·k", p_dot_k)?;

    let total_initial = proton + incoming;
    total_initial
        .validate()
        .map_err(|source| DisError::InvalidFourVector {
            vector: "total initial state P + k",
            source,
        })?;
    let s = total_initial.mass_squared();
    validate_s(s)?;

    let x = q2 / x_denominator;
    validate_bjorken_x(x)?;

    let y = p_dot_q / p_dot_k;
    validate_inelasticity(y)?;

    let hadronic_state = proton + q;
    hadronic_state
        .validate()
        .map_err(|source| DisError::InvalidFourVector {
            vector: "hadronic state P + q",
            source,
        })?;
    let w2 = hadronic_state.mass_squared();
    validate_w2(w2)?;

    Ok(DisKinematics { q, q2, s, x, y, w2 })
}

impl DisKinematics {
    /// Return whether this already-validated event passes all supplied cuts.
    pub fn passes_cuts(&self, cuts: &DisCuts) -> Result<bool, DisError> {
        cuts.accepts(self)
    }
}

impl DisCuts {
    /// Validate the cut configuration itself.
    pub fn validate(&self) -> Result<(), DisError> {
        validate_cut_value("q2_min", self.q2_min)?;
        if self.q2_min < 0.0 {
            return Err(DisError::InvalidCutValue {
                quantity: "q2_min",
                value: self.q2_min,
            });
        }

        if let Some(q2_max) = self.q2_max {
            validate_cut_value("q2_max", q2_max)?;
            if q2_max < self.q2_min {
                return Err(DisError::InvalidCutRange {
                    quantity: "Q²",
                    minimum: self.q2_min,
                    maximum: q2_max,
                });
            }
        }

        validate_unit_interval("x", self.x_min, self.x_max)?;
        validate_unit_interval("y", self.y_min, self.y_max)?;
        validate_cut_value("w2_min", self.w2_min)?;
        if self.w2_min < 0.0 {
            return Err(DisError::InvalidCutValue {
                quantity: "w2_min",
                value: self.w2_min,
            });
        }
        Ok(())
    }

    /// Return `true` when an event lies inside every inclusive cut boundary.
    pub fn accepts(&self, event: &DisKinematics) -> Result<bool, DisError> {
        self.validate()?;
        validate_event_fields(event)?;
        Ok(event.q2 >= self.q2_min
            && self.q2_max.is_none_or(|maximum| event.q2 <= maximum)
            && event.x >= self.x_min
            && event.x <= self.x_max
            && event.y >= self.y_min
            && event.y <= self.y_max
            && event.w2 >= self.w2_min)
    }
}

fn momentum_from_energy(energy: f64, mass: f64, particle: &'static str) -> Result<f64, DisError> {
    if !energy.is_finite() {
        return Err(DisError::NonFiniteInput {
            quantity: particle,
            value: energy,
        });
    }
    if energy <= 0.0 {
        return Err(DisError::NonPositiveEnergy { particle, energy });
    }
    if energy < mass {
        return Err(DisError::EnergyBelowRestMass {
            particle,
            energy,
            mass,
        });
    }

    let momentum = ((energy - mass) * (energy + mass)).sqrt();
    validate_result("beam momentum", momentum)?;
    Ok(momentum)
}

fn validate_particle(
    vector: FourVector,
    name: &'static str,
    rest_mass: f64,
) -> Result<(), DisError> {
    vector
        .validate()
        .map_err(|source| DisError::InvalidFourVector {
            vector: name,
            source,
        })?;
    if vector.e <= 0.0 {
        return Err(DisError::NonPositiveEnergy {
            particle: name,
            energy: vector.e,
        });
    }
    if vector.e < rest_mass {
        return Err(DisError::EnergyBelowRestMass {
            particle: name,
            energy: vector.e,
            mass: rest_mass,
        });
    }

    let invariant_mass_squared = vector.mass_squared();
    validate_result("particle invariant mass squared", invariant_mass_squared)?;
    let expected_mass_squared = rest_mass * rest_mass;
    let cancellation_scale = vector.e * vector.e
        + vector.px * vector.px
        + vector.py * vector.py
        + vector.pz * vector.pz
        + expected_mass_squared;
    validate_result("mass-shell tolerance scale", cancellation_scale)?;
    let tolerance = MASS_SHELL_TOLERANCE_ULPS * f64::EPSILON * cancellation_scale.max(1.0);
    if (invariant_mass_squared - expected_mass_squared).abs() > tolerance {
        return Err(DisError::OffMassShell {
            particle: name,
            invariant_mass_squared,
            expected_mass_squared,
            tolerance,
        });
    }
    Ok(())
}

fn validate_event_fields(event: &DisKinematics) -> Result<(), DisError> {
    event
        .q
        .validate()
        .map_err(|source| DisError::InvalidFourVector {
            vector: "stored exchanged boson q",
            source,
        })?;
    validate_q2(event.q2)?;
    validate_s(event.s)?;
    validate_bjorken_x(event.x)?;
    validate_inelasticity(event.y)?;
    validate_w2(event.w2)
}

fn validate_q2(q2: f64) -> Result<(), DisError> {
    validate_result("Q²", q2)?;
    if q2 <= 0.0 {
        Err(DisError::NonPositiveQ2 { q2 })
    } else {
        Ok(())
    }
}

fn validate_s(s: f64) -> Result<(), DisError> {
    validate_result("s", s)?;
    if s <= 0.0 {
        Err(DisError::UnphysicalS { s })
    } else {
        Ok(())
    }
}

fn validate_bjorken_x(x: f64) -> Result<(), DisError> {
    validate_result("Bjorken x", x)?;
    if x <= 0.0 || x >= 1.0 {
        Err(DisError::InvalidBjorkenX { x })
    } else {
        Ok(())
    }
}

fn validate_inelasticity(y: f64) -> Result<(), DisError> {
    validate_result("inelasticity y", y)?;
    if y <= 0.0 || y >= 1.0 {
        Err(DisError::InvalidInelasticity { y })
    } else {
        Ok(())
    }
}

fn validate_w2(w2: f64) -> Result<(), DisError> {
    validate_result("W²", w2)?;
    let minimum = PROTON_MASS_GEV * PROTON_MASS_GEV;
    if w2 <= minimum {
        Err(DisError::UnphysicalW2 { w2, minimum })
    } else {
        Ok(())
    }
}

fn validate_result(quantity: &'static str, value: f64) -> Result<(), DisError> {
    if value.is_finite() {
        Ok(())
    } else {
        Err(DisError::NonFiniteResult { quantity, value })
    }
}

fn validate_denominator(quantity: &'static str, value: f64) -> Result<(), DisError> {
    if value <= 0.0 {
        Err(DisError::InvalidDenominator { quantity, value })
    } else {
        Ok(())
    }
}

fn validate_cut_value(quantity: &'static str, value: f64) -> Result<(), DisError> {
    if value.is_finite() {
        Ok(())
    } else {
        Err(DisError::InvalidCutValue { quantity, value })
    }
}

fn validate_unit_interval(
    quantity: &'static str,
    minimum: f64,
    maximum: f64,
) -> Result<(), DisError> {
    validate_cut_value(quantity, minimum)?;
    validate_cut_value(quantity, maximum)?;
    if minimum < 0.0 || maximum > 1.0 || minimum > maximum {
        return Err(DisError::InvalidCutRange {
            quantity,
            minimum,
            maximum,
        });
    }
    Ok(())
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

    fn reference_event() -> DisKinematics {
        let beams = collider_beams(27.5, 920.0).expect("reference beams must be valid");
        let outgoing = scattered_electron(15.0, 20.0).expect("reference electron must be valid");
        compute_dis_kinematics(beams.proton, beams.electron, outgoing)
            .expect("reference event must be physical")
    }

    #[test]
    fn collider_beams_are_on_shell_and_counter_propagating() {
        let beams = collider_beams(27.5, 920.0).expect("beam construction should succeed");

        assert!(beams.electron.pz > 0.0);
        assert!(beams.proton.pz < 0.0);
        assert_close(
            beams.electron.mass_squared(),
            ELECTRON_MASS_GEV * ELECTRON_MASS_GEV,
            1e-12,
        );
        assert_close(
            beams.proton.mass_squared(),
            PROTON_MASS_GEV * PROTON_MASS_GEV,
            1e-9,
        );
    }

    #[test]
    fn valid_event_satisfies_the_hadronic_mass_identity() {
        let event = reference_event();
        let identity = PROTON_MASS_GEV * PROTON_MASS_GEV + event.q2 * (1.0 / event.x - 1.0);

        assert!(event.q2 > 0.0);
        assert!(event.x > 0.0 && event.x < 1.0);
        assert!(event.y > 0.0 && event.y < 1.0);
        assert_close(event.w2, identity, 2e-9);
    }

    #[test]
    fn zero_momentum_transfer_is_rejected() {
        let beams = collider_beams(27.5, 920.0).expect("beam construction should succeed");
        let error = compute_dis_kinematics(beams.proton, beams.electron, beams.electron)
            .expect_err("Q² = 0 must be rejected");

        assert!(matches!(error, DisError::NonPositiveQ2 { .. }));
    }

    #[test]
    fn timelike_momentum_transfer_is_rejected_as_negative_q2() {
        let error = validate_q2(-1.0).expect_err("timelike q must produce invalid negative Q²");

        assert!(matches!(error, DisError::NonPositiveQ2 { q2 } if q2 < 0.0));
    }

    #[test]
    fn off_mass_shell_external_particles_are_rejected() {
        let beams = collider_beams(27.5, 920.0).expect("beam construction should succeed");
        let wrong_mass_outgoing = FourVector::new(15.0, 0.0, 0.0, 0.0);
        let error = compute_dis_kinematics(beams.proton, beams.electron, wrong_mass_outgoing)
            .expect_err("a 15 GeV invariant-mass electron must be rejected");

        assert!(matches!(
            error,
            DisError::OffMassShell {
                particle: "scattered electron",
                ..
            }
        ));
    }

    #[test]
    fn bjorken_x_outside_the_open_unit_interval_is_rejected() {
        let proton = FourVector::new(PROTON_MASS_GEV, 0.0, 0.0, 0.0);
        let incoming = incoming_electron(10.0).expect("incoming electron should be valid");
        let outgoing = scattered_electron(9.0, 60.0).expect("outgoing electron should be valid");
        let error =
            compute_dis_kinematics(proton, incoming, outgoing).expect_err("x > 1 must be rejected");

        assert!(matches!(error, DisError::InvalidBjorkenX { x } if x > 1.0));
    }

    #[test]
    fn inelasticity_outside_the_open_unit_interval_is_rejected() {
        let error = validate_inelasticity(1.25).expect_err("y > 1 must be rejected");

        assert!(matches!(error, DisError::InvalidInelasticity { y } if y > 1.0));
    }

    #[test]
    fn invalid_denominator_is_reported_without_clamping() {
        let error = validate_denominator("P·k", 0.0).expect_err("P·k = 0 must be rejected");

        assert!(matches!(
            error,
            DisError::InvalidDenominator {
                quantity: "P·k",
                ..
            }
        ));
    }

    #[test]
    fn zero_p_dot_q_denominator_is_reported() {
        let error = validate_denominator("2 P·q", 0.0).expect_err("P·q = 0 must be rejected");

        assert!(matches!(
            error,
            DisError::InvalidDenominator {
                quantity: "2 P·q",
                ..
            }
        ));
    }

    #[test]
    fn unphysical_hadronic_mass_is_rejected() {
        let error = validate_w2(-2.0).expect_err("negative W² must be rejected");

        assert!(matches!(error, DisError::UnphysicalW2 { w2, .. } if w2 < 0.0));
    }

    #[test]
    fn beam_energy_and_angle_validation_are_typed() {
        assert!(matches!(
            incoming_proton(0.0),
            Err(DisError::NonPositiveEnergy { .. })
        ));
        assert!(matches!(
            incoming_electron(ELECTRON_MASS_GEV / 2.0),
            Err(DisError::EnergyBelowRestMass { .. })
        ));
        assert!(matches!(
            scattered_electron(1.0, 181.0),
            Err(DisError::InvalidScatteringAngle { .. })
        ));
        assert!(matches!(
            collider_beams(f64::NAN, 920.0),
            Err(DisError::NonFiniteInput { .. })
        ));
    }

    #[test]
    fn cuts_accept_and_reject_without_modifying_the_event() {
        let event = reference_event();
        let accepting = DisCuts {
            q2_min: 10.0,
            q2_max: Some(100.0),
            x_min: 0.001,
            x_max: 0.01,
            y_min: 0.1,
            y_max: 0.8,
            w2_min: 4.0,
        };
        let rejecting = DisCuts {
            q2_min: 50.0,
            ..accepting
        };

        assert!(accepting.accepts(&event).expect("cuts should be valid"));
        assert!(!rejecting.accepts(&event).expect("cuts should be valid"));
    }

    #[test]
    fn malformed_cut_ranges_are_rejected() {
        let cuts = DisCuts {
            q2_min: 1.0,
            q2_max: None,
            x_min: 0.9,
            x_max: 0.1,
            y_min: 0.0,
            y_max: 1.0,
            w2_min: 4.0,
        };

        assert!(matches!(
            cuts.validate(),
            Err(DisError::InvalidCutRange { quantity: "x", .. })
        ));
    }

    #[test]
    fn inclusive_cut_boundaries_can_select_an_exact_value() {
        let event = reference_event();
        let cuts = DisCuts {
            q2_min: event.q2,
            q2_max: Some(event.q2),
            x_min: event.x,
            x_max: event.x,
            y_min: event.y,
            y_max: event.y,
            w2_min: event.w2,
        };

        assert!(cuts
            .accepts(&event)
            .expect("exact inclusive cuts are valid"));
    }

    #[test]
    fn cuts_reject_forged_non_finite_event_fields() {
        let mut event = reference_event();
        event.q2 = f64::INFINITY;
        let cuts = DisCuts {
            q2_min: 0.0,
            q2_max: None,
            x_min: 0.0,
            x_max: 1.0,
            y_min: 0.0,
            y_max: 1.0,
            w2_min: 0.0,
        };

        assert!(matches!(
            cuts.accepts(&event),
            Err(DisError::NonFiniteResult {
                quantity: "Q²", ..
            })
        ));

        let mut event = reference_event();
        event.q.px = f64::NAN;
        assert!(matches!(
            cuts.accepts(&event),
            Err(DisError::InvalidFourVector {
                vector: "stored exchanged boson q",
                ..
            })
        ));
    }
}
