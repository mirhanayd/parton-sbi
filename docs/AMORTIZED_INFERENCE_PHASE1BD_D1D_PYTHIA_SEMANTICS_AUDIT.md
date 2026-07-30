# Phase 1B-D1D-A downstream PYTHIA signed-PDF semantics audit

## Scope and authorization

This is the planning-only source audit tracked by issue #42. It inspects the
installed PYTHIA 8.312 headers and matching source tree. It does not modify or
execute PYTHIA, initialize a generator, evaluate APFEL, create events, select
an architecture, or authorize a prototype. The immutable D1C result remains:

```text
D1C_FINAL_DECISION = FAIL
failed_gate = generator_facing_signed_pdf_contract
D2_AUTHORIZED = false
```

The machine-readable inventory is
`docs/phase1bd_d1d_pythia_semantics_audit.json`. It records a SHA-256 for every
cited source file and distinguishes direct source observations from
mathematical inference.

## Source identity and method boundary

The installed headers are under
`.external/pythia-8.3.12/include/Pythia8`; the matching implementation is under
`.external/src/releases-pythia8312`. The source is the versioned 8.312 release
archive `.external/downloads/releases-pythia8312.tar.gz`, SHA-256
`c1a33aa5fa15e6b70d7946ce6d237246842887ec84ea0b35dfc2535c868a2770`.
There is no independent Git commit in the extracted source directory, so the
release archive and the 23-file hash inventory form its deterministic identity.

Direct source evidence establishes the boundary:

- `PDF::xf`, `PDF::xfVal`, and `PDF::xfSea` are non-virtual public readers;
  `xfUpdate` is the protected virtual cache-fill hook
  (`PartonDistributions.h:82-93,188-195`).
- The public readers use `max(0., value)` and valence `abs` transformations
  (`PartonDistributions.cc:122-229,272-394`).
- `PDFPtr` is `shared_ptr<PDF>` (`SharedPointers.h:64-65`), so calls through the
  installed pointer boundary execute those non-virtual readers.
- `BeamParticle` forwards hard, ordinary, valence, sea, ISR/MPI, bounds, and
  PDF-alpha_s calls through its selected PDF pointers
  (`BeamParticle.h:218-267`).
- `Pythia::setPDFPtr` accepts sixteen role-specific PDF pointers
  (`Pythia.h:110-122`); source mapping is visible in
  `BeamSetup.cc:1545-1575`. This is static role evidence, not runtime pointer
  installation or post-initialization substitution evidence.

## Prospective HERA configuration and reachability

The prospective configuration is taken from accepted repository documents:
27.5 GeV electron and 920 GeV proton beams, neutral-current gamma/Z DIS,
`x in [1e-4,0.8]`, `Q2 in [3.5,10000] GeV^2`, and `y in [0.01,0.95]`.
ISR and beam remnants are enabled. MPI, diffraction, resolved photons, photon
fluxes, and merging/alternate showers are disabled. An alternate hard proton
PDF is disabled or must be identical.

The audit uses two exclusive static labels. `HERA` means source-reachable under
that prospective configuration; `disabled` means source-capable but disabled
there. Neither label is runtime coverage. Seventeen records are prospective
HERA paths and thirteen are source-capable-but-disabled paths.

## Downstream call-site inventory

Each row has one primary semantic classification. Secondary classifications,
zero/negative behavior, guards, risks, caller chains, and explicit inferences
are retained in the JSON artifact.

| ID | Source and lines | Consumer and arithmetic | Primary semantics | Reach | Reader-only patch | Signed-weight boundary |
|---|---|---|---|---|---|---|
| CS01 | `PartonDistributions.cc:122-229,272-394` | public `xf/xfVal/xfSea`; `max`/`abs` | `REQUIRES_NONNEGATIVE_DENSITY` | HERA | boundary only | unresolved |
| CS02 | `BeamParticle.h:218-267` | role-specific pointer forwarding | `REQUIRES_NONNEGATIVE_DENSITY` | HERA | unresolved | unresolved |
| CS03 | `BeamParticle.cc:350-425` | rescaled valence + sea + companion total | `REQUIRES_NONNEGATIVE_DENSITY` | HERA | insufficient | internal redesign |
| CS04 | `BeamParticle.cc:474-514` | cumulative valence/sea/companion draw | `REQUIRES_MONOTONE_CUMULATIVE_WEIGHT` | HERA | insufficient | internal redesign |
| CS05 | `BeamRemnants.cc:196-209,287-300` | remnant construction from selected classes | `REQUIRES_MONOTONE_CUMULATIVE_WEIGHT` | HERA | insufficient | incompatible kernel |
| CS06 | `SigmaProcess.cc:414-473` | `sigmaHat * pdfA * pdfB` channel rates | `REQUIRES_NONNEGATIVE_RATE` | HERA | insufficient | internal redesign |
| CS07 | `SigmaProcess.cc:479-500` | cumulative incoming-channel draw | `REQUIRES_MONOTONE_CUMULATIVE_WEIGHT` | HERA | insufficient | internal redesign |
| CS08 | `PhaseSpace.cc:585-650` | initialization maxima and envelopes | `REQUIRES_NONNEGATIVE_MAXIMUM_OR_ENVELOPE` | HERA | insufficient | incompatible kernel |
| CS09 | `PhaseSpace.cc:1025-1130` | negative trial sigma warned then zeroed | `REQUIRES_NONNEGATIVE_RATE` | HERA | insufficient | incompatible kernel |
| CS10 | `ProcessContainer.cc:190-250,330-430` | internal sigma handling; signed LHA is separate | `REQUIRES_NONNEGATIVE_RATE` | HERA | insufficient | incompatible kernel |
| CS11 | `ProcessLevel.cc:640-715,775-840` | cumulative process-maximum choice | `REQUIRES_NONNEGATIVE_MAXIMUM_OR_ENVELOPE` | HERA | insufficient | incompatible kernel |
| CS12 | `SimpleSpaceShower.cc:1070-1225` | ISR mother/daughter ratio in rate/Sudakov | `REQUIRES_NONNEGATIVE_RATE` | HERA | insufficient | internal redesign |
| CS13 | `SimpleSpaceShower.cc:1495-1540` | ISR PDF-ratio veto weight | `REQUIRES_PROBABILITY_IN_ZERO_ONE` | HERA | insufficient | incompatible kernel |
| CS14 | `SimpleSpaceShower.cc:1568-1660` | heavy-threshold old/new PDF ratio | `REQUIRES_STRICTLY_POSITIVE_DENOMINATOR` | HERA | insufficient | internal redesign |
| CS15 | `SimpleSpaceShower.cc:2335-2500` | optional weak-shower overestimate/flavor draw | `REQUIRES_MONOTONE_CUMULATIVE_WEIGHT` | disabled | insufficient | internal redesign |
| CS16 | `SimpleTimeShower.cc:2868-2900` | beam-recoiler PDF-ratio veto | `REQUIRES_PROBABILITY_IN_ZERO_ONE` | HERA | insufficient | incompatible kernel |
| CS17 | `PartonLevel.cc:1475-1504` | incoming initiator valence/sea/companion draw | `REQUIRES_MONOTONE_CUMULATIVE_WEIGHT` | HERA | insufficient | internal redesign |
| CS18 | `MultipartonInteractions.cc:1930-1995,2140-2185,2245-2285` | MPI cumulative flavor draw | `REQUIRES_MONOTONE_CUMULATIVE_WEIGHT` | disabled | insufficient | internal redesign |
| CS19 | `MultipartonInteractions.cc:1045-1085` | MPI initiator categorical assignment | `REQUIRES_PROBABILITY_IN_ZERO_ONE` | disabled | insufficient | incompatible kernel |
| CS20 | `History.cc:1260-1310,8880-8910` | merging PDF ratios with denominator floors | `REQUIRES_STRICTLY_POSITIVE_DENOMINATOR` | disabled | insufficient | internal redesign |
| CS21 | `DireHistory.cc:1304-1325,6740-6785` | Dire history PDF ratios | `REQUIRES_STRICTLY_POSITIVE_DENOMINATOR` | disabled | insufficient | internal redesign |
| CS22 | `VinciaISR.cc:4566-4579,4833-4854`; `VinciaEW.cc:3976-3984`; `VinciaQED.cc:1778-1784,2491-2513` | optional antenna/shower PDF ratios | `REQUIRES_STRICTLY_POSITIVE_DENOMINATOR` | disabled | insufficient | internal redesign |
| CS23 | `GammaKinematics.cc:285-312` | accurate/approximate photon-flux ratio | `REQUIRES_STRICTLY_POSITIVE_DENOMINATOR` | disabled | insufficient | incompatible kernel |
| CS24 | `BeamParticle.cc:702-747` | resolved-photon `xVal/(xVal+xSea)` choice | `REQUIRES_PROBABILITY_IN_ZERO_ONE` | disabled | insufficient | incompatible kernel |
| CS25 | `BeamSetup.cc:980-1115` | pomeron/diffractive provider into standard rates | `REQUIRES_NONNEGATIVE_DENSITY` | disabled | insufficient | internal redesign |
| CS26 | `BeamSetup.cc:980-1087,1545-1575` | alternate hard-PDF slot into hard rates | `REQUIRES_NONNEGATIVE_RATE` | disabled | insufficient | internal redesign |
| CS27 | `SigmaProcess.h:196-202,622-627`; `ProcessContainer.cc:190-250,350-430` | explicit negative LHA event weights | `SUPPORTS_EXPLICIT_SIGNED_WEIGHT` | disabled | not applicable | possibly sufficient only after a positive history |
| CS28 | `BeamParticle.h:262-270`; shower/MPI/hard sources in JSON | PDF alpha_s proxy versus component couplings | `SEMANTICS_UNRESOLVED` | disabled | unresolved | unresolved |
| CS29 | `Pythia.h:110-122`; `SharedPointers.h:64-65`; `BeamSetup.cc:1545-1575` | sixteen static pointer roles | `SEMANTICS_UNRESOLVED` | HERA | unresolved | unresolved |
| CS30 | `GammaKinematics.cc:450-485` | flux-ratio trial weight | `REQUIRES_PROBABILITY_IN_ZERO_ONE` | disabled | insufficient | incompatible kernel |

Primary classification counts are:

| Classification | Count |
|---|---:|
| `REQUIRES_NONNEGATIVE_DENSITY` | 4 |
| `REQUIRES_STRICTLY_POSITIVE_DENOMINATOR` | 5 |
| `REQUIRES_NONNEGATIVE_RATE` | 5 |
| `REQUIRES_PROBABILITY_IN_ZERO_ONE` | 5 |
| `REQUIRES_NONNEGATIVE_MAXIMUM_OR_ENVELOPE` | 2 |
| `REQUIRES_MONOTONE_CUMULATIVE_WEIGHT` | 6 |
| `SUPPORTS_EXPLICIT_SIGNED_WEIGHT` | 1 |
| `SEMANTICS_UNRESOLVED` | 2 |
| `SIGNED_VALUE_ALGEBRAICALLY_VALID` | 0 |

## Direct source findings and mathematical inferences

### Hard process

Direct source evidence: `SigmaProcess::sigmaPDF` multiplies channel matrix
elements by the two beam PDFs and sums the resulting `pdfSigma` values
(`SigmaProcess.cc:414-473`). `pickInState` treats those channel values as a
monotone cumulative distribution (`SigmaProcess.cc:479-500`). Phase-space
initialization uses PDF-weighted trials to construct maxima
(`PhaseSpace.cc:585-650`), and a negative trial cross section is later warned
about and replaced by zero (`PhaseSpace.cc:1025-1130`). Process choice uses
cumulative nonnegative maxima (`ProcessLevel.cc:640-715,775-840`).

Inference: a negative PDF contribution reaches rate, channel-selection, and
envelope construction before a complete event history exists. Removing only
the public clipping readers would therefore create negative or nonmonotone
inputs to algorithms whose stock mathematical meaning is positive sampling.

### ISR and beam recoils

Direct source evidence: the standard space shower forms mother/daughter PDF
ratios inside its branching kernel, protects denominators with `TINYPDF`, and
uses the result in Sudakov/trial evolution (`SimpleSpaceShower.cc:1070-1225`).
Later veto steps compare a PDF-ratio weight with a uniform random number
(`SimpleSpaceShower.cc:1495-1540`). Heavy-flavor threshold handling requires a
strictly positive old PDF denominator (`SimpleSpaceShower.cc:1568-1660`). The
time shower also applies a beam-recoiler PDF-ratio veto
(`SimpleTimeShower.cc:2868-2900`).

Inference: a negative PDF numerator is not an externally attachable sign in
these paths. It changes or invalidates a branching rate, Sudakov integrand, or
veto probability. A mathematically defined signed internal shower would be a
new sampling architecture, not a minimal reader patch.

### Valence, sea, companion, and remnants

Direct source evidence: `xfModified` constructs a rescaled sum of valence,
sea/gluon, and companion terms (`BeamParticle.cc:350-425`).
`pickValSeaComp` multiplies that total by a uniform random number and traverses
cumulative component weights (`BeamParticle.cc:474-514`). `PartonLevel`
invokes this classification for incoming partons (`PartonLevel.cc:1475-1504`),
and `BeamRemnants` consumes the resulting state (`BeamRemnants.cc:196-209`).

Inference: signed components do not define a monotone categorical probability.
An external final event sign cannot retrospectively correct which flavor or
remnant state was sampled.

### Disabled but source-capable consumers

MPI repeats cumulative PDF flavor selection
(`MultipartonInteractions.cc:1930-1995,2140-2185,2245-2285`). Merging, Dire,
and Vincia form PDF ratios with positive floors or direct denominators. Photon
flux and resolved-photon paths form flux ratios and valence probabilities.
Diffraction and alternate hard PDFs feed the same hard-rate machinery. These
paths are disabled in the prospective HERA configuration, but that is not a
claim of global safety or unreachability.

### alpha_s and pointer coverage

`BeamParticle::alphaS` can forward the PDF provider's coupling
(`BeamParticle.h:262-270`), while the standard hard, ISR, and MPI components in
the cited sources use their own coupling objects. A future architecture must
therefore prove coupling-policy consistency separately. The sixteen pointer
slots have a static source mapping, but this audit performed no initialization
and makes no runtime pointer-substitution claim.

## Minimal-public-patch sufficiency

```text
remove/bypass positivity transforms in PDF::xf/xfVal/xfSea = INSUFFICIENT
```

The change is sufficient only to expose a signed cached value at that public
boundary. It is insufficient for the generator because multiple prospective
HERA paths then interpret the sign as a channel rate, cumulative probability,
Sudakov/branching rate, positive denominator, veto probability, or rejection
maximum. Any one of those reachable paths would disprove reader-only
sufficiency; this audit identifies independent failures in the hard process,
ISR, and remnant logic.

## Signed-weight feasibility boundary

The source supports explicitly signed Les Houches event weights when the LHA
strategy declares them (`SigmaProcess.h:622-627`; `ProcessContainer.cc:350-430`).
That is evidence only for a sign attached after an externally constructed event
history. It is not evidence that a negative PDF can be passed through the
internal generator.

| Where the sign first enters | Classification |
|---|---|
| After a complete positive-probability history | `EXTERNAL_SIGNED_WEIGHT_POSSIBLY_SUFFICIENT` |
| Hard-process channel selection | `REQUIRES_SIGNED_INTERNAL_SAMPLING_REDESIGN` |
| ISR backward evolution or Sudakov construction | `INCOMPATIBLE_WITH_CURRENT_PROBABILITY_KERNEL` |
| Remnant or flavor selection | `REQUIRES_SIGNED_INTERNAL_SAMPLING_REDESIGN` |
| Rejection maximum or envelope | `INCOMPATIBLE_WITH_CURRENT_PROBABILITY_KERNEL` |

Therefore an external signed event weight is not sufficient for negative PDFs
in stock internal generation: the sign changes sampling decisions before a
complete positive-probability history exists. This conclusion does not design
or authorize a signed-weight replacement.

## Unresolved evidence

Four questions remain for a later architecture comparison:

1. No accepted mathematical contract specifies a signed Markov/Sudakov or
   alternative ISR kernel.
2. No accepted contract reformulates hard-channel and remnant categorical
   selection as an unbiased signed measure.
3. A single alpha_s policy across PDF, hard, ISR, and MPI consumers is not
   established by a reader patch.
4. Static inspection cannot prove which of sixteen PDF pointer roles a future
   initialized configuration installs or substitutes.

These questions prevent selection of a fork, signed-weight system, or alternate
generator here. They do not prevent comparison of those architecture classes,
because the material stock and minimal-patch source paths have been resolved.

## Conclusions

1. Stock PYTHIA 8.312 does not support the accepted signed PDF contract. This
   is the immutable D1C `FAIL`.
2. Removing the three public positivity transformations is `INSUFFICIENT`.
3. Prospective-HERA-reachable downstream nonnegative probability, rate,
   denominator, maximum, and cumulative-weight assumptions exist.
4. An external signed event weight cannot preserve the target measure without
   changing internal sampling when the PDF sign enters these paths.
5. The four unresolved questions above remain explicit.
6. D1D-A result:

```text
READY_FOR_ARCHITECTURE_COMPARISON
```

This result selects no architecture and authorizes no implementation or
prototype. It records only that the source audit is sufficiently complete for
a later reviewed comparison.

## Validation and limits

The required validation is JSON parse/schema/authorization checking,
`cargo fmt --all -- --check`, and `git diff --check`. No repository binary,
APFEL/LHAPDF command, PYTHIA initialization or event execution, numerical
study, event, dataset, or observable scan is part of this audit.

All authorization flags remain false, including `IMPLEMENTATION_AUTHORIZED`,
`PROTOTYPE_AUTHORIZED`, `PYTHIA_FORK_AUTHORIZED`,
`SIGNED_WEIGHT_PROTOTYPE_AUTHORIZED`, `ALTERNATIVE_GENERATOR_AUTHORIZED`,
`PYTHIA_INIT_AUTHORIZED`, `PYTHIA_NEXT_AUTHORIZED`,
`EVENT_GENERATION_AUTHORIZED`, `DATASET_AUTHORIZED`, and `D2_AUTHORIZED`.

## Next step

A separately reviewed D1D architecture comparison may use this audit to assess
a versioned PYTHIA patch, a mathematically specified signed-weight/internal
sampling redesign, another generator interface, or stopping generator
coupling. This document does not select or authorize any of them.
