#!/usr/bin/env bash
# Activate the repository-local HepMC3, PYTHIA 8, and structure function backends in WSL.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    printf 'error: source this file instead of executing it\n' >&2
    exit 1
fi

_pythia_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
_pythia_repo_root="$(cd -- "${_pythia_script_dir}/.." && pwd -P)"

# Activate APFEL++ and LHAPDF environment first.
# shellcheck source=scripts/apfelxx_env.sh
source "${_pythia_script_dir}/apfelxx_env.sh"

export HEPMC3_ROOT="${HEPMC3_ROOT:-${_pythia_repo_root}/.external/hepmc3-3.3.0}"
export PYTHIA8_ROOT="${PYTHIA8_ROOT:-${_pythia_repo_root}/.external/pythia-8.3.12}"
export PYTHIA_BACKEND_BIN="${PYTHIA_BACKEND_BIN:-${_pythia_repo_root}/physics-engine/build/pythia_dis_cli}"

# Path updates
_pythia_prepend_path() {
    local variable_name="$1"
    local entry="$2"
    local current_value="${!variable_name-}"

    case ":${current_value}:" in
        *":${entry}:"*)
            ;;
        *)
            if [[ -n "${current_value}" ]]; then
                printf -v "${variable_name}" '%s:%s' "${entry}" "${current_value}"
            else
                printf -v "${variable_name}" '%s' "${entry}"
            fi
            ;;
    esac
    export "${variable_name}"
}

_pythia_prepend_path PATH "${PYTHIA8_ROOT}/bin"
_pythia_prepend_path PATH "${HEPMC3_ROOT}/bin"

_pythia_prepend_path LD_LIBRARY_PATH "${PYTHIA8_ROOT}/lib"
_pythia_prepend_path LD_LIBRARY_PATH "${HEPMC3_ROOT}/lib"
if [[ -d "${HEPMC3_ROOT}/lib64" ]]; then
    _pythia_prepend_path LD_LIBRARY_PATH "${HEPMC3_ROOT}/lib64"
fi

_pythia_prepend_path CMAKE_PREFIX_PATH "${PYTHIA8_ROOT}"
_pythia_prepend_path CMAKE_PREFIX_PATH "${HEPMC3_ROOT}"

unset -f _pythia_prepend_path
unset _pythia_script_dir _pythia_repo_root
