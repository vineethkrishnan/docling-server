# ⚙️ Configuration Reference

Complete configuration options for the Docling API.

---

## Table of Contents

- [Environment Variables](#environment-variables)
- [Nginx Configuration](#nginx-configuration)
- [Celery Configuration](#celery-configuration)
- [Docker Configuration](#docker-configuration)
- [Conversion Options](#conversion-options)

---

## Environment Variables

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCLING_API_TOKEN` | *required* | API authentication token (min 16 chars for production) |
| `ENV` | `production` | Environment: `production` or `development` |
| `HOST` | `0.0.0.0` | API host binding |
| `PORT` | `8000` | API port |
| `WORKERS` | `2` | Number of Uvicorn workers |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |

### Redis Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `redis` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | `` | Redis password (optional) |
| `REDIS_DB` | `0` | Redis database number |

### Celery Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_CONCURRENCY` | `2` | Tasks per worker |
| `CELERY_QUEUE` | `docling` | Task queue name |
| `CELERY_LOGLEVEL` | `info` | Log level: `debug`, `info`, `warning`, `error` |
| `PRELOAD_MODELS` | `true` | Preload ML models on worker startup |

### Embedding Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Sentence transformer model |

**Available models:**

| Model | Dimensions | Speed | Quality |
|-------|------------|-------|---------|
| `all-MiniLM-L6-v2` | 384 | Fast | Good |
| `all-mpnet-base-v2` | 768 | Medium | Better |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | Medium | Multilingual |

### Flower Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `FLOWER_USER` | `admin` | Flower dashboard username |
| `FLOWER_PASSWORD` | `admin` | Flower dashboard password |
| `FLOWER_PORT` | `5555` | Flower dashboard port |

### SSL/Domain Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DOMAIN` | `docling.ayunis.de` | Your domain name |
| `LETSENCRYPT_EMAIL` | `` | Email for Let's Encrypt notifications |

---

## Example Configuration Files

### Production `.env`

```bash
# ===========================================
# Production Configuration
# ===========================================

# API (REQUIRED - generate with: openssl rand -hex 32)
DOCLING_API_TOKEN=your-secure-64-character-hex-token-here

# Environment
ENV=production
WORKERS=2
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Celery
CELERY_CONCURRENCY=2
CELERY_LOGLEVEL=info
PRELOAD_MODELS=true

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Flower (change from defaults!)
FLOWER_USER=admin
FLOWER_PASSWORD=your-flower-password

# Domain
DOMAIN=docling.yourdomain.com
LETSENCRYPT_EMAIL=admin@yourdomain.com
```

### Development `.env`

```bash
# ===========================================
# Development Configuration
# ===========================================

DOCLING_API_TOKEN=dev-token-123
ENV=development
WORKERS=1
CORS_ORIGINS=http://localhost:8080,http://localhost:3000

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

CELERY_CONCURRENCY=1
CELERY_LOGLEVEL=debug
PRELOAD_MODELS=false

FLOWER_USER=admin
FLOWER_PASSWORD=admin
```

---

## Nginx Configuration

### Rate Limiting

Located in `nginx/nginx.conf`:

```nginx
# Rate limit zones (adjust based on traffic)
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=5r/s;
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;
```

**Parameters:**

| Parameter | Description |
|-----------|-------------|
| `rate=30r/s` | 30 requests per second per IP |
| `zone:10m` | 10MB memory for tracking (about 160k IPs) |
| `burst=50` | Allow 50 request burst |
| `nodelay` | Don't delay burst requests |

### Adjusting Rate Limits

**For higher traffic:**

```nginx
# In http block
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;

# In location block
limit_req zone=api_limit burst=200 nodelay;
limit_conn conn_limit 100;
```

**Disable rate limiting:**

```nginx
# Comment out in location blocks:
# limit_req zone=api_limit burst=50 nodelay;
# limit_conn conn_limit 50;
```

### Timeouts

```nginx
# Client timeouts
client_body_timeout 900s;
client_max_body_size 100M;

# Proxy timeouts (for long-running conversions)
proxy_connect_timeout 60s;
proxy_send_timeout 900s;
proxy_read_timeout 900s;
```

**For very large documents (increase timeouts):**

```nginx
client_body_timeout 1800s;  # 30 minutes
proxy_read_timeout 1800s;
```

### SSL Configuration

```nginx
# Protocols
ssl_protocols TLSv1.2 TLSv1.3;

# Ciphers (modern configuration)
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:...;

# Session settings
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
```

---

## Celery Configuration

Located in `app/worker.py`:

### Task Settings

```python
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,           # Acknowledge after completion
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    task_time_limit=900,           # 15 minute hard limit
    task_soft_time_limit=540,      # 9 minute soft limit (warning)
    
    # Results
    result_expires=604800,         # 7 days
    result_extended=True,          # Store additional metadata
)
```

### Worker Settings

```python
celery_app.conf.update(
    worker_prefetch_multiplier=1,     # One task at a time (for heavy tasks)
    worker_concurrency=2,             # From CELERY_CONCURRENCY env
    worker_max_tasks_per_child=50,    # Restart after 50 tasks (memory)
)
```

### Task Routing

```python
task_routes={
    "tasks.process_document_task": {"queue": "docling"},
    "tasks.process_batch_task": {"queue": "docling"},
}
task_default_queue="docling"
```

### Adjusting for Performance

**For more throughput (lighter documents):**

```python
worker_prefetch_multiplier=4,    # Prefetch more tasks
worker_concurrency=4,            # More concurrent tasks
task_time_limit=300,             # Shorter timeout
```

**For heavy documents:**

```python
worker_prefetch_multiplier=1,    # One at a time
worker_concurrency=1,            # Single task
task_time_limit=1800,            # 30 minute timeout
worker_max_tasks_per_child=10,   # Restart frequently
```

---

## Docker Configuration

### Resource Limits

In `docker-compose.yml`:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 1G

  worker:
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 2G
```

**Recommended limits:**

| Service | Min RAM | Recommended | Heavy Usage |
|---------|---------|-------------|-------------|
| API | 1 GB | 2-4 GB | 4 GB |
| Worker | 2 GB | 4-8 GB | 16 GB |
| Redis | 256 MB | 512 MB | 1 GB |

### Volume Mounts

```yaml
volumes:
  # Redis persistence
  redis-data:
    driver: local
  
  # Temporary files (downloads, processing)
  docling-temp:
    driver: local
  docling-uploads:
    driver: local
  
  # Model cache (shared between workers)
  model-cache:
    driver: local
  easyocr-cache:
    driver: local
```

### Health Checks

```yaml
api:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
    interval: 30s
    timeout: 10s
    start_period: 60s
    retries: 3
```

---

## Conversion Options

### Output Formats

| Format | Description | Use Case |
|--------|-------------|----------|
| `markdown` | Formatted Markdown | Human-readable, documentation |
| `json` | Structured JSON | API integrations, parsing |
| `text` | Plain text | Simple extraction |
| `doctags` | Document tags format | Advanced processing |

### Table Extraction

```json
{
  "options": {
    "extract_tables": true
  }
}
```

**Output:**

```json
{
  "tables": [
    {
      "id": "table_1",
      "page": 1,
      "headers": ["Name", "Value"],
      "rows": [
        ["Item 1", "100"],
        ["Item 2", "200"]
      ]
    }
  ]
}
```

### OCR Settings

```json
{
  "options": {
    "ocr_enabled": true
  }
}
```

OCR is automatically applied to:
- Scanned PDFs
- Image files (PNG, JPG, TIFF)
- PDFs with embedded images

### Embedding Generation

```json
{
  "options": {
    "generate_embeddings": true,
    "chunk_size": 512,
    "chunk_overlap": 50
  }
}
```

**Parameters:**

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| `chunk_size` | 100-4096 | 512 | Characters per chunk |
| `chunk_overlap` | 0-500 | 50 | Overlap between chunks |

**Output:**

```json
{
  "chunks": [
    {
      "id": "chunk-0",
      "content": "First chunk of text...",
      "metadata": {
        "page": 1,
        "position": 0,
        "char_start": 0,
        "char_end": 512
      },
      "embedding": [0.123, -0.456, ...]  // 384 dimensions
    }
  ]
}
```

---

## Performance Tuning

### For High Volume (Many Small Documents)

```bash
# .env
WORKERS=4
CELERY_CONCURRENCY=4
PRELOAD_MODELS=true

# nginx.conf
rate=100r/s
burst=200
```

### For Large Documents (PDFs 100+ pages)

```bash
# .env
WORKERS=2
CELERY_CONCURRENCY=1
PRELOAD_MODELS=true

# worker.py
task_time_limit=1800
task_soft_time_limit=1500
worker_max_tasks_per_child=10
```

### For Low Memory Environments

```bash
# .env
WORKERS=1
CELERY_CONCURRENCY=1
PRELOAD_MODELS=false  # Load models on demand
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # Smaller model

# docker-compose.yml
memory: 2G (worker)
```

---

**Next:** [Deployment Guide](./DEPLOYMENT.md) | [Security Guide](./SECURITY.md)
