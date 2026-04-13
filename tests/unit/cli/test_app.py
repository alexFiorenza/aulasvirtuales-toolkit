"""Unit tests for aulasvirtuales_cli.app — CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from aulasvirtuales_cli.app import app

runner = CliRunner()


@pytest.mark.unit
class TestVersionFlag:
    def test_version_flag(self):
        """--version prints the version and exits."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "aulasvirtuales" in result.output


@pytest.mark.unit
class TestCoursesCommand:
    @patch("aulasvirtuales_cli.app._get_client")
    def test_courses_command(self, mock_get_client):
        """courses command displays enrolled courses in a table."""
        from aulasvirtuales.client import Course

        mock_client = MagicMock()
        mock_client.get_courses.return_value = [
            Course(id=101, fullname="Matemática Discreta", url="http://example.com"),
            Course(id=202, fullname="Sistemas Operativos", url="http://example.com"),
        ]
        mock_get_client.return_value = mock_client

        result = runner.invoke(app, ["courses"])

        assert result.exit_code == 0
        assert "101" in result.output
        assert "Matemática Discreta" in result.output
        assert "202" in result.output


@pytest.mark.unit
class TestResourcesCommand:
    @patch("aulasvirtuales_cli.app._get_client")
    def test_resources_command(self, mock_get_client):
        """resources command displays sections and resources."""
        from aulasvirtuales.client import Resource, Section

        mock_client = MagicMock()
        mock_client.get_course_contents.return_value = [
            Section(
                id=1, number=1, name="Unidad 1",
                resources=[
                    Resource(id=10, name="Apunte.pdf", module="resource"),
                    Resource(id=11, name="Foro General", module="forum"),
                ],
            ),
        ]
        mock_get_client.return_value = mock_client

        result = runner.invoke(app, ["resources", "101"])

        assert result.exit_code == 0
        assert "Unidad 1" in result.output
        assert "Apunte.pdf" in result.output


@pytest.mark.unit
class TestEventsCommand:
    @patch("aulasvirtuales_cli.app._get_client")
    def test_events_command(self, mock_get_client):
        """events command displays upcoming events."""
        from aulasvirtuales.client import Event

        mock_client = MagicMock()
        mock_client.get_upcoming_events.return_value = [
            Event(
                id=1, name="Entrega TP1", course_name="Matemática",
                module="assign", timestamp=1700100000, url="http://example.com",
                action="Entregar",
            ),
        ]
        mock_get_client.return_value = mock_client

        result = runner.invoke(app, ["events"])

        assert result.exit_code == 0
        assert "Entrega TP1" in result.output


@pytest.mark.unit
class TestGradesCommand:
    @patch("aulasvirtuales_cli.app._get_client")
    def test_grades_command(self, mock_get_client):
        """grades command displays grades table."""
        from aulasvirtuales.client import GradeItem

        mock_client = MagicMock()
        mock_client.get_grades.return_value = [
            GradeItem(name="Parcial 1", grade="8.00", range="0–10", percentage="80%", feedback="Bien"),
        ]
        mock_get_client.return_value = mock_client

        result = runner.invoke(app, ["grades", "101"])

        assert result.exit_code == 0
        assert "Parcial 1" in result.output
        assert "8.00" in result.output


@pytest.mark.unit
class TestForumsCommand:
    @patch("aulasvirtuales_cli.app._get_client")
    def test_forums_command(self, mock_get_client):
        """forums command lists forums."""
        from aulasvirtuales.client import Resource

        mock_client = MagicMock()
        mock_client.get_forums.return_value = [
            Resource(id=5, name="Foro General", module="forum"),
        ]
        mock_get_client.return_value = mock_client

        result = runner.invoke(app, ["forums", "101"])

        assert result.exit_code == 0
        assert "Foro General" in result.output


@pytest.mark.unit
class TestConfigCommand:
    @patch("aulasvirtuales_cli.app.get_download_dir")
    @patch("aulasvirtuales_cli.app.get_ocr_config")
    def test_config_command_show(self, mock_ocr_config, mock_download_dir, tmp_path):
        """config command with no args shows current configuration."""
        mock_download_dir.return_value = tmp_path
        mock_ocr_config.return_value = {}

        result = runner.invoke(app, ["config"])

        assert result.exit_code == 0
        normalized_output = "".join(result.output.split())
        assert str(tmp_path) in normalized_output


@pytest.mark.unit
class TestStatusCommand:
    @patch("aulasvirtuales_cli.app.get_token")
    @patch("aulasvirtuales_cli.app.is_session_valid")
    @patch("aulasvirtuales_cli.app.get_credentials")
    def test_status_logged_in(self, mock_creds, mock_valid, mock_token):
        """status shows logged-in state when session is active."""
        mock_creds.return_value = ("testuser", "testpass")
        mock_token.return_value = "valid_token"
        mock_valid.return_value = True

        result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "testuser" in result.output
