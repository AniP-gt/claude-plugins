#!/usr/bin/env python3
"""
TickTick Token Store

トークンの永続化を管理する。
OAuth2クライアント情報も保存。
保存先: ~/.config/ticktick-mcp/config.json (パーミッション 0600)
単一アカウントモデル。
"""

import json
import os
import time
from typing import Any, Dict, Optional


CONFIG_DIR = os.path.expanduser("~/.config/ticktick-mcp")
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
        # O_CREAT|O_TRUNC で最初から 0o600 で作成し chmod タイミング問題を回避
        fd = os.open(STORE_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(self._data, f, indent=2)

    # --- クライアント登録情報 ---

    def get_client_credentials(self) -> Optional[Dict[str, Any]]:
        """登録済みクライアント情報を取得"""
        return self._data.get("client_credentials")

    def save_client_credentials(self, client_id: str, client_secret: str):
        """OAuth2クライアント情報を保存"""
        self._data["client_credentials"] = {
            "client_id": client_id,
            "client_secret": client_secret,
            "saved_at": int(time.time()),
        }
        self._save()

    # --- 認証トークン ---

    def save_auth(self, access_token: str, scope: str, expires_in: int = 0):
        """認証トークンを保存"""
        self._data["auth"] = {
            "access_token": access_token,
            "scope": scope,
            "authenticated_at": int(time.time()),
            "expires_in": expires_in,
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
