"""Integration tests for download + conversion pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest


def _mock_download_http(files: dict[str, bytes]) -> MagicMock:
    """Create a mock httpx.Client that simulates downloading files.

    Args:
        files: Mapping of filename → file content bytes.
    """
    http = MagicMock(spec=httpx.Client)

    def _stream(method, url, **kwargs):
        # Extract filename from URL
        filename = url.split("/")[-1]
        content = files.get(filename, b"default content")
        response = MagicMock()
        response.iter_bytes.return_value = [content]
        response.raise_for_status.return_value = None
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=response)
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx

    http.stream = _stream
    return http


@pytest.mark.integration
class TestDownloadAndConvert:
    def test_download_saves_file(self, tmp_path):
        """File is downloaded and saved to the destination directory."""
        from aulasvirtuales.downloader import download_file

        http = _mock_download_http({"apunte.pdf": b"PDF content here"})

        url = "https://aulasvirtuales.frba.utn.edu.ar/pluginfile.php/123/mod_resource/content/1/apunte.pdf"
        result = download_file(http, url, tmp_path)

        assert result.exists()
        assert result.name == "apunte.pdf"
        assert result.read_bytes() == b"PDF content here"

    def test_download_and_convert_pdf_to_md(self, tmp_path):
        """Download a PDF file and convert it to markdown."""
        import sys
        mock_inspector = MagicMock()
        mock_inspector.process_pdf.return_value = MagicMock(markdown="# Lecture Notes\n\nContent here")

        with patch.dict(sys.modules, {"pdf_inspector": mock_inspector}):
            from aulasvirtuales.converter import convert_and_save
            from aulasvirtuales.downloader import download_file

            # Step 1: Download
            http = _mock_download_http({"lecture.pdf": b"fake pdf bytes"})
            url = "https://aulasvirtuales.frba.utn.edu.ar/pluginfile.php/1/mod_resource/content/1/lecture.pdf"
            pdf_path = download_file(http, url, tmp_path)

            assert pdf_path.exists()

            # Step 2: Convert
            md_path = convert_and_save(pdf_path, tmp_path)

            assert md_path.exists()
            assert md_path.suffix == ".md"
            assert "Lecture Notes" in md_path.read_text(encoding="utf-8")

    def test_download_folder_multiple_files(self, tmp_path):
        """Multiple files from a folder are downloaded to the same directory."""
        from aulasvirtuales.downloader import download_file

        http = _mock_download_http({
            "file1.pdf": b"content1",
            "file2.pdf": b"content2",
            "file3.pdf": b"content3",
        })

        urls = [
            "https://aulasvirtuales.frba.utn.edu.ar/pluginfile.php/1/mod_folder/content/1/file1.pdf",
            "https://aulasvirtuales.frba.utn.edu.ar/pluginfile.php/1/mod_folder/content/1/file2.pdf",
            "https://aulasvirtuales.frba.utn.edu.ar/pluginfile.php/1/mod_folder/content/1/file3.pdf",
        ]

        paths = [download_file(http, url, tmp_path) for url in urls]

        assert len(paths) == 3
        assert all(p.exists() for p in paths)
        assert paths[0].read_bytes() == b"content1"
        assert paths[2].read_bytes() == b"content3"
