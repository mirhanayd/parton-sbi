# Phase 2B FONLL validation policy V1

## Result

```text
OUTCOME = FPD3_ADOPT_HYBRID_COMPONENT_VALIDATION_POLICY
PROPORTIONALITY = SCIENTIFICALLY_DESIRABLE_BUT_NOT_REQUIRED_GATE
DISCLOSURE = DISCLOSURE_SCIENTIFICALLY_SUFFICIENT
TERMINOLOGY = TERMINOLOGY_REPLACEMENT_JUSTIFIED
RESEARCH_QUESTION_IMPACT = UNCHANGED
V4 = V4_SUCCESSOR_PLANNING_NOW_WARRANTED
PHASE2B_AUTHORIZED = false
PHASE2B_EXECUTION_STATUS = NOT_EXECUTED
```

Policy decision only. No V4 was created, no authorization review was performed,
and no physics was executed. The authoritative record is
[`contracts/phase2b_fonll_validation_policy_v1.json`](contracts/phase2b_fonll_validation_policy_v1.json).

Predecessors bound and unmodified: FONLL-A amendment `10cf19fe…`, V3
`78a02968…`, blocker resolution `d66a1bbc…`, numerical policy `a855dfeb…`.
`AP1` and `NP2` are unchanged.

## What the original requirement actually said

This is the crux, and the accepted records answer it directly.

The Phase 2A obligation `INDEPENDENT_NUMERICAL_CLOSURE_PLAN` asks *"Is there a
bounded, independent **plan** to test formulae, normalization, support, and
sampling?"* Its pass condition is:

> Phase2B has a finite reproducible plan capable of returning PASS, FAIL, or
> INCONCLUSIVE.

Its fail condition is circularity, unboundedness, adaptivity to failures, or
missing tolerances. The underlying accepted claim is literally *"A bounded
numerical closure plan is required."*

The v1 execution authorization review then states, in terms:

> A component decomposition can satisfy `INDEPENDENT_NUMERICAL_CLOSURE_PLAN`; a
> wholly independent full FONLL-A program is not categorically required.

And the FONLL-A amendment's own scheme-selection table rated FONLL-A **MEDIUM**
on *independent closure strength* and selected it anyway, over ZM-VFN which
scored **HIGH** on exactly that criterion. The accepted contract knowingly
traded maximal independent-closure strength against threshold physics fidelity,
research-objective preservation and PDF-family compatibility.

So:

1. **Did the original requirement require an independent executable
   implementation for every load-bearing component? No.**
2. **Did it require a credible independent closure strategy? Yes** — bounded,
   non-circular, deterministic, with declared reference provenance and failure
   precedence.
3. **Did any accepted record promise end-to-end independent FONLL-A? No** — the
   v1 review says the opposite.
4. **Is the present executable-FONLL requirement original? No.** It is a later
   and progressively stronger interpretation introduced in the v2/V3 planning
   successors and hardened by the blocker-resolution review.

That is a reconstruction, not a relaxation. The v1 review *did* find the
decomposition insufficient — but for three specific defects, all since
addressed: the unvalidated PDF bridge (now `B1`–`B8` against a hash-bound
exact-integer oracle), the unvalidated shared-coupling node (resolved by `AP1`),
and asserted-rather-than-bound quadrature independence (now two hash-bound
implementations with disjoint provenance).

## Evidence classes

| Class | Can establish | Cannot establish |
| --- | --- | --- |
| `E1` executable independent oracle | agreement of two independent implementations at compared points under matched configuration | correctness of the shared specification; behaviour off the compared points; an error bound |
| `E2` published independent benchmark | that the scheme and code family were independently cross-checked at *that* configuration | anything about *this* frozen build; executable replication; a transferable tolerance |
| `E3` independent analytic check | exact correctness of the checked algebraic relation | anything about convolutions, coefficient functions or evolution |
| `E4` semantic implementation crosscheck | that data crosses an interface with the intended identity and transformation | that the physics downstream is correct |
| `E5` source provenance only | what was run; conformance to a declared convention | numerical correctness of any output |
| `E6` internal self-convergence | numerical stability and reproducibility | correctness, an error bound, or independence |

## Current validation graph

| Node | Class | Independent | Mode | Future test | Residual risk |
| --- | --- | --- | --- | --- | --- |
| complete NC observable | `E6` | no | composition | — | end-to-end composition error not independently detectable |
| electroweak assembly | `E3` | yes | static | `TEST_EW_JACOBIAN` | outer assembly only |
| massless coefficients | `E2` | yes | published | `TEST_MASSLESS` | candidate-side settings not yet frozen |
| massive contribution | `E2` | yes | published | — | no version-matched replication |
| FONLL matching difference | `E2` | yes | published | — | no exact project configuration |
| PDFs | `E5` | yes | static | `TEST_BRIDGE` identity | byte identity is not physical correctness |
| PDF → APFEL bridge | `E4` | yes | executable | `TEST_BRIDGE` | semantics only |
| `alpha_s` | `E5` | yes | static + diagnostic | compatibility check + `AP1` diagnostic | CT18 running-order tension unresolved |
| coordinate / Jacobian | `E3` | yes | static | `TEST_EW_JACOBIAN` | none beyond the identities |
| numerical integration | `E6` | no | two disjoint implementations | `TEST_QUADRATURE_A/B` | independence of implementation, not of integrand |
| normalization | `E6` | no | executable | `TEST_NORMALIZATION` | a bias common to both paths would escape |
| normalized-law assembly | `E3` | yes | algebraic | `TEST_NORMALIZED_LAW` | inherits normalization risk |

**No end-to-end independent closure is claimed.** Component evidence is not
collapsed into an end-to-end claim.

## Proportionality

`SCIENTIFICALLY_DESIRABLE_BUT_NOT_REQUIRED_GATE`.

The paper claim is methodological. Its conclusions are conditional on the
explicitly defined simulator: if the frozen FONLL-A implementation contained an
error, the question *"can amortized SBI recover theta from data generated by
this declared law"* would still be assessable. What would become false is any
statement that the law is the true physics — which the accepted nonclaims
already forbid. A second complete independently executable FONLL-A
implementation is a physics-software project comparable to or larger than the
inference study it would support, and it would validate APFEL rather than the
inference method.

This is **not** proportionality used as an excuse for weak physics. Every
independent check that is actually available is made mandatory and gating by
this policy, and the uncovered residual is named rather than absorbed.

## Failure modes

| Failure | Classification |
| --- | --- |
| wrong PDF mapping / flavour / sign / zero / support | `DETECTABLE_BY_CURRENT_PLAN` |
| incorrect electroweak assembly | `DETECTABLE_BY_CURRENT_PLAN` |
| wrong heavy-quark masses | `DETECTABLE_BY_CURRENT_PLAN` (as configuration) |
| wrong `alpha_s` configuration | `DETECTABLE_BY_CURRENT_PLAN` (convention) |
| APFEL internal coefficient-function error | `PARTIALLY_DETECTABLE` |
| incorrect FONLL scheme / damping / order | `PARTIALLY_DETECTABLE` |
| wrong scale settings | `PARTIALLY_DETECTABLE` |
| normalization error | `PARTIALLY_DETECTABLE` |
| **correctly configured, correctly interfaced, internally wrong FONLL matching term** | **`NOT_INDEPENDENTLY_DETECTABLE`** |

The last row is the honest residual this policy discloses rather than removes.

**Posterior calibration does not validate the physics.** Calibration and
coverage are measured against the same simulator that generated the data, so
they are circular with respect to the correctness of the observation law. They
validate the inference pipeline, nothing more.

## The decision

`FR1` is rejected. It would be required if executable independence were an
accepted non-negotiable, if missing `E1` made the law *uninterpretable* rather
than merely less validated, or if disclosure would overstate credibility. None
holds — and it is explicitly **not** rejected on a "more validation is always
better" basis, which is not a scientific argument either way.

`FR2` is sound but insufficiently specific: it does not freeze the per-node
coverage matrix, which would leave open a post-hoc choice of which component
checks counted as "available" — the same failure mode `NP2` forbids elsewhere.

**`FR3` is adopted, and it is not a compromise.** The node set genuinely
partitions on evidence *availability*: independent validation is bindable for
the electroweak assembly, the Jacobian, the PDF identity and bridge, the two
quadrature implementations and the massless sector; it is not bindable for the
massive contribution, the matching difference or the end-to-end rate. The policy
consequence differs between those groups, so a single uniform rule would be less
accurate than the evidence supports. `FR3` is **stronger** than `FR2`: available
independent checks become mandatory and gating, the coverage matrix is frozen
before authorization, and a node whose available check is skipped **fails**
rather than being reclassified.

## Terminology

`TERMINOLOGY_REPLACEMENT_JUSTIFIED`. The old rule — *no load-bearing
UNVALIDATED node* — is unsatisfiable in principle under the accepted contract,
because the end-to-end rate can never carry `E1` without a second complete
implementation the contract never required. As a completion criterion it makes a
successor plan permanently unreachable for a reason unrelated to scientific
merit.

`NO_UNDISCLOSED_LOAD_BEARING_VALIDATION_GAP` keeps the rigour where it belongs:
every load-bearing node must carry an evidence class, a validation method, a
residual-risk statement, and explicit paper disclosure wherever independent
executable validation is absent. It does **not** permit an unnamed gap, does
**not** turn a disclosed gap into a `PASS`, and does **not** allow reclassifying
a node to avoid running an available check.

## Preserved non-equivalences

```text
PUBLISHED            != EXECUTABLE
BENCHMARKED          != FULLY_VALIDATED
COMPONENT_VALIDATION != END_TO_END_VALIDATION
DISCLOSED_LIMITATION != PASS
ABSENCE_OF_EVIDENCE  != EVIDENCE_OF_CORRECTNESS
CALIBRATED_POSTERIOR != VALIDATED_PHYSICS_IMPLEMENTATION
```

## Contract impact

| Scope | Classification |
| --- | --- |
| `INDEPENDENT_NUMERICAL_CLOSURE_PLAN` obligation | `DISAMBIGUATES_EXISTING_CONTRACT` |
| `G1` gate semantics | `REPLACES_VALIDATION_GATE_SEMANTICS` |
| successor completion criterion | `REPLACES_VALIDATION_GATE_SEMANTICS` |
| paper claim boundary | `NARROWS_CLAIM_BOUNDARY` |
| research question | `UNCHANGED` |

Both replacements are recorded explicitly. Seven research-question invariants
are asserted and validator-checked.

## Paper impact

**MAY claim** — the APFEL version, commit and configuration are frozen and
source-defined; independent published FONLL and heavy-flavour benchmark evidence
exists for the scheme and code family; every available independent component
test was specified and performed; the electroweak assembly and Jacobian were
checked against independent analytic oracles; the PDF interface was checked
against a hash-bound deterministic oracle; normalization was checked for
reproducible numerical stability; **the absence of an independently executable
exact FONLL-A comparator is a stated limitation**; the inference conclusions are
conditional on the explicitly defined frozen reduced simulator.

**MUST NOT claim** — independently executable FONLL-A closure; that the
published benchmark proves the correctness of the present frozen
implementation; production-precision FONLL validation; complete end-to-end
independent physics closure; that posterior calibration validates the physics
implementation; that any external benchmark level is an uncertainty on this
work; that a disclosed limitation is a passed gate; that absence of a detected
discrepancy is evidence of correctness.

The mandatory paper limitation is not optional prose: the paper must state that
no independently executable exact FONLL-A comparator was available, that the
heavy-flavour and matching terms rest on published evidence obtained at other
groups' configurations, and that no end-to-end independent closure is claimed.

## Is V4 warranted?

`V4_SUCCESSOR_PLANNING_NOW_WARRANTED`. **No policy blockers remain.** The seven
remaining items are ordinary plan authoring under decided semantics:

1. declare the `NP2` numerical stability target and empirical protocol;
2. replace the grid gate with the exact coverage and nesting audit;
3. freeze the candidate-side APFEL settings for the massless test, extend the
   bridge contract to the publication's initial scale, derive the work cap;
4. freeze the component coverage matrix required by this policy;
5. serialize the non-gating `alpha` diagnostic, its probes and reporting format;
6. record the runtime identity disclosure;
7. recount the per-category resource model.

A separate independent authorization review remains required after V4.

## Phase completion report

All commands ran in WSL Ubuntu from the repository root. No native physics
validation was performed, so `scripts/pythia_env.sh` was not sourced.

| Command | Result |
| --- | --- |
| `python3 scripts/validate_phase2_fonll_a_contract_amendment.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan.py` | PASS |
| `python3 scripts/validate_phase2b_execution_authorization_review.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan_v2.py` | PASS |
| `python3 scripts/validate_phase2b_execution_authorization_review_v2.py` | PASS |
| `python3 scripts/validate_phase2b_preauthorization_validation_plan_v3.py` | PASS |
| `python3 scripts/validate_phase2b_blocker_resolution.py` | PASS |
| `python3 scripts/validate_phase2b_numerical_policy_decision.py` | PASS |
| `python3 scripts/validate_phase2b_fonll_validation_policy.py` | PASS |
| `python3 scripts/validate_phase2_reduced_nc_dis_roadmap.py` | PASS |
| `python3 scripts/validate_phase1b_closeout.py` | PASS |
| focused FONLL-policy suite | PASS, 91 tests |
| `python3 -m pytest -q analysis/tests/` | PASS, 898 tests |
| `cargo fmt --all -- --check` | PASS |
| `git diff --check` | PASS |

The machine artifact SHA-256 is
`8210b926f1461938638f9ddcbb94c1003e52b4a5ec0bcd944d53e6b6bec8ce91`.

Three corrections were made during this task rather than hidden, all of them
strengthening the guards. An adversarial test showed the validator would have
accepted the `pdfs` node carrying no disclosure duty, so that node now declares
that the grids are a published input which is not re-validated here. A second
test showed a published node could be promoted to an executable oracle, and a
third showed it could be demoted to an analytic check to retire its disclosure
duty; published evidence is now structurally required to be classed `E2`. The
permitted-claim scan was also refined to match affirmative assertions only, so
that naming the missing comparator — which this policy *requires* — is not
itself flagged. No scientific rule was weakened.

## Next step

Draft the Phase 2B preauthorization V4 successor plan under `AP1`, `NP2` and
`FPD3`, freezing the component coverage matrix and the seven plan-authoring
items. Phase 2B remains `NOT_AUTHORIZED` and `NOT_EXECUTED`.
