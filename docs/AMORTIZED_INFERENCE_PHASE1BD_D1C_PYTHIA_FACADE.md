# Phase 1B-D1C-B PYTHIA PDF facade admission audit

## Result and scope

```text
D1C_STAGE = D1C_B_FACADE_ADMISSION_BLOCKED
FACADE_COMPATIBILITY = INCOMPATIBLE_NONVIRTUAL_POSITIVITY_CLIPPING
FACADE_PUBLISHED = false
PYTHIA_INITIALIZED = false
PYTHIA_NEXT_EXECUTED = false
ATTEMPTED_EVENTS = 0
SUCCESSFUL_EVENTS = 0
SAVED_EVENTS = 0
RUNTIME_CONSUMER_ATTRIBUTION_COMPLETE = false
CONSUMER_ENVELOPE_RESULT_AVAILABLE = false
SCIENTIFIC_STUDY_RESULT_AVAILABLE = false
D2_AUTHORIZED = false
```

D1C-B audited the exact installed PYTHIA 8.312 extension boundary before
publishing a persistent-APFEL facade. The public boundary cannot preserve the
accepted signed binary64 contract. The implementation therefore stops fail
closed before creating a facade, facade lease, Pythia object, output
directory, or queryable transport identity. This is a negative compatibility
result, not the final D1C scientific decision.

## Installed primary-source audit

The installed headers are under
`.external/pythia-8.3.12/include/Pythia8`; the matching source is under
`.external/src/releases-pythia8312`. The authoritative findings are:

- `include/Pythia8/PartonDistributions.h:83-87` declares `PDF::xf`,
  `PDF::xfVal`, and `PDF::xfSea` without `virtual`.
- `src/PartonDistributions.cc:122-379` implements those methods using
  `max(0., value)` throughout; `xfVal` also uses absolute values in some beam
  cases.
- `include/Pythia8/PartonDistributions.h:195` exposes only the protected
  `virtual void xfUpdate(int,double,double)` hook for ordinary flavor values.
  A subclass may store a signed value, but it cannot override the public
  reader that clips it.
- `include/Pythia8/BeamParticle.h:219-267` calls `xf`, `xfVal`, `xfSea`,
  `xfMax`, `xfSame`, `insideBounds`, and `alphaS` through `PDFPtr`.
- `include/Pythia8/SharedPointers.h:50-52` defines `PDFPtr` as
  `shared_ptr<PDF>`. Static dispatch therefore selects the non-virtual base
  readers even when the object is a subclass.
- `include/Pythia8/Pythia.h:111-122` and `src/BeamSetup.cc:21-92` install up
  to sixteen ordinary, hard, pomeron, photon, unresolved, and VMD pointers.
  Ordinary and hard pointers default to the supplied objects, but the signed
  reader limitation remains.
- `src/BeamSetup.cc:1021-1068` may create separate hard PDFs when
  `PDF:useHard` or nuclear-hard settings are enabled.
- `src/BeamSetup.cc:1558-1568` has an internal complete pointer map, but it is
  not exposed through `Pythia`. Public `Pythia::getPDFPtr` delegates to the PDF
  factory, not to this map. Complete post-init pointer identity is therefore
  unresolved through the installed public API.

## Exact method matrix

All scales named `Q2` below are in GeV2. The prospective persistent evaluator
would take `sqrt(Q2)` exactly once and pass Q in GeV to APFEL.

| Method | Exact installed signature | Base behavior and sign effect | Candidate disposition | Synthetic coverage |
|---|---|---|---|---|
| `xf` | `double xf(int id, double x, double Q2)` | Non-virtual cached reader; applies `max(0, ...)` | Binding blocker | Native signed probe proves `-1` becomes `+0` through `PDFPtr` |
| `xfVal` | `double xfVal(int id, double x, double Q2)` | Non-virtual; derives valence, applies `max`, and sometimes `abs` | Binding blocker | Native probe proves `-1.5` becomes `+0` |
| `xfSea` | `double xfSea(int id, double x, double Q2)` | Non-virtual; derives sea and applies `max` | Binding blocker | Native probe proves `-0.5` becomes `+0` |
| `xfUpdate` | `virtual void xfUpdate(int id, double x, double Q2) = 0` | Protected cache-fill hook | Insufficient: signed storage is later clipped | Probe subclass implements it |
| `insideBounds` | `virtual bool insideBounds(double x, double Q2)` | Default `true` | Would require strict support override | Matrix coverage only; facade not published |
| `alphaS` | `virtual double alphaS(double Q2)` | Default `1` | Would route `sqrt(Q2)` once to persistent `AlphaQCD` | Matrix coverage only |
| `mQuarkPDF` | `virtual double mQuarkPDF(int id)` | Default `-1` | Would expose accepted thresholds/masses | Matrix coverage only |
| `xfMax` | `virtual double xfMax(int id, double x, double Q2)` | Default calls clipping `xf` | Override technically possible but cannot repair ordinary readers | Matrix coverage only |
| `xfSame` | `virtual double xfSame(int id, double x, double Q2)` | Default calls clipping `xf` | Override technically possible but cannot repair ordinary readers | Matrix coverage only |
| `setExtrapolate` | `virtual void setExtrapolate(bool)` | Default no-op | Would reject extrapolation | Matrix coverage only |
| `xfFlux` | `virtual double xfFlux(int,double,double)` | Default zero | Photon flux disabled | Disabled-path classification |
| `xfApprox` | `virtual double xfApprox(int,double,double)` | Default zero | Resolved photon disabled | Disabled-path classification |
| `xfGamma` | `virtual double xfGamma(int,double,double)` | Default zero | Resolved photon disabled | Disabled-path classification |
| `xfIntegratedTotal` | `virtual double xfIntegratedTotal(double)` | Default zero | MPI/photon path disabled | Disabled-path classification |

Hiding `xf`, `xfVal`, or `xfSea` in a subclass is not an override. Calls made
through `shared_ptr<PDF>` continue to execute the base implementation. Neither
clipping, absolute-value replacement, returning zero on failure, nor patching
around the result is scientifically permitted.

## Signed-value evidence

`src/pythia_pdf_contract_audit.cpp` supplies a deterministic subclass whose
protected cached fields contain signed values. It compares direct protected
raw values with the public result reached through `PDFPtr`:

| Quantity | Raw bits/value | Public base result |
|---|---:|---:|
| inclusive gluon | `-1.0` | `+0.0` |
| up valence | `-1.5` | `+0.0` |
| up sea | `-0.5` | `+0.0` |

The integration test also evaluates the predeclared accepted APFEL gluon
probe `(flavor=21, x=0.999, Q=Qmin)` and verifies that it is negative before
the PYTHIA boundary. No negative point was searched for adaptively.

## Admission, identity, and lifetime consequences

The source-compatible facade candidate is identified by
`persistent_apfel_signed_pythia_facade_candidate_v1`; its policy hash includes
PYTHIA 8.312, the complete audited method list, Q2-to-Q policy, valence/sea
formula policy, sign policy, provenance schema, pointer policy, mutex policy,
and the persistent evaluator-policy identity. Runtime counters, timings,
queries, and output paths are excluded.

No `facade_transport_identity` is published because no facade can satisfy the
signed boundary. Consequently no persistent-context lease is acquired. The
required prospective order remains Pythia destruction, facade destruction,
lease release, then persistent-context destruction, but this task does not
claim that order was exercised. Failed admission exposes no native APFEL
handle, C++ pointer, partial Pythia harness, or usable facade.

## Scale, flavor, valence/sea, and alpha_s contract

Had the public boundary been compatible, all `Q2` inputs would require finite
`Q2 > 0`, deterministic binary64 square root exactly once, strict Q support,
and recording of input-Q2 and derived-Q bits. Inclusive flavors would be
limited to `-5..-1`, `1..5`, and `21`; top would be typed inactive and other
IDs typed unsupported. Valence would be signed `x(q-qbar)` and sea signed
`x*qbar`, with no positivity repair. `alphaS(Q2)` would route the derived Q to
the same persistent `AlphaQCD` policy. These rules are recorded but are not
claimed as executed facade behavior.

## Pointer classification and zero-event initialization

The required pre-init policy remains: lepton A uses its pointlike lepton
provider; proton B and hard-B must be the same instrumented facade;
`PDF:useHard`, nuclear-hard PDFs, MPI, diffraction, resolved photons, photon
flux, unresolved, pomeron, and VMD slots must be disabled. Any unknown or
substituted proton provider fails closed.

Because the primary signed-value admission gate fails before pointer
installation, no pointer classification is claimed as measured and
`Pythia::init()` was not called. Post-init pointer substitution evidence is
therefore unavailable, not assumed successful.

## Query provenance

The versioned diagnostic schema is
`partonsbi.d1c.pythia-pdf-query-provenance.v1` with a fixed capacity of 4,096
records. Each record has a monotonic sequence; phase; consumer; method;
flavor; exact x/input-scale/derived-Q bits; optional raw and facade output
bits; status; typed reason; threshold side; and evaluator/facade policy
identity references. Overflow fails closed and never drops, samples, or grows
the buffer. `UNCLASSIFIED_EVENT_RUNTIME` is recorded as rejected and fails
closed. Records are provenance diagnostics and never ML features.

No facade query records were produced because admission stopped before facade
construction. Runtime consumer attribution therefore remains incomplete.

## CLI and remaining work

`prototype-pythia-pdf-facade --prepare-only --output <DIRECTORY>` performs the
signed-boundary admission check before creating its output directory. Under
the installed 8.312 contract it returns a typed incompatibility. `--study`,
`--events`, `--next`, and `--generate` are rejected by the parser. No
preparation manifest, Pythia initialization, event attempt, or event output is
created.

A reviewed architectural decision is required before further D1C work. It
must decide whether modifying/forking the PYTHIA public PDF boundary is
scientifically and operationally acceptable, or whether another transport
interface can preserve the accepted signed contract. The process-isolated
APFEL fallback does not solve this clipping boundary. D2 remains unauthorized.
