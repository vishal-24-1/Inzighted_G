from django.conf import settings
from .auth import get_tenant_tag
from .rag_ingestion import initialize_pinecone, get_embedding_client
from .gemini_client import gemini_client
from .tanglish_prompts import strip_gamification_prefix
from .models import Document, TutoringQuestionBatch, ChatSession
import json
import sentry_sdk

# NOTE: The legacy batch generation helpers `generate_question_batch_for_session`
# and `generate_tutoring_question` were removed from this module in favor of
# the canonical structured question generation implemented in
# `backend/api/agent_flow.py` which uses `gemini_client.generate_questions_structured`.
#
# If you need to generate structured question batches, use the TutorAgent
# (`backend.api.agent_flow.TutorAgent`) or `gemini_client.generate_questions_structured`.
# The removal reduces duplication; tests that relied on the legacy helpers
# have been removed/updated accordingly.



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
        # No relevant context found - use LLM to generate general knowledge response
        print("No relevant context found in user documents. Using LLM general knowledge fallback.")
        
        fallback_prompt = (
            "You are a helpful educational assistant. The user has asked a question but no relevant content was found in their uploaded documents.\n"
            "Provide a helpful, educational answer based on your general knowledge. Keep the response concise and informative.\n"
            "QUESTION: {query}\n\n"
            "Provide a helpful answer:"
        )
        
        try:
            print("Calling Gemini LLM for general knowledge fallback...")
            if not gemini_client.is_available():
                return "Error: AI service is not available. Please check your configuration."
            
            fallback_response = gemini_client.generate_response(
                fallback_prompt.format(query=query), 
                max_tokens=800
            )
            
            # Add a note that this is general knowledge
            if fallback_response and not fallback_response.startswith("Error:"):
                return strip_gamification_prefix(fallback_response)
            else:
                return "I could not find any relevant information in your documents to answer this question, and I'm having trouble accessing general knowledge at the moment."
                
        except Exception as e:
            print(f"Error in LLM general knowledge fallback: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "rag_query",
                "function": "query_rag_fallback",
                "user_id": user_id,
                "query": query[:100]
            })
            return "I could not find any relevant information in your documents to answer this question."

    # Build a strict context prompt that forces the LLM to only use provided context
    context = "\n".join([f"[{sid}#{ci}] {txt}" for sid, ci, txt in context_items])

    prompt_template = (
        "You are a helpful assistant that MUST answer using ONLY the provided context below.\n"
        "CRITICAL RULES:\n"
        "- Do NOT use any external knowledge or make assumptions beyond the context.\n"
        "- If the context does NOT contain information to answer the question, you MUST respond EXACTLY with: 'NO_ANSWER_IN_CONTEXT'\n"
        "- Only provide an answer if you can directly find the information in the context.\n"
        "- Do NOT try to infer, deduce, or piece together partial information.\n"
        "- Provide concise answers with specific references to the context when available.\n\n"
        "CONTEXT:\n{context}\n\n"
        "QUESTION:\n{query}\n\n"
        "Answer now (or respond with 'NO_ANSWER_IN_CONTEXT' if the context doesn't contain the answer):"
    )

    augmented_prompt = prompt_template.format(context=context.strip(), query=query)

    # 6. Call Gemini LLM with context
    try:
        print("Calling Gemini LLM with RAG context...")
        if not gemini_client.is_available():
            return "Error: Gemini LLM client is not available. Please check your LLM_API_KEY configuration."
        
        llm_response = gemini_client.generate_response(augmented_prompt, max_tokens=1000)
        print("Gemini LLM response received.")
        print(f"LLM response: {llm_response[:200]}...")  # Debug log
        
        # Check if LLM couldn't answer from the context
        # Multiple checks for various "I don't know" patterns
        no_answer_indicators = [
            "NO_ANSWER_IN_CONTEXT",
            "I don't know based on the provided documents",
            "I don't know based on provided documents",
            "cannot be found in the context",
            "not found in the context",
            "no information in the context"
        ]
        
        response_lower = llm_response.lower()
        should_fallback = any(indicator.lower() in response_lower for indicator in no_answer_indicators)
        
        # Also fallback if response is suspiciously short or generic (likely means RAG chunks were irrelevant)
        if len(llm_response.strip()) < 30 and not should_fallback:
            print("Response too short, might be irrelevant context. Checking...")
            should_fallback = True
        
        if should_fallback:
            print("LLM couldn't answer from RAG context (detected no-answer indicator). Falling back to general knowledge...")
            
            # Use general knowledge fallback
            fallback_prompt = (
                "You are a helpful educational assistant. The user has asked a question but the specific content in their documents doesn't contain the answer.\n"
                "Provide a helpful, educational answer based on your general knowledge. Keep the response concise and informative.\n"
                "QUESTION: {query}\n\n"
                "Provide a helpful answer:"
            )
            
            try:
                fallback_response = gemini_client.generate_response(
                    fallback_prompt.format(query=query), 
                    max_tokens=800
                )
                
                if fallback_response and not fallback_response.startswith("Error:"):
                    print("General knowledge fallback successful.")
                    return strip_gamification_prefix(fallback_response)
                else:
                    return strip_gamification_prefix(llm_response)  # Return original "I don't know" response
                    
            except Exception as fb_error:
                print(f"Error in general knowledge fallback: {fb_error}")
                return llm_response  # Return original response
        
        return strip_gamification_prefix(llm_response)
        
    except Exception as e:
        print(f"Error calling Gemini LLM: {e}")
        sentry_sdk.capture_exception(e, extras={
            "component": "rag_query",
            "function": "query_rag",
            "user_id": user_id,
            "query": query[:100]  # First 100 chars of query
        })
        return f"Error: Failed to get response from AI model - {str(e)}"
