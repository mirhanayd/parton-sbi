# Phase 1A: discrete LHAPDF-member hard-PDF reweighting closure

## Status

**COMPLETE — FAIL: NOMINAL-POOL REUSE REJECTED; DIRECT REGENERATION REQUIRED.**
The original Stage A smoke study remains recorded below as a historically
blocked run. An explicit no-extrapolation support decision was subsequently
made and a clean confirmation study generated exactly 2,000 accepted,
in-support events. Its nominal `ESS/N = 0.04156296108415559`, below the fixed
0.20 threshold. Mild member 24 and stress member 51 also failed the gate.
Direct closure was therefore unnecessary and was not run. Pool reuse and the
reweighting path are rejected; Phase 1B-D is authorized for planning only.

## Strict-support scientific decision

The active policy is version 1 `strict_in_grid`. LHAPDF extrapolation is not
allowed. The Rust support bridge reads each installed member's authoritative
`LHAPDF::PDF::xMin`, `xMax`, `qMin`, and `qMax` values. The reusable set domain
is their intersection; numeric bounds are not hard-coded in generic physics
code. For installed CT18NLO data version 1, all 59 members were verified to
share:

```text
x in [1e-9, 1]
Q in [1.295, 100000] GeV
```

The PYTHIA HepMC3 converter serializes proton-side `GenPdfInfo::x2` from
`Info::x2pdf()` and `GenPdfInfo::scale` from `Info::QFac()`. The generator veto
uses those exact two quantities. The scale is Q in GeV, not reconstructed DIS
Q and not Q². For managed-lhapdf evaluation, PartonSBI squares the stored scale
exactly once before calling `xfxQ2`.

Generation applies the existing DIS cuts, momentum-conservation check, and
strict support selection before accepting an event, and continues until the
requested in-support count is reached. Support vetoes remain in the attempted
event accounting and final selected-cross-section normalization. The study
domain is therefore the original DIS selection intersected with strict LHAPDF
support; no equivalence with the unrestricted generator domain is claimed.

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

For new runs, the generator writes the inclusive CSV with 17 significant
digits. Validation independently compares its `Info::weight()` column with the
selected HepMC3 `W` value using a fixed relative tolerance of `1e-5`. This
tolerance covers the earlier six-significant-digit CSV contract (the observed
legacy maximum is `4.6729e-6`); new 17-digit runs are much tighter. A
mismatch is a structural failure, and trailing CSV rows after HepMC EOF are
rejected.

HepMC `GenCrossSection` is PYTHIA's evolving cross-section estimate at the time
an event is written, not a final run normalization. Phase 1A generation now
records final `sigmaGen`, `sigmaErr`, `Info::weightSum`, selected-event weight
sums, and

```text
sigma_selected = sigmaGen * selected_weight_sum / Info::weightSum
```

in `summary.json`. These fields establish that rate-normalization inputs are
available; they do not establish direct-versus-reweighted rate closure. Until
a predeclared comparison and acceptance threshold are actually evaluated, the
status remains `RATE CLOSURE NOT ESTABLISHED`. Prefix runs selected with
`--max-events` and samples with structural invalid events are never assigned a
reweighted cross section. Older runs are shape-only.

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

`analysis/reweighting/metrics.py` fixes all bin edges and rejects any event
outside the declared range instead of silently dropping underflow or overflow.
A populated comparison bin requires effective weighted counts of at least five
on both sides. Direct-target A and B are pooled to define the null, and each
bootstrap pair is drawn independently from that pool. The predeclared policy
uses 8,191 replicates with seed `7132026`, allocates alpha `0.05` equally over
the 64 observable-metric comparisons, and uses the conservative,
non-interpolated order statistic at rank 8,186. Its finite-sample upper-tail
bound is `6/8192`, below `0.05/64`. Chi-square per effective degree of freedom,
maximum populated-bin pull, Jensen-Shannon divergence, and Wasserstein distance
are compared with this direct-self distribution. Undefined or underresolved
metrics make shape closure `INCONCLUSIVE`; any threshold exceedance makes it
`FAIL`.

## Original Stage A smoke study — blocked historical result

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

## Clean strict-support confirmation study

Study `phase1a_strict_support_confirmation_20260727` was generated from clean
implementation commit `424a987ca849554c2fbf8075792633297b1c8a46` with
`git_dirty=false` and seed `210201`. The exact shell invocation was:

```bash
cargo run --release -- generate-dis-events \
  --electron-energy 27.5 \
  --proton-energy 920 \
  --q2-min 3.5 \
  --q2-max 10000 \
  --x-min 0.0001 \
  --x-max 0.8 \
  --y-min 0.01 \
  --y-max 0.95 \
  --events 2000 \
  --seed 210201 \
  --pdf-set CT18NLO \
  --pdf-member 0 \
  --pdf-support-policy strict_in_grid \
  --parton-shower true \
  --hadronization true \
  --output outputs/phase1a_strict_support_confirmation_20260727/full/nominal
```

PYTHIA gamma/Z process 211 was active, showers and hadronization were enabled,
and MPI was disabled. No generator weights, maxima, phase-space sampling, or
target members were changed.

| Event accounting | Count |
| --- | ---: |
| attempted | 2336 |
| PYTHIA generated | 2336 |
| PYTHIA failures | 0 |
| reconstructed DIS-cut vetoes | 321 |
| momentum-conservation vetoes | 14 |
| strict PDF-support vetoes | 1 |
| accepted in-support | 2000 |

The one support veto was `below_q_minimum`; it was counted and replaced by
continued generation. The accepted HepMC3 pool streamed as exactly 2,000
events, all with an unambiguous proton-side entry and `InSupport` outcome.
There were zero structural failures, missing entries, ambiguous entries,
non-finite ratios, zero ratios, or observable extraction failures. All 58
non-central members were scanned with valid-ratio fraction 1.0.

Final normalization metadata were:

| Quantity | Value |
| --- | ---: |
| PYTHIA weight sum | 4882.624220548377 |
| selected weight sum | 3275.821378678103 |
| selected sum of squared weights | 129093.37320307645 |
| selected negative weights | 0 |
| `sigmaGen` | 0.00014710181824581162 mb |
| selected cross section | 98692.68231294063 pb |

Stored-versus-recomputed nominal `xf` agreement retained the `1e-6` tolerance:

| Statistic | Relative disagreement |
| --- | ---: |
| median | 6.744524631535534e-10 |
| p95 | 2.63247814752144e-9 |
| p99 | 5.459636533694609e-9 |
| maximum | 8.66065223052482e-9 |
| outside tolerance | 0/2000 |

The unchanged target-selection rule again chose mild member 24 and stress
member 51:

| Role | Member | Score | ESS | ESS/N | Ratio range |
| --- | ---: | ---: | ---: | ---: | --- |
| nominal | 0 | — | 83.12592216831118 | 0.04156296108415559 | self ratio |
| mild | 24 | 0.031459687899194975 | 83.16530005303699 | 0.041582650026518495 | 0.9019719336–1.055561697 |
| stress | 51 | 0.34155264832892285 | 85.66916660756044 | 0.04283458330378022 | 0.8953801796–1.741981285 |

All three values are below `ESS/N = 0.20`. The nominal self-ratio distribution
is numerically consistent with one; the low ESS comes from the unmodified
PYTHIA event-weight tail, not a PDF-ratio failure. No clipping, unweighting,
winsorization, resampling, or post-hoc target replacement was applied.

## Closure and rate decisions

- Hard-process direct closure: **not run; unnecessary after the ESS gate rejected reuse**.
- Full-event mild direct closure: **not run; unnecessary after the ESS gate rejected reuse**.
- Full-event stress direct closure: **not run; unnecessary after the ESS gate rejected reuse**.
- Direct-versus-direct self-closure: **not run**.
- Observable-level closure: **not run and not claimed**.
- Direct-target rate closure: **not run and not claimed**.
- Pool reuse: **rejected**.
- Reweighting path: **rejected for pool production**.
- Direct regeneration: **required per PDF parameter point**.
- Phase 1B-D: **planning permitted; implementation not started**.

| Physics level | Mild member 24 | Stress member 51 | Direct self-closure |
| --- | --- | --- | --- |
| hard process | not run — ESS stop | not run — ESS stop | not run |
| full event | not run — ESS stop | not run — ESS stop | not run |

All sixteen predeclared observed closure variables therefore have status
`NOT EVALUATED`; no observable was removed or declared passing. This does not
make the Phase 1A decision inconclusive: the predeclared ESS gate is sufficient
to reject pool reuse before direct closure. The full-event nominal extraction
itself produced zero observable-extraction failures.

The exact state is:

```text
FAIL — NOMINAL-POOL REUSE REJECTED
DIRECT REGENERATION REQUIRED
POOL_REUSE_ALLOWED = false
REWEIGHTING_PATH_ALLOWED = false
DIRECT_REGENERATION_REQUIRED = true
PHASE1A_COMPLETE = true
PHASE1B-D_PLANNING_PERMISSION = true
```

## Post-study infrastructure audit

The original blocked observation remains historical evidence. Before the clean
restart, a source-level audit and strict-support implementation hardened the
scientific contract:

- the streaming validator now retains only compact scalar accumulator state,
  cross-checks CSV/HepMC weights, and rejects CSV/HepMC cardinality mismatch;
- rate-normalization metadata can no longer be reported as rate closure, and a
  partial or structurally invalid nominal sample cannot produce a reweighted
  cross section;
- member scans treat a finite zero target density as a valid zero weight while
  withholding the logarithmic deformation score for that member;
- new generator metadata records beam IDs, MPI state, Git commit, and dirty
  state; direct-run compatibility requires all four to be present and equal;
- fixed-bin analysis rejects out-of-range values and uses a resolved pooled-null
  bootstrap policy; and
- a single closure case can never grant pool reuse or Phase 1B permission;
- authoritative per-member LHAPDF support is typed, intersected, serialized,
  and revalidated before generation or scanning; and
- the aggregate ESS decision can finalize a negative Phase 1A result but can
  never grant reuse after an ESS pass without independent direct closure.

The smoke sample predates the new `git_dirty` field and was generated while the
Phase 1A implementation was uncommitted (`repository_dirty=true` in the member
scan manifest). This does not change the below-grid support observation, but it
prevents that sample from serving as a future direct-run compatibility
reference. The clean confirmation run replaces it as the decision reference.

The exact verbatim Stage A shell commands and exit codes were not retained in a
committed manifest. Configuration, seed, path, versions, counts, timestamp,
runtime, and numerical results are retained, but the missing command transcript
is a reproducibility limitation. No command is reconstructed and presented as
verbatim after the fact.

## Validation

The post-implementation WSL validation completed with these results:

| Command | Result |
| --- | --- |
| `cargo fmt --all -- --check` | pass |
| `cargo check --workspace` | pass, warning-free |
| `cargo test --workspace` | 153 passed, 7 ignored, 0 failed |
| `cargo test --test pdf_reweighting -- --nocapture` | 38 passed, 2 installation-dependent ignored |
| `cargo test --test pdf_reweighting -- --ignored --nocapture` | 2 passed, 0 failed |
| `cargo clippy --workspace --all-targets -- -D warnings` | pass, warning-free |
| `analysis/venv/bin/python -m pytest analysis/tests` | 32 passed |
| `ctest --test-dir physics-engine/build --output-on-failure` | 1/1 passed |
| `git diff --check` | pass |
| Clean 2,000-event generator, streaming-parser self-check, and 58-member scan | pass |

Raw event pools, scans, and diagnostics remain under ignored `outputs/` and are
not committed. The compact machine-readable decision is committed as
`docs/phase1a_strict_support_decision.json`. No direct-closure metrics or plots
were fabricated after the ESS stop.

## Scientific limitations

The ratio changes only the proton-side hard PDF. It does not reweight the
initial-state shower, hadronization, or every generator-internal PDF-dependent
choice. Accepted-event cuts can change correlations. The active process is
PYTHIA gamma/Z rather than the analytic photon-only structure-function path.
Finite Monte Carlo fluctuations, support mismatch, and existing PYTHIA
overweights remain explicit. Inclusive NC `e- p` does not provide unrestricted
flavor separation.

## Next step

Write and review the Phase 1B-D scientific design for a continuous,
sum-rule-preserving PDF family with direct event regeneration at each parameter
point. Do not implement Phase 1B-D or revive nominal-pool reuse in this task.
