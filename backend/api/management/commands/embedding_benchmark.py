from django.core.management.base import BaseCommand
from django.conf import settings
from api.gemini_client import gemini_client
import time


class Command(BaseCommand):
    help = 'Benchmark parallel embedding performance'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=20, help='Number of texts to embed')
        parser.add_argument('--concurrency', type=int, default=None, help='Override concurrency setting')
        parser.add_argument('--mock', action='store_true', help='Use mock texts instead of real API calls')

    def handle(self, *args, **options):
        count = options['count']
        concurrency = options['concurrency']
        use_mock = options['mock']
        
        if concurrency:
            # Temporarily override concurrency for this test
            original_concurrency = getattr(settings, 'EMBEDDING_CONCURRENCY', 5)
            settings.EMBEDDING_CONCURRENCY = concurrency
            self.stdout.write(f'Temporarily setting concurrency to {concurrency}')
        
        # Create test texts
        texts = [f"This is sample text number {i} for embedding benchmark testing." for i in range(count)]
        
        if use_mock:
            self.stdout.write(f'🧪 Mock benchmark: {count} texts')
            # Mock embedding (just return dummy vectors)
            start_time = time.time()
            mock_embeddings = [[0.1] * 768 for _ in texts]  # Dummy 768-dim vectors
            total_time = time.time() - start_time
            self.stdout.write(f'Mock embeddings: {len(mock_embeddings)} vectors in {total_time:.3f}s')
        else:
            self.stdout.write(f'🚀 Real API benchmark: {count} texts with concurrency {getattr(settings, "EMBEDDING_CONCURRENCY", 5)}')
            
            try:
                start_time = time.time()
                embeddings = gemini_client.get_embeddings(texts)
                total_time = time.time() - start_time
                
                if embeddings:
                    vector_dim = len(embeddings[0]) if embeddings[0] else 0
                    self.stdout.write(self.style.SUCCESS(
                        f'✅ Success: {len(embeddings)} embeddings in {total_time:.3f}s '
                        f'({total_time/count:.3f}s per text, {vector_dim}D vectors)'
                    ))
                    
                    # Calculate theoretical serial time (rough estimate)
                    estimated_serial_time = count * 0.5  # Assume ~500ms per embedding
                    speedup = estimated_serial_time / total_time if total_time > 0 else 0
                    self.stdout.write(f'📈 Estimated speedup: {speedup:.1f}x vs serial')
                else:
                    self.stdout.write(self.style.ERROR('❌ No embeddings returned'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Embedding failed: {e}'))
        
        # Restore original concurrency if it was overridden
        if concurrency and 'original_concurrency' in locals():
            settings.EMBEDDING_CONCURRENCY = original_concurrency