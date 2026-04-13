"""Unit tests for aulasvirtuales.downloader — file downloading and URL parsing."""

from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from aulasvirtuales.downloader import (
    download_file,
    filename_from_url,
    get_resource_files,
)
from tests.conftest import SAMPLE_FOLDER_HTML, SAMPLE_RESOURCE_HTML


def _mock_http(html: str = "", final_url: str = "https://example.com") -> MagicMock:
    """Create a mock httpx.Client returning the given HTML response."""
    mock = MagicMock(spec=httpx.Client)
    response = MagicMock()
    response.text = html
    response.url = final_url
    mock.get.return_value = response
    return mock


# ---------------------------------------------------------------------------
# Tests: get_resource_files
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestGetResourceFiles:
    def test_get_resource_files_single(self):
        """Extracts download URL from a single resource page."""
        http = _mock_http(
            html=SAMPLE_RESOURCE_HTML,
            final_url="https://aulasvirtuales.frba.utn.edu.ar/mod/resource/view.php?id=1",
        )

        urls = get_resource_files(http, resource_id=1, module="resource")

        assert len(urls) == 1
        assert "pluginfile.php" in urls[0]
        assert "mod_resource" in urls[0]
        assert "apunte.pdf" in urls[0]

    def test_get_resource_files_folder(self):
        """Extracts multiple download URLs from a folder page."""
        http = _mock_http(html=SAMPLE_FOLDER_HTML)

        urls = get_resource_files(http, resource_id=4, module="folder")

        assert len(urls) == 2
        assert "archivo1.pdf" in urls[0]
        assert "archivo2.pdf" in urls[1]

    def test_get_resource_files_unsupported_module(self):
        """Returns empty list for unsupported module types."""
        http = _mock_http()

        urls = get_resource_files(http, resource_id=1, module="quiz")

        assert urls == []


# ---------------------------------------------------------------------------
# Tests: download_file
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDownloadFile:
    def test_download_file_saves_to_disk(self, tmp_path):
        """File is downloaded and saved to the destination directory."""
        http = MagicMock(spec=httpx.Client)
        stream_response = MagicMock()
        stream_response.iter_bytes.return_value = [b"file content here"]
        stream_response.raise_for_status.return_value = None
        stream_context = MagicMock()
        stream_context.__enter__ = MagicMock(return_value=stream_response)
        stream_context.__exit__ = MagicMock(return_value=False)
        http.stream.return_value = stream_context

        url = "https://aulasvirtuales.frba.utn.edu.ar/pluginfile.php/123/mod_resource/content/1/apunte.pdf"

        result = download_file(http, url, tmp_path)

        assert result == tmp_path / "apunte.pdf"
        assert result.exists()
        assert result.read_bytes() == b"file content here"

    def test_download_file_custom_filename(self, tmp_path):
        """File is saved with a custom filename when specified."""
        http = MagicMock(spec=httpx.Client)
        stream_response = MagicMock()
        stream_response.iter_bytes.return_value = [b"data"]
        stream_response.raise_for_status.return_value = None
        stream_context = MagicMock()
        stream_context.__enter__ = MagicMock(return_value=stream_response)
        stream_context.__exit__ = MagicMock(return_value=False)
        http.stream.return_value = stream_context

        url = "https://example.com/pluginfile.php/123/mod_resource/content/1/original.pdf"

        result = download_file(http, url, tmp_path, filename="renamed.pdf")

        assert result == tmp_path / "renamed.pdf"
        assert result.exists()


# ---------------------------------------------------------------------------
# Tests: filename_from_url
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFilenameFromUrl:
    def test_filename_from_url(self):
        """Filename is correctly extracted and decoded from URL."""
        url = "https://aulasvirtuales.frba.utn.edu.ar/pluginfile.php/123/mod_resource/content/1/Apunte%20Tema%201.pdf"
        result = filename_from_url(url)
        assert result == "Apunte Tema 1.pdf"

    def test_filename_from_url_simple(self):
        """Simple filename without encoding."""
        url = "https://example.com/path/to/file.pdf"
        result = filename_from_url(url)
        assert result == "file.pdf"
