#!/usr/bin/env python3
"""
Todoist OAuth PKCE Flow

OAuth 2.0 PKCE + 動的クライアント登録 (RFC 7591) で
Todoist MCP用トークンを取得する。
ブラウザで認証後、ローカルHTTPサーバーでコールバックを受信。
"""

import base64
import hashlib
import json
import os
import secrets
import subprocess
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

sys.path.insert(0, os.path.dirname(__file__))
from token_store import TokenStore, TokenStoreError


# OAuth endpoints
AUTHORIZE_URL = "https://todoist.com/oauth/authorize"
TOKEN_URL = "https://todoist.com/oauth/access_token"
REGISTER_URL = "https://todoist.com/oauth/register"
CALLBACK_PORT = 3120
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"

SCOPE = "data:read_write"

# 動的クライアント登録パラメータ
CLIENT_NAME = "Claude Code Todoist Plugin"


class OAuthError(Exception):
    """OAuth認証エラー"""
    pass


def _generate_pkce() -> tuple:
    """PKCE code_verifier と code_challenge (S256) を生成"""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _register_client() -> dict:
    """
    動的クライアント登録 (RFC 7591)

    Returns:
        {"client_id": "..."}
    """
    payload = json.dumps({
        "client_name": CLIENT_NAME,
        "redirect_uris": [REDIRECT_URI],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }).encode()

    req = Request(REGISTER_URL, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")

    try:
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
    except (URLError, HTTPError) as e:
        raise OAuthError(f"Client registration failed: {e}") from e

    client_id = result.get("client_id")
    if not client_id:
        raise OAuthError(f"Client registration failed: no client_id in response")

    return {"client_id": client_id}


def _exchange_code(code: str, code_verifier: str, client_id: str) -> dict:
    """認可コードをトークンに交換"""
    data = urlencode({
        "client_id": client_id,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }).encode()

    req = Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
    except (URLError, HTTPError) as e:
        raise OAuthError(f"Token exchange failed: {e}") from e

    if "error" in result:
        error = result.get("error", "unknown")
        desc = result.get("error_description", "")
        raise OAuthError(f"Token exchange failed: {error} {desc}")

    return result


class _CallbackHandler(BaseHTTPRequestHandler):
    """OAuthコールバック受信ハンドラ"""

    auth_code: Optional[str] = None
    received_state: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/callback":
            if "code" in params:
                _CallbackHandler.auth_code = params["code"][0]
                _CallbackHandler.received_state = params.get("state", [None])[0]
                self._respond(200, "認証成功！このタブを閉じてターミナルに戻ってください。")
            elif "error" in params:
                _CallbackHandler.error = params.get("error", ["unknown"])[0]
                self._respond(400, f"認証エラー: {_CallbackHandler.error}")
            else:
                self._respond(400, "不明なコールバック")
        else:
            self._respond(404, "Not Found")

    def _respond(self, status: int, message: str):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Todoist MCP Login</title></head>
<body style="font-family:sans-serif;text-align:center;padding:50px">
<h2>{message}</h2></body></html>"""
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """ログ出力を抑制"""
        pass


def login() -> None:
    """
    OAuth PKCEフローを実行してトークンを取得・保存する。
    初回はクライアント登録も実行。
    """
    store = TokenStore()

    # 1. クライアント登録確認
    creds = store.get_client_credentials()
    if not creds:
        print("クライアント登録を実行中...")
        reg = _register_client()
        store.save_client_credentials(reg["client_id"])
        creds = store.get_client_credentials()
        print("クライアント登録完了。")

    client_id = creds["client_id"]

    # 2. PKCE生成
    code_verifier, code_challenge = _generate_pkce()
    state = secrets.token_urlsafe(32)

    # 3. 認可URL構築
    auth_params = urlencode({
        "client_id": client_id,
        "scope": SCOPE,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    auth_url = f"{AUTHORIZE_URL}?{auth_params}"

    print("ブラウザが開きます。Todoistアカウントで認証してください。")
    print(f"ブラウザが自動で開かない場合は、以下のURLを開いてください:\n{auth_url}\n")

    # 4. ブラウザを開く
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", auth_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            webbrowser.open(auth_url)
    except Exception:
        pass  # URLは既に表示済み

    # 5. コールバックサーバー起動
    _CallbackHandler.auth_code = None
    _CallbackHandler.received_state = None
    _CallbackHandler.error = None

    server = HTTPServer(("127.0.0.1", CALLBACK_PORT), _CallbackHandler)
    print(f"認証コールバック待機中 (port {CALLBACK_PORT})...")

    try:
        while _CallbackHandler.auth_code is None and _CallbackHandler.error is None:
            server.handle_request()
    except KeyboardInterrupt:
        raise OAuthError("Login cancelled by user")
    finally:
        server.server_close()

    if _CallbackHandler.error:
        raise OAuthError(f"OAuth error: {_CallbackHandler.error}")

    # 6. state検証
    if _CallbackHandler.received_state != state:
        raise OAuthError("State mismatch: possible CSRF attack")

    code = _CallbackHandler.auth_code
    print("認証コード受信。トークンを取得中...")

    # 7. トークン交換
    result = _exchange_code(code, code_verifier, client_id)

    access_token = result.get("access_token", "")
    scope = result.get("scope", SCOPE)

    if not access_token:
        raise OAuthError("No access token in response")

    # 8. トークン保存
    store.save_auth(
        access_token=access_token,
        scope=scope,
    )

    print("Login successful!")


if __name__ == "__main__":
    try:
        login()
    except (OAuthError, TokenStoreError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
