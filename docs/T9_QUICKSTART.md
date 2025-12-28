# AUTO_BUILDER - Quick Start Guide (5 Minutes)

## 1. Installation (1 minute)

```bash
# Clone
git clone https://github.com/infinityxai/auto_builder.git
cd auto_builder

# Install
pip install -r requirements.txt
```

## 2. Setup (1 minute)

```bash
# Copy config
cp .env.example .env

# Or set env var
export ENV=development
```

## 3. Run (1 minute)

```bash
# Start server
python -m uvicorn src.main:app --reload

# Open browser
# http://localhost:8000/docs
```

## 4. Test (1 minute)

```bash
# Health check
curl http://localhost:8000/health

# Example request
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'
```

## 5. Code (1 minute)

```python
# src/main.py
from fastapi import FastAPI

app = FastAPI()

@app.post("/api/v1/process")
async def process(data: dict):
    return {"result": "processed"}
```

## Next Steps

1. **Read Full Docs**: See [Architecture Guide](./architecture/)
2. **Setup Development**: See [Dev Setup Guide](./dev_setup.md)
3. **Deploy**: See [Deployment Guide](./deployment.md)
4. **API Reference**: See [API Specs](./api/)

## Common Commands

```bash
# Run tests
pytest

# Format code
black src/

# Type check
mypy src/

# Deploy
gcloud run deploy auto_builder --source .
```

## Quick Links

| Resource | Link |
|----------|------|
| API Docs | http://localhost:8000/docs |
| GitHub | https://github.com/infinityxai/auto_builder |
| Issues | https://github.com/infinityxai/auto_builder/issues |
| Discussions | https://github.com/infinityxai/auto_builder/discussions |

---
**Last Updated**: 2025-12-11
**Version**: 1.0.0
