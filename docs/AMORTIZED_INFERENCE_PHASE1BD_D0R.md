# Phase 1B-D0R projected-baseline revalidation

## Decision

```text
REVISED_STAGE0_DECISION = PASS
D1_AUTHORIZATION_CANDIDATE = true
D1_AUTHORIZED = false
```

This is a revised input-boundary validation under accepted ADR-004. It does
not overturn the historical v1 `FAIL`; it tests a separately versioned
baseline and admissibility contract. It does not implement D1, evolution,
LHAPDF artifact export, PYTHIA coupling, events, datasets, or inference.

## Provenance

- ADR merge: `a8aedec454576740ad9e11aeb7e977cc853bba17`
- implementation commit: `94e46aca6dd870c6de21f9426f165ac1880429dd`
- study ID: `phase1bd_d0r_projected_boundary_v2_20260728`
- clean study: `git_dirty=false`
- runtime: 102.673619115 seconds
- command:

```bash
cargo run --release -- validate-continuous-pdf-family \
  --family-version v2 \
  --full-study \
  --study-id phase1bd_d0r_projected_boundary_v2_20260728 \
  --output outputs/phase1bd_d0r_projected_boundary_v2_20260728
```

The ignored output contains the full point, topology, fidelity, sum-rule,
guard-shell, and manifest reports. No full scan is committed.

## Authoritative source and projected baseline

The raw source is CT18NLO member 0, DataVersion 1, LHAPDF 6.5.6, at
`Q0=1.295 GeV` over declared support `[1e-9,1]`. The C++ bridge reads the
installed GridPDF interpolator (`logcubic`) and extrapolator (`continuation`).
PartonSBI's caller policy remains `strict_no_extrapolation`.

The new object is explicitly:

```text
ct18nlo_member0_sumrule_projected_boundary_v2
```

It is not unmodified CT18NLO. Independent construction reproduced:

| constant | value |
| --- | ---: |
| `A_u0` | `1.000002115126194` |
| `A_d0` | `1.0000202605996376` |
| `A_g0` | `0.9999935202034873` |

Raw moments were `1.9999957697565593`, `0.999979739810846`, and
`0.9999991913056491` for up valence, down valence, and total momentum.
Projected values were `1.9999999999999998`, `1.0`, and
`0.9999999999999999`.

## Family and center

The family is `ct18nlo_two_parameter_boundary_v2` with the unchanged
`(delta_v,lambda_sea)` definition and unchanged hard box. At the center the
relative family normalizations were unity to about `1.4e-15`. Every flavor
passed the existing `1e-6` relative / `1e-10` absolute pointwise comparison
against the projected baseline.

Raw CT18NLO remains mandatory fidelity evidence. Maximum relative shifts were:

| flavor | maximum relative shift | old-threshold failures |
| --- | ---: | ---: |
| gluon | `6.479796512898374e-6` | 322 |
| up | `2.115127689774372e-6` | 156 |
| down | `2.0260610853927383e-5` | 185 |

These expected projection corrections are not center failures.

## Sign topology and negative momentum

Topology discovery uses authoritative knots, 64 logarithmic subdivisions per
knot interval, deterministic bisection (`1e-14` x tolerance, 128-iteration
limit), and an independent 128-subdivision sensitivity pass. All discovered
components were stable under refinement.

The projected gluon first crosses at `x=0.9935531299173881` and reaches a
minimum number density `-1.88671377771894e-9` at
`x=0.9954963079520738`. The complete machine report also records the tiny
endpoint interpolation components of the light sea and a second gluon sign
change near the endpoint; these inherited components are not omitted.

The gluon integrated negative momentum was
`6.187895394497226e-12`, fraction `1.582215207073383e-11`. Independent
integration differed by `1.1738412151519472e-18`, below
`max(1e-17,1e-6 N_f)`. Inherited antiquark/strange components were likewise
integrated. Pure positive rescalings preserve their connected intervals and
negative-momentum fractions algebraically. No value was clipped, replaced, or
discarded.

## Complete scan

Exactly 441 unique points covered the unchanged closed `21 x 21` box. Exactly
80 unique points covered the unchanged 5%-expanded perimeter and remained
diagnostic, not prior points. All 441 pilot points and all 80 guard points
passed the revised contract; no point was invalid or inconclusive.

Pilot normalization ranges were:

| normalization | minimum | maximum |
| --- | ---: | ---: |
| `A_u` | `0.8746584240579475` | `1.0195559461213208` |
| `A_d` | `0.8420811985803742` | `1.0561303372726496` |
| `S` | `0.7788007830714049` | `1.2840254166877414` |
| `A_g` | `0.6158543451441613` | `1.3932774087070732` |

Maximum absolute residuals were `2.220446049250313e-16` and
`1.1102230246251565e-16` for constructed valence, zero for constructed
momentum, `2.7977620220553945e-14`, `1.0769163338864018e-14`, and
`7.216449660063518e-15` independently. Maximum refinement change was
`3.175237850427948e-14`.

V1 and v2 numerical family values agreed exactly in the reported binary64
evaluations over all 441 points and the complete deterministic x grid. All
441 v2 identities were unique and repeated construction was byte-identical.
V1 and v2 identities remain distinct.

## Limitations and gate

This PASS validates only a two-parameter input-scale boundary representation.
Baseline-relative NLO input admissibility is not positivity of evolved
structure functions or cross sections. Inclusive neutral-current e-p data do
not provide unrestricted flavor separation.

D1 is still unauthorized. The result creates only a candidate for a separate
review decision. The single next step is scientific review of this D0R PR and,
if accepted, an explicit roadmap authorization decision for D1.
