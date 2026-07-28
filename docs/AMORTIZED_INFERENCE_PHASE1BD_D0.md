# Phase 1B-D0: continuous PDF boundary-family validation

## Status

**COMPLETE — FAIL. D1 IS NOT AUTHORIZED.**

Stage 0 implemented and evaluated only the input-scale mathematical family
approved by ADR-001. The deterministic pilot-box study found two independent
fixed-gate failures: all 441 hard-domain points have a negative gluon density
near `x -> 1`, and the exactly normalized center does not reconstruct
CT18NLO member 0 within the declared pointwise tolerance. No density,
normalization, tolerance, or pilot bound was repaired after observing the
result.

No APFEL++ evolution, LHAPDF artifact writer, generated PDF grid, PYTHIA
coupling, event generation, sampling experiment, dataset, or neural model was
implemented.

## Clean study provenance

Study ID:

```text
phase1bd_d0_ct18nlo_v1_pilot_box_20260728
```

Implementation commit:

```text
96531d02548aa0b4a105c03edac25ac485c061a1
```

The run recorded `git_dirty=false`, PartonSBI 0.1.0, Rust
`1.97.1`, Linux x86-64, LHAPDF 6.5.6, and a runtime of
163.656684039 seconds. The exact command was:

```bash
cargo run --release -- validate-continuous-pdf-family \
  --full-study \
  --study-id phase1bd_d0_ct18nlo_v1_pilot_box_20260728 \
  --output outputs/phase1bd_d0_ct18nlo_v1_pilot_box_20260728
```

The ignored output directory contains the study manifest, metadata,
point-level, sum-rule, positivity, central-reconstruction, guard-shell, and
decision JSON reports. Their SHA-256 hashes are recorded in the ignored study
manifest. Raw scan outputs are not committed. The compact reviewed decision is
`phase1bd_d0_decision.json`.

## Authoritative baseline metadata

The implementation obtains metadata and input-grid knots from the installed
LHAPDF `PDFInfo`, `PDF`, and public `GridPDF::xKnots()` interfaces. Generic
family code contains no hard-coded CT18 support or scale values.

| Quantity | Authoritative value |
| --- | ---: |
| Set/member | CT18NLO / 0 |
| Data version | 1 |
| QCD order | 1 (NLO) |
| Flavor scheme | variable |
| Supported flavors | `-5..-1`, `1..5`, `21` |
| `x` support | `[1e-9, 1]` |
| `Q` support | `[1.295, 100000]` GeV |
| `Q0` | 1.295 GeV |
| `alpha_s(MZ)` | 0.118 |
| Charm mass / threshold | 1.3 / 1.3 GeV |
| Bottom mass / threshold | 4.75 / 4.75 GeV |
| Input `x` knots | 161 |

`Q0` equals the authoritative `qMin` exactly. Q is stored in GeV and is
squared exactly once for managed-lhapdf's `xfxQ2` API. The lowest raw grid
knot, `9.26136e-10`, lies below the declared `XMin=1e-9`. It remains recorded
in the validation grid, where the explicitly compact family is zero; it is
never queried through LHAPDF extrapolation. Integration and central
reconstruction use the declared support.

The baseline charm, anticharm, bottom, and antibottom `xf` values were zero at
every in-support input knot within the unchanged `1e-10` absolute tolerance.
They were not clipped.

## Implemented family

The hard pilot domain is:

```text
theta = (delta_v, lambda_sea)
delta_v in [-0.20, 0.20]
lambda_sea in [-0.25, 0.25]
```

Values outside this box return a typed error. Signed zero is canonicalized to
positive zero; NaN and infinity are rejected.

At `Q0`, number densities are reconstructed as `f=xf/x`. With `x_p=0.1`,
the valence distributions use the common tilt
`(x/x_p)^delta_v`, separate positive normalizations impose
`integral(u_v)=2` and `integral(d_v)=1`, and the light sea is scaled by
`exp(lambda_sea)`. The gluon retains its baseline shape and a positive
normalization imposes the momentum rule.

Momentum is integrated once over each separately represented flavor:

```text
x * [g + u + ubar + d + dbar + s + sbar + c + cbar + b + bbar]
```

Since `u=u_v+ubar` and `d=d_v+dbar`, the sum contains the intended two sea
copies. No additional factor of two is applied.

## Integration and identity

Primary construction uses adaptive 15-point Gauss-Kronrod integration in
`z=log(x)`, split at every in-support input knot and at `x_p=0.1`, with
absolute and relative requests of `1e-10` and a finite subdivision limit.

The independent verifier uses generated 64-point Gauss-Legendre nodes on
two- and four-way deterministic refinements of every interval. It does not
reuse adaptive samples or accumulated values.

Parameter identities serialize a lexicographically ordered UTF-8 JSON map.
Every floating-point field uses its exact binary64 bits as 16 lowercase
hexadecimal digits. Full SHA-256 identifiers were unique for all 441 pilot
points and byte-identical on repeated construction.

## Pilot and guard-shell scan

The closed `21 x 21` scan contained exactly 441 unique hard-domain points.
The diagnostic guard shell was the unique perimeter of a closed `21 x 21`
grid with both ranges expanded by 5%:

```text
delta_v in [-0.21, 0.21]
lambda_sea in [-0.2625, 0.2625]
```

It contained exactly 80 unique points. These are conditioning diagnostics,
not prior points, and did not alter or shrink the pilot box.

All 441 pilot constructions and all 80 guard constructions produced finite,
strictly positive normalization constants. There were zero construction
errors and zero inconclusive points.

| Normalization | Pilot minimum | Pilot maximum |
| --- | ---: | ---: |
| `A_u` | 0.8746602740708905 | 1.0195581026108094 |
| `A_d` | 0.8420982596504005 | 1.0561517351065781 |
| `S` | 0.7788007830714049 | 1.2840254166877414 |
| `A_g` | 0.6158503545333242 | 1.3932683805529793 |

## Sum rules and quadrature

Every point passed the construction, independent, and refinement gates:

| Maximum absolute quantity over 441 points | Value | Gate |
| --- | ---: | ---: |
| Construction `u_v` residual | `2.220446049250313e-16` | `1e-8` |
| Construction `d_v` residual | `1.1102230246251565e-16` | `1e-8` |
| Construction momentum residual | `0` | `1e-8` |
| Independent `u_v` residual | `3.7969627442180354e-14` | `1e-6` |
| Independent `d_v` residual | `8.43769498715119e-15` | `1e-6` |
| Independent momentum residual | `7.771561172376096e-15` | `1e-6` |
| Quadrature-refinement change | `3.774758283725532e-14` | `1e-8` |

The Stage 0 failure is therefore not a normalization or quadrature failure.

## Positivity

The deterministic validation grid includes all 161 authoritative knots,
logarithmic interval midpoints, the declared lower support, refined points
around `x_p`, and points approaching one.

Every pilot point fails the unchanged negativity criterion. The global pilot
minimum is:

```text
density = -2.357711254447399e-9
flavor = 21 (gluon)
x = 0.9963031667118196
theta = (-0.20, -0.25)
```

The 80 guard points also fail positivity. Their minimum is
`-2.391628105922302e-9` for the gluon at the same `x`, at
`theta=(-0.21,-0.2625)`. Negative values were recorded and never set to zero.

## Central reconstruction

At `theta=(0,0)`, exact finite-support normalization gives:

```text
A_u = 1.000002115126
A_d = 1.000020260600
S   = 1
A_g = 0.9999935202035
```

Those corrections are scientifically small but exceed the predeclared
pointwise reconstruction gate. The nonzero failures are:

| Flavor | Maximum relative error | Points outside tolerance |
| --- | ---: | ---: |
| gluon | `6.479796512590086e-6` | 322 |
| up | `2.1151276897743718e-6` | 156 |
| down | `2.0260610853927383e-5` | 185 |

Antiquark, strange, and zero-boundary heavy flavors reconstruct within their
applicable tolerance. The failure was not hidden by an average and the center
was not special-cased.

## Decision and limitations

The fixed decision is:

```text
STAGE0_DECISION = FAIL
D1_AUTHORIZED = false
PILOT_BOX_ACCEPTED = false
```

This is a completed negative scientific result. It does not authorize
shrinking the box, changing tolerances, clipping endpoint interpolation, or
starting APFEL evolution.

The family remains a two-direction deformation of one named baseline, not a
general PDF fit. Inclusive neutral-current electron-proton data cannot support
unrestricted full-flavor separation. Stage 0 tests the input boundary only;
it makes no claim about evolution, interpolation artifacts, PYTHIA support,
event weights, direct generation, datasets, or inference.

## Validation

Before the clean study, the implementation passed:

| Command | Result |
| --- | --- |
| `cargo test --workspace` | 165 passed, 9 ignored, 0 failed |
| `cargo test --test continuous_pdf_family -- --nocapture` | 2 passed, 2 ignored |
| `cargo test --test continuous_pdf_family -- --ignored --nocapture` | 2 passed |
| `cargo clippy --workspace --all-targets -- -D warnings` | pass |
| `git diff --check` | pass |

The final repository-wide validation results are recorded in the pull request
and completion handoff.

## Next step

Scientifically review this negative Stage 0 result and write a new ADR deciding
whether the baseline interpolation/finite-support reconstruction contract or
the proposed family should be revised. Do not begin D1 under the failed gate.
