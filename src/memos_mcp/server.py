"""FastMCP server implementation for Memos with streaming endpoints."""

import asyncio
import logging
from typing import List, Optional, AsyncGenerator
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from pydantic import ValidationError

from .client import MemosClient, MemosAPIError, MemosAuthenticationError
from .config import get_api_config, validate_environment
from .models import (
    Memo,
    CreateMemoRequest,
    MemoResponse,
    MemoListResponse,
    SearchQuery,
    ApiConfig,
)
from .auth import TokenAuthMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global client instance
_memos_client: Optional[MemosClient] = None


@asynccontextmanager
async def get_memos_client() -> AsyncGenerator[MemosClient, None]:
    """Get or create a Memos client instance."""
    global _memos_client
    
    if _memos_client is None:
        try:
            config = get_api_config()
            _memos_client = MemosClient(config)
        except Exception as e:
            logger.error(f"Failed to create Memos client: {e}")
            raise
    
    try:
        yield _memos_client
    finally:
        # Keep client alive for reuse
        pass


async def cleanup_client() -> None:
    """Cleanup the global client instance."""
    global _memos_client
    if _memos_client:
        await _memos_client.close()
        _memos_client = None


# Initialize FastMCP app
app = FastMCP("Memos MCP Server")


@app.tool()
async def create_memo(request: CreateMemoRequest) -> MemoResponse:
    """
    Create a new memo in Memos.
    
    Args:
        request: The memo creation request containing content and optional tags
        
    Returns:
        MemoResponse with the created memo details
    """
    try:
        async with get_memos_client() as client:
            memo = await client.create_memo(request)
            
            return MemoResponse(
                success=True,
                message="Memo created successfully",
                memo=memo
            )
            
    except MemosAuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        return MemoResponse(
            success=False,
            message="Authentication failed. Please check your access token.",
            error=str(e)
        )
    except MemosAPIError as e:
        logger.error(f"Memos API error: {e}")
        return MemoResponse(
            success=False,
            message="Failed to create memo",
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating memo: {e}")
        return MemoResponse(
            success=False,
            message="An unexpected error occurred",
            error=str(e)
        )


@app.tool()
async def list_memos(
    limit: int = 50,
    offset: int = 0
) -> MemoListResponse:
    """
    List memos with pagination support.
    
    Args:
        limit: Maximum number of memos to return (1-200)
        offset: Number of memos to skip
        
    Returns:
        MemoListResponse with the list of memos
    """
    # Validate parameters
    if limit < 1 or limit > 200:
        return MemoListResponse(
            success=False,
            memos=[],
            total=0,
            error="Limit must be between 1 and 200"
        )
    
    if offset < 0:
        return MemoListResponse(
            success=False,
            memos=[],
            total=0,
            error="Offset must be non-negative"
        )
    
    try:
        async with get_memos_client() as client:
            memos = await client.get_all_memos(limit=limit, offset=offset)
            
            return MemoListResponse(
                success=True,
                memos=memos,
                total=len(memos),
                page=offset // limit + 1,
                page_size=limit,
                has_more=len(memos) == limit
            )
            
    except MemosAuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        return MemoListResponse(
            success=False,
            memos=[],
            total=0,
            error="Authentication failed. Please check your access token."
        )
    except MemosAPIError as e:
        logger.error(f"Memos API error: {e}")
        return MemoListResponse(
            success=False,
            memos=[],
            total=0,
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error listing memos: {e}")
        return MemoListResponse(
            success=False,
            memos=[],
            total=0,
            error=str(e)
        )


@app.tool()
async def search_memos(query: SearchQuery) -> MemoListResponse:
    """
    Search memos by content and tags.
    
    Args:
        query: Search parameters including text query, tags, and filters
        
    Returns:
        MemoListResponse with matching memos
    """
    try:
        async with get_memos_client() as client:
            memos = await client.search_memos(query)
            
            return MemoListResponse(
                success=True,
                memos=memos,
                total=len(memos),
                page=query.offset // query.limit + 1,
                page_size=query.limit,
                has_more=len(memos) == query.limit
            )
            
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return MemoListResponse(
            success=False,
            memos=[],
            total=0,
            error=f"Invalid search parameters: {e}"
        )
    except MemosAuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        return MemoListResponse(
            success=False,
            memos=[],
            total=0,
            error="Authentication failed. Please check your access token."
        )
    except MemosAPIError as e:
        logger.error(f"Memos API error: {e}")
        return MemoListResponse(
            success=False,
            memos=[],
            total=0,
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error searching memos: {e}")
        return MemoListResponse(
            success=False,
            memos=[],
            total=0,
            error=str(e)
        )


@app.tool()
async def get_memo_by_id(memo_id: int) -> MemoResponse:
    """
    Get a specific memo by its ID.
    
    Args:
        memo_id: The unique identifier of the memo
        
    Returns:
        MemoResponse with the memo details
    """
    if not memo_id or memo_id <= 0:
        return MemoResponse(
            success=False,
            message="Valid memo ID is required",
            error="Invalid memo ID"
        )
    
    try:
        async with get_memos_client() as client:
            memo = await client.get_memo_by_id(memo_id)
            
            if memo:
                return MemoResponse(
                    success=True,
                    message="Memo found",
                    memo=memo
                )
            else:
                return MemoResponse(
                    success=False,
                    message="Memo not found",
                    error=f"No memo found with ID: {memo_id}"
                )
            
    except MemosAuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        return MemoResponse(
            success=False,
            message="Authentication failed. Please check your access token.",
            error=str(e)
        )
    except MemosAPIError as e:
        logger.error(f"Memos API error: {e}")
        return MemoResponse(
            success=False,
            message="Failed to get memo",
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error getting memo: {e}")
        return MemoResponse(
            success=False,
            message="An unexpected error occurred",
            error=str(e)
        )


@app.tool()
async def quick_memo(content: str, tags: Optional[str] = None) -> MemoResponse:
    """
    Quickly create a memo with simple text content and optional tags.
    
    Args:
        content: The text content of the memo
        tags: Optional comma-separated or space-separated tags
        
    Returns:
        MemoResponse with the created memo details
    """
    if not content or not content.strip():
        return MemoResponse(
            success=False,
            message="Content is required",
            error="Memo content cannot be empty"
        )
    
    # Parse tags
    tag_list = []
    if tags:
        tag_list = [tag.strip().lstrip('#') for tag in tags.replace(',', ' ').split() if tag.strip()]
    
    request = CreateMemoRequest(
        content=content.strip(),
        tags=tag_list,
        visibility="PRIVATE"
    )
    
    return await create_memo(request)


@app.tool()
async def test_connection() -> dict:
    """
    Test the connection to Memos API.
    
    Returns:
        Dictionary with connection status and details
    """
    try:
        async with get_memos_client() as client:
            is_connected = await client.test_connection()
            
            if is_connected:
                return {
                    "success": True,
                    "message": "Successfully connected to Memos API",
                    "status": "connected"
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to connect to Memos API",
                    "status": "disconnected",
                    "error": "Connection test failed"
                }
                
    except MemosAuthenticationError as e:
        return {
            "success": False,
            "message": "Authentication failed",
            "status": "authentication_error",
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Connection test error: {e}")
        return {
            "success": False,
            "message": "Connection test failed",
            "status": "error",
            "error": str(e)
        }


# Health check removed - not supported in FastMCP


@app.tool()
async def get_server_info() -> dict:
    """
    Get information about the MCP server.
    
    Returns:
        Dictionary with server information
    """
    try:
        config = get_api_config()
        return {
            "name": "Memos MCP Server",
            "version": "0.1.0",
            "description": "A streamable HTTP MCP server for Memos note-taking app",
            "base_url": config.base_url,
            "api_version": config.api_version,
            "tools": [
                "create_memo",
                "list_memos", 
                "search_memos",
                "get_memo_by_id",
                "quick_memo",
                "test_connection",
                "get_server_info"
            ]
        }
    except Exception as e:
        return {
            "name": "Memos MCP Server",
            "version": "0.1.0",
            "error": str(e)
        }


# Startup and shutdown events removed - not supported in FastMCP


# Export the app for running
def create_app():
    """Create and return the FastMCP ASGI app with optional authentication."""
    import os
    
    # Get the base FastMCP HTTP app
    http_app = app.http_app()
    
    # Check if authentication should be enabled
    auth_enabled = os.getenv("ENABLE_TOKEN_AUTH", "true").lower() in ("true", "1", "yes")
    
    if auth_enabled:
        try:
            # Get access token for authentication
            api_config = get_api_config()
            
            # Wrap the HTTP app with authentication middleware
            authenticated_app = TokenAuthMiddleware(
                http_app,
                access_token=api_config.access_token,
                enabled=auth_enabled
            )
            
            logger.info("HTTP authentication middleware enabled")
            return authenticated_app
        except Exception as e:
            logger.warning("Could not enable authentication: %s. Running without authentication.", e)
    
    return http_app

# Export for uvicorn
http_app = create_app()


if __name__ == "__main__":
    import uvicorn
    from .config import get_server_config
    
    try:
        server_config = get_server_config()
        # Use FastMCP's built-in server instead of uvicorn directly
        app.run(
            transport="http",
            host=server_config.host,
            port=server_config.port
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        exit(1)