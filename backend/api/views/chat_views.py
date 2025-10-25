from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import sentry_sdk
import time
from ..rag_query import query_rag
from ..models import ChatSession, ChatMessage
from ..serializers import ChatSessionListSerializer, ChatSessionSerializer, ChatMessageSerializer


class ChatBotView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, *args, **kwargs):
		message = request.data.get('message', '').strip()
		session_id = request.data.get('session_id')
		if not message:
			return Response({"error": "Message is required"}, status=400)
		try:
			user = request.user
			user_id = str(user.id)
			if not hasattr(request, 'user'):
				return Response({"error": "Unauthorized"}, status=401)

			if not getattr(__import__('api.gemini_client', fromlist=['gemini_client']), 'gemini_client').is_available():
				return Response({"error": "AI service is currently unavailable"}, status=503)

			chat_session = self._get_or_create_session(user, session_id)
			user_message = ChatMessage.objects.create(session=chat_session, user=user, content=message, is_user_message=True)

			start_time = time.time()
			response = query_rag(user_id, message)
			response_time_ms = int((time.time() - start_time) * 1000)

			ai_message = ChatMessage.objects.create(session=chat_session, user=user, content=response, is_user_message=False, response_time_ms=response_time_ms, token_count=len(response.split()))
			chat_session.save()

			return Response({"response": response, "user_message": message, "session_id": str(chat_session.id), "message_id": str(ai_message.id), "response_time_ms": response_time_ms})
		except Exception as e:
			sentry_sdk.capture_exception(e, extras={"component": "chat", "view": "ChatBotView", "user_id": str(request.user.id) if request.user else None, "session_id": session_id})
			return Response({"error": f"Failed to generate response: {str(e)}"}, status=500)

	def _get_or_create_session(self, user, session_id=None):
		if session_id:
			try:
				session = ChatSession.objects.get(id=session_id, user=user, is_active=True)
				return session
			except ChatSession.DoesNotExist:
				pass
		# Use user's preferred language when creating new session
		language = getattr(user, 'preferred_language', user.PREFERRED_LANGUAGE_CHOICES[0][0])
		return ChatSession.objects.create(user=user, language=language)


class ChatSessionListView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		sessions = ChatSession.objects.filter(user=request.user, is_active=True)
		serializer = ChatSessionListSerializer(sessions, many=True)
		return Response(serializer.data)


class ChatSessionDetailView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, session_id):
		try:
			session = ChatSession.objects.get(id=session_id, user=request.user, is_active=True)
			serializer = ChatSessionSerializer(session)
			return Response(serializer.data)
		except ChatSession.DoesNotExist:
			return Response({"error": "Chat session not found"}, status=404)

	def delete(self, request, session_id):
		try:
			session = ChatSession.objects.get(id=session_id, user=request.user, is_active=True)
			session.is_active = False
			session.save()
			return Response({"message": "Chat session deleted successfully"})
		except ChatSession.DoesNotExist:
			return Response({"error": "Chat session not found"}, status=404)


__all__ = ['ChatBotView', 'ChatSessionListView', 'ChatSessionDetailView']
