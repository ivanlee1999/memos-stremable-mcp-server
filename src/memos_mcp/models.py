"""Pydantic models for Memos MCP server."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class Memo(BaseModel):
    """Represents a Memos memo."""
    
    id: Optional[int] = None
    uid: Optional[str] = None
    name: Optional[str] = None
    row_status: Optional[str] = Field(None, description="Row status (NORMAL, ARCHIVED)")
    creator_id: Optional[int] = None
    creator_username: Optional[str] = None
    created_ts: Optional[int] = None
    updated_ts: Optional[int] = None
    display_ts: Optional[int] = None
    content: str = Field(..., description="The main content of the memo")
    visibility: Optional[str] = Field("PRIVATE", description="Visibility (PRIVATE, PROTECTED, PUBLIC)")
    tags: List[str] = Field(default_factory=list, description="Tags associated with the memo")
    pinned: bool = Field(False, description="Whether the memo is pinned")
    parent_id: Optional[int] = Field(None, description="Parent memo ID for replies")
    resources: List[dict] = Field(default_factory=list, description="Attached resources")
    relations: List[dict] = Field(default_factory=list, description="Memo relations")
    reactions: List[dict] = Field(default_factory=list, description="Memo reactions")
    property: Optional[dict] = Field(None, description="Additional properties")
    
    @property
    def text(self) -> str:
        """Alias for content to maintain compatibility."""
        return self.content
    
    @property
    def created_at(self) -> Optional[datetime]:
        """Convert timestamp to datetime."""
        if self.created_ts:
            return datetime.fromtimestamp(self.created_ts)
        return None
    
    @property
    def updated_at(self) -> Optional[datetime]:
        """Convert timestamp to datetime."""
        if self.updated_ts:
            return datetime.fromtimestamp(self.updated_ts)
        return None
    
    @validator("tags", pre=True)
    def parse_tags(cls, v):
        """Parse tags from various input formats."""
        if isinstance(v, str):
            # Handle comma-separated or space-separated tags
            return [tag.strip().lstrip('#') for tag in v.replace(',', ' ').split() if tag.strip()]
        elif isinstance(v, list):
            return [str(tag).strip().lstrip('#') for tag in v if str(tag).strip()]
        return []

    @validator("text")
    def validate_text(cls, v):
        """Ensure text is not empty."""
        if not v or not v.strip():
            raise ValueError("Memo text cannot be empty")
        return v.strip()


class CreateMemoRequest(BaseModel):
    """Request model for creating a new memo."""
    
    content: str = Field(..., description="The content of the memo to create")
    visibility: str = Field("PRIVATE", description="Visibility (PRIVATE, PROTECTED, PUBLIC)")
    tags: Optional[List[str]] = Field(default_factory=list, description="Optional tags for the memo")
    pinned: bool = Field(False, description="Whether to pin the memo")
    
    @validator("content")
    def validate_content(cls, v):
        """Ensure content is not empty."""
        if not v or not v.strip():
            raise ValueError("Memo content cannot be empty")
        return v.strip()


class MemoResponse(BaseModel):
    """Standardized response for memo operations."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message about the operation")
    memo: Optional[Memo] = Field(None, description="The memo data if applicable")
    error: Optional[str] = Field(None, description="Error details if the operation failed")


class MemoListResponse(BaseModel):
    """Response model for listing memos."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    memos: List[Memo] = Field(..., description="List of memos")
    total: int = Field(..., description="Total number of memos")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Number of memos per page")
    has_more: bool = Field(False, description="Whether there are more memos available")
    error: Optional[str] = Field(None, description="Error details if the operation failed")


class SearchQuery(BaseModel):
    """Search parameters for finding memos."""
    
    query: str = Field(..., description="Search text to find in memo content")
    tags: Optional[List[str]] = Field(default_factory=list, description="Filter by specific tags")
    limit: int = Field(50, description="Maximum number of results to return", ge=1, le=200)
    offset: int = Field(0, description="Number of results to skip", ge=0)
    date_from: Optional[datetime] = Field(None, description="Filter memos created after this date")
    date_to: Optional[datetime] = Field(None, description="Filter memos created before this date")
    
    @validator("query")
    def validate_query(cls, v):
        """Ensure query is not empty."""
        if not v or not v.strip():
            raise ValueError("Search query cannot be empty")
        return v.strip()


class MemosApiResponse(BaseModel):
    """Raw response from Memos API."""
    
    status: int = Field(..., description="HTTP status code")
    data: Dict[str, Any] = Field(..., description="Response data from Memos API")
    success: bool = Field(..., description="Whether the API call was successful")
    message: Optional[str] = Field(None, description="API response message")


class ApiConfig(BaseModel):
    """Configuration for Memos API client."""
    
    access_token: str = Field(..., description="Access token for Memos API authentication")
    base_url: str = Field(..., description="Base URL for Memos instance")
    api_version: str = Field("v1", description="API version to use")
    timeout: int = Field(30, description="Request timeout in seconds", ge=1, le=300)
    max_retries: int = Field(3, description="Maximum number of retry attempts", ge=0, le=10)
    
    @validator("access_token")
    def validate_token(cls, v):
        """Ensure access token is provided."""
        if not v or not v.strip():
            raise ValueError("Access token is required")
        return v.strip()
    
    @validator("base_url")
    def validate_base_url(cls, v):
        """Ensure base URL is provided and properly formatted."""
        if not v or not v.strip():
            raise ValueError("Base URL is required")
        return v.rstrip('/')


class ServerConfig(BaseModel):
    """Configuration for the MCP server."""
    
    host: str = Field("localhost", description="Server host address")
    port: int = Field(8000, description="Server port number", ge=1, le=65535)
    log_level: str = Field("INFO", description="Logging level")
    cors_origins: List[str] = Field(default_factory=list, description="CORS allowed origins")
    api_rate_limit: int = Field(100, description="API rate limit per minute", ge=1)
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Ensure valid log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v.upper()