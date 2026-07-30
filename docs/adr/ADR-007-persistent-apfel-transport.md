# ADR-007: Persistent APFEL transport and PYTHIA consumer coverage

- Status: Proposed for scientific review
- Decision date: 2026-07-30
- Scope: Phase 1B-D1B planning only
- Decision: `AUTHORIZE_SEPARATE_BOUNDED_PROTOTYPE`
- Prototype authorized by this ADR PR: `false`
- D2 authorized: `false`

## Context

The approved D0R boundary family passed. D1 and D1R both failed their finite
LHAPDF transport contracts. D1A then compared a rebuild-per-batch APFEL
reference with one fixed 6-by-6 threshold-aware bilinear representation. That
representation failed its binding off-knot and threshold gates. Direct APFEL
remained `INCONCLUSIVE` because a persistent scalar path, safety, lifetime,
cache behavior, and complete PYTHIA consumer coverage were not measured.

This decision preserves all three results. In particular, the fixed 6-by-6
failure does not reject other custom representations, and the direct APFEL
candidate is unselected rather than failed. The decision is based on committed
evidence and local source inspection only; no APFEL run, PYTHIA run, numerical
prototype, or event generation was performed.

## APFEL lifetime audit

The installed primary sources support a persistent evolution object but do not
establish concurrent safety:

- `.external/src/apfelxx-4.8.0/inc/apfel/dglapbuilder.h:231` declares
  `BuildDglap(...) -> std::unique_ptr<Dglap<Distribution>>`; its construction
  in `.external/src/apfelxx-4.8.0/src/evolution/dglapbuilder.cc:1117-1144`
  materializes the reference distributions and returns an owned object.
- `.external/src/apfelxx-4.8.0/inc/apfel/matchedevolution.h:74` exposes
  `Evaluate(double mu) const`. The implementation in
  `.external/src/apfelxx-4.8.0/src/kernel/matchedevolution.cc:74-109` evolves
  from the retained reference object through threshold matching for every Q
  evaluation. Reusing `Dglap` therefore avoids rebuilding grids, splitting
  objects, matching conditions, and the boundary, but it does not make a new
  Q evaluation free.
- `TabulateObject<Set<Distribution>>::EvaluatexQ` and `EvaluateMapxQ` are
  const evaluators over retained Q-grid values
  (`inc/apfel/tabulateobject.h:122-137`,
  `src/kernel/tabulateobject.cc:197-229`). Such a table is a new finite
  transport representation and is not accepted as direct APFEL by definition.
- `src/apfel_evolution_bridge.cpp:210-241` and `338-363` currently construct
  `AlphaQCD`, the APFEL grid, and `Dglap` inside each bridge call. The D1A
  direct rate therefore measures batch reconstruction, not persistent scalar
  service. The observable bridge's `direct_cache_q` at lines 471-481 is only a
  last-Q cache within one call.
- The bridge's alpha callback captures `AlphaQCD` by reference. A persistent
  context must own `AlphaQCD` for longer than `Dglap`, with destruction order
  encoded in its type. The same context can own thresholds, masses, QCD order,
  flavor conversion policy, boundary identity, and alpha_s metadata. The raw
  LHAPDF boundary object is needed during construction, not scalar evaluation.
- Evaluation is syntactically const, but APFEL has process-global mutable
  verbosity state (`src/kernel/messages.cc:32`), and the current bridge also
  calls `LHAPDF::setVerbosity`. Neither project supplies a reentrancy or
  thread-safety guarantee for this combined path. Constness is not sufficient
  evidence.

The prospective context is therefore immutable after successful construction,
except for a mutex-protected exact-last-Q cache and counters. All construction,
evaluation, and destruction are serialized per context. One context is owned
by one theta-specific generator worker; contexts are never concurrently read
without the lock. Process-level parallelism is the default safety boundary.
This is a testable safety model, not a claim that APFEL is thread safe.

## Architecture alternatives

| Option | Identity and lifetime | Cost and safety | PYTHIA feasibility | Decision |
|---|---|---|---|---|
| A. Persistent in-process APFEL with serialized scalar access | One theta-specific identity owns `AlphaQCD`, thresholds, boundary provenance, grid, and `Dglap`. Fresh direct APFEL is the independent reference. | Initialization is paid once. New Q values still perform evolution; same-Q flavor/x calls may reuse a locked exact-Q distribution. Memory scales with live theta contexts. A mutex provides a conservative concurrency boundary but not crash isolation. | Synchronous scalar calls fit `PDF::xfUpdate`; one generator/context per process avoids shared-PDF races. | Selected for a separate bounded feasibility prototype. |
| B. Persistent process-isolated APFEL worker with deterministic batched IPC | Same mathematical identity, held by a worker process. | Best crash/global-state isolation; deterministic request framing is possible. Per-scalar IPC and scheduling can dominate because PYTHIA calls are synchronous and not naturally batchable. More lifecycle and failure-recovery state. | Feasible as a fallback if in-process safety fails, but performance risk is material. | Retained revisit option, not the first prototype. |
| C. Rebuild per query or small batch | Direct mathematical reference with no persistent lifetime. | Repeats grid/evolution construction. D1A measured only about 151-154 effective calls/s for batch rebuilding. | Useful for oracle comparisons, not acceptable as production transport. | Diagnostic reference only. |

A pretabulated APFEL object or another custom interpolator would require its
own transport identity and closure gates. The failed 6-by-6 table cannot be
silently refined or reinterpreted in this decision.

## Prospective evaluator contract

The future prototype, if separately authorized, must implement this contract:

- Input flavors use PDG IDs `-6..-1, 1..6, 21`; top is inactive and returns a
  typed inactive-flavor outcome, never an extrapolated value.
- The API accepts finite `x` and Q in GeV and returns `x*f_i(x,Q)`. A PYTHIA
  facade accepts Q2 in GeV2 and takes the square root exactly once before the
  evaluator. Negative Q2, NaN, and infinity fail closed.
- Calls are accepted only inside the versioned intersection of D0R support and
  the evolution contract. There is no extrapolation or clamping.
- At charm and bottom thresholds, exact-threshold behavior and lower/upper
  one-sided limits follow the retained APFEL matching convention and are
  recorded; a caller cannot choose a side implicitly.
- Results and alpha_s, when requested, must be finite. Initialization,
  unsupported flavor, support, threshold, lifetime, cache, and evaluator
  failures are typed.
- The theta identity and evaluator-policy identity are separate immutable
  SHA-256 identities. Cache keys contain both, APFEL/LHAPDF versions,
  integration/evolution policies, thresholds, support, and compiler-facing
  ABI version.
- The cache owner constructs once, publishes only after validation, and
  destroys the `Dglap` before its owned `AlphaQCD` dependency. A failed or
  partially constructed context is never queryable.
- Serial calls are deterministic. Threaded calls are serialized by the
  context mutex until measured evidence permits anything stronger. Parallel
  work uses one context and one PYTHIA instance per process. A process-isolated
  mode must have deterministic request ordering, timeouts, crash detection,
  and no automatic scientific fallback.

PYTHIA's base `PDF::xf`, `xfVal`, and `xfSea` maintain mutable cached state and
apply `max(0, ...)` (`PartonDistributions.cc:122-391`). A future facade must
record and test this behavior explicitly: the underlying evaluator must never
clip, and generator-facing clipping/inherited-sign consequences cannot be
called evaluator identity.

## PYTHIA consumer audit

The installed source is PYTHIA 8.312 under
`.external/src/releases-pythia8312`. Its `PDF` contract receives Q2 and exposes
`xfUpdate`, `xf`, `xfVal`, `xfSea`, `insideBounds`, `alphaS`, `mQuarkPDF`,
`xfMax`, `xfSame`, and photon-specific methods. `Pythia::setPDFPtr` can install
ordinary, hard, pomeron, photon, unresolved, and VMD pointers
(`include/Pythia8/Pythia.h:111-122`). Therefore public `xfUpdate` inspection
alone cannot prove complete coverage.

| Consumer | Enabling configuration and call chain | Methods and variables | Exercise and bound | Status |
|---|---|---|---|---|
| Hard NC DIS | `WeakBosonExchange:ff2ff(t:gmZ)=on`; `SigmaProcess::sigmaPDF` -> `BeamParticle::xfHard` -> hard PDF | `xfMax` during phase-space initialization, then `xfHard/xf`; x and factorization Q2 | Initialization and synthetic hard calls cover the method family. The configured hard envelope is analytic. | `COVERED` for source/design; runtime instrumentation still required for final evidence |
| Initial-state shower | `PartonLevel:ISR=on`; `SimpleSpaceShower` -> `BeamParticle::xfISR` -> `xfModified` -> `xf`, `xfVal`, `xfSea` | Dynamic daughter/mother x and `pdfScale2`; `alphaS` may also be queried | Calls depend on evolving parton systems. Synthetic calls test the facade but cannot prove the enabled shower path. | `REQUIRES_EVENT_EXECUTION` |
| Beam remnants | `PartonLevel:Remnants=on` by default; `BeamRemnants::add` -> `BeamParticle::remnantFlavours*`, with `pickValSeaComp`/modified PDFs from the resolved initiator state | `xfVal`, `xfSea`, `xf` and companion/valence bookkeeping x,Q2 | Real DIS remnant state is event dependent. Direct synthetic invocation cannot establish all query sequences. | `REQUIRES_EVENT_EXECUTION` |
| MPI | Repository explicitly sets `PartonLevel:MPI=off`; enabled source uses `MultipartonInteractions` -> `xfMPI/xfISR` | Dynamic x and pT2/factorization Q2 | Must remain off and init must fail if changed. | `DISABLED_BY_CONFIGURATION` |
| Diffraction | No soft/diffractive process is enabled; `Diffraction:doHard` defaults off. `BeamSetup::initPDFs` creates pomeron PDFs only for diffraction | Pomeron/hard PDF methods and diffractive x/scale | Must be asserted off; any activation invalidates the envelope. | `DISABLED_BY_CONFIGURATION` |
| Resolved photon and photon flux | Electron beam is direct NC DIS; `PDF:lepton2gamma=off` and `Photon:ProcessType=0` defaults are retained. `BeamSetup` otherwise installs gamma, unresolved, hard-gamma, and flux pointers | `xfFlux`, `xfApprox`, `xfGamma`, ordinary/hard photon PDFs | Must be asserted off; photon modes require a new consumer audit. | `DISABLED_BY_CONFIGURATION` |
| Alternate/hard PDF pointer | `BeamSetup::initPDFs` may replace `pdfHard*` when `PDF:useHard`; `setPDFPtr` accepts separate pointers | `xfHard`, `xfMax`, `xfSame` | Prototype must install the instrumented proton facade as both ordinary and hard B pointer and fail if `PDF:useHard` selects another object. | `REQUIRES_RUNTIME_INSTRUMENTATION` |
| Initialization-time trials | `BeamSetup::initPDFs` creates pointers; `SigmaProcess::sigmaPDF(initPS=true)` can use `xfMax` | x and factorization Q2 selected during phase-space setup | `Pythia::init()` plus fail-closed logging covers observed initialization calls, but static analysis cannot prove their full numerical range. | `REQUIRES_RUNTIME_INSTRUMENTATION` |

## Event-execution requirement and query envelope

Static analysis defines the method set and disabled branches. `Pythia::init()`
can exercise pointer installation and phase-space setup. A synthetic harness
can test every virtual method and fixed boundary probe. Neither establishes
the event-state-dependent ISR and remnant call sequences. Complete evidence
for the declared shower-enabled, hadronized DIS configuration therefore
requires a separately authorized, controlled **non-production event
execution** using `pythia.next()` and a fail-closed instrumented PDF facade.
It must not save events, define the envelope from observations, or constitute
production generation. This task authorizes no such execution.

The hard-process domain is the exact intersection

`x in [1e-4,0.8]`, `Q2 in [3.5,10000] GeV2`, `y in [0.01,0.95]`,
`Q2 = x*y*s`, with `s = 4*27.5*920 GeV2`,

and strict evaluator support. ISR and remnants receive a conservative envelope
of the full declared evaluator support in x and Q2 unless source-level bounds
prove a smaller superset before execution. MPI, diffraction, photon, alternate
hard-PDF, and other optional consumers must be explicitly disabled or routed
through the same instrumented facade. Any out-of-envelope call terminates the
run with a typed record; it never extrapolates.

Instrumentation records consumer class, method, flavor, exact x/Q2 bits, call
count, and rejection reason as provenance diagnostics. These generator-only
records are not observed ML features. Observed calls may validate coverage but
never define or shrink the predeclared envelope. Complete coverage requires:
every enabled source-listed consumer is instrumented; all disabled settings
are manifest-checked; initialization, synthetic method probes, and controlled
event execution complete without unclassified or out-of-envelope calls; and
the instrumentation itself is tested fail closed.

## Full neutral-current observable contract

The D1R photon-only check used `InitializeF2NCObjectsZM` and
`InitializeFLNCObjectsZM` with fixed electromagnetic charges. It omitted Z,
gamma-Z, and xF3 and is not a full NC gate.

A future binding contract must use the installed APFEL++ 4.8.0
`InitializeF2NCObjectsZM`, `InitializeFLNCObjectsZM`, and
`InitializeF3NCObjectsZM`, built at NLO with the same thresholds, evolution,
and alpha_s. Parity-even charges come from `ElectroWeakCharges(Q,false)` and
parity-violating charges from
`ParityViolatingElectroWeakCharges(Q,false)`; the `false` argument selects
space-like virtuality. The APFEL constants and on-shell electroweak convention
must be serialized, not silently replaced. Beams are unpolarized electrons
and positrons, tested separately; no polarization term is allowed.

With `Y_plus = 1 + (1-y)^2` and `Y_minus = 1 - (1-y)^2`, compare F2, FL, xF3,
the reduced cross section

`sigma_r(e±) = F2 - y^2/Y_plus * FL ∓ Y_minus/Y_plus * xF3`,

and

`d2sigma(e±)/(dx dQ2) = 2*pi*alpha_em(Q2)^2/(x*Q2^2) *
 [Y_plus*F2 - y^2*FL ∓ Y_minus*xF3]`.

The e+/e- sign mapping must be verified against APFEL's charge convention in
the prototype before accepting any number. Use `muF=muR=Q`, the declared beam
energies, and exactly the hard-domain intersection above. Compare persistent
and fresh-reference paths at deterministic log-grid points, cut boundaries,
and one-sided charm/bottom threshold probes. Each F2, FL, xF3, reduced, and
differential-cross-section comparison passes when relative error is at most
`1e-4` or absolute error is at most `1e-8`; the rule is fixed before running.
Require finite F2/FL/xF3 and nonnegative differential cross sections within a
`1e-12` absolute numerical allowance; values in `[-1e-12,0)` are reported as
borderline, not clipped. This prospective contract must be reviewed before it
is executed.

## Validation hierarchy for a separate prototype

1. Identity, metadata, strict support, finiteness, and determinism.
2. Persistent evaluator versus a freshly rebuilt direct-APFEL reference at
   fixed deterministic probes.
3. One-sided charm and bottom threshold closure.
4. Scalar/batch throughput, initialization, memory, lifetime, cache,
   serialized thread stress, and multi-process isolation.
5. Complete fail-closed PYTHIA consumer instrumentation and envelope evidence.
6. Full unpolarized neutral-current gamma/Z F2, FL, xF3, reduced, and
   differential-cross-section closure for e- and e+.
7. Later and separately authorized D2 event-distribution closure.

## Performance requirement

No fixed calls-per-second threshold is justified yet. Let `N_pdf` be measured
PDF calls per attempted event, `epsilon` the accepted/attempted efficiency,
`R_selected` the target accepted-event rate, `W` CPU workers, and `f_pdf` the
maximum permitted PDF fraction of worker time. Required per-worker scalar
service is

`C_required >= N_pdf * R_selected / (epsilon * W * f_pdf)`.

Initialization is separately constrained by
`T_init * N_theta_contexts / reuse_count`; it must not be hidden in scalar
throughput. `N_pdf`, `epsilon`, the research throughput target, feasible W,
allowed PDF fraction, Q-cache hit rate, and mutex/IPC overhead remain unknown
until fail-closed runtime instrumentation. D1A's 1000 calls/s criterion is not
carried forward as a binding threshold.

## Decision

The source evidence justifies recommending
`AUTHORIZE_SEPARATE_BOUNDED_PROTOTYPE` for Option A: one persistent,
theta-specific in-process APFEL context with serialized access and a fresh
rebuild-per-batch reference. The safety model, consumer strategy, reference,
acceptance hierarchy, and event-execution requirement are concrete enough to
test. This is a recommendation for a separate authorization decision only:
`PROTOTYPE_AUTHORIZED=false` in this planning PR.

Prospective caps are 30 minutes numerical wall time, 2 GiB generated output,
and center plus at most two predeclared stress anchors. The prototype must use
no production event output and must stop fail closed on any unknown consumer,
support violation, cache identity failure, nondeterminism, or unmet closure
gate. It cannot authorize D2.

## Consequences and rejected alternatives

- Rebuild-per-query is rejected as production transport and retained only as
  an independent reference.
- Process-isolated IPC is retained as the fallback if serialized in-process
  safety or crash containment fails; it is not selected first because
  synchronous scalar IPC is an unmeasured bottleneck.
- APFEL `TabulateObject` and new custom interpolators remain separate finite
  transport proposals. The fixed 6-by-6 result stays failed.
- The future prototype must acknowledge PYTHIA `PDF` caching and positivity
  clamping, not mistake facade output for exact evaluator identity.
- D1/D1R failures, D1A `INCONCLUSIVE`, and all global discrepancies remain
  historical evidence. No acceptance threshold is changed here.

## Revisit conditions

Revisit the architecture if serialized persistent evaluation cannot meet the
derived performance budget, APFEL lifetime or destruction tests fail, process
isolation is required for correctness, PYTHIA consumer instrumentation finds
an unbounded or unsupported call path, the full gamma/Z contract is ambiguous,
or controlled event execution cannot be separately authorized. Record an
`INCONCLUSIVE` or negative result rather than expanding D2 scope.
