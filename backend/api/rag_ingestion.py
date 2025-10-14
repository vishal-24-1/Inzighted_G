import os
import uuid
from pinecone import Pinecone, ServerlessSpec
from django.conf import settings
from .auth import get_tenant_tag
from .s3_storage import s3_storage
from .gemini_client import gemini_client
import docx
from pypdf import PdfReader
import tempfile
import sentry_sdk
import unicodedata

# Try to import pdfplumber as a fallback for better PDF text extraction
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False
    print("pdfplumber not available, using pypdf only")

# Try to import OCR dependencies for scanned PDF handling
try:
    import pdf2image
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print("OCR dependencies not available - install with: pip install pdf2image pytesseract Pillow")
    print("Note: Also requires poppler-utils and tesseract-ocr system packages")

# Try to import spaCy for sentence segmentation
try:
    import spacy
    HAS_SPACY = True
    _spacy_nlp = None  # Lazy-loaded spaCy model
except ImportError:
    HAS_SPACY = False
    print("spaCy not available - install with: pip install spacy && python -m spacy download en_core_web_sm")

# --- Initialization Functions ---

def initialize_pinecone():
    """Initializes and returns the Pinecone index."""
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index_name = settings.PINECONE_INDEX
    
    # Create index if it doesn't exist
    if not pc.has_index(index_name):
        # Allow embedding dimension to be configured via settings.EMBEDDING_DIM (default 1536)
        embedding_dim = getattr(settings, 'EMBEDDING_DIM', 1536)
        try:
            embedding_dim = int(embedding_dim)
        except Exception:
            embedding_dim = 1536

        pc.create_index(
            name=index_name,
            vector_type="dense",
            dimension=embedding_dim,
            metric='cosine',
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            ),
            deletion_protection="disabled",
            tags={"environment": settings.ENV, "model": "gemini-embedding-001"}
        )
    
    return pc.Index(index_name)

def get_embedding_client():
    """Returns the Gemini embedding client."""
    return gemini_client

# --- Document Reading Functions ---

def read_pdf(file_path: str) -> str:
    """Reads and extracts text from a PDF file (legacy method)."""
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def read_pdf_pages_hybrid(file_path: str) -> list[str]:
    """
    Robust PDF text extraction with OCR fallback for scanned pages.
    
    Strategy:
    1. Try multiple pypdf extraction modes
    2. Fall back to pdfplumber if available
    3. For minimal text pages, use OCR (pdf2image + pytesseract)
    4. Handle errors gracefully and continue with other pages
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        List of page texts (one string per page)
    """
    try:
        reader = PdfReader(file_path)
        pages = []
        total_chars = 0
        ocr_pages_count = 0
        
        print(f"Starting hybrid PDF extraction for {len(reader.pages)} pages...")
        
        for i, page in enumerate(reader.pages):
            page_number = i + 1
            page_text = ""
            used_ocr = False
            
            # Step 1: Try multiple pypdf extraction strategies
            try:
                # Strategy 1: Standard extraction
                page_text = page.extract_text() or ""
                extraction_method = "pypdf-standard"
                
                # Strategy 2: If text is minimal, try layout mode
                if len(page_text.strip()) < 30:
                    try:
                        layout_text = page.extract_text(extraction_mode="layout", space_width=200) or ""
                        if len(layout_text.strip()) > len(page_text.strip()):
                            page_text = layout_text
                            extraction_method = "pypdf-layout"
                    except Exception:
                        pass
                
                # Strategy 3: If still minimal, try plain mode
                if len(page_text.strip()) < 30:
                    try:
                        plain_text = page.extract_text(extraction_mode="plain") or ""
                        if len(plain_text.strip()) > len(page_text.strip()):
                            page_text = plain_text
                            extraction_method = "pypdf-plain"
                    except Exception:
                        pass
                
            except Exception as e:
                print(f"Page {page_number}: pypdf extraction failed: {e}")
                page_text = ""
                extraction_method = "pypdf-failed"
            
            # Step 2: Try pdfplumber if text is still minimal
            if len(page_text.strip()) < 30 and HAS_PDFPLUMBER:
                try:
                    with pdfplumber.open(file_path) as pdf:
                        if i < len(pdf.pages):
                            plumber_text = pdf.pages[i].extract_text() or ""
                            if len(plumber_text.strip()) > len(page_text.strip()):
                                page_text = plumber_text
                                extraction_method = "pdfplumber"
                except Exception as e:
                    print(f"Page {page_number}: pdfplumber extraction failed: {e}")
            
            # Step 3: OCR fallback for minimal text pages
            minimal_threshold = getattr(settings, 'PDF_OCR_THRESHOLD', 50)
            if len(page_text.strip()) < minimal_threshold and HAS_OCR:
                try:
                    print(f"Page {page_number}: Text minimal ({len(page_text.strip())} chars), applying OCR...")
                    
                    # Convert PDF page to image
                    dpi = getattr(settings, 'PDF_OCR_DPI', 300)
                    images = pdf2image.convert_from_path(
                        file_path,
                        first_page=page_number,
                        last_page=page_number,
                        dpi=dpi,
                        fmt='PNG'
                    )
                    
                    if images:
                        # Extract text using OCR
                        ocr_config = getattr(settings, 'TESSERACT_CONFIG', '--psm 1 --oem 3')
                        ocr_text = pytesseract.image_to_string(images[0], config=ocr_config).strip()
                        
                        if len(ocr_text) > len(page_text.strip()):
                            page_text = ocr_text
                            extraction_method = "ocr"
                            used_ocr = True
                            ocr_pages_count += 1
                            print(f"Page {page_number}: OCR extracted {len(ocr_text)} characters")
                        else:
                            print(f"Page {page_number}: OCR didn't improve text quality")
                    
                except Exception as e:
                    print(f"Page {page_number}: OCR extraction failed: {e}")
                    # Continue with whatever text we have
            
            # Clean up and finalize page text
            page_text = page_text.strip()
            
            # Mark pages with minimal content
            if len(page_text) < 30:
                page_text = f"[Page {page_number} content minimal - {extraction_method}] " + page_text
                print(f"Page {page_number}: Minimal content ({len(page_text)} chars) using {extraction_method}")
            else:
                print(f"Page {page_number}: {len(page_text)} chars extracted using {extraction_method}" + 
                      (" (OCR)" if used_ocr else ""))
            
            pages.append(page_text)
            total_chars += len(page_text)
        
        print(f"✅ Hybrid PDF extraction complete:")
        print(f"   - {len(pages)} pages processed")
        print(f"   - {total_chars} total characters")
        print(f"   - {ocr_pages_count} pages used OCR fallback")
        
        # Overall quality warning
        if total_chars < 500:
            print(f"⚠️  WARNING: Very little text extracted ({total_chars} chars)")
            print("   This may be a heavily scanned PDF or have extraction issues")
        
        return pages
        
    except Exception as e:
        print(f"❌ Critical error in PDF extraction: {e}")
        return []

def read_pdf_pages(file_path: str) -> list[str]:
    """
    LEGACY: Reads and extracts text from a PDF file, returning a list of page texts.
    Returns one string per page, preserving page boundaries.
    Uses improved extraction strategies for better text capture.
    
    NOTE: This function is kept for backward compatibility.
    New code should use read_pdf_pages_hybrid() for better OCR support.
    """
    try:
        reader = PdfReader(file_path)
        pages = []
        total_chars = 0
        
        for i, page in enumerate(reader.pages):
            # Try multiple extraction strategies
            page_text = ""
            
            # Strategy 1: Standard extraction
            try:
                page_text = page.extract_text() or ""
            except Exception as e:
                print(f"Standard extraction failed for page {i+1}: {e}")
            
            # Strategy 2: If text is too short, try with different options
            if len(page_text.strip()) < 50:
                try:
                    # Try with layout mode and space width
                    page_text = page.extract_text(extraction_mode="layout", space_width=200) or ""
                except Exception:
                    pass
            
            # Strategy 3: If still poor, try plain extraction mode
            if len(page_text.strip()) < 50:
                try:
                    page_text = page.extract_text(extraction_mode="plain") or ""
                except Exception:
                    pass
                    
            # Strategy 4: Try pdfplumber as fallback if available and extraction is poor
            if len(page_text.strip()) < 50 and HAS_PDFPLUMBER:
                try:
                    with pdfplumber.open(file_path) as pdf:
                        if i < len(pdf.pages):
                            plumber_text = pdf.pages[i].extract_text() or ""
                            if len(plumber_text.strip()) > len(page_text.strip()):
                                page_text = plumber_text
                                print(f"Page {i+1}: Used pdfplumber fallback")
                except Exception as e:
                    print(f"pdfplumber fallback failed for page {i+1}: {e}")
            
            # Clean up the text
            page_text = page_text.strip()
            
            # Filter out pages with only minimal content (likely headers/footers only)
            if len(page_text) < 30:
                print(f"PDF page {i+1}: {len(page_text)} characters extracted (possibly header/footer only)")
                # Still include it but mark as minimal
                page_text = f"[Page {i+1} content minimal] " + page_text
            else:
                print(f"PDF page {i+1}: {len(page_text)} characters extracted")
            
            pages.append(page_text)
            total_chars += len(page_text)
        
        print(f"PDF extraction complete: {len(pages)} pages, {total_chars} total characters")
        
        # If total extraction is very poor, log warning
        if total_chars < 500:
            print(f"WARNING: PDF extraction yielded very little text ({total_chars} chars). This may be a scanned PDF or have extraction issues.")
        
        return pages
    except Exception as e:
        print(f"Error reading PDF pages: {e}")
        return []

def read_docx(file_path: str) -> str:
    """Reads and extracts text from a DOCX file."""
    doc = docx.Document(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def read_document(file_path: str) -> str:
    """
    Reads a document, automatically detecting the file type (legacy method).
    """
    _, extension = os.path.splitext(file_path)
    if extension.lower() == '.pdf':
        return read_pdf(file_path)
    elif extension.lower() == '.docx':
        return read_docx(file_path)
    elif extension.lower() == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported file type: {extension}")

def read_document_pages(file_path: str) -> list[str]:
    """
    Reads a document and returns pages as a list of strings.
    For PDFs: returns actual pages using hybrid extraction (with OCR fallback).
    For other formats: returns single-item list.
    """
    _, extension = os.path.splitext(file_path)
    print(f"Reading document: {os.path.basename(file_path)} (type: {extension})")
    
    if extension.lower() == '.pdf':
        # Use hybrid extraction by default, fallback to legacy if OCR not available
        use_hybrid = getattr(settings, 'PDF_USE_HYBRID_EXTRACTION', True)
        
        if use_hybrid and HAS_OCR:
            print("Using hybrid PDF extraction (with OCR fallback)")
            return read_pdf_pages_hybrid(file_path)
        else:
            if not HAS_OCR:
                print("OCR dependencies not available, using legacy PDF extraction")
            else:
                print("Using legacy PDF extraction (hybrid disabled)")
            return read_pdf_pages(file_path)
    elif extension.lower() == '.docx':
        text = read_docx(file_path)
        print(f"DOCX extracted: {len(text)} characters")
        return [text] if text.strip() else []
    elif extension.lower() == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"TXT read: {len(text)} characters")
        return [text] if text.strip() else []
    else:
        raise ValueError(f"Unsupported file type: {extension}")

# --- Text Chunking Function ---

def chunk_text(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """
    LEGACY: Splits a long text into smaller chunks with overlap.
    (A simple implementation based on character count, not tokens)
    """
    if not isinstance(text, str):
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def clean_text_for_upsert(s: str, max_len: int = 1000) -> str:
    """
    Clean text to be safely included in JSON metadata for Pinecone upserts.

    - Normalize to NFC
    - Remove unpaired surrogate codepoints (0xD800-0xDFFF)
    - Remove control characters except tab/newline/carriage-return
    - Encode/decode with 'replace' to ensure valid UTF-8
    - Truncate to max_len
    """
    if not s:
        return ""

    try:
        s = unicodedata.normalize('NFC', s)
    except Exception:
        # If normalization fails, fall back to original
        pass

    filtered_chars = []
    for ch in s:
        cp = ord(ch)
        # Skip surrogate codepoints
        if 0xD800 <= cp <= 0xDFFF:
            continue
        # Remove control characters except newline/tab/carriage return
        if cp < 32 and ch not in ('\n', '\r', '\t'):
            continue
        filtered_chars.append(ch)

    safe = ''.join(filtered_chars)

    # Ensure valid UTF-8 by replace-on-encode, then truncate
    try:
        safe = safe.encode('utf-8', 'replace').decode('utf-8', 'replace')
    except Exception:
        # Last-resort fallback: remove any non-ASCII
        safe = ''.join(ch for ch in safe if ord(ch) < 128)

    return safe[:max_len]

def chunk_pages_to_chunks(pages: list[str], chunk_size: int = 1000, overlap: int = 100) -> list[tuple[str, int]]:
    """
    LEGACY: Converts pages to chunks with page metadata.
    Returns list of (chunk_text, page_number) tuples.
    
    Strategy: Each non-empty page gets at least one chunk. Long pages are split further.
    """
    chunks_with_pages = []
    
    for page_idx, page_text in enumerate(pages):
        page_number = page_idx + 1  # 1-indexed page numbers
        
        if not page_text.strip():
            print(f"Page {page_number}: empty, skipping")
            continue
            
        # If page fits in chunk_size, use whole page as one chunk
        if len(page_text) <= chunk_size:
            chunks_with_pages.append((page_text.strip(), page_number))
            print(f"Page {page_number}: single chunk ({len(page_text)} chars)")
        else:
            # Split long page into multiple chunks
            start = 0
            chunk_count = 0
            while start < len(page_text):
                end = start + chunk_size
                chunk = page_text[start:end].strip()
                if chunk:  # Only add non-empty chunks
                    chunks_with_pages.append((chunk, page_number))
                    chunk_count += 1
                start += chunk_size - overlap
            print(f"Page {page_number}: split into {chunk_count} chunks ({len(page_text)} chars)")
    
    print(f"Total chunks created: {len(chunks_with_pages)}")
    return chunks_with_pages

# --- New Token-Aware Chunking Functions ---

def get_spacy_nlp():
    """
    Lazy-load spaCy model for sentence segmentation.
    Only loads components needed for sentence boundary detection.
    """
    global _spacy_nlp
    if _spacy_nlp is None:
        if not HAS_SPACY:
            raise ImportError("spaCy not available. Install with: pip install spacy && python -m spacy download en_core_web_sm")
        
        model_name = getattr(settings, 'RAG_SPACY_MODEL', 'en_core_web_sm')
        try:
            # Only load sentence boundary detector to save memory
            _spacy_nlp = spacy.load(model_name, disable=["ner", "tagger", "parser", "lemmatizer"])
            # Ensure a lightweight sentencizer is present so doc.sents works even when parser is disabled
            if "sentencizer" not in _spacy_nlp.pipe_names:
                try:
                    _spacy_nlp.add_pipe("sentencizer")
                    print(f"✅ Added sentencizer to spaCy pipeline for model: {model_name}")
                except Exception:
                    print(f"Warning: could not add sentencizer to spaCy model: {model_name}")
            else:
                print(f"✅ Loaded spaCy model: {model_name} (sentencizer present)")
        except OSError:
            raise ImportError(f"spaCy model '{model_name}' not found. Install with: python -m spacy download {model_name}")
    
    return _spacy_nlp

def sentencize_text(text: str) -> list[str]:
    """
    Split text into sentences using spaCy sentence segmentation.
    
    Args:
        text: Input text to split into sentences
        
    Returns:
        List of sentence strings (stripped of whitespace)
    """
    if not text.strip():
        return []
    
    nlp = get_spacy_nlp()
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    
    print(f"Split text into {len(sentences)} sentences")
    return sentences

def hybrid_chunk_sentences(sentences: list[str], tokenizer_func, target_tokens: int, overlap_tokens: int) -> list[str]:
    """
    Create chunks from sentences using token-aware boundaries with overlap.
    
    Args:
        sentences: List of sentence strings
        tokenizer_func: Function that takes a text string and returns token count
        target_tokens: Target number of tokens per chunk
        overlap_tokens: Number of tokens to overlap between chunks
        
    Returns:
        List of chunk strings (joined sentences)
    """
    if not sentences:
        return []
    
    chunks = []
    current_chunk_sentences = []
    current_chunk_tokens = 0
    
    for sentence in sentences:
        sentence_tokens = tokenizer_func(sentence)
        
        # Check if adding this sentence would exceed target
        if current_chunk_sentences and (current_chunk_tokens + sentence_tokens > target_tokens):
            # Finalize current chunk
            chunk_text = " ".join(current_chunk_sentences)
            chunks.append(chunk_text)
            print(f"Chunk {len(chunks)}: {current_chunk_tokens} tokens, {len(current_chunk_sentences)} sentences")
            
            # Create overlap for next chunk
            overlap_sentences = []
            overlap_token_count = 0
            
            # Add sentences from the end of current chunk until we reach overlap target
            for i in range(len(current_chunk_sentences) - 1, -1, -1):
                sent = current_chunk_sentences[i]
                sent_tokens = tokenizer_func(sent)
                if overlap_token_count + sent_tokens <= overlap_tokens:
                    overlap_sentences.insert(0, sent)
                    overlap_token_count += sent_tokens
                else:
                    break
            
            # Start next chunk with overlap sentences
            current_chunk_sentences = overlap_sentences[:]
            current_chunk_tokens = overlap_token_count
        
        # Add current sentence to chunk
        current_chunk_sentences.append(sentence)
        current_chunk_tokens += sentence_tokens
        
        # Handle edge case: single sentence longer than target
        if len(current_chunk_sentences) == 1 and sentence_tokens > target_tokens:
            print(f"WARNING: Single sentence exceeds target tokens ({sentence_tokens} > {target_tokens})")
            # Allow it as its own chunk
            chunk_text = sentence
            chunks.append(chunk_text)
            print(f"Chunk {len(chunks)}: {sentence_tokens} tokens (oversized), 1 sentence")
            current_chunk_sentences = []
            current_chunk_tokens = 0
    
    # Add final chunk if any sentences remain
    if current_chunk_sentences:
        chunk_text = " ".join(current_chunk_sentences)
        chunks.append(chunk_text)
        print(f"Chunk {len(chunks)} (final): {current_chunk_tokens} tokens, {len(current_chunk_sentences)} sentences")
    
    print(f"✅ Created {len(chunks)} token-aware chunks from {len(sentences)} sentences")
    return chunks

def token_chunk_pages_to_chunks(pages: list[str], target_tokens: int = None, overlap_tokens: int = None) -> list[tuple[str, int]]:
    """
    Convert pages to token-aware chunks with sentence boundaries and page metadata.
    
    Args:
        pages: List of page text strings
        target_tokens: Target tokens per chunk (from settings if None)
        overlap_tokens: Overlap tokens between chunks (from settings if None)
        
    Returns:
        List of (chunk_text, page_number) tuples
    """
    if target_tokens is None:
        target_tokens = getattr(settings, 'RAG_TOKEN_CHUNK_SIZE', 400)
    if overlap_tokens is None:
        overlap_tokens = getattr(settings, 'RAG_TOKEN_CHUNK_OVERLAP', 50)
    
    print(f"Token chunking: target={target_tokens}, overlap={overlap_tokens}")
    
    # Create tokenizer function from gemini_client
    def tokenizer_func(text: str) -> int:
        return gemini_client.count_tokens(text)
    
    chunks_with_pages = []
    
    for page_idx, page_text in enumerate(pages):
        page_number = page_idx + 1
        
        if not page_text.strip():
            print(f"Page {page_number}: empty, skipping")
            continue
        
        # Split page into sentences
        sentences = sentencize_text(page_text)
        if not sentences:
            print(f"Page {page_number}: no sentences found, skipping")
            continue
        
        # Create token-aware chunks from sentences
        page_chunks = hybrid_chunk_sentences(sentences, tokenizer_func, target_tokens, overlap_tokens)
        
        # Add page metadata to chunks
        for chunk_text in page_chunks:
            chunks_with_pages.append((chunk_text, page_number))
        
        print(f"Page {page_number}: {len(sentences)} sentences -> {len(page_chunks)} chunks")
    
    print(f"✅ Token chunking complete: {len(chunks_with_pages)} chunks from {len(pages)} pages")
    return chunks_with_pages

# --- Main Ingestion Pipeline ---

def ingest_document_from_s3(s3_key: str, user_id: str):
    """
    Downloads document from S3, processes, chunks, embeds, and upserts into Pinecone.
    """
    print(f"Starting S3 ingestion for user {user_id}, S3 key {s3_key}...")

    # 1. Get tenant tag (namespace)
    tenant_tag = get_tenant_tag(user_id)
    print(f"Generated tenant tag: {tenant_tag}")

    # 2. Download document from S3 to temporary file
    temp_file = None
    temp_file_path = None
    try:
        # Extract original file extension from S3 key to preserve it for read_document
        original_filename = s3_key.split('/')[-1]
        file_extension = os.path.splitext(original_filename)[1] or '.tmp'
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        temp_file_path = temp_file.name
        temp_file.close()
        
        if not s3_storage.download_document(s3_key, temp_file_path):
            print("Error: Failed to download document from S3")
            sentry_sdk.capture_message(
                "Failed to download document from S3",
                level="error",
                extras={
                    "component": "rag_ingestion",
                    "s3_key": s3_key,
                    "user_id": user_id
                }
            )
            return False
        
        print(f"Downloaded document from S3 to {temp_file_path}")
    except Exception as e:
        print(f"Error creating temporary file: {e}")
        sentry_sdk.capture_exception(e, extras={
            "component": "rag_ingestion",
            "function": "ingest_document_from_s3",
            "s3_key": s3_key,
            "user_id": user_id
        })
        return False

    # 3. Read and chunk the document using page-aware approach
    try:
        pages = read_document_pages(temp_file_path)
        if not pages or not any(page.strip() for page in pages):
            print("Warning: Document is empty or could not be read.")
            return False
        
        # Use token-aware chunking by default, fallback to legacy if needed
        use_legacy = getattr(settings, 'RAG_USE_LEGACY_CHUNKER', False)
        
        if use_legacy or not HAS_SPACY:
            if not HAS_SPACY:
                print("WARNING: spaCy not available, using legacy character-based chunking")
            print("Using legacy character-based chunking")
            chunks_with_pages = chunk_pages_to_chunks(pages, chunk_size=1000, overlap=100)
        else:
            print("Using token-aware sentence-based chunking")
            try:
                chunks_with_pages = token_chunk_pages_to_chunks(
                    pages,
                    target_tokens=getattr(settings, 'RAG_TOKEN_CHUNK_SIZE', 400),
                    overlap_tokens=getattr(settings, 'RAG_TOKEN_CHUNK_OVERLAP', 50)
                )
            except Exception as e:
                print(f"Token chunking failed, falling back to legacy: {e}")
                chunks_with_pages = chunk_pages_to_chunks(pages, chunk_size=1000, overlap=100)
        
        if not chunks_with_pages:
            print("Warning: No chunks generated from document.")
            return False
            
        chunks = [chunk_text for chunk_text, page_num in chunks_with_pages]
        print(f"Document processed: {len(pages)} pages -> {len(chunks)} chunks")
        
        # Log a preview of the first chunk
        if chunks:
            preview = chunks[0][:200] + "..." if len(chunks[0]) > 200 else chunks[0]
            print(f"First chunk preview: {preview}")
            
    except Exception as e:
        print(f"Error reading or chunking document: {e}")
        sentry_sdk.capture_exception(e, extras={
            "component": "rag_ingestion",
            "function": "ingest_document_from_s3",
            "stage": "document_reading_chunking",
            "s3_key": s3_key,
            "user_id": user_id
        })
        return False
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    # 4. Initialize models and index
    try:
        embedding_client = get_embedding_client()
        index = initialize_pinecone()
        print("Initialized embedding client and Pinecone index.")
    except Exception as e:
        print(f"Error initializing embedding client or Pinecone: {e}")
        sentry_sdk.capture_exception(e, extras={
            "component": "rag_ingestion",
            "function": "ingest_document_from_s3",
            "stage": "initialization",
            "s3_key": s3_key,
            "user_id": user_id
        })
        return False

    # 5. Embed chunks
    try:
        print("Embedding chunks...")
        embeddings = embedding_client.get_embeddings(chunks)
        print("Embedding complete.")
    except Exception as e:
        print(f"Error encoding chunks: {e}")
        sentry_sdk.capture_exception(e, extras={
            "component": "rag_ingestion",
            "function": "ingest_document_from_s3",
            "stage": "embedding",
            "s3_key": s3_key,
            "user_id": user_id,
            "chunks_count": len(chunks)
        })
        return False

    # 6. Prepare vectors for upsert with page metadata
    vectors = []
    source_doc_id = s3_key.split('/')[-1]  # Use S3 key filename as source_doc_id
    for i, chunk in enumerate(chunks):
        # Find the corresponding page number for this chunk
        page_number = chunks_with_pages[i][1] if i < len(chunks_with_pages) else 1
        
        safe_text = clean_text_for_upsert(chunk, max_len=1000)
        vectors.append({
            'id': f"{tenant_tag}:{source_doc_id}:{i}",  # Deterministic ID
            'values': embeddings[i], # Gemini API returns list directly
            'metadata': {
                'tenant_tag': tenant_tag,  # CRITICAL: Include tenant_tag for isolation
                'source_doc_id': source_doc_id,
                'chunk_index': i,
                'page_number': page_number,  # NEW: Include page metadata
                'text': safe_text,  # Cleaned metadata text for Pinecone
                's3_key': s3_key
            }
        })

    # 7. Upsert to Pinecone using namespace
    try:
        print(f"Upserting {len(vectors)} vectors to Pinecone namespace: {tenant_tag}...")
        index.upsert(vectors=vectors, namespace=tenant_tag)
        print("Upsert complete.")
        return True
    except Exception as e:
        print(f"Error upserting to Pinecone: {e}")
        sentry_sdk.capture_exception(e, extras={
            "component": "rag_ingestion",
            "function": "ingest_document_from_s3",
            "stage": "pinecone_upsert",
            "s3_key": s3_key,
            "user_id": user_id,
            "vectors_count": len(vectors)
        })
        return False
    
def ingest_document(file_path: str, user_id: str):
    """
    Legacy function for backward compatibility - processes local file directly.
    """
    print(f"Starting ingestion for user {user_id}, file {file_path}...")

    # 1. Get tenant tag (namespace)
    tenant_tag = get_tenant_tag(user_id)
    print(f"Generated tenant tag: {tenant_tag}")

    # 2. Read and chunk the document using page-aware approach
    try:
        pages = read_document_pages(file_path)
        if not pages or not any(page.strip() for page in pages):
            print("Warning: Document is empty or could not be read.")
            return
        
        # Use token-aware chunking by default, fallback to legacy if needed
        use_legacy = getattr(settings, 'RAG_USE_LEGACY_CHUNKER', False)
        
        if use_legacy or not HAS_SPACY:
            if not HAS_SPACY:
                print("WARNING: spaCy not available, using legacy character-based chunking")
            print("Using legacy character-based chunking")
            chunks_with_pages = chunk_pages_to_chunks(pages, chunk_size=1000, overlap=100)
        else:
            print("Using token-aware sentence-based chunking")
            try:
                chunks_with_pages = token_chunk_pages_to_chunks(
                    pages,
                    target_tokens=getattr(settings, 'RAG_TOKEN_CHUNK_SIZE', 400),
                    overlap_tokens=getattr(settings, 'RAG_TOKEN_CHUNK_OVERLAP', 50)
                )
            except Exception as e:
                print(f"Token chunking failed, falling back to legacy: {e}")
                chunks_with_pages = chunk_pages_to_chunks(pages, chunk_size=1000, overlap=100)
        
        if not chunks_with_pages:
            print("Warning: No chunks generated from document.")
            return
            
        chunks = [chunk_text for chunk_text, page_num in chunks_with_pages]
        print(f"Document processed: {len(pages)} pages -> {len(chunks)} chunks")
        
        # Log a preview of the first chunk
        if chunks:
            preview = chunks[0][:200] + "..." if len(chunks[0]) > 200 else chunks[0]
            print(f"First chunk preview: {preview}")
            
    except Exception as e:
        print(f"Error reading or chunking document: {e}")
        return

    # 3. Initialize models and index
    try:
        embedding_client = get_embedding_client()
        index = initialize_pinecone()
        print("Initialized embedding client and Pinecone index.")
    except Exception as e:
        print(f"Error initializing embedding client or Pinecone: {e}")
        return

    # 4. Embed chunks
    try:
        print("Embedding chunks...")
        embeddings = embedding_client.get_embeddings(chunks)
        print("Embedding complete.")
    except Exception as e:
        print(f"Error encoding chunks: {e}")
        return

    # 5. Prepare vectors for upsert with page metadata
    vectors = []
    source_doc_id = os.path.basename(file_path)
    for i, chunk in enumerate(chunks):
        # Find the corresponding page number for this chunk
        page_number = chunks_with_pages[i][1] if i < len(chunks_with_pages) else 1
        
        safe_text = clean_text_for_upsert(chunk, max_len=1000)
        vectors.append({
            'id': f"{tenant_tag}:{source_doc_id}:{i}",  # Deterministic ID
            'values': embeddings[i], # Gemini API returns list directly
            'metadata': {
                'tenant_tag': tenant_tag,  # CRITICAL: Include tenant_tag for isolation
                'source_doc_id': source_doc_id,
                'chunk_index': i,
                'page_number': page_number,  # NEW: Include page metadata
                'text': safe_text,  # Cleaned metadata text for Pinecone
            }
        })

    # 6. Upsert to Pinecone using namespace
    try:
        print(f"Upserting {len(vectors)} vectors to Pinecone namespace: {tenant_tag}...")
        index.upsert(vectors=vectors, namespace=tenant_tag)
        print("Upsert complete.")
    except Exception as e:
        print(f"Error upserting to Pinecone: {e}")

    print("Ingestion process finished.")