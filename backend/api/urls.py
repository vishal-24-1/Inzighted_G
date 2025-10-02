from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, ProfileView,
    IngestView, QueryView, DocumentListView, ChatBotView,
    ChatSessionListView, ChatSessionDetailView,
    TutoringSessionStartView, TutoringSessionAnswerView, 
    TutoringSessionEndView, TutoringSessionDetailView,
    SessionInsightsView, UserSessionsListView
)

urlpatterns = [
    # Authentication URLs
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', ProfileView.as_view(), name='profile'),
    
    # RAG URLs
    path('documents/', DocumentListView.as_view(), name='documents'),
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
]
