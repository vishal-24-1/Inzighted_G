"""
Django management command to pre-generate question batches for tutoring sessions.
Usage: python manage.py pregenerate_questions --user-id <user_id> --document-id <doc_id> --count 10
"""

from django.core.management.base import BaseCommand, CommandError
from api.rag_query import pregenerate_questions_for_session
from api.models import User, Document

class Command(BaseCommand):
    help = 'Pre-generate a batch of tutoring questions for a user/document'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=str,
            required=True,
            help='User ID to generate questions for'
        )
        parser.add_argument(
            '--document-id',
            type=str,
            default=None,
            help='Document ID to generate questions for (optional)'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of questions to generate (default: 10)'
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        document_id = options['document_id']
        count = options['count']

        self.stdout.write(f"Pre-generating {count} questions for user {user_id}...")
        
        if document_id:
            # Validate document exists and belongs to user
            try:
                document = Document.objects.get(id=document_id, user__id=user_id)
                self.stdout.write(f"Document: {document.filename}")
            except Document.DoesNotExist:
                raise CommandError(f"Document {document_id} not found or doesn't belong to user {user_id}")
        
        # Validate user exists
        try:
            user = User.objects.get(id=user_id)
            self.stdout.write(f"User: {user.email}")
        except User.DoesNotExist:
            raise CommandError(f"User {user_id} not found")

        # Generate questions
        try:
            result = pregenerate_questions_for_session(user_id, document_id, count)
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Successfully generated {result['questions_generated']} questions"
                    )
                )
                self.stdout.write(f"Cache key: {result['cache_key']}")
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to generate questions: {result['message']}")
                )
                
        except Exception as e:
            raise CommandError(f"Error during question generation: {str(e)}")