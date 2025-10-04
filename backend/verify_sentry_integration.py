"""
Sentry Integration Verification Script

This script verifies that Sentry has been properly integrated into the HelloTutor backend.
Run this after setting up your Sentry DSN to ensure everything is working correctly.

Usage:
    python verify_sentry_integration.py
"""

import os
import sys
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hellotutor.settings')

# Initialize Django
import django
django.setup()

def check_sentry_installed():
    """Check if sentry-sdk is installed"""
    try:
        import sentry_sdk
        print("✅ sentry-sdk is installed")
        return True
    except ImportError:
        print("❌ sentry-sdk is NOT installed")
        print("   Run: pip install 'sentry-sdk[django]>=1.40.0'")
        return False

def check_sentry_configured():
    """Check if Sentry is configured in settings"""
    from django.conf import settings
    
    dsn = getattr(settings, 'SENTRY_DSN', None)
    environment = getattr(settings, 'SENTRY_ENVIRONMENT', None)
    
    if not dsn:
        print("⚠️  SENTRY_DSN is not configured in .env")
        print("   Add: SENTRY_DSN=your_sentry_dsn_here")
        return False
    
    if dsn == "your_sentry_dsn_here":
        print("⚠️  SENTRY_DSN still has placeholder value")
        print("   Update with your real DSN from sentry.io")
        return False
    
    print(f"✅ SENTRY_DSN is configured")
    print(f"✅ Environment: {environment or 'development'}")
    return True

def check_sentry_initialized():
    """Check if Sentry has been initialized"""
    try:
        import sentry_sdk
        hub = sentry_sdk.Hub.current
        client = hub.client
        
        if client is None:
            print("⚠️  Sentry client is None - not initialized")
            return False
        
        print("✅ Sentry is initialized")
        return True
    except Exception as e:
        print(f"❌ Error checking Sentry initialization: {e}")
        return False

def test_sentry_capture():
    """Test capturing a message to Sentry"""
    try:
        import sentry_sdk
        
        print("\n📤 Sending test message to Sentry...")
        event_id = sentry_sdk.capture_message(
            "HelloTutor Backend - Sentry Integration Test",
            level="info",
            extras={
                "test": True,
                "component": "verification_script"
            }
        )
        
        if event_id:
            print(f"✅ Test message sent successfully!")
            print(f"   Event ID: {event_id}")
            print(f"   Check your Sentry dashboard: https://sentry.io/")
            return True
        else:
            print("⚠️  Message capture returned None (Sentry might not be configured)")
            return False
            
    except Exception as e:
        print(f"❌ Error sending test message: {e}")
        return False

def check_integration_files():
    """Check that all expected files have Sentry imports"""
    files_to_check = [
        'api/gemini_client.py',
        'api/views.py',
        'api/rag_ingestion.py',
        'api/rag_query.py',
        'api/s3_storage.py',
        'api/insight_generator.py',
        'api/auth.py',
    ]
    
    print("\n🔍 Checking integration files...")
    all_good = True
    
    for file_path in files_to_check:
        full_path = backend_dir / file_path
        if not full_path.exists():
            print(f"⚠️  File not found: {file_path}")
            all_good = False
            continue
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'import sentry_sdk' in content:
                print(f"✅ {file_path} has Sentry import")
            else:
                print(f"❌ {file_path} missing Sentry import")
                all_good = False
    
    return all_good

def main():
    """Main verification function"""
    print("=" * 60)
    print("🔐 HelloTutor Backend - Sentry Integration Verification")
    print("=" * 60)
    print()
    
    checks = {
        "Sentry SDK Installed": check_sentry_installed(),
        "Sentry Configured": check_sentry_configured(),
        "Sentry Initialized": check_sentry_initialized(),
        "Integration Files": check_integration_files(),
    }
    
    # Only test capture if basics are working
    if all([checks["Sentry SDK Installed"], checks["Sentry Configured"], checks["Sentry Initialized"]]):
        checks["Test Message Sent"] = test_sentry_capture()
    else:
        print("\n⚠️  Skipping test message (prerequisites not met)")
        checks["Test Message Sent"] = None
    
    print("\n" + "=" * 60)
    print("📊 Verification Summary")
    print("=" * 60)
    
    for check_name, result in checks.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⏭️  SKIP"
        print(f"{status} - {check_name}")
    
    passed = sum(1 for v in checks.values() if v is True)
    total = len([v for v in checks.values() if v is not None])
    
    print("\n" + "=" * 60)
    if passed == total:
        print("🎉 All checks passed! Sentry is fully integrated.")
        print("\n📌 Next steps:")
        print("   1. Check your Sentry dashboard for the test message")
        print("   2. Set up alerting rules")
        print("   3. Configure team access")
        print("   4. Review SENTRY_INTEGRATION.md for best practices")
    else:
        print(f"⚠️  {total - passed} check(s) failed. Review the output above.")
        print("\n📌 Troubleshooting:")
        print("   1. Install Sentry: pip install 'sentry-sdk[django]>=1.40.0'")
        print("   2. Configure DSN in .env file")
        print("   3. Restart Django server")
        print("   4. Review SENTRY_SETUP_QUICK_START.md")
    
    print("=" * 60)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
