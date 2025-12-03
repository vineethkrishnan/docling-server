"""Utility functions for the Docling API."""

import hashlib
import mimetypes
import os
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx
import magic
import structlog

from models import DocumentType

logger = structlog.get_logger()

# MIME type to DocumentType mapping
MIME_TYPE_MAP: dict[str, DocumentType] = {
    "application/pdf": DocumentType.PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocumentType.DOCX,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": DocumentType.PPTX,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": DocumentType.XLSX,
    "text/html": DocumentType.HTML,
    "text/markdown": DocumentType.MD,
    "text/asciidoc": DocumentType.ASCIIDOC,
    "image/png": DocumentType.IMAGE,
    "image/jpeg": DocumentType.IMAGE,
    "image/tiff": DocumentType.IMAGE,
    "image/webp": DocumentType.IMAGE,
    "image/bmp": DocumentType.IMAGE,
}

# Extension to DocumentType mapping (fallback)
EXT_TYPE_MAP: dict[str, DocumentType] = {
    ".pdf": DocumentType.PDF,
    ".docx": DocumentType.DOCX,
    ".pptx": DocumentType.PPTX,
    ".xlsx": DocumentType.XLSX,
    ".html": DocumentType.HTML,
    ".htm": DocumentType.HTML,
    ".md": DocumentType.MD,
    ".markdown": DocumentType.MD,
    ".adoc": DocumentType.ASCIIDOC,
    ".asciidoc": DocumentType.ASCIIDOC,
    ".png": DocumentType.IMAGE,
    ".jpg": DocumentType.IMAGE,
    ".jpeg": DocumentType.IMAGE,
    ".tiff": DocumentType.IMAGE,
    ".tif": DocumentType.IMAGE,
    ".webp": DocumentType.IMAGE,
    ".bmp": DocumentType.IMAGE,
}


def generate_task_id() -> str:
    """Generate a unique task identifier."""
    return str(uuid.uuid4())


def generate_chunk_id(task_id: str, index: int) -> str:
    """Generate a unique chunk identifier."""
    return f"{task_id}_chunk_{index:04d}"


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def detect_document_type(file_path: Path) -> DocumentType:
    """Detect document type from file content and extension."""
    # Try magic detection first
    try:
        mime = magic.from_file(str(file_path), mime=True)
        if mime in MIME_TYPE_MAP:
            return MIME_TYPE_MAP[mime]
    except Exception as e:
        logger.warning("Magic detection failed", error=str(e))

    # Fallback to extension
    ext = file_path.suffix.lower()
    if ext in EXT_TYPE_MAP:
        return EXT_TYPE_MAP[ext]

    # Default to PDF if unknown
    logger.warning("Unknown document type, defaulting to PDF", extension=ext)
    return DocumentType.PDF


def get_extension_from_url(url: str) -> str:
    """Extract file extension from URL."""
    parsed = urlparse(url)
    path = parsed.path
    ext = Path(path).suffix.lower()
    return ext if ext else ".pdf"


def get_filename_from_url(url: str) -> str:
    """Extract filename from URL."""
    parsed = urlparse(url)
    path = parsed.path
    filename = Path(path).name
    return filename if filename else "document"


async def download_file(url: str, timeout: float = 300.0) -> tuple[Path, str]:
    """
    Download a file from URL to a temporary location.
    
    Returns:
        Tuple of (file_path, original_filename)
    """
    logger.info("Downloading file", url=url)
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        
        # Get filename from Content-Disposition or URL
        content_disposition = response.headers.get("content-disposition", "")
        if "filename=" in content_disposition:
            filename = content_disposition.split("filename=")[-1].strip('"\'')
        else:
            filename = get_filename_from_url(url)
        
        # Determine extension
        content_type = response.headers.get("content-type", "")
        ext = get_extension_from_url(url)
        if not ext or ext == ".":
            ext = mimetypes.guess_extension(content_type.split(";")[0]) or ".pdf"
        
        # Create temp file
        temp_dir = Path(tempfile.gettempdir()) / "docling_downloads"
        temp_dir.mkdir(exist_ok=True)
        
        temp_file = temp_dir / f"{uuid.uuid4()}{ext}"
        temp_file.write_bytes(response.content)
        
        logger.info(
            "File downloaded",
            url=url,
            filename=filename,
            size_bytes=len(response.content),
            path=str(temp_file)
        )
        
        return temp_file, filename


def cleanup_temp_file(file_path: Path) -> None:
    """Remove temporary file."""
    try:
        if file_path.exists():
            file_path.unlink()
            logger.debug("Cleaned up temp file", path=str(file_path))
    except Exception as e:
        logger.warning("Failed to cleanup temp file", path=str(file_path), error=str(e))


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50
) -> list[tuple[str, int, int]]:
    """
    Split text into overlapping chunks.
    
    Returns:
        List of tuples (chunk_text, start_char, end_char)
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        
        # Try to break at sentence or word boundary
        if end < text_length:
            # Look for sentence boundary
            for sep in [". ", ".\n", "! ", "!\n", "? ", "?\n", "\n\n"]:
                last_sep = text[start:end].rfind(sep)
                if last_sep > chunk_size * 0.5:  # At least half the chunk
                    end = start + last_sep + len(sep)
                    break
            else:
                # Look for word boundary
                last_space = text[start:end].rfind(" ")
                if last_space > chunk_size * 0.7:
                    end = start + last_space + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append((chunk, start, end))
        
        # Move start with overlap
        start = end - chunk_overlap if end < text_length else text_length
    
    return chunks


def format_bytes(size: int) -> str:
    """Format byte size to human readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing potentially dangerous characters."""
    # Remove path separators and null bytes
    for char in ["/", "\\", "\x00", "..", ":"]:
        filename = filename.replace(char, "_")
    return filename[:255]  # Limit length


def get_redis_url() -> str:
    """Get Redis URL from environment."""
    host = os.getenv("REDIS_HOST", "redis")
    port = os.getenv("REDIS_PORT", "6379")
    password = os.getenv("REDIS_PASSWORD", "")
    db = os.getenv("REDIS_DB", "0")
    
    if password:
        return f"redis://:{password}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"
