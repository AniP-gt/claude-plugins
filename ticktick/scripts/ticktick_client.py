#!/usr/bin/env python3
"""
TickTick REST API Client

TickTick Open API v1 に直接接続し、タスク管理操作を行う。
Base URL: https://api.ticktick.com/open/v1
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(__file__))
from token_store import TokenStore, TokenStoreError


class TickTickClientError(Exception):
    """TickTick APIクライアントエラー"""
    pass


class TickTickClient:
    """TickTick REST APIクライアント"""

    BASE_URL = "https://api.ticktick.com/open/v1"

    def __init__(self, debug: bool = False, timeout: int = 30):
        self.debug = debug
        self.timeout = timeout
        self.token_store = TokenStore()

    def _log(self, message: str):
        if self.debug:
            print(f"[DEBUG] {message}", file=sys.stderr)

    def _build_headers(self) -> Dict[str, str]:
        token = self.token_store.get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, body: Optional[Dict] = None,
                 params: Optional[Dict] = None) -> Any:
        """HTTP リクエストを送信"""
        url = f"{self.BASE_URL}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        self._log(f"{method} {url}")

        data = json.dumps(body).encode() if body is not None else None
        req = Request(url, data=data, method=method)

        for k, v in self._build_headers().items():
            req.add_header(k, v)

        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode()
                self._log(f"Response: {raw[:300]}")
                if not raw.strip():
                    return None
                return json.loads(raw)
        except HTTPError as e:
            body_text = e.read().decode() if hasattr(e, "read") else ""
            if e.code == 429:
                raise TickTickClientError(f"Rate limit exceeded (HTTP 429). Please wait and retry.")
            raise TickTickClientError(f"HTTP {e.code}: {body_text}") from e
        except URLError as e:
            raise TickTickClientError(f"Network error: {e}") from e

    # ---- Projects ----

    def get_projects(self) -> List[Dict]:
        """全プロジェクト一覧を取得"""
        result = self._request("GET", "/project")
        return result or []

    def get_project(self, project_id: str) -> Dict:
        """プロジェクトをIDで取得"""
        return self._request("GET", f"/project/{project_id}") or {}

    def get_project_data(self, project_id: str) -> Dict:
        """プロジェクトとそのタスク一覧を取得"""
        return self._request("GET", f"/project/{project_id}/data") or {}

    def create_project(self, name: str, color: str = "", view_mode: str = "list",
                       kind: str = "TASK") -> Dict:
        """プロジェクトを作成"""
        body: Dict[str, Any] = {"name": name, "viewMode": view_mode, "kind": kind}
        if color:
            body["color"] = color
        return self._request("POST", "/project", body=body) or {}

    def update_project(self, project_id: str, **kwargs) -> Dict:
        """プロジェクトを更新"""
        return self._request("PUT", f"/project/{project_id}", body=kwargs) or {}

    def delete_project(self, project_id: str) -> None:
        """プロジェクトを削除"""
        self._request("DELETE", f"/project/{project_id}")

    # ---- Tasks ----

    def get_task(self, project_id: str, task_id: str) -> Dict:
        """タスクをIDで取得"""
        return self._request("GET", f"/project/{project_id}/task/{task_id}") or {}

    def create_task(self, title: str, project_id: str = "", content: str = "",
                    due_date: str = "", priority: int = 0,
                    tags: Optional[List[str]] = None,
                    is_all_day: bool = False) -> Dict:
        """タスクを作成"""
        body: Dict[str, Any] = {"title": title, "priority": priority, "isAllDay": is_all_day}
        if project_id:
            body["projectId"] = project_id
        if content:
            body["content"] = content
        if due_date:
            body["dueDate"] = due_date
        if tags:
            body["tags"] = tags
        return self._request("POST", "/task", body=body) or {}

    def update_task(self, task_id: str, **kwargs) -> Dict:
        """タスクを更新"""
        return self._request("POST", f"/task/{task_id}", body=kwargs) or {}

    def complete_task(self, project_id: str, task_id: str) -> None:
        """タスクを完了にする"""
        self._request("POST", f"/project/{project_id}/task/{task_id}/complete")

    def delete_task(self, project_id: str, task_id: str) -> None:
        """タスクを削除"""
        self._request("DELETE", f"/project/{project_id}/task/{task_id}")

    def batch_tasks(self, add: Optional[List[Dict]] = None,
                    update: Optional[List[Dict]] = None,
                    delete: Optional[List[Dict]] = None) -> Dict:
        """タスクのバッチ操作"""
        body: Dict[str, Any] = {}
        if add:
            body["add"] = add
        if update:
            body["update"] = update
        if delete:
            body["delete"] = delete
        return self._request("POST", "/batch/task", body=body) or {}
