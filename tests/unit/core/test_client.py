"""Unit tests for aulasvirtuales.client — MoodleClient."""

import json
from unittest.mock import MagicMock, PropertyMock

import httpx
import pytest

from aulasvirtuales.client import (
    AssignmentDetails,
    Course,
    Discussion,
    Event,
    ForumPost,
    GradeItem,
    MoodleClient,
    MoodleClientError,
    Resource,
    Section,
    SubmissionComment,
)

from tests.conftest import (
    DASHBOARD_HTML,
    SAMPLE_COURSES_RESPONSE,
    SAMPLE_COURSE_STATE,
    SAMPLE_EVENTS_RESPONSE,
    SAMPLE_FORUM_DISCUSSIONS_HTML,
    SAMPLE_GRADES_ACTION_MENU_HTML,
    SAMPLE_GRADES_EMPTY_HTML,
    SAMPLE_GRADES_HTML,
    SAMPLE_POSTS_RESPONSE,
    SAMPLE_ASSIGNMENT_HTML,
    SAMPLE_COMMENTS_RESPONSE,
    SESSKEY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(monkeypatch) -> MoodleClient:
    """Create a MoodleClient with a mocked HTTP client."""
    mock_response = MagicMock()
    mock_response.text = DASHBOARD_HTML

    mock_http = MagicMock(spec=httpx.Client)
    mock_http.get.return_value = mock_response

    # Bypass __init__ to inject mocks
    client = object.__new__(MoodleClient)
    client._http = mock_http
    client._sesskey = SESSKEY
    return client


def _setup_ajax(client: MoodleClient, response_data):
    """Configure the mock HTTP client to return the given AJAX response."""
    mock_response = MagicMock()
    mock_response.json.return_value = response_data
    client._http.post.return_value = mock_response


def _setup_get(client: MoodleClient, html: str, url: str | None = None):
    """Configure mock HTTP GET to return the given HTML."""
    mock_response = MagicMock()
    mock_response.text = html
    if url:
        mock_response.url = url
    client._http.get.return_value = mock_response


# ---------------------------------------------------------------------------
# Tests: _fetch_sesskey
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFetchSesskey:
    def test_fetch_sesskey_success(self, monkeypatch):
        """Sesskey is correctly extracted from dashboard HTML."""
        mock_response = MagicMock()
        mock_response.text = DASHBOARD_HTML

        mock_http = MagicMock(spec=httpx.Client)
        mock_http.get.return_value = mock_response

        client = object.__new__(MoodleClient)
        client._http = mock_http
        result = client._fetch_sesskey()

        assert result == SESSKEY

    def test_fetch_sesskey_missing_raises(self):
        """MoodleClientError is raised when sesskey is not found."""
        mock_response = MagicMock()
        mock_response.text = "<html><body>No sesskey here</body></html>"

        mock_http = MagicMock(spec=httpx.Client)
        mock_http.get.return_value = mock_response

        client = object.__new__(MoodleClient)
        client._http = mock_http

        with pytest.raises(MoodleClientError, match="Could not extract sesskey"):
            client._fetch_sesskey()


# ---------------------------------------------------------------------------
# Tests: get_courses
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetCourses:
    def test_get_courses_returns_course_list(self, monkeypatch):
        """Courses are parsed from AJAX response."""
        client = _make_client(monkeypatch)
        _setup_ajax(client, SAMPLE_COURSES_RESPONSE)

        courses = client.get_courses()

        assert len(courses) == 2
        assert isinstance(courses[0], Course)
        assert courses[0].id == 101
        assert courses[0].fullname == "Matemática Discreta"
        assert courses[1].id == 202


# ---------------------------------------------------------------------------
# Tests: get_course_contents
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetCourseContents:
    def test_get_course_contents_filters_invisible(self, monkeypatch):
        """Invisible resources and sections are excluded."""
        client = _make_client(monkeypatch)
        _setup_ajax(client, [{"error": False, "data": json.dumps(SAMPLE_COURSE_STATE)}])

        sections = client.get_course_contents(101)

        # 3 sections total, but "Unidad Oculta" (visible=False) is excluded
        assert len(sections) == 2
        assert sections[0].name == "Unidad 1"

        # "Recurso Oculto" (uservisible=False) is excluded
        visible_resources = sections[0].resources
        assert len(visible_resources) == 2
        assert all(r.name != "Recurso Oculto" for r in visible_resources)

    def test_get_course_contents_returns_sections_with_resources(self, monkeypatch):
        """Sections contain their associated resources."""
        client = _make_client(monkeypatch)
        _setup_ajax(client, [{"error": False, "data": json.dumps(SAMPLE_COURSE_STATE)}])

        sections = client.get_course_contents(101)

        # Unidad 1 has 2 visible resources
        assert sections[0].resources[0].name == "Apunte Tema 1"
        assert sections[0].resources[0].module == "resource"
        assert sections[0].resources[1].name == "Foro General"
        assert sections[0].resources[1].module == "forum"

        # Unidad 2 has 1 visible resource
        assert len(sections[1].resources) == 1
        assert sections[1].resources[0].name == "Carpeta PDFs"


# ---------------------------------------------------------------------------
# Tests: get_forums
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetForums:
    def test_get_forums_filters_by_module(self, monkeypatch):
        """Only forum-type resources are returned."""
        client = _make_client(monkeypatch)
        _setup_ajax(client, [{"error": False, "data": json.dumps(SAMPLE_COURSE_STATE)}])

        forums = client.get_forums(101)

        assert len(forums) == 1
        assert forums[0].module == "forum"
        assert forums[0].name == "Foro General"


# ---------------------------------------------------------------------------
# Tests: get_forum_discussions
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetForumDiscussions:
    def test_get_forum_discussions_deduplicates(self, monkeypatch):
        """Duplicate discussion IDs are removed."""
        client = _make_client(monkeypatch)
        _setup_get(client, SAMPLE_FORUM_DISCUSSIONS_HTML)

        discussions = client.get_forum_discussions(2, limit=10)

        # HTML has discuss.php?d=100 twice, should be deduplicated
        assert len(discussions) == 3
        ids = [d.id for d in discussions]
        assert len(set(ids)) == 3

    def test_get_forum_discussions_respects_limit(self, monkeypatch):
        """Limit parameter caps the number of returned discussions."""
        client = _make_client(monkeypatch)
        _setup_get(client, SAMPLE_FORUM_DISCUSSIONS_HTML)

        discussions = client.get_forum_discussions(2, limit=2)

        assert len(discussions) == 2


# ---------------------------------------------------------------------------
# Tests: get_discussion_posts
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetDiscussionPosts:
    def test_get_discussion_posts_parses_correctly(self, monkeypatch):
        """Posts are parsed from AJAX response with all fields."""
        client = _make_client(monkeypatch)
        _setup_ajax(client, SAMPLE_POSTS_RESPONSE)

        posts = client.get_discussion_posts(100)

        assert len(posts) == 2
        assert isinstance(posts[0], ForumPost)
        assert posts[0].subject == "Bienvenidos"
        assert posts[0].author == "Prof. García"
        assert posts[0].clean_message == "Hola a todos!"
        assert posts[1].author == "Juan Pérez"


# ---------------------------------------------------------------------------
# Tests: get_upcoming_events
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetUpcomingEvents:
    def test_get_upcoming_events_by_course(self, monkeypatch):
        """Events for a specific course are returned."""
        client = _make_client(monkeypatch)
        _setup_ajax(client, SAMPLE_EVENTS_RESPONSE)

        events = client.get_upcoming_events(course_id=101)

        assert len(events) == 1
        assert isinstance(events[0], Event)
        assert events[0].name == "Entrega TP1"
        assert events[0].course_name == "Matemática Discreta"
        assert events[0].action == "Entregar"

        # Verify correct AJAX method was called
        call_args = client._http.post.call_args
        payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
        assert any("by_course" in str(arg) for arg in [call_args])

    def test_get_upcoming_events_all(self, monkeypatch):
        """Global events (no course_id) are returned."""
        client = _make_client(monkeypatch)
        _setup_ajax(client, SAMPLE_EVENTS_RESPONSE)

        events = client.get_upcoming_events(course_id=None)

        assert len(events) == 1


# ---------------------------------------------------------------------------
# Tests: get_grades
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetGrades:
    def test_get_grades_parses_html_table(self, monkeypatch):
        """Grade table is correctly parsed from HTML."""
        client = _make_client(monkeypatch)
        _setup_get(client, SAMPLE_GRADES_HTML)

        grades = client.get_grades(101)

        assert len(grades) == 2
        assert isinstance(grades[0], GradeItem)
        assert grades[0].name == "Parcial 1"
        assert grades[0].grade == "8.00"
        assert grades[0].range == "0–10"
        assert grades[0].percentage == "80.00 %"
        assert grades[0].feedback == "Bien"
        assert grades[1].name == "TP1"
        assert grades[1].grade == "10.00"

    def test_get_grades_strips_action_menu_from_grade_cells(self, monkeypatch):
        """Action-menu HTML in grade cells is stripped, preserving real grades."""
        client = _make_client(monkeypatch)
        _setup_get(client, SAMPLE_GRADES_ACTION_MENU_HTML)

        grades = client.get_grades(101)

        assert len(grades) == 3
        assert grades[0].name == "TPG1 Ética"
        assert grades[0].grade == "Entrega Muy bien"
        assert grades[0].percentage == "75,00 %"
        assert grades[1].name == "Quiz 1"
        assert grades[1].grade == "8,50"
        assert grades[1].range == "0–10"
        assert grades[2].name == "TPG2"
        assert grades[2].grade == ""

    def test_parse_grade_table_extracts_assign_cmids(self, monkeypatch):
        """Assign cmids are extracted from gradeitemheader links."""
        client = _make_client(monkeypatch)

        parsed = client._parse_grade_table(SAMPLE_GRADES_ACTION_MENU_HTML)

        assert len(parsed) == 3
        _, cmid0 = parsed[0]
        _, cmid1 = parsed[1]
        _, cmid2 = parsed[2]
        assert cmid0 == 100
        assert cmid1 is None  # quiz, not assign
        assert cmid2 == 300

    def test_get_grades_empty_table(self, monkeypatch):
        """Empty list returned when no grade table exists."""
        client = _make_client(monkeypatch)
        _setup_get(client, SAMPLE_GRADES_EMPTY_HTML)

        grades = client.get_grades(101)

        assert grades == []


# ---------------------------------------------------------------------------
# Tests: get_assignment_details
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetAssignmentDetails:
    def test_get_assignment_details_with_comments(self, monkeypatch):
        """Assignment grade and comments are extracted."""
        client = _make_client(monkeypatch)

        # First call returns assignment page HTML, second call returns comments JSON
        assignment_response = MagicMock()
        assignment_response.text = SAMPLE_ASSIGNMENT_HTML

        comments_response = MagicMock()
        comments_response.json.return_value = SAMPLE_COMMENTS_RESPONSE

        client._http.get.return_value = assignment_response
        client._http.post.return_value = comments_response

        details = client.get_assignment_details(1)

        assert isinstance(details, AssignmentDetails)
        assert details.grade == "8.50"
        assert details.submission_status == "Enviado para calificar"
        assert len(details.comments) == 1
        assert details.comments[0].author == "Prof. García"
        assert details.comments[0].content == "Buen trabajo"

    def test_get_assignment_details_graceful_failure(self, monkeypatch):
        """Returns grade even if comment AJAX fails."""
        client = _make_client(monkeypatch)

        assignment_response = MagicMock()
        assignment_response.text = SAMPLE_ASSIGNMENT_HTML

        client._http.get.return_value = assignment_response
        client._http.post.side_effect = Exception("AJAX error")

        details = client.get_assignment_details(1)

        # Grade should still be parsed even though comments failed
        assert details.grade == "8.50"
        assert details.comments == []


# ---------------------------------------------------------------------------
# Tests: Resource.type_label
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestResourceTypeLabel:
    def test_known_module_type(self):
        """Known modules return human-readable labels."""
        r = Resource(id=1, name="Test", module="resource")
        assert r.type_label == "File"

        r2 = Resource(id=2, name="Test", module="forum")
        assert r2.type_label == "Forum"

    def test_unknown_module_type(self):
        """Unknown modules return the raw module name."""
        r = Resource(id=1, name="Test", module="custommod")
        assert r.type_label == "custommod"
