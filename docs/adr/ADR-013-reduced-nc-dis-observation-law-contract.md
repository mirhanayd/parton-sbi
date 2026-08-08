# ADR-013: Source-backed Reduced NC DIS observation-law contract

## Status

Proposed

## Context

Phase 2A requires defining a mathematical and scientific contract for the Reduced NC DIS observation model, strictly backed by primary or authoritative sources. The contract must bind the physics formulae, perturbative conventions, probability laws, detector kinematics, and simulation-based inference (SBI) objectives.

## Primary-Source Methodology

Every load-bearing claim relies on authoritative references (e.g., PDG, APFEL++ documentation, canonical SBI literature) to prevent unverified assumptions.

## Exact Contract

- Formula: Standard NC DIS differential cross section.
- Electroweak Scheme: G_F scheme.
- Perturbative Scheme: NLO VFNS.
- PDF Family: Accepted continuous family.

## Selected-Event Law

Conditioned fixed-N shape-only observation law without counting information.

## Posterior Law

The posterior probability target is `p(theta | D, N, selected)`.

## Identifiability Boundary

Proof-of-principle sensitivity only for predeclared parameter combinations that pass the later identifiability and information-content gates.

## Phase 2B Proposal Boundary

A bounded validation plan is proposed for numerical closure, but NOT authorized in this phase.

## Decision Derivation

All 11 binding gates evaluate to SUPPORTED. The provisional decision is PASS.

## Consequences

Recommends the Phase 2B validation proposal.

## Nonclaims

Does not claim full-generator equivalence, real detector simulation, or legacy D2 completion.

## Authorization

- PHASE2A_CONTRACT_REVIEW_AUTHORIZED = True
- PHASE2B_AUTHORIZED = False
- NUMERICAL_PHYSICS_AUTHORIZED = False

## Unresolved Items

Tolerances and specific detector model specifics are deferred to Phase 2B/2C.

## Source Limitations

Sources do not guarantee full-rate numerical positivity; this must be verified numerically.
