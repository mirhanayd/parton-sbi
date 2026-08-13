# Phase 2 FONLL-A heavy-flavor contract amendment

## Result

```text
DECISION = D1_PREPARE_FONLL_A_NLO_CONTRACT_AMENDMENT
HISTORICAL_PHASE2A_STATUS = COMPLETE
HISTORICAL_PHASE2A_SCIENTIFIC_DECISION = INCONCLUSIVE
PHASE2B_AUTHORIZED = false
PHASE2B_EXECUTION_STATUS = NOT_EXECUTED
```

This is a follow-on contract amendment. It does not convert historical Phase
2A into PASS and does not authorize formula implementation or numerical
closure.

## Evidence method

The requested `/tmp/partonsbi-phase2a-evidence-review/` cache was absent at
preflight, so its initial status was `EVIDENCE_CACHE_INCOMPLETE`. The review
retrieved only the previously identified versioned HERA 2015, APFEL 2014,
FONLL 2010 and APFEL++ 2017 sources and the official APFEL 3.1.1 release. All
bytes remained under `/tmp`; none are committed.

The load-bearing software identity is APFEL tag 3.1.1 at commit
`72bf6ec7c72c923dd2115f2a98c6f593f9c91d2a`. Its source exposes FONLL-A,
neutral-current structure functions, mass and threshold controls, scale and
`alpha_s` controls, damping controls, and the `ExternalSetAPFEL` boundary hook.
Exact source hashes and locators are serialized in the amendment artifact.

## Candidate evidence matrix

Each candidate was checked for exact identity, order, flavor treatment,
masses, thresholds, matching, coefficient functions, scales, `alpha_s`, NC
`e-/e+` applicability, accepted-family compatibility, software exposure,
validity domain, positivity, no-clipping testability, independent closure,
paper impact, and contract impact.

| Candidate | Source binding | Accepted family | Software binding | Threshold scope | Result |
| --- | --- | --- | --- | --- | --- |
| APFEL FONLL-A NLO | Complete for scheme selection | Compatible through the pinned external boundary hook, bridge unimplemented | APFEL 3.1.1 pinned | Massive GM-VFN with explicit power-two damping | Eligible |
| HERA RTOPT NLO VFNS | HERA configuration bound; full implementation contract absent | Conceptually compatible | No pinned project implementation | General-mass | Eliminated |
| APFEL FFN | Explicit | Incompatible without a new fixed-flavor PDF/`alpha_s` contract | APFEL 3.1.1 pinned | Massive fixed flavor | Eliminated |
| APFEL ZM-VFN | Explicit | Compatible only after domain narrowing | APFEL 3.1.1 pinned | Not reliable near heavy thresholds | Eliminated |

The required special classifications are:

```text
FFN_REQUIRES_NEW_PDF_CONTRACT
ZMVFN_REQUIRES_PREDECLARED_VALIDITY_DOMAIN
RTOPT_IMPLEMENTATION_PATH_NOT_BOUND
```

## Decision matrix

| Criterion | FONLL-A | RTOPT | FFN | ZM-VFN |
| --- | --- | --- | --- | --- |
| preservation of research objective | HIGH | HIGH | MEDIUM | MEDIUM |
| exact source binding | HIGH | MEDIUM | HIGH | HIGH |
| compatibility with accepted PDF family | MEDIUM | MEDIUM | LOW | HIGH |
| reproducible software configuration | HIGH | LOW | HIGH | HIGH |
| minimal contract change | HIGH | MEDIUM | LOW | MEDIUM |
| threshold physics fidelity | HIGH | HIGH | HIGH | LOW |
| later no-clipping testability | HIGH | LOW | HIGH | HIGH |
| independent closure strength | MEDIUM | LOW | MEDIUM | HIGH |
| paper claim preservation | HIGH | HIGH | MEDIUM | MEDIUM |
| reversibility | HIGH | MEDIUM | LOW | HIGH |

The machine artifact contains the evidence-backed rationale for every rating.

## FONLL-A findings and amendment

FONLL-A NLO disambiguates the generic `FONLL-like NLO VFNS` wording; it does
not replace the scientific question. APFEL's controls are sufficient to define
a reproducible later physics configuration. No accepted PartonSBI record
requires the complete heavy-flavor structure functions specifically from
APFEL++. Using pinned APFEL for the complete FONLL-A NC observable is
compatible with the reduced-model research direction, subject to a separately
reviewed and tested external-boundary bridge.

The amendment binds:

- APFEL 3.1.1 FONLL-A at NLO;
- the accepted `ct18nlo_two_parameter_boundary_v2` family and projected
  baseline;
- five-flavor project scope, with top outside the study;
- the FONLL massive-plus-difference matching construction;
- APFEL's enabled power-two damping treatment;
- `mu_F = mu_R = Q`;
- the HERA unpolarized `e-/e+` NC gamma/Z formula;
- latent `(x_Bj,Q2)` coordinates, `d2sigma/dx dQ2`, and
  `dy/dQ2 = 1/(s*x_Bj)` at fixed `x_Bj`;
- strict support, no extrapolation, no clipping, no absolute-value repair, and
  no post-hoc support deletion; and
- failure before any downstream use on nonfinite, negative, unsupported,
  unnormalizable, or reference-inconsistent rates.

## Pre-authorization versus post-authorization evidence

Pre-authorization evidence includes the exact formula and heavy-flavor
convention, support policy, no-repair rule, anchors, grids, justified
tolerances, convergence rules, independent-reference strategy, resource bound,
and failure precedence.

This amendment resolves the formula identity, FONLL-A convention, support and
no-repair policy, and failure precedence. It leaves the mass convention and
values, shared `alpha_s` identity, anchors, grids, tolerances, convergence
rules, complete independent FONLL-A reference, and resource bound unresolved.

Post-authorization validation may include an actual positivity scan,
normalization integration, and independent numerical closure. None was
performed. A numerical result cannot be used retroactively as the
pre-authorization plan that was required to authorize it.

## Authorization and limitations

All implementation, APFEL execution, numerical physics, event, dataset,
detector, neural, legacy D2, and Phase 2B authorization flags remain false.
Pointwise positivity of the complete deformed differential rate remains
unproved. Inclusive NC `e-p` data do not establish unrestricted flavor
separation, and no generator-level claim is added.

## Validation

The static-only completion validation passed:

```text
python3 scripts/validate_phase1b_closeout.py
VALID partonsbi.phase1b.closeout-manifest.v2 artifacts=20 adrs=11 lineage=7

python3 scripts/validate_phase2_reduced_nc_dis_roadmap.py
VALID partonsbi.phase2.reduced-nc-dis-roadmap.v2 issues=9 obligations=24 offline_live_github=false

python3 scripts/phase2a_contract_review.py
VALID phase2a.contract_review

python3 scripts/validate_phase2_fonll_a_contract_amendment.py
VALID phase2.fonll_a_contract_amendment

python3 -m pytest -q analysis/tests/test_phase2_fonll_a_contract_amendment.py
17 passed

python3 -m pytest -q analysis/tests/
375 passed

cargo fmt --all -- --check
PASS

git diff --check
PASS
```

No APFEL/APFEL++ calculation, cross-section evaluation, positivity scan,
normalization integration, event generation, dataset construction, detector
simulation, or neural training was run.

## Next step

A separate review must bind every unresolved pre-authorization item and make
the Phase 2B proposal complete. This next step is not authorized here and must
not execute numerical physics.
