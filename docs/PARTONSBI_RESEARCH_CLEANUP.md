# PartonSBI research-only cleanup

## Scope

This cleanup converts the imported QuarkSim source tree into the research-only PartonSBI repository. It removes the Cornell-potential exercise and desktop GUI while preserving the validated DIS, APFEL++, LHAPDF, PYTHIA 8, HepMC3, HERA validation, uncertainty-analysis, and pointwise-surrogate infrastructure. It does not implement Phase 1A or any later inference phase.

## Imported baseline

- Imported baseline commit: `2384250` (`Splitting repo from my own repo quark-sim for research`).
- Initial working tree: clean.
- Initial `cargo check --workspace`: passed with 33 warnings concentrated in legacy GUI code.
- Initial `cargo test --workspace`: failed before tests because the validation harness used absolute paths from the previous checkout.
- Initial CTest: failed because generated CTest metadata referenced the previous checkout.

## Imported-repository relocation maintenance

`tests/validation_module_harness.rs` contained three absolute source paths rooted at `/mnt/c/Users/mirha/OneDrive/Belgeler/GitHub/neuronswq/quark_sim`. They were replaced with repository-relative `#[path = "../src/..."]` declarations. The module layout was adjusted only enough for the included validation source to retain its existing `super::structure_function_provider` contract; validation physics and snapshots were unchanged.

`physics-engine/build/` contained no tracked files (`git ls-files physics-engine/build` returned no output). The generated directory was removed and regenerated rather than editing CMake/CTest files. The exact successful commands were:

```bash
source scripts/pythia_env.sh
cmake -S physics-engine -B physics-engine/build \
  -DNLOHMANN_JSON_INCLUDE_DIR="$PWD/.external/include"
cmake --build physics-engine/build
```

The imported PYTHIA installation also embedded its former absolute XML-data path. `scripts/pythia_env.sh` now sets `PYTHIA8DATA` from repository-relative `PYTHIA8_ROOT`, restoring event generation without changing generator settings. `scripts/apfelxx_env.sh` now exports the existing repository-local nlohmann-json include directory so subsequent plain CMake regeneration follows the documented command.

Baseline after relocation maintenance and before cleanup:

- `cargo check --workspace`: passed;
- `cargo test --workspace`: passed, 149 tests with 5 explicitly ignored;
- CTest: passed, 1/1;
- `git diff --check`: passed; and
- no `physics-engine/build/` file was tracked or staged.

## Cleanup inventory

### Files removed

The final removed-file inventory is recorded in the cleanup commit and summarized here:

- Cornell model/training/trajectory/plotting sources: `src/model.rs`, `src/training.rs`, `src/scattering.rs`, `src/plotting.rs`, and `src/physics/legacy_cornell.rs`;
- the complete desktop layer under `src/gui/`;
- the Cornell-only `PRODUCTION_CONFIG.md`;
- tracked Python bytecode caches; and
- the generated `data/cache/apfel_predictions_cache.json` cache.

### Files renamed

No source file required a filesystem rename. Cargo derives the crate and primary binary names from the renamed package.

### Files created

- `AGENTS.md`;
- `docs/CURRENT_PHASE.md`; and
- `docs/PARTONSBI_RESEARCH_CLEANUP.md`.

## Identity and dependency changes

- Cargo package: `parton-sbi`.
- Rust crate: `parton_sbi`.
- Primary binary: `parton-sbi`.
- Display name: PartonSBI.
- Removed Cargo dependencies: `eframe`, `egui`, `egui_plot`, and `textplots`.
- Retained Candle, Plotters, serialization, CSV, LHAPDF, CLI, and validation dependencies.

## Preserved research modules

- exact finite-mass DIS four-vectors and kinematics;
- LO structure functions and cross sections;
- LHAPDF integration;
- APFEL++ backend and structure-function provider abstraction;
- structure-function validation and validation artifact generation;
- checked-in APFEL++ surrogate and training path;
- PYTHIA 8 generation and HepMC3 output;
- typed streaming HepMC3 extraction and run provenance;
- HERA validation and theory-uncertainty analysis;
- C++ backend tests, Rust tests, real reduced HepMC3 fixtures, APFEL snapshots, and HERA reference data; and
- amortized-inference audit, roadmap, and Phase 0A record.

## Command changes

The removed Cornell session, model-loading, training, and GUI launch modes no longer exist. Running `parton-sbi` without arguments now prints help. Scientific commands retained are `dis-kinematics`, `dis-cross-section`, `structure-functions`, `generate-dis-events`, `validate-hera`, `theory-uncertainties`, and `train-surrogate`.

## Tracked artifact cleanup

Generated build/install/output paths remain ignored. Python bytecode, local environments, theory caches, analysis outputs, local environment files, and closure-study outputs are now explicitly covered without ignoring source fixtures or checked-in reference data. `models/surrogate_v1/` and the reduced Phase 0A HepMC3 fixture are intentionally retained.

## Final validation

- `cargo fmt --all -- --check`: passed.
- `cargo check --workspace`: passed without Rust warnings.
- `cargo test --workspace`: passed, 115 tests; 5 existing LHAPDF installation tests remained explicitly ignored.
- Test-count change: 149 passed before cleanup to 115 passed after cleanup. The reduction removes GUI/Cornell tests; DIS validation tests remain, and new headless-default and generated-file parser checks were added.
- `ctest --test-dir physics-engine/build --output-on-failure`: passed, 1/1.
- `cargo run --release`: printed PartonSBI help and exited successfully without opening a window.
- `cargo run --release -- --help`: printed PartonSBI help and exited successfully.
- The representative APFEL NLO structure-function command passed for `x=0.01`, `Q2=100 GeV2`, `CT18NLO/0`.
- A two-accepted-event PYTHIA smoke run passed with seed `424242`; its generated `events.hepmc3` was parsed successfully by `HepMcReader` through the configured smoke-file test.
- Python analysis tests passed 19/19 through `unittest`; system Python lacked pytest, which is now declared in `analysis/requirements.txt` for a fresh analysis environment.
- `git diff --check`: passed.
- Remaining build warning: GNU Make reported transient sub-second clock skew for generated files on the OneDrive-mounted workspace. The rebuild and CTest completed successfully; no generated build files are tracked.

## Current scientific capabilities

PartonSBI is a headless forward-simulation and validation framework for inclusive DIS. It evaluates analytic/APFEL++/surrogate structure functions, generates PYTHIA events, preserves run provenance, streams HepMC3 records into typed Rust structures, and supports HERA comparison and theory-uncertainty analysis.

## Current scientific limitations

There is no PDF reweighting, continuous PDF family, pseudo-experiment dataset, posterior estimator, detector response, or unrestricted flavor separation. The analytic/APFEL photon-exchange and PYTHIA gamma/Z paths are not identical. `GenPdfInfo` and hard flavor remain generator truth rather than observed inference features. The surrogate remains a bounded pointwise interpolator and is not inference truth.

## Intentionally preserved legacy provenance

- `docs/AMORTIZED_INFERENCE_AUDIT.md` records the source-grounded pre-import QuarkSim state, paths, names, and audit commit.
- `docs/AMORTIZED_INFERENCE_PHASE0A_HEPMC3.md` records that Phase 0A was completed in the imported QuarkSim baseline and identifies the historical source run used for the reduced fixture.
- `docs/hepmc3_event_format.md` identifies the historical QuarkSim run from which the reduced real-event fixture was copied.
- `docs/CURRENT_PHASE.md` records import of the validated QuarkSim baseline and the absence of the removed Cornell demo.
- This cleanup report names removed identities, dependencies, files, and obsolete absolute paths so the migration is reviewable.
- Historical Git commit messages remain unchanged.

These references describe provenance and do not define active package names, commands, imports, or product identity.

## Readiness for Phase 1A

The validated DIS infrastructure is ready to begin Phase 1A as a separate task. Phase 1A itself was not implemented here, and Phase 1B/neural inference remain gated on its documented scientific decision.
