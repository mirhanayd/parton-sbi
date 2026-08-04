# ADR-011: Independent evidence for separate-contract priority

- Status: Proposed
- Scope: Phase 1B-D1G planning only
- Schema: `partonsbi.phase1bd.d1g.independent-contract-priority.v2`
- Decision: `NO_UNIQUE_PRIORITY_MAINTAIN_PAUSE`
- Implementation authorization: false

## Context and immutable boundary

D1F remains `MAINTAIN_CURRENT_CONTRACT_AND_PAUSE`. The current full-generator
line remains `MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE`, the active policy remains
`PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION`, and no prospective contract
is active. D1G asks only whether independent evidence makes exactly one of four
prospective contracts the priority for a future planning review.

The rejected v1 D1G proposal was never merged and is not immutable scientific
state. Its source-content audit found one contradicted identity, 14 overstated
claim scopes, one misbound claim, and decision-coded support for Candidate C.
This v2 record applies those corrections without changing D1F, authorizing a
task, or superseding the roadmap.

## Source identity and content audit

Thirteen external sources remain in the bounded registry. Publication dates
and downloadable-version dates are now separate fields with explicit date
kinds. The corrected registry has five `VERIFIED` and eight
`VERIFIED_WITH_QUALIFICATION` identities. The v1 identity audit is retained as
provenance: five verified, seven qualified, and one contradicted.

The contradicted record was the D'Agostini citation. V1 attached the URL and
bytes of Höcker and Kartvelishvili (`hep-ph/9509307`) to a different DOI. V2
identifies the actual publisher article:

- Giulio D'Agostini, “A multidimensional unfolding method based on Bayes'
  theorem”;
- *Nuclear Instruments and Methods in Physics Research Section A* 362 (1995)
  487-498;
- publisher date 1995-08-15;
- DOI `10.1016/0168-9002(95)00274-X`; and
- publisher URL
  `https://www.sciencedirect.com/science/article/pii/016890029500274X`.

No official downloadable byte identity was available, so its content hash is
null and the publisher/DOI limitation is explicit. This source is contextual;
it does not establish a normalized PartonSBI detector law, QCD factorization,
an observation measure, or an end-to-end MVP.

The 18-claim `source_content_ledger` retains the independent v1 audit result:

| Content classification | Count |
|---|---:|
| `DIRECTLY_SUPPORTED` | 2 |
| `SUPPORTED_WITH_QUALIFICATION` | 1 |
| `OVERSTATED_IN_V1` | 14 |
| `MISBOUND_IN_V1` | 1 |
| `PRIMARY_EVIDENCE_UNAVAILABLE` | 0 |

Each claim records the inspected location, supported statement, unsupported
extensions, option and criterion scope, maximum status, and whether it may be
load-bearing. Any future content change requires another independent review.

## Corrected scorecards

The explicit 72-cell audited ledger replaces opaque status-code generation.
Every cell retains its v1 audit classification and a correction reason.

| Candidate | Qualified | Primary evidence unavailable | Eligible |
|---|---:|---:|---|
| B: new nonnegative family | 7 | 11 | false |
| C: lower-level DIS model | 7 | 11 | false |
| D: weighted empirical set | 8 | 10 | false |
| E: signed-weight research | 9 | 9 | false |

Candidate B has qualified scientific, QCD, PDF-interpretation, bounded-review,
falsifiability, objective-change, and negative-review-value evidence. It has no
independent observation law, posterior, no-clipping/strict-support proof, or
composite MVP evidence.

Candidate C has qualified scientific, QCD, PDF-interpretation, event-set,
calibration, falsifiability, and negative-review-value components. HERA
formulae do not establish a normalized observation measure, posterior, event
weights, fixed-N rate/shape semantics, no clipping, strict support, or an MVP.
Deep Sets supplies representation only; SBC supplies validation methodology
only. Correct components do not constitute a composite MVP.

Candidate D has qualified positive importance-weight component semantics and
strict-domination context, but no random observed-set law, posterior,
calibration, no-clipping result, or complete MVP. Candidate E has qualified
estimator-weight context, but missing measure and posterior evidence is not an
impossibility proof. Every affirmative `NOT_SUPPORTED` v1 score for E was
corrected to `PRIMARY_EVIDENCE_UNAVAILABLE` where no impossibility source
exists.

## Mandatory gates and composite MVP

For B, C, and D the normalized-measure, posterior, MVP, no-hidden-repair, and
complete-independent-evidence gates are unavailable. For E the normalized,
posterior, MVP, and complete-independent-evidence gates are unavailable; its
no-hidden-repair gate is qualified. All candidates retain qualified scientific
motivation, bounded-review, falsifiability, and objective-change gates, and all
prospective-supersession flags are explicit.

`independent_evidence_available` is positive only if every preference-critical
claim has independent evidence: normalized measure, posterior, motivation,
bounded review, falsifiability, composite MVP, objective change, and
no-hidden-repair semantics. One unrelated source is insufficient.

The composite MVP requires evidence for nine components: physical data law,
finite positive normalization, detector law, event representation, posterior
or training target, calibration, implementation boundary, validation
boundary, and repository-infrastructure compatibility. All four composite MVP
results are `PRIMARY_EVIDENCE_UNAVAILABLE`.

## Candidate C boundary

Candidate C is
`SCIENTIFICALLY_MOTIVATED_COMPONENTS_PRESENT_BUT_PRIORITY_GATES_UNMET`. It is
not a normalized observation model, coherent executable posterior, forward
detector kernel, positive finite rate, end-to-end MVP, or full-generator
equivalent. It does not complete issue #10.

All fourteen obligations remain `NOT_EVALUATED`: exact e-/e+ NC formula; F2,
FL, and xF3 conventions; gamma/Z/interference; electroweak scheme; scale
choices; flavor/heavy-quark treatment; coordinates/Jacobian; finite nonzero
normalization; nonnegative complete differential rate; strict PDF support;
detector-kernel normalization; perfect-detector identity kernel; independent
numerical closure; and explicit omitted physics.

## Decision and consequences

No candidate passes every mandatory gate. Therefore:

```text
eligible_candidates = []
decision = NO_UNIQUE_PRIORITY_MAINTAIN_PAUSE
```

The next step is `MAINTAIN_PAUSE_PENDING_PREFERENCE_CRITICAL_EVIDENCE`. A new
priority review is warranted only after independent evidence addresses a
candidate's normalized measure, posterior, no-hidden-repair, and composite MVP
gaps. No lower-level DIS contract proposal is created by this record.

Validation scope is
`ARTIFACT_INTEGRITY_AND_AUDITED_LEDGER_BINDING`. The validator proves
deterministic construction, source-identity and audited-ledger integrity,
scope and maximum-status compliance, gate/decision recomputation, and
authorization/roadmap boundaries. It does not read external papers, guarantee
future source availability, discharge physics obligations, or validate an
executable simulator.

Issue #49 remains open. Issue #10 and D2 remain blocked and unauthorized;
D3-D5 remain Backlog. No roadmap supersession is active. All twelve
authorization flags remain false. No parser, generator, event, detector,
dataset, numerical-physics, neural, prototype, or D2 work is authorized.
