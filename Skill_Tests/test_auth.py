import unittest
from unittest.mock import patch, MagicMock
import urllib.parse
import sys
import os

# Add the directory containing auth.py to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth import (
    get_google_auth_url,
    exchange_code_for_tokens,
    get_user_info,
    OAuthCallbackHandler,
    login
)

class TestGoogleAuth(unittest.TestCase):
    def test_get_google_auth_url(self):
        client_id = "test-client-id"
        redirect_uri = "http://localhost:8080/"
        scopes = ["openid", "email"]

        url = get_google_auth_url(client_id, redirect_uri, scopes)
        parsed = urllib.parse.urlparse(url)

        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "accounts.google.com")
        self.assertEqual(parsed.path, "/o/oauth2/v2/auth")

        query = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(query["client_id"][0], client_id)
        self.assertEqual(query["redirect_uri"][0], redirect_uri)
        self.assertEqual(query["response_type"][0], "code")
        self.assertEqual(query["scope"][0], "openid email")
        self.assertEqual(query["access_type"][0], "offline")
        self.assertEqual(query["prompt"][0], "consent")

    @patch("requests.post")
    def test_exchange_code_for_tokens(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "mock-access-token",
            "refresh_token": "mock-refresh-token",
            "expires_in": 3600
        }
        mock_post.return_value = mock_response

        tokens = exchange_code_for_tokens(
            client_id="id",
            client_secret="secret",
            code="auth-code",
            redirect_uri="http://localhost:8080/"
        )

        self.assertEqual(tokens["access_token"], "mock-access-token")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://oauth2.googleapis.com/token")
        self.assertEqual(kwargs["data"]["code"], "auth-code")

    @patch("requests.get")
    def test_get_user_info(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "email": "test@example.com",
            "name": "Test User"
        }
        mock_get.return_value = mock_response

        info = get_user_info("mock-access-token")
        self.assertEqual(info["email"], "test@example.com")
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer mock-access-token")

    @patch("auth.webbrowser.open")
    @patch("auth.run_local_server")
    @patch("auth.exchange_code_for_tokens")
    @patch("auth.get_user_info")
    def test_login_flow(self, mock_get_user_info, mock_exchange, mock_run_server, mock_webbrowser):
        mock_run_server.return_value = "code-123"
        mock_exchange.return_value = {"access_token": "token-123"}
        mock_get_user_info.return_value = {"email": "user@example.com", "name": "Vibe Coder"}

        res = login(client_id="test_id", client_secret="test_secret")

        self.assertEqual(res["user_info"]["name"], "Vibe Coder")
        mock_webbrowser.assert_called_once()
        mock_run_server.assert_called_once()
        mock_exchange.assert_called_once_with(
            "test_id", "test_secret", "code-123", "http://localhost:8080/"
        )
        mock_get_user_info.assert_called_once_with("token-123")

    @patch("http.server.BaseHTTPRequestHandler.__init__", return_value=None)
    def test_handler_success(self, mock_init):
        mock_server = MagicMock()
        mock_server.auth_code = None

        handler = OAuthCallbackHandler()
        handler.server = mock_server
        handler.path = "/?code=captured-auth-code"
        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_GET()

        self.assertEqual(mock_server.auth_code, "captured-auth-code")
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_called_once_with('Content-Type', 'text/html')
        handler.end_headers.assert_called_once()
        handler.wfile.write.assert_called()

if __name__ == "__main__":
    unittest.main()
