# Phase 2B preauthorization validation plan v2

## Result

```text
OUTCOME = RV1_PREAUTH_V2_COMPLETE_READY_FOR_NEW_AUTHORIZATION_REVIEW
PLAN_COMPLETENESS = COMPLETE
PHASE2B_AUTHORIZED = false
PHASE2B_EXECUTION_STATUS = NOT_EXECUTED
```

This scientific successor to the immutable v1 plan and merged AR2 review
resolves the four blockers at the specification level only. It neither
authorizes nor executes Phase 2B. The authoritative record is
[`contracts/phase2b_preauthorization_validation_plan_v2.json`](contracts/phase2b_preauthorization_validation_plan_v2.json).

## Immutable lineage

The successor binds the FONLL-A amendment at
`10cf19fedcdfe1b94e18ff89d1ae09514a31b8e0f6b055beeb729d61b6c32da8`,
the v1 plan at
`7eb8834eb8435532a85bd7d49b173b03e57a268f69f9676e0effbd877903672b`,
and the AR2 review at
`03d8119efb819b7a8b51161d5f2ce58fe59dd385b63f2dbfd6203692dac1f9e2`.
Their bytes and decisions are unchanged. Historical Phase 2A remains
`COMPLETE/INCONCLUSIVE`; ADR-013 remains Proposed.

## B1: coupling identity

The selected architecture is
`AS2_DUAL_PROVIDER_PREDECLARED_EQUIVALENCE_TEST`. APFEL 3.1.1 has no external
coupling callback, so v2 does not pretend that CT18/LHAPDF's interpolated
HOPPET table and APFEL's internal exact two-loop evolution are one object.

Provider A is CT18NLO DataVersion 1 member 0 through LHAPDF6 `alphasQ`, with
`AlphaS_Type=ipol`, its 37 serialized pairs, and the accepted mass/threshold
metadata. Provider B is APFEL 3.1.1 `AlphaQCD` with explicit reference, order,
pole-mass threshold and five-flavor controls. Source inspection shows that its
`exact` NLO path is a fixed 10-step classical RK4 calculation per flavor
segment, so binary64 roundoff alone is not treated as its numerical error.

The future test compares both on 257 log-Q points, all 21 CT18 table nodes in
the physics domain, `M_Z`, and both sides plus the exact bottom threshold:

```text
|alpha_CT18-alpha_APFEL|
  <= E_CT18_ipol(Q) + E_APFEL_RK4(Q)
     + (32*2^-53)*max(|alpha_CT18|,|alpha_APFEL|).
```

`E_CT18_ipol` comes from an 80-decimal directed-rounding replay of LHAPDF
6.5.6's actual log-`Q2` cubic interpolation, after enclosing every six-decimal
table value by `+/-5e-7`. `E_APFEL_RK4` compares APFEL with an independent
mpmath 1.3.0, 80-decimal threshold-split RK4 sequence at 20/40/80/160 steps.
The last two differences must contract by at least eight; its geometric tail
and the APFEL-to-160-step difference form the envelope. The relative term
covers only binary64 transport. Failed refinement, unavailable evidence or an
ambiguous threshold side is inconclusive; a finite mismatch outside the bound
fails. The propagated contribution must also fit its `0.000125*S_node` share.

## B2: negative-rate adjudication

The selected policy is `NR2_ERROR_ENVELOPE_WITH_INCONCLUSIVE_BAND`. No
complete binary128 APFEL oracle is claimed. The future task must record

```text
r_hat = K*(c2*F2_hat + cL*FL_hat + c3*xF3_hat)
E_upstream = |K|*(|c2|*E_F2 + |cL|*E_FL + |c3|*E_xF3)
             + E_bridge_rate + E_alpha_rate + E_grid_rate + E_jacobian_rate
E_outer = gamma_32*S_assembly
E_total = E_upstream + E_outer.
```

The fixed classifications are:

- `r_hat < -E_total`: `FAIL_NEGATIVE_RATE`;
- `|r_hat| <= E_total`: `INCONCLUSIVE_SIGN`;
- `r_hat > E_total`: numerically positive for the bounded claim.

One inconclusive-sign point prevents global positivity PASS. Raw signed values
are retained. Clipping, `abs`, `max(rate,0)`, support deletion and
retry-until-positive behavior are forbidden. Optional binary128 outer
assembly is diagnostic only and cannot erase upstream uncertainty.

## B3: bridge and independent references

The bridge is `BRIDGE_STATICALLY_BOUND_AND_POSTAUTH_TESTABLE`.
`ContinuousPdfPoint::densities` returns number densities; the callback returns
`x*f` exactly once. PDG flavors `±1..±5` map directly, PDG gluon 21 maps to
APFEL slot 0, and top, antitop and photon are exact positive zero. `Q` means
GeV and must equal the accepted boundary `Q0`; support is checked first.

The future bridge test injects 14 exactly representable sentinels, then
instruments all callback values at nine theta anchors and fixed 17/33/65 x
levels. Every slot is compared against the accepted Rust evaluator. The
callback supplies PDFs only; coupling responsibility remains with AS2.

MassiveDISsFunction v1.2 is a `MASSIVE_FONLL_COMPONENT_ORACLE`. Its independent
C++/GSL/LHAPDF source exposes NC/CC `F1/F2/F3/FL`, massive, massless,
subtraction and FONLL paths. The publication reports matched `F2c` and `FLc`
agreement at approximately 0.1% or better for an intrinsic-charm setup. Its
no-intrinsic old FONLL-A branch is the compatible S-ACOT special case. It is
not complete PartonSBI rate or normalization closure.

The later component comparison must explicitly call `SetPrec(6.25e-5)` and
use a test-only MassiveDIS build that retains every GSL `qags` absolute-error
estimate instead of passing a null error pointer. The absolute weighted sum of
those errors and the independent APFEL refinement envelope must each be no
larger than half of `T_SF=0.000125` on the local absolute scale. A larger
internal envelope is inconclusive and cannot consume another budget component.

The reference graph has no `UNVALIDATED` load-bearing node. The complete rate
remains `PARTIAL`; v2 makes no end-to-end independent-equivalence claim.

## Independent quadratures

Path A is fixed tensor Gauss-Legendre at orders 16/32/64 using pinned SciPy
1.18.0 `scipy.special.roots_legendre`. Path B is fixed tensor
Clenshaw-Curtis at 17/33/65 nodes using the direct cosine-sum implementation in
[`phase2b_quadrature_oracles.py`](../../analysis/validation/phase2b_quadrature_oracles.py).
Path B imports neither SciPy nor NumPy for node, weight or accumulation work.
Path A accumulates through a NumPy binary64 dot product; path B uses Python
`math.fsum`, so their accumulation cores are distinct as well.

Both paths necessarily share the future physics integrand and domain map, but
no quadrature core. Generic analytic polynomial tests verify nodes, weights,
symmetry and exactness now. They contain no DIS integrand.

## B4: comparisons and numerical budget

All external comparisons use

```text
|a-b| <= atol_pair + rtol_source*max(|a|,|b|),
atol_pair = E_num_a + E_num_b.
```

When the relative scale lies below `atol_pair/rtol_source`, a point can pass
only if an analytic zero is expected; otherwise it is
`INCONCLUSIVE_NEAR_ZERO`. Source-bound relative values are `0.001` for the
MassiveDIS component comparison and `1e-5` for the massless benchmark. The old
`0.013` is superseded for the v2 component oracle, and no arbitrary `0.0013`
threshold remains.

The parent internal allowance is `0.001` on the local absolute assembly scale.
Bridge, coupling, structure-function evaluation, Jacobian, grid, quadrature A,
quadrature B and normalization propagation receive equal worst-case shares:

```text
sum_i T_i = 8*0.000125 = 0.001 = T_external.
```

No observed result may tune these shares. Representation and roundoff floors
remain explicit absolute terms; if they dominate a cancellation-scale point,
the result is inconclusive rather than relaxed.

## Normalized-law propagation

For `q=r/Z`, `|r-r_hat|<=E_r`, `|Z-Z_hat|<=E_Z`, and `Z_hat>E_Z>0`:

```text
|q_hat-q|
  <= E_r/(Z_hat-E_Z)
     + |r_hat|*E_Z/(Z_hat*(Z_hat-E_Z)).
```

The first term remains meaningful near zero rate. Independent estimates define
`Z_hat=(Z_A+Z_B)/2` and an interval `E_Z`; closure uses cross ratios
`I_A[r]/Z_B` and `I_B[r]/Z_A`. Same-path self-normalization cannot count as
evidence. There is no standalone normalized-law residual constant.

## Resource and execution boundary

Inherited point and normalization caps remain 63,882 and 98,811. Added
coupling, high-precision envelope and bridge checks raise reference/contract
calls to 2,191. The fixed high-precision sequences contribute 338,400 bounded
beta-function right-hand-side evaluations, raising the total declared cap to
503,284:

```text
63882 + 98811 + 310 + 2*282 + 9*(17+33+65)
  + 282 + 282*(20+40+80+160)*4 = 503284.
```

All coupling, bridge, MassiveDIS, APFEL, positivity, convergence,
normalization and closure checks are `DEFINED_NOT_EXECUTED`. Phase 2B remains
Not Authorized and `NOT_EXECUTED`; Phase 2C and downstream work remain
unauthorized.

## Phase completion report

All commands are run from the repository root in WSL Ubuntu after sourcing
`scripts/pythia_env.sh` where required. Final results are filled only after the
complete local validation pass.

| Exact command | Result |
| --- | --- |
| `python3 scripts/validate_phase1b_closeout.py` | PASS — 20 artifacts, 11 ADRs, 7 lineage records |
| `python3 scripts/validate_phase2_reduced_nc_dis_roadmap.py` | PASS — 9 issues, 24 obligations |
| `python3 scripts/phase2a_contract_review.py` | PASS |
| `python3 scripts/validate_phase2_fonll_a_contract_amendment.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan.py` | PASS |
| `python3 scripts/validate_phase2b_execution_authorization_review.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan_v2.py` | PASS |
| `python3 -m pytest -q analysis/tests/test_phase2b_preauthorization_validation_plan_v2.py` | PASS — 29 passed |
| `python3 -m pytest -q analysis/tests/` | PASS — 446 passed |
| `cargo fmt --all -- --check` | PASS |
| `cargo check --workspace` | PASS |
| `cargo test --workspace` | PASS — 231 passed, 18 ignored |
| `ctest --test-dir physics-engine/build --output-on-failure` | PASS — 1/1 passed |
| `git diff --check` | PASS |

Unresolved scientific limitations remain explicit: the complete NC rate has
only partial independent coverage; the exact accepted-PDF MassiveDIS/APFEL
component comparison, alpha_s provider comparison, bridge validation,
positivity classification, physics quadratures, normalization and closure are
all post-authorization work and remain `NOT_EXECUTED`. Consequently this
revision establishes only a reviewable plan and does not establish physical
closure, positivity, normalization accuracy or execution authorization.

## Next action

Conduct a new execution-authorization review of this exact v2 artifact. Do not
run Phase 2B unless that later review returns authorization.
