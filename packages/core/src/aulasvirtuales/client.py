import httpx

from aulasvirtuales.models import (  # noqa: F401 — backward compat re-exports
    MODULE_TYPE_LABELS,
    AssignmentDetails,
    Course,
    Discussion,
    Event,
    ForumPost,
    GradeItem,
    Resource,
    Section,
    SubmissionComment,
)
from aulasvirtuales.services.assignments import AssignmentsService
from aulasvirtuales.services.courses import CoursesService
from aulasvirtuales.services.events import EventsService
from aulasvirtuales.services.forums import ForumsService
from aulasvirtuales.services.grades import GradesService
from aulasvirtuales.session import MoodleClientError, MoodleSession  # noqa: F401


class MoodleClient:
    """Facade that delegates to domain services.

    Consumers keep using ``MoodleClient`` as the single entry point.
    All method signatures are unchanged for backward compatibility.
    """

    def __init__(self, session_cookie: str) -> None:
        self._session = MoodleSession(session_cookie)
        self._courses = CoursesService(self._session)
        self._assignments = AssignmentsService(self._session)
        self._forums = ForumsService(self._session, self._courses)
        self._events = EventsService(self._session)
        self._grades = GradesService(self._session, self._assignments)

    @property
    def http(self) -> httpx.Client:
        return self._session.http

    @property
    def _http(self) -> httpx.Client:
        return self._session.http

    def get_courses(self) -> list[Course]:
        return self._courses.get_courses()

    def get_course_contents(self, course_id: int) -> list[Section]:
        return self._courses.get_course_contents(course_id)

    def get_forums(self, course_id: int) -> list[Resource]:
        return self._forums.get_forums(course_id)

    def get_forum_discussions(self, forum_cmid: int, limit: int = 10) -> list[Discussion]:
        return self._forums.get_forum_discussions(forum_cmid, limit)

    def get_discussion_posts(self, discussion_id: int) -> list[ForumPost]:
        return self._forums.get_discussion_posts(discussion_id)

    def get_upcoming_events(self, course_id: int | None = None, limit: int = 20) -> list[Event]:
        return self._events.get_upcoming_events(course_id, limit)

    def get_grades(self, course_id: int) -> list[GradeItem]:
        return self._grades.get_grades(course_id)

    def get_grades_with_status(self, course_id: int) -> list[GradeItem]:
        return self._grades.get_grades_with_status(course_id)

    def get_assignment_details(self, assignment_cmid: int) -> AssignmentDetails:
        return self._assignments.get_assignment_details(assignment_cmid)
