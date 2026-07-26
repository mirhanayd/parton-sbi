# Phase 1A: discrete LHAPDF-member hard-PDF reweighting closure

## Status

**BLOCKED at the Stage A support gate.** The fresh full-event nominal smoke
sample contains an event whose serialized PDF scale lies below the declared
CT18NLO grid. The mandated structural-support stop rule was applied before any
direct-target sample was generated. Phase 1A remains incomplete, pool reuse is
not permitted, and Phase 1B is not permitted.

## Scientific hypothesis

For an event generated with nominal member `n` and target member `t`, the
proton-side hard-PDF approximation is

```text
r_i = [x f_t(a_i, x_i, mu_i)] / [x f_n(a_i, x_i, mu_i)]
w_i,target = w_i,nominal r_i.
```

Here `a_i`, `x_i`, and `mu_i` are hidden generator truth from HepMC3
`GenPdfInfo`. This phase tests reuse of a set of simulated events. It is not an
instantaneous PDF measurement from one event and does not expose generator
truth as an observed inference feature.

## Event-weight and rate semantics

The active PYTHIA process writes exactly one HepMC3 `W` value per inspected
event. It is `Pythia8::Info::weight()` and must be used when filling
histograms. The active Born process is normally non-negative and often unit
weighted, but PYTHIA can assign weights above unity when its phase-space
maximum is violated. The inspected imported 10,000-event run contained weights
from `1` to `883.1042720955727`; they are not clipped. The parser continues to
support signed weights, and a future signed sample must preserve them.

Multiple weights require an explicit index. Missing weights are invalid; unity
is never fabricated.

HepMC `GenCrossSection` is PYTHIA's evolving cross-section estimate at the time
an event is written, not a final run normalization. Phase 1A generation now
records final `sigmaGen`, `sigmaErr`, `Info::weightSum`, selected-event weight
sums, and

```text
sigma_selected = sigmaGen * selected_weight_sum / Info::weightSum
```

in `summary.json`. Rate closure is established only when both nominal and
direct-target runs contain this final contract. Older runs are shape-only and
must report `RATE CLOSURE NOT ESTABLISHED`.

## LHAPDF semantics

`managed-lhapdf` 0.4.2 calls LHAPDF `xfxQ2(id, x, Q2)`: it accepts `Q2` in
`GeV2` and returns `x f(id,x,Q2)`. HepMC `GenPdfInfo::scale` is `Q` in GeV.
PartonSBI therefore squares that scale exactly once in
`LhapdfProvider::xfx_at_scale` and compares the returned `x f` with the stored
proton-side `xf`.

## Proton-side identification

The supported channel requires exactly one status-4 electron beam (PDG 11) and
one status-4 proton beam (PDG 2212), consistent with run provenance when beam
IDs are recorded. Exactly one of the two `GenPdfInfo` entries must be the
electron. The other must be PDG 21 or `+/-1` through `+/-5`. This rule is
ordering-independent. Missing, double-lepton, unsupported, or ambiguous
entries are typed invalid outcomes.

## Denominator policy and fixed tolerance

The primary denominator is the generator-stored nominal proton-side `xf`.
PartonSBI independently recomputes the nominal value and records both ratios.
Before direct-target closure, the relative consistency tolerance is fixed to

```text
1.0e-6
```

using

```text
abs(xf_stored - xf_recomputed) / max(abs(xf_stored), 1e-300).
```

The tolerance is deliberately wider than the approximately eight significant
digits in the observed HepMC serialization. Events outside it are quarantined;
the implementation does not switch denominators. A recomputed-denominator run
is secondary sensitivity analysis only.

## ESS and weight-tail policy

The primary effective sample size is

```text
ESS_signed = (sum w)^2 / sum(w^2).
```

Absolute-weight ESS is also reported. Ratios and weights are never clipped,
trimmed, winsorized, or resampled for acceptance. The fixed stop condition is

```text
ESS/N < 0.20  =>  DIRECT REGENERATION REQUIRED.
```

Diagnostics are reported overall, by hard flavor, and in fixed coarse `x` and
scale regions, with minimum, median, mean, maximum, p90, p95, p99, p99.9, and
coefficient of variation.

## Target-member scan declared before closure

Every installed non-central CT18NLO member is evaluated over the fresh
member-0 full-event smoke support. The fixed score is

```text
median(abs(log r)) + 0.5 p95(abs(log r)) + 0.25 p99(abs(log r)).
```

The mild target is the member closest to the lower quartile of valid scores;
ties use the lower member ID. The stress target is the strongest valid member
with predicted `ESS/N >= 0.20`. If none exists, it is the strongest
structurally valid member and is labeled an expected reuse failure. Selected
members will not be replaced after target closure is viewed.

## Fixed run configuration

- Process: neutral-current `e- p`, PYTHIA gamma/Z t-channel process 211.
- Beams: `Ee = 27.5 GeV`, `Ep = 920 GeV`.
- PDF set: CT18NLO, nominal member 0.
- Cuts: `Q2=[3.5,10000] GeV2`, `x=[1e-4,0.8]`, `y=[0.01,0.95]`.
- Selection: reconstructed DIS cuts and momentum-conservation veto after
  `pythia.next()`.
- Hard level: shower off, hadronization off.
- Full-event level: shower on, hadronization on.
- Space-shower dipole recoil: on; MPI: off.

## Seeds, shards, and stages

Seed families are disjoint by physics level, member role, stage, and shard:

| Level | Nominal | Mild A/B | Stress A/B |
| --- | --- | --- | --- |
| Hard smoke | 110001 | 120001/120002 | 130001/130002 |
| Full smoke | 210001 | 220001/220002 | 230001/230002 |
| Hard pilot | 110101 | 120101/120102 | 130101/130102 |
| Full pilot | 210101 | 220101/220102 | 230101/230102 |

Smoke statistics are 2,000 accepted events per run; target self-closure uses
two independently seeded 2,000-event direct shards. Pilot statistics are
10,000 per run; target self-closure uses two independently seeded 10,000-event
shards so every nominal/direct compatibility comparison has the same declared
event count. The preferred final study is five
independent 10,000-event shards per member. Final generation is allowed only
when smoke/pilot structural checks pass, projected additional wall time is at
most three hours, projected disk use is at most 15 GB, and no mandatory ESS
stop condition has already made reuse impossible.

## Observable and analysis policy

Observed closure variables are fixed before target comparison: `log10(x)`,
`log10(Q2)`, `y`, `log10(W2)`, scattered-electron energy and cosine, final and
charged multiplicities, visible final-state energy, scalar final-state `pT`,
leading stable-hadron `pT`, and coarse stable-particle species fractions. Hard
flavor, member ID, and nominal/target `xf` remain hidden diagnostics.

`analysis/reweighting/metrics.py` fixes all bin edges. A populated comparison
bin requires effective weighted counts of at least five on both sides.
Direct-target A versus B supplies the self-closure reference. Two hundred
bootstrap pairs use seed `7132026`. For each observable, chi-square per
effective degree of freedom, maximum populated-bin pull, Jensen-Shannon
divergence, and Wasserstein distance are compared with the direct-self
distribution. The acceptance quantile is Bonferroni-adjusted to control a 5%
familywise error rate across all observables and metrics. Undefined metrics
make shape closure `INCONCLUSIVE`; any threshold exceedance makes it `FAIL`.

## Stage A results

The full-event nominal member-0 smoke run used seed `210001` and produced 2,000
accepted events from 2,352 attempts in 8.97 seconds. It occupied 18 MiB,
corresponding to about 223 accepted events/s and 9 KiB/event. A naive 300,000
event preferred-final projection would therefore be about 22.5 generator
minutes and 2.7 GiB, within the resource ceilings. Resource limits were not the
reason for stopping.

Final run normalization metadata were successfully recorded:

| Quantity | Value |
| --- | ---: |
| PYTHIA weight sum | 5093.565602444933 |
| selected weight sum | 3398.610591368124 |
| selected sum of squared weights | 491132.3264617853 |
| `sigmaGen` | 0.0001501108976502209 mb |
| selected cross section | 100159.4023622537 pb |

The nominal self-check accepted 1,999 events and quarantined one event. For the
1,999 supported events, stored-versus-recomputed nominal `xf` agreement was:

| Statistic | Relative disagreement |
| --- | ---: |
| median | 6.811531501657305e-10 |
| p95 | 2.905651029932948e-9 |
| p99 | 5.534786223620489e-9 |
| maximum | 1.2782592478328388e-8 |
| outside `1e-6` tolerance | 0/1999 |

The invalid event was HepMC event 364, with proton-side anti-up flavor,
`x=0.000161763565`, and `GenPdfInfo::scale=1.21048019 GeV`. CT18NLO declares
`QMin=1.295 GeV`; equivalently, its `Q2` of `1.465262290382436 GeV2` is below
the grid minimum `1.677025 GeV2`. PYTHIA serialized a stored nominal
`xf=0.470827481`, but PartonSBI correctly refused an unsupported LHAPDF
recomputation. This is a support failure, not a serialization-tolerance
failure. It was not dropped silently and no extrapolation was introduced.

The nominal supported-event weight statistics were already below the reuse
gate:

| Events | ESS | ESS/N | Decision |
| ---: | ---: | ---: | --- |
| 1999 | 23.504421538498942 | 0.011758089814156549 | DIRECT REGENERATION REQUIRED |

The deterministic scan evaluated all 58 non-central CT18NLO members over the
1,999 supported tuples. It provisionally selected member 24 as mild and member
51 as stress, before direct closure:

| Target | Member | Score | Predicted ESS/N | Ratio range | Status |
| --- | ---: | ---: | ---: | --- | --- |
| mild | 24 | 0.031848035426381115 | 0.011429876515116066 | 0.9069203395–1.036147839 | reuse failure |
| stress | 51 | 0.3334122520607933 | 0.01192163495858963 | 0.8951064758–1.775217248 | reuse failure |

No scanned non-central member met `ESS/N >= 0.20`. This is driven primarily by
the unmodified PYTHIA nominal overweight tail, not by the modest mild-member
ratio distribution. No clipping or target replacement was applied.

### Partial full-event weight and phase-space diagnostics

The supported nominal self-reweighting weights retained the PYTHIA overweight
tail exactly:

| Quantity | Value |
| --- | ---: |
| events | 1999 |
| zero / negative / non-finite weights | 0 / 0 / 0 |
| sum of weights | 3397.6105911591417 |
| sum of absolute weights | 3397.6105911591417 |
| sum of squared weights | 491131.3265144065 |
| minimum | 0.9999999872174076 |
| median | 1.000000000105111 |
| mean | 1.6996551231411425 |
| maximum | 676.3540490576032 |
| p90 / p95 | 1.1097688069681098 / 2.0208302242780665 |
| p99 / p99.9 | 7.711035398648551 / 51.159360523173866 |
| coefficient of variation | 9.167760249349024 |

Flavor-level ESS diagnostics were:

| Proton flavor | Events | ESS/N | Reuse gate |
| ---: | ---: | ---: | --- |
| -5 | 2 | 1.000000 | pass |
| -4 | 166 | 0.135053 | fail |
| -3 | 90 | 0.634524 | pass |
| -2 | 465 | 0.244648 | pass |
| -1 | 117 | 0.260736 | pass |
| 1 | 173 | 0.585256 | pass |
| 2 | 759 | 0.062034 | fail |
| 3 | 75 | 0.102097 | fail |
| 4 | 150 | 0.010960 | fail |
| 5 | 2 | 1.000000 | pass |

The coarse phase-space diagnostics show where the overweight tail dominates:

| Region | Events | ESS/N | Reuse gate |
| --- | ---: | ---: | --- |
| `x < 1e-3` | 606 | 0.420718 | pass |
| `1e-3 <= x < 1e-2` | 692 | 0.009757 | fail |
| `1e-2 <= x < 1e-1` | 496 | 0.220038 | pass |
| `x >= 1e-1` | 205 | 1.000000 | pass |
| `Q < 2 GeV` | 295 | 0.210925 | pass |
| `2 <= Q < 5 GeV` | 1435 | 0.009580 | fail |
| `5 <= Q < 10 GeV` | 211 | 0.036308 | fail |
| `10 <= Q < 100 GeV` | 58 | 0.596892 | pass |

These regional passes do not override the mandatory overall reuse failure.
The single event below the PDF grid is excluded from these numerical summaries
only after being retained and counted as a typed structural failure.

## Closure and rate decisions

- Hard-process direct closure: **INCONCLUSIVE — not started after support stop**.
- Full-event mild direct closure: **INCONCLUSIVE — not started after support stop**.
- Full-event stress direct closure: **INCONCLUSIVE — not started after support stop**.
- Direct-versus-direct self-closure: **not evaluated**.
- Observable-level failures: **not evaluated**.
- Direct-target rate closure: **RATE CLOSURE NOT ESTABLISHED** because no direct
  target sample was generated.
- Pool reuse: **not allowed**.
- Phase 1B: **not allowed**.

| Physics level | Mild member 24 | Stress member 51 | Direct self-closure |
| --- | --- | --- | --- |
| hard process | INCONCLUSIVE — not run | INCONCLUSIVE — not run | not evaluated |
| full event | INCONCLUSIVE — support stop | INCONCLUSIVE — support stop | not evaluated |

All sixteen predeclared observed closure variables therefore have status
`NOT EVALUATED`; no observable was removed or declared passing. The full-event
nominal extraction itself produced zero observable-extraction failures. No
hard-process ESS exists because hard-process generation was not started after
the structural stop. No valid nominal-pool reuse domain has been established.

The exact state is:

```text
PHASE 1A BLOCKED — STRUCTURAL PDF-SUPPORT FAILURE
DIRECT REGENERATION REQUIRED BY ESS
POOL REUSE NOT AUTHORIZED
PHASE 1B NOT AUTHORIZED
```

## Validation

The post-implementation WSL validation completed with these results:

| Command | Result |
| --- | --- |
| `cargo fmt --all -- --check` | pass |
| `cargo check --workspace` | pass, warning-free |
| `cargo test --workspace` | 142 passed, 7 ignored, 0 failed |
| `cargo test --test pdf_reweighting -- --nocapture` | 27 passed, 2 installation-dependent ignored |
| `cargo test --test pdf_reweighting -- --ignored --nocapture` | 2 passed, 0 failed |
| `analysis/venv/bin/python -m pytest analysis/tests` | 24 passed |
| `ctest --test-dir physics-engine/build --output-on-failure` | 1/1 passed |
| `git diff --check` | pass |
| Phase 1A CLI help and real-fixture smoke | pass |

The ignored study directory contains only the partial full-event smoke run,
member scan, and nominal diagnostics. The required final-study decision,
closure-metric, plot, and report artifacts were not fabricated after the stop
gate; no generated output is committed.

## Scientific limitations

The ratio changes only the proton-side hard PDF. It does not reweight the
initial-state shower, hadronization, or every generator-internal PDF-dependent
choice. Accepted-event cuts can change correlations. The active process is
PYTHIA gamma/Z rather than the analytic photon-only structure-function path.
Finite Monte Carlo fluctuations, support mismatch, and existing PYTHIA
overweights remain explicit. Inclusive NC `e- p` does not provide unrestricted
flavor separation.

## Next step

Make one explicit scientific decision about the out-of-grid scale contract
(reject that generator domain, or separately validate exact PYTHIA/LHAPDF
extrapolation semantics) before restarting Phase 1A under a new study ID. Do
not begin Phase 1B.
