#!/usr/bin/env python3
"""
Todoist MCP Token Store

トークンの永続化を管理する。
動的クライアント登録情報も保存。
保存先: ~/.config/todoist-mcp/config.json (パーミッション 0600)
単一アカウントモデル。
Todoistトークンは10年有効のためリフレッシュ不要。
"""

import json
import os
import time
from typing import Any, Dict, Optional


CONFIG_DIR = os.path.expanduser("~/.config/todoist-mcp")
STORE_PATH = os.path.join(CONFIG_DIR, "config.json")


class TokenStoreError(Exception):
    """トークンストアエラー"""
    pass


class TokenStore:
    """トークン永続化管理"""

    def __init__(self):
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        """ストアファイルを読み込み"""
        if not os.path.exists(STORE_PATH):
            return {"client_credentials": None, "auth": None}
        try:
            with open(STORE_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"client_credentials": None, "auth": None}

    def _save(self):
        """ストアファイルに保存 (パーミッション 0600)"""
        os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)
        with open(STORE_PATH, "w") as f:
            json.dump(self._data, f, indent=2)
        os.chmod(STORE_PATH, 0o600)

    # --- クライアント登録情報 ---

    def get_client_credentials(self) -> Optional[Dict[str, Any]]:
        """登録済みクライアント情報を取得"""
        return self._data.get("client_credentials")

    def save_client_credentials(self, client_id: str):
        """動的クライアント登録結果を保存（client_secret不要）"""
        self._data["client_credentials"] = {
            "client_id": client_id,
            "registered_at": int(time.time()),
        }
        self._save()

    # --- 認証トークン ---

    def save_auth(self, access_token: str, scope: str):
        """認証トークンを保存（トークン10年有効、refresh_token不要）"""
        self._data["auth"] = {
            "access_token": access_token,
            "scope": scope,
            "authenticated_at": int(time.time()),
        }
        self._save()

    def remove_auth(self):
        """認証トークンを削除"""
        self._data["auth"] = None
        self._save()

    def is_authenticated(self) -> bool:
        """認証済みかどうか"""
        auth = self._data.get("auth")
        return auth is not None and bool(auth.get("access_token"))

    def get_auth(self) -> Optional[Dict[str, Any]]:
        """認証情報を取得"""
        return self._data.get("auth")

    def get_valid_token(self) -> str:
        """有効なアクセストークンを取得"""
        auth = self._data.get("auth")
        if not auth or not auth.get("access_token"):
            raise TokenStoreError("Not authenticated. Run 'login' first.")
        return auth["access_token"]
