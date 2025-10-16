from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import sentry_sdk
import tempfile
import os
import time
from ..serializers import DocumentIngestSerializer, DocumentSerializer
from ..models import Document
from ..rag_ingestion import ingest_document, ingest_document_from_s3
from ..s3_storage import s3_storage
from ..tasks import process_document


class IngestView(APIView):
	permission_classes = [IsAuthenticated]
	serializer_class = DocumentIngestSerializer

	def post(self, request, *args, **kwargs):
		serializer = self.serializer_class(data=request.data)
		if serializer.is_valid():
			file_obj = serializer.validated_data['file']
			user_id = str(request.user.id)

			# Duplicate check: prevent same user from uploading the same file again
			# We consider filename + file_size a reasonable proxy for duplicate detection.
			# If a non-failed record exists, return 409 Conflict with the existing document data.
			existing = Document.objects.filter(
				user=request.user,
				filename=file_obj.name,
				file_size=file_obj.size
			).exclude(status='failed').order_by('-upload_date').first()
			if existing:
				# Return 409 Conflict so frontend can open the library/selector
				return Response({
					"error": "Document already uploaded",
					"message": "You have already uploaded this document. Open your library to select it.",
					"document": DocumentSerializer(existing).data
				}, status=status.HTTP_409_CONFLICT)

			document = Document.objects.create(
				user=request.user,
				filename=file_obj.name,
				file_size=file_obj.size,
				status='uploading'
			)

			temp_file_path = None
			try:
				with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_obj.name)[1]) as temp_file:
					for chunk in file_obj.chunks():
						temp_file.write(chunk)
					temp_file_path = temp_file.name

				s3_key = s3_storage.upload_document(temp_file_path, user_id, file_obj.name)

				if not s3_key:
					document.status = 'processing'
					document.save()
					try:
						ingest_document(temp_file_path, user_id)
						document.status = 'completed'
						document.save()
						return Response({"message": "Document uploaded and processed successfully (local fallback).", "document": DocumentSerializer(document).data, "async": False}, status=status.HTTP_201_CREATED)
					except Exception as proc_error:
						document.status = 'failed'
						document.save()
						sentry_sdk.capture_exception(proc_error, extras={"component": "document_ingestion", "view": "IngestView", "mode": "local_fallback", "user_id": user_id, "filename": file_obj.name})
						return Response({"error": "Document processing failed.", "details": str(proc_error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

				document.s3_key = s3_key
				document.status = 'processing'
				document.save()

				if not self._is_celery_available(timeout=1):
					sentry_sdk.capture_message("Celery unavailable - falling back to synchronous ingestion", level="warning", extras={"document_id": str(document.id), "user_id": user_id})
					try:
						success = ingest_document_from_s3(s3_key, user_id)
						if not success:
							document.status = 'failed'
							document.save()
							return Response({"error": "Document ingestion failed.", "details": "Failed to process document from S3"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
						document.status = 'completed'
						document.save()
						return Response({"message": "Document uploaded and processed successfully (synchronous fallback).", "document": DocumentSerializer(document).data, "async": False}, status=status.HTTP_201_CREATED)
					except Exception as sync_error:
						document.status = 'failed'
						document.save()
						sentry_sdk.capture_exception(sync_error, extras={"component": "document_ingestion", "view": "IngestView", "mode": "sync_fallback", "user_id": user_id, "filename": file_obj.name})
						return Response({"error": "Document processing failed.", "details": str(sync_error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

				try:
					task = process_document.delay(s3_key=s3_key, user_id=user_id, document_id=str(document.id))
					return Response({"message": "Document uploaded successfully. Processing started in background.", "document": DocumentSerializer(document).data, "task_id": task.id, "async": True, "status": "processing"}, status=status.HTTP_202_ACCEPTED)
				except Exception as celery_error:
					sentry_sdk.capture_message("Celery enqueue failed, using synchronous processing", level="warning", extras={"error": str(celery_error), "document_id": str(document.id), "user_id": user_id})
					try:
						success = ingest_document_from_s3(s3_key, user_id)
						if not success:
							document.status = 'failed'
							document.save()
							return Response({"error": "Document ingestion failed.", "details": "Failed to process document from S3"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
						document.status = 'completed'
						document.save()
						return Response({"message": "Document uploaded and processed successfully (synchronous fallback).", "document": DocumentSerializer(document).data, "async": False}, status=status.HTTP_201_CREATED)
					except Exception as sync_error:
						document.status = 'failed'
						document.save()
						sentry_sdk.capture_exception(sync_error, extras={"component": "document_ingestion", "view": "IngestView", "mode": "sync_fallback", "user_id": user_id, "filename": file_obj.name})
						return Response({"error": "Document processing failed.", "details": str(sync_error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
			except Exception as e:
				document.status = 'failed'
				document.save()
				sentry_sdk.capture_exception(e, extras={"component": "document_ingestion", "view": "IngestView", "user_id": str(request.user.id), "filename": file_obj.name})
				return Response({"error": "Document upload failed.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
			finally:
				if temp_file_path and os.path.exists(temp_file_path):
					os.remove(temp_file_path)

		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def _is_celery_available(self, timeout: int = 2) -> bool:
		try:
			from hellotutor.celery_app import app as celery_app
			insp = celery_app.control.inspect(timeout=timeout)
			if insp is None:
				return False
			ping_result = insp.ping()
			if not ping_result or not isinstance(ping_result, dict):
				return False
			return True
		except Exception:
			return False


class DocumentListView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		# Filter out deleted documents - only show active documents to user
		documents = Document.objects.filter(
			user=request.user,
			is_deleted=False
		).order_by('-upload_date')
		serializer = DocumentSerializer(documents, many=True)
		return Response(serializer.data)


class DocumentStatusView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, document_id):
		try:
			document = Document.objects.get(id=document_id, user=request.user)
			response_data = {
				'document_id': str(document.id),
				'filename': document.filename,
				'status': document.status,
				'upload_date': document.upload_date.isoformat(),
				'file_size': document.file_size,
			}
			status_messages = {
				'uploading': 'Document is being uploaded to storage...',
				'processing': 'Document is being processed (extraction, chunking, embedding)...',
				'completed': 'Document processing completed successfully. Ready for use.',
				'failed': 'Document processing failed. Please try uploading again.',
				'deleting': 'Document is being deleted...',
				'deleted': 'Document has been deleted.',
				'delete_failed': 'Document deletion failed. Please try again.',
			}
			response_data['message'] = status_messages.get(document.status, 'Unknown status')
			if document.status == 'completed' and document.upload_date:
				response_data['note'] = 'Document is ready for tutoring sessions'
			return Response(response_data)
		except Document.DoesNotExist:
			return Response({'error': 'Document not found or you do not have access to it'}, status=status.HTTP_404_NOT_FOUND)


class DocumentDeleteView(APIView):
	"""
	Delete a document and its vectors from Pinecone.
	
	This endpoint performs a safe soft-delete that:
	1. Marks the document as deleted in the database
	2. Enqueues a Celery task to remove vectors from Pinecone
	3. Preserves existing sessions and insights that reference the document
	
	The deletion is idempotent - deleting an already-deleted document succeeds.
	"""
	permission_classes = [IsAuthenticated]

	def delete(self, request, document_id):
		"""
		Delete a document by ID.
		
		Args:
			document_id (str): UUID of the document to delete
			
		Returns:
			202 Accepted: Deletion task enqueued successfully
			404 Not Found: Document doesn't exist or user doesn't have access
			400 Bad Request: Document is currently processing
			500 Internal Server Error: Deletion task failed to enqueue
		"""
		try:
			# Get document and verify ownership
			document = Document.objects.get(id=document_id, user=request.user)
			
			# Check if already deleted
			if document.is_deleted:
				return Response({
					'success': True,
					'message': 'Document already deleted',
					'document_id': str(document.id),
					'status': document.status,
				}, status=status.HTTP_200_OK)
			
			# Prevent deletion if document is currently being processed
			if document.status in ['uploading', 'processing']:
				return Response({
					'error': 'Cannot delete document while it is being processed',
					'message': 'Please wait for processing to complete before deleting',
					'document_id': str(document.id),
					'status': document.status,
				}, status=status.HTTP_400_BAD_REQUEST)
			
			# Mark document as being deleted (soft delete)
			document.is_deleted = True
			document.status = 'deleting'
			document.deleted_by = request.user
			document.save(update_fields=['is_deleted', 'status', 'deleted_by', 'deleted_at'])
			
			# Check if Celery is available before trying to enqueue
			if self._is_celery_available(timeout=1):
				# Try to enqueue Celery task for vector deletion
				try:
					from ..tasks import delete_document_vectors
					
					task = delete_document_vectors.delay(
						document_id=str(document.id),
						user_id=str(request.user.id),
						deleted_by_id=str(request.user.id)
					)
					
					sentry_sdk.add_breadcrumb(
						category='document_deletion',
						message='Document deletion task enqueued',
						level='info',
						data={
							'document_id': str(document.id),
							'user_id': str(request.user.id),
							'task_id': task.id,
						}
					)
					
					return Response({
						'success': True,
						'message': 'Document deletion started. Vectors will be removed from Pinecone.',
						'document_id': str(document.id),
						'filename': document.filename,
						'task_id': task.id,
						'status': 'deleting',
						'note': 'Existing sessions and insights based on this document are preserved.',
					}, status=status.HTTP_202_ACCEPTED)
					
				except Exception as celery_error:
					# Log the error but continue to synchronous fallback
					sentry_sdk.capture_message(
						"Celery task enqueue failed - falling back to synchronous deletion",
						level="warning",
						extras={
							'error': str(celery_error),
							'document_id': str(document.id),
							'user_id': str(request.user.id),
						}
					)
			else:
				# Celery not available
				sentry_sdk.add_breadcrumb(
					category='document_deletion',
					message='Celery unavailable - using synchronous deletion',
					level='info',
					data={
						'document_id': str(document.id),
						'user_id': str(request.user.id),
					}
				)
			
			# Synchronous deletion fallback
			try:
				# Import and execute deletion synchronously
				from ..auth import get_tenant_tag
				from ..rag_ingestion import initialize_pinecone
				
				tenant_tag = get_tenant_tag(str(request.user.id))
				source_doc_id = document.s3_key.split('/')[-1] if document.s3_key else str(document.id)
				
				index = initialize_pinecone()
				filter_expr = {'source_doc_id': {'$eq': source_doc_id}}
				index.delete(filter=filter_expr, namespace=tenant_tag)
				
				document.status = 'deleted'
				document.save(update_fields=['status'])
				
				sentry_sdk.add_breadcrumb(
					category='document_deletion',
					message='Synchronous deletion completed',
					level='info',
					data={
						'document_id': str(document.id),
						'user_id': str(request.user.id),
					}
				)
				
				return Response({
					'success': True,
					'message': 'Document deleted successfully.',
					'document_id': str(document.id),
					'filename': document.filename,
					'status': 'deleted',
					'note': 'Existing sessions and insights based on this document are preserved.',
				}, status=status.HTTP_200_OK)
				
			except Exception as sync_error:
				# Synchronous deletion also failed
				document.status = 'delete_failed'
				document.save(update_fields=['status'])
				
				sentry_sdk.capture_exception(sync_error, extras={
					'component': 'document_deletion',
					'view': 'DocumentDeleteView',
					'mode': 'sync_fallback',
					'document_id': str(document.id),
					'user_id': str(request.user.id),
				})
				
				return Response({
					'error': 'Document deletion failed',
					'message': 'Failed to delete vectors from Pinecone. Please try again.',
					'details': str(sync_error),
					'document_id': str(document.id),
				}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
				
		except Document.DoesNotExist:
			return Response({
				'error': 'Document not found',
				'message': 'Document does not exist or you do not have access to it',
			}, status=status.HTTP_404_NOT_FOUND)
		
		except Exception as e:
			sentry_sdk.capture_exception(e, extras={
				'component': 'document_deletion',
				'view': 'DocumentDeleteView',
				'document_id': document_id,
				'user_id': str(request.user.id),
			})
			
			return Response({
				'error': 'Deletion request failed',
				'message': 'An unexpected error occurred',
				'details': str(e),
			}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
	
	def _is_celery_available(self, timeout: int = 2) -> bool:
		"""Check if Celery workers are available and responding."""
		try:
			from hellotutor.celery_app import app as celery_app
			insp = celery_app.control.inspect(timeout=timeout)
			if insp is None:
				return False
			ping_result = insp.ping()
			if not ping_result or not isinstance(ping_result, dict):
				return False
			return True
		except Exception:
			return False


__all__ = ['IngestView', 'DocumentListView', 'DocumentStatusView', 'DocumentDeleteView']
