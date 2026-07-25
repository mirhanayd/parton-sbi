//! APFEL++ structure functions through a versioned JSON subprocess protocol.
//!
//! One request is written to the backend's standard input and exactly one JSON
//! response is read from standard output. Backend diagnostics belong on
//! standard error so they cannot corrupt the protocol document.

use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use serde::{Deserialize, Serialize};

use super::structure_function_provider::{
    PerturbativeOrder, StructureFunctionMetadata, StructureFunctionProvider,
    StructureFunctionProviderError, StructureFunctionRequest, StructureFunctionResult,
    PHOTON_EXCHANGE_MODE, STRUCTURE_FUNCTION_SCHEMA_VERSION,
};

/// Default backend location when commands are run from the crate root.
pub const DEFAULT_APFEL_BACKEND_PATH: &str = "physics-engine/build/apfel_cli";

/// Factorization scheme configured by the phase-three APFEL++ backend.
pub const APFEL_ZM_VFNS_SCHEME: &str = "ZM-VFNS";

const MAX_DIAGNOSTIC_BYTES: usize = 4096;

/// Structured error supplied by the APFEL++ protocol.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ApfelProtocolError {
    pub code: String,
    pub message: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub hint: Option<String>,
}

/// Schema-v1 response. Optional fields are validated against `success` before
/// a public [`StructureFunctionResult`] can be constructed.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ApfelProtocolResponse {
    pub schema_version: u32,
    pub success: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub f2: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub fl: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub xf3: Option<f64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub metadata: Option<StructureFunctionMetadata>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub error: Option<ApfelProtocolError>,
}

/// APFEL++ subprocess implementation of [`StructureFunctionProvider`].
///
/// Construction does not probe the executable. Missing or non-executable
/// backends are reported on evaluation, and no LO fallback is attempted.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ApfelStructureFunctionProvider {
    executable: PathBuf,
}

impl ApfelStructureFunctionProvider {
    #[must_use]
    pub fn new(executable: impl Into<PathBuf>) -> Self {
        Self {
            executable: executable.into(),
        }
    }

    #[must_use]
    pub fn executable(&self) -> &Path {
        &self.executable
    }

    fn exchange(
        &self,
        request: &StructureFunctionRequest,
    ) -> Result<StructureFunctionResult, StructureFunctionProviderError> {
        let mut request_json = serde_json::to_vec(request)
            .map_err(|source| StructureFunctionProviderError::RequestSerialization { source })?;
        request_json.push(b'\n');

        let mut child = Command::new(&self.executable)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|source| self.map_spawn_error(source))?;

        let Some(mut stdin) = child.stdin.take() else {
            let _ = child.kill();
            let _ = child.wait();
            return Err(StructureFunctionProviderError::InvalidResponse {
                message: "failed to open the APFEL++ backend standard input".to_owned(),
            });
        };
        if let Err(source) = stdin.write_all(&request_json) {
            drop(stdin);
            let _ = child.wait();
            return Err(StructureFunctionProviderError::BackendIo {
                executable: self.executable.clone(),
                operation: "writing the schema-v1 request",
                source,
            });
        }
        drop(stdin);

        let output = child.wait_with_output().map_err(|source| {
            StructureFunctionProviderError::BackendIo {
                executable: self.executable.clone(),
                operation: "waiting for the response",
                source,
            }
        })?;
        decode_output(
            request,
            &self.executable,
            output.status.success(),
            output.status.code(),
            &output.stdout,
            &output.stderr,
        )
    }

    fn map_spawn_error(&self, source: io::Error) -> StructureFunctionProviderError {
        if source.kind() == io::ErrorKind::NotFound {
            StructureFunctionProviderError::BackendUnavailable {
                executable: self.executable.clone(),
                source,
            }
        } else {
            StructureFunctionProviderError::BackendIo {
                executable: self.executable.clone(),
                operation: "starting the process",
                source,
            }
        }
    }
}

impl Default for ApfelStructureFunctionProvider {
    fn default() -> Self {
        Self::new(DEFAULT_APFEL_BACKEND_PATH)
    }
}

impl StructureFunctionProvider for ApfelStructureFunctionProvider {
    fn evaluate(
        &self,
        request: &StructureFunctionRequest,
    ) -> Result<StructureFunctionResult, StructureFunctionProviderError> {
        request.validate()?;
        self.exchange(request)
    }
}

fn decode_output(
    request: &StructureFunctionRequest,
    executable: &Path,
    process_succeeded: bool,
    status: Option<i32>,
    stdout: &[u8],
    stderr: &[u8],
) -> Result<StructureFunctionResult, StructureFunctionProviderError> {
    let stdout_text = truncate_diagnostic(stdout);
    let stderr_text = truncate_diagnostic(stderr);
    let response = match serde_json::from_slice::<ApfelProtocolResponse>(stdout) {
        Ok(response) => response,
        Err(_source) if !process_succeeded => {
            return Err(StructureFunctionProviderError::BackendExited {
                executable: executable.to_owned(),
                status,
                stdout: stdout_text,
                stderr: stderr_text,
            });
        }
        Err(source) => {
            return Err(StructureFunctionProviderError::ResponseDeserialization {
                source,
                stdout: stdout_text,
                stderr: stderr_text,
            });
        }
    };

    interpret_response(
        request,
        executable,
        process_succeeded,
        status,
        response,
        stdout_text,
        stderr_text,
    )
}

fn interpret_response(
    request: &StructureFunctionRequest,
    executable: &Path,
    process_succeeded: bool,
    status: Option<i32>,
    response: ApfelProtocolResponse,
    stdout: String,
    stderr: String,
) -> Result<StructureFunctionResult, StructureFunctionProviderError> {
    if response.schema_version != STRUCTURE_FUNCTION_SCHEMA_VERSION {
        return Err(StructureFunctionProviderError::SchemaMismatch {
            expected: STRUCTURE_FUNCTION_SCHEMA_VERSION,
            actual: response.schema_version,
        });
    }

    if !response.success {
        if response.f2.is_some()
            || response.fl.is_some()
            || response.xf3.is_some()
            || response.metadata.is_some()
        {
            return Err(StructureFunctionProviderError::InvalidResponse {
                message: "a failure response must not contain physics results or metadata"
                    .to_owned(),
            });
        }
        let error =
            response
                .error
                .ok_or_else(|| StructureFunctionProviderError::InvalidResponse {
                    message: "a failure response must contain an error object".to_owned(),
                })?;
        if error.code.trim().is_empty() || error.message.trim().is_empty() {
            return Err(StructureFunctionProviderError::InvalidResponse {
                message: "backend error code and message must be non-empty".to_owned(),
            });
        }
        return Err(StructureFunctionProviderError::BackendRejected {
            code: error.code,
            message: error.message,
            hint: error.hint,
            status,
        });
    }

    if response.error.is_some() {
        return Err(StructureFunctionProviderError::InvalidResponse {
            message: "a success response must not contain an error object".to_owned(),
        });
    }
    if !process_succeeded {
        return Err(StructureFunctionProviderError::BackendExited {
            executable: executable.to_owned(),
            status,
            stdout,
            stderr,
        });
    }

    let f2 = required_result(response.f2, "f2")?;
    let fl = required_result(response.fl, "fl")?;
    let xf3 = required_result(response.xf3, "xf3")?;
    let metadata =
        response
            .metadata
            .ok_or_else(|| StructureFunctionProviderError::InvalidResponse {
                message: "a success response is missing metadata".to_owned(),
            })?;
    let result = StructureFunctionResult {
        f2,
        fl,
        xf3,
        metadata,
    };
    result.validate_finite()?;
    validate_metadata(request, &result.metadata)?;
    Ok(result)
}

fn required_result(
    value: Option<f64>,
    field: &'static str,
) -> Result<f64, StructureFunctionProviderError> {
    value.ok_or_else(|| StructureFunctionProviderError::InvalidResponse {
        message: format!("a success response is missing {field}"),
    })
}

fn validate_metadata(
    request: &StructureFunctionRequest,
    metadata: &StructureFunctionMetadata,
) -> Result<(), StructureFunctionProviderError> {
    expect_metadata("backend", "apfel", &metadata.backend.to_string())?;
    expect_non_empty_version("apfelxx_version", metadata.apfelxx_version.as_deref())?;
    expect_non_empty_version("lhapdf_version", metadata.lhapdf_version.as_deref())?;
    expect_metadata("pdf_set", &request.pdf_set, &metadata.pdf_set)?;
    expect_metadata(
        "pdf_member",
        &request.pdf_member.to_string(),
        &metadata.pdf_member.to_string(),
    )?;
    expect_metadata("order", request.order.as_str(), metadata.order.as_str())?;
    expect_metadata(
        "process",
        &request.process.to_string(),
        &metadata.process.to_string(),
    )?;
    expect_metadata(
        "projectile",
        &request.projectile.to_string(),
        &metadata.projectile.to_string(),
    )?;
    expect_metadata(
        "target",
        &request.target.to_string(),
        &metadata.target.to_string(),
    )?;
    expect_scale("mu_f_over_q", request.mu_f_over_q, metadata.mu_f_over_q)?;
    expect_scale("mu_r_over_q", request.mu_r_over_q, metadata.mu_r_over_q)?;
    expect_metadata("scheme", APFEL_ZM_VFNS_SCHEME, &metadata.scheme)?;
    expect_metadata(
        "electromagnetic_mode",
        PHOTON_EXCHANGE_MODE,
        &metadata.electromagnetic_mode,
    )?;

    let minimum_pdf_order = match request.order {
        PerturbativeOrder::Lo => 0,
        PerturbativeOrder::Nlo => 1,
    };
    if metadata.pdf_order_qcd < minimum_pdf_order {
        return Err(StructureFunctionProviderError::MetadataMismatch {
            field: "pdf_order_qcd",
            expected: format!(">={minimum_pdf_order} for {} coefficients", request.order),
            actual: metadata.pdf_order_qcd.to_string(),
        });
    }
    Ok(())
}

fn expect_non_empty_version(
    field: &'static str,
    actual: Option<&str>,
) -> Result<(), StructureFunctionProviderError> {
    match actual {
        Some(version) if !version.trim().is_empty() => Ok(()),
        Some(version) => Err(StructureFunctionProviderError::MetadataMismatch {
            field,
            expected: "a non-empty version string".to_owned(),
            actual: version.to_owned(),
        }),
        None => Err(StructureFunctionProviderError::MetadataMismatch {
            field,
            expected: "a non-empty version string".to_owned(),
            actual: "missing".to_owned(),
        }),
    }
}

fn expect_metadata(
    field: &'static str,
    expected: &str,
    actual: &str,
) -> Result<(), StructureFunctionProviderError> {
    if expected != actual {
        return Err(StructureFunctionProviderError::MetadataMismatch {
            field,
            expected: expected.to_owned(),
            actual: actual.to_owned(),
        });
    }
    Ok(())
}

fn expect_scale(
    field: &'static str,
    expected: f64,
    actual: f64,
) -> Result<(), StructureFunctionProviderError> {
    let scale = expected.abs().max(actual.abs()).max(1.0);
    if !actual.is_finite() || (actual - expected).abs() > 8.0 * f64::EPSILON * scale {
        return Err(StructureFunctionProviderError::MetadataMismatch {
            field,
            expected: expected.to_string(),
            actual: actual.to_string(),
        });
    }
    Ok(())
}

fn truncate_diagnostic(bytes: &[u8]) -> String {
    let was_truncated = bytes.len() > MAX_DIAGNOSTIC_BYTES;
    let bytes = if was_truncated {
        &bytes[..MAX_DIAGNOSTIC_BYTES]
    } else {
        bytes
    };
    let mut text = String::from_utf8_lossy(bytes).into_owned();
    if was_truncated {
        text.push_str("... [truncated]");
    }
    text
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::physics::structure_function_provider::StructureFunctionBackend;

    fn request(order: PerturbativeOrder) -> StructureFunctionRequest {
        let set = match order {
            PerturbativeOrder::Lo => "CT18LO",
            PerturbativeOrder::Nlo => "CT18NLO",
        };
        StructureFunctionRequest::electromagnetic_nc(0.01, 100.0, order, set, 0)
    }

    fn metadata(request: &StructureFunctionRequest) -> StructureFunctionMetadata {
        StructureFunctionMetadata {
            backend: StructureFunctionBackend::Apfel,
            apfelxx_version: Some("4.0.0".to_owned()),
            lhapdf_version: Some("6.5.6".to_owned()),
            pdf_set: request.pdf_set.clone(),
            pdf_member: request.pdf_member,
            pdf_order_qcd: match request.order {
                PerturbativeOrder::Lo => 0,
                PerturbativeOrder::Nlo => 1,
            },
            pdf_data_version: 1,
            order: request.order,
            process: request.process,
            projectile: request.projectile,
            target: request.target,
            mu_f_over_q: request.mu_f_over_q,
            mu_r_over_q: request.mu_r_over_q,
            scheme: APFEL_ZM_VFNS_SCHEME.to_owned(),
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

    fn success_response(request: &StructureFunctionRequest) -> ApfelProtocolResponse {
        ApfelProtocolResponse {
            schema_version: STRUCTURE_FUNCTION_SCHEMA_VERSION,
            success: true,
            f2: Some(0.8),
            fl: Some(0.1),
            xf3: Some(0.0),
            metadata: Some(metadata(request)),
            error: None,
        }
    }

    fn interpret(
        request: &StructureFunctionRequest,
        response: ApfelProtocolResponse,
    ) -> Result<StructureFunctionResult, StructureFunctionProviderError> {
        interpret_response(
            request,
            Path::new(DEFAULT_APFEL_BACKEND_PATH),
            true,
            Some(0),
            response,
            String::new(),
            String::new(),
        )
    }

    #[test]
    fn protocol_success_response_round_trips() {
        let request = request(PerturbativeOrder::Nlo);
        let response = success_response(&request);
        let json = serde_json::to_value(&response).unwrap();

        assert_eq!(json["success"], true);
        assert_eq!(json["metadata"]["backend"], "apfel");
        assert_eq!(json["metadata"]["pdf_order_qcd"], 1);
        assert_eq!(json["metadata"]["pdf_data_version"], 1);
        assert_eq!(json["metadata"]["scheme"], "ZM-VFNS");
        assert_eq!(json["metadata"]["electromagnetic_mode"], "photon_exchange");
        assert_eq!(
            serde_json::from_value::<ApfelProtocolResponse>(json).unwrap(),
            response
        );
    }

    #[test]
    fn accepts_finite_success_with_matching_metadata() {
        let request = request(PerturbativeOrder::Nlo);
        let result = interpret(&request, success_response(&request)).unwrap();
        assert_eq!((result.f2, result.fl, result.xf3), (0.8, 0.1, 0.0));
        assert_eq!(result.metadata.pdf_order_qcd, 1);
    }

    #[test]
    fn preserves_structured_backend_errors_without_fallback() {
        let request = request(PerturbativeOrder::Nlo);
        let response = ApfelProtocolResponse {
            schema_version: STRUCTURE_FUNCTION_SCHEMA_VERSION,
            success: false,
            f2: None,
            fl: None,
            xf3: None,
            metadata: None,
            error: Some(ApfelProtocolError {
                code: "pdf_order_mismatch".to_owned(),
                message: "NLO coefficients require an NLO PDF".to_owned(),
                hint: Some("select CT18NLO".to_owned()),
            }),
        };

        let error = interpret_response(
            &request,
            Path::new(DEFAULT_APFEL_BACKEND_PATH),
            false,
            Some(2),
            response,
            String::new(),
            String::new(),
        )
        .unwrap_err();
        assert!(matches!(
            error,
            StructureFunctionProviderError::BackendRejected {
                ref code,
                status: Some(2),
                ..
            } if code == "pdf_order_mismatch"
        ));
    }

    #[test]
    fn rejects_wrong_schema_missing_fields_and_ambiguous_responses() {
        let request = request(PerturbativeOrder::Lo);
        let mut response = success_response(&request);
        response.schema_version = 2;
        assert!(matches!(
            interpret(&request, response),
            Err(StructureFunctionProviderError::SchemaMismatch { .. })
        ));

        let mut response = success_response(&request);
        response.fl = None;
        assert!(matches!(
            interpret(&request, response),
            Err(StructureFunctionProviderError::InvalidResponse { .. })
        ));

        let mut response = success_response(&request);
        response.error = Some(ApfelProtocolError {
            code: "unexpected".to_owned(),
            message: "ambiguous".to_owned(),
            hint: None,
        });
        assert!(matches!(
            interpret(&request, response),
            Err(StructureFunctionProviderError::InvalidResponse { .. })
        ));
    }

    #[test]
    fn rejects_non_finite_values_and_invalid_pdf_metadata() {
        let request = request(PerturbativeOrder::Nlo);
        let mut response = success_response(&request);
        response.f2 = Some(f64::NAN);
        assert!(matches!(
            interpret(&request, response),
            Err(StructureFunctionProviderError::NonFiniteResult { .. })
        ));

        let mut response = success_response(&request);
        response.metadata.as_mut().unwrap().pdf_data_version = -1;
        assert!(matches!(
            interpret(&request, response),
            Err(StructureFunctionProviderError::InvalidResponse { .. })
        ));

        let mut response = success_response(&request);
        response.metadata.as_mut().unwrap().pdf_order_qcd = 0;
        assert!(matches!(
            interpret(&request, response),
            Err(StructureFunctionProviderError::MetadataMismatch {
                field: "pdf_order_qcd",
                ..
            })
        ));
    }

    #[test]
    fn rejects_metadata_and_scale_mismatches() {
        let request = request(PerturbativeOrder::Nlo);
        let mut response = success_response(&request);
        response.metadata.as_mut().unwrap().pdf_set = "OTHER".to_owned();
        assert!(matches!(
            interpret(&request, response),
            Err(StructureFunctionProviderError::MetadataMismatch {
                field: "pdf_set",
                ..
            })
        ));

        let mut response = success_response(&request);
        response.metadata.as_mut().unwrap().mu_f_over_q = 2.0;
        assert!(matches!(
            interpret(&request, response),
            Err(StructureFunctionProviderError::MetadataMismatch {
                field: "mu_f_over_q",
                ..
            })
        ));

        let mut response = success_response(&request);
        response.metadata.as_mut().unwrap().apfelxx_version = Some(String::new());
        assert!(matches!(
            interpret(&request, response),
            Err(StructureFunctionProviderError::MetadataMismatch {
                field: "apfelxx_version",
                ..
            })
        ));
    }

    #[test]
    fn malformed_stdout_is_a_protocol_error() {
        let request = request(PerturbativeOrder::Lo);
        let error = decode_output(
            &request,
            Path::new(DEFAULT_APFEL_BACKEND_PATH),
            true,
            Some(0),
            b"LHAPDF chatter\n{not-json}",
            b"diagnostic",
        )
        .unwrap_err();
        assert!(matches!(
            error,
            StructureFunctionProviderError::ResponseDeserialization { .. }
        ));
    }

    #[test]
    fn missing_backend_has_actionable_error_and_never_falls_back() {
        let provider =
            ApfelStructureFunctionProvider::new("/definitely/not/a/real/quark-sim-apfel-backend");
        let error = provider
            .evaluate(&request(PerturbativeOrder::Lo))
            .unwrap_err();

        assert!(matches!(
            error,
            StructureFunctionProviderError::BackendUnavailable { .. }
        ));
        assert!(error.to_string().contains("setup_apfelxx_wsl.sh"));
    }
}
