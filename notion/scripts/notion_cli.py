#!/usr/bin/env python3
"""
Notion MCP CLI (公式 MCP Python SDK 使用)

Streamable HTTP + OAuth 2.1 (PKCE + 動的クライアント登録) で
Notion MCPサーバーに接続し、ページ・データベースツールを実行するCLI。

複数アカウント対応:
- ログイン後に `notion-get-users user_id=self` を呼び、認証ユーザーの
  email/name/id を取得して、`~/.config/notion-mcp/<slug>/` 配下に
  tokens.json / client_info.json / meta.json を保存する。
- 切替は `--account <slug or email>` または `set-default <slug>`。

Usage:
    python notion_cli.py login
    python notion_cli.py accounts
    python notion_cli.py set-default <account>
    python notion_cli.py logout <account>
    python notion_cli.py [--account <account>] tools
    python notion_cli.py [--account <account>] call <tool_name> --arg key=value
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

from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)


MCP_SERVER_URL = "https://mcp.notion.com/mcp"
# OAuthClientProvider.server_url には MCP リソース URL（= MCP_SERVER_URL）をそのまま渡す。
# 新しい mcp SDK は oauth-protected-resource の `resource` フィールドと server_url を厳密に
# 一致比較するため、ベース URL（パスなし）を渡すと
# `Protected resource ... does not match expected ...` で失敗する。
AUTH_SERVER_URL = MCP_SERVER_URL
CALLBACK_PORT = 3032
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"
# Notion MCP は scope を必須としない（DCR 時にサーバー側で適用範囲が決まる）。
SCOPE = ""
CLIENT_NAME = "Claude Code Notion Plugin"

CONFIG_DIR = Path(os.path.expanduser("~/.config/notion-mcp"))
PENDING_DIR = CONFIG_DIR / "_pending"
DEFAULT_FILE = CONFIG_DIR / "default.txt"

# 旧来の単一アカウント保存パス（マイグレーション対象）
LEGACY_TOKENS_FILE = CONFIG_DIR / "tokens.json"
LEGACY_CLIENT_INFO_FILE = CONFIG_DIR / "client_info.json"

# OrbStack Linux VM はホストmacOSのブラウザを呼び出せる
ORBSTACK_OPEN = "/opt/orbstack-guest/bin/open"


def _write_secret_json(path: Path, data: Any) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(path, 0o600)


def _write_secret_text(path: Path, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.chmod(path, 0o600)


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)


class AccountStorage(TokenStorage):
    """アカウント単位にトークン・クライアント情報を永続化するストレージ"""

    def __init__(self, account_dir: Path) -> None:
        self.dir = account_dir
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
<html><head><meta charset="utf-8"><title>Notion MCP Login</title></head>
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


def _build_provider(storage: AccountStorage) -> tuple[OAuthClientProvider, CallbackServer]:
    metadata_kwargs: dict[str, Any] = dict(
        client_name=CLIENT_NAME,
        redirect_uris=[REDIRECT_URI],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="none",
    )
    if SCOPE:
        metadata_kwargs["scope"] = SCOPE
    metadata = OAuthClientMetadata(**metadata_kwargs)  # type: ignore[arg-type]
    callback = CallbackServer()

    async def redirect_handler(url: str) -> None:
        print("ブラウザで認証画面を開きます...", file=sys.stderr)
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


async def _with_session(storage: AccountStorage, fn):
    """OAuthプロバイダ付きでMCPセッションを開き、fn(session) を実行"""
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


def _email_to_slug(email: str) -> str:
    """メールアドレスを安全なディレクトリ名に変換"""
    safe = email.lower().strip()
    # ファイル名で使える文字に正規化
    out_chars = []
    for ch in safe:
        if ch.isalnum() or ch in "-_":
            out_chars.append(ch)
        elif ch in "@.+":
            out_chars.append("-")
    slug = "".join(out_chars).strip("-")
    # 連続ハイフンをまとめる
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "account"


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


def _list_account_entries() -> list[dict[str, Any]]:
    if not CONFIG_DIR.exists():
        return []
    entries = []
    for path in sorted(CONFIG_DIR.iterdir()):
        # シンボリックリンクは除外する（攻撃者が CONFIG_DIR にリンクを仕込んだ場合に
        # `logout` 経由で `shutil.rmtree` がリンク先を削除しうる経路を塞ぐ）
        if not path.is_dir() or path.is_symlink() or path.name.startswith("_"):
            continue
        if not (path / "tokens.json").exists():
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


def _resolve_account(account: str | None) -> Path:
    """account 指定（slug / email / 部分一致）から保存先パスを解決。

    解決順:
      1. `--account` 指定 → slug/email 完全一致 → 部分一致
      2. デフォルト設定（default.txt）あり → それ
      3. アカウントが 1 件のみ → そのまま
      4. 複数あり TTY → 対話選択
      5. 複数あり非 TTY → エラー
    """
    entries = _list_account_entries()
    if not entries:
        raise RuntimeError("アカウントが未設定です。先に `login` を実行してください。")

    if account:
        # 1. slug 完全一致
        for entry in entries:
            if entry["key"] == account:
                return entry["path"]
        # 2. email 完全一致
        for entry in entries:
            if entry.get("email", "").lower() == account.lower():
                return entry["path"]
        # 3. 部分一致（slug or email）
        lower = account.lower()
        matches = [
            entry for entry in entries
            if lower in entry["key"].lower() or lower in entry.get("email", "").lower()
        ]
        if len(matches) == 1:
            return matches[0]["path"]
        if len(matches) > 1:
            keys = ", ".join(m["key"] for m in matches)
            raise RuntimeError(f"アカウント指定 `{account}` が複数にマッチします: {keys}")
        raise RuntimeError(f"アカウントが見つかりません: {account}")

    default_key = _read_default_key()
    if default_key:
        for entry in entries:
            if entry["key"] == default_key:
                return entry["path"]
        # default が指す key が消えている → 進ませる前にデフォルトをクリア
        print(f"warn: デフォルトアカウント '{default_key}' が見つかりません。再選択します。", file=sys.stderr)
        _clear_default_key()

    if len(entries) == 1:
        return entries[0]["path"]

    selected = _prompt_select_account(entries)
    return selected["path"]


def _migrate_legacy_files_if_present() -> None:
    """旧来の ~/.config/notion-mcp/{tokens,client_info}.json があれば
    `_pending` 配下に退避し、login 時にメタ情報付与してリネームできるようにする。
    """
    if not LEGACY_TOKENS_FILE.exists():
        return
    PENDING_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        shutil.move(str(LEGACY_TOKENS_FILE), str(PENDING_DIR / "tokens.json"))
        if LEGACY_CLIENT_INFO_FILE.exists():
            shutil.move(str(LEGACY_CLIENT_INFO_FILE), str(PENDING_DIR / "client_info.json"))
    except OSError as e:
        print(f"warn: legacy ファイルの退避に失敗しました: {e}", file=sys.stderr)


async def _fetch_self_and_teams(storage: AccountStorage) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """1 セッションで notion-get-users(self) と notion-get-teams を取得"""

    async def _call(session: ClientSession):
        user_resp = await session.call_tool("notion-get-users", {"user_id": "self"})
        try:
            teams_resp = await session.call_tool("notion-get-teams", {})
        except Exception as e:  # teams は権限・ワークスペース構成で失敗しうる
            print(f"warn: notion-get-teams 取得に失敗（無視して続行）: {e}", file=sys.stderr)
            teams_resp = None
        return user_resp, teams_resp

    user_resp, teams_resp = await _with_session(storage, _call)

    user_text = _extract_text(list(user_resp.content))
    try:
        user_data = json.loads(user_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"notion-get-users の応答が JSON として解析できません: {e}\n{user_text}") from e
    results = user_data.get("results") or []
    if not results:
        raise RuntimeError(f"notion-get-users self の results が空です: {user_text}")
    user = results[0]

    teams: list[dict[str, Any]] = []
    if teams_resp is not None:
        teams_text = _extract_text(list(teams_resp.content))
        try:
            teams_data = json.loads(teams_text)
            # Notion MCP は `joinedTeams` / `otherTeams` で返す（API バージョンにより
            # `results` / `teams` の場合もあるためフォールバック）
            raw_teams: list[Any] = []
            for key in ("joinedTeams", "otherTeams", "results", "teams"):
                v = teams_data.get(key)
                if isinstance(v, list):
                    raw_teams.extend(v)
            for t in raw_teams:
                if not isinstance(t, dict):
                    continue
                teams.append({
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "role": t.get("role"),
                    "is_member": t.get("is_member"),
                })
        except json.JSONDecodeError:
            print(f"warn: notion-get-teams の応答が JSON ではありません（無視）: {teams_text[:200]}", file=sys.stderr)

    return user, teams


def _prompt_select_account(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """複数アカウントから対話的に 1 件選ばせる。TTY が無ければ例外。"""
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        labels = ", ".join(e["key"] for e in entries)
        raise RuntimeError(
            "複数のアカウントが登録されていますが、デフォルトが未設定で対話 TTY がありません。"
            f" `--account <key>` を指定するか `set-default <key>` を実行してください。"
            f" 候補: {labels}"
        )

    print("複数の Notion アカウントが登録されています。使用するアカウントを選択してください:", file=sys.stderr)
    for idx, entry in enumerate(entries, start=1):
        email = entry.get("email") or "?"
        name = entry.get("name") or "?"
        print(f"  {idx}. {entry['key']}  ({email} / {name})", file=sys.stderr)

    while True:
        try:
            raw = input("番号を入力 (Ctrl+C で中断): ").strip()
        except EOFError:
            raise RuntimeError("選択入力が EOF で中断されました") from None
        if not raw:
            continue
        try:
            n = int(raw)
        except ValueError:
            print("数値で入力してください", file=sys.stderr)
            continue
        if 1 <= n <= len(entries):
            return entries[n - 1]
        print(f"1〜{len(entries)} の範囲で入力してください", file=sys.stderr)


async def _cmd_login_async() -> None:
    _ensure_config_dir()
    _migrate_legacy_files_if_present()

    # 既存の中断残骸はクリア（legacy 退避結果は保持）
    if PENDING_DIR.exists() and not (PENDING_DIR / "tokens.json").exists():
        shutil.rmtree(PENDING_DIR)

    pending_storage = AccountStorage(PENDING_DIR)

    async def _init(session: ClientSession):
        return None

    try:
        await _with_session(pending_storage, _init)
    except BaseException:
        if PENDING_DIR.exists():
            shutil.rmtree(PENDING_DIR, ignore_errors=True)
        raise

    tokens = await pending_storage.get_tokens()
    if tokens is None or not tokens.access_token:
        shutil.rmtree(PENDING_DIR, ignore_errors=True)
        raise RuntimeError("トークン取得に失敗しました（tokens.json が生成されていません）")

    # 認証ユーザー情報と teams を取得（slug 決定用 + meta.json 用）
    try:
        user, teams = await _fetch_self_and_teams(pending_storage)
    except BaseException:
        shutil.rmtree(PENDING_DIR, ignore_errors=True)
        raise

    email = (user.get("email") or "").strip()
    name = (user.get("name") or "").strip()
    user_id = (user.get("id") or "").strip()

    if not email and not user_id:
        shutil.rmtree(PENDING_DIR, ignore_errors=True)
        raise RuntimeError("ユーザー識別子（email / id）が取得できませんでした")

    slug = _email_to_slug(email) if email else f"user-{user_id[:8]}"

    final_dir = CONFIG_DIR / slug
    if final_dir.exists():
        shutil.rmtree(final_dir)
    PENDING_DIR.rename(final_dir)

    meta = {
        "email": email,
        "name": name,
        "user_id": user_id,
        "type": user.get("type", ""),
        "teams": teams,
    }
    _write_secret_json(final_dir / "meta.json", meta)

    if _read_default_key() is None:
        _write_secret_text(DEFAULT_FILE, slug)

    label = email or name or slug
    print(f"Login successful: {label}")
    print(f"Account key: {slug}")
    if teams:
        team_names = ", ".join(t.get("name") or "?" for t in teams[:5])
        more = f" 他{len(teams) - 5}件" if len(teams) > 5 else ""
        print(f"Teams: {team_names}{more}")


async def _cmd_tools_async(account: str | None) -> None:
    account_dir = _resolve_account(account)
    storage = AccountStorage(account_dir)

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


async def _cmd_refresh_meta_async(account: str | None) -> None:
    """既存トークンを使って meta.json（email/name/teams）を再取得・上書きする"""
    account_dir = _resolve_account(account)
    storage = AccountStorage(account_dir)

    user, teams = await _fetch_self_and_teams(storage)
    email = (user.get("email") or "").strip()
    name = (user.get("name") or "").strip()
    user_id = (user.get("id") or "").strip()

    meta_path = account_dir / "meta.json"
    existing: dict[str, Any] = {}
    if meta_path.exists():
        try:
            existing = json.loads(meta_path.read_text())
        except (json.JSONDecodeError, OSError):
            existing = {}

    meta = {
        **existing,
        "email": email or existing.get("email", ""),
        "name": name or existing.get("name", ""),
        "user_id": user_id or existing.get("user_id", ""),
        "type": user.get("type") or existing.get("type", ""),
        "teams": teams,
    }
    _write_secret_json(meta_path, meta)

    print(f"Refreshed: {account_dir.name}")
    print(f"  Email: {meta['email']}")
    print(f"  Name:  {meta['name']}")
    if teams:
        team_names = ", ".join(t.get("name") or "?" for t in teams[:5])
        more = f" 他{len(teams) - 5}件" if len(teams) > 5 else ""
        print(f"  Teams: {team_names}{more}")


async def _cmd_call_async(tool_name: str, arg_pairs: list[str] | None, account: str | None) -> None:
    arguments: dict[str, Any] = {}
    for item in arg_pairs or []:
        if "=" not in item:
            print(f"Error: Invalid argument format: {item} (expected key=value)", file=sys.stderr)
            sys.exit(1)
        key, value = item.split("=", 1)
        arguments[key] = _parse_arg_value(value)

    account_dir = _resolve_account(account)
    storage = AccountStorage(account_dir)

    async def _call(session: ClientSession):
        return await session.call_tool(tool_name, arguments)

    result = await _with_session(storage, _call)
    print(_extract_text(list(result.content)))


def cmd_login(_args) -> None:
    asyncio.run(_cmd_login_async())


def cmd_tools(args) -> None:
    asyncio.run(_cmd_tools_async(args.account))


def cmd_call(args) -> None:
    asyncio.run(_cmd_call_async(args.tool_name, args.arg, args.account))


def cmd_refresh_meta(args) -> None:
    asyncio.run(_cmd_refresh_meta_async(args.account))


def cmd_logout(args) -> None:
    target_dir = _resolve_account(args.account)
    target_key = target_dir.name
    shutil.rmtree(target_dir)
    print(f"Logged out: {target_key}")

    if _read_default_key() == target_key:
        remaining = _list_account_entries()
        if remaining:
            _write_secret_text(DEFAULT_FILE, remaining[0]["key"])
            print(f"Default account set: {remaining[0]['key']}")
        else:
            _clear_default_key()


def cmd_accounts(_args) -> None:
    entries = _list_account_entries()
    default_key = _read_default_key()
    if not entries:
        print("No accounts configured. Run 'login' first.")
        return

    for entry in entries:
        key = entry["key"]
        marker = " [default]" if key == default_key else ""
        email = entry.get("email", "?")
        name = entry.get("name", "?")
        teams = entry.get("teams") or []
        team_names = ", ".join(t.get("name") or "?" for t in teams[:5])
        if len(teams) > 5:
            team_names += f" 他{len(teams) - 5}件"
        print(f"  {key}{marker}")
        print(f"    Email: {email}")
        print(f"    Name:  {name}")
        if team_names:
            print(f"    Teams: {team_names}")
        print()


def cmd_set_default(args) -> None:
    target_dir = _resolve_account(args.account)
    _ensure_config_dir()
    _write_secret_text(DEFAULT_FILE, target_dir.name)
    print(f"Default account set: {target_dir.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Notion MCP CLI - Notion ページ・データベース操作（公式MCP Python SDK経由、複数アカウント対応）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # ログイン（初回はブラウザが自動で開く・認証ユーザーの email を取得して自動命名）
  %(prog)s login

  # 登録済みアカウント一覧
  %(prog)s accounts

  # デフォルトアカウントを切替
  %(prog)s set-default <account_key_or_email>

  # ツール一覧（特定アカウントを指定したい場合は --account）
  %(prog)s tools
  %(prog)s --account hidetsugu-miya-mysis-jp tools

  # ページ検索
  %(prog)s call notion-search --arg query="meeting notes"

  # URL からページ取得（議事録などを Markdown として読む）
  %(prog)s call notion-fetch --arg id="https://www.notion.so/xxxx"

  # ログアウト（個別アカウント）
  %(prog)s logout <account_key_or_email>
        """,
    )
    parser.add_argument(
        "--account",
        default=None,
        help="アカウントキー（slug）またはメールアドレス（部分一致可）。省略時はデフォルト",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("login", help="OAuth 2.1 認証を実行（複数アカウント追加可）")
    subparsers.add_parser("accounts", help="保存済みアカウント一覧")
    subparsers.add_parser("tools", help="利用可能なNotion MCPツール一覧")

    p_logout = subparsers.add_parser("logout", help="アカウントのトークンを削除")
    p_logout.add_argument("account", help="アカウントキー（slug）またはメールアドレス")

    p_default = subparsers.add_parser("set-default", help="デフォルトアカウントを設定")
    p_default.add_argument("account", help="アカウントキー（slug）またはメールアドレス")

    p_call = subparsers.add_parser("call", help="Notion MCPツールを実行")
    p_call.add_argument("tool_name", help="ツール名")
    p_call.add_argument("--arg", action="append", help="ツール引数 (key=value形式、複数指定可)")

    subparsers.add_parser(
        "refresh-meta",
        help="既存トークンで notion-get-users(self) と notion-get-teams を呼び meta.json を再生成（再認証なし）",
    )

    args = parser.parse_args()

    commands = {
        "login": cmd_login,
        "logout": cmd_logout,
        "accounts": cmd_accounts,
        "set-default": cmd_set_default,
        "tools": cmd_tools,
        "call": cmd_call,
        "refresh-meta": cmd_refresh_meta,
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
