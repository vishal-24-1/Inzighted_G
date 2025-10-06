"""
API Views for Tanglish Agent Flow
New endpoints that implement the spec without affecting existing views
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import sentry_sdk
from ..models import ChatSession, ChatMessage, QuestionItem, EvaluatorResult, Document
from ..agent_flow import TutorAgent
from ..gemini_client import gemini_client
import time
import logging

logger = logging.getLogger(__name__)


class AgentSessionStartView(APIView):
    """
    Start a new Tanglish agent tutoring session.
    POST /api/agent/session/start
    
    Body: {
        "document_id": "uuid" (optional),
        "language": "tanglish" or "english" (optional, default: tanglish)
    }
    
    Returns: {
        "session_id": "uuid",
        "first_question": {
            "text": "question in Tanglish",
            "question_id": "q_abc123",
            "archetype": "Concept Unfold",
            "difficulty": "easy"
        }
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        document_id = request.data.get('document_id')
        language = request.data.get('language', 'tanglish')
        
        try:
            user = request.user
            
            # Verify document if provided
            document = None
            if document_id:
                try:
                    document = Document.objects.get(id=document_id, user=user, status='completed')
                except Document.DoesNotExist:
                    return Response(
                        {"error": "Document not found or not processed yet"},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Check Gemini availability
            if not gemini_client.is_available():
                return Response(
                    {"error": "AI tutoring service is currently unavailable"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Create session
            session_title = f"Tanglish Session - {document.filename}" if document else "General Tanglish Session"
            session = ChatSession.objects.create(
                user=user,
                title=session_title,
                document=document,
                language=language
            )
            
            # Initialize agent
            agent = TutorAgent(session)
            
            # Get first question
            first_question_text, first_question_item = agent.get_next_question()
            
            if not first_question_text:
                return Response(
                    {"error": "Failed to generate first question"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Save first question as a bot message
            question_message = ChatMessage.objects.create(
                session=session,
                user=user,
                content=first_question_text,
                is_user_message=False
            )
            
            return Response({
                "session_id": str(session.id),
                "first_question": {
                    "text": first_question_text,
                    "question_id": first_question_item.question_id if first_question_item else None,
                    "archetype": first_question_item.archetype if first_question_item else None,
                    "difficulty": first_question_item.difficulty if first_question_item else None,
                    "message_id": str(question_message.id)
                },
                "language": language
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error starting agent session: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "agent_views",
                "view": "AgentSessionStartView",
                "user_id": str(request.user.id)
            })
            return Response(
                {"error": f"Failed to start session: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AgentRespondView(APIView):
    """
    Submit user response to current question.
    POST /api/agent/session/<session_id>/respond
    
    Body: {
        "message": "user's answer or question"
    }
    
    Returns: {
        "reply": "agent's reply (if any)",
        "next_question": {
            "text": "...",
            "question_id": "...",
            ...
        },
        "session_complete": false,
        "evaluation": {
            "score": 0.85,
            "xp": 75,
            "correct": true,
            "explanation": "..."
        }
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, session_id):
        user_message = request.data.get('message', '').strip()
        
        if not user_message:
            return Response(
                {"error": "Message is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = request.user
            
            # Get session
            try:
                session = ChatSession.objects.get(id=session_id, user=user, is_active=True)
            except ChatSession.DoesNotExist:
                return Response(
                    {"error": "Session not found or inactive"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Initialize agent
            agent = TutorAgent(session)
            
            # Get current question item
            batch = agent.get_or_create_question_batch()
            current_question_item = QuestionItem.objects.filter(
                batch=batch,
                order=batch.current_question_index
            ).first()
            
            if not current_question_item:
                return Response(
                    {"error": "No current question found"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Handle user message through agent flow
            start_time = time.time()
            result = agent.handle_user_message(user_message, current_question_item)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Build response
            response_data = {
                "session_id": str(session.id),
                "session_complete": result.get('session_complete', False),
                "response_time_ms": response_time_ms
            }
            
            # Add reply if present
            if result.get('reply'):
                # Save reply message
                reply_msg = ChatMessage.objects.create(
                    session=session,
                    user=user,
                    content=result['reply'],
                    is_user_message=False,
                    response_time_ms=response_time_ms
                )
                response_data["reply"] = {
                    "text": result['reply'],
                    "message_id": str(reply_msg.id)
                }
            
            # Add next question if present
            if result.get('next_question'):
                # Save next question message
                next_q_msg = ChatMessage.objects.create(
                    session=session,
                    user=user,
                    content=result['next_question'],
                    is_user_message=False
                )
                
                next_q_item = result.get('next_question_item')
                response_data["next_question"] = {
                    "text": result['next_question'],
                    "question_id": next_q_item.question_id if next_q_item else None,
                    "archetype": next_q_item.archetype if next_q_item else None,
                    "difficulty": next_q_item.difficulty if next_q_item else None,
                    "message_id": str(next_q_msg.id)
                }
            
            # Add evaluation if present
            if result.get('evaluation'):
                eval_result = result['evaluation']
                response_data["evaluation"] = {
                    "score": eval_result.score,
                    "xp": eval_result.xp,
                    "correct": eval_result.correct,
                    "explanation": eval_result.explanation,
                    "confidence": eval_result.confidence,
                    "followup_action": eval_result.followup_action
                }
            
            # Mark session as inactive if complete
            if result.get('session_complete'):
                session.is_active = False
                session.save()
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Error in agent respond: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "agent_views",
                "view": "AgentRespondView",
                "session_id": session_id,
                "user_id": str(request.user.id)
            })
            return Response(
                {"error": f"Failed to process response: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AgentSessionStatusView(APIView):
    """
    Get current status of agent session.
    GET /api/agent/session/<session_id>/status
    
    Returns: {
        "session_id": "...",
        "language": "tanglish",
        "total_questions": 10,
        "current_question_index": 3,
        "questions_answered": 3,
        "total_xp": 245,
        "is_complete": false
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, session_id):
        try:
            user = request.user
            
            # Get session
            try:
                session = ChatSession.objects.get(id=session_id, user=user)
            except ChatSession.DoesNotExist:
                return Response(
                    {"error": "Session not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get batch
            from ..models import TutoringQuestionBatch
            batch = TutoringQuestionBatch.objects.filter(session=session).first()
            
            if not batch:
                return Response(
                    {"error": "No question batch found for session"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Calculate stats
            evaluations = EvaluatorResult.objects.filter(message__session=session)
            total_xp = sum(ev.xp for ev in evaluations)
            questions_answered = evaluations.count()
            
            return Response({
                "session_id": str(session.id),
                "language": session.language,
                "total_questions": batch.total_questions,
                "current_question_index": batch.current_question_index,
                "questions_answered": questions_answered,
                "total_xp": total_xp,
                "is_complete": batch.status == 'completed',
                "is_active": session.is_active
            })
            
        except Exception as e:
            logger.error(f"Error getting session status: {e}")
            return Response(
                {"error": f"Failed to get status: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AgentLanguageToggleView(APIView):
    """
    Toggle session language between Tanglish and English.
    POST /api/agent/session/<session_id>/language
    
    Body: {
        "language": "english" or "tanglish"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, session_id):
        language = request.data.get('language', '').lower()
        
        if language not in ['tanglish', 'english']:
            return Response(
                {"error": "Language must be 'tanglish' or 'english'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = request.user
            
            # Get session
            try:
                session = ChatSession.objects.get(id=session_id, user=user)
            except ChatSession.DoesNotExist:
                return Response(
                    {"error": "Session not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Update language
            session.language = language
            session.save()
            
            return Response({
                "session_id": str(session.id),
                "language": language,
                "message": f"Language switched to {language}"
            })
            
        except Exception as e:
            logger.error(f"Error toggling language: {e}")
            return Response(
                {"error": f"Failed to toggle language: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
