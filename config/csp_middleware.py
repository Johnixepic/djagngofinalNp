"""
Custom Content Security Policy middleware.
Implements CSP without requiring django-csp dependency.
"""
import secrets
from typing import Callable


class ContentSecurityPolicyMiddleware:
    """
    Adds Content-Security-Policy headers to responses.
    
    Supports nonce generation for inline scripts.
    Stores the nonce in request.csp_nonce for use in templates.
    """
    
    # Default policy directives
    DEFAULT_POLICY = {
        "default-src": ["'self'"],
        "script-src": ["'self'"],
        "style-src": ["'self'"],
        "img-src": ["'self'", "data:"],
        "font-src": ["'self'"],
        "connect-src": ["'self'"],
        "object-src": ["'none'"],
        "base-uri": ["'self'"],
        "form-action": ["'self'"],
        "frame-ancestors": ["'none'"],
    }
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request):
        # Generate a nonce for inline scripts
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce
        
        # Add nonce to script-src directive
        policy = self.DEFAULT_POLICY.copy()
        policy["script-src"] = list(policy["script-src"]) + [f"'nonce-{nonce}'"]
        
        # Build the CSP header string
        directives = []
        for directive, values in policy.items():
            directives.append(f"{directive} {' '.join(values)}")
        
        csp_header = "; ".join(directives)
        
        response = self.get_response(request)
        response["Content-Security-Policy"] = csp_header
        
        return response
