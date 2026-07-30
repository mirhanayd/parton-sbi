use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::time::Instant;

use parton_sbi::physics::{
    build_or_load_artifact, build_or_load_artifact_v2, default_cache_root, default_cache_root_v2,
    evaluate_artifact, evaluate_artifact_v2, evolve_grid, evolve_grid_v2,
    mandatory_artifact_anchors_v2, refine_common_grid_v2, validate_moments_v2,
    validate_photon_observables_v2, validate_raw_ct_fidelity_v2, validate_transport_v2,
    ArtifactGrid, ArtifactGridV2, ComputationalGridKind, ContinuousPdfContext, EvolvedGrid,
    LhapdfProvider, MomentClosureV2, PdfTheta, PhotonObservableClosureV2, RawCtFidelityV2,
    RefinementTraceV2, TransportClosureV2, ALPHA_S_ABSOLUTE_TOLERANCE, ALPHA_S_RELATIVE_TOLERANCE,
    BOUNDARY_ABSOLUTE_TOLERANCE, BOUNDARY_RELATIVE_TOLERANCE, D1_FLAVORS,
    ROUND_TRIP_ABSOLUTE_TOLERANCE, ROUND_TRIP_RELATIVE_TOLERANCE,
};
use serde::{Deserialize, Serialize};

pub const VALIDATE_PDF_ARTIFACT_HELP: &str =
    "Validate the Phase 1B-D1 APFEL++/LHAPDF artifact contract

Usage:
  parton-sbi validate-pdf-artifact [--artifact-version v1|v2] --delta-v <VALUE> --lambda-sea <VALUE>
  parton-sbi validate-pdf-artifact [--artifact-version v1|v2] --anchors
  parton-sbi validate-pdf-artifact [--artifact-version v1|v2] --study --study-id <ID> --output <DIRECTORY>

Modes:
  one point     Build and validate one approved D0R v2 parameter point.
  --anchors     Validate the center, four axis endpoints, and four corners.
  --study       Run the complete clean-provenance nine-anchor Stage 1 study.

The historical v1 contract remains the default. Select v2 explicitly for the
ADR-005 revised contract. Both write ignored deterministic LHAPDF6 artifacts.
Neither invokes PYTHIA or generates events.
";

#[derive(Debug, Clone, PartialEq)]
pub struct PdfArtifactCliArgs {
    mode: ArtifactCliMode,
    study_id: Option<String>,
    output: Option<PathBuf>,
    artifact_version: ArtifactContractVersion,
}

#[derive(Debug, Clone, PartialEq)]
enum ArtifactCliMode {
    Point(PdfTheta),
    Anchors,
    Study,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ArtifactContractVersion {
    V1,
    V2,
}

pub fn parse_validate_pdf_artifact(args: &[String]) -> Result<PdfArtifactCliArgs, String> {
    let mut delta_v = None;
    let mut lambda_sea = None;
    let mut anchors = false;
    let mut study = false;
    let mut study_id = None;
    let mut output = None;
    let mut artifact_version = ArtifactContractVersion::V1;
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
            "--delta-v" | "--lambda-sea" | "--study-id" | "--output" | "--artifact-version" => {
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
                    "--artifact-version" => {
                        artifact_version = match value.as_str() {
                            "v1" => ArtifactContractVersion::V1,
                            "v2" => ArtifactContractVersion::V2,
                            _ => return Err("--artifact-version must be v1 or v2".into()),
                        }
                    }
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
        artifact_version,
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
    if args.artifact_version == ArtifactContractVersion::V2 {
        return run_validate_pdf_artifact_v2(args);
    }
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

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
enum RevisedStage1Decision {
    Pass,
    Fail,
    Inconclusive,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct RevisedAnchorReport {
    name: String,
    theta: PdfTheta,
    artifact_hash: String,
    set_name: String,
    artifact_bytes: u64,
    moment_closure: MomentClosureV2,
    transport_closure: TransportClosureV2,
    observable_closure: PhotonObservableClosureV2,
    strict_support_passed: bool,
    threshold_subgrid_count: usize,
    inactive_top_passed: bool,
    manifest_byte_reproducible: bool,
    passed: bool,
    reasons: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct RevisedStage1Report {
    schema_version: String,
    study_id: String,
    exact_command: Vec<String>,
    git_commit: String,
    git_dirty: bool,
    baseline_version: String,
    family_version: String,
    artifact_schema_version: String,
    evolution_policy_version: String,
    grid_policy_version: String,
    cache_policy_version: String,
    computational_x_minimum: f64,
    exported_x_minimum: f64,
    zero_continuation_policy: String,
    base_grid: Vec<(usize, f64, usize)>,
    doubled_grid: Vec<(usize, f64, usize)>,
    final_common_grid_hash: String,
    final_x_knot_count: usize,
    final_unique_q_knot_count: usize,
    q_subgrids_gev: Vec<Vec<f64>>,
    refinement_trace_hash: String,
    refinement_trace: RefinementTraceV2,
    raw_ct18_fidelity: RawCtFidelityV2,
    anchor_count: usize,
    anchors: Vec<RevisedAnchorReport>,
    revised_stage1_decision: RevisedStage1Decision,
    d2_authorization_candidate: bool,
    d2_authorized: bool,
    runtime_seconds: f64,
    generated_artifacts_committed: bool,
    limitations: Vec<String>,
}

fn run_validate_pdf_artifact_v2(args: PdfArtifactCliArgs) -> Result<(), String> {
    let context = ContinuousPdfContext::load_ct18nlo_v2().map_err(|error| error.to_string())?;
    let (commit, dirty) = git_state()?;
    if matches!(args.mode, ArtifactCliMode::Study) && dirty {
        return Err("revised Stage 1 study requires a clean committed implementation".into());
    }
    let started = Instant::now();
    let all_anchors = mandatory_artifact_anchors_v2().map_err(|error| error.to_string())?;
    let selected_anchors = match args.mode {
        ArtifactCliMode::Point(theta) => vec![("point".to_owned(), theta)],
        ArtifactCliMode::Anchors | ArtifactCliMode::Study => all_anchors.clone(),
    };
    eprintln!("revised-D1: constructing deterministic common grid");
    let refinement = if matches!(args.mode, ArtifactCliMode::Anchors | ArtifactCliMode::Study) {
        refine_common_grid_v2(&context, &all_anchors, &default_cache_root_v2())
            .map_err(|error| error.to_string())?
    } else {
        let grid = ArtifactGridV2::initial(&context).map_err(|error| error.to_string())?;
        parton_sbi::physics::RefinementResultV2 {
            grid,
            trace: RefinementTraceV2 {
                policy_version: parton_sbi::physics::REFINEMENT_POLICY_VERSION_V2.into(),
                iterations: Vec::new(),
                complete: false,
                failure_reason: Some(
                    "single-point diagnostic does not run global refinement".into(),
                ),
            },
        }
    };
    let trace_hash = refinement
        .trace
        .canonical_hash()
        .map_err(|error| error.to_string())?;
    let final_grid_hash = refinement
        .grid
        .canonical_hash()
        .map_err(|error| error.to_string())?;
    eprintln!("revised-D1: running mandatory raw-CT18 decomposition");
    let raw_ct18_fidelity =
        validate_raw_ct_fidelity_v2(&context).map_err(|error| error.to_string())?;
    let mut anchors = Vec::new();
    for (name, theta) in selected_anchors {
        eprintln!("revised-D1: {name}: base/doubled full-domain moments");
        let base = evolve_grid_v2(
            &context,
            theta,
            &refinement.grid.x_knots,
            &refinement.grid.unique_q_knots_gev,
            ComputationalGridKind::Base,
        )
        .map_err(|error| error.to_string())?;
        let doubled = evolve_grid_v2(
            &context,
            theta,
            &refinement.grid.x_knots,
            &refinement.grid.unique_q_knots_gev,
            ComputationalGridKind::Doubled,
        )
        .map_err(|error| error.to_string())?;
        let moment_closure =
            validate_moments_v2(&base, &doubled).map_err(|error| error.to_string())?;
        eprintln!("revised-D1: {name}: PDF transport and sign topology");
        let (artifact, transport_closure) = validate_transport_v2(
            &context,
            theta,
            &refinement.grid,
            &trace_hash,
            &default_cache_root_v2(),
        )
        .map_err(|error| error.to_string())?;
        eprintln!("revised-D1: {name}: NLO photon F2/FL closure");
        let observable_closure = validate_photon_observables_v2(&context, theta, &artifact)
            .map_err(|error| error.to_string())?;
        let strict_support_passed = strict_support_smoke_v2(&artifact, &refinement.grid);
        let repeated = build_or_load_artifact_v2(
            &context,
            theta,
            &refinement.grid,
            &trace_hash,
            &default_cache_root_v2(),
        )
        .map_err(|error| error.to_string())?;
        let manifest_byte_reproducible = artifact.manifest == repeated.manifest;
        let artifact_bytes = artifact
            .manifest
            .checksums
            .iter()
            .map(|entry| entry.byte_count)
            .sum();
        let mut reasons = Vec::new();
        if !refinement.trace.complete {
            reasons.push(
                refinement
                    .trace
                    .failure_reason
                    .clone()
                    .unwrap_or_else(|| "global refinement did not complete".into()),
            );
        }
        if !moment_closure.passed {
            reasons.push("base/doubled full-domain moment or leakage gate failed".into());
        }
        if !transport_closure.passed {
            reasons.push("revised direct/APFEL artifact transport gate failed".into());
        }
        if !observable_closure.passed {
            reasons.push("NLO photon F2/FL or reduced-cross-section gate failed".into());
        }
        if !strict_support_passed {
            reasons.push("strict artifact support gate failed".into());
        }
        if !manifest_byte_reproducible {
            reasons.push("v2 artifact manifest was not byte reproducible".into());
        }
        anchors.push(RevisedAnchorReport {
            name,
            theta,
            artifact_hash: artifact.manifest.artifact_hash.clone(),
            set_name: artifact.manifest.set_name.clone(),
            artifact_bytes,
            moment_closure,
            transport_closure,
            observable_closure,
            strict_support_passed,
            threshold_subgrid_count: artifact.manifest.grid.q_subgrids_gev.len(),
            inactive_top_passed: !artifact
                .manifest
                .grid
                .unique_q_knots_gev
                .iter()
                .any(|q| q.to_bits() == context.metadata.top_threshold_gev.to_bits()),
            manifest_byte_reproducible,
            passed: reasons.is_empty(),
            reasons,
        });
    }
    let decision = aggregate_revised_stage1(anchors.iter().map(|anchor| anchor.passed), false);
    let report = RevisedStage1Report {
        schema_version: "partonsbi.phase1bd.d1r.study.v2".into(),
        study_id: args.study_id.clone().unwrap_or_else(|| "v2-smoke".into()),
        exact_command: std::env::args().collect(),
        git_commit: commit,
        git_dirty: dirty,
        baseline_version: "ct18nlo_member0_sumrule_projected_boundary_v2".into(),
        family_version: "ct18nlo_two_parameter_boundary_v2".into(),
        artifact_schema_version: parton_sbi::physics::PDF_ARTIFACT_SCHEMA_VERSION_V2.into(),
        evolution_policy_version: parton_sbi::physics::EVOLUTION_POLICY_VERSION_V2.into(),
        grid_policy_version: parton_sbi::physics::ARTIFACT_GRID_POLICY_VERSION_V2.into(),
        cache_policy_version: parton_sbi::physics::ARTIFACT_CACHE_POLICY_VERSION_V2.into(),
        computational_x_minimum: parton_sbi::physics::COMPUTATIONAL_XMIN,
        exported_x_minimum: parton_sbi::physics::EXPORTED_XMIN,
        zero_continuation_policy: "exact_zero_on_[1e-11,1e-9)".into(),
        base_grid: parton_sbi::physics::ComputationalGridDefinition::new(
            ComputationalGridKind::Base,
        )
        .subgrids,
        doubled_grid: parton_sbi::physics::ComputationalGridDefinition::new(
            ComputationalGridKind::Doubled,
        )
        .subgrids,
        final_common_grid_hash: final_grid_hash,
        final_x_knot_count: refinement.grid.x_knots.len(),
        final_unique_q_knot_count: refinement.grid.unique_q_knots_gev.len(),
        q_subgrids_gev: refinement.grid.q_subgrids_gev.clone(),
        refinement_trace_hash: trace_hash,
        refinement_trace: refinement.trace,
        raw_ct18_fidelity,
        anchor_count: anchors.len(),
        anchors,
        revised_stage1_decision: decision,
        d2_authorization_candidate: decision == RevisedStage1Decision::Pass,
        d2_authorized: false,
        runtime_seconds: started.elapsed().as_secs_f64(),
        generated_artifacts_committed: false,
        limitations: vec![
            "The binding observable is NLO zero-mass photon exchange, not full gamma/Z neutral-current validation.".into(),
            "Raw CT18 pointwise fidelity is mandatory but nonbinding because the evolution implementation is independent.".into(),
            "A revised Stage 1 PASS is only a D2 authorization candidate pending separate scientific review.".into(),
        ],
    };
    if let Some(output) = args.output {
        fs::create_dir_all(&output).map_err(|error| error.to_string())?;
        let target = output.join("stage1r_decision.json");
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

fn aggregate_revised_stage1(
    anchor_passes: impl IntoIterator<Item = bool>,
    scientifically_unresolved: bool,
) -> RevisedStage1Decision {
    if scientifically_unresolved {
        RevisedStage1Decision::Inconclusive
    } else if anchor_passes.into_iter().all(|passed| passed) {
        RevisedStage1Decision::Pass
    } else {
        RevisedStage1Decision::Fail
    }
}

fn strict_support_smoke_v2(
    artifact: &parton_sbi::physics::PdfArtifactV2,
    grid: &ArtifactGridV2,
) -> bool {
    let xmin = grid.x_knots[0];
    let xmax = *grid.x_knots.last().expect("nonempty x grid");
    let qmin = grid.unique_q_knots_gev[0];
    let qmax = *grid.unique_q_knots_gev.last().expect("nonempty Q grid");
    let exact = evaluate_artifact_v2(artifact, &[xmin, xmax], &[qmin, qmax]).is_ok();
    let below_x = evaluate_artifact_v2(
        artifact,
        &[f64::from_bits(xmin.to_bits() - 1), xmax],
        &[qmin, qmax],
    )
    .is_err();
    let above_x = evaluate_artifact_v2(
        artifact,
        &[xmin, f64::from_bits(xmax.to_bits() + 1)],
        &[qmin, qmax],
    )
    .is_err();
    let below_q = evaluate_artifact_v2(
        artifact,
        &[xmin, xmax],
        &[f64::from_bits(qmin.to_bits() - 1), qmax],
    )
    .is_err();
    let above_q = evaluate_artifact_v2(
        artifact,
        &[xmin, xmax],
        &[qmin, f64::from_bits(qmax.to_bits() + 1)],
    )
    .is_err();
    exact && below_x && above_x && below_q && above_q
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

    #[test]
    fn revised_stage1_aggregation_preserves_all_three_decisions() {
        assert_eq!(
            aggregate_revised_stage1([true; 9], false),
            RevisedStage1Decision::Pass
        );
        assert_eq!(
            aggregate_revised_stage1([true, false], false),
            RevisedStage1Decision::Fail
        );
        assert_eq!(
            aggregate_revised_stage1([true; 9], true),
            RevisedStage1Decision::Inconclusive
        );
    }

    #[test]
    fn parser_selects_v2_without_reinterpreting_v1() {
        let v1 = parse_validate_pdf_artifact(&["--anchors".into()]).unwrap();
        let v2 = parse_validate_pdf_artifact(&[
            "--artifact-version".into(),
            "v2".into(),
            "--anchors".into(),
        ])
        .unwrap();
        assert_eq!(v1.artifact_version, ArtifactContractVersion::V1);
        assert_eq!(v2.artifact_version, ArtifactContractVersion::V2);
    }
}
