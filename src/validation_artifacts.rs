//! CSV, JSON, and SVG artifacts for structure-function validation.
//!
//! This module is intentionally independent of the legacy Cornell plotting
//! code and Candle. It validates the complete report before writing, permits an
//! existing output directory, and never overwrites a final artifact.

use std::error::Error;
use std::fmt;
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufWriter, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use plotters::backend::SVGBackend;
use plotters::prelude::*;

use crate::physics::structure_function_validation::{
    StructureFunctionValidationError, StructureFunctionValidationReport,
    StructureFunctionValidationRow, VALIDATION_Q2_VALUES_GEV2,
};

pub const VALIDATION_CSV_FILENAME: &str = "apfel_vs_lo.csv";
pub const VALIDATION_JSON_FILENAME: &str = "apfel_vs_lo.json";
pub const VALIDATION_SVG_FILENAME: &str = "apfel_vs_lo.svg";

static TEMP_FILE_COUNTER: AtomicU64 = AtomicU64::new(0);

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationArtifactPaths {
    pub csv: PathBuf,
    pub json: PathBuf,
    pub svg: PathBuf,
}

impl ValidationArtifactPaths {
    #[must_use]
    pub fn in_directory(output_directory: &Path) -> Self {
        Self {
            csv: output_directory.join(VALIDATION_CSV_FILENAME),
            json: output_directory.join(VALIDATION_JSON_FILENAME),
            svg: output_directory.join(VALIDATION_SVG_FILENAME),
        }
    }

    fn as_array(&self) -> [&Path; 3] {
        [&self.csv, &self.json, &self.svg]
    }
}

#[derive(Debug)]
pub enum ValidationArtifactError {
    InvalidReport(StructureFunctionValidationError),
    EmptyOutputPath,
    OutputIsNotDirectory {
        path: PathBuf,
    },
    ArtifactExists {
        path: PathBuf,
    },
    Io {
        operation: &'static str,
        path: PathBuf,
        source: io::Error,
    },
    Csv {
        path: PathBuf,
        source: csv::Error,
    },
    Json {
        path: PathBuf,
        source: serde_json::Error,
    },
    Plot {
        path: PathBuf,
        message: String,
    },
}

impl fmt::Display for ValidationArtifactError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidReport(source) => write!(formatter, "{source}"),
            Self::EmptyOutputPath => write!(formatter, "validation output path must not be empty"),
            Self::OutputIsNotDirectory { path } => write!(
                formatter,
                "validation output path '{}' exists but is not a directory",
                path.display()
            ),
            Self::ArtifactExists { path } => write!(
                formatter,
                "refusing to overwrite existing validation artifact '{}'",
                path.display()
            ),
            Self::Io {
                operation,
                path,
                source,
            } => write!(
                formatter,
                "failed while {operation} '{}': {source}",
                path.display()
            ),
            Self::Csv { path, source } => {
                write!(
                    formatter,
                    "failed to serialize CSV '{}': {source}",
                    path.display()
                )
            }
            Self::Json { path, source } => write!(
                formatter,
                "failed to serialize JSON '{}': {source}",
                path.display()
            ),
            Self::Plot { path, message } => write!(
                formatter,
                "failed to render SVG '{}': {message}",
                path.display()
            ),
        }
    }
}

impl Error for ValidationArtifactError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::InvalidReport(source) => Some(source),
            Self::Io { source, .. } => Some(source),
            Self::Csv { source, .. } => Some(source),
            Self::Json { source, .. } => Some(source),
            _ => None,
        }
    }
}

impl From<StructureFunctionValidationError> for ValidationArtifactError {
    fn from(source: StructureFunctionValidationError) -> Self {
        Self::InvalidReport(source)
    }
}

/// Generate all three validation artifacts without replacing existing files.
pub fn write_validation_artifacts(
    output_directory: &Path,
    report: &StructureFunctionValidationReport,
) -> Result<ValidationArtifactPaths, ValidationArtifactError> {
    report.validate()?;
    prepare_output_directory(output_directory)?;

    let final_paths = ValidationArtifactPaths::in_directory(output_directory);
    reject_existing_artifacts(&final_paths)?;

    let csv_temp = allocate_temp_path(output_directory, VALIDATION_CSV_FILENAME);
    let json_temp = allocate_temp_path(output_directory, VALIDATION_JSON_FILENAME);
    let svg_temp = allocate_temp_path(output_directory, VALIDATION_SVG_FILENAME);
    let mut temporary_files = TemporaryFiles::default();

    let csv_file = create_new_file(&csv_temp, "creating temporary CSV")?;
    temporary_files.track(csv_temp.clone());
    write_csv(&csv_temp, csv_file, report)?;

    let json_file = create_new_file(&json_temp, "creating temporary JSON")?;
    temporary_files.track(json_temp.clone());
    write_json(&json_temp, json_file, report)?;

    let svg_file = create_new_file(&svg_temp, "reserving temporary SVG")?;
    drop(svg_file);
    temporary_files.track(svg_temp.clone());
    write_svg(&svg_temp, report)?;

    // Check the full set once more before creating any final file. The final
    // copy itself uses create_new, so a concurrent writer still cannot be
    // overwritten after this check.
    reject_existing_artifacts(&final_paths)?;
    persist_without_overwrite(&csv_temp, &final_paths.csv)?;
    temporary_files.untrack(&csv_temp);
    persist_without_overwrite(&json_temp, &final_paths.json)?;
    temporary_files.untrack(&json_temp);
    persist_without_overwrite(&svg_temp, &final_paths.svg)?;
    temporary_files.untrack(&svg_temp);

    Ok(final_paths)
}

fn prepare_output_directory(path: &Path) -> Result<(), ValidationArtifactError> {
    if path.as_os_str().is_empty() {
        return Err(ValidationArtifactError::EmptyOutputPath);
    }
    if path.exists() {
        if !path.is_dir() {
            return Err(ValidationArtifactError::OutputIsNotDirectory {
                path: path.to_owned(),
            });
        }
        return Ok(());
    }
    fs::create_dir_all(path).map_err(|source| ValidationArtifactError::Io {
        operation: "creating validation output directory",
        path: path.to_owned(),
        source,
    })
}

fn reject_existing_artifacts(
    paths: &ValidationArtifactPaths,
) -> Result<(), ValidationArtifactError> {
    for path in paths.as_array() {
        if path.exists() {
            return Err(ValidationArtifactError::ArtifactExists {
                path: path.to_owned(),
            });
        }
    }
    Ok(())
}

fn allocate_temp_path(output_directory: &Path, final_name: &str) -> PathBuf {
    let serial = TEMP_FILE_COUNTER.fetch_add(1, Ordering::Relaxed);
    output_directory.join(format!(".{final_name}.tmp-{}-{serial}", std::process::id()))
}

fn write_csv(
    path: &Path,
    file: File,
    report: &StructureFunctionValidationReport,
) -> Result<(), ValidationArtifactError> {
    let mut writer = csv::WriterBuilder::new()
        .has_headers(true)
        .from_writer(file);
    for row in &report.rows {
        writer
            .serialize(row)
            .map_err(|source| ValidationArtifactError::Csv {
                path: path.to_owned(),
                source,
            })?;
    }
    writer
        .flush()
        .map_err(|source| ValidationArtifactError::Io {
            operation: "flushing temporary CSV",
            path: path.to_owned(),
            source,
        })
}

fn write_json(
    path: &Path,
    file: File,
    report: &StructureFunctionValidationReport,
) -> Result<(), ValidationArtifactError> {
    let mut writer = BufWriter::new(file);
    serde_json::to_writer_pretty(&mut writer, report).map_err(|source| {
        ValidationArtifactError::Json {
            path: path.to_owned(),
            source,
        }
    })?;
    writer
        .write_all(b"\n")
        .and_then(|()| writer.flush())
        .map_err(|source| ValidationArtifactError::Io {
            operation: "flushing temporary JSON",
            path: path.to_owned(),
            source,
        })
}

fn write_svg(
    path: &Path,
    report: &StructureFunctionValidationReport,
) -> Result<(), ValidationArtifactError> {
    let drawing_area = SVGBackend::new(path, (1_200, 900)).into_drawing_area();
    drawing_area
        .fill(&WHITE)
        .map_err(|error| plot_error(path, error))?;
    let panels = drawing_area.split_evenly((2, 1));

    let (f2_min, f2_max) = value_range(
        report.rows.iter().flat_map(|row| [row.lo_f2, row.apfel_f2]),
        0.0,
        1.0,
    );
    let (relative_min, relative_max) = value_range(
        report
            .rows
            .iter()
            .filter_map(|row| row.f2_relative_difference),
        0.0,
        1.0,
    );
    let x_min = report.metadata.grid.x_values[0].log10();
    let x_max = report.metadata.grid.x_values[report.metadata.grid.x_values.len() - 1].log10();

    let top_caption = format!(
        "APFEL vs direct LO F₂ — {}/{} — APFEL {} — lines: LO, markers: APFEL",
        report.metadata.pdf.set, report.metadata.pdf.member, report.metadata.candidate.order
    );
    let mut f2_chart = ChartBuilder::on(&panels[0])
        .caption(top_caption, ("sans-serif", 24).into_font())
        .margin(15)
        .x_label_area_size(50)
        .y_label_area_size(80)
        .build_cartesian_2d(x_min..x_max, f2_min..f2_max)
        .map_err(|error| plot_error(path, error))?;
    f2_chart
        .configure_mesh()
        .x_desc("Bjorken x (log scale)")
        .y_desc("F₂ (dimensionless)")
        .x_label_formatter(&|log_x| format!("{:.0e}", 10.0_f64.powf(*log_x)))
        .draw()
        .map_err(|error| plot_error(path, error))?;

    for (index, q2) in VALIDATION_Q2_VALUES_GEV2.iter().copied().enumerate() {
        let color = Palette99::pick(index).mix(0.9);
        let lo_points = rows_at_q2(&report.rows, q2).map(|row| (row.x.log10(), row.lo_f2));
        f2_chart
            .draw_series(LineSeries::new(lo_points, color.stroke_width(2)))
            .map_err(|error| plot_error(path, error))?
            .label(format!("Q² = {q2:.0} GeV²"))
            .legend(move |(x, y)| {
                PathElement::new(vec![(x, y), (x + 24, y)], color.stroke_width(2))
            });

        let marker_color = Palette99::pick(index).mix(0.9);
        f2_chart
            .draw_series(
                rows_at_q2(&report.rows, q2).map(|row| {
                    Circle::new((row.x.log10(), row.apfel_f2), 4, marker_color.filled())
                }),
            )
            .map_err(|error| plot_error(path, error))?;
    }
    f2_chart
        .configure_series_labels()
        .background_style(WHITE.mix(0.85))
        .border_style(BLACK)
        .draw()
        .map_err(|error| plot_error(path, error))?;

    let relative_caption = format!(
        "F₂ relative difference: {} — μF/Q = {}, μR/Q = {}",
        report.metadata.f2_difference.relative,
        report.metadata.candidate.mu_f_over_q,
        report.metadata.candidate.mu_r_over_q
    );
    let mut difference_chart = ChartBuilder::on(&panels[1])
        .caption(relative_caption, ("sans-serif", 22).into_font())
        .margin(15)
        .x_label_area_size(50)
        .y_label_area_size(80)
        .build_cartesian_2d(x_min..x_max, relative_min..relative_max)
        .map_err(|error| plot_error(path, error))?;
    difference_chart
        .configure_mesh()
        .x_desc("Bjorken x (log scale)")
        .y_desc("|F₂(APFEL)-F₂(LO)| / |F₂(LO)|")
        .x_label_formatter(&|log_x| format!("{:.0e}", 10.0_f64.powf(*log_x)))
        .draw()
        .map_err(|error| plot_error(path, error))?;

    for (index, q2) in VALIDATION_Q2_VALUES_GEV2.iter().copied().enumerate() {
        let color = Palette99::pick(index).mix(0.9);
        let points = rows_at_q2(&report.rows, q2).filter_map(|row| {
            row.f2_relative_difference
                .map(|value| (row.x.log10(), value))
        });
        difference_chart
            .draw_series(LineSeries::new(points, color.stroke_width(2)))
            .map_err(|error| plot_error(path, error))?;
        let marker_color = Palette99::pick(index).mix(0.9);
        difference_chart
            .draw_series(rows_at_q2(&report.rows, q2).filter_map(|row| {
                row.f2_relative_difference
                    .map(|value| Circle::new((row.x.log10(), value), 3, marker_color.filled()))
            }))
            .map_err(|error| plot_error(path, error))?;
    }

    let undefined_count = report
        .rows
        .iter()
        .filter(|row| row.f2_relative_difference.is_none())
        .count();
    if undefined_count > 0 {
        let x = x_min + 0.04 * (x_max - x_min);
        let y = relative_max - 0.08 * (relative_max - relative_min);
        difference_chart
            .draw_series(std::iter::once(Text::new(
                format!("{undefined_count} undefined relative value(s): LO F₂ = 0"),
                (x, y),
                ("sans-serif", 16).into_font().color(&BLACK),
            )))
            .map_err(|error| plot_error(path, error))?;
    }

    drawing_area
        .present()
        .map_err(|error| plot_error(path, error))
}

fn rows_at_q2(
    rows: &[StructureFunctionValidationRow],
    q2: f64,
) -> impl Iterator<Item = &StructureFunctionValidationRow> {
    rows.iter().filter(move |row| row.q2 == q2)
}

fn value_range(
    values: impl Iterator<Item = f64>,
    default_minimum: f64,
    default_maximum: f64,
) -> (f64, f64) {
    let mut minimum = f64::INFINITY;
    let mut maximum = f64::NEG_INFINITY;
    for value in values {
        minimum = minimum.min(value);
        maximum = maximum.max(value);
    }
    if !minimum.is_finite() || !maximum.is_finite() {
        return (default_minimum, default_maximum);
    }
    let span = maximum - minimum;
    let padding = if span > 0.0 {
        span * 0.08
    } else {
        maximum.abs().max(1.0) * 0.08
    };
    (minimum - padding, maximum + padding)
}

fn create_new_file(path: &Path, operation: &'static str) -> Result<File, ValidationArtifactError> {
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|source| {
            if source.kind() == io::ErrorKind::AlreadyExists {
                ValidationArtifactError::ArtifactExists {
                    path: path.to_owned(),
                }
            } else {
                ValidationArtifactError::Io {
                    operation,
                    path: path.to_owned(),
                    source,
                }
            }
        })
}

fn persist_without_overwrite(
    temporary: &Path,
    final_path: &Path,
) -> Result<(), ValidationArtifactError> {
    let mut source = File::open(temporary).map_err(|source| ValidationArtifactError::Io {
        operation: "opening completed temporary artifact",
        path: temporary.to_owned(),
        source,
    })?;
    let mut destination = create_new_file(final_path, "creating final validation artifact")?;

    if let Err(source) = io::copy(&mut source, &mut destination)
        .and_then(|_| destination.flush())
        .and_then(|()| destination.sync_all())
    {
        drop(destination);
        let _ = fs::remove_file(final_path);
        return Err(ValidationArtifactError::Io {
            operation: "persisting validation artifact",
            path: final_path.to_owned(),
            source,
        });
    }

    fs::remove_file(temporary).map_err(|source| ValidationArtifactError::Io {
        operation: "removing persisted temporary artifact",
        path: temporary.to_owned(),
        source,
    })
}

fn plot_error(path: &Path, error: impl fmt::Display) -> ValidationArtifactError {
    ValidationArtifactError::Plot {
        path: path.to_owned(),
        message: error.to_string(),
    }
}

#[derive(Default)]
struct TemporaryFiles {
    paths: Vec<PathBuf>,
}

impl TemporaryFiles {
    fn track(&mut self, path: PathBuf) {
        self.paths.push(path);
    }

    fn untrack(&mut self, path: &Path) {
        self.paths.retain(|candidate| candidate != path);
    }
}

impl Drop for TemporaryFiles {
    fn drop(&mut self) {
        for path in &self.paths {
            if path.is_file() {
                let _ = fs::remove_file(path);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Read;
    use std::time::{SystemTime, UNIX_EPOCH};

    use crate::physics::structure_function_validation::{
        compare_structure_function_grid, StructureFunctionValidationConfig,
        StructureFunctionValidationReport, VALIDATION_X_VALUES,
    };
    use crate::physics::{
        PerturbativeOrder, StructureFunctionBackend, StructureFunctionMetadata,
        StructureFunctionProvider, StructureFunctionProviderError, StructureFunctionRequest,
        StructureFunctionResult,
    };

    struct MockProvider {
        backend: StructureFunctionBackend,
        zero_first: bool,
    }

    impl StructureFunctionProvider for MockProvider {
        fn evaluate(
            &self,
            request: &StructureFunctionRequest,
        ) -> Result<StructureFunctionResult, StructureFunctionProviderError> {
            let first =
                request.x == VALIDATION_X_VALUES[0] && request.q2 == VALIDATION_Q2_VALUES_GEV2[0];
            let f2 = match self.backend {
                StructureFunctionBackend::LoPdf if self.zero_first && first => 0.0,
                StructureFunctionBackend::LoPdf => 2.0,
                StructureFunctionBackend::Apfel => 2.5,
                StructureFunctionBackend::Surrogate => 2.5,
            };
            Ok(StructureFunctionResult {
                f2,
                fl: if self.backend == StructureFunctionBackend::Apfel {
                    0.1
                } else {
                    0.0
                },
                xf3: 0.0,
                metadata: StructureFunctionMetadata {
                    backend: self.backend,
                    apfelxx_version: (self.backend == StructureFunctionBackend::Apfel)
                        .then(|| "4.8.0".to_owned()),
                    lhapdf_version: (self.backend == StructureFunctionBackend::Apfel)
                        .then(|| "6.5.6".to_owned()),
                    pdf_set: request.pdf_set.clone(),
                    pdf_member: request.pdf_member,
                    pdf_order_qcd: 1,
                    pdf_data_version: 1,
                    order: request.order,
                    process: request.process,
                    projectile: request.projectile,
                    target: request.target,
                    mu_f_over_q: request.mu_f_over_q,
                    mu_r_over_q: request.mu_r_over_q,
                    scheme: match self.backend {
                        StructureFunctionBackend::LoPdf => "lo_parton_model",
                        StructureFunctionBackend::Apfel => "ZM-VFNS",
                        StructureFunctionBackend::Surrogate => "surrogate",
                    }
                    .to_owned(),
                    electromagnetic_mode: "photon_exchange".to_owned(),
                    os_arch: None,
                    rust_version: None,
                    git_commit: None,
                    git_dirty: None,
                    pythia_version: None,
                    hepmc_version: None,
                    python_env_hash: None,
                },
            })
        }
    }

    struct TestDirectory(PathBuf);

    impl TestDirectory {
        fn new() -> Self {
            let nonce = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .expect("clock should be after the Unix epoch")
                .as_nanos();
            let path = std::env::temp_dir().join(format!(
                "quark_sim_validation_artifacts_{}_{}",
                std::process::id(),
                nonce
            ));
            fs::create_dir(&path).expect("unique test directory should be created");
            Self(path)
        }
    }

    impl Drop for TestDirectory {
        fn drop(&mut self) {
            if self
                .0
                .file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.starts_with("quark_sim_validation_artifacts_"))
            {
                let _ = fs::remove_dir_all(&self.0);
            }
        }
    }

    fn report(zero_first: bool) -> StructureFunctionValidationReport {
        let lo = MockProvider {
            backend: StructureFunctionBackend::LoPdf,
            zero_first,
        };
        let apfel = MockProvider {
            backend: StructureFunctionBackend::Apfel,
            zero_first: false,
        };
        compare_structure_function_grid(
            &lo,
            &apfel,
            &StructureFunctionValidationConfig::new("CT18NLO", 0, PerturbativeOrder::Nlo),
        )
        .unwrap()
    }

    #[test]
    fn writes_exact_artifact_names_into_an_existing_directory() {
        let directory = TestDirectory::new();
        let report = report(false);

        let paths = write_validation_artifacts(&directory.0, &report).unwrap();

        assert_eq!(paths.csv, directory.0.join(VALIDATION_CSV_FILENAME));
        assert_eq!(paths.json, directory.0.join(VALIDATION_JSON_FILENAME));
        assert_eq!(paths.svg, directory.0.join(VALIDATION_SVG_FILENAME));
        for path in paths.as_array() {
            assert!(path.is_file());
            assert!(fs::metadata(path).unwrap().len() > 0);
        }
    }

    #[test]
    fn csv_and_json_preserve_twenty_rows_and_undefined_relative_values() {
        let directory = TestDirectory::new();
        let expected = report(true);
        let paths = write_validation_artifacts(&directory.0, &expected).unwrap();

        let decoded: StructureFunctionValidationReport =
            serde_json::from_reader(File::open(&paths.json).unwrap()).unwrap();
        assert_eq!(decoded, expected);
        assert_eq!(decoded.rows.len(), 20);
        assert_eq!(decoded.rows[0].f2_relative_difference, None);

        let mut reader = csv::Reader::from_path(&paths.csv).unwrap();
        let csv_rows: Vec<StructureFunctionValidationRow> =
            reader.deserialize().collect::<Result<_, _>>().unwrap();
        assert_eq!(csv_rows, expected.rows);
        let csv_text = fs::read_to_string(paths.csv).unwrap();
        assert_eq!(csv_text.lines().count(), 21);
    }

    #[test]
    fn svg_contains_comparison_and_difference_labels() {
        let directory = TestDirectory::new();
        let paths = write_validation_artifacts(&directory.0, &report(false)).unwrap();
        let svg = fs::read_to_string(paths.svg).unwrap();

        assert!(svg.contains("<svg"));
        assert!(svg.contains("APFEL"));
        assert!(svg.contains("relative difference"));
        assert!(svg.contains("CT18NLO"));
    }

    #[test]
    fn never_overwrites_an_existing_artifact() {
        let directory = TestDirectory::new();
        let report = report(false);
        let paths = write_validation_artifacts(&directory.0, &report).unwrap();
        let original_json = fs::read(&paths.json).unwrap();

        let error = write_validation_artifacts(&directory.0, &report).unwrap_err();

        assert!(matches!(
            error,
            ValidationArtifactError::ArtifactExists { .. }
        ));
        assert_eq!(fs::read(paths.json).unwrap(), original_json);
    }

    #[test]
    fn a_preexisting_target_prevents_the_entire_write_set() {
        let directory = TestDirectory::new();
        let paths = ValidationArtifactPaths::in_directory(&directory.0);
        fs::write(&paths.csv, b"sentinel").unwrap();

        let error = write_validation_artifacts(&directory.0, &report(false)).unwrap_err();

        assert!(matches!(
            error,
            ValidationArtifactError::ArtifactExists { ref path } if path == &paths.csv
        ));
        assert_eq!(fs::read(&paths.csv).unwrap(), b"sentinel");
        assert!(!paths.json.exists());
        assert!(!paths.svg.exists());
    }

    #[test]
    fn rejects_a_tampered_report_before_creating_outputs() {
        let parent = TestDirectory::new();
        let output = parent.0.join("new-output");
        let mut report = report(false);
        report.rows[0].f2_absolute_difference = 99.0;

        let error = write_validation_artifacts(&output, &report).unwrap_err();

        assert!(matches!(error, ValidationArtifactError::InvalidReport(_)));
        assert!(!output.exists());
    }

    #[test]
    fn empty_and_file_output_paths_are_rejected() {
        assert!(matches!(
            write_validation_artifacts(Path::new(""), &report(false)),
            Err(ValidationArtifactError::EmptyOutputPath)
        ));

        let directory = TestDirectory::new();
        let file = directory.0.join("not-a-directory");
        fs::write(&file, b"x").unwrap();
        assert!(matches!(
            write_validation_artifacts(&file, &report(false)),
            Err(ValidationArtifactError::OutputIsNotDirectory { .. })
        ));
    }

    #[test]
    fn persisted_files_are_complete_readable_documents() {
        let directory = TestDirectory::new();
        let paths = write_validation_artifacts(&directory.0, &report(false)).unwrap();

        let mut bytes = Vec::new();
        File::open(paths.json)
            .unwrap()
            .read_to_end(&mut bytes)
            .unwrap();
        assert_eq!(bytes.last(), Some(&b'\n'));
    }
}
