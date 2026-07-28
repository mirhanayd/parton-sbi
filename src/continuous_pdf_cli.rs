use parton_sbi::physics::{
    guard_shell_5_percent, pilot_grid_21x21, validate_positivity, ContinuousPdfContext,
    ContinuousPdfError, ContinuousPdfMetadata, D0BaselineMoments, D0DeltaMoments,
    ParameterPointIdentity, PdfNormalizations, PdfTheta, PositivityMinimum, Stage0Classification,
    SumRuleValidation, CONSTRUCTION_TOLERANCE, HEAVY_BOUNDARY_TOLERANCE_XF, INDEPENDENT_TOLERANCE,
    REFINEMENT_TOLERANCE,
};
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::path::{Path, PathBuf};
use std::time::Instant;

pub const VALIDATE_CONTINUOUS_PDF_HELP: &str =
    "Validate the Phase 1B-D0 continuous PDF boundary family

Usage:
  parton-sbi validate-continuous-pdf-family \
      --delta-v <VALUE> --lambda-sea <VALUE> [--output <DIRECTORY>]

  parton-sbi validate-continuous-pdf-family \
      --anchors --output <DIRECTORY>

  parton-sbi validate-continuous-pdf-family \
      --full-study --study-id <ID> --output <DIRECTORY>

Options:
  --pdf-set <SET>       Baseline LHAPDF set (default: CT18NLO).
  --pdf-member <INDEX>  Baseline member (default: 0).
  --delta-v <VALUE>     Valence tilt in the hard pilot interval [-0.20, 0.20].
  --lambda-sea <VALUE>  Log sea scale in the hard pilot interval [-0.25, 0.25].
  --anchors             Evaluate the nine mandatory center/axis/corner anchors.
  --full-study          Evaluate the exact 21x21 box and 5% diagnostic shell.
  --study-id <ID>       Required for --full-study.
  --output <DIRECTORY>  New output directory for machine-readable reports.

This D0 command constructs only input-scale mathematical boundary conditions.
It performs no APFEL evolution, grid export, PYTHIA coupling, or event generation.
";

#[derive(Debug, Clone, PartialEq)]
pub enum ContinuousPdfMode {
    Point(PdfTheta),
    Anchors,
    FullStudy,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ContinuousPdfCliArgs {
    pub set_name: String,
    pub member: i32,
    pub mode: ContinuousPdfMode,
    pub study_id: Option<String>,
    pub output: Option<PathBuf>,
    pub command: Vec<String>,
}

pub fn parse_validate_continuous_pdf(args: &[String]) -> Result<ContinuousPdfCliArgs, String> {
    let mut set_name = "CT18NLO".to_owned();
    let mut member = 0i32;
    let mut delta_v = None;
    let mut lambda_sea = None;
    let mut anchors = false;
    let mut full_study = false;
    let mut study_id = None;
    let mut output = None;
    let mut index = 0;
    while index < args.len() {
        let flag = args[index].as_str();
        if flag == "--anchors" {
            if anchors {
                return Err("duplicate --anchors".into());
            }
            anchors = true;
            index += 1;
            continue;
        }
        if flag == "--full-study" {
            if full_study {
                return Err("duplicate --full-study".into());
            }
            full_study = true;
            index += 1;
            continue;
        }
        let value = args
            .get(index + 1)
            .filter(|value| !value.starts_with("--"))
            .ok_or_else(|| format!("{flag} requires a value"))?;
        match flag {
            "--pdf-set" => {
                if value.trim().is_empty() {
                    return Err("--pdf-set must not be empty".into());
                }
                set_name = value.clone();
            }
            "--pdf-member" => {
                member = value
                    .parse()
                    .map_err(|_| format!("invalid --pdf-member: {value}"))?;
                if member < 0 {
                    return Err("--pdf-member must be non-negative".into());
                }
            }
            "--delta-v" => {
                if delta_v.is_some() {
                    return Err("duplicate --delta-v".into());
                }
                delta_v = Some(parse_finite(flag, value)?);
            }
            "--lambda-sea" => {
                if lambda_sea.is_some() {
                    return Err("duplicate --lambda-sea".into());
                }
                lambda_sea = Some(parse_finite(flag, value)?);
            }
            "--study-id" => {
                if study_id.replace(value.clone()).is_some() {
                    return Err("duplicate --study-id".into());
                }
            }
            "--output" => {
                if output.replace(PathBuf::from(value)).is_some() {
                    return Err("duplicate --output".into());
                }
            }
            _ => {
                return Err(format!(
                    "unknown validate-continuous-pdf-family option: {flag}"
                ))
            }
        }
        index += 2;
    }
    let selected_modes =
        usize::from(anchors) + usize::from(full_study) + usize::from(delta_v.is_some());
    if selected_modes != 1 {
        return Err("choose exactly one of an explicit theta, --anchors, or --full-study".into());
    }
    let mode = if anchors {
        if lambda_sea.is_some() {
            return Err("--lambda-sea cannot be combined with --anchors".into());
        }
        ContinuousPdfMode::Anchors
    } else if full_study {
        if lambda_sea.is_some() {
            return Err("--lambda-sea cannot be combined with --full-study".into());
        }
        if study_id.as_deref().is_none_or(str::is_empty) {
            return Err("--full-study requires a non-empty --study-id".into());
        }
        ContinuousPdfMode::FullStudy
    } else {
        let delta = delta_v.expect("explicit mode was counted");
        let sea = lambda_sea.ok_or("--delta-v requires --lambda-sea")?;
        ContinuousPdfMode::Point(PdfTheta::new(delta, sea).map_err(|error| error.to_string())?)
    };
    if !matches!(mode, ContinuousPdfMode::Point(_)) && output.is_none() {
        return Err("--anchors and --full-study require --output".into());
    }
    Ok(ContinuousPdfCliArgs {
        set_name,
        member,
        mode,
        study_id,
        output,
        command: std::env::args().collect(),
    })
}

fn parse_finite(flag: &str, value: &str) -> Result<f64, String> {
    let parsed = value
        .parse::<f64>()
        .map_err(|_| format!("invalid value for {flag}: {value}"))?;
    if parsed.is_finite() {
        Ok(parsed)
    } else {
        Err(format!("{flag} must be finite"))
    }
}

#[derive(Debug, Clone, Serialize)]
struct PointSummary {
    scope: &'static str,
    theta: PdfTheta,
    classification: Stage0Classification,
    normalizations: Option<PdfNormalizations>,
    identity: Option<ParameterPointIdentity>,
    sum_rules: Option<SumRuleValidation>,
    positivity: Option<PositivityMinimum>,
    error: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
struct CentralFlavorMetrics {
    flavor: i32,
    count: usize,
    median_absolute_error: f64,
    p95_absolute_error: f64,
    p99_absolute_error: f64,
    maximum_absolute_error: f64,
    median_relative_error: Option<f64>,
    p95_relative_error: Option<f64>,
    p99_relative_error: Option<f64>,
    maximum_relative_error: Option<f64>,
    worst_x: f64,
    outside_tolerance: usize,
}

#[derive(Debug, Clone, Serialize)]
struct CentralReconstructionReport {
    relative_tolerance: f64,
    relative_threshold_abs_xf: f64,
    absolute_tolerance: f64,
    passed: bool,
    flavors: Vec<CentralFlavorMetrics>,
}

#[derive(Debug, Clone, Serialize)]
struct Stage0Decision {
    schema_version: &'static str,
    study_id: String,
    decision: Stage0Classification,
    phase: &'static str,
    family: &'static str,
    pilot_point_count: usize,
    guard_shell_point_count: usize,
    invalid_pilot_points: usize,
    inconclusive_pilot_points: usize,
    central_reconstruction_passed: bool,
    metadata_passed: bool,
    heavy_boundary_tolerance_xf: f64,
    construction_sum_rule_tolerance: f64,
    independent_sum_rule_tolerance: f64,
    refinement_tolerance: f64,
    d1_authorized: bool,
    reasons: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
struct StudyManifest {
    schema_version: &'static str,
    study_id: String,
    command: Vec<String>,
    git_commit: String,
    git_dirty: bool,
    partonsbi_version: &'static str,
    rustc_version: &'static str,
    os_arch: &'static str,
    lhapdf_version: String,
    runtime_seconds: f64,
    pilot_point_count: usize,
    guard_shell_point_count: usize,
    artifact_sha256: BTreeMap<String, String>,
}

pub fn run_validate_continuous_pdf(args: ContinuousPdfCliArgs) -> Result<(), String> {
    let started = Instant::now();
    let context = ContinuousPdfContext::load(
        &args.set_name,
        args.member,
        (args.set_name == "CT18NLO" && args.member == 0).then_some(1),
    )
    .map_err(|error| error.to_string())?;
    let validation_grid = context.validation_x_grid();
    let baseline_moments = context
        .baseline_moments()
        .map_err(|error| error.to_string())?;
    let (pilot, guard): (Vec<PdfTheta>, Vec<PdfTheta>) = match args.mode {
        ContinuousPdfMode::Point(theta) => (vec![theta], Vec::new()),
        ContinuousPdfMode::Anchors => (mandatory_anchors(), Vec::new()),
        ContinuousPdfMode::FullStudy => (pilot_grid_21x21(), guard_shell_5_percent()),
    };
    let mut delta_cache = BTreeMap::<u64, D0DeltaMoments>::new();
    for theta in pilot.iter().chain(&guard) {
        delta_cache.entry(theta.delta_v.to_bits()).or_insert(
            context
                .delta_moments(theta.delta_v)
                .map_err(|error| error.to_string())?,
        );
    }
    let mut pilot_summaries = Vec::with_capacity(pilot.len());
    for theta in pilot {
        pilot_summaries.push(evaluate_point(
            &context,
            &baseline_moments,
            &delta_cache,
            theta,
            "pilot",
            &validation_grid,
        ));
    }
    let mut guard_summaries = Vec::with_capacity(guard.len());
    for theta in guard {
        guard_summaries.push(evaluate_point(
            &context,
            &baseline_moments,
            &delta_cache,
            theta,
            "guard_diagnostic",
            &validation_grid,
        ));
    }
    let central =
        central_reconstruction(&context, &baseline_moments, &delta_cache, &validation_grid)
            .map_err(|error| error.to_string())?;
    let study_id = args
        .study_id
        .clone()
        .unwrap_or_else(|| "d0_interactive_validation".into());
    let decision = aggregate_decision(&study_id, &pilot_summaries, &guard_summaries, &central);

    if let Some(output) = &args.output {
        write_reports(
            output,
            &args,
            &context.metadata,
            &baseline_moments,
            &pilot_summaries,
            &guard_summaries,
            &central,
            &decision,
            started.elapsed().as_secs_f64(),
        )?;
        println!("Stage 0 reports: {}", output.display());
    }
    println!(
        "Stage 0 {}: {} pilot point(s), {} guard diagnostic point(s), D1 authorized={}",
        decision_text(decision.decision),
        decision.pilot_point_count,
        decision.guard_shell_point_count,
        decision.d1_authorized
    );
    if let Some(point) = pilot_summaries.first() {
        if let Some(normalizations) = point.normalizations {
            println!(
                "theta=({:.8},{:.8}) A_u={:.12e} A_d={:.12e} S={:.12e} A_g={:.12e}",
                point.theta.delta_v,
                point.theta.lambda_sea,
                normalizations.a_u,
                normalizations.a_d,
                normalizations.sea_scale,
                normalizations.a_g
            );
        }
    }
    Ok(())
}

fn evaluate_point(
    context: &ContinuousPdfContext,
    baseline: &D0BaselineMoments,
    deltas: &BTreeMap<u64, D0DeltaMoments>,
    theta: PdfTheta,
    scope: &'static str,
    validation_grid: &[f64],
) -> PointSummary {
    let result = || -> Result<PointSummary, ContinuousPdfError> {
        let delta = deltas
            .get(&theta.delta_v.to_bits())
            .ok_or_else(|| ContinuousPdfError::MetadataInvalid("missing delta cache".into()))?;
        let point = context.construct_from_moments(theta, baseline, delta)?;
        let sums = context.sum_rules_from_moments(&point, baseline, delta);
        let positivity = validate_positivity(&point, validation_grid)?;
        let identity = point.canonical_identity()?;
        let repeat = point.canonical_identity()?;
        if identity != repeat {
            return Err(ContinuousPdfError::IdentitySerialization(
                "repeated construction was not byte-identical".into(),
            ));
        }
        let classification = if !sums.construction_passes()
            || !sums.independent_passes()
            || positivity.classification == Stage0Classification::Fail
        {
            Stage0Classification::Fail
        } else if positivity.classification == Stage0Classification::Inconclusive {
            Stage0Classification::Inconclusive
        } else {
            Stage0Classification::Pass
        };
        Ok(PointSummary {
            scope,
            theta,
            classification,
            normalizations: Some(point.normalizations),
            identity: Some(identity),
            sum_rules: Some(sums),
            positivity: Some(positivity),
            error: None,
        })
    }();
    match result {
        Ok(summary) => summary,
        Err(error) => PointSummary {
            scope,
            theta,
            classification: Stage0Classification::Fail,
            normalizations: None,
            identity: None,
            sum_rules: None,
            positivity: None,
            error: Some(error.to_string()),
        },
    }
}

fn mandatory_anchors() -> Vec<PdfTheta> {
    [
        (0.0, 0.0),
        (-0.20, 0.0),
        (0.20, 0.0),
        (0.0, -0.25),
        (0.0, 0.25),
        (-0.20, -0.25),
        (-0.20, 0.25),
        (0.20, -0.25),
        (0.20, 0.25),
    ]
    .into_iter()
    .map(|(delta, sea)| PdfTheta::new(delta, sea).expect("anchor is in the hard domain"))
    .collect()
}

fn central_reconstruction(
    context: &ContinuousPdfContext,
    baseline: &D0BaselineMoments,
    deltas: &BTreeMap<u64, D0DeltaMoments>,
    grid: &[f64],
) -> Result<CentralReconstructionReport, ContinuousPdfError> {
    let theta = PdfTheta::new(0.0, 0.0)?;
    let delta = deltas
        .get(&0.0f64.to_bits())
        .ok_or_else(|| ContinuousPdfError::MetadataInvalid("central delta is absent".into()))?;
    let point = context.construct_from_moments(theta, baseline, delta)?;
    let mut reports = Vec::new();
    let xmin = context.metadata.support.x_minimum;
    for flavor in [21, 2, -2, 1, -1, 3, -3, 4, -4, 5, -5] {
        let mut absolute = Vec::new();
        let mut relative = Vec::new();
        let mut outside = 0usize;
        let mut worst_x = f64::NAN;
        let mut worst_metric = -1.0f64;
        for &x in grid.iter().filter(|x| **x >= xmin) {
            let baseline_xf = context
                .baseline_densities(x)?
                .flavor(flavor)
                .expect("listed flavor")
                * x;
            let constructed_xf = point.densities(x)?.flavor(flavor).expect("listed flavor") * x;
            let abs = (constructed_xf - baseline_xf).abs();
            absolute.push(abs);
            let (failed, metric) = if baseline_xf.abs() >= 1.0e-8 {
                let rel = abs / baseline_xf.abs();
                relative.push(rel);
                (rel > 1.0e-6, rel)
            } else {
                (abs > 1.0e-10, abs / 1.0e-10)
            };
            if failed {
                outside += 1;
            }
            if metric > worst_metric {
                worst_metric = metric;
                worst_x = x;
            }
        }
        absolute.sort_by(f64::total_cmp);
        relative.sort_by(f64::total_cmp);
        reports.push(CentralFlavorMetrics {
            flavor,
            count: absolute.len(),
            median_absolute_error: percentile(&absolute, 0.5),
            p95_absolute_error: percentile(&absolute, 0.95),
            p99_absolute_error: percentile(&absolute, 0.99),
            maximum_absolute_error: absolute.last().copied().unwrap_or(f64::NAN),
            median_relative_error: optional_percentile(&relative, 0.5),
            p95_relative_error: optional_percentile(&relative, 0.95),
            p99_relative_error: optional_percentile(&relative, 0.99),
            maximum_relative_error: relative.last().copied(),
            worst_x,
            outside_tolerance: outside,
        });
    }
    Ok(CentralReconstructionReport {
        relative_tolerance: 1.0e-6,
        relative_threshold_abs_xf: 1.0e-8,
        absolute_tolerance: 1.0e-10,
        passed: reports.iter().all(|report| report.outside_tolerance == 0),
        flavors: reports,
    })
}

fn percentile(sorted: &[f64], fraction: f64) -> f64 {
    if sorted.is_empty() {
        return f64::NAN;
    }
    let rank = ((sorted.len() - 1) as f64 * fraction).ceil() as usize;
    sorted[rank]
}

fn optional_percentile(sorted: &[f64], fraction: f64) -> Option<f64> {
    (!sorted.is_empty()).then(|| percentile(sorted, fraction))
}

fn aggregate_decision(
    study_id: &str,
    pilot: &[PointSummary],
    guard: &[PointSummary],
    central: &CentralReconstructionReport,
) -> Stage0Decision {
    let invalid = pilot
        .iter()
        .filter(|point| point.classification == Stage0Classification::Fail)
        .count();
    let inconclusive = pilot
        .iter()
        .filter(|point| point.classification == Stage0Classification::Inconclusive)
        .count();
    let mut reasons = Vec::new();
    if invalid > 0 {
        reasons.push(format!(
            "{invalid} pilot points failed a fixed Stage 0 gate"
        ));
    }
    if inconclusive > 0 {
        reasons.push(format!(
            "{inconclusive} pilot points have an inconclusive positivity or quadrature result"
        ));
    }
    if !central.passed {
        reasons.push("central reconstruction exceeded its fixed pointwise tolerance".into());
    }
    let decision = if invalid > 0 || !central.passed {
        Stage0Classification::Fail
    } else if inconclusive > 0 {
        Stage0Classification::Inconclusive
    } else {
        Stage0Classification::Pass
    };
    if decision == Stage0Classification::Pass {
        reasons.push(
            "all 441 hard-domain points passed; guard-shell diagnostics do not define the prior"
                .into(),
        );
    }
    if guard
        .iter()
        .any(|point| point.classification != Stage0Classification::Pass)
    {
        reasons.push(
            "one or more guard-shell diagnostics failed; this does not alter the hard-box decision"
                .into(),
        );
    }
    Stage0Decision {
        schema_version: "partonsbi.phase1bd_d0_decision.v1",
        study_id: study_id.into(),
        decision,
        phase: "Phase 1B-D0",
        family: "ct18nlo_two_parameter_boundary_v1",
        pilot_point_count: pilot.len(),
        guard_shell_point_count: guard.len(),
        invalid_pilot_points: invalid,
        inconclusive_pilot_points: inconclusive,
        central_reconstruction_passed: central.passed,
        metadata_passed: true,
        heavy_boundary_tolerance_xf: HEAVY_BOUNDARY_TOLERANCE_XF,
        construction_sum_rule_tolerance: CONSTRUCTION_TOLERANCE,
        independent_sum_rule_tolerance: INDEPENDENT_TOLERANCE,
        refinement_tolerance: REFINEMENT_TOLERANCE,
        d1_authorized: decision == Stage0Classification::Pass,
        reasons,
    }
}

#[allow(clippy::too_many_arguments)]
fn write_reports(
    output: &Path,
    args: &ContinuousPdfCliArgs,
    metadata: &ContinuousPdfMetadata,
    baseline_moments: &D0BaselineMoments,
    pilot: &[PointSummary],
    guard: &[PointSummary],
    central: &CentralReconstructionReport,
    decision: &Stage0Decision,
    runtime_seconds: f64,
) -> Result<(), String> {
    if output.exists() {
        return Err(format!(
            "output directory already exists and will not be overwritten: {}",
            output.display()
        ));
    }
    std::fs::create_dir_all(output)
        .map_err(|error| format!("failed to create {}: {error}", output.display()))?;
    let mut hashes = BTreeMap::new();
    write_json(output, "metadata_report.json", metadata, &mut hashes)?;
    write_json(
        output,
        "integration_baseline.json",
        baseline_moments,
        &mut hashes,
    )?;
    write_json(output, "point_summary.json", pilot, &mut hashes)?;
    let sum_rules = pilot
        .iter()
        .map(|point| (&point.theta, &point.sum_rules, point.classification))
        .collect::<Vec<_>>();
    write_json(output, "sum_rule_report.json", &sum_rules, &mut hashes)?;
    let positivity = pilot
        .iter()
        .map(|point| (&point.theta, &point.positivity, point.classification))
        .collect::<Vec<_>>();
    write_json(output, "positivity_report.json", &positivity, &mut hashes)?;
    write_json(
        output,
        "central_reconstruction_report.json",
        central,
        &mut hashes,
    )?;
    write_json(output, "guard_shell_diagnostic.json", guard, &mut hashes)?;
    write_json(output, "stage0_decision.json", decision, &mut hashes)?;
    let (git_commit, git_dirty) = git_provenance()?;
    let manifest = StudyManifest {
        schema_version: "partonsbi.phase1bd_d0_study.v1",
        study_id: decision.study_id.clone(),
        command: args.command.clone(),
        git_commit,
        git_dirty,
        partonsbi_version: env!("CARGO_PKG_VERSION"),
        rustc_version: env!("RUSTC_VERSION"),
        os_arch: env!("OS_ARCH"),
        lhapdf_version: metadata.lhapdf_version.clone(),
        runtime_seconds,
        pilot_point_count: pilot.len(),
        guard_shell_point_count: guard.len(),
        artifact_sha256: hashes,
    };
    let mut ignored = BTreeMap::new();
    write_json(output, "study_manifest.json", &manifest, &mut ignored)
}

fn write_json<T: Serialize + ?Sized>(
    output: &Path,
    name: &str,
    value: &T,
    hashes: &mut BTreeMap<String, String>,
) -> Result<(), String> {
    let bytes =
        serde_json::to_vec_pretty(value).map_err(|error| format!("serialize {name}: {error}"))?;
    let path = output.join(name);
    std::fs::write(&path, &bytes).map_err(|error| format!("write {}: {error}", path.display()))?;
    hashes.insert(name.into(), format!("sha256:{:x}", Sha256::digest(&bytes)));
    Ok(())
}

fn git_provenance() -> Result<(String, bool), String> {
    let commit = std::process::Command::new("git")
        .args(["rev-parse", "HEAD"])
        .output()
        .map_err(|error| format!("git rev-parse failed: {error}"))?;
    if !commit.status.success() {
        return Err("git rev-parse HEAD failed".into());
    }
    let status = std::process::Command::new("git")
        .args(["status", "--porcelain", "--untracked-files=no"])
        .output()
        .map_err(|error| format!("git status failed: {error}"))?;
    if !status.status.success() {
        return Err("git status --porcelain failed".into());
    }
    Ok((
        String::from_utf8_lossy(&commit.stdout).trim().into(),
        !status.stdout.is_empty(),
    ))
}

fn decision_text(decision: Stage0Classification) -> &'static str {
    match decision {
        Stage0Classification::Pass => "PASS",
        Stage0Classification::Fail => "FAIL",
        Stage0Classification::Inconclusive => "INCONCLUSIVE",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parser_accepts_point_and_rejects_mixed_modes() {
        let point = parse_validate_continuous_pdf(&[
            "--delta-v".into(),
            "-0".into(),
            "--lambda-sea".into(),
            "0.2".into(),
        ])
        .unwrap();
        match point.mode {
            ContinuousPdfMode::Point(theta) => {
                assert_eq!(theta.delta_v.to_bits(), 0.0f64.to_bits());
            }
            _ => panic!("expected point mode"),
        }
        assert!(parse_validate_continuous_pdf(&[
            "--anchors".into(),
            "--full-study".into(),
            "--output".into(),
            "outputs/test".into(),
        ])
        .is_err());
    }

    #[test]
    fn fail_and_inconclusive_aggregation_never_authorize_d1() {
        let central = CentralReconstructionReport {
            relative_tolerance: 1e-6,
            relative_threshold_abs_xf: 1e-8,
            absolute_tolerance: 1e-10,
            passed: true,
            flavors: vec![],
        };
        let point = |classification| PointSummary {
            scope: "pilot",
            theta: PdfTheta::new(0.0, 0.0).unwrap(),
            classification,
            normalizations: None,
            identity: None,
            sum_rules: None,
            positivity: None,
            error: None,
        };
        let fail = aggregate_decision("test", &[point(Stage0Classification::Fail)], &[], &central);
        assert!(!fail.d1_authorized);
        let inconclusive = aggregate_decision(
            "test",
            &[point(Stage0Classification::Inconclusive)],
            &[],
            &central,
        );
        assert!(!inconclusive.d1_authorized);
    }
}
