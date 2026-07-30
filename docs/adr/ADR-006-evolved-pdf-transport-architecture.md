# ADR-006: Evolved-PDF transport architecture

- Status: Proposed for scientific review
- Decision date: 2026-07-30
- Scope: Phase 1B-D1A only
- Decision: `INCONCLUSIVE`

## Context

The approved D0R boundary family passed its input-scale validation. Both
subsequent attempts to transport its APFEL++ evolution through finite LHAPDF6
grids failed their predeclared Stage 1 contracts.

The original D1 study failed global off-knot transport and evolved-moment
gates. D1R then established that exact-knot serialization is correct and that
an independent implementation reproduces LHAPDF's interpolation, but the
common 641-by-149 refined grid still produced 3,492,044 direct-APFEL versus
LHAPDF failures, a non-monotonic maximum absolute discrepancy, an over-budget
anchor, unresolved finite-support leakage convergence, and three sign-topology
mismatches. Its NLO photon-only F2/FL checks passed. These results remain
`FAIL`; they do not authorize D2.

ADR-002 selected one generated LHAPDF artifact as the APFEL-validation and
PYTHIA representation. Its revisit condition is now met: the standard finite
artifact has not reproduced the approved family under the global pointwise
contract within the fixed resource and numerical gates.

This ADR uses only committed D1/D1R evidence and source inspection. It does not
repeat an anchor study, create an artifact, or implement a transport.

## Requirements decomposition

The following requirements must not be conflated:

1. **Global evaluator identity:** pointwise agreement with direct APFEL over
   every exported x/Q point.
2. **Reachable-domain evaluator closure:** pointwise agreement over a
   predeclared conservative domain reachable by every PDF consumer in the
   configured PYTHIA process.
3. **Physical closure:** agreement of binding structure functions,
   differential cross sections, and ultimately generated-event distributions.
4. **One serialized representation:** APFEL validation and PYTHIA consume the
   same bytes and evaluator.
5. **One mathematical definition:** all numerical evaluators represent the
   same versioned D0R family, with explicit transport error and provenance.

PartonSBI scientifically requires requirements 2, 3, and 5, together with
strict support, no extrapolation, deterministic identity, and complete
diagnostics. Requirements 1 and 4 are conservative implementation choices,
not consequences of the inference objective. Relaxing them is acceptable only
after a predeclared all-consumer domain and layered physical-closure contract
are validated; it is not justified merely by the prior implementation's
failure.

## Generator-reachable domain

The hard-process configured envelope can be derived before observing events
from the declared beam energies, neutral-current DIS process, x/Q2/y cuts,
factorization-scale convention, and strict PDF support. The simultaneous cuts
must be intersected through the exact DIS kinematic relation rather than
treated as an enclosing rectangle.

That envelope is distinct from:

- the mathematically supported PDF domain;
- a high-probability region inferred from generated events; and
- a detector-selected region, which is outside the present repository scope.

The current source establishes the hard-process inputs, but it does not prove
a conservative x/Q envelope for every PYTHIA initial-state shower,
final-state/shower-related, and auxiliary PDF query. Defining acceptance from
observed generated events would be circular. Therefore the exact
all-consumer process-reachable domain is **INCONCLUSIVE** before an
instrumented, non-production prototype. Global pointwise closure is not an
intrinsic requirement if such a conservative envelope can be proven, but it
cannot yet be replaced by the hard-process envelope alone.

## Architecture comparison

| Option | Scientific relation and closure | Reproducibility, safety, and cost | Decision |
|---|---|---|---|
| A. Continue global standard-LHAPDF refinement | Preserves ADR-002 and the strongest global pointwise claim. D1R's 641-by-149 result was non-monotonic, retained millions of failures, exceeded its per-anchor budget, and did not settle leakage or topology. | Deterministic and PYTHIA-native, but further refinement increases build time and artifact storage without committed evidence of convergence. Threshold behavior remains LHAPDF-interpolator dependent. | Rejected as the next path. |
| B. Reachable-domain LHAPDF artifact | Preserves standard LHAPDF and could support the configured process if every consumer is enclosed. Global discrepancies remain mandatory diagnostics. | Low integration cost and familiar caching, but the all-consumer envelope is not established. Reducing support or selecting events could alter the prior/process and is forbidden without a separate decision. | Inconclusive; candidate only after reachability proof. |
| C. Direct APFEL-backed PYTHIA adapter | Removes finite-LHAPDF interpolation and most directly shares the approved mathematical evolution. Threshold behavior is APFEL's. | No committed evidence yet establishes APFEL distribution lifetime, reentrancy, thread/process safety, deterministic cache construction, or PDF-call throughput under PYTHIA. Storage is low; initialization and per-call CPU may be high. | Authorized only for a bounded feasibility prototype. |
| D. Repository-owned deterministic interpolator | A content-addressed representation could make APFEL validation and PYTHIA use the same custom evaluator while choosing an interpolation suited to the evolved family. | Potentially deterministic and fast, but creates interpolation, threshold, maintenance, adapter, and validation responsibilities. Construction/storage depend on the selected grid and are not yet bounded by evidence. | Authorized only for comparison in the bounded prototype. |
| E. Observable-only acceptance with the current LHAPDF artifact | The photon F2/FL pass shows some physical combinations are insensitive to observed pointwise errors. It does not establish gamma/Z, differential-cross-section, shower-query, or event-distribution closure. | Cheapest path, but inherited sign/leakage and PDF discrepancies would be hidden behind an incomplete observable. Claims would be limited to the tested photon observable. | Rejected as the sole acceptance contract. |
| F. Hybrid reference and transport | Direct APFEL remains the scientific reference while PYTHIA uses a separately validated transport. This preserves one mathematical definition but abandons byte/evaluator identity from ADR-002. | Can isolate performance and generator constraints, but requires independent identities, error budgets, support auditing, and process-level closure. Failure modes include reference/transport drift. | Scientifically viable umbrella, but transport mechanism and reachable domain are unresolved. Not selected for implementation. |

Changing evolution engine, baseline family, exported support, or scientific
prior is outside D1A and is not justified by the present evidence.

## PDF-level and observable-level acceptance

A revised architecture must use a layered contract:

1. metadata, support, finiteness, determinism, and no-extrapolation gates;
2. binding PDF-level closure on a predeclared conservative all-consumer
   process-reachable domain;
3. binding full neutral-current gamma/Z structure-function and differential
   cross-section closure at predeclared points;
4. in a later, separately authorized D2, instrumented query coverage and
   generated-event distribution closure;
5. global-support pointwise discrepancies retained as mandatory diagnostics,
   even when outside a proven reachable domain.

Universal global pointwise closure is not selected as an unconditional
scientific gate. Observable-only closure is also insufficient. The existing
NLO photon F2/FL result satisfies neither the full electroweak observable gate
nor generator compatibility.

## Decision

The transport architecture is **INCONCLUSIVE**. Standard global LHAPDF
refinement is rejected as the next experiment, but the committed record cannot
yet choose between a direct APFEL-backed evaluator and a repository-owned
deterministic interpolator, nor can it certify the complete PYTHIA-reachable
domain.

One narrowly scoped D1A prototype/validation PR is authorized to compare
Options C and D and to instrument all prospective PYTHIA PDF-query classes
without production event generation. The current standard LHAPDF transport
may be retained only as a diagnostic baseline. Selection must use predeclared
accuracy, safety, performance, and reachability criteria rather than post-hoc
success.

## Prototype budget and acceptance boundary

- At most one implementation PR.
- At most 30 minutes of numerical validation runtime.
- At most 2 GiB of generated disk use; generated artifacts remain untracked.
- Center plus at most two predeclared stress anchors.
- No nine-anchor global refinement.
- No production event generation or corpus.
- Measure deterministic construction, evaluator agreement, query-domain
  coverage, calls per second, process lifetime, cache identity, and
  thread/process safety.
- A prototype result may recommend a transport contract; it cannot authorize
  D2.

## Consequences

- ADR-002's same-artifact choice remains historical but is under explicit
  reconsideration; it is not silently replaced here.
- The approved D0R family and both negative Stage 1 results remain unchanged.
- D2, PYTHIA production coupling, event generation, sampling, datasets, and
  neural inference remain unauthorized.
- A future accepted transport ADR must define the conservative all-consumer
  reachable domain and the full gamma/Z observable gate before D2 can be
  considered.

## Revisit conditions

Revisit this decision after the bounded prototype reports deterministic
evaluator accuracy, full PDF-query reachability instrumentation, APFEL
thread/process behavior, throughput, cache behavior, and a predeclared full
neutral-current observable contract. If neither candidate can meet the fixed
budget without changing the approved family or process, record another
negative result rather than expanding scope.
