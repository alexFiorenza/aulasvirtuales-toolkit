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
    def test_ocr_and_save_pdf(self, mock_pdf_to_images, mock_get_llm, tmp_path):
        """Multi-page PDF OCR produces markdown with page separators."""
        from aulasvirtuales.ocr import ocr_and_save

        # Setup mock LLM
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = [
            MagicMock(content="Page 1 content"),
            MagicMock(content="Page 2 content"),
        ]
        mock_get_llm.return_value = mock_llm

        # Setup mock PDF-to-images
        mock_pdf_to_images.return_value = [b"page1_png", b"page2_png"]

        # Create fake PDF
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake pdf data")

        result = ocr_and_save(pdf_path, "ollama", "llava", output_dir=tmp_path)

        assert result.suffix == ".md"
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "Page 1 content" in content
        assert "Page 2 content" in content
        assert "---" in content  # Page separator

    @patch("aulasvirtuales.ocr._get_llm")
    def test_ocr_and_save_image(self, mock_get_llm, tmp_path):
        """Single image file OCR saves extracted text."""
        from aulasvirtuales.ocr import ocr_and_save

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Text from image")
        mock_get_llm.return_value = mock_llm

        img_path = tmp_path / "photo.png"
        img_path.write_bytes(b"fake png data")

        result = ocr_and_save(img_path, "ollama", "llava", output_dir=tmp_path)

        assert result == tmp_path / "photo.md"
        assert result.read_text(encoding="utf-8") == "Text from image"

    @patch("aulasvirtuales.ocr._get_llm")
    def test_ocr_and_save_with_page_callback(self, mock_get_llm, tmp_path):
        """Page callback is invoked for progress tracking."""
        from aulasvirtuales.ocr import ocr_and_save

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Content")
        mock_get_llm.return_value = mock_llm

        img_path = tmp_path / "test.jpg"
        img_path.write_bytes(b"fake")

        pages_tracked = []

        def on_page(current, total):
            pages_tracked.append((current, total))

        ocr_and_save(img_path, "ollama", "llava", output_dir=tmp_path, on_page=on_page)

        assert len(pages_tracked) == 1
        assert pages_tracked[0] == (1, 1)
