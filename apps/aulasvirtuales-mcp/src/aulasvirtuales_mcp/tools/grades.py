from aulasvirtuales_mcp.server import get_client, mcp


@mcp.tool()
def get_grades(course_id: int | str):
    """Show grades and feedback for a course."""
    client = get_client()
    return client.get_grades(int(course_id))
