# Completed

- Imported validated QuarkSim DIS baseline into PartonSBI.
- Repository and scientific audit.
- Amortized-inference roadmap.
- Phase 0A typed streaming HepMC3 extraction.
- Rust baseline restored to green.
- Research-only repository cleanup and renaming.
- Phase 1A discrete LHAPDF-member reweighting infrastructure.
- Strict in-grid LHAPDF support contract and provenance-complete confirmation
  study.
- Phase 1A negative decision: nominal-pool reuse rejected by the predeclared
  ESS gate.
- Phase 1B-D design and staged acceptance contract.
- Phase 1B-D0 mathematical boundary-family implementation and complete
  441-point pilot-box study.
- Phase 1B-D0 negative decision: the proposed pilot family failed positivity
  and central-reconstruction gates.
- D0-revision audit and proposed baseline/admissibility contract.
- ADR-004 accepted and revised D0 projected-baseline revalidation completed.
- Phase 1B-D1 APFEL++ evolution and deterministic one-member LHAPDF artifact
  implementation.
- Phase 1B-D1 negative decision: the fixed off-knot transport and evolved
  sum-rule gates failed across the complete nine-anchor study.
- Phase 1B-D1 revision audit and ADR-005 proposal.
- ADR-005 accepted and revised D1 threshold-separated artifact implementation
  completed.
- Phase 1B-D1R negative decision: deterministic refinement exceeded its fixed
  performance cap, moment/leakage convergence failed, and direct off-knot
  transport remained outside tolerance across all nine anchors.
- Phase 1B-D1A evolved-PDF transport architecture audit completed with an
  `INCONCLUSIVE` decision and a bounded prototype authorization.
- Phase 1B-D1A bounded transport-comparison prototype completed with an
  `INCONCLUSIVE` decision: the fixed custom interpolator failed, while direct
  APFEL transport remained unselected because required evidence was not
  measured.
- Phase 1B-D1B source-level persistent-transport and PYTHIA-consumer audit
  completed with a recommendation for a separately authorized bounded
  prototype; this planning result does not itself authorize that prototype.
- Phase 1B-D1C-A persistent APFEL transport core implementation. This is an
  engineering milestone inside the authorized bounded prototype, not a
  completed scientific gate.

# Current state

- CLI and batch-oriented DIS research infrastructure.
- APFEL++, LHAPDF, PYTHIA 8, HepMC3, and Candle surrogate retained.
- No Cornell demo.
- No desktop GUI.
- Phase 1A is complete with a negative scientific result.
- The active support policy is `strict_in_grid`; PDF extrapolation is disabled.
- The clean 2,000-event confirmation pool had nominal `ESS/N = 0.04156296`,
  below the fixed 0.20 reuse threshold.
- Reweighting-based pool reuse is rejected; direct event generation is required
  at every PDF parameter point.
- The D0 input-scale continuous boundary family and validation CLI are
  implemented. This is not an evolved or generator-ready PDF artifact.
- The clean v1 D0 study evaluated 441 hard-box points and 80 guard-shell
  diagnostics. All hard-box points failed because the gluon became negative
  near `x -> 1`; the center also exceeded the fixed reconstruction tolerance.
- The D0-revision audit found no negative raw gluon knots. The inherited
  LHAPDF `logcubic` interpolant first crosses below zero off-knot at
  `x=0.9935531299173892`; its negative gluon momentum fraction is
  `1.5822152070733786e-11`.
- ADR-004 defines a versioned sum-rule-projected CT18NLO boundary and a
  baseline-relative NLO input-admissibility contract. That v2 contract is now
  implemented and has passed a clean 441-point/80-guard-point revalidation.
- The historical D0 v1 `FAIL` and revised-D0 v2 `PASS` remain unchanged.
- D1 was explicitly authorized after D0R review and is now complete with
  `STAGE1_DECISION = FAIL`.
- The clean D1 study evaluated exactly nine anchors from implementation commit
  `1a7181ad1582029aa93cf743807c24e18a147704`.
- Boundary callbacks and alpha_s knots passed, but 511,900 off-knot
  flavor-point round trips exceeded tolerance. The maximum evolved sum-rule
  residual was `4.2761916359967955e-4` at `Q=100000 GeV`.
- Deterministic APFEL-evolved LHAPDF artifacts now exist only in the ignored
  content-addressed cache. No artifact is generator-ready under the failed
  Stage 1 contract.
- The D1-revision audit found the lhagrid1 serialization correct: all exact
  knots passed, and an independent log-bicubic implementation reproduced
  LHAPDF. Off-knot errors are global finite-grid representation errors.
- The apparent high-Q conservation failure combines finite exported support
  with evolution below `x=1e-9`. On an APFEL computational grid extending to
  `1e-11`, independently integrated full-domain moments meet the proposed
  `1e-5` gate while the lost exported-support momentum remains explicit.
- ADR-005 defines threshold-separated, deterministically refined artifacts,
  computational-domain moment gates, raw-CT18 fidelity as a mandatory
  diagnostic, and NLO photon-exchange structure-function closure.
- The clean D1R study ran from commit
  `de26c57066dc018b530963d25d9a547b4b650c67` with `dirty=false` and evaluated
  all nine mandatory anchors on one common 641-x by 149-Q grid.
- Exact-knot serialization and independent LHAPDF log-bicubic reconstruction
  passed with zero tolerance failures, and all nine NLO photon F2/FL
  observable closures passed.
- The refinement trace stopped at `669.137992893 s` for its worst anchor,
  above the fixed 600-second cap. It retained `3,492,044` direct off-knot
  failures with maximum absolute error `1374.7964848542324`.
- The worst base and doubled full-domain residuals were
  `1.0118550574755858e-5` and `8.177903536354947e-6`; the maximum
  base/doubled leakage disagreement was `4.501148846980385e-7`, above the
  fixed `1e-7` gate.
- Revised Stage 1 is complete with `FAIL`;
  `D2_AUTHORIZATION_CANDIDATE = false` and `D2_AUTHORIZED = false`.
- ADR-006 rejects further unconstrained global LHAPDF refinement as the next
  path. It does not yet select between a direct APFEL-backed evaluator and a
  repository-owned deterministic interpolator because all-consumer PYTHIA
  reachability, evaluator safety, performance, and cache behavior remain
  unproven.
- A layered future acceptance contract requires PDF closure on a predeclared
  conservative all-consumer reachable domain, full neutral-current gamma/Z
  observable closure, and later separately authorized event-distribution
  closure. Global-support pointwise discrepancies remain mandatory
  diagnostics.
- The clean D1A prototype ran from commit
  `6cdd617cae88dc7b4d79a2388f1822076a8008bd` with `dirty=false`, three fixed
  anchors, no events, and the versioned
  `serde_json_float_roundtrip_pretty_v1` evidence policy.
- The fixed 6x6 custom bilinear representation reproduced all 396 stored knots
  at every anchor, but failed 245 of 275 off-knot comparisons at every anchor
  and failed one-sided threshold closure. It is rejected without post-hoc
  refinement.
- Direct APFEL deterministic batch repetition and strict support passed, but
  persistent scalar throughput, thread safety, process isolation, and the
  complete all-consumer query envelope were not measured. Direct APFEL
  transport remains unselected.
- The unresolved PYTHIA consumers are `initial_state_shower` and
  `beam_remnants`; all-consumer envelope closure is false.
- D1A is complete with `PROTOTYPE_DECISION = INCONCLUSIVE`,
  `DIRECT_CANDIDATE_STATUS = INCONCLUSIVE`, `CUSTOM_CANDIDATE_STATUS = FAIL`,
  and `D2_AUTHORIZED = false`.
- The D1B source audit found that an owned APFEL `Dglap<Distribution>` can
  outlive construction and answer repeated `Evaluate(Q)` calls, but neither
  APFEL reentrancy nor thread safety is established. The prospective design is
  one theta-specific in-process context with mutex-serialized access and a
  fresh rebuild-per-batch reference.
- Static source analysis and `Pythia::init()` cannot close the enabled ISR and
  beam-remnant consumer envelope. A future bounded prototype would require
  separately authorized, controlled non-production `pythia.next()` execution
  with fail-closed PDF instrumentation; observed queries may validate but not
  define the envelope.
- The D1B planning decision `AUTHORIZE_SEPARATE_BOUNDED_PROTOTYPE` was reviewed,
  and issue #39 separately authorizes the bounded D1C prototype.
- D1C-A now provides a theta-specific persistent APFEL context with opaque
  native lifetime, mutex-serialized evaluation, strict support, signed `x*f`,
  separate evaluator/theta identities, an exact-Q cache, and a safe Rust RAII
  owner. The fresh rebuild-per-batch APFEL path remains independent.
- The D1C-A preparation CLI can initialize and destroy the three authorized
  anchors and record a compact ignored manifest. It has no study, PYTHIA, or
  event-execution mode.
- D1C-A operational preparation completed successfully from clean commit
  `4fd1b3c45d339a8663ecf750f02662f96383691b`. This establishes only
  construction, metadata inspection, identity, and destruction evidence; the
  ignored raw manifest is preserved by hash in a compact reviewed evidence
  artifact.
- The final issue #39 decision is `D1C_FINAL_DECISION = FAIL`. Its binding
  generator-facing signed-PDF gate has FAIL precedence over every later
  unevaluated gate.
- The D1C-B source audit found a binding installed-interface incompatibility:
  PYTHIA 8.312's public `PDF::xf`, `PDF::xfVal`, and `PDF::xfSea` readers are
  non-virtual and apply positivity clipping. A subclass can fill signed cached
  values through `xfUpdate`, but calls through `shared_ptr<PDF>` still execute
  the clipping base readers.
- D1C-B therefore publishes no facade or transport identity and does not call
  `Pythia::init()` or `pythia.next()`. A deterministic native probe confirms
  that signed inclusive, valence, and sea values become positive zero at the
  public boundary. Runtime consumer attribution and pointer substitution
  evidence remain unavailable.
- Sixteen installed PDF pointer slots have a source-backed prospective
  classification; no runtime installation or post-init substitution was
  measured. Zero-event initialization, ISR/remnant attribution, complete
  consumer-envelope closure, full neutral-current gamma/Z closure,
  operational performance, and controlled event execution remain
  unevaluated. They are not required for the final decision because the
  binding sign failure terminates the acceptance hierarchy first. No full
  numerical study was needed or permitted after that failure.
- The failure is scoped to persistent in-process APFEL transport through the
  installed stock PYTHIA 8.312 public PDF subclass boundary. D1C-A remains
  engineering evidence but is not selected for production coupling. Other
  modified or custom generator interfaces are neither rejected nor authorized
  by issue #39.
- Issue #42 is active planning-only work. The independent integrity review
  rejected the v2 `READY_FOR_ARCHITECTURE_COMPARISON` claim because stored
  commands were not executable, the raw key and mappings were defective, 105
  declaration-derived locations were missing or unresolved, and 74
  classification defects plus one owning-symbol defect remained.
- The corrected v3/v2 artifacts use a repository-owned static generator and
  ten structured argument-array specifications over the same 374
  installed/release PYTHIA 8.312 files. All 4,033 occurrence-level canonical
  raw matches are classified: 1,109 included, 2,924 excluded with reasons,
  and zero unclassified. Exact regenerated-set equality and deterministic
  ordering pass.
- Audit v3 separates 146 call-site groups containing 703 concrete source uses
  from two boundary nodes, sixteen pointer-role records, five unresolved
  policy records, and one signed-LHA policy record. Mapping validation reports
  zero dangling targets, incompatible multi-target mappings, orphan
  search-derived records, nonexistent coordinates, or invalid symbols.
- Concrete static reachability is 226 prospective-HERA source-reachable, 444
  source-capable but disabled by configuration, and 33 unresolved. Boundary
  and pointer metadata are explicitly not runtime paths. Static reachability
  remains distinct from runtime coverage.
- Installed and extracted release copies of every cited installed PYTHIA
  header are byte-identical under independently recorded SHA-256 hashes. The
  full search manifest and its hash are bound into the v3 audit artifact.
- All 90 previously missed legitimate locations are now included as 31
  material consumers, 32 boundary records, and 27 pointer/policy provenance
  records. All 15 `getXPDF` locations remain explicit `UNRESOLVED` findings;
  none is suppressed to earn readiness.
- D1D-A finds that removing only the public `PDF::xf`, `PDF::xfVal`, and
  `PDF::xfSea` positivity transformations is `INSUFFICIENT`: prospective-HERA
  hard-process, ISR, and beam-remnant paths require nonnegative rates,
  denominators, probabilities, maxima, or monotone cumulative weights.
- For confirmed audited reachable paths, an external signed event weight
  cannot repair a sign that already changed an internal selection
  probability, veto, channel/remnant choice, maximum, or envelope. This claim
  is not generalized to the unresolved `getXPDF` paths. Existing signed Les
  Houches event-weight handling is not evidence for negative-PDF sampling.
- The validator derives `D1D_A_RESULT = EVIDENCE_CORRECTION_REQUIRED` because
  the 15 `getXPDF` semantic classifications remain unresolved. No PYTHIA fork,
  signed-weight design, alternate generator, implementation, or prototype is
  selected or authorized; issue #42 remains planning only.
- No PYTHIA continuous-PDF coupling, direct event corpus, sampling method,
  dataset, or amortized posterior model exists.

# Next scientific action

```text
A separately reviewed static classification of the 15 unresolved getXPDF
paths is required. Do not begin architecture comparison, any further
generator-coupling implementation, or D2 until the current D1D-A acceptance
conditions pass.
```

The approved design's later APFEL and fixed-envelope proposals remain
unimplemented hypotheses.

# Gate

- Do not reuse or reweight a nominal event pool.
- Do not begin D2: revised Stage 1 failed and
  `D2_AUTHORIZATION_CANDIDATE = false`.
- Do not reinterpret exact-knot or photon-observable closure as qualification
  of the failed direct off-knot transport contract.
- Any additional D1 revision requires a new reviewed architecture decision.
- The D1A prototype authorization is planning/validation only and cannot
  authorize production PYTHIA coupling or D2.
- The D1A `INCONCLUSIVE` decision does not select direct APFEL transport; the
  custom 6x6 representation is rejected and D2 remains unauthorized.
- Issue #39 authorizes only the bounded D1C prototype. D1C-A does not authorize
  production coupling, retained events, datasets, or D2, and it does not
  itself select production transport. The binding D1C-B sign failure completes
  issue #39's scientific result as `FAIL`.
- Do not proceed from D1C-B to runtime consumer instrumentation using the
  installed `PDF` subclass boundary: its non-virtual positivity-clipping
  readers violate the accepted signed-value contract.
- Issue #42 and D1D-A are planning only. The current result is
  `EVIDENCE_CORRECTION_REQUIRED`; architecture comparison, implementation,
  prototypes, and D2 remain blocked and unauthorized.
- Do not shrink the pilot box, clip negative densities, or change tolerances
  without a reviewed scientific decision.
- Do not begin neural inference until D0-D5 pass and a separate neural phase is
  authorized.

# Model recommendation

- Maintenance: GPT-5.6 Sol — Medium
- Scientific implementation: GPT-5.6 Sol — High
- Cross-phase architecture review: GPT-5.6 Sol — High
