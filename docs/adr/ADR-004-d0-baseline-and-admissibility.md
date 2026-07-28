# ADR-004: D0 baseline identity and NLO admissibility

Status: Proposed for scientific review

Date: 2026-07-28

## Context

Phase 1B-D0 completed with `FAIL`. That negative result is retained in
`AMORTIZED_INFERENCE_PHASE1BD_D0.md` and
`phase1bd_d0_decision.json`; this ADR does not reinterpret it as a pass.
Every one of the 441 pilot points failed the fixed pointwise-negativity gate,
and the normalized center failed the fixed raw-CT18NLO reconstruction gate.
The metadata, heavy-flavor boundary, sum rules, construction stability,
independent quadrature, and deterministic point identity passed.

The failed family used two objects under one name:

1. the raw LHAPDF representation of CT18NLO member 0 at `Q0`; and
2. its exact finite-support sum-rule projection.

Those objects cannot be identical because the public numerical representation
does not satisfy the valence and momentum rules exactly under the repository's
declared support and integration contract. The center was therefore required
both to reproduce raw CT18NLO and to differ from it by the projection needed
to impose exact sum rules.

The strict positivity gate also treated a scheme-dependent NLO input PDF as
though every interpolated number density were itself a physical observable.
The D0 endpoint audit was required before changing that contract.

## Primary-source audit

The audit used the installed LHAPDF 6.5.6 headers, CT18NLO
`DataVersion: 1` member file, and the matching LHAPDF source tag
`lhapdf-6.5.6` at commit
`92239ac82134be698805c1002b4615e5167c6fa3`.

`GridPDF` stores the tabulated `xf` values in `KnotArray`. Its `logcubic`
interpolator constructs an unconstrained cubic Hermite polynomial in
`log(x)`. Endpoint derivatives are estimated from adjacent knot slopes; there
is no sign-preserving limiter. At `Q0`, evaluation uses the first Q row and
the x polynomial. The installed global LHAPDF configuration selects the
`continuation` extrapolator, so strict support must remain a caller contract.
No extrapolated value was used in this audit.

APFEL++ 4.8.0 accepts input-distribution callbacks and the repository's
existing backend passes the physical `x f_i` map through
`apfel::PhysToQCDEv`. It does not require strict positivity of every
factorization-scheme PDF value at the input boundary. A later stage must
nevertheless validate evolved physical observables before generation.

## Endpoint-source diagnosis

At `Q0 = 1.295 GeV`, all 161 authoritative raw gluon knots are nonnegative.
Direct `xfxQ2` evaluations at every knot agree with `KnotArray::xf` to a
maximum absolute difference of `4.5494933690416522e-24`.

The final interval is:

```text
last positive knot:
  x       = 0.99262
  xf_g    = 2.6821982100000002e-9

first zero knot:
  x       = 1
  xf_g    = 0

negative raw knots:
  none
```

The LHAPDF logcubic polynomial becomes negative between those nonnegative
knots:

```text
first zero crossing       = 0.9935531299173892
negative interval         = (0.9935531299173892, 1)
minimum interpolated xf_g = -1.8784951425865714e-9
at x                      = 0.9955233026506225
minimum number density g  = -1.8869448687227857e-9
at x                      = 0.9955207116819784
```

The original D0 grid's logarithmic midpoint at
`x=0.9963031667118196` has raw `g=-1.6922161497066621e-9`; it was sufficient
to fail the fixed gate but is not the continuous interpolant's true minimum.

The last-interval cubic coefficients, ordered from cubic through constant,
are:

```text
-2.4216475309708858e-8
 4.8432950619417723e-8
-2.6898673519708860e-8
 2.6821982100000002e-9
```

This establishes that the negative excursion is created by LHAPDF's off-knot
logcubic interpolation. It is already present at `theta=(0,0)` before any
PartonSBI deformation or sum-rule projection.

The raw integrated negative gluon momentum is:

```text
integral x max(-g,0) dx = 6.187935491060024e-12
fraction of gluon momentum = 1.5822152070733786e-11
```

An independent refined GL64 evaluation gives
`6.187936586360181e-12`. The positive gluon normalizations do not change the
zero crossing or create a sign change. They scale the excursion:

| `A_g` case | Minimum `g` | Negative momentum |
| --- | ---: | ---: |
| center, `0.9999935202034876` | `-1.8869326417040061e-9` | `6.187895394497210e-12` |
| pilot minimum, `0.6158503545333242` | `-1.1620756663877644e-9` | `3.810842265998655e-12` |
| pilot maximum, `1.3932683805529793` | `-2.6290206214381498e-9` | `8.621454860595505e-12` |

The deformation therefore inherits and positively rescales the same endpoint
feature; it does not introduce it.

## Central-moment diagnosis

The raw CT18NLO moments on `[1e-9,1]` are:

| Moment | GK15 | refined GL64 |
| --- | ---: | ---: |
| `integral u_v^0 dx` | `1.9999957697565598` | `1.9999957697565556` |
| `integral d_v^0 dx` | `0.9999797398108460` | `0.9999797398108469` |
| `integral x sum_i f_i^0 dx` | `0.9999991913056495` | `0.9999991913056507` |
| `integral x g^0 dx` | `0.3910931625101645` | `0.3910931625101662` |
| light-sea momentum | `0.1583622595118473` | `0.1583622595118495` |

The exact raw residuals are:

```text
u-valence = -4.230243440206394e-6
d-valence = -2.026018915401995e-5
momentum  = -8.086943509288957e-7
```

They produce:

```text
A_u = 1.0000021151261937
A_d = 1.0000202605996376
A_g = 0.9999935202034876
```

These reproduce the original report's rounded values to at least
`3.7e-13`. GK15, GL64 with 2, 4, and 8 subdivisions, and deterministic
refinement agree at approximately `1e-14`; quadrature is not the source.
Explicit flavor IDs and the raw momentum result exclude an extra sea factor or
quark/antiquark convention error.

The raw knot-only trapezoid gives valence moments
`2.0026079537233068` and `1.0015103868055282`, and total momentum
`1.0002523082817836`. Adding one logarithmic midpoint per interval moves these
to `2.0006487566617102`, `1.0003624606674992`, and
`1.0000628340795883`. This slow deterministic convergence shows why raw-knot
trapezoids are not an authoritative moment definition; it does not contradict
the mutually agreeing GK15 and GL64 results.

Extending the diagnostic from the declared `xMin=1e-9` down to the first raw
knot at `9.26136e-10` adds:

```text
u-valence              = 5.433040778806293e-7
d-valence              = 0
total momentum         = 1.084180276815840e-9
```

Finite declared support explains part of the up-valence residual but not the
down-valence correction or the momentum correction. The endpoint negative
momentum is also far too small to explain the normalization factors.

The remaining residual belongs to the public numerical baseline: finite-
precision CT18NLO tabulation plus LHAPDF's declared interpolation over the
chosen finite support. The installed artifact does not expose the unpublished
pre-tabulation fit, so those two contributions cannot be separated further
without changing the authoritative baseline. That separation is unnecessary
for the contract decision: the public LHAPDF representation is the
reproducible source object.

The projection changes integrated momentum by:

```text
up valence  +6.743735139310437e-7
down valence +2.668524947393334e-6
gluon       -2.534204110441108e-6
net         +8.086943509288957e-7
```

The maximum pointwise relative `xf` changes are the original D0 values:
`2.115127689774372e-6` for up, `2.026061085392738e-5` for down, and
`6.479796512590086e-6` for the gluon. They are small, explicit, and larger
than the old raw-center gate. They must not be hidden by averaging.

## Alternatives

### Option A: raw-LHAPDF center

Set `theta=0` equal to the raw LHAPDF values and normalize deformations
relative to the raw numerical moments.

- Center identity and future direct-CT comparisons are simple.
- Exact physical sum rules are not true at the center under the declared
  representation.
- Special-casing the center would make the family discontinuous in its
  semantics.
- APFEL++ and a future artifact could consume it, but every manifest would
  have to carry inherited residuals.

Rejected: it gives up the exact sum-rule objective and does not resolve the
distinction between the fitted PDF and its public numerical representation.

### Option B: versioned sum-rule-projected baseline

Define a new named baseline by applying the measured finite-support projection
once to raw CT18NLO member 0:

```text
u_v^P = A_u^0 u_v^0
d_v^P = A_d^0 d_v^0
sea^P = sea^0
g^P   = A_g^0 g^0
```

with the three constants above. `theta=0` means this projected object.
The raw CT18NLO comparison becomes a fidelity diagnostic with explicit,
nonzero expected corrections, not an identity gate.

- Valence and momentum rules are exact under the repository representation.
- Center identity is exact against a single versioned object.
- Applying the existing normalized tilts to the projected baseline is
  algebraically equivalent to the D0 v1 family values; only provenance,
  identity, and the comparison contract change.
- APFEL++ can consume the same physical `xf` callback.
- A later LHAPDF artifact and Pythia must identify the projected baseline, not
  claim to be unmodified CT18NLO.
- Reproducibility requires raw set/member/data version, support, interpolation,
  integration policy, and projection constants in every point identity.

Selected.

### Option C: sign-preserving endpoint representation

A local log-linear final gluon interval would preserve both endpoint knots and
remove the negative excursion. Relative to LHAPDF logcubic it has:

```text
maximum absolute xf difference = 3.587625971806028e-9
maximum density difference     = 3.605393685752992e-9
net gluon momentum change      = 1.488208682078120e-11
fraction of gluon momentum     = 3.805253644748755e-11
```

The numerical effect is tiny, but it creates a third baseline representation.
A future LHAPDF `logcubic` artifact would reproduce the overshoot unless its
interpolation policy or knots also changed, and consistency with APFEL++ and
Pythia has not been demonstrated.

Rejected for the revision: changing interpolation is unnecessary once input
admissibility distinguishes inherited NLO representation behavior from new
deformation behavior. Revisit only if evolved observables reveal a material
endpoint effect.

### Option D: different `Q0`, set, or perturbative order

Moving to `Q=1.3 GeV` is not a numerical repair. It moves above the selected
boundary and the charm threshold; direct CT18NLO evaluation already reaches
`max |xf_c| = 6.187059967364876e-4` on the knot grid there, so the verified
zero-heavy-flavor boundary changes. A different set or order changes the
support, alpha-s evolution, thresholds, generator consistency, and scientific
reference.

Rejected: those are new scientific families, not D0 contract revisions.

### Option E: independent analytic basis

An analytic basis could make endpoint powers and positivity explicit, but it
adds unvalidated choices for sea asymmetry, strange normalization, gluon
shape, threshold matching, polynomial order, and parameter priors.

Rejected for the same reasons recorded in ADR-001. It may be reconsidered only
through a separately reviewed family design.

## Decision

### Baseline identity

Adopt, subject to review and a separate implementation task:

```text
baseline_version = ct18nlo_member0_sumrule_projected_boundary_v2
family_version   = ct18nlo_two_parameter_boundary_v2
```

The source remains CT18NLO member 0, `DataVersion: 1`, evaluated through
LHAPDF 6.5.6 at metadata-derived `Q0=1.295 GeV` with strict declared support.
The projected baseline is constructed exactly as Option B. Its provenance
must include the raw source identity, all authoritative metadata, interpolation
and extrapolation policy, integration policy, projection constants, and
software versions.

`theta=(0,0)` means exact reproduction of the projected baseline. It does not
mean byte- or pointwise identity with raw CT18NLO. Raw CT18NLO deviations must
remain a reported fidelity diagnostic with the values above as reviewed
reference results.

### Input admissibility

Replace universal input-PDF nonnegativity with a baseline-relative NLO
admissibility contract:

1. retain finite values, positive normalizations, heavy-boundary, support,
   sum-rule, quadrature, and identity gates unchanged;
2. enumerate every baseline sign interval from authoritative knots and
   deterministic off-knot root searches;
3. reject every new flavor sign change or negative connected component created
   by a deformation;
4. allow an inherited negative component only when the declared deformation
   maps it by an explicit positive multiplicative factor;
5. record, for each flavor, `integral x max(-f_i,0) dx` and its fraction of
   that flavor's signed momentum;
6. for a purely scaled flavor, require the negative-momentum fraction and sign
   interval to remain invariant. Independent integrations must agree within
   `max(1e-17, 1e-6 * inherited_negative_momentum)`;
7. do not clip, replace, project, or silently omit a negative value.

For the current family, the gluon and sea are pure positive rescalings. Up and
down are not; they must remain nonnegative wherever their projected baselines
are nonnegative. A future implementation must fail rather than invent an
allowance for a new quark negative region.

This is not a claim that a negative NLO PDF value is physical. PDF
admissibility and physical-observable admissibility are separate. If revised
D0 passes, D1 must evaluate evolved structure functions and the declared
neutral-current cross section over a predeclared grid. Non-finite or negative
physical predictions stop progression before Pythia coupling. Artifact
interpolation must also be compared against the direct APFEL++ object,
including the endpoint region.

## Revised Stage 0 acceptance proposal

Revised Stage 0 should pass only when:

- the projected-baseline manifest matches the authoritative raw source and
  reviewed projection constants;
- `theta=0` reproduces the projected baseline under the existing `1e-6`
  relative / `1e-10` absolute pointwise rule;
- the raw CT18NLO comparison reports, but does not erase, the expected
  projection corrections;
- all 441 original pilot points pass the unchanged construction and independent
  sum-rule thresholds;
- normalization constants are finite and strictly positive;
- heavy flavors retain the verified zero boundary;
- no deformation introduces a new sign interval;
- inherited negative components obey the baseline-relative scaling and
  negative-momentum invariant above;
- all 80 guard-shell points remain diagnostic only;
- canonical identities use the new baseline and family versions and remain
  deterministic;
- values outside the hard pilot box remain typed errors.

The pilot bounds and all original numerical tolerances remain unchanged. The
original v1 D0 result remains `FAIL`.

## Consequences

- The distinction between raw CT18NLO and the projected PartonSBI boundary is
  explicit and reproducible.
- Exact center identity and exact sum rules refer to one object rather than two
  incompatible objects.
- Tiny inherited logcubic endpoint behavior is reported rather than clipped.
- A revised D0 implementation can reuse the existing mathematical values but
  must change versioned provenance, comparison logic, sign diagnostics, and
  tests.
- D1 remains unauthorized until that revised implementation and complete
  pilot-box validation are reviewed and pass.
- No APFEL evolution, LHAPDF artifact, Pythia coupling, events, datasets, or
  neural work is authorized by this ADR.

## Rejected options

Options A, C, D, and E are rejected for this revision. No tolerance is relaxed,
no pilot bound is changed, and no observed value is clipped.

## Revisit conditions

Revisit this decision if:

- independent implementations do not reproduce the projection constants;
- a revised pilot point creates a new sign interval;
- APFEL++ evolution amplifies the inherited endpoint component materially;
- a physical structure function or cross section becomes inadmissible;
- a generated artifact cannot preserve the direct APFEL++ representation;
- new scattering channels justify a different family.

## Implementation authorization

```text
D0_REVISION_IMPLEMENTATION_AUTHORIZED = true
D1_AUTHORIZED = false
```

Authorization is limited to implementing and revalidating the revised D0
baseline and admissibility contract after this ADR is accepted. It does not
authorize D1 or any later phase.
