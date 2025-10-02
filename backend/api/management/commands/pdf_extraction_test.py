from django.core.management.base import BaseCommand
from api.rag_ingestion import read_document_pages, read_pdf_pages_hybrid, read_pdf_pages, HAS_OCR


class Command(BaseCommand):
    help = 'Test PDF extraction methods and compare results'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Path to PDF file')
        parser.add_argument('--method', type=str, default='auto', 
                          choices=['auto', 'legacy', 'hybrid'], 
                          help='Extraction method to use')
        parser.add_argument('--verbose', action='store_true', help='Show detailed output')

    def handle(self, *args, **options):
        file_path = options['file']
        method = options['method']
        verbose = options['verbose']

        self.stdout.write(self.style.SUCCESS(f'Testing PDF extraction for: {file_path}'))
        self.stdout.write(f'OCR dependencies available: {HAS_OCR}')
        self.stdout.write('')

        if method == 'auto':
            self.stdout.write(self.style.HTTP_INFO('=== Auto Method (read_document_pages) ==='))
            try:
                pages = read_document_pages(file_path)
                self._show_results(pages, verbose)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Auto method failed: {e}'))

        elif method == 'legacy':
            self.stdout.write(self.style.HTTP_INFO('=== Legacy Method (read_pdf_pages) ==='))
            try:
                pages = read_pdf_pages(file_path)
                self._show_results(pages, verbose)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Legacy method failed: {e}'))

        elif method == 'hybrid':
            if not HAS_OCR:
                self.stdout.write(self.style.WARNING('OCR dependencies not available, hybrid method may not work optimally'))
            
            self.stdout.write(self.style.HTTP_INFO('=== Hybrid Method (read_pdf_pages_hybrid) ==='))
            try:
                pages = read_pdf_pages_hybrid(file_path)
                self._show_results(pages, verbose)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Hybrid method failed: {e}'))

    def _show_results(self, pages, verbose=False):
        """Display extraction results"""
        total_chars = sum(len(page) for page in pages)
        
        self.stdout.write(f'Extracted {len(pages)} pages, {total_chars} total characters')
        self.stdout.write('')
        
        for i, page in enumerate(pages, 1):
            chars = len(page)
            preview = page[:200].replace('\n', ' ').strip()
            if len(page) > 200:
                preview += '...'
            
            self.stdout.write(f'Page {i}: {chars} chars')
            if verbose:
                self.stdout.write(f'  Preview: {preview}')
                self.stdout.write('')