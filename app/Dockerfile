# ============================================
# Docling Production Dockerfile
# Multi-stage build for optimized image size
# ============================================

# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt


# Stage 2: Runtime
FROM python:3.12-slim AS runtime

# Labels
LABEL maintainer="Docling Production Setup"
LABEL description="Production-ready Docling document processing service"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_HOME=/app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd --gid 1000 docling && \
    useradd --uid 1000 --gid docling --shell /bin/bash --create-home docling

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set work directory
WORKDIR $APP_HOME

# Copy application code
COPY --chown=docling:docling . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Create directories for temp files, downloads, and model caches
RUN mkdir -p /tmp/docling_downloads /tmp/docling_uploads \
    /home/docling/.cache /home/docling/.easyocr && \
    chown -R docling:docling /tmp/docling_downloads /tmp/docling_uploads \
    /home/docling/.cache /home/docling/.easyocr

# Switch to non-root user
USER docling

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Expose port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["./entrypoint.sh"]

# Default command (can be overridden)
CMD ["api"]
