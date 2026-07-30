//! D1C-B admission contract for a signed persistent-APFEL PYTHIA facade.
//!
//! PYTHIA 8.312 exposes `PDF::xf`, `PDF::xfVal`, and `PDF::xfSea` as
//! non-virtual methods and clamps their stored values with `max(0, value)`.
//! `BeamParticle` reaches those methods through `shared_ptr<PDF>`. The
//! installed public extension boundary therefore cannot transport the
//! accepted signed APFEL values bit-for-bit. This module records that
//! incompatibility and refuses to publish a facade or initialize PYTHIA.

use std::collections::BTreeMap;
use std::error::Error;
use std::ffi::{c_char, CStr};
use std::fmt;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub const PYTHIA_PDF_FACADE_AUDIT_SCHEMA: &str =
    "partonsbi.d1c.pythia-pdf-facade.compatibility-audit.v1";
pub const PYTHIA_PDF_FACADE_ABI_VERSION: &str = "partonsbi_pythia_pdf_facade_admission_abi_v1";
pub const PYTHIA_PDF_FACADE_POLICY_VERSION: &str =
    "persistent_apfel_signed_pythia_facade_candidate_v1";
pub const PYTHIA_PDF_SCALE_POLICY_VERSION: &str = "pythia_q2_sqrt_once_to_apfel_q_gev_v1";
pub const PYTHIA_PDF_VALENCE_SEA_POLICY_VERSION: &str = "signed_q_minus_qbar_and_signed_qbar_v1";
pub const PYTHIA_PDF_SIGN_POLICY_VERSION: &str = "signed_binary64_no_clipping_v1";
pub const PYTHIA_PDF_POINTER_POLICY_VERSION: &str =
    "all_proton_slots_instrumented_or_disabled_fail_closed_v1";
pub const PYTHIA_PDF_PROVENANCE_SCHEMA: &str = "partonsbi.d1c.pythia-pdf-query-provenance.v1";
pub const PYTHIA_PDF_PROVENANCE_CAPACITY: usize = 4096;
pub const D1C_B_STAGE: &str = "D1C_B_FACADE_ADMISSION_BLOCKED";
pub const D1C_B_PYTHIA_INITIALIZED: bool = false;
pub const D1C_B_PYTHIA_NEXT_EXECUTED: bool = false;
pub const D1C_B_ATTEMPTED_EVENTS: u64 = 0;
pub const D1C_B_SUCCESSFUL_EVENTS: u64 = 0;
pub const D1C_B_SAVED_EVENTS: u64 = 0;
pub const D1C_B_RUNTIME_CONSUMER_ATTRIBUTION_COMPLETE: bool = false;
pub const D1C_B_CONSUMER_ENVELOPE_RESULT_AVAILABLE: bool = false;
pub const D1C_B_SCIENTIFIC_STUDY_RESULT_AVAILABLE: bool = false;
pub const D1C_B_D2_AUTHORIZED: bool = false;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PythiaPdfCompatibilityDecision {
    IncompatibleNonvirtualPositivityClipping,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct PythiaSignedBoundaryEvidence {
    pub pythia_version_integer: i32,
    pub raw_inclusive: f64,
    pub base_inclusive: f64,
    pub raw_valence: f64,
    pub base_valence: f64,
    pub raw_sea: f64,
    pub base_sea: f64,
}

impl PythiaSignedBoundaryEvidence {
    pub fn demonstrates_clipping(self) -> bool {
        self.pythia_version_integer == 8312
            && self.raw_inclusive.to_bits() == (-1.0_f64).to_bits()
            && self.base_inclusive.to_bits() == 0.0_f64.to_bits()
            && self.raw_valence.to_bits() == (-1.5_f64).to_bits()
            && self.base_valence.to_bits() == 0.0_f64.to_bits()
            && self.raw_sea.to_bits() == (-0.5_f64).to_bits()
            && self.base_sea.to_bits() == 0.0_f64.to_bits()
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum PythiaPdfFacadeError {
    NativeAudit(String),
    SignedBoundaryIncompatible(PythiaSignedBoundaryEvidence),
    ProvenanceOverflow { capacity: usize },
    UnclassifiedEventRuntime,
}

impl fmt::Display for PythiaPdfFacadeError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NativeAudit(message) => formatter.write_str(message),
            Self::SignedBoundaryIncompatible(evidence) => write!(
                formatter,
                "PYTHIA {} non-virtual PDF boundary clips signed values: raw inclusive {:?}, base inclusive {:?}",
                evidence.pythia_version_integer, evidence.raw_inclusive, evidence.base_inclusive
            ),
            Self::ProvenanceOverflow { capacity } => write!(
                formatter,
                "query provenance capacity {capacity} was exhausted; records are never dropped"
            ),
            Self::UnclassifiedEventRuntime => formatter.write_str(
                "unclassified event-runtime PDF consumer is forbidden in D1C-B",
            ),
        }
    }
}

impl Error for PythiaPdfFacadeError {}

extern "C" {
    fn partonsbi_pythia_pdf_signed_boundary_audit(
        raw_inclusive: *mut f64,
        base_inclusive: *mut f64,
        raw_valence: *mut f64,
        base_valence: *mut f64,
        raw_sea: *mut f64,
        base_sea: *mut f64,
        pythia_version_integer: *mut i32,
        error_buffer: *mut c_char,
        error_buffer_size: usize,
    ) -> i32;
}

pub fn audit_installed_pythia_signed_boundary(
) -> Result<PythiaSignedBoundaryEvidence, PythiaPdfFacadeError> {
    let mut evidence = PythiaSignedBoundaryEvidence {
        pythia_version_integer: 0,
        raw_inclusive: f64::NAN,
        base_inclusive: f64::NAN,
        raw_valence: f64::NAN,
        base_valence: f64::NAN,
        raw_sea: f64::NAN,
        base_sea: f64::NAN,
    };
    let mut error = [0 as c_char; 1024];
    // SAFETY: every output points to live storage and the error buffer is
    // bounded and zero-initialized for the duration of the native call.
    let status = unsafe {
        partonsbi_pythia_pdf_signed_boundary_audit(
            &mut evidence.raw_inclusive,
            &mut evidence.base_inclusive,
            &mut evidence.raw_valence,
            &mut evidence.base_valence,
            &mut evidence.raw_sea,
            &mut evidence.base_sea,
            &mut evidence.pythia_version_integer,
            error.as_mut_ptr(),
            error.len(),
        )
    };
    if status != 0 {
        // SAFETY: native code always writes a bounded NUL-terminated message
        // on failure; the zero-initialized buffer is valid even if empty.
        let message = unsafe { CStr::from_ptr(error.as_ptr()) }
            .to_string_lossy()
            .into_owned();
        return Err(PythiaPdfFacadeError::NativeAudit(if message.is_empty() {
            format!("PYTHIA signed-boundary audit failed with status {status}")
        } else {
            message
        }));
    }
    Ok(evidence)
}

pub fn require_signed_facade_compatibility(
) -> Result<PythiaSignedBoundaryEvidence, PythiaPdfFacadeError> {
    let evidence = audit_installed_pythia_signed_boundary()?;
    if evidence.demonstrates_clipping() {
        Err(PythiaPdfFacadeError::SignedBoundaryIncompatible(evidence))
    } else {
        Err(PythiaPdfFacadeError::NativeAudit(
            "installed PYTHIA boundary did not reproduce its audited 8.312 contract".into(),
        ))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PythiaPdfMethodDisposition {
    NonvirtualClippingBlocker,
    WouldRequireCandidateOverride,
    ProtectedUpdateHook,
    DisabledConsumerMethod,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct PythiaPdfMethodAudit {
    pub method: &'static str,
    pub signature: &'static str,
    pub scale: &'static str,
    pub base_behavior: &'static str,
    pub signed_value_behavior: &'static str,
    pub disposition: PythiaPdfMethodDisposition,
    pub source: &'static str,
}

pub const PYTHIA_PDF_METHOD_MATRIX: [PythiaPdfMethodAudit; 14] = [
    PythiaPdfMethodAudit {
        method: "xf",
        signature: "double xf(int id, double x, double Q2)",
        scale: "Q2_GeV2",
        base_behavior: "updates cache then returns max(0, stored xf)",
        signed_value_behavior: "clips",
        disposition: PythiaPdfMethodDisposition::NonvirtualClippingBlocker,
        source: "include/Pythia8/PartonDistributions.h:83; src/PartonDistributions.cc:122-209",
    },
    PythiaPdfMethodAudit {
        method: "xfVal",
        signature: "double xfVal(int id, double x, double Q2)",
        scale: "Q2_GeV2",
        base_behavior: "derives valence then applies max(0, value), sometimes abs",
        signed_value_behavior: "clips_or_absolute_value",
        disposition: PythiaPdfMethodDisposition::NonvirtualClippingBlocker,
        source: "include/Pythia8/PartonDistributions.h:86; src/PartonDistributions.cc:215-286",
    },
    PythiaPdfMethodAudit {
        method: "xfSea",
        signature: "double xfSea(int id, double x, double Q2)",
        scale: "Q2_GeV2",
        base_behavior: "derives sea then applies max(0, value)",
        signed_value_behavior: "clips",
        disposition: PythiaPdfMethodDisposition::NonvirtualClippingBlocker,
        source: "include/Pythia8/PartonDistributions.h:87; src/PartonDistributions.cc:292-379",
    },
    PythiaPdfMethodAudit {
        method: "xfUpdate",
        signature: "virtual void xfUpdate(int id, double x, double Q2) = 0",
        scale: "Q2_GeV2",
        base_behavior: "subclass fills protected cached flavor fields",
        signed_value_behavior: "can_store_signed_but_nonvirtual_readers_clip",
        disposition: PythiaPdfMethodDisposition::ProtectedUpdateHook,
        source: "include/Pythia8/PartonDistributions.h:195",
    },
    PythiaPdfMethodAudit {
        method: "insideBounds",
        signature: "virtual bool insideBounds(double x, double Q2)",
        scale: "Q2_GeV2",
        base_behavior: "returns true",
        signed_value_behavior: "not_applicable",
        disposition: PythiaPdfMethodDisposition::WouldRequireCandidateOverride,
        source: "include/Pythia8/PartonDistributions.h:90",
    },
    PythiaPdfMethodAudit {
        method: "alphaS",
        signature: "virtual double alphaS(double Q2)",
        scale: "Q2_GeV2",
        base_behavior: "returns 1",
        signed_value_behavior: "not_applicable",
        disposition: PythiaPdfMethodDisposition::WouldRequireCandidateOverride,
        source: "include/Pythia8/PartonDistributions.h:93",
    },
    PythiaPdfMethodAudit {
        method: "mQuarkPDF",
        signature: "virtual double mQuarkPDF(int id)",
        scale: "none",
        base_behavior: "returns -1",
        signed_value_behavior: "not_applicable",
        disposition: PythiaPdfMethodDisposition::WouldRequireCandidateOverride,
        source: "include/Pythia8/PartonDistributions.h:96",
    },
    PythiaPdfMethodAudit {
        method: "xfMax",
        signature: "virtual double xfMax(int id, double x, double Q2)",
        scale: "Q2_GeV2",
        base_behavior: "delegates to nonvirtual xf",
        signed_value_behavior: "clips_by_default",
        disposition: PythiaPdfMethodDisposition::WouldRequireCandidateOverride,
        source: "include/Pythia8/PartonDistributions.h:148",
    },
    PythiaPdfMethodAudit {
        method: "xfSame",
        signature: "virtual double xfSame(int id, double x, double Q2)",
        scale: "Q2_GeV2",
        base_behavior: "delegates to nonvirtual xf",
        signed_value_behavior: "clips_by_default",
        disposition: PythiaPdfMethodDisposition::WouldRequireCandidateOverride,
        source: "include/Pythia8/PartonDistributions.h:151",
    },
    PythiaPdfMethodAudit {
        method: "setExtrapolate",
        signature: "virtual void setExtrapolate(bool)",
        scale: "none",
        base_behavior: "no-op",
        signed_value_behavior: "not_applicable",
        disposition: PythiaPdfMethodDisposition::WouldRequireCandidateOverride,
        source: "include/Pythia8/PartonDistributions.h:80",
    },
    PythiaPdfMethodAudit {
        method: "xfFlux",
        signature: "virtual double xfFlux(int id, double x, double Q2)",
        scale: "Q2_GeV2",
        base_behavior: "returns 0",
        signed_value_behavior: "disabled_photon_path",
        disposition: PythiaPdfMethodDisposition::DisabledConsumerMethod,
        source: "include/Pythia8/PartonDistributions.h:134",
    },
    PythiaPdfMethodAudit {
        method: "xfApprox",
        signature: "virtual double xfApprox(int id, double x, double Q2)",
        scale: "Q2_GeV2",
        base_behavior: "returns 0",
        signed_value_behavior: "disabled_photon_path",
        disposition: PythiaPdfMethodDisposition::DisabledConsumerMethod,
        source: "include/Pythia8/PartonDistributions.h:135",
    },
    PythiaPdfMethodAudit {
        method: "xfGamma",
        signature: "virtual double xfGamma(int id, double x, double Q2)",
        scale: "Q2_GeV2",
        base_behavior: "returns 0",
        signed_value_behavior: "disabled_photon_path",
        disposition: PythiaPdfMethodDisposition::DisabledConsumerMethod,
        source: "include/Pythia8/PartonDistributions.h:136",
    },
    PythiaPdfMethodAudit {
        method: "xfIntegratedTotal",
        signature: "virtual double xfIntegratedTotal(double Q2)",
        scale: "Q2_GeV2",
        base_behavior: "returns 0",
        signed_value_behavior: "disabled_MPI_photon_path",
        disposition: PythiaPdfMethodDisposition::DisabledConsumerMethod,
        source: "include/Pythia8/PartonDistributions.h:125",
    },
];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PythiaPdfPointerDisposition {
    PointlikeLeptonProvider,
    InstrumentedFacadeRequiredButBlocked,
    DisabledNull,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct PythiaPdfPointerClassification {
    pub slot: &'static str,
    pub role: &'static str,
    pub disposition: PythiaPdfPointerDisposition,
}

pub const PYTHIA_PDF_POINTER_CLASSIFICATION: [PythiaPdfPointerClassification; 16] = [
    PythiaPdfPointerClassification {
        slot: "A",
        role: "electron_beam",
        disposition: PythiaPdfPointerDisposition::PointlikeLeptonProvider,
    },
    PythiaPdfPointerClassification {
        slot: "B",
        role: "proton_beam",
        disposition: PythiaPdfPointerDisposition::InstrumentedFacadeRequiredButBlocked,
    },
    PythiaPdfPointerClassification {
        slot: "HardA",
        role: "electron_hard_process",
        disposition: PythiaPdfPointerDisposition::PointlikeLeptonProvider,
    },
    PythiaPdfPointerClassification {
        slot: "HardB",
        role: "proton_hard_process",
        disposition: PythiaPdfPointerDisposition::InstrumentedFacadeRequiredButBlocked,
    },
    PythiaPdfPointerClassification {
        slot: "PomA",
        role: "pomeron_a",
        disposition: PythiaPdfPointerDisposition::DisabledNull,
    },
    PythiaPdfPointerClassification {
        slot: "PomB",
        role: "pomeron_b",
        disposition: PythiaPdfPointerDisposition::DisabledNull,
    },
    PythiaPdfPointerClassification {
        slot: "GamA",
        role: "resolved_photon_a",
        disposition: PythiaPdfPointerDisposition::DisabledNull,
    },
    PythiaPdfPointerClassification {
        slot: "GamB",
        role: "resolved_photon_b",
        disposition: PythiaPdfPointerDisposition::DisabledNull,
    },
    PythiaPdfPointerClassification {
        slot: "HardGamA",
        role: "hard_photon_a",
        disposition: PythiaPdfPointerDisposition::DisabledNull,
    },
    PythiaPdfPointerClassification {
        slot: "HardGamB",
        role: "hard_photon_b",
        disposition: PythiaPdfPointerDisposition::DisabledNull,
    },
    PythiaPdfPointerClassification {
        slot: "UnresA",
        role: "unresolved_a",
        disposition: PythiaPdfPointerDisposition::DisabledNull,
    },
    PythiaPdfPointerClassification {
        slot: "UnresB",
        role: "unresolved_b",
        disposition: PythiaPdfPointerDisposition::DisabledNull,
    },
    PythiaPdfPointerClassification {
        slot: "UnresGamA",
        role: "unresolved_photon_a",
        disposition: PythiaPdfPointerDisposition::DisabledNull,
    },
    PythiaPdfPointerClassification {
        slot: "UnresGamB",
        role: "unresolved_photon_b",
        disposition: PythiaPdfPointerDisposition::DisabledNull,
    },
    PythiaPdfPointerClassification {
        slot: "VMDA",
        role: "vmd_a",
        disposition: PythiaPdfPointerDisposition::DisabledNull,
    },
    PythiaPdfPointerClassification {
        slot: "VMDB",
        role: "vmd_b",
        disposition: PythiaPdfPointerDisposition::DisabledNull,
    },
];

pub fn pythia_facade_policy_identity(persistent_evaluator_identity: &str) -> String {
    let mut inputs = BTreeMap::<String, String>::new();
    inputs.insert(
        "alpha_s_routing".into(),
        "persistent_alphaqcd_q2_sqrt_once_v1".into(),
    );
    inputs.insert("facade_abi".into(), PYTHIA_PDF_FACADE_ABI_VERSION.into());
    inputs.insert(
        "facade_policy".into(),
        PYTHIA_PDF_FACADE_POLICY_VERSION.into(),
    );
    inputs.insert(
        "method_coverage".into(),
        PYTHIA_PDF_METHOD_MATRIX
            .iter()
            .map(|entry| entry.method)
            .collect::<Vec<_>>()
            .join("|"),
    );
    inputs.insert(
        "mutex_policy".into(),
        "cross_language_recursive_process_mutex_v2".into(),
    );
    inputs.insert(
        "persistent_evaluator_identity".into(),
        persistent_evaluator_identity.into(),
    );
    inputs.insert(
        "pointer_policy".into(),
        PYTHIA_PDF_POINTER_POLICY_VERSION.into(),
    );
    inputs.insert(
        "provenance_schema".into(),
        PYTHIA_PDF_PROVENANCE_SCHEMA.into(),
    );
    inputs.insert("pythia_version".into(), "8.312".into());
    inputs.insert(
        "scale_policy".into(),
        PYTHIA_PDF_SCALE_POLICY_VERSION.into(),
    );
    inputs.insert("sign_policy".into(), PYTHIA_PDF_SIGN_POLICY_VERSION.into());
    inputs.insert(
        "valence_sea_policy".into(),
        PYTHIA_PDF_VALENCE_SEA_POLICY_VERSION.into(),
    );
    let bytes = serde_json::to_vec(&inputs).expect("BTreeMap serialization is infallible");
    format!("sha256:{:x}", Sha256::digest(bytes))
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PythiaExecutionPhase {
    SyntheticProbe,
    PythiaInitialization,
    EventRuntimeReserved,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PythiaConsumerClassification {
    SyntheticMethodProbe,
    PythiaInitialization,
    UnclassifiedEventRuntime,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PythiaFacadeMethod {
    Xf,
    XfVal,
    XfSea,
    XfMax,
    XfSame,
    InsideBounds,
    AlphaS,
    MQuarkPdf,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PythiaQueryStatus {
    Accepted,
    Rejected,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum PythiaQueryReason {
    Accepted,
    OutsideSupport,
    InactiveFlavor,
    UnsupportedFlavor,
    NonFinite,
    UnknownConsumer,
    SignedBoundaryIncompatible,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PythiaPdfQueryRecord {
    pub sequence: u64,
    pub execution_phase: PythiaExecutionPhase,
    pub consumer: PythiaConsumerClassification,
    pub method: PythiaFacadeMethod,
    pub flavor: i32,
    pub x_bits: u64,
    pub input_scale_bits: u64,
    pub derived_q_bits: Option<u64>,
    pub raw_apfel_output_bits: Option<u64>,
    pub facade_output_bits: Option<u64>,
    pub status: PythiaQueryStatus,
    pub reason: PythiaQueryReason,
    pub threshold_side: Option<String>,
    pub evaluator_policy_identity: String,
    pub facade_policy_identity: String,
}

#[derive(Debug, Clone)]
pub struct BoundedPythiaQueryProvenance {
    capacity: usize,
    records: Vec<PythiaPdfQueryRecord>,
}

impl BoundedPythiaQueryProvenance {
    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            capacity,
            records: Vec::new(),
        }
    }
    pub fn records(&self) -> &[PythiaPdfQueryRecord] {
        &self.records
    }
    pub fn record(&mut self, mut record: PythiaPdfQueryRecord) -> Result<(), PythiaPdfFacadeError> {
        if self.records.len() == self.capacity {
            return Err(PythiaPdfFacadeError::ProvenanceOverflow {
                capacity: self.capacity,
            });
        }
        record.sequence = self.records.len() as u64;
        let unclassified =
            record.consumer == PythiaConsumerClassification::UnclassifiedEventRuntime;
        if unclassified {
            record.status = PythiaQueryStatus::Rejected;
            record.reason = PythiaQueryReason::UnknownConsumer;
        }
        self.records.push(record);
        if unclassified {
            Err(PythiaPdfFacadeError::UnclassifiedEventRuntime)
        } else {
            Ok(())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn record(consumer: PythiaConsumerClassification) -> PythiaPdfQueryRecord {
        PythiaPdfQueryRecord {
            sequence: u64::MAX,
            execution_phase: PythiaExecutionPhase::SyntheticProbe,
            consumer,
            method: PythiaFacadeMethod::Xf,
            flavor: 21,
            x_bits: 0.1_f64.to_bits(),
            input_scale_bits: 100.0_f64.to_bits(),
            derived_q_bits: Some(10.0_f64.to_bits()),
            raw_apfel_output_bits: Some((-1.0_f64).to_bits()),
            facade_output_bits: None,
            status: PythiaQueryStatus::Accepted,
            reason: PythiaQueryReason::Accepted,
            threshold_side: Some("ABOVE_BOTTOM".into()),
            evaluator_policy_identity: "sha256:evaluator".into(),
            facade_policy_identity: "sha256:facade".into(),
        }
    }

    #[test]
    fn pythia_pdf_facade_admission_detects_nonvirtual_clipping() {
        let evidence = audit_installed_pythia_signed_boundary().unwrap();
        assert!(evidence.demonstrates_clipping());
        assert!(matches!(
            require_signed_facade_compatibility(),
            Err(PythiaPdfFacadeError::SignedBoundaryIncompatible(_))
        ));
    }

    #[test]
    fn pythia_pdf_method_matrix_records_every_relevant_boundary() {
        for required in [
            "xf",
            "xfVal",
            "xfSea",
            "xfUpdate",
            "insideBounds",
            "alphaS",
            "mQuarkPDF",
            "xfMax",
            "xfSame",
        ] {
            assert!(PYTHIA_PDF_METHOD_MATRIX
                .iter()
                .any(|entry| entry.method == required));
        }
        assert_eq!(
            PYTHIA_PDF_METHOD_MATRIX
                .iter()
                .filter(|entry| entry.disposition
                    == PythiaPdfMethodDisposition::NonvirtualClippingBlocker)
                .count(),
            3
        );
        assert_eq!(PYTHIA_PDF_POINTER_CLASSIFICATION.len(), 16);
        assert_eq!(
            PYTHIA_PDF_POINTER_CLASSIFICATION
                .iter()
                .filter(|entry| entry.disposition
                    == PythiaPdfPointerDisposition::InstrumentedFacadeRequiredButBlocked)
                .map(|entry| entry.slot)
                .collect::<Vec<_>>(),
            vec!["B", "HardB"]
        );
    }

    #[test]
    fn pythia_pdf_provenance_is_bounded_ordered_and_fail_closed() {
        let mut provenance = BoundedPythiaQueryProvenance::with_capacity(2);
        provenance
            .record(record(PythiaConsumerClassification::SyntheticMethodProbe))
            .unwrap();
        assert!(matches!(
            provenance.record(record(
                PythiaConsumerClassification::UnclassifiedEventRuntime
            )),
            Err(PythiaPdfFacadeError::UnclassifiedEventRuntime)
        ));
        assert_eq!(provenance.records()[0].sequence, 0);
        assert_eq!(provenance.records()[1].sequence, 1);
        assert_eq!(
            provenance.records()[1].reason,
            PythiaQueryReason::UnknownConsumer
        );
        assert!(matches!(
            provenance.record(record(PythiaConsumerClassification::SyntheticMethodProbe)),
            Err(PythiaPdfFacadeError::ProvenanceOverflow { capacity: 2 })
        ));
    }

    #[test]
    fn facade_identity_excludes_runtime_evidence_and_d2_stays_closed() {
        let first = pythia_facade_policy_identity("sha256:evaluator");
        let second = pythia_facade_policy_identity("sha256:evaluator");
        assert_eq!(first, second);
        assert_ne!(first, pythia_facade_policy_identity("sha256:other"));
        const {
            assert!(!D1C_B_PYTHIA_INITIALIZED);
            assert!(!D1C_B_PYTHIA_NEXT_EXECUTED);
            assert!(D1C_B_ATTEMPTED_EVENTS == 0);
            assert!(!D1C_B_D2_AUTHORIZED);
        }
    }
}
