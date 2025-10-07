"""
Tanglish Agent Flow - Core State Machine
Implements the exact flow from specification § 1
"""

from .models import ChatSession, ChatMessage, QuestionItem, EvaluatorResult, TutoringQuestionBatch
from .gemini_client import gemini_client
from .rag_ingestion import initialize_pinecone, get_embedding_client
from .auth import get_tenant_tag
import logging
import sentry_sdk
import uuid

logger = logging.getLogger(__name__)


class TutorAgent:
    """
    Core Tanglish tutoring agent implementing the state machine from spec § 1.
    
    Flow:
    1. Pull next question from queue
    2. Deliver question in Tanglish
    3. Wait for user reply
    4. Classify intent (DIRECT_ANSWER / MIXED / RETURN_QUESTION)
    5. Branch and handle accordingly
    6. Run evaluator where needed
    7. Store results
    8. Advance queue
    9. After all questions: generate insights
    """
    
    def __init__(self, session: ChatSession):
        self.session = session
        self.user = session.user
        self.user_id = str(self.user.id)
        self.tenant_tag = get_tenant_tag(self.user_id)
    
    def get_or_create_question_batch(self) -> TutoringQuestionBatch:
        """
        Get existing question batch or create new one with structured questions.
        Uses the new generate_questions_structured method from Gemini client.
        """
        # Check for existing batch
        batch = TutoringQuestionBatch.objects.filter(session=self.session).first()
        
        if batch and batch.status in ['ready', 'in_progress']:
            logger.info(f"Found existing question batch: {batch.total_questions} questions")
            return batch
        
        # Need to create new batch
        logger.info("Creating new structured question batch...")
        
        try:
            # Get document context for question generation
            context = self._fetch_document_context()
            
            if not context:
                raise ValueError("No document context available")
            
            # Generate structured questions using Gemini
            questions_data = gemini_client.generate_questions_structured(context, total_questions=10)
            
            if not questions_data:
                raise ValueError("Failed to generate questions")
            
            # Create TutoringQuestionBatch
            batch = TutoringQuestionBatch.objects.create(
                session=self.session,
                user=self.user,
                document=self.session.document,
                questions=questions_data,  # Store full structured data
                current_question_index=0,
                total_questions=len(questions_data),
                source_doc_id=str(self.session.document.id) if self.session.document else None,
                tenant_tag=self.tenant_tag,
                status='ready'
            )
            
            # Create QuestionItem records for tracking
            for idx, q_data in enumerate(questions_data):
                QuestionItem.objects.create(
                    session=self.session,
                    batch=batch,
                    question_id=q_data.get('question_id', f"q_{uuid.uuid4().hex[:8]}"),
                    archetype=q_data.get('archetype', 'Concept Unfold'),
                    question_text=q_data.get('question_text', ''),
                    difficulty=q_data.get('difficulty', 'medium'),
                    expected_answer=q_data.get('expected_answer', ''),
                    order=idx,
                    asked=False
                )
            
            logger.info(f"Created question batch with {len(questions_data)} structured questions")
            return batch
            
        except Exception as e:
            logger.error(f"Error creating question batch: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "agent_flow",
                "method": "get_or_create_question_batch",
                "session_id": str(self.session.id)
            })
            
            # Create fallback batch
            fallback_questions = [{
                "question_id": "q_fallback",
                "archetype": "Concept Unfold",
                "question_text": "Can you explain the main topic from your document?",
                "difficulty": "easy",
                "expected_answer": "General explanation"
            }]
            
            batch = TutoringQuestionBatch.objects.create(
                session=self.session,
                user=self.user,
                document=self.session.document,
                questions=fallback_questions,
                current_question_index=0,
                total_questions=1,
                tenant_tag=self.tenant_tag,
                status='failed'
            )
            
            return batch
    
    def _fetch_document_context(self) -> str:
        """
        Fetch document chunks from Pinecone to build context for question generation.
        Similar to rag_query but fetches more chunks for comprehensive question generation.
        """
        try:
            embedding_client = get_embedding_client()
            index = initialize_pinecone()
            
            # Use a generic query to get diverse chunks
            exploration_query = "document content topics concepts key information"
            query_embeddings = embedding_client.get_embeddings([exploration_query])
            query_embedding = query_embeddings[0]
            
            # Build metadata filter
            metadata_filter = {"tenant_tag": {"$eq": self.tenant_tag}}
            
            if self.session.document:
                # Try to resolve document ID to source_doc_id
                from .models import Document
                doc = Document.objects.filter(id=self.session.document.id).first()
                if doc and hasattr(doc, 's3_key') and doc.s3_key:
                    source_doc_id = doc.s3_key.split('/')[-1]
                    metadata_filter["source_doc_id"] = {"$eq": source_doc_id}
            
            # Query Pinecone for chunks
            results = index.query(
                vector=query_embedding,
                top_k=20,  # Get more chunks for comprehensive context
                namespace=self.tenant_tag,
                include_metadata=True,
                filter=metadata_filter
            )
            
            # Extract and combine text from matches
            raw_matches = results.get('matches', []) if isinstance(results, dict) else getattr(results, 'matches', [])
            
            context_parts = []
            for m in raw_matches:
                md = m.get('metadata', {}) if isinstance(m, dict) else getattr(m, 'metadata', {})
                
                # Verify tenant tag
                if md.get('tenant_tag') != self.tenant_tag:
                    continue
                
                chunk_text = md.get('text', '').strip()
                if chunk_text:
                    context_parts.append(chunk_text)
            
            if not context_parts:
                logger.warning("No context chunks found for question generation")
                return "General educational content. Generate questions about learning and understanding."
            
            # Combine context (limit total size)
            combined_context = "\n\n".join(context_parts[:15])  # Limit to first 15 chunks
            return combined_context[:12000]  # Limit total characters
            
        except Exception as e:
            logger.error(f"Error fetching document context: {e}")
            return "Educational content. Generate appropriate tutoring questions."
    
    def get_next_question(self) -> tuple[str, QuestionItem]:
        """
        Get the next question from the batch.
        Returns (question_text, QuestionItem) or (None, None) if exhausted.
        """
        batch = self.get_or_create_question_batch()
        
        if batch.status == 'completed':
            logger.info("Question batch completed")
            return None, None
        
        # Get current QuestionItem
        question_item = QuestionItem.objects.filter(
            batch=batch,
            order=batch.current_question_index
        ).first()
        
        if not question_item:
            logger.error(f"QuestionItem not found for index {batch.current_question_index}")
            return None, None
        
        # Mark as asked
        if not question_item.asked:
            question_item.asked = True
            question_item.save()
        
        # Update batch status
        if batch.status == 'ready':
            batch.status = 'in_progress'
            batch.save()
        
        # Apply language preference
        question_text = question_item.question_text
        if self.session.language == 'english':
            # Simple conversion: just return as-is (or add translation logic later)
            pass
        
        return question_text, question_item
    
    def advance_to_next_question(self) -> bool:
        """
        Move to the next question in the batch.
        Returns True if more questions available, False if exhausted.
        """
        batch = TutoringQuestionBatch.objects.filter(session=self.session).first()
        
        if not batch:
            return False
        
        if batch.current_question_index < batch.total_questions - 1:
            batch.current_question_index += 1
            batch.save()
            logger.info(f"Advanced to question {batch.current_question_index + 1}/{batch.total_questions}")
            return True
        else:
            # All questions exhausted
            batch.status = 'completed'
            batch.save()
            logger.info("All questions in batch completed")
            return False
    
    def handle_user_message(self, user_message: str, current_question_item: QuestionItem) -> dict:
        """
        Core flow § 1: Handle user message with intent classification and branching.
        
        Returns dict with:
        - reply: Text to send back to user
        - next_question: Next question text (if flow continues)
        - session_complete: Boolean indicating if session is done
        - evaluation: Evaluation results (if answer was evaluated)
        """
        print(f"\n{'='*60}")
        print(f"[AGENT] HANDLING USER MESSAGE")
        print(f"[AGENT] Session: {self.session.id}")
        print(f"[AGENT] User message: {user_message[:100]}...")
        print(f"{'='*60}\n")
        
        # Store user message
        user_msg_record = ChatMessage.objects.create(
            session=self.session,
            user=self.user,
            content=user_message,
            is_user_message=True
        )
        
        # § 1.4 — Classify intent using Gemini
        print(f"[AGENT] Calling intent classifier...")
        classifier_token = gemini_client.classify_intent(user_message)
        print(f"[AGENT] ✅ Intent classified as: {classifier_token}\n")
        
        # Update message with classifier token
        user_msg_record.classifier_token = classifier_token
        user_msg_record.save()
        
        # § 1.5 — Branch based on classifier token
        print(f"[AGENT] Branching to handler for intent: {classifier_token}")
        
        if classifier_token == "DIRECT_ANSWER":
            # § 1.5.1 — Treat as answer, evaluate, store, advance
            print(f"[AGENT] → Calling _handle_direct_answer\n")
            return self._handle_direct_answer(user_message, current_question_item, user_msg_record)
        
        elif classifier_token == "MIXED":
            # § 1.5.2 — Answer follow-up, evaluate, store, advance
            print(f"[AGENT] → Calling _handle_mixed\n")
            return self._handle_mixed(user_message, current_question_item, user_msg_record)
        
        elif classifier_token == "RETURN_QUESTION":
            # § 1.5.3 — Answer user question, resume with next question
            print(f"[AGENT] → Calling _handle_return_question\n")
            return self._handle_return_question(user_message, current_question_item, user_msg_record)
        
        else:
            # Fallback
            logger.warning(f"[AGENT] ⚠️ Unknown classifier token: {classifier_token}")
            return {
                "reply": "I didn't understand that. Can you please clarify?",
                "next_question": None,
                "session_complete": False,
                "evaluation": None
            }
    
    def _handle_direct_answer(self, user_message: str, question_item: QuestionItem, user_msg_record: ChatMessage) -> dict:
        """
        Handle DIRECT_ANSWER flow - user directly answered the tutoring question.
        NO RAG explanation shown, only evaluation (score/XP/feedback in evaluation object).
        """
        logger.info("Handling DIRECT_ANSWER flow - NO RAG explanation, evaluation only")
        
        # Run evaluator to score the answer
        evaluation = self._evaluate_answer(user_message, question_item, user_msg_record)
        
        # For DIRECT_ANSWER: NO reply text shown to user
        # The evaluation object contains score/XP/explanation which frontend shows separately
        
        # Advance to next question
        has_more = self.advance_to_next_question()
        
        if has_more:
            next_q_text, next_q_item = self.get_next_question()
            return {
                "reply": None,  # No explanation for direct answers
                "next_question": next_q_text,
                "next_question_item": next_q_item,
                "session_complete": False,
                "evaluation": evaluation
            }
        else:
            # Session complete - trigger insights generation
            self._generate_session_insights()
            return {
                "reply": "Great job! You've completed all questions. 🎉",
                "next_question": None,
                "session_complete": True,
                "evaluation": evaluation
            }
    
    def _handle_mixed(self, user_message: str, question_item: QuestionItem, user_msg_record: ChatMessage) -> dict:
        """
        Handle MIXED flow - user provided both an answer and a follow-up question
        Answer their question first, then evaluate their answer, then move to next question
        """
        logger.info("Handling MIXED flow")
        
        # First, answer the follow-up question part using RAG
        followup_reply = self._answer_user_question_with_rag(user_message)
        
        # Then evaluate the answer portion
        # For MIXED messages, the whole message is treated as the answer for evaluation
        evaluation = self._evaluate_answer(user_message, question_item, user_msg_record)
        
        # Advance to next question
        has_more = self.advance_to_next_question()
        
        if has_more:
            next_q_text, next_q_item = self.get_next_question()
            return {
                "reply": followup_reply,
                "next_question": next_q_text,
                "next_question_item": next_q_item,
                "session_complete": False,
                "evaluation": evaluation
            }
        else:
            self._generate_session_insights()
            return {
                "reply": followup_reply + "\n\nGreat job! You've completed all questions. 🎉",
                "next_question": None,
                "session_complete": True,
                "evaluation": evaluation
            }
    
    def _handle_return_question(self, user_message: str, question_item: QuestionItem, user_msg_record: ChatMessage) -> dict:
        """
        Handle RETURN_QUESTION flow
        User asked a question instead of answering - answer their question then move to next question
        """
        print(f"\n[AGENT] === RETURN_QUESTION Flow ===")
        print(f"[AGENT] User asked: {user_message[:80]}...")
        
        # Answer the user's question using RAG
        print(f"[AGENT] Calling RAG to answer user's question...")
        clarification_reply = self._answer_user_question_with_rag(user_message)
        print(f"[AGENT] RAG reply length: {len(clarification_reply)} chars")
        print(f"[AGENT] RAG reply preview: {clarification_reply[:150]}...")
        
        # Move to next question (as per requirement)
        has_more = self.advance_to_next_question()
        
        if has_more:
            next_q_text, next_q_item = self.get_next_question()
            print(f"[AGENT] ✅ Returning reply + next question\n")
            return {
                "reply": clarification_reply,
                "next_question": next_q_text,
                "next_question_item": next_q_item,
                "session_complete": False,
                "evaluation": None  # No evaluation for questions
            }
        else:
            # All questions exhausted
            self._generate_session_insights()
            print(f"[AGENT] ✅ Session complete, returning reply\n")
            return {
                "reply": clarification_reply + "\n\nGreat job! You've completed all questions. 🎉",
                "next_question": None,
                "session_complete": True,
                "evaluation": None
            }
    
    def _evaluate_answer(self, student_answer: str, question_item: QuestionItem, user_msg_record: ChatMessage) -> EvaluatorResult:
        """
        Run answer evaluator using Gemini Judge (§ 4 from spec).
        Creates and returns EvaluatorResult record.
        """
        try:
            # Build context for evaluation
            context = f"Question: {question_item.question_text}\nExpected: {question_item.expected_answer}"
            
            # Call Gemini evaluator
            eval_dict = gemini_client.evaluate_answer(
                context=context,
                expected_answer=question_item.expected_answer,
                student_answer=student_answer
            )
            
            # Create EvaluatorResult record
            evaluator_result = EvaluatorResult.objects.create(
                message=user_msg_record,
                question=question_item,
                raw_json=eval_dict,
                score=eval_dict.get('score', 0.0),
                correct=eval_dict.get('correct', False),
                xp=eval_dict.get('XP', 0),
                explanation=eval_dict.get('explanation', ''),
                confidence=eval_dict.get('confidence', 0.0),
                followup_action=eval_dict.get('followup_action', 'none'),
                return_question_answer=eval_dict.get('return_question_answer', '')
            )
            
            logger.info(f"Answer evaluated: score={evaluator_result.score}, XP={evaluator_result.xp}")
            return evaluator_result
            
        except Exception as e:
            logger.error(f"Error evaluating answer: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "agent_flow",
                "method": "_evaluate_answer",
                "session_id": str(self.session.id)
            })
            
            # Fallback: create minimal evaluation
            evaluator_result = EvaluatorResult.objects.create(
                message=user_msg_record,
                question=question_item,
                raw_json={"error": str(e)},
                score=0.5,
                correct=False,
                xp=25,
                explanation="Unable to fully evaluate. Partial credit given.",
                confidence=0.3,
                followup_action='none',
                return_question_answer=''
            )
            return evaluator_result
    
    def _answer_user_question_with_rag(self, user_message: str) -> str:
        """
        Answer user's question using RAG (Retrieval Augmented Generation).
        Uses the document context to answer the user's question in Tanglish style.
        """
        try:
            # Use RAG to answer the user's question
            from .rag_query import query_rag
            
            logger.info(f"[RAG] Answering user question using RAG: {user_message[:50]}...")
            rag_response = query_rag(self.user_id, user_message)
            logger.info(f"[RAG] Raw response length: {len(rag_response)} chars, preview: {rag_response[:100]}...")
            
            # Check if RAG found nothing
            if "I could not find" in rag_response or "I don't know" in rag_response:
                logger.info("[RAG] No relevant content found, returning fallback message")
                return f"{rag_response}\n\nLet me know if you have other questions, or let's continue with the next question."
            
            # If RAG response is too long, summarize it in Tanglish style
            if len(rag_response) > 200:
                logger.info(f"[RAG] Response too long ({len(rag_response)} chars), summarizing in Tanglish...")
                # Ask Gemini to make it concise and Tanglish - CRITICAL: Must provide the answer, not ask back
                summary_prompt = (
                    f"Convert this answer into concise Tanglish style (mix of Tamil and English). "
                    f"Keep the key information but make it conversational and brief (under 150 words). "
                    f"IMPORTANT: You must PROVIDE the answer, not ask the user a question.\n\n"
                    f"Original answer:\n{rag_response}\n\n"
                    f"Tanglish version (provide the answer):"
                )
                rag_response = gemini_client.generate_response(summary_prompt, max_tokens=200)
                logger.info(f"[RAG] Tanglish summary: {rag_response[:100]}...")
            
            # If the RAG response contains prompting language (asking user to try/answer),
            # rewrite it into a direct factual Tanglish answer.
            prompting_phrases = [
                'try', 'try to', 'can you', 'do you know', 'tell me', 'please', 'let me know',
                'could you', 'explain', 'try panna', 'ungalukku therinja', 'intha question', 'please try'
            ]
            lower_resp = (rag_response or '').lower()
            if any(p in lower_resp for p in prompting_phrases) or rag_response.strip().endswith('?'):
                logger.info('[RAG] Detected prompting language in RAG output — forcing rewrite into direct answer')
                rewrite_prompt = (
                    f"Rewrite the following text into a clear, direct answer in Tanglish (Tamil in latin words) and use English for technical terms. "
                    f"Do NOT ask the user any follow-up questions or tell them to try anything. "
                    f"Keep key facts and, if available, include short citations in square brackets like [doc:chunk].\n\n"
                    f"Original text:\n{rag_response}\n\n"
                    f"Tanglish direct answer:"
                )
                try:
                    rewritten = gemini_client.generate_response(rewrite_prompt, max_tokens=200)
                    if rewritten:
                        rag_response = rewritten.strip()
                        logger.info(f"[RAG] Rewrote prompting output into direct answer: {rag_response[:120]}...")
                except Exception as e:
                    logger.warning(f"[RAG] Failed to rewrite prompting output: {e}")

            # Return the answer with encouragement to continue
            logger.info(f"[RAG] Returning final response to user")
            return f"{rag_response}\n\nNow, let's continue with the question."
                
        except Exception as e:
            logger.error(f"Error answering user question with RAG: {e}")
            sentry_sdk.capture_exception(e)
            # Fallback to generic response
            if '?' in user_message:
                return "Good question! Let me help: focus on the key concepts from your document. Try your best to answer based on what you've learned."
            else:
                return "I see. Let's continue with the next question."
                return "I see. Let's continue with the next question."
    
    def _generate_session_insights(self):
        """
        Generate BoostMe insights after session completion.
        Calculates XP (1 per question), accuracy (% correct), and 3 zones (focus/steady/edge).
        """
        try:
            logger.info("Generating BoostMe session insights...")
            
            # Collect QA records and evaluations
            evaluations = EvaluatorResult.objects.filter(
                message__session=self.session
            ).select_related('question', 'message')
            
            total_questions = evaluations.count()
            
            if total_questions == 0:
                logger.warning("No evaluations found for insights")
                return None
            
            # Calculate Accuracy: percentage of correct answers
            correct_count = evaluations.filter(correct=True).count()
            accuracy = round((correct_count / total_questions) * 100, 2) if total_questions > 0 else 0.0

            # Calculate session XP as: (average XP per answered question * accuracy%) / 100
            # - avg_xp: mean of EvaluatorResult.xp across attended evaluations
            # - session_xp = (avg_xp * accuracy) / 100
            # Store as integer XP points (rounded)
            sum_xp = 0
            for ev in evaluations:
                # ensure xp is numeric; default to 0 if missing
                try:
                    sum_xp += float(ev.xp or 0)
                except Exception:
                    sum_xp += 0

            avg_xp = (sum_xp / total_questions) if total_questions > 0 else 0.0
            session_xp = (avg_xp * accuracy) / 100.0
            xp_points = int(round(session_xp))

            logger.info(f"Session metrics - avg_xp: {avg_xp:.2f}, session_xp: {xp_points}, Accuracy: {accuracy}%, Total Q&A: {total_questions}")
            
            # Build QA records for insights prompt
            qa_records = []
            for eval_result in evaluations:
                qa_records.append({
                    "question": eval_result.question.question_text if eval_result.question else "N/A",
                    "answer": eval_result.message.content if eval_result.message else "N/A",
                    "score": eval_result.score,
                    "xp": eval_result.xp,
                    "correct": eval_result.correct
                })
            
            # Call Gemini for BoostMe insights (3 zones)
            boostme_insights = gemini_client.generate_boostme_insights(qa_records)
            
            # Create or update SessionInsight record
            from .models import SessionInsight
            
            insight, created = SessionInsight.objects.update_or_create(
                session=self.session,
                defaults={
                    "user": self.user,
                    "document": self.session.document,
                    # BoostMe fields
                    "focus_zone": boostme_insights.get('focus_zone', []),
                    "steady_zone": boostme_insights.get('steady_zone', []),
                    "edge_zone": boostme_insights.get('edge_zone', []),
                    "xp_points": xp_points,
                    "accuracy": accuracy,
                    # Legacy SWOT fields (empty for backward compatibility)
                    "strength": "",
                    "weakness": "",
                    "opportunity": "",
                    "threat": "",
                    # Metadata
                    "total_qa_pairs": total_questions,
                    "status": 'completed'
                }
            )
            
            logger.info(f"BoostMe insights {'created' if created else 'updated'} - XP: {xp_points}, Accuracy: {accuracy}%")
            return insight
            
        except Exception as e:
            logger.error(f"Error generating session insights: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "agent_flow",
                "method": "_generate_session_insights",
                "session_id": str(self.session.id)
            })
            return None
