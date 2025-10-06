"""
Test script to verify end session insights generation flow
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellotutor.settings')
django.setup()

from api.models import ChatSession
from api.insight_generator import generate_insights_for_session

def test_end_session_insights():
    """Test that end session properly generates BoostMe insights"""
    
    # Get a session
    session = ChatSession.objects.first()
    if not session:
        print("❌ No sessions found in database")
        return
    
    print(f"\n{'='*60}")
    print(f"Testing End Session Insights Generation")
    print(f"{'='*60}")
    print(f"Session ID: {session.id}")
    print(f"Session Title: {session.get_title()}")
    print(f"User: {session.user.name}")
    
    # Call the same function that views.py calls
    print(f"\nCalling generate_insights_for_session()...")
    insight = generate_insights_for_session(str(session.id))
    
    if insight:
        print(f"\n✅ SUCCESS - Insights generated!")
        print(f"\n📊 BoostMe Insights:")
        print(f"  Focus Zone ({len(insight.focus_zone or [])} points):")
        if insight.focus_zone:
            for i, point in enumerate(insight.focus_zone, 1):
                print(f"    {i}. {point}")
        
        print(f"\n  Steady Zone ({len(insight.steady_zone or [])} points):")
        if insight.steady_zone:
            for i, point in enumerate(insight.steady_zone, 1):
                print(f"    {i}. {point}")
        
        print(f"\n  Edge Zone ({len(insight.edge_zone or [])} points):")
        if insight.edge_zone:
            for i, point in enumerate(insight.edge_zone, 1):
                print(f"    {i}. {point}")
        
        print(f"\n📈 Metrics:")
        print(f"  ⭐ XP Points: {insight.xp_points}")
        print(f"  🎯 Accuracy: {insight.accuracy}%")
        print(f"  📝 Total Q&A: {insight.total_qa_pairs}")
        print(f"  ✅ Status: {insight.status}")
        
    else:
        print(f"\n❌ FAILED - No insights generated")
        print(f"This usually means:")
        print(f"  - Session has < 2 answered questions")
        print(f"  - No EvaluatorResults found for this session")
    
    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    test_end_session_insights()
