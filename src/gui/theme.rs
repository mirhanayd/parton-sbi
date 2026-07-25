use eframe::egui::{Color32, Stroke, Visuals, Rounding, style::Margin};
use eframe::egui::epaint::Shadow;

/// Apply a highly professional, modern dark theme to the egui context.
pub fn apply_theme(ctx: &eframe::egui::Context) {
    let mut visuals = Visuals::dark();

    // Backgrounds (deep dark blue-ish gray)
    let bg_color = Color32::from_rgb(22, 24, 29); // App background
    let panel_bg = Color32::from_rgb(28, 31, 38); // Side panels
    let window_bg = Color32::from_rgb(35, 39, 46); // Windows / popups

    // Accents
    let accent_color = Color32::from_rgb(59, 130, 246); // Modern blue
    let accent_hover = Color32::from_rgb(96, 165, 250);

    // Text colors
    let text_primary = Color32::from_rgb(220, 220, 225);
    let text_secondary = Color32::from_rgb(140, 145, 155);

    // Borders / Strokes
    let border_color = Color32::from_rgb(50, 55, 65);
    let thin_stroke = Stroke::new(1.0, border_color);

    // Update global backgrounds
    visuals.window_fill = window_bg;
    visuals.panel_fill = panel_bg;
    visuals.faint_bg_color = Color32::from_rgb(45, 50, 60);
    visuals.extreme_bg_color = Color32::from_rgb(15, 17, 20); // Deepest dark for inputs

    // Overriding widgets
    visuals.widgets.noninteractive.bg_fill = bg_color;
    visuals.widgets.noninteractive.bg_stroke = thin_stroke;
    visuals.widgets.noninteractive.fg_stroke = Stroke::new(1.0, text_primary);
    
    visuals.widgets.inactive.bg_fill = Color32::from_rgb(40, 45, 55);
    visuals.widgets.inactive.bg_stroke = thin_stroke;
    visuals.widgets.inactive.fg_stroke = Stroke::new(1.0, text_secondary);
    visuals.widgets.inactive.rounding = Rounding::same(6.0);

    visuals.widgets.hovered.bg_fill = Color32::from_rgb(55, 60, 70);
    visuals.widgets.hovered.bg_stroke = Stroke::new(1.0, accent_hover);
    visuals.widgets.hovered.fg_stroke = Stroke::new(1.0, Color32::WHITE);
    visuals.widgets.hovered.rounding = Rounding::same(6.0);

    visuals.widgets.active.bg_fill = accent_color;
    visuals.widgets.active.bg_stroke = Stroke::new(1.0, accent_color);
    visuals.widgets.active.fg_stroke = Stroke::new(1.0, Color32::WHITE);
    visuals.widgets.active.rounding = Rounding::same(6.0);

    // Selection color
    visuals.selection.bg_fill = accent_color;
    visuals.selection.stroke = Stroke::new(1.0, Color32::WHITE);

    // General UI adjustments
    visuals.window_rounding = Rounding::same(8.0);
    visuals.window_shadow = Shadow {
        extrusion: 16.0,
        color: Color32::from_black_alpha(150),
    };
    
    let mut style = (*ctx.style()).clone();
    style.visuals = visuals;
    
    // Spacing
    style.spacing.item_spacing = eframe::egui::vec2(10.0, 10.0);
    style.spacing.button_padding = eframe::egui::vec2(12.0, 6.0);
    style.spacing.window_margin = Margin::same(12.0);
    
    // Better default fonts (make text slightly larger for modern readability)
    for text_style in style.text_styles.values_mut() {
        text_style.size *= 1.15;
    }

    ctx.set_style(style);
}
