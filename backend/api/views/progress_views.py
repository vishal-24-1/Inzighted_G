"""
Progress API Views

Endpoints for retrieving user gamification progress (Streak and Batch systems)
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..serializers import ProgressSerializer
from ..progress import get_progress_summary
import logging
import sentry_sdk

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_progress(request):
    """
    GET /api/progress/
    
    Retrieve current user's gamification progress including:
    - Streak system: current streak, earned milestones, progress to next milestone
    - Batch system: current batch, stars earned, XP progress
    
    Returns:
        200: Progress data
        {
            "streak": {
                "current": 12,
                "last_test_date": "2025-10-17",
                "earned_milestones": ["Bronze (7)", "Silver (15)"],
                "next_milestone": 15,
                "progress_to_next": 80.0
            },
            "batch": {
                "current_batch": "Silver",
                "current_star": 2,
                "xp_points": 45,
                "total_tests_taken": 10,
                "stars_per_batch": 5,
                "xp_to_next_star": 15,
                "next_star_threshold": 60
            }
        }
    """
    try:
        user = request.user
        
        # Get progress summary
        progress_data = get_progress_summary(user)
        
        # Serialize and return
        serializer = ProgressSerializer(progress_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving progress for user {request.user.id}: {e}", exc_info=True)
        sentry_sdk.capture_exception(e, extras={
            'component': 'progress_views',
            'endpoint': 'get_user_progress',
            'user_id': str(request.user.id) if request.user else None,
        })
        return Response(
            {'error': 'Failed to retrieve progress data'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
