"""Unit tests for aulasvirtuales_mcp.server — MCP server tools."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aulasvirtuales.client import Course, Event, GradeItem, Resource, Section


# ---------------------------------------------------------------------------
# Helper to mock _get_client globally for MCP tools
# ---------------------------------------------------------------------------

def _mock_client():
    """Create a mock MoodleClient."""
    client = MagicMock()
    return client


# ---------------------------------------------------------------------------
# Tests: MCP Tools
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetCoursesTool:
    @patch("aulasvirtuales_mcp.server._get_client")
    def test_get_courses_tool(self, mock_get_client):
        """get_courses MCP tool returns course list."""
        from aulasvirtuales_mcp.server import get_courses

        mock_client = _mock_client()
        mock_client.get_courses.return_value = [
            Course(id=101, fullname="Matemática", url="http://example.com"),
        ]
        mock_get_client.return_value = mock_client

        result = get_courses()

        assert len(result) == 1
        assert result[0].id == 101


@pytest.mark.unit
class TestGetCourseResourcesTool:
    @patch("aulasvirtuales_mcp.server._get_client")
    def test_get_course_resources_tool(self, mock_get_client):
        """get_course_resources MCP tool returns sections."""
        from aulasvirtuales_mcp.server import get_course_resources

        mock_client = _mock_client()
        mock_client.get_course_contents.return_value = [
            Section(
                id=1, number=1, name="Unidad 1",
                resources=[Resource(id=10, name="Apunte", module="resource")],
            ),
        ]
        mock_get_client.return_value = mock_client

        result = get_course_resources(101)

        assert len(result) == 1
        assert result[0].name == "Unidad 1"


@pytest.mark.unit
class TestGetUpcomingEventsTool:
    @patch("aulasvirtuales_mcp.server._get_client")
    def test_get_upcoming_events_tool(self, mock_get_client):
        """get_upcoming_events MCP tool returns events."""
        from aulasvirtuales_mcp.server import get_upcoming_events

        mock_client = _mock_client()
        mock_client.get_upcoming_events.return_value = [
            Event(id=1, name="TP1", course_name="Mat", module="assign",
                  timestamp=1700000000, url="http://example.com", action="Submit"),
        ]
        mock_get_client.return_value = mock_client

        result = get_upcoming_events()

        assert len(result) == 1
        assert result[0].name == "TP1"


@pytest.mark.unit
class TestGetGradesTool:
    @patch("aulasvirtuales_mcp.server._get_client")
    def test_get_grades_tool(self, mock_get_client):
        """get_grades MCP tool returns grade items."""
        from aulasvirtuales_mcp.server import get_grades

        mock_client = _mock_client()
        mock_client.get_grades.return_value = [
            GradeItem(name="Parcial", grade="8", range="0-10", percentage="80%", feedback="OK"),
        ]
        mock_get_client.return_value = mock_client

        result = get_grades(101)

        assert len(result) == 1
        assert result[0].grade == "8"


@pytest.mark.unit
class TestOcrStatus:
    def test_ocr_status_no_jobs(self):
        """ocr_status returns 'no jobs' message when registry is empty."""
        from aulasvirtuales_mcp.server import ocr_status, _ocr_jobs

        _ocr_jobs.clear()

        result = ocr_status()

        assert "No OCR jobs" in result


@pytest.mark.unit
class TestClearDownloadsTool:
    @patch("aulasvirtuales_mcp.server.get_download_dir")
    def test_clear_downloads_empty_dir(self, mock_get_dir, tmp_path):
        """clear_downloads reports empty when directory has no files."""
        from aulasvirtuales_mcp.server import clear_downloads

        empty_dir = tmp_path / "downloads"
        empty_dir.mkdir()
        mock_get_dir.return_value = empty_dir

        result = clear_downloads()

        assert "empty" in result.lower()

    @patch("aulasvirtuales_mcp.server.get_download_dir")
    def test_clear_downloads_requires_force(self, mock_get_dir, tmp_path):
        """clear_downloads asks for confirmation without force flag."""
        from aulasvirtuales_mcp.server import clear_downloads

        dl_dir = tmp_path / "downloads"
        dl_dir.mkdir()
        (dl_dir / "file.txt").write_text("data")
        mock_get_dir.return_value = dl_dir

        result = clear_downloads(force=False)

        assert "force" in result.lower()
        # File should still exist
        assert (dl_dir / "file.txt").exists()

    @patch("aulasvirtuales_mcp.server.get_download_dir")
    def test_clear_downloads_with_force(self, mock_get_dir, tmp_path):
        """clear_downloads deletes files when force=True."""
        from aulasvirtuales_mcp.server import clear_downloads

        dl_dir = tmp_path / "downloads"
        dl_dir.mkdir()
        (dl_dir / "file.txt").write_text("data")
        mock_get_dir.return_value = dl_dir

        result = clear_downloads(force=True)

        assert "✓" in result
        assert not (dl_dir / "file.txt").exists()
