from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, ProfileView,
    IngestView, QueryView, DocumentListView
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
]
