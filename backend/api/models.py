from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Google OAuth fields
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True, help_text="Google OAuth user ID")
    google_access_token = models.TextField(null=True, blank=True, help_text="Google OAuth access token")
    google_refresh_token = models.TextField(null=True, blank=True, help_text="Google OAuth refresh token")
    is_google_user = models.BooleanField(default=False, help_text="Whether user signed up via Google")
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.email})"

class Document(models.Model):
    """
    Model to track uploaded documents
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    filename = models.CharField(max_length=255)
    file_size = models.IntegerField()
    s3_key = models.CharField(max_length=500, null=True, blank=True)  # S3 object key
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=[
        ('uploading', 'Uploading'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='uploading')
    
    def __str__(self):
        return f"{self.filename} - {self.user.name}"


class ChatSession(models.Model):
    """
    Model to track chat sessions for each user
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_sessions', help_text='Document this session is based on (for tutoring sessions)')
    title = models.CharField(max_length=255, blank=True)  # Auto-generated from first message
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Chat Session - {self.user.name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
    def get_title(self):
        """Generate title from first user message if not set"""
        if self.title:
            return self.title
        
        first_message = self.messages.filter(is_user_message=True).first()
        if first_message:
            # Use first 50 characters of the first message as title
            title = first_message.content[:50]
            if len(first_message.content) > 50:
                title += "..."
            return title
        return f"Chat {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class ChatMessage(models.Model):
    """
    Model to store individual chat messages within a session
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    content = models.TextField()
    is_user_message = models.BooleanField()  # True for user messages, False for AI responses
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional fields for tracking AI response metadata
    response_time_ms = models.IntegerField(null=True, blank=True)  # Time taken to generate response
    token_count = models.IntegerField(null=True, blank=True)  # Approximate token count
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        message_type = "User" if self.is_user_message else "AI"
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{message_type}: {preview}"


class SessionInsight(models.Model):
    """
    Model to store SWOT analysis insights for completed tutoring sessions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name='insight')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='session_insights')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='session_insights', null=True, blank=True)
    
    # SWOT Analysis Fields
    strength = models.TextField(help_text="Student's strengths identified from the session")
    weakness = models.TextField(help_text="Areas where student needs improvement")
    opportunity = models.TextField(help_text="Learning opportunities for the student")
    threat = models.TextField(help_text="Potential challenges or obstacles")
    
    # Session Metadata
    total_qa_pairs = models.IntegerField(default=0, help_text="Total question-answer pairs in the session")
    session_duration_minutes = models.IntegerField(null=True, blank=True, help_text="Duration of session in minutes")
    
    # Processing Status
    status = models.CharField(max_length=50, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Session Insight"
        verbose_name_plural = "Session Insights"
    
    def __str__(self):
        return f"Insights for {self.session.get_title()} - {self.user.name}"
    
    def get_session_duration(self):
        """Calculate session duration from first to last message"""
        if self.session_duration_minutes:
            return self.session_duration_minutes
            
        messages = self.session.messages.all()
        if messages.count() < 2:
            return 0
            
        first_message = messages.first()
        last_message = messages.last()
        duration = (last_message.created_at - first_message.created_at).total_seconds() / 60
        return round(duration)


class TutoringQuestionBatch(models.Model):
    """
    Model to store pre-generated batches of tutoring questions for a session
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name='question_batch')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='question_batches')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='question_batches', null=True, blank=True)
    
    # Questions stored as JSON array
    questions = models.JSONField(help_text="Array of pre-generated questions")
    current_question_index = models.IntegerField(default=0, help_text="Index of the current question being asked")
    total_questions = models.IntegerField(help_text="Total number of questions in the batch")
    
    # Metadata
    source_doc_id = models.CharField(max_length=255, null=True, blank=True, help_text="Source document ID used for generation")
    tenant_tag = models.CharField(max_length=255, help_text="Tenant tag for multi-tenancy")
    
    # Status and timestamps
    status = models.CharField(max_length=50, choices=[
        ('generating', 'Generating'),
        ('ready', 'Ready'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='generating')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Tutoring Question Batch"
        verbose_name_plural = "Tutoring Question Batches"
    
    def __str__(self):
        return f"Question Batch for {self.session.get_title()} ({self.current_question_index}/{self.total_questions})"
    
    def get_current_question(self):
        """Get the current question to ask"""
        if (self.status == 'ready' or self.status == 'in_progress') and self.current_question_index < len(self.questions):
            return self.questions[self.current_question_index]
        return None
    
    def get_next_question(self):
        """Move to next question and return it"""
        if self.current_question_index < len(self.questions) - 1:
            self.current_question_index += 1
            self.status = 'in_progress'
            self.save()
            return self.questions[self.current_question_index]
        else:
            # All questions exhausted
            self.status = 'completed'
            self.save()
            return None
    
    def has_more_questions(self):
        """Check if there are more questions available"""
        return self.current_question_index < len(self.questions) - 1
