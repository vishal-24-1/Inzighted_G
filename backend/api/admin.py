from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, Document
from .models import ChatSession, ChatMessage, SessionInsight


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
	list_display = ('id', 'user', 'title', 'is_active', 'updated_at')
	list_filter = ('is_active',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
	"""Admin for ChatMessage: show key fields and allow filtering by message type (user vs tutor)."""
	model = ChatMessage
	list_display = ('id', 'session', 'user', 'is_user_message', 'created_at')
	list_filter = ('is_user_message',)


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
