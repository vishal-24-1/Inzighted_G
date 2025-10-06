from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, Document, TutoringQuestionBatch
from .models import ChatSession, ChatMessage, SessionInsight
from .models import QuestionItem, EvaluatorResult


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
	model = User
	list_display = ('email', 'name', 'username', 'is_active', 'is_staff', 'created_at')
	list_filter = ('is_active', 'is_staff', 'is_superuser')
	search_fields = ('email', 'name', 'username')
	ordering = ('-created_at',)
	fieldsets = (
		(None, {'fields': ('email', 'username', 'password')}),
		('Personal info', {'fields': ('name',)}),
		('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
		('Important dates', {'fields': ('last_login', 'date_joined')}),
	)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
	model = Document
	list_display = ('filename', 'user', 'file_size', 'status', 'upload_date')
	list_filter = ('status', 'upload_date')
	search_fields = ('filename', 'user__email', 'user__name')
	readonly_fields = ('upload_date',)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
	"""Admin for ChatSession: show key fields and allow filtering by active state."""
	model = ChatSession
	list_display = ('id', 'user', 'title', 'language', 'is_active', 'updated_at')
	list_filter = ('is_active', 'language', 'created_at')
	search_fields = ('title', 'user__email', 'user__name')
	readonly_fields = ('id', 'created_at', 'updated_at')
	
	fieldsets = (
		('Session Information', {
			'fields': ('user', 'document', 'title', 'language', 'is_active')
		}),
		('Timestamps', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		})
	)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
	"""Admin for ChatMessage: show key fields and allow filtering by message type (user vs tutor)."""
	model = ChatMessage
	list_display = ('id', 'session_title', 'user', 'is_user_message', 'classifier_token', 'created_at')
	list_filter = ('is_user_message', 'classifier_token', 'created_at')
	search_fields = ('content', 'user__email', 'user__name', 'session__title')
	readonly_fields = ('id', 'created_at', 'content_preview')
	
	fieldsets = (
		('Message Information', {
			'fields': ('session', 'user', 'is_user_message', 'classifier_token')
		}),
		('Content', {
			'fields': ('content', 'content_preview'),
			'classes': ('wide',)
		}),
		('Metadata', {
			'fields': ('response_time_ms', 'token_count', 'created_at'),
			'classes': ('collapse',)
		})
	)
	
	def session_title(self, obj):
		"""Display session title"""
		return obj.session.get_title() if obj.session else "N/A"
	session_title.short_description = 'Session'
	session_title.admin_order_field = 'session__title'
	
	def content_preview(self, obj):
		"""Display content preview"""
		preview = obj.content[:150] + "..." if len(obj.content) > 150 else obj.content
		return preview
	content_preview.short_description = 'Content Preview'


@admin.register(SessionInsight)
class SessionInsightAdmin(admin.ModelAdmin):
	"""Admin for SessionInsight: manage SWOT analysis insights for tutoring sessions."""
	model = SessionInsight
	list_display = ('id', 'session_title', 'user', 'document', 'status', 'total_qa_pairs', 'session_duration_display', 'created_at')
	list_filter = ('status', 'created_at', 'updated_at')
	search_fields = ('user__name', 'user__email', 'session__title', 'document__filename')
	readonly_fields = ('id', 'created_at', 'updated_at', 'session_duration_display')
	
	fieldsets = (
		('Session Information', {
			'fields': ('session', 'user', 'document', 'status', 'total_qa_pairs', 'session_duration_minutes')
		}),
		('SWOT Analysis', {
			'fields': ('strength', 'weakness', 'opportunity', 'threat'),
			'classes': ('wide',)
		}),
		('Timestamps', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		})
	)
	
	def session_title(self, obj):
		"""Display session title in admin list"""
		return obj.session.get_title()
	session_title.short_description = 'Session Title'
	session_title.admin_order_field = 'session__title'
	
	def session_duration_display(self, obj):
		"""Display formatted session duration"""
		duration = obj.get_session_duration()
		if duration:
			return f"{duration} minutes"
		return "N/A"
	session_duration_display.short_description = 'Duration'
	session_duration_display.admin_order_field = 'session_duration_minutes'


@admin.register(TutoringQuestionBatch)
class TutoringQuestionBatchAdmin(admin.ModelAdmin):
	"""Admin for TutoringQuestionBatch: manage pre-generated question batches for tutoring sessions."""
	model = TutoringQuestionBatch
	list_display = ('id', 'session_title', 'user', 'document_name', 'status', 'question_progress', 'created_at')
	list_filter = ('status', 'created_at', 'updated_at')
	search_fields = ('user__name', 'user__email', 'session__title', 'document__filename')
	readonly_fields = ('id', 'created_at', 'updated_at', 'question_progress_display')
	
	fieldsets = (
		('Session Information', {
			'fields': ('session', 'user', 'document', 'status', 'source_doc_id', 'tenant_tag')
		}),
		('Questions', {
			'fields': ('questions', 'current_question_index', 'total_questions', 'question_progress_display'),
			'classes': ('wide',)
		}),
		('Timestamps', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		})
	)
	
	def session_title(self, obj):
		"""Display session title in admin list"""
		return obj.session.get_title()
	session_title.short_description = 'Session Title'
	session_title.admin_order_field = 'session__title'
	
	def document_name(self, obj):
		"""Display document name in admin list"""
		return obj.document.filename if obj.document else "No Document"
	document_name.short_description = 'Document'
	document_name.admin_order_field = 'document__filename'
	
	def question_progress(self, obj):
		"""Display question progress in admin list"""
		return f"{obj.current_question_index + 1}/{obj.total_questions}"
	question_progress.short_description = 'Progress'
	
	def question_progress_display(self, obj):
		"""Display detailed question progress"""
		return f"Question {obj.current_question_index + 1} of {obj.total_questions} ({obj.status})"
	question_progress_display.short_description = 'Question Progress'


@admin.register(QuestionItem)
class QuestionItemAdmin(admin.ModelAdmin):
	"""Admin for QuestionItem: manage individual structured questions with archetypes."""
	model = QuestionItem
	list_display = ('question_id', 'archetype', 'difficulty', 'order', 'asked', 'session_title', 'created_at')
	list_filter = ('archetype', 'difficulty', 'asked', 'created_at')
	search_fields = ('question_id', 'question_text', 'session__title', 'session__user__email')
	readonly_fields = ('id', 'question_id', 'created_at', 'question_score_display')
	
	fieldsets = (
		('Question Information', {
			'fields': ('session', 'batch', 'question_id', 'order', 'asked')
		}),
		('Question Details', {
			'fields': ('archetype', 'difficulty', 'question_text', 'expected_answer'),
			'classes': ('wide',)
		}),
		('Scoring Metrics', {
			'fields': ('topic_diversity_score', 'cognitive_variety_score', 
			          'difficulty_progression_score', 'recency_penalty', 'question_score_display'),
			'classes': ('collapse',)
		}),
		('Metadata', {
			'fields': ('created_at',),
			'classes': ('collapse',)
		})
	)
	
	def session_title(self, obj):
		"""Display session title in admin list"""
		return obj.session.get_title() if obj.session else "N/A"
	session_title.short_description = 'Session'
	session_title.admin_order_field = 'session__title'
	
	def question_score_display(self, obj):
		"""Display computed question score"""
		score = obj.compute_question_score()
		return f"{score:.4f}"
	question_score_display.short_description = 'Computed Score'


@admin.register(EvaluatorResult)
class EvaluatorResultAdmin(admin.ModelAdmin):
	"""Admin for EvaluatorResult: manage answer evaluations with XP and Tanglish feedback."""
	model = EvaluatorResult
	list_display = ('id', 'student_name', 'score', 'xp', 'correct', 'confidence', 
	                'followup_action', 'question_archetype', 'created_at')
	list_filter = ('correct', 'followup_action', 'created_at')
	search_fields = ('message__user__name', 'message__user__email', 'explanation', 
	                 'question__question_text')
	readonly_fields = ('id', 'created_at', 'raw_json', 'student_answer', 'question_text_display')
	
	fieldsets = (
		('Evaluation Metadata', {
			'fields': ('message', 'question', 'created_at')
		}),
		('Evaluation Results', {
			'fields': ('score', 'correct', 'xp', 'confidence', 'followup_action'),
		}),
		('Feedback', {
			'fields': ('explanation', 'return_question_answer'),
			'classes': ('wide',)
		}),
		('Context (Read-only)', {
			'fields': ('student_answer', 'question_text_display'),
			'classes': ('collapse',)
		}),
		('Raw Data', {
			'fields': ('raw_json',),
			'classes': ('collapse',)
		})
	)
	
	def student_name(self, obj):
		"""Display student name"""
		return obj.message.user.name if obj.message and obj.message.user else "N/A"
	student_name.short_description = 'Student'
	student_name.admin_order_field = 'message__user__name'
	
	def question_archetype(self, obj):
		"""Display question archetype"""
		return obj.question.archetype if obj.question else "N/A"
	question_archetype.short_description = 'Archetype'
	question_archetype.admin_order_field = 'question__archetype'
	
	def student_answer(self, obj):
		"""Display student's answer text"""
		if obj.message:
			answer = obj.message.content
			return answer[:200] + "..." if len(answer) > 200 else answer
		return "N/A"
	student_answer.short_description = "Student's Answer"
	
	def question_text_display(self, obj):
		"""Display the question text"""
		if obj.question:
			text = obj.question.question_text
			return text[:200] + "..." if len(text) > 200 else text
		return "N/A"
	question_text_display.short_description = "Question Text"
