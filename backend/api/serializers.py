from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Document, ChatSession, ChatMessage, SessionFeedback
import logging
from django.db import DatabaseError, IntegrityError

logger = logging.getLogger(__name__)

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('email', 'username', 'name', 'password', 'password_confirm', 'preferred_language')
    
    def validate(self, attrs):
        pwd = attrs.get('password')
        pwd_confirm = attrs.get('password_confirm')
        if not pwd or not pwd_confirm:
            raise serializers.ValidationError("Password and password_confirm are required")
        if pwd != pwd_confirm:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        # Extract known fields safely
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password', None)
        preferred_language = validated_data.pop('preferred_language', None)

        email = validated_data.get('email')
        username = validated_data.get('username')
        name = validated_data.get('name')

        # Normalize and infer missing username from email
        if email:
            email = email.strip().lower()
        if not username and email:
            username = email.split('@')[0]

        if not email or not password:
            raise serializers.ValidationError('Email and password are required')

        try:
            # Use create_user to ensure password hashing and user manager logic
            user = User.objects.create_user(email=email, username=username, password=password)
            # Set optional fields that create_user may not accept
            if name:
                user.name = name
            if preferred_language:
                try:
                    user.preferred_language = preferred_language
                    user.save()
                except DatabaseError as db_err:
                    # If DB schema not updated yet, log and continue without failing registration
                    logger.warning("Could not save preferred_language (migration missing?): %s", db_err)
                    # Attempt to save without preferred_language to ensure user exists
                    try:
                        user.save(update_fields=[f for f in ['name'] if getattr(user, 'name', None)])
                    except Exception:
                        # fallback to full save if update_fields not possible
                        try:
                            user.save()
                        except Exception:
                            pass
            else:
                user.save()
            return user
        except IntegrityError as ie:
            logger.warning("IntegrityError creating user: %s", ie)
            raise serializers.ValidationError({'non_field_errors': 'A user with that email or username already exists.'})
        except Exception as e:
            # Convert to serializer validation error so DRF returns 400 instead of 500
            logger.exception("Error creating user: %s", e)
            raise serializers.ValidationError({'non_field_errors': str(e)})

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Email and password are required')
        
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'name', 'created_at', 'preferred_language')
        read_only_fields = ('id', 'created_at')

    def update(self, instance, validated_data):
        # Update fields safely and handle DB errors for optional fields
        preferred_language = validated_data.pop('preferred_language', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        try:
            if preferred_language is not None:
                instance.preferred_language = preferred_language
            instance.save()
        except DatabaseError as db_err:
            logger.warning("Could not update preferred_language (migration missing?): %s", db_err)
            # attempt to save other fields only
            try:
                instance.save(update_fields=[k for k in validated_data.keys() if hasattr(instance, k)])
            except Exception:
                pass

        return instance

class GoogleAuthSerializer(serializers.Serializer):
    """
    Serializer for Google OAuth authentication
    Accepts the credential (ID token) from Google Sign-In
    """
    credential = serializers.CharField(required=True, help_text="Google ID token from OAuth")
    
    def validate_credential(self, value):
        if not value or len(value) < 10:
            raise serializers.ValidationError("Invalid Google credential token")
        return value

class RagQuerySerializer(serializers.Serializer):
    query = serializers.CharField()

class DocumentIngestSerializer(serializers.Serializer):
    file = serializers.FileField()

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('id', 'filename', 'file_size', 's3_key', 'upload_date', 'status')
        read_only_fields = ('id', 's3_key', 'upload_date')


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ('id', 'content', 'is_user_message', 'created_at', 'response_time_ms', 'token_count')
        read_only_fields = ('id', 'created_at')


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    title = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    # include document metadata so UI can show the uploaded/selected document name
    document = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = ('id', 'title', 'created_at', 'updated_at', 'is_active', 'messages', 'message_count', 'document')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_title(self, obj):
        return obj.get_title()
    
    def get_message_count(self, obj):
        return obj.messages.count()

    def get_document(self, obj):
        if hasattr(obj, 'document') and obj.document:
            return {
                'id': str(obj.document.id),
                'filename': obj.document.filename,
                'status': obj.document.status
            }
        return None


class ChatSessionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing chat sessions without messages"""
    title = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = ('id', 'title', 'created_at', 'updated_at', 'is_active', 'message_count', 'last_message_at', 'document')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_title(self, obj):
        return obj.get_title()
    
    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_last_message_at(self, obj):
        last_message = obj.messages.last()
        return last_message.created_at if last_message else obj.created_at

    def get_document(self, obj):
        # lightweight document info for list views
        try:
            if hasattr(obj, 'document') and obj.document:
                return obj.document.filename
        except Exception:
            pass
        return None


class SessionFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for session feedback"""
    
    class Meta:
        model = SessionFeedback
        fields = ('id', 'session', 'rating', 'liked', 'improve', 'skipped', 'created_at')
        read_only_fields = ('id', 'session', 'created_at')
    
    def validate(self, attrs):
        """Validate that either feedback is provided or skipped is True"""
        skipped = attrs.get('skipped', False)
        improve = attrs.get('improve', '').strip()
        
        if not skipped and not improve:
            raise serializers.ValidationError({
                'improve': 'This field is required unless you skip the feedback.'
            })
        
        return attrs


class ProgressSerializer(serializers.Serializer):
    """
    Serializer for user gamification progress (Streak and Batch systems)
    
    This is a read-only serializer that formats the progress data from
    the progress.get_progress_summary() function.
    """
    
    streak = serializers.DictField(
        help_text="Streak system progress with current streak, milestones, and next goal"
    )
    batch = serializers.DictField(
        help_text="Batch system progress with current batch, stars, and XP information"
    )
    
    class Meta:
        fields = ('streak', 'batch')
