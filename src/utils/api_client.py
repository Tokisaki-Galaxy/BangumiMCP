"""HTTP client utilities for Bangumi API."""
import asyncio
import json
import os
from typing import Any, Dict, Optional

import httpx

from ..config import BANGUMI_API_BASE, USER_AGENT

# Shared httpx client for connection pooling
_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()


async def get_http_client() -> httpx.AsyncClient:
    """
    Get or create the shared HTTP client.
    
    Thread-safe singleton pattern for connection pooling.
    """
    global _client
    if _client is None:
        async with _client_lock:
            # Double-check after acquiring lock
            if _client is None:
                _client = httpx.AsyncClient(follow_redirects=False, timeout=30.0)
    return _client


async def close_http_client():
    """
    Close the shared HTTP client and release resources.
    
    Should be called during application shutdown to properly clean up
    network connections and resources.
    """
    global _client
    if _client is not None:
        async with _client_lock:
            if _client is not None:
                await _client.aclose()
                _client = None


async def make_bangumi_request(
    method: str,
    path: str,
    query_params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Any:
    """Make a request to the Bangumi API with proper headers and error handling."""
    request_headers = headers.copy() if headers else {}
    request_headers["User-Agent"] = USER_AGENT
    request_headers["Accept"] = "application/json"

    # Dynamically get token from environment to avoid stale imports
    bangumi_token = os.getenv("BANGUMI_TOKEN")
    if bangumi_token:
        request_headers["Authorization"] = f"Bearer {bangumi_token}"

    url = f"{BANGUMI_API_BASE}{path}"

    client = await get_http_client()
    try:
        response = await client.request(
            method=method,
            url=url,
            params=query_params,
            json=json_body,
            headers=request_headers,
        )

        # Handle redirect responses (e.g., image endpoints) without attempting JSON parsing
        # Only handle redirect statuses that are expected to carry a Location header
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("Location")
            if location:
                return {"Location": location}
            return {
                "error": f"{response.status_code} redirect without Location",
                "status_code": response.status_code,
            }

        # Handle other 3xx codes that shouldn't have a Location header
        if 300 <= response.status_code < 400:
            return {
                "error": f"Unexpected redirect status: {response.status_code}",
                "status_code": response.status_code,
            }

        response.raise_for_status()

        # Some successful responses (e.g., 204 No Content) may have an empty body; avoid JSON parsing then
        if response.status_code == 204 or not response.content:
            return None

        # Return the raw JSON response, let the calling tool handle its structure (dict or list)
        return response.json()
    except httpx.HTTPStatusError as e:
        error_msg = (
            f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        )
        # Try to parse the error response body if it's JSON
        try:
            error_details = e.response.json()
            return {
                "error": error_msg,
                "status_code": e.response.status_code,
                "details": error_details,
            }
        except json.JSONDecodeError:
            return {
                "error": error_msg,
                "status_code": e.response.status_code,
                "details": e.response.text,
            }
    except httpx.RequestError as e:
        error_msg = f"An error occurred while requesting {e.request.url!r}: {e}"
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        return {"error": error_msg}


def handle_api_error_response(response: Any) -> Optional[str]:
    """
    Checks if the API response indicates an error and returns a formatted error message.
    Handles both dictionary-based errors and returns from make_bangumi_request on failure.
    """
    # Check for error structure returned by make_bangumi_request on HTTPStatusError or RequestError
    if isinstance(response, dict) and (
        "error" in response or "status_code" in response
    ):
        # This is an error dictionary created by our helper
        status_code = response.get("status_code", "N/A")
        error_msg = response.get("error", "Unknown error during request.")
        details = response.get("details", "")
        return f"Bangumi API Request Error (Status {status_code}): {error_msg}. Details: {details}".strip()

    # Check for error structure returned by Bangumi API itself (often dictionaries)
    # Safely check if the response is a dictionary before accessing its keys
    if isinstance(response, dict):
        if "title" in response and "description" in response:
            # This looks like a common Bangumi error response structure
            error_title = response.get("title", "API Error")
            error_description = response.get("description", "No description provided.")
            # The API might return a status code in the body too, or rely on HTTP status
            return f"Bangumi API Error: {error_title}. {error_description}".strip()

        # Check if it's a dictionary but *not* empty and *doesn't* look like a success response from list endpoints
        # Check for specific error fields if structure varies
        # Add more checks here if other error dictionary formats are observed
        # Example: if "message" in response and "code" in response: return f"API Error {response['code']}: {response['message']}"
        return None  # If it's a dictionary but doesn't match known error formats, assume it's a valid data response for now

    # If it's not a dictionary, or it's a dictionary that doesn't match known error formats, assume it's not an error
    return None
