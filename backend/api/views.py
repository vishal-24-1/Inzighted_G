from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
import sentry_sdk
from .serializers import (
    RagQuerySerializer, DocumentIngestSerializer, 
    UserRegistrationSerializer, UserLoginSerializer, 
    UserProfileSerializer, DocumentSerializer,
    ChatSessionSerializer, ChatSessionListSerializer, ChatMessageSerializer,
    GoogleAuthSerializer
)
from .rag_ingestion import ingest_document, ingest_document_from_s3
from .rag_query import query_rag, generate_tutoring_question
from .models import User, Document, ChatSession, ChatMessage, SessionInsight, TutoringQuestionBatch
from .s3_storage import s3_storage
from .gemini_client import gemini_client
import os
import tempfile
from django.conf import settings
import time
from google.oauth2 import id_token
from google.auth.transport import requests

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

class GoogleAuthView(APIView):
    """
    API view to handle Google OAuth authentication.
    Receives Google credential (ID token), verifies it, and returns JWT tokens.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Get the credential from request
            credential = request.data.get('credential')
            
            # Debug logging
            print(f"Received Google auth request")
            print(f"Request data keys: {request.data.keys()}")
            print(f"Credential present: {bool(credential)}")
            
            if not credential:
                print("ERROR: No credential provided")
                return Response(
                    {'error': 'No credential provided'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify the Google token
            try:
                print(f"Verifying token with client ID: {settings.GOOGLE_OAUTH_CLIENT_ID[:20]}...")
                idinfo = id_token.verify_oauth2_token(
                    credential, 
                    requests.Request(), 
                    settings.GOOGLE_OAUTH_CLIENT_ID
                )
                
                print(f"Token verified successfully")
                print(f"Token info: {idinfo.keys()}")
                
                # Check if token is for our app
                if idinfo['aud'] != settings.GOOGLE_OAUTH_CLIENT_ID:
                    print(f"ERROR: Invalid audience. Expected: {settings.GOOGLE_OAUTH_CLIENT_ID}, Got: {idinfo['aud']}")
                    return Response(
                        {'error': 'Invalid token audience'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Extract user information
                email = idinfo.get('email')
                name = idinfo.get('name', '')
                google_id = idinfo.get('sub')
                
                print(f"User email: {email}, name: {name}")
                
                if not email:
                    print("ERROR: No email in token")
                    return Response(
                        {'error': 'Email not provided by Google'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if user exists, create if not
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': email.split('@')[0],
                        'name': name,
                        'google_id': google_id,
                        'is_active': True,
                    }
                )
                
                print(f"User {'created' if created else 'found'}: {user.email}")
                
                # Update Google ID if user exists but doesn't have it
                if not created and not user.google_id:
                    user.google_id = google_id
                    user.save()
                    print(f"Updated Google ID for existing user")
                
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                
                print(f"JWT tokens generated successfully")
                
                return Response({
                    'user': UserProfileSerializer(user).data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'message': 'Login successful' if not created else 'Account created successfully'
                })
                
            except ValueError as e:
                # Invalid token
                print(f"ERROR: Token verification failed: {str(e)}")
                sentry_sdk.capture_exception(e, extras={
                    "component": "auth",
                    "view": "GoogleAuthView",
                    "error_type": "token_verification_failed"
                })
                return Response(
                    {'error': f'Invalid token: {str(e)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            print(f"ERROR: Unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
            sentry_sdk.capture_exception(e, extras={
                "component": "auth",
                "view": "GoogleAuthView"
            })
            return Response(
                {'error': f'Authentication failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
                sentry_sdk.capture_exception(e, extras={
                    "component": "document_ingestion",
                    "view": "IngestView",
                    "user_id": str(request.user.id),
                    "filename": file_obj.name
                })
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

class ChatBotView(APIView):
    """
    API view to handle chatbot conversations using RAG system with user's documents.
    Manages chat sessions and stores conversation history.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        message = request.data.get('message', '').strip()
        session_id = request.data.get('session_id')  # Optional: existing session ID
        
        if not message:
            return Response(
                {"error": "Message is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = request.user
            user_id = str(user.id)
            
            # Check if Gemini client is available
            if not gemini_client.is_available():
                return Response(
                    {"error": "AI service is currently unavailable"}, 
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            # Get or create chat session
            chat_session = self._get_or_create_session(user, session_id)
            
            # Store user message
            user_message = ChatMessage.objects.create(
                session=chat_session,
                user=user,
                content=message,
                is_user_message=True
            )

            # Use RAG system to get context-aware response from user's documents
            import time
            start_time = time.time()
            
            response = query_rag(user_id, message)
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Store AI response
            ai_message = ChatMessage.objects.create(
                session=chat_session,
                user=user,
                content=response,
                is_user_message=False,
                response_time_ms=response_time_ms,
                token_count=len(response.split())  # Rough estimate
            )

            # Update session timestamp
            chat_session.save()  # This updates the updated_at field

            return Response({
                "response": response,
                "user_message": message,
                "session_id": str(chat_session.id),
                "message_id": str(ai_message.id),
                "response_time_ms": response_time_ms
            })

        except Exception as e:
            sentry_sdk.capture_exception(e, extras={
                "component": "chat",
                "view": "ChatBotView",
                "user_id": str(request.user.id) if request.user else None,
                "session_id": session_id
            })
            return Response(
                {"error": f"Failed to generate response: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_or_create_session(self, user, session_id=None):
        """Get existing session or create new one"""
        if session_id:
            try:
                # Try to get existing session
                session = ChatSession.objects.get(id=session_id, user=user, is_active=True)
                return session
            except ChatSession.DoesNotExist:
                pass
        
        # Create new session
        return ChatSession.objects.create(user=user)


class ChatSessionListView(APIView):
    """
    API view to list user's chat sessions
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = ChatSession.objects.filter(user=request.user, is_active=True)
        serializer = ChatSessionListSerializer(sessions, many=True)
        return Response(serializer.data)


class ChatSessionDetailView(APIView):
    """
    API view to get detailed chat session with all messages
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user, is_active=True)
            serializer = ChatSessionSerializer(session)
            return Response(serializer.data)
        except ChatSession.DoesNotExist:
            return Response(
                {"error": "Chat session not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, session_id):
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user, is_active=True)
            session.is_active = False
            session.save()
            return Response({"message": "Chat session deleted successfully"})
        except ChatSession.DoesNotExist:
            return Response(
                {"error": "Chat session not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class TutoringSessionStartView(APIView):
    """
    API view to start a tutoring session.
    Creates a new ChatSession and generates the first tutoring question.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        document_id = request.data.get('document_id')
        
        try:
            user = request.user
            user_id = str(user.id)
            
            # Verify document exists and belongs to user
            if document_id:
                try:
                    document = Document.objects.get(id=document_id, user=user, status='completed')
                except Document.DoesNotExist:
                    return Response(
                        {"error": "Document not found or not processed yet"}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Check if Gemini client is available
            if not gemini_client.is_available():
                return Response(
                    {"error": "AI tutoring service is currently unavailable"}, 
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            # Create session title
            session_title = f"Tutoring Session - {document.filename}" if document_id and 'document' in locals() else "General Tutoring Session"
            
            # Create new tutoring session
            session = ChatSession.objects.create(
                user=user,
                title=session_title,
                document=document if document_id and 'document' in locals() else None
            )
            
            # Generate first tutoring question
            start_time = time.time()
            first_question = generate_tutoring_question(user_id, document_id, session_id=str(session.id))
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Save the first question as a bot message
            question_message = ChatMessage.objects.create(
                session=session,
                user=user,
                content=first_question,
                is_user_message=False,
                response_time_ms=response_time_ms,
                token_count=len(first_question.split())
            )

            return Response({
                "session_id": str(session.id),
                "first_question": {
                    "id": str(question_message.id),
                    "text": first_question,
                    "created_at": question_message.created_at.isoformat()
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            sentry_sdk.capture_exception(e, extras={
                "component": "tutoring",
                "view": "TutoringSessionStartView",
                "user_id": str(request.user.id) if request.user else None,
                "document_id": document_id
            })
            return Response(
                {"error": f"Failed to start tutoring session: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TutoringSessionAnswerView(APIView):
    """
    API view to handle student answers in a tutoring session.
    Saves the answer and generates the next question.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        answer_text = request.data.get('text', '').strip()
        
        if not answer_text:
            return Response(
                {"error": "Answer text is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = request.user
            user_id = str(user.id)
            
            # Get the tutoring session
            try:
                session = ChatSession.objects.get(id=session_id, user=user, is_active=True)
            except ChatSession.DoesNotExist:
                return Response(
                    {"error": "Tutoring session not found or inactive"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Save student's answer
            answer_message = ChatMessage.objects.create(
                session=session,
                user=user,
                content=answer_text,
                is_user_message=True
            )
            
            # Check if we should continue or end the session
            message_count = session.messages.count()
            user_answers_count = session.messages.filter(is_user_message=True).count()
            
            # Check if we have a question batch for this session
            question_batch = TutoringQuestionBatch.objects.filter(session=session).first()
            
            if question_batch and question_batch.status in ['ready', 'in_progress']:
                # We have an active question batch - continue until all questions are used
                print(f"Question batch status: {question_batch.status}, progress: {question_batch.current_question_index + 1}/{question_batch.total_questions}")
                
                # Only end if we've exhausted all questions in the batch
                if not question_batch.has_more_questions() and question_batch.status != 'completed':
                    # Mark batch as completed
                    question_batch.status = 'completed'
                    question_batch.save()
                    return Response({
                        "finished": True,
                        "message": f"Congratulations! You've completed all {question_batch.total_questions} questions in this tutoring session. Excellent work!"
                    })
                elif question_batch.status == 'completed':
                    return Response({
                        "finished": True,
                        "message": f"You've already completed all {question_batch.total_questions} questions for this session. Well done!"
                    })
            else:
                # No question batch - use legacy termination logic for backward compatibility
                # For MVP, continue asking questions until we have at least 2 user answers (minimum requirement)
                # and a maximum of 6 total messages (3 Q&A pairs)
                if user_answers_count >= 2 and message_count >= 6:
                    return Response({
                        "finished": True,
                        "message": "Great job! You've completed this tutoring session."
                    })
                elif user_answers_count >= 5:  # Maximum 5 answers to prevent overly long sessions
                    return Response({
                        "finished": True,
                        "message": "Excellent work! You've completed an extended tutoring session."
                    })
            
            # Generate next question using the session context
            start_time = time.time()
            session_document_id = str(session.document.id) if session.document else None
            if session_document_id:
                print(f"Generating next question scoped to document: {session.document.filename}")
            else:
                print("Generating next question with general scope (no document selected)")
            
            # Generate next question using the session's document context
            next_question = generate_tutoring_question(user_id, session_document_id, session_id=session_id)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Save the next question
            question_message = ChatMessage.objects.create(
                session=session,
                user=user,
                content=next_question,
                is_user_message=False,
                response_time_ms=response_time_ms,
                token_count=len(next_question.split())
            )

            # Update session timestamp
            session.save()

            return Response({
                "next_question": {
                    "id": str(question_message.id),
                    "text": next_question,
                    "created_at": question_message.created_at.isoformat()
                }
            })

        except Exception as e:
            sentry_sdk.capture_exception(e, extras={
                "component": "tutoring",
                "view": "TutoringSessionAnswerView",
                "user_id": str(request.user.id) if request.user else None,
                "session_id": session_id
            })
            return Response(
                {"error": f"Failed to process answer: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TutoringSessionEndView(APIView):
    """
    API view to end a tutoring session.
    Marks the session as inactive, saves final state, and auto-generates insights.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            user = request.user
            
            # Get the tutoring session
            try:
                session = ChatSession.objects.get(id=session_id, user=user, is_active=True)
            except ChatSession.DoesNotExist:
                return Response(
                    {"error": "Tutoring session not found or already ended"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Mark session as inactive
            session.is_active = False
            session.save()

            # Auto-generate insights for this session
            try:
                from .insight_generator import generate_insights_for_session
                insight = generate_insights_for_session(str(session.id))
                
                insights_generated = insight is not None
                insight_status = insight.status if insight else 'failed'
                
            except Exception as e:
                print(f"Error generating insights: {str(e)}")
                insights_generated = False
                insight_status = 'failed'

            return Response({
                "message": "Tutoring session ended successfully",
                "session_id": str(session.id),
                "total_messages": session.messages.count(),
                "insights_generated": insights_generated,
                "insight_status": insight_status
            })

        except Exception as e:
            return Response(
                {"error": f"Failed to end session: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TutoringSessionDetailView(APIView):
    """
    API view to get tutoring session details with all messages.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            serializer = ChatSessionSerializer(session)
            return Response(serializer.data)
        except ChatSession.DoesNotExist:
            return Response(
                {"error": "Tutoring session not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class SessionInsightsView(APIView):
    """
    API view to get stored SWOT analysis insights for a tutoring session.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            user = request.user
            
            # Get the session
            try:
                session = ChatSession.objects.get(id=session_id, user=user)
            except ChatSession.DoesNotExist:
                return Response(
                    {"error": "Session not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if insights exist for this session
            try:
                insight = session.insight
            except SessionInsight.DoesNotExist:
                # Try to generate insights if they don't exist
                try:
                    from .insight_generator import generate_insights_for_session
                    insight = generate_insights_for_session(str(session.id))
                    
                    if not insight:
                        return Response({
                            "message": "Not enough data to generate insights yet",
                            "reason": "At least 2 question-answer pairs are needed for analysis",
                            "session_id": str(session.id)
                        }, status=status.HTTP_202_ACCEPTED)
                        
                except Exception as e:
                    return Response({
                        "error": "Failed to generate insights",
                        "details": str(e)
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Check if insights are still processing
            if insight.status == 'processing':
                return Response({
                    "message": "Insights are being generated",
                    "status": "processing",
                    "session_id": str(session.id)
                }, status=status.HTTP_202_ACCEPTED)
            
            # Check if insights generation failed
            if insight.status == 'failed':
                return Response({
                    "error": "Insights generation failed",
                    "session_id": str(session.id),
                    "status": "failed"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Return successful insights
            document_name = insight.document.filename if insight.document else session.get_title()
            
            return Response({
                "session_id": str(session.id),
                "document_name": document_name,
                "session_title": session.get_title(),
                "total_qa_pairs": insight.total_qa_pairs,
                "session_duration": insight.get_session_duration(),
                "status": insight.status,
                "insights": {
                    "strength": insight.strength,
                    "weakness": insight.weakness,
                    "opportunity": insight.opportunity,
                    "threat": insight.threat
                },
                "created_at": insight.created_at.isoformat(),
                "updated_at": insight.updated_at.isoformat()
            })

        except Exception as e:
            sentry_sdk.capture_exception(e, extras={
                "component": "insights",
                "view": "SessionInsightsView",
                "user_id": str(request.user.id) if request.user else None,
                "session_id": session_id
            })
            return Response(
                {"error": f"Failed to retrieve insights: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserSessionsListView(APIView):
    """
    API view to list all sessions for a user (for session selection in insights).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get all sessions for the user, ordered by most recent
            sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')
            
            session_data = []
            for session in sessions:
                # Get document name if available
                document_name = "Unknown Document"
                try:
                    # Try to find associated document
                    if hasattr(session, 'document') and session.document:
                        document_name = session.document.filename
                    else:
                        # Fallback to session title
                        document_name = session.get_title()
                except:
                    document_name = session.get_title()
                
                session_data.append({
                    "id": str(session.id),
                    "title": session.get_title(),
                    "document_name": document_name,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "is_active": session.is_active,
                    "message_count": session.messages.count()
                })
            
            return Response(session_data)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch sessions: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )