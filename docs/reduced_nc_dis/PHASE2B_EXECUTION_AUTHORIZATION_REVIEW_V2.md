# Phase 2B v2 execution authorization review

## Decision

```text
DECISION = AR2_PREAUTH_V2_REVISION_REQUIRED
PHASE2B_BOUNDED_NUMERICAL_VALIDATION_AUTHORIZED = false
PHASE2B_EXECUTION_AUTHORIZED = false
PHASE2B_EXECUTION_STATUS = NOT_EXECUTED
```

This independent successor review does not authorize the frozen v2 plan. The
FONLL-A research direction remains viable, but its numerical budget, several
post-authorization test identities, resource cap, and dependency resolution
must be revised before responsible execution. The authoritative record is
[`contracts/phase2b_execution_authorization_review_v2.json`](contracts/phase2b_execution_authorization_review_v2.json).

The review binds preauthorization v2 at SHA-256
`a79e87538fae4d3f20793756b321af4d7521c1277ee08580e1b773a7452a9cd2`,
the previous AR2 record at
`03d8119efb819b7a8b51161d5f2ce58fe59dd385b63f2dbfd6203692dac1f9e2`,
and the FONLL-A amendment at
`10cf19fedcdfe1b94e18ff89d1ae09514a31b8e0f6b055beeb729d61b6c32da8`.
Historical Phase 2A remains `COMPLETE/INCONCLUSIVE`.

## Integrity preflight

The exact path `C:/tmp/partonsbi-phase2b-preauth-v2-pr-body.md` was absent from
the tracked path set, its Git history, repository references, and the working
tree. Its classification is `TEMP_A_NOT_TRACKED`; no cleanup commit or PR was
required. The tracked root `pr_body.md` is historical Phase 2A material, not
the named Phase 2B v2 temporary file. The scientific review therefore started
from unchanged main SHA `d2d2d4d95a6a405200ac9aba78d50ab19e67ead6`.

## Parent-budget audit

The classification is `BUDGET_PARENT_NOT_JUSTIFIED`. The 0.001 evidence is an
observed, rounded approximately 0.1% APFEL/MassiveDISsFunction implementation
agreement, not a formal accuracy guarantee. The primary paper presents
illustrative matched charm `F2c` and `FLc` comparisons at `Q=5 GeV` with a toy
intrinsic-charm PDF setup, while its prose reports this level or better across
its NC and CC structure-function checks. See the
[MassiveDISsFunction paper](https://arxiv.org/abs/1605.06515).

That observation does not establish a complete-rate relative, absolute, or
mixed allowance for the accepted theta-dependent PDF bridge, two `alpha_s`
providers, gamma/Z assembly, Jacobian, grid, two quadratures, or normalized
law. It cannot be promoted into `T_external` merely because it is the strongest
published component comparison available.

The equal split is classified `ERROR_BUDGET_STRUCTURE_INVALID`. Although
`8*0.000125=0.001`, the eight terms are not shown to be commensurable,
nonoverlapping primitive errors. Bridge and Jacobian roundoff cannot plausibly
consume equal relative shares, alpha propagation differs from quadrature
discretization, and normalization has denominator amplification through
`1/(Z_hat-E_Z)`. Near-zero rates also invalidate a simple relative
decomposition.

## Architecture audits

### AS2 coupling

`AS2_REVISION_REQUIRED`. Phase 2B requires numerical equivalence within a
bounded tolerance, not an identical coupling object; APFEL exposes no external
coupling callback. The proposed CT18/LHAPDF interpolation replay and independent
80-decimal RK4 refinement are directionally appropriate, and bottom-threshold
side probes are present. However, 282 points establish only sampled pointwise
agreement, with no continuous-domain remainder bound. The rate gate inherits
the rejected parent allocation, and the independent beta/matching code is not
source-bound.

### PDF/APFEL bridge

`BRIDGE_PLAN_REVISION_REQUIRED`. The PDG-to-APFEL map, `x*f`-once intent,
strict support, exact `Q0`, 14 sentinels, nine anchors, and 17/33/65 grids can
detect most mapping, sign, support, scale and normalization mistakes. The plan
does not freeze an immutable emitted LHAPDF member identity or hash, so a
shared wrong member can evade the comparison. The synthetic input is described
as sentinel `x*f` values rather than a separately bound `f -> x*f` path, and
the `16u` bound has no eventual source-level operation inventory.

### Quadratures

`QUADRATURE_INDEPENDENCE_QUALIFIED`. SciPy 1.15.3 Gauss-Legendre node and
weight generation with NumPy dot is numerically and implementation-wise
distinct from the repository cosine-sum Clenshaw-Curtis rule with
`math.fsum`. They share no node, weight, recurrence, or accumulation core.
Symmetry, positivity, total weight, degree-12 monomial, and exponential tests
detect common implementation defects. They still share the physics integrand,
domain map, and successive-difference convergence policy, while NumPy is
unpinned; the independence claim is therefore useful but qualified.

## Reference coverage

MassiveDISsFunction v1.2 is a source-restorable and later-runnable
`MASSIVE_FONLL_COMPONENT_ORACLE_QUALIFIED`, not a complete-rate oracle. Its
interfaces cover NC/CC `F1`, `F2`, `F3`, `FL`, massive, massless, subtraction,
and matched paths, subject to rebinding the accepted PDF, mass, coupling and
scale configuration. V2 does not enumerate the promised 64 fixed component
coordinates or bind the test-only GSL error-estimate patch bytes.

The full graph is:

| Node | V2 status | Authorization finding |
| --- | --- | --- |
| complete NC rate | `PARTIAL` | No end-to-end independent rate oracle |
| electroweak assembly | `FULLY_INDEPENDENT` | Analytic oracle; fixed points not serialized |
| massless coefficients | `PUBLISHED_INDEPENDENT_BENCHMARK` | Coordinates referenced, not enumerated |
| massive contribution | `INDEPENDENT_POSTAUTH_TEST_DEFINED` | 64 coordinates absent |
| FONLL difference | `INDEPENDENT_POSTAUTH_TEST_DEFINED` | Signed decomposition appropriate; coordinates absent |
| PDF provider | `INDEPENDENT_POSTAUTH_TEST_DEFINED` | Emitted member identity/hash absent |
| PDF-to-APFEL bridge | `INDEPENDENT_POSTAUTH_TEST_DEFINED` | Wrong-member independence not closed |
| `alpha_s` | `INDEPENDENT_POSTAUTH_TEST_DEFINED` | Sampled rather than continuous-domain claim |
| coordinate/Jacobian | `FULLY_INDEPENDENT` | Analytic identity adequate |
| quadrature A | `FULLY_INDEPENDENT` | Distinct algorithm; NumPy unpinned |
| quadrature B | `FULLY_INDEPENDENT` | Distinct direct scalar implementation |
| normalization assembly | `INDEPENDENT_POSTAUTH_TEST_DEFINED` | Needs compatible absolute budgets |

There is no nominal `UNVALIDATED` node, and every future failure may fail
Phase 2B. The post-authorization graph is nevertheless
`POSTAUTH_SPECIFICATION_UNDERDEFINED`: missing coordinates, comparator patch
identity, and member identity leave load-bearing tests insufficiently frozen
before authorization. No post-hoc repair is permitted.

## Sign, normalization, and Jacobian

NR2 is `NR2_REVISION_REQUIRED`. Its ordering is conservative:

```text
r_hat < -E_total   => FAIL_NEGATIVE_RATE
|r_hat| <= E_total => INCONCLUSIVE_SIGN
r_hat > E_total    => bounded positive
```

Any inconclusive required point blocks a global positivity PASS; no averaging,
clipping, deletion, or high-precision repair is allowed. But `E_F2`, `E_FL`,
`E_xF3`, bridge, alpha, grid, and Jacobian errors are not operationally
converted to compatible absolute rate units, and some can overlap.
`gamma_32*S_assembly` bounds only the stated outer assembly, not APFEL internals.

The normalized-law inequality is formally valid when `Z_hat>E_Z`, the true
normalization is positive, and all errors use compatible absolute units:

```text
|q_hat-q| <= E_r/(Z_hat-E_Z)
             + |r_hat|*E_Z/[Z_hat*(Z_hat-E_Z)].
```

V2 correctly makes `Z_hat<=E_Z` inconclusive or a failure, never a pass, and
the first term remains meaningful near zero rate. Its input budgets still
require revision.

The Jacobian result is `JACOBIAN_BOUND_AUTHORIZED`. One `s*x` multiplication,
one reciprocal/division, an independently ordered analytic value and one
comparison subtraction are conservatively covered by `8*2^-53` relative.
Input representation uncertainty remains separate from this local arithmetic
bound.

## Resource and dependency audits

The serialized arithmetic does reproduce 503,284 under a one-segment RK4
assumption. It is not conservative under v2's own requirement that
20/40/80/160 steps occur per flavor segment. Points below `m_b` cross two
segments. A conservative recomputation, also including the separately declared
synthetic bridge callback comparison, is:

```text
63882 + 98811 + 310 + 2*282 + 9*(17+33+65) + 282
  + 282*2*(20+40+80+160)*4 + 1 = 841,685.
```

This remains finite and deterministic, with no adaptive extension or
retry-until-pass rule, but the frozen 503,284 cap is
`RESOURCE_BOUND_REVISION_REQUIRED`.

Dependency reproducibility is `UNPINNED_LOAD_BEARING_DEPENDENCY`. SciPy
`==1.15.3` and mpmath `==1.3.0` are pinned, but quadrature A uses load-bearing
NumPy arrays and `numpy.dot` while `analysis/requirements.txt` specifies only
`numpy>=1.26.0`; Python is also not fixed. Resolver-selected NumPy/BLAS
semantics can therefore change the frozen numerical path.

## Decision derivation and authorization

The invalid parent and allocation independently forbid AR1. The underdefined
AS2 and bridge claims, missing post-authorization identities, understated
resource cap, and unpinned NumPy path are additional bounded plan blockers.
They do not invalidate the FONLL-A research direction, so AR3 is unwarranted.
The exact decision is therefore `AR2_PREAUTH_V2_REVISION_REQUIRED`.

All Phase 2B execution and downstream authorization flags remain false.
Issue #55 remains Open/Backlog, Gate Decision Not Evaluated, Authorization Not
Authorized. Phase 2C, events, datasets, detector work, training, neural work,
legacy D2, and full-generator execution remain unauthorized. Execution remains
`NOT_EXECUTED`.

No APFEL or APFEL++ numerical physics, structure-function calculation,
coupling scan, bridge validation, positivity scan, normalization integration,
MassiveDIS comparison, FONLL closure, event generation, dataset construction,
detector simulation, or neural work was performed.

## Phase completion report

The exact validation commands and final results are recorded here after the
complete local validation gate. All commands run from the repository root in
WSL Ubuntu, with `scripts/pythia_env.sh` sourced for native physics validation.

| Exact command | Result |
| --- | --- |
| `python3 scripts/validate_phase1b_closeout.py` | PASS — 20 artifacts, 11 ADRs, 7 lineage records |
| `python3 scripts/validate_phase2_reduced_nc_dis_roadmap.py` | PASS — 9 issues, 24 obligations |
| `python3 scripts/phase2a_contract_review.py` | PASS |
| `python3 scripts/validate_phase2_fonll_a_contract_amendment.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan.py` | PASS |
| `python3 scripts/validate_phase2b_execution_authorization_review.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan_v2.py` | PASS |
| `python3 scripts/validate_phase2b_execution_authorization_review_v2.py` | PASS |
| `python3 -m pytest -q analysis/tests/test_phase2b_execution_authorization_review_v2.py` | PASS — 27 passed |
| `python3 -m pytest -q analysis/tests/` | ENVIRONMENT FAIL — 472 passed, 1 failed because unsourced system SciPy was 1.18.0 rather than the frozen 1.15.3; not accepted as validation evidence |
| `python3 -m pip install --disable-pip-version-check --target /tmp/partonsbi-phase2b-auth-v2-site -r analysis/requirements.txt` | PASS — isolated WSL target installed SciPy 1.15.3; the open constraint selected NumPy 2.4.6 |
| `PYTHONPATH=/tmp/partonsbi-phase2b-auth-v2-site python3 -m pytest -q analysis/tests/` | PASS — 473 passed |
| `source scripts/pythia_env.sh && cargo fmt --all -- --check` | PASS |
| `source scripts/pythia_env.sh && cargo check --workspace` | PASS |
| `source scripts/pythia_env.sh && cargo test --workspace` | HARNESS TIMEOUT — first 124-second attempt ended after compilation with a broken pipe; not a scientific or test assertion failure |
| `source scripts/pythia_env.sh && cargo test --workspace` | PASS on bounded 300-second rerun — all test binaries passed; expected environment-dependent tests remained ignored |
| `source scripts/pythia_env.sh && ctest --test-dir physics-engine/build --output-on-failure` | PASS — 1/1 passed |
| `git diff --check` | PASS |

The unresolved scientific limitations are exactly the AR2 blockers above. A
negative authorization result is the intended honest outcome of this review.

## Next action

Revise the v2 plan without executing it: derive a complete-rate error target
and nonoverlapping absolute primitive bounds, fully freeze AS2/bridge/reference
test identities, correct the resource bound, and pin the load-bearing Python
stack. A later independent authorization review must assess that successor.
