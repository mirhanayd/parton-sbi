#!/usr/bin/env bash
# Run the quark_sim Docker image

set -Eeuo pipefail

readonly IMAGE_NAME="quark_sim:latest"

echo "Running Docker image: ${IMAGE_NAME}..."
if [ $# -eq 0 ]; then
    docker run -it --rm "${IMAGE_NAME}" bash
else
    docker run -it --rm "${IMAGE_NAME}" "$@"
fi
