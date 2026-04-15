"""Integration tests for MCP tools — end-to-end internal flows."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aulasvirtuales.client import Course, Resource, Section


@pytest.mark.integration
class TestMcpToolsPipeline:
    @patch("aulasvirtuales_mcp.tools.downloads.get_download_dir")
    @patch("aulasvirtuales_mcp.tools.downloads.download_file")
    @patch("aulasvirtuales_mcp.tools.downloads.get_resource_files")
    @patch("aulasvirtuales_mcp.tools.downloads.get_client")
    @pytest.mark.asyncio
    async def test_mcp_download_basic(
        self, mock_get_client, mock_get_files, mock_download, mock_get_dir, tmp_path
    ):
        """MCP download tool finds resource, gets URLs, and downloads files."""
        from aulasvirtuales_mcp.tools.downloads import download

        mock_client = MagicMock()
        mock_client.get_course_contents.return_value = [
            Section(
                id=1, number=1, name="Unidad 1",
                resources=[Resource(id=10, name="Apunte.pdf", module="resource")],
            ),
        ]
        mock_get_client.return_value = mock_client
        mock_get_files.return_value = ["https://example.com/apunte.pdf"]

        downloaded_path = tmp_path / "apunte.pdf"
        downloaded_path.write_bytes(b"content")
        mock_download.return_value = downloaded_path

        mock_get_dir.return_value = tmp_path

        ctx = MagicMock()
        result = await download(course_id=101, resource_id=10, ctx=ctx)

        assert "Downloaded" in result
        assert "apunte.pdf" in result

    @patch("aulasvirtuales_mcp.tools.downloads.get_download_dir")
    def test_mcp_read_downloaded_file_lists_files(self, mock_get_dir, tmp_path):
        """read_downloaded_file lists files when no filename is given."""
        from aulasvirtuales_mcp.tools.downloads import read_downloaded_file

        (tmp_path / "apunte.md").write_text("# Content")
        (tmp_path / "notes.txt").write_text("Notes")
        mock_get_dir.return_value = tmp_path

        result = read_downloaded_file()

        assert len(result) == 1
        assert "apunte.md" in result[0]
        assert "notes.txt" in result[0]
