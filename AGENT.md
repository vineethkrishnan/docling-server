# 🤖 AGENT.md - AI & Developer Guide

Guidelines for AI assistants and contributors working on this codebase.

> 📖 **For full documentation:** See [README.md](./README.md) and [docs/](./docs/)

---

## Quick Context

| Item | Value |
|------|-------|
| **Stack** | Python 3.12, FastAPI, Celery, Redis, Nginx, Docker |
| **Domain** | `docling.ayunis.de` |
| **Purpose** | Document processing API (PDF/DOCX → Markdown/JSON) |

---

## Architecture

```
Internet → Nginx (SSL) → FastAPI (8000) → Celery → Workers
                                            ↓
                                         Flower
```

- **Task queuing**: Celery with Redis broker
- **Result storage**: Celery's Redis backend
- **Monitoring**: Flower dashboard (localhost only)

---

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI endpoints, uses Celery AsyncResult |
| `app/tasks.py` | Celery tasks (results via Celery backend) |
| `app/worker.py` | Celery configuration |
| `app/transcribe.py` | Docling integration |
| `app/models.py` | Pydantic schemas |
| `docker-compose.yml` | Production services |
| `docker-compose.dev.yml` | Development services |

---

## Code Conventions

### Python Style

```python
# Type hints everywhere
def process(file: Path, options: Options) -> dict[str, Any]:
    """Google-style docstring."""
    pass

# Import order: stdlib → third-party → local
import os
from pathlib import Path

import structlog
from fastapi import FastAPI

from models import ConversionOptions
```

### Logging

```python
import structlog
logger = structlog.get_logger()

logger.info("Processing", task_id=task_id, filename=filename)
logger.error("Failed", task_id=task_id, error=str(e))
```

### Error Handling

```python
# API - use HTTPException
raise HTTPException(status_code=400, detail="Invalid input")

# Tasks - log and return error result
logger.error("Task failed", task_id=task_id, error=str(e))
return {"status": "failed", "error": str(e)}
```

---

## Adding Features

### New Endpoint

1. Add route in `app/main.py`
2. Add models in `app/models.py`
3. Test with curl or Swagger UI

### New Celery Task

1. Add task in `app/tasks.py` with `@shared_task`
2. Return dict result (stored automatically by Celery)
3. **Don't** add custom Redis storage code

```python
@shared_task(bind=True, max_retries=3)
def my_task(self, task_id: str) -> dict[str, Any]:
    # Process and return - Celery handles storage
    return {"task_id": task_id, "status": "completed", ...}
```

---

## Testing

```bash
# Dev environment
make dev-up
make dev-test

# Manual testing
curl -X POST http://localhost:8080/convert \
  -H "X-API-Key: dev-token-123" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://arxiv.org/pdf/2408.09869"}'
```

---

## Important Rules

### Do NOT:

- ❌ Commit `.env` files (contains secrets)
- ❌ Commit `certbot/conf/` (SSL keys)
- ❌ Add custom Redis storage code (use Celery backend)
- ❌ Run `make clean` in production

### Always:

- ✅ Use type hints
- ✅ Use structured logging (structlog)
- ✅ Handle errors gracefully
- ✅ Test changes locally first

---

## Documentation

| Topic | Location |
|-------|----------|
| Deployment | [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) |
| Development | [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md) |
| API Reference | [docs/API.md](./docs/API.md) |
| Configuration | [docs/CONFIGURATION.md](./docs/CONFIGURATION.md) |
| Security | [docs/SECURITY.md](./docs/SECURITY.md) |

---

## BugBot Integration

This project uses Cursor BugBot for automated PR reviews.

**Trigger manually:**
```
cursor review
```

**Configuration:**
- `.cursor/BUGBOT.md` - Project-wide rules
- `app/.cursor/BUGBOT.md` - Python-specific rules

---

## Quick Commands

```bash
# Development
make dev-up       # Start
make dev-logs     # Logs
make dev-test     # Test

# Production
make up           # Start
make status       # Status
make logs         # Logs
```
