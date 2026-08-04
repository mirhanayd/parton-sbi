# ADR-011: Independent evidence for separate-contract priority

- Status: Proposed
- Scope: Phase 1B-D1G planning only
- Schema: `partonsbi.phase1bd.d1g.independent-contract-priority.v1`
- Decision: `PRIORITIZE_LOWER_LEVEL_DIS_CONTRACT_REVIEW`
- Implementation authorization: false

## Context and immutable boundary

D1F remains `MAINTAIN_CURRENT_CONTRACT_AND_PAUSE`. The current full-generator
line remains `MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE`, its preferred separate
review remains `NONE` as the pre-D1G state, and the lower-level candidate
remains a prospective separate contract rather than continuation or repair.
The active policy remains `PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION`.

D1G asks a narrower question: whether independent primary evidence makes
exactly one of four prospective contracts the priority for a later planning
review. It does not change the active contract, reopen the generator line,
discharge a proof obligation, select a simulator, or authorize implementation.

## Evidence method

The review uses thirteen load-bearing primary sources, within the limits of
five sources per candidate and eighteen overall:

| Candidate | Sources | Primary evidence scope |
|---|---:|---|
| New nonnegative family | 3 | perturbative MSbar positivity, global-fit positivity and sum-rule constraints, closure methodology |
| Lower-level DIS | 4 | HERA e-/e+ neutral-current structure, detector response probabilities, simulation-based calibration, permutation-invariant set representation |
| Weighted empirical sets | 3 | positive importance-weighted empirical measures, ESS diagnostics, weighted-risk domination conditions |
| Signed-weight research | 3 | MC@NLO negative estimator weights, Sherpa cancellation/cost evidence, proper scoring rules for probability distributions |

Twelve versioned arXiv PDFs were retrieved under
`/tmp/partonsbi_d1g_sources` on 2026-08-04 and identified by SHA-256. The
proper-scoring-rule article is pinned by its peer-reviewed DOI. No external
bytes are committed. Every load-bearing claim is restricted to a source,
claim, candidate, criterion, and maximum supported status. ADR-010 and this
ADR are not independent preference evidence.

## Candidate B: new nonnegative family

Primary research supports qualified statements about perturbative-domain
MSbar positivity and positivity constraints used in global PDF fits. It also
shows why physical-observable positivity, scheme-dependent PDF positivity,
and low-scale behavior must not be conflated.

The evidence does not define a new PartonSBI theta, prior, family identity,
complete observation measure, posterior, detector law, or end-to-end MVP.
Therefore the candidate is not eligible. Any future such family would be a new
scientific contract, not a correction or repair of D0R.

## Candidate C: lower-level neutral-current DIS hard event

Independent H1/ZEUS evidence establishes a scientifically relevant inclusive
e-/e+ neutral-current DIS scope with QCD PDF analysis and gamma-Z/xF3
structure. Independent method papers establish qualified component semantics
for conditional detector response, repeated-sampling Bayesian calibration,
and permutation-invariant set processing.

Together these sources make the following planning question coherent and
bounded:

```text
z ~ p_theta(z)
y ~ K(y | z)
D = {y_i}_{i=1}^N

p_theta(z) proportional to
  1_A(z) d_sigma_theta/dz
```

This is only a component-level contract argument. It does not prove finite
normalization, pointwise nonnegativity, conventions, support closure, detector
normalization, or an executable data law. The lower-level observation omits
ISR, showering, hadronization, underlying event, and beam remnants and is not
equivalent to a full generator event.

All fourteen D1F Option C obligations remain `NOT_EVALUATED`:

1. exact e- and e+ neutral-current differential formula;
2. F2, FL, and xF3 conventions and signs;
3. gamma, Z, and interference terms;
4. electroweak parameter scheme;
5. factorization and renormalization scales;
6. flavor and heavy-quark treatment;
7. phase-space coordinates and Jacobian;
8. finite nonzero normalization for every accepted theta;
9. complete-rate nonnegativity;
10. strict PDF-support intersection;
11. detector/acceptance-kernel normalization;
12. perfect-detector identity-kernel special case;
13. independent numerical closure; and
14. explicit omitted-physics declaration.

Passing the D1G priority gates means only that a later contract review is
scientifically justified and falsifiable. It is not a PASS for these
obligations and not implementation authorization.

## Candidate D: positive weighted empirical sets

Primary evidence supports positive importance-weighted empirical measures
when proposal, target, domination, likelihood-ratio weights, normalization,
and ESS semantics are explicit. It does not establish posterior conditioning
on a random weighted observed event set, repeated-sampling calibration for
that object, or a PartonSBI end-to-end objective. Weighted events are not
ordinary iid unweighted events, and signed weights are excluded from this
candidate. Posterior and MVP priority gates therefore remain unavailable.

## Candidate E: signed-weight research

MC@NLO and Sherpa sources establish negative complete-event weights as
estimator contributions with cancellation and efficiency costs. They do not
make each signed event a probability outcome. Proper scoring rules elicit
probability distributions; no reviewed positive normalized observation law,
coherent posterior, proper loss, or coverage construction is supplied for the
signed sample. The normalized-measure, posterior, calibration, and MVP cells
are `NOT_SUPPORTED`. Negative NLO weights alone cannot justify signed
posterior conditioning.

## Mandatory-gate result

| Candidate | Eligible | Blocking gates |
|---|---|---|
| New nonnegative family | false | normalized measure, posterior, event-law/MVP evidence |
| Lower-level DIS | true | none at planning-priority level; fourteen contract obligations remain unevaluated |
| Weighted empirical sets | false | posterior and end-to-end MVP evidence |
| Signed-weight research | false | normalized measure, posterior, calibration, and end-to-end MVP |

Exactly one candidate passes all ten mandatory priority gates. No manual
score total or preference label breaks a tie. The derived planning decision is
therefore:

```text
PRIORITIZE_LOWER_LEVEL_DIS_CONTRACT_REVIEW
```

## Consequences

The next action is creation of a separate lower-level DIS contract-review
proposal. That proposal must independently review all fourteen obligations
before any later implementation decision. A priority result is not an
authorization.

Issue #10 remains open, blocked, and unauthorized. D2 remains blocked; D3-D5
remain Backlog. No roadmap supersession is active, and a lower-level model
cannot complete issue #10.

All twelve authorization flags remain false, including lower-level simulator,
event generation, dataset, neural training, and D2 authorization. No parser,
generator, event, dataset, numerical-physics, detector-simulation, neural, or
prototype work is part of this decision.
