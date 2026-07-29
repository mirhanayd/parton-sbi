use std::fs;
use std::path::PathBuf;

use parton_sbi::physics::{
    build_or_load_artifact, build_or_load_artifact_v2, evaluate_artifact, evaluate_artifact_v2,
    evolve_grid_v2, load_and_validate_artifact_v2, validate_moments_v2, ArtifactGrid,
    ArtifactGridV2, ComputationalGridKind, ContinuousPdfContext, ContinuousPdfFamilyVersion,
    D1EvolutionConfig, D1EvolutionConfigV2, PdfTheta, D1_FLAVORS, PDF_ARTIFACT_SCHEMA_VERSION,
    PDF_ARTIFACT_SCHEMA_VERSION_V2,
};

fn test_cache() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(".external/partonsbi/tests/pdf-artifacts")
}

const UNIT_TRACE_HASH: &str =
    "sha256:0000000000000000000000000000000000000000000000000000000000000000";

#[test]
fn d1_rejects_every_historical_v1_boundary() {
    let context = ContinuousPdfContext::load_ct18nlo_v1();
    if let Ok(context) = context {
        let error = D1EvolutionConfig::from_context(&context).unwrap_err();
        assert!(error.to_string().contains("only"));
        assert_eq!(context.family_version(), ContinuousPdfFamilyVersion::V1);
    }
}

#[test]
#[ignore = "requires APFEL++ 4.8.0, LHAPDF 6.5.6, and CT18NLO DataVersion 1"]
fn center_artifact_is_loadable_and_strictly_versioned() {
    let root = test_cache().join("center");
    let context = ContinuousPdfContext::load_ct18nlo_v2().unwrap();
    let artifact =
        build_or_load_artifact(&context, PdfTheta::new(0.0, 0.0).unwrap(), &root).unwrap();
    assert_eq!(artifact.manifest.member, 0);
    assert_eq!(
        artifact.manifest.schema_version,
        PDF_ARTIFACT_SCHEMA_VERSION
    );
    assert_eq!(
        artifact.manifest.family_version,
        "ct18nlo_two_parameter_boundary_v2"
    );
    assert_eq!(artifact.manifest.extrapolator_policy, "error");
    assert!(artifact.manifest.set_name.starts_with("PartonSBI_D1_"));
    assert!(artifact.set_directory.is_dir());
    let grid = ArtifactGrid::from_context(&context).unwrap();
    let xs = [grid.x_knots[0], grid.x_knots[grid.x_knots.len() - 1]];
    let qs = [
        grid.q_knots_gev[0],
        grid.q_knots_gev[grid.q_knots_gev.len() - 1],
    ];
    let loaded = evaluate_artifact(&artifact, &xs, &qs).unwrap();
    assert_eq!(loaded.flavors, D1_FLAVORS);
    assert!(loaded.xf_values.iter().all(|value| value.is_finite()));
    assert!(loaded.alpha_s_values.iter().all(|value| value.is_finite()));
    fs::remove_dir_all(root).unwrap();
}

#[test]
#[ignore = "requires APFEL++ 4.8.0, LHAPDF 6.5.6, and CT18NLO DataVersion 1"]
fn strict_support_refuses_every_extrapolation_request() {
    let root = test_cache().join("support");
    let context = ContinuousPdfContext::load_ct18nlo_v2().unwrap();
    let artifact =
        build_or_load_artifact(&context, PdfTheta::new(0.0, 0.0).unwrap(), &root).unwrap();
    let grid = ArtifactGrid::from_context(&context).unwrap();
    let q = [
        grid.q_knots_gev[0],
        grid.q_knots_gev[grid.q_knots_gev.len() - 1],
    ];
    assert!(evaluate_artifact(&artifact, &[grid.x_knots[0] / 2.0, 1.0], &q).is_err());
    assert!(evaluate_artifact(&artifact, &[grid.x_knots[0], 1.0], &[q[0] / 2.0, q[1]]).is_err());
    fs::remove_dir_all(root).unwrap();
}

#[test]
#[ignore = "requires APFEL++ 4.8.0, LHAPDF 6.5.6, and CT18NLO DataVersion 1"]
fn corruption_is_quarantined_and_regenerated_without_overwrite() {
    let root = test_cache().join("corruption");
    let theta = PdfTheta::new(0.0, 0.0).unwrap();
    let context = ContinuousPdfContext::load_ct18nlo_v2().unwrap();
    let artifact = build_or_load_artifact(&context, theta, &root).unwrap();
    let member = artifact
        .set_directory
        .join(format!("{}_0000.dat", artifact.manifest.set_name));
    let original = fs::read(&member).unwrap();
    fs::write(&member, b"corrupt").unwrap();
    let regenerated = build_or_load_artifact(&context, theta, &root).unwrap();
    assert_eq!(
        fs::read(
            regenerated
                .set_directory
                .join(format!("{}_0000.dat", regenerated.manifest.set_name))
        )
        .unwrap(),
        original
    );
    let parent = regenerated.cache_directory.parent().unwrap();
    assert!(fs::read_dir(parent)
        .unwrap()
        .filter_map(Result::ok)
        .any(|entry| entry.file_name().to_string_lossy().contains(".corrupt.")));
    fs::remove_dir_all(root).unwrap();
}

#[test]
#[ignore = "requires APFEL++ 4.8.0, LHAPDF 6.5.6, and CT18NLO DataVersion 1"]
fn concurrent_same_hash_builds_publish_one_identical_artifact() {
    let root = test_cache().join("concurrency");
    let handles = (0..2)
        .map(|_| {
            let root = root.clone();
            std::thread::spawn(move || {
                let context = ContinuousPdfContext::load_ct18nlo_v2().unwrap();
                build_or_load_artifact(&context, PdfTheta::new(0.2, -0.25).unwrap(), &root).unwrap()
            })
        })
        .collect::<Vec<_>>();
    let first = handles
        .into_iter()
        .map(|handle| handle.join().unwrap())
        .collect::<Vec<_>>();
    assert_eq!(first[0].manifest, first[1].manifest);
    assert_eq!(first[0].cache_directory, first[1].cache_directory);
    fs::remove_dir_all(root).unwrap();
}

#[test]
fn revised_evolution_is_explicitly_versioned_and_keeps_v1_distinct() {
    assert_ne!(PDF_ARTIFACT_SCHEMA_VERSION, PDF_ARTIFACT_SCHEMA_VERSION_V2);
    assert_eq!(
        PDF_ARTIFACT_SCHEMA_VERSION_V2,
        "partonsbi.lhapdf_artifact.v2"
    );
    let context = ContinuousPdfContext::load_ct18nlo_v1();
    if let Ok(context) = context {
        assert!(D1EvolutionConfigV2::from_context(&context).is_err());
    }
}

#[test]
#[ignore = "requires APFEL++ 4.8.0, LHAPDF 6.5.6, and CT18NLO DataVersion 1"]
fn revised_artifact_has_three_subgrids_and_strict_support() {
    let root = test_cache().join("revised-center");
    let context = ContinuousPdfContext::load_ct18nlo_v2().unwrap();
    let grid = ArtifactGridV2::initial(&context).unwrap();
    let theta = PdfTheta::new(0.0, 0.0).unwrap();
    let artifact =
        build_or_load_artifact_v2(&context, theta, &grid, UNIT_TRACE_HASH, &root).unwrap();
    assert_eq!(
        artifact.manifest.schema_version,
        PDF_ARTIFACT_SCHEMA_VERSION_V2
    );
    assert_eq!(artifact.manifest.grid.q_subgrids_gev.len(), 3);
    assert_eq!(
        artifact.manifest.grid.q_subgrids_gev[0].last(),
        artifact.manifest.grid.q_subgrids_gev[1].first()
    );
    assert_eq!(
        artifact.manifest.grid.q_subgrids_gev[1].last(),
        artifact.manifest.grid.q_subgrids_gev[2].first()
    );
    let reloaded = load_and_validate_artifact_v2(&artifact.cache_directory).unwrap();
    assert_eq!(artifact.manifest, reloaded.manifest);

    let xs = [grid.x_knots[0], grid.x_knots[grid.x_knots.len() - 1]];
    let qs = [
        grid.unique_q_knots_gev[0],
        grid.unique_q_knots_gev[grid.unique_q_knots_gev.len() - 1],
    ];
    let loaded = evaluate_artifact_v2(&artifact, &xs, &qs).unwrap();
    assert!(loaded.xf_values.iter().all(|value| value.is_finite()));
    assert!(evaluate_artifact_v2(&artifact, &[xs[0] / 2.0, xs[1]], &qs).is_err());
    assert!(evaluate_artifact_v2(&artifact, &xs, &[qs[0] / 2.0, qs[1]]).is_err());
    fs::remove_dir_all(root).unwrap();
}

#[test]
#[ignore = "requires APFEL++ 4.8.0, LHAPDF 6.5.6, and CT18NLO DataVersion 1"]
fn revised_full_domain_moments_are_accounted_separately_from_retained_support() {
    let context = ContinuousPdfContext::load_ct18nlo_v2().unwrap();
    let grid = ArtifactGridV2::initial(&context).unwrap();
    let theta = PdfTheta::new(0.0, 0.0).unwrap();
    let xs = [grid.x_knots[0], 1.0];
    let base = evolve_grid_v2(
        &context,
        theta,
        &xs,
        &grid.unique_q_knots_gev,
        ComputationalGridKind::Base,
    )
    .unwrap();
    let doubled = evolve_grid_v2(
        &context,
        theta,
        &xs,
        &grid.unique_q_knots_gev,
        ComputationalGridKind::Doubled,
    )
    .unwrap();
    let closure = validate_moments_v2(&base, &doubled).unwrap();
    assert!(closure.maximum_base_full_residual.is_finite());
    assert!(closure.maximum_doubled_full_residual.is_finite());
    assert!(closure.maximum_leakage > 0.0);
    assert!(closure.high_q_doubled.full_momentum > closure.high_q_doubled.retained_momentum);
}

#[test]
#[ignore = "requires APFEL++ 4.8.0, LHAPDF 6.5.6, and CT18NLO DataVersion 1"]
fn revised_cache_quarantines_corruption_and_serializes_concurrent_publication() {
    let root = test_cache().join("revised-cache");
    let context = ContinuousPdfContext::load_ct18nlo_v2().unwrap();
    let grid = ArtifactGridV2::initial(&context).unwrap();
    let theta = PdfTheta::new(0.0, 0.0).unwrap();
    let artifact =
        build_or_load_artifact_v2(&context, theta, &grid, UNIT_TRACE_HASH, &root).unwrap();
    let member = artifact
        .set_directory
        .join(format!("{}_0000.dat", artifact.manifest.set_name));
    let original = fs::read(&member).unwrap();
    fs::write(&member, b"corrupt").unwrap();
    let regenerated =
        build_or_load_artifact_v2(&context, theta, &grid, UNIT_TRACE_HASH, &root).unwrap();
    assert_eq!(fs::read(&member).unwrap(), original);
    assert!(regenerated
        .cache_directory
        .parent()
        .unwrap()
        .read_dir()
        .unwrap()
        .filter_map(Result::ok)
        .any(|entry| entry.file_name().to_string_lossy().contains(".corrupt.")));

    let concurrent_root = root.join("concurrent");
    let handles = (0..2)
        .map(|_| {
            let concurrent_root = concurrent_root.clone();
            let grid = grid.clone();
            std::thread::spawn(move || {
                let context = ContinuousPdfContext::load_ct18nlo_v2().unwrap();
                build_or_load_artifact_v2(
                    &context,
                    PdfTheta::new(0.2, -0.25).unwrap(),
                    &grid,
                    UNIT_TRACE_HASH,
                    &concurrent_root,
                )
                .unwrap()
            })
        })
        .collect::<Vec<_>>();
    let artifacts = handles
        .into_iter()
        .map(|handle| handle.join().unwrap())
        .collect::<Vec<_>>();
    assert_eq!(artifacts[0].manifest, artifacts[1].manifest);
    assert_eq!(artifacts[0].cache_directory, artifacts[1].cache_directory);
    fs::remove_dir_all(root).unwrap();
}
