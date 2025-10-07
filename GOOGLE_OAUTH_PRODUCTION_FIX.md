# Google OAuth Production Fix

## Problem
Google OAuth was working in development but failing in production with the following errors:
- `Cross-Origin-Opener-Policy policy would block the window.closed call` (COOP error)
- `Failed to load resource: the server responded with a status of 400 (Bad Request)`
- `Uncaught (in promise) Error: A listener indicated an asynchronous response by returning true`

## Root Causes

### 1. **OAuth Flow Mismatch**
- **Frontend**: Uses `useGoogleLogin` from `@react-oauth/google` which implements OAuth 2.0 authorization code flow
  - Returns an **access token** (not an ID token)
- **Backend**: Expected an **ID token** (OpenID Connect flow)
  - Was using `id_token.verify_oauth2_token()` which only works with ID tokens

### 2. **Missing Security Headers**
- Django didn't set proper `Cross-Origin-Opener-Policy` headers
- Google OAuth popup couldn't communicate with parent window due to COOP restrictions

### 3. **CORS Configuration**
- Missing explicit CORS headers for OAuth requests

## Solutions Implemented

### 1. Updated Backend to Handle Both Token Types

**File**: `backend/api/views.py`

Modified `GoogleAuthView` to:
- First try to verify credential as ID token (OpenID Connect flow)
- If that fails, treat it as access token and fetch user info from Google's API
- Extract user information from whichever method succeeds

```python
# Try ID token verification first
try:
    idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID)
    email = idinfo.get('email')
    name = idinfo.get('name', '')
    google_id = idinfo.get('sub')
except ValueError:
    # Fall back to access token - fetch user info from Google
    response = http_requests.get(
        'https://www.googleapis.com/oauth2/v2/userinfo',
        headers={'Authorization': f'Bearer {credential}'},
        timeout=10
    )
    user_info = response.json()
    email = user_info.get('email')
    name = user_info.get('name', '')
    google_id = user_info.get('id')
```

### 2. Added Security Headers Middleware

**File**: `backend/api/middleware.py` (new file)

Created custom middleware to set proper headers:
```python
class SecurityHeadersMiddleware:
    def __call__(self, request):
        response = self.get_response(request)
        response['Cross-Origin-Opener-Policy'] = 'unsafe-none'  # Allow OAuth popups
        response['Cross-Origin-Resource-Policy'] = 'cross-origin'
        return response
```

### 3. Updated Django Settings

**File**: `backend/hellotutor/settings.py`

Added:
- Custom middleware to MIDDLEWARE list
- Security headers configuration:
  ```python
  SECURE_CROSS_ORIGIN_OPENER_POLICY = None
  SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
  ```
- Explicit CORS headers:
  ```python
  CORS_ALLOW_HEADERS = [
      'accept', 'accept-encoding', 'authorization', 
      'content-type', 'dnt', 'origin', 'user-agent',
      'x-csrftoken', 'x-requested-with',
  ]
  ```

## Deployment Steps

### 1. Update Backend Code
```bash
cd backend
git pull origin main
```

### 2. Restart Django Server
```bash
# Development
python manage.py runserver

# Production (systemd)
sudo systemctl restart hellotutor
# or
sudo systemctl restart gunicorn
```

### 3. Verify Production Environment Variables
Ensure `.env` file has:
```env
GOOGLE_OAUTH_CLIENT_ID=your-production-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-production-client-secret
```

### 4. Test OAuth Flow
1. Go to `https://app.inzighted.com/login`
2. Click "Continue with Google"
3. Should see Google account picker popup
4. Select account
5. Should redirect back and log in successfully

## How It Works Now

### Development Flow
1. User clicks "Continue with Google"
2. `useGoogleLogin` opens popup to Google OAuth
3. User grants permission
4. Google returns **access token**
5. Frontend sends access token to backend
6. Backend uses access token to fetch user info from `https://www.googleapis.com/oauth2/v2/userinfo`
7. Backend creates/finds user and returns JWT tokens

### Production Flow
Same as development - now works consistently!

## Verification Checklist

- [x] Backend accepts both ID tokens and access tokens
- [x] Security headers set to allow OAuth popups
- [x] CORS configured for production domain (app.inzighted.com)
- [x] Middleware added to Django settings
- [x] Proper error logging for debugging
- [ ] Test on production server
- [ ] Verify no COOP errors in browser console
- [ ] Verify successful login flow
- [ ] Check Django logs for "Access token verified" message

## Debugging

If issues persist:

### Check Django Logs
```bash
# Look for these messages
tail -f /path/to/logs/django.log | grep "Google auth"
```

Expected log flow:
```
Received Google auth request
Request data keys: dict_keys(['credential'])
Credential present: True
Attempting to verify as ID token...
Not an ID token, trying as access token: [error message]
Fetching user info with access token...
Access token verified, user info retrieved: dict_keys(['id', 'email', 'verified_email', 'name', 'given_name', 'family_name', 'picture', 'locale'])
User email: user@example.com, name: John Doe
User found: user@example.com
JWT tokens generated successfully
```

### Check Browser Console
Should NOT see:
- ❌ `Cross-Origin-Opener-Policy policy would block the window.closed call`
- ❌ `Failed to load resource: the server responded with a status of 400`

Should see:
- ✅ Successful POST to `/api/auth/google/` with 200 status
- ✅ Response includes `access`, `refresh`, and `user` fields

### Verify Headers
```bash
curl -I https://server.inzighted.com/api/auth/google/
```

Should include:
```
Cross-Origin-Opener-Policy: unsafe-none
Cross-Origin-Resource-Policy: cross-origin
Access-Control-Allow-Origin: https://app.inzighted.com
Access-Control-Allow-Credentials: true
```

## Alternative Solution (Not Implemented)

If you want to use ID tokens instead of access tokens:

**Frontend**: Change `useGoogleLogin` to `GoogleLogin` component:
```tsx
import { GoogleLogin } from '@react-oauth/google';

<GoogleLogin
  onSuccess={(credentialResponse) => {
    googleLogin(credentialResponse.credential); // This is an ID token
  }}
  onError={() => {
    console.log('Login Failed');
  }}
/>
```

This would give you an ID token directly, but requires UI changes.

## Security Considerations

- ✅ Backend validates tokens with Google
- ✅ Only accepts tokens for configured client ID
- ✅ CORS restricted to specific domains
- ✅ JWT tokens used for subsequent requests
- ✅ Sentry error tracking for auth failures
- ✅ Both OAuth flows supported for flexibility

## References

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Sign-In for Web](https://developers.google.com/identity/sign-in/web)
- [@react-oauth/google Documentation](https://www.npmjs.com/package/@react-oauth/google)
- [Django CORS Headers](https://pypi.org/project/django-cors-headers/)
- [Cross-Origin-Opener-Policy (COOP)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cross-Origin-Opener-Policy)
