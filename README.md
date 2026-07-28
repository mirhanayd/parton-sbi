# PartonSBI

**PartonSBI: Simulation-Based Inference for Parton Structure from Event-Level Scattering Data**

PartonSBI is a research repository for forward simulation, extraction, and validation of inclusive deep-inelastic electron-proton scattering data. Its current role is primarily a forward simulation and validation framework: it provides tested DIS kinematics, structure-function calculations, event generation, provenance, and event-level extraction on which later simulation-based inference studies may be built.

## Scientific objective

The long-term inference unit is a pseudo-experiment containing a set of events,

```text
D = {event_1, ..., event_N},
```

with target posterior `p(theta_PDF | D)`. The objective is not to determine an instantaneous PDF for one proton from one event.

## Implemented capabilities

- exact finite-mass electron and proton beam four-vectors and inclusive DIS kinematics;
- leading-order electromagnetic DIS structure functions and differential cross sections using LHAPDF;
- LO/NLO photon-exchange structure functions through APFEL++;
- the checked-in Candle pointwise APFEL++ surrogate in `models/surrogate_v1/` and its existing training command;
- HERA comparison and theory-uncertainty analysis utilities;
- PYTHIA 8 neutral-current electron-proton event generation with configurable seeds, cuts, showering, and hadronization;
- HepMC3 event output plus JSON/CSV run artifacts;
- typed streaming Rust extraction of real HepMC3 ASCII v3 records, including all weights, `GenPdfInfo`, typed attributes, particles, vertices, and run provenance;
- typed discrete LHAPDF-member hard-PDF reweighting, member scanning, ESS and
  weight-tail diagnostics, plus fixed-bin closure-analysis infrastructure;
- the immutable Phase 1B-D0 v1 result and ADR-004 v2 sum-rule-projected
  input-scale two-parameter PDF boundary construction,
  authoritative CT18NLO metadata/knot audit, independent quadrature, canonical
  parameter identities, and deterministic Stage 0 validation CLI; and
- Rust, C++, and Python validation fixtures supporting these components.

## Explicit non-capabilities

PartonSBI implements only the D0 input-scale mathematical continuous boundary
family. It does not implement APFEL evolution of that family, an LHAPDF grid
artifact, PYTHIA coupling, direct event generation at continuous parameter
points, pseudo-experiment construction, amortized neural posterior inference,
detector simulation, unfolding, or real-data PDF extraction. Phase 1A discrete
LHAPDF-member reweighting infrastructure is implemented and Phase 1A is
complete with a negative result: the clean strict-support study failed the
fixed `ESS/N >= 0.20` gate. Nominal-pool reuse and the reweighting production
path are rejected; direct regeneration is required per PDF parameter point.
No direct-target closure was needed or claimed. The historical Phase 1B-D0 v1
pilot study remains `FAIL`. A separately versioned ADR-004 revalidation passed
its baseline-relative NLO input contract over 441 hard-box and 80 guard-shell
points. That PASS is only a D1 authorization candidate; D1 is not authorized.

Inclusive neutral-current electron-proton data do not provide unrestricted full-flavor PDF separation. The implemented channel primarily constrains charge-weighted quark-plus-antiquark combinations, with only indirect and correlated sensitivity to other directions. `GenPdfInfo`, hard flavor, and nominal PDF values are generator truth/provenance for validation and future reweighting studies; they are not detector-observed inputs and must not be exposed as default inference features.

## Repository architecture

```text
src/physics/       Rust DIS, PDF, APFEL, surrogate, and HepMC3 library code
src/main.rs        Headless scientific CLI
physics-engine/    C++17 APFEL++ and PYTHIA 8 subprocess backends
analysis/          HERA, uncertainty, and reweighting-closure analysis
models/            Validated checked-in structure-function surrogate artifact
tests/             Rust integration tests and deterministic fixtures
data/hepdata/      Source-controlled HERA reference data
scripts/           WSL-local and native-Ubuntu CI dependency setup and activation
docs/              Scientific scope, audit, roadmap, and phase records
docker/            Optional reproducible container build surface
```

The APFEL++ structure-function path and PYTHIA event path are separate. APFEL++ output is not injected into PYTHIA, and the pointwise surrogate is not an event generator or posterior model.

## Native dependencies

The supported local environment is WSL Ubuntu. The setup scripts install or configure:

- a Rust 2021 toolchain;
- CMake and a C++17 compiler;
- LHAPDF 6.5.6 with CT18LO and CT18NLO;
- APFEL++ 4.8.0;
- PYTHIA 8.312;
- HepMC3 3.3.0; and
- Python 3 with the packages in `analysis/requirements.txt`.

## WSL Ubuntu setup

Run all local commands from the repository root in WSL Ubuntu:

```bash
bash scripts/setup_all_wsl.sh
source scripts/pythia_env.sh
python3 -m venv analysis/venv
analysis/venv/bin/pip install -r analysis/requirements.txt
```

Do not use native Windows Rust/C++ tools, PowerShell, CMD, Git Bash, or WSLg. The default workflow is headless.

GitHub Actions runs on native Ubuntu rather than WSL and therefore uses the
dedicated CI entry point:

```bash
bash scripts/setup_ci_ubuntu.sh
```

That entry point requires GitHub Actions environment markers and is not a
replacement for the WSL-only local setup. A pushed change must complete the
remote workflow before CI can be described as green.

## Build

```bash
source scripts/pythia_env.sh
cmake -S physics-engine -B physics-engine/build
cmake --build physics-engine/build
cargo build --release
```

Running without a command prints help and exits normally:

```bash
cargo run --release
cargo run --release -- --help
```

## Tests

```bash
source scripts/pythia_env.sh
cargo fmt --all -- --check
cargo check --workspace
cargo test --workspace
ctest --test-dir physics-engine/build --output-on-failure
analysis/venv/bin/python -m pytest analysis/tests
git diff --check
```

The five LHAPDF installation tests are intentionally ignored by the normal Rust suite. Run them explicitly after environment activation:

```bash
cargo test --test lhapdf_integration -- --ignored
```

## Structure-function CLI

Evaluate APFEL++ at one point:

```bash
cargo run --release -- structure-functions \
  --backend apfel \
  --x 0.01 \
  --q2 100 \
  --order NLO \
  --pdf-set CT18NLO \
  --pdf-member 0
```

The existing `lo` and `surrogate` backends use the same command contract. The surrogate is a bounded pointwise interpolator and rejects out-of-domain queries.

## Event-generation CLI

Generate a small reproducible run:

```bash
cargo run --release -- generate-dis-events \
  --electron-energy 27.5 \
  --proton-energy 920.0 \
  --q2-min 10.0 \
  --events 10 \
  --seed 42 \
  --pdf-set CT18LO \
  --pdf-member 0 \
  --pdf-support-policy strict_in_grid \
  --output outputs/smoke
```

Each timestamped run contains `config.json`, `metadata.json`, `generator.log`, `events.hepmc3`, `inclusive_observables.csv`, and `summary.json`. Generated runs belong under ignored output directories and must not be committed.

`strict_in_grid` is the only supported generation policy. PartonSBI obtains
per-member bounds from authoritative LHAPDF metadata, uses their intersection,
and continues generation until the requested number of events passes DIS cuts,
momentum conservation, and strict PDF support. PDF extrapolation is disabled.
The support scale is the Q in GeV serialized as `GenPdfInfo::scale`; it is
squared exactly once for LHAPDF's `xfxQ2` call.

## HepMC3 extraction

The authoritative streaming reader is `parton_sbi::physics::HepMcReader`:

```rust
use parton_sbi::physics::HepMcReader;

let mut reader = HepMcReader::open("outputs/example/events.hepmc3")?;
while let Some(event) = reader.next_event()? {
    println!("event {}: {} particles", event.event_number, event.particles.len());
}
```

Load adjacent run provenance separately with `HepMcRunProvenance::load`. The parser keeps event data streaming and does not fabricate absent metadata.

## Discrete member reweighting

The Phase 1A CLI streams a generated run and writes compact diagnostics without
copying the HepMC3 event pool:

```bash
cargo run --release -- validate-pdf-reweighting \
  --nominal-run outputs/example-run \
  --target-pdf-set CT18NLO \
  --target-pdf-member 24 \
  --output outputs/example-reweighting
```

This command implements only the proton-side hard-PDF importance ratio. Hard
flavor and `GenPdfInfo` remain hidden generator truth. A successful command is
not, by itself, a closure result or permission to reuse an event pool.

## Continuous boundary-family validation

Validate one D0 parameter point:

```bash
cargo run --release -- validate-continuous-pdf-family \
  --family-version v2 \
  --delta-v 0 \
  --lambda-sea 0
```

The default `v1` contract is retained for historical reproducibility; v2 must
be selected explicitly. The `--anchors` and `--full-study` modes write compact
reports under an ignored output directory. This command evaluates only the
input-scale mathematical family. It does not evolve PDFs, write an LHAPDF
artifact, invoke PYTHIA, or generate events.

## Current roadmap

Completed groundwork includes the repository/scientific audit and Phase 0A
typed streaming HepMC3 extraction. Phase 1A is complete. The original blocked
smoke study is retained as historical evidence; a clean replacement generated
2,000 accepted in-support events under a no-extrapolation contract. Its nominal
`ESS/N = 0.04156296`, while mild member 24 and stress member 51 also remained
below 0.20. Pool reuse was therefore rejected before direct closure. The next
Phase 1B-D0 subsequently evaluated the proposed input family over exactly 441
hard-box points and 80 diagnostic guard-shell points. The v1 positivity and
central-reconstruction gates failed. ADR-004 then authorized a separate v2
projected-baseline study; its unchanged 441/80 scan passed without changing
family values, bounds, or numerical tolerances. D1 nevertheless remains
unauthorized until scientific review of that result. See
`docs/CURRENT_PHASE.md`, `docs/AMORTIZED_INFERENCE_PHASE1A_REWEIGHTING.md`,
`docs/AMORTIZED_INFERENCE_PHASE1BD_D0.md`, and
`docs/AMORTIZED_INFERENCE_PHASE1BD_D0R.md`.

## Scientific limitations

- The Rust LO and APFEL++ paths use a photon-exchange definition, while the current PYTHIA process enables gamma/Z exchange; these paths must not be treated as identical.
- APFEL++ uses a zero-mass variable-flavor-number scheme, which limits threshold studies.
- No target-mass, higher-twist, complete electroweak/radiative, or detector corrections are implemented.
- PYTHIA showering and hadronization are phenomenological and model dependent.
- The checked-in surrogate is an interpolation artifact, not simulation truth for inference.
- Hard-PDF direct closure and shower/hadronization sufficiency remain
  unvalidated because the predeclared ESS gate already rejected pool reuse;
  no direct sample was generated or claimed.
- The validated study domain is the declared DIS selection intersected with
  strict LHAPDF support, not the unrestricted PYTHIA domain.
- Both D0 versions are tied to CT18NLO member 0 at `Q0=1.295 GeV`. V1 failed;
  the v2 PASS is under review and does not make the box a production prior.

See `docs/scientific_scope_and_limitations.md` and the amortized-inference audit for the complete source-grounded limitations.

## Reproducibility policy

Seeds, PDF set/member, cuts, beam settings, native dependency versions, Git metadata where available, and run configuration must be retained with generated artifacts. Missing provenance remains explicitly absent. Generated event pools, caches, local environments, and analysis outputs are not source artifacts and must not be committed. Scientific approximations and negative closure/calibration results must be documented rather than hidden.

## Citation

No PartonSBI publication is claimed. A project citation will be added if and when an archival release or publication exists.
