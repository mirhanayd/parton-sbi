//! Separated state structs for the GUI.
//!
//! This module contains all state types used by the DIS analysis GUI pages.
//! The state is deliberately split into independent concerns to avoid a
//! monolithic "god struct".

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

// ---------------------------------------------------------------------------
// Top-level mode selector
// ---------------------------------------------------------------------------

/// The two main application modes that are always cleanly separated.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TopLevelMode {
    LegacyCornell,
    DisAnalysis,
}

/// Active page within the DIS analysis mode.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DisPage {
    Configuration,
    InclusiveCalculation,
    EventGeneration,
    EventViewer,
    DataValidation,
    RunHistory,
}

impl DisPage {
    pub const ALL: [DisPage; 6] = [
        DisPage::Configuration,
        DisPage::InclusiveCalculation,
        DisPage::EventGeneration,
        DisPage::EventViewer,
        DisPage::DataValidation,
        DisPage::RunHistory,
    ];

    #[must_use]
    pub fn label(self) -> &'static str {
        match self {
            DisPage::Configuration => "⚙ Configuration",
            DisPage::InclusiveCalculation => "📊 Inclusive Calculation",
            DisPage::EventGeneration => "🚀 Event Generation",
            DisPage::EventViewer => "🔍 Event Viewer",
            DisPage::DataValidation => "✅ Data Validation",
            DisPage::RunHistory => "📁 Run History",
        }
    }
}

// ---------------------------------------------------------------------------
// UI state
// ---------------------------------------------------------------------------

/// Transient UI state not persisted across sessions.
pub struct UiState {
    pub mode: TopLevelMode,
    pub active_dis_page: DisPage,
    pub status_message: Option<String>,
}

impl Default for UiState {
    fn default() -> Self {
        Self {
            mode: TopLevelMode::DisAnalysis,
            active_dis_page: DisPage::Configuration,
            status_message: None,
        }
    }
}

// ---------------------------------------------------------------------------
// DIS configuration
// ---------------------------------------------------------------------------

/// All user-configurable physics parameters for DIS analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DisConfig {
    pub electron_energy_gev: f64,
    pub proton_energy_gev: f64,
    pub process: String,
    pub x_min: f64,
    pub x_max: f64,
    pub q2_min_gev2: f64,
    pub q2_max_gev2: f64,
    pub y_min: f64,
    pub y_max: f64,
    pub w2_cut_gev2: f64,
    pub backend: String,
    pub perturbative_order: String,
    pub pdf_set: String,
    pub pdf_member: i32,
    pub mu_f_over_q: f64,
    pub mu_r_over_q: f64,
    pub event_count: usize,
    pub random_seed: String,
    pub parton_shower: bool,
    pub hadronization: bool,
    pub output_directory: String,
}

impl Default for DisConfig {
    fn default() -> Self {
        Self {
            electron_energy_gev: 27.5,
            proton_energy_gev: 920.0,
            process: "NC".to_string(),
            x_min: 1e-4,
            x_max: 0.8,
            q2_min_gev2: 3.5,
            q2_max_gev2: 10000.0,
            y_min: 0.01,
            y_max: 0.95,
            w2_cut_gev2: 10.0,
            backend: "apfel".to_string(),
            perturbative_order: "NLO".to_string(),
            pdf_set: "CT18NLO".to_string(),
            pdf_member: 0,
            mu_f_over_q: 1.0,
            mu_r_over_q: 1.0,
            event_count: 10000,
            random_seed: String::new(),
            parton_shower: true,
            hadronization: true,
            output_directory: "outputs/dis_run".to_string(),
        }
    }
}

/// Validation error for a DIS configuration field.
#[derive(Debug, Clone, PartialEq)]
pub struct ConfigValidationError {
    pub field: String,
    pub message: String,
}

impl std::fmt::Display for ConfigValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: {}", self.field, self.message)
    }
}

impl DisConfig {
    /// Validate all fields, returning a list of every problem found.
    #[must_use]
    pub fn validate(&self) -> Vec<ConfigValidationError> {
        let mut errors = Vec::new();

        if self.electron_energy_gev <= 0.0 || !self.electron_energy_gev.is_finite() {
            errors.push(ConfigValidationError {
                field: "Electron Energy".into(),
                message: "must be a positive finite number".into(),
            });
        }
        if self.proton_energy_gev <= 0.0 || !self.proton_energy_gev.is_finite() {
            errors.push(ConfigValidationError {
                field: "Proton Energy".into(),
                message: "must be a positive finite number".into(),
            });
        }
        if self.x_min <= 0.0 || self.x_min >= 1.0 {
            errors.push(ConfigValidationError {
                field: "x_min".into(),
                message: "must be in (0, 1)".into(),
            });
        }
        if self.x_max <= 0.0 || self.x_max > 1.0 {
            errors.push(ConfigValidationError {
                field: "x_max".into(),
                message: "must be in (0, 1]".into(),
            });
        }
        if self.x_min >= self.x_max {
            errors.push(ConfigValidationError {
                field: "x range".into(),
                message: "x_min must be less than x_max".into(),
            });
        }
        if self.q2_min_gev2 <= 0.0 {
            errors.push(ConfigValidationError {
                field: "Q² min".into(),
                message: "must be positive".into(),
            });
        }
        if self.q2_max_gev2 <= self.q2_min_gev2 {
            errors.push(ConfigValidationError {
                field: "Q² range".into(),
                message: "Q²_max must be greater than Q²_min".into(),
            });
        }
        if self.y_min < 0.0 || self.y_min >= 1.0 {
            errors.push(ConfigValidationError {
                field: "y_min".into(),
                message: "must be in [0, 1)".into(),
            });
        }
        if self.y_max <= 0.0 || self.y_max > 1.0 {
            errors.push(ConfigValidationError {
                field: "y_max".into(),
                message: "must be in (0, 1]".into(),
            });
        }
        if self.y_min >= self.y_max {
            errors.push(ConfigValidationError {
                field: "y range".into(),
                message: "y_min must be less than y_max".into(),
            });
        }
        if self.w2_cut_gev2 < 0.0 {
            errors.push(ConfigValidationError {
                field: "W² cut".into(),
                message: "must be non-negative".into(),
            });
        }
        if self.pdf_set.trim().is_empty() {
            errors.push(ConfigValidationError {
                field: "PDF Set".into(),
                message: "must not be empty".into(),
            });
        }
        if self.pdf_member < 0 {
            errors.push(ConfigValidationError {
                field: "PDF Member".into(),
                message: "must be non-negative".into(),
            });
        }
        if self.mu_f_over_q <= 0.0 || !self.mu_f_over_q.is_finite() {
            errors.push(ConfigValidationError {
                field: "μ_F/Q".into(),
                message: "must be a positive finite number".into(),
            });
        }
        if self.mu_r_over_q <= 0.0 || !self.mu_r_over_q.is_finite() {
            errors.push(ConfigValidationError {
                field: "μ_R/Q".into(),
                message: "must be a positive finite number".into(),
            });
        }
        if !matches!(self.backend.as_str(), "apfel" | "lo" | "apfel++" | "direct") {
            errors.push(ConfigValidationError {
                field: "Backend".into(),
                message: format!(
                    "unsupported backend '{}'; use 'apfel' or 'lo'",
                    self.backend
                ),
            });
        }
        if !matches!(self.perturbative_order.as_str(), "LO" | "NLO") {
            errors.push(ConfigValidationError {
                field: "Perturbative Order".into(),
                message: format!(
                    "unsupported order '{}'; use 'LO' or 'NLO'",
                    self.perturbative_order
                ),
            });
        }
        if self.output_directory.trim().is_empty() {
            errors.push(ConfigValidationError {
                field: "Output Directory".into(),
                message: "must not be empty".into(),
            });
        }
        if !self.random_seed.is_empty() {
            if self.random_seed.parse::<i64>().is_err() {
                errors.push(ConfigValidationError {
                    field: "Random Seed".into(),
                    message: "must be a valid integer or empty for random".into(),
                });
            }
        }

        errors
    }
}

// ---------------------------------------------------------------------------
// Backend process state
// ---------------------------------------------------------------------------

/// The lifecycle state of a background computation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProcessStatus {
    Idle,
    Running,
    Completed,
    Failed,
    Cancelled,
}

/// State for a background process (event generation, calculation, etc.).
pub struct BackendProcess {
    pub status: ProcessStatus,
    pub stdout_lines: Vec<String>,
    pub stderr_lines: Vec<String>,
    pub exit_code: Option<i32>,
    pub cancel_flag: Arc<AtomicBool>,
    pub progress_text: String,
}

impl Default for BackendProcess {
    fn default() -> Self {
        Self {
            status: ProcessStatus::Idle,
            stdout_lines: Vec::new(),
            stderr_lines: Vec::new(),
            exit_code: None,
            cancel_flag: Arc::new(AtomicBool::new(false)),
            progress_text: String::new(),
        }
    }
}

impl BackendProcess {
    /// Request cancellation of the running process.
    pub fn request_cancel(&self) {
        self.cancel_flag.store(true, Ordering::Release);
    }

    /// Reset to idle state for a new run.
    pub fn reset(&mut self) {
        self.status = ProcessStatus::Idle;
        self.stdout_lines.clear();
        self.stderr_lines.clear();
        self.exit_code = None;
        self.cancel_flag = Arc::new(AtomicBool::new(false));
        self.progress_text.clear();
    }
}

// ---------------------------------------------------------------------------
// Physics results (inclusive calculation)
// ---------------------------------------------------------------------------

/// Results from an inclusive DIS calculation at a single kinematic point.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InclusiveResult {
    pub x: f64,
    pub q2_gev2: f64,
    pub y: f64,
    pub w2_gev2: f64,
    pub f2: f64,
    pub fl: f64,
    pub xf3: f64,
    pub dsigma_dxdq2_gev_m4: f64,
    pub dsigma_dxdq2_pb_gev2: f64,
    pub parton_densities: Vec<(i32, f64)>,
    pub backend_name: String,
    pub order: String,
    pub pdf_set: String,
    pub pdf_member: i32,
    pub scheme: String,
}

// ---------------------------------------------------------------------------
// Event generation summary
// ---------------------------------------------------------------------------

/// Summary of a completed event generation run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventGenSummary {
    pub total_events: usize,
    pub accepted_events: usize,
    pub failed_events: usize,
    pub output_path: String,
    pub hepmc3_file: Option<String>,
    pub config_file: Option<String>,
    pub metadata_file: Option<String>,
}

// ---------------------------------------------------------------------------
// HepMC3 event viewer data
// ---------------------------------------------------------------------------

/// A single particle from a HepMC3 event record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HepMC3Particle {
    pub id: i32,
    pub pdg_id: i32,
    pub status: i32,
    pub px: f64,
    pub py: f64,
    pub pz: f64,
    pub energy: f64,
    pub mass: f64,
    pub production_vertex: Option<i32>,
    pub end_vertex: Option<i32>,
}

/// A single vertex from a HepMC3 event record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HepMC3Vertex {
    pub id: i32,
    pub x: f64,
    pub y: f64,
    pub z: f64,
    pub t: f64,
    pub incoming: Vec<i32>,
    pub outgoing: Vec<i32>,
}

/// A parsed HepMC3 event.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HepMC3Event {
    pub event_number: i64,
    pub particles: Vec<HepMC3Particle>,
    pub vertices: Vec<HepMC3Vertex>,
    pub weights: Vec<f64>,
}

// ---------------------------------------------------------------------------
// Validation summary
// ---------------------------------------------------------------------------

/// Summary loaded from a validation or uncertainty analysis run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationSummary {
    pub dataset: String,
    pub backend: String,
    pub order: String,
    pub pdf_set: String,
    pub n_points: usize,
    pub chi2: f64,
    pub ndf: usize,
    pub chi2_ndf: f64,
    pub mean_ratio: f64,
    pub max_pull: f64,
}

/// A single data-vs-theory comparison point for display.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComparisonPoint {
    pub q2: f64,
    pub x: f64,
    pub y: f64,
    pub data_value: f64,
    pub data_stat_error: f64,
    pub theory_central: f64,
    pub pdf_unc_plus: f64,
    pub pdf_unc_minus: f64,
    pub scale_unc_plus: f64,
    pub scale_unc_minus: f64,
    pub ratio: f64,
    pub residual: f64,
    pub pull: f64,
}

// ---------------------------------------------------------------------------
// Run history
// ---------------------------------------------------------------------------

/// Metadata for a previously completed run found in the output directory.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunHistoryEntry {
    pub directory: PathBuf,
    pub run_name: String,
    pub has_config: bool,
    pub has_metadata: bool,
    pub has_summary: bool,
    pub has_comparison: bool,
    pub has_events: bool,
    pub schema_version: Option<i32>,
}

pub const CURRENT_SCHEMA_VERSION: i32 = 1;

/// Check whether a schema version is compatible with the current version.
#[must_use]
pub fn is_schema_compatible(version: Option<i32>) -> bool {
    match version {
        Some(v) => v == CURRENT_SCHEMA_VERSION,
        None => false,
    }
}

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

/// Categorized error types for actionable messages.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GuiErrorCategory {
    LhapdfSetNotInstalled,
    ApfelBackendMissing,
    PythiaBackendMissing,
    InvalidKinematics,
    UnsupportedOrder,
    InvalidOutputSchema,
    WslgUnavailable,
    ProcessFailed,
    FileNotFound,
    ParseError,
    Unknown,
}

/// A user-facing error with category and actionable message.
#[derive(Debug, Clone)]
pub struct GuiError {
    pub category: GuiErrorCategory,
    pub message: String,
    pub suggestion: String,
}

impl GuiError {
    #[must_use]
    pub fn new(category: GuiErrorCategory, message: impl Into<String>) -> Self {
        let message = message.into();
        let suggestion = match category {
            GuiErrorCategory::LhapdfSetNotInstalled => {
                "Install the PDF set with: lhapdf install <set-name>".to_string()
            }
            GuiErrorCategory::ApfelBackendMissing => {
                "Build the APFEL++ backend: cd physics-engine && mkdir -p build && cd build && cmake .. && make".to_string()
            }
            GuiErrorCategory::PythiaBackendMissing => {
                "Ensure PYTHIA 8 is installed and scripts/pythia_env.sh sets the correct paths"
                    .to_string()
            }
            GuiErrorCategory::InvalidKinematics => {
                "Check the kinematic ranges (x, Q², y, W²) in the configuration tab".to_string()
            }
            GuiErrorCategory::UnsupportedOrder => {
                "Use LO or NLO for the perturbative order".to_string()
            }
            GuiErrorCategory::InvalidOutputSchema => {
                "This output was created by an incompatible version and cannot be loaded".to_string()
            }
            GuiErrorCategory::WslgUnavailable => {
                "Install WSLg or set up X11 forwarding (export DISPLAY=:0)".to_string()
            }
            GuiErrorCategory::ProcessFailed => {
                "Check the stderr log for details".to_string()
            }
            GuiErrorCategory::FileNotFound => {
                "Verify the file path and ensure it exists".to_string()
            }
            GuiErrorCategory::ParseError => {
                "The file format may be corrupted or incompatible".to_string()
            }
            GuiErrorCategory::Unknown => "An unexpected error occurred".to_string(),
        };
        Self {
            category,
            message,
            suggestion,
        }
    }
}

/// Application-wide error state.
pub struct ErrorState {
    pub errors: Vec<GuiError>,
}

impl Default for ErrorState {
    fn default() -> Self {
        Self { errors: Vec::new() }
    }
}

impl ErrorState {
    /// Push a new error. Keeps the last 20 errors.
    pub fn push(&mut self, error: GuiError) {
        self.errors.push(error);
        if self.errors.len() > 20 {
            self.errors.remove(0);
        }
    }

    pub fn clear(&mut self) {
        self.errors.clear();
    }

    #[must_use]
    pub fn has_errors(&self) -> bool {
        !self.errors.is_empty()
    }

    /// Most recent error.
    #[must_use]
    pub fn latest(&self) -> Option<&GuiError> {
        self.errors.last()
    }
}

// ---------------------------------------------------------------------------
// Command construction helpers (no shell-string concatenation)
// ---------------------------------------------------------------------------

/// Build a structured command for the structure-functions CLI.
#[must_use]
pub fn build_structure_function_command(
    x: f64,
    q2: f64,
    backend: &str,
    order: &str,
    pdf_set: &str,
    pdf_member: i32,
    mu_f_over_q: f64,
    mu_r_over_q: f64,
) -> Vec<String> {
    let mut args = vec![
        "structure-functions".to_string(),
        "--backend".to_string(),
        backend.to_string(),
        "--x".to_string(),
        x.to_string(),
        "--q2".to_string(),
        q2.to_string(),
        "--order".to_string(),
        order.to_string(),
        "--pdf-set".to_string(),
        pdf_set.to_string(),
        "--pdf-member".to_string(),
        pdf_member.to_string(),
    ];
    if (mu_f_over_q - 1.0).abs() > 1e-12 {
        args.push("--mu-f-over-q".to_string());
        args.push(mu_f_over_q.to_string());
    }
    if (mu_r_over_q - 1.0).abs() > 1e-12 {
        args.push("--mu-r-over-q".to_string());
        args.push(mu_r_over_q.to_string());
    }
    args
}

/// Build a structured command for the event generation CLI.
#[must_use]
pub fn build_event_generation_command(config: &DisConfig) -> Vec<String> {
    let mut args = vec![
        "generate-dis-events".to_string(),
        "--electron-energy".to_string(),
        config.electron_energy_gev.to_string(),
        "--proton-energy".to_string(),
        config.proton_energy_gev.to_string(),
        "--q2-min".to_string(),
        config.q2_min_gev2.to_string(),
        "--q2-max".to_string(),
        config.q2_max_gev2.to_string(),
        "--x-min".to_string(),
        config.x_min.to_string(),
        "--x-max".to_string(),
        config.x_max.to_string(),
        "--y-min".to_string(),
        config.y_min.to_string(),
        "--y-max".to_string(),
        config.y_max.to_string(),
        "--events".to_string(),
        config.event_count.to_string(),
        "--pdf-set".to_string(),
        config.pdf_set.to_string(),
        "--pdf-member".to_string(),
        config.pdf_member.to_string(),
        "--parton-shower".to_string(),
        config.parton_shower.to_string(),
        "--hadronization".to_string(),
        config.hadronization.to_string(),
        "--output".to_string(),
        config.output_directory.to_string(),
    ];
    if !config.random_seed.is_empty() {
        args.push("--seed".to_string());
        args.push(config.random_seed.clone());
    }
    args
}

/// Build a structured command for the validate-hera CLI.
#[must_use]
pub fn build_validate_hera_command(
    dataset: &str,
    backend: &str,
    order: &str,
    pdf_set: &str,
    pdf_member: i32,
    output: &str,
) -> Vec<String> {
    vec![
        "validate-hera".to_string(),
        "--dataset".to_string(),
        dataset.to_string(),
        "--backend".to_string(),
        backend.to_string(),
        "--order".to_string(),
        order.to_string(),
        "--pdf-set".to_string(),
        pdf_set.to_string(),
        "--pdf-member".to_string(),
        pdf_member.to_string(),
        "--output".to_string(),
        output.to_string(),
    ]
}

/// Build a structured command for the theory-uncertainties CLI.
#[must_use]
pub fn build_theory_uncertainties_command(
    dataset: &str,
    backend: &str,
    order: &str,
    pdf_set: &str,
    output: &str,
    pdf_uncertainty: bool,
    scale_variations: bool,
) -> Vec<String> {
    let mut args = vec![
        "theory-uncertainties".to_string(),
        "--dataset".to_string(),
        dataset.to_string(),
        "--backend".to_string(),
        backend.to_string(),
        "--order".to_string(),
        order.to_string(),
        "--pdf-set".to_string(),
        pdf_set.to_string(),
        "--output".to_string(),
        output.to_string(),
    ];
    if pdf_uncertainty {
        args.push("--pdf-uncertainty".to_string());
    }
    if scale_variations {
        args.push("--scale-variations".to_string());
    }
    args
}
