//! Parton-distribution access backed by LHAPDF.
//!
//! The values exposed by this module follow the native LHAPDF convention:
//! every flavor field in [`PartonDensities`] is `x * f(x, Q^2)`, not
//! `f(x, Q^2)`. Keeping that convention at the interface prevents callers
//! from accidentally multiplying by `x` twice.

use std::error::Error;
use std::ffi::{CStr, CString};
use std::fmt;
use std::os::raw::{c_char, c_int};
use std::panic::{catch_unwind, AssertUnwindSafe};

use managed_lhapdf::{Pdf, PdfSet};
use serde::{Deserialize, Serialize};

const GLUON_ID: i32 = 21;
const DOWN_ID: i32 = 1;
const UP_ID: i32 = 2;
const STRANGE_ID: i32 = 3;
const CHARM_ID: i32 = 4;
const BOTTOM_ID: i32 = 5;

/// Parton densities at one `(x, Q^2)` point.
///
/// All parton fields contain `x * f(x, Q^2)`, exactly as returned by
/// LHAPDF's `xfxQ2` API. `q2` is measured in `GeV^2`.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct PartonDensities {
    pub x: f64,
    pub q2: f64,
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

/// A pluggable source of parton densities.
///
/// Implementations must return flavor values using the `x * f(x, Q^2)`
/// convention documented on [`PartonDensities`].
pub trait PdfProvider {
    fn parton_densities(&self, x: f64, q2: f64) -> Result<PartonDensities, PdfError>;
}

/// Authoritative origin of one strict-support boundary.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PdfSupportBoundSource {
    LhapdfPdfXMin,
    LhapdfPdfXMax,
    LhapdfPdfQMin,
    LhapdfPdfQMax,
}

/// Per-member LHAPDF validity domain, with `Q` expressed in GeV.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PdfSupportBounds {
    pub x_minimum: f64,
    pub x_maximum: f64,
    pub q_minimum_gev: f64,
    pub q_maximum_gev: f64,
    pub x_minimum_source: PdfSupportBoundSource,
    pub x_maximum_source: PdfSupportBoundSource,
    pub q_minimum_source: PdfSupportBoundSource,
    pub q_maximum_source: PdfSupportBoundSource,
}

impl PdfSupportBounds {
    pub fn new(
        x_minimum: f64,
        x_maximum: f64,
        q_minimum_gev: f64,
        q_maximum_gev: f64,
    ) -> Result<Self, String> {
        if !x_minimum.is_finite()
            || !x_maximum.is_finite()
            || !q_minimum_gev.is_finite()
            || !q_maximum_gev.is_finite()
            || x_minimum <= 0.0
            || x_maximum < x_minimum
            || x_maximum > 1.0
            || q_minimum_gev <= 0.0
            || q_maximum_gev < q_minimum_gev
        {
            return Err(format!(
                "invalid LHAPDF support bounds: x=[{x_minimum}, {x_maximum}], Q=[{q_minimum_gev}, {q_maximum_gev}] GeV"
            ));
        }
        Ok(Self {
            x_minimum,
            x_maximum,
            q_minimum_gev,
            q_maximum_gev,
            x_minimum_source: PdfSupportBoundSource::LhapdfPdfXMin,
            x_maximum_source: PdfSupportBoundSource::LhapdfPdfXMax,
            q_minimum_source: PdfSupportBoundSource::LhapdfPdfQMin,
            q_maximum_source: PdfSupportBoundSource::LhapdfPdfQMax,
        })
    }

    #[must_use]
    pub fn same_numeric_domain(&self, other: &Self) -> bool {
        self.x_minimum == other.x_minimum
            && self.x_maximum == other.x_maximum
            && self.q_minimum_gev == other.q_minimum_gev
            && self.q_maximum_gev == other.q_maximum_gev
    }
}

#[repr(C)]
#[derive(Default)]
struct RawPdfSupportBounds {
    x_minimum: f64,
    x_maximum: f64,
    q_minimum_gev: f64,
    q_maximum_gev: f64,
}

extern "C" {
    fn partonsbi_lhapdf_member_support(
        set_name: *const c_char,
        member: c_int,
        x_minimum: *mut f64,
        x_maximum: *mut f64,
        q_minimum_gev: *mut f64,
        q_maximum_gev: *mut f64,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> c_int;
}

fn authoritative_member_support(set_name: &str, member: i32) -> Result<PdfSupportBounds, String> {
    let set_name = CString::new(set_name)
        .map_err(|_| "PDF set name contains an embedded NUL byte".to_owned())?;
    let mut raw = RawPdfSupportBounds::default();
    let mut error_buffer = [0 as c_char; 1024];
    // SAFETY: every pointer refers to live, writable storage for the duration
    // of the call. The C++ bridge catches exceptions and reports a status code.
    let status = unsafe {
        partonsbi_lhapdf_member_support(
            set_name.as_ptr(),
            member,
            &mut raw.x_minimum,
            &mut raw.x_maximum,
            &mut raw.q_minimum_gev,
            &mut raw.q_maximum_gev,
            error_buffer.as_mut_ptr(),
            error_buffer.len(),
        )
    };
    if status != 0 {
        // SAFETY: the bridge always NUL-terminates the fixed-size error buffer.
        let message = unsafe { CStr::from_ptr(error_buffer.as_ptr()) }
            .to_string_lossy()
            .into_owned();
        return Err(message);
    }
    PdfSupportBounds::new(
        raw.x_minimum,
        raw.x_maximum,
        raw.q_minimum_gev,
        raw.q_maximum_gev,
    )
}

/// Failures reported while selecting or evaluating a PDF.
#[derive(Debug, Clone, PartialEq)]
pub enum PdfError {
    EmptySetName,
    InvalidMember {
        member: i32,
    },
    SetUnavailable {
        set_name: String,
        message: String,
    },
    MissingSetMetadata {
        set_name: String,
        key: &'static str,
    },
    InvalidSetMetadata {
        set_name: String,
        key: &'static str,
        value: String,
    },
    MemberOutOfRange {
        set_name: String,
        member: i32,
        member_count: usize,
    },
    MemberUnavailable {
        set_name: String,
        member: i32,
        message: String,
    },
    SupportMetadataUnavailable {
        set_name: String,
        member: i32,
        message: String,
    },
    InvalidInput {
        name: &'static str,
        value: f64,
        requirement: &'static str,
    },
    XOutsideGrid {
        x: f64,
        minimum: f64,
        maximum: f64,
    },
    Q2OutsideGrid {
        q2: f64,
        minimum: f64,
        maximum: f64,
    },
    UnsupportedFlavor {
        pdg_id: i32,
    },
    BackendEvaluationFailed {
        pdg_id: i32,
        x: f64,
        q2: f64,
    },
    NonFiniteDensity {
        pdg_id: i32,
        value: f64,
    },
}

impl fmt::Display for PdfError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptySetName => write!(formatter, "PDF set name must not be empty"),
            Self::InvalidMember { member } => {
                write!(formatter, "PDF member must be non-negative, got {member}")
            }
            Self::SetUnavailable { set_name, message } => {
                write!(formatter, "PDF set '{set_name}' is unavailable: {message}")
            }
            Self::MissingSetMetadata { set_name, key } => write!(
                formatter,
                "PDF set '{set_name}' does not provide required '{key}' metadata"
            ),
            Self::InvalidSetMetadata {
                set_name,
                key,
                value,
            } => write!(
                formatter,
                "PDF set '{set_name}' has invalid '{key}' metadata value '{value}'"
            ),
            Self::MemberOutOfRange {
                set_name,
                member,
                member_count,
            } => write!(
                formatter,
                "PDF member {member} is outside set '{set_name}' (available members: 0..{})",
                member_count.saturating_sub(1)
            ),
            Self::MemberUnavailable {
                set_name,
                member,
                message,
            } => write!(
                formatter,
                "PDF set '{set_name}' member {member} is unavailable: {message}"
            ),
            Self::SupportMetadataUnavailable {
                set_name,
                member,
                message,
            } => write!(
                formatter,
                "support metadata for PDF set '{set_name}' member {member} is unavailable: {message}"
            ),
            Self::InvalidInput {
                name,
                value,
                requirement,
            } => write!(
                formatter,
                "invalid {name}={value}: value must be {requirement}"
            ),
            Self::XOutsideGrid {
                x,
                minimum,
                maximum,
            } => write!(
                formatter,
                "x={x} is outside the PDF grid [{minimum}, {maximum}]"
            ),
            Self::Q2OutsideGrid {
                q2,
                minimum,
                maximum,
            } => write!(
                formatter,
                "Q^2={q2} GeV^2 is outside the PDF grid [{minimum}, {maximum}] GeV^2"
            ),
            Self::UnsupportedFlavor { pdg_id } => {
                write!(formatter, "PDF grid does not provide PDG flavor {pdg_id}")
            }
            Self::BackendEvaluationFailed { pdg_id, x, q2 } => write!(
                formatter,
                "LHAPDF failed while evaluating PDG flavor {pdg_id} at x={x}, Q^2={q2} GeV^2"
            ),
            Self::NonFiniteDensity { pdg_id, value } => write!(
                formatter,
                "LHAPDF returned non-finite x*f={value} for PDG flavor {pdg_id}"
            ),
        }
    }
}

impl Error for PdfError {}

/// An LHAPDF-backed implementation of [`PdfProvider`].
///
/// Construction is explicit and owns one LHAPDF member. There is no global
/// mutable provider state. Grid limits are cached so invalid evaluation points
/// can be rejected before calling the backend API, whose Rust wrapper panics on
/// out-of-range input.
#[derive(Debug)]
pub struct LhapdfProvider {
    pdf: Pdf,
    set_name: String,
    member: i32,
    member_count: usize,
    data_version: usize,
    order_qcd: i32,
    available_flavors: Vec<i32>,
    x_minimum: f64,
    x_maximum: f64,
    q2_minimum: f64,
    q2_maximum: f64,
    support_bounds: PdfSupportBounds,
}

impl LhapdfProvider {
    /// Load one installed LHAPDF set member.
    pub fn new(set_name: impl Into<String>, member: i32) -> Result<Self, PdfError> {
        let set_name = set_name.into();
        let set_name = set_name.trim();
        if set_name.is_empty() {
            return Err(PdfError::EmptySetName);
        }
        if member < 0 {
            return Err(PdfError::InvalidMember { member });
        }

        let set = PdfSet::new(set_name).map_err(|error| PdfError::SetUnavailable {
            set_name: set_name.to_owned(),
            message: error.to_string(),
        })?;
        let data_version = parse_usize_metadata(&set, set_name, "DataVersion")?;
        let order_qcd_value = parse_usize_metadata(&set, set_name, "OrderQCD")?;
        let order_qcd =
            i32::try_from(order_qcd_value).map_err(|_| PdfError::InvalidSetMetadata {
                set_name: set_name.to_owned(),
                key: "OrderQCD",
                value: order_qcd_value.to_string(),
            })?;
        let member_count = parse_usize_metadata(&set, set_name, "NumMembers")?;
        if member_count == 0 {
            return Err(PdfError::InvalidSetMetadata {
                set_name: set_name.to_owned(),
                key: "NumMembers",
                value: member_count.to_string(),
            });
        }
        let member_index =
            usize::try_from(member).map_err(|_| PdfError::InvalidMember { member })?;
        if member_index >= member_count {
            return Err(PdfError::MemberOutOfRange {
                set_name: set_name.to_owned(),
                member,
                member_count,
            });
        }

        let support_bounds = authoritative_member_support(set_name, member).map_err(|message| {
            PdfError::SupportMetadataUnavailable {
                set_name: set_name.to_owned(),
                member,
                message,
            }
        })?;
        let q2_minimum = support_bounds.q_minimum_gev * support_bounds.q_minimum_gev;
        let q2_maximum = support_bounds.q_maximum_gev * support_bounds.q_maximum_gev;
        if !q2_minimum.is_finite() || !q2_maximum.is_finite() {
            return Err(PdfError::InvalidSetMetadata {
                set_name: set_name.to_owned(),
                key: "QMin/QMax",
                value: format!(
                    "{}/{}",
                    support_bounds.q_minimum_gev, support_bounds.q_maximum_gev
                ),
            });
        }

        let mut pdf = Pdf::with_setname_and_member(set_name, member).map_err(|error| {
            PdfError::MemberUnavailable {
                set_name: set_name.to_owned(),
                member,
                message: error.to_string(),
            }
        })?;
        let x_minimum = pdf.x_min();
        let x_maximum = pdf.x_max();
        if x_minimum != support_bounds.x_minimum || x_maximum != support_bounds.x_maximum {
            return Err(PdfError::InvalidSetMetadata {
                set_name: set_name.to_owned(),
                key: "XMin/XMax",
                value: format!(
                    "managed-lhapdf={x_minimum}/{x_maximum}, authoritative={}/{}",
                    support_bounds.x_minimum, support_bounds.x_maximum
                ),
            });
        }
        if !x_minimum.is_finite()
            || !x_maximum.is_finite()
            || x_minimum <= 0.0
            || x_maximum < x_minimum
        {
            return Err(PdfError::InvalidSetMetadata {
                set_name: set_name.to_owned(),
                key: "XMin/XMax",
                value: format!("{x_minimum}/{x_maximum}"),
            });
        }
        let available_flavors = pdf.flavors();

        Ok(Self {
            pdf,
            set_name: set_name.to_owned(),
            member,
            member_count,
            data_version,
            order_qcd,
            available_flavors,
            x_minimum,
            x_maximum,
            q2_minimum,
            q2_maximum,
            support_bounds,
        })
    }

    #[must_use]
    pub fn set_name(&self) -> &str {
        &self.set_name
    }

    #[must_use]
    pub const fn member(&self) -> i32 {
        self.member
    }

    /// Number of members declared by the installed PDF set.
    #[must_use]
    pub const fn member_count(&self) -> usize {
        self.member_count
    }

    /// Version of the installed grid data, as declared by the PDF set.
    #[must_use]
    pub const fn data_version(&self) -> usize {
        self.data_version
    }

    /// Perturbative order declared by the installed PDF set (`0 = LO`, `1 = NLO`).
    #[must_use]
    pub const fn order_qcd(&self) -> i32 {
        self.order_qcd
    }

    #[must_use]
    pub fn available_flavors(&self) -> &[i32] {
        &self.available_flavors
    }

    #[must_use]
    pub const fn x_range(&self) -> (f64, f64) {
        (self.x_minimum, self.x_maximum)
    }

    /// Return the valid `Q^2` grid range in `GeV^2`.
    #[must_use]
    pub const fn q2_range(&self) -> (f64, f64) {
        (self.q2_minimum, self.q2_maximum)
    }

    #[must_use]
    pub fn support_bounds(&self) -> &PdfSupportBounds {
        &self.support_bounds
    }

    /// Evaluate the LHAPDF quantity `x f(flavor, x, Q)` at a scale `Q` in GeV.
    ///
    /// The managed wrapper exposes LHAPDF's `xfxQ2` call, so this helper
    /// squares the physical scale exactly once and returns `x f`, not `f`.
    /// Unlike the inclusive-density adapter, an unavailable flavor is an
    /// error: PDF reweighting must never silently replace it with zero.
    pub fn xfx_at_scale(&self, pdg_id: i32, x: f64, scale_gev: f64) -> Result<f64, PdfError> {
        if !scale_gev.is_finite() || scale_gev <= 0.0 {
            return Err(PdfError::InvalidInput {
                name: "Q",
                value: scale_gev,
                requirement: "finite and positive",
            });
        }
        let q2 = scale_gev * scale_gev;
        if !q2.is_finite() {
            return Err(PdfError::InvalidInput {
                name: "Q^2",
                value: q2,
                requirement: "finite and positive",
            });
        }
        self.validate_point(x, q2)?;
        if !self.available_flavors.contains(&pdg_id) {
            return Err(PdfError::UnsupportedFlavor { pdg_id });
        }

        let value = catch_unwind(AssertUnwindSafe(|| self.pdf.xfx_q2(pdg_id, x, q2)))
            .map_err(|_| PdfError::BackendEvaluationFailed { pdg_id, x, q2 })?;
        if !value.is_finite() {
            return Err(PdfError::NonFiniteDensity { pdg_id, value });
        }
        Ok(value)
    }

    fn validate_point(&self, x: f64, q2: f64) -> Result<(), PdfError> {
        if !x.is_finite() || x <= 0.0 || x >= 1.0 {
            return Err(PdfError::InvalidInput {
                name: "x",
                value: x,
                requirement: "finite and in (0, 1)",
            });
        }
        if !q2.is_finite() || q2 <= 0.0 {
            return Err(PdfError::InvalidInput {
                name: "Q^2",
                value: q2,
                requirement: "finite and positive",
            });
        }
        if x < self.x_minimum || x > self.x_maximum {
            return Err(PdfError::XOutsideGrid {
                x,
                minimum: self.x_minimum,
                maximum: self.x_maximum,
            });
        }
        if q2 < self.q2_minimum || q2 > self.q2_maximum {
            return Err(PdfError::Q2OutsideGrid {
                q2,
                minimum: self.q2_minimum,
                maximum: self.q2_maximum,
            });
        }
        Ok(())
    }

    fn xfx_or_zero(&self, pdg_id: i32, x: f64, q2: f64) -> Result<f64, PdfError> {
        if !self.available_flavors.contains(&pdg_id) {
            return Ok(0.0);
        }

        let value = catch_unwind(AssertUnwindSafe(|| self.pdf.xfx_q2(pdg_id, x, q2)))
            .map_err(|_| PdfError::BackendEvaluationFailed { pdg_id, x, q2 })?;
        if !value.is_finite() {
            return Err(PdfError::NonFiniteDensity { pdg_id, value });
        }
        Ok(value)
    }
}

impl PdfProvider for LhapdfProvider {
    fn parton_densities(&self, x: f64, q2: f64) -> Result<PartonDensities, PdfError> {
        self.validate_point(x, q2)?;

        Ok(PartonDensities {
            x,
            q2,
            gluon: self.xfx_or_zero(GLUON_ID, x, q2)?,
            up: self.xfx_or_zero(UP_ID, x, q2)?,
            anti_up: self.xfx_or_zero(-UP_ID, x, q2)?,
            down: self.xfx_or_zero(DOWN_ID, x, q2)?,
            anti_down: self.xfx_or_zero(-DOWN_ID, x, q2)?,
            strange: self.xfx_or_zero(STRANGE_ID, x, q2)?,
            anti_strange: self.xfx_or_zero(-STRANGE_ID, x, q2)?,
            charm: self.xfx_or_zero(CHARM_ID, x, q2)?,
            anti_charm: self.xfx_or_zero(-CHARM_ID, x, q2)?,
            bottom: self.xfx_or_zero(BOTTOM_ID, x, q2)?,
            anti_bottom: self.xfx_or_zero(-BOTTOM_ID, x, q2)?,
        })
    }
}

fn metadata_value(set: &PdfSet, set_name: &str, key: &'static str) -> Result<String, PdfError> {
    set.entry(key).ok_or_else(|| PdfError::MissingSetMetadata {
        set_name: set_name.to_owned(),
        key,
    })
}

fn parse_usize_metadata(
    set: &PdfSet,
    set_name: &str,
    key: &'static str,
) -> Result<usize, PdfError> {
    let value = metadata_value(set, set_name, key)?;
    value
        .parse::<usize>()
        .map_err(|_| PdfError::InvalidSetMetadata {
            set_name: set_name.to_owned(),
            key,
            value,
        })
}
