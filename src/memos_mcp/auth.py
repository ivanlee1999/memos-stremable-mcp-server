"""Authentication middleware for Memos MCP server."""

import hashlib
import logging
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


def compute_token_hash(token: str) -> str:
    """Compute SHA256 hash of the access token."""
    return hashlib.sha256(token.encode()).hexdigest()


class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates SHA256 hash of access token from query parameter."""
    
    def __init__(self, app, access_token: str, enabled: bool = True):
        """
        Initialize the authentication middleware.
        
        Args:
            app: The ASGI application
            access_token: The actual access token to validate against
            enabled: Whether authentication is enabled (default: True)
        """
        super().__init__(app)
        self.expected_token_hash = compute_token_hash(access_token) if enabled else None
        self.enabled = enabled
        
        if enabled:
            logger.info("Token authentication enabled. Expected token hash: %s", 
                       self.expected_token_hash[:8] + "...")

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """
        Process the request and validate token if authentication is enabled.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain
            
        Returns:
            Response from the next handler or 401 if authentication fails
        """
        # Skip authentication if disabled
        if not self.enabled:
            return await call_next(request)
        
        # Extract token from query parameters
        provided_token_hash = request.query_params.get("token")
        
        if not provided_token_hash:
            logger.warning("Request rejected: Missing token query parameter from %s", 
                          request.client.host if request.client else "unknown")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authentication required",
                    "message": "Token query parameter is required. Access URL format: /mcp?token=<sha256_hash>",
                    "code": "MISSING_TOKEN"
                }
            )
        
        # Validate token hash
        if provided_token_hash != self.expected_token_hash:
            logger.warning("Request rejected: Invalid token hash from %s. Provided: %s, Expected: %s...", 
                          request.client.host if request.client else "unknown",
                          provided_token_hash[:8] + "..." if len(provided_token_hash) > 8 else provided_token_hash,
                          self.expected_token_hash[:8] + "...")
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authentication failed",
                    "message": "Invalid token provided",
                    "code": "INVALID_TOKEN"
                }
            )
        
        # Token is valid, proceed with the request
        logger.debug("Request authenticated successfully from %s", 
                    request.client.host if request.client else "unknown")
        return await call_next(request)


def create_auth_url(base_url: str, token: str, enabled: bool = True) -> str:
    """
    Create an authenticated URL with the token hash.
    
    Args:
        base_url: The base URL of the server
        token: The access token
        enabled: Whether authentication is enabled
        
    Returns:
        The complete URL with token parameter if auth is enabled, otherwise base URL
    """
    if not enabled:
        return base_url
    
    token_hash = compute_token_hash(token)
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}token={token_hash}"