# AUTO_BUILDER - Configuration Reference

## Environment Variables

### Core Settings
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| ENV | string | development | Environment (development, staging, production) |
| LOG_LEVEL | string | info | Logging level (debug, info, warn, error) |
| PORT | integer | 8000 | Server port |
| HOST | string | localhost | Server host |

### Database
| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| FIRESTORE_PROJECT | string | Yes | GCP Project ID |
| FIRESTORE_CREDENTIALS | JSON | Yes | Service account JSON |
| FIRESTORE_DATABASE | string | No | Database ID |

### Cache
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| REDIS_HOST | string | localhost | Redis hostname |
| REDIS_PORT | integer | 6379 | Redis port |
| REDIS_PASSWORD | string | "" | Redis password |
| CACHE_TTL | integer | 3600 | Cache TTL (seconds) |

### LLM Providers
| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| OPENAI_API_KEY | string | No | OpenAI API key |
| GROQ_API_KEY | string | No | Groq API key |
| ANTHROPIC_API_KEY | string | No | Anthropic API key |

### API Settings
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| API_RATE_LIMIT | integer | 1000 | Requests per minute |
| API_TIMEOUT | integer | 30 | Request timeout (seconds) |
| CORS_ORIGINS | string | * | CORS allowed origins |

### Security
| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| JWT_SECRET | string | Yes | JWT signing secret |
| JWT_EXPIRY | integer | 86400 | Token expiry (seconds) |
| ENCRYPTION_KEY | string | Yes | Data encryption key |

## Configuration Files

### pyproject.toml

```toml
[project]
name = "auto_builder"
version = "1.0.0"
description = "Infinity X AI - auto_builder Service"

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
]

[tool.black]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  auto_builder:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENV=development
      - LOG_LEVEL=debug
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0"]
```

## Configuration Profiles

### Development
- Debug logging enabled
- Hot reload enabled
- Mock external services
- Local database

### Staging
- Info logging
- Full feature set
- Real external services
- Staging database

### Production
- Minimal logging
- Performance optimizations
- All features enabled
- Production database

## Feature Flags

```python
FEATURES = {
    "advanced_analytics": True,
    "beta_features": False,
    "experimental_mode": False,
}
```

## SSL/TLS Configuration

### Certificate Management
```bash
# Install certificate
certbot certonly --dns-google \
  -d infinityxai.com \
  -d *.infinityxai.com
```

### Auto-renewal
```bash
certbot renew --quiet --no-eff-email
```

## Performance Tuning

### Database Connection Pool
```python
POOL_SIZE = 10
MAX_OVERFLOW = 20
POOL_TIMEOUT = 30
```

### Cache Configuration
```python
CACHE_BACKEND = "redis"
CACHE_TTL = 3600
CACHE_KEY_PREFIX = "auto_builder:"
```

---
**Last Updated**: 2025-12-11
**Version**: 1.0.0
