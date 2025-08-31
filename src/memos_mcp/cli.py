"""Command-line interface for Memos MCP server."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
import uvicorn
from rich.console import Console
from rich.table import Table
from rich.text import Text

from .config import get_api_config, get_server_config, create_env_template, validate_environment
from .client import MemosClient
from .models import CreateMemoRequest

app = typer.Typer(
    name="memos-mcp",
    help="Memos MCP Server - A streamable HTTP MCP server for Memos note-taking app"
)
console = Console()


@app.command()
def serve(
    host: str = typer.Option(None, "--host", "-h", help="Server host"),
    port: int = typer.Option(None, "--port", "-p", help="Server port"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload for development"),
    log_level: str = typer.Option(None, "--log-level", "-l", help="Log level (DEBUG, INFO, WARNING, ERROR)")
):
    """Start the Memos MCP server."""
    try:
        validate_environment()
        server_config = get_server_config()
        
        # Override with CLI arguments if provided
        host = host or server_config.host
        port = port or server_config.port
        log_level = log_level or server_config.log_level
        
        console.print(f"🚀 Starting Memos MCP Server on {host}:{port}", style="green bold")
        console.print(f"📝 Log level: {log_level}", style="blue")
        
        if reload:
            console.print("🔄 Auto-reload enabled", style="yellow")
        
        # Import and run the FastMCP server directly
        from .server import app
        
        if reload:
            # For development with reload, we can use uvicorn
            uvicorn.run(
                "memos_mcp.server:http_app",
                host=host,
                port=port,
                log_level=log_level.lower(),
                reload=reload
            )
        else:
            # For production, use FastMCP's built-in server
            app.run(
                transport="http",
                host=host,
                port=port
            )
        
    except Exception as e:
        console.print(f"❌ Failed to start server: {e}", style="red bold")
        sys.exit(1)


@app.command()
def init():
    """Initialize configuration by creating a .env file template."""
    env_file = Path(".env")
    
    if env_file.exists():
        overwrite = typer.confirm("A .env file already exists. Overwrite it?")
        if not overwrite:
            console.print("❌ Initialization cancelled", style="yellow")
            return
    
    try:
        env_content = create_env_template()
        env_file.write_text(env_content)
        
        console.print("✅ Created .env file template", style="green bold")
        console.print("📝 Please edit the .env file and add your Memos access token", style="blue")
        console.print(f"📍 File location: {env_file.absolute()}", style="blue")
        
    except Exception as e:
        console.print(f"❌ Failed to create .env file: {e}", style="red bold")
        sys.exit(1)


@app.command()
def test():
    """Test connection to Memos API."""
    async def _test_connection():
        try:
            validate_environment()
            config = get_api_config()
            
            console.print("🔗 Testing connection to Memos API...", style="blue")
            
            async with MemosClient(config) as client:
                is_connected = await client.test_connection()
                
                if is_connected:
                    console.print("✅ Successfully connected to Memos API", style="green bold")
                    return True
                else:
                    console.print("❌ Failed to connect to Memos API", style="red bold")
                    return False
                    
        except Exception as e:
            console.print(f"❌ Connection test failed: {e}", style="red bold")
            return False
    
    success = asyncio.run(_test_connection())
    sys.exit(0 if success else 1)


@app.command()
def create(
    content: str = typer.Argument(..., help="The content of the memo"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
):
    """Create a new memo."""
    async def _create_memo():
        try:
            validate_environment()
            config = get_api_config()
            
            # Parse tags
            tag_list = []
            if tags:
                tag_list = [tag.strip().lstrip('#') for tag in tags.split(',') if tag.strip()]
            
            request = CreateMemoRequest(
                content=content,
                tags=tag_list
            )
            
            console.print("📝 Creating memo...", style="blue")
            
            async with MemosClient(config) as client:
                memo = await client.create_memo(request)
                
                console.print("✅ Memo created successfully!", style="green bold")
                
                # Display memo details
                table = Table(title="Created Memo")
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="green")
                
                table.add_row("Content", memo.get_text())
                table.add_row("Tags", ", ".join(memo.tags) if memo.tags else "None")
                table.add_row("Visibility", memo.visibility or "PRIVATE")
                if memo.get_created_at():
                    table.add_row("Created", memo.get_created_at().strftime("%Y-%m-%d %H:%M:%S"))
                
                console.print(table)
                return True
                
        except Exception as e:
            console.print(f"❌ Failed to create memo: {e}", style="red bold")
            return False
    
    success = asyncio.run(_create_memo())
    sys.exit(0 if success else 1)


@app.command()
def list(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of memos to show"),
    offset: int = typer.Option(0, "--offset", "-o", help="Number of memos to skip"),
):
    """List recent memos."""
    async def _list_memos():
        try:
            validate_environment()
            config = get_api_config()
            
            console.print(f"📋 Fetching {limit} memos...", style="blue")
            
            async with MemosClient(config) as client:
                memos = await client.get_all_memos(limit=limit, offset=offset)
                
                if not memos:
                    console.print("📭 No memos found", style="yellow")
                    return True
                
                # Display memos in a table
                table = Table(title=f"Recent Memos (showing {len(memos)})")
                table.add_column("ID", style="dim")
                table.add_column("Content", max_width=50)
                table.add_column("Tags", style="cyan")
                table.add_column("Created", style="green")
                
                for memo in memos:
                    content = memo.get_text()[:47] + "..." if len(memo.get_text()) > 50 else memo.get_text()
                    tags = ", ".join(memo.tags) if memo.tags else "-"
                    created = memo.get_created_at().strftime("%m-%d %H:%M") if memo.get_created_at() else "-"
                    
                    table.add_row(
                        memo.id or "-",
                        content,
                        tags,
                        created
                    )
                
                console.print(table)
                return True
                
        except Exception as e:
            console.print(f"❌ Failed to list memos: {e}", style="red bold")
            return False
    
    success = asyncio.run(_list_memos())
    sys.exit(0 if success else 1)


@app.command()
def info():
    """Show server configuration and status."""
    try:
        validate_environment()
        api_config = get_api_config()
        server_config = get_server_config()
        
        # Configuration table
        config_table = Table(title="Server Configuration")
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="green")
        
        config_table.add_row("Server Host", server_config.host)
        config_table.add_row("Server Port", str(server_config.port))
        config_table.add_row("Log Level", server_config.log_level)
        config_table.add_row("API Rate Limit", f"{server_config.api_rate_limit}/min")
        config_table.add_row("Memos Base URL", api_config.base_url)
        config_table.add_row("API Version", api_config.api_version)
        config_table.add_row("Request Timeout", f"{api_config.timeout}s")
        config_table.add_row("Max Retries", str(api_config.max_retries))
        
        console.print(config_table)
        
        # Access token status
        token_text = Text()
        if api_config.access_token:
            token_text.append("✅ Access token configured", style="green")
        else:
            token_text.append("❌ Access token not configured", style="red")
        
        console.print(token_text)
        
    except Exception as e:
        console.print(f"❌ Failed to get configuration: {e}", style="red bold")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()