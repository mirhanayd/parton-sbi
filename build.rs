use std::process::Command;

fn main() {
    // Re-run this build script if the .git directory changes
    println!("cargo:rerun-if-changed=.git/HEAD");
    println!("cargo:rerun-if-changed=.git/index");

    // Capture Git Hash
    let git_hash = Command::new("git")
        .args(["rev-parse", "HEAD"])
        .output()
        .ok()
        .and_then(|output| String::from_utf8(output.stdout).ok())
        .map(|s| s.trim().to_string())
        .unwrap_or_else(|| "unknown".to_string());
    println!("cargo:rustc-env=GIT_HASH={}", git_hash);

    // Capture Git Dirty State
    let git_dirty = Command::new("git")
        .args(["status", "--porcelain"])
        .output()
        .ok()
        .and_then(|output| String::from_utf8(output.stdout).ok())
        .map(|s| !s.trim().is_empty())
        .unwrap_or(false);
    println!("cargo:rustc-env=GIT_DIRTY={}", git_dirty);

    // Capture Rustc Version
    let rustc_version = Command::new("rustc")
        .args(["--version"])
        .output()
        .ok()
        .and_then(|output| String::from_utf8(output.stdout).ok())
        .map(|s| s.trim().to_string())
        .unwrap_or_else(|| "unknown".to_string());
    println!("cargo:rustc-env=RUSTC_VERSION={}", rustc_version);

    // Capture OS details roughly
    let os_arch = std::env::consts::OS.to_string() + "-" + std::env::consts::ARCH;
    println!("cargo:rustc-env=OS_ARCH={}", os_arch);
}
