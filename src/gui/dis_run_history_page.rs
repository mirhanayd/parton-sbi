//! Run history page.
//!
//! Lists output runs and reads their metadata. Supports opening existing
//! config.json, metadata.json, summary.json, comparison.json, and events.hepmc3
//! files. Detects incompatible schema versions.

use eframe::egui;
use std::fs;
use std::path::{Path, PathBuf};

use super::state::{
    is_schema_compatible, GuiError, GuiErrorCategory, RunHistoryEntry, CURRENT_SCHEMA_VERSION,
};

/// State for the run history page.
pub struct RunHistoryPageState {
    pub base_directory: String,
    pub entries: Vec<RunHistoryEntry>,
    pub selected_entry: Option<usize>,
    pub file_content: Option<String>,
    pub file_label: String,
    pub scanned: bool,
}

impl Default for RunHistoryPageState {
    fn default() -> Self {
        Self {
            base_directory: "outputs".to_string(),
            entries: Vec::new(),
            selected_entry: None,
            file_content: None,
            file_label: String::new(),
            scanned: false,
        }
    }
}

/// Render the run history page.
pub fn render_run_history_page(
    state: &mut RunHistoryPageState,
    errors: &mut Vec<GuiError>,
    ui: &mut egui::Ui,
) {
    ui.heading("📁 Run History");
    ui.separator();

    ui.horizontal(|ui| {
        ui.label("Output base directory:");
        ui.text_edit_singleline(&mut state.base_directory);
        if ui.button("🔄 Scan").clicked() {
            scan_runs(state, errors);
        }
    });

    if !state.scanned {
        ui.label("Click 'Scan' to discover existing output runs.");
        return;
    }

    if state.entries.is_empty() {
        ui.label("No output runs found in the specified directory.");
        return;
    }

    ui.separator();
    ui.label(format!("Found {} runs:", state.entries.len()));

    // Run list
    egui::ScrollArea::vertical()
        .max_height(200.0)
        .show(ui, |ui| {
            for (idx, entry) in state.entries.iter().enumerate() {
                let selected = state.selected_entry == Some(idx);
                let label = format!(
                    "{} {}{}{}{}",
                    entry.run_name,
                    if entry.has_config { "📝" } else { "" },
                    if entry.has_summary { "📊" } else { "" },
                    if entry.has_events { "📄" } else { "" },
                    if !is_schema_compatible(entry.schema_version) {
                        " ⚠ incompatible"
                    } else {
                        ""
                    },
                );
                if ui.selectable_label(selected, &label).clicked() {
                    state.selected_entry = Some(idx);
                    state.file_content = None;
                    state.file_label.clear();
                }
            }
        });

    // Selected entry details
    if let Some(idx) = state.selected_entry {
        if let Some(entry) = state.entries.get(idx).cloned() {
            ui.separator();
            ui.heading(format!("Run: {}", entry.run_name));

            ui.group(|ui| {
                ui.label(format!("Directory: {}", entry.directory.display()));

                if let Some(sv) = entry.schema_version {
                    if sv != CURRENT_SCHEMA_VERSION {
                        ui.colored_label(
                            egui::Color32::RED,
                            format!(
                                "⚠ Schema version {sv} is not compatible with current version {CURRENT_SCHEMA_VERSION}. \
                                 Files will not be reinterpreted."
                            ),
                        );
                    } else {
                        ui.colored_label(
                            egui::Color32::GREEN,
                            format!("✓ Schema version {sv} is compatible."),
                        );
                    }
                }

                // File open buttons
                ui.horizontal(|ui| {
                    let dir = entry.directory.clone();
                    let compatible = is_schema_compatible(entry.schema_version);

                    if entry.has_config
                        && ui
                            .add_enabled(compatible, egui::Button::new("📝 config.json"))
                            .clicked()
                    {
                        open_file(&dir.join("config.json"), state, errors);
                    }
                    if entry.has_metadata
                        && ui
                            .add_enabled(compatible, egui::Button::new("📋 metadata.json"))
                            .clicked()
                    {
                        open_file(&dir.join("metadata.json"), state, errors);
                    }
                    if entry.has_summary
                        && ui
                            .add_enabled(compatible, egui::Button::new("📊 summary.json"))
                            .clicked()
                    {
                        open_file(&dir.join("summary.json"), state, errors);
                    }
                    if entry.has_comparison
                        && ui
                            .add_enabled(compatible, egui::Button::new("📈 comparison.json"))
                            .clicked()
                    {
                        open_file(&dir.join("comparison.json"), state, errors);
                    }
                    if entry.has_events {
                        // Find events file
                        let events_path = find_events_file(&dir);
                        if let Some(ref ep) = events_path {
                            if ui
                                .add_enabled(compatible, egui::Button::new("📄 events.hepmc3"))
                                .clicked()
                            {
                                open_file(ep, state, errors);
                            }
                        }
                    }
                });
            });

            // File content viewer
            if let Some(ref content) = state.file_content {
                ui.separator();
                ui.heading(format!("📄 {}", state.file_label));
                egui::ScrollArea::vertical()
                    .max_height(400.0)
                    .show(ui, |ui| {
                        ui.code(content);
                    });
            }
        }
    }
}

/// Scan the base directory for output runs.
pub fn scan_runs(state: &mut RunHistoryPageState, errors: &mut Vec<GuiError>) {
    let base = Path::new(&state.base_directory);
    if !base.is_dir() {
        errors.push(GuiError::new(
            GuiErrorCategory::FileNotFound,
            format!("Directory not found: {}", state.base_directory),
        ));
        state.scanned = false;
        return;
    }

    state.entries.clear();
    state.selected_entry = None;
    state.file_content = None;

    // Recursively scan for directories containing config.json, metadata.json, summary.json, etc.
    scan_directory(base, &mut state.entries);

    // Sort by name
    state.entries.sort_by(|a, b| a.run_name.cmp(&b.run_name));
    state.scanned = true;
}

fn scan_directory(dir: &Path, entries: &mut Vec<RunHistoryEntry>) {
    let read_dir = match fs::read_dir(dir) {
        Ok(rd) => rd,
        Err(_) => return,
    };

    for entry in read_dir.flatten() {
        let path = entry.path();
        if path.is_dir() {
            let has_config = path.join("config.json").exists();
            let has_metadata = path.join("metadata.json").exists();
            let has_summary = path.join("summary.json").exists();
            let has_comparison = path.join("comparison.json").exists();
            let has_events = find_events_file(&path).is_some();

            if has_config || has_metadata || has_summary || has_comparison || has_events {
                let schema_version = read_schema_version(&path);
                entries.push(RunHistoryEntry {
                    run_name: path
                        .file_name()
                        .map(|n| n.to_string_lossy().to_string())
                        .unwrap_or_else(|| "unknown".to_string()),
                    directory: path.clone(),
                    has_config,
                    has_metadata,
                    has_summary,
                    has_comparison,
                    has_events,
                    schema_version,
                });
            }

            // Recurse one level deeper
            scan_directory(&path, entries);
        }
    }
}

/// Try to read the schema_version from config.json.
fn read_schema_version(dir: &Path) -> Option<i32> {
    let config_path = dir.join("config.json");
    if !config_path.exists() {
        // If there's no config.json, assume current version.
        return Some(CURRENT_SCHEMA_VERSION);
    }
    let content = fs::read_to_string(&config_path).ok()?;
    let value: serde_json::Value = serde_json::from_str(&content).ok()?;
    value
        .get("schema_version")
        .and_then(|v| v.as_i64())
        .map(|v| v as i32)
}

/// Find the events HepMC3 file in a directory.
fn find_events_file(dir: &Path) -> Option<PathBuf> {
    let candidates = ["events.hepmc3", "events.hepmc", "events.hepmc3.gz"];
    for name in &candidates {
        let path = dir.join(name);
        if path.exists() {
            return Some(path);
        }
    }
    None
}

/// Open and display a file's content.
fn open_file(path: &Path, state: &mut RunHistoryPageState, errors: &mut Vec<GuiError>) {
    match fs::read_to_string(path) {
        Ok(content) => {
            // Truncate very large files for display
            let display_content = if content.len() > 100_000 {
                format!(
                    "{}\n\n... [truncated, {} bytes total]",
                    &content[..100_000],
                    content.len()
                )
            } else {
                content
            };
            state.file_label = path
                .file_name()
                .map(|n| n.to_string_lossy().to_string())
                .unwrap_or_else(|| "file".to_string());
            state.file_content = Some(display_content);
        }
        Err(e) => {
            errors.push(GuiError::new(
                GuiErrorCategory::FileNotFound,
                format!("Failed to read {}: {e}", path.display()),
            ));
        }
    }
}
