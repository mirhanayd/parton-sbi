use std::fs;
use std::path::PathBuf;
use std::time::Instant;

use parton_sbi::physics::{
    prototype_anchors, DeterministicTransportGrid, DirectApfelEvaluator, HardProcessQueryEnvelope,
    PrototypeDecision, PrototypeStudyContract, StudyBudget, TransportQuery, D1_FLAVORS,
};
use serde::{Deserialize, Serialize};

pub const PROTOTYPE_PDF_TRANSPORT_HELP: &str = "Phase 1B-D1A bounded transport prototype

Usage:
  parton-sbi prototype-pdf-transport --prepare-only --output <DIRECTORY>
  parton-sbi prototype-pdf-transport --study --output <DIRECTORY>

Options:
  --prepare-only  Write the immutable three-anchor study contract without APFEL evaluation.
  --study         Run the bounded comparison. Internally limited to 30 minutes and 2 GiB.
  --output        Ignored output directory for compact prototype data.

The command never calls pythia.next(), never generates events, and never
authorizes D2.
";

#[derive(Debug, Clone, PartialEq)]
pub struct PdfTransportPrototypeCliArgs {
    pub mode: PrototypeMode,
    pub output: PathBuf,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PrototypeMode {
    PrepareOnly,
    Study,
}

pub fn parse_prototype_pdf_transport(
    arguments: &[String],
) -> Result<PdfTransportPrototypeCliArgs, String> {
    let mut mode = None;
    let mut output = None;
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--prepare-only" => set_once(&mut mode, PrototypeMode::PrepareOnly, "mode")?,
            "--study" => set_once(&mut mode, PrototypeMode::Study, "mode")?,
            "--output" => {
                index += 1;
                let value = arguments
                    .get(index)
                    .ok_or_else(|| "--output requires a path".to_owned())?;
                set_once(&mut output, PathBuf::from(value), "--output")?;
            }
            flag => return Err(format!("unknown prototype-pdf-transport option: {flag}")),
        }
        index += 1;
    }
    Ok(PdfTransportPrototypeCliArgs {
        mode: mode.ok_or_else(|| "select exactly one of --prepare-only or --study".to_owned())?,
        output: output.ok_or_else(|| "--output is required".to_owned())?,
    })
}

fn set_once<T>(slot: &mut Option<T>, value: T, name: &str) -> Result<(), String> {
    if slot.is_some() {
        return Err(format!("{name} was provided more than once"));
    }
    *slot = Some(value);
    Ok(())
}

#[derive(Debug, Serialize)]
struct PreparationManifest {
    schema_version: &'static str,
    git_commit: &'static str,
    git_dirty_at_build: bool,
    contract: PrototypeStudyContract,
    hard_process_envelope: HardProcessQueryEnvelope,
    pythia_initialization_permitted: bool,
    pythia_next_permitted: bool,
    event_generation_permitted: bool,
    d2_authorized: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct AnchorStudySummary {
    anchor: String,
    direct_identity: String,
    custom_identity: String,
    maximum_absolute_knot_difference: f64,
    maximum_absolute_off_knot_difference: f64,
    maximum_relative_off_knot_difference: f64,
    deterministic_reload: bool,
    deterministic_repeat: bool,
    threshold_probe_count: usize,
    direct_calls_per_second: f64,
    custom_calls_per_second: f64,
}

#[derive(Debug, Serialize)]
struct PrototypeStudySummary {
    schema_version: &'static str,
    decision: PrototypeDecision,
    anchors: Vec<AnchorStudySummary>,
    initialization_seconds: f64,
    query_envelope: HardProcessQueryEnvelope,
    unresolved_consumers: Vec<String>,
    serialized_direct_access: bool,
    custom_thread_safe_immutable_data: bool,
    process_isolation_probe: &'static str,
    peak_memory_kib: Option<u64>,
    no_events: bool,
    d2_authorized: bool,
}

pub fn run_prototype_pdf_transport(arguments: PdfTransportPrototypeCliArgs) -> Result<(), String> {
    fs::create_dir_all(&arguments.output).map_err(|error| error.to_string())?;
    let contract = PrototypeStudyContract::fixed().map_err(|error| error.to_string())?;
    let envelope = HardProcessQueryEnvelope::hera_dis();
    let manifest = PreparationManifest {
        schema_version: "partonsbi.d1a.transport-prototype.preparation.v1",
        git_commit: env!("GIT_HASH"),
        git_dirty_at_build: env!("GIT_DIRTY") == "true",
        contract,
        hard_process_envelope: envelope.clone(),
        pythia_initialization_permitted: true,
        pythia_next_permitted: false,
        event_generation_permitted: false,
        d2_authorized: false,
    };
    write_json(
        arguments.output.join("preparation_manifest.json"),
        &manifest,
    )?;
    if arguments.mode == PrototypeMode::PrepareOnly {
        return Ok(());
    }
    run_bounded_study(&arguments.output, envelope)
}

fn run_bounded_study(
    output: &std::path::Path,
    envelope: HardProcessQueryEnvelope,
) -> Result<(), String> {
    let budget = StudyBudget::start(output).map_err(|error| error.to_string())?;
    let initialized = Instant::now();
    let direct = DirectApfelEvaluator::initialize().map_err(|error| error.to_string())?;
    let initialization_seconds = initialized.elapsed().as_secs_f64();
    budget.enforce().map_err(|error| error.to_string())?;

    let config = direct.config();
    let mut xs = vec![
        config.exported_x_minimum,
        1.0e-4,
        0.01,
        0.1,
        0.8,
        config.exported_x_maximum,
    ];
    xs.sort_by(f64::total_cmp);
    xs.dedup_by(|a, b| a.to_bits() == b.to_bits());
    let mut qs = vec![
        config.q_minimum_gev,
        config.charm_threshold_gev,
        config.bottom_threshold_gev,
        10.0,
        100.0,
        config.q_maximum_gev,
    ];
    qs.sort_by(f64::total_cmp);
    qs.dedup_by(|a, b| a.to_bits() == b.to_bits());
    let thresholds = vec![config.charm_threshold_gev, config.bottom_threshold_gev];
    let direct_identity = direct.identity().to_owned();
    let mut anchor_summaries = Vec::new();
    for anchor in prototype_anchors().map_err(|error| error.to_string())? {
        budget.enforce().map_err(|error| error.to_string())?;
        let queries = qs
            .iter()
            .flat_map(|q| {
                xs.iter().flat_map(move |x| {
                    D1_FLAVORS.iter().map(move |flavor| TransportQuery {
                        flavor: *flavor,
                        x: *x,
                        q_gev: *q,
                    })
                })
            })
            .collect::<Vec<_>>();
        let values = direct
            .evaluate_batch(anchor.theta, &queries)
            .map_err(|error| error.to_string())?;
        let xf_values = values.iter().map(|value| value.xf).collect::<Vec<_>>();
        let custom = DeterministicTransportGrid::new(
            xs.clone(),
            qs.clone(),
            thresholds.clone(),
            D1_FLAVORS.to_vec(),
            xf_values,
        )
        .map_err(|error| error.to_string())?;
        let cache_path = output.join(format!("{}_custom_grid.json", anchor.name));
        write_json(&cache_path, &custom)?;
        let reloaded: DeterministicTransportGrid =
            serde_json::from_slice(&fs::read(&cache_path).map_err(|error| error.to_string())?)
                .map_err(|error| error.to_string())?;
        let mut maximum_absolute_knot_difference = 0.0_f64;
        for (query, expected) in queries.iter().zip(values.iter()) {
            let actual = reloaded
                .evaluate(*query)
                .map_err(|error| error.to_string())?;
            maximum_absolute_knot_difference =
                maximum_absolute_knot_difference.max((actual.xf - expected.xf).abs());
        }
        let probe_queries = qs
            .windows(2)
            .flat_map(|q_pair| {
                let q = (q_pair[0] * q_pair[1]).sqrt();
                xs.windows(2).flat_map(move |x_pair| {
                    let x = (x_pair[0] * x_pair[1]).sqrt();
                    D1_FLAVORS.iter().map(move |flavor| TransportQuery {
                        flavor: *flavor,
                        x,
                        q_gev: q,
                    })
                })
            })
            .collect::<Vec<_>>();
        let direct_started = Instant::now();
        let direct_probes = direct
            .evaluate_batch(anchor.theta, &probe_queries)
            .map_err(|error| error.to_string())?;
        let direct_calls_per_second =
            probe_queries.len() as f64 / direct_started.elapsed().as_secs_f64();
        let repeated = direct
            .evaluate_batch(anchor.theta, &probe_queries)
            .map_err(|error| error.to_string())?;
        let deterministic_repeat = direct_probes == repeated;
        let mut maximum_absolute_off_knot_difference = 0.0_f64;
        let mut maximum_relative_off_knot_difference = 0.0_f64;
        for (query, expected) in probe_queries.iter().zip(direct_probes.iter()) {
            let actual = reloaded
                .evaluate(*query)
                .map_err(|error| error.to_string())?;
            let absolute = (actual.xf - expected.xf).abs();
            let relative = if expected.xf == 0.0 {
                0.0
            } else {
                absolute / expected.xf.abs()
            };
            maximum_absolute_off_knot_difference =
                maximum_absolute_off_knot_difference.max(absolute);
            maximum_relative_off_knot_difference =
                maximum_relative_off_knot_difference.max(relative);
        }
        let benchmark_started = Instant::now();
        let benchmark_query = queries[queries.len() / 2];
        let repetitions = 10_000usize;
        for _ in 0..repetitions {
            let _ = reloaded
                .evaluate(benchmark_query)
                .map_err(|error| error.to_string())?;
        }
        let custom_calls_per_second =
            repetitions as f64 / benchmark_started.elapsed().as_secs_f64();
        anchor_summaries.push(AnchorStudySummary {
            anchor: anchor.name,
            direct_identity: direct_identity.clone(),
            custom_identity: custom.identity.clone(),
            maximum_absolute_knot_difference,
            maximum_absolute_off_knot_difference,
            maximum_relative_off_knot_difference,
            deterministic_reload: custom == reloaded,
            deterministic_repeat,
            threshold_probe_count: probe_queries.len(),
            direct_calls_per_second,
            custom_calls_per_second,
        });
        budget.enforce().map_err(|error| error.to_string())?;
    }

    let unresolved_consumers = envelope.unresolved_consumers();
    let summary = PrototypeStudySummary {
        schema_version: "partonsbi.d1a.transport-prototype.study.v1",
        decision: PrototypeDecision::Inconclusive,
        anchors: anchor_summaries,
        initialization_seconds,
        query_envelope: envelope,
        unresolved_consumers,
        serialized_direct_access: true,
        custom_thread_safe_immutable_data: true,
        process_isolation_probe:
            "cache reload is process-portable; independent invocation must compare identities",
        peak_memory_kib: linux_peak_memory_kib(),
        no_events: true,
        d2_authorized: false,
    };
    write_json(output.join("study_summary.json"), &summary)?;
    budget.enforce().map_err(|error| error.to_string())
}

fn linux_peak_memory_kib() -> Option<u64> {
    let status = fs::read_to_string("/proc/self/status").ok()?;
    let line = status.lines().find(|line| line.starts_with("VmHWM:"))?;
    line.split_whitespace().nth(1)?.parse().ok()
}

fn write_json(path: impl AsRef<std::path::Path>, value: &impl Serialize) -> Result<(), String> {
    let bytes = serde_json::to_vec_pretty(value).map_err(|error| error.to_string())?;
    fs::write(path, bytes).map_err(|error| error.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parser_requires_one_mode_and_output() {
        let parse = |args: &[&str]| {
            parse_prototype_pdf_transport(
                &args
                    .iter()
                    .map(|value| (*value).to_owned())
                    .collect::<Vec<_>>(),
            )
        };
        assert!(parse(&["--prepare-only", "--output", "outputs/test"]).is_ok());
        assert!(parse(&["--study", "--output", "outputs/test"]).is_ok());
        assert!(parse(&["--prepare-only", "--study", "--output", "x"]).is_err());
        assert!(parse(&["--prepare-only"]).is_err());
    }
}
