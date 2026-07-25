//! Inclusive DIS calculation page.
//!
//! Displays x, Q², y, W², parton densities, F₂, F_L, xF₃,
//! differential cross section, units, and backend metadata.

use eframe::egui;
use std::sync::atomic::AtomicBool;
use std::sync::Arc;

use egui_plot::{Bar, BarChart, Legend, Plot};

use super::state::{
    BackendProcess, DisConfig, GuiError, GuiErrorCategory, InclusiveResult, ProcessStatus,
};
use super::worker::{self, WorkerHandle, WorkerMessage};

#[derive(PartialEq, Clone, Copy)]
pub enum InclusiveView {
    Visualized,
    Raw,
    Plot,
}

/// State for the inclusive calculation page.
pub struct InclusivePageState {
    pub calc_x: String,
    pub calc_q2: String,
    pub result: Option<InclusiveResult>,
    pub process: BackendProcess,
    pub worker: Option<WorkerHandle>,
    pub view_mode: InclusiveView,
}

impl Default for InclusivePageState {
    fn default() -> Self {
        Self {
            calc_x: "0.01".to_string(),
            calc_q2: "100.0".to_string(),
            result: None,
            process: BackendProcess::default(),
            worker: None,
            view_mode: InclusiveView::Visualized,
        }
    }
}

/// Render the inclusive calculation page.
pub fn render_inclusive_page(
    state: &mut InclusivePageState,
    config: &DisConfig,
    errors: &mut Vec<GuiError>,
    ui: &mut egui::Ui,
    ctx: &egui::Context,
) {
    ui.heading("📊 Inclusive DIS Calculation");
    ui.separator();

    // Poll worker for updates
    if let Some(ref handle) = state.worker {
        for msg in handle.drain() {
            match msg {
                WorkerMessage::StdoutLine(line) => {
                    state.process.stdout_lines.push(line);
                }
                WorkerMessage::StderrLine(line) => {
                    state.process.stderr_lines.push(line);
                }
                WorkerMessage::Progress(text) => {
                    state.process.progress_text = text;
                }
                WorkerMessage::Completed(code) => {
                    state.process.exit_code = Some(code);
                    state.process.status = ProcessStatus::Completed;
                    // Parse the result from stdout
                    parse_inclusive_result(state);
                }
                WorkerMessage::Failed(msg) => {
                    state.process.status = ProcessStatus::Failed;
                    errors.push(GuiError::new(
                        GuiErrorCategory::ProcessFailed,
                        msg,
                    ));
                }
            }
        }
        if state.process.status == ProcessStatus::Running {
            ctx.request_repaint();
        }
    }

    // Input fields
    egui::Grid::new("inclusive_input_grid")
        .num_columns(2)
        .spacing([20.0, 8.0])
        .show(ui, |ui| {
            ui.label("Bjorken x:");
            ui.text_edit_singleline(&mut state.calc_x);
            ui.end_row();

            ui.label("Q² [GeV²]:");
            ui.text_edit_singleline(&mut state.calc_q2);
            ui.end_row();
        });

    ui.separator();

    let is_running = state.process.status == ProcessStatus::Running;

    ui.horizontal(|ui| {
        if ui
            .add_enabled(!is_running, egui::Button::new("🔬 Calculate"))
            .clicked()
        {
            start_inclusive_calculation(state, config, errors);
        }
        if ui
            .add_enabled(is_running, egui::Button::new("⏹ Cancel"))
            .clicked()
        {
            if let Some(ref handle) = state.worker {
                handle.cancel();
            }
        }
    });

    // Status
    match state.process.status {
        ProcessStatus::Running => {
            ui.spinner();
            ui.label(&state.process.progress_text);
        }
        ProcessStatus::Failed => {
            ui.colored_label(egui::Color32::RED, "⚠ Calculation failed");
            if let Some(code) = state.process.exit_code {
                ui.label(format!("Exit code: {code}"));
            }
        }
        _ => {}
    }

    // Display results
    if let Some(ref result) = state.result {
        ui.separator();
        ui.horizontal(|ui| {
            ui.heading("Results");
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.selectable_value(&mut state.view_mode, InclusiveView::Plot, "📈 Plot");
                ui.selectable_value(&mut state.view_mode, InclusiveView::Raw, "📄 Raw JSON");
                ui.selectable_value(&mut state.view_mode, InclusiveView::Visualized, "📊 Visualized");
            });
        });

        match state.view_mode {
            InclusiveView::Visualized => {
                egui::Grid::new("inclusive_result_grid")
            .num_columns(2)
            .spacing([20.0, 6.0])
            .striped(true)
            .show(ui, |ui| {
                ui.label("x:");
                ui.label(format!("{:.6e}", result.x));
                ui.end_row();

                ui.label("Q² [GeV²]:");
                ui.label(format!("{:.4}", result.q2_gev2));
                ui.end_row();

                ui.label("y:");
                ui.label(format!("{:.6}", result.y));
                ui.end_row();

                ui.label("W² [GeV²]:");
                ui.label(format!("{:.4}", result.w2_gev2));
                ui.end_row();

                ui.separator();
                ui.separator();
                ui.end_row();

                ui.label("F₂:");
                ui.label(format!("{:.6e}", result.f2));
                ui.end_row();

                ui.label("F_L:");
                ui.label(format!("{:.6e}", result.fl));
                ui.end_row();

                ui.label("xF₃:");
                ui.label(format!("{:.6e}", result.xf3));
                ui.end_row();

                ui.separator();
                ui.separator();
                ui.end_row();

                ui.label("d²σ/(dx dQ²) [GeV⁻⁴]:");
                ui.label(format!("{:.6e}", result.dsigma_dxdq2_gev_m4));
                ui.end_row();

                ui.label("d²σ/(dx dQ²) [pb/GeV²]:");
                ui.label(format!("{:.6e}", result.dsigma_dxdq2_pb_gev2));
                ui.end_row();

                ui.separator();
                ui.separator();
                ui.end_row();

                ui.label("Backend:");
                ui.label(&result.backend_name);
                ui.end_row();

                ui.label("Order:");
                ui.label(&result.order);
                ui.end_row();

                ui.label("PDF Set:");
                ui.label(format!("{} (member {})", result.pdf_set, result.pdf_member));
                ui.end_row();

                ui.label("Scheme:");
                ui.label(&result.scheme);
                ui.end_row();
            });

        // Parton densities
        if !result.parton_densities.is_empty() {
            ui.separator();
            ui.collapsing("🧬 Parton Densities x·f(x, Q²)", |ui| {
                egui::Grid::new("parton_density_grid")
                    .num_columns(2)
                    .striped(true)
                    .show(ui, |ui| {
                        ui.strong("PDG ID");
                        ui.strong("x·f(x, Q²)");
                        ui.end_row();

                        for (pdg_id, xf) in &result.parton_densities {
                            let name = pdg_id_name(*pdg_id);
                            ui.label(format!("{name} ({pdg_id})"));
                            ui.label(format!("{xf:.6e}"));
                            ui.end_row();
                        }
                    });
            });
        }
            } // end Visualized
            InclusiveView::Raw => {
                egui::ScrollArea::vertical()
                    .max_height(400.0)
                    .show(ui, |ui| {
                        let json = serde_json::to_string_pretty(&result).unwrap_or_else(|_| "Failed to serialize JSON".to_string());
                        ui.add(
                            egui::TextEdit::multiline(&mut json.as_str())
                                .font(egui::TextStyle::Monospace)
                                .desired_width(f32::INFINITY)
                                .interactive(false),
                        );
                    });
            }
            InclusiveView::Plot => {
                ui.add_space(8.0);
                
                let mut bars = Vec::new();
                let is_partons = !result.parton_densities.is_empty();
                
                if is_partons {
                    let pdg_ids: Vec<i32> = result.parton_densities.iter().map(|(id, _)| *id).collect();
                    
                    let parton_name = |pdg_id: i32| -> &'static str {
                        match pdg_id {
                            0 | 21 => "g",
                            1 => "d",
                            2 => "u",
                            3 => "s",
                            4 => "c",
                            5 => "b",
                            6 => "t",
                            -1 => "d̄",
                            -2 => "ū",
                            -3 => "s̄",
                            -4 => "c̄",
                            -5 => "b̄",
                            -6 => "t̄",
                            _ => "?",
                        }
                    };

                    for (i, (pdg_id, xf)) in result.parton_densities.iter().enumerate() {
                        bars.push(
                            Bar::new(i as f64, *xf)
                                .name(parton_name(*pdg_id))
                        );
                    }
                    
                    let chart = BarChart::new(bars)
                        .name("x·f(x, Q²)")
                        .color(egui::Color32::from_rgb(100, 200, 150));
                    
                    Plot::new("inclusive_parton_plot")
                        .view_aspect(2.5)
                        .legend(Legend::default())
                        .y_axis_formatter(|mark, _max_chars, _range| format!("{:.1e}", mark.value))
                        .x_axis_formatter(move |mark, _max_chars, _range| {
                            let idx = mark.value.round() as usize;
                            if idx < pdg_ids.len() {
                                parton_name(pdg_ids[idx]).to_string()
                            } else {
                                String::new()
                            }
                        })
                        .show(ui, |plot_ui| {
                            plot_ui.bar_chart(chart);
                        });
                } else {
                    // If no parton densities, plot F2, FL, xF3
                    bars.push(Bar::new(0.0, result.f2).name("F₂"));
                    bars.push(Bar::new(1.0, result.fl).name("F_L"));
                    bars.push(Bar::new(2.0, result.xf3).name("xF₃"));
                    
                    let chart = BarChart::new(bars)
                        .name("Structure Functions")
                        .color(egui::Color32::from_rgb(100, 150, 250));
                        
                    let names = vec!["F₂", "F_L", "xF₃"];
                    Plot::new("inclusive_sf_plot")
                        .view_aspect(2.5)
                        .legend(Legend::default())
                        .y_axis_formatter(|mark, _max_chars, _range| format!("{:.1e}", mark.value))
                        .x_axis_formatter(move |mark, _max_chars, _range| {
                            let idx = mark.value.round() as usize;
                            if idx < names.len() {
                                names[idx].to_string()
                            } else {
                                String::new()
                            }
                        })
                        .show(ui, |plot_ui| {
                            plot_ui.bar_chart(chart);
                        });
                }
            }
        }
    }

    // Logs
    if !state.process.stdout_lines.is_empty() || !state.process.stderr_lines.is_empty() {
        ui.separator();
        ui.collapsing("📋 Process Output", |ui| {
            egui::ScrollArea::vertical()
                .max_height(200.0)
                .show(ui, |ui| {
                    for line in &state.process.stdout_lines {
                        ui.label(line);
                    }
                    for line in &state.process.stderr_lines {
                        ui.colored_label(egui::Color32::YELLOW, line);
                    }
                });
        });
    }
}

fn start_inclusive_calculation(
    state: &mut InclusivePageState,
    config: &DisConfig,
    errors: &mut Vec<GuiError>,
) {
    let x: f64 = match state.calc_x.parse() {
        Ok(v) if v > 0.0 && v < 1.0 => v,
        _ => {
            errors.push(GuiError::new(
                GuiErrorCategory::InvalidKinematics,
                "Bjorken x must be in (0, 1)",
            ));
            return;
        }
    };
    let q2: f64 = match state.calc_q2.parse() {
        Ok(v) if v > 0.0 => v,
        _ => {
            errors.push(GuiError::new(
                GuiErrorCategory::InvalidKinematics,
                "Q² must be positive",
            ));
            return;
        }
    };

    state.process.reset();
    state.process.status = ProcessStatus::Running;
    state.result = None;

    let args = super::state::build_structure_function_command(
        x,
        q2,
        &config.backend,
        &config.perturbative_order,
        &config.pdf_set,
        config.pdf_member,
        config.mu_f_over_q,
        config.mu_r_over_q,
    );

    let cancel_flag = Arc::clone(&state.process.cancel_flag);
    // We run the quark_sim binary itself as a subprocess.
    let exe = std::env::current_exe()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| "quark_sim".to_string());

    state.worker = Some(worker::spawn_subprocess(&exe, &args, cancel_flag));
}

/// Parse inclusive result from the captured stdout lines.
fn parse_inclusive_result(state: &mut InclusivePageState) {
    // The structure-functions command outputs JSON. Try to parse it.
    let combined = state.process.stdout_lines.join("\n");

    if let Some(start) = combined.find('{') {
        if let Some(end) = combined.rfind('}') {
            let json_str = &combined[start..=end];
            if let Ok(value) = serde_json::from_str::<serde_json::Value>(json_str) {
                let x = state.calc_x.parse().unwrap_or(0.0);
                let q2 = state.calc_q2.parse().unwrap_or(0.0);
                let y = if x > 0.0 { q2 / (101200.0 * x) } else { 0.0 };
                let w2 = 101200.0 * y * (1.0 - x) + 0.88; // roughly

                let result = InclusiveResult {
                    x,
                    q2_gev2: q2,
                    y,
                    w2_gev2: w2,
                    f2: value.get("f2").or_else(|| value.get("F2")).and_then(|v| v.as_f64()).unwrap_or(0.0),
                    fl: value.get("fl").or_else(|| value.get("FL")).and_then(|v| v.as_f64()).unwrap_or(0.0),
                    xf3: value.get("xf3").or_else(|| value.get("xF3")).and_then(|v| v.as_f64()).unwrap_or(0.0),
                    dsigma_dxdq2_gev_m4: 0.0,
                    dsigma_dxdq2_pb_gev2: 0.0,
                    parton_densities: vec![],
                    backend_name: value.get("metadata").and_then(|m| m.get("backend")).and_then(|v| v.as_str()).unwrap_or("").to_string(),
                    order: value.get("metadata").and_then(|m| m.get("order")).and_then(|v| v.as_str()).unwrap_or("").to_string(),
                    pdf_set: value.get("metadata").and_then(|m| m.get("pdf_set")).and_then(|v| v.as_str()).unwrap_or("").to_string(),
                    pdf_member: value.get("metadata").and_then(|m| m.get("pdf_member")).and_then(|v| v.as_i64()).unwrap_or(0) as i32,
                    scheme: value.get("metadata").and_then(|m| m.get("scheme")).and_then(|v| v.as_str()).unwrap_or("").to_string(),
                };
                
                state.result = Some(result);
                return;
            }
        }
    }
}

/// Map PDG ID to particle name.
fn pdg_id_name(pdg_id: i32) -> &'static str {
    match pdg_id {
        1 => "d",
        -1 => "d̄",
        2 => "u",
        -2 => "ū",
        3 => "s",
        -3 => "s̄",
        4 => "c",
        -4 => "c̄",
        5 => "b",
        -5 => "b̄",
        6 => "t",
        -6 => "t̄",
        21 => "g",
        _ => "unknown",
    }
}
