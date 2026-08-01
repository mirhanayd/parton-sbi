# ADR-008: Signed-generator coupling terminal planning decision

- Status: Proposed
- Date: 2026-08-01
- Phase: 1B-D1D-B
- Decision artifact: `docs/phase1bd_d1d_terminal_decision.json`

## Context

The merged D1D-A evidence record is a negative result. Its precedence is
immutable here:

- `D1C_FINAL_DECISION = FAIL`;
- `MINIMAL_PUBLIC_READER_PATCH = INSUFFICIENT`;
- `PROVENANCE_SLICE_V1_DECISION = FAIL`;
- `PROVENANCE_SLICE_V1_STATUS = REJECTED_DIAGNOSTIC`;
- `D1D_A_FINAL_DECISION = FAIL`;
- `D1D_A_FAILED_GATE = provenance_evidence_integrity`;
- `ARCHITECTURE_COMPARISON_READY = false`; and
- `D2_AUTHORIZED = false`.

This ADR is a planning decision, not an implementation authorization. The
scientific contract remains the signed binary64 `x*f` interface for
`ct18nlo_two_parameter_boundary_v2`, the declared theta box, strict support
without extrapolation, shape-only fixed-N inference over event sets, and
consistent hard-process, ISR/backward-evolution, and beam-remnant treatment.

## Decision

The proposed decision is **INCONCLUSIVE**.

The decision is derived rather than fixed by assertion. D1D-A did not pass its
mandatory evidence gate and architecture-comparison readiness remains false,
so no prototype can be authorized. At the same time, Sherpa and Herwig expose
potentially relevant full-generator interfaces. The reviewed primary sources
do not prove signed PDF scalar preservation or mathematically valid signed
internal rates through every hard-process, ISR, and remnant consumer. That
missing evidence prevents authorization, but the existence of potentially
coherent interfaces also prevents the stronger conclusion that every current
route is disproven and disproportionately costly.

Accordingly, current generator-coupling work stops, all authorization flags
remain false, and the record may be reconsidered only if a stated reopen
condition is independently satisfied. This is not a universal impossibility
theorem.

## Architecture A: repository-owned PYTHIA fork or patch

Assessment: `NOT_SUPPORTED_FOR_A_BOUNDED_PROTOTYPE`.

Changing the three public positivity readers is already established as
insufficient. Bypassing those readers would not validate downstream
sign-sensitive consumers. A coherent redesign would have to cover hard-process
rates, backward-evolution kernels, remnants, flavor/categorical selections,
denominators, ratios, maxima, envelopes, vetoes, and cumulative selections.
The rejected provenance slice cannot bound that redesign. A versioned fork
would additionally carry continuing upstream-integration and scientific-
validation costs. No fork, patch, or bypass is authorized.

## Architecture B: signed-weight generator architecture

Assessment: `NOT_SUPPORTED_FOR_THE_FIXED_CONTRACT`.

Signed matrix-element contributions, signed complete-event samples, and
weighted empirical event sets are distinct from ordinary positive-probability
event generation. Negative event weights can represent cancellations between
already constructed complete histories. An external final weight cannot
retroactively repair negative probabilities, denominators, maxima,
categorical selections, Sudakov factors, or rejection sampling used before a
complete history exists. A signed-kernel or signed-Sudakov architecture would
need its own reviewed mathematical measure and sampling construction; none is
available for the fixed contract.

## Architecture C: bounded alternative-interface desk review

Three candidates, and no more, were reviewed.

### Sherpa external-PDF and full DIS stack

Sherpa documents an external `PDF_Base` interface, PDF scalar accessors,
initial-state PDF selection, alpha_s routing, and a neutral-current lepton-
proton DIS configuration. Its primary literature also discusses negative final
event weights in NLO matching. These sources do not demonstrate that a signed
PDF scalar remains signed and scientifically valid through every hard, shower,
and remnant consumer. The candidate is therefore potentially coherent but
unresolved, not authorized.

Primary sources:

- [Sherpa 3 software paper](https://arxiv.org/abs/2410.22148)
- [official external-PDF interface](https://sherpa-team.gitlab.io/sherpa/v3.0.0alpha1/manual/customization/external-pdf.html)
- [official ISR and PDF configuration](https://sherpa-team.gitlab.io/sherpa/v3.0.1/manual/parameters/isr.html)
- [official DIS example](https://sherpa-team.gitlab.io/sherpa/master/examples.html)
- [official source repository](https://gitlab.com/sherpa-team/sherpa/-/tree/master)

### Herwig PDF and shower stack

The Herwig primary manuals and software papers cover lepton-hadron hard
scattering, backward-evolution showers, beam remnants, MC@NLO event weights,
public source availability, and current maintenance. They do not establish
complete provider coverage or signed-PDF validity across the fixed hard/ISR/
remnant contract. This candidate is also potentially coherent but unresolved,
not authorized.

Primary sources:

- [Herwig++ physics and manual paper](https://arxiv.org/abs/0803.0883)
- [Herwig 7.0 software paper](https://arxiv.org/abs/1512.01178)
- [Herwig 7.3 software paper](https://arxiv.org/abs/2312.05175)

### Les Houches signed hard-event transport

The Les Houches Event File can transport weighted parton-level events, and
MC@NLO demonstrates negative weights for complete hard-event samples. This is
a boundary format, not a replacement for PDF-dependent ISR, remnant, provider,
or alpha_s semantics in the receiving generator. It therefore cannot satisfy
the complete coupling contract by itself.

Primary sources:

- [Les Houches Event File standard](https://arxiv.org/abs/hep-ph/0609017)
- [MC@NLO construction](https://arxiv.org/abs/hep-ph/0204244)

## Architecture D: stop further generator-coupling work

Assessment: `SUPPORTED_WITH_QUALIFICATION_FOR_CURRENT_CONTRACT`.

Stopping is justified as the current operational policy for this particular
projected D0R family, signed binary64 contract, theta box, shape-only fixed-N
MVP, and hard/ISR/remnant consistency requirement. It avoids presenting an
unbounded maintenance project as a scientific prototype. It does not prove
that signed generator coupling is impossible for all generators, PDF families,
or inference contracts.

## Twenty-criterion assessment

Legend: S = `SUPPORTED`; Q = `SUPPORTED_WITH_QUALIFICATION`; N =
`NOT_SUPPORTED`; U = `PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE`; A =
`NOT_APPLICABLE`.

| # | Criterion | A: fork | B: signed weight | C: alternatives | D: stop |
|---:|---|:---:|:---:|:---:|:---:|
| 1 | Signed scalar preservation | N | N | U | A |
| 2 | Nonnegative probability/rate validity | N | N | N | A |
| 3 | Hard-process coverage | N | U | Q | A |
| 4 | ISR/Sudakov coverage | N | N | Q | A |
| 5 | Beam-remnant coverage | N | N | Q | A |
| 6 | Flavor and categorical selection | N | N | U | A |
| 7 | Denominator and ratio validity | N | N | U | A |
| 8 | Maximum/envelope/rejection semantics | N | N | U | A |
| 9 | Event-weight semantics | N | Q | Q | A |
| 10 | Strict support and no extrapolation | Q | U | U | A |
| 11 | alpha_s consistency | U | U | Q | A |
| 12 | Full neutral-current gamma/Z compatibility | N | U | U | A |
| 13 | Deterministic identity and provenance | Q | N | Q | S |
| 14 | Thread/process safety | U | U | U | A |
| 15 | Build and deployment reproducibility | Q | N | Q | A |
| 16 | License and redistribution | U | A | Q | A |
| 17 | Upstream maintenance burden | N | N | Q | S |
| 18 | Bounded prototype falsifiability | N | N | N | A |
| 19 | Amortized set-inference compatibility | Q | Q | Q | Q |
| 20 | Authorization-hierarchy compatibility | N | N | N | S |

Missing evidence is never converted into support. Candidate-specific evidence
and rationales are serialized in the decision artifact.

## Unresolved evidence

- No complete independently validated PDF-consumer/dataflow graph exists.
- No reviewed signed-kernel or signed-Sudakov construction covers all internal
  sampling decisions.
- The candidate alternatives do not prove signed scalar preservation across
  hard scattering, backward evolution, and remnants.
- Exact gamma/Z, support, provider, alpha_s, concurrency, and reproducibility
  behavior remains unvalidated for the fixed contract.
- Maintenance and redistribution costs are not sufficiently bounded across
  every potentially coherent route.

## Reopen conditions

Generator coupling may be reconsidered only after at least one independently
reviewed evidence change, such as:

1. a mathematical signed-kernel and signed-Sudakov formulation covering all
   internal sampling decisions;
2. a primary-source generator interface proving signed scalar, rate, ISR,
   remnant, and event-weight semantics;
3. an independently validated complete consumer and dataflow graph; or
4. a separately reviewed and approved change to the PDF-family or inference
   contract.

A reopen condition is not an authorization. Any reconsideration requires its
own scoped decision and approval.

## Consequences

All implementation and prototype authorization flags remain false. Issue #42
remains open for review of this proposed decision. Issue #10 remains blocked,
and D2 remains unauthorized. No later phase begins in this ADR.

The next step is `SCIENTIFIC_REVIEW_OF_TERMINAL_D1D_B_DECISION`.
