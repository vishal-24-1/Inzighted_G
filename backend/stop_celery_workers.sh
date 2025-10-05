#!/bin/bash
# Stop Celery Workers Script for Linux/Mac

echo "Stopping InzightedG Celery Workers..."

# Find and kill all celery worker processes
CELERY_PIDS=$(pgrep -f "celery.*worker")

if [ -n "$CELERY_PIDS" ]; then
    echo "Found Celery worker processes:"
    echo "$CELERY_PIDS"
    
    echo "Stopping workers..."
    kill $CELERY_PIDS 2>/dev/null
    
    # Wait a moment
    sleep 2
    
    # Force kill if still running
    REMAINING=$(pgrep -f "celery.*worker")
    if [ -n "$REMAINING" ]; then
        echo "Force stopping remaining workers..."
        kill -9 $REMAINING 2>/dev/null
    fi
    
    echo "✓ All Celery workers stopped"
else
    echo "No Celery workers found running"
fi

echo "Workers have been stopped."
