// Deep Inelastic Scattering (DIS) Simülasyonu
// Elektronların PROTON (3 Kuarklı Sistem) hedefine saçılması

use crate::model::QuarkModel;
use candle_core::{Device, Result, Tensor};
use plotters::prelude::*;

/// Hedefteki Kuarkların yapısı
#[derive(Clone, Copy, Debug)]
pub struct TargetQuark {
    pub x: f32,
    pub y: f32,
    pub spin: f32, // +0.5 (Yukarı) veya -0.5 (Aşağı)
}

/// Protonun içindeki standart kuark dizilimi (Varsayılan: Up-Up-Down)
pub fn get_proton_quarks() -> Vec<TargetQuark> {
    vec![
        TargetQuark {
            x: 0.0,
            y: 0.8,
            spin: 0.5,
        }, // Üst (Up) -> Spin Yukarı
        TargetQuark {
            x: 0.7,
            y: -0.4,
            spin: 0.5,
        }, // Sağ Alt (Up) -> Spin Yukarı
        TargetQuark {
            x: -0.7,
            y: -0.4,
            spin: -0.5,
        }, // Sol Alt (Down) -> Spin Aşağı
    ]
}

/// Elektron yapısı
#[derive(Clone, Debug)]
pub struct Electron {
    pub x: f32,
    pub y: f32,
    pub vx: f32,
    pub vy: f32,
    pub trajectory: Vec<(f32, f32)>,
    pub impact_parameter: f32,
}

impl Electron {
    pub fn new(x: f32, y: f32, vx: f32, vy: f32) -> Self {
        Self {
            x,
            y,
            vx,
            vy,
            trajectory: vec![(x, y)],
            impact_parameter: y,
        }
    }

    /// Fizik motoru: Bir zaman adımı (dt) ilerle
    #[allow(clippy::too_many_arguments)] // Legacy interactive integrator signature.
    pub fn update_step(
        &mut self,
        model: &QuarkModel,
        targets: &[TargetQuark],
        mean: f32,
        std: f32,
        device: &Device,
        dt: f32,
        force_scale: f32,
    ) -> Result<()> {
        // 1. Potansiyel Alan Kuvveti (Elektriksel)
        let (fx_pot, fy_pot) = calculate_potential_force(
            self.x,
            self.y,
            model,
            targets,
            mean,
            std,
            device,
            force_scale,
        )?;

        // 2. Spin Etkileşimi (Manyetik benzeri basit bir model)
        // Spinler birbirini itiyor veya çekiyor gibi düşünebiliriz.
        // Elektronun spini ile kuark spini arasındaki etkileşimi simüle ediyoruz.
        // Bu, yörüngede ekstra bir bükülme (sapma) yaratır.
        let mut fx_spin = 0.0;
        let mut fy_spin = 0.0;

        for q in targets {
            let dx = self.x - q.x;
            let dy = self.y - q.y;
            let dist_sq = dx * dx + dy * dy;

            if dist_sq < 0.1 {
                continue;
            } // Çok yakınsa sonsuz döngü olmasın

            // Spin kuvveti mesafenin karesiyle ters orantılı olsun (Dipol etkisi gibi)
            // Elektronun spinini varsayılan olarak -0.5 kabul edelim.
            // Aynı yönlü spinler iter, zıt yönlüler çeker (veya tam tersi modele göre).
            let electron_spin = -0.5;
            let interaction = q.spin * electron_spin;

            // Kuvvet vektörü (dairesel saptırma etkisi)
            // Spin etkileşimi genellikle hıza dik etki eder (Lorentz kuvveti gibi)
            let spin_force = interaction / (dist_sq * dist_sq.sqrt()) * 0.1; // 0.1 spin katsayısı

            fx_spin += -dy * spin_force;
            fy_spin += dx * spin_force;
        }

        // Toplam Kuvvet
        let fx = fx_pot + fx_spin;
        let fy = fy_pot + fy_spin;

        // Hız ve Konum Güncelle
        self.vx += fx * dt;
        self.vy += fy * dt;
        self.x += self.vx * dt;
        self.y += self.vy * dt;

        // Yörüngeye ekle
        if let Some(last) = self.trajectory.last() {
            if (self.x - last.0).hypot(self.y - last.1) > 0.05 {
                self.trajectory.push((self.x, self.y));
            }
        }

        Ok(())
    }
}

// Yardımcı: Potansiyel kuvvetini hesapla
#[allow(clippy::too_many_arguments)] // Legacy Cornell force helper signature.
fn calculate_potential_force(
    x: f32,
    y: f32,
    model: &QuarkModel,
    targets: &[TargetQuark],
    mean: f32,
    std: f32,
    device: &Device,
    scale: f32,
) -> Result<(f32, f32)> {
    let epsilon = 0.02;
    let v_curr = get_total_potential(x, y, targets, model, mean, std, device)?;
    let v_x = get_total_potential(x + epsilon, y, targets, model, mean, std, device)?;
    let v_y = get_total_potential(x, y + epsilon, targets, model, mean, std, device)?;

    let fx = -(v_x - v_curr) / epsilon * scale;
    let fy = -(v_y - v_curr) / epsilon * scale;

    Ok((fx, fy))
}

fn get_total_potential(
    x: f32,
    y: f32,
    quarks: &[TargetQuark],
    model: &QuarkModel,
    mean: f32,
    std: f32,
    device: &Device,
) -> Result<f32> {
    let mut total = 0.0;
    for q in quarks {
        let dx = x - q.x;
        let dy = y - q.y;
        let input = Tensor::from_vec(vec![dx, dy, 0.0], (1, 3), device)?;
        let raw = model.forward(&input)?;
        let val = raw
            .broadcast_mul(&Tensor::new(&[std], device)?)?
            .broadcast_add(&Tensor::new(&[mean], device)?)?
            .to_vec2::<f32>()?[0][0];
        total += val;
    }
    Ok(total)
}

// ... ScatteringParams ve diğer kodlar aynı kalabilir ...
pub struct ScatteringParams {
    pub num_electrons: usize,
    pub max_impact_parameter: f32,
    pub initial_velocity: f32,
    pub time_step: f32,
    pub max_steps: usize,
    pub force_scale: f32,
}

impl Default for ScatteringParams {
    fn default() -> Self {
        Self {
            num_electrons: 30,
            max_impact_parameter: 2.5,
            initial_velocity: 0.5,
            time_step: 0.05,
            max_steps: 400,
            force_scale: 0.2,
        }
    }
}

pub fn simulate_scattering(
    model: &QuarkModel,
    params: &ScatteringParams,
    mean: f32,
    std: f32,
    device: &Device,
) -> Result<Vec<Electron>> {
    let mut electrons = Vec::new();
    let targets = get_proton_quarks();

    for i in 0..params.num_electrons {
        let impact = if params.num_electrons == 1 {
            0.0
        } else {
            -params.max_impact_parameter
                + (2.0 * params.max_impact_parameter * i as f32) / (params.num_electrons - 1) as f32
        };
        let mut e = Electron::new(-5.0, impact, params.initial_velocity, 0.0);
        for _ in 0..params.max_steps {
            if e.x > 6.0 || e.y.abs() > 5.0 {
                break;
            }
            e.update_step(
                model,
                &targets,
                mean,
                std,
                device,
                params.time_step,
                params.force_scale,
            )?;
        }
        electrons.push(e);
    }
    Ok(electrons)
}

pub fn plot_scattering(electrons: &[Electron], filename: &str) -> Result<()> {
    let root = SVGBackend::new(filename, (1000, 800)).into_drawing_area();
    root.fill(&WHITE).map_err(plot_error)?;
    let mut chart = ChartBuilder::on(&root)
        .caption("Proton Saçılması", ("sans-serif", 40))
        .margin(15)
        .x_label_area_size(50)
        .y_label_area_size(60)
        .build_cartesian_2d(-6f32..6f32, -4f32..4f32)
        .map_err(plot_error)?;
    chart.configure_mesh().draw().map_err(plot_error)?;

    for q in get_proton_quarks() {
        // Kuarkları spinlerine göre farklı renklerde çiz
        let color = if q.spin > 0.0 { RED } else { CYAN };
        chart
            .draw_series(std::iter::once(Circle::new((q.x, q.y), 8, color.filled())))
            .map_err(plot_error)?;
    }

    for (i, e) in electrons.iter().enumerate() {
        let color = Palette99::pick(i);
        chart
            .draw_series(LineSeries::new(
                e.trajectory.iter().map(|&(x, y)| (x, y)),
                color.stroke_width(2),
            ))
            .map_err(plot_error)?;
    }
    root.present().map_err(plot_error)?;
    Ok(())
}

fn plot_error(error: impl std::fmt::Display) -> candle_core::Error {
    candle_core::Error::Msg(format!("scattering plot error: {error}"))
}
