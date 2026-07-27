#!/usr/bin/env bash
# Build a pinned PYTHIA 8 release in a repository-local prefix.
# Everything is installed below this repository's .external directory by default.

set -Eeuo pipefail

readonly PYTHIA_VERSION="8.312"
readonly PYTHIA_URL="https://gitlab.com/Pythia8/releases/-/archive/pythia8312/releases-pythia8312.tar.gz"
readonly PYTHIA_SHA256="c1a33aa5fa15e6b70d7946ce6d237246842887ec84ea0b35dfc2535c868a2770"

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

note() {
    printf '%s\n' "$*"
}

usage() {
    cat <<'EOF'
Usage: scripts/setup_pythia8_wsl.sh [OPTIONS]

Build PYTHIA 8.312 and install it to a repository-local directory.
No sudo command or system-library overwrite is used.

Options:
  --external-root PATH  Controlled dependency root (default: REPO/.external)
  --jobs N              Parallel build jobs (default: min(nproc, 4))
  -h, --help            Show this help
EOF
}

require_wsl_ubuntu() {
    [[ -r /proc/sys/kernel/osrelease ]] ||
        die "cannot inspect the kernel; run this script inside WSL Ubuntu"
    grep -qi microsoft /proc/sys/kernel/osrelease ||
        die "this installer is restricted to WSL"
    [[ -r /etc/os-release ]] || die "/etc/os-release is unavailable"

    # shellcheck disable=SC1091
    source /etc/os-release
    [[ "${ID:-}" == "ubuntu" ]] ||
        die "this installer supports WSL Ubuntu; detected ${PRETTY_NAME:-unknown}"
}

normalise_path() {
    local path="$1"
    [[ -n "${path}" ]] || die "paths must not be empty"
    [[ "${path}" == /* ]] || die "path must be absolute: ${path}"
    [[ "${path}" != *$'\n'* ]] || die "path must not contain a newline"
    path="$(readlink -m -- "${path}")"
    [[ "${path}" != "/" ]] || die "refusing to use the filesystem root"
    printf '%s\n' "${path}"
}

check_prerequisites() {
    local -a missing=()
    local command_name

    for command_name in apt awk cat make curl dirname \
        g++ gcc grep install nproc pkg-config readlink rm sed \
        sha256sum tar; do
        command -v "${command_name}" >/dev/null 2>&1 || missing+=("${command_name}")
    done

    if (("${#missing[@]}" > 0)); then
        printf 'error: missing required command(s): %s\n' "${missing[*]}" >&2
        cat >&2 <<'EOF'
Review and run the following inside WSL Ubuntu, then retry:

  sudo apt-get update
  sudo apt-get install --no-install-recommends build-essential curl pkg-config
EOF
        exit 1
    fi
}

verify_sha256() {
    local file="$1"
    local expected="$2"
    local label="$3"
    local actual
    actual="$(sha256sum -- "${file}" | awk '{print $1}')"
    [[ "${actual}" == "${expected}" ]] ||
        die "SHA-256 mismatch for ${label}: expected ${expected}, got ${actual}"
    note "Verified ${label} SHA-256: ${actual}"
}

download_pinned() {
    local url="$1"
    local destination="$2"
    local expected="$3"
    local label="$4"
    local temporary

    if [[ -f "${destination}" ]]; then
        verify_sha256 "${destination}" "${expected}" "${label}"
        return
    fi
    [[ ! -e "${destination}" ]] || die "download target is not a regular file: ${destination}"

    temporary="$(mktemp "${destination}.part.XXXXXX")"
    trap 'rm -f -- "${temporary:-}"' RETURN
    note "Downloading ${label} from its official endpoint..."
    curl --fail --show-error --silent --location --proto '=https' --tlsv1.2 \
        --retry 3 --retry-delay 2 --output "${temporary}" "${url}"
    [[ -s "${temporary}" ]] || die "${label} download is empty"
    verify_sha256 "${temporary}" "${expected}" "${label}"
    mv -- "${temporary}" "${destination}"
    trap - RETURN
}

validate_tar_archive() {
    local archive="$1"
    local expected_root="$2"
    local label="$3"
    local entry listing_line entry_type
    local count=0

    tar -tzf "${archive}" >/dev/null || die "${label} is not a readable tar.gz archive"
    while IFS= read -r entry; do
        count=$((count + 1))
        [[ -n "${entry}" ]] || die "${label} contains an empty path"
        case "${entry}" in
            /* | .. | ../* | */../* | */..) die "${label} contains unsafe path ${entry}" ;;
        esac
        [[ "${entry}" != *'\'* ]] || die "${label} contains a backslash path"
        case "${entry}" in
            "${expected_root}" | "${expected_root}"/*) ;;
            *) die "${label} contains a path outside ${expected_root}/: ${entry}" ;;
        esac
    done < <(LC_ALL=C tar -tzf "${archive}")
    ((count > 0)) || die "${label} archive is empty"

    while IFS= read -r listing_line; do
        [[ -n "${listing_line}" ]] || continue
        entry_type="${listing_line:0:1}"
        case "${entry_type}" in
            - | d) ;;
            *) die "${label} contains unsupported archive entry type ${entry_type}" ;;
        esac
    done < <(LC_ALL=C tar -tvzf "${archive}")
}

external_root="${REPO_ROOT}/.external"
jobs=""

while (($# > 0)); do
    case "$1" in
        --external-root)
            (($# >= 2)) || die "--external-root requires a path"
            external_root="$2"
            shift 2
            ;;
        --jobs)
            (($# >= 2)) || die "--jobs requires a positive integer"
            jobs="$2"
            shift 2
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *) die "unknown option: $1" ;;
    esac
done

external_root="$(normalise_path "${external_root}")"
if [[ -z "${jobs}" ]]; then
    detected_jobs="$(nproc)"
    ((detected_jobs < 4)) && jobs="${detected_jobs}" || jobs=4
fi
[[ "${jobs}" =~ ^[1-9][0-9]*$ ]] || die "build jobs must be a positive integer"

require_wsl_ubuntu
check_prerequisites

readonly DOWNLOAD_DIR="${external_root}/downloads"
readonly SOURCE_PARENT="${external_root}/src"
readonly SOURCE_DIR="${SOURCE_PARENT}/releases-pythia8312"
readonly PREFIX="${external_root}/pythia-8.3.12"
readonly HEPMC3_PREFIX="${external_root}/hepmc3-3.3.0"

# LHAPDF must be set up and sourced
if [[ -z "${LHAPDF_PREFIX:-}" ]]; then
    # shellcheck source=scripts/lhapdf_env.sh
    source "${SCRIPT_DIR}/lhapdf_env.sh"
fi
[[ -d "${LHAPDF_PREFIX}" ]] || die "LHAPDF installation is missing at ${LHAPDF_PREFIX}"
[[ -d "${HEPMC3_PREFIX}" ]] || die "HepMC3 installation is missing at ${HEPMC3_PREFIX}"

install -d -- "${DOWNLOAD_DIR}" "${SOURCE_PARENT}"

pythia_archive="${DOWNLOAD_DIR}/releases-pythia8312.tar.gz"
download_pinned "${PYTHIA_URL}" "${pythia_archive}" "${PYTHIA_SHA256}" "PYTHIA ${PYTHIA_VERSION}"
validate_tar_archive "${pythia_archive}" "releases-pythia8312" "PYTHIA"

if [[ ! -d "${SOURCE_DIR}" ]]; then
    tar --extract --gzip --file "${pythia_archive}" --directory "${SOURCE_PARENT}" \
        --no-same-owner --no-same-permissions
fi
[[ -f "${SOURCE_DIR}/configure" ]] || die "PYTHIA 8 source tree is incomplete"

if [[ ! -x "${PREFIX}/bin/pythia8-config" ]]; then
    note "Configuring PYTHIA ${PYTHIA_VERSION}..."
    (
        cd -- "${SOURCE_DIR}"
        ./configure \
            --prefix="${PREFIX}" \
            --with-lhapdf6="${LHAPDF_PREFIX}" \
            --with-hepmc3="${HEPMC3_PREFIX}"
        make -j"${jobs}"
        make install
    )
fi

[[ -x "${PREFIX}/bin/pythia8-config" ]] || die "installed pythia8-config is missing"

note ""
note "PYTHIA 8 setup complete"
note "  PYTHIA prefix:   ${PREFIX}"
note "  LHAPDF prefix:   ${LHAPDF_PREFIX}"
note "  HepMC3 prefix:   ${HEPMC3_PREFIX}"
note ""
