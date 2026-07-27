# Roadmap for amortized PDF inference from sets of DIS events

## 1. Scientific objective

Develop and validate an amortized inference system that maps one pseudo-experiment containing many unbinned DIS events,

```text
D = {event_1, event_2, ..., event_N},
```

to a calibrated posterior over a deliberately identifiable, low-dimensional PDF parameter vector,

```text
p(theta_PDF | D).
```

The model estimates parameters shared by the ensemble that generated the events. It must never be described as measuring an “instantaneous PDF of one proton from one event.”

The first milestone is a simulator closure test, not a phenomenological global PDF fit. It will use truth-level synthetic pseudo-experiments, a narrow PDF family, an explicitly defined neutral-current electron-proton channel, a permutation-invariant encoder, and calibration diagnostics.

## 2. Non-goals for the first implementation

- Full free-form PDFs or independent parameters for every flavor.
- Claims of `u_v/d_v/strange/charm/gluon` separation from one inclusive NC channel.
- Real-data inference or publication-grade PDF uncertainties.
- GEANT4, detailed detector geometry, unfolding, or hundreds of detector nuisances.
- Intrinsic charm.
- Simultaneous ZMVFNS/GM-VFNS morphing.
- Normalizing flows, Factorizable Normalizing Flows, or differentiable coverage penalties before a Gaussian closure test passes.
- Making PYTHIA, APFEL++, or LHAPDF differentiable.
- Reusing the existing pointwise structure-function surrogate as an event-set posterior model.

## 3. Governing design constraints from the audit

1. APFEL and PYTHIA currently load immutable LHAPDF grids; no continuous `theta_PDF` API exists.
2. The raw HepMC3 record has useful hard-PDF information, but the Rust reader cannot parse it reliably.
3. The APFEL pure-photon and PYTHIA gamma/Z definitions must be harmonized or explicitly separated.
4. A single nominal pool may be reused only after an importance-reweighting closure test against direct alternate-PDF generation.
5. Dataset splits must be by parameter point, pool, and seed family—not by individual event rows.
6. The first target must follow the limited identifiability of inclusive NC `e- p` data.

## 4. Staged implementation plan

### Phase 0 — restore and specify the forward baseline

Work:

1. Restore `cargo fmt --check` and test compilation without changing scientific behavior.
2. Define one authoritative event-process configuration: beam charge, gamma-only versus gamma/Z, perturbative/hard-process assumptions, shower, hadronization, cuts, and PDF provenance.
3. Replace or correct the HepMC3 reader with a streaming, standards-compliant extraction path that preserves particle IDs, vertices, weights, `GenPdfInfo`, event scale, and run metadata.
4. Introduce no ML yet. Write schema fixtures from real HepMC3 output and test them.

Acceptance criteria:

- `cargo fmt --all -- --check`, `cargo check --workspace`, and `cargo test --workspace` pass in the supported WSL environment.
- The C++ CTest and declared Python tests pass from documented commands.
- A real generated event round-trips into typed fields with correct PDG IDs, status, four-vectors, vertices, event weight, hard incoming flavor, `x`, factorization proxy scale, nominal PDF values, run seed, and set/member.
- The event-process definition is identical across generation and any analytic comparison, or differences are machine-readable and intentional.

### Phase 1 — PDF parameterization and reweighting feasibility

**Current decision.** Phase 1A is complete. A provenance-clean, strict-support
confirmation study rejected reweighting-based nominal-pool reuse because the
nominal, mild-member, and stress-member samples all had `ESS/N < 0.20`.
Consequently:

- reweighting-based pool reuse is rejected;
- direct generation at every PDF parameter point is required;
- hard-PDF ratios remain diagnostics, not an authorized event-pool path; and
- neural inference remains unimplemented.

The next planned subphase is **Phase 1B-D — Continuous, sum-rule-preserving PDF
family with direct event regeneration**. The `-D` suffix records the direct
generation route. Planning is permitted; implementation is outside Phase 1A
and must not revive the failed nominal-pool reuse path.

Work:

1. Implement a small, sum-rule-aware continuous PDF family at `Q0` behind a versioned interface.
2. Feed it to APFEL++ through the existing distribution-callback mechanism, or generate validated temporary LHAPDF grids. Do not silently interpolate PDF members.
3. Implement a proton-side hard-PDF reweighting prototype from raw `GenPdfInfo`.
4. Compare reweighted nominal events against direct alternate-member generation using disjoint seeds.
5. Measure support overlap and effective sample size (ESS).

Acceptance criteria:

- Numerical valence and momentum sum rules satisfy a documented tolerance at every allowed parameter point.
- All parton densities used by the generator are finite; positivity policy is tested on a dense `x` grid.
- APFEL evolution of the reference point reproduces the selected reference PDF/structure functions within an agreed tolerance.
- For at least two alternate CT18NLO members or controlled deformations, reweighted and regenerated distributions agree within predeclared statistical tolerances for `x,Q2,y`, hard flavor, multiplicity, and chosen hadronic summaries.
- ESS is reported for every tested target. A target with `ESS/N < 0.2` or pathological tail weights is not served by reuse.
- If closure fails, the recorded decision is direct regeneration per parameter point; training does not proceed on unvalidated weights.

### Phase 2 — truth-level pseudo-experiment dataset

Work:

1. Generate or reweight split-specific event pools.
2. Assemble many-event pseudo-experiments with complete provenance.
3. Freeze feature transforms using training data only.
4. Implement a binned likelihood/chi-square baseline over the same pseudo-experiments.

Acceptance criteria:

- Every pseudo-experiment has `theta`, split, pool ID, seed family, event-selection definition, and generator/model provenance.
- No base event, pool, or seed family crosses train/validation/test boundaries.
- Empirical event counts and weighted rates follow the declared luminosity/count model.
- Feature distributions are finite and cut-consistent; a schema validator rejects incomplete records.
- Baseline inference recovers central synthetic points within expected Monte Carlo uncertainty.

### Phase 3 — first amortized posterior closure

Work:

1. Implement a DeepSets full-covariance Gaussian posterior in Candle.
2. Train with Gaussian negative log likelihood on complete event sets.
3. Compare against a diagonal Gaussian ablation and the binned baseline.
4. Run the complete calibration and leakage suite below.

Acceptance criteria:

- Held-out-`theta` bias and RMSE meet predeclared thresholds relative to prior width and the binned baseline.
- Mean posterior NLL improves over the prior predictor and is competitive with the binned baseline.
- Coverage at 50%, 68%, 90%, and 95% is statistically compatible with nominal coverage; deviations must lie inside precomputed binomial confidence bands or trigger recalibration/model revision.
- SBC ranks show no statistically significant systematic skew/U-shape after accounting for finite sample size and multiple checks.
- Posterior width contracts with event count and does not collapse on OOD/edge cases.
- Repeated training with the same seed is reproducible; different seeds report performance dispersion.
- Inference time and peak memory are benchmarked for the target `N`.

### Phase 4 — detector-systematics extension

Work:

1. Add a versioned fast detector response, initially for scattered-electron energy and angle.
2. Add acceptance, efficiency, and reconstruction masks.
3. Recompute detector-level `Q2,x,y` and selected hadronic summaries.
4. Add a small nuisance vector and either condition on it or marginalize it through simulation.

Acceptance criteria:

- Truth-to-reconstruction response is validated against controlled analytic/toy expectations.
- Efficiency and acceptance are bounded and reproducible from seed/configuration.
- Closure passes when train/test detector nuisances match.
- Coverage remains acceptable when test nuisances are held out within the declared range.
- Missingness/masks cannot leak `theta` or split identity.

### Phase 5 — theoretical-systematics extension

Work:

1. Add scale variations, heavy-flavor-scheme alternatives, shower/hadronization tune variations, and PDF-reweighting approximation uncertainty one at a time.
2. Encode each theory configuration in metadata.
3. Treat theory variables as explicit nuisance parameters or simulator mixture labels; never hide them in random seeds.

Acceptance criteria:

- Each nuisance has a documented prior and an independently reproducible simulator configuration.
- Posterior coverage is tested with nuisance values unseen during training.
- Nominal PDF uncertainty does not absorb identifiable generator mismodeling without diagnostics.
- Reweighting approximation error is included or reweighting is disabled where closure fails.

### Phase 6 — flavor/channel expansion

Candidate additions, in evidence order:

1. multiple proton beam energies to improve `F2/FL` separation and gluon sensitivity;
2. NC `e+ p` with consistent electroweak `xF3` treatment;
3. CC `e- p` and `e+ p`;
4. neutron/deuteron or controlled nuclear targets;
5. charm tags, strange-sensitive final states, jets, and validated semi-inclusive observables.

Acceptance criteria:

- Each new channel has generator, cross-section, event-schema, and validation tests.
- An information/Fisher or simulation study demonstrates that the channel adds an independent constraint before a new flavor parameter is introduced.
- Flavor-expanded fits pass the same SBC, coverage, posterior-predictive, seed-split, and OOD tests as the MVP.
- No “full flavor separation” claim is made until independent channels demonstrably resolve the relevant degeneracies.

## 5. Smallest scientifically valid MVP

The MVP begins only after Phases 0 and 1 pass.

### 5.1 Parameter vector and reference scale

Use two shared PDF directions at

```text
Q0 = 1.30 GeV,
theta = (delta_v, lambda_sea).
```

Reference densities are the CT18NLO central member at `Q0`. The proposed family is intentionally not flavor-separated:

- `delta_v` applies a common low-`x` shape tilt `x^delta_v` to both `u_v` and `d_v`; separate normalization constants restore `integral u_v dx = 2` and `integral d_v dx = 1`.
- `lambda_sea` multiplies the common light-antiquark sea sector by `exp(lambda_sea)`. The relative `ubar:dbar:s:sbar` shapes remain fixed to the reference.
- Heavy flavors retain the reference boundary prescription.
- The gluon shape is fixed and its positive normalization is determined by the momentum sum rule after the quark deformation.

This parameterization tests whether event sets recover a high-`x`-versus-low-`x` valence/sea deformation. It does not claim independent `u_v`, `d_v`, strange, charm, or free gluon extraction.

Proposed priors for the pilot:

```text
delta_v    ~ Uniform(-0.20, 0.20)
lambda_sea ~ Uniform(-0.25, 0.25)
```

These are engineering priors, not phenomenological uncertainties. Before freezing them, scan the full rectangle and narrow it if the dependent gluon normalization becomes non-positive, APFEL evolution fails, or importance weights have unacceptable ESS.

### 5.2 Sum rules and positivity

- Enforce valence-number integrals numerically at `Q0` for every parameter point.
- Enforce total momentum fraction equal to one by solving for one dependent gluon normalization.
- Construct multiplicative factors with exponentials/powers so reference-positive components remain positive.
- Reject parameter points if any reconstructed flavor or the dependent gluon becomes negative/non-finite on a dense logarithmic-plus-high-`x` grid.
- Store integral residuals and minimum density in each parameter-point manifest.

### 5.3 Observable channel and event features

Initial channel:

```text
NC e- p at Ee = 27.5 GeV, Ep = 920 GeV,
one harmonized electroweak definition,
truth-level perfect detector,
fixed shower/hadronization configuration.
```

Use a minimal per-event feature vector derived without target leakage:

```text
[log x, log Q2, logit y, log W2,
 log E_scattered, cos(theta_scattered),
 log(1 + N_charged), log(1 + N_final), event_weight]
```

Start with the first six inclusive/lepton features if hadronic reweighting closure is weaker than inclusive closure. Hard flavor and nominal PDF values are reweighting/provenance fields, not default inference inputs; using them as observed features would be unphysical for data. Raw truth particles should be retained in storage for later studies but not required by the first encoder.

Use explicit masks for any missing value, and fit all normalization transforms on training splits only.

### 5.4 Pseudo-experiment design

Pilot values:

| Quantity | MVP value |
| --- | --- |
| Events per pseudo-experiment | `N = 1,024` fixed initially; later test 256, 512, 2,048, 4,096 |
| Parameter points | 128 space-filling points in the prior rectangle |
| Pseudo-experiments per point | 100 |
| Total set examples | 12,800 |
| Total event slots | 13,107,200, assembled from split-specific pools |

If direct regeneration is required, begin with 64 parameter points and 50 pseudo-experiments per point as a resource pilot, then scale only after measured throughput/storage are available. The inspected ASCII HepMC footprint is about 86 MiB per 10,000 events, so training should consume a compact columnar feature artifact rather than repeatedly parse HepMC3. Raw events remain immutable provenance artifacts.

### 5.5 Split strategy

Assign whole parameter points before any pseudo-experiment construction:

- 72 points train;
- 16 points validation;
- 24 points in-prior interpolation test;
- 8 points edge-of-prior stress test;
- 8 points reserved for OOD just outside the training box but inside the simulator-safe domain.

Within each split, use disjoint generator pools and seed families. A base generated event or seed family may belong to only one split. Pseudo-experiments at the same `theta` can share a split-specific pool only with documented resampling, overlap statistics, and grouped evaluation. Randomly splitting event rows is forbidden.

The primary test is unseen `theta`. A second test holds out seed families at selected training-domain `theta` values. Report both; neither substitutes for the other.

### 5.6 Posterior and baseline

Primary posterior: a two-dimensional full-covariance Gaussian with mean vector and Cholesky-parameterized covariance. This represents the dominant correlation between the two PDF directions with only three covariance outputs.

Baseline: bin the same selected events in a fixed two-dimensional `(log x, log Q2)` grid chosen from training simulations, use weighted Poisson/compound-Poisson or an explicitly justified Gaussian likelihood, and infer the same two parameters by grid scan/interpolation. Also report a prior-only predictor.

The binned baseline must use identical cuts, luminosity/count conditioning, event weights, and split provenance.

### 5.7 Expected cost

- Raw storage at the observed HepMC3 density is roughly 8.6 KiB/event, so 1 million raw events is approximately 8.6 GiB before compression. Compact nine-feature `f32/f64` records are orders of magnitude smaller.
- APFEL currently launches one subprocess per point; dense grid construction will be process-launch dominated unless a batch protocol is added later.
- DeepSets training over 12.8 million event slots is modest on a modern GPU and feasible on CPU for a pilot, but actual wall times must be measured rather than promised.
- Direct PYTHIA generation cost is not recorded by the repository. Phase 1 must benchmark events/s and bytes/event before approving the full sample count.

### 5.8 Known physics limitations

- Only one beam charge, one proton target, and one nominal beam-energy pair.
- No independent `u/d`, strange, charm, or gluon parameter.
- ZM-VFNS limitations near charm threshold.
- No target-mass, higher-twist, or complete radiative-correction treatment.
- PYTHIA shower/hadronization model dependence.
- Perfect detector and fixed acceptance in the first closure test.
- Importance reweighting, if used, is an approximation whose closure/ESS domain must be explicit.
- A Gaussian posterior may not represent boundary-induced skewness; edge failures trigger later architecture work, not automatic flow adoption.

## 6. Architecture comparison

| Option | Strengths | Risks in this repository | Recommendation |
| --- | --- | --- | --- |
| A. DeepSets + diagonal Gaussian | Smallest implementation; permutation invariant; easy Gaussian NLL | Cannot represent correlation between `delta_v` and `lambda_sea`; may give misleading marginal coverage | Implement as an ablation/smoke baseline, not the primary closure model |
| B. DeepSets + full-covariance Gaussian | Still simple; directly captures the expected two-parameter degeneracy; Cholesky output guarantees positive covariance | Requires stable covariance parameterization and joint calibration tests | **First primary model** |
| C. Set Transformer + Gaussian | Can model event-event interactions and adaptive attention | Higher memory roughly with set-size squared unless induced/pooled variants are used; little justification for inclusive scalar features | Consider only if DeepSets fails predictive checks for demonstrable representation reasons |
| D. Set encoder + conditional normalizing flow | Can model skewed/multimodal posteriors | More code, validation burden, and numerical failure modes; Candle support would require substantial custom work or a second stack | Defer until a Gaussian demonstrably fails away from boundaries |

### 6.1 Proposed first network

```text
per-event MLP phi: 9 -> 64 -> 64
masked mean aggregation (plus log N or total expected count)
context MLP rho: 65 -> 64 -> 32
posterior head: 2 means + 3 Cholesky parameters
```

If event count itself carries cross-section information, it must be generated from a declared luminosity/count model and provided explicitly. If all sets are conditioned on fixed `N`, the model learns shape information only; it must not be described as using total-rate information.

The covariance diagonal uses a positive transform with a floor; the off-diagonal is unconstrained in the Cholesky factor. Train by average per-set Gaussian NLL. Add gradient clipping only if diagnostics show instability.

## 7. Candle versus Python

Recommendation: **native Candle in Rust for the first DeepSets Gaussian closure**, with the existing Python environment retained only for independent scientific analysis and plots.

Reasons:

- Candle tensor/autograd, linear layers, AdamW, CPU/optional CUDA, and safetensors are already dependencies and exercised by two training paths.
- DeepSets and a two-dimensional Gaussian NLL require only basic tensor operations; a second ML framework is not justified.
- Keeping event schema, batching, model, and inference in Rust reduces cross-language drift for the first closure.
- Python already provides NumPy/SciPy/pandas/Matplotlib baseline and calibration analysis; it is not currently a training stack and even lacks pytest in its declared requirements.

Before training, the Rust path must add deterministic seeds for parameter sampling, pool sampling, model initialization, and batching; mini-batch set loading; checkpoint/resume; and complete run manifests. If a later conditional flow is scientifically necessary and Candle implementation becomes disproportionate, reconsider a hybrid Python research trainer with safetensors/ONNX-compatible export at that time. Do not add PyTorch/JAX merely for the Gaussian MVP.

## 8. Proposed data schema

Use versioned, immutable manifests plus compact columnar event features. A conceptual schema is:

```text
run_manifest
  schema_version
  git_commit + dirty flag
  generator/APFEL/LHAPDF/PYTHIA/HepMC versions
  process and electroweak definition
  beam IDs, charges, energies
  cuts, shower, hadronization, scales
  nominal PDF set/member
  theta_parameterization_version, Q0, theta
  sum_rule_residuals, positivity minimum
  pool_id, seed_family_id, generator_seed
  reweighting_method, source_theta, ESS diagnostics

event_record
  experiment_id, event_id, pool_event_id
  event_weight, target_weight, inclusion_probability
  x_true, Q2_true, y_true, W2_true
  scattered electron four-vector
  charged/final multiplicities
  optional raw-particle reference
  hard_flavor, pdf_x1/x2, pdf_scale, nominal_xf1/xf2  # provenance/reweighting only

pseudo_experiment
  experiment_id, split, theta_id, theta
  pool_id, seed_family_id
  event_count, luminosity/count-model fields
  ordered list/offsets into event_record (order has no meaning)
```

Store the event order randomly permuted during training and test permutation invariance explicitly. Never expose `theta_id`, pool ID, seed, file path, generation timestamp, or reweighting source as model features.

## 9. Validation plan

### 9.1 Required inference metrics

- Parameter recovery bias overall and as a function of true `theta`.
- RMSE and MAE per parameter, normalized by prior width.
- Posterior negative log likelihood.
- Posterior contraction versus prior and versus event count.
- Simulation-based calibration rank histograms for each parameter and suitable joint diagnostics.
- Empirical marginal and joint coverage at 50%, 68%, 90%, and 95%, with binomial uncertainty bands.
- Posterior predictive checks for unbinned/binned `x,Q2,y`, scattered-lepton, multiplicity, and any selected hadronic features.
- In-prior unseen-`theta` test.
- Held-out-random-seed-family test.
- Edge-of-prior and controlled out-of-training-prior stress tests.
- Comparison against the binned chi-square/likelihood baseline and prior-only predictor.
- Training wall time, throughput, peak memory, checkpoint size, and per-pseudo-experiment inference latency.

### 9.2 Leakage prevention

- Split parameter points first.
- Split generator pools and seed families second.
- Construct pseudo-experiments only within a split.
- Fit transforms/binning on training only.
- Keep all augmented/reweighted descendants of one base event in one split.
- Group repeated pseudo-experiments that share a finite pool when computing uncertainty.
- Hash and record source pool membership so overlap can be audited.
- Never split adjacent rows from one generated file across train and test without an explicit, justified grouped design.

### 9.3 Posterior predictive checks

For each held-out dataset, draw `theta` from the inferred posterior, simulate or reweight replicated datasets, and compare:

- one- and two-dimensional kinematic distributions;
- event count if rate is modeled;
- tails near analysis cuts;
- hard-flavor fractions as a hidden diagnostic, not an observed feature;
- charged/final multiplicities when hadronic features are used; and
- summary discrepancies chosen before viewing test results.

A posterior can have acceptable parameter RMSE and still fail posterior predictive checks; such a model does not pass closure.

## 10. Stop/go rules

- Do not train if continuous PDF generation or reweighting has not passed Phase 1.
- Do not add flavor parameters because a network can output them; add them only after observable information supports them.
- Do not progress to detector nuisances until truth-level SBC and coverage pass.
- Do not progress to a flow until the full-covariance Gaussian fails a diagnosed posterior-shape requirement on adequate simulations.
- Do not use the current surrogate as simulation truth while its checked-in maximum test relative `F2` error is about 112.5%.
- Do not mix events from the same pool/seed family across evaluation splits.

## 11. Single next implementation step

Write and review the Phase 1B-D scientific design for a continuous,
sum-rule-preserving PDF family whose parameter points are simulated through
direct event regeneration. Define parameter support, sum-rule tolerances,
generator coupling, seed separation, computational budget, and acceptance
criteria before implementation. Do not train a neural model or reuse the
rejected nominal-pool weighting path.
