use std::fs;
use std::path::PathBuf;
use std::time::Instant;

use parton_sbi::physics::{
    audit_transport_reload, derive_prototype_decision, prototype_anchors, CandidateEvidence,
    CandidateStatus, ComparisonEvidence, DeterministicTransportGrid, DirectApfelEvaluator,
    HardProcessQueryEnvelope, MeasurementStatus, PrototypeDecision, PrototypeStudyContract,
    ReloadAudit, StudyBudget, TransportQuery, D1_FLAVORS, MINIMUM_PROTOTYPE_CALLS_PER_SECOND,
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
    evaluator_policy_identity: String,
    anchor_transport_identity: String,
    custom_identity: String,
    knot_comparison: ComparisonEvidence,
    off_knot_comparison: ComparisonEvidence,
    one_sided_threshold_comparison: ComparisonEvidence,
    direct_deterministic_repeat: MeasurementStatus,
    custom_deterministic_repeat: MeasurementStatus,
    reload_audit: ReloadAudit,
    strict_support: MeasurementStatus,
    direct_batch_rebuild_effective_calls_per_second: f64,
    direct_scalar_adapter_benchmark_status: MeasurementStatus,
    custom_scalar_calls_per_second: f64,
}

#[derive(Debug, Serialize)]
struct PrototypeStudySummary {
    schema_version: &'static str,
    decision: PrototypeDecision,
    direct_candidate_status: CandidateStatus,
    custom_candidate_status: CandidateStatus,
    all_consumer_envelope_complete: bool,
    anchors: Vec<AnchorStudySummary>,
    initialization_seconds: f64,
    query_envelope: HardProcessQueryEnvelope,
    unresolved_consumers: Vec<String>,
    direct_thread_safety: MeasurementStatus,
    custom_thread_safety: MeasurementStatus,
    direct_process_isolation: MeasurementStatus,
    custom_process_isolation: MeasurementStatus,
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
    let evaluator_policy_identity = direct.evaluator_policy_identity().to_owned();
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
        let stored_bytes = fs::read(&cache_path).map_err(|error| error.to_string())?;
        let reloaded: DeterministicTransportGrid =
            serde_json::from_slice(&stored_bytes).map_err(|error| error.to_string())?;
        let reload_audit = audit_transport_reload(&custom, &reloaded, &stored_bytes)
            .map_err(|error| error.to_string())?;
        let mut knot_pairs = Vec::with_capacity(queries.len());
        for (query, expected) in queries.iter().zip(values.iter()) {
            let actual = reloaded
                .evaluate(*query)
                .map_err(|error| error.to_string())?;
            knot_pairs.push((expected.xf, actual.xf));
        }
        let knot_comparison = ComparisonEvidence::from_pairs(knot_pairs);
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
        let direct_batch_rebuild_effective_calls_per_second =
            probe_queries.len() as f64 / direct_started.elapsed().as_secs_f64();
        let repeated = direct
            .evaluate_batch(anchor.theta, &probe_queries)
            .map_err(|error| error.to_string())?;
        let direct_deterministic_repeat = measurement(direct_probes == repeated);
        let mut off_knot_pairs = Vec::with_capacity(probe_queries.len());
        for (query, expected) in probe_queries.iter().zip(direct_probes.iter()) {
            let actual = reloaded
                .evaluate(*query)
                .map_err(|error| error.to_string())?;
            off_knot_pairs.push((expected.xf, actual.xf));
        }
        let off_knot_comparison = ComparisonEvidence::from_pairs(off_knot_pairs);

        let threshold_queries = one_sided_threshold_queries(&xs, &thresholds);
        let direct_thresholds = direct
            .evaluate_batch(anchor.theta, &threshold_queries)
            .map_err(|error| error.to_string())?;
        let mut threshold_pairs = Vec::with_capacity(threshold_queries.len());
        for (query, expected) in threshold_queries.iter().zip(direct_thresholds.iter()) {
            let actual = reloaded
                .evaluate(*query)
                .map_err(|error| error.to_string())?;
            threshold_pairs.push((expected.xf, actual.xf));
        }
        let one_sided_threshold_comparison = ComparisonEvidence::from_pairs(threshold_pairs);

        let benchmark_started = Instant::now();
        let benchmark_query = queries[queries.len() / 2];
        let repetitions = 10_000usize;
        let first_custom = reloaded
            .evaluate(benchmark_query)
            .map_err(|error| error.to_string())?;
        for _ in 0..repetitions {
            let _ = reloaded
                .evaluate(benchmark_query)
                .map_err(|error| error.to_string())?;
        }
        let custom_scalar_calls_per_second =
            repetitions as f64 / benchmark_started.elapsed().as_secs_f64();
        let repeated_custom = reloaded
            .evaluate(benchmark_query)
            .map_err(|error| error.to_string())?;
        let custom_deterministic_repeat =
            measurement(first_custom.xf.to_bits() == repeated_custom.xf.to_bits());
        let outside = TransportQuery {
            flavor: 21,
            x: config.exported_x_minimum / 2.0,
            q_gev: config.q_minimum_gev,
        };
        let strict_support = measurement(
            direct.evaluate_batch(anchor.theta, &[outside]).is_err()
                && reloaded.evaluate(outside).is_err(),
        );
        anchor_summaries.push(AnchorStudySummary {
            anchor: anchor.name,
            evaluator_policy_identity: evaluator_policy_identity.clone(),
            anchor_transport_identity: direct
                .anchor_transport_identity(anchor.theta)
                .map_err(|error| error.to_string())?,
            custom_identity: custom.identity.clone(),
            knot_comparison,
            off_knot_comparison,
            one_sided_threshold_comparison,
            direct_deterministic_repeat,
            custom_deterministic_repeat,
            reload_audit,
            strict_support,
            direct_batch_rebuild_effective_calls_per_second,
            direct_scalar_adapter_benchmark_status: MeasurementStatus::NotMeasured,
            custom_scalar_calls_per_second,
        });
        budget.enforce().map_err(|error| error.to_string())?;
    }

    let unresolved_consumers = envelope.unresolved_consumers();
    let all_consumer_envelope_complete = unresolved_consumers.is_empty();
    let anchor_identities_unique = anchor_summaries
        .iter()
        .map(|summary| &summary.anchor_transport_identity)
        .collect::<std::collections::BTreeSet<_>>()
        .len()
        == anchor_summaries.len();
    let direct_evidence = CandidateEvidence {
        accuracy: MeasurementStatus::NotMeasured,
        identity: measurement(anchor_identities_unique),
        reload: MeasurementStatus::NotMeasured,
        threshold: MeasurementStatus::Passed,
        support: aggregate(
            anchor_summaries
                .iter()
                .map(|summary| summary.strict_support),
        ),
        deterministic_repeat: aggregate(
            anchor_summaries
                .iter()
                .map(|summary| summary.direct_deterministic_repeat),
        ),
        scalar_throughput: MeasurementStatus::NotMeasured,
        thread_safety: MeasurementStatus::NotMeasured,
        process_isolation: MeasurementStatus::NotMeasured,
    };
    let custom_evidence = CandidateEvidence {
        accuracy: aggregate(anchor_summaries.iter().map(|summary| {
            measurement(
                summary.knot_comparison.outside_tolerance_count == 0
                    && summary.off_knot_comparison.outside_tolerance_count == 0,
            )
        })),
        identity: aggregate(
            anchor_summaries
                .iter()
                .map(|summary| summary.reload_audit.stored_identity_status),
        ),
        reload: aggregate(anchor_summaries.iter().map(|summary| {
            aggregate([
                summary.reload_audit.binary64_identity_status,
                summary.reload_audit.canonical_bytes_status,
            ])
        })),
        threshold: aggregate(
            anchor_summaries
                .iter()
                .map(|summary| summary.one_sided_threshold_comparison.status()),
        ),
        support: aggregate(
            anchor_summaries
                .iter()
                .map(|summary| summary.strict_support),
        ),
        deterministic_repeat: aggregate(
            anchor_summaries
                .iter()
                .map(|summary| summary.custom_deterministic_repeat),
        ),
        scalar_throughput: aggregate(anchor_summaries.iter().map(|summary| {
            measurement(
                summary.custom_scalar_calls_per_second >= MINIMUM_PROTOTYPE_CALLS_PER_SECOND,
            )
        })),
        thread_safety: MeasurementStatus::NotMeasured,
        process_isolation: MeasurementStatus::NotMeasured,
    };
    let direct_candidate_status = direct_evidence.status();
    let custom_candidate_status = custom_evidence.status();
    let decision = derive_prototype_decision(
        direct_candidate_status,
        custom_candidate_status,
        all_consumer_envelope_complete,
    );
    let summary = PrototypeStudySummary {
        schema_version: "partonsbi.d1a.transport-prototype.study.v2",
        decision,
        direct_candidate_status,
        custom_candidate_status,
        all_consumer_envelope_complete,
        anchors: anchor_summaries,
        initialization_seconds,
        query_envelope: envelope,
        unresolved_consumers,
        direct_thread_safety: direct_evidence.thread_safety,
        custom_thread_safety: custom_evidence.thread_safety,
        direct_process_isolation: direct_evidence.process_isolation,
        custom_process_isolation: custom_evidence.process_isolation,
        peak_memory_kib: linux_peak_memory_kib(),
        no_events: true,
        d2_authorized: false,
    };
    write_json(output.join("study_summary.json"), &summary)?;
    budget.enforce().map_err(|error| error.to_string())
}

fn one_sided_threshold_queries(xs: &[f64], thresholds: &[f64]) -> Vec<TransportQuery> {
    thresholds
        .iter()
        .flat_map(|threshold| {
            let below = f64::from_bits(threshold.to_bits() - 1);
            let above = f64::from_bits(threshold.to_bits() + 1);
            [below, above].into_iter().flat_map(|q_gev| {
                xs.iter().flat_map(move |x| {
                    D1_FLAVORS.iter().map(move |flavor| TransportQuery {
                        flavor: *flavor,
                        x: *x,
                        q_gev,
                    })
                })
            })
        })
        .collect()
}

fn measurement(passed: bool) -> MeasurementStatus {
    if passed {
        MeasurementStatus::Passed
    } else {
        MeasurementStatus::Failed
    }
}

fn aggregate(statuses: impl IntoIterator<Item = MeasurementStatus>) -> MeasurementStatus {
    let statuses = statuses.into_iter().collect::<Vec<_>>();
    if statuses.contains(&MeasurementStatus::Failed) {
        MeasurementStatus::Failed
    } else if statuses.is_empty() || statuses.contains(&MeasurementStatus::NotMeasured) {
        MeasurementStatus::NotMeasured
    } else {
        MeasurementStatus::Passed
    }
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
