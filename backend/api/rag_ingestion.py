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

def read_pdf_pages(file_path: str) -> list[str]:
    """
    Reads and extracts text from a PDF file, returning a list of page texts.
    Returns one string per page, preserving page boundaries.
    """
    try:
        reader = PdfReader(file_path)
        pages = []
        total_chars = 0
        
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            pages.append(page_text)
            total_chars += len(page_text)
            print(f"PDF page {i+1}: {len(page_text)} characters extracted")
        
        print(f"PDF extraction complete: {len(pages)} pages, {total_chars} total characters")
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
    For PDFs: returns actual pages. For other formats: returns single-item list.
    """
    _, extension = os.path.splitext(file_path)
    print(f"Reading document: {os.path.basename(file_path)} (type: {extension})")
    
    if extension.lower() == '.pdf':
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
    Splits a long text into smaller chunks with overlap.
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

def chunk_pages_to_chunks(pages: list[str], chunk_size: int = 1000, overlap: int = 100) -> list[tuple[str, int]]:
    """
    Converts pages to chunks with page metadata.
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
    try:
        # Extract original file extension from S3 key to preserve it for read_document
        original_filename = s3_key.split('/')[-1]
        file_extension = os.path.splitext(original_filename)[1] or '.tmp'
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        temp_file_path = temp_file.name
        temp_file.close()
        
        if not s3_storage.download_document(s3_key, temp_file_path):
            print("Error: Failed to download document from S3")
            return False
        
        print(f"Downloaded document from S3 to {temp_file_path}")
    except Exception as e:
        print(f"Error creating temporary file: {e}")
        return False

    # 3. Read and chunk the document using page-aware approach
    try:
        pages = read_document_pages(temp_file_path)
        if not pages or not any(page.strip() for page in pages):
            print("Warning: Document is empty or could not be read.")
            return False
            
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
        return False

    # 5. Embed chunks
    try:
        print("Embedding chunks...")
        embeddings = embedding_client.get_embeddings(chunks)
        print("Embedding complete.")
    except Exception as e:
        print(f"Error encoding chunks: {e}")
        return False

    # 6. Prepare vectors for upsert with page metadata
    vectors = []
    source_doc_id = s3_key.split('/')[-1]  # Use S3 key filename as source_doc_id
    for i, chunk in enumerate(chunks):
        # Find the corresponding page number for this chunk
        page_number = chunks_with_pages[i][1] if i < len(chunks_with_pages) else 1
        
        vectors.append({
            'id': f"{tenant_tag}:{source_doc_id}:{i}",  # Deterministic ID
            'values': embeddings[i], # Gemini API returns list directly
            'metadata': {
                'tenant_tag': tenant_tag,  # CRITICAL: Include tenant_tag for isolation
                'source_doc_id': source_doc_id,
                'chunk_index': i,
                'page_number': page_number,  # NEW: Include page metadata
                'text': chunk[:1000],  # Limit metadata text size for Pinecone
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
        
        vectors.append({
            'id': f"{tenant_tag}:{source_doc_id}:{i}",  # Deterministic ID
            'values': embeddings[i], # Gemini API returns list directly
            'metadata': {
                'tenant_tag': tenant_tag,  # CRITICAL: Include tenant_tag for isolation
                'source_doc_id': source_doc_id,
                'chunk_index': i,
                'page_number': page_number,  # NEW: Include page metadata
                'text': chunk[:1000],  # Limit metadata text size for Pinecone
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