"""
Celery Tasks for InzightedG

This module contains asynchronous tasks for document processing pipeline:
- Document ingestion (extraction, chunking, embedding, Pinecone upload)
- Background processing for uploaded documents

All tasks are designed to be idempotent and include comprehensive error handling.
"""

import logging
import time
from celery import shared_task
from django.conf import settings
import sentry_sdk

from .models import Document
from .rag_ingestion import ingest_document_from_s3

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name='api.tasks.process_document',
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3},
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_document(self, s3_key: str, user_id: str, document_id: str):
    """
    Asynchronously process an uploaded document through the RAG ingestion pipeline.
    
    This task performs the complete document processing workflow:
    1. Updates document status to 'processing'
    2. Extracts text from document (PDF/DOCX) with OCR fallback
    3. Chunks text into semantic pieces with token-awareness
    4. Generates embeddings using Gemini Embedding-001
    5. Uploads vectors to Pinecone with tenant isolation
    6. Updates document status to 'completed' or 'failed'
    
    Args:
        s3_key (str): S3 object key for the uploaded document
        user_id (str): UUID of the user who uploaded the document
        document_id (str): UUID of the Document model instance
        
    Returns:
        dict: Status information about the processing result
        
    Raises:
        Exception: Any exception during processing (triggers retry with backoff)
        
    Retry Strategy:
        - Max retries: 3
        - Exponential backoff: 2^n seconds with jitter
        - Total max backoff: 600 seconds (10 minutes)
        
    Idempotency:
        - Checks document status before processing
        - Skips if already 'completed'
        - Safe to retry multiple times
    """
    
    task_id = self.request.id
    retry_count = self.request.retries
    
    logger.info(
        f"[Task {task_id}] Starting document processing "
        f"(attempt {retry_count + 1}/4): "
        f"document_id={document_id}, s3_key={s3_key}, user_id={user_id}"
    )
    
    # Sentry breadcrumb for tracking
    sentry_sdk.add_breadcrumb(
        category='task',
        message='Document processing started',
        level='info',
        data={
            'task_id': task_id,
            'document_id': document_id,
            's3_key': s3_key,
            'user_id': user_id,
            'retry_count': retry_count,
        }
    )
    
    start_time = time.time()
    
    try:
        # Get the document instance
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            error_msg = f"Document {document_id} not found in database"
            logger.error(f"[Task {task_id}] {error_msg}")
            sentry_sdk.capture_message(error_msg, level='error')
            return {
                'success': False,
                'error': error_msg,
                'document_id': document_id,
            }
        
        # Idempotency check: Skip if already completed
        if document.status == 'completed':
            logger.info(
                f"[Task {task_id}] Document {document_id} already completed, skipping processing"
            )
            return {
                'success': True,
                'message': 'Document already processed',
                'document_id': document_id,
                'status': 'completed',
            }
        
        # Update status to processing
        document.status = 'processing'
        document.save(update_fields=['status'])
        logger.info(f"[Task {task_id}] Document status updated to 'processing'")
        
        # Execute the ingestion pipeline
        logger.info(f"[Task {task_id}] Starting ingestion pipeline...")
        
        # Call the existing ingestion function
        # This performs: download from S3 → extract → chunk → embed → upload to Pinecone
        success = ingest_document_from_s3(s3_key, user_id)
        
        if not success:
            raise Exception("Document ingestion returned False (processing failed)")
        
        # Update status to completed
        document.status = 'completed'
        document.save(update_fields=['status'])
        
        elapsed_time = time.time() - start_time
        logger.info(
            f"[Task {task_id}] Document processing completed successfully "
            f"in {elapsed_time:.2f} seconds: document_id={document_id}"
        )
        
        # Sentry success breadcrumb
        sentry_sdk.add_breadcrumb(
            category='task',
            message='Document processing completed',
            level='info',
            data={
                'task_id': task_id,
                'document_id': document_id,
                'elapsed_time': elapsed_time,
            }
        )
        
        return {
            'success': True,
            'message': 'Document processed successfully',
            'document_id': document_id,
            'status': 'completed',
            'elapsed_time': elapsed_time,
            'retry_count': retry_count,
        }
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        error_msg = str(e)
        
        logger.error(
            f"[Task {task_id}] Document processing failed "
            f"(attempt {retry_count + 1}/4) after {elapsed_time:.2f}s: {error_msg}",
            exc_info=True
        )
        
        # Capture exception in Sentry with context
        sentry_sdk.capture_exception(e, extras={
            'component': 'celery_task',
            'task_name': 'process_document',
            'task_id': task_id,
            'document_id': document_id,
            's3_key': s3_key,
            'user_id': user_id,
            'retry_count': retry_count,
            'elapsed_time': elapsed_time,
        })
        
        # Update document status to failed if this is the last retry
        if retry_count >= 2:  # 0, 1, 2 = 3 total attempts
            try:
                document = Document.objects.get(id=document_id)
                document.status = 'failed'
                document.save(update_fields=['status'])
                logger.error(
                    f"[Task {task_id}] Document {document_id} marked as 'failed' "
                    f"after {retry_count + 1} attempts"
                )
            except Exception as update_error:
                logger.error(
                    f"[Task {task_id}] Failed to update document status: {update_error}"
                )
        
        # Re-raise to trigger Celery retry mechanism
        raise


@shared_task(
    bind=True,
    name='api.tasks.batch_process_documents',
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2},
)
def batch_process_documents(self, document_data_list: list):
    """
    Process multiple documents in batch (future optimization).
    
    Args:
        document_data_list (list): List of dicts with keys: s3_key, user_id, document_id
        
    Returns:
        dict: Summary of batch processing results
    """
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Starting batch processing of {len(document_data_list)} documents")
    
    results = {
        'total': len(document_data_list),
        'successful': 0,
        'failed': 0,
        'details': []
    }
    
    for doc_data in document_data_list:
        try:
            # Enqueue individual process_document task
            result = process_document.delay(
                s3_key=doc_data['s3_key'],
                user_id=doc_data['user_id'],
                document_id=doc_data['document_id']
            )
            
            results['successful'] += 1
            results['details'].append({
                'document_id': doc_data['document_id'],
                'task_id': result.id,
                'status': 'enqueued'
            })
            
        except Exception as e:
            results['failed'] += 1
            results['details'].append({
                'document_id': doc_data.get('document_id', 'unknown'),
                'status': 'failed',
                'error': str(e)
            })
            logger.error(f"[Task {task_id}] Failed to enqueue document: {e}")
    
    logger.info(
        f"[Task {task_id}] Batch processing complete: "
        f"{results['successful']} successful, {results['failed']} failed"
    )
    
    return results


@shared_task(name='api.tasks.cleanup_expired_sessions')
def cleanup_expired_sessions():
    """
    Periodic task to clean up expired chat sessions (future use).
    Can be scheduled with Celery Beat.
    """
    logger.info("Running cleanup_expired_sessions task")
    # Implementation for cleaning up old sessions
    return {'status': 'completed', 'message': 'Cleanup task placeholder'}


@shared_task(name='api.tasks.test_celery')
def test_celery():
    """
    Simple test task to verify Celery is working.
    Usage: test_celery.delay()
    """
    logger.info("Test Celery task executed successfully!")
    return {
        'status': 'success',
        'message': 'Celery is configured and working properly!',
        'timestamp': time.time()
    }
