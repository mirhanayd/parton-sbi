//! Backend-independent structure-function requests and results.
//!
//! The existing leading-order functions in [`super::structure_functions`]
//! remain the source of the educational photon-exchange approximation. This
//! module adds an object-safe provider interface without changing that API.

use std::error::Error;
use std::fmt;
use std::io;
use std::path::PathBuf;
use std::str::FromStr;

use serde::{Deserialize, Serialize};

use super::pdf::PdfProvider;
use super::structure_functions::{evaluate_lo_structure_functions, StructureFunctionError};

/// Version of the Rust/APFEL++ JSON request and response schema.
pub const STRUCTURE_FUNCTION_SCHEMA_VERSION: u32 = 1;

/// Machine-readable identifier for pure photon exchange.
pub const PHOTON_EXCHANGE_MODE: &str = "photon_exchange";

/// Machine-readable identifier for the existing LO parton-model calculation.
pub const LO_PARTON_MODEL_SCHEME: &str = "lo_parton_model";

/// Perturbative orders supported by the phase-three interface.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum PerturbativeOrder {
    Lo,
    Nlo,
}

impl PerturbativeOrder {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Lo => "LO",
            Self::Nlo => "NLO",
        }
    }
}

impl fmt::Display for PerturbativeOrder {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(self.as_str())
    }
}

impl FromStr for PerturbativeOrder {
    type Err = ParsePerturbativeOrderError;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        if value.eq_ignore_ascii_case("LO") {
            Ok(Self::Lo)
        } else if value.eq_ignore_ascii_case("NLO") {
            Ok(Self::Nlo)
        } else {
            Err(ParsePerturbativeOrderError {
                value: value.to_owned(),
            })
        }
    }
}

/// An unsupported textual perturbative order.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParsePerturbativeOrderError {
    value: String,
}

impl ParsePerturbativeOrderError {
    #[must_use]
    pub fn value(&self) -> &str {
        &self.value
    }
}

impl fmt::Display for ParsePerturbativeOrderError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            formatter,
            "unsupported perturbative order '{}'; supported orders are LO and NLO",
            self.value
        )
    }
}

impl Error for ParsePerturbativeOrderError {}

/// Inclusive process supported by this phase.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StructureFunctionProcess {
    NcDis,
}

impl fmt::Display for StructureFunctionProcess {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("nc_dis")
    }
}

/// Incident lepton supported by this phase.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum DisProjectile {
    Electron,
}

impl fmt::Display for DisProjectile {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("electron")
    }
}

/// Hadronic target supported by this phase.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum DisTarget {
    Proton,
}

impl fmt::Display for DisTarget {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("proton")
    }
}

/// Backend that produced a structure-function result.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StructureFunctionBackend {
    LoPdf,
    Apfel,
    Surrogate,
}

impl fmt::Display for StructureFunctionBackend {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::LoPdf => formatter.write_str("lo_pdf"),
            Self::Apfel => formatter.write_str("apfel"),
            Self::Surrogate => formatter.write_str("surrogate"),
        }
    }
}

/// A versioned request shared by the LO and APFEL++ backends.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StructureFunctionRequest {
    pub schema_version: u32,
    pub process: StructureFunctionProcess,
    pub projectile: DisProjectile,
    pub target: DisTarget,
    pub x: f64,
    /// Momentum-transfer scale `Q²` in GeV².
    pub q2: f64,
    pub order: PerturbativeOrder,
    pub pdf_set: String,
    pub pdf_member: i32,
    /// Factorization-scale ratio `mu_F / Q`.
    pub mu_f_over_q: f64,
    /// Renormalization-scale ratio `mu_R / Q`.
    pub mu_r_over_q: f64,
}

impl StructureFunctionRequest {
    /// Construct an electromagnetic neutral-current electron-proton request.
    #[must_use]
    pub fn electromagnetic_nc(
        x: f64,
        q2: f64,
        order: PerturbativeOrder,
        pdf_set: impl Into<String>,
        pdf_member: i32,
    ) -> Self {
        Self {
            schema_version: STRUCTURE_FUNCTION_SCHEMA_VERSION,
            process: StructureFunctionProcess::NcDis,
            projectile: DisProjectile::Electron,
            target: DisTarget::Proton,
            x,
            q2,
            order,
            pdf_set: pdf_set.into(),
            pdf_member,
            mu_f_over_q: 1.0,
            mu_r_over_q: 1.0,
        }
    }

    /// Validate protocol, kinematic, PDF, and scale inputs before evaluation.
    pub fn validate(&self) -> Result<(), StructureFunctionProviderError> {
        if self.schema_version != STRUCTURE_FUNCTION_SCHEMA_VERSION {
            return Err(StructureFunctionProviderError::InvalidRequest {
                field: "schema_version",
                value: self.schema_version.to_string(),
                requirement: "equal to the supported schema version 1",
            });
        }
        if !self.x.is_finite() || self.x <= 0.0 || self.x >= 1.0 {
            return Err(StructureFunctionProviderError::InvalidRequest {
                field: "x",
                value: self.x.to_string(),
                requirement: "finite and in the open interval (0, 1)",
            });
        }
        if !self.q2.is_finite() || self.q2 <= 0.0 {
            return Err(StructureFunctionProviderError::InvalidRequest {
                field: "q2",
                value: self.q2.to_string(),
                requirement: "finite and positive in GeV^2",
            });
        }
        if self.pdf_set.is_empty() || self.pdf_set.trim() != self.pdf_set {
            return Err(StructureFunctionProviderError::InvalidRequest {
                field: "pdf_set",
                value: self.pdf_set.clone(),
                requirement: "non-empty and free of leading or trailing whitespace",
            });
        }
        if self.pdf_member < 0 {
            return Err(StructureFunctionProviderError::InvalidRequest {
                field: "pdf_member",
                value: self.pdf_member.to_string(),
                requirement: "a non-negative member index",
            });
        }
        validate_scale("mu_f_over_q", self.mu_f_over_q)?;
        validate_scale("mu_r_over_q", self.mu_r_over_q)?;
        Ok(())
    }
}

fn validate_scale(field: &'static str, value: f64) -> Result<(), StructureFunctionProviderError> {
    if !value.is_finite() || value <= 0.0 {
        return Err(StructureFunctionProviderError::InvalidRequest {
            field,
            value: value.to_string(),
            requirement: "a finite, positive ratio",
        });
    }
    Ok(())
}

/// Reproducibility metadata returned with every structure-function result.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StructureFunctionMetadata {
    pub backend: StructureFunctionBackend,
    pub apfelxx_version: Option<String>,
    pub lhapdf_version: Option<String>,
    pub pdf_set: String,
    pub pdf_member: i32,
    /// Perturbative order declared by the selected PDF member.
    pub pdf_order_qcd: i32,
    /// Data-version integer declared by the selected PDF grid.
    pub pdf_data_version: i32,
    pub order: PerturbativeOrder,
    pub process: StructureFunctionProcess,
    pub projectile: DisProjectile,
    pub target: DisTarget,
    pub mu_f_over_q: f64,
    pub mu_r_over_q: f64,
    pub scheme: String,
    pub electromagnetic_mode: String,
    #[serde(default)]
    pub os_arch: Option<String>,
    #[serde(default)]
    pub rust_version: Option<String>,
    #[serde(default)]
    pub git_commit: Option<String>,
    #[serde(default)]
    pub git_dirty: Option<bool>,
    #[serde(default)]
    pub pythia_version: Option<String>,
    #[serde(default)]
    pub hepmc_version: Option<String>,
    #[serde(default)]
    pub python_env_hash: Option<String>,
}

/// Backend-independent inclusive structure functions at one `(x, Q²)` point.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StructureFunctionResult {
    pub f2: f64,
    pub fl: f64,
    pub xf3: f64,
    pub metadata: StructureFunctionMetadata,
}

impl StructureFunctionResult {
    /// Require all numerical physics outputs to be finite.
    pub fn validate_finite(&self) -> Result<(), StructureFunctionProviderError> {
        for (quantity, value) in [("F2", self.f2), ("FL", self.fl), ("xF3", self.xf3)] {
            if !value.is_finite() {
                return Err(StructureFunctionProviderError::NonFiniteResult { quantity, value });
            }
        }
        if self.metadata.pdf_order_qcd < 0 {
            return Err(StructureFunctionProviderError::InvalidResponse {
                message: format!(
                    "metadata pdf_order_qcd must be non-negative, got {}",
                    self.metadata.pdf_order_qcd
                ),
            });
        }
        if self.metadata.pdf_data_version < 0 {
            return Err(StructureFunctionProviderError::InvalidResponse {
                message: format!(
                    "metadata pdf_data_version must be non-negative, got {}",
                    self.metadata.pdf_data_version
                ),
            });
        }
        Ok(())
    }
}

/// Object-safe abstraction over structure-function calculations.
pub trait StructureFunctionProvider {
    fn evaluate(
        &self,
        request: &StructureFunctionRequest,
    ) -> Result<StructureFunctionResult, StructureFunctionProviderError>;
}

/// Adapter from the existing [`PdfProvider`] LO calculation to the common API.
#[derive(Debug)]
pub struct LoPdfStructureFunctionProvider<P> {
    pdf: P,
    pdf_set: String,
    pdf_member: i32,
    pdf_order_qcd: i32,
    pdf_data_version: i32,
}

impl<P> LoPdfStructureFunctionProvider<P> {
    pub fn new(
        pdf: P,
        pdf_set: impl Into<String>,
        pdf_member: i32,
        pdf_order_qcd: i32,
        pdf_data_version: i32,
    ) -> Result<Self, StructureFunctionProviderError> {
        let pdf_set = pdf_set.into();
        if pdf_set.is_empty() || pdf_set.trim() != pdf_set {
            return Err(StructureFunctionProviderError::InvalidRequest {
                field: "pdf_set",
                value: pdf_set,
                requirement: "non-empty and free of leading or trailing whitespace",
            });
        }
        for (field, value) in [
            ("pdf_member", pdf_member),
            ("pdf_order_qcd", pdf_order_qcd),
            ("pdf_data_version", pdf_data_version),
        ] {
            if value < 0 {
                return Err(StructureFunctionProviderError::InvalidRequest {
                    field,
                    value: value.to_string(),
                    requirement: "a non-negative integer",
                });
            }
        }
        Ok(Self {
            pdf,
            pdf_set,
            pdf_member,
            pdf_order_qcd,
            pdf_data_version,
        })
    }

    #[must_use]
    pub fn pdf_provider(&self) -> &P {
        &self.pdf
    }

    #[must_use]
    pub fn pdf_set(&self) -> &str {
        &self.pdf_set
    }

    #[must_use]
    pub const fn pdf_member(&self) -> i32 {
        self.pdf_member
    }
}

impl<P: PdfProvider> StructureFunctionProvider for LoPdfStructureFunctionProvider<P> {
    fn evaluate(
        &self,
        request: &StructureFunctionRequest,
    ) -> Result<StructureFunctionResult, StructureFunctionProviderError> {
        request.validate()?;
        if request.order != PerturbativeOrder::Lo {
            return Err(StructureFunctionProviderError::UnsupportedOrder {
                backend: StructureFunctionBackend::LoPdf,
                order: request.order,
            });
        }
        if request.mu_f_over_q != 1.0 || request.mu_r_over_q != 1.0 {
            return Err(StructureFunctionProviderError::UnsupportedScale {
                backend: StructureFunctionBackend::LoPdf,
                mu_f_over_q: request.mu_f_over_q,
                mu_r_over_q: request.mu_r_over_q,
            });
        }
        validate_configuration_match("pdf_set", &self.pdf_set, &request.pdf_set)?;
        validate_configuration_match(
            "pdf_member",
            &self.pdf_member.to_string(),
            &request.pdf_member.to_string(),
        )?;

        let lo = evaluate_lo_structure_functions(&self.pdf, request.x, request.q2)
            .map_err(StructureFunctionProviderError::LoEvaluation)?;
        let result = StructureFunctionResult {
            f2: lo.f2,
            fl: lo.fl,
            xf3: lo.xf3,
            metadata: StructureFunctionMetadata {
                backend: StructureFunctionBackend::LoPdf,
                apfelxx_version: None,
                lhapdf_version: None,
                pdf_set: self.pdf_set.clone(),
                pdf_member: self.pdf_member,
                pdf_order_qcd: self.pdf_order_qcd,
                pdf_data_version: self.pdf_data_version,
                order: PerturbativeOrder::Lo,
                process: request.process,
                projectile: request.projectile,
                target: request.target,
                mu_f_over_q: request.mu_f_over_q,
                mu_r_over_q: request.mu_r_over_q,
                scheme: "LO".to_string(),
                electromagnetic_mode: "photon_exchange".to_string(),
                os_arch: None,
                rust_version: None,
                git_commit: None,
                git_dirty: None,
                pythia_version: None,
                hepmc_version: None,
                python_env_hash: None,
            },
        };
        result.validate_finite()?;
        Ok(result)
    }
}

fn validate_configuration_match(
    field: &'static str,
    configured: &str,
    requested: &str,
) -> Result<(), StructureFunctionProviderError> {
    if configured != requested {
        return Err(StructureFunctionProviderError::ConfigurationMismatch {
            field,
            configured: configured.to_owned(),
            requested: requested.to_owned(),
        });
    }
    Ok(())
}

/// Typed failures from request validation, provider evaluation, or transport.
#[derive(Debug)]
pub enum StructureFunctionProviderError {
    InvalidRequest {
        field: &'static str,
        value: String,
        requirement: &'static str,
    },
    UnsupportedOrder {
        backend: StructureFunctionBackend,
        order: PerturbativeOrder,
    },
    UnsupportedScale {
        backend: StructureFunctionBackend,
        mu_f_over_q: f64,
        mu_r_over_q: f64,
    },
    ConfigurationMismatch {
        field: &'static str,
        configured: String,
        requested: String,
    },
    LoEvaluation(StructureFunctionError),
    BackendUnavailable {
        executable: PathBuf,
        source: io::Error,
    },
    BackendIo {
        executable: PathBuf,
        operation: &'static str,
        source: io::Error,
    },
    BackendExited {
        executable: PathBuf,
        status: Option<i32>,
        stdout: String,
        stderr: String,
    },
    RequestSerialization {
        source: serde_json::Error,
    },
    ResponseDeserialization {
        source: serde_json::Error,
        stdout: String,
        stderr: String,
    },
    SchemaMismatch {
        expected: u32,
        actual: u32,
    },
    BackendRejected {
        code: String,
        message: String,
        hint: Option<String>,
        status: Option<i32>,
    },
    InvalidResponse {
        message: String,
    },
    MetadataMismatch {
        field: &'static str,
        expected: String,
        actual: String,
    },
    NonFiniteResult {
        quantity: &'static str,
        value: f64,
    },
    OutOfDomain {
        x: f64,
        q2: f64,
        reason: String,
    },
    EvaluationFailed(String),
}

impl fmt::Display for StructureFunctionProviderError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidRequest {
                field,
                value,
                requirement,
            } => write!(
                formatter,
                "invalid structure-function request field {field}='{value}': expected {requirement}"
            ),
            Self::UnsupportedOrder { backend, order } => write!(
                formatter,
                "structure-function backend '{backend}' does not support order {order}"
            ),
            Self::UnsupportedScale {
                backend,
                mu_f_over_q,
                mu_r_over_q,
            } => write!(
                formatter,
                "structure-function backend '{backend}' does not support mu_F/Q={mu_f_over_q}, mu_R/Q={mu_r_over_q}"
            ),
            Self::ConfigurationMismatch {
                field,
                configured,
                requested,
            } => write!(
                formatter,
                "provider {field} is configured as '{configured}', but the request uses '{requested}'"
            ),
            Self::LoEvaluation(source) => {
                write!(formatter, "LO structure-function evaluation failed: {source}")
            }
            Self::BackendUnavailable { executable, source } => write!(
                formatter,
                "APFEL++ backend '{}' is unavailable: {source}; run scripts/setup_apfelxx_wsl.sh in WSL",
                executable.display()
            ),
            Self::BackendIo {
                executable,
                operation,
                source,
            } => write!(
                formatter,
                "APFEL++ backend '{}' failed while {operation}: {source}",
                executable.display()
            ),
            Self::BackendExited {
                executable,
                status,
                stdout,
                stderr,
            } => write!(
                formatter,
                "APFEL++ backend '{}' exited unsuccessfully (status {status:?}); stdout: {stdout}; stderr: {stderr}",
                executable.display()
            ),
            Self::RequestSerialization { source } => {
                write!(formatter, "failed to serialize APFEL++ schema-v1 request: {source}")
            }
            Self::ResponseDeserialization {
                source,
                stdout,
                stderr,
            } => write!(
                formatter,
                "APFEL++ returned invalid schema-v1 JSON: {source}; stdout: {stdout}; stderr: {stderr}"
            ),
            Self::SchemaMismatch { expected, actual } => write!(
                formatter,
                "APFEL++ response schema version {actual} is unsupported; expected {expected}"
            ),
            Self::BackendRejected {
                code,
                message,
                hint,
                status,
            } => {
                write!(
                    formatter,
                    "APFEL++ rejected the request [{code}] (status {status:?}): {message}"
                )?;
                if let Some(hint) = hint {
                    write!(formatter, "; hint: {hint}")?;
                }
                Ok(())
            }
            Self::InvalidResponse { message } => {
                write!(formatter, "APFEL++ returned an invalid response: {message}")
            }
            Self::MetadataMismatch {
                field,
                expected,
                actual,
            } => write!(
                formatter,
                "APFEL++ metadata field {field} is '{actual}', expected '{expected}'"
            ),
            Self::NonFiniteResult { quantity, value } => {
                write!(formatter, "backend returned non-finite {quantity}={value}")
            }
            Self::OutOfDomain { x, q2, reason } => write!(
                formatter,
                "surrogate model rejected point x={x}, Q2={q2}: {reason}"
            ),
            Self::EvaluationFailed(message) => write!(
                formatter,
                "provider evaluation failed: {message}"
            ),
        }
    }
}

impl Error for StructureFunctionProviderError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::LoEvaluation(source) => Some(source),
            Self::BackendUnavailable { source, .. } | Self::BackendIo { source, .. } => {
                Some(source)
            }
            Self::RequestSerialization { source }
            | Self::ResponseDeserialization { source, .. } => Some(source),
            _ => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::physics::pdf::{PartonDensities, PdfError};

    struct MockPdf;

    impl PdfProvider for MockPdf {
        fn parton_densities(&self, x: f64, q2: f64) -> Result<PartonDensities, PdfError> {
            Ok(PartonDensities {
                x,
                q2,
                gluon: 9.0,
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
            })
        }
    }

    fn request(order: PerturbativeOrder) -> StructureFunctionRequest {
        StructureFunctionRequest::electromagnetic_nc(0.01, 100.0, order, "CT18LO", 0)
    }

    fn mock_metadata() -> StructureFunctionMetadata {
        StructureFunctionMetadata {
            backend: StructureFunctionBackend::Apfel,
            apfelxx_version: Some("4.0.0".to_owned()),
            lhapdf_version: Some("6.5.6".to_owned()),
            pdf_set: "CT18LO".to_owned(),
            pdf_member: 0,
            pdf_order_qcd: 0,
            pdf_data_version: 1,
            order: PerturbativeOrder::Lo,
            process: StructureFunctionProcess::NcDis,
            projectile: DisProjectile::Electron,
            target: DisTarget::Proton,
            mu_f_over_q: 1.0,
            mu_r_over_q: 1.0,
            scheme: "ZM-VFNS".to_owned(),
            electromagnetic_mode: PHOTON_EXCHANGE_MODE.to_owned(),
            os_arch: None,
            rust_version: None,
            git_commit: None,
            git_dirty: None,
            pythia_version: None,
            hepmc_version: None,
            python_env_hash: None,
        }
    }

    #[test]
    fn request_json_round_trip_uses_schema_v1_names() {
        let request = request(PerturbativeOrder::Nlo);
        let json = serde_json::to_value(&request).unwrap();

        assert_eq!(json["schema_version"], 1);
        assert_eq!(json["process"], "nc_dis");
        assert_eq!(json["projectile"], "electron");
        assert_eq!(json["target"], "proton");
        assert_eq!(json["order"], "NLO");
        assert_eq!(
            serde_json::from_value::<StructureFunctionRequest>(json).unwrap(),
            request
        );
    }

    #[test]
    fn rejects_unknown_textual_and_json_orders() {
        let error = "NNLO".parse::<PerturbativeOrder>().unwrap_err();
        assert_eq!(error.value(), "NNLO");

        let json = serde_json::to_string(&request(PerturbativeOrder::Lo))
            .unwrap()
            .replace("\"LO\"", "\"NNLO\"");
        assert!(serde_json::from_str::<StructureFunctionRequest>(&json).is_err());
    }

    #[test]
    fn validates_schema_kinematics_pdf_and_scales() {
        let mut candidate = request(PerturbativeOrder::Lo);
        candidate.schema_version = 2;
        assert!(candidate.validate().is_err());

        candidate = request(PerturbativeOrder::Lo);
        candidate.x = 1.0;
        assert!(candidate.validate().is_err());

        candidate = request(PerturbativeOrder::Lo);
        candidate.q2 = f64::NAN;
        assert!(candidate.validate().is_err());

        candidate = request(PerturbativeOrder::Lo);
        candidate.pdf_set = " CT18LO".to_owned();
        assert!(candidate.validate().is_err());

        candidate = request(PerturbativeOrder::Lo);
        candidate.pdf_member = -1;
        assert!(candidate.validate().is_err());

        candidate = request(PerturbativeOrder::Lo);
        candidate.mu_f_over_q = 0.0;
        assert!(candidate.validate().is_err());

        candidate = request(PerturbativeOrder::Lo);
        candidate.mu_r_over_q = f64::INFINITY;
        assert!(candidate.validate().is_err());
    }

    #[test]
    fn lo_pdf_adapter_uses_existing_calculation_through_trait() {
        let provider = LoPdfStructureFunctionProvider::new(MockPdf, "CT18LO", 0, 0, 1).unwrap();
        let provider: &dyn StructureFunctionProvider = &provider;

        let result = provider.evaluate(&request(PerturbativeOrder::Lo)).unwrap();

        let expected = (4.0 / 9.0) * (0.36 + 0.04 + 0.01 + 0.01)
            + (1.0 / 9.0) * (0.18 + 0.02 + 0.015 + 0.015 + 0.002 + 0.002);
        assert!((result.f2 - expected).abs() < 1.0e-15);
        assert_eq!(result.fl, 0.0);
        assert_eq!(result.xf3, 0.0);
        assert_eq!(result.metadata.backend, StructureFunctionBackend::LoPdf);
        assert_eq!(result.metadata.pdf_data_version, 1);
    }

    #[test]
    fn lo_pdf_adapter_rejects_nlo_scales_and_configuration_mismatch() {
        let provider = LoPdfStructureFunctionProvider::new(MockPdf, "CT18LO", 0, 0, 1).unwrap();
        assert!(matches!(
            provider.evaluate(&request(PerturbativeOrder::Nlo)),
            Err(StructureFunctionProviderError::UnsupportedOrder { .. })
        ));

        let mut scaled = request(PerturbativeOrder::Lo);
        scaled.mu_f_over_q = 2.0;
        assert!(matches!(
            provider.evaluate(&scaled),
            Err(StructureFunctionProviderError::UnsupportedScale { .. })
        ));

        let mut different_set = request(PerturbativeOrder::Lo);
        different_set.pdf_set = "OTHER".to_owned();
        assert!(matches!(
            provider.evaluate(&different_set),
            Err(StructureFunctionProviderError::ConfigurationMismatch {
                field: "pdf_set",
                ..
            })
        ));
    }

    struct MockStructureFunctionProvider;

    impl StructureFunctionProvider for MockStructureFunctionProvider {
        fn evaluate(
            &self,
            _request: &StructureFunctionRequest,
        ) -> Result<StructureFunctionResult, StructureFunctionProviderError> {
            Ok(StructureFunctionResult {
                f2: 0.8,
                fl: 0.1,
                xf3: 0.0,
                metadata: mock_metadata(),
            })
        }
    }

    #[test]
    fn abstraction_supports_deterministic_trait_object_mocks() {
        let provider: &dyn StructureFunctionProvider = &MockStructureFunctionProvider;
        let result = provider.evaluate(&request(PerturbativeOrder::Lo)).unwrap();
        assert_eq!((result.f2, result.fl, result.xf3), (0.8, 0.1, 0.0));
    }

    #[test]
    fn rejects_invalid_pdf_metadata_and_non_finite_results() {
        let mut result = StructureFunctionResult {
            f2: f64::NAN,
            fl: 0.0,
            xf3: 0.0,
            metadata: mock_metadata(),
        };
        assert!(matches!(
            result.validate_finite(),
            Err(StructureFunctionProviderError::NonFiniteResult { quantity: "F2", .. })
        ));

        result.f2 = 0.8;
        result.metadata.pdf_order_qcd = -1;
        assert!(matches!(
            result.validate_finite(),
            Err(StructureFunctionProviderError::InvalidResponse { .. })
        ));
    }
}
