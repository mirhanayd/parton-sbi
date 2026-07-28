use std::process::Command;

fn main() {
    println!("cargo:rerun-if-changed=src/lhapdf_support_bridge.cpp");
    println!("cargo:rerun-if-changed=src/apfel_evolution_bridge.cpp");

    let lhapdf = pkg_config::Config::new()
        .atleast_version("6")
        .cargo_metadata(false)
        .probe("lhapdf")
        .expect("LHAPDF 6 must be available through pkg-config");
    let mut support_bridge = cc::Build::new();
    support_bridge
        .cpp(true)
        .file("src/lhapdf_support_bridge.cpp")
        .flag_if_supported("-std=c++17");
    for include_path in &lhapdf.include_paths {
        support_bridge.include(include_path);
    }
    support_bridge.compile("partonsbi_lhapdf_support_bridge");

    let apfel_config = std::env::var("APFELXX_ROOT")
        .map(|root| std::path::PathBuf::from(root).join("bin/apfelxx-config"))
        .unwrap_or_else(|_| std::path::PathBuf::from("apfelxx-config"));
    let config_value = |flag: &str| {
        let output = Command::new(&apfel_config)
            .arg(flag)
            .output()
            .unwrap_or_else(|error| {
                panic!("failed to run {} {flag}: {error}", apfel_config.display())
            });
        assert!(
            output.status.success(),
            "{} {flag} failed",
            apfel_config.display()
        );
        String::from_utf8(output.stdout)
            .expect("apfelxx-config output must be UTF-8")
            .trim()
            .to_owned()
    };
    let apfel_version = config_value("--version");
    assert_eq!(
        apfel_version, "4.8.0",
        "PartonSBI D1 is pinned to APFEL++ 4.8.0"
    );
    let apfel_root = std::env::var("APFELXX_ROOT").ok();
    let configured_include = std::path::PathBuf::from(config_value("--incdir"));
    let configured_lib = std::path::PathBuf::from(config_value("--libdir"));
    let apfel_include = if configured_include.is_dir() {
        configured_include
    } else {
        std::path::PathBuf::from(
            apfel_root
                .as_ref()
                .expect("APFELXX_ROOT is required when apfelxx-config is not relocatable"),
        )
        .join("include")
    };
    let apfel_lib = if configured_lib.is_dir() {
        configured_lib
    } else {
        std::path::PathBuf::from(
            apfel_root
                .as_ref()
                .expect("APFELXX_ROOT is required when apfelxx-config is not relocatable"),
        )
        .join("lib")
    };
    let mut evolution_bridge = cc::Build::new();
    evolution_bridge
        .cpp(true)
        .file("src/apfel_evolution_bridge.cpp")
        .include(&apfel_include)
        .flag_if_supported("-std=c++17");
    for include_path in &lhapdf.include_paths {
        evolution_bridge.include(include_path);
    }
    evolution_bridge.compile("partonsbi_apfel_evolution_bridge");
    println!("cargo:rustc-link-search=native={}", apfel_lib.display());
    println!("cargo:rustc-link-lib=dylib=apfelxx");
    pkg_config::Config::new()
        .atleast_version("6")
        .probe("lhapdf")
        .expect("LHAPDF 6 must be linkable through pkg-config");

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
