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
