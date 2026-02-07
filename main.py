import os
import json
from pathlib import Path
from typing import Any, List, Dict, Optional
from enum import Enum, IntEnum  # Import Enum and IntEnum

import httpx
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP, Context, Image
from mcp.types import TextContent  # Corrected import location for TextContent

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("bangumi-tv")

# --- Constants ---
BANGUMI_API_BASE = "https://api.bgm.tv"
USER_AGENT = "BangumiMCP/1.0.0 (https://github.com/Ukenn2112/BangumiMCP)"
BANGUMI_TOKEN = os.getenv("BANGUMI_TOKEN")


# --- Bangumi API Enum Definitions ---
class SubjectType(IntEnum):
    """
    条目类型
    1 = book, 2 = anime, 3 = music, 4 = game, 6 = real
    """

    BOOK = 1
    ANIME = 2
    MUSIC = 3
    GAME = 4
    REAL = 6


class EpType(IntEnum):
    """
    章节类型
    0 = 本篇, 1 = 特别篇, 2 = OP, 3 = ED, 4 = 预告/宣传/广告, 5 = MAD, 6 = 其他
    """

    MAIN_STORY = 0
    SP = 1
    OP = 2
    ED = 3
    PV = 4
    MAD = 5
    OTHER = 6


class CharacterType(IntEnum):
    """
    type of a character
    1 = 角色, 2 = 机体, 3 = 舰船, 4 = 组织...
    """

    CHARACTER = 1
    MECHANIC = 2
    SHIP = 3
    ORGANIZATION = 4


class PersonType(IntEnum):
    """
    type of a person or company
    1 = 个人, 2 = 公司, 3 = 组合
    """

    INDIVIDUAL = 1
    CORPORATION = 2
    ASSOCIATION = 3


class PersonCareer(str, Enum):
    """
    Career of a person
    'producer', 'mangaka', 'artist', 'seiyu', 'writer', 'illustrator', 'actor'
    """

    PRODUCER = "producer"
    MANGAKA = "mangaka"
    ARTIST = "artist"
    SEIYU = "seiyu"
    WRITER = "writer"
    ILLUSTRATOR = "illustrator"
    ACTOR = "actor"


class BloodType(IntEnum):
    """
    Blood type of a person.
    1=A, 2=B, 3=AB, 4=O
    """

    A = 1
    B = 2
    AB = 3
    O = 4


class CollectionType(IntEnum):
    """
    Collection status type.
    1=Wish, 2=Collect, 3=Doing, 4=On Hold, 5=Dropped
    """

    WISH = 1
    COLLECT = 2
    DOING = 3
    ON_HOLD = 4
    DROPPED = 5


class EpisodeCollectionType(IntEnum):
    """
    Episode collection status type.
    0=None, 1=Watched
    """

    NONE = 0
    WATCHED = 1


# --- Helper Function for API Requests ---
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

    if BANGUMI_TOKEN:
        request_headers["Authorization"] = f"Bearer {BANGUMI_TOKEN}"

    url = f"{BANGUMI_API_BASE}{path}"

    async with httpx.AsyncClient(follow_redirects=False) as client:
        try:
            print(
                f"DEBUG: Making {method} request to {url} with params={query_params}, json={json_body}"
            )
            response = await client.request(
                method=method,
                url=url,
                params=query_params,
                json=json_body,
                headers=request_headers,
                timeout=30.0,
            )

            # Handle 302 redirect for image endpoints
            if response.status_code == 302:
                location = response.headers.get("Location")
                if location:
                    return {"Location": location}
                return {"error": "302 redirect without Location", "status_code": 302}

            response.raise_for_status()
            # Return the raw JSON response, let the calling tool handle its structure (dict or list)
            json_response = response.json()
            print(
                f"DEBUG: Received response (type: {type(json_response)}, keys/length: {list(json_response.keys()) if isinstance(json_response, dict) else len(json_response) if isinstance(json_response, list) else 'N/A'})"
            )
            return json_response
        except httpx.HTTPStatusError as e:
            error_msg = (
                f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
            )
            print(f"ERROR: {error_msg}")
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
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"An unexpected error occurred: {e}"
            print(f"ERROR: {error_msg}")
            return {"error": error_msg}


## --- Error Handling Helper Correction ---
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
        pass  # If it's a dictionary but doesn't match known error formats, assume it's a valid data response for now

    # If it's not a dictionary, or it's a dictionary that doesn't match known error formats, assume it's not an error
    return None


# --- Formatting Functions (Same as before) ---
def format_subject_summary(subject: Dict[str, Any]) -> str:
    """Formats a subject dictionary into a readable summary string."""
    name = subject.get("name")
    name_cn = subject.get("name_cn")
    subject_type = subject.get("type")
    subject_id = subject.get("id")
    score = subject.get("rating", {}).get("score")  # Access Nested Score
    rank = subject.get("rating", {}).get("rank")  # Access Nested Rank
    summary = subject.get("short_summary") or subject.get("summary", "")

    try:
        type_str = (
            SubjectType(subject_type).name
            if subject_type is not None
            else "Unknown Type"
        )
    except ValueError:
        type_str = f"Unknown Type ({subject_type})"

    formatted_string = f"[{type_str}] {name_cn or name} (ID: {subject_id})\n"
    if score is not None:
        formatted_string += f"  Score: {score}\n"
    if rank is not None:
        formatted_string += f"  Rank: {rank}\n"
    if summary:
        formatted_summary = summary  # [:200] + '...' if len(summary) > 200 else summary
        formatted_string += f"  Summary: {formatted_summary}\n"

    # Add images URL if available (for potential LLM multi-modal future use or user info)
    images = subject.get("images")
    if images and images.get("common"):
        formatted_string += f"  Image: {images.get('common')}\n"  # Or 'grid', 'large', 'medium', 'small' depending on preference

    return formatted_string


def format_character_summary(character: Dict[str, Any]) -> str:
    """Formats a character dictionary into a readable summary string."""
    character_id = character.get("id")
    name = character.get("name")
    char_type = character.get("type")  # Integer enum
    summary = character.get("short_summary") or character.get("summary", "")

    try:
        type_str = (
            CharacterType(char_type).name if char_type is not None else "Unknown Type"
        )
    except ValueError:
        type_str = f"Unknown Type ({char_type})"

    formatted_string = f"[{type_str}] {name} (ID: {character_id})\n"
    if summary:
        formatted_summary = summary  # [:200] + '...' if len(summary) > 200 else summary
        formatted_string += f"  Summary: {formatted_summary}\n"

    images = character.get("images")
    if images and images.get("common"):
        formatted_string += f"  Image: {images.get('common')}\n"

    return formatted_string


def format_person_summary(person: Dict[str, Any]) -> str:
    """Formats a person dictionary into a readable summary string."""
    person_id = person.get("id")
    name = person.get("name")
    person_type = person.get("type")  # Integer enum
    career = person.get("career")  # List of string enums
    summary = person.get("short_summary") or person.get("summary", "")

    try:
        type_str = (
            PersonType(person_type).name if person_type is not None else "Unknown Type"
        )
    except ValueError:
        type_str = f"Unknown Type ({person_type})"

    formatted_string = f"[{type_str}] {name} (ID: {person_id})\n"
    if career:
        formatted_string += f"  Career: {', '.join(career)}\n"
    if summary:
        formatted_summary = summary  # [:200] + '...' if len(summary) > 200 else summary
        formatted_string += f"  Summary: {formatted_summary}\n"

    images = person.get("images")
    if images and images.get("common"):
        formatted_string += f"  Image: {images.get('common')}\n"

    return formatted_string


# --- Resources ---


@mcp.resource("api://bangumi/openapi")
def get_bangumi_openapi_spec() -> TextContent:  # Explicitly return TextContent
    """
    Exposes the Bangumi API OpenAPI specification.

    This resource provides the detailed documentation for the Bangumi API calls,
    useful for understanding available endpoints, parameters, and responses.
    """
    file_path = Path(__file__).parent / "bangumi-tv-api.json"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            api_spec_content = f.read()
        return TextContent(text=api_spec_content, mimeType="application/json")
    except FileNotFoundError:
        return TextContent(
            text="Error: bangumi-tv-api.json not found.", mimeType="text/plain"
        )
    except Exception as e:
        return TextContent(
            text=f"Error reading bangumi-tv-api.json: {e}", mimeType="text/plain"
        )


# --- Tools (Mapping API Endpoints) ---


@mcp.tool()
async def get_daily_broadcast() -> str:
    """
    Get the daily broadcast schedule for the current week on Bangumi.

    Returns:
        The broadcast schedule grouped by day of the week, or an error message.
    """
    response = await make_bangumi_request(method="GET", path="/calendar")

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a list of dictionaries, where each dict represents a day
    if not isinstance(response, list):
        return f"Unexpected API response format for /calendar: {response}"

    calendar_data = response
    if not calendar_data:
        return "Could not retrieve daily broadcast calendar."

    formatted_schedule = ["Daily Broadcast Schedule:"]

    # The API returns days in a specific order, we can just iterate through the list
    for day_entry in calendar_data:
        weekday = day_entry.get("weekday", {})
        items = day_entry.get("items", [])

        # Get readable weekday name, default to English if others are missing
        weekday_name = (
            weekday.get("cn")
            or weekday.get("ja")
            or weekday.get("en")
            or f"Weekday ID {weekday.get('id', 'N/A')}"
        )
        formatted_schedule.append(f"\n--- {weekday_name} ---")

        if not items:
            formatted_schedule.append("  No broadcasts scheduled.")
        else:
            formatted_results = [format_subject_summary(s) for s in items]
            results_text = (
                f"Found {len(items)} subjects.\n"
                + "---\n".join(formatted_results)
            )
            formatted_schedule.append(results_text)

    return "\n".join(formatted_schedule)


@mcp.tool()
async def search_subjects(
    keyword: str,
    subject_type: Optional[SubjectType] = None,
    sort: str = "match",
    limit: int = 30,
    offset: int = 0,
) -> str:
    """
    Search for subjects on Bangumi.

    Supported Subject Types (integer enum):
    1: Book, 2: Anime, 3: Music, 4: Game, 6: Real

    Supported Sort orders (string enum):
    'match', 'heat', 'rank', 'score'

    Args:
        keyword: The search keyword.
        subject_type: Optional filter by subject type. Use integer values (1, 2, 3, 4, 6).
        sort: Optional sort order. Defaults to 'match'.
        limit: Pagination limit. Max 50. Defaults to 30.
        offset: Pagination offset. Defaults to 0.

    Returns:
        Formatted search results or an error message.
    """
    json_body = {"keyword": keyword, "sort": sort, "filter": {}}
    if subject_type is not None:
        json_body["filter"]["type"] = [int(subject_type)]

    params = {"limit": min(limit, 50), "offset": offset}  # Enforce max limit

    response = await make_bangumi_request(
        method="POST",
        path="/v0/search/subjects",
        query_params=params,  # Pass limit/offset as query params
        json_body=json_body,  # Pass keyword and filter as JSON body
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a dictionary with 'data' and 'total'
    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format for search_subjects: {response}"

    subjects = response.get("data", [])
    if not subjects:
        return f"No subjects found for keyword '{keyword}'."

    formatted_results = [format_subject_summary(s) for s in subjects]
    total = response.get("total", 0)
    results_text = (
        f"Found {len(subjects)} subjects (Total matched: {total}).\n"
        + "---\n".join(formatted_results)
    )

    return results_text


@mcp.tool()
async def browse_subjects(
    subject_type: SubjectType,
    cat: Optional[int] = None,
    series: Optional[bool] = None,
    platform: Optional[str] = None,
    sort: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    limit: int = 30,
    offset: int = 0,
) -> str:
    """
    Browse subjects by type and filters.

    Supported Subject Types (integer enum, required):
    1: Book, 2: Anime, 3: Music, 4: Game, 6: Real

    Supported Categories (integer enums for 'cat', specific to SubjectType):
    Book (type=1): Other=0, Comic=1001, Novel=1002, Illustration=1003
    Anime (type=2): Other=0, TV=1, OVA=2, Movie=3, WEB=5
    Game (type=4): Other=0, Games=4001, Software=4002, DLC=4003, Tabletop=4005
    Real (type=6): Other=0, JP=1, EN=2, CN=3, TV=6001, Movie=6002, Live=6003, Show=6004

    Supported Sort orders (string for 'sort', optional):
    'date', 'rank' (Default sorting may vary if 'sort' is not provided)

    Args:
        subject_type: Required filter by subject type (integer value from SubjectType enum).
        cat: Optional filter by subject category (integer value from category enums).
        series: Optional filter for books (type=1). True for series main entry.
        platform: Optional filter for games (type=4). E.g. 'Web', 'PC', 'PS4'.
        sort: Optional sort order ('date' or 'rank').
        year: Optional filter by year.
        month: Optional filter by month (1-12).
        limit: Pagination limit. Max 50. Defaults to 30.
        offset: Pagination offset. Defaults to 0.

    Returns:
        Formatted list of subjects or an error message.
    """
    query_params: Dict[str, Any] = {
        "type": int(subject_type),
        "limit": min(limit, 50),
        "offset": offset,
    }
    if cat is not None:
        query_params["cat"] = cat
    if series is not None:
        query_params["series"] = series
    if platform is not None:
        query_params["platform"] = platform
    if sort is not None:
        query_params["sort"] = sort
    if year is not None:
        query_params["year"] = year
    if month is not None:
        query_params["month"] = month

    response = await make_bangumi_request(
        method="GET", path="/v0/subjects", query_params=query_params
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a dictionary with 'data' and 'total'
    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format for browse_subjects: {response}"

    subjects = response.get("data", [])
    if not subjects:
        return f"No subjects found for the given criteria."

    formatted_results = [format_subject_summary(s) for s in subjects]
    total = response.get("total", 0)
    results_text = f"Found {len(subjects)} subjects (Total: {total}).\n" + "---\n".join(
        formatted_results
    )

    return results_text


@mcp.tool()
async def get_subject_details(subject_id: int) -> str:
    """
    Get details of a specific subject (e.g., anime, book, game).

    Args:
        subject_id: The ID of the subject.

    Returns:
        Formatted subject details or an error message.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/subjects/{subject_id}"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a dictionary
    if not isinstance(response, dict):
        return f"Unexpected API response format for get_subject_details: {response}"

    subject = response
    infobox = subject.get("infobox")
    tags = subject.get("tags")

    details_text = f"Subject Details (ID: {subject_id}):\n"
    details_text += f"  Name: {subject.get('name')}\n"
    if subject.get("name_cn"):
        details_text += f"  Chinese Name: {subject.get('name_cn')}\n"
    try:
        details_text += f"  Type: {SubjectType(subject.get('type')).name if subject.get('type') is not None else 'Unknown Type'}\n"
    except ValueError:
        details_text += f"  Type: Unknown Type ({subject.get('type')})\n"

    if subject.get("date"):
        details_text += f"  Date: {subject.get('date')}\n"
    if subject.get("platform"):
        details_text += f"  Platform: {subject.get('platform')}\n"
    if subject.get("volumes"):
        details_text += f"  Volumes: {subject.get('volumes')}\n"
    if subject.get("eps") is not None:  # Could be 0
        details_text += f"  Episodes (Wiki): {subject.get('eps')}\n"
    if subject.get("total_episodes"):
        details_text += f"  Episodes (DB): {subject.get('total_episodes')}\n"

    details_text += f"  Summary:\n{subject.get('summary')}\n"

    if subject.get("rating", {}).get("score") is not None:
        details_text += f"  Score: {subject['rating'].get('score')} (Votes: {subject['rating'].get('total')})\n"
    if subject.get("rating", {}).get("rank") is not None:
        details_text += f"  Rank: {subject['rating'].get('rank')}\n"

    if tags:
        tags_list = [f"{t['name']} ({t['count']})" for t in tags]
        details_text += f"  Tags: {', '.join(tags_list)}\n"

    if infobox:
        details_text += (
            "  Infobox: (Details available in raw response, potentially complex)\n"
        )

    if "collection" in subject:  # requires auth and user had collected it
        collection = subject["collection"]
        details_text += f"  Collection (Total Users): Wish: {collection.get('wish',0)}, Collected: {collection.get('collect',0)}, Doing: {collection.get('doing',0)}, On Hold: {collection.get('on_hold',0)}, Dropped: {collection.get('dropped',0)}\n"

    images = subject.get("images")
    if images and images.get("large"):
        details_text += f"  Cover Image: {images.get('large')}\n"

    return details_text


@mcp.tool()
async def get_subject_image(
    subject_id: int, image_type: str = "large"
) -> str:
    """
    Get the image URL for a subject.

    Supported image types:
    small, grid, large, medium, common

    Args:
        subject_id: The ID of the subject.
        image_type: The type of image to get. Defaults to 'large'.

    Returns:
        The image URL or an error message.
    """
    if image_type not in ["small", "grid", "large", "medium", "common"]:
        return f"Invalid image_type: {image_type}. Must be one of: small, grid, large, medium, common"

    response = await make_bangumi_request(
        method="GET",
        path=f"/v0/subjects/{subject_id}/image",
        query_params={"type": image_type},
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if isinstance(response, dict) and "Location" in response:
        return f"Subject Image URL: {response['Location']}"

    return f"Could not retrieve image for subject ID {subject_id}"


@mcp.tool()
async def get_subject_persons(subject_id: int) -> str:
    """
    List persons (staff, cast) related to a subject.

    Args:
        subject_id: The ID of the subject.

    Returns:
        Formatted list of related persons or an error message.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/subjects/{subject_id}/persons"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a list of persons
    if not isinstance(response, list):
        return f"Unexpected API response format for get_subject_persons: {response}"

    persons = response
    if not persons:
        return f"No persons found related to subject ID {subject_id}."

    formatted_results = []
    for person in persons:
        name = person.get("name")
        person_id = person.get("id")
        relation = person.get("relation")  # e.g., "导演", "动画制作", "声优"
        career = ", ".join(
            person.get("career", []) or []
        )  # person.get('career') could be None or empty list
        eps = person.get("eps")  # Participation in episodes/tracks for THIS subject

        # Safely get person type name if available and is valid enum value
        person_type_int = person.get("type")
        person_type_str = "Unknown Type"
        if person_type_int is not None:
            try:
                person_type_str = PersonType(person_type_int).name
            except ValueError:
                person_type_str = f"Unknown Type ({person_type_int})"

        formatted_results.append(
            f"Person ID: {person_id}, Name: {name}, Type: {person_type_str}, Relation (in subject): {relation}, Overall Career: {career}, Participating Episodes/Tracks: {eps}"
        )

    return "Related Persons:\n" + "\n---\n".join(formatted_results)


@mcp.tool()
async def get_subject_characters(subject_id: int) -> str:
    """
    List characters related to a subject.

    Args:
        subject_id: The ID of the subject.

    Returns:
        Formatted list of related characters or an error message.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/subjects/{subject_id}/characters"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a list of characters
    if not isinstance(response, list):
        return f"Unexpected API response format for get_subject_characters: {response}"

    characters = response
    if not characters:
        return f"No characters found related to subject ID {subject_id}."

    formatted_results = []
    for character in characters:
        name = character.get("name")
        char_id = character.get("id")
        relation = character.get("relation")
        actors = ", ".join(
            [a.get("name") for a in character.get("actors", []) if a.get("name")] or []
        )

        # Safely get character type name
        char_type_int = character.get("type")
        char_type_str = "Unknown Type"
        if char_type_int is not None:
            try:
                char_type_str = CharacterType(char_type_int).name
            except ValueError:
                char_type_str = f"Unknown Type ({char_type_int})"

        formatted_results.append(
            f"Character ID: {char_id}, Name: {name}, Type: {char_type_str}, Relation (in subject): {relation}, Voice Actors: {actors}"
        )

    return "Related Characters:\n" + "\n---\n".join(formatted_results)


@mcp.tool()
async def get_subject_relations(subject_id: int) -> str:
    """
    List related subjects (sequels, prequels, adaptations) for a subject.

    Args:
        subject_id: The ID of the subject.

    Returns:
        Formatted list of related subjects or an error message.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/subjects/{subject_id}/subjects"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a list of related subjects
    if not isinstance(response, list):
        return f"Unexpected API response format for get_subject_relations: {response}"

    related_subjects = response
    if not related_subjects:
        return f"No related subjects found for subject ID {subject_id}."

    formatted_results = []
    for rel_subject in related_subjects:
        name = rel_subject.get("name")
        name_cn = rel_subject.get("name_cn")
        rel_id = rel_subject.get("id")

        # Safely get subject type string
        rel_type_int = rel_subject.get("type")
        rel_type_str = "Unknown Type"
        if rel_type_int is not None:
            try:
                rel_type_str = SubjectType(rel_type_int).name
            except ValueError:
                rel_type_str = f"Unknown Type ({rel_type_int})"

        relation = rel_subject.get("relation")

        formatted_results.append(
            f"Subject ID: {rel_id}, Name: {name_cn or name}, Type: {rel_type_str}, Relation: {relation}"
        )

    return "Related Subjects:\n" + "\n---\n".join(formatted_results)


@mcp.tool()
async def get_episodes(
    subject_id: int,
    episode_type: Optional[EpType] = None,
    limit: int = 100,
    offset: int = 0,
) -> str:
    """
    List episodes for a subject.

    Supported Episode Types (integer enum):
    0: MainStory, 1: SP, 2: OP, 3: ED, 4: PV, 5: MAD, 6: Other

    Args:
        subject_id: The ID of the subject.
        episode_type: Optional filter by episode type (integer value from EpType enum).
        limit: Pagination limit. Max 200. Defaults to 100.
        offset: Pagination offset. Defaults to 0.

    Returns:
        Formatted list of episodes or an error message.
    """
    query_params: Dict[str, Any] = {
        "subject_id": subject_id,
        "limit": min(limit, 200),
        "offset": offset,
    }
    if episode_type is not None:
        query_params["type"] = int(episode_type)

    response = await make_bangumi_request(
        method="GET", path="/v0/episodes", query_params=query_params
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a dictionary with 'data' and 'total'
    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format for get_episodes: {response}"

    episodes = response.get("data", [])
    if not episodes:
        return f"No episodes found for subject ID {subject_id} with the given criteria."

    formatted_results = []
    for ep in episodes:
        ep_id = ep.get("id")
        name = ep.get("name")
        name_cn = ep.get("name_cn")
        sort = ep.get("sort")

        ep_type_int = ep.get("type")
        ep_type_str = "Unknown Type"
        if ep_type_int is not None:
            try:
                ep_type_str = EpType(ep_type_int).name
            except ValueError:
                ep_type_str = f"Unknown Type ({ep_type_int})"

        airdate = ep.get("airdate")

        formatted_results.append(
            f"Episode ID: {ep_id}, Type: {ep_type_str}, Number: {sort}, Name: {name_cn or name}, Airdate: {airdate}"
        )

    total = response.get("total", 0)
    results_text = f"Found {len(episodes)} episodes (Total: {total}).\n" + "---\n".join(
        formatted_results
    )

    return results_text


@mcp.tool()
async def get_episode_details(episode_id: int) -> str:
    """
    Get details of a specific episode.

    Args:
        episode_id: The ID of the episode.

    Returns:
        Formatted episode details or an error message.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/episodes/{episode_id}"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a dictionary
    if not isinstance(response, dict):
        return f"Unexpected API response format for get_episode_details: {response}"

    episode = response  # Response is the episode dictionary directly

    details_text = f"Episode Details (ID: {episode_id}):\n"
    details_text += f"  Subject ID: {episode.get('subject_id')}\n"
    ep_type_int = episode.get("type")
    ep_type_str = "Unknown Type"
    if ep_type_int is not None:
        try:
            ep_type_str = EpType(ep_type_int).name
        except ValueError:
            ep_type_str = f"Unknown Type ({ep_type_int})"

    details_text += f"  Type: {ep_type_str}\n"
    details_text += f"  Number: {episode.get('sort')}\n"
    if episode.get("ep") is not None:
        details_text += f"  Subject Episode Number: {episode.get('ep')}\n"
    details_text += f"  Name: {episode.get('name')}\n"
    if episode.get("name_cn"):
        details_text += f"  Chinese Name: {episode.get('name_cn')}\n"
    details_text += f"  Airdate: {episode.get('airdate')}\n"
    if episode.get("duration"):
        details_text += f"  Duration: {episode.get('duration')} ({episode.get('duration_seconds', 0)}s)\n"
    if episode.get("disc"):
        details_text += f"  Disc: {episode.get('disc')}\n"
    details_text += f"  Comment Count: {episode.get('comment')}\n"
    details_text += f"  Description:\n{episode.get('desc')}\n"

    return details_text


@mcp.tool()
async def search_characters(
    keyword: str, limit: int = 30, offset: int = 0, nsfw_filter: Optional[bool] = None
) -> str:
    """
    Search for characters on Bangumi.

    Supported Character Types (integer enum in result):
    1: Character, 2: Mechanic, 3: Ship, 4: Organization

    Args:
        keyword: The search keyword.
        limit: Pagination limit. Defaults to 30.
        offset: Pagination offset. Defaults to 0.
        nsfw_filter: Optional NSFW filter (boolean). Set to True to include, False to exclude. Requires authorization for non-default behavior.

    Returns:
        Formatted search results or an error message.
    """
    json_body = {"keyword": keyword, "filter": {}}
    if nsfw_filter is not None:
        json_body["filter"]["nsfw"] = nsfw_filter  # Filter is in JSON body

    params = {"limit": limit, "offset": offset}

    response = await make_bangumi_request(
        method="POST",
        path="/v0/search/characters",
        query_params=params,
        json_body=json_body,
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a dictionary with 'data' and 'total'
    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format for search_characters: {response}"

    characters = response.get("data", [])
    if not characters:
        return f"No characters found for keyword '{keyword}'."

    formatted_results = [format_character_summary(c) for c in characters]
    total = response.get("total", 0)
    results_text = (
        f"Found {len(characters)} characters (Total matched: {total}).\n"
        + "---\n".join(formatted_results)
    )

    return results_text


@mcp.tool()
async def get_character_details(character_id: int) -> str:
    """
    Get details of a specific character.

    Args:
        character_id: The ID of the character.

    Returns:
        Formatted character details or an error message.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/characters/{character_id}"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a dictionary
    if not isinstance(response, dict):
        return f"Unexpected API response format for get_character_details: {response}"

    character = response
    infobox = character.get("infobox")

    details_text = f"Character Details (ID: {character_id}):\n"
    details_text += f"  Name: {character.get('name')}\n"
    char_type_int = character.get("type")
    char_type_str = "Unknown Type"
    if char_type_int is not None:
        try:
            char_type_str = CharacterType(char_type_int).name
        except ValueError:
            char_type_str = f"Unknown Type ({char_type_int})"

    details_text += f"  Type: {char_type_str}\n"
    details_text += f"  Summary:\n{character.get('summary')}\n"
    details_text += f"  Locked: {character.get('locked')}\n"

    if character.get("gender"):
        details_text += f"  Gender: {character.get('gender')}\n"
    if character.get("blood_type") is not None:
        try:
            details_text += (
                f"  Blood Type: {BloodType(character.get('blood_type')).name}\n"
            )
        except ValueError:
            details_text += f"  Blood Type: Unknown ({character.get('blood_type')})\n"

    if character.get("birth_year"):
        details_text += f"  Birth Date: {character.get('birth_year')}-{character.get('birth_mon')}-{character.get('birth_day')}\n"

    if infobox:
        details_text += (
            "  Infobox: (Details available in raw response, potentially complex)\n"
        )

    stat = character.get("stat", {})
    details_text += f"  Comments: {stat.get('comments', 0)}, Collections: {stat.get('collects', 0)}\n"

    images = character.get("images")
    if images and images.get("large"):
        details_text += f"  Image: {images.get('large')}\n"

    return details_text


@mcp.tool()
async def get_character_subjects(character_id: int) -> str:
    """
    List subjects (e.g., anime, games) where a character appears.

    Args:
        character_id: The ID of the character.

    Returns:
        Formatted list of related subjects or an error message.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/characters/{character_id}/subjects"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a list of subjects
    if not isinstance(response, list):
        return f"Unexpected API response format for get_character_subjects: {response}"

    related_subjects = response
    if not related_subjects:
        return f"No subjects found related to character ID {character_id}."

    formatted_results = []
    for rel_subject in related_subjects:
        name = rel_subject.get("name")
        name_cn = rel_subject.get("name_cn")
        rel_id = rel_subject.get("id")
        rel_type_int = rel_subject.get("type")
        try:
            rel_type_str = (
                SubjectType(rel_type_int).name
                if rel_type_int is not None
                else "Unknown Type"
            )
        except ValueError:
            rel_type_str = f"Unknown Type ({rel_type_int})"

        staff_info = rel_subject.get(
            "staff"
        )  # Staff refers to the role of the char in the subject e.g. "主角"

        formatted_results.append(
            f"Subject ID: {rel_id}, Name: {name_cn or name}, Type: {rel_type_str}, Role/Staff (in subject): {staff_info}"
        )

    return "Subjects This Character Appears In:\n" + "\n---\n".join(formatted_results)


@mcp.tool()
async def get_character_persons(character_id: int) -> str:
    """
    List persons (e.g., voice actors) related to a character.

    Args:
        character_id: The ID of the character.

    Returns:
        Formatted list of related persons or an error message.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/characters/{character_id}/persons"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a list of persons
    if not isinstance(response, list):
        return f"Unexpected API response format for get_character_persons: {response}"

    persons = response
    if not persons:
        return f"No persons found related to character ID {character_id}."

    formatted_results = []
    for person in persons:
        name = person.get("name")
        person_id = person.get("id")
        person_type_int = person.get("type")
        try:
            person_type_str = (
                PersonType(person_type_int).name
                if person_type_int is not None
                else "Unknown Type"
            )
        except ValueError:
            person_type_str = f"Unknown Type ({person_type_int})"

        staff_info = person.get("staff")  # Role of the person for this character (e.g.,

        formatted_results.append(
            f"Person ID: {person_id}, Name: {name}, Type: {person_type_str}, Role (for character): {staff_info}"
        )

    return "Persons Related to This Character:\n" + "\n---\n".join(formatted_results)


@mcp.tool()
async def get_character_image(
    character_id: int, image_type: str = "large"
) -> str:
    """
    Get the image URL for a character.

    Supported image types:
    small, grid, large, medium

    Args:
        character_id: The ID of the character.
        image_type: The type of image to get. Defaults to 'large'.

    Returns:
        The image URL or an error message.
    """
    if image_type not in ["small", "grid", "large", "medium"]:
        return f"Invalid image_type: {image_type}. Must be one of: small, grid, large, medium"

    response = await make_bangumi_request(
        method="GET",
        path=f"/v0/characters/{character_id}/image",
        query_params={"type": image_type},
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if isinstance(response, dict) and "Location" in response:
        return f"Character Image URL: {response['Location']}"

    return f"Could not retrieve image for character ID {character_id}"


@mcp.tool()
async def collect_character(character_id: int) -> str:
    """
    Collect (favorite) a character for the current user.

    Requires authentication (BANGUMI_TOKEN).

    Args:
        character_id: The ID of the character to collect.

    Returns:
        Success message or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    response = await make_bangumi_request(
        method="POST", path=f"/v0/characters/{character_id}/collect"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # 204 No Content means success
    return f"Successfully collected character ID {character_id}."


@mcp.tool()
async def uncollect_character(character_id: int) -> str:
    """
    Remove a character from the current user's collection.

    Requires authentication (BANGUMI_TOKEN).

    Args:
        character_id: The ID of the character to uncollect.

    Returns:
        Success message or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    response = await make_bangumi_request(
        method="DELETE", path=f"/v0/characters/{character_id}/collect"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    return f"Successfully uncollected character ID {character_id}."


@mcp.tool()
async def search_persons(
    keyword: str,
    limit: int = 30,
    offset: int = 0,
    career_filter: Optional[List[PersonCareer]] = None,
) -> str:
    """
    Search for persons or companies on Bangumi.

    Supported Person Types (integer enum in result):
    1: Individual, 2: Corporation, 3: Association

    Supported Career Filters (string enum):
    'producer', 'mangaka', 'artist', 'seiyu', 'writer', 'illustrator', 'actor'

    Args:
        keyword: The search keyword.
        limit: Pagination limit. Defaults to 30.
        offset: Pagination offset. Defaults to 0.
        career_filter: Optional filter by person career (list of strings from PersonCareer enum).

    Returns:
        Formatted search results or an error message.
    """
    json_body = {"keyword": keyword, "filter": {}}
    if career_filter:
        # Ensure string values for the API call using the enum values
        formatted_careers = [
            c.value if isinstance(c, PersonCareer) else str(c) for c in career_filter
        ]
        json_body["filter"]["career"] = formatted_careers  # Filter is in JSON body

    params = {"limit": limit, "offset": offset}  # Query parameters for the POST request

    response = await make_bangumi_request(
        method="POST",
        path="/v0/search/persons",
        query_params=params,
        json_body=json_body,
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a dictionary with 'data' and 'total'
    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format for search_persons: {response}"

    persons = response.get("data", [])
    if not persons:
        return f"No persons found for keyword '{keyword}'."

    formatted_results = [format_person_summary(p) for p in persons]
    total = response.get("total", 0)
    results_text = (
        f"Found {len(persons)} persons (Total matched: {total}).\n"
        + "---\n".join(formatted_results)
    )

    return results_text


@mcp.tool()
async def get_person_details(person_id: int) -> str:
    """
    Get details of a specific person or company.

    Args:
        person_id: The ID of the person/company.

    Returns:
        Formatted person details or an error message.
    """
    response = await make_bangumi_request(method="GET", path=f"/v0/persons/{person_id}")

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a dictionary
    if not isinstance(response, dict):
        return f"Unexpected API response format for get_person_details: {response}"

    person = response
    infobox = person.get("infobox")

    details_text = f"Person Details (ID: {person_id}):\n"
    details_text += f"  Name: {person.get('name')}\n"
    person_type_int = person.get("type")
    person_type_str = "Unknown Type"
    if person_type_int is not None:
        try:
            person_type_str = PersonType(person_type_int).name
        except ValueError:
            person_type_str = f"Unknown Type ({person_type_int})"

    details_text += f"  Type: {person_type_str}\n"
    details_text += f"  Summary:\n{person.get('summary')}\n"
    details_text += f"  Locked: {person.get('locked')}\n"
    details_text += f"  Careers: {', '.join(person.get('career') or [])}\n"

    if person.get("gender"):
        details_text += f"  Gender: {person.get('gender')}\n"
    if person.get("blood_type") is not None:
        try:
            details_text += (
                f"  Blood Type: {BloodType(person.get('blood_type')).name}\n"
            )
        except ValueError:
            details_text += f"  Blood Type: Unknown ({person.get('blood_type')})\n"

    if person.get("birth_year"):
        details_text += f"  Birth Date: {person.get('birth_year')}-{person.get('birth_mon')}-{person.get('birth_day')}\n"

    if infobox:
        details_text += (
            "  Infobox: (Details available in raw response, potentially complex)\n"
        )

    stat = person.get("stat", {})
    details_text += f"  Comments: {stat.get('comments', 0)}, Collections: {stat.get('collects', 0)}\n"

    images = person.get("images")
    if images and images.get("large"):
        details_text += f"  Image: {images.get('large')}\n"

    return details_text


@mcp.tool()
async def get_person_subjects(person_id: int) -> str:
    """
    List subjects (e.g., anime, games) a person is related to (e.g., worked on).

    Args:
        person_id: The ID of the person.

    Returns:
        Formatted list of related subjects or an error message.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/persons/{person_id}/subjects"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a list of related subjects
    if not isinstance(response, list):
        return f"Unexpected API response format for get_person_subjects: {response}"

    related_subjects = response
    if not related_subjects:
        return f"No subjects found related to person ID {person_id}."

    formatted_results = []
    for rel_subject in related_subjects:
        name = rel_subject.get("name")
        name_cn = rel_subject.get("name_cn")
        rel_id = rel_subject.get("id")
        rel_type_int = rel_subject.get("type")
        try:
            rel_type_str = (
                SubjectType(rel_type_int).name
                if rel_type_int is not None
                else "Unknown Type"
            )
        except ValueError:
            rel_type_str = f"Unknown Type ({rel_type_int})"

        staff_info = rel_subject.get(
            "staff"
        )  # Role of the person in the subject e.g. "导演"

        formatted_results.append(
            f"Subject ID: {rel_id}, Name: {name_cn or name}, Type: {rel_type_str}, Role/Staff: {staff_info}"
        )

    return "Subjects This Person is Related To:\n" + "\n---\n".join(formatted_results)


@mcp.tool()
async def get_person_characters(person_id: int) -> str:
    """
    List characters voiced or portrayed by a person (e.g., voice actor, actor).

    Args:
        person_id: The ID of the person.

    Returns:
        Formatted list of related characters or an error message.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/persons/{person_id}/characters"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    # Expecting a list of characters
    if not isinstance(response, list):
        return f"Unexpected API response format for get_person_characters: {response}"

    characters = response
    if not characters:
        return f"No characters found related to person ID {person_id}."

    formatted_results = []
    for character in characters:
        name = character.get("name")
        char_id = character.get("id")
        char_type_int = character.get("type")
        try:
            char_type_str = (
                CharacterType(char_type_int).name
                if char_type_int is not None
                else "Unknown Type"
            )
        except ValueError:
            char_type_str = f"Unknown Type ({char_type_int})"

        staff_info = character.get(
            "staff"
        )  # Role of the person for this character (e.g., Voice Actor name)

        formatted_results.append(
            f"Character ID: {char_id}, Name: {name}, Type: {char_type_str}, Role: {staff_info}"
        )

    return "Characters Related to This Person:\n" + "\n---\n".join(formatted_results)


@mcp.tool()
async def get_person_image(
    person_id: int, image_type: str = "large"
) -> str:
    """
    Get the image URL for a person.

    Supported image types:
    small, grid, large, medium

    Args:
        person_id: The ID of the person.
        image_type: The type of image to get. Defaults to 'large'.

    Returns:
        The image URL or an error message.
    """
    if image_type not in ["small", "grid", "large", "medium"]:
        return f"Invalid image_type: {image_type}. Must be one of: small, grid, large, medium"

    response = await make_bangumi_request(
        method="GET",
        path=f"/v0/persons/{person_id}/image",
        query_params={"type": image_type},
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if isinstance(response, dict) and "Location" in response:
        return f"Person Image URL: {response['Location']}"

    return f"Could not retrieve image for person ID {person_id}"


@mcp.tool()
async def collect_person(person_id: int) -> str:
    """
    Collect (favorite) a person for the current user.

    Requires authentication (BANGUMI_TOKEN).

    Args:
        person_id: The ID of the person to collect.

    Returns:
        Success message or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    response = await make_bangumi_request(
        method="POST", path=f"/v0/persons/{person_id}/collect"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    return f"Successfully collected person ID {person_id}."


@mcp.tool()
async def uncollect_person(person_id: int) -> str:
    """
    Remove a person from the current user's collection.

    Requires authentication (BANGUMI_TOKEN).

    Args:
        person_id: The ID of the person to uncollect.

    Returns:
        Success message or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    response = await make_bangumi_request(
        method="DELETE", path=f"/v0/persons/{person_id}/collect"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    return f"Successfully uncollected person ID {person_id}."


# --- User & Collection Functions ---


@mcp.tool()
async def get_user_info(username: str) -> str:
    """
    Get user information by username.

    Args:
        username: The username to look up.

    Returns:
        Formatted user info or error.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/users/{username}"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict):
        return f"Unexpected API response format: {response}"

    user = response
    details = f"User: {username}\n"
    details += f"  ID: {user.get('id')}\n"
    details += f"  Nickname: {user.get('nickname')}\n"
    if user.get('sign'):
        details += f"  Sign: {user.get('sign')}\n"

    return details


@mcp.tool()
async def get_user_avatar(username: str, avatar_type: str = "large") -> str:
    """
    Get the avatar URL for a user.

    Supported avatar types:
    small, large, medium

    Args:
        username: The username.
        avatar_type: The type of avatar. Defaults to 'large'.

    Returns:
        The avatar URL or error.
    """
    if avatar_type not in ["small", "large", "medium"]:
        return f"Invalid avatar_type: {avatar_type}. Must be one of: small, large, medium"

    response = await make_bangumi_request(
        method="GET",
        path=f"/v0/users/{username}/avatar",
        query_params={"type": avatar_type},
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if isinstance(response, dict) and "Location" in response:
        return f"User Avatar URL: {response['Location']}"

    return f"Could not retrieve avatar for user {username}"


@mcp.tool()
async def get_current_user() -> str:
    """
    Get the current user's information.

    Requires authentication (BANGUMI_TOKEN).

    Returns:
        Current user info or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    response = await make_bangumi_request(method="GET", path="/v0/me")

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict):
        return f"Unexpected API response format: {response}"

    user = response
    details = f"Current User:\n"
    details += f"  ID: {user.get('id')}\n"
    details += f"  Username: {user.get('username')}\n"
    details += f"  Nickname: {user.get('nickname')}\n"
    if user.get('email'):
        details += f"  Email: {user.get('email')}\n"
    if user.get('reg_time'):
        details += f"  Registered: {user.get('reg_time')}\n"

    return details


@mcp.tool()
async def get_user_collections(
    username: str,
    subject_type: Optional[SubjectType] = None,
    collection_type: Optional[int] = None,
    limit: int = 30,
    offset: int = 0,
) -> str:
    """
    Get the collection list for a user.

    Collection types:
    1: Wish, 2: Collect, 3: Doing, 4: On Hold, 5: Dropped

    Args:
        username: The username.
        subject_type: Optional filter by subject type.
        collection_type: Optional filter by collection status (1-5).
        limit: Pagination limit. Defaults to 30.
        offset: Pagination offset. Defaults to 0.

    Returns:
        Formatted collection list or error.
    """
    query_params: Dict[str, Any] = {"limit": min(limit, 50), "offset": offset}
    if subject_type is not None:
        query_params["subject_type"] = int(subject_type)
    if collection_type is not None:
        query_params["type"] = collection_type

    response = await make_bangumi_request(
        method="GET",
        path=f"/v0/users/{username}/collections",
        query_params=query_params,
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format: {response}"

    collections = response.get("data", [])
    if not collections:
        return f"No collections found for user {username}."

    status_map = {1: "Wish", 2: "Collected", 3: "Doing", 4: "On Hold", 5: "Dropped"}
    lines = [f"Collections for user {username}:"]
    lines.append(f"Total: {response.get('total', 0)}\n")

    for item in collections:
        subj = item.get("subject", {})
        name = subj.get("name_cn") or subj.get("name")
        subj_type = subj.get("type")
        status = status_map.get(item.get("type"), "Unknown")

        try:
            type_str = SubjectType(subj_type).name if subj_type else "?"
        except ValueError:
            type_str = f"?"

        lines.append(f"  [{type_str}] {name} - {status}")

    return "\n".join(lines)


@mcp.tool()
async def get_user_subject_collection(username: str, subject_id: int) -> str:
    """
    Get a user's collection status for a specific subject.

    Args:
        username: The username.
        subject_id: The subject ID.

    Returns:
        Collection details or error.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/users/{username}/collections/{subject_id}"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict):
        return f"Unexpected API response format: {response}"

    coll = response
    details = f"Collection for {username} on subject {subject_id}:\n"
    details += f"  Type: {coll.get('type')}\n"
    if coll.get('ep_status') is not None:
        details += f"  Episode Status: {coll.get('ep_status')}\n"
    if coll.get('vol_status') is not None:
        details += f"  Volume Status: {coll.get('vol_status')}\n"
    if coll.get('rating'):
        details += f"  Rating: {coll.get('rating')}\n"
    if coll.get('comment'):
        details += f"  Comment: {coll.get('comment')}\n"

    return details


@mcp.tool()
async def update_subject_collection(
    subject_id: int,
    collection_type: Optional[int] = None,
    ep_status: Optional[int] = None,
    vol_status: Optional[int] = None,
    rating: Optional[int] = None,
    comment: Optional[str] = None,
) -> str:
    """
    Update the collection status for a subject.

    Collection types:
    1: Wish, 2: Collect, 3: Doing, 4: On Hold, 5: Dropped

    Args:
        subject_id: The subject ID.
        collection_type: Collection status (1-5).
        ep_status: Episode status (0-n).
        vol_status: Volume status (0-n).
        rating: Rating (0-10).
        comment: Personal comment.

    Returns:
        Success message or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    json_body: Dict[str, Any] = {}
    if collection_type is not None:
        json_body["type"] = collection_type
    if ep_status is not None:
        json_body["ep_status"] = ep_status
    if vol_status is not None:
        json_body["vol_status"] = vol_status
    if rating is not None:
        json_body["rating"] = rating
    if comment is not None:
        json_body["comment"] = comment

    response = await make_bangumi_request(
        method="POST",
        path=f"/v0/users/-/collections/{subject_id}",
        json_body=json_body,
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    return f"Successfully updated collection for subject {subject_id}."


@mcp.tool()
async def get_user_episode_collection(
    subject_id: int,
    episode_type: Optional[EpType] = None,
    limit: int = 100,
    offset: int = 0,
) -> str:
    """
    Get the episode collection status for a subject.

    Args:
        subject_id: The subject ID.
        episode_type: Optional filter by episode type.
        limit: Pagination limit. Defaults to 100.
        offset: Pagination offset. Defaults to 0.

    Returns:
        Episode collection details or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    query_params: Dict[str, Any] = {"limit": min(limit, 1000), "offset": offset}
    if episode_type is not None:
        query_params["episode_type"] = int(episode_type)

    response = await make_bangumi_request(
        method="GET",
        path=f"/v0/users/-/collections/{subject_id}/episodes",
        query_params=query_params,
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format: {response}"

    episodes = response.get("data", [])
    if not episodes:
        return f"No episode collection found for subject {subject_id}."

    lines = [f"Episode collection for subject {subject_id}:"]
    for ep in episodes:
        ep_id = ep.get("id")
        ep_type = ep.get("type")
        status = ep.get("type")
        name = ep.get("name") or ep.get("name_cn")

        try:
            type_str = EpType(ep_type).name if ep_type else "?"
        except ValueError:
            type_str = f"?"

        status_str = "Watched" if status == 1 else "Not Watched"
        lines.append(f"  [{type_str}] {name} - {status_str}")

    return "\n".join(lines)


@mcp.tool()
async def update_episode_collection(
    subject_id: int,
    episode_ids: List[int],
    episode_type: int = 1,
) -> str:
    """
    Update the collection status for episodes.

    Episode collection types:
    0: None, 1: Watched

    Args:
        subject_id: The subject ID.
        episode_ids: List of episode IDs to update.
        episode_type: Collection status (0 or 1). Defaults to 1 (Watched).

    Returns:
        Success message or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    json_body = {
        "episode_id": episode_ids,
        "type": episode_type,
    }

    response = await make_bangumi_request(
        method="PATCH",
        path=f"/v0/users/-/collections/{subject_id}/episodes",
        json_body=json_body,
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    return f"Successfully updated collection for {len(episode_ids)} episodes."


@mcp.tool()
async def get_single_episode_collection(episode_id: int) -> str:
    """
    Get the collection status for a single episode.

    Args:
        episode_id: The episode ID.

    Returns:
        Episode collection status or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    response = await make_bangumi_request(
        method="GET", path=f"/v0/users/-/collections/-/episodes/{episode_id}"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict):
        return f"Unexpected API response format: {response}"

    ep = response
    status = "Watched" if ep.get("type") == 1 else "Not Watched"
    details = f"Episode {episode_id} collection:\n"
    details += f"  Status: {status}\n"

    return details


@mcp.tool()
async def update_single_episode_collection(
    episode_id: int, episode_type: int = 1
) -> str:
    """
    Update the collection status for a single episode.

    Args:
        episode_id: The episode ID.
        episode_type: Collection status (0 or 1). Defaults to 1 (Watched).

    Returns:
        Success message or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    json_body = {"type": episode_type}

    response = await make_bangumi_request(
        method="PUT",
        path=f"/v0/users/-/collections/-/episodes/{episode_id}",
        json_body=json_body,
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    return f"Successfully updated collection for episode {episode_id}."


@mcp.tool()
async def get_user_character_collections(username: str) -> str:
    """
    Get a user's character collection list.

    Args:
        username: The username.

    Returns:
        Character collection list or error.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/users/{username}/collections/-/characters"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format: {response}"

    characters = response.get("data", [])
    if not characters:
        return f"No character collections found for user {username}."

    lines = [f"Character collections for {username}:"]
    for char in characters:
        char_id = char.get("id")
        name = char.get("name")
        lines.append(f"  [ID: {char_id}] {name}")

    return "\n".join(lines)


@mcp.tool()
async def get_user_character_collection(
    username: str, character_id: int
) -> str:
    """
    Get a user's collection status for a specific character.

    Args:
        username: The username.
        character_id: The character ID.

    Returns:
        Character collection details or error.
    """
    response = await make_bangumi_request(
        method="GET",
        path=f"/v0/users/{username}/collections/-/characters/{character_id}",
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict):
        return f"Unexpected API response format: {response}"

    char = response
    details = f"Character collection for {username} on character {character_id}:\n"
    details += f"  ID: {char.get('id')}\n"
    details += f"  Name: {char.get('name')}\n"
    details += f"  Comment: {char.get('comment') or 'N/A'}\n"

    return details


@mcp.tool()
async def get_user_person_collections(username: str) -> str:
    """
    Get a user's person collection list.

    Args:
        username: The username.

    Returns:
        Person collection list or error.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/users/{username}/collections/-/persons"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format: {response}"

    persons = response.get("data", [])
    if not persons:
        return f"No person collections found for user {username}."

    lines = [f"Person collections for {username}:"]
    for person in persons:
        person_id = person.get("id")
        name = person.get("name")
        lines.append(f"  [ID: {person_id}] {name}")

    return "\n".join(lines)


@mcp.tool()
async def get_user_person_collection(username: str, person_id: int) -> str:
    """
    Get a user's collection status for a specific person.

    Args:
        username: The username.
        person_id: The person ID.

    Returns:
        Person collection details or error.
    """
    response = await make_bangumi_request(
        method="GET",
        path=f"/v0/users/{username}/collections/-/persons/{person_id}",
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict):
        return f"Unexpected API response format: {response}"

    person = response
    details = f"Person collection for {username} on person {person_id}:\n"
    details += f"  ID: {person.get('id')}\n"
    details += f"  Name: {person.get('name')}\n"
    details += f"  Comment: {person.get('comment') or 'N/A'}\n"

    return details


# --- Revision History Functions ---


@mcp.tool()
async def get_person_revisions(
    person_id: int,
    limit: int = 30,
    offset: int = 0,
) -> str:
    """
    Get revision history for a person.

    Args:
        person_id: The person ID.
        limit: Pagination limit. Defaults to 30.
        offset: Pagination offset. Defaults to 0.

    Returns:
        Revision history or error.
    """
    query_params: Dict[str, Any] = {
        "person_id": person_id,
        "limit": min(limit, 50),
        "offset": offset,
    }

    response = await make_bangumi_request(
        method="GET", path="/v0/revisions/persons", query_params=query_params
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format: {response}"

    revisions = response.get("data", [])
    if not revisions:
        return f"No revisions found for person ID {person_id}."

    lines = [f"Revisions for person {person_id}:"]
    lines.append(f"Total: {response.get('total', 0)}\n")

    for rev in revisions:
        rev_id = rev.get("id")
        action = rev.get("action")
        created = rev.get("created")
        user = rev.get("user", {})
        username = user.get("username") if user else "Unknown"

        lines.append(f"  [ID: {rev_id}] {action} by {username} at {created}")

    return "\n".join(lines)


@mcp.tool()
async def get_person_revision(revision_id: int) -> str:
    """
    Get details of a specific person revision.

    Args:
        revision_id: The revision ID.

    Returns:
        Revision details or error.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/revisions/persons/{revision_id}"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict):
        return f"Unexpected API response format: {response}"

    rev = response
    details = f"Revision {revision_id} Details:\n"
    details += f"  Type: {rev.get('type')}\n"
    details += f"  Action: {rev.get('action')}\n"
    details += f"  Created: {rev.get('created')}\n"

    user = rev.get("user", {})
    if user:
        details += f"  User: {user.get('username')}\n"

    if rev.get("summary"):
        details += f"  Summary: {rev.get('summary')}\n"

    diff = rev.get("diff")
    if diff:
        details += f"  Changes: {diff}\n"

    return details


@mcp.tool()
async def get_character_revisions(
    character_id: int,
    limit: int = 30,
    offset: int = 0,
) -> str:
    """
    Get revision history for a character.

    Args:
        character_id: The character ID.
        limit: Pagination limit. Defaults to 30.
        offset: Pagination offset. Defaults to 0.

    Returns:
        Revision history or error.
    """
    query_params: Dict[str, Any] = {
        "character_id": character_id,
        "limit": min(limit, 50),
        "offset": offset,
    }

    response = await make_bangumi_request(
        method="GET", path="/v0/revisions/characters", query_params=query_params
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format: {response}"

    revisions = response.get("data", [])
    if not revisions:
        return f"No revisions found for character ID {character_id}."

    lines = [f"Revisions for character {character_id}:"]
    lines.append(f"Total: {response.get('total', 0)}\n")

    for rev in revisions:
        rev_id = rev.get("id")
        action = rev.get("action")
        created = rev.get("created")
        user = rev.get("user", {})
        username = user.get("username") if user else "Unknown"

        lines.append(f"  [ID: {rev_id}] {action} by {username} at {created}")

    return "\n".join(lines)


@mcp.tool()
async def get_character_revision(revision_id: int) -> str:
    """
    Get details of a specific character revision.

    Args:
        revision_id: The revision ID.

    Returns:
        Revision details or error.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/revisions/characters/{revision_id}"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict):
        return f"Unexpected API response format: {response}"

    rev = response
    details = f"Revision {revision_id} Details:\n"
    details += f"  Type: {rev.get('type')}\n"
    details += f"  Action: {rev.get('action')}\n"
    details += f"  Created: {rev.get('created')}\n"

    user = rev.get("user", {})
    if user:
        details += f"  User: {user.get('username')}\n"

    if rev.get("summary"):
        details += f"  Summary: {rev.get('summary')}\n"

    diff = rev.get("diff")
    if diff:
        details += f"  Changes: {diff}\n"

    return details


@mcp.tool()
async def get_subject_revisions(
    subject_id: int,
    limit: int = 30,
    offset: int = 0,
) -> str:
    """
    Get revision history for a subject.

    Args:
        subject_id: The subject ID.
        limit: Pagination limit. Defaults to 30.
        offset: Pagination offset. Defaults to 0.

    Returns:
        Revision history or error.
    """
    query_params: Dict[str, Any] = {
        "subject_id": subject_id,
        "limit": min(limit, 50),
        "offset": offset,
    }

    response = await make_bangumi_request(
        method="GET", path="/v0/revisions/subjects", query_params=query_params
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format: {response}"

    revisions = response.get("data", [])
    if not revisions:
        return f"No revisions found for subject ID {subject_id}."

    lines = [f"Revisions for subject {subject_id}:"]
    lines.append(f"Total: {response.get('total', 0)}\n")

    for rev in revisions:
        rev_id = rev.get("id")
        action = rev.get("action")
        created = rev.get("created")
        user = rev.get("user", {})
        username = user.get("username") if user else "Unknown"

        lines.append(f"  [ID: {rev_id}] {action} by {username} at {created}")

    return "\n".join(lines)


@mcp.tool()
async def get_subject_revision(revision_id: int) -> str:
    """
    Get details of a specific subject revision.

    Args:
        revision_id: The revision ID.

    Returns:
        Revision details or error.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/revisions/subjects/{revision_id}"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict):
        return f"Unexpected API response format: {response}"

    rev = response
    details = f"Revision {revision_id} Details:\n"
    details += f"  Type: {rev.get('type')}\n"
    details += f"  Action: {rev.get('action')}\n"
    details += f"  Created: {rev.get('created')}\n"

    user = rev.get("user", {})
    if user:
        details += f"  User: {user.get('username')}\n"

    if rev.get("summary"):
        details += f"  Summary: {rev.get('summary')}\n"

    diff = rev.get("diff")
    if diff:
        details += f"  Changes: {diff}\n"

    return details


@mcp.tool()
async def get_episode_revisions(
    episode_id: int,
    limit: int = 30,
    offset: int = 0,
) -> str:
    """
    Get revision history for an episode.

    Args:
        episode_id: The episode ID.
        limit: Pagination limit. Defaults to 30.
        offset: Pagination offset. Defaults to 0.

    Returns:
        Revision history or error.
    """
    query_params: Dict[str, Any] = {
        "episode_id": episode_id,
        "limit": min(limit, 50),
        "offset": offset,
    }

    response = await make_bangumi_request(
        method="GET", path="/v0/revisions/episodes", query_params=query_params
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format: {response}"

    revisions = response.get("data", [])
    if not revisions:
        return f"No revisions found for episode ID {episode_id}."

    lines = [f"Revisions for episode {episode_id}:"]
    lines.append(f"Total: {response.get('total', 0)}\n")

    for rev in revisions:
        rev_id = rev.get("id")
        action = rev.get("action")
        created = rev.get("created")
        user = rev.get("user", {})
        username = user.get("username") if user else "Unknown"

        lines.append(f"  [ID: {rev_id}] {action} by {username} at {created}")

    return "\n".join(lines)


@mcp.tool()
async def get_episode_revision(revision_id: int) -> str:
    """
    Get details of a specific episode revision.

    Args:
        revision_id: The revision ID.

    Returns:
        Revision details or error.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/revisions/episodes/{revision_id}"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict):
        return f"Unexpected API response format: {response}"

    rev = response
    details = f"Revision {revision_id} Details:\n"
    details += f"  Type: {rev.get('type')}\n"
    details += f"  Action: {rev.get('action')}\n"
    details += f"  Created: {rev.get('created')}\n"

    user = rev.get("user", {})
    if user:
        details += f"  User: {user.get('username')}\n"

    if rev.get("summary"):
        details += f"  Summary: {rev.get('summary')}\n"

    diff = rev.get("diff")
    if diff:
        details += f"  Changes: {diff}\n"

    return details


# --- Index (Directory) Functions ---


@mcp.tool()
async def create_index(title: str, description: str) -> str:
    """
    Create a new index (directory).

    Requires authentication (BANGUMI_TOKEN).

    Args:
        title: The title of the index.
        description: The description of the index.

    Returns:
        Index ID or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    json_body = {
        "title": title,
        "description": description,
    }

    response = await make_bangumi_request(
        method="POST", path="/v0/indices", json_body=json_body
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict):
        return f"Unexpected API response format: {response}"

    index_id = response.get("id")
    return f"Successfully created index. ID: {index_id}"


@mcp.tool()
async def get_index(index_id: int) -> str:
    """
    Get index (directory) details.

    Args:
        index_id: The index ID.

    Returns:
        Index details or error.
    """
    response = await make_bangumi_request(
        method="GET", path=f"/v0/indices/{index_id}"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict):
        return f"Unexpected API response format: {response}"

    idx = response
    details = f"Index {index_id}:\n"
    details += f"  Title: {idx.get('title')}\n"
    details += f"  Description: {idx.get('description')}\n"
    details += f"  Creator: {idx.get('creator', {}).get('username') if isinstance(idx.get('creator'), dict) else idx.get('creator')}\n"
    details += f"  Created: {idx.get('created')}\n"
    details += f"  Subject Count: {idx.get('subject_count', 0)}\n"

    return details


@mcp.tool()
async def update_index(
    index_id: int, title: str, description: str
) -> str:
    """
    Update index (directory) information.

    Requires authentication (BANGUMI_TOKEN).

    Args:
        index_id: The index ID.
        title: New title.
        description: New description.

    Returns:
        Success message or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    json_body = {
        "title": title,
        "description": description,
    }

    response = await make_bangumi_request(
        method="PUT", path=f"/v0/indices/{index_id}", json_body=json_body
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    return f"Successfully updated index {index_id}."


@mcp.tool()
async def get_index_subjects(
    index_id: int,
    subject_type: Optional[SubjectType] = None,
    limit: int = 30,
    offset: int = 0,
) -> str:
    """
    Get subjects in an index.

    Args:
        index_id: The index ID.
        subject_type: Optional filter by subject type.
        limit: Pagination limit. Defaults to 30.
        offset: Pagination offset. Defaults to 0.

    Returns:
        Index subjects or error.
    """
    query_params: Dict[str, Any] = {
        "limit": min(limit, 50),
        "offset": offset,
    }
    if subject_type is not None:
        query_params["type"] = int(subject_type)

    response = await make_bangumi_request(
        method="GET", path=f"/v0/indices/{index_id}/subjects", query_params=query_params
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    if not isinstance(response, dict) or "data" not in response:
        return f"Unexpected API response format: {response}"

    subjects = response.get("data", [])
    if not subjects:
        return f"No subjects found in index {index_id}."

    lines = [f"Subjects in index {index_id}:"]
    lines.append(f"Total: {response.get('total', 0)}\n")

    for subj in subjects:
        subj_id = subj.get("id")
        name = subj.get("title") or subj.get("name")
        lines.append(f"  [ID: {subj_id}] {name}")

    return "\n".join(lines)


@mcp.tool()
async def add_subject_to_index(
    index_id: int, subject_id: int, comment: Optional[str] = None
) -> str:
    """
    Add a subject to an index.

    Requires authentication (BANGUMI_TOKEN).

    Args:
        index_id: The index ID.
        subject_id: The subject ID to add.
        comment: Optional comment.

    Returns:
        Success message or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    json_body: Dict[str, Any] = {"subject_id": subject_id}
    if comment:
        json_body["comment"] = comment

    response = await make_bangumi_request(
        method="POST", path=f"/v0/indices/{index_id}/subjects", json_body=json_body
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    return f"Successfully added subject {subject_id} to index {index_id}."


@mcp.tool()
async def update_index_subject(
    index_id: int, subject_id: int, comment: Optional[str] = None
) -> str:
    """
    Update subject information in an index.

    Requires authentication (BANGUMI_TOKEN).

    Args:
        index_id: The index ID.
        subject_id: The subject ID to update.
        comment: New comment.

    Returns:
        Success message or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    json_body: Dict[str, Any] = {}
    if comment:
        json_body["comment"] = comment

    response = await make_bangumi_request(
        method="PUT",
        path=f"/v0/indices/{index_id}/subjects/{subject_id}",
        json_body=json_body,
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    return f"Successfully updated subject {subject_id} in index {index_id}."


@mcp.tool()
async def remove_subject_from_index(
    index_id: int, subject_id: int
) -> str:
    """
    Remove a subject from an index.

    Requires authentication (BANGUMI_TOKEN).

    Args:
        index_id: The index ID.
        subject_id: The subject ID to remove.

    Returns:
        Success message or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    response = await make_bangumi_request(
        method="DELETE", path=f"/v0/indices/{index_id}/subjects/{subject_id}"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    return f"Successfully removed subject {subject_id} from index {index_id}."


@mcp.tool()
async def collect_index(index_id: int) -> str:
    """
    Collect (favorite) an index for the current user.

    Requires authentication (BANGUMI_TOKEN).

    Args:
        index_id: The index ID.

    Returns:
        Success message or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    response = await make_bangumi_request(
        method="POST", path=f"/v0/indices/{index_id}/collect"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    return f"Successfully collected index {index_id}."


@mcp.tool()
async def uncollect_index(index_id: int) -> str:
    """
    Remove an index from the current user's collection.

    Requires authentication (BANGUMI_TOKEN).

    Args:
        index_id: The index ID.

    Returns:
        Success message or error.
    """
    if not BANGUMI_TOKEN:
        return "BANGUMI_TOKEN is required for this operation."

    response = await make_bangumi_request(
        method="DELETE", path=f"/v0/indices/{index_id}/collect"
    )

    error_msg = handle_api_error_response(response)
    if error_msg:
        return error_msg

    return f"Successfully uncollected index {index_id}."


# --- Prompts ---


@mcp.prompt()
def search_and_summarize_anime(keyword: str) -> str:
    """
    Search for anime based on a keyword and ask for a summary of the results.

    Args:
        keyword: The keyword to search for anime.
    """
    # This prompt prepares the LLM to use the search tool and then summarize.
    # The LLM needs to understand it first needs to call the search tool.
    return f"Search for anime matching '{keyword}' using the 'search_subjects' tool (filtering by subject_type=2 for anime), then summarize the main subjects found from the tool output."


@mcp.prompt()
def get_subject_full_info(subject_id: int) -> str:
    """
    Get detailed information, related persons, characters, and relations for a subject.

    Args:
        subject_id: The ID of the subject to get information for.
    """
    return f"Get the full details for subject ID {subject_id} using 'get_subject_details'. Also get related persons using 'get_subject_persons', related characters using 'get_subject_characters', and other related subjects using 'get_subject_relations'. Summarize the key information from all these tool outputs."


@mcp.prompt()
def find_voice_actor(character_name: str) -> str:
    """
    Search for a character by name and find their voice actor.

    Args:
        character_name: The name of the character.
    """
    return f"Search for the character '{character_name}' using 'search_characters'. If the search finds characters, identify the most relevant character ID. Then, use 'get_character_persons' with the character ID to list persons related to them (like voice actors). Summarize the voice actors found from the tool output."


# --- Running the server ---

if __name__ == "__main__":
    print("Starting Bangumi MCP Server...")
    mcp.run(transport="stdio")
    print("Bangumi MCP Server stopped.")
