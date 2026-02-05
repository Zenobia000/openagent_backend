#!/bin/bash
# 構建 OpenCode Sandbox Docker Image

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="opencode-sandbox"
IMAGE_TAG="latest"

echo "🐳 Building OpenCode Sandbox Docker Image..."
echo "   Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""

# 構建 Docker image
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" "${SCRIPT_DIR}"

echo ""
echo "✅ Build complete!"
echo ""
echo "Test the image:"
echo "  echo '{\"code\": \"print(1+1)\"}' | docker run -i --rm ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "Test with matplotlib:"
echo "  echo '{\"code\": \"import matplotlib.pyplot as plt\\nplt.plot([1,2,3])\\nplt.title('Test')\\nprint('done')\"}' | docker run -i --rm ${IMAGE_NAME}:${IMAGE_TAG}"
