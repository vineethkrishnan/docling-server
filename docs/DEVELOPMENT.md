# 🔧 Development Guide

Complete guide for setting up the local development environment, testing, and contributing.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Development Environment](#development-environment)
- [Running Locally](#running-locally)
- [Testing](#testing)
- [Debugging](#debugging)
- [Code Style & Conventions](#code-style--conventions)
- [Adding Features](#adding-features)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

Get the dev environment running in 2 minutes:

```bash
# Clone repository
git clone https://github.com/your-repo/docling-production-setup.git
cd docling-production-setup

# Start development environment
make dev-up

# Verify it's running
make dev-test

# View all endpoints
make dev-status
```

**Development Endpoints:**

| Service | URL | Description |
|---------|-----|-------------|
| API | http://localhost:8080 | Main API (via Nginx) |
| API Direct | http://localhost:8000 | Direct access (debugging) |
| API Docs | http://localhost:8080/docs | Swagger UI |
| Flower | http://localhost:5555 | Task monitoring |

**Default Credentials:**
- API Token: `dev-token-123`
- Flower: `admin` / `admin`

---

## Development Environment

### Prerequisites

```bash
# macOS
brew install docker docker-compose python@3.12

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose python3.12 python3.12-venv

# Verify
docker --version          # 24.0+
docker compose version    # v2.20+
python3 --version         # 3.12+
```

### Project Structure

```
docling-production-setup/
├── app/                      # Application code
│   ├── main.py              # FastAPI application
│   ├── worker.py            # Celery configuration
│   ├── tasks.py             # Async tasks
│   ├── transcribe.py        # Docling integration
│   ├── embeddings.py        # Vector embeddings
│   ├── models.py            # Pydantic schemas
│   ├── utils.py             # Utilities
│   ├── Dockerfile           # Production image
│   ├── Dockerfile.dev       # Development image
│   └── requirements.txt     # Dependencies
├── nginx/
│   ├── nginx.conf           # Production config
│   └── nginx-dev.conf       # Development config
├── docs/                    # Documentation
├── docker-compose.yml       # Production services
├── docker-compose.dev.yml   # Development services
└── Makefile                 # Commands
```

### Environment Files

| File | Purpose |
|------|---------|
| `.env` | Root config (gitignored) |
| `app/.env.example` | Production template |
| `app/.env.dev` | Development defaults |

---

## Running Locally

### Option 1: Docker (Recommended)

```bash
# Build and start all services
make dev-up

# View logs (follow mode)
make dev-logs

# Stop services
make dev-down

# Clean everything (including volumes)
make dev-clean
```

### Option 2: Docker with Rebuild

```bash
# Rebuild images (after code changes)
make dev-build

# Restart specific service
docker compose -f docker-compose.dev.yml restart api

# Rebuild and restart single service
docker compose -f docker-compose.dev.yml up -d --build api
```

### Option 3: Local Python (Advanced)

For faster iteration without Docker:

```bash
# 1. Start Redis only
docker compose -f docker-compose.dev.yml up -d redis

# 2. Create virtual environment
cd app
python3.12 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install watchfiles ipython ipdb  # Dev tools

# 4. Set environment
export REDIS_HOST=localhost
export REDIS_PORT=6379
export DOCLING_API_TOKEN=dev-token-123
export ENV=development

# 5. Run API (with auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 6. Run worker (in separate terminal)
celery -A worker.celery_app worker --loglevel=debug -E
```

---

## Testing

### Test API Endpoints

```bash
# Health check
make dev-test

# Or manually
curl http://localhost:8080/health
```

### Test Document Conversion

**Convert from URL:**

```bash
# Submit conversion task
curl -X POST http://localhost:8080/convert \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-token-123" \
  -d '{
    "url": "https://arxiv.org/pdf/2408.09869",
    "options": {
      "output_format": "markdown",
      "extract_tables": true
    }
  }'

# Response:
# {"task_id": "abc123...", "status": "pending", ...}

# Check task status
curl http://localhost:8080/tasks/abc123... \
  -H "X-API-Key: dev-token-123"
```

**Upload a file:**

```bash
# Upload PDF
curl -X POST http://localhost:8080/convert/upload \
  -H "X-API-Key: dev-token-123" \
  -F "file=@/path/to/document.pdf" \
  -F "output_format=markdown" \
  -F "extract_tables=true"
```

**Batch conversion:**

```bash
curl -X POST http://localhost:8080/convert/batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-token-123" \
  -d '{
    "urls": [
      "https://example.com/doc1.pdf",
      "https://example.com/doc2.pdf"
    ],
    "options": {
      "output_format": "json"
    }
  }'
```

### Test with Embeddings

```bash
curl -X POST http://localhost:8080/convert \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-token-123" \
  -d '{
    "url": "https://arxiv.org/pdf/2408.09869",
    "options": {
      "generate_embeddings": true,
      "chunk_size": 512,
      "chunk_overlap": 50
    }
  }'
```

### Monitor Tasks in Flower

1. Open http://localhost:5555
2. Login: `admin` / `admin`
3. Click "Tasks" to see processing status
4. Click individual tasks for details

---

## Debugging

### View Logs

```bash
# All services
make dev-logs

# Specific service
make dev-logs-api
make dev-logs-worker

# Last 50 lines with timestamps
docker compose -f docker-compose.dev.yml logs --tail=50 -t api
```

### Shell Access

```bash
# API container
make dev-shell-api

# Worker container
make dev-shell-worker

# Redis CLI
make dev-shell-redis

# Example: Check Redis keys
redis-cli KEYS "*"
```

### Debug Python Code

**Using ipdb (in container):**

```python
# Add to your code
import ipdb; ipdb.set_trace()
```

Then attach to container:
```bash
docker attach docling-api-dev
# Use ipdb commands: n (next), s (step), c (continue), q (quit)
```

**Using VS Code Remote Containers:**

1. Install "Dev Containers" extension
2. Open command palette: "Dev Containers: Attach to Running Container"
3. Select `docling-api-dev`
4. Set breakpoints and debug

### Check Celery Tasks

```bash
# List active tasks
docker compose -f docker-compose.dev.yml exec worker \
  celery -A worker.celery_app inspect active

# List scheduled tasks
docker compose -f docker-compose.dev.yml exec worker \
  celery -A worker.celery_app inspect scheduled

# Purge all tasks (careful!)
docker compose -f docker-compose.dev.yml exec worker \
  celery -A worker.celery_app purge
```

### Inspect Redis

```bash
# Connect to Redis
make dev-shell-redis

# Useful commands
KEYS *                           # List all keys
KEYS celery-task-meta-*          # List task results
GET celery-task-meta-<task-id>   # Get specific result
LLEN celery                      # Queue length
INFO                             # Redis stats
```

---

## Code Style & Conventions

### Python Style

```python
# Use type hints everywhere
def process_document(
    file_path: Path,
    options: ConversionOptions,
) -> dict[str, Any]:
    """
    Process a document file.
    
    Args:
        file_path: Path to the document
        options: Conversion options
        
    Returns:
        Dictionary with conversion results
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    pass
```

### Import Order

```python
# 1. Standard library
import os
import json
from pathlib import Path
from typing import Any

# 2. Third-party
import structlog
from fastapi import FastAPI, HTTPException
from celery import shared_task

# 3. Local
from models import ConversionOptions
from utils import generate_task_id
```

### Logging

```python
import structlog
logger = structlog.get_logger()

# Use structured logging
logger.info("Processing document", task_id=task_id, filename=filename)
logger.error("Failed to process", task_id=task_id, error=str(e))
```

### Error Handling

```python
# API endpoints - use HTTPException
@app.post("/convert")
async def convert(request: ConversionRequest):
    if not request.url:
        raise HTTPException(
            status_code=400,
            detail="URL is required"
        )

# Tasks - log and re-raise for retry
@shared_task(bind=True, max_retries=3)
def process_task(self, task_id: str):
    try:
        # process...
    except TransientError as e:
        logger.warning("Retrying task", task_id=task_id, error=str(e))
        raise self.retry(exc=e)
```

---

## Adding Features

### New API Endpoint

1. **Add route in `app/main.py`:**

```python
@app.post("/convert/advanced", response_model=TaskResponse)
async def convert_advanced(
    request: AdvancedConversionRequest,
    api_key: str = Security(verify_api_key),
):
    """Advanced conversion with extra options."""
    task_id = generate_task_id()
    # ... implementation
    return TaskResponse(task_id=task_id, status=TaskStatus.PENDING)
```

2. **Add models in `app/models.py`:**

```python
class AdvancedConversionRequest(BaseModel):
    url: str
    options: ConversionOptions
    advanced_option: str = "default"
```

3. **Test the endpoint:**

```bash
curl -X POST http://localhost:8080/convert/advanced \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-token-123" \
  -d '{"url": "https://example.com/doc.pdf", "advanced_option": "value"}'
```

### New Celery Task

1. **Add task in `app/tasks.py`:**

```python
@shared_task(bind=True, max_retries=3)
def process_special_task(
    self,
    task_id: str,
    special_param: str,
) -> dict[str, Any]:
    """Process with special handling."""
    logger.info("Processing special task", task_id=task_id)
    
    try:
        # Your processing logic
        result = {"task_id": task_id, "status": "completed"}
        return result
    except Exception as e:
        logger.error("Task failed", task_id=task_id, error=str(e))
        raise self.retry(exc=e)
```

2. **Call from API:**

```python
from tasks import process_special_task

@app.post("/special")
async def special_endpoint(request: SpecialRequest):
    task_id = generate_task_id()
    process_special_task.delay(task_id=task_id, special_param=request.param)
    return {"task_id": task_id}
```

### New Document Format

1. **Update `app/utils.py`:**

```python
MIME_TYPE_MAP = {
    # ... existing types
    "application/x-newformat": "newformat",
}

EXT_TYPE_MAP = {
    # ... existing extensions
    ".newext": "newformat",
}
```

2. **Add handling in `app/transcribe.py`:**

```python
def convert_document(file_path: Path, task_id: str, options: ConversionOptions):
    doc_type = detect_document_type(file_path)
    
    if doc_type == "newformat":
        return convert_newformat(file_path, options)
    # ... existing logic
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose -f docker-compose.dev.yml logs api

# Common issues:
# - Port already in use
sudo lsof -i :8000
# - Missing dependencies
make dev-build
```

### Redis Connection Failed

```bash
# Check Redis is running
docker compose -f docker-compose.dev.yml ps redis

# Test connection
docker compose -f docker-compose.dev.yml exec redis redis-cli ping
# Should return: PONG
```

### Task Stuck in Pending

```bash
# Check worker is running
docker compose -f docker-compose.dev.yml ps worker

# Check worker logs
make dev-logs-worker

# Check queue
docker compose -f docker-compose.dev.yml exec redis redis-cli LLEN celery
```

### Model Download Issues

First run downloads ~2GB of models. If stuck:

```bash
# Check worker logs for download progress
make dev-logs-worker

# Clear cache and retry
docker compose -f docker-compose.dev.yml down -v
make dev-up
```

### Hot Reload Not Working

The `./app` directory is mounted in dev mode. If changes aren't detected:

```bash
# Restart the service
docker compose -f docker-compose.dev.yml restart api

# Or rebuild
make dev-build
make dev-up
```

---

## Development Commands Reference

```bash
# Lifecycle
make dev-up          # Start all services
make dev-down        # Stop all services
make dev-restart     # Restart services
make dev-clean       # Remove containers & volumes

# Building
make dev-build       # Build/rebuild images

# Logs
make dev-logs        # All logs (follow)
make dev-logs-api    # API logs
make dev-logs-worker # Worker logs

# Testing
make dev-test        # Test health endpoints
make dev-status      # Show status & URLs

# Debugging
make dev-shell-api   # Shell into API
make dev-shell-worker # Shell into worker
make dev-shell-redis # Redis CLI
```

---

**Next:** [API Reference](./API.md) | [Configuration](./CONFIGURATION.md)
