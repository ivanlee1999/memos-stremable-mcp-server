"""Memos API client implementation with authentication and error handling."""

import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
from .models import (
    Memo, 
    CreateMemoRequest, 
    SearchQuery, 
    MemosApiResponse, 
    ApiConfig
)

logger = logging.getLogger(__name__)


class MemosAPIError(Exception):
    """Base exception for Memos API errors."""
    pass


class MemosAuthenticationError(MemosAPIError):
    """Authentication related errors."""
    pass


class MemosRateLimitError(MemosAPIError):
    """Rate limiting errors."""
    pass


class MemosClient:
    """Async HTTP client for Memos API operations."""
    
    def __init__(self, config: ApiConfig):
        """Initialize the Memos client with configuration."""
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            headers = {
                "Authorization": f"Bearer {self.config.access_token}",
                "Content-Type": "application/json",
                "User-Agent": "memos-mcp/0.1.0",
            }
            
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(self.config.timeout),
                follow_redirects=True,
            )
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _make_request(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> MemosApiResponse:
        """Make an HTTP request with retry logic and error handling."""
        await self._ensure_client()
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self._client.request(method, url, **kwargs)
                
                # Handle rate limiting
                if response.status_code == 429:
                    if attempt < self.config.max_retries:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise MemosRateLimitError("Rate limit exceeded")
                
                # Handle authentication errors
                if response.status_code == 401:
                    raise MemosAuthenticationError("Invalid access token")
                
                # Parse response
                try:
                    data = response.json() if response.content else {}
                except json.JSONDecodeError:
                    data = {"raw_content": response.text}
                
                return MemosApiResponse(
                    status=response.status_code,
                    data=data,
                    success=200 <= response.status_code < 300,
                    message=data.get("message") if isinstance(data, dict) else None
                )
                
            except httpx.RequestError as e:
                if attempt < self.config.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise MemosAPIError(f"Request failed after {self.config.max_retries} retries: {e}")
        
        raise MemosAPIError("Unexpected error in request handling")
    
    async def create_memo(self, request: CreateMemoRequest) -> Memo:
        """Create a new memo using the Memos API."""
        # Format content with tags if provided
        content = request.content
        if request.tags:
            tags_str = " ".join(f"#{tag}" for tag in request.tags)
            content = f"{content} {tags_str}"
        
        payload = {
            "content": content,
            "visibility": request.visibility,
            "pinned": request.pinned
        }
        
        url = f"{self.config.base_url}/api/{self.config.api_version}/memos"
        response = await self._make_request("POST", url, json=payload)
        
        if not response.success:
            error_msg = response.data.get("message", "Failed to create memo")
            raise MemosAPIError(f"Create memo failed: {error_msg}")
        
        # Parse memo from API response
        memo_data = response.data
        return self._parse_memo_from_api(memo_data)
    
    async def get_all_memos(
        self, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Memo]:
        """Get all memos with pagination."""
        url = f"{self.config.base_url}/api/{self.config.api_version}/memos"
        params = {
            "pageSize": limit,
            "pageToken": str(offset) if offset > 0 else None
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        response = await self._make_request("GET", url, params=params)
        
        if not response.success:
            logger.warning(f"Failed to get memos: {response.data}")
            return []
        
        memos = []
        memo_list = response.data.get("memos", [])
        
        for memo_data in memo_list:
            try:
                memo = self._parse_memo_from_api(memo_data)
                memos.append(memo)
            except Exception as e:
                logger.warning(f"Failed to parse memo: {e}")
                continue
        
        return memos
    
    async def search_memos(self, query: SearchQuery) -> List[Memo]:
        """Search memos by content and tags."""
        url = f"{self.config.base_url}/api/{self.config.api_version}/memos"
        params = {
            "pageSize": query.limit,
            "pageToken": str(query.offset) if query.offset > 0 else None,
            "filter": self._build_search_filter(query)
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        response = await self._make_request("GET", url, params=params)
        
        if not response.success:
            logger.warning(f"Failed to search memos: {response.data}")
            # Fallback to client-side filtering
            return await self._client_side_search(query)
        
        memos = []
        memo_list = response.data.get("memos", [])
        
        for memo_data in memo_list:
            try:
                memo = self._parse_memo_from_api(memo_data)
                if self._matches_filters(memo, query):
                    memos.append(memo)
            except Exception as e:
                logger.warning(f"Failed to parse memo: {e}")
                continue
        
        return memos
    
    def _matches_filters(self, memo: Memo, query: SearchQuery) -> bool:
        """Check if memo matches additional filters."""
        # Date filtering
        if query.date_from and memo.created_at and memo.created_at < query.date_from:
            return False
        if query.date_to and memo.created_at and memo.created_at > query.date_to:
            return False
        
        # Tag filtering
        if query.tags and not any(tag in memo.tags for tag in query.tags):
            return False
        
        return True
    
    def _parse_memo_from_api(self, memo_data: Dict[str, Any]) -> Memo:
        """Parse memo from Memos API response data."""
        import re
        
        # Extract content and tags
        content = memo_data.get("content", "")
        
        # Extract hashtags from content
        tag_matches = re.findall(r'#(\w+)', content)
        tags = list(set(tag_matches))
        
        return Memo(
            id=memo_data.get("id"),
            uid=memo_data.get("uid"),
            name=memo_data.get("name"),
            row_status=memo_data.get("rowStatus"),
            creator_id=memo_data.get("creatorId"),
            creator_username=memo_data.get("creatorUsername"),
            created_ts=memo_data.get("createdTs"),
            updated_ts=memo_data.get("updatedTs"),
            display_ts=memo_data.get("displayTs"),
            content=content,
            visibility=memo_data.get("visibility", "PRIVATE"),
            tags=tags,
            pinned=memo_data.get("pinned", False),
            parent_id=memo_data.get("parentId"),
            resources=memo_data.get("resources", []),
            relations=memo_data.get("relations", []),
            reactions=memo_data.get("reactions", []),
            property=memo_data.get("property")
        )
    
    def _build_search_filter(self, query: SearchQuery) -> str:
        """Build Memos API filter string for search."""
        filters = []
        
        # Content search
        if query.query:
            filters.append(f'content.contains("{query.query}")')
        
        # Tag search
        if query.tags:
            tag_filters = [f'content.contains("#{tag}")' for tag in query.tags]
            filters.append(f'({" || ".join(tag_filters)})')
        
        # Date filters
        if query.date_from:
            timestamp = int(query.date_from.timestamp())
            filters.append(f'created_ts >= {timestamp}')
        
        if query.date_to:
            timestamp = int(query.date_to.timestamp())
            filters.append(f'created_ts <= {timestamp}')
        
        return " && ".join(filters) if filters else ""
    
    async def _client_side_search(self, query: SearchQuery) -> List[Memo]:
        """Fallback client-side search when server-side search fails."""
        all_memos = await self.get_all_memos(limit=query.limit * 2, offset=query.offset)
        
        filtered_memos = []
        query_lower = query.query.lower()
        
        for memo in all_memos:
            # Check content
            if query_lower in memo.content.lower():
                if self._matches_filters(memo, query):
                    filtered_memos.append(memo)
            # Check tags
            elif query.tags and any(tag in memo.tags for tag in query.tags):
                if self._matches_filters(memo, query):
                    filtered_memos.append(memo)
        
        return filtered_memos[:query.limit]
    
    async def test_connection(self) -> bool:
        """Test if the client can connect to Memos API."""
        try:
            # Try to get current user to test authentication
            url = f"{self.config.base_url}/api/{self.config.api_version}/user"
            response = await self._make_request("GET", url)
            return response.success
        except MemosAuthenticationError:
            return False
        except Exception as e:
            logger.warning(f"Connection test failed: {e}")
            return False
    
    async def get_memo_by_id(self, memo_id: int) -> Optional[Memo]:
        """Get a specific memo by its ID."""
        url = f"{self.config.base_url}/api/{self.config.api_version}/memos/{memo_id}"
        
        try:
            response = await self._make_request("GET", url)
            
            if not response.success:
                return None
            
            return self._parse_memo_from_api(response.data)
        except Exception as e:
            logger.warning(f"Failed to get memo {memo_id}: {e}")
            return None