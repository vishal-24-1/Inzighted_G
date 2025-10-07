"""
Custom middleware for handling security headers required for Google OAuth.
"""

class SecurityHeadersMiddleware:
    """
    Middleware to add security headers that allow Google OAuth popup to work correctly.
    
    This middleware adds:
    - Cross-Origin-Opener-Policy: Removes restrictions on popup windows
    - Cross-Origin-Embedder-Policy: Allows embedding from trusted sources
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Allow OAuth popup windows to communicate
        # Setting to 'unsafe-none' allows popups to work
        response['Cross-Origin-Opener-Policy'] = 'unsafe-none'
        
        # Allow credentials and cross-origin requests
        response['Cross-Origin-Resource-Policy'] = 'cross-origin'
        
        return response
