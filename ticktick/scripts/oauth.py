#!/usr/bin/env python3
"""
TickTick OAuth 2.0 Authorization Code Flow

OAuth 2.0 Authorization Code で TickTick API用トークンを取得する。
ブラウザで認証後、ローカルHTTPサーバーでコールバックを受信。

事前準備:
  https://developer.ticktick.com/ でアプリ登録し、
  client_id と client_secret を取得すること。
  Redirect URI には http://localhost:3121/callback を設定すること。
"""

import base64
import html as html_module
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Tuple
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

sys.path.insert(0, os.path.dirname(__file__))
from token_store import TokenStore, TokenStoreError


AUTHORIZE_URL = "https://ticktick.com/oauth/authorize"
TOKEN_URL = "https://ticktick.com/oauth/token"
CALLBACK_PORT = 3121
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"

SCOPE = "tasks:read tasks:write"

# ヘッドレス2ステップ認証で pending state ファイルのパスを渡す環境変数
_PENDING_AUTH_ENV = "TICKTICK_OAUTH_PENDING_FILE"


class OAuthError(Exception):
    """OAuth認証エラー"""
    pass


def _is_headless() -> bool:
    if os.path.exists("/.dockerenv"):
        return True
    if os.environ.get("CONTAINER") or os.environ.get("container"):
        return True
    if sys.platform == "linux" and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return True
    return False


def _prompt_callback_url(port: int) -> Optional[str]:
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


def _extract_code_from_url(url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """URLからcode, state, errorを抽出"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    code = params.get("code", [None])[0]
    state = params.get("state", [None])[0]
    error = params.get("error", [None])[0]
    return code, state, error


def _exchange_code(code: str, client_id: str, client_secret: str) -> dict:
    """認可コードをトークンに交換"""
    data = urlencode({
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }).encode()

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    req = Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Authorization", f"Basic {credentials}")

    try:
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
    except HTTPError as e:
        # Fix #4: エラーボディを本文に含めない（ログには出さない）
        raise OAuthError(f"Token exchange failed: HTTP {e.code}") from e
    except URLError as e:
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
                # Fix #2: XSS防止のためエスケープ
                self._respond(400, f"認証エラー: {html_module.escape(_CallbackHandler.error)}")
            else:
                self._respond(400, "不明なコールバック")
        else:
            self._respond(404, "Not Found")

    def _respond(self, status: int, message: str):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        # Fix #2: message は呼び出し元でエスケープ済み
        body = (
            "<!DOCTYPE html>"
            "<html><head><meta charset=\"utf-8\"><title>TickTick MCP Login</title></head>"
            "<body style=\"font-family:sans-serif;text-align:center;padding:50px\">"
            f"<h2>{message}</h2></body></html>"
        )
        self.wfile.write(body.encode())

    def log_message(self, format, *args):
        pass


def _load_client_credentials() -> Tuple[str, str]:
    """ストアからclient_id, client_secretを取得"""
    store = TokenStore()
    creds = store.get_client_credentials()
    if not creds:
        raise OAuthError(
            "クライアント情報が設定されていません。\n"
            "https://developer.ticktick.com/ でアプリ登録後、以下を実行してください:\n"
            "  python3 ticktick_cli.py setup"
        )
    return creds["client_id"], creds["client_secret"]


def _write_pending_file(pending: dict) -> str:
    """
    pending state をランダムなファイル名で保存する。
    Fix #1: 固定ファイル名を廃止し mkstemp で予測不可能なパスを生成。
    """
    fd, path = tempfile.mkstemp(prefix="ticktick_oauth_", suffix=".json",
                                dir=tempfile.gettempdir())
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(pending, f)
    except Exception:
        os.unlink(path)
        raise
    return path


def login() -> None:
    """OAuth 2.0 Authorization Code フローを実行してトークンを取得・保存する。"""
    client_id, client_secret = _load_client_credentials()

    state = secrets.token_urlsafe(32)

    auth_params = urlencode({
        "client_id": client_id,
        "scope": SCOPE,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": state,
    })
    auth_url = f"{AUTHORIZE_URL}?{auth_params}"

    headless = _is_headless()

    if headless:
        print("以下のURLをブラウザで開いて認証してください:")
    else:
        print("ブラウザが開きます。TickTickアカウントで認証してください。")
    print(f"\n{auth_url}\n")

    if not headless:
        try:
            open_cmd = shutil.which("open") or shutil.which("xdg-open")
            if open_cmd:
                subprocess.Popen([open_cmd, auth_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                webbrowser.open(auth_url)
        except Exception:
            pass

    code = None

    if headless:
        pasted_url = _prompt_callback_url(CALLBACK_PORT)
        if pasted_url:
            code, received_state, error = _extract_code_from_url(pasted_url)
            if error:
                raise OAuthError(f"OAuth error: {error}")
            if not code:
                raise OAuthError("コールバックURLにcodeが含まれていません")
            if received_state != state:
                raise OAuthError("State mismatch: possible CSRF attack")

    if code is None:
        _CallbackHandler.auth_code = None
        _CallbackHandler.received_state = None
        _CallbackHandler.error = None

        # Fix #3: 常に 127.0.0.1 にバインド
        server = HTTPServer(("127.0.0.1", CALLBACK_PORT), _CallbackHandler)
        server.timeout = 300
        print(f"認証コールバック待機中 (port {CALLBACK_PORT})...")

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

        if _CallbackHandler.received_state != state:
            raise OAuthError("State mismatch: possible CSRF attack")

        code = _CallbackHandler.auth_code

    print("認証コード受信。トークンを取得中...")

    result = _exchange_code(code, client_id, client_secret)

    access_token = result.get("access_token", "")
    scope = result.get("scope", SCOPE)
    expires_in = result.get("expires_in", 0)

    if not access_token:
        raise OAuthError("No access token in response")

    store = TokenStore()
    store.save_auth(access_token=access_token, scope=scope, expires_in=expires_in)

    print("Login successful!")


def login_url_only() -> str:
    """
    認証URLを生成して出力し、state をファイルに保存して即終了。
    ヘッドレス環境での2ステップ認証用（ステップ1）。
    ファイルパスは環境変数 TICKTICK_OAUTH_PENDING_FILE に設定される。
    """
    client_id, _ = _load_client_credentials()

    state = secrets.token_urlsafe(32)

    auth_params = urlencode({
        "client_id": client_id,
        "scope": SCOPE,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": state,
    })
    auth_url = f"{AUTHORIZE_URL}?{auth_params}"

    pending = {
        "state": state,
        "client_id": client_id,
    }
    # Fix #1: ランダムファイル名で保存、パスを環境変数経由で次ステップに渡す
    path = _write_pending_file(pending)
    os.environ[_PENDING_AUTH_ENV] = path

    print(auth_url)
    # ファイルパスをコメントとして stderr に出力（次ステップで使用）
    print(f"[pending_file:{path}]", file=sys.stderr)
    return auth_url


def login_with_code(callback_url: str) -> None:
    """
    コールバックURLからトークンを取得・保存する。
    ヘッドレス環境での2ステップ認証用（ステップ2）。
    """
    # pending ファイルパスを取得（環境変数 → 固定パスフォールバックなし）
    pending_file = os.environ.get(_PENDING_AUTH_ENV, "")
    if not pending_file:
        raise OAuthError(
            "保留中の認証ファイルが見つかりません。\n"
            "先に login --url-only を実行し、出力された [pending_file:...] パスを\n"
            f"環境変数 {_PENDING_AUTH_ENV} に設定してください。"
        )

    # Fix #1: O_RDONLY で直接開き TOCTOU を回避
    try:
        fd = os.open(pending_file, os.O_RDONLY)
    except FileNotFoundError:
        raise OAuthError(f"Pending auth file not found: {pending_file}")

    with os.fdopen(fd, "r") as f:
        pending = json.load(f)

    expected_state = pending["state"]

    code, received_state, error = _extract_code_from_url(callback_url)

    if error:
        raise OAuthError(f"OAuth error: {error}")
    if not code:
        raise OAuthError("コールバックURLにcodeが含まれていません")
    if received_state != expected_state:
        raise OAuthError("State mismatch: possible CSRF attack")

    print("認証コード受信。トークンを取得中...")

    _, client_secret = _load_client_credentials()
    client_id = pending["client_id"]
    result = _exchange_code(code, client_id, client_secret)

    access_token = result.get("access_token", "")
    scope = result.get("scope", SCOPE)
    expires_in = result.get("expires_in", 0)

    if not access_token:
        raise OAuthError("No access token in response")

    store = TokenStore()
    # Fix #5: finally で必ずクリーンアップ
    try:
        store.save_auth(access_token=access_token, scope=scope, expires_in=expires_in)
    finally:
        try:
            os.unlink(pending_file)
        except OSError:
            pass

    print("Login successful!")


if __name__ == "__main__":
    try:
        login()
    except (OAuthError, TokenStoreError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
