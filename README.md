# 🔖 Docling Production Setup

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A production-ready document processing API powered by [Docling](https://github.com/DS4SD/docling).

Convert PDF, DOCX, PPTX, and more to Markdown, JSON, or plain text with table extraction, OCR, and vector embeddings.

---

## ✨ Features

- **Document Conversion** - PDF, DOCX, PPTX, XLSX, HTML, Images → Markdown/JSON/Text
- **Table Extraction** - Preserve table structure from documents
- **OCR Support** - Process scanned documents and images
- **Vector Embeddings** - Generate embeddings for RAG applications
- **Async Processing** - Background task processing with Celery
- **Batch Processing** - Convert multiple documents in parallel
- **Monitoring** - Flower dashboard + Prometheus metrics
- **SSL/TLS** - Automatic certificates with Let's Encrypt

---

## 🚀 Quick Start

### Production

```bash
# 1. Configure
cp app/.env.example .env
export DOCLING_API_TOKEN=$(openssl rand -hex 32)
nano .env  # Add your token and domain

# 2. Deploy
make init

# 3. Verify
curl https://yourdomain.com/health
```

📖 **Full guide:** [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md)

### Development

```bash
# Start dev environment
make dev-up

# Check status
make dev-status

# Test API
curl -X POST http://localhost:8080/convert \
  -H "X-API-Key: dev-token-123" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://arxiv.org/pdf/2408.09869"}'
```

📖 **Full guide:** [docs/DEVELOPMENT.md](./docs/DEVELOPMENT.md)

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [**Deployment Guide**](./docs/DEPLOYMENT.md) | Production setup, SSL, scaling, maintenance |
| [**Development Guide**](./docs/DEVELOPMENT.md) | Local setup, testing, debugging, contributing |
| [**API Reference**](./docs/API.md) | Endpoints, request/response formats, examples |
| [**Configuration**](./docs/CONFIGURATION.md) | Environment variables, nginx, Celery settings |
| [**Security Guide**](./docs/SECURITY.md) | Authentication, secrets, security checklist |
| [**AGENT.md**](./AGENT.md) | Guidelines for AI assistants and contributors |

---

## 🏗️ Architecture

```
Internet → Nginx (SSL) → FastAPI → Celery (Redis) → Workers
                                         ↓
                                      Flower
```

| Service | Purpose |
|---------|---------|
| **Nginx** | Reverse proxy, SSL, rate limiting |
| **API** | FastAPI REST endpoints |
| **Worker** | Document processing (Celery) |
| **Redis** | Message broker & result backend |
| **Flower** | Task monitoring dashboard |

---

## 📡 API Overview

```bash
# Convert document
curl -X POST https://api.example.com/convert \
  -H "X-API-Key: your-token" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/doc.pdf"}'

# Check status
curl https://api.example.com/tasks/{task_id} \
  -H "X-API-Key: your-token"
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/convert` | POST | Convert from URL |
| `/convert/upload` | POST | Upload & convert |
| `/convert/batch` | POST | Batch conversion |
| `/tasks/{id}` | GET | Get results |
| `/health` | GET | Health check |
| `/docs` | GET | API documentation |

📖 **Full reference:** [docs/API.md](./docs/API.md)

---

## ⚙️ Configuration

Key settings in `.env`:

```bash
DOCLING_API_TOKEN=your-secure-token  # Required
WORKERS=2                             # API workers
CELERY_CONCURRENCY=2                  # Tasks per worker
EMBEDDING_MODEL=all-MiniLM-L6-v2     # Embedding model
```

📖 **All options:** [docs/CONFIGURATION.md](./docs/CONFIGURATION.md)

---

## 🔒 Security

- ✅ API key authentication required
- ✅ Startup validation rejects weak tokens
- ✅ Flower bound to localhost only
- ✅ TLS 1.2/1.3 with strong ciphers
- ✅ Rate limiting per IP

```bash
# Generate secure token
openssl rand -hex 32
```

📖 **Security checklist:** [docs/SECURITY.md](./docs/SECURITY.md)

---

## 🔧 Commands

```bash
# Production
make up          # Start services
make down        # Stop services
make status      # Check status
make logs        # View logs
make monitoring  # Enable Flower dashboard

# Development
make dev-up      # Start dev environment
make dev-down    # Stop dev environment
make dev-test    # Test endpoints
make dev-logs    # View logs

# Maintenance
make ssl-renew   # Renew certificates
make scale N=3   # Scale workers
make backup-certs # Backup SSL certs
```

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) first.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📞 Support

- **Documentation:** [docs/](./docs/)
- **Bug Reports:** [GitHub Issues](../../issues)
- **Feature Requests:** [GitHub Issues](../../issues)
- **Security Issues:** vineeth.nk@locaboo.com (private)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Acknowledgments

- [Docling](https://github.com/DS4SD/docling) - Document processing engine (MIT)
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Celery](https://docs.celeryq.dev/) - Task queue
- [Sentence Transformers](https://sbert.net/) - Embeddings
