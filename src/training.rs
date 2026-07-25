// Eğitim ve test fonksiyonları
// Bu dosya, modelin eğitimi, testi ve kaydedilmesi işlemlerini yönetir.

use candle_core::{DType, Device, Result, Tensor};
use candle_nn::{optim::AdamW, Optimizer, VarBuilder, VarMap};
use serde::{Deserialize, Serialize}; // JSON işlemleri için gerekli
use std::fs::File; // Dosya oluşturma için gerekli
use std::io::Write; // Dosyaya yazma için gerekli

use crate::model::QuarkModel;
use quark_sim::physics::cornell_potential;

/// Model konfigürasyonu (Eğitim istatistiklerini saklamak için)
#[derive(Serialize, Deserialize)]
pub struct ModelConfig {
    pub target_mean: f32,
    pub target_std: f32,
}

/// Eğitim verisi oluştur
pub fn generate_training_data(
    n_samples: usize,
    device: &Device,
) -> Result<(Tensor, Tensor, f32, f32)> {
    let mut distances_data = Vec::with_capacity(n_samples * 3);
    let mut potentials_data = Vec::with_capacity(n_samples);

    for _ in 0..n_samples {
        // Rastgele 3D mesafe vektörü (0.05 - 3.0 fm arası)
        let r = rand::random::<f32>() * 2.95 + 0.05;
        let theta = rand::random::<f32>() * 2.0 * std::f32::consts::PI;
        let phi = rand::random::<f32>() * std::f32::consts::PI;

        let dx = r * phi.sin() * theta.cos();
        let dy = r * phi.sin() * theta.sin();
        let dz = r * phi.cos();

        distances_data.push(dx);
        distances_data.push(dy);
        distances_data.push(dz);

        // Cornell potansiyeli ile gerçek hedef hesapla
        potentials_data.push(cornell_potential(r));
    }

    let distances = Tensor::from_vec(distances_data, (n_samples, 3), device)?;
    let target = Tensor::from_vec(potentials_data, (n_samples, 1), device)?;

    // Normalizasyon istatistikleri hesapla
    let target_mean = target.mean_all()?.to_vec0::<f32>()?;
    let target_std = target
        .var_keepdim(0)?
        .sqrt()?
        .mean_all()?
        .to_vec0::<f32>()?
        .max(1e-6);

    Ok((distances, target, target_mean, target_std))
}

/// Modeli eğit
#[allow(clippy::too_many_arguments)] // Legacy training API retained for compatibility.
pub fn train_model(
    model: &QuarkModel,
    optimizer: &mut AdamW,
    distances: &Tensor,
    target: &Tensor,
    target_mean: f32,
    target_std: f32,
    epochs: usize,
    device: &Device,
) -> Result<Vec<(usize, f32)>> {
    let mut loss_history = Vec::new();

    let target_normalized = target
        .broadcast_sub(&Tensor::new(&[target_mean], device)?)?
        .broadcast_div(&Tensor::new(&[target_std], device)?)?;

    println!("\n🎓 Eğitim başlıyor / Starting training...");
    println!("   • Epoch sayısı / Epochs: {}", epochs);
    println!(
        "   • Öğrenme oranı / Learning rate: {:.4}",
        optimizer.learning_rate()
    );
    println!("   • Hedef ortalama / Target mean: {:.4} GeV", target_mean);
    println!("   • Hedef std sapma / Target std: {:.4} GeV\n", target_std);

    for epoch in 0..epochs {
        let predictions = model.forward(distances)?;
        let loss = predictions.sub(&target_normalized)?.sqr()?.mean_all()?;

        // NaN kontrolü
        let loss_check = loss.to_vec0::<f32>()?;
        if loss_check.is_nan() || loss_check.is_infinite() {
            eprintln!(
                "❌ HATA: Loss NaN veya Inf oldu (epoch {}). Eğitim durduruluyor.",
                epoch
            );
            break;
        }

        optimizer.backward_step(&loss)?;

        if epoch % 100 == 0 {
            let real_loss = predictions
                .broadcast_mul(&Tensor::new(&[target_std], device)?)?
                .broadcast_add(&Tensor::new(&[target_mean], device)?)?
                .sub(target)?
                .sqr()?
                .mean_all()?;
            let loss_val = real_loss.to_vec0::<f32>()?;
            loss_history.push((epoch, loss_val));

            if epoch % 500 == 0 {
                println!("Epoch {}: Kayıp / Loss (MSE) = {:.6} GeV²", epoch, loss_val);
            }
        }
    }

    println!("\n✅ Eğitim tamamlandı / Training completed!");
    Ok(loss_history)
}

/// Result arrays returned by the legacy Cornell model test.
pub type ModelTestResults = (
    Vec<f32>,
    Vec<f32>,
    Vec<f32>,
    Vec<(f32, f32)>,
    Vec<(f32, f32)>,
);

/// Test verisi üret ve değerlendir
pub fn test_model(
    model: &QuarkModel,
    target_mean: f32,
    target_std: f32,
    device: &Device,
) -> Result<ModelTestResults> {
    println!("\n🧪 Test başlıyor / Starting test...");

    let test_distances_vals = vec![0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.3, 1.6, 2.0, 2.4, 2.8];
    let mut cornell_values = Vec::new();
    let mut nn_values = Vec::new();

    println!("\n┌───────────────┬──────────────┬──────────────┬────────────┐");
    println!("│ Mesafe/Dist  │ Cornell (GeV)│    NN (GeV)  │ Hata/Error │");
    println!("├───────────────┼──────────────┼──────────────┼────────────┤");

    for &r in &test_distances_vals {
        let test_input = Tensor::from_vec(vec![r, 0.0, 0.0], (1, 3), device)?;
        let prediction_norm = model.forward(&test_input)?;
        let prediction = prediction_norm
            .broadcast_mul(&Tensor::new(&[target_std], device)?)?
            .broadcast_add(&Tensor::new(&[target_mean], device)?)?;
        let pred_value = prediction.to_vec2::<f32>()?[0][0];

        let true_value = cornell_potential(r);
        let error = ((pred_value - true_value).abs() / true_value.abs()) * 100.0;

        println!(
            "│ {:13.2} │ {:12.6} │ {:12.6} │ {:10.2}% │",
            r, true_value, pred_value, error
        );

        cornell_values.push(true_value);
        nn_values.push(pred_value);
    }

    println!("└───────────────┴──────────────┴──────────────┴────────────┘");

    // Grafik için ek veri noktaları
    let r_values: Vec<f32> = (10..=250).map(|i| i as f32 * 0.01).collect();

    let potential_points_theory: Vec<(f32, f32)> = r_values
        .iter()
        .map(|&r| (r, cornell_potential(r)))
        .collect();

    let mut potential_points_nn = Vec::new();
    for &r in &r_values {
        let test_input = Tensor::from_vec(vec![r, 0.0, 0.0], (1, 3), device)?;
        let prediction_norm = model.forward(&test_input)?;
        let prediction = prediction_norm
            .broadcast_mul(&Tensor::new(&[target_std], device)?)?
            .broadcast_add(&Tensor::new(&[target_mean], device)?)?;
        let pred_value = prediction.to_vec2::<f32>()?[0][0];
        potential_points_nn.push((r, pred_value));
    }

    Ok((
        test_distances_vals,
        cornell_values,
        nn_values,
        potential_points_theory,
        potential_points_nn,
    ))
}

/// Model ve optimizer oluştur
pub fn create_model_and_optimizer(
    device: &Device,
    learning_rate: f64,
) -> Result<(QuarkModel, AdamW, VarMap)> {
    let varmap = VarMap::new();
    let vs = VarBuilder::from_varmap(&varmap, DType::F32, device);
    let model = QuarkModel::new(vs.clone())?;

    // AdamW optimizer parametreleri
    let params = candle_nn::optim::ParamsAdamW {
        lr: learning_rate,
        beta1: 0.9,
        beta2: 0.999,
        eps: 1e-8,
        weight_decay: 0.01,
    };
    let optimizer = candle_nn::optim::AdamW::new(varmap.all_vars(), params)?;

    Ok((model, optimizer, varmap))
}

/// Modeli VE Konfigürasyonu (İstatistikleri) kaydet
pub fn save_model_with_config(
    varmap: &VarMap,
    model_path: &str,
    config_path: &str,
    mean: f32,
    std: f32,
) -> Result<()> {
    println!("\n💾 Model ve Konfigürasyon kaydediliyor...");

    // 1. Ağırlıkları kaydet (.safetensors)
    varmap.save(model_path)?;
    println!("   ✓ Ağırlıklar: {}", model_path);

    // 2. İstatistikleri kaydet (.json)
    let config = ModelConfig {
        target_mean: mean,
        target_std: std,
    };
    // JSON oluştur
    let json = serde_json::to_string_pretty(&config).map_err(candle_core::Error::wrap)?;
    // Dosyaya yaz
    let mut file = File::create(config_path).map_err(candle_core::Error::wrap)?;
    file.write_all(json.as_bytes())
        .map_err(candle_core::Error::wrap)?;

    println!("   ✓ Konfigürasyon: {}", config_path);
    Ok(())
}

/// Modeli VE Konfigürasyonu yükle
pub fn load_model_with_config(
    model_path: &str,
    config_path: &str,
    device: &Device,
) -> Result<(QuarkModel, VarMap, f32, f32)> {
    println!("\n📂 Model ve Konfigürasyon yükleniyor...");

    // 1. Konfigürasyonu oku (Mean ve Std değerlerini geri getir)
    let file = File::open(config_path).map_err(candle_core::Error::wrap)?;
    let config: ModelConfig = serde_json::from_reader(file).map_err(candle_core::Error::wrap)?;
    println!(
        "   ✓ İstatistikler yüklendi: Mean={:.4}, Std={:.4}",
        config.target_mean, config.target_std
    );

    // 2. Mimarinin değişkenlerini VarMap'e kaydet, ardından ağırlıkları yükle.
    // VarMap yalnızca önceden kayıtlı değişkenleri yüklediği için bu sıra önemlidir.
    let mut varmap = VarMap::new();
    let vs = VarBuilder::from_varmap(&varmap, DType::F32, device);
    let model = QuarkModel::new(vs)?;
    varmap.load(model_path)?;
    println!("   ✓ Ağırlıklar yüklendi: {}", model_path);

    // Modeli ve ESKİ istatistikleri döndür
    Ok((model, varmap, config.target_mean, config.target_std))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;
    use std::time::{SystemTime, UNIX_EPOCH};

    struct TemporaryModelFiles {
        model: PathBuf,
        config: PathBuf,
    }

    impl Drop for TemporaryModelFiles {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.model);
            let _ = std::fs::remove_file(&self.config);
        }
    }

    #[test]
    fn saved_parameters_round_trip_with_matching_predictions() -> Result<()> {
        let device = Device::Cpu;
        let first_varmap = VarMap::new();
        let first_builder = VarBuilder::from_varmap(&first_varmap, DType::F32, &device);
        let first_model = QuarkModel::new(first_builder)?;
        let input = Tensor::from_vec(vec![0.15_f32, -0.25, 0.35, 0.8, 0.1, -0.4], (2, 3), &device)?;
        let first_predictions = first_model.forward(&input)?.to_vec2::<f32>()?;

        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(candle_core::Error::wrap)?
            .as_nanos();
        let base = format!(
            "quark_sim_model_round_trip_{}_{}",
            std::process::id(),
            unique
        );
        let files = TemporaryModelFiles {
            model: std::env::temp_dir().join(format!("{base}.safetensors")),
            config: std::env::temp_dir().join(format!("{base}_config.json")),
        };
        let expected_mean = 1.25;
        let expected_std = 0.75;
        save_model_with_config(
            &first_varmap,
            &files.model.to_string_lossy(),
            &files.config.to_string_lossy(),
            expected_mean,
            expected_std,
        )?;

        let (second_model, _second_varmap, restored_mean, restored_std) = load_model_with_config(
            &files.model.to_string_lossy(),
            &files.config.to_string_lossy(),
            &device,
        )?;
        assert_eq!(restored_mean, expected_mean);
        assert_eq!(restored_std, expected_std);
        let second_predictions = second_model.forward(&input)?.to_vec2::<f32>()?;

        for (first, second) in first_predictions
            .iter()
            .flatten()
            .zip(second_predictions.iter().flatten())
        {
            let difference = (first - second).abs();
            assert!(
                difference <= 1e-6,
                "prediction mismatch after reload: {first} vs {second} (|Δ|={difference})"
            );
        }

        Ok(())
    }
}
