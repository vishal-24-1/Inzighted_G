# Generated migration for SessionFeedback model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_document_deleted_at_document_deleted_by_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SessionFeedback',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('rating', models.IntegerField(blank=True, help_text='User rating 0-10 for recommendation likelihood', null=True)),
                ('liked', models.TextField(blank=True, help_text='What the user liked about the session (optional)')),
                ('improve', models.TextField(blank=True, help_text='What the user thinks should be improved (required unless skipped)')),
                ('skipped', models.BooleanField(default=False, help_text='Whether the user skipped the feedback form')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='feedback', to='api.chatsession')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='session_feedbacks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Session Feedback',
                'verbose_name_plural': 'Session Feedbacks',
                'ordering': ['-created_at'],
            },
        ),
    ]
