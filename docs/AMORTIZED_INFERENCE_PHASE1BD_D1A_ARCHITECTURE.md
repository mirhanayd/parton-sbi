# Phase 1B-D1A evolved-PDF transport architecture

## Scope

This report records the architecture decision requested by issue #33. It uses
the committed D1 and D1R results and source inspection only. No APFEL scan,
LHAPDF artifact, refinement, anchor study, PYTHIA integration, or event sample
was produced.

## Evidence reviewed

- D0R boundary family: `PASS`.
- Original Stage 1: `FAIL`.
- Revised Stage 1: `FAIL`.
- Exact lhagrid1 knot serialization: passed.
- Independent reproduction of LHAPDF interpolation: passed.
- Global direct-APFEL versus finite-grid off-knot closure: failed.
- Computational/exported-support leakage convergence: failed.
- Transported sign topology: failed at three anchors.
- NLO photon-only F2/FL closure: passed at all nine anchors, but is not a
  neutral-current gamma/Z or PYTHIA closure result.

The D1R common 641-x by 149-Q representation retained 3,492,044 direct
off-knot tolerance failures and exceeded its fixed per-anchor refinement
budget. These committed results provide no credible convergence basis for
another unconstrained global LHAPDF refinement.

## Scientific requirement

PartonSBI requires a common, versioned mathematical PDF definition and
validated numerical transport for every generator PDF consumer. Closure must
be binding at PDF level over a conservative, predeclared all-consumer
process-reachable domain and at physical-observable level for full
neutral-current gamma/Z structure functions and differential cross sections.
A later D2 would still need controlled query coverage and event-distribution
closure.

Global equality over the entire exported support and one identical serialized
evaluator for APFEL and PYTHIA were stronger design choices. They are not
discarded merely because they failed, but the research objective does not make
them mandatory when an all-consumer domain and layered physical closure can be
established independently.

## Reachability result

The hard DIS domain can be specified before generation from beams, process,
x/Q2/y cuts, scale convention, and strict support. The current implementation
does not establish a conservative envelope for every PYTHIA shower and
auxiliary PDF query. Generated events must not be used post hoc to define that
envelope.

Result: `INCONCLUSIVE_PENDING_ALL_CONSUMER_ENVELOPE`.

## Architecture result

Overall decision: `INCONCLUSIVE`.

Global standard-LHAPDF refinement is rejected as the next path. The evidence
does not yet distinguish safely between:

- a direct APFEL-backed PYTHIA PDF adapter; and
- a repository-owned deterministic precomputed interpolator.

A hybrid reference/transport contract is scientifically viable in principle,
but selecting it now would leave evaluator safety, throughput, deterministic
caching, and generator reachability unresolved.

## Authorized prototype

One D1A prototype/validation PR may compare the two candidate evaluators under
these fixed limits:

- 30 minutes maximum numerical validation runtime;
- 2 GiB maximum generated disk use;
- center plus no more than two predeclared stress anchors;
- no nine-anchor refinement;
- no production event generation;
- no D2 implementation.

It must measure deterministic identity, direct-reference accuracy,
all-consumer query coverage, threshold behavior, calls per second, process
lifetime, cache behavior, and thread/process safety. It must also specify the
full neutral-current gamma/Z observable contract that would precede D2.

## Decision and authorization

```text
ARCHITECTURE_DECISION = INCONCLUSIVE
D1A_PROTOTYPE_AUTHORIZED = true
D2_AUTHORIZED = false
```

This authorization covers a bounded comparison only. It does not authorize a
production transport, PYTHIA coupling, generated events, datasets, sampling,
or neural inference.

## Lightweight validation

The documentation change is validated with Rust formatting, whitespace checks,
and JSON parsing only, as required by the D1A task. No scientific numerical
study is repeated.
