use serde_json::Value;
use std::fs;
use std::process::Command;

// Deterministic snapshot tolerance
const TOLERANCE: f64 = 1e-4;

#[test]
fn test_apfel_cli_snapshot() {
    let output = Command::new("cargo")
        .args([
            "run",
            "--release",
            "--",
            "structure-functions",
            "--backend",
            "apfel",
            "--x",
            "0.01",
            "--q2",
            "100",
            "--order",
            "NLO",
            "--pdf-set",
            "CT18NLO",
        ])
        .output()
        .expect("Failed to execute command");

    assert!(output.status.success());
    let result_str = String::from_utf8(output.stdout).unwrap();

    // Parse generated and snapshot JSON
    let generated: Value = serde_json::from_str(&result_str).unwrap();
    let snapshot_str =
        fs::read_to_string("tests/fixtures/apfel_nlo.json").expect("Fixture missing");
    let snapshot: Value = serde_json::from_str(&snapshot_str).unwrap();

    let gen_f2 = generated["f2"].as_f64().unwrap();
    let snap_f2 = snapshot["f2"].as_f64().unwrap();
    assert!(
        (gen_f2 - snap_f2).abs() < TOLERANCE,
        "F2 deviation: {} vs {}",
        gen_f2,
        snap_f2
    );
}

#[test]
fn test_surrogate_snapshot() {
    let output = Command::new("cargo")
        .args([
            "run",
            "--release",
            "--",
            "structure-functions",
            "--backend",
            "surrogate",
            "--x",
            "0.01",
            "--q2",
            "100",
            "--order",
            "NLO",
            "--pdf-set",
            "CT18NLO",
            "--pdf-member",
            "0",
        ])
        .output()
        .expect("Failed to execute command");

    assert!(output.status.success());
    let result_str = String::from_utf8(output.stdout).unwrap();

    assert!(result_str.contains("\"f2\""));
}
