# AUTO_BUILDER - Deployment Guide

## Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Security scanning complete (Snyk)
- [ ] Documentation updated
- [ ] Environment variables configured
- [ ] Backup strategy verified

## Deployment Process

### 1. Build

```bash
# Build Docker image
docker build -t auto_builder:latest .

# Tag for registry
docker tag auto_builder:latest gcr.io/infinity-x-one-systems/auto_builder:latest
```

### 2. Push

```bash
# Push to GCR
docker push gcr.io/infinity-x-one-systems/auto_builder:latest
```

### 3. Deploy to GCP

```bash
# Deploy to Cloud Run
gcloud run deploy auto_builder \
  --image gcr.io/infinity-x-one-systems/auto_builder:latest \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 1 \
  --set-env-vars ENV=production
```

### 4. Verify

```bash
# Test health endpoint
curl https://<service-url>/health

# View logs
gcloud run logs read auto_builder --limit 50
```

## Rolling Deployment

```bash
# Gradual traffic shift (90-10)
gcloud run update-traffic auto_builder \
  --to-revisions LATEST=10,PREVIOUS=90
```

## Rollback Procedure

```bash
# Identify previous revision
gcloud run revisions list --service auto_builder

# Rollback to previous
gcloud run update-traffic auto_builder \
  --to-revisions <previous-revision-id>=100
```

## Infrastructure as Code

### Terraform

```hcl
resource "google_cloud_run_service" "auto_builder" {
  name     = "auto_builder"
  location = "us-central1"

  template {
    spec {
      containers {
        image = "gcr.io/infinity-x-one-systems/auto_builder:latest"
      }
    }
  }
}
```

### Deployment Commands

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply deployment
terraform apply
```

## Environment Configuration

### Production (.env.production)
```
ENV=production
LOG_LEVEL=info
CACHE_TTL=3600
RATE_LIMIT=1000
```

### Staging (.env.staging)
```
ENV=staging
LOG_LEVEL=debug
CACHE_TTL=1800
RATE_LIMIT=500
```

### Development (.env.development)
```
ENV=development
LOG_LEVEL=debug
CACHE_TTL=60
RATE_LIMIT=unlimited
```

## Health Checks

### Readiness Probe
```
GET /health/ready
Expected: 200 OK
Interval: 10s
```

### Liveness Probe
```
GET /health/live
Expected: 200 OK
Interval: 30s
```

## Scaling Configuration

### Auto-scaling
```yaml
minInstances: 1
maxInstances: 10
targetCPUUtilization: 80
targetMemoryUtilization: 85
```

## Monitoring & Logging

### Cloud Logging
```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision" \
  --limit 50 \
  --format json
```

### Cloud Monitoring
- CPU Utilization
- Memory Usage
- Request Latency
- Error Rate

## Disaster Recovery

### Backup
```bash
# Backup Firestore
gcloud firestore export gs://backup-bucket/backup-$(date +%s)
```

### Restore
```bash
# Restore Firestore
gcloud firestore import gs://backup-bucket/backup-<timestamp>
```

## Post-Deployment

1. **Verification**: Check health endpoints
2. **Smoke Tests**: Run basic functionality tests
3. **Monitoring**: Monitor metrics for 24 hours
4. **Communication**: Notify stakeholders

---
**Last Updated**: 2025-12-11
**Version**: 1.0.0
