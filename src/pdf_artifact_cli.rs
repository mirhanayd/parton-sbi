use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::time::Instant;

use parton_sbi::physics::{
    build_or_load_artifact, default_cache_root, evaluate_artifact, evolve_grid, ArtifactGrid,
    ContinuousPdfContext, EvolvedGrid, LhapdfProvider, PdfTheta, ALPHA_S_ABSOLUTE_TOLERANCE,
    ALPHA_S_RELATIVE_TOLERANCE, BOUNDARY_ABSOLUTE_TOLERANCE, BOUNDARY_RELATIVE_TOLERANCE,
    D1_FLAVORS, ROUND_TRIP_ABSOLUTE_TOLERANCE, ROUND_TRIP_RELATIVE_TOLERANCE,
};
use serde::{Deserialize, Serialize};

pub const VALIDATE_PDF_ARTIFACT_HELP: &str =
    "Validate the Phase 1B-D1 APFEL++/LHAPDF artifact contract

Usage:
  parton-sbi validate-pdf-artifact --delta-v <VALUE> --lambda-sea <VALUE>
  parton-sbi validate-pdf-artifact --anchors
  parton-sbi validate-pdf-artifact --study --study-id <ID> --output <DIRECTORY>

Modes:
  one point     Build and validate one approved D0R v2 parameter point.
  --anchors     Validate the center, four axis endpoints, and four corners.
  --study       Run the complete clean-provenance nine-anchor Stage 1 study.

This command writes deterministic one-member LHAPDF6 artifacts to the ignored
repository-local .external cache. It does not invoke PYTHIA or generate events.
";

#[derive(Debug, Clone, PartialEq)]
pub struct PdfArtifactCliArgs {
    mode: ArtifactCliMode,
    study_id: Option<String>,
    output: Option<PathBuf>,
}

#[derive(Debug, Clone, PartialEq)]
enum ArtifactCliMode {
    Point(PdfTheta),
    Anchors,
    Study,
}

pub fn parse_validate_pdf_artifact(args: &[String]) -> Result<PdfArtifactCliArgs, String> {
    let mut delta_v = None;
    let mut lambda_sea = None;
    let mut anchors = false;
    let mut study = false;
    let mut study_id = None;
    let mut output = None;
    let mut index = 0;
    while index < args.len() {
        let flag = args[index].as_str();
        match flag {
            "--anchors" => {
                anchors = true;
                index += 1;
            }
            "--study" => {
                study = true;
                index += 1;
            }
            "--delta-v" | "--lambda-sea" | "--study-id" | "--output" => {
                let value = args
                    .get(index + 1)
                    .ok_or_else(|| format!("{flag} requires a value"))?;
                match flag {
                    "--delta-v" => {
                        delta_v = Some(
                            value
                                .parse::<f64>()
                                .map_err(|_| "--delta-v must be numeric".to_string())?,
                        )
                    }
                    "--lambda-sea" => {
                        lambda_sea = Some(
                            value
                                .parse::<f64>()
                                .map_err(|_| "--lambda-sea must be numeric".to_string())?,
                        )
                    }
                    "--study-id" => study_id = Some(value.clone()),
                    "--output" => output = Some(PathBuf::from(value)),
                    _ => unreachable!(),
                }
                index += 2;
            }
            _ => return Err(format!("unknown validate-pdf-artifact option: {flag}")),
        }
    }
    let selected = usize::from(anchors)
        + usize::from(study)
        + usize::from(delta_v.is_some() || lambda_sea.is_some());
    if selected != 1 {
        return Err("select exactly one of an explicit theta, --anchors, or --study".into());
    }
    let mode = if anchors {
        ArtifactCliMode::Anchors
    } else if study {
        if study_id.is_none() || output.is_none() {
            return Err("--study requires --study-id and --output".into());
        }
        ArtifactCliMode::Study
    } else {
        ArtifactCliMode::Point(
            PdfTheta::new(
                delta_v.ok_or("--delta-v is required")?,
                lambda_sea.ok_or("--lambda-sea is required")?,
            )
            .map_err(|error| error.to_string())?,
        )
    };
    Ok(PdfArtifactCliArgs {
        mode,
        study_id,
        output,
    })
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
enum Stage1Decision {
    Pass,
    Fail,
    Inconclusive,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct FlavorMetric {
    count: usize,
    maximum_relative_error: f64,
    maximum_absolute_error: f64,
    outside_tolerance: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct AnchorReport {
    name: String,
    theta: PdfTheta,
    artifact_hash: String,
    set_name: String,
    boundary_maximum_relative_error: f64,
    boundary_maximum_absolute_error: f64,
    round_trip: BTreeMap<i32, FlavorMetric>,
    alpha_s_maximum_relative_error: f64,
    alpha_s_maximum_absolute_error: f64,
    maximum_evolved_sum_rule_residual: f64,
    evolved_sum_rule_residual_at_q0: f64,
    evolved_sum_rule_worst_q_gev: f64,
    raw_ct18_center_fidelity: Option<FlavorMetric>,
    all_values_finite: bool,
    observable_nonnegative: bool,
    byte_reproducible: bool,
    passed: bool,
    reasons: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Stage1Report {
    schema_version: String,
    study_id: String,
    exact_command: Vec<String>,
    git_commit: String,
    git_dirty: bool,
    baseline_version: String,
    family_version: String,
    apfelxx_version: String,
    lhapdf_version: String,
    anchor_count: usize,
    anchors: Vec<AnchorReport>,
    stage1_decision: Stage1Decision,
    d2_authorization_candidate: bool,
    d2_authorized: bool,
    runtime_seconds: f64,
    limitations: Vec<String>,
}

pub fn run_validate_pdf_artifact(args: PdfArtifactCliArgs) -> Result<(), String> {
    let context = ContinuousPdfContext::load_ct18nlo_v2().map_err(|error| error.to_string())?;
    let grid = ArtifactGrid::from_context(&context).map_err(|error| error.to_string())?;
    let (commit, dirty) = git_state()?;
    let thetas = match args.mode {
        ArtifactCliMode::Point(theta) => vec![("point".to_owned(), theta)],
        ArtifactCliMode::Anchors | ArtifactCliMode::Study => mandatory_anchors()?,
    };
    if matches!(args.mode, ArtifactCliMode::Study) && dirty {
        return Err("Stage 1 study requires a clean committed implementation".into());
    }
    let started = Instant::now();
    let mut anchors = Vec::new();
    for (name, theta) in thetas {
        anchors.push(validate_anchor(&context, &grid, name, theta)?);
    }
    let all_pass = anchors.iter().all(|anchor| anchor.passed);
    let decision = if all_pass {
        Stage1Decision::Pass
    } else {
        Stage1Decision::Fail
    };
    let report = Stage1Report {
        schema_version: "partonsbi.phase1bd.d1.study.v1".into(),
        study_id: args.study_id.clone().unwrap_or_else(|| "smoke".into()),
        exact_command: std::env::args().collect(),
        git_commit: commit,
        git_dirty: dirty,
        baseline_version: "ct18nlo_member0_sumrule_projected_boundary_v2".into(),
        family_version: "ct18nlo_two_parameter_boundary_v2".into(),
        apfelxx_version: "4.8.0".into(),
        lhapdf_version: context.metadata.lhapdf_version.clone(),
        anchor_count: anchors.len(),
        anchors,
        stage1_decision: decision,
        d2_authorization_candidate: decision == Stage1Decision::Pass,
        d2_authorized: false,
        runtime_seconds: started.elapsed().as_secs_f64(),
        limitations: vec![
            "Stage 1 validates evolution and artifact transport only; it does not validate PYTHIA coupling.".into(),
            "The compact observable gate is photon-only and parton-level; electroweak and detector effects are absent.".into(),
        ],
    };
    if let Some(output) = args.output {
        fs::create_dir_all(&output).map_err(|error| error.to_string())?;
        let target = output.join("stage1_decision.json");
        if target.exists() {
            return Err(format!("refusing to overwrite {}", target.display()));
        }
        fs::write(
            &target,
            serde_json::to_vec_pretty(&report).map_err(|error| error.to_string())?,
        )
        .map_err(|error| error.to_string())?;
    }
    println!(
        "{}",
        serde_json::to_string_pretty(&report).map_err(|error| error.to_string())?
    );
    Ok(())
}

fn mandatory_anchors() -> Result<Vec<(String, PdfTheta)>, String> {
    [
        ("center", 0.0, 0.0),
        ("delta_min", -0.20, 0.0),
        ("delta_max", 0.20, 0.0),
        ("sea_min", 0.0, -0.25),
        ("sea_max", 0.0, 0.25),
        ("corner_min_min", -0.20, -0.25),
        ("corner_min_max", -0.20, 0.25),
        ("corner_max_min", 0.20, -0.25),
        ("corner_max_max", 0.20, 0.25),
    ]
    .into_iter()
    .map(|(name, delta, sea)| {
        PdfTheta::new(delta, sea)
            .map(|theta| (name.to_owned(), theta))
            .map_err(|error| error.to_string())
    })
    .collect()
}

fn validate_anchor(
    context: &ContinuousPdfContext,
    grid: &ArtifactGrid,
    name: String,
    theta: PdfTheta,
) -> Result<AnchorReport, String> {
    let artifact = build_or_load_artifact(context, theta, &default_cache_root())
        .map_err(|error| error.to_string())?;
    let validation_xs = with_log_midpoints(&grid.x_knots);
    let validation_qs = with_log_midpoints(&grid.q_knots_gev);
    let direct = evolve_grid(context, theta, &validation_xs, &validation_qs)
        .map_err(|error| error.to_string())?;
    let loaded = evaluate_artifact(&artifact, &validation_xs, &validation_qs)
        .map_err(|error| error.to_string())?;
    let point = context
        .construct(theta)
        .map_err(|error| error.to_string())?;
    let mut boundary_rel: f64 = 0.0;
    let mut boundary_abs: f64 = 0.0;
    for (ix, x) in validation_xs.iter().copied().enumerate() {
        let densities = point.densities(x).map_err(|error| error.to_string())?;
        for flavor in D1_FLAVORS {
            let expected = x * densities
                .flavor(flavor)
                .ok_or_else(|| format!("missing flavor {flavor}"))?;
            let actual = direct.xf(flavor, ix, 0).ok_or("missing direct boundary")?;
            let absolute = (actual - expected).abs();
            boundary_abs = boundary_abs.max(absolute);
            if expected.abs() >= 1e-14 {
                boundary_rel = boundary_rel.max(absolute / expected.abs());
            }
        }
    }
    let mut round_trip = BTreeMap::new();
    let mut all_values_finite = true;
    for flavor in D1_FLAVORS {
        let mut metric = FlavorMetric {
            count: 0,
            maximum_relative_error: 0.0,
            maximum_absolute_error: 0.0,
            outside_tolerance: 0,
        };
        let iflavor = direct
            .flavors
            .iter()
            .position(|id| *id == flavor)
            .expect("declared flavor");
        for index in iflavor..direct.xf_values.len() {
            if index % D1_FLAVORS.len() != iflavor {
                continue;
            }
            let expected = direct.xf_values[index];
            let actual = loaded.xf_values[index];
            all_values_finite &= expected.is_finite() && actual.is_finite();
            let absolute = (actual - expected).abs();
            let relative = if expected == 0.0 {
                0.0
            } else {
                absolute / expected.abs()
            };
            metric.count += 1;
            metric.maximum_absolute_error = metric.maximum_absolute_error.max(absolute);
            metric.maximum_relative_error = metric.maximum_relative_error.max(relative);
            if !within_round_trip(expected, actual) {
                metric.outside_tolerance += 1;
            }
        }
        round_trip.insert(flavor, metric);
    }
    let direct_alpha_knots = direct
        .alpha_s_values
        .iter()
        .step_by(2)
        .copied()
        .collect::<Vec<_>>();
    let loaded_alpha_knots = loaded
        .alpha_s_values
        .iter()
        .step_by(2)
        .copied()
        .collect::<Vec<_>>();
    let (alpha_rel, alpha_abs) = maximum_errors(&direct_alpha_knots, &loaded_alpha_knots);
    let sum_rule_residual = |values: &[f64; 3]| {
        (values[0] - 2.0)
            .abs()
            .max((values[1] - 1.0).abs())
            .max((values[2] - 1.0).abs())
    };
    let evolved_sum_rule_residual_at_q0 = sum_rule_residual(&direct.sum_rules[0]);
    let (evolved_sum_rule_worst_q_gev, maximum_evolved_sum_rule_residual) = direct
        .qs_gev
        .iter()
        .copied()
        .zip(direct.sum_rules.iter().map(sum_rule_residual))
        .max_by(|left, right| left.1.total_cmp(&right.1))
        .expect("evolution grid is non-empty");
    let raw_ct18_center_fidelity = if theta == PdfTheta::new(0.0, 0.0).expect("center") {
        let raw = LhapdfProvider::new("CT18NLO", 0).map_err(|error| error.to_string())?;
        let mut metric = FlavorMetric {
            count: 0,
            maximum_relative_error: 0.0,
            maximum_absolute_error: 0.0,
            outside_tolerance: 0,
        };
        for (iq, q) in validation_qs.iter().copied().enumerate() {
            for (ix, x) in validation_xs.iter().copied().enumerate() {
                for flavor in D1_FLAVORS {
                    let expected = raw
                        .xfx_at_scale(flavor, x, q)
                        .map_err(|error| error.to_string())?;
                    let actual = direct.xf(flavor, ix, iq).ok_or("missing direct value")?;
                    let absolute = (actual - expected).abs();
                    let relative = if expected == 0.0 {
                        0.0
                    } else {
                        absolute / expected.abs()
                    };
                    metric.count += 1;
                    metric.maximum_absolute_error = metric.maximum_absolute_error.max(absolute);
                    metric.maximum_relative_error = metric.maximum_relative_error.max(relative);
                    if expected.abs() >= 1e-8 && relative > 2.0e-3 {
                        metric.outside_tolerance += 1;
                    }
                }
            }
        }
        Some(metric)
    } else {
        None
    };
    let observable_nonnegative = compact_observable_gate(&loaded);
    let repeated = build_or_load_artifact(context, theta, &default_cache_root())
        .map_err(|error| error.to_string())?;
    let byte_reproducible = artifact.manifest == repeated.manifest;
    let mut reasons = Vec::new();
    if boundary_rel > BOUNDARY_RELATIVE_TOLERANCE && boundary_abs > BOUNDARY_ABSOLUTE_TOLERANCE {
        reasons.push("input boundary callback mismatch".into());
    }
    if round_trip
        .values()
        .any(|metric| metric.outside_tolerance > 0)
    {
        reasons.push("LHAPDF round-trip tolerance failure".into());
    }
    if alpha_rel > ALPHA_S_RELATIVE_TOLERANCE && alpha_abs > ALPHA_S_ABSOLUTE_TOLERANCE {
        reasons.push("alpha_s round-trip tolerance failure".into());
    }
    if maximum_evolved_sum_rule_residual > 1.0e-5 {
        reasons.push("evolved APFEL sum-rule tolerance failure".into());
    }
    if raw_ct18_center_fidelity
        .as_ref()
        .is_some_and(|metric| metric.outside_tolerance > 0)
    {
        reasons.push("raw CT18NLO evolved-fidelity diagnostic exceeds 2e-3".into());
    }
    if !all_values_finite {
        reasons.push("non-finite evolved value".into());
    }
    if !observable_nonnegative {
        reasons.push("photon-only observable gate failure".into());
    }
    if !byte_reproducible {
        reasons.push("artifact manifest is not reproducible".into());
    }
    Ok(AnchorReport {
        name,
        theta,
        artifact_hash: artifact.manifest.artifact_hash.clone(),
        set_name: artifact.manifest.set_name.clone(),
        boundary_maximum_relative_error: boundary_rel,
        boundary_maximum_absolute_error: boundary_abs,
        round_trip,
        alpha_s_maximum_relative_error: alpha_rel,
        alpha_s_maximum_absolute_error: alpha_abs,
        maximum_evolved_sum_rule_residual,
        evolved_sum_rule_residual_at_q0,
        evolved_sum_rule_worst_q_gev,
        raw_ct18_center_fidelity,
        all_values_finite,
        observable_nonnegative,
        byte_reproducible,
        passed: reasons.is_empty(),
        reasons,
    })
}

fn within_round_trip(expected: f64, actual: f64) -> bool {
    let absolute = (actual - expected).abs();
    if expected.abs() >= 1e-8 {
        absolute / expected.abs() <= ROUND_TRIP_RELATIVE_TOLERANCE
    } else {
        absolute <= ROUND_TRIP_ABSOLUTE_TOLERANCE
    }
}

fn with_log_midpoints(knots: &[f64]) -> Vec<f64> {
    let mut values = Vec::with_capacity(knots.len() * 2 - 1);
    for pair in knots.windows(2) {
        values.push(pair[0]);
        values.push(((pair[0].ln() + pair[1].ln()) / 2.0).exp());
    }
    values.push(*knots.last().expect("artifact grids are non-empty"));
    values
}

fn maximum_errors(expected: &[f64], actual: &[f64]) -> (f64, f64) {
    expected.iter().zip(actual).fold(
        (0.0_f64, 0.0_f64),
        |(max_rel, max_abs), (expected, actual)| {
            let absolute = (actual - expected).abs();
            let relative = if *expected == 0.0 {
                0.0
            } else {
                absolute / expected.abs()
            };
            (max_rel.max(relative), max_abs.max(absolute))
        },
    )
}

fn compact_observable_gate(grid: &EvolvedGrid) -> bool {
    let charge = |flavor: i32| match flavor.abs() {
        2 | 4 => 4.0 / 9.0,
        1 | 3 | 5 => 1.0 / 9.0,
        _ => 0.0,
    };
    for iq in 0..grid.qs_gev.len() {
        let q2 = grid.qs_gev[iq] * grid.qs_gev[iq];
        if !(3.5..=10_000.0).contains(&q2) {
            continue;
        }
        for ix in 0..grid.xs.len() {
            if !(1.0e-4..=0.8).contains(&grid.xs[ix]) {
                continue;
            }
            let f2 = [1, 2, 3, 4, 5]
                .into_iter()
                .map(|flavor| {
                    charge(flavor)
                        * (grid.xf(flavor, ix, iq).unwrap_or(f64::NAN)
                            + grid.xf(-flavor, ix, iq).unwrap_or(f64::NAN))
                })
                .sum::<f64>();
            if !f2.is_finite() || f2 < 0.0 {
                return false;
            }
        }
    }
    true
}

fn git_state() -> Result<(String, bool), String> {
    let commit = Command::new("git")
        .args(["rev-parse", "HEAD"])
        .output()
        .map_err(|error| error.to_string())?;
    let status = Command::new("git")
        .args(["status", "--porcelain"])
        .output()
        .map_err(|error| error.to_string())?;
    if !commit.status.success() || !status.status.success() {
        return Err("git provenance query failed".into());
    }
    Ok((
        String::from_utf8_lossy(&commit.stdout).trim().to_owned(),
        !status.stdout.is_empty(),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parser_requires_one_explicit_mode() {
        assert!(parse_validate_pdf_artifact(&[]).is_err());
        assert!(parse_validate_pdf_artifact(&["--anchors".into(), "--study".into()]).is_err());
        let point = parse_validate_pdf_artifact(&[
            "--delta-v".into(),
            "0".into(),
            "--lambda-sea".into(),
            "-0".into(),
        ])
        .unwrap();
        assert_eq!(
            point.mode,
            ArtifactCliMode::Point(PdfTheta::new(0.0, 0.0).unwrap())
        );
    }

    #[test]
    fn exactly_nine_unique_anchors_are_predeclared() {
        let anchors = mandatory_anchors().unwrap();
        assert_eq!(anchors.len(), 9);
        let unique = anchors
            .iter()
            .map(|(_, theta)| (theta.delta_v.to_bits(), theta.lambda_sea.to_bits()))
            .collect::<std::collections::BTreeSet<_>>();
        assert_eq!(unique.len(), 9);
    }

    #[test]
    fn d2_is_never_actual_authorization_from_stage1_aggregation() {
        assert!(Stage1Decision::Pass != Stage1Decision::Fail);
    }
}
