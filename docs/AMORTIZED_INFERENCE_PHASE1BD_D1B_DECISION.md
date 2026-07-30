# Phase 1B-D1B persistent APFEL transport decision

## Result

```text
D1B_PLANNING_DECISION = AUTHORIZE_SEPARATE_BOUNDED_PROTOTYPE
SELECTED_PROSPECTIVE_ARCHITECTURE = persistent_in_process_apfel_serialized_v1
PROTOTYPE_AUTHORIZED = false
D2_AUTHORIZED = false
```

This is a design result for issue #37, not an implementation authorization.
No adapter, PDF subclass, numerical study, PYTHIA execution, or event was
created. The original D1 and D1R failures and the D1A `INCONCLUSIVE` result are
unchanged. Only the tested fixed 6-by-6 bilinear transport is rejected.

## Evidence and method

The audit inspected the committed D1/D1R/D1A record and the installed primary
sources for APFEL++ 4.8.0 and PYTHIA 8.312. Exact paths and symbols are recorded
in [ADR-007](adr/ADR-007-persistent-apfel-transport.md). No numerical evidence
was regenerated.

APFEL's `BuildDglap` returns an owned `Dglap<Distribution>` whose const
`Evaluate(Q)` can be called repeatedly. Persistence removes repeated object and
boundary construction, although each new Q still evolves from the retained
reference. A stable context must own `AlphaQCD` longer than the Dglap callback
that references it. APFEL/LHAPDF global verbosity and the absence of a formal
reentrancy guarantee prevent a thread-safety claim. The selected prospective
model therefore serializes all access to one theta-specific context and uses
one generator/context per process.

## Architecture decision

| Architecture | Outcome | Reason |
|---|---|---|
| Persistent in-process APFEL, serialized access | Recommended for a separately authorized bounded prototype | Direct mathematical path, compatible with synchronous PYTHIA calls, conservative lock-based safety model, independently testable lifetime/cache behavior |
| Persistent process worker with deterministic IPC | Fallback | Strong isolation, but per-scalar synchronous IPC is a material unmeasured bottleneck |
| Rebuild per call or small batch | Reference only | Rebuild cost is the D1A diagnostic baseline and is not a production lifetime model |

The recommendation does not select transport for production. The future
prototype must pass every layer before another decision can select it.

## Consumer-envelope conclusion

The hard NC DIS proton PDF path is source-identifiable through
`SigmaProcess::sigmaPDF -> BeamParticle::xfHard`. Its configured domain is the
intersection of `x`, `Q2`, and `y` cuts under `Q2=x*y*s`. Initialization-time
phase-space queries must still be logged through `xfMax`/the hard pointer.

The shower-enabled configuration invokes event-state-dependent
`SimpleSpaceShower -> BeamParticle::xfISR -> xfModified`, and beam-remnant
construction uses resolved initiator state and valence/sea/companion methods.
MPI is explicitly off. Diffraction, resolved-photon/photon-flux paths, and
alternate hard PDFs must be asserted off or routed through the same facade.

Static inspection, `Pythia::init()`, and synthetic direct-method calls are all
necessary but not sufficient. Complete all-consumer evidence requires a
separately authorized controlled non-production `pythia.next()` execution with
fail-closed instrumentation because ISR and remnant sequences require event
state. It may discard every event and record only query provenance. Observed
queries validate but never define the predeclared envelope.

## Prospective evaluator contract

- PDG flavors, finite x and Q in GeV, output `x*f`; PYTHIA Q2 is square-rooted
  exactly once.
- Strict versioned support and no extrapolation/clamping.
- Explicit lower, exact, and upper charm/bottom threshold semantics; inactive
  top is typed.
- Immutable theta and policy identities, content-addressed cache, deterministic
  construction/destruction, and typed initialization/lifetime failures.
- Serial determinism, mutex-serialized threaded calls, and one context per
  process for parallel operation until stronger safety evidence exists.
- Underlying APFEL values remain unclipped. PYTHIA base-class positivity
  clamping is a separately reported generator-facade behavior.

## Prospective full NC observable gate

The future gate contains unpolarized e- and e+ F2, FL, xF3, reduced cross
sections, and `d2sigma/dx dQ2`, including gamma, Z, and gamma-Z interference.
It uses APFEL's space-like parity-even and parity-violating electroweak charges,
NLO coefficient functions, the same thresholds/evolution/alpha_s, and
`muF=muR=Q`. It spans the exact configured DIS intersection and one-sided
charm/bottom probes. Each comparison uses relative `1e-4` or absolute `1e-8`;
cross sections must be finite and nonnegative within a reported `1e-12`
numerical allowance. The lepton-charge sign convention must be verified before
any numerical result is accepted. The prior photon-only F2/FL pass is not this
contract.

## Validation hierarchy and performance

The ordered layers are: identity/support/determinism; persistent-versus-fresh
APFEL closure; threshold closure; performance/lifetime/safety; complete
consumer instrumentation; full gamma/Z observable closure; and only later,
under separate D2 authorization, event-distribution closure.

The required scalar capacity must be derived from measured operation:

```text
C_required >= N_pdf * R_selected / (epsilon * W * f_pdf)
```

where `N_pdf` is calls per attempted event, `epsilon` is selection efficiency,
`R_selected` is target accepted-event rate, `W` is CPU workers, and `f_pdf` is
the permitted PDF time fraction. All are currently unmeasured or undecided.
No inherited 1000-calls/s threshold is binding.

## Prospective caps and authorization boundary

- numerical wall time at most 30 minutes;
- generated output at most 2 GiB;
- center plus at most two predeclared stress anchors;
- no production event output or dataset;
- controlled event execution only if separately authorized;
- no D2 implementation or authorization.

The single next scientific action is review of this decision. A separate
authorization would be required before creating any persistent-evaluator
prototype issue or code.
