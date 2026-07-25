# Phase 0A: streaming HepMC3 extraction

> Historical phase record: Phase 0A was completed before the imported QuarkSim
> codebase was renamed to PartonSBI. GUI references below describe the state at
> phase completion; the authoritative parser remains in the current library.

## Implementation summary

Phase 0A replaces the GUI-only, shifted-column parser with a reusable physics
module at `src/physics/hepmc3.rs`. It reads the real HepMC3 ASCII v3 syntax
written by the then-named QuarkSim PYTHIA backend, yields one event at a time, preserves all
numeric weights and relevant attributes, reconstructs explicit and compact
implicit vertices, and reports contextual typed errors.

No generator settings, event-generation physics, dependency manifests, PDF
parameterization, reweighting, pseudo-experiment construction, detector model,
or inference model were added or changed.

The GUI now consumes this module. Its display projection retains actual HepMC
particle IDs, PDG IDs, statuses, momenta, generated masses, production/end
vertices, and vertex incoming/outgoing lists.

## Files changed

Created:

- `src/physics/hepmc3.rs`;
- `tests/hepmc3_streaming.rs`;
- `tests/fixtures/hepmc3_real_minimal.hepmc3`;
- `tests/fixtures/hepmc3_real_minimal_config.json`;
- `tests/fixtures/hepmc3_real_minimal_metadata.json`; and
- this document.

Modified:

- `src/physics/mod.rs` to export the public contract;
- `src/gui/dis_event_viewer_page.rs`, `src/gui/state.rs`, and
  `src/gui/tests.rs` to use an explicit GUI projection;
- `src/physics/apfel.rs`, `src/physics/structure_function_provider.rs`,
  `src/physics/structure_function_validation.rs`, and
  `src/validation_artifacts.rs` for only the audit-approved stale test
  initializer/exhaustive-match compatibility fixes; and
- `docs/hepmc3_event_format.md` for the authoritative format description.

## Public API

The current `parton_sbi::physics` module exports:

- `HepMcReader<R: BufRead>` with `new`, `open`, `next_event`, `format_version`,
  and the standard `Iterator` implementation;
- `HepMcEvent` with `final_state_particles`, `beam_particles`, `particle`, and
  `scattered_electron` selectors;
- `HepMcParticle`, `HepMcVertex`, `HepMcPdfInfo`, and `HepMcAttribute`;
- `HepMcRunProvenance::load` and `enrich_beam_ids_from_event`;
- `HepMcRunCuts`; and
- `HepMcError`.

The event structure preserves declared counts, optional event position, units,
all weights, typed physics attributes, raw attributes, complete particles,
reconstructed vertices/connectivity, and source line bounds. Physical numeric
values use `f64`.

## Fixture origin

`hepmc3_real_minimal.hepmc3` is a reduced, deterministic fixture from the
existing historical QuarkSim-generated file:

```text
outputs/dis_run/dis_run_20260717_141023/events.hepmc3
```

It retains complete event blocks 225 and 2743, plus the original HepMC header
and footer. Both are unusually small real events (13 vertices and 19 particles)
and retain the original weights, `GenPdfInfo`, scales, alpha values, signal
process, flow attributes, beam/history/final particles, explicit vertices, and
compact implicit-vertex syntax. Matching JSON fixtures are reduced copies of
that run's `config.json` and `metadata.json`; the original run counts therefore
describe the source run rather than the two-event excerpt.

## Validation performed

Focused tests verify:

1. particle ID versus parent/production reference;
2. PDG ID and status columns (including protection against the old shift);
3. all four-momentum components and generated mass;
4. preservation of one or multiple signed weights;
5. all nine HepMC3 3.3.0 `GenPdfInfo` fields;
6. event scale and alpha/process attributes;
7. explicit and implicit vertex connectivity;
8. status-4 beam identification;
9. ancestry-based scattered-electron selection;
10. final-state filtering;
11. absent optional attributes represented as `None`/empty collections;
12. contextual errors for malformed mandatory particle records;
13. iterator traversal across both real events; and
14. merged run provenance, including explicit absence and event-based beam-ID
    enrichment.

Validation results in the supported WSL environment:

- `cargo test --test hepmc3_streaming`: **pass**, 9/9;
- `cargo check --workspace`: **pass** (existing warnings remain);
- `cargo test --workspace`: all parser, GUI, event-generation, APFEL, and
  validation tests reached by the run passed, but the unrelated pre-existing
  `tests/regression_tests.rs::test_surrogate_snapshot` failed because its child
  CLI omits the required `--pdf-set` option;
- `cargo test --workspace -- --skip test_surrogate_snapshot`: **pass** for all
  remaining tests; the five explicitly ignored LHAPDF integration tests remain
  ignored by their existing annotations;
- `ctest --test-dir physics-engine/build --output-on-failure`: **pass**, 1/1;
- `cargo fmt --all -- --check`: still fails on broad pre-existing formatting
  differences in files outside this phase; and
- `git diff --check`: **pass**.

No regression test was deleted, weakened, or marked ignored. The failing
surrogate snapshot was demonstrated directly with the exact child command,
which exits with `Error: missing required option: --pdf-set`; it was not repaired
because it is unrelated to Phase 0A.

## Remaining limitations

- The parser is intentionally scoped to the repository's HepMC3 ASCII v3 dialect;
  embedded general run-info blocks and other serialization formats are not yet
  represented.
- The GUI still materializes its display projections for navigation, although
  the scientific API is streaming.
- Current JSON does not serialize beam IDs, APFEL++ version, or Git dirty state.
  Those fields remain `None`; beam IDs can be derived from a same-run event.
- `GenPdfInfo::scale` and `event_scale` are retained without claiming distinct
  factorization and renormalization scales.
- Hard flavor and nominal `xf` values are provenance/reweighting truth, not
  observable model features.
- Signed weights are representable and tested in parsing, but the configured
  Born-level PYTHIA production path is not a validated negative-weight sample.

## Readiness for Phase 1 PDF reweighting

The Rust side now has the minimum trustworthy event tuple for a Phase 1
prototype: event weight, incoming parton IDs, `x1/x2`, PDF scale, nominal
`xf1/xf2`, PDF IDs, run PDF set/member, actual seed, and graph/kinematic truth.
This makes extraction ready for a reweighting closure study.

It does **not** establish that hard-PDF ratios are scientifically sufficient.
Phase 1 must still define a constrained PDF parameterization, implement the
ratio outside the observed-feature schema, and compare reweighted nominal
events with independently seeded direct regeneration while reporting support
overlap and effective sample size. Shower-dependent PDF effects and the
gamma/Z versus analytic photon-only mismatch remain unresolved.
