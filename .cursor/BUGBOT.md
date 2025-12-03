# Docling Production Setup - BugBot Rules

## Project Overview

This is a production-ready document processing API powered by Docling with:
- FastAPI REST API for document conversion
- Celery workers for async document processing
- Redis for task queue and caching
- Nginx reverse proxy with SSL/TLS
- Docker Compose deployment (production & development)

**Domain:** docling.ayunis.de  
**Tech Stack:** Python 3.12, FastAPI, Celery, Redis, Docling, Docker

---

## Security Rules

### API Security
- Flag any hardcoded API tokens, passwords, or secrets
- Ensure all endpoints requiring authentication use the `verify_api_key` dependency
- Flag any endpoint that exposes sensitive data without authentication
- Check for proper input validation on all user-supplied data
- Flag any use of `eval()`, `exec()`, or `pickle.loads()` with user input

### Docker Security
- Flag containers running as root user (should use `docling` user)
- Ensure no sensitive data in Dockerfile or docker-compose files
- Flag exposed ports that shouldn't be public
- Check for proper volume permissions

### Environment Variables
- Never commit actual `.env` files (only `.env.example` or `.env.dev`)
- Flag any secrets or tokens that appear to be real values
- Ensure sensitive env vars use `${VAR:-default}` pattern in compose files

---

## Code Quality Rules

### Python Standards
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Ensure all async functions are properly awaited
- Flag any blocking I/O operations in async contexts
- Check for proper exception handling (no bare `except:` clauses)

### FastAPI Best Practices
- Use Pydantic models for request/response validation
- Ensure proper HTTP status codes are returned
- Flag any endpoint without proper error handling
- Check for CORS configuration in production endpoints

### Celery Tasks
- Ensure tasks have proper `bind=True` for access to `self`
- Flag tasks without `autoretry_for` for transient errors
- Check for proper task result cleanup/expiration
- Ensure task timeouts are configured appropriately

---

## Infrastructure Rules

### Docker Compose
- Ensure services have health checks defined
- Flag missing `restart: unless-stopped` policies
- Check for proper network isolation
- Ensure volumes are properly named and configured
- Flag any service without resource limits in production

### Nginx Configuration
- Ensure SSL/TLS is properly configured in production
- Check for proper rate limiting configuration
- Flag missing security headers
- Ensure proper proxy timeouts for long-running requests
- Check for proper upstream configuration

### Redis Configuration
- Ensure proper memory limits are set
- Check for appendonly persistence in production
- Flag missing password configuration in production

---

## Testing Guidelines

- Flag changes to core processing logic without corresponding tests
- Ensure test files follow `test_*.py` naming convention
- Check for proper mocking of external services (Redis, Docling)
- Flag any test that makes real network requests

---

## Documentation Rules

- Ensure new endpoints are documented in README.md
- Flag changes to API contracts without updating OpenAPI docs
- Check that AGENT.md is updated for significant architectural changes

---

## Specific File Rules

### `app/main.py`
- Ensure all routes have proper authentication
- Check for proper request validation
- Flag any route without proper error handling

### `app/tasks.py`
- Ensure task results are properly serialized
- Check for proper file cleanup after processing
- Flag any task without proper timeout handling

### `app/transcribe.py`
- Check for proper error handling in document conversion
- Ensure temporary files are cleaned up
- Flag any unhandled document type

### `docker-compose.yml` / `docker-compose.dev.yml`
- Ensure environment variables use proper defaults
- Check for proper service dependencies
- Flag any exposed debug ports in production compose

### `nginx/*.conf`
- Check for proper SSL configuration
- Ensure rate limiting is appropriate
- Flag any configuration that could cause security issues

---

## Ignore Patterns

Do NOT flag the following:
- Development-specific configurations in `*.dev.*` files
- Simplified auth in development environment (dev-token-123)
- Debug logging levels in development configs
- Lower resource limits in development compose
- HTTP-only configuration in nginx-dev.conf (expected for local dev)
