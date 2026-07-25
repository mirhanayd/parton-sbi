#!/usr/bin/env bash
# Activate the repository-local APFEL++ installation and native backend in WSL.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    printf 'error: source this file instead of executing it\n' >&2
    exit 1
fi

_apfel_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
_apfel_repo_root="$(cd -- "${_apfel_script_dir}/.." && pwd -P)"

# LHAPDF must be activated before APFEL++ and the subprocess backend.
# shellcheck source=scripts/lhapdf_env.sh
source "${_apfel_script_dir}/lhapdf_env.sh"

export APFELXX_ROOT="${APFELXX_ROOT:-${_apfel_repo_root}/.external/apfelxx-4.8.0}"
export APFEL_BACKEND_BIN="${APFEL_BACKEND_BIN:-${_apfel_repo_root}/physics-engine/build/apfel_cli}"

case ":${PATH}:" in
    *":${APFELXX_ROOT}/bin:"*) ;;
    *) export PATH="${APFELXX_ROOT}/bin:${PATH}" ;;
esac

case ":${LD_LIBRARY_PATH:-}:" in
    *":${APFELXX_ROOT}/lib:"*) ;;
    *) export LD_LIBRARY_PATH="${APFELXX_ROOT}/lib${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}" ;;
esac

case ":${CMAKE_PREFIX_PATH:-}:" in
    *":${APFELXX_ROOT}:"*) ;;
    *) export CMAKE_PREFIX_PATH="${APFELXX_ROOT}${CMAKE_PREFIX_PATH:+:${CMAKE_PREFIX_PATH}}" ;;
esac

unset _apfel_script_dir _apfel_repo_root
