# Phase 1B-D design: continuous PDF family with direct regeneration

Status: design for scientific review; no Phase 1B-D implementation exists.

## 1. Executive decision summary

- Use a two-parameter multiplicative deformation of CT18NLO member 0 at the
  authoritative `Q0 = 1.295 GeV` boundary.
- Enforce both valence-number rules analytically and the momentum rule through
  a positive gluon normalization; fail rather than clip an invalid family.
- Evolve with APFEL++ at NLO and export one immutable, content-addressed
  LHAPDF6 artifact per parameter point.
- Load the same artifact in validation and Pythia, with explicit all-consumer
  strict-support instrumentation.
- Generate every point directly. The Phase 1A nominal pool is never reused.
- Test fixed-envelope accept-reject unweighting as the primary shape-only MVP
  hypothesis. It is not accepted until its empirical gate passes.
- Keep rate-aware Poisson event counts, weighted neural sets, additional flavor
  directions, large-scale production, and neural inference deferred.

## 2. Scientific scope and inherited decision

Phase 1A rejected nominal-pool reuse because the predeclared effective-sample-size
gate failed. Phase 1B-D therefore studies a continuous, sum-rule-preserving PDF
family by generating events directly at each PDF parameter point. It must not
reuse, reweight, resample, or clip a nominal event pool.

The inference unit remains a set of events,

```text
D = {event_1, ..., event_N},
```

and the eventual target is `p(theta_PDF | D)`. This design does not implement
that posterior, generate a training set, or authorize neural inference.

The first implementation target is a shape-only study of the normalized
truth-level distribution after the declared DIS and strict-support selections.
Rate-aware inference is a separate extension.

This is a controlled, low-dimensional closure family. It is not a complete
proton-PDF parameterization. Later charged-current, positron-proton,
flavor-tagged, and multi-energy channels could motivate separately gated
flavor directions without changing the first MVP claim.

## 3. Authoritative baseline

The initial family is tied to the installed CT18NLO member 0 metadata:

| Quantity | Design value |
| --- | --- |
| LHAPDF set/version | CT18NLO, `DataVersion: 1` |
| Members | 59 |
| QCD order | NLO (`OrderQCD: 1`) |
| Flavor scheme | variable, five active flavors at high scale |
| `x` support | `[1e-9, 1]` |
| `Q` support | `[1.295, 1e5]` GeV |
| `alpha_s(M_Z)` | 0.118 |
| charm mass | 1.300 GeV |
| bottom mass | 4.750 GeV |
| strange mass | 0.2 GeV |

Generic code must obtain these values from authoritative LHAPDF metadata. The
numbers above define this design instance; they must not become generic
hard-coded limits.

The input scale is selected as

```text
Q0 = 1.295 GeV,
```

not the rounded roadmap proposal of 1.30 GeV. It is the actual CT18NLO lower
grid scale, lies just below the charm threshold, and permits forward evolution
for every supported event. Choosing 1.30 GeV would silently exclude the first
part of the declared grid and would change the family. Exact-boundary
evaluation, central-member reconstruction, and the vanishing heavy-flavor
boundary condition are mandatory Stage 0/1 checks. A failure requires a design
revision; implementations must not silently move `Q0`.

All scale variables in the family and APFEL++ evolution are `Q` in GeV.
LHAPDF APIs that accept `Q2` receive `Q0 * Q0` exactly once.

### 3.1 Primary-source basis

The design was checked against the installed, pinned interfaces rather than a
secondary tutorial:

- LHAPDF 6.5.6 set metadata and the `PDFInfo`, `GridPDF`, factory,
  `ErrExtrapolator`, and interpolation interfaces;
- APFEL++ 4.8.0 `AlphaQCD`, `BuildDglap`, `Distribution`, sum-rule tests, and
  DGLAP examples;
- Pythia 8.312 `PDF`, `setPDFPtr`, LHAPDF6 adapter, custom-PDF example,
  phase-space-weight implementation, and phase-space settings reference;
- the repository's pinned setup scripts, CMake integration, generator source,
  and Phase 0A/1A provenance contracts.

The installed LHAPDF configuration selects `logcubic` interpolation and exposes
an `error` extrapolator. The installed Pythia adapter's boundary handling is
the reason all-consumer support instrumentation is a gate rather than an
assumption.

## 4. Parameterization alternatives

### 4.1 Multiplicative deformation of CT18NLO

This option deforms a validated central PDF at `Q0`, retains its detailed
small- and large-`x` structure, and uses two parameters with direct physical
interpretations. Its drawbacks are dependence on the CT18NLO baseline and the
need to reconstruct and integrate flavor combinations accurately at a
threshold-scale grid boundary.

### 4.2 Independent analytic basis

An analytic basis such as

```text
x f_i(x, Q0) = A_i x^(a_i) (1-x)^(b_i) P_i(x)
```

would make endpoint behavior explicit and could later support broader PDF
families. With only two parameters, however, it would replace rather than
locally explore the validated baseline. It also introduces otherwise
unconstrained choices for sea asymmetry, strange fraction, gluon shape,
threshold matching, and polynomial order.

### 4.3 Selection

The multiplicative CT18NLO deformation is selected for the first direct-
generation family. An independent analytic basis is rejected for the MVP and
may be reconsidered only after direct-generation and sampling semantics pass.

## 5. Exact two-parameter family

Let the parameters be

```text
theta = (delta_v, lambda_sea).
```

The candidate pilot box inherited from the roadmap is

```text
delta_v     in [-0.20, 0.20]
lambda_sea  in [-0.25, 0.25].
```

These are validation bounds, not an accepted scientific prior. Stage 0 must
test the full box, including edges and corners, for positivity, sum rules,
numerical conditioning, and selected-DIS sensitivity. Production prior bounds
remain `REQUIRES EXPERIMENT`.

For `x` in `[x_min, 1]`, reconstruct number densities from the baseline
LHAPDF values:

```text
f_i^0(x) = xf_i^0(x, Q0) / x
u_v^0    = u^0 - ubar^0
d_v^0    = d^0 - dbar^0.
```

Use the fixed conditioning pivot `x_p = 0.1` and define

```text
t_v(x; delta_v) = (x / x_p)^delta_v.
```

The valence distributions are

```text
u_v(x; theta) = A_u(delta_v) u_v^0(x) t_v(x; delta_v)
d_v(x; theta) = A_d(delta_v) d_v^0(x) t_v(x; delta_v)

A_u = 2 / integral[u_v^0 t_v dx]
A_d = 1 / integral[d_v^0 t_v dx].
```

The common light-sea deformation is

```text
S(lambda_sea) = exp(lambda_sea)

ubar = S ubar^0
dbar = S dbar^0
s    = S s^0
sbar = S sbar^0

u = u_v + ubar
d = d_v + dbar.
```

This deliberately preserves the baseline light-sea flavor ratios and
asymmetries. It does not claim they are identified by inclusive neutral-current
electron-proton data.

At the selected CT18NLO boundary, `c`, `cbar`, `b`, and `bbar` must be zero
within the exact Stage 0 tolerance and are not free parameters. APFEL++ creates
them through variable-flavor evolution above their thresholds. If the
authoritative baseline does not satisfy that boundary condition, family
construction fails rather than copying or clipping heavy flavor.

Let

```text
M_q(theta) = integral[x * sum(q + qbar) dx]
M_g0       = integral[x * g0 dx]
A_g(theta) = (1 - M_q(theta)) / M_g0
g(theta)   = A_g(theta) g0.
```

Construction fails when any normalization is non-finite or non-positive.
There is no positivity repair and no value clipping.

The model has compact declared support. It is zero outside `[x_min, 1]`; it is
never evaluated there as an extrapolated PDF. The sum rules are therefore
defined on `[1e-9, 1]`, an explicit finite-support modeling choice.

At small `x`, the sea and gluon retain their baseline powers and the valence
receives only the explicit `x^delta_v` factor. At large `x`, the tilt is finite
and the baseline endpoint zeros and powers are preserved; sea and gluon shapes
change only by normalization. The family is smooth on the open support, uses
zero at `x=1`, and introduces no extra polynomial or hidden continuation.

### 5.1 Sum-rule algorithm

Construction uses deterministic adaptive Gauss-Kronrod integration in
`z = log(x)`, partitioned at every input-grid knot and at the fixed pivot.
Requested absolute and relative integration tolerances are `1e-10`.
An independent verifier uses composite 64-point Gauss-Legendre quadrature on a
strict refinement of the same domain.

The construction gate is:

```text
abs(integral[u_v dx] - 2) <= 1e-8
abs(integral[d_v dx] - 1) <= 1e-8
abs(integral[x * (g + sum(q + qbar)) dx] - 1) <= 1e-8.
```

The independent acceptance gate is `1e-6` for each residual. A result that
depends on quadrature tolerance or partition refinement is `INCONCLUSIVE`, not
a pass.

Positivity is checked at all artifact knots and at midpoint/refined points.
Any negative value is recorded. Values below `-1e-12` fail immediately; values
in `[-1e-12, 0)` make the result inconclusive pending a numerical analysis.
They are never silently set to zero.

### 5.2 Central point

`theta = (0, 0)` is the family reference. The normalization construction may
make sub-tolerance corrections to the tabulated central member because the
finite support and numerical quadrature enforce exact sum rules. It must
reproduce CT18NLO member 0 within the Stage 1 pointwise and observable
tolerances. It must not be special-cased to bypass the sum-rule algorithm.

### 5.3 Pilot domain and anchors

The initial hard validation domain is exactly:

```text
-0.20 <= delta_v <= 0.20
-0.25 <= lambda_sea <= 0.25.
```

Inputs outside it return a typed error; they are not projected to a boundary.
The nine mandatory anchors are the center, four axis endpoints, and four
corners:

```text
(0, 0)
(-0.20, 0), (0.20, 0)
(0, -0.25), (0, 0.25)
(-0.20, -0.25), (-0.20, 0.25)
(0.20, -0.25),  (0.20, 0.25).
```

Stage 0 also uses a deterministic `21 x 21` scan of the closed box and a 5%
expanded guard shell as a conditioning diagnostic. Guard-shell points are not
prior samples. The production prior remains unresolved until this experiment
passes; invalid points are never silently projected inward.

## 6. Scientific identifiability

The two parameters are deliberately broad directions:

- `delta_v` changes a common valence shape while preserving valence counts.
- `lambda_sea` changes a common light-sea normalization, with the gluon
  normalization compensating the momentum sum rule.

Inclusive neutral-current electron-proton scattering does not provide
unrestricted flavor separation. The shared sea direction and shared valence
tilt encode this limitation rather than claim independent `u`, `d`, `s`, or
gluon identification. Sensitivity, degeneracy, and prior-to-posterior
contraction must be reported by parameter direction. A negative
identifiability result is valid.

Hard flavor and `GenPdfInfo` remain generator provenance and validation truth;
they are not default observed ML features.

## 7. Evolution and direct-generation artifact

### 7.1 Alternatives considered

1. **APFEL++ evolution followed by a generated LHAPDF grid.** One immutable
   artifact can be loaded by both validation and Pythia. It requires a small,
   tested `lhagrid1` writer because LHAPDF 6.5.6 exposes no public grid-writer
   API.
2. **A custom Pythia `PDF` implementation.** Pythia permits this through
   `setPDFPtr`, but it would introduce a second interpolation/cache path and
   risk disagreement with the APFEL++ validation path.
3. **Separate APFEL++ and Pythia representations.** This is smaller initially
   but cannot establish that validation and generation used the same numerical
   family.

| Criterion | APFEL++ to LHAPDF grid | Custom Pythia PDF | Separate representations |
| --- | --- | --- | --- |
| NLO/VFNS consistency | one APFEL++ evolution | must duplicate or embed evolution | disagreement risk |
| thresholds and `alpha_s` | metadata-derived and serialized | custom responsibility | two contracts |
| Pythia compatibility | native LHAPDF interface | supported by `setPDFPtr` | native plus separate validator |
| APFEL++ compatibility | direct construction reference | adapter required | native but different bytes |
| caching and identity | immutable file artifact | custom in-memory identity | multiple identities |
| process safety | atomic read-only artifact | ownership/cache audit required | dual cache audit |
| CI feasibility | deterministic round-trip fixture | custom C++ surface | cheapest but scientifically weak |
| runtime | per-point evolution plus load | per-process evolution/load | duplicated work possible |

### 7.2 Selected mechanism

APFEL++ evolves the `Q0` callback at NLO using the metadata-derived masses,
thresholds, and `alpha_s`. A deterministic exporter writes a one-member
LHAPDF6 `lhagrid1` artifact, its `.info` file, and a cryptographic manifest.
The artifact uses the authoritative baseline `x` and `Q` knot layout, while
all values are newly evolved from the parameterized boundary condition.
The APFEL++ `AlphaQCD` object is initialized from the CT18NLO
`alpha_s(M_Z)`, NLO order, and heavy-flavor thresholds; the exporter evaluates
that same object on the artifact `AlphaS_Qs` knots to produce `AlphaS_Vals`.
It does not copy a numerically independent running-coupling table.

Both APFEL++ validation and Pythia load the same generated artifact. The
analytic boundary callback and direct APFEL++ evolution remain independent
construction references. The writer is not accepted until LHAPDF 6.5.6 can
round-trip every flavor/knot and agrees with direct APFEL++ values and sum
rules.

A generated `.info` file explicitly selects LHAPDF 6.5.6's `logcubic`
interpolator and `error` extrapolator. Interpolation is validated both at knots
and deterministic off-knot points. The error extrapolator is defense in depth:
the caller and the instrumented Pythia adapter must still reject unsupported
queries before evaluation. The generated artifact carries the same
metadata-derived support, variable-flavor settings, masses, NLO order, and
tabulated `alpha_s` contract used by APFEL++.

A custom Pythia PDF is rejected as the primary representation. A thin,
diagnostic Pythia adapter that loads the same artifact and records every
support query is permitted in a future implementation if required to enforce
the support contract.

Pythia's installed LHAPDF adapter freezes some out-of-grid queries at a
boundary. That behavior is not accepted as strict in-grid evaluation.
Stages 2 and 3 must count every Pythia PDF query, including shower consumers,
and fail closed if any query is outside the artifact domain. A strict
hard-process `GenPdfInfo` veto alone is insufficient evidence.

## 8. Deterministic identity and cache contract

Each point is serialized as canonical UTF-8 JSON with:

- a schema and family version;
- lexicographically sorted keys and no insignificant whitespace;
- PDF set and data version;
- metadata-derived support and evolution settings;
- each floating-point value encoded by its exact lowercase IEEE-754 binary64
  hexadecimal bit pattern;
- source commit and toolchain/dependency identifiers where they affect bytes.

The point identifier is the full lowercase SHA-256 digest:

```text
sha256:<64 hexadecimal characters>.
```

Floating-point values never appear in directory names. The ignored cache path
is:

```text
.external/partonsbi/pdf-artifacts/v1/sha256/<first-two>/<full-hash>/
```

Builds use a per-hash filesystem lock and a same-filesystem temporary
directory. Files are checksummed, reopened through LHAPDF, validated, and only
then atomically renamed. Every load revalidates the manifest and file hashes.
A corrupt or incomplete directory is marked unusable; scientific execution
does not overwrite it in place or accept it as a cache hit. Under the same
per-hash lock, recovery atomically renames it to an ignored
`<full-hash>.corrupt.<observed-manifest-hash>` quarantine path and performs a
fresh temporary build. A byte-valid artifact with the expected identity is
immutable; an attempted build that differs is a fatal reproducibility error.

Scientific production requires a clean repository and records
`git_commit` and `dirty=false`. A dirty build may be used only for explicitly
labeled development diagnostics and cannot enter an accepted dataset.
Generated grids are cache artifacts and must not be committed.

## 9. Direct generation pipeline

For each parameter point:

1. validate and canonicalize `theta`;
2. construct the `Q0` boundary and enforce sum rules;
3. evolve and validate the immutable LHAPDF artifact;
4. calibrate the sampling envelope using a disjoint deterministic seed family;
5. generate independent candidate shards directly with that artifact;
6. enforce DIS, momentum, and all-consumer PDF-support selections;
7. apply the predeclared sampling decision;
8. write validated set shards and manifests;
9. assemble fixed-`N` pseudo-experiments without cross-point mixing;
10. run direct-versus-direct reproducibility and anchor checks.

There is no nominal pool and no cross-point event reuse.

Seeds are derived by hashing the study ID, split, point ID, stage, replicate,
and shard index, then mapping into Pythia's documented seed range. The complete
mapping is recorded and collisions are rejected. Artifact construction,
envelope calibration, candidate generation, sampling RNG, validation, and
train/validation/test splits use disjoint seed namespaces. A retry preserves
the logical shard identity and records an attempt counter; it never silently
changes an accepted shard.

Manifests record attempted events, Pythia successes, each veto reason,
candidate and selected weights, cross sections, support queries, seeds,
commands, dependency versions, file hashes, and clean Git provenance.

## 10. Event sampling and overweight decision

Phase 1A showed a severe generator-weight tail. Phase 1B-D must resolve that
sampling semantics problem before generating a training corpus.

### 10.1 Options

**Pythia maximum-envelope adjustment.** `PhaseSpace:increaseMaximum=on` can
change the envelope after earlier events have been accepted. It is rejected
for the MVP because those earlier events then carry incorrect relative
sampling semantics.

**Second-stage accept-reject unweighting.** A weighted candidate stream can be
converted to an unweighted stream only if the recorded nonnegative weight is
the target/proposal ratio up to a constant and a fixed independent upper bound
`M` is valid. Candidates are selected with probability `w/M`. This is the
primary MVP hypothesis, not yet an accepted implementation.

**Weighted event sets.** Keeping weights is statistically legitimate for some
estimators, but a neural set model would need an explicit weighted empirical-
measure contract and would not receive ordinary i.i.d. sets. It is deferred as
a primary training representation and retained as a validation reference.

**Weight clipping, winsorization, or overwriting.** Rejected. No source weight
may be clipped, capped, removed, or set to one.

| Option | Statistical/bias contract | Efficiency and negative weights | Set/rate/calibration impact |
| --- | --- | --- | --- |
| Dynamic Pythia maximum | earlier accepts can acquire wrong relative normalization | efficient if known; does not solve signed weights | invalidates a stable fixed-`N` contract |
| Fixed-bound accept-reject | exact only when `w` is a nonnegative target/proposal ratio and `M` is valid | efficiency `E[w]/M`; negative weights unsupported | yields ordinary shape sets if Stage 4 passes; rate retained separately |
| Weighted empirical sets | correct for compatible weighted estimators | retains signed weights but ESS may remain poor | requires weighted encoders and new calibration theory |
| Shape/rate separation | conditions on fixed `N` without changing event weights | orthogonal to generator efficiency | prevents implicit use of cross section; Poisson rate can be added later |

### 10.2 Primary experiment

Stage 4 tests second-stage accept-reject unweighting. For each parameter point,
an independent calibration stream contains exactly 100,000 Pythia-successful
candidates and is reduced without storing event records. The candidate rule is
predeclared as

```text
M = next_up(2 * maximum_finite_nonnegative_calibration_weight).
```

The factor, count, point identity, and calibration seeds are part of the
envelope version. This empirical rule is a hypothesis to validate, not proof
of a globally bounded Pythia weight. Production candidates use disjoint seeds
and share the frozen point-specific `M`. Any negative/non-finite weight, any
`w > M`, or any unsupported query invalidates the complete shard; previously
selected events from it do not enter a dataset. The bound is not raised after
observing production. Retrying under a revised envelope is a new versioned
experiment, not a repair of the same sample.

Selected events carry a unit statistical weight only because of their
recorded Bernoulli selection. The source generator weight, inclusion
probability, envelope version, and random draw remain provenance. The method
passes only if unweighted observables agree with independent weighted
estimators and independent direct samples under the acceptance document.

### 10.3 Shape and rate semantics

The MVP produces fixed-size sets from the normalized selected distribution:

```text
p(event | theta, declared selection).
```

The set size is fixed and cross-section information is excluded from model
features. This is explicitly shape-only inference.

A later rate-aware extension may use

```text
N ~ Poisson(luminosity * selected_cross_section(theta))
```

with a predeclared luminosity and all normalization uncertainties. It is
deferred and cannot be inferred from fixed-`N` sets. Cross sections are still
retained as validation diagnostics.

## 11. Validation program

The binding pass/fail/inconclusive rules are in
`AMORTIZED_INFERENCE_PHASE1BD_ACCEPTANCE.md`.

- Stage 0: family mathematics, metadata, prior-box scan, and independent sum
  rules.
- Stage 1: APFEL++ evolution, grid serialization, round-trip fidelity, and
  central reconstruction.
- Stage 2: APFEL++/Pythia same-artifact proof, all-consumer support, and
  `alpha_s`/evolution metadata consistency.
- Stage 3: independently seeded direct-generator smoke runs at the center,
  axis endpoints, and corners.
- Stage 4: weight semantics, fixed-envelope validation, unweighting, and
  shape/rate separation.
- Stage 5: small independently seeded direct anchor design,
  direct-versus-direct closure, throughput/storage measurement, and
  scale-authorization decision.

No later stage begins after an earlier `FAIL`. `INCONCLUSIVE` requires a
documented decision before continuation.

## 12. Resource model

The roadmap scale contains:

```text
128 points * 100 sets * 1024 events = 13,107,200 selected events.
```

At the Phase 1A measured accepted-event rate of approximately 223 events/s,
the optimistic raw serial generation time is:

```text
13,107,200 / 223 = 58,776.7 s = 16.33 h.
```

At approximately 9 KiB per event, raw storage would be:

```text
117,964,800 KiB = 115,200 MiB = 112.5 GiB
```

before manifests, indices, temporary files, or compression.

The predeclared 100,000-candidate calibration at 128 points adds 12,800,000
candidates, or another optimistic 15.94 serial hours. If second-stage
unweighting has efficiency `epsilon`, selected-event candidate cost is at
least `16.33 / epsilon` serial hours. At `epsilon=0.5`, calibration plus
selected-event generation is approximately 48.6 serial hours. Candidates
should be streamed rather than persisted when reproducibility permits.

A smaller `64 * 50 * 1024 = 3,276,800`-event scale is still about 4.08 raw
serial hours and 28.1 GiB. None of these estimates includes:

- APFEL++ construction and grid-export time per point;
- LHAPDF/Pythia startup and initialization;
- support vetoes;
- unweighting inefficiency;
- failed or retried shards;
- validation replicas;
- filesystem and compression overhead;
- parallel scaling or contention.

The nine-point Stage 3 smoke design at 100 accepted events per point is 900
events: an optimistic 4.0 seconds of event production and about 7.9 MiB before
startup, artifact construction, vetoes, and manifests. The nine-anchor Stage 4
calibration is 900,000 streamed candidates: an optimistic 67.3 minutes and
7.72 GiB if candidates were unnecessarily persisted. Final Stage 4 validation
sample sizes must be chosen by the predeclared power calculation, not by these
arithmetic examples.

Stage 5 must measure each term. Parallel speedup is not assumed.

Parameter points and shards may run as isolated processes after their
immutable artifacts pass validation. A scheduler must limit memory and local
disk explicitly; it may not share mutable Pythia state. Each completed shard
is published atomically with a content hash. Restart discovers completed
manifests, verifies their bytes and seed identities, and schedules only missing
logical shards. A failed shard retains its failure manifest and attempt count;
replacement is a versioned retry, never an in-place rewrite.

## 13. Future data and manifest schemas

Future implementation must version and validate:

- `pdf_parameter_point`: canonical parameters, baseline, support, sum rules,
  evolution inputs, and point hash;
- `pdf_artifact`: every file hash, grid layout, APFEL++ and LHAPDF versions,
  round-trip results, and clean provenance;
- `generation_run`: process/cuts, point ID, support policy, seeds, attempts,
  veto counters, query bounds, weights, cross sections, and command;
- `sampling_run`: calibration sample identity, fixed bound, candidate and
  selected counts, every violation, inclusion probabilities, and RNG identity;
- `event_shard`: point/split/shard IDs, source and sampling run IDs, event
  range, feature schema, content hash, and failure/retry state;
- `pseudo_experiment`: ordered event-shard slices, fixed `N`, shape/rate
  contract, split, assembly seed, and content hash;
- `dataset`: included point and pseudo-experiment IDs, split policy, schema
  hashes, aggregate counts, dependency versions, and decision provenance;
- `study_decision`: stage outcomes, reasons, metrics, and authorization state.

Default observed ML features must exclude parameter values and IDs, artifact
paths/hashes, seeds, generator weights, inclusion probabilities,
`GenPdfInfo`, hard flavor, support-veto reasons, timestamps, cross-section
normalization in the shape-only study, and other generator-only provenance.
Feature leakage tests are required before any neural stage.

## 14. Explicit design decisions

| ID | Status | Decision |
| --- | --- | --- |
| D-001 | ACCEPTED | Direct event regeneration replaces nominal-pool reuse. |
| D-002 | ACCEPTED | The MVP family is a multiplicative deformation of CT18NLO member 0. |
| D-003 | REJECTED | An independent analytic PDF basis is not the MVP family. |
| D-004 | ACCEPTED | `Q0` is the metadata-derived CT18NLO boundary, 1.295 GeV for v1. |
| D-005 | REJECTED | The rounded `Q0 = 1.30 GeV` proposal is not used. |
| D-006 | ACCEPTED | `theta = (delta_v, lambda_sea)` is the two-dimensional family. |
| D-007 | REQUIRES EXPERIMENT | The roadmap parameter box is a pilot box, not a frozen prior. |
| D-008 | ACCEPTED | Valence-number constraints are imposed analytically by normalization. |
| D-009 | ACCEPTED | The gluon normalization enforces the momentum sum rule. |
| D-010 | ACCEPTED | The light sea uses one common exponential scaling. |
| D-011 | ACCEPTED | Heavy flavors are generated by variable-flavor evolution from the verified boundary. |
| D-012 | REJECTED | Negative PDFs are not repaired by clipping. |
| D-013 | ACCEPTED | The family has explicit compact `x` support and no extrapolation. |
| D-014 | ACCEPTED | APFEL++ is the authoritative evolution engine. |
| D-015 | ACCEPTED | A generated, immutable LHAPDF grid is the direct-generation artifact. |
| D-016 | REJECTED | Separate numerical PDF definitions for APFEL++ and Pythia are not allowed. |
| D-017 | REJECTED | A custom Pythia PDF is not the primary family representation. |
| D-018 | REQUIRES EXPERIMENT | A diagnostic Pythia adapter may be needed to prove all-consumer support. |
| D-019 | ACCEPTED | Point identities use canonical serialization and full SHA-256 hashes. |
| D-020 | ACCEPTED | Generated PDF grids remain ignored cache artifacts. |
| D-021 | ACCEPTED | Scientific production requires clean Git provenance. |
| D-022 | ACCEPTED | Generation, calibration, sampling, and validation seed families are disjoint. |
| D-023 | REJECTED | Events are never reused across parameter points. |
| D-024 | REJECTED | Pythia dynamic maximum increases are not the MVP sampling strategy. |
| D-025 | REQUIRES EXPERIMENT | Fixed-bound second-stage accept-reject is the primary MVP sampling hypothesis. |
| D-026 | DEFERRED | Weighted empirical event sets are not the primary neural input. |
| D-027 | REJECTED | Weight clipping, winsorization, removal, and overwriting are prohibited. |
| D-028 | ACCEPTED | The first dataset contract is fixed-`N`, normalized, and shape-only. |
| D-029 | DEFERRED | Poisson event counts and rate-aware inference are a later extension. |
| D-030 | ACCEPTED | Every Pythia PDF consumer must obey or expose the strict support contract. |
| D-031 | ACCEPTED | Hard flavor and `GenPdfInfo` remain provenance, not observed features. |
| D-032 | ACCEPTED | Inclusive NC e-p results cannot be described as full-flavor separation. |
| D-033 | ACCEPTED | No later validation stage begins after a failed prerequisite. |
| D-034 | REQUIRES EXPERIMENT | Central-member reconstruction tolerances must be demonstrated, not assumed. |
| D-035 | REQUIRES EXPERIMENT | Throughput, artifact cost, unweighting efficiency, and storage must be measured before scale-up. |
| D-036 | ACCEPTED | APFEL++ and the artifact use the CT18 metadata-derived NLO `alpha_s` contract. |
| D-037 | ACCEPTED | LHAPDF interpolation is explicitly `logcubic`; extrapolation uses the fail-closed `error` policy. |
| D-038 | ACCEPTED | The nine center/axis/corner points are the mandatory pilot anchors. |
| D-039 | ACCEPTED | Out-of-domain theta values fail and are never projected into the pilot box. |
| D-040 | DEFERRED | Charged-current, e+ p, tagged, and multi-energy channels may motivate later flavor directions. |

## 15. Risks, unresolved questions, and revisit triggers

### Risks

- Boundary reconstruction at `Q0` may not reproduce the central set within the
  declared tolerance after exact sum-rule normalization.
- The common sea deformation can force a nonpositive gluon normalization at a
  pilot boundary.
- Threshold interpolation and the generated `alpha_s` table may disagree
  between direct APFEL++ evaluation and LHAPDF.
- Pythia shower consumers may issue queries outside the strict artifact
  domain.
- The Pythia source weight may not admit an efficient, stable fixed envelope.
- Direct-generation storage and wall time may exceed available resources after
  unweighting losses.
- The two inclusive-channel directions may be weakly identifiable or strongly
  degenerate.

### Unresolved questions

- Does the complete pilot box pass positivity and evolution stability?
- Can a deterministic `lhagrid1` writer meet the round-trip tolerance on every
  threshold and flavor?
- Is the diagnostic adapter sufficient to expose all Pythia PDF queries
  without changing process physics?
- Does a predeclared fixed envelope exist with useful unweighting efficiency?
- What measured CPU, startup, artifact, and compressed-storage budgets are
  required?
- Is the two-parameter family distinguishable using only the eventual
  observed-feature schema?

Each question maps to Stages 0–5. A failed answer triggers a new ADR or a
scientific scope decision; it is not repaired by relaxing a tolerance after
observing results.

Rejected architecture choices may be revisited only after the selected path
fails its declared stage, the failure is documented, and a new ADR compares
the changed tradeoffs. Deferred extensions require new channels or a
separately approved inference objective.

## 16. Planned implementation subphases

These are future, separately reviewed tasks.

### Phase 1B-D0 — family mathematics

Planned scope: metadata access, boundary construction, quadrature, positivity,
sum rules, parameter scan, and schemas.

- Candidate files: `src/physics/continuous_pdf.rs`,
  `src/continuous_pdf_cli.rs`, `tests/continuous_pdf_family.rs`, and
  `schemas/pdf_parameter_point.schema.json`.
- Dependencies: reuse managed-lhapdf and existing serialization first; any new
  quadrature or hashing crate requires a separate dependency review and pinned
  lockfile change.
- Tests: authoritative metadata, Q/Q2 handling, center/corner construction,
  independent quadrature, exact canonical float encoding, stable hashes,
  positivity, and all construction failures.
- Artifacts: a small JSON pilot-box scan and Stage 0 decision; no PDF grids or
  events.
- Gate: all Stage 0 criteria pass.
- Stop: invalid metadata, a nonpositive normalization, unresolved negative
  PDFs, unstable integrals, or an invalid pilot box.

Model recommendation: GPT-5.6 Sol — High.

### Phase 1B-D1 — evolution and artifact

Planned scope: APFEL++ family evolution, deterministic LHAPDF writer,
round-trip loader, content-addressed cache, lock protocol, and artifact
manifests.

- Candidate files: `physics-engine/include/continuous_pdf_artifact.hpp`,
  `physics-engine/src/continuous_pdf_artifact.cpp`,
  `physics-engine/src/continuous_pdf_artifact_cli.cpp`,
  `src/physics/pdf_artifact.rs`, `tests/pdf_artifact.rs`, and
  `schemas/pdf_artifact.schema.json`.
- Dependencies: installed APFEL++ 4.8.0 and LHAPDF 6.5.6; prefer the C++ and
  filesystem facilities already in use. A checksum or lock dependency must be
  justified and version-pinned.
- Tests: APFEL callback conventions, evolution order/thresholds, every
  flavor/knot round-trip, off-knot comparison, sum rules, byte
  reproducibility, concurrent builders, interrupted writes, and corrupt cache
  rejection.
- Artifacts: ignored one-member grid fixtures generated during tests, a small
  checked-in manifest/report only when deterministic and license-safe, and a
  Stage 1 decision.
- Gate: all Stage 1 criteria pass against independent APFEL++ values and the
  central baseline.
- Stop: a second numerical family definition, cache race, metadata loss, or
  any unexplained serialization discrepancy.

Model recommendation: GPT-5.6 Sol — High.

### Phase 1B-D2 — Pythia coupling and support

Planned scope: select generated artifacts in the C++ generator, instrument
every PDF consumer, extend versioned manifests, and prove that serialized
`GenPdfInfo::scale` and strict support semantics remain correct.

- Candidate files: focused changes to
  `physics-engine/include/pythia_dis_generator.hpp`,
  `physics-engine/src/pythia_dis_generator.cpp`,
  `physics-engine/src/pythia_dis_cli.cpp`,
  `src/physics/pythia.rs`, `src/physics/hepmc3.rs`,
  `tests/continuous_pdf_generation.rs`, and
  `schemas/generation_run.schema.json`.
- Dependencies: existing Pythia 8.312, HepMC3 3.03.00, and LHAPDF 6.5.6;
  adding a second PDF library or representation is prohibited.
- Tests: configuration serialization, artifact selection, hard/shower
  consumer identity, support query counters, strict boundary cases,
  `GenPdfInfo::scale` identity, Q/Q2 evaluation, veto accounting, and streaming
  parser compatibility.
- Artifacts: small deterministic test fixtures, Stage 2 coupling report, and
  Stage 3 smoke report; generated diagnostic runs remain ignored.
- Gate: Stage 2 coupling and Stage 3 direct-smoke criteria pass with no hidden
  boundary freezing.
- Stop: an unidentified consumer, unsupported query, artifact mismatch, or a
  need to change process physics rather than define an explicit
  selection/adapter contract.

Model recommendation: GPT-5.6 Sol — High.

### Phase 1B-D3 — sampling experiment

Planned scope: characterize weights, calibrate fixed envelopes with disjoint
seeds, test second-stage accept-reject, compare weighted and unweighted
observables, and decide the event-set sampling contract.

- Candidate files: `src/physics/event_sampling.rs`,
  `src/event_sampling_cli.rs`, a new `analysis/direct_sampling/` package,
  `tests/event_sampling.rs`,
  `analysis/tests/test_direct_sampling.py`, and
  `schemas/sampling_run.schema.json`.
- Dependencies: use the existing deterministic RNG and analysis stack where
  possible; any distribution-test package must be pinned and justified.
- Tests: disjoint seed namespaces, fixed-bound freezing, every failure path,
  Bernoulli reproducibility, zero clipping, streaming operation, weighted
  versus unweighted metrics, power reporting, and shape/rate separation.
- Artifacts: small metrics/decision JSON and plots referenced by the report;
  candidate streams and selected event pools remain ignored.
- Gate: all Stage 4 criteria pass.
- Stop: a bound breach, invalid weight, distribution failure, insufficient
  power, or unproven source-weight semantics. A failure requires a new sampling
  ADR and never authorizes clipping or threshold tuning.

Model recommendation: GPT-5.6 Sol — High.

### Phase 1B-D4 — direct anchor closure

Planned scope: central, edge, and corner points; independent replicas;
direct-versus-direct closure; artifact/cache reproducibility; and shape-only
sensitivity maps.

- Candidate files: `src/direct_pdf_closure_cli.rs`,
  `analysis/direct_closure/`, `tests/direct_pdf_closure.rs`,
  `analysis/tests/test_direct_closure.py`, and
  `schemas/event_set.schema.json`.
- Dependencies: no inference framework; reuse existing Rust streaming and
  Python validation dependencies unless a reviewed statistic requires one.
- Tests: point/replica seed isolation, cache identity, restart behavior,
  direct-direct and central-baseline metrics, feature leakage, manifest
  compatibility, and negative-sensitivity reporting.
- Artifacts: compact closure metrics, sensitivity maps, and Stage 5 report;
  raw anchor event pools remain ignored.
- Gate: the closure portion of Stage 5 passes without cross-point reuse.
- Stop: unexplained replica differences, leakage, unsupported queries,
  unreported veto/rate changes, or a failure to reproduce manifests.

Model recommendation: GPT-5.6 Sol — High.

### Phase 1B-D5 — production theta design and dataset generation

Planned scope: measured resource pilot, sharding/restart tests, final dataset
schema, theta/split policy, storage plan, and go/no-go decision. Production
generation is contingent on an explicit `scale_up_allowed=true` Stage 5
decision; the resource pilot alone does not authorize it.

- Candidate files: `src/direct_dataset_cli.rs`,
  `schemas/event_shard.schema.json`,
  `schemas/pseudo_experiment.schema.json`,
  `schemas/direct_dataset.schema.json`, focused restart/integrity integration
  tests, and a Phase 1B-D completion report.
- Dependencies: no neural framework additions; compression or object-store
  dependencies require measured need and a separate operational review.
- Tests: shard interruption/restart, collision detection, content hashes,
  split isolation, corruption handling, disk budget, and proof that generated
  outputs stay untracked.
- Artifacts: resource projection, approved theta/split design, final schemas,
  manifest index, and explicit `scale_up_allowed` decision. Pilot and any
  subsequently authorized production event data remain ignored.
- Gate: Stage 5 establishes a resource-bounded, reproducible plan before any
  large corpus or neural inference work.
- Stop: a resource overrun, non-reproducible resume, seed collision, artifact
  corruption, or any failed prerequisite. Generated pools remain uncommitted.

Model recommendation: GPT-5.6 Sol — High.

## 17. Exact implementation gate and completion state

This document is a design artifact only. No continuous family, APFEL++ grid
exporter, Pythia coupling, unweighting algorithm, event corpus, or neural model
has been implemented. The single next scientific step after design approval is
Phase 1B-D0: validate the parameterized boundary condition and candidate pilot
box.
