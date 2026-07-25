//! Event generation page.
//!
//! Launches PYTHIA event generation in a worker thread and displays progress,
//! accepted/failed events, output location, logs, and summary statistics.

use eframe::egui;
use std::sync::atomic::AtomicBool;
use std::sync::Arc;

use super::state::{
    BackendProcess, DisConfig, EventGenSummary, GuiError, GuiErrorCategory, ProcessStatus,
};
use super::worker::{self, WorkerHandle, WorkerMessage};

#[derive(PartialEq, Clone, Copy)]
pub enum EventGenView {
    Visualized,
    Raw,
}

/// State for the event generation page.
pub struct EventGenPageState {
    pub process: BackendProcess,
    pub worker: Option<WorkerHandle>,
    pub summary: Option<EventGenSummary>,
    pub accepted_count: usize,
    pub failed_count: usize,
    pub view_mode: EventGenView,
}

impl Default for EventGenPageState {
    fn default() -> Self {
        Self {
            process: BackendProcess::default(),
            worker: None,
            summary: None,
            accepted_count: 0,
            failed_count: 0,
            view_mode: EventGenView::Visualized,
        }
    }
}

/// Render the event generation page.
pub fn render_event_gen_page(
    state: &mut EventGenPageState,
    config: &DisConfig,
    errors: &mut Vec<GuiError>,
    ui: &mut egui::Ui,
    ctx: &egui::Context,
) {
    ui.heading("🚀 Event Generation (PYTHIA 8)");
    ui.separator();

    // Poll worker
    if let Some(ref handle) = state.worker {
        for msg in handle.drain() {
            match msg {
                WorkerMessage::StdoutLine(line) => {
                    // Try to parse progress info from stdout
                    parse_event_progress(&line, state);
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
                    parse_event_summary(state, config);
                }
                WorkerMessage::Failed(msg) => {
                    state.process.status = ProcessStatus::Failed;
                    errors.push(GuiError::new(GuiErrorCategory::ProcessFailed, msg));
                }
            }
        }
        if state.process.status == ProcessStatus::Running {
            ctx.request_repaint();
        }
    }

    // Configuration summary
    ui.group(|ui| {
        ui.label(format!(
            "Beams: e⁻ ({:.1} GeV) × p ({:.1} GeV)",
            config.electron_energy_gev, config.proton_energy_gev
        ));
        ui.label(format!(
            "Events: {} | PDF: {} | Order: {}",
            config.event_count, config.pdf_set, config.perturbative_order
        ));
        ui.label(format!(
            "Q²: [{:.1}, {:.1}] GeV² | x: [{:.1e}, {:.2}]",
            config.q2_min_gev2, config.q2_max_gev2, config.x_min, config.x_max
        ));
        ui.label(format!(
            "Parton shower: {} | Hadronization: {}",
            if config.parton_shower { "ON" } else { "OFF" },
            if config.hadronization { "ON" } else { "OFF" }
        ));
    });

    ui.separator();

    let is_running = state.process.status == ProcessStatus::Running;

    ui.horizontal(|ui| {
        if ui
            .add_enabled(!is_running, egui::Button::new("▶ Start Generation"))
            .clicked()
        {
            start_event_generation(state, config, errors);
        }
        if ui
            .add_enabled(is_running, egui::Button::new("⏹ Cancel"))
            .clicked()
        {
            if let Some(ref handle) = state.worker {
                handle.cancel();
            }
            state.process.status = ProcessStatus::Cancelled;
        }
    });

    // Progress display
    match state.process.status {
        ProcessStatus::Running => {
            ui.separator();
            ui.spinner();
            ui.label(&state.process.progress_text);
            let progress = if config.event_count > 0 {
                state.accepted_count as f32 / config.event_count as f32
            } else {
                0.0
            };
            ui.add(egui::ProgressBar::new(progress.min(1.0)).show_percentage());
            ui.label(format!(
                "Accepted: {} | Failed: {}",
                state.accepted_count, state.failed_count
            ));
        }
        ProcessStatus::Completed => {
            ui.separator();
            ui.colored_label(egui::Color32::GREEN, "✓ Generation completed");
        }
        ProcessStatus::Failed => {
            ui.separator();
            ui.colored_label(egui::Color32::RED, "⚠ Generation failed");
            if let Some(code) = state.process.exit_code {
                ui.label(format!("Exit code: {code}"));
            }
        }
        ProcessStatus::Cancelled => {
            ui.separator();
            ui.colored_label(egui::Color32::YELLOW, "⚠ Generation cancelled");
        }
        ProcessStatus::Idle => {}
    }

    // Summary
    if let Some(ref summary) = state.summary {
        ui.separator();
        ui.horizontal(|ui| {
            ui.heading("Summary");
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                ui.selectable_value(&mut state.view_mode, EventGenView::Raw, "📄 Raw JSON");
                ui.selectable_value(&mut state.view_mode, EventGenView::Visualized, "📊 Visualized Data");
            });
        });

        match state.view_mode {
            EventGenView::Visualized => {
                egui::Grid::new("event_gen_summary_grid")
            .num_columns(2)
            .striped(true)
            .show(ui, |ui| {
                ui.label("Total events requested:");
                ui.label(format!("{}", summary.total_events));
                ui.end_row();

                ui.label("Accepted events:");
                ui.label(format!("{}", summary.accepted_events));
                ui.end_row();

                ui.label("Failed events:");
                ui.label(format!("{}", summary.failed_events));
                ui.end_row();

                ui.label("Output path:");
                ui.label(&summary.output_path);
                ui.end_row();

                if let Some(ref hepmc3) = summary.hepmc3_file {
                    ui.label("HepMC3 file:");
                    ui.label(hepmc3);
                    ui.end_row();
                }
            });
            }
            EventGenView::Raw => {
                egui::ScrollArea::vertical()
                    .max_height(400.0)
                    .show(ui, |ui| {
                        let json = serde_json::to_string_pretty(&summary).unwrap_or_else(|_| "Failed to serialize JSON".to_string());
                        ui.add(
                            egui::TextEdit::multiline(&mut json.as_str())
                                .font(egui::TextStyle::Monospace)
                                .desired_width(f32::INFINITY)
                                .interactive(false),
                        );
                    });
            }
        }
    }

    // Logs
    if !state.process.stdout_lines.is_empty() || !state.process.stderr_lines.is_empty() {
        ui.separator();
        ui.collapsing("📋 Generator Logs", |ui| {
            egui::ScrollArea::vertical()
                .max_height(300.0)
                .stick_to_bottom(true)
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

fn start_event_generation(
    state: &mut EventGenPageState,
    config: &DisConfig,
    errors: &mut Vec<GuiError>,
) {
    // Validate config first
    let config_errors = config.validate();
    if !config_errors.is_empty() {
        for e in &config_errors {
            errors.push(GuiError::new(
                GuiErrorCategory::InvalidKinematics,
                e.to_string(),
            ));
        }
        return;
    }

    state.process.reset();
    state.process.status = ProcessStatus::Running;
    state.summary = None;
    state.accepted_count = 0;
    state.failed_count = 0;

    let args = super::state::build_event_generation_command(config);
    let cancel_flag = Arc::clone(&state.process.cancel_flag);

    let exe = std::env::current_exe()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| "quark_sim".to_string());

    state.worker = Some(worker::spawn_subprocess(&exe, &args, cancel_flag));
}

/// Try to parse event counts from a stdout line.
fn parse_event_progress(line: &str, state: &mut EventGenPageState) {
    // Look for patterns like "Events generated: 100" or "Accepted: 100 Failed: 5"
    if let Some(rest) = line.strip_prefix("Events generated:") {
        if let Ok(n) = rest.trim().parse::<usize>() {
            state.accepted_count = n;
        }
    }
    if line.contains("accepted") || line.contains("Accepted") {
        // Try to extract number after "accepted" or "Accepted"
        for word in line.split_whitespace() {
            if let Ok(n) = word.parse::<usize>() {
                state.accepted_count = n;
                break;
            }
        }
    }
}

/// Create a summary after completion.
fn parse_event_summary(state: &mut EventGenPageState, config: &DisConfig) {
    state.summary = Some(EventGenSummary {
        total_events: config.event_count,
        accepted_events: state.accepted_count,
        failed_events: state.failed_count,
        output_path: config.output_directory.clone(),
        hepmc3_file: Some(format!("{}/events.hepmc3", config.output_directory)),
        config_file: Some(format!("{}/config.json", config.output_directory)),
        metadata_file: Some(format!("{}/metadata.json", config.output_directory)),
    });
}
