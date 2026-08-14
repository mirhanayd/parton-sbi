# ADR-013: Source-backed Reduced NC DIS observation-law contract

## Status

Proposed

## Context

Phase 2A defined the mathematical and scientific contract for the Reduced NC
DIS observation model using primary or authoritative source evidence. The
review binds the selected-event law, posterior target, paper claim boundary,
and the gates that must pass before any later numerical closure phase can be
authorized.

PR #63 merged the Phase 2A source-backed contract review. The accepted
machine-readable decision is conservative: Phase 2A is complete, but its final
scientific decision is `INCONCLUSIVE`.

## Primary-Source Methodology

Every load-bearing claim relies on authoritative references or repository facts
recorded in the source registry and claim ledger. Missing primary evidence is
not converted into support.

## Exact Contract

- Formula: Standard NC DIS differential cross section.
- Electroweak scheme: `G_F` scheme.
- Perturbative scheme: NLO VFNS remains incompletely bound for the full
  heavy-flavor contract.
- PDF family: `ct18nlo_two_parameter_boundary_v2`, the accepted versioned
  sum-rule-projected baseline, with strict grid support.

## Selected-Event Law

The accepted baseline is a selected-event, fixed-`N`, shape-only observation
law. Count/rate information is not part of the Phase 2A baseline.

## Posterior Law

The posterior target is `p(theta | D, N, selected)` for an event set `D`, not an
instantaneous single-proton PDF inferred from one event.

## Gate Summary

The accepted Phase 2A gate grouping is:

- `SUPPORTED`: `posterior_target_coherence`,
  `fixed_n_shape_only_semantics`, `paper_claim_boundary_consistency`,
  `selected_event_conditioning_coherence`.
- `SUPPORTED_WITH_QUALIFICATION`:
  `finite_positive_normalization_reviewability`, `strict_support_contract`,
  `normalized_detector_kernel_contract`,
  `bounded_identifiability_and_information_plan`.
- `PRIMARY_EVIDENCE_UNAVAILABLE`: `exact_formula_contract`,
  `no_hidden_clipping`, `bounded_phase2b_validation_plan`.

The unresolved `exact_formula_contract` includes the `CLAIM_HEAVY_FLAVOR`
limitation: the review does not bind a single complete, internally consistent
heavy-flavor scheme from primary evidence. The full differential-rate
positivity premise is therefore not established by Phase 2A.

## Decision Derivation

Because required primary evidence remains unavailable, the final Phase 2A
scientific decision is `INCONCLUSIVE`.

This is neither a PASS nor a FAIL. It is a completed conservative review result
that blocks Phase 2B authorization until the missing evidence and validation
plan details are addressed by a later reviewed decision.

## Phase 2B Boundary

The Phase 2B proposal remains:

- `plan_completeness = INCOMPLETE`
- `authorization = NOT_AUTHORIZED`
- `execution_status = NOT_EXECUTED`

Anchors, grids, tolerances, convergence rules, and independent-reference
details remain unresolved. No Phase 2B numerical work is authorized by this
ADR or by the Phase 2A closeout.

## Nonclaims

The bounded paper nonclaims remain in force. The review does not claim
full-generator equivalence, showering, ISR, hadronization, beam-remnant
modelling, underlying event, full collider realism, production-grade detector
simulation, unrestricted full-flavor determination, global-fit replacement,
universal identifiability, guaranteed contraction for every theta direction,
legacy D2 completion, or full-generator closure.

## Authorization

- `PHASE2A_CONTRACT_REVIEW_AUTHORIZED = true`
- `PHASE2B_AUTHORIZED = false`
- `NUMERICAL_PHYSICS_AUTHORIZED = false`
- `IMPLEMENTATION_AUTHORIZED = false`
- `D2_AUTHORIZED = false`

## Consequences

Phase 2A is closed as a completed source-backed contract review with an
`INCONCLUSIVE` scientific decision. Phase 2B issue #55 remains Backlog,
Not Evaluated, and Not Authorized.

## Follow-on FONLL-A contract amendment

A later bounded source review is recorded in
`docs/reduced_nc_dis/contracts/phase2_fonll_a_contract_amendment.json`. Its
derived outcome is `D1_PREPARE_FONLL_A_NLO_CONTRACT_AMENDMENT`. The historical
Phase 2A result remains `INCONCLUSIVE`; this is a versioned follow-on
disambiguation, not a retroactive Phase 2A PASS.

The amendment selects APFEL FONLL-A at NLO for the reduced NC DIS formula. It
pins APFEL 3.1.1 at commit
`72bf6ec7c72c923dd2115f2a98c6f593f9c91d2a`, the NC `e-/e+` HERA convention,
`mu_F = mu_R = Q`, the `(x_Bj,Q2)` differential measure and its `dx dy` to
`dx dQ2` Jacobian, APFEL's enabled power-two FONLL damping, the accepted
`ct18nlo_two_parameter_boundary_v2` family, and the strict no-extrapolation,
no-clipping, no-absolute-value and no-post-hoc-support-deletion policy.

This selection narrows the previous generic `FONLL-like NLO VFNS` wording. It
does not change the observation law, PDF-family identity, research question,
or paper nonclaims. The accepted records do not require complete heavy-flavor
structure functions specifically from APFEL++; pinned APFEL exposes the
complete FONLL-A NC observable and an external boundary interface.

The heavy-quark mass convention and values, exact shared `alpha_s` identity,
theta anchors, kinematic grids, justified tolerances, convergence rules,
complete independent FONLL-A reference, and resource bound remain unresolved
pre-authorization evidence. Pointwise complete-rate positivity is not proved.
Actual positivity scans, normalization integrations, and independent numerical
closure are post-authorization validation and have not occurred. Phase 2B
remains `NOT_AUTHORIZED` and `NOT_EXECUTED`.

## Follow-on Phase 2B pre-authorization plan

The subsequent versioned pre-authorization plan derives
`P1_PREAUTH_PLAN_COMPLETE_READY_FOR_SEPARATE_AUTHORIZATION_REVIEW`. It binds
the mass/coupling configuration, anchors, domain, grids, justified tolerances,
convergence, independent-reference decomposition, resource bounds, positivity
policy and normalization strategy. This does not rewrite this ADR's historical
review result: Historical Phase 2A remains `INCONCLUSIVE`, and ADR-013 remains
Proposed.

Planning completeness is not execution authority. Phase 2B remains `NOT_AUTHORIZED` and `NOT_EXECUTED`;
issue #55 remains Backlog with Gate
Decision Not Evaluated. No numerical positivity, normalization or independent
closure result is asserted.

## Follow-on Phase 2B execution authorization review

The subsequent authorization review derives
`AR2_PREAUTH_PLAN_REVISION_REQUIRED`. This successor decision preserves the
P1 planning-completeness result but does not authorize execution. It identifies
bounded revisions to the shared `alpha_s` identity, complete-rate
high-precision sign adjudication, exact accepted-PDF bridge closure,
quadrature implementation independence, and tolerance/error-budget semantics.

Historical Phase 2A remains `INCONCLUSIVE`; this ADR remains Proposed. Phase
2B remains `NOT_AUTHORIZED` and `NOT_EXECUTED`, and no downstream phase is
authorized.

## Follow-on Phase 2B preauthorization v2 successor

The planning successor derives
`RV1_PREAUTH_V2_COMPLETE_READY_FOR_NEW_AUTHORIZATION_REVIEW`. It resolves the
four AR2 planning blockers with a predeclared dual-provider coupling test,
propagated negative-rate uncertainty, exact bridge and quadrature provenance,
mixed near-zero comparison semantics, and an explicit numerical error budget.

Historical Phase 2A remains `INCONCLUSIVE`; ADR-013 remains Proposed. The v1
plan and AR2 review remain immutable historical records. Phase 2B remains
`NOT_AUTHORIZED` and `NOT_EXECUTED`, and no downstream phase is authorized.

## Follow-on Phase 2B v2 execution authorization review

The independent successor review derives
`AR2_PREAUTH_V2_REVISION_REQUIRED`. It does not accept the observed
approximately 0.1% APFEL/MassiveDISsFunction component discrepancy as a
formal parent budget for the complete rate, and the equal eight-way allocation
is not a derived error structure. Additional bounded revisions are required
for AS2 and bridge claim coverage, frozen post-authorization test identities,
the per-flavor-segment resource count, and the load-bearing NumPy pin.

Historical Phase 2A remains `INCONCLUSIVE`; ADR-013 remains Proposed. Phase 2B
remains `NOT_AUTHORIZED` and `NOT_EXECUTED`, and no downstream phase is
authorized.

## Follow-on Phase 2B preauthorization V3 successor

The V3 scientific successor derives `V3R6_MULTIPLE_BLOCKERS_REMAIN`. It
replaces the rejected global/equal-share budget and upstream sign-envelope
model with gate-local validation, an exact PDF bridge contract, and strict
implemented-rate nonnegativity. Its proposed continuous finite-provider AS2
design remains explicitly blocked rather than being called a certificate.

V3 is not complete: alpha and massless-reference execution semantics and the
numerical runtime identity remain underbound, grid and quadrature remainder
acceptance remains scientifically underived, and the FONLL component comparator
is not fully executable from frozen inputs. Historical Phase 2A remains
`INCONCLUSIVE`; this ADR remains Proposed. Phase 2B remains `NOT_AUTHORIZED`
and `NOT_EXECUTED`, and no downstream phase is authorized.

## Follow-on Phase 2B preauthorization blocker resolution

The blocker-resolution record derives `BR5_MULTIPLE_BLOCKERS_REMAIN`. It is not
an execution authorization review and it created no V4 successor plan.

It resolves the exact CT18 and APFEL coupling representations from pinned
source, including the sentinel magnitude clamp in LHAPDF's alpha interpolation
and the truncated one-sixth literal in APFEL's fixed-step recursion; it closes
the `4*pi` conversion question; it binds a rigorous interval backend; and it
establishes that validated initial-value-problem integration is not required
because the frozen recursion is a finite arithmetic composition. It binds the
MassiveDIS v1.2 source identity and recovers the released massless benchmark
program.

Three blocker families remain. The platform natural logarithm invoked by both
coupling providers is selected at load time from CPU features and carries only
an author-stated error analysis, so neither implemented provider can be
enclosed. No independent executable FONLL-A comparator is bound. No rigorous
quadrature remainder is obtainable against the accepted binary64 black-box
integrand, and no accepted record declares a project precision target for the
normalized law.

Historical Phase 2A remains `INCONCLUSIVE`; this ADR remains Proposed. Phase 2B
remains `NOT_AUTHORIZED` and `NOT_EXECUTED`, and no downstream phase is
authorized.

## Follow-on Phase 2B numerical-contract policy decision

The policy decision derives `PD1_ADOPT_AP1_AND_NP2`. It is a scientific
contract-policy decision, not an authorization review and not a successor
preauthorization plan; no V4 was created.

`AP1_APFEL_ALPHA_IS_AUTHORITATIVE_SIMULATOR_COUPLING` makes APFEL 3.1.1's
internal coupling the authoritative coupling of the reduced simulator. The
decisive source fact is that `ComputeDISOperators.f` evaluates `a_QCD` directly
and the external PDF callback carries no coupling, so LHAPDF's `alphasQ` is
never consulted by the DIS computation and the previous continuous-equivalence
gate would have certified a function outside the observation law. CT18NLO
coupling metadata becomes a provenance and declared-convention compatibility
constraint covering `alpha_s(M_Z)`, perturbative order, flavour thresholds and
the heavy-flavour setup. The CT18NLO running-order tension between
`AlphaS_OrderQCD` and its `SetDesc` is recorded as an unresolved compatibility
item and assigned to a required, non-gating diagnostic. No provider-equivalence
claim is permitted.

`NP2_REQUIRE_EMPIRICAL_NUMERICAL_STABILITY_NOT_CERTIFIED_ACCURACY` fixes the
normalization claim type. A rigorous remainder is not implementable against the
accepted binary64 black-box integrand, and the proof-of-principle claim rests on
empirical posterior calibration rather than a quadrature theorem. Normalization
remains part of the probability-law contract and must remain finite and strictly
positive, with no clipping or repair of any kind. No numerical tolerance was
selected; the decision fixes only that a target must be predeclared.

Both policies replace a preauthorization gate explicitly and narrow the paper
claim boundary. Neither changes the observation law, the posterior target or the
research question. `BLOCKER_FONLL_REFERENCE_EXECUTION_SPEC` survives the
decision, so a successor plan may be drafted but cannot reach a complete state
until the independent-reference scope question is separately recorded.

Historical Phase 2A remains `INCONCLUSIVE`; this ADR remains Proposed. Phase 2B
remains `NOT_AUTHORIZED` and `NOT_EXECUTED`, and no downstream phase is
authorized.
