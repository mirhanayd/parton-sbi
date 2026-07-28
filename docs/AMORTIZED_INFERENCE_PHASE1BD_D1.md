# Phase 1B-D1 APFEL++ evolution and LHAPDF artifact validation

## Decision

```text
STAGE1_DECISION = FAIL
D2_AUTHORIZATION_CANDIDATE = false
D2_AUTHORIZED = false
```

This is a completed negative Stage 1 result. It does not invalidate the
revised-D0 boundary-family PASS. It shows that the implemented APFEL++ evolution
and one-member LHAPDF transport do not satisfy the predeclared Stage 1
round-trip and evolved-sum-rule gates.

## Provenance

- D0R merge: `12755acbbf0791f97be95fe72177bab4a126c58b`
- clean implementation commit:
  `1a7181ad1582029aa93cf743807c24e18a147704`
- study ID: `phase1bd_d1_apfel_lhapdf_artifact_v1_20260728`
- study command:

  ```bash
  cargo run --release -- validate-pdf-artifact \
    --study \
    --study-id phase1bd_d1_apfel_lhapdf_artifact_v1_20260728 \
    --output outputs/phase1bd_d1_apfel_lhapdf_artifact_v1_20260728
  ```

- recorded repository state: `git_dirty=false`
- clean-study runtime: `170.603836004 s`
- generated grids and full point reports remained under ignored `.external/`
  and `outputs/` paths.

## Implemented contract

The only accepted boundary source is
`ct18nlo_member0_sumrule_projected_boundary_v2` with family
`ct18nlo_two_parameter_boundary_v2`. The historical v1 family is rejected by
the D1 constructor.

The native bridge uses APFEL++ 4.8.0 at NLO with the same metadata-derived
`AlphaQCD` object for evolution and the artifact's `AlphaS_Qs` and
`AlphaS_Vals`. Input `Q` is in GeV; LHAPDF `xfxQ2` receives `Q²` exactly once.
The CT18NLO five-flavor ceiling is explicit. Charm and bottom thresholds are
active at 1.3 and 4.75 GeV. The authoritative top metadata is retained, but top
evolution is placed above the artifact support because the artifact contains
only the declared CT18NLO five-flavor layout.

The artifact grid contains 161 x knots and 39 Q knots. It retains all
authoritative supported CT18NLO knots, inserts the exact declared x boundaries,
and adds absent charm/top threshold knots. Each artifact is a deterministic
one-member `lhagrid1` set with:

- `Interpolator: logcubic`;
- `Extrapolator: error`;
- exact binary64-derived parameter identity upstream;
- a full SHA-256 content address;
- checksums for every payload file;
- same-filesystem temporary construction and atomic publication;
- per-hash locking, validation on load, and corruption quarantine;
- repository-local ignored cache storage.

No artifact is coupled to PYTHIA in this phase.

## Nine-anchor study

The center, four axis endpoints, and four corners were evaluated. All nine
artifacts were finite, loadable by LHAPDF 6.5.6, manifest-reproducible, and
passed the compact photon-only non-negativity diagnostic over the declared DIS
study region.

The C++ boundary callback agreed with the Rust D0R family. Across all anchors,
the maximum relative discrepancy was `5.598119172309163e-15` and the maximum
absolute discrepancy was `1.1102230246251565e-14`.

At the exact artifact Q knots, the independently loaded LHAPDF alpha_s values
agreed with the APFEL `AlphaQCD` values exactly to the recorded binary64
precision (`maximum relative error = 0`).

## Failed gates

### Evolved sum rules

The maximum Q0 residual was `1.5824809165287945e-6`, within the fixed `1e-5`
gate. Residuals grew with scale and reached
`4.2761916359967955e-4` at `Q=100000 GeV`, so the evolved sum-rule gate failed.
The five-flavor correction was made before the final clean study; no top
momentum is silently omitted from the final artifact.

### LHAPDF round trip

Exact tabulated knots and alpha_s knots transport deterministically, but the
predeclared off-knot validation detected 511,900 flavor-point values outside
the combined relative/absolute tolerance across the nine anchors. The largest
absolute discrepancy was `15.714798898214212`. The failure is retained; the
interpolator, knot layout, and tolerances were not changed after observation.

### Raw CT18NLO evolved fidelity

The center comparison is diagnostic because the boundary is the named
sum-rule-projected baseline rather than unmodified CT18NLO. Nevertheless, the
fixed evolved-fidelity check found 8,403 values outside the `2e-3` relative
criterion and a maximum absolute discrepancy of `22.925097585983167`.

## Reproducibility and cache tests

Focused native tests cover version rejection, artifact loading, strict support,
corruption quarantine/regeneration, and concurrent same-hash publication.
Artifact payloads are never overwritten. Extrapolation requests fail through
the LHAPDF error extrapolator and are not repaired.

## Limitations

- The physical diagnostic is photon-only and parton-level; it is not an
  electroweak, detector, or generator validation.
- The raw-center evolution comparison combines a projected boundary with an
  APFEL++ evolution implementation, whereas CT18NLO was produced with a
  different evolution implementation.
- A deterministic artifact is not generator compatibility. No PYTHIA
  initialization, event, sampling, dataset, or neural-inference path was added.
- The full generated study and 1.5 MB-per-anchor grids are intentionally
  ignored and untracked; only this reviewed summary and compact decision JSON
  are source controlled.

## Next decision

D2 is not authorized. The next scientific step is a focused Stage 1 revision
decision addressing APFEL high-Q sum-rule preservation and LHAPDF off-knot
transport. That decision must predeclare any revised grid/interpolation
contract before implementation or rerunning acceptance.
