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
		documents = Document.objects.filter(user=request.user).order_by('-upload_date')
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
			}
			response_data['message'] = status_messages.get(document.status, 'Unknown status')
			if document.status == 'completed' and document.upload_date:
				response_data['note'] = 'Document is ready for tutoring sessions'
			return Response(response_data)
		except Document.DoesNotExist:
			return Response({'error': 'Document not found or you do not have access to it'}, status=status.HTTP_404_NOT_FOUND)


__all__ = ['IngestView', 'DocumentListView', 'DocumentStatusView']
