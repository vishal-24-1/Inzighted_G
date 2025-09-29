import hmac
import hashlib
from django.conf import settings

def get_tenant_tag(user_id: str) -> str:
    """
    Generates a secure HMAC tag for a given user ID.
    """
    secret = settings.HMAC_SECRET
    if not secret:
        raise ValueError("HMAC_SECRET is not set in the environment.")
    
    return hmac.new(secret.encode('utf-8'), user_id.encode('utf-8'), hashlib.sha256).hexdigest()
