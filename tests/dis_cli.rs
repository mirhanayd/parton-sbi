use std::process::Command;

fn binary() -> Command {
    Command::new(env!("CARGO_BIN_EXE_quark_sim"))
}

#[test]
fn subcommand_help_has_no_training_or_gui_side_effects() {
    let output = binary()
        .args(["dis-kinematics", "--help"])
        .output()
        .expect("DIS help command should start");
    let stdout = String::from_utf8(output.stdout).expect("stdout should be UTF-8");

    assert!(output.status.success());
    assert!(stdout.contains("--electron-energy"));
    assert!(stdout.contains("measured from the incoming +z direction"));
    assert!(!stdout.contains("Using CPU"));
    assert!(!stdout.contains("Output directory"));
    assert!(!stdout.contains("training samples"));
}

#[test]
fn reference_cli_event_prints_expected_invariants() {
    let output = binary()
        .args([
            "dis-kinematics",
            "--electron-energy",
            "27.5",
            "--proton-energy",
            "920.0",
            "--scattered-electron-energy",
            "15.0",
            "--theta-deg",
            "20.0",
        ])
        .output()
        .expect("DIS calculation command should start");
    let stdout = String::from_utf8(output.stdout).expect("stdout should be UTF-8");

    assert!(output.status.success());
    assert!(stdout.contains("s   = 101200.854031085386 GeV²"));
    assert!(stdout.contains("Q²  = 49.753587913075 GeV²"));
    assert!(stdout.contains("x   = 0.001043829650"));
    assert!(stdout.contains("y   = 0.470992917430"));
    assert!(stdout.contains("W²  = 47615.597612251062 GeV²"));
}

#[test]
fn unphysical_cli_input_exits_with_an_error() {
    let output = binary()
        .args([
            "dis-kinematics",
            "--electron-energy",
            "-1",
            "--proton-energy",
            "920.0",
            "--scattered-electron-energy",
            "15.0",
            "--theta-deg",
            "20.0",
        ])
        .output()
        .expect("invalid DIS command should start");
    let stderr = String::from_utf8(output.stderr).expect("stderr should be UTF-8");

    assert!(!output.status.success());
    assert!(stderr.contains("incoming electron energy must be positive"));
}
