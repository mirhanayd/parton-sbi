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
- Phase 1B-D1D-A static evidence closure completed with a final `FAIL` at
  `provenance_evidence_integrity`; provenance slice v1 is retained only as a
  rejected diagnostic.

# Current state

- The Phase 1B closeout remains frozen. Its inventory correctly recorded no
  selected next phase at that time and is not modified by subsequent work.
- After closeout, the user explicitly authorized the independent,
  planning-only [Phase 2 reduced NC DIS line](reduced_nc_dis/README.md). The
  high-level set-level PDF SBI objective is unchanged; the simulator and
  observation contract are being reconsidered through an explicit normalized,
  detector-aware reduced model.
- [Phase 2A](reduced_nc_dis/ROADMAP.md) is in mathematical planning and
  primary-source contract review. It is not legacy D2. No Phase 2
  implementation, numerical physics, event, dataset, detector, or neural work
  is authorized.
- Issues #49 and #51 are closed. Issue #10 remains open, blocked, not
  evaluated, and unauthorized. Legacy D2 remains blocked; the full-generator
  line remains paused.
- The maintenance-only [Phase 1B closeout](PHASE1B_CLOSEOUT.md) and
  [identity manifest](phase1b_closeout_manifest.json) freeze the accepted
  evidence, ADR, merge-lineage, pause, and authorization record. They add no
  scientific result and select no next phase.
- Phase 1B-D1F is merged with
  `D1F_FINAL_DECISION = MAINTAIN_CURRENT_CONTRACT_AND_PAUSE`; the active
  full-generator line remains paused and no redesign is an active contract.
- Phase 1B-D1G is a planning-only independent primary-evidence review of four
  separate prospective contracts. The corrected v2 evidence-derived result is
  `NO_UNIQUE_PRIORITY_MAINTAIN_PAUSE`: every candidate is ineligible because
  preference-critical evidence remains unavailable.
- D1G v1 was never merged and is not immutable scientific state. Its
  independent audit found five verified, seven qualified, and one contradicted
  source identity; 14 claim scopes were overstated and one was misbound. The
  corrected registry has five verified and eight qualified identities.
- The contradicted D'Agostini record now uses the exact 1995 publisher DOI,
  article identity, and publication date. The Höcker-Kartvelishvili arXiv URL
  and hash are removed. No official downloadable article bytes were available,
  so its hash is null and its contextual limitation is explicit.
- The explicit 72-cell audited ledger yields qualified/unavailable totals of
  7/11 for Candidate B, 7/11 for Candidate C, 8/10 for Candidate D, and 9/9
  for Candidate E. Missing evidence is not converted into incompatibility.
- Candidate C is
  `SCIENTIFICALLY_MOTIVATED_COMPONENTS_PRESENT_BUT_PRIORITY_GATES_UNMET`.
  HERA formulae, unfolding context, SBC, and Deep Sets components do not define
  a normalized measure, coherent posterior, forward detector law, or composite
  end-to-end MVP. All fourteen mathematical, physics, support, detector, and
  closure obligations remain `NOT_EVALUATED`.
- The independent-evidence gate requires complete primary coverage of every
  preference-critical claim. The composite MVP separately requires nine
  physical-law, normalization, detector, representation, target, calibration,
  implementation, validation, and infrastructure components. Both gates remain
  unavailable for all four candidates.
- Validation is limited to deterministic artifact construction, identity and
  audited-ledger integrity, scope/maximum enforcement, derivation, and frozen
  boundaries. It does not independently re-read publications or prove
  scientific correctness, future source availability, discharged obligations,
  or executable validity.
- The next action is `MAINTAIN_PAUSE_PENDING_PREFERENCE_CRITICAL_EVIDENCE`;
  no lower-level contract proposal or other task is authorized. The active
  policy remains `PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION`.
- Issue #49 is closed. Issue #10 remains open, blocked, and
  unauthorized; D2 remains Blocked; D3-D5 remain Backlog; no roadmap
  supersession is active and all twelve authorization flags remain false.
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
- Issue #42 remains planning-only work. The byte-identical v3 broad search uses
  `PYTHON_REGEX_OCCURRENCE_ENGINE_V1` over 374 installed/release PYTHIA 8.312
  files. It searches all 779 derived identifiers and replays 67,375 raw and
  63,763 P10 syntactic occurrences with exact deterministic equality. This
  syntactic closure remains supported.
- The separate provenance slice v1 is now a deterministic rejected diagnostic
  prototype. Its independent integrity review found 720 syntactically
  confirmed roots, 162 ordinary uses promoted to roots, 43 calls promoted to
  roots, and 14 unresolved roots. All 939 reachability flags came from
  symbol/filename heuristics.
- With global fallback disabled, zero historical members had locally typed
  recovery: 669 paths selected the same global `class PDF` root and three
  calibration records (`CSG034.M006`, `CSG034.M007`, `CSG034.M014`) referenced
  absent units. The former 672/672 claim was construction-circular and is not
  readiness evidence.
- All 867 serialized paths have length two. Production contains no explicit
  multi-edge dataflow, assignment, argument/parameter, caller-return, cache
  write/read, forwarding, call, or alias propagation. Of 1,221 edges, only 314
  had source-supported meaning; 658 were synthetic root attachments, 181 had
  the wrong kind, 33 supported only the target, and 35 remained unresolved.
- Coordinate-level attribution admitted 209 same-line unrelated and 11
  declaration/comment occurrences, including wrong dispositions for four
  `state` and 28 `id` controls. The outside-slice challenge found 46 missed
  provenance occurrences at 32 coordinates and 189 unresolved occurrences at
  139 coordinates.
- The 35 lexical `getXPDF` occurrences are four mirrored inline definitions and
  31 direct calls, giving 33 mirror-deduplicated semantic source units. They
  remain scientifically unresolved; 35 separate dynamic-target claims are not
  supported.
- Seven of eight adversarial validator cases were incorrectly accepted. Audit
  v6 therefore removes v1 readiness, independent-recovery, outside-closure,
  negative-control, and valid-review-queue claims. V1 totals remain only under
  `REJECTED_DIAGNOSTIC_NOT_READINESS_EVIDENCE`.
- The 672 retained direct source-reviewed uses still pass brace-tracked
  function ownership, and all 66 denominator dispositions retain explicit
  curated coordinates and rationales. Those records—not provenance slice
  v1—support the minimal-reader conclusion.
- Audit v6 and the v1 decision artifact finalize
  `PROVENANCE_SLICE_V1_DECISION = FAIL` and `D1D_A_FINAL_DECISION = FAIL` at
  failed gate `provenance_evidence_integrity`. Architecture comparison is not
  ready.
- The evaluated audit-v5 input is bound by an immutable source-commit,
  repository-path, Git-blob, schema, and content-SHA-256 tuple. The historical
  source is commit `e197509928d5ccbbf7765956688522f919ccecec`, path
  `docs/phase1bd_d1d_pythia_semantics_audit.json`, and blob
  `b152650e4e21e4ac77cc5cbab2ca8d2c0aee1987`; the same live path now contains
  audit v6 and is not used as the v5 identity.
- D1D-A finds that removing only the public `PDF::xf`, `PDF::xfVal`, and
  `PDF::xfSea` positivity transformations is `INSUFFICIENT`: prospective-HERA
  hard-process, ISR, and beam-remnant paths require nonnegative rates,
  denominators, probabilities, maxima, or monotone cumulative weights.
- For confirmed audited reachable paths, an external signed event weight
  cannot repair a sign that already changed an internal selection
  probability, veto, channel/remnant choice, maximum, or envelope. This claim
  is not generalized to any machine-unreviewed candidate. Existing signed Les
  Houches event-weight handling is not evidence for negative-PDF sampling.
- The final D1D-A decision uses `EVIDENCE_INTEGRITY_FAIL_PRECEDENCE`. No
  PYTHIA fork, signed-weight design, alternate generator, architecture,
  implementation, or prototype is selected or authorized. PR #43 is merged;
  issue #10 and D2 remain blocked.
- Phase 1B-D1D-B v3 proposes the evidence-derived result `INCONCLUSIVE` for the
  fixed signed-generator coupling contract. The validator binds every external
  source to the repository-owned exact identity registry, requires explicit
  source-to-claim bindings for every evidence-bearing score, and independently
  recomputes candidate and architecture route states, the Architecture C
  aggregate, all six rule fields, the decision, and the operational policy.
- Architecture A and the final-event-weight Architecture B are
  `COHERENT_BOUNDED_PATH_NOT_SUPPORTED`. Architecture C is
  `COHERENT_BOUNDED_PATH_POSSIBLE_WITH_EVIDENCE_GAPS`: Sherpa and Herwig each
  have six unavailable and four qualified critical criteria with zero
  affirmative critical failures; LHEF has eight affirmative and two qualified
  critical criteria and remains a boundary transport rather than a complete
  generator route.
- Sherpa hard-process coverage is only `SUPPORTED_WITH_QUALIFICATION`. Its
  pinned HERA configuration does not prove complete gamma/Z/interference
  compatibility, which remains `PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE`. Negative
  MC@NLO complete-event weights are not evidence for signed internal PDF rates
  or signed Sudakov kernels.
- All reviewed external byte representations and reported hashes were
  independently reproduced on 2026-08-01. The hashes identify the reviewed
  bytes, but those bytes are not vendored or archived here; future availability
  still depends on the official hosts. This is not currently blocking because
  every load-bearing identity reproduced.
- Current policy is `PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION`. This is an
  interim pause under the failed readiness gate, not a selected terminal stop
  and not a universal impossibility theorem.
- Generator coupling may be reconsidered only after one of these evidence
  conditions is separately reviewed: (1) signed-kernel and signed-Sudakov
  mathematics; (2) a pinned primary-source generator interface proving signed
  scalar, rate, ISR, remnant, and event-weight semantics; (3) an independently
  validated complete consumer/dataflow graph; or (4) a separately reviewed and
  approved change to the PDF-family or inference contract. A reopen condition
  is not an authorization.
- All ten D1D-B authorization flags are false. Issue #42 is closed as completed
  planning work. Architecture comparison was not promoted to readiness, issue
  #10 stays blocked, and D2 remains unauthorized.
- Phase 1B-D1E now records the corrected planning-only result
  `D1E_PROPOSED_DECISION = INCONCLUSIVE`. The previous draft `FEASIBLE`
  result is superseded. `PREFERRED_FEASIBILITY_CANDIDATE =
  LLVM_CLANG_LIBTOOLING_18_1_8`, while `SELECTED_TOOLCHAIN = null`.
  Preference is not permission to acquire, install, run, or implement LLVM.
- The authoritative future source contract has one semantic tree,
  `.external/src/releases-pythia8312`, with 127 headers and 120 core
  translation units. The 127 byte-identical installed headers are identity
  evidence only and cannot create duplicate semantic nodes. Clean CI performs
  `PORTABLE_MANIFEST_VALIDATION_ONLY`: it does not retrieve the official
  archive or independently resolve the upstream tag/commit. Optional ignored
  source bytes are checked only when the local checkout exists.
- `COMPILE_CONTRACT_STATUS =
  SOURCE_INSPECTION_CORRECTED_BUT_PARSE_NOT_VALIDATED`. A future command set
  must add `-DXMLDIR="<PINNED_SHARE_ROOT>/xmldoc"` for `Pythia.cc` and
  `-DFJCORE_HAVE_LIMITED_THREAD_SAFETY` for `FJcore.cc`; the previous empty
  definition list and one-template argv claim were false. No parser ran and
  the exact 120-TU command inventory remains future work.
- Typed declarations, definitions, assignments, call/parameter/return flow,
  member/cache flow, and explicit unresolved states replace every prohibited
  identifier, filename, historical, global, or synthetic fallback. The 672
  historical records remain a blinded post-construction holdout; `state`,
  `size`, `id`, `push_back`, `p`, and `Vec4` remain mandatory exact-occurrence
  negative controls. Twenty-five binding definitions now cover node/source
  schemas, stable identities, path and reachability rules, aliases, callbacks,
  ODR/templates/macros, exclusions, material misses, resource/truncation
  limits, unresolved caps, independent review, and machine gate predicates.
- Static evidence cannot establish runtime pointer installation, post-init
  substitution, configuration-selected targets, query envelopes, or
  thread/process behavior. It also cannot solve signed-rate or signed-Sudakov
  mathematics. All 18 future acceptance gates must pass before a graph can
  claim completeness.
- `IMPLEMENTATION_COST_BOUND = NOT_SUPPORTED`. The original 7.0-week estimate
  is retained only as challenged history; independent implementation ranges
  are 15.2/30.6/57.4 person-weeks. Independent reproduction is 1/2/3 weeks,
  so its two-week cap is supported only with qualification. These are
  feasibility ranges, not scheduling commitments.
- AST graph work remains potentially valuable for
  `provenance_evidence_integrity`, but this record authorizes no implementation.
  No parser or graph was implemented, no compilation database or production
  nodes/edges were generated. Issue #45 is closed as completed planning with
  `INCONCLUSIVE`; issue #10 and D2 remain blocked under
  `PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION`.
- Phase 1B-D1F v3 corrects the unmerged v2 termination proposal after the
  independent integrity audit. V2 was never merged and is not an immutable
  scientific result. The corrected independent axes derive
  `D1F_CURRENT_LINE_DISPOSITION = MAINTAIN_CURRENT_FULL_GENERATOR_PAUSE`,
  `D1F_PREFERRED_SEPARATE_CONTRACT_REVIEW = NONE`, and
  `D1F_TOP_LEVEL_DECISION = MAINTAIN_CURRENT_CONTRACT_AND_PAUSE`.
- Five current-line propositions are directly supported, accepted-generator-
  measure absence is an explicit inference, and two propositions remain
  `NOT_EVALUATED`: a bounded alternative-generator path and preservation of
  the current contract by continuation. Missing evidence is not converted into
  affirmative incompatibility, so termination is not derived.
- `ACTIVE_OPERATIONAL_POLICY =
  PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION`,
  `CURRENT_FULL_GENERATOR_LINE =
  PAUSED_NO_BOUNDED_CONTINUATION_ESTABLISHED`, and
  `LOWER_LEVEL_CONTRACT_REVIEW =
  PLAUSIBLE_BUT_NOT_PREFERRED_OR_AUTHORIZED`.
- The six reviewed choices are: preserve the current D0R/full-generator
  contract and pause; define a prospectively new nonnegative family; define a
  lower-level neutral-current DIS hard-event law; adopt a weighted empirical
  event-set objective; create signed-weight inference research; or terminate
  the current Phase 1B full-generator line.
- Normalized-measure gates are `PASS_WITH_QUALIFICATION` for the preserved
  contract, a new nonnegative family, the lower-level hard-event model, and a
  positive weighted empirical measure; `FAIL` for signed-weight research; and
  `NOT_APPLICABLE` for termination. Option A is not operationally instantiated.
  Option C has only a plausible mathematical form, not a completed measure.
- The lower-level option proposes `z ~ p_theta(z)`, `y ~ K(y|z)`, and a fixed-N
  set `D={y_i}`, with `p_theta` proportional to the accepted full neutral-
  current differential rate. Exact electron/positron formulae, F2/FL/xF3
  conventions, gamma/Z/interference terms, electroweak scheme, scales, flavors,
  phase-space Jacobian, finite normalization, complete-rate positivity, strict
  support, detector-kernel normalization, identity-kernel case, independent
  numerical closure, and omitted-physics declaration remain unevaluated proof
  obligations.
- The lower-level observation is not a full-generator event. Its future
  contract must enumerate omitted ISR, showering, hadronization, underlying
  event, and beam-remnant effects and may not claim full-generator equivalence.
- The lower-level option remains
  `PLAUSIBLE_SEPARATE_REVIEW_CANDIDATE_REQUIRES_INDEPENDENT_EVIDENCE` and
  `INCOMPLETE_BUT_REVIEWABLE`. It is not preferred, selected, authorized, or
  implementation-ready. Its fourteen proof obligations remain
  `NOT_EVALUATED`.
- ADR-010 is a decision record and contract description, not independent
  evidence for its own candidate. The v3 scorecards bind every source claim to
  an exact option and criterion. The audit baseline is preserved as 17 direct,
  30 qualified, 53 misbound, 8 unsupported, 1 overstated, and 11
  not-applicable historical classifications. Corrected cells comprise 17
  direct immutable, 30 explicit-inference, 62 prospective-hypothesis, and 11
  not-applicable evidence classes.
- No roadmap supersession is active. Issue #10 remains open, blocked, not
  evaluated, and not authorized; D2 remains blocked and D3-D5 remain backlog.
  If a lower-level contract were separately accepted later, ADR-002 and
  ADR-006 would require prospective supersession, ADR-003 would require
  explicit confirmation, and Neural would require a new decision. A
  lower-level model cannot complete issue #10.
- The nonnegative-family option would be a new active family and theta
  contract, not a correction to D0R. D0R remains immutable evidence. The
  scientific justification for imposing NLO nonnegativity for generator
  compatibility is not established.
- Weighted empirical sets are not ordinary iid unweighted sets. Positive
  normalized weights can define an empirical probability measure only with a
  proposal/weight law, ESS, posterior, loss, and repeated-sampling calibration.
  Signed weights do not pass as probabilities. This option would prospectively
  supersede ADR-003's primary objective.
- Signed-weight research fails the normalized-measure gate because no reviewed
  positive data law, posterior, proper loss, or coverage definition exists.
  Negative complete-event weights alone do not supply those semantics.
- All D0R, D1, D1R, D1C, D1D, and D1E results remain immutable evidence. D1C
  remains `FAIL`, the minimal public-reader patch remains `INSUFFICIENT`, the
  provenance slice remains a rejected diagnostic, D1D-A remains `FAIL`, and
  D1D-B and D1E remain `INCONCLUSIVE`.
- Issue #47 is planning-only work. Issue #10 remains open and blocked; D2,
  event generation, datasets, neural training, every implementation, and every
  prototype remain unauthorized.
- `LOWER_LEVEL_NORMALIZED_MEASURE_STATUS = PASS_WITH_QUALIFICATION`,
  `D1F_LOWER_LEVEL_CANDIDATE_STATUS =
  PLAUSIBLE_SEPARATE_REVIEW_CANDIDATE_REQUIRES_INDEPENDENT_EVIDENCE`,
  `LOWER_LEVEL_SIMULATOR_AUTHORIZED = false`,
  `EVENT_GENERATION_AUTHORIZED = false`, `DATASET_AUTHORIZED = false`,
  `NEURAL_TRAINING_AUTHORIZED = false`, and `D2_AUTHORIZED = false`.
- Independent evidence does not establish a unique separate-review priority.
  Prospective hypotheses cannot become load-bearing preference evidence.
- No PYTHIA continuous-PDF coupling, direct event corpus, sampling method,
  dataset, or amortized posterior model exists.

# Next scientific action

```text
MAINTAIN_PAUSE_PENDING_PREFERENCE_CRITICAL_EVIDENCE
```

No new contract review is created. Another priority review is warranted only
after independent evidence addresses a candidate's normalized measure,
posterior, no-hidden-repair, and composite MVP gaps. Candidate C's fourteen
obligations remain `NOT_EVALUATED`. The maintained pause authorizes no
lower-level simulator, implementation, parser, generator, event, dataset,
numerical closure, neural work, issue #10, roadmap supersession, or D2 work.

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
- Issue #42 is closed as completed D1D planning. D1D-A is final `FAIL`, D1D-B
  is final `INCONCLUSIVE` with an interim non-authorizing pause, and D1E is a
  feasibility result only. Architecture-comparison readiness remains false;
  issue #45 is a closed planning record, while all implementations,
  prototypes, issue #10, and D2 remain blocked and unauthorized.
- Do not shrink the pilot box, clip negative densities, or change tolerances
  without a reviewed scientific decision.
- Do not begin neural inference until D0-D5 pass and a separate neural phase is
  authorized.

# Model recommendation

- Maintenance: GPT-5.6 Sol — Medium
- Scientific implementation: GPT-5.6 Sol — High
- Cross-phase architecture review: GPT-5.6 Sol — High

# Phase 2A Review

Phase 2A review is complete. PR #63 merged at
`e798a64265afd806bb7030218e2fac60e1656a78`, issue #54 is closed/completed,
and the final scientific decision is `INCONCLUSIVE`.

The accepted gate grouping is:

- `SUPPORTED`: `posterior_target_coherence`,
  `fixed_n_shape_only_semantics`, `paper_claim_boundary_consistency`,
  `selected_event_conditioning_coherence`.
- `SUPPORTED_WITH_QUALIFICATION`:
  `finite_positive_normalization_reviewability`, `strict_support_contract`,
  `normalized_detector_kernel_contract`,
  `bounded_identifiability_and_information_plan`.
- `PRIMARY_EVIDENCE_UNAVAILABLE`: `exact_formula_contract`,
  `no_hidden_clipping`, `bounded_phase2b_validation_plan`.

Phase 2B issue #55 remains Backlog with Gate Decision Not Evaluated,
Authorization Not Authorized, and execution `NOT_EXECUTED`; its proposal is
`INCOMPLETE`. Phase 2 umbrella issue #53 remains In Progress. Legacy issue #10
remains Blocked, Not Evaluated, and Not Authorized. ADR-013 remains Proposed.

## Phase 2 follow-on heavy-flavor contract amendment

A bounded post-closeout source review selected
`D1_PREPARE_FONLL_A_NLO_CONTRACT_AMENDMENT`. APFEL FONLL-A at NLO is the only
eligible reviewed candidate: it preserves the accepted PDF family and reduced
NC DIS question and has a pinned APFEL 3.1.1 configuration surface. RTOPT has
no bound implementation path, FFN requires a new PDF contract, and ZM-VFN
requires a predeclared high-`Q2` validity-domain narrowing.

This is a follow-on amendment, not a retroactive Phase 2A PASS. Historical
Phase 2A remains complete and `INCONCLUSIVE`; ADR-013 remains Proposed. The
mass convention and values, shared `alpha_s` identity, anchors, grids,
tolerances, convergence rules, complete independent FONLL-A reference, and
resource bound remain unresolved pre-authorization evidence. Phase 2B remains
unauthorized, incomplete, and unexecuted. No formula evaluation, positivity
scan, normalization integration, event generation, dataset, detector
implementation, or neural work has occurred.

## Phase 2B pre-authorization validation plan

The versioned follow-on plan derives
`P1_PREAUTH_PLAN_COMPLETE_READY_FOR_SEPARATE_AUTHORIZATION_REVIEW`. It binds
the heavy-quark pole masses, shared `alpha_s` identity, nine theta anchors,
physics domain, coordinate/Jacobian convention, deterministic grids,
source/error-budget tolerances, convergence rules, an independent-reference
decomposition, finite resource bounds, no-clipping positivity policy,
normalization closure and failure precedence.

This is planning completeness only. Historical Phase 2A remains complete with
scientific decision `INCONCLUSIVE`; ADR-013 remains Proposed. Phase 2B remains Not Authorized,
issue #55 remains Open/Backlog with Gate Decision Not
Evaluated, and execution remains `NOT_EXECUTED`. No APFEL numerical physics,
positivity or normalization scan, event, dataset, detector, or neural work was
performed.

## Phase 2B execution authorization review

The successor authorization review derives
`AR2_PREAUTH_PLAN_REVISION_REQUIRED`. The P1 artifact remains complete as a
reviewable plan, and the FONLL-A selection remains viable, but execution is not
authorized. The review requires amendments for the shared CT18/APFEL
`alpha_s` identity, operational complete-rate high-precision sign
adjudication, exact deformed-PDF bridge/reference coverage, normalization
implementation independence, and the `0.0013`/near-zero error budgets.

Phase 2B remains Not Authorized, Open/Backlog, Gate Decision Not Evaluated,
and `NOT_EXECUTED`. Historical Phase 2A remains `COMPLETE/INCONCLUSIVE` and
ADR-013 remains Proposed. Phase 2C and all event, dataset, detector, neural,
legacy D2, and full-generator work remain unauthorized.

## Phase 2B preauthorization v2 successor

The scientific successor plan derives
`RV1_PREAUTH_V2_COMPLETE_READY_FOR_NEW_AUTHORIZATION_REVIEW`. It addresses the
four AR2 blockers at the planning level by binding an AS2 dual-provider
`alpha_s` comparison, an NR2 propagated sign envelope, an exact future
PDF/APFEL bridge test, independently implemented normalization quadratures,
mixed near-zero comparator rules and a complete numerical error allocation.

This is not an execution authorization. Phase 2B remains Not Authorized,
Open/Backlog, Gate Decision Not Evaluated and `NOT_EXECUTED`; every actual DIS,
positivity, normalization, convergence and reference comparison remains
unexecuted. Historical Phase 2A remains `COMPLETE/INCONCLUSIVE`, ADR-013
remains Proposed, and Phase 2C and all downstream work remain unauthorized.

## Phase 2B v2 execution authorization review

The independent successor review derives
`AR2_PREAUTH_V2_REVISION_REQUIRED`. Its critical classifications are
`BUDGET_PARENT_NOT_JUSTIFIED`, `ERROR_BUDGET_STRUCTURE_INVALID`,
`AS2_REVISION_REQUIRED`, and `BRIDGE_PLAN_REVISION_REQUIRED`. The published
approximately 0.1% APFEL/MassiveDISsFunction component discrepancy is not a
formal parent allowance for the complete rate and normalized law. The frozen
503,284 resource cap also undercounts RK4 work required per flavor segment,
and load-bearing NumPy remains unpinned.

Phase 2B remains Not Authorized, Open/Backlog, Gate Decision Not Evaluated,
and `NOT_EXECUTED`. Historical Phase 2A remains `COMPLETE/INCONCLUSIVE`;
ADR-013 remains Proposed. Phase 2C and all event, dataset, detector, neural,
legacy D2, and full-generator work remain unauthorized.
