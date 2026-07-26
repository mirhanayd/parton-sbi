use parton_sbi::physics::{
    identify_proton_pdf_entry, reweight_event, validate_run_compatibility, DenominatorPolicy,
    HepMcEvent, HepMcReader, HepMcRunCuts, HepMcRunProvenance, LhapdfProvider, PdfEntrySide,
    PdfMemberSpec, PdfReweightingInvalidReason, PdfReweightingRequest, PdfWeightEvaluator,
    WeightStatistics, DEFAULT_NOMINAL_XF_RELATIVE_TOLERANCE,
};
use std::io::{BufReader, Cursor};
use std::path::PathBuf;

const REAL_FIXTURE: &str = "tests/fixtures/hepmc3_real_minimal.hepmc3";

#[derive(Clone)]
struct MockPdf(Result<f64, String>);

impl PdfWeightEvaluator for MockPdf {
    fn xfx_at_scale(&self, _flavor: i32, _x: f64, _scale_gev: f64) -> Result<f64, String> {
        self.0.clone()
    }
}

fn event(pdf_payload: &str, weights: Option<&str>) -> HepMcEvent {
    let weight_record = weights
        .map(|weights| format!("W {weights}\n"))
        .unwrap_or_default();
    let input = format!(
        "E 7 0 2\nU GEV MM\n{weight_record}A 0 GenPdfInfo {pdf_payload}\nP 1 0 11 0 0 27.5 27.5 0.000511 4\nP 2 0 2212 0 0 -920 920.0005 0.938 4\n"
    );
    HepMcReader::new(BufReader::new(Cursor::new(input.into_bytes())))
        .next_event()
        .unwrap()
        .unwrap()
}

fn standard_event() -> HepMcEvent {
    event("11 2 0.9 0.2 10 0.5 2.0 0 0", Some("4.0"))
}

fn request() -> PdfReweightingRequest {
    PdfReweightingRequest {
        source_pdf: PdfMemberSpec::new("MockSet", 0).unwrap(),
        target_pdf: PdfMemberSpec::new("MockSet", 1).unwrap(),
        source_run_identity: "mock-run".to_owned(),
        source_seed: Some(101),
        event_weight_index: None,
        denominator_policy: DenominatorPolicy::Stored,
        nominal_xf_relative_tolerance: DEFAULT_NOMINAL_XF_RELATIVE_TOLERANCE,
    }
}

fn evaluate(
    event: &HepMcEvent,
    nominal: f64,
    target: f64,
) -> parton_sbi::physics::PdfReweightingResult {
    reweight_event(
        event,
        None,
        &request(),
        &MockPdf(Ok(nominal)),
        &MockPdf(Ok(target)),
    )
    .unwrap()
}

#[test]
fn correct_proton_side_selection_for_electron_proton_ordering() {
    let selected = identify_proton_pdf_entry(&standard_event(), None).unwrap();
    assert_eq!(selected.side, PdfEntrySide::Second);
    assert_eq!(selected.flavor, 2);
    assert_eq!(selected.x, 0.2);
    assert_eq!(selected.scale_gev, 10.0);
    assert_eq!(selected.stored_xf, 2.0);
}

#[test]
fn correct_proton_side_selection_when_pdf_ordering_is_reversed() {
    let event = event("-2 11 0.3 0.9 8 1.5 0.5 0 0", Some("1"));
    let selected = identify_proton_pdf_entry(&event, None).unwrap();
    assert_eq!(selected.side, PdfEntrySide::First);
    assert_eq!(selected.flavor, -2);
    assert_eq!(selected.x, 0.3);
}

#[test]
fn rejects_two_lepton_side_entries() {
    let result = identify_proton_pdf_entry(&event("11 11 0.9 0.8 10 0.5 0.5 0 0", Some("1")), None);
    assert_eq!(
        result.unwrap_err().0,
        PdfReweightingInvalidReason::AmbiguousPdfEntries
    );
}

#[test]
fn rejects_unsupported_or_ambiguous_entries() {
    let result = identify_proton_pdf_entry(&event("11 6 0.9 0.2 10 0.5 2.0 0 0", Some("1")), None);
    assert_eq!(
        result.unwrap_err().0,
        PdfReweightingInvalidReason::UnsupportedFlavor
    );
}

#[test]
fn exact_ratio_calculation_uses_mock_evaluators() {
    let result = evaluate(&standard_event(), 2.0, 3.0);
    assert!(result.valid);
    assert_eq!(result.ratio_stored_denominator, Some(1.5));
    assert_eq!(result.ratio_recomputed_denominator, Some(1.5));
}

#[test]
fn stored_denominator_is_the_default() {
    let mut request = request();
    request.nominal_xf_relative_tolerance = 1.0;
    let result = reweight_event(
        &standard_event(),
        None,
        &request,
        &MockPdf(Ok(2.5)),
        &MockPdf(Ok(3.0)),
    )
    .unwrap();
    assert_eq!(result.primary_ratio, Some(1.5));
}

#[test]
fn recomputed_denominator_is_retained_as_a_diagnostic() {
    let mut request = request();
    request.nominal_xf_relative_tolerance = 1.0;
    let result = reweight_event(
        &standard_event(),
        None,
        &request,
        &MockPdf(Ok(2.5)),
        &MockPdf(Ok(3.0)),
    )
    .unwrap();
    assert_eq!(result.ratio_recomputed_denominator, Some(1.2));
}

#[test]
fn signed_original_weights_are_preserved() {
    let result = evaluate(&event("11 2 0.9 0.2 10 0.5 2.0 0 0", Some("-4")), 2.0, 3.0);
    assert_eq!(result.original_event_weight, Some(-4.0));
    assert_eq!(result.target_event_weight, Some(-6.0));
}

#[test]
fn target_event_weight_is_calculated_exactly() {
    assert_eq!(
        evaluate(&standard_event(), 2.0, 3.0).target_event_weight,
        Some(6.0)
    );
}

#[test]
fn multiple_event_weights_require_explicit_selection() {
    let result = evaluate(&event("11 2 0.9 0.2 10 0.5 2.0 0 0", Some("1 2")), 2.0, 3.0);
    assert_eq!(
        result.invalid_reason,
        Some(PdfReweightingInvalidReason::MultipleEventWeightsRequireIndex)
    );
}

#[test]
fn missing_event_weights_are_not_replaced() {
    let result = evaluate(&event("11 2 0.9 0.2 10 0.5 2.0 0 0", None), 2.0, 3.0);
    assert_eq!(
        result.invalid_reason,
        Some(PdfReweightingInvalidReason::MissingEventWeight)
    );
}

#[test]
fn zero_nominal_denominator_is_typed_invalid() {
    let result = evaluate(&event("11 2 0.9 0.2 10 0.5 0 0 0", Some("1")), 1.0, 2.0);
    assert_eq!(
        result.invalid_reason,
        Some(PdfReweightingInvalidReason::NonPositiveStoredNominalXf)
    );
}

#[test]
fn negative_nominal_denominator_is_rejected() {
    let result = evaluate(&event("11 2 0.9 0.2 10 0.5 -1 0 0", Some("1")), 1.0, 2.0);
    assert_eq!(
        result.invalid_reason,
        Some(PdfReweightingInvalidReason::NonPositiveStoredNominalXf)
    );
}

#[test]
fn non_finite_target_value_is_typed_invalid() {
    let result = reweight_event(
        &standard_event(),
        None,
        &request(),
        &MockPdf(Ok(2.0)),
        &MockPdf(Ok(f64::NAN)),
    )
    .unwrap();
    assert_eq!(
        result.invalid_reason,
        Some(PdfReweightingInvalidReason::NonFiniteTargetXf)
    );
}

#[test]
fn unsupported_flavor_is_typed_invalid() {
    let result = evaluate(&event("11 99 0.9 0.2 10 0.5 2 0 0", Some("1")), 2.0, 3.0);
    assert_eq!(
        result.invalid_reason,
        Some(PdfReweightingInvalidReason::UnsupportedFlavor)
    );
}

#[test]
fn invalid_x_is_typed_invalid() {
    let result = evaluate(&event("11 2 0.9 1.0 10 0.5 2 0 0", Some("1")), 2.0, 3.0);
    assert_eq!(
        result.invalid_reason,
        Some(PdfReweightingInvalidReason::InvalidX)
    );
}

#[test]
fn invalid_scale_is_typed_invalid() {
    let result = evaluate(&event("11 2 0.9 0.2 0 0.5 2 0 0", Some("1")), 2.0, 3.0);
    assert_eq!(
        result.invalid_reason,
        Some(PdfReweightingInvalidReason::InvalidScale)
    );
}

#[test]
fn analytically_known_ess_is_exact() {
    let statistics = WeightStatistics::from_weights(&[1.0, 1.0, 2.0], &[1.0, 1.0, 2.0]);
    assert_eq!(statistics.effective_sample_size.signed, 16.0 / 6.0);
    let tails = statistics.weight_distribution.unwrap();
    assert_eq!(tails.minimum, 1.0);
    assert_eq!(tails.maximum, 2.0);
    assert!(tails.coefficient_of_variation.is_some());
}

#[test]
fn signed_weight_ess_diagnostics_are_correct() {
    let statistics = WeightStatistics::from_weights(&[1.0, -1.0, 2.0], &[1.0; 3]);
    assert_eq!(statistics.effective_sample_size.signed, 4.0 / 6.0);
    assert_eq!(statistics.effective_sample_size.absolute_weight, 16.0 / 6.0);
    assert_eq!(statistics.negative_weights, 1);
}

#[test]
fn large_ratios_are_not_clipped() {
    let result = evaluate(&standard_event(), 2.0, 2.0e12);
    assert_eq!(result.primary_ratio, Some(1.0e12));
    assert_eq!(result.target_event_weight, Some(4.0e12));
}

fn provenance() -> HepMcRunProvenance {
    HepMcRunProvenance {
        source_run_directory: PathBuf::from("run"),
        config_path: PathBuf::from("run/config.json"),
        metadata_path: PathBuf::from("run/metadata.json"),
        schema_version: Some(1),
        process: Some("neutral_current_dis".to_owned()),
        event_schema_version: Some(1),
        electroweak_process: Some("gamma_z_t_channel".to_owned()),
        event_selection: Some("selection-v1".to_owned()),
        space_shower_dipole_recoil: Some(true),
        beam_particle_id_1: Some(11),
        beam_particle_id_2: Some(2212),
        electron_energy_gev: Some(27.5),
        proton_energy_gev: Some(920.0),
        pdf_set: Some("CT18NLO".to_owned()),
        pdf_member: Some(0),
        configured_seed: Some(100),
        generator_seed: Some(100),
        parton_shower: Some(true),
        hadronization: Some(true),
        cuts: HepMcRunCuts {
            q2_min_gev2: Some(3.5),
            q2_max_gev2: Some(10_000.0),
            x_min: Some(1.0e-4),
            x_max: Some(0.8),
            y_min: Some(0.01),
            y_max: Some(0.95),
        },
        configured_event_count: Some(2_000),
        accepted_event_count: Some(2_000),
        generator_version: Some("8.312".to_owned()),
        apfelxx_version: None,
        lhapdf_version: Some("6.5.6".to_owned()),
        pythia_version: Some("8.312".to_owned()),
        hepmc_version: Some("3.03.00".to_owned()),
        git_commit: Some("abc".to_owned()),
        git_dirty: Some(false),
        build_timestamp: Some("time".to_owned()),
    }
}

#[test]
fn run_compatibility_accepts_member_and_seed_differences() {
    let nominal = provenance();
    let mut target = nominal.clone();
    target.pdf_member = Some(7);
    target.configured_seed = Some(200);
    target.generator_seed = Some(200);
    assert!(validate_run_compatibility(&nominal, &target).compatible);
}

#[test]
fn run_compatibility_rejects_beam_differences() {
    let nominal = provenance();
    let mut target = nominal.clone();
    target.proton_energy_gev = Some(1000.0);
    assert!(!validate_run_compatibility(&nominal, &target).compatible);
}

#[test]
fn run_compatibility_rejects_cut_differences() {
    let nominal = provenance();
    let mut target = nominal.clone();
    target.cuts.q2_min_gev2 = Some(10.0);
    assert!(!validate_run_compatibility(&nominal, &target).compatible);
}

#[test]
fn run_compatibility_rejects_process_differences() {
    let nominal = provenance();
    let mut target = nominal.clone();
    target.process = Some("different".to_owned());
    assert!(!validate_run_compatibility(&nominal, &target).compatible);
}

#[test]
fn run_compatibility_rejects_shower_differences() {
    let nominal = provenance();
    let mut target = nominal.clone();
    target.parton_shower = Some(false);
    assert!(!validate_run_compatibility(&nominal, &target).compatible);
}

#[test]
fn run_compatibility_rejects_hadronization_differences() {
    let nominal = provenance();
    let mut target = nominal.clone();
    target.hadronization = Some(false);
    assert!(!validate_run_compatibility(&nominal, &target).compatible);
}

#[test]
fn real_phase0a_fixture_streams_through_reweighting_pipeline() {
    let reader = HepMcReader::open(REAL_FIXTURE).unwrap();
    let mut count = 0;
    for event in reader {
        let event = event.unwrap();
        let mut request = request();
        request.nominal_xf_relative_tolerance = 10.0;
        let result =
            reweight_event(&event, None, &request, &MockPdf(Ok(1.0)), &MockPdf(Ok(1.0))).unwrap();
        assert!(result.valid);
        count += 1;
    }
    assert_eq!(count, 2);
}

#[test]
#[ignore = "requires LHAPDF 6 and CT18NLO installed in WSL"]
fn stored_vs_recomputed_nominal_xf_integration_check() {
    let event = HepMcReader::open(REAL_FIXTURE)
        .unwrap()
        .next_event()
        .unwrap()
        .unwrap();
    let pdf = LhapdfProvider::new("CT18NLO", 0).unwrap();
    let mut request = request();
    request.source_pdf = PdfMemberSpec::new("CT18NLO", 0).unwrap();
    request.target_pdf = request.source_pdf.clone();
    let result = reweight_event(&event, None, &request, &pdf, &pdf).unwrap();
    assert!(result.valid, "{result:?}");
}

#[test]
#[ignore = "requires LHAPDF 6 and CT18NLO installed in WSL"]
fn cli_smoke_output_has_the_declared_schema() {
    let unique = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let root = std::env::temp_dir().join(format!("partonsbi_phase1a_cli_{unique}"));
    let run = root.join("run");
    let output = root.join("diagnostics");
    std::fs::create_dir_all(&run).unwrap();
    std::fs::copy(REAL_FIXTURE, run.join("events.hepmc3")).unwrap();
    std::fs::copy(
        "tests/fixtures/hepmc3_real_minimal_config.json",
        run.join("config.json"),
    )
    .unwrap();
    std::fs::copy(
        "tests/fixtures/hepmc3_real_minimal_metadata.json",
        run.join("metadata.json"),
    )
    .unwrap();
    std::fs::write(
        run.join("inclusive_observables.csv"),
        "event_number,event_weight,Q2,x,y,W2,scattered_electron_E,scattered_electron_px,scattered_electron_py,scattered_electron_pz,number_of_final_state_particles,number_of_charged_final_state_particles\n\
225,1,3.88727,0.336657,0.000114097,8.53975,26.2138,-1.91659,0.454825,26.1397,4,2\n\
2743,1,3.54945,0.256776,0.000136591,11.154,26.7593,-1.59,-1.02789,26.6923,4,2\n",
    )
    .unwrap();
    std::fs::write(
        run.join("summary.json"),
        r#"{"requested_events":2,"attempted_events":2,"accepted_events":2,"failed_events":0,"vetoed_cuts_events":0,"vetoed_conservation_events":0}"#,
    )
    .unwrap();

    let status = std::process::Command::new(env!("CARGO_BIN_EXE_parton-sbi"))
        .args([
            "validate-pdf-reweighting",
            "--nominal-run",
            run.to_str().unwrap(),
            "--target-pdf-set",
            "CT18NLO",
            "--target-pdf-member",
            "0",
            "--output",
            output.to_str().unwrap(),
        ])
        .status()
        .unwrap();
    assert!(status.success());
    let manifest: serde_json::Value =
        serde_json::from_slice(&std::fs::read(output.join("manifest.json")).unwrap()).unwrap();
    let summary: serde_json::Value =
        serde_json::from_slice(&std::fs::read(output.join("reweighting_summary.json")).unwrap())
            .unwrap();
    assert_eq!(manifest["schema_version"], 1);
    assert_eq!(summary["schema_version"], 1);
    assert_eq!(summary["diagnostics"]["total_events"], 2);
    assert_eq!(
        std::fs::read_to_string(output.join("event_diagnostics.jsonl"))
            .unwrap()
            .lines()
            .count(),
        2
    );
    let _ = std::fs::remove_dir_all(root);
}
