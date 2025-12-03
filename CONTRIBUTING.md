# Contributing to Docling Production Setup

Thank you for your interest in contributing! This document provides guidelines
and instructions for contributing to this project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Reporting Issues](#reporting-issues)

---

## Code of Conduct

This project and everyone participating in it is governed by our
[Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to
uphold this code. Please report unacceptable behavior to vineeth.nk@locaboo.com.

---

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/docling-production-setup.git
   cd docling-production-setup
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL-OWNER/docling-production-setup.git
   ```

---

## Development Setup

### Prerequisites

- Docker & Docker Compose v2+
- Python 3.12+
- Git

### Setup Development Environment

```bash
# Start development environment
make dev-up

# Verify it's working
make dev-test

# View logs
make dev-logs
```

### Running Tests

```bash
# Run all health checks
make dev-test

# Test specific endpoint
curl -X POST http://localhost:8080/convert \
  -H "X-API-Key: dev-token-123" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://arxiv.org/pdf/2408.09869"}'
```

For detailed development instructions, see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-new-format` - New features
- `fix/upload-timeout` - Bug fixes
- `docs/update-api-reference` - Documentation
- `refactor/simplify-task-handling` - Code refactoring

### Commit Messages

Write clear, concise commit messages:

```
type: short description

Longer description if needed. Explain what and why,
not how (the code shows how).

Fixes #123
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat: add support for EPUB documents

fix: resolve timeout issue with large PDF uploads

docs: update API reference with batch endpoint examples
```

---

## Pull Request Process

### Before Submitting

1. **Update your branch** with the latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Test your changes**:
   ```bash
   make dev-up
   make dev-test
   ```

3. **Check for linting issues** (if applicable):
   ```bash
   # In app directory
   pip install ruff
   ruff check .
   ```

4. **Update documentation** if you've changed:
   - API endpoints
   - Configuration options
   - Environment variables
   - Dependencies

### Submitting a Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature
   ```

2. Open a Pull Request on GitHub

3. Fill in the PR template with:
   - Description of changes
   - Related issue(s)
   - Testing performed
   - Checklist completion

4. Wait for review and address feedback

### PR Review Criteria

Your PR will be reviewed for:

- [ ] Code quality and style
- [ ] Test coverage
- [ ] Documentation updates
- [ ] Security considerations
- [ ] Performance impact
- [ ] Breaking changes

---

## Style Guidelines

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use type hints for all functions
- Use Google-style docstrings
- Maximum line length: 88 characters (Black default)

```python
def process_document(
    file_path: Path,
    options: ConversionOptions,
) -> dict[str, Any]:
    """
    Process a document file.

    Args:
        file_path: Path to the document file.
        options: Conversion options.

    Returns:
        Dictionary containing conversion results.

    Raises:
        FileNotFoundError: If the file doesn't exist.
    """
    pass
```

### Import Order

```python
# 1. Standard library
import os
from pathlib import Path

# 2. Third-party
import structlog
from fastapi import FastAPI

# 3. Local
from models import ConversionOptions
```

### Logging

Use structured logging with `structlog`:

```python
import structlog
logger = structlog.get_logger()

# Good
logger.info("Processing document", task_id=task_id, filename=filename)

# Avoid
print(f"Processing {filename}")
```

### Error Handling

```python
# API endpoints
raise HTTPException(status_code=400, detail="Invalid input")

# Background tasks
try:
    result = process()
except Exception as e:
    logger.error("Processing failed", error=str(e))
    return {"status": "failed", "error": str(e)}
```

---

## Reporting Issues

### Bug Reports

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) and include:

- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Docker version, etc.)
- Relevant logs

### Feature Requests

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md) and include:

- Clear description of the feature
- Use case / motivation
- Proposed solution (if any)
- Alternative solutions considered

### Security Issues

**Do NOT open public issues for security vulnerabilities.**

Email security concerns directly to: vineeth.nk@locaboo.com

---

## Questions?

- Check the [documentation](docs/)
- Open a [discussion](https://github.com/OWNER/docling-production-setup/discussions)
- Email: vineeth.nk@locaboo.com

Thank you for contributing! 🎉
