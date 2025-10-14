"""Insight generation helper.

This module provides a small compatibility layer so views and tests can call
`generate_insights_for_session(session_id)`. It delegates to the TutorAgent
implementation to avoid duplicating logic.
"""
import sentry_sdk
from .models import ChatSession


class InsightGenerator:
    """Thin wrapper kept for backward compatibility.

    The real logic lives in `agent_flow.TutorAgent._generate_session_insights`.
    """

    def generate_session_insights(self, session):
        from .agent_flow import TutorAgent

        agent = TutorAgent(session)
        return agent._generate_session_insights()


def generate_insights_for_session(session_id: str):
    """Convenience function used by views and tests.

    Returns a SessionInsight instance on success or None on failure.
    """
    try:
        session = ChatSession.objects.get(id=session_id)
    except ChatSession.DoesNotExist:
        return None

    try:
        generator = InsightGenerator()
        insight = generator.generate_session_insights(session)
        return insight
    except Exception as e:
        # Log to Sentry but fail gracefully for the calling views
        try:
            sentry_sdk.capture_exception(e)
        except Exception:
            pass
        return None
