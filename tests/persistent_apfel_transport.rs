use std::process::Command;
use std::sync::Arc;

use parton_sbi::physics::{
    DirectApfelEvaluator, PdfTheta, PersistentApfelContext, PersistentApfelError,
    PersistentApfelQuery, PersistentThresholdSide, TransportQuery,
};

const RELATIVE_TOLERANCE: f64 = 1.0e-5;
const ABSOLUTE_TOLERANCE: f64 = 1.0e-9;

fn theta(delta_v: f64, lambda_sea: f64) -> PdfTheta {
    PdfTheta::new(delta_v, lambda_sea).unwrap()
}

fn agrees(candidate: f64, reference: f64) -> bool {
    let absolute = (candidate - reference).abs();
    let relative = absolute / reference.abs();
    absolute <= ABSOLUTE_TOLERANCE || relative <= RELATIVE_TOLERANCE
}

#[test]
fn persistent_apfel_matches_fresh_reference_for_fixed_anchors() {
    let fresh = DirectApfelEvaluator::initialize().unwrap();
    for point in [theta(0.0, 0.0), theta(-0.2, 0.0), theta(-0.2, 0.25)] {
        let persistent = PersistentApfelContext::initialize(point).unwrap();
        let support = persistent.support();
        let probes = [
            PersistentApfelQuery {
                flavor: 21,
                x: 1.0e-4,
                q_gev: support.q_minimum_gev,
            },
            PersistentApfelQuery {
                flavor: 2,
                x: 0.01,
                q_gev: 10.0,
            },
            PersistentApfelQuery {
                flavor: -1,
                x: 0.3,
                q_gev: support.bottom_threshold_gev,
            },
            PersistentApfelQuery {
                flavor: 21,
                x: 0.999,
                q_gev: support.q_minimum_gev,
            },
        ];
        let reference_queries = probes
            .iter()
            .map(|query| TransportQuery {
                flavor: query.flavor,
                x: query.x,
                q_gev: query.q_gev,
            })
            .collect::<Vec<_>>();
        let reference = fresh.evaluate_batch(point, &reference_queries).unwrap();
        let batch = persistent.evaluate_batch(&probes).unwrap();
        assert_eq!(batch.len(), probes.len());
        for ((value, expected), query) in batch.iter().zip(&reference).zip(&probes) {
            assert_eq!(value.query, *query);
            assert!(agrees(value.xf, expected.xf), "{value:?} != {expected:?}");
            let scalar = persistent.evaluate_scalar(*query).unwrap();
            assert_eq!(scalar.xf.to_bits(), value.xf.to_bits());
            assert_eq!(scalar.threshold_side, value.threshold_side);
        }
        let repeated = persistent.evaluate_batch(&probes).unwrap();
        assert!(batch
            .iter()
            .zip(repeated)
            .all(|(left, right)| left.xf.to_bits() == right.xf.to_bits()));

        // The accepted D0R boundary has an inherited signed gluon excursion.
        // The core must return it unchanged rather than clipping it.
        assert!(batch[3].xf < 0.0);
    }
}

#[test]
fn persistent_apfel_concurrent_initialization_is_process_serialized() {
    let threads = [(0.0, 0.0), (-0.2, 0.0), (-0.2, 0.25)]
        .into_iter()
        .map(|(delta_v, lambda_sea)| {
            std::thread::spawn(move || {
                let context =
                    PersistentApfelContext::initialize(theta(delta_v, lambda_sea)).unwrap();
                (
                    context.identities().evaluator_policy_identity.clone(),
                    context.identities().theta_transport_identity.clone(),
                )
            })
        })
        .collect::<Vec<_>>();
    let identities = threads
        .into_iter()
        .map(|thread| thread.join().unwrap())
        .collect::<Vec<_>>();
    assert!(identities
        .windows(2)
        .all(|pair| pair[0].0 == pair[1].0 && pair[0].1 != pair[1].1));
}

#[test]
fn persistent_and_fresh_reference_calls_are_process_serialized() {
    let point = theta(0.0, 0.0);
    let persistent = Arc::new(PersistentApfelContext::initialize(point).unwrap());
    let fresh = Arc::new(DirectApfelEvaluator::initialize().unwrap());
    let persistent_query = PersistentApfelQuery {
        flavor: 21,
        x: 0.01,
        q_gev: 10.0,
    };
    let reference_query = TransportQuery {
        flavor: persistent_query.flavor,
        x: persistent_query.x,
        q_gev: persistent_query.q_gev,
    };
    let persistent_thread = {
        let persistent = Arc::clone(&persistent);
        std::thread::spawn(move || persistent.evaluate_scalar(persistent_query).unwrap().xf)
    };
    let fresh_thread = {
        let fresh = Arc::clone(&fresh);
        std::thread::spawn(move || fresh.evaluate_batch(point, &[reference_query]).unwrap()[0].xf)
    };
    assert!(agrees(
        persistent_thread.join().unwrap(),
        fresh_thread.join().unwrap()
    ));
}

#[test]
fn persistent_apfel_one_sided_thresholds_close_against_fresh_reference() {
    let fresh = DirectApfelEvaluator::initialize().unwrap();
    for point in [theta(0.0, 0.0), theta(-0.2, 0.0), theta(-0.2, 0.25)] {
        let persistent = PersistentApfelContext::initialize(point).unwrap();
        let support = persistent.support();
        let probes = [
            (4, support.charm_threshold_gev.next_down()),
            (4, support.charm_threshold_gev),
            (4, support.charm_threshold_gev.next_up()),
            (5, support.bottom_threshold_gev.next_down()),
            (5, support.bottom_threshold_gev),
            (5, support.bottom_threshold_gev.next_up()),
        ]
        .map(|(flavor, q_gev)| PersistentApfelQuery {
            flavor,
            x: 0.01,
            q_gev,
        });
        let reference_queries = probes
            .iter()
            .map(|query| TransportQuery {
                flavor: query.flavor,
                x: query.x,
                q_gev: query.q_gev,
            })
            .collect::<Vec<_>>();
        let expected = fresh.evaluate_batch(point, &reference_queries).unwrap();
        let actual = persistent.evaluate_batch(&probes).unwrap();
        for (actual, expected) in actual.iter().zip(expected) {
            assert!(
                agrees(actual.xf, expected.xf),
                "threshold closure failed for {point:?}: {actual:?} != {expected:?}"
            );
        }
        assert_eq!(
            actual[0].threshold_side,
            PersistentThresholdSide::BelowCharm
        );
        assert_eq!(actual[1].threshold_side, PersistentThresholdSide::AtCharm);
        assert_eq!(
            actual[2].threshold_side,
            PersistentThresholdSide::BetweenCharmAndBottom
        );
        assert_eq!(
            actual[3].threshold_side,
            PersistentThresholdSide::BetweenCharmAndBottom
        );
        assert_eq!(actual[4].threshold_side, PersistentThresholdSide::AtBottom);
        assert_eq!(
            actual[5].threshold_side,
            PersistentThresholdSide::AboveBottom
        );
    }
}

#[test]
fn persistent_apfel_enforces_support_flavors_thresholds_and_order() {
    let context = PersistentApfelContext::initialize(theta(0.0, 0.0)).unwrap();
    let support = context.support();
    let query = |flavor, x, q_gev| PersistentApfelQuery { flavor, x, q_gev };

    for rejected in [
        query(21, support.x_minimum / 2.0, 10.0),
        query(21, support.x_maximum.next_up(), 10.0),
        query(21, 0.1, support.q_minimum_gev.next_down()),
        query(21, 0.1, support.q_maximum_gev.next_up()),
    ] {
        assert!(matches!(
            context.evaluate_scalar(rejected),
            Err(PersistentApfelError::OutsideSupport { .. })
        ));
    }
    assert!(matches!(
        context.evaluate_scalar(query(6, 0.1, 10.0)),
        Err(PersistentApfelError::InactiveFlavor(6))
    ));
    assert!(matches!(
        context.evaluate_scalar(query(0, 0.1, 10.0)),
        Err(PersistentApfelError::UnsupportedFlavor(0))
    ));

    assert_eq!(
        context
            .evaluate_scalar(query(4, 0.1, support.charm_threshold_gev.next_down()))
            .unwrap()
            .threshold_side,
        PersistentThresholdSide::BelowCharm
    );
    assert_eq!(
        context
            .evaluate_scalar(query(4, 0.1, support.charm_threshold_gev))
            .unwrap()
            .threshold_side,
        PersistentThresholdSide::AtCharm
    );
    assert_eq!(
        context
            .evaluate_scalar(query(4, 0.1, support.charm_threshold_gev.next_up()))
            .unwrap()
            .threshold_side,
        PersistentThresholdSide::BetweenCharmAndBottom
    );
    assert_eq!(
        context
            .evaluate_scalar(query(5, 0.1, support.bottom_threshold_gev.next_down()))
            .unwrap()
            .threshold_side,
        PersistentThresholdSide::BetweenCharmAndBottom
    );
    assert_eq!(
        context
            .evaluate_scalar(query(5, 0.1, support.bottom_threshold_gev))
            .unwrap()
            .threshold_side,
        PersistentThresholdSide::AtBottom
    );
    assert_eq!(
        context
            .evaluate_scalar(query(5, 0.1, support.bottom_threshold_gev.next_up()))
            .unwrap()
            .threshold_side,
        PersistentThresholdSide::AboveBottom
    );

    let ordered = [
        query(2, 0.7, 100.0),
        query(21, 1.0e-3, 2.0),
        query(-3, 0.2, 20.0),
    ];
    let values = context.evaluate_batch(&ordered).unwrap();
    assert_eq!(
        values.iter().map(|value| value.query).collect::<Vec<_>>(),
        ordered
    );
}

#[test]
fn persistent_apfel_identities_cache_and_threads_are_deterministic() {
    let contexts = [
        PersistentApfelContext::initialize(theta(0.0, 0.0)).unwrap(),
        PersistentApfelContext::initialize(theta(-0.2, 0.0)).unwrap(),
        PersistentApfelContext::initialize(theta(-0.2, 0.25)).unwrap(),
    ];
    assert!(contexts.windows(2).all(|pair| {
        pair[0].identities().evaluator_policy_identity
            == pair[1].identities().evaluator_policy_identity
            && pair[0].identities().theta_transport_identity
                != pair[1].identities().theta_transport_identity
    }));
    assert!(contexts[0]
        .ensure_transport_identity(&contexts[1].identities().theta_transport_identity)
        .is_err());

    let context = Arc::new(contexts.into_iter().next().unwrap());
    let query = PersistentApfelQuery {
        flavor: 21,
        x: 0.01,
        q_gev: 10.0,
    };
    let expected = context.evaluate_scalar(query).unwrap().xf.to_bits();
    let before = context.diagnostics().unwrap();
    let threads = (0..4)
        .map(|_| {
            let context = Arc::clone(&context);
            std::thread::spawn(move || {
                (0..4)
                    .map(|_| context.evaluate_scalar(query).unwrap().xf.to_bits())
                    .collect::<Vec<_>>()
            })
        })
        .collect::<Vec<_>>();
    for thread in threads {
        assert!(thread
            .join()
            .unwrap()
            .into_iter()
            .all(|bits| bits == expected));
    }
    let after = context.diagnostics().unwrap();
    assert_eq!(after.scalar_calls, before.scalar_calls + 16);
    assert_eq!(after.cache_hits, before.cache_hits + 16);
}

#[test]
fn persistent_apfel_subprocess_child() {
    if std::env::var_os("PARTON_SBI_D1C_SUBPROCESS_CHILD").is_none() {
        return;
    }
    let context = PersistentApfelContext::initialize(theta(0.0, 0.0)).unwrap();
    assert!(context
        .evaluate_scalar(PersistentApfelQuery {
            flavor: 21,
            x: 0.01,
            q_gev: 10.0,
        })
        .unwrap()
        .xf
        .is_finite());
}

#[test]
fn persistent_apfel_constructs_and_destroys_in_an_independent_process() {
    let status = Command::new(std::env::current_exe().unwrap())
        .args([
            "--exact",
            "persistent_apfel_subprocess_child",
            "--nocapture",
        ])
        .env("PARTON_SBI_D1C_SUBPROCESS_CHILD", "1")
        .status()
        .unwrap();
    assert!(status.success());
}
