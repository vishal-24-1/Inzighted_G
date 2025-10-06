"""
Insight Generation Module
Handles automatic generation of BoostMe insights for completed tutoring sessions.
Now uses TutorAgent's new BoostMe insights (3 zones + XP + Accuracy).
"""

import logging
from typing import Optional, Dict, Any
from django.conf import settings
from .models import ChatSession, SessionInsight, Document
from .gemini_client import gemini_client
import sentry_sdk

logger = logging.getLogger(__name__)


class InsightGenerator:
    """
    Handles automatic generation of BoostMe insights for tutoring sessions.
    Now delegates to TutorAgent for new insights format.
    """
    
    def __init__(self):
        # Use the module-level HTTP-based Gemini client instance
        self.gemini_client = gemini_client
    
    def generate_session_insights(self, session: ChatSession) -> Optional[SessionInsight]:
        """
        Generate BoostMe insights for a completed tutoring session.
        Uses TutorAgent's _generate_session_insights() which creates:
        - focus_zone (weak areas)
        - steady_zone (strong areas)
        - edge_zone (growth potential)
        - xp_points (count of answered questions)
        - accuracy (percentage of correct answers)
        
        Args:
            session: The ChatSession object to analyze
            
        Returns:
            SessionInsight object if successful, None if failed
        """
        try:
            # Check if insights already exist for this session
            if hasattr(session, 'insight') and session.insight:
                existing_insight = session.insight
                
                # Check if BoostMe fields are populated
                if existing_insight.focus_zone or existing_insight.steady_zone or existing_insight.edge_zone:
                    logger.info(f"BoostMe insights already exist for session {session.id}")
                    return existing_insight
                else:
                    logger.info(f"Found old SWOT insights for session {session.id}, regenerating with BoostMe format")
                    # Continue to regenerate with new format
            
            # Use TutorAgent to generate new BoostMe insights
            from .agent_flow import TutorAgent
            
            agent = TutorAgent(session)
            insight = agent._generate_session_insights()
            
            if insight:
                logger.info(f"Successfully generated BoostMe insights for session {session.id}")
                logger.info(f"  XP: {insight.xp_points}, Accuracy: {insight.accuracy}%")
                return insight
            else:
                logger.warning(f"Failed to generate insights for session {session.id} - not enough data")
                return None
                
        except Exception as e:
            logger.error(f"Error generating insight for session {session.id}: {str(e)}")
            sentry_sdk.capture_exception(e, extras={
                "component": "insight_generator",
                "method": "generate_session_insights",
                "session_id": str(session.id)
            })
            return None
    
    # Legacy helper methods kept for backward compatibility if needed elsewhere
    def _extract_qa_pairs(self, session: ChatSession) -> list:
        """Extract question-answer pairs from session messages."""
        messages = session.messages.all().order_by('created_at')
        qa_pairs = []
        
        current_question = None
        current_answers = []
        
        for message in messages:
            if message.is_user_message:
                if current_question:
                    current_answers.append(message.content)
            else:
                if current_question and current_answers:
                    combined_answer = " ".join(current_answers)
                    qa_pairs.append({
                        'question': current_question,
                        'answer': combined_answer
                    })
                    current_answers = []
                current_question = message.content
        
        if current_question and current_answers:
            combined_answer = " ".join(current_answers)
            qa_pairs.append({
                'question': current_question,
                'answer': combined_answer
            })
        
        return qa_pairs
    
    def _get_session_document(self, session: ChatSession) -> Optional[Document]:
        """
        Get the document associated with this session.
        """
        try:
            # First, check if the session has a document directly associated
            if session.document:
                return session.document
            
            # Fallback: return user's most recent document if no session document
            return session.user.documents.filter(status='completed').order_by('-upload_date').first()
        except Exception:
            return None
    
    def _calculate_session_duration(self, session: ChatSession) -> int:
        """Calculate session duration in minutes."""
        messages = session.messages.all().order_by('created_at')
        if messages.count() < 2:
            return 0
            
        first_message = messages.first()
        last_message = messages.last()
        duration = (last_message.created_at - first_message.created_at).total_seconds() / 60
        return round(duration)
    
    def _generate_swot_analysis(self, qa_pairs: list, session: ChatSession) -> Dict[str, str]:
        """Generate SWOT analysis using Gemini AI."""
        # Prepare the prompt
        qa_text = "\n".join([
            f"Q: {pair['question']}\nA: {pair['answer']}\n"
            for pair in qa_pairs
        ])
        
        prompt = f"""You are an expert tutor who critically evaluates how students think, respond, and understand concepts. Carefully analyze the following Q&A pairs. For each answer, infer:

- The student’s conceptual understanding
- Where they are thinking incorrectly
- How their misunderstandings affect their responses
- The reasoning they are using instead of the correct one
- Signs of confusion or misplaced confidence

Then generate a high-impact SWOT analysis that feels like feedback from a real tutor who wants the student to improve quickly.

Session Details:
- Total Q&A pairs: {len(qa_pairs)}
- Session duration: {self._calculate_session_duration(session)} minutes

Q&A Pairs:
{qa_text}

### OUTPUT IN THIS EXACT JSON FORMAT:
{{
  "strength": [
    "Point 1 (specific, encouraging, tied to their correct reasoning)",
    "Point 2 (acknowledges effort, accuracy, or confidence)"
  ],
  "weakness": [
    "Point 1 (directly calls out a misunderstanding: explain what the student thought vs what is correct)",
    "Point 2 (links the wrong reasoning to the wrong answer in a strong, corrective tone)"
  ],
  "opportunity": [
    "Point 1 (suggest what they can fix or practice based on the identified misunderstanding)",
    "Point 2 (show how correcting that specific misconception will level them up)"
  ],
  "threat": [
    "Point 1 (expose how their current misunderstanding or wrong thinking pattern will cause repeated mistakes)",
    "Point 2 (warn about long-term consequences if this wrong perspective isn't corrected)"
  ]
}}

### TONE & STYLE RULES:
- Do NOT be generic — reference how they actually answered.
- Weakness and threat must directly confront incorrect reasoning.
- Explicitly state: “You are thinking X, but the correct concept is Y.”
- Highlight how misunderstanding led to wrong answers.
- Be bold, corrective, and unfiltered — but still goal-oriented.
- Strengths and opportunities should stay motivating and confidence-building.
- Do not add any extra commentary or formatting outside the JSON.
- Each point should be concise, specific, and actionable within 10 to 15 words."""

        try:
            # Generate content using Gemini HTTP client
            # Use generate_response which returns the textual output
            response = self.gemini_client.generate_response(prompt, max_tokens=1200)
            
            # Parse the JSON response or fallback to plain text
            import json
            response_text = (response or '').strip()
            
            # Look for a JSON block in the response. Use JSONDecoder.raw_decode
            # to locate the first valid JSON object inside potentially noisy model output.
            import json
            decoder = json.JSONDecoder()
            swot_data = None

            # Scan for the first '{' and try to decode a JSON object from there
            for pos, ch in enumerate(response_text):
                if ch != '{':
                    continue
                try:
                    obj, end = decoder.raw_decode(response_text[pos:])
                    if isinstance(obj, dict):
                        swot_data = obj
                        break
                except json.JSONDecodeError:
                    # Not a valid JSON object starting at this position; continue scanning
                    continue

            if swot_data is not None:
                return {
                    'strength': swot_data.get('strength', 'No specific strengths identified.'),
                    'weakness': swot_data.get('weakness', 'No specific weaknesses identified.'),
                    'opportunity': swot_data.get('opportunity', 'No specific opportunities identified.'),
                    'threat': swot_data.get('threat', 'No specific threats identified.')
                }

            # Fallback: parse plain text response if no valid JSON object was found
            return self._parse_plain_text_response(response_text)
                
        except Exception as e:
            logger.error(f"Error generating SWOT analysis: {str(e)}")
            sentry_sdk.capture_exception(e, extras={
                "component": "insight_generator",
                "method": "_generate_swot_analysis",
                "qa_pairs_count": len(qa_pairs),
                "session_id": str(session.id)
            })
            return {
                'strength': 'Unable to analyze strengths at this time.',
                'weakness': 'Unable to analyze weaknesses at this time.',
                'opportunity': 'Unable to analyze opportunities at this time.',
                'threat': 'Unable to analyze threats at this time.'
            }
    
    def _parse_plain_text_response(self, response: str) -> Dict[str, str]:
        """
        Fallback method to parse plain text response if JSON parsing fails.
        """
        swot = {
            'strength': 'Analysis not available.',
            'weakness': 'Analysis not available.',
            'opportunity': 'Analysis not available.',
            'threat': 'Analysis not available.'
        }
        
        # Try to extract sections based on keywords
        response_lower = response.lower()
        
        # Simple extraction logic - you might want to improve this
        sections = ['strength', 'weakness', 'opportunity', 'threat']
        
        for i, section in enumerate(sections):
            start_patterns = [f"{section}:", f"{section}s:", f"**{section}"]
            
            for pattern in start_patterns:
                start_idx = response_lower.find(pattern.lower())
                if start_idx != -1:
                    start_idx += len(pattern)
                    
                    # Find end (next section or end of text)
                    end_idx = len(response)
                    for next_section in sections[i+1:]:
                        for next_pattern in [f"{next_section}:", f"{next_section}s:", f"**{next_section}"]:
                            next_idx = response_lower.find(next_pattern.lower(), start_idx)
                            if next_idx != -1:
                                end_idx = min(end_idx, next_idx)
                    
                    content = response[start_idx:end_idx].strip()
                    if content:
                        swot[section] = content
                    break
        
        return swot


# Convenience function for external use
def generate_insights_for_session(session_id: str) -> Optional[SessionInsight]:
    """
    Generate insights for a session by ID.
    
    Args:
        session_id: UUID string of the session
        
    Returns:
        SessionInsight object if successful, None if failed
    """
    try:
        session = ChatSession.objects.get(id=session_id)
        generator = InsightGenerator()
        return generator.generate_session_insights(session)
    except ChatSession.DoesNotExist:
        logger.error(f"Session {session_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error generating insights for session {session_id}: {str(e)}")
        sentry_sdk.capture_exception(e, extras={
            "component": "insight_generator",
            "function": "generate_insights_for_session",
            "session_id": session_id
        })
        return None