use std::time::Duration;

use parton_sbi::physics::{
    derive_prototype_decision, prototype_anchors, CandidateEvidence, CandidateStatus,
    DeterministicTransportGrid, DirectApfelEvaluator, HardProcessQueryEnvelope, MeasurementStatus,
    PrototypeDecision, PrototypeStudyContract, StudyBudget, ThresholdSide, TransportQuery,
    CUSTOM_INTERPOLATOR_PROTOTYPE_VERSION, D2_AUTHORIZED, DIRECT_APFEL_PROTOTYPE_VERSION,
    MAX_STUDY_BYTES,
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
    assert!(evaluator.evaluator_policy_identity().starts_with("sha256:"));
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
    const { assert!(!D2_AUTHORIZED) };
    assert!(!contract.d2_authorized);
}

#[test]
fn selection_requires_every_predeclared_gate() {
    let evidence = CandidateEvidence {
        accuracy: MeasurementStatus::Passed,
        identity: MeasurementStatus::Passed,
        reload: MeasurementStatus::Passed,
        threshold: MeasurementStatus::Passed,
        support: MeasurementStatus::Passed,
        deterministic_repeat: MeasurementStatus::Passed,
        scalar_throughput: MeasurementStatus::Passed,
        thread_safety: MeasurementStatus::Passed,
        process_isolation: MeasurementStatus::Passed,
    };
    assert_eq!(evidence.status(), CandidateStatus::Pass);
    assert_eq!(
        derive_prototype_decision(CandidateStatus::Pass, CandidateStatus::Fail, true),
        PrototypeDecision::DirectApfelSelected
    );
    assert_eq!(
        derive_prototype_decision(CandidateStatus::Pass, CandidateStatus::Fail, false),
        PrototypeDecision::Inconclusive
    );
}
