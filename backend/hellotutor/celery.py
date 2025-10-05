"""
Celery Configuration for InzightedG

This module configures Celery for asynchronous task processing,
particularly for document ingestion pipeline (extraction, chunking, embedding, Pinecone upload).

Key Features:
- Redis as broker and result backend
- JSON serialization for cross-platform compatibility
- Exponential backoff retry mechanism
- Task result tracking
- Worker concurrency configuration
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellotutor.settings')

# Create Celery app instance
app = Celery('hellotutor')

# Load configuration from Django settings with 'CELERY_' prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed Django apps
app.autodiscover_tasks()

# Celery Configuration
app.conf.update(
    # Broker and Result Backend
    broker_connection_retry_on_startup=True,
    
    # Task Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
    
    # Task Execution
    task_acks_late=True,  # Acknowledge task after completion (safer for retries)
    task_reject_on_worker_lost=True,  # Re-queue tasks if worker crashes
    task_track_started=True,  # Track when task starts executing
    
    # Result Backend
    result_extended=True,  # Store additional task metadata
    result_expires=3600,  # Results expire after 1 hour
    
    # Worker Configuration
    worker_prefetch_multiplier=4,  # How many tasks to prefetch per worker
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (memory cleanup)
    
    # Task Time Limits
    task_soft_time_limit=1800,  # 30 minutes soft limit (raises exception)
    task_time_limit=2400,  # 40 minutes hard limit (kills process)
    
    # Retry Configuration
    task_autoretry_for=(Exception,),  # Retry on any exception
    task_retry_kwargs={
        'max_retries': 3,
        'countdown': 5,  # Initial delay before first retry (seconds)
    },
    task_retry_backoff=True,  # Enable exponential backoff
    task_retry_backoff_max=600,  # Max backoff time (10 minutes)
    task_retry_jitter=True,  # Add randomness to backoff to prevent thundering herd
    
    # Logging
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Debug task to test Celery setup
    Usage: debug_task.delay()
    """
    print(f'Request: {self.request!r}')
    return 'Celery is working!'


# Optional: Celery Beat schedule for periodic tasks (future use)
app.conf.beat_schedule = {
    # Example: Clean up expired sessions every day at midnight
    # 'cleanup-expired-sessions': {
    #     'task': 'api.tasks.cleanup_expired_sessions',
    #     'schedule': crontab(hour=0, minute=0),
    # },
}
