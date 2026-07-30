//! Bounded Phase 1B-D1A comparison prototype.
//!
//! This module is not a PYTHIA adapter and never generates events. It compares
//! a serialized direct-APFEL reference with a repository-owned deterministic
//! interpolator under the fixed limits accepted in ADR-006.

use std::collections::BTreeSet;
use std::error::Error;
use std::fmt;
use std::fs;
use std::path::Path;
use std::sync::Mutex;
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use super::{
    evolve_grid_values_v2, ComputationalGridKind, ContinuousPdfContext, D1EvolutionConfigV2,
    EvolvedGridV2, PdfTheta, D1_FLAVORS,
};

pub const DIRECT_APFEL_PROTOTYPE_VERSION: &str = "direct_apfel_transport_prototype_v1";
pub const CUSTOM_INTERPOLATOR_PROTOTYPE_VERSION: &str =
    "threshold_piecewise_logx_logq_bilinear_prototype_v1";
pub const QUERY_ENVELOPE_POLICY_VERSION: &str = "pythia_8.312_static_query_envelope_v1";
pub const PROTOTYPE_STUDY_POLICY_VERSION: &str = "d1a_three_anchor_bounded_study_v1";
pub const MAX_STUDY_RUNTIME: Duration = Duration::from_secs(30 * 60);
pub const MAX_STUDY_BYTES: u64 = 2 * 1024 * 1024 * 1024;
pub const PROTOTYPE_RELATIVE_TOLERANCE: f64 = 1.0e-5;
pub const PROTOTYPE_ABSOLUTE_TOLERANCE: f64 = 1.0e-9;
pub const MINIMUM_PROTOTYPE_CALLS_PER_SECOND: f64 = 1_000.0;
pub const D2_AUTHORIZED: bool = false;

#[derive(Debug)]
pub enum TransportPrototypeError {
    Initialization(String),
    Lifetime(String),
    Support { x: f64, q_gev: f64 },
    InvalidGrid(String),
    UnsupportedFlavor(i32),
    Budget(String),
    Evolution(String),
    Io(std::io::Error),
}

impl fmt::Display for TransportPrototypeError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Initialization(message)
            | Self::Lifetime(message)
            | Self::InvalidGrid(message)
            | Self::Budget(message)
            | Self::Evolution(message) => formatter.write_str(message),
            Self::Support { x, q_gev } => {
                write!(formatter, "strict support rejected x={x}, Q={q_gev} GeV")
            }
            Self::UnsupportedFlavor(flavor) => write!(formatter, "unsupported flavor {flavor}"),
            Self::Io(error) => write!(formatter, "{error}"),
        }
    }
}

impl Error for TransportPrototypeError {}

impl From<std::io::Error> for TransportPrototypeError {
    fn from(value: std::io::Error) -> Self {
        Self::Io(value)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct TransportQuery {
    pub flavor: i32,
    pub x: f64,
    pub q_gev: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ThresholdSide {
    BelowCharm,
    AtCharm,
    BetweenCharmAndBottom,
    AtBottom,
    AboveBottom,
}

fn threshold_side(q: f64, charm: f64, bottom: f64) -> ThresholdSide {
    if q.to_bits() == charm.to_bits() {
        ThresholdSide::AtCharm
    } else if q.to_bits() == bottom.to_bits() {
        ThresholdSide::AtBottom
    } else if q < charm {
        ThresholdSide::BelowCharm
    } else if q < bottom {
        ThresholdSide::BetweenCharmAndBottom
    } else {
        ThresholdSide::AboveBottom
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TransportValue {
    pub query: TransportQuery,
    pub xf: f64,
    pub threshold_side: ThresholdSide,
}

/// Immutable APFEL configuration with explicitly serialized access.
///
/// APFEL++ reentrancy has not been established for this repository. The
/// context therefore remains behind a mutex and every native call is made
/// while holding the lock. Poisoning is reported as a typed lifetime error.
#[derive(Debug)]
pub struct DirectApfelEvaluator {
    context: Mutex<ContinuousPdfContext>,
    config: D1EvolutionConfigV2,
    identity: String,
}

impl DirectApfelEvaluator {
    pub fn initialize() -> Result<Self, TransportPrototypeError> {
        let context = ContinuousPdfContext::load_ct18nlo_v2()
            .map_err(|error| TransportPrototypeError::Initialization(error.to_string()))?;
        Self::from_context(context)
    }

    pub fn from_context(context: ContinuousPdfContext) -> Result<Self, TransportPrototypeError> {
        let config = D1EvolutionConfigV2::from_context(&context)
            .map_err(|error| TransportPrototypeError::Initialization(error.to_string()))?;
        let identity = hash_words(&[
            DIRECT_APFEL_PROTOTYPE_VERSION.as_bytes(),
            config.policy_version.as_bytes(),
            &config.q0_gev.to_bits().to_be_bytes(),
            &config.exported_x_minimum.to_bits().to_be_bytes(),
            &config.q_maximum_gev.to_bits().to_be_bytes(),
        ]);
        Ok(Self {
            context: Mutex::new(context),
            config,
            identity,
        })
    }

    pub fn identity(&self) -> &str {
        &self.identity
    }

    pub fn config(&self) -> &D1EvolutionConfigV2 {
        &self.config
    }

    pub fn evaluate_batch(
        &self,
        theta: PdfTheta,
        queries: &[TransportQuery],
    ) -> Result<Vec<TransportValue>, TransportPrototypeError> {
        validate_queries(
            queries,
            self.config.exported_x_minimum,
            self.config.exported_x_maximum,
            self.config.q_minimum_gev,
            self.config.q_maximum_gev,
        )?;
        let (xs, qs) = padded_evaluation_axes(
            queries,
            self.config.exported_x_minimum,
            self.config.exported_x_maximum,
            self.config.q_minimum_gev,
            self.config.q_maximum_gev,
        );
        let context = self.context.lock().map_err(|_| {
            TransportPrototypeError::Lifetime("direct APFEL context lock was poisoned".into())
        })?;
        let grid = evolve_grid_values_v2(&context, theta, &xs, &qs, ComputationalGridKind::Base)
            .map_err(|error| TransportPrototypeError::Evolution(error.to_string()))?;
        queries
            .iter()
            .map(|query| value_from_grid(&grid, *query, &self.config))
            .collect()
    }
}

fn padded_evaluation_axes(
    queries: &[TransportQuery],
    x_minimum: f64,
    x_maximum: f64,
    q_minimum_gev: f64,
    q_maximum_gev: f64,
) -> (Vec<f64>, Vec<f64>) {
    let mut xs = queries.iter().map(|query| query.x).collect::<Vec<_>>();
    xs.push(x_maximum);
    sort_dedup(&mut xs);
    if xs.len() < 2 {
        xs.push(x_minimum);
        sort_dedup(&mut xs);
    }

    let mut qs = queries.iter().map(|query| query.q_gev).collect::<Vec<_>>();
    qs.push(q_minimum_gev);
    sort_dedup(&mut qs);
    if qs.len() < 2 {
        qs.push(q_maximum_gev);
        sort_dedup(&mut qs);
    }

    debug_assert!(xs.len() >= 2 && qs.len() >= 2);
    debug_assert!(xs[0] >= x_minimum && xs.last().copied() == Some(x_maximum));
    debug_assert!(qs[0].to_bits() == q_minimum_gev.to_bits());
    debug_assert!(qs.last().is_some_and(|q| *q <= q_maximum_gev));
    (xs, qs)
}

fn value_from_grid(
    grid: &EvolvedGridV2,
    query: TransportQuery,
    config: &D1EvolutionConfigV2,
) -> Result<TransportValue, TransportPrototypeError> {
    let ix = grid
        .xs
        .iter()
        .position(|value| value.to_bits() == query.x.to_bits())
        .ok_or_else(|| TransportPrototypeError::Evolution("direct x result is missing".into()))?;
    let iq = grid
        .qs_gev
        .iter()
        .position(|value| value.to_bits() == query.q_gev.to_bits())
        .ok_or_else(|| TransportPrototypeError::Evolution("direct Q result is missing".into()))?;
    let xf = grid
        .xf(query.flavor, ix, iq)
        .ok_or(TransportPrototypeError::UnsupportedFlavor(query.flavor))?;
    if !xf.is_finite() {
        return Err(TransportPrototypeError::Evolution(
            "direct APFEL returned a non-finite value".into(),
        ));
    }
    Ok(TransportValue {
        query,
        xf,
        threshold_side: threshold_side(
            query.q_gev,
            config.charm_threshold_gev,
            config.bottom_threshold_gev,
        ),
    })
}

/// Repository-owned immutable transport representation.
///
/// The predeclared interpolation policy is bilinear interpolation in
/// `(ln(x), ln(Q))`. Every heavy-flavor threshold must be an exact Q knot and
/// interpolation is forbidden from crossing one. At an exact threshold the
/// stored knot is returned; one-sided intervals are used immediately below
/// and above. This is intentionally independent of LHAPDF log-bicubic code.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct DeterministicTransportGrid {
    pub version: String,
    pub x_knots: Vec<f64>,
    pub q_knots_gev: Vec<f64>,
    pub thresholds_gev: Vec<f64>,
    pub flavors: Vec<i32>,
    pub xf_values: Vec<f64>,
    pub identity: String,
}

impl DeterministicTransportGrid {
    pub fn new(
        x_knots: Vec<f64>,
        q_knots_gev: Vec<f64>,
        thresholds_gev: Vec<f64>,
        flavors: Vec<i32>,
        xf_values: Vec<f64>,
    ) -> Result<Self, TransportPrototypeError> {
        validate_knots(&x_knots, "x")?;
        validate_knots(&q_knots_gev, "Q")?;
        if flavors.is_empty()
            || xf_values.len() != x_knots.len() * q_knots_gev.len() * flavors.len()
            || xf_values.iter().any(|value| !value.is_finite())
        {
            return Err(TransportPrototypeError::InvalidGrid(
                "custom grid shape or values are invalid".into(),
            ));
        }
        for threshold in &thresholds_gev {
            if !q_knots_gev
                .iter()
                .any(|q| q.to_bits() == threshold.to_bits())
            {
                return Err(TransportPrototypeError::InvalidGrid(format!(
                    "threshold {threshold} GeV is not an exact Q knot"
                )));
            }
        }
        let identity = custom_grid_identity(
            &x_knots,
            &q_knots_gev,
            &thresholds_gev,
            &flavors,
            &xf_values,
        );
        Ok(Self {
            version: CUSTOM_INTERPOLATOR_PROTOTYPE_VERSION.into(),
            x_knots,
            q_knots_gev,
            thresholds_gev,
            flavors,
            xf_values,
            identity,
        })
    }

    pub fn from_evolved(
        grid: EvolvedGridV2,
        thresholds_gev: Vec<f64>,
    ) -> Result<Self, TransportPrototypeError> {
        Self::new(
            grid.xs,
            grid.qs_gev,
            thresholds_gev,
            grid.flavors,
            grid.xf_values,
        )
    }

    pub fn evaluate(
        &self,
        query: TransportQuery,
    ) -> Result<TransportValue, TransportPrototypeError> {
        validate_queries(
            std::slice::from_ref(&query),
            self.x_knots[0],
            *self.x_knots.last().expect("validated nonempty x knots"),
            self.q_knots_gev[0],
            *self.q_knots_gev.last().expect("validated nonempty Q knots"),
        )?;
        let flavor_index = self
            .flavors
            .iter()
            .position(|flavor| *flavor == query.flavor)
            .ok_or(TransportPrototypeError::UnsupportedFlavor(query.flavor))?;
        let ix = lower_bracket(&self.x_knots, query.x);
        let iq = lower_bracket(&self.q_knots_gev, query.q_gev);
        if self.thresholds_gev.iter().any(|threshold| {
            self.q_knots_gev[iq] < *threshold && self.q_knots_gev[iq + 1] > *threshold
        }) {
            return Err(TransportPrototypeError::InvalidGrid(
                "interpolation interval crosses a heavy-flavor threshold".into(),
            ));
        }
        let tx = log_fraction(self.x_knots[ix], self.x_knots[ix + 1], query.x);
        let tq = log_fraction(self.q_knots_gev[iq], self.q_knots_gev[iq + 1], query.q_gev);
        let value = |x_index: usize, q_index: usize| {
            self.xf_values
                [(q_index * self.x_knots.len() + x_index) * self.flavors.len() + flavor_index]
        };
        let lower = value(ix, iq) * (1.0 - tx) + value(ix + 1, iq) * tx;
        let upper = value(ix, iq + 1) * (1.0 - tx) + value(ix + 1, iq + 1) * tx;
        let xf = lower * (1.0 - tq) + upper * tq;
        let charm = self
            .thresholds_gev
            .first()
            .copied()
            .unwrap_or(f64::INFINITY);
        let bottom = self.thresholds_gev.get(1).copied().unwrap_or(f64::INFINITY);
        Ok(TransportValue {
            query,
            xf,
            threshold_side: threshold_side(query.q_gev, charm, bottom),
        })
    }
}

fn lower_bracket(knots: &[f64], value: f64) -> usize {
    match knots.binary_search_by(|probe| probe.total_cmp(&value)) {
        Ok(index) if index + 1 < knots.len() => index,
        Ok(index) => index - 1,
        Err(index) => index - 1,
    }
}

fn log_fraction(low: f64, high: f64, value: f64) -> f64 {
    (value.ln() - low.ln()) / (high.ln() - low.ln())
}

fn validate_knots(knots: &[f64], name: &str) -> Result<(), TransportPrototypeError> {
    if knots.len() < 2
        || knots
            .iter()
            .any(|value| !value.is_finite() || *value <= 0.0)
        || knots.windows(2).any(|pair| pair[0] >= pair[1])
    {
        return Err(TransportPrototypeError::InvalidGrid(format!(
            "{name} knots must be finite, positive, and strictly increasing"
        )));
    }
    Ok(())
}

fn validate_queries(
    queries: &[TransportQuery],
    xmin: f64,
    xmax: f64,
    qmin: f64,
    qmax: f64,
) -> Result<(), TransportPrototypeError> {
    if queries.is_empty() {
        return Err(TransportPrototypeError::InvalidGrid(
            "at least one transport query is required".into(),
        ));
    }
    for query in queries {
        if !D1_FLAVORS.contains(&query.flavor) {
            return Err(TransportPrototypeError::UnsupportedFlavor(query.flavor));
        }
        if !query.x.is_finite()
            || !query.q_gev.is_finite()
            || query.x < xmin
            || query.x > xmax
            || query.q_gev < qmin
            || query.q_gev > qmax
        {
            return Err(TransportPrototypeError::Support {
                x: query.x,
                q_gev: query.q_gev,
            });
        }
    }
    Ok(())
}

fn sort_dedup(values: &mut Vec<f64>) {
    values.sort_by(f64::total_cmp);
    values.dedup_by(|left, right| left.to_bits() == right.to_bits());
}

fn custom_grid_identity(
    xs: &[f64],
    qs: &[f64],
    thresholds: &[f64],
    flavors: &[i32],
    values: &[f64],
) -> String {
    let mut hasher = Sha256::new();
    hasher.update(CUSTOM_INTERPOLATOR_PROTOTYPE_VERSION.as_bytes());
    for collection in [xs, qs, thresholds, values] {
        hasher.update((collection.len() as u64).to_be_bytes());
        for value in collection {
            hasher.update(value.to_bits().to_be_bytes());
        }
    }
    for flavor in flavors {
        hasher.update(flavor.to_be_bytes());
    }
    format!("sha256:{:x}", hasher.finalize())
}

fn hash_words(words: &[&[u8]]) -> String {
    let mut hasher = Sha256::new();
    for word in words {
        hasher.update((word.len() as u64).to_be_bytes());
        hasher.update(word);
    }
    format!("sha256:{:x}", hasher.finalize())
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PrototypeAnchor {
    pub name: String,
    pub theta: PdfTheta,
}

pub fn prototype_anchors() -> Result<Vec<PrototypeAnchor>, TransportPrototypeError> {
    let anchor = |name: &str, delta_v, lambda_sea| {
        PdfTheta::new(delta_v, lambda_sea)
            .map(|theta| PrototypeAnchor {
                name: name.into(),
                theta,
            })
            .map_err(|error| TransportPrototypeError::Initialization(error.to_string()))
    };
    Ok(vec![
        anchor("center", 0.0, 0.0)?,
        anchor("delta_min", -0.20, 0.0)?,
        anchor("corner_min_max", -0.20, 0.25)?,
    ])
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum QueryConsumerStatus {
    ActiveConfigured,
    DisabledConfigured,
    UnresolvedWithoutInstrumentation,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProspectivePdfConsumer {
    pub class: String,
    pub call_path: String,
    pub status: QueryConsumerStatus,
    pub evidence: String,
}

pub fn prospective_pythia_consumers() -> Vec<ProspectivePdfConsumer> {
    vec![
        ProspectivePdfConsumer {
            class: "hard_process".into(),
            call_path: "Pythia::setPDFPtr -> BeamSetup -> PDF::xf -> PDF::xfUpdate".into(),
            status: QueryConsumerStatus::ActiveConfigured,
            evidence: "Pythia8/Pythia.h and Pythia8/PartonDistributions.h".into(),
        },
        ProspectivePdfConsumer {
            class: "initial_state_shower".into(),
            call_path: "SpaceShower -> BeamParticle PDF queries".into(),
            status: QueryConsumerStatus::UnresolvedWithoutInstrumentation,
            evidence: "prospective ISR consumer; exact envelope is not exposed by PDF::xf".into(),
        },
        ProspectivePdfConsumer {
            class: "multi_parton_interactions".into(),
            call_path: "MultipartonInteractions -> BeamParticle PDF queries".into(),
            status: QueryConsumerStatus::DisabledConfigured,
            evidence: "MPI is disabled by the accepted DIS configuration".into(),
        },
        ProspectivePdfConsumer {
            class: "beam_remnants".into(),
            call_path: "BeamRemnants -> BeamParticle flavor/companion PDF queries".into(),
            status: QueryConsumerStatus::UnresolvedWithoutInstrumentation,
            evidence: "hadronization remains enabled; query reach requires instrumentation".into(),
        },
        ProspectivePdfConsumer {
            class: "hard_diffraction_and_photon_flux".into(),
            call_path: "optional PDF virtual methods on PDF".into(),
            status: QueryConsumerStatus::DisabledConfigured,
            evidence: "not enabled by neutral-current process 211 configuration".into(),
        },
    ]
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HardProcessQueryEnvelope {
    pub policy_version: String,
    pub electron_energy_gev: f64,
    pub proton_energy_gev: f64,
    pub s_gev2: f64,
    pub x_minimum: f64,
    pub x_maximum: f64,
    pub q2_minimum_gev2: f64,
    pub q2_maximum_gev2: f64,
    pub y_minimum: f64,
    pub y_maximum: f64,
    pub scale_convention: String,
    pub strict_support: bool,
    pub consumers: Vec<ProspectivePdfConsumer>,
}

impl HardProcessQueryEnvelope {
    pub fn hera_dis() -> Self {
        let electron_energy_gev = 27.5;
        let proton_energy_gev = 920.0;
        Self {
            policy_version: QUERY_ENVELOPE_POLICY_VERSION.into(),
            electron_energy_gev,
            proton_energy_gev,
            s_gev2: 4.0 * electron_energy_gev * proton_energy_gev,
            x_minimum: 1.0e-4,
            x_maximum: 0.8,
            q2_minimum_gev2: 3.5,
            q2_maximum_gev2: 10_000.0,
            y_minimum: 0.01,
            y_maximum: 0.95,
            scale_convention: "hard_Q=sqrt(Q2); all other PYTHIA consumers unresolved".into(),
            strict_support: true,
            consumers: prospective_pythia_consumers(),
        }
    }

    pub fn contains_hard_query(&self, x: f64, q_gev: f64) -> bool {
        if !x.is_finite() || !q_gev.is_finite() || q_gev <= 0.0 {
            return false;
        }
        let q2 = q_gev * q_gev;
        let y = q2 / (x * self.s_gev2);
        x >= self.x_minimum
            && x <= self.x_maximum
            && q2 >= self.q2_minimum_gev2
            && q2 <= self.q2_maximum_gev2
            && y >= self.y_minimum
            && y <= self.y_maximum
    }

    pub fn synthetic_queries(&self) -> Vec<(f64, f64)> {
        let mut points = BTreeSet::new();
        for x in [self.x_minimum, 0.01, self.x_maximum] {
            for y in [self.y_minimum, 0.5, self.y_maximum] {
                let q2 = x * y * self.s_gev2;
                let q = q2.sqrt();
                if self.contains_hard_query(x, q) {
                    points.insert((x.to_bits(), q.to_bits()));
                }
            }
        }
        points
            .into_iter()
            .map(|(x, q)| (f64::from_bits(x), f64::from_bits(q)))
            .collect()
    }

    pub fn unresolved_consumers(&self) -> Vec<String> {
        self.consumers
            .iter()
            .filter(|consumer| {
                consumer.status == QueryConsumerStatus::UnresolvedWithoutInstrumentation
            })
            .map(|consumer| consumer.class.clone())
            .collect()
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PrototypeDecision {
    DirectApfelSelected,
    CustomInterpolatorSelected,
    Inconclusive,
    Rejected,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PrototypeSelectionEvidence {
    pub direct_accuracy_pass: bool,
    pub custom_accuracy_pass: bool,
    pub deterministic_identity_pass: bool,
    pub strict_support_pass: bool,
    pub threshold_behavior_pass: bool,
    pub thread_safety_pass: bool,
    pub process_isolation_pass: bool,
    pub cache_reload_pass: bool,
    pub all_consumer_envelope_complete: bool,
    pub direct_calls_per_second: f64,
    pub custom_calls_per_second: f64,
}

impl PrototypeSelectionEvidence {
    pub fn decision(&self) -> PrototypeDecision {
        let common = self.deterministic_identity_pass
            && self.strict_support_pass
            && self.threshold_behavior_pass
            && self.thread_safety_pass
            && self.process_isolation_pass
            && self.cache_reload_pass;
        if !common {
            return PrototypeDecision::Rejected;
        }
        if !self.all_consumer_envelope_complete {
            return PrototypeDecision::Inconclusive;
        }
        let direct = self.direct_accuracy_pass
            && self.direct_calls_per_second >= MINIMUM_PROTOTYPE_CALLS_PER_SECOND;
        let custom = self.custom_accuracy_pass
            && self.custom_calls_per_second >= MINIMUM_PROTOTYPE_CALLS_PER_SECOND;
        match (direct, custom) {
            (true, false) => PrototypeDecision::DirectApfelSelected,
            (false, true) => PrototypeDecision::CustomInterpolatorSelected,
            (true, true) => PrototypeDecision::Inconclusive,
            (false, false) => PrototypeDecision::Rejected,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PrototypeStudyContract {
    pub policy_version: String,
    pub maximum_runtime_seconds: u64,
    pub maximum_generated_bytes: u64,
    pub anchors: Vec<PrototypeAnchor>,
    pub metrics: Vec<String>,
    pub production_events: bool,
    pub d2_authorized: bool,
}

impl PrototypeStudyContract {
    pub fn fixed() -> Result<Self, TransportPrototypeError> {
        Ok(Self {
            policy_version: PROTOTYPE_STUDY_POLICY_VERSION.into(),
            maximum_runtime_seconds: MAX_STUDY_RUNTIME.as_secs(),
            maximum_generated_bytes: MAX_STUDY_BYTES,
            anchors: prototype_anchors()?,
            metrics: [
                "direct_reference_accuracy",
                "custom_interpolator_accuracy",
                "threshold_neighborhood_behavior",
                "strict_support",
                "deterministic_repetition",
                "initialization_time",
                "calls_per_second",
                "peak_memory_when_measurable",
                "thread_safety",
                "process_isolation",
                "cache_construction_and_reload",
                "identity_reproducibility",
                "all_consumer_query_envelope",
            ]
            .into_iter()
            .map(str::to_owned)
            .collect(),
            production_events: false,
            d2_authorized: D2_AUTHORIZED,
        })
    }
}

#[derive(Debug)]
pub struct StudyBudget {
    started: Instant,
    output_root: std::path::PathBuf,
}

impl StudyBudget {
    pub fn start(output_root: &Path) -> Result<Self, TransportPrototypeError> {
        fs::create_dir_all(output_root)?;
        let budget = Self {
            started: Instant::now(),
            output_root: output_root.to_path_buf(),
        };
        budget.enforce()?;
        Ok(budget)
    }

    pub fn enforce(&self) -> Result<(), TransportPrototypeError> {
        Self::enforce_observed(self.started.elapsed(), directory_bytes(&self.output_root)?)
    }

    pub fn enforce_observed(
        elapsed: Duration,
        generated_bytes: u64,
    ) -> Result<(), TransportPrototypeError> {
        if elapsed > MAX_STUDY_RUNTIME {
            return Err(TransportPrototypeError::Budget(
                "D1A study exceeded the fixed 30-minute runtime".into(),
            ));
        }
        if generated_bytes > MAX_STUDY_BYTES {
            return Err(TransportPrototypeError::Budget(format!(
                "D1A study exceeded the fixed 2 GiB disk cap: {generated_bytes} bytes"
            )));
        }
        Ok(())
    }

    #[cfg(test)]
    fn with_started(output_root: &Path, started: Instant) -> Self {
        Self {
            started,
            output_root: output_root.to_path_buf(),
        }
    }
}

fn directory_bytes(path: &Path) -> Result<u64, std::io::Error> {
    let mut total = 0u64;
    for entry in fs::read_dir(path)? {
        let entry = entry?;
        let metadata = entry.metadata()?;
        if metadata.is_dir() {
            total = total.saturating_add(directory_bytes(&entry.path())?);
        } else {
            total = total.saturating_add(metadata.len());
        }
    }
    Ok(total)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn synthetic_grid() -> DeterministicTransportGrid {
        let xs = vec![0.01, 0.1, 1.0];
        let qs = vec![1.0, 2.0, 4.0];
        let flavors = vec![21];
        let mut values = Vec::new();
        for q in &qs {
            for x in &xs {
                values.push(x * q);
            }
        }
        DeterministicTransportGrid::new(xs, qs, vec![2.0], flavors, values).unwrap()
    }

    #[test]
    fn versions_and_identities_are_separate() {
        let grid = synthetic_grid();
        assert_ne!(DIRECT_APFEL_PROTOTYPE_VERSION, grid.version);
        assert!(grid.identity.starts_with("sha256:"));
    }

    #[test]
    fn strict_support_and_knot_reproduction() {
        let grid = synthetic_grid();
        let value = grid
            .evaluate(TransportQuery {
                flavor: 21,
                x: 0.1,
                q_gev: 2.0,
            })
            .unwrap();
        assert_eq!(value.xf, 0.2);
        assert_eq!(value.threshold_side, ThresholdSide::AtCharm);
        assert!(grid
            .evaluate(TransportQuery {
                flavor: 21,
                x: 0.001,
                q_gev: 2.0,
            })
            .is_err());
    }

    #[test]
    fn interpolation_is_deterministic_and_threshold_one_sided() {
        let grid = synthetic_grid();
        let below = TransportQuery {
            flavor: 21,
            x: 0.05,
            q_gev: 1.999,
        };
        let above = TransportQuery {
            q_gev: 2.001,
            ..below
        };
        assert_eq!(grid.evaluate(below).unwrap(), grid.evaluate(below).unwrap());
        assert_eq!(
            grid.evaluate(below).unwrap().threshold_side,
            ThresholdSide::BelowCharm
        );
        assert_eq!(
            grid.evaluate(above).unwrap().threshold_side,
            ThresholdSide::BetweenCharmAndBottom
        );
    }

    #[test]
    fn synthetic_query_envelope_is_predeclared() {
        let envelope = HardProcessQueryEnvelope::hera_dis();
        let queries = envelope.synthetic_queries();
        assert!(!queries.is_empty());
        assert!(queries
            .iter()
            .all(|(x, q)| envelope.contains_hard_query(*x, *q)));
        assert!(envelope
            .unresolved_consumers()
            .contains(&"initial_state_shower".to_owned()));
    }

    #[test]
    fn fixed_contract_has_three_anchors_and_never_authorizes_d2() {
        let contract = PrototypeStudyContract::fixed().unwrap();
        assert_eq!(contract.anchors.len(), 3);
        assert_eq!(contract.maximum_runtime_seconds, 1800);
        assert_eq!(contract.maximum_generated_bytes, 2 * 1024 * 1024 * 1024);
        assert!(!contract.production_events);
        assert!(!contract.d2_authorized);
    }

    #[test]
    fn runtime_cap_is_enforced() {
        let root =
            std::env::temp_dir().join(format!("partonsbi-d1a-budget-{}", std::process::id()));
        fs::create_dir_all(&root).unwrap();
        let budget = StudyBudget::with_started(
            &root,
            Instant::now() - MAX_STUDY_RUNTIME - Duration::from_secs(1),
        );
        assert!(matches!(
            budget.enforce(),
            Err(TransportPrototypeError::Budget(_))
        ));
        fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn disk_cap_and_selection_gates_are_enforced() {
        assert!(StudyBudget::enforce_observed(Duration::ZERO, MAX_STUDY_BYTES + 1).is_err());
        let evidence = PrototypeSelectionEvidence {
            direct_accuracy_pass: true,
            custom_accuracy_pass: true,
            deterministic_identity_pass: true,
            strict_support_pass: true,
            threshold_behavior_pass: true,
            thread_safety_pass: true,
            process_isolation_pass: true,
            cache_reload_pass: true,
            all_consumer_envelope_complete: false,
            direct_calls_per_second: 10_000.0,
            custom_calls_per_second: 10_000.0,
        };
        assert_eq!(evidence.decision(), PrototypeDecision::Inconclusive);
        assert!(!D2_AUTHORIZED);
    }

    #[test]
    fn prototype_pdf_transport_filter_covers_authorization_gate() {
        assert!(!D2_AUTHORIZED);
    }

    #[test]
    fn direct_axes_pad_off_knot_and_single_query_batches() {
        let off_knot = vec![
            TransportQuery {
                flavor: 21,
                x: 0.02,
                q_gev: 5.0,
            },
            TransportQuery {
                flavor: 2,
                x: 0.03,
                q_gev: 7.0,
            },
        ];
        let (xs, qs) = padded_evaluation_axes(&off_knot, 1.0e-9, 1.0, 1.295, 100_000.0);
        assert_eq!(xs, vec![0.02, 0.03, 1.0]);
        assert_eq!(qs, vec![1.295, 5.0, 7.0]);

        let single = vec![TransportQuery {
            flavor: 21,
            x: 1.0,
            q_gev: 1.295,
        }];
        let (xs, qs) = padded_evaluation_axes(&single, 1.0e-9, 1.0, 1.295, 100_000.0);
        assert_eq!(xs, vec![1.0e-9, 1.0]);
        assert_eq!(qs, vec![1.295, 100_000.0]);
    }

    #[test]
    fn direct_batch_padding_preserves_results_order_and_is_deterministic() {
        let evaluator = DirectApfelEvaluator::initialize().unwrap();
        let theta = PdfTheta::new(0.0, 0.0).unwrap();
        let queries = vec![
            TransportQuery {
                flavor: 2,
                x: 0.03,
                q_gev: 7.0,
            },
            TransportQuery {
                flavor: 21,
                x: 0.02,
                q_gev: 5.0,
            },
        ];
        let first = evaluator.evaluate_batch(theta, &queries).unwrap();
        let repeated = evaluator.evaluate_batch(theta, &queries).unwrap();
        assert_eq!(first, repeated);
        assert_eq!(first.len(), queries.len());
        assert_eq!(first[0].query, queries[0]);
        assert_eq!(first[1].query, queries[1]);
        assert!(first.iter().all(|result| result.query.x != 1.0));
        assert!(first.iter().all(|result| result.query.q_gev != 1.295));

        let one_query = vec![TransportQuery {
            flavor: 21,
            x: 0.02,
            q_gev: 5.0,
        }];
        let one_result = evaluator.evaluate_batch(theta, &one_query).unwrap();
        assert_eq!(one_result.len(), 1);
        assert_eq!(one_result[0].query, one_query[0]);

        let outside = vec![TransportQuery {
            flavor: 21,
            x: evaluator.config().exported_x_minimum / 2.0,
            q_gev: 5.0,
        }];
        assert!(matches!(
            evaluator.evaluate_batch(theta, &outside),
            Err(TransportPrototypeError::Support { .. })
        ));
    }
}
