//! Neural network surrogate for structure functions.
//!
//! Provides a `candle_core`-based MLP trained on deterministically sampled
//! outputs from APFEL++. The surrogate enforces strict physical phase-space
//! limits and cannot be used as exact ground truth.

use std::error::Error;
use std::fs;
use std::path::Path;

use candle_core::{DType, Device, Result as CandleResult, Tensor};
use candle_nn::{Linear, Module, VarBuilder, VarMap};
use serde::{Deserialize, Serialize};

use super::structure_function_provider::{
    PerturbativeOrder, StructureFunctionBackend, StructureFunctionMetadata,
    StructureFunctionProvider, StructureFunctionProviderError,
    StructureFunctionRequest, StructureFunctionResult, PHOTON_EXCHANGE_MODE,
};

/// Name of the scheme used by the surrogate.
pub const SURROGATE_SCHEME: &str = "surrogate_nlo";

/// Model configuration stored with the `.safetensors` file.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurrogateConfig {
    /// APFEL++ or underlying provider backend name.
    pub source_backend: String,
    /// PDF set and member used for training.
    pub pdf_set: String,
    pub pdf_member: i32,
    pub order: PerturbativeOrder,

    /// Domain limit for x.
    pub x_min: f64,
    pub x_max: f64,
    /// Domain limit for Q² [GeV²].
    pub q2_min: f64,
    pub q2_max: f64,
    /// Domain limit for μ_F / Q.
    pub mu_f_ratio_min: f64,
    pub mu_f_ratio_max: f64,
    /// Domain limit for μ_R / Q.
    pub mu_r_ratio_min: f64,
    pub mu_r_ratio_max: f64,

    /// Input normalizations: mean and standard deviation.
    /// Vector order: [log10(x), log10(Q²), μ_F/Q, μ_R/Q]
    pub input_mean: Vec<f32>,
    pub input_std: Vec<f32>,

    /// Target normalizations: mean and standard deviation.
    /// Vector order: [log10(F₂), FL, xF₃]
    pub target_mean: Vec<f32>,
    pub target_std: Vec<f32>,

    /// Last known validation MSE.
    pub validation_mse: f32,
    /// Last known test max relative error.
    pub test_max_rel_error: f32,
}

impl SurrogateConfig {
    /// Check if a request is safely inside the training domain.
    pub fn is_in_domain(&self, req: &StructureFunctionRequest) -> bool {
        req.x >= self.x_min
            && req.x <= self.x_max
            && req.q2 >= self.q2_min
            && req.q2 <= self.q2_max
            && req.mu_f_over_q >= self.mu_f_ratio_min
            && req.mu_f_over_q <= self.mu_f_ratio_max
            && req.mu_r_over_q >= self.mu_r_ratio_min
            && req.mu_r_over_q <= self.mu_r_ratio_max
            && req.pdf_set == self.pdf_set
            && req.pdf_member == self.pdf_member
            && req.order == self.order
    }
}

/// A multilayer perceptron mapping 4 inputs to 3 outputs.
pub struct SurrogateModel {
    layer1: Linear,
    layer2: Linear,
    layer3: Linear,
    layer4: Linear,
}

impl SurrogateModel {
    pub const INPUT_SIZE: usize = 4;
    pub const HIDDEN1_SIZE: usize = 128;
    pub const HIDDEN2_SIZE: usize = 64;
    pub const HIDDEN3_SIZE: usize = 32;
    pub const OUTPUT_SIZE: usize = 3;

    pub fn new(vs: VarBuilder) -> CandleResult<Self> {
        let layer1 = candle_nn::linear(Self::INPUT_SIZE, Self::HIDDEN1_SIZE, vs.pp("layer1"))?;
        let layer2 = candle_nn::linear(Self::HIDDEN1_SIZE, Self::HIDDEN2_SIZE, vs.pp("layer2"))?;
        let layer3 = candle_nn::linear(Self::HIDDEN2_SIZE, Self::HIDDEN3_SIZE, vs.pp("layer3"))?;
        let layer4 = candle_nn::linear(Self::HIDDEN3_SIZE, Self::OUTPUT_SIZE, vs.pp("layer4"))?;

        Ok(Self {
            layer1,
            layer2,
            layer3,
            layer4,
        })
    }

    pub fn forward(&self, xs: &Tensor) -> CandleResult<Tensor> {
        let xs = self.layer1.forward(xs)?;
        let xs = xs.relu()?;
        let xs = self.layer2.forward(&xs)?;
        let xs = xs.relu()?;
        let xs = self.layer3.forward(&xs)?;
        let xs = xs.relu()?;
        let xs = self.layer4.forward(&xs)?;
        Ok(xs)
    }
}

/// A full structure-function provider relying on the surrogate model.
pub struct SurrogateProvider {
    model: SurrogateModel,
    config: SurrogateConfig,
    device: Device,
}

impl SurrogateProvider {
    pub fn load(model_dir: impl AsRef<Path>) -> Result<Self, Box<dyn Error>> {
        let dir = model_dir.as_ref();
        let config_path = dir.join("model_config.json");
        let weights_path = dir.join("model.safetensors");

        if !config_path.exists() {
            return Err(format!("Model config not found at {}", config_path.display()).into());
        }
        if !weights_path.exists() {
            return Err(format!("Model weights not found at {}", weights_path.display()).into());
        }

        let config_json = fs::read_to_string(config_path)?;
        let config: SurrogateConfig = serde_json::from_str(&config_json)?;

        let device = Device::Cpu;
        let mut varmap = VarMap::new();
        varmap.load(&weights_path)?;
        let vs = VarBuilder::from_varmap(&varmap, DType::F32, &device);
        let model = SurrogateModel::new(vs)?;

        Ok(Self {
            model,
            config,
            device,
        })
    }

    pub fn config(&self) -> &SurrogateConfig {
        &self.config
    }
}

impl StructureFunctionProvider for SurrogateProvider {
    fn evaluate(
        &self,
        request: &StructureFunctionRequest,
    ) -> Result<StructureFunctionResult, StructureFunctionProviderError> {
        request.validate()?;

        if !self.config.is_in_domain(request) {
            return Err(StructureFunctionProviderError::OutOfDomain {
                x: request.x,
                q2: request.q2,
                reason: format!(
                    "Out of training domain: x=[{:.1e}, {:.1e}], Q2=[{:.1}, {:.1}], \
                     muF_ratio=[{:.1}, {:.1}], muR_ratio=[{:.1}, {:.1}]. Surrogate cannot extrapolate.",
                    self.config.x_min,
                    self.config.x_max,
                    self.config.q2_min,
                    self.config.q2_max,
                    self.config.mu_f_ratio_min,
                    self.config.mu_f_ratio_max,
                    self.config.mu_r_ratio_min,
                    self.config.mu_r_ratio_max
                ),
            });
        }

        // Prepare input: [log10(x), log10(Q²), mu_F/Q, mu_R/Q]
        let x_log = request.x.log10() as f32;
        let q2_log = request.q2.log10() as f32;
        let muf = request.mu_f_over_q as f32;
        let mur = request.mu_r_over_q as f32;

        let input_raw = [x_log, q2_log, muf, mur];
        let mut input_norm = [0.0f32; 4];
        for i in 0..4 {
            input_norm[i] = (input_raw[i] - self.config.input_mean[i]) / self.config.input_std[i];
        }

        let input_tensor = Tensor::from_vec(input_norm.to_vec(), (1, 4), &self.device)
            .map_err(|e| StructureFunctionProviderError::EvaluationFailed(e.to_string()))?;

        let output_tensor = self
            .model
            .forward(&input_tensor)
            .map_err(|e| StructureFunctionProviderError::EvaluationFailed(e.to_string()))?;

        let outputs = output_tensor
            .to_vec2::<f32>()
            .map_err(|e| StructureFunctionProviderError::EvaluationFailed(e.to_string()))?[0]
            .clone();

        // Outputs are: [log10(F2), FL, xF3] (normalized)
        let f2_log_norm = outputs[0];
        let fl_norm = outputs[1];
        let xf3_norm = outputs[2];

        let f2_log = f2_log_norm * self.config.target_std[0] + self.config.target_mean[0];
        let fl = fl_norm * self.config.target_std[1] + self.config.target_mean[1];
        let xf3 = xf3_norm * self.config.target_std[2] + self.config.target_mean[2];

        // Ensure non-negativity for F2 (since it's 10^f2_log it's always positive)
        let f2 = 10_f64.powf(f2_log as f64);

        Ok(StructureFunctionResult {
            f2,
            fl: fl as f64,
            xf3: xf3 as f64,
            metadata: StructureFunctionMetadata {
                backend: StructureFunctionBackend::Surrogate,
                apfelxx_version: None,
                lhapdf_version: None,
                pdf_set: self.config.pdf_set.clone(),
                pdf_member: self.config.pdf_member,
                pdf_order_qcd: 0,
                pdf_data_version: 0,
                order: self.config.order,
                process: request.process,
                projectile: request.projectile,
                target: request.target,
                mu_f_over_q: request.mu_f_over_q,
                mu_r_over_q: request.mu_r_over_q,
                scheme: SURROGATE_SCHEME.to_string(),
                electromagnetic_mode: PHOTON_EXCHANGE_MODE.to_string(),
                os_arch: None,
                rust_version: None,
                git_commit: None,
                git_dirty: None,
                pythia_version: None,
                hepmc_version: None,
                python_env_hash: None,
            },
        })
    }
}
