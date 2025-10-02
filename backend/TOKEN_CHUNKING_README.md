# Token-Aware RAG Chunking Implementation

## Overview

This implementation adds hybrid token-aware chunking to the RAG pipeline that:
- Uses spaCy for sentence segmentation (preserves sentence boundaries)
- Uses Gemini tokenizer (with tiktoken fallback) for accurate token counting
- Targets ~400 tokens per chunk with ~50 token overlap
- Maintains backward compatibility with character-based chunking

## Installation Requirements

### 1. Install Python Dependencies

From the `backend` directory:

```powershell
pip install -r requirements.txt
```

### 2. Install spaCy Language Model

```powershell
python -m spacy download en_core_web_sm
```

### 3. Verify Installation

```powershell
python manage.py shell -c "import spacy, tiktoken; print('✅ Dependencies installed successfully')"
```

## Configuration

The following settings are available in `backend/hellotutor/settings.py`:

```python
# RAG Chunking Settings
RAG_TOKEN_CHUNK_SIZE = 400          # Target tokens per chunk
RAG_TOKEN_CHUNK_OVERLAP = 50        # Overlap tokens between chunks
RAG_USE_GEMINI_TOKENIZER = True     # Try Gemini tokenizer first
RAG_SPACY_MODEL = "en_core_web_sm"  # spaCy model for sentences
RAG_USE_LEGACY_CHUNKER = False      # Fallback to character-based chunking
```

## Usage

### Normal Document Ingestion

The token-aware chunking is automatically used during document ingestion:

```python
# Existing ingestion endpoints work unchanged
POST /api/ingest/  # Uses new chunking automatically
```

### Preview Chunking (Testing)

Use the preview script to test chunking on local files:

```powershell
# Test token-aware chunking
python scripts/chunk_preview.py --file "path/to/document.pdf" --target 400 --overlap 50

# Test legacy chunking for comparison
python scripts/chunk_preview.py --file "path/to/document.pdf" --legacy
```

### Django Shell Testing

```python
python manage.py shell

# Test token-aware chunking
from api.rag_ingestion import read_document_pages, token_chunk_pages_to_chunks
pages = read_document_pages("path/to/file.pdf")
chunks = token_chunk_pages_to_chunks(pages, target_tokens=400, overlap_tokens=50)
print(f"Created {len(chunks)} chunks")

# Test tokenizer
from api.gemini_client import gemini_client
token_count = gemini_client.count_tokens("This is a test sentence.")
print(f"Token count: {token_count}")
```

## Algorithm Details

### Tokenization Strategy

1. **Primary**: Gemini API `countTokens` endpoint (uses LLM_API_KEY)
2. **Fallback**: tiktoken with `cl100k_base` encoding
3. **Last Resort**: Whitespace-based approximation

### Chunking Algorithm

1. **Sentence Segmentation**: spaCy splits text into sentences
2. **Token-Aware Grouping**: Sentences are combined until target token limit
3. **Overlap Creation**: Last N sentences from chunk i become first sentences of chunk i+1
4. **Boundary Preservation**: Never split sentences across chunks

### Edge Cases

- **Long Sentences**: If a single sentence > target tokens, it becomes its own chunk (logged as warning)
- **spaCy Unavailable**: Automatically falls back to legacy character-based chunking
- **Tokenizer Failures**: Graceful fallback chain ensures ingestion continues

## Performance Considerations

- **Sentence Segmentation**: ~2-5ms per page (spaCy model cached)
- **Token Counting**: ~50-100ms per chunk (API call or local tiktoken)
- **Memory Usage**: spaCy model uses ~50MB RAM (loaded once)

## Monitoring and Logs

The implementation provides detailed logging:

```
✅ Loaded spaCy model: en_core_web_sm
Split text into 24 sentences
Chunk 1: 387 tokens, 3 sentences
Chunk 2: 421 tokens, 4 sentences
WARNING: Single sentence exceeds target tokens (456 > 400)
✅ Created 8 token-aware chunks from 24 sentences
```

## Backward Compatibility

- **Legacy Chunking**: Available via `RAG_USE_LEGACY_CHUNKER = True`
- **Automatic Fallback**: If spaCy/tiktoken unavailable, falls back gracefully
- **Existing APIs**: No changes to document upload/ingestion endpoints
- **Chunk Metadata**: Same format as before (page_number preserved)

## Troubleshooting

### spaCy Model Not Found
```powershell
python -m spacy download en_core_web_sm
```

### tiktoken Not Available
```powershell
pip install tiktoken
```

### Force Legacy Chunking
Set in `settings.py`:
```python
RAG_USE_LEGACY_CHUNKER = True
```

### Check Tokenizer Status
```python
python manage.py shell -c "from api.gemini_client import gemini_client; print('Tokenizer available:', hasattr(gemini_client, 'count_tokens'))"
```

## Testing Examples

### Basic Functionality Test
```powershell
python scripts/chunk_preview.py --file "sample.pdf"
```

### Chunk Size Tuning
```powershell
python scripts/chunk_preview.py --file "sample.pdf" --target 300 --overlap 30
```

### Compare with Legacy
```powershell
# New method
python scripts/chunk_preview.py --file "sample.pdf" --target 400

# Legacy method  
python scripts/chunk_preview.py --file "sample.pdf" --legacy
```

## Migration Path

1. **Phase 1**: Install dependencies and test with preview script
2. **Phase 2**: Enable token-aware chunking in development
3. **Phase 3**: Monitor chunk quality and adjust `RAG_TOKEN_CHUNK_SIZE`
4. **Phase 4**: Deploy to production with fallback enabled
5. **Phase 5**: Remove legacy chunking after validation

The implementation ensures zero downtime during migration with automatic fallbacks.