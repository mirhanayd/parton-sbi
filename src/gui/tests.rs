//! Unit tests for the GUI module.
//!
//! All tests run without opening a window. They validate configuration,
//! command construction, schema loading, run-history parsing, process-state
//! transitions, cancellation, error rendering, and event filtering.

use super::dis_event_viewer_page::{filter_by_pdg, filter_final_state, parse_hepmc3};
use super::dis_run_history_page::scan_runs;
use super::state::*;

use std::fs;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

// ---------------------------------------------------------------------------
// Configuration validation
// ---------------------------------------------------------------------------

#[test]
fn valid_default_config_passes_validation() {
    let config = DisConfig::default();
    let errors = config.validate();
    assert!(
        errors.is_empty(),
        "default config should be valid: {errors:?}"
    );
}

#[test]
fn negative_electron_energy_fails_validation() {
    let mut config = DisConfig::default();
    config.electron_energy_gev = -10.0;
    let errors = config.validate();
    assert!(
        errors.iter().any(|e| e.field == "Electron Energy"),
        "should flag negative electron energy"
    );
}

#[test]
fn zero_proton_energy_fails_validation() {
    let mut config = DisConfig::default();
    config.proton_energy_gev = 0.0;
    let errors = config.validate();
    assert!(
        errors.iter().any(|e| e.field == "Proton Energy"),
        "should flag zero proton energy"
    );
}

#[test]
fn x_min_greater_than_x_max_fails_validation() {
    let mut config = DisConfig::default();
    config.x_min = 0.9;
    config.x_max = 0.1;
    let errors = config.validate();
    assert!(
        errors.iter().any(|e| e.field == "x range"),
        "should flag inverted x range"
    );
}

#[test]
fn q2_min_greater_than_q2_max_fails_validation() {
    let mut config = DisConfig::default();
    config.q2_min_gev2 = 1000.0;
    config.q2_max_gev2 = 10.0;
    let errors = config.validate();
    assert!(
        errors.iter().any(|e| e.field == "Q² range"),
        "should flag inverted Q² range"
    );
}

#[test]
fn empty_pdf_set_fails_validation() {
    let mut config = DisConfig::default();
    config.pdf_set = String::new();
    let errors = config.validate();
    assert!(
        errors.iter().any(|e| e.field == "PDF Set"),
        "should flag empty PDF set"
    );
}

#[test]
fn whitespace_only_pdf_set_fails_validation() {
    let mut config = DisConfig::default();
    config.pdf_set = "   ".to_string();
    let errors = config.validate();
    assert!(
        errors.iter().any(|e| e.field == "PDF Set"),
        "should flag whitespace-only PDF set"
    );
}

#[test]
fn negative_pdf_member_fails_validation() {
    let mut config = DisConfig::default();
    config.pdf_member = -1;
    let errors = config.validate();
    assert!(
        errors.iter().any(|e| e.field == "PDF Member"),
        "should flag negative PDF member"
    );
}

#[test]
fn unsupported_backend_fails_validation() {
    let mut config = DisConfig::default();
    config.backend = "qcdnum".to_string();
    let errors = config.validate();
    assert!(
        errors.iter().any(|e| e.field == "Backend"),
        "should flag unsupported backend"
    );
}

#[test]
fn unsupported_order_fails_validation() {
    let mut config = DisConfig::default();
    config.perturbative_order = "NNLO".to_string();
    let errors = config.validate();
    assert!(
        errors.iter().any(|e| e.field == "Perturbative Order"),
        "should flag unsupported order"
    );
}

#[test]
fn invalid_random_seed_fails_validation() {
    let mut config = DisConfig::default();
    config.random_seed = "not_a_number".to_string();
    let errors = config.validate();
    assert!(
        errors.iter().any(|e| e.field == "Random Seed"),
        "should flag non-numeric seed"
    );
}

#[test]
fn nan_scale_ratio_fails_validation() {
    let mut config = DisConfig::default();
    config.mu_f_over_q = f64::NAN;
    let errors = config.validate();
    assert!(
        errors.iter().any(|e| e.field == "μ_F/Q"),
        "should flag NaN scale ratio"
    );
}

#[test]
fn empty_output_directory_fails_validation() {
    let mut config = DisConfig::default();
    config.output_directory = String::new();
    let errors = config.validate();
    assert!(
        errors.iter().any(|e| e.field == "Output Directory"),
        "should flag empty output directory"
    );
}

// ---------------------------------------------------------------------------
// Command construction
// ---------------------------------------------------------------------------

#[test]
fn structure_function_command_has_no_shell_metacharacters() {
    let args =
        build_structure_function_command(0.01, 100.0, "apfel", "NLO", "CT18NLO", 0, 1.0, 1.0);
    for arg in &args {
        assert!(
            !arg.contains(';') && !arg.contains('|') && !arg.contains('&'),
            "command args must not contain shell metacharacters: {arg}"
        );
    }
}

#[test]
fn structure_function_command_has_all_required_flags() {
    let args =
        build_structure_function_command(0.01, 100.0, "apfel", "NLO", "CT18NLO", 0, 1.0, 1.0);
    assert!(args.contains(&"--backend".to_string()));
    assert!(args.contains(&"--x".to_string()));
    assert!(args.contains(&"--q2".to_string()));
    assert!(args.contains(&"--order".to_string()));
    assert!(args.contains(&"--pdf-set".to_string()));
    assert!(args.contains(&"--pdf-member".to_string()));
}

#[test]
fn scale_ratios_omitted_when_unity() {
    let args =
        build_structure_function_command(0.01, 100.0, "apfel", "NLO", "CT18NLO", 0, 1.0, 1.0);
    assert!(
        !args.contains(&"--mu-f-over-q".to_string()),
        "should not include default mu_f"
    );
    assert!(
        !args.contains(&"--mu-r-over-q".to_string()),
        "should not include default mu_r"
    );
}

#[test]
fn scale_ratios_included_when_non_unity() {
    let args =
        build_structure_function_command(0.01, 100.0, "apfel", "NLO", "CT18NLO", 0, 0.5, 2.0);
    assert!(
        args.contains(&"--mu-f-over-q".to_string()),
        "should include non-default mu_f"
    );
    assert!(
        args.contains(&"--mu-r-over-q".to_string()),
        "should include non-default mu_r"
    );
}

#[test]
fn event_generation_command_includes_seed_when_set() {
    let mut config = DisConfig::default();
    config.random_seed = "42".to_string();
    let args = build_event_generation_command(&config);
    assert!(args.contains(&"--seed".to_string()));
    assert!(args.contains(&"42".to_string()));
}

#[test]
fn event_generation_command_omits_seed_when_empty() {
    let config = DisConfig::default();
    let args = build_event_generation_command(&config);
    assert!(!args.contains(&"--seed".to_string()));
}

#[test]
fn validate_hera_command_has_all_required_flags() {
    let args = build_validate_hera_command(
        "HERA1+2_NCep_920",
        "apfel",
        "NLO",
        "CT18NLO",
        0,
        "outputs/validation",
    );
    assert!(args.contains(&"--dataset".to_string()));
    assert!(args.contains(&"--backend".to_string()));
    assert!(args.contains(&"--order".to_string()));
    assert!(args.contains(&"--pdf-set".to_string()));
    assert!(args.contains(&"--output".to_string()));
}

#[test]
fn theory_uncertainties_command_includes_flags_when_enabled() {
    let args = build_theory_uncertainties_command(
        "HERA1+2_NCep_920",
        "apfel",
        "NLO",
        "CT18NLO",
        "outputs/unc",
        true,
        true,
    );
    assert!(args.contains(&"--pdf-uncertainty".to_string()));
    assert!(args.contains(&"--scale-variations".to_string()));
}

#[test]
fn theory_uncertainties_command_omits_flags_when_disabled() {
    let args = build_theory_uncertainties_command(
        "HERA1+2_NCep_920",
        "apfel",
        "NLO",
        "CT18NLO",
        "outputs/unc",
        false,
        false,
    );
    assert!(!args.contains(&"--pdf-uncertainty".to_string()));
    assert!(!args.contains(&"--scale-variations".to_string()));
}

// ---------------------------------------------------------------------------
// Schema compatibility
// ---------------------------------------------------------------------------

#[test]
fn current_schema_is_compatible() {
    assert!(is_schema_compatible(Some(CURRENT_SCHEMA_VERSION)));
}

#[test]
fn none_schema_is_incompatible() {
    assert!(!is_schema_compatible(None));
}

#[test]
fn old_schema_is_incompatible() {
    assert!(!is_schema_compatible(Some(0)));
}

#[test]
fn future_schema_is_incompatible() {
    assert!(!is_schema_compatible(Some(CURRENT_SCHEMA_VERSION + 1)));
}

// ---------------------------------------------------------------------------
// Process-state transitions
// ---------------------------------------------------------------------------

#[test]
fn backend_process_starts_idle() {
    let process = BackendProcess::default();
    assert_eq!(process.status, ProcessStatus::Idle);
    assert!(process.stdout_lines.is_empty());
    assert!(process.stderr_lines.is_empty());
    assert!(process.exit_code.is_none());
}

#[test]
fn backend_process_reset_clears_all_state() {
    let mut process = BackendProcess::default();
    process.status = ProcessStatus::Completed;
    process.stdout_lines.push("test".to_string());
    process.stderr_lines.push("error".to_string());
    process.exit_code = Some(0);
    process.progress_text = "done".to_string();

    process.reset();

    assert_eq!(process.status, ProcessStatus::Idle);
    assert!(process.stdout_lines.is_empty());
    assert!(process.stderr_lines.is_empty());
    assert!(process.exit_code.is_none());
    assert!(process.progress_text.is_empty());
}

// ---------------------------------------------------------------------------
// Cancellation state
// ---------------------------------------------------------------------------

#[test]
fn cancellation_flag_propagates() {
    let process = BackendProcess::default();
    let flag = Arc::clone(&process.cancel_flag);

    assert!(!flag.load(Ordering::Acquire));
    process.request_cancel();
    assert!(flag.load(Ordering::Acquire));
}

#[test]
fn reset_creates_new_cancel_flag() {
    let mut process = BackendProcess::default();
    let old_flag = Arc::clone(&process.cancel_flag);
    process.request_cancel();

    process.reset();

    // Old flag should still be true
    assert!(old_flag.load(Ordering::Acquire));
    // New flag should be false
    assert!(!process.cancel_flag.load(Ordering::Acquire));
}

// ---------------------------------------------------------------------------
// Error rendering data
// ---------------------------------------------------------------------------

#[test]
fn error_categories_have_actionable_suggestions() {
    let categories = [
        GuiErrorCategory::LhapdfSetNotInstalled,
        GuiErrorCategory::ApfelBackendMissing,
        GuiErrorCategory::PythiaBackendMissing,
        GuiErrorCategory::InvalidKinematics,
        GuiErrorCategory::UnsupportedOrder,
        GuiErrorCategory::InvalidOutputSchema,
        GuiErrorCategory::WslgUnavailable,
        GuiErrorCategory::ProcessFailed,
        GuiErrorCategory::FileNotFound,
        GuiErrorCategory::ParseError,
        GuiErrorCategory::Unknown,
    ];

    for category in categories {
        let error = GuiError::new(category, "test message");
        assert!(
            !error.suggestion.is_empty(),
            "category {:?} should have a non-empty suggestion",
            error.category
        );
    }
}

#[test]
fn error_state_keeps_latest_error() {
    let mut state = ErrorState::default();
    assert!(!state.has_errors());

    state.push(GuiError::new(GuiErrorCategory::Unknown, "first"));
    state.push(GuiError::new(GuiErrorCategory::Unknown, "second"));

    assert!(state.has_errors());
    assert_eq!(state.latest().unwrap().message, "second");
}

#[test]
fn error_state_limits_to_twenty() {
    let mut state = ErrorState::default();
    for i in 0..25 {
        state.push(GuiError::new(
            GuiErrorCategory::Unknown,
            format!("error {i}"),
        ));
    }
    assert_eq!(state.errors.len(), 20);
    // First error should be "error 5" (0-4 were evicted)
    assert_eq!(state.errors[0].message, "error 5");
}

#[test]
fn error_state_clear_removes_all() {
    let mut state = ErrorState::default();
    state.push(GuiError::new(GuiErrorCategory::Unknown, "test"));
    state.clear();
    assert!(!state.has_errors());
}

// ---------------------------------------------------------------------------
// Event filtering
// ---------------------------------------------------------------------------

#[test]
fn parse_hepmc3_empty_input_returns_no_events() {
    let events = parse_hepmc3("").unwrap();
    assert!(events.is_empty());
}

#[test]
fn parse_hepmc3_single_event() {
    let input = include_str!("../../tests/fixtures/hepmc3_real_minimal.hepmc3");
    let events = parse_hepmc3(input).unwrap();
    assert_eq!(events.len(), 2);
    assert_eq!(events[0].event_number, 225);
    assert_eq!(events[0].particles.len(), 19);
    assert_eq!(events[0].vertices.len(), 13);
    assert_eq!(events[0].particles[0].id, 1);
    assert_eq!(events[0].particles[0].pdg_id, 11);
    assert_eq!(events[0].particles[0].status, 4);
}

#[test]
fn filter_final_state_returns_only_status_one() {
    let input = include_str!("../../tests/fixtures/hepmc3_real_minimal.hepmc3");
    let events = parse_hepmc3(input).unwrap();
    let final_state = filter_final_state(&events[0]);
    assert_eq!(final_state.len(), 4);
    for p in &final_state {
        assert_eq!(p.status, 1);
    }
}

#[test]
fn filter_by_pdg_returns_matching_particles() {
    let input = include_str!("../../tests/fixtures/hepmc3_real_minimal.hepmc3");
    let events = parse_hepmc3(input).unwrap();
    let electrons = filter_by_pdg(&events[0], 11);
    assert_eq!(electrons.len(), 5);
    let photons = filter_by_pdg(&events[0], 22);
    assert_eq!(photons.len(), 2);
    let muons = filter_by_pdg(&events[0], 13);
    assert!(muons.is_empty());
}

// ---------------------------------------------------------------------------
// Run-history parsing (filesystem-based test)
// ---------------------------------------------------------------------------

#[test]
fn run_history_scanning_with_temp_directory() {
    let unique = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let tmp = std::env::temp_dir().join(format!("quark_sim_gui_test_{unique}"));

    // Create a mock run directory
    let run_dir = tmp.join("test_run");
    fs::create_dir_all(&run_dir).unwrap();

    // Write mock config.json with schema_version
    let config = serde_json::json!({
        "schema_version": CURRENT_SCHEMA_VERSION,
        "process": "NC"
    });
    fs::write(run_dir.join("config.json"), config.to_string()).unwrap();
    fs::write(run_dir.join("summary.json"), "{}").unwrap();

    let mut state = super::dis_run_history_page::RunHistoryPageState {
        base_directory: tmp.to_string_lossy().to_string(),
        ..Default::default()
    };
    let mut errors = Vec::new();
    scan_runs(&mut state, &mut errors);

    assert!(errors.is_empty(), "should not have errors: {errors:?}");
    assert_eq!(state.entries.len(), 1);
    assert_eq!(state.entries[0].run_name, "test_run");
    assert!(state.entries[0].has_config);
    assert!(state.entries[0].has_summary);
    assert!(is_schema_compatible(state.entries[0].schema_version));

    // Cleanup
    let _ = fs::remove_dir_all(&tmp);
}

#[test]
fn incompatible_schema_detected() {
    let unique = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let tmp = std::env::temp_dir().join(format!("quark_sim_gui_test_incompat_{unique}"));
    let run_dir = tmp.join("old_run");
    fs::create_dir_all(&run_dir).unwrap();

    let config = serde_json::json!({
        "schema_version": 999,
        "process": "NC"
    });
    fs::write(run_dir.join("config.json"), config.to_string()).unwrap();

    let mut state = super::dis_run_history_page::RunHistoryPageState {
        base_directory: tmp.to_string_lossy().to_string(),
        ..Default::default()
    };
    let mut errors = Vec::new();
    scan_runs(&mut state, &mut errors);

    assert_eq!(state.entries.len(), 1);
    assert!(!is_schema_compatible(state.entries[0].schema_version));

    let _ = fs::remove_dir_all(&tmp);
}

// ---------------------------------------------------------------------------
// Legacy session data
// ---------------------------------------------------------------------------

#[test]
fn legacy_session_missing_optional_fields_defaults_to_none() {
    let json = r#"{
        "loss_history": [],
        "potential_theory": [],
        "potential_nn": [],
        "test_distances": [],
        "cornell_values": [],
        "nn_values": [],
        "loss_file": "",
        "potential_file": ""
    }"#;
    let data: super::legacy_cornell::AppData =
        serde_json::from_str(json).expect("legacy session should load");
    assert!(data.scattering_file.is_none());
    assert!(data.electrons.is_none());
}
