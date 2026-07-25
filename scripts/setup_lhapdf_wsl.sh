#!/usr/bin/env bash
#
# Build LHAPDF in a user-owned WSL prefix and install the pinned CT18LO set.
# This script never invokes sudo or apt and does not remove an existing install.

set -Eeuo pipefail

readonly LHAPDF_VERSION="6.5.6"
readonly PDF_SET="CT18LO"
readonly PDF_MEMBER="0"
readonly LHAPDF_SOURCE_URL="https://lhapdf.hepforge.org/downloads/?f=LHAPDF-6.5.6.tar.gz"
readonly PDF_SET_URL="https://lhapdfsets.web.cern.ch/lhapdfsets/current/CT18LO.tar.gz"

# Neither upstream download page publishes an adjacent checksum/signature file.
# These integrity pins were recorded from the official HTTPS artifacts on
# 2026-07-16. They are reproducibility pins, not upstream-authenticated
# signatures. In addition, archives are structurally checked before extraction.
readonly LHAPDF_SOURCE_SHA256="6b8b7e38dc26a977a24f5a321215b7054c14a4469d04134d70cb93a860eeeea7"
readonly PDF_SET_SHA256="e3c37591ebd0f4c8e413d16b49a2e6c6cdefc1cb575b5e75e21dedd116ca1e3f"

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

note() {
    printf '%s\n' "$*"
}

usage() {
    cat <<'EOF'
Usage: scripts/setup_lhapdf_wsl.sh [OPTIONS]

Build LHAPDF 6.5.6 without sudo and install CT18LO member 0.

Options:
  --prefix PATH    Installation prefix
                   (default: $HOME/.local/lhapdf-6.5.6)
  --data-dir PATH  LHAPDF data directory
                   (default: PREFIX/share/LHAPDF)
  --jobs N         Parallel build jobs (default: LHAPDF_BUILD_JOBS or nproc)
  -h, --help       Show this help

The same values may be supplied through LHAPDF_PREFIX, LHAPDF_DATA_DIR,
and LHAPDF_BUILD_JOBS. Command-line options take precedence.

This script intentionally does not run apt or sudo. If prerequisites are
missing, it prints the Ubuntu package command for the user to review.
EOF
}

require_wsl_ubuntu() {
    [[ -r /proc/sys/kernel/osrelease ]] ||
        die "cannot inspect the kernel; run this script inside WSL Ubuntu"
    grep -qi 'microsoft' /proc/sys/kernel/osrelease ||
        die "this installer is restricted to WSL"
    [[ -r /etc/os-release ]] ||
        die "/etc/os-release is unavailable"

    # shellcheck disable=SC1091
    source /etc/os-release
    [[ "${ID:-}" == "ubuntu" ]] ||
        die "this installer supports WSL Ubuntu; detected ${PRETTY_NAME:-unknown}"
}

normalise_path() {
    local path="$1"
    [[ -n "${path}" ]] || die "installation paths must not be empty"
    [[ "${path}" == /* ]] || die "path must be absolute: ${path}"
    [[ "${path}" != *$'\n'* ]] || die "path must not contain a newline"

    path="$(readlink -m -- "${path}")"
    [[ "${path}" != "/" ]] || die "refusing to use the filesystem root as a prefix or data directory"
    printf '%s\n' "${path}"
}

check_prerequisites() {
    local -a missing=()
    local command_name

    for command_name in c++ make curl tar gzip sha256sum awk grep sed readlink \
        install cp pkg-config mktemp rm dirname basename; do
        if ! command -v "${command_name}" >/dev/null 2>&1; then
            missing+=("${command_name}")
        fi
    done

    if (("${#missing[@]}" > 0)); then
        printf 'error: missing required command(s): %s\n' "${missing[*]}" >&2
        cat >&2 <<'EOF'
Review and run the following inside WSL Ubuntu, then retry:

  sudo apt-get update
  sudo apt-get install --no-install-recommends build-essential ca-certificates curl pkg-config

CMake is not required: the official LHAPDF 6.5.6 release includes its
Autotools-generated configure script.
EOF
        exit 1
    fi
}

download() {
    local url="$1"
    local destination="$2"
    local label="$3"

    note "Downloading ${label} from its official HTTPS endpoint..."
    curl --fail --show-error --silent --location --proto '=https' --tlsv1.2 \
        --retry 3 --retry-delay 2 --output "${destination}" "${url}"
    [[ -s "${destination}" ]] || die "${label} download is empty"
}

verify_sha256() {
    local archive="$1"
    local expected="$2"
    local label="$3"
    local actual

    actual="$(sha256sum -- "${archive}" | awk '{print $1}')"
    if [[ "${actual}" != "${expected}" ]]; then
        printf 'error: SHA-256 mismatch for %s\n' "${label}" >&2
        printf '  expected: %s\n' "${expected}" >&2
        printf '  actual:   %s\n' "${actual}" >&2
        exit 1
    fi
    note "Verified ${label} SHA-256: ${actual}"
}

validate_tar_archive() {
    local archive="$1"
    local expected_root="$2"
    local label="$3"
    local entry
    local listing_line
    local entry_type
    local count=0

    tar -tzf "${archive}" >/dev/null ||
        die "${label} is not a readable gzip-compressed tar archive"

    while IFS= read -r entry; do
        count=$((count + 1))

        [[ -n "${entry}" ]] || die "${label} contains an empty path"
        case "${entry}" in
            /* | .. | ../* | */../* | */..)
                die "${label} contains an unsafe path: ${entry}"
                ;;
        esac
        [[ "${entry}" != *'\'* ]] ||
            die "${label} contains a path with a backslash: ${entry}"
        case "${entry}" in
            "${expected_root}" | "${expected_root}"/*)
                ;;
            *)
                die "${label} contains a path outside ${expected_root}/: ${entry}"
                ;;
        esac
    done < <(LC_ALL=C tar -tzf "${archive}")

    ((count > 0)) || die "${label} contains no entries"

    # Reject links and special files as well as traversal paths. The official
    # source and CT18LO archives only need directories and regular files.
    while IFS= read -r listing_line; do
        [[ -n "${listing_line}" ]] || continue
        entry_type="${listing_line:0:1}"
        case "${entry_type}" in
            - | d)
                ;;
            *)
                die "${label} contains an unsupported archive entry type: ${entry_type}"
                ;;
        esac
    done < <(LC_ALL=C tar -tvzf "${archive}")

    note "Validated ${label} archive structure under ${expected_root}/"
}

extract_archive() {
    local archive="$1"
    local destination="$2"

    install -d -- "${destination}"
    tar --extract --gzip --file "${archive}" --directory "${destination}" \
        --no-same-owner --no-same-permissions
}

validate_pdf_set() {
    local set_dir="$1"
    local info_file="${set_dir}/${PDF_SET}.info"
    local member_file="${set_dir}/${PDF_SET}_0000.dat"
    local num_members
    local order_qcd

    [[ -s "${info_file}" ]] ||
        die "${PDF_SET} metadata is missing or empty: ${info_file}"
    [[ -s "${member_file}" ]] ||
        die "${PDF_SET} member ${PDF_MEMBER} is missing or empty: ${member_file}"

    grep -Eq '^Format:[[:space:]]*lhagrid1[[:space:]]*$' "${info_file}" ||
        die "${PDF_SET} metadata does not declare the lhagrid1 format"
    grep -Eq '^Flavors:.*-5.*-4.*-3.*-2.*-1.*1.*2.*3.*4.*5.*21' "${info_file}" ||
        die "${PDF_SET} metadata does not contain the expected quark/gluon flavors"
    grep -Eq '^PdfType:[[:space:]]*central[[:space:]]*$' "${member_file}" ||
        die "${PDF_SET} member ${PDF_MEMBER} is not marked central"

    num_members="$(awk -F: '/^NumMembers:/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${info_file}")"
    [[ "${num_members}" == "1" ]] ||
        die "${PDF_SET} was expected to have one member, found ${num_members:-unknown}"

    order_qcd="$(awk -F: '/^OrderQCD:/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${info_file}")"
    [[ "${order_qcd}" == "0" ]] ||
        die "${PDF_SET} was expected to be LO (OrderQCD 0), found ${order_qcd:-unknown}"
}

prefix="${LHAPDF_PREFIX:-}"
if [[ -z "${prefix}" ]]; then
    [[ -n "${HOME:-}" ]] ||
        die "HOME is unset; provide an absolute path through --prefix"
    prefix="${HOME}/.local/lhapdf-${LHAPDF_VERSION}"
fi

data_dir="${LHAPDF_DATA_DIR:-}"
jobs="${LHAPDF_BUILD_JOBS:-}"

while (($# > 0)); do
    case "$1" in
        --prefix)
            (($# >= 2)) || die "--prefix requires a path"
            prefix="$2"
            shift 2
            ;;
        --data-dir)
            (($# >= 2)) || die "--data-dir requires a path"
            data_dir="$2"
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
        *)
            die "unknown option: $1 (run with --help)"
            ;;
    esac
done

require_wsl_ubuntu
check_prerequisites

prefix="$(normalise_path "${prefix}")"
if [[ -z "${data_dir}" ]]; then
    data_dir="${prefix}/share/LHAPDF"
fi
data_dir="$(normalise_path "${data_dir}")"

if [[ -z "${jobs}" ]]; then
    if command -v nproc >/dev/null 2>&1; then
        jobs="$(nproc)"
    else
        jobs="1"
    fi
fi
[[ "${jobs}" =~ ^[1-9][0-9]*$ ]] ||
    die "--jobs/LHAPDF_BUILD_JOBS must be a positive integer"

install -d -- "${prefix}" "${data_dir}"
[[ -w "${prefix}" ]] || die "installation prefix is not writable: ${prefix}"
[[ -w "${data_dir}" ]] || die "data directory is not writable: ${data_dir}"

tmp_root="$(readlink -f -- "${TMPDIR:-/tmp}")" ||
    die "temporary directory does not exist: ${TMPDIR:-/tmp}"
[[ -d "${tmp_root}" && -w "${tmp_root}" ]] ||
    die "temporary directory is not writable: ${tmp_root}"

work_dir="$(mktemp -d "${tmp_root}/neuronswq-lhapdf.XXXXXXXX")"
work_dir="$(readlink -f -- "${work_dir}")" ||
    die "failed to resolve the temporary work directory"
cleanup() {
    local work_parent
    local work_name

    work_parent="$(dirname -- "${work_dir}")"
    work_name="$(basename -- "${work_dir}")"
    if [[ "${work_parent}" == "${tmp_root}" &&
        "${work_name}" == neuronswq-lhapdf.* &&
        -d "${work_dir}" ]]; then
        rm -rf -- "${work_dir}"
    else
        printf 'warning: refusing to clean unexpected temporary path: %s\n' "${work_dir}" >&2
    fi
}
trap cleanup EXIT

lhapdf_config="${prefix}/bin/lhapdf-config"
lhaglue_header="${prefix}/include/LHAPDF/LHAGlue.h"
needs_lhapdf_build=true
if [[ -x "${lhapdf_config}" ]]; then
    installed_version="$("${lhapdf_config}" --version 2>/dev/null || true)"
    [[ "${installed_version}" == "${LHAPDF_VERSION}" ]] ||
        die "${prefix} already contains LHAPDF ${installed_version:-unknown}; expected ${LHAPDF_VERSION}"
    if [[ -s "${lhaglue_header}" ]]; then
        needs_lhapdf_build=false
        note "LHAPDF ${LHAPDF_VERSION} with C++ compatibility headers is already installed; skipping the build."
    else
        note "LHAPDF ${LHAPDF_VERSION} is missing ${lhaglue_header}; repairing the installation."
    fi
fi

if [[ "${needs_lhapdf_build}" == true ]]; then
    source_archive="${work_dir}/LHAPDF-${LHAPDF_VERSION}.tar.gz"
    download "${LHAPDF_SOURCE_URL}" "${source_archive}" "LHAPDF ${LHAPDF_VERSION}"
    verify_sha256 "${source_archive}" "${LHAPDF_SOURCE_SHA256}" "LHAPDF ${LHAPDF_VERSION}"
    validate_tar_archive "${source_archive}" "LHAPDF-${LHAPDF_VERSION}" "LHAPDF ${LHAPDF_VERSION}"
    extract_archive "${source_archive}" "${work_dir}/source"

    source_dir="${work_dir}/source/LHAPDF-${LHAPDF_VERSION}"
    [[ -x "${source_dir}/configure" ]] ||
        die "the LHAPDF release does not contain an executable configure script"

    note "Configuring LHAPDF ${LHAPDF_VERSION} for ${prefix}..."
    (
        cd -- "${source_dir}"
        # managed-lhapdf includes LHAPDF/LHAPDF.h, whose public umbrella header
        # requires LHAGlue.h. Keep the upstream compatibility headers enabled.
        ./configure --prefix="${prefix}" --disable-python --disable-doxygen \
            --enable-lhaglue --enable-lhaglue-cxx --disable-static --enable-shared

        note "Building LHAPDF with ${jobs} job(s)..."
        make -j"${jobs}"
        note "Installing LHAPDF into the user prefix..."
        make install
    )

    [[ -x "${lhapdf_config}" ]] ||
        die "installation finished without creating ${lhapdf_config}"
    installed_version="$("${lhapdf_config}" --version)"
    [[ "${installed_version}" == "${LHAPDF_VERSION}" ]] ||
        die "installed LHAPDF reports ${installed_version}; expected ${LHAPDF_VERSION}"
    [[ -s "${lhaglue_header}" ]] ||
        die "installation did not create the required public header: ${lhaglue_header}"
fi

set_target="${data_dir}/${PDF_SET}"
if [[ -e "${set_target}" ]]; then
    [[ -d "${set_target}" ]] ||
        die "${set_target} exists but is not a directory"
    validate_pdf_set "${set_target}"
    note "${PDF_SET} member ${PDF_MEMBER} is already installed; skipping extraction."
else
    pdf_archive="${work_dir}/${PDF_SET}.tar.gz"
    download "${PDF_SET_URL}" "${pdf_archive}" "${PDF_SET}"
    verify_sha256 "${pdf_archive}" "${PDF_SET_SHA256}" "${PDF_SET}"
    validate_tar_archive "${pdf_archive}" "${PDF_SET}" "${PDF_SET}"
    extract_archive "${pdf_archive}" "${work_dir}/pdf-set"
    validate_pdf_set "${work_dir}/pdf-set/${PDF_SET}"

    # Copy only after the staged set has passed every validation. A pre-existing
    # target is never overwritten.
    cp -a -- "${work_dir}/pdf-set/${PDF_SET}" "${set_target}"
    validate_pdf_set "${set_target}"
fi

export LHAPDF_PREFIX="${prefix}"
export LHAPDF_DATA_DIR="${data_dir}"
# shellcheck source=lhapdf_env.sh
source "${SCRIPT_DIR}/lhapdf_env.sh"

pkg_config_version="$(pkg-config --modversion lhapdf 2>/dev/null || true)"
[[ "${pkg_config_version}" == "${LHAPDF_VERSION}" ]] ||
    die "pkg-config cannot resolve LHAPDF ${LHAPDF_VERSION} from ${prefix}"

set_index="$(awk -F: '/^SetIndex:/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${set_target}/${PDF_SET}.info")"
data_version="$(awk -F: '/^DataVersion:/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${set_target}/${PDF_SET}.info")"
order_qcd="$(awk -F: '/^OrderQCD:/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${set_target}/${PDF_SET}.info")"

cat <<EOF

LHAPDF setup complete
  LHAPDF version: ${installed_version}
  pkg-config:     ${pkg_config_version}
  prefix:         ${prefix}
  library dir:    $("${lhapdf_config}" --libdir)
  configured data:$("${lhapdf_config}" --datadir)
  active data dir:${data_dir}
  PDF set:        ${PDF_SET}
  PDF member:     ${PDF_MEMBER}
  set index:      ${set_index}
  data version:   ${data_version}
  QCD order code: ${order_qcd} (0 = LO)

Activate this installation in each new WSL shell:

  source "${SCRIPT_DIR}/lhapdf_env.sh"
EOF
