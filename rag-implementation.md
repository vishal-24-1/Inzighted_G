# Multi-Tenant RAG Implementation Guide
**Goal:** Build a secure multi-tenant RAG system using Pinecone as the vector database and Gemini Embedding-001 for embeddings. Each student can only access their own documents. The LLM should generate answers grounded in retrieved content with citations.

---

## 1. Project Overview
**Components:**
- **Ingestion Service:** Upload, sanitize, chunk, embed, and store student documents.
- **Auth Service:** Authenticate students and derive tenant_tag.
- **Query Service:** Embed queries, retrieve relevant chunks securely, generate LLM responses.
- **LLM Service:** Generate responses using only retrieved content.
- **Audit & Compliance:** Logs, deletion, and data protection.

**Security Principles:**
1. Use **HMAC-derived tenant_tag** instead of raw student_id.
2. **Server-side filtering** is mandatory; client-side filtering is prohibited.
3. Use **namespaces** in Pinecone for extra isolation (optional but recommended).
4. Track **provenance**: source_doc_id, chunk_index, offsets.
5. Use the same embedding model for ingestion and queries.

---

## 2. Environment Setup
**Environment Variables:**
PINECONE_API_KEY=...
PINECONE_INDEX=student_documents
HMAC_SECRET=...
LLM_API_KEY=...
EMBEDDING_API_KEY=...
ENV=development|staging|production

yaml
Copy code

**Dependencies:**
- Python 3.10+
- pinecone-client
- google-generativeai (for Gemini Embedding-001)
- LangChain (optional)
- Other utilities: uuid, hmac, hashlib, pandas, etc.

---

## 3. Core Workflow

### 3.1 Ingestion Pipeline
1. Accept documents from a student (PDF, DOCX, TXT, PPTX).
2. Sanitize content to remove scripts/malicious content.
3. Chunk documents into 200–500 tokens with overlap (~50 tokens).
4. For each chunk:
   - Generate embedding using Gemini Embedding-001.
   - Create metadata:
     ```
     tenant_tag (HMAC of student_id)
     source_doc_id
     chunk_index
     char_offset_start, char_offset_end
     ingested_at timestamp
     embedding_model
     ```
5. Upsert vectors into Pinecone:
   - Use namespace=f"tenant-{tenant_tag}" (optional)
   - Include metadata={"tenant_tag": tenant_tag}

---

### 3.2 Query Pipeline
1. Authenticate the student and retrieve student_id.
2. Compute tenant_tag = HMAC(student_id, HMAC_SECRET).
3. Embed the student query using Gemini Embedding-001.
4. Retrieve top_k relevant vectors from Pinecone:
   - Apply namespace=f"tenant-{tenant_tag}" (optional)
   - Apply metadata filter: tenant_tag
5. Re-rank results if necessary (BM25/lexical overlap).
6. Build augmented prompt:
"You are an assistant. Answer ONLY using the provided context.
Context:
[source_doc_id#chunk_index] <chunk_text>
Question:
<student_query>
Answer with citations (source_doc_id:chunk_index)."

yaml
Copy code
7. Call LLM with prompt and temperature 0.0–0.2.
8. Return answer with citations to the student.

---

## 4. Security & Compliance
- Never store raw student_id in vector DB.
- Use **server-side filters** to enforce tenant isolation.
- Log retrievals: tenant_tag, query hash, retrieved chunk IDs, timestamp.
- Delete tenant data using Pinecone `delete_by_filter({"tenant_tag": tenant_tag})`.
- Rotate HMAC secrets periodically.

---

## 5. Testing & Validation
1. **Cross-Tenant Isolation:** Ensure queries return only chunks belonging to the correct tenant.
2. **Deletion:** Verify tenant data can be fully removed.
3. **Grounding:** Confirm LLM answers include citations and reference only retrieved chunks.
4. **Fail-Safe:** Missing tenant_tag in metadata → chunk is ignored.

---

## 6. Agent Instructions
**When reading this Markdown, an AI agent should:**
1. Generate configuration for Pinecone, Gemini Embedding-001, and LLM.
2. Generate auth module for HMAC tenant_tag derivation.
3. Generate ingestion module (chunking, embedding, upsert) with metadata.
4. Generate query module (secure retrieval, prompt building, LLM call).
5. Include logging and deletion functionality.
6. Write automated tests for cross-tenant security, deletion, and grounding.
7. Output clear, functional Python code for each module.

---

## 7. Implementation Notes
- Use consistent embedding model (Gemini Embedding-001) for ingestion and queries.
- Keep chunk-level provenance for citations.
- Use namespaces + tenant_tag filtering for defense-in-depth.
- LLM system prompt must strictly enforce context-only responses.

---

## 8. References
- LangChain RAG tutorial: [https://www.langchain.com/docs/](https://www.langchain.com/docs/)
- Gemini Embedding API: [https://ai.google.dev/gemini-api/docs/embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- Pinecone metadata filtering & namespaces: [https://docs.pinecone.io/](https://docs.pinecone.io/)
- Prompt engineering best practices: [https://platform.openai.com/docs/guides/prompting](https://platform.openai.com/docs/guides/prompting)



pinecode index setup:

Install Pinecone
Ready to get started with Pinecone? First, install the Python SDK:

pip install pinecone
Initialize
Next, use your API key to initialize your client:

from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="********-****-****-****-************")

# Create index for vector storage (not using integrated embeddings since we use Gemini)
index_name = "student-documents"

if not pc.has_index(index_name):
    pc.create_index(
        name=index_name,
        vector_type="dense",
    dimension=1536,  # Gemini Embedding-001 dimension (updated)
        metric="cosine",  # typical for semantic search
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        ),
        deletion_protection="disabled",
        tags={"environment": "dev", "model": "gemini-embedding-001"}
    )
