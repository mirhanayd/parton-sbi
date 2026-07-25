//! GUI module — two-mode application with Legacy Cornell Demo and DIS Analysis.
//!
//! The application renders a side panel with mode and page selection, and
//! dispatches to the active page's rendering function. The Cornell demo and
//! DIS analysis are completely separated and never mixed.

pub mod dis_config_page;
pub mod dis_event_gen_page;
pub mod dis_event_viewer_page;
pub mod dis_inclusive_page;
pub mod dis_run_history_page;
pub mod dis_validation_page;
pub mod legacy_cornell;
pub mod state;
pub mod theme;
pub mod worker;

#[cfg(test)]
mod tests;

use eframe::egui;

use dis_config_page::render_config_page;
use dis_event_gen_page::{render_event_gen_page, EventGenPageState};
use dis_event_viewer_page::{render_event_viewer_page, EventViewerPageState};
use dis_inclusive_page::{render_inclusive_page, InclusivePageState};
use dis_run_history_page::{render_run_history_page, RunHistoryPageState};
use dis_validation_page::{render_validation_page, ValidationPageState};
use legacy_cornell::{render_cornell_page, AppData, CornellPageState, InteractiveContext};
use state::{DisConfig, DisPage, ErrorState, GuiError, TopLevelMode, UiState};
use theme::apply_theme;

// Re-export types needed by main.rs
pub use legacy_cornell::{AppData as LegacyAppData, InteractiveContext as LegacyInteractiveContext};

// ---------------------------------------------------------------------------
// Main application struct
// ---------------------------------------------------------------------------

/// The top-level application struct. Holds separated state for each concern.
pub struct SimulationApp {
    // UI navigation
    ui_state: UiState,

    // Legacy Cornell state
    cornell_state: CornellPageState,

    // DIS state
    dis_config: DisConfig,
    config_validation_errors: Vec<String>,
    inclusive_state: InclusivePageState,
    event_gen_state: EventGenPageState,
    event_viewer_state: EventViewerPageState,
    validation_state: ValidationPageState,
    run_history_state: RunHistoryPageState,

    // Error state
    error_state: ErrorState,
}

impl SimulationApp {
    /// Create a new application with legacy Cornell data (for backward compatibility).
    pub fn new(data: AppData, interactive: Option<InteractiveContext>) -> Self {
        Self {
            ui_state: UiState {
                mode: TopLevelMode::LegacyCornell,
                ..UiState::default()
            },
            cornell_state: CornellPageState::new(data, interactive),
            dis_config: DisConfig::default(),
            config_validation_errors: Vec::new(),
            inclusive_state: InclusivePageState::default(),
            event_gen_state: EventGenPageState::default(),
            event_viewer_state: EventViewerPageState::default(),
            validation_state: ValidationPageState::default(),
            run_history_state: RunHistoryPageState::default(),
            error_state: ErrorState::default(),
        }
    }

    /// Create a new application starting in DIS analysis mode.
    pub fn new_dis_mode() -> Self {
        Self {
            ui_state: UiState::default(),
            cornell_state: CornellPageState::empty(),
            dis_config: DisConfig::default(),
            config_validation_errors: Vec::new(),
            inclusive_state: InclusivePageState::default(),
            event_gen_state: EventGenPageState::default(),
            event_viewer_state: EventViewerPageState::default(),
            validation_state: ValidationPageState::default(),
            run_history_state: RunHistoryPageState::default(),
            error_state: ErrorState::default(),
        }
    }
}

impl eframe::App for SimulationApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Side panel for mode and page selection
        egui::SidePanel::left("nav_panel")
            .resizable(false)
            .default_width(220.0)
            .show(ctx, |ui| {
                ui.heading("🔬 Quark Sim");
                ui.separator();

                ui.label("Mode:");
                ui.selectable_value(
                    &mut self.ui_state.mode,
                    TopLevelMode::LegacyCornell,
                    "🎓 Legacy Cornell Demo",
                );
                ui.selectable_value(
                    &mut self.ui_state.mode,
                    TopLevelMode::DisAnalysis,
                    "⚛ DIS Analysis",
                );

                if self.ui_state.mode == TopLevelMode::DisAnalysis {
                    ui.separator();
                    ui.label("DIS Pages:");
                    for page in DisPage::ALL {
                        ui.selectable_value(
                            &mut self.ui_state.active_dis_page,
                            page,
                            page.label(),
                        );
                    }
                }

                ui.separator();

                // Error display
                if self.error_state.has_errors() {
                    ui.collapsing("⚠ Errors", |ui| {
                        if ui.button("Clear all").clicked() {
                            self.error_state.clear();
                        }
                        egui::ScrollArea::vertical()
                            .max_height(200.0)
                            .show(ui, |ui| {
                                for error in self.error_state.errors.iter().rev() {
                                    ui.colored_label(egui::Color32::RED, &error.message);
                                    ui.small(&error.suggestion);
                                    ui.separator();
                                }
                            });
                    });
                }
            });

        // Central panel with the active page content
        egui::CentralPanel::default().show(ctx, |ui| {
            egui::ScrollArea::vertical().show(ui, |ui| {
                match self.ui_state.mode {
                    TopLevelMode::LegacyCornell => {
                        render_cornell_page(&mut self.cornell_state, ui, ctx);
                    }
                    TopLevelMode::DisAnalysis => {
                        self.render_dis_page(ui, ctx);
                    }
                }
            });
        });
    }
}

impl SimulationApp {
    fn render_dis_page(&mut self, ui: &mut egui::Ui, ctx: &egui::Context) {
        match self.ui_state.active_dis_page {
            DisPage::Configuration => {
                render_config_page(
                    &mut self.dis_config,
                    &mut self.config_validation_errors,
                    ui,
                );
            }
            DisPage::InclusiveCalculation => {
                render_inclusive_page(
                    &mut self.inclusive_state,
                    &self.dis_config,
                    &mut self.error_state.errors,
                    ui,
                    ctx,
                );
            }
            DisPage::EventGeneration => {
                render_event_gen_page(
                    &mut self.event_gen_state,
                    &self.dis_config,
                    &mut self.error_state.errors,
                    ui,
                    ctx,
                );
            }
            DisPage::EventViewer => {
                render_event_viewer_page(
                    &mut self.event_viewer_state,
                    &mut self.error_state.errors,
                    ui,
                );
            }
            DisPage::DataValidation => {
                render_validation_page(
                    &mut self.validation_state,
                    &mut self.error_state.errors,
                    ui,
                );
            }
            DisPage::RunHistory => {
                render_run_history_page(
                    &mut self.run_history_state,
                    &mut self.error_state.errors,
                    ui,
                );
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Public launcher function
// ---------------------------------------------------------------------------

/// Launch the GUI application.
pub fn launch_gui(
    app_data: AppData,
    title: &str,
    interactive: Option<InteractiveContext>,
) -> candle_core::Result<()> {
    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1400.0, 900.0])
            .with_title(title),
        ..Default::default()
    };

    eframe::run_native(
        title,
        native_options,
        Box::new(move |cc| {
            theme::apply_theme(&cc.egui_ctx);
            Box::new(SimulationApp::new(app_data, interactive))
        }),
    )
    .map_err(|error| candle_core::Error::Msg(format!("GUI error: {error}")))
}

/// Launch the GUI directly in DIS analysis mode.
pub fn launch_dis_gui(title: &str) -> candle_core::Result<()> {
    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1400.0, 900.0])
            .with_title(title),
        ..Default::default()
    };

    eframe::run_native(
        title,
        native_options,
        Box::new(move |cc| {
            theme::apply_theme(&cc.egui_ctx);
            Box::new(SimulationApp::new_dis_mode())
        }),
    )
    .map_err(|error| candle_core::Error::Msg(format!("GUI error: {error}")))
}
