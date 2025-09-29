from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, Document


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
