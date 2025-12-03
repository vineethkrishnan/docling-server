"""Document transcription using Docling."""

import time
from pathlib import Path
from typing import Any

import structlog
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    PdfPipelineOptions,
    TableFormerMode,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling_core.types.doc import DoclingDocument, TableItem

from models import (
    ConversionOptions,
    DocumentChunk,
    DocumentType,
    OutputFormat,
    TableData,
)
from utils import chunk_text, detect_document_type, generate_chunk_id

logger = structlog.get_logger()


class DoclingTranscriber:
    """Handles document conversion using Docling."""

    def __init__(self):
        """Initialize the transcriber with default options."""
        self._converter: DocumentConverter | None = None
        self._initialized = False

    def _get_converter(self, options: ConversionOptions) -> DocumentConverter:
        """Get or create a document converter with the specified options."""
        # Configure PDF pipeline options
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = options.ocr_enabled
        pipeline_options.do_table_structure = options.extract_tables
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
        
        # Configure OCR if enabled
        if options.ocr_enabled:
            pipeline_options.ocr_options = EasyOcrOptions(
                force_full_page_ocr=False,
                lang=["en"],
            )
        
        # Configure image extraction
        pipeline_options.images_scale = 2.0 if options.extract_images else 1.0
        pipeline_options.generate_page_images = options.extract_images
        pipeline_options.generate_picture_images = options.extract_images

        # Create converter with PDF options
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                )
            }
        )
        
        return converter

    def convert_document(
        self,
        file_path: Path,
        task_id: str,
        options: ConversionOptions,
    ) -> dict[str, Any]:
        """
        Convert a document using Docling.
        
        Args:
            file_path: Path to the document file
            task_id: Unique task identifier
            options: Conversion options
            
        Returns:
            Dictionary containing conversion results
        """
        start_time = time.time()
        
        logger.info(
            "Starting document conversion",
            task_id=task_id,
            file_path=str(file_path),
            options=options.model_dump(),
        )

        try:
            # Detect document type
            doc_type = detect_document_type(file_path)
            
            # Get converter
            converter = self._get_converter(options)
            
            # Convert document
            result = converter.convert(file_path)
            doc: DoclingDocument = result.document
            
            # Extract content based on output format
            content = self._extract_content(doc, options.output_format)
            
            # Extract tables if requested
            tables = None
            if options.extract_tables:
                tables = self._extract_tables(doc)
            
            # Generate chunks
            chunks = None
            if options.generate_embeddings:
                chunks = self._generate_chunks(
                    content=content,
                    task_id=task_id,
                    chunk_size=options.chunk_size,
                    chunk_overlap=options.chunk_overlap,
                )
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract metadata
            metadata = self._extract_metadata(doc, result)
            
            logger.info(
                "Document conversion completed",
                task_id=task_id,
                document_type=doc_type.value,
                page_count=metadata.get("page_count"),
                processing_time_ms=processing_time_ms,
            )
            
            return {
                "content": content,
                "document_type": doc_type,
                "chunks": chunks,
                "tables": tables,
                "metadata": metadata,
                "page_count": metadata.get("page_count"),
                "processing_time_ms": processing_time_ms,
            }

        except Exception as e:
            logger.error(
                "Document conversion failed",
                task_id=task_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def _extract_content(
        self,
        doc: DoclingDocument,
        output_format: OutputFormat,
    ) -> str:
        """Extract content from DoclingDocument in the specified format."""
        if output_format == OutputFormat.MARKDOWN:
            return doc.export_to_markdown()
        elif output_format == OutputFormat.JSON:
            return doc.model_dump_json(indent=2)
        elif output_format == OutputFormat.TEXT:
            # Extract plain text by stripping markdown
            md = doc.export_to_markdown()
            # Basic markdown stripping
            lines = []
            for line in md.split("\n"):
                # Remove headers
                line = line.lstrip("#").strip()
                # Remove bold/italic
                line = line.replace("**", "").replace("*", "").replace("__", "").replace("_", "")
                # Remove links but keep text
                while "[" in line and "](" in line:
                    start = line.find("[")
                    mid = line.find("](", start)
                    end = line.find(")", mid)
                    if start >= 0 and mid > start and end > mid:
                        text = line[start + 1:mid]
                        line = line[:start] + text + line[end + 1:]
                    else:
                        break
                if line:
                    lines.append(line)
            return "\n".join(lines)
        elif output_format == OutputFormat.DOCTAGS:
            return doc.export_to_document_tokens()
        else:
            return doc.export_to_markdown()

    def _extract_tables(self, doc: DoclingDocument) -> list[TableData]:
        """Extract tables from the document."""
        tables = []
        
        for idx, (item, _) in enumerate(doc.iterate_items()):
            if isinstance(item, TableItem):
                try:
                    table_data = item.export_to_dataframe()
                    
                    # Get headers and rows
                    headers = list(table_data.columns) if not table_data.empty else []
                    rows = table_data.values.tolist() if not table_data.empty else []
                    
                    # Convert to strings
                    headers = [str(h) for h in headers]
                    rows = [[str(cell) for cell in row] for row in rows]
                    
                    # Get markdown representation
                    markdown = item.export_to_markdown()
                    
                    tables.append(TableData(
                        id=f"table_{idx}",
                        page=item.prov[0].page_no if item.prov else None,
                        headers=headers,
                        rows=rows,
                        markdown=markdown,
                    ))
                except Exception as e:
                    logger.warning(
                        "Failed to extract table",
                        table_idx=idx,
                        error=str(e),
                    )
        
        return tables

    def _generate_chunks(
        self,
        content: str,
        task_id: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[DocumentChunk]:
        """Generate document chunks for embedding."""
        raw_chunks = chunk_text(content, chunk_size, chunk_overlap)
        
        chunks = []
        for idx, (text, start, end) in enumerate(raw_chunks):
            chunks.append(DocumentChunk(
                id=generate_chunk_id(task_id, idx),
                content=text,
                metadata={
                    "chunk_index": idx,
                    "char_start": start,
                    "char_end": end,
                    "chunk_size": len(text),
                },
                embedding=None,  # Embeddings added later
            ))
        
        return chunks

    def _extract_metadata(
        self,
        doc: DoclingDocument,
        result: Any,
    ) -> dict[str, Any]:
        """Extract metadata from the document."""
        metadata: dict[str, Any] = {}
        
        # Basic metadata
        if hasattr(doc, "name"):
            metadata["title"] = doc.name
        
        # Page count
        if hasattr(result, "pages") and result.pages:
            metadata["page_count"] = len(result.pages)
        elif hasattr(doc, "pages") and doc.pages:
            metadata["page_count"] = len(doc.pages)
        else:
            # Try to infer from content
            metadata["page_count"] = 1
        
        # Document origin
        if hasattr(doc, "origin") and doc.origin:
            if hasattr(doc.origin, "filename"):
                metadata["filename"] = doc.origin.filename
            if hasattr(doc.origin, "mimetype"):
                metadata["mimetype"] = doc.origin.mimetype
        
        return metadata


# Global transcriber instance
transcriber = DoclingTranscriber()


def convert_document(
    file_path: Path,
    task_id: str,
    options: ConversionOptions,
) -> dict[str, Any]:
    """
    Convert a document using the global transcriber.
    
    This is the main entry point for document conversion.
    """
    return transcriber.convert_document(file_path, task_id, options)
