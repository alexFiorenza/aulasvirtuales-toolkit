"""Unit tests for aulasvirtuales.ocr — OCR pipeline via vision LLMs."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestGetLlm:
    def test_get_llm_valid_provider(self):
        """Known providers instantiate the correct class."""
        from aulasvirtuales.ocr import _get_llm

        mock_module = MagicMock()
        mock_cls = MagicMock()
        mock_module.ChatOllama = mock_cls

        with patch("importlib.import_module", return_value=mock_module):
            result = _get_llm("ollama", "llava")

        mock_cls.assert_called_once_with(model="llava")

    def test_get_llm_unknown_provider_raises(self):
        """ValueError is raised for unknown providers."""
        from aulasvirtuales.ocr import _get_llm

        with pytest.raises(ValueError, match="Unknown provider"):
            _get_llm("nonexistent", "model")


@pytest.mark.unit
class TestOcrImage:
    def test_ocr_image_returns_content(self):
        """Single image OCR returns extracted text from LLM."""
        from aulasvirtuales.ocr import _ocr_image

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="# Extracted heading\n\nSome text")

        result = _ocr_image(b"fake_image_bytes", mock_llm, "image/png", "Extract text")

        assert result == "# Extracted heading\n\nSome text"
        mock_llm.invoke.assert_called_once()


@pytest.mark.unit
class TestOcrAndSave:
    @patch("aulasvirtuales.ocr._get_llm")
    @patch("aulasvirtuales.ocr._pdf_to_images")
    async def test_ocr_and_save_pdf(self, mock_pdf_to_images, mock_get_llm, tmp_path):
        """Multi-page PDF OCR produces markdown with page separators."""
        from aulasvirtuales.ocr import ocr_and_save

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="Page 1 content"),
            MagicMock(content="Page 2 content"),
        ]
        mock_get_llm.return_value = mock_llm

        mock_pdf_to_images.return_value = [b"page1_png", b"page2_png"]

        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake pdf data")

        result = await ocr_and_save(pdf_path, "ollama", "llava", output_dir=tmp_path)

        assert result.suffix == ".md"
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "Page 1 content" in content
        assert "Page 2 content" in content
        assert "---" in content

    @patch("aulasvirtuales.ocr._get_llm")
    async def test_ocr_and_save_image(self, mock_get_llm, tmp_path):
        """Single image file OCR saves extracted text."""
        from aulasvirtuales.ocr import ocr_and_save

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Text from image")
        mock_get_llm.return_value = mock_llm

        img_path = tmp_path / "photo.png"
        img_path.write_bytes(b"fake png data")

        result = await ocr_and_save(img_path, "ollama", "llava", output_dir=tmp_path)

        assert result == tmp_path / "photo.md"
        assert result.read_text(encoding="utf-8") == "Text from image"

    @patch("aulasvirtuales.ocr._get_llm")
    async def test_ocr_and_save_with_page_callback(self, mock_get_llm, tmp_path):
        """Page callback is invoked for progress tracking."""
        from aulasvirtuales.ocr import ocr_and_save

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Content")
        mock_get_llm.return_value = mock_llm

        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"fake")

        pages_tracked = []

        async def on_page(current, total):
            pages_tracked.append((current, total))

        await ocr_and_save(
            img_path, "ollama", "llava", output_dir=tmp_path, on_page=on_page
        )

        assert len(pages_tracked) == 1
        assert pages_tracked[0] == (1, 1)

    @patch("aulasvirtuales.ocr._get_llm")
    @patch("aulasvirtuales.ocr._pdf_to_images")
    async def test_ocr_and_save_reports_status(self, mock_pdf_to_images, mock_get_llm, tmp_path):
        """on_status callback receives step descriptions during OCR."""
        from aulasvirtuales.ocr import ocr_and_save

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="Page 1"),
            MagicMock(content="Page 2"),
        ]
        mock_get_llm.return_value = mock_llm
        mock_pdf_to_images.return_value = [b"img1", b"img2"]

        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes(b"fake pdf")

        statuses: list[str] = []

        async def on_status(message: str) -> None:
            statuses.append(message)

        await ocr_and_save(
            pdf_path, "ollama", "llava", output_dir=tmp_path, on_status=on_status
        )

        assert any("Rendering" in s for s in statuses)
        assert any("page 1/2" in s for s in statuses)
        assert any("page 2/2" in s for s in statuses)

    @patch("aulasvirtuales.ocr._get_llm")
    @patch("aulasvirtuales.ocr._pdf_to_images")
    async def test_ocr_and_save_reports_status_convert_step(
        self, mock_pdf_to_images, mock_get_llm, tmp_path
    ):
        """on_status reports conversion step for non-PDF files."""
        from aulasvirtuales.ocr import ocr_and_save

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Content")
        mock_get_llm.return_value = mock_llm
        mock_pdf_to_images.return_value = [b"img1"]

        docx_path = tmp_path / "report.docx"
        docx_path.write_bytes(b"fake docx")

        statuses: list[str] = []

        async def on_status(message: str) -> None:
            statuses.append(message)

        with patch("aulasvirtuales.ocr._ensure_pdf", return_value=(tmp_path / "report.pdf", False)):
            (tmp_path / "report.pdf").write_bytes(b"fake pdf")
            await ocr_and_save(
                docx_path, "ollama", "llava", output_dir=tmp_path, on_status=on_status
            )

        assert any("Converting" in s for s in statuses)

    @patch("aulasvirtuales.ocr._get_llm")
    @patch("aulasvirtuales.ocr._pdf_to_images")
    async def test_ocr_and_save_page_error_includes_page_number(
        self, mock_pdf_to_images, mock_get_llm, tmp_path
    ):
        """RuntimeError includes page number when OCR fails on a specific page."""
        from aulasvirtuales.ocr import ocr_and_save

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="Page 1 OK"),
            Exception("connection timeout"),
        ]
        mock_get_llm.return_value = mock_llm
        mock_pdf_to_images.return_value = [b"img1", b"img2", b"img3"]

        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes(b"fake pdf")

        with pytest.raises(RuntimeError, match="page 2/3"):
            await ocr_and_save(pdf_path, "ollama", "llava", output_dir=tmp_path)
