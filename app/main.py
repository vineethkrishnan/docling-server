"""FastAPI application for Docling document processing."""

import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import structlog
from celery.result import AsyncResult
from fastapi import FastAPI, File, HTTPException, Query, Security, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from models import (
    BatchConversionRequest,
    BatchTaskResponse,
    ConversionOptions,
    ConversionRequest,
    ConversionResult,
    HealthResponse,
    StatsResponse,
    TaskResponse,
    TaskStatus,
)
from worker import celery_app
from tasks import process_batch_task, process_document_task
from utils import generate_task_id, sanitize_filename

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "docling_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "docling_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)
DOCUMENT_PROCESSING_TIME = Histogram(
    "docling_document_processing_seconds",
    "Document processing time in seconds",
)

# API configuration
API_VERSION = "1.0.0"
API_TITLE = "Docling Document Processing API"
API_DESCRIPTION = """
Production-ready document processing API powered by Docling.

## Features
- Convert PDF, DOCX, PPTX, XLSX, HTML, and images to Markdown, JSON, or plain text
- Extract tables with structure preservation
- Generate vector embeddings for document chunks
- Async processing with task status tracking
- Webhook notifications for task completion
- Batch processing support

## Authentication
All endpoints require an API key passed via the `X-API-Key` header.

## Monitoring
- Flower Dashboard: Monitor Celery tasks at /flower (if enabled)
- Prometheus metrics: Available at /metrics
"""

# API Key security
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key():
    """Get API key from environment."""
    token = os.getenv("DOCLING_API_TOKEN")
    if not token:
        raise RuntimeError("DOCLING_API_TOKEN environment variable is required")
    return token


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Verify the API key."""
    expected_key = get_api_key()
    if not api_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key


# Application startup time
_startup_time: float = 0


def _validate_security_settings():
    """Validate security settings on startup."""
    env = os.getenv("ENV", "production")
    warnings = []
    
    # Check API token
    api_token = os.getenv("DOCLING_API_TOKEN", "")
    weak_tokens = ["changeme", "dev-token-123", "test", "admin", "password", ""]
    if api_token.lower() in weak_tokens or len(api_token) < 16:
        if env == "production":
            raise RuntimeError(
                "DOCLING_API_TOKEN is weak or missing. "
                "Production requires a secure token (min 16 characters)."
            )
        warnings.append("API token is weak - acceptable for development only")
    
    # Check Flower credentials
    flower_user = os.getenv("FLOWER_USER", "admin")
    flower_pass = os.getenv("FLOWER_PASSWORD", "admin")
    if flower_user == "admin" and flower_pass == "admin":
        if env == "production":
            warnings.append("Flower using default admin/admin credentials")
    
    return warnings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global _startup_time
    _startup_time = time.time()
    
    logger.info("Starting Docling API", version=API_VERSION)
    
    # Validate security settings
    try:
        warnings = _validate_security_settings()
        for warning in warnings:
            logger.warning("Security warning", message=warning)
    except RuntimeError as e:
        logger.error("Security validation failed", error=str(e))
        raise
    
    # Test Celery broker connection
    try:
        celery_app.control.ping(timeout=1)
        logger.info("Celery broker connection established")
    except Exception as e:
        logger.warning("Celery broker not immediately available", error=str(e))
    
    yield
    
    logger.info("Shutting down Docling API")


# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Health & Metrics Endpoints ==============

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Check service health status."""
    # Check Celery broker connection
    broker_connected = False
    workers_active = 0
    
    try:
        inspect = celery_app.control.inspect(timeout=2)
        ping_response = celery_app.control.ping(timeout=2)
        if ping_response:
            broker_connected = True
            workers_active = len(ping_response)
    except Exception:
        pass
    
    return HealthResponse(
        status="healthy" if broker_connected else "degraded",
        version=API_VERSION,
        redis_connected=broker_connected,  # Keep field name for compatibility
        workers_active=workers_active,
        uptime_seconds=time.time() - _startup_time,
    )


@app.get("/health/live", tags=["Health"])
async def liveness():
    """Kubernetes liveness probe."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def readiness():
    """Kubernetes readiness probe."""
    try:
        ping_response = celery_app.control.ping(timeout=2)
        if ping_response:
            return {"status": "ready"}
        raise Exception("No workers available")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Not ready: {str(e)}",
        )


@app.get("/metrics", tags=["Metrics"])
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/stats", response_model=StatsResponse, tags=["Metrics"])
async def get_statistics(api_key: str = Security(verify_api_key)):
    """Get processing statistics from Celery."""
    try:
        inspect = celery_app.control.inspect(timeout=2)
        
        # Get active tasks
        active = inspect.active() or {}
        active_count = sum(len(tasks) for tasks in active.values())
        
        # Get reserved (queued) tasks
        reserved = inspect.reserved() or {}
        reserved_count = sum(len(tasks) for tasks in reserved.values())
        
        # Get worker stats
        stats = inspect.stats() or {}
        total_completed = 0
        for worker_stats in stats.values():
            if "total" in worker_stats:
                total_completed += sum(worker_stats["total"].values())
        
        return StatsResponse(
            total_tasks=total_completed + active_count + reserved_count,
            completed_tasks=total_completed,
            failed_tasks=0,  # Would need to track separately
            pending_tasks=reserved_count + active_count,
            avg_processing_time_ms=0,  # Would need to calculate from results
        )
    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        return StatsResponse(
            total_tasks=0,
            completed_tasks=0,
            failed_tasks=0,
            pending_tasks=0,
            avg_processing_time_ms=0,
        )


# ============== Document Processing Endpoints ==============

@app.post(
    "/convert",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Conversion"],
)
async def convert_document_url(
    request: ConversionRequest,
    api_key: str = Security(verify_api_key),
):
    """
    Convert a document from URL.
    
    Submits a document conversion task and returns a task ID for tracking.
    Use the `/tasks/{task_id}` endpoint to check status and retrieve results.
    """
    if not request.url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is required",
        )
    
    task_id = generate_task_id()
    created_at = datetime.now(timezone.utc)
    
    # Queue the task
    process_document_task.delay(
        task_id=task_id,
        url=request.url,
        options_dict=request.options.model_dump(),
        webhook_url=request.webhook_url,
        metadata=request.metadata,
    )
    
    logger.info(
        "Document conversion task created",
        task_id=task_id,
        url=request.url,
    )
    
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        created_at=created_at,
        message="Task queued for processing",
    )


@app.post(
    "/convert/upload",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Conversion"],
)
async def convert_document_upload(
    file: UploadFile = File(..., description="Document file to convert"),
    output_format: str = Query(default="markdown", description="Output format"),
    extract_tables: bool = Query(default=True, description="Extract tables"),
    extract_images: bool = Query(default=False, description="Extract images"),
    ocr_enabled: bool = Query(default=True, description="Enable OCR"),
    generate_embeddings: bool = Query(default=False, description="Generate embeddings"),
    chunk_size: int = Query(default=512, ge=100, le=4096, description="Chunk size"),
    chunk_overlap: int = Query(default=50, ge=0, le=500, description="Chunk overlap"),
    webhook_url: str | None = Query(default=None, description="Webhook URL"),
    api_key: str = Security(verify_api_key),
):
    """
    Convert an uploaded document.
    
    Upload a document file and submit it for conversion.
    Use the `/tasks/{task_id}` endpoint to check status and retrieve results.
    """
    task_id = generate_task_id()
    created_at = datetime.now(timezone.utc)
    
    # Save uploaded file to temp location
    filename = sanitize_filename(file.filename or "document")
    temp_dir = Path(tempfile.gettempdir()) / "docling_uploads"
    temp_dir.mkdir(exist_ok=True)
    
    temp_file = temp_dir / f"{task_id}_{filename}"
    
    try:
        content = await file.read()
        temp_file.write_bytes(content)
    except Exception as e:
        logger.error("Failed to save uploaded file", error=str(e), filename=filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to save uploaded file. Please try again.",
        )
    
    # Build options
    options = ConversionOptions(
        output_format=output_format,
        extract_tables=extract_tables,
        extract_images=extract_images,
        ocr_enabled=ocr_enabled,
        generate_embeddings=generate_embeddings,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    
    # Queue the task
    process_document_task.delay(
        task_id=task_id,
        file_path=str(temp_file),
        filename=filename,
        options_dict=options.model_dump(),
        webhook_url=webhook_url,
    )
    
    logger.info(
        "Document upload task created",
        task_id=task_id,
        filename=filename,
        size_bytes=len(content),
    )
    
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        created_at=created_at,
        message="Task queued for processing",
    )


@app.post(
    "/convert/batch",
    response_model=BatchTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Conversion"],
)
async def convert_documents_batch(
    request: BatchConversionRequest,
    api_key: str = Security(verify_api_key),
):
    """
    Convert multiple documents in batch.
    
    Submit multiple document URLs for conversion.
    Each document gets its own task ID for individual tracking.
    """
    batch_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)
    
    # Create task configs
    task_configs = []
    task_ids = []
    
    for url in request.urls:
        task_id = generate_task_id()
        task_ids.append(task_id)
        task_configs.append({
            "task_id": task_id,
            "url": url,
            "options": request.options.model_dump(),
        })
    
    # Queue batch processing
    process_batch_task.delay(
        batch_id=batch_id,
        task_configs=task_configs,
        webhook_url=request.webhook_url,
    )
    
    logger.info(
        "Batch conversion task created",
        batch_id=batch_id,
        num_documents=len(request.urls),
    )
    
    return BatchTaskResponse(
        batch_id=batch_id,
        task_ids=task_ids,
        total_documents=len(request.urls),
        status=TaskStatus.PENDING,
        created_at=created_at,
    )


# ============== Task Management Endpoints ==============

@app.get(
    "/tasks/{task_id}",
    response_model=ConversionResult,
    tags=["Tasks"],
)
async def get_task_status(
    task_id: str,
    api_key: str = Security(verify_api_key),
):
    """
    Get task status and results.
    
    Retrieve the current status and results (if completed) for a task.
    Results are fetched from Celery's result backend.
    """
    # Find the Celery task by looking for it in active/reserved tasks
    # or by checking the result backend
    try:
        inspect = celery_app.control.inspect(timeout=2)
        
        # Check active tasks
        active = inspect.active() or {}
        for worker, tasks in active.items():
            for task in tasks:
                if task.get("kwargs", {}).get("task_id") == task_id:
                    return ConversionResult(
                        task_id=task_id,
                        status=TaskStatus.PROCESSING,
                        created_at=datetime.now(timezone.utc),
                    )
        
        # Check reserved (queued) tasks
        reserved = inspect.reserved() or {}
        for worker, tasks in reserved.items():
            for task in tasks:
                if task.get("kwargs", {}).get("task_id") == task_id:
                    return ConversionResult(
                        task_id=task_id,
                        status=TaskStatus.PENDING,
                        created_at=datetime.now(timezone.utc),
                    )
    except Exception as e:
        logger.warning("Failed to inspect tasks", error=str(e))
    
    # Check result backend for completed tasks
    # We need to find the Celery task ID that has our task_id in kwargs
    # For now, iterate through recent results (this is a limitation)
    
    # Try to find result by iterating through known task patterns
    # This is a workaround since we use custom task_id, not Celery's task_id
    try:
        # Search in result backend using pattern matching
        backend = celery_app.backend
        
        # Try to get all keys (works with Redis backend)
        if hasattr(backend, 'client'):
            redis_client = backend.client
            keys = redis_client.keys("celery-task-meta-*")
            
            for key in keys:
                try:
                    data = redis_client.get(key)
                    if data:
                        import json
                        result_data = json.loads(data)
                        result = result_data.get("result", {})
                        
                        if isinstance(result, dict) and result.get("task_id") == task_id:
                            # Found the task
                            created_at = result.get("created_at")
                            if isinstance(created_at, str):
                                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                            
                            completed_at = result.get("completed_at")
                            if isinstance(completed_at, str):
                                completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                            
                            return ConversionResult(
                                task_id=result.get("task_id", task_id),
                                status=TaskStatus(result.get("status", "pending")),
                                filename=result.get("filename"),
                                document_type=result.get("document_type"),
                                content=result.get("content"),
                                chunks=result.get("chunks"),
                                tables=result.get("tables"),
                                metadata=result.get("metadata", {}),
                                page_count=result.get("page_count"),
                                processing_time_ms=result.get("processing_time_ms"),
                                error=result.get("error"),
                                created_at=created_at or datetime.now(timezone.utc),
                                completed_at=completed_at,
                            )
                except Exception:
                    continue
    except Exception as e:
        logger.error("Failed to search results", error=str(e))
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task {task_id} not found",
    )


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Tasks"],
)
async def delete_task(
    task_id: str,
    api_key: str = Security(verify_api_key),
):
    """
    Delete a task and its results.
    
    Remove task data from Celery's result backend.
    """
    try:
        backend = celery_app.backend
        
        if hasattr(backend, 'client'):
            redis_client = backend.client
            keys = redis_client.keys("celery-task-meta-*")
            
            for key in keys:
                try:
                    data = redis_client.get(key)
                    if data:
                        import json
                        result_data = json.loads(data)
                        result = result_data.get("result", {})
                        
                        if isinstance(result, dict) and result.get("task_id") == task_id:
                            redis_client.delete(key)
                            logger.info("Task deleted", task_id=task_id)
                            return
                except Exception:
                    continue
    except Exception as e:
        logger.error("Failed to delete task", error=str(e))
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task {task_id} not found",
    )


# ============== Error Handlers ==============

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error("Unexpected error", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "status_code": 500},
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENV", "production") == "development",
        workers=int(os.getenv("WORKERS", 1)),
    )
