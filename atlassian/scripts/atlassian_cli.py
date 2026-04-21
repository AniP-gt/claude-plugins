#!/usr/bin/env python3
"""
Atlassian MCP CLI (公式 MCP Python SDK 使用)

Streamable HTTP + OAuth 2.1 (PKCE + 動的クライアント登録) で
Atlassian Rovo MCPサーバーに接続し、Jira・Confluenceツールを実行するCLI。

Usage:
    python atlassian_cli.py login
    python atlassian_cli.py tools
    python atlassian_cli.py call <tool_name> --arg key=value
"""

import argparse
import asyncio
import html as _html
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)


MCP_SERVER_URL = "https://mcp.atlassian.com/v1/mcp"
# 認可サーバーは mcp.atlassian.com の oauth-authorization-server メタデータから
# authorization_endpoint=https://mcp.atlassian.com/v1/authorize,
# token_endpoint=https://cf.mcp.atlassian.com/v1/token と判明している。
# OAuthClientProvider には well-known 取得ルートとなるベースURLを渡す
# （mcp SDK 1.9.x は oauth-protected-resource チェーンを自動では辿らないため）
AUTH_SERVER_URL = "https://mcp.atlassian.com"
CALLBACK_PORT = 3031
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"
SCOPE = "openid email profile"
CLIENT_NAME = "Claude Code Atlassian Plugin"

CONFIG_DIR = Path(os.path.expanduser("~/.config/atlassian-mcp"))
CLIENT_INFO_FILE = CONFIG_DIR / "client_info.json"
TOKENS_FILE = CONFIG_DIR / "tokens.json"

# OrbStack Linux VM はホストmacOSのブラウザを呼び出せる
ORBSTACK_OPEN = "/opt/orbstack-guest/bin/open"


def _write_secret_json(path: Path, data: Any) -> None:
    # O_CREAT に 0o600 を渡して作成時点で他ユーザ読み取り不可にする
    # （open()+chmod 方式だと chmod 前の瞬間だけ umask 依存の緩い権限になる）
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    # 既存ファイル上書き時は O_CREAT の mode が効かないため明示的に 0o600 を再適用
    os.chmod(path, 0o600)


class FileTokenStorage(TokenStorage):
    """~/.config/atlassian-mcp/ 配下にトークンとクライアント情報を永続化"""

    def __init__(self) -> None:
        CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)

    async def get_tokens(self) -> OAuthToken | None:
        if not TOKENS_FILE.exists():
            return None
        with open(TOKENS_FILE) as f:
            return OAuthToken.model_validate(json.load(f))

    async def set_tokens(self, tokens: OAuthToken) -> None:
        _write_secret_json(TOKENS_FILE, tokens.model_dump(mode="json", exclude_none=True))

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        if not CLIENT_INFO_FILE.exists():
            return None
        with open(CLIENT_INFO_FILE) as f:
            return OAuthClientInformationFull.model_validate(json.load(f))

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        _write_secret_json(CLIENT_INFO_FILE, client_info.model_dump(mode="json", exclude_none=True))


class _CallbackHandler(BaseHTTPRequestHandler):
    """OAuthコールバック受信ハンドラ"""

    def __init__(self, request, client_address, server, data):
        self.data = data
        super().__init__(request, client_address, server)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        if "code" in params:
            self.data["code"] = params["code"][0]
            self.data["state"] = params.get("state", [None])[0]
            self._respond(200, "Login successful! このタブを閉じてターミナルに戻ってください。")
        elif "error" in params:
            self.data["error"] = params["error"][0]
            self._respond(400, f"認証エラー: {self.data['error']}")
        else:
            self._respond(400, "不明なコールバック")

    def _respond(self, status: int, message: str):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        safe_message = _html.escape(message)
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Atlassian MCP Login</title></head>
<body style="font-family:sans-serif;text-align:center;padding:50px">
<h2>{safe_message}</h2></body></html>"""
        self.wfile.write(html.encode())

    def log_message(self, *_args):
        return


class CallbackServer:
    """認可コードを受け取るローカルHTTPサーバー"""

    def __init__(self, port: int = CALLBACK_PORT):
        self.port = port
        self.data: dict[str, Any] = {"code": None, "state": None, "error": None}
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None

    def _make_handler(self):
        data = self.data

        class _H(_CallbackHandler):
            def __init__(self, req, addr, srv):
                super().__init__(req, addr, srv, data)

        return _H

    def start(self) -> None:
        self.server = HTTPServer(("localhost", self.port), self._make_handler())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=1)

    def wait(self, timeout: int = 300) -> tuple[str, str | None]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.data["code"]:
                return self.data["code"], self.data["state"]
            if self.data["error"]:
                raise RuntimeError(f"OAuth error: {self.data['error']}")
            time.sleep(0.2)
        raise TimeoutError("OAuthコールバック待機がタイムアウトしました（5分）")


def _open_browser(url: str) -> None:
    """ブラウザを開く。OrbStack環境ではホストmacOSのopenを使う"""
    if os.path.exists(ORBSTACK_OPEN):
        subprocess.Popen(
            [ORBSTACK_OPEN, url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    try:
        webbrowser.open(url)
    except Exception:
        pass


def _build_provider() -> tuple[OAuthClientProvider, CallbackServer]:
    storage = FileTokenStorage()
    metadata = OAuthClientMetadata(
        client_name=CLIENT_NAME,
        redirect_uris=[REDIRECT_URI],  # type: ignore[arg-type]
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope=SCOPE,
        token_endpoint_auth_method="none",
    )
    callback = CallbackServer()

    async def redirect_handler(url: str) -> None:
        print(f"ブラウザで認証画面を開きます...", file=sys.stderr)
        _open_browser(url)

    async def callback_handler() -> tuple[str, str | None]:
        return callback.wait()

    provider = OAuthClientProvider(
        server_url=AUTH_SERVER_URL,
        client_metadata=metadata,
        storage=storage,
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )
    return provider, callback


def _extract_text(content: list) -> str:
    """MCPレスポンスのcontentリストからテキストを抽出"""
    if not isinstance(content, list):
        return json.dumps(content, ensure_ascii=False, indent=2)
    parts = []
    for item in content:
        text = getattr(item, "text", None)
        if text is not None:
            parts.append(text)
        elif isinstance(item, str):
            parts.append(item)
        else:
            parts.append(json.dumps(item, ensure_ascii=False, default=str))
    return "\n".join(parts) if parts else ""


def _parse_arg_value(value_str: str):
    """引数値を適切な型に変換"""
    lower = value_str.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    try:
        return int(value_str)
    except ValueError:
        pass
    try:
        return float(value_str)
    except ValueError:
        pass
    try:
        return json.loads(value_str)
    except (json.JSONDecodeError, ValueError):
        pass
    return value_str


async def _with_session(fn):
    """OAuthプロバイダ付きでMCPセッションを開き、fn(session) を実行"""
    provider, callback = _build_provider()
    callback.start()
    try:
        async with streamablehttp_client(url=MCP_SERVER_URL, auth=provider) as (
            read,
            write,
            _get_session_id,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await fn(session)
    finally:
        callback.stop()


async def _cmd_login_async() -> None:
    async def _init(session: ClientSession):
        return None

    await _with_session(_init)
    print("Login successful!")


async def _cmd_tools_async() -> None:
    async def _list(session: ClientSession):
        return await session.list_tools()

    result = await _with_session(_list)
    for tool in result.tools:
        print(f"  {tool.name}")
        desc = (tool.description or "").strip()
        if desc:
            print(f"    {desc.splitlines()[0]}")
        schema = tool.inputSchema or {}
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for pname, pinfo in props.items():
            req_mark = "*" if pname in required else " "
            ptype = pinfo.get("type", "")
            pdesc = pinfo.get("description", "")
            print(f"    {req_mark} {pname} ({ptype}): {pdesc}")
        print()


async def _cmd_call_async(tool_name: str, arg_pairs: list[str] | None) -> None:
    arguments: dict[str, Any] = {}
    for item in arg_pairs or []:
        if "=" not in item:
            print(f"Error: Invalid argument format: {item} (expected key=value)", file=sys.stderr)
            sys.exit(1)
        key, value = item.split("=", 1)
        arguments[key] = _parse_arg_value(value)

    async def _call(session: ClientSession):
        return await session.call_tool(tool_name, arguments)

    result = await _with_session(_call)
    print(_extract_text(list(result.content)))


def cmd_login(args) -> None:
    asyncio.run(_cmd_login_async())


def cmd_tools(args) -> None:
    asyncio.run(_cmd_tools_async())


def cmd_call(args) -> None:
    asyncio.run(_cmd_call_async(args.tool_name, args.arg))


def cmd_logout(args) -> None:
    removed = []
    for path in (TOKENS_FILE, CLIENT_INFO_FILE):
        if path.exists():
            path.unlink()
            removed.append(str(path))
    if removed:
        print("Logged out. Removed:")
        for p in removed:
            print(f"  {p}")
    else:
        print("Not currently authenticated.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Atlassian MCP CLI - Jira・Confluence操作（公式MCP Python SDK経由）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # ログイン（初回はブラウザが自動で開く）
  %(prog)s login

  # ツール一覧
  %(prog)s tools

  # アクセス可能なAtlassianリソースの一覧
  %(prog)s call getAccessibleAtlassianResources

  # Jiraイシュー検索
  %(prog)s call search_jira_issues --arg query="project = PROJ AND status = Open"

  # Confluenceページ検索
  %(prog)s call search_confluence --arg query="meeting notes"

  # ログアウト（トークン削除）
  %(prog)s logout
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("login", help="OAuth 2.1 認証を実行")
    subparsers.add_parser("tools", help="利用可能なAtlassian MCPツール一覧")
    subparsers.add_parser("logout", help="保存されたトークンを削除")

    p_call = subparsers.add_parser("call", help="Atlassian MCPツールを実行")
    p_call.add_argument("tool_name", help="ツール名")
    p_call.add_argument("--arg", action="append", help="ツール引数 (key=value形式、複数指定可)")

    args = parser.parse_args()

    commands = {
        "login": cmd_login,
        "tools": cmd_tools,
        "call": cmd_call,
        "logout": cmd_logout,
    }

    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
