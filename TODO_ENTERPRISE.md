# Enterprise rollout TODO (ordered)

This file lists concrete steps to bring the Omni Gateway to enterprise-grade readiness.

1) Replace `vision_cortex` stubs with production implementations
   - Ensure the real `vision_cortex` package files exist under the repo and are importable.
   - If canonical code is in a different repo, add as a git submodule or package into `pyproject.toml`.

2) Pin dependencies & lock
   - Use `requirements-lock.txt` for deterministic builds in CI and Docker.
   - Run `pip install -r requirements-lock.txt` in CI.

3) Increase test coverage
   - Add unit tests for all agent types and integration tests for endpoints.
   - Add e2e tests that start the service in a container and run the headless-team tests.

4) Observability
   - Configure OpenTelemetry exporter (OTLP) or Prometheus scrape endpoint in k8s.
   - Wire up tracing for critical request paths and agent execution.

5) Secrets & credentials
   - Move secrets to Vault, GCP Secret Manager, or AWS Secrets Manager.
   - Ensure no plaintext secrets in the repo.

6) CI/CD
   - Enable the provided GitHub Actions workflow and expand to include linters, SCA (safety), container builds, and deployment.
   - Add environment-specific deployment workflows for staging and production.

7) Production deployment artifacts
   - Build and push `Dockerfile.prod` images to a registry.
   - Deploy via k8s manifests or Helm charts; configure liveness/readiness probes.

8) Autoscaling & resource limits
   - Configure HPA or cloud autoscaling based on custom metrics.

9) Security and compliance
   - Run SAST and SCA; remediate issues.
   - Add RBAC and network policies in k8s.

10) Runbook & SLOs
   - Finalize `RUNBOOK.md` with incident steps, rollback, and runbook automation.
   - Define SLOs and alerting rules.

Validation commands (local)
```
# Start service in background
python ops/run_uvicorn_bg.py start

# Run unit/integration tests
python ops/exec_pytest_subprocess.py

# Run headless team tests
python ops/run_headless_test_now.py
cat tools/headless_test_results.json

# Build Docker image
docker build -f Dockerfile.prod -t mcp/omni-gateway:local .

# Deploy to local k8s
kubectl apply -f k8s/omni-deployment.yaml
```

Notes:
- The repo currently contains safe stubs for `vision_cortex` to allow development and testing; replace them with your production module sources before shipping.
