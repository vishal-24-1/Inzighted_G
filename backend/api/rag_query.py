from django.conf import settings
from .auth import get_tenant_tag
from .rag_ingestion import initialize_pinecone, get_embedding_client
from .gemini_client import gemini_client

def query_rag(user_id: str, query: str, top_k: int = 5) -> str:
    """
    Queries the RAG system for a given user and query.
    """
    print(f"Starting RAG query for user {user_id}...")

    # 1. Get tenant tag (namespace)
    tenant_tag = get_tenant_tag(user_id)
    print(f"Generated tenant tag: {tenant_tag}")

    # 2. Initialize models and index
    try:
        embedding_client = get_embedding_client()
        index = initialize_pinecone()
        print("Initialized embedding client and Pinecone index.")
    except Exception as e:
        print(f"Error initializing embedding client or Pinecone: {e}")
        return "Error: Could not initialize backend services."

    # 3. Embed the query
    try:
        print("Embedding query...")
        query_embeddings = embedding_client.get_embeddings([query])
        query_embedding = query_embeddings[0]
        print("Embedding complete.")
    except Exception as e:
        print(f"Error encoding query: {e}")
        return "Error: Could not process your query."

    # 4. Retrieve from Pinecone using namespace with strict tenant filtering
    try:
        print(f"Querying Pinecone namespace {tenant_tag} with top_k={top_k}...")
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=tenant_tag,  # Primary isolation via namespaces
            include_metadata=True,
            filter={"tenant_tag": {"$eq": tenant_tag}}  # Additional metadata filter for defense-in-depth
        )
        print("Pinecone query complete.")
    except Exception as e:
        print(f"Error querying Pinecone: {e}")
        return "Error: Could not retrieve relevant documents."

    # 5. Normalize matches across Pinecone client versions
    context_items = []

    # results may be a dict-like or an object with .matches; handle both
    raw_matches = None
    if isinstance(results, dict):
        raw_matches = results.get('matches') or []
    else:
        # object returned by newer client
        raw_matches = getattr(results, 'matches', []) or []

    # Debug print to help trace retrieval issues
    print(f"Retrieved {len(raw_matches)} raw matches from Pinecone")

    # Helper to extract metadata from different match shapes
    def _get_match_metadata(m):
        if isinstance(m, dict):
            return m.get('metadata', {}), m.get('id')
        else:
            # pinecone client object
            meta = getattr(m, 'metadata', None)
            mid = getattr(m, 'id', None)
            return meta or {}, mid

    # Collect context from matches with strict tenant verification
    for m in raw_matches:
        md, mid = _get_match_metadata(m)
        print(f" - match id={mid} metadata_keys={list(md.keys())}")

        # CRITICAL: Verify tenant_tag in metadata matches current user
        match_tenant_tag = md.get('tenant_tag')
        if match_tenant_tag != tenant_tag:
            print(f"WARNING: Skipping cross-tenant match! Expected {tenant_tag}, got {match_tenant_tag}")
            continue

        chunk_text = md.get('text', '').strip()
        chunk_index = md.get('chunk_index')
        source_id = md.get('source_doc_id')
        if chunk_text and source_id is not None and chunk_index is not None:
            context_items.append((source_id, chunk_index, chunk_text))

    if not context_items:
        # Strong safeguard: don't call LLM if we don't have any retrieved context
        print("No relevant context found (or metadata missing). Skipping LLM call.")
        return "I could not find any relevant information in your documents to answer this question."

    # Build a strict context prompt that forces the LLM to only use provided context
    context = "\n".join([f"[{sid}#{ci}] {txt}" for sid, ci, txt in context_items])

    prompt_template = (
        "You are a helpful assistant that MUST answer using ONLY the provided context.\n"
        "Do NOT use any external knowledge or make assumptions beyond the context.\n"
        "If the answer cannot be found in the context, respond exactly: 'I don't know based on the provided documents.'\n"
        "Provide concise answers and include citations in the form [source_doc_id:chunk_index] for any facts drawn from the context.\n\n"
        "CONTEXT:\n{context}\n\n"
        "QUESTION:\n{query}\n\n"
        "Answer now."
    )

    augmented_prompt = prompt_template.format(context=context.strip(), query=query)

    # 6. Call Gemini LLM
    try:
        print("Calling Gemini LLM...")
        if not gemini_client.is_available():
            return "Error: Gemini LLM client is not available. Please check your LLM_API_KEY configuration."
        
        llm_response = gemini_client.generate_response(augmented_prompt, max_tokens=1000)
        print("Gemini LLM response received.")
        return llm_response
        
    except Exception as e:
        print(f"Error calling Gemini LLM: {e}")
        return f"Error: Failed to get response from AI model - {str(e)}"
