// Sinir ağı modeli

use candle_core::{Result, Tensor};
use candle_nn::{Linear, Module, VarBuilder};

// SİMÜLASYON PARAMETRELERİ (Yüksek Kapasite + AdamW)
pub const INPUT_SIZE: usize = 3; // Girdi: x, y, z mesafeleri
pub const HIDDEN1_SIZE: usize = 256; // İlk gizli katman (128 → 256)
pub const HIDDEN2_SIZE: usize = 128; // İkinci gizli katman (64 → 128)
pub const HIDDEN3_SIZE: usize = 64; // Üçüncü gizli katman (32 → 64)
pub const OUTPUT_SIZE: usize = 1; // Çıktı: Potansiyel Enerji

/// Kuark potansiyelini tahmin eden sinir ağı modeli
/// 4 katmanlı derin ağ: 3 -> 256 -> 128 -> 64 -> 1
pub struct QuarkModel {
    layer1: Linear,
    layer2: Linear,
    layer3: Linear,
    layer4: Linear,
}

impl QuarkModel {
    /// Yeni model oluştur
    pub fn new(vs: VarBuilder) -> Result<Self> {
        let layer1 = candle_nn::linear(INPUT_SIZE, HIDDEN1_SIZE, vs.pp("ln1"))?;
        let layer2 = candle_nn::linear(HIDDEN1_SIZE, HIDDEN2_SIZE, vs.pp("ln2"))?;
        let layer3 = candle_nn::linear(HIDDEN2_SIZE, HIDDEN3_SIZE, vs.pp("ln3"))?;
        let layer4 = candle_nn::linear(HIDDEN3_SIZE, OUTPUT_SIZE, vs.pp("ln4"))?;
        Ok(Self {
            layer1,
            layer2,
            layer3,
            layer4,
        })
    }

    /// İleri besleme (Forward Pass)
    pub fn forward(&self, xs: &Tensor) -> Result<Tensor> {
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
