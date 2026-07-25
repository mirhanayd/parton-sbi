#!/usr/bin/env bash
# Orchestrates the setup of all external physics dependencies for quark_sim.
# Ensures the exact order of operations: LHAPDF -> HepMC3 -> Pythia 8 -> APFEL++ & backend.

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
readonly REPO_ROOT="$(dirname "${SCRIPT_DIR}")"

# Define ANSI color codes for readable logging
readonly GREEN='\033[0;32m'
readonly BLUE='\033[0;34m'
readonly RED='\033[0;31m'
readonly NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}==>${NC} ${GREEN}$1${NC}"
}

log_error() {
    echo -e "${RED}ERROR:${NC} $1" >&2
}

cd "${REPO_ROOT}"

log_info "Starting full WSL setup for quark_sim environment..."

# 1. LHAPDF
log_info "Step 1/4: Installing LHAPDF..."
"${SCRIPT_DIR}/setup_lhapdf_wsl.sh"

# 2. HepMC3
log_info "Step 2/4: Installing HepMC3..."
"${SCRIPT_DIR}/setup_hepmc3_wsl.sh"

# 3. Pythia 8
log_info "Step 3/4: Installing Pythia 8..."
"${SCRIPT_DIR}/setup_pythia8_wsl.sh"

# 4. APFEL++ and JSON C++ backend
log_info "Step 4/4: Installing APFEL++ and building physics backend..."
"${SCRIPT_DIR}/setup_apfelxx_wsl.sh"

log_info "All external physics dependencies successfully installed!"
log_info "Run the following to initialize the active environment:"
log_info "  source \"${SCRIPT_DIR}/apfelxx_env.sh\""
