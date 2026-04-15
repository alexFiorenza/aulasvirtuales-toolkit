from aulasvirtuales_mcp.server import get_client, mcp


@mcp.tool()
def get_forums(course_id: int | str):
    """List forums in a course."""
    client = get_client()
    return client.get_forums(int(course_id))


@mcp.tool()
def get_forum_discussions(forum_id: int | str, limit: int | str = 10):
    """List discussions in a forum."""
    client = get_client()
    return client.get_forum_discussions(int(forum_id), int(limit))


@mcp.tool()
def get_discussion_posts(discussion_id: int | str):
    """Show messages in a forum discussion."""
    client = get_client()
    return client.get_discussion_posts(int(discussion_id))
