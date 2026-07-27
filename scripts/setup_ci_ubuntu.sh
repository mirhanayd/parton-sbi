#!/usr/bin/env bash
# Install pinned PartonSBI native dependencies on GitHub-hosted Ubuntu runners.

set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
readonly EXTERNAL_ROOT="${REPO_ROOT}/.external"
readonly LHAPDF_PREFIX="${EXTERNAL_ROOT}/lhapdf-6.5.6"
readonly LHAPDF_DATA_DIR="${LHAPDF_PREFIX}/share/LHAPDF"

# shellcheck source=scripts/platform_policy.sh
source "${SCRIPT_DIR}/platform_policy.sh"

usage() {
    cat <<'EOF'
Usage: scripts/setup_ci_ubuntu.sh [--check-platform]

Install the pinned PartonSBI native dependencies on a GitHub Actions Ubuntu
runner. --check-platform performs no installation and reports how the current
environment is classified.
EOF
}

check_platform_only=false
case "${1:-}" in
    "") ;;
    --check-platform) check_platform_only=true ;;
    -h | --help)
        usage
        exit 0
        ;;
    *)
        printf 'error: unknown option: %s\n' "$1" >&2
        usage >&2
        exit 2
        ;;
esac
(($# <= 1)) || {
    printf 'error: too many arguments\n' >&2
    exit 2
}

partonsbi_require_ubuntu_linux
if [[ "${check_platform_only}" == true ]]; then
    if partonsbi_is_wsl; then
        printf '%s\n' \
            "platform check: WSL Ubuntu detected; native CI setup would be rejected"
    elif [[ "${CI:-}" == "true" && "${GITHUB_ACTIONS:-}" == "true" ]]; then
        printf '%s\n' \
            "platform check: native Ubuntu GitHub Actions environment detected"
    else
        printf '%s\n' \
            "platform check: native Ubuntu detected without GitHub Actions markers"
    fi
    exit 0
fi

export PARTONSBI_NATIVE_UBUNTU_CI=1
partonsbi_require_native_ubuntu_ci

[[ -n "${GITHUB_ENV:-}" ]] || {
    printf 'error: GITHUB_ENV is unavailable\n' >&2
    exit 1
}
[[ -n "${GITHUB_PATH:-}" ]] || {
    printf 'error: GITHUB_PATH is unavailable\n' >&2
    exit 1
}

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
    build-essential \
    ca-certificates \
    cmake \
    curl \
    dpkg-dev \
    gfortran \
    git \
    pkg-config

export LHAPDF_PREFIX LHAPDF_DATA_DIR

printf '%s\n' "==> Installing LHAPDF 6.5.6 in ${LHAPDF_PREFIX}"
bash "${SCRIPT_DIR}/setup_lhapdf_wsl.sh" \
    --prefix "${LHAPDF_PREFIX}" \
    --data-dir "${LHAPDF_DATA_DIR}"

# The LHAPDF child process cannot update this shell.
# shellcheck source=scripts/lhapdf_env.sh
source "${SCRIPT_DIR}/lhapdf_env.sh"

printf '%s\n' "==> Installing HepMC3 3.3.0"
bash "${SCRIPT_DIR}/setup_hepmc3_wsl.sh" --external-root "${EXTERNAL_ROOT}"

printf '%s\n' "==> Installing PYTHIA 8.312"
bash "${SCRIPT_DIR}/setup_pythia8_wsl.sh" --external-root "${EXTERNAL_ROOT}"

printf '%s\n' "==> Installing APFEL++ 4.8.0 and building native backends"
bash "${SCRIPT_DIR}/setup_apfelxx_wsl.sh" \
    --external-root "${EXTERNAL_ROOT}" \
    --engine-build "${REPO_ROOT}/physics-engine/build"

# Derive the complete runtime/build environment from the authoritative helper.
# shellcheck source=scripts/pythia_env.sh
source "${SCRIPT_DIR}/pythia_env.sh"

[[ "$(lhapdf-config --version)" == "6.5.6" ]]
[[ "$(apfelxx-config --version | tr -d '[:space:]')" == "4.8.0" ]]
[[ -x "${PYTHIA8_ROOT}/bin/pythia8-config" ]]
[[ -x "${HEPMC3_ROOT}/bin/HepMC3-config" || -x "${HEPMC3_ROOT}/bin/hepmc3-config" ]]
[[ -x "${APFEL_BACKEND_BIN}" ]]
[[ -x "${PYTHIA_BACKEND_BIN}" ]]

append_github_env() {
    local name="$1"
    local value="${!name-}"
    [[ "${value}" != *$'\n'* ]] || {
        printf 'error: %s contains a newline\n' "${name}" >&2
        return 1
    }
    printf '%s=%s\n' "${name}" "${value}" >>"${GITHUB_ENV}"
}

for variable_name in \
    LHAPDF_PREFIX LHAPDF_DATA_DIR LHAPDF_DATA_PATH \
    APFELXX_ROOT NLOHMANN_JSON_INCLUDE_DIR \
    PYTHIA8_ROOT PYTHIA8DATA HEPMC3_ROOT \
    CMAKE_PREFIX_PATH LD_LIBRARY_PATH PKG_CONFIG_PATH \
    APFEL_BACKEND_BIN PYTHIA_BACKEND_BIN; do
    append_github_env "${variable_name}"
done

for path_entry in \
    "${LHAPDF_PREFIX}/bin" \
    "${APFELXX_ROOT}/bin" \
    "${PYTHIA8_ROOT}/bin" \
    "${HEPMC3_ROOT}/bin"; do
    printf '%s\n' "${path_entry}" >>"${GITHUB_PATH}"
done

printf '%s\n' "Native Ubuntu CI dependency setup complete."

