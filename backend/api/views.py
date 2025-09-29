from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    RagQuerySerializer, DocumentIngestSerializer, 
    UserRegistrationSerializer, UserLoginSerializer, 
    UserProfileSerializer, DocumentSerializer
)
from .rag_ingestion import ingest_document, ingest_document_from_s3
from .rag_query import query_rag
from .models import User, Document
from .s3_storage import s3_storage
import os
import tempfile
from django.conf import settings

class RegisterView(APIView):
    """
    API view to handle user registration.
    """
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserProfileSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    """
    API view to handle user login.
    """
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserProfileSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileView(APIView):
    """
    API view to handle user profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class IngestView(APIView):
    """
    API view to handle document ingestion.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentIngestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            file_obj = serializer.validated_data['file']
            user_id = str(request.user.id)  # Get user_id from authenticated user

            # Create document record
            document = Document.objects.create(
                user=request.user,
                filename=file_obj.name,
                file_size=file_obj.size,
                status='processing'
            )

            # Save file to temporary location first
            temp_file_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_obj.name)[1]) as temp_file:
                    for chunk in file_obj.chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name

                # Upload to S3
                s3_key = s3_storage.upload_document(temp_file_path, user_id, file_obj.name)
                if not s3_key:
                    # If S3 upload fails, fall back to local processing
                    print("S3 upload failed, falling back to local processing")
                    ingest_document(temp_file_path, user_id)
                else:
                    # Update document with S3 key and process from S3
                    document.s3_key = s3_key
                    document.save()
                    
                    # Process document from S3
                    success = ingest_document_from_s3(s3_key, user_id)
                    if not success:
                        document.status = 'failed'
                        document.save()
                        return Response({
                            "error": "Document ingestion failed.",
                            "details": "Failed to process document from S3"
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                document.status = 'completed'
                document.save()
                
                return Response({
                    "message": "Document ingestion completed successfully.",
                    "document": DocumentSerializer(document).data
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                document.status = 'failed'
                document.save()
                return Response({
                    "error": "Document ingestion failed.",
                    "details": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            finally:
                # Clean up temporary file
                if temp_file_path and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class QueryView(APIView):
    """
    API view to handle RAG queries.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RagQuerySerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user_id = str(request.user.id)  # Get user_id from authenticated user
            query = serializer.validated_data['query']

            response = query_rag(user_id, query)

            return Response({"response": response})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DocumentListView(APIView):
    """
    API view to list user's documents.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        documents = Document.objects.filter(user=request.user).order_by('-upload_date')
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data)