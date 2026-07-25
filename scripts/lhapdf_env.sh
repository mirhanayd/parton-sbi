#!/usr/bin/env bash
#
# Source this file from WSL before building or running the LHAPDF-backed code:
#
#   source scripts/lhapdf_env.sh
#
# Override LHAPDF_PREFIX and/or LHAPDF_DATA_DIR before sourcing when a
# non-default installation location is used.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    printf '%s\n' "This helper must be sourced: source scripts/lhapdf_env.sh" >&2
    exit 2
fi

if [[ -z "${LHAPDF_PREFIX:-}" ]]; then
    if [[ -z "${HOME:-}" ]]; then
        printf '%s\n' "LHAPDF_PREFIX is unset and HOME is unavailable." >&2
        return 1
    fi
    LHAPDF_PREFIX="${HOME}/.local/lhapdf-6.5.6"
fi

LHAPDF_DATA_DIR="${LHAPDF_DATA_DIR:-${LHAPDF_PREFIX}/share/LHAPDF}"

_lhapdf_prepend_path() {
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

_lhapdf_prepend_path PATH "${LHAPDF_PREFIX}/bin"
_lhapdf_prepend_path PKG_CONFIG_PATH "${LHAPDF_PREFIX}/lib/pkgconfig"
if [[ -d "${LHAPDF_PREFIX}/lib64/pkgconfig" ]]; then
    _lhapdf_prepend_path PKG_CONFIG_PATH "${LHAPDF_PREFIX}/lib64/pkgconfig"
fi
_lhapdf_prepend_path LD_LIBRARY_PATH "${LHAPDF_PREFIX}/lib"
if [[ -d "${LHAPDF_PREFIX}/lib64" ]]; then
    _lhapdf_prepend_path LD_LIBRARY_PATH "${LHAPDF_PREFIX}/lib64"
fi
_lhapdf_prepend_path LHAPDF_DATA_PATH "${LHAPDF_DATA_DIR}"

export LHAPDF_PREFIX LHAPDF_DATA_DIR

unset -f _lhapdf_prepend_path
