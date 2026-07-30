//! Phase 1B-D1C-A persistent APFEL transport core.
//!
//! The native context owns one accepted D0R theta point and serializes every
//! APFEL operation behind a single native mutex. This module is not a PYTHIA
//! facade, does not generate events, and does not authorize D2.

use std::collections::BTreeMap;
use std::error::Error;
use std::ffi::{c_void, CStr, CString};
use std::fmt;
use std::marker::PhantomData;
use std::os::raw::{c_char, c_int};
use std::ptr::NonNull;
use std::rc::Rc;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use super::{
    ContinuousPdfContext, ContinuousPdfFamilyVersion, D1EvolutionConfigV2, PdfTheta,
    PROJECTED_BASELINE_VERSION_V2,
};

pub const PERSISTENT_APFEL_ABI_VERSION: &str = "partonsbi_persistent_apfel_abi_v1";
pub const PERSISTENT_APFEL_POLICY_VERSION: &str = "persistent_in_process_apfel_serialized_v1";
pub const PERSISTENT_APFEL_MUTEX_POLICY_VERSION: &str = "single_native_process_mutex_v1";
pub const PERSISTENT_APFEL_CACHE_POLICY_VERSION: &str =
    "theta_scoped_exact_q_bits_last_distribution_v1";
pub const PERSISTENT_APFEL_FLAVOR_POLICY_VERSION: &str =
    "pdg_signed_xf_five_flavor_top_inactive_v1";
pub const PERSISTENT_APFEL_PREPARATION_SCHEMA: &str =
    "partonsbi.d1c.persistent-apfel.preparation.v1";
pub const D1C_PROTOTYPE_AUTHORIZED: bool = true;
pub const D1C_CONTROLLED_PYTHIA_NEXT_AUTHORIZED: bool = true;
pub const D1C_PRODUCTION_EVENTS_AUTHORIZED: bool = false;
pub const D1C_D2_AUTHORIZED: bool = false;

const STATUS_INVALID_ARGUMENT: i32 = 1;
const STATUS_INVALID_HANDLE: i32 = 2;
const STATUS_UNSUPPORTED_FLAVOR: i32 = 3;
const STATUS_INACTIVE_FLAVOR: i32 = 4;
const STATUS_OUTSIDE_SUPPORT: i32 = 5;
const STATUS_NON_FINITE: i32 = 6;
const STATUS_CACHE_FAILURE: i32 = 7;

#[derive(Debug, Clone, PartialEq)]
pub enum PersistentApfelError {
    Initialization(String),
    InvalidInput(String),
    Lifetime(String),
    UnsupportedFlavor(i32),
    InactiveFlavor(i32),
    OutsideSupport {
        x: Option<f64>,
        q_gev: Option<f64>,
    },
    NonFinite(String),
    Cache(String),
    BatchQuery {
        index: usize,
        query: PersistentApfelQuery,
        source: Box<PersistentApfelError>,
    },
    IdentityMismatch {
        expected: String,
        actual: String,
    },
    Native {
        status: i32,
        message: String,
    },
}

impl fmt::Display for PersistentApfelError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Initialization(message)
            | Self::InvalidInput(message)
            | Self::Lifetime(message)
            | Self::NonFinite(message)
            | Self::Cache(message) => formatter.write_str(message),
            Self::UnsupportedFlavor(flavor) => write!(formatter, "unsupported flavor {flavor}"),
            Self::InactiveFlavor(flavor) => write!(formatter, "inactive flavor {flavor}"),
            Self::OutsideSupport { x, q_gev } => {
                write!(
                    formatter,
                    "strict support rejected x={x:?}, Q={q_gev:?} GeV"
                )
            }
            Self::BatchQuery {
                index,
                query,
                source,
            } => write!(
                formatter,
                "persistent APFEL batch query {index} ({query:?}) was rejected: {source}"
            ),
            Self::IdentityMismatch { expected, actual } => {
                write!(
                    formatter,
                    "transport identity mismatch: expected {expected}, got {actual}"
                )
            }
            Self::Native { status, message } => {
                write!(
                    formatter,
                    "persistent APFEL native status {status}: {message}"
                )
            }
        }
    }
}

impl Error for PersistentApfelError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::BatchQuery { source, .. } => Some(source.as_ref()),
            _ => None,
        }
    }
}

/// RAII owner of the cross-language APFEL/LHAPDF process boundary.
///
/// D1C Rust code acquires this authoritative native recursive mutex before
/// provider loading or any per-instance evaluator mutex. Nested persistent C
/// ABI calls reacquire the same mutex on the same thread.
pub(crate) struct ApfelProcessGuard {
    held: bool,
    _not_send_or_sync: PhantomData<Rc<()>>,
}

impl Drop for ApfelProcessGuard {
    fn drop(&mut self) {
        if !self.held {
            return;
        }
        let mut error = [0 as c_char; 1024];
        // SAFETY: only a successful matching lock call constructs this guard.
        let status = unsafe { partonsbi_apfel_process_unlock(error.as_mut_ptr(), error.len()) };
        if status != 0 {
            // Continuing would silently invalidate the process-wide safety
            // contract, so an impossible unlock failure is fail-closed.
            std::process::abort();
        }
        self.held = false;
    }
}

pub(crate) fn lock_apfel_process() -> Result<ApfelProcessGuard, PersistentApfelError> {
    let mut error = [0 as c_char; 1024];
    // SAFETY: the bounded error buffer remains valid until native acquisition
    // returns with this thread owning the recursive process mutex.
    let status = unsafe { partonsbi_apfel_process_lock(error.as_mut_ptr(), error.len()) };
    if status != 0 {
        return Err(PersistentApfelError::Lifetime(native_message(
            &error,
            "APFEL/LHAPDF process lock failed",
        )));
    }
    Ok(ApfelProcessGuard {
        held: true,
        _not_send_or_sync: PhantomData,
    })
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct PersistentApfelQuery {
    pub flavor: i32,
    pub x: f64,
    pub q_gev: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PersistentThresholdSide {
    BelowCharm,
    AtCharm,
    BetweenCharmAndBottom,
    AtBottom,
    AboveBottom,
}

impl PersistentThresholdSide {
    fn from_native(value: i32) -> Result<Self, PersistentApfelError> {
        match value {
            -2 => Ok(Self::BelowCharm),
            -1 => Ok(Self::AtCharm),
            0 => Ok(Self::BetweenCharmAndBottom),
            1 => Ok(Self::AtBottom),
            2 => Ok(Self::AboveBottom),
            _ => Err(PersistentApfelError::Native {
                status: STATUS_INVALID_ARGUMENT,
                message: format!("native threshold side {value} is invalid"),
            }),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct PersistentApfelValue {
    pub query: PersistentApfelQuery,
    pub xf: f64,
    pub threshold_side: PersistentThresholdSide,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct PersistentApfelSupport {
    pub x_minimum: f64,
    pub x_maximum: f64,
    pub q_minimum_gev: f64,
    pub q_maximum_gev: f64,
    pub charm_threshold_gev: f64,
    pub bottom_threshold_gev: f64,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct PersistentApfelDiagnostics {
    pub scalar_calls: u64,
    pub batch_calls: u64,
    pub batch_queries: u64,
    pub alpha_s_calls: u64,
    pub cache_hits: u64,
    pub cache_misses: u64,
    pub rejected_calls: u64,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PersistentApfelIdentities {
    pub evaluator_policy_identity: String,
    pub theta_transport_identity: String,
    pub projected_boundary_identity: String,
}

extern "C" {
    fn partonsbi_apfel_process_lock(error_buffer: *mut c_char, error_buffer_size: usize) -> c_int;
    fn partonsbi_apfel_process_unlock(error_buffer: *mut c_char, error_buffer_size: usize)
        -> c_int;
    fn partonsbi_persistent_apfel_create(
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
        exported_xmax: f64,
        evaluator_policy_identity: *const c_char,
        theta_transport_identity: *const c_char,
        projected_boundary_identity: *const c_char,
        output_handle: *mut *mut c_void,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> c_int;
    fn partonsbi_persistent_apfel_destroy(
        handle: *mut c_void,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> c_int;
    fn partonsbi_persistent_apfel_evaluate_scalar(
        handle: *mut c_void,
        flavor: c_int,
        x: f64,
        q: f64,
        output_value: *mut f64,
        output_threshold_side: *mut c_int,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> c_int;
    fn partonsbi_persistent_apfel_evaluate_batch(
        handle: *mut c_void,
        flavors: *const c_int,
        xs: *const f64,
        qs: *const f64,
        count: usize,
        output_values: *mut f64,
        output_threshold_sides: *mut c_int,
        rejected_index: *mut usize,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> c_int;
    fn partonsbi_persistent_apfel_alpha_s(
        handle: *mut c_void,
        q: f64,
        output_value: *mut f64,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> c_int;
    fn partonsbi_persistent_apfel_identity(
        handle: *mut c_void,
        identity_kind: c_int,
        output: *mut c_char,
        output_size: usize,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> c_int;
    fn partonsbi_persistent_apfel_support(
        handle: *mut c_void,
        x_min: *mut f64,
        x_max: *mut f64,
        q_min: *mut f64,
        q_max: *mut f64,
        charm_threshold: *mut f64,
        bottom_threshold: *mut f64,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> c_int;
    fn partonsbi_persistent_apfel_diagnostics(
        handle: *mut c_void,
        scalar_calls: *mut u64,
        batch_calls: *mut u64,
        batch_queries: *mut u64,
        alpha_s_calls: *mut u64,
        cache_hits: *mut u64,
        cache_misses: *mut u64,
        rejected_calls: *mut u64,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> c_int;
    fn partonsbi_persistent_apfel_live_contexts() -> usize;
}

/// Safe owner of one theta-specific native APFEL evolution context.
///
/// `Send` and `Sync` are justified only by the cross-language native
/// process-wide mutex. Rust initialization takes it before LHAPDF loading and
/// projected-boundary construction; every persistent FFI operation takes the
/// same mutex. They do not assert that APFEL or LHAPDF is independently thread
/// safe.
pub struct PersistentApfelContext {
    handle: Option<NonNull<c_void>>,
    theta: PdfTheta,
    config: D1EvolutionConfigV2,
    support: PersistentApfelSupport,
    identities: PersistentApfelIdentities,
}

// SAFETY: every native operation, including destruction, takes the single
// authoritative native mutex. The pointer is an opaque non-dereferenced token.
unsafe impl Send for PersistentApfelContext {}
// SAFETY: shared Rust calls cannot enter APFEL concurrently because the native
// mutex serializes lookup, cache mutation, evaluation, and destruction.
unsafe impl Sync for PersistentApfelContext {}

impl fmt::Debug for PersistentApfelContext {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("PersistentApfelContext")
            .field("theta", &self.theta)
            .field("config", &self.config)
            .field("support", &self.support)
            .field("identities", &self.identities)
            .field("open", &self.handle.is_some())
            .finish()
    }
}

impl PersistentApfelContext {
    pub fn initialize(theta: PdfTheta) -> Result<Self, PersistentApfelError> {
        let _process = lock_apfel_process()?;
        let context = ContinuousPdfContext::load_ct18nlo_v2()
            .map_err(|error| PersistentApfelError::Initialization(error.to_string()))?;
        Self::from_context_locked(&context, theta)
    }

    pub fn from_context(
        context: &ContinuousPdfContext,
        theta: PdfTheta,
    ) -> Result<Self, PersistentApfelError> {
        let _process = lock_apfel_process()?;
        Self::from_context_locked(context, theta)
    }

    fn from_context_locked(
        context: &ContinuousPdfContext,
        theta: PdfTheta,
    ) -> Result<Self, PersistentApfelError> {
        if context.family_version() != ContinuousPdfFamilyVersion::V2 {
            return Err(PersistentApfelError::Initialization(
                "persistent APFEL requires the accepted D0R v2 family".into(),
            ));
        }
        let config = D1EvolutionConfigV2::from_context(context)
            .map_err(|error| PersistentApfelError::Initialization(error.to_string()))?;
        let point = context
            .construct(theta)
            .map_err(|error| PersistentApfelError::Initialization(error.to_string()))?;
        let parameter_identity = point
            .canonical_identity()
            .map_err(|error| PersistentApfelError::Initialization(error.to_string()))?;
        let normalizations = point.effective_raw_normalizations();
        let projected = context.projected_baseline_manifest().ok_or_else(|| {
            PersistentApfelError::Initialization(
                "persistent APFEL requires projected D0R provenance".into(),
            )
        })?;
        if projected.baseline_version != PROJECTED_BASELINE_VERSION_V2 {
            return Err(PersistentApfelError::Initialization(
                "projected baseline version does not match D0R v2".into(),
            ));
        }
        let identities = build_identities(
            context,
            theta,
            &config,
            &parameter_identity.sha256,
            &projected.canonical_identity.sha256,
        )?;
        let raw_set = CString::new(context.metadata.set_name.as_str())
            .map_err(|_| PersistentApfelError::Initialization("raw set contains NUL".into()))?;
        let evaluator_identity = CString::new(identities.evaluator_policy_identity.as_str())
            .expect("SHA-256 identity contains no NUL");
        let theta_identity = CString::new(identities.theta_transport_identity.as_str())
            .expect("SHA-256 identity contains no NUL");
        let boundary_identity = CString::new(identities.projected_boundary_identity.as_str())
            .expect("SHA-256 identity contains no NUL");
        let mut raw_handle = std::ptr::null_mut();
        let mut error = [0 as c_char; 1024];
        // SAFETY: all pointers remain valid for the call; native construction
        // publishes a non-null opaque token only after full initialization.
        let status = unsafe {
            partonsbi_persistent_apfel_create(
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
                config.computational_x_minimum,
                config.exported_x_minimum,
                config.exported_x_maximum,
                evaluator_identity.as_ptr(),
                theta_identity.as_ptr(),
                boundary_identity.as_ptr(),
                &mut raw_handle,
                error.as_mut_ptr(),
                error.len(),
            )
        };
        if status != 0 {
            return Err(native_error(status, &error, None));
        }
        let handle = NonNull::new(raw_handle).ok_or_else(|| {
            PersistentApfelError::Initialization(
                "native construction succeeded without a handle".into(),
            )
        })?;
        let mut result = Self {
            handle: Some(handle),
            theta,
            config,
            support: PersistentApfelSupport {
                x_minimum: f64::NAN,
                x_maximum: f64::NAN,
                q_minimum_gev: f64::NAN,
                q_maximum_gev: f64::NAN,
                charm_threshold_gev: f64::NAN,
                bottom_threshold_gev: f64::NAN,
            },
            identities,
        };
        let initialization_check = (|| {
            result.support = result.native_support()?;
            for (kind, expected) in [
                (0, &result.identities.evaluator_policy_identity),
                (1, &result.identities.theta_transport_identity),
                (2, &result.identities.projected_boundary_identity),
            ] {
                let actual = result.native_identity(kind)?;
                if actual != expected.as_str() {
                    return Err(PersistentApfelError::IdentityMismatch {
                        expected: (*expected).clone(),
                        actual,
                    });
                }
            }
            let expected = PersistentApfelSupport {
                x_minimum: result.config.exported_x_minimum,
                x_maximum: result.config.exported_x_maximum,
                q_minimum_gev: result.config.q_minimum_gev,
                q_maximum_gev: result.config.q_maximum_gev,
                charm_threshold_gev: result.config.charm_threshold_gev,
                bottom_threshold_gev: result.config.bottom_threshold_gev,
            };
            if support_bits(result.support) != support_bits(expected) {
                return Err(PersistentApfelError::Initialization(
                    "native support does not match the accepted configuration".into(),
                ));
            }
            Ok(())
        })();
        if let Err(error) = initialization_check {
            let _ = result.destroy_inner();
            return Err(error);
        }
        Ok(result)
    }

    pub fn theta(&self) -> PdfTheta {
        self.theta
    }

    pub fn config(&self) -> &D1EvolutionConfigV2 {
        &self.config
    }

    pub fn support(&self) -> PersistentApfelSupport {
        self.support
    }

    pub fn identities(&self) -> &PersistentApfelIdentities {
        &self.identities
    }

    pub fn ensure_transport_identity(&self, identity: &str) -> Result<(), PersistentApfelError> {
        if identity == self.identities.theta_transport_identity {
            Ok(())
        } else {
            Err(PersistentApfelError::IdentityMismatch {
                expected: self.identities.theta_transport_identity.clone(),
                actual: identity.to_owned(),
            })
        }
    }

    pub fn evaluate_scalar(
        &self,
        query: PersistentApfelQuery,
    ) -> Result<PersistentApfelValue, PersistentApfelError> {
        let handle = self.handle()?;
        let mut value = f64::NAN;
        let mut side = i32::MIN;
        let mut error = [0 as c_char; 1024];
        // SAFETY: the handle is owned by self and all output buffers are live.
        let status = unsafe {
            partonsbi_persistent_apfel_evaluate_scalar(
                handle.as_ptr(),
                query.flavor,
                query.x,
                query.q_gev,
                &mut value,
                &mut side,
                error.as_mut_ptr(),
                error.len(),
            )
        };
        if status != 0 {
            return Err(native_error(status, &error, Some(query)));
        }
        if !value.is_finite() {
            return Err(PersistentApfelError::NonFinite(
                "native scalar result is non-finite".into(),
            ));
        }
        Ok(PersistentApfelValue {
            query,
            xf: value,
            threshold_side: PersistentThresholdSide::from_native(side)?,
        })
    }

    pub fn evaluate_batch(
        &self,
        queries: &[PersistentApfelQuery],
    ) -> Result<Vec<PersistentApfelValue>, PersistentApfelError> {
        if queries.is_empty() {
            return Ok(Vec::new());
        }
        let handle = self.handle()?;
        let flavors = queries.iter().map(|query| query.flavor).collect::<Vec<_>>();
        let xs = queries.iter().map(|query| query.x).collect::<Vec<_>>();
        let qs = queries.iter().map(|query| query.q_gev).collect::<Vec<_>>();
        let mut values = vec![f64::NAN; queries.len()];
        let mut sides = vec![i32::MIN; queries.len()];
        let mut rejected_index = usize::MAX;
        let mut error = [0 as c_char; 1024];
        // SAFETY: input/output slices have exactly count elements and remain
        // live for the native call; the handle is owned by self.
        let status = unsafe {
            partonsbi_persistent_apfel_evaluate_batch(
                handle.as_ptr(),
                flavors.as_ptr(),
                xs.as_ptr(),
                qs.as_ptr(),
                queries.len(),
                values.as_mut_ptr(),
                sides.as_mut_ptr(),
                &mut rejected_index,
                error.as_mut_ptr(),
                error.len(),
            )
        };
        if status != 0 {
            let query = queries.get(rejected_index).copied();
            let source = native_error(status, &error, query);
            if let Some(query) = query {
                return Err(PersistentApfelError::BatchQuery {
                    index: rejected_index,
                    query,
                    source: Box::new(source),
                });
            }
            return Err(source);
        }
        queries
            .iter()
            .copied()
            .zip(values)
            .zip(sides)
            .map(|((query, xf), side)| {
                if !xf.is_finite() {
                    return Err(PersistentApfelError::NonFinite(
                        "native batch result is non-finite".into(),
                    ));
                }
                Ok(PersistentApfelValue {
                    query,
                    xf,
                    threshold_side: PersistentThresholdSide::from_native(side)?,
                })
            })
            .collect()
    }

    pub fn alpha_s(&self, q_gev: f64) -> Result<f64, PersistentApfelError> {
        let handle = self.handle()?;
        let mut value = f64::NAN;
        let mut error = [0 as c_char; 1024];
        // SAFETY: handle/output buffers are valid for the call.
        let status = unsafe {
            partonsbi_persistent_apfel_alpha_s(
                handle.as_ptr(),
                q_gev,
                &mut value,
                error.as_mut_ptr(),
                error.len(),
            )
        };
        if status != 0 {
            return Err(native_error(
                status,
                &error,
                Some(PersistentApfelQuery {
                    flavor: 21,
                    x: self.support.x_minimum,
                    q_gev,
                }),
            ));
        }
        Ok(value)
    }

    pub fn diagnostics(&self) -> Result<PersistentApfelDiagnostics, PersistentApfelError> {
        let handle = self.handle()?;
        let mut diagnostics = PersistentApfelDiagnostics::default();
        let mut error = [0 as c_char; 1024];
        // SAFETY: handle and all output fields are valid for the call.
        let status = unsafe {
            partonsbi_persistent_apfel_diagnostics(
                handle.as_ptr(),
                &mut diagnostics.scalar_calls,
                &mut diagnostics.batch_calls,
                &mut diagnostics.batch_queries,
                &mut diagnostics.alpha_s_calls,
                &mut diagnostics.cache_hits,
                &mut diagnostics.cache_misses,
                &mut diagnostics.rejected_calls,
                error.as_mut_ptr(),
                error.len(),
            )
        };
        if status != 0 {
            return Err(native_error(status, &error, None));
        }
        Ok(diagnostics)
    }

    pub fn close(mut self) -> Result<(), PersistentApfelError> {
        self.destroy_inner()
    }

    fn handle(&self) -> Result<NonNull<c_void>, PersistentApfelError> {
        self.handle.ok_or_else(|| {
            PersistentApfelError::Lifetime("persistent APFEL context is closed".into())
        })
    }

    fn native_identity(&self, kind: i32) -> Result<String, PersistentApfelError> {
        let handle = self.handle()?;
        let mut output = [0 as c_char; 256];
        let mut error = [0 as c_char; 1024];
        // SAFETY: handle and buffers are valid for the call.
        let status = unsafe {
            partonsbi_persistent_apfel_identity(
                handle.as_ptr(),
                kind,
                output.as_mut_ptr(),
                output.len(),
                error.as_mut_ptr(),
                error.len(),
            )
        };
        if status != 0 {
            return Err(native_error(status, &error, None));
        }
        // SAFETY: native copy always NUL-terminates on success.
        Ok(unsafe { CStr::from_ptr(output.as_ptr()) }
            .to_string_lossy()
            .into_owned())
    }

    fn native_support(&self) -> Result<PersistentApfelSupport, PersistentApfelError> {
        let handle = self.handle()?;
        let mut support = PersistentApfelSupport {
            x_minimum: f64::NAN,
            x_maximum: f64::NAN,
            q_minimum_gev: f64::NAN,
            q_maximum_gev: f64::NAN,
            charm_threshold_gev: f64::NAN,
            bottom_threshold_gev: f64::NAN,
        };
        let mut error = [0 as c_char; 1024];
        // SAFETY: handle and support output fields are valid for the call.
        let status = unsafe {
            partonsbi_persistent_apfel_support(
                handle.as_ptr(),
                &mut support.x_minimum,
                &mut support.x_maximum,
                &mut support.q_minimum_gev,
                &mut support.q_maximum_gev,
                &mut support.charm_threshold_gev,
                &mut support.bottom_threshold_gev,
                error.as_mut_ptr(),
                error.len(),
            )
        };
        if status != 0 {
            return Err(native_error(status, &error, None));
        }
        Ok(support)
    }

    fn destroy_inner(&mut self) -> Result<(), PersistentApfelError> {
        let Some(handle) = self.handle.take() else {
            return Ok(());
        };
        let mut error = [0 as c_char; 1024];
        // SAFETY: this consumes the only owned handle token. Drop cannot call
        // destroy again because handle was taken before the FFI call.
        let status = unsafe {
            partonsbi_persistent_apfel_destroy(handle.as_ptr(), error.as_mut_ptr(), error.len())
        };
        if status != 0 {
            return Err(native_error(status, &error, None));
        }
        Ok(())
    }
}

impl Drop for PersistentApfelContext {
    fn drop(&mut self) {
        let _ = self.destroy_inner();
    }
}

/// Process-safe provenance diagnostic for native RAII publication/release.
/// This value is never an observed ML feature.
pub fn persistent_apfel_live_context_count() -> usize {
    // SAFETY: native code acquires the authoritative process mutex and returns
    // only the current registry size.
    unsafe { partonsbi_persistent_apfel_live_contexts() }
}

fn build_identities(
    context: &ContinuousPdfContext,
    theta: PdfTheta,
    config: &D1EvolutionConfigV2,
    parameter_identity: &str,
    projected_boundary_identity: &str,
) -> Result<PersistentApfelIdentities, PersistentApfelError> {
    let metadata = &context.metadata;
    let mut policy = BTreeMap::<String, String>::new();
    policy.insert("abi_version".into(), PERSISTENT_APFEL_ABI_VERSION.into());
    policy.insert("alpha_s_mz_bits".into(), float_bits(config.alpha_s_mz));
    policy.insert("alpha_s_policy".into(), "apfel_alphaqcd_nlo_v1".into());
    policy.insert("apfelxx_version".into(), config.apfelxx_version.clone());
    policy.insert(
        "bottom_threshold_bits".into(),
        float_bits(config.bottom_threshold_gev),
    );
    policy.insert(
        "cache_policy".into(),
        PERSISTENT_APFEL_CACHE_POLICY_VERSION.into(),
    );
    policy.insert(
        "charm_threshold_bits".into(),
        float_bits(config.charm_threshold_gev),
    );
    policy.insert(
        "computational_xmin_bits".into(),
        float_bits(config.computational_x_minimum),
    );
    policy.insert("evolution_policy".into(), config.policy_version.clone());
    policy.insert(
        "exported_xmax_bits".into(),
        float_bits(config.exported_x_maximum),
    );
    policy.insert(
        "exported_xmin_bits".into(),
        float_bits(config.exported_x_minimum),
    );
    policy.insert(
        "flavor_policy".into(),
        PERSISTENT_APFEL_FLAVOR_POLICY_VERSION.into(),
    );
    policy.insert("flavor_scheme".into(), config.flavor_scheme.clone());
    policy.insert("grid_policy".into(), canonical_grid_policy(config));
    policy.insert("lhapdf_version".into(), metadata.lhapdf_version.clone());
    policy.insert(
        "mutex_policy".into(),
        PERSISTENT_APFEL_MUTEX_POLICY_VERSION.into(),
    );
    policy.insert("order_qcd".into(), config.perturbative_order.to_string());
    policy.insert(
        "policy_version".into(),
        PERSISTENT_APFEL_POLICY_VERSION.into(),
    );
    policy.insert("qmax_bits".into(), float_bits(config.q_maximum_gev));
    policy.insert("qmin_bits".into(), float_bits(config.q_minimum_gev));
    policy.insert(
        "top_policy".into(),
        "inactive_above_exported_qmax_v1".into(),
    );
    let evaluator_policy_identity = hash_canonical_map(&policy)?;

    let mut transport = BTreeMap::<String, String>::new();
    transport.insert("delta_v_bits".into(), float_bits(theta.delta_v));
    transport.insert(
        "evaluator_policy_identity".into(),
        evaluator_policy_identity.clone(),
    );
    transport.insert("lambda_sea_bits".into(), float_bits(theta.lambda_sea));
    transport.insert("parameter_point_identity".into(), parameter_identity.into());
    transport.insert(
        "projected_boundary_identity".into(),
        projected_boundary_identity.into(),
    );
    transport.insert(
        "transport_schema".into(),
        "theta_transport_identity_v1".into(),
    );
    let theta_transport_identity = hash_canonical_map(&transport)?;
    Ok(PersistentApfelIdentities {
        evaluator_policy_identity,
        theta_transport_identity,
        projected_boundary_identity: projected_boundary_identity.into(),
    })
}

fn canonical_grid_policy(config: &D1EvolutionConfigV2) -> String {
    config
        .base_grid
        .subgrids
        .iter()
        .map(|(nodes, xmin, degree)| format!("{nodes}:{}:{degree}", float_bits(*xmin)))
        .collect::<Vec<_>>()
        .join("|")
}

fn hash_canonical_map(values: &BTreeMap<String, String>) -> Result<String, PersistentApfelError> {
    let bytes = serde_json::to_vec(values)
        .map_err(|error| PersistentApfelError::Initialization(error.to_string()))?;
    Ok(format!("sha256:{:x}", Sha256::digest(bytes)))
}

fn float_bits(value: f64) -> String {
    format!("{:016x}", value.to_bits())
}

fn support_bits(support: PersistentApfelSupport) -> [u64; 6] {
    [
        support.x_minimum.to_bits(),
        support.x_maximum.to_bits(),
        support.q_minimum_gev.to_bits(),
        support.q_maximum_gev.to_bits(),
        support.charm_threshold_gev.to_bits(),
        support.bottom_threshold_gev.to_bits(),
    ]
}

fn native_error(
    status: i32,
    buffer: &[c_char],
    query: Option<PersistentApfelQuery>,
) -> PersistentApfelError {
    // SAFETY: every native failure path writes a bounded NUL-terminated string.
    let message = unsafe { CStr::from_ptr(buffer.as_ptr()) }
        .to_string_lossy()
        .into_owned();
    match status {
        STATUS_INVALID_ARGUMENT => PersistentApfelError::InvalidInput(message),
        STATUS_INVALID_HANDLE => PersistentApfelError::Lifetime(message),
        STATUS_UNSUPPORTED_FLAVOR => {
            PersistentApfelError::UnsupportedFlavor(query.map_or(0, |value| value.flavor))
        }
        STATUS_INACTIVE_FLAVOR => {
            PersistentApfelError::InactiveFlavor(query.map_or(6, |value| value.flavor))
        }
        STATUS_OUTSIDE_SUPPORT => PersistentApfelError::OutsideSupport {
            x: query.map(|value| value.x),
            q_gev: query.map(|value| value.q_gev),
        },
        STATUS_NON_FINITE => PersistentApfelError::NonFinite(message),
        STATUS_CACHE_FAILURE => PersistentApfelError::Cache(message),
        _ => PersistentApfelError::Native { status, message },
    }
}

fn native_message(buffer: &[c_char], fallback: &str) -> String {
    // The buffer is zero-initialized, hence remains a valid empty C string even
    // if native lock acquisition cannot report a more specific message.
    let message = unsafe { CStr::from_ptr(buffer.as_ptr()) }
        .to_string_lossy()
        .into_owned();
    if message.is_empty() {
        fallback.to_owned()
    } else {
        message
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn center() -> PersistentApfelContext {
        PersistentApfelContext::initialize(PdfTheta::new(0.0, 0.0).unwrap()).unwrap()
    }

    #[test]
    fn persistent_apfel_identity_and_cache_are_theta_scoped() {
        let context = center();
        let query = PersistentApfelQuery {
            flavor: 21,
            x: 0.01,
            q_gev: 10.0,
        };
        let before = context.diagnostics().unwrap();
        let first = context.evaluate_scalar(query).unwrap();
        let middle = context.diagnostics().unwrap();
        let second = context.evaluate_scalar(query).unwrap();
        let after = context.diagnostics().unwrap();
        assert_eq!(first.xf.to_bits(), second.xf.to_bits());
        assert_eq!(middle.cache_misses, before.cache_misses + 1);
        assert_eq!(after.cache_hits, middle.cache_hits + 1);
        assert!(context
            .ensure_transport_identity(&context.identities().theta_transport_identity)
            .is_ok());
        assert!(matches!(
            context.ensure_transport_identity("sha256:wrong"),
            Err(PersistentApfelError::IdentityMismatch { .. })
        ));
    }

    #[test]
    fn persistent_apfel_strict_support_and_flavors_are_typed() {
        let context = center();
        let support = context.support();
        let query = |flavor, x, q_gev| PersistentApfelQuery { flavor, x, q_gev };
        assert!(matches!(
            context.evaluate_scalar(query(21, support.x_minimum / 2.0, 10.0)),
            Err(PersistentApfelError::OutsideSupport { .. })
        ));
        assert!(matches!(
            context.evaluate_scalar(query(6, 0.01, 10.0)),
            Err(PersistentApfelError::InactiveFlavor(6))
        ));
        assert!(matches!(
            context.evaluate_scalar(query(22, 0.01, 10.0)),
            Err(PersistentApfelError::UnsupportedFlavor(22))
        ));
    }

    #[test]
    fn persistent_apfel_native_handle_rejects_use_after_destroy() {
        let mut context = center();
        let handle = context.handle.take().unwrap();
        let mut error = [0 as c_char; 1024];
        assert_eq!(
            unsafe {
                partonsbi_persistent_apfel_destroy(handle.as_ptr(), error.as_mut_ptr(), error.len())
            },
            0
        );
        let mut value = f64::NAN;
        let mut side = 0;
        assert_eq!(
            unsafe {
                partonsbi_persistent_apfel_evaluate_scalar(
                    handle.as_ptr(),
                    21,
                    0.01,
                    10.0,
                    &mut value,
                    &mut side,
                    error.as_mut_ptr(),
                    error.len(),
                )
            },
            STATUS_INVALID_HANDLE
        );
        assert_eq!(
            unsafe {
                partonsbi_persistent_apfel_destroy(handle.as_ptr(), error.as_mut_ptr(), error.len())
            },
            STATUS_INVALID_HANDLE
        );
        assert_eq!(
            unsafe {
                partonsbi_persistent_apfel_destroy(
                    std::ptr::null_mut(),
                    error.as_mut_ptr(),
                    error.len(),
                )
            },
            STATUS_INVALID_HANDLE
        );
    }

    #[test]
    fn persistent_apfel_failed_initialization_never_returns_a_handle() {
        let _process = lock_apfel_process().unwrap();
        let context = ContinuousPdfContext::load_ct18nlo_v1().unwrap();
        let theta = PdfTheta::new(0.0, 0.0).unwrap();
        assert!(matches!(
            PersistentApfelContext::from_context(&context, theta),
            Err(PersistentApfelError::Initialization(_))
        ));
    }

    #[test]
    fn persistent_apfel_raii_and_explicit_close_publish_and_release_once() {
        let _process = lock_apfel_process().unwrap();
        let before = persistent_apfel_live_context_count();
        {
            let _context = center();
            assert_eq!(persistent_apfel_live_context_count(), before + 1);
        }
        assert_eq!(persistent_apfel_live_context_count(), before);

        let context = center();
        assert_eq!(persistent_apfel_live_context_count(), before + 1);
        context.close().unwrap();
        // close consumes the wrapper; its subsequent Drop observes an empty
        // handle and cannot destroy the native context twice.
        assert_eq!(persistent_apfel_live_context_count(), before);
    }

    #[test]
    fn persistent_apfel_failed_native_construction_is_never_published() {
        let _process = lock_apfel_process().unwrap();
        let before = persistent_apfel_live_context_count();
        let mut handle = usize::MAX as *mut c_void;
        let mut error = [0 as c_char; 1024];
        let status = unsafe {
            partonsbi_persistent_apfel_create(
                std::ptr::null(),
                0,
                1.0,
                1.0,
                1.0,
                2.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
                3.0,
                1,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0e-11,
                1.0e-9,
                1.0,
                std::ptr::null(),
                std::ptr::null(),
                std::ptr::null(),
                &mut handle,
                error.as_mut_ptr(),
                error.len(),
            )
        };
        assert_ne!(status, 0);
        assert!(handle.is_null());
        assert_eq!(persistent_apfel_live_context_count(), before);
    }

    #[test]
    fn persistent_apfel_rejected_query_count_and_batch_index_are_deterministic() {
        let context = center();
        let support = context.support();
        let valid = PersistentApfelQuery {
            flavor: 21,
            x: 0.01,
            q_gev: 10.0,
        };
        let rejected = PersistentApfelQuery {
            flavor: 21,
            x: support.x_minimum / 2.0,
            q_gev: 10.0,
        };
        let before = context.diagnostics().unwrap();
        context.evaluate_scalar(valid).unwrap();
        let successful = context.diagnostics().unwrap();
        assert_eq!(successful.rejected_calls, before.rejected_calls);

        assert!(matches!(
            context.evaluate_scalar(rejected),
            Err(PersistentApfelError::OutsideSupport { .. })
        ));
        let after_scalar = context.diagnostics().unwrap();
        assert_eq!(after_scalar.rejected_calls, before.rejected_calls + 1);

        let error = context
            .evaluate_batch(&[valid, rejected, valid])
            .unwrap_err();
        assert!(matches!(
            error,
            PersistentApfelError::BatchQuery {
                index: 1,
                query,
                source,
            } if query == rejected
                && matches!(*source, PersistentApfelError::OutsideSupport { .. })
        ));
        let after_batch = context.diagnostics().unwrap();
        // A failed batch counts once, at its first rejected query, and does not
        // increment successful batch-call/query counters.
        assert_eq!(after_batch.rejected_calls, before.rejected_calls + 2);
        assert_eq!(after_batch.batch_calls, after_scalar.batch_calls);
        assert_eq!(after_batch.batch_queries, after_scalar.batch_queries);

        let handle = context.handle().unwrap();
        let mut scalar_calls = 0;
        let mut error_buffer = [0 as c_char; 1024];
        let status = unsafe {
            partonsbi_persistent_apfel_diagnostics(
                handle.as_ptr(),
                &mut scalar_calls,
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                std::ptr::null_mut(),
                error_buffer.as_mut_ptr(),
                error_buffer.len(),
            )
        };
        assert_eq!(status, STATUS_INVALID_ARGUMENT);
        assert_eq!(
            context.diagnostics().unwrap().rejected_calls,
            after_batch.rejected_calls
        );
    }
}
