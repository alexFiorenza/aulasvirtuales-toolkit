"""Unit tests for aulasvirtuales.auth — authentication functions."""

import pytest

from aulasvirtuales.auth import (
    delete_credentials,
    delete_token,
    get_credentials,
    get_token,
    is_session_valid,
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
