# Phase 2B preauthorization blocker resolution V1

## Result

```text
OUTCOME = BR5_MULTIPLE_BLOCKERS_REMAIN
V4_CREATED = false
PHASE2B_AUTHORIZED = false
PHASE2B_EXECUTION_STATUS = NOT_EXECUTED
PHASE2C_AUTHORIZED = false
```

This is a blocker-resolution record, not an execution authorization review. The
authoritative artifact is
[`contracts/phase2b_blocker_resolution_v1.json`](contracts/phase2b_blocker_resolution_v1.json).

No DIS structure function, alpha comparison, bridge validation, MassiveDIS or
FONLL benchmark, raw-rate scan, normalization integral, convergence study,
event, dataset, detector, or neural operation was executed. Historical Phase 2A
remains `COMPLETE/INCONCLUSIVE` and ADR-013 remains Proposed. The V3 artifact
was verified byte-for-byte at
`78a029686489e9712e65ef6f9df3263b4821f96de0ee9873a910dee31f307e06` and was not
modified.

## What this task set out to do

The accepted V3 result `V3R6_MULTIPLE_BLOCKERS_REMAIN` left three blocker
families. This task attacked all three with primary-source review, exact
symbolic derivation, and non-DIS software validation. Real progress was made in
each. It was not enough to reach `BR1`, and the record below says exactly where
each family stops and why.

## Workstream A — continuous alpha_s certification

### The exact CT18 function is now derived, not described

V3 called provider A an "exact LHAPDF cubic-Hermite interpolation in
`z=ln(Q^2)`". That is nearly right and materially incomplete. From
`AlphaS_Ipol.cc`, `KnotArray.h` and `AlphaS.h` in LHAPDF 6.5.6:

- `alphasQ(Q)` is `alphasQ2(Q*Q)` with one rounded binary64 square.
- The knot coordinate is the **natural** logarithm of `Q^2`; the base-ten logs
  appear only in the low-`Q^2` extrapolation branch, which strict support makes
  unreachable.
- CT18NLO has 37 pairwise-distinct squared knots, so `_setup_grids` builds
  **exactly one** subgrid. There are no threshold subgrids for this set.
- Slopes are finite differences with respect to `ln Q^2`: forward/central in the
  first cell, central/backward in the last, central/central otherwise.
- Line 71 returns `DBL_MAX` whenever the assembled cubic has magnitude at least
  `2`. **The provider is therefore not a continuous function.** `Utils.h` imports
  `namespace std`, so the `abs` there is the `double` overload and there is no
  integer-truncation trap; but any enclosure must decide that magnitude branch
  for a whole cell before it may use the smooth expression. V3 did not record
  this clamp.

Locally installed CT18NLO bytes matched the frozen `.info` and member hashes
exactly, and the 21 in-domain knots, 24 breakpoints and 23 root intervals of the
V3 partition were reproduced independently.

### The exact APFEL mathematics is now derived, and `4*pi` is resolved

All five V3-recorded APFEL file hashes were re-verified. From
`AlphaQCD.f`, `a_QCD.f` and `consts.h`:

```fortran
Q2 = Q * Q / kren
AlphaQCD = 4d0 * pi * a_QCD(Q2)      ! pi = 3.1415926535897932385d0
```

That closes V3's open item outright. The `pi` parameter is the nearest binary64
to π (`400921fb54442d18`), `4d0 * pi` scales by a power of two and is exact, and
Fortran's left-to-right evaluation puts the single rounding on the final
product. A later test can call `AlphaQCD(Q)` directly and never form the
conversion by hand.

Two further exact facts matter and were not in V3:

- `AS_EXACT` updates with `SXTH = 0.166666666666666D0`, hex `3fc555555555553d`.
  That is **not** one sixth (`3fc5555555555555`); the relative deviation is
  `-3.997e-15`. Any bitwise-replay claim must carry the literal.
- Flavour selection is asymmetric: `nff` advances on `mur2 >= mur2th(k)` while
  `nfi` advances on `mur20 > mur2th(k)`. With `nfMaxAlpha = 5` the top threshold
  is unreachable, so the V3 sketch of an `mt` split is unnecessary. With
  `kren = 1` and unit matching-scale ratios, `dlog(kappa) = 0` and the NLO
  threshold matching is the **exact identity**.

### Validated ODE integration turns out not to be required

This is the methodological result of the workstream. `AS_EXACT` is a fixed
ten-step recursion with no adaptivity, no step control and no error estimate.
Given an enclosure of `DLR`, the entire computation is a finite composition of
`+`, `-` and `*`. Ordinary interval evaluation already encloses everything the
recursion can produce; interval Runge–Kutta with a local truncation bound and
Taylor-model integration are both answers to a question the frozen contract does
not ask.

The distinction that makes this sound is worth stating plainly: the enclosure
bounds **the algorithm's output**, not the exact solution of the beta-function
differential equation. Those are different objects, and only the first is the
load-bearing one under the accepted sign contract.

### The backend is bound

Because the Hermite cubic, the beta right-hand side and the RK4 recursion need
only the four rational operations, the external backend requirement collapses to
a single transcendental: the natural logarithm.

```text
ALPHA_BACKEND_BOUND
  rational core   analysis/validation/phase2b_interval_oracles.py
                  exact Fraction endpoints, outward dyadic normalisation,
                  RN(z) within u*|z| + eta of z, u = 2^-53, eta = 2^-1075
                  standard library only
  transcendental  python-flint 0.6.0 Arb ball arithmetic
                  cp310 wheel sha256 4a99082434cbc568c7ad55fe6810eb832e04548af3d8130539ec4b78b0cc5cb9
```

`mpmath` and `mpmath.iv` are rejected, as the accepted records already require.
MPFI is acceptable in principle but has no maintained Python binding with a
reproducible wheel identity. The probe ran under CPython 3.12 because the frozen
3.10.20 is not installed here, so the cp310 wheel identity is bound but was not
itself exercised.

### Where Workstream A stops

Both providers call the platform natural logarithm, and the accepted sign
contract makes the **implemented** finite-precision object the load-bearing one.
Enclosing an idealised real-arithmetic function is therefore not sufficient, and
enclosing the implemented one needs a bound on that libm routine. From glibc
2.39 source:

- `sysdeps/ieee754/dbl-64/e_log.c` states a worst-case error around `0.507` ULP
  on the near-one path and `0.519` ULP with FMA or `0.520` ULP without. That is
  the implementers' own error analysis, not a machine-checked proof.
- `sysdeps/x86_64/fpu/multiarch/e_log.c` resolves the symbol through an **ifunc**
  chosen at load time among SSE2, AVX, FMA4 and FMA variants, and the source
  itself documents different rounding for the FMA and non-FMA paths. The
  mathematical function realised by `log` depends on the CPU. The inspection
  host advertises `fma` and `avx2`; a host without FMA would select a different
  variant.

So the consistency **claim** is `ALPHA_CLAIM_BOUNDED_NUMERICAL_CONSISTENCY` —
exact identity is the wrong claim for two genuinely different finite algorithms
and could never pass — but its **level** has no source. The massless `1e-5` and
MassiveDIS `0.001` figures are comparator-local and non-transferable, machine
epsilon is not a physics requirement, and the research-question record selects
no metric. The structurally correct fallback — record the discrepancy and lean
on the reference-closure gates instead of an alpha threshold — cannot be adopted
because every one of those gates is itself blocked.

No tolerance was manufactured, and A7 was deliberately not serialized: writing a
PASS/FAIL/INCONCLUSIVE algorithm with a resource ceiling on top of two
unresolved inputs would present an untestable design as a finished one.

## Workstream B — executable independent references

### MassiveDIS: source bound, benchmark not reconstructable

`massiveDISsFunction` v1.2 was retrieved and inspected
(`ccdcbc5147da8532cf80c41d890cc117adee10d3a9141164de752780cfd8f9f2`). The build
recipe, the `F(x, Q, order, scheme, sfunction, muF/Q, muR/Q)` entry point, full
NC `F1/F2/F3/FL` coverage, the mass and scale setters, and the intrinsic-charm
terms are all bound. A finite internal-work ceiling is now derivable: the code
calls `gsl_integration_qags` with a subdivision limit of 1000 and
`gsl_integration_qagiu` with 100000, giving at most 21,000 and 1,500,000
integrand evaluations per call respectively.

Two findings block it anyway:

- The published comparison uses `NNPDF30_nlo_as_0118_IC5`. The LHAPDF 6.5.6
  index contains **no** set with an `IC` suffix. The published configuration is
  not reconstructable, and the published evidence is figure-only, so no exact
  reference coordinates or values exist either.
- Every internal call in `src/massiveDIS.cc` passes `NULL` for the GSL error
  pointer and precedes it with `gsl_set_error_handler_off()`. An unmodified
  MassiveDIS therefore returns **no** error interval and does not signal
  non-convergence. Retaining one requires patching the comparator, which changes
  its frozen identity.

Result: `FONLL_REF_PUBLISHED_ONLY`. A bounded search for a stronger comparator
found `yadism`, whose own documentation states FONLL is not provided explicitly
and only FFNS, FFN0 and ZM-VFNS ingredients are available; assembling FONLL-A
from those and matching APFEL's damping was not completed here, and its NNPDF
lineage makes the independence claim arguable. APFEL++ is rejected as an
independent comparator outright.

### Massless: the reference side is now recoverable

New evidence beyond V3: the publication points at a released benchmark program,
`code/StructureFunctionsJoint.cc` in
`alexanderkarlberg/n3lo-structure-function-benchmarks`
(`199f7e90b057083a2cb68d4e6649cc527c30ba27bcb09977641acc87a457a5fe`). It fixes
`Q0 = sqrt(2.0)` in binary64, `xmuR = xmuF = 1`, the HOPPET settings, the
four-subgrid APFEL++ grid, and the coupling tabulation. The publication itself
states the active-flavour state V3 recorded as missing: `nf = 3` at the initial
scale, because the charm threshold sits above `Q0`.

It also exposes a prose-versus-code discrepancy worth recording. The paper says
the charm mass is `sqrt(2) + 1e-9`; the released code holds the literal
`1.414213563`, which exceeds `sqrt(2)` by `6.269e-10`. The executable truth and
the prose differ, and a future test must bind the literal. That closes V3's
question about how `sqrt(2)+1e-9` is parsed by showing the reference never
parsed it.

The acceptance rule needs no invention: containment in the published
displayed-digit interval. What still blocks the gate is the **candidate** side —
the accepted APFEL 3.1.1 grid and interpolation settings for such a run are not
frozen, the accepted bridge contract pins the callback scale to the CT18
boundary at `1.295 GeV` and does not cover a `sqrt(2) GeV` toy-PDF run, and no
finite work cap follows until both exist. Result: `MASSLESS_REF_PARTIAL`.

### Reference graph

Load-bearing nodes still validated only by self-convergence or not at all:
`complete_implemented_nc_rate`, `massive_contribution`,
`fonll_difference_matching`, `alpha_s`, both quadrature paths, and both
assembly nodes. A future `V4 COMPLETE` result may not contain a load-bearing
unvalidated node, and several remain.

## Workstream C — grid and quadrature remainder

### Is a rigorous remainder required? Neither option is currently available

A rigorous remainder needs an integrand that can be evaluated in interval
arithmetic, or at least a certified derivative bound of known order. The
accepted integrand is the frozen APFEL FONLL-A binary64 rate wrapper: one
binary64 number per point, no interval extension, no derivative enclosure, no
modulus of continuity. Interval Gauss rules, validated adaptive quadrature, Arb
ball integration and Taylor-model quadrature all share that precondition, and
none of them can be applied to such a black box. Demanding `C1A` would mean
replacing the accepted implementation — the same reason AS1 was rejected.

So the empirical route is the only structurally available one. It is
unanchored. The load-bearing object is `q = r/Z`; a relative error in `Z` biases
the per-event log density, and over an event set of size `N` the log-posterior
bias scales like `N` times that relative error. A sufficient accuracy for `Z`
therefore follows from a declared `N` and a declared acceptable posterior or
coverage distortion. The accepted research-question record fixes no `N`,
explicitly states that no information-content or calibration metric is selected,
and declares no acceptable distortion. No target was manufactured.

### Successive differences do not bound anything

Non-DIS tests on functions with known exact integrals validate the rule
mechanics. Gauss–Legendre 16/32/64 and Clenshaw–Curtis 17/33/65 reproduce
polynomial and exponential integrals to rounding, converge on a smooth rational,
and both stall on a near-endpoint pole.

The decisive case is an entire integrand, `exp(-((x-c)/w)^2)` with `c = 0.1824`
and `w = 1e-4`, whose centre is at least `0.01269` from every node of all six
rules:

| rule | level 1 | level 2 | level 3 | d1 | d2 |
| --- | --- | --- | --- | --- | --- |
| Gauss–Legendre 16/32/64 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Clenshaw–Curtis 17/33/65 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

The exact integral is `1.7725e-4`. Both paths report perfect self-convergence
**and** perfect mutual agreement while both are entirely wrong, and the
cross-path difference is exactly zero. That settles the general question:
successive-difference agreement is not a remainder bound, and an independent
second rule that shares the node-placement problem does not rescue it. It is a
statement about the rule, not a prediction about the DIS integrand.

### The grid gate does not currently measure anything

`TEST_GRID_CONVERGENCE` conflates three things. Pointwise validation coverage is
real: the levels decide how many points the sign gate examines. Discretisation
error is **not applicable** — nothing is interpolated between tested points, so
there is no discretisation being performed and no error to estimate. A continuum
claim is unsupported, as the accepted sign contract already says.

As specified in V3 the gate does not map to a scientifically meaningful
quantity, and it needs replacement rather than a threshold. The recommended
successor redesign is an exact coverage and consistency audit: each coarse
level's nodes bitwise present in every finer level, every shared point carrying
a bitwise identical cached rate, and the required augmentation points present at
every level. The first of those was checked here — the 17/33/65 geometric grids
**are** bitwise nested on both the `x` and `Q^2` axes, while a 16/32/64
hierarchy is not, which shows the property has to be tested rather than assumed.
V3 itself was not edited.

## Workstream D — execution environment

| Item | State |
| --- | --- |
| CPython 3.10.20 | source hash bound; executable **not** bound, host has 3.12.3 only |
| NumPy 2.2.6 / SciPy 1.15.3 / mpmath 1.3.0 | cp310 wheel hashes bound |
| python-flint 0.6.0 | cp310 wheel hash bound; not a repository requirement |
| OS / kernel / glibc of inspection host | Ubuntu 24.04.3, WSL2 6.6.87.2, glibc 2.39-0ubuntu8.8 — **not** the frozen runtime |
| Compiler identity | not bound |
| libm identity | **not bound**; resolved by ifunc from CPU features |

```text
REPRODUCIBILITY = ENVIRONMENT_REPRODUCIBILITY_UNRESOLVED
```

A bitwise claim is not made and would be wrong: it would require a frozen CPU
feature set in addition to frozen software, because the selected libm variant
and its documented rounding differ between FMA and non-FMA hosts.

The weaker `NUMERICALLY_REPRODUCIBLE_WITH_FROZEN_SOFTWARE_IDENTITY` is also not
claimed. It asserts that freezing the software identity determines the numbers,
and the ifunc finding shows it does not: the same frozen LHAPDF, APFEL and glibc
versions realise different logarithms on hosts with and without FMA. It would
additionally need a declared agreement tolerance, which no accepted record
supplies, so it is not a checkable statement. Unresolved is the honest label.

## Resource model

Categories are reported in their own units and are never summed.

| Category | Unit | Value |
| --- | --- | ---: |
| physics evaluator calls | frozen rate evaluations | 63,882 |
| alpha interval cells | interval cells | null |
| alpha RHS evaluations | interval beta RHS evaluations | null |
| external reference calls | comparator invocations | null |
| bridge evaluator calls | callback attempts | 1,045 |
| quadrature integrand calls | integrand evaluations | 98,811 |
| analytic unit-test calls | analytic cases | 216 |
| storage bound | emitted records | null |

An aggregate remains `BLOCKED_NOT_DERIVABLE`. Three categories are explicitly
`null` rather than filled with a plausible number.

## Remaining blockers

| ID | Family | Missing |
| --- | --- | --- |
| `BLOCKER_ALPHA_IMPLEMENTED_LOG_ENCLOSURE` | A | rigorous enclosure of the platform `log`, plus a frozen CPU feature set |
| `BLOCKER_ALPHA_CONSISTENCY_CRITERION` | A | a defensible nonzero consistency level, or an accepted propagation-only gate |
| `BLOCKER_FONLL_REFERENCE_EXECUTION_SPEC` | B | an executable independent FONLL-A comparator with a matched configuration and rule |
| `BLOCKER_MASSLESS_CANDIDATE_SIDE` | B | frozen APFEL grid settings, a `sqrt(2) GeV` bridge, a work cap |
| `BLOCKER_PROJECT_PRECISION_TARGET` | C | a declared accuracy requirement for the normalized law |
| `BLOCKER_GRID_GATE_SEMANTICS` | C | a gate whose quantity is scientifically meaningful |
| `BLOCKER_NUMERICAL_RUNTIME_IDENTITY` | D | executable interpreter, libm and CPU feature identity |

## Why no authorization review and no V4

`BR1_ALL_PREAUTH_BLOCKERS_RESOLVED` was not independently and positively
established, so no successor plan was created. Creating one would present
unresolved specifications as complete. An authorization review conducted now
could only restate these blockers, so none is warranted.

## Phase completion report

All commands ran in WSL Ubuntu from the repository root. No native physics
validation was performed, so `scripts/pythia_env.sh` was not sourced. The
dependency tree was installed outside the repository at
`/home/mrxn/p2b-blocker-site` and is not a deliverable.

| Command | Result |
| --- | --- |
| `python3 scripts/validate_phase2_fonll_a_contract_amendment.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan.py` | PASS |
| `python3 scripts/validate_phase2b_execution_authorization_review.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan_v2.py` | PASS |
| `python3 scripts/validate_phase2b_execution_authorization_review_v2.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan_v3.py` | PASS |
| `python3 scripts/validate_phase2_reduced_nc_dis_roadmap.py` | PASS |
| `python3 scripts/validate_phase2b_blocker_resolution.py` | PASS |
| focused new suites (blocker resolution, interval oracles, grid oracles) | PASS, 127 tests |
| `python3 -m pytest -q analysis/tests/` with the pinned tree | PASS, 731 tests |
| `cargo fmt --all -- --check` | PASS |
| `git diff --check` | PASS |

The machine artifact SHA-256 is
`d66a1bbcb67b7105f489233bfd292c7064bcda35ef8c6f8dbc0dec41aa6da8de`.

One correction was made during this task rather than hidden. An adversarial test
showed the validator would have accepted a MassiveDIS entry upgraded to
`FONLL_REF_EXECUTABLE_FULLY_SPECIFIED` without requiring a reconstructable
configuration, a bound scheme correspondence, an error certificate or a work
bound. The validator was strengthened; no scientific rule was weakened.

Two epistemic classifications were **downgraded** during self-review, not
strengthened. The environment classification moved from
`NUMERICALLY_REPRODUCIBLE_WITH_FROZEN_SOFTWARE_IDENTITY` to
`ENVIRONMENT_REPRODUCIBILITY_UNRESOLVED`, and the glibc source locator gained an
explicit note that the bytes were retrieved from a GitHub mirror rather than
upstream.

A note on the toy evidence, recorded rather than omitted: the truncated
one-sixth literal shifted the toy recursion midpoint by `1.31e-17`, which is
inside that configuration's `2.33e-16` accumulated rounding envelope. The
literal is a real deviation from one sixth and matters for any bitwise-replay
claim, but this toy configuration does not by itself demonstrate a numerically
significant effect.

## Next step

Two decisions gate everything else, and neither is more source review:

1. Will the project certify alpha against a declared and clearly qualified
   platform-logarithm bound on a frozen CPU, or does it require an interval
   re-implementation of the selected libm routine?
2. What accuracy does the normalized simulator law actually require? Declaring
   the event-set size and an acceptable posterior or coverage distortion yields
   an accuracy for `Z`; the alternative is removing the normalization-accuracy
   claim from the paper boundary.

Both are scientific decisions about the claim. Until they are recorded, a
successor preauthorization plan cannot be complete.
