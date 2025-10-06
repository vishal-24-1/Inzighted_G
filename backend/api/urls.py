from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, ProfileView, GoogleAuthView,
    IngestView, QueryView, DocumentListView, DocumentStatusView, ChatBotView,
    ChatSessionListView, ChatSessionDetailView,
    TutoringSessionStartView, TutoringSessionAnswerView, 
    TutoringSessionEndView, TutoringSessionDetailView,
    SessionInsightsView, UserSessionsListView
)
from .agent import (
    AgentSessionStartView, AgentRespondView, 
    AgentSessionStatusView, AgentLanguageToggleView
)

urlpatterns = [
    # Authentication URLs
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/google/', GoogleAuthView.as_view(), name='google_auth'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', ProfileView.as_view(), name='profile'),
    
    # RAG URLs
    path('documents/', DocumentListView.as_view(), name='documents'),
    path('documents/<uuid:document_id>/status/', DocumentStatusView.as_view(), name='document_status'),
    path('ingest/', IngestView.as_view(), name='ingest'),
    path('query/', QueryView.as_view(), name='query'),
    
    # ChatBot URLs
    path('chat/', ChatBotView.as_view(), name='chatbot'),
    path('chat/sessions/', ChatSessionListView.as_view(), name='chat_sessions'),
    path('chat/sessions/<uuid:session_id>/', ChatSessionDetailView.as_view(), name='chat_session_detail'),
    
    # Tutoring URLs
    path('tutoring/start/', TutoringSessionStartView.as_view(), name='tutoring_start'),
    path('tutoring/<uuid:session_id>/answer/', TutoringSessionAnswerView.as_view(), name='tutoring_answer'),
    path('tutoring/<uuid:session_id>/end/', TutoringSessionEndView.as_view(), name='tutoring_end'),
    path('tutoring/<uuid:session_id>/', TutoringSessionDetailView.as_view(), name='tutoring_detail'),
    
    # Insights URLs
    path('sessions/', UserSessionsListView.as_view(), name='user_sessions'),
    path('sessions/<uuid:session_id>/insights/', SessionInsightsView.as_view(), name='session_insights'),
    
    # NEW: Tanglish Agent URLs (implements spec flow)
    path('agent/session/start/', AgentSessionStartView.as_view(), name='agent_session_start'),
    path('agent/session/<uuid:session_id>/respond/', AgentRespondView.as_view(), name='agent_respond'),
    path('agent/session/<uuid:session_id>/status/', AgentSessionStatusView.as_view(), name='agent_status'),
    path('agent/session/<uuid:session_id>/language/', AgentLanguageToggleView.as_view(), name='agent_language_toggle'),
]