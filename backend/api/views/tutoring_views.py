from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import sentry_sdk
import logging
import time
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from ..models import ChatSession, SessionInsight, SessionFeedback
from ..serializers import ChatSessionSerializer, SessionFeedbackSerializer

# Module logger
logger = logging.getLogger(__name__)


def is_session_expired(session: ChatSession) -> bool:
    """
    Check if a tutoring session has exceeded the timeout duration.
    
    Args:
        session: ChatSession instance
        
    Returns:
        bool: True if session has been active longer than SESSION_TIMEOUT_MINS
    """
    timeout_mins = getattr(settings, 'SESSION_TIMEOUT_MINS', 15)
    timeout_duration = timedelta(minutes=timeout_mins)
    elapsed_time = timezone.now() - session.created_at
    return elapsed_time > timeout_duration


def end_session_helper(session: ChatSession) -> dict:
    """
    Shared helper to end a tutoring session, generate insights, and update progress.
    Used by both manual end endpoint and automatic timeout logic.
    
    Args:
        session: ChatSession instance to end
        
    Returns:
        dict with keys: already_ended, insights_generated, insight_status, total_messages
    """
    # Check if session is already inactive (idempotent)
    if not session.is_active:
        logger.info(f"Session {session.id} already ended, returning cached status")
        return {
            "already_ended": True,
            "insights_generated": False,
            "insight_status": "already_completed",
            "total_messages": session.messages.count()
        }
    
    # Mark session as inactive
    session.is_active = False
    session.save()
    
    # Generate insights
    try:
        from api.insight_generator import generate_insights_for_session
        insight = generate_insights_for_session(str(session.id))
        insights_generated = insight is not None
        insight_status = insight.status if insight else 'failed'
    except Exception as e:
        logger.error(f"Error generating insights for session {session.id}: {e}")
        insights_generated = False
        insight_status = 'failed'
    
    # Process session completion for XP/batch updates
    try:
        from ..progress import process_session_completion
        proc_result = process_session_completion(session)
        logger.info(f"process_session_completion result for session {session.id}: {proc_result}")
    except Exception as e:
        logger.error(f"Error running process_session_completion for session {session.id}: {e}")
        try:
            sentry_sdk.capture_exception(e)
        except Exception:
            pass
    
    return {
        "already_ended": False,
        "insights_generated": insights_generated,
        "insight_status": insight_status,
        "total_messages": session.messages.count()
    }


class TutoringSessionStartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        document_id = request.data.get('document_id')
        # Use user's preferred language, fallback to request data
        user_preferred = getattr(request.user, 'preferred_language', request.user.PREFERRED_LANGUAGE_CHOICES[0][0])
        language = getattr(request.user, 'preferred_language', None) or request.data.get('language', user_preferred)
        try:
            user = request.user
            user_id = str(user.id)
            document = None
            if document_id:
                try:
                    from ..models import Document
                    document = Document.objects.get(id=document_id, user=user, status='completed')
                except Exception:
                    return Response({"error": "Document not found or not processed yet"}, status=404)

            if not getattr(__import__('api.gemini_client', fromlist=['gemini_client']), 'gemini_client').is_available():
                return Response({"error": "AI tutoring service is currently unavailable"}, status=503)

            session_title = f"Tutoring Session - {document.filename}" if document else "General Tutoring Session"
            session = ChatSession.objects.create(user=user, title=session_title, document=document, language=language)

            from ..agent_flow import TutorAgent
            agent = TutorAgent(session)
            start_time = time.time()
            first_question_text, first_question_item = agent.get_next_question()
            response_time_ms = int((time.time() - start_time) * 1000)
            if not first_question_text:
                return Response({"error": "Failed to generate first question"}, status=500)

            from ..models import ChatMessage
            question_message = ChatMessage.objects.create(session=session, user=user, content=first_question_text, is_user_message=False, response_time_ms=response_time_ms, token_count=len(first_question_text.split()))

            return Response({"session_id": str(session.id), "first_question": {"id": str(question_message.id), "text": first_question_text, "created_at": question_message.created_at.isoformat()}}, status=201)
        except Exception as e:
            sentry_sdk.capture_exception(e, extras={"component": "tutoring", "view": "TutoringSessionStartView", "user_id": str(request.user.id) if request.user else None, "document_id": document_id})
            return Response({"error": f"Failed to start tutoring session: {str(e)}"}, status=500)


class TutoringSessionAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        answer_text = request.data.get('text', '').strip()
        if not answer_text:
            return Response({"error": "Answer text is required"}, status=400)
        try:
            user = request.user
            try:
                session = ChatSession.objects.get(id=session_id, user=user, is_active=True)
            except ChatSession.DoesNotExist:
                return Response({"error": "Tutoring session not found or inactive"}, status=404)
            
            # Check if session has expired
            if is_session_expired(session):
                logger.info(f"Session {session.id} has exceeded timeout, auto-ending")
                result = end_session_helper(session)
                return Response({
                    "error": "Session has timed out after 15 minutes",
                    "session_expired": True,
                    "message": "Your session has automatically ended. Great work!",
                    "insights_generated": result["insights_generated"],
                    "insight_status": result["insight_status"]
                }, status=410)  # 410 Gone - resource expired

            from ..agent_flow import TutorAgent
            from ..models import QuestionItem
            agent = TutorAgent(session)
            batch = agent.get_or_create_question_batch()
            current_question_item = QuestionItem.objects.filter(batch=batch, order=batch.current_question_index).first()
            if not current_question_item:
                return Response({"error": "No current question found"}, status=500)

            start_time = time.time()
            result = agent.handle_user_message(answer_text, current_question_item)
            response_time_ms = int((time.time() - start_time) * 1000)

            response_data = {"session_id": str(session.id), "response_time_ms": response_time_ms}
            if result.get('session_complete'):
                response_data["finished"] = True
                response_data["message"] = "Congratulations! You've completed all questions. Great work! 🎉"
                if result.get('evaluation'):
                    eval_result = result['evaluation']
                    response_data["evaluation"] = {"score": eval_result.score, "xp": eval_result.xp, "correct": eval_result.correct, "explanation": eval_result.explanation}
                return Response(response_data)

            if result.get('reply'):
                from ..models import ChatMessage
                reply_msg = ChatMessage.objects.create(session=session, user=user, content=result['reply'], is_user_message=False, response_time_ms=response_time_ms)
                response_data["feedback"] = {"id": str(reply_msg.id), "text": result['reply']}

            # If agent returned a separate proceed prompt, store it as a separate bot message
            if result.get('proceed_message'):
                from ..models import ChatMessage
                proceed_msg = ChatMessage.objects.create(session=session, user=user, content=result['proceed_message'], is_user_message=False)
                response_data["proceed_message"] = {"id": str(proceed_msg.id), "text": result['proceed_message']}

            if result.get('next_question'):
                from ..models import ChatMessage
                next_q_msg = ChatMessage.objects.create(session=session, user=user, content=result['next_question'], is_user_message=False)
                response_data["next_question"] = {"id": str(next_q_msg.id), "text": result['next_question'], "created_at": next_q_msg.created_at.isoformat()}

            if result.get('evaluation'):
                eval_result = result['evaluation']
                response_data["evaluation"] = {"score": eval_result.score, "xp": eval_result.xp, "correct": eval_result.correct, "explanation": eval_result.explanation, "followup_action": eval_result.followup_action}

            session.save()
            return Response(response_data)
        except Exception as e:
            sentry_sdk.capture_exception(e, extras={"component": "tutoring", "view": "TutoringSessionAnswerView", "user_id": str(request.user.id) if request.user else None, "session_id": session_id})
            return Response({"error": f"Failed to process answer: {str(e)}"}, status=500)


class TutoringSessionEndView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            user = request.user
            try:
                session = ChatSession.objects.get(id=session_id, user=user)
            except ChatSession.DoesNotExist:
                return Response({"error": "Tutoring session not found"}, status=404)
            
            # Use shared helper to end session (idempotent)
            result = end_session_helper(session)
            
            if result["already_ended"]:
                return Response({
                    "message": "Tutoring session was already ended",
                    "session_id": str(session.id),
                    "total_messages": result["total_messages"],
                    "insights_generated": False,
                    "insight_status": result["insight_status"]
                })
            
            return Response({
                "message": "Tutoring session ended successfully",
                "session_id": str(session.id),
                "total_messages": result["total_messages"],
                "insights_generated": result["insights_generated"],
                "insight_status": result["insight_status"]
            })
        except Exception as e:
            sentry_sdk.capture_exception(e, extras={
                "component": "tutoring",
                "view": "TutoringSessionEndView",
                "user_id": str(request.user.id) if request.user else None,
                "session_id": session_id
            })
            return Response({"error": f"Failed to end session: {str(e)}"}, status=500)


class TutoringSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            
            # Check if session has expired and auto-end if still active
            if session.is_active and is_session_expired(session):
                logger.info(f"Session {session.id} expired during detail fetch, auto-ending")
                end_session_helper(session)
            
            serializer = ChatSessionSerializer(session)
            data = serializer.data
            
            # Add timeout information for frontend timer
            data['session_expired'] = is_session_expired(session)
            data['timeout_mins'] = getattr(settings, 'SESSION_TIMEOUT_MINS', 15)
            
            return Response(data)
        except ChatSession.DoesNotExist:
            return Response({"error": "Tutoring session not found"}, status=404)


class SessionInsightsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        
            user = request.user
            try:
                session = ChatSession.objects.get(id=session_id, user=user)
            except ChatSession.DoesNotExist:
                return Response({"error": "Session not found"}, status=404)

            try:
                insight = session.insight
            except SessionInsight.DoesNotExist:
                try:
                    from api.insight_generator import generate_insights_for_session
                    insight = generate_insights_for_session(str(session.id))
                    if not insight:
                        return Response({"message": "Not enough data to generate insights yet", "reason": "At least 2 question-answer pairs are needed for analysis", "session_id": str(session.id)}, status=202)
                except Exception as e:
                    return Response({"error": "Failed to generate insights", "details": str(e)}, status=500)

            if insight.status == 'processing':
                return Response({"message": "Insights are being generated", "status": "processing", "session_id": str(session.id)}, status=202)

            if insight.status == 'failed':
                return Response({"error": "Insights generation failed", "session_id": str(session.id), "status": "failed"}, status=400)

            document_name = insight.document.filename if insight.document else session.get_title()
            return Response({
                "session_id": str(session.id),
                "document_name": document_name,
                "session_title": session.get_title(),
                "total_qa_pairs": insight.total_qa_pairs,
                "session_duration": insight.get_session_duration(),
                "status": insight.status,
                "insights": {
                    "focus_zone": insight.focus_zone if insight.focus_zone else [],
                    "steady_zone": insight.steady_zone if insight.steady_zone else [],
                    "edge_zone": insight.edge_zone if insight.edge_zone else [],
                    "xp_points": insight.xp_points,
                    "accuracy": insight.accuracy
                },
                "legacy_swot": {
                    "strength": insight.strength if insight.strength else None,
                    "weakness": insight.weakness if insight.weakness else None,
                    "opportunity": insight.opportunity if insight.opportunity else None,
                    "threat": insight.threat if insight.threat else None
                } if (insight.strength or insight.weakness) else None,
                "created_at": insight.created_at.isoformat(),
                "updated_at": insight.updated_at.isoformat()
            })


class UserSessionsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')
            session_data = []
            for session in sessions:
                document_name = "Unknown Document"
                try:
                    if hasattr(session, 'document') and session.document:
                        document_name = session.document.filename
                    else:
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
            return Response({"error": f"Failed to fetch sessions: {str(e)}"}, status=500)


class SessionFeedbackView(APIView):
    """
    View to submit post-session feedback
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, session_id):
        try:
            user = request.user
            
            # Verify session exists and belongs to user
            try:
                session = ChatSession.objects.get(id=session_id, user=user)
            except ChatSession.DoesNotExist:
                return Response(
                    {"error": "Session not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if feedback already exists
            if hasattr(session, 'feedback') and session.feedback:
                return Response(
                    {"error": "Feedback already submitted for this session"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create feedback
            serializer = SessionFeedbackSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(session=session, user=user)
                return Response(
                    {
                        "message": "Feedback submitted successfully",
                        "feedback": serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {"error": "Invalid feedback data", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            sentry_sdk.capture_exception(e, extras={
                "component": "tutoring",
                "view": "SessionFeedbackView",
                "user_id": str(request.user.id) if request.user else None,
                "session_id": session_id
            })
            return Response(
                {"error": f"Failed to submit feedback: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get(self, request, session_id):
        """Get existing feedback for a session"""
        try:
            user = request.user
            
            try:
                session = ChatSession.objects.get(id=session_id, user=user)
            except ChatSession.DoesNotExist:
                return Response(
                    {"error": "Session not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check if feedback exists
            try:
                feedback = session.feedback
                serializer = SessionFeedbackSerializer(feedback)
                return Response(serializer.data)
            except SessionFeedback.DoesNotExist:
                return Response(
                    {"message": "No feedback submitted yet"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            sentry_sdk.capture_exception(e)
            return Response(
                {"error": f"Failed to retrieve feedback: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


__all__ = [
    'TutoringSessionStartView', 'TutoringSessionAnswerView',
    'TutoringSessionEndView', 'TutoringSessionDetailView',
    'SessionInsightsView', 'UserSessionsListView', 'SessionFeedbackView'
]
