# Phase 2B pre-authorization validation plan

## Result

```text
OUTCOME = P1_PREAUTH_PLAN_COMPLETE_READY_FOR_SEPARATE_AUTHORIZATION_REVIEW
PLAN_COMPLETENESS = COMPLETE
PHASE2B_AUTHORIZED = false
PHASE2B_EXECUTION_STATUS = NOT_EXECUTED
```

This follow-on record completes the planning inputs left unresolved by the
FONLL-A contract amendment. It does not authorize Phase 2B and contains no
numerical physics result. Historical Phase 2A remains complete with scientific
decision `INCONCLUSIVE`; ADR-013 remains Proposed.

The authoritative record is
[`contracts/phase2b_preauthorization_validation_plan.json`](contracts/phase2b_preauthorization_validation_plan.json).
Machine-readable records override this summary if they conflict.

## Source review

Load-bearing publication and software bytes were retrieved only under
`/tmp/partonsbi-phase2b-preauth-review/`; no publication bytes are committed.
The JSON source registry records official URLs, retrieval time, SHA-256,
publication/version dates and exact locators for:

- HERA 2015 NC DIS formulae, kinematics and perturbative-QCD fit domain;
- APFEL 2014, FONLL 2010 and pinned APFEL 3.1.1 source;
- official CT18NLO DataVersion 1 and the CT18 publication;
- the FONLLdis/FastKernel and APFEL/FONLLdis published FONLL benchmarks; and
- the independent APFEL++/HOPPET massless DIS benchmark and pinned code.

## Heavy masses and shared coupling

The plan selects the pole-mass convention with `m_c=1.30 GeV` and
`m_b=4.75 GeV`. The convention is a project methodology choice constrained by
the accepted CT18 family; the values are source-supported CT18 defaults. APFEL
uses the pole masses as the charm and bottom flavor thresholds, with a
five-flavor ceiling and top outside scope.

The shared coupling identity is
`ct18nlo_as_mz_0p118_nlo_vfns_mc1p3_mb4p75_nfmax5_v1`:
`alpha_s(M_Z=91.187 GeV)=0.118`, NLO/two-loop running, matching at the pole-mass
thresholds, and `n_f<=5`. APFEL must evolve from this repository-owned tuple;
an APFEL default is not evidence. Independent references receive the same
tuple but use their own evolution. Copying APFEL samples would destroy
independence. The pinned calls are `SetAlphaQCDRef(0.118,91.187)` and
`SetPerturbativeOrder(1)`; mass and threshold controls are likewise serialized
in the authoritative record.

## Theta anchors

The accepted validation domain remains

```text
delta_v    in [-0.20, 0.20]
lambda_sea in [-0.25, 0.25].
```

Exactly nine anchors are fixed: the center, four axis endpoints and four
corners. They are validation anchors, not a prior, and may not be replaced or
augmented in response to results.

## Coordinate and physics-domain contract

The latent coordinates are `(x_Bj,Q2)`, the rate is
`d2sigma/dx_Bj/dQ2`, and the massless-beam configuration is an unpolarized
`e- p` collision with `E_e=27.5 GeV`, `E_p=920 GeV` and
`s=101200 GeV2`. APFEL's `dx_Bj dy` result is converted using

```text
y = Q2/(s*x_Bj)
dy/dQ2 at fixed x_Bj = 1/(s*x_Bj).
```

The fixed physics-validity domain is

```text
6e-7 <= x_Bj <= 0.65
3.5 GeV2 <= Q2 <= 50000 GeV2
0.005 <= Q2/(101200*x_Bj) <= 0.95.
```

This is the explicit intersection of the HERA kinematic envelope, the HERA
perturbative-QCD fit floor chosen for the proof of principle, physical DIS
kinematics and strict accepted PDF support. The numerical grid does not define
this domain. Every boundary is fixed before execution, and no point or region
may be removed after a failure.

## Validation grids and resource bound

Three deterministic log-spaced tensor levels use 17, 33 and 65 nodes in each
coordinate before domain filtering. Each level is augmented with exact `y`
and `Q2` boundaries, one-sided bottom evolution-threshold probes, and
one-sided charm/bottom production-threshold curves. Normalization uses
separate fixed tensor Gauss-Legendre orders 16/32/64 and Clenshaw-Curtis orders
17/33/65 in `(log x_Bj,log Q2)`.

The structural cap is nine anchors, three levels, 63,882 point-grid candidate
evaluations, 98,811 normalization-integrand evaluations, 310 independent
reference evaluations, 163,003 declared evaluations in total, and 64 MiB of
output. Exceeding a count yields `INCONCLUSIVE`. Wall time is provenance, not
an arbitrary scientific gate.

## Tolerances and convergence

| Quantity | Threshold | Basis |
| --- | ---: | --- |
| Published FONLL component comparison | relative `0.013` | Maximum accuracy reported for the independent FONLLdis benchmark |
| Massless NLO NC comparison | relative `1e-5` | Published APFEL++/HOPPET benchmark |
| Integral/grid discretization | relative `0.0013` | One tenth of the weakest independent physics-reference envelope |
| Unit-normalization residual | absolute `0.0013` | Same probability-mass error budget |
| Shared `alpha_s` identity | relative `72*2^-53` | Bounded binary64 path plus high-precision solver residual |
| Jacobian | relative `8*2^-53` | Explicit floating-point operation budget |
| Negative roundoff | `gamma_32*S` plus nonnegative high-precision sign | Local backward-error bound, never a repair |

Integration must meet the final-level tolerance, reduce the preceding
successive difference by at least one half, and agree between both quadrature
families. Grid, support-boundary and positivity classifications must stabilize
between the final two levels. Independent-reference discrepancies must be
inside their source-bound tolerance and change by no more than one tenth of
that tolerance at final refinement. A physical negative or nonfinite value is
`FAIL`; finite admissible results that do not stabilize within the fixed bound
are `INCONCLUSIVE`.

## Independent-reference hierarchy

No complete independent implementation of the accepted theta-dependent
gamma/Z FONLL-A rate is claimed. The repository gate permits an independently
checked decomposition because it requires independent checks of formulae,
normalization, support and sampling, and FONLL is an explicit additive
construction. The hierarchy is:

1. published FONLLdis benchmarks for massive and matched FONLL-A heavy
   structure functions;
2. HOPPET against APFEL++ for massless NLO NC structure functions and reduced
   cross sections;
3. an APFEL-free analytic implementation for HERA charge signs, kinematic
   factors and the `dx dy` to `dx dQ2` Jacobian; and
4. separately implemented Gauss-Legendre and Clenshaw-Curtis normalization.

An APFEL wrapper, second APFEL front end or copied APFEL `alpha_s` table is
internal repetition and satisfies no independence gate. Component agreement
must not be reported as unqualified full end-to-end code equivalence.

## Positivity and normalization policy

The complete gamma/Z FONLL-A NLO `e- p` differential rate must be nonnegative
on the entire declared domain at every anchor. A binary64 negative is merely
roundoff-compatible only if its magnitude is at most `gamma_32*S` and an
at-least-binary128 recomputation is nonnegative. The raw negative remains
recorded. Clipping, `abs()`, `max(rate,0)`, hidden rejected-point removal and
post-hoc support deletion are forbidden. A genuine negative takes precedence
over normalization and reference checks.

For every anchor,

```text
Z_theta = integral_A_z d2sigma_theta/dx_Bj/dQ2 dx_Bj dQ2
p_theta = 1_A_z (d2sigma_theta/dx_Bj/dQ2) / Z_theta
```

must be finite, strictly positive and converged by both quadrature families.
The Phase 2B selected-event check is the lossless-detector case
`epsilon=alpha_theta=1`, so both implementations must integrate `p_theta` to
one. A nontrivial detector kernel remains Phase 2D work. Fixed-`N`, shape-only
semantics remain unchanged; no count likelihood enters.

## Authorization separation and limitations

The mass, coupling, anchors, domain, Jacobian, grids, tolerances, convergence,
reference hierarchy, resource bounds, positivity policy, normalization plan
and failure precedence are complete pre-authorization items.

Actual APFEL evaluations, positivity scans, normalization integrals,
convergence studies, cross-implementation comparisons and selected-event
normalization checks remain `NOT_EXECUTED` post-authorization work. Pointwise
positivity and normalization closure are not established by this plan. The
decomposition does not remove the limitation that no independent comparator
covers the complete project observable end to end. Inclusive NC `e-p` data do
not establish unrestricted flavor separation.

## Phase completion report

All local commands were run from the repository root in WSL Ubuntu after
`source scripts/pythia_env.sh`. Results for the final artifact were:

| Exact command | Result |
| --- | --- |
| `python3 scripts/validate_phase1b_closeout.py` | PASS: 20 artifacts, 11 ADRs, 7 lineage entries |
| `python3 scripts/validate_phase2_reduced_nc_dis_roadmap.py` | PASS: 9 issues, 24 obligations |
| `python3 scripts/phase2a_contract_review.py` | PASS |
| `python3 scripts/validate_phase2_fonll_a_contract_amendment.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan.py` | PASS |
| `python3 -m pytest -q analysis/tests/test_phase2b_preauthorization_validation_plan.py` | PASS: 24 tests |
| `python3 -m pytest -q analysis/tests/` | PASS: 399 tests |
| `cargo fmt --all -- --check` | PASS |
| `git diff --check` | PASS |

The required grep audit was run for `PHASE2B_AUTHORIZED`, `NOT_AUTHORIZED`,
`NOT_EXECUTED`, `clipping`, `abs(`, `standard tolerance`, `reasonable
tolerance` and `phase2_pr_body.tmp.md`. Changed-scope matches are either
negative state/policy assertions, validator prohibitions or adversarial test
mutations. The temporary filename is absent, untracked and unreferenced.

One initial combined validation wrapper reached its 120-second command-harness
limit (`exit 124`) before buffered results returned. It is not used as
evidence; every required command was rerun separately and passed as recorded
above.

The reproducible command set is:

```text
python3 scripts/validate_phase1b_closeout.py
python3 scripts/validate_phase2_reduced_nc_dis_roadmap.py
python3 scripts/phase2a_contract_review.py
python3 scripts/validate_phase2_fonll_a_contract_amendment.py
python3 scripts/validate_phase2b_preauthorization_validation_plan.py
python3 -m pytest -q analysis/tests/
cargo fmt --all -- --check
git diff --check
```

## Next step

A separate decision may review whether to authorize execution of this exact
plan. This task does not authorize or begin that execution.
