"""Unit tests for aulasvirtuales.converter — format conversion functions."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest


@pytest.mark.unit
class TestPdfToMarkdown:
    def test_pdf_to_markdown(self, tmp_path):
        """PDF is converted to markdown string via pymupdf4llm."""
        mock_module = MagicMock()
        mock_module.to_markdown.return_value = "# Heading\n\nSome content"

        with patch.dict(sys.modules, {"pymupdf4llm": mock_module}):
            from aulasvirtuales.converter import pdf_to_markdown

            pdf_path = tmp_path / "test.pdf"
            pdf_path.write_bytes(b"fake pdf content")

            result = pdf_to_markdown(pdf_path)

            assert result == "# Heading\n\nSome content"
            mock_module.to_markdown.assert_called_once_with(str(pdf_path))


@pytest.mark.unit
class TestConvertAndSave:
    def test_convert_and_save_creates_file(self, tmp_path):
        """Converted markdown is saved to disk with .md extension."""
        mock_module = MagicMock()
        mock_module.to_markdown.return_value = "# Test\n\nContent"

        with patch.dict(sys.modules, {"pymupdf4llm": mock_module}):
            from aulasvirtuales.converter import convert_and_save

            pdf_path = tmp_path / "document.pdf"
            pdf_path.write_bytes(b"fake pdf")

            result = convert_and_save(pdf_path)

            assert result == tmp_path / "document.md"
            assert result.exists()
            assert result.read_text(encoding="utf-8") == "# Test\n\nContent"

    def test_convert_and_save_custom_output_dir(self, tmp_path):
        """Markdown file is saved to custom output directory."""
        mock_module = MagicMock()
        mock_module.to_markdown.return_value = "# Content"

        with patch.dict(sys.modules, {"pymupdf4llm": mock_module}):
            from aulasvirtuales.converter import convert_and_save

            pdf_path = tmp_path / "input" / "doc.pdf"
            pdf_path.parent.mkdir()
            pdf_path.write_bytes(b"fake")

            output_dir = tmp_path / "output"

            result = convert_and_save(pdf_path, output_dir=output_dir)

            assert result == output_dir / "doc.md"
            assert result.exists()


@pytest.mark.unit
class TestDocxToMarkdown:
    def test_docx_to_markdown_via_mammoth(self, tmp_path):
        """DOCX is converted to markdown directly via mammoth."""
        mock_mammoth = MagicMock()
        mock_mammoth.convert_to_markdown.return_value = MagicMock(
            value="# Document Title\n\nParagraph content"
        )

        with patch.dict(sys.modules, {"mammoth": mock_mammoth}):
            from aulasvirtuales.converter import DocxToMarkdown

            docx_path = tmp_path / "report.docx"
            docx_path.write_bytes(b"fake docx")

            result = DocxToMarkdown().convert(docx_path)

            assert result == tmp_path / "report.md"
            assert result.exists()
            assert result.read_text(encoding="utf-8") == "# Document Title\n\nParagraph content"

    def test_docx_to_markdown_custom_output_dir(self, tmp_path):
        """Markdown file is saved to custom output directory."""
        mock_mammoth = MagicMock()
        mock_mammoth.convert_to_markdown.return_value = MagicMock(value="# Content")

        with patch.dict(sys.modules, {"mammoth": mock_mammoth}):
            from aulasvirtuales.converter import DocxToMarkdown

            docx_path = tmp_path / "input" / "doc.docx"
            docx_path.parent.mkdir()
            docx_path.write_bytes(b"fake")

            output_dir = tmp_path / "output"

            result = DocxToMarkdown().convert(docx_path, output_dir)

            assert result == output_dir / "doc.md"
            assert result.exists()


@pytest.mark.unit
class TestDocxToPdf:
    def test_docx_to_pdf_libreoffice_missing(self, monkeypatch):
        """FileNotFoundError is raised when LibreOffice is not installed."""
        import shutil

        monkeypatch.setattr(shutil, "which", lambda _: None)

        from aulasvirtuales.converter import docx_to_pdf

        with pytest.raises(FileNotFoundError, match="LibreOffice"):
            docx_to_pdf(Path("/fake/file.docx"))


@pytest.mark.unit
class TestPptxToPdf:
    def test_pptx_to_pdf_libreoffice_missing(self, monkeypatch):
        """FileNotFoundError is raised when LibreOffice is not installed."""
        import shutil

        monkeypatch.setattr(shutil, "which", lambda _: None)

        from aulasvirtuales.converter import pptx_to_pdf

        with pytest.raises(FileNotFoundError, match="LibreOffice"):
            pptx_to_pdf(Path("/fake/file.pptx"))
