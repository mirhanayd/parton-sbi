// Grafik çizim ve görselleştirme

use candle_core::{Device, Error, Result, Tensor};
use plotters::backend::SVGBackend;
use plotters::prelude::*;
use textplots::{Chart, Plot, Shape};

use crate::model::QuarkModel;
use quark_sim::physics::cornell_potential;

/// SVG grafikleri oluştur ve kaydet
#[allow(clippy::too_many_arguments)] // Legacy plotting API retained during DIS isolation.
pub fn plot_results(
    output_dir: &str,
    loss_history: &[(usize, f32)],
    test_distances: &[f32],
    cornell_values: &[f32],
    nn_values: &[f32],
    model: &QuarkModel,
    target_mean: f32,
    target_std: f32,
    device: &Device,
) -> Result<(String, String)> {
    // Grafik 1: Eğitim Kaybı
    let loss_filename = format!("{}/training_loss.svg", output_dir);
    plot_loss_history(&loss_filename, loss_history)?;

    // Grafik 2: Cornell Potansiyeli Karşılaştırması
    let potential_filename = format!("{}/cornell_potential.svg", output_dir);
    plot_potential_comparison(
        &potential_filename,
        test_distances,
        cornell_values,
        nn_values,
        model,
        target_mean,
        target_std,
        device,
    )?;

    Ok((loss_filename, potential_filename))
}

/// Eğitim kaybı grafiği
fn plot_loss_history(filename: &str, loss_history: &[(usize, f32)]) -> Result<()> {
    let filename_clone = filename.to_string();
    let loss_plot = SVGBackend::new(&filename_clone, (800, 600)).into_drawing_area();
    loss_plot.fill(&WHITE).map_err(plot_error)?;

    if loss_history.is_empty() {
        loss_plot
            .draw(&Text::new(
                "Training-loss data unavailable (model loaded without training)",
                (400, 300),
                ("sans-serif", 24).into_font().color(&BLACK),
            ))
            .map_err(plot_error)?;
        loss_plot.present().map_err(plot_error)?;
        println!("   ✓ {} kaydedildi / saved (no training history)", filename);
        return Ok(());
    }

    let max_loss = loss_history
        .iter()
        .map(|(_, l)| *l)
        .fold(f32::NEG_INFINITY, f32::max);
    let min_loss = loss_history
        .iter()
        .map(|(_, l)| *l)
        .fold(f32::INFINITY, f32::min);
    let max_epoch = loss_history
        .iter()
        .map(|(e, _)| *e)
        .max()
        .unwrap_or(1)
        .max(1) as f32;
    let loss_span = (max_loss - min_loss).abs();
    let padding = (loss_span * 0.1).max(1e-6);

    let mut loss_chart = ChartBuilder::on(&loss_plot)
        .caption(
            "Eğitim Kaybı (Training Loss)",
            ("sans-serif", 30).into_font(),
        )
        .margin(10)
        .x_label_area_size(40)
        .y_label_area_size(50)
        .build_cartesian_2d(0f32..max_epoch, (min_loss - padding)..(max_loss + padding))
        .map_err(plot_error)?;

    loss_chart
        .configure_mesh()
        .x_desc("Epoch")
        .y_desc("MSE (GeV²)")
        .draw()
        .map_err(plot_error)?;

    loss_chart
        .draw_series(LineSeries::new(
            loss_history.iter().map(|(e, l)| (*e as f32, *l)),
            &BLUE,
        ))
        .map_err(plot_error)?;

    loss_plot.present().map_err(plot_error)?;
    println!("   ✓ {} kaydedildi / saved", filename);
    Ok(())
}

/// Cornell potansiyeli karşılaştırma grafiği
#[allow(clippy::too_many_arguments)] // Legacy plotting API retained during DIS isolation.
fn plot_potential_comparison(
    filename: &str,
    test_distances: &[f32],
    cornell_values: &[f32],
    nn_values: &[f32],
    model: &QuarkModel,
    target_mean: f32,
    target_std: f32,
    device: &Device,
) -> Result<()> {
    let filename_clone = filename.to_string();
    let potential_plot = SVGBackend::new(&filename_clone, (800, 600)).into_drawing_area();
    potential_plot.fill(&WHITE).map_err(plot_error)?;

    // Daha fazla nokta için düzgün eğri
    let r_values: Vec<f32> = (10..=250).map(|i| i as f32 * 0.01).collect();
    let cornell_curve: Vec<(f32, f32)> = r_values
        .iter()
        .map(|&r| (r, cornell_potential(r)))
        .collect();

    let mut nn_curve = Vec::new();
    for &r in &r_values {
        let test_input = Tensor::from_vec(vec![r, 0.0, 0.0], (1, 3), device)?;
        let prediction_norm = model.forward(&test_input)?;
        let prediction = prediction_norm
            .broadcast_mul(&Tensor::new(&[target_std], device)?)?
            .broadcast_add(&Tensor::new(&[target_mean], device)?)?;
        let pred_value = prediction.to_vec2::<f32>()?[0][0];
        nn_curve.push((r, pred_value));
    }

    let mut potential_chart = ChartBuilder::on(&potential_plot)
        .caption(
            "Cornell Potansiyeli: Teori vs Sinir Ağı",
            ("sans-serif", 30).into_font(),
        )
        .margin(10)
        .x_label_area_size(40)
        .y_label_area_size(60)
        .build_cartesian_2d(0f32..2.5f32, -4f32..3f32)
        .map_err(plot_error)?;

    potential_chart
        .configure_mesh()
        .x_desc("Mesafe r (fm)")
        .y_desc("Potansiyel V(r) (GeV)")
        .draw()
        .map_err(plot_error)?;

    // Teorik Cornell potansiyeli (mavi)
    potential_chart
        .draw_series(LineSeries::new(cornell_curve.iter().copied(), &BLUE))
        .map_err(plot_error)?
        .label("Teorik Cornell")
        .legend(|(x, y)| PathElement::new(vec![(x, y), (x + 20, y)], BLUE));

    // Sinir ağı tahmini (kırmızı)
    potential_chart
        .draw_series(LineSeries::new(nn_curve.iter().copied(), &RED))
        .map_err(plot_error)?
        .label("Sinir Ağı Tahmini")
        .legend(|(x, y)| PathElement::new(vec![(x, y), (x + 20, y)], RED));

    // Test noktaları (yeşil)
    potential_chart
        .draw_series(
            test_distances
                .iter()
                .zip(nn_values.iter())
                .map(|(&r, &v)| Circle::new((r, v), 3, GREEN.filled())),
        )
        .map_err(plot_error)?
        .label("Test Noktaları")
        .legend(|(x, y)| Circle::new((x + 10, y), 3, GREEN.filled()));

    potential_chart
        .configure_series_labels()
        .background_style(WHITE.mix(0.8))
        .border_style(BLACK)
        .draw()
        .map_err(plot_error)?;

    // Hata hesapla ve göster
    let relative_errors: Vec<f32> = cornell_values
        .iter()
        .zip(nn_values.iter())
        .filter_map(|(&theory, &prediction)| {
            (theory.abs() > f32::EPSILON)
                .then_some(((prediction - theory).abs() / theory.abs()) * 100.0)
        })
        .collect();

    if !relative_errors.is_empty() {
        let avg_error = relative_errors.iter().sum::<f32>() / relative_errors.len() as f32;
        potential_chart
            .draw_series(std::iter::once(Text::new(
                format!("Ortalama Hata: {:.2}%", avg_error),
                (1.8, -3.5),
                ("sans-serif", 20).into_font().color(&BLACK),
            )))
            .map_err(plot_error)?;
    }

    potential_plot.present().map_err(plot_error)?;
    println!("   ✓ {} kaydedildi / saved", filename);
    Ok(())
}

fn plot_error(error: impl std::fmt::Display) -> Error {
    Error::Msg(format!("plotting error: {error}"))
}

/// Terminal ASCII grafikleri göster
#[allow(dead_code)]
pub fn show_terminal_plots(
    loss_history: &[(usize, f32)],
    test_distances: &[f32],
    cornell_values: &[f32],
    nn_values: &[f32],
) {
    println!("\n📊 TERMINAL GRAFİKLERİ / TERMINAL PLOTS:\n");

    // Kayıp eğrisi
    println!("=== Eğitim Kayıbı / Training Loss ===");
    let loss_points: Vec<(f32, f32)> = loss_history.iter().map(|(e, l)| (*e as f32, *l)).collect();

    let max_epoch = loss_history.iter().map(|(e, _)| *e).max().unwrap_or(10000) as f32;
    if loss_points.is_empty() {
        println!("Training-loss data unavailable.");
    } else {
        Chart::new(120, 30, 0.0, max_epoch.max(1.0))
            .lineplot(&Shape::Lines(&loss_points))
            .display();
    }

    // Cornell potansiyeli karşılaştırması
    println!("\n=== Cornell Potansiyeli / Cornell Potential (Mavi/Blue=Teori/Theory, Kırmızı/Red=NN) ===");
    let theory_points: Vec<(f32, f32)> = test_distances
        .iter()
        .zip(cornell_values.iter())
        .map(|(&r, &v)| (r, v))
        .collect();

    let nn_points: Vec<(f32, f32)> = test_distances
        .iter()
        .zip(nn_values.iter())
        .map(|(&r, &v)| (r, v))
        .collect();

    let max_distance = test_distances.iter().fold(0.0f32, |a, &b| a.max(b));
    Chart::new(120, 30, 0.0, max_distance)
        .lineplot(&Shape::Lines(&theory_points))
        .lineplot(&Shape::Lines(&nn_points))
        .display();
}

#[cfg(test)]
mod tests {
    use super::plot_loss_history;
    use std::path::PathBuf;
    use std::time::{SystemTime, UNIX_EPOCH};

    struct TemporarySvg(PathBuf);

    impl Drop for TemporarySvg {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }

    #[test]
    fn empty_loss_history_creates_a_labelled_placeholder() -> candle_core::Result<()> {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should be after Unix epoch")
            .as_nanos();
        let output = TemporarySvg(std::env::temp_dir().join(format!(
            "quark_sim_empty_training_loss_{}_{}.svg",
            std::process::id(),
            nonce
        )));
        let output_path = output.0.to_string_lossy().into_owned();

        plot_loss_history(&output_path, &[])?;

        let contents = std::fs::read_to_string(&output.0)
            .map_err(|error| candle_core::Error::Msg(error.to_string()))?;
        assert!(contents.contains("Training-loss data unavailable"));
        Ok(())
    }
}
