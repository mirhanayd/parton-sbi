//! Physics utilities for the PartonSBI DIS research pipeline.

pub mod apfel;
pub mod constants;
pub mod continuous_pdf;
pub mod cross_section;
pub mod dis_kinematics;
pub mod four_vector;
pub mod hepmc3;
pub mod pdf;
pub mod pdf_artifact;
pub mod pdf_artifact_v2;
pub mod pdf_reweighting;
pub mod pdf_transport_prototype;
pub mod structure_function_provider;
pub mod structure_function_validation;
pub mod structure_functions;
pub mod surrogate;
pub mod surrogate_training;

pub use apfel::{
    ApfelProtocolError, ApfelProtocolResponse, ApfelStructureFunctionProvider,
    APFEL_ZM_VFNS_SCHEME, DEFAULT_APFEL_BACKEND_PATH,
};
pub use constants::{ELECTRON_MASS_GEV, PROTON_MASS_GEV};
pub use continuous_pdf::*;
pub use cross_section::{
    exact_inelasticity, gev_minus_four_to_pb_per_gev2, leptonic_y_plus,
    lo_differential_cross_section, CouplingError, CrossSectionError, ElectromagneticCoupling,
    FixedAlpha, LoDisCrossSection, DEFAULT_FIXED_ALPHA, GEV_MINUS_2_TO_PB,
};
pub use dis_kinematics::{
    collider_beams, compute_dis_kinematics, incoming_electron, incoming_proton, scattered_electron,
    ColliderBeams, DisCuts, DisError, DisKinematics,
};
pub use four_vector::{FourVector, FourVectorError};
pub use hepmc3::{
    HepMcAttribute, HepMcError, HepMcEvent, HepMcParticle, HepMcPdfInfo, HepMcReader, HepMcRunCuts,
    HepMcRunProvenance, HepMcRunSummary, HepMcVertex,
};
pub use pdf::{
    LhapdfProvider, PartonDensities, PdfError, PdfProvider, PdfSupportBoundSource, PdfSupportBounds,
};
pub use pdf_artifact::*;
pub use pdf_artifact_v2::*;
pub use pdf_reweighting::{
    extract_event_observables, identify_proton_pdf_entry, load_full_set_strict_support_contract,
    reweight_event, summarize_reweighting, validate_run_compatibility, DenominatorPolicy,
    EffectiveSampleSize, EventObservableSummary, InclusiveObservableRow, PdfEntrySide,
    PdfMemberSpec, PdfMemberSupportDomain, PdfReweightingAccumulator, PdfReweightingDiagnostics,
    PdfReweightingError, PdfReweightingInvalidReason, PdfReweightingRequest, PdfReweightingResult,
    PdfSupportContract, PdfSupportOutcome, PdfSupportPolicy, PdfWeightEvaluator, ProtonPdfEntry,
    RatioStatistics, RunCompatibilityIssue, RunCompatibilityReport, ScalarDistributionStatistics,
    WeightStatistics, DEFAULT_NOMINAL_XF_RELATIVE_TOLERANCE, PDF_REUSE_ESS_FRACTION_THRESHOLD,
    PDF_SUPPORT_POLICY_VERSION,
};
pub use pdf_transport_prototype::*;
pub use structure_function_provider::{
    DisProjectile, DisTarget, LoPdfStructureFunctionProvider, ParsePerturbativeOrderError,
    PerturbativeOrder, StructureFunctionBackend, StructureFunctionMetadata,
    StructureFunctionProcess, StructureFunctionProvider, StructureFunctionProviderError,
    StructureFunctionRequest, StructureFunctionResult, LO_PARTON_MODEL_SCHEME,
    PHOTON_EXCHANGE_MODE, STRUCTURE_FUNCTION_SCHEMA_VERSION,
};
pub use structure_functions::{
    electromagnetic_f2_from_xf, evaluate_lo_structure_functions, LoStructureFunctions,
    StructureFunctionError, DOWN_TYPE_CHARGE_SQUARED, LO_LONGITUDINAL_STRUCTURE_FUNCTION,
    LO_PARITY_VIOLATING_STRUCTURE_FUNCTION, UP_TYPE_CHARGE_SQUARED,
};
pub use surrogate::{SurrogateConfig, SurrogateModel, SurrogateProvider, SURROGATE_SCHEME};
pub use surrogate_training::{generate_dataset, train_and_save_surrogate, SurrogateDataPoint};
