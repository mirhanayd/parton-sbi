//! Training pipeline for the neural network surrogate.
//!
//! Generates datasets by querying APFEL++, handles train/validation/test splits,
//! and trains the `candle_core` surrogate model.

use std::error::Error;
use std::fs;
use std::path::Path;

use candle_core::{DType, Device, Tensor};
use candle_nn::{optim::AdamW, Optimizer, VarBuilder, VarMap};
use rand::seq::SliceRandom;
use rand::rngs::StdRng;
use rand::SeedableRng;

use super::apfel::ApfelStructureFunctionProvider;
use super::structure_function_provider::{
    PerturbativeOrder, StructureFunctionProvider, StructureFunctionRequest,
};
use super::surrogate::{SurrogateConfig, SurrogateModel};

/// Dataset row representing one kinematic point and its target values.
#[derive(Debug, Clone)]
pub struct SurrogateDataPoint {
    // Inputs
    pub x: f64,
    pub q2: f64,
    pub mu_f_ratio: f64,
    pub mu_r_ratio: f64,
    // Targets
    pub f2: f64,
    pub fl: f64,
    pub xf3: f64,
}

/// Generate a dataset over a grid using APFEL++.
pub fn generate_dataset(
    provider: &ApfelStructureFunctionProvider,
    pdf_set: &str,
    pdf_member: i32,
    order: PerturbativeOrder,
) -> Result<Vec<SurrogateDataPoint>, Box<dyn Error>> {
    println!("Generating dataset using APFEL++...");
    let mut data = Vec::new();

    // Logarithmic grid for x and Q²
    let x_vals = log_space(1e-5, 0.8, 5);
    let q2_vals = log_space(3.5, 10000.0, 5);
    let mu_f_ratios = [0.5, 1.0, 2.0];
    let mu_r_ratios = [0.5, 1.0, 2.0];

    let total = x_vals.len() * q2_vals.len() * mu_f_ratios.len() * mu_r_ratios.len();
    let mut count = 0;

    for &x in &x_vals {
        for &q2 in &q2_vals {
            for &mu_f in &mu_f_ratios {
                for &mu_r in &mu_r_ratios {
                    let mut req = StructureFunctionRequest::electromagnetic_nc(
                        x, q2, order, pdf_set, pdf_member,
                    );
                    req.mu_f_over_q = mu_f;
                    req.mu_r_over_q = mu_r;

                    match provider.evaluate(&req) {
                        Ok(res) => {
                            data.push(SurrogateDataPoint {
                                x,
                                q2,
                                mu_f_ratio: mu_f,
                                mu_r_ratio: mu_r,
                                f2: res.f2,
                                fl: res.fl,
                                xf3: res.xf3,
                            });
                        }
                        Err(e) => {
                            eprintln!("APFEL++ error at x={x}, Q2={q2}: {e}");
                        }
                    }

                    count += 1;
                    if count % 1000 == 0 {
                        println!("  Generated {}/{} points...", count, total);
                    }
                }
            }
        }
    }

    println!("Dataset generated with {} valid points.", data.len());
    Ok(data)
}

fn log_space(start: f64, end: f64, n: usize) -> Vec<f64> {
    let log_start = start.log10();
    let log_end = end.log10();
    let step = (log_end - log_start) / (n as f64 - 1.0);
    (0..n)
        .map(|i| 10_f64.powf(log_start + step * i as f64))
        .collect()
}

/// Train the surrogate model and save it to the specified directory.
pub fn train_and_save_surrogate(
    data: Vec<SurrogateDataPoint>,
    output_dir: impl AsRef<Path>,
    pdf_set: String,
    pdf_member: i32,
    order: PerturbativeOrder,
) -> Result<(), Box<dyn Error>> {
    let dir = output_dir.as_ref();
    fs::create_dir_all(dir)?;

    let n_total = data.len();
    if n_total < 100 {
        return Err("Not enough data to train surrogate".into());
    }

    // Determine domain bounds
    let mut x_min = f64::MAX;
    let mut x_max = f64::MIN;
    let mut q2_min = f64::MAX;
    let mut q2_max = f64::MIN;
    for pt in &data {
        x_min = x_min.min(pt.x);
        x_max = x_max.max(pt.x);
        q2_min = q2_min.min(pt.q2);
        q2_max = q2_max.max(pt.q2);
    }

    // Split data into train (70%), val (15%), test (15%)
    let mut rng = StdRng::seed_from_u64(42);
    let mut indices: Vec<usize> = (0..n_total).collect();
    indices.shuffle(&mut rng);

    let n_train = (n_total as f64 * 0.7) as usize;
    let n_val = (n_total as f64 * 0.15) as usize;

    let train_indices = &indices[0..n_train];
    let val_indices = &indices[n_train..n_train + n_val];
    let test_indices = &indices[n_train + n_val..];

    // Compute normalization statistics on training set
    let mut input_sum = [0.0f64; 4];
    let mut input_sq_sum = [0.0f64; 4];
    let mut target_sum = [0.0f64; 3];
    let mut target_sq_sum = [0.0f64; 3];

    for &idx in train_indices {
        let pt = &data[idx];
        let inputs = [
            pt.x.log10(),
            pt.q2.log10(),
            pt.mu_f_ratio,
            pt.mu_r_ratio,
        ];
        let targets = [pt.f2.max(1e-10).log10(), pt.fl, pt.xf3];

        for i in 0..4 {
            input_sum[i] += inputs[i];
            input_sq_sum[i] += inputs[i] * inputs[i];
        }
        for i in 0..3 {
            target_sum[i] += targets[i];
            target_sq_sum[i] += targets[i] * targets[i];
        }
    }

    let n_train_f = n_train as f64;
    let mut input_mean = [0.0f32; 4];
    let mut input_std = [0.0f32; 4];
    for i in 0..4 {
        let mean = input_sum[i] / n_train_f;
        let var = (input_sq_sum[i] / n_train_f) - mean * mean;
        input_mean[i] = mean as f32;
        input_std[i] = var.max(1e-12).sqrt() as f32;
    }

    let mut target_mean = [0.0f32; 3];
    let mut target_std = [0.0f32; 3];
    for i in 0..3 {
        let mean = target_sum[i] / n_train_f;
        let var = (target_sq_sum[i] / n_train_f) - mean * mean;
        target_mean[i] = mean as f32;
        target_std[i] = var.max(1e-12).sqrt() as f32;
    }

    // Setup device and model
    let device = Device::Cpu;
    let mut varmap = VarMap::new();
    let vs = VarBuilder::from_varmap(&varmap, DType::F32, &device);
    let model = SurrogateModel::new(vs)?;

    let mut optimizer = AdamW::new_lr(varmap.all_vars(), 0.001)?;

    // Prepare tensors
    let train_x = build_input_tensor(&data, train_indices, &input_mean, &input_std, &device)?;
    let train_y = build_target_tensor(&data, train_indices, &target_mean, &target_std, &device)?;
    let val_x = build_input_tensor(&data, val_indices, &input_mean, &input_std, &device)?;
    let val_y = build_target_tensor(&data, val_indices, &target_mean, &target_std, &device)?;

    println!("\nTraining surrogate...");
    println!("Train set: {}, Val set: {}, Test set: {}", train_indices.len(), val_indices.len(), test_indices.len());

    let epochs = 2000;
    let mut best_val_loss = f32::MAX;
    let mut best_epoch = 0;
    let patience = 200;
    let mut wait = 0;

    for epoch in 0..epochs {
        // Forward pass
        let pred = model.forward(&train_x)?;
        let loss = pred.sub(&train_y)?.sqr()?.mean_all()?;
        
        optimizer.backward_step(&loss)?;

        if epoch % 50 == 0 || epoch == epochs - 1 {
            let val_pred = model.forward(&val_x)?;
            let val_loss = val_pred.sub(&val_y)?.sqr()?.mean_all()?.to_vec0::<f32>()?;
            let train_loss = loss.to_vec0::<f32>()?;

            println!("Epoch {epoch:4}: Train MSE = {train_loss:.4e}, Val MSE = {val_loss:.4e}");

            if val_loss < best_val_loss {
                best_val_loss = val_loss;
                best_epoch = epoch;
                wait = 0;
                varmap.save(dir.join("model.safetensors"))?;
            } else {
                wait += 50;
                if wait >= patience {
                    println!("Early stopping at epoch {epoch}. Best epoch was {best_epoch}.");
                    break;
                }
            }
        }
    }

    // Load best model to evaluate test set
    varmap.load(dir.join("model.safetensors"))?;
    let test_x = build_input_tensor(&data, test_indices, &input_mean, &input_std, &device)?;
    let test_pred = model.forward(&test_x)?;
    let test_pred_vec = test_pred.to_vec2::<f32>()?;

    let mut max_rel_error = 0.0f32;
    for (i, &idx) in test_indices.iter().enumerate() {
        let pt = &data[idx];
        let f2_log_norm = test_pred_vec[i][0];
        let f2_log = f2_log_norm * target_std[0] + target_mean[0];
        let f2_pred = 10_f32.powf(f2_log);
        
        let target_f2 = pt.f2 as f32;
        let rel_err = (f2_pred - target_f2).abs() / target_f2.max(1e-12);
        max_rel_error = max_rel_error.max(rel_err);
    }

    println!("Test Set Max Relative Error on F2: {:.2}%", max_rel_error * 100.0);

    // Save config
    let config = SurrogateConfig {
        source_backend: "apfel".to_string(),
        pdf_set,
        pdf_member,
        order,
        x_min,
        x_max,
        q2_min,
        q2_max,
        mu_f_ratio_min: 0.5,
        mu_f_ratio_max: 2.0,
        mu_r_ratio_min: 0.5,
        mu_r_ratio_max: 2.0,
        input_mean: input_mean.to_vec(),
        input_std: input_std.to_vec(),
        target_mean: target_mean.to_vec(),
        target_std: target_std.to_vec(),
        validation_mse: best_val_loss,
        test_max_rel_error: max_rel_error,
    };

    fs::write(
        dir.join("model_config.json"),
        serde_json::to_string_pretty(&config)?,
    )?;

    println!("Surrogate successfully trained and saved to {}", dir.display());
    Ok(())
}

fn build_input_tensor(
    data: &[SurrogateDataPoint],
    indices: &[usize],
    mean: &[f32; 4],
    std: &[f32; 4],
    device: &Device,
) -> Result<Tensor, Box<dyn Error>> {
    let mut flat = Vec::with_capacity(indices.len() * 4);
    for &idx in indices {
        let pt = &data[idx];
        let inputs = [
            pt.x.log10() as f32,
            pt.q2.log10() as f32,
            pt.mu_f_ratio as f32,
            pt.mu_r_ratio as f32,
        ];
        for i in 0..4 {
            flat.push((inputs[i] - mean[i]) / std[i]);
        }
    }
    Ok(Tensor::from_vec(flat, (indices.len(), 4), device)?)
}

fn build_target_tensor(
    data: &[SurrogateDataPoint],
    indices: &[usize],
    mean: &[f32; 3],
    std: &[f32; 3],
    device: &Device,
) -> Result<Tensor, Box<dyn Error>> {
    let mut flat = Vec::with_capacity(indices.len() * 3);
    for &idx in indices {
        let pt = &data[idx];
        let targets = [
            pt.f2.max(1e-10).log10() as f32,
            pt.fl as f32,
            pt.xf3 as f32,
        ];
        for i in 0..3 {
            flat.push((targets[i] - mean[i]) / std[i]);
        }
    }
    Ok(Tensor::from_vec(flat, (indices.len(), 3), device)?)
}
