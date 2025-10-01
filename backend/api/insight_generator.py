"""
Insight Generation Module
Handles automatic generation of SWOT analysis insights for completed tutoring sessions.
"""

import logging
from typing import Optional, Dict, Any
from django.conf import settings
from .models import ChatSession, SessionInsight, Document
from .gemini_client import gemini_client

logger = logging.getLogger(__name__)


class InsightGenerator:
    """
    Handles automatic generation of SWOT insights for tutoring sessions.
    """
    
    def __init__(self):
        # Use the module-level HTTP-based Gemini client instance
        self.gemini_client = gemini_client
    
    def generate_session_insights(self, session: ChatSession) -> Optional[SessionInsight]:
        """
        Generate SWOT insights for a completed tutoring session.
        
        Args:
            session: The ChatSession object to analyze
            
        Returns:
            SessionInsight object if successful, None if failed
        """
        try:
            # Check if insights already exist for this session
            if hasattr(session, 'insight') and session.insight:
                logger.info(f"Insights already exist for session {session.id}")
                return session.insight
            
            # Get Q&A pairs from the session
            qa_pairs = self._extract_qa_pairs(session)
            
            if not qa_pairs:
                logger.warning(f"No Q&A pairs found for session {session.id}")
                return None
            
            # Create insight record with pending status
            # Create insight record with placeholder SWOT fields so DB constraints are satisfied
            insight = SessionInsight.objects.create(
                session=session,
                user=session.user,
                document=self._get_session_document(session),
                strength='',
                weakness='',
                opportunity='',
                threat='',
                total_qa_pairs=len(qa_pairs),
                session_duration_minutes=self._calculate_session_duration(session),
                status='processing'
            )
            
            try:
                # Generate SWOT analysis using Gemini (HTTP client)
                swot_analysis = self._generate_swot_analysis(qa_pairs, session)

                # Update insight with generated analysis
                insight.strength = swot_analysis.get('strength', '')
                insight.weakness = swot_analysis.get('weakness', '')
                insight.opportunity = swot_analysis.get('opportunity', '')
                insight.threat = swot_analysis.get('threat', '')
                insight.status = 'completed'
                insight.save()

                logger.info(f"Successfully generated insights for session {session.id}")
                return insight

            except Exception as e:
                # Mark as failed if generation fails
                insight.status = 'failed'
                insight.save()
                logger.error(f"Failed to generate insights for session {session.id}: {str(e)}")
                # Re-raise so the outer exception handler can capture and return None
                raise
                
        except Exception as e:
            logger.error(f"Error creating insight record for session {session.id}: {str(e)}")
            return None
    
    def _extract_qa_pairs(self, session: ChatSession) -> list:
        """Extract question-answer pairs from session messages."""
        messages = session.messages.all().order_by('created_at')
        qa_pairs = []
        
        current_question = None
        
        for message in messages:
            if message.is_user_message:
                # User message (answer to previous question or new question)
                if current_question:
                    # This is an answer to the previous question
                    qa_pairs.append({
                        'question': current_question,
                        'answer': message.content
                    })
                    current_question = None
                # If no current question, this might be the first message
            else:
                # AI message (question)
                current_question = message.content
        
        return qa_pairs
    
    def _get_session_document(self, session: ChatSession) -> Optional[Document]:
        """
        Try to identify the document associated with this session.
        This is a best-effort approach - you might need to adjust based on your data structure.
        """
        try:
            # For tutoring sessions, we might be able to infer the document from session title
            # or from user's recent documents. This is implementation-specific.
            # For now, return the user's most recent document
            return session.user.documents.filter(status='completed').order_by('-upload_date').first()
        except Exception:
            return None
    
    def _calculate_session_duration(self, session: ChatSession) -> int:
        """Calculate session duration in minutes."""
        messages = session.messages.all()
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
        
        prompt = f"""Analyze the following tutoring session Q&A pairs and provide SWOT insights about the student's performance.

Session Details:
- Total Q&A pairs: {len(qa_pairs)}
- Session duration: {self._calculate_session_duration(session)} minutes

Q&A Pairs:
{qa_text}

Please provide a detailed SWOT analysis in the following JSON format:
{{
    "strength": "Student's key strengths and what they did well",
    "weakness": "Areas where the student struggled or needs improvement", 
    "opportunity": "Learning opportunities and potential growth areas",
    "threat": "Challenges or obstacles that might hinder progress"
}}

Focus on:
- Understanding of concepts
- Problem-solving approach
- Communication clarity
- Learning progression
- Areas of confusion

Provide specific, actionable insights based on the actual Q&A content."""

        try:
            # Generate content using Gemini HTTP client
            # Use generate_response which returns the textual output
            response = self.gemini_client.generate_response(prompt, max_tokens=1200)
            
            # Parse the JSON response or fallback to plain text
            import json
            response_text = (response or '').strip()
            
            # Look for JSON block in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                swot_data = json.loads(json_text)
                
                return {
                    'strength': swot_data.get('strength', 'No specific strengths identified.'),
                    'weakness': swot_data.get('weakness', 'No specific weaknesses identified.'),
                    'opportunity': swot_data.get('opportunity', 'No specific opportunities identified.'),
                    'threat': swot_data.get('threat', 'No specific threats identified.')
                }
            else:
                # Fallback: parse plain text response
                return self._parse_plain_text_response(response_text)
                
        except Exception as e:
            logger.error(f"Error generating SWOT analysis: {str(e)}")
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
        return None