#!/usr/bin/env bash
# Build the quark_sim Docker image

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
readonly REPO_ROOT="$(dirname "${SCRIPT_DIR}")"
readonly IMAGE_NAME="quark_sim:latest"

echo "Building Docker image: ${IMAGE_NAME}..."
cd "${REPO_ROOT}"
docker build -t "${IMAGE_NAME}" -f docker/Dockerfile .
echo "Build complete."
