use std::path::PathBuf;

use parton_sbi::physics::require_signed_facade_compatibility;
#[cfg(test)]
use parton_sbi::physics::{
    D1C_B_D2_AUTHORIZED, D1C_B_PYTHIA_NEXT_EXECUTED, D1C_B_SCIENTIFIC_STUDY_RESULT_AVAILABLE,
};

pub const PROTOTYPE_PYTHIA_PDF_FACADE_HELP: &str =
    "Phase 1B-D1C-B PYTHIA PDF facade admission check

Usage:
  parton-sbi prototype-pythia-pdf-facade --prepare-only --output <DIRECTORY>

The installed PYTHIA 8.312 PDF boundary is checked before any output or Pythia
object is created. The command fails closed because non-virtual xf/xfVal/xfSea
methods clip signed values. It has no study, event, next, or generate mode.
";

#[derive(Debug, Clone, PartialEq)]
pub struct PythiaPdfFacadeCliArgs {
    pub output: PathBuf,
}

pub fn parse_prototype_pythia_pdf_facade(
    arguments: &[String],
) -> Result<PythiaPdfFacadeCliArgs, String> {
    let mut prepare_only = false;
    let mut output = None;
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--prepare-only" if !prepare_only => prepare_only = true,
            "--prepare-only" => return Err("--prepare-only was provided more than once".into()),
            "--output" => {
                index += 1;
                let value = arguments
                    .get(index)
                    .ok_or_else(|| "--output requires a path".to_owned())?;
                if output.replace(PathBuf::from(value)).is_some() {
                    return Err("--output was provided more than once".into());
                }
            }
            "--study" | "--events" | "--next" | "--generate" => {
                return Err(format!(
                    "{} is forbidden by the D1C-B preparation-only contract",
                    arguments[index]
                ));
            }
            flag => {
                return Err(format!(
                    "unknown prototype-pythia-pdf-facade option: {flag}"
                ))
            }
        }
        index += 1;
    }
    if !prepare_only {
        return Err("prototype-pythia-pdf-facade requires --prepare-only".into());
    }
    Ok(PythiaPdfFacadeCliArgs {
        output: output.ok_or_else(|| "--output is required".to_owned())?,
    })
}

pub fn run_prototype_pythia_pdf_facade(_arguments: PythiaPdfFacadeCliArgs) -> Result<(), String> {
    require_signed_facade_compatibility()
        .map(|_| ())
        .map_err(|error| {
            format!("D1C-B facade admission rejected before Pythia initialization: {error}")
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn prototype_pythia_pdf_facade_parser_has_no_event_or_study_mode() {
        let parsed = parse_prototype_pythia_pdf_facade(&[
            "--prepare-only".into(),
            "--output".into(),
            "outputs/d1c_b".into(),
        ])
        .unwrap();
        assert_eq!(parsed.output, PathBuf::from("outputs/d1c_b"));
        for forbidden in ["--study", "--events", "--next", "--generate"] {
            assert!(parse_prototype_pythia_pdf_facade(&[forbidden.into()]).is_err());
        }
    }

    #[test]
    fn prototype_pythia_pdf_facade_stops_before_output_init_or_d2() {
        let output = std::env::temp_dir().join(format!(
            "partonsbi-d1c-b-forbidden-output-{}",
            std::process::id()
        ));
        let _ = std::fs::remove_dir_all(&output);
        let error = run_prototype_pythia_pdf_facade(PythiaPdfFacadeCliArgs {
            output: output.clone(),
        })
        .unwrap_err();
        assert!(error.contains("non-virtual PDF boundary clips signed values"));
        assert!(!output.exists());
        const {
            assert!(!D1C_B_PYTHIA_NEXT_EXECUTED);
            assert!(!D1C_B_SCIENTIFIC_STUDY_RESULT_AVAILABLE);
            assert!(!D1C_B_D2_AUTHORIZED);
        }
    }
}
