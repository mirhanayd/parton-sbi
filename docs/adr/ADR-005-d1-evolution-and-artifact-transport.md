# ADR-005: D1 evolution and LHAPDF transport revision

Status: proposed for scientific review

Date: 2026-07-28

## Context

Phase 1B-D1 produced deterministic APFEL++ 4.8.0 evolutions and immutable,
one-member LHAPDF 6.5.6 artifacts for all nine mandatory anchors. The study
`phase1bd_d1_apfel_lhapdf_artifact_v1_20260728` completed with:

```text
STAGE1_DECISION = FAIL
D2_AUTHORIZATION_CANDIDATE = false
D2_AUTHORIZED = false
```

The boundary callback, exact alpha-s knot transport, finite-value checks,
strict support, cache integrity, concurrency, and deterministic bytes passed.
The fixed off-knot transport, evolved-sum-rule, and raw-CT18 pointwise gates
failed. PR #28 merged that negative result without changing its tolerances,
grid, or decision.

This ADR separates three questions that the original aggregate decision could
not answer:

1. whether APFEL evolution conserves moments on its computational domain;
2. whether a finite LHAPDF grid transports the direct APFEL representation;
3. whether independent APFEL evolution should reproduce the distributed
   CT18NLO grid pointwise.

The accepted D0R boundary family is unchanged.

## Primary-source contract

The audit used:

- installed APFEL++ 4.8.0 headers, source, and examples;
- installed LHAPDF 6.5.6 headers;
- official LHAPDF tag `lhapdf-6.5.6`, commit
  `92239ac82134be698805c1002b4615e5167c6fa3`;
- LHAPDF's `DESIGN`, `GridPDF.cc`, `KnotArray`, and
  `LogBicubicInterpolator.cc`;
- installed CT18NLO member 0, `DataVersion: 1`; and
- the committed D1 writer and APFEL bridge.

LHAPDF's format documentation specifies unsquared Q values in files,
x-outer/Q-inner data rows, increasing PDG flavor order, and repeated Q knots
between subgrids. `GridPDF` squares file Q once when loading. Public `xfxQ`
accepts Q and performs the corresponding conversion once.

## Serialization audit

The D1 writer follows the official lhagrid1 layout:

- x is the outer data loop;
- Q is the inner data loop;
- flavors are `[-5,-4,-3,-2,-1,1,2,3,4,5,21]`;
- file knots are unsquared Q;
- the evaluator calls `xfxQ`, not `xfxQ2`;
- values use 17-digit scientific notation.

Across all nine anchors, 69,069 exact flavor/x/Q knot comparisons per anchor
had zero failures under the unchanged D1 rule. At the center, the maximum
absolute difference was `3.1763735522036263e-22`, for flavor 2 at
`x=1`, `Q=2.50067 GeV`. Large relative values at exact zeros are numerically
meaningless and pass the declared absolute branch.

An independent implementation of the LHAPDF 6.5.6 log-bicubic formula agreed
with the loaded artifact with zero D1-tolerance failures at every midpoint.
Across anchors its maximum absolute difference was
`1.0913936421275139e-11`; center p95 and p99 absolute differences were
`8.881784197001252e-16` and `2.842170943040401e-14`.

Decision 1: **serialization is correct**. The off-knot failure is not an
x/Q transposition, flavor permutation, Q-versus-Q2 error, or text-precision
loss.

## CT18NLO and artifact subgrids

The installed CT18NLO member contains one Q subgrid:

```text
x knots: 161
Q knots: 37
subgrid separators: one opening and one final separator
duplicated Q knots: none
```

Its first Q knots are `1.295`, `1.29875`, and `1.46461 GeV`; the charm
threshold `1.3 GeV` is bracketed but not an exact file knot. Bottom is an exact
`4.75 GeV` knot. Top `172 GeV` is bracketed by `148.517` and `214.38 GeV`.
The D1 artifact writes one 161-by-39 block after inserting exact charm and top
threshold knots.

The LHAPDF design nevertheless identifies Q subgrids as the mechanism for
preventing cubic derivatives from crossing threshold discontinuities. A
diagnostic three-segment representation using the same knots changed only 439
of 271,887 center failures; failures remained global. Threshold separation is
therefore not a sufficient repair, but it is required for a new evolved
artifact whose threshold behavior is not inherited from the distributed CT18
file.

Decision 2: **revised artifacts require Q subgrids separated at charm and
bottom thresholds**. The five-flavor ceiling remains unchanged. This decision
is based on interpolation semantics, not on an aggregate-error rescue.

## Off-knot localization and grid experiments

At the center, 56,793 of 271,887 midpoint values failed. The largest absolute
difference was `13.676177930319682`, for the gluon at
`x=1.0635741629054353e-9`, `Q=71852.27901743959 GeV`.

Failures were not threshold-local:

| Region | Center failures |
| --- | ---: |
| threshold neighborhood | 4,969 |
| low Q away from thresholds | 18,975 |
| mid Q | 23,287 |
| high Q | 9,562 |
| low x | 11,414 |
| DIS x range | 30,845 |
| endpoint x | 14,534 |

Every flavor failed; the gluon had the largest center count (7,195). Only
1,122 center failures used the near-zero absolute branch.

The following deterministic center diagnostics retained the original D1
tolerances. Sizes are numerical payload estimates; times include direct
evolution and midpoint evaluation on the audit host.

| Representation | Knots | Payload | Time | Failure fraction | p95 abs. | p99 abs. | Max abs. |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A: one block | 161 x 39 | 1.73 MB | 20.4 s | 20.89% | 1.54e-4 | 1.30e-2 | 13.68 |
| B: threshold segments | 161 x 39 | 1.73 MB | 20.7 s | 20.73% | 1.93e-4 | 1.25e-2 | 13.68 |
| C: log-Q midpoints | 161 x 77 | 3.41 MB | 40.5 s | 17.40% | 2.43e-4 | 4.11e-3 | 5.04 |
| D: log-x midpoints | 321 x 39 | 3.44 MB | 25.9 s | 17.47% | 9.47e-5 | 1.12e-2 | 12.46 |
| E: both plus segments | 321 x 77 | 6.80 MB | 53.5 s | 13.35% | 2.24e-4 | 3.14e-3 | 4.01 |

Uniform one-level refinement helps but does not approach closure. The error is
smooth-region representation error as well as threshold behavior.

Decision 3: **deterministic error-driven x/Q refinement is required**.
Uniform density alone is rejected as needlessly expensive and insufficient.

Decision 4: refinement starts from authoritative supported CT18 knots plus
exact support and threshold knots. At every iteration it evaluates a fixed
tensor of logarithmic midpoint and one-third/two-third probes for all eleven
flavors and all nine anchors. Every interval implicated by a failure under the
unchanged `1e-5` relative / `1e-9` absolute rule is bisected; the union is
applied globally in lexicographic order. At most four iterations, 1,025 x
knots, 257 Q knots, 256 MiB per member, and ten minutes per anchor are allowed.
Exceeding any bound is a Stage 1 FAIL, not permission to loosen tolerances.

This is a predeclared algorithm with a complexity ceiling, not manual knot
tuning after observing individual points.

## APFEL moments and finite-support accounting

The original APFEL `Distribution::Integrate` and an independent composite
GL64-in-log-x integral agree on the qualitative failure. At the center on
`[1e-9,1]`, maximum residuals were `5.4652029149782066e-5` and
`5.4644316958007977e-5`. At `Q=100000 GeV`:

```text
u_v = 1.9999605170783317
d_v = 0.9999810126831417
quark momentum = 0.5103337947465085
gluon momentum = 0.4896115532243417
total momentum = 0.9999453479708502
```

The center first exceeds `1e-5` at `Q=23.0855 GeV`. The delta-min anchor
exhibits the original worst native residual, `4.2761916349154383e-4`, driven
primarily by truncated u valence.

Node doubling, degree-five interpolation, and shifted APFEL subgrid transitions
at fixed `xmin=1e-9` yielded residuals from `5.51e-5` to `5.65e-5`; they do
not converge toward zero.

The audit then extended only APFEL's computational grid while defining the
D0 boundary to be exactly zero below `1e-9`. No LHAPDF value was queried
outside support:

| Computational xmin | Center max independent residual | High-Q full momentum | High-Q retained momentum | Momentum below 1e-9 |
| --- | ---: | ---: | ---: | ---: |
| 1e-9 | 5.46e-5 | 0.99994536 | 0.99994535 | 0 |
| 1e-10 | 9.09e-6 | 0.99999094 | 0.99994619 | 4.4607e-5 |
| 1e-11 | 2.82e-6 | 1.00000211 | 0.99994725 | 5.4195e-5 |
| 1e-11, doubled nodes | 8.38e-7 | 0.99999916 | 0.99994360 | 5.4194e-5 |
| 1e-12 | 5.52e-6 | 1.00000552 | 0.99994874 | 5.6179e-5 |

For delta-min at `1e-11` with doubled nodes, the independent full-domain
maximum residual was `6.4815101532555985e-6`; high-Q momentum below exported
support was `6.2578836954374495e-5`.

The artifact-backed independent center integral had a maximum residual
`7.020911922306361e-5`, which combines exported-support leakage and transport
interpolation.

Decision 5: **the APFEL computational grid must extend to `1e-11` with the
declared zero input continuation below `1e-9` and a doubled-node convergence
partner**. Exported artifact support remains `[1e-9,1]`.

Decision 6: **conservation is a computational-domain gate**. Independent GL64
moments are binding; `Distribution::Integrate` remains a required diagnostic
because its extreme-anchor convergence differs at the `1e-5` scale.

Decision 7: **below-xMin evolved momentum is explicit provenance**. Every Q
knot records full-domain moments, retained-support moments, and their
difference. Retained-support momentum is not falsely required to equal one.
The leakage must be finite, nonnegative within numerical tolerance, and agree
between the base and doubled computational grids within `1e-7` absolute.

## Raw CT18 fidelity decomposition

On 270,193 flavor/x/Q comparisons:

| Comparison | Outside 2e-3 | Near-zero outside | Max absolute |
| --- | ---: | ---: | ---: |
| raw CT boundary evolved by APFEL vs public CT18 | 8,529 | 161 | 12.5682 |
| projected APFEL vs raw-boundary APFEL | 0 | 0 | 0.07226 |
| projected APFEL vs public CT18 | 8,532 | 161 | 12.6363 |

Thus the D0 projection adds three pointwise failures, while the independent
evolution implementation accounts for essentially the entire discrepancy.
The raw-evolution failures are concentrated but not confined to thresholds:
2,881 threshold, 2,190 other low-Q, 1,477 mid-Q, and 1,981 high-Q values.
By x, 3,618 are in the DIS range, 3,183 near the endpoint, and 1,728 at low x.
Charm and anticharm each contribute 1,474 failures and the gluon 1,670.

Decision 8: **raw CT18 pointwise fidelity is a mandatory diagnostic, not a
hard gate**. An independent evolution engine cannot support a claim of
universal pointwise identity with the public fitted grid. The decomposition,
including threshold and near-zero reporting, remains compulsory.

## Physical-observable audit

The D1 `compact_observable_gate` computes only the leading parton-model
photon-exchange expression

```text
F2 = sum_q e_q^2 [xq + x qbar]
```

using NLO-evolved PDFs. It contains no APFEL coefficient functions, no FL,
no parity-violating term, no gamma/Z interference, and no massive-heavy-flavor
treatment. It is a useful finite/sign smoke test but cannot bind Stage 1.

The repository's authoritative APFEL backend already constructs zero-mass
neutral-current photon-exchange F2, FL, and xF3 through APFEL++ coefficient
functions, with xF3 identically zero for electromagnetic charges.

Decision 9: **the binding physical gate is direct-APFEL versus
artifact-backed APFEL++ NLO photon-exchange F2 and FL**, with
`mu_F=mu_R=Q`, over the predeclared DIS x/Q2 grid. The combined relative
`1e-4` / absolute `1e-8` rule allows one order of magnitude above the PDF
transport tolerance for convolution numerics. Both paths must be finite, and
the photon-only reduced cross section must be nonnegative for
`y in [0.01,0.95]`. This is not full gamma/Z validation.

## Alternatives

| Option | Assessment |
| --- | --- |
| Threshold subgrids plus deterministic refinement | Selected. Preserves standard LHAPDF, deterministic bytes, cache identity, and future Pythia compatibility. Cost is bounded explicitly. |
| One dense global subgrid | Rejected. It interpolates across thresholds and uniform refinement remained inefficient. |
| Error-driven refinement without threshold separation | Rejected alone. It can close smooth regions but does not encode threshold semantics. |
| Custom Pythia PDF backed by direct APFEL | Rejected for this revision. It abandons the accepted common artifact, adds thread/process-lifetime risks, and belongs to a new design review. |
| Separate APFEL and Pythia representations | Rejected. It breaks the same-artifact scientific contract. |
| Reduced Q or x support | Rejected. It changes the study domain to evade observed failures. |
| Different evolution engine or baseline artifact | Rejected. The audit identifies finite-support and transport causes without requiring a new scientific family. |

## Revised Stage 1 acceptance

Decision 10 authorizes a future revised-D1 implementation and revalidation
only. It must:

1. preserve the accepted D0R v2 boundary, pilot box, nine anchors, alpha-s
   object, five-flavor ceiling, and strict exported support;
2. use a zero boundary continuation below `1e-9` only on an APFEL
   computational grid extending to `1e-11`;
3. run base and doubled-node computational grids and require independent GL64
   full-domain valence/momentum residuals `<=1e-5` at every Q and anchor;
4. record retained-support moments and below-support leakage, requiring
   base/refined leakage agreement `<=1e-7`;
5. write charm/bottom-separated Q subgrids and use the bounded deterministic
   refinement algorithm above;
6. retain exact-knot zero-failure, alpha-s, finite-value, strict-support,
   checksum, corruption, concurrency, and byte-reproducibility gates;
7. require loaded LHAPDF and independent log-bicubic reconstruction to agree
   within `1e-12` relative or `1e-10` absolute;
8. require direct APFEL versus artifact values to pass the unchanged
   `1e-5` relative / `1e-9` absolute rule at all fixed probes;
9. retain raw-CT18 decomposition as a nonbinding diagnostic;
10. pass the NLO photon-exchange F2/FL observable contract above; and
11. return PASS, FAIL, or INCONCLUSIVE without changing thresholds or silently
    dropping points.

Any complexity-cap breach, unresolved subgrid boundary, computational-grid
nonconvergence, or observable ambiguity is FAIL or INCONCLUSIVE. D2 remains
blocked until a revised-D1 PR is separately reviewed and merged.

## Consequences

- The original D1 FAIL remains immutable.
- The artifact writer and cache architecture are retained.
- Conservation and exported-domain retention are no longer conflated.
- Raw CT18 remains essential evidence without demanding impossible
  implementation identity.
- Revised D1 will be more expensive, but its complexity is bounded before
  implementation.
- No PYTHIA coupling or event generation is authorized.

## Revisit conditions

Revisit this ADR if the bounded refinement cannot close all nine anchors, the
computational-domain moments fail convergence, standard LHAPDF subgrids cannot
represent the APFEL threshold behavior, or the NLO structure-function paths
cannot be made representation-identical.

## Authorization

```text
D1_REVISION_IMPLEMENTATION_AUTHORIZED = true
D2_AUTHORIZED = false
```

Authorization is limited to implementing and revalidating this revised Stage 1
contract after scientific review of this ADR.
