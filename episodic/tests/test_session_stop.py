"""bin/session_stop.py の単体テスト。"""
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
    sys.modules.pop("session_stop", None)
    return importlib.import_module("session_stop")


def test_passes_through_to_hook(mod, monkeypatch) -> None:
    calls: list = []

    class _R:
        returncode = 0

    def fake_run(args, **kw):
        calls.append((args, kw))
        return _R()

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    rc = mod.main()
    assert rc == 0
    assert calls[0][0][0] == sys.executable
    assert str(mod.HOOK_PY) in calls[0][0]
    assert "CLAUDE_PLUGIN_ROOT" in calls[0][1]["env"]


def test_subprocess_exception_yields_zero(mod, monkeypatch) -> None:
    def raise_run(*a, **k):
        raise OSError("boom")

    monkeypatch.setattr(mod.subprocess, "run", raise_run)
    assert mod.main() == 0
