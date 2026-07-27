use parton_sbi::physics::{HepMcError, HepMcReader, HepMcRunProvenance};
use std::fs;
use std::io::{BufReader, Cursor};
use std::path::{Path, PathBuf};

const FIXTURE: &str = "tests/fixtures/hepmc3_real_minimal.hepmc3";
const SMOKE_FILE_ENV: &str = "PARTONSBI_HEPMC3_SMOKE_FILE";

fn approx_eq(actual: f64, expected: f64, tolerance: f64) {
    assert!(
        (actual - expected).abs() <= tolerance,
        "expected {expected:.16e}, got {actual:.16e}"
    );
}

fn first_fixture_event() -> parton_sbi::physics::HepMcEvent {
    let mut reader = HepMcReader::open(FIXTURE).expect("fixture should open");
    reader
        .next_event()
        .expect("fixture should parse")
        .expect("fixture should contain an event")
}

#[test]
fn real_particle_layout_is_not_shifted() {
    let event = first_fixture_event();
    let beam_electron = event.particle(1).expect("particle 1");

    assert_eq!(beam_electron.id, 1);
    assert_eq!(beam_electron.production_reference, 0);
    assert_eq!(beam_electron.pdg_id, 11);
    assert_eq!(beam_electron.status, 4);
    approx_eq(beam_electron.px, -7.105_427_357_601_002e-15, 1e-27);
    approx_eq(beam_electron.py, 5.329_070_518_200_751e-15, 1e-27);
    approx_eq(beam_electron.pz, 27.499_880_389_437_01, 1e-12);
    approx_eq(beam_electron.energy, 27.499_880_394_184_686, 1e-12);
    approx_eq(beam_electron.generated_mass, 0.000_511, 1e-15);

    let child = event.particle(2).expect("particle 2");
    assert_eq!(child.production_reference, 1);
    assert_eq!(child.production_vertex_id, Some(-1));
    assert_eq!(child.pdg_id, 11);
    assert_eq!(child.status, 41);
}

#[test]
fn real_event_preserves_weights_pdf_info_scale_and_attributes() {
    let event = first_fixture_event();
    assert_eq!(event.weights, vec![1.0]);
    approx_eq(
        event.event_scale.expect("event scale"),
        1.971_497_557_943_24,
        1e-14,
    );
    approx_eq(
        event.alpha_qcd.expect("alphaQCD"),
        0.342_520_213_327_221,
        1e-15,
    );
    approx_eq(
        event.alpha_qed.expect("alphaQED"),
        0.007_496_313_602_774_57,
        1e-17,
    );
    assert_eq!(event.signal_process_id, Some(211));

    let pdf = event.pdf_info.expect("GenPdfInfo");
    assert_eq!(pdf.incoming_parton_id_1, 11);
    assert_eq!(pdf.incoming_parton_id_2, 2);
    approx_eq(pdf.x1, 0.951_993_596, 1e-12);
    approx_eq(pdf.x2, 0.336_657_043, 1e-12);
    approx_eq(pdf.scale, 1.971_497_56, 1e-10);
    approx_eq(pdf.xf1, 0.628_836_956, 1e-12);
    approx_eq(pdf.xf2, 0.561_987_674, 1e-12);
    assert_eq!((pdf.pdf_id_1, pdf.pdf_id_2), (0, 0));
    assert!(pdf.additional_fields.is_empty());
    assert!(event
        .attributes
        .iter()
        .any(|attribute| attribute.name == "GenCrossSection"));
    assert!(event
        .attributes
        .iter()
        .any(|attribute| attribute.owner_id == 4 && attribute.name == "flow1"));
}

#[test]
fn real_event_reconstructs_explicit_and_implicit_connectivity() {
    let event = first_fixture_event();
    assert_eq!(event.vertices.len(), 13);

    let hard_vertex = event
        .vertices
        .iter()
        .find(|vertex| vertex.id == -6)
        .expect("explicit hard vertex");
    assert!(!hard_vertex.implicit);
    assert_eq!(hard_vertex.incoming_particle_ids, vec![6, 10]);
    assert_eq!(hard_vertex.outgoing_particle_ids, vec![11, 12]);
    assert_eq!(event.particle(6).unwrap().end_vertex_id, Some(-6));
    assert_eq!(event.particle(11).unwrap().parent_particle_ids, vec![6, 10]);

    let first_implicit = event
        .vertices
        .iter()
        .find(|vertex| vertex.id == -1)
        .expect("implicit beam vertex");
    assert!(first_implicit.implicit);
    assert_eq!(first_implicit.incoming_particle_ids, vec![1]);
    assert_eq!(first_implicit.outgoing_particle_ids, vec![2]);
    assert_eq!(event.particle(1).unwrap().child_particle_ids, vec![2]);
}

#[test]
fn beam_scattered_electron_and_final_state_selection_use_typed_fields() {
    let event = first_fixture_event();
    let beams: Vec<_> = event
        .beam_particles()
        .map(|particle| particle.pdg_id)
        .collect();
    assert_eq!(beams, vec![11, 2212]);

    let scattered = event.scattered_electron().expect("scattered electron");
    assert_eq!(scattered.id, 19);
    assert_eq!(scattered.pdg_id, 11);
    assert_eq!(scattered.status, 1);

    let final_ids: Vec<_> = event
        .final_state_particles()
        .map(|particle| particle.id)
        .collect();
    assert_eq!(final_ids, vec![13, 17, 18, 19]);
}

#[test]
fn iterator_streams_multiple_real_events() {
    let reader = HepMcReader::open(FIXTURE).expect("fixture should open");
    let numbers: Vec<_> = reader
        .map(|event| event.expect("event should parse").event_number)
        .collect();
    assert_eq!(numbers, vec![225, 2743]);
}

#[test]
fn streaming_parser_accepts_configured_smoke_file() {
    let path = std::env::var(SMOKE_FILE_ENV).unwrap_or_else(|_| FIXTURE.to_string());
    let reader = HepMcReader::open(&path).expect("HepMC3 input should open");
    let mut event_count = 0;
    for event in reader {
        event.expect("HepMC3 event should parse");
        event_count += 1;
    }
    assert!(event_count > 0, "HepMC3 input should contain an event");
}

#[test]
fn all_event_weights_are_preserved() {
    let input = b"HepMC::Version 3.03.00\nE 7 1 2\nU GEV MM\nW 1.0 -0.5 2.25\nP 1 0 11 0 0 10 10 0 4\nP 2 1 11 1 0 9 9.1 0 1\nHepMC::Asciiv3-END_EVENT_LISTING\n";
    let mut reader = HepMcReader::new(BufReader::new(Cursor::new(input)));
    let event = reader.next_event().unwrap().unwrap();
    assert_eq!(event.weights, vec![1.0, -0.5, 2.25]);
}

#[test]
fn missing_optional_attributes_are_explicitly_absent() {
    let input = b"E 8 1 2\nU GEV MM\nP 1 0 11 0 0 10 10 0 4\nP 2 1 11 1 0 9 9.1 0 1\n";
    let mut reader = HepMcReader::new(BufReader::new(Cursor::new(input)));
    let event = reader.next_event().unwrap().unwrap();
    assert!(event.weights.is_empty());
    assert!(event.pdf_info.is_none());
    assert!(event.event_scale.is_none());
    assert!(event.alpha_qcd.is_none());
    assert!(event.alpha_qed.is_none());
    assert!(event.signal_process_id.is_none());
}

#[test]
fn malformed_particle_record_is_an_error_with_line_and_event_context() {
    let input = b"E 91 0 1\nU GEV MM\nP 1 0 11 0 0\n";
    let mut reader = HepMcReader::new(BufReader::new(Cursor::new(input)));
    let error = reader.next_event().expect_err("malformed P must fail");
    match error {
        HepMcError::Parse {
            line_number,
            event_number,
            message,
            ..
        } => {
            assert_eq!(line_number, 3);
            assert_eq!(event_number, Some(91));
            assert!(message.contains("P record requires"));
        }
        other => panic!("expected parse error, got {other}"),
    }
}

#[test]
fn run_provenance_loads_config_and_metadata_without_fabricating_missing_fields() {
    let unique = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let run_dir = std::env::temp_dir().join(format!("parton_sbi_hepmc_fixture_{unique}"));
    fs::create_dir_all(&run_dir).unwrap();
    copy_fixture(
        "tests/fixtures/hepmc3_real_minimal_config.json",
        &run_dir.join("config.json"),
    );
    copy_fixture(
        "tests/fixtures/hepmc3_real_minimal_metadata.json",
        &run_dir.join("metadata.json"),
    );

    let mut provenance = HepMcRunProvenance::load(&run_dir).expect("provenance should load");
    assert_eq!(provenance.pdf_set.as_deref(), Some("CT18NLO"));
    assert_eq!(provenance.pdf_member, Some(0));
    assert_eq!(provenance.generator_seed, Some(204_505_473));
    assert_eq!(provenance.configured_seed, None);
    assert_eq!(provenance.process.as_deref(), Some("neutral_current_dis"));
    assert_eq!(provenance.electron_energy_gev, Some(27.5));
    assert_eq!(provenance.proton_energy_gev, Some(920.0));
    assert_eq!(provenance.parton_shower, Some(true));
    assert_eq!(provenance.hadronization, Some(true));
    assert_eq!(provenance.cuts.q2_min_gev2, Some(3.5));
    assert_eq!(provenance.pythia_version.as_deref(), Some("8.312"));
    assert_eq!(provenance.generator_version.as_deref(), Some("8.312"));
    assert_eq!(provenance.hepmc_version.as_deref(), Some("3.03.00"));
    assert_eq!(provenance.lhapdf_version.as_deref(), Some("6.5.6"));
    assert_eq!(provenance.apfelxx_version, None);
    assert_eq!(provenance.git_dirty, None);
    assert_eq!(provenance.beam_particle_id_1, None);
    assert_eq!(provenance.beam_particle_id_2, None);

    provenance.enrich_beam_ids_from_event(&first_fixture_event());
    assert_eq!(provenance.beam_particle_id_1, Some(11));
    assert_eq!(provenance.beam_particle_id_2, Some(2212));

    let _ = fs::remove_dir_all(run_dir);
}

fn copy_fixture(source: impl AsRef<Path>, destination: &PathBuf) {
    fs::copy(source, destination).expect("fixture copy should succeed");
}
