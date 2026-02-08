"""OpenAPI specification resource."""
from pathlib import Path
from mcp.types import TextContent


def register(mcp):
    """Register OpenAPI resource with the MCP server."""

    @mcp.resource("api://bangumi/openapi")
    def get_bangumi_openapi_spec() -> TextContent:
        """
        Exposes the Bangumi API OpenAPI specification.

        This resource provides the detailed documentation for the Bangumi API calls,
        useful for understanding available endpoints, parameters, and responses.
        """
        file_path = Path(__file__).parent.parent.parent / "bangumi-tv-api.json"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                api_spec_content = f.read()
            return TextContent(type="text", text=api_spec_content)
        except FileNotFoundError:
            return TextContent(
                type="text", text="Error: bangumi-tv-api.json not found."
            )
        except Exception as e:
            return TextContent(
                type="text", text=f"Error reading bangumi-tv-api.json: {e}"
            )
