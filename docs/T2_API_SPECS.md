# AUTO_BUILDER - API Specifications

## API Overview

### Base URL
```
Production: https://api.infinityxai.com/auto_builder
Staging: https://staging-api.infinityxai.com/auto_builder
Development: http://localhost:8000/auto_builder
```

### Authentication
- **Method**: Bearer Token (JWT)
- **Header**: `Authorization: Bearer <token>`
- **Token Refresh**: 24 hours expiration

### Versioning
- **Current Version**: v1
- **URL Pattern**: `/api/v1/...`
- **Deprecation Policy**: 6 months notice

## Common Response Format

```json
{
  "status": "success|error",
  "data": {},
  "error": null,
  "timestamp": "2025-12-11T01:58:54Z",
  "request_id": "req_1234567890"
}
```

## HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful operation |
| 201 | Created | Resource created |
| 204 | No Content | Success with no body |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Authentication failed |
| 403 | Forbidden | Permission denied |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limited |
| 500 | Internal Error | Server error |

## Rate Limiting

- **Limit**: 1000 requests/minute
- **Header**: `X-RateLimit-Remaining`
- **Retry-After**: 60 seconds

## Endpoints

### [GET] /health
Health check endpoint

**Response**: 200 OK
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-12-11T01:58:54Z"
}
```

### [POST] /process
Main processing endpoint

**Request**:
```json
{
  "input": "..."
}
```

**Response**: 200 OK
```json
{
  "result": "...",
  "processing_time_ms": 1234
}
```

## Error Handling

### Error Codes
| Code | Message | Description |
|------|---------|-------------|
| INVALID_INPUT | Invalid input provided | Request validation failed |
| UNAUTHORIZED | Unauthorized | Authentication required |
| NOT_FOUND | Resource not found | Requested resource doesn't exist |
| INTERNAL_ERROR | Internal server error | Server-side error occurred |

### Example Error Response
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_INPUT",
    "message": "Invalid input provided",
    "details": {}
  },
  "request_id": "req_1234567890"
}
```

## Pagination

```
GET /items?page=1&limit=20&sort=-created_at
```

**Response**:
```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

## Webhook Events

### Supported Events
- `data.created`
- `data.updated`
- `data.deleted`
- `job.completed`
- `job.failed`

### Webhook Format
```json
{
  "event": "data.created",
  "timestamp": "2025-12-11T01:58:54Z",
  "data": {}
}
```

## SDK / Client Libraries

### Python
```bash
pip install infinity-x-ai-auto_builder
```

### JavaScript
```bash
npm install @infinityxai/auto_builder
```

## API Examples

### Python
```python
import infinity_x_ai

client = infinity_x_ai.Client(api_key="sk_...")
response = client.process(input="...")
```

### JavaScript
```javascript
const client = new InfinityXAI.auto_builderClient({
  apiKey: "sk_..."
});

const response = await client.process({ input: "..." });
```

---
**Last Updated**: 2025-12-11
**Version**: 1.0.0
