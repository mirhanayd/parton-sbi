# ADR-008: Signed-generator coupling terminal planning decision

- Status: Proposed
- Date: 2026-08-01
- Phase: 1B-D1D-B
- Decision artifact: `docs/phase1bd_d1d_terminal_decision.json`
- Schema: `partonsbi.phase1bd.d1d.terminal-decision.v3`
- Artifact SHA-256: `d310b452a5a80d5bd59a91af2787b795dba7da17eb5d684990d9b718373376a7`

## Immutable precedence and fixed scope

This correction does not change the merged scientific record:

- `D1C_FINAL_DECISION = FAIL`;
- `MINIMAL_PUBLIC_READER_PATCH = INSUFFICIENT`;
- `PROVENANCE_SLICE_V1_DECISION = FAIL`;
- `PROVENANCE_SLICE_V1_STATUS = REJECTED_DIAGNOSTIC`;
- `D1D_A_FINAL_DECISION = FAIL`;
- `D1D_A_FAILED_GATE = provenance_evidence_integrity`;
- `ARCHITECTURE_COMPARISON_READY = false`; and
- `D2_AUTHORIZED = false`.

The fixed contract remains the signed binary64 `x*f` interface for
`ct18nlo_two_parameter_boundary_v2`, the declared theta box, strict support
without extrapolation, shape-only fixed-N inference over event sets, and
consistent hard-process, ISR/backward-evolution, and beam-remnant treatment.

## Epistemic score contract

The v3 record separates five meanings:

- `SUPPORTED`: direct primary or immutable repository evidence establishes the
  criterion for the stated scope.
- `SUPPORTED_WITH_QUALIFICATION`: evidence establishes only a stated subset.
- `NOT_SUPPORTED`: evidence affirmatively establishes incompatibility or
  failure for the stated scope. Missing or unreviewed evidence is not failure.
- `PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE`: the bounded review did not find enough
  primary evidence to decide. This is not affirmative incompatibility.
- `NOT_APPLICABLE`: the criterion does not apply to the architecture.

Every cell records a precise claim, evidence scope, rationale, source IDs,
source-supported claim keys, source-specific claim bindings, epistemic basis,
and any explicit disproportionate-cost evidence. Every claim key must be
bound to a claim in the exact cited source rather than the union of all cited
sources. The validator rejects epistemic relabeling.

The validator also compares the complete serialized source-identity registry
with the repository-owned `build_sources()` contract. A changed content hash,
immutable identifier, URL, version, claim scope, repository commit, source
path, Git blob, pinned-file set, or pinned-file hash fails even when the
replacement value is syntactically well formed. This identity binding does not
replace independent recomputation of candidate aggregation, route states,
rule fields, the decision, or the operational policy.

## Evidence-derived decision

The proposed decision remains **INCONCLUSIVE**, now derived from the candidate
matrices rather than serialized assumptions.

| Rule input | Recomputed value | Derivation |
|---|:---:|---|
| `mandatory_d1d_a_gate_passed` | `false` | Immutable D1D-A `FAIL` |
| `architecture_comparison_ready` | `false` | Immutable merged evidence |
| `potentially_coherent_route_remains` | `true` | Architecture C contains evidence-gap possible routes |
| `no_current_architecture_has_coherent_bounded_path` | `false` | Logical complement of the A/B/C route states |
| `primary_or_mathematical_evidence_insufficient` | `true` | Unresolved critical criteria in Sherpa and Herwig |
| `disproportionate_cost_supported_for_all_routes` | `false` | Cost, reproducibility, and boundedness are not affirmatively established for every route |

`derive_decision()` maps this combination to `INCONCLUSIVE`. The current
operational policy is:

```text
PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION
```

This is an interim pause supported by the failed readiness gate. It is not the
terminal decision `DO_NOT_AUTHORIZE_FURTHER_GENERATOR_PROTOTYPE`. A terminal
stop could be selected only if all A/B/C routes were recomputed as not
supported and explicit all-route maintenance, reproducibility, and bounded-
falsifiability evidence established disproportionate cost.

## Architecture route states

### A. Repository-owned PYTHIA fork or patch

Route state: `COHERENT_BOUNDED_PATH_NOT_SUPPORTED`.

The public-reader change remains insufficient. A wider fork remains largely
undecided rather than disproven, but the failed provenance-evidence gate
affirmatively prevents defining a bounded complete-consumer prototype now.
Bypass, downstream redesign, versioned maintenance, and redistribution remain
separate questions. No fork or patch is authorized.

### B. Signed-weight generator architecture

Route state: `COHERENT_BOUNDED_PATH_NOT_SUPPORTED`.

Primary evidence supports negative weights on complete MC@NLO/LHEF histories.
It does not turn those weights into signed internal PDF probabilities or signed
Sudakov kernels. A final weight affirmatively cannot repair internal PDF
ratios, categorical choices, remnants, maxima, vetoes, or rejection sampling
performed before the complete event exists. A distinct signed-kernel
formulation remains an unavailable mathematical input, not an implementation
authorization.

### C. Alternative generator or transport interface

Route state: `COHERENT_BOUNDED_PATH_POSSIBLE_WITH_EVIDENCE_GAPS`.

Candidate route states are computed from ten critical criteria:

| Candidate | Route state | Critical U | Critical Q | Critical N | Critical S |
|---|---|---:|---:|---:|---:|
| Sherpa external-PDF/full-DIS stack | `COHERENT_BOUNDED_PATH_POSSIBLE_WITH_EVIDENCE_GAPS` | 6 | 4 | 0 | 0 |
| Herwig PDF/shower stack | `COHERENT_BOUNDED_PATH_POSSIBLE_WITH_EVIDENCE_GAPS` | 6 | 4 | 0 | 0 |
| Les Houches signed hard-event transport | `COHERENT_BOUNDED_PATH_NOT_SUPPORTED` | 0 | 2 | 8 | 0 |

Sherpa and Herwig have no affirmative critical incompatibility in this bounded
desk review, but neither has complete signed scalar, rate, denominator,
selection, envelope, or bounded-prototype evidence. They are possible only in
the epistemic sense required by the rule; they are not selected or authorized.

LHEF is a complete-event transport boundary with an `XWGTUP` event-weight
field. MC@NLO separately establishes negative complete-event weights. That
qualified combination does not establish signed internal PDF or shower
semantics. LHEF affirmatively delegates or omits the provider, ISR, remnant,
categorical, denominator, and sampling components required of a complete
generator route.

Architecture C is aggregated from the candidate matrices, never copied as a
manual tuple. `NOT_SUPPORTED` requires every applicable candidate to fail;
`SUPPORTED` requires every applicable candidate to support; any unresolved
candidate preserves `PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE`; remaining mixed
evidence becomes `SUPPORTED_WITH_QUALIFICATION`; all-`NOT_APPLICABLE` remains
`NOT_APPLICABLE`.

### D. Operational pause

Assessment: `INTERIM_PAUSE_SUPPORTED_BY_FAILED_READINESS_GATE`.

Architecture D is not a completed terminal-stop selection while the derived
decision is `INCONCLUSIVE`. The pause prevents unauthorized work while leaving
the evidence-gap routes explicit. Reopen conditions are evidence requirements,
not authorization.

## Sherpa and Herwig evidence discipline

The pinned Sherpa HERA configuration establishes lepton-proton beams, an EW-
order-two DIS process, PDF selection, shower configuration, and MC@NLO mode.
It does not separately prove the required complete gamma, Z, gamma-Z
interference, charge-sign, and convention contract. Therefore:

- Sherpa `hard_process_coverage = SUPPORTED_WITH_QUALIFICATION`; and
- Sherpa `full_neutral_current_gamma_z_compatibility = PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE`.

Herwig is treated equivalently: primary papers establish general lepton-hadron
hard processes, backward evolution, remnants, and release software, but not
the fixed complete signed-PDF or neutral-current component contract.

Negative MC@NLO complete-event weights support only event-weight semantics.
They are not used as evidence for signed internal PDF rates or Sudakov kernels.

The Herwig 7.0 source scope is limited to `mcatnlo_matching_framework` and
`subtractive_nlo_matching_integration`; negative complete-event weights are
bound only to the MC@NLO paper. The LHEF source scope is limited to
`xwgtup_event_weight_field`; negative-weight meaning is a qualified
cross-source conclusion, not a claim made by the LHEF standard alone.

## Pinned external evidence

All retrievals occurred on `2026-08-01` UTC. Mutable `master` identities are
excluded from supporting evidence.

The independent integrity audit reproduced every load-bearing external byte
representation and hash. Those external bytes are not vendored or archived in
this repository. Their hashes identify the reviewed byte representations, but
future availability still depends on the official hosts. This is not currently
a blocker because all load-bearing identities reproduced; a URL plus hash is
not represented as a guarantee of future availability.

| Source | Exact identity | Content SHA-256 |
|---|---|---|
| Sherpa external-PDF documentation | Manual 3.0.1, versioned URL | `7b8936eac5ee66fa569fc64a0b027e692ad86de9f5979638373267ebf703fbaa` |
| Sherpa ISR documentation | Manual 3.0.1, versioned URL | `e5b1f8d7c38ec2371333672c90bd80710a352d0806b032488bfecbbe4a744110` |
| Sherpa combined manual | Manual 3.0.1, versioned URL | `7f78e097a43d8c27f9b082a5e1919701aac955c7bf7db944e1e1b03709addcf5` |
| Sherpa official source | commit `82ede7a88616eec1ca2ebf6ba3b7dde53fcb3f2c` | Per-file hashes below |
| Sherpa HERA YAML | blob `dfa23751d6bd6e28f202fe915ed666edf13e2aad` at the pinned commit | `2ee1d02489b061009c901bb5c30663d0d39bdb5c045c5041a6f67bd622bb98b1` |
| Sherpa 3 paper | arXiv `2410.22148v1` | `5adefda595551caec2bb33f48eaaf6b4c67d343e398c7a5dec822242a7ac0447` |
| Herwig++ manual | arXiv `0803.0883v3` | `ea5fa4e0cd538b9eeb38ffb3ac2d825a5cae3780c33f1d8d6b22bafc4e921d93` |
| Herwig 7.0 paper | arXiv `1512.01178v1` | `fe7512b2939da056fea4fb34ad7fa8a6a425d4a38b5d04fe6fcc360d4704deb3` |
| Herwig 7.3 paper | arXiv `2312.05175v2` | `028b0658f35ebac3dd24d96a6247653bb45725bfd9de53baa07151787fec7f9b` |
| LHEF standard | arXiv `hep-ph/0609017v1` | `9509b8727dad8cecc1c467d91b25af540e663b2a744c4377f65618b523659330` |
| MC@NLO paper | arXiv `hep-ph/0204244v2` | `a0b4c198461c324f28c5adb20f663982f4b89684f653beb07d746841c6975c81` |

Pinned Sherpa commit files include:

- `PDF/Main/PDF_Base.H`: `a2e16eb17f1e19b9390140d0bc688fc1da175a3a7b460a68e801f39d7f30db9a`;
- `PDF/Main/ISR_Handler.C`: `1933b82a128a79e43ecfbcc1661ff008d279804b29cb4a51603ccfb5ddfcd38a`;
- `Examples/Jets_in_DIS/HERA/Sherpa.yaml`: `2ee1d02489b061009c901bb5c30663d0d39bdb5c045c5041a6f67bd622bb98b1`;
- `CMakeLists.txt`: `b82d719019060ba990583253bf422141365a716dcc562523e57d6912c65f3292`;
- `LICENCE`: `55a4562db3fe9920e7a2ad7405f00bb2207f53c5d51faf696361f9b33029749a`; and
- `COPYING`: `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`.

## Aggregate twenty-criterion matrix

Legend: S = `SUPPORTED`; Q = `SUPPORTED_WITH_QUALIFICATION`; N =
`NOT_SUPPORTED`; U = `PRIMARY_SOURCE_EVIDENCE_UNAVAILABLE`; A =
`NOT_APPLICABLE`.

| # | Criterion | A | B | C | D |
|---:|---|:---:|:---:|:---:|:---:|
| 1 | Signed scalar preservation | U | N | U | A |
| 2 | Nonnegative probability/rate validity | U | N | U | A |
| 3 | Hard-process coverage | U | Q | Q | A |
| 4 | ISR/Sudakov coverage | U | N | Q | A |
| 5 | Beam-remnant coverage | U | N | Q | A |
| 6 | Flavor/categorical selection | U | N | U | A |
| 7 | Denominator/ratio validity | U | N | U | A |
| 8 | Maximum/envelope/rejection semantics | U | N | U | A |
| 9 | Event-weight semantics | U | Q | Q | A |
| 10 | Strict support/no extrapolation | Q | U | U | A |
| 11 | alpha_s consistency | U | U | Q | A |
| 12 | Full neutral-current gamma/Z compatibility | U | U | U | A |
| 13 | Deterministic identity/provenance | Q | Q | Q | S |
| 14 | Thread/process safety | U | U | U | A |
| 15 | Build/deployment reproducibility | Q | U | Q | A |
| 16 | License/redistribution | U | A | Q | A |
| 17 | Upstream maintenance burden | U | U | U | Q |
| 18 | Bounded prototype falsifiability | N | N | U | A |
| 19 | Amortized set-inference compatibility | Q | Q | Q | Q |
| 20 | Authorization-hierarchy compatibility | N | N | N | S |

Complete candidate-level matrices and criterion-specific rationales are in the
v2 JSON artifact.

## Unresolved evidence and reopen conditions

The record remains blocked by the missing complete consumer graph, missing
signed-kernel/Sudakov construction, incomplete signed semantics for Sherpa and
Herwig, incomplete neutral-current component validation, and unbounded
maintenance/concurrency/support evidence.

Reconsideration requires independently reviewed new evidence:

1. reviewed signed-kernel and signed-Sudakov mathematics;
2. a pinned primary-source generator interface proving signed scalar, rate,
   ISR, remnant, and event-weight semantics;
3. an independently validated complete consumer/dataflow graph; or
4. a separately reviewed and approved change to the PDF-family or inference
   contract.

A reopen condition is not an authorization.

## Consequences

All ten implementation and prototype authorization flags remain false. Issue
#42 remains open for review. Issue #10 remains blocked, and D2 remains
unauthorized. No later phase begins here.

The next step is
`SCIENTIFIC_REVIEW_OF_EVIDENCE_DERIVED_D1D_B_DECISION`.
