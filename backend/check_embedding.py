import os
import sys
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellotutor.settings')
django.setup()

from api.gemini_client import gemini_client

# Test Gemini embedding API
try:
    embeddings = gemini_client.get_embeddings(["Hello world"])
    v = embeddings[0]
    length = len(v)
    print("embedding length:", length)
    print("embedding (first 8 values):", v[:8])
    print("✅ Gemini embedding API working correctly!")
except Exception as e:
    print(f"❌ Error testing Gemini embedding: {e}")
    print("\n📝 Make sure to set EMBEDDING_API_KEY in your .env file:")
    print("EMBEDDING_API_KEY=your_gemini_api_key_here")