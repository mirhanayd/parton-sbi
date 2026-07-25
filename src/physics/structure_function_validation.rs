//! Deterministic APFEL-versus-direct-LO structure-function validation.
//!
//! This module contains no filesystem or plotting code. It evaluates the exact
//! required 5-by-4 grid through backend-independent providers, verifies
//! reproducibility metadata, and returns a serializable report.

use std::error::Error;
use std::fmt;

use serde::{Deserialize, Serialize};

use super::structure_function_provider::{
    DisProjectile, DisTarget, PerturbativeOrder, StructureFunctionBackend,
    StructureFunctionMetadata, StructureFunctionProcess, StructureFunctionProvider,
    StructureFunctionProviderError, StructureFunctionRequest, StructureFunctionResult,
    STRUCTURE_FUNCTION_SCHEMA_VERSION,
};

pub const VALIDATION_X_VALUES: [f64; 5] = [1.0e-4, 1.0e-3, 1.0e-2, 0.1, 0.4];
pub const VALIDATION_Q2_VALUES_GEV2: [f64; 4] = [10.0, 100.0, 1_000.0, 10_000.0];
pub const VALIDATION_POINT_COUNT: usize =
    VALIDATION_X_VALUES.len() * VALIDATION_Q2_VALUES_GEV2.len();

pub const F2_ABSOLUTE_DIFFERENCE_DEFINITION: &str = "abs(apfel_f2 - lo_f2)";
pub const F2_RELATIVE_DIFFERENCE_DEFINITION: &str = "abs(apfel_f2 - lo_f2) / abs(lo_f2)";
pub const F2_ZERO_DENOMINATOR_POLICY: &str = "null when lo_f2 == 0; no epsilon substitution";

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StructureFunctionValidationConfig {
    pub pdf_set: String,
    pub pdf_member: i32,
    pub apfel_order: PerturbativeOrder,
    pub mu_f_over_q: f64,
    pub mu_r_over_q: f64,
}

impl StructureFunctionValidationConfig {
    #[must_use]
    pub fn new(
        pdf_set: impl Into<String>,
        pdf_member: i32,
        apfel_order: PerturbativeOrder,
    ) -> Self {
        Self {
            pdf_set: pdf_set.into(),
            pdf_member,
            apfel_order,
            mu_f_over_q: 1.0,
            mu_r_over_q: 1.0,
        }
    }

    pub fn validate(&self) -> Result<(), StructureFunctionValidationError> {
        if self.pdf_set.is_empty() || self.pdf_set.trim() != self.pdf_set {
            return Err(StructureFunctionValidationError::InvalidConfiguration {
                field: "pdf_set",
                value: self.pdf_set.clone(),
                requirement: "non-empty and free of leading or trailing whitespace",
            });
        }
        if self.pdf_member < 0 {
            return Err(StructureFunctionValidationError::InvalidConfiguration {
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

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ValidationBackendMetadata {
    pub backend: StructureFunctionBackend,
    pub order: PerturbativeOrder,
    pub scheme: String,
    pub electromagnetic_mode: String,
    pub apfelxx_version: Option<String>,
    pub lhapdf_version: Option<String>,
    pub mu_f_over_q: f64,
    pub mu_r_over_q: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ValidationPdfMetadata {
    pub set: String,
    pub member: i32,
    pub order_qcd: i32,
    pub data_version: i32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ValidationGridMetadata {
    pub x_values: [f64; 5],
    pub q2_values_gev2: [f64; 4],
    pub ordering: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ValidationUnitMetadata {
    pub q2: String,
    pub structure_functions: String,
    pub differences: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct F2DifferenceConvention {
    pub absolute: String,
    pub relative: String,
    pub zero_denominator: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StructureFunctionValidationMetadata {
    pub schema_version: u32,
    pub application_version: String,
    pub process: StructureFunctionProcess,
    pub projectile: DisProjectile,
    pub target: DisTarget,
    pub pdf: ValidationPdfMetadata,
    pub reference: ValidationBackendMetadata,
    pub candidate: ValidationBackendMetadata,
    pub grid: ValidationGridMetadata,
    pub units: ValidationUnitMetadata,
    pub f2_difference: F2DifferenceConvention,
    pub row_count: usize,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StructureFunctionValidationRow {
    pub x: f64,
    pub q2: f64,
    pub lo_f2: f64,
    pub apfel_f2: f64,
    pub apfel_fl: f64,
    pub apfel_xf3: f64,
    pub f2_absolute_difference: f64,
    pub f2_relative_difference: Option<f64>,
    pub lo_order: PerturbativeOrder,
    pub apfel_order: PerturbativeOrder,
    pub pdf_set: String,
    pub pdf_member: i32,
    pub mu_f_over_q: f64,
    pub mu_r_over_q: f64,
    pub apfelxx_version: Option<String>,
    pub lhapdf_version: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct StructureFunctionValidationReport {
    pub metadata: StructureFunctionValidationMetadata,
    pub rows: Vec<StructureFunctionValidationRow>,
}

impl StructureFunctionValidationReport {
    /// Revalidate a report immediately before artifact generation.
    pub fn validate(&self) -> Result<(), StructureFunctionValidationError> {
        if self.metadata.schema_version != STRUCTURE_FUNCTION_SCHEMA_VERSION {
            return Err(StructureFunctionValidationError::InvalidReport {
                message: format!(
                    "schema version is {}, expected {}",
                    self.metadata.schema_version, STRUCTURE_FUNCTION_SCHEMA_VERSION
                ),
            });
        }
        if self.metadata.grid.x_values != VALIDATION_X_VALUES
            || self.metadata.grid.q2_values_gev2 != VALIDATION_Q2_VALUES_GEV2
        {
            return Err(StructureFunctionValidationError::InvalidReport {
                message: "grid metadata does not match the fixed validation grid".to_owned(),
            });
        }
        if self.metadata.row_count != VALIDATION_POINT_COUNT
            || self.rows.len() != VALIDATION_POINT_COUNT
        {
            return Err(StructureFunctionValidationError::InvalidReport {
                message: format!(
                    "expected {VALIDATION_POINT_COUNT} rows, metadata declares {} and report contains {}",
                    self.metadata.row_count,
                    self.rows.len()
                ),
            });
        }
        if self.metadata.f2_difference.absolute != F2_ABSOLUTE_DIFFERENCE_DEFINITION
            || self.metadata.f2_difference.relative != F2_RELATIVE_DIFFERENCE_DEFINITION
            || self.metadata.f2_difference.zero_denominator != F2_ZERO_DENOMINATOR_POLICY
        {
            return Err(StructureFunctionValidationError::InvalidReport {
                message: "F2 difference convention metadata was modified".to_owned(),
            });
        }

        for (index, row) in self.rows.iter().enumerate() {
            let x_index = index / VALIDATION_Q2_VALUES_GEV2.len();
            let q2_index = index % VALIDATION_Q2_VALUES_GEV2.len();
            let expected_x = VALIDATION_X_VALUES[x_index];
            let expected_q2 = VALIDATION_Q2_VALUES_GEV2[q2_index];
            if row.x != expected_x || row.q2 != expected_q2 {
                return Err(StructureFunctionValidationError::InvalidReport {
                    message: format!(
                        "row {index} is at ({}, {}), expected ({expected_x}, {expected_q2})",
                        row.x, row.q2
                    ),
                });
            }
            validate_row_values(row)?;
            validate_row_metadata(row, &self.metadata)?;
        }
        Ok(())
    }
}

#[derive(Debug)]
pub enum StructureFunctionValidationError {
    InvalidConfiguration {
        field: &'static str,
        value: String,
        requirement: &'static str,
    },
    Provider {
        backend: StructureFunctionBackend,
        x: f64,
        q2: f64,
        source: StructureFunctionProviderError,
    },
    MetadataMismatch {
        backend: StructureFunctionBackend,
        field: &'static str,
        expected: String,
        actual: String,
        x: f64,
        q2: f64,
    },
    InconsistentPdfMetadata {
        field: &'static str,
        reference: String,
        candidate: String,
        x: f64,
        q2: f64,
    },
    NonFiniteDifference {
        quantity: &'static str,
        value: f64,
        x: f64,
        q2: f64,
    },
    InvalidReport {
        message: String,
    },
}

impl fmt::Display for StructureFunctionValidationError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidConfiguration {
                field,
                value,
                requirement,
            } => write!(
                formatter,
                "invalid validation configuration {field}='{value}': expected {requirement}"
            ),
            Self::Provider {
                backend,
                x,
                q2,
                source,
            } => write!(
                formatter,
                "{backend} evaluation failed at x={x}, Q²={q2} GeV²: {source}"
            ),
            Self::MetadataMismatch {
                backend,
                field,
                expected,
                actual,
                x,
                q2,
            } => write!(
                formatter,
                "{backend} metadata mismatch at x={x}, Q²={q2} GeV²: {field}='{actual}', expected '{expected}'"
            ),
            Self::InconsistentPdfMetadata {
                field,
                reference,
                candidate,
                x,
                q2,
            } => write!(
                formatter,
                "LO/APFEL PDF metadata mismatch at x={x}, Q²={q2} GeV²: {field} is '{reference}' versus '{candidate}'"
            ),
            Self::NonFiniteDifference {
                quantity,
                value,
                x,
                q2,
            } => write!(
                formatter,
                "calculated {quantity} is non-finite ({value}) at x={x}, Q²={q2} GeV²"
            ),
            Self::InvalidReport { message } => {
                write!(formatter, "invalid structure-function validation report: {message}")
            }
        }
    }
}

impl Error for StructureFunctionValidationError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Provider { source, .. } => Some(source),
            _ => None,
        }
    }
}

/// Compare APFEL with the direct LO provider over the exact required grid.
///
/// The reference always uses LO coefficients and unit scales, independently of
/// the candidate APFEL order and scale ratios.
pub fn compare_structure_function_grid(
    lo_provider: &dyn StructureFunctionProvider,
    apfel_provider: &dyn StructureFunctionProvider,
    configuration: &StructureFunctionValidationConfig,
) -> Result<StructureFunctionValidationReport, StructureFunctionValidationError> {
    configuration.validate()?;

    let mut rows = Vec::with_capacity(VALIDATION_POINT_COUNT);
    let mut first_lo_metadata: Option<StructureFunctionMetadata> = None;
    let mut first_apfel_metadata: Option<StructureFunctionMetadata> = None;

    for x in VALIDATION_X_VALUES {
        for q2 in VALIDATION_Q2_VALUES_GEV2 {
            let lo_request = StructureFunctionRequest::electromagnetic_nc(
                x,
                q2,
                PerturbativeOrder::Lo,
                configuration.pdf_set.clone(),
                configuration.pdf_member,
            );
            let mut apfel_request = StructureFunctionRequest::electromagnetic_nc(
                x,
                q2,
                configuration.apfel_order,
                configuration.pdf_set.clone(),
                configuration.pdf_member,
            );
            apfel_request.mu_f_over_q = configuration.mu_f_over_q;
            apfel_request.mu_r_over_q = configuration.mu_r_over_q;

            let lo = evaluate_provider(lo_provider, StructureFunctionBackend::LoPdf, &lo_request)?;
            let apfel = evaluate_provider(
                apfel_provider,
                StructureFunctionBackend::Apfel,
                &apfel_request,
            )?;

            validate_result_metadata(&lo, &lo_request, StructureFunctionBackend::LoPdf, x, q2)?;
            validate_result_metadata(
                &apfel,
                &apfel_request,
                StructureFunctionBackend::Apfel,
                x,
                q2,
            )?;
            validate_pdf_metadata_match(&lo.metadata, &apfel.metadata, x, q2)?;
            validate_grid_metadata_consistency(
                &mut first_lo_metadata,
                &lo.metadata,
                StructureFunctionBackend::LoPdf,
                x,
                q2,
            )?;
            validate_grid_metadata_consistency(
                &mut first_apfel_metadata,
                &apfel.metadata,
                StructureFunctionBackend::Apfel,
                x,
                q2,
            )?;

            let absolute_difference = (apfel.f2 - lo.f2).abs();
            if !absolute_difference.is_finite() {
                return Err(StructureFunctionValidationError::NonFiniteDifference {
                    quantity: "F2 absolute difference",
                    value: absolute_difference,
                    x,
                    q2,
                });
            }
            let relative_difference = if lo.f2 == 0.0 {
                None
            } else {
                let value = absolute_difference / lo.f2.abs();
                if !value.is_finite() {
                    return Err(StructureFunctionValidationError::NonFiniteDifference {
                        quantity: "F2 relative difference",
                        value,
                        x,
                        q2,
                    });
                }
                Some(value)
            };

            rows.push(StructureFunctionValidationRow {
                x,
                q2,
                lo_f2: lo.f2,
                apfel_f2: apfel.f2,
                apfel_fl: apfel.fl,
                apfel_xf3: apfel.xf3,
                f2_absolute_difference: absolute_difference,
                f2_relative_difference: relative_difference,
                lo_order: lo.metadata.order,
                apfel_order: apfel.metadata.order,
                pdf_set: configuration.pdf_set.clone(),
                pdf_member: configuration.pdf_member,
                mu_f_over_q: configuration.mu_f_over_q,
                mu_r_over_q: configuration.mu_r_over_q,
                apfelxx_version: apfel.metadata.apfelxx_version.clone(),
                lhapdf_version: apfel.metadata.lhapdf_version.clone(),
            });
        }
    }

    let lo_metadata = first_lo_metadata.expect("the fixed grid is non-empty");
    let apfel_metadata = first_apfel_metadata.expect("the fixed grid is non-empty");
    let metadata = StructureFunctionValidationMetadata {
        schema_version: STRUCTURE_FUNCTION_SCHEMA_VERSION,
        application_version: env!("CARGO_PKG_VERSION").to_owned(),
        process: StructureFunctionProcess::NcDis,
        projectile: DisProjectile::Electron,
        target: DisTarget::Proton,
        pdf: ValidationPdfMetadata {
            set: configuration.pdf_set.clone(),
            member: configuration.pdf_member,
            order_qcd: apfel_metadata.pdf_order_qcd,
            data_version: apfel_metadata.pdf_data_version,
        },
        reference: backend_metadata(&lo_metadata),
        candidate: backend_metadata(&apfel_metadata),
        grid: ValidationGridMetadata {
            x_values: VALIDATION_X_VALUES,
            q2_values_gev2: VALIDATION_Q2_VALUES_GEV2,
            ordering: "x ascending, then Q2 ascending".to_owned(),
        },
        units: ValidationUnitMetadata {
            q2: "GeV^2".to_owned(),
            structure_functions: "dimensionless".to_owned(),
            differences: "dimensionless".to_owned(),
        },
        f2_difference: F2DifferenceConvention {
            absolute: F2_ABSOLUTE_DIFFERENCE_DEFINITION.to_owned(),
            relative: F2_RELATIVE_DIFFERENCE_DEFINITION.to_owned(),
            zero_denominator: F2_ZERO_DENOMINATOR_POLICY.to_owned(),
        },
        row_count: rows.len(),
    };
    let report = StructureFunctionValidationReport { metadata, rows };
    report.validate()?;
    Ok(report)
}

fn evaluate_provider(
    provider: &dyn StructureFunctionProvider,
    backend: StructureFunctionBackend,
    request: &StructureFunctionRequest,
) -> Result<StructureFunctionResult, StructureFunctionValidationError> {
    provider
        .evaluate(request)
        .map_err(|source| StructureFunctionValidationError::Provider {
            backend,
            x: request.x,
            q2: request.q2,
            source,
        })
}

fn validate_result_metadata(
    result: &StructureFunctionResult,
    request: &StructureFunctionRequest,
    backend: StructureFunctionBackend,
    x: f64,
    q2: f64,
) -> Result<(), StructureFunctionValidationError> {
    result
        .validate_finite()
        .map_err(|source| StructureFunctionValidationError::Provider {
            backend,
            x,
            q2,
            source,
        })?;

    expect_metadata(
        backend,
        "backend",
        &backend.to_string(),
        &result.metadata.backend.to_string(),
        x,
        q2,
    )?;
    expect_metadata(
        backend,
        "pdf_set",
        &request.pdf_set,
        &result.metadata.pdf_set,
        x,
        q2,
    )?;
    expect_metadata(
        backend,
        "pdf_member",
        &request.pdf_member.to_string(),
        &result.metadata.pdf_member.to_string(),
        x,
        q2,
    )?;
    expect_metadata(
        backend,
        "order",
        request.order.as_str(),
        result.metadata.order.as_str(),
        x,
        q2,
    )?;
    expect_metadata(
        backend,
        "process",
        &request.process.to_string(),
        &result.metadata.process.to_string(),
        x,
        q2,
    )?;
    expect_metadata(
        backend,
        "projectile",
        &request.projectile.to_string(),
        &result.metadata.projectile.to_string(),
        x,
        q2,
    )?;
    expect_metadata(
        backend,
        "target",
        &request.target.to_string(),
        &result.metadata.target.to_string(),
        x,
        q2,
    )?;
    expect_scale(
        backend,
        "mu_f_over_q",
        request.mu_f_over_q,
        result.metadata.mu_f_over_q,
        x,
        q2,
    )?;
    expect_scale(
        backend,
        "mu_r_over_q",
        request.mu_r_over_q,
        result.metadata.mu_r_over_q,
        x,
        q2,
    )?;
    if result.metadata.scheme.trim().is_empty() {
        return metadata_error(backend, "scheme", "a non-empty value", "", x, q2);
    }
    if result.metadata.electromagnetic_mode.trim().is_empty() {
        return metadata_error(
            backend,
            "electromagnetic_mode",
            "a non-empty value",
            "",
            x,
            q2,
        );
    }

    match backend {
        StructureFunctionBackend::LoPdf => {
            if result.metadata.apfelxx_version.is_some() {
                return metadata_error(
                    backend,
                    "apfelxx_version",
                    "missing for the direct LO backend",
                    result
                        .metadata
                        .apfelxx_version
                        .as_deref()
                        .unwrap_or_default(),
                    x,
                    q2,
                );
            }
        }
        StructureFunctionBackend::Apfel => {
            expect_non_empty_version(
                backend,
                "apfelxx_version",
                result.metadata.apfelxx_version.as_deref(),
                x,
                q2,
            )?;
            expect_non_empty_version(
                backend,
                "lhapdf_version",
                result.metadata.lhapdf_version.as_deref(),
                x,
                q2,
            )?;
        }
        StructureFunctionBackend::Surrogate => {
            if result.metadata.apfelxx_version.is_some() {
                return metadata_error(
                    backend,
                    "apfelxx_version",
                    "missing for the surrogate backend",
                    result
                        .metadata
                        .apfelxx_version
                        .as_deref()
                        .unwrap_or_default(),
                    x,
                    q2,
                );
            }
        }
    }
    Ok(())
}

fn validate_pdf_metadata_match(
    reference: &StructureFunctionMetadata,
    candidate: &StructureFunctionMetadata,
    x: f64,
    q2: f64,
) -> Result<(), StructureFunctionValidationError> {
    for (field, reference_value, candidate_value) in [
        (
            "pdf_order_qcd",
            reference.pdf_order_qcd.to_string(),
            candidate.pdf_order_qcd.to_string(),
        ),
        (
            "pdf_data_version",
            reference.pdf_data_version.to_string(),
            candidate.pdf_data_version.to_string(),
        ),
    ] {
        if reference_value != candidate_value {
            return Err(StructureFunctionValidationError::InconsistentPdfMetadata {
                field,
                reference: reference_value,
                candidate: candidate_value,
                x,
                q2,
            });
        }
    }
    Ok(())
}

fn validate_grid_metadata_consistency(
    first: &mut Option<StructureFunctionMetadata>,
    current: &StructureFunctionMetadata,
    backend: StructureFunctionBackend,
    x: f64,
    q2: f64,
) -> Result<(), StructureFunctionValidationError> {
    if let Some(expected) = first {
        if expected != current {
            return Err(StructureFunctionValidationError::MetadataMismatch {
                backend,
                field: "complete metadata",
                expected: format!("{expected:?}"),
                actual: format!("{current:?}"),
                x,
                q2,
            });
        }
    } else {
        *first = Some(current.clone());
    }
    Ok(())
}

fn backend_metadata(metadata: &StructureFunctionMetadata) -> ValidationBackendMetadata {
    ValidationBackendMetadata {
        backend: metadata.backend,
        order: metadata.order,
        scheme: metadata.scheme.clone(),
        electromagnetic_mode: metadata.electromagnetic_mode.clone(),
        apfelxx_version: metadata.apfelxx_version.clone(),
        lhapdf_version: metadata.lhapdf_version.clone(),
        mu_f_over_q: metadata.mu_f_over_q,
        mu_r_over_q: metadata.mu_r_over_q,
    }
}

fn validate_row_values(
    row: &StructureFunctionValidationRow,
) -> Result<(), StructureFunctionValidationError> {
    for (quantity, value) in [
        ("LO F2", row.lo_f2),
        ("APFEL F2", row.apfel_f2),
        ("APFEL FL", row.apfel_fl),
        ("APFEL xF3", row.apfel_xf3),
        ("F2 absolute difference", row.f2_absolute_difference),
    ] {
        if !value.is_finite() {
            return Err(StructureFunctionValidationError::NonFiniteDifference {
                quantity,
                value,
                x: row.x,
                q2: row.q2,
            });
        }
    }
    if let Some(value) = row.f2_relative_difference {
        if !value.is_finite() {
            return Err(StructureFunctionValidationError::NonFiniteDifference {
                quantity: "F2 relative difference",
                value,
                x: row.x,
                q2: row.q2,
            });
        }
    }

    let expected_absolute = (row.apfel_f2 - row.lo_f2).abs();
    let expected_relative = if row.lo_f2 == 0.0 {
        None
    } else {
        Some(expected_absolute / row.lo_f2.abs())
    };
    if row.f2_absolute_difference != expected_absolute
        || row.f2_relative_difference != expected_relative
    {
        return Err(StructureFunctionValidationError::InvalidReport {
            message: format!(
                "row at x={}, Q²={} does not follow the declared difference convention",
                row.x, row.q2
            ),
        });
    }
    Ok(())
}

fn validate_row_metadata(
    row: &StructureFunctionValidationRow,
    metadata: &StructureFunctionValidationMetadata,
) -> Result<(), StructureFunctionValidationError> {
    if row.lo_order != metadata.reference.order
        || row.apfel_order != metadata.candidate.order
        || row.pdf_set != metadata.pdf.set
        || row.pdf_member != metadata.pdf.member
        || row.mu_f_over_q != metadata.candidate.mu_f_over_q
        || row.mu_r_over_q != metadata.candidate.mu_r_over_q
        || row.apfelxx_version != metadata.candidate.apfelxx_version
        || row.lhapdf_version != metadata.candidate.lhapdf_version
    {
        return Err(StructureFunctionValidationError::InvalidReport {
            message: format!(
                "row metadata at x={}, Q²={} disagrees with report metadata",
                row.x, row.q2
            ),
        });
    }
    Ok(())
}

fn validate_scale(field: &'static str, value: f64) -> Result<(), StructureFunctionValidationError> {
    if !value.is_finite() || value <= 0.0 {
        return Err(StructureFunctionValidationError::InvalidConfiguration {
            field,
            value: value.to_string(),
            requirement: "a finite, positive ratio",
        });
    }
    Ok(())
}

fn expect_metadata(
    backend: StructureFunctionBackend,
    field: &'static str,
    expected: &str,
    actual: &str,
    x: f64,
    q2: f64,
) -> Result<(), StructureFunctionValidationError> {
    if expected == actual {
        Ok(())
    } else {
        metadata_error(backend, field, expected, actual, x, q2)
    }
}

fn expect_scale(
    backend: StructureFunctionBackend,
    field: &'static str,
    expected: f64,
    actual: f64,
    x: f64,
    q2: f64,
) -> Result<(), StructureFunctionValidationError> {
    let scale = expected.abs().max(actual.abs()).max(1.0);
    if actual.is_finite() && (actual - expected).abs() <= 8.0 * f64::EPSILON * scale {
        Ok(())
    } else {
        metadata_error(
            backend,
            field,
            &expected.to_string(),
            &actual.to_string(),
            x,
            q2,
        )
    }
}

fn expect_non_empty_version(
    backend: StructureFunctionBackend,
    field: &'static str,
    actual: Option<&str>,
    x: f64,
    q2: f64,
) -> Result<(), StructureFunctionValidationError> {
    match actual {
        Some(value) if !value.trim().is_empty() => Ok(()),
        Some(value) => metadata_error(backend, field, "a non-empty version", value, x, q2),
        None => metadata_error(backend, field, "a non-empty version", "missing", x, q2),
    }
}

fn metadata_error<T>(
    backend: StructureFunctionBackend,
    field: &'static str,
    expected: &str,
    actual: &str,
    x: f64,
    q2: f64,
) -> Result<T, StructureFunctionValidationError> {
    Err(StructureFunctionValidationError::MetadataMismatch {
        backend,
        field,
        expected: expected.to_owned(),
        actual: actual.to_owned(),
        x,
        q2,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    struct MockProvider {
        backend: StructureFunctionBackend,
        f2: f64,
        zero_first_lo_point: bool,
        wrong_set: bool,
    }

    impl StructureFunctionProvider for MockProvider {
        fn evaluate(
            &self,
            request: &StructureFunctionRequest,
        ) -> Result<StructureFunctionResult, StructureFunctionProviderError> {
            request.validate()?;
            let f2 = if self.zero_first_lo_point
                && request.x == VALIDATION_X_VALUES[0]
                && request.q2 == VALIDATION_Q2_VALUES_GEV2[0]
            {
                0.0
            } else {
                self.f2
            };
            let metadata = StructureFunctionMetadata {
                backend: self.backend,
                apfelxx_version: (self.backend == StructureFunctionBackend::Apfel)
                    .then(|| "4.8.0".to_owned()),
                lhapdf_version: (self.backend == StructureFunctionBackend::Apfel)
                    .then(|| "6.5.6".to_owned()),
                pdf_set: if self.wrong_set {
                    "WrongSet".to_owned()
                } else {
                    request.pdf_set.clone()
                },
                pdf_member: request.pdf_member,
                pdf_order_qcd: 1,
                pdf_data_version: 7,
                order: request.order,
                process: request.process,
                projectile: request.projectile,
                target: request.target,
                mu_f_over_q: request.mu_f_over_q,
                mu_r_over_q: request.mu_r_over_q,
                scheme: match self.backend {
                    StructureFunctionBackend::LoPdf => "lo_parton_model",
                    StructureFunctionBackend::Apfel => "ZM-VFNS",
                    StructureFunctionBackend::Surrogate => "surrogate",
                }
                .to_owned(),
                electromagnetic_mode: "photon_exchange".to_owned(),
                os_arch: None,
                rust_version: None,
                git_commit: None,
                git_dirty: None,
                pythia_version: None,
                hepmc_version: None,
                python_env_hash: None,
            };
            Ok(StructureFunctionResult {
                f2,
                fl: if self.backend == StructureFunctionBackend::Apfel {
                    0.1
                } else {
                    0.0
                },
                xf3: 0.0,
                metadata,
            })
        }
    }

    fn config() -> StructureFunctionValidationConfig {
        StructureFunctionValidationConfig::new("CT18NLO", 0, PerturbativeOrder::Nlo)
    }

    fn lo(f2: f64) -> MockProvider {
        MockProvider {
            backend: StructureFunctionBackend::LoPdf,
            f2,
            zero_first_lo_point: false,
            wrong_set: false,
        }
    }

    fn apfel(f2: f64) -> MockProvider {
        MockProvider {
            backend: StructureFunctionBackend::Apfel,
            f2,
            zero_first_lo_point: false,
            wrong_set: false,
        }
    }

    #[test]
    fn fixed_grid_is_exact_complete_and_lexicographic() {
        let report = compare_structure_function_grid(&lo(2.0), &apfel(2.5), &config()).unwrap();

        assert_eq!(report.rows.len(), 20);
        assert_eq!(report.metadata.grid.x_values, VALIDATION_X_VALUES);
        assert_eq!(
            report.metadata.grid.q2_values_gev2,
            VALIDATION_Q2_VALUES_GEV2
        );
        for (index, row) in report.rows.iter().enumerate() {
            assert_eq!(
                row.x,
                VALIDATION_X_VALUES[index / VALIDATION_Q2_VALUES_GEV2.len()]
            );
            assert_eq!(
                row.q2,
                VALIDATION_Q2_VALUES_GEV2[index % VALIDATION_Q2_VALUES_GEV2.len()]
            );
        }
    }

    #[test]
    fn implements_exact_absolute_and_relative_difference_conventions() {
        let report = compare_structure_function_grid(&lo(2.0), &apfel(2.5), &config()).unwrap();

        for row in &report.rows {
            assert_eq!(row.f2_absolute_difference, 0.5);
            assert_eq!(row.f2_relative_difference, Some(0.25));
        }
        assert_eq!(
            report.metadata.f2_difference.relative,
            F2_RELATIVE_DIFFERENCE_DEFINITION
        );
    }

    #[test]
    fn exact_zero_denominator_is_undefined_without_epsilon_substitution() {
        let lo = MockProvider {
            zero_first_lo_point: true,
            ..lo(2.0)
        };
        let report = compare_structure_function_grid(&lo, &apfel(2.5), &config()).unwrap();

        assert_eq!(report.rows[0].lo_f2, 0.0);
        assert_eq!(report.rows[0].f2_absolute_difference, 2.5);
        assert_eq!(report.rows[0].f2_relative_difference, None);
        assert_eq!(report.rows[1].f2_relative_difference, Some(0.25));
    }

    #[test]
    fn baseline_is_always_lo_with_unit_scales() {
        struct RequestRecorder(std::cell::RefCell<Vec<StructureFunctionRequest>>);

        impl StructureFunctionProvider for RequestRecorder {
            fn evaluate(
                &self,
                request: &StructureFunctionRequest,
            ) -> Result<StructureFunctionResult, StructureFunctionProviderError> {
                self.0.borrow_mut().push(request.clone());
                lo(1.0).evaluate(request)
            }
        }

        let recorder = RequestRecorder(std::cell::RefCell::new(Vec::new()));
        let mut configuration = config();
        configuration.mu_f_over_q = 0.5;
        configuration.mu_r_over_q = 2.0;
        compare_structure_function_grid(&recorder, &apfel(1.1), &configuration).unwrap();

        for request in recorder.0.borrow().iter() {
            assert_eq!(request.order, PerturbativeOrder::Lo);
            assert_eq!((request.mu_f_over_q, request.mu_r_over_q), (1.0, 1.0));
        }
    }

    #[test]
    fn rejects_invalid_configuration_before_calling_providers() {
        let mut configuration = config();
        configuration.pdf_member = -1;
        assert!(matches!(
            compare_structure_function_grid(&lo(1.0), &apfel(1.1), &configuration),
            Err(StructureFunctionValidationError::InvalidConfiguration { .. })
        ));

        configuration = config();
        configuration.mu_r_over_q = f64::NAN;
        assert!(matches!(
            compare_structure_function_grid(&lo(1.0), &apfel(1.1), &configuration),
            Err(StructureFunctionValidationError::InvalidConfiguration { .. })
        ));
    }

    #[test]
    fn rejects_backend_and_pdf_metadata_mismatches() {
        let wrong = MockProvider {
            wrong_set: true,
            ..apfel(1.1)
        };
        assert!(matches!(
            compare_structure_function_grid(&lo(1.0), &wrong, &config()),
            Err(StructureFunctionValidationError::MetadataMismatch {
                backend: StructureFunctionBackend::Apfel,
                field: "pdf_set",
                ..
            })
        ));

        let wrong_backend = MockProvider {
            backend: StructureFunctionBackend::LoPdf,
            ..apfel(1.1)
        };
        assert!(matches!(
            compare_structure_function_grid(&lo(1.0), &wrong_backend, &config()),
            Err(StructureFunctionValidationError::MetadataMismatch {
                field: "backend",
                ..
            })
        ));
    }

    #[test]
    fn serializable_report_round_trips_and_preserves_null() {
        let lo = MockProvider {
            zero_first_lo_point: true,
            ..lo(2.0)
        };
        let report = compare_structure_function_grid(&lo, &apfel(2.5), &config()).unwrap();
        let json = serde_json::to_string(&report).unwrap();
        let decoded: StructureFunctionValidationReport = serde_json::from_str(&json).unwrap();

        assert_eq!(decoded, report);
        assert_eq!(decoded.rows[0].f2_relative_difference, None);
        assert!(json.contains("\"f2_relative_difference\":null"));
    }

    #[test]
    fn report_validation_detects_tampered_differences_and_ordering() {
        let mut report = compare_structure_function_grid(&lo(2.0), &apfel(2.5), &config()).unwrap();
        report.rows[0].f2_relative_difference = Some(999.0);
        assert!(matches!(
            report.validate(),
            Err(StructureFunctionValidationError::InvalidReport { .. })
        ));

        let mut report = compare_structure_function_grid(&lo(2.0), &apfel(2.5), &config()).unwrap();
        report.rows.swap(0, 1);
        assert!(matches!(
            report.validate(),
            Err(StructureFunctionValidationError::InvalidReport { .. })
        ));
    }
}
