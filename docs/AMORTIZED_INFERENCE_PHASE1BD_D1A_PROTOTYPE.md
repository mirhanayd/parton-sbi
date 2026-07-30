# Phase 1B-D1A transport-comparison prototype

## Scope and authorization boundary

This report finalizes the bounded evaluator comparison authorized by issue
#35 and ADR-006. It compares a direct APFEL-backed reference with one fixed,
repository-owned transport representation. It does not reinterpret the
historical D1 or D1R failures, select a production evaluator, couple a PDF to
PYTHIA, generate events, or authorize D2.

The outcome is:

```text
PROTOTYPE_DECISION = INCONCLUSIVE
DIRECT_CANDIDATE_STATUS = INCONCLUSIVE
CUSTOM_CANDIDATE_STATUS = FAIL
D2_AUTHORIZED = false
```

## Evaluators

The direct candidate is an immutable APFEL++ evolution configuration exposed
through deterministic batch evaluation. Native access is serialized because
APFEL++ reentrancy has not been established. Each measured call reconstructs
and evaluates an APFEL batch; no persistent scalar PYTHIA adapter was built.

The custom candidate is the content-addressed
`threshold_piecewise_logx_logq_bilinear_prototype_v1` representation. It has
six fixed x knots, six fixed Q knots, explicit charm and bottom threshold
knots, strict support, no extrapolation, and bilinear interpolation in
`(ln(x), ln(Q))`. It does not use LHAPDF log-bicubic interpolation. The grid
was fixed before the study and was not refined after observing its errors.

## Study provenance

- Clean implementation commit:
  `6cdd617cae88dc7b4d79a2388f1822076a8008bd`
- Preparation schema:
  `partonsbi.d1a.transport-prototype.preparation.v2`
- Study schema: `partonsbi.d1a.transport-prototype.study.v3`
- Study policy: `d1a_three_anchor_bounded_study_v1`
- Evidence serialization policy:
  `serde_json_float_roundtrip_pretty_v1`
- Build-recorded dirty state: `false`
- Fixed runtime limit: 1,800 seconds
- Fixed generated-output limit: 2,147,483,648 bytes (2 GiB)
- Generated output: 38,625 bytes
- No event generation; `pythia.next()` remained forbidden.

The external end-to-end measurement, including the release build, was 76.39
seconds wall time with maximum RSS 782,836 KiB and exit status 0. The study
process separately reported a Linux `VmHWM` peak of 27,836 KiB. These are
different measurement scopes and must not be compared as if they were the
same process interval.

The three predeclared anchors were:

| Anchor | `delta_v` | `lambda_sea` |
|---|---:|---:|
| `center` | 0.0 | 0.0 |
| `delta_min` | -0.2 | 0.0 |
| `corner_min_max` | -0.2 | 0.25 |

## Accuracy and threshold evidence

The binding comparison tolerance remained relative error at most `1e-5` or
absolute error at most `1e-9`.

| Anchor | Knot failures / count | Knot max abs / rel | Off-knot failures / count | Off-knot max abs | Off-knot max rel | Threshold failures / count | Threshold max abs |
|---|---:|---:|---:|---:|---:|---:|---:|
| `center` | 0 / 396 | 0 / 0 | 245 / 275 | 6573.413343675164 | 270.94250759930225 | 8 / 264 | 5.724478086222007e-6 |
| `delta_min` | 0 / 396 | 0 / 0 | 245 / 275 | 7588.295758877917 | 14841.190788935332 | 10 / 264 | 6.582971479929256e-6 |
| `corner_min_max` | 0 / 396 | 0 / 0 | 245 / 275 | 7610.1990946808055 | 347.7008628954715 | 8 / 264 | 6.82762225778788e-6 |

The maximum threshold relative error is reported as the finite binary64
maximum (`1.7976931348623157e308`) because the comparison includes near-zero
reference values. The absolute criterion still gives a binding and explicit
failure count.

Exact knot reproduction passed after the binary64 JSON correction, but every
anchor failed off-knot and one-sided threshold closure. The current fixed 6x6
bilinear representation is therefore rejected. Its high scalar throughput
cannot compensate for failed binding accuracy.

## Reload and identity audit

Every custom artifact passed all reload gates:

| Anchor | Stored identity | Binary64 fields | Canonical bytes | First mismatch |
|---|---|---|---|---|
| `center` | PASSED | PASSED | PASSED | null |
| `delta_min` | PASSED | PASSED | PASSED | null |
| `corner_min_max` | PASSED | PASSED | PASSED | null |

The evaluator-policy identity is common to the direct evaluator definition,
while the three anchor-transport identities are distinct and include the
parameter-point identity. Custom identities and their recomputed identities
also match. Deterministic repeat and strict support passed for both evaluated
paths.

## Performance evidence

| Anchor | Direct batch-rebuild effective calls/s | Custom scalar calls/s |
|---|---:|---:|
| `center` | 153.9825939677198 | 16971157.517798502 |
| `delta_min` | 150.95530983696736 | 16879574.36465282 |
| `corner_min_max` | 152.38405766987628 | 15539001.339461915 |

`direct_batch_rebuild_effective_calls_per_second` includes APFEL batch
reconstruction. It is not persistent scalar PYTHIA-adapter throughput. The
direct scalar adapter benchmark, direct thread safety, direct process
isolation, custom thread safety, and custom process isolation are all
`NOT_MEASURED`.

## Query-envelope limitation

The deterministic hard-process envelope is predeclared from the beam and DIS
configuration and passed strict-support checks. It is not an all-consumer
PYTHIA envelope. The following consumers remain unresolved:

- `initial_state_shower`
- `beam_remnants`

No generated events were used to define the envelope. All-consumer envelope
closure is therefore `false`.

## Candidate gates

| Gate | Direct APFEL | Fixed custom interpolator |
|---|---|---|
| Accuracy | NOT_MEASURED | FAILED |
| Identity | PASSED | PASSED |
| Reload | NOT_MEASURED | PASSED |
| Threshold behavior | PASSED | FAILED |
| Strict support | PASSED | PASSED |
| Deterministic repeat | PASSED | PASSED |
| Persistent scalar throughput | NOT_MEASURED | PASSED |
| Thread safety | NOT_MEASURED | NOT_MEASURED |
| Process isolation | NOT_MEASURED | NOT_MEASURED |
| Candidate status | **INCONCLUSIVE** | **FAIL** |

Known custom failures are not hidden by the incomplete query envelope. The
direct candidate remains unselected because its persistent scalar accuracy,
throughput, reload/lifetime behavior, thread safety, process isolation, and
complete consumer envelope were not established.

## Decision and limitations

The final result is **INCONCLUSIVE**. The fixed custom representation is
rejected; direct APFEL transport is neither accepted nor rejected. The D1 and
D1R negative results remain unchanged, and successful photon-only observable
checks from those phases are not reinterpreted as full generator closure.

A separate future decision would be required to test a persistent direct
APFEL-backed scalar adapter and instrument all enabled PYTHIA PDF consumers.
This report does not authorize that implementation, production coupling,
events, datasets, neural inference, or D2.
