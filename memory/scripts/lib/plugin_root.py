"""プラグインルートの解決ヘルパー。

優先順位:
  1. 環境変数 CLAUDE_PLUGIN_ROOT（hook / command / agent 起動時に Claude Code が注入）
  2. このファイル位置からの相対解決（scripts/lib/ → ../.. = プラグインルート）
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        return Path(env).resolve()
    # scripts/lib/plugin_root.py から見て parents[2] がプラグインルート
    return Path(__file__).resolve().parents[2]
