#!/bin/bash
# Bash script to start 4 Celery workers on Linux/Mac
# Usage: ./start_celery_workers.sh

echo "Starting InzightedG Celery Workers..."

# Check if Redis is running
echo "Checking Redis connection..."
if ! nc -z localhost 6379 2>/dev/null; then
    echo "ERROR: Redis is not running on localhost:6379"
    echo "Please start Redis first:"
    echo "  - Using Docker: docker run -d -p 6379:6379 redis:7-alpine"
    echo "  - Or install Redis: sudo apt-get install redis-server (Ubuntu)"
    exit 1
fi

echo "Redis connection OK"

# Set environment variables
export CELERY_BROKER_URL="redis://localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://localhost:6379/1"

# Navigate to script directory
cd "$(dirname "$0")"

echo ""
echo "Starting 4 Celery Workers..."
echo "Press Ctrl+C to stop all workers"
echo ""

# Start 4 workers in background
celery -A hellotutor worker --loglevel=info --concurrency=4 -n worker1@%h &
WORKER1_PID=$!
echo "✓ Worker 1 started (PID: $WORKER1_PID)"

celery -A hellotutor worker --loglevel=info --concurrency=4 -n worker2@%h &
WORKER2_PID=$!
echo "✓ Worker 2 started (PID: $WORKER2_PID)"

celery -A hellotutor worker --loglevel=info --concurrency=4 -n worker3@%h &
WORKER3_PID=$!
echo "✓ Worker 3 started (PID: $WORKER3_PID)"

celery -A hellotutor worker --loglevel=info --concurrency=4 -n worker4@%h &
WORKER4_PID=$!
echo "✓ Worker 4 started (PID: $WORKER4_PID)"

echo ""
echo "All workers are running!"
echo "Monitor workers: http://localhost:5555 (if Flower is installed)"
echo ""
echo "To stop workers, run: ./stop_celery_workers.sh"

# Trap Ctrl+C and stop all workers
trap "echo ''; echo 'Stopping workers...'; kill $WORKER1_PID $WORKER2_PID $WORKER3_PID $WORKER4_PID 2>/dev/null; echo 'Workers stopped.'; exit 0" INT TERM

# Wait for any worker to exit
wait
