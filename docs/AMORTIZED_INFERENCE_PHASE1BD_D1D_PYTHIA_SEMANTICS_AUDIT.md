# Phase 1B-D1D-A downstream PYTHIA signed-PDF semantics audit

## Scope and immutable result

This is the planning-only installed-source audit tracked by issue #42. It does
not modify or execute PYTHIA, initialize a generator, evaluate APFEL or LHAPDF,
create events, select an architecture, or authorize a prototype.

The immutable D1C result remains:

```text
D1C_FINAL_DECISION = FAIL
failed_gate = generator_facing_signed_pdf_contract
D2_AUTHORIZED = false
```

The D1D-A correction preserves the already-supported conclusion:

```text
MINIMAL_PUBLIC_READER_PATCH = INSUFFICIENT
```

Removing only the positivity transformations in `PDF::xf`, `PDF::xfVal`, and
`PDF::xfSea` cannot give stock PYTHIA valid signed-PDF semantics. Multiple
prospective-HERA paths consume PDF-derived values as nonnegative rates,
positive denominators, probabilities, maxima, envelopes, or monotone
cumulative weights.

## Evidence artifacts and schemas

- `docs/phase1bd_d1d_pythia_semantics_search_manifest.json`
  (`partonsbi.phase1bd.d1d.pythia-semantics-search-manifest.v1`) records the
  reproducible full-tree search and classification of every raw match.
- `docs/phase1bd_d1d_pythia_semantics_audit.json`
  (`partonsbi.phase1bd.d1d.pythia-semantics-audit.v2`) records the refactored
  boundary, pointer, policy, call-site-group, and concrete-member model.

The audit v2 artifact binds the search manifest by SHA-256:

```text
a7aec222fdb75165733739624ae1b6db9782ded715bf5d03a7a8944b192656b5
```

## Source identity and header correspondence

The searched roots are:

```text
.external/pythia-8.3.12/include/Pythia8
.external/src/releases-pythia8312/include/Pythia8
.external/src/releases-pythia8312/src
```

The versioned release archive is
`.external/downloads/releases-pythia8312.tar.gz`, SHA-256
`c1a33aa5fa15e6b70d7946ce6d237246842887ec84ea0b35dfc2535c868a2770`.
The extracted directory is not an independent Git checkout, so the archive
hash and deterministic searched-file inventory identify the source tree.

The installed and extracted release copies of every cited installed header
were compared independently:

| Header | Installed versus release |
|---|---|
| `Pythia.h` | `IDENTICAL` |
| `SharedPointers.h` | `IDENTICAL` |
| `PartonDistributions.h` | `IDENTICAL` |
| `BeamParticle.h` | `IDENTICAL` |
| `SigmaProcess.h` | `IDENTICAL` |

The aggregate correspondence result is `ALL_IDENTICAL`. Both paths and both
hashes remain explicit in the search manifest and audit artifact; archive
identity alone is not used as proof of correspondence.

## Reproducible search closure

Identifiers were derived first from the five installed headers above. Nine
deterministic `LC_ALL=C grep -RInE` searches then covered:

1. `PDFPtr`, `setPDFPtr`, `getPDFPtr`, and role-specific pointer fields;
2. `xf`, `xfVal`, `xfSea`, `xfUpdate`, `xfHard`, `xfISR`, `xfMPI`,
   `xfModified`, `xfMax`, `xfSame`, `insideBounds`, `xfFlux`, `xfApprox`, and
   `xfGamma`;
3. PDF-owned and component-owned `alphaS` access;
4. valence, sea, companion, and rescaling caches;
5. PDF numerator, denominator, and ratio identifiers;
6. PDF-weighted sigma, rate, maximum, and negative-sigma policy identifiers;
7. PDF and explicit event-weight identifiers;
8. `TINYPDF` denominator/guard candidates;
9. indirect remnant and resolved-photon handoffs.

The exact commands and patterns are stored in the search manifest. The search
covered 374 `.h`/`.cc` files. Its canonical sorted `{path,sha256,bytes}`
inventory has a deterministic aggregate hash recorded in both evidence files.

### Raw-match disposition

```text
pattern_count                 = 9
raw_match_count               = 2778
included_match_count          = 797
excluded_match_count          = 1981
unclassified_raw_match_count  = 0
```

Every included match maps to a boundary node, pointer role, policy record, or
specific call-site group/member. Every excluded match records its file, exact
line, symbol or matched identifier, exclusion class, and reason. Exclusions
are divided among definitions, declarations, comments, false positives,
duplicate aliases, and source-capable occurrences irrelevant to PDF semantics.
No copied source blocks or large verbatim excerpts are stored.

## Corrected evidence model

The previous 30 records were heterogeneous groups and were incorrectly
described as 30 concrete call sites. Audit v2 separates:

```text
call_site_group_count          = 137
concrete_call_site_count       = 672
boundary_node_count            = 2
pointer_role_record_count      = 16
unresolved_policy_record_count = 4
policy_evidence_record_count   = 1
```

Each of the 137 call-site groups contains a nonempty `members` array. Every one
of the 672 concrete members records the exact source file and line, enclosing
symbol, PDF method/cache/ratio/field identifiers, concise arithmetic role,
unique primary semantic classification, static reachability status, direct
source status, and separately marked mathematical inference.

The two boundary nodes are not counted as runtime consumer calls:

1. the non-virtual public PDF readers and virtual `xfUpdate` cache-fill hook;
2. generic `BeamParticle` forwarding to ordinary, hard, ISR/MPI, bounds, and
   alpha_s PDF methods.

The sixteen `setPDFPtr` roles are static pointer metadata, not sixteen runtime
consumer call sites. Their source declarations, `BeamSetup::getPDFPtr` map
keys, prospective role classifications, and lack of runtime installation
verification are recorded independently.

## Corrected reachability model

The four permitted statuses are:

```text
PROSPECTIVE_HERA_SOURCE_REACHABLE
SOURCE_CAPABLE_DISABLED_BY_CONFIGURATION
HERA_REACHABILITY_UNRESOLVED
BOUNDARY_OR_METADATA_NOT_A_RUNTIME_PATH
```

For the 672 concrete call sites:

| Reachability | Count |
|---|---:|
| `PROSPECTIVE_HERA_SOURCE_REACHABLE` | 212 |
| `SOURCE_CAPABLE_DISABLED_BY_CONFIGURATION` | 436 |
| `HERA_REACHABILITY_UNRESOLVED` | 24 |
| `BOUNDARY_OR_METADATA_NOT_A_RUNTIME_PATH` | 0 |

The prospective HERA configuration remains 27.5 GeV electron on 920 GeV
proton, neutral-current gamma/Z DIS, `x in [1e-4,0.8]`,
`Q2 in [3.5,10000] GeV^2`, and `y in [0.01,0.95]`, with ISR and beam remnants
enabled. MPI, diffraction, resolved photons, photon flux, and optional
alternate shower/merging paths are disabled. Static source reachability is not
runtime coverage.

The 24 unresolved concrete sites are not counted as disabled merely to retain
an old total. In particular, static inspection cannot close every
beam-recoiler/time-shower path in the prospective configuration. PDF-owned
alpha_s forwarding is a separate unresolved policy record: standard hard,
ISR, and MPI components also own coupling objects, and source inspection alone
does not prove one future routing policy. Runtime installation or substitution
of the sixteen PDF roles likewise remains unresolved metadata rather than a
consumer call.

## Corrected semantic classifications

Primary classifications are counted over concrete members, not groups or
boundary metadata:

| Primary classification | Count |
|---|---:|
| `REQUIRES_NONNEGATIVE_DENSITY` | 26 |
| `REQUIRES_STRICTLY_POSITIVE_DENOMINATOR` | 375 |
| `REQUIRES_NONNEGATIVE_RATE` | 66 |
| `REQUIRES_PROBABILITY_IN_ZERO_ONE` | 40 |
| `REQUIRES_NONNEGATIVE_MAXIMUM_OR_ENVELOPE` | 93 |
| `REQUIRES_MONOTONE_CUMULATIVE_WEIGHT` | 72 |

The high denominator count reflects full-tree coverage of standard, merging,
Dire, and Vincia PDF-ratio paths rather than one representative record per
file. Disabled paths remain source-capable evidence and are not described as
enabled in the prospective HERA configuration.

## Material source conclusions

### Public boundary

Direct source evidence: `PDF::xf`, `PDF::xfVal`, and `PDF::xfSea` are
non-virtual; `xfUpdate` is the protected virtual cache-fill hook
(`PartonDistributions.h:82-93,188-195`). The public readers apply `max` and
`abs` positivity transformations (`PartonDistributions.cc:122-394`).

Inference: bypassing these transformations exposes signed cached values, but
does not make their consumers mathematically valid.

### Hard process and rejection sampling

Direct source evidence: `SigmaProcess::sigmaPDF` multiplies channel matrix
elements by beam PDFs and accumulates channel rates
(`SigmaProcess.cc:414-473`). `pickInState` performs a cumulative channel draw
(`SigmaProcess.cc:479-500`). Phase-space setup constructs maxima from
PDF-weighted trials (`PhaseSpace.cc:585-650`), and negative trial cross sections
are warned about then replaced by zero (`PhaseSpace.cc:1025-1130`). Process
selection consumes cumulative nonnegative maxima
(`ProcessLevel.cc:640-715,775-840`).

Inference: signed PDFs enter rates, categorical selection, and rejection
envelopes before a complete event history exists.

### ISR, Sudakov, and veto probabilities

Direct source evidence: standard ISR uses mother/daughter PDF ratios in
branching/Sudakov kernels (`SimpleSpaceShower.cc:1070-1225`), applies
PDF-ratio veto probabilities (`SimpleSpaceShower.cc:1495-1540`), and requires
positive old-PDF denominators in heavy-threshold corrections
(`SimpleSpaceShower.cc:1568-1660`). The full search also classifies every
matching standard, Dire, Vincia, merging, and beam-recoiler ratio site rather
than treating a few examples as complete coverage.

Inference: a negative PDF inside a rate, Sudakov integrand, denominator, or
veto probability requires a new internal sampling contract. It is not an
externally attachable final sign.

### Valence, sea, companion, and remnant selection

Direct source evidence: `BeamParticle::xfModified` forms rescaled component
totals (`BeamParticle.cc:350-425`); `pickValSeaComp` draws from cumulative
valence/sea/companion weights (`BeamParticle.cc:474-514`); incoming partons are
classified in `PartonLevel` (`PartonLevel.cc:1475-1504`); and beam-remnant
construction consumes those states (`BeamRemnants.cc:196-209,287-300`).

Inference: negative component weights do not define a monotone categorical
distribution. A final event sign cannot repair a flavor/remnant state sampled
from invalid probabilities.

## Minimal-reader-patch conclusion

```text
MINIMAL_PUBLIC_READER_PATCH = INSUFFICIENT
```

This conclusion is stronger after search closure, not weaker. Several
independent prospective-HERA algorithms require nonnegative densities, rates,
probabilities, denominators, maxima, or cumulative weights. A reader-only
change cannot supply a mathematically defined replacement for any of those
sampling kernels.

## External signed-weight boundary

PYTHIA has explicit negative Les Houches event-weight handling when the LHA
strategy declares it (`SigmaProcess.h:622-627`; `ProcessContainer.cc:350-430`).
That supports a sign attached after an externally constructed event history.
It does not equate negative NLO contribution weights with negative PDFs inside
hard-channel, ISR, remnant, or envelope sampling.

Therefore:

```text
EXTERNAL_FINAL_SIGNED_WEIGHT_ALONE_CANNOT_REPAIR_SIGNS_ENTERING_
STOCK_INTERNAL_HARD_ISR_REMNANT_OR_ENVELOPE_SAMPLING
```

No signed-weight implementation or internal sampling redesign is selected or
authorized here.

## Unresolved evidence

Four policy questions remain explicit:

1. no accepted signed Markov/Sudakov replacement exists for ISR;
2. no accepted unbiased signed categorical contract exists for hard-channel
   or remnant selection;
3. one PDF/hard/ISR/MPI alpha_s routing policy is not established;
4. static source cannot prove post-initialization identity or substitution of
   every PDF pointer role.

## D1D-A readiness rule and result

`READY_FOR_ARCHITECTURE_COMPARISON` is returned only because all required
conditions are true:

- unclassified raw search matches are zero;
- every included match maps to evidence;
- every concrete member has an included raw match;
- every group has at least one concrete member;
- every cited file is present in the hashed inventory;
- all cited installed/release header correspondences are resolved;
- reachability counts are recomputed from the new enum;
- direct source and mathematical inference remain separate;
- every planning authorization flag remains false.

Thus:

```text
D1D_A_RESULT = READY_FOR_ARCHITECTURE_COMPARISON
```

If any condition had failed, the result would be
`SOURCE_AUDIT_INCOMPLETE`. The result selects no architecture and authorizes
no implementation or prototype.

## Validation and next step

Validation is limited to JSON parsing, evidence invariants,
`cargo fmt --all -- --check`, and `git diff --check`. No repository binary,
PYTHIA, APFEL, LHAPDF, event, observable, or numerical study is executed.

A later reviewed D1D architecture comparison may use this closed source audit
to assess a versioned PYTHIA patch, a mathematically specified signed internal
sampling/weight design, another generator interface, or stopping generator
coupling. This audit selects and authorizes none of those options, and
`D2_AUTHORIZED=false` remains binding.
