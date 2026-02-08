"""Bangumi MCP Server - Model Context Protocol server for Bangumi TV API."""
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

# --- Running the server ---

if __name__ == "__main__":
    print("Starting Bangumi MCP Server...")
    mcp.run(transport="stdio")
    print("Bangumi MCP Server stopped.")
