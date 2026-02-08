"""Workflow prompts for common Bangumi tasks."""


def register(mcp):
    """Register all workflow prompts with the MCP server."""

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
