use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn binary() -> Command {
    Command::new(env!("CARGO_BIN_EXE_quark_sim"))
}

fn create_temp_dir() -> PathBuf {
    use rand::Rng;
    let mut rng = rand::thread_rng();
    let num: u32 = rng.gen();
    let path = std::env::temp_dir().join(format!("quark_sim_test_{}", num));
    fs::create_dir_all(&path).unwrap();
    path
}

// 1. JSON configuration test: verify output directory and config.json exist
#[test]
fn test_json_configuration_creation() {
    let output_path = create_temp_dir();

    let _output = binary()
        .args([
            "generate-dis-events",
            "--electron-energy",
            "27.5",
            "--proton-energy",
            "920.0",
            "--q2-min",
            "10.0",
            "--events",
            "5",
            "--seed",
            "12345",
            "--pdf-set",
            "CT18LO",
            "--output",
            output_path.to_str().unwrap(),
        ])
        .output()
        .expect("should run generate-dis-events command");

    // The command might fail if PYTHIA is not compiled/found, but the JSON config
    // is written by Rust *before* invoking the backend, so we check if the run directory
    // and config.json are created!
    let mut run_dirs = fs::read_dir(&output_path).unwrap();
    let run_dir_entry = run_dirs
        .next()
        .expect("should have created a run directory");
    let run_dir = run_dir_entry.unwrap().path();

    let config_file = run_dir.join("config.json");
    assert!(config_file.is_file(), "config.json should be created");

    let config_content = fs::read_to_string(config_file).unwrap();
    let parsed: serde_json::Value = serde_json::from_str(&config_content).unwrap();
    assert_eq!(parsed["schema_version"], 1);
    assert_eq!(parsed["electron_energy_gev"], 27.5);
    assert_eq!(parsed["proton_energy_gev"], 920.0);

    let _ = fs::remove_dir_all(output_path);
}

// 2. Invalid beam-energy test: rejected by Rust validation
#[test]
fn test_invalid_beam_energy_rejected() {
    let output_path = create_temp_dir();

    let output = binary()
        .args([
            "generate-dis-events",
            "--electron-energy",
            "-27.5",
            "--proton-energy",
            "920.0",
            "--q2-min",
            "10.0",
            "--events",
            "5",
            "--pdf-set",
            "CT18LO",
            "--output",
            output_path.to_str().unwrap(),
        ])
        .output()
        .unwrap();

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("energies must be positive") || stderr.contains("Error:"));

    let _ = fs::remove_dir_all(output_path);
}

// 3. Invalid cut test: rejected by Rust validation
#[test]
fn test_invalid_cut_rejected() {
    let output_path = create_temp_dir();

    // q2-min >= q2-max (via explicit --q2-max 5)
    let output = binary()
        .args([
            "generate-dis-events",
            "--electron-energy",
            "27.5",
            "--proton-energy",
            "920.0",
            "--q2-min",
            "10.0",
            "--q2-max",
            "5.0",
            "--events",
            "5",
            "--pdf-set",
            "CT18LO",
            "--output",
            output_path.to_str().unwrap(),
        ])
        .output()
        .unwrap();

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("invalid Q2 cuts") || stderr.contains("Error:"));

    let _ = fs::remove_dir_all(output_path);
}

// 4. Missing backend test: returns actionable error
#[test]
fn test_missing_backend_reported() {
    let output_path = create_temp_dir();

    // Run pointing to a non-existent backend path
    let output = binary()
        .env("PYTHIA_BACKEND_BIN", "/nonexistent/path/to/pythia_dis_cli")
        .args([
            "generate-dis-events",
            "--electron-energy",
            "27.5",
            "--proton-energy",
            "920.0",
            "--q2-min",
            "10.0",
            "--events",
            "5",
            "--pdf-set",
            "CT18LO",
            "--output",
            output_path.to_str().unwrap(),
        ])
        .output()
        .unwrap();

    assert!(!output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("backend executable not found") || stderr.contains("Error:"));

    let _ = fs::remove_dir_all(output_path);
}

// The following tests require a compiled and working C++ backend.
// We tag them with #[cfg(feature = "pythia_backend_test")] or conditionally run them,
// but since they are run in WSL where the backend is compiled, we can run them if the backend is present.
fn is_backend_available() -> bool {
    let backend_bin = std::env::var("PYTHIA_BACKEND_BIN")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("physics-engine/build/pythia_dis_cli"));
    backend_bin.is_file()
}

// 5. Small deterministic generation test
#[test]
fn test_small_deterministic_generation() {
    if !is_backend_available() {
        return; // Skip if backend is not built
    }

    let output_path = create_temp_dir();

    let output = binary()
        .args([
            "generate-dis-events",
            "--electron-energy",
            "27.5",
            "--proton-energy",
            "920.0",
            "--q2-min",
            "10.0",
            "--events",
            "5",
            "--seed",
            "42",
            "--pdf-set",
            "CT18LO",
            "--output",
            output_path.to_str().unwrap(),
        ])
        .output()
        .unwrap();

    assert!(
        output.status.success(),
        "run should succeed, stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let mut run_dirs = fs::read_dir(&output_path).unwrap();
    let run_dir = run_dirs.next().unwrap().unwrap().path();

    // 6. HepMC3 output existence and parse test
    let hepmc_file = run_dir.join("events.hepmc3");
    assert!(hepmc_file.is_file());
    let hepmc_content = fs::read_to_string(hepmc_file).unwrap();
    assert!(hepmc_content.starts_with("HepMC::"));

    // 7. Momentum conservation verification
    let summary_file = run_dir.join("summary.json");
    assert!(summary_file.is_file());
    let summary_content = fs::read_to_string(summary_file).unwrap();
    let summary: serde_json::Value = serde_json::from_str(&summary_content).unwrap();
    assert_eq!(summary["success"], true);
    assert_eq!(
        summary["vetoed_conservation_events"], 0,
        "No events should fail momentum conservation"
    );

    // 8. Observable reconstruction test
    let csv_file = run_dir.join("inclusive_observables.csv");
    assert!(csv_file.is_file());
    let csv_content = fs::read_to_string(csv_file).unwrap();
    let lines: Vec<&str> = csv_content.lines().collect();
    assert!(lines.len() >= 6, "Header + 5 events");
    // Verify first event values
    let first_event_cols: Vec<&str> = lines[1].split(',').collect();
    assert_eq!(
        first_event_cols.len(),
        20,
        "Should have 20 columns containing true and reconstructed observables"
    );
    let q2_mismatch: f64 = first_event_cols[16].parse().unwrap();
    assert!(
        (0.0..50.0).contains(&q2_mismatch),
        "True and reconstructed Q2 mismatch should be reasonable"
    );

    // 9. Metadata completeness test
    let metadata_file = run_dir.join("metadata.json");
    assert!(metadata_file.is_file());
    let metadata_content = fs::read_to_string(metadata_file).unwrap();
    let metadata: serde_json::Value = serde_json::from_str(&metadata_content).unwrap();
    assert!(metadata.get("pythia_version").is_some());
    assert!(metadata.get("hepmc3_version").is_some());
    assert!(metadata.get("lhapdf_version").is_some());
    assert_eq!(metadata["requested_event_count"], 5);
    assert_eq!(metadata["accepted_event_count"], 5);
    assert_eq!(metadata["random_seed"], 42);

    let _ = fs::remove_dir_all(output_path);
}

// 10. Same-seed reproducibility test
#[test]
fn test_same_seed_reproducibility() {
    if !is_backend_available() {
        return; // Skip if backend is not built
    }

    let output_path_1 = create_temp_dir();
    let output_path_2 = create_temp_dir();

    // First run
    let output1 = binary()
        .args([
            "generate-dis-events",
            "--electron-energy",
            "27.5",
            "--proton-energy",
            "920.0",
            "--q2-min",
            "10.0",
            "--events",
            "10",
            "--seed",
            "123456",
            "--pdf-set",
            "CT18LO",
            "--output",
            output_path_1.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(output1.status.success());

    // Second run
    let output2 = binary()
        .args([
            "generate-dis-events",
            "--electron-energy",
            "27.5",
            "--proton-energy",
            "920.0",
            "--q2-min",
            "10.0",
            "--events",
            "10",
            "--seed",
            "123456",
            "--pdf-set",
            "CT18LO",
            "--output",
            output_path_2.to_str().unwrap(),
        ])
        .output()
        .unwrap();
    assert!(output2.status.success());

    let mut dirs1 = fs::read_dir(&output_path_1).unwrap();
    let path1 = dirs1.next().unwrap().unwrap().path();
    let mut dirs2 = fs::read_dir(&output_path_2).unwrap();
    let path2 = dirs2.next().unwrap().unwrap().path();

    // Compare summary statistics
    let s1 = fs::read_to_string(path1.join("summary.json")).unwrap();
    let s2 = fs::read_to_string(path2.join("summary.json")).unwrap();
    let summary1: serde_json::Value = serde_json::from_str(&s1).unwrap();
    let summary2: serde_json::Value = serde_json::from_str(&s2).unwrap();

    assert_eq!(summary1["accepted_events"], summary2["accepted_events"]);
    assert_eq!(summary1["attempted_events"], summary2["attempted_events"]);
    assert_eq!(
        summary1["vetoed_cuts_events"],
        summary2["vetoed_cuts_events"]
    );

    // Compare inclusive observables files exactly
    let obs1 = fs::read_to_string(path1.join("inclusive_observables.csv")).unwrap();
    let obs2 = fs::read_to_string(path2.join("inclusive_observables.csv")).unwrap();
    assert_eq!(
        obs1, obs2,
        "CSV output must be identical for identical seed"
    );

    let _ = fs::remove_dir_all(output_path_1);
    let _ = fs::remove_dir_all(output_path_2);
}
