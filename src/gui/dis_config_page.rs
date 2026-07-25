//! DIS Configuration page.
//!
//! Renders a form with all configurable DIS parameters and validates them
//! before allowing execution.

use eframe::egui;

use super::state::DisConfig;

/// Render the DIS configuration form and return validation errors if the
/// user clicks "Validate".
pub fn render_config_page(
    config: &mut DisConfig,
    validation_errors: &mut Vec<String>,
    ui: &mut egui::Ui,
) {
    ui.heading("⚙ DIS Configuration");
    ui.separator();

    egui::Grid::new("dis_config_grid")
        .num_columns(2)
        .spacing([20.0, 8.0])
        .striped(true)
        .show(ui, |ui| {
            // --- Beam energies ---
            ui.label("Electron beam energy [GeV]:");
            ui.add(egui::DragValue::new(&mut config.electron_energy_gev).speed(0.1));
            ui.end_row();

            ui.label("Proton beam energy [GeV]:");
            ui.add(egui::DragValue::new(&mut config.proton_energy_gev).speed(1.0));
            ui.end_row();

            // --- Process ---
            ui.label("Process:");
            egui::ComboBox::from_id_source("process_combo")
                .selected_text(&config.process)
                .show_ui(ui, |ui| {
                    ui.selectable_value(&mut config.process, "NC".to_string(), "NC (Neutral Current)");
                    ui.selectable_value(&mut config.process, "CC".to_string(), "CC (Charged Current)");
                });
            ui.end_row();

            ui.separator();
            ui.separator();
            ui.end_row();

            // --- Kinematic ranges ---
            ui.label("x range:");
            ui.horizontal(|ui| {
                ui.add(
                    egui::DragValue::new(&mut config.x_min)
                        .speed(1e-5)
                        .prefix("min: "),
                );
                ui.add(
                    egui::DragValue::new(&mut config.x_max)
                        .speed(0.01)
                        .prefix("max: "),
                );
            });
            ui.end_row();

            ui.label("Q² range [GeV²]:");
            ui.horizontal(|ui| {
                ui.add(
                    egui::DragValue::new(&mut config.q2_min_gev2)
                        .speed(0.1)
                        .prefix("min: "),
                );
                ui.add(
                    egui::DragValue::new(&mut config.q2_max_gev2)
                        .speed(10.0)
                        .prefix("max: "),
                );
            });
            ui.end_row();

            ui.label("y range:");
            ui.horizontal(|ui| {
                ui.add(
                    egui::DragValue::new(&mut config.y_min)
                        .speed(0.01)
                        .prefix("min: "),
                );
                ui.add(
                    egui::DragValue::new(&mut config.y_max)
                        .speed(0.01)
                        .prefix("max: "),
                );
            });
            ui.end_row();

            ui.label("W² cut [GeV²]:");
            ui.add(egui::DragValue::new(&mut config.w2_cut_gev2).speed(0.5));
            ui.end_row();

            ui.separator();
            ui.separator();
            ui.end_row();

            // --- Backend settings ---
            ui.label("Structure-function backend:");
            egui::ComboBox::from_id_source("backend_combo")
                .selected_text(&config.backend)
                .show_ui(ui, |ui| {
                    ui.selectable_value(&mut config.backend, "apfel".to_string(), "APFEL++");
                    ui.selectable_value(&mut config.backend, "lo".to_string(), "Direct LO");
                    ui.selectable_value(&mut config.backend, "surrogate".to_string(), "Surrogate (ML)");
                });
            ui.end_row();

            if config.backend == "surrogate" {
                ui.label("Surrogate limits:");
                if let Ok(text) = std::fs::read_to_string("models/surrogate_v1/config.json") {
                    if let Ok(json) = serde_json::from_str::<serde_json::Value>(&text) {
                        ui.group(|ui| {
                            let x_min = json["x_min"].as_f64().unwrap_or(0.0);
                            let x_max = json["x_max"].as_f64().unwrap_or(0.0);
                            let q2_min = json["q2_min"].as_f64().unwrap_or(0.0);
                            let q2_max = json["q2_max"].as_f64().unwrap_or(0.0);
                            let mse = json["validation_mse"].as_f64().unwrap_or(0.0);
                            ui.label(format!("x: {x_min:.1e} - {x_max:.1e}"));
                            ui.label(format!("Q²: {q2_min:.1} - {q2_max:.1} GeV²"));
                            ui.label(format!("Validation MSE: {mse:.2e}"));
                            ui.colored_label(egui::Color32::YELLOW, "⚠ Requests outside these bounds are strictly rejected.");
                        });
                    }
                } else {
                    ui.colored_label(egui::Color32::RED, "❌ Surrogate model not found (run `train-surrogate` first).");
                }
                ui.end_row();
            }

            ui.label("Perturbative order:");
            egui::ComboBox::from_id_source("order_combo")
                .selected_text(&config.perturbative_order)
                .show_ui(ui, |ui| {
                    ui.selectable_value(
                        &mut config.perturbative_order,
                        "LO".to_string(),
                        "LO",
                    );
                    ui.selectable_value(
                        &mut config.perturbative_order,
                        "NLO".to_string(),
                        "NLO",
                    );
                });
            ui.end_row();

            ui.label("PDF set:");
            ui.text_edit_singleline(&mut config.pdf_set);
            ui.end_row();

            ui.label("PDF member:");
            ui.add(egui::DragValue::new(&mut config.pdf_member).speed(1));
            ui.end_row();

            ui.label("μ_F / Q:");
            ui.add(egui::DragValue::new(&mut config.mu_f_over_q).speed(0.1));
            ui.end_row();

            ui.label("μ_R / Q:");
            ui.add(egui::DragValue::new(&mut config.mu_r_over_q).speed(0.1));
            ui.end_row();

            ui.separator();
            ui.separator();
            ui.end_row();

            // --- Event generation settings ---
            ui.label("Event count:");
            ui.add(egui::DragValue::new(&mut config.event_count).speed(100));
            ui.end_row();

            ui.label("Random seed (empty = auto):");
            ui.text_edit_singleline(&mut config.random_seed);
            ui.end_row();

            ui.label("Parton shower:");
            ui.checkbox(&mut config.parton_shower, "");
            ui.end_row();

            ui.label("Hadronization:");
            ui.checkbox(&mut config.hadronization, "");
            ui.end_row();

            ui.label("Output directory:");
            ui.text_edit_singleline(&mut config.output_directory);
            ui.end_row();
        });

    ui.separator();

    if ui.button("✅ Validate Configuration").clicked() {
        let errors = config.validate();
        validation_errors.clear();
        for e in &errors {
            validation_errors.push(e.to_string());
        }
        if errors.is_empty() {
            validation_errors.push("✓ All configuration fields are valid.".to_string());
        }
    }

    if !validation_errors.is_empty() {
        ui.separator();
        for msg in validation_errors.iter() {
            if msg.starts_with('✓') {
                ui.colored_label(egui::Color32::GREEN, msg);
            } else {
                ui.colored_label(egui::Color32::RED, format!("❌ {msg}"));
            }
        }
    }
}
