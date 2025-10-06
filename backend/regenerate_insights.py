"""
Quick script to regenerate BoostMe insights for existing sessions
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellotutor.settings')
django.setup()

from api.models import SessionInsight, EvaluatorResult, ChatSession
from api.agent_flow import TutorAgent

def regenerate_all_insights():
    """Regenerate insights for all sessions that have EvaluatorResults"""
    insights = SessionInsight.objects.all()
    print(f"Found {insights.count()} SessionInsight records")
    
    for insight in insights:
        session = insight.session
        print(f"\n{'='*60}")
        print(f"Session: {session.get_title()}")
        print(f"Session ID: {session.id}")
        
        # Check if there are EvaluatorResults
        results = EvaluatorResult.objects.filter(message__session=session)
        print(f"EvaluatorResults: {results.count()}")
        
        if results.count() == 0:
            print("⚠️ No EvaluatorResults - skipping")
            continue
        
        # Show current state
        print(f"Current state:")
        print(f"  Focus zone: {insight.focus_zone}")
        print(f"  Steady zone: {insight.steady_zone}")
        print(f"  Edge zone: {insight.edge_zone}")
        print(f"  XP: {insight.xp_points}")
        print(f"  Accuracy: {insight.accuracy}")
        
        # Regenerate using TutorAgent
        try:
            agent = TutorAgent(session)
            new_insight = agent._generate_session_insights()
            
            if new_insight:
                print(f"✅ Regenerated successfully!")
                print(f"  Focus zone: {new_insight.focus_zone}")
                print(f"  Steady zone: {new_insight.steady_zone}")
                print(f"  Edge zone: {new_insight.edge_zone}")
                print(f"  XP: {new_insight.xp_points}")
                print(f"  Accuracy: {new_insight.accuracy}")
            else:
                print("❌ Failed to regenerate")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    regenerate_all_insights()
