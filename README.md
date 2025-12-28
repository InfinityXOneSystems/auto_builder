# Omni Gateway (Development)

This repo contains the Omni Gateway and helper tools for local development.

Quick start (dev):

1. Create a virtualenv and install deps:
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
```

2. Start gateway:
```bash
python ops/run_uvicorn_bg.py start
```

3. Run headless tests:
```bash
python ops/run_headless_test_now.py
cat tools/headless_test_results.json
```

Enterprise-grade checklist (placeholder):
- Hardened secrets handling
- Proper package packaging and versioning
- CI with tests and vulnerability scans
- Observability (OTel, Prometheus) configured
- Autoscaling and deployment manifests

Optional: Build Docker image and deploy to Cloud Run (recommended)
```bash
# Set environment variables:
export GCP_PROJECT=your-gcp-project
export CLOUD_RUN_REGION=us-central1
export IMAGE_NAME=gcr.io/$GCP_PROJECT/omni-gateway:latest
./scripts/deploy_cloudrun.sh
```

---

# auto_builder

This section is reserved for auto_builder documentation.
