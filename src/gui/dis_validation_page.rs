//! Data validation page.
//!
//! Displays HERA validation results including dataset metadata, theory settings,
//! data/theory comparison, uncertainty bands, ratio, residual, pull, and χ²/NDF.

use eframe::egui;
use std::fs;
use std::path::Path;

use egui_plot::{BarChart, Bar, Legend, Plot, Points, PlotPoints};

use super::state::{ComparisonPoint, GuiError, GuiErrorCategory, ValidationSummary};

#[derive(PartialEq, Clone, Copy)]
pub enum ValidationView {
    Visualized,
    Raw,
    Plot,
}

/// State for the data validation page.
pub struct ValidationPageState {
    pub output_dir: String,
    pub summary: Option<ValidationSummary>,
    pub comparison_points: Vec<ComparisonPoint>,
    pub loaded: bool,
    pub dataset_name: String,
    pub show_uncertainties: bool,
    pub sort_by_q2: bool,
    pub view_mode: ValidationView,
}

impl Default for ValidationPageState {
    fn default() -> Self {
        Self {
            output_dir: "outputs/uncertainties/HERA1+2_NCep_920".to_string(),
            summary: None,
            comparison_points: Vec::new(),
            loaded: false,
            dataset_name: String::new(),
            show_uncertainties: true,
            sort_by_q2: true,
            view_mode: ValidationView::Visualized,
        }
    }
}

/// Render the data validation page.
pub fn render_validation_page(
    state: &mut ValidationPageState,
    errors: &mut Vec<GuiError>,
    ui: &mut egui::Ui,
) {
    ui.heading("✅ Data Validation (HERA)");
    ui.separator();

    // Directory selection
    ui.horizontal(|ui| {
        ui.label("Validation output directory:");
        ui.text_edit_singleline(&mut state.output_dir);
        if ui.button("📂 Load Results").clicked() {
            load_validation_results(state, errors);
        }
    });

    if !state.loaded {
        ui.label("No validation results loaded. Run the validation pipeline first, then load results here.");
        return;
    }

    // Summary
    if let Some(ref summary) = state.summary {
        ui.separator();
        ui.heading("📊 Summary");
        ui.group(|ui| {
            egui::Grid::new("validation_summary_grid")
                .num_columns(2)
                .spacing([20.0, 6.0])
                .striped(true)
                .show(ui, |ui| {
                    ui.label("Dataset:");
                    ui.label(&summary.dataset);
                    ui.end_row();

                    ui.label("Backend:");
                    ui.label(&summary.backend);
                    ui.end_row();

                    ui.label("Order:");
                    ui.label(&summary.order);
                    ui.end_row();

                    ui.label("PDF Set:");
                    ui.label(&summary.pdf_set);
                    ui.end_row();

                    ui.separator();
                    ui.separator();
                    ui.end_row();

                    ui.label("Number of points:");
                    ui.label(format!("{}", summary.n_points));
                    ui.end_row();

                    ui.strong("χ²:");
                    ui.strong(format!("{:.2}", summary.chi2));
                    ui.end_row();

                    ui.strong("NDF:");
                    ui.strong(format!("{}", summary.ndf));
                    ui.end_row();

                    ui.strong("χ² / NDF:");
                    let chi2_color = if summary.chi2_ndf < 2.0 {
                        egui::Color32::GREEN
                    } else if summary.chi2_ndf < 3.0 {
                        egui::Color32::YELLOW
                    } else {
                        egui::Color32::RED
                    };
                    ui.colored_label(chi2_color, format!("{:.4}", summary.chi2_ndf));
                    ui.end_row();

                    ui.label("Mean Data/Theory ratio:");
                    ui.label(format!("{:.4}", summary.mean_ratio));
                    ui.end_row();

                    ui.label("Max |pull|:");
                    ui.label(format!("{:.2}", summary.max_pull));
                    ui.end_row();
                });
        });
    }

    // Controls
    ui.separator();
    ui.horizontal(|ui| {
        ui.checkbox(&mut state.show_uncertainties, "Show uncertainty bands");
        ui.checkbox(&mut state.sort_by_q2, "Sort by Q²");
    });

    // Comparison table
    if !state.comparison_points.is_empty() {
        ui.separator();
        ui.horizontal(|ui| {
            ui.heading("Data vs Theory");
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.selectable_value(&mut state.view_mode, ValidationView::Plot, "📈 Plot");
                ui.selectable_value(&mut state.view_mode, ValidationView::Raw, "📄 Raw JSON");
                ui.selectable_value(&mut state.view_mode, ValidationView::Visualized, "📊 Visualized Table");
            });
        });

        match state.view_mode {
            ValidationView::Visualized => {
                let mut points = state.comparison_points.clone();
        if state.sort_by_q2 {
            points.sort_by(|a, b| a.q2.partial_cmp(&b.q2).unwrap_or(std::cmp::Ordering::Equal));
        }

        egui::ScrollArea::vertical()
            .max_height(400.0)
            .show(ui, |ui| {
                egui::Grid::new("comparison_grid")
                    .num_columns(if state.show_uncertainties { 12 } else { 8 })
                    .striped(true)
                    .show(ui, |ui| {
                        // Header
                        ui.strong("Q² [GeV²]");
                        ui.strong("x");
                        ui.strong("y");
                        ui.strong("Data");
                        ui.strong("Theory");
                        ui.strong("Ratio");
                        ui.strong("Residual");
                        ui.strong("Pull");
                        if state.show_uncertainties {
                            ui.strong("PDF +");
                            ui.strong("PDF -");
                            ui.strong("Scale +");
                            ui.strong("Scale -");
                        }
                        ui.end_row();

                        let display_count = points.len().min(200);
                        for point in points.iter().take(display_count) {
                            ui.label(format!("{:.1}", point.q2));
                            ui.label(format!("{:.4e}", point.x));
                            ui.label(format!("{:.4}", point.y));
                            ui.label(format!("{:.4}", point.data_value));
                            ui.label(format!("{:.4}", point.theory_central));
                            ui.label(format!("{:.4}", point.ratio));
                            ui.label(format!("{:.4}", point.residual));

                            let pull_color = if point.pull.abs() < 2.0 {
                                egui::Color32::GREEN
                            } else if point.pull.abs() < 3.0 {
                                egui::Color32::YELLOW
                            } else {
                                egui::Color32::RED
                            };
                            ui.colored_label(pull_color, format!("{:.2}", point.pull));

                            if state.show_uncertainties {
                                ui.label(format!("{:.4}", point.pdf_unc_plus));
                                ui.label(format!("{:.4}", point.pdf_unc_minus));
                                ui.label(format!("{:.4}", point.scale_unc_plus));
                                ui.label(format!("{:.4}", point.scale_unc_minus));
                            }
                            ui.end_row();
                        }

                        if points.len() > display_count {
                            ui.label(format!("... and {} more points", points.len() - display_count));
                            ui.end_row();
                        }
                    });
            });
            }
            ValidationView::Raw => {
                egui::ScrollArea::vertical()
                    .max_height(400.0)
                    .show(ui, |ui| {
                        let json = serde_json::to_string_pretty(&state.comparison_points).unwrap_or_else(|_| "Failed to serialize JSON".to_string());
                        ui.add(
                            egui::TextEdit::multiline(&mut json.as_str())
                                .font(egui::TextStyle::Monospace)
                                .desired_width(f32::INFINITY)
                                .interactive(false),
                        );
                    });
            }
            ValidationView::Plot => {
                ui.add_space(8.0);
                
                let mut points_data: Vec<[f64; 2]> = Vec::new();
                for (i, p) in state.comparison_points.iter().enumerate() {
                    // Use index for X-axis if not sorting by Q2, otherwise use Q2
                    let x_val = if state.sort_by_q2 { p.q2 } else { i as f64 };
                    points_data.push([x_val, p.pull]);
                }
                
                let scatter = Points::new(PlotPoints::new(points_data))
                    .name("Pull (σ)")
                    .radius(4.0)
                    .color(egui::Color32::from_rgb(100, 150, 255));
                
                Plot::new("validation_pull_plot")
                    .view_aspect(2.5)
                    .legend(Legend::default())
                    .x_axis_formatter(move |mark, _max_chars, _range| {
                        format!("{:.1}", mark.value)
                    })
                    .y_axis_formatter(|mark, _max_chars, _range| format!("{:.1} σ", mark.value))
                    .label_formatter(move |name, value| {
                        format!("{}: y={:.2} σ, x={:.1}", name, value.y, value.x)
                    })
                    .show(ui, |plot_ui| {
                        plot_ui.hline(egui_plot::HLine::new(0.0).color(egui::Color32::GRAY));
                        plot_ui.hline(egui_plot::HLine::new(1.0).color(egui::Color32::DARK_GREEN).style(egui_plot::LineStyle::Dashed { length: 5.0 }));
                        plot_ui.hline(egui_plot::HLine::new(-1.0).color(egui::Color32::DARK_GREEN).style(egui_plot::LineStyle::Dashed { length: 5.0 }));
                        plot_ui.hline(egui_plot::HLine::new(3.0).color(egui::Color32::RED).style(egui_plot::LineStyle::Dashed { length: 5.0 }));
                        plot_ui.hline(egui_plot::HLine::new(-3.0).color(egui::Color32::RED).style(egui_plot::LineStyle::Dashed { length: 5.0 }));
                        plot_ui.points(scatter);
                    });
            }
        }
    }
}

/// Load validation results from a directory.
fn load_validation_results(state: &mut ValidationPageState, errors: &mut Vec<GuiError>) {
    let dir = Path::new(&state.output_dir);
    if !dir.is_dir() {
        errors.push(GuiError::new(
            GuiErrorCategory::FileNotFound,
            format!("Directory not found: {}", state.output_dir),
        ));
        state.loaded = false;
        return;
    }

    // Load summary.json
    let summary_path = dir.join("summary.json");
    if summary_path.exists() {
        match fs::read_to_string(&summary_path) {
            Ok(json) => {
                match serde_json::from_str::<serde_json::Value>(&json) {
                    Ok(val) => {
                        state.summary = Some(ValidationSummary {
                            dataset: val
                                .get("dataset")
                                .and_then(|v| v.as_str())
                                .unwrap_or("unknown")
                                .to_string(),
                            backend: val
                                .get("backend")
                                .and_then(|v| v.as_str())
                                .unwrap_or("unknown")
                                .to_string(),
                            order: val
                                .get("order")
                                .and_then(|v| v.as_str())
                                .unwrap_or("unknown")
                                .to_string(),
                            pdf_set: val
                                .get("pdf_set")
                                .and_then(|v| v.as_str())
                                .unwrap_or("unknown")
                                .to_string(),
                            n_points: val
                                .get("n_points")
                                .and_then(|v| v.as_u64())
                                .unwrap_or(0) as usize,
                            chi2: val
                                .get("chi2")
                                .or_else(|| val.get("chi2_full_cov"))
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.0),
                            ndf: val
                                .get("ndf")
                                .and_then(|v| v.as_u64())
                                .unwrap_or(0) as usize,
                            chi2_ndf: val
                                .get("chi2_ndf")
                                .or_else(|| val.get("chi2_per_ndf"))
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.0),
                            mean_ratio: val
                                .get("mean_ratio")
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.0),
                            max_pull: val
                                .get("max_pull")
                                .or_else(|| val.get("max_abs_pull"))
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.0),
                        });
                    }
                    Err(e) => {
                        errors.push(GuiError::new(
                            GuiErrorCategory::ParseError,
                            format!("Failed to parse summary.json: {e}"),
                        ));
                    }
                }
            }
            Err(e) => {
                errors.push(GuiError::new(
                    GuiErrorCategory::FileNotFound,
                    format!("Failed to read summary.json: {e}"),
                ));
            }
        }
    }

    // Load comparison.json
    let comparison_path = dir.join("comparison.json");
    if comparison_path.exists() {
        match fs::read_to_string(&comparison_path) {
            Ok(json) => match serde_json::from_str::<Vec<serde_json::Value>>(&json) {
                Ok(arr) => {
                    state.comparison_points.clear();
                    for val in arr {
                        let point = ComparisonPoint {
                            q2: val.get("Q2").and_then(|v| v.as_f64()).unwrap_or(0.0),
                            x: val.get("x").and_then(|v| v.as_f64()).unwrap_or(0.0),
                            y: val.get("y").and_then(|v| v.as_f64()).unwrap_or(0.0),
                            data_value: val
                                .get("Sigma")
                                .or_else(|| val.get("data"))
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.0),
                            data_stat_error: val
                                .get("stat")
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.0),
                            theory_central: val
                                .get("theory_central")
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.0),
                            pdf_unc_plus: val
                                .get("pdf_uncertainty_plus")
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.0),
                            pdf_unc_minus: val
                                .get("pdf_uncertainty_minus")
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.0),
                            scale_unc_plus: val
                                .get("scale_uncertainty_plus")
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.0),
                            scale_unc_minus: val
                                .get("scale_uncertainty_minus")
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.0),
                            ratio: if val
                                .get("theory_central")
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.0)
                                != 0.0
                            {
                                val.get("Sigma")
                                    .or_else(|| val.get("data"))
                                    .and_then(|v| v.as_f64())
                                    .unwrap_or(0.0)
                                    / val
                                        .get("theory_central")
                                        .and_then(|v| v.as_f64())
                                        .unwrap_or(1.0)
                            } else {
                                0.0
                            },
                            residual: val
                                .get("Sigma")
                                .or_else(|| val.get("data"))
                                .and_then(|v| v.as_f64())
                                .unwrap_or(0.0)
                                - val
                                    .get("theory_central")
                                    .and_then(|v| v.as_f64())
                                    .unwrap_or(0.0),
                            pull: 0.0, // Will be computed below
                        };
                        state.comparison_points.push(point);
                    }
                    // Compute pulls
                    for point in &mut state.comparison_points {
                        let total_unc = (point.data_stat_error.powi(2)
                            + point.pdf_unc_plus.powi(2)
                            + point.scale_unc_plus.powi(2))
                        .sqrt();
                        if total_unc > 0.0 {
                            point.pull = point.residual / total_unc;
                        }
                    }
                }
                Err(e) => {
                    errors.push(GuiError::new(
                        GuiErrorCategory::ParseError,
                        format!("Failed to parse comparison.json: {e}"),
                    ));
                }
            },
            Err(e) => {
                errors.push(GuiError::new(
                    GuiErrorCategory::FileNotFound,
                    format!("Failed to read comparison.json: {e}"),
                ));
            }
        }
    }

    state.loaded = true;
}
