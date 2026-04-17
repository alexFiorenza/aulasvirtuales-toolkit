"""Unit tests for aulasvirtuales.reader."""

from unittest.mock import MagicMock

import httpx
import pytest

from aulasvirtuales.models import Resource
from aulasvirtuales.reader import read_resource
from tests.conftest import SAMPLE_PAGE_VIEW_HTML, SAMPLE_URL_VIEW_HTML


def _mock_http(html: str) -> MagicMock:
    client = MagicMock(spec=httpx.Client)
    response = MagicMock()
    response.text = html
    client.get.return_value = response
    return client


@pytest.mark.unit
class TestReadResource:
    def test_read_label_returns_stripped_description(self):
        resource = Resource(id=5, name="Aviso", module="label", description="<p>Leer antes del parcial.</p>")
        result = read_resource(MagicMock(), resource)
        assert result.module == "label"
        assert result.resource_id == 5
        assert result.content == "Leer antes del parcial."

    def test_read_label_falls_back_to_name_when_no_description(self):
        # Moodle puts label HTML in cm["name"] — description may be absent
        resource = Resource(id=5, name="Leer antes de la clase", module="label", description=None)
        result = read_resource(MagicMock(), resource)
        assert result.content == "Leer antes de la clase"

    def test_read_url_extracts_external_url(self):
        http = _mock_http(SAMPLE_URL_VIEW_HTML)
        resource = Resource(id=7, name="Campus", module="url", url="/mod/url/view.php?id=7")
        result = read_resource(http, resource)
        assert result.module == "url"
        assert result.resource_id == 7
        assert result.content == "https://meet.google.com/abc-def-ghi"
        http.get.assert_called_once_with("/mod/url/view.php?id=7", follow_redirects=True)

    def test_read_url_no_url_field_raises(self):
        resource = Resource(id=7, name="Link", module="url", url=None)
        with pytest.raises(ValueError, match="has no url"):
            read_resource(MagicMock(), resource)

    def test_read_url_no_redirect_found_raises(self):
        http = _mock_http("<html><body>no link here</body></html>")
        resource = Resource(id=7, name="Link", module="url", url="/mod/url/view.php?id=7")
        with pytest.raises(ValueError, match="Could not extract redirect URL"):
            read_resource(http, resource)

    def test_read_page_extracts_text(self):
        http = _mock_http(SAMPLE_PAGE_VIEW_HTML)
        resource = Resource(id=6, name="Reglamento", module="page", url="/mod/page/view.php?id=6")
        result = read_resource(http, resource)
        assert result.module == "page"
        assert result.resource_id == 6
        assert "contenido de la página" in result.content
        http.get.assert_called_once_with("/mod/page/view.php?id=6", follow_redirects=True)

    def test_read_page_no_url_field_raises(self):
        resource = Resource(id=6, name="Page", module="page", url=None)
        with pytest.raises(ValueError, match="has no url"):
            read_resource(MagicMock(), resource)

    def test_unsupported_module_raises(self):
        resource = Resource(id=1, name="Quiz", module="quiz")
        with pytest.raises(ValueError, match="not supported"):
            read_resource(MagicMock(), resource)
