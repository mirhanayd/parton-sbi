# Environment

- Use only WSL Ubuntu for local commands.
- Source `scripts/pythia_env.sh` before native physics validation.
- Do not use PowerShell, CMD, Git Bash, or native Windows builds.

# Scientific objective

The inference unit is a set of events:

```text
D = {event_1, ..., event_N}
```

The long-term target is:

```text
p(theta_PDF | D)
```

Never describe the objective as determining the instantaneous PDF of one proton from one event.

# Scientific constraints

- Do not claim full flavor separation from one inclusive NC e-p channel.
- Treat hard flavor and GenPdfInfo as provenance/reweighting truth.
- Do not expose generator-only truth as default observed ML features.
- Do not hide closure, calibration, ESS, support, or coverage failures.
- A negative scientific result is valid.
- Do not begin later roadmap phases before current acceptance criteria pass.

# Development constraints

- Make phase-scoped changes.
- Do not perform unrelated refactors.
- Do not weaken, delete, or ignore tests to produce a green build.
- Do not commit generated event pools or local environments.
- Preserve seed and run provenance.
- Document every scientific approximation.

# Required validation

Where relevant:

```bash
source scripts/pythia_env.sh
cargo fmt --all -- --check
cargo check --workspace
cargo test --workspace
ctest --test-dir physics-engine/build --output-on-failure
git diff --check
```

# Completion requirements

- Write a phase completion report.
- Record exact commands.
- Record pass/fail results.
- Record unresolved scientific limitations.
- State one next step.
- Do not implement the next phase in the same task.
