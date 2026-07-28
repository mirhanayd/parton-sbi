//! Phase 1B-D0 input-scale continuous PDF family.
//!
//! This module implements only the mathematical boundary condition at the
//! authoritative LHAPDF lower scale. It does not evolve PDFs, write LHAPDF
//! artifacts, couple to PYTHIA, or generate events.

use std::collections::BTreeMap;
use std::error::Error;
use std::ffi::{CStr, CString};
use std::fmt;
use std::os::raw::{c_char, c_int};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use super::{LhapdfProvider, PdfError, PdfSupportBounds};

pub const CONTINUOUS_PDF_SCHEMA_VERSION: &str = "partonsbi.pdf_parameter_point.v1";
pub const CONTINUOUS_PDF_FAMILY_VERSION: &str = "ct18nlo_two_parameter_boundary_v1";
pub const PILOT_DOMAIN_VERSION: &str = "phase1bd_d0_pilot_box_v1";
pub const INTEGRATION_POLICY_VERSION: &str = "logx_gk15_gl64_v1";
pub const DELTA_V_MIN: f64 = -0.20;
pub const DELTA_V_MAX: f64 = 0.20;
pub const LAMBDA_SEA_MIN: f64 = -0.25;
pub const LAMBDA_SEA_MAX: f64 = 0.25;
pub const VALENCE_PIVOT_X: f64 = 0.1;
pub const CONSTRUCTION_TOLERANCE: f64 = 1.0e-8;
pub const INDEPENDENT_TOLERANCE: f64 = 1.0e-6;
pub const REFINEMENT_TOLERANCE: f64 = 1.0e-8;
pub const NEGATIVE_FAIL_TOLERANCE: f64 = -1.0e-12;
pub const HEAVY_BOUNDARY_TOLERANCE_XF: f64 = 1.0e-10;

const GLUON: i32 = 21;
const DOWN: i32 = 1;
const UP: i32 = 2;
const STRANGE: i32 = 3;
const CHARM: i32 = 4;
const BOTTOM: i32 = 5;
const BRIDGE_FLAVOR_CAPACITY: usize = 32;
const BRIDGE_X_KNOT_CAPACITY: usize = 4096;

/// A typed D0 failure. No variant repairs or clamps an invalid construction.
#[derive(Debug, Clone, PartialEq)]
pub enum ContinuousPdfError {
    InvalidTheta {
        name: &'static str,
        value: f64,
        requirement: &'static str,
    },
    MetadataUnavailable(String),
    MetadataInvalid(String),
    Pdf(PdfError),
    NonFiniteDensity {
        flavor: i32,
        x: f64,
        value: f64,
    },
    InvalidNormalization {
        name: &'static str,
        value: f64,
    },
    HeavyFlavorBoundary {
        flavor: i32,
        x: f64,
        xf: f64,
    },
    IntegrationDidNotConverge {
        interval_start: f64,
        interval_end: f64,
        estimated_error: f64,
        limit: usize,
    },
    IdentitySerialization(String),
}

impl fmt::Display for ContinuousPdfError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidTheta {
                name,
                value,
                requirement,
            } => write!(f, "invalid {name}={value}: {requirement}"),
            Self::MetadataUnavailable(message) => {
                write!(f, "authoritative LHAPDF metadata unavailable: {message}")
            }
            Self::MetadataInvalid(message) => {
                write!(f, "authoritative LHAPDF metadata is inconsistent: {message}")
            }
            Self::Pdf(error) => write!(f, "{error}"),
            Self::NonFiniteDensity { flavor, x, value } => {
                write!(f, "non-finite density for flavor {flavor} at x={x}: {value}")
            }
            Self::InvalidNormalization { name, value } => {
                write!(f, "{name} normalization must be finite and positive, got {value}")
            }
            Self::HeavyFlavorBoundary { flavor, x, xf } => write!(
                f,
                "heavy flavor {flavor} has xf={xf} at x={x}, Q0; expected zero within {HEAVY_BOUNDARY_TOLERANCE_XF}"
            ),
            Self::IntegrationDidNotConverge {
                interval_start,
                interval_end,
                estimated_error,
                limit,
            } => write!(
                f,
                "quadrature did not converge on [{interval_start}, {interval_end}]: estimated error {estimated_error}, subdivision limit {limit}"
            ),
            Self::IdentitySerialization(message) => {
                write!(f, "canonical identity serialization failed: {message}")
            }
        }
    }
}

impl Error for ContinuousPdfError {}

impl From<PdfError> for ContinuousPdfError {
    fn from(value: PdfError) -> Self {
        Self::Pdf(value)
    }
}

/// Canonical two-parameter point. Signed zero is normalized to positive zero.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct PdfTheta {
    pub delta_v: f64,
    pub lambda_sea: f64,
}

impl PdfTheta {
    pub fn new(delta_v: f64, lambda_sea: f64) -> Result<Self, ContinuousPdfError> {
        Self::new_with_scope(delta_v, lambda_sea, false)
    }

    fn guard(delta_v: f64, lambda_sea: f64) -> Result<Self, ContinuousPdfError> {
        Self::new_with_scope(delta_v, lambda_sea, true)
    }

    fn new_with_scope(
        delta_v: f64,
        lambda_sea: f64,
        guard: bool,
    ) -> Result<Self, ContinuousPdfError> {
        let delta_v = canonical_zero(delta_v);
        let lambda_sea = canonical_zero(lambda_sea);
        if !delta_v.is_finite() {
            return Err(ContinuousPdfError::InvalidTheta {
                name: "delta_v",
                value: delta_v,
                requirement: "must be finite",
            });
        }
        if !lambda_sea.is_finite() {
            return Err(ContinuousPdfError::InvalidTheta {
                name: "lambda_sea",
                value: lambda_sea,
                requirement: "must be finite",
            });
        }
        let expansion = if guard { 1.05 } else { 1.0 };
        let delta_limit = DELTA_V_MAX * expansion;
        let lambda_limit = LAMBDA_SEA_MAX * expansion;
        if delta_v < -delta_limit || delta_v > delta_limit {
            return Err(ContinuousPdfError::InvalidTheta {
                name: "delta_v",
                value: delta_v,
                requirement: if guard {
                    "outside the deterministic 5% guard domain"
                } else {
                    "outside the hard pilot domain [-0.20, 0.20]"
                },
            });
        }
        if lambda_sea < -lambda_limit || lambda_sea > lambda_limit {
            return Err(ContinuousPdfError::InvalidTheta {
                name: "lambda_sea",
                value: lambda_sea,
                requirement: if guard {
                    "outside the deterministic 5% guard domain"
                } else {
                    "outside the hard pilot domain [-0.25, 0.25]"
                },
            });
        }
        Ok(Self {
            delta_v,
            lambda_sea,
        })
    }
}

fn canonical_zero(value: f64) -> f64 {
    if value == 0.0 {
        0.0
    } else {
        value
    }
}

/// Authoritative baseline contract loaded from the installed LHAPDF member.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ContinuousPdfMetadata {
    pub set_name: String,
    pub member: i32,
    pub data_version: i32,
    pub order_qcd: i32,
    pub q0_gev: f64,
    pub support: PdfSupportBounds,
    pub supported_flavors: Vec<i32>,
    pub alpha_s_mz: f64,
    pub charm_mass_gev: f64,
    pub charm_threshold_gev: f64,
    pub bottom_mass_gev: f64,
    pub bottom_threshold_gev: f64,
    pub flavor_scheme: String,
    pub lhapdf_version: String,
    pub x_knots: Vec<f64>,
}

#[repr(C)]
struct RawMetadata {
    data_version: c_int,
    order_qcd: c_int,
    alpha_s_mz: f64,
    charm_mass_gev: f64,
    charm_threshold_gev: f64,
    bottom_mass_gev: f64,
    bottom_threshold_gev: f64,
}

impl Default for RawMetadata {
    fn default() -> Self {
        Self {
            data_version: 0,
            order_qcd: 0,
            alpha_s_mz: f64::NAN,
            charm_mass_gev: f64::NAN,
            charm_threshold_gev: f64::NAN,
            bottom_mass_gev: f64::NAN,
            bottom_threshold_gev: f64::NAN,
        }
    }
}

extern "C" {
    fn partonsbi_lhapdf_member_metadata(
        set_name: *const c_char,
        member: c_int,
        data_version: *mut c_int,
        order_qcd: *mut c_int,
        alpha_s_mz: *mut f64,
        charm_mass_gev: *mut f64,
        charm_threshold_gev: *mut f64,
        bottom_mass_gev: *mut f64,
        bottom_threshold_gev: *mut f64,
        flavor_scheme: *mut c_char,
        flavor_scheme_size: usize,
        lhapdf_version: *mut c_char,
        lhapdf_version_size: usize,
        flavors: *mut c_int,
        flavor_capacity: usize,
        flavor_count: *mut usize,
        x_knots: *mut f64,
        x_knot_capacity: usize,
        x_knot_count: *mut usize,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> c_int;
}

impl ContinuousPdfMetadata {
    pub fn load(set_name: &str, member: i32) -> Result<Self, ContinuousPdfError> {
        let provider = LhapdfProvider::new(set_name, member)?;
        let c_set = CString::new(set_name)
            .map_err(|_| ContinuousPdfError::MetadataInvalid("set name contains NUL".into()))?;
        let mut raw = RawMetadata::default();
        let mut scheme = [0 as c_char; 128];
        let mut version = [0 as c_char; 128];
        let mut flavors = [0 as c_int; BRIDGE_FLAVOR_CAPACITY];
        let mut flavor_count = 0usize;
        let mut x_knots = [0.0; BRIDGE_X_KNOT_CAPACITY];
        let mut x_knot_count = 0usize;
        let mut error_buffer = [0 as c_char; 1024];
        // SAFETY: all buffers are valid for the duration of the call and the
        // C++ bridge catches every exception before crossing the ABI.
        let status = unsafe {
            partonsbi_lhapdf_member_metadata(
                c_set.as_ptr(),
                member,
                &mut raw.data_version,
                &mut raw.order_qcd,
                &mut raw.alpha_s_mz,
                &mut raw.charm_mass_gev,
                &mut raw.charm_threshold_gev,
                &mut raw.bottom_mass_gev,
                &mut raw.bottom_threshold_gev,
                scheme.as_mut_ptr(),
                scheme.len(),
                version.as_mut_ptr(),
                version.len(),
                flavors.as_mut_ptr(),
                flavors.len(),
                &mut flavor_count,
                x_knots.as_mut_ptr(),
                x_knots.len(),
                &mut x_knot_count,
                error_buffer.as_mut_ptr(),
                error_buffer.len(),
            )
        };
        if status != 0 {
            // SAFETY: snprintf in the bridge always NUL-terminates the buffer.
            let message = unsafe { CStr::from_ptr(error_buffer.as_ptr()) }
                .to_string_lossy()
                .into_owned();
            return Err(ContinuousPdfError::MetadataUnavailable(message));
        }
        if flavor_count > flavors.len() || x_knot_count > x_knots.len() {
            return Err(ContinuousPdfError::MetadataInvalid(
                "bridge returned an invalid output count".into(),
            ));
        }
        // SAFETY: both fixed buffers were initialized with NUL bytes.
        let flavor_scheme = unsafe { CStr::from_ptr(scheme.as_ptr()) }
            .to_string_lossy()
            .into_owned();
        // SAFETY: both fixed buffers were initialized with NUL bytes.
        let lhapdf_version = unsafe { CStr::from_ptr(version.as_ptr()) }
            .to_string_lossy()
            .into_owned();
        let supported_flavors = flavors[..flavor_count].to_vec();
        let x_knots = x_knots[..x_knot_count].to_vec();
        let metadata = Self {
            set_name: set_name.to_owned(),
            member,
            data_version: raw.data_version,
            order_qcd: raw.order_qcd,
            q0_gev: provider.support_bounds().q_minimum_gev,
            support: provider.support_bounds().clone(),
            supported_flavors,
            alpha_s_mz: raw.alpha_s_mz,
            charm_mass_gev: raw.charm_mass_gev,
            charm_threshold_gev: raw.charm_threshold_gev,
            bottom_mass_gev: raw.bottom_mass_gev,
            bottom_threshold_gev: raw.bottom_threshold_gev,
            flavor_scheme,
            lhapdf_version,
            x_knots,
        };
        metadata.validate(&provider)?;
        Ok(metadata)
    }

    fn validate(&self, provider: &LhapdfProvider) -> Result<(), ContinuousPdfError> {
        if self.data_version != provider.data_version() as i32
            || self.order_qcd != provider.order_qcd()
        {
            return Err(ContinuousPdfError::MetadataInvalid(
                "managed and C++ LHAPDF metadata disagree".into(),
            ));
        }
        if self.q0_gev != self.support.q_minimum_gev {
            return Err(ContinuousPdfError::MetadataInvalid(
                "Q0 is not exactly the authoritative Q minimum".into(),
            ));
        }
        for (name, value) in [
            ("q0", self.q0_gev),
            ("alpha_s_mz", self.alpha_s_mz),
            ("charm_mass", self.charm_mass_gev),
            ("charm_threshold", self.charm_threshold_gev),
            ("bottom_mass", self.bottom_mass_gev),
            ("bottom_threshold", self.bottom_threshold_gev),
        ] {
            if !value.is_finite() || value <= 0.0 {
                return Err(ContinuousPdfError::MetadataInvalid(format!(
                    "{name} must be finite and positive, got {value}"
                )));
            }
        }
        let required = [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 21];
        if required
            .iter()
            .any(|flavor| !self.supported_flavors.contains(flavor))
        {
            return Err(ContinuousPdfError::MetadataInvalid(format!(
                "required flavors are missing from {:?}",
                self.supported_flavors
            )));
        }
        if self.flavor_scheme.trim().is_empty()
            || self.lhapdf_version.trim().is_empty()
            || self.x_knots.len() < 2
            || self.x_knots.iter().any(|x| !x.is_finite() || *x <= 0.0)
            || self.x_knots.windows(2).any(|pair| pair[0] >= pair[1])
            || self.x_knots.last().copied() != Some(1.0)
        {
            return Err(ContinuousPdfError::MetadataInvalid(
                "flavor scheme, version, or x-knot contract is invalid".into(),
            ));
        }
        Ok(())
    }
}

/// Separate flavor-number densities. Momentum is `x` times the sum of each
/// field exactly once; quarks already include their corresponding sea term.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct NumberDensities {
    pub gluon: f64,
    pub up: f64,
    pub anti_up: f64,
    pub down: f64,
    pub anti_down: f64,
    pub strange: f64,
    pub anti_strange: f64,
    pub charm: f64,
    pub anti_charm: f64,
    pub bottom: f64,
    pub anti_bottom: f64,
}

impl NumberDensities {
    pub fn flavor(self, id: i32) -> Option<f64> {
        match id {
            21 => Some(self.gluon),
            2 => Some(self.up),
            -2 => Some(self.anti_up),
            1 => Some(self.down),
            -1 => Some(self.anti_down),
            3 => Some(self.strange),
            -3 => Some(self.anti_strange),
            4 => Some(self.charm),
            -4 => Some(self.anti_charm),
            5 => Some(self.bottom),
            -5 => Some(self.anti_bottom),
            _ => None,
        }
    }

    pub fn momentum_integrand(self, x: f64) -> f64 {
        x * (self.gluon
            + self.up
            + self.anti_up
            + self.down
            + self.anti_down
            + self.strange
            + self.anti_strange
            + self.charm
            + self.anti_charm
            + self.bottom
            + self.anti_bottom)
    }
}

/// Positive normalization constants fixed by the three proton sum rules.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct PdfNormalizations {
    pub a_u: f64,
    pub a_d: f64,
    pub sea_scale: f64,
    pub a_g: f64,
}

/// One fully constructed input-scale parameter point.
#[derive(Debug)]
pub struct ContinuousPdfPoint<'a> {
    context: &'a ContinuousPdfContext,
    pub theta: PdfTheta,
    pub normalizations: PdfNormalizations,
}

/// Loaded baseline plus deterministic integration policy.
#[derive(Debug)]
pub struct ContinuousPdfContext {
    provider: LhapdfProvider,
    pub metadata: ContinuousPdfMetadata,
    partitions_z: Vec<f64>,
}

impl ContinuousPdfContext {
    pub fn load_ct18nlo_v1() -> Result<Self, ContinuousPdfError> {
        Self::load("CT18NLO", 0, Some(1))
    }

    pub fn load(
        set_name: &str,
        member: i32,
        expected_data_version: Option<i32>,
    ) -> Result<Self, ContinuousPdfError> {
        let provider = LhapdfProvider::new(set_name, member)?;
        let metadata = ContinuousPdfMetadata::load(set_name, member)?;
        if let Some(expected) = expected_data_version {
            if metadata.data_version != expected {
                return Err(ContinuousPdfError::MetadataInvalid(format!(
                    "expected DataVersion {expected}, found {}",
                    metadata.data_version
                )));
            }
        }
        let mut xs = metadata
            .x_knots
            .iter()
            .copied()
            .filter(|x| *x >= metadata.support.x_minimum && *x <= 1.0)
            .collect::<Vec<_>>();
        xs.push(metadata.support.x_minimum);
        xs.push(VALENCE_PIVOT_X);
        xs.push(1.0);
        xs.sort_by(f64::total_cmp);
        xs.dedup_by(|a, b| a.to_bits() == b.to_bits());
        let partitions_z = xs.into_iter().map(f64::ln).collect();
        let context = Self {
            provider,
            metadata,
            partitions_z,
        };
        context.verify_heavy_boundary()?;
        Ok(context)
    }

    fn baseline(&self, x: f64) -> Result<NumberDensities, ContinuousPdfError> {
        if x < self.metadata.support.x_minimum || x > 1.0 {
            return Ok(NumberDensities {
                gluon: 0.0,
                up: 0.0,
                anti_up: 0.0,
                down: 0.0,
                anti_down: 0.0,
                strange: 0.0,
                anti_strange: 0.0,
                charm: 0.0,
                anti_charm: 0.0,
                bottom: 0.0,
                anti_bottom: 0.0,
            });
        }
        let xf = |id| self.provider.xfx_at_scale(id, x, self.metadata.q0_gev);
        let density = |id| -> Result<f64, ContinuousPdfError> {
            let value = xf(id)? / x;
            if !value.is_finite() {
                return Err(ContinuousPdfError::NonFiniteDensity {
                    flavor: id,
                    x,
                    value,
                });
            }
            Ok(value)
        };
        Ok(NumberDensities {
            gluon: density(GLUON)?,
            up: density(UP)?,
            anti_up: density(-UP)?,
            down: density(DOWN)?,
            anti_down: density(-DOWN)?,
            strange: density(STRANGE)?,
            anti_strange: density(-STRANGE)?,
            charm: density(CHARM)?,
            anti_charm: density(-CHARM)?,
            bottom: density(BOTTOM)?,
            anti_bottom: density(-BOTTOM)?,
        })
    }

    pub fn baseline_densities(&self, x: f64) -> Result<NumberDensities, ContinuousPdfError> {
        self.baseline(x)
    }

    fn verify_heavy_boundary(&self) -> Result<(), ContinuousPdfError> {
        for &x in self
            .metadata
            .x_knots
            .iter()
            .filter(|x| **x >= self.metadata.support.x_minimum)
        {
            for flavor in [CHARM, -CHARM, BOTTOM, -BOTTOM] {
                let xf = self
                    .provider
                    .xfx_at_scale(flavor, x, self.metadata.q0_gev)?;
                if xf.abs() > HEAVY_BOUNDARY_TOLERANCE_XF {
                    return Err(ContinuousPdfError::HeavyFlavorBoundary { flavor, x, xf });
                }
            }
        }
        Ok(())
    }

    pub fn construct(&self, theta: PdfTheta) -> Result<ContinuousPdfPoint<'_>, ContinuousPdfError> {
        self.construct_scoped(theta)
    }

    fn construct_scoped(
        &self,
        theta: PdfTheta,
    ) -> Result<ContinuousPdfPoint<'_>, ContinuousPdfError> {
        let tilt = |x: f64| (x / VALENCE_PIVOT_X).powf(theta.delta_v);
        let u_integral = self.integrate_primary(|x| {
            let b = self.baseline(x)?;
            Ok((b.up - b.anti_up) * tilt(x))
        })?;
        let d_integral = self.integrate_primary(|x| {
            let b = self.baseline(x)?;
            Ok((b.down - b.anti_down) * tilt(x))
        })?;
        let a_u = 2.0 / u_integral;
        let a_d = 1.0 / d_integral;
        validate_normalization("A_u", a_u)?;
        validate_normalization("A_d", a_d)?;
        let sea_scale = theta.lambda_sea.exp();
        validate_normalization("S", sea_scale)?;

        let quark_momentum = self.integrate_primary(|x| {
            let b = self.baseline(x)?;
            let up_valence = a_u * (b.up - b.anti_up) * tilt(x);
            let down_valence = a_d * (b.down - b.anti_down) * tilt(x);
            // u and d already contain one sea copy; adding anti-u and anti-d
            // below gives the required second copy, with no extra factor two.
            Ok(x * (up_valence
                + down_valence
                + sea_scale * (2.0 * b.anti_up + 2.0 * b.anti_down + b.strange + b.anti_strange)))
        })?;
        let baseline_gluon_momentum =
            self.integrate_primary(|x| Ok(x * self.baseline(x)?.gluon))?;
        let a_g = (1.0 - quark_momentum) / baseline_gluon_momentum;
        validate_normalization("A_g", a_g)?;
        Ok(ContinuousPdfPoint {
            context: self,
            theta,
            normalizations: PdfNormalizations {
                a_u,
                a_d,
                sea_scale,
                a_g,
            },
        })
    }

    pub fn baseline_moments(&self) -> Result<D0BaselineMoments, ContinuousPdfError> {
        let primary_sea_momentum = self.integrate_primary(|x| {
            let b = self.baseline(x)?;
            Ok(x * (2.0 * b.anti_up + 2.0 * b.anti_down + b.strange + b.anti_strange))
        })?;
        let primary_gluon_momentum = self.integrate_primary(|x| Ok(x * self.baseline(x)?.gluon))?;
        let independent_sea_momentum = self.integrate_independent_pair(|x| {
            let b = self.baseline(x)?;
            Ok(x * (2.0 * b.anti_up + 2.0 * b.anti_down + b.strange + b.anti_strange))
        })?;
        let independent_gluon_momentum =
            self.integrate_independent_pair(|x| Ok(x * self.baseline(x)?.gluon))?;
        Ok(D0BaselineMoments {
            primary_sea_momentum,
            primary_gluon_momentum,
            independent_sea_momentum,
            independent_gluon_momentum,
        })
    }

    pub fn delta_moments(&self, delta_v: f64) -> Result<D0DeltaMoments, ContinuousPdfError> {
        if !delta_v.is_finite() || !(DELTA_V_MIN * 1.05..=DELTA_V_MAX * 1.05).contains(&delta_v) {
            return Err(ContinuousPdfError::InvalidTheta {
                name: "delta_v",
                value: delta_v,
                requirement: "outside the D0 pilot plus 5% diagnostic domain",
            });
        }
        let tilt = |x: f64| (x / VALENCE_PIVOT_X).powf(delta_v);
        let uv = |x: f64| {
            let b = self.baseline(x)?;
            Ok((b.up - b.anti_up) * tilt(x))
        };
        let dv = |x: f64| {
            let b = self.baseline(x)?;
            Ok((b.down - b.anti_down) * tilt(x))
        };
        let uv_momentum = |x: f64| uv(x).map(|value| x * value);
        let dv_momentum = |x: f64| dv(x).map(|value| x * value);
        Ok(D0DeltaMoments {
            delta_v,
            primary_u_valence: self.integrate_primary(uv)?,
            primary_d_valence: self.integrate_primary(dv)?,
            primary_u_valence_momentum: self.integrate_primary(uv_momentum)?,
            primary_d_valence_momentum: self.integrate_primary(dv_momentum)?,
            independent_u_valence: self.integrate_independent_pair(uv)?,
            independent_d_valence: self.integrate_independent_pair(dv)?,
            independent_u_valence_momentum: self.integrate_independent_pair(uv_momentum)?,
            independent_d_valence_momentum: self.integrate_independent_pair(dv_momentum)?,
        })
    }

    pub fn construct_from_moments(
        &self,
        theta: PdfTheta,
        baseline: &D0BaselineMoments,
        delta: &D0DeltaMoments,
    ) -> Result<ContinuousPdfPoint<'_>, ContinuousPdfError> {
        if theta.delta_v.to_bits() != delta.delta_v.to_bits() {
            return Err(ContinuousPdfError::MetadataInvalid(
                "delta-moment cache does not match theta".into(),
            ));
        }
        let a_u = 2.0 / delta.primary_u_valence;
        let a_d = 1.0 / delta.primary_d_valence;
        let sea_scale = theta.lambda_sea.exp();
        validate_normalization("A_u", a_u)?;
        validate_normalization("A_d", a_d)?;
        validate_normalization("S", sea_scale)?;
        let quark_momentum = a_u * delta.primary_u_valence_momentum
            + a_d * delta.primary_d_valence_momentum
            + sea_scale * baseline.primary_sea_momentum;
        let a_g = (1.0 - quark_momentum) / baseline.primary_gluon_momentum;
        validate_normalization("A_g", a_g)?;
        Ok(ContinuousPdfPoint {
            context: self,
            theta,
            normalizations: PdfNormalizations {
                a_u,
                a_d,
                sea_scale,
                a_g,
            },
        })
    }

    pub fn sum_rules_from_moments(
        &self,
        point: &ContinuousPdfPoint<'_>,
        baseline: &D0BaselineMoments,
        delta: &D0DeltaMoments,
    ) -> SumRuleValidation {
        let n = point.normalizations;
        let primary_u = n.a_u * delta.primary_u_valence;
        let primary_d = n.a_d * delta.primary_d_valence;
        let primary_momentum = n.a_u * delta.primary_u_valence_momentum
            + n.a_d * delta.primary_d_valence_momentum
            + n.sea_scale * baseline.primary_sea_momentum
            + n.a_g * baseline.primary_gluon_momentum;
        let independent_u = n.a_u * delta.independent_u_valence.refined;
        let independent_d = n.a_d * delta.independent_d_valence.refined;
        let independent_momentum = n.a_u * delta.independent_u_valence_momentum.refined
            + n.a_d * delta.independent_d_valence_momentum.refined
            + n.sea_scale * baseline.independent_sea_momentum.refined
            + n.a_g * baseline.independent_gluon_momentum.refined;
        let coarse_u = n.a_u * delta.independent_u_valence.coarse;
        let coarse_d = n.a_d * delta.independent_d_valence.coarse;
        let coarse_momentum = n.a_u * delta.independent_u_valence_momentum.coarse
            + n.a_d * delta.independent_d_valence_momentum.coarse
            + n.sea_scale * baseline.independent_sea_momentum.coarse
            + n.a_g * baseline.independent_gluon_momentum.coarse;
        SumRuleValidation {
            construction_u_valence_residual: primary_u - 2.0,
            construction_d_valence_residual: primary_d - 1.0,
            construction_momentum_residual: primary_momentum - 1.0,
            independent_u_valence_residual: independent_u - 2.0,
            independent_d_valence_residual: independent_d - 1.0,
            independent_momentum_residual: independent_momentum - 1.0,
            maximum_refinement_change: (independent_u - coarse_u)
                .abs()
                .max((independent_d - coarse_d).abs())
                .max((independent_momentum - coarse_momentum).abs()),
        }
    }

    pub fn validation_x_grid(&self) -> Vec<f64> {
        let mut xs = self.metadata.x_knots.clone();
        for pair in self.metadata.x_knots.windows(2) {
            xs.push((pair[0].ln().midpoint(pair[1].ln())).exp());
        }
        let xmin = self.metadata.support.x_minimum;
        xs.extend([
            xmin,
            xmin * (1.0 + 1.0e-10),
            VALENCE_PIVOT_X,
            VALENCE_PIVOT_X * (1.0 - 1.0e-10),
            VALENCE_PIVOT_X * (1.0 + 1.0e-10),
            1.0 - 1.0e-12,
            1.0 - 1.0e-9,
            1.0,
        ]);
        xs.retain(|x| x.is_finite() && *x > 0.0 && *x <= 1.0);
        xs.sort_by(f64::total_cmp);
        xs.dedup_by(|a, b| a.to_bits() == b.to_bits());
        xs
    }

    pub fn integrate_primary<F>(&self, function: F) -> Result<f64, ContinuousPdfError>
    where
        F: Fn(f64) -> Result<f64, ContinuousPdfError>,
    {
        integrate_gk15_logx(&self.partitions_z, function, 1.0e-10, 1.0e-10, 20)
    }

    pub fn integrate_independent<F>(
        &self,
        function: F,
    ) -> Result<IndependentIntegral, ContinuousPdfError>
    where
        F: Fn(f64) -> Result<f64, ContinuousPdfError>,
    {
        let coarse = integrate_gl64_logx(&self.partitions_z, &function, 2)?;
        let refined = integrate_gl64_logx(&self.partitions_z, &function, 4)?;
        Ok(IndependentIntegral {
            value: refined,
            refinement_change: (refined - coarse).abs(),
        })
    }

    fn integrate_independent_pair<F>(
        &self,
        function: F,
    ) -> Result<QuadraturePair, ContinuousPdfError>
    where
        F: Fn(f64) -> Result<f64, ContinuousPdfError>,
    {
        Ok(QuadraturePair {
            coarse: integrate_gl64_logx(&self.partitions_z, &function, 2)?,
            refined: integrate_gl64_logx(&self.partitions_z, &function, 4)?,
        })
    }
}

impl ContinuousPdfPoint<'_> {
    pub fn densities(&self, x: f64) -> Result<NumberDensities, ContinuousPdfError> {
        if !x.is_finite() || x <= 0.0 {
            return Err(ContinuousPdfError::MetadataInvalid(format!(
                "x must be finite and positive, got {x}"
            )));
        }
        if x < self.context.metadata.support.x_minimum || x > 1.0 {
            return self.context.baseline(x);
        }
        let b = self.context.baseline(x)?;
        let tilt = (x / VALENCE_PIVOT_X).powf(self.theta.delta_v);
        let up_valence = self.normalizations.a_u * (b.up - b.anti_up) * tilt;
        let down_valence = self.normalizations.a_d * (b.down - b.anti_down) * tilt;
        let sea = self.normalizations.sea_scale;
        let result = NumberDensities {
            gluon: self.normalizations.a_g * b.gluon,
            up: up_valence + sea * b.anti_up,
            anti_up: sea * b.anti_up,
            down: down_valence + sea * b.anti_down,
            anti_down: sea * b.anti_down,
            strange: sea * b.strange,
            anti_strange: sea * b.anti_strange,
            charm: 0.0,
            anti_charm: 0.0,
            bottom: 0.0,
            anti_bottom: 0.0,
        };
        for flavor in [
            GLUON, UP, -UP, DOWN, -DOWN, STRANGE, -STRANGE, CHARM, -CHARM, BOTTOM, -BOTTOM,
        ] {
            let value = result.flavor(flavor).expect("listed flavor is present");
            if !value.is_finite() {
                return Err(ContinuousPdfError::NonFiniteDensity { flavor, x, value });
            }
        }
        Ok(result)
    }

    pub fn sum_rules(&self) -> Result<SumRuleValidation, ContinuousPdfError> {
        let primary_u = self.context.integrate_primary(|x| {
            let d = self.densities(x)?;
            Ok(d.up - d.anti_up)
        })?;
        let primary_d = self.context.integrate_primary(|x| {
            let d = self.densities(x)?;
            Ok(d.down - d.anti_down)
        })?;
        let primary_momentum = self
            .context
            .integrate_primary(|x| Ok(self.densities(x)?.momentum_integrand(x)))?;
        let independent_u = self.context.integrate_independent(|x| {
            let d = self.densities(x)?;
            Ok(d.up - d.anti_up)
        })?;
        let independent_d = self.context.integrate_independent(|x| {
            let d = self.densities(x)?;
            Ok(d.down - d.anti_down)
        })?;
        let independent_momentum = self
            .context
            .integrate_independent(|x| Ok(self.densities(x)?.momentum_integrand(x)))?;
        Ok(SumRuleValidation {
            construction_u_valence_residual: primary_u - 2.0,
            construction_d_valence_residual: primary_d - 1.0,
            construction_momentum_residual: primary_momentum - 1.0,
            independent_u_valence_residual: independent_u.value - 2.0,
            independent_d_valence_residual: independent_d.value - 1.0,
            independent_momentum_residual: independent_momentum.value - 1.0,
            maximum_refinement_change: independent_u
                .refinement_change
                .max(independent_d.refinement_change)
                .max(independent_momentum.refinement_change),
        })
    }

    pub fn canonical_identity(&self) -> Result<ParameterPointIdentity, ContinuousPdfError> {
        let metadata = &self.context.metadata;
        let mut values = BTreeMap::<String, String>::new();
        values.insert("alpha_s_mz".into(), float_hex(metadata.alpha_s_mz));
        values.insert(
            "baseline_data_version".into(),
            metadata.data_version.to_string(),
        );
        values.insert("baseline_member".into(), metadata.member.to_string());
        values.insert("baseline_set".into(), metadata.set_name.clone());
        values.insert(
            "bottom_mass_gev".into(),
            float_hex(metadata.bottom_mass_gev),
        );
        values.insert(
            "bottom_threshold_gev".into(),
            float_hex(metadata.bottom_threshold_gev),
        );
        values.insert("charm_mass_gev".into(), float_hex(metadata.charm_mass_gev));
        values.insert(
            "charm_threshold_gev".into(),
            float_hex(metadata.charm_threshold_gev),
        );
        values.insert(
            "family_version".into(),
            CONTINUOUS_PDF_FAMILY_VERSION.into(),
        );
        values.insert("flavor_scheme".into(), metadata.flavor_scheme.clone());
        values.insert(
            "integration_policy_version".into(),
            INTEGRATION_POLICY_VERSION.into(),
        );
        values.insert("lhapdf_version".into(), metadata.lhapdf_version.clone());
        values.insert(
            "normalization_a_d".into(),
            float_hex(self.normalizations.a_d),
        );
        values.insert(
            "normalization_a_g".into(),
            float_hex(self.normalizations.a_g),
        );
        values.insert(
            "normalization_a_u".into(),
            float_hex(self.normalizations.a_u),
        );
        values.insert(
            "normalization_sea_scale".into(),
            float_hex(self.normalizations.sea_scale),
        );
        values.insert("order_qcd".into(), metadata.order_qcd.to_string());
        values.insert("pilot_domain_version".into(), PILOT_DOMAIN_VERSION.into());
        values.insert("q0_gev".into(), float_hex(metadata.q0_gev));
        values.insert(
            "schema_version".into(),
            CONTINUOUS_PDF_SCHEMA_VERSION.into(),
        );
        values.insert(
            "support_q_max_gev".into(),
            float_hex(metadata.support.q_maximum_gev),
        );
        values.insert(
            "support_q_min_gev".into(),
            float_hex(metadata.support.q_minimum_gev),
        );
        values.insert(
            "support_x_max".into(),
            float_hex(metadata.support.x_maximum),
        );
        values.insert(
            "support_x_min".into(),
            float_hex(metadata.support.x_minimum),
        );
        values.insert("theta_delta_v".into(), float_hex(self.theta.delta_v));
        values.insert("theta_lambda_sea".into(), float_hex(self.theta.lambda_sea));
        values.insert("partonsbi_version".into(), env!("CARGO_PKG_VERSION").into());
        let canonical_bytes = serde_json::to_vec(&values)
            .map_err(|error| ContinuousPdfError::IdentitySerialization(error.to_string()))?;
        let digest = Sha256::digest(&canonical_bytes);
        Ok(ParameterPointIdentity {
            canonical_utf8: String::from_utf8(canonical_bytes)
                .map_err(|error| ContinuousPdfError::IdentitySerialization(error.to_string()))?,
            sha256: format!("sha256:{digest:x}"),
        })
    }
}

fn validate_normalization(name: &'static str, value: f64) -> Result<(), ContinuousPdfError> {
    if !value.is_finite() || value <= 0.0 {
        Err(ContinuousPdfError::InvalidNormalization { name, value })
    } else {
        Ok(())
    }
}

fn float_hex(value: f64) -> String {
    format!("{:016x}", canonical_zero(value).to_bits())
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ParameterPointIdentity {
    pub canonical_utf8: String,
    pub sha256: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct IndependentIntegral {
    pub value: f64,
    pub refinement_change: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct QuadraturePair {
    pub coarse: f64,
    pub refined: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct D0BaselineMoments {
    pub primary_sea_momentum: f64,
    pub primary_gluon_momentum: f64,
    pub independent_sea_momentum: QuadraturePair,
    pub independent_gluon_momentum: QuadraturePair,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct D0DeltaMoments {
    pub delta_v: f64,
    pub primary_u_valence: f64,
    pub primary_d_valence: f64,
    pub primary_u_valence_momentum: f64,
    pub primary_d_valence_momentum: f64,
    pub independent_u_valence: QuadraturePair,
    pub independent_d_valence: QuadraturePair,
    pub independent_u_valence_momentum: QuadraturePair,
    pub independent_d_valence_momentum: QuadraturePair,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct SumRuleValidation {
    pub construction_u_valence_residual: f64,
    pub construction_d_valence_residual: f64,
    pub construction_momentum_residual: f64,
    pub independent_u_valence_residual: f64,
    pub independent_d_valence_residual: f64,
    pub independent_momentum_residual: f64,
    pub maximum_refinement_change: f64,
}

impl SumRuleValidation {
    pub fn construction_passes(self) -> bool {
        self.construction_u_valence_residual.abs() <= CONSTRUCTION_TOLERANCE
            && self.construction_d_valence_residual.abs() <= CONSTRUCTION_TOLERANCE
            && self.construction_momentum_residual.abs() <= CONSTRUCTION_TOLERANCE
    }

    pub fn independent_passes(self) -> bool {
        self.independent_u_valence_residual.abs() <= INDEPENDENT_TOLERANCE
            && self.independent_d_valence_residual.abs() <= INDEPENDENT_TOLERANCE
            && self.independent_momentum_residual.abs() <= INDEPENDENT_TOLERANCE
            && self.maximum_refinement_change <= REFINEMENT_TOLERANCE
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Stage0Classification {
    Pass,
    Fail,
    Inconclusive,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PositivityMinimum {
    pub classification: Stage0Classification,
    pub density: f64,
    pub flavor: i32,
    pub x: f64,
}

pub fn validate_positivity(
    point: &ContinuousPdfPoint<'_>,
    xs: &[f64],
) -> Result<PositivityMinimum, ContinuousPdfError> {
    let mut minimum = PositivityMinimum {
        classification: Stage0Classification::Pass,
        density: f64::INFINITY,
        flavor: 0,
        x: f64::NAN,
    };
    for &x in xs {
        let densities = point.densities(x)?;
        for flavor in [
            GLUON, UP, -UP, DOWN, -DOWN, STRANGE, -STRANGE, CHARM, -CHARM, BOTTOM, -BOTTOM,
        ] {
            let density = densities.flavor(flavor).expect("listed flavor is present");
            if density < minimum.density {
                minimum.density = density;
                minimum.flavor = flavor;
                minimum.x = x;
            }
            if density < NEGATIVE_FAIL_TOLERANCE {
                minimum.classification = Stage0Classification::Fail;
            } else if density < 0.0 && minimum.classification != Stage0Classification::Fail {
                minimum.classification = Stage0Classification::Inconclusive;
            }
        }
    }
    Ok(minimum)
}

/// Exactly 441 unique points on the closed 21 by 21 pilot box.
pub fn pilot_grid_21x21() -> Vec<PdfTheta> {
    let mut points = Vec::with_capacity(441);
    for i in 0..=20 {
        let delta = DELTA_V_MIN + (DELTA_V_MAX - DELTA_V_MIN) * f64::from(i) / 20.0;
        for j in 0..=20 {
            let sea = LAMBDA_SEA_MIN + (LAMBDA_SEA_MAX - LAMBDA_SEA_MIN) * f64::from(j) / 20.0;
            points.push(PdfTheta::new(delta, sea).expect("enumerated point is in domain"));
        }
    }
    points
}

/// The 80 unique perimeter points of a 21 by 21 grid expanded by 5%.
pub fn guard_shell_5_percent() -> Vec<PdfTheta> {
    let dmin = DELTA_V_MIN * 1.05;
    let dmax = DELTA_V_MAX * 1.05;
    let smin = LAMBDA_SEA_MIN * 1.05;
    let smax = LAMBDA_SEA_MAX * 1.05;
    let mut points = Vec::with_capacity(80);
    for i in 0..=20 {
        let d = dmin + (dmax - dmin) * f64::from(i) / 20.0;
        points.push(PdfTheta::guard(d, smin).expect("guard point"));
        points.push(PdfTheta::guard(d, smax).expect("guard point"));
    }
    for j in 1..20 {
        let s = smin + (smax - smin) * f64::from(j) / 20.0;
        points.push(PdfTheta::guard(dmin, s).expect("guard point"));
        points.push(PdfTheta::guard(dmax, s).expect("guard point"));
    }
    points
}

fn integrate_gk15_logx<F>(
    partitions: &[f64],
    function: F,
    abs_tol: f64,
    rel_tol: f64,
    max_depth: usize,
) -> Result<f64, ContinuousPdfError>
where
    F: Fn(f64) -> Result<f64, ContinuousPdfError>,
{
    if partitions.len() < 2 {
        return Err(ContinuousPdfError::MetadataInvalid(
            "integration partition has fewer than two points".into(),
        ));
    }
    let per_interval_abs = abs_tol / (partitions.len() - 1) as f64;
    let transformed = |z: f64| {
        let x = z.exp();
        function(x).map(|value| value * x)
    };
    let mut total = 0.0;
    for pair in partitions.windows(2) {
        total += adaptive_gk15(
            &transformed,
            pair[0],
            pair[1],
            per_interval_abs,
            rel_tol,
            max_depth,
        )?;
    }
    if !total.is_finite() {
        return Err(ContinuousPdfError::MetadataInvalid(
            "primary integral is non-finite".into(),
        ));
    }
    Ok(total)
}

fn adaptive_gk15<F>(
    function: &F,
    a: f64,
    b: f64,
    abs_tol: f64,
    rel_tol: f64,
    depth: usize,
) -> Result<f64, ContinuousPdfError>
where
    F: Fn(f64) -> Result<f64, ContinuousPdfError>,
{
    let (value, error) = gk15(function, a, b)?;
    let tolerance = abs_tol.max(rel_tol * value.abs());
    if error <= tolerance {
        return Ok(value);
    }
    if depth == 0 {
        return Err(ContinuousPdfError::IntegrationDidNotConverge {
            interval_start: a.exp(),
            interval_end: b.exp(),
            estimated_error: error,
            limit: 0,
        });
    }
    let midpoint = a.midpoint(b);
    Ok(
        adaptive_gk15(function, a, midpoint, abs_tol / 2.0, rel_tol, depth - 1)?
            + adaptive_gk15(function, midpoint, b, abs_tol / 2.0, rel_tol, depth - 1)?,
    )
}

fn gk15<F>(function: &F, a: f64, b: f64) -> Result<(f64, f64), ContinuousPdfError>
where
    F: Fn(f64) -> Result<f64, ContinuousPdfError>,
{
    const XGK: [f64; 8] = [
        0.991_455_371_120_812_6,
        0.949_107_912_342_758_5,
        0.864_864_423_359_769_1,
        0.741_531_185_599_394_5,
        0.586_087_235_467_691_1,
        0.405_845_151_377_397_2,
        0.207_784_955_007_898_48,
        0.0,
    ];
    const WGK: [f64; 8] = [
        0.022_935_322_010_529_224,
        0.063_092_092_629_978_55,
        0.104_790_010_322_250_18,
        0.140_653_259_715_525_92,
        0.169_004_726_639_267_9,
        0.190_350_578_064_785_42,
        0.204_432_940_075_298_89,
        0.209_482_141_084_727_82,
    ];
    const WG: [f64; 4] = [
        0.129_484_966_168_869_7,
        0.279_705_391_489_276_64,
        0.381_830_050_505_118_9,
        0.417_959_183_673_469_4,
    ];
    let center = a.midpoint(b);
    let half = (b - a) / 2.0;
    let fc = function(center)?;
    let mut kronrod = WGK[7] * fc;
    let mut gauss = WG[3] * fc;
    for index in 0..7 {
        let offset = half * XGK[index];
        let pair_sum = function(center - offset)? + function(center + offset)?;
        kronrod += WGK[index] * pair_sum;
        if index == 1 {
            gauss += WG[0] * pair_sum;
        } else if index == 3 {
            gauss += WG[1] * pair_sum;
        } else if index == 5 {
            gauss += WG[2] * pair_sum;
        }
    }
    let kronrod = kronrod * half;
    let gauss = gauss * half;
    Ok((kronrod, (kronrod - gauss).abs()))
}

fn integrate_gl64_logx<F>(
    partitions: &[f64],
    function: &F,
    subdivisions: usize,
) -> Result<f64, ContinuousPdfError>
where
    F: Fn(f64) -> Result<f64, ContinuousPdfError>,
{
    let (nodes, weights) = gauss_legendre_nodes_weights(64);
    let mut total = 0.0;
    for pair in partitions.windows(2) {
        for subdivision in 0..subdivisions {
            let left = pair[0] + (pair[1] - pair[0]) * subdivision as f64 / subdivisions as f64;
            let right =
                pair[0] + (pair[1] - pair[0]) * (subdivision + 1) as f64 / subdivisions as f64;
            let midpoint = left.midpoint(right);
            let half = (right - left) / 2.0;
            for (&node, &weight) in nodes.iter().zip(&weights) {
                let z = midpoint + half * node;
                let x = z.exp();
                total += half * weight * function(x)? * x;
            }
        }
    }
    if !total.is_finite() {
        return Err(ContinuousPdfError::MetadataInvalid(
            "independent integral is non-finite".into(),
        ));
    }
    Ok(total)
}

fn gauss_legendre_nodes_weights(order: usize) -> (Vec<f64>, Vec<f64>) {
    let mut nodes = vec![0.0; order];
    let mut weights = vec![0.0; order];
    let half = order.div_ceil(2);
    for i in 0..half {
        let mut root = (std::f64::consts::PI * (i as f64 + 0.75) / (order as f64 + 0.5)).cos();
        let mut derivative = 0.0;
        for _ in 0..64 {
            let (polynomial, prior) = legendre_pair(order, root);
            derivative = order as f64 * (root * polynomial - prior) / (root * root - 1.0);
            let next = root - polynomial / derivative;
            if (next - root).abs() <= 4.0 * f64::EPSILON {
                root = next;
                break;
            }
            root = next;
        }
        let weight = 2.0 / ((1.0 - root * root) * derivative * derivative);
        nodes[i] = -root;
        nodes[order - 1 - i] = root;
        weights[i] = weight;
        weights[order - 1 - i] = weight;
    }
    (nodes, weights)
}

fn legendre_pair(order: usize, x: f64) -> (f64, f64) {
    let mut prior = 1.0;
    let mut current = x;
    if order == 0 {
        return (prior, 0.0);
    }
    if order == 1 {
        return (current, prior);
    }
    for degree in 2..=order {
        let next =
            ((2 * degree - 1) as f64 * x * current - (degree - 1) as f64 * prior) / degree as f64;
        prior = current;
        current = next;
    }
    (current, prior)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn signed_zero_is_canonicalized_and_non_finite_is_rejected() {
        let theta = PdfTheta::new(-0.0, -0.0).unwrap();
        assert_eq!(theta.delta_v.to_bits(), 0.0f64.to_bits());
        assert_eq!(theta.lambda_sea.to_bits(), 0.0f64.to_bits());
        assert!(PdfTheta::new(f64::NAN, 0.0).is_err());
        assert!(PdfTheta::new(0.0, f64::INFINITY).is_err());
    }

    #[test]
    fn hard_domain_never_clamps() {
        assert!(PdfTheta::new(DELTA_V_MAX.next_up(), 0.0).is_err());
        assert!(PdfTheta::new(0.0, LAMBDA_SEA_MIN.next_down()).is_err());
    }

    #[test]
    fn pilot_and_guard_enumerations_are_exact_and_unique() {
        let pilot = pilot_grid_21x21();
        assert_eq!(pilot.len(), 441);
        let unique = pilot
            .iter()
            .map(|p| (p.delta_v.to_bits(), p.lambda_sea.to_bits()))
            .collect::<std::collections::BTreeSet<_>>();
        assert_eq!(unique.len(), 441);
        let guard = guard_shell_5_percent();
        assert_eq!(guard.len(), 80);
        let unique = guard
            .iter()
            .map(|p| (p.delta_v.to_bits(), p.lambda_sea.to_bits()))
            .collect::<std::collections::BTreeSet<_>>();
        assert_eq!(unique.len(), 80);
        assert!(guard.iter().all(|p| {
            p.delta_v < DELTA_V_MIN
                || p.delta_v > DELTA_V_MAX
                || p.lambda_sea < LAMBDA_SEA_MIN
                || p.lambda_sea > LAMBDA_SEA_MAX
        }));
    }

    #[test]
    fn gl64_integrates_known_polynomial() {
        // The zero-width log interval is deliberately invalid for the generic
        // path; use x in [exp(-4),1] and compare the analytic x^2 integral.
        let partitions = [-4.0, 0.0];
        let value = integrate_gl64_logx(&partitions, &|x| Ok(x * x), 4).unwrap();
        let expected = (1.0 - (-12.0f64).exp()) / 3.0;
        assert!((value - expected).abs() < 1.0e-14);
    }

    #[test]
    fn gk15_and_independent_quadrature_agree() {
        let partitions = [-8.0, -2.0, 0.0];
        let adaptive =
            integrate_gk15_logx(&partitions, |x| Ok(x.sqrt()), 1e-12, 1e-12, 20).unwrap();
        let independent = integrate_gl64_logx(&partitions, &|x| Ok(x.sqrt()), 4).unwrap();
        assert!((adaptive - independent).abs() < 1.0e-11);
    }

    #[test]
    fn momentum_convention_has_no_extra_factor_two() {
        let densities = NumberDensities {
            gluon: 1.0,
            up: 2.0,
            anti_up: 3.0,
            down: 4.0,
            anti_down: 5.0,
            strange: 6.0,
            anti_strange: 7.0,
            charm: 0.0,
            anti_charm: 0.0,
            bottom: 0.0,
            anti_bottom: 0.0,
        };
        assert_eq!(densities.momentum_integrand(0.5), 14.0);
    }

    #[test]
    fn nonpositive_and_nonfinite_normalizations_are_typed_failures() {
        for value in [0.0, -1.0, f64::NAN, f64::INFINITY] {
            assert!(matches!(
                validate_normalization("A_g", value),
                Err(ContinuousPdfError::InvalidNormalization { name: "A_g", .. })
            ));
        }
    }

    #[test]
    fn adaptive_quadrature_reports_a_finite_subdivision_failure() {
        let discontinuous = |x: f64| Ok(if x < 0.3 { 0.0 } else { 1.0 });
        let error = integrate_gk15_logx(&[-4.0, 0.0], discontinuous, 1e-16, 1e-16, 0).unwrap_err();
        assert!(matches!(
            error,
            ContinuousPdfError::IntegrationDidNotConverge { .. }
        ));
    }
}
