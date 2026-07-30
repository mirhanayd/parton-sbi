use std::fs;
use std::path::PathBuf;

use parton_sbi::physics::{
    PdfTheta, PersistentApfelContext, PersistentApfelDiagnostics, PersistentApfelIdentities,
    PersistentApfelSupport, D1C_CONTROLLED_PYTHIA_NEXT_AUTHORIZED, D1C_D2_AUTHORIZED,
    D1C_PRODUCTION_EVENTS_AUTHORIZED, D1C_PROTOTYPE_AUTHORIZED, PERSISTENT_APFEL_ABI_VERSION,
    PERSISTENT_APFEL_CACHE_POLICY_VERSION, PERSISTENT_APFEL_MUTEX_POLICY_VERSION,
    PERSISTENT_APFEL_POLICY_VERSION, PERSISTENT_APFEL_PREPARATION_SCHEMA,
};
use serde::Serialize;

pub const PROTOTYPE_PERSISTENT_APFEL_HELP: &str = "Phase 1B-D1C-A persistent APFEL core preparation

Usage:
  parton-sbi prototype-persistent-apfel --prepare-only --output <DIRECTORY>

Options:
  --prepare-only  Initialize and destroy the three authorized contexts and write
                  a compact preparation manifest. No study is executed.
  --output        Ignored output directory for the preparation manifest.

This command never initializes PYTHIA, never calls pythia.next(), never creates
events or datasets, and never authorizes D2.
";

#[derive(Debug, Clone, PartialEq)]
pub struct PersistentApfelCliArgs {
    pub output: PathBuf,
}

pub fn parse_prototype_persistent_apfel(
    arguments: &[String],
) -> Result<PersistentApfelCliArgs, String> {
    let mut prepare_only = false;
    let mut output = None;
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--prepare-only" if !prepare_only => prepare_only = true,
            "--prepare-only" => return Err("--prepare-only was provided more than once".into()),
            "--output" => {
                index += 1;
                let value = arguments
                    .get(index)
                    .ok_or_else(|| "--output requires a path".to_owned())?;
                if output.replace(PathBuf::from(value)).is_some() {
                    return Err("--output was provided more than once".into());
                }
            }
            flag => return Err(format!("unknown prototype-persistent-apfel option: {flag}")),
        }
        index += 1;
    }
    if !prepare_only {
        return Err("prototype-persistent-apfel requires --prepare-only".into());
    }
    Ok(PersistentApfelCliArgs {
        output: output.ok_or_else(|| "--output is required".to_owned())?,
    })
}

#[derive(Debug, Serialize)]
struct PreparationAnchor {
    name: &'static str,
    theta: PdfTheta,
    identities: PersistentApfelIdentities,
    support: PersistentApfelSupport,
    diagnostics_before_destroy: PersistentApfelDiagnostics,
}

#[derive(Debug, Serialize)]
struct PreparationLimits {
    numerical_wall_time_seconds: u64,
    internal_study_deadline_seconds: u64,
    maximum_generated_bytes: u64,
    maximum_pythia_next_calls_per_anchor: u64,
    maximum_successful_events_in_memory_per_anchor: u64,
    saved_production_events: u64,
}

#[derive(Debug, Serialize)]
struct PreparationManifest {
    schema_version: &'static str,
    git_commit: &'static str,
    git_dirty_at_build: bool,
    apfelxx_version: &'static str,
    lhapdf_version: &'static str,
    evaluator_policy_version: &'static str,
    bridge_abi_version: &'static str,
    mutex_policy_version: &'static str,
    cache_policy_version: &'static str,
    anchors: Vec<PreparationAnchor>,
    limits: PreparationLimits,
    #[serde(rename = "PROTOTYPE_AUTHORIZED")]
    prototype_authorized: bool,
    #[serde(rename = "CONTROLLED_PYTHIA_NEXT_AUTHORIZED")]
    controlled_pythia_next_authorized: bool,
    #[serde(rename = "PYTHIA_NEXT_EXECUTED")]
    pythia_next_executed: bool,
    #[serde(rename = "PRODUCTION_EVENTS_AUTHORIZED")]
    production_events_authorized: bool,
    #[serde(rename = "D2_AUTHORIZED")]
    d2_authorized: bool,
    consumer_envelope_result_available: bool,
    scientific_study_result_available: bool,
}

pub fn run_prototype_persistent_apfel(arguments: PersistentApfelCliArgs) -> Result<(), String> {
    fs::create_dir_all(&arguments.output).map_err(|error| error.to_string())?;
    let mut anchors = Vec::new();
    for (name, theta) in authorized_anchors()? {
        let context =
            PersistentApfelContext::initialize(theta).map_err(|error| error.to_string())?;
        anchors.push(PreparationAnchor {
            name,
            theta,
            identities: context.identities().clone(),
            support: context.support(),
            diagnostics_before_destroy: context.diagnostics().map_err(|error| error.to_string())?,
        });
        context.close().map_err(|error| error.to_string())?;
    }
    let manifest = PreparationManifest {
        schema_version: PERSISTENT_APFEL_PREPARATION_SCHEMA,
        git_commit: env!("GIT_HASH"),
        git_dirty_at_build: env!("GIT_DIRTY") == "true",
        apfelxx_version: "4.8.0",
        lhapdf_version: "6.5.6",
        evaluator_policy_version: PERSISTENT_APFEL_POLICY_VERSION,
        bridge_abi_version: PERSISTENT_APFEL_ABI_VERSION,
        mutex_policy_version: PERSISTENT_APFEL_MUTEX_POLICY_VERSION,
        cache_policy_version: PERSISTENT_APFEL_CACHE_POLICY_VERSION,
        anchors,
        limits: fixed_limits(),
        prototype_authorized: D1C_PROTOTYPE_AUTHORIZED,
        controlled_pythia_next_authorized: D1C_CONTROLLED_PYTHIA_NEXT_AUTHORIZED,
        pythia_next_executed: false,
        production_events_authorized: D1C_PRODUCTION_EVENTS_AUTHORIZED,
        d2_authorized: D1C_D2_AUTHORIZED,
        consumer_envelope_result_available: false,
        scientific_study_result_available: false,
    };
    let bytes = serde_json::to_vec_pretty(&manifest).map_err(|error| error.to_string())?;
    fs::write(arguments.output.join("preparation_manifest.json"), bytes)
        .map_err(|error| error.to_string())
}

fn authorized_anchors() -> Result<Vec<(&'static str, PdfTheta)>, String> {
    [
        ("center", 0.0, 0.0),
        ("delta_min", -0.2, 0.0),
        ("corner_min_max", -0.2, 0.25),
    ]
    .into_iter()
    .map(|(name, delta_v, lambda_sea)| {
        PdfTheta::new(delta_v, lambda_sea)
            .map(|theta| (name, theta))
            .map_err(|error| error.to_string())
    })
    .collect()
}

fn fixed_limits() -> PreparationLimits {
    PreparationLimits {
        numerical_wall_time_seconds: 1800,
        internal_study_deadline_seconds: 1700,
        maximum_generated_bytes: 2 * 1024 * 1024 * 1024,
        maximum_pythia_next_calls_per_anchor: 128,
        maximum_successful_events_in_memory_per_anchor: 32,
        saved_production_events: 0,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn prototype_persistent_apfel_parser_is_prepare_only() {
        let args = parse_prototype_persistent_apfel(&[
            "--prepare-only".into(),
            "--output".into(),
            "outputs/d1c".into(),
        ])
        .unwrap();
        assert_eq!(args.output, PathBuf::from("outputs/d1c"));
        assert!(
            parse_prototype_persistent_apfel(&["--output".into(), "outputs/d1c".into()]).is_err()
        );
        assert!(parse_prototype_persistent_apfel(&["--study".into()]).is_err());
    }

    #[test]
    fn prototype_persistent_apfel_contract_keeps_caps_and_d2_closed() {
        let limits = fixed_limits();
        assert_eq!(authorized_anchors().unwrap().len(), 3);
        assert_eq!(limits.numerical_wall_time_seconds, 1800);
        assert_eq!(limits.internal_study_deadline_seconds, 1700);
        assert_eq!(limits.maximum_pythia_next_calls_per_anchor, 128);
        assert_eq!(limits.saved_production_events, 0);
        const {
            assert!(D1C_PROTOTYPE_AUTHORIZED);
            assert!(D1C_CONTROLLED_PYTHIA_NEXT_AUTHORIZED);
            assert!(!D1C_PRODUCTION_EVENTS_AUTHORIZED);
            assert!(!D1C_D2_AUTHORIZED);
        }
    }
}
