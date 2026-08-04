# Phase 1B closeout and reproducibility freeze

## Scope and scientific objective

This is a maintenance-only closeout of the accepted Phase 1A and Phase 1B
record at main commit `0acd10e0e27a5ae60cef31827f09ec77f3fccb33` (tree
`703e5f404c90e2773444adb0b1892f7a9308507d`). It adds no scientific result,
changes no accepted result, selects no candidate, and authorizes no later work.
The machine-readable authority is
[`phase1b_closeout_manifest.json`](phase1b_closeout_manifest.json).

The inference unit remains a set of events,
`D = {event_1, ..., event_N}`, with long-term target
`p(theta_PDF | D)`. It is not the instantaneous PDF of one proton inferred
from one event. One inclusive neutral-current electron-proton channel does not
provide unrestricted full-flavor separation.

## Accepted decision history

- Phase 1A: `FAIL — NOMINAL-POOL REUSE REJECTED`. This rejects reuse under the
  strict-support ESS gate, not direct regeneration or PDF SBI generally.
- D0: the original result remains `FAIL`; D0R is a separately versioned
  `PASS`. D0R does not supersede or erase D0.
- D1: the original result remains `FAIL`; the separately versioned D1R also
  remains `FAIL`. D1R does not supersede or erase D1.
- D1A architecture and bounded prototype: both `INCONCLUSIVE`.
- D1B: the historical planning result was
  `AUTHORIZE_SEPARATE_BOUNDED_PROTOTYPE`; it is historical evidence, not an
  active authorization.
- D1C: `FAIL`.
- D1D-A: `FAIL`; provenance slice v1 remains `REJECTED_DIAGNOSTIC`.
- D1D-B: `INCONCLUSIVE` with
  `PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION`.
- D1E: `INCONCLUSIVE`.
- D1F: `MAINTAIN_CURRENT_CONTRACT_AND_PAUSE`.
- D1G: `NO_UNIQUE_PRIORITY_MAINTAIN_PAUSE`; the eligible-candidate set is
  empty.

Failures and inconclusive outcomes are immutable scientific records. A later
revision may coexist with an earlier result, but it does not delete,
reinterpret, or mark that result as superseded.

## Frozen evidence artifacts

All listed hashes are SHA-256. The manifest also freezes each schema,
scientific scope, limitation, and non-supersession status.

| Phase | Artifact | Decision/status | SHA-256 |
|---|---|---|---|
| Phase 1A | `docs/phase1a_strict_support_decision.json` | `FAIL — NOMINAL-POOL REUSE REJECTED` | `59c2880886a72e35aa914c05c02068274eb78be93e4da25c51f5570f8940072c` |
| D0 | `docs/phase1bd_d0_decision.json` | `FAIL` | `c4f7ba061494a406ba99946d72b0842f2eeca952fdeb1cd3b552b43e674a7f04` |
| D0 revision | `docs/phase1bd_d0_revision_decision.json` | `D0_REVISION_PLAN_SELECTED` | `ef44ec6b230d06edce4b30b435d30ee382e3e151a8dfe3a9f8098e4ac6747873` |
| D0R | `docs/phase1bd_d0r_decision.json` | `PASS` | `40e75fda281578f45d193858667eeed2c1747a07d64f53672adec10145c9e775` |
| D1 | `docs/phase1bd_d1_decision.json` | `FAIL` | `3cdb3e6e11fae63aa9b4bb9e0094c0610a8c01eb636eecc25571e3c2f11e9881` |
| D1 revision | `docs/phase1bd_d1_revision_decision.json` | `SELECTED` | `885aa404b1c8effe96f44d29d6217330481fb66a311f6ad6212d1f8ab5859b4e` |
| D1R | `docs/phase1bd_d1r_decision.json` | `FAIL` | `69b5e823bb802a4adbc426ec5478caeeba623791a7b533d15557bf34f1bb8998` |
| D1A | `docs/phase1bd_d1a_architecture_decision.json` | `INCONCLUSIVE` | `9eb3feda36583a9e21835b7c3fa85ae5463db89d4212cbfb3721e3526eb5e626` |
| D1A prototype | `docs/phase1bd_d1a_prototype_decision.json` | `INCONCLUSIVE` | `e2274acb12d7cff2b8c22b0655537737556d9e1fc903abdbd92bfe2f24260a41` |
| D1B | `docs/phase1bd_d1b_decision.json` | `AUTHORIZE_SEPARATE_BOUNDED_PROTOTYPE` (historical) | `a92190686734091369a0a21caa9c032d62672dd5d1274f4b102fadbb1c710d6f` |
| D1C-A | `docs/phase1bd_d1c_a_preparation_evidence.json` | `PASS_PREPARATION_ONLY` | `1acffdc63690cd3185ef32c0cbd742f23d79c646a5c7dd775470dfae7732c55f` |
| D1C | `docs/phase1bd_d1c_decision.json` | `FAIL` | `1ce8a824175d078887bef6fc7c72bbccb2b7c8277cd9669c2a355ced42a6e41b` |
| D1D search | `docs/phase1bd_d1d_pythia_semantics_search_manifest.json` | syntactic closure only | `e381a6774a17306336ebb016f152b611e9b66c4628e5c3835cc93efb5a9dc701` |
| D1D slice | `docs/phase1bd_d1d_pythia_pdf_provenance_slice.json` | `REJECTED_DIAGNOSTIC` | `6641d6e2fb615780819bd957be2f942eab5f78f34828073eb66078088ef708c7` |
| D1D slice decision | `docs/phase1bd_d1d_pythia_provenance_slice_decision.json` | `FAIL` | `f92958fe745d64c24cd6d12222537154af7d916f24a0c7362c460123d46e04d7` |
| D1D audit | `docs/phase1bd_d1d_pythia_semantics_audit.json` | `FAIL` | `bd63eb4b779c8f6fa622b4a4111fa07a963303d7c80ba3761c339bb764a5b430` |
| D1D-B | `docs/phase1bd_d1d_terminal_decision.json` | `INCONCLUSIVE` | `d310b452a5a80d5bd59a91af2787b795dba7da17eb5d684990d9b718373376a7` |
| D1E | `docs/phase1bd_d1e_consumer_graph_feasibility.json` | `INCONCLUSIVE` | `2d597d24b6591dfe14a711a8b115956cbbfbaed6969bf65f772fa0510c107614` |
| D1F | `docs/phase1bd_d1f_active_contract_decision.json` | `MAINTAIN_CURRENT_CONTRACT_AND_PAUSE` | `62afa19354cb4546f4bc6019d58168d1803b6b2c9e8c57f29ecab14e29d198e5` |
| D1G | `docs/phase1bd_d1g_independent_contract_priority.json` | `NO_UNIQUE_PRIORITY_MAINTAIN_PAUSE` | `1d0eeed3bb012446ee2e75f00f175e31ecbfab61a5e326345f4007c0a640b778` |

## Frozen ADR identities

The exact status capitalization is historical and intentionally preserved.

| ADR | Status | SHA-256 |
|---|---|---|
| `ADR-001-continuous-pdf-family.md` | Accepted for staged validation | `bb31dcdf2f0e38e6807c06c887fa1b2ff1895755f03f90c81e4bca4e5bfc01d8` |
| `ADR-002-direct-generation-artifact.md` | Accepted for staged validation | `4d9501e09b9447e14a60945c8517db7a1ddac518f9e1bc5878760ba69e719cce` |
| `ADR-003-event-sampling-semantics.md` | Experiment required | `89c0cf8c09c4349f79855b614b2fea5c9d6eb632882bff5c18abe7f1a8d28fd5` |
| `ADR-004-d0-baseline-and-admissibility.md` | Proposed for scientific review | `db29c0f8a47e47bd22a54ec7548878f3f48332ed9acfafb987f53140ee72f4c8` |
| `ADR-005-d1-evolution-and-artifact-transport.md` | proposed for scientific review | `80e88b9ab650ae2bfdf4de3636cbad7c139c391aeb936195279e873999ca7424` |
| `ADR-006-evolved-pdf-transport-architecture.md` | Proposed for scientific review | `67093e678656307aa85d9eb3d99422dcac927d9b1a90f6c6b2a0f4e6e363b94d` |
| `ADR-007-persistent-apfel-transport.md` | Proposed for scientific review | `ae494c126e9431d7bc679a2256b4500960c7edc18dbfffdb89f62a4fe9643abf` |
| `ADR-008-signed-generator-coupling-terminal-decision.md` | Proposed | `a3463f3e1fea2b777e315c24daabd0b7181d43a3e5dc14b6d40d23ae311df112` |
| `ADR-009-ast-pdf-consumer-graph-feasibility.md` | Proposed | `9481ac861075141067813143b7d1beb66b7f6f0c2a3c164e79db18aa3eb8ed69` |
| `ADR-010-active-scientific-contract-after-generator-pause.md` | Proposed | `e30b2dd4045af61a45953d2f176132dcb84d3b6d7424d4ecdf8ae1525115e428` |
| `ADR-011-independent-evidence-for-contract-priority.md` | Proposed | `657cdd5e25eada28df3027b2626e92f62a5a6d979730a542550fca77a2a0918f` |

## Accepted merge lineage

| PR | Method | Main commit | Reviewed head | History statement |
|---|---|---|---|---|
| #40 | squash | `0e3e2870c95e4cfbd4665598ccc163071d5f762a` | `f01d84aced9e671f7f6896d4cc50b929a0471117` | reviewed branch commits are not ancestors |
| #41 | squash | `2cfcc431fbb742df7f483cdeac0077ff6fb27118` | `70756c10f1c2fc66c4067a4b4e7ff0dfabdb796f` | reviewed branch commits are not ancestors |
| #43 | merge commit | `c7c6f6a61f8aaec0a726cb440124e0f2c955634f` | `ba85569cd3df43456c3e73d521a72a3ce49dff6d` | reviewed branch history preserved |
| #44 | merge commit | `a9f91275e4add2adaffd9fbf6c98ca8fe14802df` | `21ee2061894854cfe9c89d0f9ee88d4a1f484aef` | reviewed branch history preserved |
| #46 | merge commit | `c5745c8f6e1cef4bf44108f06e0426a4ab7c1dfe` | `e16545640daf8d96d516538c2d4de1d18e6c5075` | reviewed branch history preserved |
| #48 | merge commit | `fc1949b8f3e6f21e48db84f89419a04c56bbcfec` | `8e270b4bd6c1c6476ab476d00c3c2ad2213d5eed` | reviewed branch history preserved |
| #50 | merge commit | `0acd10e0e27a5ae60cef31827f09ec77f3fccb33` | `80323f5b9725e3e32d1a5b52655620e2d0362a71` | reviewed branch history preserved |

The validator checks the recorded parents against full local Git history. It
does not pretend that the squashed PR #40 and #41 branch heads are ancestors of
main.

## Active pause, roadmap, and authorization boundary

The active policy is `PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION`. The
full-generator line is paused because no bounded continuation has been
established. No preferred or active scientific candidate and no implementation
next step exists. This pause is not a proof that PDF SBI is impossible.

Issue #51 is the open closeout-maintenance record. Issue #10 remains open,
`Blocked`, `Not Evaluated`, and `Not Authorized`. D2 remains `Blocked`; D3-D5
remain `Backlog`. No roadmap supersession and no next-phase selection is
active.

All authorization flags are false: implementation, prototype, PDF-family
redesign, lower-level simulator, weighted-set objective, signed-weight
research, `Pythia::init()`, `Pythia::next()`, event generation, dataset,
neural training, and D2.

## Non-authorizing reopen conditions

The four preserved conditions are:

1. new primary or mathematical evidence closes preference-critical normalized
   measure, posterior, no-hidden-repair, and composite-MVP gaps;
2. an independently reviewed generator or inference architecture provides a
   bounded and falsifiable path;
3. a separately accepted scientific-contract change; or
4. an explicit user decision terminates or redirects the research objective.

A reopen condition becoming true does not itself authorize implementation.
None is selected or preferred.

## Reproducibility and validation scope

Run the offline validator from the repository root:

```bash
python3 scripts/validate_phase1b_closeout.py
python3 -m json.tool docs/phase1b_closeout_manifest.json >/dev/null
python3 -m pytest -q analysis/tests/test_phase1b_closeout.py
cargo fmt --all -- --check
git diff --check
```

The validator checks canonical serialization, paths, schemas, file SHA-256
identities, decision payload invariants, ADR statuses and identities, the seven
recorded merge parent relationships, the generated-from tree, issue and
roadmap boundaries, the pause, reopen conditions, and all authorization flags.
It requires full Git history for the CLI lineage check; focused mutation tests
can disable only that Git-history portion for deterministic fixtures.

This validation does not rerun physics, re-read external publications, prove
scientific correctness, establish runtime behavior, execute a generator, or
authorize future work. The sole next action is maintenance: preserve the
accepted evidence and pause until a separately reviewed non-authorizing reopen
condition is satisfied.
