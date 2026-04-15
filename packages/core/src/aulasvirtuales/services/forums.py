from aulasvirtuales.models import Discussion, ForumPost, Resource
from aulasvirtuales.parsers import parse_forum_discussions
from aulasvirtuales.services.courses import CoursesService
from aulasvirtuales.session import MoodleSession


class ForumsService:
    def __init__(self, session: MoodleSession, courses: CoursesService) -> None:
        self._session = session
        self._courses = courses

    def get_forums(self, course_id: int) -> list[Resource]:
        sections = self._courses.get_course_contents(course_id)
        return [r for s in sections for r in s.resources if r.module == "forum"]

    def get_forum_discussions(self, forum_cmid: int, limit: int = 10) -> list[Discussion]:
        response = self._session.http.get(
            f"/mod/forum/view.php?id={forum_cmid}", follow_redirects=True,
        )
        return parse_forum_discussions(response.text, limit)

    def get_discussion_posts(self, discussion_id: int) -> list[ForumPost]:
        data = self._session.ajax(
            "mod_forum_get_discussion_posts",
            {"discussionid": discussion_id},
        )
        return [
            ForumPost(
                id=p["id"],
                subject=p.get("subject", ""),
                author=p.get("author", {}).get("fullname", ""),
                message=p.get("message", ""),
                timestamp=p.get("timecreated", 0),
            )
            for p in data.get("posts", [])
        ]
