"""Unit tests for aulasvirtuales.auth — authentication functions."""

from unittest.mock import MagicMock

import pytest

from aulasvirtuales.auth import (
    AuthenticationError,
    InvalidCredentialsError,
    _has_keycloak_error,
    delete_credentials,
    delete_token,
    get_credentials,
    get_token,
    is_session_valid,
    login,
    save_credentials,
    save_token,
    SERVICE_NAME,
)


@pytest.mark.unit
class TestCredentialStorage:
    def test_save_and_get_credentials(self, mock_keyring):
        """Credentials can be saved and retrieved from keyring."""
        save_credentials("testuser", "testpass")

        result = get_credentials()

        assert result == ("testuser", "testpass")
        assert mock_keyring[(SERVICE_NAME, "username")] == "testuser"
        assert mock_keyring[(SERVICE_NAME, "password")] == "testpass"

    def test_get_credentials_missing(self, mock_keyring):
        """Returns None when no credentials are stored."""
        result = get_credentials()

        assert result is None

    def test_delete_credentials(self, mock_keyring):
        """Credentials are removed from keyring."""
        save_credentials("testuser", "testpass")
        delete_credentials()

        assert get_credentials() is None
        assert (SERVICE_NAME, "username") not in mock_keyring
        assert (SERVICE_NAME, "password") not in mock_keyring

    def test_delete_credentials_when_missing(self, mock_keyring):
        """Deleting non-existent credentials does not raise."""
        # Should not raise
        delete_credentials()


@pytest.mark.unit
class TestTokenStorage:
    def test_save_and_get_token(self, mock_keyring):
        """Session token can be saved and retrieved."""
        save_token("session_abc123")

        result = get_token()

        assert result == "session_abc123"

    def test_get_token_missing(self, mock_keyring):
        """Returns None when no token is stored."""
        result = get_token()

        assert result is None

    def test_delete_token(self, mock_keyring):
        """Token is removed from keyring."""
        save_token("session_abc123")
        delete_token()

        assert get_token() is None

    def test_delete_token_when_missing(self, mock_keyring):
        """Deleting non-existent token does not raise."""
        delete_token()


@pytest.mark.unit
class TestSessionValidation:
    def test_is_session_valid_true(self, monkeypatch):
        """Session is valid when GET /my/ returns 200."""
        import httpx

        mock_response = type("Response", (), {"status_code": 200})()
        monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: mock_response)

        assert is_session_valid("valid_cookie") is True

    def test_is_session_valid_false(self, monkeypatch):
        """Session is invalid when GET /my/ returns redirect."""
        import httpx

        mock_response = type("Response", (), {"status_code": 302})()
        monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: mock_response)

        assert is_session_valid("expired_cookie") is False


@pytest.mark.unit
class TestKeycloakErrorDetection:
    def test_detects_input_error(self):
        page = MagicMock()
        page.query_selector.side_effect = lambda sel: "el" if sel == "#input-error" else None

        assert _has_keycloak_error(page) is True

    def test_detects_alert_error(self):
        page = MagicMock()
        page.query_selector.side_effect = lambda sel: "el" if sel == ".alert-error" else None

        assert _has_keycloak_error(page) is True

    def test_no_error_elements(self):
        page = MagicMock()
        page.query_selector.return_value = None

        assert _has_keycloak_error(page) is False


@pytest.mark.unit
class TestLoginErrorHandling:
    """Login raises typed errors based on Playwright state."""

    @pytest.fixture
    def mock_playwright(self, monkeypatch):
        """Mock the full sync_playwright context manager chain."""
        from playwright.sync_api import TimeoutError as PWTimeout

        page = MagicMock()
        page.url = "https://sso.frba.utn.edu.ar/auth/realms/utn/login"
        page.query_selector.return_value = None

        context = MagicMock()
        context.new_page.return_value = page
        context.cookies.return_value = []

        browser = MagicMock()
        browser.new_context.return_value = context

        pw = MagicMock()
        pw.chromium.launch.return_value = browser

        pw_cm = MagicMock()
        pw_cm.__enter__.return_value = pw
        pw_cm.__exit__.return_value = False

        monkeypatch.setattr(
            "aulasvirtuales.auth.sync_playwright", lambda: pw_cm
        )
        return {"page": page, "context": context, "timeout_error": PWTimeout}

    def test_invalid_credentials_detected(self, mock_playwright):
        """Keycloak error element after timeout → InvalidCredentialsError."""
        page = mock_playwright["page"]
        page.wait_for_url.side_effect = mock_playwright["timeout_error"]("timeout")
        page.query_selector.side_effect = (
            lambda sel: "err" if sel == "#input-error" else None
        )

        with pytest.raises(InvalidCredentialsError):
            login("user", "wrong")

    def test_sso_timeout_without_error_element(self, mock_playwright):
        """Timeout with no Keycloak error → generic AuthenticationError."""
        page = mock_playwright["page"]
        page.wait_for_url.side_effect = mock_playwright["timeout_error"]("timeout")
        page.query_selector.return_value = None

        with pytest.raises(AuthenticationError) as exc_info:
            login("user", "pw")

        assert not isinstance(exc_info.value, InvalidCredentialsError)

    def test_username_selector_timeout(self, mock_playwright):
        """Timeout waiting for the username input → AuthenticationError (SSO down)."""
        page = mock_playwright["page"]
        page.wait_for_selector.side_effect = mock_playwright["timeout_error"]("timeout")

        with pytest.raises(AuthenticationError) as exc_info:
            login("user", "pw")

        assert "portal SSO" in str(exc_info.value)

    def test_successful_login_returns_cookie(self, mock_playwright):
        """Happy path: MoodleSession cookie is returned."""
        mock_playwright["context"].cookies.return_value = [
            {"name": "MoodleSession", "value": "cookie_abc"},
            {"name": "other", "value": "ignored"},
        ]

        token = login("user", "pw")

        assert token == "cookie_abc"
