#!/usr/bin/env python3
"""Validate the maintenance-only Phase 1B closeout identity manifest."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA = "partonsbi.phase1b.closeout-manifest.v2"
MANIFEST_PATH = "docs/phase1b_closeout_manifest.json"
GENERATED_FROM_MAIN = "0acd10e0e27a5ae60cef31827f09ec77f3fccb33"
GENERATED_FROM_TREE = "703e5f404c90e2773444adb0b1892f7a9308507d"

AUTHORIZATION_FLAGS = (
    "IMPLEMENTATION_AUTHORIZED",
    "PROTOTYPE_AUTHORIZED",
    "PDF_FAMILY_REDESIGN_AUTHORIZED",
    "LOWER_LEVEL_SIMULATOR_AUTHORIZED",
    "WEIGHTED_SET_OBJECTIVE_AUTHORIZED",
    "SIGNED_WEIGHT_RESEARCH_AUTHORIZED",
    "PYTHIA_INIT_AUTHORIZED",
    "PYTHIA_NEXT_AUTHORIZED",
    "EVENT_GENERATION_AUTHORIZED",
    "DATASET_AUTHORIZED",
    "NEURAL_TRAINING_AUTHORIZED",
    "D2_AUTHORIZED",
)


def artifact(
    phase: str,
    path: str,
    schema: str | int,
    sha256: str,
    decision: str,
    scientific_scope: str,
    limitation: str,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "path": path,
        "schema": schema,
        "sha256": sha256,
        "decision": decision,
        "immutable": True,
        "superseded": False,
        "superseded_by": None,
        "scientific_scope": scientific_scope,
        "limitation": limitation,
    }


ARTIFACT_SPECS = (
    artifact(
        "Phase 1A",
        "docs/phase1a_strict_support_decision.json",
        1,
        "59c2880886a72e35aa914c05c02068274eb78be93e4da25c51f5570f8940072c",
        "FAIL — NOMINAL-POOL REUSE REJECTED",
        "Strict-support discrete-member reweighting and the predeclared ESS reuse gate.",
        "This rejects nominal-pool reuse; it does not reject direct regeneration or PDF SBI generally.",
    ),
    artifact(
        "Phase 1B-D0",
        "docs/phase1bd_d0_decision.json",
        "partonsbi.phase1bd_d0_decision.v1",
        "c4f7ba061494a406ba99946d72b0842f2eeca952fdeb1cd3b552b43e674a7f04",
        "FAIL",
        "Original D0 continuous boundary-family pilot and guard-shell validation.",
        "The original failed result coexists with D0R and is not replaced by it.",
    ),
    artifact(
        "Phase 1B-D0 revision",
        "docs/phase1bd_d0_revision_decision.json",
        "partonsbi.phase1bd_d0_revision_decision.v1",
        "ef44ec6b230d06edce4b30b435d30ee382e3e151a8dfe3a9f8098e4ac6747873",
        "D0_REVISION_PLAN_SELECTED",
        "Diagnosis and bounded authorization record for the separately versioned D0 revision.",
        "This planning record did not itself validate D0R or authorize D1.",
    ),
    artifact(
        "Phase 1B-D0R",
        "docs/phase1bd_d0r_decision.json",
        "partonsbi.phase1bd_d0r_decision.v2",
        "40e75fda281578f45d193858667eeed2c1747a07d64f53672adec10145c9e775",
        "PASS",
        "Projected-baseline D0R validation under the ADR-004 admissibility contract.",
        "D0R PASS does not delete or reinterpret the original D0 FAIL.",
    ),
    artifact(
        "Phase 1B-D1",
        "docs/phase1bd_d1_decision.json",
        "partonsbi.phase1bd.d1.decision.v1",
        "3cdb3e6e11fae63aa9b4bb9e0094c0610a8c01eb636eecc25571e3c2f11e9881",
        "FAIL",
        "Original APFEL evolution and one-member LHAPDF transport validation.",
        "The failed off-knot and evolved-moment gates remain immutable.",
    ),
    artifact(
        "Phase 1B-D1 revision",
        "docs/phase1bd_d1_revision_decision.json",
        "partonsbi.phase1bd.d1_revision.decision.v1",
        "885aa404b1c8effe96f44d29d6217330481fb66a311f6ad6212d1f8ab5859b4e",
        "SELECTED",
        "Selection of the threshold-separated D1 revision contract.",
        "Selection did not erase the original D1 FAIL or authorize D2.",
    ),
    artifact(
        "Phase 1B-D1R",
        "docs/phase1bd_d1r_decision.json",
        "partonsbi.phase1bd.d1r.decision.v2",
        "69b5e823bb802a4adbc426ec5478caeeba623791a7b533d15557bf34f1bb8998",
        "FAIL",
        "Revised Stage 1 threshold-separated artifact and transport study.",
        "D1R failed its fixed performance, moment/leakage, and off-knot gates and does not replace D1.",
    ),
    artifact(
        "Phase 1B-D1A",
        "docs/phase1bd_d1a_architecture_decision.json",
        "partonsbi.phase1bd.d1a.architecture-decision.v1",
        "9eb3feda36583a9e21835b7c3fa85ae5463db89d4212cbfb3721e3526eb5e626",
        "INCONCLUSIVE",
        "Architecture review of evolved-PDF transport candidates.",
        "No production architecture was selected by this decision.",
    ),
    artifact(
        "Phase 1B-D1A",
        "docs/phase1bd_d1a_prototype_decision.json",
        "partonsbi.phase1bd.d1a.transport-prototype-decision.v1",
        "e2274acb12d7cff2b8c22b0655537737556d9e1fc903abdbd92bfe2f24260a41",
        "INCONCLUSIVE",
        "Bounded transport-comparison prototype result.",
        "The custom representation failed and direct APFEL transport remained unselected.",
    ),
    artifact(
        "Phase 1B-D1B",
        "docs/phase1bd_d1b_decision.json",
        "partonsbi.phase1bd.d1b.transport-decision.v1",
        "a92190686734091369a0a21caa9c032d62672dd5d1274f4b102fadbb1c710d6f",
        "AUTHORIZE_SEPARATE_BOUNDED_PROTOTYPE",
        "Historical source-level persistent-transport and PYTHIA-consumer planning decision.",
        "This was a bounded historical prototype authorization, not current implementation or D2 authorization.",
    ),
    artifact(
        "Phase 1B-D1C-A",
        "docs/phase1bd_d1c_a_preparation_evidence.json",
        "partonsbi.d1c.persistent-apfel.preparation-evidence.v1",
        "1acffdc63690cd3185ef32c0cbd742f23d79c646a5c7dd775470dfae7732c55f",
        "PASS_PREPARATION_ONLY",
        "Persistent APFEL construction, identity, lifetime, and destruction preparation evidence.",
        "This is engineering preparation evidence; the final D1C scientific gate was not evaluated here.",
    ),
    artifact(
        "Phase 1B-D1C",
        "docs/phase1bd_d1c_decision.json",
        "partonsbi.phase1bd.d1c.final-decision.v1",
        "1ce8a824175d078887bef6fc7c72bbccb2b7c8277cd9669c2a355ced42a6e41b",
        "FAIL",
        "Final stock-PYTHIA signed-PDF public-reader compatibility decision.",
        "Failure is scoped to the tested stock PYTHIA 8.312 public PDF boundary.",
    ),
    artifact(
        "Phase 1B-D1D-A",
        "docs/phase1bd_d1d_pythia_semantics_search_manifest.json",
        "partonsbi.phase1bd.d1d.pythia-semantics-search-manifest.v3",
        "e381a6774a17306336ebb016f152b611e9b66c4628e5c3835cc93efb5a9dc701",
        "SUPPORTED_SYNTACTIC_CLOSURE_ONLY",
        "Deterministic broad PYTHIA 8.312 syntactic occurrence corpus.",
        "Syntactic closure is not a typed consumer graph or scientific provenance classification.",
    ),
    artifact(
        "Phase 1B-D1D-A",
        "docs/phase1bd_d1d_pythia_pdf_provenance_slice.json",
        "partonsbi.phase1bd.d1d.pythia-pdf-provenance-slice.v1",
        "6641d6e2fb615780819bd957be2f942eab5f78f34828073eb66078088ef708c7",
        "REJECTED_DIAGNOSTIC",
        "Tokenizer-based typed-PDF provenance-slice diagnostic.",
        "The slice is retained only as rejected diagnostic evidence and is not a valid review queue.",
    ),
    artifact(
        "Phase 1B-D1D-A",
        "docs/phase1bd_d1d_pythia_provenance_slice_decision.json",
        "partonsbi.phase1bd.d1d.pythia-provenance-slice-decision.v1",
        "f92958fe745d64c24cd6d12222537154af7d916f24a0c7362c460123d46e04d7",
        "FAIL",
        "Independent integrity decision for provenance-slice v1.",
        "The failed gate is provenance evidence integrity; supported syntactic results remain narrower.",
    ),
    artifact(
        "Phase 1B-D1D-A",
        "docs/phase1bd_d1d_pythia_semantics_audit.json",
        "partonsbi.phase1bd.d1d.pythia-semantics-audit.v6",
        "bd63eb4b779c8f6fa622b4a4111fa07a963303d7c80ba3761c339bb764a5b430",
        "FAIL",
        "Final D1D-A evidence-integrity audit and preserved direct evidence.",
        "The record does not establish architecture-comparison readiness.",
    ),
    artifact(
        "Phase 1B-D1D-B",
        "docs/phase1bd_d1d_terminal_decision.json",
        "partonsbi.phase1bd.d1d.terminal-decision.v3",
        "d310b452a5a80d5bd59a91af2787b795dba7da17eb5d684990d9b718373376a7",
        "INCONCLUSIVE",
        "Evidence-derived terminal generator-coupling planning record.",
        "The operational result is an interim non-authorizing pause, not a universal impossibility theorem.",
    ),
    artifact(
        "Phase 1B-D1E",
        "docs/phase1bd_d1e_consumer_graph_feasibility.json",
        "partonsbi.phase1bd.d1e.consumer-graph-feasibility.v2",
        "2d597d24b6591dfe14a711a8b115956cbbfbaed6969bf65f772fa0510c107614",
        "INCONCLUSIVE",
        "Planning feasibility and acceptance contract for an AST-grounded consumer graph.",
        "No parser, graph implementation, or toolchain was selected or authorized.",
    ),
    artifact(
        "Phase 1B-D1F",
        "docs/phase1bd_d1f_active_contract_decision.json",
        "partonsbi.phase1bd.d1f.active-contract-decision.v3",
        "62afa19354cb4546f4bc6019d58168d1803b6b2c9e8c57f29ecab14e29d198e5",
        "MAINTAIN_CURRENT_CONTRACT_AND_PAUSE",
        "Active-contract decision after the generator-coupling line became unbounded.",
        "No separate prospective contract was preferred or authorized.",
    ),
    artifact(
        "Phase 1B-D1G",
        "docs/phase1bd_d1g_independent_contract_priority.json",
        "partonsbi.phase1bd.d1g.independent-contract-priority.v2",
        "1d0eeed3bb012446ee2e75f00f175e31ecbfab61a5e326345f4007c0a640b778",
        "NO_UNIQUE_PRIORITY_MAINTAIN_PAUSE",
        "Independent-evidence review of four prospective scientific contracts.",
        "All candidates remain ineligible; component evidence does not establish a normalized law, posterior, or MVP.",
    ),
)

ADR_SPECS = (
    ("docs/adr/ADR-001-continuous-pdf-family.md", "Accepted for staged validation", "bb31dcdf2f0e38e6807c06c887fa1b2ff1895755f03f90c81e4bca4e5bfc01d8"),
    ("docs/adr/ADR-002-direct-generation-artifact.md", "Accepted for staged validation", "4d9501e09b9447e14a60945c8517db7a1ddac518f9e1bc5878760ba69e719cce"),
    ("docs/adr/ADR-003-event-sampling-semantics.md", "Experiment required", "89c0cf8c09c4349f79855b614b2fea5c9d6eb632882bff5c18abe7f1a8d28fd5"),
    ("docs/adr/ADR-004-d0-baseline-and-admissibility.md", "Proposed for scientific review", "db29c0f8a47e47bd22a54ec7548878f3f48332ed9acfafb987f53140ee72f4c8"),
    ("docs/adr/ADR-005-d1-evolution-and-artifact-transport.md", "proposed for scientific review", "80e88b9ab650ae2bfdf4de3636cbad7c139c391aeb936195279e873999ca7424"),
    ("docs/adr/ADR-006-evolved-pdf-transport-architecture.md", "Proposed for scientific review", "67093e678656307aa85d9eb3d99422dcac927d9b1a90f6c6b2a0f4e6e363b94d"),
    ("docs/adr/ADR-007-persistent-apfel-transport.md", "Proposed for scientific review", "ae494c126e9431d7bc679a2256b4500960c7edc18dbfffdb89f62a4fe9643abf"),
    ("docs/adr/ADR-008-signed-generator-coupling-terminal-decision.md", "Proposed", "a3463f3e1fea2b777e315c24daabd0b7181d43a3e5dc14b6d40d23ae311df112"),
    ("docs/adr/ADR-009-ast-pdf-consumer-graph-feasibility.md", "Proposed", "9481ac861075141067813143b7d1beb66b7f6f0c2a3c164e79db18aa3eb8ed69"),
    ("docs/adr/ADR-010-active-scientific-contract-after-generator-pause.md", "Proposed", "e30b2dd4045af61a45953d2f176132dcb84d3b6d7424d4ecdf8ae1525115e428"),
    ("docs/adr/ADR-011-independent-evidence-for-contract-priority.md", "Proposed", "657cdd5e25eada28df3027b2626e92f62a5a6d979730a542550fca77a2a0918f"),
)


def lineage(
    pr_number: int,
    merge_commit: str,
    first_parent: str,
    second_parent: str | None,
    merge_method: str,
    reviewed_branch_head: str,
    preserved: bool,
) -> dict[str, Any]:
    record = {
        "pr_number": pr_number,
        "merge_commit": merge_commit,
        "first_parent": first_parent,
        "second_parent": second_parent,
        "merge_method": merge_method,
        "reviewed_branch_head": reviewed_branch_head,
        "reviewed_branch_commits_preserved": preserved,
        "metadata_source": "LOCAL_GIT_AND_GITHUB_PR_METADATA",
    }
    if merge_method == "SQUASH":
        record.update(
            {
                "reviewed_branch_head_source": "GITHUB_PR_METADATA",
                "reviewed_branch_head_offline_ancestry_verifiable": False,
                "squash_commit_parentage_offline_verifiable": True,
            }
        )
    else:
        record.update(
            {
                "reviewed_branch_head_source": "LOCAL_GIT_SECOND_PARENT_AND_GITHUB_PR_METADATA",
                "reviewed_branch_head_offline_ancestry_verifiable": True,
                "merge_commit_parentage_offline_verifiable": True,
            }
        )
    return record


MERGE_LINEAGE = (
    lineage(40, "0e3e2870c95e4cfbd4665598ccc163071d5f762a", "c0468d784e27d95d20a420beecb7133975701706", None, "SQUASH", "f01d84aced9e671f7f6896d4cc50b929a0471117", False),
    lineage(41, "2cfcc431fbb742df7f483cdeac0077ff6fb27118", "0e3e2870c95e4cfbd4665598ccc163071d5f762a", None, "SQUASH", "70756c10f1c2fc66c4067a4b4e7ff0dfabdb796f", False),
    lineage(43, "c7c6f6a61f8aaec0a726cb440124e0f2c955634f", "2cfcc431fbb742df7f483cdeac0077ff6fb27118", "ba85569cd3df43456c3e73d521a72a3ce49dff6d", "MERGE_COMMIT", "ba85569cd3df43456c3e73d521a72a3ce49dff6d", True),
    lineage(44, "a9f91275e4add2adaffd9fbf6c98ca8fe14802df", "c7c6f6a61f8aaec0a726cb440124e0f2c955634f", "21ee2061894854cfe9c89d0f9ee88d4a1f484aef", "MERGE_COMMIT", "21ee2061894854cfe9c89d0f9ee88d4a1f484aef", True),
    lineage(46, "c5745c8f6e1cef4bf44108f06e0426a4ab7c1dfe", "a9f91275e4add2adaffd9fbf6c98ca8fe14802df", "e16545640daf8d96d516538c2d4de1d18e6c5075", "MERGE_COMMIT", "e16545640daf8d96d516538c2d4de1d18e6c5075", True),
    lineage(48, "fc1949b8f3e6f21e48db84f89419a04c56bbcfec", "c5745c8f6e1cef4bf44108f06e0426a4ab7c1dfe", "8e270b4bd6c1c6476ab476d00c3c2ad2213d5eed", "MERGE_COMMIT", "8e270b4bd6c1c6476ab476d00c3c2ad2213d5eed", True),
    lineage(50, "0acd10e0e27a5ae60cef31827f09ec77f3fccb33", "fc1949b8f3e6f21e48db84f89419a04c56bbcfec", "80323f5b9725e3e32d1a5b52655620e2d0362a71", "MERGE_COMMIT", "80323f5b9725e3e32d1a5b52655620e2d0362a71", True),
)

SCIENTIFIC_OBJECTIVE = {
    "inference_unit": "D = {event_1, ..., event_N}",
    "target": "p(theta_PDF | D)",
    "single_event_instantaneous_pdf_objective": False,
    "unrestricted_full_flavor_separation_claimed_for_inclusive_nc_ep": False,
}

ACCEPTED_DECISIONS = {
    "PHASE1A_FINAL_DECISION": "FAIL — NOMINAL-POOL REUSE REJECTED",
    "D0_ORIGINAL_DECISION": "FAIL",
    "D0R_DECISION": "PASS",
    "D1_ORIGINAL_DECISION": "FAIL",
    "D1R_DECISION": "FAIL",
    "D1A_ARCHITECTURE_DECISION": "INCONCLUSIVE",
    "D1A_PROTOTYPE_DECISION": "INCONCLUSIVE",
    "D1B_HISTORICAL_PLANNING_DECISION": "AUTHORIZE_SEPARATE_BOUNDED_PROTOTYPE",
    "D1C_FINAL_DECISION": "FAIL",
    "D1D_A_FINAL_DECISION": "FAIL",
    "D1D_B_FINAL_DECISION": "INCONCLUSIVE",
    "D1E_FINAL_DECISION": "INCONCLUSIVE",
    "D1F_FINAL_DECISION": "MAINTAIN_CURRENT_CONTRACT_AND_PAUSE",
    "D1G_FINAL_DECISION": "NO_UNIQUE_PRIORITY_MAINTAIN_PAUSE",
    "D1G_ELIGIBLE_CANDIDATES": [],
}

ISSUE_STATE = {
    "closeout_workflow": {
        "issue_number": 51,
        "inventory_snapshot": {
            "observed_state": "OPEN",
            "observed_status": "In Progress",
            "observed_gate_decision": "Not Evaluated",
            "observed_authorization": "Planning Only",
            "observed_phase": "Phase 1B-D1",
            "observed_work_type": "Documentation",
            "observed_priority": "P1",
            "observed_at": "2026-08-04T23:18:27Z",
            "source": "GITHUB_ISSUE_AND_PROJECT_METADATA",
        },
        "expected_post_merge_finalization": {
            "state": "CLOSED",
            "status": "Done",
            "gate_decision": "INCONCLUSIVE",
            "authorization": "Completed",
            "phase": "Phase 1B-D1",
            "work_type": "Documentation",
            "priority": "P1",
        },
        "lifecycle_semantics": {
            "inventory_snapshot_is_historical": True,
            "post_merge_state_is_not_repository_validated": True,
            "offline_validator_can_verify_live_github_state": False,
            "post_merge_authorization_is_workflow_completion_not_scientific_authorization": True,
        },
    },
    "issue_10": {
        "number": 10,
        "expected_state": "OPEN",
        "expected_status": "Blocked",
        "expected_gate_decision": "Not Evaluated",
        "expected_authorization": "Not Authorized",
        "source": "PROJECT_POLICY_SNAPSHOT",
        "offline_validator_can_verify_live_github_state": False,
    },
}

ROADMAP_STATE = {
    "D2": "Blocked",
    "D3": "Backlog",
    "D4": "Backlog",
    "D5": "Backlog",
    "active_supersession": False,
    "next_phase_selected": False,
}

ACTIVE_POLICY = {
    "ACTIVE_OPERATIONAL_POLICY": "PAUSE_GENERATOR_COUPLING_WITHOUT_AUTHORIZATION",
    "CURRENT_FULL_GENERATOR_LINE": "PAUSED_NO_BOUNDED_CONTINUATION_ESTABLISHED",
    "preferred_scientific_candidate": None,
    "active_scientific_candidate": None,
    "implementation_next_step": None,
    "maintenance_next_action": "PRESERVE_ACCEPTED_EVIDENCE_AND_PAUSE",
    "pause_claims_pdf_sbi_impossible": False,
}

REOPEN_CONDITIONS = (
    {
        "condition_id": "PREFERENCE_CRITICAL_EVIDENCE_CLOSED",
        "condition": "New primary or mathematical evidence closes normalized-measure, posterior, no-hidden-repair, and composite-MVP gaps for a candidate.",
        "authorization_granted": False,
    },
    {
        "condition_id": "BOUNDED_ARCHITECTURE_INDEPENDENTLY_REVIEWED",
        "condition": "An independently reviewed generator or inference architecture provides a bounded and falsifiable path.",
        "authorization_granted": False,
    },
    {
        "condition_id": "SCIENTIFIC_CONTRACT_CHANGE_ACCEPTED",
        "condition": "A separate review accepts a change to the scientific contract.",
        "authorization_granted": False,
    },
    {
        "condition_id": "USER_TERMINATES_OR_REDIRECTS_OBJECTIVE",
        "condition": "An explicit user decision terminates or redirects the research objective.",
        "authorization_granted": False,
    },
)

VALIDATION_RECORD = {
    "scope": "IDENTITY_ANCESTRY_AND_POLICY_CONSISTENCY_ONLY",
    "offline": True,
    "artifact_count": len(ARTIFACT_SPECS),
    "adr_count": len(ADR_SPECS),
    "merge_lineage_count": len(MERGE_LINEAGE),
    "validator_proves": [
        "repository artifact and ADR byte identities",
        "local Git commit and parent relationships",
        "frozen repository policy consistency",
        "integrity of the recorded external-state snapshot and expected lifecycle fields",
    ],
    "validator_does_not_prove": [
        "live GitHub issue state",
        "live GitHub Project fields",
        "live PR metadata",
        "external branch-head availability after deletion",
        "scientific correctness beyond accepted record consistency",
    ],
    "historical_artifacts_regenerated": False,
    "offline_validator_contacted_internet": False,
    "github_metadata_was_used_to_construct_inventory": True,
    "physics_libraries_executed": False,
}

TOP_LEVEL_KEYS = {
    "schema_version",
    "generated_from_main",
    "scientific_objective",
    "accepted_decisions",
    "accepted_artifacts",
    "accepted_adrs",
    "merge_lineage",
    "issue_state",
    "roadmap_state",
    "active_policy",
    "authorization",
    "reopen_conditions",
    "validation",
}


class CloseoutValidationError(RuntimeError):
    """Raised when the closeout identity or policy contract is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CloseoutValidationError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "generated_from_main": {
            "commit_sha": GENERATED_FROM_MAIN,
            "tree_sha": GENERATED_FROM_TREE,
            "branch": "main",
            "worktree_clean_when_inventoried": True,
        },
        "scientific_objective": copy.deepcopy(SCIENTIFIC_OBJECTIVE),
        "accepted_decisions": copy.deepcopy(ACCEPTED_DECISIONS),
        "accepted_artifacts": copy.deepcopy(list(ARTIFACT_SPECS)),
        "accepted_adrs": [
            {"path": path, "status": status, "sha256": digest, "immutable": True}
            for path, status, digest in ADR_SPECS
        ],
        "merge_lineage": copy.deepcopy(list(MERGE_LINEAGE)),
        "issue_state": copy.deepcopy(ISSUE_STATE),
        "roadmap_state": copy.deepcopy(ROADMAP_STATE),
        "active_policy": copy.deepcopy(ACTIVE_POLICY),
        "authorization": {flag: False for flag in AUTHORIZATION_FLAGS},
        "reopen_conditions": copy.deepcopy(list(REOPEN_CONDITIONS)),
        "validation": copy.deepcopy(VALIDATION_RECORD),
    }


def serialized(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        text=True,
        capture_output=True,
    )


def is_shallow_repository(repo: Path) -> bool:
    return git(repo, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"


def _adr_status(text: str) -> str | None:
    for line in text.splitlines():
        normalized = line.removeprefix("- ")
        if normalized.startswith("Status:"):
            return normalized.split(":", 1)[1].strip()
    return None


def _artifact_by_path(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = manifest["accepted_artifacts"]
    require(isinstance(rows, list), "accepted_artifacts must be a list")
    require(all(isinstance(row, dict) and "path" in row for row in rows), "artifact record lacks path")
    paths = [row["path"] for row in rows]
    require(len(paths) == len(set(paths)), "duplicate artifact path")
    return {row["path"]: row for row in rows}


def _validate_historical_payloads(repo: Path) -> None:
    def load(path: str) -> dict[str, Any]:
        return json.loads((repo / path).read_text(encoding="utf-8"))

    require(load("docs/phase1a_strict_support_decision.json")["decision"] == ACCEPTED_DECISIONS["PHASE1A_FINAL_DECISION"], "Phase 1A decision changed")
    require(load("docs/phase1bd_d0_decision.json")["decision"] == "FAIL", "original D0 FAIL changed")
    require(load("docs/phase1bd_d0r_decision.json")["stage0_decision"] == "PASS", "D0R PASS changed")
    require(load("docs/phase1bd_d1_decision.json")["stage1_decision"] == "FAIL", "original D1 FAIL changed")
    require(load("docs/phase1bd_d1r_decision.json")["revised_stage1_decision"] == "FAIL", "D1R FAIL changed")
    require(load("docs/phase1bd_d1a_architecture_decision.json")["architecture_decision"] == "INCONCLUSIVE", "D1A architecture decision changed")
    require(load("docs/phase1bd_d1a_prototype_decision.json")["decision"] == "INCONCLUSIVE", "D1A prototype decision changed")
    require(load("docs/phase1bd_d1b_decision.json")["decision"] == "AUTHORIZE_SEPARATE_BOUNDED_PROTOTYPE", "D1B historical decision changed")
    require(load("docs/phase1bd_d1c_decision.json")["decision"] == "FAIL", "D1C FAIL changed")
    require(load("docs/phase1bd_d1d_pythia_provenance_slice_decision.json")["decision"] == "FAIL", "D1D-A provenance decision changed")
    require(load("docs/phase1bd_d1d_pythia_semantics_audit.json")["d1d_a_final_decision"] == "FAIL", "D1D-A final decision changed")
    require(load("docs/phase1bd_d1d_terminal_decision.json")["decision"] == "INCONCLUSIVE", "D1D-B decision changed")
    require(load("docs/phase1bd_d1e_consumer_graph_feasibility.json")["decision"] == "INCONCLUSIVE", "D1E decision changed")
    require(load("docs/phase1bd_d1f_active_contract_decision.json")["decision"] == ACCEPTED_DECISIONS["D1F_FINAL_DECISION"], "D1F pause changed")
    d1g = load("docs/phase1bd_d1g_independent_contract_priority.json")
    require(d1g["decision"] == ACCEPTED_DECISIONS["D1G_FINAL_DECISION"], "D1G pause changed")
    require(d1g["derived_decision_inputs"]["eligible_candidates"] == [], "D1G eligible candidates changed")


def validate_manifest(manifest: dict[str, Any], repo: Path, *, verify_git: bool = True) -> None:
    require(set(manifest) == TOP_LEVEL_KEYS, "manifest top-level schema changed")
    require(manifest["schema_version"] == SCHEMA, "closeout schema mismatch")
    require(manifest["generated_from_main"] == build_manifest()["generated_from_main"], "generated-from-main identity changed")
    require(manifest["scientific_objective"] == SCIENTIFIC_OBJECTIVE, "scientific objective changed")
    require(manifest["accepted_decisions"] == ACCEPTED_DECISIONS, "accepted decision ledger changed")

    records = _artifact_by_path(manifest)
    expected = {row["path"]: row for row in ARTIFACT_SPECS}
    require(set(records) == set(expected), "required accepted artifact missing or added")
    hashes = []
    for path, expected_row in expected.items():
        row = records[path]
        require(row == expected_row, f"accepted artifact metadata changed: {path}")
        artifact_path = repo / path
        require(artifact_path.is_file(), f"accepted artifact missing: {path}")
        require(sha256_file(artifact_path) == row["sha256"], f"artifact SHA-256 mismatch: {path}")
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        require(payload.get("schema_version") == row["schema"], f"artifact schema mismatch: {path}")
        require(row["immutable"] is True, f"artifact not immutable: {path}")
        require(row["superseded"] is False and row["superseded_by"] is None, f"historical result represented as superseded: {path}")
        hashes.append(row["sha256"])
    require(len(hashes) == len(set(hashes)), "duplicate artifact byte identity")

    failed_paths = {
        "docs/phase1a_strict_support_decision.json",
        "docs/phase1bd_d0_decision.json",
        "docs/phase1bd_d1_decision.json",
        "docs/phase1bd_d1r_decision.json",
        "docs/phase1bd_d1c_decision.json",
        "docs/phase1bd_d1d_pythia_provenance_slice_decision.json",
        "docs/phase1bd_d1d_pythia_semantics_audit.json",
    }
    require(failed_paths <= set(records), "historical FAIL result deleted")
    require(records["docs/phase1bd_d0_decision.json"]["superseded"] is False, "D0R represented as replacing D0")
    require(records["docs/phase1bd_d1_decision.json"]["superseded"] is False, "D1R represented as replacing D1")
    _validate_historical_payloads(repo)

    expected_adrs = [
        {"path": path, "status": status, "sha256": digest, "immutable": True}
        for path, status, digest in ADR_SPECS
    ]
    require(manifest["accepted_adrs"] == expected_adrs, "accepted ADR ledger changed")
    for row in manifest["accepted_adrs"]:
        path = repo / row["path"]
        require(path.is_file(), f"ADR missing: {row['path']}")
        require(sha256_file(path) == row["sha256"], f"ADR SHA-256 mismatch: {row['path']}")
        require(_adr_status(path.read_text(encoding="utf-8")) == row["status"], f"ADR status mismatch: {row['path']}")

    require(manifest["merge_lineage"] == list(MERGE_LINEAGE), "accepted PR merge lineage or provenance changed")
    require({row["pr_number"] for row in manifest["merge_lineage"]} == {40, 41, 43, 44, 46, 48, 50}, "accepted PR lineage entry omitted")
    for row in manifest["merge_lineage"]:
        require(row["metadata_source"] == "LOCAL_GIT_AND_GITHUB_PR_METADATA", f"merge metadata source changed: PR #{row['pr_number']}")
        if row["merge_method"] == "SQUASH":
            require(row["reviewed_branch_head_source"] == "GITHUB_PR_METADATA", f"squash head lacks GitHub provenance: PR #{row['pr_number']}")
            require(row["reviewed_branch_head_offline_ancestry_verifiable"] is False, f"squash head incorrectly claimed offline-verifiable: PR #{row['pr_number']}")
            require(row["squash_commit_parentage_offline_verifiable"] is True, f"squash commit parentage marked non-verifiable: PR #{row['pr_number']}")
        else:
            require(row["reviewed_branch_head_offline_ancestry_verifiable"] is True, f"merge head ancestry marked non-verifiable: PR #{row['pr_number']}")
            require(row["merge_commit_parentage_offline_verifiable"] is True, f"merge-commit parentage marked non-verifiable: PR #{row['pr_number']}")
    if verify_git:
        require(not is_shallow_repository(repo), "full local Git history required for lineage validation")
        require(git(repo, "cat-file", "-e", f"{GENERATED_FROM_MAIN}^{{commit}}", check=False).returncode == 0, "generated main commit missing")
        require(git(repo, "rev-parse", f"{GENERATED_FROM_MAIN}^{{tree}}").stdout.strip() == GENERATED_FROM_TREE, "generated main tree changed")
        require(git(repo, "merge-base", "--is-ancestor", GENERATED_FROM_MAIN, "HEAD", check=False).returncode == 0, "generated main is not an ancestor of HEAD")
        for row in manifest["merge_lineage"]:
            merge_commit = row["merge_commit"]
            require(git(repo, "cat-file", "-e", f"{merge_commit}^{{commit}}", check=False).returncode == 0, f"merge commit missing: PR #{row['pr_number']}")
            parents = git(repo, "rev-list", "--parents", "-n", "1", merge_commit).stdout.strip().split()
            recorded = [merge_commit, row["first_parent"]] + ([row["second_parent"]] if row["second_parent"] else [])
            require(parents == recorded, f"merge parents changed: PR #{row['pr_number']}")
            require(git(repo, "merge-base", "--is-ancestor", merge_commit, GENERATED_FROM_MAIN, check=False).returncode == 0, f"merge not in accepted main ancestry: PR #{row['pr_number']}")
            if row["reviewed_branch_commits_preserved"]:
                require(row["merge_method"] == "MERGE_COMMIT" and row["second_parent"] == row["reviewed_branch_head"], f"preserved merge contract changed: PR #{row['pr_number']}")
            else:
                require(row["merge_method"] == "SQUASH" and row["second_parent"] is None, f"historical squash contract changed: PR #{row['pr_number']}")

    issue_state = manifest["issue_state"]
    require("closeout_issue" not in issue_state, "issue #51 represented as timeless current state")
    require(issue_state == ISSUE_STATE, "issue #10 boundary or closeout lifecycle changed")
    workflow = issue_state["closeout_workflow"]
    require(workflow["inventory_snapshot"]["observed_at"], "issue #51 inventory timestamp missing")
    require(workflow["inventory_snapshot"]["source"] == "GITHUB_ISSUE_AND_PROJECT_METADATA", "issue #51 snapshot source changed")
    require(workflow["expected_post_merge_finalization"]["state"] == "CLOSED", "expected issue #51 post-merge close state missing")
    require(workflow["expected_post_merge_finalization"]["authorization"] == "Completed", "issue #51 lifecycle grants or misstates authorization")
    require(workflow["lifecycle_semantics"]["offline_validator_can_verify_live_github_state"] is False, "offline validator claims live GitHub verification")
    require(workflow["lifecycle_semantics"]["post_merge_authorization_is_workflow_completion_not_scientific_authorization"] is True, "workflow completion confused with scientific authorization")
    require(issue_state["issue_10"] == ISSUE_STATE["issue_10"], "issue #10 active expected boundary changed")
    require(issue_state["issue_10"]["source"] == "PROJECT_POLICY_SNAPSHOT", "issue #10 represented only as historical observation")
    require(manifest["roadmap_state"] == ROADMAP_STATE, "D2-D5 roadmap state changed")
    require(manifest["active_policy"] == ACTIVE_POLICY, "active pause or candidate selection changed")
    require(manifest["active_policy"]["preferred_scientific_candidate"] is None, "scientific candidate selected")
    require(manifest["active_policy"]["implementation_next_step"] is None, "implementation next step selected")
    require(manifest["authorization"] == {flag: False for flag in AUTHORIZATION_FLAGS}, "authorization flag became true")
    require(manifest["reopen_conditions"] == list(REOPEN_CONDITIONS), "reopen conditions changed")
    require(all(row["authorization_granted"] is False for row in manifest["reopen_conditions"]), "reopen condition grants authorization")
    validation = manifest["validation"]
    require("internet_contacted" not in validation, "ambiguous whole-process internet claim restored")
    require(validation == VALIDATION_RECORD, "validation scope or aggregate changed")
    require(validation["offline_validator_contacted_internet"] is False, "offline validator internet scope changed")
    require(validation["github_metadata_was_used_to_construct_inventory"] is True, "GitHub inventory provenance denied")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    path = repo / MANIFEST_PATH
    require(path.is_file(), f"missing manifest: {MANIFEST_PATH}")
    text = path.read_text(encoding="utf-8")
    manifest = json.loads(text)
    validate_manifest(manifest, repo, verify_git=True)
    require(text == serialized(manifest), "manifest serialization is not canonical pretty JSON")
    print(
        f"VALID {SCHEMA} artifacts={len(manifest['accepted_artifacts'])} "
        f"adrs={len(manifest['accepted_adrs'])} lineage={len(manifest['merge_lineage'])}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CloseoutValidationError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
