"""OS 環境差分の薄ラッパ。

テストで monkeypatch しやすいよう、socket / time / config から取得する値を
関数として切り出す。
"""
from __future__ import annotations

import socket
import time

from .config import host_hash as _host_hash


def hostname() -> str:
    return socket.gethostname()


def host_hash(length: int | None = None) -> str:
    return _host_hash(length)


def now() -> float:
    return time.time()
