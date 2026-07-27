//! Typed, event-level hard-PDF reweighting and closure diagnostics.
//!
//! This module deliberately treats `GenPdfInfo` and hard flavor as hidden
//! generator truth. They are used for importance weighting and diagnostics,
//! never as default observed inference features.

use super::{HepMcEvent, HepMcRunProvenance, LhapdfProvider, PdfError, PdfSupportBounds};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::error::Error;
use std::fmt;

pub const DEFAULT_NOMINAL_XF_RELATIVE_TOLERANCE: f64 = 1.0e-6;
pub const PDF_REUSE_ESS_FRACTION_THRESHOLD: f64 = 0.20;
pub const PDF_SUPPORT_POLICY_VERSION: u32 = 1;
const RELATIVE_DENOMINATOR_EPSILON: f64 = 1.0e-300;
const ELECTRON_PDG_ID: i32 = 11;
const PROTON_PDG_ID: i32 = 2212;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PdfSupportPolicy {
    StrictInGrid,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PdfSupportOutcome {
    InSupport,
    BelowXMinimum,
    AboveXMaximum,
    BelowQMinimum,
    AboveQMaximum,
    NonFinite,
}

impl fmt::Display for PdfSupportOutcome {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        let name = serde_json::to_value(self)
            .ok()
            .and_then(|value| value.as_str().map(str::to_owned))
            .unwrap_or_else(|| "unknown".to_owned());
        formatter.write_str(&name)
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PdfMemberSupportDomain {
    pub member: i32,
    pub bounds: PdfSupportBounds,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PdfSupportContract {
    pub schema_version: u32,
    pub policy: PdfSupportPolicy,
    pub extrapolation_allowed: bool,
    pub pdf_set: String,
    pub nominal_member: i32,
    pub member_domains: Vec<PdfMemberSupportDomain>,
    pub intersection: PdfSupportBounds,
    pub all_members_share_bounds: bool,
}

impl PdfSupportContract {
    pub fn strict_in_grid(
        pdf_set: impl Into<String>,
        nominal_member: i32,
        mut member_domains: Vec<PdfMemberSupportDomain>,
    ) -> Result<Self, PdfReweightingError> {
        let pdf_set = pdf_set.into();
        if pdf_set.trim().is_empty() || nominal_member < 0 || member_domains.is_empty() {
            return Err(PdfReweightingError::InvalidRequest(
                "strict support requires a PDF set, nominal member, and member domains".to_owned(),
            ));
        }
        member_domains.sort_by_key(|domain| domain.member);
        if member_domains
            .windows(2)
            .any(|pair| pair[0].member == pair[1].member)
            || !member_domains
                .iter()
                .any(|domain| domain.member == nominal_member)
        {
            return Err(PdfReweightingError::InvalidRequest(
                "support domains must contain unique members including the nominal member"
                    .to_owned(),
            ));
        }
        let first = member_domains[0].bounds.clone();
        let all_members_share_bounds = member_domains
            .iter()
            .all(|domain| domain.bounds.same_numeric_domain(&first));
        let x_minimum = member_domains
            .iter()
            .map(|domain| domain.bounds.x_minimum)
            .max_by(f64::total_cmp)
            .expect("non-empty member domains");
        let x_maximum = member_domains
            .iter()
            .map(|domain| domain.bounds.x_maximum)
            .min_by(f64::total_cmp)
            .expect("non-empty member domains");
        let q_minimum_gev = member_domains
            .iter()
            .map(|domain| domain.bounds.q_minimum_gev)
            .max_by(f64::total_cmp)
            .expect("non-empty member domains");
        let q_maximum_gev = member_domains
            .iter()
            .map(|domain| domain.bounds.q_maximum_gev)
            .min_by(f64::total_cmp)
            .expect("non-empty member domains");
        let intersection =
            PdfSupportBounds::new(x_minimum, x_maximum, q_minimum_gev, q_maximum_gev).map_err(
                |message| PdfReweightingError::InconsistentMemberGrid {
                    pdf_set: pdf_set.clone(),
                    message,
                },
            )?;
        Ok(Self {
            schema_version: PDF_SUPPORT_POLICY_VERSION,
            policy: PdfSupportPolicy::StrictInGrid,
            extrapolation_allowed: false,
            pdf_set,
            nominal_member,
            member_domains,
            intersection,
            all_members_share_bounds,
        })
    }

    #[must_use]
    pub fn assess(&self, x: f64, q_gev: f64) -> PdfSupportOutcome {
        if !x.is_finite() || !q_gev.is_finite() {
            PdfSupportOutcome::NonFinite
        } else if x < self.intersection.x_minimum {
            PdfSupportOutcome::BelowXMinimum
        } else if x > self.intersection.x_maximum {
            PdfSupportOutcome::AboveXMaximum
        } else if q_gev < self.intersection.q_minimum_gev {
            PdfSupportOutcome::BelowQMinimum
        } else if q_gev > self.intersection.q_maximum_gev {
            PdfSupportOutcome::AboveQMaximum
        } else {
            PdfSupportOutcome::InSupport
        }
    }

    pub fn validate_for_members(
        &self,
        source: &PdfMemberSpec,
        target: &PdfMemberSpec,
    ) -> Result<(), PdfReweightingError> {
        if self.schema_version != PDF_SUPPORT_POLICY_VERSION
            || self.policy != PdfSupportPolicy::StrictInGrid
            || self.extrapolation_allowed
            || self.pdf_set != source.set_name
            || self.pdf_set != target.set_name
            || self.nominal_member != source.member
            || !self
                .member_domains
                .iter()
                .any(|domain| domain.member == target.member)
        {
            return Err(PdfReweightingError::InvalidRequest(
                "reweighting request is incompatible with the strict in-grid support contract"
                    .to_owned(),
            ));
        }
        Ok(())
    }

    #[must_use]
    pub fn same_reusable_domain(&self, other: &Self) -> bool {
        self.schema_version == other.schema_version
            && self.policy == other.policy
            && !self.extrapolation_allowed
            && !other.extrapolation_allowed
            && self.pdf_set == other.pdf_set
            && self.member_domains == other.member_domains
            && self.intersection == other.intersection
            && self.all_members_share_bounds == other.all_members_share_bounds
    }
}

pub fn load_full_set_strict_support_contract(
    pdf_set: &str,
    nominal_member: i32,
) -> Result<PdfSupportContract, PdfReweightingError> {
    let nominal = LhapdfProvider::new(pdf_set, nominal_member)?;
    let member_count = nominal.member_count();
    let mut domains = Vec::with_capacity(member_count);
    for member in 0..member_count {
        let member = i32::try_from(member).map_err(|_| {
            PdfReweightingError::InvalidRequest("PDF member count exceeds i32".to_owned())
        })?;
        let provider = LhapdfProvider::new(pdf_set, member)?;
        domains.push(PdfMemberSupportDomain {
            member,
            bounds: provider.support_bounds().clone(),
        });
    }
    PdfSupportContract::strict_in_grid(pdf_set, nominal_member, domains)
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct PdfMemberSpec {
    pub set_name: String,
    pub member: i32,
}

impl PdfMemberSpec {
    pub fn new(set_name: impl Into<String>, member: i32) -> Result<Self, PdfReweightingError> {
        let set_name = set_name.into();
        if set_name.trim().is_empty() {
            return Err(PdfReweightingError::InvalidRequest(
                "PDF set name must not be empty".to_owned(),
            ));
        }
        if member < 0 {
            return Err(PdfReweightingError::InvalidRequest(format!(
                "PDF member must be non-negative, got {member}"
            )));
        }
        Ok(Self { set_name, member })
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum DenominatorPolicy {
    #[default]
    Stored,
    Recomputed,
}

impl fmt::Display for DenominatorPolicy {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Stored => formatter.write_str("stored"),
            Self::Recomputed => formatter.write_str("recomputed"),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PdfReweightingRequest {
    pub source_pdf: PdfMemberSpec,
    pub target_pdf: PdfMemberSpec,
    pub source_run_identity: String,
    pub source_seed: Option<i64>,
    pub event_weight_index: Option<usize>,
    pub denominator_policy: DenominatorPolicy,
    pub nominal_xf_relative_tolerance: f64,
    pub support_contract: PdfSupportContract,
}

impl PdfReweightingRequest {
    pub fn validate(&self) -> Result<(), PdfReweightingError> {
        if self.source_run_identity.trim().is_empty() {
            return Err(PdfReweightingError::InvalidRequest(
                "source run identity must not be empty".to_owned(),
            ));
        }
        if !self.nominal_xf_relative_tolerance.is_finite()
            || self.nominal_xf_relative_tolerance < 0.0
        {
            return Err(PdfReweightingError::InvalidRequest(format!(
                "nominal xf relative tolerance must be finite and non-negative, got {}",
                self.nominal_xf_relative_tolerance
            )));
        }
        self.support_contract
            .validate_for_members(&self.source_pdf, &self.target_pdf)?;
        Ok(())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PdfReweightingInvalidReason {
    MissingPdfInfo,
    InvalidBeamConfiguration,
    AmbiguousPdfEntries,
    UnsupportedFlavor,
    InvalidX,
    InvalidScale,
    MissingEventWeight,
    MultipleEventWeightsRequireIndex,
    EventWeightIndexOutOfRange,
    NonFiniteEventWeight,
    OutsideStrictPdfSupport,
    NonFiniteStoredNominalXf,
    NonPositiveStoredNominalXf,
    NominalPdfEvaluationFailed,
    NonFiniteRecomputedNominalXf,
    NonPositiveRecomputedNominalXf,
    TargetPdfEvaluationFailed,
    NonFiniteTargetXf,
    NegativeTargetXf,
    NominalXfMismatch,
    NonFiniteRatio,
    NonFiniteTargetWeight,
}

impl fmt::Display for PdfReweightingInvalidReason {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        let name = serde_json::to_value(self)
            .ok()
            .and_then(|value| value.as_str().map(str::to_owned))
            .unwrap_or_else(|| "unknown".to_owned());
        formatter.write_str(&name)
    }
}

#[derive(Debug)]
pub enum PdfReweightingError {
    InvalidRequest(String),
    InconsistentMemberGrid { pdf_set: String, message: String },
    Pdf(PdfError),
}

impl fmt::Display for PdfReweightingError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidRequest(message) => formatter.write_str(message),
            Self::InconsistentMemberGrid { pdf_set, message } => {
                write!(
                    formatter,
                    "PDF set '{pdf_set}' has no valid member-grid intersection: {message}"
                )
            }
            Self::Pdf(error) => error.fmt(formatter),
        }
    }
}

impl Error for PdfReweightingError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Pdf(error) => Some(error),
            Self::InvalidRequest(_) | Self::InconsistentMemberGrid { .. } => None,
        }
    }
}

impl From<PdfError> for PdfReweightingError {
    fn from(error: PdfError) -> Self {
        Self::Pdf(error)
    }
}

pub trait PdfWeightEvaluator {
    fn xfx_at_scale(&self, flavor: i32, x: f64, scale_gev: f64) -> Result<f64, String>;
}

impl PdfWeightEvaluator for LhapdfProvider {
    fn xfx_at_scale(&self, flavor: i32, x: f64, scale_gev: f64) -> Result<f64, String> {
        LhapdfProvider::xfx_at_scale(self, flavor, x, scale_gev).map_err(|error| error.to_string())
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PdfEntrySide {
    First,
    Second,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ProtonPdfEntry {
    pub side: PdfEntrySide,
    pub flavor: i32,
    pub x: f64,
    pub scale_gev: f64,
    pub stored_xf: f64,
    pub pdf_id: i32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PdfReweightingResult {
    pub event_number: i64,
    pub source_pdf: PdfMemberSpec,
    pub target_pdf: PdfMemberSpec,
    pub source_run_identity: String,
    pub source_seed: Option<i64>,
    pub selected_event_weight_index: Option<usize>,
    pub original_event_weight: Option<f64>,
    pub proton_side: Option<PdfEntrySide>,
    pub proton_side_flavor: Option<i32>,
    pub proton_side_x: Option<f64>,
    pub pdf_scale_gev: Option<f64>,
    pub stored_nominal_xf: Option<f64>,
    pub support_outcome: Option<PdfSupportOutcome>,
    pub recomputed_nominal_xf: Option<f64>,
    pub target_xf: Option<f64>,
    pub stored_nominal_relative_difference: Option<f64>,
    pub ratio_stored_denominator: Option<f64>,
    pub ratio_recomputed_denominator: Option<f64>,
    pub denominator_policy: DenominatorPolicy,
    pub primary_ratio: Option<f64>,
    pub target_event_weight: Option<f64>,
    pub valid: bool,
    pub invalid_reason: Option<PdfReweightingInvalidReason>,
    pub invalid_message: Option<String>,
}

impl PdfReweightingResult {
    fn invalid(
        event_number: i64,
        request: &PdfReweightingRequest,
        reason: PdfReweightingInvalidReason,
        message: impl Into<String>,
    ) -> Self {
        Self {
            event_number,
            source_pdf: request.source_pdf.clone(),
            target_pdf: request.target_pdf.clone(),
            source_run_identity: request.source_run_identity.clone(),
            source_seed: request.source_seed,
            selected_event_weight_index: None,
            original_event_weight: None,
            proton_side: None,
            proton_side_flavor: None,
            proton_side_x: None,
            pdf_scale_gev: None,
            stored_nominal_xf: None,
            support_outcome: None,
            recomputed_nominal_xf: None,
            target_xf: None,
            stored_nominal_relative_difference: None,
            ratio_stored_denominator: None,
            ratio_recomputed_denominator: None,
            denominator_policy: request.denominator_policy,
            primary_ratio: None,
            target_event_weight: None,
            valid: false,
            invalid_reason: Some(reason),
            invalid_message: Some(message.into()),
        }
    }

    fn with_entry(mut self, entry: &ProtonPdfEntry) -> Self {
        self.proton_side = Some(entry.side);
        self.proton_side_flavor = Some(entry.flavor);
        self.proton_side_x = Some(entry.x);
        self.pdf_scale_gev = Some(entry.scale_gev);
        self.stored_nominal_xf = Some(entry.stored_xf);
        self
    }

    fn with_weight(mut self, index: usize, weight: f64) -> Self {
        self.selected_event_weight_index = Some(index);
        self.original_event_weight = Some(weight);
        self
    }

    fn with_support_outcome(mut self, outcome: PdfSupportOutcome) -> Self {
        self.support_outcome = Some(outcome);
        self
    }
}

fn supported_proton_parton(pdg_id: i32) -> bool {
    pdg_id == 21 || (1..=5).contains(&pdg_id.abs())
}

pub fn identify_proton_pdf_entry(
    event: &HepMcEvent,
    provenance: Option<&HepMcRunProvenance>,
) -> Result<ProtonPdfEntry, (PdfReweightingInvalidReason, String)> {
    let beams: Vec<i32> = event
        .beam_particles()
        .map(|particle| particle.pdg_id)
        .collect();
    if beams.len() != 2
        || beams.iter().filter(|&&id| id == ELECTRON_PDG_ID).count() != 1
        || beams.iter().filter(|&&id| id == PROTON_PDG_ID).count() != 1
    {
        return Err((
            PdfReweightingInvalidReason::InvalidBeamConfiguration,
            format!("expected exactly one status-4 electron and proton beam, observed {beams:?}"),
        ));
    }

    if let Some(provenance) = provenance {
        if let (Some(first), Some(second)) =
            (provenance.beam_particle_id_1, provenance.beam_particle_id_2)
        {
            let valid = (first == ELECTRON_PDG_ID && second == PROTON_PDG_ID)
                || (first == PROTON_PDG_ID && second == ELECTRON_PDG_ID);
            if !valid {
                return Err((
                    PdfReweightingInvalidReason::InvalidBeamConfiguration,
                    format!(
                        "run provenance beam IDs ({first}, {second}) are not the supported e- p channel"
                    ),
                ));
            }
        }
    }

    let Some(pdf) = event.pdf_info.as_ref() else {
        return Err((
            PdfReweightingInvalidReason::MissingPdfInfo,
            "event has no GenPdfInfo attribute".to_owned(),
        ));
    };

    let entries = [
        (
            PdfEntrySide::First,
            pdf.incoming_parton_id_1,
            pdf.x1,
            pdf.xf1,
            pdf.pdf_id_1,
        ),
        (
            PdfEntrySide::Second,
            pdf.incoming_parton_id_2,
            pdf.x2,
            pdf.xf2,
            pdf.pdf_id_2,
        ),
    ];
    let lepton_count = entries
        .iter()
        .filter(|(_, flavor, _, _, _)| *flavor == ELECTRON_PDG_ID)
        .count();
    if lepton_count != 1 {
        return Err((
            PdfReweightingInvalidReason::AmbiguousPdfEntries,
            format!(
                "expected exactly one electron-side GenPdfInfo entry, observed flavors ({}, {})",
                pdf.incoming_parton_id_1, pdf.incoming_parton_id_2
            ),
        ));
    }
    let (side, flavor, x, stored_xf, pdf_id) = entries
        .into_iter()
        .find(|(_, flavor, _, _, _)| *flavor != ELECTRON_PDG_ID)
        .expect("one non-lepton entry follows from the checked count");
    if !supported_proton_parton(flavor) {
        return Err((
            PdfReweightingInvalidReason::UnsupportedFlavor,
            format!("unsupported proton-side hard flavor {flavor}"),
        ));
    }
    if !x.is_finite() || x <= 0.0 || x >= 1.0 {
        return Err((
            PdfReweightingInvalidReason::InvalidX,
            format!("invalid proton-side x={x}"),
        ));
    }
    if !pdf.scale.is_finite() || pdf.scale <= 0.0 {
        return Err((
            PdfReweightingInvalidReason::InvalidScale,
            format!("invalid GenPdfInfo scale={} GeV", pdf.scale),
        ));
    }
    if !stored_xf.is_finite() {
        return Err((
            PdfReweightingInvalidReason::NonFiniteStoredNominalXf,
            format!("stored nominal xf is {stored_xf}"),
        ));
    }
    if stored_xf <= 0.0 {
        return Err((
            PdfReweightingInvalidReason::NonPositiveStoredNominalXf,
            format!("stored nominal xf must be positive, got {stored_xf}"),
        ));
    }

    Ok(ProtonPdfEntry {
        side,
        flavor,
        x,
        scale_gev: pdf.scale,
        stored_xf,
        pdf_id,
    })
}

fn select_event_weight(
    event: &HepMcEvent,
    requested_index: Option<usize>,
) -> Result<(usize, f64), (PdfReweightingInvalidReason, String)> {
    if event.weights.is_empty() {
        return Err((
            PdfReweightingInvalidReason::MissingEventWeight,
            "event has no HepMC3 W record".to_owned(),
        ));
    }
    let index = match (event.weights.len(), requested_index) {
        (1, None) => 0,
        (1, Some(index)) => index,
        (_, None) => {
            return Err((
                PdfReweightingInvalidReason::MultipleEventWeightsRequireIndex,
                format!(
                    "event has {} weights; --event-weight-index is required",
                    event.weights.len()
                ),
            ))
        }
        (_, Some(index)) => index,
    };
    let Some(&weight) = event.weights.get(index) else {
        return Err((
            PdfReweightingInvalidReason::EventWeightIndexOutOfRange,
            format!(
                "weight index {index} is outside event weight range 0..{}",
                event.weights.len().saturating_sub(1)
            ),
        ));
    };
    if !weight.is_finite() {
        return Err((
            PdfReweightingInvalidReason::NonFiniteEventWeight,
            format!("event weight at index {index} is {weight}"),
        ));
    }
    Ok((index, weight))
}

pub fn reweight_event(
    event: &HepMcEvent,
    provenance: Option<&HepMcRunProvenance>,
    request: &PdfReweightingRequest,
    nominal_pdf: &dyn PdfWeightEvaluator,
    target_pdf: &dyn PdfWeightEvaluator,
) -> Result<PdfReweightingResult, PdfReweightingError> {
    request.validate()?;
    let base = |reason, message| {
        PdfReweightingResult::invalid(event.event_number, request, reason, message)
    };

    let entry = match identify_proton_pdf_entry(event, provenance) {
        Ok(entry) => entry,
        Err((reason, message)) => return Ok(base(reason, message)),
    };
    let support_outcome = request.support_contract.assess(entry.x, entry.scale_gev);
    if support_outcome != PdfSupportOutcome::InSupport {
        return Ok(base(
            PdfReweightingInvalidReason::OutsideStrictPdfSupport,
            format!(
                "strict support decision {support_outcome} for x={} and GenPdfInfo Q={} GeV within x=[{}, {}], Q=[{}, {}] GeV",
                entry.x,
                entry.scale_gev,
                request.support_contract.intersection.x_minimum,
                request.support_contract.intersection.x_maximum,
                request.support_contract.intersection.q_minimum_gev,
                request.support_contract.intersection.q_maximum_gev,
            ),
        )
        .with_entry(&entry)
        .with_support_outcome(support_outcome));
    }
    let (weight_index, original_weight) =
        match select_event_weight(event, request.event_weight_index) {
            Ok(weight) => weight,
            Err((reason, message)) => {
                return Ok(base(reason, message)
                    .with_entry(&entry)
                    .with_support_outcome(support_outcome))
            }
        };

    let nominal_xf = match nominal_pdf.xfx_at_scale(entry.flavor, entry.x, entry.scale_gev) {
        Ok(value) => value,
        Err(message) => {
            return Ok(base(
                PdfReweightingInvalidReason::NominalPdfEvaluationFailed,
                message,
            )
            .with_entry(&entry)
            .with_support_outcome(support_outcome)
            .with_weight(weight_index, original_weight))
        }
    };
    if !nominal_xf.is_finite() {
        return Ok(base(
            PdfReweightingInvalidReason::NonFiniteRecomputedNominalXf,
            format!("recomputed nominal xf is {nominal_xf}"),
        )
        .with_entry(&entry)
        .with_support_outcome(support_outcome)
        .with_weight(weight_index, original_weight));
    }
    if nominal_xf <= 0.0 {
        return Ok(base(
            PdfReweightingInvalidReason::NonPositiveRecomputedNominalXf,
            format!("recomputed nominal xf must be positive, got {nominal_xf}"),
        )
        .with_entry(&entry)
        .with_weight(weight_index, original_weight));
    }

    let relative_difference = (entry.stored_xf - nominal_xf).abs()
        / entry.stored_xf.abs().max(RELATIVE_DENOMINATOR_EPSILON);
    let target_xf = match target_pdf.xfx_at_scale(entry.flavor, entry.x, entry.scale_gev) {
        Ok(value) => value,
        Err(message) => {
            let mut result = base(
                PdfReweightingInvalidReason::TargetPdfEvaluationFailed,
                message,
            )
            .with_entry(&entry)
            .with_support_outcome(support_outcome)
            .with_weight(weight_index, original_weight);
            result.recomputed_nominal_xf = Some(nominal_xf);
            result.stored_nominal_relative_difference = Some(relative_difference);
            return Ok(result);
        }
    };

    let mut result = PdfReweightingResult::invalid(
        event.event_number,
        request,
        PdfReweightingInvalidReason::NonFiniteRatio,
        "uninitialized ratio",
    )
    .with_entry(&entry)
    .with_support_outcome(support_outcome)
    .with_weight(weight_index, original_weight);
    result.recomputed_nominal_xf = Some(nominal_xf);
    result.target_xf = Some(target_xf);
    result.stored_nominal_relative_difference = Some(relative_difference);

    if !target_xf.is_finite() {
        result.invalid_reason = Some(PdfReweightingInvalidReason::NonFiniteTargetXf);
        result.invalid_message = Some(format!("target xf is {target_xf}"));
        return Ok(result);
    }
    if target_xf < 0.0 {
        result.invalid_reason = Some(PdfReweightingInvalidReason::NegativeTargetXf);
        result.invalid_message = Some(format!(
            "target xf is negative ({target_xf}); it cannot define a non-negative importance ratio"
        ));
        return Ok(result);
    }
    if relative_difference > request.nominal_xf_relative_tolerance {
        result.invalid_reason = Some(PdfReweightingInvalidReason::NominalXfMismatch);
        result.invalid_message = Some(format!(
            "stored/recomputed nominal xf relative difference {relative_difference:.6e} exceeds predeclared tolerance {:.6e}",
            request.nominal_xf_relative_tolerance
        ));
        return Ok(result);
    }

    let ratio_stored = target_xf / entry.stored_xf;
    let ratio_recomputed = target_xf / nominal_xf;
    result.ratio_stored_denominator = Some(ratio_stored);
    result.ratio_recomputed_denominator = Some(ratio_recomputed);
    let primary_ratio = match request.denominator_policy {
        DenominatorPolicy::Stored => ratio_stored,
        DenominatorPolicy::Recomputed => ratio_recomputed,
    };
    if !ratio_stored.is_finite() || !ratio_recomputed.is_finite() || !primary_ratio.is_finite() {
        result.invalid_reason = Some(PdfReweightingInvalidReason::NonFiniteRatio);
        result.invalid_message = Some(format!(
            "non-finite ratio: stored={ratio_stored}, recomputed={ratio_recomputed}"
        ));
        return Ok(result);
    }
    let target_weight = original_weight * primary_ratio;
    if !target_weight.is_finite() {
        result.invalid_reason = Some(PdfReweightingInvalidReason::NonFiniteTargetWeight);
        result.invalid_message = Some(format!(
            "target weight {original_weight} * {primary_ratio} is non-finite"
        ));
        return Ok(result);
    }

    result.primary_ratio = Some(primary_ratio);
    result.target_event_weight = Some(target_weight);
    result.valid = true;
    result.invalid_reason = None;
    result.invalid_message = None;
    Ok(result)
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EffectiveSampleSize {
    pub signed: f64,
    pub signed_fraction: f64,
    pub absolute_weight: f64,
    pub absolute_weight_fraction: f64,
    pub reuse_threshold: f64,
    pub direct_regeneration_required: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RatioStatistics {
    pub minimum: f64,
    pub median: f64,
    pub mean: f64,
    pub maximum: f64,
    pub p90: f64,
    pub p95: f64,
    pub p99: f64,
    pub p99_9: f64,
    pub coefficient_of_variation: Option<f64>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct WeightStatistics {
    pub event_count: usize,
    pub zero_weights: usize,
    pub negative_weights: usize,
    pub non_finite_weights: usize,
    pub sum_weights: f64,
    pub sum_absolute_weights: f64,
    pub sum_squared_weights: f64,
    pub effective_sample_size: EffectiveSampleSize,
    pub weight_distribution: Option<RatioStatistics>,
    pub ratios: Option<RatioStatistics>,
}

impl WeightStatistics {
    #[must_use]
    pub fn from_weights(weights: &[f64], ratios: &[f64]) -> Self {
        let finite_weights: Vec<f64> = weights
            .iter()
            .copied()
            .filter(|value| value.is_finite())
            .collect();
        let event_count = weights.len();
        let non_finite_weights = event_count - finite_weights.len();
        let zero_weights = finite_weights.iter().filter(|&&value| value == 0.0).count();
        let negative_weights = finite_weights.iter().filter(|&&value| value < 0.0).count();
        let sum_weights: f64 = finite_weights.iter().sum();
        let sum_absolute_weights: f64 = finite_weights.iter().map(|value| value.abs()).sum();
        let sum_squared_weights: f64 = finite_weights.iter().map(|value| value * value).sum();
        let signed = if sum_squared_weights > 0.0 {
            sum_weights * sum_weights / sum_squared_weights
        } else {
            0.0
        };
        let absolute_weight = if sum_squared_weights > 0.0 {
            sum_absolute_weights * sum_absolute_weights / sum_squared_weights
        } else {
            0.0
        };
        let denominator = event_count as f64;
        let signed_fraction = if event_count > 0 {
            signed / denominator
        } else {
            0.0
        };
        let absolute_weight_fraction = if event_count > 0 {
            absolute_weight / denominator
        } else {
            0.0
        };

        Self {
            event_count,
            zero_weights,
            negative_weights,
            non_finite_weights,
            sum_weights,
            sum_absolute_weights,
            sum_squared_weights,
            effective_sample_size: EffectiveSampleSize {
                signed,
                signed_fraction,
                absolute_weight,
                absolute_weight_fraction,
                reuse_threshold: PDF_REUSE_ESS_FRACTION_THRESHOLD,
                direct_regeneration_required: signed_fraction < PDF_REUSE_ESS_FRACTION_THRESHOLD,
            },
            weight_distribution: ratio_statistics(&finite_weights),
            ratios: ratio_statistics(ratios),
        }
    }
}

fn percentile(sorted: &[f64], probability: f64) -> f64 {
    if sorted.len() == 1 {
        return sorted[0];
    }
    let position = probability * (sorted.len() - 1) as f64;
    let lower = position.floor() as usize;
    let upper = position.ceil() as usize;
    if lower == upper {
        sorted[lower]
    } else {
        let fraction = position - lower as f64;
        sorted[lower] * (1.0 - fraction) + sorted[upper] * fraction
    }
}

fn ratio_statistics(ratios: &[f64]) -> Option<RatioStatistics> {
    let mut finite: Vec<f64> = ratios
        .iter()
        .copied()
        .filter(|value| value.is_finite())
        .collect();
    if finite.is_empty() {
        return None;
    }
    finite.sort_by(f64::total_cmp);
    let mean = finite.iter().sum::<f64>() / finite.len() as f64;
    let variance = finite
        .iter()
        .map(|value| (value - mean) * (value - mean))
        .sum::<f64>()
        / finite.len() as f64;
    Some(RatioStatistics {
        minimum: finite[0],
        median: percentile(&finite, 0.5),
        mean,
        maximum: *finite.last().expect("non-empty ratios"),
        p90: percentile(&finite, 0.90),
        p95: percentile(&finite, 0.95),
        p99: percentile(&finite, 0.99),
        p99_9: percentile(&finite, 0.999),
        coefficient_of_variation: if mean != 0.0 {
            Some(variance.sqrt() / mean.abs())
        } else {
            None
        },
    })
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ScalarDistributionStatistics {
    pub count: usize,
    pub median: f64,
    pub p95: f64,
    pub p99: f64,
    pub maximum: f64,
    pub fraction_outside_tolerance: f64,
    pub tolerance: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PdfReweightingDiagnostics {
    pub total_events: usize,
    pub valid_events: usize,
    pub invalid_events: usize,
    pub invalid_by_reason: BTreeMap<String, usize>,
    pub overall: WeightStatistics,
    pub nominal_xf_consistency: Option<ScalarDistributionStatistics>,
    pub by_flavor: BTreeMap<String, WeightStatistics>,
    pub by_x_region: BTreeMap<String, WeightStatistics>,
    pub by_scale_region: BTreeMap<String, WeightStatistics>,
}

#[derive(Debug, Default)]
struct GroupValues {
    weights: Vec<f64>,
    ratios: Vec<f64>,
}

impl GroupValues {
    fn push(&mut self, weight: f64, ratio: f64) {
        self.weights.push(weight);
        self.ratios.push(ratio);
    }

    fn into_statistics(self) -> WeightStatistics {
        WeightStatistics::from_weights(&self.weights, &self.ratios)
    }
}

/// Incremental diagnostics builder for a streaming event source.
///
/// It retains only the scalar samples required for exact tail quantiles and
/// grouped ESS calculations, never complete events or event-level result
/// records. The compact event diagnostics remain authoritative on disk.
#[derive(Debug, Default)]
pub struct PdfReweightingAccumulator {
    total_events: usize,
    valid_events: usize,
    invalid_by_reason: BTreeMap<String, usize>,
    weights: Vec<f64>,
    ratios: Vec<f64>,
    nominal_xf_relative_differences: Vec<f64>,
    by_flavor: BTreeMap<String, GroupValues>,
    by_x_region: BTreeMap<String, GroupValues>,
    by_scale_region: BTreeMap<String, GroupValues>,
}

impl PdfReweightingAccumulator {
    pub fn push(&mut self, result: &PdfReweightingResult) {
        self.total_events += 1;
        if let Some(difference) = result
            .stored_nominal_relative_difference
            .filter(|value| value.is_finite())
        {
            self.nominal_xf_relative_differences.push(difference);
        }
        if !result.valid {
            let reason = result
                .invalid_reason
                .map(|reason| reason.to_string())
                .unwrap_or_else(|| "unknown".to_owned());
            *self.invalid_by_reason.entry(reason).or_insert(0) += 1;
            return;
        }

        self.valid_events += 1;
        let (Some(weight), Some(ratio)) = (result.target_event_weight, result.primary_ratio) else {
            return;
        };
        self.weights.push(weight);
        self.ratios.push(ratio);
        if let Some(flavor) = result.proton_side_flavor {
            self.by_flavor
                .entry(flavor.to_string())
                .or_default()
                .push(weight, ratio);
        }
        if let Some(x) = result.proton_side_x {
            let region = match x {
                value if value < 1.0e-3 => "x_lt_1e-3",
                value if value < 1.0e-2 => "x_1e-3_to_1e-2",
                value if value < 1.0e-1 => "x_1e-2_to_1e-1",
                _ => "x_ge_1e-1",
            };
            self.by_x_region
                .entry(region.to_owned())
                .or_default()
                .push(weight, ratio);
        }
        if let Some(scale) = result.pdf_scale_gev {
            let region = match scale {
                value if value < 2.0 => "q_lt_2",
                value if value < 5.0 => "q_2_to_5",
                value if value < 10.0 => "q_5_to_10",
                value if value < 100.0 => "q_10_to_100",
                _ => "q_ge_100",
            };
            self.by_scale_region
                .entry(region.to_owned())
                .or_default()
                .push(weight, ratio);
        }
    }

    #[must_use]
    pub fn finish(mut self, tolerance: f64) -> PdfReweightingDiagnostics {
        self.nominal_xf_relative_differences.sort_by(f64::total_cmp);
        let nominal_xf_consistency = if self.nominal_xf_relative_differences.is_empty() {
            None
        } else {
            let differences = &self.nominal_xf_relative_differences;
            Some(ScalarDistributionStatistics {
                count: differences.len(),
                median: percentile(differences, 0.5),
                p95: percentile(differences, 0.95),
                p99: percentile(differences, 0.99),
                maximum: *differences.last().expect("non-empty differences"),
                fraction_outside_tolerance: differences
                    .iter()
                    .filter(|&&value| value > tolerance)
                    .count() as f64
                    / differences.len() as f64,
                tolerance,
            })
        };
        let group_statistics = |groups: BTreeMap<String, GroupValues>| {
            groups
                .into_iter()
                .map(|(key, values)| (key, values.into_statistics()))
                .collect()
        };

        PdfReweightingDiagnostics {
            total_events: self.total_events,
            valid_events: self.valid_events,
            invalid_events: self.total_events - self.valid_events,
            invalid_by_reason: self.invalid_by_reason,
            overall: WeightStatistics::from_weights(&self.weights, &self.ratios),
            nominal_xf_consistency,
            by_flavor: group_statistics(self.by_flavor),
            by_x_region: group_statistics(self.by_x_region),
            by_scale_region: group_statistics(self.by_scale_region),
        }
    }
}

#[must_use]
pub fn summarize_reweighting(
    results: &[PdfReweightingResult],
    tolerance: f64,
) -> PdfReweightingDiagnostics {
    let mut accumulator = PdfReweightingAccumulator::default();
    for result in results {
        accumulator.push(result);
    }
    accumulator.finish(tolerance)
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RunCompatibilityIssue {
    pub field: String,
    pub nominal: String,
    pub direct_target: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RunCompatibilityReport {
    pub compatible: bool,
    pub allowed_differences: Vec<String>,
    pub incompatibilities: Vec<RunCompatibilityIssue>,
}

fn compare_field<T: fmt::Debug + PartialEq>(
    issues: &mut Vec<RunCompatibilityIssue>,
    field: &str,
    nominal: &T,
    direct: &T,
) {
    if nominal != direct {
        issues.push(RunCompatibilityIssue {
            field: field.to_owned(),
            nominal: format!("{nominal:?}"),
            direct_target: format!("{direct:?}"),
        });
    }
}

fn compare_required_field<T: fmt::Debug + PartialEq>(
    issues: &mut Vec<RunCompatibilityIssue>,
    field: &str,
    nominal: &Option<T>,
    direct: &Option<T>,
) {
    if nominal.is_none() || direct.is_none() || nominal != direct {
        issues.push(RunCompatibilityIssue {
            field: field.to_owned(),
            nominal: format!("{nominal:?}"),
            direct_target: format!("{direct:?}"),
        });
    }
}

#[must_use]
pub fn validate_run_compatibility(
    nominal: &HepMcRunProvenance,
    direct_target: &HepMcRunProvenance,
) -> RunCompatibilityReport {
    let mut issues = Vec::new();
    compare_field(
        &mut issues,
        "schema_version",
        &nominal.schema_version,
        &direct_target.schema_version,
    );
    compare_field(
        &mut issues,
        "process",
        &nominal.process,
        &direct_target.process,
    );
    compare_field(
        &mut issues,
        "event_schema_version",
        &nominal.event_schema_version,
        &direct_target.event_schema_version,
    );
    compare_field(
        &mut issues,
        "electroweak_process",
        &nominal.electroweak_process,
        &direct_target.electroweak_process,
    );
    compare_field(
        &mut issues,
        "event_selection",
        &nominal.event_selection,
        &direct_target.event_selection,
    );
    compare_field(
        &mut issues,
        "space_shower_dipole_recoil",
        &nominal.space_shower_dipole_recoil,
        &direct_target.space_shower_dipole_recoil,
    );
    compare_required_field(
        &mut issues,
        "beam_particle_id_1",
        &nominal.beam_particle_id_1,
        &direct_target.beam_particle_id_1,
    );
    compare_required_field(
        &mut issues,
        "beam_particle_id_2",
        &nominal.beam_particle_id_2,
        &direct_target.beam_particle_id_2,
    );
    compare_field(
        &mut issues,
        "electron_energy_gev",
        &nominal.electron_energy_gev,
        &direct_target.electron_energy_gev,
    );
    compare_field(
        &mut issues,
        "proton_energy_gev",
        &nominal.proton_energy_gev,
        &direct_target.proton_energy_gev,
    );
    compare_field(
        &mut issues,
        "pdf_set",
        &nominal.pdf_set,
        &direct_target.pdf_set,
    );
    compare_field(
        &mut issues,
        "parton_shower",
        &nominal.parton_shower,
        &direct_target.parton_shower,
    );
    compare_required_field(
        &mut issues,
        "multiparton_interactions",
        &nominal.multiparton_interactions,
        &direct_target.multiparton_interactions,
    );
    compare_field(
        &mut issues,
        "hadronization",
        &nominal.hadronization,
        &direct_target.hadronization,
    );
    compare_field(&mut issues, "cuts", &nominal.cuts, &direct_target.cuts);
    compare_field(
        &mut issues,
        "configured_event_count",
        &nominal.configured_event_count,
        &direct_target.configured_event_count,
    );
    compare_field(
        &mut issues,
        "generator_version",
        &nominal.generator_version,
        &direct_target.generator_version,
    );
    compare_field(
        &mut issues,
        "pythia_version",
        &nominal.pythia_version,
        &direct_target.pythia_version,
    );
    compare_field(
        &mut issues,
        "lhapdf_version",
        &nominal.lhapdf_version,
        &direct_target.lhapdf_version,
    );
    compare_field(
        &mut issues,
        "hepmc_version",
        &nominal.hepmc_version,
        &direct_target.hepmc_version,
    );
    compare_required_field(
        &mut issues,
        "git_commit",
        &nominal.git_commit,
        &direct_target.git_commit,
    );
    if nominal.git_dirty != Some(false)
        || direct_target.git_dirty != Some(false)
        || nominal.git_dirty != direct_target.git_dirty
    {
        issues.push(RunCompatibilityIssue {
            field: "git_dirty".to_owned(),
            nominal: format!("{:?}", nominal.git_dirty),
            direct_target: format!("{:?}", direct_target.git_dirty),
        });
    }
    let support_compatible = match (
        nominal.pdf_support_contract.as_ref(),
        direct_target.pdf_support_contract.as_ref(),
        nominal.pdf_member,
        direct_target.pdf_member,
    ) {
        (Some(left), Some(right), Some(left_member), Some(right_member)) => {
            left.nominal_member == left_member
                && right.nominal_member == right_member
                && left.same_reusable_domain(right)
        }
        _ => false,
    };
    if !support_compatible {
        issues.push(RunCompatibilityIssue {
            field: "pdf_support_contract".to_owned(),
            nominal: format!("{:?}", nominal.pdf_support_contract),
            direct_target: format!("{:?}", direct_target.pdf_support_contract),
        });
    }

    RunCompatibilityReport {
        compatible: issues.is_empty(),
        allowed_differences: vec![
            "pdf_member".to_owned(),
            "configured_seed".to_owned(),
            "generator_seed".to_owned(),
            "build_timestamp".to_owned(),
            "source_run_directory".to_owned(),
            "run_identity".to_owned(),
        ],
        incompatibilities: issues,
    }
}

#[derive(Debug, Clone, PartialEq, Deserialize)]
pub struct InclusiveObservableRow {
    pub event_number: i64,
    pub event_weight: f64,
    #[serde(rename = "Q2")]
    pub q2: f64,
    pub x: f64,
    pub y: f64,
    #[serde(rename = "W2")]
    pub w2: f64,
    #[serde(rename = "scattered_electron_E")]
    pub scattered_electron_energy: f64,
    pub scattered_electron_px: f64,
    pub scattered_electron_py: f64,
    pub scattered_electron_pz: f64,
    pub number_of_final_state_particles: usize,
    pub number_of_charged_final_state_particles: usize,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EventObservableSummary {
    pub event_number: i64,
    pub generator_csv_event_number: i64,
    pub log10_x: f64,
    pub log10_q2: f64,
    pub y: f64,
    pub log10_w2: f64,
    pub scattered_electron_energy: f64,
    pub scattered_electron_cos_theta: f64,
    pub final_state_multiplicity: usize,
    pub charged_final_state_multiplicity: usize,
    pub visible_final_state_energy: f64,
    pub scalar_final_state_pt_sum: f64,
    pub leading_stable_hadron_pt: f64,
    pub electron_muon_fraction: f64,
    pub photon_fraction: f64,
    pub neutrino_fraction: f64,
    pub hadron_fraction: f64,
    pub other_fraction: f64,
}

fn finite_positive(name: &str, value: f64) -> Result<f64, String> {
    if value.is_finite() && value > 0.0 {
        Ok(value)
    } else {
        Err(format!("{name} must be finite and positive, got {value}"))
    }
}

#[must_use]
fn is_neutrino(pdg_id: i32) -> bool {
    matches!(pdg_id.abs(), 12 | 14 | 16)
}

#[must_use]
fn is_hadron(pdg_id: i32) -> bool {
    pdg_id.abs() >= 100
}

pub fn extract_event_observables(
    event: &HepMcEvent,
    row: &InclusiveObservableRow,
) -> Result<EventObservableSummary, String> {
    // The backend writes HepMC and CSV records in the same accepted-event
    // loop, so sequential order is authoritative. HepMC's event number comes
    // from PYTHIA's counter and can skip after generator failures or custom
    // vetoes, while the CSV number is the contiguous output-row index.
    for (name, value) in [
        ("event weight", row.event_weight),
        ("y", row.y),
        ("scattered electron energy", row.scattered_electron_energy),
        ("scattered electron px", row.scattered_electron_px),
        ("scattered electron py", row.scattered_electron_py),
        ("scattered electron pz", row.scattered_electron_pz),
    ] {
        if !value.is_finite() {
            return Err(format!("{name} must be finite, got {value}"));
        }
    }
    let x = finite_positive("x", row.x)?;
    let q2 = finite_positive("Q2", row.q2)?;
    let w2 = finite_positive("W2", row.w2)?;
    if !(0.0..1.0).contains(&row.y) {
        return Err(format!("y must be in [0,1), got {}", row.y));
    }
    let scattered_p = (row.scattered_electron_px * row.scattered_electron_px
        + row.scattered_electron_py * row.scattered_electron_py
        + row.scattered_electron_pz * row.scattered_electron_pz)
        .sqrt();
    if !scattered_p.is_finite() || scattered_p <= 0.0 {
        return Err(format!("scattered electron momentum is {scattered_p}"));
    }

    let final_particles: Vec<_> = event.final_state_particles().collect();
    if final_particles.len() != row.number_of_final_state_particles {
        return Err(format!(
            "HepMC final-state multiplicity {} differs from generator CSV {}",
            final_particles.len(),
            row.number_of_final_state_particles
        ));
    }
    let mut visible_energy = 0.0;
    let mut scalar_pt = 0.0;
    let mut leading_hadron_pt: f64 = 0.0;
    let mut category_counts = [0usize; 5];
    for particle in &final_particles {
        let pt = (particle.px * particle.px + particle.py * particle.py).sqrt();
        if !particle.energy.is_finite() || !pt.is_finite() {
            return Err(format!("non-finite final-state particle {}", particle.id));
        }
        scalar_pt += pt;
        let abs_id = particle.pdg_id.abs();
        if is_neutrino(abs_id) {
            category_counts[2] += 1;
        } else {
            visible_energy += particle.energy;
            if matches!(abs_id, 11 | 13) {
                category_counts[0] += 1;
            } else if abs_id == 22 {
                category_counts[1] += 1;
            } else if is_hadron(abs_id) {
                category_counts[3] += 1;
                leading_hadron_pt = leading_hadron_pt.max(pt);
            } else {
                category_counts[4] += 1;
            }
        }
    }
    let count = final_particles.len() as f64;
    let fraction = |index: usize| {
        if count > 0.0 {
            category_counts[index] as f64 / count
        } else {
            0.0
        }
    };

    Ok(EventObservableSummary {
        event_number: event.event_number,
        generator_csv_event_number: row.event_number,
        log10_x: x.log10(),
        log10_q2: q2.log10(),
        y: row.y,
        log10_w2: w2.log10(),
        scattered_electron_energy: row.scattered_electron_energy,
        scattered_electron_cos_theta: row.scattered_electron_pz / scattered_p,
        final_state_multiplicity: row.number_of_final_state_particles,
        charged_final_state_multiplicity: row.number_of_charged_final_state_particles,
        visible_final_state_energy: visible_energy,
        scalar_final_state_pt_sum: scalar_pt,
        leading_stable_hadron_pt: leading_hadron_pt,
        electron_muon_fraction: fraction(0),
        photon_fraction: fraction(1),
        neutrino_fraction: fraction(2),
        hadron_fraction: fraction(3),
        other_fraction: fraction(4),
    })
}
