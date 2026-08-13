# Phase 2B preauthorization validation plan V3

## Result

```text
OUTCOME = V3R6_MULTIPLE_BLOCKERS_REMAIN
PLAN_COMPLETENESS = BLOCKED
PHASE2B_AUTHORIZED = false
PHASE2B_EXECUTION_STATUS = NOT_EXECUTED
```

V3 is a scientific successor to the immutable FONLL-A amendment, v1 plan,
AR2-v1, v2 plan, and AR2-v2 review. It removes the invalid global budget and
equal split, advances the alpha and bridge designs, closes the raw-sign design,
freezes exact dependency inputs, and records the remaining blockers without
inventing acceptance thresholds or executable identities. The
authoritative record is
[`contracts/phase2b_preauthorization_validation_plan_v3.json`](contracts/phase2b_preauthorization_validation_plan_v3.json).

This document is a plan revision only. No DIS structure function, alpha
comparison, bridge validation, raw-rate scan, normalization integral,
convergence study, event, dataset, detector, or neural operation was executed.

## Immutable lineage and scientific boundary

V3 binds these predecessor SHA-256 values:

- FONLL-A amendment: `10cf19fedcdfe1b94e18ff89d1ae09514a31b8e0f6b055beeb729d61b6c32da8`
- v1 preauthorization plan: `7eb8834eb8435532a85bd7d49b173b03e57a268f69f9676e0effbd877903672b`
- AR2-v1: `03d8119efb819b7a8b51161d5f2ce58fe59dd385b63f2dbfd6203692dac1f9e2`
- v2 preauthorization plan: `a79e87538fae4d3f20793756b321af4d7521c1277ee08580e1b773a7452a9cd2`
- AR2-v2: `d7826158718ea0c4e5d3fc7c0f60829913e9634c98c45d2316c63bffdce47821`

Historical Phase 2A remains `COMPLETE/INCONCLUSIVE`; ADR-013 remains
Proposed. The inference unit remains a set of events
`D={event_1,...,event_N}`, with long-term target `p(theta_PDF | D)`. V3 does
not claim an instantaneous one-event proton PDF, full flavor separation from
one inclusive NC channel, or generator truth as default observed features.

## Gate-local architecture

There is no `T_external`, no complete-rate `0.001` allowance, and no equal
eight-way allocation. Gates are noncommensurable and cannot compensate one
another.

| Gate | V3 planning state | Local meaning |
| --- | --- | --- |
| G1 FONLL component reference | `BLOCKED_PREAUTH_SPECIFICATION` | Independent comparator/configuration only |
| G2 massless reference | `BLOCKED_PREAUTH_SPECIFICATION` | Published table frozen; candidate interval/heavy-flavor/work specification incomplete |
| G3 alpha_s consistency | `BLOCKED_PREAUTH_SPECIFICATION` | Provisional continuous-certificate design only |
| G4 PDF bridge identity | `FULLY_SPECIFIED_NOT_EXECUTED` | Exact identity and one-multiply transport |
| G5 EW/Jacobian | `FULLY_SPECIFIED_NOT_EXECUTED` | Analytic identities and local `8u` arithmetic |
| G6 raw-rate sign | `FULLY_SPECIFIED_NOT_EXECUTED` | Strict implemented-rate nonnegativity |
| G7 grid refinement | `BLOCKED_ACCEPTANCE_RULE` | No justified remainder ceiling |
| G8/G9 quadratures A/B | `BLOCKED_ACCEPTANCE_RULE` | Path-local remainder proof absent |
| G10 cross normalization | `BLOCKED_BY_UPSTREAM_RULES` | Certified interval overlap only |
| G11 normalized-law closure | `BLOCKED_BY_UPSTREAM_RULES` | Algebraic propagation only |

One bad required point prevents Phase 2B PASS. `INCONCLUSIVE` is never PASS.

## Comparator semantics

The published approximately 0.1% APFEL/MassiveDIS agreement is exactly
`PUBLISHED_OBSERVED_BENCHMARK_LEVEL`. It is local to the published `F2c` and
`FLc` setup at `Q=5 GeV` with `NNPDF30_nlo_as_0118_IC5`. A future exact
replication could require “replication no worse than the published benchmark
level,” but `0.001` is neither a theorem nor a complete-rate uncertainty and
is inherited by no other gate. The source supplies plots, not exact x/output
records, so this comparator is not executable from the frozen bytes.

The massless benchmark is separate. V3 serializes its 27 NLO NC coordinates
(`Q={2,50,100} GeV`, nine x values, `F1/F2/F3`) and all 81 printed values.
That makes the publication a `PUBLISHED_INDEPENDENT_BENCHMARK`; it does not
make `TEST_MASSLESS` executable. No exact candidate-interval backend or
construction is frozen, and the full active-flavor/matching state at the
`Q0=sqrt(2)` and charm boundaries—including threshold equality and parsing of
`sqrt(2)+1e-9`—is incomplete. No finite candidate internal-work cap exists.
Consequently V3 defines no PASS rule or resource count for this test. The
paper's observed `1e-5` level remains local published evidence and is not used
as an unrelated tolerance.

## Alpha_s architecture

The choice is `AS2_CONTINUOUS_EQUIVALENCE_CERTIFICATION`. Static APFEL 3.1.1
source inspection rejects AS1: the public API configures an internal coupling
and `ComputeDISOperators` calls `a_QCD`; `ExternalSetAPFEL` is a PDF-only
callback. Adding an alpha callback would change the accepted implementation.

The reduced contract does not require mathematically identical functions.
CT18/LHAPDF is a finite cubic interpolation of serialized HOPPET values, while
APFEL is a different finite ten-step RK4 algorithm. It requires continuous
consistency at the declared CT18 serialization resolution and propagation of
the entire certified discrepancy through later NLO rate evidence. AS2 is the
selected architecture, but V3 does not yet turn that intention into a fully
specified postauthorization test.

The provisional design uses `z=ln(Q^2)` on
`Q^2 in [3.5,50000] GeV^2`, split at the 21 in-domain CT18 knots, both
endpoints, `m_b=4.75 GeV`, and `m_t=172 GeV`. Because `m_b` is already a knot,
it sketches 24 breakpoints and 23 roots, 256-bit outward-dyadic arithmetic,
rational log range reduction, a 128-term atanh series, and deterministic
left-first subdivision to depth 12. Those descriptions are not an
implementation identity or an executable interval proof.

The remaining AS2 specification gaps are load-bearing:

- No repository path and SHA-256 bind an interval backend; primitive outward
  rounding, centered mean-value dual operations, enclosure formulas and
  comparisons are not normatively defined.
- LHAPDF returns `alpha_s`, while APFEL exposes `a_QCD`; the contract has not
  frozen whether and how `alpha_s(APFEL)=4*pi*a_QCD` is formed, including the
  exact pi constant, operation order and outward rounding.
- The counted 29 probes per provider are not listed as exact Q or Q2 bit
  patterns. Log range-reduction constants, split constants and literal series
  coefficients are not serialized.
- Decimal-token parsing, Q-versus-Q2 threshold-side `nextafter` construction,
  threshold equality/matching behavior, floating-point exceptions, and exact
  backend build/compiler semantics are not frozen.

The previous arithmetic—188,393 cells per provider, 9,829,200 APFEL beta-RHS
interval evaluations, 58 provider probes, 3,840 log-series terms and
10,209,884 primitive actions—is retained only as
`NONAUTHORITATIVE_CANDIDATE_CEILING`. It is not `TEST_ALPHA.resource_count`,
not an aggregate input, and not evidence for authorization. `mpmath.iv` is not
a rigorous backend; mpmath remains a pinned diagnostic only.

## PDF artifact and bridge

The raw identity is CT18NLO DataVersion 1, SetIndex 14400, member 0:

- archive `c9127231e77e97cbec79cb5839203ab00f8db77237a061b61f9420f2b7b9c213`
- metadata `be60232d8e6c49982c82f5fa990fd5b0fd1050719944f31602bf27cdb16548b0`
- member file `375db856d2f8c7087a626c92ebf228d3f080e5de83175519778ffaf6e72e5410`

Flavor order is `[-5,-4,-3,-2,-1,1,2,3,4,5,21]`; support is
`x in [1e-9,1]`, `Q in [1.295,100000] GeV`; `Q0=1.295 GeV`; interpolation is
`logcubic`; the caller enforces strict no-extrapolation. The projected family,
baseline, D0R implementation/decision, and all nine canonical theta IDs are
frozen. Failed D1/D1R evolved artifacts are not accepted.

Bridge B1-B8 cover exact identity, flavor map, `x*f` once, sign, zero, strict
support, Q-in-GeV at exact Q0, and linked callback identity. Signed power-of-two
`f` sentinels are called at `x=1/2` and `x=1/4`; a third callback alternates
bitwise `+0/-0` across mapped flavors. The valid tuple, 15 exact
identity-category mutations, four support cases, four Q cases, and two link
cases are enumerated in the JSON. An exact full-tuple comparison rejects any
other raw/projected identity mismatch. Real comparison uses all nine anchors
and 17/33/65 x levels. The bridge performs one RN-even multiplication.
For normal exact `p*=x*fhat` and `b=RN(p*)`,
`|b-p*|<=u|p*|`, `u=2^-53`. Acceptance is bitwise equality to an independently
correctly rounded product from the hash-bound exact-integer oracle—not an
unexplained `16u` allowance. That oracle also defines signed zero, gradual
underflow, subnormal crossover, overflow, and nonfinite rejection. The maximum
is 1,045 callback attempts, 1,040 evaluator calls, 14,532 slot comparisons, and
1,063 logical cases including identity/interface checks.

## Raw-rate sign contract

V3 chooses `SIGN1_STRICT_IMPLEMENTED_RATE_NONNEGATIVITY`. The probability-law
object is the raw, frozen, finite-precision simulator rate—not an all-orders
cross section or a certified abstract exact finite-order formula.

```text
raw finite rate < 0  => FAIL
raw finite rate >= 0 => local sign PASS
```

Raw bits are retained, including signed zero. No clipping, `abs`,
`max(rate,0)`, replacement, deletion, epsilon, averaging, or retry is allowed.
Any later negative runtime rate aborts. The finite scan is not promoted to a
continuum-positivity theorem.

## Remaining blockers

For grid statistics, `d1=|D33-D17|` and `d2=|D65-D33|` do not bound unsampled
behavior without a proven approximation order, derivative/Lipschitz enclosure,
or accepted scientific precision target. For Gauss-Legendre 16/32/64 and
Clenshaw-Curtis 17/33/65, three finite estimates likewise do not bound a DIS
integral remainder. Generic polynomial tests validate implementations, not the
future physics integrand. Cross-rule agreement cannot replace either missing
path-local bound because both paths share the integrand and domain map.

Normalization therefore lacks certified intervals
`Z_A±E_A`, `Z_B±E_B`. Its eventual rule is finite positive lower endpoints and
interval overlap. Normalized-law closure will use opposite denominators
`I_A[r/Z_B]=Z_A/Z_B` and `I_B[r/Z_A]=Z_B/Z_A`, with all residual bounds
algebraically propagated; there is no standalone normalized-law threshold and
no claim of theoretical uncertainty on q.

The second blocker is `TEST_FONLL_COMPONENT`. MassiveDIS's source evidence is
figure-only. The older FONLLdis/FastKernel source has 24 exact `F2c/FLc` table
records, but its referenced Les Houches PDF/alpha setup and a finite executable
comparator work bound are not yet fully frozen. V3 records both routes without
pretending either is an executable test.

Three additional preauthorization blockers remain. `TEST_ALPHA` lacks its
hash-bound interval backend, exact formulas and alpha_s/a_QCD conversion,
literal probes/constants, and parse/threshold/build semantics.
`TEST_MASSLESS` has published reference records but lacks an executable
candidate-interval algorithm, complete heavy-flavor boundary setup, and finite
work cap. Finally, exact source and wheel inputs do not bind a CPython
executable or the OS/libc/libm/compiler/CPU floating-point runtime. These are
not documentation niceties: they prevent reproducible numerical decisions.

## Test and resource summary

| Test | State | Maximum |
| --- | --- | ---: |
| TEST_ALPHA | blocked specification | not derivable; 10,209,884 is a nonauthoritative candidate ceiling only |
| TEST_BRIDGE | fully specified | 1,063 logical cases |
| TEST_FONLL_COMPONENT | blocked | not derivable |
| TEST_MASSLESS | blocked specification | not derivable; 27 rows / 81 tokens are publication inventory only |
| TEST_EW_JACOBIAN | fully specified | 216 analytic cases |
| TEST_RAW_RATE_SIGN | fully specified | 63,882 rate evaluations |
| TEST_GRID_CONVERGENCE | blocked | reuses 63,882 records |
| TEST_QUADRATURE_A | blocked rule | 48,384 integrand evaluations |
| TEST_QUADRATURE_B | blocked rule | 50,427 integrand evaluations |
| TEST_CROSS_QUADRATURE | blocked upstream | 9 cached comparisons |
| TEST_NORMALIZATION | blocked upstream | 72 cached operations |
| TEST_NORMALIZED_LAW | blocked upstream | 98,811 cached contributions + 18 residuals |

There are 162,693 planned raw-rate/integrand evaluations in the bounded partial
vector, but that vector is not a complete-plan aggregate. Per-test maxima are
deterministic and finite only where the test specification is complete, with no
retry-until-pass. `TEST_ALPHA`, `TEST_FONLL_COMPONENT`, and `TEST_MASSLESS`
have `resource_count=null`. An authoritative aggregate maximum is therefore
also `null`. The provisional AS2 ceiling and massless publication inventory
are excluded, and summing heterogeneous cells, RHS calls, slots, and
comparisons would conceal rather than solve D7.

## Runtime inputs and blocker

The intended runtime inputs are Linux x86_64, CPython 3.10.20, NumPy 2.2.6,
SciPy 1.15.3, and mpmath 1.3.0. Exact CPython source and package-wheel hashes
are in the JSON and
[`analysis/requirements-phase2b-v3.txt`](../../analysis/requirements-phase2b-v3.txt),
and the intended NumPy/SciPy environment is single-threaded. Those hashes do
not bind the CPython executable, OS/root filesystem, libc, libm, dynamic
loader and transitive shared libraries, compiler/linker flags, CPU features,
or floating-point environment. D8 therefore remains
`PARTIAL_BLOCKER_REMAINS`; no bit-level or rigorous numerical claim may treat
the runtime as frozen. Pandas, matplotlib, and pytest remain non-load-bearing.

## Failure precedence

```text
CONTRACT_IDENTITY_FAILURE
SUPPORT_FAILURE
BRIDGE_FAILURE
ALPHA_S_FAILURE
REFERENCE_FAILURE
NONFINITE_IMPLEMENTED_RATE
RAW_NEGATIVE_RATE
NORMALIZATION_NONPOSITIVE
CONVERGENCE_FAILURE
RESOURCE_EXHAUSTION
INCONCLUSIVE
```

## Phase completion report

All commands below ran in WSL Ubuntu from the repository root. No native
physics validation was performed, so `scripts/pythia_env.sh` was not sourced.

| Command | Result |
| --- | --- |
| `python3 scripts/validate_phase2_fonll_a_contract_amendment.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan.py` | PASS |
| `python3 scripts/validate_phase2b_execution_authorization_review.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan_v2.py` | PASS |
| `python3 scripts/validate_phase2b_execution_authorization_review_v2.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan_v3.py` | PASS |
| `python3 -m pytest -q analysis/tests/test_phase2b_preauthorization_validation_plan_v3.py analysis/tests/test_phase2b_bridge_oracles.py` | PASS, 131 tests |
| `python3 -m pytest -q analysis/tests/` | FAIL, 601 passed / 1 failed because host SciPy 1.18.0 violated the predecessor's exact 1.15.3 guard |
| `python3 -m pip install --target /tmp/partonsbi-phase2b-preauth-v3-review/analysis-site -r analysis/requirements.txt` | PASS; temporary WSL dependency tree only |
| `env PYTHONPATH=/tmp/partonsbi-phase2b-preauth-v3-review/analysis-site python3 -m pytest -q analysis/tests/` | PASS, 602 tests |
| `env PYTHONPATH=/tmp/partonsbi-phase2b-preauth-v3-review/analysis-site python3 -m pytest -q analysis/tests/` after WSL cleared that temporary tree | FAIL, 601 passed / 1 exact-version guard failure; not treated as a dependency-matched run |
| `bash -lc "python3 -m pip install --quiet --target /tmp/partonsbi-phase2b-v3-analysis-site -r /mnt/c/Users/mirha/OneDrive/Belgeler/GitHub/parton-sbi/analysis/requirements.txt && cd /mnt/c/Users/mirha/OneDrive/Belgeler/GitHub/parton-sbi && PYTHONPATH=/tmp/partonsbi-phase2b-v3-analysis-site python3 -m pytest -q analysis/tests/"` | PASS, 604 tests; authoritative final coupled run |
| PR CI run `31748390132`, Python Analysis Tests | FAIL during collection: the `pytest` entrypoint did not place the repository root on `sys.path` for the new bridge-oracle test |
| `/home/mrxn/.local/bin/pytest -q analysis/tests/test_phase2b_preauthorization_validation_plan_v3.py analysis/tests/test_phase2b_bridge_oracles.py` after explicit test-root import fix | PASS, 131 tests |
| `bash -lc "python3 -m pip install --quiet --target /tmp/partonsbi-phase2b-v3-ci-fix-site -r /mnt/c/Users/mirha/OneDrive/Belgeler/GitHub/parton-sbi/analysis/requirements.txt && cd /mnt/c/Users/mirha/OneDrive/Belgeler/GitHub/parton-sbi && PYTHONPATH=/tmp/partonsbi-phase2b-v3-ci-fix-site /home/mrxn/.local/bin/pytest -q analysis/tests/"` | PASS, 604 tests; exact CI-style entrypoint verification for correction cycle 1 |
| `cargo fmt --all -- --check` | PASS |
| `git diff --check` | PASS |

The machine artifact SHA-256 is
`78a029686489e9712e65ef6f9df3263b4821f96de0ee9873a910dee31f307e06`.
The temporary dependency directory is outside the repository and is not a
deliverable. The one failed first run is retained here rather than hidden; no
scientific rule or test was weakened to obtain the clean dependency-matched
run.

Unresolved scientific limitations remain part of this record: no end-to-end
independent rate comparator, no complete FONLL or massless candidate test, no
executable AS2 certificate, no fully bound numerical runtime, no grid or
quadrature remainder rule, no continuum sign proof, only nine theta anchors,
and no unrestricted flavor separation from inclusive NC e-p observations.

## Next step

Freeze and hash the AS2 backend with exact formulas, `4*pi` mapping,
probes/constants and parse/threshold/build semantics; complete the massless
heavy-flavor/candidate-interval/work specification and numerical runtime
identity; resolve the grid/quadrature remainder criteria; and freeze one exact
finite FONLL component comparator. Then create a new successor plan. Do not
conduct an authorization review or execute Phase 2B from this V3 record.
