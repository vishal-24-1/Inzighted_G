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
    language = models.CharField(max_length=16, default="tanglish", help_text="Language preference: tanglish or english")
    
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
    
    # New fields for Tanglish agent flow
    classifier_token = models.CharField(max_length=32, null=True, blank=True, help_text="Intent classifier result: DIRECT_ANSWER, MIXED, or RETURN_QUESTION")
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        message_type = "User" if self.is_user_message else "AI"
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{message_type}: {preview}"


class SessionInsight(models.Model):
    """
    Model to store BoostMe insights for completed tutoring sessions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name='insight')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='session_insights')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='session_insights', null=True, blank=True)
    
    # BoostMe Insights Fields (3 Zones)
    focus_zone = models.JSONField(null=True, blank=True, help_text="Array of 2 Tanglish points - low understanding/weak areas")
    steady_zone = models.JSONField(null=True, blank=True, help_text="Array of 2 Tanglish points - high clarity/strong areas")
    edge_zone = models.JSONField(null=True, blank=True, help_text="Array of 2 Tanglish points - potential improvement/growth areas")
    
    # Performance Metrics
    xp_points = models.IntegerField(default=0, help_text="Total XP earned (1 XP per answered question)")
    accuracy = models.FloatField(null=True, blank=True, help_text="Percentage accuracy (0-100) based on correct answers")
    
    # Legacy SWOT Fields (deprecated but kept for migration compatibility)
    strength = models.TextField(blank=True, default='', help_text="DEPRECATED: Use steady_zone instead")
    weakness = models.TextField(blank=True, default='', help_text="DEPRECATED: Use focus_zone instead")
    opportunity = models.TextField(blank=True, default='', help_text="DEPRECATED: Use edge_zone instead")
    threat = models.TextField(blank=True, default='', help_text="DEPRECATED: No longer used")
    
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


class QuestionItem(models.Model):
    """
    Model to store individual structured questions with archetype metadata.
    Extends TutoringQuestionBatch for the new Tanglish agent flow.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='question_items')
    batch = models.ForeignKey(TutoringQuestionBatch, on_delete=models.CASCADE, null=True, blank=True, related_name='structured_questions')
    
    # Question metadata from spec
    question_id = models.CharField(max_length=64, help_text="Auto-generated question ID")
    archetype = models.CharField(max_length=64, choices=[
        ('Concept Unfold', 'Concept Unfold'),
        ('Critical Reversal', 'Critical Reversal'),
        ('Application Sprint', 'Application Sprint'),
        ('Explainer Role', 'Explainer Role'),
        ('Scenario Repair', 'Scenario Repair'),
        ('Experimental Thinking', 'Experimental Thinking'),
        ('Debate Card', 'Debate Card'),
    ], help_text="Question archetype from spec")
    question_text = models.TextField(help_text="The Tanglish question text")
    difficulty = models.CharField(max_length=16, choices=[
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ])
    expected_answer = models.TextField(help_text="Expected answer or key concepts")
    order = models.IntegerField(default=0, help_text="Question order in sequence")
    asked = models.BooleanField(default=False, help_text="Whether question has been asked")
    
    # Question selection scoring
    topic_diversity_score = models.FloatField(default=0.0)
    cognitive_variety_score = models.FloatField(default=0.0)
    difficulty_progression_score = models.FloatField(default=0.0)
    recency_penalty = models.FloatField(default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = "Question Item"
        verbose_name_plural = "Question Items"
    
    def __str__(self):
        return f"Q{self.order}: {self.archetype} - {self.question_text[:50]}..."
    
    def compute_question_score(self):
        """Compute selection score using the formula from spec"""
        score = (0.45 * self.topic_diversity_score + 
                 0.30 * self.cognitive_variety_score + 
                 0.20 * self.difficulty_progression_score - 
                 0.05 * self.recency_penalty)
        return score


class EvaluatorResult(models.Model):
    """
    Model to store answer evaluation results with XP, score, and Tanglish feedback.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.OneToOneField(ChatMessage, on_delete=models.CASCADE, related_name='evaluation')
    question = models.ForeignKey(QuestionItem, on_delete=models.SET_NULL, null=True, blank=True, related_name='evaluations')
    
    # Evaluation results from Gemini judge
    raw_json = models.JSONField(help_text="Raw JSON response from evaluator")
    score = models.FloatField(help_text="Score between 0.0 and 1.0")
    correct = models.BooleanField(help_text="Whether answer is correct (score >= 0.75)")
    xp = models.IntegerField(default=0, help_text="XP points awarded (1-100)")
    explanation = models.TextField(help_text="Tanglish explanation of evaluation")
    confidence = models.FloatField(help_text="Evaluator confidence (0.0-1.0)")
    followup_action = models.CharField(max_length=32, choices=[
        ('none', 'None'),
        ('give_hint', 'Give Hint'),
        ('ask_clarification', 'Ask Clarification'),
        ('show_solution', 'Show Solution'),
    ], default='none')
    return_question_answer = models.TextField(blank=True, help_text="Tanglish hint or correction to send to student")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Evaluator Result"
        verbose_name_plural = "Evaluator Results"
    
    def __str__(self):
        return f"Eval: {self.score:.2f} ({self.xp}XP) - {self.explanation[:50]}..."
