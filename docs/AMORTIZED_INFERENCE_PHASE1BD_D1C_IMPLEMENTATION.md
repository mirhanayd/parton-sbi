# Phase 1B-D1C-A persistent APFEL transport core

## Scope and status

Issue #39 authorizes a bounded D1C prototype. This commit implements only its
first stage: one theta-specific persistent APFEL++ transport core, a safe Rust
owner, a preparation-only CLI, and focused lifetime/identity/safety checks.

```text
D1C_STAGE = D1C-A_CORE_IMPLEMENTATION
PROTOTYPE_AUTHORIZED = true
CONTROLLED_PYTHIA_NEXT_AUTHORIZED = true
PYTHIA_NEXT_EXECUTED = false
PRODUCTION_EVENTS_AUTHORIZED = false
D2_AUTHORIZED = false
SCIENTIFIC_GATE_COMPLETE = false
```

No PYTHIA PDF facade, consumer-envelope instrumentation, observable scan,
event execution, event output, dataset, or final D1C scientific decision is
present. The authorization to use bounded controlled `pythia.next()` later in
issue #39 is recorded but was not exercised in D1C-A.

## Native lifetime contract

The native bridge exposes opaque create, scalar/batch evaluate, alpha_s,
identity, support, diagnostics, and destroy operations. A successfully
published handle is a monotonically allocated opaque token; it is never a
publicly dereferenceable pointer. Null, fabricated, already-destroyed, and
partially constructed handles fail with typed status codes.

Each context owns, in destruction order:

1. the exact-Q cache;
2. `Dglap<Distribution>`;
3. `AlphaQCD`;
4. the APFEL grid;
5. the authoritative CT18NLO boundary member.

This ensures that the Dglap alpha_s callback cannot outlive `AlphaQCD`, and
that exact-Q0 boundary evaluation remains tied to the accepted projected D0R
source. Construction publishes a handle only after all owned objects exist.
Destruction removes the token from the registry before releasing dependencies.

One process-wide native mutex protects construction, handle lookup,
evaluation, cache mutation, diagnostics, and destruction. This is a
conservative prototype boundary; it does not claim general APFEL++ or LHAPDF
reentrancy or thread safety. There is no process-global scientific fallback.

## Evaluation contract

- Inputs use PDG flavors `-6..-1`, `1..6`, and `21`, finite `x`, and finite
  `Q` in GeV.
- Top and antitop return a typed inactive-flavor error. Unsupported IDs return
  a distinct typed error.
- Results are signed binary64 `x*f`; no clipping, absolute-value conversion,
  nearest-boundary replacement, extrapolation, or weights substitution occurs.
- Strict exported x/Q support is checked before evaluation.
- The charm and bottom lower/exact/upper sides are classified using exact
  binary64 threshold equality. Input and output order are preserved.
- Alpha_s is evaluated from the same owned `AlphaQCD` policy.

The independent correctness reference remains the existing fresh
rebuild-per-batch APFEL path. The persistent implementation does not replace
or share its evolution object.

## Rust ownership and errors

`PersistentApfelContext` is a non-null RAII owner after successful
initialization. It exposes no raw pointer publicly. `Drop` consumes the native
token exactly once; explicit `close` uses the same path. Public scalar, batch,
alpha_s, support, identity, and diagnostic operations return typed `Result`
values.

`Send` and `Sync` are justified only by the authoritative native mutex.
Threaded focused checks therefore establish serialized deterministic access,
not lock-free reentrancy. A subprocess smoke check independently constructs,
queries, and destroys a context; it is not the process-isolated fallback from
ADR-007.

## Identity and cache

The two identities remain separate:

- `evaluator_policy_identity` hashes the bridge ABI, APFEL/LHAPDF versions,
  evolution/grid/flavor/alpha_s/support/threshold policy, and mutex/cache
  policy;
- `theta_transport_identity` additionally hashes the exact canonical theta
  bits, parameter-point identity, and projected-boundary identity.

Runtime counters and timings are excluded. The exact-last-Q cache is scoped to
one theta context, keyed by exact Q binary64 bits, and protected by the same
native mutex. Hits and misses are counted. Cache-fill failure is typed and
clears the invalid entry; it never silently falls back to a fresh evaluator.

## Preparation-only CLI

```bash
parton-sbi prototype-persistent-apfel \
  --prepare-only \
  --output outputs/phase1bd_d1c_persistent_apfel
```

The command initializes and destroys exactly `center`, `delta_min`, and
`corner_min_max`, then writes a compact ignored
`preparation_manifest.json`. It records identities, support, thresholds,
versions, counters, issue #39 resource limits, and the authorization boundary.
It has no study mode and cannot initialize PYTHIA or create events.

## Focused validation

The focused checks cover persistent scalar/batch agreement with the fresh
reference at all three anchors, caller-order preservation, deterministic
repeat, inherited negative-gluon sign preservation, strict support, typed
flavors, charm/bottom threshold sides, identity separation, exact-Q cache,
failed initialization, safe handle lifetime, serialized Rust-thread access,
and independent subprocess construction/destruction.

The final commands for this stage are:

```bash
source scripts/pythia_env.sh
cargo fmt --all -- --check
cargo check --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo test --lib persistent_apfel -- --nocapture
cargo test --test persistent_apfel_transport -- --nocapture
cargo test prototype_persistent_apfel -- --nocapture
git diff --check
```

All commands passed in WSL Ubuntu. The library filter ran 4 persistent-APFEL
tests, the integration target ran 5 tests (including its independently spawned
child process), and the CLI filter ran 2 command-contract tests. Formatting,
workspace checking, Clippy with warnings denied, and diff whitespace checking
all passed. Two pre-existing D1A constant assertions were expressed as
compile-time assertions to satisfy Rust 1.97 Clippy without changing either
authorization value or scientific behavior.

No full workspace test, APFEL scan, D1A/D1C scientific study, observable scan,
or CI watch loop is part of this stage.

## Limitations and next step

This core has no evidence about persistent scalar throughput under a PYTHIA
consumer load, full consumer coverage, generator-facing sign behavior, or the
full neutral-current gamma/Z observable contract. The next separately scoped
step within issue #39 is implementation and review of fail-closed PYTHIA
consumer instrumentation under the already fixed resource caps. D2 remains
unauthorized.
