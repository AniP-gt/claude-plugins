"""bin/session_user_prompt_submit.py の単体テスト。"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "bin"))


@pytest.fixture
def mod(monkeypatch: pytest.MonkeyPatch):
    sys.modules.pop("session_user_prompt_submit", None)
    return importlib.import_module("session_user_prompt_submit")


def test_passes_through(mod, monkeypatch) -> None:
    calls: list = []

    class _R:
        returncode = 0

    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: (calls.append((a, k)), _R())[1])
    rc = mod.main()
    assert rc == 0
    args = calls[0][0][0]
    assert args[0] == sys.executable
    assert str(mod.HOOK_PY) in args
