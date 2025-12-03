# Docling API - Developer Integration Guide

## 🌐 API Endpoints

| Environment           | URL                                      |
| --------------------- | ---------------------------------------- |
| **Production API**    | `https://docling.ayunis.de`              |
| **API Documentation** | `https://docling.ayunis.de/docs`         |
| **OpenAPI Spec**      | `https://docling.ayunis.de/openapi.json` |

---

## 🔐 Authentication

All API requests (except health checks) require an API key.

**Header:** `X-API-Key: YOUR_API_TOKEN`

```bash
curl -H "X-API-Key: YOUR_API_TOKEN" https://docling.ayunis.de/convert ...
```

---

## 📋 Available Endpoints

### Health Checks (No Auth Required)

```bash
# Liveness check
GET /health/live
# Response: {"status": "alive"}

# Readiness check
GET /health/ready
# Response: {"status": "ready"}

# Full health status
GET /health
# Response: {"status": "healthy", "version": "1.0.0", "redis_connected": true, "workers_active": 1, "uptime_seconds": 2776}
```

### Document Conversion

#### Convert from URL (Async)

```bash
POST /convert
Content-Type: application/json
X-API-Key: YOUR_API_TOKEN

{
  "url": "https://example.com/document.pdf",
  "output_format": "markdown"
}
```

**Response:**

```json
{
  "task_id": "2e9efb91-5a82-461b-ae55-1052aa57dd9b",
  "status": "pending",
  "created_at": "2025-12-03T08:30:37.374067Z",
  "message": "Task queued for processing"
}
```

#### Upload File (Async)

```bash
POST /convert/upload
Content-Type: multipart/form-data
X-API-Key: YOUR_API_TOKEN

file=@document.pdf
output_format=markdown
```

#### Batch Conversion

```bash
POST /convert/batch
Content-Type: application/json
X-API-Key: YOUR_API_TOKEN

{
  "urls": [
    "https://example.com/doc1.pdf",
    "https://example.com/doc2.pdf"
  ],
  "output_format": "markdown"
}
```

### Task Status & Results

```bash
GET /tasks/{task_id}
X-API-Key: YOUR_API_TOKEN
```

**Response (Completed):**

```json
{
  "task_id": "2e9efb91-5a82-461b-ae55-1052aa57dd9b",
  "status": "completed",
  "filename": "document.pdf",
  "document_type": "pdf",
  "content": "# Document Title\n\nConverted markdown content...",
  "chunks": null,
  "tables": [
    {
      "id": "table_1",
      "page": 1,
      "headers": ["Column1", "Column2"],
      "rows": [["data1", "data2"]],
      "markdown": "| Column1 | Column2 |\n|---------|---------|..."
    }
  ],
  "metadata": {
    "title": "Document Title",
    "page_count": 9,
    "filename": "document.pdf",
    "mimetype": "application/pdf"
  },
  "page_count": 9,
  "processing_time_ms": 25068,
  "error": null,
  "created_at": "2025-12-03T08:30:37Z",
  "completed_at": "2025-12-03T08:31:02Z"
}
```

**Possible Status Values:**

- `pending` - Task queued, waiting for worker
- `processing` - Currently being processed
- `completed` - Successfully completed
- `failed` - Processing failed (check `error` field)

### Statistics

```bash
GET /stats
X-API-Key: YOUR_API_TOKEN
```

---

## 💻 Code Examples

### Python

```python
import requests
import time

API_URL = "https://docling.ayunis.de"
API_TOKEN = "YOUR_API_TOKEN"

headers = {"X-API-Key": API_TOKEN}

# Convert a PDF from URL
def convert_document(url: str, output_format: str = "markdown"):
    # Start conversion
    response = requests.post(
        f"{API_URL}/convert",
        headers=headers,
        json={"url": url, "output_format": output_format}
    )
    task = response.json()
    task_id = task["task_id"]
    print(f"Task created: {task_id}")

    # Poll for results
    while True:
        result = requests.get(
            f"{API_URL}/tasks/{task_id}",
            headers=headers
        ).json()

        if result["status"] == "completed":
            return result
        elif result["status"] == "failed":
            raise Exception(result.get("error", "Unknown error"))

        print(f"Status: {result['status']}...")
        time.sleep(2)

# Usage
result = convert_document("https://arxiv.org/pdf/2408.09869")
print(f"Content: {result['content'][:500]}...")
print(f"Tables found: {len(result.get('tables', []))}")
print(f"Pages: {result['page_count']}")
```

### JavaScript/TypeScript

```typescript
const API_URL = "https://docling.ayunis.de";
const API_TOKEN = "YOUR_API_TOKEN";

async function convertDocument(url: string): Promise<any> {
  // Start conversion
  const response = await fetch(`${API_URL}/convert`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_TOKEN,
    },
    body: JSON.stringify({ url, output_format: "markdown" }),
  });

  const task = await response.json();
  const taskId = task.task_id;
  console.log(`Task created: ${taskId}`);

  // Poll for results
  while (true) {
    const result = await fetch(`${API_URL}/tasks/${taskId}`, {
      headers: { "X-API-Key": API_TOKEN },
    }).then((r) => r.json());

    if (result.status === "completed") {
      return result;
    } else if (result.status === "failed") {
      throw new Error(result.error || "Unknown error");
    }

    console.log(`Status: ${result.status}...`);
    await new Promise((r) => setTimeout(r, 2000));
  }
}

// Usage
const result = await convertDocument("https://arxiv.org/pdf/2408.09869");
console.log(`Content: ${result.content.substring(0, 500)}...`);
console.log(`Tables: ${result.tables?.length || 0}`);
```

### cURL

```bash
# 1. Start conversion
TASK_ID=$(curl -s -X POST "https://docling.ayunis.de/convert" \
  -H "X-API-Key: YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://arxiv.org/pdf/2408.09869", "output_format": "markdown"}' \
  | jq -r '.task_id')

echo "Task ID: $TASK_ID"

# 2. Check status (repeat until completed)
curl -s "https://docling.ayunis.de/tasks/$TASK_ID" \
  -H "X-API-Key: YOUR_API_TOKEN" | jq '.status'

# 3. Get results
curl -s "https://docling.ayunis.de/tasks/$TASK_ID" \
  -H "X-API-Key: YOUR_API_TOKEN" | jq '.'
```

### File Upload (Python)

```python
import requests

API_URL = "https://docling.ayunis.de"
API_TOKEN = "YOUR_API_TOKEN"

def upload_and_convert(file_path: str):
    with open(file_path, "rb") as f:
        response = requests.post(
            f"{API_URL}/convert/upload",
            headers={"X-API-Key": API_TOKEN},
            files={"file": f},
            data={"output_format": "markdown"}
        )
    return response.json()

# Usage
task = upload_and_convert("document.pdf")
print(f"Task ID: {task['task_id']}")
```

---

## 📊 Output Formats

| Format     | Description                                |
| ---------- | ------------------------------------------ |
| `markdown` | Clean markdown with headers, lists, tables |
| `json`     | Structured JSON with full metadata         |
| `text`     | Plain text extraction                      |

---

## 📄 Supported Document Types

- **PDF** - Full support with layout analysis, table extraction, OCR
- **DOCX** - Microsoft Word documents
- **PPTX** - PowerPoint presentations
- **Images** - PNG, JPG, TIFF (with OCR)
- **HTML** - Web pages

---

## ⚡ Performance

| Metric                  | Typical Value          |
| ----------------------- | ---------------------- |
| Simple PDF (1-5 pages)  | 5-15 seconds           |
| Complex PDF (10+ pages) | 20-60 seconds          |
| With many tables        | +2-6 seconds per table |
| Max file size           | 100 MB                 |
| Concurrent requests     | Unlimited (queued)     |

---

## 🚨 Error Handling

### HTTP Status Codes

| Code | Meaning                                |
| ---- | -------------------------------------- |
| 200  | Success                                |
| 400  | Bad request (invalid input)            |
| 401  | Unauthorized (missing/invalid API key) |
| 404  | Task not found                         |
| 429  | Rate limited                           |
| 500  | Server error                           |

### Error Response Format

```json
{
  "detail": "Error message here"
}
```

### Task Failure

```json
{
  "task_id": "...",
  "status": "failed",
  "error": "Description of what went wrong"
}
```

---

## 🔒 Rate Limits

| Endpoint      | Limit                     |
| ------------- | ------------------------- |
| General API   | 30 requests/second per IP |
| File uploads  | 5 requests/second per IP  |
| Burst allowed | Yes (50 requests burst)   |

---

## 💡 Best Practices

1. **Poll efficiently** - Use exponential backoff (2s, 4s, 8s...) when checking task status
2. **Handle failures** - Always check for `status: "failed"` and the `error` field
3. **Batch when possible** - Use `/convert/batch` for multiple documents
4. **Cache results** - Store completed conversions to avoid re-processing
5. **Set timeouts** - Large documents may take 60+ seconds

---

## 🆘 Support

- **API Documentation**: https://docling.ayunis.de/docs
- **Health Status**: https://docling.ayunis.de/health
- **Issues**: Contact your administrator

---

## 📝 Quick Reference

```bash
# Health check
curl https://docling.ayunis.de/health/live

# Convert URL
curl -X POST https://docling.ayunis.de/convert \
  -H "X-API-Key: TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/doc.pdf"}'

# Get result
curl https://docling.ayunis.de/tasks/TASK_ID \
  -H "X-API-Key: TOKEN"
```
