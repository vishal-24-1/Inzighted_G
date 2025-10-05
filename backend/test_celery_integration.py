"""
Celery Integration Test Script

This script tests the Celery integration for document processing.
Run this after setting up Celery workers to verify everything works.

Usage:
    python test_celery_integration.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellotutor.settings')
django.setup()

from api.tasks import test_celery, process_document
from api.models import Document, User
from celery.result import AsyncResult
import time


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_success(text):
    """Print success message"""
    print(f"✅ {text}")


def print_error(text):
    """Print error message"""
    print(f"❌ {text}")


def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")


def test_celery_connection():
    """Test 1: Basic Celery connectivity"""
    print_header("Test 1: Celery Connection")
    
    try:
        print_info("Sending test task to Celery...")
        result = test_celery.delay()
        
        print_info(f"Task ID: {result.id}")
        print_info("Waiting for result (timeout: 10s)...")
        
        task_result = result.get(timeout=10)
        
        if task_result and task_result.get('status') == 'success':
            print_success("Celery connection test PASSED")
            print_info(f"Message: {task_result.get('message')}")
            return True
        else:
            print_error("Unexpected result from test task")
            return False
            
    except Exception as e:
        print_error(f"Celery connection test FAILED: {str(e)}")
        print_info("Make sure:")
        print_info("  1. Redis is running (redis-cli ping)")
        print_info("  2. Celery workers are started")
        print_info("  3. Environment variables are set")
        return False


def test_task_registration():
    """Test 2: Check if process_document task is registered"""
    print_header("Test 2: Task Registration")
    
    try:
        from celery import current_app
        
        registered_tasks = list(current_app.tasks.keys())
        
        if 'api.tasks.process_document' in registered_tasks:
            print_success("process_document task is registered")
            return True
        else:
            print_error("process_document task NOT registered")
            print_info("Registered tasks:")
            for task in registered_tasks:
                if task.startswith('api.'):
                    print_info(f"  - {task}")
            return False
            
    except Exception as e:
        print_error(f"Task registration check FAILED: {str(e)}")
        return False


def test_mock_document_processing():
    """Test 3: Mock document processing task"""
    print_header("Test 3: Mock Document Processing")
    
    try:
        # Get a test user
        user = User.objects.first()
        if not user:
            print_error("No users found in database. Please create a user first.")
            return False
        
        print_info(f"Using test user: {user.email}")
        
        # Check if there's a document to test with
        test_doc = Document.objects.filter(user=user, status='completed').first()
        
        if not test_doc:
            print_info("No completed documents found. Skipping actual task execution.")
            print_info("This test requires an uploaded document to fully verify.")
            return True
        
        print_info(f"Found test document: {test_doc.filename}")
        print_info("Testing idempotency (document already completed)...")
        
        # Enqueue task for already-completed document (should skip processing)
        result = process_document.delay(
            s3_key=test_doc.s3_key,
            user_id=str(user.id),
            document_id=str(test_doc.id)
        )
        
        print_info(f"Task ID: {result.id}")
        print_info("Waiting for result (timeout: 60s)...")
        
        task_result = result.get(timeout=60)
        
        if task_result and task_result.get('success'):
            print_success("Document processing task executed successfully")
            print_info(f"Result: {task_result}")
            return True
        else:
            print_error("Document processing task returned unexpected result")
            print_info(f"Result: {task_result}")
            return False
            
    except Exception as e:
        print_error(f"Mock document processing FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_task_status_tracking():
    """Test 4: Task status tracking"""
    print_header("Test 4: Task Status Tracking")
    
    try:
        print_info("Sending test task...")
        result = test_celery.delay()
        task_id = result.id
        
        print_info(f"Task ID: {task_id}")
        
        # Check various states
        states_checked = []
        for i in range(10):
            task_result = AsyncResult(task_id)
            state = task_result.state
            
            if state not in states_checked:
                print_info(f"Task state: {state}")
                states_checked.append(state)
            
            if state in ['SUCCESS', 'FAILURE']:
                break
                
            time.sleep(0.5)
        
        if 'SUCCESS' in states_checked:
            print_success("Task status tracking works correctly")
            return True
        else:
            print_error("Task did not reach SUCCESS state")
            return False
            
    except Exception as e:
        print_error(f"Task status tracking test FAILED: {str(e)}")
        return False


def test_worker_count():
    """Test 5: Check number of active workers"""
    print_header("Test 5: Worker Count")
    
    try:
        from celery import current_app
        
        inspect = current_app.control.inspect()
        active_workers = inspect.active()
        
        if not active_workers:
            print_error("No active Celery workers found!")
            print_info("Please start workers using:")
            print_info("  - Windows: .\\start_celery_workers.ps1")
            print_info("  - Linux/Mac: ./start_celery_workers.sh")
            print_info("  - Docker: docker-compose up -d")
            return False
        
        worker_count = len(active_workers.keys())
        print_success(f"Found {worker_count} active worker(s)")
        
        for worker_name in active_workers.keys():
            print_info(f"  - {worker_name}")
        
        if worker_count >= 4:
            print_success("All 4 workers are running")
            return True
        else:
            print_error(f"Only {worker_count}/4 workers running")
            return False
            
    except Exception as e:
        print_error(f"Worker count check FAILED: {str(e)}")
        return False


def run_all_tests():
    """Run all tests"""
    print_header("Celery Integration Test Suite")
    print_info("This script will verify your Celery setup")
    
    results = []
    
    # Run tests
    results.append(("Celery Connection", test_celery_connection()))
    results.append(("Task Registration", test_task_registration()))
    results.append(("Worker Count", test_worker_count()))
    results.append(("Task Status Tracking", test_task_status_tracking()))
    results.append(("Mock Document Processing", test_mock_document_processing()))
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status:12} {test_name}")
    
    print("\n" + "-" * 60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("All tests passed! Celery is working correctly.")
        return True
    else:
        print_error(f"{total - passed} test(s) failed. Please review the output above.")
        return False


if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
