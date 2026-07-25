#!/usr/bin/env bash
# Build the PartonSBI Docker image

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
readonly REPO_ROOT="$(dirname "${SCRIPT_DIR}")"
readonly IMAGE_NAME="parton-sbi:latest"

echo "Building Docker image: ${IMAGE_NAME}..."
cd "${REPO_ROOT}"
docker build -t "${IMAGE_NAME}" -f docker/Dockerfile .
echo "Build complete."
