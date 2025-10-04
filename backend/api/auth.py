import hmac
import hashlib
from django.conf import settings
import sentry_sdk

def get_tenant_tag(user_id: str) -> str:
    """
    Generates a secure HMAC tag for a given user ID.
    """
    try:
        secret = settings.HMAC_SECRET
        if not secret:
            sentry_sdk.capture_message(
                "HMAC_SECRET is not set in environment",
                level="error",
                extras={"component": "auth", "function": "get_tenant_tag"}
            )
            raise ValueError("HMAC_SECRET is not set in the environment.")
        
        return hmac.new(secret.encode('utf-8'), user_id.encode('utf-8'), hashlib.sha256).hexdigest()
    except Exception as e:
        sentry_sdk.capture_exception(e, extras={
            "component": "auth",
            "function": "get_tenant_tag",
            "user_id": user_id
        })
        raise
