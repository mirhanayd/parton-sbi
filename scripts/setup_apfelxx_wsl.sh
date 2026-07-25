#!/usr/bin/env bash
# Build a pinned APFEL++ release, install CT18NLO, and build the JSON backend.
# Everything is installed below this repository's .external directory by default.

set -Eeuo pipefail

readonly APFELXX_VERSION="4.8.0"
readonly APFELXX_COMMIT="75b1fce6b7de128aa1f153aa6a2c84ee840fdfcb"
readonly APFELXX_URL="https://github.com/vbertone/apfelxx/archive/refs/tags/4.8.0.tar.gz"
readonly APFELXX_SHA256="d577cf0f8cbcfae18699670941827c6c72dfec4aeb14321365c36937ace6a34a"

readonly JSON_VERSION="3.11.3"
readonly JSON_URL="https://raw.githubusercontent.com/nlohmann/json/v3.11.3/single_include/nlohmann/json.hpp"
readonly JSON_SHA256="9bea4c8066ef4a1c206b2be5a36302f8926f7fdc6087af5d20b417d0cf103ea6"

readonly PDF_SET="CT18NLO"
readonly PDF_MEMBER="0"
readonly PDF_SET_URL="https://lhapdfsets.web.cern.ch/current/CT18NLO.tar.gz"
readonly PDF_SET_SHA256="c9127231e77e97cbec79cb5839203ab00f8db77237a061b61f9420f2b7b9c213"

# APFEL++ declares Fortran as a project language. Ubuntu WSL images often omit
# gfortran even when GCC is present. If so, the two signed Ubuntu packages below
# are downloaded with APT and unpacked into .external without changing dpkg state.
readonly GFORTRAN_VERSION="13.3.0-6ubuntu2~24.04.1"
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
Usage: scripts/setup_apfelxx_wsl.sh [OPTIONS]

Build APFEL++ 4.8.0 and the versioned JSON structure-function backend, and
install the CT18NLO PDF set. No sudo command or system-library overwrite is used.

Options:
  --external-root PATH  Controlled dependency root (default: REPO/.external)
  --engine-build PATH   Backend CMake build directory
                        (default: REPO/physics-engine/build)
  --jobs N              Parallel build jobs (default: min(nproc, 4))
  -h, --help            Show this help

Environment equivalents: APFEL_EXTERNAL_ROOT, APFEL_ENGINE_BUILD_DIR,
APFEL_BUILD_JOBS. Source scripts/apfelxx_env.sh after setup.
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

    for command_name in apt awk cat cmake curl dirname dpkg-deb g++ gcc-13 grep \
        install ldconfig ln make mktemp mv nproc pkg-config readlink rm sed \
        sha256sum tar tr; do
        command -v "${command_name}" >/dev/null 2>&1 || missing+=("${command_name}")
    done

    if (("${#missing[@]}" > 0)); then
        printf 'error: missing required command(s): %s\n' "${missing[*]}" >&2
        cat >&2 <<'EOF'
Review and run the following inside WSL Ubuntu, then retry:

  sudo apt-get update
  sudo apt-get install --no-install-recommends build-essential cmake curl pkg-config
EOF
        exit 1
    fi

    pkg-config --exists lhapdf ||
        die "LHAPDF pkg-config metadata is unavailable; source scripts/lhapdf_env.sh"
    command -v lhapdf-config >/dev/null 2>&1 ||
        die "lhapdf-config is unavailable; run and source scripts/setup_lhapdf_wsl.sh"
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
    note "Downloading ${label} from its official HTTPS endpoint..."
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

validate_ct18nlo() {
    local set_dir="$1"
    local info_file="${set_dir}/${PDF_SET}.info"
    local num_members order_qcd data_version set_index

    [[ -s "${info_file}" ]] || die "missing ${PDF_SET} metadata: ${info_file}"
    [[ -s "${set_dir}/${PDF_SET}_0000.dat" ]] || die "missing ${PDF_SET} member 0"
    [[ -s "${set_dir}/${PDF_SET}_0058.dat" ]] || die "incomplete ${PDF_SET} member set"
    num_members="$(awk -F: '/^NumMembers:/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${info_file}")"
    order_qcd="$(awk -F: '/^OrderQCD:/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${info_file}")"
    data_version="$(awk -F: '/^DataVersion:/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${info_file}")"
    set_index="$(awk -F: '/^SetIndex:/ {gsub(/[[:space:]]/, "", $2); print $2; exit}' "${info_file}")"
    [[ "${num_members}" == "59" ]] || die "${PDF_SET} expected 59 members, found ${num_members:-unknown}"
    [[ "${order_qcd}" == "1" ]] || die "${PDF_SET} expected OrderQCD 1, found ${order_qcd:-unknown}"
    [[ "${data_version}" == "1" ]] || die "${PDF_SET} expected DataVersion 1, found ${data_version:-unknown}"
    [[ "${set_index}" == "14400" ]] || die "${PDF_SET} expected SetIndex 14400, found ${set_index:-unknown}"
}

external_root="${APFEL_EXTERNAL_ROOT:-${REPO_ROOT}/.external}"
engine_build="${APFEL_ENGINE_BUILD_DIR:-${REPO_ROOT}/physics-engine/build}"
jobs="${APFEL_BUILD_JOBS:-}"

while (($# > 0)); do
    case "$1" in
        --external-root)
            (($# >= 2)) || die "--external-root requires a path"
            external_root="$2"
            shift 2
            ;;
        --engine-build)
            (($# >= 2)) || die "--engine-build requires a path"
            engine_build="$2"
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
engine_build="$(normalise_path "${engine_build}")"
if [[ -z "${jobs}" ]]; then
    detected_jobs="$(nproc)"
    ((detected_jobs < 4)) && jobs="${detected_jobs}" || jobs=4
fi
[[ "${jobs}" =~ ^[1-9][0-9]*$ ]] || die "build jobs must be a positive integer"

require_wsl_ubuntu

# shellcheck source=scripts/lhapdf_env.sh
source "${SCRIPT_DIR}/lhapdf_env.sh"
check_prerequisites

readonly DOWNLOAD_DIR="${external_root}/downloads"
readonly SOURCE_PARENT="${external_root}/src"
readonly SOURCE_DIR="${SOURCE_PARENT}/apfelxx-${APFELXX_VERSION}"
readonly BUILD_DIR="${external_root}/build/apfelxx-${APFELXX_VERSION}"
readonly PREFIX="${external_root}/apfelxx-${APFELXX_VERSION}"
readonly JSON_INCLUDE_DIR="${external_root}/include"
readonly JSON_HEADER="${JSON_INCLUDE_DIR}/nlohmann/json.hpp"
readonly TOOLCHAIN_DIR="${external_root}/toolchain/gfortran-13"

install -d -- "${DOWNLOAD_DIR}" "${SOURCE_PARENT}" "${external_root}/build" \
    "${JSON_INCLUDE_DIR}/nlohmann" "${TOOLCHAIN_DIR}"

fortran_compiler="$(command -v gfortran || true)"
if [[ -z "${fortran_compiler}" ]]; then
    fortran_compiler="${TOOLCHAIN_DIR}/usr/bin/x86_64-linux-gnu-gfortran-13"
    if [[ ! -x "${fortran_compiler}" ]]; then
        package_dir="${DOWNLOAD_DIR}/gfortran-${GFORTRAN_VERSION}"
        install -d -- "${package_dir}"
        note "gfortran is absent; downloading signed Ubuntu packages without installing system-wide..."
        (
            cd -- "${package_dir}"
            apt download \
                "gfortran-13-x86-64-linux-gnu=${GFORTRAN_VERSION}" \
                "libgfortran-13-dev=${GFORTRAN_VERSION}"
        )
        shopt -s nullglob
        packages=("${package_dir}"/*.deb)
        shopt -u nullglob
        (("${#packages[@]}" == 2)) || die "expected two gfortran packages, found ${#packages[@]}"
        for package in "${packages[@]}"; do
            dpkg-deb --extract "${package}" "${TOOLCHAIN_DIR}"
        done
    fi
fi
[[ -x "${fortran_compiler}" ]] || die "Fortran compiler is unavailable"
"${fortran_compiler}" --version >/dev/null

# A user-unpacked gfortran contains f951 and the Fortran development libraries,
# while the matching system GCC package owns cc1 and the LTO plugin. Give GCC an
# explicit, ordered search path so the two signed package locations form one
# coherent toolchain without copying or replacing system files.
if [[ "${fortran_compiler}" == "${TOOLCHAIN_DIR}"/* ]]; then
    fortran_exec_dir="${TOOLCHAIN_DIR}/usr/libexec/gcc/x86_64-linux-gnu/13"
    fortran_lib_dir="${TOOLCHAIN_DIR}/usr/lib/gcc/x86_64-linux-gnu/13"
    system_exec_dir="$(dirname -- "$(gcc-13 -print-prog-name=cc1)")"
    system_lib_dir="$(dirname -- "$(gcc-13 -print-file-name=liblto_plugin.so)")"
    [[ -x "${fortran_exec_dir}/f951" ]] || die "user-local f951 is unavailable"
    [[ -x "${system_exec_dir}/cc1" ]] || die "matching system cc1 is unavailable"
    [[ -f "${system_lib_dir}/liblto_plugin.so" ]] || die "matching GCC LTO plugin is unavailable"

    # libgfortran-13-dev provides an unversioned relative symlink intended for a
    # system package layout. Recreate only its missing target inside the local
    # prefix, pointing at the already installed libgfortran ABI 5 runtime.
    runtime_lib="$(ldconfig -p | awk '/libgfortran\.so\.5 .*x86-64/ {print $NF; exit}')"
    [[ -f "${runtime_lib}" ]] || die "the libgfortran.so.5 runtime is unavailable"
    local_runtime_dir="${TOOLCHAIN_DIR}/usr/lib/x86_64-linux-gnu"
    local_runtime_lib="${local_runtime_dir}/libgfortran.so.5"
    install -d -- "${local_runtime_dir}"
    if [[ ! -e "${local_runtime_lib}" ]]; then
        ln --symbolic -- "${runtime_lib}" "${local_runtime_lib}"
    fi
    export COMPILER_PATH="${fortran_exec_dir}:${system_exec_dir}${COMPILER_PATH:+:${COMPILER_PATH}}"
    export LIBRARY_PATH="${fortran_lib_dir}:${system_lib_dir}${LIBRARY_PATH:+:${LIBRARY_PATH}}"
fi

apfel_archive="${DOWNLOAD_DIR}/apfelxx-${APFELXX_VERSION}.tar.gz"
download_pinned "${APFELXX_URL}" "${apfel_archive}" "${APFELXX_SHA256}" "APFEL++ ${APFELXX_VERSION}"
validate_tar_archive "${apfel_archive}" "apfelxx-${APFELXX_VERSION}" "APFEL++"
if [[ ! -d "${SOURCE_DIR}" ]]; then
    tar --extract --gzip --file "${apfel_archive}" --directory "${SOURCE_PARENT}" \
        --no-same-owner --no-same-permissions
fi
[[ -f "${SOURCE_DIR}/CMakeLists.txt" ]] || die "APFEL++ source tree is incomplete"
grep -Fq "set(apfelxx_VERSION ${APFELXX_VERSION})" "${SOURCE_DIR}/CMakeLists.txt" ||
    die "APFEL++ source version does not match ${APFELXX_VERSION}"

if [[ ! -x "${PREFIX}/bin/apfelxx-config" ]]; then
    note "Configuring APFEL++ ${APFELXX_VERSION} (${APFELXX_COMMIT})..."
    FC="${fortran_compiler}" cmake -S "${SOURCE_DIR}" -B "${BUILD_DIR}" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="${PREFIX}" \
        -DCMAKE_Fortran_COMPILER="${fortran_compiler}"
    cmake --build "${BUILD_DIR}" --parallel "${jobs}"
    cmake --install "${BUILD_DIR}"
fi
[[ "$("${PREFIX}/bin/apfelxx-config" --version | tr -d '[:space:]')" == "${APFELXX_VERSION}" ]] ||
    die "installed apfelxx-config does not report ${APFELXX_VERSION}"

download_pinned "${JSON_URL}" "${JSON_HEADER}" "${JSON_SHA256}" "nlohmann/json ${JSON_VERSION}"

pdf_archive="${DOWNLOAD_DIR}/${PDF_SET}.tar.gz"
download_pinned "${PDF_SET_URL}" "${pdf_archive}" "${PDF_SET_SHA256}" "${PDF_SET}"
validate_tar_archive "${pdf_archive}" "${PDF_SET}" "${PDF_SET}"
lhapdf_data_dir="${LHAPDF_DATA_DIR:-$(lhapdf-config --datadir)}"
lhapdf_data_dir="$(normalise_path "${lhapdf_data_dir}")"
install -d -- "${lhapdf_data_dir}"
if [[ ! -d "${lhapdf_data_dir}/${PDF_SET}" ]]; then
    tar --extract --gzip --file "${pdf_archive}" --directory "${lhapdf_data_dir}" \
        --no-same-owner --no-same-permissions
fi
validate_ct18nlo "${lhapdf_data_dir}/${PDF_SET}"

[[ -f "${REPO_ROOT}/physics-engine/CMakeLists.txt" ]] ||
    die "physics-engine/CMakeLists.txt is missing"
note "Configuring and building the APFEL++ JSON backend..."
cmake -S "${REPO_ROOT}/physics-engine" -B "${engine_build}" \
    -DCMAKE_BUILD_TYPE=Release \
    -DAPFELXX_ROOT="${PREFIX}" \
    -DNLOHMANN_JSON_INCLUDE_DIR="${JSON_INCLUDE_DIR}"
cmake --build "${engine_build}" --parallel "${jobs}"

note ""
note "APFEL++ setup complete"
note "  APFEL++ version:  $("${PREFIX}/bin/apfelxx-config" --version | tr -d '[:space:]')"
note "  APFEL++ commit:   ${APFELXX_COMMIT}"
note "  LHAPDF version:   $(lhapdf-config --version)"
note "  PDF set/member:   ${PDF_SET}/${PDF_MEMBER}"
note "  APFEL++ prefix:   ${PREFIX}"
note "  APFEL++ build:    ${BUILD_DIR}"
note "  backend build:    ${engine_build}"
note "  backend binary:   ${engine_build}/apfel_cli"
note ""
note "Activate this installation in each new WSL shell:"
note "  source \"${SCRIPT_DIR}/apfelxx_env.sh\""
