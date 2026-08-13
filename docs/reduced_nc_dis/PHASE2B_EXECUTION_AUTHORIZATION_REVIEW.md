# Phase 2B execution authorization review

## Decision

```text
DECISION = AR2_PREAUTH_PLAN_REVISION_REQUIRED
PHASE2B_BOUNDED_NUMERICAL_VALIDATION_AUTHORIZED = false
PHASE2B_EXECUTION_AUTHORIZED = false
PHASE2B_EXECUTION_STATUS = NOT_EXECUTED
```

The merged P1 record is complete as a reviewable plan, but this adversarial
authorization review does not authorize its execution. The accepted FONLL-A
contract and research direction remain viable; four bounded planning gaps must
be amended before a later authorization review can return AR1.

The authoritative successor record is
[`contracts/phase2b_execution_authorization_review.json`](contracts/phase2b_execution_authorization_review.json).
It binds the P1 artifact at SHA-256
`7eb8834eb8435532a85bd7d49b173b03e57a268f69f9676e0effbd877903672b`
and the FONLL-A amendment at
`10cf19fedcdfe1b94e18ff89d1ae09514a31b8e0f6b055beeb729d61b6c32da8`.

## Audit result

The pole masses `m_c=1.30 GeV`, `m_b=4.75 GeV`, thresholds equal to those
pole masses, and `n_f<=5` form a coherent mass contract. The coupling contract
does not yet prove one numerical identity: CT18NLO declares an interpolated
HOPPET running solution, while the plan gives APFEL an internally evolved
two-loop coupling and compares it only with a new analytic solver. A shared
repository name does not close that difference.

The kinematic domain is valid as the predeclared intersection of the `x_Bj`,
`Q2`, and `y` inequalities. The rectangular tensors are candidate grids only;
the fixed kinematic mask excludes inconsistent combinations without looking at
rate results. The nine anchors exactly cover the center, axis endpoints and
corners, but establish claims only at those anchors—not every interior theta.

The 17/33/65 point grids are nested. The exact resource arithmetic closes:

```text
point evaluations         = 63,882
normalization evaluations = 98,811
reference evaluations     =    310
total                      = 163,003
```

There is no unbounded adaptive loop or continue-until-pass rule.

## Authorization blockers

1. Bind one shared `alpha_s` object across CT18NLO's `ipol`/HOPPET
   provenance, APFEL and the independent oracle, including threshold-side
   matching and an evidence-derived comparison rule.
2. Replace or operationally bind the complete-rate binary128 adjudicator.
   Reassembling binary64 APFEL outputs in binary128 does not recompute APFEL's
   internal coefficient and evolution calculations at high precision.
3. Add independent closure for the exact deformed-PDF flavor map and
   `ExternalSetAPFEL` bridge. Also bind provenance or tests showing that the
   two normalization quadratures do not share one computational core.
4. Replace the factor-of-ten-only `0.0013` integration and normalization
   tolerances with a complete error allocation, and define relative comparison
   behavior near zero.

The published `0.013` FONLL and `1e-5` massless comparison envelopes are
source-backed but still need explicit near-zero semantics. The analytic
Jacobian `8*2^-53` tolerance is authorized. The `72*2^-53` coupling tolerance
does not test the CT18 coupling object, and `gamma_32*S` covers only the outer
assembly rather than APFEL internals; both are unjustified for AR1 as written.

## Independent-reference conclusion

The repository's `INDEPENDENT_NUMERICAL_CLOSURE_PLAN` permits a component
decomposition; it does not categorically require a second complete FONLL-A
program. The present decomposition is nevertheless insufficient. Analytic
electroweak/Jacobian checks are fully independent, and published massless,
massive and matched benchmarks are useful component evidence. The exact
accepted PDF bridge and cross-object coupling identity remain unvalidated,
while quadrature implementation independence is asserted rather than bound.

## Failure and claim boundaries

The no-clipping intent is retained: no `abs()`, zero replacement,
`max(rate,0)`, hidden point deletion or support shrinkage is allowed. A genuine
negative must fail; unavailable high-precision adjudication is inconclusive.
One bad anchor cannot be averaged away, resource exhaustion cannot become a
pass, and an inconclusive result is not a pass.

Even a later successful execution could claim only bounded validation of the
reduced NC DIS FONLL-A observation law. It would not establish generator,
shower, hadronization, detector, global-fit, unrestricted flavor-identification
or production-precision claims.

## Historical and execution state

Historical Phase 2A remains `COMPLETE/INCONCLUSIVE`; ADR-013 remains Proposed.
The FONLL-A selection and P1 plan are unchanged. Phase 2B remains Open,
Backlog, Gate Decision Not Evaluated, Not Authorized and `NOT_EXECUTED`.
Phase 2C, events, datasets, detector work, training, neural work, legacy D2 and
full-generator execution all remain unauthorized.

## Phase completion report

All commands were run from the repository root in WSL Ubuntu after sourcing
`scripts/pythia_env.sh`. The final local results were:

| Exact command | Result |
| --- | --- |
| `python3 scripts/validate_phase1b_closeout.py` | PASS: 20 artifacts, 11 ADRs, 7 lineage entries |
| `python3 scripts/validate_phase2_reduced_nc_dis_roadmap.py` | PASS: 9 issues, 24 obligations |
| `python3 scripts/phase2a_contract_review.py` | PASS |
| `python3 scripts/validate_phase2_fonll_a_contract_amendment.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan.py` | PASS |
| `python3 scripts/validate_phase2b_execution_authorization_review.py` | PASS |
| `python3 -m pytest -q analysis/tests/test_phase2b_execution_authorization_review.py` | PASS: 18 tests |
| `python3 -m pytest -q analysis/tests/` | PASS: 417 tests |
| `cargo fmt --all -- --check` | PASS |
| `git diff --check` | PASS |

The unresolved scientific limitations are exactly the four authorization
blockers above. No numerical physics result was produced or used to choose
AR2.

## Next action

Amend and separately review the P1 plan to close the four blockers. No Phase
2B numerical work may begin until a later authorization review returns AR1.
