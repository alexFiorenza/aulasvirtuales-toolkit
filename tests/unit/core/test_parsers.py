"""Unit tests for parse_url_redirect and parse_page_content."""

import pytest

from aulasvirtuales.parsers import parse_page_content, parse_url_redirect
from tests.conftest import (
    SAMPLE_PAGE_VIEW_HTML,
    SAMPLE_URL_META_REFRESH_HTML,
    SAMPLE_URL_VIEW_HTML,
)


@pytest.mark.unit
class TestParseUrlRedirect:
    def test_extracts_from_urlworkaround_div(self):
        url = parse_url_redirect(SAMPLE_URL_VIEW_HTML)
        assert url == "https://meet.google.com/abc-def-ghi"

    def test_extracts_from_meta_refresh(self):
        url = parse_url_redirect(SAMPLE_URL_META_REFRESH_HTML)
        assert url == "https://zoom.us/j/123456789"

    def test_returns_none_when_no_url(self):
        assert parse_url_redirect("<html><body>nothing</body></html>") is None

    def test_meta_refresh_takes_precedence_after_missing_workaround(self):
        html = """
        <html><head>
        <meta http-equiv="refresh" content="0; url=https://youtube.com/watch?v=abc">
        </head><body><p>No workaround div here.</p></body></html>
        """
        url = parse_url_redirect(html)
        assert url == "https://youtube.com/watch?v=abc"


@pytest.mark.unit
class TestParsePageContent:
    def test_extracts_text_from_generalbox(self):
        content = parse_page_content(SAMPLE_PAGE_VIEW_HTML)
        assert "Este es el contenido de la página" in content
        assert "Con varios párrafos" in content

    def test_strips_html_tags(self):
        content = parse_page_content(SAMPLE_PAGE_VIEW_HTML)
        assert "<p>" not in content
        assert "<div" not in content

    def test_falls_back_to_full_html_on_no_match(self):
        html = "<html><body><p>Solo texto plano.</p></body></html>"
        content = parse_page_content(html)
        assert "Solo texto plano" in content
