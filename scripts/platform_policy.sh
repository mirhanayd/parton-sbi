#!/usr/bin/env bash
# Shared platform gates for PartonSBI dependency installers.
# This file is sourced; it is not an installation entry point.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    printf 'error: source this helper from a PartonSBI setup script\n' >&2
    exit 2
fi

partonsbi_platform_error() {
    printf 'error: %s\n' "$*" >&2
    return 1
}

partonsbi_require_ubuntu_linux() {
    [[ "$(uname -s)" == "Linux" ]] ||
        partonsbi_platform_error "dependency setup supports Linux only"
    [[ -r /etc/os-release ]] ||
        partonsbi_platform_error "/etc/os-release is unavailable"

    # shellcheck disable=SC1091
    source /etc/os-release
    [[ "${ID:-}" == "ubuntu" ]] ||
        partonsbi_platform_error \
            "dependency setup supports Ubuntu; detected ${PRETTY_NAME:-unknown}"
}

partonsbi_is_wsl() {
    [[ -r /proc/sys/kernel/osrelease ]] &&
        grep -qi microsoft /proc/sys/kernel/osrelease
}

partonsbi_require_wsl_ubuntu() {
    partonsbi_require_ubuntu_linux
    partonsbi_is_wsl ||
        partonsbi_platform_error "this installer is restricted to WSL Ubuntu"
}

partonsbi_require_native_ubuntu_ci() {
    partonsbi_require_ubuntu_linux
    ! partonsbi_is_wsl ||
        partonsbi_platform_error \
            "native-Ubuntu CI setup must not run inside WSL; use setup_all_wsl.sh"
    [[ "${PARTONSBI_NATIVE_UBUNTU_CI:-}" == "1" ]] ||
        partonsbi_platform_error "PARTONSBI_NATIVE_UBUNTU_CI=1 is required"
    [[ "${CI:-}" == "true" ]] ||
        partonsbi_platform_error "CI=true is required for native-Ubuntu setup"
    [[ "${GITHUB_ACTIONS:-}" == "true" ]] ||
        partonsbi_platform_error \
            "GITHUB_ACTIONS=true is required for native-Ubuntu setup"
}

partonsbi_require_wsl_or_native_ci() {
    partonsbi_require_ubuntu_linux
    if partonsbi_is_wsl; then
        return 0
    fi
    partonsbi_require_native_ubuntu_ci
}

