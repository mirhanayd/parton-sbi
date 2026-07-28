use std::fs;
use std::path::PathBuf;

use parton_sbi::physics::{
    build_or_load_artifact, evaluate_artifact, ArtifactGrid, ContinuousPdfContext,
    ContinuousPdfFamilyVersion, D1EvolutionConfig, PdfTheta, D1_FLAVORS,
    PDF_ARTIFACT_SCHEMA_VERSION,
};

fn test_cache() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(".external/partonsbi/tests/pdf-artifacts")
}

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
