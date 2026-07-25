//! HepMC3 event viewer page.
//!
//! Reads HepMC3 event files and displays event number, particles, PDG IDs,
//! status, four-momenta, vertices, parent/child relationships, and supports
//! final-state filtering.

use eframe::egui;
use std::io::{BufReader, Cursor};
use std::path::Path;

use egui_plot::{Bar, BarChart, Legend, Plot};
use quark_sim::physics::{HepMcError, HepMcEvent, HepMcReader};

use super::state::{GuiError, GuiErrorCategory, HepMC3Event, HepMC3Particle, HepMC3Vertex};

#[derive(PartialEq, Clone, Copy)]
pub enum EventView {
    Visualized,
    Raw,
    Plot,
}

/// State for the event viewer page.
pub struct EventViewerPageState {
    pub file_path: String,
    pub events: Vec<HepMC3Event>,
    pub selected_event: usize,
    pub show_final_state_only: bool,
    pub pdg_filter: String,
    pub loaded: bool,
    pub view_mode: EventView,
}

impl Default for EventViewerPageState {
    fn default() -> Self {
        Self {
            file_path: "outputs/dis_run/events.hepmc3".to_string(),
            events: Vec::new(),
            selected_event: 0,
            show_final_state_only: false,
            pdg_filter: String::new(),
            loaded: false,
            view_mode: EventView::Visualized,
        }
    }
}

/// Render the event viewer page.
pub fn render_event_viewer_page(
    state: &mut EventViewerPageState,
    errors: &mut Vec<GuiError>,
    ui: &mut egui::Ui,
) {
    ui.heading("🔍 Event Viewer (HepMC3)");
    ui.separator();

    // File selection
    ui.horizontal(|ui| {
        ui.label("HepMC3 file:");
        ui.text_edit_singleline(&mut state.file_path);
        if ui.button("📂 Load").clicked() {
            load_hepmc3_file(state, errors);
        }
    });

    if !state.loaded {
        ui.label("No event file loaded. Enter a path and click Load.");
        return;
    }

    if state.events.is_empty() {
        ui.colored_label(egui::Color32::YELLOW, "File loaded but no events found.");
        return;
    }

    ui.separator();
    ui.label(format!("Total events loaded: {}", state.events.len()));

    // Event selector
    ui.horizontal(|ui| {
        ui.label("Event:");
        if ui.button("◀").clicked() && state.selected_event > 0 {
            state.selected_event -= 1;
        }
        ui.label(format!(
            "{} / {}",
            state.selected_event + 1,
            state.events.len()
        ));
        if ui.button("▶").clicked() && state.selected_event + 1 < state.events.len() {
            state.selected_event += 1;
        }
        ui.add(
            egui::Slider::new(
                &mut state.selected_event,
                0..=state.events.len().saturating_sub(1),
            )
            .text("Event #"),
        );
    });

    // Filters
    ui.horizontal(|ui| {
        ui.checkbox(
            &mut state.show_final_state_only,
            "Final-state only (status=1)",
        );
        ui.label("PDG filter:");
        ui.text_edit_singleline(&mut state.pdg_filter);
    });

    let event = &state.events[state.selected_event];

    ui.separator();
    ui.heading(format!(
        "Event #{} (weight: {:.4})",
        event.event_number,
        event.weights.first().copied().unwrap_or(1.0)
    ));

    // Particle table
    let pdg_filter_value: Option<i32> = if state.pdg_filter.trim().is_empty() {
        None
    } else {
        state.pdg_filter.trim().parse().ok()
    };

    let filtered_particles: Vec<&HepMC3Particle> = event
        .particles
        .iter()
        .filter(|p| {
            if state.show_final_state_only && p.status != 1 {
                return false;
            }
            if let Some(pdg) = pdg_filter_value {
                if p.pdg_id != pdg {
                    return false;
                }
            }
            true
        })
        .collect();

    ui.label(format!(
        "Particles shown: {} / {}",
        filtered_particles.len(),
        event.particles.len()
    ));

    ui.horizontal(|ui| {
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            ui.selectable_value(&mut state.view_mode, EventView::Plot, "📈 Plot");
            ui.selectable_value(&mut state.view_mode, EventView::Raw, "📄 Raw JSON");
            ui.selectable_value(
                &mut state.view_mode,
                EventView::Visualized,
                "📊 Visualized Table",
            );
        });
    });

    match state.view_mode {
        EventView::Visualized => {
            egui::ScrollArea::vertical()
                .max_height(350.0)
                .show(ui, |ui| {
                    egui::Grid::new("particle_grid")
                        .num_columns(9)
                        .striped(true)
                        .show(ui, |ui| {
                            // Header
                            ui.strong("#");
                            ui.strong("PDG ID");
                            ui.strong("Name");
                            ui.strong("Status");
                            ui.strong("px [GeV]");
                            ui.strong("py [GeV]");
                            ui.strong("pz [GeV]");
                            ui.strong("E [GeV]");
                            ui.strong("Mass [GeV]");
                            ui.end_row();

                            for p in &filtered_particles {
                                ui.label(format!("{}", p.id));
                                ui.label(format!("{}", p.pdg_id));
                                ui.label(pdg_id_name(p.pdg_id));
                                ui.label(format!("{}", p.status));
                                ui.label(format!("{:.4}", p.px));
                                ui.label(format!("{:.4}", p.py));
                                ui.label(format!("{:.4}", p.pz));
                                ui.label(format!("{:.4}", p.energy));
                                ui.label(format!("{:.4}", p.mass));
                                ui.end_row();
                            }
                        });
                });

            // Vertex information
            if !event.vertices.is_empty() {
                ui.separator();
                ui.collapsing("🔗 Vertices", |ui| {
                    egui::Grid::new("vertex_grid")
                        .num_columns(5)
                        .striped(true)
                        .show(ui, |ui| {
                            ui.strong("ID");
                            ui.strong("Position (x,y,z,t)");
                            ui.strong("Incoming");
                            ui.strong("Outgoing");
                            ui.strong("Type");
                            ui.end_row();

                            for v in &event.vertices {
                                ui.label(format!("{}", v.id));
                                ui.label(format!(
                                    "({:.2}, {:.2}, {:.2}, {:.2})",
                                    v.x, v.y, v.z, v.t
                                ));
                                ui.label(format!("{:?}", v.incoming));
                                ui.label(format!("{:?}", v.outgoing));
                                let vtype = if v.incoming.is_empty() {
                                    "Initial"
                                } else {
                                    "Interaction"
                                };
                                ui.label(vtype);
                                ui.end_row();
                            }
                        });
                });
            }
        }
        EventView::Raw => {
            egui::ScrollArea::vertical()
                .max_height(400.0)
                .show(ui, |ui| {
                    let json = serde_json::to_string_pretty(&event)
                        .unwrap_or_else(|_| "Failed to serialize JSON".to_string());
                    ui.add(
                        egui::TextEdit::multiline(&mut json.as_str())
                            .font(egui::TextStyle::Monospace)
                            .desired_width(f32::INFINITY)
                            .interactive(false),
                    );
                });
        }
        EventView::Plot => {
            render_simple_event_display(event, &filtered_particles, ui);
        }
    }
}

/// A simplified graphical event display showing particle flow.
fn render_simple_event_display(
    event: &HepMC3Event,
    particles: &[&HepMC3Particle],
    ui: &mut egui::Ui,
) {
    ui.collapsing("📐 Simplified Event Display", |ui| {
        ui.label("pz vs px projection of final-state particles:");

        let plot = egui_plot::Plot::new("event_display")
            .height(300.0)
            .data_aspect(1.0)
            .allow_drag(true)
            .allow_zoom(true);

        plot.show(ui, |plot_ui| {
            // Draw particle momentum vectors as points
            let final_state: Vec<[f64; 2]> = particles
                .iter()
                .filter(|p| p.status == 1)
                .map(|p| [p.pz, p.px])
                .collect();

            if !final_state.is_empty() {
                plot_ui.points(
                    egui_plot::Points::new(final_state)
                        .radius(4.0)
                        .color(egui::Color32::LIGHT_BLUE)
                        .name("Final-state particles"),
                );
            }

            // Draw beam particles (status == 4 typically)
            let beam: Vec<[f64; 2]> = event
                .particles
                .iter()
                .filter(|p| p.status == 4 || p.status == 21)
                .map(|p| [p.pz, p.px])
                .collect();

            if !beam.is_empty() {
                plot_ui.points(
                    egui_plot::Points::new(beam)
                        .radius(6.0)
                        .color(egui::Color32::RED)
                        .name("Beam particles"),
                );
            }
        });
    });
}

/// Load and parse a HepMC3 file.
fn load_hepmc3_file(state: &mut EventViewerPageState, errors: &mut Vec<GuiError>) {
    let path = Path::new(&state.file_path);
    if !path.exists() {
        errors.push(GuiError::new(
            GuiErrorCategory::FileNotFound,
            format!("File not found: {}", state.file_path),
        ));
        state.loaded = false;
        return;
    }

    let mut reader = match HepMcReader::open(path) {
        Ok(reader) => reader,
        Err(e) => {
            errors.push(GuiError::new(
                GuiErrorCategory::ParseError,
                format!("Failed to open HepMC3 file: {e}"),
            ));
            state.loaded = false;
            return;
        }
    };

    let mut events = Vec::new();
    loop {
        match reader.next_event() {
            Ok(Some(event)) => events.push(project_event(event)),
            Ok(None) => break,
            Err(error) => {
                errors.push(GuiError::new(
                    GuiErrorCategory::ParseError,
                    format!("Failed to parse HepMC3 file: {error}"),
                ));
                state.events.clear();
                state.loaded = false;
                return;
            }
        }
    }

    state.events = events;
    state.selected_event = 0;
    state.loaded = true;
}

/// Parse an in-memory snippet through the authoritative streaming reader.
///
/// The GUI file-loading path uses [`HepMcReader::open`] directly. This helper
/// exists for small GUI tests and performs only an explicit display projection.
pub fn parse_hepmc3(content: &str) -> Result<Vec<HepMC3Event>, HepMcError> {
    HepMcReader::new(BufReader::new(Cursor::new(content.as_bytes())))
        .map(|event| event.map(project_event))
        .collect()
}

fn project_event(event: HepMcEvent) -> HepMC3Event {
    let particles = event
        .particles
        .into_iter()
        .map(|particle| HepMC3Particle {
            id: particle.id,
            pdg_id: particle.pdg_id,
            status: particle.status,
            px: particle.px,
            py: particle.py,
            pz: particle.pz,
            energy: particle.energy,
            mass: particle.generated_mass,
            production_vertex: particle.production_vertex_id,
            end_vertex: particle.end_vertex_id,
        })
        .collect();
    let vertices = event
        .vertices
        .into_iter()
        .map(|vertex| {
            let [x, y, z, t] = vertex.position.unwrap_or([0.0; 4]);
            HepMC3Vertex {
                id: vertex.id,
                x,
                y,
                z,
                t,
                incoming: vertex.incoming_particle_ids,
                outgoing: vertex.outgoing_particle_ids,
            }
        })
        .collect();
    HepMC3Event {
        event_number: event.event_number,
        particles,
        vertices,
        weights: event.weights,
    }
}

/// Filter events to final-state particles only.
#[must_use]
pub fn filter_final_state(event: &HepMC3Event) -> Vec<&HepMC3Particle> {
    event.particles.iter().filter(|p| p.status == 1).collect()
}

/// Filter events by PDG ID.
#[must_use]
pub fn filter_by_pdg(event: &HepMC3Event, pdg_id: i32) -> Vec<&HepMC3Particle> {
    event
        .particles
        .iter()
        .filter(|p| p.pdg_id == pdg_id)
        .collect()
}

/// Map PDG ID to particle name.
fn pdg_id_name(pdg_id: i32) -> &'static str {
    match pdg_id {
        11 => "e⁻",
        -11 => "e⁺",
        12 => "νe",
        -12 => "ν̄e",
        13 => "μ⁻",
        -13 => "μ⁺",
        22 => "γ",
        23 => "Z⁰",
        24 => "W⁺",
        -24 => "W⁻",
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
        21 => "g",
        111 => "π⁰",
        211 => "π⁺",
        -211 => "π⁻",
        321 => "K⁺",
        -321 => "K⁻",
        2212 => "p",
        -2212 => "p̄",
        2112 => "n",
        _ => "?",
    }
}
