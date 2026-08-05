# Repository strategy and planned layout

## Current decision

```text
CURRENT_REPOSITORY = parton-sbi
CURRENT_ARCHITECTURE = MONOREPO_WITH_INDEPENDENT_RESEARCH_LINE
REPOSITORY_STRATEGY = KEEP_IN_PARTON_SBI
```

No repository split is active or authorized.

## Split triggers

A separate `reduced-dis-sim` repository may be proposed only if at least one
condition becomes true:

1. the reduced simulator becomes useful outside PartonSBI;
2. it requires an independent public API and semantic versioning;
3. multiple downstream projects depend on it;
4. it needs an independent release and governance cycle; or
5. simulator development becomes scientifically independent of PDF posterior
   inference.

A trigger permits a proposal, not an automatic split.

## Planned future code layout

The following paths are plans only and do not exist in this phase:

```text
src/reduced_nc_dis/
  mod.rs
  kinematics.rs
  electroweak.rs
  structure_functions.rs
  differential_rate.rs
  acceptance.rs
  normalization.rs
  sampler.rs
  detector.rs
  provenance.rs
  errors.rs

analysis/reduced_nc_dis/
  calibration/
  coverage/
  diagnostics/
  paper/

tests/reduced_nc_dis/
  formula_closure/
  normalization/
  sampling/
  detector/
  integration/
```

Files or directories appear only after the relevant phase is separately
authorized. This roadmap selects no preferred implementation architecture.
