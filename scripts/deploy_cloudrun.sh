#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME=${IMAGE_NAME:-gcr.io/$GCP_PROJECT/omni-gateway:latest}
echo "Building image ${IMAGE_NAME}..."
docker build -f Dockerfile.prod -t ${IMAGE_NAME} .
echo "Pushing image..."
docker push ${IMAGE_NAME}
echo "Deploying to Cloud Run..."
gcloud run deploy omni-gateway --image ${IMAGE_NAME} --platform managed --region ${CLOUD_RUN_REGION:-us-central1} --allow-unauthenticated
