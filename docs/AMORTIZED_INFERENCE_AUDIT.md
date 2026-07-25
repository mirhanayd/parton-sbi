# Amortized PDF inference: repository and scientific audit

> Historical provenance: this audit records the pre-cleanup QuarkSim source
> state and its original paths. Active PartonSBI commands and package metadata
> are documented in the repository README and `docs/CURRENT_PHASE.md`.

Audit date: 2026-07-25  
Repository root: `neuronswq/`  
Active Rust package: `neuronswq/quark_sim/`  
Audited Git commit: `cbfff1ee5902f830d03810e9b19cf54e1c699c72` on `main`

## Executive finding

QuarkSim has useful pieces for an eventual simulation-based PDF inference workflow, but it does **not** yet have an end-to-end parameterized forward model. It currently contains three related but disconnected paths:

1. a deterministic Rust LO photon-exchange calculation using one immutable LHAPDF member;
2. a deterministic APFEL++ subprocess that evaluates LO/NLO photon-exchange structure functions using one immutable LHAPDF member, plus a Candle interpolation surrogate for that pointwise calculation; and
3. a stochastic PYTHIA 8 `e- p` neutral-current event generator that independently selects its own LHAPDF member and writes HepMC3 plus a CSV.

APFEL++ output is not passed into PYTHIA, the Candle surrogate does not generate or reweight events, and no interface maps a continuous `theta_PDF` to a PDF at a reference scale. The scientifically correct future inference unit is a set of many events forming one pseudo-experiment, `D = {x_i}_{i=1}^N`, with target `p(theta_PDF | D)`. Nothing in the current repository implements that posterior.

Inclusive neutral-current electron-proton data alone do not identify fully flavor-separated PDFs. The present implemented channel primarily constrains charge-weighted quark-plus-antiquark combinations; high/low-`x` shape information and NLO scaling violations can add limited valence/sea/gluon sensitivity, but `u_v`, `d_v`, strange, and charm cannot all be independently extracted.

## 1. Repository state

### 1.1 Layout and build units

- The Git repository root is one directory above the active package. The root `README.md` describes an older LO-only state and conflicts with newer source code.
- `quark_sim/Cargo.toml` defines one Rust 2021 package named `quark_sim`. There is no `[workspace]` section and no multi-crate workspace.
- `quark_sim/build.rs` only embeds Git/Rust/OS metadata. It does not build or link the C++ engine.
- `quark_sim/physics-engine/CMakeLists.txt` is a separate CMake C++17 build. It creates `apfel_backend`, `apfel_cli`, `pythia_dis_backend`, `pythia_dis_cli`, and one registered CTest, `apfel_backend_test`.
- Native dependencies are installed outside Cargo. The WSL scripts pin LHAPDF 6.5.6, APFEL++ 4.8.0, PYTHIA 8.312, HepMC3 3.3.0/3.03.00, CT18LO, and CT18NLO.
- Candle Core/NN 0.8.4, managed-lhapdf 0.4.2, eframe 0.26.2, and Plotters 0.3.7 are locked in `Cargo.lock`.
- Local generated/install trees exist in `.external/`, `physics-engine/build/`, `target/`, `outputs/`, and `analysis/venv/`. They are not additional project crates.

The working tree was already dirty before this audit: `quark_sim/.gitignore` was modified, and `cover.png`, `meta.json`, `quark_sim/.github/`, and most of `quark_sim/analysis/` were untracked. Those changes were preserved. Only the two requested documents were added.

### 1.2 Documentation versus implementation

Several statements in documentation are stale or stronger than the implementation:

- Root `README.md` says there is no event generator, while `physics-engine/src/pythia_dis_generator.cpp` does generate events.
- `quark_sim/README.md` shows an `APFEL -> PYTHIA` edge, but no such data connection exists.
- Its event example uses `generate-events`, while the implemented subcommand is `generate-dis-events` (`src/main.rs::parse_command`).
- `docs/pythia8_dis_generation.md` says true values come from `pythia.info.Q2()`; source actually uses `-pythia.info.tHat()` and `pythia.info.x2()`.
- `docs/scientific_scope_and_limitations.md` describes the APFEL path as pure photon exchange. That is correct for APFEL, but PYTHIA enables `WeakBosonExchange:ff2ff(t:gmZ)`, a gamma/Z process. The two paths therefore do not share an identical electroweak definition.
- The GUI offers a charged-current choice in `src/gui/dis_config_page.rs`, but `DisConfig.process` is neither validated nor passed by `build_event_generation_command`; the Rust and C++ event requests hard-code neutral current.
- The GUI offers the surrogate backend, but `DisConfig::validate` rejects `"surrogate"`, and the GUI looks for `models/surrogate_v1/config.json` while the checked-in file is `model_config.json`.

### 1.3 Installed native baseline

The audited WSL environment resolved:

| Component | Observed version/location |
| --- | --- |
| Rust | `rustc 1.97.1`, `cargo 1.97.1` |
| CMake / C++ | CMake 3.28.3, GCC 13.3.0 |
| Python | 3.12.3 |
| LHAPDF | 6.5.6 under `/home/mrxn/.local/lhapdf-6.5.6` |
| APFEL++ | 4.8.0 under `.external/apfelxx-4.8.0` |
| PYTHIA | 8.312 under `.external/pythia-8.3.12` |
| HepMC3 | 3.03.00 under `.external/hepmc3-3.3.0` |
| CT18NLO | 59-member Hessian set, `QMin=1.295 GeV`, `QMax=1e5 GeV` |
| CT18LO | one member, same reported Q range |

`scripts/pythia_env.sh` is the complete activation helper because it sources APFEL++ and LHAPDF first and then exports the PYTHIA/HepMC paths and `PYTHIA_BACKEND_BIN`. The primary README only tells users to source `apfelxx_env.sh`, which is insufficient as a clean event-generation instruction.

## 2. Build and test status

All commands were invoked through WSL Ubuntu from `quark_sim/` after sourcing `scripts/pythia_env.sh` where native libraries were relevant.

| Check | Result |
| --- | --- |
| `cargo fmt --all -- --check` | **Fail.** Existing formatting differences span `src/main.rs`, GUI files, surrogate files, and `tests/regression_tests.rs`. No formatting was applied. |
| `cargo check --workspace` | **Pass** in 51.96 s, with 32 warnings. Warnings include unused imports/dead code and future-incompatible `f64` literal fallback to `f32`. |
| `cargo test --workspace` | **Fail at test compilation.** No trustworthy full Rust test result exists. |
| `ctest --test-dir physics-engine/build --output-on-failure` | **Pass:** `apfel_backend_test`, 1/1. |
| `python3 -m pytest analysis/tests` | **Cannot start:** `/usr/bin/python3: No module named pytest`. |
| `analysis/venv/bin/python -m pytest analysis/tests` | **Cannot start:** checked-in venv also has no `pytest`. |

The relevant Rust test compile errors are:

```text
error[E0063]: missing fields `git_commit`, `git_dirty`, `hepmc_version` and 4 other fields
  --> src/physics/apfel.rs:417:9

error[E0063]: missing fields `git_commit`, `git_dirty`, `hepmc_version` and 4 other fields
  --> src/physics/structure_function_provider.rs:706:9

error[E0063]: missing fields ...
  --> src/physics/structure_function_validation.rs:868:28

error[E0063]: missing fields ...
  --> src/validation_artifacts.rs:556:27

error[E0004]: non-exhaustive patterns: `StructureFunctionBackend::Surrogate` not covered
  --> src/physics/structure_function_validation.rs:585:11
```

The Python requirement file declares NumPy, SciPy, pandas, and Matplotlib but not pytest. The CI workflow is currently untracked and located under `quark_sim/.github/`; if committed there without moving it to the Git root, GitHub will not discover it. Its Cargo commands also assume the package is at repository root.

## 3. Forward-pipeline map

There is no single connected forward pipeline. The source-grounded paths are shown below.

```text
Rust analytic point path
ColliderBeams + scattered FourVector
  -> DisKinematics
  -> LhapdfProvider / PartonDensities
  -> LoStructureFunctions
  -> LoDisCrossSection

Pointwise higher-order path
StructureFunctionRequest
  -> ApfelStructureFunctionProvider JSON subprocess
  -> C++ APFEL++ callback backed by one LHAPDF::PDF
  -> StructureFunctionResult(F2, FL, xF3, metadata)
  -> optional Candle SurrogateProvider interpolation

Event path (independent of both paths above)
GenerateDisEventsCliArgs
  -> JSON + pythia_dis_cli
  -> Pythia8::Pythia configured with LHAPDF set/member
  -> hard NC gamma/Z event
  -> ISR/FSR shower (optional), MPI off
  -> hadronization/decays (optional)
  -> HepMC3 Pythia8ToHepMC3 + inclusive_observables.csv
  -> simplified Rust GUI ASCII parser (currently incorrect for real P records)
```

### 3.1 Stage-by-stage properties

| Stage | File and public symbol | Input -> output | Determinism / differentiability | Batch/offline suitability | Metadata and seeds |
| --- | --- | --- | --- | --- | --- |
| Beam configuration | `src/physics/dis_kinematics.rs::{incoming_electron,incoming_proton,collider_beams}`, `ColliderBeams` | beam energies -> two `FourVector`s | Deterministic; ordinary `f64`, not autograd-differentiable | Scalar API; trivially loopable; suitable offline | No metadata object |
| Scattered lepton / invariants | `scattered_electron`, `compute_dis_kinematics`, `DisKinematics`, `DisCuts` | three `FourVector`s -> `q,Q2,s,x,y,W2` | Deterministic; not connected to autograd | Scalar, loopable | No event ID/seed |
| Rust PDFs | `src/physics/pdf.rs::{PdfProvider,LhapdfProvider,PartonDensities}` | `(x,Q2)` -> eleven `x f_i` fields | Deterministic interpolation; native opaque/non-differentiable | Scalar only, loopable; good for grids | Provider retains set/member/grid metadata but result does not carry it |
| Rust LO SF | `src/physics/structure_functions.rs::{evaluate_lo_structure_functions,electromagnetic_f2_from_xf}` | `PdfProvider,(x,Q2)` -> `LoStructureFunctions` | Deterministic/non-differentiable in current representation | Scalar, loopable | Returns densities, not provenance |
| APFEL SF | `src/physics/apfel.rs::ApfelStructureFunctionProvider::evaluate`; `physics-engine/src/apfel_backend.cpp::evaluate_impl` | `StructureFunctionRequest` -> `StructureFunctionResult` | Deterministic for fixed libraries/grid; subprocess and native code are not differentiable | One subprocess per point; technically parallelizable, not a true batch API | Strong set/member/order/scale/version metadata; no RNG |
| Differential cross section | `src/physics/cross_section.rs::lo_differential_cross_section` | `x,Q2,s,F2,coupling` -> `LoDisCrossSection` | Deterministic/non-autograd | Scalar, loopable | No provenance beyond numerical fields |
| Event orchestration | `src/main.rs::{parse_generate_dis_events_command,run_generate_dis_events}`, `GenerateDisEventsCliArgs` | CLI -> config JSON/run directory | Deterministic orchestration; generator seed controls stochastic work | One run per subprocess; offline-capable | Writes config before backend; run-level seed metadata |
| Hard event | `physics-engine/src/pythia_dis_generator.cpp::run_generator` | `DisEventRequest` -> `Pythia8::Event` | Stochastic/non-differentiable | Sequential accepted-event loop; offline generation is its main use | Explicit or time-derived seed; set/member recorded at run level |
| Shower/hadronization | same function; `PartonLevel:*`, `HadronLevel:all` | hard record -> full event | Stochastic/non-differentiable | No batch API; offline | Controlled by same Pythia RNG; switches recorded |
| HepMC3 output | `Pythia8ToHepMC3::fill_next_event`, `HepMC3::WriterAscii` | Pythia event -> `events.hepmc3` | Deterministic serialization conditional on event | Streaming event writes; suitable offline | `W`, `GenPdfInfo`, event scale and other attributes in raw file; run seed/set/member only in separate JSON |
| Inclusive CSV | `run_generator` CSV block | accepted event -> 20 scalar columns | Deterministic extraction | Compact and batch-friendly | Event number and event weight; no flavor, scale, seed, or set/member columns |
| HepMC reader/UI | `src/gui/dis_event_viewer_page.rs::{parse_hepmc3,filter_final_state,filter_by_pdg}` and `src/gui/state.rs::{HepMC3Event,HepMC3Particle,HepMC3Vertex}` | ASCII string -> simplified Rust structs | Deterministic/non-differentiable | Reads entire file into memory, so unsuitable for large training corpora | Keeps only one weight; discards attributes and genealogy; parsing bug described below |
| Candle SF surrogate | `src/physics/surrogate.rs::{SurrogateModel,SurrogateProvider}` | `[log10 x,log10 Q2,muF/Q,muR/Q]` -> `[F2,FL,xF3]` | Deterministic inference; differentiable inside Candle w.r.t. tensor inputs/weights | MLP accepts leading batch dimension; CPU-only provider | Model config stores domain, source set/member/order and metrics |
| Candle SF training | `src/physics/surrogate_training.rs::{generate_dataset,train_and_save_surrogate}` | 225-point APFEL grid -> saved MLP | APFEL targets deterministic; split RNG fixed to 42; weight initialization reproducibility is not documented | Full-batch CPU training | Stores normalizations and two aggregate metrics, not full split IDs |
| Legacy Candle model | `src/model.rs::QuarkModel`, `src/training.rs` | random 3-vector -> Cornell scalar | Unrelated to DIS; training RNG is not seeded | Full-batch | No reproducible training seed |

No stage after APFEL is wired to the event generator. The APFEL structure-function surrogate cannot be substituted for the PYTHIA hard-process PDF.

## 4. Event-information audit

### 4.1 Writer and observed files

The generator writes six files per timestamped run: `config.json`, `metadata.json`, `generator.log`, `events.hepmc3`, `inclusive_observables.csv`, and `summary.json` (`src/main.rs::run_generate_dis_events`). An inspected 10,000-event run used 86 MiB for HepMC3 (1,051,418 lines) and 1.5 MiB for the scalar CSV (10,001 lines). This size difference matters for a many-pseudo-experiment training design.

Raw HepMC3 contains more information than the Rust reader exposes. An observed event includes:

```text
W <event weight>
A 0 GenPdfInfo <id1> <id2> <x1> <x2> <scale> <xf1> <xf2> ...
A 0 alphaQCD ...
A 0 alphaQED ...
A 0 event_scale ...
A 0 signal_process_id ...
P ... <PDG ID> <px> <py> <pz> <E> <m> <status>
```

### 4.2 Truth-level fields

| Requested field | Status | Source / caveat |
| --- | --- | --- |
| Incoming electron four-vector | **Exists in raw HepMC3**; derivable from run config | Beam particle status 4. Not present in CSV. |
| Incoming proton four-vector | **Exists in raw HepMC3**; derivable from run config | Beam particle status 4. Not present in CSV. |
| Scattered electron four-vector | **Exists** | Explicit CSV `E,px,py,pz`; raw HepMC3 final electron plus history. |
| `x`, `Q2`, `y`, `W2` | **Exists** | CSV has hard-labeled and electron-reconstructed values plus absolute mismatches. The “true” definitions use `-tHat`, `x2`, derived `y`, and proton mass. |
| Hard-process flavor | **Available in raw record, not exposed by project reader/CSV** | `GenPdfInfo` carries incoming parton IDs; documentation-status particles also encode hard history. Requires a correct HepMC3 reader and semantics tests. |
| Parton-level final state | **Exists conditionally/raw** | Full Pythia history is serialized; clean final partons are easiest when hadronization is off. No typed Rust extraction. |
| Hadron-level final state | **Exists when enabled** | Stable and intermediate particles in raw HepMC3. |
| Particle IDs | **Exists raw** | PDG IDs in `P` records. Current GUI parser reads the production-vertex token as PDG ID and is wrong for actual files. |
| Charges | **Derivable, not stored per particle** | Pythia uses `chargeType()` only for the CSV charged multiplicity. A PDG database/table is needed for per-particle charge. |
| Status codes | **Exists raw** | Current GUI parser is shifted and therefore also reads status incorrectly. |
| Event weights | **Exists** | HepMC3 `W` and CSV `event_weight`. Observed weights are not always one. |
| Factorization/renormalization scales | **Partial** | Raw attributes contain one `event_scale` and `GenPdfInfo` scale. Separate `mu_F` and `mu_R` are not written, and event CLI has no scale-ratio controls. |
| Generator random seed | **Run-level only** | Actual Pythia seed in `metadata.json`; no per-event seed/substream. |
| PDF set/member | **Run-level only** | `metadata.json` and `config.json`; not embedded by name/member in each HepMC event or CSV row. |

### 4.3 Reader defect

Actual HepMC3 ASCII particle records look like `P particle_id production_vertex pdg_id px py pz E m status`. `parse_hepmc3` treats token 2 as the PDG ID and shifts every later field left. It also assigns particles a sequential vector index rather than retaining the HepMC particle ID, leaves both vertex-link fields `None`, ignores bracketed vertex connectivity, and skips all `A` attributes including `GenPdfInfo` and event scales. Tests in `src/gui/tests.rs` use a simplified fixture consistent with the incorrect parser, so they do not catch the mismatch.

Until this is replaced or corrected, the GUI representation is not a scientifically reliable event reader. The raw HepMC3 written by HepMC3 itself remains the authoritative event record.

### 4.4 Future detector-level fields

| Detector-level field | Current state |
| --- | --- |
| Smeared scattered-electron energy/angle | Unavailable |
| Reconstructed detector-level `Q2,x,y` | Unavailable; current `_reco` fields are generator-level electron-method values, not detector reconstruction |
| Acceptance masks | Unavailable |
| Efficiencies | Unavailable |
| Particle-identification outputs | Unavailable |
| Reconstructed hadronic observables | Unavailable |

Truth particles can seed a future fast detector response, but no detector schema, smearing, acceptance, PID, reconstruction, or nuisance metadata exists today.

## 5. PDF-parameterization feasibility

### 5.1 How PDFs are supplied now

- Rust LO: `LhapdfProvider::new(set_name, member)` owns one `managed_lhapdf::Pdf`. The general `PdfProvider` trait could accept a new Rust implementation for the LO formula, but none represents continuous fit parameters.
- APFEL++: `evaluate_impl` loads `LHAPDF::mkPDF(request.pdf_set, request.pdf_member)`. Its APFEL `distributions` callback closes over that immutable LHAPDF object.
- PYTHIA: `PDF:pSet = LHAPDF6:<set>/<member>` is configured once before `pythia.init()`.
- Theory uncertainty code evaluates discrete LHAPDF members and scale variations. It does not define a continuous PDF fit parameterization.

### 5.2 Answers to feasibility questions

1. **Does QuarkSim only load immutable LHAPDF grids?** For actual production backends, yes. The Rust `PdfProvider` trait is abstract, but the only real implementation is immutable LHAPDF. APFEL and PYTHIA also load named set/member grids.
2. **Can APFEL++ receive a custom continuously parameterized PDF function?** APFEL++ itself is called with a C++ distribution callback, so the underlying library mechanism can accept a different function. QuarkSim's JSON schema and backend do not expose one; the callback is hard-wired to LHAPDF.
3. **Can event weights be recomputed for alternative PDF parameters?** Not by current code. There is no event reweighter and no `theta_PDF` evaluator. APFEL member/scale arrays apply only to pointwise structure functions.
4. **Does the generator expose enough information for PDF reweighting?** Raw HepMC3 includes a promising minimal hard-process tuple via `GenPdfInfo` (incoming IDs, `x1/x2`, scale, nominal `xf1/xf2`) plus event weight, and run JSON identifies the nominal set/member. The CSV and Rust reader do not expose this tuple. It is enough to prototype a proton-side hard-PDF ratio, but not enough to claim exact shower-aware reweighting without validation.
5. **Can one nominal pool be reused through importance weighting/resampling?** Potentially for restricted, support-overlapping PDF deformations using `w_target = w_nominal * f_target(id,x,muF)/f_nominal(id,x,muF)`. This is not implemented or validated. Effective sample size, tail weights, cut migration, flavor mixtures, and correlations must be checked against independently regenerated target samples.
6. **Would arbitrary PDF parameters require regenerating PYTHIA events?** With the current interface, yes: they must first be materialized as a loadable LHAPDF set/member and PYTHIA reinitialized. Even after adding a hard-event reweighter, exact changes to PDF-dependent ISR/shower evolution generally require regeneration or a validated shower-reweighting mechanism.
7. **Are positive and negative event weights supported?** HepMC3 `W`, the CSV `double`, the Rust `f64`, and the Python `sqrt(sum w_i^2)` utility can represent signed values. The configured PYTHIA Born process does not intentionally generate a signed NLO-weight sample, negative-weight behavior has no test, and the Rust LO cross-section path rejects a negative structure-function factor. End-to-end signed-weight support is therefore unverified.
8. **Are sum rules enforced?** No QuarkSim parameterization or numerical sum-rule checks exist. Named LHAPDF sets are assumed to have been fitted consistently upstream.

### 5.3 Required proof before training data production

Before claiming continuous-parameter training data, the project needs a closure test that:

1. extracts `GenPdfInfo` and event weights with a standards-compliant streaming HepMC3 reader;
2. generates nominal and alternate discrete LHAPDF-member samples with disjoint seeds;
3. reweights the nominal sample to the alternate member;
4. compares weighted `x,Q2,y`, flavor, multiplicity, and selected hadronic distributions to direct regeneration;
5. reports effective sample size and maximum/quantile weight ratios; and
6. defines whether the accepted approximation is hard-process-only or includes PDF-dependent shower effects.

Failure of this test means the MVP must regenerate events for each parameter point.

## 6. Identifiability audit

### 6.1 Implemented channels

| Channel or handle | Implemented? | Evidence |
| --- | --- | --- |
| NC `e- p` DIS | **Yes** | Rust types restrict projectile to `Electron`, target to `Proton`; Pythia beams are PDG 11 and 2212. |
| NC `e+ p` DIS | **No generator/provider mode** | Python validation reads an `e+p` HERA table, but APFEL request still says electron and pure photon `xF3=0`; no positron beam option. |
| CC `e- p` / `e+ p` | **No** | GUI label only; C++ request rejects processes other than neutral current. |
| Neutron/deuteron/nuclear targets | **No** | `DisTarget` has only `Proton`; Pythia proton is hard-coded. |
| Charm-tagged observables | **No** | Charm particles may occur in raw events, but no tag definition, efficiency, or tagged cross section exists. |
| Strange-sensitive observables | **No dedicated channel** | Strange contributes only inside inclusive charge-weighted sums; identified kaons do not constitute a validated strange tag. |
| Semi-inclusive observables | **No analysis implementation** | Raw final states exist, but no SIDIS observable/fragmentation-function calculation or schema exists. |
| Identified hadrons | **Raw PDG IDs only** | No calibrated identified-hadron observable. |
| Hadronic jets | **No** | No jet clustering dependency or code. |
| Multiple beam energies | **Configurable one run at a time** | Electron and proton energies are CLI/config fields. No joint multi-energy dataset schema exists. |

The Pythia process includes gamma/Z exchange while the APFEL result forces parity-violating charges to zero. Charge-sign sensitivity from `xF3` is therefore absent from the pointwise provider and inconsistent across paths.

### 6.2 Constrainable PDF combinations

For pure-photon inclusive NC DIS, the leading combination is approximately

```text
F2 ~ x [4/9 (u+ubar+c+cbar) + 1/9 (d+dbar+s+sbar+b+bbar)].
```

- **`u_v`:** appreciable high-`x` sensitivity because the proton and charge factor favor `u`, but not a clean independent `u_v` measurement.
- **`d_v`:** much weaker and highly correlated with `u_v`; no neutron/deuteron or CC channel breaks the degeneracy.
- **Sea:** low-`x` data constrain a charge-weighted sea combination, not separate `ubar`, `dbar`, and `s`.
- **Gluon:** absent from the Rust LO `F2`; indirect sensitivity appears at NLO through coefficient functions and `Q2` scaling violations. A broad `Q2` lever arm and internally consistent evolution are required.
- **Strange:** not independently identifiable from the current inclusive channel. It is entangled with other down-type sea PDFs.
- **Charm:** inclusive charm contribution is entangled with the up-type singlet and heavy-flavor scheme. No charm tag exists, and the APFEL backend uses ZM-VFNS near threshold.

The current observable set can support a low-dimensional closure test for a **common valence-shape direction and a common light-sea normalization/shape direction**, possibly with a dependent gluon normalization imposed by the momentum sum rule. It cannot support a claim of full flavor separation.

Multiple beam energies could help separate `F2` and `FL` through different `y`, improving gluon sensitivity, but the current project has no multi-run dataset abstraction. Adding `e+`, CC, neutron/deuteron, charm-tagged, or jet channels would provide genuinely new flavor information and belongs to later phases.

## 7. Existing ML capability

Two Candle MLPs exist:

- `src/model.rs::QuarkModel` is a `3 -> 256 -> 128 -> 64 -> 1` regression model for the unrelated Cornell demonstration.
- `src/physics/surrogate.rs::SurrogateModel` is a `4 -> 128 -> 64 -> 32 -> 3` pointwise APFEL interpolator. It is trained in Rust with AdamW by `train_and_save_surrogate`.

Neither is a set encoder or posterior estimator. The surrogate training grid has only `5 x 5 x 3 x 3 = 225` possible points before failures, randomly splits individual grid points 70/15/15, uses CPU full-batch training, and reports only validation MSE and maximum test relative `F2` error. The checked-in config reports a maximum test relative error of about 1.125 (112.5%), so it is not an adequate truth replacement for inference data generation.

Candle already supplies tensors, autograd, linear layers, AdamW, CPU/optional CUDA, and safetensors. A two-parameter DeepSets Gaussian posterior needs no second ML stack. Missing research infrastructure includes event-set batching/masking, Gaussian likelihood utilities, controlled model initialization seeds, experiment manifests, checkpoints/resume, calibration metrics, and leakage-safe dataset splits.

## 8. Blockers

### Must be resolved before any inference model is trained

1. No continuous, sum-rule-preserving `theta_PDF -> f_i(x,Q0)` parameterization is exposed to APFEL/PYTHIA.
2. Reweighting feasibility is unvalidated; arbitrary current parameters require discrete LHAPDF grids and regeneration.
3. The Rust HepMC3 reader misparses real particle records and discards the attributes needed for reweighting.
4. APFEL and PYTHIA are disconnected and use inconsistent electroweak definitions (pure photon versus gamma/Z).
5. No pseudo-experiment/set data schema, split provenance, pool ID, or seed-family ID exists.
6. Full Rust tests do not compile; formatting also fails.
7. No detector response exists, which is acceptable only for the first truth-level closure test.

### User decisions required before implementation proceeds beyond the prerequisite phase

- Accept a deliberately non-flavor-separated two-parameter PDF family for the first closure test, or require additional observable channels first.
- Choose hard-process PDF reweighting as an explicitly approximate MVP path if it passes closure, or require direct PYTHIA regeneration at every parameter point.
- Decide whether the event-MVP process definition is PYTHIA gamma/Z or a harmonized photon-only model; it must not silently mix the two.

## 9. Exact source references and inspected files

The repository tree was enumerated excluding only `.git`; large installed/generated trees (`.external`, `target`, `physics-engine/build`, `analysis/venv`) were identified and then excluded from source inventory. The following project files were directly read or targeted by symbol/content scans:

- Root: `.gitattributes`, `README.md`, `quark_sim/.gitignore`, `quark_sim/Cargo.toml`, `quark_sim/Cargo.lock`, `quark_sim/build.rs`, `quark_sim/README.md`, `quark_sim/PRODUCTION_CONFIG.md`.
- Build/CI: `quark_sim/physics-engine/CMakeLists.txt`, `quark_sim/docker/{Dockerfile,build.sh,run.sh}`, `quark_sim/scripts/{apfelxx_env.sh,lhapdf_env.sh,pythia_env.sh,setup_all_wsl.sh,setup_apfelxx_wsl.sh,setup_hepmc3_wsl.sh,setup_lhapdf_wsl.sh,setup_pythia8_wsl.sh}`, `quark_sim/.github/workflows/ci.yml`.
- Rust root: `quark_sim/src/{lib.rs,main.rs,model.rs,plotting.rs,scattering.rs,structure_function_cli.rs,training.rs,validation_artifacts.rs}`.
- Rust physics: every file under `quark_sim/src/physics/`: `apfel.rs`, `constants.rs`, `cross_section.rs`, `dis_kinematics.rs`, `four_vector.rs`, `legacy_cornell.rs`, `mod.rs`, `pdf.rs`, `structure_function_provider.rs`, `structure_function_validation.rs`, `structure_functions.rs`, `surrogate.rs`, `surrogate_training.rs`.
- Rust GUI: every file under `quark_sim/src/gui/`: `dis_config_page.rs`, `dis_event_gen_page.rs`, `dis_event_viewer_page.rs`, `dis_inclusive_page.rs`, `dis_run_history_page.rs`, `dis_validation_page.rs`, `legacy_cornell.rs`, `mod.rs`, `state.rs`, `tests.rs`, `theme.rs`, `worker.rs`.
- C++: `quark_sim/physics-engine/include/{apfel_backend.hpp,pythia_dis_generator.hpp}`, `quark_sim/physics-engine/src/{apfel_backend.cpp,apfel_cli.cpp,pythia_dis_cli.cpp,pythia_dis_generator.cpp}`, `quark_sim/physics-engine/tests/apfel_backend_test.cpp`.
- Rust tests/fixtures: every file under `quark_sim/tests/`: `dis_cli.rs`, `dis_kinematics.rs`, `lhapdf_integration.rs`, `pythia_integration_tests.rs`, `regression_tests.rs`, `validation_module_harness.rs`, `fixtures/apfel_nlo.json`.
- Analysis: `analysis/requirements.txt`; all Python files under `analysis/hepdata/`, `analysis/validation/`, and `analysis/tests/`; `data/hepdata/HERA1+2_NCep_920.dat`; `data/cache/apfel_predictions_cache.json` was inventoried as an existing cache.
- Documentation: every pre-existing Markdown file under `quark_sim/docs/`: `chi_square_method.md`, `dis_kinematics.md`, `hepdata_sources.md`, `hepmc3_event_format.md`, `hera_validation.md`, `lhapdf_integration.md`, `lo_dis_cross_section.md`, `pythia8_dis_generation.md`, `reproducibility.md`, `scientific_scope_and_limitations.md`, `theory_uncertainties.md`.
- Models/artifacts: `models/surrogate_v1/model_config.json`; `model.safetensors` was inventoried as a binary artifact.
- Existing event evidence: `outputs/dis_run/dis_run_20260717_141023/{config.json,metadata.json,summary.json,events.hepmc3,inclusive_observables.csv}` and output run/file inventories.

## 10. Exact WSL baseline commands

The build/test commands that determine the baseline were:

```bash
cd /mnt/c/Users/mirha/OneDrive/Belgeler/GitHub/neuronswq/quark_sim
source scripts/pythia_env.sh
rustc --version
cargo --version
cmake --version | head -1
c++ --version | head -1
python3 --version
pkg-config --modversion lhapdf
apfelxx-config --version
pythia8-config --version
hepmc3-config --version
ldd physics-engine/build/apfel_cli
ldd physics-engine/build/pythia_dis_cli
cargo fmt --all -- --check
cargo check --workspace
cargo test --workspace
ctest --test-dir physics-engine/build --output-on-failure
python3 -m pytest analysis/tests
analysis/venv/bin/python -m pytest analysis/tests
```

Read-only inventory/source commands included `git status --short`, `git ls-files`, `git ls-files --others --exclude-standard`, `find` with generated-tree exclusions, `wc -l`, `sed -n`, `grep -RInE`, `du -h`, and inspection of installed CT18 metadata. `rg` was attempted first as the preferred search tool but is not installed in the WSL distribution (`bash: rg: command not found`), so `grep` was used. The first unrestricted `find` timed out because it descended into large generated dependency/build trees; the subsequent source inventory explicitly pruned those trees.
