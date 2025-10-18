"""Views package - re-export view classes from the implementation module.

This package splits the original large `views.py` into smaller modules while
keeping the original import surface. Code that imports from `api.views` will
continue to work.
"""
from .auth_views import RegisterView, LoginView, ProfileView, GoogleAuthView
from .ingest_views import IngestView, DocumentListView, DocumentStatusView, DocumentDeleteView
from .chat_views import ChatBotView, ChatSessionListView, ChatSessionDetailView
from .tutoring_views import (
    TutoringSessionStartView, TutoringSessionAnswerView,
    TutoringSessionEndView, TutoringSessionDetailView,
    SessionInsightsView, UserSessionsListView, SessionFeedbackView
)
from .rag_views import QueryView

__all__ = [
    'RegisterView', 'LoginView', 'ProfileView', 'GoogleAuthView',
    'IngestView', 'QueryView', 'DocumentListView', 'DocumentStatusView', 'DocumentDeleteView',
    'ChatBotView', 'ChatSessionListView', 'ChatSessionDetailView',
    'TutoringSessionStartView', 'TutoringSessionAnswerView',
    'TutoringSessionEndView', 'TutoringSessionDetailView',
    'SessionInsightsView', 'UserSessionsListView', 'SessionFeedbackView'
]
