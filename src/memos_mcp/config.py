"""Configuration management for Memos MCP server."""

import os
from typing import Optional
from dotenv import load_dotenv
from .models import ApiConfig, ServerConfig

# Load environment variables from .env file
load_dotenv()


def get_api_config() -> ApiConfig:
    """Get API configuration from environment variables."""
    access_token = os.getenv("MEMOS_ACCESS_TOKEN")
    if not access_token:
        raise ValueError(
            "MEMOS_ACCESS_TOKEN environment variable is required. "
            "Get your token from your Memos instance settings."
        )
    
    base_url = os.getenv("MEMOS_BASE_URL")
    if not base_url:
        raise ValueError(
            "MEMOS_BASE_URL environment variable is required. "
            "Set it to your Memos instance URL (e.g., http://localhost:5230)."
        )
    
    return ApiConfig(
        access_token=access_token,
        base_url=base_url,
        api_version=os.getenv("MEMOS_API_VERSION", "v1"),
        timeout=int(os.getenv("MEMOS_TIMEOUT", "30")),
        max_retries=int(os.getenv("MEMOS_MAX_RETRIES", "3")),
    )


def get_server_config() -> ServerConfig:
    """Get server configuration from environment variables."""
    cors_origins = []
    cors_env = os.getenv("CORS_ORIGINS", "")
    if cors_env:
        cors_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
    
    return ServerConfig(
        host=os.getenv("SERVER_HOST", "localhost"),
        port=int(os.getenv("SERVER_PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        cors_origins=cors_origins,
        api_rate_limit=int(os.getenv("API_RATE_LIMIT", "100")),
    )


def create_env_template() -> str:
    """Create a template .env file content."""
    return """# Memos MCP Server Configuration

# Required: Your Memos instance URL and access token
MEMOS_BASE_URL=http://localhost:5230
MEMOS_ACCESS_TOKEN=your_access_token_here

# Optional: Memos API configuration
MEMOS_API_VERSION=v1
MEMOS_TIMEOUT=30
MEMOS_MAX_RETRIES=3

# Optional: Server configuration
SERVER_HOST=localhost
SERVER_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
API_RATE_LIMIT=100

# Instructions for Memos setup:
# 1. Set your Memos instance URL:
#    - For self-hosted: http://localhost:5230 (default Docker port)
#    - For demo: https://demo.usememos.com
#    - For custom domain: https://your-memos-domain.com
# 2. Get your access token:
#    - Go to your Memos instance and log in
#    - Go to Settings page
#    - Find "Access Tokens" section
#    - Click "Create" button
#    - Provide description (e.g., "MCP Server")
#    - Set expiration date
#    - Copy the generated token
# 3. Replace "your_access_token_here" with your actual token
# 4. Adjust other settings as needed
"""


def validate_environment() -> None:
    """Validate that all required environment variables are set."""
    try:
        get_api_config()
        get_server_config()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nTo fix this, create a .env file with the following content:")
        print(create_env_template())
        raise