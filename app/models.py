"""Pydantic models for the Docling API."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OutputFormat(str, Enum):
    """Supported output formats."""
    MARKDOWN = "markdown"
    JSON = "json"
    TEXT = "text"
    DOCTAGS = "doctags"


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    HTML = "html"
    IMAGE = "image"
    ASCIIDOC = "asciidoc"
    MD = "md"


# ============== Request Models ==============

class ConversionOptions(BaseModel):
    """Options for document conversion."""
    output_format: OutputFormat = Field(
        default=OutputFormat.MARKDOWN,
        description="Output format for the converted document"
    )
    extract_tables: bool = Field(
        default=True,
        description="Extract tables from the document"
    )
    extract_images: bool = Field(
        default=False,
        description="Extract and process images from the document"
    )
    ocr_enabled: bool = Field(
        default=True,
        description="Enable OCR for scanned documents and images"
    )
    generate_embeddings: bool = Field(
        default=False,
        description="Generate vector embeddings for the document chunks"
    )
    chunk_size: int = Field(
        default=512,
        ge=100,
        le=4096,
        description="Size of text chunks for embedding generation"
    )
    chunk_overlap: int = Field(
        default=50,
        ge=0,
        le=500,
        description="Overlap between consecutive chunks"
    )


class ConversionRequest(BaseModel):
    """Request model for document conversion."""
    url: str | None = Field(
        default=None,
        description="URL of the document to convert"
    )
    options: ConversionOptions = Field(
        default_factory=ConversionOptions,
        description="Conversion options"
    )
    webhook_url: str | None = Field(
        default=None,
        description="Webhook URL to notify when processing is complete"
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Custom metadata to attach to the task"
    )


class BatchConversionRequest(BaseModel):
    """Request model for batch document conversion."""
    urls: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of document URLs to convert"
    )
    options: ConversionOptions = Field(
        default_factory=ConversionOptions,
        description="Conversion options applied to all documents"
    )
    webhook_url: str | None = Field(
        default=None,
        description="Webhook URL to notify when all processing is complete"
    )


# ============== Response Models ==============

class TaskResponse(BaseModel):
    """Response model for task creation."""
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    created_at: datetime = Field(..., description="Task creation timestamp")
    message: str = Field(..., description="Status message")


class DocumentChunk(BaseModel):
    """A chunk of processed document with optional embedding."""
    id: str = Field(..., description="Chunk identifier")
    content: str = Field(..., description="Text content of the chunk")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Chunk metadata (page, position, etc.)"
    )
    embedding: list[float] | None = Field(
        default=None,
        description="Vector embedding if requested"
    )


class TableData(BaseModel):
    """Extracted table data."""
    id: str = Field(..., description="Table identifier")
    page: int | None = Field(default=None, description="Page number")
    headers: list[str] = Field(default_factory=list, description="Table headers")
    rows: list[list[str]] = Field(default_factory=list, description="Table rows")
    markdown: str = Field(..., description="Markdown representation")


class ConversionResult(BaseModel):
    """Result of document conversion."""
    task_id: str = Field(..., description="Task identifier")
    status: TaskStatus = Field(..., description="Task status")
    filename: str | None = Field(default=None, description="Original filename")
    document_type: DocumentType | None = Field(
        default=None,
        description="Detected document type"
    )
    content: str | None = Field(
        default=None,
        description="Converted content in requested format"
    )
    chunks: list[DocumentChunk] | None = Field(
        default=None,
        description="Document chunks with optional embeddings"
    )
    tables: list[TableData] | None = Field(
        default=None,
        description="Extracted tables"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Document metadata"
    )
    page_count: int | None = Field(default=None, description="Number of pages")
    processing_time_ms: int | None = Field(
        default=None,
        description="Processing time in milliseconds"
    )
    error: str | None = Field(default=None, description="Error message if failed")
    created_at: datetime = Field(..., description="Task creation timestamp")
    completed_at: datetime | None = Field(
        default=None,
        description="Task completion timestamp"
    )


class BatchTaskResponse(BaseModel):
    """Response for batch conversion request."""
    batch_id: str = Field(..., description="Batch identifier")
    task_ids: list[str] = Field(..., description="Individual task identifiers")
    total_documents: int = Field(..., description="Total documents in batch")
    status: TaskStatus = Field(..., description="Overall batch status")
    created_at: datetime = Field(..., description="Batch creation timestamp")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    redis_connected: bool = Field(..., description="Redis connection status")
    workers_active: int = Field(..., description="Number of active workers")
    uptime_seconds: float = Field(..., description="Service uptime")


class StatsResponse(BaseModel):
    """Statistics response."""
    total_tasks: int = Field(..., description="Total tasks processed")
    pending_tasks: int = Field(..., description="Tasks waiting to be processed")
    completed_tasks: int = Field(..., description="Successfully completed tasks")
    failed_tasks: int = Field(..., description="Failed tasks")
    avg_processing_time_ms: float = Field(
        ...,
        description="Average processing time"
    )
