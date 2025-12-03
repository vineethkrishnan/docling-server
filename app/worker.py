"""Celery worker configuration."""

import os

from celery import Celery

from utils import get_redis_url

# Redis URL for broker and backend
REDIS_URL = get_redis_url()

# Create Celery app
celery_app = Celery(
    "docling_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Enable task events for Flower monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    task_time_limit=900,  # 15 minute hard limit
    task_soft_time_limit=540,  # 9 minute soft limit (warning)
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Only fetch one task at a time (for heavy tasks)
    worker_concurrency=int(os.getenv("CELERY_CONCURRENCY", 2)),
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (memory management)
    
    # Result backend settings
    result_expires=604800,  # Results expire after 7 days
    result_extended=True,  # Store additional task metadata
    
    # Task routing
    task_routes={
        "tasks.process_document_task": {"queue": "docling"},
        "tasks.process_batch_task": {"queue": "docling"},
    },
    
    # Default queue
    task_default_queue="docling",
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute between retries
    
    # Beat schedule (if needed for periodic tasks)
    beat_schedule={
        "cleanup-old-results": {
            "task": "tasks.cleanup_old_results",
            "schedule": 86400.0,  # Daily
        },
    },
)

# Optional: Configure task priority
celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5


if __name__ == "__main__":
    celery_app.start()
