"""
Google OAuth 2.0 Authentication Helper for Python.
Provides a local callback server to handle redirection and exchange auth codes for tokens.
"""

import os
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

# Constants
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
DEFAULT_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email"
]

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """
    Lightweight HTTP Request Handler that intercepts the Google OAuth redirect
    containing the authorization code.
    """
    def log_message(self, format, *args):
        # Suppress server logs in console for a cleaner CLI interface
        pass

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        if 'code' in query_params:
            self.server.auth_code = query_params['code'][0]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            success_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Successful</title>
                <style>
                    body {
                        font-family: 'Outfit', 'Inter', sans-serif;
                        background: radial-gradient(circle at center, #1e1e2f, #0f0f1a);
                        color: #ffffff;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .card {
                        background: rgba(255, 255, 255, 0.05);
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 16px;
                        padding: 40px;
                        text-align: center;
                        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
                        max-width: 400px;
                    }
                    h1 {
                        color: #4285F4;
                        margin-bottom: 10px;
                        font-size: 24px;
                    }
                    p {
                        color: #b0b0cc;
                        font-size: 16px;
                        line-height: 1.5;
                    }
                    .icon {
                        font-size: 48px;
                        margin-bottom: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="icon">🚀</div>
                    <h1>Login Successful!</h1>
                    <p>You have successfully authenticated with Google. You can safely close this tab and return to the terminal.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode('utf-8'))
        else:
            self.send_response(400)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            error_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Failed</title>
                <style>
                    body {
                        font-family: 'Outfit', 'Inter', sans-serif;
                        background: radial-gradient(circle at center, #2f1e1e, #1a0f0f);
                        color: #ffffff;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .card {
                        background: rgba(255, 255, 255, 0.05);
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 16px;
                        padding: 40px;
                        text-align: center;
                        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
                        max-width: 400px;
                    }
                    h1 {
                        color: #ea4335;
                        margin-bottom: 10px;
                        font-size: 24px;
                    }
                    p {
                        color: #ccb0b0;
                        font-size: 16px;
                        line-height: 1.5;
                    }
                    .icon {
                        font-size: 48px;
                        margin-bottom: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="icon">⚠️</div>
                    <h1>Authentication Failed</h1>
                    <p>Authorization code not found. Please try logging in again.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode('utf-8'))


def get_google_auth_url(client_id: str, redirect_uri: str, scopes: list = None) -> str:
    """
    Constructs the Google OAuth 2.0 authorization URL.
    """
    if scopes is None:
        scopes = DEFAULT_SCOPES
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent"
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def run_local_server(port: int = 8080) -> str:
    """
    Runs a local HTTP server to listen for the redirect callback.
    Blocks until the authorization code is retrieved.
    """
    server = HTTPServer(('localhost', port), OAuthCallbackHandler)
    server.auth_code = None
    
    print(f"\n[OAuth] Waiting for authentication on http://localhost:{port}...")
    
    # Process requests until we capture the authorization code
    while server.auth_code is None:
        server.handle_request()
        
    return server.auth_code


def exchange_code_for_tokens(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    """
    Exchanges the authorization code for access, ID, and refresh tokens.
    """
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    response = requests.post(GOOGLE_TOKEN_URL, data=data)
    response.raise_for_status()
    return response.json()


def get_user_info(access_token: str) -> dict:
    """
    Retrieves the authenticated user's profile information.
    """
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(GOOGLE_USERINFO_URL, headers=headers)
    response.raise_for_status()
    return response.json()


def login(client_id: str = None, client_secret: str = None, port: int = 8080) -> dict:
    """
    Main login flow coordination function.
    """
    # Fallback to environment variables if not passed directly
    client_id = client_id or os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = client_secret or os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError(
            "Missing Google client ID or client secret. "
            "Please provide them as arguments or set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env variables."
        )
        
    redirect_uri = f"http://localhost:{port}/"
    auth_url = get_google_auth_url(client_id, redirect_uri)
    
    print(f"\n[OAuth] Opening browser for authentication...")
    print(f"[OAuth] If it doesn't open automatically, please visit: {auth_url}\n")
    
    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"[OAuth] Could not automatically open browser: {e}")
        
    # Start local server to capture the code
    auth_code = run_local_server(port)
    print("[OAuth] Authorization code captured successfully.")
    
    # Exchange code for tokens
    print("[OAuth] Exchanging authorization code for tokens...")
    tokens = exchange_code_for_tokens(client_id, client_secret, auth_code, redirect_uri)
    
    # Retrieve user profile info
    print("[OAuth] Fetching user profile information...")
    user_info = get_user_info(tokens['access_token'])
    
    return {
        "tokens": tokens,
        "user_info": user_info
    }


if __name__ == "__main__":
    # Standard entry point for direct script testing
    print("=== Google Login CLI Client ===")
    try:
        result = login()
        print("\n=== Authentication Complete! ===")
        print(f"User: {result['user_info'].get('name')} ({result['user_info'].get('email')})")
        print(f"Access Token: {result['tokens'].get('access_token')[:15]}...")
    except ValueError as val_err:
        print(f"\n[Configuration Error] {val_err}")
    except Exception as err:
        print(f"\n[Error] Authentication failed: {err}")
