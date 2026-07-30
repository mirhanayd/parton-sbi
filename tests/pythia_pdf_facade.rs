use parton_sbi::physics::{
    audit_installed_pythia_signed_boundary, require_signed_facade_compatibility,
    BoundedPythiaQueryProvenance, PdfTheta, PersistentApfelContext, PersistentApfelQuery,
    PythiaConsumerClassification, PythiaExecutionPhase, PythiaFacadeMethod, PythiaPdfFacadeError,
    PythiaPdfQueryRecord, PythiaQueryReason, PythiaQueryStatus, D1C_B_ATTEMPTED_EVENTS,
    D1C_B_D2_AUTHORIZED, D1C_B_PYTHIA_INITIALIZED, D1C_B_PYTHIA_NEXT_EXECUTED, D1C_B_SAVED_EVENTS,
    D1C_B_SUCCESSFUL_EVENTS, PYTHIA_PDF_METHOD_MATRIX,
};

#[test]
fn accepted_negative_apfel_probe_blocks_pythia_facade_selection() {
    let context = PersistentApfelContext::initialize(PdfTheta::new(0.0, 0.0).unwrap()).unwrap();
    let accepted = context
        .evaluate_scalar(PersistentApfelQuery {
            flavor: 21,
            x: 0.999,
            q_gev: context.support().q_minimum_gev,
        })
        .unwrap();
    assert!(accepted.xf < 0.0);

    let audit = audit_installed_pythia_signed_boundary().unwrap();
    assert!(audit.demonstrates_clipping());
    assert_eq!(audit.raw_inclusive.to_bits(), (-1.0_f64).to_bits());
    assert_eq!(audit.base_inclusive.to_bits(), 0.0_f64.to_bits());
    assert!(matches!(
        require_signed_facade_compatibility(),
        Err(PythiaPdfFacadeError::SignedBoundaryIncompatible(_))
    ));
}

#[test]
fn installed_method_matrix_exposes_the_nonvirtual_blocker() {
    let blockers = PYTHIA_PDF_METHOD_MATRIX
        .iter()
        .filter(|entry| entry.signed_value_behavior.contains("clip"))
        .map(|entry| entry.method)
        .collect::<Vec<_>>();
    assert!(blockers.contains(&"xf"));
    assert!(blockers.contains(&"xfVal"));
    assert!(blockers.contains(&"xfSea"));
}

#[test]
fn provenance_is_diagnostic_bounded_and_unknown_runtime_fails_closed() {
    let mut provenance = BoundedPythiaQueryProvenance::with_capacity(1);
    let error = provenance
        .record(PythiaPdfQueryRecord {
            sequence: u64::MAX,
            execution_phase: PythiaExecutionPhase::EventRuntimeReserved,
            consumer: PythiaConsumerClassification::UnclassifiedEventRuntime,
            method: PythiaFacadeMethod::Xf,
            flavor: 21,
            x_bits: 0.999_f64.to_bits(),
            input_scale_bits: (1.295_f64 * 1.295).to_bits(),
            derived_q_bits: Some(1.295_f64.to_bits()),
            raw_apfel_output_bits: Some((-1.0_f64).to_bits()),
            facade_output_bits: None,
            status: PythiaQueryStatus::Accepted,
            reason: PythiaQueryReason::Accepted,
            threshold_side: Some("BELOW_CHARM".into()),
            evaluator_policy_identity: "sha256:evaluator".into(),
            facade_policy_identity: "sha256:blocked".into(),
        })
        .unwrap_err();
    assert!(matches!(
        error,
        PythiaPdfFacadeError::UnclassifiedEventRuntime
    ));
    assert_eq!(provenance.records()[0].sequence, 0);
    assert_eq!(
        provenance.records()[0].reason,
        PythiaQueryReason::UnknownConsumer
    );
}

#[test]
fn incompatibility_stops_before_init_next_or_events() {
    const {
        assert!(!D1C_B_PYTHIA_INITIALIZED);
        assert!(!D1C_B_PYTHIA_NEXT_EXECUTED);
        assert!(D1C_B_ATTEMPTED_EVENTS == 0);
        assert!(D1C_B_SUCCESSFUL_EVENTS == 0);
        assert!(D1C_B_SAVED_EVENTS == 0);
        assert!(!D1C_B_D2_AUTHORIZED);
    }
}
