# Memos MCP Server

A streamable HTTP MCP (Model Context Protocol) server for Memos note-taking app, enabling seamless integration with AI assistants and other tools.

## Features

- 🚀 **FastMCP-based server** with streaming HTTP support
- 📝 **Create memos** with content and tags
- 🔍 **Search and list memos** with filtering capabilities  
- 🔗 **Access token authentication** for secure API access
- ⚡ **Async/await** for high performance
- 🐳 **Docker support** for easy deployment
- 📊 **Rate limiting** and error handling
- 🛠️ **CLI interface** for management and testing

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/ivanlee1999/memos-mcp.git
cd memos-mcp

# Install dependencies
pip install -e .
```

### 2. Configuration

Create a `.env` file with your Memos access token:

```bash
# Initialize configuration
memos-mcp init

# Edit the .env file and add your access token
```

To get your access token:
1. Go to your Memos instance and log in
2. Navigate to Settings page
3. Find "Access Tokens" section
4. Click "Create" button
5. Provide description (e.g., "MCP Server")
6. Set expiration date
7. Copy the generated token

### 3. Run the Server

```bash
# Start the server
memos-mcp serve

# Or with custom settings
memos-mcp serve --host 0.0.0.0 --port 8080 --log-level DEBUG
```

### 4. Test the Connection

```bash
# Test API connection
memos-mcp test

# Create a memo from CLI
memos-mcp create "This is my first memo" --tags "test,mcp"

# List recent memos
memos-mcp list --limit 5
```

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Create .env file first
memos-mcp init

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the server
docker-compose down
```

### Using Docker directly

```bash
# Build the image
docker build -t memos-mcp .

# Run the container
docker run -d \
  --name memos-mcp-server \
  -p 8000:8000 \
  -e MEMOS_ACCESS_TOKEN=your_token_here \
  -e MEMOS_BASE_URL=http://your-memos-instance.com \
  memos-mcp
```

## API Reference

The server provides the following MCP tools:

### `create_memo`
Create a new memo with content and optional tags.

**Parameters:**
- `request: CreateMemoRequest` - Memo creation request

**Example:**
```json
{
  "content": "Remember to review the quarterly reports",
  "tags": ["work", "important"],
  "source": "mcp_server"
}
```

### `list_memos`
List memos with pagination support.

**Parameters:**
- `limit: int` - Maximum number of memos (1-200, default: 50)
- `offset: int` - Number of memos to skip (default: 0)

### `search_memos`
Search memos by content and tags.

**Parameters:**
- `query: SearchQuery` - Search parameters

**Example:**
```json
{
  "query": "quarterly reports",
  "tags": ["work"],
  "limit": 10,
  "offset": 0
}
```

### `get_memo_by_id`
Get a specific memo by its ID.

**Parameters:**
- `memo_id: str` - The unique identifier of the memo

### `quick_memo`
Quickly create a memo with simple text and tags.

**Parameters:**
- `content: str` - The text content
- `tags: str` (optional) - Comma or space-separated tags

### `test_connection`
Test the connection to Flomo API.

### `get_server_info`
Get information about the MCP server.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MEMOS_ACCESS_TOKEN` | **Required** - Your Memos access token | - |
| `MEMOS_BASE_URL` | **Required** - Your Memos instance URL | - |
| `MEMOS_API_VERSION` | API version to use | `v1` |
| `MEMOS_TIMEOUT` | Request timeout in seconds | `30` |
| `MEMOS_MAX_RETRIES` | Maximum retry attempts | `3` |
| `SERVER_HOST` | Server host address | `localhost` |
| `SERVER_PORT` | Server port number | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CORS_ORIGINS` | Comma-separated CORS origins | - |
| `API_RATE_LIMIT` | Rate limit per minute | `100` |

## CLI Commands

```bash
# Server management
memos-mcp serve              # Start the server
memos-mcp init               # Create .env template
memos-mcp test               # Test API connection
memos-mcp info               # Show configuration

# Memo operations
memos-mcp create "content" --tags "tag1,tag2"  # Create memo
memos-mcp list --limit 10 --offset 0           # List memos
```

## Development

### Setup Development Environment

```bash
# Clone and install in development mode
git clone https://github.com/ivanlee1999/memos-mcp.git
cd memos-mcp
pip install -e ".[dev]"

# Run with auto-reload
memos-mcp serve --reload
```

### Project Structure

```
memos-mcp/
├── src/memos_mcp/
│   ├── __init__.py          # Package initialization
│   ├── server.py            # FastMCP server implementation
│   ├── client.py            # Memos API client
│   ├── models.py            # Pydantic data models
│   ├── config.py            # Configuration management
│   └── cli.py               # Command-line interface
├── pyproject.toml           # Project configuration
├── Dockerfile               # Container image
├── docker-compose.yml       # Container orchestration
└── README.md               # Documentation
```

### Code Quality

```bash
# Format code
black src/
isort src/

# Type checking
mypy src/

# Linting
flake8 src/

# Run tests
pytest
```

## Troubleshooting

### Common Issues

1. **Authentication Error**: Make sure your access token is correct and not expired
2. **Connection Failed**: Check if you can access your Memos instance from your network
3. **Rate Limited**: Wait a moment and try again, or increase retry delays
4. **Import Errors**: Make sure you've installed the package with `pip install -e .`

### Debug Mode

Run with debug logging to see detailed information:

```bash
memos-mcp serve --log-level DEBUG
```

### Health Check

The server provides a health check endpoint:

```bash
curl http://localhost:8000/health
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the Flomo API documentation

## Acknowledgments

- Based on the FastMCP framework
- Inspired by the Readwise Reader MCP server
- Uses the official Memos API