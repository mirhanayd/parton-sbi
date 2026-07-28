//! Phase 1B-D1 APFEL++ evolution and immutable one-member LHAPDF6 artifacts.
//!
//! This module consumes only the approved D0R v2 boundary family. It does not
//! couple artifacts to PYTHIA or generate events.

use std::collections::BTreeMap;
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
    ContinuousPdfContext, ContinuousPdfError, ContinuousPdfFamilyVersion, PdfTheta,
    CONTINUOUS_PDF_FAMILY_VERSION_V2, EXTRAPOLATION_CALLER_POLICY, PROJECTED_BASELINE_VERSION_V2,
};

pub const PDF_ARTIFACT_SCHEMA_VERSION: &str = "partonsbi.lhapdf_artifact.v1";
pub const EVOLUTION_POLICY_VERSION: &str = "apfelxx_4.8.0_nlo_vfns_v1";
pub const ARTIFACT_GRID_POLICY_VERSION: &str = "ct18nlo_authoritative_knots_plus_thresholds_v1";
pub const ARTIFACT_CACHE_POLICY_VERSION: &str = "immutable_sha256_atomic_publish_v1";
pub const ROUND_TRIP_RELATIVE_TOLERANCE: f64 = 1.0e-5;
pub const ROUND_TRIP_ABSOLUTE_TOLERANCE: f64 = 1.0e-9;
pub const ALPHA_S_RELATIVE_TOLERANCE: f64 = 1.0e-8;
pub const ALPHA_S_ABSOLUTE_TOLERANCE: f64 = 1.0e-10;
pub const EVOLVED_SUM_RULE_TOLERANCE: f64 = 1.0e-5;
pub const BOUNDARY_RELATIVE_TOLERANCE: f64 = 1.0e-12;
pub const BOUNDARY_ABSOLUTE_TOLERANCE: f64 = 1.0e-14;
pub const D1_FLAVORS: [i32; 11] = [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 21];

#[derive(Debug)]
pub enum PdfArtifactError {
    Boundary(ContinuousPdfError),
    UnsupportedFamily(String),
    InvalidConfiguration(String),
    Evolution(String),
    ArtifactLoad(String),
    Io(std::io::Error),
    Serialization(serde_json::Error),
    CacheLockTimeout(PathBuf),
    ChecksumMismatch {
        path: PathBuf,
        expected: String,
        actual: String,
    },
    ExistingInvalidArtifact(PathBuf),
}

impl fmt::Display for PdfArtifactError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Boundary(error) => write!(f, "{error}"),
            Self::UnsupportedFamily(message)
            | Self::InvalidConfiguration(message)
            | Self::Evolution(message)
            | Self::ArtifactLoad(message) => f.write_str(message),
            Self::Io(error) => write!(f, "{error}"),
            Self::Serialization(error) => write!(f, "{error}"),
            Self::CacheLockTimeout(path) => {
                write!(f, "timed out acquiring artifact lock {}", path.display())
            }
            Self::ChecksumMismatch {
                path,
                expected,
                actual,
            } => write!(
                f,
                "artifact checksum mismatch for {}: expected {expected}, found {actual}",
                path.display()
            ),
            Self::ExistingInvalidArtifact(path) => {
                write!(f, "existing artifact is invalid: {}", path.display())
            }
        }
    }
}

impl Error for PdfArtifactError {}

impl From<ContinuousPdfError> for PdfArtifactError {
    fn from(value: ContinuousPdfError) -> Self {
        Self::Boundary(value)
    }
}

impl From<std::io::Error> for PdfArtifactError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}

impl From<serde_json::Error> for PdfArtifactError {
    fn from(value: serde_json::Error) -> Self {
        Self::Serialization(value)
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct D1EvolutionConfig {
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
    pub x_minimum: f64,
    pub x_maximum: f64,
    pub extrapolation_policy: String,
}

impl D1EvolutionConfig {
    pub fn from_context(context: &ContinuousPdfContext) -> Result<Self, PdfArtifactError> {
        if context.family_version() != ContinuousPdfFamilyVersion::V2 {
            return Err(PdfArtifactError::UnsupportedFamily(
                "D1 accepts only ct18nlo_two_parameter_boundary_v2".into(),
            ));
        }
        let m = &context.metadata;
        if m.lhapdf_version != "6.5.6" || m.order_qcd != 1 || m.flavor_scheme != "variable" {
            return Err(PdfArtifactError::InvalidConfiguration(format!(
                "D1 requires LHAPDF 6.5.6 CT18NLO NLO VFNS metadata, found version={}, order={}, scheme={}",
                m.lhapdf_version, m.order_qcd, m.flavor_scheme
            )));
        }
        Ok(Self {
            schema_version: PDF_ARTIFACT_SCHEMA_VERSION.into(),
            policy_version: EVOLUTION_POLICY_VERSION.into(),
            apfelxx_version: "4.8.0".into(),
            perturbative_order: m.order_qcd,
            flavor_scheme: m.flavor_scheme.clone(),
            maximum_active_flavors: 5,
            alpha_s_mz: m.alpha_s_mz,
            mz_gev: m.mz_gev,
            q0_gev: m.q0_gev,
            q_minimum_gev: m.support.q_minimum_gev,
            q_maximum_gev: m.support.q_maximum_gev,
            charm_mass_gev: m.charm_mass_gev,
            charm_threshold_gev: m.charm_threshold_gev,
            bottom_mass_gev: m.bottom_mass_gev,
            bottom_threshold_gev: m.bottom_threshold_gev,
            top_mass_gev: m.top_mass_gev,
            top_threshold_gev: m.top_threshold_gev,
            x_minimum: m.support.x_minimum,
            x_maximum: m.support.x_maximum,
            extrapolation_policy: EXTRAPOLATION_CALLER_POLICY.into(),
        })
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ArtifactGrid {
    pub policy_version: String,
    pub x_knots: Vec<f64>,
    pub q_knots_gev: Vec<f64>,
    pub inserted_thresholds_gev: Vec<f64>,
}

impl ArtifactGrid {
    pub fn from_context(context: &ContinuousPdfContext) -> Result<Self, PdfArtifactError> {
        let m = &context.metadata;
        let mut xs = m
            .x_knots
            .iter()
            .copied()
            .filter(|x| *x >= m.support.x_minimum && *x <= m.support.x_maximum)
            .collect::<Vec<_>>();
        xs.extend([m.support.x_minimum, m.support.x_maximum]);
        sort_unique(&mut xs);
        let mut qs = m
            .q_knots_gev
            .iter()
            .copied()
            .filter(|q| *q >= m.support.q_minimum_gev && *q <= m.support.q_maximum_gev)
            .collect::<Vec<_>>();
        qs.extend([m.support.q_minimum_gev, m.support.q_maximum_gev]);
        let mut inserted = Vec::new();
        for threshold in [
            m.charm_threshold_gev,
            m.bottom_threshold_gev,
            m.top_threshold_gev,
        ] {
            if threshold >= m.support.q_minimum_gev
                && threshold <= m.support.q_maximum_gev
                && !qs.iter().any(|q| q.to_bits() == threshold.to_bits())
            {
                qs.push(threshold);
                inserted.push(threshold);
            }
        }
        sort_unique(&mut qs);
        if xs.first().copied() != Some(m.support.x_minimum)
            || xs.last().copied() != Some(m.support.x_maximum)
            || qs.first().copied() != Some(m.support.q_minimum_gev)
            || qs.last().copied() != Some(m.support.q_maximum_gev)
        {
            return Err(PdfArtifactError::InvalidConfiguration(
                "artifact grid does not span the declared support exactly".into(),
            ));
        }
        Ok(Self {
            policy_version: ARTIFACT_GRID_POLICY_VERSION.into(),
            x_knots: xs,
            q_knots_gev: qs,
            inserted_thresholds_gev: inserted,
        })
    }
}

fn sort_unique(values: &mut Vec<f64>) {
    values.sort_by(f64::total_cmp);
    values.dedup_by(|a, b| a.to_bits() == b.to_bits());
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvolvedGrid {
    pub xs: Vec<f64>,
    pub qs_gev: Vec<f64>,
    pub flavors: Vec<i32>,
    /// Q-major, then x, then flavor.
    pub xf_values: Vec<f64>,
    pub alpha_s_values: Vec<f64>,
    /// APFEL-native `(u_v, d_v, momentum)` integrals at every Q.
    pub sum_rules: Vec<[f64; 3]>,
}

impl EvolvedGrid {
    pub fn xf(&self, flavor: i32, ix: usize, iq: usize) -> Option<f64> {
        let iflavor = self.flavors.iter().position(|id| *id == flavor)?;
        self.xf_values
            .get((iq * self.xs.len() + ix) * self.flavors.len() + iflavor)
            .copied()
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ArtifactFileChecksum {
    pub relative_path: String,
    pub sha256: String,
    pub byte_count: u64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PdfArtifactManifest {
    pub schema_version: String,
    pub artifact_hash: String,
    pub set_name: String,
    pub member: i32,
    pub parameter_identity: String,
    pub baseline_version: String,
    pub family_version: String,
    pub evolution: D1EvolutionConfig,
    pub grid: ArtifactGrid,
    pub interpolation_policy: String,
    pub extrapolator_policy: String,
    pub cache_policy_version: String,
    pub checksums: Vec<ArtifactFileChecksum>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct PdfArtifact {
    pub cache_directory: PathBuf,
    pub set_directory: PathBuf,
    pub manifest: PdfArtifactManifest,
}

extern "C" {
    fn partonsbi_apfel_evolve_grid(
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
        xs: *const f64,
        nx: usize,
        qs: *const f64,
        nq: usize,
        values: *mut f64,
        alphas: *mut f64,
        sum_rules: *mut f64,
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
}

pub fn evolve_grid(
    context: &ContinuousPdfContext,
    theta: PdfTheta,
    xs: &[f64],
    qs: &[f64],
) -> Result<EvolvedGrid, PdfArtifactError> {
    let config = D1EvolutionConfig::from_context(context)?;
    validate_requested_grid(&config, xs, qs)?;
    let point = context.construct(theta)?;
    let n = point.effective_raw_normalizations();
    let c_set = CString::new(context.metadata.set_name.as_str())
        .map_err(|_| PdfArtifactError::InvalidConfiguration("raw set contains NUL".into()))?;
    let mut values = vec![f64::NAN; xs.len() * qs.len() * D1_FLAVORS.len()];
    let mut alphas = vec![f64::NAN; qs.len()];
    let mut sum_rules_flat = vec![f64::NAN; qs.len() * 3];
    let mut error = [0 as c_char; 1024];
    // SAFETY: fixed buffers remain live, and the bridge catches C++ exceptions.
    let status = unsafe {
        partonsbi_apfel_evolve_grid(
            c_set.as_ptr(),
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
            n.sea_scale,
            n.a_u,
            n.a_d,
            n.a_g,
            xs.as_ptr(),
            xs.len(),
            qs.as_ptr(),
            qs.len(),
            values.as_mut_ptr(),
            alphas.as_mut_ptr(),
            sum_rules_flat.as_mut_ptr(),
            error.as_mut_ptr(),
            error.len(),
        )
    };
    if status != 0 {
        return Err(PdfArtifactError::Evolution(c_error(&error)));
    }
    Ok(EvolvedGrid {
        xs: xs.to_vec(),
        qs_gev: qs.to_vec(),
        flavors: D1_FLAVORS.to_vec(),
        xf_values: values,
        alpha_s_values: alphas,
        sum_rules: sum_rules_flat
            .chunks_exact(3)
            .map(|values| [values[0], values[1], values[2]])
            .collect(),
    })
}

fn validate_requested_grid(
    config: &D1EvolutionConfig,
    xs: &[f64],
    qs: &[f64],
) -> Result<(), PdfArtifactError> {
    if xs.len() < 2
        || qs.len() < 2
        || xs.first().copied() != Some(config.x_minimum)
        || xs.last().copied() != Some(config.x_maximum)
        || qs.first().copied() != Some(config.q_minimum_gev)
        || qs.last().copied() != Some(config.q_maximum_gev)
        || xs.windows(2).any(|pair| pair[0] >= pair[1])
        || qs.windows(2).any(|pair| pair[0] >= pair[1])
    {
        return Err(PdfArtifactError::InvalidConfiguration(
            "evolution grid must be strictly ordered and span exact x/Q support".into(),
        ));
    }
    Ok(())
}

pub fn default_cache_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join(".external/partonsbi/pdf-artifacts/v1/sha256")
}

pub fn build_or_load_artifact(
    context: &ContinuousPdfContext,
    theta: PdfTheta,
    cache_root: &Path,
) -> Result<PdfArtifact, PdfArtifactError> {
    let config = D1EvolutionConfig::from_context(context)?;
    let grid = ArtifactGrid::from_context(context)?;
    let point = context.construct(theta)?;
    let point_identity = point.canonical_identity()?;
    let artifact_hash = artifact_identity(&point_identity.sha256, &config, &grid)?;
    let hash = artifact_hash
        .strip_prefix("sha256:")
        .expect("internal artifact hash has prefix");
    let parent = cache_root.join(&hash[..2]);
    let cache_directory = parent.join(hash);
    fs::create_dir_all(&parent)?;
    let lock_path = parent.join(format!(".{hash}.lock"));
    let _lock = CacheLock::acquire(&lock_path, Duration::from_secs(120))?;
    if cache_directory.exists() {
        match load_and_validate(&cache_directory) {
            Ok(artifact) => return Ok(artifact),
            Err(_) => {
                let quarantine = parent.join(format!(".{hash}.corrupt.{}", std::process::id()));
                fs::rename(&cache_directory, &quarantine)?;
            }
        }
    }

    let temp = parent.join(format!(".{hash}.tmp.{}", std::process::id()));
    if temp.exists() {
        return Err(PdfArtifactError::ExistingInvalidArtifact(temp));
    }
    fs::create_dir(&temp)?;
    let set_name = format!("PartonSBI_D1_{hash}");
    let set_directory = temp.join(&set_name);
    fs::create_dir(&set_directory)?;
    let evolved = evolve_grid(context, theta, &grid.x_knots, &grid.q_knots_gev)?;
    write_lhagrid(&set_directory, &set_name, context, &config, &grid, &evolved)?;
    let checksums = checksum_artifact_files(&temp)?;
    let manifest = PdfArtifactManifest {
        schema_version: PDF_ARTIFACT_SCHEMA_VERSION.into(),
        artifact_hash,
        set_name,
        member: 0,
        parameter_identity: point_identity.sha256,
        baseline_version: PROJECTED_BASELINE_VERSION_V2.into(),
        family_version: CONTINUOUS_PDF_FAMILY_VERSION_V2.into(),
        evolution: config,
        grid,
        interpolation_policy: "logcubic".into(),
        extrapolator_policy: "error".into(),
        cache_policy_version: ARTIFACT_CACHE_POLICY_VERSION.into(),
        checksums,
    };
    let manifest_path = temp.join("artifact_manifest.json");
    write_new(&manifest_path, &serde_json::to_vec_pretty(&manifest)?)?;
    fs::rename(&temp, &cache_directory)?;
    load_and_validate(&cache_directory)
}

fn artifact_identity(
    point_identity: &str,
    config: &D1EvolutionConfig,
    grid: &ArtifactGrid,
) -> Result<String, PdfArtifactError> {
    let mut values = BTreeMap::new();
    values.insert("schema_version", PDF_ARTIFACT_SCHEMA_VERSION.to_owned());
    values.insert("parameter_identity", point_identity.to_owned());
    values.insert("baseline_version", PROJECTED_BASELINE_VERSION_V2.to_owned());
    values.insert(
        "family_version",
        CONTINUOUS_PDF_FAMILY_VERSION_V2.to_owned(),
    );
    values.insert("evolution", serde_json::to_string(config)?);
    values.insert("grid", serde_json::to_string(grid)?);
    let bytes = serde_json::to_vec(&values)?;
    Ok(format!("sha256:{:x}", Sha256::digest(bytes)))
}

fn write_lhagrid(
    directory: &Path,
    set_name: &str,
    context: &ContinuousPdfContext,
    config: &D1EvolutionConfig,
    grid: &ArtifactGrid,
    evolved: &EvolvedGrid,
) -> Result<(), PdfArtifactError> {
    let info_path = directory.join(format!("{set_name}.info"));
    let member_path = directory.join(format!("{set_name}_0000.dat"));
    let m = &context.metadata;
    let q_list = format_list(&grid.q_knots_gev);
    let alpha_list = format_list(&evolved.alpha_s_values);
    let info = format!(
        "SetDesc: 'PartonSBI D1 deterministic APFEL++ evolution artifact; not unmodified CT18NLO'\n\
Authors: PartonSBI research artifact\n\
Format: lhagrid1\nDataVersion: 1\nNumMembers: 1\nSetIndex: 0\n\
Flavors: [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 21]\n\
OrderQCD: {order}\nFlavorScheme: {scheme}\nNumFlavors: 5\nErrorType: replicas\n\
XMin: {xmin}\nXMax: {xmax}\nQMin: {qmin}\nQMax: {qmax}\n\
MZ: {mz}\nMCharm: {mc}\nMBottom: {mb}\nMTop: {mt}\n\
AlphaS_MZ: {asmz}\nAlphaS_OrderQCD: {order}\nAlphaS_Type: ipol\n\
AlphaS_Qs: [{q_list}]\nAlphaS_Vals: [{alpha_list}]\n\
Interpolator: logcubic\nExtrapolator: error\n\
PartonSBI_ArtifactSchema: {schema}\nPartonSBI_EvolutionPolicy: {policy}\n",
        order = config.perturbative_order,
        scheme = config.flavor_scheme,
        xmin = float_text(config.x_minimum),
        xmax = float_text(config.x_maximum),
        qmin = float_text(config.q_minimum_gev),
        qmax = float_text(config.q_maximum_gev),
        mz = float_text(config.mz_gev),
        mc = float_text(config.charm_mass_gev),
        mb = float_text(config.bottom_mass_gev),
        mt = float_text(config.top_mass_gev),
        asmz = float_text(config.alpha_s_mz),
        schema = PDF_ARTIFACT_SCHEMA_VERSION,
        policy = EVOLUTION_POLICY_VERSION,
    );
    write_new(&info_path, info.as_bytes())?;

    let mut member = Vec::<u8>::new();
    member.extend_from_slice(b"PdfType: central\nFormat: lhagrid1\n---\n");
    member.extend_from_slice(format!("{}\n", format_space_line(&grid.x_knots)).as_bytes());
    member.extend_from_slice(format!("{}\n", format_space_line(&grid.q_knots_gev)).as_bytes());
    member.extend_from_slice(b"-5 -4 -3 -2 -1 1 2 3 4 5 21\n");
    for ix in 0..grid.x_knots.len() {
        for iq in 0..grid.q_knots_gev.len() {
            let row = D1_FLAVORS
                .iter()
                .map(|flavor| {
                    float_text(
                        evolved
                            .xf(*flavor, ix, iq)
                            .expect("evolved grid has all declared flavors"),
                    )
                })
                .collect::<Vec<_>>()
                .join(" ");
            member.extend_from_slice(row.as_bytes());
            member.push(b'\n');
        }
    }
    member.extend_from_slice(b"---\n");
    write_new(&member_path, &member)?;

    let metadata = serde_json::json!({
        "schema_version": PDF_ARTIFACT_SCHEMA_VERSION,
        "raw_source": {
            "set": m.set_name,
            "member": m.member,
            "data_version": m.data_version,
            "lhapdf_version": m.lhapdf_version,
        },
        "projected_baseline_version": PROJECTED_BASELINE_VERSION_V2,
        "family_version": CONTINUOUS_PDF_FAMILY_VERSION_V2,
        "evolution": config,
        "grid": grid,
    });
    write_new(
        &directory.join("partonsbi_metadata.json"),
        &serde_json::to_vec_pretty(&metadata)?,
    )?;
    Ok(())
}

fn format_list(values: &[f64]) -> String {
    values
        .iter()
        .map(|value| float_text(*value))
        .collect::<Vec<_>>()
        .join(", ")
}

fn format_space_line(values: &[f64]) -> String {
    values
        .iter()
        .map(|value| float_text(*value))
        .collect::<Vec<_>>()
        .join(" ")
}

fn float_text(value: f64) -> String {
    format!("{value:.17e}")
}

fn write_new(path: &Path, bytes: &[u8]) -> Result<(), PdfArtifactError> {
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    file.write_all(bytes)?;
    file.sync_all()?;
    Ok(())
}

fn checksum_artifact_files(root: &Path) -> Result<Vec<ArtifactFileChecksum>, PdfArtifactError> {
    let mut paths = Vec::new();
    collect_files(root, root, &mut paths)?;
    paths.sort();
    paths
        .into_iter()
        .map(|relative| {
            let bytes = fs::read(root.join(&relative))?;
            Ok(ArtifactFileChecksum {
                relative_path: relative.to_string_lossy().replace('\\', "/"),
                sha256: format!("sha256:{:x}", Sha256::digest(&bytes)),
                byte_count: bytes.len() as u64,
            })
        })
        .collect()
}

fn collect_files(
    root: &Path,
    current: &Path,
    paths: &mut Vec<PathBuf>,
) -> Result<(), std::io::Error> {
    for entry in fs::read_dir(current)? {
        let entry = entry?;
        let path = entry.path();
        if path.is_dir() {
            collect_files(root, &path, paths)?;
        } else {
            paths.push(path.strip_prefix(root).expect("descendant").to_path_buf());
        }
    }
    Ok(())
}

pub fn load_and_validate(cache_directory: &Path) -> Result<PdfArtifact, PdfArtifactError> {
    let manifest_path = cache_directory.join("artifact_manifest.json");
    let manifest: PdfArtifactManifest = serde_json::from_slice(&fs::read(&manifest_path)?)?;
    if manifest.schema_version != PDF_ARTIFACT_SCHEMA_VERSION
        || manifest.baseline_version != PROJECTED_BASELINE_VERSION_V2
        || manifest.family_version != CONTINUOUS_PDF_FAMILY_VERSION_V2
        || manifest.extrapolator_policy != "error"
    {
        return Err(PdfArtifactError::ExistingInvalidArtifact(
            cache_directory.to_path_buf(),
        ));
    }
    for expected in &manifest.checksums {
        let path = cache_directory.join(&expected.relative_path);
        let bytes = fs::read(&path)?;
        let actual = format!("sha256:{:x}", Sha256::digest(&bytes));
        if actual != expected.sha256 || bytes.len() as u64 != expected.byte_count {
            return Err(PdfArtifactError::ChecksumMismatch {
                path,
                expected: expected.sha256.clone(),
                actual,
            });
        }
    }
    let set_directory = cache_directory.join(&manifest.set_name);
    Ok(PdfArtifact {
        cache_directory: cache_directory.to_path_buf(),
        set_directory,
        manifest,
    })
}

pub fn evaluate_artifact(
    artifact: &PdfArtifact,
    xs: &[f64],
    qs: &[f64],
) -> Result<EvolvedGrid, PdfArtifactError> {
    load_and_validate(&artifact.cache_directory)?;
    if xs.len() < 2 || qs.len() < 2 {
        return Err(PdfArtifactError::InvalidConfiguration(
            "artifact evaluation requires ordered two-or-more-point grids".into(),
        ));
    }
    let parent = artifact
        .set_directory
        .parent()
        .ok_or_else(|| PdfArtifactError::ArtifactLoad("artifact parent is missing".into()))?;
    let c_parent = CString::new(parent.to_string_lossy().as_bytes())
        .map_err(|_| PdfArtifactError::ArtifactLoad("artifact path contains NUL".into()))?;
    let c_set = CString::new(artifact.manifest.set_name.as_str())
        .map_err(|_| PdfArtifactError::ArtifactLoad("artifact set contains NUL".into()))?;
    let mut values = vec![f64::NAN; xs.len() * qs.len() * D1_FLAVORS.len()];
    let mut alphas = vec![f64::NAN; qs.len()];
    let mut error = [0 as c_char; 1024];
    // SAFETY: buffers remain live and the bridge catches all exceptions.
    let status = unsafe {
        partonsbi_lhapdf_artifact_evaluate(
            c_parent.as_ptr(),
            c_set.as_ptr(),
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
        return Err(PdfArtifactError::ArtifactLoad(c_error(&error)));
    }
    Ok(EvolvedGrid {
        xs: xs.to_vec(),
        qs_gev: qs.to_vec(),
        flavors: D1_FLAVORS.to_vec(),
        xf_values: values,
        alpha_s_values: alphas,
        sum_rules: Vec::new(),
    })
}

fn c_error(buffer: &[c_char]) -> String {
    // SAFETY: bridge error buffers are initialized by Rust and written by snprintf.
    unsafe { CStr::from_ptr(buffer.as_ptr()) }
        .to_string_lossy()
        .into_owned()
}

struct CacheLock {
    path: PathBuf,
    _file: File,
}

impl CacheLock {
    fn acquire(path: &Path, timeout: Duration) -> Result<Self, PdfArtifactError> {
        let start = Instant::now();
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
                    if start.elapsed() >= timeout {
                        return Err(PdfArtifactError::CacheLockTimeout(path.to_path_buf()));
                    }
                    thread::sleep(Duration::from_millis(25));
                }
                Err(error) => return Err(error.into()),
            }
        }
    }
}

impl Drop for CacheLock {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.path);
    }
}

pub fn file_sha256(path: &Path) -> Result<String, PdfArtifactError> {
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn deterministic_float_text_distinguishes_binary64_values() {
        assert_eq!(float_text(1.0), "1.00000000000000000e0");
        assert_ne!(
            float_text(1.0),
            float_text(f64::from_bits(1.0f64.to_bits() + 1))
        );
    }

    #[test]
    fn cache_path_is_repository_local_and_ignored() {
        let root = default_cache_root();
        assert!(root.starts_with(env!("CARGO_MANIFEST_DIR")));
        assert!(root.to_string_lossy().contains("/.external/"));
    }
}
