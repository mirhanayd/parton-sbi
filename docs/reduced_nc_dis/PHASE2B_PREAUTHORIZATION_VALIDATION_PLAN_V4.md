# Phase 2B preauthorization validation plan V4

## Result

```text
OUTCOME = V4_PREAUTH_PLAN_COMPLETE_READY_FOR_SEPARATE_EXECUTION_AUTHORIZATION_REVIEW
PHASE2B_AUTHORIZED = false
PHASE2B_EXECUTED   = false
PHASE2C_AUTHORIZED = false
NEXT_ACTION = SEPARATE_INDEPENDENT_PHASE2B_EXECUTION_AUTHORIZATION_REVIEW
```

**Completing V4 is not authorization to execute Phase 2B.** This is a planning
artifact. No DIS structure function, APFEL, APFEL++, MassiveDIS, FONLL
benchmark, coupling diagnostic, bridge validation, positivity scan or
normalization integral was executed. The authoritative record is
[`contracts/phase2b_preauthorization_validation_plan_v4.json`](contracts/phase2b_preauthorization_validation_plan_v4.json).

Predecessors bound and unmodified — FONLL-A amendment `10cf19fe…`, v1
`7eb8834e…`, AR2-v1 `03d8119e…`, v2 `a79e8753…`, AR2-v2 `d7826158…`, V3
`78a02968…`, blocker resolution `d66a1bbc…`, numerical policy `a855dfeb…`,
FONLL validation policy `8210b926…`.

Inherited unchanged: `AP1`, `NP2`, `FPD3`,
`NO_UNDISCLOSED_LOAD_BEARING_VALIDATION_GAP`, `SIGN1`. **V4 creates no new
scientific policy.**

## The seven authoring items

### 1 — NP2 stability protocol · `FROZEN`

`NP2_STABILITY_RULE_V4_SELF_SCALED_NO_FREE_PARAMETER`. **No scalar tolerance is
invented**, because none is derivable: the accepted research-question record
fixes no event-set size, selects no metric, and declares no acceptable posterior
distortion. Instead every comparison scale is *computed at execution from
formulas frozen now*, with no adjustable parameter:

| Quantity | Frozen formula |
| --- | --- |
| within-family | `d1 = |Z_L2 − Z_L1|`, `d2 = |Z_L3 − Z_L2|`; require `d2 ≤ d1` |
| family A noise | `eps_A = gamma_k · Σ|w_i f_i|`, `k = ceil(log2 n)`, `gamma_k = k·u/(1−k·u)` (NumPy pairwise dot) |
| family B noise | `eps_B = u·|Z_B|` (`math.fsum` is exactly rounded) |
| cross-family | `|Z_A − Z_B| ≤ d2_A + d2_B + eps_A + eps_B` |

`PASS` needs all six estimates finite, both finest estimates strictly positive,
both within-family criteria satisfied, and the cross-family criterion satisfied
— **at every one of the nine anchors**. Non-monotone refinement is
`INCONCLUSIVE`, never `PASS`. Cross-family disagreement is `FAIL`. Agreement is
necessary and **explicitly not sufficient**. Everything is absolute, so no
near-zero division can arise and no relative form may be substituted later.

Forbidden imports are named: the MassiveDIS `0.001`, the massless `1e-5`, and
any other external benchmark discrepancy.

### 2 — Grid gate · `FROZEN`

Replaced by `EXACT_COVERAGE_AND_NESTING_AUDIT`. It certifies **structure only**
and no continuum property. Nesting was verified in this task, not assumed:

| Family | Levels | Nesting |
| --- | --- | --- |
| point grid (x and Q²) | 17/33/65 | `NESTED_BITWISE`, zero failures |
| Clenshaw–Curtis | 17/33/65 | `NESTED_BITWISE` at strides 2, 2 and 4 |
| Gauss–Legendre | 16/32/64 | **`NOT_NESTED`** — orders 16 and 32 share **zero** nodes |

Mislabelling the Gauss–Legendre ladder as nested is explicitly forbidden. The
plan must retain the deterministic non-DIS counterexample in which two
refinement sequences agree perfectly with themselves and each other while both
are wrong, so the audit can never be reinterpreted as a convergence proof.

### 3 — Massless reference · `FROZEN_WITH_DECLARED_UNBOUND_ITEMS`

Reference side bound from the publication and its released program
(`199f7e90…`): NLO, `Q0 = sqrt(2.0)` in binary64, `alpha_s(Q0) = 0.35`,
**`nf = 3` at `Q0`**, thresholds `1.414213563 / 4.5 / 175.0`, `xmuR = xmuF = 1`,
`sin²θ_W = 1 − (80.377/91.1876)²`, ZM NC `F1/F2/F3`, 27 coordinates, 81 tokens.
The prose-versus-code discrepancy is carried forward: the paper says
`sqrt(2)+1e-9`, the code holds `1.414213563` — **the executable literal binds**.

Candidate-side grid settings are **bound by reference, not invented**: APFEL
3.1.1's source-defined defaults at `initParameters.f` (`1acd6161…`) lines 87–91,
`SetNumberOfGrids(3)` with `(80,3,1e-5)`, `(50,5,0.1)`, `(40,5,0.8)`. The future
run must *not* call the setters, so the defaults apply, and must record the
realised values.

Declared unbound: the publishers' internal grid settings, and their codes'
mutual agreement beyond the displayed digits. Consequently the comparison is
candidate-against-published-values, **not** reproduction of their pipeline, and
no tolerance may be derived from their agreement statement. Acceptance is
displayed-digit containment — publication precision only.

### 4 — Bridge · `FROZEN`

Two profiles. **A**: the accepted CT18 boundary at `Q0 = 1.295`. **B**: the
massless-reference boundary at `Q0 = sqrt(2.0) = 1.4142135623730951`, existing
*only* to run the massless candidate and never supplying the accepted simulator.
Shared semantics keep `f` versus `x·f` with exactly one multiplication, Q in GeV
never Q², bitwise `Q0` equality, signed-zero preservation, bitwise `+0.0`
structural slots, and subnormal comparison against the hash-bound exact-integer
oracle. No extrapolation, no support repair, no double multiplication, no
implicit remap, no silent zero replacement.

Work cap recounted: **1,047** callback attempts, **1,042** evaluator
invocations, **14,588** slot comparisons (`1042 × 14`). V3's 14,532 used a
different convention and is deliberately not reused.

### 5 — Alpha diagnostic · `FROZEN`, `NON_GATING`

Under `AP1` the runtime coupling is APFEL's `AlphaQCD`; CT18 metadata is
provenance. The diagnostic node set is deterministic: the two domain endpoints,
the squares of the 21 in-domain CT18 knots, and the two `nextafter` neighbours
of `mb²` — **25 distinct nodes, 50 provider evaluations**, verified here. It
reports observed absolute and relative differences and **must not** establish
continuum equivalence, bitwise identity, certified consistency, physics
correctness, authorization, or a generic error budget. The unresolved
running-order compatibility item is carried and must be reported; a material
convention mismatch still triggers scientific review.

### 6 — Runtime identity · `FROZEN_WITH_EXPLICIT_CLASSIFICATIONS`

Fourteen dependencies, each classified separately across source-identified,
hash-pinned, installed, executable-here, and required-for-execution. **A source
hash is explicitly not executable verification.** Four load-bearing
dependencies — CPython 3.10.20, NumPy 2.2.6, SciPy 1.15.3, APFEL 3.1.1 — are
hash-pinned but **not installed**; installing and verifying them is an
execution-time prerequisite, not a planning gap, since no planning decision
depends on their presence.

CPU microarchitecture is **not** a scientific dependency: `AP1` removed the
coupling certification that would have made the ifunc-selected `libm` variant
load-bearing. It is recorded for disclosure only. Rigorous glibc/libm log
certification is **not** resurrected as a gate.

### 7 — Resource model · `FROZEN`

Recounted from first principles; **no total copied**. Fourteen categories, each
with unit, formula, fixed factors, minimum, nominal, worst case and cap.

| Category | Unit | Cap |
| --- | --- | ---: |
| point-grid complete-rate evaluations | complete-rate evaluation | 63,882 |
| quadrature A integrand evaluations | complete-rate evaluation | 48,384 |
| quadrature B integrand evaluations | complete-rate evaluation | 50,427 |
| massless candidate evaluations | ZM structure-function evaluation | 81 |
| published record comparisons | published scalar comparison | 81 |
| bridge callback attempts | callback attempt | 1,047 |
| bridge evaluator invocations | evaluator invocation | 1,042 |
| bridge slot comparisons | slot comparison | 14,588 |
| alpha diagnostic evaluations | alpha provider evaluation | 50 |
| analytic EW/Jacobian cases | analytic case | 216 |
| grid audit structural checks | structural oracle check | 63,894 |
| normalization cross-check operations | cached operation | 63 |
| serialization bytes | byte | 41,096,192 |
| non-physics oracle tests | structural oracle check | 1,000 |

Exactly **one** additive aggregate is formed, over the three categories that
genuinely share a unit: **162,693 complete-rate evaluations**, where one
evaluation is one call to the frozen wrapper at one `(x, Q², theta)` point.
Nothing else is summed. Retry budget is **zero**; resource exhaustion is
`INCONCLUSIVE`.

## Component coverage matrix

Sixteen components, each with implementation identity, evidence class,
reference identity, independence, executability, availability, mandatory and
gating status, test definition, comparison target, PASS/FAIL/INCONCLUSIVE
semantics, residual risk, allowed and prohibited claim, work formula and
resource category.

| Component | Class | Indep. | Gating |
| --- | --- | --- | --- |
| complete NC observable | `E6` | no | no |
| electroweak assembly | `E3` | yes | yes |
| massless coefficients | `E2` | yes | yes |
| massive contribution | `E2` | yes | no |
| FONLL matching difference | `E2` | yes | no |
| PDF provider | `E5` | yes | yes |
| PDF → APFEL bridge | `E4` | yes | yes |
| `alpha_s` | `E5` | yes | **no** (AP1 policy exception) |
| coordinate / Jacobian | `E3` | yes | yes |
| point-grid coverage | `E4` | yes | yes |
| quadrature A | `E6` | no | yes |
| quadrature B | `E6` | no | yes |
| normalization assembly | `E6` | no | yes |
| normalized-law assembly | `E3` | yes | yes |
| support / domain handling | `E4` | yes | yes |
| raw-rate sign classification | `E4` | no | yes |

The complete NC observable is **not** `E1`, **not** independently closed, and
**not** end-to-end validated. `ALPHA_S` is the single policy-designated
non-gating row, authorised by `AP1` and not extensible.

## The surviving limitation

> A correctly configured, correctly interfaced but internally wrong FONLL
> matching term is **not independently detectable**.

No independently executable exact FONLL-A comparator is bound. The massive and
matching contributions rest on published evidence obtained at other groups'
configurations. This is a declared permanent limitation of the Phase 2B result,
not a deferred task, and the paper must state it.

## Paper boundary

**MAY** (if later executed successfully): frozen APFEL FONLL-A configuration;
fixed source and configuration identities; available independent component
checks predeclared and executed; independent published FONLL/heavy-flavour
evidence exists; normalization showed reproducible empirical stability under two
independently implemented fixed quadrature families; coupling compatibility
investigated diagnostically; **the absence of an independently executable exact
FONLL-A comparator is an explicit limitation**; conclusions conditional on the
frozen reduced simulator.

**MUST NOT**: independent executable full FONLL-A closure; current-implementation
correctness inferred from a published benchmark; production-precision
validation; end-to-end independent physics closure; rigorous normalization
accuracy; continuum coupling equivalence; continuum rate positivity; posterior
calibration as proof of physics; global-fit replacement; unrestricted PDF
determination; full-generator equivalence.

## Phase completion report

All commands ran in WSL Ubuntu from the repository root. No native physics
validation was performed, so `scripts/pythia_env.sh` was not sourced.

| Command | Result |
| --- | --- |
| all eleven predecessor Phase 2 validators | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan_v4.py` | PASS |
| focused V4 suite | PASS, 118 tests |
| `python3 -m pytest -q analysis/tests/` | PASS, 1,016 tests |
| `cargo fmt --all -- --check` | PASS |
| `git diff --check` | PASS |

The machine artifact SHA-256 is
`fec4acd52fdf3371e38eeb519d853949b5190183fd11691d72d471725368f676`.

### Corrections made rather than hidden

Two internal inconsistencies were found by self-review. The complete NC
observable was initially marked `mandatory` while having no available check,
contradicting the rule that an available mandatory check must be gating; it is
now `mandatory: false` with `disclosure_required: true`. Separately, the
`ALPHA_S` row is non-gating by `AP1` policy while being mandatory with an
available reference, so the matrix rule now carries an explicit, non-extensible
policy exception naming that single row.

A third correction touches predecessor **tooling**, and is disclosed here
because it deserves scrutiny. The numerical-policy and FONLL-policy validators,
and three predecessor test modules, asserted that the V4 artifact *does not
exist*. That was correct as written for those tasks, whose scientific claim was
"this task did not create V4" — but the assertion was implemented as permanent
file absence, which a legitimate successor necessarily violates. The guard now
asserts each record's own `v4_not_created_in_this_task` flag **and**, whenever a
V4 exists, that V4 binds that record as a predecessor at its exact hash. This
preserves the original scientific intent and is strictly stronger, since a rogue
V4 that failed to bind its predecessors would now be caught where previously
only its existence was. **No predecessor JSON artifact was modified**; all nine
predecessor hashes are verified on disk by the V4 validator.

## Next step

`SEPARATE_INDEPENDENT_PHASE2B_EXECUTION_AUTHORIZATION_REVIEW`. That review is
not performed here and is not implied by V4's completeness. Phase 2B remains
`NOT_AUTHORIZED` and `NOT_EXECUTED`.
