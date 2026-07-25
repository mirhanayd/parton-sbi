//! Manual parsing for the structure-function subcommands.
//!
//! The legacy executable already uses a small manual parser. Keeping the new
//! commands here avoids a partial migration to a second CLI framework while
//! still giving their larger option sets one shared, thoroughly tested parser.

use std::env;
use std::ffi::OsStr;
use std::path::{Path, PathBuf};
use std::str::FromStr;

use quark_sim::physics::{PerturbativeOrder, DEFAULT_APFEL_BACKEND_PATH};

pub const STRUCTURE_FUNCTIONS_HELP: &str = r#"Inclusive neutral-current DIS structure functions

Usage:
  quark_sim structure-functions \
      --backend <lo|apfel> \
      --x <BJORKEN_X> \
      --q2 <GEV2> \
      --order <LO|NLO> \
      --pdf-set <INSTALLED_SET> \
      --pdf-member <INDEX> \
      [--mu-f-over-q <RATIO>] \
      [--mu-r-over-q <RATIO>] \
      [--apfel-backend <PATH>]

The scale ratios default to 1.0. The direct 'lo' backend only accepts LO
with unit scales. For 'apfel', the executable is resolved in this order:
--apfel-backend, APFEL_BACKEND_BIN, then physics-engine/build/apfel_cli.
An unavailable APFEL backend is an error; there is no fallback to direct LO.
"#;

pub const VALIDATE_STRUCTURE_FUNCTIONS_HELP: &str = r#"Validate APFEL structure functions against the direct LO baseline

Usage:
  quark_sim validate-structure-functions \
      --pdf-set <INSTALLED_SET> \
      --output <DIRECTORY> \
      [--pdf-member <INDEX>] \
      [--order <LO|NLO>] \
      [--mu-f-over-q <RATIO>] \
      [--mu-r-over-q <RATIO>] \
      [--apfel-backend <PATH>]

Defaults:
  --pdf-member 0
  --order NLO
  --mu-f-over-q 1.0
  --mu-r-over-q 1.0

The output directory may already exist, but apfel_vs_lo.csv,
apfel_vs_lo.json, and apfel_vs_lo.svg are never overwritten. The direct
baseline is always LO with unit scales and the same PDF set/member.
"#;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RequestedStructureFunctionBackend {
    Lo,
    Apfel,
}

impl RequestedStructureFunctionBackend {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Lo => "lo",
            Self::Apfel => "apfel",
        }
    }
}

impl FromStr for RequestedStructureFunctionBackend {
    type Err = String;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        if value.eq_ignore_ascii_case("lo") {
            Ok(Self::Lo)
        } else if value.eq_ignore_ascii_case("apfel") {
            Ok(Self::Apfel)
        } else {
            Err(format!(
                "unsupported structure-function backend '{value}'; expected lo or apfel"
            ))
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum StructureFunctionsCliCommand {
    Calculate(StructureFunctionsCliArgs),
    Help,
}

#[derive(Debug, Clone, PartialEq)]
pub struct StructureFunctionsCliArgs {
    pub backend: RequestedStructureFunctionBackend,
    pub x: f64,
    pub q2: f64,
    pub order: PerturbativeOrder,
    pub pdf_set: String,
    pub pdf_member: i32,
    pub mu_f_over_q: f64,
    pub mu_r_over_q: f64,
    pub apfel_backend: Option<PathBuf>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ValidateStructureFunctionsCliCommand {
    Run(ValidateStructureFunctionsCliArgs),
    Help,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ValidateStructureFunctionsCliArgs {
    pub pdf_set: String,
    pub output: PathBuf,
    pub pdf_member: i32,
    pub order: PerturbativeOrder,
    pub mu_f_over_q: f64,
    pub mu_r_over_q: f64,
    pub apfel_backend: Option<PathBuf>,
}

pub fn parse_structure_functions_command(
    args: &[String],
) -> Result<StructureFunctionsCliCommand, String> {
    const COMMAND: &str = "structure-functions";

    if is_help_only(args) {
        return Ok(StructureFunctionsCliCommand::Help);
    }
    if args.is_empty() {
        return Err(format!(
            "{COMMAND} requires backend, kinematics, order, and PDF options\n\n{STRUCTURE_FUNCTIONS_HELP}"
        ));
    }

    let mut backend = None;
    let mut x = None;
    let mut q2 = None;
    let mut order = None;
    let mut pdf_set = None;
    let mut pdf_member = None;
    let mut mu_f_over_q = None;
    let mut mu_r_over_q = None;
    let mut apfel_backend = None;
    let mut index = 0;

    while index < args.len() {
        let flag = args[index].as_str();
        reject_mixed_help(flag, COMMAND)?;
        let value = option_value(args, index, flag)?;

        match flag {
            "--backend" => set_once(
                &mut backend,
                RequestedStructureFunctionBackend::from_str(value)?,
                flag,
                COMMAND,
            )?,
            "--x" => set_once(&mut x, parse_x(value)?, flag, COMMAND)?,
            "--q2" => set_once(&mut q2, parse_positive(value, flag)?, flag, COMMAND)?,
            "--order" => set_once(
                &mut order,
                PerturbativeOrder::from_str(value).map_err(|error| error.to_string())?,
                flag,
                COMMAND,
            )?,
            "--pdf-set" => set_once(&mut pdf_set, parse_pdf_set(value)?, flag, COMMAND)?,
            "--pdf-member" => set_once(
                &mut pdf_member,
                parse_pdf_member(value, flag)?,
                flag,
                COMMAND,
            )?,
            "--mu-f-over-q" => set_once(
                &mut mu_f_over_q,
                parse_positive(value, flag)?,
                flag,
                COMMAND,
            )?,
            "--mu-r-over-q" => set_once(
                &mut mu_r_over_q,
                parse_positive(value, flag)?,
                flag,
                COMMAND,
            )?,
            "--apfel-backend" => set_once(
                &mut apfel_backend,
                parse_non_empty_path(value, flag)?,
                flag,
                COMMAND,
            )?,
            _ => return Err(format!("unknown {COMMAND} option: {flag}")),
        }
        index += 2;
    }

    let parsed = StructureFunctionsCliArgs {
        backend: required(backend, "--backend", COMMAND)?,
        x: required(x, "--x", COMMAND)?,
        q2: required(q2, "--q2", COMMAND)?,
        order: required(order, "--order", COMMAND)?,
        pdf_set: required(pdf_set, "--pdf-set", COMMAND)?,
        pdf_member: required(pdf_member, "--pdf-member", COMMAND)?,
        mu_f_over_q: mu_f_over_q.unwrap_or(1.0),
        mu_r_over_q: mu_r_over_q.unwrap_or(1.0),
        apfel_backend,
    };
    validate_backend_combination(&parsed)?;
    Ok(StructureFunctionsCliCommand::Calculate(parsed))
}

pub fn parse_validate_structure_functions_command(
    args: &[String],
) -> Result<ValidateStructureFunctionsCliCommand, String> {
    const COMMAND: &str = "validate-structure-functions";

    if is_help_only(args) {
        return Ok(ValidateStructureFunctionsCliCommand::Help);
    }
    if args.is_empty() {
        return Err(format!(
            "{COMMAND} requires --pdf-set and --output\n\n{VALIDATE_STRUCTURE_FUNCTIONS_HELP}"
        ));
    }

    let mut pdf_set = None;
    let mut output = None;
    let mut pdf_member = None;
    let mut order = None;
    let mut mu_f_over_q = None;
    let mut mu_r_over_q = None;
    let mut apfel_backend = None;
    let mut index = 0;

    while index < args.len() {
        let flag = args[index].as_str();
        reject_mixed_help(flag, COMMAND)?;
        let value = option_value(args, index, flag)?;

        match flag {
            "--pdf-set" => set_once(&mut pdf_set, parse_pdf_set(value)?, flag, COMMAND)?,
            "--output" => set_once(
                &mut output,
                parse_non_empty_path(value, flag)?,
                flag,
                COMMAND,
            )?,
            "--pdf-member" => set_once(
                &mut pdf_member,
                parse_pdf_member(value, flag)?,
                flag,
                COMMAND,
            )?,
            "--order" => set_once(
                &mut order,
                PerturbativeOrder::from_str(value).map_err(|error| error.to_string())?,
                flag,
                COMMAND,
            )?,
            "--mu-f-over-q" => set_once(
                &mut mu_f_over_q,
                parse_positive(value, flag)?,
                flag,
                COMMAND,
            )?,
            "--mu-r-over-q" => set_once(
                &mut mu_r_over_q,
                parse_positive(value, flag)?,
                flag,
                COMMAND,
            )?,
            "--apfel-backend" => set_once(
                &mut apfel_backend,
                parse_non_empty_path(value, flag)?,
                flag,
                COMMAND,
            )?,
            _ => return Err(format!("unknown {COMMAND} option: {flag}")),
        }
        index += 2;
    }

    Ok(ValidateStructureFunctionsCliCommand::Run(
        ValidateStructureFunctionsCliArgs {
            pdf_set: required(pdf_set, "--pdf-set", COMMAND)?,
            output: required(output, "--output", COMMAND)?,
            pdf_member: pdf_member.unwrap_or(0),
            order: order.unwrap_or(PerturbativeOrder::Nlo),
            mu_f_over_q: mu_f_over_q.unwrap_or(1.0),
            mu_r_over_q: mu_r_over_q.unwrap_or(1.0),
            apfel_backend,
        },
    ))
}

/// Resolve the APFEL executable without probing or running it.
///
/// Resolution is deliberately separate from parsing so help remains
/// side-effect free. Callers may validate or start the returned path only when
/// actually executing an APFEL-backed command.
pub fn resolve_apfel_backend_path(explicit: Option<&Path>) -> Result<PathBuf, String> {
    let environment = env::var_os("APFEL_BACKEND_BIN");
    resolve_apfel_backend_path_from(
        explicit,
        environment.as_deref(),
        Path::new(env!("CARGO_MANIFEST_DIR")),
    )
}

/// Pure implementation of APFEL executable precedence, exposed for tests.
pub fn resolve_apfel_backend_path_from(
    explicit: Option<&Path>,
    environment: Option<&OsStr>,
    manifest_dir: &Path,
) -> Result<PathBuf, String> {
    if let Some(path) = explicit {
        if path.as_os_str().is_empty() {
            return Err("--apfel-backend must not be empty".to_owned());
        }
        return Ok(path.to_path_buf());
    }
    if let Some(path) = environment {
        if path.is_empty() {
            return Err("APFEL_BACKEND_BIN is set but empty".to_owned());
        }
        return Ok(PathBuf::from(path));
    }
    Ok(manifest_dir.join(DEFAULT_APFEL_BACKEND_PATH))
}

/// Check the resolved backend immediately before execution.
pub fn validate_apfel_backend_executable(path: &Path) -> Result<(), String> {
    let metadata = std::fs::metadata(path).map_err(|error| {
        format!(
            "APFEL++ backend '{}' is unavailable: {error}; run scripts/setup_apfelxx_wsl.sh",
            path.display()
        )
    })?;
    if !metadata.is_file() {
        return Err(format!(
            "APFEL++ backend '{}' is not a regular file",
            path.display()
        ));
    }

    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;

        if metadata.permissions().mode() & 0o111 == 0 {
            return Err(format!(
                "APFEL++ backend '{}' is not executable",
                path.display()
            ));
        }
    }
    Ok(())
}

fn validate_backend_combination(arguments: &StructureFunctionsCliArgs) -> Result<(), String> {
    if arguments.backend == RequestedStructureFunctionBackend::Lo {
        if arguments.order != PerturbativeOrder::Lo {
            return Err(
                "the direct lo backend only supports --order LO; APFEL is required for NLO"
                    .to_owned(),
            );
        }
        if arguments.mu_f_over_q != 1.0 || arguments.mu_r_over_q != 1.0 {
            return Err(
                "the direct lo backend only supports --mu-f-over-q 1 and --mu-r-over-q 1"
                    .to_owned(),
            );
        }
        if arguments.apfel_backend.is_some() {
            return Err("--apfel-backend is only valid with --backend apfel".to_owned());
        }
    }
    Ok(())
}

fn is_help_only(args: &[String]) -> bool {
    matches!(args, [flag] if flag == "-h" || flag == "--help")
}

fn reject_mixed_help(flag: &str, command: &str) -> Result<(), String> {
    if flag == "-h" || flag == "--help" {
        Err(format!("--help must be used by itself after {command}"))
    } else {
        Ok(())
    }
}

fn option_value<'a>(args: &'a [String], index: usize, flag: &str) -> Result<&'a str, String> {
    if !flag.starts_with("--") {
        return Err(format!(
            "unexpected positional argument for structure-function command: {flag}"
        ));
    }
    args.get(index + 1)
        .filter(|value| value.as_str() != "-h" && !value.starts_with("--"))
        .map(String::as_str)
        .ok_or_else(|| format!("{flag} requires a value"))
}

fn parse_finite(value: &str, flag: &str) -> Result<f64, String> {
    let parsed = value
        .parse::<f64>()
        .map_err(|_| format!("invalid numeric value for {flag}: {value}"))?;
    if !parsed.is_finite() {
        return Err(format!("{flag} must be finite, got {value}"));
    }
    Ok(parsed)
}

fn parse_x(value: &str) -> Result<f64, String> {
    let parsed = parse_finite(value, "--x")?;
    if parsed <= 0.0 || parsed >= 1.0 {
        return Err(format!("--x must satisfy 0 < x < 1, got {value}"));
    }
    Ok(parsed)
}

fn parse_positive(value: &str, flag: &str) -> Result<f64, String> {
    let parsed = parse_finite(value, flag)?;
    if parsed <= 0.0 {
        return Err(format!("{flag} must be positive, got {value}"));
    }
    Ok(parsed)
}

fn parse_pdf_member(value: &str, flag: &str) -> Result<i32, String> {
    let parsed = value
        .parse::<i32>()
        .map_err(|_| format!("invalid non-negative integer for {flag}: {value}"))?;
    if parsed < 0 {
        return Err(format!("{flag} must be non-negative, got {value}"));
    }
    Ok(parsed)
}

fn parse_pdf_set(value: &str) -> Result<String, String> {
    if value.is_empty() || value.trim() != value {
        return Err(
            "--pdf-set must be non-empty without leading or trailing whitespace".to_owned(),
        );
    }
    Ok(value.to_owned())
}

fn parse_non_empty_path(value: &str, flag: &str) -> Result<PathBuf, String> {
    if value.trim().is_empty() {
        return Err(format!("{flag} must not be empty"));
    }
    Ok(PathBuf::from(value))
}

fn set_once<T>(slot: &mut Option<T>, value: T, flag: &str, command: &str) -> Result<(), String> {
    if slot.replace(value).is_some() {
        Err(format!("duplicate {command} option: {flag}"))
    } else {
        Ok(())
    }
}

fn required<T>(value: Option<T>, flag: &str, command: &str) -> Result<T, String> {
    value.ok_or_else(|| format!("missing required {command} option: {flag}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn strings(values: &[&str]) -> Vec<String> {
        values.iter().map(|value| (*value).to_owned()).collect()
    }

    fn parse_structure(values: &[&str]) -> Result<StructureFunctionsCliCommand, String> {
        parse_structure_functions_command(&strings(values))
    }

    fn parse_validation(values: &[&str]) -> Result<ValidateStructureFunctionsCliCommand, String> {
        parse_validate_structure_functions_command(&strings(values))
    }

    #[test]
    fn help_is_explicit_and_side_effect_free() {
        assert_eq!(
            parse_structure(&["--help"]),
            Ok(StructureFunctionsCliCommand::Help)
        );
        assert_eq!(
            parse_validation(&["-h"]),
            Ok(ValidateStructureFunctionsCliCommand::Help)
        );
        assert!(parse_structure(&["--help", "--x", "0.1"]).is_err());
        assert!(parse_validation(&["--pdf-set", "CT18NLO", "--help"]).is_err());
    }

    #[test]
    fn parses_apfel_point_options_in_any_order_and_defaults_scales() {
        let command = parse_structure(&[
            "--pdf-member",
            "3",
            "--q2",
            "100",
            "--backend",
            "APFEL",
            "--pdf-set",
            "CT18NLO",
            "--order",
            "nlo",
            "--x",
            "0.01",
        ])
        .unwrap();

        let StructureFunctionsCliCommand::Calculate(arguments) = command else {
            panic!("expected a calculation");
        };
        assert_eq!(arguments.backend, RequestedStructureFunctionBackend::Apfel);
        assert_eq!(arguments.order, PerturbativeOrder::Nlo);
        assert_eq!((arguments.x, arguments.q2), (0.01, 100.0));
        assert_eq!((arguments.mu_f_over_q, arguments.mu_r_over_q), (1.0, 1.0));
        assert_eq!(arguments.pdf_member, 3);
        assert_eq!(arguments.apfel_backend, None);
    }

    #[test]
    fn validation_has_documented_defaults() {
        let command =
            parse_validation(&["--output", "outputs/check", "--pdf-set", "CT18NLO"]).unwrap();

        let ValidateStructureFunctionsCliCommand::Run(arguments) = command else {
            panic!("expected validation");
        };
        assert_eq!(arguments.pdf_member, 0);
        assert_eq!(arguments.order, PerturbativeOrder::Nlo);
        assert_eq!((arguments.mu_f_over_q, arguments.mu_r_over_q), (1.0, 1.0));
        assert_eq!(arguments.output, PathBuf::from("outputs/check"));
    }

    #[test]
    fn validation_accepts_explicit_member_order_scales_and_backend() {
        let command = parse_validation(&[
            "--pdf-set",
            "CT18NLO",
            "--output",
            "validation run",
            "--pdf-member",
            "2",
            "--order",
            "LO",
            "--mu-f-over-q",
            "0.5",
            "--mu-r-over-q",
            "2",
            "--apfel-backend",
            "/tmp/apfel cli",
        ])
        .unwrap();

        let ValidateStructureFunctionsCliCommand::Run(arguments) = command else {
            panic!("expected validation");
        };
        assert_eq!(arguments.pdf_member, 2);
        assert_eq!(arguments.order, PerturbativeOrder::Lo);
        assert_eq!((arguments.mu_f_over_q, arguments.mu_r_over_q), (0.5, 2.0));
        assert_eq!(
            arguments.apfel_backend,
            Some(PathBuf::from("/tmp/apfel cli"))
        );
    }

    #[test]
    fn rejects_missing_duplicate_unknown_and_orphan_options() {
        assert!(parse_structure(&[]).is_err());
        assert!(parse_validation(&[]).is_err());
        assert!(parse_structure(&["--backend", "apfel"]).is_err());
        assert!(parse_validation(&["--pdf-set", "CT18NLO"]).is_err());
        assert!(parse_validation(&[
            "--pdf-set",
            "CT18NLO",
            "--pdf-set",
            "Other",
            "--output",
            "out",
        ])
        .is_err());
        assert!(parse_structure(&["--unknown", "value"]).is_err());
        assert!(parse_validation(&["positional"]).is_err());
        assert!(parse_structure(&["--x", "--q2", "100"]).is_err());
    }

    #[test]
    fn rejects_invalid_numbers_members_orders_and_names() {
        let common = [
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
            "--pdf-member",
            "0",
        ];
        for invalid_x in ["0", "1", "NaN", "inf"] {
            let mut args = common.to_vec();
            args[3] = invalid_x;
            assert!(parse_structure(&args).is_err());
        }
        for invalid_q2 in ["0", "-1", "NaN"] {
            let mut args = common.to_vec();
            args[5] = invalid_q2;
            assert!(parse_structure(&args).is_err());
        }
        let mut args = common.to_vec();
        args[7] = "NNLO";
        assert!(parse_structure(&args).is_err());
        let mut args = common.to_vec();
        args[11] = "-1";
        assert!(parse_structure(&args).is_err());
        let mut args = common.to_vec();
        args[9] = " CT18NLO";
        assert!(parse_structure(&args).is_err());
    }

    #[test]
    fn direct_lo_backend_rejects_unsupported_configuration() {
        let base = [
            "--backend",
            "lo",
            "--x",
            "0.01",
            "--q2",
            "100",
            "--order",
            "LO",
            "--pdf-set",
            "CT18LO",
            "--pdf-member",
            "0",
        ];
        assert!(parse_structure(&base).is_ok());

        let mut nlo = base.to_vec();
        nlo[7] = "NLO";
        assert!(parse_structure(&nlo).is_err());

        let mut scaled = base.to_vec();
        scaled.extend(["--mu-f-over-q", "2"]);
        assert!(parse_structure(&scaled).is_err());

        let mut backend_path = base.to_vec();
        backend_path.extend(["--apfel-backend", "/tmp/apfel_cli"]);
        assert!(parse_structure(&backend_path).is_err());
    }

    #[test]
    fn backend_path_resolution_has_deterministic_precedence() {
        let manifest = Path::new("/repo");
        let explicit = Path::new("/explicit/apfel_cli");

        assert_eq!(
            resolve_apfel_backend_path_from(
                Some(explicit),
                Some(OsStr::new("/environment/apfel_cli")),
                manifest,
            )
            .unwrap(),
            explicit
        );
        assert_eq!(
            resolve_apfel_backend_path_from(
                None,
                Some(OsStr::new("/environment/apfel_cli")),
                manifest,
            )
            .unwrap(),
            PathBuf::from("/environment/apfel_cli")
        );
        assert_eq!(
            resolve_apfel_backend_path_from(None, None, manifest).unwrap(),
            manifest.join(DEFAULT_APFEL_BACKEND_PATH)
        );
        assert!(resolve_apfel_backend_path_from(None, Some(OsStr::new("")), manifest).is_err());
    }

    #[test]
    fn missing_backend_validation_error_names_setup_action() {
        let missing = Path::new("/definitely/missing/apfel_cli");
        let error = validate_apfel_backend_executable(missing).unwrap_err();
        assert!(error.contains("setup_apfelxx_wsl.sh"));
        assert!(error.contains("apfel_cli"));
    }
}
