from django.conf import settings
from .auth import get_tenant_tag
from .rag_ingestion import initialize_pinecone, get_embedding_client
from .gemini_client import gemini_client
from .models import Document, TutoringQuestionBatch, ChatSession
import json
import sentry_sdk

def generate_question_batch_for_session(session_id: str, document_id: str = None, total_questions: int = 10) -> TutoringQuestionBatch:
    """
    Generate a complete batch of unique questions from all chunks of a document.
    This replaces the single question generation approach with intelligent batch generation.
    """
    try:
        session = ChatSession.objects.get(id=session_id)
        user_id = str(session.user.id)
        
        print(f"Generating question batch for session {session_id}, user {user_id}...")
        
        # Check if batch already exists for this session
        existing_batch = TutoringQuestionBatch.objects.filter(session=session).first()
        if existing_batch and existing_batch.status in ['ready', 'in_progress']:
            print(f"Found existing question batch with {existing_batch.total_questions} questions")
            return existing_batch
        
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
            raise Exception("Could not initialize backend services")

        # Debug: Check what documents the user has
        user_documents = Document.objects.filter(user=session.user)
        print(f"User has {user_documents.count()} documents:")
        for doc in user_documents:
            s3_key = getattr(doc, 's3_key', 'No s3_key')
            print(f"  - Document ID: {doc.id}, Filename: {doc.filename}, S3 Key: {s3_key}")

        # 3. Build metadata filter for document-specific retrieval
        metadata_filter = {"tenant_tag": {"$eq": tenant_tag}}
        source_doc_id = None
        
        if document_id:
            try:
                doc = Document.objects.filter(id=document_id, user__id=user_id).first()
                if doc and getattr(doc, 's3_key', None):
                    source_doc_id = doc.s3_key.split('/')[-1]
                    metadata_filter["source_doc_id"] = {"$eq": source_doc_id}
                    print(f"Resolved document_id {document_id} to source_doc_id: {source_doc_id}")
                else:
                    # Fall back to using provided value directly (in case caller passed source_doc_id)
                    metadata_filter["source_doc_id"] = {"$eq": document_id}
                    source_doc_id = document_id
                    print(f"Could not resolve to s3_key, using document_id directly: {document_id}")
            except Exception as e:
                print(f"Warning: could not resolve document_id: {e}")
                metadata_filter["source_doc_id"] = {"$eq": document_id}
                source_doc_id = document_id
        else:
            print("No document_id provided, will search all user documents")

        print(f"Using metadata filter: {metadata_filter}")

        # 4. First, try to get some chunks to verify the user has data in Pinecone
        try:
            print(f"Testing if user has any data in namespace {tenant_tag}...")
            
            # Use a generic document exploration query to get diverse chunks
            exploration_query = "document content topics concepts key information"
            query_embeddings = embedding_client.get_embeddings([exploration_query])
            query_embedding = query_embeddings[0]
            
            # First test with just tenant filter to see if user has any data
            test_results = index.query(
                vector=query_embedding,
                top_k=5,  # Small number for testing
                namespace=tenant_tag,
                include_metadata=True,
                filter={"tenant_tag": {"$eq": tenant_tag}}  # Only tenant filter
            )
            
            test_matches = test_results.get('matches', []) if isinstance(test_results, dict) else getattr(test_results, 'matches', [])
            print(f"Test query found {len(test_matches)} total chunks for user")
            
            if len(test_matches) == 0:
                print("❌ No chunks found for user at all - document may not be ingested yet")
                raise Exception("No document content found for this user. Please ensure your document has been processed successfully.")
            
            # Now try with document-specific filter if we have document_id
            if document_id:
                print(f"Testing document-specific filter...")
                doc_results = index.query(
                    vector=query_embedding,
                    top_k=5,
                    namespace=tenant_tag,
                    include_metadata=True,
                    filter=metadata_filter
                )
                doc_matches = doc_results.get('matches', []) if isinstance(doc_results, dict) else getattr(doc_results, 'matches', [])
                print(f"Document-specific query found {len(doc_matches)} chunks")
                
                if len(doc_matches) == 0:
                    print(f"⚠️  No chunks found for source_doc_id: {source_doc_id}")
                    print("Available source_doc_ids in user's data:")
                    for match in test_matches[:3]:  # Show first 3 matches
                        md = match.get('metadata', {}) if isinstance(match, dict) else getattr(match, 'metadata', {})
                        available_source = md.get('source_doc_id', 'Unknown')
                        print(f"  - {available_source}")
                    
                    # Use the first available document's source_doc_id
                    if test_matches:
                        first_match_md = test_matches[0].get('metadata', {}) if isinstance(test_matches[0], dict) else getattr(test_matches[0], 'metadata', {})
                        fallback_source_id = first_match_md.get('source_doc_id')
                        if fallback_source_id:
                            print(f"🔄 Falling back to available document: {fallback_source_id}")
                            metadata_filter["source_doc_id"] = {"$eq": fallback_source_id}
                            source_doc_id = fallback_source_id
                        else:
                            # Remove document filter and use all user documents
                            print("🔄 Removing document filter, using all user documents")
                            metadata_filter = {"tenant_tag": {"$eq": tenant_tag}}
                            source_doc_id = None

        except Exception as e:
            print(f"Error in preliminary testing: {e}")
            raise Exception(f"Could not access document content: {str(e)}")

        # 5. Retrieve ALL chunks for the document using a proper embedding approach
        try:
            print(f"Fetching ALL chunks for document from namespace {tenant_tag}...")
            
            # Use a large top_k to get as many chunks as possible
            results = index.query(
                vector=query_embedding,  # Use real embedding vector
                top_k=1000,  # Large number to get all chunks
                namespace=tenant_tag,
                include_metadata=True,
                filter=metadata_filter
            )
            print("Pinecone query complete.")
        except Exception as e:
            print(f"Error querying Pinecone: {e}")
            raise Exception("Could not retrieve document content")

        # 5. Process ALL matches to build comprehensive context
        context_items = []
        raw_matches = results.get('matches', []) if isinstance(results, dict) else getattr(results, 'matches', [])
        
        print(f"Retrieved {len(raw_matches)} total chunks for batch generation")

        def _get_match_metadata(m):
            if isinstance(m, dict):
                return m.get('metadata', {}), m.get('id')
            else:
                meta = getattr(m, 'metadata', None)
                mid = getattr(m, 'id', None)
                return meta or {}, mid

        # Collect ALL context from matches with tenant verification
        for m in raw_matches:
            md, mid = _get_match_metadata(m)
            
            # Verify tenant_tag
            match_tenant_tag = md.get('tenant_tag')
            if match_tenant_tag != tenant_tag:
                print(f"WARNING: Skipping cross-tenant match! Expected {tenant_tag}, got {match_tenant_tag}")
                continue

            chunk_text = md.get('text', '').strip()
            chunk_index = md.get('chunk_index')
            source_id = md.get('source_doc_id')
            page_number = md.get('page_number', 'N/A')
            
            if chunk_text and source_id is not None and chunk_index is not None:
                context_items.append((source_id, chunk_index, page_number, chunk_text))

        if not context_items:
            print("No relevant context found for question generation.")
            raise Exception("No document content available for question generation")

        # 6. Sort chunks by page and chunk_index for logical ordering
        context_items.sort(key=lambda x: (x[2] if x[2] != 'N/A' else 0, x[1]))
        
        # 7. Build comprehensive context from ALL chunks
        full_document_context = "\n\n".join([
            f"[Page {page}, Section {ci}] {txt}"
            for sid, ci, page, txt in context_items
        ])
        
        print(f"Built comprehensive context from {len(context_items)} chunks")

        # 8. Create intelligent batch generation prompt
        batch_prompt_template = (
            "You are an expert tutor creating a comprehensive question set for a student. "
            "Based on the complete educational content provided below, generate EXACTLY {total_questions} diverse and unique tutoring questions.\n\n"
            "REQUIREMENTS:\n"
            "1. Generate {total_questions} distinct questions that cover different concepts from the content\n"
            "2. Ensure questions progress from basic understanding to advanced application\n"
            "3. Each question should focus on a different topic/concept from the content\n"
            "4. Vary question types: conceptual, analytical, application-based, and critical thinking\n"
            "5. Questions should be answerable using ONLY the provided content\n"
            "6. Make questions engaging and pedagogically sound\n"
            "7. Return ONLY a JSON array of questions in this format: [\"Question 1?\", \"Question 2?\", ...]\n"
            "8. Do not include numbering, explanations, or any other text - just the JSON array\n\n"
            "EDUCATIONAL CONTENT:\n{context}\n\n"
            "Generate exactly {total_questions} unique questions as a JSON array:"
        )

        augmented_prompt = batch_prompt_template.format(
            context=full_document_context[:15000],  # Limit context size for LLM
            total_questions=total_questions
        )

        # 9. Call Gemini LLM for batch generation
        try:
            print(f"Calling Gemini LLM for batch generation of {total_questions} questions...")
            if not gemini_client.is_available():
                raise Exception("Gemini LLM client is not available")
            
            llm_response = gemini_client.generate_response(augmented_prompt, max_tokens=2000)
            print("Batch generation response received.")
            
            # Parse JSON response
            try:
                # Clean the response and extract JSON
                cleaned_response = llm_response.strip()
                if cleaned_response.startswith('```json'):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]
                cleaned_response = cleaned_response.strip()
                
                questions_list = json.loads(cleaned_response)
                
                if not isinstance(questions_list, list):
                    raise ValueError("Response is not a JSON array")
                
                # Validate and clean questions
                valid_questions = []
                for q in questions_list:
                    if isinstance(q, str) and q.strip() and len(q.strip()) > 10:
                        valid_questions.append(q.strip())
                
                if len(valid_questions) < total_questions // 2:  # At least half the requested questions
                    raise ValueError(f"Only got {len(valid_questions)} valid questions, expected {total_questions}")
                
                questions_list = valid_questions[:total_questions]  # Limit to requested number
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Failed to parse JSON response: {e}")
                print(f"Raw response: {llm_response[:500]}...")
                
                # Fallback: try to extract questions from raw text
                lines = llm_response.split('\n')
                questions_list = []
                for line in lines:
                    line = line.strip()
                    if line and ('?' in line or line.endswith('.')):
                        # Remove numbering and quotes
                        clean_line = line.lstrip('0123456789. "\'').rstrip('"\' ')
                        if len(clean_line) > 10:
                            questions_list.append(clean_line)
                
                if len(questions_list) < 3:  # Minimum threshold
                    raise Exception("Could not extract valid questions from LLM response")
                
                questions_list = questions_list[:total_questions]
            
            print(f"Successfully generated {len(questions_list)} questions")
            
        except Exception as e:
            print(f"Error calling Gemini LLM for batch generation: {e}")
            raise Exception(f"Failed to generate question batch: {str(e)}")

        # 10. Create and save TutoringQuestionBatch
        question_batch = TutoringQuestionBatch.objects.create(
            session=session,
            user=session.user,
            document=session.document,
            questions=questions_list,
            current_question_index=0,
            total_questions=len(questions_list),
            source_doc_id=source_doc_id,
            tenant_tag=tenant_tag,
            status='ready'
        )
        
        print(f"Created question batch with {len(questions_list)} questions for session {session_id}")
        return question_batch
        
    except Exception as e:
        print(f"Error in generate_question_batch_for_session: {str(e)}")
        sentry_sdk.capture_exception(e, extras={
            "component": "rag_query",
            "function": "generate_question_batch_for_session",
            "session_id": session_id,
            "document_id": document_id if 'document_id' in locals() else None,
            "user_id": user_id if 'user_id' in locals() else None
        })
        # Create a failed batch record for tracking
        try:
            session = ChatSession.objects.get(id=session_id)
            TutoringQuestionBatch.objects.create(
                session=session,
                user=session.user,
                document=session.document,
                questions=["Sorry, I'm having trouble generating questions right now. Please try again."],
                current_question_index=0,
                total_questions=1,
                source_doc_id=source_doc_id if 'source_doc_id' in locals() else None,
                tenant_tag=get_tenant_tag(str(session.user.id)),
                status='failed'
            )
        except:
            pass
        raise e

def generate_tutoring_question(user_id: str, document_id: str = None, top_k: int = 4, session_id: str = None) -> str:
    """
    Generates a tutoring question using the intelligent batch approach.
    If no batch exists for the session, creates one. Otherwise, returns the next question from the batch.
    """
    print(f"Generating tutoring question for user {user_id}, session {session_id}...")
    
    # If no session_id provided, fall back to the old single-question generation
    if not session_id:
        return _generate_single_question_legacy(user_id, document_id, top_k)
    
    try:
        # Get or create question batch for this session
        session = ChatSession.objects.get(id=session_id)
        
        # Check if we have an existing question batch
        question_batch = TutoringQuestionBatch.objects.filter(session=session).first()
        
        if not question_batch or question_batch.status == 'failed':
            # Generate new batch
            print("No existing question batch found, generating new batch...")
            try:
                question_batch = generate_question_batch_for_session(
                    session_id=session_id,
                    document_id=document_id,
                    total_questions=10  # Default batch size
                )
            except Exception as e:
                print(f"Failed to generate question batch: {e}")
                sentry_sdk.capture_exception(e, extras={
                    "component": "rag_query",
                    "function": "generate_tutoring_question",
                    "session_id": session_id,
                    "document_id": document_id,
                    "user_id": user_id
                })
                return "I'm having trouble generating questions right now. Please try again later."
        
        # Get the current question from the batch
        if question_batch.status == 'ready' and question_batch.current_question_index == 0:
            # First question
            current_question = question_batch.get_current_question()
            question_batch.status = 'in_progress'
            question_batch.save()
            print(f"Returning first question from batch (1/{question_batch.total_questions})")
            return current_question
        elif question_batch.status == 'in_progress':
            # Get next question
            next_question = question_batch.get_next_question()
            if next_question:
                print(f"Returning question {question_batch.current_question_index + 1}/{question_batch.total_questions}")
                return next_question
            else:
                # All questions exhausted
                print("All questions in batch have been used")
                return "Congratulations! You've completed all the prepared questions for this session. Great work!"
        elif question_batch.status == 'completed':
            print("Question batch already completed")
            return "You've completed all the questions for this session. Well done!"
        else:
            print(f"Unexpected batch status: {question_batch.status}")
            return "I'm having trouble with the question sequence. Please try again."
            
    except ChatSession.DoesNotExist:
        print(f"Session {session_id} not found, falling back to legacy method")
        return _generate_single_question_legacy(user_id, document_id, top_k)
    except Exception as e:
        print(f"Error in generate_tutoring_question: {str(e)}")
        sentry_sdk.capture_exception(e, extras={
            "component": "rag_query",
            "function": "generate_tutoring_question",
            "session_id": session_id,
            "user_id": user_id
        })
        return "I'm having trouble generating a question right now. Please try again."

def _generate_single_question_legacy(user_id: str, document_id: str = None, top_k: int = 4) -> str:
    """
    Legacy single question generation (original implementation).
    Uses static retrieval prompt and generates one question at a time.
    """
    print(f"Using legacy question generation for user {user_id}...")
    
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
        return "I'm having trouble accessing your documents right now. Please try again later."

    # 3. Create a question-generation prompt to retrieve diverse content
    question_prompt = "generate tutoring question key concepts important topics"
    
    try:
        print("Embedding question-generation prompt...")
        query_embeddings = embedding_client.get_embeddings([question_prompt])
        query_embedding = query_embeddings[0]
        print("Embedding complete.")
    except Exception as e:
        print(f"Error encoding question prompt: {e}")
        return "I'm having trouble processing your documents right now."

    # 4. Retrieve from Pinecone using namespace with strict tenant filtering
    try:
        print(f"Querying Pinecone namespace {tenant_tag} for question generation...")
        
        # Build metadata filter
        metadata_filter = {"tenant_tag": {"$eq": tenant_tag}}
        # document_id coming from API may be the Django Document.id (UUID) while
        # vectors were stored with source_doc_id equal to the S3 filename.
        # Try to resolve a Document record to the stored source_doc_id when possible.
        if document_id:
            try:
                doc = Document.objects.filter(id=document_id, user__id=user_id).first()
                if doc and getattr(doc, 's3_key', None):
                    source_doc_id = doc.s3_key.split('/')[-1]
                    metadata_filter["source_doc_id"] = {"$eq": source_doc_id}
                    print(f"Resolved document_id to source_doc_id: {source_doc_id}")
                else:
                    # Fall back to using provided value directly (in case caller passed source_doc_id)
                    metadata_filter["source_doc_id"] = {"$eq": document_id}
            except Exception as e:
                print(f"Warning: could not resolve document_id to source_doc_id: {e}")
                metadata_filter["source_doc_id"] = {"$eq": document_id}
        
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=tenant_tag,
            include_metadata=True,
            filter=metadata_filter
        )
        print("Pinecone query complete.")
    except Exception as e:
        print(f"Error querying Pinecone: {e}")
        return "I couldn't retrieve your document content. Please try uploading your document again."

    # 5. Process matches to build context
    context_items = []
    raw_matches = None
    if isinstance(results, dict):
        raw_matches = results.get('matches') or []
    else:
        raw_matches = getattr(results, 'matches', []) or []

    print(f"Retrieved {len(raw_matches)} matches for question generation")

    def _get_match_metadata(m):
        if isinstance(m, dict):
            return m.get('metadata', {}), m.get('id')
        else:
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
        page_number = md.get('page_number', 'N/A')
        
        if chunk_text and source_id is not None and chunk_index is not None:
            context_items.append((source_id, chunk_index, page_number, chunk_text))

    if not context_items:
        print("No relevant context found for question generation.")
        # Instead of failing, generate a general question about the document
        return "Based on your uploaded document, can you explain what the main topic or subject matter is about?"

    # Build context for question generation
    # Use a larger snippet from each chunk so the LLM has enough material to form questions
    context = "\n".join([
        f"[Doc {sid}, Page {page}, Chunk {ci}] {txt[:800]}..."
        for sid, ci, page, txt in context_items
    ])

    # Create a focused prompt for tutoring question generation
    question_prompt_template = (
        "You are an expert tutor. Based on the educational content provided below, generate UP TO TWO focused tutoring questions (each question on its own line).\n"
        "REQUIREMENTS:\n"
        "1. Each question should be clear and test understanding of an important concept from the content.\n"
        "2. Prefer application or analysis-style prompts (not simple recall) when possible.\n"
        "3. Keep each question concise and focused on ONE main idea.\n"
        "4. Ensure the questions are answerable using ONLY the provided content.\n"
        "5. If content is limited, generate one solid question that uses what's available.\n"
        "6. Return ONLY the question texts, each on a separate line, and nothing else.\n\n"
        "EDUCATIONAL CONTENT:\n{context}\n\n"
        "Generate up to two tutoring questions now (one per line):"
    )

    augmented_prompt = question_prompt_template.format(context=context.strip())

    # 6. Call Gemini LLM
    try:
        print("Calling Gemini LLM for question generation...")
        if not gemini_client.is_available():
            return "The AI tutoring service is currently unavailable. Please try again later."
        
        question = gemini_client.generate_response(augmented_prompt, max_tokens=150)
        print("Question generated successfully.")
        return question.strip()
        
    except Exception as e:
        print(f"Error calling Gemini LLM for question generation: {e}")
        return "I'm having trouble generating a question right now. Please try again."

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
        sentry_sdk.capture_exception(e, extras={
            "component": "rag_query",
            "function": "query_rag",
            "user_id": user_id,
            "query": query[:100]  # First 100 chars of query
        })
        return f"Error: Failed to get response from AI model - {str(e)}"
