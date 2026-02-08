"""Bangumi MCP Server - Model Context Protocol server for Bangumi TV API."""
import asyncio
import atexit

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("bangumi-tv")

# Import and register all components
from src.resources import openapi_resource
from src.tools import (
    subject_tools,
    character_tools,
    person_tools,
    user_tools,
    collection_tools,
    revision_tools,
    index_tools,
)
from src.prompts import workflow_prompts
from src.utils.api_client import close_http_client

# Register resources
openapi_resource.register(mcp)

# Register tools (55 total)
subject_tools.register(mcp)
character_tools.register(mcp)
person_tools.register(mcp)
user_tools.register(mcp)
collection_tools.register(mcp)
revision_tools.register(mcp)
index_tools.register(mcp)

# Register prompts
workflow_prompts.register(mcp)


def cleanup():
    """Cleanup function to close HTTP client on shutdown."""
    try:
        # Try to use existing event loop if available
        try:
            loop = asyncio.get_running_loop()
            # Loop is running, we can't block here, cleanup will happen via atexit
            return
        except RuntimeError:
            # No running loop, we can safely create one
            pass
        
        # Try to get existing event loop (not running)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                # Loop is closed, create a new one
                asyncio.run(close_http_client())
            else:
                # Loop exists but not running, use it
                loop.run_until_complete(close_http_client())
        except Exception:
            # If all else fails, create new event loop
            try:
                asyncio.run(close_http_client())
            except Exception:
                pass  # Best effort cleanup
    except Exception:
        pass  # Silent failure for cleanup


# Register cleanup handler
atexit.register(cleanup)

# --- Running the server ---

if __name__ == "__main__":
    mcp.run(transport="stdio")
