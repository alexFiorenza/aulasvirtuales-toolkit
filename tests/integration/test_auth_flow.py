"""Integration tests for the authentication flow."""

from unittest.mock import MagicMock, patch

import pytest

import aulasvirtuales.auth as auth
from aulasvirtuales.client import MoodleClient


@pytest.mark.integration
class TestAuthFlow:
    @patch("aulasvirtuales.auth.is_session_valid")
    @patch("aulasvirtuales.auth.login")
    def test_login_saves_token_and_creates_client(
        self, mock_login, mock_valid, mock_keyring
    ):
        """Full auth flow: save creds → login → save token → create client."""
        mock_login.return_value = "session_cookie_abc123"
        mock_valid.return_value = True

        # Step 1: Save credentials
        auth.save_credentials("student", "password123")

        # Step 2: Retrieve credentials
        creds = auth.get_credentials()
        assert creds == ("student", "password123")

        # Step 3: Login
        token = auth.login(creds[0], creds[1])
        assert token == "session_cookie_abc123"

        # Step 4: Save token
        auth.save_token(token)
        assert auth.get_token() == "session_cookie_abc123"

        # Step 5: Validate session
        assert auth.is_session_valid(token) is True

    @patch("aulasvirtuales.auth.is_session_valid")
    @patch("aulasvirtuales.auth.login")
    def test_expired_session_triggers_relogin(
        self, mock_login, mock_valid, mock_keyring
    ):
        """Expired session token triggers a new login with stored credentials."""
        # First call: session is expired. Second call: new session is valid.
        mock_valid.side_effect = [False, True]
        mock_login.return_value = "new_session_cookie"

        # Setup: have saved creds + expired token
        auth.save_credentials("student", "pass")
        auth.save_token("expired_token")

        # Check: session is invalid
        old_token = auth.get_token()
        assert not auth.is_session_valid(old_token)

        # Re-login
        creds = auth.get_credentials()
        new_token = auth.login(creds[0], creds[1])
        auth.save_token(new_token)

        # New session is valid
        assert auth.get_token() == "new_session_cookie"
        assert auth.is_session_valid(new_token)
