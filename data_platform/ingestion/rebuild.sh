#!/usr/bin/env bash

# Stop containers for one image, remove image, then rebuild.
# Usage: ./rebuild.sh [image-ref] [build-context]
#
# Examples:
#   ./rebuild.sh
#   ./rebuild.sh lambda
#   ./rebuild.sh bamboo-analytics/data-platform:latest .

set -euo pipefail

IMAGE_REF="${1:-lambda}"
BUILD_CONTEXT="${2:-.}"

echo "=========================================="
echo "Docker Rebuild Script"
echo "=========================================="
echo "Image ref: ${IMAGE_REF}"
echo "Build context: ${BUILD_CONTEXT}"
echo "=========================================="

echo ""
echo "Step 1: Find and remove containers using this image..."
container_ids="$(docker ps -aq --filter "ancestor=${IMAGE_REF}" || true)"

# If no container is found by tag/name, try the image digest/id.
if [ -z "${container_ids}" ]; then
  image_id="$(docker image inspect --format '{{.Id}}' "${IMAGE_REF}" 2>/dev/null || true)"
  if [ -n "${image_id}" ]; then
    container_ids="$(docker ps -aq --filter "ancestor=${image_id}" || true)"
  fi
fi

if [ -n "${container_ids}" ]; then
  echo "Containers to remove:"
  docker ps -a --filter "id=${container_ids}"
  docker stop ${container_ids} >/dev/null 2>&1 || true
  docker rm ${container_ids} >/dev/null 2>&1 || true
  echo "Removed containers: ${container_ids}"
else
  echo "No containers found for '${IMAGE_REF}'."
fi

echo ""
echo "Step 2: Remove image..."
if docker image inspect "${IMAGE_REF}" >/dev/null 2>&1; then
  docker image rm -f "${IMAGE_REF}"
  echo "Removed image '${IMAGE_REF}'."
else
  echo "Image '${IMAGE_REF}' does not exist. Skipping remove."
fi

echo ""
echo "Step 3: Rebuild image..."
docker build -t "${IMAGE_REF}" "${BUILD_CONTEXT}"

echo ""
echo "=========================================="
echo "Rebuild complete"
echo "=========================================="
echo "Run:"
echo "docker run --rm -p 9000:8080 ${IMAGE_REF}"
