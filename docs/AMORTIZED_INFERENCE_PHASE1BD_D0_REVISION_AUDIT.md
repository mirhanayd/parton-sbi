# Phase 1B-D0 revision audit

## Status

**DECISION PROPOSED — REVISED D0 IMPLEMENTATION ONLY. D1 IS NOT AUTHORIZED.**

The original Phase 1B-D0 result remains:

```text
STAGE0_DECISION = FAIL
D1_AUTHORIZED = false
```

This audit diagnoses that negative result and proposes a versioned baseline
and admissibility contract for scientific review. It does not implement the
revision, modify the D0 family, rerun the 441-point study, evolve PDFs, create
an LHAPDF artifact, couple to PYTHIA, generate events, create datasets, or
implement inference.

## Repository and GitHub state

- D0 implementation PR: #23, squash-merged into `main`.
- D0 merge commit: `6a69943e391d26020256f1b9455eac46c1f65061`.
- D0 roadmap issue: #8, completed with gate decision `FAIL`.
- D0-revision ADR issue: #24, planning only.
- Revised D0-validation issue: #25, blocked by #24.
- D1 issue: #9, blocked by #25 and not authorized.

A completed negative result is not unfinished work.

## Diagnostic provenance

The diagnostics ran from clean commit:

```text
6a69943e391d26020256f1b9455eac46c1f65061
```

with `git status --short` empty. The temporary diagnostic source, executable,
LHAPDF source checkout, and numerical outputs were kept under ignored
`outputs/` paths. No exploratory output is committed.

Primary sources inspected:

- installed LHAPDF 6.5.6 public headers;
- official LHAPDF `lhapdf-6.5.6` source tag at
  `92239ac82134be698805c1002b4615e5167c6fa3`;
- installed CT18NLO `DataVersion: 1` `.info` and member-0 grid;
- installed APFEL++ 4.8.0 public interfaces;
- the repository's APFEL++ callback and D0 implementation.

The final temporary C++ diagnostic source SHA-256 was:

```text
50f48f7617e1175b7638a13f0194616d3d8428fbea6d95ae5e6d8934fe435701
```

It was compiled and run in WSL with:

```bash
source scripts/pythia_env.sh
g++ -std=c++20 -O2 -Wall -Wextra -Werror \
  -I/home/mrxn/.local/lhapdf-6.5.6/include \
  outputs/d0r_diagnostic.cpp \
  -L/home/mrxn/.local/lhapdf-6.5.6/lib \
  -Wl,-rpath,/home/mrxn/.local/lhapdf-6.5.6/lib \
  -lLHAPDF \
  -o outputs/d0r_diagnostic
outputs/d0r_diagnostic > outputs/d0r_diagnostic.txt
```

The unchanged D0 CLI independently reproduced the center:

```bash
cargo run --release -- validate-continuous-pdf-family \
  --delta-v 0 \
  --lambda-sea 0 \
  --output outputs/d0r_center_cli
```

## Endpoint diagnostic

### Raw knots

At `Q0=1.295 GeV`, all 161 raw gluon knots are nonnegative:

| Quantity | Result |
| --- | ---: |
| Last positive knot `x` | `0.99262` |
| Last positive knot `xf_g` | `2.6821982100000002e-9` |
| First zero knot `x` | `1` |
| First zero knot `xf_g` | `0` |
| Negative raw knots | `0` |
| Raw-knot/API maximum absolute difference | `4.5494933690416522e-24` |

### Off-knot interpolation

The first off-knot zero crossing is `x=0.9935531299173892`. The gluon is
negative between that point and `x=1`.

| Quantity | Result |
| --- | ---: |
| Minimum interpolated `xf_g` | `-1.8784951425865714e-9` |
| Location | `0.9955233026506225` |
| Minimum interpolated number density | `-1.8869448687227857e-9` |
| Location | `0.9955207116819784` |
| Integrated negative momentum | `6.187935491060024e-12` |
| Fraction of gluon momentum | `1.5822152070733786e-11` |

Direct source inspection and the stored cubic coefficients prove that this is
an unconstrained `logcubic` overshoot between nonnegative knots. It exists at
the raw center before PartonSBI normalization. Every pilot `A_g` is positive,
so the family retains the same sign interval and only rescales its magnitude.

The installed default extrapolator is `continuation`, but all diagnostic
evaluations were inside declared support. Revised D0 must preserve the
explicit no-extrapolation caller contract.

## Central reconstruction diagnostic

### Raw numerical moments

| Quantity | GK15 | GL64 refined | Difference scale |
| --- | ---: | ---: | ---: |
| `integral u_v dx` | `1.9999957697565598` | `1.9999957697565556` | `4.2e-15` |
| `integral d_v dx` | `0.9999797398108460` | `0.9999797398108469` | `8.9e-16` |
| total momentum | `0.9999991913056495` | `0.9999991913056507` | `1.2e-15` |
| gluon momentum | `0.3910931625101645` | `0.3910931625101662` | `1.7e-15` |

GL64 subdivision refinements through 8 subdivisions remain stable at the same
scale. The original normalizations are reproduced to about `1e-13`:

```text
A_u = 1.0000021151261937
A_d = 1.0000202605996376
A_g = 0.9999935202034876
```

### Cause classification

| Candidate cause | Decision | Evidence |
| --- | --- | --- |
| Quadrature | Excluded | GK15 and independent GL64 agree at `~1e-14`. |
| Flavor convention | Excluded | Explicit quark/antiquark IDs give total momentum near one with no extra sea factor. |
| Finite support | Partial | The omitted raw-knot sliver supplies `5.433040778806293e-7` up valence but negligible momentum and no represented down valence. |
| Endpoint negative region | Negligible for moments | Negative gluon momentum is `6.19e-12`. |
| Public tabulation/interpolation | Dominant reproducible source | The installed finite-precision grid plus logcubic interpolation yields the residuals. |

The public artifact cannot separate rounding of the tabulated CT18NLO values
from interpolation effects without an unavailable pre-tabulation fit. The
public LHAPDF representation is therefore the authoritative raw numerical
object.

### Projection effect

The exact projection changes integrated momentum by:

| Component | Shift |
| --- | ---: |
| Up valence | `+6.743735139310437e-7` |
| Down valence | `+2.668524947393334e-6` |
| Gluon | `-2.534204110441108e-6` |
| Net | `+8.086943509288957e-7` |

The largest pointwise relative shifts remain:

| Flavor | Maximum relative shift | Points outside old tolerance |
| --- | ---: | ---: |
| Gluon | `6.479796512590086e-6` | 322 |
| Up | `2.115127689774372e-6` | 156 |
| Down | `2.026061085392738e-5` | 185 |

These are the expected raw-to-projected differences. They are not changed or
reclassified under the original D0 result.

## Contract comparison

| Option | Exact sum rules | Center identity | Endpoint/admissibility | APFEL/artifact/PYTHIA consistency | Interpretation and cost |
| --- | --- | --- | --- | --- | --- |
| A. Raw LHAPDF | No; inherits measured residuals | Exact to raw CT18 | Inherits logcubic sign | Simple raw consumption, but manifests inherit residuals | Lowest cost; abandons exact-sum objective |
| B. Projected baseline | Yes | Exact to a named projected object | Inherits and records baseline sign | One explicit callback/artifact identity; raw CT is a fidelity reference | Low implementation cost; clearest provenance |
| C. Sign-preserving endpoint | Can be projected | Exact to a third representation | Removes endpoint overshoot | Requires interpolation/artifact policy changes to avoid reintroduction | Moderate cost; scientifically unnecessary at measured scale |
| D. New `Q0`/set/order | Depends on new family | New center | New threshold/support behavior | Requires requalifying alpha-s, thresholds, APFEL and PYTHIA | High cost; changes scientific question |
| E. Analytic basis | Can enforce rules | No CT center identity | Endpoint chosen by new assumptions | Requires a wholly new evolution/artifact reference | Highest modeling cost and unconstrained choices |

Option B is selected for review. Applying the existing normalized deformation
to the projected baseline is algebraically equivalent to the v1 D0 family
values, so this decision does not opportunistically reshape the pilot box.

## Selected baseline contract

Proposed versions:

```text
baseline_version = ct18nlo_member0_sumrule_projected_boundary_v2
family_version   = ct18nlo_two_parameter_boundary_v2
```

The projected object is constructed from raw CT18NLO member 0 at the exact
metadata boundary, using the unchanged support, flavor convention, and
integration policy. It stores the three projection constants and complete raw
provenance. `theta=(0,0)` reproduces this object exactly. Raw CT18NLO remains a
mandatory comparison with the measured nonzero deviations above.

At later stages, APFEL++ and any generated artifact must identify the projected
object. Pythia must consume that same artifact. No consumer may describe it as
unmodified CT18NLO.

## Selected admissibility contract

Strict pointwise nonnegativity is replaced only for inherited,
factorization-scheme input behavior. Revised D0 must:

- inventory baseline sign intervals from knots and deterministic off-knot root
  searches;
- forbid deformation-created sign intervals;
- permit an inherited interval only under an explicit positive multiplicative
  map;
- record per-flavor integrated negative momentum and its signed-momentum
  fraction;
- require the fraction and interval to be invariant for purely scaled
  flavors, with independent integration agreement;
- retain finite-value, support, heavy-boundary, sum-rule, normalization,
  quadrature, and identity gates;
- retain the no-clipping and no-extrapolation rules.

This input contract is paired with a later physical-observable gate. A revised
D0 pass would authorize only D1 implementation. D1 would still have to show
finite and admissible evolved structure functions and neutral-current cross
sections, plus direct-APFEL/artifact agreement, before D2 could be considered.

## Revised Stage 0 proposal

The revised validation must rerun the unchanged 441-point box and 80-point
guard shell. It may pass only if:

1. authoritative raw metadata and projected-baseline provenance match;
2. center identity passes against the projected baseline;
3. raw CT18 deviations reproduce the reviewed correction diagnostics;
4. original sum-rule and quadrature tolerances pass unchanged;
5. all normalizations remain finite and positive;
6. no new negative component or sign crossing is introduced;
7. inherited negative momentum obeys the exact scaling contract;
8. heavy flavors remain zero at `Q0`;
9. identities are deterministic and versioned;
10. outside-box inputs remain typed errors.

The original pilot bounds are not changed. The original v1 decision remains
`FAIL`; the revised contract requires a new study ID and decision artifact.

## Decision and authorization

```text
D0_REVISION_IMPLEMENTATION_AUTHORIZED = true
D0_REVISION_DECISION = PROPOSED_FOR_REVIEW
D1_AUTHORIZED = false
```

The authorization becomes effective only if ADR-004 is accepted. It permits
only implementation and revalidation of the revised D0 boundary contract.

## Validation

The unchanged baseline before documentation edits passed:

| Command | Result |
| --- | --- |
| `cargo fmt --all -- --check` | pass |
| `cargo check --workspace` | pass |
| `cargo test --workspace` | 165 passed, 9 ignored, 0 failed |
| `cargo clippy --workspace --all-targets -- -D warnings` | pass |
| `analysis/venv/bin/python -m pytest analysis/tests` | 32 passed |
| `ctest --test-dir physics-engine/build --output-on-failure` | 1 passed |
| `git diff --check` | pass |

Final validation is recorded in the pull request.

## Limitations

- The audit diagnoses the installed CT18NLO/LHAPDF representation only.
- It does not demonstrate APFEL evolution or artifact round-tripping.
- Input-PDF admissibility is not a substitute for physical-observable
  validation.
- The family remains two-dimensional and does not provide unrestricted flavor
  separation from inclusive neutral-current electron-proton data.
- No event, rate, detector, dataset, or inference claim follows from this ADR.

## Next step

Scientifically review ADR-004. If accepted, authorize issue #25 to implement
and rerun revised D0 only. D1 remains blocked until that new study passes.
