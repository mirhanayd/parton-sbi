# ADR-002: direct-generation PDF artifact

Status: Accepted for staged validation

Date: 2026-07-28

## Context

Direct Pythia generation and APFEL++ validation must use the same numerical
PDF family. Maintaining an APFEL++ callback and an unrelated custom Pythia
implementation would create two interpolation/evolution definitions.

LHAPDF 6.5.6 can load `lhagrid1` data but does not expose a public grid-writer
API. Pythia can accept a custom `PDF` through `setPDFPtr`, but that route
introduces separate cache and boundary behavior. The installed stock Pythia
LHAPDF adapter may freeze out-of-grid queries at a boundary, which does not
satisfy the PartonSBI strict-support contract.

## Decision

APFEL++ is the authoritative evolution engine. A future deterministic exporter
will serialize each validated parameter point as an immutable, one-member
LHAPDF6 `lhagrid1` artifact with an `.info` file and cryptographic manifest.

Both APFEL++ validation and Pythia generation load that artifact. The direct
APFEL++ evolution remains the independent comparison used to qualify the
writer and loader.

Artifacts use:

- canonical point serialization;
- full SHA-256 identities;
- metadata-derived support and evolution inputs;
- repository-local ignored storage under `.external/`;
- per-hash locking, temporary construction, checksum verification, and atomic
  publication;
- clean Git provenance for scientific production.

Every Pythia PDF consumer must be instrumented or mediated so unsupported
queries are visible and fail closed. A hard-process `GenPdfInfo` check alone
does not prove shower-side support.

## Consequences

- Generation and validation share one immutable numerical representation.
- A small LHAPDF writer must be implemented and exhaustively round-trip tested.
- Generated grids are reproducible cache products, not source artifacts, and
  must not be committed.
- Corrupt or partial cache entries cannot be accepted or overwritten in place.
- Strict support may require a thin diagnostic Pythia adapter that reads the
  same artifact; that experiment does not make a custom PDF the authoritative
  family.

## Rejected alternatives

- Separate APFEL++ and Pythia PDF definitions are rejected.
- A custom Pythia PDF is rejected as the primary representation.
- Parsing incidental program output for support or grid metadata is rejected.
- Allowing Pythia's implicit boundary freeze is rejected.
- Floating-point directory names are rejected.

## Validation

Stages 1 and 2 of
`../AMORTIZED_INFERENCE_PHASE1BD_ACCEPTANCE.md` must pass before an artifact
can be used outside short diagnostics. This ADR does not implement the writer,
cache, or Pythia integration.

## Revisit conditions

Revisit the artifact architecture only if the installed LHAPDF format cannot
round-trip the evolved family, strict all-consumer support cannot be enforced,
or measured artifact cost violates the reviewed resource budget. Any
replacement must still provide one authoritative numerical family to APFEL++
and Pythia.
