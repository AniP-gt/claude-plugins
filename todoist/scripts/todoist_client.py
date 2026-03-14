#!/usr/bin/env python3
"""
Todoist MCP Streamable HTTP Client

Todoist MCP サーバーに Streamable HTTP で接続し、
Todoistツール（タスク管理・プロジェクト操作等）を実行する。
"""

import requests
import json
import os
import sys
import tempfile
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(__file__))
from token_store import TokenStore, TokenStoreError


class TodoistMCPError(Exception):
    """Todoist MCP通信エラー"""
    pass


class TodoistMCPClient:
    """Todoist MCP Streamable HTTPクライアント"""

    DEFAULT_URL = "https://ai.todoist.net/mcp"

    def __init__(self, debug: bool = False,
                 reuse_session: bool = True, timeout: int = 120):
        self.base_url = self.DEFAULT_URL
        self.debug = debug
        self.request_id = 0
        self.session_id = None
        self.session = requests.Session()
        self.reuse_session = reuse_session
        self.timeout = timeout

        self.token_store = TokenStore()

        if self.reuse_session:
            cached_session_id = self._load_cached_session()
            if cached_session_id:
                self.session_id = cached_session_id
                self._log(f"Reusing cached session: {self.session_id}")
                try:
                    self._send_request("ping", {})
                    return
                except Exception as e:
                    self._log(f"Cached session invalid ({e}), initializing new session")
                    self.session_id = None

        self._initialize()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
        return False

    def _log(self, message: str):
        if self.debug:
            print(f"[DEBUG] {message}")

    def _get_session_cache_path(self) -> str:
        return os.path.join(
            tempfile.gettempdir(),
            "todoist_mcp_session.json"
        )

    def _load_cached_session(self) -> Optional[str]:
        cache_path = self._get_session_cache_path()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    data = json.load(f)
                    return data.get("session_id")
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def _save_session(self):
        cache_path = self._get_session_cache_path()
        try:
            with open(cache_path, "w") as f:
                json.dump({"session_id": self.session_id}, f)
        except IOError:
            pass

    def _build_headers(self) -> Dict[str, str]:
        """共通HTTPヘッダーを構築"""
        token = self.token_store.get_valid_token()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {token}",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        return headers

    def _parse_sse(self, response_bytes: bytes) -> Dict[str, Any]:
        """SSE形式のレスポンスをパース（UTF-8でデコード）"""
        sse_text = response_bytes.decode("utf-8")
        lines = sse_text.strip().split("\n")
        for line in lines:
            if line.startswith("data: "):
                data_json = line[6:]
                return json.loads(data_json)
        raise TodoistMCPError(f"Invalid SSE format: {sse_text[:200]}")

    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """JSON-RPCリクエストを送信"""
        self.request_id += 1
        request_data = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {},
        }

        self._log(f"Sending: {method} {params}")

        headers = self._build_headers()

        try:
            response = self.session.post(
                self.base_url,
                json=request_data,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise TodoistMCPError(f"HTTP request failed: {e}") from e

        if "mcp-session-id" in response.headers:
            self.session_id = response.headers["mcp-session-id"]
            self._log(f"Session ID: {self.session_id}")

        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            response_data = self._parse_sse(response.content)
        else:
            response_data = response.json()

        self._log(f"Received: {json.dumps(response_data, ensure_ascii=False)[:200]}")

        if "error" in response_data:
            error_info = response_data["error"]
            raise TodoistMCPError(
                f"MCP Error [{error_info.get('code')}]: {error_info.get('message')}"
            )

        return response_data.get("result", {})

    def _initialize(self):
        """MCPハンドシェイク実行"""
        init_result = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "todoist-mcp-cli",
                "version": "1.0.0",
            },
        })

        server_info = init_result.get("serverInfo", {})
        self._log(f"Server: {server_info.get('name')} v{server_info.get('version')}")

        self._send_notification("notifications/initialized")

        if self.reuse_session and self.session_id:
            self._save_session()

    def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """JSON-RPC通知を送信"""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }

        headers = self._build_headers()

        try:
            self.session.post(
                self.base_url,
                json=notification,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException:
            pass

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """MCPツールを呼び出し"""
        result = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        return result.get("content", [])

    def list_tools(self) -> List[Dict[str, Any]]:
        """利用可能なツール一覧を取得"""
        result = self._send_request("tools/list")
        return result.get("tools", [])
