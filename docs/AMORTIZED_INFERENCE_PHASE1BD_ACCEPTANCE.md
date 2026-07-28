# Phase 1B-D staged acceptance contract

Status: proposed gate contract for scientific review.

No criterion in this document is evidence that Phase 1B-D has been
implemented. Each stage produces an explicit `PASS`, `FAIL`, or
`INCONCLUSIVE` decision. A `FAIL` stops later stages. An `INCONCLUSIVE` also
stops continuation until the ambiguity is resolved and reviewed.

## Common rules

- Use direct, independently seeded generation at every PDF parameter point.
- Never reuse or reweight a nominal event pool.
- Never extrapolate a PDF beyond its declared support.
- Never clip, winsorize, discard by magnitude, or overwrite generator weights.
- Record exact commands, seeds, versions, hashes, Git commit, and dirty state.
- Keep generated grids, candidates, events, and large outputs untracked.
- Preserve the Phase 1A strict-support event and run-provenance contract.
- Treat `Q` and `Q2` distinctly and square `Q` exactly once for `Q2` APIs.
- Do not expose parameters, hashes, seeds, weights, hard flavor, or
  `GenPdfInfo` as default observed features.

## Stage 0 — boundary family and pilot box

Required points include the center, four corners, four axis endpoints, a
deterministic `21 x 21` scan of the complete proposed box, and a 5% expanded
guard shell used only as a conditioning diagnostic.

Pass only when:

- PDF metadata is read authoritatively and matches the selected baseline;
- `Q0` is the exact lower grid scale and all flavor conventions are verified;
- the center reconstructs the baseline boundary within `1e-6` relative error
  where `|xf| >= 1e-8`, and `1e-10` absolute error otherwise;
- valence residuals and momentum residual are each at most `1e-8` during
  construction and `1e-6` under independent quadrature;
- all normalizations are finite and strictly positive;
- no evaluated density is negative;
- heavy-flavor boundary values satisfy the documented zero condition;
- quadrature refinement changes every sum rule by at most `1e-8`;
- every tested point has a stable canonical ID and byte-identical manifest.
- parameters outside the hard pilot box return a typed error and are never
  projected onto its boundary.

Fail on an invalid normalization, a density below `-1e-12`, a sum-rule failure,
metadata mismatch, or non-deterministic identity.

Mark inconclusive for density values in `[-1e-12, 0)`, quadrature sensitivity,
or unresolved boundary interpolation. Do not shrink the parameter box after
seeing results without a new reviewed scientific decision.

Output: a small parameter scan, sum-rule report, and Stage 0 decision.

## Stage 1 — evolution and LHAPDF artifact

Test the center and every Stage 0 anchor over all artifact knots and a
deterministic off-knot sample.

Pass only when:

- APFEL++ uses the metadata-derived NLO order, masses, thresholds, and
  `alpha_s`;
- direct APFEL++ and the round-tripped LHAPDF artifact agree to `1e-5`
  relative error where `|xf| >= 1e-8`, and `1e-9` absolute error otherwise;
- reports include median, 95th-percentile, 99th-percentile, and maximum
  flavor-wise errors without dropping failed or near-zero points;
- artifact `alpha_s` agrees with the APFEL++ construction value to `1e-8`
  relative or `1e-10` absolute error at every tabulated `Q` knot;
- evolved valence and momentum sum rules satisfy `1e-5` independently;
- no knot or deterministic off-knot artifact evaluation is negative; the
  Stage 0 fail/inconclusive thresholds apply unchanged;
- the center agrees with CT18NLO member 0 to `2e-3` relative error for
  non-negligible grid values, with exceptions listed rather than averaged
  away;
- support metadata and every grid knot round-trip exactly;
- evaluating immediately outside every support boundary raises the declared
  error and never returns a frozen or extrapolated value;
- two clean builds produce byte-identical artifacts and hashes;
- a corrupted/truncated cache entry is rejected;
- concurrent builders publish one validated artifact without partial reads.

Fail on an unexplained flavor/order mismatch, sum-rule violation, hidden
extrapolation, cache corruption acceptance, or disagreement outside tolerance.
Mark inconclusive if discrepancies are localized to threshold interpolation
and their scientific effect has not been bounded.

Output: artifact manifest, round-trip report, central comparison, and Stage 1
decision. Generated grids remain ignored.

## Stage 2 — Pythia coupling and support

Initialize controlled center-point probes with the declared neutral-current
e-p configuration. This stage qualifies the coupling and query instrumentation,
not a generated event sample.

Pass only when:

- Pythia reports the exact generated artifact identity;
- APFEL++ validation and every Pythia PDF consumer use the same artifact;
- every PDF query is finite and inside the declared `x,Q` support;
- no Pythia boundary freeze or extrapolation path is exercised;
- the artifact records the same NLO order, thresholds, masses, flavor scheme,
  `alpha_s`, support, interpolation, and error-extrapolator policy used by
  APFEL++;
- direct controlled queries agree between APFEL++, LHAPDF, and the Pythia
  adapter under the Stage 1 tolerances;
- query counters cover hard, shower, and every other enabled PDF consumer;
- clean provenance and versioned configuration survive parse/serialize
  round-trips.

Fail on an unidentified PDF consumer, any unsupported accepted query,
artifact mismatch, ambiguous proton side, or counter inconsistency. Mark
inconclusive if Pythia cannot expose enough information to prove the
all-consumer contract; add instrumentation before proceeding.

Output: coupling manifest, controlled-query report, and Stage 2 decision.

## Stage 3 — direct generator smoke

Use the center, four axis endpoints, and four corners that passed Stages 0–2.
Each point uses an independent declared seed and a short directly generated
sample of exactly 100 accepted events. No point may consume events, weights,
or random streams from another.

Pass only when:

- Pythia reports the exact parameter-point artifact and member;
- every PDF query is finite and inside the declared `x,Q` support;
- no boundary freeze or extrapolation path is exercised;
- hard-process proton-side `GenPdfInfo` recomputes from the artifact within the
  unchanged `1e-6` tolerance;
- the scale used by the support decision is exactly the serialized
  `GenPdfInfo::scale = Q`;
- accepted events pass DIS, momentum, and strict-support selections;
- attempted, generated, vetoed, and accepted counters reconcile exactly;
- zero events have missing or ambiguous proton-side provenance;
- source weights and selected cross sections are retained without clipping;
- the HepMC3 streaming parser reads every accepted event and its run manifest;
- rerunning one point with the same seed produces byte-identical scientific
  records or a documented set of excluded nondeterministic metadata fields.

Fail on unsupported queries, artifact mismatch, structural event failure,
counter mismatch, seed reuse, clipping, or dirty/missing provenance. Mark
inconclusive when reproducibility or an enabled consumer cannot be observed
well enough to decide.

Output: nine small ignored event runs, compact smoke metrics, and Stage 3
decision.

## Stage 4 — weight semantics and event sampling

Use disjoint seed families for envelope calibration, production candidates,
Bernoulli selection, and validation. Predeclare the envelope rule and all
histograms before production.

Pass the second-stage accept-reject hypothesis only when:

- all source weights are finite and nonnegative;
- each point's calibration has exactly 100,000 Pythia-successful candidates;
- the fixed bound is exactly
  `next_up(2 * maximum_finite_nonnegative_calibration_weight)` and is frozen
  before its production candidate stream;
- zero production candidates have `w > M`;
- no bound is raised, weight clipped, or candidate removed after observation;
- inclusion uses the recorded probability `w/M` and an independent RNG;
- selected events all carry auditable source weights and random draws;
- at least two independent replicas agree under the predeclared direct-versus-
  direct test;
- selected unweighted one- and two-dimensional observables agree with
  independent weighted estimates after Holm family-wise correction, with no
  significant failures at family-wise `alpha = 0.01`;
- the maximum standardized mean discrepancy over predeclared scalar
  observables is at most `0.10`;
- unweighting efficiency, runtime, and uncertainty are reported;
- fixed-`N` shape-only and rate diagnostics are stored separately.

Fail on any bound breach, negative/non-finite weight, clipping, seed overlap,
or systematic distribution disagreement. Mark inconclusive when sample sizes
give less than 80% power for the declared `0.10` standardized discrepancy or
when source-weight semantics cannot be proven.

A Stage 4 failure does not authorize pool reuse, dynamic maximum tuning, or
neural training. It requires a new sampling-method decision.

Output: calibration and sampling manifests, weighted/unweighted closure
metrics, and Stage 4 decision.

## Stage 5 — small direct-generation design and scale decision

Use the center, accepted axis endpoints/corners, and at least one interior
point. Generate at least two fully independent direct replicas at each point.
Include a representative multi-point, multi-shard resource pilot.

Pass only when:

- no events or random streams are shared across points or replicas;
- artifact and event generation are reproducible from manifests;
- direct replicas pass the Stage 4 family-wise closure criteria;
- the central generated artifact agrees with direct CT18NLO generation under
  the same selection and sampling semantics;
- expected parameter directions produce reproducible distribution changes, or
  a documented negative sensitivity result;
- observed-feature construction passes explicit leakage tests;
- selected cross sections and all veto rates are reported but excluded from
  shape-only model inputs;
- support and provenance gates have zero structural failures;
- artifact construction, initialization, candidate generation, unweighting,
  serialization, storage, retry, and validation costs are measured;
- projected event, candidate, wall-time, peak-memory, and storage budgets are
  recorded with uncertainty;
- the plan fits a predeclared resource budget or explicitly reduces scope
  before corpus generation;
- interrupted shards resume without duplication or silent seed changes;
- all content hashes, split assignments, and manifests reproduce;
- no generated grid, event pool, cache, or local environment is tracked;
- the final dataset size and split policy are approved.

Fail on cross-point reuse, leakage, unsupported queries, unexplained replica
differences, hidden selection changes, resource overrun, non-reproducible
resume, or unavailable storage/compute. Mark inconclusive if sensitivity is
below measurement power or scaling uncertainty is too large to decide; do not
describe weak sensitivity as identifiability.

Output: anchor study, sensitivity/degeneracy report, feature-schema decision,
resource report, Stage 5 decision, and explicit `scale_up_allowed` boolean.

## Authorization matrix

| State | Direct artifacts | Direct pilot events | Large corpus | Neural inference |
| --- | ---: | ---: | ---: | ---: |
| Design review only | no | no | no | no |
| Stage 0 pass | D1 only | no | no | no |
| Stage 1 pass | yes | no | no | no |
| Stage 2 pass | yes | D2 smoke only | no | no |
| Stage 3 pass | yes | D3 sampling experiment only | no | no |
| Stage 4 pass | yes | D4/D5 anchors/resource pilot only | no | no |
| Stage 5 pass | yes | yes | separately authorized | no |

Neural inference always requires a later, separately reviewed phase even if
all Phase 1B-D stages pass.
