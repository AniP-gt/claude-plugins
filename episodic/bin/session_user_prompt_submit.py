#!/usr/bin/env python3
"""UserPromptSubmit hook: ユーザー入力時に pending debounce をキャンセルする。

bash bin/session-user-prompt-submit.sh の Python 化。stdin の JSON ペイロードを
session/hook.py にパススルーする。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_PY = REPO_ROOT / "session" / "hook.py"


def main() -> int:
    env = dict(os.environ)
    env.setdefault("CLAUDE_PLUGIN_ROOT", str(REPO_ROOT))
    try:
        result = subprocess.run(
            [sys.executable, str(HOOK_PY)],
            stdin=sys.stdin,
            env=env,
            check=False,
        )
        return result.returncode
    except (OSError, subprocess.SubprocessError):
        return 0


if __name__ == "__main__":
    sys.exit(main())
