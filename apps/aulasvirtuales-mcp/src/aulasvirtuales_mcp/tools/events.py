from aulasvirtuales_mcp.server import get_client, mcp


@mcp.tool()
def get_upcoming_events(course_id: int | str | None = None):
    """Show upcoming events for a specific course or across all courses."""
    client = get_client()
    return client.get_upcoming_events(int(course_id) if course_id is not None else None)
