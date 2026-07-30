# Phase 1B-D1R revised evolution and artifact validation

## Outcome

```text
REVISED_STAGE1_DECISION = FAIL
D2_AUTHORIZATION_CANDIDATE = false
D2_AUTHORIZED = false
```

The revised contract did not qualify an evolved LHAPDF artifact for D2. This
is a completed negative scientific result, not an incomplete run. The original
D1 `FAIL` remains unchanged.

All nine mandatory anchors failed the aggregate revised Stage 1 contract.
Exact-knot serialization, independent LHAPDF log-bicubic reconstruction,
strict support, deterministic manifests, and the binding NLO photon
observables passed. Bounded refinement exceeded the fixed 600-second-per-anchor
cap, full-domain moment/leakage convergence failed, and direct APFEL-to-artifact
off-knot transport remained far outside tolerance.

## Provenance

- ADR-005 merge commit:
  `a7002d380a35ff10549905edb22a0b2ad3bf5771`
- implementation commit:
  `281675a815d6c087176d9675ae6f1535e5bb6f17`
- DrvFS atomic-publication maintenance commit:
  `de26c57066dc018b530963d25d9a547b4b650c67`
- study commit:
  `de26c57066dc018b530963d25d9a547b4b650c67`
- study ID:
  `phase1bd_d1r_refined_lhapdf_artifact_v2_20260729`
- Git dirty state: `false`
- runtime recorded by the study: `14673.085230043 s`
- measured wall time: `3:53:18`
- maximum resident set size: `588508 KiB`

The exact invocation was:

```bash
source scripts/pythia_env.sh
cargo run --release -- validate-pdf-artifact \
  --artifact-version v2 \
  --study \
  --study-id phase1bd_d1r_refined_lhapdf_artifact_v2_20260729 \
  --output outputs/phase1bd_d1r_refined_lhapdf_artifact_v2_20260729
```

The complete study output and generated LHAPDF members remain under ignored
`outputs/` and `.external/` paths. They are not committed.

## Versioned contract

```text
artifact_schema_version = partonsbi.lhapdf_artifact.v2
evolution_policy_version = apfelxx_4.8.0_nlo_vfns_extended_x_v2
grid_policy_version = threshold_subgrids_bounded_refinement_v2
cache_policy_version = immutable_sha256_atomic_publish_v2
computational_xmin = 1e-11
exported_xmin = 1e-9
continuation = exact zero on [1e-11,1e-9)
```

The base APFEL computational grid is
`(400,1e-11,3), (250,0.1,3), (180,0.6,3), (160,0.85,5)`.
The convergence grid exactly doubles the node counts to
`800, 500, 360, 320`.

The final common artifact grid has 641 x knots and 149 unique Q knots. It is
serialized as three official threshold-separated Q subgrids:

| Subgrid | Q range (GeV) | Q knots |
| --- | ---: | ---: |
| Q0 to charm | 1.295 to 1.3 | 9 |
| charm to bottom | 1.3 to 4.75 | 37 |
| bottom to Qmax | 4.75 to 100000 | 105 |

Charm and bottom boundary knots are repeated in adjacent subgrids, so the file
contains 151 Q rows across the three blocks and 149 unique Q values. Top
remains inactive.

## Deterministic refinement

The same global grid was used for every anchor. Failed interval unions were
formed across all flavors, anchors, and fixed probes before bisection.

| Iteration | x knots | unique Q knots | comparisons | failures | max abs. error | max anchor time (s) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 161 | 38 | 5,392,134 | 1,912,191 | 19.383216590591474 | 71.904846148 |
| 1 | 321 | 75 | 21,333,312 | 3,821,787 | 5.009382820491737 | 367.413528763 |
| 2 | 641 | 149 | 84,863,988 | 3,492,044 | 1374.7964848542324 | 669.137992893 |

The final trace is incomplete with the recorded reason:

```text
anchor construction/validation exceeded 600 seconds
```

The maximum errors did not converge monotonically. No further refinement,
post-hoc knot selection, tolerance change, or anchor removal was performed.

## Artifact identity and cache

All nine final manifests were byte-reproducible, had distinct SHA-256
identities, passed strict support checks, used three Q subgrids, and preserved
inactive top. Member payloads ranged from 24,412,574 to 24,447,387 bytes.

| Anchor | Artifact identity |
| --- | --- |
| center | `sha256:65abe4ff0826130cc6718572715c582ea7e1e6242b63c6b65ca65819c563ae85` |
| delta_min | `sha256:408f406fda3d65b511c0ff1d89d3e6e0b7c81c1f2514a22afc10179087430d21` |
| delta_max | `sha256:6029381bd8570fc917468730d5926180a0e1aab7c23d2e1cd642771b515f1a17` |
| sea_min | `sha256:9399ca558178db010065006dc9157f5f067f0fb06659049084f4c702cefa851a` |
| sea_max | `sha256:0d0c89a867c7fc328404e9cebd831dffc3a62cbf164eb54963405a89cb932c93` |
| corner_min_min | `sha256:ca03320d904b91d27e478ff3488820bdfd14fb94454c7b0a17743594b9637687` |
| corner_min_max | `sha256:76cb6f4241569f3e889d28fc4dcfffe1460a570cdd426ac775fd2df3d3be3806` |
| corner_max_min | `sha256:07e87d6f629949158b6e2dc034ce5ddd5c48724b8386dc13420fa19154d29ecd` |
| corner_max_max | `sha256:1604073f1a0669589a231d62c7f86ba0969b1e62ce2fd860f8c0a49dda139007` |

Checksum validation, corrupt-entry quarantine, same-hash concurrency, and
atomic publication remain tested. A transient DrvFS/OneDrive directory-rename
denial during the first clean attempt was handled by a narrow, bounded retry
of the same-directory atomic rename. No partial artifact was accepted and the
scientific identity was unchanged.

## Full-domain moments and finite-support leakage

Independent GL64 integration reports full computational-domain moments,
retained exported-support moments, and momentum below `x=1e-9` separately.

- maximum base-grid full-domain residual:
  `1.0118550574755858e-5`;
- maximum doubled-grid full-domain residual:
  `8.177903536354947e-6`;
- maximum base/doubled leakage disagreement:
  `4.501148846980385e-7`;
- evolved below-support momentum range:
  `1.5946975628899906e-8` to `6.399771093912321e-5`.

The doubled full-domain residual passes the `1e-5` bound, but the worst base
residual is slightly above it and the leakage convergence error exceeds the
fixed `1e-7` tolerance. All nine anchor-level moment closures therefore fail.
The exported-support retained momentum is not incorrectly required to equal
one.

At `Q=100000 GeV`, the center has:

```text
base full momentum     = 1.000002172414077
base retained momentum = 0.9999472491703156
base leaked momentum   = 5.492324376143998e-5
doubled full momentum  = 0.999998926956501
doubled retained       = 0.9999436143528181
doubled leaked         = 5.531260368296653e-5
```

## LHAPDF transport

Serialization and the independent interpolation audit pass:

- 9,455,391 exact-knot comparisons, zero outside tolerance;
- maximum exact-knot absolute error:
  `7.940934264346711e-23`;
- 84,863,988 independent log-bicubic comparisons, zero outside tolerance;
- maximum independent reconstruction absolute error:
  `1.4551915228366852e-11`;
- alpha_s maximum relative and absolute errors: zero.

The artifact therefore implements its tabulated bytes and LHAPDF interpolation
semantics correctly. It does not adequately represent direct APFEL evolution
between knots:

- 84,863,988 direct off-knot comparisons;
- 3,492,044 outside the unchanged PDF tolerance;
- maximum direct/APFEL-artifact absolute error:
  `1374.7964848542324`;
- 760,914 one-sided threshold comparisons;
- 32,573 threshold comparisons outside tolerance;
- maximum threshold absolute error:
  `0.44561921911935265`.

Refinement reduced some early errors but did not converge before the fixed
performance cap. This is not a serialization failure and is not repaired by
claiming exact-knot closure.

Sign-topology comparison made 44,154 component checks. Three components
mismatched across the center, `delta_min`, and `corner_min_max` anchors.
The largest direct and artifact inherited negative momenta were
`2.153157823039308e-8` and `2.1532164333931046e-8`, respectively. Values were
not clipped.

## Binding NLO photon observable

All nine anchors pass the implemented APFEL++ NLO zero-mass photon-exchange
observable closure:

- 648 F2 comparisons, zero outside tolerance;
- 648 FL comparisons, zero outside tolerance;
- maximum F2 absolute error: `2.7480122328782386e-6`;
- maximum FL absolute error: `3.450660381432158e-6`;
- minimum direct reduced photon cross section:
  `0.00100958708359842`;
- minimum artifact-backed reduced photon cross section:
  `0.0010096128177690012`;
- non-finite values: zero.

This positive observable result does not override the failed transport,
moment/leakage, or performance gates. It is not full neutral-current gamma/Z
validation.

## Raw CT18 fidelity diagnostic

Raw CT18 fidelity remains mandatory but nonbinding:

| Comparison | Values | Outside 2e-3 rule | Max abs. error |
| --- | ---: | ---: | ---: |
| raw-boundary APFEL vs public CT18 | 264,825 | 8,682 | 22.857152790773398 |
| projected vs raw-boundary APFEL | 264,825 | 0 | 0.07553967101557646 |
| projected APFEL vs public CT18 | 264,825 | 8,681 | 22.928345020358393 |

The worst public-grid discrepancy is flavor 21 near `x=1e-9` and high Q.
The zero hard-tolerance failures between projected and raw-boundary APFEL
evolution confirm that the D0R projection is not the source of the public-grid
fidelity discrepancy.

## Decision

Every anchor records these aggregate reasons:

1. anchor construction/validation exceeded 600 seconds;
2. base/doubled full-domain moment or leakage gate failed;
3. revised direct/APFEL artifact transport gate failed.

Consequently:

```text
REVISED_STAGE1_DECISION = FAIL
D2_AUTHORIZATION_CANDIDATE = false
D2_AUTHORIZED = false
```

The revised artifact is not generator-ready. No PYTHIA coupling, event
generation, sampling, dataset construction, or neural inference was added or
authorized.

## Validation

The implementation and report were checked with:

```bash
source scripts/pythia_env.sh
cargo fmt --all -- --check
cargo check --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
cargo test --test continuous_pdf_family -- --nocapture
cargo test --test continuous_pdf_family -- --ignored --nocapture
cargo test --test pdf_artifact -- --nocapture
cargo test --test pdf_artifact -- --ignored --nocapture
analysis/venv/bin/python -m pytest analysis/tests
ctest --test-dir physics-engine/build --output-on-failure
git diff --check
```

Results:

- `cargo fmt`, `cargo check`, Clippy with warnings denied, and
  `git diff --check`: pass;
- `cargo test --workspace`: 182 passed, 18 ignored, zero failed;
- `continuous_pdf_family`: 2 default tests and all 4 native ignored tests
  passed;
- `pdf_artifact`: 2 default tests and all 7 native ignored tests passed;
- Python analysis: 32 passed;
- CTest: 1/1 passed;
- CLI help: pass;
- v1 one-point smoke: operational pass with the preserved scientific `FAIL`;
- v2 projected-center one-point smoke: operational pass with scientific
  `FAIL`, independently of the complete study; and
- complete clean-provenance v2 study: process exit zero with the binding
  revised Stage 1 `FAIL`.

## Limitations

- The binding observable is photon exchange, not full gamma/Z neutral current.
- The refined finite LHAPDF grid remains inadequate for pointwise direct-APFEL
  transport under the fixed tolerance and performance budget.
- The independent base/doubled convergence contract exposes residual
  numerical sensitivity and below-support momentum; neither is hidden by
  evaluating only exported support.
- Raw CT18 comparison spans a separately evolved public artifact and remains a
  diagnostic, not a claim of implementation identity.
- No statement about PYTHIA consumer support or event-level closure follows
  from this Stage 1R study.

## Next step

Scientifically review this completed negative D1R result. Any further D1
architecture proposal requires a new ADR and explicit authorization. D2
remains unauthorized.
