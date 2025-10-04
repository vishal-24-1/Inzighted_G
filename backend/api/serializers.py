from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, Document, ChatSession, ChatMessage

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('email', 'username', 'name', 'password', 'password_confirm')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

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
        fields = ('id', 'email', 'username', 'name', 'created_at')
        read_only_fields = ('id', 'created_at')

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
