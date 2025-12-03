"""Celery tasks for document processing."""

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog
from celery import shared_task

from embeddings import embed_chunks
from models import ConversionOptions, ConversionResult, DocumentChunk, TaskStatus
from transcribe import convert_document
from utils import cleanup_temp_file, download_file

logger = structlog.get_logger()


async def _send_webhook(webhook_url: str, payload: dict[str, Any]) -> None:
    """Send webhook notification."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            logger.info("Webhook sent successfully", url=webhook_url)
    except Exception as e:
        logger.error("Webhook failed", url=webhook_url, error=str(e))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_task(
    self,
    task_id: str,
    url: str | None = None,
    file_path: str | None = None,
    filename: str | None = None,
    options_dict: dict[str, Any] | None = None,
    webhook_url: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Process a document conversion task.
    
    Args:
        task_id: Unique task identifier
        url: URL to download document from
        file_path: Local file path (if already downloaded)
        filename: Original filename
        options_dict: Conversion options as dictionary
        webhook_url: Optional webhook URL for notification
        metadata: Optional custom metadata
        
    Returns:
        Conversion result dictionary (stored by Celery in result backend)
    """
    start_time = time.time()
    temp_file: Path | None = None
    
    logger.info(
        "Processing document task",
        task_id=task_id,
        url=url,
        file_path=file_path,
    )
    
    try:
        # Parse options
        options = ConversionOptions(**(options_dict or {}))
        
        # Get the file
        if url:
            # Download from URL
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                temp_file, filename = loop.run_until_complete(download_file(url))
            finally:
                loop.close()
            file_to_process = temp_file
        elif file_path:
            file_to_process = Path(file_path)
            if not file_to_process.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
        else:
            raise ValueError("Either url or file_path must be provided")
        
        # Convert document
        result = convert_document(file_to_process, task_id, options)
        
        # Generate embeddings if requested
        if options.generate_embeddings and result.get("chunks"):
            chunks = result["chunks"]
            embedded_chunks = embed_chunks(chunks)
            result["chunks"] = [
                chunk.model_dump() if isinstance(chunk, DocumentChunk) else chunk
                for chunk in embedded_chunks
            ]
        
        # Prepare final result
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        final_result = {
            "task_id": task_id,
            "status": TaskStatus.COMPLETED.value,
            "filename": filename,
            "document_type": result.get("document_type", "unknown"),
            "content": result.get("content"),
            "chunks": result.get("chunks"),
            "tables": [t.model_dump() if hasattr(t, "model_dump") else t for t in (result.get("tables") or [])],
            "metadata": {**(metadata or {}), **result.get("metadata", {})},
            "page_count": result.get("page_count"),
            "processing_time_ms": processing_time_ms,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Send webhook if configured
        if webhook_url:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_send_webhook(webhook_url, final_result))
            finally:
                loop.close()
        
        logger.info(
            "Document processing completed",
            task_id=task_id,
            processing_time_ms=processing_time_ms,
        )
        
        return final_result
        
    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        error_result = {
            "task_id": task_id,
            "status": TaskStatus.FAILED.value,
            "filename": filename,
            "document_type": None,
            "content": None,
            "chunks": None,
            "tables": None,
            "metadata": metadata,
            "page_count": None,
            "processing_time_ms": processing_time_ms,
            "error": str(e),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        
        logger.error(
            "Document processing failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        
        # Send webhook with error
        if webhook_url:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_send_webhook(webhook_url, error_result))
            finally:
                loop.close()
        
        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return error_result
        
    finally:
        # Cleanup temp file
        if temp_file:
            cleanup_temp_file(temp_file)


@shared_task
def process_batch_task(
    batch_id: str,
    task_configs: list[dict[str, Any]],
    webhook_url: str | None = None,
) -> dict[str, Any]:
    """
    Process a batch of document conversions.
    
    Args:
        batch_id: Unique batch identifier
        task_configs: List of task configurations
        webhook_url: Optional webhook URL for batch completion notification
        
    Returns:
        Batch result summary
    """
    logger.info(
        "Processing batch",
        batch_id=batch_id,
        num_documents=len(task_configs),
    )
    
    results = []
    for config in task_configs:
        task_id = config.get("task_id")
        try:
            result = process_document_task.delay(
                task_id=task_id,
                url=config.get("url"),
                options_dict=config.get("options"),
                webhook_url=None,  # Don't send individual webhooks
                metadata=config.get("metadata"),
            )
            results.append({"task_id": task_id, "celery_task_id": result.id})
        except Exception as e:
            logger.error(
                "Failed to queue batch task",
                batch_id=batch_id,
                task_id=task_id,
                error=str(e),
            )
            results.append({"task_id": task_id, "error": str(e)})
    
    batch_result = {
        "batch_id": batch_id,
        "total_documents": len(task_configs),
        "queued_tasks": results,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    return batch_result
