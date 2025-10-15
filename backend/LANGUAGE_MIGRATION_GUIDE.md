# Migration Guide for Dynamic Language Support

## Database Changes Required

### 1. Ensure User Model Has `preferred_language` Field

Check if your User model already has the `preferred_language` field:

```python
# In api/models.py or your custom user model

class User(AbstractUser):
    LANGUAGE_CHOICES = [
        ('english', 'English'),
        ('tanglish', 'Tanglish'),
    ]
    
    preferred_language = models.CharField(
        max_length=20, 
        choices=LANGUAGE_CHOICES, 
        default='tanglish',
        null=True,
        blank=True
    )
```

### 2. Create Migration (if field doesn't exist)

If the `preferred_language` field doesn't exist, create a migration:

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

### 3. Ensure ChatSession Has `language` Field

The ChatSession model should have a `language` field:

```python
class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="Chat Session")
    language = models.CharField(max_length=20, default='tanglish')
    # ... other fields
```

If this field is missing, add it and run migrations.

## Post-Migration Steps

### 1. Update Existing Users

Set default language for existing users:

```python
# Run in Django shell: python manage.py shell

from api.models import User

# Option 1: Set all existing users to tanglish
User.objects.filter(preferred_language__isnull=True).update(preferred_language='tanglish')

# Option 2: Set based on some criteria
# English-speaking users
User.objects.filter(country='US').update(preferred_language='english')

# Tanglish users
User.objects.filter(country='IN').update(preferred_language='tanglish')
```

### 2. Update Existing Sessions

Ensure all existing sessions have a language:

```python
from api.models import ChatSession

# Set language for sessions without language
ChatSession.objects.filter(language__isnull=True).update(language='tanglish')

# Or sync with user's preference
for session in ChatSession.objects.all():
    if not session.language and session.user.preferred_language:
        session.language = session.user.preferred_language
        session.save()
```

### 3. Verify Changes

```python
# Check users without language preference
User.objects.filter(preferred_language__isnull=True).count()

# Check sessions without language
ChatSession.objects.filter(language__isnull=True).count()

# Should both return 0
```

## Adding New Languages

### 1. Update LANGUAGE_CHOICES in User Model

```python
class User(AbstractUser):
    LANGUAGE_CHOICES = [
        ('english', 'English'),
        ('tanglish', 'Tanglish'),
        ('hindi', 'Hindi'),        # Add new language
        ('spanish', 'Spanish'),    # Add new language
        ('tamil', 'Tamil'),        # Add new language
    ]
    
    preferred_language = models.CharField(
        max_length=20, 
        choices=LANGUAGE_CHOICES, 
        default='tanglish'
    )
```

### 2. Run Migration

```bash
python manage.py makemigrations
python manage.py migrate
```

### 3. Test New Language

```python
# In Django shell
from api.models import User, ChatSession
from api.agent_flow import TutorAgent

# Create test user with new language
user = User.objects.create(username='hindi_user', preferred_language='hindi')

# Create session
session = ChatSession.objects.create(user=user, title='Hindi Test')

# Initialize agent
agent = TutorAgent(session)

# Verify language propagation
print(f"User language: {user.preferred_language}")
print(f"Session language: {session.language}")
print(f"Agent language: {agent.language}")
# All should show 'hindi'
```

## Rollback Plan

If you need to rollback the changes:

### 1. Revert Code Changes

```bash
git revert <commit-hash>
```

### 2. No Database Rollback Needed

The changes are backward compatible:
- New `preferred_language` field has default='tanglish'
- All code has fallback chains
- Existing data continues to work

### 3. Optional: Remove Field

If you want to remove the `preferred_language` field:

```python
# Create migration
class Migration(migrations.Migration):
    dependencies = [
        ('api', 'XXXX_previous_migration'),
    ]
    
    operations = [
        migrations.RemoveField(
            model_name='user',
            name='preferred_language',
        ),
    ]
```

## Testing Checklist

After migration, verify:

- [ ] All users have a `preferred_language` value (or NULL)
- [ ] All sessions have a `language` value
- [ ] New sessions inherit user's preferred_language
- [ ] Agent reads correct language from user
- [ ] Questions generated in correct language
- [ ] Evaluations use correct language
- [ ] Insights generated in correct language
- [ ] Changing user's language affects new sessions
- [ ] Existing sessions maintain their language

## Common Issues

### Issue 1: Field Already Exists

**Error**: `django.db.utils.OperationalError: duplicate column name: preferred_language`

**Solution**: Skip migration, field already exists
```bash
python manage.py migrate --fake
```

### Issue 2: NULL Values

**Error**: Users or sessions have NULL language

**Solution**: Run the update scripts in Post-Migration Steps

### Issue 3: Language Mismatch

**Problem**: User has preferred_language='english' but gets Tanglish questions

**Debug**:
```python
# Check the language flow
user = User.objects.get(username='problem_user')
session = ChatSession.objects.filter(user=user).last()
agent = TutorAgent(session)

print(f"User.preferred_language: {user.preferred_language}")
print(f"Session.language: {session.language}")
print(f"Agent.language: {agent.language}")
```

**Solution**: Ensure session was created AFTER code deployment

## Monitoring

Add logging to track language usage:

```python
# In views/tutoring_views.py
import logging
logger = logging.getLogger(__name__)

# In TutoringSessionStartView.post()
logger.info(f"Creating session for user {user.username} with language: {language}")

# In agent_flow.py TutorAgent.__init__()
logger.info(f"TutorAgent initialized with language: {self.language}")
```

Check logs to ensure language is flowing correctly through the system.
