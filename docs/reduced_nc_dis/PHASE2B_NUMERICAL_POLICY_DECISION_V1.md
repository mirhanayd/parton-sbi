# Phase 2B numerical-contract policy decision V1

## Result

```text
OUTCOME = PD1_ADOPT_AP1_AND_NP2
ALPHA_POLICY = AP1_APFEL_ALPHA_IS_AUTHORITATIVE_SIMULATOR_COUPLING
NORMALIZATION_POLICY = NP2_REQUIRE_EMPIRICAL_NUMERICAL_STABILITY_NOT_CERTIFIED_ACCURACY
RESEARCH_QUESTION_IMPACT = UNCHANGED
PHASE2B_AUTHORIZED = false
PHASE2B_EXECUTION_STATUS = NOT_EXECUTED
```

This is a scientific contract-policy decision. It is not an execution
authorization review, not a source search, and not a successor preauthorization
plan; **no V4 was created**. The authoritative record is
[`contracts/phase2b_numerical_policy_decision_v1.json`](contracts/phase2b_numerical_policy_decision_v1.json).

Predecessors are bound and unmodified: FONLL-A amendment
`10cf19fe…`, V3 `78a02968…`, blocker resolution `d66a1bbc…`. Historical Phase 2A
remains `COMPLETE/INCONCLUSIVE`; ADR-013 remains Proposed.

## Question A — which coupling is authoritative

### The fact that decides it

`ComputeDISOperators.f` (sha256 `4f4b17ba…`) sets `mu2as` from the
factorisation scale and, on the non-FFNS branch that FONLL-A NC takes, evaluates

```fortran
as(1) = a_QCD(mu2as)
```

**LHAPDF's `alphasQ` is never consulted by the DIS computation.** The external
PDF callback `ExternalSetAPFEL` carries densities only and no coupling.

This makes the V3 `G3` gate scientifically defective rather than merely hard.
`G3` would have rigorously certified LHAPDF's `alphasQ` over the continuum — a
function the observation law does not evaluate. Requiring a proof about an
object outside the simulator is not conservatism. That, and not difficulty, is
why `AP1` is adopted.

### The five review questions

**1. Must the runtime `alpha_s` evaluator be numerically identical to the one
that produced the PDF grids?** **No.** The fit's coupling is already embedded in
the grid values. What the evaluation must share is the renormalisation scheme,
the perturbative order and the flavour-threshold convention — a mismatch there
is a genuine theory inconsistency. Numerical identity is a far stronger and
different property: CT18 serialises a HOPPET running solution and interpolates
it, APFEL integrates the same equation with a fixed ten-step recursion, and
their difference is numerical, not theoretical. The accepted massless benchmark
corroborates the field's practice — HOPPET and APFEL++ each ran their *own*
coupling from a common `alpha_s` at a common initial scale.

**2. Is declared-convention consistency the relevant contract?** **Yes**, and it
is satisfied on every serialized item but one:

| Item | CT18NLO declared | APFEL accepted control | Status |
| --- | --- | --- | --- |
| `alpha_s(M_Z)` | `0.118000` at `MZ 91.1870` | `SetAlphaQCDRef(0.118,91.187)` | compatible |
| observable order | `OrderQCD 1` | `SetPerturbativeOrder(1)` | compatible |
| pole masses | `1.3000 / 4.7500 / 172.0000` | `SetPoleMasses(1.3,4.75,172.0)` | compatible |
| flavour scheme | variable, `NumFlavors 5` | `SetVFNS`, `SetMaxFlavourAlpha(5)` | compatible |
| matching / `muR:muF` ratios | not serialized | `SetMassMatchingScales(1,1,1)`, `SetRenFacRatio(1)` | APFEL side declared only |
| **order of the coupling running** | `AlphaS_OrderQCD 1`, but `SetDesc` states a HOPPET **three-loop** running solution | `ipt=1`, i.e. the two-loop beta function | **unresolved** |

The last row is a real tension inside the CT18NLO metadata itself. `AP1` does
not resolve it and does not hide it: it becomes a mandatory item of the required
diagnostic.

**3. Does `AP1` introduce a new hidden theory inconsistency?** **No, and nothing
is hidden.** The frozen software already evaluates the coefficient functions
with APFEL's coupling; no policy choice changes that without modifying the
accepted implementation, so `AP1` describes the existing simulator rather than
altering it. Any residual mismatch between the fitting and evaluation running is
*formally* suppressed relative to the claimed NLO accuracy — a next-order
difference in the beta function shifts `alpha_s` by a relatively higher-order
amount, entering an already order-`alpha_s` term. Formal suppression is a
scaling argument, **not a bound**, so the residual must be measured and
reported rather than assumed small.

**4. Does it change the research question?** **No.** Inference unit, posterior
target, theta domain and prior, observation space, selected-event conditioning
and detector kernel are all untouched.

**5. What diagnostic remains appropriate?** A **required but non-gating**
comparison: the declared-convention checklist above including the unresolved
running-order item, plus a numerical CT18-versus-simulator coupling comparison
over the accepted `Q^2` domain, reported as sampled diagnostic evidence and
never as equivalence. The observed value is published whatever it is. A
difference large enough to change a reported conclusion, or any failed
compatibility item, triggers scientific review — a qualitative trigger, **not a
numerical threshold**, and no tolerance is defined here.

`AP2` was rejected because freezing an image would not convert an author-stated
ULP analysis into a proof, and the certified quantity would still not be
load-bearing. `AP3` was rejected because replacing the coupling provider inside
the pinned APFEL 3.1.1 build changes the simulator object and reopens the
amendment — the same reasoning that already rejected `AS1`.

## Question B — what is claimed about normalization

### Four things that are not the same

- **Mathematical proof of quadrature error** — needs an interval-extensible
  integrand or a certified derivative bound. The accepted integrand is a frozen
  binary64 wrapper returning one number per point. Unobtainable without
  replacing the implementation.
- **Empirical convergence evidence** — observed behaviour of a predeclared
  ladder and an independent second rule. Evidence of stability, **not a bound**;
  the blocker-resolution record exhibits an entire integrand on which both
  accepted rules return exactly zero at every level while the true integral is
  `1.7725e-4`.
- **Reproducibility** — whether frozen software and inputs give the same
  numbers. Asserted only at the level of frozen software identity, because the
  platform logarithm is ifunc-selected.
- **Physical or theory uncertainty** — a different object entirely, not claimed.

**1. Does the proof-of-principle paper require a certified integration
theorem?** **No.** What makes the methodological claim true or false is whether
the posterior is calibrated, established by empirical coverage evidence. A
certified remainder would improve the description of the simulator's internals;
it is not the load-bearing support for the claim.

**2. Is empirical independent-quadrature stability sufficient if accurately
disclosed?** **Yes, conditionally** — the claim must be stated as stability and
reproducibility, the two families must keep independent node generation, weight
generation and accumulation, the ladder and decision rule must be predeclared,
finite positive normalization stays mandatory, instability yields
`FAIL`/`INCONCLUSIVE`, and the limitation is disclosed. Two rules with different
node placements *reduce* but do not eliminate the risk of missing structure
between nodes, and `NP2` does not claim otherwise.

**3. What becomes forbidden.** Certified accuracy of any stated value; treating
a successive difference as a remainder bound; treating cross-family agreement as
proof of convergence; transferring any external benchmark level including the
published `0.001` and `1e-5` observations; attaching theoretical uncertainty to
the normalization estimate; any tolerance chosen after seeing an estimate.

**4. Minimum predeclared criteria a future plan must contain.** Two families
with disjoint implementation provenance; a fixed refinement ladder frozen in an
immutable artifact before execution; the comparison statistic and precision
target declared in that artifact **before** any estimate exists, with the plan
invalid if written afterwards; absolute comparison whenever an interval contains
zero and relative only away from zero; agreement at *every* theta anchor with no
averaging and no anchor dropped; finite strictly positive `Z` at every anchor;
non-monotone or growing differences `INCONCLUSIVE`, never `PASS`; cross-family
disagreement `FAIL`, with agreement necessary and explicitly not sufficient; a
bounded finite work count with no retry-until-pass, no point deletion and no
post-hoc tuning; and the stability-not-a-bound disclosure carried in both the
artifact and the paper.

**No numerical tolerance is defined here.** This decision fixes the claim type;
selecting the target is the successor plan's task, and this record only fixes
that it must be predeclared rather than discovered.

`NP1` was rejected because it makes authorization conditional on an unobtainable
precondition. `NP3` was rejected because the accepted observation law is
explicitly normalized, so removing validation of the denominator would leave a
load-bearing quantity unvalidated; the compatibility proof it would require was
not attempted and is not believed to exist.

## Contract impact

Both policies leave the research question untouched. Both replace a gate, and
that replacement is stated rather than slipped in.

| Scope | `AP1` | `NP2` |
| --- | --- | --- |
| Observation law / probability law | `DISAMBIGUATES_EXISTING_CONTRACT` | `DISAMBIGUATES_EXISTING_CONTRACT` |
| Preauthorization gate semantics | `REPLACES_EXISTING_CONTRACT` (`G3`) | `REPLACES_EXISTING_CONTRACT` (`G7`–`G11`) |
| Paper claim boundary | `NARROWS_CLAIM_BOUNDARY` | `NARROWS_CLAIM_BOUNDARY` |
| Research question | `UNCHANGED` | `UNCHANGED` |

`G3`'s continuous provider-equivalence certification with propagated discrepancy
is replaced by declared-convention compatibility plus a mandatory non-gating
diagnostic. The certified path-local remainder producing `Z_A ± E_A` and
`Z_B ± E_B` is replaced by a predeclared empirical stability protocol;
cross-path comparison survives as *agreement*, not as an interval-overlap
certificate.

## Paper impact

**MAY say**

- the simulator's coupling is APFEL 3.1.1's NLO variable-flavour running,
  configured to the CT18NLO declared convention;
- CT18NLO coupling metadata is a provenance and compatibility constraint on the
  PDF boundary, not the runtime evaluator;
- the declared-convention items were checked and are reported, including any
  that remain unresolved;
- an observed CT18-versus-simulator coupling comparison, reported as a sampled
  diagnostic;
- *"normalization was checked for reproducible numerical stability under
  independent fixed-refinement quadratures"*;
- normalization was finite and strictly positive at every evaluated
  configuration;
- the raw implemented rate was nonnegative at every evaluated point.

**MUST NOT say**

- CT18 and APFEL `alpha_s` are equivalent, identical or certified consistent;
- the coupling is certified over the continuum, or the sampled diagnostic bounds
  the provider difference;
- *"normalization is rigorously certified to X accuracy"*;
- a successive difference bounds the quadrature remainder;
- cross-family agreement proves convergence;
- any external benchmark level applies to normalization;
- the rate is positive on the continuum or at all orders;
- any accuracy figure selected after results were seen.

A must-not item may be revisited only if future evidence changes the contract
through a new reviewed decision record.

## Blocker status after the decision

| Blocker | Status |
| --- | --- |
| `BLOCKER_ALPHA_IMPLEMENTED_LOG_ENCLOSURE` | **dissolved by policy** |
| `BLOCKER_ALPHA_CONSISTENCY_CRITERION` | **dissolved by policy** |
| `BLOCKER_PROJECT_PRECISION_TARGET` | converted to a plan-authoring item |
| `BLOCKER_GRID_GATE_SEMANTICS` | converted to a plan-authoring item |
| `BLOCKER_MASSLESS_CANDIDATE_SIDE` | converted to a plan-authoring item |
| `BLOCKER_NUMERICAL_RUNTIME_IDENTITY` | downgraded to a disclosure requirement |
| `BLOCKER_FONLL_REFERENCE_EXECUTION_SPEC` | **remains a scientific blocker** |

## Is a successor plan warranted?

**Drafting is warranted; completeness is not yet achievable.** The two policy
questions that gated the alpha and numerical-acceptance semantics are decided,
so a successor preauthorization plan can be written. It could not be `COMPLETE`,
because the blocker-resolution rule forbids a complete result containing a
load-bearing unvalidated node, and no independent executable FONLL-A comparator
is bound.

That exposes a **third policy question this task was not scoped to decide**:

> Is an independent executable FONLL-A component reference a required Phase 2B
> gate, or is its absence an accepted and disclosed limitation of a
> proof-of-principle result?

Deciding it inside this record would exceed the requested scope. Until it is
recorded, a successor plan can be drafted but cannot reach a complete state.

## Phase completion report

All commands ran in WSL Ubuntu from the repository root. No native physics
validation was performed, so `scripts/pythia_env.sh` was not sourced. The
dependency tree was installed outside the repository and is not a deliverable.

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
| `python3 scripts/validate_phase2b_numerical_policy_decision.py` | PASS |
| `python3 scripts/validate_phase1b_closeout.py` | PASS |
| focused policy-decision suite | PASS, 76 tests |
| `python3 -m pytest -q analysis/tests/` | PASS, 807 tests |
| `cargo fmt --all -- --check` | PASS |
| `git diff --check` | PASS |

The machine artifact SHA-256 is
`a855dfeb49a4f6f8e26804c5fac8708691fa9c345be57acfc5efa55e1864830c`.

One correction was made during this task rather than hidden. An adversarial test
showed the validator would have accepted a record that dissolved the
independent-reference blocker, which neither decided policy addresses. The
validator now restricts `DISSOLVED_BY_POLICY` to the two alpha-gate blockers
that lie inside this decision's scope and requires the independent-reference
blocker to stay recorded as remaining. No scientific rule was weakened.

## Next step

Decide the third policy question about the independent FONLL-A reference. A
successor preauthorization plan may be drafted in parallel under `PD1`, but it
cannot reach a complete state until that question is recorded. Phase 2B remains
`NOT_AUTHORIZED` and `NOT_EXECUTED`.
