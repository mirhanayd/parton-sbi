use std::time::Duration;

use parton_sbi::physics::{
    prototype_anchors, DeterministicTransportGrid, DirectApfelEvaluator, HardProcessQueryEnvelope,
    PrototypeDecision, PrototypeSelectionEvidence, PrototypeStudyContract, StudyBudget,
    ThresholdSide, TransportQuery, CUSTOM_INTERPOLATOR_PROTOTYPE_VERSION, D2_AUTHORIZED,
    DIRECT_APFEL_PROTOTYPE_VERSION, MAX_STUDY_BYTES,
};

fn grid() -> DeterministicTransportGrid {
    let xs = vec![0.01, 0.1, 1.0];
    let qs = vec![1.0, 2.0, 4.0];
    let flavors = vec![21];
    let values = qs
        .iter()
        .flat_map(|q| xs.iter().map(move |x| x * q))
        .collect();
    DeterministicTransportGrid::new(xs, qs, vec![2.0], flavors, values).unwrap()
}

#[test]
fn explicit_versions_and_identity_separation() {
    let transport = grid();
    assert_eq!(transport.version, CUSTOM_INTERPOLATOR_PROTOTYPE_VERSION);
    assert_ne!(transport.version, DIRECT_APFEL_PROTOTYPE_VERSION);
    assert_eq!(transport.identity, grid().identity);
}

#[test]
fn strict_support_knot_reproduction_and_repeatability() {
    let transport = grid();
    let query = TransportQuery {
        flavor: 21,
        x: 0.1,
        q_gev: 2.0,
    };
    let first = transport.evaluate(query).unwrap();
    assert_eq!(first, transport.evaluate(query).unwrap());
    assert_eq!(first.xf, 0.2);
    assert!(transport
        .evaluate(TransportQuery { x: 1.0e-4, ..query })
        .is_err());
}

#[test]
fn threshold_behavior_is_one_sided() {
    let transport = grid();
    let query = |q_gev| TransportQuery {
        flavor: 21,
        x: 0.1,
        q_gev,
    };
    assert_eq!(
        transport.evaluate(query(1.999)).unwrap().threshold_side,
        ThresholdSide::BelowCharm
    );
    assert_eq!(
        transport.evaluate(query(2.0)).unwrap().threshold_side,
        ThresholdSide::AtCharm
    );
    assert_eq!(
        transport.evaluate(query(2.001)).unwrap().threshold_side,
        ThresholdSide::BetweenCharmAndBottom
    );
}

#[test]
fn direct_context_initializes_without_evolution() {
    let evaluator = DirectApfelEvaluator::initialize().unwrap();
    assert!(evaluator.identity().starts_with("sha256:"));
    assert_eq!(evaluator.config().apfelxx_version, "4.8.0");
}

#[test]
fn query_envelope_is_synthetic_and_reports_unresolved_consumers() {
    let envelope = HardProcessQueryEnvelope::hera_dis();
    let queries = envelope.synthetic_queries();
    assert!(queries
        .iter()
        .all(|(x, q)| envelope.contains_hard_query(*x, *q)));
    assert!(envelope
        .unresolved_consumers()
        .contains(&"beam_remnants".to_owned()));
}

#[test]
fn fixed_caps_anchors_and_d2_gate_are_immutable() {
    let contract = PrototypeStudyContract::fixed().unwrap();
    assert_eq!(prototype_anchors().unwrap().len(), 3);
    assert_eq!(contract.maximum_runtime_seconds, 30 * 60);
    assert_eq!(contract.maximum_generated_bytes, 2 * 1024 * 1024 * 1024);
    assert!(StudyBudget::enforce_observed(Duration::ZERO, MAX_STUDY_BYTES).is_ok());
    assert!(StudyBudget::enforce_observed(Duration::ZERO, MAX_STUDY_BYTES + 1).is_err());
    assert!(!D2_AUTHORIZED);
    assert!(!contract.d2_authorized);
}

#[test]
fn selection_requires_every_predeclared_gate() {
    let evidence = PrototypeSelectionEvidence {
        direct_accuracy_pass: true,
        custom_accuracy_pass: false,
        deterministic_identity_pass: true,
        strict_support_pass: true,
        threshold_behavior_pass: true,
        thread_safety_pass: true,
        process_isolation_pass: true,
        cache_reload_pass: true,
        all_consumer_envelope_complete: true,
        direct_calls_per_second: 10_000.0,
        custom_calls_per_second: 0.0,
    };
    assert_eq!(evidence.decision(), PrototypeDecision::DirectApfelSelected);
    let unresolved = PrototypeSelectionEvidence {
        all_consumer_envelope_complete: false,
        ..evidence
    };
    assert_eq!(unresolved.decision(), PrototypeDecision::Inconclusive);
}
