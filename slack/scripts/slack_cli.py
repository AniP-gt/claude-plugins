#!/usr/bin/env python3
"""
Slack MCP CLI (公式 MCP Python SDK 使用)

Streamable HTTP + OAuth 2.0 (PKCE public client) で Slack MCP サーバーに接続し、
Slack操作（検索・送信・チャンネル読み取り等）を実行するCLI。

Slack は RFC 7591 動的クライアント登録をサポートしないため、
固定 CLIENT_ID を pre-populate して SDK の登録ステップをスキップする。

Usage:
    python slack_cli.py login
    python slack_cli.py logout <workspace>
    python slack_cli.py workspaces
    python slack_cli.py set-default <workspace>
    python slack_cli.py tools
    python slack_cli.py call <tool_name> --arg key=value
"""

from __future__ import annotations

import argparse
import asyncio
import html as _html
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)


MCP_SERVER_URL = "https://mcp.slack.com/mcp"
# OAuth メタデータは https://mcp.slack.com/.well-known/oauth-authorization-server で提供される。
# issuer は https://slack.com だが、well-known は mcp.slack.com 側にしかない。
# SDK は server_url からパスを剥がして well-known を引きに行くため mcp.slack.com を指定する。
AUTH_SERVER_URL = "https://mcp.slack.com"

# 第三者アプリの固定 CLIENT_ID（PKCE public client）。既存プラグイン踏襲。
SLACK_CLIENT_ID = "1601185624273.8899143856786"

# Slack はカンマ区切り scope を要求する
SCOPES = ",".join([
    "search:read.public",
    "chat:write",
    "channels:history",
    "groups:history",
    "mpim:history",
    "im:history",
    "users:read",
])

CALLBACK_PORT = 3118
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"
CLIENT_NAME = "Claude Code Slack Plugin"

CONFIG_DIR = Path(os.path.expanduser("~/.config/slack-mcp"))
PENDING_DIR = CONFIG_DIR / "_pending"
DEFAULT_FILE = CONFIG_DIR / "default.txt"

# OrbStack Linux VM はホストmacOSのブラウザを呼び出せる
ORBSTACK_OPEN = "/opt/orbstack-guest/bin/open"

AUTH_TEST_URL = "https://slack.com/api/auth.test"


def _write_secret_json(path: Path, data: Any) -> None:
    # O_CREAT に 0o600 を渡して作成時点で他ユーザ読み取り不可にする
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    # 既存ファイル上書き時は O_CREAT の mode が効かないため明示的に再適用
    os.chmod(path, 0o600)


def _write_secret_text(path: Path, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.chmod(path, 0o600)


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)


def _is_headless() -> bool:
    """ブラウザが開けない環境かを判定する"""
    if os.path.exists(ORBSTACK_OPEN):
        return False
    if os.path.exists("/.dockerenv"):
        return True
    if os.environ.get("CONTAINER") or os.environ.get("container"):
        return True
    if sys.platform == "linux" and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return True
    return False


def _open_browser(url: str) -> None:
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


def _make_workspace_key(team_name: str, team_id: str) -> str:
    safe = (team_name or "unknown").lower().strip().replace(" ", "-")
    # ファイル名に使えない文字を除去
    safe = "".join(ch for ch in safe if ch.isalnum() or ch in "-_")
    return f"{safe}-{team_id}" if safe else team_id


class WorkspaceStorage(TokenStorage):
    """ワークスペース単位にトークン・クライアント情報を永続化するストレージ"""

    def __init__(self, workspace_dir: Path) -> None:
        self.dir = workspace_dir
        self.dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.tokens_path = self.dir / "tokens.json"
        self.client_info_path = self.dir / "client_info.json"

    async def get_tokens(self) -> OAuthToken | None:
        if not self.tokens_path.exists():
            return None
        with open(self.tokens_path) as f:
            return OAuthToken.model_validate(json.load(f))

    async def set_tokens(self, tokens: OAuthToken) -> None:
        _write_secret_json(
            self.tokens_path,
            tokens.model_dump(mode="json", exclude_none=True),
        )

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        if not self.client_info_path.exists():
            return None
        with open(self.client_info_path) as f:
            return OAuthClientInformationFull.model_validate(json.load(f))

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        _write_secret_json(
            self.client_info_path,
            client_info.model_dump(mode="json", exclude_none=True),
        )


def _preseed_client_info(storage: WorkspaceStorage) -> None:
    """固定 CLIENT_ID の client_info.json を事前投入し、SDK の動的登録をスキップさせる"""
    if storage.client_info_path.exists():
        return
    info = OAuthClientInformationFull(
        client_id=SLACK_CLIENT_ID,
        client_secret=None,
        redirect_uris=[REDIRECT_URI],  # type: ignore[arg-type]
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope=SCOPES,
        token_endpoint_auth_method="none",
        client_name=CLIENT_NAME,
    )
    _write_secret_json(
        storage.client_info_path,
        info.model_dump(mode="json", exclude_none=True),
    )


class _SlackOAuthClientProvider(OAuthClientProvider):
    """Slack 用の scope 検証を無効化する

    Slack は OAuth レスポンスに本プラグインが当該リクエストで要求したスコープだけでなく、
    過去に同じ OAuth アプリ（公開 CLIENT_ID）へ許可された他スコープも含めて累積的に返す。
    （例: 要求 `search:read.public,chat:write,...` に対し `canvases:read` 等も返る）
    これは OAuth 2.1 の "subset grant" ルールに反するが Slack 側の仕様であり、
    SDK 既定の `_validate_token_scopes` は正当なトークンを拒否してしまう。
    実行時は必要スコープが応答に含まれていれば十分で、余剰スコープで副作用は生じないため
    検証自体を無効化する（OAuth 2.1 の scope 検証は任意）。
    """

    async def _validate_token_scopes(self, token_response: OAuthToken) -> None:
        return


class _CallbackHandler(BaseHTTPRequestHandler):
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
<html><head><meta charset="utf-8"><title>Slack MCP Login</title></head>
<body style="font-family:sans-serif;text-align:center;padding:50px">
<h2>{safe_message}</h2></body></html>"""
        self.wfile.write(html.encode())

    def log_message(self, *_args):
        return


class CallbackServer:
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


def _build_provider(storage: WorkspaceStorage) -> tuple[_SlackOAuthClientProvider, CallbackServer]:
    metadata = OAuthClientMetadata(
        client_name=CLIENT_NAME,
        redirect_uris=[REDIRECT_URI],  # type: ignore[arg-type]
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope=SCOPES,
        token_endpoint_auth_method="none",
    )
    callback = CallbackServer()

    async def redirect_handler(url: str) -> None:
        print("ブラウザで認証画面を開きます...", file=sys.stderr)
        _open_browser(url)

    async def callback_handler() -> tuple[str, str | None]:
        return callback.wait()

    provider = _SlackOAuthClientProvider(
        server_url=AUTH_SERVER_URL,
        client_metadata=metadata,
        storage=storage,
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )
    return provider, callback


async def _with_session(storage: WorkspaceStorage, fn):
    provider, callback = _build_provider(storage)
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


def _read_default_key() -> str | None:
    if not DEFAULT_FILE.exists():
        return None
    try:
        key = DEFAULT_FILE.read_text().strip()
    except OSError:
        return None
    return key or None


def _clear_default_key() -> None:
    if DEFAULT_FILE.exists():
        DEFAULT_FILE.unlink()


def _list_workspace_entries() -> list[dict[str, Any]]:
    if not CONFIG_DIR.exists():
        return []
    entries = []
    for path in sorted(CONFIG_DIR.iterdir()):
        if not path.is_dir() or path.name.startswith("_"):
            continue
        meta_path = path / "meta.json"
        meta: dict[str, Any] = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except (json.JSONDecodeError, OSError):
                meta = {}
        entries.append({"key": path.name, "path": path, **meta})
    return entries


def _resolve_workspace(workspace: str | None) -> Path:
    entries = _list_workspace_entries()
    if not entries:
        raise RuntimeError("ワークスペースが未設定です。先に `login` を実行してください。")

    if workspace:
        for entry in entries:
            if entry["key"] == workspace:
                return entry["path"]
        # 部分一致検索
        lower = workspace.lower()
        for entry in entries:
            if lower in entry["key"].lower():
                return entry["path"]
        raise RuntimeError(f"ワークスペースが見つかりません: {workspace}")

    default_key = _read_default_key()
    if default_key:
        for entry in entries:
            if entry["key"] == default_key:
                return entry["path"]
    # default 不整合時は最初のエントリ
    return entries[0]["path"]


async def _fetch_team_info(access_token: str) -> tuple[str, str]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            AUTH_TEST_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"auth.test failed: {data.get('error', 'unknown')}")
    team_id = data.get("team_id") or ""
    team_name = data.get("team") or "unknown"
    if not team_id:
        raise RuntimeError("auth.test にteam_idが含まれていません")
    return team_id, team_name


async def _cmd_login_async() -> None:
    if _is_headless():
        print(
            "Error: ヘッドレス環境を検出しました。デスクトップ環境で `slack_cli.py login` を実行してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    _ensure_config_dir()

    # 前回中断時の残骸をクリア
    if PENDING_DIR.exists():
        shutil.rmtree(PENDING_DIR)

    pending_storage = WorkspaceStorage(PENDING_DIR)
    _preseed_client_info(pending_storage)

    async def _init(session: ClientSession):
        return None

    try:
        await _with_session(pending_storage, _init)
    except BaseException:
        # 失敗時は _pending を残さない
        if PENDING_DIR.exists():
            shutil.rmtree(PENDING_DIR, ignore_errors=True)
        raise

    tokens = await pending_storage.get_tokens()
    if tokens is None or not tokens.access_token:
        shutil.rmtree(PENDING_DIR, ignore_errors=True)
        raise RuntimeError("トークン取得に失敗しました（tokens.json が生成されていません）")

    try:
        team_id, team_name = await _fetch_team_info(tokens.access_token)
    except BaseException:
        shutil.rmtree(PENDING_DIR, ignore_errors=True)
        raise

    key = _make_workspace_key(team_name, team_id)
    final_dir = CONFIG_DIR / key
    if final_dir.exists():
        shutil.rmtree(final_dir)
    PENDING_DIR.rename(final_dir)

    meta = {
        "team_id": team_id,
        "team_name": team_name,
        "scope": tokens.scope or "",
    }
    _write_secret_json(final_dir / "meta.json", meta)

    if _read_default_key() is None:
        _write_secret_text(DEFAULT_FILE, key)

    print(f"Login successful: {team_name} ({team_id})")
    print(f"Workspace key: {key}")


async def _cmd_tools_async(workspace: str | None) -> None:
    workspace_dir = _resolve_workspace(workspace)
    storage = WorkspaceStorage(workspace_dir)

    async def _list(session: ClientSession):
        return await session.list_tools()

    result = await _with_session(storage, _list)
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


def _extract_text(content: list) -> str:
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


async def _cmd_call_async(tool_name: str, arg_pairs: list[str] | None, workspace: str | None) -> None:
    arguments: dict[str, Any] = {}
    for item in arg_pairs or []:
        if "=" not in item:
            print(f"Error: Invalid argument format: {item} (expected key=value)", file=sys.stderr)
            sys.exit(1)
        key, value = item.split("=", 1)
        arguments[key] = _parse_arg_value(value)

    workspace_dir = _resolve_workspace(workspace)
    storage = WorkspaceStorage(workspace_dir)

    async def _call(session: ClientSession):
        return await session.call_tool(tool_name, arguments)

    result = await _with_session(storage, _call)
    print(_extract_text(list(result.content)))


def cmd_login(_args) -> None:
    asyncio.run(_cmd_login_async())


def cmd_tools(args) -> None:
    asyncio.run(_cmd_tools_async(args.workspace))


def cmd_call(args) -> None:
    asyncio.run(_cmd_call_async(args.tool_name, args.arg, args.workspace))


def cmd_logout(args) -> None:
    entries = _list_workspace_entries()
    target = None
    for entry in entries:
        if entry["key"] == args.workspace:
            target = entry
            break
    if target is None:
        print(f"ワークスペースが見つかりません: {args.workspace}", file=sys.stderr)
        sys.exit(1)

    shutil.rmtree(target["path"])
    print(f"Logged out: {target['key']}")

    if _read_default_key() == target["key"]:
        remaining = [e for e in _list_workspace_entries() if e["key"] != target["key"]]
        if remaining:
            _write_secret_text(DEFAULT_FILE, remaining[0]["key"])
            print(f"Default workspace set: {remaining[0]['key']}")
        else:
            _clear_default_key()


def cmd_workspaces(_args) -> None:
    entries = _list_workspace_entries()
    default_key = _read_default_key()
    if not entries:
        print("No workspaces configured. Run 'login' first.")
        return

    for entry in entries:
        key = entry["key"]
        marker = " [default]" if key == default_key else ""
        team_name = entry.get("team_name", "?")
        team_id = entry.get("team_id", "?")
        scope = entry.get("scope", "N/A")
        print(f"  {key}{marker}")
        print(f"    Team: {team_name} ({team_id})")
        print(f"    Scope: {scope}")
        print()


def cmd_set_default(args) -> None:
    entries = _list_workspace_entries()
    keys = [e["key"] for e in entries]
    if args.workspace not in keys:
        print(f"ワークスペースが見つかりません: {args.workspace}", file=sys.stderr)
        sys.exit(1)
    _ensure_config_dir()
    _write_secret_text(DEFAULT_FILE, args.workspace)
    print(f"Default workspace set: {args.workspace}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Slack MCP CLI - Slack操作（検索・送信・チャンネル読み取り等、公式MCP Python SDK経由）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # ログイン（ブラウザが自動で開く）
  %(prog)s login

  # ワークスペース確認
  %(prog)s workspaces

  # ツール一覧
  %(prog)s tools

  # メッセージ検索
  %(prog)s call slack_search_public --arg query="hello" --arg limit=3

  # メッセージ送信
  %(prog)s call slack_send_message --arg channel_id="C..." --arg message="Hello!"

  # ログアウト
  %(prog)s logout <workspace_key>
        """,
    )
    parser.add_argument("--workspace", default=None, help="ワークスペースキー（省略時はデフォルト）")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("login", help="OAuth 2.0 (PKCE) 認証を実行")
    subparsers.add_parser("workspaces", help="保存済みワークスペース一覧")
    subparsers.add_parser("tools", help="利用可能なSlack MCPツール一覧")

    p_logout = subparsers.add_parser("logout", help="ワークスペースのトークンを削除")
    p_logout.add_argument("workspace", help="ワークスペースキー")

    p_default = subparsers.add_parser("set-default", help="デフォルトワークスペースを設定")
    p_default.add_argument("workspace", help="ワークスペースキー")

    p_call = subparsers.add_parser("call", help="Slack MCPツールを実行")
    p_call.add_argument("tool_name", help="ツール名")
    p_call.add_argument("--arg", action="append", help="ツール引数 (key=value形式、複数指定可)")

    args = parser.parse_args()

    commands = {
        "login": cmd_login,
        "logout": cmd_logout,
        "workspaces": cmd_workspaces,
        "set-default": cmd_set_default,
        "tools": cmd_tools,
        "call": cmd_call,
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
