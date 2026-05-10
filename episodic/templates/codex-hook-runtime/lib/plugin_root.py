"""プラグインルートの解決ヘルパー。

優先順位:
  1. 環境変数 CLAUDE_PLUGIN_ROOT（hook / command / agent 起動時に Claude Code が注入）
  2. codex-hook-runtime/lib 配置なら codex-hook-runtime
  3. このファイル位置からの相対解決（scripts/lib/ → ../.. = プラグインルート）
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
    path = Path(__file__).resolve()
    runtime_root = path.parent.parent
    if path.parent.name == "lib" and (runtime_root / "bin").is_dir():
        return runtime_root
    # scripts/lib/plugin_root.py から見て parents[2] がプラグインルート
    return path.parents[2]
