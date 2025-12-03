# Docling App - BugBot Rules (Python/FastAPI)

## Python Specific Rules

### Async/Await
- Flag any blocking I/O operations (file reads, network calls) in async functions
- Use `aiofiles` for file operations in async contexts
- Use `httpx` with async client for HTTP requests
- Flag any `time.sleep()` - use `asyncio.sleep()` instead

### Type Safety
- All function parameters must have type hints
- All return types must be specified
- Use `Optional[T]` for nullable types
- Use `Pydantic` models instead of raw dicts for API data

### Error Handling
```python
# BAD - bare except
except:
    pass

# GOOD - specific exceptions
except (ValueError, KeyError) as e:
    logger.error(f"Error: {e}")
    raise HTTPException(status_code=400, detail=str(e))
```

### Logging
- Use structured logging with `structlog` or standard `logging`
- Include request IDs in log messages
- Never log sensitive data (tokens, passwords, PII)
- Use appropriate log levels (debug/info/warning/error)

---

## FastAPI Specific Rules

### Request Validation
- All request bodies must use Pydantic models
- Use `Query()`, `Path()`, `Body()` for parameter validation
- Set appropriate `min_length`, `max_length`, `ge`, `le` constraints

### Response Models
- All endpoints must specify `response_model`
- Use `status_code` parameter for non-200 responses
- Return proper error responses with `HTTPException`

### Dependencies
- Use dependency injection for shared logic
- The `verify_api_key` dependency is required for protected endpoints
- Flag any endpoint without proper authentication dependency

### Background Tasks
- Use Celery for long-running tasks, not FastAPI background tasks
- Return task_id immediately for async operations
- Provide status endpoints for task monitoring

---

## Celery Task Rules

### Task Definition
```python
# REQUIRED patterns for tasks:
@celery_app.task(
    bind=True,                    # Access to self
    autoretry_for=(Exception,),   # Auto-retry on failures
    retry_backoff=True,           # Exponential backoff
    retry_kwargs={'max_retries': 3},
    soft_time_limit=300,          # Soft timeout
    time_limit=600,               # Hard timeout
)
def process_document(self, ...):
    ...
```

### Result Handling
- Task results must be JSON-serializable
- Clean up temporary files in `finally` block
- Update task state with `self.update_state()` for progress

### Error Handling
- Catch and log all exceptions
- Return structured error responses
- Use `self.retry()` for transient failures

---

## File Handling Rules

### Temporary Files
```python
# REQUIRED - Always clean up temp files
try:
    with tempfile.NamedTemporaryFile(delete=False) as f:
        # process file
finally:
    if os.path.exists(temp_path):
        os.unlink(temp_path)
```

### Uploads
- Validate file size before processing
- Check file extension/MIME type
- Use secure filenames (sanitize user input)
- Store in designated upload directory only

---

## Security Rules

### Input Validation
- Sanitize all user input
- Validate URLs before downloading
- Check file sizes before processing
- Never use user input in file paths without validation

### Secrets
- Never hardcode secrets
- Use environment variables for all credentials
- Flag any string that looks like a token/password

### Dependencies
- Keep dependencies updated (check requirements.txt)
- Flag known vulnerable package versions
- Prefer well-maintained packages

---

## Docling Integration

### Document Processing
- Always wrap Docling calls in try/except
- Handle unsupported document types gracefully
- Set appropriate timeouts for large documents
- Clean up Docling converter after use

### Memory Management
- Process large documents in chunks if possible
- Monitor memory usage for batch operations
- Use garbage collection for large objects

---

## Testing Requirements

Changes to these files require tests:
- `main.py` - API endpoint tests
- `tasks.py` - Celery task tests (use `celery.contrib.testing`)
- `transcribe.py` - Document conversion tests
- `embeddings.py` - Embedding generation tests
- `utils.py` - Utility function unit tests
