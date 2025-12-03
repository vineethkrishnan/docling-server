#!/bin/bash
set -e

# ============================================
# Docling Entrypoint Script
# Handles different service modes
# ============================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for Redis to be ready
wait_for_redis() {
    log_info "Waiting for Redis to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python -c "import redis; r = redis.from_url('${REDIS_URL:-redis://redis:6379/0}'); r.ping()" 2>/dev/null; then
            log_info "Redis is ready!"
            return 0
        fi
        log_warn "Redis not ready, attempt $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "Redis failed to become ready after $max_attempts attempts"
    return 1
}

# Download and cache embedding model
preload_models() {
    log_info "Preloading embedding model..."
    python -c "
from sentence_transformers import SentenceTransformer
import os
model_name = os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
print(f'Loading model: {model_name}')
model = SentenceTransformer(model_name)
print(f'Model loaded with dimension: {model.get_sentence_embedding_dimension()}')
" || log_warn "Failed to preload embedding model"
}

# Main entrypoint logic
case "${1:-api}" in
    api)
        log_info "Starting Docling API server..."
        wait_for_redis
        
        # Get configuration from environment
        HOST="${HOST:-0.0.0.0}"
        PORT="${PORT:-8000}"
        WORKERS="${WORKERS:-2}"
        
        log_info "Configuration: HOST=$HOST, PORT=$PORT, WORKERS=$WORKERS"
        
        exec uvicorn main:app \
            --host "$HOST" \
            --port "$PORT" \
            --workers "$WORKERS" \
            --loop uvloop \
            --http httptools \
            --no-access-log
        ;;
        
    worker)
        log_info "Starting Celery worker..."
        wait_for_redis
        
        # Optionally preload models
        if [ "${PRELOAD_MODELS:-false}" = "true" ]; then
            preload_models
        fi
        
        # Get configuration from environment
        CONCURRENCY="${CELERY_CONCURRENCY:-2}"
        QUEUE="${CELERY_QUEUE:-docling}"
        LOGLEVEL="${CELERY_LOGLEVEL:-info}"
        
        log_info "Configuration: CONCURRENCY=$CONCURRENCY, QUEUE=$QUEUE, LOGLEVEL=$LOGLEVEL"
        
        exec celery -A worker.celery_app worker \
            --loglevel="$LOGLEVEL" \
            --concurrency="$CONCURRENCY" \
            --queues="$QUEUE" \
            --hostname="worker@%h" \
            -E
        ;;
        
    beat)
        log_info "Starting Celery beat scheduler..."
        wait_for_redis
        
        exec celery -A worker.celery_app beat \
            --loglevel="${CELERY_LOGLEVEL:-info}"
        ;;
        
    flower)
        log_info "Starting Flower monitoring..."
        wait_for_redis
        
        exec celery -A worker.celery_app flower \
            --port="${FLOWER_PORT:-5555}" \
            --basic_auth="${FLOWER_USER:-admin}:${FLOWER_PASSWORD:-admin}"
        ;;
        
    shell)
        log_info "Starting interactive shell..."
        exec /bin/bash
        ;;
        
    test)
        log_info "Running tests..."
        exec pytest -v --tb=short
        ;;
        
    *)
        log_info "Running custom command: $@"
        exec "$@"
        ;;
esac
