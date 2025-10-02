from django.core.management.base import BaseCommand
from api.rag_ingestion import read_document_pages, token_chunk_pages_to_chunks


class Command(BaseCommand):
    help = 'Preview token-aware chunking for a local document file'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Path to local document (pdf/docx/txt)')
        parser.add_argument('--target', type=int, default=None, help='Target tokens per chunk (overrides settings)')
        parser.add_argument('--overlap', type=int, default=None, help='Overlap tokens per chunk (overrides settings)')

    def handle(self, *args, **options):
        file_path = options['file']
        target = options['target']
        overlap = options['overlap']

        pages = read_document_pages(file_path)
        if not pages:
            self.stdout.write(self.style.ERROR('No pages extracted from file.'))
            return

        chunks_with_pages = token_chunk_pages_to_chunks(pages, target_tokens=target, overlap_tokens=overlap)
        self.stdout.write(self.style.SUCCESS(f'Created {len(chunks_with_pages)} chunks'))
        for i, (chunk, page) in enumerate(chunks_with_pages[:20], start=1):
            self.stdout.write(f'Chunk {i} (page {page}): {len(chunk.split())} words | preview: {chunk[:200]!s}...')
