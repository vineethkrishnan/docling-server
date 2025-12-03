# 📖 API Reference

Complete API documentation for the Docling Document Processing API.

---

## Table of Contents

- [Authentication](#authentication)
- [Endpoints Overview](#endpoints-overview)
- [Document Conversion](#document-conversion)
- [Task Management](#task-management)
- [Health & Monitoring](#health--monitoring)
- [Error Handling](#error-handling)
- [Examples](#examples)

---

## Authentication

All API endpoints (except health probes) require authentication via the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-token" https://api.example.com/...
```

### Authentication Errors

| Status | Description |
|--------|-------------|
| `401 Unauthorized` | Missing or invalid API key |

```json
{
  "detail": "Invalid or missing API key",
  "status_code": 401
}
```

---

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/convert` | Convert document from URL |
| `POST` | `/convert/upload` | Convert uploaded document |
| `POST` | `/convert/batch` | Batch convert multiple documents |
| `GET` | `/tasks/{task_id}` | Get task status and results |
| `DELETE` | `/tasks/{task_id}` | Delete task results |
| `GET` | `/health` | Health check |
| `GET` | `/health/live` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/stats` | Processing statistics |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/docs` | Interactive API documentation |

---

## Document Conversion

### Convert from URL

**`POST /convert`**

Submit a document URL for conversion.

**Request Body:**

```json
{
  "url": "https://example.com/document.pdf",
  "options": {
    "output_format": "markdown",
    "extract_tables": true,
    "extract_images": false,
    "ocr_enabled": true,
    "generate_embeddings": false,
    "chunk_size": 512,
    "chunk_overlap": 50
  },
  "webhook_url": "https://your-server.com/webhook",
  "metadata": {
    "custom_field": "value"
  }
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | URL of the document to convert |
| `options` | object | No | Conversion options (see below) |
| `webhook_url` | string | No | URL to receive completion notification |
| `metadata` | object | No | Custom metadata to include in results |

**Conversion Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `output_format` | string | `markdown` | Output format: `markdown`, `json`, `text`, `doctags` |
| `extract_tables` | boolean | `true` | Extract tables from documents |
| `extract_images` | boolean | `false` | Extract images |
| `ocr_enabled` | boolean | `true` | Enable OCR for scanned documents |
| `generate_embeddings` | boolean | `false` | Generate vector embeddings |
| `chunk_size` | integer | `512` | Chunk size for embeddings (100-4096) |
| `chunk_overlap` | integer | `50` | Overlap between chunks (0-500) |

**Response:** `202 Accepted`

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "message": "Task queued for processing"
}
```

---

### Upload Document

**`POST /convert/upload`**

Upload and convert a document file.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | Document file to convert |
| `output_format` | string | No | Output format (default: `markdown`) |
| `extract_tables` | boolean | No | Extract tables (default: `true`) |
| `extract_images` | boolean | No | Extract images (default: `false`) |
| `ocr_enabled` | boolean | No | Enable OCR (default: `true`) |
| `generate_embeddings` | boolean | No | Generate embeddings (default: `false`) |
| `chunk_size` | integer | No | Chunk size (default: `512`) |
| `chunk_overlap` | integer | No | Chunk overlap (default: `50`) |
| `webhook_url` | string | No | Webhook URL for completion |

**Example:**

```bash
curl -X POST https://api.example.com/convert/upload \
  -H "X-API-Key: your-token" \
  -F "file=@document.pdf" \
  -F "output_format=markdown" \
  -F "extract_tables=true"
```

**Response:** `202 Accepted`

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "message": "Task queued for processing"
}
```

---

### Batch Conversion

**`POST /convert/batch`**

Submit multiple documents for conversion.

**Request Body:**

```json
{
  "urls": [
    "https://example.com/doc1.pdf",
    "https://example.com/doc2.pdf",
    "https://example.com/doc3.pdf"
  ],
  "options": {
    "output_format": "markdown",
    "extract_tables": true
  },
  "webhook_url": "https://your-server.com/batch-complete"
}
```

**Response:** `202 Accepted`

```json
{
  "batch_id": "batch-123-456-789",
  "task_ids": [
    "task-1-uuid",
    "task-2-uuid",
    "task-3-uuid"
  ],
  "total_documents": 3,
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## Task Management

### Get Task Status

**`GET /tasks/{task_id}`**

Retrieve task status and results.

**Response (Pending):**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Response (Processing):**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Response (Completed):**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "filename": "document.pdf",
  "document_type": "pdf",
  "content": "# Document Title\n\nDocument content in markdown...",
  "chunks": [
    {
      "id": "chunk-0",
      "content": "First chunk of text...",
      "metadata": {"page": 1, "position": 0},
      "embedding": [0.1, 0.2, ...]
    }
  ],
  "tables": [
    {
      "id": "table_1",
      "page": 1,
      "headers": ["Column 1", "Column 2"],
      "rows": [["Value 1", "Value 2"]]
    }
  ],
  "metadata": {
    "title": "Document Title",
    "author": "Author Name",
    "page_count": 10
  },
  "page_count": 10,
  "processing_time_ms": 5432,
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:30:05Z"
}
```

**Response (Failed):**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error": "Failed to download document: Connection timeout",
  "processing_time_ms": 30000,
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:30:30Z"
}
```

---

### Delete Task

**`DELETE /tasks/{task_id}`**

Delete task results from storage.

**Response:** `204 No Content`

**Error:** `404 Not Found` if task doesn't exist.

---

## Health & Monitoring

### Health Check

**`GET /health`**

Full health status including dependencies.

**Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "redis_connected": true,
  "workers_active": 2,
  "uptime_seconds": 3600.5
}
```

| Status | Description |
|--------|-------------|
| `healthy` | All systems operational |
| `degraded` | Some issues but operational |

---

### Liveness Probe

**`GET /health/live`**

Kubernetes liveness probe. Returns 200 if the service is running.

```json
{"status": "alive"}
```

---

### Readiness Probe

**`GET /health/ready`**

Kubernetes readiness probe. Returns 200 if ready to accept traffic.

```json
{"status": "ready"}
```

Returns `503` if not ready (e.g., Redis not connected).

---

### Statistics

**`GET /stats`**

Processing statistics.

**Response:**

```json
{
  "total_tasks": 1000,
  "completed_tasks": 950,
  "failed_tasks": 20,
  "pending_tasks": 30,
  "avg_processing_time_ms": 5500
}
```

---

### Prometheus Metrics

**`GET /metrics`**

Prometheus-compatible metrics.

```
# HELP docling_requests_total Total number of requests
# TYPE docling_requests_total counter
docling_requests_total{method="POST",endpoint="/convert",status="202"} 100

# HELP docling_request_latency_seconds Request latency in seconds
# TYPE docling_request_latency_seconds histogram
docling_request_latency_seconds_bucket{method="POST",endpoint="/convert",le="0.1"} 50

# HELP docling_document_processing_seconds Document processing time
# TYPE docling_document_processing_seconds histogram
docling_document_processing_seconds_bucket{le="5"} 80
```

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Error description",
  "status_code": 400
}
```

### Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `202` | Accepted (task queued) |
| `204` | No Content (successful deletion) |
| `400` | Bad Request (invalid input) |
| `401` | Unauthorized (invalid API key) |
| `404` | Not Found (task not found) |
| `429` | Too Many Requests (rate limited) |
| `500` | Internal Server Error |
| `503` | Service Unavailable |

---

## Examples

### Python

```python
import requests

API_URL = "https://api.example.com"
API_KEY = "your-api-token"

headers = {"X-API-Key": API_KEY}

# Submit conversion
response = requests.post(
    f"{API_URL}/convert",
    headers=headers,
    json={
        "url": "https://arxiv.org/pdf/2408.09869",
        "options": {"output_format": "markdown"}
    }
)
task_id = response.json()["task_id"]
print(f"Task ID: {task_id}")

# Poll for results
import time
while True:
    result = requests.get(
        f"{API_URL}/tasks/{task_id}",
        headers=headers
    ).json()
    
    if result["status"] == "completed":
        print(result["content"][:500])
        break
    elif result["status"] == "failed":
        print(f"Error: {result['error']}")
        break
    
    time.sleep(2)
```

### JavaScript/Node.js

```javascript
const API_URL = "https://api.example.com";
const API_KEY = "your-api-token";

async function convertDocument(url) {
  // Submit task
  const submitResponse = await fetch(`${API_URL}/convert`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify({
      url: url,
      options: { output_format: "markdown" },
    }),
  });
  
  const { task_id } = await submitResponse.json();
  console.log(`Task ID: ${task_id}`);
  
  // Poll for results
  while (true) {
    const resultResponse = await fetch(`${API_URL}/tasks/${task_id}`, {
      headers: { "X-API-Key": API_KEY },
    });
    const result = await resultResponse.json();
    
    if (result.status === "completed") {
      return result;
    } else if (result.status === "failed") {
      throw new Error(result.error);
    }
    
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
}

convertDocument("https://arxiv.org/pdf/2408.09869")
  .then((result) => console.log(result.content.slice(0, 500)))
  .catch((err) => console.error(err));
```

### cURL

```bash
# Convert document
TASK_ID=$(curl -s -X POST https://api.example.com/convert \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-token" \
  -d '{"url": "https://arxiv.org/pdf/2408.09869"}' | jq -r '.task_id')

echo "Task ID: $TASK_ID"

# Wait and check status
sleep 30
curl -s https://api.example.com/tasks/$TASK_ID \
  -H "X-API-Key: your-token" | jq '.status, .content[:200]'
```

### Webhook Handler (Python Flask)

```python
from flask import Flask, request

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json
    task_id = data["task_id"]
    status = data["status"]
    
    if status == "completed":
        content = data["content"]
        # Process the converted document
        print(f"Task {task_id} completed: {len(content)} chars")
    else:
        error = data.get("error")
        print(f"Task {task_id} failed: {error}")
    
    return {"received": True}

if __name__ == "__main__":
    app.run(port=5000)
```

---

**Next:** [Configuration Reference](./CONFIGURATION.md) | [Development Guide](./DEVELOPMENT.md)
