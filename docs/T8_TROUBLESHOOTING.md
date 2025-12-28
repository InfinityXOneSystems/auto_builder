# AUTO_BUILDER - Troubleshooting Guide

## Common Issues & Solutions

### Issue: Service Not Responding

**Symptoms**:
- Connection timeout
- 503 Service Unavailable
- Request hangs

**Diagnosis**:
```bash
# Check service status
gcloud run services describe auto_builder --region us-central1

# View recent logs
gcloud run logs read auto_builder --limit 50

# Check metrics
gcloud monitoring time-series list \
  --filter='metric.type=run.googleapis.com/request_count'
```

**Solutions**:
1. Check instance health: `curl https://<url>/health`
2. Review error logs for stack traces
3. Check resource utilization
4. Scale up if needed
5. Restart service if hung

### Issue: High Latency

**Diagnosis**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Profile endpoints
from time import time
start = time()
# ... operation
duration = time() - start
print(f"Operation took {duration}ms")
```

**Solutions**:
1. Check database query performance
2. Enable caching
3. Optimize slow endpoints
4. Scale horizontally
5. Review network latency

### Issue: Database Connection Errors

**Error Message**:
```
psycopg2.OperationalError: could not connect to server
```

**Solutions**:
```bash
# Check database status
gcloud sql instances describe auto_builder

# Check connection pool
SELECT count(*) FROM pg_stat_activity;

# Increase pool size if needed
POOL_SIZE = 20
```

### Issue: Out of Memory

**Symptoms**:
- OOMKilled pod
- Memory spike
- Slow response times

**Diagnosis**:
```bash
# Check memory usage
kubectl top pod auto_builder

# Review memory leaks
pip install tracemalloc
```

**Solutions**:
1. Increase memory limit
2. Fix memory leaks
3. Reduce batch size
4. Implement cleanup routines

### Issue: High CPU Usage

**Diagnosis**:
```bash
# Profile CPU usage
python -m cProfile src/main.py

# Identify hot paths
kernprof -l -v script.py
```

**Solutions**:
1. Optimize algorithms
2. Use caching
3. Batch processing
4. Scale horizontally
5. Use async/await

## Debugging Tips

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Debug message: %s", variable)
```

### Interactive Debugging
```python
import pdb
pdb.set_trace()  # Breakpoint
```

### Request Logging
```python
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {duration}ms")
    return response
```

## Health Checks

### Readiness Check
```bash
curl http://localhost:8000/health/ready
# Expected: 200 OK with {status: "ready"}
```

### Liveness Check
```bash
curl http://localhost:8000/health/live
# Expected: 200 OK with {status: "live"}
```

## Log Analysis

### Find Errors
```bash
gcloud logging read "severity=ERROR" --limit 100
```

### Find Specific Errors
```bash
gcloud logging read "resource.type=cloud_run_revision AND 'KEYWORD'" --limit 50
```

## Monitoring Dashboard

### Key Metrics to Watch
- Request latency (P50, P95, P99)
- Error rate
- Active connections
- Cache hit ratio
- Database connections

### Setting Alerts
```bash
gcloud monitoring alert-policies create \
  --notification-channels=<CHANNEL_ID> \
  --display-name="High Error Rate" \
  --condition-display-name="Error Rate > 1%" \
  --condition-threshold-value=1.0
```

## Support Resources

- [Documentation](../README.md)
- [API Specifications](./api/)
- [Slack Channel](#)
- [Issue Tracker](#)
- [Status Page](#)

---
**Last Updated**: 2025-12-11
**Version**: 1.0.0
