#!/usr/bin/env python
"""
Chunk Preview Script - Test token-aware chunking on local files

Usage:
    python scripts/chunk_preview.py --file "path/to/document.pdf" --target 400 --overlap 50
    python scripts/chunk_preview.py --file "path/to/document.pdf" --legacy

This script allows you to test the new token-aware chunking pipeline without
running the full ingestion process. It shows chunk statistics and previews.
"""

import os
import sys
import argparse
import django

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellotutor.settings')
django.setup()

from api.rag_ingestion import (
    read_document_pages, 
    chunk_pages_to_chunks, 
    token_chunk_pages_to_chunks,
    HAS_SPACY
)
from api.gemini_client import gemini_client

def preview_chunks(file_path, target_tokens=400, overlap_tokens=50, use_legacy=False):
    """
    Preview chunking behavior for a given file.
    """
    print(f"📄 Processing file: {os.path.basename(file_path)}")
    print(f"📍 Full path: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        return
    
    try:
        # Read document pages
        print("\n📖 Reading document pages...")
        pages = read_document_pages(file_path)
        
        if not pages:
            print("❌ No pages found or document could not be read")
            return
        
        print(f"✅ Read {len(pages)} pages")
        for i, page in enumerate(pages[:3], 1):  # Show first 3 pages
            print(f"   Page {i}: {len(page)} characters")
        
        if len(pages) > 3:
            print(f"   ... and {len(pages) - 3} more pages")
        
        # Choose chunking method
        if use_legacy or not HAS_SPACY:
            if not HAS_SPACY:
                print("\n⚠️  spaCy not available - using legacy chunking")
            else:
                print(f"\n🔄 Using legacy character-based chunking")
            
            chunks_with_pages = chunk_pages_to_chunks(pages, chunk_size=1000, overlap=100)
            chunking_method = "Legacy (character-based)"
        else:
            print(f"\n🧠 Using token-aware chunking (target: {target_tokens}, overlap: {overlap_tokens})")
            try:
                chunks_with_pages = token_chunk_pages_to_chunks(pages, target_tokens, overlap_tokens)
                chunking_method = "Token-aware (sentence-based)"
            except Exception as e:
                print(f"❌ Token chunking failed: {e}")
                print("🔄 Falling back to legacy chunking")
                chunks_with_pages = chunk_pages_to_chunks(pages, chunk_size=1000, overlap=100)
                chunking_method = "Legacy (fallback)"
        
        if not chunks_with_pages:
            print("❌ No chunks generated")
            return
        
        # Analyze chunks
        print(f"\n📊 Chunking Results ({chunking_method}):")
        print(f"   Total chunks: {len(chunks_with_pages)}")
        
        # Calculate token counts if possible
        chunk_stats = []
        for i, (chunk_text, page_num) in enumerate(chunks_with_pages):
            try:
                if not use_legacy and HAS_SPACY:
                    token_count = gemini_client.count_tokens(chunk_text)
                else:
                    # Approximate token count for legacy chunks
                    token_count = len(chunk_text.split())
                
                chunk_stats.append({
                    'index': i,
                    'page': page_num,
                    'chars': len(chunk_text),
                    'tokens': token_count,
                    'text': chunk_text
                })
            except Exception as e:
                print(f"⚠️  Could not count tokens for chunk {i}: {e}")
                chunk_stats.append({
                    'index': i,
                    'page': page_num,
                    'chars': len(chunk_text),
                    'tokens': len(chunk_text.split()),  # Fallback
                    'text': chunk_text
                })
        
        # Statistics
        if chunk_stats:
            token_counts = [stat['tokens'] for stat in chunk_stats]
            char_counts = [stat['chars'] for stat in chunk_stats]
            
            print(f"   Token counts: min={min(token_counts)}, max={max(token_counts)}, avg={sum(token_counts)//len(token_counts)}")
            print(f"   Character counts: min={min(char_counts)}, max={max(char_counts)}, avg={sum(char_counts)//len(char_counts)}")
            
            # Check if any chunks exceed target
            if not use_legacy:
                oversized = [stat for stat in chunk_stats if stat['tokens'] > target_tokens * 1.1]  # 10% tolerance
                if oversized:
                    print(f"   ⚠️  {len(oversized)} chunks exceed target tokens by >10%")
        
        # Show chunk previews
        print(f"\n📝 Chunk Previews (first 5):")
        for i, stat in enumerate(chunk_stats[:5]):
            preview = stat['text'][:150] + "..." if len(stat['text']) > 150 else stat['text']
            preview = preview.replace('\n', ' ').replace('\r', ' ')
            print(f"   Chunk {stat['index']+1} (Page {stat['page']}, {stat['tokens']} tokens):")
            print(f"      {preview}")
            print()
        
        if len(chunk_stats) > 5:
            print(f"   ... and {len(chunk_stats) - 5} more chunks")
        
        print("✅ Chunking preview complete!")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Preview document chunking behavior")
    parser.add_argument("--file", required=True, help="Path to document file")
    parser.add_argument("--target", type=int, default=400, help="Target tokens per chunk (default: 400)")
    parser.add_argument("--overlap", type=int, default=50, help="Overlap tokens between chunks (default: 50)")
    parser.add_argument("--legacy", action="store_true", help="Use legacy character-based chunking")
    
    args = parser.parse_args()
    
    print("🔧 Token-Aware Chunking Preview Tool")
    print("="*50)
    
    preview_chunks(
        file_path=args.file,
        target_tokens=args.target,
        overlap_tokens=args.overlap,
        use_legacy=args.legacy
    )

if __name__ == "__main__":
    main()