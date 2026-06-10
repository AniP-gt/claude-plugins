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
    """hook.py を直接 import し、stdin payload を run() に渡して rc を返す。"""
    calls: list = []

    class _FakeHook:
        @staticmethod
        def read_hook_input():
            return {"session_id": "s"}

        @staticmethod
        def run(payload):
            calls.append(payload)
            return 0

    monkeypatch.setattr(mod, "_load_hook_module", lambda: _FakeHook)
    rc = mod.main()
    assert rc == 0
    assert calls == [{"session_id": "s"}]


def test_sets_plugin_root_env(mod, monkeypatch) -> None:
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)

    class _FakeLoader:
        def exec_module(self, module):
            pass

    import importlib.util as iu

    real_spec = iu.spec_from_file_location
    monkeypatch.setattr(
        mod.importlib.util, "spec_from_file_location",
        lambda name, path: real_spec(name, path),
    )
    mod._load_hook_module()
    import os

    assert os.environ.get("CLAUDE_PLUGIN_ROOT") == str(mod.REPO_ROOT)


def test_hook_exception_yields_zero(mod, monkeypatch) -> None:
    """hook のロード・実行が例外を投げてもフックは 0 を返す（Claude Code を阻害しない）。"""
    def raise_load():
        raise OSError("boom")

    monkeypatch.setattr(mod, "_load_hook_module", raise_load)
    assert mod.main() == 0
