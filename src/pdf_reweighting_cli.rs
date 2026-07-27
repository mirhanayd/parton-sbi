use chrono::Utc;
use parton_sbi::physics::{
    extract_event_observables, load_full_set_strict_support_contract, reweight_event,
    validate_run_compatibility, DenominatorPolicy, EventObservableSummary, HepMcReader,
    HepMcRunProvenance, HepMcRunSummary, InclusiveObservableRow, LhapdfProvider, PdfMemberSpec,
    PdfReweightingAccumulator, PdfReweightingDiagnostics, PdfReweightingRequest,
    PdfReweightingResult, PdfSupportContract, WeightStatistics,
    DEFAULT_NOMINAL_XF_RELATIVE_TOLERANCE, PDF_REUSE_ESS_FRACTION_THRESHOLD,
};
use serde::Serialize;
use std::collections::BTreeMap;
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};

const CSV_HEPMC_EVENT_WEIGHT_RELATIVE_TOLERANCE: f64 = 1.0e-5;

pub const VALIDATE_PDF_REWEIGHTING_HELP: &str =
    "Validate discrete LHAPDF-member hard-PDF reweighting

Usage:
  parton-sbi validate-pdf-reweighting \\
      --nominal-run <RUN_DIRECTORY> \\
      --target-pdf-set <SET> \\
      --target-pdf-member <INDEX> \\
      --output <DIRECTORY> \\
      [--direct-target-run <RUN_DIRECTORY>] \\
      [--event-weight-index <INDEX>] \\
      [--max-events <COUNT>] \\
      [--strict <true|false>] \\
      [--denominator-policy <stored|recomputed>] \\
      [--nominal-xf-relative-tolerance <VALUE>]

The default denominator is the generator-stored proton-side xf. Stored and
recomputed nominal xf values must agree within the predeclared default relative
tolerance of 1e-6. Ratios and target weights are never clipped.
";

pub const SCAN_PDF_MEMBERS_HELP: &str = "Scan all non-central members over nominal event support

Usage:
  parton-sbi scan-pdf-members \\
      --nominal-run <RUN_DIRECTORY> \\
      --output <DIRECTORY> \\
      [--pdf-set <SET>] \\
      [--event-weight-index <INDEX>] \\
      [--max-events <COUNT>] \\
      [--nominal-xf-relative-tolerance <VALUE>]
";

#[derive(Debug, Clone, PartialEq)]
pub struct ValidatePdfReweightingArgs {
    pub nominal_run: PathBuf,
    pub direct_target_run: Option<PathBuf>,
    pub target_pdf_set: String,
    pub target_pdf_member: i32,
    pub output: PathBuf,
    pub event_weight_index: Option<usize>,
    pub max_events: Option<usize>,
    pub strict: bool,
    pub denominator_policy: DenominatorPolicy,
    pub nominal_xf_relative_tolerance: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ScanPdfMembersArgs {
    pub nominal_run: PathBuf,
    pub pdf_set: Option<String>,
    pub output: PathBuf,
    pub event_weight_index: Option<usize>,
    pub max_events: Option<usize>,
    pub nominal_xf_relative_tolerance: f64,
}

fn value_after<'a>(args: &'a [String], index: usize, flag: &str) -> Result<&'a str, String> {
    args.get(index + 1)
        .filter(|value| !value.starts_with("--"))
        .map(String::as_str)
        .ok_or_else(|| format!("{flag} requires a value"))
}

fn set_once<T>(slot: &mut Option<T>, value: T, flag: &str) -> Result<(), String> {
    if slot.replace(value).is_some() {
        Err(format!("duplicate option: {flag}"))
    } else {
        Ok(())
    }
}

fn non_negative_i32(flag: &str, value: &str) -> Result<i32, String> {
    let parsed = value
        .parse::<i32>()
        .map_err(|_| format!("{flag} requires a non-negative integer, got {value}"))?;
    if parsed < 0 {
        Err(format!("{flag} must be non-negative, got {parsed}"))
    } else {
        Ok(parsed)
    }
}

fn positive_usize(flag: &str, value: &str) -> Result<usize, String> {
    let parsed = value
        .parse::<usize>()
        .map_err(|_| format!("{flag} requires a positive integer, got {value}"))?;
    if parsed == 0 {
        Err(format!("{flag} must be positive"))
    } else {
        Ok(parsed)
    }
}

fn parse_tolerance(value: &str) -> Result<f64, String> {
    let parsed = value
        .parse::<f64>()
        .map_err(|_| format!("invalid nominal-xf relative tolerance: {value}"))?;
    if !parsed.is_finite() || parsed < 0.0 {
        Err(format!(
            "nominal-xf relative tolerance must be finite and non-negative, got {value}"
        ))
    } else {
        Ok(parsed)
    }
}

pub fn parse_validate_pdf_reweighting(
    args: &[String],
) -> Result<ValidatePdfReweightingArgs, String> {
    if args.is_empty() {
        return Err(format!(
            "missing required options\n\n{VALIDATE_PDF_REWEIGHTING_HELP}"
        ));
    }
    let mut nominal_run = None;
    let mut direct_target_run = None;
    let mut target_pdf_set = None;
    let mut target_pdf_member = None;
    let mut output = None;
    let mut event_weight_index = None;
    let mut max_events = None;
    let mut strict = None;
    let mut denominator_policy = None;
    let mut relative_tolerance = None;
    let mut index = 0;
    while index < args.len() {
        let flag = args[index].as_str();
        let value = value_after(args, index, flag)?;
        match flag {
            "--nominal-run" => set_once(&mut nominal_run, PathBuf::from(value), flag)?,
            "--direct-target-run" => set_once(&mut direct_target_run, PathBuf::from(value), flag)?,
            "--target-pdf-set" => set_once(&mut target_pdf_set, value.to_owned(), flag)?,
            "--target-pdf-member" => {
                set_once(&mut target_pdf_member, non_negative_i32(flag, value)?, flag)?
            }
            "--output" => set_once(&mut output, PathBuf::from(value), flag)?,
            "--event-weight-index" => set_once(
                &mut event_weight_index,
                value
                    .parse::<usize>()
                    .map_err(|_| format!("{flag} requires a non-negative integer"))?,
                flag,
            )?,
            "--max-events" => set_once(&mut max_events, positive_usize(flag, value)?, flag)?,
            "--strict" => set_once(
                &mut strict,
                value
                    .parse::<bool>()
                    .map_err(|_| format!("{flag} requires true or false"))?,
                flag,
            )?,
            "--denominator-policy" => {
                let policy = match value {
                    "stored" => DenominatorPolicy::Stored,
                    "recomputed" => DenominatorPolicy::Recomputed,
                    _ => return Err(format!("{flag} requires stored or recomputed")),
                };
                set_once(&mut denominator_policy, policy, flag)?;
            }
            "--nominal-xf-relative-tolerance" => {
                set_once(&mut relative_tolerance, parse_tolerance(value)?, flag)?
            }
            _ => return Err(format!("unknown validate-pdf-reweighting option: {flag}")),
        }
        index += 2;
    }

    Ok(ValidatePdfReweightingArgs {
        nominal_run: nominal_run
            .ok_or_else(|| "missing required option: --nominal-run".to_owned())?,
        direct_target_run,
        target_pdf_set: target_pdf_set
            .ok_or_else(|| "missing required option: --target-pdf-set".to_owned())?,
        target_pdf_member: target_pdf_member
            .ok_or_else(|| "missing required option: --target-pdf-member".to_owned())?,
        output: output.ok_or_else(|| "missing required option: --output".to_owned())?,
        event_weight_index,
        max_events,
        strict: strict.unwrap_or(true),
        denominator_policy: denominator_policy.unwrap_or_default(),
        nominal_xf_relative_tolerance: relative_tolerance
            .unwrap_or(DEFAULT_NOMINAL_XF_RELATIVE_TOLERANCE),
    })
}

pub fn parse_scan_pdf_members(args: &[String]) -> Result<ScanPdfMembersArgs, String> {
    if args.is_empty() {
        return Err(format!(
            "missing required options\n\n{SCAN_PDF_MEMBERS_HELP}"
        ));
    }
    let mut nominal_run = None;
    let mut pdf_set = None;
    let mut output = None;
    let mut event_weight_index = None;
    let mut max_events = None;
    let mut relative_tolerance = None;
    let mut index = 0;
    while index < args.len() {
        let flag = args[index].as_str();
        let value = value_after(args, index, flag)?;
        match flag {
            "--nominal-run" => set_once(&mut nominal_run, PathBuf::from(value), flag)?,
            "--pdf-set" => set_once(&mut pdf_set, value.to_owned(), flag)?,
            "--output" => set_once(&mut output, PathBuf::from(value), flag)?,
            "--event-weight-index" => set_once(
                &mut event_weight_index,
                value
                    .parse::<usize>()
                    .map_err(|_| format!("{flag} requires a non-negative integer"))?,
                flag,
            )?,
            "--max-events" => set_once(&mut max_events, positive_usize(flag, value)?, flag)?,
            "--nominal-xf-relative-tolerance" => {
                set_once(&mut relative_tolerance, parse_tolerance(value)?, flag)?
            }
            _ => return Err(format!("unknown scan-pdf-members option: {flag}")),
        }
        index += 2;
    }
    Ok(ScanPdfMembersArgs {
        nominal_run: nominal_run
            .ok_or_else(|| "missing required option: --nominal-run".to_owned())?,
        pdf_set,
        output: output.ok_or_else(|| "missing required option: --output".to_owned())?,
        event_weight_index,
        max_events,
        nominal_xf_relative_tolerance: relative_tolerance
            .unwrap_or(DEFAULT_NOMINAL_XF_RELATIVE_TOLERANCE),
    })
}

#[derive(Serialize)]
struct EventDiagnosticRecord<'a> {
    #[serde(flatten)]
    reweighting: &'a PdfReweightingResult,
    event_weight_relative_difference: Option<f64>,
    observables: Option<EventObservableSummary>,
    observable_error: Option<String>,
}

#[derive(Serialize)]
struct ReweightingManifest<'a> {
    schema_version: u32,
    created_at_utc: String,
    repository_commit: &'static str,
    repository_dirty: bool,
    package_version: &'static str,
    rust_version: &'static str,
    command: Vec<String>,
    nominal_run: &'a Path,
    direct_target_run: Option<&'a Path>,
    request: &'a PdfReweightingRequest,
    nominal_provenance: &'a HepMcRunProvenance,
    target_run_compatibility: Option<&'a parton_sbi::physics::RunCompatibilityReport>,
}

#[derive(Serialize)]
struct RateClosureSummary {
    status: String,
    source_rate_normalization_established: bool,
    direct_target_rate_normalization_established: bool,
    normalization_inputs_available_for_comparison: bool,
    comparison_performed: bool,
    reweighted_selected_cross_section_pb: Option<f64>,
    direct_target_selected_cross_section_pb: Option<f64>,
    method: Option<String>,
    reason: String,
}

#[derive(Serialize)]
struct ReweightingSummary<'a> {
    schema_version: u32,
    diagnostics: &'a PdfReweightingDiagnostics,
    observable_invalid_events: usize,
    source_run_summary: &'a HepMcRunSummary,
    direct_target_run_summary: Option<&'a HepMcRunSummary>,
    rate_closure: RateClosureSummary,
    decision: &'static str,
}

fn ensure_fresh_output(output: &Path, files: &[&str]) -> Result<(), String> {
    fs::create_dir_all(output)
        .map_err(|error| format!("failed to create {}: {error}", output.display()))?;
    for file in files {
        let path = output.join(file);
        if path.exists() {
            return Err(format!("refusing to overwrite existing {}", path.display()));
        }
    }
    Ok(())
}

fn write_json(path: &Path, value: &impl Serialize) -> Result<(), String> {
    let file = File::create(path)
        .map_err(|error| format!("failed to create {}: {error}", path.display()))?;
    serde_json::to_writer_pretty(BufWriter::new(file), value)
        .map_err(|error| format!("failed to write {}: {error}", path.display()))
}

fn relative_difference(left: f64, right: f64) -> f64 {
    (left - right).abs() / left.abs().max(right.abs()).max(f64::MIN_POSITIVE)
}

fn verified_support_contract(
    provenance: &HepMcRunProvenance,
    pdf_set: &str,
    nominal_member: i32,
) -> Result<PdfSupportContract, String> {
    let recorded = provenance.pdf_support_contract.clone().ok_or_else(|| {
        "run does not declare the required strict_in_grid PDF support contract".to_owned()
    })?;
    let nominal_spec =
        PdfMemberSpec::new(pdf_set, nominal_member).map_err(|error| error.to_string())?;
    recorded
        .validate_for_members(&nominal_spec, &nominal_spec)
        .map_err(|error| format!("invalid recorded PDF support contract: {error}"))?;
    let current = load_full_set_strict_support_contract(pdf_set, nominal_member)
        .map_err(|error| format!("failed to load authoritative PDF support: {error}"))?;
    if recorded != current {
        return Err(
            "recorded PDF support contract differs from authoritative installed LHAPDF metadata"
                .to_owned(),
        );
    }
    Ok(recorded)
}

pub fn run_validate_pdf_reweighting(args: ValidatePdfReweightingArgs) -> Result<(), String> {
    ensure_fresh_output(
        &args.output,
        &[
            "manifest.json",
            "reweighting_summary.json",
            "event_diagnostics.jsonl",
        ],
    )?;
    let mut nominal_provenance =
        HepMcRunProvenance::load(&args.nominal_run).map_err(|error| error.to_string())?;
    let source_set = nominal_provenance
        .pdf_set
        .clone()
        .ok_or_else(|| "nominal run does not declare a PDF set".to_owned())?;
    let source_member = nominal_provenance
        .pdf_member
        .ok_or_else(|| "nominal run does not declare a PDF member".to_owned())?;
    if source_set != args.target_pdf_set {
        return Err(format!(
            "target set '{}' differs from nominal set '{}'; Phase 1A validates members of one set",
            args.target_pdf_set, source_set
        ));
    }
    let support_contract =
        verified_support_contract(&nominal_provenance, &source_set, source_member)?;
    let source_spec =
        PdfMemberSpec::new(&source_set, source_member).map_err(|error| error.to_string())?;
    let target_spec = PdfMemberSpec::new(&args.target_pdf_set, args.target_pdf_member)
        .map_err(|error| error.to_string())?;
    support_contract
        .validate_for_members(&source_spec, &target_spec)
        .map_err(|error| error.to_string())?;
    let request = PdfReweightingRequest {
        source_pdf: source_spec,
        target_pdf: target_spec,
        source_run_identity: args.nominal_run.to_string_lossy().into_owned(),
        source_seed: nominal_provenance.generator_seed,
        event_weight_index: args.event_weight_index,
        denominator_policy: args.denominator_policy,
        nominal_xf_relative_tolerance: args.nominal_xf_relative_tolerance,
        support_contract,
    };
    let nominal_pdf =
        LhapdfProvider::new(&source_set, source_member).map_err(|error| error.to_string())?;
    let target_pdf = LhapdfProvider::new(&args.target_pdf_set, args.target_pdf_member)
        .map_err(|error| error.to_string())?;

    let direct_provenance = args
        .direct_target_run
        .as_ref()
        .map(HepMcRunProvenance::load)
        .transpose()
        .map_err(|error| error.to_string())?;
    let compatibility = direct_provenance
        .as_ref()
        .map(|direct| validate_run_compatibility(&nominal_provenance, direct));
    if let Some(direct) = &direct_provenance {
        if direct.pdf_member != Some(args.target_pdf_member) {
            return Err(format!(
                "direct target run member {:?} does not match requested member {}",
                direct.pdf_member, args.target_pdf_member
            ));
        }
    }

    let hepmc_path = args.nominal_run.join("events.hepmc3");
    let csv_path = args.nominal_run.join("inclusive_observables.csv");
    let mut reader = HepMcReader::open(&hepmc_path).map_err(|error| error.to_string())?;
    let mut csv_reader = csv::Reader::from_path(&csv_path)
        .map_err(|error| format!("failed to open {}: {error}", csv_path.display()))?;
    let mut csv_rows = csv_reader.deserialize::<InclusiveObservableRow>();
    let diagnostics_path = args.output.join("event_diagnostics.jsonl");
    let diagnostics_file = File::create(&diagnostics_path)
        .map_err(|error| format!("failed to create {}: {error}", diagnostics_path.display()))?;
    let mut diagnostics_writer = BufWriter::new(diagnostics_file);
    let mut diagnostics_accumulator = PdfReweightingAccumulator::default();
    let mut processed_events = 0usize;
    let mut reached_hepmc_eof = false;
    let mut observable_invalid_events = 0usize;
    while args
        .max_events
        .is_none_or(|maximum| processed_events < maximum)
    {
        let Some(event) = reader.next_event().map_err(|error| error.to_string())? else {
            reached_hepmc_eof = true;
            break;
        };
        if nominal_provenance.beam_particle_id_1.is_none()
            || nominal_provenance.beam_particle_id_2.is_none()
        {
            nominal_provenance.enrich_beam_ids_from_event(&event);
        }
        let row = csv_rows
            .next()
            .ok_or_else(|| {
                format!(
                    "inclusive CSV ended before HepMC event {}",
                    event.event_number
                )
            })?
            .map_err(|error| format!("failed to parse inclusive CSV: {error}"))?;
        let result = reweight_event(
            &event,
            Some(&nominal_provenance),
            &request,
            &nominal_pdf,
            &target_pdf,
        )
        .map_err(|error| error.to_string())?;
        let event_weight_relative_difference = result
            .original_event_weight
            .map(|weight| relative_difference(weight, row.event_weight));
        let event_weight_error = event_weight_relative_difference
            .filter(|difference| *difference > CSV_HEPMC_EVENT_WEIGHT_RELATIVE_TOLERANCE)
            .map(|difference| {
                format!(
                    "HepMC and generator CSV event weights disagree: relative difference {difference:.6e} exceeds {:.6e}",
                    CSV_HEPMC_EVENT_WEIGHT_RELATIVE_TOLERANCE
                )
            });
        let mut errors = Vec::new();
        if let Some(error) = event_weight_error {
            errors.push(error);
        }
        let observables = match extract_event_observables(&event, &row) {
            Ok(observables) => Some(observables),
            Err(error) => {
                errors.push(error);
                None
            }
        };
        let (observables, observable_error) = if errors.is_empty() {
            (observables, None)
        } else {
            observable_invalid_events += 1;
            (None, Some(errors.join("; ")))
        };
        serde_json::to_writer(
            &mut diagnostics_writer,
            &EventDiagnosticRecord {
                reweighting: &result,
                event_weight_relative_difference,
                observables,
                observable_error,
            },
        )
        .map_err(|error| format!("failed to serialize event diagnostics: {error}"))?;
        diagnostics_writer
            .write_all(b"\n")
            .map_err(|error| format!("failed to write event diagnostics: {error}"))?;
        diagnostics_accumulator.push(&result);
        processed_events += 1;
    }
    if reached_hepmc_eof {
        if let Some(trailing_row) = csv_rows.next() {
            let row = trailing_row
                .map_err(|error| format!("failed to parse trailing inclusive CSV row: {error}"))?;
            return Err(format!(
                "inclusive CSV contains a trailing row {} after HepMC EOF",
                row.event_number
            ));
        }
    }
    diagnostics_writer
        .flush()
        .map_err(|error| format!("failed to flush event diagnostics: {error}"))?;

    let diagnostics = diagnostics_accumulator.finish(args.nominal_xf_relative_tolerance);
    let source_summary =
        HepMcRunSummary::load(&args.nominal_run).map_err(|error| error.to_string())?;
    let direct_summary = args
        .direct_target_run
        .as_ref()
        .map(HepMcRunSummary::load)
        .transpose()
        .map_err(|error| error.to_string())?;
    let complete_valid_source_sample = args.max_events.is_none()
        && diagnostics.invalid_events == 0
        && observable_invalid_events == 0
        && source_summary.accepted_events == Some(diagnostics.total_events as u64);
    let reweighted_cross_section_pb = match (
        complete_valid_source_sample,
        source_summary.sigma_gen_mb,
        source_summary.pythia_weight_sum,
    ) {
        (true, Some(sigma), Some(weight_sum)) if weight_sum != 0.0 => {
            Some(sigma * 1.0e9 * diagnostics.overall.sum_weights / weight_sum)
        }
        _ => None,
    };
    let direct_rate_established = direct_summary
        .as_ref()
        .is_some_and(HepMcRunSummary::rate_normalization_established);
    let normalization_inputs_available = source_summary.rate_normalization_established()
        && direct_rate_established
        && reweighted_cross_section_pb.is_some();
    let rate_closure = RateClosureSummary {
        status: "RATE CLOSURE NOT ESTABLISHED".to_owned(),
        source_rate_normalization_established: source_summary.rate_normalization_established(),
        direct_target_rate_normalization_established: direct_rate_established,
        normalization_inputs_available_for_comparison: normalization_inputs_available,
        comparison_performed: false,
        reweighted_selected_cross_section_pb: reweighted_cross_section_pb,
        direct_target_selected_cross_section_pb: direct_summary
            .as_ref()
            .and_then(|summary| summary.selected_cross_section_pb),
        method: source_summary.rate_normalization_method.clone(),
        reason: if normalization_inputs_available {
            "normalization inputs are available, but no predeclared direct-versus-reweighted rate acceptance test has been performed".to_owned()
        } else if !complete_valid_source_sample {
            "a complete structurally valid nominal sample is required before a reweighted rate can be formed".to_owned()
        } else if direct_summary.is_none() {
            "no direct-target run was supplied".to_owned()
        } else {
            "final run-normalization metadata are incomplete".to_owned()
        },
    };
    let decision = if diagnostics.invalid_events > 0 || observable_invalid_events > 0 {
        "STRUCTURAL FAILURE"
    } else if diagnostics
        .overall
        .effective_sample_size
        .direct_regeneration_required
    {
        "DIRECT REGENERATION REQUIRED"
    } else {
        "ELIGIBLE FOR CLOSURE COMPARISON"
    };
    let summary = ReweightingSummary {
        schema_version: 1,
        diagnostics: &diagnostics,
        observable_invalid_events,
        source_run_summary: &source_summary,
        direct_target_run_summary: direct_summary.as_ref(),
        rate_closure,
        decision,
    };
    write_json(&args.output.join("reweighting_summary.json"), &summary)?;
    let manifest = ReweightingManifest {
        schema_version: 1,
        created_at_utc: Utc::now().to_rfc3339(),
        repository_commit: option_env!("GIT_HASH").unwrap_or("unknown"),
        repository_dirty: option_env!("GIT_DIRTY") == Some("true"),
        package_version: env!("CARGO_PKG_VERSION"),
        rust_version: env!("RUSTC_VERSION"),
        command: std::env::args().collect(),
        nominal_run: &args.nominal_run,
        direct_target_run: args.direct_target_run.as_deref(),
        request: &request,
        nominal_provenance: &nominal_provenance,
        target_run_compatibility: compatibility.as_ref(),
    };
    write_json(&args.output.join("manifest.json"), &manifest)?;

    if args.strict
        && (diagnostics.invalid_events > 0
            || observable_invalid_events > 0
            || compatibility
                .as_ref()
                .is_some_and(|report| !report.compatible))
    {
        return Err(format!(
            "strict validation failed: {} reweighting-invalid events, {} observable-invalid events, compatible runs={}",
            diagnostics.invalid_events,
            observable_invalid_events,
            compatibility
                .as_ref()
                .is_none_or(|report| report.compatible)
        ));
    }
    println!(
        "Processed {} events: {} valid, {} invalid; ESS/N={:.6}; {}",
        diagnostics.total_events,
        diagnostics.valid_events,
        diagnostics.invalid_events,
        diagnostics.overall.effective_sample_size.signed_fraction,
        decision
    );
    Ok(())
}

#[derive(Clone)]
struct ScanSupportPoint {
    flavor: i32,
    x: f64,
    scale_gev: f64,
    stored_nominal_xf: f64,
    original_weight: f64,
}

#[derive(Debug, Serialize)]
struct MemberScanEntry {
    member: i32,
    valid_ratio_fraction: f64,
    invalid_ratio_reasons: BTreeMap<String, usize>,
    zero_ratio_count: usize,
    median_absolute_log_ratio: Option<f64>,
    p95_absolute_log_ratio: Option<f64>,
    p99_absolute_log_ratio: Option<f64>,
    deformation_score: Option<f64>,
    predicted_weight_statistics: WeightStatistics,
    minimum_ratio: Option<f64>,
    maximum_ratio: Option<f64>,
    flavor_level_ess: BTreeMap<String, WeightStatistics>,
    x_region_ess: BTreeMap<String, WeightStatistics>,
}

#[derive(Serialize)]
struct MemberScanDocument<'a> {
    schema_version: u32,
    created_at_utc: String,
    repository_commit: &'static str,
    repository_dirty: bool,
    package_version: &'static str,
    rust_version: &'static str,
    command: Vec<String>,
    nominal_run: &'a Path,
    nominal_provenance: &'a HepMcRunProvenance,
    pdf_set: &'a str,
    nominal_member: i32,
    support_contract: &'a PdfSupportContract,
    event_count: usize,
    invalid_nominal_events: usize,
    nominal_xf_relative_tolerance: f64,
    deformation_score_definition: &'static str,
    mild_selection_rule: &'static str,
    stress_selection_rule: &'static str,
    selected_mild_member: Option<i32>,
    selected_stress_member: Option<i32>,
    stress_meets_ess_threshold: bool,
    entries: &'a [MemberScanEntry],
}

fn quantile(sorted: &[f64], probability: f64) -> Option<f64> {
    if sorted.is_empty() {
        return None;
    }
    if sorted.len() == 1 {
        return Some(sorted[0]);
    }
    let position = probability * (sorted.len() - 1) as f64;
    let lower = position.floor() as usize;
    let upper = position.ceil() as usize;
    let fraction = position - lower as f64;
    Some(sorted[lower] * (1.0 - fraction) + sorted[upper] * fraction)
}

fn scan_group_statistics(
    points: &[ScanSupportPoint],
    weights: &[Option<(f64, f64)>],
    key: impl Fn(&ScanSupportPoint) -> String,
) -> BTreeMap<String, WeightStatistics> {
    let mut groups: BTreeMap<String, (Vec<f64>, Vec<f64>)> = BTreeMap::new();
    for (point, values) in points.iter().zip(weights) {
        let Some((weight, ratio)) = values else {
            continue;
        };
        let group = groups.entry(key(point)).or_default();
        group.0.push(*weight);
        group.1.push(*ratio);
    }
    groups
        .into_iter()
        .map(|(key, (weights, ratios))| (key, WeightStatistics::from_weights(&weights, &ratios)))
        .collect()
}

pub fn run_scan_pdf_members(args: ScanPdfMembersArgs) -> Result<(), String> {
    ensure_fresh_output(&args.output, &["member_scan.json"])?;
    let mut provenance =
        HepMcRunProvenance::load(&args.nominal_run).map_err(|error| error.to_string())?;
    let nominal_set = provenance
        .pdf_set
        .clone()
        .ok_or_else(|| "nominal run does not declare a PDF set".to_owned())?;
    let pdf_set = args.pdf_set.clone().unwrap_or_else(|| nominal_set.clone());
    if pdf_set != nominal_set {
        return Err(format!(
            "scan set '{pdf_set}' differs from nominal run set '{nominal_set}'"
        ));
    }
    let nominal_member = provenance
        .pdf_member
        .ok_or_else(|| "nominal run does not declare a PDF member".to_owned())?;
    let support_contract = verified_support_contract(&provenance, &pdf_set, nominal_member)?;
    let nominal_pdf =
        LhapdfProvider::new(&pdf_set, nominal_member).map_err(|error| error.to_string())?;
    let member_count = nominal_pdf.member_count();
    let nominal_spec =
        PdfMemberSpec::new(&pdf_set, nominal_member).map_err(|error| error.to_string())?;
    let nominal_request = PdfReweightingRequest {
        source_pdf: nominal_spec.clone(),
        target_pdf: nominal_spec,
        source_run_identity: args.nominal_run.to_string_lossy().into_owned(),
        source_seed: provenance.generator_seed,
        event_weight_index: args.event_weight_index,
        denominator_policy: DenominatorPolicy::Stored,
        nominal_xf_relative_tolerance: args.nominal_xf_relative_tolerance,
        support_contract: support_contract.clone(),
    };
    let mut support = Vec::new();
    let mut invalid_nominal_events = 0usize;
    let mut reader = HepMcReader::open(args.nominal_run.join("events.hepmc3"))
        .map_err(|error| error.to_string())?;
    while args
        .max_events
        .is_none_or(|maximum| support.len() + invalid_nominal_events < maximum)
    {
        let Some(event) = reader.next_event().map_err(|error| error.to_string())? else {
            break;
        };
        if provenance.beam_particle_id_1.is_none() || provenance.beam_particle_id_2.is_none() {
            provenance.enrich_beam_ids_from_event(&event);
        }
        let result = reweight_event(
            &event,
            Some(&provenance),
            &nominal_request,
            &nominal_pdf,
            &nominal_pdf,
        )
        .map_err(|error| error.to_string())?;
        if result.valid {
            support.push(ScanSupportPoint {
                flavor: result.proton_side_flavor.expect("valid flavor"),
                x: result.proton_side_x.expect("valid x"),
                scale_gev: result.pdf_scale_gev.expect("valid scale"),
                stored_nominal_xf: result.stored_nominal_xf.expect("valid stored xf"),
                original_weight: result.original_event_weight.expect("valid weight"),
            });
        } else {
            invalid_nominal_events += 1;
        }
    }
    if support.is_empty() {
        return Err("nominal support scan produced no valid events".to_owned());
    }

    let mut entries = Vec::new();
    for member in 0..member_count {
        let member = i32::try_from(member).map_err(|_| "PDF member count exceeds i32")?;
        if member == nominal_member {
            continue;
        }
        let target = LhapdfProvider::new(&pdf_set, member).map_err(|error| error.to_string())?;
        let mut values = Vec::with_capacity(support.len());
        let mut invalid = BTreeMap::new();
        let mut absolute_logs = Vec::new();
        let mut zero_ratio_count = 0usize;
        for point in &support {
            match target.xfx_at_scale(point.flavor, point.x, point.scale_gev) {
                Ok(target_xf) if target_xf.is_finite() && target_xf >= 0.0 => {
                    let ratio = target_xf / point.stored_nominal_xf;
                    let weight = point.original_weight * ratio;
                    if ratio.is_finite() && weight.is_finite() && ratio >= 0.0 {
                        values.push(Some((weight, ratio)));
                        if ratio == 0.0 {
                            zero_ratio_count += 1;
                        } else {
                            absolute_logs.push(ratio.ln().abs());
                        }
                    } else {
                        values.push(None);
                        *invalid
                            .entry("non_finite_ratio_or_weight".to_owned())
                            .or_insert(0) += 1;
                    }
                }
                Ok(_) => {
                    values.push(None);
                    *invalid.entry("negative_target_xf".to_owned()).or_insert(0) += 1;
                }
                Err(_) => {
                    values.push(None);
                    *invalid
                        .entry("target_pdf_evaluation_failed".to_owned())
                        .or_insert(0) += 1;
                }
            }
        }
        absolute_logs.sort_by(f64::total_cmp);
        let weights: Vec<f64> = values.iter().flatten().map(|(weight, _)| *weight).collect();
        let ratios: Vec<f64> = values.iter().flatten().map(|(_, ratio)| *ratio).collect();
        let median = quantile(&absolute_logs, 0.5);
        let p95 = quantile(&absolute_logs, 0.95);
        let p99 = quantile(&absolute_logs, 0.99);
        let score = match (zero_ratio_count, median, p95, p99) {
            (0, Some(median), Some(p95), Some(p99)) => Some(median + 0.5 * p95 + 0.25 * p99),
            _ => None,
        };
        entries.push(MemberScanEntry {
            member,
            valid_ratio_fraction: ratios.len() as f64 / support.len() as f64,
            invalid_ratio_reasons: invalid,
            zero_ratio_count,
            median_absolute_log_ratio: median,
            p95_absolute_log_ratio: p95,
            p99_absolute_log_ratio: p99,
            deformation_score: score,
            predicted_weight_statistics: WeightStatistics::from_weights(&weights, &ratios),
            minimum_ratio: ratios.iter().copied().min_by(f64::total_cmp),
            maximum_ratio: ratios.iter().copied().max_by(f64::total_cmp),
            flavor_level_ess: scan_group_statistics(&support, &values, |point| {
                point.flavor.to_string()
            }),
            x_region_ess: scan_group_statistics(&support, &values, |point| match point.x {
                value if value < 1.0e-3 => "x_lt_1e-3".to_owned(),
                value if value < 1.0e-2 => "x_1e-3_to_1e-2".to_owned(),
                value if value < 1.0e-1 => "x_1e-2_to_1e-1".to_owned(),
                _ => "x_ge_1e-1".to_owned(),
            }),
        });
    }

    let mut scored: Vec<&MemberScanEntry> = entries
        .iter()
        .filter(|entry| entry.valid_ratio_fraction == 1.0 && entry.deformation_score.is_some())
        .collect();
    scored.sort_by(|left, right| {
        left.deformation_score
            .expect("scored entry")
            .total_cmp(&right.deformation_score.expect("scored entry"))
            .then(left.member.cmp(&right.member))
    });
    let mild = if scored.is_empty() {
        None
    } else {
        let scores: Vec<f64> = scored
            .iter()
            .map(|entry| entry.deformation_score.expect("scored entry"))
            .collect();
        let lower_quartile = quantile(&scores, 0.25).expect("non-empty scores");
        scored
            .iter()
            .min_by(|left, right| {
                (left.deformation_score.expect("scored entry") - lower_quartile)
                    .abs()
                    .total_cmp(
                        &(right.deformation_score.expect("scored entry") - lower_quartile).abs(),
                    )
                    .then(left.member.cmp(&right.member))
            })
            .copied()
    };
    let reusable: Vec<&MemberScanEntry> = scored
        .iter()
        .copied()
        .filter(|entry| {
            entry
                .predicted_weight_statistics
                .effective_sample_size
                .signed_fraction
                >= PDF_REUSE_ESS_FRACTION_THRESHOLD
        })
        .collect();
    let stress = reusable.last().copied().or_else(|| scored.last().copied());
    let stress_meets_ess_threshold = stress.is_some_and(|entry| {
        entry
            .predicted_weight_statistics
            .effective_sample_size
            .signed_fraction
            >= PDF_REUSE_ESS_FRACTION_THRESHOLD
    });
    let document = MemberScanDocument {
        schema_version: 1,
        created_at_utc: Utc::now().to_rfc3339(),
        repository_commit: option_env!("GIT_HASH").unwrap_or("unknown"),
        repository_dirty: option_env!("GIT_DIRTY") == Some("true"),
        package_version: env!("CARGO_PKG_VERSION"),
        rust_version: env!("RUSTC_VERSION"),
        command: std::env::args().collect(),
        nominal_run: &args.nominal_run,
        nominal_provenance: &provenance,
        pdf_set: &pdf_set,
        nominal_member,
        support_contract: &support_contract,
        event_count: support.len() + invalid_nominal_events,
        invalid_nominal_events,
        nominal_xf_relative_tolerance: args.nominal_xf_relative_tolerance,
        deformation_score_definition:
            "median(|log r|) + 0.5*p95(|log r|) + 0.25*p99(|log r|)",
        mild_selection_rule: "non-central member closest to the lower quartile of valid deformation scores; ties use lower member ID",
        stress_selection_rule: "strongest valid member with predicted ESS/N >= 0.20, otherwise strongest structurally valid member labeled expected reuse failure",
        selected_mild_member: mild.map(|entry| entry.member),
        selected_stress_member: stress.map(|entry| entry.member),
        stress_meets_ess_threshold,
        entries: &entries,
    };
    write_json(&args.output.join("member_scan.json"), &document)?;
    println!(
        "Scanned {} non-central members over {} valid events; mild={:?}, stress={:?}, stress ESS gate={}",
        entries.len(),
        support.len(),
        document.selected_mild_member,
        document.selected_stress_member,
        stress_meets_ess_threshold
    );
    Ok(())
}
