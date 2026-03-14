#!/usr/bin/env python3
"""
Slack OAuth PKCE Flow

OAuth 2.0 PKCE (Public Client) でSlack MCP用トークンを取得する。
ブラウザで認証後、ローカルHTTPサーバーでコールバックを受信。

OAuth設定は https://mcp.slack.com/.well-known/oauth-authorization-server から取得。
"""

import base64
import hashlib
import json
import os
import secrets
import subprocess
import sys
import tempfile
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

sys.path.insert(0, os.path.dirname(__file__))
from token_store import TokenStore, TokenStoreError, CLIENT_ID


# OAuth endpoints (from /.well-known/oauth-authorization-server)
AUTHORIZE_URL = "https://slack.com/oauth/v2_user/authorize"
TOKEN_URL = "https://slack.com/api/oauth.v2.user.access"
CALLBACK_PORT = 3118
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"

# PKCE状態の一時保存先
_PENDING_AUTH_FILE = os.path.join(tempfile.gettempdir(), "slack_oauth_pending.json")

# Supported scopes (from /.well-known/oauth-authorization-server)
SCOPES = ",".join([
    "search:read.public",
    "chat:write",
    "channels:history",
    "groups:history",
    "mpim:history",
    "im:history",
    "users:read",
])


class OAuthError(Exception):
    """OAuth認証エラー"""
    pass


def _is_headless() -> bool:
    """ブラウザが使えない環境かを判定"""
    if os.path.exists("/.dockerenv"):
        return True
    if os.environ.get("CONTAINER") or os.environ.get("container"):
        return True
    if sys.platform == "linux" and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return True
    return False


def _prompt_callback_url(port: int) -> Optional[str]:
    """コールバックURLの手動入力を受け付ける。TTYでない場合はスキップ。"""
    if not sys.stdin.isatty():
        return None
    print(f"\n--- 手動認証モード ---")
    print(f"認証後、ブラウザのアドレスバーに表示されるURL（localhost:{port}/callback?...）を")
    print(f"以下に貼り付けてください（空Enterでコールバックサーバー待機に切替）:")
    try:
        url = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    return url if url else None


def _extract_code_from_url(url: str) -> tuple:
    """URLからcodeとstateを抽出"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    code = params.get("code", [None])[0]
    state = params.get("state", [None])[0]
    error = params.get("error", [None])[0]
    return code, state, error


def _generate_pkce() -> tuple:
    """PKCE code_verifier と code_challenge (S256) を生成"""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _exchange_code(code: str, code_verifier: str) -> dict:
    """認可コードをトークンに交換"""
    data = urlencode({
        "client_id": CLIENT_ID,
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

    if not result.get("ok"):
        raise OAuthError(f"Token exchange failed: {result.get('error', 'unknown')}")

    return result


class _CallbackHandler(BaseHTTPRequestHandler):
    """OAuthコールバック受信ハンドラ"""

    auth_code: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/callback":
            if "code" in params:
                _CallbackHandler.auth_code = params["code"][0]
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
<html><head><meta charset="utf-8"><title>Slack MCP Login</title></head>
<body style="font-family:sans-serif;text-align:center;padding:50px">
<h2>{message}</h2></body></html>"""
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """ログ出力を抑制"""
        pass


def login() -> str:
    """
    OAuth PKCEフローを実行してトークンを取得・保存する。

    Returns:
        保存されたワークスペースキー
    """
    code_verifier, code_challenge = _generate_pkce()
    state = secrets.token_urlsafe(32)

    auth_params = urlencode({
        "client_id": CLIENT_ID,
        "scope": SCOPES,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    auth_url = f"{AUTHORIZE_URL}?{auth_params}"

    headless = _is_headless()

    if headless:
        print("以下のURLをブラウザで開いて認証してください:")
    else:
        print("ブラウザが開きます。Slackワークスペースを選択して認証してください。")
    print(f"\n{auth_url}\n")

    # ブラウザを開く（ヘッドレスでなければ）
    if not headless:
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", auth_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                webbrowser.open(auth_url)
        except Exception:
            pass  # URLは既に表示済み

    # コールバック受信
    code = None

    if headless:
        pasted_url = _prompt_callback_url(CALLBACK_PORT)
        if pasted_url:
            code, received_state, error = _extract_code_from_url(pasted_url)
            if error:
                raise OAuthError(f"OAuth error: {error}")
            if not code:
                raise OAuthError("コールバックURLにcodeが含まれていません")
            # Slackはstateを_CallbackHandlerで検証しないが、念のため
            if received_state != state:
                raise OAuthError("State mismatch: possible CSRF attack")

    if code is None:
        _CallbackHandler.auth_code = None
        _CallbackHandler.error = None

        bind_addr = "0.0.0.0" if headless else "127.0.0.1"
        server = HTTPServer((bind_addr, CALLBACK_PORT), _CallbackHandler)
        server.timeout = 300
        print(f"認証コールバック待機中 (port {CALLBACK_PORT}, bind {bind_addr})...")
        if headless:
            print(f"ポートフォワード（-p {CALLBACK_PORT}:{CALLBACK_PORT}）が設定されていれば自動で完了します。")

        try:
            while _CallbackHandler.auth_code is None and _CallbackHandler.error is None:
                server.handle_request()
                if _CallbackHandler.auth_code is None and _CallbackHandler.error is None:
                    raise OAuthError("コールバック待機がタイムアウトしました（5分）")
        except KeyboardInterrupt:
            raise OAuthError("Login cancelled by user")
        finally:
            server.server_close()

        if _CallbackHandler.error:
            raise OAuthError(f"OAuth error: {_CallbackHandler.error}")

        code = _CallbackHandler.auth_code

    print("認証コード受信。トークンを取得中...")

    # トークン交換
    result = _exchange_code(code, code_verifier)

    # トークン情報を抽出 (v2_user エンドポイントはトップレベルにトークンを返す)
    access_token = result.get("access_token", "")
    refresh_token = result.get("refresh_token", "")
    expires_in = result.get("expires_in", 43200)
    scope = result.get("scope", "")
    team = result.get("team", {})
    team_id = team.get("id", result.get("team_id", ""))
    team_name = team.get("name", result.get("team_name", "unknown"))

    if not access_token:
        raise OAuthError("No access token in response")

    # 保存
    store = TokenStore()
    key = store.save_workspace(
        team_id=team_id,
        team_name=team_name,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        scope=scope,
    )

    print(f"Login successful: {team_name} ({team_id})")
    return key


def login_url_only() -> str:
    """認証URLを生成して出力し、PKCE状態をファイルに保存して即終了。"""
    code_verifier, code_challenge = _generate_pkce()
    state = secrets.token_urlsafe(32)

    auth_params = urlencode({
        "client_id": CLIENT_ID,
        "scope": SCOPES,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    auth_url = f"{AUTHORIZE_URL}?{auth_params}"

    pending = {"code_verifier": code_verifier, "state": state}
    with open(_PENDING_AUTH_FILE, "w") as f:
        json.dump(pending, f)
    os.chmod(_PENDING_AUTH_FILE, 0o600)

    print(auth_url)
    return auth_url


def _save_token(result: dict, code_verifier: str) -> str:
    """トークン交換結果を保存して workspace key を返す"""
    access_token = result.get("access_token", "")
    refresh_token = result.get("refresh_token", "")
    expires_in = result.get("expires_in", 43200)
    scope = result.get("scope", "")
    team = result.get("team", {})
    team_id = team.get("id", result.get("team_id", ""))
    team_name = team.get("name", result.get("team_name", "unknown"))

    if not access_token:
        raise OAuthError("No access token in response")

    store = TokenStore()
    key = store.save_workspace(
        team_id=team_id,
        team_name=team_name,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        scope=scope,
    )

    print(f"Login successful: {team_name} ({team_id})")
    return key


def login_with_code(callback_url: str) -> str:
    """コールバックURLからトークンを取得・保存する。"""
    if not os.path.exists(_PENDING_AUTH_FILE):
        raise OAuthError("保留中の認証がありません。先に login --url-only を実行してください。")

    with open(_PENDING_AUTH_FILE) as f:
        pending = json.load(f)

    code_verifier = pending["code_verifier"]
    expected_state = pending["state"]

    code, received_state, error = _extract_code_from_url(callback_url)

    if error:
        raise OAuthError(f"OAuth error: {error}")
    if not code:
        raise OAuthError("コールバックURLにcodeが含まれていません")
    if received_state != expected_state:
        raise OAuthError("State mismatch: possible CSRF attack")

    print("認証コード受信。トークンを取得中...")
    result = _exchange_code(code, code_verifier)
    key = _save_token(result, code_verifier)

    os.unlink(_PENDING_AUTH_FILE)
    return key


if __name__ == "__main__":
    try:
        login()
    except (OAuthError, TokenStoreError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
