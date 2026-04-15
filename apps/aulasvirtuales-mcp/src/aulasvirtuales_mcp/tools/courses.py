from aulasvirtuales_mcp.server import get_client, mcp


@mcp.tool()
def get_courses() -> list:
    """List enrolled courses."""
    client = get_client()
    return client.get_courses()


@mcp.tool()
def get_course_resources(course_id: int) -> list:
    """List sections and resources of a course."""
    client = get_client()
    return client.get_course_contents(course_id)
