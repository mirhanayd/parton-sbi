//! Streaming extraction of PartonSBI's HepMC3 ASCII v3 event records.
//!
//! The supported particle layout is the one emitted by HepMC3 3.3.0:
//! `P id parent_object pdg_id px py pz energy mass status`. A positive
//! `parent_object` denotes a parent particle and therefore an implicit vertex;
//! a negative value denotes an explicitly serialized vertex.

use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{BTreeMap, HashMap, HashSet, VecDeque};
use std::error::Error;
use std::fmt;
use std::fs::File;
use std::io::{self, BufRead, BufReader};
use std::path::{Path, PathBuf};

/// A preserved HepMC3 attribute, including attributes not interpreted here.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct HepMcAttribute {
    pub owner_id: i32,
    pub name: String,
    pub value: String,
    pub source_line: usize,
}

/// The standard HepMC3 `GenPdfInfo` payload emitted by PYTHIA's converter.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HepMcPdfInfo {
    pub incoming_parton_id_1: i32,
    pub incoming_parton_id_2: i32,
    pub x1: f64,
    pub x2: f64,
    pub scale: f64,
    pub xf1: f64,
    pub xf2: f64,
    pub pdf_id_1: i32,
    pub pdf_id_2: i32,
    /// Forward-compatible storage for fields beyond HepMC3 3.3.0's nine fields.
    pub additional_fields: Vec<String>,
}

/// One particle and its reconstructed graph connectivity.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HepMcParticle {
    pub id: i32,
    /// The exact second field of the ASCII `P` record.
    pub production_reference: i32,
    /// Explicit or reconstructed implicit production vertex.
    pub production_vertex_id: Option<i32>,
    pub pdg_id: i32,
    pub px: f64,
    pub py: f64,
    pub pz: f64,
    pub energy: f64,
    pub generated_mass: f64,
    pub status: i32,
    pub end_vertex_id: Option<i32>,
    pub parent_particle_ids: Vec<i32>,
    pub child_particle_ids: Vec<i32>,
    pub additional_fields: Vec<String>,
    pub source_line: usize,
}

/// One explicit or HepMC3-reconstructed implicit event vertex.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HepMcVertex {
    pub id: i32,
    pub status: i32,
    pub position: Option<[f64; 4]>,
    pub incoming_particle_ids: Vec<i32>,
    pub outgoing_particle_ids: Vec<i32>,
    pub implicit: bool,
    pub source_line: Option<usize>,
}

/// One complete event yielded by the streaming reader.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HepMcEvent {
    pub event_number: i64,
    pub declared_vertex_count: usize,
    pub declared_particle_count: usize,
    pub event_position: Option<[f64; 4]>,
    pub momentum_unit: Option<String>,
    pub length_unit: Option<String>,
    pub weights: Vec<f64>,
    pub event_scale: Option<f64>,
    pub alpha_qcd: Option<f64>,
    pub alpha_qed: Option<f64>,
    pub signal_process_id: Option<i32>,
    pub pdf_info: Option<HepMcPdfInfo>,
    pub attributes: Vec<HepMcAttribute>,
    pub particles: Vec<HepMcParticle>,
    pub vertices: Vec<HepMcVertex>,
    pub source_start_line: usize,
    pub source_end_line: usize,
}

impl HepMcEvent {
    /// Stable generator-level final-state particles.
    #[must_use]
    pub fn final_state_particles(&self) -> impl Iterator<Item = &HepMcParticle> {
        self.particles
            .iter()
            .filter(|particle| particle.status == 1)
    }

    /// Incoming beam particles, as marked by PYTHIA/HepMC status 4.
    #[must_use]
    pub fn beam_particles(&self) -> impl Iterator<Item = &HepMcParticle> {
        self.particles
            .iter()
            .filter(|particle| particle.status == 4)
    }

    #[must_use]
    pub fn particle(&self, id: i32) -> Option<&HepMcParticle> {
        self.particles.iter().find(|particle| particle.id == id)
    }

    /// Select the final electron descended from the status-4 incoming electron.
    ///
    /// This mirrors the generator's ancestry-based selection. The fallback to
    /// any stable electron is retained for records without usable genealogy.
    #[must_use]
    pub fn scattered_electron(&self) -> Option<&HepMcParticle> {
        let beam_id = self
            .beam_particles()
            .find(|particle| particle.pdg_id == 11)
            .map(|particle| particle.id);

        if let Some(beam_id) = beam_id {
            let by_id: HashMap<i32, &HepMcParticle> = self
                .particles
                .iter()
                .map(|particle| (particle.id, particle))
                .collect();
            let mut descendants = HashSet::new();
            let mut queue = VecDeque::from([beam_id]);
            while let Some(id) = queue.pop_front() {
                if !descendants.insert(id) {
                    continue;
                }
                if let Some(particle) = by_id.get(&id) {
                    queue.extend(particle.child_particle_ids.iter().copied());
                }
            }
            if let Some(electron) = self.particles.iter().find(|particle| {
                particle.pdg_id == 11 && particle.status == 1 && descendants.contains(&particle.id)
            }) {
                return Some(electron);
            }
        }

        self.particles
            .iter()
            .find(|particle| particle.pdg_id == 11 && particle.status == 1)
    }
}

/// Kinematic cuts captured in run-level JSON provenance.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct HepMcRunCuts {
    pub q2_min_gev2: Option<f64>,
    pub q2_max_gev2: Option<f64>,
    pub x_min: Option<f64>,
    pub x_max: Option<f64>,
    pub y_min: Option<f64>,
    pub y_max: Option<f64>,
}

/// Run provenance kept separate from observed event features.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HepMcRunProvenance {
    pub source_run_directory: PathBuf,
    pub config_path: PathBuf,
    pub metadata_path: PathBuf,
    pub schema_version: Option<i64>,
    pub process: Option<String>,
    pub event_schema_version: Option<i64>,
    pub electroweak_process: Option<String>,
    pub event_selection: Option<String>,
    pub space_shower_dipole_recoil: Option<bool>,
    pub beam_particle_id_1: Option<i32>,
    pub beam_particle_id_2: Option<i32>,
    pub electron_energy_gev: Option<f64>,
    pub proton_energy_gev: Option<f64>,
    pub pdf_set: Option<String>,
    pub pdf_member: Option<i32>,
    pub configured_seed: Option<i64>,
    pub generator_seed: Option<i64>,
    pub parton_shower: Option<bool>,
    pub hadronization: Option<bool>,
    pub cuts: HepMcRunCuts,
    pub configured_event_count: Option<u64>,
    pub accepted_event_count: Option<u64>,
    pub generator_version: Option<String>,
    pub apfelxx_version: Option<String>,
    pub lhapdf_version: Option<String>,
    pub pythia_version: Option<String>,
    pub hepmc_version: Option<String>,
    pub git_commit: Option<String>,
    pub git_dirty: Option<bool>,
    pub build_timestamp: Option<String>,
}

/// Final run-level generation and rate-normalization statistics.
///
/// `GenCrossSection` inside an event is only PYTHIA's running estimate at that
/// point in generation. These fields come from the final `summary.json` and
/// therefore provide the authoritative final estimate for newly generated
/// Phase 1A runs.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HepMcRunSummary {
    pub source_summary_path: PathBuf,
    pub requested_events: Option<u64>,
    pub attempted_events: Option<u64>,
    pub accepted_events: Option<u64>,
    pub failed_events: Option<u64>,
    pub vetoed_cuts_events: Option<u64>,
    pub vetoed_conservation_events: Option<u64>,
    pub event_weight_semantics: Option<String>,
    pub pythia_weight_sum: Option<f64>,
    pub selected_weight_sum: Option<f64>,
    pub selected_weight_squared_sum: Option<f64>,
    pub selected_negative_weight_count: Option<u64>,
    pub sigma_gen_mb: Option<f64>,
    pub sigma_err_mb: Option<f64>,
    pub selected_weight_fraction: Option<f64>,
    pub selected_cross_section_mb: Option<f64>,
    pub selected_cross_section_pb: Option<f64>,
    pub rate_normalization_method: Option<String>,
}

impl HepMcRunSummary {
    pub fn load(run_directory: impl AsRef<Path>) -> Result<Self, HepMcError> {
        let source_summary_path = run_directory.as_ref().join("summary.json");
        let summary = read_json(&source_summary_path)?;
        Ok(Self {
            source_summary_path,
            requested_events: value_u64(&summary, "requested_events"),
            attempted_events: value_u64(&summary, "attempted_events"),
            accepted_events: value_u64(&summary, "accepted_events"),
            failed_events: value_u64(&summary, "failed_events"),
            vetoed_cuts_events: value_u64(&summary, "vetoed_cuts_events"),
            vetoed_conservation_events: value_u64(&summary, "vetoed_conservation_events"),
            event_weight_semantics: value_string(&summary, "event_weight_semantics"),
            pythia_weight_sum: value_f64(&summary, "pythia_weight_sum"),
            selected_weight_sum: value_f64(&summary, "selected_weight_sum"),
            selected_weight_squared_sum: value_f64(&summary, "selected_weight_squared_sum"),
            selected_negative_weight_count: value_u64(&summary, "selected_negative_weight_count"),
            sigma_gen_mb: value_f64(&summary, "sigma_gen_mb"),
            sigma_err_mb: value_f64(&summary, "sigma_err_mb"),
            selected_weight_fraction: value_f64(&summary, "selected_weight_fraction"),
            selected_cross_section_mb: value_f64(&summary, "selected_cross_section_mb"),
            selected_cross_section_pb: value_f64(&summary, "selected_cross_section_pb"),
            rate_normalization_method: value_string(&summary, "rate_normalization_method"),
        })
    }

    #[must_use]
    pub fn rate_normalization_established(&self) -> bool {
        [
            self.pythia_weight_sum,
            self.selected_weight_sum,
            self.selected_weight_squared_sum,
            self.sigma_gen_mb,
            self.sigma_err_mb,
            self.selected_cross_section_pb,
        ]
        .into_iter()
        .all(|value| value.is_some_and(f64::is_finite))
            && self.event_weight_semantics.is_some()
            && self.rate_normalization_method.is_some()
    }
}

impl HepMcRunProvenance {
    /// Load `config.json` and `metadata.json` from a PartonSBI run directory.
    pub fn load(run_directory: impl AsRef<Path>) -> Result<Self, HepMcError> {
        let source_run_directory = run_directory.as_ref().to_path_buf();
        let config_path = source_run_directory.join("config.json");
        let metadata_path = source_run_directory.join("metadata.json");
        let config = read_json(&config_path)?;
        let metadata = read_json(&metadata_path)?;

        let metadata_cuts = metadata.get("cuts");
        let cuts = HepMcRunCuts {
            q2_min_gev2: nested_f64(metadata_cuts, "q2_min_gev2")
                .or_else(|| value_f64(&config, "q2_min_gev2")),
            q2_max_gev2: nested_f64(metadata_cuts, "q2_max_gev2")
                .or_else(|| value_f64(&config, "q2_max_gev2")),
            x_min: nested_f64(metadata_cuts, "x_min").or_else(|| value_f64(&config, "x_min")),
            x_max: nested_f64(metadata_cuts, "x_max").or_else(|| value_f64(&config, "x_max")),
            y_min: nested_f64(metadata_cuts, "y_min").or_else(|| value_f64(&config, "y_min")),
            y_max: nested_f64(metadata_cuts, "y_max").or_else(|| value_f64(&config, "y_max")),
        };
        let pythia_version = value_string(&metadata, "pythia_version");

        Ok(Self {
            source_run_directory,
            config_path,
            metadata_path,
            schema_version: value_i64(&config, "schema_version"),
            process: value_string(&config, "process")
                .or_else(|| value_string(&metadata, "process")),
            event_schema_version: value_i64(&metadata, "event_schema_version"),
            electroweak_process: value_string(&metadata, "electroweak_process"),
            event_selection: value_string(&metadata, "event_selection"),
            space_shower_dipole_recoil: value_bool(&metadata, "space_shower_dipole_recoil"),
            beam_particle_id_1: value_i32(&metadata, "beam_particle_id_1")
                .or_else(|| value_i32(&config, "beam_particle_id_1")),
            beam_particle_id_2: value_i32(&metadata, "beam_particle_id_2")
                .or_else(|| value_i32(&config, "beam_particle_id_2")),
            electron_energy_gev: value_f64(&metadata, "electron_energy_gev")
                .or_else(|| value_f64(&config, "electron_energy_gev")),
            proton_energy_gev: value_f64(&metadata, "proton_energy_gev")
                .or_else(|| value_f64(&config, "proton_energy_gev")),
            pdf_set: value_string(&metadata, "pdf_set")
                .or_else(|| value_string(&config, "pdf_set")),
            pdf_member: value_i32(&metadata, "pdf_member")
                .or_else(|| value_i32(&config, "pdf_member")),
            configured_seed: value_i64(&config, "random_seed"),
            generator_seed: value_i64(&metadata, "random_seed"),
            parton_shower: value_bool(&metadata, "parton_shower_state")
                .or_else(|| value_bool(&config, "parton_shower")),
            hadronization: value_bool(&metadata, "hadronization_state")
                .or_else(|| value_bool(&config, "hadronization")),
            cuts,
            configured_event_count: value_u64(&config, "number_of_events"),
            accepted_event_count: value_u64(&metadata, "accepted_event_count"),
            generator_version: value_string(&metadata, "generator_version")
                .or_else(|| pythia_version.clone()),
            apfelxx_version: value_string(&metadata, "apfelxx_version")
                .or_else(|| value_string(&metadata, "apfel_version")),
            lhapdf_version: value_string(&metadata, "lhapdf_version"),
            pythia_version,
            hepmc_version: value_string(&metadata, "hepmc3_version")
                .or_else(|| value_string(&metadata, "hepmc_version")),
            git_commit: value_string(&metadata, "git_commit"),
            git_dirty: value_bool(&metadata, "git_dirty"),
            build_timestamp: value_string(&metadata, "build_timestamp"),
        })
    }

    /// Fill beam IDs only when they are absent from JSON and are observed as
    /// status-4 particles in an event from the same run.
    pub fn enrich_beam_ids_from_event(&mut self, event: &HepMcEvent) {
        let mut beam_ids = event.beam_particles().map(|particle| particle.pdg_id);
        if self.beam_particle_id_1.is_none() {
            self.beam_particle_id_1 = beam_ids.next();
        } else {
            let _ = beam_ids.next();
        }
        if self.beam_particle_id_2.is_none() {
            self.beam_particle_id_2 = beam_ids.next();
        }
    }
}

/// Context-rich errors from event or provenance extraction.
#[derive(Debug)]
pub enum HepMcError {
    Io {
        path: Option<PathBuf>,
        line_number: usize,
        event_number: Option<i64>,
        source: io::Error,
    },
    Parse {
        line_number: usize,
        event_number: Option<i64>,
        record: String,
        message: String,
    },
    Provenance {
        path: PathBuf,
        message: String,
    },
}

impl fmt::Display for HepMcError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io {
                path,
                line_number,
                event_number,
                source,
            } => write!(
                formatter,
                "HepMC3 I/O error{} at line {}{}: {}",
                path.as_ref()
                    .map(|path| format!(" in {}", path.display()))
                    .unwrap_or_default(),
                line_number,
                event_number
                    .map(|number| format!(", event {number}"))
                    .unwrap_or_default(),
                source
            ),
            Self::Parse {
                line_number,
                event_number,
                record,
                message,
            } => write!(
                formatter,
                "invalid HepMC3 record at line {}{}: {} ({})",
                line_number,
                event_number
                    .map(|number| format!(", event {number}"))
                    .unwrap_or_default(),
                message,
                record
            ),
            Self::Provenance { path, message } => {
                write!(
                    formatter,
                    "invalid run provenance in {}: {message}",
                    path.display()
                )
            }
        }
    }
}

impl Error for HepMcError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Io { source, .. } => Some(source),
            _ => None,
        }
    }
}

/// A streaming HepMC3 ASCII v3 reader.
pub struct HepMcReader<R: BufRead> {
    reader: R,
    source_path: Option<PathBuf>,
    line_number: usize,
    pending_line: Option<(usize, String)>,
    finished: bool,
    format_version: Option<String>,
}

impl HepMcReader<BufReader<File>> {
    /// Open a HepMC3 file without reading it into memory.
    pub fn open(path: impl AsRef<Path>) -> Result<Self, HepMcError> {
        let path = path.as_ref().to_path_buf();
        let file = File::open(&path).map_err(|source| HepMcError::Io {
            path: Some(path.clone()),
            line_number: 0,
            event_number: None,
            source,
        })?;
        Ok(Self::with_source(BufReader::new(file), Some(path)))
    }
}

impl<R: BufRead> HepMcReader<R> {
    #[must_use]
    pub fn new(reader: R) -> Self {
        Self::with_source(reader, None)
    }

    fn with_source(reader: R, source_path: Option<PathBuf>) -> Self {
        Self {
            reader,
            source_path,
            line_number: 0,
            pending_line: None,
            finished: false,
            format_version: None,
        }
    }

    #[must_use]
    pub fn format_version(&self) -> Option<&str> {
        self.format_version.as_deref()
    }

    /// Read and validate one event, retaining the next header for the next call.
    pub fn next_event(&mut self) -> Result<Option<HepMcEvent>, HepMcError> {
        if self.finished {
            return Ok(None);
        }

        let (start_line, header) = loop {
            let Some((line_number, line)) = self.read_line(None)? else {
                self.finished = true;
                return Ok(None);
            };
            let trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with('#') {
                continue;
            }
            if let Some(version) = trimmed.strip_prefix("HepMC::Version ") {
                self.format_version = Some(version.trim().to_owned());
                continue;
            }
            if trimmed == "HepMC::Asciiv3-END_EVENT_LISTING" {
                self.finished = true;
                return Ok(None);
            }
            if trimmed.starts_with("HepMC::") || matches!(trimmed.as_bytes()[0], b'A' | b'T' | b'W')
            {
                continue;
            }
            if trimmed.starts_with("E ") {
                break (line_number, trimmed.to_owned());
            }
            return Err(parse_error(
                line_number,
                None,
                trimmed,
                "record encountered outside an event",
            ));
        };

        let mut event = parse_event_header(start_line, &header)?;
        loop {
            let Some((line_number, line)) = self.read_line(Some(event.event_number))? else {
                self.finished = true;
                break;
            };
            let trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with('#') {
                continue;
            }
            if trimmed.starts_with("E ") {
                self.pending_line = Some((line_number, trimmed.to_owned()));
                break;
            }
            if trimmed == "HepMC::Asciiv3-END_EVENT_LISTING" {
                self.finished = true;
                break;
            }
            event.source_end_line = line_number;
            match trimmed.as_bytes()[0] {
                b'U' => parse_units(&mut event, line_number, trimmed)?,
                b'W' => parse_weights(&mut event, line_number, trimmed)?,
                b'A' => parse_attribute_record(&mut event, line_number, trimmed)?,
                b'V' => {
                    event
                        .vertices
                        .push(parse_vertex(line_number, event.event_number, trimmed)?)
                }
                b'P' => {
                    event
                        .particles
                        .push(parse_particle(line_number, event.event_number, trimmed)?)
                }
                _ if trimmed.starts_with("HepMC::") => {
                    self.finished = true;
                    break;
                }
                _ => {
                    return Err(parse_error(
                        line_number,
                        Some(event.event_number),
                        trimmed,
                        "unsupported record type inside event",
                    ));
                }
            }
        }

        finalize_event(&mut event)?;
        Ok(Some(event))
    }

    fn read_line(
        &mut self,
        event_number: Option<i64>,
    ) -> Result<Option<(usize, String)>, HepMcError> {
        if let Some(line) = self.pending_line.take() {
            return Ok(Some(line));
        }
        let mut line = String::new();
        let count = self
            .reader
            .read_line(&mut line)
            .map_err(|source| HepMcError::Io {
                path: self.source_path.clone(),
                line_number: self.line_number + 1,
                event_number,
                source,
            })?;
        if count == 0 {
            return Ok(None);
        }
        self.line_number += 1;
        Ok(Some((self.line_number, line)))
    }
}

impl<R: BufRead> Iterator for HepMcReader<R> {
    type Item = Result<HepMcEvent, HepMcError>;

    fn next(&mut self) -> Option<Self::Item> {
        match self.next_event() {
            Ok(Some(event)) => Some(Ok(event)),
            Ok(None) => None,
            Err(error) => {
                self.finished = true;
                Some(Err(error))
            }
        }
    }
}

fn parse_event_header(line_number: usize, record: &str) -> Result<HepMcEvent, HepMcError> {
    let fields: Vec<&str> = record.split_whitespace().collect();
    if fields.len() < 4 {
        return Err(parse_error(
            line_number,
            None,
            record,
            "E record requires event number and declared vertex/particle counts",
        ));
    }
    let event_number = parse_i64(fields[1], line_number, None, record, "event number")?;
    let declared_vertex_count = parse_usize(
        fields[2],
        line_number,
        Some(event_number),
        record,
        "vertex count",
    )?;
    if declared_vertex_count > i32::MAX as usize {
        return Err(parse_error(
            line_number,
            Some(event_number),
            record,
            "vertex count exceeds the HepMC3 signed-ID range",
        ));
    }
    let declared_particle_count = parse_usize(
        fields[3],
        line_number,
        Some(event_number),
        record,
        "particle count",
    )?;
    let event_position =
        parse_optional_position(&fields[4..], line_number, Some(event_number), record)?;
    Ok(HepMcEvent {
        event_number,
        declared_vertex_count,
        declared_particle_count,
        event_position,
        momentum_unit: None,
        length_unit: None,
        weights: Vec::new(),
        event_scale: None,
        alpha_qcd: None,
        alpha_qed: None,
        signal_process_id: None,
        pdf_info: None,
        attributes: Vec::new(),
        particles: Vec::new(),
        vertices: Vec::new(),
        source_start_line: line_number,
        source_end_line: line_number,
    })
}

fn parse_units(event: &mut HepMcEvent, line_number: usize, record: &str) -> Result<(), HepMcError> {
    let fields: Vec<&str> = record.split_whitespace().collect();
    if fields.len() != 3 {
        return Err(parse_error(
            line_number,
            Some(event.event_number),
            record,
            "U record requires momentum and length units",
        ));
    }
    event.momentum_unit = Some(fields[1].to_owned());
    event.length_unit = Some(fields[2].to_owned());
    Ok(())
}

fn parse_weights(
    event: &mut HepMcEvent,
    line_number: usize,
    record: &str,
) -> Result<(), HepMcError> {
    let fields: Vec<&str> = record.split_whitespace().collect();
    if fields.len() < 2 {
        return Err(parse_error(
            line_number,
            Some(event.event_number),
            record,
            "W record requires at least one weight",
        ));
    }
    event.weights = fields[1..]
        .iter()
        .map(|field| {
            parse_f64(
                field,
                line_number,
                Some(event.event_number),
                record,
                "event weight",
            )
        })
        .collect::<Result<Vec<_>, _>>()?;
    Ok(())
}

fn parse_attribute_record(
    event: &mut HepMcEvent,
    line_number: usize,
    record: &str,
) -> Result<(), HepMcError> {
    let mut fields = record
        .splitn(4, char::is_whitespace)
        .filter(|field| !field.is_empty());
    let _prefix = fields.next();
    let owner_text = fields.next().ok_or_else(|| {
        parse_error(
            line_number,
            Some(event.event_number),
            record,
            "A record requires an owner ID",
        )
    })?;
    let name = fields.next().ok_or_else(|| {
        parse_error(
            line_number,
            Some(event.event_number),
            record,
            "A record requires an attribute name",
        )
    })?;
    let value = fields.next().unwrap_or("");
    let owner_id = parse_i32(
        owner_text,
        line_number,
        Some(event.event_number),
        record,
        "attribute owner ID",
    )?;
    event.attributes.push(HepMcAttribute {
        owner_id,
        name: name.to_owned(),
        value: value.to_owned(),
        source_line: line_number,
    });

    if owner_id != 0 {
        return Ok(());
    }
    match name {
        "GenPdfInfo" => {
            event.pdf_info = Some(parse_pdf_info(
                line_number,
                event.event_number,
                record,
                value,
            )?)
        }
        "event_scale" => {
            event.event_scale = Some(parse_f64(
                value,
                line_number,
                Some(event.event_number),
                record,
                "event scale",
            )?)
        }
        "alphaQCD" => {
            event.alpha_qcd = Some(parse_f64(
                value,
                line_number,
                Some(event.event_number),
                record,
                "alphaQCD",
            )?)
        }
        "alphaQED" => {
            event.alpha_qed = Some(parse_f64(
                value,
                line_number,
                Some(event.event_number),
                record,
                "alphaQED",
            )?)
        }
        "signal_process_id" => {
            event.signal_process_id = Some(parse_i32(
                value,
                line_number,
                Some(event.event_number),
                record,
                "signal process ID",
            )?)
        }
        _ => {}
    }
    Ok(())
}

fn parse_pdf_info(
    line_number: usize,
    event_number: i64,
    record: &str,
    value: &str,
) -> Result<HepMcPdfInfo, HepMcError> {
    let fields: Vec<&str> = value.split_whitespace().collect();
    if fields.len() < 9 {
        return Err(parse_error(
            line_number,
            Some(event_number),
            record,
            "GenPdfInfo requires the nine HepMC3 3.3.0 fields",
        ));
    }
    Ok(HepMcPdfInfo {
        incoming_parton_id_1: parse_i32(
            fields[0],
            line_number,
            Some(event_number),
            record,
            "incoming parton ID 1",
        )?,
        incoming_parton_id_2: parse_i32(
            fields[1],
            line_number,
            Some(event_number),
            record,
            "incoming parton ID 2",
        )?,
        x1: parse_f64(fields[2], line_number, Some(event_number), record, "x1")?,
        x2: parse_f64(fields[3], line_number, Some(event_number), record, "x2")?,
        scale: parse_f64(
            fields[4],
            line_number,
            Some(event_number),
            record,
            "PDF scale",
        )?,
        xf1: parse_f64(fields[5], line_number, Some(event_number), record, "xf1")?,
        xf2: parse_f64(fields[6], line_number, Some(event_number), record, "xf2")?,
        pdf_id_1: parse_i32(
            fields[7],
            line_number,
            Some(event_number),
            record,
            "PDF ID 1",
        )?,
        pdf_id_2: parse_i32(
            fields[8],
            line_number,
            Some(event_number),
            record,
            "PDF ID 2",
        )?,
        additional_fields: fields[9..]
            .iter()
            .map(|field| (*field).to_owned())
            .collect(),
    })
}

fn parse_particle(
    line_number: usize,
    event_number: i64,
    record: &str,
) -> Result<HepMcParticle, HepMcError> {
    let fields: Vec<&str> = record.split_whitespace().collect();
    if fields.len() < 10 {
        return Err(parse_error(
            line_number,
            Some(event_number),
            record,
            "P record requires id, parent object, PDG ID, four-momentum, mass, and status",
        ));
    }
    Ok(HepMcParticle {
        id: parse_i32(
            fields[1],
            line_number,
            Some(event_number),
            record,
            "particle ID",
        )?,
        production_reference: parse_i32(
            fields[2],
            line_number,
            Some(event_number),
            record,
            "production reference",
        )?,
        production_vertex_id: None,
        pdg_id: parse_i32(fields[3], line_number, Some(event_number), record, "PDG ID")?,
        px: parse_f64(fields[4], line_number, Some(event_number), record, "px")?,
        py: parse_f64(fields[5], line_number, Some(event_number), record, "py")?,
        pz: parse_f64(fields[6], line_number, Some(event_number), record, "pz")?,
        energy: parse_f64(fields[7], line_number, Some(event_number), record, "energy")?,
        generated_mass: parse_f64(
            fields[8],
            line_number,
            Some(event_number),
            record,
            "generated mass",
        )?,
        status: parse_i32(fields[9], line_number, Some(event_number), record, "status")?,
        end_vertex_id: None,
        parent_particle_ids: Vec::new(),
        child_particle_ids: Vec::new(),
        additional_fields: fields[10..]
            .iter()
            .map(|field| (*field).to_owned())
            .collect(),
        source_line: line_number,
    })
}

fn parse_vertex(
    line_number: usize,
    event_number: i64,
    record: &str,
) -> Result<HepMcVertex, HepMcError> {
    let fields: Vec<&str> = record.split_whitespace().collect();
    if fields.len() < 4 {
        return Err(parse_error(
            line_number,
            Some(event_number),
            record,
            "V record requires id, status, and incoming-particle list",
        ));
    }
    let id = parse_i32(
        fields[1],
        line_number,
        Some(event_number),
        record,
        "vertex ID",
    )?;
    if id >= 0 {
        return Err(parse_error(
            line_number,
            Some(event_number),
            record,
            "serialized vertex ID must be negative",
        ));
    }
    let status = parse_i32(
        fields[2],
        line_number,
        Some(event_number),
        record,
        "vertex status",
    )?;
    let close_index = fields
        .iter()
        .position(|field| field.ends_with(']'))
        .ok_or_else(|| {
            parse_error(
                line_number,
                Some(event_number),
                record,
                "unterminated incoming-particle list",
            )
        })?;
    if !fields[3].starts_with('[') {
        return Err(parse_error(
            line_number,
            Some(event_number),
            record,
            "vertex incoming-particle list must start with '['",
        ));
    }
    let list = fields[3..=close_index].join(" ");
    let list = list.trim_start_matches('[').trim_end_matches(']');
    let mut incoming_particle_ids = Vec::new();
    if !list.trim().is_empty() {
        for field in list.split(',') {
            incoming_particle_ids.push(parse_i32(
                field.trim(),
                line_number,
                Some(event_number),
                record,
                "incoming particle ID",
            )?);
        }
    }
    let position = parse_optional_position(
        &fields[close_index + 1..],
        line_number,
        Some(event_number),
        record,
    )?;
    Ok(HepMcVertex {
        id,
        status,
        position,
        incoming_particle_ids,
        outgoing_particle_ids: Vec::new(),
        implicit: false,
        source_line: Some(line_number),
    })
}

fn parse_optional_position(
    fields: &[&str],
    line_number: usize,
    event_number: Option<i64>,
    record: &str,
) -> Result<Option<[f64; 4]>, HepMcError> {
    if fields.is_empty() {
        return Ok(None);
    }
    if fields.len() != 5 || fields[0] != "@" {
        return Err(parse_error(
            line_number,
            event_number,
            record,
            "position must use '@ x y z t'",
        ));
    }
    Ok(Some([
        parse_f64(fields[1], line_number, event_number, record, "position x")?,
        parse_f64(fields[2], line_number, event_number, record, "position y")?,
        parse_f64(fields[3], line_number, event_number, record, "position z")?,
        parse_f64(fields[4], line_number, event_number, record, "position t")?,
    ]))
}

fn finalize_event(event: &mut HepMcEvent) -> Result<(), HepMcError> {
    if event.particles.len() != event.declared_particle_count {
        return Err(event_error(
            event,
            format!(
                "declared {} particles but parsed {}",
                event.declared_particle_count,
                event.particles.len()
            ),
        ));
    }
    let mut particle_indices = HashMap::new();
    for (index, particle) in event.particles.iter().enumerate() {
        if particle.id <= 0 || particle_indices.insert(particle.id, index).is_some() {
            return Err(event_error(
                event,
                format!("particle ID {} is non-positive or duplicated", particle.id),
            ));
        }
    }

    let mut explicit = BTreeMap::new();
    let parsed_vertices = std::mem::take(&mut event.vertices);
    for vertex in parsed_vertices {
        let id = vertex.id;
        if explicit.insert(id, vertex).is_some() {
            return Err(event_error(event, format!("duplicate vertex ID {id}")));
        }
    }
    if explicit.len() > event.declared_vertex_count {
        return Err(event_error(
            event,
            "more explicit vertices than the declared vertex count".to_owned(),
        ));
    }

    let mut implicit_mothers = Vec::new();
    let mut seen_mothers = HashSet::new();
    for particle in &event.particles {
        if particle.production_reference > 0 && seen_mothers.insert(particle.production_reference) {
            implicit_mothers.push(particle.production_reference);
        }
        if particle.production_reference > 0
            && !particle_indices.contains_key(&particle.production_reference)
        {
            return Err(event_error(
                event,
                format!(
                    "particle {} refers to missing parent particle {}",
                    particle.id, particle.production_reference
                ),
            ));
        }
        if particle.production_reference < 0
            && !explicit.contains_key(&particle.production_reference)
        {
            return Err(event_error(
                event,
                format!(
                    "particle {} refers to missing explicit vertex {}",
                    particle.id, particle.production_reference
                ),
            ));
        }
    }

    let available_ids: Vec<i32> = (1..=event.declared_vertex_count)
        .map(|offset| -(offset as i32))
        .filter(|id| !explicit.contains_key(id))
        .collect();
    if available_ids.len() != implicit_mothers.len() {
        return Err(event_error(
            event,
            format!(
                "declared {} vertices imply {} implicit vertices, but {} parent-particle references were found",
                event.declared_vertex_count,
                available_ids.len(),
                implicit_mothers.len()
            ),
        ));
    }

    let mut mother_to_vertex = HashMap::new();
    for (id, mother) in available_ids.iter().zip(implicit_mothers.iter()) {
        mother_to_vertex.insert(*mother, *id);
        explicit.insert(
            *id,
            HepMcVertex {
                id: *id,
                status: 0,
                position: None,
                incoming_particle_ids: vec![*mother],
                outgoing_particle_ids: Vec::new(),
                implicit: true,
                source_line: None,
            },
        );
    }

    for particle in &mut event.particles {
        particle.production_vertex_id = match particle.production_reference {
            0 => None,
            reference if reference < 0 => Some(reference),
            reference => mother_to_vertex.get(&reference).copied(),
        };
        if let Some(vertex_id) = particle.production_vertex_id {
            let Some(vertex) = explicit.get_mut(&vertex_id) else {
                return Err(HepMcError::Parse {
                    line_number: particle.source_line,
                    event_number: Some(event.event_number),
                    record: format!("P {}", particle.id),
                    message: format!("missing reconstructed production vertex {vertex_id}"),
                });
            };
            vertex.outgoing_particle_ids.push(particle.id);
        }
    }

    for vertex in explicit.values() {
        for incoming in &vertex.incoming_particle_ids {
            if !particle_indices.contains_key(incoming) {
                return Err(event_error(
                    event,
                    format!(
                        "vertex {} refers to missing incoming particle {incoming}",
                        vertex.id
                    ),
                ));
            }
        }
    }

    for vertex in explicit.values() {
        let incoming = vertex.incoming_particle_ids.clone();
        let outgoing = vertex.outgoing_particle_ids.clone();
        for incoming_id in &incoming {
            let particle = &mut event.particles[particle_indices[incoming_id]];
            if particle.end_vertex_id.replace(vertex.id).is_some() {
                return Err(event_error(
                    event,
                    format!("particle {incoming_id} ends at more than one vertex"),
                ));
            }
            extend_unique(&mut particle.child_particle_ids, &outgoing);
        }
        for outgoing_id in &outgoing {
            let particle = &mut event.particles[particle_indices[outgoing_id]];
            extend_unique(&mut particle.parent_particle_ids, &incoming);
        }
    }

    event.vertices = explicit.into_values().collect();
    Ok(())
}

fn extend_unique(target: &mut Vec<i32>, values: &[i32]) {
    for value in values {
        if !target.contains(value) {
            target.push(*value);
        }
    }
}

fn event_error(event: &HepMcEvent, message: String) -> HepMcError {
    HepMcError::Parse {
        line_number: event.source_end_line,
        event_number: Some(event.event_number),
        record: "event graph".to_owned(),
        message,
    }
}

fn parse_error(
    line_number: usize,
    event_number: Option<i64>,
    record: &str,
    message: impl Into<String>,
) -> HepMcError {
    HepMcError::Parse {
        line_number,
        event_number,
        record: record.to_owned(),
        message: message.into(),
    }
}

fn parse_i32(
    value: &str,
    line_number: usize,
    event_number: Option<i64>,
    record: &str,
    field: &str,
) -> Result<i32, HepMcError> {
    value.parse().map_err(|_| {
        parse_error(
            line_number,
            event_number,
            record,
            format!("invalid {field}: '{value}'"),
        )
    })
}

fn parse_i64(
    value: &str,
    line_number: usize,
    event_number: Option<i64>,
    record: &str,
    field: &str,
) -> Result<i64, HepMcError> {
    value.parse().map_err(|_| {
        parse_error(
            line_number,
            event_number,
            record,
            format!("invalid {field}: '{value}'"),
        )
    })
}

fn parse_usize(
    value: &str,
    line_number: usize,
    event_number: Option<i64>,
    record: &str,
    field: &str,
) -> Result<usize, HepMcError> {
    value.parse().map_err(|_| {
        parse_error(
            line_number,
            event_number,
            record,
            format!("invalid {field}: '{value}'"),
        )
    })
}

fn parse_f64(
    value: &str,
    line_number: usize,
    event_number: Option<i64>,
    record: &str,
    field: &str,
) -> Result<f64, HepMcError> {
    value.parse().map_err(|_| {
        parse_error(
            line_number,
            event_number,
            record,
            format!("invalid {field}: '{value}'"),
        )
    })
}

fn read_json(path: &Path) -> Result<Value, HepMcError> {
    let file = File::open(path).map_err(|source| HepMcError::Io {
        path: Some(path.to_path_buf()),
        line_number: 0,
        event_number: None,
        source,
    })?;
    serde_json::from_reader(BufReader::new(file)).map_err(|error| HepMcError::Provenance {
        path: path.to_path_buf(),
        message: error.to_string(),
    })
}

fn nested_f64(value: Option<&Value>, key: &str) -> Option<f64> {
    value
        .and_then(|value| value.get(key))
        .and_then(Value::as_f64)
}

fn value_f64(value: &Value, key: &str) -> Option<f64> {
    value.get(key).and_then(Value::as_f64)
}

fn value_i64(value: &Value, key: &str) -> Option<i64> {
    value.get(key).and_then(Value::as_i64)
}

fn value_u64(value: &Value, key: &str) -> Option<u64> {
    value.get(key).and_then(Value::as_u64)
}

fn value_i32(value: &Value, key: &str) -> Option<i32> {
    value_i64(value, key).and_then(|value| i32::try_from(value).ok())
}

fn value_bool(value: &Value, key: &str) -> Option<bool> {
    value.get(key).and_then(Value::as_bool)
}

fn value_string(value: &Value, key: &str) -> Option<String> {
    value.get(key).and_then(Value::as_str).map(str::to_owned)
}
