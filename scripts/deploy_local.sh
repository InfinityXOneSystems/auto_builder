#!/bin/bash
set -euo pipefail
IMAGE_NAME="mcp/omni-gateway:local"
docker build -f Dockerfile.prod -t ${IMAGE_NAME} .
kubectl apply -f k8s/omni-deployment.yaml
