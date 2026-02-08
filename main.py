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
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, schedule the cleanup
            loop.create_task(close_http_client())
        else:
            # If loop is not running, run it to execute cleanup
            loop.run_until_complete(close_http_client())
    except Exception:
        # If there's no event loop or it's closed, try creating a new one
        try:
            asyncio.run(close_http_client())
        except Exception:
            pass  # Best effort cleanup


# Register cleanup handler
atexit.register(cleanup)

# --- Running the server ---

if __name__ == "__main__":
    try:
        mcp.run(transport="stdio")
    finally:
        # Ensure cleanup runs even if run() exits normally
        cleanup()
