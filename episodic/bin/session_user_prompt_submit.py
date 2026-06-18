#!/usr/bin/env python3
"""UserPromptSubmit hook: ユーザー入力時に pending debounce をキャンセルする。

session/hook.py を直接 import して実行する。subprocess で別インタープリタを
起動しない（毎プロンプト送信のインタープリタ二重起動コストの回避）。
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_PY = REPO_ROOT / "session" / "hook.py"


def _load_hook_module():
    """session/hook.py を一意モジュール名で直接ロードする。

    `session/hook.py`（ファイル）と `session/hook/`（ディレクトリ）が同名共存する
    ため、`import hook` ではなくファイルパス指定でロードする。
    """
    os.environ.setdefault("CLAUDE_PLUGIN_ROOT", str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("episodic_session_hook", HOOK_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    try:
        hook = _load_hook_module()
        return hook.run(hook.read_hook_input())
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
