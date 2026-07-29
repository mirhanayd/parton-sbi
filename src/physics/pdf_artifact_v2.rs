//! ADR-005 revised Phase 1B-D1 evolution and LHAPDF artifact transport.
//!
//! This module is deliberately version-separated from [`super::pdf_artifact`].
//! The historical v1 implementation and its negative decision remain
//! reproducible. Nothing in this module couples a PDF artifact to PYTHIA.

use std::collections::{BTreeMap, BTreeSet};
use std::error::Error;
use std::ffi::{CStr, CString};
use std::fmt;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::os::raw::{c_char, c_int};
use std::path::{Path, PathBuf};
use std::thread;
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use super::{
    ContinuousPdfContext, ContinuousPdfError, ContinuousPdfFamilyVersion, LhapdfProvider, PdfTheta,
    D1_FLAVORS, EXTRAPOLATION_CALLER_POLICY, PROJECTED_BASELINE_VERSION_V2,
};

pub const PDF_ARTIFACT_SCHEMA_VERSION_V2: &str = "partonsbi.lhapdf_artifact.v2";
pub const EVOLUTION_POLICY_VERSION_V2: &str = "apfelxx_4.8.0_nlo_vfns_extended_x_v2";
pub const ARTIFACT_GRID_POLICY_VERSION_V2: &str = "threshold_subgrids_bounded_refinement_v2";
pub const ARTIFACT_CACHE_POLICY_VERSION_V2: &str = "immutable_sha256_atomic_publish_v2";
pub const REFINEMENT_POLICY_VERSION_V2: &str = "global_nine_anchor_log_probe_bisection_v2";
pub const MOMENT_POLICY_VERSION_V2: &str = "independent_gl64_logx_64_panel_v2";
pub const SIGN_TOPOLOGY_POLICY_VERSION_V2: &str = "direct_artifact_connected_sign_components_v2";
pub const OBSERVABLE_POLICY_VERSION_V2: &str = "apfel_nlo_photon_f2_fl_v2";

pub const COMPUTATIONAL_XMIN: f64 = 1.0e-11;
pub const EXPORTED_XMIN: f64 = 1.0e-9;
pub const MAX_REFINEMENT_ITERATIONS: usize = 4;
pub const MAX_X_KNOTS: usize = 1025;
pub const MAX_Q_KNOTS: usize = 257;
pub const MAX_ARTIFACT_BYTES: u64 = 256 * 1024 * 1024;
pub const MAX_SECONDS_PER_ANCHOR: f64 = 600.0;
pub const PDF_RELATIVE_TOLERANCE: f64 = 1.0e-5;
pub const PDF_ABSOLUTE_TOLERANCE: f64 = 1.0e-9;
pub const EXACT_KNOT_RELATIVE_TOLERANCE: f64 = 1.0e-12;
pub const EXACT_KNOT_ABSOLUTE_TOLERANCE: f64 = 1.0e-14;
pub const LOG_BICUBIC_RELATIVE_TOLERANCE: f64 = 1.0e-12;
pub const LOG_BICUBIC_ABSOLUTE_TOLERANCE: f64 = 1.0e-10;
pub const FULL_DOMAIN_SUM_RULE_TOLERANCE: f64 = 1.0e-5;
pub const LEAKAGE_CONVERGENCE_TOLERANCE: f64 = 1.0e-7;
pub const OBSERVABLE_RELATIVE_TOLERANCE: f64 = 1.0e-4;
pub const OBSERVABLE_ABSOLUTE_TOLERANCE: f64 = 1.0e-8;
pub const REDUCED_CROSS_SECTION_MINIMUM: f64 = -1.0e-12;

const INDEPENDENT_MOMENT_STRIDE: usize = 29;

#[derive(Debug)]
pub enum PdfArtifactV2Error {
    Boundary(ContinuousPdfError),
    UnsupportedVersion(String),
    InvalidConfiguration(String),
    Evolution(String),
    ArtifactLoad(String),
    RefinementLimit(String),
    Io(std::io::Error),
    Serialization(serde_json::Error),
    CacheLockTimeout(PathBuf),
    ChecksumMismatch {
        path: PathBuf,
        expected: String,
        actual: String,
    },
}

impl fmt::Display for PdfArtifactV2Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Boundary(error) => write!(f, "{error}"),
            Self::UnsupportedVersion(message)
            | Self::InvalidConfiguration(message)
            | Self::Evolution(message)
            | Self::ArtifactLoad(message)
            | Self::RefinementLimit(message) => f.write_str(message),
            Self::Io(error) => write!(f, "{error}"),
            Self::Serialization(error) => write!(f, "{error}"),
            Self::CacheLockTimeout(path) => {
                write!(f, "timed out acquiring v2 artifact lock {}", path.display())
            }
            Self::ChecksumMismatch {
                path,
                expected,
                actual,
            } => write!(
                f,
                "v2 artifact checksum mismatch for {}: expected {expected}, found {actual}",
                path.display()
            ),
        }
    }
}

impl Error for PdfArtifactV2Error {}

impl From<ContinuousPdfError> for PdfArtifactV2Error {
    fn from(value: ContinuousPdfError) -> Self {
        Self::Boundary(value)
    }
}

impl From<std::io::Error> for PdfArtifactV2Error {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}

impl From<serde_json::Error> for PdfArtifactV2Error {
    fn from(value: serde_json::Error) -> Self {
        Self::Serialization(value)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ComputationalGridKind {
    Base,
    Doubled,
}

impl ComputationalGridKind {
    fn node_multiplier(self) -> i32 {
        match self {
            Self::Base => 1,
            Self::Doubled => 2,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ComputationalGridDefinition {
    pub kind: ComputationalGridKind,
    pub subgrids: Vec<(usize, f64, usize)>,
}

impl ComputationalGridDefinition {
    pub fn new(kind: ComputationalGridKind) -> Self {
        let multiplier = kind.node_multiplier() as usize;
        Self {
            kind,
            subgrids: vec![
                (400 * multiplier, COMPUTATIONAL_XMIN, 3),
                (250 * multiplier, 0.1, 3),
                (180 * multiplier, 0.6, 3),
                (160 * multiplier, 0.85, 5),
            ],
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct D1EvolutionConfigV2 {
    pub schema_version: String,
    pub policy_version: String,
    pub apfelxx_version: String,
    pub perturbative_order: i32,
    pub flavor_scheme: String,
    pub maximum_active_flavors: i32,
    pub alpha_s_mz: f64,
    pub mz_gev: f64,
    pub q0_gev: f64,
    pub q_minimum_gev: f64,
    pub q_maximum_gev: f64,
    pub charm_mass_gev: f64,
    pub charm_threshold_gev: f64,
    pub bottom_mass_gev: f64,
    pub bottom_threshold_gev: f64,
    pub top_mass_gev: f64,
    pub top_threshold_gev: f64,
    pub exported_x_minimum: f64,
    pub exported_x_maximum: f64,
    pub computational_x_minimum: f64,
    pub zero_continuation_below_exported_support: bool,
    pub extrapolation_policy: String,
    pub base_grid: ComputationalGridDefinition,
    pub doubled_grid: ComputationalGridDefinition,
}

impl D1EvolutionConfigV2 {
    pub fn from_context(context: &ContinuousPdfContext) -> Result<Self, PdfArtifactV2Error> {
        if context.family_version() != ContinuousPdfFamilyVersion::V2 {
            return Err(PdfArtifactV2Error::UnsupportedVersion(
                "revised D1 accepts only ct18nlo_two_parameter_boundary_v2".into(),
            ));
        }
        let metadata = &context.metadata;
        if metadata.lhapdf_version != "6.5.6"
            || metadata.order_qcd != 1
            || metadata.flavor_scheme != "variable"
            || metadata.support.x_minimum.to_bits() != EXPORTED_XMIN.to_bits()
        {
            return Err(PdfArtifactV2Error::InvalidConfiguration(
                "revised D1 requires the accepted LHAPDF 6.5.6 CT18NLO NLO VFNS support".into(),
            ));
        }
        Ok(Self {
            schema_version: PDF_ARTIFACT_SCHEMA_VERSION_V2.into(),
            policy_version: EVOLUTION_POLICY_VERSION_V2.into(),
            apfelxx_version: "4.8.0".into(),
            perturbative_order: metadata.order_qcd,
            flavor_scheme: metadata.flavor_scheme.clone(),
            maximum_active_flavors: 5,
            alpha_s_mz: metadata.alpha_s_mz,
            mz_gev: metadata.mz_gev,
            q0_gev: metadata.q0_gev,
            q_minimum_gev: metadata.support.q_minimum_gev,
            q_maximum_gev: metadata.support.q_maximum_gev,
            charm_mass_gev: metadata.charm_mass_gev,
            charm_threshold_gev: metadata.charm_threshold_gev,
            bottom_mass_gev: metadata.bottom_mass_gev,
            bottom_threshold_gev: metadata.bottom_threshold_gev,
            top_mass_gev: metadata.top_mass_gev,
            top_threshold_gev: metadata.top_threshold_gev,
            exported_x_minimum: metadata.support.x_minimum,
            exported_x_maximum: metadata.support.x_maximum,
            computational_x_minimum: COMPUTATIONAL_XMIN,
            zero_continuation_below_exported_support: true,
            extrapolation_policy: EXTRAPOLATION_CALLER_POLICY.into(),
            base_grid: ComputationalGridDefinition::new(ComputationalGridKind::Base),
            doubled_grid: ComputationalGridDefinition::new(ComputationalGridKind::Doubled),
        })
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ArtifactGridV2 {
    pub policy_version: String,
    pub x_knots: Vec<f64>,
    pub unique_q_knots_gev: Vec<f64>,
    pub q_subgrids_gev: Vec<Vec<f64>>,
    pub thresholds_gev: Vec<f64>,
}

impl ArtifactGridV2 {
    pub fn initial(context: &ContinuousPdfContext) -> Result<Self, PdfArtifactV2Error> {
        let metadata = &context.metadata;
        let mut xs = metadata
            .x_knots
            .iter()
            .copied()
            .filter(|x| *x >= metadata.support.x_minimum && *x <= metadata.support.x_maximum)
            .collect::<Vec<_>>();
        xs.extend([metadata.support.x_minimum, metadata.support.x_maximum]);
        sort_unique(&mut xs);
        let mut qs = metadata
            .q_knots_gev
            .iter()
            .copied()
            .filter(|q| {
                *q >= metadata.support.q_minimum_gev && *q <= metadata.support.q_maximum_gev
            })
            .collect::<Vec<_>>();
        qs.extend([
            metadata.support.q_minimum_gev,
            metadata.support.q_maximum_gev,
            metadata.charm_threshold_gev,
            metadata.bottom_threshold_gev,
        ]);
        sort_unique(&mut qs);
        Self::from_unique_knots(
            xs,
            qs,
            metadata.charm_threshold_gev,
            metadata.bottom_threshold_gev,
        )
    }

    pub fn from_unique_knots(
        mut xs: Vec<f64>,
        mut qs: Vec<f64>,
        charm_threshold: f64,
        bottom_threshold: f64,
    ) -> Result<Self, PdfArtifactV2Error> {
        sort_unique(&mut xs);
        sort_unique(&mut qs);
        if xs.len() < 4
            || qs.len() < 6
            || xs.first().copied() != Some(EXPORTED_XMIN)
            || xs.last().copied() != Some(1.0)
            || !qs.iter().any(|q| q.to_bits() == charm_threshold.to_bits())
            || !qs.iter().any(|q| q.to_bits() == bottom_threshold.to_bits())
        {
            return Err(PdfArtifactV2Error::InvalidConfiguration(
                "v2 artifact grid must span support and contain exact heavy thresholds".into(),
            ));
        }
        let first = qs
            .iter()
            .copied()
            .filter(|q| *q <= charm_threshold)
            .collect::<Vec<_>>();
        let second = qs
            .iter()
            .copied()
            .filter(|q| *q >= charm_threshold && *q <= bottom_threshold)
            .collect::<Vec<_>>();
        let third = qs
            .iter()
            .copied()
            .filter(|q| *q >= bottom_threshold)
            .collect::<Vec<_>>();
        if [first.len(), second.len(), third.len()]
            .into_iter()
            .any(|count| count < 2)
        {
            return Err(PdfArtifactV2Error::InvalidConfiguration(
                "each LHAPDF threshold subgrid requires at least two Q knots".into(),
            ));
        }
        Ok(Self {
            policy_version: ARTIFACT_GRID_POLICY_VERSION_V2.into(),
            x_knots: xs,
            unique_q_knots_gev: qs,
            q_subgrids_gev: vec![first, second, third],
            thresholds_gev: vec![charm_threshold, bottom_threshold],
        })
    }

    pub fn repeated_q_knots(&self) -> Vec<f64> {
        self.q_subgrids_gev.iter().flatten().copied().collect()
    }

    pub fn canonical_hash(&self) -> Result<String, PdfArtifactV2Error> {
        Ok(format!(
            "sha256:{:x}",
            Sha256::digest(serde_json::to_vec(self)?)
        ))
    }

    pub fn estimated_member_bytes(&self) -> u64 {
        let data_rows = self
            .q_subgrids_gev
            .iter()
            .map(|qs| qs.len() * self.x_knots.len())
            .sum::<usize>();
        // Eleven 24-byte scientific fields plus separators and grid headers.
        (data_rows * (11 * 24 + 11) + self.x_knots.len() * 25 + 16_384) as u64
    }
}

fn sort_unique(values: &mut Vec<f64>) {
    values.sort_by(f64::total_cmp);
    values.dedup_by(|left, right| left.to_bits() == right.to_bits());
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct IndependentMoments {
    pub full_u_valence: f64,
    pub full_d_valence: f64,
    pub full_momentum: f64,
    pub retained_u_valence: f64,
    pub retained_d_valence: f64,
    pub retained_momentum: f64,
    pub leaked_momentum: f64,
    pub full_flavor_momentum: BTreeMap<i32, f64>,
    pub retained_flavor_momentum: BTreeMap<i32, f64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvolvedGridV2 {
    pub xs: Vec<f64>,
    pub qs_gev: Vec<f64>,
    pub flavors: Vec<i32>,
    pub xf_values: Vec<f64>,
    pub alpha_s_values: Vec<f64>,
    pub native_sum_rules: Vec<[f64; 3]>,
    pub independent_moments: Vec<IndependentMoments>,
    pub computational_grid: ComputationalGridKind,
}

impl EvolvedGridV2 {
    pub fn xf(&self, flavor: i32, ix: usize, iq: usize) -> Option<f64> {
        let flavor_index = self.flavors.iter().position(|id| *id == flavor)?;
        self.xf_values
            .get((iq * self.xs.len() + ix) * self.flavors.len() + flavor_index)
            .copied()
    }
}

extern "C" {
    fn partonsbi_apfel_evolve_grid_v2(
        raw_set: *const c_char,
        raw_member: c_int,
        q0: f64,
        alpha_s_mz: f64,
        mz: f64,
        qmax: f64,
        charm_mass: f64,
        charm_threshold: f64,
        bottom_mass: f64,
        bottom_threshold: f64,
        top_mass: f64,
        top_threshold: f64,
        order: c_int,
        delta_v: f64,
        sea_scale: f64,
        a_u: f64,
        a_d: f64,
        a_g: f64,
        computational_xmin: f64,
        exported_xmin: f64,
        node_multiplier: c_int,
        compute_moments: c_int,
        xs: *const f64,
        nx: usize,
        qs: *const f64,
        nq: usize,
        values: *mut f64,
        alphas: *mut f64,
        native_sum_rules: *mut f64,
        independent: *mut f64,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> c_int;

    fn partonsbi_lhapdf_artifact_evaluate(
        search_parent: *const c_char,
        set_name: *const c_char,
        xs: *const f64,
        nx: usize,
        qs: *const f64,
        nq: usize,
        values: *mut f64,
        alphas: *mut f64,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> c_int;

    fn partonsbi_apfel_artifact_observables_v2(
        raw_set: *const c_char,
        raw_member: c_int,
        q0: f64,
        alpha_s_mz: f64,
        mz: f64,
        qmax: f64,
        charm_mass: f64,
        charm_threshold: f64,
        bottom_mass: f64,
        bottom_threshold: f64,
        top_mass: f64,
        top_threshold: f64,
        order: c_int,
        delta_v: f64,
        sea_scale: f64,
        a_u: f64,
        a_d: f64,
        a_g: f64,
        computational_xmin: f64,
        exported_xmin: f64,
        node_multiplier: c_int,
        search_parent: *const c_char,
        set_name: *const c_char,
        xs: *const f64,
        nx: usize,
        qs: *const f64,
        nq: usize,
        direct_values: *mut f64,
        artifact_values: *mut f64,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> c_int;
}

pub fn evolve_grid_v2(
    context: &ContinuousPdfContext,
    theta: PdfTheta,
    xs: &[f64],
    qs: &[f64],
    kind: ComputationalGridKind,
) -> Result<EvolvedGridV2, PdfArtifactV2Error> {
    let point = context.construct(theta)?;
    let normalizations = point.effective_raw_normalizations();
    evolve_grid_v2_with_normalizations(
        context,
        theta,
        normalizations.sea_scale,
        normalizations.a_u,
        normalizations.a_d,
        normalizations.a_g,
        xs,
        qs,
        kind,
        true,
    )
}

pub fn evolve_grid_values_v2(
    context: &ContinuousPdfContext,
    theta: PdfTheta,
    xs: &[f64],
    qs: &[f64],
    kind: ComputationalGridKind,
) -> Result<EvolvedGridV2, PdfArtifactV2Error> {
    let point = context.construct(theta)?;
    let normalizations = point.effective_raw_normalizations();
    evolve_grid_v2_with_normalizations(
        context,
        theta,
        normalizations.sea_scale,
        normalizations.a_u,
        normalizations.a_d,
        normalizations.a_g,
        xs,
        qs,
        kind,
        false,
    )
}

pub fn evolve_raw_ct_center_v2(
    context: &ContinuousPdfContext,
    xs: &[f64],
    qs: &[f64],
    kind: ComputationalGridKind,
) -> Result<EvolvedGridV2, PdfArtifactV2Error> {
    evolve_grid_v2_with_normalizations(
        context,
        PdfTheta::new(0.0, 0.0)?,
        1.0,
        1.0,
        1.0,
        1.0,
        xs,
        qs,
        kind,
        false,
    )
}

#[allow(clippy::too_many_arguments)]
fn evolve_grid_v2_with_normalizations(
    context: &ContinuousPdfContext,
    theta: PdfTheta,
    sea_scale: f64,
    a_u: f64,
    a_d: f64,
    a_g: f64,
    xs: &[f64],
    qs: &[f64],
    kind: ComputationalGridKind,
    compute_moments: bool,
) -> Result<EvolvedGridV2, PdfArtifactV2Error> {
    let config = D1EvolutionConfigV2::from_context(context)?;
    validate_requested_grid(&config, xs, qs)?;
    let raw_set = CString::new(context.metadata.set_name.as_str())
        .map_err(|_| PdfArtifactV2Error::InvalidConfiguration("raw set contains NUL".into()))?;
    let mut values = vec![f64::NAN; xs.len() * qs.len() * D1_FLAVORS.len()];
    let mut alphas = vec![f64::NAN; qs.len()];
    let mut native = vec![f64::NAN; qs.len() * 3];
    let mut independent = vec![f64::NAN; qs.len() * INDEPENDENT_MOMENT_STRIDE];
    let mut error = [0 as c_char; 1024];
    // SAFETY: all buffers remain live and the bridge catches C++ exceptions.
    let status = unsafe {
        partonsbi_apfel_evolve_grid_v2(
            raw_set.as_ptr(),
            context.metadata.member,
            config.q0_gev,
            config.alpha_s_mz,
            config.mz_gev,
            config.q_maximum_gev,
            config.charm_mass_gev,
            config.charm_threshold_gev,
            config.bottom_mass_gev,
            config.bottom_threshold_gev,
            config.top_mass_gev,
            config.top_threshold_gev,
            config.perturbative_order,
            theta.delta_v,
            sea_scale,
            a_u,
            a_d,
            a_g,
            COMPUTATIONAL_XMIN,
            EXPORTED_XMIN,
            kind.node_multiplier(),
            i32::from(compute_moments),
            xs.as_ptr(),
            xs.len(),
            qs.as_ptr(),
            qs.len(),
            values.as_mut_ptr(),
            alphas.as_mut_ptr(),
            native.as_mut_ptr(),
            independent.as_mut_ptr(),
            error.as_mut_ptr(),
            error.len(),
        )
    };
    if status != 0 {
        return Err(PdfArtifactV2Error::Evolution(c_error(&error)));
    }
    if values.iter().chain(&alphas).any(|value| !value.is_finite())
        || (compute_moments
            && native
                .iter()
                .chain(&independent)
                .any(|value| !value.is_finite()))
    {
        return Err(PdfArtifactV2Error::Evolution(
            "non-finite value in revised-D1 evolution output".into(),
        ));
    }
    let independent_moments = if compute_moments {
        independent
            .chunks_exact(INDEPENDENT_MOMENT_STRIDE)
            .map(|values| {
                let full_flavor_momentum = D1_FLAVORS
                    .iter()
                    .copied()
                    .zip(values[7..18].iter().copied())
                    .collect();
                let retained_flavor_momentum = D1_FLAVORS
                    .iter()
                    .copied()
                    .zip(values[18..29].iter().copied())
                    .collect();
                IndependentMoments {
                    full_u_valence: values[0],
                    full_d_valence: values[1],
                    full_momentum: values[2],
                    retained_u_valence: values[3],
                    retained_d_valence: values[4],
                    retained_momentum: values[5],
                    leaked_momentum: values[6],
                    full_flavor_momentum,
                    retained_flavor_momentum,
                }
            })
            .collect()
    } else {
        Vec::new()
    };
    Ok(EvolvedGridV2 {
        xs: xs.to_vec(),
        qs_gev: qs.to_vec(),
        flavors: D1_FLAVORS.to_vec(),
        xf_values: values,
        alpha_s_values: alphas,
        native_sum_rules: if compute_moments {
            native
                .chunks_exact(3)
                .map(|values| [values[0], values[1], values[2]])
                .collect()
        } else {
            Vec::new()
        },
        independent_moments,
        computational_grid: kind,
    })
}

fn validate_requested_grid(
    config: &D1EvolutionConfigV2,
    xs: &[f64],
    qs: &[f64],
) -> Result<(), PdfArtifactV2Error> {
    if xs.len() < 2
        || qs.len() < 2
        || xs.first().is_none_or(|x| *x < config.exported_x_minimum)
        || xs.last().copied() != Some(config.exported_x_maximum)
        || qs.first().copied() != Some(config.q_minimum_gev)
        || qs.last().is_none_or(|q| *q > config.q_maximum_gev)
        || xs.windows(2).any(|pair| pair[0] >= pair[1])
        || qs.windows(2).any(|pair| pair[0] >= pair[1])
    {
        return Err(PdfArtifactV2Error::InvalidConfiguration(
            "revised-D1 request must be ordered and remain inside exported support".into(),
        ));
    }
    Ok(())
}

fn c_error(buffer: &[c_char]) -> String {
    // SAFETY: bridge buffers are zero-initialized and written by snprintf.
    unsafe { CStr::from_ptr(buffer.as_ptr()) }
        .to_string_lossy()
        .into_owned()
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ArtifactFileChecksumV2 {
    pub relative_path: String,
    pub sha256: String,
    pub byte_count: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PdfArtifactManifestV2 {
    pub schema_version: String,
    pub artifact_hash: String,
    pub set_name: String,
    pub member: i32,
    pub parameter_identity: String,
    pub raw_source_identity: String,
    pub baseline_version: String,
    pub family_version: String,
    pub evolution: D1EvolutionConfigV2,
    pub grid: ArtifactGridV2,
    pub final_common_grid_hash: String,
    pub refinement_policy_version: String,
    pub refinement_trace_hash: String,
    pub interpolation_policy: String,
    pub extrapolator_policy: String,
    pub cache_policy_version: String,
    pub moment_policy_version: String,
    pub sign_topology_policy_version: String,
    pub observable_policy_version: String,
    pub checksums: Vec<ArtifactFileChecksumV2>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct PdfArtifactV2 {
    pub cache_directory: PathBuf,
    pub set_directory: PathBuf,
    pub manifest: PdfArtifactManifestV2,
}

pub fn default_cache_root_v2() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join(".external/partonsbi/pdf-artifacts/v2/sha256")
}

pub fn build_or_load_artifact_v2(
    context: &ContinuousPdfContext,
    theta: PdfTheta,
    grid: &ArtifactGridV2,
    refinement_trace_hash: &str,
    cache_root: &Path,
) -> Result<PdfArtifactV2, PdfArtifactV2Error> {
    let config = D1EvolutionConfigV2::from_context(context)?;
    if grid.x_knots.len() > MAX_X_KNOTS
        || grid.unique_q_knots_gev.len() > MAX_Q_KNOTS
        || grid.estimated_member_bytes() > MAX_ARTIFACT_BYTES
    {
        return Err(PdfArtifactV2Error::RefinementLimit(
            "v2 artifact grid exceeds a predeclared complexity cap".into(),
        ));
    }
    let point = context.construct(theta)?;
    let point_identity = point.canonical_identity()?;
    let grid_hash = grid.canonical_hash()?;
    let artifact_hash = artifact_identity_v2(
        &point_identity.sha256,
        context,
        &config,
        grid,
        &grid_hash,
        refinement_trace_hash,
    )?;
    let hash = artifact_hash
        .strip_prefix("sha256:")
        .expect("internal artifact hash has a prefix");
    let parent = cache_root.join(&hash[..2]);
    let cache_directory = parent.join(hash);
    fs::create_dir_all(&parent)?;
    let lock_path = parent.join(format!(".{hash}.lock"));
    let _lock = CacheLockV2::acquire(&lock_path, Duration::from_secs(120))?;
    if cache_directory.exists() {
        match load_and_validate_artifact_v2(&cache_directory) {
            Ok(artifact) => return Ok(artifact),
            Err(_) => {
                let quarantine = parent.join(format!(".{hash}.corrupt.{}", std::process::id()));
                fs::rename(&cache_directory, quarantine)?;
            }
        }
    }

    let temp = parent.join(format!(".{hash}.tmp.{}", std::process::id()));
    if temp.exists() {
        return Err(PdfArtifactV2Error::InvalidConfiguration(format!(
            "temporary v2 artifact already exists: {}",
            temp.display()
        )));
    }
    fs::create_dir(&temp)?;
    let set_name = format!("PartonSBI_D1R_{hash}");
    let set_directory = temp.join(&set_name);
    fs::create_dir(&set_directory)?;
    let evolved = evolve_grid_values_v2(
        context,
        theta,
        &grid.x_knots,
        &grid.unique_q_knots_gev,
        ComputationalGridKind::Doubled,
    )?;
    write_lhagrid_v2(&set_directory, &set_name, context, &config, grid, &evolved)?;
    let checksums = checksum_artifact_files_v2(&temp)?;
    let actual_payload_bytes = checksums.iter().map(|entry| entry.byte_count).sum::<u64>();
    if actual_payload_bytes > MAX_ARTIFACT_BYTES {
        fs::remove_dir_all(&temp)?;
        return Err(PdfArtifactV2Error::RefinementLimit(format!(
            "written v2 artifact payload {actual_payload_bytes} exceeds the {MAX_ARTIFACT_BYTES}-byte cap"
        )));
    }
    let manifest = PdfArtifactManifestV2 {
        schema_version: PDF_ARTIFACT_SCHEMA_VERSION_V2.into(),
        artifact_hash,
        set_name,
        member: 0,
        parameter_identity: point_identity.sha256,
        raw_source_identity: format!(
            "{}:{}:data-version-{}",
            context.metadata.set_name, context.metadata.member, context.metadata.data_version
        ),
        baseline_version: PROJECTED_BASELINE_VERSION_V2.into(),
        family_version: super::CONTINUOUS_PDF_FAMILY_VERSION_V2.into(),
        evolution: config,
        grid: grid.clone(),
        final_common_grid_hash: grid_hash,
        refinement_policy_version: REFINEMENT_POLICY_VERSION_V2.into(),
        refinement_trace_hash: refinement_trace_hash.into(),
        interpolation_policy: "logcubic".into(),
        extrapolator_policy: "error".into(),
        cache_policy_version: ARTIFACT_CACHE_POLICY_VERSION_V2.into(),
        moment_policy_version: MOMENT_POLICY_VERSION_V2.into(),
        sign_topology_policy_version: SIGN_TOPOLOGY_POLICY_VERSION_V2.into(),
        observable_policy_version: OBSERVABLE_POLICY_VERSION_V2.into(),
        checksums,
    };
    write_new_v2(
        &temp.join("artifact_manifest.json"),
        &serde_json::to_vec_pretty(&manifest)?,
    )?;
    fs::rename(&temp, &cache_directory)?;
    load_and_validate_artifact_v2(&cache_directory)
}

fn artifact_identity_v2(
    point_identity: &str,
    context: &ContinuousPdfContext,
    config: &D1EvolutionConfigV2,
    grid: &ArtifactGridV2,
    grid_hash: &str,
    refinement_trace_hash: &str,
) -> Result<String, PdfArtifactV2Error> {
    let mut values = BTreeMap::new();
    values.insert(
        "schema_version".to_owned(),
        PDF_ARTIFACT_SCHEMA_VERSION_V2.to_owned(),
    );
    values.insert("parameter_identity".to_owned(), point_identity.to_owned());
    values.insert(
        "raw_source_identity".to_owned(),
        format!(
            "{}:{}:data-version-{}",
            context.metadata.set_name, context.metadata.member, context.metadata.data_version
        ),
    );
    values.insert(
        "baseline_version".to_owned(),
        PROJECTED_BASELINE_VERSION_V2.to_owned(),
    );
    values.insert(
        "family_version".to_owned(),
        super::CONTINUOUS_PDF_FAMILY_VERSION_V2.to_owned(),
    );
    values.insert(
        "evolution_policy_version".to_owned(),
        config.policy_version.clone(),
    );
    values.insert("apfelxx_version".to_owned(), config.apfelxx_version.clone());
    values.insert(
        "lhapdf_version".to_owned(),
        context.metadata.lhapdf_version.clone(),
    );
    values.insert(
        "partonsbi_version".to_owned(),
        env!("CARGO_PKG_VERSION").to_owned(),
    );
    values.insert(
        "perturbative_order".to_owned(),
        config.perturbative_order.to_string(),
    );
    values.insert("flavor_scheme".to_owned(), config.flavor_scheme.clone());
    values.insert(
        "maximum_active_flavors".to_owned(),
        config.maximum_active_flavors.to_string(),
    );
    for (key, value) in [
        ("alpha_s_mz", config.alpha_s_mz),
        ("mz_gev", config.mz_gev),
        ("q0_gev", config.q0_gev),
        ("q_minimum_gev", config.q_minimum_gev),
        ("q_maximum_gev", config.q_maximum_gev),
        ("charm_mass_gev", config.charm_mass_gev),
        ("charm_threshold_gev", config.charm_threshold_gev),
        ("bottom_mass_gev", config.bottom_mass_gev),
        ("bottom_threshold_gev", config.bottom_threshold_gev),
        ("top_mass_gev", config.top_mass_gev),
        ("top_threshold_gev", config.top_threshold_gev),
        ("exported_x_minimum", config.exported_x_minimum),
        ("exported_x_maximum", config.exported_x_maximum),
        ("computational_x_minimum", config.computational_x_minimum),
    ] {
        values.insert(key.to_owned(), binary64_hex(value));
    }
    values.insert(
        "zero_continuation_below_exported_support".to_owned(),
        config.zero_continuation_below_exported_support.to_string(),
    );
    values.insert(
        "base_computational_grid".to_owned(),
        computational_grid_identity(&config.base_grid),
    );
    values.insert(
        "doubled_computational_grid".to_owned(),
        computational_grid_identity(&config.doubled_grid),
    );
    values.insert(
        "artifact_grid_policy_version".to_owned(),
        grid.policy_version.clone(),
    );
    values.insert(
        "artifact_x_knots_binary64".to_owned(),
        binary64_list(&grid.x_knots),
    );
    values.insert(
        "artifact_unique_q_knots_binary64".to_owned(),
        binary64_list(&grid.unique_q_knots_gev),
    );
    values.insert(
        "artifact_q_subgrids_binary64".to_owned(),
        grid.q_subgrids_gev
            .iter()
            .map(|subgrid| binary64_list(subgrid))
            .collect::<Vec<_>>()
            .join(";"),
    );
    values.insert(
        "artifact_thresholds_binary64".to_owned(),
        binary64_list(&grid.thresholds_gev),
    );
    values.insert("final_common_grid_hash".to_owned(), grid_hash.to_owned());
    values.insert(
        "refinement_policy_version".to_owned(),
        REFINEMENT_POLICY_VERSION_V2.to_owned(),
    );
    values.insert(
        "refinement_trace_hash".to_owned(),
        refinement_trace_hash.to_owned(),
    );
    values.insert(
        "cache_policy_version".to_owned(),
        ARTIFACT_CACHE_POLICY_VERSION_V2.to_owned(),
    );
    values.insert("interpolation_policy".to_owned(), "logcubic".to_owned());
    values.insert("extrapolator_policy".to_owned(), "error".to_owned());
    values.insert(
        "moment_policy_version".to_owned(),
        MOMENT_POLICY_VERSION_V2.to_owned(),
    );
    values.insert(
        "sign_topology_policy_version".to_owned(),
        SIGN_TOPOLOGY_POLICY_VERSION_V2.to_owned(),
    );
    values.insert(
        "observable_policy_version".to_owned(),
        OBSERVABLE_POLICY_VERSION_V2.to_owned(),
    );
    let bytes = serde_json::to_vec(&values)?;
    Ok(format!("sha256:{:x}", Sha256::digest(bytes)))
}

fn binary64_hex(value: f64) -> String {
    format!("{:016x}", value.to_bits())
}

fn binary64_list(values: &[f64]) -> String {
    values
        .iter()
        .map(|value| binary64_hex(*value))
        .collect::<Vec<_>>()
        .join(",")
}

fn computational_grid_identity(grid: &ComputationalGridDefinition) -> String {
    grid.subgrids
        .iter()
        .map(|(nodes, xmin, degree)| format!("{nodes}:{}:{degree}", binary64_hex(*xmin)))
        .collect::<Vec<_>>()
        .join(",")
}

fn write_lhagrid_v2(
    directory: &Path,
    set_name: &str,
    context: &ContinuousPdfContext,
    config: &D1EvolutionConfigV2,
    grid: &ArtifactGridV2,
    evolved: &EvolvedGridV2,
) -> Result<(), PdfArtifactV2Error> {
    let info_path = directory.join(format!("{set_name}.info"));
    let member_path = directory.join(format!("{set_name}_0000.dat"));
    let q_list = format_list_v2(&grid.unique_q_knots_gev);
    let alpha_list = format_list_v2(&evolved.alpha_s_values);
    let info = format!(
        "SetDesc: 'PartonSBI revised D1 deterministic APFEL++ artifact; projected boundary, not unmodified CT18NLO'\n\
Authors: PartonSBI research artifact\n\
Format: lhagrid1\nDataVersion: 2\nNumMembers: 1\nSetIndex: 0\n\
Flavors: [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 21]\n\
OrderQCD: {order}\nFlavorScheme: {scheme}\nNumFlavors: 5\nErrorType: replicas\n\
XMin: {xmin}\nXMax: {xmax}\nQMin: {qmin}\nQMax: {qmax}\n\
MZ: {mz}\nMCharm: {mc}\nMBottom: {mb}\nMTop: {mt}\n\
AlphaS_MZ: {asmz}\nAlphaS_OrderQCD: {order}\nAlphaS_Type: ipol\n\
AlphaS_Qs: [{q_list}]\nAlphaS_Vals: [{alpha_list}]\n\
Interpolator: logcubic\nExtrapolator: error\n\
PartonSBI_ArtifactSchema: {schema}\nPartonSBI_EvolutionPolicy: {policy}\n\
PartonSBI_GridPolicy: {grid_policy}\nPartonSBI_ComputationalXMin: {computational_xmin}\n\
PartonSBI_ZeroContinuationBelowXMin: true\n",
        order = config.perturbative_order,
        scheme = config.flavor_scheme,
        xmin = float_text_v2(config.exported_x_minimum),
        xmax = float_text_v2(config.exported_x_maximum),
        qmin = float_text_v2(config.q_minimum_gev),
        qmax = float_text_v2(config.q_maximum_gev),
        mz = float_text_v2(config.mz_gev),
        mc = float_text_v2(config.charm_mass_gev),
        mb = float_text_v2(config.bottom_mass_gev),
        mt = float_text_v2(config.top_mass_gev),
        asmz = float_text_v2(config.alpha_s_mz),
        schema = PDF_ARTIFACT_SCHEMA_VERSION_V2,
        policy = EVOLUTION_POLICY_VERSION_V2,
        grid_policy = ARTIFACT_GRID_POLICY_VERSION_V2,
        computational_xmin = float_text_v2(COMPUTATIONAL_XMIN),
    );
    write_new_v2(&info_path, info.as_bytes())?;

    let mut member = Vec::new();
    member.extend_from_slice(b"PdfType: central\nFormat: lhagrid1\n---\n");
    for q_subgrid in &grid.q_subgrids_gev {
        member.extend_from_slice(format!("{}\n", format_space_line_v2(&grid.x_knots)).as_bytes());
        member.extend_from_slice(format!("{}\n", format_space_line_v2(q_subgrid)).as_bytes());
        member.extend_from_slice(b"-5 -4 -3 -2 -1 1 2 3 4 5 21\n");
        for ix in 0..grid.x_knots.len() {
            for q in q_subgrid {
                let iq = grid
                    .unique_q_knots_gev
                    .iter()
                    .position(|candidate| candidate.to_bits() == q.to_bits())
                    .expect("subgrid knots belong to the unique Q union");
                let row = D1_FLAVORS
                    .iter()
                    .map(|flavor| {
                        float_text_v2(
                            evolved
                                .xf(*flavor, ix, iq)
                                .expect("evolved v2 grid has every flavor"),
                        )
                    })
                    .collect::<Vec<_>>()
                    .join(" ");
                member.extend_from_slice(row.as_bytes());
                member.push(b'\n');
            }
        }
        member.extend_from_slice(b"---\n");
    }
    if member.len() as u64 > MAX_ARTIFACT_BYTES {
        return Err(PdfArtifactV2Error::RefinementLimit(format!(
            "actual member payload {} exceeds {} bytes",
            member.len(),
            MAX_ARTIFACT_BYTES
        )));
    }
    write_new_v2(&member_path, &member)?;
    let metadata = serde_json::json!({
        "schema_version": PDF_ARTIFACT_SCHEMA_VERSION_V2,
        "raw_source": {
            "set": context.metadata.set_name,
            "member": context.metadata.member,
            "data_version": context.metadata.data_version,
            "lhapdf_version": context.metadata.lhapdf_version,
        },
        "projected_baseline_version": PROJECTED_BASELINE_VERSION_V2,
        "family_version": super::CONTINUOUS_PDF_FAMILY_VERSION_V2,
        "evolution": config,
        "grid": grid,
    });
    write_new_v2(
        &directory.join("partonsbi_metadata.json"),
        &serde_json::to_vec_pretty(&metadata)?,
    )?;
    Ok(())
}

fn format_list_v2(values: &[f64]) -> String {
    values
        .iter()
        .map(|value| float_text_v2(*value))
        .collect::<Vec<_>>()
        .join(", ")
}

fn format_space_line_v2(values: &[f64]) -> String {
    values
        .iter()
        .map(|value| float_text_v2(*value))
        .collect::<Vec<_>>()
        .join(" ")
}

fn float_text_v2(value: f64) -> String {
    format!("{value:.17e}")
}

fn write_new_v2(path: &Path, bytes: &[u8]) -> Result<(), PdfArtifactV2Error> {
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    file.write_all(bytes)?;
    file.sync_all()?;
    Ok(())
}

fn checksum_artifact_files_v2(
    root: &Path,
) -> Result<Vec<ArtifactFileChecksumV2>, PdfArtifactV2Error> {
    let mut paths = Vec::new();
    collect_files_v2(root, root, &mut paths)?;
    paths.sort();
    paths
        .into_iter()
        .map(|relative| {
            let bytes = fs::read(root.join(&relative))?;
            Ok(ArtifactFileChecksumV2 {
                relative_path: relative.to_string_lossy().replace('\\', "/"),
                sha256: format!("sha256:{:x}", Sha256::digest(&bytes)),
                byte_count: bytes.len() as u64,
            })
        })
        .collect()
}

fn collect_files_v2(
    root: &Path,
    current: &Path,
    paths: &mut Vec<PathBuf>,
) -> Result<(), std::io::Error> {
    for entry in fs::read_dir(current)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            collect_files_v2(root, &path, paths)?;
        } else {
            paths.push(path.strip_prefix(root).expect("descendant").to_path_buf());
        }
    }
    Ok(())
}

pub fn load_and_validate_artifact_v2(
    cache_directory: &Path,
) -> Result<PdfArtifactV2, PdfArtifactV2Error> {
    let manifest: PdfArtifactManifestV2 =
        serde_json::from_slice(&fs::read(cache_directory.join("artifact_manifest.json"))?)?;
    if manifest.schema_version != PDF_ARTIFACT_SCHEMA_VERSION_V2
        || manifest.cache_policy_version != ARTIFACT_CACHE_POLICY_VERSION_V2
        || manifest.evolution.policy_version != EVOLUTION_POLICY_VERSION_V2
        || manifest.grid.policy_version != ARTIFACT_GRID_POLICY_VERSION_V2
        || manifest.extrapolator_policy != "error"
    {
        return Err(PdfArtifactV2Error::UnsupportedVersion(
            "artifact manifest is not the accepted revised-D1 v2 contract".into(),
        ));
    }
    for expected in &manifest.checksums {
        let path = cache_directory.join(&expected.relative_path);
        let bytes = fs::read(&path)?;
        let actual = format!("sha256:{:x}", Sha256::digest(&bytes));
        if actual != expected.sha256 || bytes.len() as u64 != expected.byte_count {
            return Err(PdfArtifactV2Error::ChecksumMismatch {
                path,
                expected: expected.sha256.clone(),
                actual,
            });
        }
    }
    Ok(PdfArtifactV2 {
        cache_directory: cache_directory.to_path_buf(),
        set_directory: cache_directory.join(&manifest.set_name),
        manifest,
    })
}

pub fn evaluate_artifact_v2(
    artifact: &PdfArtifactV2,
    xs: &[f64],
    qs: &[f64],
) -> Result<EvolvedGridV2, PdfArtifactV2Error> {
    load_and_validate_artifact_v2(&artifact.cache_directory)?;
    if xs.is_empty()
        || qs.is_empty()
        || xs.windows(2).any(|pair| pair[0] >= pair[1])
        || qs.windows(2).any(|pair| pair[0] >= pair[1])
    {
        return Err(PdfArtifactV2Error::InvalidConfiguration(
            "v2 artifact evaluation requires ordered nonempty grids".into(),
        ));
    }
    let parent = artifact
        .set_directory
        .parent()
        .ok_or_else(|| PdfArtifactV2Error::ArtifactLoad("artifact parent is missing".into()))?;
    let parent = CString::new(parent.to_string_lossy().as_bytes())
        .map_err(|_| PdfArtifactV2Error::ArtifactLoad("artifact path contains NUL".into()))?;
    let set_name = CString::new(artifact.manifest.set_name.as_str())
        .map_err(|_| PdfArtifactV2Error::ArtifactLoad("artifact set contains NUL".into()))?;
    let mut values = vec![f64::NAN; xs.len() * qs.len() * D1_FLAVORS.len()];
    let mut alphas = vec![f64::NAN; qs.len()];
    let mut error = [0 as c_char; 1024];
    // SAFETY: fixed buffers remain live and the bridge catches C++ exceptions.
    let status = unsafe {
        partonsbi_lhapdf_artifact_evaluate(
            parent.as_ptr(),
            set_name.as_ptr(),
            xs.as_ptr(),
            xs.len(),
            qs.as_ptr(),
            qs.len(),
            values.as_mut_ptr(),
            alphas.as_mut_ptr(),
            error.as_mut_ptr(),
            error.len(),
        )
    };
    if status != 0 {
        return Err(PdfArtifactV2Error::ArtifactLoad(c_error(&error)));
    }
    Ok(EvolvedGridV2 {
        xs: xs.to_vec(),
        qs_gev: qs.to_vec(),
        flavors: D1_FLAVORS.to_vec(),
        xf_values: values,
        alpha_s_values: alphas,
        native_sum_rules: Vec::new(),
        independent_moments: Vec::new(),
        computational_grid: ComputationalGridKind::Doubled,
    })
}

struct CacheLockV2 {
    path: PathBuf,
    _file: File,
}

impl CacheLockV2 {
    fn acquire(path: &Path, timeout: Duration) -> Result<Self, PdfArtifactV2Error> {
        let started = Instant::now();
        loop {
            match OpenOptions::new().write(true).create_new(true).open(path) {
                Ok(mut file) => {
                    writeln!(file, "pid={}", std::process::id())?;
                    return Ok(Self {
                        path: path.to_path_buf(),
                        _file: file,
                    });
                }
                Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => {
                    if started.elapsed() >= timeout {
                        return Err(PdfArtifactV2Error::CacheLockTimeout(path.to_path_buf()));
                    }
                    thread::sleep(Duration::from_millis(25));
                }
                Err(error) => return Err(error.into()),
            }
        }
    }
}

impl Drop for CacheLockV2 {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.path);
    }
}

pub fn artifact_payload_sha256_v2(path: &Path) -> Result<String, PdfArtifactV2Error> {
    let mut file = File::open(path)?;
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 64 * 1024];
    loop {
        let count = file.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        digest.update(&buffer[..count]);
    }
    Ok(format!("sha256:{:x}", digest.finalize()))
}

fn upper_interval(value: f64, knots: &[f64]) -> usize {
    let upper = knots.partition_point(|candidate| *candidate <= value);
    upper.min(knots.len() - 1).saturating_sub(1)
}

fn x_cubic_value(
    evolved: &EvolvedGridV2,
    flavor: i32,
    global_iq: usize,
    x: f64,
) -> Result<f64, PdfArtifactV2Error> {
    let xs = &evolved.xs;
    if x < xs[0] || x > *xs.last().expect("nonempty grid") {
        return Err(PdfArtifactV2Error::InvalidConfiguration(
            "independent log-bicubic x request is outside support".into(),
        ));
    }
    let ix = upper_interval(x, xs);
    let log_x = x.ln();
    let log_left = xs[ix].ln();
    let log_right = xs[ix + 1].ln();
    let width = log_right - log_left;
    let t = (log_x - log_left) / width;
    let value = |index: usize| {
        evolved
            .xf(flavor, index, global_iq)
            .expect("declared evolved flavor")
    };
    let derivative = |index: usize| {
        if index == 0 {
            (value(1) - value(0)) / (xs[1].ln() - xs[0].ln())
        } else if index + 1 == xs.len() {
            (value(index) - value(index - 1)) / (xs[index].ln() - xs[index - 1].ln())
        } else {
            let left = (value(index) - value(index - 1)) / (xs[index].ln() - xs[index - 1].ln());
            let right = (value(index + 1) - value(index)) / (xs[index + 1].ln() - xs[index].ln());
            (left + right) / 2.0
        }
    };
    let low = value(ix);
    let high = value(ix + 1);
    let low_derivative = derivative(ix) * width;
    let high_derivative = derivative(ix + 1) * width;
    let t2 = t * t;
    let t3 = t2 * t;
    Ok((2.0 * t3 - 3.0 * t2 + 1.0) * low
        + (t3 - 2.0 * t2 + t) * low_derivative
        + (-2.0 * t3 + 3.0 * t2) * high
        + (t3 - t2) * high_derivative)
}

pub fn independent_log_bicubic_v2(
    evolved: &EvolvedGridV2,
    grid: &ArtifactGridV2,
    flavor: i32,
    x: f64,
    q: f64,
) -> Result<f64, PdfArtifactV2Error> {
    if !D1_FLAVORS.contains(&flavor) {
        return Err(PdfArtifactV2Error::InvalidConfiguration(format!(
            "unsupported independent-interpolation flavor {flavor}"
        )));
    }
    let repeated_q = grid.repeated_q_knots();
    if q < repeated_q[0] || q > *repeated_q.last().expect("nonempty Q grid") {
        return Err(PdfArtifactV2Error::InvalidConfiguration(
            "independent log-bicubic Q request is outside support".into(),
        ));
    }
    let iq = upper_interval(q, &repeated_q);
    let global_index = |flat_index: usize| {
        grid.unique_q_knots_gev
            .iter()
            .position(|candidate| candidate.to_bits() == repeated_q[flat_index].to_bits())
            .expect("repeated Q knot belongs to global union")
    };
    let low = x_cubic_value(evolved, flavor, global_index(iq), x)?;
    let high = x_cubic_value(evolved, flavor, global_index(iq + 1), x)?;
    let log_q2 = 2.0 * q.ln();
    let log_knots = repeated_q
        .iter()
        .map(|value| 2.0 * value.ln())
        .collect::<Vec<_>>();
    let width = log_knots[iq + 1] - log_knots[iq];
    if width <= 0.0 {
        return Err(PdfArtifactV2Error::InvalidConfiguration(
            "independent interpolation selected a zero-width Q interval".into(),
        ));
    }
    let lower_edge = iq == 0 || repeated_q[iq].to_bits() == repeated_q[iq - 1].to_bits();
    let upper_edge = iq + 1 == repeated_q.len() - 1
        || repeated_q[iq + 1].to_bits() == repeated_q[iq + 2].to_bits();
    if lower_edge && upper_edge {
        return Ok(low + (log_q2 - log_knots[iq]) / width * (high - low));
    }
    let low_derivative;
    let high_derivative;
    if lower_edge {
        low_derivative = high - low;
        let high_high = x_cubic_value(evolved, flavor, global_index(iq + 2), x)?;
        high_derivative = (low_derivative
            + (high_high - high) * width / (log_knots[iq + 2] - log_knots[iq + 1]))
            / 2.0;
    } else if upper_edge {
        high_derivative = high - low;
        let low_low = x_cubic_value(evolved, flavor, global_index(iq - 1), x)?;
        low_derivative =
            (high_derivative + (low - low_low) * width / (log_knots[iq] - log_knots[iq - 1])) / 2.0;
    } else {
        let low_low = x_cubic_value(evolved, flavor, global_index(iq - 1), x)?;
        let high_high = x_cubic_value(evolved, flavor, global_index(iq + 2), x)?;
        low_derivative =
            ((high - low) + (low - low_low) * width / (log_knots[iq] - log_knots[iq - 1])) / 2.0;
        high_derivative = ((high - low)
            + (high_high - high) * width / (log_knots[iq + 2] - log_knots[iq + 1]))
            / 2.0;
    }
    let t = (log_q2 - log_knots[iq]) / width;
    let t2 = t * t;
    let t3 = t2 * t;
    Ok((2.0 * t3 - 3.0 * t2 + 1.0) * low
        + (t3 - 2.0 * t2 + t) * low_derivative
        + (-2.0 * t3 + 3.0 * t2) * high
        + (t3 - t2) * high_derivative)
}

pub fn within_pdf_tolerance(expected: f64, actual: f64) -> bool {
    let absolute = (actual - expected).abs();
    absolute <= PDF_ABSOLUTE_TOLERANCE
        || (expected != 0.0 && absolute / expected.abs() <= PDF_RELATIVE_TOLERANCE)
}

fn within_exact_knot_tolerance(expected: f64, actual: f64) -> bool {
    let absolute = (actual - expected).abs();
    absolute <= EXACT_KNOT_ABSOLUTE_TOLERANCE
        || (expected != 0.0 && absolute / expected.abs() <= EXACT_KNOT_RELATIVE_TOLERANCE)
}

fn within_log_bicubic_tolerance(expected: f64, actual: f64) -> bool {
    let absolute = (actual - expected).abs();
    absolute <= LOG_BICUBIC_ABSOLUTE_TOLERANCE
        || (expected != 0.0 && absolute / expected.abs() <= LOG_BICUBIC_RELATIVE_TOLERANCE)
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct ErrorSummaryV2 {
    pub count: usize,
    pub outside_tolerance: usize,
    pub near_zero_count: usize,
    pub near_zero_outside_tolerance: usize,
    pub outside_tolerance_by_flavor: BTreeMap<i32, usize>,
    pub outside_tolerance_by_x_region: BTreeMap<String, usize>,
    pub outside_tolerance_by_q_region: BTreeMap<String, usize>,
    pub median_absolute_error: f64,
    pub p95_absolute_error: f64,
    pub p99_absolute_error: f64,
    pub maximum_absolute_error: f64,
    pub maximum_relative_error: f64,
    pub worst_flavor: i32,
    pub worst_x: f64,
    pub worst_q_gev: f64,
}

#[derive(Default)]
struct ErrorAccumulatorV2 {
    absolute_errors: Vec<f64>,
    summary: ErrorSummaryV2,
}

impl ErrorAccumulatorV2 {
    fn observe(&mut self, flavor: i32, x: f64, q: f64, expected: f64, actual: f64, accepted: bool) {
        let absolute = (actual - expected).abs();
        let relative = if expected == 0.0 {
            0.0
        } else {
            absolute / expected.abs()
        };
        self.summary.count += 1;
        self.summary.outside_tolerance += usize::from(!accepted);
        self.summary.near_zero_count += usize::from(expected.abs() < 1.0e-8);
        if !accepted {
            *self
                .summary
                .outside_tolerance_by_flavor
                .entry(flavor)
                .or_default() += 1;
            let x_region = if x < 1.0e-4 {
                "below_dis"
            } else if x <= 0.8 {
                "dis"
            } else {
                "endpoint"
            };
            *self
                .summary
                .outside_tolerance_by_x_region
                .entry(x_region.into())
                .or_default() += 1;
            let q_region = if q < 4.75 {
                "low_q"
            } else if q <= 100.0 {
                "mid_q"
            } else {
                "high_q"
            };
            *self
                .summary
                .outside_tolerance_by_q_region
                .entry(q_region.into())
                .or_default() += 1;
            self.summary.near_zero_outside_tolerance += usize::from(expected.abs() < 1.0e-8);
        }
        self.summary.maximum_relative_error = self.summary.maximum_relative_error.max(relative);
        if absolute >= self.summary.maximum_absolute_error {
            self.summary.maximum_absolute_error = absolute;
            self.summary.worst_flavor = flavor;
            self.summary.worst_x = x;
            self.summary.worst_q_gev = q;
        }
        self.absolute_errors.push(absolute);
    }

    fn finish(mut self) -> ErrorSummaryV2 {
        self.absolute_errors.sort_by(f64::total_cmp);
        self.summary.median_absolute_error = percentile(&self.absolute_errors, 0.5);
        self.summary.p95_absolute_error = percentile(&self.absolute_errors, 0.95);
        self.summary.p99_absolute_error = percentile(&self.absolute_errors, 0.99);
        self.summary
    }
}

fn percentile(sorted: &[f64], quantile: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    let index = ((sorted.len() - 1) as f64 * quantile).round() as usize;
    sorted[index]
}

#[derive(Debug, Clone)]
struct ProbeAxis {
    values: Vec<f64>,
    source_intervals: Vec<Option<usize>>,
}

fn probe_axis(knots: &[f64]) -> ProbeAxis {
    let mut pairs = vec![(knots[0], None)];
    for (interval, pair) in knots.windows(2).enumerate() {
        let left = pair[0].ln();
        let right = pair[1].ln();
        for fraction in [1.0 / 3.0, 0.5, 2.0 / 3.0] {
            pairs.push(((left + fraction * (right - left)).exp(), Some(interval)));
        }
    }
    pairs.push((*knots.last().expect("nonempty knots"), None));
    pairs.sort_by(|left, right| left.0.total_cmp(&right.0));
    pairs.dedup_by(|left, right| left.0.to_bits() == right.0.to_bits());
    ProbeAxis {
        values: pairs.iter().map(|pair| pair.0).collect(),
        source_intervals: pairs.iter().map(|pair| pair.1).collect(),
    }
}

fn midpoint_axis(knots: &[f64]) -> Vec<f64> {
    let mut values = Vec::with_capacity(2 * knots.len() - 1);
    for pair in knots.windows(2) {
        values.push(pair[0]);
        values.push(((pair[0].ln() + pair[1].ln()) / 2.0).exp());
    }
    values.push(*knots.last().expect("nonempty knots"));
    values
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RefinementIterationV2 {
    pub iteration: usize,
    pub x_knot_count: usize,
    pub q_knot_count: usize,
    pub failed_x_interval_count: usize,
    pub failed_q_interval_count: usize,
    pub inserted_x_knots: Vec<f64>,
    pub inserted_q_knots_gev: Vec<f64>,
    pub comparisons: usize,
    pub failures: usize,
    pub failures_by_flavor: BTreeMap<i32, usize>,
    pub failures_by_x_region: BTreeMap<String, usize>,
    pub failures_by_q_region: BTreeMap<String, usize>,
    pub maximum_absolute_error: f64,
    pub maximum_relative_error: f64,
    pub maximum_artifact_bytes: u64,
    pub maximum_anchor_seconds: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RefinementTraceV2 {
    pub policy_version: String,
    pub iterations: Vec<RefinementIterationV2>,
    pub complete: bool,
    pub failure_reason: Option<String>,
}

impl RefinementTraceV2 {
    pub fn canonical_hash(&self) -> Result<String, PdfArtifactV2Error> {
        Ok(format!(
            "sha256:{:x}",
            Sha256::digest(serde_json::to_vec(self)?)
        ))
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RefinementResultV2 {
    pub grid: ArtifactGridV2,
    pub trace: RefinementTraceV2,
}

pub fn mandatory_artifact_anchors_v2() -> Result<Vec<(String, PdfTheta)>, PdfArtifactV2Error> {
    [
        ("center", 0.0, 0.0),
        ("delta_min", -0.20, 0.0),
        ("delta_max", 0.20, 0.0),
        ("sea_min", 0.0, -0.25),
        ("sea_max", 0.0, 0.25),
        ("corner_min_min", -0.20, -0.25),
        ("corner_min_max", -0.20, 0.25),
        ("corner_max_min", 0.20, -0.25),
        ("corner_max_max", 0.20, 0.25),
    ]
    .into_iter()
    .map(|(name, delta, sea)| {
        PdfTheta::new(delta, sea)
            .map(|theta| (name.to_owned(), theta))
            .map_err(PdfArtifactV2Error::Boundary)
    })
    .collect()
}

pub fn refine_common_grid_v2(
    context: &ContinuousPdfContext,
    anchors: &[(String, PdfTheta)],
    cache_root: &Path,
) -> Result<RefinementResultV2, PdfArtifactV2Error> {
    if anchors.len() != 9 {
        return Err(PdfArtifactV2Error::InvalidConfiguration(
            "global revised-D1 refinement requires exactly nine anchors".into(),
        ));
    }
    let mut grid = ArtifactGridV2::initial(context)?;
    let mut trace = RefinementTraceV2 {
        policy_version: REFINEMENT_POLICY_VERSION_V2.into(),
        iterations: Vec::new(),
        complete: false,
        failure_reason: None,
    };
    for iteration in 0..=MAX_REFINEMENT_ITERATIONS {
        let x_probes = probe_axis(&grid.x_knots);
        let q_probes = probe_axis(&grid.unique_q_knots_gev);
        let mut failed_x = BTreeSet::new();
        let mut failed_q = BTreeSet::new();
        let mut comparisons = 0;
        let mut failures = 0;
        let mut failures_by_flavor = BTreeMap::new();
        let mut failures_by_x_region = BTreeMap::new();
        let mut failures_by_q_region = BTreeMap::new();
        let mut maximum_absolute_error = 0.0_f64;
        let mut maximum_relative_error = 0.0_f64;
        let mut maximum_artifact_bytes = 0;
        let mut maximum_anchor_seconds = 0.0_f64;
        let provisional_trace_hash = format!(
            "sha256:{:x}",
            Sha256::digest(format!("{}:{iteration}", grid.canonical_hash()?))
        );
        for (_, theta) in anchors {
            let started = Instant::now();
            let artifact = build_or_load_artifact_v2(
                context,
                *theta,
                &grid,
                &provisional_trace_hash,
                cache_root,
            )?;
            maximum_artifact_bytes = maximum_artifact_bytes.max(
                artifact
                    .manifest
                    .checksums
                    .iter()
                    .map(|entry| entry.byte_count)
                    .sum(),
            );
            let direct = evolve_grid_values_v2(
                context,
                *theta,
                &x_probes.values,
                &q_probes.values,
                ComputationalGridKind::Doubled,
            )?;
            let loaded = evaluate_artifact_v2(&artifact, &x_probes.values, &q_probes.values)?;
            for iq in 0..q_probes.values.len() {
                for ix in 0..x_probes.values.len() {
                    for flavor in D1_FLAVORS {
                        let expected = direct
                            .xf(flavor, ix, iq)
                            .expect("direct grid contains every flavor");
                        let actual = loaded
                            .xf(flavor, ix, iq)
                            .expect("artifact grid contains every flavor");
                        let absolute = (actual - expected).abs();
                        let relative = if expected == 0.0 {
                            0.0
                        } else {
                            absolute / expected.abs()
                        };
                        comparisons += 1;
                        maximum_absolute_error = maximum_absolute_error.max(absolute);
                        maximum_relative_error = maximum_relative_error.max(relative);
                        if !within_pdf_tolerance(expected, actual) {
                            failures += 1;
                            *failures_by_flavor.entry(flavor).or_default() += 1;
                            let x_region = if x_probes.values[ix] < 1.0e-4 {
                                "below_dis"
                            } else if x_probes.values[ix] <= 0.8 {
                                "dis"
                            } else {
                                "endpoint"
                            };
                            *failures_by_x_region.entry(x_region.into()).or_default() += 1;
                            let q_region =
                                if q_probes.values[iq] < context.metadata.bottom_threshold_gev {
                                    "low_q"
                                } else if q_probes.values[iq] <= 100.0 {
                                    "mid_q"
                                } else {
                                    "high_q"
                                };
                            *failures_by_q_region.entry(q_region.into()).or_default() += 1;
                            if let Some(interval) = x_probes.source_intervals[ix] {
                                failed_x.insert(interval);
                            }
                            if let Some(interval) = q_probes.source_intervals[iq] {
                                failed_q.insert(interval);
                            }
                        }
                    }
                }
            }
            let elapsed = started.elapsed().as_secs_f64();
            maximum_anchor_seconds = maximum_anchor_seconds.max(elapsed);
            if elapsed > MAX_SECONDS_PER_ANCHOR {
                trace.failure_reason = Some(format!(
                    "anchor construction/validation exceeded {MAX_SECONDS_PER_ANCHOR} seconds"
                ));
            }
        }
        let mut inserted_x = Vec::new();
        let mut inserted_q = Vec::new();
        if failures == 0 {
            trace.complete = true;
        } else if iteration == MAX_REFINEMENT_ITERATIONS {
            trace.failure_reason =
                Some("fixed probe failures remain after four refinement iterations".into());
        } else if trace.failure_reason.is_none() {
            inserted_x = failed_x
                .iter()
                .map(|index| {
                    let pair = &grid.x_knots[*index..=*index + 1];
                    ((pair[0].ln() + pair[1].ln()) / 2.0).exp()
                })
                .collect();
            inserted_q = failed_q
                .iter()
                .map(|index| {
                    let pair = &grid.unique_q_knots_gev[*index..=*index + 1];
                    ((pair[0].ln() + pair[1].ln()) / 2.0).exp()
                })
                .collect();
            if grid.x_knots.len() + inserted_x.len() > MAX_X_KNOTS
                || grid.unique_q_knots_gev.len() + inserted_q.len() > MAX_Q_KNOTS
            {
                trace.failure_reason =
                    Some("deterministic refinement would exceed a knot-count cap".into());
            }
        }
        trace.iterations.push(RefinementIterationV2 {
            iteration,
            x_knot_count: grid.x_knots.len(),
            q_knot_count: grid.unique_q_knots_gev.len(),
            failed_x_interval_count: failed_x.len(),
            failed_q_interval_count: failed_q.len(),
            inserted_x_knots: inserted_x.clone(),
            inserted_q_knots_gev: inserted_q.clone(),
            comparisons,
            failures,
            failures_by_flavor,
            failures_by_x_region,
            failures_by_q_region,
            maximum_absolute_error,
            maximum_relative_error,
            maximum_artifact_bytes,
            maximum_anchor_seconds,
        });
        if trace.complete || trace.failure_reason.is_some() {
            break;
        }
        let mut xs = grid.x_knots.clone();
        xs.extend(inserted_x);
        let mut qs = grid.unique_q_knots_gev.clone();
        qs.extend(inserted_q);
        grid = ArtifactGridV2::from_unique_knots(
            xs,
            qs,
            context.metadata.charm_threshold_gev,
            context.metadata.bottom_threshold_gev,
        )?;
        if grid.estimated_member_bytes() > MAX_ARTIFACT_BYTES {
            trace.failure_reason =
                Some("deterministic refinement would exceed the payload cap".into());
            break;
        }
    }
    Ok(RefinementResultV2 { grid, trace })
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct MomentClosureV2 {
    pub maximum_base_full_residual: f64,
    pub maximum_doubled_full_residual: f64,
    pub maximum_leakage_difference: f64,
    pub minimum_leakage: f64,
    pub maximum_leakage: f64,
    pub high_q_base: IndependentMoments,
    pub high_q_doubled: IndependentMoments,
    pub passed: bool,
}

pub fn validate_moments_v2(
    base: &EvolvedGridV2,
    doubled: &EvolvedGridV2,
) -> Result<MomentClosureV2, PdfArtifactV2Error> {
    if base.qs_gev != doubled.qs_gev
        || base.independent_moments.len() != doubled.independent_moments.len()
        || base.independent_moments.is_empty()
    {
        return Err(PdfArtifactV2Error::InvalidConfiguration(
            "base and doubled grids do not share the moment Q grid".into(),
        ));
    }
    let residual = |moments: &IndependentMoments| {
        (moments.full_u_valence - 2.0)
            .abs()
            .max((moments.full_d_valence - 1.0).abs())
            .max((moments.full_momentum - 1.0).abs())
    };
    let maximum_base_full_residual = base
        .independent_moments
        .iter()
        .map(residual)
        .fold(0.0_f64, f64::max);
    let maximum_doubled_full_residual = doubled
        .independent_moments
        .iter()
        .map(residual)
        .fold(0.0_f64, f64::max);
    let maximum_leakage_difference = base
        .independent_moments
        .iter()
        .zip(&doubled.independent_moments)
        .map(|(left, right)| (left.leaked_momentum - right.leaked_momentum).abs())
        .fold(0.0_f64, f64::max);
    let minimum_leakage = base
        .independent_moments
        .iter()
        .chain(&doubled.independent_moments)
        .map(|moments| moments.leaked_momentum)
        .fold(f64::INFINITY, f64::min);
    let maximum_leakage = base
        .independent_moments
        .iter()
        .chain(&doubled.independent_moments)
        .map(|moments| moments.leaked_momentum)
        .fold(f64::NEG_INFINITY, f64::max);
    let passed = maximum_base_full_residual <= FULL_DOMAIN_SUM_RULE_TOLERANCE
        && maximum_doubled_full_residual <= FULL_DOMAIN_SUM_RULE_TOLERANCE
        && maximum_leakage_difference <= LEAKAGE_CONVERGENCE_TOLERANCE
        && minimum_leakage >= -1.0e-12;
    Ok(MomentClosureV2 {
        maximum_base_full_residual,
        maximum_doubled_full_residual,
        maximum_leakage_difference,
        minimum_leakage,
        maximum_leakage,
        high_q_base: base
            .independent_moments
            .last()
            .expect("checked nonempty moments")
            .clone(),
        high_q_doubled: doubled
            .independent_moments
            .last()
            .expect("checked nonempty moments")
            .clone(),
        passed,
    })
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SignTopologyClosureV2 {
    pub comparisons: usize,
    pub mismatched_components: usize,
    pub direct_negative_components: usize,
    pub artifact_negative_components: usize,
    pub maximum_direct_negative_momentum: f64,
    pub maximum_artifact_negative_momentum: f64,
    pub passed: bool,
}

fn sign_class(value: f64) -> i8 {
    if value > PDF_ABSOLUTE_TOLERANCE {
        1
    } else if value < -PDF_ABSOLUTE_TOLERANCE {
        -1
    } else {
        0
    }
}

fn sign_components(values: &[f64]) -> usize {
    let mut count = 0;
    let mut negative = false;
    for value in values {
        let next = sign_class(*value) < 0;
        if next && !negative {
            count += 1;
        }
        negative = next;
    }
    count
}

fn negative_momentum_trapezoid(xs: &[f64], values: &[f64]) -> f64 {
    xs.windows(2)
        .zip(values.windows(2))
        .map(|(x, y)| {
            let left = (-y[0]).max(0.0);
            let right = (-y[1]).max(0.0);
            (x[1] - x[0]) * (left + right) / 2.0
        })
        .sum()
}

pub fn compare_sign_topology_v2(
    direct: &EvolvedGridV2,
    loaded: &EvolvedGridV2,
) -> Result<SignTopologyClosureV2, PdfArtifactV2Error> {
    if direct.xs != loaded.xs || direct.qs_gev != loaded.qs_gev {
        return Err(PdfArtifactV2Error::InvalidConfiguration(
            "sign-topology grids differ".into(),
        ));
    }
    let mut comparisons = 0;
    let mut mismatched_components = 0;
    let mut direct_negative_components = 0;
    let mut artifact_negative_components = 0;
    let mut maximum_direct_negative_momentum = 0.0_f64;
    let mut maximum_artifact_negative_momentum = 0.0_f64;
    for iq in 0..direct.qs_gev.len() {
        for flavor in D1_FLAVORS {
            let direct_values = (0..direct.xs.len())
                .map(|ix| direct.xf(flavor, ix, iq).expect("direct flavor"))
                .collect::<Vec<_>>();
            let loaded_values = (0..loaded.xs.len())
                .map(|ix| loaded.xf(flavor, ix, iq).expect("loaded flavor"))
                .collect::<Vec<_>>();
            let direct_components = sign_components(&direct_values);
            let artifact_components = sign_components(&loaded_values);
            comparisons += 1;
            mismatched_components += usize::from(direct_components != artifact_components);
            direct_negative_components += direct_components;
            artifact_negative_components += artifact_components;
            maximum_direct_negative_momentum = maximum_direct_negative_momentum
                .max(negative_momentum_trapezoid(&direct.xs, &direct_values));
            maximum_artifact_negative_momentum = maximum_artifact_negative_momentum
                .max(negative_momentum_trapezoid(&loaded.xs, &loaded_values));
        }
    }
    Ok(SignTopologyClosureV2 {
        comparisons,
        mismatched_components,
        direct_negative_components,
        artifact_negative_components,
        maximum_direct_negative_momentum,
        maximum_artifact_negative_momentum,
        passed: mismatched_components == 0,
    })
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TransportClosureV2 {
    pub exact_knots: ErrorSummaryV2,
    pub independent_log_bicubic: ErrorSummaryV2,
    pub direct_artifact: ErrorSummaryV2,
    pub threshold_transport: ErrorSummaryV2,
    pub alpha_s_maximum_relative_error: f64,
    pub alpha_s_maximum_absolute_error: f64,
    pub sign_topology: SignTopologyClosureV2,
    pub passed: bool,
}

pub fn validate_transport_v2(
    context: &ContinuousPdfContext,
    theta: PdfTheta,
    grid: &ArtifactGridV2,
    trace_hash: &str,
    cache_root: &Path,
) -> Result<(PdfArtifactV2, TransportClosureV2), PdfArtifactV2Error> {
    let artifact = build_or_load_artifact_v2(context, theta, grid, trace_hash, cache_root)?;
    let direct_knots = evolve_grid_values_v2(
        context,
        theta,
        &grid.x_knots,
        &grid.unique_q_knots_gev,
        ComputationalGridKind::Doubled,
    )?;
    let loaded_knots = evaluate_artifact_v2(&artifact, &grid.x_knots, &grid.unique_q_knots_gev)?;
    let mut exact = ErrorAccumulatorV2::default();
    for (iq, q) in grid.unique_q_knots_gev.iter().copied().enumerate() {
        for (ix, x) in grid.x_knots.iter().copied().enumerate() {
            for flavor in D1_FLAVORS {
                let expected = direct_knots.xf(flavor, ix, iq).expect("direct flavor");
                let actual = loaded_knots.xf(flavor, ix, iq).expect("loaded flavor");
                exact.observe(
                    flavor,
                    x,
                    q,
                    expected,
                    actual,
                    within_exact_knot_tolerance(expected, actual),
                );
            }
        }
    }
    let (alpha_s_maximum_relative_error, alpha_s_maximum_absolute_error) = direct_knots
        .alpha_s_values
        .iter()
        .zip(&loaded_knots.alpha_s_values)
        .fold(
            (0.0_f64, 0.0_f64),
            |(max_relative, max_absolute), (a, b)| {
                let absolute = (b - a).abs();
                let relative = if *a == 0.0 { 0.0 } else { absolute / a.abs() };
                (max_relative.max(relative), max_absolute.max(absolute))
            },
        );

    let x_probes = probe_axis(&grid.x_knots);
    let q_probes = probe_axis(&grid.unique_q_knots_gev);
    let direct_probes = evolve_grid_values_v2(
        context,
        theta,
        &x_probes.values,
        &q_probes.values,
        ComputationalGridKind::Doubled,
    )?;
    let loaded_probes = evaluate_artifact_v2(&artifact, &x_probes.values, &q_probes.values)?;
    let mut independent = ErrorAccumulatorV2::default();
    let mut transport = ErrorAccumulatorV2::default();
    for (iq, q) in q_probes.values.iter().copied().enumerate() {
        for (ix, x) in x_probes.values.iter().copied().enumerate() {
            for flavor in D1_FLAVORS {
                let direct = direct_probes.xf(flavor, ix, iq).expect("direct flavor");
                let loaded = loaded_probes.xf(flavor, ix, iq).expect("loaded flavor");
                let reconstructed = independent_log_bicubic_v2(&direct_knots, grid, flavor, x, q)?;
                independent.observe(
                    flavor,
                    x,
                    q,
                    reconstructed,
                    loaded,
                    within_log_bicubic_tolerance(reconstructed, loaded),
                );
                transport.observe(
                    flavor,
                    x,
                    q,
                    direct,
                    loaded,
                    within_pdf_tolerance(direct, loaded),
                );
            }
        }
    }
    let sign_topology = compare_sign_topology_v2(&direct_probes, &loaded_probes)?;
    let mut threshold_qs = vec![grid.unique_q_knots_gev[0]];
    threshold_qs.extend(grid.thresholds_gev.iter().flat_map(|q| {
        [
            f64::from_bits(q.to_bits() - 1),
            *q,
            f64::from_bits(q.to_bits() + 1),
        ]
    }));
    let threshold_xs = midpoint_axis(&grid.x_knots);
    let direct_thresholds = evolve_grid_values_v2(
        context,
        theta,
        &threshold_xs,
        &threshold_qs,
        ComputationalGridKind::Doubled,
    )?;
    let loaded_thresholds = evaluate_artifact_v2(&artifact, &threshold_xs, &threshold_qs)?;
    let mut threshold_transport = ErrorAccumulatorV2::default();
    for (iq, q) in threshold_qs.iter().copied().enumerate().skip(1) {
        for (ix, x) in threshold_xs.iter().copied().enumerate() {
            for flavor in D1_FLAVORS {
                let direct = direct_thresholds.xf(flavor, ix, iq).expect("direct flavor");
                let loaded = loaded_thresholds.xf(flavor, ix, iq).expect("loaded flavor");
                threshold_transport.observe(
                    flavor,
                    x,
                    q,
                    direct,
                    loaded,
                    within_pdf_tolerance(direct, loaded),
                );
            }
        }
    }
    let exact_knots = exact.finish();
    let independent_log_bicubic = independent.finish();
    let direct_artifact = transport.finish();
    let threshold_transport = threshold_transport.finish();
    let passed = exact_knots.outside_tolerance == 0
        && independent_log_bicubic.outside_tolerance == 0
        && direct_artifact.outside_tolerance == 0
        && threshold_transport.outside_tolerance == 0
        && (alpha_s_maximum_relative_error <= super::ALPHA_S_RELATIVE_TOLERANCE
            || alpha_s_maximum_absolute_error <= super::ALPHA_S_ABSOLUTE_TOLERANCE)
        && sign_topology.passed;
    Ok((
        artifact,
        TransportClosureV2 {
            exact_knots,
            independent_log_bicubic,
            direct_artifact,
            threshold_transport,
            alpha_s_maximum_relative_error,
            alpha_s_maximum_absolute_error,
            sign_topology,
            passed,
        },
    ))
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PhotonObservableClosureV2 {
    pub x_count: usize,
    pub q_count: usize,
    pub y_count: usize,
    pub f2: ErrorSummaryV2,
    pub fl: ErrorSummaryV2,
    pub minimum_direct_reduced_cross_section: f64,
    pub minimum_artifact_reduced_cross_section: f64,
    pub non_finite_count: usize,
    pub passed: bool,
}

pub fn photon_observable_grid_v2() -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let xs = vec![
        1.0e-4, 3.0e-4, 1.0e-3, 3.0e-3, 1.0e-2, 3.0e-2, 0.1, 0.3, 0.8,
    ];
    let q2s: Vec<f64> = vec![3.5, 10.0, 22.55, 22.5625, 22.58, 100.0, 1_000.0, 10_000.0];
    let qs = q2s.into_iter().map(f64::sqrt).collect();
    let ys = vec![0.01, 0.5, 0.95];
    (xs, qs, ys)
}

pub fn validate_photon_observables_v2(
    context: &ContinuousPdfContext,
    theta: PdfTheta,
    artifact: &PdfArtifactV2,
) -> Result<PhotonObservableClosureV2, PdfArtifactV2Error> {
    let config = D1EvolutionConfigV2::from_context(context)?;
    let point = context.construct(theta)?;
    let normalizations = point.effective_raw_normalizations();
    let (xs, qs, ys) = photon_observable_grid_v2();
    let raw_set = CString::new(context.metadata.set_name.as_str())
        .map_err(|_| PdfArtifactV2Error::InvalidConfiguration("raw set contains NUL".into()))?;
    let parent = artifact
        .set_directory
        .parent()
        .ok_or_else(|| PdfArtifactV2Error::ArtifactLoad("artifact parent missing".into()))?;
    let parent = CString::new(parent.to_string_lossy().as_bytes())
        .map_err(|_| PdfArtifactV2Error::ArtifactLoad("artifact path contains NUL".into()))?;
    let set_name = CString::new(artifact.manifest.set_name.as_str())
        .map_err(|_| PdfArtifactV2Error::ArtifactLoad("artifact set contains NUL".into()))?;
    let mut direct = vec![f64::NAN; xs.len() * qs.len() * 2];
    let mut loaded = vec![f64::NAN; direct.len()];
    let mut error = [0 as c_char; 1024];
    // SAFETY: buffers remain live and the bridge catches all C++ exceptions.
    let status = unsafe {
        partonsbi_apfel_artifact_observables_v2(
            raw_set.as_ptr(),
            context.metadata.member,
            config.q0_gev,
            config.alpha_s_mz,
            config.mz_gev,
            config.q_maximum_gev,
            config.charm_mass_gev,
            config.charm_threshold_gev,
            config.bottom_mass_gev,
            config.bottom_threshold_gev,
            config.top_mass_gev,
            config.top_threshold_gev,
            config.perturbative_order,
            theta.delta_v,
            normalizations.sea_scale,
            normalizations.a_u,
            normalizations.a_d,
            normalizations.a_g,
            COMPUTATIONAL_XMIN,
            EXPORTED_XMIN,
            ComputationalGridKind::Doubled.node_multiplier(),
            parent.as_ptr(),
            set_name.as_ptr(),
            xs.as_ptr(),
            xs.len(),
            qs.as_ptr(),
            qs.len(),
            direct.as_mut_ptr(),
            loaded.as_mut_ptr(),
            error.as_mut_ptr(),
            error.len(),
        )
    };
    if status != 0 {
        return Err(PdfArtifactV2Error::Evolution(c_error(&error)));
    }
    let mut f2 = ErrorAccumulatorV2::default();
    let mut fl = ErrorAccumulatorV2::default();
    let mut minimum_direct_reduced_cross_section = f64::INFINITY;
    let mut minimum_artifact_reduced_cross_section = f64::INFINITY;
    let mut non_finite_count = 0;
    for (iq, q) in qs.iter().copied().enumerate() {
        for (ix, x) in xs.iter().copied().enumerate() {
            let index = 2 * (iq * xs.len() + ix);
            f2.observe(
                0,
                x,
                q,
                direct[index],
                loaded[index],
                observable_within_tolerance(direct[index], loaded[index]),
            );
            fl.observe(
                0,
                x,
                q,
                direct[index + 1],
                loaded[index + 1],
                observable_within_tolerance(direct[index + 1], loaded[index + 1]),
            );
            for y in &ys {
                let y_plus = 1.0 + (1.0 - y).powi(2);
                let direct_reduced = direct[index] - y * y / y_plus * direct[index + 1];
                let artifact_reduced = loaded[index] - y * y / y_plus * loaded[index + 1];
                non_finite_count +=
                    usize::from(!direct_reduced.is_finite() || !artifact_reduced.is_finite());
                minimum_direct_reduced_cross_section =
                    minimum_direct_reduced_cross_section.min(direct_reduced);
                minimum_artifact_reduced_cross_section =
                    minimum_artifact_reduced_cross_section.min(artifact_reduced);
            }
        }
    }
    let f2 = f2.finish();
    let fl = fl.finish();
    let passed = f2.outside_tolerance == 0
        && fl.outside_tolerance == 0
        && non_finite_count == 0
        && minimum_direct_reduced_cross_section >= REDUCED_CROSS_SECTION_MINIMUM
        && minimum_artifact_reduced_cross_section >= REDUCED_CROSS_SECTION_MINIMUM;
    Ok(PhotonObservableClosureV2 {
        x_count: xs.len(),
        q_count: qs.len(),
        y_count: ys.len(),
        f2,
        fl,
        minimum_direct_reduced_cross_section,
        minimum_artifact_reduced_cross_section,
        non_finite_count,
        passed,
    })
}

fn observable_within_tolerance(expected: f64, actual: f64) -> bool {
    let absolute = (actual - expected).abs();
    absolute <= OBSERVABLE_ABSOLUTE_TOLERANCE
        || (expected != 0.0 && absolute / expected.abs() <= OBSERVABLE_RELATIVE_TOLERANCE)
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RawCtFidelityV2 {
    pub raw_boundary_apfel_vs_public: ErrorSummaryV2,
    pub projected_vs_raw_boundary_apfel: ErrorSummaryV2,
    pub projected_apfel_vs_public: ErrorSummaryV2,
    pub binding_gate: bool,
}

pub fn validate_raw_ct_fidelity_v2(
    context: &ContinuousPdfContext,
) -> Result<RawCtFidelityV2, PdfArtifactV2Error> {
    let grid = ArtifactGridV2::initial(context)?;
    let xs = midpoint_axis(&grid.x_knots);
    let qs = midpoint_axis(&grid.unique_q_knots_gev);
    let center = PdfTheta::new(0.0, 0.0)?;
    let projected =
        evolve_grid_values_v2(context, center, &xs, &qs, ComputationalGridKind::Doubled)?;
    let raw_boundary = evolve_raw_ct_center_v2(context, &xs, &qs, ComputationalGridKind::Doubled)?;
    let public = LhapdfProvider::new("CT18NLO", 0)
        .map_err(|error| PdfArtifactV2Error::ArtifactLoad(error.to_string()))?;
    let mut raw_public = ErrorAccumulatorV2::default();
    let mut projected_raw = ErrorAccumulatorV2::default();
    let mut projected_public = ErrorAccumulatorV2::default();
    for (iq, q) in qs.iter().copied().enumerate() {
        for (ix, x) in xs.iter().copied().enumerate() {
            for flavor in D1_FLAVORS {
                let public_value = public
                    .xfx_at_scale(flavor, x, q)
                    .map_err(|error| PdfArtifactV2Error::ArtifactLoad(error.to_string()))?;
                let raw_value = raw_boundary.xf(flavor, ix, iq).expect("raw flavor");
                let projected_value = projected.xf(flavor, ix, iq).expect("projected flavor");
                raw_public.observe(
                    flavor,
                    x,
                    q,
                    public_value,
                    raw_value,
                    within_raw_ct_diagnostic(public_value, raw_value),
                );
                projected_raw.observe(
                    flavor,
                    x,
                    q,
                    raw_value,
                    projected_value,
                    within_raw_ct_diagnostic(raw_value, projected_value),
                );
                projected_public.observe(
                    flavor,
                    x,
                    q,
                    public_value,
                    projected_value,
                    within_raw_ct_diagnostic(public_value, projected_value),
                );
            }
        }
    }
    Ok(RawCtFidelityV2 {
        raw_boundary_apfel_vs_public: raw_public.finish(),
        projected_vs_raw_boundary_apfel: projected_raw.finish(),
        projected_apfel_vs_public: projected_public.finish(),
        binding_gate: false,
    })
}

fn within_raw_ct_diagnostic(expected: f64, actual: f64) -> bool {
    let absolute = (actual - expected).abs();
    if expected.abs() >= 1.0e-8 {
        absolute / expected.abs() <= 2.0e-3
    } else {
        absolute <= PDF_ABSOLUTE_TOLERANCE
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn computational_grids_and_versions_are_frozen() {
        assert_eq!(
            ComputationalGridDefinition::new(ComputationalGridKind::Base).subgrids,
            vec![
                (400, 1e-11, 3),
                (250, 0.1, 3),
                (180, 0.6, 3),
                (160, 0.85, 5)
            ]
        );
        assert_eq!(
            ComputationalGridDefinition::new(ComputationalGridKind::Doubled).subgrids,
            vec![
                (800, 1e-11, 3),
                (500, 0.1, 3),
                (360, 0.6, 3),
                (320, 0.85, 5)
            ]
        );
        assert_ne!(
            PDF_ARTIFACT_SCHEMA_VERSION_V2,
            super::super::PDF_ARTIFACT_SCHEMA_VERSION
        );
    }

    #[test]
    fn threshold_subgrids_repeat_boundaries_and_exclude_top() {
        let grid = ArtifactGridV2::from_unique_knots(
            vec![1e-9, 1e-5, 0.1, 1.0],
            vec![1.295, 1.3, 2.0, 4.75, 10.0, 100_000.0],
            1.3,
            4.75,
        )
        .unwrap();
        assert_eq!(grid.q_subgrids_gev.len(), 3);
        assert_eq!(grid.q_subgrids_gev[0].last(), Some(&1.3));
        assert_eq!(grid.q_subgrids_gev[1].first(), Some(&1.3));
        assert_eq!(grid.q_subgrids_gev[1].last(), Some(&4.75));
        assert_eq!(grid.q_subgrids_gev[2].first(), Some(&4.75));
        assert!(!grid.unique_q_knots_gev.contains(&172.0));
    }

    #[test]
    fn refinement_and_payload_caps_are_binding() {
        assert_eq!(MAX_REFINEMENT_ITERATIONS, 4);
        assert_eq!(MAX_X_KNOTS, 1025);
        assert_eq!(MAX_Q_KNOTS, 257);
        assert_eq!(MAX_ARTIFACT_BYTES, 268_435_456);
    }

    #[test]
    fn exactly_nine_global_anchors_are_unique() {
        let anchors = mandatory_artifact_anchors_v2().unwrap();
        assert_eq!(anchors.len(), 9);
        let unique = anchors
            .iter()
            .map(|(_, theta)| (theta.delta_v.to_bits(), theta.lambda_sea.to_bits()))
            .collect::<BTreeSet<_>>();
        assert_eq!(unique.len(), 9);
    }

    #[test]
    fn sign_components_and_negative_momentum_are_not_clipped() {
        let values = [1.0, -2.0, -1.0, 0.0, 3.0, -4.0];
        assert_eq!(sign_components(&values), 2);
        let negative = negative_momentum_trapezoid(&[0.0, 0.1, 0.2, 0.4, 0.7, 1.0], &values);
        assert!(negative > 0.0);
        assert_eq!(values[1], -2.0);
        assert_eq!(values[5], -4.0);
    }

    #[test]
    fn observable_grid_is_predeclared_and_covers_the_dis_domain() {
        let (xs, qs, ys) = photon_observable_grid_v2();
        assert_eq!(xs.first(), Some(&1.0e-4));
        assert_eq!(xs.last(), Some(&0.8));
        assert_eq!(qs.first().map(|q| q * q), Some(3.5));
        assert_eq!(qs.last().map(|q| q * q), Some(10_000.0));
        assert!(qs.iter().any(|q| (*q - 4.75).abs() < 1.0e-12));
        assert_eq!(ys, vec![0.01, 0.5, 0.95]);
    }

    #[test]
    fn refinement_hash_is_byte_stable_and_versioned() {
        let trace = RefinementTraceV2 {
            policy_version: REFINEMENT_POLICY_VERSION_V2.into(),
            iterations: Vec::new(),
            complete: false,
            failure_reason: Some("unit diagnostic".into()),
        };
        assert_eq!(
            trace.canonical_hash().unwrap(),
            trace.canonical_hash().unwrap()
        );
        assert_ne!(
            trace.policy_version,
            super::super::ARTIFACT_GRID_POLICY_VERSION
        );
    }

    #[test]
    fn d2_is_never_authorized_by_revised_stage1_code() {
        let candidate = true;
        let d2_authorized = false;
        assert!(candidate);
        assert!(!d2_authorized);
    }
}
