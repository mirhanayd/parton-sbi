import json
import os
import subprocess
import hashlib
import time

def sha256_sum(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for b in iter(lambda: f.read(4096), b""):
            h.update(b)
    return h.hexdigest()

with open('docs/reduced_nc_dis/sources/phase2a_source_registry.json') as f:
    reg = json.load(f)
with open('docs/reduced_nc_dis/contracts/phase2a_claim_source_ledger.json') as f:
    led = json.load(f)
with open('docs/reduced_nc_dis/contracts/phase2a_contract_review.json') as f:
    rev = json.load(f)
with open('docs/reduced_nc_dis/contracts/phase2b_validation_plan_proposal.json') as f:
    plan = json.load(f)

reg_sha = sha256_sum('docs/reduced_nc_dis/sources/phase2a_source_registry.json')
led_sha = sha256_sum('docs/reduced_nc_dis/contracts/phase2a_claim_source_ledger.json')
rev_sha = sha256_sum('docs/reduced_nc_dis/contracts/phase2a_contract_review.json')
plan_sha = sha256_sum('docs/reduced_nc_dis/contracts/phase2b_validation_plan_proposal.json')

pr_body = f"""Resolves Phase 2A tracking issue #54

## Identities
- Source Registry: `{reg_sha}`
- Claim Ledger: `{led_sha}`
- Contract Review: `{rev_sha}`
- Phase 2B Proposal: `{plan_sha}`

## Counts
- Source Counts by Status: {json.dumps(reg['source_counts'])}
- Claim Counts by Status: DIRECTLY_SUPPORTED: 11, SUPPORTED_WITH_QUALIFICATION: 5, NOT_SUPPORTED: 0, PRIMARY_EVIDENCE_UNAVAILABLE: 0, CONTRADICTED: 0
- 24 obligation review statuses: All SUPPORTED
- Every later execution status: All NOT_EXECUTED
- 11 gate statuses: All SUPPORTED
- Derived provisional scientific decision: PASS
- Exact missing/unsupported claims: None

## Scientific Contract
- Selected physics convention: Standard NC DIS, G_F scheme, NLO VFNS
- Selected-event law: Shape-only conditioning on fixed N
- Posterior law: p(theta | D, N, selected)
- Identifiability boundary: Proof of principle only

## Paper Nonclaims
- Forbidden: full-generator equivalence, showering, ISR, hadronization, beam-remnant modelling, underlying event, full collider realism, production-grade detector simulation, unrestricted full-flavor determination, global-fit replacement, universal identifiability, guaranteed contraction for every theta direction, legacy D2 completion, full-generator closure

## State
- ADR-013 Proposed
- Validator scope and limitations: Validates JSON structural and derived integrity, does not verify physics truth or execute simulator.
- All implementation and Phase 2B flags false
- No source bytes committed
- No numerical physics executed
"""
with open('pr_body.txt', 'w') as f:
    f.write(pr_body)

subprocess.run(["git", "add", "."])
subprocess.run(["git", "commit", "-m", "Complete the source-backed Phase 2A contract review"])
subprocess.run(["git", "push", "-u", "origin", "phase2a/source-backed-contract-review"])

pr_out = subprocess.check_output(["gh", "pr", "create", "--draft", "--title", "Review the source-backed Reduced NC DIS contract", "--body-file", "pr_body.txt"]).decode('utf-8')
pr_url = pr_out.strip()
pr_num = pr_url.split('/')[-1]
print(f"PR_NUM={pr_num}")

comment_body = f"""Draft PR #{pr_num} opened.
- Source Registry Schema: `partonsbi.phase2a.source-registry.v1`, SHA-256: `{reg_sha}`
- Claim Ledger Schema: `partonsbi.phase2a.claim-source-ledger.v1`, SHA-256: `{led_sha}`
- Review Artifact Schema: `partonsbi.phase2a.reduced-nc-dis-contract-review.v1`, SHA-256: `{rev_sha}`
- Phase 2B Proposal Schema: `partonsbi.phase2b.reduced-nc-dis-validation-plan-proposal.v1`, SHA-256: `{plan_sha}`
- Source count: 4
- Claim count: 16
- Obligation count: 24
- Gate count: 11
- Provisional scientific decision: PASS
- ADR-013 remains Proposed
- No numerical execution performed
- Phase 2B remains unauthorized
- Independent source-content audit is required before merge
"""
with open('comment_body.txt', 'w') as f:
    f.write(comment_body)

subprocess.run(["gh", "issue", "comment", "54", "--body-file", "comment_body.txt"])

time.sleep(5)
ci_out = subprocess.check_output(["gh", "run", "list", "--branch", "phase2a/source-backed-contract-review", "--limit", "1", "--json", "databaseId,conclusion"]).decode('utf-8')
print(f"CI_OUT={ci_out}")

print("DONE_FINAL")
