//! Legacy Cornell educational demo mode.
//!
//! This module preserves the original interactive proton spin laboratory
//! visualization. It is **not** a DIS physics analysis tool — it uses
//! neural-network-predicted Cornell potentials for pedagogical illustration.

use crate::model::QuarkModel;
use crate::scattering::{get_proton_quarks, Electron, TargetQuark};
use candle_core::Device;
use eframe::egui;
use egui_plot::{Line, Plot, PlotPoints, Points, Text};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use std::sync::Arc;

// ---------------------------------------------------------------------------
// Session data (preserved from original gui.rs)
// ---------------------------------------------------------------------------

#[derive(Serialize, Deserialize, Clone)]
pub struct ElectronData {
    pub trajectory: Vec<(f32, f32)>,
    pub impact_parameter: f32,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct AppData {
    pub loss_history: Vec<(usize, f32)>,
    pub potential_theory: Vec<(f32, f32)>,
    pub potential_nn: Vec<(f32, f32)>,
    pub test_distances: Vec<f32>,
    pub cornell_values: Vec<f32>,
    pub nn_values: Vec<f32>,
    pub loss_file: String,
    pub potential_file: String,
    #[serde(default)]
    pub scattering_file: Option<String>,
    #[serde(default)]
    pub electrons: Option<Vec<ElectronData>>,
}

impl AppData {
    pub fn save_session(&self, output_dir: &str) -> std::io::Result<String> {
        let filename = format!("{}/session.json", output_dir);
        let json = serde_json::to_string_pretty(self)?;
        fs::write(&filename, json)?;
        Ok(filename)
    }
    pub fn load_session(filename: impl AsRef<Path>) -> std::io::Result<Self> {
        let json = fs::read_to_string(filename)?;
        let data: AppData = serde_json::from_str(&json)?;
        Ok(data)
    }
}

// ---------------------------------------------------------------------------
// Interactive context (preserved from original gui.rs)
// ---------------------------------------------------------------------------

pub struct InteractiveContext {
    pub model: Arc<QuarkModel>,
    pub device: Device,
    pub mean: f32,
    pub std: f32,
    pub live_electrons: Vec<Electron>,
    pub targets: Vec<TargetQuark>,
}

// ---------------------------------------------------------------------------
// Cornell page state
// ---------------------------------------------------------------------------

pub struct CornellPageState {
    pub data: AppData,
    pub interactive: Option<InteractiveContext>,
    pub show_loss: bool,
    pub show_theory: bool,
    pub show_nn: bool,
    pub show_points: bool,
    pub last_error: Option<String>,
}

impl CornellPageState {
    #[must_use]
    pub fn new(data: AppData, interactive: Option<InteractiveContext>) -> Self {
        Self {
            data,
            interactive,
            show_loss: true,
            show_theory: true,
            show_nn: true,
            show_points: true,
            last_error: None,
        }
    }

    /// Create a minimal state for when no session data is available.
    #[must_use]
    pub fn empty() -> Self {
        Self::new(
            AppData {
                loss_history: Vec::new(),
                potential_theory: Vec::new(),
                potential_nn: Vec::new(),
                test_distances: Vec::new(),
                cornell_values: Vec::new(),
                nn_values: Vec::new(),
                loss_file: String::new(),
                potential_file: String::new(),
                scattering_file: None,
                electrons: None,
            },
            None,
        )
    }
}

// ---------------------------------------------------------------------------
// Cornell page rendering
// ---------------------------------------------------------------------------

/// Render the legacy Cornell demo page.
pub fn render_cornell_page(state: &mut CornellPageState, ui: &mut egui::Ui, ctx: &egui::Context) {
    // Update interactive simulation
    if let Some(ref mut context) = state.interactive {
        let dt = 0.05;
        let force_scale = 0.2;
        for e in &mut context.live_electrons {
            if e.x < 10.0 && e.x > -10.0 && e.y.abs() < 8.0 {
                if let Err(error) = e.update_step(
                    &context.model,
                    &context.targets,
                    context.mean,
                    context.std,
                    &context.device,
                    dt,
                    force_scale,
                ) {
                    state.last_error = Some(format!("Interactive simulation stopped: {error}"));
                    break;
                }
            }
        }
        ctx.request_repaint();
    }

    ui.heading("🔬 Proton Spin Laboratuvarı");
    ui.label("⚠ Educational Cornell potential demo — not a DIS physics analysis.");

    if let Some(error) = &state.last_error {
        ui.colored_label(egui::Color32::RED, error);
    }

    if let Some(ref mut ctx) = state.interactive {
        ui.horizontal(|ui| {
            ui.colored_label(egui::Color32::GREEN, "🟢 CANLI MOD");
            if ui.button("🧹 Parçacıkları Temizle").clicked() {
                ctx.live_electrons.clear();
            }
        });
        ui.label("Kuarklara tıklayarak spin yönlerini (↑/↓) değiştirebilirsiniz.");
    }

    ui.separator();

    ui.group(|ui| {
        let plot = Plot::new("interactive_plot")
            .height(500.0)
            .data_aspect(1.0)
            .allow_drag(true)
            .allow_zoom(true)
            .coordinates_formatter(
                egui_plot::Corner::LeftBottom,
                egui_plot::CoordinatesFormatter::default(),
            );

        plot.show(ui, |plot_ui| {
            // 1. Target quarks
            if let Some(ref mut ctx) = state.interactive {
                for quark in ctx.targets.iter_mut() {
                    let color = if quark.spin > 0.0 {
                        egui::Color32::RED
                    } else {
                        egui::Color32::BLUE
                    };
                    let symbol = if quark.spin > 0.0 { "⬆" } else { "⬇" };

                    plot_ui.points(
                        Points::new(vec![[quark.x as f64, quark.y as f64]])
                            .radius(10.0_f32)
                            .color(color)
                            .name("Kuark"),
                    );

                    plot_ui.text(
                        Text::new(
                            [quark.x as f64, quark.y as f64 + 0.2].into(),
                            symbol,
                        )
                        .color(egui::Color32::BLACK)
                        .name("Spin"),
                    );
                }

                if plot_ui.response().clicked() {
                    if let Some(pointer) = plot_ui.pointer_coordinate() {
                        let px = pointer.x as f32;
                        let py = pointer.y as f32;

                        let mut clicked_quark = false;
                        for quark in ctx.targets.iter_mut() {
                            let dist =
                                ((quark.x - px).powi(2) + (quark.y - py).powi(2)).sqrt();
                            if dist < 0.3 {
                                quark.spin *= -1.0;
                                clicked_quark = true;
                                break;
                            }
                        }

                        if !clicked_quark {
                            let vx = 0.5;
                            let vy = 0.0;
                            ctx.live_electrons.push(Electron::new(px, py, vx, vy));
                        }
                    }
                }
            } else {
                for quark in get_proton_quarks() {
                    let color = if quark.spin > 0.0 {
                        egui::Color32::RED
                    } else {
                        egui::Color32::BLUE
                    };
                    plot_ui.points(
                        Points::new(vec![[quark.x as f64, quark.y as f64]])
                            .radius(10.0_f32)
                            .color(color),
                    );
                }
            }

            // 2. Live electrons
            if let Some(ref ctx) = state.interactive {
                for e in &ctx.live_electrons {
                    let points: PlotPoints = e
                        .trajectory
                        .iter()
                        .map(|(x, y)| [*x as f64, *y as f64])
                        .collect();
                    plot_ui.line(
                        Line::new(points)
                            .color(egui::Color32::YELLOW)
                            .width(2.0_f32),
                    );
                    plot_ui.points(
                        Points::new(vec![[e.x as f64, e.y as f64]])
                            .radius(3.0_f32)
                            .color(egui::Color32::YELLOW),
                    );
                }
            } else if let Some(ref electrons) = state.data.electrons {
                for electron in electrons {
                    let points: PlotPoints = electron
                        .trajectory
                        .iter()
                        .map(|(x, y)| [*x as f64, *y as f64])
                        .collect();
                    plot_ui.line(
                        Line::new(points)
                            .color(egui::Color32::LIGHT_BLUE)
                            .width(1.5_f32),
                    );
                }
            }
        });
    });

    // Statistics charts
    ui.collapsing("📉 İstatistikler", |ui| {
        ui.columns(2, |columns| {
            columns[0].group(|ui| {
                ui.heading("Eğitim Kaybı");
                ui.checkbox(&mut state.show_loss, "Göster");
                if state.data.loss_history.is_empty() {
                    ui.label("Eğitim kaybı verisi yok (model eğitim yapılmadan yüklendi).");
                } else if state.show_loss {
                    let points: PlotPoints = state
                        .data
                        .loss_history
                        .iter()
                        .map(|(e, l)| [*e as f64, *l as f64])
                        .collect();
                    Plot::new("loss")
                        .height(200.0)
                        .show(ui, |p| p.line(Line::new(points)));
                }
            });
            columns[1].group(|ui| {
                ui.heading("Potansiyel");
                ui.horizontal(|ui| {
                    ui.checkbox(&mut state.show_theory, "Teori");
                    ui.checkbox(&mut state.show_nn, "Sinir ağı");
                    ui.checkbox(&mut state.show_points, "Test noktaları");
                });
                Plot::new("potential").height(200.0).show(ui, |p| {
                    if state.show_theory {
                        let pts: PlotPoints = state
                            .data
                            .potential_theory
                            .iter()
                            .map(|(x, y)| [*x as f64, *y as f64])
                            .collect();
                        p.line(Line::new(pts).color(egui::Color32::BLUE).name("Teori"));
                    }
                    if state.show_nn {
                        let pts: PlotPoints = state
                            .data
                            .potential_nn
                            .iter()
                            .map(|(x, y)| [*x as f64, *y as f64])
                            .collect();
                        p.line(
                            Line::new(pts).color(egui::Color32::RED).name("Yapay Zeka"),
                        );
                    }
                    if state.show_points {
                        let pts: PlotPoints = state
                            .data
                            .test_distances
                            .iter()
                            .zip(state.data.nn_values.iter())
                            .map(|(x, y)| [*x as f64, *y as f64])
                            .collect();
                        p.points(
                            Points::new(pts)
                                .color(egui::Color32::GREEN)
                                .radius(3.0_f32)
                                .name("Test"),
                        );
                    }
                });
            });
        });
    });
}
